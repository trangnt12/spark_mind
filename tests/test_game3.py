"""Kiểm tra game 3 (Làm tốt hơn AI): nội dung, thứ tự, giới hạn từ/ký tự, nộp trùng, completed_at, khôi phục F5, cờ, quản trị."""
import json
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(GOC / "src"))
from sparkmind import config, flags, flags_store, game3_store  # noqa: E402
from tests.test_game2 import SAI, client, completed, nguoi_moi, nop, nop_game1  # noqa: E402,F401
from tests.test_progress import nop_hanh_vi, nop_tu_danh_gia, tien_do  # noqa: E402

B = "/api/research/game3"
ND = game3_store.noi_dung_game3()
T1, T2 = (t["id"] for t in ND["tinh_huong"])
AI1, AI2 = (t["ai_goc"] for t in ND["tinh_huong"])
BAI = "Mình sẽ cho sinh viên đổi vỏ chai lấy điểm cộng rèn luyện, rồi dùng số điểm đó để đổi suất ăn giảm giá ngay tại căng tin trường."
BAI2 = "Mỗi lớp năm nhất có một anh chị khóa trên làm người dẫn đường, cùng đi ăn trưa và tham quan trường trong tuần đầu tiên."


def bat_dau(c, t):
    return c.post(f"{B}/start", json={"session_token": t})


def o3(tinh_huong_id, noi_dung, dan=0, roi=0, giay=60):
    return {"tinh_huong_id": tinh_huong_id, "noi_dung": noi_dung, "paste_count": dan, "tab_leave_count": roi, "thoi_gian_giay": giay}


def nop_items(c, t, items):
    return c.post(f"{B}/submit", json={"session_token": t, "items": items})


def nop3(c, t, b1=BAI, b2=BAI2, dan=(0, 0), roi=(0, 0), giay=(60, 60)):
    """Nộp MỘT lần cho cả hai tình huống (đúng như nút "Nộp bài")."""
    return nop_items(c, t, [o3(T1, b1, dan[0], roi[0], giay[0]), o3(T2, b2, dan[1], roi[1], giay[1])])


def bai_game3(db):
    return db["game_responses"].find_one({"game": 3})


# ---------- Nội dung ----------

def test_noi_dung_va_id_co_dinh():
    assert ND["so"] == 3 and ND["ten"] == "Làm tốt hơn AI"
    assert [t["id"] for t in ND["tinh_huong"]] == ["g3_t1", "g3_t2"]            # thứ tự cố định t1 rồi t2
    assert all(t["tieu_de"] and t["ai_goc"] for t in ND["tinh_huong"])
    assert ND["toi_thieu_ky_tu"] == 80 and "toi_thieu_tu" not in ND and ND["toi_da_ky_tu"] == 800
    assert config.GAME_BAT_BUOC == (1, 2, 3) == config.GAME_DA_CO


def test_noi_dung_cho_trinh_duyet_khong_lo_truong_thua(client):
    c, _ = client
    d = c.get("/api/content/game3").json()
    assert set(d) == {"so", "ten", "gioi_thieu", "tinh_huong", "toi_thieu_ky_tu", "toi_da_ky_tu"}   # không có ghi chú nội bộ
    assert set(d["gioi_thieu"]) == {"nhiem_vu", "cach_choi", "luu_y", "thoi_gian"}
    assert all(set(t) == {"id", "tieu_de", "ai_goc"} for t in d["tinh_huong"])
    assert [t["id"] for t in d["tinh_huong"]] == [T1, T2]


def test_start_chi_bao_da_nop_chua(client):
    c, db = client
    t = nguoi_moi(c, db)
    assert bat_dau(c, t).json() == {"submitted": False}
    nop3(c, t, dan=(2, 0), roi=(1, 0))
    assert bat_dau(c, t).json() == {"submitted": True}                              # bài đã nộp xem qua /review, không qua start
    assert nop3(c, t).json() == {"ok": True}                                          # không điểm, không thời gian, không nhận xét


# ---------- Lưu trữ ----------

