/* Biểu đồ SVG tự viết: cột theo ngày, phễu, thanh tiến độ. Không thư viện ngoài. Màu lấy từ biến CSS qua class. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var S = function () { return SM.svg.apply(null, arguments); };

  function nhanNgay(iso) { return iso.slice(8, 10) + "/" + iso.slice(5, 7); }

  /* Làm tròn đỉnh trục lên số "đẹp" (1, 2, 5, 10, 20, 50...) để vạch chia dễ đọc. */
  function dinhTruc(max) {
    if (max <= 4) return 4;
    var mu = Math.pow(10, Math.floor(Math.log10(max))), t = max / mu;
    return (t <= 1 ? 1 : t <= 2 ? 2 : t <= 5 ? 5 : 10) * mu;
  }

  function vachNgang(dinh, l, t, r, b) {
    var g = S("g", {class: "luoi-bd"});
    for (var i = 0; i <= 4; i++) {
      var y = b - (b - t) * i / 4;
      g.appendChild(S("line", {x1: l, x2: r, y1: y, y2: y, class: "vach"}));
      g.appendChild(S("text", {x: l - 8, y: y + 4, "text-anchor": "end", class: "chu-bd"}, SM.so(dinh * i / 4)));
    }
    return g;
  }

  /* data = [{ngay: "2026-11-01", n: 3}, ...] -> biểu đồ cột. Mỗi cột có <title> (di chuột/đọc màn hình). */
  SM.bieuDoCot = function (data, nhan) {
    var W = 720, H = 240, l = 44, r = 12, t = 12, b = 32, max = Math.max.apply(null, data.map(function (d) { return d.n; }));
    var dinh = dinhTruc(max), rong = (W - l - r) / data.length;
    var svg = S("svg", {viewBox: "0 0 " + W + " " + H, class: "bieu-do", role: "img", "aria-label": nhan});
    svg.appendChild(vachNgang(dinh, l, t, W - r, H - b));
    data.forEach(function (d, i) {
      var cao = (H - b - t) * d.n / dinh, x = l + i * rong;
      var cot = S("rect", {x: x + rong * 0.15, width: rong * 0.7, y: H - b - cao, height: cao, rx: 3, class: "cot"});
      cot.appendChild(S("title", {}, nhanNgay(d.ngay) + ": " + SM.so(d.n)));
      svg.appendChild(cot);
      if (i % 5 === 0 || i === data.length - 1) svg.appendChild(S("text", {x: x + rong / 2, y: H - 10, "text-anchor": "middle", class: "chu-bd"}, nhanNgay(d.ngay)));
    });
    return svg;
  };

  /* Thanh tiến độ ngang: giá trị so với mục tiêu. */
  SM.tienDo = function (n, mucTieu, nhan) {
    var ti = Math.min(1, n / Math.max(1, mucTieu));
    var svg = S("svg", {viewBox: "0 0 640 16", class: "tien-do-svg", role: "img", "aria-label": nhan});
    svg.appendChild(S("rect", {x: 0, y: 0, width: 640, height: 16, rx: 8, class: "nen-tien-do"}));
    if (ti > 0) svg.appendChild(S("rect", {x: 0, y: 0, width: Math.max(16, 640 * ti), height: 16, rx: 8, class: "cot"}));
    return svg;
  };

  /* steps = [{nhan, n}], mucTieu: vạch đứt thể hiện mục tiêu. Mỗi dòng: nhãn - thanh - số (và % mục tiêu). */
  SM.pheu = function (steps, mucTieu, nhan) {
    var W = 720, dong = 38, l = 130, r = 120, H = steps.length * dong + 8;
    var max = Math.max(mucTieu, Math.max.apply(null, steps.map(function (s) { return s.n; })), 1), rong = W - l - r;
    var svg = S("svg", {viewBox: "0 0 " + W + " " + H, class: "bieu-do pheu", role: "img", "aria-label": nhan});
    steps.forEach(function (s, i) {
      var y = 4 + i * dong, w = rong * s.n / max;
      svg.appendChild(S("text", {x: l - 10, y: y + 20, "text-anchor": "end", class: "chu-bd chu-dam"}, s.nhan));
      svg.appendChild(S("rect", {x: l, y: y + 4, width: rong, height: 22, rx: 6, class: "nen-tien-do"}));
      if (s.n > 0) svg.appendChild(S("rect", {x: l, y: y + 4, width: Math.max(6, w), height: 22, rx: 6, class: "cot"}));
      svg.appendChild(S("text", {x: l + rong + 10, y: y + 20, class: "chu-bd"}, SM.so(s.n) + " (" + Math.round(100 * s.n / Math.max(1, mucTieu)) + "%)"));
    });
    var xm = l + rong * mucTieu / max;
    svg.appendChild(S("line", {x1: xm, x2: xm, y1: 0, y2: H, class: "vach-muc-tieu"}));
    return svg;
  };
})();
