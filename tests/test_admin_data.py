"""Kiểm tra trang dữ liệu quản trị (registry), nhãn dữ liệu, migration và xóa dữ liệu thử. Dùng DB giả (mongomock)."""
import csv
import io
import sys
from datetime import timedelta
from pathlib import Path

import mongomock
import pytest
from bson import ObjectId
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from server import main, research  # noqa: E402
from sparkmind import admin_registry as reg, admin_view, config, data_label, du_lieu_thu, research_store as kho, user_store  # noqa: E402
from sparkmind.thoi_gian import utc_now  # noqa: E402
from test_admin_auth import duyet_route  # noqa: E402

MK = "mat-khau-dai-12-ky-tu"
GOC = {"Origin": "http://testserver"}
EMAIL = "trang.bi.mat@gmail.com"


@pytest.fixture
def db():
    d = mongomock.MongoClient().spark_mind
    user_store.tao_chi_muc_user(d)
    main.app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: d
    yield d
    main.app.dependency_overrides.clear()


def vao(db, role, ip="1.2.3.4"):
    user_store.tao_user(db, role + "1", "x", role, MK, "test", bat_buoc_doi_mk=False)
    c = TestClient(main.app, client=(ip, 5))
    r = c.post("/api/auth/login", json={"username": role + "1", "password": MK}, headers=GOC)
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return c


@pytest.fixture
def admin(db):
    return vao(db, "admin", "10.0.0.1")


@pytest.fixture
def viewer(db):
    return vao(db, "viewer", "10.0.0.2")


def nap_nguoi(db, label="that", email=EMAIL, source="volunteer"):
    ma = db["access_codes"].insert_one({"code": f"AB{ObjectId()}"[:8].upper(), "source": source, "is_used": True, "data_label": label}).inserted_id
    return db["participants"].insert_one({
        "code_id": ma, "source": source, "data_label": label, "email": email, "grade": "3", "gender": "1", "school_name": "Trường A",
        "consent": True, "guardian_consent": True, "ip_hash": "0123456789abcdef0123", "user_agent": "Mozilla/UA-BI-MAT",
        "session_token": "TOKEN-BI-MAT", "started_at": utc_now()}).inserted_id


# ---------- Registry và route ----------

def test_registry_nhat_quan_va_co_du_bang():
    assert reg.kiem_tra_registry() == []
    assert {"survey_form1", "survey_clean", "access_codes", "participants", "behavior_answers", "self_assessment",
            "game_responses", "scores", "schools", "audit_log"} <= set(reg.BANG)
    assert "users" not in reg.BANG and "admin_sessions" not in reg.BANG and "login_attempts" not in reg.BANG
    assert {t for t, b in reg.BANG.items() if b["che_do"] == "crud"} == {"access_codes"}


def test_route_dung_theo_registry_va_khong_co_xoa_ca_bang():
    cac = {}
    for duong, r, _ in duyet_route(main.app.routes):
        if isinstance(r, APIRoute) and duong.startswith("/api/admin/data/"):
            for m in r.methods:
                cac.setdefault(duong, set()).add(m)
    for ten, cfg in reg.BANG.items():
        ghi = cac.get(f"/api/admin/data/{ten}", set())
        chi_tiet = cac[f"/api/admin/data/{ten}/{{id_}}"]
        assert ("POST" in ghi) == (cfg["che_do"] == "crud")                      # chỉ bảng crud mới có POST
        assert ("PATCH" in chi_tiet) == (cfg["che_do"] == "crud")                # bảng readonly KHÔNG có PATCH
        assert ("DELETE" in chi_tiet) == bool(cfg["quyen"]["xoa"])
        assert "DELETE" not in ghi and "PATCH" not in ghi and "PUT" not in ghi   # không có xóa/sửa cả bảng
    assert "DELETE" not in cac["/api/admin/data/survey_form1/{id_}"]            # dữ liệu gốc không xóa được
    for duong, ms in cac.items():
        assert "{id_}" in duong or ms <= {"GET", "POST"}                         # không route nào xóa/sửa ở cấp bảng


def test_patch_bang_readonly_405(db, admin):
    pid = nap_nguoi(db)
    assert admin.patch(f"/api/admin/data/participants/{pid}", json={"grade": "5"}, headers=GOC).status_code == 405
    assert admin.post("/api/admin/data/participants", json={"grade": "5"}, headers=GOC).status_code == 405
    assert db["participants"].find_one({"_id": pid})["grade"] == "3"


