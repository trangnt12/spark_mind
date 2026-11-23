"""Kiểm tra API dự đoán: demo (không lưu gì), kết quả nghiên cứu, tính cộng pred_contribs, models/ không bị phục vụ."""
import json
import sys
from datetime import datetime
from pathlib import Path

import mongomock
import numpy as np
import pandas as pd
import pytest
import xgboost as xgb
from fastapi.testclient import TestClient
from starlette.routing import Mount

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(GOC / "src"))
from server import main, predict_api, research  # noqa: E402
from sparkmind import config, modeling as M, predict as P, research_store as kho  # noqa: E402

DUNG = {f"B4_{i}": v for i, v in enumerate([4, 5, 2, 4, 3, 2, 5], 1)}
DS_MUC = ["Thap", "Trung_binh", "Cao"]


@pytest.fixture
def client(monkeypatch):
    db = mongomock.MongoClient().spark_mind
    monkeypatch.setattr(config, "IP_HASH_SECRET", "khoa-thu")
    kho.tao_chi_muc(db)
    predict_api.gioi_han_demo.xoa()
    main.app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: db
    yield TestClient(main.app, client=("1.2.3.4", 50000)), db
    main.app.dependency_overrides.clear()


def demo(c, answers):
    return c.post("/api/predict/demo", json={"answers": answers})


def vector_mau(n: int = 5) -> list:
    """n bộ B4 cố định (hạt giống 0) để so sánh."""
    rng = np.random.default_rng(0)
    return [{f"B4_{i}": int(v) for i, v in enumerate(rng.integers(1, 6, 7), 1)} for _ in range(n)]


# (a) đủ 7 câu
def test_demo_du_7_cau(client):
    c, _ = client
    r = demo(c, DUNG)
    assert r.status_code == 200
    d = r.json()
    assert d["che_do"] == "demo" and d["model_version"]
    assert sum(d["xac_suat"].values()) == pytest.approx(1.0, abs=1e-9)
    assert d["muc"] == max(d["xac_suat"], key=d["xac_suat"].get)
    assert 0 <= d["diem_du_doan"] <= 100
    assert 1 <= len(d["dong_gop"]) <= 4
    for g in d["dong_gop"]:
        assert set(g) == {"id", "gia_tri", "chieu", "do_lon"}            # không lộ số SHAP thô
        assert g["id"].startswith("B4_") and g["chieu"] in ("tang", "giam") and g["do_lon"] in ("nho", "vua", "lon")


# (b) đầu vào sai -> 422 có thông báo tiếng Việt
@pytest.mark.parametrize("sua", [
    lambda a: {k: v for k, v in a.items() if k != "B4_3"},         # thiếu câu
    lambda a: {**a, "B4_1": 0}, lambda a: {**a, "B4_1": 6},        # ngoài khoảng
    lambda a: {**a, "B4_2": "3"}, lambda a: {**a, "B4_2": "abc"},  # chữ
    lambda a: {**a, "B4_4": 3.5}, lambda a: {**a, "B4_4": 3.0},    # số thực
    lambda a: {**a, "B4_5": True}, lambda a: {**a, "B4_5": None},
    lambda a: {**a, "C1": 5}, lambda a: {}])
def test_demo_422(client, sua):
    c, _ = client
    r = demo(c, sua(DUNG))
    assert r.status_code == 422
    assert "B4" in r.json()["detail"]                                  # nêu rõ câu nào có vấn đề


def test_demo_422_body_hong(client):
    c, _ = client
    assert c.post("/api/predict/demo", json=[1, 2]).status_code == 422
    assert c.post("/api/predict/demo", json={"answers": [1]}).status_code == 422
    r = c.post("/api/predict/demo", content="{hong", headers={"content-type": "application/json"})
    assert r.status_code == 422 and "answers" in r.json()["detail"]


def test_demo_gioi_han_30_moi_phut(client):
    c, _ = client
    assert all(demo(c, DUNG).status_code == 200 for _ in range(30))
    r = demo(c, DUNG)
    assert r.status_code == 429 and "Retry-After" in r.headers
    khac = TestClient(main.app, client=("5.6.7.8", 1))                 # IP khác không bị ảnh hưởng
    assert demo(khac, DUNG).status_code == 200


# (c) demo không ghi gì vào DB
def test_demo_khong_ghi_db(client):
    c, db = client
    kho.tao_ma_moi(db, 2, "volunteer")
    truoc = {t: db[t].count_documents({}) for t in db.list_collection_names()}
    for a in vector_mau():
        assert demo(c, a).status_code == 200
    assert demo(c, {}).status_code == 422
    assert {t: db[t].count_documents({}) for t in db.list_collection_names()} == truoc


