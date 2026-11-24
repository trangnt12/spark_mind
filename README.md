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

## Thêm một bảng vào trang dữ liệu quản trị

Chỉ cần thêm **một mục** vào `BANG` trong `src/sparkmind/admin_registry.py` (không viết route, không sửa giao diện):

```python
"ten_collection": {
    "nhom": "huong2",                 # menu: huong1 | huong2 | cau_hinh | he_thong
    "ten": "Tên hiển thị",
    "che_do": "readonly",             # readonly = chỉ xem; crud = thêm/sửa/xóa (phải có thêm khóa "ghi")
    "co_nhan": True,                  # bảng có trường data_label (thu | pilot | that)?
    "cot": [("truong", "Nhãn cột", "text")],   # kiểu: text int float bool datetime id email hash nhan bi_mat
    "chi_tiet": {},                   # nhãn tiếng Việt thêm cho trang chi tiết
    "tim": ["truong"],                # trường tìm kiếm chữ
    "loc": [("truong", "Nhãn", "text", None)], # bộ lọc: enum | text | bool | int
    "sap_xep": ["truong"], "mac_dinh": ("truong", -1),
    "quyen": {"doc": XEM, "xuat": XEM, "ghi": KHONG, "xoa": ADMIN},
},
```

Rồi chạy `python -m pytest tests -q`: test kiểm tra registry và route (bảng readonly không được có PATCH, mọi route phải có kiểm tra quyền).
Dữ liệu nghiên cứu luôn để `readonly`; xóa chỉ cho admin và gõ lại ID.

## Gán nhãn dữ liệu thử / thật

```bash
python scripts/make_codes.py --n 5 --source volunteer --data-label thu   # mã dùng thử (mặc định là that)
python scripts/make_codes.py --n 300 --source hired_team --batch nhom_thue_1   # mã hàng loạt theo lô (CSV ở outputs/)
python scripts/compute_flags.py --dry-run   # tính lại cờ chống gian lận sau khi đổi ngưỡng (bỏ --dry-run để ghi)
python scripts/migrate_data_label.py            # chỉ xem (dry-run): số bản ghi cũ sẽ được gán nhãn
python scripts/migrate_data_label.py --apply    # ghi thật (phải gõ GAN NHAN); chạy lại nhiều lần vẫn an toàn
```

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

## Triển khai Render

Dùng gói miễn phí (512MB RAM), nên chỉ cài thư viện server cần (`requirements-server.txt`, không có jupyter/shap/matplotlib/scikit-learn).

| Mục | Giá trị |
|---|---|
| Build Command | `pip install -r requirements-server.txt` |
| Start Command | `uvicorn server.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"` |

Biến môi trường (đặt ở tab Environment của Render, **không** commit):

| Biến | Ý nghĩa |
|---|---|
| `MONGODB_URI` | Chuỗi kết nối MongoDB Atlas |
| `MONGODB_DB` | Tên database (`spark-mind`, có gạch ngang) |
| `INGEST_SECRET` | Khóa bí mật Apps Script gửi kèm (header `X-API-Key`) |
| `PYTHON_VERSION` | `3.12.10` |

Kiểm tra sau khi deploy: mở `https://<tên-app>.onrender.com/health`, kết quả đúng là `{"status":"ok"}`. Gói miễn phí ngủ sau ~15 phút không có truy cập; cron-job.org ping `/health` để giữ server thức.
