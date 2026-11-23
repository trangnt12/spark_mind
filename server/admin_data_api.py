"""Route dữ liệu quản trị TẠO TỰ ĐỘNG từ registry (src/sparkmind/admin_registry.py).

Với mỗi bảng trong registry:
  GET    /api/admin/data/{bảng}              danh sách (phân trang, tìm kiếm, lọc, sắp xếp)
  GET    /api/admin/data/{bảng}/export.csv   xuất CSV (tối đa 5000 dòng)
  GET    /api/admin/data/{bảng}/{id}         chi tiết một bản ghi
  POST   /api/admin/data/{bảng}              tạo     (CHỈ bảng crud)
  PATCH  /api/admin/data/{bảng}/{id}         sửa     (CHỈ bảng crud)
  GET    /api/admin/data/{bảng}/{id}/lien-quan   số bản ghi con sẽ bị xóa theo (bảng có bang_con)
  DELETE /api/admin/data/{bảng}/{id}?confirm=<id>   xóa từng bản ghi (nếu registry cho phép; có bang_con thì xóa cả dữ liệu con)
Route nào registry không cho phép thì KHÔNG được tạo (bảng readonly không có POST/PATCH). Mỗi route có require_role riêng.
"""
from datetime import date

from fastapi import APIRouter, Body, Depends, Request, Response

from server.auth import chay_ma, loi, require_role
from sparkmind import admin_crud, admin_query, admin_registry as reg, admin_view
from sparkmind.audit import write_audit

router = APIRouter(prefix="/api/admin/data")


def _an_thu(request: Request) -> bool:
    """ex_test=true (mặc định) = ẩn dữ liệu thử."""
    return request.query_params.get("ex_test", "true").lower() != "false"


def _chay_truy_van(ham, *args):
    try:
        return ham(*args)
    except admin_query.LoiTruyVan as e:
        raise loi(422, e.args[0])


def _meta_bang(ten: str, cfg: dict, vai_tro: str) -> dict:
    """Mô tả bảng cho giao diện (không chứa hàm). Quyền đã quy về True/False theo vai trò đang đăng nhập."""
    q = cfg["quyen"]
    return {"khoa": ten, "ten": cfg["ten"], "nhom": cfg["nhom"], "che_do": cfg["che_do"], "co_nhan": cfg["co_nhan"],
            "cot": [{"khoa": k, "nhan": n, "kieu": t} for k, n, t in cfg["cot"]],
            "loc": [{"khoa": k, "nhan": n, "kieu": t, "lua_chon": lc} for k, n, t, lc in cfg["loc"]],
            "sap_xep": cfg["sap_xep"], "mac_dinh": {"truong": cfg["mac_dinh"][0], "chieu": cfg["mac_dinh"][1]},
            "tim_kiem": bool(cfg["tim"]), "ghi_chu": cfg.get("ghi_chu"), "co_bang_con": bool(cfg.get("bang_con")), "ghi": cfg.get("ghi", {}),
            "quyen": {k: vai_tro in q[k] for k in ("doc", "xuat", "ghi", "xoa")},
            "toi_da_xuat": reg.SO_DONG_XUAT_TOI_DA}


@router.get("")
def danh_sach_bang(ctx=Depends(require_role("admin", "viewer"))):
    """Các bảng vai trò này được xem (để dựng menu và trang)."""
    vt = ctx["user"]["role"]
    return {"bang": [_meta_bang(t, b, vt) for t, b in reg.bang_cho_vai_tro(vt)], "nhom": list(reg.NHOM)}


# ---------- Mỗi hàm dưới đây là một "nhà máy": nhận tên bảng, trả về hàm xử lý route ----------

def _ham_ds(ten, cfg, dep):
    def ds(request: Request, ctx=Depends(dep)):
        return _chay_truy_van(admin_query.danh_sach, ctx["db"], ten, cfg, dict(request.query_params), ctx["user"]["role"], _an_thu(request))
    return ds


