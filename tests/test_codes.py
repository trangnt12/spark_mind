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
    assert list(dong[0]) == ["code", "source", "created_at", "label"]


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
