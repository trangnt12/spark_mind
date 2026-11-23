"""Kiểm tra nền tảng quản trị (mục 1–4): mật khẩu, tài khoản, phiên, CSRF, khóa dò mật khẩu, phân quyền, nhật ký.
Dùng DB giả (mongomock); không chạm MongoDB thật."""
import sys
from datetime import timedelta
from pathlib import Path

import mongomock
import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from server import auth, main, research  # noqa: E402
from sparkmind import audit, passwords, session_store, user_store  # noqa: E402
from sparkmind.thoi_gian import utc_now  # noqa: E402

MK = "mat-khau-dai-12-ky-tu"
GOC = {"Origin": "http://testserver"}


@pytest.fixture
def db():
    d = mongomock.MongoClient().spark_mind
    user_store.tao_chi_muc_user(d)
    session_store.tao_chi_muc_phien(d)
    audit.tao_chi_muc_audit(d)
    main.app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: d
    yield d
    main.app.dependency_overrides.clear()


def tao(db, ten, role, mk=MK, doi_mk=False):
    return user_store.tao_user(db, ten, ten.title(), role, mk, "test", bat_buoc_doi_mk=doi_mk)


def client(ip="1.2.3.4", **kw):
    return TestClient(main.app, client=(ip, 50000), **kw)


def dang_nhap(c, ten, mk=MK):
    r = c.post("/api/auth/login", json={"username": ten, "password": mk}, headers=GOC)
    if r.status_code == 200:
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return r


def dang_nhap_ok(db, ten, role, ip="1.2.3.4"):
    tao(db, ten, role)
    c = client(ip)
    assert dang_nhap(c, ten).status_code == 200
    return c


# ---------- Mật khẩu và tài khoản ----------

def test_bam_mat_khau_scrypt_co_tham_so_va_muoi_ngau_nhien():
    a, b = passwords.bam(MK), passwords.bam(MK)
    assert a != b                                      # muối khác nhau
    algo, n, r, p, muoi, _ = a.split("$")
    assert (algo, int(n), int(r), int(p)) == ("scrypt", 2 ** 14, 8, 1) and len(bytes.fromhex(muoi)) == 16
    assert passwords.xac_minh(MK, a) and not passwords.xac_minh(MK + "x", a)
    assert not passwords.xac_minh(MK, None)            # user không tồn tại: vẫn chạy scrypt rồi trả False
    assert not passwords.xac_minh(MK, "hong")          # hash hỏng không làm sập


def test_mat_khau_toi_thieu_12_ky_tu():
    assert passwords.kiem_tra_do_manh("ngan-qua") == "too_short"
    assert passwords.kiem_tra_do_manh("a" * 11) == "too_short"
    assert passwords.kiem_tra_do_manh("a" * 12) is None
    assert len(passwords.tao_mat_khau_tam()) >= 12


def test_tao_user_chu_thuong_duy_nhat_va_khong_lo_hash(db):
    u = tao(db, "  Trang ", "admin")
    assert u["username"] == "trang" and u["must_change_password"] is False
    assert db["users"].index_information()["username_1"]["unique"]
    with pytest.raises(Exception) as e:
        tao(db, "TRANG", "viewer")
    assert e.value.noi_dung == "username_taken"
    assert "password_hash" not in user_store.cong_khai(u)
    assert all("password_hash" not in x for x in user_store.danh_sach(db))
    for doc in (u,):
        assert doc["password_hash"].startswith("scrypt$") and MK not in doc["password_hash"]


@pytest.mark.parametrize("ten,role,mk,ma", [("ab", "admin", MK, "bad_username"), ("co dau", "admin", MK, "bad_username"),
                                            ("hop-le", "root", MK, "bad_role"), ("hop-le", "admin", "ngan", "weak_password")])
def test_tao_user_sai(db, ten, role, mk, ma):
    with pytest.raises(Exception) as e:
        user_store.tao_user(db, ten, "x", role, mk, "test")
    assert e.value.noi_dung == ma


# ---------- Đăng nhập và phiên ----------

def test_dang_nhap_dat_cookie_an_toan_va_chi_luu_bam_token(db):
    tao(db, "trang", "admin")
    c = client()
    r = dang_nhap(c, "trang")
    assert r.status_code == 200 and "csrf_token" in r.json() and "password_hash" not in r.text
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "secure" not in cookie   # HTTP thường: chưa Secure
    token = c.cookies.get(auth.TEN_COOKIE)
    phien = db["admin_sessions"].find_one()
    assert phien["_id"] == session_store.bam_token(token) and token not in str(phien)       # chỉ lưu băm SHA-256
    assert db["admin_sessions"].index_information()["expires_at_1"]["expireAfterSeconds"] == 0   # TTL index
    assert db["users"].find_one()["last_login_at"] is not None