def test_phan_quyen_trang_du_lieu(db, admin, viewer):
    rater = vao(db, "rater", "10.0.0.3")
    pid = nap_nguoi(db)
    assert TestClient(main.app).get("/api/admin/data").status_code == 401
    assert rater.get("/api/admin/data").status_code == 403 and rater.get("/api/admin/data/participants").status_code == 403
    assert viewer.get("/api/admin/data/participants").status_code == 200
    assert viewer.delete(f"/api/admin/data/participants/{pid}?confirm={pid}", headers=GOC).status_code == 403
    assert viewer.post("/api/admin/data/access_codes", json={"code": "ABCDEF12"}, headers=GOC).status_code == 403
    assert viewer.get("/api/admin/data/audit_log").status_code == 403            # nhật ký chỉ admin
    assert admin.get("/api/admin/data/audit_log").status_code == 200
    assert {b["khoa"] for b in viewer.get("/api/admin/data").json()["bang"]} == set(reg.BANG) - {"audit_log"}
    assert viewer.get("/api/admin/test-data").status_code == 403 and viewer.post("/api/admin/test-data/delete", json={"confirm": "XOA"}, headers=GOC).status_code == 403


def test_meta_theo_vai_tro(admin, viewer):
    ma_a = {b["khoa"]: b for b in admin.get("/api/admin/data").json()["bang"]}
    ma_v = {b["khoa"]: b for b in viewer.get("/api/admin/data").json()["bang"]}
    assert ma_a["participants"]["quyen"] == {"doc": True, "xuat": True, "ghi": False, "xoa": True}
    assert ma_v["participants"]["quyen"] == {"doc": True, "xuat": True, "ghi": False, "xoa": False}
    assert ma_a["access_codes"]["quyen"]["ghi"] is True and ma_v["access_codes"]["quyen"]["ghi"] is False
    assert ma_a["survey_form1"]["quyen"]["xoa"] is False


# ---------- Danh sách: phân trang, tìm kiếm, lọc, sắp xếp ----------

def nap_clean(db, n=30):
    for i in range(n):
        db["survey_clean"].insert_one({"_id": f"id{i:03d}", "thoi_gian": utc_now() - timedelta(minutes=i), "nguon": "google_form" if i % 2 else "web",
                                       "dot": "dot4", "muc": ["Thap", "Trung_binh", "Cao"][i % 3], "diem_sang_tao": float(i),
                                       "truong_chuan": f"Trường số {i}", "in_chat": i % 2 == 0, "data_label": "that"})


def test_phan_trang_dung(db, admin):
    nap_clean(db, 30)
    t1 = admin.get("/api/admin/data/survey_clean?size=10&sort=diem_sang_tao&order=asc").json()
    assert (t1["tong"], t1["so_trang"], t1["trang"], len(t1["dong"])) == (30, 3, 1, 10)
    t3 = admin.get("/api/admin/data/survey_clean?size=10&page=3&sort=diem_sang_tao&order=asc").json()
    assert [d["diem_sang_tao"] for d in t3["dong"]] == [float(i) for i in range(20, 30)]
    tat_ca = {d["_id"] for p in (1, 2, 3) for d in admin.get(f"/api/admin/data/survey_clean?size=10&page={p}&sort=muc").json()["dong"]}
    assert len(tat_ca) == 30                                                      # không trùng, không sót dòng giữa các trang
    assert admin.get("/api/admin/data/survey_clean?size=10&page=99").json()["trang"] == 3   # trang quá lớn: lấy trang cuối
    assert len(admin.get("/api/admin/data/survey_clean?size=5000").json()["dong"]) == 30 and admin.get("/api/admin/data/survey_clean?size=5000").json()["kich_thuoc"] == 100


def test_tim_kiem_loc_sap_xep(db, admin):
    nap_clean(db, 30)
    r = admin.get("/api/admin/data/survey_clean?q=trường số 1").json()          # không phân biệt hoa thường: 1, 10..19
    assert r["tong"] == 11
    assert admin.get("/api/admin/data/survey_clean?q=.*").json()["tong"] == 0     # regex bị thoát, không phải ký tự đại diện
    assert admin.get("/api/admin/data/survey_clean?q=id007").json()["tong"] == 1  # khớp đúng ID
    assert admin.get("/api/admin/data/survey_clean?f.muc=Cao").json()["tong"] == 10
    assert admin.get("/api/admin/data/survey_clean?f.muc=Cao&f.in_chat=true").json()["tong"] == 5   # lọc kết hợp (AND)
    assert admin.get("/api/admin/data/survey_clean?f.nguon=web&q=số 2").json()["tong"] == 6
    ds = admin.get("/api/admin/data/survey_clean?sort=diem_sang_tao&order=desc&size=3").json()["dong"]
    assert [d["diem_sang_tao"] for d in ds] == [29.0, 28.0, 27.0]
    for xau in ("sort=password_hash", "f.khong_co=1", "f.muc=Sai", "f.in_chat=maybe", "page=abc"):
        assert admin.get(f"/api/admin/data/survey_clean?{xau}").status_code == 422


