// Trang kết quả dùng chung cho demo và nghiên cứu. Dùng lại h(), hienThi(), tieuDe()... của app.js.
// Mọi chữ lấy từ /api/content/results-ui (tt.kq) và /api/content/form-b (tt.fb); file này không viết cứng chữ.
// Không khen/chê, không gắn nhãn "yếu/giỏi", không gợi ý hành động nhân quả.
"use strict";

// ---------- Tính số hiển thị ----------

/** Điểm dự đoán -> khoảng "điểm ± sai số", cắt trong 0–100, làm tròn số nguyên. */
function khoangDiem(diem, saiSo) {
  return { tu: Math.round(Math.max(0, diem - saiSo)), den: Math.round(Math.min(100, diem + saiSo)) };
}

/** Xác suất (0–1) làm tròn tới 5%. */
function lam5(xacSuat) {
  return Math.round(xacSuat * 20) * 5;
}

// ---------- a. Mức tự đánh giá dự đoán: thanh 3 đoạn ----------

function theMuc(kq) {
  const u = tt.kq;
  const doan = Object.keys(u.ten_muc).map((m) => h("div", { class: "doan" + (m === kq.muc ? " chon" : "") },
    h("span", { class: "do tuong-chay" }), h("small", {}, u.ten_muc[m])));
  return h("div", { class: "the" }, h("h2", {}, u.nhan_muc),
    h("div", { class: "thanh-muc", role: "img", "aria-label": u.ten_muc[kq.muc] }, doan),
    h("p", { class: "ten-muc" }, u.ten_muc[kq.muc]), h("p", { class: "mo-ta" }, u.mo_ta_muc[kq.muc]));
}

// ---------- b. Điểm ước lượng dưới dạng khoảng ----------

function theDiem(kq) {
  const u = tt.kq, k = khoangDiem(kq.diem_du_doan, u.diem.sai_so);
  const dai = h("span", { class: "khoang tuong-chay", style: `--tu:${k.tu}%;--den:${k.den}%` });
  return h("div", { class: "the" }, h("h2", {}, u.nhan_diem),
    h("small", { class: "mo-ta" }, u.diem.giai_thich),
    h("p", { class: "so-khoang" }, u.diem.khoang.replace("{tu}", k.tu).replace("{den}", k.den)),
    h("div", { class: "duong-diem", "aria-hidden": "true" }, dai),
    h("div", { class: "moc-diem", "aria-hidden": "true" }, h("span", {}, "0"), h("span", {}, "100")),
    h("p", { class: "mo-ta" }, u.diem.ghi_chu));
}

// ---------- c. Xác suất 3 mức (làm tròn 5%) ----------

function dongXacSuat(m, xacSuat) {
  const u = tt.kq, p = lam5(xacSuat);
  const chu = p === 0 ? u.xac_suat.duoi_5 : u.xac_suat.khoang.replace("{p}", p);
  return h("li", { class: "dong-xs" }, h("span", { class: "ten-xs" }, u.ten_muc[m]),
    h("span", { class: "thanh-xs", "aria-hidden": "true" },
      h("span", { class: "tuong-chay", style: `--p:${Math.max(p, 2)}%` })),
    h("span", { class: "chu-xs" }, chu));
}

function theXacSuat(kq) {
  const u = tt.kq;
  return h("div", { class: "the" }, h("h2", {}, u.nhan_xac_suat),
    h("ul", { class: "ds-xs" }, Object.keys(u.ten_muc).map((m) => dongXacSuat(m, kq.xac_suat[m]))),
    h("p", { class: "mo-ta" }, u.xac_suat.ghi_chu));
}

// ---------- d. Cần lưu ý ----------

function theLuuY() {
  const u = tt.kq.gioi_han;
  return h("div", { class: "the luu-y", role: "note" }, h("h2", {}, u.tieu_de),
    u.doan.map((d) => h("p", { class: "mo-ta" }, d)));
}

// ---------- e. Mô hình đã dựa vào đâu? (thu gọn mặc định) ----------

/** Một thẻ câu trả lời: mũi tên, chữ đầy đủ của câu B4 (từ form_b), chiều + độ lớn, giá trị bạn chọn.
 *  Hai chiều dùng màu trung tính như nhau (không xanh/đỏ) để không giống khen hay chê. */
