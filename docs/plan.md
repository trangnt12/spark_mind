# Lịch làm việc 20/11 – 6/12/2026
Nguồn: bảng `notebook_hang_ngay` của Trang. Mốc đã chốt: code hai hướng xong 4/12 (dự phòng 5–6/12), thu hướng 2 từ 7/12 đến khoảng 20/12, báo cáo cuối tháng 12. Việc đã xong: cài đặt, notebook 01, nạp MongoDB, endpoint nhận Google Form (19/11).

| Ngày | Việc | Kết quả |
|---|---|---|
| 20/11 | Notebook 02 (mô tả, Cronbach alpha, so sánh nhóm, tương quan); nội dung form B và 3 game nháp trong `content/` | Bảng T1–T5, nội dung game nháp |
| 21/11 | Server: `/health`, mã tham gia, đồng ý, lưu form B, lưu bài game; lên Render; cron ping; Apps Script thử với form thật | Server chạy trực tuyến |
| 22/11 | Giao diện: nhập mã, đồng ý, thông tin cơ bản, form B (đọc từ `content/`), game 1 | Game 1 chơi được |
| 23/11 | Notebook 03: RF, XGBoost, baseline, CV 5 lớp lặp lại trên 3 bản dữ liệu | Bảng so sánh mô hình |
| 24/11 | Notebook 04: SHAP, kiểm tra `pred_contribs`, lưu mô hình; rubric game 1 | Biểu đồ SHAP, file mô hình |
| 25/11 | `/api/predict` và trang kết quả; chế độ demo và research | Mốc: lõi hướng 1 xong |
| 26/11 | Game 2 và chấm tự động; Apps Script đẩy form sang server | Game 2, form tự đổ vào MongoDB |
| 27/11 | Đồng hồ, chặn dán, ghi sự kiện; script tạo mã hàng loạt; 2 câu kiểm tra chú ý (cờ `chu_y_sai`) | Chống gian lận cơ bản |
| 28/11 | Thử trên điện thoại với 5–10 người; script sao lưu MongoDB; bảng kiểm tra | Danh sách lỗi, bản sao lưu |
| 29/11 | Sửa lỗi, thử tải nhẹ; game 3 nếu còn giờ | Bản ổn định |
| 30/11 | MỐC QUYẾT ĐỊNH: thử ~20 người; hướng dẫn cho đội thuê | Sẵn sàng mở thu thập |
| 1/12 | Mở đợt 1 (30–50 người); đóng băng kết quả hướng 1 | Đợt 1 đang chạy |
| 2/12 | Script chấm AI theo lô; thử 2–3 mô hình trên 30–50 câu | Script chấm chạy được |
| 3/12 | Mở thu thập đầy đủ; gắn cờ chất lượng; file mẫu 100–150 câu cho người chấm | Thu thập đang chạy |
| 4/12 | Xuất bảng và hình hướng 1; video demo dự phòng; gắn thẻ phiên bản ổn định | Xong cả hai hướng |
| 5–6/12 | Dự phòng | |

## Ba game (đã chốt hướng)
1. Đồ vật bí ẩn (kiểu AUT): số ý, số ý hợp lệ (AI lọc), độ độc đáo theo tần suất.
2. Soi lỗi AI: chọn nhận xét đúng về lỗi, +1/−1, chấm tự động.
3. Nâng cấp ý tưởng AI: AI chấm `them_y_moi`, `khac_goc`, `kha_thi` (1–5); 2 người chấm lại 100–150 bài.
Nội dung nháp: `content/games/`, `content/form_b.json`.
