"""Mô hình CHỈ dùng 7 câu B4 (B4_1..B4_7, số gốc 1–5) cho máy chủ.

Vì sao có file này: trang kết quả chỉ hỏi 7 câu B4, nên mô hình phục vụ cũng phải chỉ nhận đúng 7 câu đó
(mô hình đủ biến cũ vẫn giữ nguyên trong models/xgb_clf.json, xgb_reg.json để dùng cho luận văn).

Quy tắc giống modeling.py: đặc trưng lấy từ danh sách trắng (có kiểm tra cột cấm), cùng tham số XGBoost,
cùng cách chia CV 5 lớp x 10 lần lặp (random_state=42). Không dò tham số.
"""
from datetime import date

import numpy as np
import pandas as pd
import xgboost as xgb

from . import modeling as M
from .columns import B4

FILE_CLF, FILE_REG, FILE_META = "xgb_b4_clf.json", "xgb_b4_reg.json", "model_b4_meta.json"


def tao_x_b4(ban: pd.DataFrame) -> pd.DataFrame:
    """Bảng 7 cột B4 từ bản dữ liệu đã làm sạch. Báo lỗi nếu lọt cột cấm hoặc có ô trống."""
    M.kiem_tra_cot_cam(B4)
    X = M.tao_dac_trung(ban)[B4]
    if X.isna().any().any():
        raise ValueError("B4 có ô trống: mô hình B4 không điền trung vị, cần xử lý trước")
    return X.astype(float)


def mo_hinh_b4() -> dict:
    """Hai mô hình XGBoost chưa học, đúng tham số của modeling (không viết lại tham số ở đây)."""
    pl, hq = M.tao_mo_hinh_phan_loai(B4, cot_chu=[]), M.tao_mo_hinh_hoi_quy(B4, cot_chu=[])
    return {"clf": pl["XGBoost"], "reg": hq["XGBoost"]}


def do_cv(X: pd.DataFrame, y_lop, y_diem) -> dict:
    """CV lặp 5 x 10 cho ĐÚNG mô hình B4. Trả trung bình và độ lệch chuẩn theo 50 fold."""
    chia = M.tao_cac_lan_chia(y_lop)
    mh = mo_hinh_b4()
    pl = M.chay_cv(X, y_lop, {"XGBoost": mh["clf"]}, chia, "lop")
    hq = M.chay_cv(X, y_diem, {"XGBoost": mh["reg"]}, chia, "diem")
    kq = {"so_fold": len(chia)}
    for ten, bang, cot in (("phan_loai", pl, ["macro_f1", "acc", "bal_acc"]), ("hoi_quy", hq, ["r2", "mae"])):
        kq[ten] = {c: {"tb": float(bang[c].mean()), "sd": float(bang[c].std())} for c in cot}
    return kq


def huan_luyen_b4(X: pd.DataFrame, y_lop, y_diem) -> dict:
    """Huấn luyện hai mô hình trên toàn bản chính (không cần tiền xử lý vì B4 đủ và đã là số)."""
    mh = mo_hinh_b4()
    return {"clf": mh["clf"].named_steps["mo_hinh"].fit(X, y_lop),
            "reg": mh["reg"].named_steps["mo_hinh"].fit(X, y_diem)}


def tao_meta_b4(ten_ban: str, n: int, cv: dict) -> dict:
    """File mô tả: thứ tự cột, phiên bản xgboost, số đo CV và số 'X/10' (accuracy CV làm tròn xuống 1 chữ số)."""
    acc = cv["phan_loai"]["acc"]["tb"]
    return {"ngay": date.today().isoformat(), "ten_ban_du_lieu": ten_ban, "so_dong": int(n),
            "cot_mo_hinh_theo_thu_tu": list(B4), "anh_xa_muc": {str(i): m for i, m in enumerate(M.MUC_THU_TU)},
            "phien_ban": {"xgboost": xgb.__version__}, "cv_5x10": cv,
            "dung_khoang_x_tren_10": int(np.floor(acc * 10 + 1e-9)),
            "ghi_chu": "Mô hình CHỈ 7 câu B4, dự đoán năng lực sáng tạo TỰ NHẬN THỨC. "
                       "'dung_khoang_x_tren_10' = accuracy CV làm tròn xuống một chữ số."}
