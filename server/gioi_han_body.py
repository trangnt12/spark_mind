"""Giới hạn kích thước body của mọi yêu cầu ghi (POST/PUT/PATCH/DELETE): quá config.BODY_TOI_DA_BYTE thì trả 413.

Kiểm tra Content-Length ngay đầu (từ chối trước khi đọc). Body gửi kiểu chunked (không có Content-Length) được đếm khi đọc;
vượt mức thì dừng đọc (FastAPI báo 400). Các endpoint có giới hạn riêng nhỏ hơn (hướng 1: 20.000 byte) vẫn giữ nguyên.
"""
import json

from sparkmind import config

PHUONG_THUC_GHI = {"POST", "PUT", "PATCH", "DELETE"}


class BodyQuaLon(Exception):
    """Body vượt giới hạn khi đang đọc."""


class GioiHanBody:
    """Middleware ASGI thuần (không dùng BaseHTTPMiddleware để đếm được từng khối body)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in PHUONG_THUC_GHI:
            return await self.app(scope, receive, send)
        gioi_han = config.BODY_TOI_DA_BYTE
        try:
            dai = int(dict(scope["headers"]).get(b"content-length", b"0"))
        except ValueError:
            dai = 0
        if dai > gioi_han:
            return await _tra_413(send)
        da_doc = 0

        async def doc_co_dem():
            nonlocal da_doc
            msg = await receive()
            da_doc += len(msg.get("body", b""))
            if da_doc > gioi_han:
                raise BodyQuaLon()
            return msg

        try:
            await self.app(scope, doc_co_dem, send)
        except BodyQuaLon:
            await _tra_413(send)


async def _tra_413(send) -> None:
    body = json.dumps({"detail": "Yêu cầu quá lớn."}, ensure_ascii=False).encode("utf-8")
    await send({"type": "http.response.start", "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})
