/* Trang chấm bài của người chấm (#/rate và #/rate/<mã mục>). Người chấm chỉ thấy mục được giao và điểm của chính mình.
   Server chỉ trả nội dung mục (đồ vật, công dụng / tình huống, bản gốc AI, ý tưởng); không có thông tin người chơi.
   Điểm được lưu khi bấm "Lưu và tiếp theo", khi bấm Mục trước/sau, hoặc khi rời sang trang khác. Thời gian chấm đo ở trình duyệt (trừ lúc ẩn tab). */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  var huongDan = null;     // hướng dẫn chấm (content/rating_guide.json), tải một lần
  var dangMo = null;       // mục đang mở: {code, lay(): thân yêu cầu lưu, ban: có thay đổi chưa lưu, tg: bộ đo giờ}
  SM.trang = SM.trang || {};

  /* Bộ đo thời gian: cộng dồn giây khi tab đang hiện. */
  function boDoGio() {
    var tong = 0, bat = document.hidden ? null : Date.now();
    function dung() { if (bat !== null) { tong += Date.now() - bat; bat = null; } }
    function chay() { if (bat === null && !document.hidden) bat = Date.now(); }
    function ghi() { if (document.hidden) dung(); else chay(); }
    document.addEventListener("visibilitychange", ghi);
    return {giay: function () { dung(); chay(); return Math.round(tong / 1000); },
      xong: function () { document.removeEventListener("visibilitychange", ghi); }};
  }

  function luu(m, khiXong) {
    var t = m.tg.giay();
    return SM.api("PUT", "/api/rate/items/" + encodeURIComponent(m.code) + "/rating", {diem: m.lay().diem, ghi_chu: m.lay().ghi_chu, thoi_gian_cham_giay: m.daGui ? 0 : t})
      .then(function (kq) { if (kq.ok) { m.daGui = true; m.ban = false; } if (khiXong) khiXong(kq); return kq; });
  }

  /* Lưu mục trước đó nếu còn thay đổi (khi người dùng bấm Back, đổi menu...). */
  function luuNeuBan() {
    var m = dangMo;
    if (!m) return Promise.resolve();
    dangMo = null;
    m.tg.xong();
    return m.ban && !m.khoa ? luu(m) : Promise.resolve();
  }
  SM.trang.roiChamBai = luuNeuBan;   // app.js gọi khi người chấm sang trang khác

  function chonMa(duong) { var m = /^\/rate\/([A-Za-z0-9-]+)$/.exec(duong); return m ? m[1] : null; }
  function viTri(ds, code) { for (var i = 0; i < ds.length; i++) if (ds[i].item_code === code) return i; return -1; }

  function thanhTienDo(d, t) {
    return h("div", {class: "tien-do-cham"}, h("p", {class: "mo-ta"}, SM.thayThe(t.tien_do, {n: d.da_cham, tong: d.tong})),
      h("progress", {max: d.tong || 1, value: d.da_cham, "aria-label": SM.thayThe(t.tien_do, {n: d.da_cham, tong: d.tong})}));
  }

  function bangNhom(g) {
    var hang = g.nhom.concat([g.khong_cham_duoc]).map(function (n) {
      return h("tr", {}, h("th", {scope: "row"}, n.ma), h("td", {}, n.ten), h("td", {}, n.vi_du || n.mo_ta || ""));
    });
    return h("table", {class: "bang bang-nho"}, h("tbody", {}, hang));
  }

  function bangMoc(g) {
    var diem = [1, 2, 3, 4, 5];
    return h("div", {class: "cuon-ngang"}, h("table", {class: "bang bang-nho"},
      h("thead", {}, h("tr", {}, h("th", {}, ""), diem.map(function (d) { return h("th", {}, d); }))),
      h("tbody", {}, g.tieu_chi.map(function (c) {
        return h("tr", {}, h("th", {scope: "row"}, c.ten), diem.map(function (d) { return h("td", {}, c.moc[d]); }));
      }))));
  }

  function khungHuongDan(game, t) {
    var g = huongDan["game" + game];
    return h("details", {class: "the khung-huong-dan"}, h("summary", {}, t.huong_dan + ": " + g.tieu_de), h("p", {class: "mo-ta"}, g.mo_ta),
      game === 1 ? bangNhom(g) : bangMoc(g));
  }

  function chon(id, giaTri, lua, khoa, t) {
    var s = h("select", {id: id, disabled: khoa}, h("option", {value: ""}, t.chua_chon), lua.map(function (o) { return h("option", {value: String(o.v)}, o.t); }));
    s.value = giaTri === undefined || giaTri === null ? "" : String(giaTri);
    return s;
  }

  function nhan(chu, o, phu) {
    return h("label", {class: "truong-nhap", for: o.id}, h("span", {}, chu), phu ? h("span", {class: "mo-ta"}, phu) : null, o);
  }

  function noiDungGame1(muc, t) {
    var c = muc.noi_dung, g = t.g1;
    return h("div", {class: "the"}, h("p", {class: "o-nhan"}, g.do_vat), h("p", {class: "gt-muc"}, c.do_vat),
      h("p", {class: "o-nhan"}, g.cong_dung), h("p", {class: "gt-muc"}, c.cong_dung));
  }

  function noiDungGame3(muc, t) {
    var c = muc.noi_dung, g = t.g3;
    return h("div", {class: "the"}, h("p", {class: "o-nhan"}, g.tinh_huong), h("p", {class: "gt-muc"}, c.tinh_huong),
      h("p", {class: "o-nhan"}, g.ai_goc), h("blockquote", {class: "khung-ai-goc"}, c.ai_goc),
      h("p", {class: "o-nhan"}, g.y_tuong), h("p", {class: "gt-muc y-nguoi-choi"}, c.y_tuong));
  }

  /* Ô chọn điểm của mục; trả {phanTu, lay()}. */
  function oChonDiem(muc, t) {
    var cu = (muc.rating && muc.rating.diem) || {}, khoa = muc.locked, ghiChu = h("textarea", {id: "ghi-chu", rows: 2, maxlength: 1000, disabled: khoa});
    ghiChu.value = (muc.rating && muc.rating.ghi_chu) || "";
    var o = {}, hang = [];
    if (muc.game === 1) {
      var lua = huongDan.game1.nhom.map(function (n) { return {v: n.ma, t: n.ma + " · " + n.ten}; }).concat([{v: "X", t: "X · " + huongDan.game1.khong_cham_duoc.ten}]);
      o.nhom = chon("o-nhom", cu.nhom, lua, khoa, t);
      hang.push(nhan(t.g1.nhom, o.nhom));
    } else {
      var thang = [1, 2, 3, 4, 5].map(function (d) { return {v: d, t: String(d)}; }).concat([{v: "X", t: "X"}]);
      huongDan.game3.tieu_chi.forEach(function (c) {
        o[c.ma] = chon("o-" + c.ma, cu[c.ma], thang, khoa, t);
        hang.push(nhan(c.ten, o[c.ma], c.hoi));
      });
    }
    return {phanTu: [h("div", {class: "luoi-chon"}, hang), nhan(t.ghi_chu, ghiChu)], o: o, ghiChu: ghiChu,
      lay: function () {
        var diem = {};
        Object.keys(o).forEach(function (k) { if (o[k].value !== "") diem[k] = /^\d$/.test(o[k].value) ? Number(o[k].value) : o[k].value; });
        return {diem: diem, ghi_chu: ghiChu.value};
      }};
  }

  function chuyenToi(ds, i) { if (i >= 0 && i < ds.length) location.hash = "#/rate/" + ds[i].item_code; }

  function veMuc(goc, d, muc, i, t) {
    var cho = oChonDiem(muc, t), thongBao = h("p", {class: "mo mo-ta", role: "status"}), m = {code: muc.item_code, lay: cho.lay, ban: false, khoa: muc.locked, tg: boDoGio(), daGui: false};
    dangMo = m;
    var danh = function () { m.ban = true; thongBao.textContent = ""; };
    Object.keys(cho.o).forEach(function (k) { cho.o[k].addEventListener("change", danh); });
    cho.ghiChu.addEventListener("input", danh);
    function di(buoc) {
      var moi = function () { dangMo = null; m.tg.xong(); chuyenToi(d.muc, i + buoc); };
      if (m.ban && !m.khoa) luu(m, function (kq) { if (kq.ok) moi(); else thongBao.textContent = SM.chuLoi(kq.ma); }); else moi();
    }
    var nutLuu = h("button", {type: "button", disabled: muc.locked, onclick: function () {
      if (i + 1 >= d.muc.length) { luu(m, function (kq) { thongBao.textContent = kq.ok ? t.da_luu + " " + t.het : SM.chuLoi(kq.ma); }); return; }
      di(1);
    }}, t.luu_tiep);
    var form = h("section", {class: "the"}, h("h2", {}, SM.thayThe(t.muc_so, {i: i + 1, tong: d.muc.length})), muc.game === 1 ? noiDungGame1(muc, t) : noiDungGame3(muc, t),
      cho.phanTu, muc.locked ? h("p", {class: "the the-vang"}, t.da_khoa) : null,
      h("div", {class: "thao-tac"}, h("button", {type: "button", class: "phu", disabled: i === 0, onclick: function () { di(-1); }}, t.truoc),
        nutLuu, h("button", {type: "button", class: "phu", disabled: i + 1 >= d.muc.length, onclick: function () { di(1); }}, t.sau)), thongBao);
    goc.replaceChildren(h("section", {class: "trang trang-cham"}, h("h1", {}, t.tieu_de), thanhTienDo(d, t), khungHuongDan(muc.game, t), form));
  }

  function veLoi(goc, ma) { goc.replaceChildren(h("section", {class: "trang"}, h("p", {class: "loi"}, SM.chuLoi(ma)))); }

  SM.trang.chamBai = function (goc) {
    var t = SM.ui.cham_bai, duong = (location.hash || "#/").slice(1), code = chonMa(duong);
    goc.replaceChildren(h("section", {class: "trang"}, SM.ui.dang_tai));
    var tai = luuNeuBan().then(function () { return huongDan || SM.api("GET", "/api/rate/guide").then(function (kq) { if (kq.ok) huongDan = kq.data; return kq.ok; }); }).then(function (g) { return !!g; });
    tai.then(function (ok) { return ok ? SM.api("GET", "/api/rate/items") : {ok: false, ma: "khac"}; }).then(function (kq) {
      if (!kq.ok) { veLoi(goc, kq.ma); return; }
      var d = kq.data;
      if (!d.muc.length) { luuNeuBan(); goc.replaceChildren(h("section", {class: "trang"}, h("h1", {}, t.tieu_de), h("p", {class: "mo-ta"}, t.khong_co_muc))); return; }
      var i = code ? viTri(d.muc, code) : -1;
      if (i < 0) { var ch = d.muc.filter(function (x) { return !x.da_cham; })[0] || d.muc[0]; location.replace("#/rate/" + ch.item_code); return; }
      SM.api("GET", "/api/rate/items/" + encodeURIComponent(code)).then(function (r) {
        if (r.ok) veMuc(goc, d, r.data, i, t); else veLoi(goc, r.ma);
      });
    });
  };
})();
