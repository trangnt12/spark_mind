"""Giải thích mô hình bằng SHAP (notebook 04).

SHAP cho biết: với MỖI người, từng biến đã đẩy dự đoán lên hay xuống bao nhiêu so với mức trung bình (giá trị nền).
Đây là mô tả cách MÔ HÌNH dự đoán, KHÔNG phải nguyên nhân thật ngoài đời.

Quy ước:
- Đặc trưng lấy từ modeling.DAC_TRUNG (có kiểm tra cột cấm). Tham số mô hình lấy từ modeling (không viết lại).
- Cấp học (cap_hoc) được one-hot thành 3 cột; khi tính tầm quan trọng thì cộng SHAP 3 cột lại thành 1 biến.
- Hạng 1 = quan trọng nhất.
"""
import json

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.base import clone

from . import config, modeling as M

DUNG_SAI = 1e-4                                   # sai số cho phép khi kiểm tra tính cộng
FILE_NHAN = config.ROOT / "content" / "feature_labels.json"


def doc_nhan() -> dict:
    """Đọc nhãn tiếng Việt của các biến (content/feature_labels.json)."""
    return json.loads(FILE_NHAN.read_text(encoding="utf-8"))


def tien_xu_ly_va_chuyen(X_tr: pd.DataFrame, X_ap: pd.DataFrame):
    """Học tiền xử lý (điền thiếu bằng trung vị, one-hot cấp học) trên X_tr, áp cho X_ap.

    Trả (bộ tiền xử lý đã học, bảng đã đổi có tên cột như 'B4_1', 'cap_hoc_THPT').
    """
    tx = M._tien_xu_ly(M._cot_so(X_tr), chuan_hoa=False).fit(X_tr)
    ten = [t.split("__", 1)[1] for t in tx.get_feature_names_out()]
    return tx, pd.DataFrame(tx.transform(X_ap), columns=ten, index=X_ap.index)


def tao_mo_hinh_chua_hoc(cot_so) -> dict:
    """Bốn mô hình chưa huấn luyện, đúng tham số của notebook 03 (lấy trực tiếp từ modeling)."""
    pl, hq = M.tao_mo_hinh_phan_loai(cot_so), M.tao_mo_hinh_hoi_quy(cot_so)
    return {"xgb_clf": pl["XGBoost"], "rf_clf": pl["Random Forest"],
            "xgb_reg": hq["XGBoost"], "rf_reg": hq["Random Forest"]}


def huan_luyen_cuoi(X: pd.DataFrame, y_lop, y_diem, ten_mh=None) -> dict:
    """Huấn luyện mô hình trên TOÀN BỘ X.

    Trả {'tien_xu_ly', 'X_mh' (bảng đã đổi), 'mo_hinh': {tên: mô hình đã học}}.
    ten_mh: chỉ huấn luyện các mô hình này (mặc định cả bốn).
    """
    M.kiem_tra_cot_cam(X.columns)
    tx, Xm = tien_xu_ly_va_chuyen(X, X)
    mh = {}
    for ten, p in tao_mo_hinh_chua_hoc(M._cot_so(X)).items():
        if ten_mh and ten not in ten_mh:
            continue
        y = y_lop if ten.endswith("clf") else y_diem
        mh[ten] = clone(p.named_steps["mo_hinh"]).fit(Xm, y)   # clone: mô hình mới tinh, cùng tham số
    return {"tien_xu_ly": tx, "X_mh": Xm, "mo_hinh": mh}


def tinh_shap(mo_hinh, Xm: pd.DataFrame):
    """SHAP bằng TreeExplainer. Trả (giá trị SHAP, giá trị nền).

    Phân loại: mảng (người, biến, 3 mức). Hồi quy: mảng (người, biến).
    check_additivity=False vì ta tự kiểm tra tính cộng ở kiem_tra_cong (chặt hơn: 1e-4).
    """
    ex = shap.TreeExplainer(mo_hinh)
    return np.asarray(ex.shap_values(Xm, check_additivity=False)), np.atleast_1d(np.asarray(ex.expected_value, dtype=float))


