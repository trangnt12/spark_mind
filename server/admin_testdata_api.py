"""Dọn dữ liệu thử (chỉ admin): xem trước (dry-run) rồi xóa. Chỉ đụng bản ghi nhãn thu/pilot."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.auth import loi, require_role
from sparkmind import du_lieu_thu

router = APIRouter(prefix="/api/admin/test-data")
chi_admin = require_role("admin")


class XoaThuBody(BaseModel):
    confirm: str = Field(max_length=20)


@router.get("")
def xem_truoc(ctx=Depends(chi_admin)):
    """Dry-run: số bản ghi sẽ bị xóa theo từng bảng. Không xóa gì."""
    kq = du_lieu_thu.xem_truoc(ctx["db"])
    return {"bang": kq, "tong": sum(kq.values()), "tu_xac_nhan": du_lieu_thu.TU_XAC_NHAN}


@router.post("/delete")
def xoa(body: XoaThuBody, ctx=Depends(chi_admin)):
    try:
        kq = du_lieu_thu.xoa(ctx["db"], ctx["user"], body.confirm)
    except ValueError:
        raise loi(422, "xac_nhan_sai")
    return {"da_xoa": kq, "tong": sum(kq.values())}