def test_cookie_secure_khi_https(db):
    tao(db, "trang", "admin")
    c = client(base_url="https://testserver")
    r = c.post("/api/auth/login", json={"username": "trang", "password": MK}, headers={"Origin": "https://testserver"})
    assert "secure" in r.headers["set-cookie"].lower()


def test_loi_chung_chung_khong_lo_tai_khoan(db):
    tao(db, "trang", "admin")
    sai_mk = dang_nhap(client("5.5.5.5"), "trang", "sai-mat-khau-12")
    khong_co = dang_nhap(client("6.6.6.6"), "khong-ton-tai", "sai-mat-khau-12")
    assert (sai_mk.status_code, sai_mk.json()) == (khong_co.status_code, khong_co.json()) == (401, {"detail": {"code": "bad_credentials"}})


def test_tai_khoan_bi_khoa_cung_bao_loi_chung(db):
    u = tao(db, "trang", "admin")
    db["users"].update_one({"_id": u["_id"]}, {"$set": {"is_active": False}})
    assert dang_nhap(client(), "trang").json() == {"detail": {"code": "bad_credentials"}}


def test_khoa_sau_5_lan_sai_theo_username_va_ip(db):
    tao(db, "trang", "admin")
    c = client("9.9.9.9")
    ket_qua = [dang_nhap(c, "trang", "sai-mat-khau-12").status_code for _ in range(5)]
    assert ket_qua == [401, 401, 401, 401, 429]                 # lần thứ 5 kích hoạt khóa
    r = dang_nhap(c, "trang")                                    # đúng mật khẩu vẫn bị chặn trong lúc khóa
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0
    assert dang_nhap(client("8.8.8.8"), "trang").status_code == 200   # IP khác không bị khóa
    assert "9.9.9.9" not in str(list(db["login_attempts"].find()))    # không lưu IP thô


def test_khoa_ca_voi_username_khong_ton_tai(db):
    c = client("9.9.9.9")
    assert [dang_nhap(c, "ma", "sai-mat-khau-12").status_code for _ in range(5)][-1] == 429


def test_het_khoa_sau_15_phut(db):
    tao(db, "trang", "admin")
    c = client("9.9.9.9")
    for _ in range(5):
        dang_nhap(c, "trang", "sai-mat-khau-12")
    db["login_attempts"].update_many({}, {"$set": {"locked_until": utc_now() - timedelta(seconds=1)}})
    assert dang_nhap(c, "trang").status_code == 200


def test_khong_tin_x_forwarded_for(db):
    tao(db, "trang", "admin")
    c = client("9.9.9.9")
    for i in range(5):   # giả IP khác mỗi lần vẫn bị tính theo IP thật của kết nối
        c.post("/api/auth/login", json={"username": "trang", "password": "sai-mat-khau-12"},
               headers={**GOC, "X-Forwarded-For": f"10.0.0.{i}"})
    assert dang_nhap(c, "trang").status_code == 429


def test_phien_het_han_khong_hoat_dong_2_gio_va_toi_da_12_gio(db):
    c = dang_nhap_ok(db, "trang", "admin")
    assert c.get("/api/auth/me").status_code == 200
    db["admin_sessions"].update_many({}, {"$set": {"last_seen_at": utc_now() - timedelta(hours=2, minutes=1)}})
    assert c.get("/api/auth/me").status_code == 401
    c2 = client("7.7.7.7")
    dang_nhap(c2, "trang")
    db["admin_sessions"].update_many({}, {"$set": {"created_at": utc_now() - timedelta(hours=12, minutes=1)}})
    assert c2.get("/api/auth/me").status_code == 401


def test_dung_phien_gia_han_thoi_gian_khong_hoat_dong(db):
    c = dang_nhap_ok(db, "trang", "admin")
    db["admin_sessions"].update_many({}, {"$set": {"last_seen_at": utc_now() - timedelta(hours=1, minutes=50)}})
    assert c.get("/api/auth/me").status_code == 200
    assert utc_now() - db["admin_sessions"].find_one()["last_seen_at"] < timedelta(minutes=1)


