"""Chữ trên form phải GIỐNG HỆT từng ký tự với docs/survey_v2.md (nguồn chuẩn).

Ba việc kiểm tra:
1. content/form_b.json khớp survey_v2.md (tiêu đề, mô tả, tên phần, câu hỏi, đáp án, thang điểm, nhãn dòng).
2. web/*.js và web/*.html không viết cứng chữ câu hỏi hay đáp án (chữ phải đến từ API).
3. API không lộ các dòng ghi chú của file (loại câu hỏi, điều hướng) cho người chơi.
"""
import json
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(GOC / "src"))
from server import main  # noqa: E402

LOAI = {"Trắc nghiệm - Chọn 1 đáp án": "chon_mot", "Hộp kiểm - Chọn nhiều đáp án": "chon_nhieu",
        "Trả lời ngắn": "chu_tu_do", "Lưới trắc nghiệm - Thang đo Likert 5 mức độ": "luoi_1_5"}
MUC_KHAC = "Mục khác: `___________`"


# ---------- Đọc survey_v2.md ----------

def _cau_moi(dong: str) -> dict:
    """Dòng '### A1. chữ *(Bắt buộc)*' -> câu hỏi mới. Phần trong ngoặc: '(Bắt buộc)' hoặc '(gợi ý - Bắt buộc)'."""
    m = re.fullmatch(r"### (\S+) (.+?) \*\((.+)\)\*", dong)
    assert m, f"survey_v2.md: không đọc được dòng câu hỏi: {dong}"
    ngoac = m.group(3)
    goi_y = ngoac[: -len(" - Bắt buộc")] if ngoac.endswith(" - Bắt buộc") else None
    return {"nhan": m.group(1), "text": m.group(2), "bat_buoc": ngoac.endswith("Bắt buộc"),
            "huong_dan": goi_y, "loai": None, "options": [], "nhan_thang": None, "thang": [], "dong": []}


def _them_dong(cau: dict, dong: str, che_do_dong: bool) -> bool:
    """Xử lý một dòng '- ...' bên trong câu hỏi. Trả về chế độ 'đang đọc các dòng phát biểu'."""
    if dong.startswith("- [ ] "):
        chu = dong[6:]
        chu = chu.removesuffix(" *(Chuyển đến Phần C)*")   # ghi chú điều hướng, không hiện cho người chơi
        khac = chu == MUC_KHAC
        cau["options"].append(("Mục khác:" if khac else chu, khac))
    elif dong.startswith("- *(") and dong.endswith(")*"):
        cau["huong_dan"] = dong[4:-2]
    elif dong.startswith("- **Thang điểm:** "):
        cau["nhan_thang"] = "Thang điểm:"
        cau["thang"] = [x.strip("`") for x in dong[len("- **Thang điểm:** "):].split(" | ")]
    elif re.fullmatch(r"- \*\*\d+ phát biểu:\*\*", dong):
        return True
    elif che_do_dong and dong.startswith("- "):
        nhan, chu = dong[2:].split(" ", 1)
        cau["dong"].append((nhan, chu))
    return che_do_dong


def doc_khao_sat() -> dict:
    """Phân tích survey_v2.md thành {tieu_de, mo_ta, phan: [{tieu_de, cau: [...]}]}."""
    kq = {"tieu_de": None, "mo_ta": None, "phan": []}
    cau, che_do_dong = None, False
    for dong in (GOC / "docs" / "survey_v2.md").read_text(encoding="utf-8").splitlines():
        if dong.startswith("# "):
            kq["tieu_de"] = dong[2:]
        elif dong.startswith("> **Mô tả:** "):
            kq["mo_ta"] = dong[len("> **Mô tả:** "):]
        elif dong.startswith("## "):
            kq["phan"].append({"tieu_de": dong[3:], "cau": []})
        elif dong.startswith("### "):
            cau, che_do_dong = _cau_moi(dong), False
            kq["phan"][-1]["cau"].append(cau)
        elif dong.startswith("*(Loại câu hỏi: "):
            cau["loai"] = LOAI[dong[len("*(Loại câu hỏi: "):-2].split(" - Có điều hướng")[0]]
        elif cau and dong.startswith("- "):
            che_do_dong = _them_dong(cau, dong, che_do_dong)
    return kq


# ---------- Đọc form_b.json về cùng dạng ----------

