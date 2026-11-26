/* Trang Cài đặt: công tắc hướng 2 / hướng 1 web / demo, hạn đóng hướng 2, dòng thông báo.
   Admin sửa được (mỗi lần lưu hỏi xác nhận, ghi audit_log); viewer chỉ xem. Máy chủ mới là nơi quyết định quyền. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};

  /* Nhãn ĐANG MỞ / ĐÃ ĐÓNG (chữ + màu, không chỉ dựa vào màu). Dùng cả ở Tổng quan. */
  SM.nhanMoDong = function (dangMo) {
    var t = SM.ui.cai_dat;
    return h("span", {class: "nhan " + (dangMo ? "nhan-xanh" : "nhan-do")}, dangMo ? t.dang_mo : t.da_dong);
  };

  /* Giờ UTC của máy chủ (ISO không kèm Z) <-> giá trị ô datetime-local (giờ máy người dùng). */
  function sangOGio(iso) {
    if (!iso) return "";
    var d = new Date(/(Z|[+-]\d\d:?\d\d)$/.test(iso) ? iso : iso + "Z"), p = function (n) { return String(n).padStart(2, "0"); };
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + "T" + p(d.getHours()) + ":" + p(d.getMinutes());
  }
  function sangIso(oGio) { return oGio ? new Date(oGio).toISOString() : null; }

  /* Một dòng trạng thái: tên + nhãn + ghi chú phụ. */
  function dongTrangThai(ten, dangMo, phu) {
    return h("div", {class: "dong-trang-thai"}, h("strong", {}, ten), SM.nhanMoDong(dangMo), phu ? h("span", {class: "mo-ta"}, phu) : null);
  }

  function theTrangThai(d, t) {
    var v = d.hieu_luc, phu2 = null;
    if (!v.huong2_dang_mo) {
      phu2 = SM.thayThe(t.dong_tu, {gio: SM.gio(v.huong2_dong_luc)}) + " " + SM.thayThe(t.gia_han, {gio: d.gia_han_gio, het: SM.gio(v.huong2_het_gia_han_luc)});
    }
    return h("section", {class: "the"}, h("h2", {}, t.trang_thai),
      dongTrangThai(t.huong2, v.huong2_dang_mo, phu2), dongTrangThai(t.huong1_web, v.huong1_web_mo), dongTrangThai(t.demo, v.demo_mo),
      d.cap_nhat_luc ? h("p", {class: "mo-ta"}, SM.thayThe(t.cap_nhat, {gio: SM.gio(d.cap_nhat_luc), ai: d.cap_nhat_boi || "?"})) : null);
  }

  function congTac(id, nhan, ghiChu, bat, duocSua) {
    var o = h("input", {type: "checkbox", id: id, checked: bat, disabled: !duocSua});
    return {o: o, ve: h("label", {class: "hien-mk", for: id}, o, h("span", {}, h("strong", {}, nhan), h("br"), h("span", {class: "mo-ta"}, ghiChu)))};
  }

  /* Gom giá trị trên form thành body gửi máy chủ. */
  function doiBody(o) {
    return {huong2_mo: o.h2.checked, huong1_web_mo: o.h1.checked, demo_mo: o.demo.checked,
      han_dong_huong2: sangIso(o.han.value), thong_bao: o.tb.value};
  }

  /* Danh sách thay đổi (chữ) so với giá trị đang lưu, để hỏi xác nhận. Rỗng = không có gì đổi. */
  function lietKeThayDoi(cu, moi, t) {
    var bat = function (v) { return v ? t.bat : t.tat; }, ds = [];
    [["huong2_mo", t.huong2], ["huong1_web_mo", t.huong1_web], ["demo_mo", t.demo]].forEach(function (c) {
      if (cu[c[0]] !== moi[c[0]]) ds.push(c[1] + ": " + bat(cu[c[0]]) + " → " + bat(moi[c[0]]));
    });
    if (sangOGio(cu.han_dong_huong2) !== sangOGio(moi.han_dong_huong2)) ds.push(t.han_dong + ": " + (SM.gio(cu.han_dong_huong2) || t.khong) + " → " + (SM.gio(moi.han_dong_huong2) || t.khong));
    if ((cu.thong_bao || "") !== (moi.thong_bao || "").trim()) ds.push(t.thong_bao);
    return ds;
  }

  function veForm(d, t, duocSua, sauLuu) {
    var loi = h("p", {class: "loi", role: "alert"}), ok = h("p", {class: "mo-ta", role: "status"});
    var c2 = congTac("cd-h2", t.huong2, t.huong2_ghi_chu, d.huong2_mo, duocSua), c1 = congTac("cd-h1", t.huong1_web, t.huong1_web_ghi_chu, d.huong1_web_mo, duocSua);
    var cdm = congTac("cd-demo", t.demo, t.demo_ghi_chu, d.demo_mo, duocSua);
    var han = h("input", {type: "datetime-local", id: "cd-han", value: sangOGio(d.han_dong_huong2), disabled: !duocSua});
    var tb = h("textarea", {id: "cd-tb", rows: 2, maxlength: d.thong_bao_toi_da, disabled: !duocSua}, d.thong_bao || "");
    var o = {h2: c2.o, h1: c1.o, demo: cdm.o, han: han, tb: tb};
    var nut = h("button", {type: "submit"}, t.luu);
    var f = h("form", {class: "form-cai-dat"}, c2.ve, c1.ve, cdm.ve,
      h("label", {class: "truong-nhap", for: "cd-han"}, h("span", {}, t.han_dong), han, h("span", {class: "mo-ta"}, t.han_dong_ghi_chu)),
      h("label", {class: "truong-nhap", for: "cd-tb"}, h("span", {}, t.thong_bao), tb, h("span", {class: "mo-ta"}, SM.thayThe(t.thong_bao_ghi_chu, {n: d.thong_bao_toi_da}))),
      duocSua ? nut : h("p", {class: "mo-ta"}, t.chi_xem), loi, ok);
    f.addEventListener("submit", function (e) {
      e.preventDefault(); loi.textContent = ""; ok.textContent = "";
      var moi = doiBody(o), ds = lietKeThayDoi(d, moi, t);
      if (!ds.length) { ok.textContent = t.khong_doi; return; }
      if (!confirm(t.xac_nhan + "\n\n" + ds.join("\n"))) return;
      nut.disabled = true;
      SM.api("PUT", "/api/admin/settings", moi).then(function (kq) {
        nut.disabled = false;
        if (kq.ok) sauLuu(t.da_luu); else loi.textContent = SM.chuLoi(kq.ma);
      });
    });
    return h("section", {class: "the"}, h("h2", {}, t.sua), f);
  }

  SM.trang.caiDat = function (goc) {
    var t = SM.ui.cai_dat, noi = h("div", {}, SM.ui.dang_tai), thongBao = h("p", {class: "the the-vang", role: "status"});
    thongBao.hidden = true;
    function tai(loiNhan) {
      SM.api("GET", "/api/admin/settings").then(function (kq) {
        if (!kq.ok) { noi.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma))); return; }
        thongBao.hidden = !loiNhan; thongBao.textContent = loiNhan || "";
        noi.replaceChildren(theTrangThai(kq.data, t), veForm(kq.data, t, SM.me.role === "admin", tai));
      });
    }
    goc.replaceChildren(h("section", {class: "trang"}, h("div", {class: "dong-tieu-de"}, h("h1", {}, t.tieu_de),
      h("button", {class: "nho phu", type: "button", onclick: function () { tai(); }}, t.lam_moi)), h("p", {class: "mo-ta"}, t.mo_ta), thongBao, noi));
    tai();
  };
})();
