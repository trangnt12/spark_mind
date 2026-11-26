"""Làm sạch toàn bộ dữ liệu: đọc survey_form1, ghi kết quả vào survey_clean.

Chạy lại bất cứ lúc nào có thêm form. Không sửa dữ liệu gốc.
Cách dùng:
    python scripts/run_cleaning.py              # MongoDB -> MongoDB
    python scripts/run_cleaning.py --csv        # ghi thêm 3 file CSV vào data/processed
    python scripts/run_cleaning.py --tu-excel   # không cần MongoDB, đọc thẳng Excel (chạy thử)
"""
import argparse

import _boot  # noqa: F401
from sparkmind import config, data_label
from sparkmind.cleaning import bang_loc_form, clean, gan_co_trung_mau, lay_ban
from sparkmind.db import df_sang_docs, ghi_nhieu, lay_db
from sparkmind.loaders import doc_excel, doc_goc_mongo


def ghi_ban_sach(db, sach, gop: bool = True) -> int:
    """Ghi survey_clean, GIỮ data_label hiện có của từng bản ghi (làm sạch lại không làm mất nhãn). Trả số form."""
    docs = data_label.giu_nhan_hien_co(db, config.COL_CLEAN, df_sang_docs(sach))
    return ghi_nhieu(db[config.COL_CLEAN], docs, gop)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", action="store_true", help="ghi thêm CSV vào data/processed")
    p.add_argument("--tu-excel", action="store_true", help="đọc Excel thay vì MongoDB, không ghi Mongo")
    a = p.parse_args()

    db = None
    if a.tu_excel:
        raw = doc_excel()
    else:
        db = lay_db()
        raw = doc_goc_mongo(db)
    print(f"Số form gốc: {len(raw)}")
    sach = gan_co_trung_mau(clean(raw))   # cờ trùng mẫu cần so cả bảng (cả google_form lẫn web)
    print(f"Số form trùng mẫu (cờ trung_mau): {int(sach['trung_mau'].sum())}")

    print(bang_loc_form(sach).to_string(index=False))
    print("\nSố form mỗi đợt:\n" + sach["dot"].value_counts().to_string())

    if db is not None:
        n = ghi_ban_sach(db, sach)
        print(f"\nĐã ghi {n} form vào {config.MONGODB_DB}.{config.COL_CLEAN}")
    if a.csv or a.tu_excel:
        config.PROCESSED.mkdir(parents=True, exist_ok=True)
        for ban in ("chinh", "chat", "rat_chat"):
            lay_ban(sach, ban).to_csv(config.PROCESSED / f"data_{config.FILE_NAME[ban]}.csv", index=False,
                                      encoding="utf-8-sig")
        sach.to_excel(config.PROCESSED / "data_with_flags.xlsx", index=False)
        bang_loc_form(sach).to_csv(config.PROCESSED / "T2_filter_steps.csv", index=False,
                                   encoding="utf-8-sig")
        print(f"Đã ghi CSV vào {config.PROCESSED}")


if __name__ == "__main__":
    main()