function theDongGop(d) {
  const u = tt.kq, dong = cauB4().cac_dong.find((x) => x.id === d.id);
  return h("li", { class: "the-dg chieu-" + d.chieu }, bieuTuong(d.chieu === "tang" ? "bd-len" : "bd-xuong", "mui-ten"),
    h("div", {}, h("p", { class: "dg-cau" }, dong.nhan + " " + dong.text),
      h("p", { class: "dg-nhan" }, u.chieu[d.chieu] + " · " + u.do_lon[d.do_lon]),
      h("p", { class: "dg-chon" }, u.dong_gop.ban_chon.replace("{gia_tri}", tt.fb.thang_dong_y[d.gia_tri]))));
}

function mucDongGop(kq) {
  const u = tt.kq;
  return h("details", { class: "the dong-gop" },
    h("summary", {}, h("span", { class: "tieu-de-dg" }, u.nhan_dong_gop), h("small", {}, u.dong_gop.mo_ta)),
    h("p", { class: "canh-bao" }, bieuTuong("bd-canh-bao"), u.dong_gop.canh_bao),
    h("ul", { class: "ds-dg" }, kq.dong_gop.map(theDongGop)));
}

// ---------- Ghép trang ----------

/** Cho các thanh chạy mượt: đặt trạng thái cuối sau 2 khung hình (CSS lo thời gian; giảm chuyển động thì hiện ngay). */
function chayThanh() {
  const cac = goc.querySelectorAll(".tuong-chay");
  requestAnimationFrame(() => requestAnimationFrame(() => cac.forEach((e) => e.classList.add("chay"))));
}

/** Hiện trang kết quả. tuyChon: { buoc: số bước thanh tiến độ, nutChinh: chữ nút, khiBam: việc khi bấm nút }. */
function manKetQua(kq, tuyChon) {
  const nut = h("button", { type: "button", onclick: tuyChon.khiBam }, tuyChon.nutChinh);
  hienThi(tuyChon.buoc, tieuDe("ket_qua", tt.kq.tieu_de), theMuc(kq), theDiem(kq), theXacSuat(kq),
    theLuuY(), mucDongGop(kq), khungNut(nut));
  danhDauGioiThieu();
  chayThanh();
}

// ---------- Luồng nghiên cứu: màn hoàn thành gọi /api/research/result ----------

/** Màn cảm ơn cuối cùng sau khi xem kết quả. */
function manCamOn() {
  hienThi(TONG_BUOC, tieuDe("hoan_thanh", tt.ui.hoan_thanh.tieu_de), h("div", { class: "the" }, cacDoan(tt.ui.hoan_thanh.mo_ta)));
  danhDauGioiThieu();
}

/** Chưa có kết quả: 409 (chưa xong các phần) là chuyện bình thường nên hiện thông báo, không phải lỗi đỏ. */
function manChuaCoKetQua(r) {
  const chu = r.status === 409 ? tt.kq.chua_xong_giao_dien
    : (r.status === 422 && typeof r.du_lieu.detail === "string") ? r.du_lieu.detail : chuLoi(r.status);
  const cacNut = r.status === 409 ? [] : [khungNut(h("button", { type: "button", onclick: manHoanThanh }, tt.ui.chung.nut_thu_lai))];
  hienThi(TONG_BUOC, h("div", { class: "the" }, h("p", { class: "mo-ta", role: "status" }, chu)), ...cacNut);
  danhDauGioiThieu();
  if (r.status === 401) loiPhien(null, 401);       // phiên hỏng: xóa token và về màn nhập mã
}

/** Màn hoàn thành của người tham gia. Máy chủ chỉ trả kết quả khi participants đã có completed_at (nếu chưa thì 409). */
async function manHoanThanh() {
  hienThi(TONG_BUOC, h("div", { class: "the" }, h("p", { class: "mo-ta", role: "status" }, tt.kq.dang_tinh)));
  const r = await goiApi("/api/research/result", undefined, { "X-Session-Token": tt.token });
  if (r.status === 200) manKetQua(r.du_lieu, { buoc: TONG_BUOC, nutChinh: tt.kq.nut.hoan_thanh, khiBam: manCamOn });
  else manChuaCoKetQua(r);
}
