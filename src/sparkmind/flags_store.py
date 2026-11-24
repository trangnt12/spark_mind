"""Đọc dữ liệu đã lưu của một người, tính cờ (flags.py) rồi ghi participants.flags và flag_count.

Tính lại TOÀN BỘ từ dữ liệu đã lưu mỗi lần nên chạy lại bao nhiêu lần cũng cho cùng kết quả.
Chỉ ghi hai trường flags và flag_count của participants; không đụng gì khác, không xóa gì.
"""
import logging

from . import flags
from .game_store import COL_GAME
from .research_store import COL_HANH_VI, COL_NGUOI, COL_TU_DANH_GIA

log = logging.getLogger("sparkmind.flags")


def tinh_cho_nguoi(db, participant_id) -> list:
    """Danh sách cờ của một người, tính từ behavior_answers, self_assessment và game_responses."""
    hanh_vi = db[COL_HANH_VI].find_one({"participant_id": participant_id})
    tu_danh_gia = db[COL_TU_DANH_GIA].find_one({"participant_id": participant_id})
    da_nop = db[COL_GAME].find({"participant_id": participant_id, "game": {"$in": [1, 2]}, "submitted_at": {"$ne": None}})
    game = {b["game"]: b for b in da_nop}   # chỉ game đã nộp
    return flags.tinh_co(hanh_vi, tu_danh_gia, game)


def cap_nhat_co(db, participant_id) -> dict:
    """Tính và ghi flags, flag_count cho một người. Trả {"flags": [...], "flag_count": n}."""
    cac_co = tinh_cho_nguoi(db, participant_id)
    ket_qua = {"flags": cac_co, "flag_count": flags.dem_co(cac_co)}
    db[COL_NGUOI].update_one({"_id": participant_id}, {"$set": ket_qua})
    return ket_qua


def cap_nhat_co_theo_token(db, session_token: str) -> None:
    """Dùng ngay sau khi người chơi nộp một bước. Lỗi tính cờ KHÔNG được làm hỏng việc nộp bài, nên chỉ ghi log (không ghi dữ liệu cá nhân)."""
    try:
        nguoi = db[COL_NGUOI].find_one({"session_token": session_token}, {"_id": 1})
        if nguoi:
            cap_nhat_co(db, nguoi["_id"])
    except Exception as loi:  # noqa: BLE001 - cờ chỉ là phụ, không được chặn người chơi
        log.warning("Không tính được cờ: %s", type(loi).__name__)


def tinh_lai_tat_ca(db, loc: dict | None = None, ap_dung: bool = True) -> dict:
    """Tính lại cờ cho mọi người tham gia (có thể lọc, ví dụ theo data_label). ap_dung=False: chỉ đếm, không ghi gì.

    Trả {"tong", "doi", "theo_co": {cờ: số người}, "co_it_nhat_mot": số người có flag_count > 0}.
    "doi" = số người có kết quả khác giá trị đang lưu (chạy lại lần hai thì phải bằng 0).
    """
    kq = {"tong": 0, "doi": 0, "theo_co": {}, "co_it_nhat_mot": 0}
    for nguoi in db[COL_NGUOI].find(loc or {}, {"flags": 1, "flag_count": 1}):
        moi = tinh_cho_nguoi(db, nguoi["_id"])
        dem = flags.dem_co(moi)
        kq["tong"] += 1
        kq["co_it_nhat_mot"] += dem > 0
        for co in moi:
            kq["theo_co"][co] = kq["theo_co"].get(co, 0) + 1
        if nguoi.get("flags") != moi or nguoi.get("flag_count") != dem:
            kq["doi"] += 1
            if ap_dung:
                db[COL_NGUOI].update_one({"_id": nguoi["_id"]}, {"$set": {"flags": moi, "flag_count": dem}})
    return kq
