"""Đọc/ghi MongoDB cho game 3 (Làm tốt hơn AI). Cấu trúc theo docs/erd.dbml (bảng game_responses, game = 3).

Mỗi người có MỘT bản ghi game_responses (game = 3); mỗi tình huống là một mục trong answer.tinh_huong:
  {tinh_huong_id, noi_dung, so_tu, thoi_gian_lam, so_lan_dan, so_lan_roi_tab, nop_luc}
NỘP MỘT LẦN cho cả hai tình huống (nút "Nộp bài"). Đã nộp thì không sửa, nộp lại không ghi đè.
thoi_gian_lam của từng tình huống do TRÌNH DUYỆT đo (tổng thời gian ô nhập đang được dùng, đã trừ lúc ẩn tab) nên chỉ để gắn cờ;
duration_sec (cả game) do SERVER tính từ started_at đến lúc nộp.
Điểm AI và điểm người chấm KHÔNG nằm ở đây: sẽ chấm sau, lưu ở collection riêng, khóa (participant_id, tinh_huong_id).
"""
import json
from functools import lru_cache

from pymongo.errors import DuplicateKeyError

from sparkmind import config, game_store as gs, research_store as kho

GAME = 3
CAC_TRUONG_CHO_TRINH_DUYET = ("so", "ten", "gioi_thieu", "tinh_huong", "toi_thieu_ky_tu", "toi_da_ky_tu")


@lru_cache
def noi_dung_game3() -> dict:
    """Đề game 3 đọc từ content/games/game3.json (không viết cứng)."""
    with open(config.ROOT / "content" / "games" / "game3.json", encoding="utf-8") as f:
        return json.load(f)


def ai_goc_theo_id() -> dict:
    """{id tình huống: câu trả lời gốc của AI}, dùng để gắn cờ copy_ai_goc."""
    return {t["id"]: t["ai_goc"] for t in noi_dung_game3()["tinh_huong"]}


def noi_dung_cho_trinh_duyet(nd: dict) -> dict:
    """Chỉ các trường giao diện cần (không lộ ghi chú nội bộ hay trường nào khác)."""
    return {k: nd[k] for k in CAC_TRUONG_CHO_TRINH_DUYET}


def dem_tu(chu: str) -> int:
    """Số từ = số cụm chữ cách nhau bởi khoảng trắng (cách đếm duy nhất, giao diện đếm giống hệt)."""
    return len(chu.split())


def _tim_bai(db, nguoi: dict):
    return db[gs.COL_GAME].find_one({"participant_id": nguoi["_id"], "game": GAME})


def _tao_bai(db, nguoi: dict) -> dict:
    """Ghi bài mới với started_at do SERVER đặt (gọi lại thì trả bài cũ). data_label kế thừa từ participants."""
    bai = {"participant_id": nguoi["_id"], "game": GAME, "data_label": nguoi.get("data_label", config.NHAN_MAC_DINH),
           "prompt_id": "game3", "started_at": gs.bay_gio(), "submitted_at": None, "answer": {"tinh_huong": []}}
    try:
        db[gs.COL_GAME].insert_one(bai)
    except DuplicateKeyError:
        return _tim_bai(db, nguoi)
    return bai


def bat_dau_game3(db, session_token: str) -> dict:
    """Bắt đầu game 3 (started_at do server đặt); gọi lại thì trả cùng bài. Chỉ báo đã nộp chưa (bài đã nộp xem qua /review)."""
    nguoi = kho.tim_nguoi(db, session_token)
    bai = _tim_bai(db, nguoi) or _tao_bai(db, nguoi)
    return {"submitted": bai["submitted_at"] is not None}


def _kiem_tra_noi_dung(nd: dict, chu: str) -> int:
    """Trả số từ (vẫn tính và lưu để phân tích) nếu hợp lệ; ngược lại báo 422. Tối thiểu đếm theo KÝ TỰ (bỏ khoảng trắng hai đầu)."""
    so_tu = dem_tu(chu)
    if len(chu.strip()) < nd["toi_thieu_ky_tu"]:
        raise kho.LoiNghiepVu(422, f"Bạn viết thêm một chút nhé: cần ít nhất {nd['toi_thieu_ky_tu']} ký tự.")
    if len(chu) > nd["toi_da_ky_tu"]:
        raise kho.LoiNghiepVu(422, f"Bài hơi dài: tối đa {nd['toi_da_ky_tu']} ký tự.")
    return so_tu


def _kiem_tra_du_hai(nd: dict, cac_o: list) -> dict:
    """Phải có ĐÚNG mỗi tình huống một lần (không thiếu, không thừa, không trùng). Trả {id: ô}."""
    ids = [t["id"] for t in nd["tinh_huong"]]
    theo_id = {o["tinh_huong_id"]: o for o in cac_o}
    if len(cac_o) != len(ids) or set(theo_id) != set(ids):
        raise kho.LoiNghiepVu(422, "Cần nộp đủ ý tưởng cho cả hai tình huống.")
    return theo_id


def _tao_cac_muc(nd: dict, theo_id: dict, luc_nop) -> list:
    """Các mục theo đúng thứ tự trong content. Kiểm tra từng ô (số từ, độ dài) ngay tại đây."""
    cac_muc = []
    for t in nd["tinh_huong"]:
        o = theo_id[t["id"]]
        cac_muc.append({"tinh_huong_id": t["id"], "noi_dung": o["noi_dung"], "so_tu": _kiem_tra_noi_dung(nd, o["noi_dung"]),
                        "thoi_gian_lam": o["thoi_gian_giay"], "so_lan_dan": o["paste_count"],
                        "so_lan_roi_tab": o["tab_leave_count"], "nop_luc": luc_nop})
    return cac_muc


def _tong_hop(cac_muc: list, giay_ca_game: int) -> dict:
    """Số tổng ở cấp bài (để trang quản trị lọc/sắp xếp như game 1, 2). duration_sec = thời gian cả game do server tính."""
    return {"duration_sec": giay_ca_game, "answer_length": sum(len(m["noi_dung"]) for m in cac_muc),
            "paste_count": sum(m["so_lan_dan"] for m in cac_muc), "tab_leave_count": sum(m["so_lan_roi_tab"] for m in cac_muc)}


def nop_game3(db, session_token: str, d: dict, nd: dict) -> dict:
    """Nộp cả hai tình huống một lần. Đã nộp rồi thì KHÔNG ghi đè (trả ok như cũ). Nộp xong thì gán completed_at (nếu đủ 3 game)."""
    nguoi = kho.tim_nguoi(db, session_token)
    bai = _tim_bai(db, nguoi)
    if not bai:
        raise kho.LoiNghiepVu(409, "Bạn chưa bắt đầu game 3.")
    if bai["submitted_at"] is None:
        _ghi_bai(db, bai, _kiem_tra_du_hai(nd, d["items"]), nd)
    gs.kiem_tra_hoan_thanh(db, nguoi)
    return {"ok": True}


def _ghi_bai(db, bai: dict, theo_id: dict, nd: dict) -> None:
    """Điều kiện submitted_at=None làm việc "chỉ một lần" an toàn kể cả khi bấm nộp hai lần cùng lúc."""
    luc_nop = gs.bay_gio()
    cac_muc = _tao_cac_muc(nd, theo_id, luc_nop)
    gia_tri = {"answer": {"tinh_huong": cac_muc}, "submitted_at": luc_nop,
               **_tong_hop(cac_muc, max(0, round((luc_nop - bai["started_at"]).total_seconds())))}
    db[gs.COL_GAME].update_one({"_id": bai["_id"], "submitted_at": None}, {"$set": gia_tri})
