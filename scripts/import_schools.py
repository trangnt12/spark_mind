"""Nhập danh sách trường (Excel: STT, Tên trường, Tên viết tắt, Cấp) vào content/schools.csv và MongoDB.

Cách dùng:
    python scripts/import_schools.py --file duong_dan/Danh_sach_truong.xlsx
    python scripts/import_schools.py --file ... --khong-mongo     # chỉ tạo CSV, chưa ghi MongoDB
"""
import argparse
from pathlib import Path

import _boot  # noqa: F401
import pandas as pd
from sparkmind import config
from sparkmind.db import df_sang_docs, ghi_nhieu, lay_db
from sparkmind.school_matching import FILE_DS, chuan_hoa_ds


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--file", type=Path, required=True)
    p.add_argument("--khong-mongo", action="store_true")
    a = p.parse_args()

    d = chuan_hoa_ds(pd.read_excel(a.file, sheet_name=0))
    d["viet_tat"] = d["viet_tat"].fillna("").astype(str).str.strip()
    print(f"Đọc được {len(d)} trường:\n{d['cap_chuan'].value_counts().to_string()}")
    FILE_DS.parent.mkdir(exist_ok=True)
    d[["id", "ten", "viet_tat", "cap", "cap_chuan", "khoa", "key"]].to_csv(FILE_DS, index=False, encoding="utf-8-sig")
    print(f"Đã ghi {FILE_DS}")
    if a.khong_mongo:
        return
    docs = [{"_id": r["id"], "name": r["ten"], "abbreviation": r["viet_tat"], "level": r["cap_chuan"],
             "name_key": r["khoa"], "key": r["key"]} for r in d.to_dict("records")]
    n = ghi_nhieu(lay_db()["schools"], docs)
    print(f"Đã ghi {n} trường vào {config.MONGODB_DB}.schools")


if __name__ == "__main__":
    main()
