"""Kiểm tra chấm điểm trên web (phiên 3): rút mẫu, giao diện người chấm, khóa đợt, hai người chấm không thấy nhau, xuất CSV,
phân quyền theo vai trò, giới hạn tốc độ, dọn dữ liệu thử có kèm điểm chấm. Dùng DB giả (mongomock); không chạm MongoDB thật."""
import csv
import io
import json
import sys
from pathlib import Path

import mongomock
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from server import admin_rating_api, main, rate_api, research  # noqa: E402
from sparkmind import du_lieu_thu, rating_sample, rating_store, user_store  # noqa: E402
from sparkmind.research_store import LoiNghiepVu  # noqa: E402

MK = "mat-khau-dai-12-ky-tu"
GOC = {"Origin": "http://testserver"}
EMAIL = "nguoi.choi.bi.mat@gmail.com"
T1, T2 = "g3_t1", "g3_t2"


@pytest.fixture
def db():
    d = mongomock.MongoClient().spark_mind
    user_store.tao_chi_muc_user(d)
    rating_store.tao_chi_muc_cham(d)
    main.app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: d
    yield d
    main.app.dependency_overrides.clear()


def vao(db, ten, role, ip):
    user_store.tao_user(db, ten, ten, role, MK, "test", bat_buoc_doi_mk=False)
    c = TestClient(main.app, client=(ip, 5))
    r = c.post("/api/auth/login", json={"username": ten, "password": MK}, headers=GOC)
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return c


def nguoi_choi(db, nhan, so_game1=3, y=None):
    """Một người chơi đã nộp game 1 (đồ vật gạch) và game 3 (cả hai tình huống), có email để kiểm tra không rò."""
    pid = ObjectId()
    db["participants"].insert_one({"_id": pid, "email": EMAIL, "data_label": nhan, "ip_hash": "abc"})
    y = y or [f"dùng gạch làm đồ vật số {pid}-{i}" for i in range(so_game1)]
    db["game_responses"].insert_one({"participant_id": pid, "game": 1, "data_label": nhan, "prompt_id": "g1_gach", "submitted_at": 1,
                                     "answer": {"ideas": y, "n_ideas": len(y)}})
    db["game_responses"].insert_one({"participant_id": pid, "game": 3, "data_label": nhan, "prompt_id": "game3", "submitted_at": 1,
                                     "answer": {"tinh_huong": [{"tinh_huong_id": T1, "noi_dung": f"ý tưởng một của {pid}"},
                                                               {"tinh_huong_id": T2, "noi_dung": f"ý tưởng hai của {pid}"}]}})
    return pid


@pytest.fixture
def du_lieu(db):
    for _ in range(12):
        nguoi_choi(db, "thu")
    nguoi_choi(db, "that")
    return db


def rut(db, **kw):
    tham_so = {"nhan": "thu", "ten_dot": "dot1", "n_game1": 10, "n_game3": 6, "seed": 7}
    tham_so.update(kw)
    return rating_sample.rut_mau(db, tham_so["nhan"], tham_so["ten_dot"], tham_so["n_game1"], tham_so["n_game3"], tham_so["seed"],
                                 dry_run=kw.get("dry_run", False), user={"username": "t", "role": "admin"})


def muc_cua(db, dot="dot1"):
    return list(db["rating_items"].find({"rating_batch": dot}).sort("thu_tu", 1))


# ---------- Rút mẫu ----------

def test_rut_mau_so_luong_va_deu_hai_tinh_huong(du_lieu):
    kq = rut(du_lieu, n_game1=10, n_game3=7)
    assert kq["da_rut"] == {1: 10, 3: 7} and kq["thieu"] == {1: 0, 3: 0}
    muc3 = [m for m in muc_cua(du_lieu) if m["game"] == 3]
    dem = {t: sum(1 for m in muc3 if m["prompt_id"] == t) for t in (T1, T2)}
    assert sorted(dem.values()) == [3, 4]                                      # 7 chia đều hai tình huống: 3 và 4
    assert all(m["data_label"] == "thu" for m in muc_cua(du_lieu))               # không rút nhãn that
    assert du_lieu["audit_log"].count_documents({"action": "rating_sample"}) == 1


