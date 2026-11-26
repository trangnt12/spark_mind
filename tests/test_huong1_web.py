"""Kiểm tra khảo sát hướng 1 trên web (kênh thu thứ hai, đóng mặc định): công tắc, nội dung khớp tài liệu, cột khớp Google Form,
làm sạch như form Google, chống lạm dụng (trường ẩn, giới hạn tốc độ, kích thước, kiểm tra máy chủ), không thu email/tên.
Dùng DB giả (mongomock): KHÔNG ghi gì lên MongoDB thật."""
import importlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(GOC / "src"))
sys.path.insert(0, str(GOC / "scripts"))
from server import huong1_web  # noqa: E402
from sparkmind import admin_stats, config, form1_web, modeling  # noqa: E402
from sparkmind.cleaning import clean, gan_co_trung_mau  # noqa: E402
from sparkmind.columns import RAW_KEYS  # noqa: E402
from sparkmind.ingest import nhan_form  # noqa: E402
from sparkmind.loaders import doc_goc_mongo  # noqa: E402
from tests.test_form_text import doc_khao_sat  # noqa: E402
from tests.test_game2 import client  # noqa: E402,F401
from tests.test_settings import dat_cai_dat  # noqa: E402

SUBMIT, NOI_DUNG = "/api/huong1/submit", "/api/huong1/noi-dung"

# Một bài gửi từ trình duyệt (mã lựa chọn). Chữ tương ứng ở GOOGLE_FORM bên dưới.
BAI = {"consent": True, "guardian_consent": True, "A1": 6, "A2": 2, "A3": "THPT Bắc Bình", "A4": 1,
       "B1": [2, 1], "B2": 2, "B3": [5, 1], "B4_1": 4, "B4_2": 5, "B4_3": 2, "B4_4": 4, "B4_5": 3, "B4_6": 2, "B4_7": 5,
       "B5": 2, "B6": [3, 1], "B7": 2, "C1": 4, "C2": 3, "C3": 4, "C4": 5, "C5": 4, "C6": 3,
       "thoi_gian": {"khoang_ms": {"B4_1": 3000, "C1": 2500}, "sua_cuoi_ms": {}, "an_tab_ms": 0, "tong_ms": 95000}}

# Bản ghi Google Form tương ứng (chữ form v2, đúng như Apps Script gửi: chọn nhiều nối bằng ", ")
GOOGLE_FORM = {"thoi_gian": "2026-12-01 10:00:00", "A1": "Lớp 11", "A2": "Nữ", "A3": "THPT Bắc Bình",
               "A4": "Có, thường xuyên", "B1": "ChatGPT, Gemini", "B2": "Vài lần mỗi tuần",
               "B3": "Giải bài tập hoặc tìm đáp án, Lên ý tưởng cho dự án, bài thuyết trình,...",
               "B4_1": 4, "B4_2": 5, "B4_3": 2, "B4_4": 4, "B4_5": 3, "B4_6": 2, "B4_7": 5, "B5": "Từ 5 đến 15 phút",
               "B6": "Nhập câu hỏi/đề bài ngắn gọn (ví dụ: \"Giải bài toán này...\", \"Viết bài luận về...\"), "
                     "Nêu rõ yêu cầu về định dạng (ví dụ: \"Trả lời dưới dạng bảng\", \"Viết trong 300 từ\")",
               "B7": "Đọc lướt, chọn lọc ý chính rồi tự viết lại bằng văn phong của mình",
               "C1": 4, "C2": 3, "C3": 4, "C4": 5, "C5": 4, "C6": "Chưa từng tham gia."}


@pytest.fixture
def mo(client):
    """Web hướng 1 ĐÃ MỞ (công tắc bật), bộ đếm tốc độ sạch."""
    c, db = client
    dat_cai_dat(db, huong1_web_mo=True)
    huong1_web.gioi_han_nop.xoa()
    yield c, db
    huong1_web.gioi_han_nop.xoa()


