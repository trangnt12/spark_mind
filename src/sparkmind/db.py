"""Kết nối MongoDB và ghi/đọc dữ liệu khảo sát."""
import hashlib
import json
import math
from datetime import datetime

import numpy as np
import pandas as pd

from . import config
from .columns import RAW_KEYS


def lay_db():
    """Mở kết nối tới database spark-mind (tên có gạch ngang) trên Atlas (chuỗi kết nối lấy từ .env)."""
    if not config.MONGODB_URI:
        raise RuntimeError("Chưa có MONGODB_URI. Hãy tạo file .env từ .env.example.")
    from pymongo import MongoClient
    client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")  # báo lỗi sớm nếu không kết nối được
    return client[config.MONGODB_DB]


def tao_id(row: dict) -> str:
    """Mã duy nhất của một form, tính từ nội dung gốc. Chạy lại không tạo bản sao."""
    goc = {k: str(row.get(k)) for k in RAW_KEYS}
    return hashlib.sha1(json.dumps(goc, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]


def _sach(v):
    """Đổi giá trị pandas/numpy sang kiểu Mongo lưu được (NaN -> None)."""
    if v is None or v is pd.NaT:
        return None
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if math.isnan(v) else float(v)
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, datetime):
        return v
    return v


def df_sang_docs(df: pd.DataFrame) -> list:
    return [{k: _sach(v) for k, v in r.items()} for r in df.to_dict("records")]


def ghi_nhieu(collection, docs: list, gop: bool = True) -> int:
    """Ghi theo _id: có rồi thì thay, chưa có thì thêm. Trả về số tài liệu.

    gop=True ghi gộp một lượt (nhanh, dùng với MongoDB thật). gop=False ghi từng cái (dùng khi thử).
    """
    if not docs:
        return 0
    if gop:
        from pymongo import ReplaceOne
        collection.bulk_write([ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs])
    else:
        for d in docs:
            collection.replace_one({"_id": d["_id"]}, d, upsert=True)
    return len(docs)


def doc_tho_tu_dict(answers: dict, nguon: str) -> dict:
    """Tạo tài liệu gốc từ câu trả lời một form (dùng cho Apps Script và web)."""
    doc = {k: answers.get(k) for k in RAW_KEYS}
    doc["thoi_gian"] = answers.get("thoi_gian") or datetime.now()
    doc["nguon"] = nguon
    doc["_id"] = tao_id(doc)
    return doc


def doc_tu_mongo(collection) -> pd.DataFrame:
    return pd.DataFrame(list(collection.find()))
