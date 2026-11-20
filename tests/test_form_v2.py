"""Kiểm tra form v2 (đổi chữ ngày 20/11/2026): chữ cũ và chữ mới phải cho CÙNG một mã."""
import sys
from pathlib import Path

import mongomock
import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from server import main  # noqa: E402
from sparkmind import config  # noqa: E402
from sparkmind.cleaning import clean  # noqa: E402
from sparkmind.columns import ten_ngan  # noqa: E402

BASE = {"thoi_gian": "2026-11-25 10:00:00", "A1": "Lớp 11", "A2": "Nữ", "A3": "THPT X",
        "A4": "Có, thường xuyên", "B1": "ChatGPT", "B2": "Rất hiếm khi", "B3": "Dịch thuật",
        "B4_1": 4, "B4_2": 5, "B4_3": 2, "B4_4": 4, "B4_5": 3, "B4_6": 2, "B4_7": 5,
        "B5": "Dưới 5 phút", "B6": "ví dụ mẫu", "B7": "Sao chép",
        "C1": 4, "C2": 3, "C3": 4, "C4": 5, "C5": 4, "C6": "Chưa từng tham gia."}


def sach(**doi):
    return clean(pd.DataFrame([{**BASE, **doi}])).iloc[0]


# (cột, chữ cũ, chữ mới, cột kết quả, giá trị mong đợi) - mỗi dòng lựa chọn trong nhật ký
LUA_CHON = [
    ("A1", "Năm 1 Đại học", "Sinh viên năm nhất", "lop_so", 13),
    ("A1", "Năm 2 Đại học", "Sinh viên năm hai", "lop_so", 14),
    ("A1", "Năm 3 Đại học", "Sinh viên năm ba", "lop_so", 15),
    ("A1", "Năm 4 Đại học", "Sinh viên năm tư", "lop_so", 16),
    ("A1", "Năm 5 Đại học", "Sinh viên năm 5 trở lên", "lop_so", 17),
    ("A1", "Năm 5 Đại học", "Sinh viên năm 5 trở lên / Khác", "lop_so", 17),
    ("A4", "Đã từng dùng nhưng hiện tại không còn dùng",
     "Đã từng sử dụng nhưng hiện tại không còn sử dụng", "dung_ai", False),
    ("B2", "Vài lần/tuần", "Vài lần mỗi tuần", "B2_so", 3),
    ("B2", "Vài lần/tháng", "Vài lần mỗi tháng", "B2_so", 2),
    ("B5", "5 – 15 phút".replace(" – ", "–"), "Từ 5 đến 15 phút", "B5_so", 2),
    ("B5", "15 – 30 phút".replace(" – ", "–"), "Từ 15 đến 30 phút", "B5_so", 3),
    ("B3", "Giải bài tập / tìm đáp án", "Giải bài tập hoặc tìm đáp án", "B3_bai_tap", 1),
    ("B3", "Giải thích khái niệm khó hiểu", "Giải thích các khái niệm khó hiểu", "B3_khai_niem", 1),
    ("B3", "Viết luận / bài văn", "Viết bài luận hoặc bài văn", "B3_viet_luan", 1),
    ("B3", "Brainstorm ý tưởng (dự án, thuyết trình)", "Lên ý tưởng cho dự án, bài thuyết trình,...",
     "B3_brainstorm", 1),
    ("B3", "Dịch thuật", "Dịch thuật", "B3_dich", 1),
    ("B3", "Trò chuyện giải trí", "Trò chuyện, giải trí", "B3_giai_tri", 1),
    ("B6", 'Gõ ngắn gọn câu hỏi/đề bài (VD: "Giải bài toán này...")',
     'Nhập câu hỏi/đề bài ngắn gọn (ví dụ: "Giải bài toán này...")', "B6_ngan", 1),
    ("B6", "Cung cấp ngữ cảnh/vai trò rõ ràng (VD: ...)", "Cung cấp ngữ cảnh hoặc vai trò cụ thể (ví dụ: ...)",
     "B6_ngu_canh", 1),
    ("B6", "Cung cấp yêu cầu về định dạng (VD: ...)", "Nêu rõ yêu cầu về định dạng (ví dụ: ...)",
     "B6_dinh_dang", 1),
    ("B6", "Đưa ra ví dụ mẫu trước khi hỏi (Few-shot prompting)",
     "Đưa ra ví dụ mẫu trước khi đặt câu hỏi (Few-shot prompting)", "B6_vi_du", 1),
    ("B7", "Sao chép (Copy) nguyên văn để sử dụng ngay", "Sao chép nguyên văn câu trả lời để sử dụng ngay",
     "B7_sao_chep", 1),
    ("B7", "Đọc lướt, lấy ý chính rồi tự viết lại bằng văn phong của mình",
     "Đọc lướt, chọn lọc ý chính rồi tự viết lại bằng văn phong của mình", "B7_viet_lai", 1),
    ("B7", "So sánh thông tin AI đưa ra với các nguồn khác (Google, sách...)",
     "Đối chiếu thông tin AI cung cấp với các nguồn khác (Google, sách,...)", "B7_doi_chieu", 1),
    ("B7", "Tiếp tục gõ các lệnh phụ để bắt AI sửa đổi, mở rộng",
     "Tiếp tục nhập yêu cầu để AI chỉnh sửa hoặc mở rộng câu trả lời", "B7_tiep_tuc", 1),
    ("C6", "Đã từng và có giải thưởng/sản phẩm hoàn chỉnh", "Đã từng tham gia và đạt giải thưởng hoặc hoàn thành sản phẩm.",
     "C6_so", 2),
    ("C6", "Có tham gia/thực hiện nhưng chưa có kết quả nổi bật",
     "Đã tham gia/thực hiện nhưng chưa có kết quả nổi bật.", "C6_so", 1),
    ("C6", "Chưa từng tham gia", "Chưa từng tham gia.", "C6_so", 0),
]


