"""Kiểm tra trang tổng kết (web/result.js) và trang xem lại (web/review.js), phiên 25/11:
1. Khối "Mô hình đã dựa vào đâu?": thu gọn mặc định, 4 gạch đầu dòng lấy từ content, số 6/10 và ±10 chỉ ghi ở MỘT nơi.
2. Nút "Xem lại kết quả bài làm": mở thẳng trang xem lại (không qua trang giới thiệu), địa chỉ #xem-lai, F5 và Back đúng chỗ,
   chỉ vào được khi đã hoàn thành (chưa xong thì về bước đang dở).
3. Thẻ cảm ơn: chữ từ content, mailto đúng địa chỉ, chỉ ở trang tổng kết.
Phần luồng trang chạy thật bằng Node (nếu máy có) với lịch sử trình duyệt giả; phần còn lại đọc mã nguồn và content."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))
from tests.test_form_text import chuoi_trong_js  # noqa: E402
from tests.test_game2 import client  # noqa: E402,F401  (fixture máy chủ thử)


def doc(rel):
    return (GOC / rel).read_text(encoding="utf-8")


def nd(ten):
    return json.loads(doc("content/" + ten))


def chuoi_json(x):
    """Mọi chuỗi giá trị trong một file JSON."""
    if isinstance(x, dict):
        return [c for v in x.values() for c in chuoi_json(v)]
    if isinstance(x, list):
        return [c for v in x for c in chuoi_json(v)]
    return [x] if isinstance(x, str) else []


# ---------- 1. Khối "Mô hình đã dựa vào đâu?" và số của mô hình ----------

def test_khoi_mo_hinh_bon_gach_dau_dong_lay_tu_content_va_thu_gon():
    gach = nd("results_ui.json")["dong_gop"]["gach"]
    assert len(gach) == 4 and "{dung}/10" in gach[2] and "±{sai_so_noi}" in gach[2]
    assert "hàng trăm" in gach[0] and "7 câu" in gach[1] and "không phải đánh giá năng lực" in gach[3]
    js = doc("web/result.js")
    ham = js.split("function mucDongGop")[1].split("\n}\n")[0]
    assert 'h("details", { class: "the dong-gop" }' in ham and "open" not in ham                      # thu gọn mặc định
    assert "u.dong_gop.gach.map" in ham and "canh_bao" not in js and "theDongGop" not in js           # không còn danh sách từng câu


def test_so_mo_hinh_chi_ghi_o_mot_noi_va_khop_meta():
    kq = nd("results_ui.json")
    so = kq["so_mo_hinh"]
    meta = json.loads(doc("models/model_b4_meta.json"))
    # Huấn luyện lại (đóng băng ~22/12) mà quên sửa results_ui.json thì test này báo lỗi
    assert so["dung_tren_10"] == meta["dung_khoang_x_tren_10"], "sửa so_mo_hinh.dung_tren_10 theo models/model_b4_meta.json"
    mae = meta["cv_5x10"]["hoi_quy"]["mae"]["tb"]
    assert abs(so["sai_so_diem"] - mae) < 0.5 and so["sai_so_noi"] == int(mae), "sửa so_mo_hinh theo mae trong model_b4_meta.json"
    # Không chỗ nào khác trong content hay JS viết cứng "x/10", "±N" hay "khoảng N điểm"
    mau = r"\d\s*/\s*10\b|khoảng \d+ điểm|±\s*\d"
    ngoai = [(ten, c) for ten in ("results_ui.json", "research_ui.json") for c in chuoi_json(nd(ten)) if re.search(mau, c)]
    assert ngoai == [], ngoai
    for f in ("web/result.js", "web/demo.js", "web/review.js", "web/app.js"):
        assert not any(re.search(mau, c) for c in chuoi_trong_js(doc(f))), f
    js = doc("web/result.js")
    assert "u.diem.sai_so" not in js and "so_mo_hinh.sai_so_diem" in js and js.count("thaySo(") >= 4
    assert "sai_so" not in kq["diem"]


# ---------- 2. Nút xem lại và địa chỉ #xem-lai ----------

def test_nut_xem_lai_o_duoi_diem_va_trang_tong_ket_khong_con_nut_chan_trang():
    js, ui = doc("web/result.js"), nd("research_ui.json")["xem_lai"]
    assert ui["nut_xem_lai"] == "Xem lại kết quả bài làm" and ui["quay_ket_qua"] == "Quay lại kết quả"
    assert "theXacSuat(kq), tuyChon.duoiDiem" in js                                   # dưới thẻ khả năng của từng mức
    assert "duoiDiem: [theNutXemLai()]" in js and "onclick: () => manXemLai()" in js
    assert "tt.ui.xem_lai.nut_xem_lai" in js and "nutChinh" not in js.split("async function manHoanThanh")[1]


def test_trang_xem_lai_khong_co_the_cam_on_va_co_nut_quay_lai():
    rv = doc("web/review.js")
    assert "theCamOn" not in rv and "hoan_thanh" not in rv
    assert "u.quay_ket_qua" in rv and "quayLaiKetQua" in rv
    assert doc("web/result.js").count("cuoiTrang: [theCamOn()]") == 1                # chỉ gắn ở trang tổng kết (demo không có)


def test_dia_chi_xem_lai_o_app_js_f5_va_chua_hoan_thanh():
    app = doc("web/app.js")
    assert "if (laDiaChiXemLai()) manXemLai(xl.phan); else manHoanThanh();" in app    # F5 khi đã hoàn thành: ở lại #xem-lai
    assert "boDiaChiXemLai();" in app.split("function diDenBuoc(")[1].split("\n}\n")[0]  # chưa hoàn thành: bỏ #xem-lai, về bước dở
    assert "|| laDiaChiXemLai()) diDenBuocDangLam(true)" in app                       # mở thẳng #xem-lai: bỏ qua màn "tiếp tục?"


# ---------- 3. Thẻ cảm ơn ----------

def test_the_cam_on_chu_tu_content_va_mailto_dung():
    u = nd("research_ui.json")["hoan_thanh"]
    assert u["tieu_de"] == "Cảm ơn bạn đã tham gia!" and u["email"] == "nguyenthitrang.ttd@gmail.com"
    assert u["mo_ta"] == ("Câu trả lời của bạn giúp tìm hiểu cách học sinh, sinh viên Việt Nam dùng AI và tư duy sáng tạo. "
                          "Dữ liệu chỉ được dùng cho mục đích nghiên cứu. Nếu có thắc mắc, vui lòng liên hệ:")
    js = doc("web/result.js")
    assert '"mailto:" + u.email' in js and "nguyenthitrang" not in js and "u.tieu_de" in js and "u.chuc" in js
    assert 'class: "the cam-on"' in js and "cuoiTrang: [theCamOn()]" in js
    css = doc("web/style.css")
    assert "var(--xanh-nhat)" in css.split(".cam-on {")[1].split("}")[0] and "min-height: 52px" in css   # nền xanh nhạt, nút mail đủ to
    assert 'id="chan-trang" class="an"' in doc("web/index.html")                      # chân trang để trống, không có chữ nào khác


# ---------- Chạy thật luồng trang bằng Node (lịch sử trình duyệt giả) ----------

PHAN_DAU = r"""
const vm = require('vm'), fs = require('fs');
const log = [], ls = [], popstate = [], lop = new Set();
let idx = 0;
const location = { hash: '', pathname: '/play/', search: '' };
const history = {
  get state() { return ls[idx].state; },
  pushState(s, _t, url) { ls.splice(idx + 1); ls.push({ hash: url, state: s }); idx++; location.hash = url; log.push('push:' + url); },
  replaceState(s, _t, url) { ls[idx] = { hash: url.includes('#') ? url.slice(url.indexOf('#')) : '', state: s }; location.hash = ls[idx].hash; log.push('replace'); },
  back() { idx--; location.hash = ls[idx].hash; log.push('back'); popstate.forEach((f) => f()); },
};
ls.push({ hash: '', state: null });
const h = (ten, tt2, ...c) => ({ ten, tt: tt2, c });
const ctx = {
  location, history, console, log, h, document: { body: { classList: { add: (c) => { lop.add(c); log.push('lop:' + c); }, remove: (...cs) => cs.forEach((c) => lop.delete(c)), contains: (c) => lop.has(c) } } },
  goc: { replaceChildren: () => log.push('doiNoiDung') }, window2: 0,
  window: { addEventListener: (n, f) => { if (n === 'popstate') popstate.push(f); }, scrollTo: () => {} },
  tt: { token: 'tok', demo: false, fb: { tieu_de_phan: { B: 'B', C: 'C' } }, ui: { xem_lai: { game1_trong: 'x', game1_ds: 'x', khong_diem: 'x', khong_co_cau_tra_loi: 'k',
    truoc: 'Trước', sau: 'Sau', tieu_de: 't', quay_ket_qua: 'Quay lại kết quả' }, giao_dien: { dang_tai: '...' } } },
  TONG_BUOC: 7, tenGame: () => h(), veAnh: () => h(), khungYAi: () => h(), nhanSoY: () => h(), giamChuyenDong: () => false,
  hienThi: () => { lop.delete('man-xem-lai'); log.push('hienThi'); }, khungNut: (...a) => { ctx.chan = a; log.push('khungNut'); return { khung: a }; },
  datMan: (m) => { ctx.man = m; }, docMan: () => ({ man: ctx.man }),
  manHoanThanh: () => { lop.delete('man-xem-lai'); log.push('tongKet'); }, diDenBuocDangLam: () => log.push('buocDangLam'),
  goiApi: async () => ctx.phanHoi,
  phanHoi: { status: 200, du_lieu: { hanh_vi: null, tu_danh_gia: null, game1: { ideas: [], ten: 'g1', do_vat: null }, game2: { ten: 'g2', y: [], diem: 0, diem_toi_da: 5 }, game3: { ten: 'g3', tinh_huong: [] } } },
};
vm.createContext(ctx);
const chay = (f) => vm.runInContext(fs.readFileSync(f, 'utf8'), ctx);
"""


def chay_node(doan_js: str):
    if not shutil.which("node"):
        pytest.skip("máy không có Node")
    r = subprocess.run(["node", "-e", PHAN_DAU + doan_js], capture_output=True, text=True, cwd=GOC, timeout=30, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_node_nut_mo_thang_xem_lai_khong_qua_gioi_thieu_va_quay_lai_ve_tong_ket():
    kq = chay_node(r"""