def test_dang_xuat_xoa_phien(db):
    c = dang_nhap_ok(db, "trang", "admin")
    assert c.post("/api/auth/logout", headers=GOC).status_code == 200
    assert db["admin_sessions"].count_documents({}) == 0
    assert c.get("/api/auth/me").status_code == 401


# ---------- CSRF và Origin ----------

def test_ghi_bat_buoc_csrf_va_origin(db):
    c = dang_nhap_ok(db, "trang", "admin")
    thieu_csrf = TestClient(main.app, client=("1.2.3.4", 1), cookies=c.cookies)
    assert thieu_csrf.post("/api/auth/logout", headers=GOC).json()["detail"]["code"] == "csrf"
    sai_csrf = c.post("/api/auth/logout", headers={**GOC, "X-CSRF-Token": "sai"})
    assert sai_csrf.status_code == 403 and sai_csrf.json()["detail"]["code"] == "csrf"
    sai_origin = c.post("/api/auth/logout", headers={"Origin": "http://evil.example"})
    assert sai_origin.status_code == 403 and sai_origin.json()["detail"]["code"] == "origin"
    khong_origin = c.post("/api/auth/logout")
    assert khong_origin.status_code == 403
    assert c.get("/api/auth/me").status_code == 200   # GET không cần CSRF
    for phuong_thuc in ("put", "patch", "delete"):    # mọi phương thức ghi đều bị kiểm tra
        r = getattr(c, phuong_thuc)("/api/admin/users/x", headers={"Origin": "http://evil.example"})
        assert r.status_code in (403, 405)


def test_dang_nhap_kiem_origin(db):
    tao(db, "trang", "admin")
    r = client().post("/api/auth/login", json={"username": "trang", "password": MK}, headers={"Origin": "http://evil.example"})
    assert r.status_code == 403 and client().post("/api/auth/login", json={"username": "trang", "password": MK}).status_code == 403


# ---------- Đổi mật khẩu bắt buộc ----------

def test_phai_doi_mat_khau_lan_dau(db):
    tao(db, "moi", "viewer", doi_mk=True)
    c = client()
    assert dang_nhap(c, "moi").json()["must_change_password"] is True
    assert c.get("/api/admin/stats").json()["detail"]["code"] == "must_change_password"   # bị chặn mọi trang khác
    assert c.get("/api/auth/me").status_code == 200
    gui = lambda cu, moi: c.post("/api/auth/change-password", json={"current_password": cu, "new_password": moi}, headers=GOC)  # noqa: E731
    assert gui("sai-mat-khau-cu-1", "mat-khau-moi-12345").json()["detail"]["code"] == "bad_credentials"
    assert gui(MK, "ngan").json()["detail"]["code"] == "too_short"
    assert gui(MK, MK).json()["detail"]["code"] == "same_password"
    r = gui(MK, "mat-khau-moi-12345")
    assert r.status_code == 200 and r.json()["must_change_password"] is False
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    assert c.get("/api/admin/stats").status_code == 200
    assert dang_nhap(client("2.2.2.2"), "moi").status_code == 401 and dang_nhap(client("2.2.2.2"), "moi", "mat-khau-moi-12345").status_code == 200


def test_doi_mat_khau_dang_xuat_noi_khac(db):
    tao(db, "trang", "admin")
    a, b = client("1.1.1.1"), client("2.2.2.2")
    dang_nhap(a, "trang")
    dang_nhap(b, "trang")
    r = a.post("/api/auth/change-password", json={"current_password": MK, "new_password": "mat-khau-moi-12345"}, headers=GOC)
    assert r.status_code == 200
    assert b.get("/api/auth/me").status_code == 401   # phiên cũ ở nơi khác bị hủy


# ---------- Phân quyền ----------

def test_phan_quyen_theo_vai_tro(db):
    cac = {r: dang_nhap_ok(db, r, r, ip=f"3.3.3.{i}") for i, r in enumerate(("admin", "viewer", "rater"))}
    assert cac["admin"].get("/api/admin/stats").status_code == 200
    assert cac["viewer"].get("/api/admin/stats").status_code == 200
    assert cac["rater"].get("/api/admin/stats").json()["detail"]["code"] == "forbidden"
    assert cac["admin"].get("/api/admin/users").status_code == 200
    assert cac["viewer"].get("/api/admin/users").status_code == 403
    assert cac["rater"].get("/api/admin/users").status_code == 403
    assert client().get("/api/admin/stats").status_code == 401
    assert client().get("/api/admin/users").status_code == 401


