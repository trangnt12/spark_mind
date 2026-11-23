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
MONGODB_DB = os.environ.get("MONGODB_DB", "spark_mind")
INGEST_SECRET = os.environ.get("INGEST_SECRET", "")  # khóa bí mật để Apps Script gửi form vào server

IP_HASH_SECRET = os.environ.get("IP_HASH_SECRET", "")  # khóa HMAC để băm IP, không bao giờ lưu IP thô

# Trang quản trị (thống kê)
NHAN_DU_LIEU_THU = ("thu", "pilot")   # giá trị nguon/dot/source đánh dấu dữ liệu thử; công tắc "ẩn dữ liệu thử" loại chúng ra
MUC_TIEU_HUONG1 = 1000                # số form mục tiêu của hướng 1
MUC_TIEU_HUONG2 = 300                 # số người hoàn thành mục tiêu của hướng 2
ATLAS_GIOI_HAN_MB = 512               # dung lượng gói Atlas M0

RAW_EXCEL =ROOT / "data" / "raw" / "data_raw.xlsx"
PROCESSED = ROOT / "data" / "processed"

COL_RAW = "survey_form1"     # dữ liệu gốc, không sửa
COL_CLEAN = "survey_clean"   # dữ liệu đã làm sạch kèm cờ chất lượng

# Bản dữ liệu CHÍNH của báo cáo (chốt 20/11/2026): bản chặt, 297 form. Khóa cũ không đổi tên.
# Notebook và script lấy bản mặc định từ đây: lay_ban(sach, config.BAN_CHINH)
BAN_CHINH = "chat"

# Tên file xuất ra cho từng bản dữ liệu (khóa nội bộ -> tên tiếng Anh)
FILE_NAME = {"chinh": "main", "chat": "strict", "rat_chat": "very_strict"}