(async () => {
  chay('web/review.js');
  await vm.runInContext('manXemLai()', ctx);                       // bấm nút ở trang tổng kết
  const sau_mo = { hash: location.hash, state: history.state, nhat_ky: log.slice() };
  vm.runInContext('quayLaiKetQua()', ctx);                          // nút "Quay lại kết quả"
  console.log(JSON.stringify({ sau_mo, hash_cuoi: location.hash, nhat_ky: log }));
})();
""")
    assert kq["sau_mo"]["hash"] == "#xem-lai" and kq["sau_mo"]["state"] == {"tu": "tong_ket"}
    assert kq["sau_mo"]["nhat_ky"].count("hienThi") == 2 and "tongKet" not in kq["sau_mo"]["nhat_ky"]   # chỉ "đang tải" rồi trang xem lại
    assert kq["hash_cuoi"] == "" and kq["nhat_ky"][-2:] == ["back", "tongKet"]                           # về tổng kết


def test_node_back_cua_trinh_duyet_ve_tong_ket_va_forward_vao_lai():
    kq = chay_node(r"""
(async () => {
  chay('web/review.js');
  await vm.runInContext('manXemLai()', ctx);
  history.back();                                                    // người dùng bấm Back của trình duyệt
  const sau_back = log.filter((x) => x === 'tongKet').length;
  idx++; location.hash = ls[idx].hash; popstate.forEach((f) => f());  // bấm Forward
  console.log(JSON.stringify({ sau_back, hash: location.hash, so_ve: log.filter((x) => x === 'hienThi').length }));
})();
""")
    assert kq["sau_back"] == 1 and kq["hash"] == "#xem-lai" and kq["so_ve"] >= 3


def test_node_chua_hoan_thanh_409_bi_dua_ve_buoc_dang_do_va_bo_dia_chi():
    kq = chay_node(r"""
