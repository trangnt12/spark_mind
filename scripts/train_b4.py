"""Huấn luyện mô hình B4 (chỉ 7 câu), đo CV 5x10 và lưu vào models/. Chạy:  python scripts/train_b4.py

Ghi: models/xgb_b4_clf.json, models/xgb_b4_reg.json, models/model_b4_meta.json.
Sau đó chạy lại scripts/make_contrib_thresholds.py để cập nhật models/do_lon.json.
"""
import json

import _boot  # noqa: F401  (cho phép import sparkmind)

from sparkmind import config, model_b4 as B, modeling as M
from sparkmind.cleaning import clean, lay_ban
from sparkmind.loaders import doc_excel


def main() -> None:
    ban = lay_ban(clean(doc_excel()), config.BAN_CHINH).reset_index(drop=True)
    X = B.tao_x_b4(ban)
    y_lop, y_diem = M.tao_nhan(ban)
    cv = B.do_cv(X, y_lop, y_diem)                       # đo trước, ghi vào meta
    mh = B.huan_luyen_b4(X, y_lop, y_diem)
    thu_muc = config.ROOT / "models"
    mh["clf"].save_model(str(thu_muc / B.FILE_CLF))
    mh["reg"].save_model(str(thu_muc / B.FILE_REG))
    meta = B.tao_meta_b4("chat (bản chính của báo cáo)", len(ban), cv)
    (thu_muc / B.FILE_META).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"cv": cv, "X/10": meta["dung_khoang_x_tren_10"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
