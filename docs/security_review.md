# Rà soát bảo mật SparkMind (phiên 4b, 26/11/2026)

Phạm vi: toàn bộ `server/`, `web/`, `scripts/`, `src/sparkmind/` (phần bảo mật), cấu hình triển khai Render và Atlas, phụ thuộc Python. Rà soát bằng đọc mã, chạy thử trên DB giả (mongomock) và một lần kiểm tra chỉ đọc trên Atlas thật (chỉ đọc tên vai trò của tài khoản kết nối, không in khóa).
Cách tái lập: `python -m pytest tests -q` (có `tests/test_health_security.py` cho phần mới và `tests/test_admin_auth.py` cho test quét route).

Mức độ: **Cao** (có thể bị khai thác ngay, hậu quả lớn) · **Trung bình** · **Thấp** · **Thông tin** (không phải lỗi, cần biết).
Trạng thái: ✅ đã đạt · 🔧 đã sửa trong phiên này · ❓ cần Trang quyết định · ⚠ rủi ro đã chấp nhận.

## Tóm tắt các phát hiện

| # | Mức | Phát hiện | Trạng thái |
|---|---|---|---|
| S-01 | **Cao** (có điều kiện) | Giả `X-Forwarded-For` qua mặt khóa đăng nhập và mọi giới hạn tốc độ | ❓ cần quyết định |
| S-02 | Trung bình | Tài khoản Atlas dùng cho server có vai trò `atlasAdmin` (quá quyền) | ❓ Trang làm trên Atlas |
| S-03 | Trung bình | Trang công khai thiếu tiêu đề bảo mật (nosniff, khung, referrer, CSP, HSTS) | 🔧 đã sửa |
| S-04 | Trung bình | Không giới hạn kích thước body (trừ hướng 1): gửi body khổng lồ làm tràn RAM 512 MB | 🔧 đã sửa |
| S-05 | Trung bình | Bộ đếm tốc độ trong RAM phình mãi khi gặp rất nhiều IP khác nhau (kể cả IP giả) | 🔧 đã sửa |
| S-06 | Thấp | `/docs`, `/redoc`, `/openapi.json` công khai, liệt kê cả route quản trị | 🔧 đã sửa |
| S-07 | Thấp | Khóa `x-api-key` có ký tự ngoài ASCII làm `compare_digest` văng lỗi 500 | 🔧 đã sửa |
| S-08 | Thấp | `requirements-server.txt` không ghim phiên bản (trừ xgboost) | ❓ |
| S-09 | Thấp | Đăng nhập quản trị không có giới hạn theo IP riêng; mỗi lần thử tốn CPU (scrypt) | ❓ (liên quan S-01) |
| S-10 | Thấp | `participants.session_token` lưu dạng thô (không băm); lộ bản sao lưu thì chiếm được phiên người chơi | ❓ |
| S-11 | Thấp | Chuỗi tìm kiếm của admin (`?q=`) nằm trong URL, vào nhật ký truy cập của Render (có thể có email) | ⚠ + dặn dò |
| S-12 | Thấp | scrypt `n=2^14` thấp hơn khuyến nghị mới (OWASP: 2^17) | ⚠ |
| S-13 | Thông tin | Cờ `Secure` của cookie dựa vào `X-Forwarded-Proto` của Render | ❓ Trang kiểm tra 1 lần |
| S-14 | Thông tin | CSP mới chưa được thử trong trình duyệt thật | ❓ Trang mở thử 1 lần |
| S-15 | Thông tin | `.env.example` thiếu `INGEST_SECRET` | 🔧 đã sửa |

Không tìm thấy: lỗi XSS, NoSQL injection, đọc dữ liệu người khác qua id, bí mật trong git, thư viện có lỗ hổng đã biết.

---

## Kết quả từng mục