(async () => {
  chay('web/review.js');
  ctx.phanHoi = { status: 409, du_lieu: {} };
  await vm.runInContext('manXemLai()', ctx);
  console.log(JSON.stringify({ hash: location.hash, nhat_ky: log }));
})();
""")
    assert kq["hash"] == "" and "buocDangLam" in kq["nhat_ky"] and "tongKet" not in kq["nhat_ky"]


def test_node_f5_o_dia_chi_xem_lai_chi_vao_khi_da_hoan_thanh():
    kq = chay_node(r"""
(async () => {
  chay('web/review.js');
  const app = fs.readFileSync('web/app.js', 'utf8').replace(/\r\n/g, '\n');   // chuẩn hóa CRLF -> LF để cắt theo '\n' không phụ thuộc hệ điều hành
  const bat_dau = app.indexOf('function diDenBuoc(');
  vm.runInContext(app.slice(bat_dau, app.indexOf('\n}\n', bat_dau) + 3), ctx);
  vm.runInContext('var THU_TU_MAN = ["gioi_thieu","game1"]; var BUOC_SANG_MAN = { game1: { vao: "gioi_thieu", xa: "game1" }, cho_game_khac: { vao: "gioi_thieu", xa: "game1" } }; var MAN = { gioi_thieu: () => log.push("man:gioi_thieu"), game1: () => log.push("man:game1") };', ctx);
  ctx.manXemLai = () => log.push('xemLai');
  location.hash = '#xem-lai'; ls[0].hash = '#xem-lai';
  vm.runInContext('diDenBuoc("completed", true)', ctx);              // F5 đã hoàn thành
  const hoanThanh = log.slice(); log.length = 0;
  vm.runInContext('diDenBuoc("game1", true)', ctx);                  // F5 nhưng còn dở game 1
  const chuaXong = { nhat_ky: log.slice(), hash: location.hash };
  location.hash = ''; log.length = 0;
  vm.runInContext('diDenBuoc("completed", true)', ctx);              // vào bình thường (không #xem-lai)
  console.log(JSON.stringify({ hoanThanh, chuaXong, thuong: log }));
})();
""")
    assert kq["hoanThanh"] == ["xemLai"]
    assert kq["chuaXong"]["hash"] == "" and any(x.startswith("man:") for x in kq["chuaXong"]["nhat_ky"]) and "xemLai" not in kq["chuaXong"]["nhat_ky"]
    assert kq["thuong"] == ["tongKet"]


def test_node_chan_trang_xem_lai_co_hai_nut_mui_ten_truoc_sau_khong_con_tab():
    kq = chay_node(r"""
