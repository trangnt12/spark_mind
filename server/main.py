"""Server SparkMind (bản tối thiểu): /health và nhận form từ Google Form.

Chạy thử trên máy:  uvicorn server.main:app --reload
Chạy trên Render:   uvicorn server.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
"""
import hmac
import logging
import sys
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi import Depends, FastAPI, Header, HTTPException, Request  # noqa: E402
from fastapi.exception_handlers import request_validation_exception_handler  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from sparkmind import config  # noqa: E402
from sparkmind.db import lay_db  # noqa: E402
from sparkmind import predict  # noqa: E402
from sparkmind.ingest import nhan_form  # noqa: E402
from sparkmind.memory import rss_mb  # noqa: E402
from sparkmind.game_store import tao_chi_muc_game  # noqa: E402
from sparkmind.research_store import tao_chi_muc  # noqa: E402
from server import admin_data_api, admin_stats_api, admin_testdata_api, admin_users, auth, auth_api, content_api, game1, predict_api, research  # noqa: E402
from sparkmind import audit, session_store, user_store  # noqa: E402

@lru_cache
def lay_db_dung_chung():
    """Mở kết nối MongoDB một lần rồi dùng lại."""
    return lay_db()


@asynccontextmanager
async def vong_doi(_app):
    """Khi server khởi động: tạo chỉ mục cho chế độ nghiên cứu. Lỗi thì ghi tên lỗi (không ghi chuỗi kết nối)."""
    try:
        tao_chi_muc(lay_db_dung_chung())
        tao_chi_muc_game(lay_db_dung_chung())
        user_store.tao_chi_muc_user(lay_db_dung_chung())
        session_store.tao_chi_muc_phien(lay_db_dung_chung())
        audit.tao_chi_muc_audit(lay_db_dung_chung())
    except Exception as loi:
        logging.getLogger("uvicorn.error").error("Không tạo được chỉ mục: %s", type(loi).__name__)
    yield


app = FastAPI(title="SparkMind", lifespan=vong_doi)
app.include_router(research.router)
app.include_router(game1.router)
app.include_router(content_api.router)
app.include_router(predict_api.router)
app.include_router(auth_api.router)
app.include_router(admin_users.router)
app.include_router(admin_stats_api.router)
app.include_router(admin_data_api.router)
app.include_router(admin_testdata_api.router)

# Trang quản trị không được lập chỉ mục, không lưu cache, không nhúng vào khung (iframe) của trang khác
DUONG_QUAN_TRI = ("/admin", "/play/admin", "/api/auth", "/api/admin", "/api/rate")
CSP_QUAN_TRI = ("default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
                "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


@app.middleware("http")
async def header_quan_tri(request: Request, call_next):
    """Thêm header bảo mật cho mọi đường của trang quản trị (giao diện và API)."""
    resp = await call_next(request)
    if request.url.path.startswith(DUONG_QUAN_TRI):
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = CSP_QUAN_TRI
    return resp


@app.exception_handler(RequestValidationError)
async def loi_dinh_dang(request: Request, loi: RequestValidationError):
    """Demo: JSON hỏng cũng báo tiếng Việt (không trả lại nội dung người dùng gửi). Đường khác giữ mặc định."""
    if request.url.path == "/api/predict/demo":
        return JSONResponse(status_code=422, content={"detail": predict_api.chu("loi_demo", "body_sai")})
    return await request_validation_exception_handler(request, loi)


def kiem_tra_khoa(x_api_key: str = Header(default="")) -> None:
    """Chỉ cho phép nơi biết khóa bí mật (Apps Script) gửi form vào."""
    if not config.INGEST_SECRET or not hmac.compare_digest(x_api_key, config.INGEST_SECRET):
        raise HTTPException(status_code=401, detail="Sai khóa")


kiem_tra_khoa = auth.danh_dau_kiem_quyen(kiem_tra_khoa)   # đánh dấu: test route coi đây là bước kiểm tra quyền


@app.get("/health")
def health():
    """Để cron-job.org ping, giữ server không ngủ."""
    return {"status": "ok"}


@app.get("/api/admin/memory", dependencies=[Depends(kiem_tra_khoa)])
def admin_memory():
    """Xem bộ nhớ server (cần khóa như ingest). Chỉ trả 2 trường, không lộ thông tin khác."""
    return {"rss_mb": rss_mb(), "models_loaded": predict.nap_mo_hinh.cache_info().currsize > 0}


@app.post("/api/ingest/google-form", dependencies=[Depends(kiem_tra_khoa)])
def ingest_google_form(answers: dict, db=Depends(lay_db_dung_chung)):
    try:
        return nhan_form(db, answers, nguon="google_form")
    except ValueError as loi:
        raise HTTPException(status_code=422, detail=str(loi))


# Giao diện quản trị (web/admin/): HTML/CSS/JS thuần, đặt TRƯỚC /play để khớp đường dẫn /admin
app.mount("/admin", StaticFiles(directory=config.ROOT / "web" / "admin", html=True), name="admin")

# Giao diện web nghiên cứu: HTML/CSS/JS thuần trong web/, phục vụ tại /play (đặt cuối để không che API)
app.mount("/play", StaticFiles(directory=config.ROOT / "web", html=True), name="play")
