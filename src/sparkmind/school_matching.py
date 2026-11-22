"""Chuẩn hóa tên trường (A3) từ chữ tự do.

Làm 3 lớp (khớp danh sách và so gần đúng xem `khop_truong`; KHÔNG cần duyệt tay):
1. Chuẩn hóa chữ: bỏ dấu, hoa thường, bỏ khoảng trắng thừa -> `truong_khoa`.
2. Suy ra cấp học (THCS / THPT / Liên cấp / Đại học / Không rõ) -> `truong_cap`.
3. Tra bảng người duyệt `content/school_overrides.csv` (khoa -> tên chuẩn, tỉnh) -> `truong_chuan`, `truong_tinh`.
Không đoán tỉnh hay tên thật khi chữ không đủ thông tin: để trống chờ người duyệt.
"""
import difflib
import hashlib
import re
import unicodedata

import pandas as pd

from . import config

FILE_CHUAN = config.ROOT / "content" / "school_overrides.csv"
FILE_DS = config.ROOT / "content" / "schools.csv"  # danh sách trường (tạo bằng scripts/import_schools.py)

# Viết tắt trường đại học hay gặp. ĐÂY LÀ GỢI Ý, cần Trang xác nhận.
VIET_TAT_DH = {
    "ueh": "Đại học Kinh tế TP.HCM", "neu": "Đại học Kinh tế Quốc dân", "tdtu": "Đại học Tôn Đức Thắng",
    "fptu": "Đại học FPT", "fpt": "Đại học FPT", "dh fpt": "Đại học FPT", "hutech": "Đại học HUTECH",
    "uah": "Đại học Kiến trúc TP.HCM", "utehy": "Đại học Sư phạm Kỹ thuật Hưng Yên",
}


def bo_dau(text: str) -> str:
    t = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", t).split())


def suy_cap(khoa: str) -> str:
    """Cấp học từ tên đã bỏ dấu. Thứ tự kiểm tra quan trọng (liên cấp trước)."""
    if re.search(r"\b(thcs va thpt|thpt va thcs|lien cap|thcs thpt)\b", khoa):
        return "Liên cấp"
    if re.search(r"\b(thcs|trung hoc co so|cap 2)\b", khoa):
        return "THCS"
    if re.search(r"\b(thpt|trung hoc pho thong|cap 3|chuyen)\b", khoa):
        return "THPT"
    if re.search(r"\b(dai hoc|dh|hoc vien|cao dang|cd|university)\b", khoa) or khoa in VIET_TAT_DH:
        return "Đại học"
    return "Không rõ"


_TIEN_TO = r"^(truong |trung hoc co so |trung hoc pho thong |thcs va thpt |thpt va thcs |thcs thpt |thcs pt |thcs |thpt |dai hoc |hoc vien |dh |cao dang )+"


def tao_khoa(text) -> tuple:
    """Trả (cấp học, khóa so khớp). Khóa = cấp + phần tên đã bỏ tiền tố."""
    if text is None or (isinstance(text, float) and text != text):
        return "Không rõ", ""
    k = bo_dau(text)
    k = re.sub(r"\b(tp hcm|tphcm|tp ho chi minh|hcm)\b", "thanh pho ho chi minh", k)  # viết tắt hay gặp
    cap = suy_cap(k)
    loi = re.sub(_TIEN_TO, "", k).strip()
    return cap, f"{cap}|{loi}" if loi else f"{cap}|"


def doc_bang_chuan() -> pd.DataFrame:
    if FILE_CHUAN.exists():
        return pd.read_csv(FILE_CHUAN, dtype=str, encoding="utf-8-sig").fillna("")
    return pd.DataFrame(columns=["truong_khoa", "truong_chuan", "truong_tinh"])


