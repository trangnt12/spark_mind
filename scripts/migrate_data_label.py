"""Gán nhãn dữ liệu (data_label) cho bản ghi cũ chưa có nhãn. Chạy lại nhiều lần vẫn an toàn (idempotent).

Quy tắc: hướng 2 (access_codes, participants, behavior_answers, self_assessment, game_responses, scores) -> "thu";
survey_clean -> "that". survey_form1 không bao giờ bị đụng tới.

  python scripts/migrate_data_label.py              # mặc định chỉ XEM (dry-run): đếm số bản ghi sẽ gán, không ghi gì
  python scripts/migrate_data_label.py --dry-run    # giống trên (viết rõ cho dễ hiểu)
  python scripts/migrate_data_label.py --apply      # ghi thật, phải gõ GAN NHAN để xác nhận

Không in chuỗi kết nối MongoDB.
"""
import argparse
import sys

import _boot  # noqa: F401  (cho phép import sparkmind)
from sparkmind import config, data_label
from sparkmind.db import lay_db

XAC_NHAN = "GAN NHAN"


def in_ke_hoach(kh: dict) -> int:
    """In bảng kế hoạch, trả tổng số bản ghi sẽ được gán nhãn."""
    print(f"Database: {config.MONGODB_DB}")
    print(f"{'bảng':<20}{'nhãn gán':<10}{'sẽ gán':>8}{'tổng':>8}")
    for bang, m in kh.items():
        print(f"{bang:<20}{m['gan']:<10}{m['se_gan']:>8}{m['tong']:>8}")
    return sum(m["se_gan"] for m in kh.values())


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Gán data_label cho bản ghi cũ")
    p.add_argument("--dry-run", action="store_true", help="chỉ đếm, không ghi (mặc định)")
    p.add_argument("--apply", action="store_true", help="ghi thật (cần gõ xác nhận)")
    a = p.parse_args(argv)
    if a.apply and a.dry_run:
        sys.exit("Chỉ chọn một trong --dry-run và --apply.")
    db = lay_db()
    tong = in_ke_hoach(data_label.ke_hoach(db))
    if not a.apply:
        print(f"\nDRY-RUN: chưa ghi gì. Sẽ gán nhãn cho {tong} bản ghi.")
        return
    if input(f"\nSẽ ghi nhãn cho {tong} bản ghi. Gõ {XAC_NHAN} để xác nhận: ").strip() != XAC_NHAN:
        sys.exit("Đã hủy, chưa ghi gì.")
    for bang, n in data_label.ap_dung(db).items():
        print(f"  {bang}: đã gán {n}")


if __name__ == "__main__":
    main()
