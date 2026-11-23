// Bản nháp câu trả lời đang gõ dở, để tải lại trang (F5) không mất. Dùng sessionStorage: chỉ sống trong tab này,
// đóng tab là mất; gắn với session_token; xóa khi nộp xong phần đó hoặc khi bấm "Không phải bạn?".
// Câu trả lời đã nộp thì lấy từ máy chủ (GET /api/research/progress), không nằm ở đây.
"use strict";

const KHOA_NHAP = "sparkmind_nhap";

/** Đọc toàn bộ bản nháp của người đang làm (rỗng nếu của token khác hoặc hỏng). Trước khi có token thì token là chuỗi rỗng. */
function docNhap() {
  try {
    const d = JSON.parse(sessionStorage.getItem(KHOA_NHAP) || "{}");
    return d.token === (tt.token || "") ? d : {};
  } catch { return {}; }
}

/** Ghi một phần của bản nháp: "tl" (khảo sát), "g1" (game 1), "g2" (game 2). */
function ghiNhap(phan, giaTri) {
  if (tt.demo) return;
  try { sessionStorage.setItem(KHOA_NHAP, JSON.stringify({ ...docNhap(), token: tt.token || "", [phan]: giaTri })); } catch { /* đầy bộ nhớ: bỏ qua */ }
}

/** Xóa một phần (đã nộp xong) hoặc xóa hết (không truyền gì). */
function xoaNhap(phan) {
  if (!phan) { sessionStorage.removeItem(KHOA_NHAP); return; }
  const d = docNhap();
  delete d[phan];
  try { sessionStorage.setItem(KHOA_NHAP, JSON.stringify(d)); } catch { /* bỏ qua */ }
}

// ---------- Màn đang xem: tải lại trang (F5) thì ở lại đúng màn này ----------
// Còn sessionStorage (cùng tab) = vừa tải lại. Mất sessionStorage (đóng tab/trình duyệt rồi vào lại) = hỏi "tiếp tục hay làm bài mới".
const KHOA_MAN = "sparkmind_man";

/** Ghi màn đang xem (tên màn, token, mã đang nhập nếu chưa có token). */
function datMan(ten) {
  if (tt.demo) return;
  try { sessionStorage.setItem(KHOA_MAN, JSON.stringify({ man: ten, token: tt.token || "", ma: tt.ma || "" })); } catch { /* bỏ qua */ }
}

/** Màn đang xem lần trước trong tab này, hoặc null. */
function docMan() {
  try { return JSON.parse(sessionStorage.getItem(KHOA_MAN) || "null"); } catch { return null; }
}
