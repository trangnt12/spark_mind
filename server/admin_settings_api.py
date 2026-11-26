"""Trang Cài đặt của quản trị: xem (admin, viewer) và lưu (chỉ admin). Mỗi lần lưu có thay đổi đều ghi audit_log."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from server.auth import loi, require_role
from sparkmind import config, settings_store

router = APIRouter(prefix="/api/admin/settings")


class CaiDatBody(BaseModel):
    huong2_mo: bool
    huong1_web_mo: bool
    demo_mo: bool
    han_dong_huong2: datetime | None = None   # trình duyệt gửi ISO có múi giờ; máy chủ đổi sang UTC
    thong_bao: str | None = None


def _utc(t: datetime | None) -> datetime | None:
    """Đổi sang UTC không kèm múi giờ (giờ không kèm múi giờ coi là đã ở UTC)."""
    if t is None or t.tzinfo is None:
        return t
    return t.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)


def _iso(t):
    return t.isoformat() if t else None


def _day_du(db) -> dict:
    """Giá trị đã lưu + trạng thái đang hiệu lực (ĐANG MỞ / ĐÃ ĐÓNG) để hiện trên trang Cài đặt và Tổng quan."""
    cd, tt = settings_store.doc_cai_dat(db), settings_store.trang_thai(db)
    return {**{k: cd[k] for k in settings_store.CONG_TAC}, "han_dong_huong2": _iso(cd["han_dong_huong2"]), "thong_bao": cd["thong_bao"],
            "cap_nhat_luc": _iso(cd["cap_nhat_luc"]), "cap_nhat_boi": cd["cap_nhat_boi"],
            "hieu_luc": {"huong2_dang_mo": tt["huong2_dang_mo"], "huong2_dong_luc": _iso(tt["huong2_dong_luc"]),
                         "huong2_het_gia_han_luc": _iso(tt["huong2_het_gia_han_luc"]), "huong2_het_gia_han": tt["huong2_het_gia_han"],
                         "huong1_web_mo": tt["huong1_web_mo"], "demo_mo": tt["demo_mo"]},
            "gia_han_gio": config.HUONG2_GIA_HAN_GIO, "thong_bao_toi_da": config.CAI_DAT_THONG_BAO_TOI_DA}


@router.get("")
def xem(ctx=Depends(require_role("admin", "viewer"))):
    settings_store.xoa_cache()   # trang quản trị luôn thấy giá trị mới nhất
    return _day_du(ctx["db"])


@router.put("")
def luu(body: CaiDatBody, ctx=Depends(require_role("admin"))):
    try:
        thong_bao = settings_store.chuan_hoa_thong_bao(body.thong_bao)
    except ValueError:
        raise loi(422, "thong_bao_dai")
    moi = {**body.model_dump(), "han_dong_huong2": _utc(body.han_dong_huong2), "thong_bao": thong_bao}
    ket_qua = settings_store.luu_cai_dat(ctx["db"], ctx["user"], moi)
    return {**_day_du(ctx["db"]), "thay_doi": list(ket_qua["thay_doi"])}