def test_noi_dung_duoc_chep_sang_va_ma_muc_khong_lo_nguoi_choi(du_lieu):
    rut(du_lieu)
    m1 = next(m for m in muc_cua(du_lieu) if m["game"] == 1)
    assert m1["noi_dung"]["do_vat"] == "Viên gạch" and m1["noi_dung"]["cong_dung"].startswith("dùng gạch")
    m3 = next(m for m in muc_cua(du_lieu) if m["game"] == 3)
    assert set(m3["noi_dung"]) == {"tinh_huong", "ai_goc", "y_tuong"} and m3["noi_dung"]["ai_goc"]
    assert all(m["item_code"][:3] in ("G1-", "G3-") and str(m["participant_id"]) not in m["item_code"] for m in muc_cua(du_lieu))
    assert len({m["item_code"] for m in muc_cua(du_lieu)}) == len(muc_cua(du_lieu))


def test_seed_lap_lai_cung_mau_va_seed_khac_ra_mau_khac(du_lieu):
    def mau(seed, dot):
        rut(du_lieu, seed=seed, ten_dot=dot)
        return [(str(m["participant_id"]), m["nguon_khoa"], m["game"]) for m in muc_cua(du_lieu, dot)]
    a, b, c = mau(3, "a"), mau(3, "b"), mau(4, "c")
    assert a == b                                                               # cùng seed: cùng mẫu VÀ cùng thứ tự đã trộn
    assert sorted(a) != sorted(c) or a != c


def test_mau_duoc_tron_khong_xep_game_1_roi_game_3(du_lieu):
    rut(du_lieu, n_game1=20, n_game3=20)
    games = [m["game"] for m in muc_cua(du_lieu)]
    assert games != sorted(games) and [m["thu_tu"] for m in muc_cua(du_lieu)] == list(range(1, 41))


def test_khong_rut_lai_muc_da_co_trong_cung_dot(du_lieu):
    rut(du_lieu, n_game1=15, n_game3=10, seed=1)
    khoa = lambda: {(str(m["participant_id"]), m["game"], m["nguon_khoa"]) for m in muc_cua(du_lieu)}   # noqa: E731
    truoc = khoa()
    rut(du_lieu, n_game1=15, n_game3=10, seed=2)                                # cùng đợt, seed khác
    assert len(muc_cua(du_lieu)) == 50 and len(khoa()) == 50 and truoc <= khoa()
    sau = rut(du_lieu, n_game1=200, n_game3=0, seed=3)                          # đòi nhiều hơn số còn lại: lấy hết, báo thiếu
    assert sau["thieu"][1] > 0 and du_lieu["rating_items"].count_documents({"game": 1}) == 36   # 12 người x 3 ý


def test_dry_run_khong_ghi_gi(du_lieu):
    kq = rut(du_lieu, dry_run=True)
    assert kq["dry_run"] and kq["tong"] == 16
    assert du_lieu["rating_items"].count_documents({}) == 0 and du_lieu["rating_batches"].count_documents({}) == 0
    assert du_lieu["audit_log"].count_documents({}) == 0


def test_chi_rut_y_hop_le_va_nhan_that_khop_ca_ban_ghi_thieu_nhan(db):
    nguoi_choi(db, "that", y=["gạch", "dùng gạch làm bếp nướng", "Dùng gạch làm bếp nướng!", "x"])   # chỉ 1 ý hợp lệ (tên đồ vật, trùng, quá ngắn bị loại)
    pid = nguoi_choi(db, "that", y=["kê chân bàn cho khỏi lắc"])
    db["game_responses"].update_many({"participant_id": pid}, {"$unset": {"data_label": ""}})    # thiếu nhãn = that
    kq = rut(db, nhan="that", n_game1=10, n_game3=0)
    assert kq["da_rut"][1] == 2


def test_tham_so_sai_va_dot_khac_nhan_hoac_da_khoa(du_lieu):
    for kw in ({"nhan": "abc"}, {"ten_dot": "co dau cach"}, {"n_game1": -1}, {"seed": "x"}):
        with pytest.raises(LoiNghiepVu):
            rut(du_lieu, **kw)
    rut(du_lieu)
    with pytest.raises(LoiNghiepVu) as e:
        rut(du_lieu, nhan="pilot")
    assert e.value.noi_dung == "dot_khac_nhan"
    rating_store.dat_khoa_dot(du_lieu, "dot1", True)
    with pytest.raises(LoiNghiepVu) as e:
        rut(du_lieu)
    assert e.value.noi_dung == "dot_da_khoa"


