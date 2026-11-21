# Lịch làm việc 20/11/2026 – 11/1/2027
Nguồn: bảng `notebook_hang_ngay` của Trang. Mốc đã chốt: code hai hướng xong 4/12 (dự phòng 5–6/12), thu hướng 2 từ 7/12 đến khoảng 20/12, báo cáo cuối tháng 12. Việc đã xong: cài đặt, notebook 01, nạp MongoDB, endpoint nhận Google Form (19/11).

| Ngày | Việc | Kết quả |
|---|---|---|
| 20/11 ✅ | Notebook 02 (mô tả, Cronbach alpha, so sánh nhóm, tương quan); nội dung form B và 3 game nháp trong `content/` | Bảng T1–T5, nội dung game nháp (đã xong) |
| 21/11 ✅ | Server, Render, Apps Script, hướng 2 lát cắt 1, tạo mã | Server chạy trực tuyến (đã xong) |
| 22/11 | Giao diện nhập mã, đồng ý, form B, game 1 | Game 1 chơi được |
| 23/11 | Notebook 03: RF, XGBoost, baseline, CV 5 lớp lặp lại trên 3 bản dữ liệu | Bảng so sánh mô hình |
| 24/11 | Notebook 04: SHAP, kiểm tra `pred_contribs`, lưu mô hình | Biểu đồ SHAP, file mô hình |
| 25/11 | `/api/predict` và trang kết quả, demo | Mốc: lõi hướng 1 xong |
| 26/11 | Game 2; `completed_at` khi đủ 3 game | Game 2, ghi nhận hoàn thành |
| 27/11 | Chống gian lận; 2 câu kiểm tra chú ý (cờ `chu_y_sai`) | Chống gian lận cơ bản |
| 28/11 | Thử trên điện thoại; sao lưu MongoDB | Danh sách lỗi, bản sao lưu |
| 29/11 | Sửa lỗi; game 3 | Bản ổn định |
| 30/11 | MỐC QUYẾT ĐỊNH: thử 20 người | Sẵn sàng mở thu thập |
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

## Lịch cuối năm (cập nhật 21/11/2026)
| Ngày | Việc |
|---|---|
| 15/12 | Gửi file 100–150 bài (chọn ngẫu nhiên) cho 2 người chấm |
| 20/12 | Hướng 2 đóng thu |
| 22/12 | Hướng 1 đóng thu, đóng băng dữ liệu (khoảng) |
| 23–27/12 | Chạy lại mô hình trên dữ liệu đã đóng băng |
| trước 24/12 | Nhận kết quả của 2 người chấm |
| 2–3/1/2027 | Gửi thầy bản gần hoàn chỉnh (thầy chấm qua sau tuần 1 tháng 1) |
| 11/1/2027 | Hạn nộp đề án về trường |