### 1. Xác thực và phiên — ✅ (kèm S-13)
- Cookie `sm_admin`: `HttpOnly`, `SameSite=Strict`, `Secure` khi HTTPS, `path=/`, `max_age` 12 giờ (`server/auth.py`, test `test_dang_nhap_dat_cookie_an_toan...`, `test_cookie_secure_khi_https`).
- Token phiên ngẫu nhiên 256 bit (`secrets.token_urlsafe(32)`), DB chỉ lưu băm SHA-256; TTL index tự xóa; code tự kiểm tra hạn (2 giờ không hoạt động, tối đa 12 giờ). Đăng nhập luôn cấp token mới (không có session fixation). Đổi hoặc đặt lại mật khẩu, khóa tài khoản: xóa mọi phiên của người đó.
- CSRF: ba lớp. Mọi POST/PUT/PATCH/DELETE cần (1) `Origin` trùng `Host`, (2) header `X-CSRF-Token` khớp phiên (so bằng `hmac.compare_digest`), (3) cookie `SameSite=Strict`. Đăng nhập cũng kiểm `Origin`. Các route công khai của người chơi không dùng cookie (token nằm trong header hoặc body), nên CSRF không áp dụng.
- Mật khẩu: tối thiểu 12 ký tự, scrypt có muối riêng, tham số nằm trong chuỗi băm. Người dùng không tồn tại vẫn chạy scrypt (thời gian trả lời như nhau); lỗi đăng nhập luôn là một thông báo chung.
- **S-13 (Thông tin):** `Secure` được bật khi `request.url.scheme == "https"`, mà scheme lấy từ `X-Forwarded-Proto` do uvicorn `--proxy-headers`. Chưa kiểm trên Render thật. Cách kiểm: đăng nhập trang quản trị trên địa chỉ Render, mở DevTools (F12) > Application > Cookies, cột Secure của `sm_admin` phải có dấu ✓.

### 2. Khóa dò mật khẩu — ✅ về logic, ❓ về S-01
- 5 lần sai trong 15 phút theo cặp (tên + IP) thì khóa 15 phút (429); đếm cả với tên không tồn tại; khóa đếm là băm, không lưu IP thô; đổi mật khẩu cũng tính vào giới hạn.
- **S-01 (Cao, có điều kiện).** Server chạy với `--forwarded-allow-ips="*"`. Đã đọc mã uvicorn 0.54.0 (`ProxyHeadersMiddleware`): khi tin mọi proxy, nó lấy phần tử **đầu tiên** của `X-Forwarded-For` làm IP khách. Phần tử đầu do chính người gửi viết ra được (proxy chỉ nối thêm vào cuối). Kiểm tra bằng thử nghiệm tại chỗ (bọc app bằng đúng middleware đó, `trusted_hosts="*"`): 12 lần đăng nhập sai liên tiếp, mỗi lần một `X-Forwarded-For` khác, đều trả 401, **không bao giờ bị khóa**; không giả header thì lần thứ 5 bị khóa như thiết kế. Hệ quả: (a) kẻ tấn công thử mật khẩu quản trị không giới hạn; (b) mọi giới hạn tốc độ theo IP (nhập mã, demo, hướng 1) cũng bị qua mặt; (c) `ip_hash` không đáng tin. `docs/decisions.md` đã ghi (b) và (c) là rủi ro chấp nhận (chỉ để gắn cờ), nhưng **(a) chưa được ghi nhận**, và (a) mới là chỗ nguy hiểm vì liên quan quyền admin.
  - Điều kiện: chỉ đúng nếu proxy của Render để nguyên `X-Forwarded-For` do khách gửi (cách làm chuẩn là nối thêm). Cách kiểm trên Render: gửi 12 lần `curl -s -o /dev/null -w "%{http_code}\n" -X POST https://<địa-chỉ-render>/api/research/code/check -H "Content-Type: application/json" -H "X-Forwarded-For: 9.9.9.$i" -d '{"code":"SAISAI"}'` với `$i` khác nhau; nếu không lần nào ra 429 thì giả được.
  - Giảm nhẹ hiện có: mật khẩu tối thiểu 12 ký tự; mỗi lần thử tốn khoảng 40 ms CPU trên máy dev (scrypt, đã đo; trên Render miễn phí chậm hơn) nên tốc độ thử bị giới hạn ở vài chục lần mỗi giây; mọi đăng nhập đều vào `audit_log`.
  - **Cần Trang chọn** (xem mục "Việc cần Trang quyết định").

