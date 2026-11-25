"""Sao lưu MongoDB ra backups/<ngày_giờ>/ (mỗi collection một file .jsonl.gz + manifest.json).

  python scripts/backup_mongo.py            # sao lưu, giữ 14 bản mới nhất
  python scripts/backup_mongo.py --keep 30  # giữ 30 bản

Chỉ ĐỌC từ Atlas. Không sao lưu admin_sessions và login_attempts. Không in chuỗi kết nối.
backups/ chứa dữ liệu thật (có email, băm mật khẩu): đã nằm trong .gitignore, không bao giờ commit hay chia sẻ.
"""
import argparse

import _boot  # noqa: F401  (cho phép import sparkmind)
from sparkmind import backup, config
from sparkmind.db import lay_db


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Sao lưu MongoDB (chỉ đọc)")
    p.add_argument("--keep", type=int, default=14, help="số bản sao lưu giữ lại trong backups/ (mặc định 14)")
    a = p.parse_args(argv)
    db = lay_db()
    thu_muc = backup.sao_luu(db)
    mf = backup.doc_manifest(thu_muc)
    print(f"Database: {config.MONGODB_DB}. Đã sao lưu vào {thu_muc}")
    for ten, m in mf["collections"].items():
        print(f"  {ten:<22}{m['so_ban_ghi']:>8}")
    for ten in backup.don_ban_cu(backup.THU_MUC_SAO_LUU, a.keep):
        print(f"Đã xóa bản cũ: {ten}")


if __name__ == "__main__":
    main()
