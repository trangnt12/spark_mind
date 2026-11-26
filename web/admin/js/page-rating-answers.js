/* Trang "Xem câu trả lời" (admin, viewer): nội dung từng mục cạnh điểm của các người chấm. Chỉ admin thấy mã người chơi. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  function oDiem(r, t) {
    if (!r) return h("span", {class: "mo-ta"}, t.chua_cham);
    return h("div", {}, h("strong", {}, SM.diemChu(r)), r.hoan_tat ? null : h("span", {class: "nhan nhan-vang"}, t.dang_do),
      r.ghi_chu ? h("div", {class: "mo-ta"}, t.ghi_chu + ": " + r.ghi_chu) : null, h("div", {class: "mo-ta"}, SM.thayThe(t.giay, {n: r.thoi_gian_cham_giay || 0})));
  }

  function dong(m, raters, t) {
    return h("tr", {}, h("td", {}, h("strong", {}, m.item_code), m.participant_id ? h("div", {class: "mo-ta"}, m.participant_id) : null),
      h("td", {}, SM.noiDungMuc(m.game, m.noi_dung)), raters.map(function (r) { return h("td", {}, oDiem(m.diem[r], t)); }));
  }

  function bang(d, raters, t) {
    if (!d.muc.length) return h("p", {class: "mo-ta"}, t.trong);
    return h("div", {class: "cuon-ngang"}, h("table", {class: "bang"}, h("thead", {}, h("tr", {}, [t.cot_ma, t.cot_noi_dung].concat(raters).map(function (x) { return h("th", {}, x); }))),
      h("tbody", {}, d.muc.map(function (m) { return dong(m, raters, t); }))));
  }

  SM.trang.xemTraLoi = function (goc) {
    var t = SM.ui.xem_tra_loi, noi = h("div", {}), ds = h("div", {}), dot = null, trang = 1;
    var game = h("select", {id: "loc-game"}, h("option", {value: ""}, t.tat_ca), h("option", {value: "1"}, t.game1), h("option", {value: "3"}, t.game3));
    function tai() {
      var q = "?page=" + trang + (game.value ? "&game=" + game.value : "");
      SM.api("GET", "/api/admin/rating/batches/" + encodeURIComponent(dot) + "/progress").then(function (tdo) {
        var raters = tdo.ok ? tdo.data.nguoi_cham.map(function (r) { return r.rater; }) : [];
        SM.api("GET", "/api/admin/rating/batches/" + encodeURIComponent(dot) + "/answers" + q).then(function (kq) {
          if (!kq.ok) { noi.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma))); return; }
          var het = trang * kq.data.co >= kq.data.tong;
          noi.replaceChildren(h("p", {class: "mo-ta"}, SM.thayThe(t.tong, {n: kq.data.tong}) + " · " + SM.thayThe(t.trang, {t: trang})), bang(kq.data, raters, t),
            h("div", {class: "phan-trang"}, h("button", {class: "nho phu", type: "button", disabled: trang <= 1, onclick: function () { trang--; tai(); }}, t.truoc),
              h("button", {class: "nho phu", type: "button", disabled: het, onclick: function () { trang++; tai(); }}, t.sau)));
        });
      });
    }
    game.addEventListener("change", function () { trang = 1; if (dot) tai(); });
    var chon = SM.chonDot(t.chon_dot, ds, function (ten) { dot = ten; trang = 1; tai(); });
    goc.replaceChildren(h("section", {class: "trang"}, h("h1", {}, t.tieu_de),
      h("section", {class: "the"}, h("div", {class: "form-ngang"}, chon, h("label", {class: "truong-nhap", for: "loc-game"}, h("span", {}, t.game), game)), ds), noi));
  };
})();
