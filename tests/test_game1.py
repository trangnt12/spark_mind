"""Kiểm tra game 1: bắt đầu hai lần, nộp một lần, nộp trễ, thiếu token, chia đồ vật, A4/B1/B3, content."""
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import mongomock
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from server import game1, main, research  # noqa: E402
from sparkmind import config, game_store, research_store as kho  # noqa: E402
from tests.test_research import BAT_DAU, HANH_VI  # noqa: E402

B = "/api/research/game1"


@pytest.fixture
def client(monkeypatch):
    db = mongomock.MongoClient().spark_mind
    monkeypatch.setattr(config, "IP_HASH_SECRET", "khoa-thu")
    kho.tao_chi_muc(db)
    game_store.tao_chi_muc_game(db)
    research.gioi_han_ma.xoa()
    main.app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: db
    yield TestClient(main.app, client=("1.2.3.4", 50000)), db
    main.app.dependency_overrides.clear()


def nguoi_moi(c, db):
    ma = kho.tao_ma_moi(db, 1, "volunteer")[0]
    return c.post("/api/research/start", json={"code": ma, **BAT_DAU}).json()["session_token"]


def test_bat_dau_hai_lan_cung_do_vat(client):
    c, db = client
    t = nguoi_moi(c, db)
    a = c.post(f"{B}/start", json={"session_token": t}).json()
    b = c.post(f"{B}/start", json={"session_token": t}).json()
    assert a["do_vat"] == b["do_vat"] and a["started_at"] == b["started_at"]
    assert a["time_limit_sec"] == 180 and 0 < b["remaining_sec"] <= 180
    assert db["game_responses"].count_documents({}) == 1


def test_thieu_hoac_sai_token(client):
    c, _ = client
    assert c.post(f"{B}/start", json={}).status_code == 422
    assert c.post(f"{B}/start", json={"session_token": "sai"}).status_code == 401
    nop = {"session_token": "sai", "ideas": ["a"], "paste_count": 0, "tab_leave_count": 0}
    assert c.post(f"{B}/submit", json=nop).status_code == 401


def test_nop_mot_lan_va_lam_sach(client):
    c, db = client
    t = nguoi_moi(c, db)
    c.post(f"{B}/start", json={"session_token": t})
    y = ["  đỡ cây  ", "", "   ", "x" * 300] + [f"ý {i}" for i in range(60)]
    nop = {"session_token": t, "ideas": y, "paste_count": 2, "tab_leave_count": 1}
    r = c.post(f"{B}/submit", json=nop)
    assert r.status_code == 200
    d = db["game_responses"].find_one()
    assert d["answer"]["n_ideas"] == 50 and d["answer"]["ideas"][0] == "đỡ cây"
    assert len(d["answer"]["ideas"][1]) == 120
    assert d["over_time"] is False and d["paste_count"] == 2 and d["submitted_at"]
    assert c.post(f"{B}/submit", json=nop).status_code == 409


def test_nop_tre_van_nhan_va_ghi_co(client):
    c, db = client
    t = nguoi_moi(c, db)
    c.post(f"{B}/start", json={"session_token": t})
    db["game_responses"].update_one({}, {"$set": {"started_at": datetime.now() - timedelta(seconds=300)}})
    nop = {"session_token": t, "ideas": ["a"], "paste_count": 0, "tab_leave_count": 0}
    assert c.post(f"{B}/submit", json=nop).status_code == 200
    d = db["game_responses"].find_one()
    assert d["over_time"] is True and d["duration_sec"] >= 300


def test_nop_khi_chua_bat_dau(client):
    c, db = client
    nop = {"session_token": nguoi_moi(c, db), "ideas": ["a"], "paste_count": 0, "tab_leave_count": 0}
    assert c.post(f"{B}/submit", json=nop).status_code == 409


def test_do_vat_chia_deu():
    do_vat = game1.noi_dung_game1()["do_vat"]
    dem = Counter(game_store.chon_do_vat(f"MA{i:05d}", do_vat)["id"] for i in range(3000))
    assert len(dem) == 3 and all(800 < n < 1200 for n in dem.values())
    assert game_store.chon_do_vat("ab-cd", do_vat) == game_store.chon_do_vat("ABCD", do_vat)


def test_a4_chua_bao_gio_khong_can_b(client):
    c, db = client
    t = nguoi_moi(c, db)
    r = c.post("/api/research/behavior", json={"session_token": t, "A4": 4, "duration_sec": 5})
    assert r.status_code == 200 and db["behavior_answers"].find_one()["a4"] == "4"


def test_a4_co_dung_thi_bat_buoc_b_va_luu_b1_b3(client):
    c, db = client
    t = nguoi_moi(c, db)
    thieu = {k: v for k, v in HANH_VI.items() if k != "B1"}
    assert c.post("/api/research/behavior", json={"session_token": t, **thieu}).status_code == 422
    assert c.post("/api/research/behavior", json={"session_token": t, **HANH_VI, "B3": [99]}).status_code == 422
    assert c.post("/api/research/behavior", json={"session_token": t, **HANH_VI}).status_code == 200
    d = db["behavior_answers"].find_one()
    assert (d["a4"], d["b1"], d["b3"]) == ("1", "1,2", "1,5")


def test_content_khong_co_ghi_chu(client):
    c, _ = client
    for duong in ("/api/content/form-b", "/api/content/ui"):
        r = c.get(duong)
        assert r.status_code == 200 and "_ghi_chu" not in r.text
    assert "phan_b_hanh_vi" in c.get("/api/content/form-b").json()
