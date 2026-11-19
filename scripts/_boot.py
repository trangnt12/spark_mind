"""Cho phép script import gói sparkmind từ thư mục src (không cần cài đặt)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
