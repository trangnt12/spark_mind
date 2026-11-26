"""GET /api/status: công tắc đóng/mở cho người dùng (không cần đăng nhập). Chỉ trả 4 giá trị, không lộ giờ hay chi tiết nội bộ."""
from fastapi import APIRouter, Depends, HTTPException

from server.research import lay_db_nghien_cuu
from sparkmind import settings_store

router = APIRouter()


@router.get("/api/status")
def trang_thai(db=Depends(lay_db_nghien_cuu)):
    """huong2_mo (đã tính cả hạn đóng), huong1_web_mo, demo_mo, thong_bao (dòng hiện ở đầu trang, có thể null)."""
    return settings_store.cong_khai(db)


def yeu_cau_huong1_web_mo(db=Depends(lay_db_nghien_cuu)) -> None:
    """Dependency cho đường vào web hướng 1 (làm ở bước sau): công tắc huong1_web_mo tắt (mặc định) thì trả 423, giao diện hiện trang "chưa mở"."""
    if not settings_store.lay_cai_dat(db)["huong1_web_mo"]:
        raise HTTPException(status_code=423, detail=settings_store.MA_HUONG1_CHUA_MO)
