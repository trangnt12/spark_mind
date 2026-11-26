/* Trang "Mẫu chấm": rút mẫu (chỉ admin), danh sách đợt, khóa/mở đợt, tải CSV (chỉ admin). Viewer chỉ xem danh sách. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  function o(nhanChu, id, giaTri) {
    var el = h("input", {id: id, name: id, type: "text", autocomplete: "off"});
    el.value = giaTri === undefined ? "" : giaTri;
    return h("label", {class: "truong-nhap", for: id}, h("span", {}, nhanChu), el);
  }

  function thanBody(f, nhan, thu) {
    var raters = f.raters.value.split(",").map(function (x) { return x.trim(); }).filter(Boolean);
    return {data_label: nhan.value, rating_batch: f.dot.value.trim(), n_game1: Number(f.n1.value), n_game3: Number(f.n3.value),
      seed: Number(f.seed.value), dry_run: thu, raters: raters};
  }

  function formRut(t, sauRut) {
    var nhan = h("select", {id: "nhan", name: "nhan"}, ["thu", "pilot", "that"].map(function (x) { return h("option", {value: x}, x); }));
    var f = h("form", {class: "form-ngang"}, h("label", {class: "truong-nhap", for: "nhan"}, h("span", {}, t.nhan), nhan), o(t.dot, "dot"),
      o(t.n1, "n1", "30"), o(t.n3, "n3", "20"), o(t.seed, "seed", "1"), o(t.raters, "raters"));
    var tb = h("p", {class: "mo-ta", role: "status"}), loi = h("p", {class: "loi", role: "alert"});
    function gui(thu) {
      loi.textContent = ""; tb.textContent = "";
      SM.api("POST", "/api/admin/rating/sample", thanBody(f, nhan, thu)).then(function (kq) {
        if (!kq.ok) { loi.textContent = SM.chuLoi(kq.ma); return; }
        var d = kq.data;
        tb.textContent = SM.thayThe(thu ? t.ket_qua_xem_truoc : t.ket_qua_that, {g1: d.da_rut["1"], g3: d.da_rut["3"], t1: d.thieu["1"], t3: d.thieu["3"]});
        if (!thu) sauRut();
      });
    }
    f.addEventListener("submit", function (e) { e.preventDefault(); });
    f.appendChild(h("div", {class: "thao-tac"}, h("button", {type: "button", class: "phu nho", onclick: function () { gui(true); }}, t.xem_truoc),
      h("button", {type: "button", class: "nho", onclick: function () { if (confirm(t.rut_that + "?")) gui(false); }}, t.rut_that)));
    return h("section", {class: "the"}, h("h2", {}, t.tao), f, tb, loi);
  }

  function nutKhoa(d, t, taiLai) {
    return h("button", {class: "nho phu", type: "button", onclick: function () {
      if (!confirm(d.locked ? t.xac_nhan_mo : t.xac_nhan_khoa)) return;
      SM.api("POST", "/api/admin/rating/batches/" + encodeURIComponent(d.name) + "/" + (d.locked ? "unlock" : "lock"), {}).then(taiLai);
    }}, d.locked ? t.mo : t.khoa);
  }

  function dongDot(d, t, laAdmin, taiLai) {
    var duong = "/api/admin/rating/batches/" + encodeURIComponent(d.name) + "/export/";
    var xem = h("button", {class: "nho phu", type: "button", onclick: function () { sessionStorage.setItem("sm_dot", d.name); location.hash = "#/rating/answers"; }}, t.xem_muc);
    return h("tr", {}, h("td", {}, h("strong", {}, d.name)), h("td", {}, h("span", {class: "nhan nhan-" + d.data_label}, d.data_label)),
      h("td", {class: "so"}, d.so_muc["1"] + " / " + d.so_muc["3"]), h("td", {class: "so"}, SM.so(d.so_diem)), h("td", {}, d.raters.join(", ")),
      h("td", {}, h("span", {class: "nhan " + (d.locked ? "nhan-do" : "nhan-xanh")}, d.locked ? t.da_khoa : t.dang_mo)),
      h("td", {}, h("div", {class: "thao-tac"}, xem, laAdmin ? [nutKhoa(d, t, taiLai), h("a", {class: "nut-lien", href: duong + "ratings.csv"}, t.xuat_diem),
        h("a", {class: "nut-lien", href: duong + "key.csv"}, t.xuat_khoa)] : null)));
  }

  function bangDot(dot, t, laAdmin, taiLai) {
    var c = t.cot, tieuDe = [c.dot, c.nhan, c.muc, c.diem, c.nguoi, c.trang_thai, c.thao_tac];
    return h("div", {}, h("div", {class: "cuon-ngang"}, h("table", {class: "bang"}, h("thead", {}, h("tr", {}, tieuDe.map(function (x) { return h("th", {}, x); }))),
      h("tbody", {}, dot.map(function (d) { return dongDot(d, t, laAdmin, taiLai); })))), laAdmin ? h("p", {class: "mo-ta"}, t.canh_bao_khoa) : null);
  }

  SM.trang.mauCham = function (goc) {
    var t = SM.ui.mau_cham, laAdmin = SM.me.role === "admin", ds = h("div", {}, SM.ui.dang_tai);
    function tai() {
      SM.api("GET", "/api/admin/rating/batches").then(function (kq) {
        if (!kq.ok) ds.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma)));
        else ds.replaceChildren(kq.data.dot.length ? bangDot(kq.data.dot, t, laAdmin, tai) : h("p", {class: "mo-ta"}, t.trong));
      });
    }
    goc.replaceChildren(h("section", {class: "trang"}, h("h1", {}, t.tieu_de), h("p", {class: "mo-ta"}, t.mo_ta),
      laAdmin ? formRut(t, tai) : h("p", {class: "the the-vang"}, t.chi_xem), h("section", {class: "the"}, h("h2", {}, t.danh_sach), ds)));
    tai();
  };
})();
