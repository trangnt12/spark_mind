"""Đọc/ghi MongoDB cho chế độ nghiên cứu (hướng 2). Cấu trúc theo docs/erd.dbml.

Dữ liệu ở đây KHÔNG ghi vào survey_form1 hay survey_clean.
"""
import re
import secrets
from datetime import datetime

from pymongo.errors import DuplicateKeyError

from . import config

COL_MA = "access_codes"
COL_NGUOI = "participants"
COL_HANH_VI = "behavior_answers"
COL_TU_DANH_GIA = "self_assessment"

# Bảng chữ cho mã tham gia: bỏ O, 0, I, 1 để khỏi nhầm khi đọc/gõ
BANG_CHU = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
NGUON_HOP_LE = ("volunteer", "hired_team")
LOP_DUOI_18 = 7  # mã A1 từ 1 đến 7 là lớp 6–12 (dưới 18 tuổi)


class LoiNghiepVu(Exception):
    """Lỗi do người dùng (mã sai, thiếu đồng ý...). `ma_http` là mã trả về cho trình duyệt."""

    def __init__(self, ma_http: int, noi_dung: str):
        super().__init__(noi_dung)
        self.ma_http = ma_http
        self.noi_dung = noi_dung


def tao_chi_muc(db) -> None:
    """Tạo chỉ mục khi server khởi động (tạo lại nhiều lần vẫn an toàn)."""
    db[COL_MA].create_index("code", unique=True)
    db[COL_NGUOI].create_index("code_id", unique=True)
    db[COL_NGUOI].create_index("email")
    db[COL_NGUOI].create_index("ip_hash")
    db[COL_NGUOI].create_index("session_token", unique=True)
    db[COL_HANH_VI].create_index("participant_id", unique=True)
    db[COL_TU_DANH_GIA].create_index("participant_id", unique=True)


def chuan_hoa_ma(code: str) -> str:
    """Mã không phân biệt hoa thường, bỏ khoảng trắng và dấu gạch."""
    return re.sub(r"[\s-]", "", code or "").upper()


def chuan_hoa_email(email: str) -> str:
    """Chữ thường, bỏ mọi khoảng trắng. Không bắt duy nhất."""
    return re.sub(r"\s+", "", email or "").lower()


def tao_ma_moi(db, n: int, nguon: str, data_label: str = config.NHAN_MAC_DINH) -> list:
    """Tạo n mã ngẫu nhiên 8 ký tự, ghi vào access_codes (kèm nhãn dữ liệu), trả về danh sách mã."""
    if nguon not in NGUON_HOP_LE:
        raise ValueError(f"source phải là một trong {NGUON_HOP_LE}")
    if data_label not in config.NHAN_HOP_LE:
        raise ValueError(f"data_label phải là một trong {config.NHAN_HOP_LE}")
    ket_qua = []
    while len(ket_qua) < n:
        ma = "".join(secrets.choice(BANG_CHU) for _ in range(8))
        try:
            db[COL_MA].insert_one({"code": ma, "source": nguon, "is_used": False,
                                   "used_at": None, "created_at": datetime.now(), "data_label": data_label})
            ket_qua.append(ma)
        except DuplicateKeyError:
            continue  # trùng mã cũ (rất hiếm): thử mã khác
    return ket_qua


def kiem_tra_ma(db, code: str) -> dict:
    """valid: mã tồn tại và chưa dùng. can_resume: mã đã dùng nhưng người đó chưa hoàn thành."""
    ma = db[COL_MA].find_one({"code": chuan_hoa_ma(code)})
    if not ma:
        return {"valid": False, "can_resume": False}
    if not ma["is_used"]:
        return {"valid": True, "can_resume": False}
    nguoi = db[COL_NGUOI].find_one({"code_id": ma["_id"]})
    return {"valid": False, "can_resume": bool(nguoi and not nguoi.get("completed_at"))}


def kiem_tra_dong_y(d: dict) -> None:
    """Bắt buộc đồng ý; lớp 6–12 (dưới 18 tuổi) bắt buộc thêm đồng ý của phụ huynh/giáo viên."""
    if d["consent"] is not True:
        raise LoiNghiepVu(422, "Cần đồng ý tham gia nghiên cứu.")
    if d["grade"] <= LOP_DUOI_18 and d.get("guardian_consent") is not True:
        raise LoiNghiepVu(422, "Dưới 18 tuổi cần có sự đồng ý của phụ huynh hoặc giáo viên.")


def _tiep_tuc(db, ma: dict, email: str) -> str:
    """Mã đã dùng: chỉ cho vào lại nếu cùng email và chưa hoàn thành, trả cùng session_token."""
    nguoi = db[COL_NGUOI].find_one({"code_id": ma["_id"]})
    if nguoi and nguoi["email"] == email and not nguoi.get("completed_at"):
        return nguoi["session_token"]
    raise LoiNghiepVu(409, "Mã này đã được sử dụng.")


def _nguoi_moi(ma: dict, d: dict, email: str, ip_hash: str, user_agent: str) -> dict:
    """Tài liệu participants mới (không có IP thô, chỉ có ip_hash)."""
    bay_gio = datetime.now()
    return {"code_id": ma["_id"], "source": ma["source"], "data_label": ma.get("data_label", config.NHAN_MAC_DINH), "email": email,
            "grade": str(d["grade"]), "gender": str(d["gender"]),
            "school_name": d["school_name"].strip(), "consent": True, "consent_at": bay_gio,
            "guardian_consent": bool(d.get("guardian_consent")), "ip_hash": ip_hash,
            "user_agent": (user_agent or "")[:300], "started_at": bay_gio, "completed_at": None,
            "session_token": secrets.token_urlsafe(32)}


