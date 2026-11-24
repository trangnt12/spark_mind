"""Kiểm tra cờ chống gian lận (24/11): từng trường hợp nhanh / một mức / bình thường / bị gián đoạn,
bi_gian_doan không tính vào flag_count, tính lại idempotent, lưu thoi_gian_cau, người chơi không thấy cờ,
và trừ thời gian ẩn tab ở phía trình duyệt (chạy thoigian.js bằng node)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import mongomock
import pytest
from fastapi.testclient import TestClient

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(GOC / "src"))
from server import main, research  # noqa: E402
from sparkmind import config, flags, flags_store, game_store, research_store as kho  # noqa: E402
from tests.test_research import BAT_DAU, HANH_VI, TU_DANH_GIA  # noqa: E402

CAU_B = [f"B4_{i}" for i in range(1, 8)]
CAU_C = [f"C{i}" for i in range(1, 6)]
MUC_B = [4, 2, 5, 3, 4, 2, 5]   # bảy mức B4 không giống nhau


def tg_cham(cac_cau, ms=4000, **them):
    """Số đo của người làm bình thường: mỗi câu cách nhau `ms` mili giây."""
    return {"khoang_ms": {c: ms for c in cac_cau}, "sua_cuoi_ms": {}, "an_tab_ms": 0, "tong_ms": ms * len(cac_cau), **them}


def hanh_vi(muc=MUC_B, **them):
    return {f"b4_{i}": v for i, v in enumerate(muc, 1)} | {"duration_sec": 120} | them


# ---------- Luật cờ (thuần túy) ----------

def test_lam_binh_thuong_khong_co_co():
    hv = hanh_vi(thoi_gian_cau=tg_cham(CAU_B))
    tdg = {"c1": 4, "c2": 3, "c3": 5, "c4": 4, "c5": 2, "thoi_gian_cau": tg_cham(CAU_C)}
    game = {1: {"duration_sec": 150}, 2: {"duration_sec": 90}}
    assert flags.tinh_co(hv, tdg, game) == []


def test_nhieu_cau_duoi_1_giay_la_lam_qua_nhanh():
    assert flags.tinh_co(hanh_vi(thoi_gian_cau=tg_cham(CAU_B, ms=400)), None, {}) == ["lam_qua_nhanh:form_b"]


def test_it_cau_nhanh_thi_khong_co():
    """Chỉ 2/7 câu dưới 1 giây (tỉ lệ 0,29 < 0,6): không cờ."""
    tg = tg_cham(CAU_B)
    tg["khoang_ms"]["B4_1"] = tg["khoang_ms"]["B4_2"] = 300
    assert flags.tinh_co(hanh_vi(thoi_gian_cau=tg), None, {}) == []


def test_tong_thoi_gian_duoi_nguong_tung_buoc():
    toi_thieu = config.CO_TONG_GIAY_TOI_THIEU["form_b"]
    assert flags.tinh_co(hanh_vi(duration_sec=toi_thieu - 1), None, {}) == ["lam_qua_nhanh:form_b"]
    assert flags.tinh_co(hanh_vi(duration_sec=toi_thieu), None, {}) == []
    c = {"c1": 4, "c2": 3, "c3": 5, "c4": 4, "c5": 2}
    assert flags.tinh_co(None, {**c, "thoi_gian_cau": {"khoang_ms": {}, "tong_ms": 5000}}, {}) == ["lam_qua_nhanh:khoi_c"]
    assert flags.tinh_co(None, {**c, "thoi_gian_cau": {"khoang_ms": {}, "tong_ms": 60000}}, {}) == []
    assert flags.tinh_co(None, None, {1: {"duration_sec": 5}, 2: {"duration_sec": 5}}) == ["lam_qua_nhanh:game1", "lam_qua_nhanh:game2"]
    assert flags.tinh_co(None, None, {1: {"duration_sec": 100}, 2: {"duration_sec": 100}}) == []


def test_mot_dap_an_form_b_va_khoi_c():
    hv = hanh_vi([3] * 7, thoi_gian_cau=tg_cham(CAU_B))
    tdg = {f"c{i}": 4 for i in range(1, 6)} | {"thoi_gian_cau": tg_cham(CAU_C)}
    assert flags.tinh_co(hv, tdg, {}) == ["mot_dap_an:form_b", "mot_dap_an:khoi_c"]


def test_khong_co_so_do_thi_khong_ket_luan_nhanh_theo_cau():
    """Trình duyệt không gửi thời gian: không cờ nhanh theo câu, không lỗi."""
    assert flags.tinh_co(hanh_vi(), {"c1": 1, "c2": 2, "c3": 3, "c4": 4, "c5": 5}, {}) == []


def test_chua_bao_gio_dung_ai_bo_qua_phan_b():
    """A4 = 4: không có B4, làm ít giây cũng không bị cờ form B."""
    assert flags.tinh_co({"a4": "4", "duration_sec": 3}, None, {}) == []


def test_bi_gian_doan_khoang_dai_va_an_tab():
    tg = tg_cham(CAU_B)
    tg["khoang_ms"]["B4_4"] = config.CO_KHOANG_GIAN_DOAN_MS + 1
    assert flags.tinh_co(hanh_vi(thoi_gian_cau=tg), None, {}) == ["bi_gian_doan:form_b"]
    tg2 = tg_cham(CAU_B, an_tab_ms=config.CO_AN_TAB_GIAN_DOAN_MS + 1)
    assert flags.tinh_co(hanh_vi(thoi_gian_cau=tg2), None, {}) == ["bi_gian_doan:form_b"]
    tg3 = tg_cham(CAU_B, an_tab_ms=config.CO_AN_TAB_GIAN_DOAN_MS)   # đúng ngưỡng: chưa tính
    assert flags.tinh_co(hanh_vi(thoi_gian_cau=tg3), None, {}) == []


def test_bi_gian_doan_khong_tinh_vao_flag_count():
    assert flags.dem_co(["bi_gian_doan:form_b", "bi_gian_doan:khoi_c"]) == 0
    assert flags.dem_co(["bi_gian_doan:form_b", "lam_qua_nhanh:game1", "mot_dap_an:khoi_c"]) == 2
    assert "bi_gian_doan" in config.CO_THAM_KHAO


def test_moi_co_co_the_deu_hop_le():
    tat_ca = flags.tat_ca_co_co_the()
    assert len(tat_ca) == 8 and len(set(tat_ca)) == 8
    assert {flags.ma_co(c) for c in tat_ca} == {"lam_qua_nhanh", "mot_dap_an", "bi_gian_doan"}


# ---------- Qua API: lưu số đo, gắn cờ, không lộ cho người chơi ----------

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


def vao(c, db):
    ma = kho.tao_ma_moi(db, 1, "volunteer")[0]
    return c.post("/api/research/start", json={"code": ma, **BAT_DAU}).json()["session_token"]


def nop_b(c, t, **them):
    return c.post("/api/research/behavior", json={"session_token": t, **HANH_VI, **them})


def nguoi(db):
    return db[kho.COL_NGUOI].find_one()


def test_nop_binh_thuong_luu_thoi_gian_cau_va_khong_co_co(client):
    c, db = client
    t = vao(c, db)
    r = nop_b(c, t, thoi_gian_cau=tg_cham(CAU_B))
    assert r.status_code == 200 and r.json() == {"ok": True}   # người chơi chỉ thấy ok, không thấy cờ
    luu = db[kho.COL_HANH_VI].find_one()["thoi_gian_cau"]
    assert luu["khoang_ms"]["B4_3"] == 4000 and luu["an_tab_ms"] == 0 and luu["tong_ms"] == 28000
    assert nguoi(db)["flags"] == [] and nguoi(db)["flag_count"] == 0


def test_nop_nhanh_gan_co_nhung_van_luu_bai(client):
    c, db = client
    t = vao(c, db)
    r = nop_b(c, t, duration_sec=10, thoi_gian_cau=tg_cham(CAU_B, ms=200))
    assert r.status_code == 200 and "flag" not in json.dumps(r.json()).lower()
    assert db[kho.COL_HANH_VI].count_documents({}) == 1          # không xóa, không từ chối
    assert nguoi(db)["flags"] == ["lam_qua_nhanh:form_b"] and nguoi(db)["flag_count"] == 1
    r = c.post("/api/research/self-assessment", json={"session_token": t, **{k: 3 for k in TU_DANH_GIA}, "thoi_gian_cau": tg_cham(CAU_C)})
    assert r.status_code == 200
    assert nguoi(db)["flags"] == ["lam_qua_nhanh:form_b", "mot_dap_an:khoi_c"] and nguoi(db)["flag_count"] == 2


def test_gian_doan_co_trong_flags_nhung_flag_count_bang_0(client):
    c, db = client
    t = vao(c, db)
    nop_b(c, t, thoi_gian_cau=tg_cham(CAU_B, an_tab_ms=300_000))
    assert nguoi(db)["flags"] == ["bi_gian_doan:form_b"] and nguoi(db)["flag_count"] == 0


def test_khong_gui_thoi_gian_van_nop_duoc(client):
    c, db = client
    t = vao(c, db)
    assert nop_b(c, t).status_code == 200
    assert "thoi_gian_cau" not in db[kho.COL_HANH_VI].find_one()


def test_so_do_ngoai_khoang_bi_tu_choi_va_khoa_la_bi_bo(client):
    c, db = client
    t = vao(c, db)
    assert nop_b(c, t, thoi_gian_cau=tg_cham(CAU_B) | {"an_tab_ms": -5}).status_code == 422
    xau = tg_cham(CAU_B)
    xau["khoang_ms"]["B4_1"] = 10 ** 12
    assert nop_b(c, t, thoi_gian_cau=xau).status_code == 422
    la = tg_cham(CAU_B)
    la["khoang_ms"].update({"email": 5, "C1": 5})
    assert nop_b(c, t, thoi_gian_cau=la).status_code == 200
    assert set(db[kho.COL_HANH_VI].find_one()["thoi_gian_cau"]["khoang_ms"]) == set(CAU_B)   # chỉ giữ câu của khối này


def test_sua_lai_khong_ghi_de_so_do_lan_dau(client):
    c, db = client
    t = vao(c, db)
    nop_b(c, t, thoi_gian_cau=tg_cham(CAU_B, ms=5000))
    nop_b(c, t, edit=True, thoi_gian_cau=tg_cham(CAU_B, ms=100))
    assert db[kho.COL_HANH_VI].find_one()["thoi_gian_cau"]["khoang_ms"]["B4_1"] == 5000


def test_game_nop_qua_nhanh_gan_co(client):
    c, db = client
    t = vao(c, db)
    c.post("/api/research/game1/start", json={"session_token": t})
    r1 = c.post("/api/research/game1/submit", json={"session_token": t, "ideas": ["a"], "paste_count": 0, "tab_leave_count": 0})
    assert r1.status_code == 200
    c.post("/api/research/game2/start", json={"session_token": t})
    assert c.post("/api/research/game2/submit", json={"session_token": t, "chon": []}).status_code == 200
    assert nguoi(db)["flags"] == ["lam_qua_nhanh:game1", "lam_qua_nhanh:game2"] and nguoi(db)["flag_count"] == 2


def test_co_khong_lot_ra_tien_do_cua_nguoi_choi(client):
    c, db = client
    t = vao(c, db)
    nop_b(c, t, duration_sec=5, thoi_gian_cau=tg_cham(CAU_B))
    r = c.get("/api/research/progress", headers={"X-Session-Token": t})
    assert r.status_code == 200
    van_ban = json.dumps(r.json()).lower()
    assert "flag" not in van_ban and "thoi_gian_cau" not in van_ban and "khoang_ms" not in van_ban


# ---------- Tính lại toàn bộ (scripts/compute_flags.py dùng hàm này) ----------

def tao_hai_nguoi(c, db):
    nop_b(c, vao(c, db), duration_sec=5)    # người 1: làm 5 giây -> bị cờ
    nop_b(c, vao(c, db))                    # người 2: bình thường


def test_tinh_lai_idempotent_va_dry_run_khong_ghi(client):
    c, db = client
    tao_hai_nguoi(c, db)
    db[kho.COL_NGUOI].update_many({}, {"$unset": {"flags": "", "flag_count": ""}})   # giả lập chưa có cờ
    xem = flags_store.tinh_lai_tat_ca(db, ap_dung=False)
    assert xem["tong"] == 2 and xem["doi"] == 2 and xem["co_it_nhat_mot"] == 1
    assert "flags" not in db[kho.COL_NGUOI].find_one()                      # --dry-run: chưa ghi gì
    lan1 = flags_store.tinh_lai_tat_ca(db)
    sau1 = list(db[kho.COL_NGUOI].find({}, {"flags": 1, "flag_count": 1}))
    lan2 = flags_store.tinh_lai_tat_ca(db)
    assert lan1["doi"] == 2 and lan2["doi"] == 0 and lan2["theo_co"] == lan1["theo_co"]
    assert list(db[kho.COL_NGUOI].find({}, {"flags": 1, "flag_count": 1})) == sau1
    assert lan1["theo_co"] == {"lam_qua_nhanh:form_b": 1}


def test_doi_nguong_roi_tinh_lai_thi_cap_nhat(client, monkeypatch):
    c, db = client
    tao_hai_nguoi(c, db)
    flags_store.tinh_lai_tat_ca(db)
    monkeypatch.setitem(config.CO_TONG_GIAY_TOI_THIEU, "form_b", 1)   # hạ ngưỡng: người 5 giây không còn bị cờ
    kq = flags_store.tinh_lai_tat_ca(db)
    assert kq["doi"] == 1 and kq["co_it_nhat_mot"] == 0
    assert all(n["flag_count"] == 0 for n in db[kho.COL_NGUOI].find())


def test_tinh_lai_chi_dong_flags_khong_xoa_gi(client):
    c, db = client
    tao_hai_nguoi(c, db)
    truoc = {b: db[b].count_documents({}) for b in (kho.COL_NGUOI, kho.COL_HANH_VI, kho.COL_MA)}
    flags_store.tinh_lai_tat_ca(db)
    assert {b: db[b].count_documents({}) for b in truoc} == truoc


# ---------- Trình duyệt: trừ thời gian ẩn tab (chạy thoigian.js bằng node) ----------

KICH_BAN_NODE = """
let bay = 0;
const sk = {};
global.performance = { now: () => bay };
global.document = { hidden: false, addEventListener: (ten, f) => { sk[ten] = f; } };
global.tt = { demo: false };
global.docNhap = () => ({}); global.ghiNhap = () => {}; global.xoaNhap = () => {};
__MA__
const doi = (ms) => { bay += ms; };
tgBat("form_b", ["B4_1", "B4_2", "B4_3"]);
doi(2000); tgGhi("B4_1");                                   // câu đầu: 2000 ms từ lúc hiện trang
doi(1000); document.hidden = true; sk.visibilitychange();   // chuyển app 5 giây
doi(5000); document.hidden = false; sk.visibilitychange();
doi(1000); tgGhi("B4_2");                                   // thực tế chỉ xem 2000 ms từ câu trước (5000 ms ẩn bị trừ)
doi(500); tgGhi("B4_1");                                    // sửa lại câu 1: chỉ ghi mốc sửa cuối
tgGhi("XYZ");                                               // câu lạ: bỏ qua
console.log(JSON.stringify(tgLay()));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="cần node để chạy thoigian.js")
def test_trinh_duyet_tru_thoi_gian_an_tab(tmp_path):
    ma = (GOC / "web" / "thoigian.js").read_text(encoding="utf-8")
    tep = tmp_path / "chay.js"
    tep.write_text(KICH_BAN_NODE.replace("__MA__", ma), encoding="utf-8")
    kq = json.loads(subprocess.run(["node", str(tep)], capture_output=True, text=True, check=True).stdout)
    assert kq["khoang_ms"] == {"B4_1": 2000, "B4_2": 2000}
    assert kq["an_tab_ms"] == 5000
    assert kq["sua_cuoi_ms"] == {"B4_1": 4500}       # 2000+1000+1000+500 đang xem (đã trừ 5000 ẩn tab)
    assert kq["tong_ms"] == 4500


def test_trang_choi_nap_thoigian_truoc_app():
    html = (GOC / "web" / "index.html").read_text(encoding="utf-8")
    assert html.index("/play/nhap.js") < html.index("/play/thoigian.js") < html.index("/play/app.js")
