"""Kiểm tra game 2 (Soi lỗi AI): chấm điểm, không lộ đáp án, nộp trùng, token, completed_at."""
import sys
from pathlib import Path

import mongomock
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from server import game2, main, research  # noqa: E402
from sparkmind import config, game_store, research_store as kho  # noqa: E402
from sparkmind.score_game2 import cham_game2  # noqa: E402
from tests.test_research import BAT_DAU  # noqa: E402

B = "/api/research/game2"
Y = game2.noi_dung_game2()["y"]
SAI = [i["id"] for i in Y if i["la_loi"]]
DUNG = [i["id"] for i in Y if not i["la_loi"]]


@pytest.fixture
def client(monkeypatch):
    db = mongomock.MongoClient().spark_mind
    monkeypatch.setattr(config, "IP_HASH_SECRET", "khoa-thu")
    kho.tao_chi_muc(db)
    game_store.tao_chi_muc_game(db)
    research.gioi_han_ma.xoa()
    main.app.dependency_overrides[research.lay_db_nghien_cuu] = lambda: db
    yield TestClient(main.app, client=("1.2.3.4", 50000)), db
    main.app.dependency_overrides.clear()


def nguoi_moi(c, db, nhan=None):
    ma = kho.tao_ma_moi(db, 1, "volunteer", *([nhan] if nhan else []))[0]
    return c.post("/api/research/start", json={"code": ma, **BAT_DAU}).json()["session_token"]


def nop(c, t, chon):
    c.post(f"{B}/start", json={"session_token": t})
    return c.post(f"{B}/submit", json={"session_token": t, "chon": chon})


# ---------- Chấm điểm ----------

def test_cham_chon_dung_5_y_sai():
    assert cham_game2(Y, SAI) == {"score": 5, "n_correct": 5, "n_wrong": 0}


def test_cham_chon_het_12_y():
    assert cham_game2(Y, SAI + DUNG) == {"score": 0, "n_correct": 5, "n_wrong": 7}   # 5 - 7 < 0 nên về 0


def test_cham_chon_0_y():
    assert cham_game2(Y, []) == {"score": 0, "n_correct": 0, "n_wrong": 0}


def test_cham_san_0_khong_am():
    assert cham_game2(Y, DUNG[:3] + SAI[:1])["score"] == 0   # 1 - 3 = -2 -> 0


def test_cham_tru_diem_nham():
    assert cham_game2(Y, SAI[:4] + DUNG[:1]) == {"score": 3, "n_correct": 4, "n_wrong": 1}


def test_cham_diem_toi_da_5():
    assert max(cham_game2(Y, SAI + DUNG[:k])["score"] for k in range(len(DUNG) + 1)) == 5


# ---------- Không lộ đáp án ----------

def test_start_khong_lo_dap_an(client):
    c, db = client
    r = c.post(f"{B}/start", json={"session_token": nguoi_moi(c, db)})
    assert r.status_code == 200
    d = r.json()
    assert len(d["y"]) == 12 and [i["id"] for i in d["y"]] == [i["id"] for i in Y]   # thứ tự cố định
    assert d["submitted"] is False and "ket_qua" not in d
    for tu in ("la_loi", "loai_loi", "giai_thich", "sai_nam", "ket_qua"):
        assert tu not in r.text
    assert "một số ý sai" in d["tinh_huong"] and "5 ý" not in d["tinh_huong"]   # không nói số ý sai


def test_content_api_khong_lo_game2(client):
    c, _ = client
    assert c.get("/api/content/game2").status_code in (404, 405)


def test_nop_xong_moi_co_ket_qua(client):
    c, db = client
    r = nop(c, nguoi_moi(c, db), SAI[:2]).json()
    assert r["ok"] and len(r["ket_qua"]) == 12 and "loai_loi" not in str(r) and "la_loi" not in r["tinh_huong"]
    assert r["diem"] == 2 and (r["n_correct"], r["n_wrong"]) == (2, 0)
    assert [k["da_chon"] for k in r["ket_qua"] if k["la_loi"]].count(True) == 2
    assert all(k["giai_thich"] for k in r["ket_qua"])


# ---------- Lưu ----------

def test_luu_dung_truong_va_ke_thua_nhan(client):
    c, db = client
    t = nguoi_moi(c, db, "pilot")
    assert nop(c, t, SAI[:4] + DUNG[:1]).status_code == 200
    d = db["game_responses"].find_one({"game": 2})
    assert d["data_label"] == "pilot" and d["submitted_at"] and d["duration_sec"] >= 0
    assert d["answer"] == {"selected_ids": [i["id"] for i in Y if i["id"] in SAI[:4] + DUNG[:1]],
                           "score": 3, "n_correct": 4, "n_wrong": 1}


