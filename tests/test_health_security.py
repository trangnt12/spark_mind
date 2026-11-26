"""Kiểm tra phiên 4b: trang Sức khỏe (không lộ khóa) và các sửa lỗi nhỏ từ rà soát bảo mật (docs/security_review.md).
Dùng DB giả (mongomock); không chạm MongoDB thật."""
import json
import re
import sys
from pathlib import Path

import mongomock
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

GOC_DU_AN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC_DU_AN))
sys.path.insert(0, str(GOC_DU_AN / "src"))
from test_admin_auth import duyet_route  # noqa: E402  (bộ duyệt route chịu được router gộp lười của FastAPI mới)
from server import headers, landing_page, main, research  # noqa: E402
from sparkmind import audit, config, game_store, health, passwords, rating_store, research_store, security, session_store, settings_store, user_store  # noqa: E402

MK = "mat-khau-dai-12-ky-tu"
GOC = {"Origin": "http://testserver"}
WEB = GOC_DU_AN / "web"


@pytest.fixture
def db():
    d = mongomock.MongoClient().spark_mind
    for ham in (research_store.tao_chi_muc, game_store.tao_chi_muc_game, user_store.tao_chi_muc_user,
                session_store.tao_chi_muc_phien, audit.tao_chi_muc_audit, rating_store.tao_chi_muc_cham):
        ham(d)
    main.app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: d
    health.xoa_cache()
    settings_store.xoa_cache()
    yield d
    main.app.dependency_overrides.clear()
    health.xoa_cache()


def dang_nhap(db, ten, role):
    user_store.tao_user(db, ten, ten.title(), role, MK, "test", bat_buoc_doi_mk=False)
    c = TestClient(main.app, client=("1.2.3.4", 50000))
    r = c.post("/api/auth/login", json={"username": ten, "password": MK}, headers=GOC)
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return c


# ---------- Trang Sức khỏe ----------

def test_suc_khoe_admin_va_viewer_xem_duoc_rater_va_khach_khong(db):
    assert dang_nhap(db, "trang", "admin").get("/api/admin/health").status_code == 200
    assert dang_nhap(db, "xem", "viewer").get("/api/admin/health").status_code == 200
    assert dang_nhap(db, "cham", "rater").get("/api/admin/health").status_code == 403
    assert TestClient(main.app).get("/api/admin/health").status_code == 401


def test_suc_khoe_co_du_cac_phan(db):
    db["access_codes"].insert_one({"_id": 1, "code": "ABC"})
    d = dang_nhap(db, "trang", "admin").get("/api/admin/health").json()
    assert d["ket_noi"]["ok"] and d["ket_noi"]["do_tre_ms"] >= 0 and d["ket_noi"]["ten_db"] == "spark_mind"
    assert d["tien_trinh"]["rss_mb"] > 0 and d["tien_trinh"]["python"]
    assert d["mo_hinh"]["ok"] and d["mo_hinh"]["phien_ban"]
    assert {"nhap_ma", "tim_nguoi_theo_token", "dang_nhap_quan_tri", "cai_dat"} == {q["ten"] for q in d["truy_van"]}
    assert all(q["ok"] and q["ms"] >= 0 for q in d["truy_van"])
    assert {"ten": "access_codes", "so_ban_ghi": 1} in d["ban_ghi"]
    assert d["cong_tac"] == {"huong2_mo": True, "huong1_web_mo": False, "demo_mo": True, "co_thong_bao": False}   # mặc định


def test_chi_muc_du_khi_da_tao_va_bao_thieu_khi_chua_tao(db):
    assert health.kiem_tra_chi_muc(db)["thieu"] == 0
    trong = mongomock.MongoClient().khac
    kq = health.kiem_tra_chi_muc(trong)
    assert kq["thieu"] == len(health.CHI_MUC_BAT_BUOC) and not any(c["co"] for c in kq["chi_tiet"])


