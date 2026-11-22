"""Kiểm tra chế độ nghiên cứu: mã, đồng ý, tiếp tục, nộp một lần, không lưu IP thô, không rò dữ liệu."""
import sys
from pathlib import Path

import mongomock
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from server import main, research  # noqa: E402
from sparkmind import config, research_store as kho  # noqa: E402
from sparkmind.security import GioiHanTocDo, bam_ip  # noqa: E402

BAT_DAU = {"email": "  Trang@Gmail.COM ", "grade": 6, "gender": 2, "school_name": "THPT Bắc Bình",
           "consent": True, "guardian_consent": True}
HANH_VI = {"A4": 1, "B1": [1, 2], "B3": [1, 5], "B2": 2, "B4_1": 4, "B4_2": 5, "B4_3": 2, "B4_4": 4, "B4_5": 3, "B4_6": 2, "B4_7": 5,
           "B5": 2, "B6": [1, 3], "B7": 2, "duration_sec": 120}
TU_DANH_GIA = {"C1": 4, "C2": 3, "C3": 4, "C4": 5, "C5": 4, "C6": 3}


@pytest.fixture
def client(monkeypatch):
    db = mongomock.MongoClient().spark_mind
    monkeypatch.setattr(config, "IP_HASH_SECRET", "khoa-thu")
    kho.tao_chi_muc(db)
    research.gioi_han_ma.xoa()
    main.app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: db
    yield TestClient(main.app, client=("1.2.3.4", 50000)), db  # giả lập IP người dùng
    main.app.dependency_overrides.clear()


def ma_moi(db, nguon="volunteer"):
    return kho.tao_ma_moi(db, 1, nguon)[0]


def bat_dau(c, ma, **sua):
    return c.post("/api/research/start", json={"code": ma, **BAT_DAU, **sua})


def test_chi_muc_theo_erd(client):
    _, db = client
    assert db["access_codes"].index_information()["code_1"]["unique"]
    assert db["participants"].index_information()["code_id_1"]["unique"]
    assert "email_1" in db["participants"].index_information()
    assert "ip_hash_1" in db["participants"].index_information()
    assert db["behavior_answers"].index_information()["participant_id_1"]["unique"]
    assert db["self_assessment"].index_information()["participant_id_1"]["unique"]


def test_ma_tao_ra_dung_dinh_dang(client):
    _, db = client
    cac_ma = kho.tao_ma_moi(db, 50, "hired_team")
    assert len(set(cac_ma)) == 50
    assert all(len(m) == 8 and not set(m) & set("O0I1") for m in cac_ma)
    assert db["access_codes"].find_one({"code": cac_ma[0]})["source"] == "hired_team"


def test_ma_sai(client):
    c, _ = client
    assert c.post("/api/research/code/check", json={"code": "SAISAI88"}).json()["valid"] is False
    assert bat_dau(c, "SAISAI88").status_code == 404


def test_ma_hop_le_khong_phan_biet_hoa_thuong(client):
    c, db = client
    ma = ma_moi(db)
    assert c.post("/api/research/code/check", json={"code": f" {ma.lower()} "}).json()["valid"] is True


def test_ma_da_dung(client):
    c, db = client
    ma = ma_moi(db)
    assert bat_dau(c, ma).status_code == 200
    r = bat_dau(c, ma, email="nguoi.khac@gmail.com")
    assert r.status_code == 409
    assert c.post("/api/research/code/check", json={"code": ma}).json()["valid"] is False


def test_thieu_consent(client):
    c, db = client
    ma = ma_moi(db)
    assert bat_dau(c, ma, consent=False).status_code == 422
    assert db["participants"].count_documents({}) == 0
    assert db["access_codes"].find_one({"code": ma})["is_used"] is False  # mã chưa bị mất


def test_duoi_18_thieu_guardian(client):
    c, db = client
    ma = ma_moi(db)
    assert bat_dau(c, ma, grade=3, guardian_consent=False).status_code == 422
    assert bat_dau(c, ma, grade=8, guardian_consent=False).status_code == 200  # sinh viên: không cần


