"""GET /api/admin/health: trang Sức khỏe hệ thống (admin và viewer). Chỉ đọc, kết quả nhớ ngắn, không lộ khóa hay chuỗi kết nối."""
from fastapi import APIRouter, Depends

from server.auth import require_role
from sparkmind import health

router = APIRouter(prefix="/api/admin")


@router.get("/health")
def suc_khoe(ctx=Depends(require_role("admin", "viewer"))):
    return health.lay_suc_khoe(ctx["db"])
