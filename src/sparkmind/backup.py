"""Sao lưu và khôi phục MongoDB (logic dùng chung cho scripts/backup_mongo.py và restore_mongo.py).

An toàn: sao lưu chỉ ĐỌC. Khôi phục chỉ ghi vào một database MỚI (rỗng), không bao giờ vào database đang dùng.
Không có lệnh drop database/collection nào trong file này.
"""
import gzip
import re
import shutil
from datetime import datetime
from pathlib import Path

from bson import json_util

from . import config

THU_MUC_SAO_LUU = config.ROOT / "backups"
LOAI_TRU = ("admin_sessions", "login_attempts")   # phiên đăng nhập và bộ đếm đăng nhập sai: không cần sao lưu
PHIEN_BAN = 1                                      # phiên bản định dạng sao lưu
MAU_TEN_BAN = re.compile(r"^\d{8}_\d{6}$")         # tên thư mục sao lưu: ngày_giờ
DB_CAM = ("spark-mind", "admin", "local", "config")  # tên database không bao giờ được làm đích khôi phục


def _ghi_collection(col, duong_dan: Path) -> int:
    """Ghi một collection ra file .jsonl.gz (mỗi dòng một bản ghi, Extended JSON). Trả số bản ghi."""
    n = 0
    with gzip.open(duong_dan, "wt", encoding="utf-8", newline="\n") as f:
        for doc in col.find():
            f.write(json_util.dumps(doc, ensure_ascii=False) + "\n")
            n += 1
    return n


def _chi_muc(col) -> list:
    """Danh sách chỉ mục (trừ _id_) để dựng lại khi khôi phục."""
    kq = []
    for ten, thongtin in col.index_information().items():
        if ten == "_id_":
            continue
        kq.append({"name": ten, "key": [list(k) for k in thongtin["key"]], "unique": bool(thongtin.get("unique"))})
    return kq


def sao_luu(db, goc: Path = THU_MUC_SAO_LUU, bay_gio: datetime = None) -> Path:
    """Xuất mọi collection (trừ LOAI_TRU) ra goc/<ngày_giờ>/. Chỉ đọc từ db. Trả thư mục vừa tạo."""
    bay_gio = bay_gio or datetime.now()
    thu_muc = Path(goc) / bay_gio.strftime("%Y%m%d_%H%M%S")
    thu_muc.mkdir(parents=True, exist_ok=False)
    ds = {}
    for ten in sorted(db.list_collection_names()):
        if ten in LOAI_TRU or ten.startswith("system."):
            continue
        n = _ghi_collection(db[ten], thu_muc / f"{ten}.jsonl.gz")
        ds[ten] = {"so_ban_ghi": n, "chi_muc": _chi_muc(db[ten])}
    manifest = {"phien_ban": PHIEN_BAN, "database": db.name, "thoi_diem": bay_gio.isoformat(timespec="seconds"), "collections": ds}
    (thu_muc / "manifest.json").write_text(json_util.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return thu_muc


def doc_manifest(thu_muc: Path) -> dict:
    """Đọc manifest.json của một bản sao lưu."""
    duong_dan = Path(thu_muc) / "manifest.json"
    if not duong_dan.exists():
        raise FileNotFoundError(f"Không thấy manifest.json trong {thu_muc}")
    return json_util.loads(duong_dan.read_text(encoding="utf-8"))


def don_ban_cu(goc: Path, giu: int) -> list:
    """Xóa bớt bản sao lưu cũ, chỉ trong thư mục goc và chỉ thư mục tên dạng ngày_giờ. Trả tên các bản đã xóa."""
    goc = Path(goc).resolve()
    ban = sorted(p for p in goc.iterdir() if p.is_dir() and MAU_TEN_BAN.match(p.name)) if goc.exists() else []
    bo = ban[:-giu] if giu > 0 else ban
    for p in bo:
        if p.resolve().parent != goc:   # chốt chặn: không bao giờ xóa ngoài thư mục sao lưu
            continue
        shutil.rmtree(p)
    return [p.name for p in bo]


def kiem_tra_dich(client, into: str, ten_goc: str) -> None:
    """Từ chối nếu database đích trùng database đang dùng/database gốc của bản sao lưu, hoặc không rỗng."""
    cam = {config.MONGODB_DB.lower(), (ten_goc or "").lower(), *DB_CAM}
    if not into or into.lower() in cam:
        raise ValueError(f"Không được khôi phục vào database '{into}' (đang dùng hoặc hệ thống). Hãy đặt tên mới.")
    if client[into].list_collection_names():
        raise ValueError(f"Database '{into}' đã có dữ liệu. Chỉ khôi phục vào database rỗng hoặc chưa tồn tại.")


def _doc_collection(duong_dan: Path):
    """Đọc từng bản ghi trong file .jsonl.gz (giữ ObjectId, ngày giờ)."""
    with gzip.open(duong_dan, "rt", encoding="utf-8") as f:
        for dong in f:
            if dong.strip():
                yield json_util.loads(dong)


def _nap_collection(col, duong_dan: Path, chi_muc: list) -> None:
    """Ghi một collection vào db đích (theo lô 500), rồi dựng lại chỉ mục."""
    lo = []
    for doc in _doc_collection(duong_dan):
        lo.append(doc)
        if len(lo) >= 500:
            col.insert_many(lo)
            lo = []
    if lo:
        col.insert_many(lo)
    for cm in chi_muc:
        col.create_index([tuple(k) for k in cm["key"]], name=cm["name"], unique=cm["unique"])


def khoi_phuc(client, thu_muc: Path, into: str) -> dict:
    """Khôi phục bản sao lưu vào database MỚI `into`. Trả {collection: (số trong manifest, số đếm được ở đích)}."""
    thu_muc = Path(thu_muc)
    mf = doc_manifest(thu_muc)
    kiem_tra_dich(client, into, mf.get("database"))
    db = client[into]
    kq = {}
    for ten, m in mf["collections"].items():
        _nap_collection(db[ten], thu_muc / f"{ten}.jsonl.gz", m.get("chi_muc", []))
        kq[ten] = (m["so_ban_ghi"], db[ten].count_documents({}))
    return kq
