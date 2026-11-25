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

/** Thay {dung} và {sai_so_noi} trong chữ bằng số ở results_ui.json (so_mo_hinh): NƠI DUY NHẤT ghi số của mô hình. */
function thaySo(chu) {
  const s = tt.kq.so_mo_hinh;
  return chu.replace("{dung}", s.dung_tren_10).replace("{sai_so_noi}", s.sai_so_noi);
}

// ---------- a. Mức tự đánh giá dự đoán: thanh 3 đoạn ----------

function theMuc(kq) {
  const u = tt.kq;
  const doan = Object.keys(u.ten_muc).map((m) => h("div", { class: "doan" + (m === kq.muc ? " chon" : "") },
    h("span", { class: "do tuong-chay" }), h("small", {}, u.ten_ngan[m])));   // nhãn ngắn để nằm trên 1 dòng trong cột hẹp
  // Thứ bậc chữ: nhãn nhỏ -> kết quả to -> thanh -> một câu mô tả -> ghi chú nhỏ mờ ở cuối
  return h("div", { class: "the the-kq" }, h("h2", { class: "nhan-the" }, u.nhan_muc),
    h("p", { class: "so-lon" }, u.ten_muc[kq.muc]),
    h("div", { class: "thanh-muc", role: "img", "aria-label": u.ten_muc[kq.muc] }, doan),
    h("p", { class: "mo-ta" }, u.mo_ta_muc[kq.muc]),
    h("p", { class: "ghi-nho" }, u.ghi_chu_muc));   // dòng nhỏ nhắc đây chỉ là ước lượng
}

// ---------- b. Điểm ước lượng dưới dạng khoảng ----------

function theDiem(kq) {
  const u = tt.kq, k = khoangDiem(kq.diem_du_doan, u.so_mo_hinh.sai_so_diem);
  const dai = h("span", { class: "khoang tuong-chay", style: `--tu:${k.tu}%;--den:${k.den}%` });
  const chu = u.diem.khoang.replace("{tu}", k.tu).replace("{den}", k.den);   // câu đầy đủ cho trình đọc màn hình
  return h("div", { class: "the the-kq" }, h("h2", { class: "nhan-the" }, u.nhan_diem),
    h("p", { class: "so-lon", "aria-label": chu }, h("span", { "aria-hidden": "true" }, u.diem.so_lon.replace("{tu}", k.tu).replace("{den}", k.den)),
      h("small", { "aria-hidden": "true" }, " " + u.diem.don_vi)),
    h("div", { class: "duong-diem", "aria-hidden": "true" }, dai),
    h("div", { class: "moc-diem", "aria-hidden": "true" }, h("span", {}, "0"), h("span", {}, "100")),
    h("p", { class: "ghi-nho" }, u.diem.giai_thich, " ", thaySo(u.diem.ghi_chu)));
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
  return h("div", { class: "the the-kq" }, h("h2", { class: "nhan-the" }, u.nhan_xac_suat),
    h("ul", { class: "ds-xs" }, Object.keys(u.ten_muc).map((m) => dongXacSuat(m, kq.xac_suat[m]))),
    h("p", { class: "ghi-nho" }, u.xac_suat.ghi_chu));
}

// ---------- d. Cần lưu ý ----------

function theLuuY() {
  const u = tt.kq.gioi_han;
  return h("div", { class: "the luu-y", role: "note" }, h("h2", {}, u.tieu_de),
    h("ul", { class: "ds-luu-y" }, u.doan.map((d) => h("li", {}, thaySo(d)))));   // 5 ý dạng danh sách có đầu dòng
}

// ---------- e. Mô hình đã dựa vào đâu? (thu gọn mặc định) ----------

