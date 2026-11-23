// Màn hình game 2 "Soi lỗi AI" (hướng 2). Dùng lại h(), goiApi(), hienThi(), tenGame()... của app.js và game1.js.
// Bố cục: tên game, khung "tình huống" như tin nhắn gửi AI, rồi 12 thẻ đánh số; mỗi thẻ có nút gạt "Đánh dấu sai".
// Đáp án chỉ về trình duyệt SAU khi nộp (máy chủ chấm). Không có đồng hồ đếm ngược.
"use strict";

/** Gọi game2/start. Lỗi mạng thì hiện nút "Thử lại". Đã nộp rồi thì hiện luôn kết quả (chỉ xem, không làm lại). */
async function manGame2() {
  datMan("game2");
  const loi = h("div", { class: "loi an", role: "alert" });
  const nut = nutGui(tt.ui.chung.nut_thu_lai, async () => {
    const r = await goiApi("/api/research/game2/start", { session_token: tt.token });
    if (r.status !== 200) { loiPhien(loi, r.status); return r.status; }
    if (r.du_lieu.submitted) veKetQuaGame2(r.du_lieu); else veGame2(r.du_lieu);
    return 200;
  }, loi);
  hienThi(5, h("p", { class: "mo-ta" }, tt.ui.giao_dien.dang_tai), khungNut(loi, nut));
  nut.click();   // tự gọi lần đầu
}

/** Nút "Quay lại" về Game 1 (game 1 đã nộp thì chỉ xem lại, không làm lại được). */
function nutVeGame1() {
  return nutQuayLai(manGame1);
}

/** Số thẻ: "Ý 3". */
function nhanSoY(n) {
  return tt.ui.game2.y_so.replace("{n}", n);
}

/** Một thẻ ý để đánh dấu: cả thẻ là một ô tích (bấm đâu cũng được), có nút gạt "Đánh dấu sai" ở dưới. */
function theYGame2(y, thuTu, daChon) {
  const u = tt.ui.game2;
  const o = h("input", { type: "checkbox", name: "g2", value: y.id });
  o.checked = daChon;
  return h("label", { class: "the-y2" }, o, h("span", { class: "so-y2" }, nhanSoY(thuTu)),
    h("span", { class: "chu-y2" }, y.van_ban),
    h("span", { class: "gat-y2", "aria-hidden": "true" }, h("span", { class: "gat-chua" }, u.danh_dau), h("span", { class: "gat-roi" }, "🚩 " + u.da_danh_dau)));
}

/** Màn đánh dấu các ý cho là SAI. Dòng đếm chỉ nói số ý bạn đã đánh dấu, không nói tổng số ý sai. */
function veGame2(bd) {
  const u = tt.ui.game2;
  const nhap = new Set(docNhap().g2 || []);   // đánh dấu dở dang (nếu vừa F5) được khôi phục
  const loi = h("div", { class: "loi an", role: "alert" });
  const dem = h("p", { class: "dem-y2", "aria-live": "polite" });
  const ds = h("div", { class: "ds-y2" }, bd.y.map((y, i) => theYGame2(y, i + 1, nhap.has(y.id))));
  const capNhat = () => {
    const chon = [...ds.querySelectorAll("input:checked")].map((o) => o.value);
    dem.textContent = u.dem_da_danh_dau.replace("{n}", chon.length);
    ghiNhap("g2", chon);
  };
  ds.addEventListener("change", capNhat);
  const nut = nutGui(u.nut_nop, () => nopGame2(ds, loi), loi);
  hienThi(5, tenGame(2, bd.ten),
    h("div", { class: "the tinh-huong" }, h("p", { class: "ghi-chu" }, "💬 " + u.nhan_tinh_huong), h("p", { class: "bong-noi" }, bd.tinh_huong),
      h("p", { class: "ghi-chu" }, u.huong_dan)),
    dem, ds, khungNut(loi, nut, nutVeGame1()));
  capNhat();
}

