"""Huấn luyện và so sánh mô hình (notebook 03).

Nguyên tắc chống sai sót:
- Đặc trưng chỉ lấy từ danh sách trắng DAC_TRUNG; có hàm kiểm tra báo lỗi nếu lọt cột bị cấm (C1..C5, muc...).
- Mọi bước tiền xử lý (điền thiếu, chuẩn hóa, one-hot) nằm TRONG pipeline sklearn,
  nên mỗi fold chỉ học trên phần train của fold đó (không rò rỉ).
- Cố định random_state. KHÔNG dò tham số: tham số cố định theo quyết định đã chốt.
"""
import platform

import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
                             mean_absolute_error, r2_score)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.base import clone
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier, XGBRegressor

from .columns import B1_KW, B3_KW, B4, B6_KW, B7_KW, CC

RANDOM_STATE = 42
N_FOLD, N_LAP = 5, 10
MUC_THU_TU = ["Thap", "Trung_binh", "Cao"]          # thứ tự mức: 0, 1, 2
MIN_DONG_THU = 15                                    # đợt ít hơn số dòng này thì chỉ báo số dòng

# --- Danh sách đặc trưng (danh sách trắng) ---
COT_PHAN_LOAI = ["cap_hoc"]                          # chữ, one-hot trong pipeline
DAC_TRUNG = (["lop_so", "A2_nu", "A2_khac", "cap_hoc", "B2_so", "B5_so"] + B4
             + [f"B1_{k}" for k in B1_KW] + ["B1_so"]
             + [f"B3_{k}" for k in B3_KW] + ["B3_so"]
             + [f"B6_{k}" for k in B6_KW] + ["B6_so"]
             + [f"B7_{k}" for k in B7_KW])

# --- Cột TUYỆT ĐỐI KHÔNG được làm đầu vào ---
CAM_TEN = set(CC) | {"diem_sang_tao", "muc", "C6", "C6_so", "dot", "nguon", "thoi_gian", "id", "_id"}
# Cờ chống gian lận và mọi trường đo thời gian (hướng 2): chỉ để gắn cờ chất lượng, KHÔNG được làm biến dự đoán (rò rỉ / nhiễu)
CAM_TEN |= {"flags", "flag_count", "thoi_gian_cau", "khoang_ms", "sua_cuoi_ms", "an_tab_ms", "tong_ms", "ty_le_cau_nhanh",
            "lam_qua_nhanh", "mot_dap_an", "bi_gian_doan", "duration_sec", "batch"}
# Game 3 (25/11): số từ, số lần dán, thời gian làm, cờ copy AI... là dữ liệu hành vi khi chơi game, KHÔNG được làm biến dự đoán
# Hướng 1 trên web: thời gian làm bài và cờ trùng mẫu chỉ để gắn cờ chất lượng, KHÔNG được làm biến dự đoán
CAM_TEN |= {"thoi_gian_lam_bai", "trung_mau"}
CAM_TEN |= {"copy_ai_goc", "so_tu", "so_lan_dan", "so_lan_roi_tab", "thoi_gian_lam", "tinh_huong_id", "noi_dung", "nop_luc",
            "paste_count", "tab_leave_count", "answer_length"}
CAM_TIEN_TO = ("in_", "co_", "truong", "ten_truong", "flag", "thoi_gian", "khoang_", "ty_le_cau", "so_tu", "so_lan_")


def kiem_tra_cot_cam(cot, cho_phep=()) -> None:
    """Báo lỗi nếu có cột bị cấm hoặc cột ngoài danh sách trắng.

    cho_phep: cột bổ sung được phép (chỉ dùng cho phân tích bổ sung, ví dụ ('C6_so',)).
    """
    cot = list(cot)
    cam = [c for c in cot if (c in CAM_TEN or c.startswith(CAM_TIEN_TO)) and c not in cho_phep]
    la = [c for c in cot if c not in DAC_TRUNG and c not in cho_phep and c not in cam]
    if cam:
        raise ValueError(f"Cột BỊ CẤM trong bảng đặc trưng: {cam}")
    if la:
        raise ValueError(f"Cột ngoài danh sách đặc trưng đã chốt: {la}")