### 3. Quyền theo vai trò và theo dữ liệu — ✅
- Từ chối mặc định: `tests/test_admin_auth.py` duyệt mọi route `/api/admin/*` và `/api/rate/*` (cả router gộp lười) và FAIL nếu route nào thiếu `require_role` hoặc khóa ingest. Route mới `/api/admin/health` đã qua bộ quét. Có test chứng minh bộ quét bắt được route thiếu.
- Ma trận quyền (đã có test): admin toàn quyền; viewer chỉ đọc (không xuất CSV chấm điểm, không thấy `participant_id`, không xem `audit_log`); rater chỉ vào `/api/rate/*` (403 ở mọi route quản trị); admin và viewer 403 ở `/api/rate/*`. User đang bị buộc đổi mật khẩu bị chặn ở mọi route quản trị.
- Người chấm không đọc được dữ liệu người khác: `_muc_cua_nguoi_cham` trả cùng một lỗi 404 cho mục không tồn tại và mục không được giao (không đoán được qua mã); điểm luôn lọc theo `rater` = tên đăng nhập của chính mình; nội dung trả ra qua danh sách trắng (không `participant_id`, email, cờ, nhãn, điểm người kia). Test: `test_hai_nguoi_cham_khong_thay_diem_cua_nhau`, `test_muc_khong_giao_hoac_khong_ton_tai_cung_mot_loi_404`, `test_noi_dung_muc_chi_co_truong_cho_phep_khong_ro_ri`.
- Người chơi: không có route nào nhận id người khác. Danh tính **chỉ** lấy từ token phiên (256 bit). Test mới `test_route_nguoi_choi_khong_nhan_id_nguoi_khac_tu_client` quét mọi route `/api/research/*` và FAIL nếu có tham số đường dẫn hay truy vấn kiểu id/participant. Đáp án game 2 và kết quả chỉ ra sau `completed_at` (409 trước đó).
- Truy cập trực tiếp qua id ở trang dữ liệu: route chỉ được tạo cho bảng khai báo trong registry; `survey_form1` không có DELETE/POST/PATCH (405); bảng `users`, `admin_sessions`, `login_attempts` không có route dữ liệu.
- Chống NoSQL injection: tham số lọc chỉ nhận khóa khai báo trong registry và ép kiểu; tìm kiếm dùng `re.escape`; tạo/sửa chỉ nhận trường khai báo (`kiem_tra_truong`), mỗi giá trị phải là chuỗi/bool, tối đa 200 ký tự; id từ URL luôn là chuỗi (không thể là `{"$ne": ...}`).

### 4. Giới hạn tốc độ mọi route công khai — ⚠ một phần (xem S-01, S-09)
| Route công khai | Giới hạn | Ghi chú |
|---|---|---|
| `POST /api/research/code/check` | 10 lần SAI/phút/IP | mã 8 ký tự trên 32 ký tự = 2^40 khả năng, dò mù không khả thi |
| `POST /api/predict/demo` | 30 lần/phút/IP | không ghi DB |
| `POST /api/huong1/submit` | 40 bài/10 phút/IP đã băm | thêm trường bẫy bot, body tối đa 20 KB |
| `POST /api/auth/login` | khóa 5 sai/15 phút theo (tên+IP) | không có giới hạn theo IP riêng (S-09) |
| `/api/research/*` còn lại | không có | cần token 256 bit hoặc mã hợp lệ (dùng một lần); ghi vào DB bị chặn bởi chỉ mục unique |
| `POST /api/ingest/google-form`, `/api/admin/memory` | khóa `x-api-key` | |
| GET nội dung (`/api/content/*`, `/api/status`, `/health`, trang tĩnh) | không có | chỉ đọc, rẻ; chấp nhận. `/api/status` nhớ 10 giây nên không đè Atlas |
| `/api/rate/*`, `/api/admin/rating/*` nặng | theo tài khoản (240/60 đọc-ghi, 20 nặng mỗi phút) | |