/** Gửi các ý đã chọn. Lỗi mạng: giữ nguyên lựa chọn, nút đổi thành "Thử lại". */
async function nopGame2(ds, hopLoi) {
  const chon = [...ds.querySelectorAll("input:checked")].map((o) => o.value);
  const r = await goiApi("/api/research/game2/submit", { session_token: tt.token, chon });
  if (r.status !== 200) { loiPhien(hopLoi, r.status); return r.status; }
  xoaNhap("g2");
  veKetQuaGame2(r.du_lieu);
  chucMung();
  return 200;
}

/** Điểm của riêng một ý: +1 / −1 / 0 (dấu trừ thật "−" cho dễ đọc). */
function chuDiemY(d) {
  return tt.ui.game2.diem_y.replace("{d}", d > 0 ? "+" + d : d < 0 ? "−" + Math.abs(d) : "0");
}

/** Một thẻ kết quả. Xanh (✓) = nhận định của bạn đúng, thẻ gọn, không giải thích; đỏ (✗) = chưa đúng, thẻ rộng, luôn có giải thích.
 *  Hai dòng chữ tách bạch: "Sự thật" (ý của AI đúng hay sai) và "Bạn" (đã đánh dấu hay không); có ✓/✗ nên người mù màu vẫn đọc được. */
function theKetQuaGame2(k, thuTu) {
  const u = tt.ui.game2, dung = k.nhan_dinh_dung;
  const dau = h("span", { class: "dau-kq", role: "img", "aria-label": dung ? u.bieu_tuong_dung : u.bieu_tuong_sai }, dung ? "✓" : "✗");
  const con = [h("p", { class: "ghi-chu so-y2" }, nhanSoY(thuTu) + " · " + chuDiemY(k.diem)), h("p", { class: "van-ban-y" }, k.van_ban),
    h("p", { class: "ghi-chu" }, h("b", {}, k.la_loi ? u.su_that_sai : u.su_that_dung), " · ", k.da_chon ? u.ban_danh_dau : u.ban_bo_qua)];
  if (!dung) con.push(h("p", { class: "giai-thich" }, k.la_loi ? k.giai_thich : u.giai_thich_y_dung));
  return h("li", { class: "ket-qua-y " + (dung ? "y-dung" : "y-sai") }, dau, h("div", { class: "noi-dung-kq" }, con));
}

/** Khối điểm: vòng tròn điểm x/5 (vòng đầy theo điểm), kèm hai ô tóm tắt. */
function khoiDiemGame2(bd) {
  const u = tt.ui.game2, dung = bd.ket_qua.filter((k) => k.nhan_dinh_dung).length;
  return h("div", { class: "the diem-tong" }, h("p", { class: "ghi-chu" }, u.diem_cua_ban),
    h("div", { class: "vong-diem", style: `--pct:${bd.diem * 20}%` }, h("span", { class: "so-diem" }, bd.diem + "/5")),
    h("p", { class: "ghi-chu" }, u.chu_thich_diem),
    h("div", { class: "tom-tat" }, h("span", { class: "chip-dung" }, "✓ " + u.tom_tat_dung.replace("{n}", dung)),
      h("span", { class: "chip-sai" }, "✗ " + u.tom_tat_sai.replace("{n}", bd.ket_qua.length - dung))));
}

/** Màn kết quả: tên game, điểm, rồi từng ý (hiện được cả khi tải lại trang). */
function veKetQuaGame2(bd) {
  const u = tt.ui.game2;
  hienThi(5, tenGame(2, bd.ten), khoiDiemGame2(bd),
    h("ul", { class: "ds-kq2" }, bd.ket_qua.map((k, i) => theKetQuaGame2(k, i + 1))),
    khungNut(h("button", { type: "button", onclick: manChuaXong }, u.nut_tiep), nutVeGame1()));
}