def tao_dac_trung(ban: pd.DataFrame, cho_phep=()) -> pd.DataFrame:
    """Lấy bảng đặc trưng X từ bản dữ liệu đã làm sạch (kèm kiểm tra cột cấm)."""
    cot = DAC_TRUNG + list(cho_phep)
    kiem_tra_cot_cam(cot, cho_phep)
    return ban[cot].reset_index(drop=True)


def tao_nhan(ban: pd.DataFrame):
    """Trả (y_lop 0/1/2, y_diem). Mức: Thap=0, Trung_binh=1, Cao=2."""
    y_lop = ban["muc"].map({m: i for i, m in enumerate(MUC_THU_TU)}).to_numpy()
    return y_lop, ban["diem_sang_tao"].to_numpy(dtype=float)


def _tien_xu_ly(cot_so, chuan_hoa: bool, cot_chu=COT_PHAN_LOAI) -> ColumnTransformer:
    """Điền thiếu (trung vị), chuẩn hóa (nếu cần) cho cột số; one-hot cho cột chữ. Học trên train."""
    buoc = [("dien", SimpleImputer(strategy="median"))]
    if chuan_hoa:
        buoc.append(("chuan", StandardScaler()))
    return ColumnTransformer([
        ("so", Pipeline(buoc), list(cot_so)),
        ("chu", OneHotEncoder(handle_unknown="ignore", sparse_output=False), list(cot_chu))])


class XGBCanBangLop(XGBClassifier):
    """XGBoost phân loại, trọng số mẫu cân bằng lớp tính TRONG fit (chỉ từ nhãn của phần train)."""

    def fit(self, X, y, **kw):
        return super().fit(X, y, sample_weight=compute_sample_weight("balanced", y), **kw)


def _pipe(cot_so, mo_hinh, chuan_hoa=False, cot_chu=COT_PHAN_LOAI) -> Pipeline:
    return Pipeline([("tien_xu_ly", _tien_xu_ly(cot_so, chuan_hoa, cot_chu)), ("mo_hinh", mo_hinh)])


def tao_mo_hinh_phan_loai(cot_so, cot_chu=COT_PHAN_LOAI) -> dict:
    """5 mô hình phân loại, tham số cố định (không dò)."""
    rs = RANDOM_STATE
    xgb = XGBCanBangLop(max_depth=3, learning_rate=0.05, n_estimators=300, subsample=0.8,
                        colsample_bytree=0.8, random_state=rs, n_jobs=1, eval_metric="mlogloss")
    rf = RandomForestClassifier(n_estimators=500, min_samples_leaf=3,
                                class_weight="balanced_subsample", random_state=rs, n_jobs=-1)
    lr = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=rs)
    return {"Dummy phổ biến nhất": _pipe(cot_so, DummyClassifier(strategy="most_frequent"), cot_chu=cot_chu),
            "Dummy theo tỉ lệ": _pipe(cot_so, DummyClassifier(strategy="stratified", random_state=rs), cot_chu=cot_chu),
            "Logistic": _pipe(cot_so, lr, chuan_hoa=True, cot_chu=cot_chu),
            "Random Forest": _pipe(cot_so, rf, cot_chu=cot_chu),
            "XGBoost": _pipe(cot_so, xgb, cot_chu=cot_chu)}


def tao_mo_hinh_hoi_quy(cot_so, cot_chu=COT_PHAN_LOAI) -> dict:
    """4 mô hình hồi quy (phụ), cùng tinh thần, không dò tham số."""
    rs = RANDOM_STATE
    xgb = XGBRegressor(max_depth=3, learning_rate=0.05, n_estimators=300, subsample=0.8,
                       colsample_bytree=0.8, random_state=rs, n_jobs=1)
    rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=3, random_state=rs, n_jobs=-1)
    return {"Dummy trung bình": _pipe(cot_so, DummyRegressor(strategy="mean"), cot_chu=cot_chu),
            "Ridge": _pipe(cot_so, Ridge(alpha=1.0), chuan_hoa=True, cot_chu=cot_chu),
            "Random Forest": _pipe(cot_so, rf, cot_chu=cot_chu),
            "XGBoost": _pipe(cot_so, xgb, cot_chu=cot_chu)}