Tất cả giới hạn theo IP đều bị S-01 qua mặt. **S-05 (đã sửa):** `GioiHanTocDo` trước đây tạo một hàng đợi cho mỗi khóa và không bao giờ xóa, nên bị gửi bằng vài trăm nghìn IP giả sẽ ăn hết RAM (Render 512 MB). Nay hàm chỉ-đọc không tạo khóa và khóa hết hạn được dọn mỗi cửa sổ thời gian (test `test_gioi_han_toc_do_khong_phinh_bo_nho...`).

### 5. Kiểm tra đầu vào và kích thước payload — ✅ sau khi sửa S-04
- Mọi body đều qua pydantic với giới hạn độ dài/khoảng giá trị (câu trả lời form, tên trường 200 ký tự, mỗi ý game 1 ≤ 120 ký tự và ≤ 500 ý, game 3 ≤ 800 ký tự/ô, ghi chú người chấm ≤ 1000, mật khẩu ≤ 256...). Mã lựa chọn phải có trong `content/form_b.json`. Hướng 1 dùng `extra="forbid"`.
- **S-04 (đã sửa):** trước đây chỉ hướng 1 kiểm `Content-Length`; mọi route khác đọc trọn body (uvicorn không giới hạn) rồi mới kiểm tra, nên một body vài trăm MB làm tràn RAM. Nay `server/gioi_han_body.py` (middleware ASGI) từ chối mọi yêu cầu ghi lớn hơn `config.BODY_TOI_DA_BYTE` = 256 KB với 413 trước khi đọc; body gửi kiểu chunked được đếm khi đọc và bị chặn (FastAPI báo 400). Bài lớn nhất thật chỉ vài chục KB nên không ảnh hưởng người dùng. Test: `test_body_qua_lon_bi_tu_choi_413`, `test_body_chunked_vuot_gioi_han_cung_bi_chan`.
- Lỗi 422 mặc định của FastAPI có phản chiếu lại giá trị người gọi vừa gửi (`input`). Chỉ trả về chính người gửi, không lộ dữ liệu người khác; demo đã có bộ xử lý riêng không phản chiếu.

### 6. Chống XSS khi hiển thị nội dung người chơi nhập — ✅
- Giao diện quản trị, người chấm và trang xem lại dựng DOM bằng `textContent`/`createTextNode` (hàm `SM.h`, `h()` của `app.js`). Test mới `test_giao_dien_khong_chen_html_tu_du_lieu` quét mọi JS: cấm `innerHTML =`, `outerHTML =`, `document.write`, `eval(`, `new Function(`; `insertAdjacentHTML` chỉ còn một chỗ (`game1.js`, vẽ vòng đồng hồ bằng chuỗi cố định, test kiểm không ghép biến).
- Trang chủ và `/huong-1`: chữ chèn vào thẻ `<title>`, `<meta>` đều qua `html.escape(quote=True)` (test `test_trang_chu_thoat_ky_tu_dac_biet_trong_the_meta`). Nội dung đó lấy từ file `content/` do Trang quản lý, không phải do người chơi.
- API trả JSON (`application/json`) kèm `X-Content-Type-Options: nosniff` nên nội dung có thẻ `<script>` không bị trình duyệt đoán thành HTML (test `test_noi_dung_nguoi_choi_tra_ve_dang_json...`). CSV có chống công thức Excel (ô bắt đầu `= + - @`).
- Lớp thứ hai: CSP (mục 7). Quản trị: `script-src 'self'` (không `unsafe-inline` ở script lẫn style). Công khai: `script-src 'self'` cộng đúng một mã băm cho script nhúng của `survey1.html`.

