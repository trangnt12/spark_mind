"""GET /api/research/progress: tiến độ và câu trả lời đã lưu của người tham gia. Chỉ đọc, token qua header."""
from fastapi import APIRouter, Depends, Header

from server.research import chay, lay_db_nghien_cuu
from sparkmind import progress, research_store as kho

router = APIRouter()


@router.get("/api/research/progress")
def tien_do(x_session_token: str = Header(default=""), db=Depends(lay_db_nghien_cuu)):
    """Token CHỈ nhận qua header X-Session-Token (không đưa lên URL). Chỉ trả dữ liệu của chính người đó."""
    nguoi = chay(kho.tim_nguoi, db, x_session_token)
    return {**progress.tien_do(db, nguoi), "answers": progress.cau_tra_loi_da_luu(db, nguoi)}
