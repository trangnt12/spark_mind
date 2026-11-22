// Giao diện nghiên cứu SparkMind (JavaScript thuần).
// Mọi chữ hiển thị lấy từ /api/content/ui và /api/content/form-b.
// Câu trả lời chỉ giữ trong bộ nhớ trang (biến `tt`), KHÔNG lưu localStorage. localStorage chỉ giữ session_token.
// Không ghi console log dữ liệu cá nhân.
"use strict";

const KHOA_TOKEN = "sparkmind_session_token";
const TONG_BUOC = 6;
const LOP_CAN_NGUOI_LON = 7;   // mã A1 từ 1 đến 7 là lớp 6–12 (dưới 18 tuổi)
const CHUA_TUNG_DUNG = 4;      // mã A4 "Chưa bao giờ sử dụng"

// Trạng thái trong bộ nhớ: nội dung, mã, token, câu trả lời, giờ bắt đầu phần B
const tt = { ui: null, fb: null, ma: "", token: "", tl: {}, batDauB: 0, truong: [], daNop: { B: false, C: false } };
const goc = document.getElementById("man-hinh");

// ---------- Hàm nhỏ dùng chung ----------

/** Tạo phần tử HTML: h("div", {class: "the"}, con1, con2). Chữ luôn đặt bằng textContent (an toàn). */
function h(ten, thuocTinh = {}, ...con) {
  const e = document.createElement(ten);
  for (const [k, v] of Object.entries(thuocTinh)) {
    if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of con.flat()) e.append(c instanceof Node ? c : document.createTextNode(c));
  return e;
}

/** Gọi API. Mất mạng thì trả status 0 (không ném lỗi). */
async function goiApi(duongDan, thanBody) {
  try {
    const kq = await fetch(duongDan, thanBody === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(thanBody),
    });
    const du_lieu = await kq.json().catch(() => ({}));
    return { status: kq.status, du_lieu };
  } catch {
    return { status: 0, du_lieu: {} };
  }
}

/** Người dùng có bật "giảm chuyển động" không? Có thì tắt cuộn mượt, pháo giấy. */
function giamChuyenDong() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Biểu tượng SVG nhúng sẵn trong index.html (bd-logo, bd-tick, bd-x, bd-canh-bao). */
function bieuTuong(ten, lop = "") {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const dung = document.createElementNS("http://www.w3.org/2000/svg", "use");
  dung.setAttribute("href", "#" + ten);
  svg.setAttribute("aria-hidden", "true");
  if (lop) svg.setAttribute("class", lop);
  svg.append(dung);
  return svg;
}

/** Đổi sang một màn hình: cập nhật thanh tiến độ, chạy hiệu ứng trượt vào (250ms) rồi vẽ nội dung. */
function hienThi(buoc, ...nodes) {
  goc.replaceChildren(...nodes.flat());   // nodes có thể chứa mảng (vd. các đoạn mô tả)
  goc.classList.remove("vao");
  void goc.offsetWidth;                       // buộc trình duyệt chạy lại hiệu ứng
  goc.classList.add("vao");
  const phanTram = Math.round((buoc / TONG_BUOC) * 100);
  document.getElementById("thanh").style.width = phanTram + "%";
  document.querySelector(".tien-do").setAttribute("aria-valuenow", phanTram);
  document.getElementById("nhan-tien-do").textContent =
    tt.ui.chung.tien_do.replace("{b}", buoc).replace("{t}", TONG_BUOC);
  window.scrollTo(0, 0);
  goc.focus({ preventScroll: true });         // để người dùng bàn phím / đọc màn hình bắt đầu từ đầu màn mới
}

/** Chữ mô tả có nhiều dòng (ngăn bằng \n) thì tách thành các đoạn ngắn dễ đọc. */
function cacDoan(chu) {
  return chu.split("\n").map((d) => h("p", { class: "mo-ta" }, d));
}

/** Tiêu đề màn hình có emoji trang trí phía trên (emoji lấy từ research_ui.json). */
function tieuDe(khoa, chu) {
  return h("h1", {}, h("span", { class: "emo", "aria-hidden": "true" }, tt.ui.giao_dien.emoji[khoa] || ""), chu);
}

