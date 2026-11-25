// Màn hình game 3 "Làm tốt hơn AI" (hướng 2). Dùng lại h(), goiApi(), hienThi(), nutGui(), khungNut()... của app.js
// và tenGame(), manGameGioiThieu() của game_chung.js (hướng dẫn ở trang giới thiệu riêng, trang này chỉ có phần làm bài).
// MỘT màn cho cả hai tình huống: cột trái là menu "Tình huống 1/2" (đủ ký tự thì xanh nước biển + ✓), cột phải là tình huống đang chọn.
// Dưới 700px menu thành hai tab ngang. Chân trang chỉ có nút "Nộp bài" (không chữ nào khác), tắt cho tới khi CẢ HAI tình huống đủ ký tự; nộp một lần.
// Giao diện chỉ đếm KÝ TỰ (n/800). Server vẫn tính và lưu so_tu.
// Bản nháp (chữ, số lần dán/rời tab, thời gian dùng ô) lưu bằng nhap.js ở khóa "g3" nên F5 không mất. Không có điểm hay nhận xét nào hiện ra.
// Thời gian từng ô: trình duyệt cộng dồn lúc ô đang được focus (trừ lúc tab bị ẩn), gửi kèm khi nộp; máy chủ vẫn tự tính thời gian cả game.
"use strict";

// dangChoi: đang ở màn game 3; o: trạng thái từng ô theo id; xem: id tình huống đang chọn; luu: hàm lưu nháp
const g3 = { dangChoi: false, o: {}, xem: "", luu: null, menu: null, nut: null, khungs: [] };

/** Số ký tự (bỏ khoảng trắng hai đầu): giống cách máy chủ kiểm tra mức tối thiểu. */
function demKyTuG3(chu) {
  return chu.trim().length;
}

/** Trang giới thiệu riêng của game 3 (tab 1). Quay lại -> game 2 (bản đã nộp, chỉ xem). */
function manGame3GioiThieu() {
  manGameGioiThieu(3, manGame3, manGame2);
}

/** Vào game 3: lấy đề (content) và báo máy chủ bắt đầu. Lỗi mạng thì nút "Thử lại". Đã nộp rồi thì về trang tổng kết. */
async function manGame3() {
  datMan("game3");
  const loi = h("div", { class: "loi an", role: "alert" });
  const nut = nutGui(tt.ui.chung.nut_thu_lai, async () => {
    const [bd, nd] = await Promise.all([goiApi("/api/research/game3/start", { session_token: tt.token }), goiApi("/api/content/game3")]);
    const status = bd.status !== 200 ? bd.status : nd.status;
    if (status !== 200) { loiPhien(loi, status); return status; }
    if (bd.du_lieu.submitted) manHoanThanh(); else veGame3(nd.du_lieu);
    return 200;
  }, loi);
  hienThi(5, h("p", { class: "mo-ta" }, tt.ui.giao_dien.dang_tai), khungNut(loi, nut));
  nut.click();   // tự gọi lần đầu
}

/** Khung "Ý tưởng của AI": nền xám, khác hẳn ô nhập. */
function khungYAi(th) {
  return h("div", { class: "y-ai" }, h("p", { class: "ghi-chu" }, tt.ui.game3.nhan_y_ai), h("p", { class: "y-ai-chu" }, th.ai_goc));
}

/** Tên mục menu: "Tình huống 1" (chiSo bắt đầu từ 0). */
function nhanMenu(chiSo) {
  return tt.ui.game3.menu_th.replace("{n}", chiSo + 1);
}

// ---------- Đo thời gian từng ô: chỉ cộng lúc ô đang được focus và tab đang hiện ----------

/** Dừng đồng hồ của một ô (nếu đang chạy) và cộng dồn vào tổng. */
function dungDoO(st) {
  if (st.tu !== null) { st.ms += Math.round(performance.now() - st.tu); st.tu = null; }
}

/** Chạy đồng hồ của ô nếu ô đang được focus và tab đang hiện. */
function chayDoO(st) {
  if (st.tu === null && !document.hidden && document.activeElement === st.o) st.tu = performance.now();
}

