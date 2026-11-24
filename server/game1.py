"""Endpoint game 1 (hướng 2): bắt đầu và nộp. Cần session_token hợp lệ."""
import json
from functools import lru_cache

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.research import chay, lay_db_nghien_cuu
from sparkmind import config, flags_store, game_store

router = APIRouter(prefix="/api/research/game1")


@lru_cache
def noi_dung_game1() -> dict:
    """Đề game 1 đọc từ content/games/game1.json (không viết cứng)."""
    with open(config.ROOT / "content" / "games" / "game1.json", encoding="utf-8") as f:
        return json.load(f)


class BatDauGameBody(BaseModel):
    session_token: str = Field(min_length=1, max_length=100)


class NopGame1Body(BatDauGameBody):
    ideas: list[str] = Field(max_length=500, description="Mỗi ý tối đa 120 ký tự sau khi làm sạch")
    paste_count: int = Field(ge=0, le=100000)
    tab_leave_count: int = Field(ge=0, le=100000)


@router.post("/start")
def bat_dau(body: BatDauGameBody, db=Depends(lay_db_nghien_cuu)):
    return chay(game_store.bat_dau_game1, db, body.session_token, noi_dung_game1())


@router.post("/submit")
def nop(body: NopGame1Body, db=Depends(lay_db_nghien_cuu)):
    gioi_han = noi_dung_game1()["thoi_gian_giay"]
    kq = chay(game_store.nop_game1, db, body.session_token, body.model_dump(), gioi_han)
    flags_store.cap_nhat_co_theo_token(db, body.session_token)   # gắn cờ (nếu có); không báo gì cho người chơi
    return kq