def _cot_so(X: pd.DataFrame) -> list:
    return [c for c in X.columns if c not in COT_PHAN_LOAI]


def do_phan_loai(y, du_doan) -> dict:
    return {"macro_f1": f1_score(y, du_doan, average="macro"),
            "bal_acc": balanced_accuracy_score(y, du_doan), "acc": accuracy_score(y, du_doan)}


def do_hoi_quy(y, du_doan) -> dict:
    return {"r2": r2_score(y, du_doan), "mae": mean_absolute_error(y, du_doan)}


def tao_cac_lan_chia(y_lop, n_lap: int = N_LAP, n_fold: int = N_FOLD, seed: int = RANDOM_STATE) -> list:
    """Danh sách (chỉ số train, chỉ số test) của 5 lớp x 10 lần lặp, chia phân tầng theo mức.

    Dùng CHUNG một danh sách cho mọi mô hình để so sánh ghép cặp theo từng fold.
    """
    rskf = RepeatedStratifiedKFold(n_splits=n_fold, n_repeats=n_lap, random_state=seed)
    return list(rskf.split(np.zeros(len(y_lop)), y_lop))


def chay_cv(X, y, mo_hinh: dict, chia: list, kieu: str, cho_phep=(), n_fold: int = N_FOLD) -> pd.DataFrame:
    """Chạy CV lặp, trả bảng từng fold: mo_hinh, lap, fold, và các chỉ số. kieu = 'lop' hoặc 'diem'."""
    kiem_tra_cot_cam(X.columns, cho_phep)
    do = do_phan_loai if kieu == "lop" else do_hoi_quy
    dong = []
    for i, (tr, te) in enumerate(chia):
        for ten, mh in mo_hinh.items():
            m = clone(mh).fit(X.iloc[tr], y[tr])      # tiền xử lý học trên train của fold này
            dong.append({"mo_hinh": ten, "lap": i // n_fold, "fold": i % n_fold,
                         **do(y[te], m.predict(X.iloc[te]))})
    return pd.DataFrame(dong)


def khoang_tin_cay(v, n_boot: int = 2000, seed: int = RANDOM_STATE):
    """Khoảng tin cậy 95% của trung bình, bootstrap trên các giá trị theo fold (percentile 2.5 và 97.5).

    Lưu ý: các fold lặp dùng lại cùng dữ liệu nên không độc lập hoàn toàn -> khoảng này chỉ để THAM KHẢO.
    """
    v = np.asarray(v, dtype=float)
    idx = np.random.default_rng(seed).integers(0, len(v), size=(n_boot, len(v)))
    return tuple(np.percentile(v[idx].mean(axis=1), [2.5, 97.5]))


def tom_tat(folds: pd.DataFrame, chi_so) -> pd.DataFrame:
    """Mỗi mô hình một dòng: trung bình, độ lệch chuẩn, khoảng 95% (bootstrap) cho từng chỉ số."""
    dong = []
    for ten, g in folds.groupby("mo_hinh", sort=False):
        d = {"mo_hinh": ten, "so_fold": len(g)}
        for c in chi_so:
            lo, hi = khoang_tin_cay(g[c])
            d.update({f"{c}_tb": g[c].mean(), f"{c}_sd": g[c].std(), f"{c}_ci_thap": lo, f"{c}_ci_cao": hi})
        dong.append(d)
    return pd.DataFrame(dong)


def so_sanh_ghep(folds: pd.DataFrame, chi_so: str, cap: list) -> pd.DataFrame:
    """Hiệu chỉ số (A trừ B) theo từng fold ghép cặp. cap = [(A, B), ...].

    Có khoảng 95% bootstrap (tham khảo, vì fold không độc lập hoàn toàn) và tỉ lệ fold mà A hơn B.
    """
    rong = folds.pivot_table(index=["lap", "fold"], columns="mo_hinh", values=chi_so)
    dong = []
    for a, b in cap:
        hieu = (rong[a] - rong[b]).to_numpy()
        lo, hi = khoang_tin_cay(hieu)
        dong.append({"so_sanh": f"{a} - {b}", "chi_so": chi_so, "hieu_tb": hieu.mean(),
                     "ci_thap": lo, "ci_cao": hi, "ty_le_fold_A_hon_B": float((hieu > 0).mean()),
                     "ci_chua_0": not (lo <= 0 <= hi)})
    return pd.DataFrame(dong)