def test_luu_dung_van_ban_va_cac_so_do(client):
    c, db = client
    t = nguoi_moi(c, db, "thu")
    bat_dau(c, t)
    van_ban = "  " + BAI + "\nDòng hai  có  hai khoảng trắng  "
    assert nop3(c, t, b1=van_ban, dan=(3, 1), roi=(2, 0), giay=(45, 30)).status_code == 200
    bai = bai_game3(db)
    m = bai["answer"]["tinh_huong"][0]
    assert m["tinh_huong_id"] == T1 and m["noi_dung"] == van_ban                 # đúng văn bản người chơi nhập
    assert m["so_tu"] == len(van_ban.split()) and m["so_lan_dan"] == 3 and m["so_lan_roi_tab"] == 2
    assert m["thoi_gian_lam"] == 45 and bai["answer"]["tinh_huong"][1]["thoi_gian_lam"] == 30   # thời gian TỪNG Ô do trình duyệt gửi
    assert bai["data_label"] == "thu" and bai["submitted_at"] is not None
    assert "diem_ai" not in m and "score" not in bai["answer"]                   # điểm chấm sau, ở collection riêng


def test_mot_lan_nop_cho_ca_hai_co_so_tong_va_thoi_gian_server(client):
    c, db = client
    t = nguoi_moi(c, db)
    bat_dau(c, t)
    assert bai_game3(db)["submitted_at"] is None
    assert nop3(c, t, dan=(1, 2), roi=(0, 3)).json() == {"ok": True}
    bai = bai_game3(db)
    assert bai["submitted_at"] is not None and [m["tinh_huong_id"] for m in bai["answer"]["tinh_huong"]] == [T1, T2]
    assert (bai["paste_count"], bai["tab_leave_count"]) == (3, 3) and bai["answer_length"] == len(BAI) + len(BAI2)
    assert bai["duration_sec"] < 120                                                 # duration_sec = cả game, SERVER tính (không phải tổng 60 + 60 giây ô gửi lên)
    assert db["game_responses"].count_documents({"game": 3}) == 1                  # một bản ghi, hai mục


# ---------- Kiểm tra đầu vào ----------

def test_moi_o_toi_thieu_80_ky_tu_va_khong_ghi_gi_neu_thieu(client):
    c, db = client
    t = nguoi_moi(c, db)
    bat_dau(c, t)
    r = nop3(c, t, b2="a" * 79)
    assert r.status_code == 422 and "80 ký tự" in r.json()["detail"]                 # 79 ký tự: thiếu 1
    assert bai_game3(db)["answer"]["tinh_huong"] == [] and bai_game3(db)["submitted_at"] is None   # thiếu một ô thì không lưu ô nào
    assert nop3(c, t, b1="   \n  ").status_code == 422                              # toàn khoảng trắng
    assert nop3(c, t, b1=" " + "a" * 79, b2="a" * 80).status_code == 422             # khoảng trắng hai đầu không được tính
    assert nop3(c, t, b1="a" * 80, b2="a b " * 21).status_code == 200                # đúng 80 ký tự thì được (không cần đủ 15 từ)
    assert bai_game3(db)["answer"]["tinh_huong"][0]["so_tu"] == 1                    # server vẫn tính và lưu so_tu


def test_toi_da_800_ky_tu(client):
    c, db = client
    t = nguoi_moi(c, db)
    bat_dau(c, t)
    r = nop3(c, t, b1=("abcd " * 200)[:801])
    assert r.status_code == 422 and "800" in r.json()["detail"]
    assert nop3(c, t, b1=("abcd " * 200)[:800]).status_code == 200                  # đúng 800 ký tự thì được


