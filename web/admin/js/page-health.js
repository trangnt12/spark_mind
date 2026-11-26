/* Trang Sức khỏe hệ thống (admin, viewer): kết nối database, bộ nhớ, mô hình, công tắc, chỉ mục, số bản ghi, độ trễ truy vấn.
   Mọi chữ lấy từ content/admin_ui.json (mục suc_khoe); dữ liệu đưa vào trang bằng textContent (qua SM.h). Máy chủ nhớ kết quả vài giây. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  function nhan(ok, chuOk, chuLoi) { return h("span", {class: "nhan " + (ok ? "nhan-xanh" : "nhan-do")}, ok ? chuOk : chuLoi); }
  function dong(ten, giaTri) { return h("tr", {}, h("th", {}, ten), h("td", {}, giaTri)); }
  function the(tieuDe, noiDung) { return h("section", {class: "the"}, h("h2", {}, tieuDe), noiDung); }
  function bang(cacDong) { return h("div", {class: "cuon-ngang"}, h("table", {class: "bang bang-chi-tiet"}, h("tbody", {}, cacDong))); }

  function gioChay(giay) {
    var g = Math.floor(giay / 3600), p = Math.floor((giay % 3600) / 60);
    return g + " giờ " + p + " phút";
  }

  function theKetNoi(d, t) {
    var k = d.ket_noi, dl = d.dung_luong, cacDong = [dong(t.trang_thai, nhan(k.ok, t.ok, t.loi + (k.loi ? ": " + k.loi : ""))),
      dong(t.ten_db, k.ten_db), dong(t.do_tre, k.do_tre_ms === null ? "—" : k.do_tre_ms + " ms")];
    if (dl) cacDong.push(dong(t.dung_luong, dl.mb + " / " + dl.gioi_han_mb + " MB"));
    return the(t.ket_noi, bang(cacDong));
  }

  function theTienTrinh(d, t) {
    var p = d.tien_trinh, m = d.mo_hinh;
    return the(t.tien_trinh, bang([dong(t.bo_nho, p.rss_mb === null ? "—" : p.rss_mb + " MB"), dong(t.chay, gioChay(p.chay_giay)),
      dong(t.python, p.python), dong(t.mo_hinh, m.ok ? m.phien_ban : nhan(false, "", t.loi + (m.loi ? ": " + m.loi : "")))]));
  }

  function theCongTac(d, t) {
    var c = d.cong_tac;
    return the(t.cong_tac, bang([dong(t.huong2, SM.nhanMoDong(c.huong2_mo)), dong(t.huong1_web, SM.nhanMoDong(c.huong1_web_mo)),
      dong(t.demo, SM.nhanMoDong(c.demo_mo)), dong(t.thong_bao, c.co_thong_bao ? t.co : t.khong)]));
  }

  function theCauHinh(d, t) {
    return the(t.cau_hinh, h("div", {}, h("p", {class: "mo-ta"}, t.cau_hinh_ghi_chu),
      bang(Object.keys(d.cau_hinh).map(function (k) { return dong(k, nhan(d.cau_hinh[k], t.da_co, t.chua_co)); }))));
  }

  function theChiMuc(d, t) {
    var c = d.chi_muc, hang = c.chi_tiet.map(function (x) {
      return h("tr", {}, h("td", {}, x.collection), h("td", {}, x.truong), h("td", {}, x.unique ? t.duy_nhat : ""), h("td", {}, nhan(x.co, t.co, t.thieu)));
    });
    return the(t.chi_muc, h("div", {}, h("p", {class: c.thieu ? "loi" : "mo-ta"}, c.thieu ? SM.thayThe(t.chi_muc_thieu, {n: c.thieu}) : t.chi_muc_du),
      h("div", {class: "cuon-ngang"}, h("table", {class: "bang bang-nho"},
        h("thead", {}, h("tr", {}, h("th", {}, t.bang), h("th", {}, t.truong), h("th", {}, ""), h("th", {}, t.trang_thai))), h("tbody", {}, hang)))));
  }

  function theBanGhi(d, t) {
    return the(t.ban_ghi, h("div", {}, h("p", {class: "mo-ta"}, t.ban_ghi_ghi_chu),
      bang(d.ban_ghi.map(function (b) { return dong(b.ten, SM.so(b.so_ban_ghi)); }))));
  }

  function theTruyVan(d, t) {
    return the(t.truy_van, h("div", {}, h("p", {class: "mo-ta"}, t.truy_van_ghi_chu),
      bang(d.truy_van.map(function (q) { return dong(t.ten_truy_van[q.ten] || q.ten, q.ok ? q.ms + " ms" : nhan(false, "", t.loi + ": " + q.loi)); }))));
  }

  function ve(d, t) {
    var cac = [theKetNoi(d, t), theTienTrinh(d, t), theCauHinh(d, t)];
    if (d.ket_noi.ok) cac.push(theCongTac(d, t), theChiMuc(d, t), theTruyVan(d, t), theBanGhi(d, t));
    cac.push(h("p", {class: "mo-ta"}, SM.thayThe(t.tinh_luc, {gio: SM.gio(d.tinh_luc), giay: d.nho_giay})));
    return cac;
  }

  SM.trang.sucKhoe = function (goc) {
    var t = SM.ui.suc_khoe, noi = h("div", {}, SM.ui.dang_tai);
    function tai() {
      SM.api("GET", "/api/admin/health").then(function (kq) {
        noi.replaceChildren.apply(noi, kq.ok ? ve(kq.data, t) : [h("p", {class: "loi"}, SM.chuLoi(kq.ma))]);
      });
    }
    goc.replaceChildren(h("section", {class: "trang"}, h("div", {class: "dong-tieu-de"}, h("h1", {}, t.tieu_de),
      h("button", {class: "nho phu", type: "button", onclick: tai}, t.lam_moi)), h("p", {class: "mo-ta"}, t.mo_ta), noi));
    tai();
  };
})();
