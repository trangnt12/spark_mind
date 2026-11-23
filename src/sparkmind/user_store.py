"""Tài khoản quản trị (collection users). Cấu trúc theo docs/erd.dbml. KHÔNG bao giờ trả password_hash ra ngoài."""
import re

from pymongo.errors import DuplicateKeyError

from . import passwords
from .research_store import LoiNghiepVu
from .thoi_gian import utc_now

COL_USERS = "users"
VAI_TRO = ("admin", "viewer", "rater")
VAI_TRO_ADMIN_TAO_DUOC = ("viewer", "rater")   # admin tạo viewer/rater qua web; tài khoản admin tạo bằng scripts/create_user.py
MAU_USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")
TRUONG_CONG_KHAI = ("username", "display_name", "role", "must_change_password", "is_active",
                    "created_at", "created_by", "last_login_at", "failed_attempts", "locked_until")


def tao_chi_muc_user(db) -> None:
    db[COL_USERS].create_index("username", unique=True)


def chuan_hoa_username(username: str) -> str:
    """Chữ thường, bỏ khoảng trắng hai đầu."""
    return (username or "").strip().lower()


def cong_khai(user: dict | None) -> dict | None:
    """Chỉ giữ các trường an toàn để trả ra ngoài (không có password_hash, không có _id)."""
    return {k: user.get(k) for k in TRUONG_CONG_KHAI} if user else None


def tim_user(db, username: str) -> dict | None:
    return db[COL_USERS].find_one({"username": chuan_hoa_username(username)})


def tao_user(db, username: str, display_name: str, role: str, mat_khau: str,
             nguoi_tao: str, bat_buoc_doi_mk: bool = True) -> dict:
    """Tạo tài khoản. Lỗi nghiệp vụ: 422 (tên/vai trò/mật khẩu không hợp lệ), 409 (trùng tên)."""
    ten = chuan_hoa_username(username)
    if not MAU_USERNAME.match(ten):
        raise LoiNghiepVu(422, "bad_username")
    if role not in VAI_TRO:
        raise LoiNghiepVu(422, "bad_role")
    if passwords.kiem_tra_do_manh(mat_khau, ten):
        raise LoiNghiepVu(422, "weak_password")
    doc = {"username": ten, "display_name": (display_name or ten).strip()[:80], "role": role,
           "password_hash": passwords.bam(mat_khau), "must_change_password": bat_buoc_doi_mk, "is_active": True,
           "created_at": utc_now(), "created_by": nguoi_tao, "last_login_at": None,
           "failed_attempts": 0, "locked_until": None}
    try:
        db[COL_USERS].insert_one(doc)
    except DuplicateKeyError:
        raise LoiNghiepVu(409, "username_taken")
    return doc


def danh_sach(db) -> list:
    """Mọi tài khoản dạng công khai, sắp theo tên."""
    return [cong_khai(u) for u in db[COL_USERS].find().sort("username", 1)]


def dat_mat_khau(db, user: dict, mat_khau: str, bat_buoc_doi: bool) -> None:
    """Đổi mật khẩu (đã kiểm tra độ mạnh ở nơi gọi) và gỡ khóa."""
    db[COL_USERS].update_one({"_id": user["_id"]}, {"$set": {
        "password_hash": passwords.bam(mat_khau), "must_change_password": bat_buoc_doi,
        "failed_attempts": 0, "locked_until": None}})


def dat_hoat_dong(db, user: dict, hoat_dong: bool) -> None:
    """Khóa (False) hoặc mở (True) tài khoản. Mở thì xóa luôn bộ đếm đăng nhập sai."""
    sua = {"is_active": hoat_dong}
    if hoat_dong:
        sua.update({"failed_attempts": 0, "locked_until": None})
    db[COL_USERS].update_one({"_id": user["_id"]}, {"$set": sua})


def ghi_dang_nhap_ok(db, user: dict) -> None:
    db[COL_USERS].update_one({"_id": user["_id"]}, {"$set": {
        "last_login_at": utc_now(), "failed_attempts": 0, "locked_until": None}})


def ghi_dang_nhap_sai(db, user: dict | None, bi_khoa_den) -> None:
    """Tăng bộ đếm sai của user (chỉ để hiển thị). locked_until ghi lần khóa gần nhất, KHÔNG dùng để chặn
    (việc chặn theo cặp tên + IP nằm ở session_store)."""
    if not user:
        return
    sua = {"$inc": {"failed_attempts": 1}}
    if bi_khoa_den:
        sua["$set"] = {"locked_until": bi_khoa_den}
    db[COL_USERS].update_one({"_id": user["_id"]}, sua)


def dem_admin_hoat_dong(db) -> int:
    return db[COL_USERS].count_documents({"role": "admin", "is_active": True})
