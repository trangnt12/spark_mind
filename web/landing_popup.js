// Popup chọn hướng tham gia của trang chủ. Truy cập được: Esc và bấm ra ngoài để đóng, nút đóng, giữ phím Tab trong popup, trả focus về nút đã mở.
// Cần: h, bieuTuong, diaChiHopLe (landing_chung.js). Dữ liệu (ND) do landing.js nạp.
"use strict";

const POPUP = { nen: null, moTu: null, canh: [], khiPhim: null };   // trạng thái popup đang mở (nen = lớp phủ)

/** Lựa chọn của một hướng: nút dẫn đi (thẻ <a>) hoặc nút khóa khi hướng đó chưa mở / đã đóng. data-huong dùng để focus đúng lựa chọn. */
function nutLuaChon(u, href, nhanKhoa, huong) {
  if (nhanKhoa) return h("button", { type: "button", class: "lp-nut-the", disabled: true, "data-huong": huong }, nhanKhoa);
  return h("a", { class: "nut-ngoai", href, "data-huong": huong }, u.nut);
}

/** Một thẻ lựa chọn trong popup: tên, thời gian, mô tả và nút. */
function theLuaChon(u, nut, khoa) {
  return h("div", { class: "lp-lua-chon" + (khoa ? " khoa" : "") }, h("h3", {}, u.ten), h("p", { class: "lp-thoi-gian" }, u.thoi_gian),
    h("p", { class: "mo-ta" }, u.mo_ta), nut);
}

/** Hướng 1 chọn được khi có huong1_url hợp lệ; chưa có thì "Sắp mở". */
function luaChonHuong1() {
  const u = ND.ui.popup.huong1, khoa = !diaChiHopLe(ND.ui.huong1_url);
  return theLuaChon(u, nutLuaChon(u, "/huong-1", khoa && ND.ui.hai_huong.huong1.sap_mo, "huong1"), khoa);
}

/** Hướng 2 chọn được khi công tắc huong2_mo không tắt; tắt thì "Đã đóng". Chọn thì sang /play/ (màn chào có ô nhập mã). */
function luaChonHuong2() {
  const u = ND.ui.popup.huong2, khoa = huong2Dong();
  return theLuaChon(u, nutLuaChon(u, "/play/", khoa && ND.ui.hai_huong.huong2.da_dong, "huong2"), khoa);
}

/** Công tắc hướng 2 đang tắt? (Không đọc được công tắc thì coi như mở, máy chủ vẫn tự chặn.) */
function huong2Dong() {
  return !!ND.tt && ND.tt.huong2_mo === false;
}

/** Dựng hộp popup: nút đóng, tiêu đề, mô tả, hai lựa chọn. Trả {hop, dong}. */
function dungHop(khiDong) {
  const u = ND.ui.popup;
  const dong = h("button", { type: "button", class: "lp-dong", "aria-label": u.nut_dong, onclick: khiDong }, bieuTuong("bd-x"));
  const hop = h("div", { class: "lp-popup", role: "dialog", "aria-modal": "true", "aria-labelledby": "lp-popup-tieu-de" }, dong,
    h("h2", { id: "lp-popup-tieu-de" }, u.tieu_de), h("p", { class: "mo-ta" }, u.mo_ta),
    h("div", { class: "lp-lua-chon-luoi" }, luaChonHuong1(), luaChonHuong2()));
  return { hop, dong };
}

/** Các phần tử bấm được trong hộp (theo thứ tự trên màn hình): nút đóng rồi các nút/liên kết chưa khóa. */
function phanTuBamDuoc(hop) {
  return [...hop.querySelectorAll("button:not([disabled]), a[href]")];
}

/** Phím trong popup: Esc đóng; Tab xoay vòng trong popup (không thoát ra trang phía sau). */
function xuLyPhim(e) {
  if (!POPUP.nen) return;
  if (e.key === "Escape") { e.preventDefault(); dongPopup(); return; }
  if (e.key !== "Tab" || !POPUP.canh.length) return;
  const dau = POPUP.canh[0], cuoi = POPUP.canh[POPUP.canh.length - 1], dang = document.activeElement;
  if (e.shiftKey && (dang === dau || !POPUP.canh.includes(dang))) { e.preventDefault(); cuoi.focus(); }
  else if (!e.shiftKey && (dang === cuoi || !POPUP.canh.includes(dang))) { e.preventDefault(); dau.focus(); }
}

/** Mở popup. moTu = nút đã bấm (để trả focus khi đóng); uuTien = "huong1" | "huong2" để focus đúng lựa chọn (không có thì focus nút đóng). */
function moPopup(moTu, uuTien) {
  if (POPUP.nen) return;
  const { hop, dong } = dungHop(dongPopup);
  const nen = h("div", { class: "lp-phu-nen", onclick: (e) => { if (e.target === nen) dongPopup(); } }, hop);
  POPUP.nen = nen; POPUP.moTu = moTu; POPUP.canh = phanTuBamDuoc(hop);
  POPUP.khiPhim = xuLyPhim;
  document.addEventListener("keydown", POPUP.khiPhim);
  document.body.append(nen);
  document.body.classList.add("lp-khoa-cuon");
  (POPUP.canh.find((n) => n.getAttribute("data-huong") === uuTien) || dong).focus();   // focus lựa chọn đã bấm từ thẻ; không có thì nút đóng
}

/** Đóng popup, gỡ lớp khóa cuộn và trả focus về nút đã mở. */
function dongPopup() {
  if (!POPUP.nen) return;
  document.removeEventListener("keydown", POPUP.khiPhim);
  POPUP.nen.remove();
  document.body.classList.remove("lp-khoa-cuon");
  const nut = POPUP.moTu;
  POPUP.nen = null; POPUP.moTu = null; POPUP.canh = [];
  if (nut && nut.focus) nut.focus();
}
