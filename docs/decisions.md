# Quyết định đã chốt (cập nhật 19/11/2026)

Tài liệu này để Claude Code (và người mới vào dự án) hiểu bối cảnh mà không cần đọc lại các cuộc trao đổi cũ.
Sơ đồ cơ sở dữ liệu: `docs/erd.dbml`. Luồng dữ liệu: `docs/data_flow.md`.

## Phạm vi và lịch
- Hạn nộp: tháng 1/2027 (chưa rõ ngày). Code hai hướng xong trong tuần đầu tháng 12 (dự phòng 5–6/12).
- Hướng 1 cần khoảng 1000 form (hiện 460; Google Form thu đến hết tháng 12). Hướng 2: 300 người, thu từ 7/12 đến khoảng 20/12.
- Cuối tháng 12 viết báo cáo. Đầu tháng 1 gửi file cho 2 người chấm / nộp.

## Một web, hai chế độ
- **Demo**: ai cũng dùng được, làm lại bao nhiêu lần cũng được, KHÔNG đưa vào bộ dữ liệu nghiên cứu.
- **Nghiên cứu (hướng 2)**: bắt buộc có mã tham gia dùng một lần (`access_codes`). Mỗi người: thông tin cơ bản (có email) → form B → C1–C5 trả lời ngay trên web → 3 game (đủ cả 3).
- Hướng 1 trên web là form tự chấm: người dùng điền B và nhận mức, điểm 0–100, 3 yếu tố ảnh hưởng nhất, lời khuyên.

## Dữ liệu cá nhân và chống spam
- Thu email ở hướng 2, dạng rõ, không xác thực, không OTP, không ràng buộc duy nhất (để đếm số bài mỗi email). Không thu số điện thoại.
- Chống spam: mã dùng một lần; `ip_hash` (HMAC) chỉ để gắn cờ, không chặn; giới hạn tốc độ theo IP ở endpoint nhập mã; chống gian lận trong bài (đồng hồ, chặn dán, đếm lần dán và rời tab, 2 câu kiểm tra chú ý).
- Email và IP không bao giờ được xuất vào CSV phân tích hay báo cáo. Có người dưới 18 tuổi: cần ghi chú đồng ý phụ huynh/giáo viên.

## Làm sạch dữ liệu
- Chỉ một nơi: `src/sparkmind/cleaning.py`. Cờ tính riêng từng form nên làm sạch được ngay khi nộp (`ingest.py`).
- Dữ liệu gốc `survey_form1` không bao giờ sửa. Gắn cờ, không xóa. Ba bản trên 460 form: rộng (361, khóa `chinh`), chính (297, khóa `chat`), rất chặt (231, khóa `rat_chat`).
- B4.3 và B4.6 đảo chiều khi tính điểm hành vi tổng; B4.5 giữ nguyên.
- **Đã chốt ngày 20/11/2026: bản phân tích CHÍNH của báo cáo là bản chặt (khóa `chat`, 297 form).** Lý do: tiêu chí chất lượng định trước là loại người trả lời một chiều (cùng một mức cho cả khối C hoặc cả khối B). Bản `chinh` (361) là bản rộng và bản `rat_chat` (231) là bản rất chặt; cả hai chỉ dùng để phân tích độ nhạy. Quyết định này đưa ra sau thống kê mô tả (notebook 02) và TRƯỚC khi xem kết quả mô hình.
- **Quy ước gọi tên khi viết báo cáo:** bản rộng = 361 (khóa `chinh`), bản chính = 297 (khóa `chat`), bản rất chặt = 231 (khóa `rat_chat`). Trong code, khóa và tên file cũ giữ nguyên (không đổi tên); chữ "chính" trong khóa `chinh` KHÔNG còn nghĩa là bản chính của báo cáo. Bản mặc định lấy từ `config.BAN_CHINH`.
- Mô hình không tự huấn luyện lại khi có form mới. Khi chốt số cho báo cáo thì đóng băng một phiên bản dữ liệu (ghi ngày và số form).

