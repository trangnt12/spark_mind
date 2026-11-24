/* Bảng thống kê mã tham gia theo lô (hiện trên trang bảng access_codes). Dữ liệu từ GET /api/admin/codes/batches: chỉ số đếm, không có mã. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  /* anThu: hàm trả về true nếu công tắc "ẩn dữ liệu thử" của trang đang bật. Trả về phần tử có nút làm mới. */
  SM.trang.thongKeLo = function (anThu) {
    var t = SM.ui.du_lieu, cot = ["batch", "nhan", "tong", "da_dung", "chua_dung", "hoan_thanh"];
    var noi = h("div", {}, SM.ui.dang_tai);
    function tai() {
      SM.api("GET", "/api/admin/codes/batches?ex_test=" + (anThu() ? "true" : "false")).then(function (kq) {
        if (!kq.ok) { noi.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma))); return; }
        if (!kq.data.lo.length) { noi.replaceChildren(h("p", {class: "mo-ta"}, t.lo_rong)); return; }
        noi.replaceChildren(h("div", {class: "cuon-ngang"}, h("table", {class: "bang bang-nho"},
          h("thead", {}, h("tr", {}, cot.map(function (c) { return h("th", {}, t.lo_cot[c]); }))),
          h("tbody", {}, kq.data.lo.map(function (d) {
            return h("tr", {}, cot.map(function (c) {
              if (c === "batch") return h("td", {}, d.batch || t.lo_khong_co);
              if (c === "nhan") return h("td", {}, t.nhan[d.nhan] || d.nhan);
              return h("td", {class: "so"}, SM.so(d[c]));
            }));
          })))));
      });
    }
    tai();
    return h("section", {class: "the"}, h("div", {class: "dong-tieu-de"}, h("h2", {}, t.lo_tieu_de),
      h("button", {class: "nho phu", type: "button", onclick: tai}, SM.ui.tong_quan.lam_moi)), h("p", {class: "mo-ta"}, t.lo_ghi_chu), noi);
  };
})();
