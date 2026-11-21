"""Kiểm tra sửa nhãn nguồn: chỉ đổi form cũ google_form, giữ _id và nội dung, chạy lại không đổi thêm."""
import sys
from datetime import datetime
from pathlib import Path

import mongomock
import pandas as pd

RE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RE / "scripts"))
sys.path.insert(0, str(RE / "src"))
import fix_nguon  # noqa: E402
from sparkmind import config  # noqa: E402
from sparkmind.cleaning import gan_dot  # noqa: E402


def tao_db():
    db = mongomock.MongoClient().spark_mind
    docs = [
        {"_id": "cu", "nguon": "google_form", "thoi_gian": datetime(2026, 11, 5, 9), "C1": 4},
        {"_id": "moc", "nguon": "google_form", "thoi_gian": datetime(2026, 11, 20, 0), "C1": 3},
        {"_id": "moi", "nguon": "google_form", "thoi_gian": datetime(2026, 12, 1, 9), "C1": 5},
        {"_id": "web", "nguon": "web", "thoi_gian": datetime(2026, 11, 5, 9), "C1": 2},
    ]
    for ten in (config.COL_RAW, config.COL_CLEAN):
        db[ten].insert_many([dict(d) for d in docs])
    return db


def test_dry_run_khong_ghi():
    db = tao_db()
    assert fix_nguon.doi_nguon(db, dry_run=True) == {config.COL_RAW: 1, config.COL_CLEAN: 1}
    assert db[config.COL_RAW].find_one({"_id": "cu"})["nguon"] == "google_form"


def test_doi_dung_form_va_giu_noi_dung():
    db = tao_db()
    assert fix_nguon.doi_nguon(db) == {config.COL_RAW: 1, config.COL_CLEAN: 1}
    for ten in (config.COL_RAW, config.COL_CLEAN):
        nguon = {d["_id"]: d["nguon"] for d in db[ten].find()}
        assert nguon == {"cu": "excel_import", "moc": "google_form", "moi": "google_form", "web": "web"}
        assert db[ten].find_one({"_id": "cu"})["C1"] == 4  # nội dung không đổi


def test_chay_lai_khong_doi_them():
    db = tao_db()
    fix_nguon.doi_nguon(db)
    assert fix_nguon.doi_nguon(db) == {config.COL_RAW: 0, config.COL_CLEAN: 0}


def test_gan_dot_chi_dua_vao_nguon_web():
    df = pd.DataFrame({"thoi_gian": ["2026-11-05 09:00:00"] * 3,
                       "nguon": ["web", "google_form", "excel_import"]})
    assert list(gan_dot(df)) == ["web", "dot3_4-5/11", "dot3_4-5/11"]