/** Thời gian đã dùng ô (giây, làm tròn), kể cả đoạn đang chạy. */
function giayO(st) {
  return Math.round((st.ms + (st.tu === null ? 0 : performance.now() - st.tu)) / 1000);
}

// ---------- Một tình huống: ô nhập, bộ đếm, nháp ----------

/** Tạo khung nội dung một tình huống và gắn trạng thái vào g3.o[th.id]. Khôi phục bản nháp nếu vừa F5. */
function khungTinhHuong(th, nd, khiDoi) {
  const u = tt.ui.game3, nhap = ((docNhap().g3 || {}).o || {})[th.id] || {};
  const o = h("textarea", { rows: 7, maxlength: nd.toi_da_ky_tu, autocomplete: "off", placeholder: u.goi_y_o, "aria-label": u.nhan_y_ban });
  o.value = nhap.txt || "";
  const st = { o, paste: nhap.paste || 0, roiTab: nhap.roiTab || 0, ms: nhap.ms || 0, tu: null,
    demKyTu: h("p", { class: "ghi-chu dem-ky-tu", "aria-live": "off" }) };
  g3.o[th.id] = st;
  chanOMuc(o, () => { st.paste++; g3.luu(); });   // chặn dán/kéo thả/chuột phải; đếm số lần dán thử của RIÊNG ô này
  o.addEventListener("focus", () => chayDoO(st));
  o.addEventListener("blur", () => { dungDoO(st); g3.luu(); });
  o.addEventListener("input", () => { khiDoi(); g3.luu(); });
  const khung = h("div", { class: "the khung-th", id: "th-" + th.id }, h("h2", { class: "tieu-de-th" }, th.tieu_de), khungYAi(th),
    h("label", { class: "cau-hoi" }, u.nhan_y_ban, o), st.demKyTu);
  return { khung, st };
}

/** Cập nhật dòng đếm "n/800 ký tự" của một ô (đổi màu khi đã đủ mức tối thiểu). */
function veDemO(st, nd) {
  const n = demKyTuG3(st.o.value);
  st.demKyTu.textContent = tt.ui.game3.dem_ky_tu.replace("{n}", n).replace("{max}", nd.toi_da_ky_tu);
  st.demKyTu.classList.toggle("du", n >= nd.toi_thieu_ky_tu);
}

/** Các tình huống còn thiếu ký tự (danh sách chỉ số, theo thứ tự). */
function thieuTu(nd) {
  return nd.tinh_huong.map((th, i) => (demKyTuG3(g3.o[th.id].o.value) < nd.toi_thieu_ky_tu ? i : -1)).filter((i) => i >= 0);
}

/** Một mục menu "Tình huống n": xanh nước biển + ✓ khi đủ ký tự (CSS lo màu); đang xem thì có viền nổi bật. */
function mucMenu(chiSo, th, chon) {
  return h("button", { type: "button", class: "muc-menu", "data-id": th.id, onclick: () => chon(th.id) },
    h("span", { class: "dau-du", "aria-hidden": "true" }, "✓"), h("span", {}, nhanMenu(chiSo)));
}

// ---------- Màn game 3 ----------

/** Lưu nháp cả hai ô cùng lúc (chữ, số lần dán/rời tab, thời gian dùng ô) và tình huống đang xem. */
function luuNhapG3() {
  const o = Object.fromEntries(Object.entries(g3.o).map(([id, st]) => [id,
    { txt: st.o.value, paste: st.paste, roiTab: st.roiTab, ms: st.ms + (st.tu === null ? 0 : Math.round(performance.now() - st.tu)) }]));
  ghiNhap("g3", { o, xem: g3.xem });
}

