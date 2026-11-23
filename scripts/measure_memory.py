"""Đo RAM (RSS) của tiến trình sau khi nạp mô hình dự đoán. Render free chỉ có 512MB nên cảnh báo nếu vượt 300MB.

Chạy:  python scripts/measure_memory.py          (đo: chỉ predict.py, rồi cả server.main)
Cần psutil (chỉ để đo, không có trong requirements-server.txt):  pip install psutil
"""
import subprocess
import sys

import _boot  # noqa: F401
import psutil

NGUONG_MB = 300


def rss_mb() -> float:
    return psutil.Process().memory_info().rss / 1024 / 1024


def do_mot_kich_ban(ten: str) -> None:
    """Chạy TRONG tiến trình con để các kịch bản không ảnh hưởng nhau."""
    truoc = rss_mb()
    if ten == "server":
        sys.path.insert(0, str(_boot.Path(__file__).resolve().parents[1]))
        import server.main  # noqa: F401  (kéo theo fastapi, pymongo, pandas...)
    from sparkmind import predict
    sau_import = rss_mb()
    predict.du_doan({f"B4_{i}": 3 for i in range(1, 8)})        # lần gọi đầu mới nạp mô hình (lazy)
    print(f"{ten}|{truoc:.0f}|{sau_import:.0f}|{rss_mb():.0f}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        do_mot_kich_ban(sys.argv[1])
        sys.exit()
    for ten in ("predict", "server"):
        out = subprocess.run([sys.executable, "-W", "ignore", __file__, ten], capture_output=True, text=True).stdout.strip().splitlines()[-1]
        k, a, b, c = out.split("|")
        print(f"[{k}] bắt đầu {a}MB -> sau import {b}MB -> sau nạp mô hình và dự đoán {c}MB (RSS)")
        if float(c) > NGUONG_MB:
            print(f"  CẢNH BÁO: vượt {NGUONG_MB}MB (Render free chỉ có 512MB)")
