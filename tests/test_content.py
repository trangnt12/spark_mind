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


def test_game2_moi_de_4_loi_that():
    for de in doc("games/game2.json")["de"]:
        assert len(de["nhan_xet"]) == 8
        assert sum(n["la_loi"] for n in de["nhan_xet"]) == 4


def test_game1_va_game3_co_noi_dung():
    assert len(doc("games/game1.json")["do_vat"]) == 3
    g3 = doc("games/game3.json")
    assert set(g3["rubric"]) == {"them_y_moi", "khac_goc", "kha_thi"}
