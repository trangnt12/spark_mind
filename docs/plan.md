# Lịch làm việc 20/11/2026 – 11/1/2027
Nguồn: bảng `notebook_hang_ngay` của Trang. Mốc đã chốt (đổi 23/11/2026): thử nghiệm 29/11, mở thu hướng 2 từ 1/12 đến 20/12 (dài hơn để đủ 300 người), báo cáo cuối tháng 12. Việc đã xong: cài đặt, notebook 01, nạp MongoDB, endpoint nhận Google Form (19/11).

| Ngày | Việc | Kết quả |
|---|---|---|
| 20/11 ✅ | Notebook 02 (mô tả, Cronbach alpha, so sánh nhóm, tương quan); nội dung form B và 3 game nháp trong `content/` | Bảng T1–T5, nội dung game nháp (đã xong) |
| 21/11 ✅ | Server, Render, Apps Script, hướng 2 lát cắt 1, tạo mã | Server chạy trực tuyến (đã xong) |
| 22/11 ✅ | Giao diện nhập mã, đồng ý, thông tin cơ bản, form B, game 1, chữ khớp form, ảnh game, giao diện xanh lá | Game 1 chơi được (đã xong) |
| 23/11 | Notebook 03: RF, XGBoost, baseline, CV 5 lớp lặp lại trên 3 bản dữ liệu | Bảng so sánh mô hình |
| 24/11 | Notebook 04: SHAP, kiểm tra `pred_contribs`, lưu mô hình | Biểu đồ SHAP, file mô hình |
| 25/11 ✅ | `/api/predict` (API dự đoán), mô hình B4, demo, trang kết quả, endpoint `/api/admin/memory`, chữ kết quả đã duyệt | Mốc: lõi hướng 1 xong (đã xong; còn "Danh sách đóng băng mô hình ~22/12") |
| 24–27/11 | Game 2 + `completed_at` khi đủ 3 game (✅ đã xong 24/11, game 3 ✅ xong 25/11); cờ chống gian lận bản gọn (đo thời gian từng câu, không có câu kiểm tra chú ý; ✅ xong 24/11); tạo mã hàng loạt theo lô (✅ xong 24/11); game 3 | Cả 3 game chơi được, cờ chống gian lận, mã theo lô (✅ game 3 và luồng hoàn thành xong 25/11) |
| 28/11 | Thử trên điện thoại; script sao lưu MongoDB (✅ script xong 25/11, còn chạy thử thật) | Danh sách lỗi, bản sao lưu |
| 29/11 | Thử nghiệm ~20 người (gắn nhãn `pilot`) | Danh sách lỗi từ người thử |
| 30/11 | Sửa lỗi; xóa dữ liệu pilot; chạy thử script chấm AI | Bản ổn định, sẵn sàng mở thu |
| 1/12 | MỞ THU HƯỚNG 2 (đến 20/12) | Thu thập đang chạy |
| trước 10/12 | Web quản trị chấm (phiên 3) xong | Trang quản trị chấm |
| trước 15/12 | Phiên 4 xong | |

## Việc phát sinh
- 25/11 (sao lưu MongoDB): `scripts/backup_mongo.py`, `scripts/restore_mongo.py`, `src/sparkmind/backup.py`, `tests/test_backup.py`; sao lưu chỉ đọc, khôi phục chỉ vào database mới. Việc còn lại: chạy sao lưu thật hằng ngày từ 28/11 và thử khôi phục vào database tạm một lần. Xem `docs/decisions.md` mục cuối.
- 24/11 (cờ và lô mã): `src/sparkmind/flags.py`, `flags_store.py`, `scripts/compute_flags.py`, `web/thoigian.js` (đo thời gian từng câu), cờ `lam_qua_nhanh`, `mot_dap_an`, `bi_gian_doan` ở `participants.flags`; `make_codes.py --batch`; trang quản trị có cột/lọc cờ, thống kê cờ ở Tổng quan, thống kê theo lô mã. Quyết định của Trang: KHÔNG thêm câu kiểm tra chú ý. Việc còn lại: chỉnh ngưỡng `config.CO_*` sau pilot 29/11 rồi chạy `python scripts/compute_flags.py`.
- 22/11: `tests/test_form_text.py` (kiểm tra chữ trên giao diện khớp nội dung form).
- 22/11: `docs/credits.md` (ghi nguồn, tác giả ảnh game: gạch, chai, ghế).

