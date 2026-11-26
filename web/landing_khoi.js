// Các khối nội dung của trang chủ "/": mở đầu, giới thiệu, hai hướng, quy trình, kết quả, quyền riêng tư, hỏi đáp, người thực hiện, chân trang.
// Cần: h, bieuTuong, dongMoTa, diaChiHopLe (landing_chung.js), moPopup, huong2Dong (landing_popup.js), ND (landing.js).
"use strict";

/** Một khối full-width: nền "trang" hoặc "xanh" (xen kẽ), nội dung căn giữa trong .lp-trong. */
function khoi(id, nen, ...con) {
  return h("section", { id, class: "lp-khoi nen-" + nen }, h("div", { class: "lp-trong" }, con), songNgan());
}

/** Đường lượn sóng ở mép dưới khối (SVG trang trí), màu lấy từ nền của khối kế tiếp qua biến CSS. */
function songNgan() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const duong = document.createElementNS("http://www.w3.org/2000/svg", "path");
  svg.setAttribute("viewBox", "0 0 1440 60"); svg.setAttribute("preserveAspectRatio", "none"); svg.setAttribute("class", "lp-song"); svg.setAttribute("aria-hidden", "true");
  duong.setAttribute("d", "M0 30C180 60 360 60 540 36S900 0 1080 18 1320 54 1440 30V60H0Z");
  svg.append(duong);
  return svg;
}

/** Danh sách gạch đầu dòng có dấu tick. */
function dsTick(cac) {
  return h("ul", { class: "lp-ds-tick" }, cac.map((c) => h("li", {}, bieuTuong("bd-tick", "tick"), h("span", {}, c))));
}

/** Nút "Tham gia" mở popup. uuTien: hướng được focus sẵn. */
function nutMoPopup(chu, kieu, uuTien) {
  const nut = h("button", { type: "button", class: kieu, onclick: () => moPopup(nut, uuTien) }, chu);
  return nut;
}

/** Khối mở đầu: tiêu đề, ba đoạn mô tả, hai nút; bên phải là hình logo trang trí. */
function khoiMoDau(u) {
  const chu = h("div", { class: "lp-mo-dau-chu" }, h("h1", {}, u.tieu_de), u.mo_ta.map((d) => h("p", { class: "lp-dan" }, d)),
    h("div", { class: "lp-nhom-nut" }, nutMoPopup(u.nut_chinh, "lp-nut-lon"), h("a", { class: "lp-nut-phu", href: "/play/#demo" }, u.nut_demo)));
  const hinh = h("div", { class: "lp-hinh", "aria-hidden": "true" }, bieuTuong("bd-logo", "lp-logo-to"), h("i", { class: "lp-hat h1" }), h("i", { class: "lp-hat h2" }), h("i", { class: "lp-hat h3" }),
    bieuTuong("bd-tia", "lp-bt bt1"), bieuTuong("bd-den", "lp-bt bt2"), bieuTuong("bd-no-ron", "lp-bt bt3"));
  const nen = h("div", { class: "lp-nen-hero", "aria-hidden": "true" }, h("i", { class: "lp-blob b1" }), h("i", { class: "lp-blob b2" }), h("i", { class: "lp-blob b3" }));
  return h("section", { id: "dau-trang-chu", class: "lp-khoi lp-mo-dau" }, nen, h("div", { class: "lp-trong lp-mo-dau-luoi" }, chu, hinh), songNgan());
}

/** Huy hiệu biểu tượng SVG tròn, màu riêng theo thẻ (trang trí). */
function huyHieu(ten) {
  return h("span", { class: "lp-hieu", "aria-hidden": "true" }, bieuTuong(ten));
}