@pytest.mark.parametrize("cot,cu,moi,ket_qua,mong", LUA_CHON)
def test_chu_cu_va_moi_cung_ma(cot, cu, moi, ket_qua, mong):
    a, b = sach(**{cot: cu})[ket_qua], sach(**{cot: moi})[ket_qua]
    assert a == b == mong


def test_chon_nhieu_moi_chi_bat_dung_phuong_an():
    """Chữ mới chỉ bật đúng cột của nó, không bật nhầm cột khác."""
    s = sach(B3="Giải thích các khái niệm khó hiểu, Lên ý tưởng cho dự án, bài thuyết trình,...")
    bat = {c for c in s.index if c.startswith("B3_") and c != "B3_so" and s[c] == 1}
    assert bat == {"B3_khai_niem", "B3_brainstorm"} and s["B3_so"] == 2


def test_khac_giu_nhu_cu():
    assert pd.isna(sach(A1="Khác")["lop_so"]) and sach(A1="Khác")["cap_hoc"] == "Không rõ"


def test_tieu_de_cot_cu_va_moi():
    pre = "Bạn hãy cho biết mức độ đồng ý \n1 = Hoàn toàn không đồng ý  ["
    cu = [ten_ngan(f"C. Vui lòng cho biết {pre}C{i}. Tôi ...]") for i in range(1, 6)]
    moi = [ten_ngan(f"C1. Bạn hãy cho biết {pre}C1.{i}. Tôi ...]") for i in range(1, 6)]
    assert cu == moi == ["C1", "C2", "C3", "C4", "C5"]  # 5 dòng không ghi đè nhau
    assert ten_ngan("C6. Trong 12 tháng qua ...") == ten_ngan("C2. Trong 12 tháng qua ...") == "C6"
    assert ten_ngan(f"B4. Đánh giá {pre}B4.3 Tôi ...]") == ten_ngan(f"B4. Bạn hãy {pre}B4.3 Tôi ...]") == "B4_3"
    assert ten_ngan("A1. Hiện tại, bạn đang học lớp mấy?") == "A1"


FORM_V2 = {**BASE, "A1": "Sinh viên năm hai", "A2": "Khác", "A4": "Có, thỉnh thoảng",
           "B1": "ChatGPT, Gemini", "B2": "Vài lần mỗi tuần",
           "B3": "Giải bài tập hoặc tìm đáp án, Lên ý tưởng cho dự án, bài thuyết trình,...",
           "B5": "Từ 5 đến 15 phút", "B6": "Nhập câu hỏi/đề bài ngắn gọn (ví dụ: ...)",
           "B7": "Đối chiếu thông tin AI cung cấp với các nguồn khác (Google, sách,...)",
           "C6": "Đã tham gia/thực hiện nhưng chưa có kết quả nổi bật."}


def test_ingest_form_chu_moi(monkeypatch):
    db = mongomock.MongoClient().spark_mind
    main.app.dependency_overrides[main.lay_db_dung_chung] = lambda: db
    try:
        monkeypatch.setattr(config, "INGEST_SECRET", "bi-mat")
        r = TestClient(main.app).post("/api/ingest/google-form", json=FORM_V2, headers={"x-api-key": "bi-mat"})
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 200 and r.json()["dot"] == "dot5_form_v2" and r.json()["in_chinh"] is True
    d = db[config.COL_CLEAN].find_one()
    assert (d["lop_so"], d["cap_hoc"], d["B2_so"], d["B5_so"], d["C6_so"]) == (14, "Đại học", 3, 2, 1)
    assert d["B3_brainstorm"] == 1 and d["B6_ngan"] == 1 and d["B7_doi_chieu"] == 1
    assert d["B7_tiep_tuc"] == 0 and d["diem_sang_tao"] == 75.0
    assert db[config.COL_RAW].find_one()["A1"] == "Sinh viên năm hai"  # bản gốc giữ nguyên chữ người dùng


def test_dot_theo_ngay():
    assert sach(thoi_gian="2026-11-19 23:59:00")["dot"] == "dot4_sau_5_11"
    assert sach(thoi_gian="2026-11-20 00:00:00")["dot"] == "dot5_form_v2"
