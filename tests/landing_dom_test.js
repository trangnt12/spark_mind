// Chạy trang chủ (landing_chung.js, landing_popup.js, landing_khoi.js, landing.js) trên DOM giả.
// Dùng: node landing_dom_test.js <thư mục web> <landing_ui.json dạng chuỗi>
// In lỗi ra stderr và thoát mã 1 nếu có kiểm tra sai.
const fs = require("fs");
const path = require("path");
const { taoMoiTruong, boKiem } = require("./fake_dom");
const [, , thuMuc, uiJson] = process.argv;
const UI = JSON.parse(uiJson);
const { kiem, ketThuc } = boKiem();

const IDS = ["man-hinh", "chan-trang", "thong-bao", "dau-trang"];
const FILES = ["landing_chung.js", "landing_popup.js", "landing_khoi.js", "landing.js"];
const STATUS_MO = { huong2_mo: true, demo_mo: true, huong1_web_mo: false, thong_bao: "Thông báo thử" };

/** Nạp lại trang với bộ chữ và công tắc cho trước; trả về môi trường và các hàm tìm phần tử. */
async function nap(ui, status, luuLocal = {}) {
  const mt = taoMoiTruong({ ids: IDS, api: { "/api/content/landing": { status: 200, body: ui }, "/api/status": { status: status ? 200 : 500, body: status || {} } } });
  mt.luuLocal = luuLocal;
  const ma = FILES.map((f) => fs.readFileSync(path.join(thuMuc, f), "utf-8")).join("\n") + "\n;globalThis.T = { ND, moPopup, dongPopup, POPUP };";
  (0, eval)(ma);
  await mt.nho();
  const tim = (f) => [...mt.theo["dau-trang"].find(f), ...mt.theo["man-hinh"].find(f), ...mt.theo["chan-trang"].find(f), ...mt.document.body.find(f)];
  return { mt, tim, T: globalThis.T };
}

const hrefs = (tim, tienTo) => tim((n) => n.tag === "a" && (n.attrs.href || "").startsWith(tienTo));
const nutChu = (tim, chu) => tim((n) => n.tag === "button" && n.textContent === chu);

