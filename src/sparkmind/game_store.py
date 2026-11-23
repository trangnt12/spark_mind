"""Đọc/ghi MongoDB cho game 1 (hướng 2). Cấu trúc theo docs/erd.dbml (bảng game_responses).

Ở bước này chỉ LƯU bài làm, chưa chấm điểm.
"""
import hashlib
from datetime import datetime

from pymongo.errors import DuplicateKeyError

from sparkmind import config, research_store as kho

COL_GAME = "game_responses"
SO_Y_TOI_DA = 50
KY_TU_MOI_Y_TOI_DA = 120
GIAY_CHO_PHEP_TRE = 15  # nộp trễ quá số giây này vẫn nhận nhưng ghi cờ over_time


def bay_gio() -> datetime:
    """Giờ hiện tại làm tròn xuống mili giây (MongoDB chỉ lưu đến mili giây, nên lần đầu và lần sau khớp nhau)."""
    t = datetime.now()
    return t.replace(microsecond=t.microsecond // 1000 * 1000)


def tao_chi_muc_game(db) -> None:
    """Mỗi người chỉ có một bài cho mỗi game."""
    db[COL_GAME].create_index([("participant_id", 1), ("game", 1)], unique=True)


def chon_do_vat(ma: str, do_vat: list) -> dict:
    """Băm mã tham gia rồi chia theo số đồ vật: cùng mã luôn ra cùng đồ vật, các đồ vật chia đều."""
    so = int(hashlib.sha256(kho.chuan_hoa_ma(ma).encode("utf-8")).hexdigest(), 16)
    return do_vat[so % len(do_vat)]


def lam_sach_y(ideas: list) -> list:
    """Cắt khoảng trắng, bỏ ý rỗng, mỗi ý tối đa 120 ký tự, tối đa 50 ý."""
    sach = [" ".join(y.split())[:KY_TU_MOI_Y_TOI_DA].strip() for y in ideas]
    return [y for y in sach if y][:SO_Y_TOI_DA]


def _ma_cua_nguoi(db, nguoi: dict) -> str:
    """Lấy mã tham gia của người này (participants chỉ lưu code_id)."""
    return db[kho.COL_MA].find_one({"_id": nguoi["code_id"]})["code"]


def _tim_bai(db, nguoi: dict):
    return db[COL_GAME].find_one({"participant_id": nguoi["_id"], "game": 1})


def _tao_bai(db, nguoi: dict, do_vat: dict) -> dict:
    """Ghi bài mới với started_at do SERVER đặt. Hai yêu cầu cùng lúc thì lấy bài đã có."""
    bai = {"participant_id": nguoi["_id"], "game": 1, "data_label": nguoi.get("data_label", config.NHAN_MAC_DINH), "prompt_id": do_vat["id"],
           "started_at": bay_gio(), "submitted_at": None}
    try:
        db[COL_GAME].insert_one(bai)
    except DuplicateKeyError:
        return _tim_bai(db, nguoi)
    return bai


def con_lai(bai: dict, gioi_han: int) -> int:
    """Số giây còn lại, tính từ started_at của server (không bao giờ âm)."""
    da_troi = (bay_gio() - bai["started_at"]).total_seconds()
    return max(0, int(gioi_han - da_troi))


def bat_dau_game1(db, session_token: str, noi_dung: dict) -> dict:
    """Bắt đầu game 1; gọi lại thì trả cùng đồ vật và cùng started_at."""
    nguoi = kho.tim_nguoi(db, session_token)
    bai = _tim_bai(db, nguoi)
    if not bai:
        do_vat = chon_do_vat(_ma_cua_nguoi(db, nguoi), noi_dung["do_vat"])
        bai = _tao_bai(db, nguoi, do_vat)
    gioi_han = noi_dung["thoi_gian_giay"]
    do_vat = next(d for d in noi_dung["do_vat"] if d["id"] == bai["prompt_id"])
    kq = {"do_vat": do_vat, "time_limit_sec": gioi_han, "remaining_sec": con_lai(bai, gioi_han),
          "started_at": bai["started_at"].isoformat(), "submitted": bai["submitted_at"] is not None}
    if kq["submitted"]:
        kq["ideas"] = bai["answer"]["ideas"]   # trả lại các ý đã nộp để người chơi xem lại (chỉ của chính họ)
    return kq


def nop_game1(db, session_token: str, d: dict, gioi_han: int) -> dict:
    """Nộp game 1: làm sạch ý, server tự tính thời gian, mỗi người chỉ nộp một lần. Không chấm điểm."""
    nguoi = kho.tim_nguoi(db, session_token)
    bai = _tim_bai(db, nguoi)
    if not bai:
        raise kho.LoiNghiepVu(409, "Bạn chưa bắt đầu game 1.")
    y = lam_sach_y(d["ideas"])
    luc_nop = bay_gio()
    giay = (luc_nop - bai["started_at"]).total_seconds()
    gia_tri = {"answer": {"ideas": y, "n_ideas": len(y)}, "answer_length": sum(len(i) for i in y),
               "duration_sec": round(giay), "over_time": giay > gioi_han + GIAY_CHO_PHEP_TRE,
               "paste_count": d["paste_count"], "tab_leave_count": d["tab_leave_count"],
               "submitted_at": luc_nop}
    # Điều kiện submitted_at=None làm việc "chỉ một lần" an toàn kể cả khi bấm nộp hai lần cùng lúc
    kq = db[COL_GAME].update_one({"_id": bai["_id"], "submitted_at": None}, {"$set": gia_tri})
    if kq.modified_count != 1:
        raise kho.LoiNghiepVu(409, "Bạn đã nộp game 1 rồi.")
    kiem_tra_hoan_thanh(db, nguoi)
    return {"ok": True, "n_ideas": len(y)}


def kiem_tra_hoan_thanh(db, nguoi: dict) -> bool:
    """Đủ mọi game trong config.GAME_BAT_BUOC đã nộp thì gán participants.completed_at (một lần, không ghi đè)."""
    da_nop = {b["game"] for b in db[COL_GAME].find({"participant_id": nguoi["_id"], "submitted_at": {"$ne": None}})}
    if not set(config.GAME_BAT_BUOC) <= da_nop:
        return False
    # Điều kiện completed_at=None: lần sau (hoặc hai yêu cầu cùng lúc) không ghi đè giờ đã có
    db[kho.COL_NGUOI].update_one({"_id": nguoi["_id"], "completed_at": None}, {"$set": {"completed_at": bay_gio()}})
    return True
