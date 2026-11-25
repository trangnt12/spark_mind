// Màn hình game 2 "Soi lỗi AI" (hướng 2). Dùng lại h(), goiApi(), hienThi()... của app.js và tenGame(), manGameGioiThieu() của game_chung.js.
// Bấm "Tiếp tục" thì máy chủ lưu và chấm, nhưng chỉ trả {ok}: KHÔNG có điểm, đúng/sai hay đáp án ở bước này.
// Đáp án và điểm chỉ xem được ở "Xem lại bài của bạn" (review.js) sau khi đã hoàn thành cả 3 game.
// Bố cục (trang làm bài; hướng dẫn nằm ở trang giới thiệu riêng): tên game, khung "tình huống" như tin nhắn gửi AI, rồi 12 thẻ đánh số (mỗi thẻ một ô tích "Ý này sai"). Chân trang chỉ có nút.
"use strict";

/** Trang giới thiệu riêng của game 2 (tab 1). Quay lại -> game 1 (bản đã nộp, chỉ xem). */
function manGame2GioiThieu() {
  manGameGioiThieu(2, manGame2, manGame1);
}

/** Gọi game2/start. Lỗi mạng thì hiện nút "Thử lại". Đã nộp rồi thì hiện bản khóa (chỉ xem lựa chọn của mình, không sửa). */
async function manGame2() {
  datMan("game2");
  const loi = h("div", { class: "loi an", role: "alert" });
  const nut = nutGui(tt.ui.chung.nut_thu_lai, async () => {
    const r = await goiApi("/api/research/game2/start", { session_token: tt.token });
    if (r.status !== 200) { loiPhien(loi, r.status); return r.status; }
    veGame2(r.du_lieu);
    return 200;
  }, loi);
  hienThi(5, h("p", { class: "mo-ta" }, tt.ui.giao_dien.dang_tai), khungNut(loi, nut));
  nut.click();   // tự gọi lần đầu
}

/** Số thẻ: "Ý 3". */
function nhanSoY(n) {
  return tt.ui.game2.y_so.replace("{n}", n);
}

/** Một thẻ ý để đánh dấu: ô tích kiểu câu chọn nhiều đáp án (bấm đâu trên thẻ cũng được); chọn thì thẻ xanh như form B, không có nhãn thêm. khoa: bản đã nộp, không bấm được. */
function theYGame2(y, thuTu, daChon, khoa) {
  const o = h("input", { type: "checkbox", name: "g2", value: y.id, disabled: khoa });
  o.checked = daChon;
  return h("label", { class: "lua-chon the-y2" + (khoa ? " khoa" : "") }, o,
    h("span", { class: "noi-y2" }, h("span", { class: "so-y2" }, nhanSoY(thuTu)), h("span", { class: "chu-y2" }, y.van_ban)));
}

/** Các id đang được đánh dấu trong danh sách thẻ. */
function idDaChon(ds) {
  return [...ds.querySelectorAll("input:checked")].map((o) => o.value);
}

/** Màn đánh dấu các ý cho là SAI. Không hiện bộ đếm, không nói có bao nhiêu ý sai. */
function veGame2(bd) {
  const u = tt.ui.game2, khoa = bd.submitted;
  const nhap = new Set(khoa ? bd.da_chon : docNhap().g2 || []);   // đã nộp: lựa chọn đã lưu; chưa nộp: nháp (nếu vừa F5)
  const loi = h("div", { class: "loi an", role: "alert" });
  const ds = h("div", { class: "ds-y2" }, bd.y.map((y, i) => theYGame2(y, i + 1, nhap.has(y.id), khoa)));
  if (!khoa) ds.addEventListener("change", () => ghiNhap("g2", idDaChon(ds)));   // lưu nháp để F5 không mất
  const nut = khoa ? h("button", { type: "button", onclick: manGame3GioiThieu }, tt.ui.chung.nut_tiep_tuc)
    : nutGui(tt.ui.chung.nut_tiep_tuc, () => nopGame2(ds, loi), loi);
  hienThi(5, tenGame(2, bd.ten),
    h("div", { class: "the tinh-huong" }, h("p", { class: "ghi-chu" }, "💬 " + u.nhan_tinh_huong), h("p", { class: "bong-noi" }, bd.tinh_huong),
      khoa ? h("p", { class: "ghi-chu" }, u.da_nop_khong_sua) : ""),   // bản đã khóa: ghi chú nằm trong khung tình huống, KHÔNG ở chân trang
    ds, khungNut(loi, nut, nutQuayLai(manGame2GioiThieu)));
}

/** Gửi các ý đã chọn. Lỗi mạng: giữ nguyên lựa chọn, nút đổi thành "Thử lại". Thành công: sang game 3, không hiện kết quả. */
async function nopGame2(ds, hopLoi) {
  const r = await goiApi("/api/research/game2/submit", { session_token: tt.token, chon: idDaChon(ds) });
  if (r.status !== 200) { loiPhien(hopLoi, r.status); return r.status; }
  xoaNhap("g2");
  manGame3GioiThieu();
  chucMung();
  return 200;
}
