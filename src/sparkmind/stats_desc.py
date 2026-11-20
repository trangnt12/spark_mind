"""Hàm thống kê mô tả cho notebook 02 (bảng T1, T3, T4, T5).
Chỉ TÍNH trên bảng đã làm sạch; không làm sạch lại (việc đó ở cleaning.py)."""
import numpy as np
import pandas as pd
from scipy import stats

from .columns import B4, CC, NEG

MIN_N_NHOM = 5   # nhóm ít hơn 5 người thì bỏ khỏi phép so sánh (ghi rõ trong bảng)
BIEN_TUONG_QUAN = B4 + ["B2_so", "B5_so", "diem_hanh_vi", "diem_sang_tao"]
NHAN_B1 = {"B1_chatgpt": "ChatGPT", "B1_gemini": "Gemini", "B1_copilot": "Copilot", "B1_claude": "Claude"}
THU_TU_B2 = ["Rất hiếm khi", "Vài lần/tháng", "Vài lần/tuần", "Hầu như mỗi ngày"]
THU_TU_B5 = ["Dưới 5 phút", "5–15 phút", "15–30 phút", "Trên 30 phút"]


def _dem(df: pd.DataFrame, cot: str, thu_tu=None) -> pd.DataFrame:
    """Đếm số người và % theo một cột chữ."""
    vc = df[cot].value_counts(dropna=False)
    if thu_tu:
        vc = vc.reindex(thu_tu + [x for x in vc.index if x not in thu_tu]).dropna()
    return pd.DataFrame({"nhom": vc.index.astype(str), "so_nguoi": vc.values.astype(int),
                         "ty_le_%": (vc.values / len(df) * 100).round(1)})


def bang_mo_ta_mau(df: pd.DataFrame) -> pd.DataFrame:
    """T1: số người theo cấp học, giới tính, công cụ AI, tần suất, thời gian, đợt thu."""
    khoi = [("Cấp học", _dem(df, "cap_hoc")), ("Giới tính", _dem(df, "A2")),
            ("Tần suất dùng AI (B2)", _dem(df, "B2", THU_TU_B2)),
            ("Thời gian mỗi lần (B5)", _dem(df, "B5", THU_TU_B5)), ("Đợt thu", _dem(df, "dot"))]
    ai = pd.DataFrame({"nhom": list(NHAN_B1.values()), "so_nguoi": [int(df[c].sum()) for c in NHAN_B1],
                       "ty_le_%": [round(df[c].mean() * 100, 1) for c in NHAN_B1]})
    khoi.insert(2, ("Công cụ AI (B1, chọn nhiều nên tổng > 100%)", ai))
    ra = [k.assign(bien=ten) for ten, k in khoi]
    return pd.concat(ra)[["bien", "nhom", "so_nguoi", "ty_le_%"]].reset_index(drop=True)


def cronbach_alpha(items: pd.DataFrame) -> tuple[float, int]:
    """Cronbach's alpha trên các dòng đủ mọi câu. Trả (alpha, số dòng dùng)."""
    x = items.dropna()
    k = x.shape[1]
    tong_phuong_sai = x.var(ddof=1).sum()
    return float(k / (k - 1) * (1 - tong_phuong_sai / x.sum(axis=1).var(ddof=1))), len(x)


def bang_alpha(df: pd.DataFrame) -> pd.DataFrame:
    """T3: alpha của C1–C5 và của B4 (đã đảo B4_3, B4_6)."""
    dao = df[B4].copy()
    for c in NEG:
        dao[c] = 6 - dao[c]
    ra = []
    for ten, x in [("Sáng tạo tự đánh giá (C1–C5)", df[CC]), ("Hành vi dùng AI (B4_1..B4_7, đảo B4_3, B4_6)", dao)]:
        a, n = cronbach_alpha(x)
        ra.append({"thang_do": ten, "so_cau": x.shape[1], "co_mau": n, "alpha": round(a, 3)})
    return pd.DataFrame(ra)


def _hieu_ung_kw(h: float, n: int, k: int) -> float:
    """Epsilon bình phương cho Kruskal-Wallis (0 = không khác, 1 = khác hoàn toàn)."""
    return max(0.0, (h - k + 1) / (n - k))