def gui(c, **sua):
    return c.post(SUBMIT, json={**BAI, **sua})


def bo_khoa(**bo):
    """BAI nhưng bỏ các khóa trong bo (để thử thiếu câu)."""
    return {k: v for k, v in BAI.items() if k not in bo}


# ---------- Công tắc đóng/mở ----------

def test_mac_dinh_dong_tra_423_va_khong_ghi_gi(client):
    c, db = client
    assert c.get(NOI_DUNG).status_code == 423
    assert c.post(SUBMIT, json=BAI).status_code == 423
    assert db[config.COL_RAW].count_documents({}) == 0 and db[config.COL_CLEAN].count_documents({}) == 0


def test_trang_khung_khong_chua_cau_hoi(client):
    """Công tắc đóng: trang khung vẫn là HTML rỗng chữ (giao diện thấy 423 mà hiện "chưa mở"); câu hỏi không nằm trong HTML."""
    r = client[0].get("/huong-1/khao-sat")
    assert r.status_code == 200 and "Lớp 6" not in r.text and "ChatGPT" not in r.text
    assert "survey1.js" in r.text and "TRANG_RIENG" in r.text


def test_mo_cong_tac_thi_vao_duoc(mo):
    c, _ = mo
    d = c.get(NOI_DUNG).json()
    assert d["gio_khoa_nop_lai"] == 24 and d["ma_chua_tung_dung"] == 4 and d["dong_y"]["o_dong_y"]
    assert gui(c).status_code == 200


def test_dong_lai_thi_chan_lai(mo):
    c, db = mo
    dat_cai_dat(db, huong1_web_mo=False)
    assert gui(c).status_code == 423


def test_cong_tac_hai_huong_doc_lap(client):
    c, db = client
    dat_cai_dat(db, huong2_mo=False, huong1_web_mo=False)
    assert c.get(NOI_DUNG).status_code == 423
    dat_cai_dat(db, huong2_mo=False, huong1_web_mo=True)
    assert c.get(NOI_DUNG).status_code == 200


# ---------- Cột khớp Google Form, làm sạch như Google Form ----------

def tom_tat(doc):
    """Bỏ các trường khác nhau tự nhiên giữa hai bản ghi cùng nội dung."""
    return {k: v for k, v in doc.items() if k not in ("_id", "nguon", "thoi_gian", "thoi_gian_lam_bai")}


def test_cot_va_gia_tri_khop_ban_ghi_google_form(mo):
    c, db = mo
    nhan_form(db, GOOGLE_FORM, "google_form")
    assert gui(c).status_code == 200
    gg = db[config.COL_RAW].find_one({"nguon": "google_form"})
    web = db[config.COL_RAW].find_one({"nguon": "web"})
    assert set(web) - set(gg) == {"thoi_gian_lam_bai"} and set(gg) <= set(web)      # đúng các cột của Google Form, chỉ thêm một trường riêng
    assert set(RAW_KEYS) | {"_id", "nguon"} == set(gg)
    assert tom_tat(web) == tom_tat(gg)                                                # từng giá trị (chữ, số) giống hệt
    assert {k: type(v) for k, v in tom_tat(web).items()} == {k: type(v) for k, v in tom_tat(gg).items()}
    assert isinstance(web["thoi_gian"], datetime) and web["nguon"] == "web"


def test_thoi_gian_lam_bai_luu_rieng(mo):
    c, db = mo
    gui(c)
    t = db[config.COL_RAW].find_one({"nguon": "web"})["thoi_gian_lam_bai"]
    assert t["tong_ms"] == 95000 and t["khoang_ms"] == {"B4_1": 3000, "C1": 2500}
    assert db[config.COL_CLEAN].find_one({"nguon": "web"})["thoi_gian_lam_bai"] == t


def test_khong_co_thoi_gian_thi_khong_co_truong(mo):
    c, db = mo
    assert c.post(SUBMIT, json=bo_khoa(thoi_gian=1)).status_code == 200
    assert "thoi_gian_lam_bai" not in db[config.COL_RAW].find_one({"nguon": "web"})