def test_an_du_lieu_thu_trong_danh_sach(db, admin):
    nap_nguoi(db, "that")
    nap_nguoi(db, "thu")
    nap_nguoi(db, "pilot")
    db["participants"].insert_one({"source": "volunteer", "email": "a@b.c"})   # chưa có nhãn = that
    assert admin.get("/api/admin/data/participants").json()["tong"] == 2           # mặc định ẩn thu + pilot
    assert admin.get("/api/admin/data/participants?ex_test=false").json()["tong"] == 4
    assert admin.get("/api/admin/data/participants?ex_test=false&f.data_label=pilot").json()["tong"] == 1
    assert admin.get("/api/admin/data/participants?f.data_label=thu").json()["tong"] == 0   # đang ẩn thử thì lọc thu cũng không hiện
    assert admin.get("/api/admin/data/schools?ex_test=true").status_code == 200    # bảng không có nhãn vẫn dùng được


# ---------- Che thông tin nhận dạng ----------

def test_che_email_ip_va_truong_cam(db, admin, viewer):
    pid = nap_nguoi(db)
    for c in (admin, viewer):
        ds = c.get("/api/admin/data/participants").text
        ct = c.get(f"/api/admin/data/participants/{pid}").text
        for toan in (ds, ct):
            for bi_mat in (EMAIL, "TOKEN-BI-MAT", "UA-BI-MAT", "session_token", "user_agent", "0123456789abcdef0123"):
                assert bi_mat not in toan
        assert "tr***@gmail.com" in ds and "01234567…" in ds
    assert admin_view.che_ip("113.22.45.9") == "113.22.45.*" and admin_view.che_email("a@b.com").endswith("@b.com")


def test_ma_tham_gia_admin_thay_du_viewer_bi_che(db, admin, viewer):
    db["access_codes"].insert_one({"code": "QWERTY12", "source": "volunteer", "is_used": False, "data_label": "that"})
    assert "QWERTY12" in admin.get("/api/admin/data/access_codes").text
    v = viewer.get("/api/admin/data/access_codes").text
    assert "QWERTY12" not in v and "QW******" in v
    assert "QWERTY12" not in viewer.get(f"/api/admin/data/access_codes/{db['access_codes'].find_one()['_id']}").text
    assert "QWERTY12" not in viewer.get("/api/admin/data/access_codes/export.csv").text


def test_chi_tiet_doc_duoc_va_json_tho(db, admin):
    pid = db["game_responses"].insert_one({"participant_id": ObjectId(), "game": 1, "data_label": "that", "paste_count": 2,
                                           "answer": {"ideas": ["ý 1", "ý 2"], "n_ideas": 2}, "started_at": utc_now()}).inserted_id
    d = admin.get(f"/api/admin/data/game_responses/{pid}").json()
    truong = {t["khoa"]: t for t in d["truong"]}
    assert truong["paste_count"]["nhan"] == "Số lần dán" and truong["answer"]["nhan"] == "Câu trả lời" and truong["answer"]["kieu"] == "json"
    assert truong["_id"]["gia_tri"] == str(pid) and d["tho"]["answer"]["n_ideas"] == 2
    assert d["truong"][0]["khoa"] == "_id"
    assert admin.get("/api/admin/data/game_responses/khong-co").status_code == 404
    assert admin.get(f"/api/admin/data/game_responses/{ObjectId()}").status_code == 404


# ---------- Xuất CSV ----------

def test_xuat_csv_khong_co_email_va_gioi_han_dong(db, admin, monkeypatch):
    for _ in range(4):
        nap_nguoi(db)
    db["survey_clean"].insert_one({"_id": "x1", "truong_chuan": "=CONG_THUC()", "thoi_gian": utc_now(), "data_label": "that"})
    r = admin.get("/api/admin/data/participants/export.csv")
    assert r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
    assert EMAIL not in r.text and "Email" not in r.text and "TOKEN-BI-MAT" not in r.text and r.headers["x-truncated"] == "false"
    assert len(list(csv.reader(io.StringIO(r.text.lstrip("﻿"))))) == 5      # 1 dòng tiêu đề + 4 dòng
    assert "'=CONG_THUC()" in admin.get("/api/admin/data/survey_clean/export.csv").text   # chống công thức Excel
    monkeypatch.setattr(reg, "SO_DONG_XUAT_TOI_DA", 3)
    r = admin.get("/api/admin/data/participants/export.csv")
    assert len(list(csv.reader(io.StringIO(r.text.lstrip("﻿"))))) == 4 and r.headers["x-truncated"] == "true"
    assert any(a["action"] == "data_export" for a in db["audit_log"].find())
    assert TestClient(main.app).get("/api/admin/data/participants/export.csv").status_code == 401


