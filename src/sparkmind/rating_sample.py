"""Rút mẫu để chấm: chép nội dung từ game_responses sang rating_items (việc chấm không phụ thuộc bản gốc).

Dùng chung cho nút trong trang quản trị và scripts/make_rating_sample.py. Cùng seed + cùng dữ liệu = cùng mẫu.
Game 1: mỗi mục là MỘT ý hợp lệ (qua bộ lọc score_game1). Game 3: mỗi mục là một ô tình huống; rút đều hai tình huống.
Không rút lại mục đã có trong cùng đợt. Mã mục (G1-0001, G3-0001) cấp SAU KHI trộn nên không suy ra được người chơi.
"""
import json
import random

from pymongo.errors import DuplicateKeyError

from . import config, game3_store, score_game1
from .audit import write_audit
from .rating_store import COL_DOT, COL_MUC, MAU_TEN_DOT, lay_dot
from .research_store import LoiNghiepVu
from .thoi_gian import utc_now


def _bo_loc_nhan(nhan: str) -> dict:
    """Nhãn "that" khớp cả bản ghi thiếu nhãn (coi như that), giống mọi nơi khác."""
    return {"$or": [{"data_label": nhan}, {"data_label": None}]} if nhan == config.NHAN_MAC_DINH else {"data_label": nhan}


def _kiem_tham_so(nhan, ten_dot, n1, n3, seed) -> None:
    if nhan not in config.NHAN_HOP_LE:
        raise LoiNghiepVu(422, "nhan_khong_hop_le")
    if not MAU_TEN_DOT.match(ten_dot or ""):
        raise LoiNghiepVu(422, "ten_dot_khong_hop_le")
    if not all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 5000 for x in (n1, n3, seed)):
        raise LoiNghiepVu(422, "tham_so_khong_hop_le")


def _ten_do_vat() -> dict:
    with open(config.ROOT / "content" / "games" / "game1.json", encoding="utf-8") as f:
        return {d["id"]: d["ten"] for d in json.load(f)["do_vat"]}


def _ung_vien_game1(db, nhan: str) -> list:
    """Mọi ý hợp lệ của các bài game 1 đã nộp: (participant_id, khóa 'y<số thứ tự>', prompt_id, nội dung)."""
    ten, kq = _ten_do_vat(), []
    for b in db["game_responses"].find({"game": 1, "submitted_at": {"$ne": None}, **_bo_loc_nhan(nhan)}):
        y = [i for i in b.get("answer", {}).get("ideas", [])]
        hop_le = set(score_game1.loc_y_hop_le(y, ten.get(b["prompt_id"], ""))[0])
        da_lay = set()
        for i, chu in enumerate(y):
            if chu in hop_le and chu not in da_lay:   # ý đầu tiên của mỗi chữ hợp lệ (trùng đã bị bộ lọc loại)
                da_lay.add(chu)
                kq.append((b["participant_id"], f"y{i}", b["prompt_id"], {"do_vat": ten.get(b["prompt_id"], b["prompt_id"]), "cong_dung": chu}))
    return kq


def _ung_vien_game3(db, nhan: str) -> dict:
    """{tinh_huong_id: [(participant_id, tinh_huong_id, tinh_huong_id, nội dung)]} để rút đều từng tình huống."""
    nd3 = game3_store.noi_dung_game3()
    th = {t["id"]: t for t in nd3["tinh_huong"]}
    kq = {i: [] for i in th}
    for b in db["game_responses"].find({"game": 3, "submitted_at": {"$ne": None}, **_bo_loc_nhan(nhan)}):
        for m in b.get("answer", {}).get("tinh_huong", []):
            t = th.get(m["tinh_huong_id"])
            if t:
                kq[t["id"]].append((b["participant_id"], t["id"], t["id"],
                                    {"tinh_huong": t["tieu_de"], "ai_goc": t["ai_goc"], "y_tuong": m["noi_dung"]}))
    return kq


def _da_co(db, ten_dot: str, game: int) -> set:
    return {(m["participant_id"], m["nguon_khoa"]) for m in db[COL_MUC].find({"rating_batch": ten_dot, "game": game}, {"participant_id": 1, "nguon_khoa": 1})}


def _rut(rng, ung_vien: list, da_co: set, k: int) -> tuple:
    """Rút k ứng viên (chưa có trong đợt) bằng rng. Trả (danh sách rút, số còn thiếu). Sắp xếp trước để cùng seed ra cùng mẫu."""
    con = sorted((u for u in ung_vien if (u[0], u[1]) not in da_co), key=lambda u: (str(u[0]), u[1]))
    chon = rng.sample(con, min(k, len(con)))
    return chon, k - len(chon)


