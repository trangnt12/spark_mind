// Hiệu ứng cho trang chủ "/" (JavaScript thuần). Chỉ THÊM class để chạy hiệu ứng, không đổi chữ hay logic.
// Nguyên tắc: mặc định mọi khối đều hiện; JS lỗi hoặc bật "giảm chuyển động" thì trang vẫn đọc đủ.
"use strict";

const DICH_CHUYEN = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
const MUC_HIEN = ".lp-khoi:not(.lp-mo-dau) .lp-trong > :is(h2, .lp-dan, .lp-tieu-de-nho, .lp-luu-y, p, a, .lp-ds-tick, .lp-khien), .lp-khoi:not(.lp-mo-dau) .lp-the, .lp-buoc, .lp-cau-hd, .lp-chan .lp-trong > p";
const HD = { daCai: false, dau: null, tien: null, len: null };

/** Mỗi phần tử hiện ra MỘT lần khi cuộn tới; thứ tự trong cùng khối lệch nhau 70ms (--tre). */
function hienKhiCuon() {
  const cacMuc = [...document.querySelectorAll(MUC_HIEN)];
  const dem = new Map();
  const io = new IntersectionObserver((ds) => ds.forEach((d) => {
    if (!d.isIntersecting) return;
    d.target.classList.replace("hd-an", "hd-hien");
    io.unobserve(d.target);
  }), { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
  cacMuc.forEach((e) => {
    const k = dem.get(e.parentElement) || 0;
    dem.set(e.parentElement, k + 1);
    e.style.setProperty("--tre", Math.min(k, 5) * 70 + "ms");
    e.querySelectorAll(".tick").forEach((t, j) => t.style.setProperty("--k", j));
    e.classList.add("hd-an");
    io.observe(e);
  });
}

/** Mục menu đang xem sáng lên (scrollspy) và bước quy trình đang ở giữa màn hình sáng lên. */
function theoDoiVung() {
  const lienKet = new Map([...document.querySelectorAll(".lp-menu a[href^='#']")].map((a) => [a.getAttribute("href").slice(1), a]));
  const io = new IntersectionObserver((ds) => ds.forEach((d) => {
    const a = lienKet.get(d.target.id);
    if (!a) return;
    a.classList.toggle("dang-xem", d.isIntersecting);
    if (d.isIntersecting) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
  }), { rootMargin: "-40% 0px -55% 0px" });
  lienKet.forEach((a, id) => { const k = document.getElementById(id); if (k) io.observe(k); });
  const buoc = new IntersectionObserver((ds) => ds.forEach((d) => d.target.classList.toggle("sang", d.isIntersecting)), { rootMargin: "-45% 0px -45% 0px" });
  document.querySelectorAll(".lp-buoc").forEach((b) => buoc.observe(b));
}

/** Cuộn trang: header thu nhỏ + đổ bóng, thanh tiến độ mảnh ở đỉnh, nút lên đầu trang (mỗi khung hình chỉ cập nhật một lần). */
function khiCuon() {
  const y = window.scrollY, cao = document.documentElement.scrollHeight - window.innerHeight;
  HD.dau.classList.toggle("cuon", y > 16);
  HD.tien.style.transform = "scaleX(" + (cao > 0 ? Math.min(1, y / cao) : 0).toFixed(4) + ")";
  HD.len.classList.toggle("hien", y > 600);
}

/** Dựng thanh tiến độ + nút lên đầu trang (trang trí, không có chữ mới; bàn phím dùng phím Home). Chỉ chạy một lần. */
function caiToanCuc() {
  if (HD.daCai) return;
  HD.daCai = true;
  HD.dau = document.getElementById("dau-trang");
  HD.tien = h("div", { class: "lp-tien-do", "aria-hidden": "true" });
  HD.len = h("button", { type: "button", class: "lp-len-dau", tabindex: "-1", "aria-hidden": "true", onclick: () => window.scrollTo({ top: 0, behavior: DICH_CHUYEN ? "auto" : "smooth" }) }, bieuTuong("bd-len"));
  document.body.append(HD.tien, HD.len);
  let cho = false;
  window.addEventListener("scroll", () => { if (!cho) { cho = true; requestAnimationFrame(() => { cho = false; khiCuon(); }); } }, { passive: true });
  khiCuon();
}

/** Gọi sau mỗi lần landing.js dựng lại trang. Không có IntersectionObserver hoặc giảm chuyển động: bỏ hiệu ứng hiện dần. */
function hieuUngTrang() {
  caiToanCuc();
  if (!("IntersectionObserver" in window)) return;
  theoDoiVung();
  if (DICH_CHUYEN) return;
  document.documentElement.classList.add("hd");
  hienKhiCuon();
}
