#!/usr/bin/env python3
"""
Обновляет объединённую бесплатную подписку.
Скачивает источники, декодирует base64, убирает дубликаты, сохраняет plain + base64.
"""
import base64
import re
import urllib.request
import ssl
from pathlib import Path

SOURCES = [
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "https://breead1337.github.io/ws-cache-9e41/v.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt",
    "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/mix.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/hamedcode/port-based-v2ray-configs/main/sub/vless.txt",
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list_raw.txt",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/chengaopan/AutoMergePublicNodes/master/list.txt",
]

PROTOCOLS = ("vless://", "vmess://", "trojan://", "ss://", "ssr://", "hysteria2://", "hy2://", "tuic://")

def is_base64(s: str) -> bool:
    s = s.strip()
    if not s or len(s) % 4 != 0:
        return False
    if not re.match(r"^[A-Za-z0-9+/=\s]+$", s):
        return False
    try:
        base64.b64decode(s, validate=True)
        return True
    except Exception:
        return False

def fetch(url: str) -> str:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "ABS-SubUpdater/1.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=40) as r:
        return r.read().decode("utf-8", errors="ignore")

def main():
    configs = set()
    for url in SOURCES:
        print(f"→ {url}")
        try:
            content = fetch(url).strip()
            if is_base64(content) and "\n" not in content[:300]:
                try:
                    content = base64.b64decode(content).decode("utf-8", errors="ignore")
                    print("  (decoded base64)")
                except Exception:
                    pass
            count = 0
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith(PROTOCOLS):
                    configs.add(line)
                    count += 1
            print(f"  +{count}")
        except Exception as e:
            print(f"  FAIL: {e}")

    print(f"\nUnique configs: {len(configs)}")
    out_dir = Path(".")
    plain = out_dir / "free_subs.txt"
    b64 = out_dir / "free_subs.b64"
    sorted_cfgs = sorted(configs)
    plain.write_text("\n".join(sorted_cfgs) + "\n", encoding="utf-8")
    b64.write_text(base64.b64encode("\n".join(sorted_cfgs).encode()).decode(), encoding="utf-8")
    print(f"Saved: {plain} ({plain.stat().st_size // 1024} KB)")
    print(f"Saved: {b64} ({b64.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    main()