### 7. Tiêu đề bảo mật và CORS — 🔧 đã sửa (S-03), ❓ S-14
- Trước phiên này: chỉ đường quản trị có `X-Frame-Options`, `Referrer-Policy`, CSP; trang công khai không có tiêu đề nào. Nay `server/headers.py` gắn cho MỌI phản hồi: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` (quản trị: `no-referrer`), `Permissions-Policy` tắt camera/mic/vị trí, CSP, và `Strict-Transport-Security` (180 ngày) khi request đến qua HTTPS.
- CSP công khai: `default-src 'self'; script-src 'self' 'sha256-…'; style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`. `style-src 'unsafe-inline'` là cần thiết vì giao diện có thuộc tính `style` (rủi ro thấp: không cho chạy script). Test `test_csp_cong_khai_khop_voi_trang_web_thuc_te` giữ CSP khớp với HTML thật (mọi script nhúng phải có mã băm trong CSP, không có `onclick=...`, không nạp tài nguyên từ nơi lạ ngoài Google Fonts) nên ai sửa HTML làm hỏng CSP sẽ bị test báo.
- **S-14:** vì chưa thử trong trình duyệt thật, sau khi deploy Trang mở thử 5 trang (`/`, `/huong-1`, `/play/`, `/play/#demo`, `/admin/`), bấm F12 > Console: không được có dòng đỏ "Refused to load/execute ... Content Security Policy". Nếu có, gửi dòng đó cho Claude.
- CORS: không bật `CORSMiddleware`, nên trình duyệt chặn mọi trang khác gọi API (chỉ cùng nguồn). Đúng ý, không cần mở. Apps Script gọi từ máy chủ Google (không phải trình duyệt) nên không cần CORS.

### 8. Bí mật trong mã, nhật ký, git — ✅
- `.env`, `backups/`, `outputs/*.csv` (kể cả `codes_*.csv`), `data/raw/*`, `data/processed/*` đều trong `.gitignore`; `git ls-files` không có file nào trong số đó; không thấy `.env`, `backups/`, mã tham gia nào từng được thêm vào lịch sử git. Chỉ có một commit từng chứa chuỗi `mongodb+srv://` (`73dab27`) và đó chỉ là mẫu `TEN_USER:MAT_KHAU` trong `.env.example` (đã đếm: không có dòng nào khác).
- Mã không in chuỗi kết nối hay khóa: lỗi khởi động chỉ ghi `type(loi).__name__`; trang Sức khỏe chỉ báo "đã đặt / chưa đặt" và có test cố tình đặt khóa giả rồi kiểm không xuất hiện trong phản hồi. `audit_log` tự bỏ khóa chứa password/hash/token/secret/csrf.
- `ip_hash` là HMAC bằng `IP_HASH_SECRET`, IP thô không được lưu. Token phiên quản trị chỉ lưu băm.
- Lưu ý: `CLAUDE.md` và `note_private.md` nằm trong `.gitignore`, nên không lên GitHub (đúng ý nếu ghi chú riêng).
- **S-10 (Thấp):** `participants.session_token` của người chơi lưu thô, nên bản sao lưu (`backups/`, đã ngoài git) hoặc ai mở được Compass đều dùng được token để đọc bài của người chơi đó. Mức độ thấp (cần đã vào được DB, khi đó đã thấy email thẳng). Muốn khắc phục: băm token + chuyển dữ liệu; ảnh hưởng người đang làm dở nên chỉ làm khi Trang đồng ý.
- **S-11 (Thấp):** tìm kiếm ở trang dữ liệu gửi `?q=` trên URL nên nhật ký truy cập của Render có thể chứa chữ admin gõ (kể cả email). Dặn: không gõ email đầy đủ vào ô tìm; nhật ký Render chỉ admin dự án xem được.

