// Trang "Xem lại bài của bạn" (sau khi đã hoàn thành cả 3 game). Dùng lại h(), goiApi(), hienThi()... của app.js,
// tenGame()... của game_chung.js và veAnh(), khungYAi() của game1.js, game3.js.
// Dữ liệu từ GET /api/research/review (máy chủ trả 409 cho tới khi hoàn thành). Đây là NƠI DUY NHẤT người chơi thấy đáp án game 2.
// Năm phần xếp theo thứ tự làm bài, chuyển bằng hai nút mũi tên ở chân trang: Phần B và C (các đáp án đã chọn), Game 1 (các ý đã viết),
// Game 2 (ôn lại hai cột, có điểm x/5), Game 3 (hai ý tưởng đã viết).
"use strict";

const THU_TU_XL = ["hanh_vi", "tu_danh_gia", "game1", "game2", "game3"];   // thứ tự các phần của trang xem lại
const xl = { du_lieu: null, phan: THU_TU_XL[0] };   // du_lieu: bản tải về (giữ trong bộ nhớ trang, không lưu ở máy)

// ---------- Địa chỉ riêng #xem-lai: F5 ở lại đúng trang, nút Back của trình duyệt về trang tổng kết ----------
const DIA_CHI_XL = "#xem-lai";

function laDiaChiXemLai() { return location.hash === DIA_CHI_XL; }

/** Đổi địa chỉ sang #xem-lai, thêm một mục lịch sử (đánh dấu tu: tong_ket) để Back về tổng kết. Đã ở #xem-lai thì thôi. */
function vaoDiaChiXemLai() {
  if (!laDiaChiXemLai()) history.pushState({ tu: "tong_ket" }, "", DIA_CHI_XL);
}

/** Bỏ #xem-lai khỏi địa chỉ, không thêm lịch sử. */
function boDiaChiXemLai() {
  if (laDiaChiXemLai()) history.replaceState(null, "", location.pathname + location.search);
}

/** Nút "Quay lại kết quả": nếu vào từ trang tổng kết thì lùi một bước lịch sử (giống nút Back), không thì về thẳng tổng kết. */
function quayLaiKetQua() {
  if (history.state && history.state.tu === "tong_ket") { history.back(); return; }
  boDiaChiXemLai();
  manHoanThanh();
}

/** Bấm Back/Forward của trình duyệt: khớp màn với địa chỉ (#xem-lai <-> trang tổng kết). */
window.addEventListener("popstate", () => {
  if (!tt.token || tt.demo) return;
  if (laDiaChiXemLai()) manXemLai(xl.phan);
  else if ((docMan() || {}).man === "xem_lai") manHoanThanh();
});

/** Mở trang xem lại, bỏ qua mọi trang giới thiệu/đồng ý/hướng dẫn: tải dữ liệu rồi vẽ.
 *  Máy chủ trả 409 (chưa hoàn thành) thì bỏ #xem-lai và đưa về bước đang dở. */
async function manXemLai(phan = THU_TU_XL[0]) {
  datMan("xem_lai");
  vaoDiaChiXemLai();
  xl.phan = phan;
  if (xl.du_lieu) { veXemLai(); return; }
  hienThi(TONG_BUOC, h("div", { class: "the" }, h("p", { class: "mo-ta", role: "status" }, tt.ui.giao_dien.dang_tai)));
  const r = await goiApi("/api/research/review", undefined, { "X-Session-Token": tt.token });
  if (r.status !== 200) { boDiaChiXemLai(); diDenBuocDangLam(); return; }
  xl.du_lieu = r.du_lieu;
  veXemLai();
}

/** Nút mũi tên sang phần trước (-1) hoặc phần sau (+1). Tạo MỘT lần khi vào trang xem lại; phần đích tính lúc bấm. */
function nutChuyenPhan(buoc, bieu, nhan) {
  return h("button", { type: "button", class: "phu nut-chuyen", "aria-label": nhan,
    onclick: () => manXemLai(THU_TU_XL[THU_TU_XL.indexOf(xl.phan) + buoc]) }, h("span", { "aria-hidden": "true" }, bieu));
}

/** Mờ nút mũi tên ở phần đầu (nút trước) và phần cuối (nút sau). */
function capNhatNutChuyen() {
  const i = THU_TU_XL.indexOf(xl.phan);
  xl.nutTruoc.disabled = i <= 0;
  xl.nutSau.disabled = i >= THU_TU_XL.length - 1;
}

/** Khung chính: nội dung phần đang xem; chân trang có "Quay lại kết quả" và hai nút mũi tên trước/sau.
 *  Đang ở trang xem lại rồi (bấm mũi tên) thì CHỈ đổi nội dung, giữ nguyên chân trang để không bị giật. */
