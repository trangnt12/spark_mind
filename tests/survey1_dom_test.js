// Chạy phần logic của web/survey1_gui.js trong node (không cần trình duyệt): khóa nộp lại 24 giờ, bài gửi, gộp thời gian.
// Dùng: node survey1_dom_test.js <thư mục web>
const fs = require("fs");
const path = require("path");
const { boKiem } = require("./fake_dom");
const { kiem, ketThuc } = boKiem();
const MA = fs.readFileSync(path.join(process.argv[2], "survey1_gui.js"), "utf-8");

let bayGio = 1_800_000_000_000;
const kho = {};
Object.assign(global, {
  location: { search: "" }, tt: { tl: {}, ui: { loi: {} } }, KHOA_MAN: "m",
  localStorage: { getItem: (k) => (k in kho ? kho[k] : null), setItem: (k, v) => { kho[k] = String(v); }, removeItem: (k) => { delete kho[k]; } },
  docNhap: () => ({}), tgLay: () => null,
});
Date.now = () => bayGio;
(0, eval)(MA + "\nglobalThis.__t = { s1, daNopGanDay, ghiDaNop, thuBaiGui, gopThoiGian, laCheDoThu, chuLoiGui };");
const T = globalThis.__t;

// --- khóa nộp lại ---
T.s1.gioKhoa = 24;
kiem(!T.daNopGanDay(), "chưa nộp thì chưa khóa");
T.ghiDaNop();
kiem(T.daNopGanDay(), "vừa nộp thì khóa");
bayGio += 23 * 3_600_000;
kiem(T.daNopGanDay(), "23 giờ sau vẫn khóa");
bayGio += 2 * 3_600_000;
kiem(!T.daNopGanDay(), "25 giờ sau mở lại");
T.ghiDaNop();
T.s1.thu = true;
kiem(!T.daNopGanDay(), "chế độ thử không bị khóa");
delete kho.sparkmind_huong1_da_nop;
T.ghiDaNop();
kiem(!("sparkmind_huong1_da_nop" in kho), "chế độ thử không ghi dấu đã nộp");
T.s1.thu = false;
global.location.search = "?thu=1";
kiem(T.laCheDoThu(), "?thu=1 bật chế độ thử");

// --- bài gửi ---
T.s1.maChua = 4;
const tl = { dongY: true, nguoiLon: true, A1: 6, A2: 2, A3: "  Trường X ", A4: 1, B1: [1], B1_other: " ", B2: 1, B3: [1], B5: 1, B6: [1], B7: 1,
  B4_1: 3, B4_2: 3, B4_3: 3, B4_4: 3, B4_5: 3, B4_6: 3, B4_7: 3, C1: 4, C2: 4, C3: 4, C4: 4, C5: 4, C6: 1, email: "a@b.c", ten: "An" };
global.tt.tl = tl;
let b = T.thuBaiGui("");
kiem(b.A3 === "Trường X" && b.B1_other === "" && b.B4_7 === 3 && b.C6 === 1 && b.thu === false, "bài gửi đủ câu, A3 bỏ khoảng trắng");
kiem(!("email" in b) && !("ten" in b) && !Object.keys(b).some((k) => /mail|name|ho_ten/i.test(k)), "bài gửi không có email hay tên");
kiem(b.ghi_chu_them === "" && b.consent === true && b.guardian_consent === true, "có trường ẩn, đồng ý, xác nhận");
global.tt.tl = { ...tl, A4: 4 };
b = T.thuBaiGui("");
kiem(!("B1" in b) && !("B4_1" in b) && !("B1_other" in b) && b.C1 === 4, "chưa bao giờ dùng AI: không gửi phần B");

// --- gộp thời gian ---
global.docNhap = () => ({ bd: bayGio - 90_000, tg_form_b: { khoang: { B4_1: 2000 }, sua: { B4_1: 5000 }, an: 100, tong: 20000, luc: 1 } });
global.tgLay = () => ({ khoang_ms: { C1: 1500 }, sua_cuoi_ms: {}, an_tab_ms: 50, tong_ms: 7000 });
let g = T.gopThoiGian(false);
kiem(g.khoang_ms.B4_1 === 2000 && g.khoang_ms.C1 === 1500 && g.an_tab_ms === 150 && g.tong_ms === 90_000, "gộp thời gian B và C, tổng từ lúc bắt đầu");
g = T.gopThoiGian(true);
kiem(!("B4_1" in g.khoang_ms) && g.khoang_ms.C1 === 1500, "bỏ phần B thì bỏ số đo B cũ");
global.docNhap = () => ({ bd: bayGio - 9e12 });
kiem(T.gopThoiGian(true).tong_ms === 86_400_000, "tổng thời gian bị chặn ở 1 ngày");

// --- chữ lỗi ---
global.tt.ui.loi = { thieu_dong_y: "A", thieu_cau: "B" };
T.s1.ui = { loi: { qua_lon: "L", gia_tri_sai: "G" } };
kiem(T.chuLoiGui({ status: 422, du_lieu: { detail: "thieu_dong_y" } }) === "A", "422 mã lỗi -> chữ");
kiem(T.chuLoiGui({ status: 422, du_lieu: { detail: [{ loc: [] }] } }) === "B", "422 dạng danh sách -> thiếu câu");
kiem(T.chuLoiGui({ status: 413, du_lieu: {} }) === "L", "413 -> quá lớn");
ketThuc();
