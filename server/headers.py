"""Tiêu đề bảo mật cho MỌI phản hồi (trang công khai, API, trang quản trị).

- Mọi đường: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP; HSTS khi chạy HTTPS.
- Trang quản trị và API quản trị: thêm noindex, no-store, Referrer-Policy no-referrer và CSP chặt hơn.
- CSP công khai: chỉ cho script cùng nguồn + đúng MỘT script nhúng trong survey1.html (cho bằng mã băm SHA-256, có test giữ khớp);
  style cho phép 'unsafe-inline' vì giao diện có thuộc tính style; phông chỉ từ Google Fonts.
"""
import base64
import hashlib

from fastapi import Request

DUONG_QUAN_TRI = ("/admin", "/play/admin", "/api/auth", "/api/admin", "/api/rate")
SCRIPT_NHUNG_SURVEY1 = "window.TRANG_RIENG = true;"   # nội dung đúng từng ký tự của thẻ <script> nhúng trong web/survey1.html


def bam_script(noi_dung: str) -> str:
    """Giá trị 'sha256-...' dùng trong CSP để cho phép đúng một script nhúng."""
    return "'sha256-" + base64.b64encode(hashlib.sha256(noi_dung.encode("utf-8")).digest()).decode() + "'"


CSP_QUAN_TRI = ("default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
                "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
CSP_CONG_KHAI = (f"default-src 'self'; script-src 'self' {bam_script(SCRIPT_NHUNG_SURVEY1)}; "
                 "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
                 "img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
HSTS = "max-age=15552000"   # 180 ngày; chỉ gửi khi request đến qua HTTPS


def la_duong_quan_tri(duong: str) -> bool:
    return duong.startswith(DUONG_QUAN_TRI)


def them_header(request: Request, resp) -> None:
    """Gắn header bảo mật vào phản hồi `resp` (sửa tại chỗ)."""
    duong, h = request.url.path, resp.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.scheme == "https":
        h["Strict-Transport-Security"] = HSTS
    if duong.startswith("/play/") and not la_duong_quan_tri(duong):
        h["Cache-Control"] = "no-cache"   # luôn hỏi lại máy chủ (ETag): sửa JS/CSS thì người chơi nhận bản mới ngay
    if la_duong_quan_tri(duong):
        h["X-Robots-Tag"] = "noindex, nofollow"
        h["Cache-Control"] = "no-store"
        h["Referrer-Policy"] = "no-referrer"
        h["Content-Security-Policy"] = CSP_QUAN_TRI
    else:
        h["Referrer-Policy"] = "strict-origin-when-cross-origin"
        h["Content-Security-Policy"] = CSP_CONG_KHAI