def _ham_csv(ten, cfg, dep):
    def xuat(request: Request, ctx=Depends(dep)):
        db, user = ctx["db"], ctx["user"]
        dong, bi_cat = _chay_truy_van(admin_query.dong_de_xuat, db, ten, cfg, dict(request.query_params), user["role"], _an_thu(request))
        write_audit(db, user, "data_export", ten, None, {"so_dong": len(dong), "bi_cat": bi_cat})
        return Response(content="﻿" + admin_view.tao_csv(dong, cfg), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{ten}_{date.today().isoformat()}.csv"',
                                 "X-Truncated": "true" if bi_cat else "false"})
    return xuat


def _ham_chi_tiet(ten, cfg, dep):
    def chi_tiet(id_: str, ctx=Depends(dep)):
        doc = chay_ma(admin_crud.can_co, ctx["db"], ten, id_)
        vt = ctx["user"]["role"]
        return {"id": str(doc["_id"]), "ten": cfg["ten"], "truong": admin_view.cac_truong(doc, cfg, vt), "tho": admin_view.json_tho(doc, cfg, vt)}
    return chi_tiet


def _ham_tao(ten, cfg, dep):
    def tao(body: dict = Body(...), ctx=Depends(dep)):
        return chay_ma(admin_crud.tao, ctx["db"], ten, cfg, ctx["user"], body)
    return tao


def _ham_sua(ten, cfg, dep):
    def sua(id_: str, body: dict = Body(...), ctx=Depends(dep)):
        return chay_ma(admin_crud.sua, ctx["db"], ten, cfg, ctx["user"], id_, body)
    return sua


def _ham_lien_quan(ten, cfg, dep):
    def lien_quan(id_: str, ctx=Depends(dep)):
        return chay_ma(admin_crud.lien_quan, ctx["db"], ten, cfg, id_)
    return lien_quan


def _ham_xoa(ten, cfg, dep):
    def xoa(id_: str, request: Request, ctx=Depends(dep)):
        return chay_ma(admin_crud.xoa, ctx["db"], ten, cfg, ctx["user"], id_, request.query_params.get("confirm", ""))
    return xoa


def dang_ky_bang(ten: str, cfg: dict) -> None:
    """Tạo route cho một bảng theo registry. Chỉ tạo route mà registry cho phép."""
    q, goc = cfg["quyen"], f"/{ten}"
    router.add_api_route(goc, _ham_ds(ten, cfg, require_role(*q["doc"])), methods=["GET"], name=f"{ten}_ds")
    if q["xuat"]:
        router.add_api_route(f"{goc}/export.csv", _ham_csv(ten, cfg, require_role(*q["xuat"])), methods=["GET"], name=f"{ten}_csv")
    router.add_api_route(f"{goc}/{{id_}}", _ham_chi_tiet(ten, cfg, require_role(*q["doc"])), methods=["GET"], name=f"{ten}_chi_tiet")
    if cfg["che_do"] == "crud" and q["ghi"]:
        router.add_api_route(goc, _ham_tao(ten, cfg, require_role(*q["ghi"])), methods=["POST"], status_code=201, name=f"{ten}_tao")
        router.add_api_route(f"{goc}/{{id_}}", _ham_sua(ten, cfg, require_role(*q["ghi"])), methods=["PATCH"], name=f"{ten}_sua")
    if q["xoa"] and cfg.get("bang_con"):
        router.add_api_route(f"{goc}/{{id_}}/lien-quan", _ham_lien_quan(ten, cfg, require_role(*q["xoa"])), methods=["GET"], name=f"{ten}_lien_quan")
    if q["xoa"]:
        router.add_api_route(f"{goc}/{{id_}}", _ham_xoa(ten, cfg, require_role(*q["xoa"])), methods=["DELETE"], name=f"{ten}_xoa")


for _ten, _cfg in reg.BANG.items():
    dang_ky_bang(_ten, _cfg)