function veXemLai() {
  const u = tt.ui.xem_lai, ve = { hanh_vi: veXlHanhVi, tu_danh_gia: veXlTuDanhGia, game1: veXlGame1, game2: veXlGame2, game3: veXlGame3 };
  const noiDung = ve[xl.phan](xl.du_lieu[xl.phan]);
  if (document.body.classList.contains("man-xem-lai")) {
    goc.replaceChildren(noiDung);
    capNhatNutChuyen();
    window.scrollTo(0, 0);
    return;
  }
  xl.nutTruoc = nutChuyenPhan(-1, "←", u.truoc);
  xl.nutSau = nutChuyenPhan(1, "→", u.sau);
  const quay = h("button", { type: "button", class: "phu quay-lai", onclick: quayLaiKetQua }, u.quay_ket_qua);
  hienThi(TONG_BUOC, noiDung, khungNut(quay, xl.nutTruoc, xl.nutSau));
  document.body.classList.add("man-xem-lai");   // CSS: ẩn thanh tiến độ và chữ "Bước", tiêu đề tối đa 18px trên điện thoại
  capNhatNutChuyen();
}

// ---------- Phần B và C: các đáp án đã chọn (chữ câu hỏi và đáp án lấy từ form_b.json) ----------

/** Chữ các đáp án đã chọn ở câu chọn một/nhiều. Mục "khác" kèm chữ người đó đã gõ. */
function chuDapAn(cau, v, khac) {
  const cac = Array.isArray(v) ? v : [v];
  return cau.options.filter((o) => cac.includes(o.ma)).map((o) => (o.khac && khac ? o.text + " " + khac : o.text));
}

function theXlChon(cau, v, khac) {
  if (v == null) return "";
  return h("div", { class: "the cau-xl" }, h("p", { class: "cau-hoi-xl" }, cau.nhan + " " + cau.text),
    h("ul", { class: "ds-dap-an" }, chuDapAn(cau, v, khac).map((c) => h("li", {}, c))));
}

/** Lưới Likert 1–5: mỗi phát biểu kèm mức đồng ý đã chọn (chữ thang lấy từ form_b.json). */
function theXlLuoi(tieuDeCau, cacDong, tra) {
  const hang = cacDong.filter((d) => tra[d.id] != null).map((d) => h("li", { class: "dong-likert" },
    h("p", { class: "chu-likert" }, d.nhan + " " + d.text), h("p", { class: "chip-dap-an" }, tt.fb.thang_dong_y[tra[d.id]])));
  return h("div", { class: "the cau-xl" }, h("p", { class: "cau-hoi-xl" }, tieuDeCau), h("ul", { class: "ds-likert" }, hang));
}

function tieuPhanXl(khoa) {
  return h("h2", { class: "tieu-phan-xl" }, tt.fb.tieu_de_phan[khoa]);
}

/** Phần B: B1–B3, lưới B4, B5–B7. Bỏ qua (None) khi người chơi chọn chưa từng dùng AI. */
function veXlHanhVi(d) {
  if (!d || d.B1 == null) return h("div", {}, tieuPhanXl("B"), h("p", { class: "mo-ta" }, tt.ui.xem_lai.khong_co_cau_tra_loi));
  const cau = (id) => tt.fb.phan_b_hanh_vi.find((c) => c.id === id), chon = (id) => theXlChon(cau(id), d[id], d[id + "_other"]);
  return h("div", {}, tieuPhanXl("B"), chon("B1"), chon("B2"), chon("B3"),
    theXlLuoi(cau("B4").nhan + " " + cau("B4").text, cau("B4").cac_dong, d), chon("B5"), chon("B6"), chon("B7"));
}

/** Phần C: lưới C1–C5 (mức đồng ý) và câu C6 (chọn một). */
function veXlTuDanhGia(d) {
  if (!d) return h("div", {}, tieuPhanXl("C"), h("p", { class: "mo-ta" }, tt.ui.xem_lai.khong_co_cau_tra_loi));
  const c = tt.fb.phan_c_tu_danh_gia, dong = c.filter((x) => /^C[1-5]$/.test(x.id)), c6 = c.find((x) => x.id === "C6");
  return h("div", {}, tieuPhanXl("C"), theXlLuoi(tt.fb.c_luoi.nhan + " " + tt.fb.c_luoi.text, dong, d), theXlChon(c6, d.C6));
}

// ---------- Game 1 và Game 3: chỉ xem lại chữ đã viết, không điểm ----------

