/* Trang "Tiến độ chấm": mỗi người chấm đã chấm bao nhiêu mục, thời gian trung bình mỗi mục, ước tính thời gian còn lại. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  function bang(d, t) {
    var c = t.cot;
    return h("div", {class: "cuon-ngang"}, h("table", {class: "bang"}, h("thead", {}, h("tr", {}, [c.nguoi, c.xong, c.tb, c.con_lai].map(function (x) { return h("th", {}, x); }))),
      h("tbody", {}, d.nguoi_cham.map(function (r) {
        return h("tr", {}, h("td", {}, h("strong", {}, r.rater)),
          h("td", {}, h("progress", {max: r.tong || 1, value: r.da_cham}), " " + r.da_cham + "/" + r.tong),
          h("td", {}, SM.thoiLuong(r.tb_giay, t)), h("td", {}, r.da_cham >= r.tong ? "✓" : SM.thoiLuong(r.con_lai_giay, t)));
      }))));
  }

  SM.trang.tienDoCham = function (goc) {
    var t = SM.ui.tien_do_cham, noi = h("div", {}), ds = h("div", {});
    function tai(dot) {
      SM.api("GET", "/api/admin/rating/batches/" + encodeURIComponent(dot) + "/progress").then(function (kq) {
        noi.replaceChildren(kq.ok ? h("div", {}, h("p", {class: "mo-ta"}, SM.thayThe(t.tong, {n: kq.data.tong})), bang(kq.data, t)) : h("p", {class: "loi"}, SM.chuLoi(kq.ma)));
      });
    }
    var chon = SM.chonDot(t.chon_dot, ds, tai);
    goc.replaceChildren(h("section", {class: "trang"}, h("h1", {}, t.tieu_de), h("section", {class: "the"}, h("div", {class: "form-ngang"}, chon), ds, noi)));
  };
})();