def _chia_deu(rng, tong: int, so_nhom: int) -> list:
    """Chia tong cho so_nhom nhóm đều nhất; phần dư gán ngẫu nhiên cho các nhóm (bằng rng)."""
    ds = [tong // so_nhom] * so_nhom
    for i in rng.sample(range(so_nhom), tong % so_nhom):
        ds[i] += 1
    return ds


def _chon_mau(db, nhan, ten_dot, n1, n3, rng) -> tuple:
    """Trả (các mục đã rút [(game, ứng viên)], thiếu {game: số}). Chưa ghi gì."""
    g1, thieu1 = _rut(rng, _ung_vien_game1(db, nhan), _da_co(db, ten_dot, 1), n1)
    th, da3 = _ung_vien_game3(db, nhan), _da_co(db, ten_dot, 3)
    g3, thieu3 = [], 0
    for ds, (_, uv) in zip(_chia_deu(rng, n3, len(th)), sorted(th.items())):
        chon, thieu = _rut(rng, uv, da3, ds)
        g3 += chon
        thieu3 += thieu
    mau = [(1, u) for u in g1] + [(3, u) for u in g3]
    rng.shuffle(mau)
    return mau, {1: thieu1, 3: thieu3}


def _so_tiep_theo(db, game: int) -> int:
    """Số thứ tự mã kế tiếp của game (lớn nhất đang có + 1)."""
    ma = [int(m["item_code"].split("-")[1]) for m in db[COL_MUC].find({"game": game}, {"item_code": 1})]
    return max(ma, default=0) + 1


def _ghi_muc(db, mau: list, nhan: str, ten_dot: str, seed: int) -> None:
    """Ghi các mục theo thứ tự đã trộn; mã cấp theo thứ tự này. Mục thứ tự (thu_tu) liên tục trong đợt."""
    dem = {1: _so_tiep_theo(db, 1), 3: _so_tiep_theo(db, 3)}
    thu_tu = db[COL_MUC].count_documents({"rating_batch": ten_dot})
    luc = utc_now()
    for game, (pid, khoa, prompt, noi_dung) in mau:
        thu_tu += 1
        muc = {"item_code": f"G{game}-{dem[game]:04d}", "game": game, "noi_dung": noi_dung, "participant_id": pid, "nguon_khoa": khoa,
               "prompt_id": prompt, "data_label": nhan, "rating_batch": ten_dot, "thu_tu": thu_tu, "rut_luc": luc, "seed": seed}
        dem[game] += 1
        try:
            db[COL_MUC].insert_one(muc)
        except DuplicateKeyError:
            raise LoiNghiepVu(409, "trung_ma_muc")


def _chuan_bi_dot(db, nhan: str, ten_dot: str) -> dict | None:
    """Đợt đã có: phải cùng nhãn và chưa khóa. Trả đợt (hoặc None nếu chưa có)."""
    dot = lay_dot(db, ten_dot)
    if dot and dot["data_label"] != nhan:
        raise LoiNghiepVu(409, "dot_khac_nhan")
    if dot and dot.get("locked"):
        raise LoiNghiepVu(423, "dot_da_khoa")
    return dot


def rut_mau(db, nhan: str, ten_dot: str, n_game1: int, n_game3: int, seed: int, dry_run: bool = False,
            user: dict | None = None, raters: list | None = None) -> dict:
    """Rút mẫu. dry_run=True: chỉ tính, không ghi gì (kể cả audit). Trả {dry_run, da_rut: {game: số}, thieu: {game: số}, tong}."""
    _kiem_tham_so(nhan, ten_dot, n_game1, n_game3, seed)
    dot = _chuan_bi_dot(db, nhan, ten_dot)
    mau, thieu = _chon_mau(db, nhan, ten_dot, n_game1, n_game3, random.Random(seed))
    da_rut = {g: sum(1 for x, _ in mau if x == g) for g in (1, 3)}
    kq = {"dry_run": dry_run, "da_rut": da_rut, "thieu": thieu, "tong": len(mau)}
    if dry_run:
        return kq
    if not dot:
        db[COL_DOT].insert_one({"name": ten_dot, "data_label": nhan, "raters": sorted(set(raters or [])), "locked": False, "locked_at": None, "created_at": utc_now()})
    _ghi_muc(db, mau, nhan, ten_dot, seed)
    write_audit(db, user, "rating_sample", COL_MUC, ten_dot, {"nhan": nhan, "seed": seed, "yeu_cau": {"game1": n_game1, "game3": n_game3},
                                                                           "da_rut": {"game1": da_rut[1], "game3": da_rut[3]}, "thieu": {"game1": thieu[1], "game3": thieu[3]}})
    return kq