function veXlGame1(g) {
  const u = tt.ui.xem_lai, ds = g.ideas.length ? h("ul", { class: "ds-y" }, g.ideas.map((y) => h("li", { class: "dong-y" }, h("span", {}, y))))
    : h("p", { class: "mo-ta" }, u.game1_trong);
  return h("div", {}, tenGame(1, g.ten), h("div", { class: "the" }, g.do_vat ? [veAnh(g.do_vat), h("h2", {}, g.do_vat.ten)] : "",
    h("p", { class: "ghi-chu" }, u.game1_ds), ds, h("p", { class: "ghi-chu" }, u.khong_diem)));
}

function veXlGame3(g) {
  const u = tt.ui.xem_lai, the = g.tinh_huong.map((th) => h("div", { class: "the" }, h("h2", { class: "tieu-de-th" }, th.tieu_de), khungYAi(th),
    h("p", { class: "ghi-chu" }, u.game3_y_ban), h("p", { class: "y-cua-ban" }, th.noi_dung)));
  return h("div", {}, tenGame(3, g.ten), the, h("p", { class: "ghi-chu" }, u.khong_diem));
}

// ---------- Game 2: ôn lại hai cột ----------

/** Trạng thái thẻ: chon-dung (chọn đúng ý sai, XANH ✓), chon-nham (chọn nhầm ý đúng, ĐỎ ✗), khong-chon (XÁM). */
function trangThaiY2(y) {
  return !y.da_chon ? "khong-chon" : y.la_loi ? "chon-dung" : "chon-nham";
}

/** Đóng mọi tooltip đang mở (trừ thẻ `giu`). */
function dongTooltip(giu) {
  document.querySelectorAll(".the-xl2.mo-tt").forEach((t) => { if (t !== giu) t.classList.remove("mo-tt"); });
}

/** Tooltip của ý sai: chỉ chữ giải thích (không còn dòng "Loại lỗi"). Chỉ ý la_loi mới có. */
function tooltipY2(y) {
  return h("div", { class: "tooltip-y2", role: "tooltip" }, h("p", {}, y.giai_thich));
}

/** Một thẻ ý ở màn ôn lại. Ý sai có cờ 🚩 + tooltip (hover, focus, hoặc chạm để mở/đóng); ý đúng không có gì. */
function theXlY2(y, thuTu) {
  const u = tt.ui.game2, st = trangThaiY2(y);
  const dau = st === "khong-chon" ? "" : h("span", { class: "dau-kq", role: "img", "aria-label": st === "chon-dung" ? u.chon_dung : u.chon_nham },
    st === "chon-dung" ? "✓" : "✗");
  const con = [h("p", { class: "so-y2" }, nhanSoY(thuTu), dau), h("p", { class: "chu-y2" }, y.van_ban)];
  const the = h("li", { class: "the-xl2 " + st + (y.la_loi ? " co-co" : ""), id: "xl-y-" + thuTu }, con);
  if (y.la_loi) {
    const co = h("button", { type: "button", class: "co-sai", "aria-label": u.co_sai, "aria-describedby": "tt-y-" + thuTu }, "🚩");
    const tip = tooltipY2(y);
    tip.id = "tt-y-" + thuTu;
    the.append(co, tip);
    the.addEventListener("click", () => { dongTooltip(the); the.classList.toggle("mo-tt"); });   // chạm/bấm: mở hoặc đóng
    the.addEventListener("keydown", (e) => { if (e.key === "Escape") the.classList.remove("mo-tt"); });
  }
  return the;
}

/** Menu nhảy tới ý 1–12: mỗi mục là số thứ tự kèm chấm màu giống thẻ tương ứng. Bấm thì cuộn tới ý đó. */
function menuNhayY2(cacY) {
  const u = tt.ui.game2;
  return h("nav", { class: "nhay-y2", "aria-label": u.nhay_toi_y }, cacY.map((y, i) =>
    h("button", { type: "button", class: "phu nhay " + trangThaiY2(y), "aria-label": u.nhay_toi_y + " " + (i + 1), onclick: () => {
      document.getElementById("xl-y-" + (i + 1)).scrollIntoView({ behavior: giamChuyenDong() ? "auto" : "smooth", block: "start" });
    } }, h("span", { class: "cham", "aria-hidden": "true" }), String(i + 1))));
}

function veXlGame2(g) {
  const u = tt.ui.game2, x = tt.ui.xem_lai;
  const trai = h("aside", { class: "cot-trai-xl" }, h("p", { class: "diem-xl" }, u.diem.replace("{d}", g.diem).replace("{tong}", g.diem_toi_da)), menuNhayY2(g.y));
  const phai = h("ol", { class: "cot-phai-xl" }, g.y.map((y, i) => theXlY2(y, i + 1)));
  return h("div", {}, tenGame(2, g.ten), h("p", { class: "ghi-chu" }, x.chu_thich), h("div", { class: "bo-cuc-xl2" }, trai, phai));
}
