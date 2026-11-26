/* Trang "Độ đồng thuận": kappa game 1 (nhóm công dụng), kappa trọng số bậc hai game 3 (ba tiêu chí), bảng chéo, mục hai người chấm lệch nhau. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  function so(v, chuSo) { return v === null || v === undefined ? SM.ui.dong_thuan.khong_xac_dinh : v.toFixed(chuSo || 3).replace(".", ","); }
  function phanTram(v) { return v === null || v === undefined ? "" : (v * 100).toFixed(1).replace(".", ",") + "%"; }

  function bangCheo(k, d, t) {
    var c = k.nhan;
    return h("div", {class: "cuon-ngang"}, h("p", {class: "mo-ta"}, SM.thayThe(t.bang_cheo, {a: d.raters[0], b: d.raters[1]})),
      h("table", {class: "bang bang-nho bang-cheo"}, h("thead", {}, h("tr", {}, h("th", {}, ""), c.map(function (x) { return h("th", {class: "so"}, x); }))),
        h("tbody", {}, c.map(function (x, i) {
          return h("tr", {}, h("th", {scope: "row"}, x), k.bang_cheo[i].map(function (n, j) { return h("td", {class: "so" + (i === j ? " duong-cheo" : "")}, n); }));
        }))));
  }

  function khoiKappa(tieuDe, k, d, t, khoaKappa) {
    if (!k.du_du_lieu) return h("section", {class: "the"}, h("h3", {}, tieuDe), h("p", {class: "the the-vang"}, SM.thayThe(t.chua_du, {n: k.so_muc, min: d.toi_thieu})));
    return h("section", {class: "the"}, h("h3", {}, tieuDe),
      h("div", {class: "luoi-o"}, [[t.kappa, so(k[khoaKappa])], [t.dong_y_tho, phanTram(k.dong_y_tho)], [t.so_cap, SM.so(k.so_muc)]].map(function (x) {
        return h("div", {class: "o-so"}, h("span", {class: "o-nhan"}, x[0]), h("span", {class: "o-gia-tri"}, x[1]));
      })), bangCheo(k, d, t));
  }

  function khoiGame3(d, t) {
    var tc = Object.keys(d.game3.tieu_chi).map(function (ma) { return khoiKappa(t.tieu_chi[ma], d.game3.tieu_chi[ma], d, t, "kappa_trong_so"); });
    return h("div", {}, h("h2", {}, t.g3), h("p", {class: "o-gia-tri"}, t.kappa_tb + ": " + so(d.game3.trung_binh)), tc);
  }

  function dongLech(m, d) {
    return h("tr", {}, h("td", {}, m.item_code), h("td", {}, SM.noiDungMuc(m.game, m.noi_dung)), h("td", {}, SM.diemChu(m.diem_a)), h("td", {}, SM.diemChu(m.diem_b)));
  }

  function bangLech(d, t) {
    if (!d.muc_lech.length) return h("p", {class: "mo-ta"}, t.khong_lech);
    return h("div", {}, h("p", {class: "mo-ta"}, t.lech_g1 + " " + SM.thayThe(t.lech_g3, {n: d.nguong_lech_game3})),
      h("div", {class: "cuon-ngang"}, h("table", {class: "bang"}, h("thead", {}, h("tr", {}, [t.cot_ma, t.cot_noi_dung, d.raters[0], d.raters[1]].map(function (x) { return h("th", {}, x); }))),
        h("tbody", {}, d.muc_lech.map(function (m) { return dongLech(m, d); })))));
  }

  function ve(d, t) {
    return h("div", {}, d.toi_thieu < d.toi_thieu_mac_dinh ? h("p", {class: "the the-vang", role: "alert"}, SM.thayThe(t.canh_bao_thu, {min: d.toi_thieu_mac_dinh})) : null,
      h("p", {class: "mo-ta"}, SM.thayThe(t.so_muc_ca_hai, {n: d.so_muc_ca_hai_cham})),
      h("h2", {}, t.g1), khoiKappa(t.g1, d.game1, d, t, "kappa"), khoiGame3(d, t),
      h("h2", {}, SM.thayThe(t.lech, {n: d.muc_lech.length})), bangLech(d, t));
  }

  SM.trang.dongThuan = function (goc) {
    var t = SM.ui.dong_thuan, noi = h("div", {}), ds = h("div", {}), dot = null, a = h("select", {id: "rater-a"}), b = h("select", {id: "rater-b"});
    var toiThieu = h("input", {id: "toi-thieu", type: "text", inputmode: "numeric", autocomplete: "off"});
    function tai() {
      var q = "?rater_a=" + encodeURIComponent(a.value) + "&rater_b=" + encodeURIComponent(b.value) + (/^\d+$/.test(toiThieu.value) ? "&toi_thieu=" + toiThieu.value : "");
      SM.api("GET", "/api/admin/rating/batches/" + encodeURIComponent(dot) + "/agreement" + q).then(function (kq) {
        if (kq.ok && toiThieu.value === "") toiThieu.value = String(kq.data.toi_thieu);   // điền sẵn mặc định (20); hạ xuống 10 để thử
        noi.replaceChildren(kq.ok ? ve(kq.data, t) : h("p", {class: "loi"}, SM.chuLoi(kq.ma)));
      });
    }
    function doiDot(ten) {
      dot = ten;
      SM.api("GET", "/api/admin/rating/batches/" + encodeURIComponent(ten) + "/progress").then(function (kq) {
        var ten2 = kq.ok ? kq.data.nguoi_cham.map(function (r) { return r.rater; }) : [];
        [a, b].forEach(function (s, i) { s.replaceChildren(ten2.map(function (r) { return h("option", {value: r}, r); })); if (ten2[i]) s.value = ten2[i]; });
        tai();
      });
    }
    var chon = SM.chonDot(t.chon_dot, ds, doiDot);
    var nut = h("button", {class: "nho", type: "button", onclick: function () { if (dot) tai(); }}, t.tinh);
    goc.replaceChildren(h("section", {class: "trang"}, h("h1", {}, t.tieu_de), h("p", {class: "mo-ta"}, t.mo_ta),
      h("section", {class: "the"}, h("div", {class: "form-ngang"}, chon, h("label", {class: "truong-nhap", for: "rater-a"}, h("span", {}, t.nguoi_a), a),
        h("label", {class: "truong-nhap", for: "rater-b"}, h("span", {}, t.nguoi_b), b), h("label", {class: "truong-nhap", for: "toi-thieu"}, h("span", {}, t.toi_thieu), toiThieu), nut), ds), noi));
  };
})();
