# Quyết định đã chốt (cập nhật 23/11/2026)

Tài liệu này để Claude Code (và người mới vào dự án) hiểu bối cảnh mà không cần đọc lại các cuộc trao đổi cũ.
Sơ đồ cơ sở dữ liệu: `docs/erd.dbml`. Luồng dữ liệu: `docs/data_flow.md`.

## Phạm vi và lịch
- Hạn nộp: tháng 1/2027 (chưa rõ ngày). Code hai hướng xong trước 30/11 (xem lịch mới 23/11 bên dưới).
- Hướng 1 cần khoảng 1000 form (hiện 460; Google Form thu đến hết tháng 12). Hướng 2: 300 người, thu từ 1/12 đến 20/12.
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
- FastAPI, MongoDB Atlas M0 (database `spark-mind`, có gạch ngang; code đọc tên từ `MONGODB_DB`, mặc định cũng là `spark-mind`), Render miễn phí + cron-job.org ping `/health` mỗi 10 phút. Mô hình XGBoost lưu định dạng gốc, giải thích từng người bằng `pred_contribs`.
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
- **Người chấm:** đã có đủ 2 người. (Lịch cũ 15/12 và 24/12 đã đổi, xem mục 23/11/2026.)
- **Lịch thu:** (đã thay bằng lịch 23/11 bên dưới)
- **Đồng ý tham gia:** chỉ cần tích ô (người chơi, và thêm ô của người lớn với lớp 6–12); không cần giấy.
- **Mã tham gia:** mã dùng một lần được giữ; phát theo lô cho đội thuê và tình nguyện viên; chế độ demo cho người ngoài.
- **Giới hạn tốc độ:** chỉ đếm mã sai (10 lần mỗi phút theo IP). IP có thể bị giả qua header: hạn chế đã biết, chỉ dùng để gắn cờ.
- **Dữ liệu hướng 2:** lưu riêng (`participants`, `behavior_answers`, `self_assessment`...), không vào `survey_form1`.
- **Form v2 (đổi chữ 20/11):** 460 form cũ được đánh dấu `nguon="excel_import"`.


## Lịch mới (23/11/2026)
- **24–27/11:** game 2 + `completed_at`; chống gian lận + 2 câu kiểm tra chú ý; tạo mã hàng loạt; game 3. **28/11:** thử điện thoại + script sao lưu MongoDB. **29/11:** thử nghiệm ~20 người (nhãn `pilot`). **30/11:** sửa lỗi, xóa dữ liệu pilot, chạy thử script chấm AI.
- **1/12:** mở thu hướng 2. **20/12:** đóng thu. Web quản trị chấm (phiên 3) xong trước 10/12; phiên 4 trước 15/12.
- **Người chấm:** rút mẫu khoảng 12–15/12; người chấm chỉ kiểm chứng điểm AI trên một mẫu (không chấm toàn bộ). Hạn chót chấm 23/12.
- **22/12:** chốt dữ liệu. 23–27/12 chạy lại mô hình, SHAP, Kappa. 24/12–2/1 viết. Gửi thầy 2–3/1. Nộp điện tử 11/1/2027.
- **Lý do đổi:** thu dữ liệu hướng 2 dài hơn (1/12–20/12 thay vì 7/12–20/12) để đủ 300 người.

## Nút Quay lại (22/11/2026)
- Người chơi được quay lại sửa phần A, B, C trước khi vào game 1 (trong game thì không); từ 24/11 được sửa cả khi đã chơi game, cho tới khi có `completed_at`. Sửa ghi đè câu trả lời cũ (vẫn một tài liệu mỗi người), ghi `sua_luc` và `so_lan_sua` (đổi tên ngày 24/11 từ `edited_at`/`edit_count`/`info_edited_at`; dữ liệu cũ nếu có vẫn mang tên cũ, chưa có dữ liệu thật nên không di chuyển). Email và đồng ý ban đầu không sửa được. Không có `edit` thì nộp lại vẫn trả 409.

