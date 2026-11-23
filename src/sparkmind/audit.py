"""Nhật ký thao tác quản trị (audit_log): CHỈ THÊM, không có hàm sửa hay xóa."""
from .thoi_gian import utc_now

COL_AUDIT = "audit_log"
_TU_NHAY_CAM = ("password", "hash", "token", "secret", "csrf")


def tao_chi_muc_audit(db) -> None:
    db[COL_AUDIT].create_index("at")


def _loc_chi_tiet(detail: dict | None) -> dict:
    """Bỏ mọi khóa có vẻ là bí mật (mật khẩu, băm, token) để không bao giờ lọt vào nhật ký."""
    return {k: v for k, v in (detail or {}).items() if not any(t in k.lower() for t in _TU_NHAY_CAM)}


def write_audit(db, user: dict | None, action: str, collection: str | None = None,
                doc_id=None, detail: dict | None = None) -> None:
    """Ghi một dòng nhật ký. user=None cho thao tác chưa đăng nhập (vd đăng nhập sai)."""
    db[COL_AUDIT].insert_one({
        "at": utc_now(), "user_id": user.get("_id") if user else None,
        "username": user.get("username") if user else None, "role": user.get("role") if user else None,
        "action": action, "collection": collection, "doc_id": None if doc_id is None else str(doc_id),
        "detail": _loc_chi_tiet(detail)})
