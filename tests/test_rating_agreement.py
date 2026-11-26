"""Kiểm tra độ đồng thuận: kappa tự cài đặt phải khớp scikit-learn (cohen_kappa_score, weights='quadratic') trên ví dụ nhỏ biết trước."""
import sys
from pathlib import Path

import mongomock
import pytest
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sparkmind import rating_agreement as dt, rating_store  # noqa: E402

NHOM = list("ABCDEFGH") + ["X"]
THANG = [1, 2, 3, 4, 5]
A1 = list("AABBCCDDXXAABBCCHH")
B1 = list("AABCCCDDXAAABBCDHE")
A3 = [1, 2, 3, 4, 5, 3, 3, 2, 4, 5, 1, 1]
B3 = [1, 3, 3, 5, 4, 3, 2, 2, 4, 5, 2, 1]


def test_kappa_khong_trong_so_khop_sklearn():
    ours = dt.kappa(list(zip(A1, B1)), NHOM)
    assert ours == pytest.approx(cohen_kappa_score(A1, B1, labels=NHOM))
    assert ours == pytest.approx(cohen_kappa_score(A1, B1))                    # cùng số khi không truyền labels (nhãn có mặt đủ)


def test_kappa_trong_so_bac_hai_khop_sklearn():
    ours = dt.kappa(list(zip(A3, B3)), THANG, "quadratic")
    assert ours == pytest.approx(cohen_kappa_score(A3, B3, labels=THANG, weights="quadratic"))
    assert ours == pytest.approx(cohen_kappa_score(A3, B3, weights="quadratic"))   # đủ 1–5 đều có mặt nên trùng cả khi sklearn tự suy nhãn


def test_gia_tri_biet_truoc_bang_tay():
    # 2 nhãn, 10 mục: đồng ý 8 (po = 0.8); A chọn "a" 5 lần, B chọn "a" 6 lần -> pe = 0.5*0.6 + 0.5*0.4 = 0.5 -> kappa = 0.6
    cap = [("a", "a")] * 4 + [("b", "b")] * 4 + [("a", "b")] + [("b", "a")]
    assert dt.kappa(cap, ["a", "b"]) == pytest.approx(0.6)
    assert dt.ti_le_dong_y(cap) == 0.8 and dt.ma_tran_cheo(cap, ["a", "b"]) == [[4, 1], [1, 4]]
    # đồng ý hoàn toàn trên nhiều nhãn -> 1; hoàn toàn ngược -> âm
    assert dt.kappa([(1, 1), (2, 2), (3, 3), (4, 4)], THANG, "quadratic") == pytest.approx(1.0)
    assert dt.kappa([(1, 5), (5, 1), (1, 5), (5, 1)], THANG, "quadratic") < 0


def test_truong_hop_khong_xac_dinh():
    assert dt.kappa([], NHOM) is None and dt.ti_le_dong_y([]) is None
    assert dt.kappa([("A", "A")] * 5, NHOM) is None                            # cả hai luôn chọn một nhãn: mẫu số 0


def _dung_du_lieu(so_muc=24):
    db = mongomock.MongoClient().spark_mind
    rating_store.tao_chi_muc_cham(db)
    db["rating_batches"].insert_one({"name": "d", "data_label": "thu", "raters": ["a", "b"], "locked": False})
    for i in range(so_muc):
        game = 1 if i % 2 == 0 else 3
        db["rating_items"].insert_one({"item_code": f"G{game}-{i:04d}", "game": game, "rating_batch": "d", "thu_tu": i, "noi_dung": {"x": i}, "participant_id": i})
    return db


def _cham(db, rater, item, diem, xong=True):
    db["ratings"].insert_one({"item_code": item, "rater": rater, "rating_batch": "d", "diem": diem, "hoan_tat": xong})


def test_do_dong_thuan_ca_hai_game_bo_cap_co_x_va_muc_lech():
    db = _dung_du_lieu(40)
    g1 = [m["item_code"] for m in db["rating_items"].find({"game": 1}).sort("thu_tu", 1)]
    g3 = [m["item_code"] for m in db["rating_items"].find({"game": 3}).sort("thu_tu", 1)]
    nhom_a, nhom_b = (list("ABCDEFGH" * 3)[:20], list("ABCDEFGH" * 3)[:20])
    nhom_b[3], nhom_b[7] = "X", "A"                                              # hai mục lệch
    for it, a, b in zip(g1, nhom_a, nhom_b):
        _cham(db, "a", it, {"nhom": a})
        _cham(db, "b", it, {"nhom": b})
    a3, b3 = [(i % 5) + 1 for i in range(20)], [((i + (i % 3 == 0)) % 5) + 1 for i in range(20)]
    for i, it in enumerate(g3):
        da = {"them_y_moi": a3[i], "khac_goc": a3[i], "kha_thi": "X" if i == 0 else a3[i]}
        db_ = {"them_y_moi": b3[i], "khac_goc": 5 - (b3[i] - 1), "kha_thi": b3[i]}
        _cham(db, "a", it, da)
        _cham(db, "b", it, db_)
    d = dt.do_dong_thuan(db, "d", "a", "b", toi_thieu=10)
    assert d["so_muc_ca_hai_cham"] == 40
    assert d["game1"]["kappa"] == pytest.approx(cohen_kappa_score(nhom_a, nhom_b)) and d["game1"]["dong_y_tho"] == 0.9
    assert d["game1"]["nhan"][-1] == "X" and sum(map(sum, d["game1"]["bang_cheo"])) == 20
    kt = d["game3"]["tieu_chi"]
    assert kt["them_y_moi"]["kappa_trong_so"] == pytest.approx(cohen_kappa_score(a3, b3, weights="quadratic"))
    assert kt["kha_thi"]["so_muc"] == 19 and kt["them_y_moi"]["so_muc"] == 20          # bỏ cặp có X
    ks = [t["kappa_trong_so"] for t in kt.values()]
    assert d["game3"]["trung_binh"] == pytest.approx(sum(ks) / 3)
    ma_lech = {m["item_code"] for m in d["muc_lech"]}
    assert {g1[3], g1[7]} <= ma_lech and g3[0] in ma_lech                                # X một bên ở game 3 cũng là lệch
    assert all(m["noi_dung"] and "diem_a" in m and "diem_b" in m for m in d["muc_lech"])


def test_chua_du_du_lieu_thi_khong_tinh_va_ban_nhap_khong_dem():
    db = _dung_du_lieu(6)
    for m in db["rating_items"].find({"game": 1}):
        _cham(db, "a", m["item_code"], {"nhom": "A"})
        _cham(db, "b", m["item_code"], {"nhom": "A"}, xong=False)              # người b mới lưu nháp
    d = dt.do_dong_thuan(db, "d", "a", "b")
    assert d["so_muc_ca_hai_cham"] == 0 and d["game1"] == {"du_du_lieu": False, "so_muc": 0}
    assert d["game3"]["trung_binh"] is None and d["muc_lech"] == []
