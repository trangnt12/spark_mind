"""Lưu và nạp lại mô hình XGBoost dạng JSON gốc (không dùng pickle/joblib), kèm file mô tả model_meta.json.

Server (/api/predict) chỉ cần: hai file .json của XGBoost + model_meta.json (thứ tự cột, trung vị để điền thiếu,
các cấp học để one-hot). Không cần sklearn pipeline.
"""
import json
from datetime import date

import numpy as np
import pandas as pd
import shap
import sklearn
import xgboost as xgb

from . import modeling as M


def luu_xgb(mo_hinh, duong_dan) -> None:
    """Lưu mô hình XGBoost ở định dạng JSON gốc."""
    mo_hinh.save_model(str(duong_dan))


def tao_meta(tx, Xm: pd.DataFrame, ten_ban: str, n: int, f1_cv: dict) -> dict:
    """Thông tin để server dựng lại đầu vào đúng thứ tự và biết mô hình sinh ra từ đâu."""
    cot_so = list(tx.transformers_[0][2])
    return {"ngay": date.today().isoformat(), "ten_ban_du_lieu": ten_ban, "so_dong": int(n),
            "danh_sach_dac_trung_goc": list(M.DAC_TRUNG), "cot_mo_hinh_theo_thu_tu": list(Xm.columns),
            "trung_vi_dien_thieu": dict(zip(cot_so, map(float, tx.named_transformers_["so"].named_steps["dien"].statistics_))),
            "cap_hoc_cac_gia_tri": [str(c) for c in tx.named_transformers_["chu"].categories_[0]],
            "anh_xa_muc": {str(i): m for i, m in enumerate(M.MUC_THU_TU)},
            "phien_ban": {"xgboost": xgb.__version__, "sklearn": sklearn.__version__, "shap": shap.__version__},
            "macro_f1_cv_5x10": {k: float(v) for k, v in f1_cv.items()},
            "ghi_chu": "Mô hình dự đoán năng lực sáng tạo TỰ NHẬN THỨC. Không lưu Random Forest."}


def luu_meta(meta: dict, duong_dan) -> None:
    """Ghi model_meta.json (UTF-8, giữ dấu tiếng Việt)."""
    duong_dan.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def nap_va_kiem_tra(duong_dan, kieu: str, Xm: pd.DataFrame, mo_goc) -> float:
    """Nạp lại file JSON bằng Booster (cách server làm) rồi dự đoán; so với mô hình gốc. Trả sai số lớn nhất.

    kieu = 'lop' (so xác suất 3 mức) hoặc 'diem' (so điểm dự đoán). Báo lỗi nếu lệch từ 1e-6 trở lên.
    """
    bo = xgb.Booster(); bo.load_model(str(duong_dan))
    moi = bo.predict(xgb.DMatrix(Xm))
    cu = mo_goc.predict_proba(Xm) if kieu == "lop" else mo_goc.predict(Xm)
    lech = float(np.abs(moi - cu).max())
    if not lech < 1e-6:
        raise AssertionError(f"Mô hình nạp lại từ {duong_dan} dự đoán khác bản gốc: lệch {lech:.2e}")
    return lech
