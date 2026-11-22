// Màn hình game 1 "Đồ vật bí ẩn" (hướng 2). Dùng lại h(), goiApi(), hienThi(), tt... của app.js.
// Danh sách ý chỉ giữ trong bộ nhớ trang (biến g1), không lưu localStorage.
"use strict";

// Trạng thái game 1: các ý đã thêm, số lần dán thử, số lần rời tab, đồng hồ, đã nộp chưa
const g1 = { cacY: [], paste: 0, roiTab: 0, conLai: 0, hanChot: 0, nhip: null, daNop: false };

// ---------- Màn giới thiệu chung 3 trò ----------

function manGioiThieu() {
  const u = tt.ui.game_gioi_thieu;
  hienThi(5, tieuDe("game", u.tieu_de_chung), cacDoan(u.mo_ta),
    khungNut(h("button", { type: "button", onclick: manGame1 }, u.nut_bat_dau), nutQuayLai(manC)));
}

// ---------- Màn game 1: lấy đề từ máy chủ ----------

/** Gọi game1/start và tải chữ hướng dẫn. Lỗi mạng thì hiện nút "Thử lại" (chưa có gì để mất). */
async function manGame1() {
  const loi = h("div", { class: "loi an", role: "alert" });
  const nut = nutGui(tt.ui.chung.nut_thu_lai, async () => {
    const [bd, nd] = await Promise.all([goiApi("/api/research/game1/start", { session_token: tt.token }),
                                        goiApi("/api/content/game1")]);
    const status = bd.status !== 200 ? bd.status : nd.status;
    if (status !== 200) { loiPhien(loi, status); return status; }
    if (bd.du_lieu.submitted) { manChuaXong(); return 200; }
    veGame1(bd.du_lieu, nd.du_lieu);
    return 200;
  }, loi);
  hienThi(5, h("p", { class: "mo-ta" }, tt.ui.giao_dien.dang_tai), khungNut(loi, nut));
  nut.click();   // tự gọi lần đầu
}

// ---------- Đồng hồ: thời gian CÒN LẠI do server tính ----------

/** Đổi số giây thành m:ss. */
function dinhDangGio(giay) {
  return Math.floor(giay / 60) + ":" + String(giay % 60).padStart(2, "0");
}

const CHU_VI_VONG = 213.63;   // chu vi vòng tròn bán kính 34 (khớp stroke-dasharray trong style.css)

/** Vòng đồng hồ: trả về { khung (thẻ), nhan (chữ giờ), tien (nét vòng) }. */
function veDongHo(chuGio) {
  const nhan = h("strong", { class: "dong-ho" });
  const vong = h("div", { class: "vong" }, nhan);
  vong.insertAdjacentHTML("afterbegin", '<svg viewBox="0 0 80 80" aria-hidden="true">' +
    '<circle class="nen" cx="40" cy="40" r="34"/><circle class="tien" cx="40" cy="40" r="34"/></svg>');
  const khung = h("div", { class: "the khung-gio", role: "timer" }, vong, h("span", { class: "chu-gio" }, chuGio));
  return { khung, nhan, tien: vong.querySelector(".tien") };
}

/** Cập nhật vòng: vòng cạn dần; còn dưới 30 giây thì vàng, dưới 10 giây thì đỏ. */
function capNhatVong(dh, conLai, tong) {
  dh.nhan.textContent = dinhDangGio(conLai);
  dh.tien.style.strokeDashoffset = CHU_VI_VONG * (1 - conLai / tong);
  dh.khung.classList.toggle("vang", conLai < 30 && conLai >= 10);
  dh.khung.classList.toggle("do", conLai < 10);
}

/** Chạy đồng hồ từ số giây còn lại của server. Dùng giờ máy chỉ để đếm tiếp, nên tải lại trang vẫn đúng. */
function chayDongHo(dh, conLaiServer, tong, khiHet) {
  g1.hanChot = Date.now() + conLaiServer * 1000;
  clearInterval(g1.nhip);
  const dem = () => {
    g1.conLai = Math.max(0, Math.ceil((g1.hanChot - Date.now()) / 1000));
    capNhatVong(dh, g1.conLai, tong);
    if (g1.conLai === 0) { clearInterval(g1.nhip); khiHet(); }
  };
  g1.nhip = setInterval(dem, 250);
  dem();
}

// ---------- Chống gian lận: chặn dán, kéo thả, chuột phải; đếm dán thử và rời tab ----------

/** Gắn chặn vào ô nhập; mỗi lần dán thử thì tăng paste_count. */
function chanOMuc(o) {
  o.addEventListener("paste", (e) => { e.preventDefault(); g1.paste++; });
  for (const ten of ["drop", "dragover", "contextmenu"]) o.addEventListener(ten, (e) => e.preventDefault());
}

/** Đếm số lần rời tab (chuyển sang tab khác hoặc thu nhỏ trình duyệt). */
function demRoiTab() {
  if (document.hidden && !g1.daNop) g1.roiTab++;
}

// ---------- Danh sách ý ----------