/** Nút "Quay lại" (nút phụ): về màn trước để đổi câu trả lời, câu đã chọn vẫn được giữ. */
function nutQuayLai(veMan) {
  return h("button", { type: "button", class: "phu quay-lai", onclick: veMan }, tt.ui.giao_dien.nut_quay_lai);
}

/** Thanh nút dính đáy màn hình: chứa hộp lỗi chung (nếu có) và nút chính. */
function khungNut(...con) {
  return h("div", { class: "thanh-nut" }, ...con);
}

// ---------- Động viên nhẹ: chỉ khen việc đã làm xong một phần, không nhận xét nội dung ----------

let demKhen = 0;

/** Pháo giấy nhẹ: các mảnh nhỏ bay lên rồi mờ dần (màu do CSS). */
function phaoGiay() {
  const lop = h("div", { class: "phao", "aria-hidden": "true" });
  for (let i = 0; i < 26; i++) {
    const m = h("i");
    m.style.cssText = `--dx:${Math.round(Math.random() * 300 - 150)}px;--dy:${Math.round(Math.random() * 220 + 20)}px;` +
      `--xoay:${Math.round(Math.random() * 720 - 360)}deg;--tre:${(Math.random() * 0.15).toFixed(2)}s`;
    lop.append(m);
  }
  document.body.append(lop);
  setTimeout(() => lop.remove(), 1500);
}

/** Hiện lời khen ngắn với dấu tick nảy khi xong một phần. Giảm chuyển động thì không có pháo giấy. */
function chucMung() {
  const ds = tt.ui.giao_dien.khen;
  const the = h("div", { class: "khen", role: "status" }, bieuTuong("bd-tick", "tick-nay"), ds[demKhen++ % ds.length]);
  document.body.append(the);
  if (!giamChuyenDong()) phaoGiay();
  setTimeout(() => the.remove(), 2400);
}

/** Báo khi mất mạng (câu trả lời vẫn giữ trong bộ nhớ trang); có mạng lại thì ẩn. */
function theoDoiMang() {
  const bang = h("div", { class: "mat-mang", role: "status" }, tt.ui.giao_dien.mat_mang);
  const capNhat = () => bang.classList.toggle("an", navigator.onLine);
  document.body.append(bang);
  window.addEventListener("online", capNhat);
  window.addEventListener("offline", capNhat);
  capNhat();
}

// ---------- Báo lỗi ngay cạnh câu thiếu ----------

/** Xóa mọi dấu lỗi cạnh câu hỏi (gọi trước mỗi lần kiểm tra). */
function xoaLoiCau() {
  goc.querySelectorAll(".loi-cau").forEach((e) => e.remove());
  goc.querySelectorAll(".thieu").forEach((e) => e.classList.remove("thieu"));
}

/** Tô đỏ câu có mã `id` và ghi dòng báo lỗi ngay bên dưới câu đó. */
function loiTai(id, chu) {
  const cau = document.getElementById("cau-" + id) || document.getElementById("hang-" + id);
  if (!cau || cau.querySelector(".loi-cau")) return;
  cau.classList.add("thieu");
  cau.append(h("p", { class: "loi-cau", role: "alert" }, bieuTuong("bd-canh-bao"), chu || tt.ui.giao_dien.cau_thieu));
}

/** Cuộn đến câu lỗi đầu tiên (cuộn mượt, hoặc nhảy thẳng nếu bật giảm chuyển động). */
function cuonDenLoi() {
  const dau = goc.querySelector(".thieu");
  if (dau) dau.scrollIntoView({ behavior: giamChuyenDong() ? "auto" : "smooth", block: "center" });
}

/** Hộp báo lỗi đỏ; gọi lại với chuỗi rỗng để xóa. */
function baoLoi(hop, chu) {
  hop.textContent = chu;
  hop.classList.toggle("an", !chu);
}

/** Đổi chữ lỗi từ máy chủ thành chữ trong research_ui.json. */
function chuLoi(status) {
  const l = tt.ui.loi;
  if (status === 0) return l.mat_ket_noi;
  if (status === 429) return l.bi_chan;
  if (status === 401) return tt.ui.chung.phien_het_han;
  if (status === 422) return l.thieu_cau;
  return tt.ui.chung.loi_khac;
}

// ---------- Ô câu hỏi (chọn một, chọn nhiều, lưới 1–5) ----------

