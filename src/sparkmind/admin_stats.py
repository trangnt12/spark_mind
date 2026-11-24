"""Thống kê tổng hợp cho trang chủ quản trị (GET /api/admin/stats).

CHỈ trả số đếm tổng hợp: không email, không tên, không IP, không nội dung trả lời.
Mọi số đều tính bằng aggregation trong MongoDB; kết quả được nhớ 30 giây.
"""
import time
from datetime import timedelta

from . import config, flags
from .research_store import COL_HANH_VI, COL_MA, COL_NGUOI, COL_TU_DANH_GIA
from .game_store import COL_GAME
from .thoi_gian import utc_now

GIAY_NHO_DEM = 30
SO_NGAY = 30
_nho = {}   # (id(db), an_thu) -> (thời điểm tính, kết quả)


def xoa_cache() -> None:
    """Xóa bộ nhớ đệm (dùng khi thử)."""
    _nho.clear()


# ---------- Bộ lọc dữ liệu thử ----------

def loc_an_thu(an_thu: bool) -> dict:
    """Bỏ bản ghi có data_label thuộc nhãn thử (thu, pilot). Bản ghi chưa có nhãn được coi là "that" nên vẫn hiện."""
    return {"data_label": {"$nin": list(config.NHAN_DU_LIEU_THU)}} if an_thu else {}


# ---------- Khối đếm dùng chung ----------

def _nhom(db, bang: str, loc: dict, truong: str) -> dict:
    """Đếm số tài liệu theo từng giá trị của một trường: {giá trị: số}."""
    kq = db[bang].aggregate([{"$match": loc}, {"$group": {"_id": "$" + truong, "n": {"$sum": 1}}}])
    return {str(d["_id"]) if d["_id"] is not None else "khac": d["n"] for d in kq}


