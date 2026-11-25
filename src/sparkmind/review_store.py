"""Dữ liệu cho trang "Xem lại bài của bạn" (GET /api/research/review). Chỉ ĐỌC, không ghi gì.

Đây là NƠI DUY NHẤT đáp án game 2 (la_loi, loai_loi, giai_thich) và điểm game 2 rời khỏi server.
Hàm gọi (server/review_api.py) phải kiểm tra participants.completed_at TRƯỚC khi gọi vào đây.
Chỉ trả bài của chính người đó; không trả thời gian, số lần dán hay cờ chất lượng.
"""
from sparkmind.game_store import COL_GAME
from sparkmind.progress import cau_tra_loi_da_luu


def _bai(db, nguoi: dict, game: int) -> dict:
    return db[COL_GAME].find_one({"participant_id": nguoi["_id"], "game": game}) or {}


def phan_game1(db, nguoi: dict, nd: dict) -> dict:
    """Đồ vật được giao và các ý đã viết (không điểm)."""
    bai = _bai(db, nguoi, 1)
    do_vat = next((d for d in nd["do_vat"] if d["id"] == bai.get("prompt_id")), None)
    return {"ten": nd["ten"], "do_vat": do_vat, "ideas": (bai.get("answer") or {}).get("ideas", [])}


def phan_game2(db, nguoi: dict, nd: dict) -> dict:
    """12 ý theo thứ tự cố định kèm lựa chọn của người chơi và đáp án; điểm x/5."""
    a = _bai(db, nguoi, 2).get("answer") or {}
    chon = set(a.get("selected_ids", []))
    y = [{"id": i["id"], "van_ban": i["van_ban"], "da_chon": i["id"] in chon, "la_loi": i["la_loi"],
          "loai_loi": i["loai_loi"], "giai_thich": i["giai_thich"]} for i in nd["y"]]
    return {"ten": nd["ten"], "tinh_huong": nd["tinh_huong"], "diem": a.get("score", 0), "diem_toi_da": 5, "y": y}


def phan_game3(db, nguoi: dict, nd: dict) -> dict:
    """Hai ý tưởng đã viết, kèm tên tình huống và ý của AI để nhớ lại (không điểm)."""
    viet = {m["tinh_huong_id"]: m["noi_dung"] for m in (_bai(db, nguoi, 3).get("answer") or {}).get("tinh_huong", [])}
    cac_th = [{"id": t["id"], "tieu_de": t["tieu_de"], "ai_goc": t["ai_goc"], "noi_dung": viet.get(t["id"], "")} for t in nd["tinh_huong"]]
    return {"ten": nd["ten"], "tinh_huong": cac_th}


def phan_khao_sat(db, nguoi: dict) -> dict:
    """Câu đã chọn ở phần B (hành vi, kể cả lưới B4) và phần C (tự đánh giá C1–C5, C6), cùng dạng form dùng (mã đáp án).
    Phần chưa làm hoặc bỏ qua (chưa từng dùng AI) là None. Chỉ của chính người này."""
    d = cau_tra_loi_da_luu(db, nguoi)
    return {"hanh_vi": d["behavior"], "tu_danh_gia": d["self_assessment"]}


def xem_lai(db, nguoi: dict, nd1: dict, nd2: dict, nd3: dict) -> dict:
    return {**phan_khao_sat(db, nguoi), "game1": phan_game1(db, nguoi, nd1), "game2": phan_game2(db, nguoi, nd2), "game3": phan_game3(db, nguoi, nd3)}
