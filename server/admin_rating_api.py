"""Route quản trị phần chấm (/api/admin/rating/*): đợt chấm, rút mẫu, tiến độ, độ đồng thuận, xem câu trả lời, xuất CSV.

Admin: rút mẫu, khóa/mở, xuất CSV. Viewer: chỉ xem (không thấy participant_id). Mọi thao tác ghi đều ghi audit_log (không ghi nội dung).
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from server.auth import chay_ma, loi, require_role
from sparkmind import config, rating_agreement, rating_report, rating_sample, rating_store
from sparkmind.audit import write_audit
from sparkmind.security import GioiHanTocDo

router = APIRouter(prefix="/api/admin/rating")
chi_admin = require_role("admin")
admin_hoac_xem = require_role("admin", "viewer")
gioi_han_nang = GioiHanTocDo(toi_da=20, giay=60)   # rút mẫu, xuất CSV, độ đồng thuận: tính toán nặng


def _nang(kiem_quyen):
    """Dependency kiểm quyền (kiem_quyen) rồi giới hạn tốc độ theo tài khoản."""
    def kiem_tra(ctx=Depends(kiem_quyen)) -> dict:
        khoa = str(ctx["user"]["_id"])
        if not gioi_han_nang.cho_phep(khoa):
            raise loi(429, "rate_limited", headers={"Retry-After": str(gioi_han_nang.giay_phai_cho(khoa))})
        return ctx
    kiem_tra._la_kiem_quyen = True
    return kiem_tra


admin_nang, xem_nang = _nang(chi_admin), _nang(admin_hoac_xem)


class RutMauBody(BaseModel):
    data_label: str = Field(max_length=10)
    rating_batch: str = Field(max_length=40)
    n_game1: int = Field(ge=0, le=5000)
    n_game3: int = Field(ge=0, le=5000)
    seed: int = Field(ge=0, le=5000)
    dry_run: bool = True
    raters: list[str] = Field(default_factory=list, max_length=20)


@router.get("/batches")
def danh_sach_dot(ctx=Depends(admin_hoac_xem)):
    return {"dot": rating_report.danh_sach_dot(ctx["db"]), "mac_dinh": {"toi_thieu": config.RATING_MUC_TOI_THIEU_KAPPA}}


@router.post("/sample")
def rut_mau(body: RutMauBody, ctx=Depends(admin_nang)):
    """Rút mẫu (dry_run=true: chỉ xem trước, không ghi)."""
    return chay_ma(rating_sample.rut_mau, ctx["db"], body.data_label, body.rating_batch, body.n_game1, body.n_game3, body.seed,
                   body.dry_run, ctx["user"], body.raters)


@router.post("/batches/{ten}/{hanh_dong}")
def khoa_mo(ten: str, hanh_dong: str, ctx=Depends(chi_admin)):
    if hanh_dong not in ("lock", "unlock"):
        raise loi(404, "khong_tim_thay")
    dot = chay_ma(rating_store.dat_khoa_dot, ctx["db"], ten[:40], hanh_dong == "lock")
    write_audit(ctx["db"], ctx["user"], "rating_" + hanh_dong, rating_store.COL_DOT, dot["name"], {})
    return {"name": dot["name"], "locked": dot["locked"]}


@router.get("/batches/{ten}/progress")
def tien_do(ten: str, ctx=Depends(admin_hoac_xem)):
    return chay_ma(rating_report.tien_do, ctx["db"], ten[:40])


@router.get("/batches/{ten}/answers")
def cau_tra_loi(ten: str, request: Request, ctx=Depends(admin_hoac_xem)):
    """Nội dung từng mục cạnh điểm các người chấm. Viewer không thấy participant_id."""
    q = request.query_params
    game = int(q["game"]) if q.get("game", "").isdigit() else None
    trang = int(q["page"]) if q.get("page", "").isdigit() else 1
    return chay_ma(rating_report.xem_cau_tra_loi, ctx["db"], ten[:40], game, max(1, trang), 50, ctx["user"]["role"] == "admin")


@router.get("/batches/{ten}/agreement")
def dong_thuan(ten: str, request: Request, ctx=Depends(xem_nang)):
    q = request.query_params
    dot = chay_ma(rating_report.dot_hoac_404, ctx["db"], ten[:40])
    ds = rating_report.nguoi_cham_cua_dot(ctx["db"], dot)
    a, b = (q.get("rater_a") or (ds + [None, None])[0]), (q.get("rater_b") or (ds + [None, None])[1])
    if not a or not b or a == b or a not in ds or b not in ds:
        raise loi(422, "can_hai_nguoi_cham")
    toi_thieu = int(q["toi_thieu"]) if q.get("toi_thieu", "").isdigit() and 1 <= int(q["toi_thieu"]) <= 1000 else None
    return {**rating_agreement.do_dong_thuan(ctx["db"], dot["name"], a, b, toi_thieu), "nguoi_cham_co_the_chon": ds}


def _tai_csv(ten: str, ham, hau_to: str, hanh_dong: str, ctx) -> Response:
    noi_dung = chay_ma(ham, ctx["db"], ten[:40])
    write_audit(ctx["db"], ctx["user"], hanh_dong, rating_store.COL_DIEM, ten[:40], {"so_dong": noi_dung.count("\n") - 1})
    return Response("﻿" + noi_dung, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="rating_{ten[:40]}_{hau_to}.csv"'})


@router.get("/batches/{ten}/export/ratings.csv")
def xuat_diem(ten: str, ctx=Depends(admin_nang)):
    return _tai_csv(ten, rating_report.xuat_diem_csv, "diem", "rating_export", ctx)


@router.get("/batches/{ten}/export/key.csv")
def xuat_khoa(ten: str, ctx=Depends(admin_nang)):
    return _tai_csv(ten, rating_report.xuat_khoa_csv, "khoa", "rating_key_export", ctx)
