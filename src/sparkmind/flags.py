"""Luật gắn cờ chống gian lận cho hướng 2 (web). Chỉ tính toán thuần túy, không đọc/ghi database.

CHỈ GẮN CỜ: không xóa dữ liệu, không báo cho người chơi. Mọi ngưỡng nằm ở config.py (CO_*).
Mỗi cờ là một chuỗi "mã:bước", ví dụ "lam_qua_nhanh:form_b". Ba mã cờ:
  lam_qua_nhanh : nhiều câu trả lời quá nhanh, hoặc cả bước làm xong quá sớm
  mot_dap_an    : chọn cùng một mức cho mọi câu Likert của khối
  bi_gian_doan  : có khoảng nghỉ dài hoặc ẩn tab lâu (CHỈ THAM KHẢO, không tính vào flag_count)
Dữ liệu thời gian do trình duyệt gửi nên có thể bị giả: chỉ dùng để gắn cờ, không để loại người chơi.
"""
from . import config

BUOC = ("form_b", "khoi_c", "game1", "game2")   # thứ tự cố định để kết quả luôn giống nhau mỗi lần tính


def ma_co(co: str) -> str:
    """"lam_qua_nhanh:form_b" -> "lam_qua_nhanh"."""
    return co.split(":", 1)[0]


def dem_co(cac_co: list) -> int:
    """flag_count: số cờ, KHÔNG tính cờ chỉ để tham khảo (bi_gian_doan)."""
    return sum(1 for c in cac_co if ma_co(c) not in config.CO_THAM_KHAO)


def tat_ca_co_co_the() -> list:
    """Mọi chuỗi cờ có thể có (dùng cho bộ lọc và thống kê ở trang quản trị)."""
    return ([f"lam_qua_nhanh:{b}" for b in BUOC] + [f"mot_dap_an:{b}" for b in ("form_b", "khoi_c")]
            + [f"bi_gian_doan:{b}" for b in ("form_b", "khoi_c")])


def _khoang(tg: dict | None) -> list:
    """Danh sách khoảng cách (mili giây) tới câu trước của từng câu đã đo."""
    return list(((tg or {}).get("khoang_ms") or {}).values())


def qua_nhanh_theo_cau(tg: dict | None) -> bool:
    """Tỉ lệ câu có khoảng cách dưới ngưỡng >= CO_TI_LE_CAU_NHANH. Ít câu đo được thì không xét."""
    khoang = _khoang(tg)
    if len(khoang) < config.CO_SO_CAU_TOI_THIEU:
        return False
    nhanh = sum(1 for k in khoang if k < config.CO_NGUONG_CAU_NHANH_MS)
    return nhanh / len(khoang) >= config.CO_TI_LE_CAU_NHANH


def qua_nhanh_tong(buoc: str, tong_giay: float | None) -> bool:
    """Tổng thời gian cả bước dưới ngưỡng riêng của bước. Không có số đo thì không xét."""
    return tong_giay is not None and tong_giay < config.CO_TONG_GIAY_TOI_THIEU[buoc]


def mot_dap_an(cac_muc: list | None) -> bool:
    """Trả lời đủ cả khối và chọn cùng một mức cho mọi câu."""
    if not cac_muc or any(m is None for m in cac_muc):
        return False
    return len(cac_muc) >= 2 and len(set(cac_muc)) == 1


def bi_gian_doan(tg: dict | None) -> bool:
    """Có khoảng cách (đã trừ thời gian ẩn tab) dài hơn ngưỡng, hoặc tổng thời gian ẩn tab dài hơn ngưỡng."""
    if not tg:
        return False
    dai = any(k > config.CO_KHOANG_GIAN_DOAN_MS for k in _khoang(tg))
    return dai or (tg.get("an_tab_ms") or 0) > config.CO_AN_TAB_GIAN_DOAN_MS


def co_cua_khoi(buoc: str, cac_muc: list | None, tg: dict | None, tong_giay: float | None) -> list:
    """Cờ của một khối Likert (form_b hoặc khoi_c). cac_muc = mức đã chọn của từng câu Likert; None nếu khối chưa làm/bỏ qua."""
    if cac_muc is None:
        return []
    co = []
    if qua_nhanh_theo_cau(tg) or qua_nhanh_tong(buoc, tong_giay):
        co.append(f"lam_qua_nhanh:{buoc}")
    if mot_dap_an(cac_muc):
        co.append(f"mot_dap_an:{buoc}")
    if bi_gian_doan(tg):
        co.append(f"bi_gian_doan:{buoc}")
    return co


def co_cua_game(buoc: str, tong_giay: float | None) -> list:
    """Cờ của một game đã nộp: chỉ xét tổng thời gian (do máy chủ đo)."""
    return [f"lam_qua_nhanh:{buoc}"] if qua_nhanh_tong(buoc, tong_giay) else []


def tinh_co(hanh_vi: dict | None, tu_danh_gia: dict | None, game: dict) -> list:
    """Toàn bộ cờ của một người từ dữ liệu đã lưu. `game` = {1: bản ghi game 1 đã nộp, 2: ...} (chỉ game đã nộp).

    Thuần túy và có thứ tự cố định nên tính lại bao nhiêu lần cũng ra cùng kết quả (idempotent).
    """
    co = []
    if hanh_vi:
        co += co_cua_khoi("form_b", _muc_b4(hanh_vi), hanh_vi.get("thoi_gian_cau"), hanh_vi.get("duration_sec"))
    if tu_danh_gia:
        tg = tu_danh_gia.get("thoi_gian_cau")
        tong = (tg or {}).get("tong_ms")
        co += co_cua_khoi("khoi_c", [tu_danh_gia.get(f"c{i}") for i in range(1, 6)], tg, None if tong is None else tong / 1000)
    for so in (1, 2):
        if so in game:
            co += co_cua_game(f"game{so}", game[so].get("duration_sec"))
    return co


def _muc_b4(hanh_vi: dict) -> list | None:
    """Bảy mức B4.1..B4.7; None nếu người này chọn "Chưa bao giờ sử dụng" (A4 = 4, bỏ qua phần B)."""
    muc = [hanh_vi.get(f"b4_{i}") for i in range(1, 8)]
    return None if all(m is None for m in muc) else muc