def bat_dau(db, d: dict, ip_hash: str, user_agent: str) -> str:
    """Bắt đầu tham gia: kiểm tra, đánh dấu mã đã dùng, tạo participants, trả session_token."""
    kiem_tra_dong_y(d)
    email = chuan_hoa_email(d["email"])
    ma = db[COL_MA].find_one({"code": chuan_hoa_ma(d["code"])})
    if not ma:
        raise LoiNghiepVu(404, "Mã tham gia không đúng.")
    if ma["is_used"]:
        return _tiep_tuc(db, ma, email)
    # Đánh dấu "đã dùng" bằng một thao tác duy nhất để hai người không cùng chiếm một mã
    chiem = db[COL_MA].update_one({"_id": ma["_id"], "is_used": False},
                                  {"$set": {"is_used": True, "used_at": datetime.now()}})
    if chiem.modified_count != 1:
        raise LoiNghiepVu(409, "Mã này đã được sử dụng.")
    nguoi = _nguoi_moi(ma, d, email, ip_hash, user_agent)
    db[COL_NGUOI].insert_one(nguoi)
    return nguoi["session_token"]


def tim_nguoi(db, session_token: str) -> dict:
    """Tìm người tham gia theo session_token; không có thì báo lỗi 401."""
    nguoi = db[COL_NGUOI].find_one({"session_token": session_token}) if session_token else None
    if not nguoi:
        raise LoiNghiepVu(401, "Phiên làm bài không hợp lệ.")
    return nguoi


def tinh_diem_sang_tao(c: list) -> float:
    """creativity_score = (tổng C1..C5 − 5) / 20 × 100. Thang 0–100."""
    return (sum(c) - 5) / 20 * 100


def _luu_mot_lan(db, ten_bang: str, tai_lieu: dict) -> None:
    """Ghi một tài liệu; nếu người này đã nộp rồi (trùng participant_id) thì báo lỗi 409."""
    try:
        db[ten_bang].insert_one(tai_lieu)
    except DuplicateKeyError:
        raise LoiNghiepVu(409, "Bạn đã nộp phần này rồi.")


def _ghi_de(db, ten_bang: str, participant_id, tai_lieu: dict) -> None:
    """Người dùng bấm "Quay lại" rồi sửa: ghi đè câu trả lời cũ (vẫn chỉ một tài liệu mỗi người),
    ghi giờ sửa gần nhất và số lần sửa để còn biết."""
    db[ten_bang].update_one({"participant_id": participant_id},
                            {"$set": {**tai_lieu, "sua_luc": datetime.now()}, "$inc": {"so_lan_sua": 1}},
                            upsert=True)


def chan_neu_da_hoan_thanh(nguoi: dict) -> None:
    """Sau khi completed_at được gán thì khóa khảo sát: không sửa nữa (403)."""
    if nguoi.get("completed_at"):
        raise LoiNghiepVu(403, "Bạn đã hoàn thành, không sửa được nữa.")


def _luu(db, ten_bang: str, nguoi: dict, tai_lieu: dict, ghi_de: bool) -> None:
    """Lưu một phần: lần đầu thì chặn nộp trùng (409), còn đang sửa thì ghi đè (chỉ khi chưa hoàn thành)."""
    chan_neu_da_hoan_thanh(nguoi)
    if ghi_de:
        _ghi_de(db, ten_bang, nguoi["_id"], tai_lieu)
    else:
        nhan = nguoi.get("data_label", config.NHAN_MAC_DINH)   # bảng con thừa hưởng nhãn của người tham gia
        _luu_mot_lan(db, ten_bang, {"participant_id": nguoi["_id"], "data_label": nhan, **tai_lieu})


def luu_hanh_vi(db, session_token: str, tra_loi: dict, ghi_de: bool = False) -> None:
    """Lưu câu trả lời form B (tra_loi đã được kiểm tra hợp lệ, khóa theo erd.dbml)."""
    _luu(db, COL_HANH_VI, tim_nguoi(db, session_token), tra_loi, ghi_de)


def luu_tu_danh_gia(db, session_token: str, tra_loi: dict, ghi_de: bool = False) -> float:
    """Lưu C1..C5, C6 và điểm sáng tạo tự nhận thức. Trả về điểm."""
    nguoi = tim_nguoi(db, session_token)
    diem = tinh_diem_sang_tao([tra_loi[f"c{i}"] for i in range(1, 6)])
    _luu(db, COL_TU_DANH_GIA, nguoi, {**tra_loi, "creativity_score": diem}, ghi_de)
    return diem


def sua_thong_tin(db, session_token: str, d: dict) -> None:
    """Sửa lớp, giới tính, trường (phần A) sau khi đã bắt đầu. Email và đồng ý ban đầu giữ nguyên."""
    nguoi = tim_nguoi(db, session_token)
    chan_neu_da_hoan_thanh(nguoi)
    if d["grade"] <= LOP_DUOI_18 and d.get("guardian_consent") is not True:
        raise LoiNghiepVu(422, "Dưới 18 tuổi cần có sự đồng ý của phụ huynh hoặc giáo viên.")
    db[COL_NGUOI].update_one({"_id": nguoi["_id"]}, {"$inc": {"so_lan_sua": 1}, "$set": {
        "grade": str(d["grade"]), "gender": str(d["gender"]), "school_name": d["school_name"].strip(),
        "guardian_consent": bool(d.get("guardian_consent")), "sua_luc": datetime.now()}})
