"""Hướng 1 trên web: kiểm tra câu trả lời và đổi MÃ lựa chọn thành CHỮ y hệt bản ghi của Google Form.

Chữ câu hỏi và đáp án chỉ nằm ở content/form_b.json (cùng nguồn với form B hướng 2, đã khớp từng ký tự với
docs/survey_v2.md). Trình duyệt chỉ gửi mã (ma), máy chủ tự đổi thành chữ để bản ghi trong survey_form1 giống hệt
bản ghi Google Form: chọn một -> chữ của đáp án; chọn nhiều -> các chữ nối bằng ", " theo thứ tự đáp án,
"Mục khác" -> chữ người dùng gõ; thang 1-5 -> số nguyên.
Hướng 1 KHÔNG thu email hay tên: không có trường nào như vậy trong bài gửi lên.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from . import config
from .columns import B4, CC

CAU_CHON_MOT = ("A1", "A2", "A4", "B2", "B5", "B7", "C6")
CAU_CHON_NHIEU = ("B1", "B3", "B6")
CAU_B_THUONG = ("B1", "B2", "B3", "B5", "B6", "B7")      # câu của phần B (ngoài lưới B4); bỏ qua khi A4 = "Chưa bao giờ sử dụng"
LOP_CAN_NGUOI_LON = 7                                     # mã A1 từ 1 đến 7 là lớp 6-12 (dưới 18 tuổi), cần phụ huynh/giáo viên biết
GIO_VIET_NAM = timezone(timedelta(hours=7))              # Google Form ghi giờ Việt Nam; Render chạy giờ UTC nên phải đổi
DO_DAI_CHU_TOI_DA = 200


class LoiForm1(ValueError):
    """Bài gửi không hợp lệ. `ma` là mã lỗi ngắn (giao diện đổi thành chữ trong research_ui.json > loi)."""

    def __init__(self, ma: str):
        super().__init__(ma)
        self.ma = ma


@lru_cache
def lua_chon() -> dict:
    """{id câu: {"chu": {mã: chữ}, "thu_tu": [mã...], "khac": mã của "Mục khác:" hoặc None}} đọc từ content/form_b.json."""
    with open(config.ROOT / "content" / "form_b.json", encoding="utf-8") as f:
        form = json.load(f)
    cau = form["phan_a_thong_tin"] + form["phan_b_hanh_vi"] + form["phan_c_tu_danh_gia"]
    kq = {}
    for c in cau:
        if "options" in c:
            ds = c["options"]
            kq[c["id"]] = {"chu": {o["ma"]: o["text"] for o in ds if not o.get("khac")}, "thu_tu": [o["ma"] for o in ds],
                           "khac": next((o["ma"] for o in ds if o.get("khac")), None)}
    return kq


def ma_chua_tung_dung() -> int:
    """Mã đáp án A4 "Chưa bao giờ sử dụng" (chọn thì bỏ cả phần B, như điều hướng của Google Form)."""
    return next(m for m, chu in lua_chon()["A4"]["chu"].items() if chu.startswith("Chưa bao giờ"))


def lam_sach_chu(chu) -> str:
    """Bỏ ký tự điều khiển, gộp khoảng trắng thừa, cắt tối đa 200 ký tự."""
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", str(chu or ""))).strip()[:DO_DAI_CHU_TOI_DA]


def chu_chon_mot(id_cau: str, ma) -> str:
    chu = lua_chon()[id_cau]["chu"]
    if ma is None:
        raise LoiForm1("thieu_cau")
    if ma not in chu:
        raise LoiForm1("gia_tri_sai")
    return chu[ma]


def chu_chon_nhieu(id_cau: str, cac_ma, chu_khac) -> str:
    """Nối chữ các đáp án đã chọn theo thứ tự đáp án; "Mục khác:" thay bằng chữ người dùng gõ (bắt buộc có)."""
    lc = lua_chon()[id_cau]
    chon = set(cac_ma or [])
    if not chon or not chon <= set(lc["thu_tu"]):
        raise LoiForm1("thieu_cau" if not chon else "gia_tri_sai")
    cac_chu = []
    for ma in (m for m in lc["thu_tu"] if m in chon):
        if ma == lc["khac"]:
            if not lam_sach_chu(chu_khac):
                raise LoiForm1("thieu_muc_khac")
            cac_chu.append(lam_sach_chu(chu_khac))
        else:
            cac_chu.append(lc["chu"][ma])
    return ", ".join(cac_chu)


def kiem_tra_dong_y(d: dict) -> None:
    """Phải tích đồng ý; lớp 6-12 thì phải có xác nhận của phụ huynh/giáo viên. Hai ô này KHÔNG lưu vào dữ liệu."""
    if not d.get("consent"):
        raise LoiForm1("thieu_dong_y")
    if d["A1"] <= LOP_CAN_NGUOI_LON and not d.get("guardian_consent"):
        raise LoiForm1("thieu_nguoi_lon")


def phan_a(d: dict) -> dict:
    """A1-A4 thành chữ. A3 (tên trường) là chữ người dùng gõ hoặc chọn, bắt buộc không trống."""
    kq = {k: chu_chon_mot(k, d[k]) for k in ("A1", "A2", "A4")}
    kq["A3"] = lam_sach_chu(d["A3"])
    if not kq["A3"]:
        raise LoiForm1("thieu_cau")
    return kq


def phan_b(d: dict) -> dict:
    """B1-B7 thành chữ/số. Thiếu câu nào (kể cả một dòng B4) là lỗi."""
    kq = {k: chu_chon_mot(k, d.get(k)) for k in ("B2", "B5", "B7")}
    for k in CAU_CHON_NHIEU:
        kq[k] = chu_chon_nhieu(k, d.get(k), d.get(k + "_other"))
    for k in B4:
        if d.get(k) is None:
            raise LoiForm1("thieu_cau")
        kq[k] = int(d[k])
    return kq


def thoi_gian_viet_nam(bay_gio: datetime | None = None) -> str:
    """Giờ Việt Nam dạng "2026-01-05 10:30:00" (giống cột Dấu thời gian của Google Form qua Apps Script)."""
    t = bay_gio or datetime.now(GIO_VIET_NAM)
    return t.strftime("%Y-%m-%d %H:%M:%S")


def chuyen_sang_goc(d: dict, bay_gio: datetime | None = None) -> dict:
    """Từ bài gửi (mã lựa chọn) sang câu trả lời gốc (chữ) với đúng các khóa của Google Form (columns.RAW_KEYS).

    Báo LoiForm1 nếu thiếu câu bắt buộc hoặc mã không có trong form. Chọn "Chưa bao giờ sử dụng" (A4) thì bỏ phần B."""
    kiem_tra_dong_y(d)
    goc = {"thoi_gian": thoi_gian_viet_nam(bay_gio), **phan_a(d)}
    if d["A4"] != ma_chua_tung_dung():
        goc.update(phan_b(d))
    for k in CC:
        goc[k] = int(d[k])
    goc["C6"] = chu_chon_mot("C6", d["C6"])
    return goc