## Mô hình (23/11/2026, notebook 03, `src/sparkmind/modeling.py`)
- **Biến mục tiêu:** chính là `muc` (Thap, Trung_binh, Cao); phụ là `diem_sang_tao` (hồi quy). Đây là năng lực sáng tạo **tự nhận thức**.
- **Danh sách đặc trưng (35):** `lop_so`, `A2_nu`, `A2_khac`, `cap_hoc` (one-hot), `B2_so`, `B5_so`, `B4_1..B4_7` (số gốc, KHÔNG đảo chiều; đảo chiều chỉ dùng cho điểm tổng hành vi), các cột 0/1 của B1, B3, B6, B7 và `B1_so`, `B3_so`, `B6_so`. Danh sách trắng nằm ở `modeling.DAC_TRUNG`.
- **Cấm làm đầu vào:** C1..C5, `diem_sang_tao`, `muc`, C6, `C6_so`, `dot`, `nguon`, `thoi_gian`, các cột `in_*`, `co_*`, tên trường, id. Hàm `kiem_tra_cot_cam` báo lỗi nếu lọt; có test (`tests/test_modeling.py`).
- **Lý do loại C6:** C6 (hoạt động sáng tạo 12 tháng) thuộc khối đo sáng tạo, không phải hành vi dùng LLM; đưa vào sẽ làm lẫn hai thứ. Chỉ chạy như phân tích bổ sung (mục F của notebook), kết quả thay đổi trong ±0.01 macro-F1.
- **Không dò tham số.** Tham số cố định: RF (500 cây, `min_samples_leaf=3`, `class_weight=balanced_subsample`); XGBoost (`max_depth=3`, `learning_rate=0.05`, `n_estimators=300`, `subsample=0.8`, `colsample_bytree=0.8`, trọng số mẫu cân bằng lớp tính trong fit); Logistic (`class_weight=balanced`, chuẩn hóa). Lý do: mẫu nhỏ (297), dò tham số dễ làm số đẹp giả.
- **Đánh giá:** CV phân tầng lặp 5 lớp × 10 lần, `random_state=42`, mọi mô hình dùng chung các lần chia (so ghép cặp theo fold). Chỉ số chính macro-F1. Khoảng 95% bằng bootstrap trên 50 fold, chỉ là *khoảng tham khảo* vì fold không độc lập hoàn toàn. Tiền xử lý (điền thiếu bằng trung vị, chuẩn hóa, one-hot) nằm trong pipeline, chỉ học trên train.
- **Kiểm tra rò rỉ:** xáo trộn nhãn thì macro-F1 phải ≈ 0.33 (đã đúng, 0.31–0.35).
- **Bản dữ liệu:** bản chính 297 là kết quả chính; 361 và 231 chạy riêng (T6b), 231 chỉ để đối chiếu vì bộ lọc dùng B4_3/B4_4.
- **LOBO và thử độc lập (T7, T8):** `dot` chỉ để chia nhóm, không là đặc trưng. File Excel hiện chỉ có dot1, dot2, dot3 (dot4, dot5 chưa có), nên T8 chỉ có dot1 làm tập thử (31 dòng) và trùng dòng dot1 của T7.
- **Lưu ý khi viết báo cáo:** macro-F1 khoảng 0.6–0.66 khá cao so với mức ngẫu nhiên 0.33, nhưng B4 và C cùng nằm trong một bảng tự khai (cả B4_3, B4_6 tiêu cực cũng tương quan dương với điểm), nên có thể một phần do cách trả lời chung. Ghi là giả thuyết, không viết thành kết luận nhân quả.

## Kết quả bỏ nhóm biến và chẩn đoán dot1 (23/11/2026, notebook 03 mục G2, G3)
- **G2 (T9, bản chính 297, CV 5×10, cùng các lần chia với T6):** nhóm B4 (7 câu) mang gần hết tín hiệu. "Chỉ có B4" cho macro-F1 xấp xỉ "đủ biến" (RF 0.658 so với 0.659). Bỏ B4 thì macro-F1 còn khoảng 0.43 và R2 hồi quy khoảng 0 (từ −0.12 đến 0.01). Bỏ B1/B3/B6/B7 hoặc bỏ B2/B5 gần như không đổi kết quả, tức các nhóm này không thêm gì. Chỉ có thông tin nền (lớp, giới, cấp học) cho macro-F1 khoảng 0.34, ngang đoán bừa.
- **G3 (dot1, n=31, giữ lại dot1, huấn luyện trên dot2+dot3):** Random Forest macro-F1 0.56, dummy theo tỉ lệ trung bình 0.32 (độ lệch chuẩn 0.09 qua 200 hạt giống); RF đoán đúng 19/31 dòng; R2 hồi quy khoảng 0. F1 cao hơn đoán bừa nhưng R2 không, nên **bằng chứng lẫn lộn**, và cỡ mẫu quá nhỏ để kết luận.
- **Quyết định:** giữ nguyên danh sách đặc trưng 35 cột (không bỏ nhóm nào dù không thêm gì, vì kết quả ablation là phân tích bổ sung, không dùng để chọn lại đặc trưng sau khi đã xem kết quả). Không dò tham số.
- **T8 (thử độc lập):** chờ dữ liệu dot4, dot5 trong MongoDB. Sau khi chốt và đóng băng dữ liệu (khoảng 22/12), chạy lại notebook 03 với `NGUON = 'mongo'`.