def test_csv_theo_bo_loc_va_an_thu(db, admin):
    nap_nguoi(db, "that")
    nap_nguoi(db, "thu")
    assert len(admin.get("/api/admin/data/participants/export.csv").text.strip().splitlines()) == 2
    assert len(admin.get("/api/admin/data/participants/export.csv?ex_test=false").text.strip().splitlines()) == 3


# ---------- CRUD (access_codes, schools) và nhật ký ----------

def nhat_ky(db, hanh_dong):
    return [a for a in db["audit_log"].find() if a["action"] == hanh_dong]


def test_crud_access_codes_va_audit(db, admin):
    r = admin.post("/api/admin/data/access_codes", json={"code": " ab-cd 1234 ", "source": "volunteer", "data_label": "thu"}, headers=GOC)
    assert r.status_code == 201
    doc = db["access_codes"].find_one()
    assert doc["code"] == "ABCD1234" and doc["is_used"] is False and doc["data_label"] == "thu"
    log = nhat_ky(db, "data_create")[0]
    assert log["username"] == "admin1" and log["collection"] == "access_codes" and log["doc_id"] == str(doc["_id"]) and "ABCD1234" not in str(log)
    assert admin.post("/api/admin/data/access_codes", json={"code": "ABCD1234", "source": "volunteer", "data_label": "thu"}, headers=GOC).json()["detail"]["code"] == "ma_trung"
    for xau in ({"code": "A", "source": "volunteer", "data_label": "thu"}, {"code": "ABCD9999", "source": "la", "data_label": "thu"},
                {"code": "ABCD9999", "source": "volunteer"}, {"code": "ABCD9999", "source": "volunteer", "data_label": "thu", "is_used": True}):
        assert admin.post("/api/admin/data/access_codes", json=xau, headers=GOC).status_code == 422
    i = str(doc["_id"])
    r = admin.patch(f"/api/admin/data/access_codes/{i}", json={"data_label": "pilot"}, headers=GOC)
    assert r.status_code == 200 and db["access_codes"].find_one()["data_label"] == "pilot"
    log = nhat_ky(db, "data_update")[0]
    assert log["detail"]["truong"] == {"data_label": {"cu": "thu", "moi": "pilot"}}
    assert admin.patch(f"/api/admin/data/access_codes/{i}", json={"data_label": "pilot"}, headers=GOC).json()["detail"]["code"] == "khong_co_thay_doi"
    assert admin.patch(f"/api/admin/data/access_codes/{i}", json={"code": "KHAC1234"}, headers=GOC).status_code == 422      # không đổi mã
    assert admin.patch(f"/api/admin/data/access_codes/{i}", json={"is_used": True}, headers=GOC).status_code == 422          # không sửa trường lạ
    assert admin.delete(f"/api/admin/data/access_codes/{i}", headers=GOC).json()["detail"]["code"] == "xac_nhan_sai"          # thiếu xác nhận
    assert admin.delete(f"/api/admin/data/access_codes/{i}?confirm=sai", headers=GOC).status_code == 422
    assert db["access_codes"].count_documents({}) == 1
    assert admin.delete(f"/api/admin/data/access_codes/{i}?confirm={i}", headers=GOC).status_code == 200
    assert db["access_codes"].count_documents({}) == 0
    log = nhat_ky(db, "data_delete")[0]
    assert log["doc_id"] == i and "ABCD1234" not in str(log)   # tóm tắt trong nhật ký che mã


def test_khong_sua_xoa_ma_da_dung(db, admin):
    i = db["access_codes"].insert_one({"code": "USED1234", "source": "volunteer", "is_used": True, "data_label": "that"}).inserted_id
    assert admin.patch(f"/api/admin/data/access_codes/{i}", json={"data_label": "thu"}, headers=GOC).json()["detail"]["code"] == "ma_da_dung"
    assert admin.delete(f"/api/admin/data/access_codes/{i}?confirm={i}", headers=GOC).json()["detail"]["code"] == "ma_da_dung"
    assert db["access_codes"].count_documents({}) == 1


