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
const tt = { ui: null, fb: null, ma: "", token: "", tl: {}, batDauB: 0, truong: [] };
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

/** Đổi sang một màn hình: cập nhật thanh tiến độ rồi vẽ nội dung. */
function hienThi(buoc, ...nodes) {
  goc.replaceChildren(...nodes);
  const phanTram = Math.round((buoc / TONG_BUOC) * 100);
  document.getElementById("thanh").style.width = phanTram + "%";
  document.getElementById("nhan-tien-do").textContent =
    tt.ui.chung.tien_do.replace("{b}", buoc).replace("{t}", TONG_BUOC);
  window.scrollTo(0, 0);
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
  const cu = tt.tl[cau.id];
  nhap.checked = nhieu ? (cu || []).includes(o.ma) : cu === o.ma;
  nhap.addEventListener("change", () => {
    if (!nhieu) tt.tl[cau.id] = o.ma;
    else tt.tl[cau.id] = [...goc.querySelectorAll(`input[name="${cau.id}"]:checked`)].map((x) => +x.value);
  });
  return h("label", { class: "lua-chon" }, nhap, h("span", {}, o.text), o.khac ? oGoKhac(cau, o, nhap) : "");
}

/** Câu chọn một hoặc chọn nhiều, theo mô tả trong form_b.json. */
function cauChon(cau, onChange) {
  const nhieu = cau.loai === "chon_nhieu";
  const khung = h("div", { class: "truong", id: "cau-" + cau.id },
    h("p", { class: "cau-hoi" }, tenCau(cau)),
    cau.huong_dan ? h("p", { class: "ghi-chu" }, cau.huong_dan) : "",
    cau.options.map((o) => oLuaChon(cau, o, nhieu)));
  if (onChange) khung.addEventListener("change", onChange);
  return khung;
}

/** Lưới thang 1–5: mỗi dòng một phát biểu, 5 nút lớn. Có chú giải thang ở trên. */
function luoi(cacDong, cauLuoi) {
  const thang = tt.fb.thang_dong_y;
  const chuGiai = h("ul", { class: "chu-giai" }, Object.values(thang).map((chu) => h("li", {}, chu)));
  const hang = cacDong.map((d) => h("div", { class: "hang-luoi" }, h("p", {}, d.nhan + " " + d.text),
    h("div", { class: "thang" }, Object.keys(thang).map((m) => oThang(d.id, +m)))));
  return h("div", { class: "truong" }, h("p", { class: "cau-hoi" }, tenCau(cauLuoi)), chuGiai, hang);
}

/** Một nút số trong lưới (radio dạng nút). */
function oThang(id, muc) {
  const nhap = h("input", { type: "radio", name: id, value: muc });
  nhap.checked = tt.tl[id] === muc;
  nhap.addEventListener("change", () => { tt.tl[id] = muc; });
  return h("label", {}, nhap, String(muc));
}

/** Còn câu bắt buộc nào chưa trả lời không? (chọn nhiều thì phải có ít nhất 1). */
function thieuCau(cacId) {
  return cacId.some((id) => {
    const v = tt.tl[id];
    return v == null || v === "" || (Array.isArray(v) && v.length === 0);
  });
}

