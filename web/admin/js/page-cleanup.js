/* Dọn dữ liệu thử (chỉ admin): xem trước số bản ghi sẽ xóa theo từng bảng (dry-run), gõ XOA để xác nhận. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  function tenBang(khoa) {
    var b = (SM.tables || []).filter(function (x) { return x.khoa === khoa; })[0];
    return b ? b.ten + " (" + khoa + ")" : khoa;
  }

  function bang(d, t) {
    return h("div", {class: "cuon-ngang"}, h("table", {class: "bang"}, h("thead", {}, h("tr", {}, h("th", {}, t.bang), h("th", {class: "so"}, t.so))),
      h("tbody", {}, Object.keys(d.bang).map(function (k) { return h("tr", {}, h("td", {}, tenBang(k)), h("td", {class: "so"}, SM.so(d.bang[k]))); }),
        h("tr", {class: "dong-tong"}, h("th", {scope: "row"}, t.tong), h("td", {class: "so"}, SM.so(d.tong))))));
  }

  function khoiXoa(d, t, sauXoa) {
    var loi = h("p", {class: "loi", role: "alert"});
    var o = h("input", {type: "text", "aria-label": SM.thayThe(t.go_xac_nhan, {chu: d.tu_xac_nhan}), autocomplete: "off", spellcheck: "false"});
    var nut = h("button", {type: "button", class: "nguy-hiem", disabled: true}, t.nut);
    o.addEventListener("input", function () { nut.disabled = o.value !== d.tu_xac_nhan; });
    nut.addEventListener("click", function () {
      nut.disabled = true;
      SM.api("POST", "/api/admin/test-data/delete", {confirm: o.value}).then(function (kq) {
        if (kq.ok) sauXoa(kq.data); else { loi.textContent = SM.chuLoi(kq.ma); nut.disabled = false; }
      });
    });
    return h("div", {class: "the the-do"}, h("label", {class: "truong-nhap"}, h("span", {}, SM.thayThe(t.go_xac_nhan, {chu: d.tu_xac_nhan})), o), nut, loi);
  }

  SM.trang.donDep = function (goc) {
    var t = SM.ui.don_dep, noi = h("div", {}, SM.ui.dang_tai), thongBao = h("div", {});
    function tai() {
      SM.api("GET", "/api/admin/test-data").then(function (kq) {
        if (!kq.ok) { noi.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma))); return; }
        var d = kq.data;
        noi.replaceChildren(h("h2", {}, t.xem_truoc), bang(d, t),
          d.tong ? khoiXoa(d, t, function (r) {
            thongBao.replaceChildren(h("p", {class: "the the-vang", role: "status"}, t.xong + " " + SM.so(r.tong)));
            tai();
          }) : h("p", {class: "mo-ta"}, t.khong_co));
      });
    }
    goc.replaceChildren(h("section", {class: "trang"}, h("div", {class: "dong-tieu-de"}, h("h1", {}, t.tieu_de),
      h("button", {class: "nho phu", type: "button", onclick: tai}, t.lam_moi)), h("p", {class: "mo-ta"}, t.mo_ta), thongBao, h("section", {class: "the"}, noi)));
    tai();
  };
})();
