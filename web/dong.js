// Trang "đã đóng" / "tạm đóng" / "chưa mở" và dòng thông báo của quản trị. Mọi chữ lấy từ content/research_ui.json (mục "dong").
// Máy chủ là nơi quyết định đóng hay mở (trả 423); file này chỉ vẽ trang thân thiện. Dùng lại h(), hienThi(), banner()... của app.js.
"use strict";

/** Vẽ trang đóng. loai: "khao_sat" (hướng 2 đã đóng), "demo" (tạm đóng), "huong1" (chưa mở). Không lưu màn (F5 sẽ hỏi lại máy chủ). */
function manDong(loai) {
  const u = tt.ui.dong[loai], email = tt.ui.hoan_thanh.email;
  tt.demo = false;                                                    // rời bản demo (nếu đang ở đó)
  hienThi(0, banner(h("span", { class: "emo" }, u.bieu_tuong), u.tieu_de),
    h("div", { class: "the" }, cacDoan(u.mo_ta), h("a", { class: "nut-mail", href: "mailto:" + email }, email)),
    khungNut(h("button", { type: "button", class: "phu", onclick: manMa }, tt.ui.dong.nut_quay_lai)));
  danhDauGioiThieu();
  document.getElementById("nhan-tien-do").textContent = "";           // trang đóng không có "Bước 0 trên N"
}

/** Máy chủ trả 423 (khóa) cho một đường gọi API: demo thì trang "tạm đóng", đường nghiên cứu thì trang "đã đóng". */
function khiBiKhoa(duongDan) {
  if (!tt.ui) return;
  if (duongDan.startsWith("/api/predict/demo")) manDong("demo");
  else if (duongDan.startsWith("/api/research")) manDong("khao_sat");
}

/** Hiện dòng thông báo ở đầu trang (rỗng thì ẩn). Dùng textContent nên không chèn HTML được. */
function hienThongBao(chu) {
  const o = document.getElementById("thong-bao");
  o.textContent = chu || "";
  o.classList.toggle("an", !chu);
}

/** Hỏi /api/status (công tắc đóng/mở). Lỗi mạng thì bỏ qua: máy chủ vẫn tự chặn khi cần. */
async function taiTrangThai() {
  const r = await goiApi("/api/status");
  if (r.status !== 200) return;
  tt.tt = r.du_lieu;
  hienThongBao(r.du_lieu.thong_bao);
}