/** Tên câu hỏi y nguyên trong form_b.json: số thứ tự + dấu cách + chữ, câu bắt buộc thêm dấu * đỏ. */
function tenCau(cau) {
  return [cau.nhan + " " + cau.text, cau.bat_buoc ? h("span", { class: "sao" }, " *") : ""];
}

/** Ô gõ chữ của lựa chọn "Mục khác:". Gõ chữ thì tự tích ô chọn; chữ gõ nhớ ở tt.tl[<id>_other]. */
function oGoKhac(cau, o, nhap) {
  const go = h("input", { type: "text", class: "o-khac", maxlength: 200, autocomplete: "off", "aria-label": o.text });
  go.value = tt.tl[cau.id + "_other"] || "";
  go.addEventListener("input", () => {
    tt.tl[cau.id + "_other"] = go.value;
    if (go.value && !nhap.checked) { nhap.checked = true; nhap.dispatchEvent(new Event("change", { bubbles: true })); }
  });
  return go;
}

/** Một lựa chọn (radio hoặc checkbox) nhớ vào tt.tl. */
function oLuaChon(cau, o, nhieu) {
  const nhap = h("input", { type: nhieu ? "checkbox" : "radio", name: cau.id, value: o.ma });
  const go = o.khac ? oGoKhac(cau, o, nhap) : null;
  const cu = tt.tl[cau.id];
  nhap.checked = nhieu ? (cu || []).includes(o.ma) : cu === o.ma;
  nhap.addEventListener("change", () => {
    if (!nhieu) tt.tl[cau.id] = o.ma;
    else tt.tl[cau.id] = [...goc.querySelectorAll(`input[name="${cau.id}"]:checked`)].map((x) => +x.value);
    // Chọn "Mục khác" thì đưa con trỏ vào ô gõ chữ (hoãn 0ms để không bị cú bấm nhãn giành lại focus)
    if (go && nhap.checked) setTimeout(() => go.focus(), 0);
  });
  return h("label", { class: "lua-chon" }, nhap, h("span", {}, o.text), go || "");
}

/** Câu chọn một hoặc chọn nhiều, theo mô tả trong form_b.json. */
function cauChon(cau, onChange) {
  const nhieu = cau.loai === "chon_nhieu";
  const khung = h("div", { class: "truong", id: "cau-" + cau.id },
    h("p", { class: "cau-hoi" }, tenCau(cau)),
    cau.huong_dan ? h("p", { class: "ghi-chu" }, cau.huong_dan) : "",
    h("div", { class: "ds-lua-chon" }, cau.options.map((o) => oLuaChon(cau, o, nhieu))));
  if (onChange) khung.addEventListener("change", onChange);
  return khung;
}

/** Lưới thang 1–5: mỗi dòng một phát biểu, 5 nút lớn. Có chú giải thang ở trên. */
function luoi(cacDong, cauLuoi) {
  const thang = tt.fb.thang_dong_y;
  const chuGiai = h("ul", { class: "chu-giai" }, Object.values(thang).map((chu) => h("li", {}, chu)));
  const hang = cacDong.map((d) => h("div", { class: "hang-luoi", id: "hang-" + d.id }, h("p", {}, d.nhan + " " + d.text),
    h("div", { class: "thang", role: "radiogroup", "aria-label": d.nhan + " " + d.text },
      Object.keys(thang).map((m) => oThang(d.id, +m, thang[m])))));
  return h("div", { class: "truong" }, h("p", { class: "cau-hoi" }, tenCau(cauLuoi)),
    h("p", { class: "ghi-chu" }, tt.fb.nhan_thang), chuGiai, hang);
}

/** Một nút số trong lưới (radio dạng nút). */
function oThang(id, muc, nhanThang) {
  const nhap = h("input", { type: "radio", name: id, value: muc, "aria-label": nhanThang });
  nhap.checked = tt.tl[id] === muc;
  nhap.addEventListener("change", () => { tt.tl[id] = muc; });
  return h("label", { class: "nut-so" }, nhap, String(muc));
}

/** Còn câu bắt buộc nào chưa trả lời không? (chọn nhiều thì phải có ít nhất 1).
 *  Nếu thiếu: tô đỏ và báo ngay cạnh từng câu thiếu, rồi cuộn đến câu thiếu đầu tiên. */
