"""Vẽ hình SHAP cho notebook 04: cột ngang tầm quan trọng, beeswarm, biểu đồ phụ thuộc.

Mọi hình dùng nhãn tiếng Việt (content/feature_labels.json) và giá trị GỐC của biến (thang 1–5 cho B4, không đảo chiều).
Mỗi hình có 1 dòng chú thích cách đọc ở dưới.
"""
import re

import matplotlib
matplotlib.use("Agg")   # vẽ ra file, không cần cửa sổ
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap


def _luu(fig, chu_thich: str, duong_dan):
    """Ghi chú thích 1 dòng ở đáy hình rồi lưu và đóng."""
    fig.text(0.5, 0.005, chu_thich, ha="center", va="bottom", fontsize=8, style="italic", wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(duong_dan, dpi=150); plt.close(fig)


def ve_cot_ngang(cac_bang: list, nhan: dict, chu_thich: str, duong_dan, top: int = 15):
    """Cột ngang tầm quan trọng (trung bình |SHAP|), top biến đầu. cac_bang = [(tiêu đề, bảng 'bien' + cột điểm, tên cột điểm), ...]."""
    fig, axs = plt.subplots(1, len(cac_bang), figsize=(6.2 * len(cac_bang), 5.6), squeeze=False)
    for ax, (tieu_de, bang, cot) in zip(axs[0], cac_bang):
        d = bang.sort_values(cot, ascending=False).head(top).iloc[::-1]       # đảo để biến mạnh nhất nằm trên cùng
        ax.barh([nhan.get(b, b) for b in d["bien"]], d[cot], color="#4C78A8")
        ax.set(title=tieu_de, xlabel="Trung bình |SHAP| (càng lớn càng ảnh hưởng nhiều đến dự đoán)")
    _luu(fig, chu_thich, duong_dan)


def _viet_hoa_beeswarm(fig):
    """Đổi chữ tiếng Anh shap tự sinh: thanh màu (Feature value, High, Low) và dòng 'Sum of N other features'."""
    ax, *phu = fig.axes
    nhan = [t.get_text() for t in ax.get_yticklabels()]
    ax.set_yticks(ax.get_yticks(), [re.sub(r"Sum of (\d+) other features", r"Tổng của \1 biến còn lại", t) for t in nhan])
    for cb in phu:                                   # thanh màu bên phải
        cb.set_ylabel("Giá trị câu trả lời (thấp → cao)")
        cb.set_yticks([cb.get_ylim()[0], cb.get_ylim()[1]], ["Thấp", "Cao"])


def ve_beeswarm(sv: np.ndarray, Xm: pd.DataFrame, nhan: dict, tieu_de: str, chu_thich: str, duong_dan, top: int = 15):
    """Beeswarm: mỗi chấm là một người; trục ngang là SHAP (phải = đẩy dự đoán lên), màu là giá trị gốc của biến."""
    ten = [nhan.get(c, c) for c in Xm.columns]
    ex = shap.Explanation(values=sv, data=Xm.to_numpy(dtype=float), feature_names=ten)
    fig = plt.figure(figsize=(9, 6.5))
    shap.plots.beeswarm(ex, max_display=top, show=False)
    plt.gca().set_title(tieu_de); plt.xlabel("Tác động lên dự đoán (phải: đẩy lên, trái: đẩy xuống)")
    _viet_hoa_beeswarm(plt.gcf())
    _luu(plt.gcf(), chu_thich, duong_dan)


def ve_phu_thuoc(sv: np.ndarray, Xm: pd.DataFrame, cac_bien: list, nhan: dict, tieu_de: str, chu_thich: str, duong_dan):
    """Biểu đồ phụ thuộc: với mỗi biến, trục ngang là giá trị gốc, trục dọc là SHAP; đường đỏ là trung bình theo giá trị."""
    fig, axs = plt.subplots(1, len(cac_bien), figsize=(4.8 * len(cac_bien), 4.4), squeeze=False)
    rng = np.random.default_rng(0)                                           # rung nhẹ ngang để các chấm không chồng nhau
    for ax, b in zip(axs[0], cac_bien):
        x, y = Xm[b].to_numpy(dtype=float), sv[:, list(Xm.columns).index(b)]
        ax.scatter(x + rng.uniform(-0.12, 0.12, len(x)), y, s=14, alpha=0.5, color="#4C78A8")
        tb = pd.Series(y).groupby(x).mean()
        ax.plot(tb.index, tb.values, color="#E45756", marker="o", linewidth=1.5)
        ax.axhline(0, color="grey", linewidth=0.7)
        ax.set(title=nhan.get(b, b), xlabel="Giá trị gốc của biến (B4: 1–5)", ylabel="Tác động lên dự đoán (SHAP)")
    fig.suptitle(tieu_de)
    _luu(fig, chu_thich, duong_dan)
