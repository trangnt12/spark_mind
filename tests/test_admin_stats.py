"""Kiểm tra thống kê trang chủ quản trị (mục 6): số đúng, bản chính/chặt/rất chặt, dữ liệu thử, cache 30 giây,
quyền admin/viewer, và KHÔNG lộ email, tên, IP, nội dung. Dùng DB giả."""
import json
import sys
from datetime import timedelta
from pathlib import Path

import mongomock
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from server import main, research  # noqa: E402
from sparkmind import admin_stats, config, user_store  # noqa: E402
from sparkmind.thoi_gian import utc_now  # noqa: E402

MK = "mat-khau-dai-12-ky-tu"
GOC = {"Origin": "http://testserver"}
EMAIL = "bi.mat@gmail.com"


@pytest.fixture
def db():
    d = mongomock.MongoClient().spark_mind
    user_store.tao_chi_muc_user(d)
    main.app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: d
    admin_stats.xoa_cache()
    yield d
    main.app.dependency_overrides.clear()
    admin_stats.xoa_cache()


def vao(db, role="viewer", ip="1.2.3.4"):
    user_store.tao_user(db, role + "1", "x", role, MK, "test", bat_buoc_doi_mk=False)
    c = TestClient(main.app, client=(ip, 5))
    r = c.post("/api/auth/login", json={"username": role + "1", "password": MK}, headers=GOC)
    assert r.status_code == 200
    return c


def nap_form(db, nhieu: int, nguon="google_form", dot="dot4_sau_5_11", label="that", **co):
    gio = utc_now()
    for i in range(nhieu):
        db[config.COL_CLEAN].insert_one({"nguon": nguon, "dot": dot, "data_label": label, "thoi_gian": gio - timedelta(days=i % 3),
                                         "in_chinh": co.get("chinh", True), "in_chat": co.get("chat", False), "in_rat_chat": co.get("rat", False)})


def nap_nguoi(db, nguon="volunteer", buoc=("consent",), game=(), cot=None, label="that"):
    ma = db["access_codes"].insert_one({"code": f"MA{db['access_codes'].count_documents({})}", "source": nguon, "is_used": True, "data_label": label}).inserted_id
    p = {"code_id": ma, "source": nguon, "data_label": label, "email": EMAIL, "school_name": "Trường Bí Mật", "grade": "3", "consent": True,
         "ip_hash": "abc123", "started_at": utc_now(), "completed_at": utc_now() if "done" in buoc else None}
    pid = db["participants"].insert_one(p).inserted_id
    if "b" in buoc:
        db["behavior_answers"].insert_one({"participant_id": pid, "data_label": label, "b4_1": 3})
    if "c" in buoc:
        db["self_assessment"].insert_one({"participant_id": pid, "data_label": label, "c1": 3})
    for g in game:
        db["game_responses"].insert_one({"participant_id": pid, "data_label": label, "game": g, "submitted_at": utc_now(), "answer": {"ideas": ["ý nội dung riêng"]},
                                         **(cot or {"over_time": False, "paste_count": 0, "tab_leave_count": 0})})
    return pid


def test_huong1_so_dem_ban_nguon_dot_va_ngay(db):
    nap_form(db, 3, chinh=True, chat=True, rat=True)
    nap_form(db, 2, chinh=True)
    nap_form(db, 1, nguon="web", dot="web", chinh=False)
    d = admin_stats.lay_thong_ke(db, True)["huong1"]
    assert d["tong"] == 6 and d["muc_tieu"] == 1000
    assert d["ban"] == {"chinh": 5, "chat": 3, "rat_chat": 3}
    assert d["theo_nguon"] == {"google_form": 5, "web": 1} and d["theo_dot"] == {"dot4_sau_5_11": 5, "web": 1}
    assert len(d["theo_ngay"]) == 30 and sum(x["n"] for x in d["theo_ngay"]) == 6 and d["theo_ngay"][-1]["n"] >= 1
    assert d["moi_nhat"]


def test_an_du_lieu_thu_huong1(db):
    nap_form(db, 4)
    nap_form(db, 2, label="thu")
    nap_form(db, 1, label="pilot")
    assert admin_stats.lay_thong_ke(db, True)["huong1"]["tong"] == 4
    assert admin_stats.lay_thong_ke(db, False)["huong1"]["tong"] == 7