function thieuCau(cacId) {
  const thieu = cacId.filter((id) => {
    const v = tt.tl[id];
    return v == null || v === "" || (Array.isArray(v) && v.length === 0);
  });
  thieu.forEach((id) => loiTai(id));
  cuonDenLoi();
  return thieu.length > 0;
}

/** Nút gửi dùng chung: khóa nút khi đang gửi; mạng lỗi thì nút đổi thành "Thử lại". */
function nutGui(chu, xuLy, hopLoi) {
  const nut = h("button", { type: "button" }, chu);
  nut.addEventListener("click", async () => {
    nut.disabled = true;
    nut.classList.add("dang-tai");               // vòng xoay "đang gửi"
    nut.textContent = tt.ui.chung.dang_gui;
    baoLoi(hopLoi, "");
    xoaLoiCau();
    const kq = await xuLy();
    nut.disabled = false;
    nut.classList.remove("dang-tai");
    nut.textContent = kq === 0 ? tt.ui.chung.nut_thu_lai : chu;
  });
  return nut;
}

// ---------- Màn 1: chào và nhập mã ----------

function manMa() {
  const u = tt.ui.chao;
  const o = h("input", { type: "text", id: "o-ma", autocomplete: "off", autocapitalize: "characters", maxlength: 32 });
  const loi = h("div", { class: "loi an", role: "alert" });
  const nut = nutGui(u.nut, async () => {
    const ma = o.value.trim();
    if (!ma) return baoLoi(loi, tt.ui.loi.ma_sai);
    const kq = await goiApi("/api/research/code/check", { code: ma });
    if (kq.status !== 200) { baoLoi(loi, chuLoi(kq.status)); return kq.status; }
    if (!kq.du_lieu.valid) { baoLoi(loi, tt.ui.loi.ma_sai); return 200; }
    tt.ma = ma;
    manThongTin();
    return 200;
  }, loi);
  hienThi(1, h("div", { class: "hero" }, bieuTuong("bd-logo", "logo logo-lon"), h("h1", {}, u.tieu_de)),
    h("div", { class: "the the-chao" }, cacDoan(u.mo_ta), h("hr"),
      h("label", { class: "cau-hoi", for: "o-ma" }, u.nhan_o_ma), o, loi), khungNut(nut));
}

/** Máy đã có session_token đang dở thì hỏi có làm tiếp không. */
function manTiepTuc() {
  const u = tt.ui.tiep_tuc;
  const tiep = h("button", { type: "button", onclick: () => { tt.token = localStorage.getItem(KHOA_TOKEN); manB(); } }, u.nut_tiep);
  const moi = h("button", { type: "button", class: "phu", onclick: () => { localStorage.removeItem(KHOA_TOKEN); manMa(); } }, u.nut_moi);
  hienThi(1, tieuDe("tiep_tuc", u.tieu_de), cacDoan(u.mo_ta), khungNut(tiep, moi));
}

// ---------- Màn 2: thông tin và đồng ý ----------

/** Thu và kiểm tra thông tin màn 2. Trả về { body } hoặc { loi } (chữ lỗi). */
function thuThongTin() {
  const l = tt.ui.loi, t = tt.tl;
  tt.tl.email = (document.getElementById("o-email").value || "").trim();
  const canNguoiLon = t.A1 <= LOP_CAN_NGUOI_LON;
  const loi = [];                                  // gom mọi lỗi, mỗi lỗi hiện ngay cạnh ô của nó
  const ghi = (id, chu) => { loiTai(id, chu); loi.push(chu); };
  if (!/^\S+@\S+\.\S+$/.test(t.email)) ghi("email", tt.ui.chung.email_sai);
  if (thieuCau(["A1", "A2", "A3"])) loi.push(l.thieu_cau);
  if (!t.dongY) ghi("dongY", l.thieu_dong_y);
  if (canNguoiLon && !t.nguoiLon) ghi("nguoiLon", l.thieu_nguoi_lon);
  if (loi.length) { cuonDenLoi(); return { loi: loi[0] }; }
  return { body: { code: tt.ma, email: t.email, grade: t.A1, gender: t.A2, school_name: t.A3,
                   consent: true, guardian_consent: !!(canNguoiLon && t.nguoiLon) } };
}

