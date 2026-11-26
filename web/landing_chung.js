// Hàm dùng chung của trang chủ "/" và trang "/huong-1" (JavaScript thuần, không thư viện).
// Mọi chữ lấy từ /api/content/landing (content/landing_ui.json).
"use strict";

const KHOA_TOKEN = "sparkmind_session_token";   // phải giống app.js

/** Tạo phần tử HTML: h("div", {class: "the"}, con1, con2). Chữ luôn đặt bằng textContent/text node (an toàn, không chèn HTML). */
function h(ten, thuocTinh = {}, ...con) {
  const e = document.createElement(ten);
  for (const [k, v] of Object.entries(thuocTinh)) {
    if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of con.flat(Infinity)) if (c != null && c !== false) e.append(c instanceof Node ? c : document.createTextNode(c));
  return e;
}

/** Gọi API; mất mạng thì trả status 0 (không ném lỗi). */
async function goiApi(duongDan) {
  try {
    const kq = await fetch(duongDan);
    return { status: kq.status, du_lieu: await kq.json().catch(() => ({})) };
  } catch { return { status: 0, du_lieu: {} }; }
}

/** Chỉ nhận địa chỉ http(s): chặn "javascript:" và các kiểu lạ nếu ai đó gõ nhầm vào file nội dung. */
function diaChiHopLe(url) {
  return typeof url === "string" && /^https?:\/\/\S+$/i.test(url.trim());
}

/** Có bài làm hướng 2 dở dang trên máy này không (token do app.js lưu)? */
function coBaiDo() {
  try { return !!localStorage.getItem(KHOA_TOKEN); } catch { return false; }
}

/** Biểu tượng SVG lấy từ bộ nhúng sẵn trong trang (<symbol id="bd-...">). */
function bieuTuong(ten, lop = "") {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const dung = document.createElementNS("http://www.w3.org/2000/svg", "use");
  dung.setAttribute("href", "#" + ten);
  svg.setAttribute("aria-hidden", "true");
  if (lop) svg.setAttribute("class", lop);
  svg.append(dung);
  return svg;
}

/** Dải banner đầu trang giới thiệu: logo trong vòng tròn và tiêu đề (cùng kiểu màn chào hướng 2). */
function banner(chu) {
  const vong = h("div", { class: "bieu-tuong", "aria-hidden": "true" }, h("div", { class: "nghieng" }, bieuTuong("bd-logo", "logo logo-lon")));
  return h("div", { class: "banner" }, vong, h("h1", {}, chu));
}

/** Một dòng mô tả: emoji đầu dòng nằm trong "bong bóng" tròn (giống app.js). */
function dongMoTa(chu) {
  const m = chu.match(/^(\p{Extended_Pictographic}\uFE0F?)\s*([\s\S]*)$/u);
  if (!m) return h("p", { class: "mo-ta" }, chu);
  return h("p", { class: "mo-ta dong-mo-ta" }, h("span", { class: "bong", "aria-hidden": "true" }, m[1]), h("span", {}, m[2]));
}