/** Khối giới thiệu dự án: "Vì sao có SparkMind?", mục tiêu, phương pháp. */
function khoiGioiThieu(u) {
  const mt = u.muc_tieu, pp = u.phuong_phap;
  const vi = h("div", { class: "lp-the the-gt gt-hophach" }, huyHieu("bd-den"), h("h2", {}, u.tieu_de), u.doan.map((d) => h("p", { class: "lp-dan" }, d)));
  const muc = h("div", { class: "lp-the the-gt gt-xanh" }, huyHieu("bd-muc-tieu"), h("h3", {}, h("span", { "aria-hidden": "true" }, mt.bieu_tuong + " "), mt.tieu_de), h("p", { class: "mo-ta" }, mt.dan), dsTick(mt.y));
  const phap = pp.y.map((y, i) => h("li", { class: "lp-the the-gt gt-" + ["ngoc", "san-ho", "xanh"][i % 3] }, huyHieu(["bd-tia", "bd-no-ron", "bd-khien"][i % 3]), h("span", { class: "lp-so-nho", "aria-hidden": "true" }, String(i + 1)), h("h4", {}, y.ten), h("p", { class: "mo-ta" }, y.mo_ta)));
  return khoi("gioi-thieu", "trang", h("div", { class: "lp-luoi-2" }, vi, muc),
    h("h3", { class: "lp-tieu-de-nho" }, h("span", { "aria-hidden": "true" }, pp.bieu_tuong + " "), pp.tieu_de), h("p", { class: "mo-ta" }, pp.dan), h("ol", { class: "lp-luoi-3" }, phap));
}

/** Nút của một thẻ hướng: mở popup, hoặc khóa ("Sắp mở" / "Đã đóng"). */
function nutTheHuong(u, khoa, nhanKhoa, uuTien) {
  if (khoa) return h("button", { type: "button", class: "lp-nut-the", disabled: true }, nhanKhoa);
  return nutMoPopup(u.nut, "lp-nut-the", uuTien);
}

/** Một thẻ hướng tham gia. khoa = không bấm được (đóng / chưa mở). */
function theHuong(u, khoa, nhanKhoa, uuTien) {
  const tong = uuTien === "huong1" ? " tong-ngoc" : " tong-xanh";
  const huy = khoa && uuTien === "huong2" ? h("p", { class: "lp-nhan-dong" }, u.da_dong_mo_ta) : null;
  return h("article", { class: "lp-the lp-the-huong" + tong + (khoa ? " khoa" : "") }, h("div", { class: "lp-bieu-tuong", "aria-hidden": "true" }, u.bieu_tuong),
    h("h3", {}, u.ten), h("p", { class: "lp-thoi-gian" }, u.thoi_gian), h("p", { class: "mo-ta" }, u.mo_ta), dsTick(u.y), huy, nutTheHuong(u, khoa, nhanKhoa, uuTien));
}

/** Khối hai hướng tham gia. Hướng 2 đóng (huong2_mo = false) thì "Đã đóng"; huong1_url trống thì "Sắp mở". */
function khoiHaiHuong(u) {
  const khoa1 = !diaChiHopLe(ND.ui.huong1_url), khoa2 = huong2Dong();
  return khoi("ban-se-lam-gi", "xanh", h("h2", { class: "giua" }, u.tieu_de), h("p", { class: "lp-dan giua" }, u.mo_ta),
    h("div", { class: "lp-luoi-2 deu" }, theHuong(u.huong1, khoa1, u.huong1.sap_mo, "huong1"), theHuong(u.huong2, khoa2, u.huong2.da_dong, "huong2")));
}

/** Khối quy trình hướng 2: các bước đánh số nối nhau bằng một đường. */
function khoiQuyTrinh(u) {
  const buoc = u.buoc.map((b, i) => h("li", { class: "lp-buoc" }, h("span", { class: "lp-so", "aria-label": u.nhan_buoc + " " + (i + 1) }, String(i + 1)),
    h("h3", {}, b.ten), h("p", { class: "mo-ta" }, b.mo_ta)));
  return khoi("quy-trinh", "trang", h("h2", { class: "giua" }, u.tieu_de), h("p", { class: "lp-dan giua" }, u.phu_de), h("ol", { class: "lp-quy-trinh" }, buoc));
}

/** Khối "Kết quả bạn nhận được": ba thẻ và một dòng lưu ý. */
function khoiKetQua(u) {
  const the = u.y.map((y, i) => h("li", { class: "lp-the the-kq kq-" + (i % 3) }, h("div", { class: "lp-bieu-tuong", "aria-hidden": "true" }, y.bieu_tuong), h("h3", {}, y.ten), h("p", { class: "mo-ta" }, y.mo_ta),
    h("div", { class: "lp-do", "aria-hidden": "true" }, h("i", {}))));
  return khoi("ket-qua", "xanh", h("h2", { class: "giua" }, u.tieu_de), h("p", { class: "lp-dan giua" }, u.dan), h("ul", { class: "lp-luoi-3" }, the),
    h("p", { class: "lp-luu-y" }, h("strong", {}, u.luu_y_nhan + " "), u.luu_y));
}