def test_script_rut_mau_chay_o_che_do_xem_truoc(du_lieu, monkeypatch, capsys):
    import make_rating_sample as s
    monkeypatch.setattr(s, "lay_db", lambda: du_lieu)
    s.main(["--label", "thu", "--batch", "kich_ban", "--n-game1", "5", "--n-game3", "4", "--seed", "1"])
    assert "DRY-RUN" in capsys.readouterr().out and du_lieu["rating_items"].count_documents({}) == 0
    s.main(["--label", "thu", "--batch", "kich_ban", "--n-game1", "5", "--n-game3", "4", "--seed", "1", "--apply"])
    assert du_lieu["rating_items"].count_documents({}) == 9


# ---------- Người chấm ----------

@pytest.fixture
def he(du_lieu):
    """Một đợt đã rút, hai người chấm, một admin, một viewer."""
    rut(du_lieu, n_game1=6, n_game3=4)
    ten = {r: vao(du_lieu, r, "rater", f"10.0.0.{i}") for i, r in enumerate(("cham1", "cham2"), 1)}
    return {"db": du_lieu, "r1": ten["cham1"], "r2": ten["cham2"], "admin": vao(du_lieu, "admin1", "admin", "10.0.1.1"),
            "viewer": vao(du_lieu, "viewer1", "viewer", "10.0.1.2")}


def ma_muc(he, game):
    return next(m["item_code"] for m in muc_cua(he["db"]) if m["game"] == game)


def test_nguoi_cham_thay_danh_sach_theo_thu_tu_va_tien_do(he):
    d = he["r1"].get("/api/rate/items").json()
    assert d["tong"] == 10 and d["da_cham"] == 0 and [m["item_code"] for m in d["muc"]] == [m["item_code"] for m in muc_cua(he["db"])]
    assert set(d["muc"][0]) == {"item_code", "game", "da_cham"}                  # danh sách không có nội dung


def test_noi_dung_muc_chi_co_truong_cho_phep_khong_ro_ri(he):
    nguoi_choi_ids = [str(p["_id"]) for p in he["db"]["participants"].find()]
    for game in (1, 3):
        r = he["r1"].get(f"/api/rate/items/{ma_muc(he, game)}")
        assert r.status_code == 200
        d = r.json()
        assert set(d) == {"item_code", "game", "noi_dung", "locked", "rating"}
        for cam in [EMAIL, "ip_hash", "participant", "data_label", "flags", "prompt_id", "nguon_khoa", "seed", *nguoi_choi_ids]:
            assert cam not in r.text.replace(d["noi_dung"].get("y_tuong", ""), "").replace(d["noi_dung"].get("cong_dung", ""), "")
    g = he["r1"].get("/api/rate/guide").json()
    assert [n["ma"] for n in g["game1"]["nhom"]] == list("ABCDEFGH") and len(g["game3"]["tieu_chi"]) == 3


def test_cham_game1_luu_sua_va_f5_van_con(he):
    ma = ma_muc(he, 1)
    r = he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "C"}, "ghi_chu": " hợp lý ", "thoi_gian_cham_giay": 12}, headers=GOC)
    assert r.status_code == 200 and r.json() == {"ok": True, "hoan_tat": True}
    d = he["r1"].get(f"/api/rate/items/{ma}").json()
    assert d["rating"] == {"diem": {"nhom": "C"}, "ghi_chu": "hợp lý", "hoan_tat": True}
    he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "X"}, "thoi_gian_cham_giay": 5}, headers=GOC)
    doc = he["db"]["ratings"].find_one({"item_code": ma, "rater": "cham1"})
    assert doc["diem"] == {"nhom": "X"} and doc["thoi_gian_cham_giay"] == 12 and doc["thoi_gian_sua_giay"] == 5   # lần đầu giữ nguyên, lần sửa cộng riêng
    assert he["db"]["ratings"].count_documents({"item_code": ma}) == 1
    assert he["r1"].get("/api/rate/items").json()["da_cham"] == 1