/** Vẽ lại danh sách ý thành các thẻ nhỏ; mỗi thẻ có nút xóa tròn. Dòng đếm chỉ nói số ý, không nhận xét nội dung. */
function veDanhSachY(ds) {
  const g = tt.ui.giao_dien;
  document.getElementById("so-y").textContent = g1.cacY.length ? g.so_y.replace("{n}", g1.cacY.length) : g.chua_co_y;
  ds.replaceChildren(...g1.cacY.map((y, i) => h("li", { class: "dong-y" }, h("span", {}, y),
    h("button", { type: "button", class: "phu xoa-y", "aria-label": g.xoa_y, onclick: () => { g1.cacY.splice(i, 1); veDanhSachY(ds); } },
      bieuTuong("bd-x")))));
}

/** Thêm ý trong ô vào danh sách (bỏ ý rỗng, cắt tối đa 120 ký tự). */
function themY(o, ds, toiDa) {
  const y = o.value.replace(/\s+/g, " ").trim().slice(0, toiDa);
  if (!y) return;
  g1.cacY.push(y);
  o.value = "";
  veDanhSachY(ds);
  o.focus();
}

// ---------- Nộp bài ----------

/** Gửi bài. Lỗi mạng: giữ nguyên danh sách, trả 0 để nút đổi thành "Thử lại". */
async function nopGame1(hopLoi) {
  const r = await goiApi("/api/research/game1/submit",
    { session_token: tt.token, ideas: g1.cacY, paste_count: g1.paste, tab_leave_count: g1.roiTab });
  if (r.status === 200 || r.status === 409) {     // 409: đã nộp rồi, cứ đi tiếp
    g1.daNop = true; clearInterval(g1.nhip);
    document.removeEventListener("visibilitychange", demRoiTab);
    manChuaXong();
    chucMung();
    return 200;
  }
  loiPhien(hopLoi, r.status);
  return r.status;
}

// ---------- Vẽ màn game 1 ----------

/** Ảnh đồ vật. Ảnh thiếu hoặc lỗi thì đổi thành emoji thay thế (khung giữ nguyên, giao diện không vỡ). */
function veAnh(dv) {
  const khung = h("div", { class: "anh-do-vat" });
  const emoji = () => khung.replaceChildren(h("span", { class: "anh-emoji", role: "img", "aria-label": dv.mo_ta_anh || dv.ten }, dv.emoji || "❓"));
  if (!dv.anh) { emoji(); return khung; }
  const img = h("img", { src: dv.anh, alt: dv.mo_ta_anh || dv.ten, decoding: "async", fetchpriority: "high" });
  img.addEventListener("error", emoji);
  khung.append(img);
  return khung;
}

/** Khung hiển thị đồ vật, cách dùng thông thường, ví dụ và hướng dẫn. */
function veDeBai(u, dv, nd) {
  const vd = nd.vi_du;
  return h("div", { class: "the" },
    h("p", { class: "ghi-chu" }, u.nhan_do_vat), veAnh(dv), h("h2", {}, dv.ten),
    h("p", {}, h("b", {}, u.nhan_thong_thuong + " "), dv.cach_dung_thuong),
    h("p", { class: "mo-ta" }, nd.huong_dan),
    h("p", { class: "ghi-chu" }, `${vd.do_vat} (${vd.cach_dung_thuong}): ` + vd.vi_du_khac.join("; ")));
}

/** Màn game 1 đầy đủ: đồng hồ, ô nhập, danh sách, nút nộp. */
function veGame1(bd, nd) {
  const u = tt.ui.game1, toiDa = nd.gioi_han_ky_tu_moi_y;
  Object.assign(g1, { cacY: [], paste: 0, roiTab: 0, daNop: false });
  const dh = veDongHo(u.hien_thi_gio);
  const loi = h("div", { class: "loi an", role: "alert" });
  const o = h("input", { type: "text", maxlength: toiDa, autocomplete: "off", "aria-label": u.nhan_y_tuong });
  const ds = h("ul", { class: "ds-y" });
  // Chữ đang gõ dở trong ô cũng được thêm vào trước khi nộp (kể cả khi hết giờ tự nộp)
  const nut = nutGui(u.nut_nop, () => { themY(o, ds, toiDa); return nopGame1(loi); }, loi);
  chanOMuc(o);
  o.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); themY(o, ds, toiDa); } });
  document.addEventListener("visibilitychange", demRoiTab);
  hienThi(5, dh.khung, veDeBai(u, bd.do_vat, nd),
    h("div", { class: "the" }, h("p", { class: "cau-hoi" }, u.nhan_y_tuong), o,
      h("button", { type: "button", class: "phu", style: "margin-top:10px", onclick: () => themY(o, ds, toiDa) }, u.nut_them),
      h("p", { class: "so-y", id: "so-y", "aria-live": "polite" }), ds),
    khungNut(loi, nut));
  veDanhSachY(ds);
  chayDongHo(dh, bd.remaining_sec, nd.thoi_gian_giay, () => nut.click());   // hết giờ thì tự nộp
  o.focus();
}
