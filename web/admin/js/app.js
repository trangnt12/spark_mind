/* Khung ứng dụng quản trị: khởi động, thanh bên, thanh trên, bộ định tuyến theo hash (#/...).
   Menu chỉ hiện trang đúng vai trò, nhưng MÁY CHỦ mới là nơi quyết định quyền (giao diện chỉ để tiện dùng). */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  var goc = document.getElementById("goc");

  /* Các trang cố định: đường dẫn, vai trò được vào, biểu tượng, nhóm menu, hàm vẽ. Các bảng dữ liệu được thêm động từ máy chủ. */
  var TRANG = [
    {duong: "/", vaiTro: ["admin", "viewer"], icon: "home", ten: function (u) { return u.dieu_huong.trang_chu; }, nhom: "tong_quan", ve: function (g) { SM.trang.tongQuan(g); }},
    {duong: "/rate", vaiTro: ["rater"], icon: "rate", ten: function (u) { return u.dieu_huong.cham_bai; }, nhom: "cham_bai", ve: function (g) { SM.trang.chamBai(g); }},
    {duong: "/rating/samples", vaiTro: ["admin", "viewer"], icon: "rate", ten: function (u) { return u.dieu_huong.mau_cham; }, nhom: "cham_diem", ve: function (g) { SM.trang.mauCham(g); }},
    {duong: "/rating/progress", vaiTro: ["admin", "viewer"], icon: "table", ten: function (u) { return u.dieu_huong.tien_do_cham; }, nhom: "cham_diem", ve: function (g) { SM.trang.tienDoCham(g); }},
    {duong: "/rating/agreement", vaiTro: ["admin", "viewer"], icon: "shield", ten: function (u) { return u.dieu_huong.dong_thuan; }, nhom: "cham_diem", ve: function (g) { SM.trang.dongThuan(g); }},
    {duong: "/rating/answers", vaiTro: ["admin", "viewer"], icon: "table", ten: function (u) { return u.dieu_huong.xem_tra_loi; }, nhom: "cham_diem", ve: function (g) { SM.trang.xemTraLoi(g); }},
    {duong: "/users", vaiTro: ["admin"], icon: "users", ten: function (u) { return u.dieu_huong.nguoi_dung; }, nhom: "cau_hinh", ve: function (g) { SM.trang.nguoiDung(g); }},
    {duong: "/cleanup", vaiTro: ["admin"], icon: "trash", ten: function (u) { return u.dieu_huong.don_dep; }, nhom: "he_thong", ve: function (g) { SM.trang.donDep(g); }},
    {duong: "/password", vaiTro: ["admin", "viewer", "rater"], icon: "key", ten: function (u) { return u.dieu_huong.doi_mat_khau; }, an: true,
      ve: function (g) { SM.trang.doiMatKhau(g, false, function () { alert(SM.ui.doi_mat_khau.da_doi); vaoTrangChu(); }); }}
  ];
  var NHOM_MENU = ["tong_quan", "cham_bai", "huong1", "huong2", "cham_diem", "cau_hinh", "he_thong"];
  var ICON_NHOM = {huong1: "table", huong2: "table", cau_hinh: "cog", he_thong: "shield"};
  SM.tables = [];

  /* Mọi mục menu hiện cho vai trò này: trang cố định + các bảng dữ liệu (máy chủ chỉ trả bảng được phép). */
  function mucMenuDay() {
    var ui = SM.ui, ds = TRANG.filter(function (t) { return !t.an && t.vaiTro.indexOf(SM.me.role) >= 0; })
      .map(function (t) { return {duong: t.duong, icon: t.icon, ten: t.ten(ui), nhom: t.nhom}; });
    return ds.concat(SM.tables.map(function (b) { return {duong: "/data/" + b.khoa, icon: ICON_NHOM[b.nhom] || "table", ten: b.ten, nhom: b.nhom}; }));
  }

  SM.trang = SM.trang || {};   // trang chấm của người chấm nằm ở page-rate.js

  function duongHienTai() { return (location.hash || "#/").slice(1) || "/"; }
  function trangMacDinh() { return SM.me.role === "rater" ? "/rate" : "/"; }
  function vaoTrangChu() { location.hash = "#" + trangMacDinh(); }
  /* ---------- Khung có thanh bên (menu nhóm: Tổng quan, Hướng 1, Hướng 2, Cấu hình, Hệ thống) ---------- */
  function mucMenu(m) {
    return h("a", {href: "#" + m.duong, class: "muc-menu", "data-duong": m.duong, title: m.ten}, SM.icon(m.icon), h("span", {class: "chu-menu"}, m.ten));
  }

  function menuNhom(ui) {
    var muc = mucMenuDay(), kq = [];
    NHOM_MENU.forEach(function (n) {
      var ds = muc.filter(function (m) { return m.nhom === n; });
      if (!ds.length) return;
      kq.push(h("p", {class: "tieu-de-nhom chu-menu"}, ui.nhom[n]), h("div", {class: "vach-nhom", "aria-hidden": "true"}));
      ds.forEach(function (m) { kq.push(mucMenu(m)); });
    });
    return kq;
  }

  function thanhBen(ui) {
    return h("aside", {class: "thanh-ben", id: "thanh-ben", "aria-label": ui.dieu_huong.menu_chinh},
      h("div", {class: "logo-ben"}, SM.icon("leaf"), h("span", {class: "chu-menu"}, ui.ten_trang)),
      h("nav", {}, menuNhom(ui)),
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
    var goc2 = duong.replace(/^(\/data\/[a-z_0-9]+).*$/, "$1").replace(/^\/rate\/.*$/, "/rate");   // trang chi tiết thì đánh dấu mục của bảng
    document.querySelectorAll(".muc-menu").forEach(function (a) {
      var chon = a.getAttribute("data-duong") === goc2;
      a.classList.toggle("dang-chon", chon);
      if (chon) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
  }

  /* ---------- Bộ định tuyến ---------- */
  function veTrangBang(noiDung, duong) {
    var m = /^\/data\/([a-z_0-9]+)(?:\/(.+))?$/.exec(duong);
    var bang = m && SM.tables.filter(function (b) { return b.khoa === m[1]; })[0];
    if (!bang) { SM.trang.cam(noiDung, vaoTrangChu); return true; }   // bảng không có trong danh sách của vai trò này
    if (m[2]) SM.trang.chiTiet(noiDung, bang, decodeURIComponent(m[2])); else SM.trang.duLieu(noiDung, bang);
    return true;
  }

  function dinhTuyen() {
    var duong = duongHienTai(), noiDung = document.getElementById("noi-dung");
    if (!noiDung) return;
    document.body.classList.remove("mo-ngan-keo");
    if (!/^\/rate(\/|$)/.test(duong) && SM.trang.roiChamBai) SM.trang.roiChamBai();   // rời trang chấm: lưu điểm đang dở
    danhDauMenu(duong);
    var trang = TRANG.filter(function (t) { return t.duong === duong.replace(/^\/rate\/[A-Za-z0-9-]+$/, "/rate"); })[0];   // /rate/<mã mục> dùng chung trang chấm (F5 vẫn đúng mục)
    if (!trang && /^\/data\//.test(duong)) { veTrangBang(noiDung, duong); noiDung.focus(); return; }
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
    var nap = SM.me.role === "rater" ? Promise.resolve({ok: true, data: {bang: []}}) : SM.api("GET", "/api/admin/data");
    nap.then(function (kq) {
      SM.tables = kq.ok ? kq.data.bang : [];
      dungKhung();
      if (!location.hash || location.hash === "#") location.hash = "#" + trangMacDinh();
      dinhTuyen();
    });
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
