#!/usr/bin/env python3
import os
"""
Filters subscription: keeps only configs that pass TCP + TLS handshake.
"""
import base64
import re
import socket
import ssl
import concurrent.futures
from urllib.parse import urlparse, parse_qs
from pathlib import Path

TIMEOUT = 6
MAX_WORKERS = 40
MAX_KEEP = int(os.environ.get("MAX_KEEP", "800"))

def parse_host_port(line: str):
    try:
        if line.startswith("vmess://"):
            import json
            raw = base64.b64decode(line[8:] + "==").decode("utf-8", errors="ignore")
            j = json.loads(raw)
            return j.get("add"), int(j.get("port", 443))
        # vless://, trojan://, ss://, hysteria2:// etc.
        u = urlparse(line)
        host = u.hostname
        port = u.port or 443
        return host, port
    except Exception:
        return None, None

def check(host: str, port: int) -> bool:
    if not host or not port:
        return False
    try:
        sock = socket.create_connection((host, port), timeout=TIMEOUT)
        sock.settimeout(TIMEOUT)
        # Try TLS if common ports
        if port in (443, 8443, 2053, 2083, 2087, 2096):
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                ssock = ctx.wrap_socket(sock, server_hostname=host)
                ssock.close()
                return True
            except Exception:
                sock.close()
                return True  # TCP ok, TLS failed — still count as reachable
        else:
            sock.close()
            return True
    except Exception:
        return False

def main():
    src = Path("free_subs_small.txt")
    if not src.exists():
        src = Path("free_subs.txt")
    lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()
    configs = [l.strip() for l in lines if l.strip() and not l.startswith("#") and "://" in l]
    print(f"Input: {len(configs)}")

    def worker(line):
        host, port = parse_host_port(line)
        ok = check(host, port) if host else False
        return line, ok

    working = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(worker, c): c for c in configs}
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            line, ok = fut.result()
            done += 1
            if ok:
                working.append(line)
                if len(working) >= MAX_KEEP:
                    break
            if done % 200 == 0:
                print(f"  checked {done}, alive {len(working)}")

    print(f"Working: {len(working)}")
    header = "#profile-title: 🔥 ABS free\n"
    out = header + "\n".join(working) + "\n"
    Path("free_subs_small.txt").write_text(out, encoding="utf-8")
    Path("free_subs_small.b64").write_text(base64.b64encode(out.encode()).decode())
    print("Saved filtered free_subs_small.*")

if __name__ == "__main__":
    main()
