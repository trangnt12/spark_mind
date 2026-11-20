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

    // Bảng chọn (B4.1-B4.7 và C1-C5): lấy khóa từ nhãn của từng dòng.
    // Nhận cả nhãn cũ (C1..C5) lẫn mới (C1.1..C1.5); khóa nội bộ luôn là C1..C5.
    if (item.getType() == FormApp.ItemType.GRID) {
      var rows = item.asGridItem().getRows();
      resp.forEach(function (v, i) {
        var khoa = khoaTuNhanDong(String(rows[i]));
        var so = String(v).match(/[1-5]/);
        if (khoa && so) answers[khoa] = parseInt(so[0], 10);
      });
      return;
    }

    // Câu thường: khóa lấy từ đầu tiêu đề, ví dụ "A1. Bạn hiện đang..." -> A1
    var m = item.getTitle().match(/^(A\d|B\d|C\d)\./);
    if (!m) return;
    var key = m[1];
    if (key == 'C2') key = 'C6';  // form mới: câu hoạt động sáng tạo 12 tháng đánh số C2, khóa nội bộ vẫn là C6
    if (/^C[1-5]$/.test(key)) {
      var s = String(resp).match(/[1-5]/);
      if (s) answers[key] = parseInt(s[0], 10);
    } else {
      answers[key] = Array.isArray(resp) ? resp.join(', ') : resp;
    }
  });

  guiVoiThuLai(url, secret, answers);
}

// Nhãn dòng lưới -> khóa nội bộ: "B4.3 ..." -> B4_3; "C1.2 ..." (mới) -> C2; "C2 ..." (cũ) -> C2.
function khoaTuNhanDong(nhan) {
  var m = nhan.match(/^B4\.(\d)/);
  if (m) return 'B4_' + m[1];
  m = nhan.match(/^C1\.(\d)/);   // phải thử trước nhãn cũ, kẻo C1.1..C1.5 cùng thành C1 và ghi đè nhau
  if (m) return 'C' + m[1];
  m = nhan.match(/^C(\d)/);
  return m ? 'C' + m[1] : null;
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