def test_chi_muc_khong_unique_thi_bi_coi_la_thieu():
    d2 = mongomock.MongoClient().khac2
    d2["access_codes"].create_index("code")          # có chỉ mục nhưng KHÔNG unique: sai so với yêu cầu
    chi = {(c["collection"], c["truong"]): c["co"] for c in health.kiem_tra_chi_muc(d2)["chi_tiet"]}
    assert chi[("access_codes", "code")] is False


def test_cong_tac_phan_anh_cai_dat(db):
    db["settings"].insert_one({"_id": "chung", "demo_mo": False, "huong1_web_mo": True, "thong_bao": "Bảo trì"})
    settings_store.xoa_cache()
    assert health.cong_tac(db) == {"huong2_mo": True, "huong1_web_mo": True, "demo_mo": False, "co_thong_bao": True}


def test_suc_khoe_khong_lo_khoa_hay_chuoi_ket_noi(db, monkeypatch):
    monkeypatch.setattr(config, "MONGODB_URI", "mongodb+srv://nguoi:matkhau-that@cluster0.abc.mongodb.net")
    monkeypatch.setattr(config, "INGEST_SECRET", "khoa-ingest-bi-mat")
    monkeypatch.setattr(config, "IP_HASH_SECRET", "khoa-bam-ip-bi-mat")
    r = dang_nhap(db, "trang", "admin").get("/api/admin/health")
    for bi_mat in ("matkhau-that", "khoa-ingest-bi-mat", "khoa-bam-ip-bi-mat", "mongodb+srv", "cluster0"):
        assert bi_mat not in r.text
    assert r.json()["cau_hinh"] == {"MONGODB_URI": True, "INGEST_SECRET": True, "IP_HASH_SECRET": True}   # chỉ true/false


def test_mat_ket_noi_chi_bao_ten_loi_khong_lo_noi_dung_loi():
    class DbHong:
        name = "spark-mind"

        def command(self, *_):
            raise ConnectionError("mongodb+srv://nguoi:matkhau-that@host: timeout")

    kq = health.tinh_suc_khoe(DbHong())
    assert kq["ket_noi"] == {"ok": False, "do_tre_ms": None, "ten_db": "spark-mind", "loi": "ConnectionError"}
    assert "matkhau-that" not in str(kq) and "ban_ghi" not in kq and "chi_muc" not in kq   # không hỏi tiếp database đã mất


def test_ket_qua_duoc_nho_ngan(db, monkeypatch):
    so_lan = []
    goc = health.tinh_suc_khoe
    monkeypatch.setattr(health, "tinh_suc_khoe", lambda d: so_lan.append(1) or goc(d))
    a, b = health.lay_suc_khoe(db), health.lay_suc_khoe(db)
    assert a is b and len(so_lan) == 1
    health.xoa_cache()
    health.lay_suc_khoe(db)
    assert len(so_lan) == 2


def test_trang_suc_khoe_co_trong_menu_va_chu_giao_dien():
    ui = json.loads((GOC_DU_AN / "content" / "admin_ui.json").read_text(encoding="utf-8"))
    assert ui["dieu_huong"]["suc_khoe"] and ui["suc_khoe"]["tieu_de"]
    assert '"/health"' in (WEB / "admin" / "js" / "app.js").read_text(encoding="utf-8")
    assert "page-health.js" in (WEB / "admin" / "index.html").read_text(encoding="utf-8")
    ma = (WEB / "admin" / "js" / "page-health.js").read_text(encoding="utf-8")
    cac_khoa = set(re.findall(r"\bt\.([a-z_0-9]+)", ma))
    assert cac_khoa <= set(ui["suc_khoe"]), cac_khoa - set(ui["suc_khoe"])   # chữ nào dùng cũng có trong file nội dung


# ---------- Tiêu đề bảo mật ----------

@pytest.mark.parametrize("duong", ["/", "/huong-1", "/play/", "/health", "/play/app.js"])
def test_trang_cong_khai_co_tieu_de_bao_mat(duong):
    h = TestClient(main.app).get(duong).headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in h["content-security-policy"] and "script-src 'self'" in h["content-security-policy"]
    assert "strict-transport-security" not in h              # HTTP thường (máy dev) thì chưa có HSTS