def test_tiep_tuc_cung_ma_cung_email(client):
    c, db = client
    ma = ma_moi(db)
    t1 = bat_dau(c, ma).json()["session_token"]
    t2 = bat_dau(c, ma, email="TRANG@gmail.com").json()["session_token"]
    assert t1 == t2 and db["participants"].count_documents({}) == 1
    assert bat_dau(c, ma, email="khac@gmail.com").status_code == 409


def test_luu_participant_khong_ip_tho_va_email_chuan_hoa(client):
    c, db = client
    bat_dau(c, ma_moi(db))
    p = db["participants"].find_one()
    assert p["email"] == "trang@gmail.com" and p["source"] == "volunteer"
    assert p["ip_hash"] == bam_ip("1.2.3.4") and "1.2.3.4" not in str(p)


def test_response_khong_tra_email_hay_ip(client):
    c, db = client
    r = bat_dau(c, ma_moi(db))
    assert set(r.json()) == {"session_token"}


def test_nop_hanh_vi_va_tu_danh_gia(client):
    c, db = client
    token = bat_dau(c, ma_moi(db)).json()["session_token"]
    assert c.post("/api/research/behavior", json={"session_token": token, **HANH_VI}).status_code == 200
    r = c.post("/api/research/self-assessment", json={"session_token": token, **TU_DANH_GIA})
    assert r.status_code == 200
    assert db["behavior_answers"].find_one()["b6_prompting"] == "1,3"
    assert db["self_assessment"].find_one()["creativity_score"] == 75.0  # (20 - 5) / 20 * 100


def test_luu_chu_muc_khac(client):
    """Chữ gõ ở "Mục khác:" chỉ được lưu khi đã chọn mục đó; bỏ khoảng trắng đầu/cuối."""
    c, db = client
    token = bat_dau(c, ma_moi(db)).json()["session_token"]
    body = {"session_token": token, **HANH_VI, "B3": [1, 8], "B1_other": "Grok", "B3_other": "  Làm thơ ",  # B1 chưa chọn mục khác
            "B6_other": "không dùng"}
    assert c.post("/api/research/behavior", json=body).status_code == 200
    d = db["behavior_answers"].find_one()
    assert (d["b1_other"], d["b3_other"], d["b6_other"]) == (None, "Làm thơ", None) and d["b3"] == "1,8"


def test_nop_trung(client):
    c, db = client
    token = bat_dau(c, ma_moi(db)).json()["session_token"]
    body = {"session_token": token, **HANH_VI}
    assert c.post("/api/research/behavior", json=body).status_code == 200
    assert c.post("/api/research/behavior", json=body).status_code == 409
    assert db["behavior_answers"].count_documents({}) == 1


def test_gia_tri_khong_hop_le_va_phien_sai(client):
    c, db = client
    token = bat_dau(c, ma_moi(db)).json()["session_token"]
    assert c.post("/api/research/behavior", json={"session_token": token, **HANH_VI, "B4_1": 9}).status_code == 422
    assert c.post("/api/research/behavior", json={"session_token": token, **HANH_VI, "B2": 99}).status_code == 422
    assert c.post("/api/research/self-assessment", json={"session_token": token, **TU_DANH_GIA, "C6": 7}).status_code == 422
    assert c.post("/api/research/behavior", json={"session_token": "sai", **HANH_VI}).status_code == 401
    assert db["behavior_answers"].count_documents({}) == 0


def test_khong_ghi_vao_bang_khao_sat_cu(client):
    c, db = client
    token = bat_dau(c, ma_moi(db)).json()["session_token"]
    c.post("/api/research/behavior", json={"session_token": token, **HANH_VI})
    assert db[config.COL_RAW].count_documents({}) == 0 and db[config.COL_CLEAN].count_documents({}) == 0


def test_gioi_han_toc_do_ma(client):
    c, _ = client
    ma_tra = [c.post("/api/research/code/check", json={"code": "ABCD2345"}).status_code for _ in range(11)]
    assert ma_tra[:10] == [200] * 10 and ma_tra[10] == 429