(async () => {
  // ---------- Trang chủ, công tắc mở
  let { mt, tim, T } = await nap(UI, STATUS_MO);
  const man = mt.theo["man-hinh"];
  kiem(!mt.theo["thong-bao"].hidden && mt.theo["thong-bao"].textContent === "Thông báo thử", "thông báo hiện ở đầu trang");

  // Header: tên, 5 liên kết neo trỏ tới khối có thật, nút Tham gia
  const dau = mt.theo["dau-trang"];
  const neo = dau.find((n) => n.tag === "a" && (n.attrs.href || "").startsWith("#") && n.attrs.href !== "#dau-trang-chu");
  kiem(neo.length === 5, "header có 5 liên kết neo");
  kiem(neo.map((n) => n.textContent).join("|") === "Giới thiệu|Bạn sẽ làm gì?|Quyền riêng tư|Hỏi đáp|Liên hệ", "chữ và thứ tự liên kết neo");
  const idKhoi = new Set(man.find((n) => n.tag === "section").map((n) => n.attrs.id));
  kiem(neo.every((n) => idKhoi.has(n.attrs.href.slice(1))), "mọi liên kết neo trỏ tới một khối có id");
  kiem(dau.textContent.includes("SparkMind"), "header có tên SparkMind");
  kiem(dau.find((n) => n.tag === "button" && n.textContent === "Tham gia").length === 1, "header có nút Tham gia");

  // Thứ tự khối
  const thuTu = man.find((n) => n.tag === "section").map((n) => n.attrs.id);
  kiem(thuTu.join(",") === "dau-trang-chu,gioi-thieu,ban-se-lam-gi,quy-trinh,ket-qua,quyen-rieng-tu,hoi-dap,lien-he", "thứ tự các khối: " + thuTu);
  kiem(man.find((n) => n.tag === "li" && n.attrs.class === "lp-buoc").length === 5, "5 bước quy trình");
  kiem(man.find((n) => n.attrs.class === "lp-cau-hd").length === 5, "5 câu hỏi đáp");
  kiem(tim((n) => n.tag === "footer").length === 1 && mt.theo["chan-trang"].textContent.includes("© 2026 SparkMind"), "có chân trang");

  // Liên hệ, demo, bài dở, đồng ý
  const mail = hrefs(tim, "mailto:");
  kiem(mail.length === 1 && mail[0].attrs.href === "mailto:nguyenthitrang.ttd@gmail.com" && mail[0].textContent === "nguyenthitrang.ttd@gmail.com", "mailto đúng");
  kiem(man.textContent.includes(UI.nguoi_thuc_hien.don_vi), "đơn vị hiện ra từ don_vi");
  const demo = tim((n) => n.tag === "a" && n.attrs.href === "/play/#demo");
  kiem(demo.length === 1 && demo[0].textContent === "Thử bản demo", "link demo đúng /play/#demo");
  kiem(tim((n) => (n.attrs.class || "").includes("the-bai-do")).length === 0, "không có bài dở thì không có thẻ bài dở");
  kiem(tim((n) => n.attrs.class === "lp-lien-ket" && (n.attrs.href || "").startsWith("http")).length === 0, "dong_y_url trống thì không hiện liên kết");

  // Hai thẻ hướng: mở, có nút Tìm hiểu và tham gia
  const theMo = nutChu(tim, "Tìm hiểu và tham gia");
  kiem(theMo.length === 2 && theMo.every((n) => !n.disabled), "hai thẻ đều có nút Tìm hiểu và tham gia bấm được");
  kiem(nutChu(tim, "Tham gia nghiên cứu").length === 1, "nút Tham gia nghiên cứu ở phần mở đầu");

  // Popup: mỗi nút Tham gia đều mở popup, focus vào popup, Esc đóng và trả focus
  const nutMo = [...dau.find((n) => n.tag === "button" && n.textContent === "Tham gia"), ...nutChu(tim, "Tham gia nghiên cứu"), ...theMo];
  for (const nut of nutMo) {
    nut.focus(); nut.click();
    const hop = mt.document.body.find((n) => n.attrs.role === "dialog");
    kiem(hop.length === 1 && hop[0].attrs["aria-modal"] === "true", "popup mở (role=dialog, aria-modal) từ: " + nut.textContent);
    kiem(mt.document.body.classList.contains("lp-khoa-cuon"), "popup khóa cuộn trang phía sau");
    mt.phat("keydown", { key: "Escape" });
    kiem(mt.document.body.find((n) => n.attrs.role === "dialog").length === 0 && mt.document.activeElement === nut, "Esc đóng popup và trả focus về nút đã mở");
  }

  // Popup: nút đóng, bấm ra ngoài, bấm trong hộp không đóng, Tab xoay vòng
  nutMo[0].focus(); nutMo[0].click();
  const nen = mt.document.body.find((n) => n.attrs.class === "lp-phu-nen")[0];
  const hop = nen.find((n) => n.attrs.role === "dialog")[0];
  kiem(mt.document.activeElement.attrs.class === "lp-dong", "mở từ header thì focus vào nút đóng");
  nen.dispatch("click", { target: hop });
  kiem(mt.document.body.find((n) => n.attrs.role === "dialog").length === 1, "bấm trong hộp không đóng popup");
  const cacNut = T.POPUP.canh;
  cacNut[cacNut.length - 1].focus(); mt.phat("keydown", { key: "Tab" });
  kiem(mt.document.activeElement === cacNut[0], "Tab ở phần tử cuối quay về phần tử đầu");
  mt.phat("keydown", { key: "Tab", shiftKey: true });
  kiem(mt.document.activeElement === cacNut[cacNut.length - 1], "Shift+Tab ở phần tử đầu nhảy xuống cuối");
  nen.dispatch("click", { target: nen });
  kiem(mt.document.body.find((n) => n.attrs.role === "dialog").length === 0 && mt.document.activeElement === nutMo[0], "bấm ra ngoài đóng popup, trả focus");
  nutMo[0].click(); mt.document.body.find((n) => n.attrs.class === "lp-dong")[0].click();
  kiem(mt.document.body.find((n) => n.attrs.role === "dialog").length === 0, "nút đóng hoạt động");

  // Lựa chọn trong popup: hướng 1 -> /huong-1, hướng 2 -> /play/ (màn chào có ô nhập mã)
  theMo[1].click();
  const a1 = mt.document.body.find((n) => n.tag === "a" && n.attrs.href === "/huong-1" && n.textContent === "Chọn Hướng 1");
  const a2 = mt.document.body.find((n) => n.tag === "a" && n.attrs.href === "/play/" && n.textContent === "Chọn Hướng 2");
  kiem(a1.length === 1 && a2.length === 1, "popup có hai lựa chọn dẫn /huong-1 và /play/");
  kiem(mt.document.activeElement === a2[0], "bấm thẻ hướng 2 thì focus lựa chọn hướng 2");
  T.dongPopup();

  // Accordion mở được bằng bàn phím: nút thật, aria-expanded đổi
  const hoi = man.find((n) => n.tag === "button" && n.attrs.class === "lp-hoi")[0];
  const vung = man.find((n) => n.attrs.id === hoi.attrs["aria-controls"])[0];
  kiem(hoi.attrs["aria-expanded"] === "false" && vung.hasAttribute("hidden"), "câu hỏi đáp ban đầu đóng");
  hoi.click();
  kiem(hoi.attrs["aria-expanded"] === "true" && !vung.hasAttribute("hidden"), "bấm câu hỏi thì mở câu trả lời");
  hoi.click();
  kiem(hoi.attrs["aria-expanded"] === "false" && vung.hasAttribute("hidden"), "bấm lần nữa thì đóng");

  // Menu điện thoại
  const nutMenu = dau.find((n) => n.attrs.class === "lp-nut-menu")[0];
  nutMenu.click();
  kiem(nutMenu.attrs["aria-expanded"] === "true" && dau.classList.contains("mo-menu"), "menu điện thoại mở");
  neo[0].click();
  kiem(nutMenu.attrs["aria-expanded"] === "false" && !dau.classList.contains("mo-menu"), "bấm liên kết thì đóng menu");

  // ---------- dong_y_url hợp lệ thì hiện; địa chỉ lạ thì không
  const ui2 = JSON.parse(JSON.stringify(UI)); ui2.dong_y_url = "https://example.org/dong-y";
  ({ mt, tim } = await nap(ui2, STATUS_MO));
  kiem(tim((n) => n.attrs.class === "lp-lien-ket" && n.attrs.href === "https://example.org/dong-y").length === 1, "dong_y_url có thì hiện liên kết");
  ui2.dong_y_url = "javascript:alert(1)";
  ({ mt, tim } = await nap(ui2, STATUS_MO));
  kiem(tim((n) => (n.attrs.href || "").startsWith("javascript")).length === 0, "chặn javascript:");

  // ---------- Hướng 2 đóng, hướng 1 chưa có link
  const ui3 = JSON.parse(JSON.stringify(UI)); ui3.huong1_url = "";
  ({ mt, tim, T } = await nap(ui3, { ...STATUS_MO, huong2_mo: false }));
  kiem(nutChu(tim, "Tìm hiểu và tham gia").length === 0, "hai thẻ khóa: không còn nút Tìm hiểu và tham gia");
  const dong = tim((n) => n.tag === "button" && n.textContent === "Đã đóng");
  kiem(dong.length === 1 && dong[0].disabled, "huong2_mo=false: thẻ hướng 2 hiện Đã đóng, không bấm được");
  const sap = tim((n) => n.tag === "button" && n.textContent === "Sắp mở");
  kiem(sap.length === 1 && sap[0].disabled, "huong1_url trống: thẻ hướng 1 hiện Sắp mở, không bấm được");
  kiem(mt.theo["man-hinh"].textContent.includes(UI.hai_huong.huong2.da_dong_mo_ta), "thẻ hướng 2 đóng có lời giải thích");
  mt.theo["dau-trang"].find((n) => n.tag === "button" && n.textContent === "Tham gia")[0].click();
  const popup = mt.document.body;
  kiem(popup.find((n) => n.tag === "a" && n.textContent.startsWith("Chọn Hướng")).length === 0, "popup: cả hai lựa chọn bị khóa");
  kiem(popup.find((n) => n.tag === "button" && n.disabled && n.textContent === "Đã đóng").length === 1, "popup: hướng 2 hiện Đã đóng");
  kiem(popup.find((n) => n.tag === "button" && n.disabled && n.textContent === "Sắp mở").length === 1, "popup: hướng 1 hiện Sắp mở");
  T.dongPopup();

  // ---------- Có bài dở; không đọc được công tắc thì coi như mở
  ({ mt, tim } = await nap(UI, null, { sparkmind_session_token: "tok" }));
  const bd = tim((n) => (n.attrs.class || "").includes("the-bai-do"));
  kiem(bd.length === 1 && bd[0].find((n) => n.tag === "a" && n.attrs.href === "/play/").length === 1, "thẻ bài dở dẫn /play/");
  kiem(nutChu(tim, "Tìm hiểu và tham gia").length === 2, "không đọc được công tắc: coi như mở");

  // ---------- Không tải được chữ
  const hong = taoMoiTruong({ ids: IDS, api: { "/api/content/landing": { status: 500, body: {} }, "/api/status": { status: 200, body: {} } } });
  (0, eval)(FILES.map((f) => fs.readFileSync(path.join(thuMuc, f), "utf-8")).join("\n").replace(/^const (ND|goc)\b/gm, "var $1"));
  await hong.nho();
  kiem(hong.theo["man-hinh"].textContent.startsWith("Không tải được"), "lỗi tải chữ thì báo một dòng");

  ketThuc();
})();