def dau_ra_mo_hinh(mo_hinh, Xm: pd.DataFrame) -> np.ndarray:
    """Đầu ra mà SHAP giải thích: margin (XGBoost phân loại), xác suất (RF phân loại), giá trị dự đoán (hồi quy)."""
    if isinstance(mo_hinh, xgb.XGBClassifier):
        return mo_hinh.get_booster().predict(xgb.DMatrix(Xm), output_margin=True)
    if hasattr(mo_hinh, "predict_proba"):
        return mo_hinh.predict_proba(Xm)
    return mo_hinh.predict(Xm)[:, None]


def do_lech_cong(mo_hinh, Xm, sv, nen) -> float:
    """Sai số lớn nhất giữa (tổng SHAP + giá trị nền) và đầu ra của mô hình."""
    sv = sv if sv.ndim == 3 else sv[:, :, None]      # hồi quy: thêm trục "mức" độ dài 1
    tong = sv.sum(axis=1) + nen[None, :]             # cộng theo biến, rồi cộng giá trị nền
    return float(np.abs(tong - dau_ra_mo_hinh(mo_hinh, Xm)).max())


def dung_sai_cong(mo_hinh, Xm) -> float:
    """Ngưỡng sai số cho kiểm tra tính cộng.

    Mặc định tuyệt đối 1e-4 (margin và xác suất cỡ 1). Riêng hồi quy điểm 0-100 (~60): XGBoost cộng 300 cây
    bằng float32 nên sai số làm tròn tự nhiên cỡ 1e-4, ta dùng ngưỡng tương đối 1e-5 x |điểm lớn nhất|.
    """
    return max(DUNG_SAI, 1e-5 * float(np.abs(dau_ra_mo_hinh(mo_hinh, Xm)).max()))


def kiem_tra_cong(mo_hinh, Xm, sv, nen, ten="mô hình") -> float:
    """Báo lỗi nếu tổng SHAP + nền lệch đầu ra mô hình từ ngưỡng (dung_sai_cong) trở lên. Trả sai số lớn nhất."""
    lech, nguong = do_lech_cong(mo_hinh, Xm, sv, nen), dung_sai_cong(mo_hinh, Xm)
    if not lech < nguong:
        raise AssertionError(f"SHAP của {ten} không cộng đúng: lệch tối đa {lech:.2e} (cho phép {nguong:.1e})")
    return lech


def doi_chieu_pred_contribs(mo_xgb, Xm, sv, nen, ten="XGBoost") -> float:
    """So SHAP của TreeExplainer với pred_contribs của chính XGBoost (cách server sẽ dùng).

    Báo lỗi nếu lệch từ DUNG_SAI trở lên (cả phần của từng biến lẫn giá trị nền). Trả sai số lớn nhất.
    """
    pc = mo_xgb.get_booster().predict(xgb.DMatrix(Xm), pred_contribs=True)
    if pc.ndim == 2:                                 # hồi quy: (người, biến + 1); cột cuối là giá trị nền
        pc, sv = pc[:, :, None], sv[:, :, None]
    else:                                            # phân loại: XGBoost trả (người, mức, biến + 1) -> đổi về (người, biến + 1, mức)
        pc = pc.transpose(0, 2, 1)
    lech = float(max(np.abs(pc[:, :-1, :] - sv).max(), np.abs(pc[:, -1, :] - nen[None, :]).max()))
    if not lech < DUNG_SAI:
        raise AssertionError(f"pred_contribs của {ten} khác TreeExplainer: lệch tối đa {lech:.2e}")
    return lech


def gop_cap_hoc(sv: np.ndarray, cot: list):
    """Cộng SHAP các cột one-hot 'cap_hoc_*' thành một biến 'cap_hoc'. Trả (SHAP đã gộp, tên biến đã gộp)."""
    nhom = lambda c: "cap_hoc" if c.startswith("cap_hoc_") else c
    ten_moi = list(dict.fromkeys(nhom(c) for c in cot))
    kq = [sv[:, [i for i, c in enumerate(cot) if nhom(c) == t]].sum(axis=1) for t in ten_moi]
    return np.stack(kq, axis=1), ten_moi


