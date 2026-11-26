// Trang giới thiệu riêng của hướng 1 ("/huong-1"): cùng phong cách màn chào hướng 2. Nút "Bắt đầu khảo sát" mở huong1_url ở tab mới.
// Mọi chữ lấy từ /api/content/landing (mục huong1_trang). Cần landing_chung.js.
"use strict";

const goc = document.getElementById("man-hinh");

/** Nút bắt đầu: liên kết ra ngoài (tab mới, noopener) nếu có huong1_url hợp lệ; chưa có thì nút "Sắp mở" bị khóa. */
function nutBatDau(u, url) {
  if (diaChiHopLe(url)) return h("a", { class: "nut-ngoai", href: url.trim(), target: "_blank", rel: "noopener noreferrer" }, u.nut_bat_dau);
  return h("button", { type: "button", disabled: true }, u.sap_mo);
}

/** Dựng trang: banner, thẻ thông tin; đáy trang là "Về trang chủ" và "Bắt đầu khảo sát". */
function veTrang(nd) {
  const u = nd.huong1_trang;
  const the = h("div", { class: "the" }, u.mo_ta.map(dongMoTa), h("p", { class: "cau-hoi" }, u.thong_tin_tieu_de),
    h("ul", { class: "lp-ds-tick" }, u.thong_tin.map((c) => h("li", {}, bieuTuong("bd-tick", "tick"), h("span", {}, c)))), h("p", { class: "mo-ta" }, u.cam_on));
  const chan = document.getElementById("chan-trang");
  goc.replaceChildren(banner(u.tieu_de), the);
  chan.replaceChildren(h("div", { class: "thanh-nut" }, h("a", { class: "nut-ngoai phu", href: "/" }, u.nut_quay_lai), nutBatDau(u, nd.huong1_url)));
  chan.classList.remove("an");
}

async function khoiDong() {
  const r = await goiApi("/api/content/landing");
  if (r.status !== 200) { goc.textContent = "Không tải được nội dung. Bạn tải lại trang sau vài giây."; return; }   // chưa có chữ từ máy chủ nên chỉ dòng này viết sẵn
  document.getElementById("ten-he-thong").textContent = r.du_lieu.ten_he_thong;
  veTrang(r.du_lieu);
}

khoiDong();
