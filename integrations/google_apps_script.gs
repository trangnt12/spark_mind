/**
 * Gửi mỗi bài vừa nộp trên Google Form sang server SparkMind.
 *
 * Cài đặt (làm một lần):
 * 1. Mở Google Form > dấu ba chấm > Apps Script. Xóa code mẫu, dán toàn bộ file này vào.
 * 2. Project Settings (biểu tượng bánh răng) > Script properties > thêm 2 dòng:
 *      INGEST_URL    = địa chỉ server, ví dụ https://spark-mind.onrender.com
 *      INGEST_SECRET = chuỗi bí mật, GIỐNG với INGEST_SECRET trong file .env / Render
 * 3. Triggers (biểu tượng đồng hồ) > Add Trigger: hàm onFormSubmit, nguồn "From form",
 *    sự kiện "On form submit". Cho phép quyền khi Google hỏi.
 * 4. Thử: tự nộp một form, rồi xem Executions để biết thành công hay lỗi.
 *
 * Form lỗi vẫn nằm trong bảng phản hồi của Google Form. Có thể nhập lại bằng file Excel
 * (scripts/import_excel.py), không bị trùng.
 */

function onFormSubmit(e) {
  var props = PropertiesService.getScriptProperties();
  var url = props.getProperty('INGEST_URL') + '/api/ingest/google-form';
  var secret = props.getProperty('INGEST_SECRET');

  var answers = {
    thoi_gian: Utilities.formatDate(e.response.getTimestamp(), 'Asia/Ho_Chi_Minh', 'yyyy-MM-dd HH:mm:ss')
  };

  e.response.getItemResponses().forEach(function (ir) {
    var item = ir.getItem();
    var resp = ir.getResponse();

    // Bảng chọn (B4.1-B4.7 và C1-C5): lấy khóa từ nhãn của từng dòng
    if (item.getType() == FormApp.ItemType.GRID) {
      var rows = item.asGridItem().getRows();
      resp.forEach(function (v, i) {
        var khoa = String(rows[i]).match(/^(B4\.\d|C\d)/);
        var so = String(v).match(/[1-5]/);
        if (khoa && so) answers[khoa[1].replace('.', '_')] = parseInt(so[0], 10);
      });
      return;
    }

    // Câu thường: khóa lấy từ đầu tiêu đề, ví dụ "A1. Bạn hiện đang..." -> A1
    var m = item.getTitle().match(/^(A\d|B\d|C\d)\./);
    if (!m) return;
    var key = m[1];
    if (/^C[1-5]$/.test(key)) {
      var s = String(resp).match(/[1-5]/);
      if (s) answers[key] = parseInt(s[0], 10);
    } else {
      answers[key] = Array.isArray(resp) ? resp.join(', ') : resp;
    }
  });

  guiVoiThuLai(url, secret, answers);
}

// Server miễn phí trên Render có thể đang ngủ, nên thử lại tối đa 3 lần.
function guiVoiThuLai(url, secret, answers) {
  for (var lan = 1; lan <= 3; lan++) {
    var r = UrlFetchApp.fetch(url, {
      method: 'post',
      contentType: 'application/json',
      headers: { 'x-api-key': secret },
      payload: JSON.stringify(answers),
      muteHttpExceptions: true
    });
    var ma = r.getResponseCode();
    Logger.log('Lần ' + lan + ': HTTP ' + ma + ' ' + r.getContentText());
    if (ma == 200) return;
    if (ma == 401 || ma == 422) return;  // sai khóa hoặc form không hợp lệ: thử lại cũng vô ích
    Utilities.sleep(5000);
  }
}
