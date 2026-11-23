/* Các trang không cần thanh bên: đăng nhập, đổi mật khẩu (bắt buộc lần đầu hoặc tự đổi), 403. Chữ lấy từ SM.ui (admin_ui.json). */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  /* Một ô nhập có nhãn. loai: text | password. */
  SM.truongNhap = function (nhan, id, loai, tuDong) {
    return h("label", {class: "truong-nhap", for: id}, h("span", {}, nhan),
      h("input", {id: id, name: id, type: loai, autocomplete: tuDong, required: true, spellcheck: "false", autocapitalize: "none"}));
  };

  function hienMatKhau(nhan, ...oNhap) {
    var o = h("input", {type: "checkbox", id: "hien-mk", onchange: function () {
      oNhap.forEach(function (i) { i().type = o.checked ? "text" : "password"; });
    }});
    return h("label", {class: "hien-mk", for: "hien-mk"}, o, h("span", {}, nhan));
  }

  function khung(tieuDe, moTa, con) {
    return h("div", {class: "man-giua"}, h("div", {class: "the-giua"},
      h("div", {class: "logo-lon"}, SM.icon("leaf"), h("span", {}, SM.ui.ten_trang)),
      h("h1", {}, tieuDe), moTa ? h("p", {class: "mo-ta"}, moTa) : null, con));
  }

  function gui(form, nut, loi, goi, khiOk) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      loi.textContent = "";
      nut.disabled = true;
      goi().then(function (kq) {
        nut.disabled = false;
        if (kq.ok) { khiOk(kq.data); return; }
        loi.textContent = SM.chuLoi(kq.ma);
        form.querySelectorAll("input[name=password], input[name=current], input[name=moi], input[name=lai]").forEach(function (i) { i.value = ""; });
      });
    });
  }

  SM.trang.dangNhap = function (goc, khiXong) {
    var t = SM.ui.dang_nhap, loi = h("p", {class: "loi", role: "alert"});
    var nut = h("button", {type: "submit"}, t.nut);
    var form = h("form", {class: "form-doc", novalidate: false}, SM.truongNhap(t.ten_dang_nhap, "username", "text", "username"),
      SM.truongNhap(t.mat_khau, "password", "password", "current-password"),
      hienMatKhau(t.hien, function () { return form.password; }), loi, nut);
    gui(form, nut, loi, function () {
      return SM.api("POST", "/api/auth/login", {username: form.username.value, password: form.password.value});
    }, function (data) { SM.csrf = data.csrf_token; khiXong(data); });
    goc.replaceChildren(khung(t.tieu_de, t.mo_ta, form));
    form.username.focus();
  };

  /* batBuoc=true: trang đầy màn hình (chưa vào được phần còn lại), false: nằm trong khung chính. */
  SM.trang.doiMatKhau = function (goc, batBuoc, khiXong) {
    var t = SM.ui.doi_mat_khau, loi = h("p", {class: "loi", role: "alert"});
    var nut = h("button", {type: "submit"}, t.nut);
    var form = h("form", {class: "form-doc"}, SM.truongNhap(t.hien_tai, "current", "password", "current-password"),
      SM.truongNhap(t.moi, "moi", "password", "new-password"), SM.truongNhap(t.nhap_lai, "lai", "password", "new-password"),
      hienMatKhau(SM.ui.dang_nhap.hien, function () { return form.current; }, function () { return form.moi; }, function () { return form.lai; }),
      loi, nut);
    form.addEventListener("submit", function (e) {
      if (form.moi.value !== form.lai.value) { e.stopImmediatePropagation(); e.preventDefault(); loi.textContent = t.khong_khop; }
    }, true);
    gui(form, nut, loi, function () {
      return SM.api("POST", "/api/auth/change-password", {current_password: form.current.value, new_password: form.moi.value});
    }, function (data) { SM.csrf = data.csrf_token; khiXong(data); });
    var tieuDe = batBuoc ? t.tieu_de_bat_buoc : t.tieu_de;
    goc.replaceChildren(batBuoc ? khung(tieuDe, t.mo_ta_bat_buoc, form)
      : h("section", {class: "trang"}, h("h1", {}, tieuDe), h("div", {class: "the the-hep"}, form)));
    form.current.focus();
  };

  SM.trang.cam = function (goc, veTrangChu) {
    var t = SM.ui["403"];
    goc.replaceChildren(h("section", {class: "trang trang-giua"}, h("p", {class: "ma-loi"}, "403"), h("h1", {}, t.tieu_de),
      h("p", {class: "mo-ta"}, t.mo_ta), h("button", {class: "nho", type: "button", onclick: veTrangChu}, t.nut)));
  };
})();
