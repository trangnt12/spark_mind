"""Kiểm tra các hàm thống kê mô tả (notebook 02) bằng dữ liệu nhỏ biết trước kết quả."""
import numpy as np
import pandas as pd

from sparkmind.stats_desc import cronbach_alpha, so_sanh_nhom, bang_tuong_quan


def test_alpha_cac_cau_giong_nhau_bang_1():
    x = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [1, 2, 3, 4, 5], "c": [1, 2, 3, 4, 5]})
    a, n = cronbach_alpha(x)
    assert abs(a - 1) < 1e-9 and n == 5


def test_alpha_bo_dong_thieu():
    x = pd.DataFrame({"a": [1, 2, 3, np.nan], "b": [1, 3, 2, 4]})
    assert cronbach_alpha(x)[1] == 3


def test_so_sanh_chon_dung_phep_thu():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"g2": ["a", "b"] * 20, "g3": ["a", "b", "c", "a"] * 10, "diem_sang_tao": rng.random(40)})
    assert so_sanh_nhom(df, "g2")["phep_thu"] == "Mann-Whitney U"
    assert so_sanh_nhom(df, "g3")["phep_thu"] == "Kruskal-Wallis H"


def test_nhom_qua_nho_bi_bo():
    df = pd.DataFrame({"g": ["a"] * 10 + ["b"] * 10 + ["c"] * 2, "diem_sang_tao": np.arange(22.0)})
    r = so_sanh_nhom(df, "g")
    assert r["so_nhom"] == 2 and r["nhom_bi_bo"] == "c"


def test_tuong_quan_dem_so_quan_sat():
    df = pd.DataFrame({c: np.arange(10.0) for c in
                       [f"B4_{i}" for i in range(1, 8)] + ["B2_so", "B5_so", "diem_hanh_vi", "diem_sang_tao"]})
    df.loc[0, "B2_so"] = np.nan
    t = bang_tuong_quan(df)
    assert t[(t.bien_1 == "B2_so") & (t.bien_2 == "B5_so")]["n"].iloc[0] == 9


def test_holm_ket_qua_biet_truoc():
    from sparkmind.stats_desc import holm
    assert np.allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
