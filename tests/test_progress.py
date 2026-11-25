"""Kiểm tra tiến độ và khôi phục (F5 / nhập lại mã), điền sẵn, sửa khảo sát trước completed_at, tô màu kết quả game 2."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sparkmind import config  # noqa: E402
from tests.test_game2 import B, DUNG, SAI, Y, client, nguoi_moi, nop, nop_game1  # noqa: E402,F401
from tests.test_research import BAT_DAU, HANH_VI, TU_DANH_GIA  # noqa: E402

GOC = Path(__file__).resolve().parents[1]


def tien_do(c, t):
    r = c.get("/api/research/progress", headers={"X-Session-Token": t})
    assert r.status_code == 200
    return r.json()


def nop_hanh_vi(c, t, **sua):
    return c.post("/api/research/behavior", json={"session_token": t, **HANH_VI, **sua})


def nop_tu_danh_gia(c, t, **sua):
    return c.post("/api/research/self-assessment", json={"session_token": t, **TU_DANH_GIA, **sua})


# ---------- B. F5 sau mỗi bước đưa đúng về bước dở dang ----------

def test_tien_do_sau_tung_buoc(client):
    c, db = client
    t = nguoi_moi(c, db)
    assert tien_do(c, t)["next"] == "behavior"                    # vừa nhập thông tin xong
    nop_hanh_vi(c, t)
    assert tien_do(c, t)["next"] == "self_assessment"
    nop_tu_danh_gia(c, t)
    assert tien_do(c, t)["next"] == "game1"
    nop_game1(c, t)
    d = tien_do(c, t)
    assert d["next"] == "game2" and d["steps"]["game1"] is True and d["steps"]["game2"] is False
    nop(c, t, SAI)
    d = tien_do(c, t)
    assert d["next"] == "game3" and d["completed"] is False   # xong game 2: bước kế tiếp là game 3


def test_bat_dau_game_nhung_chua_nop_van_o_buoc_do(client):
    c, db = client
    t = nguoi_moi(c, db)
    nop_hanh_vi(c, t)
    nop_tu_danh_gia(c, t)
    c.post("/api/research/game1/start", json={"session_token": t})    # mở game 1 rồi F5, chưa nộp
    assert tien_do(c, t)["next"] == "game1"


def test_tien_do_completed(client, monkeypatch):
    c, db = client
    monkeypatch.setattr(config, "GAME_BAT_BUOC", (1, 2))
    monkeypatch.setattr(config, "GAME_DA_CO", (1, 2))   # giả lập giai đoạn chỉ có 2 game
    t = nguoi_moi(c, db)
    nop_hanh_vi(c, t)
    nop_tu_danh_gia(c, t)
    nop_game1(c, t)
    nop(c, t, SAI)
    d = tien_do(c, t)
    assert d["next"] == "completed" and d["completed"] and d["locked"]


def test_tien_do_can_token_dung_va_rieng_tung_nguoi(client):
    c, db = client
    assert c.get("/api/research/progress").status_code == 401
    assert c.get("/api/research/progress", headers={"X-Session-Token": "sai"}).status_code == 401
    t1, t2 = nguoi_moi(c, db), nguoi_moi(c, db)
    nop_hanh_vi(c, t1)
    assert tien_do(c, t2)["answers"]["behavior"] is None and tien_do(c, t2)["next"] == "behavior"
    assert c.get("/api/research/progress", params={"session_token": t1}).status_code == 401   # token không nhận qua URL


def test_nhap_lai_ma_cung_email_ve_dung_buoc(client):
    c, db = client
    ma = db["access_codes"].insert_one({"code": "ABCD2345", "source": "volunteer", "is_used": False, "used_at": None}).inserted_id
    t = c.post("/api/research/start", json={"code": "ABCD2345", **BAT_DAU}).json()["session_token"]
    nop_hanh_vi(c, t)
    assert c.post("/api/research/code/check", json={"code": "ABCD2345"}).json() == {"valid": False, "can_resume": True}
    t2 = c.post("/api/research/start", json={"code": "ABCD2345", **BAT_DAU}).json()["session_token"]
    assert t2 == t and tien_do(c, t2)["next"] == "self_assessment" and ma


# ---------- Điền sẵn khi quay lại ----------

def test_dien_san_cau_tra_loi(client):
    c, db = client
    t = nguoi_moi(c, db)
    nop_hanh_vi(c, t, B3=[1, 8], B3_other="Làm thơ")
    nop_tu_danh_gia(c, t)
    a = tien_do(c, t)["answers"]
    assert a["info"] == {"A1": 6, "A2": 2, "A3": "THPT Bắc Bình", "guardian_consent": True}
    assert a["behavior"]["A4"] == 1 and a["behavior"]["B1"] == [1, 2] and a["behavior"]["B3"] == [1, 8]
    assert a["behavior"]["B2"] == 2 and a["behavior"]["B6"] == [1, 3] and a["behavior"]["B4_3"] == 2
    assert a["behavior"]["B3_other"] == "Làm thơ" and a["behavior"]["B1_other"] is None
    assert a["self_assessment"] == {"C1": 4, "C2": 3, "C3": 4, "C4": 5, "C5": 4, "C6": 3}


def test_dien_san_a4_chua_tung_dung(client):
    c, db = client
    t = nguoi_moi(c, db)
    assert c.post("/api/research/behavior", json={"session_token": t, "A4": 4, "duration_sec": 5}).status_code == 200
    b = tien_do(c, t)["answers"]["behavior"]
    assert b["A4"] == 4 and b["B1"] is None and b["B4_1"] is None


# ---------- Sửa khảo sát: được trước completed_at, bị chặn sau ----------

def test_sua_khao_sat_ghi_so_lan_sua_va_sua_luc(client):
    c, db = client
    t = nguoi_moi(c, db)
    nop_hanh_vi(c, t)
    nop_tu_danh_gia(c, t)
    assert nop_hanh_vi(c, t, edit=True, B2=3).status_code == 200
    assert nop_tu_danh_gia(c, t, edit=True, C1=1).status_code == 200
    assert c.post("/api/research/info/update", json={"session_token": t, "grade": 6, "gender": 1, "school_name": "THPT Mới", "guardian_consent": True}).status_code == 200
    hv, tdg, nguoi = (db[x].find_one() for x in ("behavior_answers", "self_assessment", "participants"))
    assert hv["so_lan_sua"] == 1 and hv["sua_luc"] and hv["b2_frequency"] == "3"
    assert tdg["so_lan_sua"] == 1 and tdg["sua_luc"] and tdg["c1"] == 1
    assert nguoi["so_lan_sua"] == 1 and nguoi["sua_luc"] and db["behavior_answers"].count_documents({}) == 1   # ghi đè, không thêm bản ghi


def test_khong_sua_duoc_sau_completed_at(client, monkeypatch):
    c, db = client
    monkeypatch.setattr(config, "GAME_BAT_BUOC", (1, 2))
    t = nguoi_moi(c, db)
    nop_hanh_vi(c, t)
    nop_tu_danh_gia(c, t)
    nop_game1(c, t)
    nop(c, t, SAI)
    assert db["participants"].find_one()["completed_at"]
    assert nop_hanh_vi(c, t, edit=True, B2=3).status_code == 403
    assert nop_tu_danh_gia(c, t, edit=True, C1=1).status_code == 403
    info = {"session_token": t, "grade": 6, "gender": 1, "school_name": "Trường khác", "guardian_consent": True}
    assert c.post("/api/research/info/update", json=info).status_code == 403
    assert db["behavior_answers"].find_one()["b2_frequency"] == "2" and db["self_assessment"].find_one()["c1"] == 4
    assert db["participants"].find_one()["school_name"] == "THPT Bắc Bình"


def test_sua_khao_sat_khong_doi_diem_game_va_completed_at(client, monkeypatch):
    c, db = client
    t = nguoi_moi(c, db)
    nop_hanh_vi(c, t)
    nop_tu_danh_gia(c, t)
    nop_game1(c, t)
    nop(c, t, SAI[:3] + DUNG[:1])
    truoc = [db["game_responses"].find_one({"game": g}) for g in (1, 2)]
    nguoi_truoc = db["participants"].find_one()["completed_at"]
    nop_hanh_vi(c, t, edit=True, B2=3)
    nop_tu_danh_gia(c, t, edit=True, C5=1)
    assert [db["game_responses"].find_one({"game": g}) for g in (1, 2)] == truoc
    assert db["participants"].find_one()["completed_at"] == nguoi_truoc


# ---------- Game đã nộp thì không làm lại ----------

def test_game_da_nop_khong_lam_lai(client):
    c, db = client
    t = nguoi_moi(c, db)
    nop_game1(c, t)
    luu1 = db["game_responses"].find_one({"game": 1})
    r = c.post("/api/research/game1/submit", json={"session_token": t, "ideas": ["khác hẳn"], "paste_count": 9, "tab_leave_count": 9})
    assert r.status_code == 409 and db["game_responses"].find_one({"game": 1}) == luu1
    s = c.post("/api/research/game1/start", json={"session_token": t}).json()
    assert s["submitted"] is True
    nop(c, t, SAI)
    luu2 = db["game_responses"].find_one({"game": 2})
    c.post(f"{B}/submit", json={"session_token": t, "chon": []})
    assert db["game_responses"].find_one({"game": 2}) == luu2
    assert c.post(f"{B}/start", json={"session_token": t}).json()["submitted"] is True


def test_giao_dien_khoi_dong_hoi_tien_do():
    js = (GOC / "web/app.js").read_text(encoding="utf-8")
    assert '"/api/research/progress"' in js and "X-Session-Token" in js and "dienSanCauTraLoi" in js
    assert "diDenBuocDangLam(" in js and "batDauTheoTrangThai()" in js    # mở web: quyết định theo trạng thái
    assert "can_resume" in js                                            # nhập lại mã dùng dở thì cho vào


# ---------- Lối thoát máy dùng chung & tên game đánh số ----------

def test_vao_lai_web_hoi_tiep_tuc_hay_lam_moi():
    """Tải lại trang (còn dấu trong tab) -> ở lại đúng màn; vào lại sau khi thoát -> hỏi; "Dùng mã khác" chỉ quên trong trình duyệt."""
    import json
    import re
    js = (GOC / "web/app.js").read_text(encoding="utf-8")
    ui = json.loads((GOC / "content/research_ui.json").read_text(encoding="utf-8"))
    assert "doi_ma" not in ui and "lienKetDoiMa" not in js and "Không phải bạn" not in json.dumps(ui, ensure_ascii=False)   # bỏ dòng "Không phải bạn?" cuối màn
    assert "nut_tiep" not in ui["tiep_tuc"] and ui["tiep_tuc"]["nut_moi"] == "Dùng mã khác"   # nút đi tiếp lấy chữ ở chung.nut_tiep_tuc
    kho = re.search(r"function batDauTheoTrangThai\(\) \{.*?\n\}", js, re.S).group(0)
    assert "man.token === luu) || laDiaChiXemLai()) diDenBuocDangLam(true); else manTiepTuc()" in kho   # có dấu trong tab (hoặc mở thẳng #xem-lai) = vào luôn; không có = hỏi
    ham = re.search(r"function thoatPhien\(\) \{.*?\n\}", js, re.S).group(0)
    assert "localStorage.removeItem(KHOA_TOKEN)" in ham and "manMa()" in ham and "xoaNhap()" in ham
    assert "goiApi" not in ham and "fetch" not in ham                                # không xóa gì trên máy chủ
    assert "onclick: thoatPhien" in js.split("function manTiepTuc")[1].split("\n}")[0]


def test_giu_man_khi_tai_lai_va_quay_lai_moi_trang():
    """Mỗi màn ghi tên màn (datMan); tải lại thì mở đúng màn nếu chưa vượt bước đã tới; có thể quay lại mọi trang trước."""
    import re
    js = {f: (GOC / "web" / f).read_text(encoding="utf-8") for f in ("app.js", "game1.js", "game2.js", "nhap.js", "result.js", "review.js", "game_chung.js")}
    for ten, f in (("ma", "app.js"), ("thong_tin", "app.js"), ("sua_thong_tin", "app.js"), ("b", "app.js"), ("c", "app.js"),
                   ("tong_ket", "result.js"), ("xem_lai", "review.js"), ("gioi_thieu", "game1.js"), ("game1", "game1.js"), ("game2", "game2.js"), ("_gt", "game_chung.js")):
        assert f'"{ten}"' in js[f] and "datMan(" in js[f], ten
    assert 'THU_TU_MAN = ["sua_thong_tin", "b", "c", "gioi_thieu", "game1_gt", "game1", "game2_gt", "game2", "game3_gt", "game3"]' in js["app.js"]
    assert "indexOf(luu.man) <= THU_TU_MAN.indexOf(dich.xa)" in js["app.js"]          # không vượt quá bước đã tới
    assert "sessionStorage" in js["nhap.js"] and "docMan" in js["nhap.js"]
    # nút Quay lại ở các màn trước (game 1 chơi + xem lại, game 2 chơi + kết quả, trang "xong", đồng ý -> nhập mã)
    assert js["game1.js"].count("nutQuayLai(manGame1GioiThieu)") == 2 and js["game2.js"].count("nutQuayLai(manGame2GioiThieu)") == 1   # trang làm bài quay về trang giới thiệu của chính game
    assert "nutQuayLai(manMa)" in js["app.js"] and "chua_xong" not in js["app.js"]          # không còn trang "chơi xong" giữa chừng
    # rời game 1 thì đồng hồ dừng, không tự nộp khi đang ở màn khác
    assert "g1.dangChoi = false; clearInterval(g1.nhip)" in js["app.js"] and "g1.dangChoi" in js["game1.js"]


def test_nut_tiep_tuc_va_nut_xanh_ben_phai():
    import json
    ui = json.loads((GOC / "content/research_ui.json").read_text(encoding="utf-8"))
    assert ui["chung"]["nut_tiep_tuc"] == "Tiếp tục" and "Lưu và tiếp tục" not in json.dumps(ui, ensure_ascii=False)
    css = (GOC / "web/style.css").read_text(encoding="utf-8")
    assert "body.man-gioi-thieu .thanh-nut { flex-wrap: nowrap; justify-content: center; }" in css   # luôn cùng một hàng, căn giữa
    assert ".thanh-nut { display: flex; flex-wrap: wrap; justify-content: center;" in css                     # mọi trang: căn giữa
    assert "body.man-gioi-thieu .thanh-nut > button:not(.phu) { order: 2; }" in css and "body.man-gioi-thieu .thanh-nut > .phu { order: 1; }" in css


def test_thoat_phien_khong_mat_du_lieu_nguoi_truoc(client):
    """Máy chủ không có endpoint xóa: người trước nhập lại mã cùng email vẫn nhận lại token cũ và tiến độ cũ."""
    c, db = client
    db["access_codes"].insert_one({"code": "ABCD2345", "source": "volunteer", "is_used": False, "used_at": None})
    t = c.post("/api/research/start", json={"code": "ABCD2345", **BAT_DAU}).json()["session_token"]
    nop_hanh_vi(c, t)
    # (client xóa token ở đây) rồi người trước nhập lại mã
    t2 = c.post("/api/research/start", json={"code": "ABCD2345", **BAT_DAU}).json()["session_token"]
    d = tien_do(c, t2)
    assert t2 == t and d["next"] == "self_assessment" and d["answers"]["behavior"]["B2"] == 2
    assert db["behavior_answers"].count_documents({}) == 1


def test_ten_game_danh_so_tu_mot_cho(client):
    import json
    c, db = client
    g = {n: json.loads((GOC / f"content/games/game{n}.json").read_text(encoding="utf-8"))["ten"] for n in (1, 2, 3)}
    assert g == {1: "Đồ vật bí ẩn", 2: "Soi lỗi AI", 3: "Làm tốt hơn AI"}
    assert json.loads((GOC / "content/research_ui.json").read_text(encoding="utf-8"))["tieu_game"] == "Game {so}: {ten}"
    assert c.get("/api/content/game1").json()["ten"] == g[1]                         # game 1 lấy tên qua content
    assert c.post(f"{B}/start", json={"session_token": nguoi_moi(c, db)}).json()["ten"] == g[2]
    assert c.get("/api/content/game3").json()["ten"] == g[3] and "tenGame(nd.so, nd.ten)" in (GOC / "web/game3.js").read_text(encoding="utf-8")   # game 3: số và tên cùng lấy từ content
    js1, js2 = (GOC / "web/game1.js").read_text(encoding="utf-8"), (GOC / "web/game2.js").read_text(encoding="utf-8")
    assert "tenGame(1, nd.ten)" in js1 and "tenGame(2, bd.ten)" in js2
    assert "Soi lỗi AI" not in json.dumps(json.loads((GOC / "content/research_ui.json").read_text(encoding="utf-8"))["game2"])  # không viết lặp tên ở chỗ khác


def test_chua_nop_khong_co_diem(client):
    c, db = client
    d = c.post(f"{B}/start", json={"session_token": nguoi_moi(c, db)}).json()
    assert "diem" not in d and "n_correct" not in d


# ---------- Lần sửa 24/11 (chiều): viền lỗi, bản nháp, xem lại game, bố cục game 2 ----------

def test_vien_loi_khong_de_len_nhau():
    """Viền đỏ vẽ BÊN TRONG khung (inset) và các hàng thang 1-5 có khoảng cách, nên không đè lên nhau (không dùng outline lòi ra ngoài)."""
    css = (GOC / "web/style.css").read_text(encoding="utf-8")
    luat = css.split(".thieu {")[1].split("}")[0]
    assert "inset 0 0 0 2px" in luat and "outline" not in luat
    assert ".hang-luoi + .hang-luoi { margin-top" in css and ".thieu > .loi-cau { grid-column: 1 / -1" in css


def test_ban_nhap_giu_cau_dang_go_khi_f5():
    js = (GOC / "web/app.js").read_text(encoding="utf-8")
    nhap = (GOC / "web/nhap.js").read_text(encoding="utf-8")
    html = (GOC / "web/index.html").read_text(encoding="utf-8")
    assert "sessionStorage" in nhap and "localStorage" not in nhap                  # chỉ sống trong tab, không lưu lâu dài
    assert html.index("/play/nhap.js") < html.index("/play/app.js")
    assert 'ghiNhap("tl", tt.tl)' in js and "docNhap().tl" in js                    # khảo sát: ghi khi gõ, đọc khi F5
    assert "xoaNhap();" in js.split("function thoatPhien()")[1].split("}")[0]      # thoát phiên thì xóa luôn bản nháp
    for f, khoa in (("game1.js", 'ghiNhap("g1"'), ("game1.js", 'docNhap().g1'), ("game2.js", 'ghiNhap("g2"'), ("game2.js", 'docNhap().g2')):
        assert khoa in (GOC / "web" / f).read_text(encoding="utf-8")


def test_game1_da_nop_tra_lai_y_de_xem_lai(client):
    c, db = client
    t = nguoi_moi(c, db)
    d = c.post("/api/research/game1/start", json={"session_token": t}).json()
    assert "ideas" not in d                                                          # chưa nộp thì không có
    c.post("/api/research/game1/submit", json={"session_token": t, "ideas": ["  đỡ cây ", "kê bàn"], "paste_count": 0, "tab_leave_count": 0})
    d = c.post("/api/research/game1/start", json={"session_token": t}).json()
    assert d["submitted"] is True and d["ideas"] == ["đỡ cây", "kê bàn"] and d["do_vat"]["id"]
    t2 = nguoi_moi(c, db)
    assert "ideas" not in c.post("/api/research/game1/start", json={"session_token": t2}).json()   # không thấy bài người khác


def test_giao_dien_xem_lai_game_da_nop():
    j1, j2 = (GOC / "web/game1.js").read_text(encoding="utf-8"), (GOC / "web/game2.js").read_text(encoding="utf-8")
    assert "veGame1DaNop(bd.du_lieu, nd.du_lieu)" in j1 and "function veGame1DaNop" in j1
    ham = j1.split("function veGame1DaNop")[1].split("// ----------")[0]
    assert "input" not in ham and "nopGame1" not in ham                              # chỉ xem, không ô nhập, không nút nộp
    assert "veGame2(r.du_lieu)" in j2 and "khoa = bd.submitted" in j2 and "disabled: khoa" in j2   # game 2 đã nộp: bản khóa, không sửa được


def test_ten_game_la_dai_to_va_co_o_moi_man_game():
    j1, j2 = (GOC / "web/game1.js").read_text(encoding="utf-8"), (GOC / "web/game2.js").read_text(encoding="utf-8")
    assert j1.count("tenGame(1, nd.ten)") >= 2                                       # màn chơi và màn xem lại
    assert j2.count("tenGame(2, bd.ten)") == 1 and "tenGame(2, g.ten)" in (GOC / "web/review.js").read_text(encoding="utf-8")   # màn đánh dấu; màn ôn lại ở review.js
    assert ".ten-game {" in (GOC / "web/style.css").read_text(encoding="utf-8")


def test_bo_cuc_game2_moi():
    import json
    j2 = (GOC / "web/game2.js").read_text(encoding="utf-8")
    css = (GOC / "web/style.css").read_text(encoding="utf-8")
    assert "theYGame2" in j2 and "lua-chon the-y2" in j2 and 'type: "checkbox"' in j2   # thẻ đánh số dùng ô tích như câu chọn nhiều đáp án
    assert "gat-y2" not in j2 and "thanh-dem-y2" not in j2 and "chot-y" not in j2       # không còn nút gạt, thanh dính, chữ chân trang
    assert ".lua-chon:has(input:checked)" in css and ".the-y2:has(input:checked)" not in css and "thanh-dem-y2" not in css and ".gat-y2" not in css
    ui = json.loads((GOC / "content/research_ui.json").read_text(encoding="utf-8"))["game2"]
    assert "nhan_sai" not in ui and "nhan-sai-y2" not in j2 and "thanh_dem" not in ui and "danh_dau" not in ui


def test_dong_ho_game1_khong_dinh_va_doi_mau_chu_khi_sap_het_gio():
    css = (GOC / "web/style.css").read_text(encoding="utf-8")
    khung = css.split(".khung-gio {")[1].split("}")[0]
    assert "sticky" not in khung and "fixed" not in khung                                # cuộn theo trang như phần tử thường
    assert ".khung-gio.vang .chu-gio" in css and ".khung-gio.do .chu-gio" in css         # sắp hết giờ: đổi màu chữ
    assert 'dh.khung.classList.toggle("do"' in (GOC / "web/game1.js").read_text(encoding="utf-8")


def test_giao_dien_nguoi_choi_khong_bi_ket_cache_cu(client):
    c, _ = client
    r = c.get("/play/app.js")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"        # luôn hỏi lại (ETag), sửa JS là có hiệu lực
    assert c.get("/play/game2.js").headers["cache-control"] == "no-cache"
    assert "no-cache" not in c.get("/api/content/ui").headers.get("cache-control", "")