def test_schools_readonly_co_ghi_chu_file_csv(db, admin, viewer):
    db["schools"].insert_one({"_id": 7, "name": "THPT Bắc Bình", "level": "THPT"})
    meta = {b["khoa"]: b for b in admin.get("/api/admin/data").json()["bang"]}["schools"]
    assert meta["che_do"] == "readonly" and meta["quyen"] == {"doc": True, "xuat": True, "ghi": False, "xoa": False}
    assert meta["ghi_chu"] == "Danh sách trường được quản lý bằng file content/schools.csv"
    assert admin.get("/api/admin/data/schools").json()["tong"] == 1 and viewer.get("/api/admin/data/schools").status_code == 200
    assert admin.post("/api/admin/data/schools", json={"name": "A", "level": "THPT"}, headers=GOC).status_code == 405
    assert admin.patch("/api/admin/data/schools/7", json={"name": "B"}, headers=GOC).status_code == 405
    assert admin.delete("/api/admin/data/schools/7?confirm=7", headers=GOC).status_code == 405
    assert db["schools"].find_one({"_id": 7})["name"] == "THPT Bắc Bình"


def test_id_so_van_tim_duoc(db, admin):
    db["schools"].insert_one({"_id": 123, "name": "Trường số", "level": "THCS"})
    assert admin.get("/api/admin/data/schools/123").json()["id"] == "123"
    assert admin.get("/api/admin/data/schools?q=123").json()["tong"] == 1


def test_xoa_tung_ban_ghi_bang_readonly_phai_go_lai_id(db, admin):
    pid = nap_nguoi(db)
    assert admin.delete(f"/api/admin/data/participants/{pid}?confirm=xoa", headers=GOC).status_code == 422
    assert db["participants"].count_documents({}) == 1
    assert admin.delete(f"/api/admin/data/participants/{pid}?confirm={pid}", headers=GOC).status_code == 200
    assert db["participants"].count_documents({}) == 0
    log = nhat_ky(db, "data_delete")[0]
    assert log["collection"] == "participants" and log["doc_id"] == str(pid)
    assert EMAIL not in str(log) and "TOKEN-BI-MAT" not in str(log) and "UA-BI-MAT" not in str(log)
    assert admin.delete(f"/api/admin/data/participants/{pid}?confirm={pid}", headers=GOC).status_code == 404


def test_form_goc_khong_xoa_duoc_clean_xoa_duoc(db, admin):
    db["survey_form1"].insert_one({"_id": "goc1", "thoi_gian": utc_now(), "A1": "Lớp 9"})
    db["survey_clean"].insert_one({"_id": "sach1", "thoi_gian": utc_now(), "data_label": "that"})
    assert admin.delete("/api/admin/data/survey_form1/goc1?confirm=goc1", headers=GOC).status_code == 405
    assert admin.patch("/api/admin/data/survey_form1/goc1", json={"A1": "x"}, headers=GOC).status_code == 405
    assert db["survey_form1"].count_documents({}) == 1
    assert admin.delete("/api/admin/data/survey_clean/sach1?confirm=sach1", headers=GOC).status_code == 200
    assert db["survey_clean"].count_documents({}) == 0 and db["survey_form1"].count_documents({}) == 1


def test_nhat_ky_chi_admin_khong_sua_xoa_duoc(db, admin):
    a = db["audit_log"].insert_one({"at": utc_now(), "action": "x"}).inserted_id
    assert admin.delete(f"/api/admin/data/audit_log/{a}?confirm={a}", headers=GOC).status_code == 405
    assert admin.patch(f"/api/admin/data/audit_log/{a}", json={"action": "y"}, headers=GOC).status_code == 405
    assert db["audit_log"].find_one({"_id": a})["action"] == "x"


def test_viet_can_csrf(db, admin):
    pid = nap_nguoi(db)
    khong_csrf = TestClient(main.app, client=("1.2.3.4", 1), cookies=admin.cookies)
    assert khong_csrf.delete(f"/api/admin/data/participants/{pid}?confirm={pid}", headers=GOC).json()["detail"]["code"] == "csrf"
    assert db["participants"].count_documents({}) == 1


# ---------- Nhãn dữ liệu ----------

def test_ma_moi_mang_nhan_va_mac_dinh_la_that(db):
    ma = kho.tao_ma_moi(db, 2, "volunteer")
    assert {d["data_label"] for d in db["access_codes"].find({"code": {"$in": ma}})} == {"that"}
    thu = kho.tao_ma_moi(db, 1, "volunteer", "thu")[0]
    assert db["access_codes"].find_one({"code": thu})["data_label"] == "thu"
    with pytest.raises(ValueError):
        kho.tao_ma_moi(db, 1, "volunteer", "gia")


