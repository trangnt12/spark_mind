/* Trang Người dùng (chỉ admin): danh sách, tạo viewer/rater, đặt lại mật khẩu, khóa/mở. Không bao giờ có password_hash. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  function trangThai(u, t) {
    if (!u.is_active) return h("span", {class: "nhan nhan-do"}, t.bi_khoa);
    return u.must_change_password ? h("span", {class: "nhan nhan-vang"}, t.cho_doi_mk) : h("span", {class: "nhan nhan-xanh"}, t.hoat_dong);
  }

  /* Khung hiện mật khẩu tạm đúng một lần, có nút sao chép. */
  function hienMkTam(cho, ten, mk) {
    var t = SM.ui.nguoi_dung, sao = h("button", {class: "nho phu", type: "button", onclick: function () {
      if (navigator.clipboard) navigator.clipboard.writeText(mk).then(function () { sao.textContent = t.da_sao_chep; });
    }}, t.sao_chep);
    cho.replaceChildren(h("div", {class: "the the-vang", role: "status"}, h("p", {}, SM.thayThe(t.mk_tam_hien, {ten: ten})),
      h("code", {class: "mk-tam"}, mk), h("p", {class: "mo-ta"}, t.mk_tam_ghi_chu),
      h("div", {class: "cong-cu"}, sao, h("button", {class: "nho", type: "button", onclick: function () { cho.replaceChildren(); }}, t.dong))));
  }

  function dong(u, t, thaoTac) {
    var tay = u.username === SM.me.username;
    return h("tr", {}, h("td", {}, h("strong", {}, u.display_name), h("br"), h("span", {class: "mo-ta"}, u.username)),
      h("td", {}, SM.ui.vai_tro[u.role]), h("td", {}, trangThai(u, t)),
      h("td", {}, u.last_login_at ? SM.gio(u.last_login_at) : t.chua_tung),
      h("td", {}, h("div", {class: "thao-tac"}, h("button", {class: "nho phu", type: "button", onclick: function () { thaoTac("dat_lai", u); }}, t.dat_lai),
        tay ? null : h("button", {class: "nho phu", type: "button", onclick: function () { thaoTac(u.is_active ? "khoa" : "mo", u); }}, u.is_active ? t.khoa : t.mo))));
  }

  function bang(users, t, thaoTac) {
    if (!users.length) return h("p", {class: "mo-ta"}, t.trong);
    return h("div", {class: "cuon-ngang"}, h("table", {class: "bang"}, h("thead", {}, h("tr", {},
      [t.ten_hien_thi, t.vai_tro, t.trang_thai, t.dang_nhap_cuoi, t.thao_tac].map(function (x) { return h("th", {}, x); }))),
      h("tbody", {}, users.map(function (u) { return dong(u, t, thaoTac); }))));
  }

  function formTao(t, khiTao) {
    var loi = h("p", {class: "loi", role: "alert"});
    var vt = h("select", {id: "vai-tro", name: "vai_tro"}, h("option", {value: "rater"}, SM.ui.vai_tro.rater), h("option", {value: "viewer"}, SM.ui.vai_tro.viewer));
    var f = h("form", {class: "form-ngang"}, SM.truongNhap(t.ten_dang_nhap, "ten", "text", "off"), SM.truongNhap(t.ten_hien_thi, "hien-thi", "text", "off"),
      h("label", {class: "truong-nhap", for: "vai-tro"}, h("span", {}, t.vai_tro), vt),
      h("label", {class: "truong-nhap", for: "mk-tam"}, h("span", {}, t.mat_khau_tam), h("input", {id: "mk-tam", name: "mk", type: "text", autocomplete: "off"})),
      h("button", {type: "submit", class: "nho"}, t.tao), loi);
    f.ten.required = true;
    f["hien-thi"].required = false;
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      loi.textContent = "";
      SM.api("POST", "/api/admin/users", {username: f.ten.value, display_name: f["hien-thi"].value, role: vt.value, temp_password: f.mk.value || null})
        .then(function (kq) { if (kq.ok) { f.reset(); khiTao(kq.data); } else loi.textContent = SM.chuLoi(kq.ma); });
    });
    return h("section", {class: "the"}, h("h2", {}, t.them), f);
  }

  SM.trang.nguoiDung = function (goc) {
    var t = SM.ui.nguoi_dung, cho = h("div", {}), danhSach = h("div", {}, SM.ui.dang_tai), loiChung = h("p", {class: "loi", role: "alert"});
    function tai() {
      SM.api("GET", "/api/admin/users").then(function (kq) {
        if (kq.ok) danhSach.replaceChildren(bang(kq.data.users, t, thaoTac)); else danhSach.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma)));
      });
    }
    function thaoTac(loai, u) {
      loiChung.textContent = "";
      if (loai === "dat_lai" && !confirm(t.xac_nhan_dat_lai)) return;
      if (loai === "khoa" && !confirm(t.xac_nhan_khoa)) return;
      var goi = loai === "dat_lai" ? SM.api("POST", "/api/admin/users/" + encodeURIComponent(u.username) + "/reset-password", {})
        : SM.api("PATCH", "/api/admin/users/" + encodeURIComponent(u.username), {is_active: loai === "mo"});
      goi.then(function (kq) {
        if (!kq.ok) { loiChung.textContent = SM.chuLoi(kq.ma); return; }
        if (kq.data.temp_password) hienMkTam(cho, u.username, kq.data.temp_password);
        tai();
      });
    }
    goc.replaceChildren(h("section", {class: "trang"}, h("h1", {}, t.tieu_de), cho,
      formTao(t, function (d) { hienMkTam(cho, d.user.username, d.temp_password); tai(); }),
      h("section", {class: "the"}, loiChung, danhSach)));
    tai();
  };
})();