def do_quan_trong(sv: np.ndarray, cot: list) -> pd.DataFrame:
    """Trung bình |SHAP| của từng biến.

    Hồi quy: cột 'tb_abs_shap'. Phân loại: thêm cột từng mức (Thap, Trung_binh, Cao) và cột 'gop' (trung bình 3 mức).
    """
    if sv.ndim == 2:
        g, ten = gop_cap_hoc(sv, cot)
        return pd.DataFrame({"bien": ten, "tb_abs_shap": np.abs(g).mean(axis=0)})
    cac = [gop_cap_hoc(sv[:, :, k], cot) for k in range(sv.shape[2])]
    d = pd.DataFrame({"bien": cac[0][1]})
    for k, m in enumerate(M.MUC_THU_TU):
        d[m] = np.abs(cac[k][0]).mean(axis=0)
    d["gop"] = d[M.MUC_THU_TU].mean(axis=1)
    return d


def them_hang(d: pd.DataFrame, cot_diem: str) -> pd.DataFrame:
    """Sắp xếp từ quan trọng nhất và thêm cột 'hang' (1 = quan trọng nhất; hòa thì cùng hạng nhỏ nhất)."""
    d = d.sort_values(cot_diem, ascending=False).reset_index(drop=True)
    d["hang"] = d[cot_diem].rank(ascending=False, method="min").astype(int)
    return d


def hang_theo_bien(d: pd.DataFrame, cot_diem: str, thu_tu: list) -> np.ndarray:
    """Vector hạng (hòa thì lấy hạng trung bình) của các biến theo đúng thứ tự thu_tu, để tính Spearman."""
    return d.set_index("bien").loc[thu_tu, cot_diem].rank(ascending=False).to_numpy()


def hang_trong_fold(X, y_lop, tr, te, ten_mh) -> pd.DataFrame:
    """Huấn luyện trên phần train của một fold, tính |SHAP| (gộp 3 mức) trên phần thử. Trả bảng bien, gop, hang."""
    Xtr, Xte = X.iloc[tr], X.iloc[te]
    tx, Xm_tr = tien_xu_ly_va_chuyen(Xtr, Xtr)
    Xm_te = pd.DataFrame(tx.transform(Xte), columns=Xm_tr.columns, index=Xte.index)
    p = tao_mo_hinh_chua_hoc(M._cot_so(X))[ten_mh]
    m = clone(p.named_steps["mo_hinh"]).fit(Xm_tr, y_lop[tr])
    sv, _ = tinh_shap(m, Xm_te)
    return them_hang(do_quan_trong(sv, list(Xm_te.columns)), "gop")


def shap_theo_fold(X, y_lop, chia, ten_mh="xgb_clf") -> pd.DataFrame:
    """Chạy hang_trong_fold cho mọi fold. Trả bảng dài: fold, bien, gop, hang."""
    kq = []
    for i, (tr, te) in enumerate(chia):
        kq.append(hang_trong_fold(X, y_lop, tr, te, ten_mh).assign(fold=i))
    return pd.concat(kq, ignore_index=True)


def tom_tat_hang(bang_fold: pd.DataFrame) -> pd.DataFrame:
    """Mỗi biến một dòng: |SHAP| trung bình, hạng trung bình, khoảng 2.5–97.5% của hạng, tỉ lệ fold nằm trong top 10."""
    g = bang_fold.groupby("bien")
    t = pd.DataFrame({"tb_abs_shap": g["gop"].mean(), "hang_tb": g["hang"].mean(),
                      "hang_p2_5": g["hang"].quantile(0.025), "hang_p97_5": g["hang"].quantile(0.975),
                      "ty_le_top10": g["hang"].apply(lambda h: float((h <= 10).mean()))})
    return t.sort_values("hang_tb").reset_index()