def so_sanh_nhom(df: pd.DataFrame, cot: str, y: str = "diem_sang_tao") -> dict:
    """So sánh điểm y giữa các nhóm của cột cot. 2 nhóm: Mann-Whitney; từ 3 nhóm: Kruskal-Wallis."""
    nhom = {g: s.dropna().values for g, s in df.groupby(cot)[y] if s.notna().sum() >= MIN_N_NHOM}
    bo = [str(g) for g, s in df.groupby(cot)[y] if s.notna().sum() < MIN_N_NHOM]
    mo_ta = "; ".join(f"{g}: n={len(v)}, trung vị={np.median(v):.1f}" for g, v in nhom.items())
    ra = {"bien_nhom": cot, "so_nhom": len(nhom), "mo_ta_nhom": mo_ta, "nhom_bi_bo": ", ".join(bo)}
    n = sum(len(v) for v in nhom.values())
    if len(nhom) == 2:
        a, b = nhom.values()
        u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        ra.update(phep_thu="Mann-Whitney U", thong_ke=u, p=p, ten_hieu_ung="rank-biserial r",
                  hieu_ung=1 - 2 * u / (len(a) * len(b)))
    elif len(nhom) >= 3:
        h, p = stats.kruskal(*nhom.values())
        ra.update(phep_thu="Kruskal-Wallis H", thong_ke=h, p=p, ten_hieu_ung="epsilon bình phương",
                  hieu_ung=_hieu_ung_kw(h, n, len(nhom)))
    ra["n"] = n
    return ra


def holm(p) -> np.ndarray:
    """Hiệu chỉnh Holm-Bonferroni cho một nhóm p-value (nhóm = các phép thử trong cùng một bảng)."""
    p = np.asarray(p, dtype=float)
    thu_tu = np.argsort(p)
    m = len(p)
    dieu_chinh = np.minimum(1.0, (m - np.arange(m)) * p[thu_tu])
    dieu_chinh = np.maximum.accumulate(dieu_chinh)   # giữ thứ tự không giảm
    ra = np.empty(m)
    ra[thu_tu] = dieu_chinh
    return ra


def bang_so_sanh(df: pd.DataFrame) -> pd.DataFrame:
    """T4: so sánh điểm sáng tạo theo cấp học, giới tính, tần suất dùng AI (có p_holm)."""
    t = pd.DataFrame([so_sanh_nhom(df, c) for c in ("cap_hoc", "A2", "B2")])
    t["p_holm"] = holm(t["p"])
    cot = ["bien_nhom", "so_nhom", "n", "phep_thu", "thong_ke", "p", "p_holm", "ten_hieu_ung", "hieu_ung",
           "mo_ta_nhom", "nhom_bi_bo"]
    return t[cot].round({"thong_ke": 3, "p": 6, "p_holm": 6, "hieu_ung": 3})


def bang_tuong_quan(df: pd.DataFrame) -> pd.DataFrame:
    """T5: Spearman từng cặp biến (dạng dài: hệ số, p, p_holm, số quan sát)."""
    ra = []
    for i, a in enumerate(BIEN_TUONG_QUAN):
        for b in BIEN_TUONG_QUAN[i + 1:]:
            x = df[[a, b]].dropna()
            rho, p = stats.spearmanr(x[a], x[b])
            ra.append({"bien_1": a, "bien_2": b, "rho": rho, "p": p, "n": len(x)})
    t = pd.DataFrame(ra)
    t.insert(4, "p_holm", holm(t["p"]))   # Holm trên cả bảng (55 cặp)
    return t.round({"rho": 3, "p": 6, "p_holm": 6})


MIN_N_DOT = 10   # đợt dưới 10 người: không tính rho, chỉ ghi chú
CAP_BIEN_DOT = [("diem_hanh_vi", "Điểm hành vi (B4 tổng)"), ("B4_3", "B4_3 (câu đảo chiều)")]


def bang_tuong_quan_theo_dot(df: pd.DataFrame) -> pd.DataFrame:
    """T5b: Spearman (điểm hành vi, B4_3) với điểm sáng tạo, tách theo đợt thu (cột dot)."""
    ra = []
    for dot, g in df.groupby("dot"):
        for cot, ten in CAP_BIEN_DOT:
            x = g[[cot, "diem_sang_tao"]].dropna()
            d = {"dot": dot, "bien": ten, "n": len(x), "rho": np.nan, "p": np.nan, "ghi_chu": ""}
            if len(x) >= MIN_N_DOT:
                d["rho"], d["p"] = stats.spearmanr(x[cot], x["diem_sang_tao"])
            else:
                d["ghi_chu"] = f"n<{MIN_N_DOT}, không tính"
            ra.append(d)
    t = pd.DataFrame(ra)
    t["p_holm"] = np.nan
    co = t["p"].notna()
    t.loc[co, "p_holm"] = holm(t.loc[co, "p"])
    t = t[["dot", "bien", "n", "rho", "p", "p_holm", "ghi_chu"]]
    return t.round({"rho": 3, "p": 6, "p_holm": 6})


def ma_tran_rho(t5: pd.DataFrame) -> pd.DataFrame:
    """Đổi bảng dài T5 thành ma trận vuông hệ số rho (để vẽ heatmap)."""
    m = pd.DataFrame(np.eye(len(BIEN_TUONG_QUAN)), index=BIEN_TUONG_QUAN, columns=BIEN_TUONG_QUAN)
    for r in t5.itertuples():
        m.loc[r.bien_1, r.bien_2] = m.loc[r.bien_2, r.bien_1] = r.rho
    return m
