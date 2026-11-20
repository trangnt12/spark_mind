"""Kiểm tra chuẩn hóa tên trường không cần duyệt tay: khop_cung_ten, khop_gan_dung, chua_chuan_hoa."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sparkmind.school_matching import chuan_chu, chuan_hoa_ds, khop_truong, tao_khoa  # noqa: E402


def ds_mau(ten_cap: list) -> pd.DataFrame:
    """Danh sách trường mẫu từ các cặp (tên, cấp: 'Cấp 2' / 'Cấp 3' / 'Đại học')."""
    return chuan_hoa_ds(pd.DataFrame({"a": range(len(ten_cap)), "b": [t for t, _ in ten_cap],
                                      "c": [""] * len(ten_cap), "d": [c for _, c in ten_cap]}))


def chay(ds, ten_lop: list) -> pd.DataFrame:
    """Chạy khop_truong cho các cặp (chữ người gõ, số lớp)."""
    d = pd.DataFrame({"A3": [t for t, _ in ten_lop], "lop_so": [x for _, x in ten_lop]})
    d["cap_hoc"] = np.select([d.lop_so <= 9, d.lop_so <= 12], ["THCS", "THPT"], default="Đại học")
    d["truong_cap"], d["truong_khoa"] = zip(*d["A3"].map(tao_khoa))
    d["truong_chuan"] = ""
    return khop_truong(d, ds)


def test_khop_cung_ten_bo_id():
    ds = ds_mau([("Trường THPT Lê Lợi", "Cấp 3"), ("Trường THPT Lê Lợi", "Cấp 3")])  # hai dòng trùng tên
    d = chay(ds, [("thpt le loi", 11)])
    assert d["truong_khop"].iloc[0] == "khop_cung_ten"
    assert d["truong_chuan"].iloc[0] == "Trường THPT Lê Lợi" and d["truong_ds_id"].iloc[0] == ""


def test_trung_khac_ten_di_so_gan_dung_lay_ung_vien_dau():
    """Hai trường khác tên chuẩn nhưng cùng khóa (khác dấu): so gần đúng, giống ngang nhau lấy trường đầu."""
    ds = ds_mau([("Trường THPT Phú Mỹ", "Cấp 3"), ("Trường THPT Phù Mỹ", "Cấp 3")])
    d = chay(ds, [("thpt phu my", 11)])
    assert d["truong_khop"].iloc[0] == "khop_gan_dung" and d["truong_do_giong"].iloc[0] == 1.0
    assert d["truong_chuan"].iloc[0] == "Trường THPT Phú Mỹ"


def test_gan_dung_mot_ung_vien():
    ds = ds_mau([("Trường THPT Nguyễn Trung Trực", "Cấp 3"), ("Trường THPT Hùng Vương", "Cấp 3")])
    d = chay(ds, [("THPT Nguyen Trung Truc A", 11)])  # thừa một chữ -> giống >= 0.90
    assert d["truong_khop"].iloc[0] == "khop_gan_dung"
    assert d["truong_chuan"].iloc[0] == "Trường THPT Nguyễn Trung Trực" and d["truong_ds_id"].iloc[0] != ""


def test_gan_dung_lay_ung_vien_giong_nhat():
    ds = ds_mau([("Trường THPT Nguyễn Trung", "Cấp 3"), ("Trường THPT Nguyễn Trung Trực", "Cấp 3")])
    d = chay(ds, [("THPT Nguyễn Trung Trực A", 11)])
    assert d["truong_chuan"].iloc[0] == "Trường THPT Nguyễn Trung Trực"
    assert d["truong_khop"].iloc[0] == "khop_gan_dung" and 0.9 <= d["truong_do_giong"].iloc[0] < 1


def test_khop_doan_tu_060_den_duoi_090():
    ds = ds_mau([("Trường THPT Nguyễn Trung Trực", "Cấp 3")])
    d = chay(ds, [("THPT Nguyễn Trung", 11), ("THPT Nguyễn Trãi", 11)])  # giống 0.83 và 0.64
    assert d["truong_khop"].tolist() == ["khop_doan", "khop_doan"]
    assert (d["truong_chuan"] == "Trường THPT Nguyễn Trung Trực").all()
    assert d["truong_do_giong"].between(0.6, 0.9, inclusive="left").all()


def test_gan_dung_chi_trong_cung_cap():
    ds = ds_mau([("Trường THCS Nguyễn Trung Trực", "Cấp 2")])  # chỉ có THCS
    d = chay(ds, [("THPT Nguyễn Trung Trực A", 11)])  # học sinh lớp 11 (THPT) -> không so với THCS
    assert d["truong_khop"].iloc[0] == "chua_chuan_hoa" and d["truong_do_giong"].iloc[0] == 0.0


def test_duoi_nguong_060_giu_chu_nguoi_go():
    ds = ds_mau([("Trường THPT Nguyễn Trung Trực", "Cấp 3")])
    d = chay(ds, [("thpt  trần   phú", 11)])  # giống 0.40
    assert d["truong_khop"].iloc[0] == "chua_chuan_hoa" and d["truong_chuan"].iloc[0] == "Thpt Trần Phú"
    assert d["truong_do_giong"].iloc[0] < 0.6 and d["truong_ds_ten"].iloc[0] == ""


def test_chua_chuan_hoa_chi_gon_khoang_trang_va_viet_hoa():
    assert chuan_chu("  dh   công nghiệp hà nội - HaUI ") == "Dh Công Nghiệp Hà Nội - HaUI"
    assert chuan_chu(None) == "" and chuan_chu(float("nan")) == ""
    d = chay(ds_mau([("Trường THPT Lê Lợi", "Cấp 3")]), [("  ITMO  ", 14)])
    assert d["truong_khop"].iloc[0] == "chua_chuan_hoa" and d["truong_chuan"].iloc[0] == "ITMO"
    assert d["truong_ds_ten"].iloc[0] == ""


def test_override_thu_cong_van_chay():
    ds = ds_mau([("Trường THPT Lê Lợi", "Cấp 3")])
    d = pd.DataFrame({"A3": ["abc"], "lop_so": [11]})
    d["cap_hoc"] = "THPT"
    d["truong_cap"], d["truong_khoa"] = zip(*d["A3"].map(tao_khoa))
    d["truong_chuan"] = "Tên Do Trang Duyệt"
    khop_truong(d, ds)
    assert d["truong_khop"].iloc[0] == "thu_cong" and d["truong_chuan"].iloc[0] == "Tên Do Trang Duyệt"