def test_phai_du_hai_tinh_huong_khong_thieu_thua_trung(client):
    c, db = client
    t = nguoi_moi(c, db)
    assert nop3(c, t).status_code == 409                                             # chưa bắt đầu
    bat_dau(c, t)
    assert nop_items(c, t, [o3(T1, BAI)]).status_code == 422                          # thiếu tình huống 2
    assert nop_items(c, t, [o3(T1, BAI), o3(T1, BAI)]).status_code == 422             # trùng
    assert nop_items(c, t, [o3(T1, BAI), o3("g3_xyz", BAI2)]).status_code == 422      # id lạ
    assert nop_items(c, t, [o3(T1, BAI), o3(T2, BAI2), o3(T1, BAI)]).status_code == 422   # thừa
    assert nop_items(c, t, []).status_code == 422
    assert nop3(c, "token-sai").status_code == 401
    assert bai_game3(db)["answer"]["tinh_huong"] == [] and bai_game3(db)["submitted_at"] is None
    assert nop_items(c, t, [o3(T2, BAI2), o3(T1, BAI)]).status_code == 200            # thứ tự gửi lên không quan trọng
    assert [m["tinh_huong_id"] for m in bai_game3(db)["answer"]["tinh_huong"]] == [T1, T2]   # nhưng lưu đúng thứ tự trong content


def test_thoi_gian_o_phai_hop_le(client):
    c, db = client
    t = nguoi_moi(c, db)
    bat_dau(c, t)
    assert nop3(c, t, giay=(-1, 60)).status_code == 422
    assert nop3(c, t, giay=(60, 86401)).status_code == 422


# ---------- Không sửa, không nộp trùng ----------

def test_nop_trung_khong_ghi_de_va_khong_sua_sau_khi_nop(client):
    c, db = client
    t = nguoi_moi(c, db)
    bat_dau(c, t)
    nop3(c, t, dan=(1, 0))
    luu = bai_game3(db)
    r = nop3(c, t, b1="Một nội dung khác hẳn, cố tình sửa lại bài đã nộp trước đó để thử xem có được hay không nhé", dan=(9, 9))
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert bai_game3(db) == luu and [m["noi_dung"] for m in luu["answer"]["tinh_huong"]] == [BAI, BAI2]
    assert db["game_responses"].count_documents({"game": 3}) == 1


# ---------- Hoàn thành ----------

def test_completed_at_chi_gan_khi_nop_game_3_va_ket_qua_het_409(client):
    c, db = client
    t = nguoi_moi(c, db)
    nop_hanh_vi(c, t)
    nop_tu_danh_gia(c, t)
    nop_game1(c, t)
    nop(c, t, SAI)
    assert tien_do(c, t)["next"] == "game3" and completed(db) is None
    assert c.get("/api/research/result", headers={"X-Session-Token": t}).status_code == 409
    bat_dau(c, t)
    assert nop_items(c, t, [o3(T1, BAI)]).status_code == 422                          # thiếu ô: chưa hoàn thành
    assert completed(db) is None and tien_do(c, t)["next"] == "game3"
    nop3(c, t)
    d = tien_do(c, t)
    assert completed(db) is not None and d["completed"] is True and d["next"] == "completed" and d["steps"]["game3"] is True
    r = c.get("/api/research/result", headers={"X-Session-Token": t})
    assert r.status_code == 200 and r.json()["che_do"] == "research"                 # luồng từ game 3 sang trang tổng kết


def test_nop_game3_truoc_game_1_2_chua_hoan_thanh(client):
    c, db = client
    t = nguoi_moi(c, db)
    bat_dau(c, t)
    nop3(c, t)
    assert completed(db) is None
    assert c.get("/api/research/result", headers={"X-Session-Token": t}).status_code == 409


# ---------- Cờ chất lượng ----------

def muc(noi_dung, giay, tinh_huong_id=T1):
    return {"tinh_huong_id": tinh_huong_id, "noi_dung": noi_dung, "thoi_gian_lam": giay}


def test_co_game3_nhanh():
    ai = game3_store.ai_goc_theo_id()
    assert flags.co_cua_game3([muc(BAI, 29), muc(BAI2, 60, T2)], ai) == ["lam_qua_nhanh:game3"]   # chỉ một tình huống nhanh cũng gắn
    assert flags.co_cua_game3([muc(BAI, 30), muc(BAI2, 60, T2)], ai) == []                       # đúng ngưỡng 30 giây thì không
    assert config.CO_TONG_GIAY_TOI_THIEU["game3"] == 30 and config.CO_GAME3_TONG_GIAY_TOI_THIEU == 60
    assert flags.co_cua_game3([muc(BAI, 60), muc(BAI2, 60, T2)], ai, tong_giay=59) == ["lam_qua_nhanh:game3"]   # tổng cả game dưới 60 giây
    assert flags.co_cua_game3([muc(BAI, 60), muc(BAI2, 60, T2)], ai, tong_giay=60) == []
    assert flags.co_cua_game3([muc(BAI, 60), muc(BAI2, 60, T2)], ai, tong_giay=None) == []                 # không có số đo thì không xét