def _theo_ngay(db, bang: str, loc: dict, truong: str) -> list:
    """Số tài liệu mỗi ngày trong 30 ngày gần nhất (ngày không có thì 0), theo giờ UTC."""
    hom_nay = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    dau = hom_nay - timedelta(days=SO_NGAY - 1)
    kq = db[bang].aggregate([
        {"$match": {**loc, truong: {"$gte": dau}}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$" + truong}}, "n": {"$sum": 1}}}])
    dem = {d["_id"]: d["n"] for d in kq}
    ngay = [(dau + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(SO_NGAY)]
    return [{"ngay": n, "n": dem.get(n, 0)} for n in ngay]


def _tong_dieu_kien(db, bang: str, loc: dict, dieu_kien: dict) -> dict:
    """Một aggregation đếm nhiều điều kiện cùng lúc: {tên: số}. dieu_kien = {tên: biểu thức $cond}."""
    nhom = {"_id": None, **{ten: {"$sum": {"$cond": [bt, 1, 0]}} for ten, bt in dieu_kien.items()}}
    kq = list(db[bang].aggregate([{"$match": loc}, {"$group": nhom}]))
    return {ten: (kq[0][ten] if kq else 0) for ten in dieu_kien}


# ---------- Hướng 1 ----------

def _ngay_moi_nhat(db, loc: dict):
    kq = list(db[config.COL_CLEAN].aggregate([{"$match": loc}, {"$group": {"_id": None, "t": {"$max": "$thoi_gian"}}}]))
    return kq[0]["t"].isoformat() if kq and kq[0]["t"] else None


def thong_ke_huong1(db, an_thu: bool) -> dict:
    loc, bang = loc_an_thu(an_thu), config.COL_CLEAN
    ban = _tong_dieu_kien(db, bang, loc, {k: {"$eq": ["$in_" + k, True]} for k in ("chinh", "chat", "rat_chat")})
    return {"tong": db[bang].count_documents(loc), "muc_tieu": config.MUC_TIEU_HUONG1,
            "theo_nguon": _nhom(db, bang, loc, "nguon"), "theo_dot": _nhom(db, bang, loc, "dot"),
            "ban": ban, "theo_ngay": _theo_ngay(db, bang, loc, "thoi_gian"),
            "moi_nhat": _ngay_moi_nhat(db, loc)}


# ---------- Hướng 2 ----------

def _thong_ke_ma(db, an_thu: bool) -> dict:
    loc = loc_an_thu(an_thu)
    dung = db[COL_MA].count_documents({**loc, "is_used": True})
    tong = db[COL_MA].count_documents(loc)
    return {"da_tao": tong, "da_dung": dung, "chua_dung": tong - dung, "theo_nguon": _nhom(db, COL_MA, loc, "source")}


def _pheu(db, loc_nguoi: dict) -> list:
    """Phễu từ đồng ý đến hoàn thành: [{"khoa", "n"}]. Mỗi bước đếm số người (mỗi bảng con chỉ một dòng/người/game)."""
    con = lambda them=None: {**loc_nguoi, **(them or {})}   # noqa: E731  (bảng con cũng mang data_label)
    buoc = [("consent", db[COL_NGUOI].count_documents({**loc_nguoi, "consent": True})),
            ("info", db[COL_NGUOI].count_documents({**loc_nguoi, "grade": {"$ne": None}, "school_name": {"$ne": None}})),
            ("behavior", db[COL_HANH_VI].count_documents(con())),
            ("self_assessment", db[COL_TU_DANH_GIA].count_documents(con()))]
    for g in (1, 2, 3):
        buoc.append((f"game{g}", db[COL_GAME].count_documents(con({"game": g, "submitted_at": {"$ne": None}}))))
    buoc.append(("completed", db[COL_NGUOI].count_documents({**loc_nguoi, "completed_at": {"$ne": None}})))
    return [{"khoa": k, "n": n} for k, n in buoc]


def _co_gian_lan(db, loc_nguoi: dict) -> dict:
    """Số bài game đã nộp và số bài bị gắn cờ (nộp trễ, có dán, có rời tab)."""
    loc = {**loc_nguoi, "submitted_at": {"$ne": None}}
    return _tong_dieu_kien(db, COL_GAME, loc, {
        "da_nop": {"$eq": [1, 1]}, "over_time": {"$eq": ["$over_time", True]},
        "paste": {"$gt": ["$paste_count", 0]}, "tab_leave": {"$gt": ["$tab_leave_count", 0]}})


def thong_ke_co(db, loc_nguoi: dict) -> dict:
    """Số NGƯỜI bị từng cờ chống gian lận (participants.flags). Chỉ số đếm, không thông tin cá nhân.

    theo_co: {"mã:bước": số người}; theo_ma: {"mã": số người bị cờ đó ở ít nhất một bước};
    co_it_nhat_mot: số người có flag_count > 0 (KHÔNG tính bi_gian_doan, vì cờ này chỉ để tham khảo);
    khong_co: số người flag_count = 0 hoặc chưa tính cờ (người chưa nộp bước nào cũng vào đây).
    Đọc từng người (chỉ trường flags) vì cần đếm người chứ không đếm cờ; số người hướng 2 chỉ vài trăm.
    """
    theo_co, theo_ma, tong, co_cho_so_sanh = {}, {}, 0, 0
    for nguoi in db[COL_NGUOI].find(loc_nguoi, {"flags": 1}):
        tong += 1
        cac_co = nguoi.get("flags") or []
        co_cho_so_sanh += flags.dem_co(cac_co) > 0
        for co in cac_co:
            theo_co[co] = theo_co.get(co, 0) + 1
        for ma in {flags.ma_co(c) for c in cac_co}:
            theo_ma[ma] = theo_ma.get(ma, 0) + 1
    return {"tong": tong, "theo_co": theo_co, "theo_ma": theo_ma, "co_it_nhat_mot": co_cho_so_sanh,
            "khong_co": tong - co_cho_so_sanh, "tham_khao": list(config.CO_THAM_KHAO)}


def thong_ke_huong2(db, an_thu: bool) -> dict:
    loc_nguoi = loc_an_thu(an_thu)
    return {"ma": _thong_ke_ma(db, an_thu), "muc_tieu": config.MUC_TIEU_HUONG2,
            "pheu": _pheu(db, loc_nguoi),
            "nguoi_moi_theo_ngay": _theo_ngay(db, COL_NGUOI, loc_nguoi, "started_at"),
            "co": _co_gian_lan(db, loc_nguoi), "co_chong_gian_lan": thong_ke_co(db, loc_nguoi)}


# ---------- Hệ thống và hàm chính ----------

def thong_ke_he_thong(db) -> dict | None:
    """Dung lượng database (MB) từ dbStats. Không lấy được (vd khi thử) thì None."""
    try:
        s = db.command("dbStats")
    except Exception:   # noqa: BLE001 - môi trường không hỗ trợ dbStats thì bỏ qua phần này
        return None
    mb = lambda x: round(x / 1048576, 1)   # noqa: E731
    return {"du_lieu_mb": mb(s.get("dataSize", 0)), "luu_tru_mb": mb(s.get("storageSize", 0)),
            "chi_muc_mb": mb(s.get("indexSize", 0)), "gioi_han_mb": config.ATLAS_GIOI_HAN_MB}


def lay_thong_ke(db, an_thu: bool = True) -> dict:
    """Thống kê đầy đủ, nhớ 30 giây theo (db, an_thu)."""
    khoa, bay_gio = (id(db), bool(an_thu)), time.monotonic()
    if khoa in _nho and bay_gio - _nho[khoa][0] < GIAY_NHO_DEM:
        return _nho[khoa][1]
    kq = {"an_du_lieu_thu": bool(an_thu), "tao_luc": utc_now().isoformat(), "huong1": thong_ke_huong1(db, an_thu),
          "huong2": thong_ke_huong2(db, an_thu), "he_thong": thong_ke_he_thong(db)}
    _nho[khoa] = (bay_gio, kq)
    return kq
