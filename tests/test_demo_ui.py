"""Kiểm tra giao diện demo và trang kết quả (web/demo.js, web/result.js) bằng cách đọc mã nguồn và nội dung API.

1. Hai file JS không viết cứng chữ tiếng Việt (chữ câu hỏi, chữ kết quả phải đến từ API).
2. Demo không gọi bất kỳ endpoint nghiên cứu nào và không đụng localStorage / session_token.
3. Màn hoàn thành của nghiên cứu gọi /api/research/result bằng header X-Session-Token (không đưa token lên URL).
4. Chữ cần cho giao diện có đủ trong content và qua được các API nội dung.
"""
import json
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(GOC / "src"))
from server import main  # noqa: E402
from tests.test_form_text import chu_viet_cung, chuoi_trong_js  # noqa: E402

CHU_VIET = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", re.I)


def doc(ten: str) -> str:
    return (GOC / "web" / ten).read_text(encoding="utf-8")


def moi_chu_trong_json(x) -> set[str]:
    """Mọi chuỗi giá trị (không tính khóa) trong một file JSON nội dung."""
    if isinstance(x, dict):
        return set().union(*(moi_chu_trong_json(v) for v in x.values()), set())
    if isinstance(x, list):
        return set().union(*(moi_chu_trong_json(v) for v in x), set())
    return {x} if isinstance(x, str) else set()


def test_js_demo_va_ket_qua_khong_viet_cung_chu():
    """Không chuỗi nào có chữ tiếng Việt, không chuỗi nào trùng chữ trong research_ui.json / results_ui.json / form_b.json."""
    chu_content = set()
    for ten in ("research_ui.json", "results_ui.json", "form_b.json"):
        chu_content |= {c for c in moi_chu_trong_json(json.loads((GOC / "content" / ten).read_text(encoding="utf-8"))) if len(c) >= 4}
    loi = []
    for ten in ("demo.js", "result.js"):
        chuoi = chuoi_trong_js(doc(ten))
        loi += [f"{ten}: {c!r}" for c in chuoi if CHU_VIET.search(c) or c in chu_content]
        loi += [f"{ten}: {c!r}" for c in chu_viet_cung(chuoi)]
    assert not loi, "JS viết cứng chữ (phải lấy từ API):\n" + "\n".join(loi)


def test_demo_khong_goi_endpoint_nghien_cuu():
    js = doc("demo.js")
    assert "/api/predict/demo" in js
    for cam in ("/api/research", "X-Session-Token", "session_token", "localStorage", "KHOA_TOKEN", "tt.token"):
        assert cam not in js, f"demo.js không được dùng {cam}"


def test_ket_qua_nghien_cuu_dung_header_khong_dung_query():
    js = doc("result.js")
    assert sum(c == "/api/research/result" for c in chuoi_trong_js(js)) == 1     # chỉ gọi ở một chỗ (bỏ qua chú thích)
    assert '"X-Session-Token"' in js and "?token" not in js and "session_token" not in js
    assert "manHoanThanh" in js and "409" in js            # 409 = chưa xong: hiện thông báo thay vì lỗi


def test_demo_lay_chu_cau_hoi_tu_form_b_va_dung_luoi_co_san():
    js = doc("demo.js")
    assert "tt.fb.phan_b_hanh_vi" in js and "luoi(" in js
    assert 'type: "radio"' not in js                       # không tự dựng lưới mới


def test_trang_nap_demo_va_result_truoc_app():
    html = doc("index.html")
    assert html.index("/play/demo.js") < html.index("/play/app.js") and html.index("/play/result.js") < html.index("/play/app.js")
    assert "bd-len" in html and "bd-xuong" in html


def test_chu_giao_dien_co_du_khoa():
    ui = json.loads((GOC / "content" / "research_ui.json").read_text(encoding="utf-8"))
    kq = json.loads((GOC / "content" / "results_ui.json").read_text(encoding="utf-8"))
    assert ui["chao"]["nut_demo"] == "Chưa có mã? Thử bản demo"
    assert {"tieu_de", "mo_ta", "nut_bat_dau", "nut_xem", "nhan_tien_do"} <= set(ui["demo"])
    assert {"ket_qua", "demo"} <= set(ui["giao_dien"]["emoji"])
    for k in ("nhan_muc", "diem", "xac_suat", "dong_gop", "nut", "chua_xong_giao_dien", "dang_tinh", "loi_giao_dien"):
        assert k in kq, k
    assert kq["diem"]["sai_so"] == 10.5 and "khoảng 10 điểm" in kq["diem"]["ghi_chu"]
    assert "B4.3" in kq["dong_gop"]["canh_bao"] and "B4.6" in kq["dong_gop"]["canh_bao"]
    assert kq["chieu"] == {"tang": "kéo điểm lên", "giam": "kéo điểm xuống"}


def test_api_noi_dung_tra_chu_ket_qua():
    c = TestClient(main.app)
    kq = c.get("/api/content/results-ui")
    assert kq.status_code == 200 and "_ghi_chu" not in kq.text and kq.json()["gioi_han"]["tieu_de"] == "Cần lưu ý"
    b4 = next(x for x in c.get("/api/content/form-b").json()["phan_b_hanh_vi"] if x["id"] == "B4")
    assert [d["id"] for d in b4["cac_dong"]] == [f"B4_{i}" for i in range(1, 8)]
