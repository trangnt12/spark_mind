"""Đọc dữ liệu gốc từ file Excel (Google Form xuất ra) hoặc từ MongoDB."""
from pathlib import Path

import pandas as pd

from . import config
from .columns import RAW_KEYS, ten_ngan
from .db import doc_tu_mongo, tao_id


def doc_excel(duong_dan: Path = config.RAW_EXCEL, nguon: str = "google_form") -> pd.DataFrame:
    """Đọc file Excel gốc, đổi tên cột ngắn, thêm cột nguon và _id."""
    df = pd.read_excel(duong_dan)
    df.columns = [ten_ngan(c) for c in df.columns]
    df = df[[c for c in df.columns if c in RAW_KEYS]].copy()
    df["nguon"] = nguon
    df["_id"] = [tao_id(r) for r in df.to_dict("records")]
    return df


def doc_goc_mongo(db) -> pd.DataFrame:
    return doc_tu_mongo(db[config.COL_RAW])


def doc_sach_mongo(db, ban: str | None = None) -> pd.DataFrame:
    """Đọc dữ liệu đã làm sạch từ MongoDB. ban = 'chinh' / 'chat' / 'rat_chat' để lấy một bản."""
    loc = {f"in_{ban}": True} if ban else {}
    return pd.DataFrame(list(db[config.COL_CLEAN].find(loc)))