def _cau_form(c: dict, thang: list[str], nhan_thang: str) -> dict:
    """Một câu của form_b.json về cùng dạng với câu của survey_v2.md."""
    return {"nhan": c["nhan"], "text": c["text"], "bat_buoc": c.get("bat_buoc", False),
            "huong_dan": c.get("huong_dan"), "loai": c["loai"],
            "options": [(o["text"], o.get("khac", False)) for o in c.get("options", [])],
            "nhan_thang": nhan_thang if c["loai"] == "luoi_1_5" else None,
            "thang": thang if c["loai"] == "luoi_1_5" else [],
            "dong": [(r["nhan"], r["text"]) for r in c.get("cac_dong", [])]}


def doc_form() -> dict:
    f = json.loads((GOC / "content" / "form_b.json").read_text(encoding="utf-8"))
    thang = list(f["thang_dong_y"].values())
    cau_c = f["phan_c_tu_danh_gia"]
    luoi_c = {**f["c_luoi"], "cac_dong": [c for c in cau_c if c["id"] != "C6"]}
    cau_c = [luoi_c] + [c for c in cau_c if c["id"] == "C6"]
    cacphan = [f["phan_a_thong_tin"], f["phan_b_hanh_vi"], cau_c]
    return {"tieu_de": f["tieu_de"], "mo_ta": f["mo_ta"],
            "phan": [{"tieu_de": f["tieu_de_phan"][k], "cau": [_cau_form(c, thang, f["nhan_thang"]) for c in ds]}
                     for k, ds in zip("ABC", cacphan)]}


# ---------- So sánh và báo chỗ lệch ----------

def _so_danh_sach(vi_tri: str, ten: str, file: list, form: list) -> list[str]:
    """So hai danh sách từng phần tử, báo rõ phần tử nào lệch."""
    loi = []
    if len(file) != len(form):
        loi.append(f"{vi_tri}: {ten} survey_v2.md có {len(file)}, form_b.json có {len(form)}")
    for i, (a, b) in enumerate(zip(file, form), 1):
        if a != b:
            loi.append(f"{vi_tri}: {ten} thứ {i} lệch\n    survey_v2.md: {a!r}\n    form_b.json : {b!r}")
    return loi


def _so_cau(file: dict, form: dict) -> list[str]:
    loi = []
    for khoa in ("nhan", "text", "bat_buoc", "huong_dan", "loai", "nhan_thang"):
        if file[khoa] != form[khoa]:
            loi.append(f"{file['nhan']}: '{khoa}' lệch\n    survey_v2.md: {file[khoa]!r}\n    form_b.json : {form[khoa]!r}")
    for ten, khoa in (("đáp án", "options"), ("nhãn thang", "thang"), ("dòng", "dong")):
        loi += _so_danh_sach(file["nhan"], ten, file[khoa], form[khoa])
    return loi


def so_sanh(file: dict, form: dict) -> list[str]:
    """Danh sách chỗ lệch (rỗng nếu khớp hoàn toàn)."""
    loi = []
    for khoa, ten in (("tieu_de", "tiêu đề form"), ("mo_ta", "mô tả form")):
        if file[khoa] != form[khoa]:
            loi.append(f"{ten} lệch\n    survey_v2.md: {file[khoa]!r}\n    form_b.json : {form[khoa]!r}")
    loi += _so_danh_sach("form", "phần", [p["tieu_de"] for p in file["phan"]], [p["tieu_de"] for p in form["phan"]])
    for pf, pj in zip(file["phan"], form["phan"]):
        loi += _so_danh_sach(pf["tieu_de"], "câu", [c["nhan"] for c in pf["cau"]], [c["nhan"] for c in pj["cau"]])
        for cf, cj in zip(pf["cau"], pj["cau"]):
            loi += _so_cau(cf, cj)
    return loi


def test_form_b_khop_survey_v2():
    loi = so_sanh(doc_khao_sat(), doc_form())
    assert not loi, "Chữ trên form lệch survey_v2.md:\n" + "\n".join(loi)


def test_bo_doc_khao_sat_du_cau():
    """Chắc chắn trình đọc đã đọc đủ: 3 phần, 4 + 7 + 2 câu, lưới B4 có 7 dòng, lưới C1 có 5 dòng."""
    k = doc_khao_sat()
    assert [len(p["cau"]) for p in k["phan"]] == [4, 7, 2]
    b4 = k["phan"][1]["cau"][3]
    assert len(b4["dong"]) == 7 and len(b4["thang"]) == 5 and b4["dong"][0][0] == "B4.1"
    assert len(k["phan"][2]["cau"][0]["dong"]) == 5 and k["phan"][2]["cau"][0]["dong"][0][0] == "C1.1."


