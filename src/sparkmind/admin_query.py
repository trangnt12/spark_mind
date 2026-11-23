"""Truy vấn danh sách cho trang dữ liệu: tìm kiếm, lọc, sắp xếp, phân trang phía server. Chỉ dùng trường khai báo trong registry."""
import math
import re

from bson import ObjectId
from bson.errors import InvalidId

from . import admin_registry as reg
from .admin_stats import loc_an_thu
from .admin_view import lam_ve


class LoiTruyVan(ValueError):
    """Tham số truy vấn sai (mã lỗi máy đọc được nằm trong args[0])."""


def id_ung_vien(text: str) -> list:
    """Một chuỗi ID có thể là chuỗi, ObjectId hoặc số: trả mọi khả năng để khớp với _id thật."""
    ds = [text]
    if re.fullmatch(r"[0-9a-fA-F]{24}", text or ""):
        try:
            ds.append(ObjectId(text))
        except InvalidId:
            pass
    if re.fullmatch(r"-?\d{1,18}", text or ""):
        ds.append(int(text))
    return ds


def _ep_kieu(kieu: str, gia_tri: str, lua_chon):
    """Đổi chuỗi trên URL sang kiểu của trường. Sai thì báo bo_loc_sai."""
    try:
        if kieu == "bool":
            return {"true": True, "false": False}[gia_tri.lower()]
        if kieu == "int":
            return int(gia_tri)
    except (KeyError, ValueError):
        raise LoiTruyVan("bo_loc_sai")
    if kieu == "enum" and lua_chon and gia_tri not in lua_chon:
        raise LoiTruyVan("bo_loc_sai")
    return gia_tri


def loc_theo_truong(cfg: dict, tham_so: dict) -> list:
    """Các điều kiện lọc từ tham số f.<khóa>=<giá trị>. Khóa không có trong registry thì báo lỗi."""
    cho_phep = {k: (kieu, lc) for k, _, kieu, lc in cfg["loc"]}
    dk = []
    for ten, gt in tham_so.items():
        if not ten.startswith("f.") or gt == "":
            continue
        khoa = ten[2:]
        if khoa not in cho_phep:
            raise LoiTruyVan("bo_loc_sai")
        kieu, lua_chon = cho_phep[khoa]
        dk.append({khoa: _ep_kieu(kieu, gt, lua_chon)})
    return dk


def loc_tim_kiem(cfg: dict, q: str) -> list:
    """Tìm chữ (regex đã thoát ký tự đặc biệt, không phân biệt hoa thường) trong các trường `tim`, hoặc khớp đúng ID."""
    q = (q or "").strip()[:100]
    if not q:
        return []
    mau = {"$regex": re.escape(q), "$options": "i"}
    hoac = [{k: mau} for k in cfg["tim"]] + [{"_id": {"$in": id_ung_vien(q)}}]
    return [{"$or": hoac}]


def xay_loc(cfg: dict, tham_so: dict, an_thu: bool) -> dict:
    """Bộ lọc MongoDB đầy đủ: tìm kiếm + lọc theo trường + ẩn dữ liệu thử (nếu bảng có nhãn)."""
    dk = loc_tim_kiem(cfg, tham_so.get("q", "")) + loc_theo_truong(cfg, tham_so)
    if an_thu and cfg["co_nhan"]:
        dk.append(loc_an_thu(True))
    return {"$and": dk} if dk else {}


def kieu_sap_xep(cfg: dict, tham_so: dict) -> list:
    """[(trường, hướng)]: chỉ nhận trường trong sap_xep (hoặc _id); luôn thêm _id để thứ tự ổn định khi phân trang."""
    truong, chieu = cfg["mac_dinh"]
    if tham_so.get("sort"):
        truong = tham_so["sort"]
        chieu = -1 if tham_so.get("order", "asc") == "desc" else 1
    if truong != "_id" and truong not in cfg["sap_xep"]:
        raise LoiTruyVan("bo_loc_sai")
    return [(truong, chieu)] + ([("_id", 1)] if truong != "_id" else [])


def _so(tham_so: dict, khoa: str, mac_dinh: int, toi_da: int) -> int:
    try:
        return max(1, min(toi_da, int(tham_so.get(khoa, mac_dinh))))
    except ValueError:
        raise LoiTruyVan("bo_loc_sai")


def danh_sach(db, ten: str, cfg: dict, tham_so: dict, vai_tro: str, an_thu: bool) -> dict:
    """Một trang danh sách: {tong, trang, kich_thuoc, so_trang, dong}."""
    loc = xay_loc(cfg, tham_so, an_thu)
    kt = _so(tham_so, "size", reg.KICH_THUOC_TRANG_MAC_DINH, reg.KICH_THUOC_TRANG_TOI_DA)
    tong = db[ten].count_documents(loc)
    so_trang = max(1, math.ceil(tong / kt))
    trang = min(_so(tham_so, "page", 1, 10 ** 6), so_trang)
    cur = db[ten].find(loc).sort(kieu_sap_xep(cfg, tham_so)).skip((trang - 1) * kt).limit(kt)
    return {"tong": tong, "trang": trang, "kich_thuoc": kt, "so_trang": so_trang,
            "dong": [lam_ve(d, cfg, vai_tro) for d in cur]}


def dong_de_xuat(db, ten: str, cfg: dict, tham_so: dict, vai_tro: str, an_thu: bool) -> tuple:
    """Các dòng để xuất CSV (tối đa SO_DONG_XUAT_TOI_DA, cùng bộ lọc và thứ tự như danh sách). Trả (dòng, bị_cắt)."""
    loc = xay_loc(cfg, tham_so, an_thu)
    cur = db[ten].find(loc).sort(kieu_sap_xep(cfg, tham_so)).limit(reg.SO_DONG_XUAT_TOI_DA + 1)
    dong = [lam_ve(d, cfg, vai_tro) for d in cur]
    return dong[:reg.SO_DONG_XUAT_TOI_DA], len(dong) > reg.SO_DONG_XUAT_TOI_DA