/** Màn game 3: tên game, hướng dẫn, menu trái + tình huống phải, rồi chân trang chỉ có nút "Nộp bài". */
function veGame3(nd) {
  const u = tt.ui.game3, loi = h("div", { class: "loi an", role: "alert" });
  g3.o = {}; g3.luu = luuNhapG3;
  const khungs = nd.tinh_huong.map((th) => khungTinhHuong(th, nd, () => capNhatG3(nd)));
  const menu = h("nav", { class: "menu-th", "aria-label": u.nhan_menu }, nd.tinh_huong.map((th, i) => mucMenu(i, th, (id) => chonTinhHuong(id, true))));
  const nut = nutGui(tt.ui.chung.nut_nop_bai, async () => { const kq = await nopGame3(nd, loi); setTimeout(() => capNhatG3(nd), 0); return kq; }, loi);
  Object.assign(g3, { menu, nut, khungs, xem: (docNhap().g3 || {}).xem || nd.tinh_huong[0].id });
  hienThi(5, tenGame(nd.so, nd.ten),
    h("div", { class: "bo-cuc-th" }, menu, h("div", { class: "cot-th" }, khungs.map((k) => k.khung))),
    khungNut(loi, nut, nutQuayLai(manGame3GioiThieu)));
  g3.dangChoi = true;   // từ đây mới đếm rời tab
  chonTinhHuong(g3.xem, false);
  capNhatG3(nd);
}

/** Chuyển sang xem một tình huống (lưu nháp ngay). Bấm menu thì đưa con trỏ vào ô nhập. */
function chonTinhHuong(id, doiFocus) {
  if (!g3.o[id]) id = Object.keys(g3.o)[0];
  g3.xem = id;
  for (const k of g3.khungs) k.khung.hidden = k.khung.id !== "th-" + id;
  for (const m of g3.menu.children) {
    const dang = m.dataset.id === id;
    m.classList.toggle("dang-xem", dang);
    m.setAttribute("aria-current", dang ? "true" : "false");
  }
  g3.luu();
  if (doiFocus) g3.o[id].o.focus();
}

/** Cập nhật mọi thứ phụ thuộc số ký tự: bộ đếm, màu menu, trạng thái nút "Nộp bài" (tắt cho tới khi đủ cả hai). */
function capNhatG3(nd) {
  const u = tt.ui.game3, thieu = thieuTu(nd);
  nd.tinh_huong.forEach((th) => veDemO(g3.o[th.id], nd));
  for (const m of g3.menu.children) {
    const du = !thieu.includes(nd.tinh_huong.findIndex((th) => th.id === m.dataset.id));
    m.classList.toggle("xong", du);
    m.title = du ? u.da_du_tu : "";
  }
  g3.nut.disabled = thieu.length > 0;   // không có chữ báo thiếu: menu xanh/không xanh đã đủ để biết
}

/** Nộp cả hai tình huống một lần. Lỗi mạng: giữ nguyên chữ, nút đổi thành "Thử lại". Thành công: sang trang tổng kết. */
async function nopGame3(nd, hopLoi) {
  const thieu = thieuTu(nd);
  if (thieu.length) return baoLoi(hopLoi, tt.ui.game3.thieu_tu.replace("{min}", nd.toi_thieu_ky_tu).replace("{ds}", thieu.map(nhanMenu).join(", ")));
  Object.values(g3.o).forEach(dungDoO);
  const items = nd.tinh_huong.map((th) => {
    const st = g3.o[th.id];
    return { tinh_huong_id: th.id, noi_dung: st.o.value, paste_count: st.paste, tab_leave_count: st.roiTab, thoi_gian_giay: giayO(st) };
  });
  const r = await goiApi("/api/research/game3/submit", { session_token: tt.token, items });
  if (r.status === 422 && typeof r.du_lieu.detail === "string") return baoLoi(hopLoi, r.du_lieu.detail);
  if (r.status !== 200) { loiPhien(hopLoi, r.status); return r.status; }
  g3.dangChoi = false; g3.luu = null; xoaNhap("g3");
  chucMung();
  manHoanThanh();
  return 200;
}

// Tab ẩn/hiện: dừng/chạy đồng hồ của ô đang focus; rời tab thì đếm cho ô đang xem rồi lưu nháp ngay.
document.addEventListener("visibilitychange", () => {
  if (!g3.dangChoi || !g3.luu) return;
  Object.values(g3.o).forEach(document.hidden ? dungDoO : chayDoO);
  if (document.hidden && g3.o[g3.xem]) { g3.o[g3.xem].roiTab++; g3.luu(); }
});
