"""Kiểm tra trang Cài đặt và công tắc đóng/mở (phiên 4a): mặc định, từng công tắc, hết hạn tự đóng,
48 giờ nộp tiếp, quyền admin/viewer, audit_log, bộ nhớ đệm. Dùng DB giả (mongomock)."""
import sys
from datetime import timedelta
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from server import research, status_api  # noqa: E402
from sparkmind import config, research_store as kho, settings_store  # noqa: E402
from sparkmind.thoi_gian import utc_now  # noqa: E402
from tests.test_admin_auth import GOC, client as tao_client, dang_nhap_ok  # noqa: E402
from tests.test_game2 import client, nguoi_moi, nop, nop_game1  # noqa: E402,F401
from tests.test_game3 import bat_dau as bat_dau_g3, nop3  # noqa: E402
from tests.test_progress import nop_hanh_vi, nop_tu_danh_gia, tien_do  # noqa: E402
from tests.test_research import BAT_DAU  # noqa: E402

DEMO = {"answers": {f"B4_{i}": 3 for i in range(1, 8)}}
CAI_DAT = "/api/admin/settings"


def dat_cai_dat(db, **gia_tri):
    """Ghi thẳng tài liệu cài đặt (như thể quản trị đã lưu) rồi xóa bộ nhớ đệm."""
    db["settings"].replace_one({"_id": "chung"}, {"_id": "chung", **gia_tri}, upsert=True)
    settings_store.xoa_cache()


def dong_tu(db, gio_truoc):
    """Hướng 2 đã đóng cách đây `gio_truoc` giờ."""
    dat_cai_dat(db, huong2_mo=False, huong2_dong_luc=utc_now() - timedelta(hours=gio_truoc))


def body(**sua):
    return {"huong2_mo": True, "huong1_web_mo": False, "demo_mo": True, "han_dong_huong2": None, "thong_bao": None, **sua}


# ---------- Mặc định ----------

def test_khong_co_tai_lieu_dung_mac_dinh(client):
    c, db = client
    assert db["settings"].count_documents({}) == 0
    d = c.get("/api/status").json()
    assert d == {"huong2_mo": True, "huong1_web_mo": False, "demo_mo": True, "thong_bao": None}   # hướng 1 web mặc định ĐÓNG
    assert config.HUONG2_GIA_HAN_GIO == 48 and config.CAI_DAT_NHO_DEM_GIAY <= 10


def test_status_cong_khai_khong_lo_chi_tiet_noi_bo(client):
    c, db = client
    dat_cai_dat(db, huong2_mo=False, huong2_dong_luc=utc_now(), cap_nhat_boi="trang", thong_bao="Bảo trì tối nay")
    r = c.get("/api/status")
    assert set(r.json()) == {"huong2_mo", "huong1_web_mo", "demo_mo", "thong_bao"} and "trang" not in r.text
    assert r.json()["huong2_mo"] is False and r.json()["thong_bao"] == "Bảo trì tối nay"


# ---------- Công tắc hướng 2 ----------

def test_dong_huong2_nguoi_moi_bi_chan_nguoi_dang_lam_van_tiep_tuc(client):
    c, db = client
    ma_moi = kho.tao_ma_moi(db, 1, "volunteer")[0]
    t = nguoi_moi(c, db)                                       # người đã bắt đầu (có phiên)
    dong_tu(db, 1)
    r = c.post("/api/research/code/check", json={"code": ma_moi})
    assert r.status_code == 423 and "đóng" in r.json()["detail"]
    assert c.post("/api/research/code/check", json={"code": "SAIMA123"}).status_code == 423   # mã sai cũng 423: không lộ mã nào đúng
    assert c.post("/api/research/start", json={"code": ma_moi, **BAT_DAU}).status_code == 423
    assert nop_hanh_vi(c, t).status_code == 200                # người đang làm dở vẫn nộp được
    assert tien_do(c, t)["next"] == "self_assessment"
    assert nop_tu_danh_gia(c, t).status_code == 200


def test_nguoi_dung_do_nhap_lai_ma_van_vao_duoc_trong_48_gio(client):
    c, db = client
    ma = kho.tao_ma_moi(db, 1, "volunteer")[0]
    assert c.post("/api/research/start", json={"code": ma, **BAT_DAU}).status_code == 200
    dong_tu(db, 47)
    assert c.post("/api/research/code/check", json={"code": ma}).json() == {"valid": False, "can_resume": True}
    assert c.post("/api/research/start", json={"code": ma, **BAT_DAU}).status_code == 200   # cùng email: vào lại cùng phiên
    dong_tu(db, 49)
    assert c.post("/api/research/code/check", json={"code": ma}).status_code == 423
    assert c.post("/api/research/start", json={"code": ma, **BAT_DAU}).status_code == 423