def test_demo_khong_log_noi_dung(client, caplog):
    c, _ = client
    caplog.set_level("DEBUG")
    demo(c, DUNG)
    assert "B4_1" not in caplog.text


# (d) kết quả nghiên cứu
def nguoi_xong(db, xong: bool, co_b4: bool = True) -> str:
    token = "tok-" + str(db["participants"].count_documents({}))
    pid = db["participants"].insert_one({"session_token": token, "email": "a@b.vn",
                                         "completed_at": datetime.now() if xong else None}).inserted_id
    if co_b4:
        db["behavior_answers"].insert_one({"participant_id": pid, **{k.lower(): v for k, v in DUNG.items()}})
    return token


def test_research_result_409_khi_chua_xong(client):
    c, db = client
    t = nguoi_xong(db, xong=False)
    r = c.get("/api/research/result", headers={"X-Session-Token": t})
    assert r.status_code == 409 and "3 trò chơi" in r.json()["detail"]


def test_research_result_200_khi_da_xong(client):
    c, db = client
    t = nguoi_xong(db, xong=True)
    truoc = {n: db[n].count_documents({}) for n in db.list_collection_names()}
    r = c.get("/api/research/result", headers={"X-Session-Token": t})
    assert r.status_code == 200 and r.json()["che_do"] == "research"
    assert r.json()["muc"] == demo(c, DUNG).json()["muc"]              # cùng B4 gốc -> cùng kết quả
    assert c.get("/api/research/result", params={"session_token": t}).status_code == 401   # query không còn được nhận
    assert {n: db[n].count_documents({}) for n in db.list_collection_names()} == truoc   # không lưu thêm


def test_research_result_token_sai_va_thieu_b4(client):
    c, db = client
    assert c.get("/api/research/result", headers={"X-Session-Token": "khong-co"}).status_code == 401
    assert c.get("/api/research/result").status_code == 401
    t = nguoi_xong(db, xong=True, co_b4=False)
    assert c.get("/api/research/result", headers={"X-Session-Token": t}).status_code == 422


# (e) pred_contribs + nền = đầu ra của mô hình
def test_pred_contribs_cong_bang_margin():
    mh = P.nap_mo_hinh()
    cot = mh["meta"]["cot_mo_hinh_theo_thu_tu"]
    dm = xgb.DMatrix(np.vstack([P.dung_vector(a, mh["meta"]) for a in vector_mau(20)]), feature_names=cot)
    pc = mh["xgb_clf"].predict(dm, pred_contribs=True)                 # (người, 3 mức, 7 câu + nền)
    margin = mh["xgb_clf"].predict(dm, output_margin=True)
    assert np.abs(pc.sum(axis=2) - margin).max() < 1e-4
    pr = mh["xgb_reg"].predict(dm, pred_contribs=True)
    assert np.abs(pr.sum(axis=1) - mh["xgb_reg"].predict(dm)).max() < 1e-3   # hồi quy: sai số float32 cỡ 1e-4


def test_mo_hinh_b4_chi_co_dung_7_cot():
    mh = P.nap_mo_hinh()
    assert mh["meta"]["cot_mo_hinh_theo_thu_tu"] == P.CAU_B4 == M.B4
    for ten in ("xgb_clf", "xgb_reg"):
        assert mh[ten].num_features() == 7 and mh[ten].feature_names == P.CAU_B4
    assert P.dung_vector(DUNG, mh["meta"]).shape == (1, 7)
    M.kiem_tra_cot_cam(mh["meta"]["cot_mo_hinh_theo_thu_tu"])         # không có cột cấm


def test_chieu_khop_dau_pred_contribs_hoi_quy():
    """chieu 'tang' <=> đóng góp hồi quy dương (kéo điểm lên); ca B4_7 = 5 trong ví dụ DUNG phải là 'tang'."""
    mh = P.nap_mo_hinh()
    cot = mh["meta"]["cot_mo_hinh_theo_thu_tu"]
    for a in vector_mau(20) + [DUNG]:
        dm = xgb.DMatrix(P.dung_vector(a, mh["meta"]), feature_names=cot)
        pc = mh["xgb_reg"].predict(dm, pred_contribs=True)[0]
        for g in P.du_doan(a)["dong_gop"]:
            assert (g["chieu"] == "tang") == (pc[cot.index(g["id"])] >= 0)
    b47 = next(g for g in P.du_doan(DUNG)["dong_gop"] if g["id"] == "B4_7")
    assert b47["chieu"] == "tang"


