"""Phục vụ trang chủ "/" và trang giới thiệu hướng 1 "/huong-1".
Chữ của thẻ title/description/og lấy từ content/landing_ui.json (mục "meta") rồi chèn vào HTML,
để trình thu thập (Zalo, Facebook, Google) đọc được mà không cần chạy JavaScript."""
from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from server.content_api import doc_noi_dung
from sparkmind import config

router = APIRouter()
KHONG_NHO = {"Cache-Control": "no-cache"}


def ve_trang(ten_file: str, khoa_meta: str) -> HTMLResponse:
    """Đọc khung HTML trong web/, thay các mốc {{title}}, {{description}}, {{og_title}}, {{og_description}} bằng chữ trong file nội dung."""
    html = (config.ROOT / "web" / ten_file).read_text(encoding="utf-8")
    for khoa, chu in doc_noi_dung("landing_ui.json")["meta"][khoa_meta].items():
        html = html.replace("{{" + khoa + "}}", escape(chu, quote=True))
    return HTMLResponse(html, headers=KHONG_NHO)


@router.get("/", include_in_schema=False)
def trang_chu():
    """Trang chủ (web/landing.html). Không đổi địa chỉ /play, /admin."""
    return ve_trang("landing.html", "trang_chu")


@router.get("/huong-1", include_in_schema=False)
def trang_huong1():
    """Trang giới thiệu riêng của hướng 1 (web/huong1.html)."""
    return ve_trang("huong1.html", "huong1")
