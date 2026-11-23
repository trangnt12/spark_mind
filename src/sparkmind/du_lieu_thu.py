"""Dọn dữ liệu thử: xóa các bản ghi có data_label "thu" hoặc "pilot". KHÔNG BAO GIỜ đụng nhãn "that" (hay bản ghi chưa có nhãn).

Chỉ xóa ở các bảng có nhãn: access_codes, participants, các bảng con hướng 2, scores, survey_clean.
survey_form1 (dữ liệu gốc) không nằm trong danh sách nên không bao giờ bị xóa.
"""
from . import config
from .audit import write_audit
from .data_label import BANG_CO_NHAN

TU_XAC_NHAN = "XOA"


def bo_loc_thu() -> dict:
    """Bộ lọc duy nhất được dùng để xóa: nhãn nằm trong NHAN_DU_LIEU_THU. Có kiểm tra phòng hờ: không chứa "that"."""
    nhan = list(config.NHAN_DU_LIEU_THU)
    assert config.NHAN_MAC_DINH not in nhan, "NHAN_DU_LIEU_THU không được chứa nhãn mặc định (that)"
    return {"data_label": {"$in": nhan}}


def xem_truoc(db) -> dict:
    """Dry-run: số bản ghi SẼ bị xóa theo từng bảng. Không xóa gì."""
    loc = bo_loc_thu()
    return {b: db[b].count_documents(loc) for b in BANG_CO_NHAN}


def xoa(db, user: dict, xac_nhan: str) -> dict:
    """Xóa thật. Phải gõ đúng "XOA". Trả {bảng: số đã xóa}; mỗi bảng có đã xóa bản ghi thì ghi một dòng audit_log."""
    if xac_nhan != TU_XAC_NHAN:
        raise ValueError("xac_nhan_sai")
    loc, kq = bo_loc_thu(), {}
    for b in BANG_CO_NHAN:
        kq[b] = db[b].delete_many(loc).deleted_count
        if kq[b]:
            write_audit(db, user, "test_data_delete", b, None, {"so_ban_ghi": kq[b], "nhan": list(config.NHAN_DU_LIEU_THU)})
    if not any(kq.values()):   # không có gì để xóa vẫn để lại dấu vết là đã có người chạy
        write_audit(db, user, "test_data_delete", None, None, {"so_ban_ghi": 0})
    return kq
