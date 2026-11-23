"""Xác thực và phân quyền cho trang quản trị: cookie phiên, CSRF, kiểm tra Origin, require_role.

Nguyên tắc TỪ CHỐI MẶC ĐỊNH: mọi endpoint /api/admin/* và /api/rate/* phải có dependency được đánh dấu
`_la_kiem_quyen` (require_role hoặc khóa INGEST_SECRET). tests/test_admin_auth.py duyệt toàn bộ route để chắc chắn.
"""
import hmac
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request

from server.research import lay_db_nghien_cuu, lay_ip
from sparkmind import research_store, session_store, user_store

TEN_COOKIE = "sm_admin"
PHUONG_THUC_AN_TOAN = ("GET", "HEAD", "OPTIONS")


def loi(ma_http: int, ma: str, **them) -> HTTPException:
    """Lỗi có mã máy đọc được (giao diện đổi mã thành chữ trong content/admin_ui.json)."""
    return HTTPException(status_code=ma_http, detail={"code": ma}, headers=them.get("headers"))


def chay_ma(ham, *args):
    """Gọi hàm của kho dữ liệu, đổi LoiNghiepVu (noi_dung là mã lỗi) thành lỗi HTTP có mã máy đọc được."""
    try:
        return ham(*args)
    except research_store.LoiNghiepVu as e:
        raise loi(e.ma_http, e.noi_dung)


def danh_dau_kiem_quyen(ham):
    """Đánh dấu một dependency là bước kiểm tra quyền (test route quét dấu này)."""
    ham._la_kiem_quyen = True
    return ham


def kiem_origin(request: Request) -> None:
    """Origin phải có và trùng host của server (chặn trang lạ gửi yêu cầu giả mạo)."""
    goc = request.headers.get("origin", "")
    if not goc or urlparse(goc).netloc != request.headers.get("host", ""):
        raise loi(403, "origin")


def kiem_csrf(request: Request, phien: dict) -> None:
    """Mọi yêu cầu ghi (POST/PUT/PATCH/DELETE) cần Origin hợp lệ và header X-CSRF-Token khớp phiên."""
    if request.method in PHUONG_THUC_AN_TOAN:
        return
    kiem_origin(request)
    gui = request.headers.get("x-csrf-token", "")
    if not hmac.compare_digest(gui.encode(), phien["csrf_token"].encode()):
        raise loi(403, "csrf")


def xac_thuc(request: Request, db) -> tuple:
    """Đọc cookie, tìm phiên và user còn hoạt động. Trả (user, phien) hoặc báo 401."""
    phien = session_store.tim_phien(db, request.cookies.get(TEN_COOKIE, ""))
    user = db[user_store.COL_USERS].find_one({"_id": phien["user_id"]}) if phien else None
    if not user or not user.get("is_active"):
        raise loi(401, "not_logged_in")
    kiem_csrf(request, phien)
    return user, phien


def dang_nhap_bat_buoc(request: Request, db=Depends(lay_db_nghien_cuu)) -> dict:
    """Cho /api/auth/me, đổi mật khẩu, đăng xuất: cần đăng nhập, KHÔNG xét vai trò, cho phép đang bị buộc đổi mật khẩu."""
    user, phien = xac_thuc(request, db)
    return {"user": user, "phien": phien, "db": db}


def require_role(*vai_tro: str):
    """Tạo dependency chỉ cho các vai trò đã nêu. User đang bị buộc đổi mật khẩu thì bị chặn (403 must_change_password)."""
    cho_phep = set(vai_tro)

    @danh_dau_kiem_quyen
    def kiem_tra(request: Request, db=Depends(lay_db_nghien_cuu)) -> dict:
        user, phien = xac_thuc(request, db)
        if user.get("must_change_password"):
            raise loi(403, "must_change_password")
        if user["role"] not in cho_phep:
            raise loi(403, "forbidden")
        return {"user": user, "phien": phien, "db": db}
    kiem_tra._vai_tro = cho_phep
    return kiem_tra


def dat_cookie(response, request: Request, token: str) -> None:
    """Cookie phiên: HttpOnly, SameSite=Strict, Secure khi chạy HTTPS (Render, sau --proxy-headers)."""
    response.set_cookie(TEN_COOKIE, token, httponly=True, samesite="strict", path="/",
                        secure=request.url.scheme == "https", max_age=int(session_store.GIO_TOI_DA.total_seconds()))


def xoa_cookie(response, request: Request) -> None:
    response.delete_cookie(TEN_COOKIE, path="/", httponly=True, samesite="strict", secure=request.url.scheme == "https")


def khoa_dang_nhap(request: Request, username: str) -> str:
    """Khóa đếm đăng nhập sai theo (username + IP). IP lấy từ request.client.host, không tin x-forwarded-for."""
    return session_store.khoa_thu(user_store.chuan_hoa_username(username)[:64], lay_ip(request))
