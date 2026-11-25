"""Kiểm tra sao lưu/khôi phục: đúng số bản ghi và kiểu dữ liệu, từ chối ghi vào database đang dùng."""
import sys
from datetime import datetime
from pathlib import Path

import mongomock
import pytest
from bson import ObjectId

RE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RE / "src"))
from sparkmind import backup, config  # noqa: E402


def tao_client():
    c = mongomock.MongoClient()
    db = c[config.MONGODB_DB]
    db.participants.insert_many([{"_id": ObjectId(), "email": f"a{i}@x.vn", "created_at": datetime(2026, 12, 1, i)} for i in range(5)])
    db.participants.create_index("email", unique=True, name="email_1")
    db.access_codes.insert_many([{"_id": f"m{i}", "used": bool(i % 2), "so": i * 1.5} for i in range(3)])
    db.admin_sessions.insert_one({"_id": "s1"})
    db.login_attempts.insert_one({"_id": "l1"})
    return c


def test_sao_luu_roi_khoi_phuc_giong_nhau(tmp_path):
    c = tao_client()
    thu_muc = backup.sao_luu(c[config.MONGODB_DB], tmp_path)
    kq = backup.khoi_phuc(c, thu_muc, "spark-mind-tam")
    assert kq == {"access_codes": (3, 3), "participants": (5, 5)}
    goc, moi = c[config.MONGODB_DB], c["spark-mind-tam"]
    for ten in ("participants", "access_codes"):
        assert sorted(goc[ten].find(), key=str) == sorted(moi[ten].find(), key=str)
    d = moi.participants.find_one()
    assert isinstance(d["_id"], ObjectId) and isinstance(d["created_at"], datetime)
    assert moi.participants.index_information()["email_1"]["unique"]


def test_khong_xuat_admin_sessions_login_attempts(tmp_path):
    c = tao_client()
    thu_muc = backup.sao_luu(c[config.MONGODB_DB], tmp_path)
    mf = backup.doc_manifest(thu_muc)
    assert set(mf["collections"]) == {"participants", "access_codes"}
    ten_file = {p.name for p in thu_muc.iterdir()}
    assert not any("admin_sessions" in t or "login_attempts" in t for t in ten_file)
    assert mf["database"] == config.MONGODB_DB and mf["phien_ban"] == backup.PHIEN_BAN


def test_tu_choi_database_dang_dung(tmp_path):
    c = tao_client()
    thu_muc = backup.sao_luu(c[config.MONGODB_DB], tmp_path)
    for ten in (config.MONGODB_DB, config.MONGODB_DB.upper(), "spark-mind", ""):
        with pytest.raises(ValueError):
            backup.khoi_phuc(c, thu_muc, ten)
    assert c[config.MONGODB_DB].participants.count_documents({}) == 5   # không bị đụng tới


def test_tu_choi_database_khong_rong(tmp_path):
    c = tao_client()
    thu_muc = backup.sao_luu(c[config.MONGODB_DB], tmp_path)
    c["da-co"].x.insert_one({"a": 1})
    with pytest.raises(ValueError):
        backup.khoi_phuc(c, thu_muc, "da-co")
    assert c["da-co"].x.count_documents({}) == 1


def test_khong_co_lenh_drop_trong_ma_nguon():
    for f in (RE / "src/sparkmind/backup.py", RE / "scripts/backup_mongo.py", RE / "scripts/restore_mongo.py"):
        txt = f.read_text(encoding="utf-8")
        assert "drop_database" not in txt and "drop_collection" not in txt and ".drop(" not in txt


def test_don_ban_cu_chi_xoa_trong_backups(tmp_path):
    goc = tmp_path / "backups"
    for i in range(4):
        (goc / f"2026120{i + 1}_000000").mkdir(parents=True)
    (goc / "giu_lai").mkdir()
    da_xoa = backup.don_ban_cu(goc, 2)
    assert da_xoa == ["20261201_000000", "20261202_000000"]
    assert (goc / "giu_lai").exists() and (goc / "20261204_000000").exists()


def test_backups_nam_trong_gitignore():
    dong = (RE / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "backups/" in [d.strip() for d in dong]
