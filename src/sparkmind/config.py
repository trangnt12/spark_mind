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
# Game 3 chưa có nên hiện chưa ai hoàn thành; trong lúc chờ, GET /api/research/result vẫn trả 409.
GAME_BAT_BUOC = (1, 2, 3)
GAME_DA_CO = (1, 2)   # game đã có màn chơi, theo thứ tự chơi; làm xong game 3 thì thêm 3 vào đây (endpoint tiến độ dùng để chỉ bước kế tiếp)
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