def test_het_48_gio_nguoi_dang_lam_bi_chan_nguoi_hoan_thanh_van_xem_ket_qua(client):
    c, db = client
    t_do, t_xong = nguoi_moi(c, db), nguoi_moi(c, db)
    nop_hanh_vi(c, t_xong); nop_tu_danh_gia(c, t_xong); nop_game1(c, t_xong); nop(c, t_xong, []); bat_dau_g3(c, t_xong); nop3(c, t_xong)
    assert db["participants"].find_one({"session_token": t_xong})["completed_at"]
    dong_tu(db, 47)
    assert nop_hanh_vi(c, t_do).status_code == 200            # trong 48 giờ: nộp được
    dong_tu(db, 49)
    assert nop_tu_danh_gia(c, t_do).status_code == 423        # quá 48 giờ: bị chặn
    assert c.get("/api/research/progress", headers={"X-Session-Token": t_do}).status_code == 423
    assert c.post("/api/research/game1/start", json={"session_token": t_do}).status_code == 423
    assert c.get("/api/research/result", headers={"X-Session-Token": t_xong}).status_code == 200   # đã hoàn thành: vẫn xem kết quả


def test_het_han_dong_tu_dong_va_48_gio_tinh_tu_han(client):
    c, db = client
    ma = kho.tao_ma_moi(db, 1, "volunteer")[0]
    dat_cai_dat(db, huong2_mo=True, han_dong_huong2=utc_now() + timedelta(hours=1))
    assert c.post("/api/research/code/check", json={"code": ma}).json()["valid"] is True      # chưa tới hạn: mở
    dat_cai_dat(db, huong2_mo=True, han_dong_huong2=utc_now() - timedelta(minutes=1))
    assert c.post("/api/research/code/check", json={"code": ma}).status_code == 423           # quá hạn: tự đóng dù công tắc còn bật
    assert c.get("/api/status").json()["huong2_mo"] is False
    han = utc_now() - timedelta(hours=49)
    dat_cai_dat(db, huong2_mo=True, han_dong_huong2=han)
    tt = settings_store.trang_thai(db)
    assert tt["huong2_het_gia_han"] is True and tt["huong2_dong_luc"] == han                  # 48 giờ tính từ hạn


# ---------- Công tắc demo và hướng 1 web ----------

def test_demo_tat_chi_demo_bi_chan(client):
    c, db = client
    assert c.post("/api/predict/demo", json=DEMO).status_code == 200
    dat_cai_dat(db, demo_mo=False)
    r = c.post("/api/predict/demo", json=DEMO)
    assert r.status_code == 423 and "demo" in r.json()["detail"].lower()
    assert c.post("/api/research/code/check", json={"code": "ABCDEFGH"}).status_code == 200   # hướng 2 không bị ảnh hưởng


def test_huong2_dong_demo_van_chay(client):
    c, db = client
    dong_tu(db, 100)
    assert c.post("/api/predict/demo", json=DEMO).status_code == 200


def test_duong_vao_huong1_web_mac_dinh_chua_mo(client):
    _, db = client
    app = FastAPI()
    app.add_api_route("/vao", lambda _=Depends(status_api.yeu_cau_huong1_web_mo): {"ok": True}, methods=["GET"])
    app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: db
    c = TestClient(app)
    assert c.get("/vao").status_code == 423                    # mặc định FALSE
    dat_cai_dat(db, huong1_web_mo=True)
    assert c.get("/vao").status_code == 200
    dat_cai_dat(db, huong1_web_mo=False, huong2_mo=False, huong2_dong_luc=utc_now())
    assert c.get("/vao").status_code == 423                    # công tắc hướng 2 không liên quan


# ---------- Bộ nhớ đệm ----------

def test_bo_nho_dem_ngan(client, monkeypatch):
    _, db = client
    assert settings_store.lay_cai_dat(db)["demo_mo"] is True
    db["settings"].replace_one({"_id": "chung"}, {"_id": "chung", "demo_mo": False}, upsert=True)   # tiến trình khác vừa đổi
    assert settings_store.lay_cai_dat(db)["demo_mo"] is True   # trong thời gian nhớ vẫn thấy giá trị cũ
    monkeypatch.setattr(config, "CAI_DAT_NHO_DEM_GIAY", 0)     # hết thời gian nhớ
    assert settings_store.lay_cai_dat(db)["demo_mo"] is False


