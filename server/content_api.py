"""Trả nội dung giao diện (câu hỏi form B, chữ giao diện) cho trình duyệt. Không cần đăng nhập."""
import csv
import json
from functools import lru_cache

from fastapi import APIRouter, HTTPException

from sparkmind import config, game3_store

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


@router.get("/landing")
def chu_trang_chu():
    """Chữ cho trang chủ "/" và màn chọn hình thức tham gia (content/landing_ui.json)."""
    return doc_noi_dung("landing_ui.json")


@router.get("/results-ui")
def chu_ket_qua():
    """Chữ cho trang kết quả (tên mức, lời nói rõ giới hạn)."""
    return doc_noi_dung("results_ui.json")


@router.get("/game1")
def game1():
    """Chữ hướng dẫn và ví dụ của game 1. Không trả danh sách đồ vật (đồ vật do /game1/start chọn theo mã)."""
    d = doc_noi_dung("games/game1.json")
    return {k: d[k] for k in ("ten", "thoi_gian_giay", "gioi_thieu", "vi_du", "gioi_han_ky_tu_moi_y")}


@router.get("/gioi-thieu/{so}")
def gioi_thieu_game(so: int):
    """Chỉ tên và khối hướng dẫn của game 1, 2 hoặc 3 (cho trang giới thiệu riêng của từng game). Không có đề hay đáp án."""
    if so not in (1, 2, 3):
        raise HTTPException(404, "Không có game này.")
    d = doc_noi_dung(f"games/game{so}.json")
    return {"so": so, "ten": d["ten"], "gioi_thieu": d["gioi_thieu"]}


@router.get("/game3")
def game3():
    """Đề game 3 cho giao diện: tên, lời dẫn, hai tình huống kèm ý tưởng của AI, giới hạn từ/ký tự. Không có trường nào khác."""
    return game3_store.noi_dung_cho_trinh_duyet(doc_noi_dung("games/game3.json"))


@lru_cache
def doc_truong() -> list[dict]:
    """Danh sách trường (content/schools.csv) gọn: tên và cấp, để người dùng chọn trong ô tìm kiếm."""
    with open(config.ROOT / "content" / "schools.csv", encoding="utf-8-sig", newline="") as f:
        return [{"ten": r["ten"], "cap": r["cap_chuan"], "vt": r["viet_tat"]} for r in csv.DictReader(f)]


@router.get("/schools")
def truong():
    return doc_truong()