## SHAP và lưu mô hình (23/11/2026, notebook 04, `src/sparkmind/explain.py`)
- **Phương pháp:** `shap.TreeExplainer` cho XGBoost và Random Forest (phân loại 3 mức và hồi quy), huấn luyện trên toàn bản chính 297 với đúng tham số của notebook 03. SHAP **mô tả mô hình, không phải nguyên nhân**. Cấp học one-hot thành 3 cột, khi xếp hạng thì cộng SHAP 3 cột lại. Tầm quan trọng gộp 3 mức = trung bình của ba mức; XGBoost (margin) và RF (xác suất) khác thang nên chỉ so thứ hạng.
- **Kiểm tra bắt buộc (có test, `tests/test_explain.py`):** tổng SHAP + giá trị nền = đầu ra mô hình (sai số < 1e-4); SHAP của TreeExplainer trùng `pred_contribs` của XGBoost (< 1e-4). Riêng hồi quy điểm 0–100, sai số làm tròn float32 của XGBoost cỡ 1.0e-4, nên ngưỡng là tương đối 1e-5 x điểm lớn nhất (khoảng 9e-4). Lệch thực tế 1.01e-4, chính `pred_contribs` của XGBoost cũng lệch `predict()` cùng mức đó.
- **Lưu mô hình:** chỉ XGBoost, dạng JSON gốc (`models/xgb_clf.json`, `models/xgb_reg.json`) cùng `models/model_meta.json` (thứ tự cột, trung vị điền thiếu, các cấp học, ánh xạ mức, phiên bản, macro-F1 CV). Server đọc bằng `xgboost.Booster`, không cần sklearn. **Không lưu Random Forest dạng pickle:** pickle phụ thuộc phiên bản thư viện, nạp file lạ có thể chạy mã tùy ý, và RF 500 cây rất nặng. RF chỉ dùng để đối chiếu thứ hạng biến. Thư mục `models/` (khoảng 1.3 MB, dưới 5 MB) được commit để server chạy `/api/predict`; đóng băng lại khi chốt dữ liệu (khoảng 22/12).
- **Kết quả (bản chính 297):** nhóm B4 (7 câu) cộng "Lớp" chiếm 8 hạng đầu ở cả hai mô hình. B4_3, B4_6 là câu tiêu cực nhưng giá trị cao vẫn đẩy dự đoán lên mức Cao (Spearman giá trị gốc với SHAP: +0.90 và +0.69), phù hợp giả thuyết xu hướng trả lời chung. Không diễn giải từng biến ngoài B4 (hạng dao động mạnh qua 50 lần chia). Tên bảng: `T10_shap_*` (bảng dot1 của G3 đã đổi tên thành `T9b_dot1_*` để khỏi trùng), `T11_*`.

## API dự đoán (23/11/2026, `src/sparkmind/predict.py`, `server/predict_api.py`)
- **Demo (`POST /api/predict/demo`):** chỉ dùng **7 câu B4** (bắt buộc đủ, số nguyên 1–5, sai thì 422 tiếng Việt). **Không ghi MongoDB, không ghi nội dung request vào log.** Giới hạn 30 lần/phút/IP. Dùng **mô hình riêng chỉ có 7 cột B4** (`models/xgb_b4_clf.json`, `xgb_b4_reg.json`, `model_b4_meta.json`; code `src/sparkmind/model_b4.py`, huấn luyện `python scripts/train_b4.py`), nên không còn điền trung vị. Trả `muc`, `xac_suat` (tổng 1), `diem_du_doan` (kẹp 0–100), tối đa 4 câu ảnh hưởng nhiều nhất (`chieu` "tang" = kéo điểm dự đoán lên, "giam" = kéo xuống, lấy từ dấu `pred_contribs` của mô hình HỒI QUY; `do_lon` nhỏ/vừa/lớn; không lộ số SHAP thô), `model_version`, `che_do`.
- **Kết quả nghiên cứu (`GET /api/research/result`):** chỉ trả khi người tham gia đã **hoàn thành cả 3 game** (`completed_at`), chưa xong thì 409. Dùng B4 gốc trong `behavior_answers` (không đảo chiều), cũng chỉ 7 câu B4 như demo. Không lưu thêm gì. Token CHỈ nhận qua header `X-Session-Token` (đã bỏ nhận query vì lọt vào log truy cập; web chưa gọi endpoint này). `completed_at` do server gán (24/11) khi đủ mọi game trong `config.GAME_BAT_BUOC` = (1, 2, 3); game 3 chưa có nên hiện chưa ai có `completed_at` và endpoint này vẫn trả 409.
- **`pred_contribs` thay `shap` trên server:** server chỉ cần `xgboost-cpu` (ghim `xgboost-cpu==3.4.1`, đúng bản trong meta; vẫn `import xgboost`) và numpy; không shap, sklearn, pickle. Giải thích từng người = `pred_contribs` của mô hình hồi quy B4 (đóng góp tính bằng điểm 0–100). Mức và xác suất vẫn từ mô hình phân loại B4. Test kiểm tra: đóng góp + nền = điểm dự đoán; dự đoán trùng mô hình nạp từ JSON.
- **Ngưỡng nhỏ/vừa/lớn:** `models/do_lon.json`, là phân vị 33.3% và 66.7% của |`pred_contribs`| của mô hình hồi quy B4 (đơn vị điểm) cho 7 câu B4 trên bản `chat` 297 (kết quả 23/11/2026: 1.48 và 3.48 điểm) (tái lập: `python scripts/make_contrib_thresholds.py`). Phải tính lại khi đóng băng lại mô hình (khoảng 22/12).
- **Chữ giao diện kết quả:** `content/results_ui.json`; giọng trung tính ("mức tự đánh giá sáng tạo"), nói rõ: ước lượng thống kê từ tự đánh giá, dựa trên 7 câu, đúng khoảng 6/10 trường hợp trong thử nghiệm, không phải đánh giá con người hay năng lực thật. "6/10" = accuracy CV 5×10 của mô hình B4 làm tròn xuống một chữ số. **Số thật đo 23/11/2026 (bản 297, mô hình B4, 50 fold): accuracy 0.628, macro-F1 0.633, balanced accuracy 0.639 (phân loại); R² 0.477, MAE 10.56 điểm (hồi quy).** Lưu trong `models/model_b4_meta.json`. Phải đo lại và đổi chữ khi đóng băng mô hình (~22/12). Hai mô hình đủ biến cũ (`xgb_clf.json`, `xgb_reg.json`) giữ nguyên cho luận văn.
- **Thư mục `models/` không được phục vụ ra ngoài:** web chỉ mount `web/` ở `/play`; có test kiểm tra.
- **RAM (đo trên Windows, `python scripts/measure_memory.py`):** khoảng 254MB nếu chỉ nạp predict, khoảng 274MB cả server sau lần dự đoán đầu; dưới ngưỡng 300MB nhưng sát. Cần đo lại trên Render.

