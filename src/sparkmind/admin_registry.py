"""Registry các bảng cho trang dữ liệu quản trị: MỘT file cấu hình mô tả mọi collection hiển thị.

THÊM BẢNG MỚI = thêm một mục vào BANG (xem README, mục "Thêm một bảng vào trang quản trị"). Không cần viết route:
server/admin_data_api.py đọc registry này để tạo route, giao diện đọc meta từ GET /api/admin/data.

Mỗi mục:
  nhom      menu bên trái: huong1 | huong2 | cau_hinh | he_thong
  ten       tên hiển thị tiếng Việt
  che_do    "readonly" (không có POST/PATCH) | "crud" (có POST/PATCH/DELETE theo quyền)
  co_nhan   bảng có trường data_label (thu | pilot | that) => lọc được bằng công tắc "ẩn dữ liệu thử"
  cot       cột trong danh sách: (khóa, nhãn, kiểu). Kiểu: text int float bool datetime id email hash nhan bi_mat
  chi_tiet  nhãn tiếng Việt thêm cho các trường chỉ hiện ở trang chi tiết {khóa: nhãn}
  tim       các trường tìm kiếm chữ (không phân biệt hoa thường) - chỉ trường chữ
  loc       bộ lọc: (khóa, nhãn, kiểu, lựa chọn) với kiểu enum | text | bool | int
  sap_xep   các trường được phép sắp xếp; mac_dinh = (trường, 1 tăng | -1 giảm)
  quyen     {"doc": vai trò, "xuat": vai trò, "ghi": vai trò (POST/PATCH), "xoa": vai trò (DELETE từng bản ghi)}
  ghi_chu   (tùy chọn) dòng ghi chú hiện trên trang thay cho ghi chú mặc định
  bang_con  (tùy chọn) bảng con bị xóa theo khi xóa một bản ghi (xem participants)
  ghi       (chỉ bảng crud) trường được tạo/sửa: khóa -> {nhan, kieu: text|choice|bool, bat_buoc, lua_chon, sua}
"""
from . import config, flags

ADMIN = ("admin",)
XEM = ("admin", "viewer")
KHONG = ()
NHAN_LUA_CHON = list(config.NHAN_HOP_LE)
BAN_NGUON = ["google_form", "excel_import", "web"]
NGUON_THAM_GIA = ["volunteer", "hired_team"]
LUA_CHON_CO = flags.tat_ca_co_co_the()   # "mã:bước", ví dụ lam_qua_nhanh:form_b
CAP_TRUONG = ["THCS", "THPT", "Đại học", "Liên cấp"]


def _nhan_loc():
    return ("data_label", "Nhãn dữ liệu", "enum", NHAN_LUA_CHON)


