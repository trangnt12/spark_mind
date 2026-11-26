"""Tạo, sửa, xóa từng bản ghi cho trang dữ liệu. Mọi thao tác đều ghi audit_log (ai, bảng, ID, trường cũ/mới).

Không có hàm xóa hàng loạt hay drop collection ở đây. Xóa luôn là MỘT bản ghi và phải gõ lại đúng ID để xác nhận.
(Xóa hàng loạt duy nhất là "xóa dữ liệu thử" trong du_lieu_thu.py, chỉ đụng nhãn thu/pilot.)
"""
import re
from datetime import datetime

from .admin_query import id_ung_vien
from .admin_view import json_an_toan, lam_ve
from .audit import write_audit
from .research_store import LoiNghiepVu, chuan_hoa_ma, kiem_tra_ten_lo
from .thoi_gian import utc_now


def tim_mot(db, ten: str, id_text: str) -> dict | None:
    return db[ten].find_one({"_id": {"$in": id_ung_vien(id_text)}})


def can_co(db, ten: str, id_text: str) -> dict:
    doc = tim_mot(db, ten, id_text)
    if not doc:
        raise LoiNghiepVu(404, "ban_ghi_khong_ton_tai")
    return doc


def _kiem_tra_mot(khoa: str, gia_tri, quy: dict):
    """Kiểm tra và chuẩn hóa giá trị của một trường theo khai báo `ghi` trong registry."""
    if quy["kieu"] == "bool":
        if not isinstance(gia_tri, bool):
            raise LoiNghiepVu(422, "truong_khong_hop_le")
        return gia_tri
    if not isinstance(gia_tri, str):
        raise LoiNghiepVu(422, "truong_khong_hop_le")
    gia_tri = " ".join(gia_tri.split())
    if quy["kieu"] == "choice" and gia_tri not in quy["lua_chon"]:
        raise LoiNghiepVu(422, "truong_khong_hop_le")
    if quy.get("bat_buoc") and not gia_tri:
        raise LoiNghiepVu(422, "thieu_truong")
    if len(gia_tri) > 200:
        raise LoiNghiepVu(422, "truong_khong_hop_le")
    return gia_tri


def kiem_tra_truong(cfg: dict, body: dict, tao: bool) -> dict:
    """Chỉ nhận trường khai báo (và với PATCH chỉ trường `sua`); thiếu trường bắt buộc khi tạo thì lỗi."""
    quy = cfg["ghi"]
    for k in body:
        if k not in quy or (not tao and not quy[k]["sua"]):
            raise LoiNghiepVu(422, "truong_khong_hop_le")
    if tao and any(q.get("bat_buoc") and k not in body for k, q in quy.items()):
        raise LoiNghiepVu(422, "thieu_truong")
    return {k: _kiem_tra_mot(k, v, quy[k]) for k, v in body.items()}


# ---------- Quy tắc riêng từng bảng (chỉ khi bảng cần) ----------

def _chuan_lo(gia_tri: dict) -> dict:
    """Tên lô (batch) rỗng thì lưu None; sai dạng thì báo 422."""
    if "batch" in gia_tri:
        try:
            gia_tri = {**gia_tri, "batch": kiem_tra_ten_lo(gia_tri["batch"])}
        except ValueError:
            raise LoiNghiepVu(422, "truong_khong_hop_le")
    return gia_tri


def _truoc_tao_access_codes(db, gia_tri: dict) -> dict:
    ma = chuan_hoa_ma(gia_tri["code"])
    if not re.fullmatch(r"[A-Z0-9]{6,32}", ma):
        raise LoiNghiepVu(422, "truong_khong_hop_le")
    if db["access_codes"].find_one({"code": ma}):
        raise LoiNghiepVu(409, "ma_trung")
    return {**gia_tri, "code": ma, "is_used": False, "used_at": None, "created_at": datetime.now()}


def _truoc_sua_access_codes(db, doc: dict, gia_tri: dict) -> None:
    if doc.get("is_used"):   # mã đã dùng: người tham gia đã mang nhãn và nguồn này, đổi sẽ làm lệch dữ liệu
        raise LoiNghiepVu(409, "ma_da_dung")


def _truoc_xoa_access_codes(db, doc: dict) -> None:
    if doc.get("is_used"):
        raise LoiNghiepVu(409, "ma_da_dung")


QUY_TAC = {
    "access_codes": {"tao": _truoc_tao_access_codes, "dan_xuat": _chuan_lo, "sua": _truoc_sua_access_codes, "xoa": _truoc_xoa_access_codes},
}


def _ghi_nhat_ky(db, user: dict, hanh_dong: str, ten: str, doc_id, chi_tiet: dict) -> None:
    write_audit(db, user, hanh_dong, ten, doc_id, chi_tiet)


