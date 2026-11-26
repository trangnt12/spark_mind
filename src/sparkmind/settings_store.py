"""Cài đặt đóng/mở (collection `settings`, MỘT tài liệu): công tắc hướng 2, hướng 1 web, demo, hạn đóng, thông báo.

- Không có tài liệu thì dùng giá trị mặc định (MAC_DINH): hướng 2 mở, hướng 1 web ĐÓNG, demo mở.
- Server đọc qua bộ nhớ đệm ngắn (config.CAI_DAT_NHO_DEM_GIAY) để công tắc có hiệu lực nhanh, kể cả khi chạy nhiều tiến trình.
- Mọi giờ là UTC, không kèm múi giờ (giống audit_log).
"""
import time
from datetime import datetime, timedelta

from . import config
from .audit import write_audit
from .thoi_gian import utc_now

COL_CAI_DAT = "settings"
ID_CAI_DAT = "chung"
MAC_DINH = {"huong2_mo": True, "huong1_web_mo": False, "demo_mo": True, "han_dong_huong2": None, "thong_bao": None}
CONG_TAC = ("huong2_mo", "huong1_web_mo", "demo_mo")
# Thông báo ngắn trong API (người dùng thấy trang thân thiện do giao diện vẽ từ content/research_ui.json)
MA_HUONG2_DONG = "Đợt khảo sát đã đóng."
MA_HUONG2_HET_GIA_HAN = "Đợt khảo sát đã đóng và thời gian nộp tiếp đã hết."
MA_HUONG1_CHUA_MO = "Chức năng này chưa mở."
MA_DEMO_DONG = "Bản demo tạm đóng."

_nho = {"db": None, "luc": 0.0, "gia_tri": None}   # bộ nhớ đệm một ô (giữ tham chiếu db nên không nhầm giữa hai kết nối)


def xoa_cache() -> None:
    """Quên bộ nhớ đệm (gọi sau khi lưu, và trong test)."""
    _nho.update(db=None, luc=0.0, gia_tri=None)


def doc_cai_dat(db) -> dict:
    """Đọc thẳng từ MongoDB, điền giá trị mặc định cho trường thiếu. Kèm dong_luc (lúc admin tắt hướng 2) và cap_nhat_luc."""
    d = db[COL_CAI_DAT].find_one({"_id": ID_CAI_DAT}) or {}
    kq = {k: d.get(k, v) for k, v in MAC_DINH.items()}
    kq.update(huong2_dong_luc=d.get("huong2_dong_luc"), cap_nhat_luc=d.get("cap_nhat_luc"), cap_nhat_boi=d.get("cap_nhat_boi"))
    return kq


def lay_cai_dat(db) -> dict:
    """Như doc_cai_dat nhưng nhớ tối đa CAI_DAT_NHO_DEM_GIAY giây."""
    bay_gio = time.monotonic()
    if _nho["db"] is db and bay_gio - _nho["luc"] < config.CAI_DAT_NHO_DEM_GIAY:
        return _nho["gia_tri"]
    gia_tri = doc_cai_dat(db)
    _nho.update(db=db, luc=bay_gio, gia_tri=gia_tri)
    return gia_tri


def thoi_diem_dong_huong2(cd: dict, bay_gio: datetime) -> datetime | None:
    """Lúc hướng 2 bắt đầu đóng (None = đang mở). Đóng khi công tắc tắt (tính từ lúc tắt) hoặc đã qua hạn han_dong_huong2 (tính từ hạn)."""
    cac_moc = []
    if not cd["huong2_mo"]:
        cac_moc.append(cd.get("huong2_dong_luc") or cd.get("cap_nhat_luc") or datetime.min)   # không rõ lúc tắt: coi như đã đóng từ lâu
    if cd.get("han_dong_huong2") and cd["han_dong_huong2"] <= bay_gio:
        cac_moc.append(cd["han_dong_huong2"])
    return min(cac_moc) if cac_moc else None


