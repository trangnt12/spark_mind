"""Kiểm tra mô-đun SHAP (dữ liệu giả nhỏ, không cần MongoDB). Chạy: python -m pytest tests -q"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sparkmind import explain as E, modeling as M  # noqa: E402


def du_lieu_gia(n: int = 90, seed: int = 0) -> pd.DataFrame:
    """Bảng giả đủ cột như bản đã làm sạch; điểm phụ thuộc B4_1 để mô hình có gì đó để học."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.integers(0, 2, n).astype(float) for c in M.DAC_TRUNG})
    for c in ["lop_so", "B2_so", "B5_so", "B1_so", "B3_so", "B6_so"] + [f"B4_{i}" for i in range(1, 8)]:
        df[c] = rng.integers(1, 6, n).astype(float)
    df["cap_hoc"] = rng.choice(["THCS", "THPT", "Đại học"], n)
    df["B7_sao_chep"] = df["B7_sao_chep"].where(df.index != 5)          # một ô thiếu để thử bước điền thiếu
    diem = df["B4_1"] * 15 + rng.normal(0, 8, n)
    muc = np.where(diem < 30, "Thap", np.where(diem < 55, "Trung_binh", "Cao"))
    muc[:3] = M.MUC_THU_TU                                               # đảm bảo đủ 3 mức
    return df.assign(diem_sang_tao=diem, muc=muc)


@pytest.fixture(scope="module")
def tinh():
    """Huấn luyện nhỏ một lần cho cả file test (giảm số cây cho nhanh)."""
    ban = du_lieu_gia()
    X = M.tao_dac_trung(ban); y_lop, y_diem = M.tao_nhan(ban)
    kq = E.huan_luyen_cuoi(X, y_lop, y_diem)
    kq["shap"] = {t: E.tinh_shap(m, kq["X_mh"]) for t, m in kq["mo_hinh"].items()}
    return kq | {"X": X, "y_lop": y_lop}


def test_co_bon_mo_hinh_va_one_hot(tinh):
    assert set(tinh["mo_hinh"]) == {"xgb_clf", "rf_clf", "xgb_reg", "rf_reg"}
    assert not tinh["X_mh"].isna().any().any()                           # đã điền thiếu
    assert {"cap_hoc_THCS", "cap_hoc_THPT", "cap_hoc_Đại học"} <= set(tinh["X_mh"].columns)
    assert "cap_hoc" not in tinh["X_mh"].columns


@pytest.mark.parametrize("ten", ["xgb_clf", "rf_clf", "xgb_reg", "rf_reg"])
def test_shap_cong_dung(tinh, ten):
    sv, nen = tinh["shap"][ten]
    lech = E.kiem_tra_cong(tinh["mo_hinh"][ten], tinh["X_mh"], sv, nen, ten)
    assert lech < 1e-4


def test_kiem_tra_cong_bao_loi_khi_lech(tinh):
    sv, nen = tinh["shap"]["xgb_reg"]
    with pytest.raises(AssertionError, match="không cộng đúng"):
        E.kiem_tra_cong(tinh["mo_hinh"]["xgb_reg"], tinh["X_mh"], sv + 0.01, nen)


@pytest.mark.parametrize("ten", ["xgb_clf", "xgb_reg"])
def test_pred_contribs_khop_tree_explainer(tinh, ten):
    sv, nen = tinh["shap"][ten]
    assert E.doi_chieu_pred_contribs(tinh["mo_hinh"][ten], tinh["X_mh"], sv, nen, ten) < 1e-4


def test_doi_chieu_pred_contribs_bao_loi_khi_lech(tinh):
    sv, nen = tinh["shap"]["xgb_clf"]
    with pytest.raises(AssertionError, match="pred_contribs"):
        E.doi_chieu_pred_contribs(tinh["mo_hinh"]["xgb_clf"], tinh["X_mh"], sv * 1.01, nen)


def test_gop_cap_hoc_giu_tong_shap(tinh):
    sv, _ = tinh["shap"]["xgb_reg"]
    g, ten = E.gop_cap_hoc(sv, list(tinh["X_mh"].columns))
    assert ten.count("cap_hoc") == 1 and len(ten) == len(M.DAC_TRUNG)    # 35 biến sau khi gộp
    assert np.allclose(g.sum(axis=1), sv.sum(axis=1))                    # gộp không làm đổi tổng


def test_quan_trong_va_hang(tinh):
    cot = list(tinh["X_mh"].columns)
    d = E.them_hang(E.do_quan_trong(tinh["shap"]["xgb_clf"][0], cot), "gop")
    assert {"bien", "Thap", "Trung_binh", "Cao", "gop", "hang"} <= set(d.columns)
    assert d["hang"].iloc[0] == 1 and d["gop"].is_monotonic_decreasing
    assert d["bien"].iloc[0] == "B4_1"                                   # dữ liệu giả: B4_1 là biến duy nhất có tác động
    r = E.do_quan_trong(tinh["shap"]["xgb_reg"][0], cot)
    assert list(r.columns) == ["bien", "tb_abs_shap"]


def test_shap_theo_fold_va_tom_tat(tinh):
    chia = M.tao_cac_lan_chia(tinh["y_lop"], n_lap=1, n_fold=3)
    bang = E.shap_theo_fold(tinh["X"], tinh["y_lop"], chia, "xgb_clf")
    assert bang["fold"].nunique() == 3
    t = E.tom_tat_hang(bang)
    assert len(t) == len(M.DAC_TRUNG) and t["bien"].iloc[0] == "B4_1"


def test_khong_cho_cot_cam_vao_huan_luyen(tinh):
    X_xau = tinh["X"].assign(C1=1.0)
    with pytest.raises(ValueError, match="CẤM"):
        E.huan_luyen_cuoi(X_xau, tinh["y_lop"], np.zeros(len(X_xau)))


def test_nhan_tieng_viet_du_cho_moi_bien(tinh):
    nhan = E.doc_nhan()
    thieu = [c for c in tinh["X_mh"].columns if c not in nhan]
    assert not thieu, f"Thiếu nhãn tiếng Việt: {thieu}"


def test_luu_nap_lai_json_giong_mo_hinh_goc(tinh, tmp_path):
    """Lưu XGBoost ra JSON, nạp lại bằng Booster: dự đoán phải giống mô hình gốc; meta ghi đủ thứ tự cột."""
    from sparkmind import model_io as IO
    for ten, kieu in [("xgb_clf", "lop"), ("xgb_reg", "diem")]:
        f = tmp_path / f"{ten}.json"
        IO.luu_xgb(tinh["mo_hinh"][ten], f)
        assert IO.nap_va_kiem_tra(f, kieu, tinh["X_mh"], tinh["mo_hinh"][ten]) < 1e-6
    meta = IO.tao_meta(tinh["tien_xu_ly"], tinh["X_mh"], "du_lieu_gia", 90, {"XGBoost": 0.5})
    assert meta["cot_mo_hinh_theo_thu_tu"] == list(tinh["X_mh"].columns)
    assert set(meta["cap_hoc_cac_gia_tri"]) == {"THCS", "THPT", "Đại học"} and "B4_1" in meta["trung_vi_dien_thieu"]
