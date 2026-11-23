"""Chấm tự động game 1 (Đồ vật bí ẩn): chỉ lọc ý hợp lệ và đếm (fluency).

Chạy SAU khi thu dữ liệu, không chạy lúc người chơi nộp. Đa dạng (flexibility) và độc đáo
(originality) làm ở bước phân tích. Quy tắc chi tiết: docs/rubric_game1.md.
"""
import re
import unicodedata

SO_TU_TOI_THIEU = 2  # ý phải có ít nhất 2 từ


def bo_dau(chu: str) -> str:
    """Bỏ dấu tiếng Việt: "Đỡ cây" -> "Do cay" (đ/Đ đổi riêng vì không tách được bằng NFD)."""
    chu = chu.replace("đ", "d").replace("Đ", "D")
    tach = unicodedata.normalize("NFD", chu)
    return "".join(c for c in tach if unicodedata.category(c) != "Mn")


def chuan_hoa_y(y: str) -> str:
    """Chuẩn hóa để so sánh: NFC, hạ chữ thường, bỏ dấu câu, gộp khoảng trắng. VẪN GIỮ dấu tiếng Việt."""
    y = unicodedata.normalize("NFC", y or "").lower()
    y = re.sub(r"[^\w\s]|_", " ", y)  # \w giữ chữ cái (có dấu) và số
    return " ".join(y.split())


def khoa_so_sanh(y: str) -> str:
    """Khóa để phát hiện trùng: đã chuẩn hóa và bỏ dấu, nên "Đỡ cây" và "do cay" cùng một khóa."""
    return bo_dau(chuan_hoa_y(y))


def chi_la_ten_do_vat(y: str, ten_do_vat: str) -> bool:
    """True nếu mọi từ của ý đều nằm trong tên đồ vật (vd "gạch", "viên gạch" với đồ vật "Viên gạch")."""
    tu_y = set(khoa_so_sanh(y).split())
    return bool(tu_y) and tu_y <= set(khoa_so_sanh(ten_do_vat).split())


def ly_do_loai(y: str, ten_do_vat: str, da_thay: set) -> str | None:
    """Trả lý do loại ("rong", "chi_ten_do_vat", "qua_ngan", "trung") hoặc None nếu ý hợp lệ."""
    khoa = khoa_so_sanh(y)
    if not khoa:
        return "rong"
    if chi_la_ten_do_vat(y, ten_do_vat):
        return "chi_ten_do_vat"
    if len(khoa.split()) < SO_TU_TOI_THIEU:
        return "qua_ngan"
    return "trung" if khoa in da_thay else None


def loc_y_hop_le(ideas: list, ten_do_vat: str) -> tuple[list, list]:
    """Tách ý hợp lệ (giữ nguyên chữ gốc, giữ thứ tự) và ý bị loại [(ý, lý do)]. Ý trùng: giữ ý đầu tiên."""
    hop_le, bi_loai, da_thay = [], [], set()
    for y in ideas:
        ly_do = ly_do_loai(y, ten_do_vat, da_thay)
        if ly_do:
            bi_loai.append((y, ly_do))
        else:
            hop_le.append(y)
            da_thay.add(khoa_so_sanh(y))
    return hop_le, bi_loai


def dem_y_hop_le(ideas: list, ten_do_vat: str) -> int:
    """Số ý hợp lệ (fluency)."""
    return len(loc_y_hop_le(ideas, ten_do_vat)[0])


def cham_game1(ideas: list, ten_do_vat: str, paste_count: int = 0, over_time: bool = False) -> dict:
    """Chấm một bài. Bài hết giờ/lỗi vẫn tính các ý đã nộp; cờ chỉ để người phân tích quyết định có loại hay không."""
    hop_le, bi_loai = loc_y_hop_le(ideas, ten_do_vat)
    return {"so_y": len(ideas), "so_y_hop_le": len(hop_le), "y_hop_le": hop_le, "y_bi_loai": bi_loai,
            "co_dan": paste_count > 0, "over_time": over_time}
