"""Endpoint game 3 (hướng 2): bắt đầu và nộp bài (một lần cho cả hai tình huống). Cần session_token hợp lệ."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.game1 import BatDauGameBody
from server.research import chay, lay_db_nghien_cuu
from sparkmind import flags_store, game3_store

router = APIRouter(prefix="/api/research/game3")


class OGame3(BaseModel):
    """Bài của một tình huống (một ô nhập)."""
    tinh_huong_id: str = Field(min_length=1, max_length=40)
    noi_dung: str = Field(max_length=5000, description="Văn bản người chơi nhập; giới hạn thật (800 ký tự) kiểm tra theo content")
    paste_count: int = Field(ge=0, le=100000)
    tab_leave_count: int = Field(ge=0, le=100000)
    thoi_gian_giay: int = Field(ge=0, le=86400, description="Tổng thời gian ô này được dùng (trình duyệt đo, đã trừ lúc ẩn tab)")


class NopGame3Body(BatDauGameBody):
    items: list[OGame3] = Field(min_length=1, max_length=10)


@router.post("/start")
def bat_dau(body: BatDauGameBody, db=Depends(lay_db_nghien_cuu)):
    return chay(game3_store.bat_dau_game3, db, body.session_token)


@router.post("/submit")
def nop(body: NopGame3Body, db=Depends(lay_db_nghien_cuu)):
    d = {"items": [o.model_dump() for o in body.items]}
    kq = chay(game3_store.nop_game3, db, body.session_token, d, game3_store.noi_dung_game3())
    flags_store.cap_nhat_co_theo_token(db, body.session_token)   # gắn cờ (nếu có); không báo gì cho người chơi
    return kq
