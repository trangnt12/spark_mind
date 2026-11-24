"""Kiểm tra mô-đun huấn luyện mô hình (dữ liệu giả, không cần Excel). Chạy: python -m pytest tests -q"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sparkmind import modeling as M  # noqa: E402


def du_lieu_gia(n: int = 90, seed: int = 0) -> pd.DataFrame:
    """Bảng giả có đủ cột như bản đã làm sạch; điểm phụ thuộc nhẹ vào B4_1 để mô hình có gì đó để học."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.integers(0, 2, n).astype(float) for c in M.DAC_TRUNG})
    for c in ["lop_so", "B2_so", "B5_so", "B1_so", "B3_so", "B6_so"] + [f"B4_{i}" for i in range(1, 8)]:
        df[c] = rng.integers(1, 6, n).astype(float)
    df["cap_hoc"] = rng.choice(["THCS", "THPT", "Đại học"], n)
    df["diem_sang_tao"] = df["B4_1"] * 15 + rng.normal(0, 8, n)
    df["muc"] = pd.cut(df["diem_sang_tao"], [-99, 45, 60, 999], labels=M.MUC_THU_TU).astype(str)
    df["muc"] = df["muc"].where(df.index >= 3, M.MUC_THU_TU[0])
    return df


def test_cam_cot_cam_bao_loi():
    """Đưa C1 (hoặc muc, dot, in_*, C6_so) vào bảng đặc trưng thì phải báo lỗi."""
    for cot_xau in ["C1", "C5", "muc", "diem_sang_tao", "C6", "C6_so", "dot", "nguon", "thoi_gian",
                    "in_chat", "co_mot_muc_12", "truong_chuan", "ten_truong", "_id", "id"]:
        with pytest.raises(ValueError, match="CẤM"):
            M.kiem_tra_cot_cam(M.DAC_TRUNG + [cot_xau])


def test_cot_co_va_thoi_gian_bi_cam():
    """Cờ chống gian lận và các trường đo thời gian (24/11) không bao giờ được vào bảng đặc trưng."""
    for cot in ["flags", "flag_count", "thoi_gian_cau", "khoang_ms", "sua_cuoi_ms", "an_tab_ms", "tong_ms",
                "ty_le_cau_nhanh", "lam_qua_nhanh", "mot_dap_an", "bi_gian_doan", "duration_sec", "batch",
                "flag_xyz", "thoi_gian_moi", "khoang_dai_nhat"]:
        with pytest.raises(ValueError, match="CẤM"):
            M.kiem_tra_cot_cam(M.DAC_TRUNG + [cot])
    assert not set(M.DAC_TRUNG) & {"flags", "flag_count", "thoi_gian_cau", "an_tab_ms", "tong_ms"}


def test_cot_la_ngoai_danh_sach_bi_chan():
    with pytest.raises(ValueError, match="ngoài danh sách"):
        M.kiem_tra_cot_cam(M.DAC_TRUNG + ["diem_hanh_vi"])


def test_danh_sach_dac_trung_hop_le_va_c6_chi_khi_cho_phep():
    M.kiem_tra_cot_cam(M.DAC_TRUNG)                       # danh sách chuẩn không lỗi
    df = du_lieu_gia(); df["C6_so"] = 1.0
    assert "C6_so" not in M.tao_dac_trung(df).columns
    assert "C6_so" in M.tao_dac_trung(df, cho_phep=("C6_so",)).columns


def test_chay_cv_chan_cot_cam():
    df = du_lieu_gia(); X = M.tao_dac_trung(df); X["C1"] = 3
    yl, _ = M.tao_nhan(df)
    with pytest.raises(ValueError, match="CẤM"):
        M.chay_cv(X, yl, M.tao_mo_hinh_phan_loai(M._cot_so(X)), M.tao_cac_lan_chia(yl, 1), "lop")


def test_pipeline_khong_ro_ri():
    """Trung vị và trung bình chuẩn hóa phải học từ phần train, KHÔNG phải từ toàn bộ dữ liệu."""
    df = du_lieu_gia(); X = M.tao_dac_trung(df); yl, _ = M.tao_nhan(df)
    X.loc[X.index >= 60, "B2_so"] = 5.0               # phần test có giá trị rất khác phần train
    X.loc[X.index < 60, "B2_so"] = 1.0
    X.loc[[0, 70], "B2_so"] = np.nan
    pipe = M.tao_mo_hinh_phan_loai(M._cot_so(X))["Logistic"]
    pipe.fit(X.iloc[:60], yl[:60])
    tx = pipe.named_steps["tien_xu_ly"].named_transformers_["so"]
    i = M._cot_so(X).index("B2_so")
    assert tx.named_steps["dien"].statistics_[i] == 1.0            # trung vị của train, không bị phần test kéo lên
    assert tx.named_steps["chuan"].mean_[i] == pytest.approx(1.0)  # trung bình của train


def test_nhan_xao_tron_cho_diem_gan_ngau_nhien():
    """Kiểm tra rò rỉ: nhãn bị xáo trộn thì macro-F1 phải ở mức đoán ngẫu nhiên (không cao bất thường)."""
    df = du_lieu_gia(150); X = M.tao_dac_trung(df)
    y = np.random.default_rng(1).permutation(M.tao_nhan(df)[0])
    mh = {"Random Forest": M.tao_mo_hinh_phan_loai(M._cot_so(X))["Random Forest"]}
    f = M.chay_cv(X, y, mh, M.tao_cac_lan_chia(y, 2), "lop")
    assert f["macro_f1"].mean() < 0.5


