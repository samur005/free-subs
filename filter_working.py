#!/usr/bin/env python3
"""
Фильтрует подписку через реальный тест sing-box.
Не затирает файл, если рабочих нод слишком мало.
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
TIMEOUT = float(os.environ.get("TIMEOUT", "10"))
WORKERS = int(os.environ.get("WORKERS", "10"))
MIN_WORKING = int(os.environ.get("MIN_WORKING", "30"))   # если меньше — не перезаписываем
TEST_URL = "https://www.gstatic.com/generate_204"


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

    print("Запускаю проверку через sing-box...")
    batch = SingBoxBatch(lines, batch_size=30, log_level="error")

    working = []
    try:
        results = batch.check(
            test_url=TEST_URL,
            timeout=TIMEOUT,
            workers=WORKERS,
        )
        for r in results:
            if r.working and r.latency_ms and r.latency_ms < 5000:
                working.append(r)
                print(f"OK  {r.latency_ms:6.0f} ms  {r.protocol:10}  {r.ip}")
    except Exception as e:
        print(f"Ошибка при проверке: {e}")
    finally:
        try:
            batch.stop()
        except Exception:
            pass

    print(f"Рабочих найдено: {len(working)}")

    if len(working) < MIN_WORKING:
        print(f"Слишком мало рабочих ({len(working)} < {MIN_WORKING}). Файл не перезаписываю.")
        # Можно раскомментировать, если хочешь хотя бы что-то оставить:
        # if working:
        #     pass
        return

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

    print(f"Сохранено рабочих: {len(working)}")


if __name__ == "__main__":
    main()