## Tên trường
- Cấp học lấy từ lớp (A1): lớp 6–9 THCS, 10–12 THPT, năm đại học là Đại học. Không dựa vào tên trường để đoán cấp.
- Khớp tên trường với `content/schools.csv` (3748 trường, không có tỉnh), KHÔNG duyệt tay, báo cáo chỉ cần tên chuẩn (`truong_chuan`). Trạng thái `truong_khop`: `khop_1`, `khop_cung_ten` (nhiều trường cùng cấp và cùng tên), `khop_gan_dung` (trường cùng cấp giống nhất, độ giống >= 0.90), `khop_doan` (0.60 đến dưới 0.90, vẫn gán tên; cột `truong_do_giong`), `chua_chuan_hoa` (dưới 0.60: giữ chữ người gõ, chỉ chuẩn hóa khoảng trắng và viết hoa), `thu_cong` (nếu có `content/school_overrides.csv`, không bắt buộc). Báo cáo thống kê theo cấp học, không theo từng trường.
- Trường Bắc Bình chiếm khoảng 9% mẫu: ghi vào hạn chế của đề tài.

## Công nghệ
- FastAPI, MongoDB Atlas M0 (database `spark_mind`), Render miễn phí + cron-job.org ping `/health` mỗi 10 phút. Mô hình XGBoost lưu định dạng gốc, giải thích từng người bằng `pred_contribs`.
- Google Form → Apps Script (`integrations/google_apps_script.gs`) → `POST /api/ingest/google-form` (khóa `x-api-key` = `INGEST_SECRET`).

## Quy ước làm việc
- Tên file bằng tiếng Anh. Commit message bằng tiếng Anh có gitmoji.
- Trang chưa biết Python: giải thích đơn giản, nói rõ cách kiểm tra và kết quả đúng.

## Form v2 (đổi chữ ngày 20/11/2026)
Chi tiết từng chữ đổi: `docs/form_changes_log.md`. Nguyên tắc: code nhận CẢ chữ cũ lẫn chữ mới, khóa nội bộ giữ nguyên (C1–C5, C6, B4_1..B4_7), dữ liệu gốc không sửa.
- `columns.py`: thêm alias cho B2 (`ORD2`) và B5 (`ORD5`); từ khóa B3/B6/B7 là bộ nhiều từ khóa (chữ cũ + chữ mới); thêm `C6_TIEN_TO` (tiền tố câu C6 cũ + mới).
- `cleaning.py`: `_lop` nhận "Sinh viên năm nhất/hai/ba/tư" (năm 1–4 → 13–16) và "Sinh viên năm 5 trở lên" (năm 5 → 17, Đại học); "Khác" vẫn là không rõ. C6 nhận chữ mới ("Đã tham gia…", "Đã từng tham gia và…").
- Tiêu đề cột: dòng lưới mới `[C1.1]..[C1.5]` → C1..C5 (nhãn cũ `[C1.]..[C5.]` vẫn đọc được); câu tiêu đề "C2." (mới) hoặc "C6." (cũ) → C6. Cùng quy tắc trong `integrations/google_apps_script.gs` (hàm `khoaTuNhanDong`; cần dán lại script vào Google Form).
- Đợt mới `dot5_form_v2`: form nộp từ 2026-11-20 (`DOT_RULES`). Form 6–19/11 vẫn là `dot4_sau_5_11`. Form từ web vẫn là đợt `web`.
- Cột `A4`, `A2`, `B1`: không cần đổi (chữ mới vẫn cho cùng kết quả). Ba bản dữ liệu vẫn 361/297/231.

## Cập nhật 21/11/2026
- **Hạn nộp:** đề án nộp về trường ngày 11/1/2027. Thầy chấm qua sau tuần 1 tháng 1 rồi mới nộp, nên cần gửi thầy bản gần hoàn chỉnh khoảng 2–3/1.
- **Người chấm:** đã có đủ 2 người. Gửi file 100–150 bài (chọn ngẫu nhiên) khoảng 15/12, nhận kết quả trước 24/12.
- **Lịch thu:** hướng 2 đóng thu 20/12; hướng 1 đóng thu và đóng băng dữ liệu khoảng 22/12; chạy lại mô hình 23–27/12.
- **Đồng ý tham gia:** chỉ cần tích ô (người chơi, và thêm ô của người lớn với lớp 6–12); không cần giấy.
- **Mã tham gia:** mã dùng một lần được giữ; phát theo lô cho đội thuê và tình nguyện viên; chế độ demo cho người ngoài.
- **Giới hạn tốc độ:** chỉ đếm mã sai (10 lần mỗi phút theo IP). IP có thể bị giả qua header: hạn chế đã biết, chỉ dùng để gắn cờ.
- **Dữ liệu hướng 2:** lưu riêng (`participants`, `behavior_answers`, `self_assessment`...), không vào `survey_form1`.
- **Form v2 (đổi chữ 20/11):** 460 form cũ được đánh dấu `nguon="excel_import"`.

