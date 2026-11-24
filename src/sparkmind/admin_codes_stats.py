"""Thống kê mã tham gia theo lô (access_codes.batch): tổng, đã dùng, đã hoàn thành. Chỉ số đếm, không trả mã hay email."""
from .admin_stats import loc_an_thu
from .research_store import COL_MA, COL_NGUOI


def thong_ke_lo(db, an_thu: bool = True) -> list:
    """[{"batch", "tong", "da_dung", "chua_dung", "hoan_thanh", "nhan"}] mỗi lô (và mỗi nhãn dữ liệu) một dòng, lô lớn trước.

    Mã chưa có lô (tạo trước ngày 24/11) gom vào batch = None. "hoan_thanh" = số người đã có completed_at.
    """
    ma = list(db[COL_MA].find(loc_an_thu(an_thu), {"batch": 1, "is_used": 1, "data_label": 1}))
    xong = {n["code_id"] for n in db[COL_NGUOI].find({"completed_at": {"$ne": None}}, {"code_id": 1})}
    dong = {}
    for m in ma:
        khoa = (m.get("batch"), m.get("data_label") or "that")   # thiếu nhãn được coi là that
        d = dong.setdefault(khoa, {"batch": khoa[0], "nhan": khoa[1], "tong": 0, "da_dung": 0, "hoan_thanh": 0})
        d["tong"] += 1
        d["da_dung"] += bool(m.get("is_used"))
        d["hoan_thanh"] += m["_id"] in xong
    kq = [{**d, "chua_dung": d["tong"] - d["da_dung"]} for d in dong.values()]
    return sorted(kq, key=lambda d: (-d["tong"], d["batch"] or ""))
