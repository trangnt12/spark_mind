// Trang chủ "/" (JavaScript thuần): nạp chữ + công tắc, dựng header cố định, thẻ "bài làm dở" và các khối (landing_khoi.js).
// Mọi chữ lấy từ /api/content/landing (content/landing_ui.json). Không đổi luồng làm bài hướng 2 (do app.js lo).
"use strict";

const ND = { ui: null, tt: null };     // nội dung chữ và công tắc đóng/mở (/api/status)
const goc = document.getElementById("man-hinh");

/** Menu trên điện thoại: mở/đóng bảng liên kết (nút hamburger có aria-expanded). */
function batTatMenu(dau, nut, mo) {
  dau.classList.toggle("mo-menu", mo);
  nut.setAttribute("aria-expanded", mo ? "true" : "false");
  nut.setAttribute("aria-label", mo ? ND.ui.dau_trang.nut_dong_menu : ND.ui.dau_trang.nut_menu);
}

/** Danh sách liên kết neo của header (bấm thì cuộn mượt tới khối; trên điện thoại thì đóng menu). */
function dsLienKet(khiBam) {
  const u = ND.ui.dau_trang;
  return h("nav", { id: "lp-menu", class: "lp-menu", "aria-label": u.nhan_dieu_huong },
    u.muc.map((m) => h("a", { href: "#" + m.id, onclick: khiBam }, m.chu)));
}

/** Header cố định: tên SparkMind, liên kết neo, nút Tham gia (luôn thấy), nút menu trên điện thoại. */
function veDauTrang() {
  const u = ND.ui.dau_trang, dau = document.getElementById("dau-trang");
  const menu = h("button", { type: "button", class: "lp-nut-menu", "aria-expanded": "false", "aria-controls": "lp-menu", "aria-label": u.nut_menu, onclick: () => batTatMenu(dau, menu, !dau.classList.contains("mo-menu")) }, bieuTuong("bd-menu"));
  const tham = h("button", { type: "button", class: "lp-nut-tham-gia", onclick: () => moPopup(tham) }, u.nut_tham_gia);
  const ten = h("a", { class: "lp-thuong-hieu", href: "#dau-trang-chu" }, bieuTuong("bd-logo", "logo"), h("span", { class: "ten" }, u.ten_du_an));
  dau.replaceChildren(h("div", { class: "lp-dau-trong" }, ten, dsLienKet(() => batTatMenu(dau, menu, false)), tham, menu));
  dau.addEventListener("keydown", (e) => { if (e.key === "Escape" && dau.classList.contains("mo-menu")) { batTatMenu(dau, menu, false); menu.focus(); } });
}

/** Thẻ "Bạn đang có bài làm dở" (chỉ khi máy này có phiên hướng 2): Tiếp tục -> /play/, app.js đưa về đúng bước dở. */
function theBaiDo() {
  if (!coBaiDo()) return null;
  const u = ND.ui.dang_lam_do;
  return h("div", { class: "lp-bai-do the-bai-do" }, h("div", { class: "lp-trong lp-bai-do-trong" },
    h("div", {}, h("strong", {}, u.tieu_de), h("p", {}, u.mo_ta)), h("a", { class: "nut-ngoai", href: "/play/" }, u.nut)));
}

/** Dựng toàn bộ thân trang theo thứ tự các khối. */
function veTrang() {
  const u = ND.ui;
  goc.replaceChildren(...[theBaiDo(), khoiMoDau(u.mo_dau), khoiGioiThieu(u.gioi_thieu), khoiHaiHuong(u.hai_huong), khoiQuyTrinh(u.quy_trinh),
    khoiKetQua(u.ket_qua), khoiRiengTu(u.rieng_tu), khoiHoiDap(u.hoi_dap), khoiNguoiThucHien(u.nguoi_thuc_hien)].filter(Boolean));
  document.getElementById("chan-trang").replaceChildren(chanTrang(u.chan_trang));
  if (typeof hieuUngTrang === "function") hieuUngTrang();   // landing_hieuung.js: chỉ thêm hiệu ứng, không đổi nội dung
}

/** Dòng thông báo của quản trị (settings.thong_bao): rỗng thì ẩn. Dùng textContent nên không chèn HTML được. */
function hienThongBao(chu) {
  const o = document.getElementById("thong-bao");
  o.textContent = chu || "";
  o.classList.toggle("an", !chu);
}

async function khoiDong() {
  const [ui, st] = await Promise.all([goiApi("/api/content/landing"), goiApi("/api/status")]);
  if (ui.status !== 200) { goc.textContent = "Không tải được nội dung. Bạn tải lại trang sau vài giây."; return; }   // chưa có chữ từ máy chủ nên chỉ dòng này viết sẵn
  ND.ui = ui.du_lieu;
  ND.tt = st.status === 200 ? st.du_lieu : null;     // không đọc được công tắc: coi như mở, máy chủ vẫn tự chặn khi cần
  if (ND.tt) hienThongBao(ND.tt.thong_bao);
  veDauTrang();
  veTrang();
  window.addEventListener("pageshow", (e) => { if (e.persisted) veTrang(); });   // quay lại từ /play/ bằng nút Back (trang lấy từ bộ nhớ đệm): vẽ lại thẻ bài dở
}

khoiDong();