/** Liên kết tới văn bản đồng ý (chỉ hiện khi file nội dung có dong_y_url hợp lệ). */
function lienKetDongY(chu) {
  if (!diaChiHopLe(ND.ui.dong_y_url)) return null;
  return h("a", { class: "lp-lien-ket", href: ND.ui.dong_y_url.trim(), target: "_blank", rel: "noopener noreferrer" }, chu);
}

/** Khối quyền riêng tư và dữ liệu: dữ liệu thu thập theo hướng, cách dùng, cam kết. */
function khoiRiengTu(u) {
  const hg = (x) => h("div", { class: "lp-the" }, h("h3", {}, x.ten), dsTick(x.y));
  return khoi("quyen-rieng-tu", "trang", h("div", { class: "lp-khien", "aria-hidden": "true" }, bieuTuong("bd-khien")), h("h2", { class: "giua" }, u.tieu_de), h("p", { class: "lp-dan giua" }, u.mo_ta),
    h("h3", { class: "lp-tieu-de-nho" }, u.thu_thap_tieu_de), h("div", { class: "lp-luoi-2 deu" }, hg(u.huong1), hg(u.huong2)),
    h("h3", { class: "lp-tieu-de-nho" }, u.su_dung_tieu_de), dsTick(u.su_dung),
    h("p", { class: "lp-luu-y" }, h("strong", {}, u.cam_ket_nhan + " "), u.cam_ket), lienKetDongY(u.lien_ket_dong_y));
}

/** Đóng/mở một câu hỏi (accordion). Nút là <button> thật nên Enter/Space mở được bằng bàn phím. */
function batTatCau(nut, vung) {
  const mo = nut.getAttribute("aria-expanded") !== "true";
  nut.setAttribute("aria-expanded", mo ? "true" : "false");
  if (mo) vung.removeAttribute("hidden"); else vung.setAttribute("hidden", "");
  vung.parentNode.classList.toggle("mo", mo);   // lớp "mo" nằm ở khung câu hỏi (xoay mũi tên)
}

/** Một câu hỏi đáp: nút hỏi (có mũi tên) và vùng trả lời ẩn. */
function mucHoiDap(c, i) {
  const vung = h("div", { class: "lp-tra-loi", id: "hd-tl-" + i, role: "region", "aria-labelledby": "hd-hoi-" + i, hidden: true }, h("div", { class: "lp-tra-loi-trong" }, h("p", {}, c.dap)));
  const nut = h("button", { type: "button", class: "lp-hoi", id: "hd-hoi-" + i, "aria-expanded": "false", "aria-controls": "hd-tl-" + i }, h("span", {}, c.hoi), bieuTuong("bd-mui-xuong", "mui"));
  nut.addEventListener("click", () => batTatCau(nut, vung));
  return h("div", { class: "lp-cau-hd" }, h("h3", {}, nut), vung);
}

/** Khối hỏi đáp thường gặp. */
function khoiHoiDap(u) {
  return khoi("hoi-dap", "xanh", h("h2", { class: "giua" }, u.tieu_de), h("div", { class: "lp-hoi-dap" }, u.cau.map(mucHoiDap)));
}

/** Khối người thực hiện và liên hệ (email dạng mailto). */
function khoiNguoiThucHien(u) {
  const dong = (nhan, noi) => h("p", { class: "lp-dong-lh" }, h("strong", {}, nhan + " "), noi);
  return khoi("lien-he", "trang", h("h2", { class: "giua" }, u.tieu_de), h("div", { class: "lp-the lp-lien-he" },
    h("p", { class: "lp-dan" }, u.gioi_thieu + " ", h("strong", {}, u.ten), ", " + u.vai_tro + "."), dong(u.don_vi_nhan, u.don_vi),
    dong(u.email_nhan, h("a", { class: "lp-lien-ket", href: "mailto:" + u.email }, u.email)), h("p", { class: "mo-ta" }, u.ho_tro)));
}

/** Chân trang: khẩu hiệu, mô tả, bản quyền. */
function chanTrang(u) {
  return h("div", { class: "lp-trong" }, h("p", { class: "lp-khau-hieu" }, u.khau_hieu), h("p", {}, u.mo_ta), h("p", { class: "lp-ban-quyen" }, u.ban_quyen));
}
