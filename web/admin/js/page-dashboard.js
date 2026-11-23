/* Trang chủ: thống kê tổng hợp (admin và viewer). Dữ liệu từ GET /api/admin/stats, chỉ có số đếm. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  /* Ô số liệu lớn: nhãn nhỏ + số. */
  function o(nhan, giaTri, phu) {
    return h("div", {class: "o-so"}, h("span", {class: "o-nhan"}, nhan), h("strong", {class: "o-gia-tri" + (String(giaTri).length > 14 ? " chu-nho" : "")}, giaTri),
      phu ? h("span", {class: "o-phu"}, phu) : null);
  }

  /* Bảng hai cột {khóa: số}. */
  function bangNhom(tieuDe, nhom, chuaCo) {
    var khoa = Object.keys(nhom).sort(function (a, b) { return nhom[b] - nhom[a]; });
    return h("div", {}, h("h3", {}, tieuDe), khoa.length
      ? h("table", {class: "bang bang-nho"}, h("tbody", {}, khoa.map(function (k) {
        return h("tr", {}, h("td", {}, k), h("td", {class: "so"}, SM.so(nhom[k])));
      }))) : h("p", {class: "mo-ta"}, chuaCo));
  }

  function the(tieuDe, ...con) { return h("section", {class: "the"}, h("h2", {}, tieuDe), con); }

  function huong1(d, t) {
    var x = t.huong1, thieu = Math.max(0, d.muc_tieu - d.tong);
    return the(x.tieu_de,
      h("div", {class: "luoi-o"}, o(x.tong, SM.so(d.tong), x.muc_tieu + ": " + SM.so(d.muc_tieu)), o(x.con_thieu, SM.so(thieu)),
        o(x.moi_nhat, d.moi_nhat ? SM.gio(d.moi_nhat) : t.chua_co)),
      SM.tienDo(d.tong, d.muc_tieu, x.tong),
      h("h3", {}, x.cac_ban),
      h("div", {class: "luoi-o"}, ["chinh", "chat", "rat_chat"].map(function (k) { return o(x.ban[k], SM.so(d.ban[k])); })),
      h("div", {class: "luoi-2"}, bangNhom(x.theo_nguon, d.theo_nguon, t.chua_co), bangNhom(x.theo_dot, d.theo_dot, t.chua_co)),
      h("h3", {}, x.theo_ngay), SM.bieuDoCot(d.theo_ngay, x.theo_ngay), h("p", {class: "mo-ta"}, t.ngay_utc));
  }

  function huong2(d, t) {
    var x = t.huong2, ma = d.ma, c = d.co;
    var buoc = d.pheu.map(function (b) { return {nhan: x.buoc[b.khoa], n: b.n}; });
    return the(x.tieu_de,
      h("div", {class: "luoi-o"}, o(x.ma_da_tao, SM.so(ma.da_tao)), o(x.ma_da_dung, SM.so(ma.da_dung)), o(x.ma_chua_dung, SM.so(ma.chua_dung))),
      h("h3", {}, x.pheu + ": " + SM.so(d.muc_tieu)), SM.pheu(buoc, d.muc_tieu, x.pheu),
      h("h3", {}, x.nguoi_moi), SM.bieuDoCot(d.nguoi_moi_theo_ngay, x.nguoi_moi),
      h("h3", {}, x.co),
      h("div", {class: "luoi-o"}, o(x.co_da_nop, SM.so(c.da_nop)), o(x.co_over_time, SM.so(c.over_time)),
        o(x.co_paste, SM.so(c.paste)), o(x.co_tab, SM.so(c.tab_leave))));
  }

  function heThong(d, t) {
    var x = t.he_thong;
    if (!d) return the(x.tieu_de, h("p", {class: "mo-ta"}, x.khong_co));
    return the(x.tieu_de, h("div", {class: "luoi-o"}, o(x.du_lieu, d.du_lieu_mb + " MB"), o(x.luu_tru, d.luu_tru_mb + " MB"),
      o(x.chi_muc, d.chi_muc_mb + " MB"), o(x.gioi_han, d.gioi_han_mb + " MB")),
      SM.tienDo(d.luu_tru_mb + d.chi_muc_mb, d.gioi_han_mb, x.luu_tru));
  }

  SM.trang.tongQuan = function (goc) {
    var t = SM.ui.tong_quan, an = true, noiDung = h("div", {class: "noi-dung-tq"}, SM.ui.dang_tai);
    var tat = h("input", {type: "checkbox", id: "an-thu", checked: true, onchange: function () { an = tat.checked; tai(); }});
    function tai() {
      SM.api("GET", "/api/admin/stats?ex_test=" + an).then(function (kq) {
        if (!kq.ok) { noiDung.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma))); return; }
        var d = kq.data;
        noiDung.replaceChildren(h("p", {class: "mo-ta"}, t.cap_nhat + " " + SM.gio(d.tao_luc) + ". " + t.ghi_chu),
          huong1(d.huong1, t), huong2(d.huong2, t), heThong(d.he_thong, t));
      });
    }
    goc.replaceChildren(h("section", {class: "trang"}, h("div", {class: "dong-tieu-de"}, h("h1", {}, t.tieu_de),
      h("div", {class: "cong-cu"}, h("label", {class: "hien-mk", for: "an-thu"}, tat, h("span", {}, t.an_du_lieu_thu)),
        h("button", {class: "nho phu", type: "button", onclick: tai}, t.lam_moi))), noiDung));
    tai();
  };
})();
