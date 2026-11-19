"""Xuất bảng tên trường cần người duyệt: content/school_review.csv.

Cách dùng:
    python scripts/export_school_review.py                # đọc từ MongoDB
    python scripts/export_school_review.py --tu-excel     # đọc từ Excel (thử)
Mở file kết quả bằng Excel, điền cột truong_chuan và truong_tinh, rồi lưu thành
content/school_overrides.csv (định dạng CSV UTF-8). Chạy lại run_cleaning.py để áp dụng.
"""
import argparse

import _boot  # noqa: F401
from sparkmind import config
from sparkmind.cleaning import clean
from sparkmind.db import lay_db
from sparkmind.loaders import doc_excel, doc_goc_mongo
from sparkmind.school_matching import bang_can_duyet


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tu-excel", action="store_true")
    a = p.parse_args()
    raw = doc_excel() if a.tu_excel else doc_goc_mongo(lay_db())
    b = bang_can_duyet(clean(raw))
    out = config.ROOT / "content" / "school_review.csv"
    out.parent.mkdir(exist_ok=True)
    b.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"{len(b)} nhóm tên trường. Đã ghi {out}")


if __name__ == "__main__":
    main()
