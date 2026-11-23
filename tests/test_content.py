"""Kiểm tra file nội dung (content/) đọc được và đúng cấu trúc cơ bản."""
import json
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[1] / "content"


def doc(ten):
    return json.loads((CONTENT / ten).read_text(encoding="utf-8"))


def test_form_b_du_cau():
    f = doc("form_b.json")
    b4 = next(x for x in f["phan_b_hanh_vi"] if x["id"] == "B4")
    assert [r["id"] for r in b4["cac_dong"]] == [f"B4_{i}" for i in range(1, 8)]
    assert [x["id"] for x in f["phan_c_tu_danh_gia"][:5]] == [f"C{i}" for i in range(1, 6)]
    dao = [r["id"] for r in b4["cac_dong"] if r.get("dao_chieu")]
    assert dao == ["B4_3", "B4_6"]  # khớp NEG trong columns.py


def test_game2_12_y_5_loi():
    y = doc("games/game2.json")["y"]
    assert len(y) == 12 and len({i["id"] for i in y}) == 12
    assert sum(i["la_loi"] for i in y) == 5
    assert all(i["loai_loi"] for i in y if i["la_loi"]) and all(i["loai_loi"] is None for i in y if not i["la_loi"])


def test_game1_va_game3_co_noi_dung():
    assert len(doc("games/game1.json")["do_vat"]) == 3
    g3 = doc("games/game3.json")
    assert set(g3["rubric"]) == {"them_y_moi", "khac_goc", "kha_thi"}


def test_game1_noi_dung_cho_trinh_duyet():
    """Endpoint /api/content/game1 trả hướng dẫn và ví dụ, không lộ ghi chú nội bộ hay danh sách đồ vật."""
    from fastapi.testclient import TestClient
    from server import main
    d = TestClient(main.app).get("/api/content/game1").json()
    assert d["thoi_gian_giay"] == 180 and d["vi_du"]["vi_du_khac"] and "do_vat" not in d
