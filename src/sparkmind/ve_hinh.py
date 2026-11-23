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


# Bảng màu Okabe-Ito: dễ phân biệt, kể cả người khó nhìn màu
MAU_MO_HINH = ["#999999", "#56B4E9", "#E69F00", "#009E73", "#D55E00"]


def ve_boxplot_macro_f1(folds: pd.DataFrame, tieu_de: str, duong_dan):
    """Boxplot macro-F1 theo mô hình (mỗi điểm là một fold; chấm đen là trung bình)."""
    ten = list(dict.fromkeys(folds["mo_hinh"]))
    du_lieu = [folds.loc[folds["mo_hinh"] == t, "macro_f1"] for t in ten]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    hop = ax.boxplot(du_lieu, tick_labels=ten, patch_artist=True, showmeans=True, widths=0.6,
                     medianprops={"color": "black"},
                     meanprops={"marker": "o", "markerfacecolor": "black", "markeredgecolor": "black"})
    for o, m in zip(hop["boxes"], MAU_MO_HINH):
        o.set_facecolor(m)
    ax.axhline(1 / 3, color="#D55E00", linestyle=":", linewidth=1)
    ax.text(0.5, 1 / 3 + 0.005, "đoán ngẫu nhiên ≈ 0.33", fontsize=7, color="#D55E00")
    ax.set(title=tieu_de, ylabel="Macro-F1 theo fold (5 lớp × 10 lần lặp)")
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    fig.tight_layout(); fig.savefig(duong_dan, dpi=150); plt.close(fig)


def ve_cot_lobo(t7: pd.DataFrame, tieu_de: str, duong_dan):
    """Cột macro-F1 theo đợt thử (leave-one-batch-out), mỗi mô hình một màu, ghi n_thu dưới tên đợt."""
    t = t7.dropna(subset=["macro_f1"])
    dots = list(dict.fromkeys(t["dot_thu"]))
    ten = list(dict.fromkeys(t["mo_hinh"]))
    rong = 0.8 / len(ten)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for k, m in enumerate(ten):
        d = t[t["mo_hinh"] == m].set_index("dot_thu").reindex(dots)
        ax.bar(np.arange(len(dots)) + k * rong, d["macro_f1"], rong, label=m, color=MAU_MO_HINH[k % 5])
    nhan = [f"{d}\n(n thử={int(t.loc[t['dot_thu'] == d, 'n_thu'].iloc[0])})" for d in dots]
    ax.set_xticks(np.arange(len(dots)) + rong * (len(ten) - 1) / 2, nhan)
    ax.axhline(1 / 3, color="#D55E00", linestyle=":", linewidth=1)
    ax.set(title=tieu_de, ylabel="Macro-F1 trên đợt bị giữ lại")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(duong_dan, dpi=150); plt.close(fig)


def ve_cot_ablation(tom_tat: pd.DataFrame, chi_so: str, tieu_de: str, duong_dan):
    """Hình cột ngang: chỉ số (macro_f1 hoặc r2) theo cấu hình bỏ nhóm biến, mỗi mô hình một màu.

    tom_tat: cột cau_hinh, mo_hinh, <chi_so>_tb. Số ghi ở đầu cột để đọc trực tiếp.
    """
    ch = list(dict.fromkeys(tom_tat["cau_hinh"])); mh = list(dict.fromkeys(tom_tat["mo_hinh"]))
    fig, ax = plt.subplots(figsize=(8, 5)); rong = 0.8 / len(mh)
    for k, m in enumerate(mh):
        v = tom_tat[tom_tat["mo_hinh"] == m].set_index("cau_hinh").reindex(ch)[f"{chi_so}_tb"]
        y = np.arange(len(ch)) + k * rong
        ax.barh(y, v, rong, label=m, color=MAU_MO_HINH[1 + k])
        for yi, x in zip(y, v):
            ax.text(x + 0.005 if x >= 0 else 0.005, yi, f"{x:.2f}", va="center", fontsize=7)
    ax.set_yticks(np.arange(len(ch)) + rong * (len(mh) - 1) / 2, ch); ax.invert_yaxis()
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set(title=tieu_de, xlabel=chi_so); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(duong_dan, dpi=150); plt.close(fig)
