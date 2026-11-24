// Đo thời gian trả lời từng câu Likert (form B: B4_1..B4_7; khối C: C1..C5) để máy chủ GẮN CỜ làm bài quá nhanh / bị gián đoạn.
// Chỉ ghi SỐ (mili giây), không ghi gì khác. Không báo gì cho người chơi. Số đo do trình duyệt tự đo nên chỉ để gắn cờ.
// Với mỗi câu: khoảng cách tới câu trả lời trước (câu đầu tính từ lúc hiện trang) khi trả lời LẦN ĐẦU; lần sửa cuối chỉ ghi mốc thời gian.
// Thời gian tab bị ẩn (Page Visibility API) được TRỪ khỏi mọi khoảng cách và được ghi riêng ở an_tab_ms.
// Dùng lại ghiNhap/xoaNhap của nhap.js để tải lại trang (F5) không mất số đo.
"use strict";

const TG = { ten: "", cau: [], khoang: {}, sua: {}, anTab: 0, anCu: 0, anTu: null, goc: 0, lanCuoi: 0, tongTruoc: 0 };

/** Thời gian "đang xem" (mili giây) tính từ lúc hiện trang, đã trừ thời gian tab bị ẩn. */
function tgHoat() {
  const bay = performance.now();
  return Math.round(bay - TG.goc - TG.anTab - (TG.anTu === null ? 0 : bay - TG.anTu));
}

/** Bắt đầu đo cho một khối ("form_b" hoặc "khoi_c"). Vào lại cùng khối (Quay lại, F5) thì giữ số đo cũ. Bản demo không đo. */
function tgBat(ten, cacCau) {
  if (tt.demo) { TG.ten = ""; return; }
  const cu = TG.ten === ten ? { khoang: TG.khoang, sua: TG.sua, an: TG.anCu + TG.anTab, tong: TG.tongTruoc + tgHoat(), luc: 0 } : (docNhap()["tg_" + ten] || null);
  Object.assign(TG, { ten, cau: cacCau, khoang: cu ? cu.khoang : {}, sua: cu ? cu.sua : {}, anTab: 0, goc: performance.now(),
    lanCuoi: 0, anTu: document.hidden ? performance.now() : null, tongTruoc: cu ? cu.tong + (cu.luc ? Date.now() - cu.luc : 0) : 0 });
  TG.anCu = cu ? cu.an : 0;   // thời gian ẩn tab của các lần xem trước
}

/** Ghi nhận một lần trả lời câu `id` (gọi từ sự kiện change). Lần đầu: ghi khoảng cách; các lần sau: chỉ ghi mốc sửa cuối. */
function tgGhi(id) {
  if (!TG.ten || !TG.cau.includes(id)) return;
  const luc = tgHoat();
  if (id in TG.khoang) TG.sua[id] = luc; else TG.khoang[id] = Math.max(0, luc - TG.lanCuoi);
  TG.lanCuoi = luc;
  ghiNhap("tg_" + TG.ten, { khoang: TG.khoang, sua: TG.sua, an: TG.anCu + TG.anTab, tong: TG.tongTruoc + luc, luc: Date.now() });
}

/** Gói số đo gửi kèm khi nộp (đúng tên trường máy chủ nhận). null nếu không đo (demo). */
function tgLay() {
  if (!TG.ten) return null;
  return { khoang_ms: TG.khoang, sua_cuoi_ms: TG.sua, an_tab_ms: TG.anCu + TG.anTab, tong_ms: TG.tongTruoc + tgHoat() };
}

/** Nộp xong thì bỏ số đo của khối này. */
function tgXoa() {
  if (TG.ten) xoaNhap("tg_" + TG.ten);
  TG.ten = ""; TG.khoang = {}; TG.sua = {};
}

// Tab ẩn/hiện: cộng dồn thời gian ẩn để trừ đi
document.addEventListener("visibilitychange", () => {
  if (!TG.ten) return;
  if (document.hidden) TG.anTu = performance.now();
  else if (TG.anTu !== null) { TG.anTab += Math.round(performance.now() - TG.anTu); TG.anTu = null; }
});
