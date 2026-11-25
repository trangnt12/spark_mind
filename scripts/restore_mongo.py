"""Khôi phục một bản sao lưu vào MỘT DATABASE MỚI (không bao giờ vào database đang dùng).

  python scripts/restore_mongo.py backups/20261128_090000 --into spark-mind-restore-test            # chỉ xem (dry-run)
  python scripts/restore_mongo.py backups/20261128_090000 --into spark-mind-restore-test --apply    # ghi thật, gõ KHOI PHUC

Database đích phải rỗng hoặc chưa tồn tại. Không có lệnh drop nào. Không in chuỗi kết nối.
"""
import argparse
import sys
from pathlib import Path

import _boot  # noqa: F401  (cho phép import sparkmind)
from sparkmind import backup, config

XAC_NHAN = "KHOI PHUC"


def in_so_sanh(kq: dict) -> bool:
    """In số bản ghi manifest so với đã ghi. Trả True nếu mọi collection khớp."""
    khop = True
    for ten, (mf, thuc) in kq.items():
        ok = mf == thuc
        khop = khop and ok
        print(f"  {ten:<22}manifest {mf:>7}  đã ghi {thuc:>7}  {'khớp' if ok else 'KHÔNG KHỚP'}")
    return khop


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Khôi phục sao lưu vào database mới")
    p.add_argument("thu_muc", help="thư mục sao lưu, ví dụ backups/20261128_090000")
    p.add_argument("--into", required=True, help="tên database MỚI (không được trùng database đang dùng)")
    p.add_argument("--dry-run", action="store_true", help="chỉ in số bản ghi (mặc định)")
    p.add_argument("--apply", action="store_true", help="ghi thật (cần gõ xác nhận)")
    a = p.parse_args(argv)
    if a.apply and a.dry_run:
        sys.exit("Chỉ chọn một trong --dry-run và --apply.")
    mf = backup.doc_manifest(Path(a.thu_muc))
    print(f"Sao lưu của database '{mf['database']}' lúc {mf['thoi_diem']}; sẽ khôi phục vào '{a.into}':")
    for ten, m in mf["collections"].items():
        print(f"  {ten:<22}{m['so_ban_ghi']:>8}")
    if not a.apply:
        print("\nDRY-RUN: chưa ghi gì.")
        return
    from pymongo import MongoClient
    client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=8000)
    try:
        backup.kiem_tra_dich(client, a.into, mf["database"])
    except ValueError as e:
        sys.exit(str(e))
    if input(f"\nSẽ ghi vào database mới '{a.into}'. Gõ {XAC_NHAN} để xác nhận: ").strip() != XAC_NHAN:
        sys.exit("Đã hủy, chưa ghi gì.")
    print("Kết quả so với manifest:")
    sys.exit(0 if in_so_sanh(backup.khoi_phuc(client, Path(a.thu_muc), a.into)) else 1)


if __name__ == "__main__":
    main()
