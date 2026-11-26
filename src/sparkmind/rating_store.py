"""Chấm điểm trên web: đợt chấm (rating_batches), mục cần chấm (rating_items), điểm (ratings). Cấu trúc theo docs/erd.dbml.

Người chấm CHỈ nhận dữ liệu qua `muc_cho_nguoi_cham` (danh sách trắng): không có participant_id, nhãn dữ liệu, cờ hay điểm người kia.
Điểm AI (ai_scores, khóa item_code) làm sau, chưa có code ở đây.
"""
import re

from pymongo.errors import DuplicateKeyError

from . import config, rating_content as nd
from .research_store import LoiNghiepVu
from .thoi_gian import utc_now

COL_DOT = "rating_batches"
COL_MUC = "rating_items"
COL_DIEM = "ratings"
MAU_TEN_DOT = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
TRUONG_CHO_NGUOI_CHAM = ("item_code", "game", "noi_dung")   # danh sách trắng: chỉ ba trường này của rating_items ra ngoài


def tao_chi_muc_cham(db) -> None:
    db[COL_DOT].create_index("name", unique=True)
    db[COL_MUC].create_index("item_code", unique=True)
    db[COL_MUC].create_index([("rating_batch", 1), ("participant_id", 1), ("game", 1), ("nguon_khoa", 1)], unique=True)
    db[COL_DIEM].create_index([("item_code", 1), ("rater", 1)], unique=True)


def lay_dot(db, ten: str) -> dict | None:
    return db[COL_DOT].find_one({"name": ten})


def dot_cua_nguoi_cham(db, username: str) -> list:
    """Các đợt giao cho người chấm này: đợt có danh sách raters rỗng (giao cho mọi người chấm) hoặc có tên người này."""
    return list(db[COL_DOT].find({"$or": [{"raters": []}, {"raters": username}]}).sort("name", 1))


def dat_khoa_dot(db, ten: str, khoa: bool) -> dict:
    """Khóa/mở một đợt. Khóa thì người chấm không lưu hay sửa được nữa."""
    kq = db[COL_DOT].update_one({"name": ten}, {"$set": {"locked": khoa, "locked_at": utc_now() if khoa else None}})
    if not kq.matched_count:
        raise LoiNghiepVu(404, "dot_khong_co")
    return lay_dot(db, ten)


def muc_cho_nguoi_cham(muc: dict) -> dict:
    """Chỉ các trường trong TRUONG_CHO_NGUOI_CHAM (không bao giờ participant_id, prompt_id, data_label...)."""
    return {k: muc[k] for k in TRUONG_CHO_NGUOI_CHAM}


def _muc_cua_nguoi_cham(db, username: str, item_code: str) -> tuple:
    """Trả (mục, đợt). Mục không tồn tại hoặc thuộc đợt không giao cho người này: cùng một lỗi 404 (không đoán được qua mã)."""
    muc = db[COL_MUC].find_one({"item_code": item_code})
    dot = next((d for d in dot_cua_nguoi_cham(db, username) if muc and d["name"] == muc["rating_batch"]), None)
    if not muc or not dot:
        raise LoiNghiepVu(404, "muc_khong_co")
    return muc, dot


def danh_sach_muc(db, username: str) -> dict:
    """Danh sách mục theo thứ tự cố định (đợt, rồi thu_tu), kèm đã chấm xong chưa và tiến độ n/N. Không có nội dung."""
    dot = dot_cua_nguoi_cham(db, username)
    ten_dot = [d["name"] for d in dot]
    muc = list(db[COL_MUC].find({"rating_batch": {"$in": ten_dot}}, {"item_code": 1, "game": 1, "rating_batch": 1}).sort([("rating_batch", 1), ("thu_tu", 1)]))
    xong = {r["item_code"] for r in db[COL_DIEM].find({"rater": username, "hoan_tat": True}, {"item_code": 1})}
    ds = [{"item_code": m["item_code"], "game": m["game"], "da_cham": m["item_code"] in xong} for m in muc]
    return {"muc": ds, "tong": len(ds), "da_cham": sum(1 for m in ds if m["da_cham"]),
            "dot": [{"name": d["name"], "locked": bool(d.get("locked"))} for d in dot]}


def lay_muc_de_cham(db, username: str, item_code: str) -> dict:
    """Nội dung một mục (danh sách trắng) và điểm của CHÍNH người này (nếu có)."""
    muc, dot = _muc_cua_nguoi_cham(db, username, item_code)
    r = db[COL_DIEM].find_one({"item_code": item_code, "rater": username})
    cua_toi = {"diem": r["diem"], "ghi_chu": r.get("ghi_chu", ""), "hoan_tat": r["hoan_tat"]} if r else None
    return {**muc_cho_nguoi_cham(muc), "locked": bool(dot.get("locked")), "rating": cua_toi}


def _giay(v) -> int:
    return max(0, min(int(v or 0), config.RATING_GIAY_TOI_DA_MOT_MUC))


def luu_diem(db, username: str, item_code: str, diem, ghi_chu: str, giay) -> dict:
    """Lưu/sửa điểm của người chấm cho một mục. Đợt đã khóa thì từ chối. Thời gian lần đầu lưu vào thoi_gian_cham_giay, lần sửa cộng vào thoi_gian_sua_giay."""
    muc, dot = _muc_cua_nguoi_cham(db, username, item_code)
    if dot.get("locked"):
        raise LoiNghiepVu(423, "dot_da_khoa")
    try:
        sach, hoan_tat = nd.kiem_tra_diem(muc["game"], diem)
    except ValueError:
        raise LoiNghiepVu(422, "diem_khong_hop_le")
    return _ghi(db, username, muc, {"diem": sach, "hoan_tat": hoan_tat, "ghi_chu": (ghi_chu or "").strip()[:1000]}, _giay(giay))


def _ghi(db, username: str, muc: dict, gia_tri: dict, giay: int) -> dict:
    bay_gio, khoa = utc_now(), {"item_code": muc["item_code"], "rater": username}
    cu = db[COL_DIEM].find_one(khoa)
    if cu:
        db[COL_DIEM].update_one(khoa, {"$set": {**gia_tri, "sua_luc": bay_gio, "thoi_gian_sua_giay": cu.get("thoi_gian_sua_giay", 0) + giay}})
    else:
        moi = {**khoa, **gia_tri, "rating_batch": muc["rating_batch"], "thoi_gian_cham_giay": giay, "thoi_gian_sua_giay": 0, "tao_luc": bay_gio, "sua_luc": bay_gio}
        try:
            db[COL_DIEM].insert_one(moi)
        except DuplicateKeyError:   # hai yêu cầu cùng lúc: coi như sửa
            return _ghi(db, username, muc, gia_tri, giay)
    return {"ok": True, "hoan_tat": gia_tri["hoan_tat"]}