def test_nhan_that_mac_dinh_va_ban_goc_khong_co_nhan(mo):
    c, db = mo
    gui(c)
    assert "data_label" not in db[config.COL_RAW].find_one()          # dữ liệu gốc không bao giờ có data_label
    assert db[config.COL_CLEAN].find_one()["data_label"] == "that" and db[config.COL_CLEAN].find_one()["dot"] == "web"


def test_duong_thu_gan_nhan_thu_va_khong_ghi_ban_goc(mo):
    """Bài thử chỉ ở bản sạch với nhãn "thu" (dọn được bằng chức năng xóa dữ liệu thử); survey_form1 không bị đụng."""
    c, db = mo
    assert gui(c, thu=True).status_code == 200
    assert db[config.COL_RAW].count_documents({}) == 0
    assert db[config.COL_CLEAN].find_one()["data_label"] == "thu" and db[config.COL_CLEAN].find_one()["nguon"] == "web"


def test_bai_thu_khong_ghi_de_bai_that_trung_ma(mo):
    """Bài thử có nội dung và giây nộp trùng một bài thật thì không được đổi nhãn bài thật thành "thu" (kẻo bị dọn nhầm)."""
    c, db = mo
    goc = form1_web.chuyen_sang_goc({**BAI})      # một bản duy nhất: cùng nội dung và cùng giây nộp
    nhan_form(db, goc, "web", nhan="that")
    nhan_form(db, goc, "web", nhan="thu")
    assert db[config.COL_CLEAN].count_documents({}) == 1 and db[config.COL_CLEAN].find_one()["data_label"] == "that"


def test_ban_goc_chi_them_moi_khong_sua(mo):
    c, db = mo
    doc = form1_web.chuyen_sang_goc({**BAI})
    nhan_form(db, doc, "web", them={"thoi_gian_lam_bai": {"tong_ms": 1}})
    nhan_form(db, doc, "web", them={"thoi_gian_lam_bai": {"tong_ms": 999}})     # cùng nội dung, cùng giây: không ghi đè bản gốc
    assert db[config.COL_RAW].count_documents({}) == 1
    assert db[config.COL_RAW].find_one()["thoi_gian_lam_bai"] == {"tong_ms": 1}


def chay_run_cleaning(db):
    """Làm đúng các bước của scripts/run_cleaning.py (không cần MongoDB thật)."""
    rc = importlib.import_module("run_cleaning")
    sach = gan_co_trung_mau(clean(doc_goc_mongo(db)))
    rc.ghi_ban_sach(db, sach, gop=False)
    return sach


def test_run_cleaning_xu_ly_ban_ghi_web_nhu_google_form(mo):
    c, db = mo
    nhan_form(db, GOOGLE_FORM, "google_form")
    gui(c)
    truoc = {d["nguon"]: d for d in db[config.COL_CLEAN].find()}
    sach = chay_run_cleaning(db)
    sau = {d["nguon"]: d for d in db[config.COL_CLEAN].find()}
    assert len(sach) == 2 and set(sau) == {"google_form", "web"}
    for khoa in ("diem_sang_tao", "diem_hanh_vi", "muc", "dung_ai", "cap_hoc", "lop_so", "B2_so", "B5_so", "C6_so", "in_chinh", "in_chat", "in_rat_chat"):
        assert sau["web"][khoa] == sau["google_form"][khoa], khoa                 # cùng chữ thì cùng kết quả làm sạch
        assert sau["web"][khoa] == truoc["web"][khoa], khoa                       # làm sạch lại cả bảng = làm sạch lúc nộp
    assert sau["web"]["dot"] == "web" and sau["web"]["data_label"] == "that"
    assert sau["web"]["thoi_gian_lam_bai"]["tong_ms"] == 95000