def test_cham_game3_ba_tieu_chi_va_ban_nhap(he):
    ma = ma_muc(he, 3)
    r = he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"them_y_moi": 4, "khac_goc": "X"}}, headers=GOC)
    assert r.json() == {"ok": True, "hoan_tat": False}                           # thiếu một tiêu chí: lưu nháp, chưa tính tiến độ
    assert he["r1"].get("/api/rate/items").json()["da_cham"] == 0
    r = he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"them_y_moi": 4, "khac_goc": "X", "kha_thi": 2}}, headers=GOC)
    assert r.json()["hoan_tat"] is True and he["r1"].get("/api/rate/items").json()["da_cham"] == 1


@pytest.mark.parametrize("game,diem", [(1, {"nhom": "Z"}), (1, {"nhom": 3}), (1, {"them_y_moi": 3}), (3, {"them_y_moi": 6}), (3, {"them_y_moi": 0}),
                                       (3, {"them_y_moi": True}), (3, {"kha_thi": "x"}), (3, {"nhom": "A"}), (3, {"them_y_moi": 2.5})])
def test_diem_khong_hop_le_bi_tu_choi(he, game, diem):
    r = he["r1"].put(f"/api/rate/items/{ma_muc(he, game)}/rating", json={"diem": diem}, headers=GOC)
    assert r.status_code == 422 and he["db"]["ratings"].count_documents({}) == 0


def test_khoa_dot_thi_khong_sua_duoc_mo_lai_thi_sua_duoc(he):
    ma = ma_muc(he, 1)
    he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "A"}}, headers=GOC)
    assert he["admin"].post("/api/admin/rating/batches/dot1/lock", json={}, headers=GOC).json() == {"name": "dot1", "locked": True}
    r = he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "B"}}, headers=GOC)
    assert r.status_code == 423 and r.json()["detail"]["code"] == "dot_da_khoa"
    assert he["r1"].get(f"/api/rate/items/{ma}").json()["locked"] is True
    assert he["db"]["ratings"].find_one({"item_code": ma})["diem"] == {"nhom": "A"}
    he["admin"].post("/api/admin/rating/batches/dot1/unlock", json={}, headers=GOC)
    assert he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "B"}}, headers=GOC).status_code == 200
    assert he["db"]["audit_log"].count_documents({"action": {"$in": ["rating_lock", "rating_unlock"]}}) == 2


def test_hai_nguoi_cham_khong_thay_diem_cua_nhau(he):
    ma = ma_muc(he, 1)
    he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "D"}, "ghi_chu": "bí mật của người 1"}, headers=GOC)
    r2 = he["r2"].get(f"/api/rate/items/{ma}")
    assert r2.json()["rating"] is None and "bí mật" not in r2.text and "cham1" not in r2.text
    assert he["r2"].get("/api/rate/items").json()["da_cham"] == 0
    he["r2"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "E"}}, headers=GOC)
    assert he["db"]["ratings"].find_one({"item_code": ma, "rater": "cham1"})["diem"] == {"nhom": "D"}   # ghi của người 2 không đè người 1


def test_muc_khong_giao_hoac_khong_ton_tai_cung_mot_loi_404(he):
    he["db"]["rating_items"].insert_one({"item_code": "G1-9999", "game": 1, "noi_dung": {}, "rating_batch": "dot_rieng", "thu_tu": 1, "participant_id": ObjectId()})
    he["db"]["rating_batches"].insert_one({"name": "dot_rieng", "data_label": "thu", "raters": ["cham2"], "locked": False})
    for ma in ("G1-9999", "G1-0000", "khong-co"):
        r = he["r1"].get(f"/api/rate/items/{ma}")
        assert r.status_code == 404 and r.json()["detail"]["code"] == "muc_khong_co"
        assert he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "A"}}, headers=GOC).status_code == 404
    assert he["r2"].get("/api/rate/items/G1-9999").status_code == 200            # được giao riêng cho người 2
    assert "G1-9999" not in [m["item_code"] for m in he["r1"].get("/api/rate/items").json()["muc"]]


def test_ghi_phai_co_csrf_va_origin(he):
    ma = ma_muc(he, 1)
    sach = TestClient(main.app, client=("10.0.0.1", 5), cookies=he["r1"].cookies)
    assert sach.put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "A"}}, headers=GOC).status_code == 403   # thiếu X-CSRF-Token
    assert he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "A"}}).status_code == 403           # thiếu Origin


def test_vuot_gioi_han_tra_429_that(he):
    ma = ma_muc(he, 1)
    codes = [he["r2"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "A"}}, headers=GOC).status_code for _ in range(rate_api.gioi_han_ghi.toi_da + 2)]
    assert codes[0] == 200 and codes[-1] == 429


