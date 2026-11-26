// DOM giả tối thiểu (không cần jsdom) để chạy web/landing*.js và web/huong1.js trong node.
// Dùng: const { taoMoiTruong } = require("./fake_dom"); const m = taoMoiTruong({ ids: [...], api: {...} });
class Goc {}                                   // lớp gốc để `instanceof Node` trong mã trang hoạt động

class Nut extends Goc {
  constructor(ten, moiTruong) {
    super();
    this.tag = ten; this.attrs = {}; this.kids = []; this.on = {}; this._text = ""; this.value = ""; this.parentNode = null; this.mt = moiTruong;
    this.classList = {
      toggle: (c, b) => { const s = new Set((this.attrs.class || "").split(" ").filter(Boolean)); if (b === undefined ? !s.has(c) : b) s.add(c); else s.delete(c); this.attrs.class = [...s].join(" "); },
      add: (c) => this.classList.toggle(c, true), remove: (c) => this.classList.toggle(c, false),
      contains: (c) => (this.attrs.class || "").split(" ").includes(c),
    };
  }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  addEventListener(e, f) { (this.on[e] = this.on[e] || []).push(f); }
  dispatch(e, ev = {}) { (this.on[e] || []).forEach((f) => f({ target: this, preventDefault() {}, ...ev })); }
  click() { this.dispatch("click"); }
  append(...c) { c.forEach((k) => { if (k.parentNode !== undefined) k.parentNode = this; }); this.kids.push(...c); }
  replaceChildren(...c) { this.kids = []; this.append(...c); }
  remove() { if (this.parentNode) this.parentNode.kids = this.parentNode.kids.filter((k) => k !== this); this.parentNode = null; }
  focus() { this.mt.document.activeElement = this; }
  get disabled() { return "disabled" in this.attrs; }
  set textContent(v) { this._text = v; this.kids = []; }
  get textContent() { return this._text + this.kids.map((k) => k.textContent).join(""); }
  get hidden() { return /(^| )an( |$)/.test(this.attrs.class || ""); }
  find(f, kq = []) { if (f(this)) kq.push(this); this.kids.forEach((k) => k.find && k.find(f, kq)); return kq; }
  /** Chỉ hiểu các bộ chọn đơn giản mã trang dùng: "button:not([disabled]), a[href]". */
  querySelectorAll(sel) {
    const khop = (n) => (n.tag === "button" && !n.disabled && sel.includes("button")) || (n.tag === "a" && n.hasAttribute("href") && sel.includes("a[href]"));
    return this.find((n) => n !== this && khop(n));
  }
}

class Chu extends Goc { constructor(t) { super(); this.textContent = t; } }

/** Tạo môi trường toàn cục giả. ids: danh sách id có sẵn trong HTML khung. api: {đường dẫn: {status, body}}. */
function taoMoiTruong({ ids, api }) {
  const mt = { api, phim: {}, luuLocal: {}, luuSession: {}, ham: {}, cuonDen: [] };
  const theo = {};
  ids.forEach((i) => { theo[i] = new Nut({ "dau-trang": "header", "chan-trang": "footer", "man-hinh": "main" }[i] || "div", mt); });
  const body = new Nut("body", mt);
  mt.document = {
    getElementById: (i) => theo[i], createElement: (t) => new Nut(t, mt), createTextNode: (t) => new Chu(t), createElementNS: (_, t) => new Nut(t, mt),
    body, activeElement: null, title: "",
    addEventListener: (e, f) => { (mt.phim[e] = mt.phim[e] || []).push(f); },
    removeEventListener: (e, f) => { mt.phim[e] = (mt.phim[e] || []).filter((x) => x !== f); },
  };
  const kho = (get) => ({ getItem: (k) => (k in get() ? get()[k] : null), setItem: (k, v) => { get()[k] = String(v); }, removeItem: (k) => { delete get()[k]; } });
  Object.assign(global, {
    Node: Goc, document: mt.document, location: { hash: "", href: "" },
    localStorage: kho(() => mt.luuLocal), sessionStorage: kho(() => mt.luuSession),
    window: { scrollTo() {}, addEventListener: (e, f) => { mt.ham[e] = f; } },
    fetch: async (url) => { const r = mt.api[url]; if (!r) throw new Error("không có " + url); return { status: r.status, json: async () => r.body }; },
  });
  mt.nho = () => new Promise((r) => setTimeout(r, 20));
  mt.phat = (ten, ev) => (mt.phim[ten] || []).forEach((f) => f({ preventDefault() {}, ...ev }));   // bắn sự kiện lên document
  mt.theo = theo;
  return mt;
}

/** Thu thập kết quả kiểm tra: kiem(dieuKien, ten); ketThuc() in lỗi và thoát mã 1 nếu có. */
function boKiem() {
  const loi = [];
  return {
    kiem: (dk, ten) => { if (!dk) loi.push(ten); },
    ketThuc: () => { if (loi.length) { console.error("SAI:\n- " + loi.join("\n- ")); process.exit(1); } console.log("ok"); },
  };
}

module.exports = { Nut, taoMoiTruong, boKiem };
