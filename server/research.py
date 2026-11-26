"""Các endpoint của chế độ nghiên cứu (hướng 2): kiểm tra mã, bắt đầu, nộp form B và C1–C5."""
import json
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from server.thoi_gian_cau import CAU_FORM_B, CAU_KHOI_C, ThoiGianCau, de_luu
from sparkmind import config, flags_store, research_store as kho
from sparkmind.security import GioiHanTocDo, bam_ip

router = APIRouter(prefix="/api/research")
CHUA_TUNG_DUNG = 4  # mã A4 "Chưa bao giờ sử dụng"
gioi_han_ma = GioiHanTocDo(toi_da=10, giay=60)  # tối đa 10 lần nhập SAI mỗi phút cho mỗi IP


def lay_db_nghien_cuu():
    """Lấy kết nối dùng chung (import muộn để main.py ghi đè được khi thử)."""
    from server.main import lay_db_dung_chung
    return lay_db_dung_chung()


class MaBody(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class BatDauBody(MaBody):
    email: str = Field(min_length=3, max_length=254, pattern=r"^\S+@\S+\.\S+$")
    grade: int = Field(ge=1, le=12)      # mã A1 trong content/form_b.json (1–7 là lớp 6–12)
    gender: int = Field(ge=1, le=3)      # mã A2
    school_name: str = Field(min_length=1, max_length=200)
    consent: bool
    guardian_consent: bool = False

    @field_validator("email", mode="before")
    @classmethod
    def _chuan_hoa_email(cls, v):
        """Chuẩn hóa (chữ thường, bỏ khoảng trắng) TRƯỚC khi kiểm tra dạng email."""
        return kho.chuan_hoa_email(v) if isinstance(v, str) else v


class SuaThongTinBody(BaseModel):
    """Sửa phần A sau khi đã bắt đầu (nút Quay lại)."""
    session_token: str = Field(min_length=1, max_length=100)
    grade: int = Field(ge=1, le=12)
    gender: int = Field(ge=1, le=3)
    school_name: str = Field(min_length=1, max_length=200)
    guardian_consent: bool = False


class HanhViBody(BaseModel):
    session_token: str = Field(min_length=1, max_length=100)
    edit: bool = False                        # true: đang sửa phần đã nộp (Quay lại), ghi đè thay vì báo 409
    A4: int                                   # dùng AI chưa; mã 4 = "Chưa bao giờ sử dụng"
    # B1–B7 bắt buộc, trừ khi A4 = 4 (kiểm tra trong nop_hanh_vi)
    B1: list[int] | None = Field(default=None, min_length=1, max_length=10)  # chọn nhiều
    B2: int | None = None
    B3: list[int] | None = Field(default=None, min_length=1, max_length=10)  # chọn nhiều
    B4_1: int | None = Field(default=None, ge=1, le=5)
    B4_2: int | None = Field(default=None, ge=1, le=5)
    B4_3: int | None = Field(default=None, ge=1, le=5)
    B4_4: int | None = Field(default=None, ge=1, le=5)
    B4_5: int | None = Field(default=None, ge=1, le=5)
    B4_6: int | None = Field(default=None, ge=1, le=5)
    B4_7: int | None = Field(default=None, ge=1, le=5)
    B5: int | None = None
    B6: list[int] | None = Field(default=None, min_length=1, max_length=10)  # chọn nhiều
    B7: int | None = None
    # chữ người dùng gõ ở lựa chọn "Mục khác:" của B1, B3, B6 (chỉ lưu khi họ đã chọn "Mục khác:")
    B1_other: str | None = Field(default=None, max_length=200)
    B3_other: str | None = Field(default=None, max_length=200)
    B6_other: str | None = Field(default=None, max_length=200)
    duration_sec: int = Field(ge=0, le=86400)
    thoi_gian_cau: ThoiGianCau | None = None  # thời gian từng câu B4 (chỉ để gắn cờ); bỏ qua khi đang sửa (edit)


class TuDanhGiaBody(BaseModel):
    session_token: str = Field(min_length=1, max_length=100)
    C1: int = Field(ge=1, le=5)
    C2: int = Field(ge=1, le=5)
    C3: int = Field(ge=1, le=5)
    C4: int = Field(ge=1, le=5)
    C5: int = Field(ge=1, le=5)
    C6: int
    edit: bool = False                        # true: đang sửa phần đã nộp (Quay lại), ghi đè thay vì báo 409
    thoi_gian_cau: ThoiGianCau | None = None  # thời gian từng câu C1–C5 (chỉ để gắn cờ); bỏ qua khi đang sửa


@lru_cache
def lua_chon_hop_le() -> dict:
    """Các mã lựa chọn hợp lệ của từng câu, đọc từ content/form_b.json (không viết cứng)."""
    with open(config.ROOT / "content" / "form_b.json", encoding="utf-8") as f:
        form = json.load(f)
    cau = form["phan_a_thong_tin"] + form["phan_b_hanh_vi"] + form["phan_c_tu_danh_gia"]
    return {c["id"]: {o["ma"] for o in c["options"]} for c in cau if "options" in c}


@lru_cache
def ma_muc_khac() -> dict:
    """Mã của lựa chọn "Mục khác:" ở từng câu (có "khac": true trong form_b.json), ví dụ {"B1": 5, ...}."""
    with open(config.ROOT / "content" / "form_b.json", encoding="utf-8") as f:
        form = json.load(f)
    return {c["id"]: o["ma"] for c in form["phan_b_hanh_vi"] for o in c.get("options", []) if o.get("khac")}


def chu_muc_khac(body) -> dict:
    """{"b1_other": ..., "b3_other": ..., "b6_other": ...}: chữ đã bỏ khoảng trắng đầu/cuối; None nếu không chọn "Mục khác:"."""
    kq = {}
    for id_cau, ma in ma_muc_khac().items():
        chu = (getattr(body, f"{id_cau}_other") or "").strip()
        kq[f"{id_cau.lower()}_other"] = chu if chu and ma in (getattr(body, id_cau) or []) else None
    return kq


def kiem_tra_lua_chon(id_cau: str, gia_tri) -> None:
    """Báo lỗi 422 nếu mã lựa chọn không có trong form."""
    ds = gia_tri if isinstance(gia_tri, list) else [gia_tri]
    if not set(ds) <= lua_chon_hop_le()[id_cau]:
        raise HTTPException(status_code=422, detail=f"Giá trị không hợp lệ ở câu {id_cau}")


def lay_ip(request: Request) -> str:
    """IP người dùng = request.client.host. Không tự đọc x-forwarded-for (người dùng giả được).

    Sau proxy của Render, uvicorn chạy với --proxy-headers --forwarded-allow-ips="*" sẽ tự thay
    client.host bằng IP thật. Chỉ dùng để băm/giới hạn tốc độ, không lưu thô.
    """
    return request.client.host if request.client else ""


def chay(ham, *args):
    """Gọi hàm của kho dữ liệu, đổi lỗi nghiệp vụ thành lỗi HTTP."""
    try:
        return ham(*args)
    except kho.LoiNghiepVu as loi:
        raise HTTPException(status_code=loi.ma_http, detail=loi.noi_dung)


@router.post("/code/check")
def kiem_tra_ma(body: MaBody, request: Request, db=Depends(lay_db_nghien_cuu)):
    ip = lay_ip(request)
    cho = gioi_han_ma.giay_phai_cho(ip)  # chỉ đếm mã SAI, nên chỉ kiểm tra chứ không tính lượt
    if cho:
        raise HTTPException(status_code=429, headers={"Retry-After": str(cho)},
                            detail=f"Nhập sai mã quá nhiều lần, vui lòng đợi {cho} giây.")
    kq = chay(kho.kiem_tra_ma, db, body.code)
    if not kq["valid"] and not kq["can_resume"]:
        gioi_han_ma.ghi_nhan(ip)  # mã không tồn tại (hoặc đã dùng xong) mới tính một lần sai
    return kq


@router.post("/start")
def bat_dau(body: BatDauBody, request: Request, db=Depends(lay_db_nghien_cuu)):
    try:
        ip_hash = bam_ip(lay_ip(request))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Server chưa cấu hình xong.")
    token = chay(kho.bat_dau, db, body.model_dump(), ip_hash, request.headers.get("user-agent", ""))
    return {"session_token": token}


@router.post("/info/update")
def sua_thong_tin(body: SuaThongTinBody, db=Depends(lay_db_nghien_cuu)):
    kiem_tra_lua_chon("A1", body.grade)
    kiem_tra_lua_chon("A2", body.gender)
    chay(kho.sua_thong_tin, db, body.session_token, body.model_dump())
    return {"ok": True}


def _dang_chuoi(v):
    """Chọn nhiều -> "1,3" (đã bỏ trùng, sắp xếp); chọn một -> chuỗi; trống -> None."""
    if v is None:
        return None
    return ",".join(str(x) for x in sorted(set(v))) if isinstance(v, list) else str(v)


def _kiem_tra_hanh_vi(body: HanhViBody) -> None:
    """A4 phải hợp lệ; B1–B7 bắt buộc trừ khi chưa bao giờ dùng AI; mọi mã phải có trong form."""
    kiem_tra_lua_chon("A4", body.A4)
    ten_cau = ["B1", "B2", "B3", "B5", "B6", "B7"] + [f"B4_{i}" for i in range(1, 8)]
    if body.A4 != CHUA_TUNG_DUNG and any(getattr(body, c) is None for c in ten_cau):
        raise HTTPException(status_code=422, detail="Thiếu câu trả lời ở phần B.")
    for c in ("B1", "B2", "B3", "B5", "B6", "B7"):
        if getattr(body, c) is not None:
            kiem_tra_lua_chon(c, getattr(body, c))


@router.post("/behavior")
def nop_hanh_vi(body: HanhViBody, db=Depends(lay_db_nghien_cuu)):
    _kiem_tra_hanh_vi(body)
    tra_loi = {"a4": str(body.A4), "b1": _dang_chuoi(body.B1), "b2_frequency": _dang_chuoi(body.B2),
               "b3": _dang_chuoi(body.B3), "b5_duration": _dang_chuoi(body.B5),
               "b6_prompting": _dang_chuoi(body.B6), "b7_after_answer": _dang_chuoi(body.B7),
               "duration_sec": body.duration_sec}
    tra_loi.update({f"b4_{i}": getattr(body, f"B4_{i}") for i in range(1, 8)})
    tra_loi.update(chu_muc_khac(body))
    if not body.edit and body.thoi_gian_cau:   # lần sửa không ghi đè số đo của lần làm đầu tiên
        tra_loi["thoi_gian_cau"] = de_luu(body.thoi_gian_cau, CAU_FORM_B)
    chay(kho.luu_hanh_vi, db, body.session_token, tra_loi, body.edit)
    flags_store.cap_nhat_co_theo_token(db, body.session_token)
    return {"ok": True}


@router.post("/self-assessment")
def nop_tu_danh_gia(body: TuDanhGiaBody, db=Depends(lay_db_nghien_cuu)):
    kiem_tra_lua_chon("C6", body.C6)
    tra_loi = {f"c{i}": getattr(body, f"C{i}") for i in range(1, 6)}
    tra_loi["c6"] = str(body.C6)
    if not body.edit and body.thoi_gian_cau:
        tra_loi["thoi_gian_cau"] = de_luu(body.thoi_gian_cau, CAU_KHOI_C)
    chay(kho.luu_tu_danh_gia, db, body.session_token, tra_loi, body.edit)
    flags_store.cap_nhat_co_theo_token(db, body.session_token)
    return {"ok": True}  # không trả điểm để người chơi không bị ảnh hưởng ở phần game