def test_ma_dung_khong_bi_tinh_vao_gioi_han(client):
    c, db = client
    ma = ma_moi(db)
    ma_tra = [c.post("/api/research/code/check", json={"code": ma}).status_code for _ in range(30)]
    assert ma_tra == [200] * 30


def test_ma_sai_lan_11_bi_429_kem_thoi_gian_cho(client):
    c, _ = client
    ma_tra = [c.post("/api/research/code/check", json={"code": "SAISAI88"}) for _ in range(11)]
    assert [r.status_code for r in ma_tra[:10]] == [200] * 10
    assert ma_tra[10].status_code == 429 and 1 <= int(ma_tra[10].headers["Retry-After"]) <= 60


def test_bo_dem_toc_do_het_han_sau_mot_phut():
    g = GioiHanTocDo(toi_da=2, giay=60)
    assert g.cho_phep("ip", 0) and g.cho_phep("ip", 1) and not g.cho_phep("ip", 2)
    assert g.cho_phep("ip", 61)


def goi_kiem_tra(c, so_lan, **kw):
    """Gọi /code/check nhiều lần, trả về danh sách mã trạng thái."""
    return [c.post("/api/research/code/check", json={"code": "ABCD2345"}, **kw).status_code
            for _ in range(so_lan)]


def test_hai_ip_khac_nhau_khong_anh_huong_nhau(client):
    c1, _ = client
    c2 = TestClient(main.app, client=("5.6.7.8", 50000))
    assert goi_kiem_tra(c1, 11)[-1] == 429       # IP thứ nhất bị chặn ở lần 11
    assert goi_kiem_tra(c2, 10) == [200] * 10    # IP thứ hai vẫn dùng bình thường


def test_header_x_forwarded_for_gia_bi_bo_qua(client):
    c, _ = client
    ma_tra = [goi_kiem_tra(c, 1, headers={"x-forwarded-for": f"9.9.9.{i}"})[0] for i in range(11)]
    assert ma_tra[-1] == 429  # đổi header mỗi lần vẫn không né được giới hạn


def test_sua_phan_da_nop_khi_quay_lai(client):
    """Nút Quay lại: gửi lại với edit=true thì ghi đè (vẫn một tài liệu), không có edit thì vẫn 409."""
    c, db = client
    token = bat_dau(c, ma_moi(db)).json()["session_token"]
    hv, tdg = {"session_token": token, **HANH_VI}, {"session_token": token, **TU_DANH_GIA}
    assert c.post("/api/research/behavior", json=hv).status_code == 200
    assert c.post("/api/research/self-assessment", json=tdg).status_code == 200
    assert c.post("/api/research/behavior", json=hv).status_code == 409
    assert c.post("/api/research/behavior", json={**hv, "B7": 3, "edit": True}).status_code == 200
    assert c.post("/api/research/self-assessment", json={**tdg, "C1": 1, "C2": 1, "C3": 1, "C4": 1, "C5": 1, "edit": True}).status_code == 200
    assert db["behavior_answers"].count_documents({}) == 1 and db["self_assessment"].count_documents({}) == 1
    assert db["behavior_answers"].find_one()["b7_after_answer"] == "3"
    assert db["behavior_answers"].find_one()["edit_count"] == 1
    assert db["self_assessment"].find_one()["creativity_score"] == 0.0


def test_sua_thong_tin_phan_a(client):
    c, db = client
    token = bat_dau(c, ma_moi(db)).json()["session_token"]
    sua = {"session_token": token, "grade": 9, "gender": 2, "school_name": " Trường mới ", "guardian_consent": False}
    r = c.post("/api/research/info/update", json=sua)
    assert r.status_code == 200
    nguoi = db["participants"].find_one()
    assert (nguoi["grade"], nguoi["gender"], nguoi["school_name"]) == ("9", "2", "Trường mới")
    assert nguoi["email"] and nguoi["consent"] is True               # email, đồng ý ban đầu giữ nguyên
    assert c.post("/api/research/info/update", json={**sua, "grade": 3}).status_code == 422   # dưới 18 thiếu xác nhận
    assert c.post("/api/research/info/update", json={**sua, "session_token": "sai"}).status_code == 401