# ---------- Phân quyền ----------

def test_phan_quyen_theo_vai_tro(he):
    ma = ma_muc(he, 1)
    for nguoi in ("admin", "viewer"):
        assert he[nguoi].get("/api/rate/items").status_code == 403                # chỉ rater mới vào /api/rate
        assert he[nguoi].get(f"/api/rate/items/{ma}").status_code == 403
    chung = ["/api/admin/rating/batches", "/api/admin/rating/batches/dot1/progress", "/api/admin/rating/batches/dot1/answers",
             "/api/admin/rating/batches/dot1/agreement", "/api/admin/rating/batches/dot1/export/ratings.csv", "/api/admin/rating/batches/dot1/export/key.csv"]
    for u in chung:
        assert he["r1"].get(u).status_code == 403                                  # người chấm không vào trang quản trị
    assert he["r1"].post("/api/admin/rating/sample", json={"data_label": "thu", "rating_batch": "x", "n_game1": 1, "n_game3": 0, "seed": 1}, headers=GOC).status_code == 403
    assert he["viewer"].get("/api/admin/rating/batches").status_code == 200
    assert he["viewer"].get("/api/admin/rating/batches/dot1/progress").status_code == 200
    for u in chung[-2:]:
        assert he["viewer"].get(u).status_code == 403                              # viewer không xuất CSV
    assert he["viewer"].post("/api/admin/rating/batches/dot1/lock", json={}, headers=GOC).status_code == 403
    assert he["viewer"].post("/api/admin/rating/sample", json={"data_label": "thu", "rating_batch": "x", "n_game1": 1, "n_game3": 0, "seed": 1}, headers=GOC).status_code == 403
    assert TestClient(main.app).get("/api/rate/items").status_code == 401 and TestClient(main.app).get("/api/admin/rating/batches").status_code == 401


def test_admin_rut_mau_qua_web_co_dry_run_va_audit(he):
    body = {"data_label": "thu", "rating_batch": "dot2", "n_game1": 4, "n_game3": 2, "seed": 5, "dry_run": True}
    r = he["admin"].post("/api/admin/rating/sample", json=body, headers=GOC).json()
    assert r["dry_run"] and r["tong"] == 6 and he["db"]["rating_items"].count_documents({"rating_batch": "dot2"}) == 0
    he["admin"].post("/api/admin/rating/sample", json={**body, "dry_run": False}, headers=GOC)
    assert he["db"]["rating_items"].count_documents({"rating_batch": "dot2"}) == 6
    nhat_ky = he["db"]["audit_log"].find_one({"action": "rating_sample", "doc_id": "dot2"})
    assert nhat_ky["detail"]["seed"] == 5 and "noi_dung" not in json.dumps(nhat_ky["detail"], default=str)   # không ghi nội dung nhạy cảm
    xau = he["admin"].post("/api/admin/rating/sample", json={**body, "data_label": "xx"}, headers=GOC)
    assert xau.status_code == 422 and xau.json()["detail"]["code"] == "nhan_khong_hop_le"


# ---------- Tiến độ, xem câu trả lời, độ đồng thuận ----------

def cham_het(he, nguoi, nhom="A", diem3=None, giay=10):
    for m in muc_cua(he["db"]):
        diem = {"nhom": nhom} if m["game"] == 1 else (diem3 or {"them_y_moi": 3, "khac_goc": 3, "kha_thi": 3})
        he[nguoi].put(f"/api/rate/items/{m['item_code']}/rating", json={"diem": diem, "thoi_gian_cham_giay": giay}, headers=GOC)


def test_tien_do_va_uoc_tinh_thoi_gian(he):
    for m in muc_cua(he["db"])[:4]:
        he["r1"].put(f"/api/rate/items/{m['item_code']}/rating", json={"diem": {"nhom": "A"} if m["game"] == 1 else {"them_y_moi": 1, "khac_goc": 1, "kha_thi": 1}, "thoi_gian_cham_giay": 20}, headers=GOC)
    d = he["viewer"].get("/api/admin/rating/batches/dot1/progress").json()
    a, b = d["nguoi_cham"]
    assert (a["rater"], a["da_cham"], a["tong"], a["tb_giay"], a["con_lai_giay"]) == ("cham1", 4, 10, 20, 120)
    assert (b["da_cham"], b["tb_giay"], b["con_lai_giay"]) == (0, None, None)


