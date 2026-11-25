// Bản demo công khai (không cần mã): giới thiệu ngắn -> 7 câu B4 -> trang kết quả.
// Dùng lại h(), goiApi(), hienThi(), luoi()... của app.js. Mọi chữ lấy từ API (/api/content/ui, form-b, results-ui).
// Câu trả lời chỉ ở bộ nhớ trang, không lưu gì. Demo KHÔNG gọi bất kỳ endpoint nghiên cứu nào.
"use strict";

/** Câu B4 (lưới 1–5) lấy từ form_b.json: chữ và thang y hệt form nghiên cứu. */
function cauB4() {
  return tt.fb.phan_b_hanh_vi.find((c) => c.id === "B4");
}

// ---------- Bước 1: giới thiệu ngắn ----------

function manDemoGioiThieu() {
  tt.demo = true; tt.tl = {};                      // bắt đầu mới: xóa câu trả lời cũ (làm lại cũng vào đây)
  const u = tt.ui.demo;
  hienThi(1, tieuDe("demo", u.tieu_de), h("div", { class: "the" }, cacDoan(u.mo_ta)),
    khungNut(h("button", { type: "button", onclick: manDemoCauHoi }, tt.ui.chung.nut_tiep_tuc),
             nutQuayLai(manMa)));
  danhDauGioiThieu();
}

// ---------- Bước 2: 7 câu B4 ----------

/** Đổi lỗi từ máy chủ thành chữ thân thiện (chữ lấy từ content). 429: dùng đúng câu máy chủ trả (có số giây chờ). */
function chuLoiDemo(r) {
  if (r.status === 422) return tt.kq.loi_giao_dien.dau_vao_sai;
  if (r.status === 429 && typeof r.du_lieu.detail === "string") return r.du_lieu.detail;
  return chuLoi(r.status);
}

/** Mã 7 câu của lưới B4, đọc từ form_b.json (không viết cứng). */
function cauDemo() {
  return cauB4().cac_dong.map((d) => d.id);
}

/** Thu 7 câu; thiếu câu nào thì tô đỏ ngay cạnh câu đó. */
function thuDemo() {
  const ids = cauDemo();
  if (thieuCau(ids)) return null;
  return { answers: Object.fromEntries(ids.map((id) => [id, tt.tl[id]])) };
}

/** Gửi 7 câu tới /api/predict/demo (máy chủ không lưu). Thành công thì sang trang kết quả. */
async function guiDemo(hopLoi) {
  const body = thuDemo();
  if (!body) { baoLoi(hopLoi, tt.ui.loi.thieu_cau); return 200; }
  const r = await goiApi("/api/predict/demo", body);
  if (r.status !== 200) { baoLoi(hopLoi, chuLoiDemo(r)); return r.status; }
  manKetQua(r.du_lieu, { buoc: 3, nutChinh: tt.kq.nut.lam_lai, khiBam: manDemoGioiThieu });
  return 200;
}

function manDemoCauHoi() {
  const b4 = cauB4();
  const loi = h("div", { class: "loi an", role: "alert" });
  const nut = nutGui(tt.ui.chung.nut_tiep_tuc, () => guiDemo(loi), loi);
  hienThi(2, h("div", { class: "the" }, luoi(b4.cac_dong, b4)),
    khungNut(loi, nut, nutQuayLai(manDemoGioiThieu)));
}