def test_https_co_hsts():
    r = TestClient(main.app, base_url="https://testserver").get("/health")
    assert r.headers["strict-transport-security"].startswith("max-age=")


def test_trang_quan_tri_giu_header_chat_hon():
    r = TestClient(main.app).get("/api/auth/ui")
    assert r.headers["cache-control"] == "no-store" and r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["content-security-policy"] == headers.CSP_QUAN_TRI and "noindex" in r.headers["x-robots-tag"]
    assert r.headers["x-content-type-options"] == "nosniff"


def test_csp_cong_khai_khop_voi_trang_web_thuc_te():
    """CSP chỉ cho script cùng nguồn: mọi script nhúng phải có mã băm trong CSP, không có on...= nhúng, không nạp gì từ nơi lạ ngoài Google Fonts."""
    csp = headers.CSP_CONG_KHAI
    for html in WEB.glob("*.html"):
        ma = html.read_text(encoding="utf-8")
        for noi_dung in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", ma, re.S):
            assert headers.bam_script(noi_dung) in csp, f"{html.name}: script nhúng không có trong CSP"
        assert not re.search(r"\son[a-z]+\s*=\s*[\"']", ma), f"{html.name}: có thuộc tính sự kiện nhúng"
        for url in re.findall(r"<(?:script|link|img|iframe)[^>]*\b(?:src|href)=\"(https?://[^\"/]+)", ma):
            assert url in ("https://fonts.googleapis.com", "https://fonts.gstatic.com"), f"{html.name}: nạp từ {url}"
    assert f">{headers.SCRIPT_NHUNG_SURVEY1}</script>" in (WEB / "survey1.html").read_text(encoding="utf-8")


# ---------- XSS: dữ liệu người chơi nhập chỉ được đưa vào trang bằng textContent ----------

def test_giao_dien_khong_chen_html_tu_du_lieu():
    """Cấm innerHTML/outerHTML/document.write/eval trong mọi JS; insertAdjacentHTML chỉ còn ở game1.js (vẽ vòng đồng hồ bằng chuỗi cố định)."""
    insert = set()
    for js in list(WEB.glob("*.js")) + list((WEB / "admin" / "js").glob("*.js")):
        ma = js.read_text(encoding="utf-8")
        assert not re.search(r"\.(innerHTML|outerHTML)\s*=|document\.write|\beval\(|new Function\(", ma), js.name
        if "insertAdjacentHTML" in ma:
            insert.add(js.name)
            assert "'<svg" in ma and not re.search(r"insertAdjacentHTML\([^)]*(\+\s*[a-zA-Z_]|\$\{)", ma)   # chỉ chuỗi cố định, không ghép biến
    assert insert == {"game1.js"}


def test_trang_chu_thoat_ky_tu_dac_biet_trong_the_meta(monkeypatch):
    nd = {"meta": {"trang_chu": {"title": 'a"><script>alert(1)</script>', "description": "<b>x</b>", "og_title": "t", "og_description": "d"}}}
    monkeypatch.setattr(landing_page, "doc_noi_dung", lambda ten: nd)
    ma = landing_page.ve_trang("landing.html", "trang_chu").body.decode()
    assert "<script>alert(1)" not in ma and "&lt;script&gt;alert(1)" in ma


def test_noi_dung_nguoi_choi_tra_ve_dang_json_khong_bi_doan_thanh_html(db):
    """Nội dung chứa thẻ script trả ra qua API quản trị: là JSON (không phải HTML) và có nosniff nên trình duyệt không thực thi."""
    db["participants"].insert_one({"_id": "p1", "school_name": "<script>alert(1)</script>", "email": "a@b.vn", "code_id": "c"})
    r = dang_nhap(db, "trang", "admin").get("/api/admin/data/participants/p1")
    assert r.status_code == 200 and "<script>" in r.text   # nội dung giữ nguyên dạng chữ
    assert r.headers["content-type"].startswith("application/json") and r.headers["x-content-type-options"] == "nosniff"