def test_du_5x10_fold_va_lap_lai_duoc():
    df = du_lieu_gia(); X = M.tao_dac_trung(df); yl, _ = M.tao_nhan(df)
    chia = M.tao_cac_lan_chia(yl)
    assert len(chia) == 50                                         # 5 fold x 10 lần lặp
    mh = {k: v for k, v in M.tao_mo_hinh_phan_loai(M._cot_so(X)).items() if k.startswith("Dummy")}
    f1 = M.chay_cv(X, yl, mh, chia, "lop")
    f2 = M.chay_cv(X, yl, mh, M.tao_cac_lan_chia(yl), "lop")       # chia lại từ đầu, cùng random_state
    assert f1.groupby("mo_hinh").size().eq(50).all()
    assert set(f1["lap"]) == set(range(10)) and set(f1["fold"]) == set(range(5))
    pd.testing.assert_frame_equal(f1, f2)                          # kết quả y hệt


def test_xgboost_va_ho_quy_chay_duoc():
    df = du_lieu_gia(); X = M.tao_dac_trung(df); yl, yd = M.tao_nhan(df)
    chia = M.tao_cac_lan_chia(yl, 1)
    f = M.chay_cv(X, yl, {"XGBoost": M.tao_mo_hinh_phan_loai(M._cot_so(X))["XGBoost"]}, chia, "lop")
    assert f["macro_f1"].between(0, 1).all()
    g = M.chay_cv(X, yd, {"Ridge": M.tao_mo_hinh_hoi_quy(M._cot_so(X))["Ridge"]}, chia, "diem")
    assert {"r2", "mae"} <= set(g.columns)


def test_tom_tat_va_so_sanh_ghep():
    f = pd.DataFrame({"mo_hinh": ["A"] * 4 + ["B"] * 4, "lap": [0, 0, 1, 1] * 2, "fold": [0, 1] * 4,
                      "macro_f1": [0.5, 0.6, 0.5, 0.6, 0.3, 0.3, 0.3, 0.3]})
    t = M.tom_tat(f, ["macro_f1"]).set_index("mo_hinh")
    assert t.loc["A", "macro_f1_tb"] == pytest.approx(0.55)
    assert t.loc["B", "macro_f1_ci_thap"] == pytest.approx(0.3)
    s = M.so_sanh_ghep(f, "macro_f1", [("A", "B")]).iloc[0]
    assert s["hieu_tb"] == pytest.approx(0.25) and s["ty_le_fold_A_hon_B"] == 1.0


def test_lobo_bo_qua_dot_it_dong():
    df = du_lieu_gia(100)
    df["dot"] = ["d1"] * 50 + ["d2"] * 44 + ["d3"] * 6
    X = M.tao_dac_trung(df)
    t = M.lobo(df, X, "lop")
    assert "dot" not in X.columns
    assert t.loc[t["dot_thu"] == "d3", "n_thu"].iloc[0] == 6
    assert t.loc[t["dot_thu"] == "d3", "macro_f1"].isna().all()    # đợt ít dòng: chỉ báo số dòng
    assert t.loc[t["dot_thu"] == "d1", "macro_f1"].notna().all()


def test_ablation_bo_nhom_khong_chua_cot_da_bo():
    cau_hinh = M.cau_hinh_ablation()
    assert not set(M.B4) & set(cau_hinh["Bỏ B4"])
    assert not set(M.NHOM_B1367) & set(cau_hinh["Bỏ B1/B3/B6/B7"])
    assert not set(M.NHOM_B2_B5) & set(cau_hinh["Bỏ B2 và B5"])
    assert set(cau_hinh["Chỉ có B4"]) == set(M.B4)
    assert set(cau_hinh["Chỉ thông tin nền"]) == {"lop_so", "A2_nu", "A2_khac", "cap_hoc"}
    assert cau_hinh["Đủ biến"] == M.DAC_TRUNG
    for cot in cau_hinh.values():
        M.kiem_tra_cot_cam(cot)                                    # mọi cấu hình đều qua kiểm tra cột cấm


def test_ablation_chay_duoc_ke_ca_khi_khong_co_cap_hoc():
    df = du_lieu_gia(60)
    yl, _ = M.tao_nhan(df)
    fl, fd = M.chay_ablation(df, M.tao_cac_lan_chia(yl, 1), ("Logistic",))
    assert set(fl["cau_hinh"]) == set(M.cau_hinh_ablation()) == set(fd["cau_hinh"])
    assert fl["macro_f1"].between(0, 1).all()                        # "Chỉ có B4" không có cap_hoc vẫn chạy


def test_chan_doan_dot_tra_ma_tran_3x3():
    df = du_lieu_gia(100)
    df["dot"] = ["d1"] * 30 + ["d2"] * 70
    r = M.chan_doan_dot(df, M.tao_dac_trung(df), "d1", n_hat=3)
    assert r["ma_tran"].shape == (3, 3) and r["ma_tran"].to_numpy().sum() == 30 == r["n_thu"]
