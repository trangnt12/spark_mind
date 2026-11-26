"""Trang "Sức khỏe hệ thống" (admin, viewer): kết nối DB, bộ nhớ, số bản ghi, chỉ mục bắt buộc, độ trễ truy vấn, mô hình, công tắc.

Nguyên tắc: CHỈ trả số liệu vận hành. Không bao giờ trả chuỗi kết nối, khóa bí mật, email hay nội dung người chơi.
Cấu hình bí mật chỉ báo "đã có / chưa có" (true/false). Lỗi chỉ báo TÊN loại lỗi, không báo nội dung lỗi (có thể chứa chuỗi kết nối).
Kết quả được nhớ ngắn (GIAY_NHO_DEM giây) để mở trang liên tục không làm nặng database.
"""
import platform
import time

from . import audit, config, game_store, rating_store, research_store as rs, session_store, settings_store, user_store
from .memory import rss_mb
from .thoi_gian import utc_now

GIAY_NHO_DEM = 15
KHOI_DONG = time.monotonic()
_nho = {"db": None, "luc": 0.0, "gia_tri": None}

# Chỉ mục bắt buộc: (collection, danh sách (trường, chiều), unique, ghi chú TTL). Khớp với các hàm tao_chi_muc_* khi server khởi động.
CHI_MUC_BAT_BUOC = [
    (rs.COL_MA, [("code", 1)], True), (rs.COL_NGUOI, [("code_id", 1)], True), (rs.COL_NGUOI, [("session_token", 1)], True),
    (rs.COL_NGUOI, [("email", 1)], False), (rs.COL_NGUOI, [("ip_hash", 1)], False),
    (rs.COL_HANH_VI, [("participant_id", 1)], True), (rs.COL_TU_DANH_GIA, [("participant_id", 1)], True),
    (game_store.COL_GAME, [("participant_id", 1), ("game", 1)], True),
    (user_store.COL_USERS, [("username", 1)], True),
    (session_store.COL_PHIEN, [("expires_at", 1)], False), (session_store.COL_PHIEN, [("user_id", 1)], False),
    (session_store.COL_THU_DANG_NHAP, [("expires_at", 1)], False), (session_store.COL_THU_DANG_NHAP, [("user_id", 1)], False),
    (audit.COL_AUDIT, [("at", 1)], False),
    (rating_store.COL_DOT, [("name", 1)], True), (rating_store.COL_MUC, [("item_code", 1)], True),
    (rating_store.COL_MUC, [("rating_batch", 1), ("participant_id", 1), ("game", 1), ("nguon_khoa", 1)], True),
    (rating_store.COL_DIEM, [("item_code", 1), ("rater", 1)], True),
]

# Vài truy vấn đại diện cho việc người dùng thật làm (đều đi qua chỉ mục): (tên, collection, bộ lọc)
TRUY_VAN_MAU = [
    ("nhap_ma", rs.COL_MA, {"code": "__suc_khoe__"}),
    ("tim_nguoi_theo_token", rs.COL_NGUOI, {"session_token": "__suc_khoe__"}),
    ("dang_nhap_quan_tri", user_store.COL_USERS, {"username": "__suc_khoe__"}),
    ("cai_dat", settings_store.COL_CAI_DAT, {"_id": settings_store.ID_CAI_DAT}),
]


def xoa_cache() -> None:
    """Quên bộ nhớ đệm (dùng khi thử)."""
    _nho.update(db=None, luc=0.0, gia_tri=None)


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


def kiem_tra_ket_noi(db) -> dict:
    """Gửi lệnh ping tới database, đo độ trễ. Lỗi thì chỉ báo tên loại lỗi."""
    t0 = time.perf_counter()
    try:
        db.command("ping")
        return {"ok": True, "do_tre_ms": _ms(t0), "ten_db": db.name}
    except Exception as loi:
        return {"ok": False, "do_tre_ms": None, "ten_db": db.name, "loi": type(loi).__name__}


def dem_ban_ghi(db) -> list:
    """Số bản ghi ước lượng của từng collection (estimated_document_count: đọc metadata, không quét bảng)."""
    kq = []
    for ten in sorted(db.list_collection_names()):
        kq.append({"ten": ten, "so_ban_ghi": db[ten].estimated_document_count()})
    return kq


def _chi_muc_co(db, collection: str, khoa: list, unique: bool) -> bool:
    """Có chỉ mục đúng trường (và đúng unique) trong collection không."""
    try:
        thong_tin = db[collection].index_information()
    except Exception:
        return False
    return any(list(c.get("key", [])) == khoa and bool(c.get("unique")) == unique for c in thong_tin.values())


