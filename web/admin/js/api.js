/* Gọi API quản trị. Cookie phiên (HttpOnly) trình duyệt tự gửi; mọi yêu cầu ghi kèm X-CSRF-Token lấy từ /api/auth/me. */
(function () {
  "use strict";
  var SM = (window.SM = window.SM || {});
  SM.csrf = "";

  /* Trả {ok, status, data, ma}. ma = mã lỗi máy đọc được (vd "bad_credentials") để đổi thành chữ trong admin_ui.json. */
  SM.api = function (phuongThuc, duongDan, thanBody) {
    var tieuDe = {"Accept": "application/json"};
    if (thanBody !== undefined) tieuDe["Content-Type"] = "application/json";
    if (phuongThuc !== "GET") tieuDe["X-CSRF-Token"] = SM.csrf;
    return fetch(duongDan, {method: phuongThuc, headers: tieuDe, credentials: "same-origin",
      body: thanBody === undefined ? undefined : JSON.stringify(thanBody)})
      .then(function (r) {
        return r.json().catch(function () { return null; }).then(function (data) {
          var ma = !r.ok && data && data.detail && data.detail.code ? data.detail.code : (r.ok ? null : "khac");
          if (r.status === 401 && ma === "not_logged_in" && SM.khiHetPhien) SM.khiHetPhien();
          return {ok: r.ok, status: r.status, data: data, ma: ma};
        });
      })
      .catch(function () { return {ok: false, status: 0, data: null, ma: "mang"}; });
  };

  /* Mã lỗi -> chữ tiếng Việt. */
  SM.chuLoi = function (ma) { return SM.ui.loi[ma] || SM.ui.loi.khac; };
})();
