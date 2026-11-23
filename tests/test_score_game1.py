"""Kiểm tra chấm game 1: chuẩn hóa, ý trùng, rỗng, tên đồ vật, quá ngắn, tiếng Việt có dấu, cờ."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sparkmind import score_game1 as g  # noqa: E402

GACH = "Viên gạch"


def test_chuan_hoa_giu_dau_bo_dau_cau():
    assert g.chuan_hoa_y("  Dùng  LÀM,   chặn giấy!! ") == "dùng làm chặn giấy"
    assert g.khoa_so_sanh("Đỡ cây") == "do cay"


def test_trung_khac_dau_va_dau_cau():
    ds = ["Làm chặn giấy", "lam chan giay", "LÀM CHẶN GIẤY!!!"]
    assert g.loc_y_hop_le(ds, GACH) == (["Làm chặn giấy"], [(ds[1], "trung"), (ds[2], "trung")])


def test_y_rong_va_chi_dau_cau():
    _, loai = g.loc_y_hop_le(["", "   ", "...", "!!"], GACH)
    assert [ly_do for _, ly_do in loai] == ["rong"] * 4


def test_chi_la_ten_do_vat():
    _, loai = g.loc_y_hop_le(["gạch", "Viên gạch", "VIEN GACH."], GACH)
    assert [ly_do for _, ly_do in loai] == ["chi_ten_do_vat"] * 3


def test_qua_ngan_mot_tu():
    assert g.loc_y_hop_le(["chặn"], GACH) == ([], [("chặn", "qua_ngan")])


def test_tieng_viet_co_dau_hop_le():
    ds = ["Kê chân bàn cho khỏi cập kênh", "Nghiền nhỏ làm bột vẽ"]
    assert g.dem_y_hop_le(ds, GACH) == 2


def test_y_co_ten_do_vat_kem_cong_dung_van_hop_le():
    assert g.dem_y_hop_le(["Dùng gạch làm bếp nướng"], GACH) == 1


def test_cham_bai_dan_va_het_gio():
    kq = g.cham_game1(["Chặn cửa", "chan cua", "gạch", ""], GACH, paste_count=1, over_time=True)
    assert (kq["so_y"], kq["so_y_hop_le"]) == (4, 1)
    assert kq["co_dan"] is True and kq["over_time"] is True
    assert g.cham_game1([], GACH)["so_y_hop_le"] == 0