def test_memory_van_dung_khoa_ingest(db, monkeypatch):
    from sparkmind import config
    monkeypatch.setattr(config, "INGEST_SECRET", "bi-mat")
    assert client().get("/api/admin/memory").status_code == 401
    assert client().get("/api/admin/memory", headers={"x-api-key": "bi-mat"}).status_code == 200


# ---------- Quét toàn bộ route: từ chối mặc định ----------

TIEN_TO_CAN_QUYEN = ("/api/admin", "/api/rate")


def co_kiem_quyen(dependant, deps_cha=()) -> bool:
    """True nếu route (hoặc dependency lồng nhau, hoặc dependency của router cha) có hàm đánh dấu _la_kiem_quyen."""
    if any(getattr(getattr(d, "dependency", None), "_la_kiem_quyen", False) for d in deps_cha):
        return True
    return any(getattr(d.call, "_la_kiem_quyen", False) or co_kiem_quyen(d) for d in dependant.dependencies)


def duyet_route(routes, tien_to="", deps_cha=()):
    """Trả (đường dẫn đầy đủ, route, dependency của router cha). FastAPI mới gộp router lười (_IncludedRouter, không có
    .path), nên phải đi vào original_router và tự cộng tiền tố; FastAPI cũ thì route đã phẳng. Cả hai đều được xử lý."""
    for r in routes:
        if hasattr(r, "original_router"):
            ctx = r.include_context
            yield from duyet_route(r.original_router.routes, tien_to + ctx.prefix, [*deps_cha, *ctx.dependencies])
        else:
            yield tien_to + getattr(r, "path", ""), r, deps_cha


def route_thieu_kiem_quyen(app) -> list:
    """Danh sách route /api/admin/* và /api/rate/* KHÔNG có kiểm tra quyền (kể cả mount hay loại route lạ)."""
    thieu = []
    for duong, r, deps_cha in duyet_route(app.routes):
        if not any(duong == t or duong.startswith(t + "/") for t in TIEN_TO_CAN_QUYEN):
            continue
        if not isinstance(r, APIRoute) or not co_kiem_quyen(r.dependant, deps_cha):
            thieu.append(duong)
    return thieu


def test_moi_route_admin_va_rate_deu_co_kiem_tra_quyen():
    assert route_thieu_kiem_quyen(main.app) == []
    cac_duong = {d for d, r, _ in duyet_route(main.app.routes) if isinstance(r, APIRoute) and d.startswith("/api/admin")}
    assert {"/api/admin/stats", "/api/admin/users", "/api/admin/memory"} <= cac_duong   # chắc chắn có quét được route


def test_bo_quet_bat_duoc_route_khong_co_quyen():
    app = FastAPI()
    r = APIRouter(prefix="/api/rate")
    r.add_api_route("/lo", lambda: {}, methods=["GET"])                     # quên kiểm tra quyền
    app.include_router(r)
    app.add_api_route("/api/admin/ok", lambda ctx=Depends(auth.require_role("admin")): {}, methods=["GET"])
    app.add_api_route("/api/admin/khong", lambda: {}, methods=["POST"])
    app.mount("/api/admin/tinh", FastAPI())                                  # mount lạ cũng bị coi là thiếu
    assert sorted(route_thieu_kiem_quyen(app)) == ["/api/admin/khong", "/api/admin/tinh", "/api/rate/lo"]


# ---------- Trang người dùng ----------