/** Ô tích đồng ý (nhớ vào tt.tl[khoa]). */
function oTich(khoa, chu) {
  const nhap = h("input", { type: "checkbox" });
  nhap.checked = !!tt.tl[khoa];
  nhap.addEventListener("change", () => { tt.tl[khoa] = nhap.checked; });
  return h("div", { class: "truong", id: "cau-" + khoa }, h("label", { class: "lua-chon" }, nhap, h("span", {}, chu)));
}

/** Ô nhập chữ (email, tên trường) có nhớ giá trị đã gõ. */
function oChu(id, nhan, ghiChu, loai, khoa) {
  const o = h("input", { type: loai, id, autocomplete: "off" });
  o.value = tt.tl[khoa] || "";
  return h("div", { class: "truong", id: "cau-" + khoa }, h("label", { class: "cau-hoi", for: id }, nhan),
    ghiChu ? h("p", { class: "ghi-chu" }, ghiChu) : "", o);
}

// ---------- Ô chọn trường (có tìm kiếm, chỉ hiện trường đúng cấp với lớp đã chọn) ----------

/** Bỏ dấu và chuyển chữ thường để tìm không phân biệt dấu. */
function boDau(chu) {
  return chu.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").toLowerCase();
}

/** Cấp học của người dùng (THCS / THPT / Đại học) theo lớp A1; "cap" nằm trong form_b.json. */
function capHienTai() {
  const o = tt.fb.phan_a_thong_tin.find((c) => c.id === "A1").options.find((x) => x.ma === tt.tl.A1);
  return o ? o.cap : "";
}

/** Trường có đúng cấp không? Trường liên cấp hợp với cả THCS và THPT. */
function dungCap(t, cap) {
  return t.cap === cap || (t.cap === "Liên cấp" && (cap === "THCS" || cap === "THPT"));
}

/** Vẽ tối đa 50 trường đúng cấp và khớp từ khóa; cuối danh sách luôn có dòng "Khác". */
function veDanhSach(ds, tuKhoa, chon) {
  const k = boDau(tuKhoa.trim()), cap = capHienTai();
  const kq = tt.truong.filter((t) => dungCap(t, cap) && boDau(t.ten + " " + t.vt).includes(k)).slice(0, 50);
  const dong = kq.map((t) => {
    const li = h("li", { class: "dong-truong" }, t.ten, h("small", {}, " · " + (t.vt ? t.vt + " · " : "") + t.cap));
    li.addEventListener("mousedown", (e) => { e.preventDefault(); chon(t); });
    return li;
  });
  const khac = h("li", { class: "dong-khac" }, tt.ui.thong_tin.truong_khac);
  khac.addEventListener("mousedown", (e) => { e.preventDefault(); chon(null); });
  ds.replaceChildren(...dong, khac);
  ds.classList.remove("an");
}

/** Ô chọn trường: bấm vào để tìm và chọn; chọn xong tên hiện ngay trong ô. Chọn "Khác" thì ô thành ô nhập tay.
 *  Tên lưu vào tt.tl.A3 (chỉ trong bộ nhớ). */
function oChonTruong(cau) {
  const u = tt.ui.thong_tin;
  const o = h("input", { type: "text", id: "o-truong", autocomplete: "off", value: tt.tl.A3 || "" });
  const ds = h("ul", { class: "ds-truong an" });
  const lai = h("button", { type: "button", class: "phu nho an" }, u.quay_lai_ds);
  const vao = (khac) => {                      // chuyển giữa "chọn trong danh sách" và "nhập tay"
    tt.tl.truongKhac = khac; ds.classList.add("an"); lai.classList.toggle("an", !khac);
    o.placeholder = khac ? u.nhan_truong_khac : (capHienTai() ? u.tim_truong : u.chon_lop_truoc);
    o.disabled = !khac && !capHienTai();
  };
  const chon = (t) => {
    if (!t) { tt.tl.A3 = ""; o.value = ""; vao(true); o.focus(); return; }
    tt.tl.A3 = t.ten; o.value = t.ten; ds.classList.add("an"); o.blur();
  };
  o.addEventListener("focus", () => { if (!tt.tl.truongKhac) { o.select(); veDanhSach(ds, "", chon); } });
  o.addEventListener("input", () => {
    if (tt.tl.truongKhac) tt.tl.A3 = o.value.trim(); else veDanhSach(ds, o.value, chon);
  });
  o.addEventListener("blur", () => { ds.classList.add("an"); if (!tt.tl.truongKhac) o.value = tt.tl.A3 || ""; });
  lai.addEventListener("click", () => { tt.tl.A3 = ""; o.value = ""; vao(false); o.focus(); });
  const khung = h("div", { class: "truong", id: "cau-A3" }, h("label", { class: "cau-hoi", for: "o-truong" }, tenCau(cau)),
    cau.huong_dan ? h("p", { class: "ghi-chu" }, cau.huong_dan) : "",
    h("div", { class: "hop-tim" }, o, ds), lai);
  /** Gọi khi người dùng đổi lớp: xóa trường đã chọn (có thể sai cấp) và quay về chọn trong danh sách. */
  khung.capNhat = () => { tt.tl.A3 = ""; o.value = ""; vao(false); };
  vao(!!tt.tl.truongKhac);
  return khung;
}

