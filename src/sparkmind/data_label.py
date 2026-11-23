"""Nhãn dữ liệu (trường data_label: thu | pilot | that) và migration gán nhãn cho bản ghi cũ.

Quy tắc gán cho bản ghi CHƯA có nhãn (dự kiến chốt trước khi tạo mã thật, khoảng 27/11/2026; chưa phải đã chốt):
- Hướng 2 (access_codes, participants, behavior_answers, self_assessment, game_responses, scores): "thu"
  (thu dữ liệu thật chỉ bắt đầu từ 1/12, nên mọi bản ghi đang có trước đó là dữ liệu thử).
- survey_clean (hướng 1): "that". survey_form1 (dữ liệu gốc) KHÔNG BAO GIỜ bị đụng tới.
Chạy lại không đổi gì thêm (chỉ gán cho bản ghi chưa có nhãn; bản ghi đã có nhãn giữ nguyên).
"""
from . import config

BANG_HUONG2 = ("access_codes", "participants", "behavior_answers", "self_assessment", "game_responses", "scores")
QUY_TAC = {**{b: "thu" for b in BANG_HUONG2}, config.COL_CLEAN: "that"}   # bảng -> nhãn gán cho bản ghi chưa có nhãn
BANG_CO_NHAN = tuple(QUY_TAC)   # các bảng có trường data_label (survey_form1 cố ý không có)
CHUA_CO_NHAN = {"data_label": None}   # khớp cả khi trường thiếu lẫn khi bằng null


def giu_nhan_hien_co(db, bang: str, docs: list) -> list:
    """Dùng khi GHI LẠI một bảng đã làm sạch: bản ghi nào đang có data_label trong DB thì giữ đúng nhãn đó
    (làm sạch lại không được làm mất nhãn). Bản ghi chưa có nhãn thì để nguyên (coi là "that"). Sửa tại chỗ và trả docs."""
    nhan = {d["_id"]: d["data_label"] for d in db[bang].find({"data_label": {"$ne": None}}, {"data_label": 1})}
    for d in docs:
        if d["_id"] in nhan:
            d["data_label"] = nhan[d["_id"]]
    return docs


def ke_hoach(db) -> dict:
    """Chỉ ĐỌC: {bảng: {"gan": nhãn, "se_gan": số bản ghi chưa có nhãn, "tong": tổng số bản ghi}}."""
    return {b: {"gan": nhan, "se_gan": db[b].count_documents(CHUA_CO_NHAN), "tong": db[b].count_documents({})}
            for b, nhan in QUY_TAC.items()}


def ap_dung(db) -> dict:
    """GHI: gán nhãn cho bản ghi chưa có nhãn. Trả {bảng: số bản ghi đã đổi}. Idempotent."""
    return {b: db[b].update_many(CHUA_CO_NHAN, {"$set": {"data_label": nhan}}).modified_count
            for b, nhan in QUY_TAC.items()}
