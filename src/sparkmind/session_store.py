"""Phiên đăng nhập lưu ở server (admin_sessions) và bộ đếm đăng nhập sai (login_attempts).

Token ngẫu nhiên chỉ gửi cho trình duyệt qua cookie; DB chỉ lưu băm SHA-256 của nó.
Phiên hết hạn sau 2 giờ không hoạt động hoặc tối đa 12 giờ kể từ lúc đăng nhập.
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from .thoi_gian import utc_now

COL_PHIEN = "admin_sessions"
COL_THU_DANG_NHAP = "login_attempts"
GIO_KHONG_HOAT_DONG = timedelta(hours=2)
GIO_TOI_DA = timedelta(hours=12)
SO_LAN_SAI_TOI_DA = 5
CUA_SO_SAI = timedelta(minutes=15)
THOI_GIAN_KHOA = timedelta(minutes=15)


def tao_chi_muc_phien(db) -> None:
    """TTL index: Mongo tự xóa phiên khi quá expires_at (có thể trễ ~1 phút, nên code vẫn tự kiểm tra hạn)."""
    db[COL_PHIEN].create_index("expires_at", expireAfterSeconds=0)
    db[COL_PHIEN].create_index("user_id")
    db[COL_THU_DANG_NHAP].create_index("expires_at", expireAfterSeconds=0)
    db[COL_THU_DANG_NHAP].create_index("user_id")


def bam_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _het_han(created_at: datetime, bay_gio: datetime) -> datetime:
    return min(bay_gio + GIO_KHONG_HOAT_DONG, created_at + GIO_TOI_DA)


def tao_phien(db, user: dict) -> tuple:
    """Tạo phiên mới. Trả (token gửi cookie, csrf_token)."""
    token, csrf, bay_gio = secrets.token_urlsafe(32), secrets.token_urlsafe(32), utc_now()
    db[COL_PHIEN].insert_one({"_id": bam_token(token), "user_id": user["_id"], "csrf_token": csrf,
                              "created_at": bay_gio, "last_seen_at": bay_gio,
                              "expires_at": _het_han(bay_gio, bay_gio)})
    return token, csrf


def tim_phien(db, token: str) -> dict | None:
    """Tìm phiên còn hiệu lực và gia hạn thời gian không hoạt động. Hết hạn thì xóa và trả None."""
    if not token:
        return None
    bay_gio = utc_now()
    phien = db[COL_PHIEN].find_one({"_id": bam_token(token)})
    if not phien:
        return None
    if bay_gio - phien["last_seen_at"] > GIO_KHONG_HOAT_DONG or bay_gio - phien["created_at"] > GIO_TOI_DA:
        db[COL_PHIEN].delete_one({"_id": phien["_id"]})
        return None
    het = _het_han(phien["created_at"], bay_gio)
    db[COL_PHIEN].update_one({"_id": phien["_id"]}, {"$set": {"last_seen_at": bay_gio, "expires_at": het}})
    return phien


def xoa_phien(db, token: str) -> None:
    db[COL_PHIEN].delete_one({"_id": bam_token(token or "")})


def xoa_phien_cua_user(db, user_id) -> int:
    """Đăng xuất mọi nơi (khi đổi/đặt lại mật khẩu, khóa tài khoản)."""
    return db[COL_PHIEN].delete_many({"user_id": user_id}).deleted_count


# ---------- Chống dò mật khẩu: 5 lần sai trong 15 phút theo (username + IP) thì khóa 15 phút ----------

def khoa_thu(username: str, ip: str) -> str:
    """Khóa đếm = băm (username|IP): không lưu IP thô, và dùng được cả khi username không tồn tại."""
    return hashlib.sha256(f"{username}|{ip}".encode("utf-8")).hexdigest()


def giay_con_khoa(db, khoa: str) -> int:
    """Số giây còn bị khóa; 0 nếu không bị khóa."""
    d = db[COL_THU_DANG_NHAP].find_one({"_id": khoa})
    if not d or not d.get("locked_until"):
        return 0
    return max(0, int((d["locked_until"] - utc_now()).total_seconds()) + 1)


def ghi_that_bai(db, khoa: str, user_id=None):
    """Ghi một lần sai. Trả thời điểm khóa nếu lần này vừa đủ 5 lần, ngược lại None."""
    bay_gio = utc_now()
    bang = db[COL_THU_DANG_NHAP]
    bang.update_one({"_id": khoa, "window_start": {"$lt": bay_gio - CUA_SO_SAI}},
                    {"$set": {"count": 0, "window_start": bay_gio, "locked_until": None}})   # cửa sổ cũ: đếm lại
    d = bang.find_one_and_update({"_id": khoa}, {"$inc": {"count": 1}, "$set": {"user_id": user_id},
                                                 "$setOnInsert": {"window_start": bay_gio}},
                                 upsert=True, return_document=True)
    if d["count"] >= SO_LAN_SAI_TOI_DA:
        khoa_den = bay_gio + THOI_GIAN_KHOA
        bang.update_one({"_id": khoa}, {"$set": {"locked_until": khoa_den, "expires_at": khoa_den}})
        return khoa_den
    bang.update_one({"_id": khoa}, {"$set": {"expires_at": d["window_start"] + CUA_SO_SAI}})
    return None


def xoa_dem_sai(db, khoa: str = None, user_id=None) -> None:
    """Xóa bộ đếm sai (đăng nhập đúng, hoặc admin mở khóa/đặt lại mật khẩu cho user)."""
    if khoa:
        db[COL_THU_DANG_NHAP].delete_one({"_id": khoa})
    if user_id:
        db[COL_THU_DANG_NHAP].delete_many({"user_id": user_id})