function manThongTin(sua = false) {
  const u = tt.ui, a = Object.fromEntries(tt.fb.phan_a_thong_tin.map((c) => [c.id, c]));
  const loi = h("div", { class: "loi an", role: "alert" });
  const hopNguoiLon = h("div", { id: "hop-nguoi-lon" }, oTich("nguoiLon", u.dong_y.o_nguoi_lon));
  const truong = oChonTruong(a.A3);
  const hienNguoiLon = () => hopNguoiLon.classList.toggle("an", !(tt.tl.A1 <= LOP_CAN_NGUOI_LON));
  let capCu = capHienTai();
  const capNhatNguoiLon = () => {               // đổi lớp: chỉ xóa trường đã chọn khi đổi sang cấp học khác
    hienNguoiLon();
    if (capHienTai() !== capCu) { capCu = capHienTai(); truong.capNhat(); }
  };
  const phanA = [cauChon(a.A1, capNhatNguoiLon), cauChon(a.A2), truong];
  if (sua) return manSuaThongTin(phanA, hopNguoiLon, loi, hienNguoiLon);
  const nut = nutGui(u.dong_y.nut, () => guiBatDau(thuThongTin(), loi), loi);
  hienThi(2, tieuDe("dong_y", u.dong_y.tieu_de),
    h("div", { class: "the" }, u.dong_y.doan.map((d) => h("p", { class: "mo-ta" }, d))),
    h("div", { class: "the" }, h("h2", {}, tt.fb.tieu_de), h("p", { class: "mo-ta" }, tt.fb.mo_ta),
      h("h2", {}, tt.fb.tieu_de_phan.A),
      oChu("o-email", u.thong_tin.nhan_email, u.thong_tin.ghi_chu_email, "email", "email"), phanA),
    h("div", { class: "the" }, oTich("dongY", u.dong_y.o_dong_y), hopNguoiLon), khungNut(loi, nut));
  hienNguoiLon();
}

/** Màn sửa phần A (sau khi bấm Quay lại từ form B): chỉ lớp, giới tính, trường; không hỏi lại email và đồng ý. */
function manSuaThongTin(phanA, hopNguoiLon, loi, hienNguoiLon) {
  const nut = nutGui(tt.ui.giao_dien.nut_luu, () => guiSuaThongTin(thuSuaThongTin(), loi), loi);
  hienThi(2, h("div", { class: "the" }, h("h2", {}, tt.fb.tieu_de_phan.A), phanA, hopNguoiLon),
    khungNut(loi, nut, nutQuayLai(manB)));
  hienNguoiLon();
}

/** Thu phần A khi sửa. Trả về { body } hoặc { loi }. */
function thuSuaThongTin() {
  const t = tt.tl, canNguoiLon = t.A1 <= LOP_CAN_NGUOI_LON;
  if (thieuCau(["A1", "A2", "A3"])) return { loi: tt.ui.loi.thieu_cau };
  if (canNguoiLon && !t.nguoiLon) { loiTai("nguoiLon", tt.ui.loi.thieu_nguoi_lon); cuonDenLoi(); return { loi: tt.ui.loi.thieu_nguoi_lon }; }
  return { body: { session_token: tt.token, grade: t.A1, gender: t.A2, school_name: t.A3,
                   guardian_consent: !!(canNguoiLon && t.nguoiLon) } };
}

