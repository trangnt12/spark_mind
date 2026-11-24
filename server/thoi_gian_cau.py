"""Dữ liệu thời gian từng câu do trình duyệt gửi kèm khi nộp form B và khối C1–C5. Chỉ chứa SỐ.

Trình duyệt tự đo nên có thể bị giả: dữ liệu này chỉ để gắn cờ (src/sparkmind/flags.py), không dùng để loại ai.
"""
from pydantic import BaseModel, Field, field_validator

from sparkmind import config

CAU_FORM_B = tuple(f"B4_{i}" for i in range(1, 8))   # các câu Likert của form B
CAU_KHOI_C = tuple(f"C{i}" for i in range(1, 6))     # các câu Likert của khối C1–C5
TOI_DA = config.THOI_GIAN_CAU_TOI_DA_MS


class ThoiGianCau(BaseModel):
    khoang_ms: dict[str, int] = Field(default_factory=dict, max_length=20)    # câu -> mili giây tới câu trả lời trước (đã trừ ẩn tab)
    sua_cuoi_ms: dict[str, int] = Field(default_factory=dict, max_length=20)  # câu -> mốc lần sửa cuối, tính từ lúc hiện trang
    an_tab_ms: int = Field(default=0, ge=0, le=TOI_DA)                        # tổng thời gian tab bị ẩn
    tong_ms: int = Field(default=0, ge=0, le=TOI_DA)                          # từ lúc hiện trang đến lúc nộp, đã trừ ẩn tab

    @field_validator("khoang_ms", "sua_cuoi_ms")
    @classmethod
    def _so_hop_le(cls, v):
        """Mọi số phải nằm trong 0..TOI_DA (chặn số vô lý), nếu không thì từ chối cả gói."""
        if any(not 0 <= x <= TOI_DA for x in v.values()):
            raise ValueError("thời gian ngoài khoảng cho phép")
        return v


def de_luu(tg: ThoiGianCau | None, cac_cau: tuple) -> dict | None:
    """Dạng đem lưu: chỉ giữ các câu thuộc khối này (bỏ khóa lạ). None nếu trình duyệt không gửi."""
    if tg is None:
        return None
    d = tg.model_dump()
    for khoa in ("khoang_ms", "sua_cuoi_ms"):
        d[khoa] = {k: v for k, v in d[khoa].items() if k in cac_cau}
    return d