def test_xem_cau_tra_loi_canh_diem_hai_nguoi_viewer_khong_thay_participant(he):
    ma = ma_muc(he, 1)
    he["r1"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "A"}}, headers=GOC)
    he["r2"].put(f"/api/rate/items/{ma}/rating", json={"diem": {"nhom": "B"}}, headers=GOC)
    v = he["viewer"].get("/api/admin/rating/batches/dot1/answers?game=1").json()
    m = next(x for x in v["muc"] if x["item_code"] == ma)
    assert m["diem"]["cham1"]["diem"] == {"nhom": "A"} and m["diem"]["cham2"]["diem"] == {"nhom": "B"} and "participant_id" not in m
    a = he["admin"].get("/api/admin/rating/batches/dot1/answers?game=1").json()
    assert "participant_id" in next(x for x in a["muc"] if x["item_code"] == ma) and v["tong"] == 6


def test_dong_thuan_qua_api_chua_du_va_du_du_lieu(he):
    cham_het(he, "r1")
    cham_het(he, "r2", nhom="B")
    d = he["viewer"].get("/api/admin/rating/batches/dot1/agreement").json()
    assert d["so_muc_ca_hai_cham"] == 10 and d["game1"] == {"du_du_lieu": False, "so_muc": 6}   # 6 < 20: chưa đủ
    d = he["viewer"].get("/api/admin/rating/batches/dot1/agreement?toi_thieu=4").json()
    assert d["game1"]["du_du_lieu"] and d["game1"]["dong_y_tho"] == 0 and len(d["muc_lech"]) == 6
    assert d["muc_lech"][0]["noi_dung"] and d["muc_lech"][0]["diem_a"] == {"nhom": "A"} and d["muc_lech"][0]["diem_b"] == {"nhom": "B"}
    assert he["viewer"].get("/api/admin/rating/batches/dot1/agreement?rater_a=cham1&rater_b=cham1").status_code == 422


# ---------- Xuất CSV ----------

def test_xuat_csv_diem_va_khoa_khong_co_email(he):
    cham_het(he, "r1")
    cham_het(he, "r2", nhom="C", diem3={"them_y_moi": 5, "khac_goc": "X", "kha_thi": 1})
    he["r1"].put(f"/api/rate/items/{ma_muc(he, 1)}/rating", json={"diem": {"nhom": "A"}, "ghi_chu": "=HYPERLINK(\"x\")"}, headers=GOC)
    r = he["admin"].get("/api/admin/rating/batches/dot1/export/ratings.csv")
    assert r.status_code == 200 and "text/csv" in r.headers["content-type"] and "attachment" in r.headers["content-disposition"]
    dong = list(csv.DictReader(io.StringIO(r.text.lstrip("﻿"))))
    assert len(dong) == 20 and {d["rater"] for d in dong} == {"cham1", "cham2"}
    g3 = next(d for d in dong if d["rater"] == "cham2" and d["game"] == "3")
    assert (g3["them_y_moi"], g3["khac_goc"], g3["kha_thi"], g3["nhom"]) == ("5", "X", "1", "")
    assert "'=HYPERLINK" in r.text and "participant" not in r.text and EMAIL not in r.text   # chống công thức Excel; không có người chơi
    k = he["admin"].get("/api/admin/rating/batches/dot1/export/key.csv")
    khoa = list(csv.DictReader(io.StringIO(k.text.lstrip("﻿"))))
    ids = {str(m["participant_id"]) for m in muc_cua(he["db"])}
    assert len(khoa) == 10 and {d["participant_id"] for d in khoa} == ids and EMAIL not in k.text and "email" not in k.text.lower()
    assert he["db"]["audit_log"].count_documents({"action": {"$in": ["rating_export", "rating_key_export"]}}) == 2
    assert he["admin"].get("/api/admin/rating/batches/khong_co/export/key.csv").status_code == 404


# ---------- Dọn dữ liệu thử ----------