def test_do_lon_chia_ba_muc_theo_nguong():
    ng = P.nap_mo_hinh()["nguong"]
    assert 0 < ng[0] < ng[1]
    assert [P._muc_do_lon(v, ng) for v in (ng[0] / 2, (ng[0] + ng[1]) / 2, ng[1] * 2)] == ["nho", "vua", "lon"]


def test_khong_con_nhan_token_qua_query(client):
    c, db = client
    t = nguoi_xong(db, xong=True)
    assert c.get("/api/research/result", params={"session_token": t}).status_code == 401
    assert c.get("/api/research/result", headers={"X-Session-Token": t}).status_code == 200


# (f) models/ không được phục vụ ra ngoài
@pytest.mark.parametrize("duong", ["/models/xgb_clf.json", "/models/model_meta.json", "/models/do_lon.json",
                                   "/models/xgb_b4_clf.json", "/models/model_b4_meta.json",
                                   "/play/models/xgb_clf.json", "/play/../models/xgb_clf.json",
                                   "/play/%2e%2e/models/xgb_clf.json", "/static/xgb_clf.json", "/xgb_clf.json"])
def test_models_khong_tai_duoc(client, duong):
    c, _ = client
    r = c.get(duong)
    assert r.status_code in (404, 405) and "learner" not in r.text


def test_khong_mount_thu_muc_chua_models():
    """Mọi đường tĩnh chỉ được trỏ vào thư mục con (web/), không phải gốc dự án và không phải models/."""
    models = (GOC / "models").resolve()
    thu_muc = [Path(r.app.directory).resolve() for r in main.app.routes
               if isinstance(r, Mount) and getattr(r.app, "directory", None)]
    assert thu_muc, "phải có đường tĩnh /play để kiểm tra"
    for t in thu_muc:
        assert t != GOC.resolve() and t != models and models not in t.parents and not (t / "xgb_clf.json").exists()


# (g) cùng đầu vào cho cùng đầu ra
def test_cung_dau_vao_cung_dau_ra():
    assert P.du_doan(DUNG) == P.du_doan(dict(DUNG))
    assert all(P.du_doan(a) == P.du_doan(a) for a in vector_mau())


# (h) đối chiếu với mô hình B4 nạp từ JSON (XGBClassifier/XGBRegressor), 5 vector mẫu
def test_doi_chieu_mo_hinh_goc():
    mh = P.nap_mo_hinh()
    clf, reg = xgb.XGBClassifier(), xgb.XGBRegressor()
    clf.load_model(str(GOC / "models" / "xgb_b4_clf.json"))
    reg.load_model(str(GOC / "models" / "xgb_b4_reg.json"))
    cot = mh["meta"]["cot_mo_hinh_theo_thu_tu"]
    for a in vector_mau(5):
        X = pd.DataFrame(P.dung_vector(a, mh["meta"]), columns=cot)
        p, diem, kq = clf.predict_proba(X)[0], float(reg.predict(X)[0]), P.du_doan(a)
        assert kq["muc"] == DS_MUC[int(p.argmax())]
        assert np.allclose([kq["xac_suat"][m] for m in DS_MUC], p, atol=1e-4)
        assert kq["diem_du_doan"] == pytest.approx(min(100, max(0, diem)), abs=0.06)


# Khớp với modeling.py và meta
def test_vector_dung_thu_tu_cot():
    meta = P.nap_mo_hinh()["meta"]
    assert meta["cot_mo_hinh_theo_thu_tu"] == M.B4
    assert P.dung_vector({"B4_1": 1, "B4_7": 5}, meta)[0][[0, 6]].tolist() == [1, 5]
    assert np.isnan(P.dung_vector({"B4_1": 1}, meta)[0][1])           # câu chưa trả lời = NaN, không điền trung vị


def test_chi_liet_ke_cau_da_tra_loi():
    kq = P.du_doan({"B4_1": 5, "B4_2": 1})
    assert {g["id"] for g in kq["dong_gop"]} <= {"B4_1", "B4_2"}


def test_requirements_server_ghim_xgboost_dung_ban_va_khong_co_thu_vien_nang():
    dong = [d.strip() for d in (GOC / "requirements-server.txt").read_text(encoding="utf-8").splitlines()]
    ten = {d.split("==")[0].lower() for d in dong if d and not d.startswith("#")}
    for ten_meta in ("model_meta.json", "model_b4_meta.json"):
        meta = json.loads((GOC / "models" / ten_meta).read_text(encoding="utf-8"))
        assert f"xgboost-cpu=={meta['phien_ban']['xgboost']}" in dong
    assert "xgboost" not in ten                                        # chỉ dùng xgboost-cpu trên server
    assert not {"shap", "scikit-learn", "sklearn"} & ten