## Nền tảng quản trị (23/11/2026, `server/auth*.py`, `server/admin_*.py`, `web/admin/`)
- **Tài khoản (`users`):** vai trò `admin`, `viewer`, `rater`. Mật khẩu tối thiểu 12 ký tự, băm `hashlib.scrypt` (n=2^14, r=8, p=1, muối ngẫu nhiên 16 byte, tham số nằm trong chuỗi lưu). Tài khoản admin đầu tiên tạo bằng `python scripts/create_user.py --username trang --role admin` (hỏi mật khẩu bằng getpass, không nhận qua tham số). Trên web, admin chỉ tạo được `viewer` và `rater`, với mật khẩu tạm (admin nhập hoặc hệ thống tự sinh, hiện đúng một lần) và `must_change_password=true`. Không API nào trả `password_hash`.
- **Phiên (`admin_sessions`):** cookie `sm_admin` HttpOnly, SameSite=Strict, Secure khi chạy HTTPS (dựa vào `--proxy-headers` của uvicorn trên Render). Token ngẫu nhiên, DB chỉ lưu băm SHA-256. Hết hạn sau 2 giờ không hoạt động, tối đa 12 giờ; TTL index tự xóa, code vẫn tự kiểm tra hạn. Đổi hoặc đặt lại mật khẩu, khóa tài khoản thì mọi phiên của người đó bị xóa.
- **CSRF:** mọi POST/PUT/PATCH/DELETE cần header `X-CSRF-Token` (lấy từ `GET /api/auth/me` hoặc phản hồi đăng nhập) và header `Origin` trùng `Host`. Đăng nhập cũng kiểm Origin.
- **Chống dò mật khẩu:** sai 5 lần trong 15 phút theo cặp (username + IP) thì khóa 15 phút (HTTP 429). Bộ đếm ở `login_attempts` (khóa là băm, không lưu IP thô; đếm cả với username không tồn tại, nên không lộ tài khoản có hay không). Lỗi đăng nhập luôn là một thông báo chung; user không tồn tại vẫn chạy scrypt (hash giả) để thời gian trả lời như nhau, so sánh bằng `hmac.compare_digest`. IP lấy từ `request.client.host`, không đọc `x-forwarded-for`. `users.failed_attempts` và `locked_until` chỉ để hiển thị, không dùng để chặn (chặn theo cặp tên + IP, tránh việc kẻ xấu khóa hộ tài khoản người khác).
- **Phân quyền từ chối mặc định:** mọi route `/api/admin/*` và `/api/rate/*` phải có dependency `require_role(...)` (hoặc khóa `INGEST_SECRET` cho `/api/admin/memory`, giữ nguyên). `tests/test_admin_auth.py` duyệt toàn bộ route (kể cả router gộp lười của FastAPI mới) và FAIL nếu có route thiếu kiểm tra; có test chứng minh bộ quét bắt được route thiếu. User đang bị buộc đổi mật khẩu thì bị chặn ở mọi route quản trị. Chưa có route `/api/rate/*` nào (chấm bài làm ở bước sau).
- **Nhật ký (`audit_log`):** `write_audit(db, user, action, collection, doc_id, detail)` chỉ thêm, không có hàm sửa/xóa; tự bỏ mọi khóa chứa password/hash/token/secret/csrf khỏi `detail`. Ghi: đăng nhập, đăng nhập sai (không ghi tên đã gõ, vì người dùng hay gõ nhầm mật khẩu vào ô tên), đăng xuất, đổi mật khẩu, tạo/đặt lại/khóa/mở tài khoản.
- **Thống kê (`GET /api/admin/stats?ex_test=true`, admin và viewer):** chỉ số đếm tổng hợp bằng aggregation, nhớ 30 giây, không email, tên, IP hay nội dung (có test kiểm). Hướng 1 tính trên `survey_clean`: bản rộng (`in_chinh`, 361), chính (`in_chat`, 297), rất chặt (`in_rat_chat`, 231). Ngày theo UTC. **Giả định cần Trang xác nhận:** "dữ liệu thử" = bản ghi có `nguon` hoặc `dot` (hướng 1), hoặc `source` (mã và người tham gia hướng 2) thuộc `config.NHAN_DU_LIEU_THU = ("thu", "pilot")`. Hiện dữ liệu thật chưa có nhãn này (nhãn khi tạo mã chỉ nằm trong CSV, không lưu DB), nên công tắc "ẩn dữ liệu thử" chưa lọc được gì cho tới khi gắn nhãn.
- **Giao diện (`web/admin/`):** HTML/CSS/JS thuần, hash router, không thư viện ngoài; toàn màn hình, thanh bên 240px thu gọn được (ngăn kéo trên màn nhỏ). Chữ trong `content/admin_ui.json` (đọc qua `GET /api/auth/ui`; chỉ câu báo lỗi tải giao diện là viết cứng vì lúc đó chưa có chữ). Header `X-Robots-Tag: noindex`, `Cache-Control: no-store`, `X-Frame-Options: DENY`, CSP `'self'` cho `/admin`, `/api/auth`, `/api/admin`, `/api/rate`. Phông Nunito tải từ Google Fonts như web người chơi (chỉ phông, không có thư viện).
- **Hạn chế đã biết:** bộ đếm thử đăng nhập và cache thống kê dùng chung giữa các tiến trình qua MongoDB (đếm) hoặc không (cache theo từng tiến trình, mỗi tiến trình có thể trễ tới 30 giây). Chưa có chức năng "quên mật khẩu" ngoài việc admin đặt lại.

