/* Khung ứng dụng quản trị: khởi động, thanh bên, thanh trên, bộ định tuyến theo hash (#/...).
   Menu chỉ hiện trang đúng vai trò, nhưng MÁY CHỦ mới là nơi quyết định quyền (giao diện chỉ để tiện dùng). */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  var goc = document.getElementById("goc");

  /* Bảng trang: đường dẫn -> vai trò được vào, biểu tượng, nhãn menu, hàm vẽ. */
  var TRANG = [
    {duong: "/", vaiTro: ["admin", "viewer"], icon: "home", nhan: "trang_chu", ve: function (g) { SM.trang.tongQuan(g); }},
    {duong: "/users", vaiTro: ["admin"], icon: "users", nhan: "nguoi_dung", ve: function (g) { SM.trang.nguoiDung(g); }},
    {duong: "/rate", vaiTro: ["rater"], icon: "rate", nhan: "cham_bai", ve: function (g) { SM.trang.chamBai(g); }},
    {duong: "/password", vaiTro: ["admin", "viewer", "rater"], icon: "key", nhan: "doi_mat_khau", an: true,
      ve: function (g) { SM.trang.doiMatKhau(g, false, function () { alert(SM.ui.doi_mat_khau.da_doi); vaoTrangChu(); }); }}
  ];

  SM.trang = SM.trang || {};
  SM.trang.chamBai = function (g) {
    var t = SM.ui.cham_bai;
    g.replaceChildren(h("section", {class: "trang"}, h("h1", {}, t.tieu_de), h("div", {class: "the"}, h("p", {}, t.mo_ta))));
  };

  function duongHienTai() { return (location.hash || "#/").slice(1) || "/"; }
  function trangMacDinh() { return SM.me.role === "rater" ? "/rate" : "/"; }
  function vaoTrangChu() { location.hash = "#" + trangMacDinh(); }
  function chop(t) { return TRANG.filter(function (x) { return x.vaiTro.indexOf(SM.me.role) >= 0 && !x.an; }); }

  /* ---------- Khung có thanh bên ---------- */
  function mucMenu(t, ui) {
    var a = h("a", {href: "#" + t.duong, class: "muc-menu", "data-duong": t.duong, title: ui.dieu_huong[t.nhan]},
      SM.icon(t.icon), h("span", {class: "chu-menu"}, ui.dieu_huong[t.nhan]));
    return a;
  }

  function thanhBen(ui) {
    return h("aside", {class: "thanh-ben", id: "thanh-ben", "aria-label": ui.dieu_huong.menu_chinh},
      h("div", {class: "logo-ben"}, SM.icon("leaf"), h("span", {class: "chu-menu"}, ui.ten_trang)),
      h("nav", {}, chop().map(function (t) { return mucMenu(t, ui); })),
      h("button", {class: "phu nho nut-thu-gon", type: "button", "aria-label": ui.dieu_huong.thu_gon, title: ui.dieu_huong.thu_gon, onclick: function () {
        var gon = document.body.classList.toggle("thu-gon");
        try { localStorage.setItem("sm_thu_gon", gon ? "1" : "0"); } catch (e) { /* bỏ qua nếu bị chặn */ }
      }}, SM.icon("chevron")));
  }

  function thanhTren(ui) {
    return h("header", {class: "thanh-tren"},
      h("button", {class: "phu nho nut-menu", type: "button", "aria-label": ui.dieu_huong.mo_menu, onclick: function () { document.body.classList.toggle("mo-ngan-keo"); }}, SM.icon("menu")),
      h("div", {class: "khoang"}),
      h("div", {class: "nguoi-dung"}, h("strong", {}, SM.me.display_name), h("span", {class: "vai-tro"}, ui.vai_tro[SM.me.role])),
      h("a", {class: "nut-lien", href: "#/password", title: ui.dieu_huong.doi_mat_khau}, SM.icon("key"), h("span", {class: "chu-an-nho"}, ui.dieu_huong.doi_mat_khau)),
      h("button", {class: "phu nho", type: "button", onclick: dangXuat}, SM.icon("logout"), h("span", {class: "chu-an-nho"}, ui.dieu_huong.dang_xuat)));
  }

  function dungKhung() {
    var ui = SM.ui, noiDung = h("main", {class: "noi-dung", id: "noi-dung", tabindex: "-1"});
    try { if (localStorage.getItem("sm_thu_gon") === "1") document.body.classList.add("thu-gon"); } catch (e) { /* bỏ qua */ }
    goc.replaceChildren(h("div", {class: "khung"}, thanhBen(ui), h("div", {class: "cot-phai"}, thanhTren(ui), noiDung),
      h("div", {class: "man-mo", onclick: function () { document.body.classList.remove("mo-ngan-keo"); }})));
    return noiDung;
  }

  function danhDauMenu(duong) {
    document.querySelectorAll(".muc-menu").forEach(function (a) {
      a.classList.toggle("dang-chon", a.getAttribute("data-duong") === duong);
      if (a.getAttribute("data-duong") === duong) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
  }

  /* ---------- Bộ định tuyến ---------- */
  function dinhTuyen() {
    var duong = duongHienTai(), noiDung = document.getElementById("noi-dung");
    if (!noiDung) return;
    document.body.classList.remove("mo-ngan-keo");
    var trang = TRANG.filter(function (t) { return t.duong === duong; })[0];
    danhDauMenu(duong);
    if (!trang) { SM.trang.khongTim(noiDung); return; }
    if (trang.vaiTro.indexOf(SM.me.role) < 0) { SM.trang.cam(noiDung, vaoTrangChu); return; }
    trang.ve(noiDung);
    noiDung.focus();
  }

  SM.trang.khongTim = function (g) {
    var t = SM.ui.khong_tim_thay;
    g.replaceChildren(h("section", {class: "trang trang-giua"}, h("p", {class: "ma-loi"}, "404"), h("h1", {}, t.tieu_de),
      h("button", {class: "nho", type: "button", onclick: vaoTrangChu}, t.nut)));
  };

  /* ---------- Đăng nhập, đăng xuất, khởi động ---------- */
  function hienTrangDangNhap() {
    SM.me = null; SM.csrf = "";
    document.body.classList.remove("mo-ngan-keo");
    SM.trang.dangNhap(goc, function () { khoiDong(); });
  }

  function dangXuat() {
    SM.api("POST", "/api/auth/logout", {}).then(function () { location.hash = "#/"; hienTrangDangNhap(); });
  }

  function vaoUngDung() {
    if (SM.me.must_change_password) {   // lần đăng nhập đầu: phải đặt mật khẩu mới rồi mới thấy các trang khác
      SM.trang.doiMatKhau(goc, true, function () { khoiDong(); });
      return;
    }
    dungKhung();
    if (!location.hash || location.hash === "#") location.hash = "#" + trangMacDinh();
    dinhTuyen();
  }

  function khoiDong() {
    SM.api("GET", "/api/auth/me").then(function (kq) {
      if (!kq.ok) { hienTrangDangNhap(); return; }
      SM.me = kq.data; SM.csrf = kq.data.csrf_token;
      vaoUngDung();
    });
  }

  SM.khiHetPhien = function () { if (SM.me) hienTrangDangNhap(); };
  window.addEventListener("hashchange", function () { if (SM.me && !SM.me.must_change_password) dinhTuyen(); });

  fetch("/api/auth/ui", {credentials: "same-origin"}).then(function (r) { return r.json(); }).then(function (ui) {
    SM.ui = ui;
    document.title = ui.ten_trang;
    khoiDong();
  }).catch(function () { goc.textContent = "Không tải được giao diện."; });
})();
