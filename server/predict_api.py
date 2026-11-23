"""API dự đoán mức tự đánh giá sáng tạo: chế độ demo (không lưu gì) và kết quả của người tham gia nghiên cứu.

- POST /api/predict/demo: nhận 7 câu B4, trả kết quả. KHÔNG ghi MongoDB, KHÔNG ghi nội dung request vào log.
- GET /api/research/result: chỉ trả khi người tham gia đã hoàn thành (có completed_at). Không lưu thêm gì.
Chữ thông báo lấy từ content/results_ui.json.
"""
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request

from server.content_api import doc_noi_dung
from server.research import chay, lay_db_nghien_cuu, lay_ip
from sparkmind import predict, research_store as kho
from sparkmind.security import GioiHanTocDo

router = APIRouter()
gioi_han_demo = GioiHanTocDo(toi_da=30, giay=60)  # tối đa 30 lần mỗi phút cho mỗi IP (tính mọi lần gọi)


def chu(nhom: str, khoa: str, **thay) -> str:
    """Lấy một câu thông báo trong content/results_ui.json rồi thay {cau}, {giay}."""
    return doc_noi_dung("results_ui.json")[nhom][khoa].format(**thay)


def _loi_422(khoa: str, **thay) -> HTTPException:
    return HTTPException(status_code=422, detail=chu("loi_demo", khoa, **thay))


def kiem_tra_demo(body) -> dict:
    """Kiểm tra body: đủ 7 câu B4_1..B4_7, mỗi câu là số nguyên 1–5 (số thực, chữ, true/false đều bị loại)."""
    ans = body.get("answers") if isinstance(body, dict) else None
    if not isinstance(ans, dict):
        raise _loi_422("body_sai")
    la = [k for k in ans if k not in predict.CAU_B4]
    if la:
        raise _loi_422("cau_la", cau=", ".join(map(str, la)))
    thieu = [k for k in predict.CAU_B4 if k not in ans]
    if thieu:
        raise _loi_422("thieu_cau", cau=", ".join(thieu))
    for k in predict.CAU_B4:
        v = ans[k]
        if isinstance(v, bool) or not isinstance(v, int):
            raise _loi_422("sai_kieu", cau=k)
        if not 1 <= v <= 5:
            raise _loi_422("ngoai_khoang", cau=k)
    return ans


@router.post("/api/predict/demo")
def du_doan_demo(request: Request, body=Body(default=None)):
    ip = lay_ip(request)
    if not gioi_han_demo.cho_phep(ip):
        cho = gioi_han_demo.giay_phai_cho(ip)
        raise HTTPException(status_code=429, headers={"Retry-After": str(cho)},
                            detail=chu("loi_demo", "qua_nhieu_lan", giay=cho))
    return {**predict.du_doan(kiem_tra_demo(body)), "che_do": "demo"}


def _b4_da_luu(db, nguoi: dict) -> dict:
    """Lấy 7 câu B4 đã lưu (đúng mã đáp án gốc, không đảo chiều). Thiếu câu nào thì báo 422."""
    hv = db[kho.COL_HANH_VI].find_one({"participant_id": nguoi["_id"]}) or {}
    ans = {f"B4_{i}": hv.get(f"b4_{i}") for i in range(1, 8)}
    if any(not isinstance(v, int) or isinstance(v, bool) for v in ans.values()):
        raise HTTPException(status_code=422, detail=chu("loi_research", "thieu_b4"))
    return ans


@router.get("/api/research/result")
def ket_qua_nghien_cuu(x_session_token: str = Header(default=""), db=Depends(lay_db_nghien_cuu)):
    """Token CHỈ nhận qua header X-Session-Token (query sẽ lọt vào log truy cập của server nên không nhận)."""
    nguoi = chay(kho.tim_nguoi, db, x_session_token)
    if not nguoi.get("completed_at"):
        raise HTTPException(status_code=409, detail=chu("loi_research", "chua_xong"))
    return {**predict.du_doan(_b4_da_luu(db, nguoi)), "che_do": "research"}
