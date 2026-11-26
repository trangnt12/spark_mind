// Khảo sát hướng 1 trên web ("/huong-1/khao-sat"): đồng ý -> phần A -> phần B (bỏ nếu chưa bao giờ dùng AI) -> phần C -> cảm ơn.
// Dùng lại các hàm của app.js (h, hienThi, cauChon, luoi, oChonLop, oChonTruong, phanB, thieuCau, nutGui...), nhap.js (bản nháp để F5 không mất)
// và thoigian.js. Chữ câu hỏi: /api/content/form-b. Chữ riêng: /api/huong1/noi-dung. Nút và lỗi chung: research_ui.json. Thu và gửi bài: survey1_gui.js.
"use strict";

/** Màn 1: giới thiệu khảo sát (tiêu đề, mô tả của form), thông tin nghiên cứu và ô đồng ý. */
function manDongY() {
  datMan("s1_dong_y");
  const u = s1.ui.dong_y, loi = h("div", { class: "loi an", role: "alert" });
  const tiep = async () => {
    if (!tt.tl.dongY) { baoLoi(loi, tt.ui.loi.thieu_dong_y); return 200; }
    if (!docNhap().bd) ghiNhap("bd", Date.now());   // mốc bắt đầu làm bài, để tính tổng thời gian
    manPhanA();
    return 200;
  };
  hienThi(1, banner(h("span", { class: "emo" }, u.bieu_tuong), tt.fb.tieu_de), h("div", { class: "the" }, h("p", { class: "mo-ta" }, tt.fb.mo_ta)),
    h("div", { class: "the" }, h("h2", {}, u.tieu_de), u.doan.map(dongMoTa)),
    h("div", { class: "the" }, oTich("dongY", u.o_dong_y)), khungNut(loi, nutGui(tt.ui.chung.nut_tiep_tuc, tiep, loi)));
  danhDauGioiThieu();
}

/** Kiểm tra phần A rồi đi tiếp: chọn đáp án "chưa bao giờ dùng AI" ở A4 thì nhảy thẳng sang phần C, như điều hướng của Google Form. */
function buocSauA() {
  const t = tt.tl;
  if (thieuCau(["A1", "A2", "A3", "A4"])) return 200;
  if (!(t.A3 || "").trim()) { loiTai("A3"); cuonDenLoi(); return 200; }
  if (t.A1 <= LOP_CAN_NGUOI_LON && !t.nguoiLon) { loiTai("nguoiLon", tt.ui.loi.thieu_nguoi_lon); cuonDenLoi(); return 200; }
  if (t.A4 === s1.maChua) manPhanC(); else manPhanB();
  return 200;
}

/** Màn 2: phần A (A1-A4). Học sinh từ lớp 6 đến 12 thì hiện thêm ô xác nhận của phụ huynh hoặc giáo viên. */
function manPhanA() {
  datMan("s1_a");
  const a = Object.fromEntries(tt.fb.phan_a_thong_tin.map((c) => [c.id, c]));
  const loi = h("div", { class: "loi an", role: "alert" });
  const hopNguoiLon = h("div", { id: "hop-nguoi-lon" }, oTich("nguoiLon", s1.ui.dong_y.o_nguoi_lon));
  const truong = oChonTruong(a.A3);
  let capCu = capHienTai();
  const khiDoiLop = () => {                      // đổi lớp: chỉ xóa trường đã chọn khi đổi sang cấp học khác
    hopNguoiLon.classList.toggle("an", !(tt.tl.A1 <= LOP_CAN_NGUOI_LON));
    if (capHienTai() !== capCu) { capCu = capHienTai(); truong.capNhat(); }
  };
  const nut = nutGui(tt.ui.chung.nut_tiep_tuc, async () => buocSauA(), loi);
  hienThi(2, h("div", { class: "the" }, h("h2", {}, tt.fb.tieu_de_phan.A), oChonLop(a.A1, khiDoiLop), cauChon(a.A2), truong, cauChon(a.A4), hopNguoiLon),
    khungNut(loi, nut, nutQuayLai(manDongY)));
  khiDoiLop();
}

/** Màn 3: phần B (B1-B7, gồm lưới B4). Dùng lại phanB() của app.js. */
function manPhanB() {
  datMan("s1_b");
  const loi = h("div", { class: "loi an", role: "alert" });
  const tiep = async () => {
    if (thieuCau(CAU_B) || thieuMucKhac(["B1", "B3", "B6"])) return 200;
    manPhanC();
    return 200;
  };
  hienThi(3, h("div", { class: "the" }, phanB(tt.fb.phan_b_hanh_vi)),
    khungNut(loi, nutGui(tt.ui.chung.nut_tiep_tuc, tiep, loi), nutQuayLai(manPhanA)));
  tgBat("form_b", CAU_B4);   // đo thời gian từng câu B4 (thoigian.js)
}

