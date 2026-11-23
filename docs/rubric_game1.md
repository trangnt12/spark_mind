# Quy tắc chấm game 1 "Đồ vật bí ẩn" (kiểu AUT)

Viết 23/11/2026. Code: `src/sparkmind/score_game1.py`. Test: `tests/test_score_game1.py`.
**Không chấm lúc người chơi nộp.** Lúc nộp chỉ lưu ý đã làm sạch (`server/game1.py`, `game_store.lam_sach_y`). Chấm làm sau, khi phân tích, để quy tắc sửa được mà không phải thu lại dữ liệu.

Cần nhớ khi viết báo cáo: đây là điểm tư duy sáng tạo **trong một trò chơi**, không phải "đo năng lực sáng tạo". Mỗi người chỉ có một đồ vật (gạch, chai nhựa hoặc ghế nhựa), nên các chỉ số chỉ so sánh được trong cùng một đồ vật.

## (a) Ý hợp lệ
Một ý được tính là hợp lệ khi qua đủ 4 bước sau, theo thứ tự:

1. **Không rỗng.** Sau khi chuẩn hóa mà không còn chữ nào (chỉ khoảng trắng hoặc dấu câu) thì loại, lý do `rong`.
2. **Không chỉ là tên đồ vật.** Mọi từ của ý đều nằm trong tên đồ vật thì loại, lý do `chi_ten_do_vat`. Ví dụ đồ vật "Viên gạch": "gạch", "viên gạch" bị loại; "dùng gạch làm bếp nướng" hợp lệ vì có từ khác.
3. **Tối thiểu 2 từ.** Ý một từ ("chặn") bị loại, lý do `qua_ngan`.
4. **Không trùng.** So sau khi chuẩn hóa, cả có dấu lẫn không dấu. Ý đầu tiên được giữ, các ý sau bị loại, lý do `trung`.

**Chuẩn hóa:** chuyển về Unicode NFC, hạ chữ thường, đổi dấu câu thành khoảng trắng, gộp khoảng trắng thừa. Để phát hiện trùng thì bỏ cả dấu tiếng Việt (đ thành d). Ví dụ "Làm chặn giấy", "lam chan giay" và "LÀM CHẶN GIẤY!!!" là một ý. Bản chữ gốc của ý vẫn được giữ để người chấm đọc.

**Ý bị dán.** Hệ thống chỉ đếm số lần dán của cả bài (`paste_count`), không biết ý nào bị dán. Nếu `paste_count` lớn hơn 0 thì gắn cờ `co_dan` cho cả bài. Không loại ý nào chỉ vì cờ này; khi phân tích, báo cáo kết quả cả khi có và không loại các bài có cờ.

**Giới hạn của bước tự động.** Quy tắc chỉ bắt lỗi hình thức. Ý vô nghĩa nhưng đủ 2 từ ("asdf qwer") vẫn qua; ý có nghĩa nhưng khác chữ ("kê chân bàn" và "đệm chân bàn") không bị coi là trùng. Phần ngữ nghĩa xử lý ở (c) và (d). Ghi vào hạn chế của đề tài.

## (b) Số ý hợp lệ (fluency)
Fluency = số ý hợp lệ của bài. Lưu thêm `so_y` (số ý đã nộp sau khi làm sạch) để so. Bài không có ý nào hợp lệ có fluency = 0, vẫn giữ trong dữ liệu.

## (c) Đa dạng (flexibility), chấm ở bước phân tích
Flexibility = số **nhóm công dụng** khác nhau trong các ý hợp lệ của một bài. Gán nhóm cho từng ý hợp lệ, mỗi ý đúng một nhóm:

| Nhóm | Ví dụ với viên gạch |
|---|---|
| Xây dựng | Xây bếp, lót đường |
| Trang trí | Làm chặn sách để trang trí, xếp thành bồn hoa |
| Đồ dùng gia đình | Kê nồi, chặn cửa |
| Thể thao và trò chơi | Làm cột gôn, xếp hình trò chơi |
| Nghệ thuật | Nghiền làm bột màu vẽ, tạc tượng |
| Công cụ | Đập vỡ vật cứng, làm búa |
| Đựng và chứa | Khoét làm chậu cây nhỏ |
| Khác | Ý không xếp được vào nhóm nào ở trên |

Nhóm "Khác" tính là một nhóm. Người gán nhóm là AI, rồi 2 người chấm kiểm tra lại một mẫu (xem `docs/plan.md`). Bảng nhóm có thể điều chỉnh sau khi đọc thử khoảng 30 bài, nhưng phải chốt trước khi gán toàn bộ và ghi lại bản cuối.

## (d) Độc đáo (originality), tính ở bước phân tích
Chỉ tính trong **cùng một đồ vật**, sau khi đã gom các ý tương tự thành cùng một "nhóm ý" (khác với nhóm công dụng ở (c); ví dụ "kê chân bàn" và "đệm chân bàn" là một nhóm ý). Một ý là **độc đáo** khi nhóm ý của nó xuất hiện ở **dưới 5%** số người chơi cùng đồ vật. Điểm độc đáo của bài = số ý độc đáo (có thể chia cho fluency để lấy tỉ lệ, báo cả hai). Mỗi đồ vật có khoảng 100 người nên ngưỡng 5% tương ứng dưới khoảng 5 người. Đếm theo số **người** có ý đó, không đếm số lần ý xuất hiện. Cách gom nhóm ý và ngưỡng phải ghi vào báo cáo; có thể thử 3% và 10% để xem độ nhạy.

## (e) Game gặp lỗi hoặc hết giờ
- Vẫn tính các ý đã nộp. Không bỏ bài.
- Hết giờ: server gắn `over_time` (nộp trễ quá 15 giây so với giới hạn), chấm như bình thường và giữ cờ.
- Game lỗi giữa chừng mà không có ý nào được lưu: fluency = 0 và đánh dấu bài thiếu, không đoán điểm.
- Khi phân tích, báo kết quả cả khi giữ và khi loại các bài có cờ `over_time` hoặc `co_dan`.