## Trang dữ liệu quản trị và nhãn dữ liệu (23/11/2026, phiên 2)
- **Registry:** `src/sparkmind/admin_registry.py` là NƠI DUY NHẤT mô tả các bảng hiển thị (tên Việt, cột, tìm kiếm, lọc, sắp xếp, quyền, chế độ `readonly` hoặc `crud`). `server/admin_data_api.py` đọc registry để tạo route; route registry không cho phép thì không được tạo (bảng readonly không có POST và PATCH, `survey_form1` không có DELETE). `kiem_tra_registry()` chạy trong test. Cách thêm bảng: README.
- **Chế độ từng bảng:** readonly: `survey_form1`, `survey_clean`, `participants`, `behavior_answers`, `self_assessment`, `game_responses`, `scores`, `audit_log`. crud: chỉ `access_codes`. `schools` là readonly (đổi ngày 23/11 theo Trang): danh sách trường quản lý bằng file `content/schools.csv`, trang có ghi chú nói rõ. `users` giữ trang Người dùng của phiên 1 (không có trong registry); `admin_sessions`, `login_attempts` không hiển thị; `content/` là file, chưa đưa vào.
- **Quyền:** xem và xuất CSV: admin, viewer (riêng `audit_log`: chỉ admin); rater không thấy các trang này. Ghi: chỉ admin, chỉ bảng crud. Xóa từng bản ghi (gõ lại ID, `?confirm=<id>`): chỉ admin, ở `survey_clean` và các bảng hướng 2 (không ở `schools`); **không xóa được `survey_form1`** (dữ liệu gốc) và `audit_log`. `access_codes` đã dùng thì không sửa hay xóa. Không có route drop collection/database, không có xóa hay sửa cả bảng.
- **Che thông tin:** `password_hash`, `session_token`, `csrf_token`, `user_agent` không bao giờ ra giao diện/CSV/nhật ký. Email che dạng `ng***@gmail.com` và không vào CSV; `ip_hash` chỉ hiện 8 ký tự đầu; IP thô (nếu có trường tên ip) giữ 3 phần đầu; mã tham gia chỉ admin thấy đủ, viewer thấy 2 ký tự đầu. CSV tối đa 5000 dòng (`X-Truncated`), chống công thức Excel, ghi `audit_log` mỗi lần xuất.
- **Nhật ký:** mọi tạo/sửa/xóa ghi `data_create|data_update|data_delete` với bảng, ID, trường cũ và mới (không ghi mã tham gia hay bí mật); xóa lưu tóm tắt đã che. Xuất CSV ghi `data_export`.
- **Nhãn dữ liệu `data_label` (thu | pilot | that):** nằm ở `access_codes`, `participants`, `behavior_answers`, `self_assessment`, `game_responses`, `scores`, `survey_clean`; KHÔNG ở `survey_form1`. Mã tạo bằng `make_codes.py` mặc định `that` (`--data-label thu|pilot` cho mã thử; pilot ngày 30/11); nhãn được chép từ mã sang người tham gia và sang các bảng con. Form hướng 1 mới nhận nhãn `that` ở bản sạch. **Bản ghi thiếu nhãn được coi là `that`** (an toàn). `scripts/run_cleaning.py` khi ghi lại `survey_clean` GIỮ `data_label` hiện có của từng bản ghi (`data_label.giu_nhan_hien_co`, có test); bản ghi chưa có nhãn vẫn chưa có (coi là `that`).
- **Thay quy ước phiên 1:** "dữ liệu thử" nay là `data_label` thuộc `config.NHAN_DU_LIEU_THU = ("thu", "pilot")`, không còn dựa vào `nguon`, `dot` hay `source`. Công tắc "ẩn dữ liệu thử" ở trang Tổng quan và mọi danh sách lọc theo trường này (mặc định bật).
- **Migration (`scripts/migrate_data_label.py`; quy tắc nhãn dự kiến chốt trước khi tạo mã thật, khoảng 27/11, chưa phải đã chốt):** hướng 2 (mọi bản ghi hiện có, vì thu dữ liệu thật chỉ bắt đầu 1/12) gán `thu`; `survey_clean` gán `that` (gồm `web`, `google_form`, `excel_import`); `survey_form1` không đụng. Chỉ gán cho bản ghi chưa có nhãn nên chạy lại không đổi gì. Mặc định chỉ xem (dry-run); `--apply` phải gõ `GAN NHAN`. Dry-run trên Atlas ngày 23/11 (chỉ đọc): `access_codes` 1, `survey_clean` 460, các bảng khác 0. CHƯA chạy `--apply`. Sau đó mã `access_codes` thử duy nhất này đã bị Trang xóa tay trong Compass trước 23/11 (không qua web quản trị, nên `audit_log` không có dòng nào về việc này); kiểm tra chỉ đọc ngày 23/11 thấy mọi bảng hướng 2 đều 0 bản ghi, `survey_clean` 460 và chưa có nhãn.
- **Xóa dữ liệu thử (`/#/cleanup`, `GET/POST /api/admin/test-data`):** chỉ admin; xem trước số bản ghi theo bảng (dry-run), phải gõ `XOA`, ghi `audit_log` theo bảng. Chỉ đụng nhãn thu/pilot ở `access_codes`, `participants`, các bảng con, `scores`, `survey_clean`; có `assert` chặn cấu hình làm nhãn `that` lọt vào danh sách xóa. **Xóa một `participants` thì xóa luôn dữ liệu của người đó** ở `behavior_answers`, `self_assessment`, `game_responses` và `scores` (qua game_responses). Màn xác nhận hiện số bản ghi con sẽ bị xóa theo từng bảng (`GET /api/admin/data/participants/{id}/lien-quan`, chỉ đọc); số đã xóa ghi vào `audit_log` (`da_xoa_bang_con`). Mã trong `access_codes` của người đó vẫn còn và vẫn ở trạng thái đã dùng. Bộ lọc con được tính hết trước khi xóa (có test, vì `scores` tìm qua `game_responses`).
- **`schools`:** matching vẫn dùng `content/schools.csv`; muốn đổi danh sách thì sửa CSV rồi chạy `scripts/import_schools.py`.

