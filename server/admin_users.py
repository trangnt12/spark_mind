"""Quản lý tài khoản (chỉ admin): danh sách, tạo viewer/rater, đặt lại mật khẩu, khóa/mở. Ghi nhật ký mọi thao tác.

Không bao giờ trả password_hash. Mật khẩu tạm (do admin nhập hoặc server tự sinh) chỉ hiện đúng một lần trong phản hồi.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.auth import chay_ma, khoa_ten_dang_nhap, loi, require_role
from sparkmind import passwords, session_store, user_store
from sparkmind.audit import write_audit

router = APIRouter(prefix="/api/admin/users")
chi_admin = require_role("admin")


class TaoUserBody(BaseModel):
    username: str = Field(max_length=64)
    display_name: str = Field(default="", max_length=80)
    role: str = Field(max_length=16)
    temp_password: str | None = Field(default=None, max_length=256)   # bỏ trống: server tự sinh


class DatLaiBody(BaseModel):
    temp_password: str | None = Field(default=None, max_length=256)


class SuaUserBody(BaseModel):
    is_active: bool


def _user_hoac_404(db, username: str) -> dict:
    user = user_store.tim_user(db, username)
    if not user:
        raise loi(404, "user_not_found")
    return user


@router.get("")
def danh_sach(ctx=Depends(chi_admin)):
    return {"users": user_store.danh_sach(ctx["db"])}


@router.post("", status_code=201)
def tao(body: TaoUserBody, ctx=Depends(chi_admin)):
    db, admin = ctx["db"], ctx["user"]
    if body.role not in user_store.VAI_TRO_ADMIN_TAO_DUOC:
        raise loi(422, "bad_role")
    mat_khau = body.temp_password or passwords.tao_mat_khau_tam()
    user = chay_ma(user_store.tao_user, db, body.username, body.display_name, body.role, mat_khau, admin["username"], True)
    write_audit(db, admin, "user_create", user_store.COL_USERS, user["_id"], {"username": user["username"], "role": body.role})
    return {"user": user_store.cong_khai(user), "temp_password": mat_khau}


@router.post("/{username}/reset-password")
def dat_lai_mat_khau(username: str, body: DatLaiBody, ctx=Depends(chi_admin)):
    db, admin = ctx["db"], ctx["user"]
    user = _user_hoac_404(db, username)
    mat_khau = body.temp_password or passwords.tao_mat_khau_tam()
    if passwords.kiem_tra_do_manh(mat_khau, user["username"]):
        raise loi(422, "weak_password")
    user_store.dat_mat_khau(db, user, mat_khau, bat_buoc_doi=True)
    session_store.xoa_phien_cua_user(db, user["_id"])   # đăng xuất mọi nơi
    session_store.xoa_dem_sai(db, user_id=user["_id"])
    session_store.xoa_dem_sai(db, khoa_ten_dang_nhap(user["username"]))
    write_audit(db, admin, "user_reset_password", user_store.COL_USERS, user["_id"], {"username": user["username"]})
    return {"temp_password": mat_khau}


def _kiem_tra_co_the_khoa(db, admin: dict, user: dict, hoat_dong: bool) -> None:
    """Không cho tự khóa mình, và không cho khóa admin cuối cùng (tránh không ai vào được)."""
    if hoat_dong:
        return
    if user["_id"] == admin["_id"]:
        raise loi(409, "cannot_lock_self")
    if user["role"] == "admin" and user_store.dem_admin_hoat_dong(db) <= 1:
        raise loi(409, "last_admin")


@router.patch("/{username}")
def khoa_hoac_mo(username: str, body: SuaUserBody, ctx=Depends(chi_admin)):
    db, admin = ctx["db"], ctx["user"]
    user = _user_hoac_404(db, username)
    _kiem_tra_co_the_khoa(db, admin, user, body.is_active)
    user_store.dat_hoat_dong(db, user, body.is_active)
    if body.is_active:
        session_store.xoa_dem_sai(db, user_id=user["_id"])
        session_store.xoa_dem_sai(db, khoa_ten_dang_nhap(user["username"]))
    else:
        session_store.xoa_phien_cua_user(db, user["_id"])
    write_audit(db, admin, "user_unlock" if body.is_active else "user_lock", user_store.COL_USERS, user["_id"],
                {"username": user["username"]})
    return {"user": user_store.cong_khai(user_store.tim_user(db, username))}
