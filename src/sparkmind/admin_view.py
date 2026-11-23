"""Biến bản ghi MongoDB thành dữ liệu an toàn để hiện ra giao diện/CSV: đổi kiểu, che thông tin nhận dạng, bỏ trường cấm."""
import csv
import io
import math
import re
from datetime import date, datetime

from bson import ObjectId

from .admin_registry import TRUONG_CAM

KIEU_KHONG_XUAT = ("email",)    # không bao giờ xuất CSV (docs/decisions.md: email và IP không vào CSV)
MAU_IP = re.compile(r"^(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}$")


def che_email(v) -> str:
    """tr***@gmail.com: giữ 2 ký tự đầu của phần tên và toàn bộ tên miền."""
    ten, _, mien = str(v).partition("@")
    return f"{ten[:2]}***@{mien}" if mien else "***"


def che_ip(v) -> str:
    """IPv4: giữ 3 phần đầu, che phần cuối (1.2.3.*). Chuỗi khác: che hết trừ 3 ký tự đầu."""
    m = MAU_IP.match(str(v))
    return f"{m.group(1)}.*" if m else str(v)[:3] + "***"


def che_bam(v) -> str:
    """Chuỗi băm (ip_hash): chỉ hiện 8 ký tự đầu."""
    return str(v)[:8] + "…" if v else v


def che_bi_mat(v, vai_tro: str):
    """Mã tham gia: admin thấy đủ; vai trò khác chỉ thấy 2 ký tự đầu."""
    return v if vai_tro == "admin" or not v else str(v)[:2] + "*" * max(0, len(str(v)) - 2)


def json_an_toan(v):
    """ObjectId -> chuỗi, datetime -> ISO, NaN -> None; đệ quy qua dict và list."""
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, dict):
        return {str(k): json_an_toan(x) for k, x in v.items() if k not in TRUONG_CAM}
    if isinstance(v, (list, tuple, set)):
        return [json_an_toan(x) for x in v]
    return v


def che_theo_kieu(kieu: str, v, vai_tro: str):
    """Che một giá trị theo kiểu cột trong registry."""
    if v is None:
        return None
    if kieu == "email":
        return che_email(v)
    if kieu == "hash":
        return che_bam(v)
    return che_bi_mat(v, vai_tro) if kieu == "bi_mat" else v


def _kieu_theo_ten(khoa: str):
    """Quy tắc chung theo TÊN trường (áp cả cho JSON thô): email, ip, ip_hash."""
    k = khoa.lower()
    if "email" in k:
        return "email"
    if k in ("ip", "client_ip") or k.endswith("_ip"):
        return "ip"
    return "hash" if k == "ip_hash" else None


def _che_gia_tri(khoa: str, v, kieu_cot: dict, vai_tro: str):
    kieu = kieu_cot.get(khoa) or _kieu_theo_ten(khoa)
    if kieu == "ip":
        return che_ip(v) if v is not None else None
    return che_theo_kieu(kieu, v, vai_tro) if kieu in ("email", "hash", "bi_mat") else v


def lam_ve(doc: dict, cfg: dict, vai_tro: str) -> dict:
    """Một dòng của danh sách: chỉ các cột trong registry, đã che và đổi kiểu. Có thêm "_id" (chuỗi)."""
    kieu_cot = {k: kieu for k, _, kieu in cfg["cot"]}
    dong = {"_id": str(doc["_id"])}
    for khoa, _, _ in cfg["cot"]:
        dong[khoa] = json_an_toan(_che_gia_tri(khoa, doc.get(khoa), kieu_cot, vai_tro))
    return dong


def json_tho(doc: dict, cfg: dict, vai_tro: str) -> dict:
    """JSON thô đã che (trường cấm bị bỏ, email/IP/băm/mã bị che) cho nút "xem JSON thô"."""
    kieu_cot = {k: kieu for k, _, kieu in cfg["cot"]}
    return json_an_toan({k: _che_gia_tri(k, v, kieu_cot, vai_tro) for k, v in doc.items() if k not in TRUONG_CAM})


def cac_truong(doc: dict, cfg: dict, vai_tro: str) -> list:
    """Danh sách trường dạng đọc được: [{khoa, nhan, kieu, gia_tri}] (cột của registry trước, rồi các trường còn lại)."""
    tho = json_tho(doc, cfg, vai_tro)
    nhan = {**cfg["chi_tiet"], **{k: n for k, n, _ in cfg["cot"]}}
    kieu = {k: t for k, _, t in cfg["cot"]}
    thu_tu = ["_id"] + [k for k, _, _ in cfg["cot"]] + sorted(k for k in tho if k != "_id" and k not in nhan)
    thu_tu += [k for k in cfg["chi_tiet"] if k not in thu_tu]
    return [{"khoa": k, "nhan": "ID" if k == "_id" else nhan.get(k, k), "kieu": kieu.get(k, "json" if isinstance(tho.get(k), (dict, list)) else "text"),
             "gia_tri": tho.get(k)} for k in dict.fromkeys(thu_tu) if k in tho]


def _chong_cong_thuc(v):
    """Excel hiểu ô bắt đầu bằng = + - @ là công thức: thêm dấu ' phía trước (giống scripts/make_codes.py)."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
        return "'" + v
    return "" if v is None else v


def tao_csv(dong: list, cfg: dict) -> str:
    """CSV (UTF-8) từ các dòng đã qua lam_ve. Bỏ cột email; thêm cột _id đầu tiên."""
    cot = [(k, n) for k, n, kieu in cfg["cot"] if kieu not in KIEU_KHONG_XUAT]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ID"] + [n for _, n in cot])
    for d in dong:
        w.writerow([_chong_cong_thuc(d["_id"])] + [_chong_cong_thuc(d.get(k)) for k, _ in cot])
    return out.getvalue()