## Hạn chế đã biết
- **Xu hướng trả lời chung:** B4 và điểm sáng tạo (C1–C5) cùng là tự đánh giá, cùng một lần trả lời; B4_3 và B4_6 (câu tiêu cực) vẫn tương quan dương với điểm. Có thể một phần tín hiệu là cách trả lời chung. Chỉ nói về liên hệ dự đoán, không nói về nguyên nhân.
- **Dữ liệu dot1 nhỏ:** nhóm form tự nhiên hiện chỉ 31 dòng (trong bản 297), kết quả rất dao động; chưa kết luận được về nhóm tự nhiên.
- **Chống gian lận theo IP trên Render:** IP có thể bị giả qua header, nên `ip_hash` và giới hạn tốc độ chỉ để gắn cờ, không phải biện pháp chặn chắc chắn.
- Các hạn chế khác đã ghi ở trên: biến đầu ra tự nhận thức, mẫu nhỏ, trường Bắc Bình chiếm khoảng 9% mẫu.

## Game 2 "Soi lỗi AI" và `completed_at` (24/11/2026)
- **Đề cố định:** một tình huống (nhờ AI giới thiệu Việt Nam), **12 ý, trong đó 5 ý sai**, thứ tự hiển thị cố định (không xáo). Nội dung ở `content/games/game2.json` (thay bản nháp 20/11 nhiều đề x 8 nhận xét). Mỗi ý sai có `loai_loi` (sai_nam, sai_so_lieu, sai_so_sanh, khai_quat_vo_can_cu, nhan_qua_vo_can_cu) để phân tích sau.
- **Không cho người chơi biết số ý sai:** đề chỉ nói "một số ý sai"; giao diện và kết quả không hiện tổng số ý sai. Người chơi chọn 0–12 ý.
- **Chấm ở server:** +1 mỗi ý sai chọn đúng, −1 mỗi ý đúng bị chọn nhầm, tối thiểu 0, **tối đa 5**. Lưu trong `game_responses` (game = 2): `answer = {selected_ids, score, n_correct, n_wrong}`, `duration_sec` (server tính từ `started_at`), `data_label` kế thừa từ `participants`. Không có giới hạn thời gian.
- **Không lộ đáp án trước khi nộp:** `/game2/start` chỉ trả `id` và `van_ban`; `la_loi`, `loai_loi`, `giai_thich` chỉ trả sau khi nộp (và không trả `loai_loi`, không trả điểm).
- **Chống nộp trùng:** nộp lần hai không đổi bản đã lưu, trả lại kết quả cũ (200, khác game 1 trả 409) để tải lại trang vẫn thấy kết quả.
- **`participants.completed_at`:** `game_store.kiem_tra_hoan_thanh` gán khi mọi game trong `config.GAME_BAT_BUOC` (hiện (1, 2, 3)) đã có `submitted_at`; gán một lần (điều kiện `completed_at = None`), không ghi đè. Thêm game mới chỉ cần thêm số vào danh sách. Vì game 3 chưa có nên hiện chưa ai hoàn thành; làm xong game 3 là tự chạy.

