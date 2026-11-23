"""Tính ngưỡng chia ba "nhỏ / vừa / lớn" cho mức đóng góp của các câu B4, ghi vào models/do_lon.json.

Cách tính: trên 297 người của bản chính (khóa 'chat'), lấy pred_contribs của mô hình XGBoost phân loại đã lưu,
chọn cột của mức được dự đoán cho từng người, lấy giá trị tuyệt đối của 7 câu B4, gộp tất cả (297 x 7 giá trị),
rồi lấy hai phân vị 33.3% và 66.7%. Chạy lại bằng một lệnh:  python scripts/make_contrib_thresholds.py
"""
import json

import _boot  # noqa: F401  (cho phép import sparkmind)
import numpy as np
import xgboost as xgb

from sparkmind import config, explain as E, modeling as M, predict as P
from sparkmind.cleaning import clean, lay_ban
from sparkmind.loaders import doc_excel


def tinh_nguong() -> dict:
    """Trả {'nguong': [t1, t2], ...}. Báo lỗi nếu số dòng khác meta (dữ liệu khác bản đã huấn luyện)."""
    mh = P.nap_mo_hinh()
    ban = lay_ban(clean(doc_excel()), config.BAN_CHINH).reset_index(drop=True)
    assert len(ban) == mh["meta"]["so_dong"], "Số dòng khác meta: không phải bản đã huấn luyện"
    X = M.tao_dac_trung(ban)
    _, Xm = E.tien_xu_ly_va_chuyen(X, X)
    assert list(Xm.columns) == mh["meta"]["cot_mo_hinh_theo_thu_tu"], "Thứ tự cột khác meta"
    dm = xgb.DMatrix(Xm.to_numpy(), feature_names=list(Xm.columns))
    pc = mh["xgb_clf"].predict(dm, pred_contribs=True)           # (người, 3 mức, 37 + 1)
    k = mh["xgb_clf"].predict(dm).argmax(axis=1)                 # mức được dự đoán của từng người
    b4 = [list(Xm.columns).index(c) for c in P.CAU_B4]
    gia_tri = np.abs(pc[np.arange(len(k)), k][:, b4]).ravel()
    t1, t2 = np.percentile(gia_tri, [100 / 3, 200 / 3])
    return {"nguong": [float(t1), float(t2)], "so_dong": int(len(ban)), "so_gia_tri": int(gia_tri.size),
            "cach_tinh": "phân vị 33.3% và 66.7% của |pred_contribs| (mức dự đoán) của 7 câu B4 trên bản 'chat'"}


if __name__ == "__main__":
    kq = tinh_nguong()
    (config.ROOT / "models" / "do_lon.json").write_text(json.dumps(kq, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Đã ghi models/do_lon.json:", kq["nguong"])
