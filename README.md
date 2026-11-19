# SparkMind

Dự đoán năng lực tư duy sáng tạo (tự nhận thức) của học sinh, sinh viên Việt Nam từ hành vi dùng LLM, bằng Random Forest, XGBoost và SHAP. Một web phục vụ hai chế độ: hướng 1 (form tự chấm) và hướng 2 (form B, 3 trò chơi, AI và người chấm).

## Cấu trúc thư mục

| Thư mục | Để làm gì |
|---|---|
| `src/sparkmind/` | Code dùng chung: tên cột, làm sạch, kết nối MongoDB, đọc dữ liệu |
| `scripts/` | Lệnh chạy một lần hoặc theo lịch (nhập Excel, làm sạch, sao lưu...) |
| `notebooks/` | Notebook phân tích: 01 làm sạch, 02 mô tả, 03 mô hình, 04 SHAP, 05 xuất |
| `server/` | Web FastAPI. Hiện có `/health` và nhận form từ Google Form; còn lại làm từ 21/11 |
| `integrations/` | Code chạy ở dịch vụ khác (Google Apps Script) |
| `content/` | Nội dung đổi được: câu hỏi, đề game, lời khuyên (không nằm trong code) |
| `data/raw/` | File Excel gốc. **Không lên GitHub** |
| `data/processed/` | CSV đã làm sạch. **Không lên GitHub** |
| `models/` | File mô hình đã huấn luyện |
| `outputs/` | Bảng và hình xuất cho báo cáo |
| `tests/` | Kiểm tra tự động (chạy `python -m pytest tests -q`) |
| `docs/` | Tài liệu: luồng dữ liệu, ghi chú quyết định |

## Cài đặt lần đầu (Git Bash)

```bash
pip install -r requirements.txt
cp .env.example .env        # rồi mở .env, dán chuỗi kết nối MongoDB vào
mkdir -p data/raw           # đặt file Excel gốc vào data/raw/data_raw.xlsx
```

## Các lệnh hay dùng

```bash
python scripts/import_excel.py --dry-run     # thử: chỉ đếm form trong Excel
python scripts/import_excel.py               # đưa Excel vào MongoDB (an toàn khi chạy lại)
python scripts/run_cleaning.py               # làm sạch dữ liệu trong MongoDB
python scripts/run_cleaning.py --csv         # làm sạch và ghi thêm CSV
python scripts/run_cleaning.py --tu-excel    # thử không cần MongoDB
python scripts/import_schools.py --file <danh_sach_truong.xlsx>   # nạp danh sách trường
python scripts/export_school_review.py       # xuất bảng tên trường cần duyệt tay
uvicorn server.main:app --reload            # chạy thử server trên máy
python -m pytest tests -q                    # kiểm tra
```

Luồng dữ liệu đầy đủ xem `docs/data_flow.md`.
