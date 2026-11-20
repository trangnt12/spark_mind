"""Tên cột, bảng quy đổi chữ -> số, và quy tắc gán đợt thu."""
import re

B4 = [f"B4_{i}" for i in range(1, 8)]
CC = [f"C{i}" for i in range(1, 6)]
NEG = ["B4_3", "B4_6"]  # câu hành vi tiêu cực, đảo chiều khi tính điểm tổng

# Các cột gốc chuẩn (tên ngắn). Google Form, web đều gửi đúng các khóa này.
RAW_KEYS = (["thoi_gian", "A1", "A2", "A3", "A4", "B1", "B2", "B3"] + B4
            + ["B5", "B6", "B7"] + CC + ["C6"])

# Bảng chữ -> số nhận CẢ chữ cũ (form v1) lẫn chữ mới (form v2, từ 20/11/2026)
ORD2 = {"Rất hiếm khi": 1, "Vài lần/tháng": 2, "Vài lần/tuần": 3, "Hầu như mỗi ngày": 4,
        "Vài lần mỗi tháng": 2, "Vài lần mỗi tuần": 3}
ORD5 = {"Dưới 5 phút": 1, "5–15 phút": 2, "15–30 phút": 3, "Trên 30 phút": 4,
        "Từ 5 đến 15 phút": 2, "Từ 15 đến 30 phút": 3}

# Câu chọn nhiều: tìm theo từ khóa (có thể nhiều từ khóa: chữ cũ và chữ mới), vì câu chữ dài có dấu phẩy
B1_KW = {"chatgpt": ("ChatGPT",), "gemini": ("Gemini",), "copilot": ("Copilot",), "claude": ("Claude",)}
B3_KW = {"bai_tap": ("Giải bài tập",), "khai_niem": ("Giải thích khái niệm", "Giải thích các khái niệm"),
         "viet_luan": ("Viết luận", "Viết bài luận"), "tom_tat": ("Tóm tắt",),
         "brainstorm": ("Brainstorm", "Lên ý tưởng"), "dich": ("Dịch thuật",), "giai_tri": ("Trò chuyện",)}
B6_KW = {"ngan": ("Gõ ngắn gọn", "Nhập câu hỏi"),
         "ngu_canh": ("ngữ cảnh/vai trò", "ngữ cảnh hoặc vai trò"),
         "dinh_dang": ("yêu cầu về định dạng",), "vi_du": ("ví dụ mẫu",)}
B7_KW = {"viet_lai": ("Đọc lướt",), "doi_chieu": ("So sánh", "Đối chiếu"),
         "tiep_tuc": ("Tiếp tục gõ", "Tiếp tục nhập"), "sao_chep": ("Sao chép",)}

# C6 (hoạt động sáng tạo 12 tháng): tiền tố của câu trả lời -> mã 0/1/2 (chữ cũ và mới)
C6_TIEN_TO = {0: ("Chưa",), 1: ("Có tham gia", "Đã tham gia"), 2: ("Đã từng và", "Đã từng tham gia và")}

# Ngưỡng chia mức theo điểm 0-100
NGUONG_THAP = 60
NGUONG_CAO = 80

# Đợt thu theo ngày (khoảng ngày, bao gồm hai đầu). Thêm đợt mới ở đây khi cần.
DOT_RULES = [
    ("dot1_rai_rac", "2000-01-01", "2026-09-15"),
    ("dot2_16/9", "2026-09-16", "2026-09-16"),
    ("dot3_4-5/11", "2026-11-04", "2026-11-05"),
    ("dot5_form_v2", "2026-11-20", "2099-12-31"),  # form đổi chữ (v2) nộp từ 20/11/2026
]
DOT_MAC_DINH_SAU = "dot4_sau_5_11"  # mọi form sau ngày 5/11 chưa có luật riêng
NGAY_CUOI_DOT3 = "2026-11-05"


def ten_ngan(tieu_de: str) -> str:
    """Đổi tiêu đề dài của Google Form thành tên ngắn (A1, B4_1, C3...).

    Nhận cả nhãn dòng lưới cũ [C1. ...] và mới [C1.1 ...]; câu "C2." (mới) hoặc "C6." (cũ) là C6.
    """
    m = re.search(r"\[B4\.(\d)[\. ]", tieu_de)
    if m:
        return f"B4_{m.group(1)}"
    m = re.search(r"\[C1\.(\d)[\. ]", tieu_de)  # nhãn mới C1.1..C1.5 -> C1..C5
    if m:
        return f"C{m.group(1)}"
    m = re.search(r"\[C(\d)[\. ]", tieu_de)  # nhãn cũ C1..C5
    if m:
        return f"C{m.group(1)}"
    m = re.match(r"(A\d|B\d|C\d)\.", tieu_de)
    if m:
        return "C6" if m.group(1) in ("C2", "C6") else m.group(1)
    if tieu_de.startswith("Dấu thời gian"):
        return "thoi_gian"
    return tieu_de