- 25/11 (thiết kế lại luồng game 1–2–3): game 2 nộp chỉ trả {ok}, đáp án chỉ ở `GET /api/research/review` sau `completed_at`; game 3 một màn, menu trái, một lần nộp, đo thời gian từng ô; khối hướng dẫn bốn mục từ content; tên nút thống nhất ("Tiếp tục", cuối game 3 "Nộp bài"); trang tổng kết có nút "Xem lại bài của bạn" (`web/review.js`, `web/game_chung.js`). Xem `docs/decisions.md` mục cuối.
- 25/11 (trang tổng kết): khối "Mô hình đã dựa vào đâu?" thu gọn, 4 gạch đầu dòng; số 6/10 và ±10 gom về `results_ui.json` > `so_mo_hinh`; nút "Xem lại kết quả bài làm" dưới điểm, mở thẳng `#xem-lai` (F5, Back đúng chỗ, chỉ khi đã hoàn thành); thẻ cảm ơn mailto ở cuối trang. Test: `tests/test_result_page.py`.
- 24/11 (tối): luồng quay lại/khôi phục theo từng màn (F5 giữ màn, quay lại mọi trang, hỏi tiếp tục hay làm mới khi vào lại), nút "Tiếp tục", nút xanh trang giới thiệu bên phải, bỏ dòng "Không phải bạn?".
- 24/11 (chiều): sửa viền lỗi bị đè, bản nháp `sessionStorage` (`web/nhap.js`), `no-cache` cho `/play`, xem lại game đã nộp, dải tên game, bố cục game 2 mới.
- 24/11 (sửa): kết quả game 2 tô xanh/đỏ có ✓/✗; `GET /api/research/progress` (`src/sparkmind/progress.py`, `server/progress_api.py`) để F5 hoặc nhập lại mã về đúng bước dở dang, điền sẵn câu trả lời, khóa sửa khảo sát sau `completed_at`; đổi `edited_at`/`edit_count` thành `sua_luc`/`so_lan_sua`.
- 24/11: game 2 (`server/game2.py`, `src/sparkmind/game2_store.py`, `score_game2.py`, `web/game2.js`) và `completed_at` (`game_store.kiem_tra_hoan_thanh`, danh sách `config.GAME_BAT_BUOC`).
- 23/11: `docs/rubric_game1.md` và `src/sparkmind/score_game1.py` (lọc ý hợp lệ, đếm fluency; không chấm lúc nộp).
- **Làm khi phân tích (sau khi thu xong, sau 20/12):** chấm đa dạng (flexibility) và độc đáo (originality) của game 1. AI gán nhóm công dụng cho từng ý hợp lệ và gom ý tương tự; 2 người chấm kiểm tra lại một mẫu (cùng mẫu rút khoảng 12–15/12). Độc đáo tính trong cùng đồ vật, ý xuất hiện ở dưới 5% người chơi. Chi tiết: `docs/rubric_game1.md`.

## Ba game (đã chốt hướng)
1. Đồ vật bí ẩn (kiểu AUT): số ý, số ý hợp lệ (AI lọc), độ độc đáo theo tần suất.
2. Soi lỗi AI (đã xong 24/11): 12 ý, 5 ý sai, chọn ý cho là sai, +1/−1, tối thiểu 0, tối đa 5, chấm tự động; không nói số ý sai.
3. Làm tốt hơn AI (đã xong 25/11): 2 tình huống cố định (`g3_t1`, `g3_t2`), mỗi tình huống viết từ 80 ký tự trở lên (đếm ký tự, đổi 25/11), tối đa 800 ký tự; không hiện điểm cho người chơi. Chấm AI ngày 1–4/12 (collection riêng); AI chấm tất cả, 2 người chấm kiểm tra trên mẫu 100–150 bài rút đều hai tình huống. Rubric sẽ viết cùng script chấm (bản nháp cũ `them_y_moi`/`khac_goc`/`kha_thi` đã bỏ khỏi file nội dung).
Nội dung nháp: `content/games/`, `content/form_b.json`.

## Lịch cuối năm (cập nhật 23/11/2026)
Lý do đổi: thu hướng 2 mở sớm hơn (1/12 thay vì 7/12) và kéo dài 1/12–20/12 để đủ 300 người; vì vậy dồn việc code và thử nghiệm vào 24–30/11.
| Ngày | Việc |
|---|---|
| 1/12 | Mở thu hướng 2 |
| trước 10/12 | Web quản trị chấm (phiên 3) xong |
| 12–15/12 | Rút mẫu (khoảng 100–150 bài) cho 2 người chấm; người chấm chỉ kiểm chứng điểm AI trên mẫu này |
| trước 15/12 | Phiên 4 xong |
| 20/12 | Hướng 2 đóng thu |
| 22/12 | Chốt (đóng băng) dữ liệu; hướng 1 đóng thu (khoảng) |
| 23/12 | Hạn chót người chấm nộp kết quả |
| 23–27/12 | Chạy lại mô hình, SHAP, Kappa |
| 24/12–2/1 | Viết đề án |
| 2–3/1/2027 | Gửi thầy bản gần hoàn chỉnh |
| 11/1/2027 | Nộp điện tử về trường |

## Danh sách đóng băng mô hình (~22/12)
Làm theo thứ tự, mỗi bước chạy xong mới sang bước sau:
1. Chạy lại notebook 03 và 04 trên dữ liệu đã đóng băng.
2. Huấn luyện lại `models/`: mô hình đủ biến (notebook 04) và mô hình B4 (`python scripts/train_b4.py`).
3. Chạy lại `python scripts/make_contrib_thresholds.py` (cập nhật `models/do_lon.json`).
4. Cập nhật MỘT nơi duy nhất: `so_mo_hinh` trong `content/results_ui.json` (`dung_tren_10` = `dung_khoang_x_tren_10`, `sai_so_diem` = MAE, `sai_so_noi` = MAE bỏ phần lẻ, cả ba lấy từ `models/model_b4_meta.json`) và ghi số thật vào `docs/decisions.md`. `tests/test_result_page.py` báo lỗi nếu hai nơi lệch nhau. `model_version` tự đổi theo ngày và số dòng của meta.
5. Chạy `python -m pytest tests -q`, rồi commit và deploy.
