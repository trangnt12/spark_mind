# Luồng dữ liệu

```
Google Form ──(Apps Script)──┐
Web hướng 1 (form tự chấm) ──┼──► survey_form1  (DỮ LIỆU GỐC, không sửa)
File Excel cũ ──(import)─────┘          │
                                        │ làm sạch từng form (clean)
                                        ▼
                                  survey_clean  (có điểm, cờ chất lượng, in_chinh/in_chat/in_rat_chat)
                                        │
                  ┌─────────────────────┴───────────────┐
                  ▼                                     ▼
          Notebook 02–05                        Server: dự đoán, kết quả
```

## Nguyên tắc
1. **Dữ liệu gốc không bao giờ bị sửa.** Mọi thứ khác tính lại được từ `survey_form1`.
2. **Mỗi form có một mã (`_id`) tính từ nội dung.** Nhập lại cùng một form không tạo bản sao.
3. **Cờ chất lượng tính riêng cho từng form** (chọn một mức, mâu thuẫn...). Vì vậy form mới được làm sạch ngay khi nộp và kết quả giống hệt làm sạch lại cả bảng (có test kiểm tra điều này).
4. **Gắn cờ, không xóa.** Ba bản dữ liệu là ba bộ lọc trên cùng một bảng.

## Khi có form mới
- Từ Google Form: Apps Script gửi sang server, server ghi `survey_form1`, làm sạch form đó, ghi `survey_clean`.
- Từ web (`/huong-1/khao-sat`, mở từ tháng 1): server nhận mã lựa chọn, đổi thành chữ y hệt Google Form, rồi làm đúng như trên với `nguon = "web"` (thêm trường `thoi_gian_lam_bai`). Không thu email hay tên.
- Làm sạch cả bảng bất cứ lúc nào: `python scripts/run_cleaning.py` (cũng gắn cờ `trung_mau` cho các form có mọi câu trả lời giống hệt nhau, kể cả giữa google_form và web).

## Mô hình KHÔNG tự huấn luyện lại mỗi lần có form
Số trong báo cáo phải cố định. Quy ước:
- Làm sạch: tự động, mỗi form mới.
- Huấn luyện lại và xuất bảng, hình: chạy tay (notebook 03–05) khi cần xem số mới.
- Khi chốt số cho báo cáo: **đóng băng** một phiên bản dữ liệu (xuất CSV, ghi ngày và số form), mọi bảng trong báo cáo lấy từ phiên bản đó.

## Khóa chuẩn của một form
`thoi_gian, A1, A2, A3, A4, B1, B2, B3, B4_1..B4_7, B5, B6, B7, C1..C5, C6, nguon`.
Apps Script và web đều phải gửi đúng các khóa này (xem `src/sparkmind/columns.py`).