### 9. Lỗi không lộ thông tin nội bộ — ✅
- Mọi lỗi nghiệp vụ trả mã ngắn hoặc câu tiếng Việt chung; lỗi hệ thống để FastAPI trả "Internal Server Error" trơn (không stack trace). Lỗi kết nối chỉ ghi tên loại lỗi.
- `/api/ingest/google-form` trả `str(ValueError)` của `nhan_form` (ví dụ "Câu A4 phải là số 1-5, nhận được: ..."): chỉ phản chiếu lại đúng giá trị khóa-chủ gửi, không lộ gì nội bộ.
- **S-06 (đã sửa):** `/docs`, `/redoc`, `/openapi.json` công khai liệt kê toàn bộ route kể cả `/api/admin/*`. Nay tắt mặc định, chỉ bật khi đặt `BAT_TAI_LIEU_API=1` trên máy dev (đã ghi vào `.env.example`). Chạy thử trên máy muốn xem `/docs`: thêm `BAT_TAI_LIEU_API=1` vào `.env`.
- **S-07 (đã sửa):** `hmac.compare_digest(str, str)` văng TypeError (500) nếu header `x-api-key` có ký tự ngoài ASCII; nay so sánh dạng byte, trả 401 (test `test_khoa_ingest_khong_phai_ascii...`). Không lộ gì, chỉ là lỗi sạch hơn.

### 10. Phụ thuộc có lỗ hổng đã biết — ✅ (kèm S-08)
- `pip-audit` (cài trong môi trường tạm, chạy trên toàn bộ 136 gói của môi trường dev, kiểm với cơ sở dữ liệu lỗ hổng ngày 26/11/2026): **"No known vulnerabilities found"**. Lệnh tái lập: `pip freeze > freeze.txt && pip-audit -r freeze.txt --no-deps --disable-pip`.
- Phiên bản server đang dùng: fastapi 0.165.0, starlette 1.10.0, uvicorn 0.54.0, pydantic 2.14.4, pymongo 4.20.0, pandas 3.1.1, numpy 2.5.5, python-dotenv 1.2.4, xgboost(-cpu) 3.4.1.
- **S-08 (Thấp):** `requirements-server.txt` chỉ ghim `xgboost-cpu==3.4.1`; các gói khác lấy bản mới nhất mỗi lần Render build. Rủi ro: một lần deploy kéo bản mới gây lỗi bất ngờ giữa đợt thu 1–20/12. Đề xuất: ghim đúng các bản trên (kiểm Render có đủ các bản này cho phiên bản Python của Render), đóng băng trước 1/12; chưa làm vì cần thử build trên Render.

### 11. Quyền Atlas và IP cho phép — ❓ (S-02)
- **S-02 (Trung bình).** Kiểm tra chỉ đọc: tài khoản trong chuỗi kết nối đang có vai trò **`atlasAdmin`** (toàn quyền trên mọi database và quản trị cụm). Nếu chuỗi kết nối trên Render bị lộ (ví dụ vào nhầm log, ảnh chụp màn hình), kẻ xấu xóa được cả database. Ba quy tắc "không drop database" trong `CLAUDE.md` chỉ ràng buộc mã của dự án, không ràng buộc quyền của tài khoản.
  - Cách sửa (Trang làm trên Atlas > Database Access): tạo tài khoản riêng cho server Render với **"Specific Privileges": `readWrite` trên database `spark-mind`** (không phải atlasAdmin). Trang Sức khỏe, sao lưu và mọi chức năng web vẫn chạy với quyền này. Dùng tài khoản thứ hai (hoặc tài khoản hiện tại) chỉ cho script trên máy cá nhân (khôi phục vào database mới cần `readWrite` trên database đích; có thể gán `readWrite` cho `spark-mind` và cho các database tên `spark-mind-test*`... hoặc để Trang dùng tài khoản cũ khi khôi phục). Sau khi đổi, sửa `MONGODB_URI` trên Render và `.env`.
- IP cho phép (Atlas > Network Access): không kiểm tra được từ mã. Render gói miễn phí không có IP cố định nên thường phải để `0.0.0.0/0` (cho mọi nơi). Khi đó lớp bảo vệ chính là mật khẩu tài khoản Atlas: dài, ngẫu nhiên, không dùng ở nơi khác. Nên: (a) xóa các dòng IP thử cũ không còn dùng; (b) bật xác thực hai lớp cho tài khoản đăng nhập Atlas và Render của Trang; (c) kết nối luôn dùng `mongodb+srv` (TLS mặc định).
- Sao lưu: `scripts/backup_mongo.py` chỉ đọc; `restore_mongo.py` chỉ vào database mới và chặn `spark-mind`; không có lệnh drop ở đâu (có test).