/** Nút gửi dùng chung: khóa nút khi đang gửi; mạng lỗi thì nút đổi thành "Thử lại". */
function nutGui(chu, xuLy, hopLoi) {
  const nut = h("button", { type: "button" }, chu);
  nut.addEventListener("click", async () => {
    nut.disabled = true;
    nut.textContent = tt.ui.chung.dang_gui;
    baoLoi(hopLoi, "");
    const kq = await xuLy();
    nut.disabled = false;
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
  hienThi(1, h("h1", {}, u.tieu_de), h("p", { class: "mo-ta" }, u.mo_ta),
    h("div", { class: "the" }, h("label", { class: "cau-hoi", for: "o-ma" }, u.nhan_o_ma), o, loi, nut));
}

/** Máy đã có session_token đang dở thì hỏi có làm tiếp không. */
function manTiepTuc() {
  const u = tt.ui.tiep_tuc;
  const tiep = h("button", { type: "button", onclick: () => { tt.token = localStorage.getItem(KHOA_TOKEN); manB(); } }, u.nut_tiep);
  const moi = h("button", { type: "button", class: "phu", onclick: () => { localStorage.removeItem(KHOA_TOKEN); manMa(); } }, u.nut_moi);
  hienThi(1, h("h1", {}, u.tieu_de), h("p", { class: "mo-ta" }, u.mo_ta), tiep, moi);
}

// ---------- Màn 2: thông tin và đồng ý ----------

/** Thu và kiểm tra thông tin màn 2. Trả về { body } hoặc { loi } (chữ lỗi). */
function thuThongTin() {
  const l = tt.ui.loi, t = tt.tl;
  tt.tl.email = (document.getElementById("o-email").value || "").trim();
  if (!/^\S+@\S+\.\S+$/.test(t.email)) return { loi: tt.ui.chung.email_sai };
  if (thieuCau(["A1", "A2", "A3"])) return { loi: l.thieu_cau };
  if (!t.dongY) return { loi: l.thieu_dong_y };
  const canNguoiLon = t.A1 <= LOP_CAN_NGUOI_LON;
  if (canNguoiLon && !t.nguoiLon) return { loi: l.thieu_nguoi_lon };
  return { body: { code: tt.ma, email: t.email, grade: t.A1, gender: t.A2, school_name: t.A3,
                   consent: true, guardian_consent: !!(canNguoiLon && t.nguoiLon) } };
}

/** Ô tích đồng ý (nhớ vào tt.tl[khoa]). */
function oTich(khoa, chu) {
  const nhap = h("input", { type: "checkbox" });
  nhap.checked = !!tt.tl[khoa];
  nhap.addEventListener("change", () => { tt.tl[khoa] = nhap.checked; });
  return h("label", { class: "lua-chon" }, nhap, h("span", {}, chu));
}

/** Ô nhập chữ (email, tên trường) có nhớ giá trị đã gõ. */
function oChu(id, nhan, ghiChu, loai, khoa) {
  const o = h("input", { type: loai, id, autocomplete: "off" });
  o.value = tt.tl[khoa] || "";
  return h("div", { class: "truong" }, h("label", { class: "cau-hoi", for: id }, nhan),
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
  const khung = h("div", { class: "truong" }, h("label", { class: "cau-hoi", for: "o-truong" }, tenCau(cau)),
    cau.huong_dan ? h("p", { class: "ghi-chu" }, cau.huong_dan) : "",
    h("div", { class: "hop-tim" }, o, ds), lai);
  /** Gọi khi người dùng đổi lớp: xóa trường đã chọn (có thể sai cấp) và quay về chọn trong danh sách. */
  khung.capNhat = () => { tt.tl.A3 = ""; o.value = ""; vao(false); };
  vao(!!tt.tl.truongKhac);
  return khung;
}

function manThongTin() {
  const u = tt.ui, a = Object.fromEntries(tt.fb.phan_a_thong_tin.map((c) => [c.id, c]));
  const loi = h("div", { class: "loi an", role: "alert" });
  const hopNguoiLon = h("div", { id: "hop-nguoi-lon" }, oTich("nguoiLon", u.dong_y.o_nguoi_lon));
  const truong = oChonTruong(a.A3);
  const capNhatNguoiLon = () => { hopNguoiLon.classList.toggle("an", !(tt.tl.A1 <= LOP_CAN_NGUOI_LON)); truong.capNhat(); };
  const nut = nutGui(u.dong_y.nut, () => guiBatDau(thuThongTin(), loi), loi);
  hienThi(2, h("h1", {}, u.dong_y.tieu_de),
    h("div", { class: "the" }, u.dong_y.doan.map((d) => h("p", { class: "mo-ta" }, d))),
    h("div", { class: "the" }, h("h2", {}, tt.fb.tieu_de), h("p", { class: "mo-ta" }, tt.fb.mo_ta),
      h("h2", {}, tt.fb.tieu_de_phan.A),
      oChu("o-email", u.thong_tin.nhan_email, u.thong_tin.ghi_chu_email, "email", "email"),
      cauChon(a.A1, capNhatNguoiLon), cauChon(a.A2),
      truong),
    h("div", { class: "the" }, oTich("dongY", u.dong_y.o_dong_y), hopNguoiLon, loi, nut));
  capNhatNguoiLon();
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

/** Thu câu trả lời form B thành body gửi /behavior. Trả về { body } hoặc { loi }. */
function thuHanhVi() {
  const t = tt.tl, boQuaB = t.A4 === CHUA_TUNG_DUNG;
  const ids = ["B1", "B2", "B3", "B4_1", "B4_2", "B4_3", "B4_4", "B4_5", "B4_6", "B4_7", "B5", "B6", "B7"];
  if (thieuCau(["A4"]) || (!boQuaB && thieuCau(ids))) return { loi: tt.ui.loi.thieu_cau };
  const body = { session_token: tt.token, A4: t.A4, duration_sec: Math.round((Date.now() - tt.batDauB) / 1000) };
  if (!boQuaB) ids.forEach((id) => { body[id] = t[id]; });
  if (!boQuaB) ["B1", "B3", "B6"].forEach((id) => { body[id + "_other"] = (t[id + "_other"] || "").trim(); });  // chữ ở "Mục khác:"
  return { body };
}

async function guiHanhVi(kq, hopLoi) {
  if (kq.loi) { baoLoi(hopLoi, kq.loi); return 200; }
  const r = await goiApi("/api/research/behavior", kq.body);
  if (r.status === 409) { manC(); return 409; }          // đã nộp phần này rồi: đi tiếp
  if (r.status !== 200) { loiPhien(hopLoi, r.status); return r.status; }
  manC();
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
  hienThi(3, h("div", { class: "the" }, cauChon(a4, capNhat), hopB, loi, nut));
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
  const r = await goiApi("/api/research/self-assessment", kq.body);
  if (r.status !== 200 && r.status !== 409) { loiPhien(hopLoi, r.status); return r.status; }
  manGioiThieu();
  return 200;
}

function manC() {
  const u = tt.ui.form_c, cauC = tt.fb.phan_c_tu_danh_gia;
  const loi = h("div", { class: "loi an", role: "alert" });
  const nut = nutGui(u.nut, () => guiTuDanhGia(thuTuDanhGia(), loi), loi);
  hienThi(4, h("div", { class: "the" }, h("h2", {}, tt.fb.tieu_de_phan.C),
    luoi(cauC.filter((c) => c.id !== "C6"), tt.fb.c_luoi),
      cauChon(cauC.find((c) => c.id === "C6")), loi, nut));
}

// ---------- Màn 5: giới thiệu và game 1 (file game1.js). Màn 6: tạm thời (game 2 và 3 làm sau) ----------

function manChuaXong() {
  const u = tt.ui.chua_xong;
  hienThi(6, h("h1", {}, u.tieu_de), h("p", { class: "mo-ta" }, u.mo_ta));
}

// ---------- Khởi động ----------

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
  if (localStorage.getItem(KHOA_TOKEN)) manTiepTuc(); else manMa();
}

khoiDong();
