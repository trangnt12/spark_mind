/* Trang dữ liệu theo từng bảng (registry-driven): danh sách có tìm kiếm, lọc, sắp xếp, phân trang, xuất CSV; trang chi tiết.
   Mọi thứ (cột, bộ lọc, quyền) lấy từ meta của máy chủ (GET /api/admin/data), nên thêm bảng mới không cần sửa file này. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  var h = SM.h;
  SM.trang = SM.trang || {};
  var NHO = {};   // trạng thái từng danh sách (giữ lại khi quay về từ trang chi tiết)

  /* ---------- Hiển thị một giá trị theo kiểu cột ---------- */
  /* Game 3 dạng đọc: mỗi tình huống một khối (id, số từ, số lần dán, rời tab, thời gian) rồi đúng văn bản người chơi nhập. */
  function hienGame3(cacMuc) {
    var g = SM.ui.du_lieu.game3;
    return h("div", {}, cacMuc.map(function (m) {
      return h("div", {class: "muc-game3"},
        h("strong", {}, g.tinh_huong + " " + m.tinh_huong_id),
        h("span", {class: "mo-ta"}, " · " + m.so_tu + " " + g.so_tu + " · " + m.so_lan_dan + " " + g.so_lan_dan + " · " +
          m.so_lan_roi_tab + " " + g.so_lan_roi_tab + " · " + m.thoi_gian_lam + " " + g.thoi_gian_lam),
        h("p", {class: "noi-dung-game3"}, m.noi_dung));
    }));
  }

  function hienGiaTri(kieu, v) {
    var t = SM.ui.du_lieu;
    if (v === null || v === undefined || v === "") return h("span", {class: "mo-ta"}, "—");
    if (kieu === "bool") return h("span", {class: "nhan " + (v ? "nhan-xanh" : "nhan-xam")}, v ? t.co : t.khong);
    if (kieu === "nhan") return h("span", {class: "nhan nhan-" + v}, t.nhan[v] || v);
    if (kieu === "datetime") return SM.gio(v);
    if (kieu === "float") return String(Math.round(v * 10) / 10);
    if (Array.isArray(v)) return v.join(", ");   // danh sách (vd. cờ chống gian lận)
    if (v && Array.isArray(v.tinh_huong)) return hienGame3(v.tinh_huong);   // bài game 3: đọc từng tình huống
    if (kieu === "json" || typeof v === "object") return h("pre", {class: "json-nho"}, JSON.stringify(v, null, 2));
    return String(v);
  }

  function chuoiTruyVan(tt, kichThuoc) {
    var p = new URLSearchParams();
    if (tt.q) p.set("q", tt.q);
    Object.keys(tt.loc).forEach(function (k) { if (tt.loc[k] !== "") p.set("f." + k, tt.loc[k]); });
    if (tt.sort) { p.set("sort", tt.sort); p.set("order", tt.order); }
    p.set("ex_test", tt.anThu ? "true" : "false");
    if (kichThuoc) { p.set("page", tt.page); p.set("size", tt.size); }
    return p.toString();
  }

  /* ---------- Thanh công cụ: tìm kiếm, bộ lọc, ẩn dữ liệu thử, xuất CSV ---------- */
  function oLoc(bl, tt, tai) {
    var t = SM.ui.du_lieu, o;
    if (bl.kieu === "enum" || bl.kieu === "bool") {
      var dsLc = bl.kieu === "bool" ? [["true", t.co], ["false", t.khong]] : bl.lua_chon.map(function (x) { return [x, bl.khoa === "data_label" ? (t.nhan[x] || x) : x]; });
      o = h("select", {"aria-label": bl.nhan}, h("option", {value: ""}, bl.nhan + ": " + t.tat_ca), dsLc.map(function (x) { return h("option", {value: x[0]}, x[1]); }));
    } else {
      o = h("input", {type: "text", placeholder: bl.nhan, "aria-label": bl.nhan});
    }
    o.value = tt.loc[bl.khoa] || "";
    o.addEventListener("change", function () { tt.loc[bl.khoa] = o.value.trim(); tt.page = 1; tai(); });
    return o;
  }

  function thanhCongCu(b, tt, tai) {
    var t = SM.ui.du_lieu, dong = [];
    if (b.tim_kiem) {
      var tim = h("input", {type: "search", class: "o-tim", placeholder: t.tim, "aria-label": t.tim, value: tt.q});
      var hen;
      tim.addEventListener("input", function () { clearTimeout(hen); hen = setTimeout(function () { tt.q = tim.value.trim(); tt.page = 1; tai(); }, 350); });
      dong.push(tim);
    }
    b.loc.forEach(function (bl) { if (!(bl.khoa === "data_label" && tt.anThu && b.co_nhan)) dong.push(oLoc(bl, tt, tai)); });
    if (b.co_nhan) {
      var an = h("input", {type: "checkbox", id: "an-thu-ds", checked: tt.anThu, onchange: function () { tt.anThu = an.checked; tt.page = 1; tai(); }});
      dong.push(h("label", {class: "hien-mk", for: "an-thu-ds"}, an, h("span", {}, t.an_thu)));
    }
    return h("div", {class: "thanh-cc"}, dong);
  }

  /* ---------- Bảng và phân trang ---------- */
  function dauCot(c, b, tt, tai) {
    if (b.sap_xep.indexOf(c.khoa) < 0) return h("th", {}, c.nhan);
    var dang = tt.sort === c.khoa;
    var nut = h("button", {type: "button", class: "dau-sap-xep", onclick: function () {
      tt.order = dang && tt.order === "asc" ? "desc" : "asc"; tt.sort = c.khoa; tai();
    }}, c.nhan, h("span", {"aria-hidden": "true"}, dang ? (tt.order === "asc" ? " ▲" : " ▼") : ""));
    return h("th", {"aria-sort": dang ? (tt.order === "asc" ? "ascending" : "descending") : "none"}, nut);
  }

  function bangDong(b, d) {
    var link = "#/data/" + b.khoa + "/" + encodeURIComponent(d._id);
    return h("tr", {}, b.cot.map(function (c, i) {
      var noi = hienGiaTri(c.kieu, d[c.khoa]);
      var ngan = ["text", "email", "json"].indexOf(c.kieu) < 0 && !Array.isArray(d[c.khoa]);   // danh sách (cờ) có thể rất dài nên cho xuống dòng   // cột ngắn (ngày, số, nhãn, ID) không xuống dòng giữa chừng
      return h("td", {class: ngan ? "ngan" : null}, i === 0 ? h("a", {href: link}, noi) : noi);
    }), h("td", {}, h("a", {href: link, class: "xem"}, SM.ui.du_lieu.chi_tiet)));
  }

  function phanTrang(kq, tt, tai) {
    var t = SM.ui.du_lieu;
    return h("div", {class: "phan-trang"}, h("span", {}, SM.thayThe(t.tong, {n: SM.so(kq.tong)})),
      h("button", {class: "nho phu", type: "button", disabled: kq.trang <= 1, onclick: function () { tt.page = kq.trang - 1; tai(); }}, t.truoc),
      h("span", {}, SM.thayThe(t.trang, {a: kq.trang, b: kq.so_trang})),
      h("button", {class: "nho phu", type: "button", disabled: kq.trang >= kq.so_trang, onclick: function () { tt.page = kq.trang + 1; tai(); }}, t.sau),
      h("select", {"aria-label": t.kich_thuoc, onchange: function (e) { tt.size = Number(e.target.value); tt.page = 1; tai(); }},
        [10, 25, 50, 100].map(function (n) { return h("option", {value: n, selected: n === tt.size}, n + " / " + t.kich_thuoc.toLowerCase()); })));
  }

  /* ---------- Biểu mẫu thêm mới (bảng crud) ---------- */
  function truongForm(k, q, giaTri) {
    var t = SM.ui.du_lieu, o;
    if (q.kieu === "choice") {
      o = h("select", {id: "f-" + k, name: k}, q.lua_chon.map(function (x) { return h("option", {value: x}, k === "data_label" ? (t.nhan[x] || x) : x); }));
    } else if (q.kieu === "bool") {
      o = h("input", {type: "checkbox", id: "f-" + k, name: k});
    } else {
      o = h("input", {type: "text", id: "f-" + k, name: k, autocomplete: "off", maxlength: 200});
    }
    if (giaTri !== undefined && giaTri !== null) { if (q.kieu === "bool") o.checked = !!giaTri; else o.value = giaTri; }
    return h("label", {class: "truong-nhap", for: "f-" + k}, h("span", {}, q.nhan + (q.bat_buoc ? " *" : "")), o);
  }

  function docForm(form, ghi, chiSua) {
    var kq = {};
    Object.keys(ghi).forEach(function (k) {
      if (chiSua && !ghi[k].sua) return;
      var o = form.elements[k];
      kq[k] = ghi[k].kieu === "bool" ? o.checked : o.value;
    });
    return kq;
  }

  function formThem(b, khiXong) {
    var t = SM.ui.du_lieu, loi = h("p", {class: "loi", role: "alert"});
    var form = h("form", {class: "form-ngang"}, Object.keys(b.ghi).map(function (k) { return truongForm(k, b.ghi[k]); }),
      h("button", {type: "submit", class: "nho"}, t.tao), loi);
    form.addEventListener("submit", function (e) {
      e.preventDefault(); loi.textContent = "";
      SM.api("POST", "/api/admin/data/" + b.khoa, docForm(form, b.ghi, false)).then(function (kq) {
        if (kq.ok) { form.reset(); khiXong(); } else loi.textContent = SM.chuLoi(kq.ma);
      });
    });
    return h("section", {class: "the"}, h("h2", {}, t.them), form);
  }

  /* ---------- Trang danh sách ---------- */
  SM.trang.duLieu = function (goc, b) {
    var t = SM.ui.du_lieu;
    var tt = NHO[b.khoa] = NHO[b.khoa] || {q: "", loc: {}, page: 1, size: 25, anThu: true, sort: b.mac_dinh.truong === "_id" ? "" : b.mac_dinh.truong, order: b.mac_dinh.chieu === 1 ? "asc" : "desc"};
    var noi = h("div", {}, SM.ui.dang_tai), them = h("div", {});
    var csv = h("a", {class: "nut-lien", download: ""}, t.xuat_csv);
    function tai() {
      csv.href = "/api/admin/data/" + b.khoa + "/export.csv?" + chuoiTruyVan(tt, false);
      SM.api("GET", "/api/admin/data/" + b.khoa + "?" + chuoiTruyVan(tt, true)).then(function (kq) {
        if (!kq.ok) { noi.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma))); return; }
        tt.page = kq.data.trang;
        noi.replaceChildren(kq.data.dong.length ? h("div", {class: "cuon-ngang"}, h("table", {class: "bang"},
          h("thead", {}, h("tr", {}, b.cot.map(function (c) { return dauCot(c, b, tt, tai); }), h("th", {}, t.thao_tac))),
          h("tbody", {}, kq.data.dong.map(function (d) { return bangDong(b, d); })))) : h("p", {class: "mo-ta"}, t.rong), phanTrang(kq.data, tt, tai));
      });
    }
    function veThem() { them.replaceChildren(b.quyen.ghi && b.che_do === "crud" ? formThem(b, tai) : ""); }
    goc.replaceChildren(h("section", {class: "trang"}, h("div", {class: "dong-tieu-de"}, h("h1", {}, b.ten),
      h("div", {class: "cong-cu"}, b.quyen.xuat ? [csv, h("span", {class: "mo-ta", title: t.ghi_chu_che}, SM.thayThe(t.xuat_ghi_chu, {n: SM.so(b.toi_da_xuat)}))] : null)),
      b.ghi_chu ? h("p", {class: "mo-ta"}, b.ghi_chu) : (b.che_do === "readonly" ? h("p", {class: "mo-ta"}, t.chi_xem + " " + t.ghi_chu_che) : null), them,
      b.khoa === "access_codes" && SM.trang.thongKeLo ? SM.trang.thongKeLo(function () { return tt.anThu; }) : null,
      h("section", {class: "the"}, thanhCongCu(b, tt, tai), noi)));
    veThem();
    tai();
  };

  /* ---------- Trang chi tiết ---------- */
  function bangTruong(truong) {
    return h("div", {class: "cuon-ngang"}, h("table", {class: "bang bang-chi-tiet"}, h("tbody", {}, truong.map(function (f) {
      return h("tr", {}, h("th", {scope: "row"}, f.nhan), h("td", {}, hienGiaTri(f.kieu, f.gia_tri)));
    }))));
  }

  /* Màn xác nhận xóa người tham gia: cho xem trước số bản ghi con sẽ bị xóa theo, từng bảng. */
  function hienBangCon(b, id, cho) {
    var t = SM.ui.du_lieu;
    SM.api("GET", "/api/admin/data/" + b.khoa + "/" + encodeURIComponent(id) + "/lien-quan").then(function (kq) {
      if (!kq.ok) { cho.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma))); return; }
      var ten = function (k) { var x = (SM.tables || []).filter(function (y) { return y.khoa === k; })[0]; return x ? x.ten + " (" + k + ")" : k; };
      cho.replaceChildren(h("p", {}, t.xoa_con), h("ul", {class: "ds-con"}, Object.keys(kq.data.bang_con).map(function (k) {
        return h("li", {}, ten(k) + ": ", h("strong", {}, SM.so(kq.data.bang_con[k])));
      })));
    });
  }

  function khoiXoa(b, id, quayLai) {
    var t = SM.ui.du_lieu, loi = h("p", {class: "loi", role: "alert"});
    var o = h("input", {type: "text", "aria-label": t.xoa, autocomplete: "off", spellcheck: "false"});
    var nut = h("button", {type: "button", class: "nguy-hiem", disabled: true}, t.xoa_nut);
    o.addEventListener("input", function () { nut.disabled = o.value.trim() !== id; });
    nut.addEventListener("click", function () {
      nut.disabled = true;
      SM.api("DELETE", "/api/admin/data/" + b.khoa + "/" + encodeURIComponent(id) + "?confirm=" + encodeURIComponent(o.value.trim())).then(function (kq) {
        if (kq.ok) { alert(t.da_xoa); quayLai(); } else { loi.textContent = SM.chuLoi(kq.ma); nut.disabled = false; }
      });
    });
    var con = h("div", {});
    if (b.co_bang_con) hienBangCon(b, id, con);
    return h("details", {class: "the the-do"}, h("summary", {}, t.xoa), con, h("p", {}, SM.thayThe(t.xoa_huong_dan, {id: id})), o, nut, loi);
  }

  function khoiSua(b, d, nap) {
    var t = SM.ui.du_lieu, loi = h("p", {class: "loi", role: "alert"});
    var form = h("form", {class: "form-ngang"}, Object.keys(b.ghi).filter(function (k) { return b.ghi[k].sua; })
      .map(function (k) { return truongForm(k, b.ghi[k], d.tho[k]); }), h("button", {type: "submit", class: "nho"}, t.luu), loi);
    form.addEventListener("submit", function (e) {
      e.preventDefault(); loi.textContent = "";
      SM.api("PATCH", "/api/admin/data/" + b.khoa + "/" + encodeURIComponent(d.id), docForm(form, b.ghi, true)).then(function (kq) {
        if (kq.ok) nap(); else loi.textContent = SM.chuLoi(kq.ma);
      });
    });
    return h("details", {class: "the"}, h("summary", {}, t.sua), form);
  }

  SM.trang.chiTiet = function (goc, b, id) {
    var t = SM.ui.du_lieu, noi = h("div", {}, SM.ui.dang_tai);
    function quayLai() { location.hash = "#/data/" + b.khoa; }
    function nap() {
      SM.api("GET", "/api/admin/data/" + b.khoa + "/" + encodeURIComponent(id)).then(function (kq) {
        if (!kq.ok) { noi.replaceChildren(h("p", {class: "loi"}, SM.chuLoi(kq.ma))); return; }
        var d = kq.data;
        noi.replaceChildren(h("section", {class: "the"}, bangTruong(d.truong)),
          b.che_do === "crud" && b.quyen.ghi ? khoiSua(b, d, nap) : (b.quyen.ghi ? null : h("p", {class: "mo-ta"}, b.che_do === "readonly" ? t.chi_xem : "")),
          h("details", {class: "the"}, h("summary", {}, t.json_tho), h("pre", {class: "json-tho"}, JSON.stringify(d.tho, null, 2))),
          b.quyen.xoa ? khoiXoa(b, d.id, quayLai) : null);
      });
    }
    goc.replaceChildren(h("section", {class: "trang"}, h("a", {href: "#/data/" + b.khoa, class: "quay-lai"}, t.quay_lai),
      h("h1", {}, b.ten + " · " + t.chi_tiet), noi));
    nap();
  };
})();
