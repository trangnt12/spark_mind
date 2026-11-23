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


## Nút Quay lại (22/11/2026)
- Người chơi được quay lại sửa phần A, B, C trước khi vào game 1 (trong game thì không). Sửa ghi đè câu trả lời cũ (vẫn một tài liệu mỗi người), ghi `edited_at` và `edit_count` (hoặc `info_edited_at` ở participants). Email và đồng ý ban đầu không sửa được. Không có `edit` thì nộp lại vẫn trả 409.

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

## Hạn chế đã biết
- **Xu hướng trả lời chung:** B4 và điểm sáng tạo (C1–C5) cùng là tự đánh giá, cùng một lần trả lời; B4_3 và B4_6 (câu tiêu cực) vẫn tương quan dương với điểm. Có thể một phần tín hiệu là cách trả lời chung. Chỉ nói về liên hệ dự đoán, không nói về nguyên nhân.
- **Dữ liệu dot1 nhỏ:** nhóm form tự nhiên hiện chỉ 31 dòng (trong bản 297), kết quả rất dao động; chưa kết luận được về nhóm tự nhiên.
- **Chống gian lận theo IP trên Render:** IP có thể bị giả qua header, nên `ip_hash` và giới hạn tốc độ chỉ để gắn cờ, không phải biện pháp chặn chắc chắn.
- Các hạn chế khác đã ghi ở trên: biến đầu ra tự nhận thức, mẫu nhỏ, trường Bắc Bình chiếm khoảng 9% mẫu.
