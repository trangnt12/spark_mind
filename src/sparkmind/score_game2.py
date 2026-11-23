"""Chấm tự động game 2 (Soi lỗi AI). Hàm thuần, không đụng MongoDB.

+1 mỗi ý SAI được chọn đúng, -1 mỗi ý ĐÚNG bị chọn nhầm, tối thiểu 0, tối đa 5 (= số ý sai).
"""
DIEM_TOI_DA = 5


def cham_game2(y: list, da_chon: list) -> dict:
    """y: danh sách ý trong content (có la_loi). da_chon: các id người chơi cho là sai. Trả điểm và hai số đếm."""
    chon = set(da_chon)
    n_dung = sum(1 for i in y if i["la_loi"] and i["id"] in chon)
    n_nham = sum(1 for i in y if not i["la_loi"] and i["id"] in chon)
    diem = min(DIEM_TOI_DA, max(0, n_dung - n_nham))
    return {"score": diem, "n_correct": n_dung, "n_wrong": n_nham}
