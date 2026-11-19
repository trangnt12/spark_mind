"""Làm sạch dữ liệu khảo sát: mã hóa số, tính điểm, gắn cờ chất lượng.

Mọi cờ đều tính RIÊNG TỪNG FORM (không phụ thuộc form khác), nên một form mới
được làm sạch ngay khi nộp và cho kết quả giống hệt làm sạch cả bảng.
Hàm không xóa form nào: chỉ gắn cờ và cột in_chinh / in_chat / in_rat_chat.
"""
import re

import numpy as np
import pandas as pd

from .school_matching import them_cot_truong
from .columns import (B1_KW, B3_KW, B4, B6_KW, B7_KW, CC, DOT_MAC_DINH_SAU, DOT_RULES,
                      NEG, NGAY_CUOI_DOT3, NGUONG_CAO, NGUONG_THAP, ORD2, ORD5, RAW_KEYS)

VERSIONS = ("chinh", "chat", "rat_chat")


def gan_dot(df: pd.DataFrame) -> pd.Series:
    """Gán đợt thu theo ngày; form từ web có đợt riêng 'web'."""
    ngay = pd.to_datetime(df["thoi_gian"]).dt.strftime("%Y-%m-%d")
    # mặc định: sau ngày cuối đợt 3 là đợt mới, trước đó mà không khớp luật là 'dot_khac'
    dot = pd.Series(np.where(ngay > NGAY_CUOI_DOT3, DOT_MAC_DINH_SAU, "dot_khac"), index=df.index)
    for ten, tu, den in DOT_RULES:
        dot[(ngay >= tu) & (ngay <= den)] = ten
    if "nguon" in df:
        dot[df["nguon"] == "web"] = "web"
    return dot


def _lop(text) -> float:
    m = re.search(r"Lớp (\d+)", str(text))
    if m:
        return int(m.group(1))
    m = re.search(r"Năm (\d) Đại học", str(text))
    return 12 + int(m.group(1)) if m else np.nan


def _nhieu(df: pd.DataFrame, cot: str, kw: dict) -> None:
    """Câu chọn nhiều: mỗi phương án một cột 0/1 và một cột đếm số phương án."""
    ten = []
    for ten_cot, tu_khoa in kw.items():
        c = f"{cot}_{ten_cot}"
        df[c] = df[cot].astype("string").str.contains(tu_khoa, regex=False).astype(float).where(df[cot].notna())
        ten.append(c)
    df[f"{cot}_so"] = df[ten].sum(axis=1, min_count=1)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Nhận bảng gốc (khóa chuẩn trong RAW_KEYS) và trả bảng đã làm sạch."""
    df = raw.copy()
    for k in RAW_KEYS:                      # thiếu cột nào thì thêm cột trống
        if k not in df:
            df[k] = np.nan
    df["thoi_gian"] = pd.to_datetime(df["thoi_gian"])
    df["dot"] = gan_dot(df)

    # --- điểm ---
    for c in B4 + CC:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["diem_sang_tao"] = (df[CC].sum(axis=1, min_count=5) - 5) / 20 * 100
    dao = df[B4].copy()
    for c in NEG:
        dao[c] = 6 - dao[c]
    df["diem_hanh_vi"] = dao.mean(axis=1)
    df["muc"] = pd.cut(df["diem_sang_tao"], [-1, NGUONG_THAP, NGUONG_CAO, 101], right=False,
                       labels=["Thap", "Trung_binh", "Cao"]).astype(object)

    # --- cờ chất lượng ---
    df["dung_ai"] = df["A4"].astype(str).str.startswith("Có")
    bb = df[B4].notna().all(axis=1)
    cc_du = df[CC].notna().all(axis=1)
    df["du_lieu_day_du"] = bb & cc_du
    df["co_mot_muc_12"] = bb & cc_du & (df[B4 + CC].nunique(axis=1) == 1)
    df["co_mot_muc_C"] = cc_du & (df[CC].nunique(axis=1) == 1)
    df["co_mot_muc_B"] = bb & (df[B4].nunique(axis=1) == 1)
    df["co_mau_thuan"] = (df["B4_3"] >= 4) & (df["B4_4"] >= 4)

    # --- mã hóa chữ thành số ---
    df["B2_so"] = df["B2"].map(ORD2)
    df["B5_so"] = df["B5"].map(ORD5)
    c6 = df["C6"].astype(str)
    df["C6_so"] = np.select([c6.str.startswith("Chưa"), c6.str.startswith("Có tham gia"),
                             c6.str.startswith("Đã từng và")], [0, 1, 2], default=-1).astype(float)
    df.loc[df["C6"].isna(), "C6_so"] = np.nan
    df["lop_so"] = df["A1"].map(_lop)
    df["A2_nu"] = (df["A2"] == "Nữ").astype(int)
    df["A2_khac"] = (df["A2"] == "Khác").astype(int)
    for cot, kw in (("B1", B1_KW), ("B3", B3_KW), ("B6", B6_KW), ("B7", B7_KW)):
        _nhieu(df, cot, kw)
    df = df.drop(columns=["B7_so"])

    # --- ba bản dữ liệu (chỉ người dùng AI, đủ dữ liệu) ---
    nen = df["dung_ai"] & df["du_lieu_day_du"]
    df["in_chinh"] = nen & ~df["co_mot_muc_12"]
    df["in_chat"] = df["in_chinh"] & ~(df["co_mot_muc_C"] | df["co_mot_muc_B"])
    df["in_rat_chat"] = df["in_chat"] & ~df["co_mau_thuan"]
    # cấp học tính từ lớp (A1): đủ 100% và đáng tin hơn đoán từ tên trường
    df["cap_hoc"] = np.select([df["lop_so"] <= 9, df["lop_so"] <= 12, df["lop_so"] > 12],
                              ["THCS", "THPT", "Đại học"], default="Không rõ")
    return them_cot_truong(df)


def lay_ban(df_sach: pd.DataFrame, ten: str) -> pd.DataFrame:
    """Lấy một trong ba bản: 'chinh', 'chat', 'rat_chat'."""
    if ten not in VERSIONS:
        raise ValueError(f"Bản phải là một trong {VERSIONS}")
    return df_sach[df_sach[f"in_{ten}"]]


def bang_loc_form(df_sach: pd.DataFrame) -> pd.DataFrame:
    """Bảng T2: số form còn lại ở từng bước lọc."""
    so = [len(df_sach), int(df_sach["dung_ai"].sum()), int(df_sach["in_chinh"].sum()),
          int(df_sach["in_chat"].sum()), int(df_sach["in_rat_chat"].sum())]
    t2 = pd.DataFrame({
        "buoc": ["Tổng số form", "Chỉ giữ người dùng AI",
                 "Bỏ form chọn một mức cho cả 12 câu (bản chính)",
                 "Bỏ thêm form chọn một mức riêng cho B hoặc C (bản chặt)",
                 "Bỏ thêm form mâu thuẫn (bản rất chặt)"],
        "con_lai": so})
    t2["bi_loai"] = (t2["con_lai"].shift(1) - t2["con_lai"]).fillna(0).astype(int)
    return t2
