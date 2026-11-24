"""Trang quản trị cho cờ chống gian lận và lô mã (24/11): cột và bộ lọc ở danh sách participants, thống kê ở Tổng quan,
CSV, thống kê theo lô mã, tạo mã có batch, quyền, và KHÔNG lộ email/mã."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sparkmind import admin_codes_stats, admin_registry as reg, admin_stats  # noqa: E402
from tests.test_admin_stats import EMAIL, GOC, db, nap_nguoi, vao  # noqa: E402,F401  (db là fixture dùng chung)

CSRF = {"X-CSRF-Token": ""}


def gan_co(db, pid, cac_co, dem):
    db["participants"].update_one({"_id": pid}, {"$set": {"flags": cac_co, "flag_count": dem}})


@pytest.fixture
def ba_nguoi(db):
    """Người 1: một cờ nhanh + một gián đoạn; người 2: chỉ gián đoạn; người 3: chưa có cờ nào (chưa tính)."""
    a, b, c = nap_nguoi(db), nap_nguoi(db), nap_nguoi(db)
    gan_co(db, a, ["lam_qua_nhanh:form_b", "bi_gian_doan:khoi_c"], 1)
    gan_co(db, b, ["bi_gian_doan:form_b"], 0)
    return a, b, c


def test_registry_hop_le_va_co_cot_loc_co():
    assert reg.kiem_tra_registry() == []
    p = reg.BANG["participants"]
    assert {"flag_count", "flags"} <= {k for k, *_ in p["cot"]}
    loc = {k: lc for k, _, _, lc in p["loc"]}
    assert "flag_count" in loc and set(loc["flags"]) == set(reg.LUA_CHON_CO) and len(loc["flags"]) == 8


def test_thong_ke_so_nguoi_bi_tung_co_va_gian_doan_khong_vao_so_sanh(db, ba_nguoi):
    c = admin_stats.thong_ke_co(db, {})
    assert c["tong"] == 3
    assert c["theo_co"] == {"lam_qua_nhanh:form_b": 1, "bi_gian_doan:khoi_c": 1, "bi_gian_doan:form_b": 1}
    assert c["theo_ma"] == {"lam_qua_nhanh": 1, "bi_gian_doan": 2}
    assert c["co_it_nhat_mot"] == 1 and c["khong_co"] == 2     # người chỉ bị bi_gian_doan vẫn tính là "không có cờ"
    assert c["tham_khao"] == ["bi_gian_doan"]


def test_thong_ke_dem_nguoi_khong_dem_co(db):
    a = nap_nguoi(db)
    gan_co(db, a, ["lam_qua_nhanh:form_b", "lam_qua_nhanh:game1", "mot_dap_an:khoi_c"], 3)
    c = admin_stats.thong_ke_co(db, {})
    assert c["theo_ma"] == {"lam_qua_nhanh": 1, "mot_dap_an": 1} and c["co_it_nhat_mot"] == 1


def test_thong_ke_tong_quan_co_khoi_co_va_an_du_lieu_thu(db):
    a, b = nap_nguoi(db, label="that"), nap_nguoi(db, label="thu")
    gan_co(db, a, ["mot_dap_an:form_b"], 1)
    gan_co(db, b, ["lam_qua_nhanh:game1"], 1)
    admin_stats.xoa_cache()
    assert admin_stats.lay_thong_ke(db, True)["huong2"]["co_chong_gian_lan"]["theo_ma"] == {"mot_dap_an": 1}
    admin_stats.xoa_cache()
    assert admin_stats.lay_thong_ke(db, False)["huong2"]["co_chong_gian_lan"]["tong"] == 2


def test_api_thong_ke_khong_lo_email(db, ba_nguoi):
    r = vao(db, "viewer").get("/api/admin/stats")
    assert r.status_code == 200 and r.json()["huong2"]["co_chong_gian_lan"]["co_it_nhat_mot"] == 1
    assert EMAIL not in r.text


def test_danh_sach_participants_hien_cot_co_va_loc_theo_co(db, ba_nguoi):
    c = vao(db, "viewer")
    tat_ca = c.get("/api/admin/data/participants").json()
    assert tat_ca["tong"] == 3 and {"flag_count", "flags"} <= set(tat_ca["dong"][0])
    r = c.get("/api/admin/data/participants", params={"f.flags": "bi_gian_doan:form_b"}).json()
    assert r["tong"] == 1 and r["dong"][0]["flags"] == ["bi_gian_doan:form_b"]
    r = c.get("/api/admin/data/participants", params={"f.flag_count": "1"}).json()
    assert r["tong"] == 1 and r["dong"][0]["flags"][0] == "lam_qua_nhanh:form_b"
    assert c.get("/api/admin/data/participants", params={"f.flags": "khong_co_that"}).status_code == 422
    assert c.get("/api/admin/data/participants", params={"f.flag_count": "abc"}).status_code == 422


def test_csv_participants_co_cot_co_noi_bang_cham_phay_va_khong_co_email(db, ba_nguoi):
    r = vao(db, "viewer").get("/api/admin/data/participants/export.csv")
    assert r.status_code == 200 and "Số cờ" in r.text and "lam_qua_nhanh:form_b; bi_gian_doan:khoi_c" in r.text
    assert EMAIL not in r.text and "@" not in r.text


def test_chi_tiet_participants_hien_flags(db, ba_nguoi):
    a, _, _ = ba_nguoi
    d = vao(db, "viewer").get(f"/api/admin/data/participants/{a}").json()
    gia_tri = {f["khoa"]: f["gia_tri"] for f in d["truong"]}
    assert gia_tri["flags"] == ["lam_qua_nhanh:form_b", "bi_gian_doan:khoi_c"] and gia_tri["flag_count"] == 1


# ---------- Lô mã ----------

def them_ma(db, batch, label="that", da_dung=False):
    return db["access_codes"].insert_one({"code": f"X{db['access_codes'].count_documents({})}ZZZZZZ", "source": "hired_team", "data_label": label,
                                          "batch": batch, "is_used": da_dung}).inserted_id


def test_thong_ke_theo_lo_tong_da_dung_hoan_thanh(db):
    ids = [them_ma(db, "nhom_thue_1", da_dung=True), them_ma(db, "nhom_thue_1", da_dung=True), them_ma(db, "nhom_thue_1"),
           them_ma(db, "lop_khoa_a"), them_ma(db, None)]
    from sparkmind.thoi_gian import utc_now
    db["participants"].insert_one({"code_id": ids[0], "completed_at": utc_now(), "data_label": "that"})
    db["participants"].insert_one({"code_id": ids[1], "completed_at": None, "data_label": "that"})
    kq = {d["batch"]: d for d in admin_codes_stats.thong_ke_lo(db)}
    assert (kq["nhom_thue_1"]["tong"], kq["nhom_thue_1"]["da_dung"], kq["nhom_thue_1"]["chua_dung"], kq["nhom_thue_1"]["hoan_thanh"]) == (3, 2, 1, 1)
    assert (kq["lop_khoa_a"]["tong"], kq["lop_khoa_a"]["hoan_thanh"]) == (1, 0)
    assert kq[None]["tong"] == 1
    assert admin_codes_stats.thong_ke_lo(db)[0]["batch"] == "nhom_thue_1"          # lô lớn đứng đầu


def test_thong_ke_lo_tach_theo_nhan_va_an_du_lieu_thu(db):
    them_ma(db, "lo_a", "that")
    them_ma(db, "lo_a", "thu")
    assert [(d["batch"], d["nhan"]) for d in admin_codes_stats.thong_ke_lo(db, True)] == [("lo_a", "that")]
    assert sorted(d["nhan"] for d in admin_codes_stats.thong_ke_lo(db, False)) == ["that", "thu"]


def test_api_lo_ma_khong_tra_ma_va_can_dang_nhap(db):
    them_ma(db, "lo_a")
    r = vao(db, "viewer").get("/api/admin/codes/batches")
    assert r.status_code == 200 and r.json()["lo"][0]["tong"] == 1 and "ZZZZZZ" not in r.text
    from fastapi.testclient import TestClient
    from server import main
    assert TestClient(main.app).get("/api/admin/codes/batches").status_code == 401


def test_danh_sach_ma_loc_theo_batch_va_nhan(db):
    them_ma(db, "lo_a", "that"), them_ma(db, "lo_b", "that"), them_ma(db, "lo_a", "thu")
    c = vao(db, "viewer")
    assert c.get("/api/admin/data/access_codes", params={"f.batch": "lo_a", "ex_test": "false"}).json()["tong"] == 2
    assert c.get("/api/admin/data/access_codes", params={"f.batch": "lo_a", "f.data_label": "thu", "ex_test": "false"}).json()["tong"] == 1
    assert c.get("/api/admin/data/access_codes", params={"f.is_used": "false", "ex_test": "false"}).json()["tong"] == 3


def dang_nhap_admin(db):
    c = vao(db, "admin")
    csrf = c.get("/api/auth/me").json()["csrf_token"]
    c.headers.update({"X-CSRF-Token": csrf, **GOC})
    return c


def test_admin_tao_ma_co_batch_va_kiem_tra_ten_lo(db):
    c = dang_nhap_admin(db)
    ok = c.post("/api/admin/data/access_codes", json={"code": "ABCD2345", "source": "hired_team", "data_label": "thu", "batch": "nhom_thue_1"})
    assert ok.status_code == 201
    assert db["access_codes"].find_one({"code": "ABCD2345"})["batch"] == "nhom_thue_1"
    xau = c.post("/api/admin/data/access_codes", json={"code": "ABCD2346", "source": "hired_team", "data_label": "thu", "batch": "=1+1"})
    assert xau.status_code == 422
    khong_lo = c.post("/api/admin/data/access_codes", json={"code": "ABCD2347", "source": "hired_team", "data_label": "thu"})
    assert khong_lo.status_code == 201 and db["access_codes"].find_one({"code": "ABCD2347"}).get("batch") is None
