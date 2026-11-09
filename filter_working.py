#!/usr/bin/env python3
"""
Фильтрует подписку простым TCP + TLS проверками.
Быстро, стабильно, не требует sing-box.
"""
import os
import sys
import base64
import socket
import ssl
import concurrent.futures
from urllib.parse import urlparse
from pathlib import Path

MAX_KEEP = int(os.environ.get("MAX_KEEP", "600"))
TIMEOUT = float(os.environ.get("TIMEOUT", "5"))
WORKERS = int(os.environ.get("WORKERS", "30"))
MIN_WORKING = int(os.environ.get("MIN_WORKING", "20"))


def parse_host_port(url: str):
    if url.startswith("vmess://"):
        try:
            import json
            raw = url[len("vmess://"):].split("#", 1)[0].strip()
            data = json.loads(base64.urlsafe_b64decode(raw.replace("+", "-").replace("/", "_") + "=" * (-len(raw) % 4)))
            host = str(data.get("add") or "").strip()
            port = int(data.get("port") or 443)
            return (host or None), port
        except Exception:
            return None, None
    try:
        p = urlparse(url)
        host = p.hostname
        port = p.port
        if not host:
            return None, None
        if port is None:
            port = 443
        return host, port
    except Exception:
        return None, None


def check_one(url: str) -> tuple[str, bool]:
    host, port = parse_host_port(url)
    if not host:
        return url, False

    try:
        # TCP
        sock = socket.create_connection((host, port), timeout=TIMEOUT)
        sock.settimeout(TIMEOUT)

        # TLS (если порт 443 или выглядит как TLS)
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                ssock.settimeout(TIMEOUT)
                # Просто факт, что TLS handshake прошёл
                return url, True
        except ssl.SSLError:
            # TCP есть, но TLS нет — для многих протоколов это нормально
            return url, True
        except Exception:
            return url, False
        finally:
            try:
                sock.close()
            except Exception:
                pass
    except Exception:
        return url, False


def main():
    src = Path("free_subs.txt")
    if not src.exists():
        src = Path("free_subs_small.txt")
    if not src.exists():
        print("Нет входного файла")
        sys.exit(1)

    lines = [
        line.strip()
        for line in src.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.startswith("#") and "://" in line
    ]
    print(f"Всего конфигов: {len(lines)}")

    if not lines:
        print("Пусто")
        return

    print("Проверяю TCP + TLS...")
    working = []

    # executor.map сохраняет порядок входа — порядок приоритета источников (Россия первой)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        for url, ok in executor.map(check_one, lines):
            if ok:
                working.append(url)

    print(f"Рабочих (TCP/TLS): {len(working)}")

    if len(working) < MIN_WORKING:
        print(f"Слишком мало рабочих ({len(working)} < {MIN_WORKING}). Файл не перезаписываю.")
        return

    working = working[:MAX_KEEP]

    out_lines = ["#profile-title: 🔥 ABS free"]
    out_lines.extend(working)

    out_txt = Path("free_subs_small.txt")
    out_b64 = Path("free_subs_small.b64")

    out_txt.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    out_b64.write_text(
        base64.b64encode("\n".join(out_lines).encode()).decode() + "\n",
        encoding="utf-8",
    )

    print(f"Сохранено: {len(working)} конфигов")


if __name__ == "__main__":
    main()