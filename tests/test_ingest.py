"""Kiểm tra nhận form mới: lưu gốc, làm sạch ngay, không nhân đôi, chặn khi sai khóa."""
import sys
from pathlib import Path

import mongomock
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from server import main  # noqa: E402
from sparkmind import config  # noqa: E402

FORM = {"thoi_gian": "2026-12-01 10:00:00", "A1": "Lớp 11", "A2": "Nữ", "A3": "THPT Bắc Bình",
        "A4": "Có, thường xuyên", "B1": "ChatGPT, Gemini", "B2": "Vài lần/tuần", "B3": "Giải bài tập",
        "B4_1": 4, "B4_2": 5, "B4_3": 2, "B4_4": 4, "B4_5": 3, "B4_6": 2, "B4_7": 5,
        "B5": "5–15 phút", "B6": "Gõ ngắn gọn", "B7": "So sánh",
        "C1": 4, "C2": 3, "C3": 4, "C4": 5, "C5": 4, "C6": "Chưa từng"}


@pytest.fixture
def client(monkeypatch):
    db = mongomock.MongoClient().spark_mind
    monkeypatch.setattr(config, "INGEST_SECRET", "bi-mat")
    main.app.dependency_overrides[main.lay_db_dung_chung] = lambda: db
    yield TestClient(main.app), db
    main.app.dependency_overrides.clear()


def gui(c, body, khoa="bi-mat"):
    return c.post("/api/ingest/google-form", json=body, headers={"x-api-key": khoa})


def test_health(client):
    assert client[0].get("/health").json() == {"status": "ok"}


def test_luu_goc_va_lam_sach_ngay(client):
    c, db = client
    r = gui(c, FORM)
    assert r.status_code == 200 and r.json()["in_chinh"] is True
    assert db[config.COL_RAW].count_documents({}) == 1
    sach = db[config.COL_CLEAN].find_one()
    assert sach["diem_sang_tao"] == 75.0 and sach["dot"] == "dot5_form_v2" and sach["cap_hoc"] == "THPT"


def test_gui_hai_lan_khong_nhan_doi(client):
    c, db = client
    gui(c, FORM)
    gui(c, FORM)
    assert db[config.COL_RAW].count_documents({}) == 1 and db[config.COL_CLEAN].count_documents({}) == 1


def test_sai_khoa_bi_chan(client):
    c, db = client
    assert gui(c, FORM, khoa="sai").status_code == 401
    assert db[config.COL_RAW].count_documents({}) == 0


def test_form_thieu_cau_tra_loi(client):
    c, _ = client
    bad = {k: v for k, v in FORM.items() if k != "C3"}
    assert gui(c, bad).status_code == 422
    assert gui(c, {**FORM, "C1": 9}).status_code == 422
