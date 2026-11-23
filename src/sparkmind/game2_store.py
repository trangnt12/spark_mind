"""Đọc/ghi MongoDB cho game 2 (Soi lỗi AI). Cấu trúc theo docs/erd.dbml (bảng game_responses, game = 2).

Đáp án (la_loi, loai_loi, giai_thich) chỉ rời server SAU khi đã nộp.
"""
from pymongo.errors import DuplicateKeyError

from sparkmind import config, game_store as gs, research_store as kho
from sparkmind.score_game2 import cham_game2

GAME = 2


def y_cho_trinh_duyet(noi_dung: dict) -> list:
    """Chỉ id và văn bản, theo đúng thứ tự cố định trong content. KHÔNG có đáp án."""
    return [{"id": i["id"], "van_ban": i["van_ban"]} for i in noi_dung["y"]]


def ket_qua_tung_y(noi_dung: dict, da_chon: list) -> list:
    """Sau khi nộp: từng ý kèm đúng/sai, giải thích, ý có được chọn không và nhan_dinh_dung
    (nhận định của người chơi đúng: chọn ý sai, hoặc không chọn ý đúng) và diem của riêng ý đó
    (+1 chọn đúng ý sai, -1 chọn nhầm ý đúng, 0 còn lại). Không có loai_loi."""
    chon = set(da_chon)
    return [{"id": i["id"], "van_ban": i["van_ban"], "la_loi": i["la_loi"], "giai_thich": i["giai_thich"],
             "da_chon": i["id"] in chon, "nhan_dinh_dung": (i["id"] in chon) == i["la_loi"],
             "diem": (i["id"] in chon) * (1 if i["la_loi"] else -1)} for i in noi_dung["y"]]


def _tim_bai(db, nguoi: dict):
    return db[gs.COL_GAME].find_one({"participant_id": nguoi["_id"], "game": GAME})


def _tao_bai(db, nguoi: dict) -> dict:
    """Ghi bài mới với started_at do SERVER đặt (gọi lại thì trả bài cũ)."""
    bai = {"participant_id": nguoi["_id"], "game": GAME, "data_label": nguoi.get("data_label", config.NHAN_MAC_DINH),
           "prompt_id": "game2", "started_at": gs.bay_gio(), "submitted_at": None}
    try:
        db[gs.COL_GAME].insert_one(bai)
    except DuplicateKeyError:
        return _tim_bai(db, nguoi)
    return bai


def _dang_tra_ve(noi_dung: dict, bai: dict) -> dict:
    """Bài đã nộp thì kèm kết quả từng ý (để tải lại trang vẫn thấy); chưa nộp thì chỉ có đề."""
    xong = bai["submitted_at"] is not None
    kq = {"ten": noi_dung["ten"], "tinh_huong": noi_dung["tinh_huong"], "y": y_cho_trinh_duyet(noi_dung), "submitted": xong}
    if xong:
        a = bai["answer"]
        kq["ket_qua"] = ket_qua_tung_y(noi_dung, a["selected_ids"])
        kq["diem"] = a["score"]   # điểm tổng (0-5, đã chặn sàn 0) và hai số đếm, chỉ trả sau khi nộp
        kq["n_correct"], kq["n_wrong"] = a["n_correct"], a["n_wrong"]
    return kq


def bat_dau_game2(db, session_token: str, noi_dung: dict) -> dict:
    """Bắt đầu game 2; gọi lại thì trả cùng started_at, không tạo bài mới."""
    nguoi = kho.tim_nguoi(db, session_token)
    return _dang_tra_ve(noi_dung, _tim_bai(db, nguoi) or _tao_bai(db, nguoi))


def _kiem_tra_id(noi_dung: dict, chon: list) -> list:
    """Bỏ trùng (giữ thứ tự hiển thị); id lạ thì báo 422."""
    hop_le = [i["id"] for i in noi_dung["y"]]
    if not set(chon) <= set(hop_le):
        raise kho.LoiNghiepVu(422, "Có ý không hợp lệ.")
    return [i for i in hop_le if i in set(chon)]


def nop_game2(db, session_token: str, chon: list, noi_dung: dict) -> dict:
    """Nộp game 2: chấm ở server, lưu một lần. Nộp lần hai KHÔNG đổi kết quả đã lưu, chỉ trả lại kết quả cũ."""
    nguoi = kho.tim_nguoi(db, session_token)
    bai = _tim_bai(db, nguoi)
    if not bai:
        raise kho.LoiNghiepVu(409, "Bạn chưa bắt đầu game 2.")
    if bai["submitted_at"] is None:
        _ghi_bai(db, bai, _kiem_tra_id(noi_dung, chon), noi_dung)
        bai = _tim_bai(db, nguoi)   # đọc lại: nếu hai lần nộp cùng lúc thì lấy bản đã được ghi trước
    gs.kiem_tra_hoan_thanh(db, nguoi)
    return {"ok": True, **_dang_tra_ve(noi_dung, bai)}


def _ghi_bai(db, bai: dict, chon: list, noi_dung: dict) -> None:
    """Điều kiện submitted_at=None làm việc "chỉ một lần" an toàn kể cả khi bấm nộp hai lần cùng lúc."""
    luc_nop = gs.bay_gio()
    gia_tri = {"answer": {"selected_ids": chon, **cham_game2(noi_dung["y"], chon)},
               "duration_sec": round((luc_nop - bai["started_at"]).total_seconds()), "submitted_at": luc_nop}
    db[gs.COL_GAME].update_one({"_id": bai["_id"], "submitted_at": None}, {"$set": gia_tri})