def test_run_cleaning_giu_nhan_thu_cua_ban_sach(mo):
    c, db = mo
    gui(c)
    db[config.COL_CLEAN].update_many({}, {"$set": {"data_label": "thu"}})
    chay_run_cleaning(db)
    assert db[config.COL_CLEAN].find_one()["data_label"] == "thu"


# ---------- Chữ khớp tài liệu (docs/survey_v2.md) ----------

def test_chu_ban_ghi_khop_survey_v2(mo):
    """Mọi đáp án trong survey_v2.md đều ra đúng chữ đó trong bản ghi gốc (so với chính tài liệu, không so với form_b.json)."""
    tai_lieu = {c["nhan"].rstrip("."): c for p in doc_khao_sat()["phan"] for c in p["cau"]}
    nhan_tai_lieu = {"A1": "A1", "A2": "A2", "A4": "A4", "B2": "B2", "B5": "B5", "B7": "B7", "C6": "C2"}   # khóa nội bộ C6 = câu C2 trên form
    dem = 0
    for id_cau, nhan in nhan_tai_lieu.items():
        chu_tl = [t for t, khac in tai_lieu[nhan]["options"] if not khac]
        chu_ra = [form1_web.chu_chon_mot(id_cau, ma) for ma in form1_web.lua_chon()[id_cau]["thu_tu"]]
        assert chu_ra == chu_tl, id_cau
        dem += len(chu_ra)
    for id_cau in ("B1", "B3", "B6"):
        chu_tl = [t for t, khac in tai_lieu[id_cau]["options"] if not khac]
        assert list(form1_web.lua_chon()[id_cau]["chu"].values()) == chu_tl, id_cau
    assert dem > 20


def test_thu_tu_cau_trong_form_giong_tai_lieu():
    """Thứ tự câu A1..C2 và số dòng lưới của survey_v2.md khớp thứ tự trong form_b.json mà trang khảo sát dùng."""
    f = json.loads((GOC / "content" / "form_b.json").read_text(encoding="utf-8"))
    tl = doc_khao_sat()
    assert [c["nhan"].rstrip(".") for c in tl["phan"][0]["cau"]] == [c["id"] for c in f["phan_a_thong_tin"]]
    assert [c["nhan"].rstrip(".") for c in tl["phan"][1]["cau"]] == ["B1", "B2", "B3", "B4", "B5", "B6", "B7"] == [c["id"] for c in f["phan_b_hanh_vi"]]
    assert [d[0] for d in tl["phan"][1]["cau"][3]["dong"]] == [d["nhan"] for d in f["phan_b_hanh_vi"][3]["cac_dong"]]
    assert [d[0].rstrip(".") for d in tl["phan"][2]["cau"][0]["dong"]] == [c["nhan"].rstrip(".") for c in f["phan_c_tu_danh_gia"][:5]]
    assert tl["phan"][2]["cau"][1]["nhan"] == f["phan_c_tu_danh_gia"][5]["nhan"] == "C2."


def test_giao_dien_khong_viet_cung_chu_cau_hoi():
    """Chữ câu hỏi và đáp án của survey_v2.md không được nằm trong file JS/HTML của trang khảo sát hướng 1."""
    ma = "".join((GOC / "web" / f).read_text(encoding="utf-8") for f in ("survey1.js", "survey1_gui.js", "survey1.html"))
    for p in doc_khao_sat()["phan"]:
        for c in p["cau"]:
            for chu in [c["text"]] + [t for t, _ in c["options"]] + [t for _, t in c["dong"]]:
                assert chu not in ma, chu


# ---------- Kiểm tra phía máy chủ ----------

def test_a4_chua_bao_gio_bo_phan_b(mo):
    c, db = mo
    body = {k: v for k, v in BAI.items() if not k.startswith(("B", "thoi_gian"))}
    assert c.post(SUBMIT, json={**body, "A4": 4}).status_code == 200
    doc = db[config.COL_RAW].find_one()
    assert doc["A4"] == "Chưa bao giờ sử dụng" and all(doc[k] is None for k in ("B1", "B2", "B3", "B5", "B6", "B7", "B4_1"))
    assert db[config.COL_CLEAN].find_one()["in_chinh"] is False                       # không dùng AI: không vào ba bản dữ liệu