def test_nhan_lan_sang_nguoi_va_cac_bang_con(db):
    from sparkmind import game_store
    ma = kho.tao_ma_moi(db, 1, "volunteer", "pilot")[0]
    token = kho.bat_dau(db, {"code": ma, "email": EMAIL, "grade": 9, "gender": 1, "school_name": "X", "consent": True, "guardian_consent": False},
                        "h", "ua")
    kho.luu_hanh_vi(db, token, {"a4": "1"})
    kho.luu_tu_danh_gia(db, token, {"c1": 3, "c2": 3, "c3": 3, "c4": 3, "c5": 3, "c6": "1"})
    game_store.bat_dau_game1(db, token, {"do_vat": [{"id": "d1"}], "thoi_gian_giay": 60})
    for bang in ("participants", "behavior_answers", "self_assessment", "game_responses"):
        assert db[bang].find_one()["data_label"] == "pilot", bang


def test_make_codes_nhan_mac_dinh_that():
    import make_codes
    assert make_codes.doc_tham_so(["--n", "1", "--source", "volunteer"]).data_label == "that"
    assert make_codes.doc_tham_so(["--n", "1", "--source", "volunteer", "--data-label", "pilot"]).data_label == "pilot"
    with pytest.raises(SystemExit):
        make_codes.doc_tham_so(["--n", "1", "--source", "volunteer", "--data-label", "gia"])


def nap_cu(db):
    """Dữ liệu cũ chưa có nhãn ở mọi bảng, kèm một bản ghi đã có nhãn that."""
    for b in data_label.BANG_HUONG2:
        db[b].insert_many([{"x": 1}, {"x": 2}])
    db["participants"].insert_one({"x": 3, "data_label": "that"})
    db["survey_clean"].insert_many([{"_id": "a"}, {"_id": "b"}, {"_id": "c", "data_label": "thu"}])
    db["survey_form1"].insert_many([{"_id": "a"}, {"_id": "b"}])


def test_migration_dry_run_khong_ghi(db):
    nap_cu(db)
    kh = data_label.ke_hoach(db)
    assert kh["access_codes"] == {"gan": "thu", "se_gan": 2, "tong": 2}
    assert kh["participants"] == {"gan": "thu", "se_gan": 2, "tong": 3}          # bản ghi đã có nhãn không tính
    assert kh["survey_clean"] == {"gan": "that", "se_gan": 2, "tong": 3}
    assert "survey_form1" not in kh
    assert all("data_label" not in d for d in db["access_codes"].find())          # ke_hoach chỉ đọc


def test_migration_gan_dung_nhan_va_idempotent(db):
    nap_cu(db)
    kq = data_label.ap_dung(db)
    assert kq["access_codes"] == 2 and kq["participants"] == 2 and kq["survey_clean"] == 2
    assert {d["data_label"] for d in db["behavior_answers"].find()} == {"thu"}
    assert {d["_id"]: d["data_label"] for d in db["survey_clean"].find()} == {"a": "that", "b": "that", "c": "thu"}   # that gán cho cũ, thu cũ giữ
    assert db["participants"].find_one({"x": 3})["data_label"] == "that"                                         # đã có nhãn: giữ nguyên
    assert all("data_label" not in d for d in db["survey_form1"].find())                                         # dữ liệu gốc không đụng
    truoc = {b: list(db[b].find()) for b in db.list_collection_names()}
    assert set(data_label.ap_dung(db).values()) == {0}                                                           # chạy lại: không đổi gì
    assert {b: list(db[b].find()) for b in db.list_collection_names()} == truoc


def test_script_migration_dry_run_mac_dinh_khong_ghi(db, monkeypatch, capsys):
    import migrate_data_label
    nap_cu(db)
    monkeypatch.setattr(migrate_data_label, "lay_db", lambda: db)
    migrate_data_label.main([])
    assert "DRY-RUN" in capsys.readouterr().out and "data_label" not in db["access_codes"].find_one()
    monkeypatch.setattr("builtins.input", lambda *_: "khong")
    with pytest.raises(SystemExit):
        migrate_data_label.main(["--apply"])
    assert "data_label" not in db["access_codes"].find_one()
    monkeypatch.setattr("builtins.input", lambda *_: "GAN NHAN")
    migrate_data_label.main(["--apply"])
    assert db["access_codes"].find_one()["data_label"] == "thu"


# ---------- Xóa dữ liệu thử ----------

def nap_hon_hop(db):
    """Mỗi bảng có nhãn: 1 thu, 1 pilot, 2 that, 1 chưa có nhãn (coi như that)."""
    for b in data_label.BANG_CO_NHAN:
        db[b].insert_many([{"data_label": "thu"}, {"data_label": "pilot"}, {"data_label": "that"}, {"data_label": "that"}, {"x": 1}])
    db["survey_form1"].insert_many([{"_id": "g1", "nguon": "thu"}, {"_id": "g2", "data_label": "thu"}])   # dữ liệu gốc: bị bỏ qua dù có chữ thu