def test_admin_tao_doi_khoa_mo_va_nhat_ky(db):
    admin = dang_nhap_ok(db, "trang", "admin")
    r = admin.post("/api/admin/users", json={"username": "Cham1", "display_name": "Người chấm 1", "role": "rater"}, headers=GOC)
    assert r.status_code == 201
    tam = r.json()["temp_password"]
    assert len(tam) >= 12 and r.json()["user"]["must_change_password"] is True and "password_hash" not in r.text
    assert admin.post("/api/admin/users", json={"username": "x-admin", "role": "admin"}, headers=GOC).json()["detail"]["code"] == "bad_role"
    assert admin.post("/api/admin/users", json={"username": "cham1", "role": "viewer"}, headers=GOC).status_code == 409
    assert admin.post("/api/admin/users", json={"username": "yeu", "role": "viewer", "temp_password": "ngan"}, headers=GOC).status_code == 422
    ds = admin.get("/api/admin/users")
    assert "password_hash" not in ds.text and {u["username"] for u in ds.json()["users"]} == {"trang", "cham1"}
    assert all({"role", "last_login_at", "is_active"} <= set(u) for u in ds.json()["users"])
    moi = client("4.4.4.4")
    assert dang_nhap(moi, "cham1", tam).json()["must_change_password"] is True
    assert admin.patch("/api/admin/users/cham1", json={"is_active": False}, headers=GOC).json()["user"]["is_active"] is False
    assert moi.get("/api/auth/me").status_code == 401                     # khóa thì phiên bị hủy
    assert dang_nhap(client("4.4.4.5"), "cham1", tam).status_code == 401
    admin.patch("/api/admin/users/cham1", json={"is_active": True}, headers=GOC)
    dat = admin.post("/api/admin/users/cham1/reset-password", json={}, headers=GOC).json()["temp_password"]
    assert dang_nhap(client("4.4.4.6"), "cham1", tam).status_code == 401 and dang_nhap(client("4.4.4.6"), "cham1", dat).status_code == 200
    hanh_dong = [a["action"] for a in db["audit_log"].find().sort("at", 1)]
    for can in ("user_create", "user_lock", "user_unlock", "user_reset_password"):
        assert can in hanh_dong
    assert tam not in str(list(db["audit_log"].find())) and dat not in str(list(db["audit_log"].find()))


def test_khong_tu_khoa_minh_va_khong_khoa_admin_cuoi(db):
    admin = dang_nhap_ok(db, "trang", "admin")
    assert admin.patch("/api/admin/users/trang", json={"is_active": False}, headers=GOC).json()["detail"]["code"] == "cannot_lock_self"
    tao(db, "admin2", "admin")
    assert admin.patch("/api/admin/users/admin2", json={"is_active": False}, headers=GOC).status_code == 200   # còn admin khác
    # Hàng rào cuối cùng: khóa admin duy nhất còn hoạt động (do người khác, vd tài khoản đã bị khóa) thì bị từ chối
    from fastapi import HTTPException
    from server import admin_users
    nguoi_khac = {"_id": "khac"}
    with pytest.raises(HTTPException) as e:
        admin_users._kiem_tra_co_the_khoa(db, nguoi_khac, user_store.tim_user(db, "trang"), False)
    assert e.value.detail == {"code": "last_admin"}


def test_nguoi_dung_404_va_viewer_khong_quan_ly(db):
    admin = dang_nhap_ok(db, "trang", "admin")
    assert admin.patch("/api/admin/users/khong-co", json={"is_active": False}, headers=GOC).json()["detail"]["code"] == "user_not_found"
    viewer = dang_nhap_ok(db, "xem", "viewer", ip="5.5.5.5")
    assert viewer.post("/api/admin/users", json={"username": "abc", "role": "rater"}, headers=GOC).status_code == 403
    assert viewer.post("/api/admin/users/trang/reset-password", json={}, headers=GOC).status_code == 403
    assert viewer.patch("/api/admin/users/trang", json={"is_active": False}, headers=GOC).status_code == 403


def test_nhat_ky_chi_them_va_khong_ghi_bi_mat(db):
    u = tao(db, "trang", "admin")
    audit.write_audit(db, u, "thu", "users", u["_id"], {"password": "bi-mat", "password_hash": "x", "csrf_token": "y", "ok": 1})
    d = db["audit_log"].find_one()
    assert d["detail"] == {"ok": 1} and d["username"] == "trang" and d["collection"] == "users" and d["doc_id"] == str(u["_id"])
    cac_ham = [n for n in dir(audit) if not n.startswith("_")]
    assert not any(t in n for n in cac_ham for t in ("update", "delete", "remove", "sua", "xoa"))   # không có hàm sửa/xóa


def test_header_bao_mat_trang_quan_tri(db):
    for duong in ("/api/auth/me", "/admin/", "/api/admin/stats"):
        r = client().get(duong)
        assert "noindex" in r.headers["x-robots-tag"] and r.headers["cache-control"] == "no-store"
        assert r.headers["x-frame-options"] == "DENY" and "default-src 'self'" in r.headers["content-security-policy"]
    html = client().get("/admin/").text
    assert 'name="robots" content="noindex' in html and "<script>" not in html


def test_chu_giao_dien_du_ma_loi_va_khong_co_bi_mat():
    ui = client().get("/api/auth/ui").json()
    for ma in ("bad_credentials", "locked", "csrf", "forbidden", "must_change_password", "weak_password", "username_taken", "last_admin", "mang", "khac"):
        assert ma in ui["loi"]
    assert set(ui["vai_tro"]) == {"admin", "viewer", "rater"} and "403" in ui
