"""GET /api/research/review: trang "Xem lại bài của bạn". Token CHỈ qua header X-Session-Token.

Trả 409 cho tới khi participants.completed_at có. CHỈ khi đã hoàn thành mới trả đáp án game 2:
trước đó không có trường nào của đáp án game 2 (la_loi, loai_loi, giai_thich, điểm) ra khỏi server.
"""
from fastapi import APIRouter, Depends, Header, HTTPException

from server.game1 import noi_dung_game1
from server.game2 import noi_dung_game2
from server.predict_api import chu
from server.research import chay, lay_db_nghien_cuu
from sparkmind import game3_store, research_store as kho, review_store

router = APIRouter()


@router.get("/api/research/review")
def xem_lai(x_session_token: str = Header(default=""), db=Depends(lay_db_nghien_cuu)):
    nguoi = chay(kho.tim_nguoi, db, x_session_token)
    if not nguoi.get("completed_at"):
        raise HTTPException(status_code=409, detail=chu("loi_research", "chua_xong"))
    return review_store.xem_lai(db, nguoi, noi_dung_game1(), noi_dung_game2(), game3_store.noi_dung_game3())
