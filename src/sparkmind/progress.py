"""Tiến độ của một người tham gia (hướng 2) và câu trả lời đã lưu để điền sẵn khi quay lại.

Chỉ ĐỌC, không ghi gì. Dùng cho GET /api/research/progress.
"""
from sparkmind import config, research_store as kho
from sparkmind.game_store import COL_GAME

# Các bước khảo sát theo thứ tự; "info" luôn xong vì tạo người tham gia là đã có phần A
BUOC_KHAO_SAT = ("behavior", "self_assessment")


def _game_da_nop(db, nguoi: dict) -> set:
    return {b["game"] for b in db[COL_GAME].find({"participant_id": nguoi["_id"], "submitted_at": {"$ne": None}})}


def tien_do(db, nguoi: dict) -> dict:
    """steps: bước nào đã xong. next: bước dở dang đầu tiên ("behavior", "self_assessment", "game1", "game2"...),
    hoặc "cho_game_khac" (các game hiện có đã xong, còn game chưa làm), hoặc "completed". locked: khảo sát đã khóa."""
    xong = {"info": True,
            "behavior": db[kho.COL_HANH_VI].count_documents({"participant_id": nguoi["_id"]}) > 0,
            "self_assessment": db[kho.COL_TU_DANH_GIA].count_documents({"participant_id": nguoi["_id"]}) > 0}
    da_nop = _game_da_nop(db, nguoi)
    xong.update({f"game{g}": g in da_nop for g in config.GAME_DA_CO})
    hoan_thanh = bool(nguoi.get("completed_at"))
    thu_tu = [*BUOC_KHAO_SAT, *(f"game{g}" for g in config.GAME_DA_CO)]
    tiep = next((b for b in thu_tu if not xong[b]), "completed" if hoan_thanh else "cho_game_khac")
    return {"steps": xong, "next": tiep, "completed": hoan_thanh, "locked": hoan_thanh}


def _chuoi_sang_danh_sach(v):
    """"1,3" -> [1, 3]; trống -> None."""
    return [int(x) for x in v.split(",")] if v else None


def _hanh_vi_cho_form(d: dict) -> dict:
    """Đổi bản ghi behavior_answers về dạng form dùng (A4, B1..B7, *_other) để điền sẵn."""
    kq = {"A4": int(d["a4"])}
    for ten, khoa, nhieu in (("B1", "b1", True), ("B2", "b2_frequency", False), ("B3", "b3", True),
                             ("B5", "b5_duration", False), ("B6", "b6_prompting", True), ("B7", "b7_after_answer", False)):
        v = d.get(khoa)
        kq[ten] = None if v is None else (_chuoi_sang_danh_sach(v) if nhieu else int(v))
    for i in range(1, 8):
        kq[f"B4_{i}"] = d.get(f"b4_{i}")
    for ten in ("B1", "B3", "B6"):
        kq[f"{ten}_other"] = d.get(f"{ten.lower()}_other")
    return kq


def cau_tra_loi_da_luu(db, nguoi: dict) -> dict:
    """Câu trả lời của chính người này (info, behavior, self_assessment); phần chưa làm là None."""
    hv = db[kho.COL_HANH_VI].find_one({"participant_id": nguoi["_id"]})
    tdg = db[kho.COL_TU_DANH_GIA].find_one({"participant_id": nguoi["_id"]})
    return {"info": {"A1": int(nguoi["grade"]), "A2": int(nguoi["gender"]), "A3": nguoi["school_name"],
                     "guardian_consent": bool(nguoi.get("guardian_consent"))},
            "behavior": _hanh_vi_cho_form(hv) if hv else None,
            "self_assessment": ({**{f"C{i}": tdg[f"c{i}"] for i in range(1, 6)}, "C6": int(tdg["c6"])} if tdg else None)}
