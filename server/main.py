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

from fastapi import Depends, FastAPI, Header, HTTPException  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from sparkmind import config  # noqa: E402
from sparkmind.db import lay_db  # noqa: E402
from sparkmind.ingest import nhan_form  # noqa: E402
from sparkmind.game_store import tao_chi_muc_game  # noqa: E402
from sparkmind.research_store import tao_chi_muc  # noqa: E402
from server import content_api, game1, research  # noqa: E402

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
    except Exception as loi:
        logging.getLogger("uvicorn.error").error("Không tạo được chỉ mục: %s", type(loi).__name__)
    yield


app = FastAPI(title="SparkMind", lifespan=vong_doi)
app.include_router(research.router)
app.include_router(game1.router)
app.include_router(content_api.router)


def kiem_tra_khoa(x_api_key: str = Header(default="")) -> None:
    """Chỉ cho phép nơi biết khóa bí mật (Apps Script) gửi form vào."""
    if not config.INGEST_SECRET or not hmac.compare_digest(x_api_key, config.INGEST_SECRET):
        raise HTTPException(status_code=401, detail="Sai khóa")


@app.get("/health")
def health():
    """Để cron-job.org ping, giữ server không ngủ."""
    return {"status": "ok"}


@app.post("/api/ingest/google-form", dependencies=[Depends(kiem_tra_khoa)])
def ingest_google_form(answers: dict, db=Depends(lay_db_dung_chung)):
    try:
        return nhan_form(db, answers, nguon="google_form")
    except ValueError as loi:
        raise HTTPException(status_code=422, detail=str(loi))


# Giao diện web nghiên cứu: HTML/CSS/JS thuần trong web/, phục vụ tại /play (đặt cuối để không che API)
app.mount("/play", StaticFiles(directory=config.ROOT / "web", html=True), name="play")