## Hiển thị kết quả game 2 và khôi phục tiến độ (24/11/2026)
- **Tô màu theo nhận định của người chơi:** xanh ✓ = nhận định đúng (chọn ý sai đúng, hoặc không chọn ý đúng); đỏ ✗ = chưa đúng (chọn nhầm ý đúng, hoặc bỏ sót ý sai). Server trả `nhan_dinh_dung` cho từng ý. Mỗi ý ghi "Ý này đúng/SAI" và "Bạn đã chọn: sai / không chọn". Ý xanh chỉ ghi gọn; ý đỏ luôn có giải thích (ý đúng bị chọn nhầm dùng câu chung trong `research_ui.json` thay cho "Đúng."). Có ký hiệu ✓/✗ nên người mù màu vẫn phân biệt. Vẫn không hiện điểm, không nói số ý sai.
- **Nguyên nhân lỗi F5 về bước 3:** màn "Tiếp tục bài đang làm?" luôn gọi `manB()` và client không biết người chơi đã xong những bước nào; câu trả lời cũng không được tải lại.
- **`GET /api/research/progress`** (header `X-Session-Token`, chỉ đọc): trả `steps` (đã xong), `next` (`behavior`, `self_assessment`, `game1`, `game2`, `cho_game_khac` khi các game hiện có đã xong nhưng chưa đủ game bắt buộc, `completed`), `locked` và `answers` (câu trả lời đã lưu của chính người đó để điền sẵn). `config.GAME_DA_CO` = (1, 2) là các game đã có màn chơi; làm game 3 thì thêm 3 vào cả `GAME_DA_CO` và (đã có sẵn) `GAME_BAT_BUOC`.
- **Client:** tải lại trang hoặc nhập lại mã dùng dở (cùng email) đều gọi progress rồi đi thẳng đến bước dở dang (bỏ màn hỏi "Tiếp tục bài đang làm?", nên đã thay bằng lối thoát bên dưới). Nộp lại khảo sát dùng cờ `edit` lấy từ progress.
- **Khóa:** khảo sát (thông tin, form B, C1–C5) sửa được tới khi có `completed_at`; sau đó server trả 403. Sửa khảo sát chỉ ghi đè giá trị, tăng `so_lan_sua`, ghi `sua_luc`; không đụng `game_responses` và `completed_at`.
- **Game đã nộp:** chỉ xem lại. Game 1 nộp lại trả 409; game 2 nộp lại trả kết quả cũ; `start` của cả hai trả `submitted` và client bỏ qua.
- **Lối thoát máy dùng chung (24/11):** dòng "Không phải bạn? Dùng mã khác" cuối màn đã BỎ (24/11 tối, theo Trang, xem mục "Luồng quay lại và khôi phục" bên dưới); việc đổi người dùng chung máy nay làm ở màn hỏi khi vào lại web.
- **Tên game đánh số (24/11):** tiêu đề "Game 1: Đồ vật bí ẩn", "Game 2: Soi lỗi AI" ghép từ mẫu `tieu_game` ("Game {so}: {ten}") trong `research_ui.json` và khóa `ten` trong `content/games/gameN.json` (chỗ duy nhất giữ tên; game 3 đã có `ten`, khi làm chỉ cần gọi `tenGame(3, ten)`).
- **Điểm game 2 ở màn kết quả (24/11, theo yêu cầu của Trang; đổi quyết định "không hiện điểm"):** đầu màn hiện "Điểm của bạn: x/5" kèm chú thích cách tính; mỗi ý có điểm riêng (+1 chọn đúng ý sai, −1 chọn nhầm ý đúng, 0 còn lại). Chỉ trả sau khi nộp (`diem`, `n_correct`, `n_wrong` và `diem` từng ý); trước khi nộp vẫn không có và vẫn không nói số ý sai. Tổng điểm từng ý có thể lớn hơn điểm hiển thị vì điểm tổng chặn sàn 0.
- **Cách ghi từng ý (24/11):** bỏ cách ghi "Ý này đúng · Bạn đã chọn: sai" vì dễ hiểu lẫn. Nay hai dòng tách bạch: "Sự thật: ý này SAI/ĐÚNG" và "Bạn: đã đánh dấu là sai / không đánh dấu", kèm điểm ý và biểu tượng ✓/✗. Card bo góc 18px.

