"""Nhận một form mới: lưu bản gốc, làm sạch ngay, lưu bản sạch.

Dùng chung cho Google Form (qua Apps Script) và web hướng 1 (nguon = "web"). Gọi lại với cùng nội dung
không tạo bản sao (mã form tính từ nội dung).
"""
from datetime import datetime

import pandas as pd

from . import config
from .cleaning import clean
from .columns import B4, CC, RAW_KEYS
from .db import df_sang_docs, doc_tho_tu_dict

SO_NGUYEN = B4 + CC  # các câu trả lời bắt buộc là số 1-5


def chuan_hoa_tra_loi(answers: dict) -> dict:
    """Ép kiểu các câu trả lời; báo lỗi rõ ràng nếu form không hợp lệ."""
    a = {k: answers.get(k) for k in RAW_KEYS}
    for k in SO_NGUYEN:
        v = a[k]
        if v in (None, ""):
            a[k] = None
            continue
        try:
            a[k] = int(v)
        except (TypeError, ValueError):
            raise ValueError(f"Câu {k} phải là số 1-5, nhận được: {v!r}")
        if not 1 <= a[k] <= 5:
            raise ValueError(f"Câu {k} phải trong khoảng 1-5, nhận được: {a[k]}")
    if not a["A4"] or not all(a[k] is not None for k in CC):
        raise ValueError("Thiếu câu A4 hoặc C1-C5")
    t = answers.get("thoi_gian")
    a["thoi_gian"] = pd.to_datetime(t).to_pydatetime() if t else datetime.now()
    return a


def nhan_form(db, answers: dict, nguon: str = "google_form", nhan: str = config.NHAN_MAC_DINH, them: dict | None = None) -> dict:
    """Lưu form gốc + làm sạch + lưu bản sạch. Trả về tóm tắt để ghi log.

    nhan: data_label của bản sạch ("that" mặc định). them: trường riêng thêm vào bản gốc (vd. thoi_gian_lam_bai của web).
    - Bản gốc chỉ được THÊM MỚI ($setOnInsert): đã có _id thì không sửa gì (dữ liệu gốc không bao giờ bị sửa).
    - Form thử (nhãn thu/pilot) KHÔNG ghi vào survey_form1: bản gốc không có data_label nên không dọn được, và run_cleaning sẽ
      làm sạch lại nó thành "that". Form thử chỉ nằm ở bản sạch, có nhãn, dọn được bằng chức năng xóa dữ liệu thử.
    """
    if nhan not in config.NHAN_HOP_LE:
        raise ValueError(f"Nhãn dữ liệu không hợp lệ: {nhan!r}")
    goc = {**doc_tho_tu_dict(chuan_hoa_tra_loi(answers), nguon), **(them or {})}
    if nhan not in config.NHAN_DU_LIEU_THU:
        db[config.COL_RAW].update_one({"_id": goc["_id"]}, {"$setOnInsert": goc}, upsert=True)
    sach = df_sang_docs(clean(pd.DataFrame([goc])))[0]
    sach["data_label"] = nhan   # nhãn nằm ở bản sạch, không đụng bản gốc
    if nhan in config.NHAN_DU_LIEU_THU:   # form thử trùng _id với form thật thì KHÔNG được ghi đè (kẻo form thật bị đổi nhãn thành thử rồi bị dọn)
        db[config.COL_CLEAN].update_one({"_id": sach["_id"]}, {"$setOnInsert": sach}, upsert=True)
    else:
        db[config.COL_CLEAN].replace_one({"_id": sach["_id"]}, sach, upsert=True)
    return {"id": goc["_id"], "dot": sach["dot"], "dung_ai": sach["dung_ai"],
            "in_chinh": sach["in_chinh"], "in_chat": sach["in_chat"], "in_rat_chat": sach["in_rat_chat"]}
