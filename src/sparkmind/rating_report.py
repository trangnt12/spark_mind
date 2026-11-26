"""Báo cáo cho trang quản trị chấm: danh sách đợt, mục, tiến độ, xem câu trả lời cạnh điểm hai người chấm, xuất CSV."""
import csv
import io

from . import rating_content as nd
from .admin_view import _chong_cong_thuc
from .rating_store import COL_DIEM, COL_DOT, COL_MUC
from .research_store import LoiNghiepVu
from .user_store import COL_USERS


def nguoi_cham_cua_dot(db, dot: dict) -> list:
    """Tên các người chấm được giao đợt này (danh sách rỗng = mọi tài khoản rater đang hoạt động)."""
    if dot["raters"]:
        return sorted(dot["raters"])
    return sorted(u["username"] for u in db[COL_USERS].find({"role": "rater", "is_active": True}, {"username": 1}))


def dot_hoac_404(db, ten: str) -> dict:
    dot = db[COL_DOT].find_one({"name": ten})
    if not dot:
        raise LoiNghiepVu(404, "dot_khong_co")
    return dot


def danh_sach_dot(db) -> list:
    """Mọi đợt kèm số mục theo game và số điểm đã nộp (không nội dung)."""
    kq = []
    for d in db[COL_DOT].find().sort("created_at", -1):
        n = {g: db[COL_MUC].count_documents({"rating_batch": d["name"], "game": g}) for g in (1, 3)}
        kq.append({"name": d["name"], "data_label": d["data_label"], "locked": bool(d.get("locked")), "raters": nguoi_cham_cua_dot(db, d),
                   "so_muc": n, "tong": n[1] + n[3], "created_at": d["created_at"].isoformat(), "so_diem": db[COL_DIEM].count_documents({"rating_batch": d["name"]})})
    return kq


def tien_do(db, ten_dot: str) -> dict:
    """Mỗi người chấm: đã chấm xong bao nhiêu/tổng, thời gian trung bình mỗi mục, ước tính thời gian còn lại (giây; None nếu chưa có số liệu)."""
    dot = dot_hoac_404(db, ten_dot)
    tong = db[COL_MUC].count_documents({"rating_batch": ten_dot})
    ds = []
    for r in nguoi_cham_cua_dot(db, dot):
        xong = list(db[COL_DIEM].find({"rating_batch": ten_dot, "rater": r, "hoan_tat": True}, {"thoi_gian_cham_giay": 1}))
        tb = sum(x["thoi_gian_cham_giay"] for x in xong) / len(xong) if xong else None
        ds.append({"rater": r, "da_cham": len(xong), "tong": tong, "tb_giay": tb, "con_lai_giay": None if tb is None else round(tb * (tong - len(xong)))})
    return {"rating_batch": ten_dot, "tong": tong, "locked": bool(dot.get("locked")), "nguoi_cham": ds}


def _diem_theo_nguoi(db, ten_dot: str, codes: list) -> dict:
    """{item_code: {rater: {diem, ghi_chu, hoan_tat, thoi_gian_cham_giay}}}"""
    kq = {}
    for r in db[COL_DIEM].find({"rating_batch": ten_dot, "item_code": {"$in": codes}}):
        kq.setdefault(r["item_code"], {})[r["rater"]] = {k: r.get(k) for k in ("diem", "ghi_chu", "hoan_tat", "thoi_gian_cham_giay")}
    return kq


def xem_cau_tra_loi(db, ten_dot: str, game: int | None, trang: int, co: int, thay_participant: bool) -> dict:
    """Nội dung từng mục cạnh điểm của các người chấm. participant_id chỉ hiện khi thay_participant (admin)."""
    dot_hoac_404(db, ten_dot)
    loc = {"rating_batch": ten_dot, **({"game": game} if game in (1, 3) else {})}
    muc = list(db[COL_MUC].find(loc).sort("thu_tu", 1).skip(max(0, trang - 1) * co).limit(co))
    diem = _diem_theo_nguoi(db, ten_dot, [m["item_code"] for m in muc])
    ds = [{"item_code": m["item_code"], "game": m["game"], "thu_tu": m["thu_tu"], "noi_dung": m["noi_dung"], "diem": diem.get(m["item_code"], {}),
           **({"participant_id": str(m["participant_id"]), "prompt_id": m["prompt_id"], "data_label": m["data_label"]} if thay_participant else {})} for m in muc]
    return {"muc": ds, "tong": db[COL_MUC].count_documents(loc), "trang": trang, "co": co}


def _dong_diem(r: dict) -> list:
    d = r["diem"]
    return [d.get("nhom", "")] + [d.get(m, "") for m in nd.ma_tieu_chi_game3()]


def xuat_diem_csv(db, ten_dot: str) -> str:
    """Điểm theo item_code, mỗi dòng một (mục, người chấm). Chỉ mã mục và tên người chấm, không có participant_id hay email."""
    dot_hoac_404(db, ten_dot)
    game = {m["item_code"]: m["game"] for m in db[COL_MUC].find({"rating_batch": ten_dot}, {"item_code": 1, "game": 1})}
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["item_code", "game", "rating_batch", "rater", "nhom", *nd.ma_tieu_chi_game3(), "hoan_tat", "thoi_gian_cham_giay", "ghi_chu"])
    for r in db[COL_DIEM].find({"rating_batch": ten_dot}).sort([("item_code", 1), ("rater", 1)]):
        w.writerow([_chong_cong_thuc(x) for x in [r["item_code"], game.get(r["item_code"]), ten_dot, r["rater"], *_dong_diem(r), r["hoan_tat"], r["thoi_gian_cham_giay"], r.get("ghi_chu", "")]])
    return out.getvalue()


def xuat_khoa_csv(db, ten_dot: str) -> str:
    """File khóa đối chiếu item_code -> participant_id (cố ý không có email)."""
    dot_hoac_404(db, ten_dot)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["item_code", "game", "rating_batch", "participant_id", "prompt_id", "nguon_khoa", "data_label"])
    for m in db[COL_MUC].find({"rating_batch": ten_dot}).sort("item_code", 1):
        w.writerow([_chong_cong_thuc(x) for x in [m["item_code"], m["game"], ten_dot, str(m["participant_id"]), m["prompt_id"], m["nguon_khoa"], m["data_label"]]])
    return out.getvalue()
