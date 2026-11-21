"""Cho biết số mã tham gia theo nguồn: tổng, đã dùng, chưa dùng.

Ví dụ:  python scripts/list_codes.py
Không in mã và không in chuỗi kết nối MongoDB.
"""
import _boot  # noqa: F401  (cho phép import sparkmind)
from sparkmind.db import lay_db
from sparkmind.research_store import COL_MA, NGUON_HOP_LE


def dem_ma(db) -> dict:
    """Trả {nguồn: {"tong", "da_dung", "chua_dung"}} cho mọi nguồn hợp lệ."""
    ket_qua = {n: {"tong": 0, "da_dung": 0, "chua_dung": 0} for n in NGUON_HOP_LE}
    for d in db[COL_MA].find({}, {"source": 1, "is_used": 1}):
        m = ket_qua.setdefault(d.get("source", "khac"), {"tong": 0, "da_dung": 0, "chua_dung": 0})
        m["tong"] += 1
        m["da_dung" if d.get("is_used") else "chua_dung"] += 1
    return ket_qua


def main() -> None:
    print(f"{'nguon':<12}{'tong':>6}{'da dung':>9}{'chua dung':>11}")
    for nguon, m in dem_ma(lay_db()).items():
        print(f"{nguon:<12}{m['tong']:>6}{m['da_dung']:>9}{m['chua_dung']:>11}")


if __name__ == "__main__":
    main()
