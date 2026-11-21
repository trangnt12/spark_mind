"""Bảo mật cho chế độ nghiên cứu: băm IP (không lưu IP thô) và giới hạn tốc độ theo IP."""
import hashlib
import hmac
import time
from collections import defaultdict, deque

from . import config


def bam_ip(ip: str, secret: str | None = None) -> str:
    """Băm IP bằng HMAC-SHA256 với khóa bí mật IP_HASH_SECRET.

    Cùng IP cho cùng kết quả (để gắn cờ trùng), nhưng không suy ngược ra IP được.
    """
    khoa = config.IP_HASH_SECRET if secret is None else secret
    if not khoa:
        raise RuntimeError("Chưa có IP_HASH_SECRET trong .env.")
    return hmac.new(khoa.encode(), (ip or "").encode(), hashlib.sha256).hexdigest()


class GioiHanTocDo:
    """Cho mỗi khóa (IP) tối đa `toi_da` lần trong `giay` giây. Lưu trong bộ nhớ của server."""

    def __init__(self, toi_da: int = 10, giay: int = 60):
        self.toi_da = toi_da
        self.giay = giay
        self._lan = defaultdict(deque)

    def cho_phep(self, khoa: str, bay_gio: float | None = None) -> bool:
        """True nếu còn lượt (và tính một lượt), False nếu đã vượt giới hạn."""
        t = time.monotonic() if bay_gio is None else bay_gio
        hang = self._lan[khoa]
        while hang and t - hang[0] >= self.giay:
            hang.popleft()  # bỏ các lần đã quá cửa sổ thời gian
        if len(hang) >= self.toi_da:
            return False
        hang.append(t)
        return True

    def xoa(self) -> None:
        """Xóa hết bộ đếm (dùng khi thử)."""
        self._lan.clear()
