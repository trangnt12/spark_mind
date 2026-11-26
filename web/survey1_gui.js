// Khảo sát hướng 1 (web): THU câu trả lời thành bài gửi và GỬI lên /api/huong1/submit, kèm dấu "đã nộp" trong trình duyệt.
// Dùng lại goiApi, thieuCau, baoLoi, chuLoi... của app.js; nhap.js (bản nháp) và thoigian.js (đo thời gian).
// Không có ô email hay tên: hướng 1 không thu hai thứ đó.
"use strict";

const KHOA_DA_NOP = "sparkmind_huong1_da_nop";    // localStorage: lúc (mili giây) trình duyệt này nộp xong
const TOI_DA_MS = 86_400_000;                      // chặn số vô lý (1 ngày), khớp THOI_GIAN_CAU_TOI_DA_MS ở máy chủ
const CAU_B4 = Array.from({ length: 7 }, (_, i) => "B4_" + (i + 1));
const CAU_B = ["B1", "B2", "B3", ...CAU_B4, "B5", "B6", "B7"];
const CAU_C = ["C1", "C2", "C3", "C4", "C5", "C6"];
const s1 = { ui: null, gioKhoa: 24, thu: false, maChua: 0 };   // chữ riêng của trang, số giờ khóa nộp lại, chế độ thử, mã A4 "Chưa bao giờ"

/** Đường dẫn thử (?thu=1): bài gán nhãn "thu", không ghi vào dữ liệu gốc, không bị khóa nộp lại. */
function laCheDoThu() {
  return new URLSearchParams(location.search).get("thu") === "1";
}

/** Trình duyệt này đã nộp trong vòng s1.gioKhoa giờ chưa? (chỉ chặn ở trình duyệt; xóa dữ liệu trình duyệt thì nộp lại được). */
function daNopGanDay() {
  try {
    const luc = Number(localStorage.getItem(KHOA_DA_NOP));
    return !s1.thu && luc > 0 && Date.now() - luc < s1.gioKhoa * 3_600_000;
  } catch { return false; }
}

/** Đánh dấu đã nộp (không đánh dấu ở chế độ thử). */
function ghiDaNop() {
  if (s1.thu) return;
  try { localStorage.setItem(KHOA_DA_NOP, String(Date.now())); } catch { /* không lưu được: bỏ qua */ }
}

/** Gộp số đo thời gian: khối B4 (lưu trong bản nháp khi chuyển sang C) + khối C (đang đo) + tổng từ lúc bấm Tiếp tục ở màn đồng ý. */
function gopThoiGian(boB) {
  const b = boB ? null : docNhap().tg_form_b, c = tgLay(), bd = docNhap().bd;
  const tong = bd ? Date.now() - bd : (c ? c.tong_ms : 0);
  return {
    khoang_ms: { ...(b ? b.khoang : {}), ...(c ? c.khoang_ms : {}) },
    sua_cuoi_ms: { ...(b ? b.sua : {}), ...(c ? c.sua_cuoi_ms : {}) },
    an_tab_ms: Math.min(TOI_DA_MS, (b ? b.an : 0) + (c ? c.an_tab_ms : 0)),
    tong_ms: Math.max(0, Math.min(TOI_DA_MS, Math.round(tong))),
  };
}

/** Thu mọi câu trả lời (mã lựa chọn) thành bài gửi. Người chưa bao giờ dùng AI thì không gửi phần B. */
function thuBaiGui(giaTriBay) {
  const t = tt.tl, boB = t.A4 === s1.maChua;
  const body = { consent: !!t.dongY, guardian_consent: !!t.nguoiLon, thu: s1.thu, ghi_chu_them: giaTriBay, A3: (t.A3 || "").trim() };
  ["A1", "A2", "A4", ...CAU_C].forEach((id) => { body[id] = t[id]; });
  if (!boB) {
    CAU_B.forEach((id) => { body[id] = t[id]; });
    ["B1", "B3", "B6"].forEach((id) => { body[id + "_other"] = (t[id + "_other"] || "").trim(); });
  }
  body.thoi_gian = gopThoiGian(boB);
  return body;
}

/** Chữ báo lỗi cho một lần gửi không thành công (422: mã lỗi ngắn của máy chủ; 423: đã có trang "chưa mở" thay thế). */
function chuLoiGui(r) {
  const ma = typeof r.du_lieu.detail === "string" ? r.du_lieu.detail : "";
  if (r.status === 422) return tt.ui.loi[ma] || s1.ui.loi[ma] || tt.ui.loi.thieu_cau;
  if (r.status === 413) return s1.ui.loi.qua_lon;
  return chuLoi(r.status);
}

/** Bấm nộp ở phần C: kiểm tra câu bắt buộc, gửi, xong thì đánh dấu đã nộp, xóa bản nháp và hiện màn cảm ơn. Trả status cho nutGui. */
async function nopKhaoSat(hopLoi, oBay) {
  if (thieuCau(CAU_C)) return 200;
  const r = await goiApi("/api/huong1/submit", thuBaiGui(oBay.value));
  if (r.status !== 200) { baoLoi(hopLoi, chuLoiGui(r)); return r.status; }
  ghiDaNop();
  tgXoa();
  xoaNhap();
  sessionStorage.removeItem(KHOA_MAN);
  manCamOn();
  return 200;
}
