"""Cấu hình đọc từ biến môi trường (file .env). Không ghi khóa bí mật vào code."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:  # chưa cài python-dotenv thì bỏ qua
    pass

MONGODB_URI = os.environ.get("MONGODB_URI", "")
MONGODB_DB = os.environ.get("MONGODB_DB", "spark-mind")
INGEST_SECRET = os.environ.get("INGEST_SECRET", "")  # khóa bí mật để Apps Script gửi form vào server

IP_HASH_SECRET = os.environ.get("IP_HASH_SECRET", "")  # khóa HMAC để băm IP, không bao giờ lưu IP thô

# Trang quản trị (thống kê)
NHAN_HOP_LE = ("thu", "pilot", "that")   # nhãn dữ liệu (trường data_label): thử, thử nghiệm 30/11, thật
NHAN_MAC_DINH = "that"                    # bản ghi chưa có data_label được coi là "that" (an toàn: không bao giờ bị xóa nhầm)
NHAN_DU_LIEU_THU = ("thu", "pilot")       # các nhãn bị ẩn bởi công tắc "ẩn dữ liệu thử" và bị "xóa dữ liệu thử" xóa
# Các game bắt buộc để được coi là hoàn thành (gán participants.completed_at). Thêm game mới: thêm số vào đây.
# Nộp xong cả 3 game thì participants.completed_at được gán và GET /api/research/result mới trả kết quả (chưa xong thì 409).
GAME_BAT_BUOC = (1, 2, 3)
GAME_DA_CO = (1, 2, 3)   # game đã có màn chơi, theo thứ tự chơi (endpoint tiến độ dùng để chỉ bước kế tiếp)
# ---- Cờ chống gian lận hướng 2 (CHỈ GẮN CỜ, không xóa, không báo người chơi). Giá trị TẠM, chỉnh lại sau pilot 29/11 ----
# Đổi ngưỡng ở đây rồi chạy lại: python scripts/compute_flags.py (xem docs/decisions.md, mục "Cờ chống gian lận")
CO_NGUONG_CAU_NHANH_MS = 1000        # khoảng cách tới câu trước dưới số này (mili giây) = "câu nhanh"
CO_TI_LE_CAU_NHANH = 0.6             # tỉ lệ câu nhanh từ mức này trở lên = lam_qua_nhanh
CO_SO_CAU_TOI_THIEU = 3              # có ít hơn số câu đo được này thì không xét tỉ lệ câu nhanh (không đủ dữ liệu)
CO_TONG_GIAY_TOI_THIEU = {"form_b": 40, "khoi_c": 15, "game1": 20, "game2": 20, "game3": 30}   # tổng thời gian một bước dưới số giây này = lam_qua_nhanh (game3: tính cho MỖI tình huống, theo thời gian dùng ô nhập)
CO_GAME3_TONG_GIAY_TOI_THIEU = 60    # game 3: cả game (server tính từ lúc bắt đầu đến lúc nộp) dưới số giây này cũng = lam_qua_nhanh (NGƯỠNG TẠM, chỉnh lại sau pilot 29/11)
CO_KHOANG_GIAN_DOAN_MS = 180_000     # một khoảng cách (đã trừ thời gian ẩn tab) dài hơn 3 phút = bi_gian_doan
CO_AN_TAB_GIAN_DOAN_MS = 120_000     # tổng thời gian ẩn tab của một bước dài hơn 2 phút = bi_gian_doan
CO_COPY_GIU_TU_GOC = 0.8             # copy_ai_goc (game 3): tỉ lệ từ của câu gốc AI còn trong bài >= mức này ...
CO_COPY_TU_MOI_TOI_DA = 0.4          # ... VÀ tỉ lệ từ mới (không có trong câu gốc) < mức này. Ngưỡng TẠM, chỉnh sau pilot 29/11
CO_THAM_KHAO = ("bi_gian_doan",)     # cờ chỉ để tham khảo: KHÔNG tính vào flag_count
THOI_GIAN_CAU_TOI_DA_MS = 86_400_000 # chặn số vô lý từ trình duyệt (1 ngày)

MUC_TIEU_HUONG1 = 1000                # số form mục tiêu của hướng 1
MUC_TIEU_HUONG2 = 300                 # số người hoàn thành mục tiêu của hướng 2
ATLAS_GIOI_HAN_MB = 512               # dung lượng gói Atlas M0

RAW_EXCEL = ROOT / "data" / "raw" / "data_raw.xlsx"
PROCESSED = ROOT / "data" / "processed"

COL_RAW = "survey_form1"     # dữ liệu gốc, không sửa
COL_CLEAN = "survey_clean"   # dữ liệu đã làm sạch kèm cờ chất lượng

# Bản dữ liệu CHÍNH của báo cáo (chốt 20/11/2026): bản chặt, 297 form. Khóa cũ không đổi tên.
# Notebook và script lấy bản mặc định từ đây: lay_ban(sach, config.BAN_CHINH)
BAN_CHINH = "chat"

# Tên file xuất ra cho từng bản dữ liệu (khóa nội bộ -> tên tiếng Anh)
FILE_NAME = {"chinh": "main", "chat": "strict", "rat_chat": "very_strict"}

# ---- Chấm điểm trên web (phiên 3) ----
RATING_MUC_TOI_THIEU_KAPPA = 20      # ít hơn số mục hai người cùng chấm xong này thì báo "chưa đủ dữ liệu" (có thể đổi bằng tham số khi xem)
RATING_NGUONG_LECH_GAME3 = 2         # game 3: hai người lệch từ số điểm này trở lên ở BẤT KỲ tiêu chí nào (hoặc một bên X, một bên không) thì liệt kê để thảo luận
RATING_GIAY_TOI_DA_MOT_MUC = 3600    # chặn số vô lý từ trình duyệt: thời gian chấm một mục tối đa 1 giờ
