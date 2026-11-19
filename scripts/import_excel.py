"""Nhập file Excel khảo sát (Google Form) vào MongoDB, collection survey_form1.

Chạy lại nhiều lần vẫn an toàn: form đã có thì được thay, không bị nhân đôi.
Cách dùng:
    python scripts/import_excel.py                # dùng data/raw/data_raw.xlsx
    python scripts/import_excel.py --file duong_dan.xlsx
    python scripts/import_excel.py --dry-run      # chỉ đếm, không ghi
"""
import argparse
from pathlib import Path

import _boot  # noqa: F401
from sparkmind import config
from sparkmind.db import df_sang_docs, ghi_nhieu, lay_db
from sparkmind.loaders import doc_excel


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--file", type=Path, default=config.RAW_EXCEL)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    df = doc_excel(a.file)
    print(f"Đọc được {len(df)} form, {df['_id'].nunique()} mã khác nhau.")
    if df["_id"].duplicated().any():
        print("CẢNH BÁO: có form trùng hệt nhau, chỉ giữ một bản mỗi form.")
        df = df.drop_duplicates("_id")
    if a.dry_run:
        print("Chế độ thử: chưa ghi gì vào MongoDB.")
        return
    db = lay_db()
    n = ghi_nhieu(db[config.COL_RAW], df_sang_docs(df))
    print(f"Đã ghi {n} form vào {config.MONGODB_DB}.{config.COL_RAW}. "
          f"Tổng hiện có: {db[config.COL_RAW].count_documents({})}")


if __name__ == "__main__":
    main()
