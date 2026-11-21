"""Tạo mã tham gia cho chế độ nghiên cứu, ghi vào MongoDB và vào file CSV.

Ví dụ:  python scripts/make_codes.py --n 5 --source volunteer --label "Nhom A"
File CSV (outputs/codes_<ngày>.csv) có cột: code, source, created_at, label.
Mã là bí mật nên file CSV không lên GitHub. --label chỉ ghi vào CSV, không lưu email.
Chỉ in các mã, KHÔNG in chuỗi kết nối MongoDB.
"""
import argparse
import csv
from datetime import date
from pathlib import Path

import _boot  # noqa: F401  (cho phép import sparkmind)
from sparkmind.db import lay_db
from sparkmind.research_store import COL_MA, NGUON_HOP_LE, tao_chi_muc, tao_ma_moi

N_TOI_DA = 500
CAC_COT = ["code", "source", "created_at", "label"]
THU_MUC_RA = Path(__file__).resolve().parents[1] / "outputs"


def so_luong(gia_tri: str) -> int:
    """Kiểm tra --n nằm trong 1..500."""
    n = int(gia_tri)
    if not 1 <= n <= N_TOI_DA:
        raise argparse.ArgumentTypeError(f"--n phải từ 1 đến {N_TOI_DA}")
    return n


def doc_tham_so(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tạo mã tham gia ngẫu nhiên 8 ký tự")
    p.add_argument("--n", type=so_luong, required=True, help=f"số mã cần tạo (tối đa {N_TOI_DA})")
    p.add_argument("--source", choices=NGUON_HOP_LE, required=True, help="nguồn người tham gia")
    p.add_argument("--label", default="", help="nhãn ghi vào CSV (vd tên người nhận mã), không ghi email")
    p.add_argument("--out", default=None, help="file CSV (mặc định outputs/codes_<ngày>.csv)")
    return p.parse_args(argv)


def lam_sach_nhan(nhan: str) -> str:
    """Chặn Excel hiểu nhãn là công thức (bắt đầu bằng = + - @)."""
    nhan = (nhan or "").strip()
    return "'" + nhan if nhan[:1] in ("=", "+", "-", "@") else nhan


def ghi_csv(db, cac_ma: list, nguon: str, nhan: str, duong_dan: Path) -> Path:
    """Ghi các mã vừa tạo vào CSV (nối thêm nếu file đã có trong ngày)."""
    created = {d["code"]: d["created_at"] for d in db[COL_MA].find({"code": {"$in": cac_ma}})}
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    moi = not duong_dan.exists()
    with open(duong_dan, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if moi:
            w.writerow(CAC_COT)
        for ma in cac_ma:
            w.writerow([ma, nguon, created[ma].isoformat(timespec="seconds"), lam_sach_nhan(nhan)])
    return duong_dan


def main() -> None:
    tham_so = doc_tham_so()
    db = lay_db()
    tao_chi_muc(db)  # bảo đảm mã không trùng (code unique)
    cac_ma = tao_ma_moi(db, tham_so.n, tham_so.source)
    out = Path(tham_so.out) if tham_so.out else THU_MUC_RA / f"codes_{date.today().isoformat()}.csv"
    ghi_csv(db, cac_ma, tham_so.source, tham_so.label, out)
    print("\n".join(cac_ma))
    print(f"Đã ghi {len(cac_ma)} mã vào {out}")


if __name__ == "__main__":
    main()