def test_a4_chua_bao_gio_thi_bo_qua_phan_b_neu_gui_kem(mo):
    c, db = mo
    assert gui(c, A4=4).status_code == 200
    assert db[config.COL_RAW].find_one()["B2"] is None


@pytest.mark.parametrize("khoa", ["A1", "A2", "A3", "A4", "C1", "C5", "C6", "consent"])
def test_thieu_cau_bat_buoc_bi_chan(mo, khoa):
    c, db = mo
    assert c.post(SUBMIT, json=bo_khoa(**{khoa: 1})).status_code == 422
    assert db[config.COL_RAW].count_documents({}) == 0


@pytest.mark.parametrize("khoa", ["B1", "B2", "B3", "B4_1", "B4_7", "B5", "B6", "B7"])
def test_dung_ai_ma_thieu_phan_b_bi_chan(mo, khoa):
    c, _ = mo
    r = c.post(SUBMIT, json=bo_khoa(**{khoa: 1}))
    assert r.status_code == 422 and r.json()["detail"] == "thieu_cau"


@pytest.mark.parametrize("sua", [{"B4_1": 0}, {"B4_1": 6}, {"C3": 9}, {"C1": "x"}, {"A1": 0}, {"B1": []}, {"A3": ""}])
def test_gia_tri_ngoai_khoang_bi_chan(mo, sua):
    assert gui(mo[0], **sua).status_code == 422


@pytest.mark.parametrize("sua", [{"A1": 40}, {"A2": 9}, {"A4": 77}, {"B2": 9}, {"B1": [99]}, {"B6": [1, 40]}, {"C6": 9}])
def test_ma_khong_co_trong_form_bi_chan(mo, sua):
    c, db = mo
    assert gui(c, **sua).status_code == 422 and db[config.COL_RAW].count_documents({}) == 0


def test_thieu_dong_y_va_phu_huynh(mo):
    c, _ = mo
    assert gui(c, consent=False).json()["detail"] == "thieu_dong_y"
    assert gui(c, guardian_consent=False).json()["detail"] == "thieu_nguoi_lon"          # lớp 11: cần xác nhận người lớn
    assert gui(c, A1=9, guardian_consent=False).status_code == 200                         # sinh viên năm hai: không cần


def test_muc_khac_bat_buoc_co_chu_va_duoc_noi_vao(mo):
    c, db = mo
    assert gui(c, B1=[1, 5]).json()["detail"] == "thieu_muc_khac"
    assert gui(c, B1=[1, 5], B1_other="  Deep   Seek ").status_code == 200
    assert db[config.COL_RAW].find_one()["B1"] == "ChatGPT, Deep Seek"                    # chữ người dùng gõ thay cho "Mục khác:"
    gui(c, B1=[1], B1_other="chữ thừa", B2=3)                                                # không chọn "Mục khác": bỏ chữ thừa
    assert not any("chữ thừa" in d["B1"] for d in db[config.COL_RAW].find())


def test_chuoi_dai_va_ky_tu_dieu_khien_bi_chan_hoac_lam_sach(mo):
    c, db = mo
    assert gui(c, A3="x" * 500).status_code == 422
    assert gui(c, A3="Trường\x00A\n\tB").status_code == 200
    assert db[config.COL_RAW].find_one()["A3"] == "Trường A B"


# ---------- Không thu email hay tên ----------

@pytest.mark.parametrize("truong", ["email", "name", "ho_ten", "ten", "phone"])
def test_truong_email_ten_bi_tu_choi(mo, truong):
    c, db = mo
    assert c.post(SUBMIT, json={**BAI, truong: "nguoi@example.com"}).status_code == 422
    assert db[config.COL_RAW].count_documents({}) == 0