def test_co_copy_ai_goc():
    ai = game3_store.ai_goc_theo_id()
    cai_tien = ("Đặt thùng rác phân loại ở căng tin, nhưng thêm máy đổi vỏ chai lấy điểm rèn luyện, "
                "cho mỗi lớp thi đua giảm nhựa mỗi tuần và công bố bảng xếp hạng trên fanpage của trường.")
    khac = "Mình sẽ cho sinh viên mang bình nước cá nhân và giảm giá đồ uống cho ai tự mang cốc đến căng tin mỗi ngày."
    # (a) chép nguyên văn (kể cả khác hoa thường, dấu câu): giữ 100% từ gốc, 0% từ mới
    assert flags.do_do_copy(AI1.upper() + "!!", AI1) == (1.0, 0.0)
    assert flags.co_cua_game3([muc(AI1, 60)], ai) == ["copy_ai_goc:game3"]
    # (b) chép rồi thêm vài chữ cho đủ 15 từ: vẫn bị cờ (đây là lỗ hổng của cách đo cũ)
    chep_them = AI1 + " Mình thấy cách này hay"
    assert len(chep_them.split()) >= 15 and flags.co_cua_game3([muc(chep_them, 60)], ai) == ["copy_ai_goc:game3"]
    # (c) cải tiến thật, nhiều ý mới: giữ phần lớn từ gốc nhưng từ mới >= 40% thì KHÔNG cờ
    giu, moi = flags.do_do_copy(cai_tien, AI1)
    assert giu >= 0.4 and moi >= config.CO_COPY_TU_MOI_TOI_DA and flags.co_cua_game3([muc(cai_tien, 60)], ai) == []
    # (d) ý hoàn toàn khác: giữ ít từ gốc nên không cờ
    giu, moi = flags.do_do_copy(khac, AI1)
    assert giu < config.CO_COPY_GIU_TU_GOC and flags.co_cua_game3([muc(khac, 60)], ai) == []
    # so với đúng tình huống của nó, không so chéo; không có đề thì bỏ qua cờ copy
    assert flags.co_cua_game3([muc(AI2, 60, T1)], ai) == []
    assert flags.co_cua_game3([muc(BAI, 60), muc(AI2, 60, T2)], ai) == ["copy_ai_goc:game3"]
    assert flags.co_cua_game3([muc(AI1, 60)], None) == [] and flags.do_do_copy("", AI1) == (0.0, 0.0)
    assert (config.CO_COPY_GIU_TU_GOC, config.CO_COPY_TU_MOI_TOI_DA) == (0.8, 0.4)


def test_co_qua_api_chi_gan_co_khong_chan(client):
    c, db = client
    t = nguoi_moi(c, db)
    bat_dau(c, t)
    r = nop3(c, t, b1=AI1 + " Mình thấy cách này hay", giay=(10, 60))                                       # chép AI + một ô chỉ dùng 10 giây
    assert r.status_code == 200                                                                      # vẫn nộp được
    co = db["participants"].find_one()["flags"]
    assert "copy_ai_goc:game3" in co and "lam_qua_nhanh:game3" in co
    assert "copy_ai_goc" not in json.dumps(r.json())                                                 # người chơi không thấy cờ
    assert flags_store.tinh_lai_tat_ca(db, ap_dung=False)["doi"] == 0                                # tính lại cho cùng kết quả (idempotent)


def test_co_nhanh_do_tong_server_hoac_tung_o(client):
    """Test chạy nhanh nên tổng của server < 40 giây: có cờ dù từng ô 60 giây. Ngược lại từng ô 60 giây thì riêng ô không gây cờ."""
    c, db = client
    t = nguoi_moi(c, db)
    bat_dau(c, t)
    nop3(c, t, giay=(60, 60))
    assert "lam_qua_nhanh:game3" in db["participants"].find_one()["flags"]                           # tổng server < 40 giây
    bai = bai_game3(db)
    assert flags.co_cua_game3(bai["answer"]["tinh_huong"], game3_store.ai_goc_theo_id(), None) == []   # từng ô 60 giây: riêng ô không gây cờ