def phan_bo_muc(cac_ban: dict) -> pd.DataFrame:
    """Phân bố 3 mức của từng bản dữ liệu: {tên bản: DataFrame} -> bảng số người và %."""
    dong = []
    for ten, b in cac_ban.items():
        dem = b["muc"].value_counts().reindex(MUC_THU_TU).fillna(0).astype(int)
        for m in MUC_THU_TU:
            dong.append({"ban": ten, "muc": m, "n": int(dem[m]), "ty_le_%": round(100 * dem[m] / len(b), 1)})
    return pd.DataFrame(dong)


def danh_gia_tach(X_tr, y_tr, X_te, y_te, mo_hinh: dict, kieu: str) -> pd.DataFrame:
    """Huấn luyện trên train, thử trên test (một lần), trả chỉ số từng mô hình."""
    do = do_phan_loai if kieu == "lop" else do_hoi_quy
    dong = []
    for ten, mh in mo_hinh.items():
        m = clone(mh).fit(X_tr, y_tr)
        dong.append({"mo_hinh": ten, **do(y_te, m.predict(X_te))})
    return pd.DataFrame(dong)


def lobo(ban: pd.DataFrame, X: pd.DataFrame, kieu: str) -> pd.DataFrame:
    """Leave-one-batch-out: lần lượt giữ MỘT đợt làm tập thử. Cột 'dot' chỉ dùng chia nhóm, không là đặc trưng.

    Đợt ít hơn MIN_DONG_THU dòng: chỉ ghi n_test, không tính chỉ số.
    """
    y_lop, y_diem = tao_nhan(ban)
    y = y_lop if kieu == "lop" else y_diem
    ct = tao_mo_hinh_phan_loai(_cot_so(X)) if kieu == "lop" else tao_mo_hinh_hoi_quy(_cot_so(X))
    dot = ban["dot"].to_numpy()
    kq = []
    for d in pd.unique(dot):
        te = dot == d
        if te.sum() < MIN_DONG_THU:
            kq.append(pd.DataFrame({"mo_hinh": ["(bỏ qua: ít dòng)"]}).assign(dot_thu=d, n_thu=int(te.sum()), n_train=int((~te).sum())))
            continue
        r = danh_gia_tach(X[~te], y[~te], X[te], y[te], ct, kieu)
        kq.append(r.assign(dot_thu=d, n_thu=int(te.sum()), n_train=int((~te).sum())))
    t = pd.concat(kq, ignore_index=True)
    return t[["dot_thu", "n_thu", "n_train", "mo_hinh"] + [c for c in t.columns if c not in ("dot_thu", "n_thu", "n_train", "mo_hinh")]]


def thu_doc_lap(ban: pd.DataFrame, X: pd.DataFrame, dot_train: list, dot_thu: list) -> pd.DataFrame:
    """Huấn luyện trên các đợt dot_train, thử riêng trên từng đợt trong dot_thu (đợt không có hoặc ít dòng thì báo n)."""
    y_lop, _ = tao_nhan(ban)
    tr = ban["dot"].isin(dot_train).to_numpy()
    ct = tao_mo_hinh_phan_loai(_cot_so(X))
    kq = []
    for d in dot_thu:
        te = (ban["dot"] == d).to_numpy()
        if te.sum() < MIN_DONG_THU:
            kq.append(pd.DataFrame({"mo_hinh": ["(không đủ dòng)"]}).assign(dot_thu=d, n_thu=int(te.sum()), n_train=int(tr.sum())))
            continue
        r = danh_gia_tach(X[tr], y_lop[tr], X[te], y_lop[te], ct, "lop")
        kq.append(r.assign(dot_thu=d, n_thu=int(te.sum()), n_train=int(tr.sum())))
    return pd.concat(kq, ignore_index=True)


def phien_ban_thu_vien() -> pd.DataFrame:
    """Ghi lại phiên bản thư viện để tái lập."""
    return pd.DataFrame({"thu_vien": ["python", "numpy", "pandas", "scikit-learn", "xgboost", "random_state"],
                         "phien_ban": [platform.python_version(), np.__version__, pd.__version__,
                                       sklearn.__version__, xgboost.__version__, RANDOM_STATE]})


