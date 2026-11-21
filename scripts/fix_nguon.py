"""Sửa nhãn nguồn: form nhập từ Excel (trước 20/11/2026) đang ghi nguon="google_form",
đổi thành nguon="excel_import" ở cả survey_form1 và survey_clean.

Chỉ đổi đúng trường nguon. Không đổi _id, không sửa nội dung trả lời.
Chạy lại an toàn: form đã đổi rồi thì không còn khớp điều kiện nên không bị đổi lần nữa.
Cách dùng:
    python scripts/fix_nguon.py --dry-run   # chỉ đếm, chưa ghi gì
    python scripts/fix_nguon.py             # đổi thật
"""
import argparse
from datetime import datetime

import _boot  # noqa: F401
from sparkmind import config
from sparkmind.db import lay_db

NGAY_MOC = datetime(2026, 11, 20)   # từ ngày này form tự đổ qua Apps Script, giữ "google_form"
NGUON_CU = "google_form"
NGUON_MOI = "excel_import"


def doi_nguon(db, dry_run: bool = False) -> dict:
    """Đổi nguon ở hai collection. Trả về {tên collection: số form được đổi (hoặc sẽ đổi)}."""
    loc = {"nguon": NGUON_CU, "thoi_gian": {"$lt": NGAY_MOC}}
    ket_qua = {}
    for ten in (config.COL_RAW, config.COL_CLEAN):
        if dry_run:
            ket_qua[ten] = db[ten].count_documents(loc)
        else:
            ket_qua[ten] = db[ten].update_many(loc, {"$set": {"nguon": NGUON_MOI}}).modified_count
    return ket_qua


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="chỉ đếm, không ghi")
    a = p.parse_args()

    ket_qua = doi_nguon(lay_db(), a.dry_run)
    dong = "Chế độ thử (chưa ghi gì). Sẽ đổi" if a.dry_run else "Đã đổi"
    for ten, n in ket_qua.items():
        print(f"{dong} {n} form ở {config.MONGODB_DB}.{ten}: {NGUON_CU} -> {NGUON_MOI}")


if __name__ == "__main__":
    main()