def trang_thai(db, bay_gio: datetime | None = None) -> dict:
    """Trạng thái đang hiệu lực: huong2_dang_mo, huong2_dong_luc, huong2_het_gia_han_luc (hết 48 giờ nộp tiếp), huong2_het_gia_han."""
    bay_gio = bay_gio or utc_now()
    cd = lay_cai_dat(db)
    dong = thoi_diem_dong_huong2(cd, bay_gio)
    het = dong + timedelta(hours=config.HUONG2_GIA_HAN_GIO) if dong else None
    return {"huong2_dang_mo": dong is None, "huong2_dong_luc": dong, "huong2_het_gia_han_luc": het,
            "huong2_het_gia_han": bool(het and bay_gio >= het),
            "huong1_web_mo": cd["huong1_web_mo"], "demo_mo": cd["demo_mo"], "thong_bao": cd["thong_bao"],
            "han_dong_huong2": cd["han_dong_huong2"]}


def ma_loi_huong2(db, da_bat_dau: bool) -> str | None:
    """None nếu được vào hướng 2. Đóng rồi: người đã bắt đầu còn được vào trong 48 giờ; người mới thì không."""
    tt = trang_thai(db)
    if tt["huong2_dang_mo"]:
        return None
    if da_bat_dau and not tt["huong2_het_gia_han"]:
        return None
    return MA_HUONG2_HET_GIA_HAN if da_bat_dau else MA_HUONG2_DONG


def cong_khai(db) -> dict:
    """Chỉ những gì người dùng cần biết (không lộ giờ, người sửa hay chi tiết nội bộ)."""
    tt = trang_thai(db)
    return {"huong2_mo": tt["huong2_dang_mo"], "huong1_web_mo": tt["huong1_web_mo"], "demo_mo": tt["demo_mo"], "thong_bao": tt["thong_bao"]}


# ---------- Lưu từ trang quản trị ----------

def chuan_hoa_thong_bao(v) -> str | None:
    """Bỏ khoảng trắng đầu/cuối; rỗng -> None; quá dài thì báo ValueError."""
    chu = (v or "").strip()
    if len(chu) > config.CAI_DAT_THONG_BAO_TOI_DA:
        raise ValueError("thong_bao_dai")
    return chu or None


def _chuoi(v):
    return v.isoformat() if isinstance(v, datetime) else v


def _cac_thay_doi(cu: dict, moi: dict) -> dict:
    return {k: {"cu": _chuoi(cu[k]), "moi": _chuoi(moi[k])} for k in MAC_DINH if cu[k] != moi[k]}


def luu_cai_dat(db, user: dict, moi: dict) -> dict:
    """Lưu đủ 5 giá trị. Giá trị không đổi thì không ghi gì. Có đổi thì ghi một dòng audit_log (ai, khi nào, cũ/mới).
    Trả {thay_doi}. Tắt hướng 2 thì nhớ lúc tắt (huong2_dong_luc) để tính 48 giờ nộp tiếp; mở lại thì xóa mốc đó."""
    cu = doc_cai_dat(db)
    moi = {k: moi.get(k, cu[k]) for k in MAC_DINH}
    thay_doi = _cac_thay_doi(cu, moi)
    if not thay_doi:
        return {"thay_doi": {}}
    bay_gio = utc_now()
    dat = {**moi, "cap_nhat_luc": bay_gio, "cap_nhat_boi": user["username"]}
    if "huong2_mo" in thay_doi:
        dat["huong2_dong_luc"] = None if moi["huong2_mo"] else bay_gio
    db[COL_CAI_DAT].update_one({"_id": ID_CAI_DAT}, {"$set": dat}, upsert=True)
    write_audit(db, user, "settings_update", COL_CAI_DAT, ID_CAI_DAT, {"thay_doi": thay_doi})
    xoa_cache()
    return {"thay_doi": thay_doi}