def test_don_du_lieu_thu_xoa_ca_muc_diem_va_dot_nhung_giu_nhan_that(he):
    db = he["db"]
    rut(db, nhan="that", ten_dot="dot_that", n_game1=2, n_game3=2)
    cham_het(he, "r1")
    db["ratings"].insert_one({"item_code": muc_cua(db, "dot_that")[0]["item_code"], "rater": "cham1", "diem": {"nhom": "A"}, "hoan_tat": True, "rating_batch": "dot_that"})
    kq = du_lieu_thu.xem_truoc(db)
    assert kq["rating_items"] == 10 and kq["ratings"] == 10 and kq["rating_batches"] == 1   # dry-run: số riêng, không xóa gì
    assert db["rating_items"].count_documents({}) == 14
    du_lieu_thu.xoa(db, {"username": "a", "role": "admin"}, "XOA")
    assert db["rating_items"].count_documents({"data_label": "thu"}) == 0 and db["rating_batches"].count_documents({"name": "dot1"}) == 0
    assert db["ratings"].count_documents({"rating_batch": "dot1"}) == 0
    assert db["rating_items"].count_documents({"data_label": "that"}) == 4 and db["rating_batches"].count_documents({"name": "dot_that"}) == 1
    assert db["ratings"].count_documents({"rating_batch": "dot_that"}) == 1                # điểm của dữ liệu thật còn nguyên
    assert db["audit_log"].count_documents({"action": "test_data_delete", "collection": "ratings"}) == 1


def test_trang_xoa_nhac_xuat_csv_va_api_tra_so_rieng(he):
    ui = he["admin"].get("/api/auth/ui").json()
    assert "Xuất CSV điểm chấm trước khi xóa nếu cần giữ" in ui["don_dep"]["nhac_xuat"]
    d = he["admin"].get("/api/admin/test-data").json()
    assert {"rating_items", "ratings", "rating_batches"} <= set(d["bang"]) and d["bang"]["rating_items"] == 10


def test_moi_route_cham_deu_co_kiem_quyen_va_khong_doc_duoc_rating_nguoi_khac():
    from test_admin_auth import duyet_route, route_thieu_kiem_quyen
    assert route_thieu_kiem_quyen(main.app) == []
    cac = {d for d, r, _ in duyet_route(main.app.routes) if d.startswith(("/api/rate", "/api/admin/rating"))}
    assert "/api/rate/items/{item_code}/rating" in cac and "/api/admin/rating/sample" in cac
    assert not any("ratings" in d and d.startswith("/api/rate") and "{item_code}" not in d for d in cac)   # không có route đọc điểm theo rater/người khác
    assert admin_rating_api.router.prefix == "/api/admin/rating"


# ---------- Chỉnh sau phiên 3 ----------

def test_xoa_participant_keo_theo_muc_cham_va_diem_cua_nguoi_do(he):
    db = he["db"]
    cham_het(he, "r1")
    pid = muc_cua(db)[0]["participant_id"]
    cua_pid = [m["item_code"] for m in muc_cua(db) if m["participant_id"] == pid]
    khac = db["rating_items"].count_documents({}) - len(cua_pid)
    lq = he["admin"].get(f"/api/admin/data/participants/{pid}/lien-quan").json()["bang_con"]
    assert lq["rating_items"] == len(cua_pid) and lq["ratings"] == len(cua_pid)       # màn xác nhận hiện số từng loại
    r = he["admin"].delete(f"/api/admin/data/participants/{pid}?confirm={pid}", headers=GOC)
    assert r.status_code == 200 and r.json()["da_xoa_bang_con"]["ratings"] == len(cua_pid)
    assert db["rating_items"].count_documents({"participant_id": pid}) == 0 and db["ratings"].count_documents({"item_code": {"$in": cua_pid}}) == 0
    assert db["rating_items"].count_documents({}) == khac and db["ratings"].count_documents({}) == khac   # người khác còn nguyên
    log = db["audit_log"].find_one({"action": "data_delete", "collection": "participants"})
    assert log["detail"]["da_xoa_bang_con"]["rating_items"] == len(cua_pid)


def test_bang_moc_game3_va_nguong_do_dong_thuan(he):
    g3 = he["r1"].get("/api/rate/guide").json()["game3"]
    assert g3["tieu_chi"][0]["moc"]["3"] == "Có một ý mới rõ nhưng đơn giản, phổ biến" and g3["tieu_chi"][2]["moc"]["5"] == "Làm được ngay, cách làm rõ ràng"
    d = he["viewer"].get("/api/admin/rating/batches/dot1/agreement?toi_thieu=10").json()
    assert d["toi_thieu"] == 10 and d["toi_thieu_mac_dinh"] == 20