BANG = {
    # ---------------- Hướng 1 ----------------
    "survey_clean": {
        "nhom": "huong1", "ten": "Form đã làm sạch", "che_do": "readonly", "co_nhan": True,
        "cot": [("thoi_gian", "Thời gian", "datetime"), ("nguon", "Nguồn", "text"), ("dot", "Đợt", "text"),
                ("cap_hoc", "Cấp học", "text"), ("truong_chuan", "Trường (chuẩn)", "text"),
                ("diem_sang_tao", "Điểm sáng tạo", "float"), ("muc", "Mức", "text"),
                ("in_chinh", "Bản rộng", "bool"), ("in_chat", "Bản chính", "bool"), ("in_rat_chat", "Bản rất chặt", "bool"),
                ("data_label", "Nhãn", "nhan")],
        "chi_tiet": {"A1": "Lớp", "A2": "Giới tính", "A3": "Trường (người dùng gõ)", "A4": "Có dùng AI", "diem_hanh_vi": "Điểm hành vi"},
        "tim": ["truong_chuan", "A3"],
        "loc": [("nguon", "Nguồn", "enum", BAN_NGUON), ("dot", "Đợt", "text", None), ("muc", "Mức", "enum", ["Thap", "Trung_binh", "Cao"]),
                ("cap_hoc", "Cấp học", "enum", ["THCS", "THPT", "Đại học"]), ("in_chinh", "Bản rộng", "bool", None),
                ("in_chat", "Bản chính", "bool", None), ("in_rat_chat", "Bản rất chặt", "bool", None), _nhan_loc()],
        "sap_xep": ["thoi_gian", "nguon", "dot", "diem_sang_tao", "muc"], "mac_dinh": ("thoi_gian", -1),
        "quyen": {"doc": XEM, "xuat": XEM, "ghi": KHONG, "xoa": ADMIN},
    },
    "survey_form1": {
        "nhom": "huong1", "ten": "Form dữ liệu gốc", "che_do": "readonly", "co_nhan": False,
        "cot": [("thoi_gian", "Thời gian", "datetime"), ("nguon", "Nguồn", "text"), ("A1", "Lớp", "text"),
                ("A2", "Giới tính", "text"), ("A4", "Có dùng AI", "text"), ("C1", "C1", "int"), ("C2", "C2", "int"),
                ("C3", "C3", "int"), ("C4", "C4", "int"), ("C5", "C5", "int")],
        "chi_tiet": {"A3": "Trường (người dùng gõ)"},
        "tim": ["A3"],
        "loc": [("nguon", "Nguồn", "enum", BAN_NGUON), ("A2", "Giới tính", "text", None)],
        "sap_xep": ["thoi_gian", "nguon"], "mac_dinh": ("thoi_gian", -1),
        "quyen": {"doc": XEM, "xuat": XEM, "ghi": KHONG, "xoa": KHONG},   # dữ liệu gốc: không bao giờ sửa hay xóa qua web
    },
    # ---------------- Hướng 2 ----------------
    "participants": {
        "nhom": "huong2", "ten": "Người tham gia", "che_do": "readonly", "co_nhan": True,
        "cot": [("started_at", "Bắt đầu", "datetime"), ("source", "Nguồn", "text"), ("data_label", "Nhãn", "nhan"),
                ("grade", "Lớp (mã)", "text"), ("gender", "Giới tính (mã)", "text"), ("school_name", "Trường", "text"),
                ("email", "Email", "email"), ("consent", "Đồng ý", "bool"), ("guardian_consent", "Phụ huynh đồng ý", "bool"),
                ("ip_hash", "IP (băm)", "hash"), ("completed_at", "Hoàn thành", "datetime"),
                ("flag_count", "Số cờ", "int"), ("flags", "Cờ chống gian lận", "ds")],
        "chi_tiet": {"code_id": "Mã tham gia (ID)", "consent_at": "Đồng ý lúc", "sua_luc": "Sửa thông tin lúc"},
        "tim": ["school_name"],
        "loc": [("source", "Nguồn", "enum", NGUON_THAM_GIA), ("consent", "Đồng ý", "bool", None),
                ("guardian_consent", "Phụ huynh đồng ý", "bool", None), ("flag_count", "Số cờ (không tính bi_gian_doan)", "int", None),
                ("flags", "Cờ", "enum", LUA_CHON_CO), _nhan_loc()],
        "sap_xep": ["started_at", "completed_at", "source", "school_name", "flag_count"], "mac_dinh": ("started_at", -1),
        "quyen": {"doc": XEM, "xuat": XEM, "ghi": KHONG, "xoa": ADMIN},
        # xóa một người thì xóa luôn dữ liệu của người đó ở các bảng này (scores đi qua game_responses)
        "bang_con": [{"bang": "behavior_answers", "truong": "participant_id"}, {"bang": "self_assessment", "truong": "participant_id"},
                     {"bang": "game_responses", "truong": "participant_id"},
                     {"bang": "scores", "truong": "response_id", "qua": "game_responses", "qua_truong": "participant_id"},
                     # mục chấm đã chép từ bài của người này và điểm của người chấm cho các mục đó (không nằm trong registry)
                     {"bang": "rating_items", "truong": "participant_id", "ngoai_registry": True},
                     {"bang": "ratings", "truong": "item_code", "qua": "rating_items", "qua_truong": "participant_id", "qua_lay": "item_code", "ngoai_registry": True}],
    },
    "behavior_answers": {
        "nhom": "huong2", "ten": "Form B (hành vi AI)", "che_do": "readonly", "co_nhan": True,
        "cot": [("participant_id", "Người tham gia (ID)", "id"), ("data_label", "Nhãn", "nhan"), ("a4", "A4", "text"),
                ("b1", "B1", "text"), ("b2_frequency", "B2", "text"), ("b3", "B3", "text")]
               + [(f"b4_{i}", f"B4.{i}", "int") for i in range(1, 8)]
               + [("b5_duration", "B5", "text"), ("b6_prompting", "B6", "text"), ("b7_after_answer", "B7", "text"),
                  ("duration_sec", "Thời gian (giây)", "int"), ("so_lan_sua", "Số lần sửa", "int")],
        "chi_tiet": {"b1_other": "B1 mục khác", "b3_other": "B3 mục khác", "b6_other": "B6 mục khác", "sua_luc": "Sửa lúc"},
        "tim": [],
        "loc": [("a4", "A4", "text", None), _nhan_loc()],
        "sap_xep": ["duration_sec", "so_lan_sua"], "mac_dinh": ("_id", -1),
        "quyen": {"doc": XEM, "xuat": XEM, "ghi": KHONG, "xoa": ADMIN},
    },
    "self_assessment": {
        "nhom": "huong2", "ten": "Tự đánh giá (C1–C5)", "che_do": "readonly", "co_nhan": True,
        "cot": [("participant_id", "Người tham gia (ID)", "id"), ("data_label", "Nhãn", "nhan")]
               + [(f"c{i}", f"C{i}", "int") for i in range(1, 6)]
               + [("c6", "C6", "text"), ("creativity_score", "Điểm sáng tạo", "float"), ("so_lan_sua", "Số lần sửa", "int")],
        "chi_tiet": {"sua_luc": "Sửa lúc"},
        "tim": [],
        "loc": [_nhan_loc()],
        "sap_xep": ["creativity_score", "so_lan_sua"], "mac_dinh": ("_id", -1),
        "quyen": {"doc": XEM, "xuat": XEM, "ghi": KHONG, "xoa": ADMIN},
    },
    "game_responses": {
        "nhom": "huong2", "ten": "Kết quả game", "che_do": "readonly", "co_nhan": True,
        "cot": [("participant_id", "Người tham gia (ID)", "id"), ("data_label", "Nhãn", "nhan"), ("game", "Game", "int"),
                ("prompt_id", "Đề", "text"), ("duration_sec", "Thời gian (giây)", "int"), ("answer_length", "Độ dài", "int"),
                ("paste_count", "Số lần dán", "int"), ("tab_leave_count", "Số lần rời tab", "int"),
                ("over_time", "Nộp trễ", "bool"), ("started_at", "Bắt đầu", "datetime"), ("submitted_at", "Nộp lúc", "datetime")],
        "chi_tiet": {"answer": "Câu trả lời"},
        "tim": ["prompt_id"],
        "loc": [("game", "Game", "int", None), ("over_time", "Nộp trễ", "bool", None), _nhan_loc()],
        "sap_xep": ["started_at", "submitted_at", "game", "paste_count", "tab_leave_count", "duration_sec"], "mac_dinh": ("started_at", -1),
        "quyen": {"doc": XEM, "xuat": XEM, "ghi": KHONG, "xoa": ADMIN},
    },
    "scores": {
        "nhom": "huong2", "ten": "Điểm chấm", "che_do": "readonly", "co_nhan": True,
        "cot": [("response_id", "Bài làm (ID)", "id"), ("data_label", "Nhãn", "nhan"), ("rater", "Người chấm", "text"),
                ("total", "Tổng điểm", "float"), ("model_name", "Mô hình", "text"), ("scored_at", "Chấm lúc", "datetime")],
        "chi_tiet": {"criteria": "Điểm từng tiêu chí", "model_version": "Phiên bản mô hình", "prompt_version": "Phiên bản prompt"},
        "tim": ["rater", "model_name"],
        "loc": [("rater", "Người chấm", "text", None), _nhan_loc()],
        "sap_xep": ["scored_at", "total", "rater"], "mac_dinh": ("scored_at", -1),
        "quyen": {"doc": XEM, "xuat": XEM, "ghi": KHONG, "xoa": ADMIN},
    },
    # ---------------- Cấu hình ----------------
    "access_codes": {
        "nhom": "cau_hinh", "ten": "Mã tham gia", "che_do": "crud", "co_nhan": True,
        "cot": [("code", "Mã", "bi_mat"), ("source", "Nguồn", "text"), ("data_label", "Nhãn", "nhan"),
                ("batch", "Lô", "text"), ("is_used", "Đã dùng", "bool"), ("used_at", "Dùng lúc", "datetime"), ("created_at", "Tạo lúc", "datetime")],
        "chi_tiet": {},
        "tim": ["code"],
        "loc": [("source", "Nguồn", "enum", NGUON_THAM_GIA), ("batch", "Lô", "text", None), ("is_used", "Đã dùng", "bool", None), _nhan_loc()],
        "sap_xep": ["created_at", "used_at", "source", "is_used", "batch"], "mac_dinh": ("created_at", -1),
        "quyen": {"doc": XEM, "xuat": XEM, "ghi": ADMIN, "xoa": ADMIN},
        "ghi": {"code": {"nhan": "Mã", "kieu": "text", "bat_buoc": True, "sua": False},
                "source": {"nhan": "Nguồn", "kieu": "choice", "bat_buoc": True, "lua_chon": NGUON_THAM_GIA, "sua": True},
                "data_label": {"nhan": "Nhãn dữ liệu", "kieu": "choice", "bat_buoc": True, "lua_chon": NHAN_LUA_CHON, "sua": True},
                "batch": {"nhan": "Lô (tùy chọn)", "kieu": "text", "bat_buoc": False, "sua": True}},
    },
    "schools": {
        "nhom": "cau_hinh", "ten": "Danh sách trường", "che_do": "readonly", "co_nhan": False,
        "ghi_chu": "Danh sách trường được quản lý bằng file content/schools.csv",   # hiện trên trang thay cho ghi chú mặc định
        "cot": [("name", "Tên trường", "text"), ("abbreviation", "Viết tắt", "text"), ("level", "Cấp", "text")],
        "chi_tiet": {"name_key": "Khóa tên", "key": "Khóa so khớp"},
        "tim": ["name", "abbreviation", "name_key"],
        "loc": [("level", "Cấp", "enum", CAP_TRUONG)],
        "sap_xep": ["name", "level"], "mac_dinh": ("name", 1),
        "quyen": {"doc": XEM, "xuat": XEM, "ghi": KHONG, "xoa": KHONG},   # matching dùng content/schools.csv nên không sửa trên web
    },
    # ---------------- Hệ thống ----------------
    "audit_log": {
        "nhom": "he_thong", "ten": "Nhật ký thao tác", "che_do": "readonly", "co_nhan": False,
        "cot": [("at", "Lúc (UTC)", "datetime"), ("username", "Người làm", "text"), ("role", "Vai trò", "text"),
                ("action", "Thao tác", "text"), ("collection", "Bảng", "text"), ("doc_id", "ID", "text")],
        "chi_tiet": {"detail": "Chi tiết"},
        "tim": ["username", "action", "collection", "doc_id"],
        "loc": [("action", "Thao tác", "text", None), ("role", "Vai trò", "enum", ["admin", "viewer", "rater"]),
                ("collection", "Bảng", "text", None)],
        "sap_xep": ["at", "username", "action"], "mac_dinh": ("at", -1),
        "quyen": {"doc": ADMIN, "xuat": ADMIN, "ghi": KHONG, "xoa": KHONG},   # nhật ký chỉ thêm, không ai sửa hay xóa
    },
}