def test_ban_ghi_web_khong_luu_email_ten_hay_ip(mo):
    c, db = mo
    gui(c)
    for ten in (config.COL_RAW, config.COL_CLEAN):
        doc = json.dumps(db[ten].find_one(), default=str, ensure_ascii=False).lower()
        assert "@" not in doc and "email" not in doc and "ip" not in {k.lower() for k in db[ten].find_one()}
        assert not any(k in db[ten].find_one() for k in ("email", "name", "ten", "ip", "ip_hash", "user_agent", "consent", "guardian_consent"))


def test_giao_dien_khong_co_o_email_hay_ten():
    ma = "".join((GOC / "web" / f).read_text(encoding="utf-8") for f in ("survey1.js", "survey1_gui.js", "survey1.html"))
    assert 'type: "email"' not in ma and "o-email" not in ma and "email:" not in ma
    nd = (GOC / "content" / "survey1_ui.json").read_text(encoding="utf-8")
    assert "không thu thập email hay họ tên" in nd.lower() and "ẩn danh" not in nd.lower()


def test_chi_cac_cot_cho_phep_trong_mongo(mo):
    c, db = mo
    gui(c)
    assert set(db[config.COL_RAW].find_one()) == set(RAW_KEYS) | {"_id", "nguon", "thoi_gian_lam_bai"}


# ---------- Chống lạm dụng ----------

def test_truong_an_bay_bot_khong_luu_gi(mo):
    c, db = mo
    r = gui(c, ghi_chu_them="http://spam.example")
    assert r.status_code == 200 and r.json() == {"ok": True}                         # bot tưởng thành công
    assert db[config.COL_RAW].count_documents({}) == 0 and db[config.COL_CLEAN].count_documents({}) == 0
    assert gui(c, ghi_chu_them="   ").status_code == 200 and db[config.COL_RAW].count_documents({}) == 1   # chỉ khoảng trắng: coi như trống


def test_gioi_han_toc_do_theo_ip(mo, monkeypatch):
    c, db = mo
    monkeypatch.setattr(huong1_web, "gioi_han_nop", huong1_web.GioiHanTocDo(toi_da=3, giay=600))
    ma = [gui(c, B4_1=1 + i % 5, C1=1 + i % 3).status_code for i in range(5)]
    assert ma == [200, 200, 200, 429, 429]
    r = gui(c)
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0
    assert db[config.COL_RAW].count_documents({}) <= 3


def test_gioi_han_toc_do_tinh_ca_bai_loi_va_theo_tung_ip(mo, monkeypatch):
    c, _ = mo
    monkeypatch.setattr(huong1_web, "gioi_han_nop", huong1_web.GioiHanTocDo(toi_da=2, giay=600))
    assert [gui(c, C1=0).status_code for _ in range(3)] == [422, 422, 429]            # bài lỗi cũng tính lượt
    from fastapi.testclient import TestClient
    from server import main
    khac = TestClient(main.app, client=("9.9.9.9", 50000))
    assert khac.post(SUBMIT, json=BAI).status_code == 200                              # IP khác không bị ảnh hưởng


def test_khong_luu_ip_goc_trong_bo_dem(mo, monkeypatch):
    c, _ = mo
    gui(c)
    khoa = list(huong1_web.gioi_han_nop._lan)
    assert khoa and "1.2.3.4" not in khoa[0] and len(khoa[0]) == 64                  # khóa đếm là băm HMAC, không phải IP thô


def test_gioi_han_kich_thuoc(mo):
    c, db = mo
    to = json.dumps({**BAI, "A3": "x" * (config.HUONG1_BODY_TOI_DA + 10)})
    r = c.post(SUBMIT, content=to, headers={"content-type": "application/json"})
    assert r.status_code == 413 and db[config.COL_RAW].count_documents({}) == 0