# ---------- Kích thước body ----------

def test_body_qua_lon_bi_tu_choi_413(monkeypatch):
    monkeypatch.setattr(config, "BODY_TOI_DA_BYTE", 1000)
    c = TestClient(main.app)
    r = c.post("/api/predict/demo", content=b"x" * 1001, headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    nho = c.post("/api/predict/demo", content=b'{"answers": {}}', headers={"Content-Type": "application/json"})
    assert nho.status_code != 413                      # body nhỏ vẫn đi qua như bình thường


def test_body_chunked_vuot_gioi_han_cung_bi_chan(monkeypatch):
    monkeypatch.setattr(config, "BODY_TOI_DA_BYTE", 1000)
    khoi = (b"x" * 400 for _ in range(10))              # không có Content-Length (gửi từng khối)
    r = TestClient(main.app).post("/api/predict/demo", content=khoi, headers={"Content-Type": "application/json"})
    assert r.status_code in (400, 413)


def test_get_khong_bi_gioi_han_body(monkeypatch):
    monkeypatch.setattr(config, "BODY_TOI_DA_BYTE", 10)
    assert TestClient(main.app).get("/health").status_code == 200


# ---------- Tài liệu API tự sinh, khóa ingest, giới hạn tốc độ ----------

@pytest.mark.parametrize("duong", ["/docs", "/redoc", "/openapi.json"])
def test_tai_lieu_api_tat_mac_dinh(duong):
    assert not config.BAT_TAI_LIEU_API
    assert TestClient(main.app).get(duong).status_code == 404


def test_khoa_ingest_khong_phai_ascii_tra_401_khong_phai_500(monkeypatch):
    monkeypatch.setattr(config, "INGEST_SECRET", "bi-mat")
    c = TestClient(main.app, raise_server_exceptions=False)
    r = c.get("/api/admin/memory", headers=[(b"x-api-key", "kh\xf3a".encode("latin-1"))])
    assert r.status_code == 401


def test_gioi_han_toc_do_khong_phinh_bo_nho_va_doc_khong_tao_khoa():
    g = security.GioiHanTocDo(toi_da=3, giay=60)
    assert g.giay_phai_cho("chua-tung-thay", 0) == 0 and "chua-tung-thay" not in g._lan   # chỉ đọc thì không tạo khóa
    for i in range(500):
        g.cho_phep(f"ip{i}", bay_gio=float(i % 50 + 100))
    assert len(g._lan) == 500
    g.cho_phep("moi", bay_gio=1000.0)                    # rất lâu sau: các khóa cũ đều hết hạn và bị dọn
    assert list(g._lan) == ["moi"]


def test_gioi_han_toc_do_van_dung_sau_khi_don():
    g = security.GioiHanTocDo(toi_da=2, giay=60)
    assert [g.cho_phep("a", t) for t in (100.0, 101.0, 102.0)] == [True, True, False]
    assert g.giay_phai_cho("a", 130.0) == 30
    assert g.cho_phep("a", 161.0)                          # lần đầu đã hết hạn


# ---------- Dữ liệu theo người: không có đường vào bằng id do client gửi ----------

def test_route_nguoi_choi_khong_nhan_id_nguoi_khac_tu_client():
    """Mọi route /api/research/* xác định người chơi CHỈ bằng token phiên: không có tham số đường dẫn hay truy vấn kiểu id/participant."""
    so_route = 0
    for duong, r, _ in duyet_route(main.app.routes):
        if isinstance(r, APIRoute) and duong.startswith("/api/research"):
            so_route += 1
            assert "{" not in duong, duong
            ten = [p.name for p in r.dependant.query_params + r.dependant.path_params]
            assert not [t for t in ten if "id" in t.lower() or "participant" in t.lower()], (duong, ten)
    assert so_route >= 10


def test_mat_khau_quan_tri_toi_thieu_12_ky_tu():
    assert passwords.kiem_tra_do_manh("a" * 11) == "too_short" and passwords.kiem_tra_do_manh(MK) is None