def them_cot_truong(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm truong_cap, truong_khoa, truong_chuan, truong_tinh vào bảng (cần cột A3)."""
    kq = df["A3"].map(tao_khoa)
    df["truong_cap"] = kq.map(lambda x: x[0])
    df["truong_khoa"] = kq.map(lambda x: x[1])
    chuan = doc_bang_chuan().drop_duplicates("truong_khoa").set_index("truong_khoa")
    df["truong_chuan"] = df["truong_khoa"].map(chuan.get("truong_chuan", pd.Series(dtype=str)))
    df["truong_tinh"] = df["truong_khoa"].map(chuan.get("truong_tinh", pd.Series(dtype=str)))
    return khop_truong(df)


def bang_can_duyet(df: pd.DataFrame) -> pd.DataFrame:
    """Bảng để người duyệt điền: mỗi dòng là một nhóm tên trường, kèm các cách viết gốc."""
    g = (df.assign(goc=df["A3"].astype(str).str.strip())
           .groupby("truong_khoa")
           .agg(truong_cap=("truong_cap", "first"), so_form=("goc", "size"),
                cach_viet=("goc", lambda s: " | ".join(sorted(set(s))[:6])))
           .reset_index().sort_values("so_form", ascending=False))
    g["gop_y"] = g["truong_khoa"].str.split("|").str[1].map(
        lambda c: VIET_TAT_DH.get(c, "") if c else "")
    g["truong_chuan"] = ""
    g["truong_tinh"] = ""
    return g


def chuan_hoa_ds(ds: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa danh sách trường gốc (STT, Tên trường, Tên viết tắt, Cấp) thành bảng dùng để khớp."""
    d = ds.iloc[:, :4].copy()
    d.columns = ["stt", "ten", "viet_tat", "cap"]
    d["ten"] = d["ten"].astype(str).str.strip()

    def cap(c):
        c = str(c)
        if "Liên" in c or "&" in c:
            return "Liên cấp"
        return "Đại học" if "Đại" in c else ("THCS" if "2" in c else "THPT")

    d["cap_chuan"] = d["cap"].map(cap)
    d["khoa"] = d["ten"].map(lambda t: tao_khoa(t)[1].split("|", 1)[1])
    d["key"] = d["cap_chuan"] + "|" + d["khoa"]
    d["id"] = d["ten"].map(lambda t: hashlib.sha1(t.encode()).hexdigest()[:12])
    return d


def doc_ds_truong() -> pd.DataFrame:
    if FILE_DS.exists():
        return pd.read_csv(FILE_DS, dtype=str, encoding="utf-8-sig").fillna("")
    return pd.DataFrame()


NGUONG_GAN_DUNG = 0.90  # từ ngưỡng này: tự thay tên (khop_gan_dung)
NGUONG_DOAN = 0.60      # từ ngưỡng này đến dưới 0.90: vẫn gán tên nhưng đánh dấu khop_doan
TRANG_THAI_DS = ("thu_cong", "khop_1", "khop_cung_ten", "khop_gan_dung", "khop_doan")  # đã gán tên từ danh sách/duyệt tay


def chuan_chu(text) -> str:
    """Giữ chữ người gõ, chỉ gộp khoảng trắng và viết hoa chữ cái đầu mỗi từ."""
    if text is None or pd.isna(text):
        return ""
    return " ".join(w[:1].upper() + w[1:] for w in str(text).split())


def _chi_muc(ds: pd.DataFrame) -> tuple:
    """Dựng bảng tra nhanh từ danh sách trường: theo khóa, theo viết tắt, theo cấp học."""
    theo_key, vt, theo_cap = {}, {}, {}
    for r in ds.itertuples():
        m = (r.id, r.ten, r.cap_chuan)
        theo_key.setdefault(r.key, []).append(m)
        theo_cap.setdefault(r.cap_chuan, []).append((r.khoa, m))
        for ma in re.split(r"[,;/]", r.viet_tat):
            if ma.strip():
                vt.setdefault(bo_dau(ma), []).append(m)
    return theo_key, vt, theo_cap


def _quyet_dinh(cands: list) -> tuple:
    """Một trường -> khop_1. Nhiều trường cùng cấp và cùng tên chuẩn (giống từng chữ, kể cả dấu) -> khop_cung_ten (bỏ id)."""
    if len(cands) == 1:
        return "khop_1", cands[0][1], cands[0][0]
    if len({" ".join(c[1].split()).casefold() for c in cands}) == 1 and len({c[2] for c in cands}) == 1:
        return "khop_cung_ten", cands[0][1], ""
    return "khop_nhieu", "", ""


def _gan_dung(core: str, cap: str, theo_cap: dict) -> tuple:
    """So gần đúng CHỈ trong trường cùng cấp học. Trả (trường giống nhất, độ giống 0-1).
    Nếu nhiều trường giống ngang nhau thì lấy trường đứng trước trong danh sách."""
    if not core or cap not in theo_cap:
        return None, 0.0
    sm = difflib.SequenceMatcher(None)
    sm.set_seq2(core)
    tot, diem = None, 0.0
    for khoa, m in theo_cap[cap]:
        sm.set_seq1(khoa)
        if sm.real_quick_ratio() > diem and sm.quick_ratio() > diem and sm.ratio() > diem:
            tot, diem = m, sm.ratio()
    return tot, diem


def _dung_cap(m: tuple, cap_lop: str) -> bool:
    """Trường (id, tên, cấp) có hợp với cấp học của người trả lời không? Liên cấp hợp với THCS và THPT."""
    return m[2] == cap_lop or (m[2] == "Liên cấp" and cap_lop in ("THCS", "THPT"))


def _theo_viet_tat(r, core: str, cap_lop: str, vt: dict) -> list:
    """Tìm trường theo chữ viết tắt (cột viet_tat), ví dụ HAUI -> Đại học Công nghiệp Hà Nội.
    PHẢI khớp cấp: học sinh THPT ghi HAUI thì không thể là trường đại học. Khi cấp là "Không rõ" (A1 = Khác) thì không lọc.
    1) Cả ô chỉ là một viết tắt. 2) Viết tắt nằm lẫn trong câu dài ("ĐH Công nghiệp HN - HaUI"): chỉ nhận khi ra đúng một trường."""
    loc = lambda ds: [m for m in ds if cap_lop == "Không rõ" or _dung_cap(m, cap_lop)]
    if loc(vt.get(core, [])):
        return loc(vt[core])
    thu = [loc(vt[t]) for t in str(bo_dau(r.get("A3", ""))).split() if len(t) >= 3 and t in vt]
    thu = [x for x in thu if len(x) == 1]
    return thu[0] if len(thu) == 1 else []


def _tim_ds(r, idx: tuple) -> tuple:
    """Tìm trường cho một dòng: trả (trạng thái, tên, id, độ giống). Khớp chắc thì độ giống = 1."""
    theo_key, vt, theo_cap = idx
    core = r["truong_khoa"].split("|", 1)[1] if "|" in r["truong_khoa"] else ""
    cap_lop = r["cap_hoc"]                       # cấp học tính từ lớp: chuẩn để so khớp
    lien_cap = theo_key.get(f"Liên cấp|{core}", [])
    if r["truong_cap"] == "Liên cấp":            # người dùng ghi rõ liên cấp
        cands = lien_cap
    else:                                        # lớp 6-9 -> THCS, lớp 10-12 -> THPT
        cands = theo_key.get(f"{cap_lop}|{core}") or lien_cap
    if not cands:
        cands = _theo_viet_tat(r, core, cap_lop, vt)
    tt, ten, ma = _quyet_dinh(cands) if cands else ("khop_nhieu", "", "")
    if tt != "khop_nhieu":
        return tt, ten, ma, 1.0
    m, diem = _gan_dung(core, cap_lop, theo_cap)  # không khớp / trùng khác tên: so gần đúng cùng cấp
    if m is None or diem < NGUONG_DOAN:
        return "chua_chuan_hoa", "", "", diem
    return ("khop_gan_dung" if diem >= NGUONG_GAN_DUNG else "khop_doan"), m[1], m[0], diem


def khop_truong(df: pd.DataFrame, ds: pd.DataFrame | None = None) -> pd.DataFrame:
    """Chuẩn hóa tên trường (không duyệt tay). Kết quả truong_khop:
    thu_cong (có trong overrides), khop_1, khop_cung_ten (nhiều trường cùng cấp, cùng tên),
    khop_gan_dung (giống nhất >= 0.90), khop_doan (0.60 đến dưới 0.90, vẫn gán tên),
    chua_chuan_hoa (dưới 0.60: giữ chữ người gõ, chỉ chuẩn hóa khoảng trắng và viết hoa).
    truong_chuan luôn có tên dùng để báo cáo; truong_do_giong là độ giống 0-1."""
    ds = doc_ds_truong() if ds is None else ds
    idx = _chi_muc(ds)

    def tim(r):
        tc = r.get("truong_chuan")
        if isinstance(tc, str) and tc:  # ô trống (NaN) không tính là đã duyệt
            return "thu_cong", tc, "", 1.0
        tt, ten, ma, diem = _tim_ds(r, idx)
        return (tt, chuan_chu(r.get("A3")), "", diem) if tt == "chua_chuan_hoa" else (tt, ten, ma, diem)

    df["truong_mau_thuan_cap"] = (df["truong_cap"].isin(["THCS", "THPT", "Đại học"])
                                  & (df["truong_cap"] != df["cap_hoc"]))
    kq = df.apply(tim, axis=1, result_type="expand")
    df["truong_khop"], df["truong_chuan"], df["truong_ds_id"], df["truong_do_giong"] = kq[0], kq[1], kq[2], kq[3]
    df["truong_do_giong"] = df["truong_do_giong"].astype(float).round(4)
    df["truong_ds_ten"] = df["truong_chuan"].where(df["truong_khop"].isin(TRANG_THAI_DS), "")
    return df
