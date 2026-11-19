# CLAUDE.md – quy tắc làm việc cho dự án SparkMind

## Dự án
Đề án thạc sĩ: dự đoán năng lực tư duy sáng tạo (tự nhận thức) của học sinh, sinh viên Việt Nam từ hành vi dùng LLM, bằng Random Forest, XGBoost và SHAP. Một web FastAPI phục vụ hai chế độ: hướng 1 (form tự chấm, dự đoán bằng XGBoost) và hướng 2 (form B, 3 trò chơi, AI chấm và 2 người chấm kiểm tra). Dữ liệu ở MongoDB Atlas (database `spark_mind`). Triển khai trên Render. Đọc `README.md` và `docs/data_flow.md` trước khi làm.

## Người dùng
Trang, lần đầu làm dự án AI, chưa biết Python. Luôn:
- Giải thích bằng tiếng Việt đơn giản, nói việc đó để làm gì trước khi làm.
- Chú thích trong code bằng tiếng Việt.
- Sau mỗi thay đổi, tóm tắt tối đa 3 dòng: đã làm gì, cách kiểm tra, kết quả đúng là gì.
- Terminal là Git Bash trên Windows: đưa lệnh kiểu Unix, dùng dấu `/`.

## Quy tắc code
- Mỗi hàm tối đa 30 dòng. Mỗi file một việc.
- Logic làm sạch chỉ nằm ở `src/sparkmind/cleaning.py`. Notebook và server chỉ gọi, không viết lại.
- Nội dung đổi được (câu hỏi, đề game, lời khuyên) để trong `content/`, không viết cứng trong code.
- Cấu hình và khóa bí mật qua biến môi trường (`.env`). **Không bao giờ in, ghi log hoặc commit** chuỗi kết nối MongoDB hay khóa API.
- Mô hình XGBoost lưu định dạng gốc (`.json` hoặc `.ubj`), không dùng joblib trên server. Giải thích từng người dùng `pred_contribs` của XGBoost (khớp TreeSHAP).
- Dữ liệu gốc (`survey_form1`) không bao giờ bị sửa. Gắn cờ chất lượng, không xóa form.

## Quy tắc khoa học (quan trọng khi viết báo cáo)
- Biến đầu ra là năng lực sáng tạo **tự nhận thức** (C1–C5 tự chấm). Không viết "đo năng lực sáng tạo".
- Báo cáo kết quả trên cả 3 bản dữ liệu (chính, chặt, rất chặt). Bản chính chỉ chốt trước khi xem kết quả mô hình.
- Kiểm định chéo 5 lớp lặp lại, so với đường cơ sở. Tương quan hành vi–sáng tạo ở nhóm tự nhiên thấp hơn nhiều so với đợt thuê; ghi rõ.
- Không trộn số của các phiên bản dữ liệu khác nhau trong cùng một bảng.
- Số hiệu trích vào báo cáo phải tái lập được bằng một lệnh.

## Cách làm việc
- Mỗi phiên làm một việc, xong thì `/clear`.
- Commit sau mỗi việc chạy được, thông điệp ngắn tiếng Việt không dấu.
- Chạy `python -m pytest tests -q` trước khi commit.
- Gặp việc không chắc: hỏi Trang, đừng tự đoán.
