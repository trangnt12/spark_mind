"""Tạo mã tham gia cho chế độ nghiên cứu và in danh sách mã ra màn hình.

Ví dụ:  python scripts/make_codes.py --n 5 --source volunteer
Chỉ in các mã, KHÔNG in chuỗi kết nối MongoDB.
"""
import argparse

import _boot  # noqa: F401  (cho phép import sparkmind)
from sparkmind.db import lay_db
from sparkmind.research_store import NGUON_HOP_LE, tao_chi_muc, tao_ma_moi


def doc_tham_so() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tạo mã tham gia ngẫu nhiên 8 ký tự")
    p.add_argument("--n", type=int, required=True, help="số mã cần tạo")
    p.add_argument("--source", choices=NGUON_HOP_LE, required=True, help="nguồn người tham gia")
    return p.parse_args()


def main() -> None:
    tham_so = doc_tham_so()
    db = lay_db()
    tao_chi_muc(db)  # bảo đảm mã không trùng (code unique)
    for ma in tao_ma_moi(db, tham_so.n, tham_so.source):
        print(ma)


if __name__ == "__main__":
    main()
