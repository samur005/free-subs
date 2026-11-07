#!/usr/bin/env python3
"""
Фильтрует подписку через реальный тест sing-box.
Оставляет только рабочие ноды, сортирует по latency.
"""
import os
import sys
import base64
from pathlib import Path

try:
    from singbox2proxy import SingBoxBatch
except ImportError:
    print("Установи: pip install singbox2proxy")
    sys.exit(1)

MAX_KEEP = int(os.environ.get("MAX_KEEP", "400"))
TIMEOUT = float(os.environ.get("TIMEOUT", "8"))
WORKERS = int(os.environ.get("WORKERS", "12"))
TEST_URL = "https://www.gstatic.com/generate_204"


def main():
    src = Path("free_subs.txt")
    if not src.exists():
        src = Path("free_subs_small.txt")
    if not src.exists():
        print("Нет входного файла (free_subs.txt / free_subs_small.txt)")
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

    print("Запускаю проверку через sing-box...")
    batch = SingBoxBatch(lines, batch_size=40, log_level="error")

    working = []
    try:
        results = batch.check(
            test_url=TEST_URL,
            timeout=TIMEOUT,
            workers=WORKERS,
        )
        for r in results:
            if r.working and r.latency_ms and r.latency_ms < 3000:
                working.append(r)
                print(f"OK  {r.latency_ms:6.0f} ms  {r.protocol:10}  {r.ip}")
    finally:
        batch.stop()

    working.sort(key=lambda x: x.latency_ms or 9999)
    working = working[:MAX_KEEP]

    out_lines = ["#profile-title: 🔥 ABS free"]
    out_lines.extend(r.url for r in working)

    out_txt = Path("free_subs_small.txt")
    out_b64 = Path("free_subs_small.b64")

    out_txt.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    out_b64.write_text(
        base64.b64encode("\n".join(out_lines).encode()).decode() + "\n",
        encoding="utf-8",
    )

    print(f"\nОставлено рабочих: {len(working)} / {len(lines)}")
    print(f"Сохранено в {out_txt} и {out_b64}")


if __name__ == "__main__":
    main()