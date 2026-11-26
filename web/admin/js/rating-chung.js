/* Tiện ích dùng chung cho các trang quản trị phần chấm: ô chọn đợt, định dạng thời gian, hiện nội dung mục và điểm. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;

  /* Tải danh sách đợt rồi dựng ô chọn đợt. khiDoi(tenDot) chạy lần đầu (đợt đang nhớ hoặc đợt đầu tiên) và mỗi lần đổi.
     noi = nơi hiện lỗi hoặc thông báo "chưa có đợt". */
  SM.chonDot = function (nhanChu, noi, khiDoi) {
    var o = h("select", {id: "chon-dot"});
    var khung = h("label", {class: "truong-nhap", for: "chon-dot"}, h("span", {}, nhanChu), o);
    SM.api("GET", "/api/admin/rating/batches").then(function (kq) {
      if (!kq.ok) { noi.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma))); return; }
      kq.data.dot.forEach(function (d) { o.appendChild(h("option", {value: d.name}, d.name + (d.locked ? " (đã khóa)" : ""))); });
      if (!kq.data.dot.length) { noi.replaceChildren(h("p", {class: "mo-ta"}, SM.ui.mau_cham.trong)); khung.hidden = true; return; }
      var luu = sessionStorage.getItem("sm_dot");
      if (luu && kq.data.dot.some(function (d) { return d.name === luu; })) o.value = luu;
      khiDoi(o.value);
    });
    o.addEventListener("change", function () { sessionStorage.setItem("sm_dot", o.value); khiDoi(o.value); });
    return khung;
  };

  /* 95 giây -> "2 phút"; null -> "Chưa có số liệu". t = khối chữ có giay, phut, gio, chua_co_so. */
  SM.thoiLuong = function (giay, t) {
    if (giay === null || giay === undefined) return t.chua_co_so;
    if (giay < 90) return SM.thayThe(t.giay, {n: Math.round(giay)});
    if (giay < 5400) return SM.thayThe(t.phut, {n: Math.round(giay / 60)});
    return SM.thayThe(t.gio, {n: Math.floor(giay / 3600), m: Math.round((giay % 3600) / 60)});
  };

  /* Nội dung một mục (game 1 hoặc 3) để hiện trong bảng. */
  SM.noiDungMuc = function (game, c) {
    if (game === 1) return h("div", {}, h("strong", {}, c.do_vat), ": ", c.cong_dung);
    return h("div", {}, h("strong", {}, c.tinh_huong), h("div", {class: "khung-ai-goc"}, c.ai_goc), h("div", {}, c.y_tuong));
  };

  /* Điểm của một người dạng chữ: game 1 "B"; game 3 "4 / 2 / X" (dấu · = chưa chọn). */
  SM.diemChu = function (diem) {
    if (!diem) return "—";
    var d = diem.diem || diem;
    if (d.nhom) return d.nhom;
    return ["them_y_moi", "khac_goc", "kha_thi"].map(function (k) { return d[k] === undefined ? "·" : d[k]; }).join(" / ");
  };
})();
