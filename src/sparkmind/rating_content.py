"""Hướng dẫn chấm đọc từ content/rating_guide.json (không viết cứng trong code). Là nguồn DUY NHẤT cho mã nhóm và tiêu chí."""
import json
from functools import lru_cache

from . import config

X = "X"   # "không chấm được" (mã X ở cả game 1 và game 3)


@lru_cache
def huong_dan() -> dict:
    with open(config.ROOT / "content" / "rating_guide.json", encoding="utf-8") as f:
        return json.load(f)


def ma_nhom_game1() -> list:
    """Các mã hợp lệ của game 1: A–H và X (đúng thứ tự trong content)."""
    return [n["ma"] for n in huong_dan()["game1"]["nhom"]] + [X]


def ma_tieu_chi_game3() -> list:
    return [t["ma"] for t in huong_dan()["game3"]["tieu_chi"]]


def thang_diem_game3() -> list:
    g = huong_dan()["game3"]
    return list(range(g["diem_toi_thieu"], g["diem_toi_da"] + 1))


def kiem_tra_diem(game: int, diem) -> dict:
    """Kiểm tra điểm người chấm gửi lên. Trả (diem đã chuẩn hóa, hoàn_tất). Sai thì ném ValueError("diem_khong_hop_le")."""
    if not isinstance(diem, dict):
        raise ValueError("diem_khong_hop_le")
    if game == 1:
        return _diem_game1(diem)
    return _diem_game3(diem)


def _diem_game1(diem: dict) -> tuple:
    if set(diem) - {"nhom"} or (diem.get("nhom") is not None and diem["nhom"] not in ma_nhom_game1()):
        raise ValueError("diem_khong_hop_le")
    return ({"nhom": diem["nhom"]} if diem.get("nhom") else {}), bool(diem.get("nhom"))


def _diem_game3(diem: dict) -> tuple:
    ma, thang = ma_tieu_chi_game3(), thang_diem_game3()
    if set(diem) - set(ma):
        raise ValueError("diem_khong_hop_le")
    sach = {}
    for k, v in diem.items():
        if v is None:
            continue
        if v != X and not (isinstance(v, int) and not isinstance(v, bool) and v in thang):
            raise ValueError("diem_khong_hop_le")
        sach[k] = v
    return sach, set(sach) == set(ma)