def test_xem_truoc_dry_run_khong_xoa(db, admin):
    nap_hon_hop(db)
    truoc = {b: db[b].count_documents({}) for b in db.list_collection_names()}
    d = admin.get("/api/admin/test-data").json()
    assert d["tu_xac_nhan"] == "XOA" and d["tong"] == 2 * len(data_label.BANG_CO_NHAN)
    assert d["bang"]["participants"] == 2 and d["bang"]["survey_clean"] == 2 and "survey_form1" not in d["bang"]
    assert {b: db[b].count_documents({}) for b in db.list_collection_names()} == truoc


def test_xoa_du_lieu_thu_can_go_xoa(db, admin):
    nap_hon_hop(db)
    for sai in ("", "xoa", "XOA ", "DELETE", "OK"):
        assert admin.post("/api/admin/test-data/delete", json={"confirm": sai}, headers=GOC).status_code == 422
    assert db["participants"].count_documents({}) == 5 and not nhat_ky(db, "test_data_delete")


def test_xoa_du_lieu_thu_khong_dung_nhan_that(db, admin):
    nap_hon_hop(db)
    r = admin.post("/api/admin/test-data/delete", json={"confirm": "XOA"}, headers=GOC)
    assert r.status_code == 200 and r.json()["tong"] == 2 * len(data_label.BANG_CO_NHAN)
    for b in data_label.BANG_CO_NHAN:
        con_lai = list(db[b].find())
        assert len(con_lai) == 3 and not any(d.get("data_label") in ("thu", "pilot") for d in con_lai)
        assert sum(1 for d in con_lai if d.get("data_label") == "that") == 2 and sum(1 for d in con_lai if "data_label" not in d) == 1
    assert db["survey_form1"].count_documents({}) == 2                              # dữ liệu gốc còn nguyên
    log = nhat_ky(db, "test_data_delete")
    assert {a["collection"] for a in log} == set(data_label.BANG_CO_NHAN) and all(a["detail"]["so_ban_ghi"] == 2 for a in log)
    assert all(a["username"] == "admin1" for a in log)
    r = admin.post("/api/admin/test-data/delete", json={"confirm": "XOA"}, headers=GOC)   # chạy lại: không còn gì để xóa
    assert r.json()["tong"] == 0 and any(a["collection"] is None for a in nhat_ky(db, "test_data_delete"))


def test_bo_loc_xoa_thu_khong_bao_gio_chua_that(monkeypatch):
    assert du_lieu_thu.bo_loc_thu() == {"data_label": {"$in": ["thu", "pilot"]}}
    monkeypatch.setattr(config, "NHAN_DU_LIEU_THU", ("thu", "that"))
    with pytest.raises(AssertionError):                                           # cấu hình nguy hiểm bị chặn trước khi xóa
        du_lieu_thu.bo_loc_thu()


def test_xoa_thu_can_csrf(db, admin):
    nap_hon_hop(db)
    c = TestClient(main.app, client=("1.2.3.4", 1), cookies=admin.cookies)
    assert c.post("/api/admin/test-data/delete", json={"confirm": "XOA"}, headers=GOC).status_code == 403
    assert db["participants"].count_documents({}) == 5


def test_stats_va_danh_sach_cung_loc_theo_nhan(db, admin):
    from sparkmind import admin_stats
    admin_stats.xoa_cache()
    nap_nguoi(db, "that")
    nap_nguoi(db, "thu")
    assert admin.get("/api/admin/stats").json()["huong2"]["ma"]["da_tao"] == 1
    assert admin.get("/api/admin/data/participants").json()["tong"] == 1
    admin_stats.xoa_cache()
    assert admin.get("/api/admin/stats?ex_test=false").json()["huong2"]["ma"]["da_tao"] == 2
    admin_stats.xoa_cache()


# ---------- Xóa người tham gia kèm dữ liệu con ----------

def nap_nguoi_day_du(db, label="that", email=EMAIL):
    """Một người có form B, C, 2 bài game, mỗi bài game 1 điểm chấm. Trả (participant_id, [response_id])."""
    pid = nap_nguoi(db, label, email)
    db["behavior_answers"].insert_one({"participant_id": pid, "data_label": label})
    db["self_assessment"].insert_one({"participant_id": pid, "data_label": label})
    rs = [db["game_responses"].insert_one({"participant_id": pid, "game": g, "data_label": label}).inserted_id for g in (1, 2)]
    for r in rs:
        db["scores"].insert_one({"response_id": r, "rater": "auto", "total": 3.0, "data_label": label})
    return pid, rs


def dem(db):
    return {b: db[b].count_documents({}) for b in ("participants", "behavior_answers", "self_assessment", "game_responses", "scores")}