async function guiSuaThongTin(kq, hopLoi) {
  if (kq.loi) { baoLoi(hopLoi, kq.loi); return 200; }
  const r = await goiApi("/api/research/info/update", kq.body);
  if (r.status !== 200) { loiPhien(hopLoi, r.status); return r.status; }
  manB();
  return 200;
}

/** Gọi /start. Thành công thì lưu session_token (chỉ token) và sang form B. */
async function guiBatDau(kq, hopLoi) {
  if (kq.loi) { baoLoi(hopLoi, kq.loi); return 200; }
  const r = await goiApi("/api/research/start", kq.body);
  if (r.status === 409) { baoLoi(hopLoi, tt.ui.loi.ma_sai); return 409; }
  if (r.status !== 200) { baoLoi(hopLoi, chuLoi(r.status)); return r.status; }
  tt.token = r.du_lieu.session_token;
  localStorage.setItem(KHOA_TOKEN, tt.token);
  manB();
  chucMung();
  return 200;
}

// ---------- Màn 3: form B ----------

/** Phần B (B1–B7): chỉ hiện khi A4 không phải "Chưa bao giờ". */
function phanB(cauB) {
  const theo = (id) => cauB.find((c) => c.id === id);
  const b4 = theo("B4");
  return h("div", { id: "phan-b" }, h("h2", {}, tt.fb.tieu_de_phan.B), ["B1", "B2", "B3"].map((id) => cauChon(theo(id))),
    luoi(b4.cac_dong, b4), ["B5", "B6", "B7"].map((id) => cauChon(theo(id))));
}

/** Đã chọn "Mục khác:" ở câu nào mà để trống ô gõ chữ thì trả về true (bắt người dùng nhập). */
function thieuMucKhac(ids) {
  const thieu = ids.filter((id) => {
    const cau = tt.fb.phan_b_hanh_vi.find((c) => c.id === id);
    const ma = cau.options.find((o) => o.khac).ma, v = tt.tl[id];
    return (Array.isArray(v) ? v.includes(ma) : v === ma) && !(tt.tl[id + "_other"] || "").trim();
  });
  thieu.forEach((id) => loiTai(id, tt.ui.loi.thieu_muc_khac));
  cuonDenLoi();
  return thieu.length > 0;
}

/** Thu câu trả lời form B thành body gửi /behavior. Trả về { body } hoặc { loi }. */
function thuHanhVi() {
  const t = tt.tl, boQuaB = t.A4 === CHUA_TUNG_DUNG;
  const ids = ["B1", "B2", "B3", "B4_1", "B4_2", "B4_3", "B4_4", "B4_5", "B4_6", "B4_7", "B5", "B6", "B7"];
  if (thieuCau(boQuaB ? ["A4"] : ["A4", ...ids])) return { loi: tt.ui.loi.thieu_cau };
  if (!boQuaB && thieuMucKhac(["B1", "B3", "B6"])) return { loi: tt.ui.loi.thieu_muc_khac };
  const body = { session_token: tt.token, A4: t.A4, duration_sec: Math.round((Date.now() - tt.batDauB) / 1000) };
  if (!boQuaB) ids.forEach((id) => { body[id] = t[id]; });
  if (!boQuaB) ["B1", "B3", "B6"].forEach((id) => { body[id + "_other"] = (t[id + "_other"] || "").trim(); });  // chữ ở "Mục khác:"
  return { body };
}

async function guiHanhVi(kq, hopLoi) {
  if (kq.loi) { baoLoi(hopLoi, kq.loi); return 200; }
  const r = await goiApi("/api/research/behavior", { ...kq.body, edit: tt.daNop.B });   // đã nộp rồi thì lần này là sửa
  if (r.status === 409) { manC(); return 409; }          // đã nộp phần này rồi: đi tiếp
  if (r.status !== 200) { loiPhien(hopLoi, r.status); return r.status; }
  manC();
  if (!tt.daNop.B) chucMung();                           // chỉ khen lần hoàn thành đầu, không khen lúc sửa
  tt.daNop.B = true;
  return 200;
}