def test_huong2_ma_pheu_va_co(db):
    nap_nguoi(db, buoc=("consent", "b", "c"), game=(1,))
    nap_nguoi(db, buoc=("consent", "b", "c", "done"), game=(1, 2, 3), cot={"over_time": True, "paste_count": 2, "tab_leave_count": 0})
    nap_nguoi(db, "hired_team", buoc=("consent",))
    db["access_codes"].insert_one({"code": "CHUA", "source": "volunteer", "is_used": False})
    d = admin_stats.lay_thong_ke(db, True)["huong2"]
    assert d["ma"] == {"da_tao": 4, "da_dung": 3, "chua_dung": 1, "theo_nguon": {"volunteer": 3, "hired_team": 1}}
    pheu = {b["khoa"]: b["n"] for b in d["pheu"]}
    assert pheu == {"consent": 3, "info": 3, "behavior": 2, "self_assessment": 2, "game1": 2, "game2": 1, "game3": 1, "completed": 1}
    assert d["muc_tieu"] == 300
    assert d["co"] == {"da_nop": 4, "over_time": 3, "paste": 3, "tab_leave": 0}
    assert len(d["nguoi_moi_theo_ngay"]) == 30 and d["nguoi_moi_theo_ngay"][-1]["n"] == 3


def test_an_du_lieu_thu_huong2(db):
    nap_nguoi(db, "volunteer", buoc=("consent", "b"), game=(1,))
    nap_nguoi(db, "volunteer", buoc=("consent", "b"), game=(1, 2), label="pilot")
    db["access_codes"].insert_one({"code": "T", "source": "volunteer", "is_used": False, "data_label": "thu"})
    an, hien = admin_stats.lay_thong_ke(db, True)["huong2"], admin_stats.lay_thong_ke(db, False)["huong2"]
    assert an["ma"]["da_tao"] == 1 and hien["ma"]["da_tao"] == 3
    assert {b["khoa"]: b["n"] for b in an["pheu"]}["behavior"] == 1 and {b["khoa"]: b["n"] for b in hien["pheu"]}["behavior"] == 2
    assert an["co"]["da_nop"] == 1 and hien["co"]["da_nop"] == 3 and an["nguoi_moi_theo_ngay"][-1]["n"] == 1


def test_cache_30_giay(db):
    nap_form(db, 1)
    assert admin_stats.lay_thong_ke(db, True)["huong1"]["tong"] == 1
    nap_form(db, 5)
    assert admin_stats.lay_thong_ke(db, True)["huong1"]["tong"] == 1       # còn trong 30 giây: dùng số cũ
    assert admin_stats.lay_thong_ke(db, False)["huong1"]["tong"] == 6      # công tắc khác: tính riêng
    k = (id(db), True)
    admin_stats._nho[k] = (admin_stats._nho[k][0] - 31, admin_stats._nho[k][1])
    assert admin_stats.lay_thong_ke(db, True)["huong1"]["tong"] == 6       # quá 30 giây: tính lại


def test_dung_luong_db(db, monkeypatch):
    monkeypatch.setattr(type(db), "command", lambda self, *a, **k: {"dataSize": 5 * 1048576, "storageSize": 8 * 1048576, "indexSize": 1048576},
                        raising=False)
    assert admin_stats.thong_ke_he_thong(db) == {"du_lieu_mb": 5.0, "luu_tru_mb": 8.0, "chi_muc_mb": 1.0, "gioi_han_mb": 512}


def test_api_stats_quyen_va_khong_lo_thong_tin_ca_nhan(db):
    nap_form(db, 2, chinh=True, chat=True)
    nap_nguoi(db, buoc=("consent", "b", "c", "done"), game=(1, 2, 3))
    for role in ("viewer", "admin"):
        r = vao(db, role, ip=f"7.7.7.{len(role)}").get("/api/admin/stats")
        assert r.status_code == 200
        van_ban = r.text
        for bi_mat in (EMAIL, "@", "Trường Bí Mật", "abc123", "ý nội dung riêng", "ip_hash", "email", "school_name", "1.2.3.4", "password"):
            assert bi_mat not in van_ban
        d = json.loads(van_ban)
        assert set(d) == {"an_du_lieu_thu", "tao_luc", "huong1", "huong2", "he_thong"} and d["an_du_lieu_thu"] is True
    assert TestClient(main.app).get("/api/admin/stats").status_code == 401


def test_api_stats_cong_tac_ex_test(db):
    nap_form(db, 3)
    nap_form(db, 2, label="thu")
    c = vao(db, "admin")
    assert c.get("/api/admin/stats").json()["huong1"]["tong"] == 3                    # mặc định ẩn dữ liệu thử
    assert c.get("/api/admin/stats?ex_test=false").json()["huong1"]["tong"] == 5
    assert c.get("/api/admin/stats?ex_test=true").json()["huong1"]["tong"] == 3


def test_stats_rong_khong_loi(db):
    d = admin_stats.lay_thong_ke(db, True)
    assert d["huong1"]["tong"] == 0 and d["huong1"]["moi_nhat"] is None and d["huong1"]["ban"] == {"chinh": 0, "chat": 0, "rat_chat": 0}
    assert all(b["n"] == 0 for b in d["huong2"]["pheu"]) and d["huong2"]["co"]["da_nop"] == 0