# ---------- Trang quản trị: quyền, audit ----------

def test_quyen_xem_va_sua(client):
    _, db = client
    admin, viewer = dang_nhap_ok(db, "trang", "admin", "5.5.5.1"), dang_nhap_ok(db, "xem", "viewer", "5.5.5.2")
    assert admin.get(CAI_DAT).status_code == 200 and viewer.get(CAI_DAT).status_code == 200
    assert admin.put(CAI_DAT, json=body(demo_mo=False), headers=GOC).status_code == 200
    r = viewer.put(CAI_DAT, json=body(demo_mo=True), headers=GOC)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "forbidden"
    assert settings_store.doc_cai_dat(db)["demo_mo"] is False  # viewer không đổi được
    assert tao_client("5.5.5.3").put(CAI_DAT, json=body(), headers=GOC).status_code == 401
    rater = dang_nhap_ok(db, "cham", "rater", "5.5.5.4")
    assert rater.get(CAI_DAT).status_code == 403 and rater.put(CAI_DAT, json=body(), headers=GOC).status_code == 403
    assert admin.put(CAI_DAT, json=body()).status_code == 403   # thiếu Origin (CSRF)


def test_luu_ghi_audit_cu_moi_va_co_hieu_luc_ngay(client):
    c, db = client
    admin = dang_nhap_ok(db, "trang", "admin")
    r = admin.put(CAI_DAT, json=body(huong2_mo=False, thong_bao="  Bảo trì  "), headers=GOC)
    assert r.status_code == 200 and sorted(r.json()["thay_doi"]) == ["huong2_mo", "thong_bao"]
    assert r.json()["hieu_luc"]["huong2_dang_mo"] is False and r.json()["hieu_luc"]["huong2_dong_luc"]
    assert c.get("/api/status").json() == {"huong2_mo": False, "huong1_web_mo": False, "demo_mo": True, "thong_bao": "Bảo trì"}   # có hiệu lực ngay (đệm đã xóa)
    a = db["audit_log"].find_one({"action": "settings_update"})
    assert a["username"] == "trang" and a["role"] == "admin" and a["at"] and a["collection"] == "settings"
    assert a["detail"]["thay_doi"]["huong2_mo"] == {"cu": True, "moi": False}
    assert a["detail"]["thay_doi"]["thong_bao"] == {"cu": None, "moi": "Bảo trì"}


def test_khong_doi_khong_ghi_audit_va_mo_lai_xoa_moc_dong(client):
    _, db = client
    admin = dang_nhap_ok(db, "trang", "admin")
    admin.put(CAI_DAT, json=body(), headers=GOC)
    assert db["audit_log"].count_documents({"action": "settings_update"}) == 0
    admin.put(CAI_DAT, json=body(huong2_mo=False), headers=GOC)
    assert db["settings"].find_one()["huong2_dong_luc"] is not None
    admin.put(CAI_DAT, json=body(huong2_mo=True), headers=GOC)
    assert db["settings"].find_one()["huong2_dong_luc"] is None and db["audit_log"].count_documents({"action": "settings_update"}) == 2


def test_han_dong_doi_mui_gio_sang_utc_va_kiem_tra_dau_vao(client):
    _, db = client
    admin = dang_nhap_ok(db, "trang", "admin")
    r = admin.put(CAI_DAT, json=body(han_dong_huong2="2026-12-20T23:59:00+07:00"), headers=GOC)
    assert r.status_code == 200 and db["settings"].find_one()["han_dong_huong2"].isoformat() == "2026-12-20T16:59:00"
    dai = admin.put(CAI_DAT, json=body(thong_bao="x" * (config.CAI_DAT_THONG_BAO_TOI_DA + 1)), headers=GOC)
    assert dai.status_code == 422 and dai.json()["detail"]["code"] == "thong_bao_dai"
    assert admin.put(CAI_DAT, json={"huong2_mo": "abc"}, headers=GOC).status_code == 422


def test_audit_chi_chua_thay_doi(client):
    _, db = client
    admin = dang_nhap_ok(db, "trang", "admin")
    admin.put(CAI_DAT, json=body(demo_mo=False), headers=GOC)
    chi_tiet = db["audit_log"].find_one({"action": "settings_update"})["detail"]
    assert set(chi_tiet) == {"thay_doi"} and set(chi_tiet["thay_doi"]) == {"demo_mo"}
