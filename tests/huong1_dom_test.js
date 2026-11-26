// Chạy trang /huong-1 (landing_chung.js, huong1.js) trên DOM giả.
// Dùng: node huong1_dom_test.js <thư mục web> <landing_ui.json dạng chuỗi>
const fs = require("fs");
const path = require("path");
const { taoMoiTruong, boKiem } = require("./fake_dom");
const [, , thuMuc, uiJson] = process.argv;
const UI = JSON.parse(uiJson);
const { kiem, ketThuc } = boKiem();
const MA = ["landing_chung.js", "huong1.js"].map((f) => fs.readFileSync(path.join(thuMuc, f), "utf-8")).join("\n");

async function nap(ui, trangThai = 200) {
  const mt = taoMoiTruong({ ids: ["man-hinh", "chan-trang", "ten-he-thong"], api: { "/api/content/landing": { status: trangThai, body: ui } } });
  (0, eval)(MA);
  await mt.nho();
  return { mt, tim: (f) => [...mt.theo["man-hinh"].find(f), ...mt.theo["chan-trang"].find(f)] };
}

(async () => {
  let { mt, tim } = await nap(UI);
  const u = UI.huong1_trang;
  kiem(mt.theo["ten-he-thong"].textContent === "SparkMind", "header có tên SparkMind");
  kiem(tim((n) => n.tag === "h1").length === 1 && tim((n) => n.tag === "h1")[0].textContent === u.tieu_de, "tiêu đề đúng");
  kiem(u.thong_tin.every((c) => mt.theo["man-hinh"].textContent.includes(c)) && u.mo_ta.every((c) => mt.theo["man-hinh"].textContent.includes(c)), "đủ mô tả và thông tin tham gia");
  const bd = tim((n) => n.tag === "a" && n.textContent === u.nut_bat_dau);
  kiem(bd.length === 1 && bd[0].attrs.href === UI.huong1_url && bd[0].attrs.target === "_blank" && bd[0].attrs.rel.includes("noopener"), "Bắt đầu khảo sát mở huong1_url ở tab mới");
  kiem(tim((n) => n.tag === "a" && n.attrs.href === "/").length === 1, "có liên kết về trang chủ");

  const ui2 = JSON.parse(JSON.stringify(UI)); ui2.huong1_url = "";
  ({ tim } = await nap(ui2));
  const sap = tim((n) => n.tag === "button" && n.textContent === u.sap_mo);
  kiem(sap.length === 1 && sap[0].disabled && tim((n) => n.textContent === u.nut_bat_dau).length === 0, "huong1_url trống: nút Sắp mở bị khóa");
  ui2.huong1_url = "javascript:alert(1)";
  ({ tim } = await nap(ui2));
  kiem(tim((n) => (n.attrs.href || "").startsWith("javascript")).length === 0, "chặn javascript:");

  ({ mt } = await nap(UI, 500));
  kiem(mt.theo["man-hinh"].textContent.startsWith("Không tải được"), "lỗi tải chữ thì báo một dòng");
  ketThuc();
})();