(async () => {
  chay('web/review.js');
  await vm.runInContext('manXemLai()', ctx);                         // phần đầu: Phần B
  const dau = ctx.chan.map((n) => ({ lop: n.tt.class, tat: !!n.disabled, nhan: n.tt['aria-label'] }));
  const thu_tu = vm.runInContext('THU_TU_XL', ctx);
  const ve_truoc = log.filter((x) => x === 'hienThi').length;
  await vm.runInContext('manXemLai("game3")', ctx);                  // bấm sang phần cuối: chỉ đổi nội dung
  const cuoi = ctx.chan.map((n) => ({ tat: !!n.disabled }));
  const gian = { khung_nut: log.filter((x) => x === 'khungNut').length, ve: log.filter((x) => x === 'hienThi').length - ve_truoc, doi: log.filter((x) => x === 'doiNoiDung').length };
  console.log(JSON.stringify({ dau, cuoi, thu_tu, gian }));
})();
""")
    assert kq["thu_tu"] == ["hanh_vi", "tu_danh_gia", "game1", "game2", "game3"]
    assert [n["lop"] for n in kq["dau"]] == ["phu quay-lai", "phu nut-chuyen", "phu nut-chuyen"]              # quay lại kết quả + 2 nút icon
    assert [n["tat"] for n in kq["dau"][1:]] == [True, False] and [n["tat"] for n in kq["cuoi"][1:]] == [False, True]   # mờ ở đầu và cuối
    assert [n["nhan"] for n in kq["dau"][1:]] == ["Trước", "Sau"]
    assert kq["gian"] == {"khung_nut": 1, "ve": 0, "doi": 1}                                                 # bấm mũi tên: không dựng lại chân trang, không vẽ lại cả trang
    rv = doc("web/review.js")
    assert "tab-xl" not in rv and "role: \"tablist\"" not in rv and "tab-xl" not in doc("web/style.css")


def test_tooltip_game2_chi_con_chu_giai_thich_khong_co_dong_loai_loi():
    rv = doc("web/review.js")
    ham = rv.split("function tooltipY2")[1].split("\n}\n")[0]
    assert "loai_loi" not in ham and "loai-loi" not in ham and "y.giai_thich" in ham
    assert "loai-loi" not in doc("web/style.css")


def test_api_xem_lai_co_dap_an_phan_b_va_c(client):
    from tests.test_review_flow import DAU, lam_den_game3, nop3, bat_dau
    c, db = client
    t = lam_den_game3(c, db)
    assert c.get("/api/research/review", headers=DAU(t)).status_code == 409           # chưa hoàn thành: không lộ gì
    bat_dau(c, t)
    nop3(c, t)
    d = c.get("/api/research/review", headers=DAU(t)).json()
    assert set(d) == {"hanh_vi", "tu_danh_gia", "game1", "game2", "game3"}
    assert all(f"B4_{i}" in d["hanh_vi"] for i in range(1, 8)) and all(f"C{i}" in d["tu_danh_gia"] for i in range(1, 7))
    assert d["hanh_vi"]["B1"] and "A1" not in d["hanh_vi"] and "email" not in json.dumps(d)


def test_trang_xem_lai_phan_b_c_lay_chu_tu_form_b():
    rv = doc("web/review.js")
    assert "tt.fb.thang_dong_y[tra[d.id]]" in rv and "tt.fb.tieu_de_phan[khoa]" in rv and "tt.fb.phan_b_hanh_vi" in rv
    assert "veXlHanhVi" in rv and "veXlTuDanhGia" in rv


def test_xem_lai_khong_tieu_de_khong_thanh_tien_do_va_tieu_de_toi_da_18px_tren_dien_thoai():
    rv, css = doc("web/review.js"), doc("web/style.css")
    assert "tieu-de-xl" not in rv and "u.tieu_de" not in rv and "tieu_de" not in nd("research_ui.json")["xem_lai"]   # bỏ tiêu đề "Xem lại bài của bạn"
    assert 'classList.add("man-xem-lai")' in rv and 'classList.add("man-ket-qua")' in doc("web/result.js")
    assert "body.man-xem-lai .tien-do, body.man-xem-lai .nhan-tien-do { display: none; }" in css   # ẩn thanh tiến độ và chữ "Bước"
    khoi = css.split("/* Điện thoại: tiêu đề ở trang kết quả và xem lại tối đa 18px */")[1].split("\n}\n")[0]
    sizes = [int(x) for x in re.findall(r"font-size: (\d+)px", khoi)]
    assert "max-width: 699px" in khoi and sizes and max(sizes) <= 18                                 # tiêu đề trên điện thoại không quá 18px
    assert 'remove("man-gioi-thieu", "man-xem-lai", "man-ket-qua")' in doc("web/app.js")                     # rời màn thì bỏ lớp
