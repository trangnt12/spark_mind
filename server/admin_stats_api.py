"""GET /api/admin/stats: số liệu tổng hợp cho trang chủ quản trị; GET /api/admin/codes/batches: thống kê mã theo lô (admin và viewer)."""
from fastapi import APIRouter, Depends

from server.auth import require_role
from sparkmind import admin_codes_stats, admin_stats

router = APIRouter(prefix="/api/admin")


@router.get("/stats")
def thong_ke(ex_test: bool = True, ctx=Depends(require_role("admin", "viewer"))):
    """ex_test=true (mặc định): ẩn dữ liệu thử (nhãn thu, pilot)."""
    return admin_stats.lay_thong_ke(ctx["db"], ex_test)


@router.get("/codes/batches")
def thong_ke_lo(ex_test: bool = True, ctx=Depends(require_role("admin", "viewer"))):
    """Mỗi dòng một lô mã: tổng, đã dùng, chưa dùng, đã hoàn thành. Không trả mã."""
    return {"lo": admin_codes_stats.thong_ke_lo(ctx["db"], ex_test)}