/** Màn 4: phần C (lưới C1.1-C1.5 và C2) rồi nộp. Có một ô ẩn chống bot. */
function manPhanC() {
  datMan("s1_c");
  const cauC = tt.fb.phan_c_tu_danh_gia, loi = h("div", { class: "loi an", role: "alert" });
  const oBay = h("input", { type: "text", id: "ghi-chu-them", name: "ghi_chu_them", tabindex: "-1", autocomplete: "off" });
  const bay = h("div", { class: "chong-bot", "aria-hidden": "true" }, oBay);
  const nut = nutGui(tt.ui.chung.nut_nop_bai, () => nopKhaoSat(loi, oBay), loi);
  const veB = () => (tt.tl.A4 === s1.maChua ? manPhanA() : manPhanB());
  hienThi(4, h("div", { class: "the" }, h("h2", {}, tt.fb.tieu_de_phan.C), luoi(cauC.filter((c) => c.id !== "C6"), tt.fb.c_luoi),
    cauChon(cauC.find((c) => c.id === "C6")), bay), khungNut(loi, nut, nutQuayLai(veB)));
  tgBat("khoi_c", ["C1", "C2", "C3", "C4", "C5"]);
}

/** Trang thân thiện có nút thư liên hệ (màn cảm ơn, màn "đã nộp"). Không có "Bước x trên y". */
function manLienHe(buoc, u, cuoi) {
  const email = tt.ui.hoan_thanh.email;
  hienThi(buoc, banner(h("span", { class: "emo" }, u.bieu_tuong), u.tieu_de),
    h("div", { class: "the cam-on-h1" }, h("span", { class: "cam-on-tick", "aria-hidden": "true" }, bieuTuong("bd-tick", "tick-ve")),
      cacDoan(u.mo_ta), h("a", { class: "nut-mail", href: "mailto:" + email }, email), cuoi ? dongMoTa(cuoi) : ""));   // class cam-on-h1: chỉ hướng 1 được căn giữa
  danhDauGioiThieu();
  document.getElementById("nhan-tien-do").textContent = "";
}

function manCamOn() {
  manLienHe(4, s1.ui.cam_on, s1.ui.cam_on.chuc);
  chucMung();
}

function manDaNop() {
  manLienHe(4, s1.ui.da_nop, "");
}

const BUOC_KHOI_PHUC = { s1_dong_y: manDongY, s1_a: manPhanA, s1_b: manPhanB, s1_c: manPhanC };

/** Mở đúng màn đang làm dở (tải lại trang F5); chưa đồng ý thì bắt đầu từ màn 1. */
function vaoDungBuoc() {
  const man = docMan(), ve = man && BUOC_KHOI_PHUC[man.man];
  if (ve && tt.tl.dongY) ve(); else manDongY();
}

/** Nhớ câu trả lời đang gõ (bản nháp), đo thời gian từng câu Likert và bỏ dấu lỗi khi người dùng trả lời lại. */
function caiSuKien() {
  const nho = () => ghiNhap("tl", tt.tl);
  goc.addEventListener("change", (e) => tgGhi(e.target.name));
  goc.addEventListener("change", boDauLoi);
  goc.addEventListener("input", boDauLoi);
  goc.addEventListener("change", nho);
  goc.addEventListener("input", nho);
}

async function khoiDong1() {
  const [ui, fb, tr, nd] = await Promise.all([goiApi("/api/content/ui"), goiApi("/api/content/form-b"),
    goiApi("/api/content/schools"), goiApi("/api/huong1/noi-dung")]);
  if ([ui, fb, tr].some((r) => r.status !== 200) || ![200, 423].includes(nd.status)) {
    goc.textContent = "Không tải được nội dung. Bạn tải lại trang sau vài giây.";   // chưa có chữ từ máy chủ nên chỉ dòng này viết sẵn
    return;
  }
  Object.assign(tt, { ui: ui.du_lieu, fb: fb.du_lieu, truong: tr.du_lieu, tongBuoc: 4 });
  document.title = tt.ui.ten_he_thong;
  document.getElementById("ten-he-thong").textContent = tt.ui.ten_he_thong;
  if (nd.status === 423) { manDong("huong1"); return; }   // công tắc huong1_web_mo đang tắt: trang "chưa mở"
  Object.assign(s1, { ui: nd.du_lieu, gioKhoa: nd.du_lieu.gio_khoa_nop_lai, maChua: nd.du_lieu.ma_chua_tung_dung, thu: laCheDoThu() });
  caiSuKien();
  theoDoiMang();
  if (s1.thu) hienThongBao(s1.ui.che_do_thu); else taiTrangThai();
  if (daNopGanDay()) { manDaNop(); return; }
  tt.tl = docNhap().tl || {};
  vaoDungBuoc();
}

khoiDong1();
