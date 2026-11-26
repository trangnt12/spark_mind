"""Độ đồng thuận giữa hai người chấm: Cohen's kappa (nhóm công dụng game 1), kappa có trọng số bậc hai (điểm game 3), bảng chéo, mục lệch.

Tự cài đặt (không cần scikit-learn trên server); tests/test_rating_agreement.py đối chiếu với sklearn.metrics.cohen_kappa_score.
Chỉ tính các mục CẢ HAI người đã chấm xong (hoan_tat). Game 3: bỏ cặp có X ở tiêu chí đó. Game 1: X tính như một nhóm.
"""
from . import config, rating_content as nd
from .rating_store import COL_DIEM, COL_MUC

X = nd.X


def ma_tran_cheo(cap: list, nhan: list) -> list:
    """Bảng chéo: hàng = người A, cột = người B, theo thứ tự `nhan`. cap = [(a, b), ...]."""
    vi_tri = {n: i for i, n in enumerate(nhan)}
    m = [[0] * len(nhan) for _ in nhan]
    for a, b in cap:
        m[vi_tri[a]][vi_tri[b]] += 1
    return m


def ti_le_dong_y(cap: list) -> float | None:
    return sum(1 for a, b in cap if a == b) / len(cap) if cap else None


def kappa(cap: list, nhan: list, trong_so: str | None = None) -> float | None:
    """Cohen's kappa. trong_so=None: không trọng số; "quadratic": trọng số bậc hai theo thứ tự `nhan`. Trả None khi không xác định (mẫu rỗng hoặc mẫu số 0)."""
    if not cap:
        return None
    n, k, m = len(cap), len(nhan), ma_tran_cheo(cap, nhan)
    hang = [sum(r) for r in m]
    cot = [sum(m[i][j] for i in range(k)) for j in range(k)]
    tu = mau = 0.0
    for i in range(k):
        for j in range(k):
            w = 0.0 if i == j else ((i - j) ** 2 / (k - 1) ** 2 if trong_so == "quadratic" else 1.0)
            tu += w * m[i][j] / n
            mau += w * hang[i] * cot[j] / n ** 2
    return None if mau == 0 else 1 - tu / mau


def _cap_cham_xong(db, ten_dot: str, a: str, b: str) -> list:
    """[(mục, điểm A, điểm B)] cho mục cả hai đã chấm xong, theo thứ tự thu_tu."""
    diem = {}
    for r in db[COL_DIEM].find({"rating_batch": ten_dot, "rater": {"$in": [a, b]}, "hoan_tat": True}):
        diem.setdefault(r["item_code"], {})[r["rater"]] = r["diem"]
    muc = db[COL_MUC].find({"rating_batch": ten_dot, "item_code": {"$in": [c for c, d in diem.items() if len(d) == 2]}}).sort("thu_tu", 1)
    return [(m, diem[m["item_code"]][a], diem[m["item_code"]][b]) for m in muc]


def _game1(cap: list, toi_thieu: int) -> dict:
    nhan = nd.ma_nhom_game1()
    ab = [(da["nhom"], db_["nhom"]) for m, da, db_ in cap if m["game"] == 1]
    if len(ab) < toi_thieu:
        return {"du_du_lieu": False, "so_muc": len(ab)}
    return {"du_du_lieu": True, "so_muc": len(ab), "kappa": kappa(ab, nhan), "dong_y_tho": ti_le_dong_y(ab),
            "nhan": nhan, "bang_cheo": ma_tran_cheo(ab, nhan)}


def _mot_tieu_chi(cap: list, ma: str, toi_thieu: int) -> dict:
    thang = nd.thang_diem_game3()
    ab = [(da[ma], db_[ma]) for m, da, db_ in cap if m["game"] == 3 and X not in (da[ma], db_[ma])]
    if len(ab) < toi_thieu:
        return {"du_du_lieu": False, "so_muc": len(ab)}
    return {"du_du_lieu": True, "so_muc": len(ab), "kappa_trong_so": kappa(ab, thang, "quadratic"),
            "dong_y_tho": ti_le_dong_y(ab), "nhan": thang, "bang_cheo": ma_tran_cheo(ab, thang)}


def _game3(cap: list, toi_thieu: int) -> dict:
    tc = {ma: _mot_tieu_chi(cap, ma, toi_thieu) for ma in nd.ma_tieu_chi_game3()}
    k = [t["kappa_trong_so"] for t in tc.values() if t.get("kappa_trong_so") is not None]
    return {"tieu_chi": tc, "trung_binh": sum(k) / len(k) if k else None}


def _lech_game1(da: dict, db_: dict) -> bool:
    return da["nhom"] != db_["nhom"]


def _lech_game3(da: dict, db_: dict) -> bool:
    for ma in nd.ma_tieu_chi_game3():
        x, y = da[ma], db_[ma]
        if (x == X) != (y == X) or (x != X and abs(x - y) >= config.RATING_NGUONG_LECH_GAME3):
            return True
    return False


def muc_lech(cap: list) -> list:
    """Các mục hai người lệch nhau (game 1: khác nhóm; game 3: xem RATING_NGUONG_LECH_GAME3), kèm điểm hai bên và nội dung."""
    kq = []
    for m, da, db_ in cap:
        if (_lech_game1 if m["game"] == 1 else _lech_game3)(da, db_):
            kq.append({"item_code": m["item_code"], "game": m["game"], "noi_dung": m["noi_dung"], "diem_a": da, "diem_b": db_})
    return kq


def do_dong_thuan(db, ten_dot: str, rater_a: str, rater_b: str, toi_thieu: int | None = None) -> dict:
    """Toàn bộ báo cáo đồng thuận của một đợt cho hai người chấm."""
    toi_thieu = config.RATING_MUC_TOI_THIEU_KAPPA if toi_thieu is None else toi_thieu
    cap = _cap_cham_xong(db, ten_dot, rater_a, rater_b)
    return {"rating_batch": ten_dot, "raters": [rater_a, rater_b], "toi_thieu": toi_thieu, "toi_thieu_mac_dinh": config.RATING_MUC_TOI_THIEU_KAPPA, "nguong_lech_game3": config.RATING_NGUONG_LECH_GAME3, "so_muc_ca_hai_cham": len(cap),
            "game1": _game1(cap, toi_thieu), "game3": _game3(cap, toi_thieu), "muc_lech": muc_lech(cap)}