def test_so_do_thoi_gian_vo_ly_bi_chan(mo):
    c, _ = mo
    assert gui(c, thoi_gian={"khoang_ms": {"C1": -5}, "tong_ms": 1}).status_code == 422
    assert gui(c, thoi_gian={"tong_ms": config.THOI_GIAN_CAU_TOI_DA_MS + 1}).status_code == 422
    r = gui(c, thoi_gian={"khoang_ms": {"khoa_la": 5, "C2": 100}, "tong_ms": 10})
    assert r.status_code == 200


def test_thieu_khoa_bi_mat_ip_thi_bao_loi_may_chu(mo, monkeypatch):
    monkeypatch.setattr(config, "IP_HASH_SECRET", "")
    assert gui(mo[0]).status_code == 500


# ---------- Nộp lặp: hạn chế đã biết, cờ trung_mau ----------

def test_nop_lap_hai_bai_giong_het_duoc_gan_co_trung_mau(mo):
    """Máy chủ không phát hiện người làm hai lần: hai bài giống hệt đều vào, rồi run_cleaning gắn cờ trung_mau cho cả hai
    (kể cả khi một bài là google_form, một là web). Cờ chỉ gắn, không loại ai khỏi ba bản dữ liệu."""
    c, db = mo
    nhan_form(db, GOOGLE_FORM, "google_form")
    gui(c)
    gui(c, B4_1=1)                                  # bài khác một câu: không trùng
    sach = chay_run_cleaning(db)
    tm = dict(zip(sach["nguon"] + sach["B4_1"].astype(int).astype(str), sach["trung_mau"]))
    assert tm == {"google_form4": True, "web4": True, "web1": False}
    assert sach.loc[sach["trung_mau"], "in_chinh"].all()                              # vẫn nằm trong bản dữ liệu (chỉ gắn cờ)
    assert db[config.COL_CLEAN].count_documents({"trung_mau": True}) == 2


def test_trung_mau_bo_qua_thoi_gian_va_khong_tinh_form_khac_nhau():
    import pandas as pd
    a = {k: 1 for k in RAW_KEYS}
    df = pd.DataFrame([{**a, "thoi_gian": "2026-01-01 10:00:00"}, {**a, "thoi_gian": "2026-01-02 11:00:00"}, {**a, "C1": 2, "thoi_gian": "x"}])
    assert gan_co_trung_mau(df)["trung_mau"].tolist() == [True, True, False]
    assert len(gan_co_trung_mau(df.iloc[0:0])) == 0


# ---------- Tổng quan quản trị và mô hình ----------

def test_tong_quan_hien_so_bai_theo_nguon(mo):
    c, db = mo
    nhan_form(db, GOOGLE_FORM, "google_form")
    gui(c)
    gui(c, B4_1=1)
    gui(c, thu=True, B4_1=3)
    ca_hai = admin_stats.thong_ke_huong1(db, an_thu=False)["theo_nguon"]
    that = admin_stats.thong_ke_huong1(db, an_thu=True)["theo_nguon"]
    assert ca_hai == {"google_form": 1, "web": 3} and that == {"google_form": 1, "web": 2}   # bài thử bị ẩn khi bật "ẩn dữ liệu thử"


def test_cot_cam_cua_mo_hinh():
    for cot in ("thoi_gian_lam_bai", "trung_mau", "nguon"):
        with pytest.raises(ValueError):
            modeling.kiem_tra_cot_cam([cot])


# ---------- Phần trình duyệt (cần node) ----------

NODE = shutil.which("node")


@pytest.mark.skipif(not NODE, reason="không có node")
def test_trinh_duyet_khoa_nop_lai_24_gio_va_bai_gui():
    """Dấu đã nộp (localStorage) khóa 24 giờ, không khóa ở chế độ thử; bài gửi không có trường email/tên và bỏ phần B khi chưa dùng AI."""
    r = subprocess.run([NODE, str(Path(__file__).with_name("survey1_dom_test.js")), str(GOC / "web")], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