/** Khối thu gọn mặc định (bấm mới mở): 4 gạch đầu dòng ngắn từ results_ui.json (dong_gop.gach). */
function mucDongGop() {
  const u = tt.kq;
  return h("details", { class: "the dong-gop" },
    h("summary", {}, h("span", { class: "tieu-de-dg" }, u.nhan_dong_gop), h("small", {}, u.dong_gop.mo_ta)),
    h("ul", { class: "ds-luu-y ds-mo-hinh" }, u.dong_gop.gach.map((g) => h("li", {}, thaySo(g)))));
}

/** Nút nổi bật "Xem lại kết quả bài làm" (chỉ ở trang tổng kết, dưới thẻ khả năng của từng mức). */
function theNutXemLai() {
  return h("div", { class: "khung-xem-lai" },
    h("button", { type: "button", class: "nut-xem-lai", onclick: () => manXemLai() }, tt.ui.xem_lai.nut_xem_lai));
}

// ---------- Ghép trang ----------

/** Cho các thanh chạy mượt: đặt trạng thái cuối sau 2 khung hình (CSS lo thời gian; giảm chuyển động thì hiện ngay). */
function chayThanh() {
  const cac = goc.querySelectorAll(".tuong-chay");
  requestAnimationFrame(() => requestAnimationFrame(() => cac.forEach((e) => e.classList.add("chay"))));
}

/** Hiện trang kết quả. tuyChon: { buoc, duoiDiem: khối chèn ngay dưới thẻ xác suất các mức, cuoiTrang: khối thêm ở cuối trang,
 *  nutChinh + khiBam: nút ở chân trang (demo có, trang tổng kết không có) }. */
function manKetQua(kq, tuyChon) {
  const nut = tuyChon.nutChinh ? [khungNut(h("button", { type: "button", onclick: tuyChon.khiBam }, tuyChon.nutChinh))] : [];
  hienThi(tuyChon.buoc, tieuDe("ket_qua", tt.kq.tieu_de), theMuc(kq), theDiem(kq), theXacSuat(kq), tuyChon.duoiDiem || [],
    theLuuY(), mucDongGop(), tuyChon.cuoiTrang || [], nut);
  danhDauGioiThieu();
  document.body.classList.add("man-ket-qua");   // CSS: tiêu đề tối đa 18px trên điện thoại
  chayThanh();
}

// ---------- Luồng nghiên cứu: trang tổng kết cuối gọi /api/research/result ----------

/** Thẻ cảm ơn ở CUỐI trang tổng kết (không có ở trang xem lại). Chữ từ research_ui.json (mục "hoan_thanh");
 *  email là liên kết mailto: dạng nút to dễ bấm trên điện thoại. */
function theCamOn() {
  const u = tt.ui.hoan_thanh;
  return h("section", { class: "the cam-on" }, h("span", { class: "cam-on-bt", "aria-hidden": "true" }, u.bieu_tuong),
    h("h2", {}, u.tieu_de), h("p", { class: "mo-ta" }, u.mo_ta),
    h("a", { class: "nut-mail", href: "mailto:" + u.email }, u.email), h("p", { class: "cam-on-chuc" }, u.chuc));
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

/** TRANG TỔNG KẾT cuối của người tham gia. Máy chủ chỉ trả kết quả khi participants đã có completed_at (nếu chưa thì 409).
 *  F5 hoặc nhập lại mã sau khi hoàn thành đều về đây. Nút "Xem lại kết quả bài làm" nằm dưới thẻ khả năng từng mức; cuối trang là thẻ cảm ơn. */
async function manHoanThanh() {
  datMan("tong_ket");
  hienThi(TONG_BUOC, h("div", { class: "the" }, h("p", { class: "mo-ta", role: "status" }, tt.kq.dang_tinh)));
  const r = await goiApi("/api/research/result", undefined, { "X-Session-Token": tt.token });
  if (r.status === 200) manKetQua(r.du_lieu, { buoc: TONG_BUOC, duoiDiem: [theNutXemLai()], cuoiTrang: [theCamOn()] });
  else manChuaCoKetQua(r);
}
