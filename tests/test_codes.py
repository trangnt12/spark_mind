"""Kiểm tra script tạo mã (CSV, giới hạn --n) và đếm mã theo nguồn."""
import csv
import sys
from pathlib import Path

import mongomock
import pytest

RE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RE / "scripts"))
sys.path.insert(0, str(RE / "src"))
import list_codes  # noqa: E402
import make_codes  # noqa: E402
from sparkmind import research_store as kho  # noqa: E402


def doc_csv(duong_dan):
    with open(duong_dan, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_ghi_csv_du_cot_va_nhan(tmp_path):
    db = mongomock.MongoClient().spark_mind
    kho.tao_chi_muc(db)
    cac_ma = kho.tao_ma_moi(db, 3, "hired_team")
    out = make_codes.ghi_csv(db, cac_ma, "hired_team", "Nhóm A", tmp_path / "x" / "codes.csv")
    dong = doc_csv(out)
    assert [d["code"] for d in dong] == cac_ma
    assert {d["source"] for d in dong} == {"hired_team"}
    assert {d["label"] for d in dong} == {"Nhóm A"}
    assert all(d["created_at"] for d in dong)
    assert list(dong[0]) == ["code", "source", "data_label", "batch", "created_at", "label"]


def test_ghi_csv_noi_them_khong_lap_tieu_de(tmp_path):
    db = mongomock.MongoClient().spark_mind
    out = tmp_path / "c.csv"
    for _ in range(2):
        make_codes.ghi_csv(db, kho.tao_ma_moi(db, 2, "volunteer"), "volunteer", "", out)
    assert len(doc_csv(out)) == 4


def test_nhan_khong_thanh_cong_thuc():
    assert make_codes.lam_sach_nhan("=1+1").startswith("'")
    assert make_codes.lam_sach_nhan("  An ") == "An"


@pytest.mark.parametrize("n", ["0", "501", "-3"])
def test_n_ngoai_khoang_bi_tu_choi(n):
    with pytest.raises(SystemExit):
        make_codes.doc_tham_so(["--n", n, "--source", "volunteer"])


def test_n_500_hop_le_va_source_sai_bi_tu_choi():
    assert make_codes.doc_tham_so(["--n", "500", "--source", "volunteer"]).n == 500
    with pytest.raises(SystemExit):
        make_codes.doc_tham_so(["--n", "5", "--source", "khac"])


def test_dem_ma_theo_nguon():
    db = mongomock.MongoClient().spark_mind
    kho.tao_ma_moi(db, 3, "volunteer")
    kho.tao_ma_moi(db, 2, "hired_team")
    db[kho.COL_MA].update_one({"source": "volunteer"}, {"$set": {"is_used": True}})
    kq = list_codes.dem_ma(db)
    assert kq["volunteer"] == {"tong": 3, "da_dung": 1, "chua_dung": 2}
    assert kq["hired_team"] == {"tong": 2, "da_dung": 0, "chua_dung": 2}


# ---------- Mã hàng loạt theo lô (24/11) ----------

CHU_CAM = set("0O1Il")


def test_ma_khong_co_ky_tu_cam_va_khong_trung():
    db = mongomock.MongoClient().spark_mind
    ds = kho.tao_ma_moi(db, 500, "hired_team", batch="nhom_thue_1")
    assert len(set(ds)) == 500                                   # không trùng nhau
    assert all(len(m) == 8 and not CHU_CAM & set(m) for m in ds)  # 8 ký tự, không có 0 O 1 I l
    assert not CHU_CAM & set(kho.BANG_CHU)


def test_ma_moi_khong_trung_ma_da_co_ke_ca_khi_chua_co_chi_muc(monkeypatch):
    """Ép bộ sinh ra mã đã có hai lần: phải bỏ qua và lấy mã khác (mongomock chưa tạo chỉ mục unique)."""
    db = mongomock.MongoClient().spark_mind
    db[kho.COL_MA].insert_one({"code": "AAAAAAAA", "source": "volunteer", "is_used": False})
    day = iter(["AAAAAAAA", "AAAAAAAA", "BBBBBBBB"])
    monkeypatch.setattr(kho, "_ma_ngau_nhien", lambda: next(day))
    assert kho.tao_ma_moi(db, 1, "volunteer") == ["BBBBBBBB"]
    assert db[kho.COL_MA].count_documents({"code": "AAAAAAAA"}) == 1


def test_batch_luu_dung_va_mac_dinh_la_none():
    db = mongomock.MongoClient().spark_mind
    a = kho.tao_ma_moi(db, 3, "volunteer", "pilot", "lop_khoa_a")
    b = kho.tao_ma_moi(db, 2, "volunteer")
    assert {d["batch"] for d in db[kho.COL_MA].find({"code": {"$in": a}})} == {"lop_khoa_a"}
    assert {d["data_label"] for d in db[kho.COL_MA].find({"code": {"$in": a}})} == {"pilot"}
    assert {d["batch"] for d in db[kho.COL_MA].find({"code": {"$in": b}})} == {None}


@pytest.mark.parametrize("ten", ["lop khoa a", "-lop", "=1+1", "a" * 41, "lớp_a", "a;b", "../x"])
def test_ten_lo_sai_bi_tu_choi(ten):
    with pytest.raises(ValueError):
        kho.kiem_tra_ten_lo(ten)
    with pytest.raises(SystemExit):
        make_codes.doc_tham_so(["--n", "1", "--source", "volunteer", "--batch", ten])


def test_ten_lo_hop_le_qua_dong_lenh():
    t = make_codes.doc_tham_so(["--n", "5", "--source", "hired_team", "--batch", "nhom_thue_1", "--data-label", "thu"])
    assert t.batch == "nhom_thue_1" and t.data_label == "thu"


def test_csv_co_batch_va_nhan(tmp_path):
    db = mongomock.MongoClient().spark_mind
    ds = kho.tao_ma_moi(db, 2, "hired_team", "thu", "nhom_thue_1")
    dong = doc_csv(make_codes.ghi_csv(db, ds, "hired_team", "", tmp_path / "c.csv", "thu", "nhom_thue_1"))
    assert {d["batch"] for d in dong} == {"nhom_thue_1"} and {d["data_label"] for d in dong} == {"thu"}


def test_csv_nam_trong_outputs_va_bi_gitignore():
    assert make_codes.THU_MUC_RA.name == "outputs"
    gi = (RE / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "outputs/*.csv" in gi and "outputs/codes_*.csv" in gi


def test_tao_nhieu_ma_khong_anh_huong_gioi_han_nhap_sai(monkeypatch):
    """Tạo 300 mã không đụng bộ đếm nhập sai; nhập đúng nhiều mã khác nhau không bị tính sai và không bị khóa;
    sau 10 lần SAI mới bị khóa (như thiết kế cũ), và khóa đó không làm hỏng mã trong DB."""
    from fastapi.testclient import TestClient
    from server import main, research
    from sparkmind import config
    db = mongomock.MongoClient().spark_mind
    kho.tao_chi_muc(db)
    monkeypatch.setattr(config, "IP_HASH_SECRET", "khoa-thu")
    research.gioi_han_ma.xoa()
    main.app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: db
    try:
        c = TestClient(main.app, client=("9.9.9.9", 4000))
        ds = kho.tao_ma_moi(db, 300, "hired_team", batch="nhom_thue_1")
        assert research.gioi_han_ma.giay_phai_cho("9.9.9.9") == 0
        for ma in ds[:25]:                                   # 25 mã đúng liên tiếp từ cùng một IP: không bị chặn
            assert c.post("/api/research/code/check", json={"code": ma}).json()["valid"] is True
        for _ in range(10):
            assert c.post("/api/research/code/check", json={"code": "SAIMA000"}).status_code == 200
        assert c.post("/api/research/code/check", json={"code": ds[0]}).status_code == 429   # khóa theo IP vì nhập SAI nhiều lần
        assert db[kho.COL_MA].count_documents({"batch": "nhom_thue_1", "is_used": False}) == 300   # mã không bị ảnh hưởng
    finally:
        main.app.dependency_overrides.clear()
        research.gioi_han_ma.xoa()