# --- G2: bỏ từng nhóm biến (ablation) ---
NHOM_NEN = ["lop_so", "A2_nu", "A2_khac", "cap_hoc"]            # thông tin nền: lớp, giới, cấp học
NHOM_B2_B5 = ["B2_so", "B5_so"]
NHOM_B1367 = [c for c in DAC_TRUNG if c.startswith(("B1_", "B3_", "B6_", "B7_"))]


def cau_hinh_ablation() -> dict:
    """Tên cấu hình -> danh sách cột đặc trưng. Cấu hình 'bỏ nhóm' không chứa cột của nhóm đã bỏ."""
    bo = lambda nhom: [c for c in DAC_TRUNG if c not in nhom]
    return {"Đủ biến": list(DAC_TRUNG), "Bỏ B4": bo(B4), "Chỉ có B4": list(B4),
            "Bỏ B1/B3/B6/B7": bo(NHOM_B1367), "Chỉ thông tin nền": list(NHOM_NEN),
            "Bỏ B2 và B5": bo(NHOM_B2_B5)}


def chay_ablation(ban: pd.DataFrame, chia: list, ten_mo_hinh=("Logistic", "Random Forest", "XGBoost")):
    """Chạy CV (cùng các lần chia) cho từng cấu hình. Trả (bảng fold phân loại, bảng fold hồi quy) có cột 'cau_hinh'."""
    y_lop, y_diem = tao_nhan(ban)
    lop, diem = [], []
    for ten, cot in cau_hinh_ablation().items():
        X = tao_dac_trung(ban)[cot]                              # tao_dac_trung đã kiểm tra cột cấm; chay_cv kiểm lại
        chu = [c for c in COT_PHAN_LOAI if c in cot]
        pl = {k: v for k, v in tao_mo_hinh_phan_loai(_cot_so(X), chu).items() if k in ten_mo_hinh}
        hq = {k: v for k, v in tao_mo_hinh_hoi_quy(_cot_so(X), chu).items() if k in ("Ridge", "Random Forest", "XGBoost")}
        lop.append(chay_cv(X, y_lop, pl, chia, "lop").assign(cau_hinh=ten))
        diem.append(chay_cv(X, y_diem, hq, chia, "diem").assign(cau_hinh=ten))
    return pd.concat(lop, ignore_index=True), pd.concat(diem, ignore_index=True)


# --- G3: chẩn đoán một đợt nhỏ (dot1) ---
def chan_doan_dot(ban: pd.DataFrame, X: pd.DataFrame, dot_giu: str, n_hat: int = 200) -> dict:
    """Giữ lại một đợt làm tập thử (như LOBO). Trả: phân bố mức, ma trận nhầm lẫn RF, macro-F1 các mô hình,
    macro-F1 dummy theo tỉ lệ (lần chạy trong LOBO và trung bình n_hat hạt giống khác nhau)."""
    from sklearn.metrics import confusion_matrix
    y, _ = tao_nhan(ban); te = (ban["dot"] == dot_giu).to_numpy()
    ct = tao_mo_hinh_phan_loai(_cot_so(X))
    rf = clone(ct["Random Forest"]).fit(X[~te], y[~te])
    mt = pd.DataFrame(confusion_matrix(y[te], rf.predict(X[te]), labels=[0, 1, 2]),
                      index=[f"that_{m}" for m in MUC_THU_TU], columns=[f"doan_{m}" for m in MUC_THU_TU])
    f1 = lambda m: f1_score(y[te], m.predict(X[te]), average="macro")
    dummy = [f1(clone(ct["Dummy theo tỉ lệ"]).set_params(mo_hinh__random_state=s).fit(X[~te], y[~te]))
             for s in range(n_hat)]
    return {"nhan_thu": y[te], "ma_tran": mt, "dummy_lan_lobo": f1(clone(ct["Dummy theo tỉ lệ"]).fit(X[~te], y[~te])),
            "dummy_tb": float(np.mean(dummy)), "dummy_sd": float(np.std(dummy)),
            "f1_rf": f1(rf), "n_thu": int(te.sum())}