### 12. Rủi ro đã chấp nhận
- **IP giả mạo trên Render (S-01 phần b, c):** giới hạn tốc độ nhập mã, demo, hướng 1 và `ip_hash` chỉ để gắn cờ, không phải rào chắn chắc chắn (đã ghi ở `docs/decisions.md`). Riêng khóa đăng nhập quản trị cần xử lý riêng (S-01 phần a).
- **Thời gian đo ở phía trình duyệt:** `thoi_gian_cau`, `an_tab_ms`, đếm dán/rời tab do trình duyệt gửi, có thể bị giả; chỉ dùng để gắn cờ, không dùng để loại bài hay chấm điểm (đã ghi ở mục Cờ chống gian lận).
- **Bộ đếm tốc độ trong RAM từng tiến trình:** mất khi khởi động lại, không chia sẻ giữa nhiều tiến trình. Hiện chạy một tiến trình nên chấp nhận được.
- **Một người làm hướng 1 nhiều lần:** không phát hiện được (không email, không mã).
- **scrypt `n=2^14` (S-12):** nhẹ hơn khuyến nghị mới để vừa RAM của Render miễn phí; bù bằng mật khẩu ≥ 12 ký tự và khóa đăng nhập. Tham số nằm trong chuỗi băm nên nâng được sau mà không làm hỏng mật khẩu cũ.
- **`style-src 'unsafe-inline'` ở trang công khai:** xem mục 7.

---

## Việc cần Trang quyết định

1. **S-01 (ưu tiên cao nhất, trước 1/12).** Chống thử mật khẩu admin khi IP giả được. Các cách, từ đơn giản đến tốn công:
   - **A (khuyến nghị, nhỏ):** thêm bộ đếm thứ hai theo **tên tài khoản** (không theo IP): quá 20 lần sai trong 15 phút từ mọi IP thì mọi lần đăng nhập vào tài khoản đó bị chậm/khóa 15 phút. Nhược điểm: kẻ xấu có thể cố tình làm admin bị khóa tạm (nhưng không vào được). Vì chỉ có vài tài khoản, đây là đánh đổi chấp nhận được; cần thêm cách mở khóa bằng script cho admin cuối cùng.
   - **B:** đọc IP khách từ header riêng của Render (nếu Render đảm bảo header đó không giả được) thay cho `X-Forwarded-For`. Cần xác minh tài liệu và thử trên Render trước khi làm.
   - **C (lớn):** thêm xác thực hai lớp (TOTP) cho admin. Mạnh nhất, nhưng thêm nhiều việc; không kịp trước 1/12 nếu không cần thiết.
   - Cho tới khi chọn: dùng mật khẩu admin dài (từ 16 ký tự, ngẫu nhiên), và trang Quản trị chỉ cần đưa cho ít người.
2. **S-02:** tạo tài khoản Atlas riêng cho Render với quyền `readWrite` trên `spark-mind` (mục 11). Việc của Trang trên Atlas, khoảng 10 phút, nên làm trước 29/11 (pilot) để thử luôn.
3. **S-08:** ghim phiên bản `requirements-server.txt` (mục 10).
4. **S-10:** có băm `session_token` của người chơi không (mục 8). Đề xuất: không làm trước khi thu xong.
5. **S-13, S-14:** hai việc kiểm tra 5 phút sau khi deploy (mục 1 và mục 7).

## Việc Claude đã sửa trong phiên này (không đổi hành vi chức năng)
`server/headers.py` (tiêu đề bảo mật toàn site), `server/gioi_han_body.py` (giới hạn body 256 KB), `src/sparkmind/security.py` (bộ đếm không phình RAM), `server/main.py` (tắt `/docs`, so khóa bằng byte), `.env.example`; test ở `tests/test_health_security.py`.
