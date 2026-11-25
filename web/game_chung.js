// Phần dùng chung của cả 3 game: dải tên game, khối hướng dẫn và TRANG GIỚI THIỆU riêng của từng game (tab 1; tab 2 là trang làm bài). Dùng lại h() của app.js.
// Chữ lấy từ content/games/gameN.json (nội dung hướng dẫn) và content/research_ui.json (tên bốn mục), không viết cứng ở đây.
"use strict";

/** Dải tên game to, rõ ở đầu mọi màn game: "Game 1" + tên. Tên lấy từ "ten" trong content/games/gameN.json (một chỗ duy nhất),
 *  mẫu chữ "Game {so}: {ten}" lấy từ research_ui.json (đọc màn hình đọc cả câu). */
function tenGame(so, ten) {
  const chu = tt.ui.tieu_game.replace("{so}", so).replace("{ten}", ten);
  return h("div", { class: "ten-game", role: "heading", "aria-level": "1", "aria-label": chu },
    h("span", { class: "so-game", "aria-hidden": "true" }, "Game " + so), h("span", { class: "ten-game-chu", "aria-hidden": "true" }, ten));
}

const MUC_GIOI_THIEU = ["nhiem_vu", "cach_choi", "luu_y", "thoi_gian"];   // thứ tự bốn mục

/** Khối hướng dẫn gọn đầu mỗi game: bốn mục (Nhiệm vụ, Cách chơi, Lưu ý, Thời gian ước tính), mỗi ý một dòng.
 *  gt = "gioi_thieu" trong content/games/gameN.json: { nhiem_vu: [...], cach_choi: [...], luu_y: [...], thoi_gian: [...] }. */
function khoiGioiThieu(gt) {
  const nhan = tt.ui.giao_dien.khoi_gioi_thieu;
  const muc = MUC_GIOI_THIEU.filter((k) => (gt[k] || []).length).map((k) =>
    h("section", { class: "muc-gt muc-" + k.replace("_", "-") },
      h("h2", {}, h("span", { "aria-hidden": "true" }, nhan[k].bieu_tuong + " "), nhan[k].nhan),
      h("ul", {}, gt[k].map((y) => h("li", {}, y)))));
  return h("div", { class: "the khoi-gt" }, muc);
}

/** Trang giới thiệu của một game (tab 1): tên game + bốn mục hướng dẫn, nút "Tiếp tục" sang trang làm bài.
 *  Chưa bắt đầu game ở máy chủ (game 1 chỉ chạy đồng hồ khi sang trang làm bài). vaoGame: hàm mở trang làm bài; quayLai: hàm về màn trước. */
async function manGameGioiThieu(so, vaoGame, quayLai) {
  datMan("game" + so + "_gt");
  const loi = h("div", { class: "loi an", role: "alert" });
  const nut = nutGui(tt.ui.chung.nut_thu_lai, async () => {
    const r = await goiApi("/api/content/gioi-thieu/" + so);
    if (r.status !== 200) { loiPhien(loi, r.status); return r.status; }
    hienThi(5, tenGame(so, r.du_lieu.ten), khoiGioiThieu(r.du_lieu.gioi_thieu),
      khungNut(h("button", { type: "button", onclick: vaoGame }, tt.ui.chung.nut_tiep_tuc), nutQuayLai(quayLai)));
    danhDauGioiThieu();
    return 200;
  }, loi);
  hienThi(5, h("p", { class: "mo-ta" }, tt.ui.giao_dien.dang_tai), khungNut(loi, nut));
  nut.click();   // tự gọi lần đầu
}
