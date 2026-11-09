#!/usr/bin/env python3
"""
Обновляет объединённую бесплатную подписку.

Скачивает источники по порядку приоритета (сначала списки для России), декодирует base64,
убирает дубликаты (один и тот же сервер под разными именами считается одним), у больших
списков берёт не больше max_count случайных серверов и сохраняет plain + base64.
Порядок в free_subs.txt — порядок приоритета источников.
"""
import base64
import random
import re
import ssl
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

# (url, max_count) — 0 = брать целиком. Порядок = приоритет.
SOURCES = [
    # Россия: белые списки и обход блокировок
    ("https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt", 0),
    ("https://raw.githubusercontent.com/zieng2/wl/main/vless_lite.txt", 0),
    ("https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt", 0),
    ("https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt", 0),
    ("https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt", 0),
    ("https://sub.vlessfo.ru/vlessforu/working_configs.txt", 0),
    # Единый список (как «GitHub Page» в YPtun): ~20 000 vless, обновляется раз в час — случайная выборка
    ("https://breead1337.github.io/ws-cache-9e41/v.txt", 1000),
    # Общие агрегаторы — только выборка
    ("https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/mix.txt", 250),
]

PROTOCOLS = ("vless://", "vmess://", "trojan://", "ss://", "ssr://", "hysteria2://", "hy2://", "tuic://")
# Заглушки вида «подписка устарела» и заведомо пустые адреса
BAD_HOSTS = {"0.0.0.0", "127.0.0.1", "localhost", ""}
SMALL_LIMIT = 1500


def is_base64(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    if not re.match(r"^[A-Za-z0-9+/=_\-\s]+$", s):
        return False
    try:
        base64.b64decode(s + "=" * (-len(s) % 4), validate=False)
        return True
    except Exception:
        return False


def fetch(url: str) -> str:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "ABS-SubUpdater/1.1"})
    with urllib.request.urlopen(req, context=ctx, timeout=40) as r:
        return r.read().decode("utf-8", errors="ignore")


def decode_body(content: str) -> str:
    content = content.strip()
    if "://" not in content[:500] and is_base64(content):
        try:
            compact = re.sub(r"\s+", "", content)
            return base64.urlsafe_b64decode(compact.replace("+", "-").replace("/", "_") + "=" * (-len(compact) % 4)).decode("utf-8", errors="ignore")
        except Exception:
            pass
    return content


def dedup_key(link: str) -> str:
    """Ключ сервера без имени (#fragment): одинаковые серверы с разными подписями — дубликаты."""
    if link.startswith("vmess://"):
        return link.split("#", 1)[0]
    return link.split("#", 1)[0].rstrip("/")


def host_of(link: str) -> str:
    if link.startswith("vmess://"):
        return "vmess"  # хост внутри base64, проверит filter_working.py
    try:
        return (urlsplit(link).hostname or "").lower()
    except Exception:
        return ""


def extract_links(body: str) -> list[str]:
    out = []
    for line in decode_body(body).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or not line.startswith(PROTOCOLS):
            continue
        if host_of(line) in BAD_HOSTS:
            continue
        out.append(line)
    return out


def pick(sources_links: list[tuple[list[str], int]], rng: random.Random) -> list[str]:
    """Объединяет списки по приоритету: дубликаты убираются, лимит источника тратится только на новые серверы."""
    seen: set[str] = set()
    result: list[str] = []
    for links, max_count in sources_links:
        if max_count > 0:
            links = links[:]
            rng.shuffle(links)
        taken = 0
        for link in links:
            if max_count > 0 and taken >= max_count:
                break
            key = dedup_key(link)
            if key in seen:
                continue
            seen.add(key)
            result.append(link)
            taken += 1
    return result


def main():
    rng = random.Random()
    collected = []
    for url, max_count in SOURCES:
        print(f"→ {url} (лимит: {max_count or 'нет'})")
        try:
            links = extract_links(fetch(url))
            print(f"  найдено {len(links)}")
            collected.append((links, max_count))
        except Exception as e:
            print(f"  FAIL: {e}")

    configs = pick(collected, rng)
    print(f"\nUnique configs: {len(configs)}")
    if not configs:
        print("Пусто — файлы не перезаписываю")
        return

    body = "\n".join(configs)
    plain = Path("free_subs.txt")
    b64 = Path("free_subs.b64")
    plain.write_text(body + "\n", encoding="utf-8")
    b64.write_text(base64.b64encode(body.encode()).decode(), encoding="utf-8")
    print(f"Saved: {plain} ({plain.stat().st_size // 1024} KB)")
    print(f"Saved: {b64} ({b64.stat().st_size // 1024} KB)")
    # Маленькая версия для клиентов, которым тяжело с большими подписками (её затем фильтрует filter_working.py)
    small_txt = "\n".join(configs[:SMALL_LIMIT]) + "\n"
    Path("free_subs_small.txt").write_text(small_txt, encoding="utf-8")
    Path("free_subs_small.b64").write_text(base64.b64encode(small_txt.encode()).decode(), encoding="utf-8")
    print(f"Saved small: free_subs_small.b64 ({Path('free_subs_small.b64').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