/** Lỗi 401 (phiên hỏng) thì xóa token và về màn nhập mã; lỗi khác chỉ báo chữ. */
function loiPhien(hopLoi, status) {
  baoLoi(hopLoi, chuLoi(status));
  if (status === 401) { localStorage.removeItem(KHOA_TOKEN); setTimeout(manMa, 2500); }
}

function manB() {
  const u = tt.ui.form_b, cauB = tt.fb.phan_b_hanh_vi;
  const a4 = tt.fb.phan_a_thong_tin.find((c) => c.id === "A4");
  const loi = h("div", { class: "loi an", role: "alert" });
  const hopB = phanB(cauB);
  const capNhat = () => hopB.classList.toggle("an", tt.tl.A4 === CHUA_TUNG_DUNG);
  if (!tt.batDauB) tt.batDauB = Date.now();   // bắt đầu tính giờ làm bài
  const nut = nutGui(u.nut, () => guiHanhVi(thuHanhVi(), loi), loi);
  hienThi(3, h("div", { class: "the" }, cauChon(a4, capNhat), hopB), khungNut(loi, nut, nutQuayLai(() => manThongTin(true))));
  capNhat();
}

// ---------- Màn 4: form C ----------

function thuTuDanhGia() {
  const ids = ["C1", "C2", "C3", "C4", "C5", "C6"];
  if (thieuCau(ids)) return { loi: tt.ui.loi.thieu_cau };
  const body = { session_token: tt.token };
  ids.forEach((id) => { body[id] = tt.tl[id]; });
  return { body };
}

async function guiTuDanhGia(kq, hopLoi) {
  if (kq.loi) { baoLoi(hopLoi, kq.loi); return 200; }
  const r = await goiApi("/api/research/self-assessment", { ...kq.body, edit: tt.daNop.C });
  if (r.status !== 200 && r.status !== 409) { loiPhien(hopLoi, r.status); return r.status; }
  manGioiThieu();
  if (!tt.daNop.C) chucMung();
  tt.daNop.C = true;
  return 200;
}

function manC() {
  const u = tt.ui.form_c, cauC = tt.fb.phan_c_tu_danh_gia;
  const loi = h("div", { class: "loi an", role: "alert" });
  const nut = nutGui(u.nut, () => guiTuDanhGia(thuTuDanhGia(), loi), loi);
  hienThi(4, h("div", { class: "the" }, h("h2", {}, tt.fb.tieu_de_phan.C),
    luoi(cauC.filter((c) => c.id !== "C6"), tt.fb.c_luoi),
      cauChon(cauC.find((c) => c.id === "C6"))), khungNut(loi, nut, nutQuayLai(manB)));
}

// ---------- Màn 5: giới thiệu và game 1 (file game1.js). Màn 6: tạm thời (game 2 và 3 làm sau) ----------

function manChuaXong() {
  const u = tt.ui.chua_xong;
  hienThi(6, tieuDe("chua_xong", u.tieu_de), cacDoan(u.mo_ta));
}

// ---------- Khởi động ----------

/** Người dùng trả lời câu đang báo lỗi thì bỏ dấu lỗi của câu đó. */
function boDauLoi(e) {
  const cau = e.target.closest(".thieu");
  if (!cau) return;
  cau.classList.remove("thieu");
  cau.querySelectorAll(".loi-cau").forEach((x) => x.remove());
}

async function khoiDong() {
  const [ui, fb, tr] = await Promise.all([goiApi("/api/content/ui"), goiApi("/api/content/form-b"), goiApi("/api/content/schools")]);
  if (ui.status !== 200 || fb.status !== 200 || tr.status !== 200) {
    goc.textContent = "Không tải được nội dung. Bạn tải lại trang sau vài giây.";  // chưa có chữ từ máy chủ nên chỉ dòng này viết sẵn
    return;
  }
  tt.ui = ui.du_lieu;
  tt.fb = fb.du_lieu;
  tt.truong = tr.du_lieu;
  document.title = tt.ui.ten_he_thong;
  document.getElementById("ten-he-thong").textContent = tt.ui.ten_he_thong;
  goc.addEventListener("change", boDauLoi);
  goc.addEventListener("input", boDauLoi);
  theoDoiMang();
  if (localStorage.getItem(KHOA_TOKEN)) manTiepTuc(); else manMa();
}

khoiDong();
