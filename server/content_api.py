"""Trả nội dung giao diện (câu hỏi form B, chữ giao diện) cho trình duyệt. Không cần đăng nhập."""
import csv
import json
from functools import lru_cache

from fastapi import APIRouter

from sparkmind import config

router = APIRouter(prefix="/api/content")


def bo_ghi_chu(x):
    """Bỏ mọi khóa bắt đầu bằng "_ghi_chu" (ghi chú nội bộ), ở mọi cấp."""
    if isinstance(x, dict):
        return {k: bo_ghi_chu(v) for k, v in x.items() if not k.startswith("_ghi_chu")}
    if isinstance(x, list):
        return [bo_ghi_chu(v) for v in x]
    return x


def doc_noi_dung(ten_file: str) -> dict:
    """Đọc file trong content/ mỗi lần gọi (sửa nội dung không cần khởi động lại server)."""
    with open(config.ROOT / "content" / ten_file, encoding="utf-8") as f:
        return bo_ghi_chu(json.load(f))


@router.get("/form-b")
def form_b():
    return doc_noi_dung("form_b.json")


@router.get("/ui")
def giao_dien():
    return doc_noi_dung("research_ui.json")


@router.get("/results-ui")
def chu_ket_qua():
    """Chữ cho trang kết quả (tên mức, lời nói rõ giới hạn)."""
    return doc_noi_dung("results_ui.json")


@router.get("/game1")
def game1():
    """Chữ hướng dẫn và ví dụ của game 1. Không trả danh sách đồ vật (đồ vật do /game1/start chọn theo mã)."""
    d = doc_noi_dung("games/game1.json")
    return {k: d[k] for k in ("ten", "thoi_gian_giay", "huong_dan", "vi_du", "gioi_han_ky_tu_moi_y")}


@lru_cache
def doc_truong() -> list[dict]:
    """Danh sách trường (content/schools.csv) gọn: tên và cấp, để người dùng chọn trong ô tìm kiếm."""
    with open(config.ROOT / "content" / "schools.csv", encoding="utf-8-sig", newline="") as f:
        return [{"ten": r["ten"], "cap": r["cap_chuan"], "vt": r["viet_tat"]} for r in csv.DictReader(f)]


@router.get("/schools")
def truong():
    return doc_truong()
