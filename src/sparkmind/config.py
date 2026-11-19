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

RAW_EXCEL = ROOT / "data" / "raw" / "data_raw.xlsx"
PROCESSED = ROOT / "data" / "processed"

COL_RAW = "survey_form1"     # dữ liệu gốc, không sửa
COL_CLEAN = "survey_clean"   # dữ liệu đã làm sạch kèm cờ chất lượng

# Tên file xuất ra cho từng bản dữ liệu (khóa nội bộ -> tên tiếng Anh)
FILE_NAME = {"chinh": "main", "chat": "strict", "rat_chat": "very_strict"}
