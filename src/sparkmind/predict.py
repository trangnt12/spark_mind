"""Dự đoán mức tự đánh giá sáng tạo từ câu trả lời B4 (dùng cho demo và kết quả nghiên cứu).

Chỉ cần xgboost + numpy (KHÔNG shap, KHÔNG sklearn, KHÔNG pandas, KHÔNG pickle):
- Mô hình nạp từ file JSON gốc của XGBoost (models/xgb_clf.json, models/xgb_reg.json), nạp một lần rồi giữ lại.
- Vector đầu vào dựng đúng thứ tự cột trong models/model_meta.json. Biến không có trong câu trả lời được điền
  bằng trung vị lưu trong meta (giống bước điền thiếu của pipeline huấn luyện ở modeling.py).
- "Đóng góp" của từng câu lấy từ pred_contribs của XGBoost (khớp TreeSHAP), tính cho đúng mức được dự đoán.
  Kết quả chỉ trả chiều (tăng/giảm) và độ lớn (nhỏ/vừa/lớn), KHÔNG trả số thô.

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
LOP_TOI_DA_THCS, LOP_TOI_DA_THPT = 9, 12            # lớp 6–9 THCS, 10–12 THPT, từ 13 là Đại học (decisions.md)


@lru_cache
def nap_mo_hinh() -> dict:
    """Nạp mô hình và meta MỘT lần (lazy): lần gọi đầu mới đọc file, các lần sau dùng lại bản trong bộ nhớ."""
    meta = json.loads((THU_MUC_MODELS / "model_meta.json").read_text(encoding="utf-8"))
    nguong = json.loads((THU_MUC_MODELS / "do_lon.json").read_text(encoding="utf-8"))["nguong"]
    mo = {}
    for ten in ("xgb_clf", "xgb_reg"):
        mo[ten] = xgb.Booster()
        mo[ten].load_model(str(THU_MUC_MODELS / f"{ten}.json"))
    ban = meta["ten_ban_du_lieu"].split()[0]
    phien_ban = f"{meta['ngay']}-{ban}-n{meta['so_dong']}"
    return {"meta": meta, "nguong": nguong, "phien_ban": phien_ban, **mo}


def _cap_hoc_tu_lop(lop: float) -> str:
    """Cấp học suy ra từ lớp (cùng quy ước với cleaning.py: không dựa vào tên trường)."""
    if lop <= LOP_TOI_DA_THCS:
        return "THCS"
    return "THPT" if lop <= LOP_TOI_DA_THPT else "Đại học"


def dung_vector(tra_loi: dict, meta: dict) -> np.ndarray:
    """Dựng vector 1 x 37 đúng thứ tự cột của meta. Biến thiếu = trung vị; cap_hoc one-hot theo lớp (trung vị)."""
    gia_tri = dict(meta["trung_vi_dien_thieu"])
    gia_tri.update({k: float(v) for k, v in tra_loi.items() if k in gia_tri})
    cap = _cap_hoc_tu_lop(gia_tri["lop_so"])
    for c in meta["cap_hoc_cac_gia_tri"]:
        gia_tri[f"cap_hoc_{c}"] = 1.0 if c == cap else 0.0
    return np.array([[gia_tri[c] for c in meta["cot_mo_hinh_theo_thu_tu"]]], dtype=float)


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

    contrib: đóng góp của 37 biến cho mức được dự đoán. Biến điền trung vị không được liệt kê.
    """
    cot = mh["meta"]["cot_mo_hinh_theo_thu_tu"]
    ds = [(c, float(contrib[cot.index(c)])) for c in CAU_B4 if c in tra_loi]
    ds.sort(key=lambda x: abs(x[1]), reverse=True)
    return [{"id": c, "gia_tri": int(tra_loi[c]), "chieu": "tang" if v >= 0 else "giam",
             "do_lon": _muc_do_lon(abs(v), mh["nguong"])} for c, v in ds[:TOI_DA_DONG_GOP]]


def chay_mo_hinh(tra_loi: dict, mh: dict) -> dict:
    """Chạy hai mô hình trên một người. Trả xác suất thô (3 mức), điểm thô và đóng góp (37 biến) của mức dự đoán."""
    cot = mh["meta"]["cot_mo_hinh_theo_thu_tu"]
    dm = xgb.DMatrix(dung_vector(tra_loi, mh["meta"]), feature_names=cot)
    xs = mh["xgb_clf"].predict(dm)[0]
    pc = mh["xgb_clf"].predict(dm, pred_contribs=True)[0]       # (3 mức, 37 biến + 1 giá trị nền)
    diem = float(mh["xgb_reg"].predict(dm)[0])
    return {"xac_suat": xs, "diem": diem, "contrib": pc[int(np.argmax(xs)), :-1]}


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
