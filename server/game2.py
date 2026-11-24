"""Endpoint game 2 (hướng 2): bắt đầu và nộp. Cần session_token hợp lệ."""
import json
from functools import lru_cache

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.game1 import BatDauGameBody
from server.research import chay, lay_db_nghien_cuu
from sparkmind import config, flags_store, game2_store

router = APIRouter(prefix="/api/research/game2")


@lru_cache
def noi_dung_game2() -> dict:
    """Đề game 2 đọc từ content/games/game2.json (có đáp án: chỉ dùng ở server)."""
    with open(config.ROOT / "content" / "games" / "game2.json", encoding="utf-8") as f:
        return json.load(f)


class NopGame2Body(BatDauGameBody):
    chon: list[str] = Field(max_length=50, description="id các ý người chơi cho là SAI (0 đến 12 ý)")


@router.post("/start")
def bat_dau(body: BatDauGameBody, db=Depends(lay_db_nghien_cuu)):
    return chay(game2_store.bat_dau_game2, db, body.session_token, noi_dung_game2())


@router.post("/submit")
def nop(body: NopGame2Body, db=Depends(lay_db_nghien_cuu)):
    kq = chay(game2_store.nop_game2, db, body.session_token, body.chon, noi_dung_game2())
    flags_store.cap_nhat_co_theo_token(db, body.session_token)   # gắn cờ (nếu có); không báo gì cho người chơi
    return kq