NHOM = ("huong1", "huong2", "cau_hinh", "he_thong")
KICH_THUOC_TRANG_MAC_DINH = 25
KICH_THUOC_TRANG_TOI_DA = 100
SO_DONG_XUAT_TOI_DA = 5000
# Trường KHÔNG BAO GIỜ hiện ra giao diện, CSV hay nhật ký, dù bảng nào
TRUONG_CAM = ("password_hash", "session_token", "csrf_token", "user_agent")


def lay_bang(ten: str) -> dict | None:
    return BANG.get(ten)


def bang_cho_vai_tro(vai_tro: str) -> list:
    """Danh sách (tên, cấu hình) các bảng mà vai trò này được xem."""
    return [(ten, b) for ten, b in BANG.items() if vai_tro in b["quyen"]["doc"]]


def kiem_tra_registry() -> list:
    """Kiểm tra cấu hình tự nhất quán; trả danh sách lỗi (rỗng là tốt). Chạy trong test."""
    loi = []
    for ten, b in BANG.items():
        if b["nhom"] not in NHOM:
            loi.append(f"{ten}: nhóm lạ")
        if b["che_do"] == "readonly" and b["quyen"]["ghi"]:
            loi.append(f"{ten}: bảng readonly không được có quyền ghi")
        if b["che_do"] == "crud" and not b.get("ghi"):
            loi.append(f"{ten}: bảng crud phải khai báo 'ghi'")
        if b["che_do"] == "readonly" and b.get("ghi"):
            loi.append(f"{ten}: bảng readonly không được khai báo 'ghi'")
        if b["mac_dinh"][0] != "_id" and b["mac_dinh"][0] not in b["sap_xep"]:
            loi.append(f"{ten}: mac_dinh phải nằm trong sap_xep")
        for bc in b.get("bang_con", []):
            if not bc.get("ngoai_registry") and (bc["bang"] not in BANG or ("qua" in bc and bc["qua"] not in BANG)):
                loi.append(f"{ten}: bang_con trỏ tới bảng không có trong registry")
        if any(k in TRUONG_CAM for k, *_ in b["cot"]):
            loi.append(f"{ten}: cột chứa trường cấm")
    return loi
