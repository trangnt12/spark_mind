"""Dự đoán mức tự đánh giá sáng tạo từ 7 câu B4 (dùng cho demo và kết quả nghiên cứu).

Chỉ cần xgboost + numpy (KHÔNG shap, KHÔNG sklearn, KHÔNG pandas, KHÔNG pickle):
- Dùng mô hình CHỈ 7 câu B4 (models/xgb_b4_clf.json, xgb_b4_reg.json, model_b4_meta.json; xem model_b4.py),
  nạp từ JSON gốc của XGBoost, nạp một lần rồi giữ lại. Không điền trung vị vì mô hình chỉ có đúng 7 cột.
- Mức và xác suất lấy từ mô hình phân loại; điểm và "đóng góp" lấy từ mô hình hồi quy.
- "Đóng góp" của từng câu lấy từ pred_contribs của mô hình hồi quy (khớp TreeSHAP): dương = kéo điểm dự đoán lên
  ("tang"), âm = kéo xuống ("giam"). Kết quả chỉ trả chiều và độ lớn (nhỏ/vừa/lớn), KHÔNG trả số thô.

Đây là mô tả cách mô hình ước lượng, không phải nguyên nhân và không phải đánh giá năng lực thật.
"""
import json
from functools import lru_cache

import numpy as np
import xgboost as xgb

from . import config

THU_MUC = ["Thap", "Trung_binh", "Cao"]            # thứ tự mức: 0, 1, 2 (khớp modeling.MUC_THU_TU)
CAU_B4 = [f"B4_{i}" for i in range(1, 8)]
TOI_DA_DONG_GOP = 4
THU_MUC_MODELS = config.ROOT / "models"


@lru_cache
def nap_mo_hinh() -> dict:
    """Nạp mô hình và meta MỘT lần (lazy): lần gọi đầu mới đọc file, các lần sau dùng lại bản trong bộ nhớ."""
    meta = json.loads((THU_MUC_MODELS / "model_b4_meta.json").read_text(encoding="utf-8"))
    nguong = json.loads((THU_MUC_MODELS / "do_lon.json").read_text(encoding="utf-8"))["nguong"]
    mo = {}
    for ten in ("xgb_clf", "xgb_reg"):
        mo[ten] = xgb.Booster()
        mo[ten].load_model(str(THU_MUC_MODELS / f"{ten.replace('xgb_', 'xgb_b4_')}.json"))
    ban = meta["ten_ban_du_lieu"].split()[0]
    phien_ban = f"{meta['ngay']}-b4-{ban}-n{meta['so_dong']}"
    return {"meta": meta, "nguong": nguong, "phien_ban": phien_ban, **mo}


def dung_vector(tra_loi: dict, meta: dict) -> np.ndarray:
    """Dựng vector 1 x 7 đúng thứ tự cột của meta. Câu chưa trả lời = NaN (XGBoost tự xử lý; API demo luôn gửi đủ 7)."""
    return np.array([[float(tra_loi.get(c, np.nan)) for c in meta["cot_mo_hinh_theo_thu_tu"]]], dtype=float)


def _kiem_tra_tra_loi(tra_loi: dict) -> None:
    """Báo ValueError nếu có câu B4 không phải số nguyên 1–5 (kiểm tra lần hai, ngoài lớp API)."""
    for k, v in tra_loi.items():
        if k not in CAU_B4 or isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 5:
            raise ValueError(f"Câu trả lời không hợp lệ: {k}")


def _xac_suat_tong_1(p: np.ndarray) -> list:
    """Làm tròn 4 số lẻ nhưng bảo đảm tổng đúng bằng 1 (phần dư dồn vào mức lớn nhất)."""
    kq = [round(float(x), 4) for x in p]
    lon = int(np.argmax(p))
    kq[lon] = round(1.0 - sum(x for i, x in enumerate(kq) if i != lon), 4)
    return kq


def _muc_do_lon(gia_tri_tuyet_doi: float, nguong: list) -> str:
    """Chia ba theo ngưỡng phân vị lấy từ dữ liệu huấn luyện (models/do_lon.json)."""
    if gia_tri_tuyet_doi < nguong[0]:
        return "nho"
    return "vua" if gia_tri_tuyet_doi < nguong[1] else "lon"


def tinh_dong_gop(contrib: np.ndarray, tra_loi: dict, mh: dict) -> list:
    """Tối đa 4 câu B4 người dùng THỰC SỰ trả lời, ảnh hưởng nhiều nhất (theo |đóng góp|).

    contrib: đóng góp của 7 câu B4 vào ĐIỂM DỰ ĐOÁN của mô hình hồi quy (đơn vị điểm 0-100).
    chieu = "tang": câu này kéo điểm dự đoán lên; "giam": kéo điểm dự đoán xuống (so với điểm trung bình nền).
    """
    cot = mh["meta"]["cot_mo_hinh_theo_thu_tu"]
    ds = [(c, float(contrib[cot.index(c)])) for c in CAU_B4 if c in tra_loi]
    ds.sort(key=lambda x: abs(x[1]), reverse=True)
    return [{"id": c, "gia_tri": int(tra_loi[c]), "chieu": "tang" if v >= 0 else "giam",
             "do_lon": _muc_do_lon(abs(v), mh["nguong"])} for c, v in ds[:TOI_DA_DONG_GOP]]


def chay_mo_hinh(tra_loi: dict, mh: dict) -> dict:
    """Chạy hai mô hình trên một người. Trả xác suất thô (3 mức, từ phân loại), điểm thô và đóng góp (7 câu, từ hồi quy)."""
    cot = mh["meta"]["cot_mo_hinh_theo_thu_tu"]
    dm = xgb.DMatrix(dung_vector(tra_loi, mh["meta"]), feature_names=cot)
    pc = mh["xgb_reg"].predict(dm, pred_contribs=True)[0]       # (7 câu + 1 giá trị nền)
    return {"xac_suat": mh["xgb_clf"].predict(dm)[0], "diem": float(mh["xgb_reg"].predict(dm)[0]),
            "contrib": pc[:-1]}


def du_doan(tra_loi: dict) -> dict:
    """Dự đoán từ các câu B4 (khóa 'B4_1'..'B4_7', số nguyên 1–5; được phép thiếu, thiếu thì dùng trung vị)."""
    _kiem_tra_tra_loi(tra_loi)
    mh = nap_mo_hinh()
    r = chay_mo_hinh(tra_loi, mh)
    return {"muc": THU_MUC[int(np.argmax(r["xac_suat"]))],
            "xac_suat": dict(zip(THU_MUC, _xac_suat_tong_1(r["xac_suat"]))),
            "diem_du_doan": round(min(100.0, max(0.0, r["diem"])), 1),
            "dong_gop": tinh_dong_gop(r["contrib"], tra_loi, mh),
            "model_version": mh["phien_ban"]}
