"""Route của người chấm (/api/rate/*): chỉ vai trò rater, chỉ thấy mục trong đợt được giao và điểm của chính mình.

Mọi trường trả ra qua danh sách trắng (rating_store.muc_cho_nguoi_cham): không participant_id, email, IP, cờ, nhãn dữ liệu, điểm người kia, điểm AI.
Có giới hạn tốc độ theo tài khoản (trong bộ nhớ server).
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from server.auth import chay_ma, loi, require_role
from sparkmind import rating_content, rating_store
from sparkmind.security import GioiHanTocDo

router = APIRouter(prefix="/api/rate")
chi_nguoi_cham = require_role("rater")
gioi_han_doc = GioiHanTocDo(toi_da=240, giay=60)
gioi_han_ghi = GioiHanTocDo(toi_da=60, giay=60)


def _gioi_han(bo_dem: GioiHanTocDo):
    """Dependency phụ thuộc require_role (nên vẫn được test quét route công nhận), chặn 429 khi vượt tốc độ."""
    def kiem_tra(request: Request, ctx=Depends(chi_nguoi_cham)) -> dict:
        khoa = str(ctx["user"]["_id"])
        if not bo_dem.cho_phep(khoa):
            raise loi(429, "rate_limited", headers={"Retry-After": str(bo_dem.giay_phai_cho(khoa))})
        return ctx
    kiem_tra._la_kiem_quyen = True
    return kiem_tra


doc, ghi = _gioi_han(gioi_han_doc), _gioi_han(gioi_han_ghi)


class DiemBody(BaseModel):
    diem: dict = Field(max_length=10)
    ghi_chu: str = Field(default="", max_length=1000)
    thoi_gian_cham_giay: int = Field(default=0, ge=0, le=86400)


@router.get("/guide")
def huong_dan(ctx=Depends(doc)):
    """Hướng dẫn chấm (từ content/rating_guide.json)."""
    return rating_content.huong_dan()


@router.get("/items")
def danh_sach(ctx=Depends(doc)):
    return rating_store.danh_sach_muc(ctx["db"], ctx["user"]["username"])


@router.get("/items/{item_code}")
def mot_muc(item_code: str, ctx=Depends(doc)):
    return chay_ma(rating_store.lay_muc_de_cham, ctx["db"], ctx["user"]["username"], item_code[:20])


@router.put("/items/{item_code}/rating")
def luu(item_code: str, body: DiemBody, ctx=Depends(ghi)):
    return chay_ma(rating_store.luu_diem, ctx["db"], ctx["user"]["username"], item_code[:20], body.diem, body.ghi_chu, body.thoi_gian_cham_giay)
