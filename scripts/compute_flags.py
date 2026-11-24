"""Tính lại cờ chống gian lận (participants.flags và flag_count) cho mọi người tham gia hướng 2.

Chạy lại khi đổi ngưỡng trong src/sparkmind/config.py (các hằng CO_*). An toàn khi chạy nhiều lần (idempotent):
lần thứ hai không đổi gì. CHỈ GẮN CỜ: chỉ ghi hai trường flags và flag_count của participants, không xóa gì,
không đụng survey_form1 hay bất kỳ bảng nào khác.

Ví dụ:
  python scripts/compute_flags.py --dry-run                  # chỉ xem sẽ đổi gì, không ghi
  python scripts/compute_flags.py --data-label thu --dry-run  # chỉ người có nhãn thu
  python scripts/compute_flags.py                              # ghi thật
Không in email, IP hay chuỗi kết nối MongoDB: chỉ in số đếm.
"""
import argparse
import sys

import _boot  # noqa: F401  (cho phép import sparkmind)
from sparkmind import config
from sparkmind.db import lay_db
from sparkmind.flags_store import tinh_lai_tat_ca


def doc_tham_so(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tính lại cờ chống gian lận cho mọi người tham gia")
    p.add_argument("--dry-run", action="store_true", help="chỉ xem kết quả, không ghi gì vào MongoDB")
    p.add_argument("--data-label", choices=config.NHAN_HOP_LE, default=None,
                   help="chỉ tính cho người có nhãn này (mặc định: tất cả; người thiếu nhãn coi là that)")
    return p.parse_args(argv)


def bo_loc(nhan: str | None) -> dict:
    """Bộ lọc participants theo nhãn dữ liệu (thiếu nhãn được coi là that)."""
    if not nhan:
        return {}
    if nhan == config.NHAN_MAC_DINH:
        return {"$or": [{"data_label": nhan}, {"data_label": {"$exists": False}}, {"data_label": None}]}
    return {"data_label": nhan}


def in_ket_qua(kq: dict, ghi: bool) -> None:
    print(f"Người tham gia đã xét: {kq['tong']}")
    print(f"Có ít nhất một cờ (không tính bi_gian_doan): {kq['co_it_nhat_mot']}")
    for co, n in sorted(kq["theo_co"].items()):
        print(f"  {co}: {n}")
    print(f"Số người có kết quả khác giá trị đang lưu: {kq['doi']} -> " + ("ĐÃ GHI" if ghi else "chưa ghi (--dry-run)"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")   # Windows có thể mặc định bảng mã không có tiếng Việt
    tham_so = doc_tham_so()
    kq = tinh_lai_tat_ca(lay_db(), bo_loc(tham_so.data_label), ap_dung=not tham_so.dry_run)
    in_ket_qua(kq, ghi=not tham_so.dry_run)


if __name__ == "__main__":
    main()
