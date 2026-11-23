"""Endpoint đăng nhập: POST /api/auth/login, POST /api/auth/logout, GET /api/auth/me, POST /api/auth/change-password.

Lỗi đăng nhập luôn chung chung ("bad_credentials"): không lộ tài khoản có tồn tại hay không.
"""
import json
from functools import lru_cache

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from server.auth import (dang_nhap_bat_buoc, dat_cookie, khoa_dang_nhap, kiem_origin, loi,
                         TEN_COOKIE, xoa_cookie)
from server.research import lay_db_nghien_cuu
from sparkmind import config, passwords, session_store, user_store
from sparkmind.audit import write_audit

router = APIRouter(prefix="/api/auth")


class DangNhapBody(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


class DoiMatKhauBody(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(max_length=256)


@lru_cache
def chu_giao_dien() -> dict:
    """Chữ của giao diện quản trị, đọc từ content/admin_ui.json (không viết cứng trong code)."""
    with open(config.ROOT / "content" / "admin_ui.json", encoding="utf-8") as f:
        return json.load(f)


@router.get("/ui")
def lay_chu_giao_dien():
    """Chữ giao diện (không có bí mật). Trang đăng nhập cần đọc trước khi có phiên."""
    return chu_giao_dien()


def _bao_that_bai(db, request: Request, username: str, user: dict | None) -> None:
    """Ghi lần sai, ghi nhật ký (không ghi tên gõ vào), rồi báo lỗi chung chung (hoặc 429 nếu vừa bị khóa)."""
    khoa_den = session_store.ghi_that_bai(db, khoa_dang_nhap(request, username), user["_id"] if user else None)
    user_store.ghi_dang_nhap_sai(db, user, khoa_den)
    write_audit(db, user, "login_failed", user_store.COL_USERS, user["_id"] if user else None,
                {"locked": bool(khoa_den)})
    if khoa_den:
        raise loi(429, "locked", headers={"Retry-After": str(int(session_store.THOI_GIAN_KHOA.total_seconds()))})
    raise loi(401, "bad_credentials")


def _chan_neu_dang_khoa(db, request: Request, username: str) -> None:
    cho = session_store.giay_con_khoa(db, khoa_dang_nhap(request, username))
    if cho:
        raise loi(429, "locked", headers={"Retry-After": str(cho)})


def _gui_phien(db, request: Request, response: Response, user: dict) -> dict:
    """Tạo phiên, đặt cookie, trả thông tin cho giao diện (kèm csrf_token)."""
    token, csrf = session_store.tao_phien(db, user)
    dat_cookie(response, request, token)
    return {**user_store.cong_khai(user), "csrf_token": csrf}


@router.post("/login")
def dang_nhap(body: DangNhapBody, request: Request, response: Response, db=Depends(lay_db_nghien_cuu)):
    kiem_origin(request)   # chặn đăng nhập giả mạo từ trang khác
    _chan_neu_dang_khoa(db, request, body.username)
    user = user_store.tim_user(db, body.username)
    dung = passwords.xac_minh(body.password, user["password_hash"] if user else None)   # luôn chạy scrypt
    if not (dung and user["is_active"]):
        _bao_that_bai(db, request, body.username, user)
    session_store.xoa_dem_sai(db, khoa_dang_nhap(request, body.username))
    user_store.ghi_dang_nhap_ok(db, user)
    write_audit(db, user, "login", user_store.COL_USERS, user["_id"])
    return _gui_phien(db, request, response, user)


@router.post("/logout")
def dang_xuat(request: Request, response: Response, ctx=Depends(dang_nhap_bat_buoc)):
    session_store.xoa_phien(ctx["db"], request.cookies.get(TEN_COOKIE, ""))
    write_audit(ctx["db"], ctx["user"], "logout", user_store.COL_USERS, ctx["user"]["_id"])
    xoa_cookie(response, request)
    return {"ok": True}


@router.get("/me")
def toi_la_ai(ctx=Depends(dang_nhap_bat_buoc)):
    """Thông tin người đang đăng nhập và csrf_token (giao diện gửi lại trong header X-CSRF-Token)."""
    return {**user_store.cong_khai(ctx["user"]), "csrf_token": ctx["phien"]["csrf_token"]}


@router.post("/change-password")
def doi_mat_khau(body: DoiMatKhauBody, request: Request, response: Response, ctx=Depends(dang_nhap_bat_buoc)):
    db, user = ctx["db"], ctx["user"]
    khoa = khoa_dang_nhap(request, user["username"])
    _chan_neu_dang_khoa(db, request, user["username"])
    if not passwords.xac_minh(body.current_password, user["password_hash"]):
        _bao_that_bai(db, request, user["username"], user)   # đoán mật khẩu cũ cũng tính vào giới hạn
    ma_loi = passwords.kiem_tra_do_manh(body.new_password, user["username"])
    if ma_loi or body.new_password == body.current_password:
        raise loi(422, ma_loi or "same_password")
    session_store.xoa_dem_sai(db, khoa)
    user_store.dat_mat_khau(db, user, body.new_password, bat_buoc_doi=False)
    session_store.xoa_phien_cua_user(db, user["_id"])   # đăng xuất mọi nơi, cấp phiên mới cho nơi đang đổi
    write_audit(db, user, "change_password", user_store.COL_USERS, user["_id"])
    return _gui_phien(db, request, response, {**user, "must_change_password": False})
