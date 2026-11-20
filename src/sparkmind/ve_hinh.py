"""Vẽ hình cho notebook 02: histogram điểm sáng tạo và heatmap tương quan."""
import matplotlib
matplotlib.use("Agg")   # vẽ ra file, không cần cửa sổ
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .columns import NGUONG_CAO, NGUONG_THAP


def ve_histogram(diem: pd.Series, tieu_de: str, duong_dan):
    """Histogram điểm sáng tạo 0–100, kẻ 2 vạch ngưỡng chia mức (60 và 80)."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(diem.dropna(), bins=np.arange(0, 105, 5), color="#4C78A8", edgecolor="white")
    for nguong in (NGUONG_THAP, NGUONG_CAO):
        ax.axvline(nguong, color="#E45756", linestyle="--", linewidth=1)
    ax.set(title=f"{tieu_de} (n={diem.notna().sum()})", xlabel="Điểm sáng tạo tự đánh giá (0–100)", ylabel="Số người")
    fig.tight_layout(); fig.savefig(duong_dan, dpi=150); plt.close(fig)


def ve_heatmap(ma_tran: pd.DataFrame, tieu_de: str, duong_dan):
    """Heatmap Spearman rho, ghi số vào từng ô; thang màu cố định từ -1 đến 1."""
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(ma_tran.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ten = list(ma_tran.columns)
    ax.set_xticks(range(len(ten)), ten, rotation=60, ha="right"); ax.set_yticks(range(len(ten)), ten)
    for i in range(len(ten)):
        for j in range(len(ten)):
            ax.text(j, i, f"{ma_tran.iat[i, j]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="Hệ số Spearman")
    ax.set_title(tieu_de)
    fig.tight_layout(); fig.savefig(duong_dan, dpi=150); plt.close(fig)


def ve_rho_theo_dot(t5b: pd.DataFrame, tieu_de: str, duong_dan):
    """Hình cột: rho theo đợt thu, mỗi biến một màu, ghi n trên đầu cột. Đợt không tính rho bị bỏ."""
    t = t5b.dropna(subset=["rho"])
    dots = list(dict.fromkeys(t["dot"]))
    bien = list(dict.fromkeys(t["bien"]))
    fig, ax = plt.subplots(figsize=(7, 4))
    rong = 0.8 / len(bien)
    for k, b in enumerate(bien):
        d = t[t["bien"] == b].set_index("dot").reindex(dots)
        x = np.arange(len(dots)) + k * rong
        ax.bar(x, d["rho"], rong, label=b, color=["#4C78A8", "#F58518"][k % 2])
        for xi, r, n in zip(x, d["rho"], d["n"]):
            ax.text(xi, r + (0.02 if r >= 0 else -0.06), f"n={int(n)}", ha="center", fontsize=7)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(np.arange(len(dots)) + rong * (len(bien) - 1) / 2, dots)
    ax.set(title=tieu_de, ylabel="Hệ số Spearman với điểm sáng tạo")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(duong_dan, dpi=150); plt.close(fig)
