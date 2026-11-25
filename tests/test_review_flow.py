"""Kiểm tra luồng thiết kế lại 25/11: game 2 không lộ đáp án, GET /api/research/review, tên nút thống nhất,
khối hướng dẫn đầu game lấy từ content, luồng đầy đủ tới trang tổng kết, F5 về đúng bước."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_game2 import B, DUNG, SAI, Y, client, completed, nguoi_moi, nop, nop_game1  # noqa: E402,F401
from tests.test_game3 import AI1, BAI, BAI2, T1, T2, bat_dau, nop3, o3, nop_items  # noqa: E402
from tests.test_progress import nop_hanh_vi, nop_tu_danh_gia, tien_do  # noqa: E402

GOC = Path(__file__).resolve().parents[1]
DAU = lambda t: {"X-Session-Token": t}  # noqa: E731
TU_DAP_AN = ("la_loi", "loai_loi", "giai_thich", "sai_nam", "sai_so_lieu", "khai_quat_vo_can_cu", "nhan_qua_vo_can_cu", "ket_qua", "n_correct", "n_wrong")


def doc(rel):
    return (GOC / rel).read_text(encoding="utf-8")


def lam_den_game3(c, db, chon=None, nhan=None):
    """Người chơi làm xong khảo sát, game 1, game 2 (chọn `chon`); chưa làm game 3."""
    t = nguoi_moi(c, db, nhan)
    nop_hanh_vi(c, t)
    nop_tu_danh_gia(c, t)
    nop_game1(c, t)
    nop(c, t, SAI[:2] + DUNG[:1] if chon is None else chon)
    return t


# ---------- Game 2 không lộ đáp án trước khi hoàn thành ----------

def test_game2_nop_xong_van_khong_lo_gi_o_moi_noi(client):
    c, db = client
    t = lam_den_game3(c, db)
    mat = [nop(c, t, []).text, c.post(f"{B}/start", json={"session_token": t}).text, c.get("/api/research/progress", headers=DAU(t)).text,
           c.get("/api/research/result", headers=DAU(t)).text, c.get("/api/content/game3").text, c.get("/api/content/game1").text]
    for chu in mat:
        for tu in TU_DAP_AN:
            assert tu not in chu, tu
    assert nop(c, t, SAI).json() == {"ok": True}


# ---------- GET /api/research/review ----------

def test_review_409_truoc_completed_at_va_khong_co_dap_an(client):
    c, db = client
    t = lam_den_game3(c, db)
    bat_dau(c, t)
    r = c.get("/api/research/review", headers=DAU(t))
    assert r.status_code == 409
    for tu in TU_DAP_AN + ("diem",):
        assert tu not in r.text, tu                                                   # 409 không kèm bất kỳ trường đáp án nào
    nop_items(c, t, [o3(T1, BAI)])                                                    # nộp thiếu ô: vẫn chưa hoàn thành
    assert c.get("/api/research/review", headers=DAU(t)).status_code == 409


def test_review_can_token_dung_header(client):
    c, db = client
    t = lam_den_game3(c, db)
    assert c.get("/api/research/review").status_code == 401
    assert c.get("/api/research/review", headers=DAU("sai")).status_code == 401
    assert c.get("/api/research/review", params={"session_token": t}).status_code == 401   # token không nhận qua URL


def test_review_sau_hoan_thanh_co_dap_an_va_bai_cua_chinh_minh(client):
    c, db = client
    t = lam_den_game3(c, db, chon=SAI[:2] + DUNG[:1])
    bat_dau(c, t)
    nop3(c, t)
    assert completed(db) is not None
    r = c.get("/api/research/review", headers=DAU(t))
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"hanh_vi", "tu_danh_gia", "game1", "game2", "game3"}
    assert d["game1"]["ideas"] == ["a b"] and d["game1"]["do_vat"]["id"] and "diem" not in json.dumps(d["game1"])   # game 1: các ý đã viết, không điểm
    g2 = d["game2"]
    assert g2["diem"] == 1 and g2["diem_toi_da"] == 5                                 # 2 đúng - 1 nhầm
    assert [y["id"] for y in g2["y"]] == [i["id"] for i in Y]                         # 12 ý theo thứ tự cố định
    theo_id = {y["id"]: y for y in g2["y"]}
    assert all(theo_id[i]["da_chon"] for i in SAI[:2] + DUNG[:1]) and sum(y["da_chon"] for y in g2["y"]) == 3
    assert {y["id"] for y in g2["y"] if y["la_loi"]} == set(SAI)                      # cờ 🚩 cho mọi ý sai, kể cả ý không chọn
    assert all(y["giai_thich"] for y in g2["y"]) and theo_id[SAI[0]]["loai_loi"] and theo_id[DUNG[0]]["loai_loi"] is None
    assert [m["noi_dung"] for m in d["game3"]["tinh_huong"]] == [BAI, BAI2]           # game 3: hai ý đã viết, không điểm
    assert "diem" not in json.dumps(d["game3"]) and "thoi_gian" not in r.text and "flags" not in r.text and "paste" not in r.text


def test_review_khong_xem_duoc_bai_nguoi_khac(client):
    c, db = client
    t1 = lam_den_game3(c, db, chon=SAI)
    bat_dau(c, t1)
    nop3(c, t1)
    t2 = lam_den_game3(c, db, chon=[])
    assert c.get("/api/research/review", headers=DAU(t2)).status_code == 409         # người 2 chưa xong game 3
    bat_dau(c, t2)
    nop3(c, t2, b1=AI1 + " thêm vài chữ nữa cho đủ số từ tối thiểu của bài viết này nhé")
    d1, d2 = (c.get("/api/research/review", headers=DAU(t)).json()["game2"] for t in (t1, t2))
    assert d1["diem"] == 5 and d2["diem"] == 0 and not any(y["da_chon"] for y in d2["y"])


# ---------- Luồng đầy đủ tới trang tổng kết, F5 về đúng bước ----------

def test_luong_day_du_va_f5_ve_dung_buoc(client):
    c, db = client
    t = nguoi_moi(c, db)
    assert tien_do(c, t)["next"] == "behavior"
    nop_hanh_vi(c, t)
    assert tien_do(c, t)["next"] == "self_assessment"
    nop_tu_danh_gia(c, t)
    assert tien_do(c, t)["next"] == "game1"
    nop_game1(c, t)
    assert tien_do(c, t)["next"] == "game2"
    c.post(f"{B}/start", json={"session_token": t})                                   # F5 giữa game 2: vẫn game 2
    assert tien_do(c, t)["next"] == "game2"
    assert nop(c, t, SAI).json() == {"ok": True}
    assert tien_do(c, t)["next"] == "game3" and c.get("/api/research/result", headers=DAU(t)).status_code == 409
    bat_dau(c, t)
    assert tien_do(c, t)["next"] == "game3"                                           # F5 giữa game 3: vẫn game 3
    assert nop3(c, t).json() == {"ok": True}
    d = tien_do(c, t)
    assert d["next"] == "completed" and d["completed"] is True                        # F5 / nhập lại mã sau khi xong: dẫn thẳng về tổng kết
    assert c.get("/api/research/result", headers=DAU(t)).json()["che_do"] == "research"
    assert c.get("/api/research/review", headers=DAU(t)).status_code == 200
    app = doc("web/app.js")
    assert 'if (buoc === "completed") { if (laDiaChiXemLai()) manXemLai(xl.phan); else manHoanThanh(); return; }' in app   # completed bỏ qua màn đã nhớ


# ---------- Tên nút thống nhất ----------

def test_ten_nut_tiep_tuc_o_mot_cho_va_nop_bai_chi_o_cuoi_game3():
    ui = json.loads(doc("content/research_ui.json"))
    kq = json.loads(doc("content/results_ui.json"))
    assert ui["chung"]["nut_tiep_tuc"] == "Tiếp tục" and ui["chung"]["nut_nop_bai"] == "Nộp bài"
    cho_phep = {"nut_tiep_tuc", "nut_nop_bai", "nut_demo", "nut_moi", "nut_quay_lai", "nut_thu_lai", "nut_them", "nut_xem_lai", "nut_ghi_chu"}   # nút phụ / thử lại
    nut = {}

    def quet(x, duong=""):
        if isinstance(x, dict):
            for k, v in x.items():
                if k.startswith("nut") and isinstance(v, str):
                    nut[duong + "." + k] = v
                quet(v, duong + "." + k)
        elif isinstance(x, list):
            for v in x:
                quet(v, duong)

    quet(ui)
    quet(kq)
    la = {d: v for d, v in nut.items() if d.rsplit(".", 1)[1] not in cho_phep}
    assert la == {}, la                                                              # không còn nút nào khác tên (nut_nop, nut_bat_dau, nut_luu, nut_xong...)
    cam = ("Nộp", "Gửi", "Lưu và tiếp tục", "Thu hồ sơ", "Bắt đầu", "Sang Game", "Xem kết quả", "Đồng ý và tiếp tục", "Hoàn thành")
    for d, v in nut.items():
        if d.rsplit(".", 1)[1] not in ("nut_nop_bai",):
            assert not any(v.startswith(x) or v == x for x in cam), (d, v)
    assert nut["." + "chung.nut_tiep_tuc"] == "Tiếp tục"


def test_js_moi_nut_di_tiep_lay_chu_o_chung_nut_tiep_tuc():
    html = doc("web/index.html")
    chay = re.findall(r'src="/play/([\w.]+\.js)"', html)
    js = {f: doc("web/" + f) for f in chay}
    for f, s in js.items():
        for cu in ("nut_nop\b", "nut_bat_dau", "nut_luu", "nut_sang_game2", "nut_xong", "nut_ket_qua", "nut_xem\b", "nut_tiep\b", "u.nut\b", "dong_y.nut"):
            assert not re.search(cu, s), (f, cu)
    assert "game3.js" in js and sum(s.count("nut_nop_bai") for s in js.values()) == 1 and "nut_nop_bai" in js["game3.js"]   # "Nộp bài" chỉ ở game 3
    for f, so_nut in (("app.js", 6), ("game1.js", 3), ("game2.js", 2), ("demo.js", 2)):
        assert js[f].count("nut_tiep_tuc") >= so_nut, f                              # nhập mã, đồng ý, sửa thông tin, B, C, tiếp tục bài; giới thiệu, game 1 x2; game 2 x2; demo x2
    khong = r"(Nộp bài|Tiếp tục|Gửi|Lưu và tiếp tục|Thu hồ sơ|Bắt đầu|Hoàn thành)"
    for f, s in js.items():                                                          # chữ nút không viết cứng trong JS
        assert not re.search(r'h\("button"[^;\n]*"' + khong + '"', s), f
    assert "nutGui(\"Tiếp tục\"" not in "".join(js.values())


# ---------- Khối hướng dẫn đầu game ----------

def test_gioi_thieu_bon_muc_lay_tu_content_cho_ca_ba_game(client):
    c, db = client
    ui = json.loads(doc("content/research_ui.json"))
    assert {k: v["nhan"] for k, v in ui["giao_dien"]["khoi_gioi_thieu"].items()} == {
        "nhiem_vu": "Nhiệm vụ", "cach_choi": "Cách chơi", "luu_y": "Lưu ý", "thoi_gian": "Thời gian ước tính"}
    t = nguoi_moi(c, db)
    gt = {1: c.get("/api/content/game1").json()["gioi_thieu"], 2: c.post(f"{B}/start", json={"session_token": t}).json()["gioi_thieu"],
          3: c.get("/api/content/game3").json()["gioi_thieu"]}
    for so, g in gt.items():
        assert list(g) == ["nhiem_vu", "cach_choi", "luu_y", "thoi_gian"], so
        assert all(isinstance(v, list) and v and all(isinstance(x, str) and x for x in v) for v in g.values()), so
        nd = json.loads(doc(f"content/games/game{so}.json"))
        assert "huong_dan" not in nd and "loi_dan" not in nd, so                      # không còn đoạn văn cũ (một nguồn duy nhất)
    assert "huong_dan" not in c.get("/api/content/game1").json()
    assert gt[2]["thoi_gian"] == ["Khoảng 3–4 phút."] and gt[3]["thoi_gian"] == ["Khoảng 5–8 phút cho 2 tình huống."]
    assert gt[2]["cach_choi"][0] == 'Tích chọn những ý bạn cho là sai.' and "ít nhất 80 ký tự" in gt[3]["cach_choi"][0]
    assert "Sau khi bấm Tiếp tục bạn không sửa lại được phần này." in gt[2]["luu_y"] and any("nộp cả hai tình huống một lần" in x for x in gt[3]["luu_y"])   # ghi chú chân trang cũ nay nằm ở "Lưu ý"
    for so, f in ((1, "game1.js"), (2, "game2.js"), (3, "game3.js")):
        assert f"manGameGioiThieu({so}, manGame{so}, " in doc("web/" + f) and "khoiGioiThieu(" not in doc("web/" + f).split(chr(10), 3)[3], f   # trang giới thiệu riêng; trang làm bài không còn khối hướng dẫn
    assert "khoiGioiThieu(r.du_lieu.gioi_thieu)" in doc("web/game_chung.js")
    d = c.get("/api/content/gioi-thieu/2").json()
    assert set(d) == {"so", "ten", "gioi_thieu"} and "la_loi" not in json.dumps(d) and c.get("/api/content/gioi-thieu/4").status_code == 404
    assert "khoiGioiThieu" in doc("web/game_chung.js") and "ghi_chu_khong_sua" not in ui["game2"]


# ---------- Giao diện game 2 và trang xem lại ----------

def test_game2_man_choi_va_man_on_lai_hai_cot():
    g2, rv, css = doc("web/game2.js"), doc("web/review.js"), doc("web/style.css")
    assert "thanh_dem" not in g2 and "thanh-dem-y2" not in g2 and "ghi_chu_khong_sua" not in g2
    assert "r.du_lieu" not in g2.split("async function nopGame2")[1]                       # nộp xong không đọc gì từ phản hồi (chỉ {ok})
    assert 'goiApi("/api/research/review"' in rv and "X-Session-Token" in rv and "diDenBuocDangLam();" in rv.split("if (r.status !== 200)")[1][:60]   # 409 -> về bước đang dở
    assert "u.diem.replace" in rv and "menuNhayY2" in rv and "scrollIntoView" in rv and "xl-y-" in rv                         # Điểm x/5 + menu nhảy tới ý 1–12
    assert '"chon-dung"' in rv and '"chon-nham"' in rv and '"khong-chon"' in rv and '"✓"' in rv and '"✗"' in rv           # xanh/đỏ/xám có ✓ ✗
    assert "if (y.la_loi)" in rv and "tooltipY2(y)" in rv and rv.count("tooltipY2(y)") == 2                                  # chỉ ý sai mới có cờ + tooltip
    assert "mo-tt" in rv and "Escape" in rv and 'type: "button", class: "co-sai"' in rv                                      # chạm mở/đóng, bàn phím (nút focus được)
    assert "@media (hover: hover) { .co-sai:hover ~ .tooltip-y2" in css and ".co-sai:focus-visible ~ .tooltip-y2" in css
    assert "position: sticky" in css.split(".cot-trai-xl {")[1].split("}")[0] and "overflow-x: auto" in css.split("max-width: 699px) {\n  .bo-cuc-xl2")[1]
    assert "min-width: 44px; min-height: 44px" in css                                  # nút đủ lớn để chạm
    sw = doc("web/result.js")
    assert "manXemLai()" in sw and "nut_xem_lai" in sw and "manCamOn" not in sw and "manChuaXong" not in doc("web/app.js")
    assert "game1: veXlGame1, game2: veXlGame2, game3: veXlGame3 }" in rv and "THU_TU_XL" in rv                    # năm phần chuyển bằng nút mũi tên


def test_trang_tong_ket_co_cam_on_va_email_mailto_o_cuoi():
    ui = json.loads(doc("content/research_ui.json"))["hoan_thanh"]
    assert ui["mo_ta"].endswith("vui lòng liên hệ:") and ui["email"] == "nguyenthitrang.ttd@gmail.com"
    assert "nguyenthitrang" not in doc("web/result.js")                                # email không viết cứng trong code
    js = doc("web/result.js")
    assert '"mailto:" + u.email' in js and "cuoiTrang" in js and "dauTrang" not in js
    assert js.index("mucDongGop(), tuyChon.cuoiTrang") > 0                          # khối cảm ơn đứng sau mọi khối kết quả, trước nút
