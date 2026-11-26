"""Kiểm tra trang chủ "/", popup chọn hướng và trang "/huong-1" (web/landing*.js, huong1.js, content/landing_ui.json).
Dùng DB giả (mongomock). Phần JS được kiểm bằng cách đọc mã nguồn và (nếu có node) chạy thử trên DOM giả."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sparkmind import config, settings_store  # noqa: E402
from tests.test_game2 import client  # noqa: E402,F401
from tests.test_research import BAT_DAU  # noqa: E402
from tests.test_settings import dat_cai_dat  # noqa: E402

WEB = config.ROOT / "web"
ND = json.loads((config.ROOT / "content" / "landing_ui.json").read_text(encoding="utf-8"))
UI = json.loads((config.ROOT / "content" / "research_ui.json").read_text(encoding="utf-8"))
CHU_VIET = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", re.I)
JS_TRANG_CHU = ["landing_chung.js", "landing_popup.js", "landing_khoi.js", "landing.js", "landing_hieuung.js"]
EMAIL = "nguyenthitrang.ttd@gmail.com"


def doc(ten):
    return (WEB / ten).read_text(encoding="utf-8")


# ---------- Máy chủ ----------

def test_trang_chu_tra_200_co_meta_va_neo(client):
    c, _ = client
    r = c.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"] and r.headers["cache-control"] == "no-cache"
    m = ND["meta"]["trang_chu"]
    assert '<html lang="vi">' in r.text and f"<title>{m['title']}</title>" in r.text
    assert f'<meta name="description" content="{m["description"]}">' in r.text
    assert f'property="og:title" content="{m["og_title"]}"' in r.text and f'property="og:description" content="{m["og_description"]}"' in r.text
    assert "{{" not in r.text and 'src="/play/landing.js"' in r.text and 'id="dau-trang"' in r.text


def test_trang_huong1_tra_200_co_meta(client):
    c, _ = client
    r = c.get("/huong-1")
    m = ND["meta"]["huong1"]
    assert r.status_code == 200 and '<html lang="vi">' in r.text and f"<title>{m['title']}</title>" in r.text
    assert f'property="og:title" content="{m["og_title"]}"' in r.text and "{{" not in r.text and 'src="/play/huong1.js"' in r.text


def test_meta_ngan_va_du_bon_the():
    for m in ND["meta"].values():
        assert set(m) == {"title", "description", "og_title", "og_description"}
        assert len(m["title"]) <= 70 and len(m["og_title"]) <= 70 and len(m["description"]) <= 160 and len(m["og_description"]) <= 160


def test_trang_cu_van_chay_dung_dia_chi(client):
    c, _ = client
    assert c.get("/play/").status_code == 200 and 'src="/play/app.js"' in c.get("/play/").text
    assert c.get("/admin/").status_code == 200
    assert c.get("/health").json() == {"status": "ok"}
    for ten in ("landing.css", "landing_chung.js", "landing_popup.js", "landing_khoi.js", "landing.js", "huong1.js"):
        assert c.get("/play/" + ten).status_code == 200


def test_api_chu_trang_chu_day_du_va_khong_lo_ghi_chu(client):
    c, _ = client
    d = c.get("/api/content/landing").json()
    assert "_ghi_chu" not in d and "_ghi_chu_huong1_url" not in d and "_ghi_chu_dong_y_url" not in d
    for khoa in ("huong1_url", "dong_y_url", "meta", "dau_trang", "mo_dau", "gioi_thieu", "hai_huong", "quy_trinh", "ket_qua", "rieng_tu",
                 "hoi_dap", "nguoi_thuc_hien", "chan_trang", "popup", "huong1_trang", "dang_lam_do"):
        assert khoa in d, khoa
    assert d["dau_trang"]["nut_tham_gia"] == "Tham gia" and d["mo_dau"]["nut_demo"] == "Thử bản demo"


def test_noi_dung_dung_chu_da_chot():
    """Các chỗ Trang yêu cầu 'dùng đúng chữ này'."""
    assert [m["chu"] for m in ND["dau_trang"]["muc"]] == ["Giới thiệu", "Bạn sẽ làm gì?", "Quyền riêng tư", "Hỏi đáp", "Liên hệ"]
    assert ND["mo_dau"]["tieu_de"] == "SparkMind: AI giúp bạn nghĩ tốt hơn, hay nghĩ ít đi?"
    assert len(ND["mo_dau"]["mo_ta"]) == 3 and len(ND["quy_trinh"]["buoc"]) == 5 and len(ND["hoi_dap"]["cau"]) == 5
    assert ND["hai_huong"]["huong1"]["thoi_gian"] == "Thời gian: Khoảng 3–5 phút."
    assert "25–30 phút" in ND["hai_huong"]["huong2"]["thoi_gian"] and "25–30 phút" in ND["popup"]["huong2"]["thoi_gian"]
    assert ND["popup"]["huong1"]["nut"] == "Chọn Hướng 1" and ND["popup"]["huong2"]["nut"] == "Chọn Hướng 2"
    assert ND["hai_huong"]["huong1"]["nut"] == ND["hai_huong"]["huong2"]["nut"] == "Tìm hiểu và tham gia"
    assert ND["huong1_trang"]["nut_bat_dau"] == "Bắt đầu khảo sát" and ND["huong1_trang"]["tieu_de"] == "Bắt đầu bằng một khảo sát nhỏ!"
    assert ND["chan_trang"]["ban_quyen"] == "© 2026 SparkMind"


def test_don_vi_va_email_lay_tu_content():
    nt = ND["nguoi_thuc_hien"]
    assert nt["email"] == EMAIL and nt["email"] == UI["hoan_thanh"]["email"]   # cùng email với màn cảm ơn của luồng làm bài
    assert nt["don_vi"] and "[TODO" not in nt["don_vi"]
    assert ND["huong1_url"].startswith("https://")


def test_status_cho_trang_chu_thong_bao_va_cong_tac(client):
    c, db = client
    assert c.get("/api/status").json()["thong_bao"] is None
    dat_cai_dat(db, thong_bao="Bảo trì tối nay", huong2_mo=False)
    d = c.get("/api/status").json()
    assert d["thong_bao"] == "Bảo trì tối nay" and d["huong2_mo"] is False


# ---------- Không hỏng luồng hướng 2 ----------

def test_luong_huong2_dung_man_chao_cu_va_ma_van_dung_luong_cu(client):
    """Chọn hướng 2 ở popup chỉ chuyển tới /play/ (màn chào có ô nhập mã). Mã vẫn kiểm bằng API cũ; hướng 2 đóng -> 423."""
    from sparkmind import research_store as kho
    c, db = client
    ma = kho.tao_ma_moi(db, 1, "volunteer")[0]
    assert c.post("/api/research/code/check", json={"code": ma}).json()["valid"] is True
    dat_cai_dat(db, huong2_mo=False)
    assert c.post("/api/research/code/check", json={"code": ma}).status_code == 423
    dat_cai_dat(db, huong2_mo=True)
    settings_store.xoa_cache()
    assert c.post("/api/research/start", json={"code": ma, **BAT_DAU}).json()["session_token"]
    assert 'class="the-chao"' not in c.get("/").text    # trang chủ không nhúng ô nhập mã nữa
    assert "manMa" in doc("app.js") and "u.nhan_o_ma" in doc("app.js")   # màn chào hướng 2 nằm nguyên ở app.js


def test_trang_chu_khong_con_o_nhap_ma_va_khong_ghi_session():
    """Trang chủ không còn tự kiểm mã hay ghi sessionStorage: mọi việc ở màn chào của app.js."""
    for ten in JS_TRANG_CHU + ["huong1.js"]:
        js = doc(ten)
        assert "code/check" not in js and "sessionStorage" not in js and "o-ma" not in js, ten


def test_khoa_luu_tru_dung_voi_app():
    js = doc("landing_chung.js")
    assert re.search(r'KHOA_TOKEN = "(\w+)"', js).group(1) in doc("app.js")
    assert '"/play/"' in doc("landing.js") and '"/play/#demo"' in doc("landing_khoi.js")


def test_demo_hash_trong_app_js_khong_doi_luong_chinh():
    app = doc("app.js")
    assert 'location.hash === "#demo"' in app and "manDemoGioiThieu();" in app


# ---------- Chữ chỉ ở một chỗ, không thư viện ngoài ----------

def test_js_khong_viet_cung_chu_tru_dong_bao_loi_tai():
    """Mỗi file JS của trang chủ chỉ được có tối đa 1 chuỗi tiếng Việt viết sẵn: dòng báo lỗi khi chưa tải được nội dung."""
    from tests.test_form_text import chuoi_trong_js
    viet = []
    for ten in JS_TRANG_CHU + ["huong1.js"]:
        viet += [c for c in chuoi_trong_js(doc(ten)) if CHU_VIET.search(c)]
    assert len(viet) == 2 and all(v.startswith("Không tải được") for v in viet)
    for ten in ("landing.html", "huong1.html"):
        assert not CHU_VIET.search(re.sub(r"<!--.*?-->|\{\{.*?\}\}", "", doc(ten), flags=re.S)), ten


def test_khong_thu_vien_ngoai_khong_anh_ngoai():
    """Chỉ phông Nunito (đang dùng cả site) được tải từ ngoài; không script, không ảnh ngoài."""
    for ten in ("landing.html", "huong1.html"):
        html = doc(ten)
        assert not re.search(r"<script[^>]+src=[\"']https?:", html) and "<img" not in html
        ngoai = set(re.findall(r"(?:href|src)=[\"'](https?://[^\"']+)", html))
        assert all(u.startswith(("https://fonts.googleapis.com", "https://fonts.gstatic.com")) for u in ngoai), ngoai
    for ten in JS_TRANG_CHU + ["huong1.js"]:
        assert not re.search(r"\b(import\s|require\(|https?://(?!www\.w3\.org))", doc(ten)), ten
    assert "url(http" not in doc("landing.css") and "@import" not in doc("landing.css")


def test_giao_dien_dep_an_toan_csp_va_reduced_motion():
    """Nâng cấp giao diện: CSS/JS ở file tĩnh (hợp CSP), không script/style nhúng mới, tôn trọng reduced-motion, mặc định nội dung hiện, nhẹ (<= 30 KB thêm)."""
    html, css, js = doc("landing.html"), doc("landing_dep.css"), doc("landing_hieuung.js")
    assert 'href="/play/landing_dep.css"' in html and 'src="/play/landing_hieuung.js"' in html
    assert not re.search(r"<script(?![^>]*src=)[^>]*>", html) and "onclick=" not in html and ' style="' not in re.sub(r'<svg width="0"[^>]*>', "", html)
    assert "prefers-reduced-motion" in js and ".hd .hd-an" in css and "@media (prefers-reduced-motion: reduce)" in css
    assert re.search(r"\.hd \.hd-an \{ opacity: 0", css) and not re.search(r"^\.hd-an \{", css, re.M)   # ẩn trước khi hiện chỉ áp khi JS bật class "hd"
    assert "url(http" not in css and "@import" not in css and "unsafe-eval" not in js and "eval(" not in js
    for khung in re.findall(r"@keyframes [\w-]+ \{(.*?)\}\s*(?:\n|$)", css):   # keyframes chỉ đổi transform/opacity/background-position, không đổi kích thước/vị trí
        assert not re.search(r"(?<![-\w])(width|height|top|left|right|bottom|margin|padding)\s*:", khung), khung
    them = sum(len(doc(t).encode()) for t in ("landing_dep.css", "landing_hieuung.js"))
    assert them <= 30 * 1024, them


def test_trang_cam_on_huong1_can_giua_bang_class_rieng():
    """Trang cảm ơn/đã nộp hướng 1 (survey1.js) và trang "chưa mở" (dong.js) căn giữa bằng cam-on-h1; trang kết quả hướng 2 (result.js) không đổi."""
    assert "cam-on-h1" in doc("survey1.js") and "cam-on-h1" not in doc("result.js")
    css = doc("style.css")
    assert re.search(r"\.cam-on-h1 \.nut-mail \{[^}]*width: min\(100%, 480px\)", css) and "text-align: center" in css.split(".cam-on-h1 {")[1].split("}")[0]


def test_ham_toi_da_30_dong():
    for ten in JS_TRANG_CHU + ["huong1.js"]:
        dong = doc(ten).splitlines()
        for i, d in enumerate(dong):
            if re.match(r"(async )?function \w+\(", d):
                cuoi = next(j for j in range(i, len(dong)) if dong[j] == "}")
                assert cuoi - i + 1 <= 30, f"{ten}: {d} dài {cuoi - i + 1} dòng"


def test_danh_sach_todo_con_lai():
    """Các chỗ [TODO] phải nằm đúng chỗ đã báo cho Trang (đổi danh sách này khi Trang điền xong)."""
    from server.content_api import bo_ghi_chu
    hien = json.dumps(bo_ghi_chu(ND), ensure_ascii=False)
    assert hien.count("[TODO") == 0      # chữ hiện cho người dùng không còn [TODO] nào
    assert ND["dong_y_url"] == ""        # [TODO] ở _ghi_chu_dong_y_url: Trang chưa điền


# ---------- Chạy trên DOM giả (cần node) ----------

NODE = shutil.which("node")


def chay_node(ten_kich_ban):
    kich_ban = Path(__file__).with_name(ten_kich_ban)
    r = subprocess.run([NODE, str(kich_ban), str(WEB), json.dumps(ND)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not NODE, reason="không có node")
def test_trang_chu_chay_tren_dom_gia():
    """Header và neo, thứ tự khối, popup (Esc, bấm ngoài, nút đóng, giữ focus, trả focus), thẻ hướng 2 theo công tắc, mailto, accordion, menu."""
    chay_node("landing_dom_test.js")


@pytest.mark.skipif(not NODE, reason="không có node")
def test_trang_huong1_chay_tren_dom_gia():
    """Trang /huong-1: nút Bắt đầu khảo sát mở huong1_url ở tab mới; trống thì Sắp mở."""
    chay_node("huong1_dom_test.js")