def kiem_tra_chi_muc(db) -> dict:
    """Từng chỉ mục bắt buộc: có hay thiếu. `thieu` = số chỉ mục chưa có (server tạo lại khi khởi động lại)."""
    ds = [{"collection": c, "truong": ", ".join(t for t, _ in k), "unique": u, "co": _chi_muc_co(db, c, k, u)}
          for c, k, u in CHI_MUC_BAT_BUOC]
    return {"chi_tiet": ds, "thieu": sum(1 for d in ds if not d["co"])}


def do_do_tre_truy_van(db) -> list:
    """Chạy vài truy vấn đại diện (chỉ đọc, tìm khóa không tồn tại) và đo mili giây."""
    kq = []
    for ten, collection, loc in TRUY_VAN_MAU:
        t0 = time.perf_counter()
        try:
            db[collection].find_one(loc)
            kq.append({"ten": ten, "ms": _ms(t0), "ok": True})
        except Exception as loi:
            kq.append({"ten": ten, "ms": None, "ok": False, "loi": type(loi).__name__})
    return kq


def dung_luong_db(db):
    """Dung lượng database (MB) và giới hạn gói Atlas M0; None nếu server không cho đọc (ví dụ DB giả khi thử)."""
    try:
        st = db.command("dbstats")
        mb = round((st["dataSize"] + st["indexSize"]) / 1048576, 1)
    except Exception:
        return None
    return {"mb": mb, "gioi_han_mb": config.ATLAS_GIOI_HAN_MB}


def thong_tin_mo_hinh() -> dict:
    """Phiên bản mô hình B4 đang nạp. Lỗi nạp (thiếu file) chỉ báo tên loại lỗi."""
    from . import predict
    try:
        mh = predict.nap_mo_hinh()
        return {"ok": True, "phien_ban": mh["phien_ban"], "da_nap": True}
    except Exception as loi:
        return {"ok": False, "phien_ban": None, "da_nap": False, "loi": type(loi).__name__}


def cong_tac(db) -> dict:
    """Các công tắc đang bật/tắt (đã tính cả hạn đóng hướng 2)."""
    tt = settings_store.trang_thai(db)
    return {"huong2_mo": tt["huong2_dang_mo"], "huong1_web_mo": tt["huong1_web_mo"], "demo_mo": tt["demo_mo"],
            "co_thong_bao": bool(tt["thong_bao"])}


def cau_hinh() -> dict:
    """Biến cấu hình bắt buộc đã có chưa (true/false). KHÔNG BAO GIỜ trả giá trị."""
    return {"MONGODB_URI": bool(config.MONGODB_URI), "INGEST_SECRET": bool(config.INGEST_SECRET),
            "IP_HASH_SECRET": bool(config.IP_HASH_SECRET)}


def tien_trinh() -> dict:
    """Bộ nhớ (rss, MB), thời gian chạy, bản Python."""
    try:
        rss = rss_mb()
    except Exception:
        rss = None
    return {"rss_mb": rss, "chay_giay": int(time.monotonic() - KHOI_DONG), "python": platform.python_version()}


def tinh_suc_khoe(db) -> dict:
    """Gom mọi phần. Nếu không ping được database thì bỏ qua các phần cần database (tránh chờ hết thời gian từng phần)."""
    kn = kiem_tra_ket_noi(db)
    kq = {"tinh_luc": utc_now().isoformat(), "nho_giay": GIAY_NHO_DEM, "ket_noi": kn, "tien_trinh": tien_trinh(),
          "mo_hinh": thong_tin_mo_hinh(), "cau_hinh": cau_hinh()}
    if kn["ok"]:
        kq.update(ban_ghi=dem_ban_ghi(db), chi_muc=kiem_tra_chi_muc(db), truy_van=do_do_tre_truy_van(db),
                  dung_luong=dung_luong_db(db), cong_tac=cong_tac(db))
    return kq


def lay_suc_khoe(db) -> dict:
    """Như tinh_suc_khoe nhưng nhớ GIAY_NHO_DEM giây (mở trang liên tục không làm nặng database)."""
    bay_gio = time.monotonic()
    if _nho["db"] is db and bay_gio - _nho["luc"] < GIAY_NHO_DEM:
        return _nho["gia_tri"]
    gia_tri = tinh_suc_khoe(db)
    _nho.update(db=db, luc=bay_gio, gia_tri=gia_tri)
    return gia_tri