def test_lien_quan_chi_dem_khong_xoa(db, admin, viewer):
    pid, _ = nap_nguoi_day_du(db)
    nap_nguoi_day_du(db, email="khac@gmail.com")                      # người khác: không được tính
    truoc = dem(db)
    r = admin.get(f"/api/admin/data/participants/{pid}/lien-quan")
    assert r.json() == {"bang_con": {"behavior_answers": 1, "self_assessment": 1, "game_responses": 2, "scores": 2}}
    assert dem(db) == truoc                                           # xem số liệu không xóa gì
    assert viewer.get(f"/api/admin/data/participants/{pid}/lien-quan").status_code == 403      # chỉ người được xóa mới xem
    assert admin.get(f"/api/admin/data/participants/{ObjectId()}/lien-quan").status_code == 404
    assert admin.get("/api/admin/data/survey_clean/x/lien-quan").status_code == 404          # chỉ bảng có bang_con mới có route này


def test_xoa_nguoi_xoa_luon_bang_con_va_ghi_nhat_ky(db, admin):
    pid, _ = nap_nguoi_day_du(db)
    khac, _ = nap_nguoi_day_du(db, email="khac@gmail.com")
    assert admin.delete(f"/api/admin/data/participants/{pid}?confirm=sai", headers=GOC).status_code == 422
    assert dem(db) == {"participants": 2, "behavior_answers": 2, "self_assessment": 2, "game_responses": 4, "scores": 4}   # sai xác nhận: chưa xóa gì
    r = admin.delete(f"/api/admin/data/participants/{pid}?confirm={pid}", headers=GOC)
    assert r.status_code == 200 and r.json()["da_xoa_bang_con"] == {"behavior_answers": 1, "self_assessment": 1, "game_responses": 2, "scores": 2}
    assert dem(db) == {"participants": 1, "behavior_answers": 1, "self_assessment": 1, "game_responses": 2, "scores": 2}
    assert db["behavior_answers"].find_one()["participant_id"] == khac and db["game_responses"].count_documents({"participant_id": khac}) == 2   # người kia còn nguyên
    log = nhat_ky(db, "data_delete")[0]
    assert log["collection"] == "participants" and log["detail"]["da_xoa_bang_con"] == {"behavior_answers": 1, "self_assessment": 1, "game_responses": 2, "scores": 2}
    assert EMAIL not in str(log)


def test_xoa_nguoi_khong_co_du_lieu_con_van_duoc(db, admin):
    pid = nap_nguoi(db)
    r = admin.delete(f"/api/admin/data/participants/{pid}?confirm={pid}", headers=GOC)
    assert r.json()["da_xoa_bang_con"] == {"behavior_answers": 0, "self_assessment": 0, "game_responses": 0, "scores": 0}


def test_route_lien_quan_chi_o_bang_co_bang_con():
    co = {d for d, r, _ in duyet_route(main.app.routes) if isinstance(r, APIRoute) and d.endswith("/lien-quan")}
    assert co == {"/api/admin/data/participants/{id_}/lien-quan"}


# ---------- run_cleaning giữ nhãn ----------

def test_run_cleaning_giu_data_label_hien_co(db):
    import pandas as pd
    import run_cleaning
    db["survey_clean"].insert_many([{"_id": "a", "data_label": "thu", "x": 0}, {"_id": "b", "data_label": "that", "x": 0}, {"_id": "c", "x": 0}])
    sach = pd.DataFrame([{"_id": "a", "x": 1}, {"_id": "b", "x": 2}, {"_id": "c", "x": 3}, {"_id": "d", "x": 4}])
    assert run_cleaning.ghi_ban_sach(db, sach, gop=False) == 4
    ket_qua = {d["_id"]: d for d in db["survey_clean"].find()}
    assert ket_qua["a"]["data_label"] == "thu" and ket_qua["b"]["data_label"] == "that"      # nhãn cũ được giữ
    assert "data_label" not in ket_qua["c"] and "data_label" not in ket_qua["d"]              # chưa có nhãn thì vẫn chưa có (coi là that)
    assert [ket_qua[k]["x"] for k in "abcd"] == [1, 2, 3, 4]                                  # nội dung đã được làm sạch lại
    run_cleaning.ghi_ban_sach(db, sach, gop=False)                                                       # chạy lại: nhãn vẫn nguyên
    assert db["survey_clean"].find_one({"_id": "a"})["data_label"] == "thu"


def test_khong_hardcode_ten_database_cu():
    goc = Path(__file__).resolve().parents[1]
    for thu_muc in ("src", "server", "scripts"):
        for f in (goc / thu_muc).rglob("*.py"):
            assert '"spark_mind"' not in f.read_text(encoding="utf-8"), f"{f} còn tên database cũ spark_mind (đúng là spark-mind)"