def test_phat_hien_cho_lech():
    """Cố tình sửa một dấu câu thì bài kiểm tra phải báo đúng chỗ."""
    form = doc_form()
    form["phan"][1]["cau"][3]["dong"][2] = ("B4.3", "Tôi thường sử dụng ngay câu trả lời của AI mà không kiểm tra lại")
    loi = so_sanh(doc_khao_sat(), form)
    assert len(loi) == 1 and "B4" in loi[0] and "dòng thứ 3" in loi[0]


def test_muc_khac_co_o_go_chu():
    """B1, B3, B6 có đúng một lựa chọn 'Mục khác:' đánh dấu khac để web hiện ô gõ chữ."""
    k = doc_khao_sat()["phan"][1]["cau"]
    co_khac = [c["nhan"] for c in k if any(kh for _, kh in c["options"])]
    assert co_khac == ["B1.", "B3.", "B6."]
    assert (GOC / "docs" / "erd.dbml").read_text(encoding="utf-8").count("_other varchar") == 3


# ---------- Web không viết cứng chữ khảo sát ----------

def moi_chu_khao_sat() -> set[str]:
    """Mọi chuỗi chữ của khảo sát mà web không được tự viết (không tính chữ 1 từ ngắn như số thứ tự)."""
    k = doc_khao_sat()
    chu = {k["tieu_de"], k["mo_ta"]}
    for p in k["phan"]:
        chu.add(p["tieu_de"])
        for c in p["cau"]:
            chu |= {c["text"], c["nhan"] + " " + c["text"], *c["thang"], *(t for t, _ in c["options"])}
            chu |= {t for _, t in c["dong"]} | {n + " " + t for n, t in c["dong"]}
            chu |= {c["huong_dan"], c["nhan_thang"]} - {None}
    return chu


def chuoi_trong_js(ma: str) -> list[str]:
    """Các chuỗi "..." '...' `...` trong JS, sau khi bỏ chú thích (chú thích được phép nhắc chữ)."""
    ma = re.sub(r"/\*.*?\*/", "", ma, flags=re.S)
    ma = re.sub(r"(?m)^\s*//.*$|(?<=[;{}\s,)])//\s.*$", "", ma)
    return [m[1:-1] for m in re.findall(r"\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`", ma)]


def chu_trong_html(ma: str) -> list[str]:
    ma = re.sub(r"<!--.*?-->", "", ma, flags=re.S)
    return [t.strip() for t in re.findall(r">([^<]+)<", ma) if t.strip()]


def chu_viet_cung(cac_chuoi: list[str]) -> list[str]:
    """Chuỗi trùng hẳn một chữ khảo sát, hoặc (với chữ dài từ 10 ký tự) có chứa nó."""
    chu = moi_chu_khao_sat()
    return sorted({c for c in cac_chuoi for s in chu if c == s or (len(s) >= 10 and s in c)})


def test_bo_phat_hien_chu_viet_cung():
    """Kiểm tra chính bộ phát hiện: chuỗi viết cứng bị bắt, chữ trong chú thích thì không."""
    ma = 'h("p", {}, "Giới tính của bạn là gì?"); // "Nam"\n/* "Lớp 6" */ const x = "ok";'
    assert chu_viet_cung(chuoi_trong_js(ma)) == ["Giới tính của bạn là gì?"]
    assert chu_viet_cung(chu_trong_html("<p>Nam</p><!-- <b>Nữ</b> -->")) == ["Nam"]


def test_web_khong_viet_cung_chu_khao_sat():
    loi = []
    for f in sorted((GOC / "web").glob("*.js")):
        loi += [f"{f.name}: {c!r}" for c in chu_viet_cung(chuoi_trong_js(f.read_text(encoding="utf-8")))]
    for f in sorted((GOC / "web").glob("*.html")):
        loi += [f"{f.name}: {c!r}" for c in chu_viet_cung(chu_trong_html(f.read_text(encoding="utf-8")))]
    assert not loi, "Web viết cứng chữ của khảo sát (phải lấy từ API):\n" + "\n".join(loi)


# ---------- API không lộ ghi chú của file ----------

def test_api_khong_lo_ghi_chu_cho_nguoi_choi():
    r = TestClient(main.app).get("/api/content/form-b")
    assert r.status_code == 200
    for chu in ("Loại câu hỏi", "Chuyển đến", "(Bắt buộc)", "ghi_chu", "Chọn một hoặc nhiều"):
        assert chu not in r.text, chu
