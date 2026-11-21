"""Bảo mật cho chế độ nghiên cứu: băm IP (không lưu IP thô) và giới hạn tốc độ theo IP."""
import hashlib
import hmac
import math
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

    def _don_hang(self, khoa: str, t: float) -> deque:
        """Bỏ các lần đã quá cửa sổ thời gian rồi trả hàng đợi của khóa."""
        hang = self._lan[khoa]
        while hang and t - hang[0] >= self.giay:
            hang.popleft()
        return hang

    def giay_phai_cho(self, khoa: str, bay_gio: float | None = None) -> int:
        """Số giây còn phải đợi nếu khóa đang bị chặn; 0 nếu chưa bị chặn. KHÔNG tính thêm lượt."""
        t = time.monotonic() if bay_gio is None else bay_gio
        hang = self._don_hang(khoa, t)
        if len(hang) < self.toi_da:
            return 0
        return max(1, math.ceil(self.giay - (t - hang[0])))

    def ghi_nhan(self, khoa: str, bay_gio: float | None = None) -> None:
        """Ghi một lần (ví dụ một lần nhập mã sai) cho khóa."""
        t = time.monotonic() if bay_gio is None else bay_gio
        self._don_hang(khoa, t).append(t)

    def xoa(self) -> None:
        """Xóa hết bộ đếm (dùng khi thử)."""
        self._lan.clear()
