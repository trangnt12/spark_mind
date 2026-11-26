"""Rút mẫu để 2 người chấm chấm (game 1 và game 3). Cùng hàm với nút "Rút mẫu" ở trang quản trị.

  python scripts/make_rating_sample.py --label thu --batch pilot_28_11 --n-game1 30 --n-game3 20 --seed 1            # chỉ XEM (mặc định)
  python scripts/make_rating_sample.py --label thu --batch pilot_28_11 --n-game1 30 --n-game3 20 --seed 1 --apply    # ghi thật

Cùng seed và cùng dữ liệu thì ra đúng cùng mẫu. Không rút lại mục đã có trong cùng đợt. Không in chuỗi kết nối MongoDB.
"""
import argparse
import sys

import _boot  # noqa: F401  (cho phép import sparkmind)
from sparkmind import rating_sample, rating_store
from sparkmind.db import lay_db
from sparkmind.research_store import LoiNghiepVu

NGUOI_SCRIPT = {"username": "script:make_rating_sample", "role": "script"}   # để audit_log biết việc làm từ script


def doc_tham_so(argv=None):
    p = argparse.ArgumentParser(description="Rút mẫu chấm điểm")
    p.add_argument("--label", required=True, choices=["thu", "pilot", "that"], help="nhãn dữ liệu cần rút")
    p.add_argument("--batch", required=True, help="tên đợt chấm, ví dụ pilot_28_11")
    p.add_argument("--n-game1", type=int, default=0, help="số ý game 1")
    p.add_argument("--n-game3", type=int, default=0, help="số bài game 3 (chia đều hai tình huống)")
    p.add_argument("--seed", type=int, required=True, help="số cố định để lặp lại đúng mẫu")
    p.add_argument("--dry-run", action="store_true", help="chỉ xem, không ghi (mặc định)")
    p.add_argument("--apply", action="store_true", help="ghi thật")
    return p.parse_args(argv)


def main(argv=None) -> None:
    a = doc_tham_so(argv)
    if a.apply and a.dry_run:
        sys.exit("Chỉ chọn một trong --dry-run và --apply.")
    db = lay_db()
    if a.apply:
        rating_store.tao_chi_muc_cham(db)
    try:
        kq = rating_sample.rut_mau(db, a.label, a.batch, a.n_game1, a.n_game3, a.seed, dry_run=not a.apply, user=NGUOI_SCRIPT)
    except LoiNghiepVu as e:
        sys.exit(f"Không rút được: {e.noi_dung}")
    print(f"{'DRY-RUN (chưa ghi gì)' if kq['dry_run'] else 'ĐÃ GHI'}: đợt {a.batch}, nhãn {a.label}, seed {a.seed}")
    print(f"  game 1: {kq['da_rut'][1]} ý (thiếu {kq['thieu'][1]}); game 3: {kq['da_rut'][3]} bài (thiếu {kq['thieu'][3]}); tổng {kq['tong']}")


if __name__ == "__main__":
    main()