def tao(db, ten: str, cfg: dict, user: dict, body: dict) -> dict:
    """POST: tạo một bản ghi mới."""
    gia_tri = kiem_tra_truong(cfg, body, tao=True)
    quy = QUY_TAC.get(ten, {})
    if "tao" in quy:
        gia_tri = quy["tao"](db, gia_tri)
    if "dan_xuat" in quy:
        gia_tri = quy["dan_xuat"](gia_tri)
    doc_id = db[ten].insert_one(dict(gia_tri)).inserted_id
    cac = {k: {"cu": None, "moi": json_an_toan(v)} for k, v in gia_tri.items() if k in cfg["ghi"] and k != "code"}   # mã không ghi vào nhật ký
    _ghi_nhat_ky(db, user, "data_create", ten, doc_id, {"truong": cac})
    return {"_id": str(doc_id)}


def sua(db, ten: str, cfg: dict, user: dict, id_text: str, body: dict) -> dict:
    """PATCH: sửa các trường được phép. Ghi giá trị cũ và mới của từng trường ĐÃ ĐỔI vào nhật ký."""
    doc = can_co(db, ten, id_text)
    gia_tri = kiem_tra_truong(cfg, body, tao=False)
    quy = QUY_TAC.get(ten, {})
    if "sua" in quy:
        quy["sua"](db, doc, gia_tri)
    if "dan_xuat" in quy:
        gia_tri = quy["dan_xuat"](gia_tri)
    doi = {k: v for k, v in gia_tri.items() if doc.get(k) != v}
    if not doi:
        raise LoiNghiepVu(409, "khong_co_thay_doi")
    db[ten].update_one({"_id": doc["_id"]}, {"$set": {**doi, "updated_at": utc_now()}})
    cac = {k: {"cu": json_an_toan(doc.get(k)), "moi": json_an_toan(v)} for k, v in doi.items() if k in cfg["ghi"] and k != "code"}
    _ghi_nhat_ky(db, user, "data_update", ten, doc["_id"], {"truong": cac})
    return {"_id": str(doc["_id"])}


def _loc_bang_con(db, doc: dict, bc: dict) -> dict:
    """Bộ lọc tìm các bản ghi con của một bản ghi (có thể đi qua một bảng trung gian, vd scores -> game_responses)."""
    if "qua" not in bc:
        return {bc["truong"]: doc["_id"]}
    lay = bc.get("qua_lay", "_id")   # trường của bảng trung gian dùng để nối (mặc định _id; ratings nối theo item_code)
    ids = [d[lay] for d in db[bc["qua"]].find({bc["qua_truong"]: doc["_id"]}, {lay: 1})]
    return {bc["truong"]: {"$in": ids}}


def dem_bang_con(db, cfg: dict, doc: dict) -> dict:
    """{bảng con: số bản ghi sẽ bị xóa theo}. Chỉ ĐỌC (màn xác nhận xóa hiển thị số này)."""
    return {bc["bang"]: db[bc["bang"]].count_documents(_loc_bang_con(db, doc, bc)) for bc in cfg.get("bang_con", [])}


def lien_quan(db, ten: str, cfg: dict, id_text: str) -> dict:
    """GET .../lien-quan: số bản ghi con sẽ bị xóa cùng bản ghi này."""
    return {"bang_con": dem_bang_con(db, cfg, can_co(db, ten, id_text))}


def xoa(db, ten: str, cfg: dict, user: dict, id_text: str, xac_nhan: str) -> dict:
    """DELETE một bản ghi: phải gõ lại đúng ID. Bản ghi có bang_con thì xóa luôn dữ liệu con của nó (số lượng ghi vào nhật ký).
    Nhật ký lưu tóm tắt đã che (không email, không mã đầy đủ)."""
    doc = can_co(db, ten, id_text)
    if (xac_nhan or "").strip() != str(doc["_id"]):
        raise LoiNghiepVu(422, "xac_nhan_sai")
    quy = QUY_TAC.get(ten, {})
    if "xoa" in quy:
        quy["xoa"](db, doc)
    # Tính MỌI bộ lọc con trước khi xóa bất cứ gì: scores tìm qua game_responses, nên game_responses chưa được xóa lúc này
    bo_loc = {bc["bang"]: _loc_bang_con(db, doc, bc) for bc in cfg.get("bang_con", [])}
    da_xoa_con = {bang: db[bang].delete_many(loc).deleted_count for bang, loc in bo_loc.items()}
    db[ten].delete_one({"_id": doc["_id"]})
    chi_tiet = {"tom_tat": lam_ve(doc, cfg, "viewer")}
    if da_xoa_con:
        chi_tiet["da_xoa_bang_con"] = da_xoa_con
    _ghi_nhat_ky(db, user, "data_delete", ten, doc["_id"], chi_tiet)
    return {"_id": str(doc["_id"]), "da_xoa_bang_con": da_xoa_con}
