"""Giờ dùng cho tài khoản, phiên và nhật ký: UTC, không kèm múi giờ (MongoDB lưu và TTL index tính theo UTC)."""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Giờ UTC hiện tại, làm tròn xuống mili giây (MongoDB chỉ lưu đến mili giây)."""
    t = datetime.now(timezone.utc).replace(tzinfo=None)
    return t.replace(microsecond=t.microsecond // 1000 * 1000)
