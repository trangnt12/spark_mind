"""Khảo sát hướng 1 trên web (kênh thu thứ hai, ĐÓNG mặc định): trang /huong-1/khao-sat, nội dung và nhận bài.

- Công tắc settings.huong1_web_mo tắt (mặc định) thì mọi đường API ở đây trả 423; giao diện hiện trang "chưa mở".
- Bài nộp lưu vào survey_form1 với nguon = "web" (đúng các cột của bản ghi Google Form) rồi làm sạch ngay (ingest.nhan_form).
- Không thu email hay tên. Chống lạm dụng: giới hạn tốc độ theo IP đã băm, trường ẩn chống bot, giới hạn kích thước,
  kiểm tra phía máy chủ. Chặn nộp lại 24 giờ do trình duyệt (localStorage); máy chủ KHÔNG phát hiện người làm hai lần.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from server.content_api import doc_noi_dung
from server.research import lay_db_nghien_cuu, lay_ip
from server.status_api import yeu_cau_huong1_web_mo
from server.thoi_gian_cau import CAU_FORM_B, CAU_KHOI_C, ThoiGianCau, de_luu
from sparkmind import config, form1_web
from sparkmind.ingest import nhan_form
from sparkmind.security import GioiHanTocDo, bam_ip

router = APIRouter()
gioi_han_nop = GioiHanTocDo(toi_da=config.HUONG1_GIOI_HAN_LAN, giay=config.HUONG1_GIOI_HAN_GIAY)
LuaChonNhieu = Annotated[list[int] | None, Field(min_length=1, max_length=10)]
Thang5 = Annotated[int | None, Field(ge=1, le=5)]
ChuKhac = Annotated[str | None, Field(max_length=form1_web.DO_DAI_CHU_TOI_DA)]


class Form1Body(BaseModel):
    """Bài gửi. Chỉ nhận đúng các trường này (khóa lạ, ví dụ email hay name, bị từ chối): hướng 1 không thu email hay tên."""
    model_config = ConfigDict(extra="forbid")
    consent: bool
    guardian_consent: bool = False
    A1: int = Field(ge=1, le=99)
    A2: int = Field(ge=1, le=99)
    A3: str = Field(min_length=1, max_length=form1_web.DO_DAI_CHU_TOI_DA * 2)
    A4: int = Field(ge=1, le=99)
    B1: LuaChonNhieu = None
    B2: int | None = None
    B3: LuaChonNhieu = None
    B4_1: Thang5 = None
    B4_2: Thang5 = None
    B4_3: Thang5 = None
    B4_4: Thang5 = None
    B4_5: Thang5 = None
    B4_6: Thang5 = None
    B4_7: Thang5 = None
    B5: int | None = None
    B6: LuaChonNhieu = None
    B7: int | None = None
    B1_other: ChuKhac = None
    B3_other: ChuKhac = None
    B6_other: ChuKhac = None
    C1: int = Field(ge=1, le=5)
    C2: int = Field(ge=1, le=5)
    C3: int = Field(ge=1, le=5)
    C4: int = Field(ge=1, le=5)
    C5: int = Field(ge=1, le=5)
    C6: int = Field(ge=1, le=99)
    thoi_gian: ThoiGianCau | None = None     # thời gian làm bài (tổng và từng câu Likert), chỉ để gắn cờ chất lượng
    ghi_chu_them: str = Field(default="", max_length=200)   # trường ẩn chống bot (tên trung tính để trình duyệt không tự điền): người thật không thấy nên luôn để trống
    thu: bool = False                         # đường dẫn thử (?thu=1): bài gán nhãn "thu", không ghi vào survey_form1


def kiem_kich_thuoc(request: Request) -> None:
    """Bài gửi lớn hơn HUONG1_BODY_TOI_DA byte thì từ chối (413) trước khi xử lý."""
    try:
        dai = int(request.headers.get("content-length", "0"))
    except ValueError:
        dai = 0
    if dai > config.HUONG1_BODY_TOI_DA:
        raise HTTPException(status_code=413, detail="qua_lon")


def kiem_toc_do(request: Request) -> None:
    """Một địa chỉ mạng gửi quá nhiều bài trong ít phút thì chặn (429). Khóa đếm là IP đã băm HMAC, đếm trong bộ nhớ, KHÔNG lưu IP."""
    try:
        khoa = bam_ip(lay_ip(request))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Server chưa cấu hình xong.")
    if not gioi_han_nop.cho_phep(khoa):
        cho = gioi_han_nop.giay_phai_cho(khoa)
        raise HTTPException(status_code=429, headers={"Retry-After": str(cho)}, detail="Gửi quá nhiều lần, vui lòng đợi một lúc.")


@router.get("/huong-1/khao-sat", include_in_schema=False)
def trang_khao_sat():
    """Khung trang khảo sát (web/survey1.html). Khung này không chứa câu hỏi; công tắc đóng thì giao diện thấy 423 và hiện trang "chưa mở"."""
    return FileResponse(config.ROOT / "web" / "survey1.html", headers={"Cache-Control": "no-cache"})


@router.get("/api/huong1/noi-dung", dependencies=[Depends(yeu_cau_huong1_web_mo)])
def noi_dung():
    """Chữ giao diện riêng của hướng 1 (content/survey1_ui.json), số giờ khóa nộp lại, mã đáp án A4 "Chưa bao giờ" (bỏ phần B). Câu hỏi lấy ở /api/content/form-b."""
    return {**doc_noi_dung("survey1_ui.json"), "gio_khoa_nop_lai": config.HUONG1_KHOA_NOP_LAI_GIO,
            "ma_chua_tung_dung": form1_web.ma_chua_tung_dung()}


@router.post("/api/huong1/submit", dependencies=[Depends(yeu_cau_huong1_web_mo), Depends(kiem_kich_thuoc), Depends(kiem_toc_do)])
def nop_khao_sat(body: Form1Body, db=Depends(lay_db_nghien_cuu)):
    """Nhận một bài: bẫy bot -> kiểm tra -> lưu gốc (nguon="web") + làm sạch. Bài thử (thu=true) chỉ lưu bản sạch, nhãn "thu"."""
    if body.ghi_chu_them.strip():
        return {"ok": True}          # bot điền trường ẩn: giả vờ thành công để nó không thử lại, KHÔNG lưu gì
    try:
        goc = form1_web.chuyen_sang_goc(body.model_dump())
        them = {"thoi_gian_lam_bai": de_luu(body.thoi_gian, CAU_FORM_B + CAU_KHOI_C)}
        nhan_form(db, goc, nguon="web", nhan="thu" if body.thu else config.NHAN_MAC_DINH,
                  them={k: v for k, v in them.items() if v is not None})
    except (form1_web.LoiForm1, ValueError) as loi:
        raise HTTPException(status_code=422, detail=getattr(loi, "ma", "gia_tri_sai"))
    return {"ok": True}