## Sửa lỗi giao diện 24/11 (chiều)
- **Viền đỏ báo thiếu câu bị đè nhau (nhất là thang 1–5):** nguyên nhân là `outline` lòi ra ngoài 4px trong khi các hàng thang sát nhau. Nay viền vẽ BÊN TRONG khung (`box-shadow: inset`), các hàng có khoảng cách, dòng báo lỗi trải hết bề ngang.
- **Không tự điền khi tải lại:** kiểm tra bằng trình duyệt giả cho thấy bài ĐÃ NỘP được điền lại đúng; có hai chỗ hở: (1) câu đang gõ dở chưa bấm "Tiếp tục" không được lưu ở đâu; (2) file giao diện không có `Cache-Control` nên trình duyệt có thể giữ bản JS cũ sau khi cập nhật. Đã sửa: bản nháp lưu ở `sessionStorage` (`web/nhap.js`; chỉ sống trong tab, gắn với token, xóa khi nộp xong phần đó hoặc khi bấm "Không phải bạn?"; đổi quyết định cũ "không lưu gì trong trình duyệt ngoài token" cho riêng bản nháp tạm này) và `/play/*` trả `Cache-Control: no-cache` (luôn hỏi lại bằng ETag). Bản nháp có cho khảo sát, ý game 1 và các ý đã đánh dấu ở game 2; đồng hồ game 1 vẫn do máy chủ tính.
- **Xem lại game đã nộp:** `/game1/start` sau khi nộp trả thêm `ideas` (chỉ của chính người đó); game 1 hiện đồ vật và các ý đã nộp (chỉ xem), game 2 hiện điểm và kết quả từng ý. Hai màn có nút chuyển qua lại ("Xem lại Game 1", "Sang Game 2").
- **Tên game:** dải xanh to "Game N" + tên ở đầu mọi màn game (chơi, xem lại, kết quả), thay cho tiêu đề nhỏ trong thẻ.
- **Bố cục game 2 mới:** khung "Tình huống" như tin nhắn gửi AI; 12 thẻ đánh số "Ý n", cả thẻ bấm được, nút gạt "Đánh dấu sai" đổi sang đỏ khi chọn; dòng đếm "Bạn đã đánh dấu n ý" (không nói tổng số ý sai). Kết quả: vòng điểm x/5, hai chip tóm tắt, thẻ xanh gọn, thẻ đỏ rộng có giải thích.

## Luồng quay lại và khôi phục (24/11, chiều tối; thay các quy định cũ về F5 và "Không phải bạn?")
- **Tải lại trang (F5) ở bước nào thì ở lại đúng màn đó**, kể cả trang giới thiệu, đồng ý, game đang chơi, kết quả. Tab nhớ "màn đang xem" ở `sessionStorage` (`datMan`/`docMan` trong `web/nhap.js`). Màn nhớ chỉ được mở nếu không vượt quá bước máy chủ báo (`GET /progress`): không nhảy cóc tới game chưa tới lượt.
- **Quay lại mọi trang trước, đi tiếp mọi trang sau:** nhập mã ⇄ đồng ý ⇄ sửa thông tin ⇄ form B ⇄ C1–C5 ⇄ giới thiệu 3 trò ⇄ Game 1 ⇄ Game 2 ⇄ trang "đã hoàn thành phần này". Màn "sửa thông tin" hiện lại chữ giới thiệu/đồng ý (chỉ đọc) kèm lớp, giới tính, trường; không hỏi lại email và đồng ý, không quay về ô nhập mã được vì mã đã dùng. Khảo sát sửa được tới `completed_at`; game đã nộp chỉ xem lại. Game 1 đang chơi mà bấm Quay lại: đồng hồ do máy chủ tính vẫn chạy, ý đã gõ được giữ bằng bản nháp, quay lại sau còn bao nhiêu giờ thì làm tiếp bấy nhiêu (hết giờ thì tự nộp).
- **Vào lại web sau khi thoát (đóng tab/trình duyệt; mở tab mới):** máy còn token trong `localStorage` nhưng tab không có `sessionStorage` -> hỏi "Tiếp tục bài đang làm?" hoặc "Dùng mã khác". Tiếp tục -> vào bước dở dang đầu tiên. Dùng mã khác -> chỉ xóa token, bản nháp, màn nhớ trong trình duyệt rồi về màn nhập mã; KHÔNG xóa gì trên máy chủ, người trước nhập lại mã (đúng email) vẫn làm tiếp.
- **Trước khi có token** (đang gõ email, tích đồng ý) tải lại trang vẫn giữ màn và chữ đã gõ (bản nháp ở `sessionStorage`, token rỗng).
- **Nút:** "Lưu và tiếp tục" đổi thành "Tiếp tục" (`giao_dien.nut_luu`). Ở các trang giới thiệu (nền xanh), nút xanh chính nằm bên phải, nút phụ (Quay lại...) bên trái.
