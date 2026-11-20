"""Kiểm tra bộ làm sạch. Chạy: python -m pytest tests -q"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sparkmind import config  # noqa: E402
from sparkmind.cleaning import bang_loc_form, clean, lay_ban  # noqa: E402
from sparkmind.db import df_sang_docs, ghi_nhieu  # noqa: E402
from sparkmind.loaders import doc_excel  # noqa: E402

can_excel = pytest.mark.skipif(not config.RAW_EXCEL.exists(), reason="chưa có data/raw/data_raw.xlsx")


@can_excel
def test_ba_ban_du_lieu():
    s = clean(doc_excel())
    assert len(s) == 460 and s["dung_ai"].sum() == 432
    assert (len(lay_ban(s, "chinh")), len(lay_ban(s, "chat")), len(lay_ban(s, "rat_chat"))) == (361, 297, 231)
    assert s["co_mot_muc_C"].sum() == 133 and s["co_mau_thuan"].sum() == 144
    assert s["dot"].value_counts().to_dict() == {"dot2_16/9": 257, "dot3_4-5/11": 162, "dot1_rai_rac": 41}
    assert bang_loc_form(s)["con_lai"].tolist() == [460, 432, 361, 297, 231]


@can_excel
def test_lam_sach_tung_form_giong_ca_bang():
    """Làm sạch một form riêng lẻ phải cho kết quả y hệt làm sạch cả bảng."""
    raw = doc_excel()
    ca_bang = clean(raw).set_index("_id")
    cols = ["diem_sang_tao", "diem_hanh_vi", "in_chinh", "in_chat", "in_rat_chat", "dot"]
    for i in (0, 100, 300, 459):
        mot = clean(raw.iloc[[i]]).set_index("_id")
        assert mot.loc[:, cols].iloc[0].equals(ca_bang.loc[mot.index[0], cols])


@can_excel
def test_ghi_mongo_khong_nhan_doi():
    import mongomock
    db = mongomock.MongoClient().db
    s = clean(doc_excel())
    for _ in range(2):  # ghi hai lần
        ghi_nhieu(db[config.COL_CLEAN], df_sang_docs(s), gop=False)
    assert db[config.COL_CLEAN].count_documents({}) == 460
    assert db[config.COL_CLEAN].count_documents({"in_chinh": True}) == 361
    doc = db[config.COL_CLEAN].find_one({"in_chinh": True})
    assert doc["diem_sang_tao"] is None or isinstance(doc["diem_sang_tao"], float)


def test_form_moi_tu_web():
    raw = pd.DataFrame([{"thoi_gian": "2026-12-10 09:00", "A1": "Lớp 11", "A2": "Nữ", "A4": "Có, thường xuyên",
                         "B2": "Vài lần/tuần", "B5": "5–15 phút", "B4_1": 4, "B4_2": 5, "B4_3": 2, "B4_4": 4,
                         "B4_5": 3, "B4_6": 2, "B4_7": 5, "C1": 4, "C2": 3, "C3": 4, "C4": 5, "C5": 4,
                         "nguon": "web"}])
    s = clean(raw)
    assert s["dot"].iloc[0] == "web" and bool(s["in_chinh"].iloc[0])
    assert s["diem_sang_tao"].iloc[0] == 75.0


def test_chuan_hoa_ten_truong():
    from sparkmind.school_matching import tao_khoa
    assert tao_khoa("Trường THPT Bắc Bình") == tao_khoa("thpt bắc bình") == ("THPT", "THPT|bac binh")
    assert tao_khoa("Trung học cơ sở Hải ninh")[0] == "THCS"
    assert tao_khoa("THCS và THPT Bắc Bình")[0] == "Liên cấp"
    assert tao_khoa("Đại học Ngoại Thương") == tao_khoa("đại học ngoại thương")
    assert tao_khoa("Nguyễn Hiền")[0] == "Không rõ"
    assert tao_khoa(None) == ("Không rõ", "")


def test_khop_ten_truong_voi_danh_sach():
    from sparkmind.school_matching import chuan_hoa_ds
    ds = chuan_hoa_ds(pd.DataFrame({"a": [1, 2, 3], "b": ["Trường THPT Bắc Bình", "Trường Đại học Kinh tế Quốc dân",
                                                          "Trường THPT Nguyễn Du"],
                                    "c": ["", "NEU", ""], "d": ["Cấp 3", "Đại học", "Cấp 3"]}))
    raw = pd.DataFrame([{"A1": "Lớp 11", "A3": "thpt bắc bình"}, {"A1": "Năm 2 Đại học", "A3": "NEU"},
                        {"A1": "Lớp 10", "A3": "THPT Không Có"}])
    from sparkmind.school_matching import khop_truong, them_cot_truong
    import numpy as np
    d = raw.copy()
    d["lop_so"] = [11, 14, 10]
    d["cap_hoc"] = np.select([d.lop_so <= 9, d.lop_so <= 12], ["THCS", "THPT"], default="Đại học")
    kq = them_cot_truong.__globals__["tao_khoa"]
    d["truong_cap"], d["truong_khoa"] = zip(*d["A3"].map(kq))
    d["truong_chuan"] = ""
    khop_truong(d, ds)
    assert d["truong_khop"].tolist() == ["khop_1", "khop_1", "chua_chuan_hoa"]
    assert d["truong_ds_ten"].iloc[1] == "Trường Đại học Kinh tế Quốc dân"


def test_khop_theo_cap_hoc_tu_lop():
    """Lớp 6 ghi 'THPT Bắc Bình' phải khớp THCS Bắc Bình; lớp 11 ghi 'Bắc Bình' khớp THPT."""
    import numpy as np
    from sparkmind.school_matching import chuan_hoa_ds, khop_truong, tao_khoa
    ds = chuan_hoa_ds(pd.DataFrame({"a": [1, 2], "b": ["Trường THPT Bắc Bình", "Trường THCS Bắc Bình"],
                                    "c": ["", ""], "d": ["Cấp 3", "Cấp 2"]}))
    d = pd.DataFrame({"A3": ["Thpt Bắc Bình", "Bắc Bình"], "lop_so": [6, 11]})
    d["cap_hoc"] = np.select([d.lop_so <= 9, d.lop_so <= 12], ["THCS", "THPT"], default="Đại học")
    d["truong_cap"], d["truong_khoa"] = zip(*d["A3"].map(tao_khoa))
    d["truong_chuan"] = ""
    khop_truong(d, ds)
    assert d["truong_ds_ten"].tolist() == ["Trường THCS Bắc Bình", "Trường THPT Bắc Bình"]
    assert d["truong_mau_thuan_cap"].tolist() == [True, False]