def test_co_game3_chua_nop_du_thi_chua_gan(client):
    c, db = client
    t = nguoi_moi(c, db)
    bat_dau(c, t)
    nop_items(c, t, [o3(T1, BAI)])                                                                   # thiếu ô: bị từ chối
    assert [x for x in db["participants"].find_one().get("flags", []) if x.endswith("game3")] == []


# ---------- Giao diện và quản trị ----------

def test_giao_dien_game3_menu_trai_mot_lan_nop():
    js = {f: (GOC / "web" / f).read_text(encoding="utf-8") for f in ("app.js", "game2.js", "game3.js", "nhap.js", "index.html")}
    css = (GOC / "web" / "style.css").read_text(encoding="utf-8")
    assert "/play/game3.js" in js["index.html"] and "/play/game_chung.js" in js["index.html"] and "manGame3GioiThieu();" in js["game2.js"]
    assert "game3: manGame3" in js["app.js"] and "manHoanThanh()" in js["game3.js"]                  # nộp xong sang trang tổng kết
    g = js["game3.js"]
    assert 'ghiNhap("g3"' in g and "docNhap().g3" in g and "chanOMuc(o" in g and "tenGame(nd.so, nd.ten)" in g and "khoiGioiThieu" not in g and "manGameGioiThieu(3, manGame3, manGame2)" in g   # hướng dẫn ở trang giới thiệu riêng
    assert 'datMan("game3")' in g and "thieu_tu" in g and "maxlength: nd.toi_da_ky_tu" in g
    assert "g3.nut.disabled = thieu.length > 0" in g                                                 # tắt cho tới khi đủ cả hai tình huống
    assert "toi_thieu_ky_tu" in g and "demTuG3" not in g and "dem_tu" not in g and "toi_thieu_tu" not in g   # chỉ đếm ký tự, không bộ đếm từ
    assert "con_thieu" not in g and "conThieu" not in g and "chot_y" not in g and "chot-y" not in g  # chân trang không còn chữ
    foot = g.split("khungNut(loi")[1].split(";")[0]
    assert foot.count("h(\"p\"") == 0 and "nut" in foot                                                # chân trang chỉ có nút (và vùng lỗi ẩn)
    ui = json.loads((GOC / "content/research_ui.json").read_text(encoding="utf-8"))["game3"]
    assert ui["dem_ky_tu"] == "{n}/{max} ký tự" and "dem_tu" not in ui and "con_thieu" not in ui and "chot_y" not in ui
    assert ".con-thieu" not in css and ".chot-y" not in css
    assert "thoi_gian_giay" in g and "dungDoO" in g and "document.hidden" in g                      # thời gian từng ô, trừ lúc ẩn tab
    assert g.count("/api/research/game3/submit") == 1 and "tinh_huong_id: th.id" in g               # một lần nộp, gửi cả hai ô
    assert "button.muc-menu.xong" in css and "--bien: #0A6C8F" in css and "max-width: 699px" in css   # xanh nước biển; dưới 700px thành tab ngang
    assert '"g3"' in js["nhap.js"]


def test_quan_tri_doc_duoc_game3():
    ui = json.loads((GOC / "content/admin_ui.json").read_text(encoding="utf-8"))
    assert ui["du_lieu"]["game3"]["so_tu"] and ui["tong_quan"]["huong2"]["buoc"]["game3"] == "Game 3"
    js = (GOC / "web/admin/js/page-data.js").read_text(encoding="utf-8")
    assert "hienGame3" in js and "m.noi_dung" in js and "m.so_lan_dan" in js and "m.so_tu" in js


@pytest.mark.parametrize("co", ["copy_ai_goc:game3", "lam_qua_nhanh:game3"])
def test_co_game3_co_trong_bo_loc_quan_tri(co):
    from sparkmind import admin_registry as reg
    assert co in reg.LUA_CHON_CO and reg.kiem_tra_registry() == []
