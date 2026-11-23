/* Tiện ích dựng giao diện bằng JS thuần (không framework, không thư viện ngoài).
   Mọi chữ đưa vào trang đều qua textContent / createTextNode nên không thể chèn HTML từ dữ liệu (chống XSS). */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var NS_SVG = "http://www.w3.org/2000/svg";

  /* h("div", {class: "the"}, "chữ", phanTu) -> phần tử HTML. Thuộc tính on* là hàm xử lý sự kiện. */
  function dung(tao, ten, thuocTinh, con) {
    var el = tao(ten);
    Object.keys(thuocTinh || {}).forEach(function (k) {
      var v = thuocTinh[k];
      if (v === null || v === undefined || v === false) return;
      if (k.indexOf("on") === 0 && typeof v === "function") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    });
    con.forEach(function (c) { them(el, c); });
    return el;
  }
  function them(cha, c) {
    if (Array.isArray(c)) c.forEach(function (x) { them(cha, x); });
    else if (c !== null && c !== undefined && c !== false) cha.appendChild(c.nodeType ? c : document.createTextNode(String(c)));
  }
  SM.h = function (ten, thuocTinh) {
    return dung(function (t) { return document.createElement(t); }, ten, thuocTinh, [].slice.call(arguments, 2));
  };
  SM.svg = function (ten, thuocTinh) {
    return dung(function (t) { return document.createElementNS(NS_SVG, t); }, ten, thuocTinh, [].slice.call(arguments, 2));
  };

  /* Biểu tượng SVG (nét 2px, tự vẽ). Mỗi biểu tượng là danh sách đường path. */
  var ICON = {
    home: ["M3 11.5 12 4l9 7.5", "M5 10v10h5v-6h4v6h5V10"],
    users: ["M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20", "M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7", "M20 20v-1.5a3.5 3.5 0 0 0-2.5-3.3", "M15.5 4.2a3.5 3.5 0 0 1 0 6.6"],
    rate: ["M9 11l3 3 8-8", "M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"],
    key: ["M14.5 9.5a4 4 0 1 1-3 3L4 20v-3h3v-2h2l2.5-2.5", "M16 8h.01"],
    logout: ["M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3", "M16 8l4 4-4 4", "M20 12H9"],
    menu: ["M4 6h16", "M4 12h16", "M4 18h16"],
    close: ["M6 6l12 12", "M18 6 6 18"],
    chevron: ["M15 6l-6 6 6 6"],
    table: ["M3 5h18v14H3z", "M3 10h18", "M9 5v14"],
    trash: ["M4 7h16", "M10 11v6", "M14 11v6", "M6 7l1 13h10l1-13", "M9 7V4h6v3"],
    shield: ["M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z", "M9 12l2 2 4-4"],
    cog: ["M4 6h10", "M18 6h2", "M4 12h4", "M12 12h8", "M4 18h12", "M20 18h0", "M16 4v4", "M10 10v4", "M18 16v4"],
    leaf: ["M5 19c0-8 5-14 15-14 0 10-6 15-14 15", "M5 19c3-5 6-8 10-10"]
  };
  SM.icon = function (ten) {
    var s = SM.svg("svg", {viewBox: "0 0 24 24", width: 22, height: 22, "aria-hidden": "true", class: "bieu-tuong",
      fill: "none", stroke: "currentColor", "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round"});
    (ICON[ten] || []).forEach(function (d) { s.appendChild(SM.svg("path", {d: d})); });
    return s;
  };

  /* Định dạng số và ngày theo kiểu Việt Nam. */
  SM.so = function (n) { return new Intl.NumberFormat("vi-VN").format(n || 0); };
  SM.gio = function (iso) {
    if (!iso) return "";
    var d = new Date(/(Z|[+-]\d\d:?\d\d)$/.test(iso) ? iso : iso + "Z");   // máy chủ trả giờ UTC không kèm "Z"
    return d.toLocaleString("vi-VN");
  };
  SM.thayThe = function (mau, giaTri) {
    return mau.replace(/\{(\w+)\}/g, function (_, k) { return giaTri[k]; });
  };
})();