def test_chon_trung_va_id_la(client):
    c, db = client
    t = nguoi_moi(c, db)
    c.post(f"{B}/start", json={"session_token": t})
    assert c.post(f"{B}/submit", json={"session_token": t, "chon": ["g2_99"]}).status_code == 422
    assert c.post(f"{B}/submit", json={"session_token": t, "chon": [SAI[0], SAI[0]]}).status_code == 200
    assert db["game_responses"].find_one({"game": 2})["answer"]["n_correct"] == 1


def test_nop_trung_khong_doi_ket_qua(client):
    c, db = client
    t = nguoi_moi(c, db)
    nop(c, t, SAI)
    luu = db["game_responses"].find_one({"game": 2})
    r = c.post(f"{B}/submit", json={"session_token": t, "chon": []})   # lần hai chọn khác hẳn
    assert r.status_code == 200 and all(k["da_chon"] == k["la_loi"] for k in r.json()["ket_qua"])
    assert db["game_responses"].find_one({"game": 2}) == luu and db["game_responses"].count_documents({"game": 2}) == 1


def test_start_sau_khi_nop_tra_ket_qua(client):
    c, db = client
    t = nguoi_moi(c, db)
    nop(c, t, SAI[:1])
    d = c.post(f"{B}/start", json={"session_token": t}).json()
    assert d["submitted"] is True and len(d["ket_qua"]) == 12


def test_nop_khi_chua_bat_dau(client):
    c, db = client
    r = c.post(f"{B}/submit", json={"session_token": nguoi_moi(c, db), "chon": []})
    assert r.status_code == 409


# ---------- Quyền truy cập ----------

def test_can_session_token(client):
    c, _ = client
    assert c.post(f"{B}/start", json={}).status_code == 422
    assert c.post(f"{B}/start", json={"session_token": "sai"}).status_code == 401
    assert c.post(f"{B}/submit", json={"session_token": "sai", "chon": []}).status_code == 401
    assert c.post(f"{B}/submit", json={"chon": []}).status_code == 422


def test_token_nguoi_khac_khong_xem_bai_nhau(client):
    c, db = client
    t1, t2 = nguoi_moi(c, db), nguoi_moi(c, db)
    nop(c, t1, SAI)
    d2 = c.post(f"{B}/start", json={"session_token": t2}).json()
    assert d2["submitted"] is False and "ket_qua" not in d2


# ---------- completed_at ----------

def nop_game1(c, t):
    c.post("/api/research/game1/start", json={"session_token": t})
    return c.post("/api/research/game1/submit", json={"session_token": t, "ideas": ["a b"], "paste_count": 0, "tab_leave_count": 0})


def completed(db):
    return db["participants"].find_one()["completed_at"]


def test_completed_at_chi_gan_khi_du_game(client, monkeypatch):
    c, db = client
    monkeypatch.setattr(config, "GAME_BAT_BUOC", (1, 2))   # giả lập "chỉ có 2 game" để thử gán
    t = nguoi_moi(c, db)
    nop_game1(c, t)
    assert completed(db) is None                          # mới xong game 1
    nop(c, t, SAI)
    assert completed(db) is not None                      # đủ game 1 và 2


def test_completed_at_khong_ghi_de(client, monkeypatch):
    c, db = client
    monkeypatch.setattr(config, "GAME_BAT_BUOC", (1, 2))
    t = nguoi_moi(c, db)
    nop_game1(c, t)
    nop(c, t, SAI)
    lan_dau = completed(db)
    nop(c, t, [])                                          # nộp trùng game 2
    assert completed(db) == lan_dau


def test_completed_at_chua_gan_khi_thieu_game_3(client):
    """Theo config mặc định (1, 2, 3): game 3 chưa có nên xong game 1 và 2 vẫn chưa hoàn thành."""
    c, db = client
    assert config.GAME_BAT_BUOC == (1, 2, 3)
    t = nguoi_moi(c, db)
    nop_game1(c, t)
    nop(c, t, SAI)
    assert completed(db) is None
    assert c.get("/api/research/result", headers={"X-Session-Token": t}).status_code == 409


def test_them_game_3_chi_can_them_ten(client):
    """Có bài game 3 đã nộp trong DB thì (1, 2, 3) đủ: hàm kiểm tra không cần sửa gì."""
    c, db = client
    t = nguoi_moi(c, db)
    nop_game1(c, t)
    nop(c, t, SAI)
    pid = db["participants"].find_one()["_id"]
    db["game_responses"].insert_one({"participant_id": pid, "game": 3, "submitted_at": game_store.bay_gio()})
    assert game_store.kiem_tra_hoan_thanh(db, db["participants"].find_one()) is True
    assert completed(db) is not None


def test_giao_dien_game2_noi_voi_game1():
    goc = Path(__file__).resolve().parents[1]
    assert "manGame2" in (goc / "web/game1.js").read_text(encoding="utf-8")
    assert "/play/game2.js" in (goc / "web/index.html").read_text(encoding="utf-8")
