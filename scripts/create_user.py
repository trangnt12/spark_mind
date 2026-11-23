"""Tạo tài khoản quản trị đầu tiên (hoặc thêm tài khoản) trực tiếp vào MongoDB.

Ví dụ:  python scripts/create_user.py --username trang --role admin
Mật khẩu được hỏi bằng getpass (không hiện lên màn hình, KHÔNG nhận qua tham số dòng lệnh để không lọt vào lịch sử lệnh).
Không in chuỗi kết nối MongoDB. Mật khẩu tối thiểu 12 ký tự. Tài khoản mới phải đổi mật khẩu ở lần đăng nhập đầu
(thêm --keep-password nếu đây là mật khẩu chính thức bạn tự đặt).
"""
import argparse
import getpass
import sys

import _boot  # noqa: F401  (cho phép import sparkmind)
from sparkmind import passwords, session_store, user_store
from sparkmind.audit import tao_chi_muc_audit, write_audit
from sparkmind.db import lay_db
from sparkmind.research_store import LoiNghiepVu

THONG_BAO_LOI = {"bad_username": "Tên đăng nhập phải 3–32 ký tự: chữ thường, số, dấu . _ -",
                 "bad_role": "Vai trò không hợp lệ.", "username_taken": "Tên đăng nhập đã tồn tại.",
                 "weak_password": f"Mật khẩu phải có ít nhất {passwords.DO_DAI_TOI_THIEU} ký tự và khác tên đăng nhập."}


def doc_tham_so(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tạo tài khoản quản trị SparkMind")
    p.add_argument("--username", required=True, help="tên đăng nhập (chữ thường, duy nhất)")
    p.add_argument("--role", choices=user_store.VAI_TRO, required=True, help="admin | viewer | rater")
    p.add_argument("--display-name", default="", help="tên hiển thị (mặc định = tên đăng nhập)")
    p.add_argument("--keep-password", action="store_true", help="không bắt đổi mật khẩu ở lần đăng nhập đầu")
    return p.parse_args(argv)


def hoi_mat_khau() -> str:
    """Hỏi mật khẩu hai lần; hai lần phải giống nhau."""
    mk = getpass.getpass("Mật khẩu (tối thiểu 12 ký tự): ")
    if mk != getpass.getpass("Nhập lại mật khẩu: "):
        sys.exit("Hai lần nhập không giống nhau.")
    return mk


def tao(db, tham_so, mat_khau: str) -> dict:
    """Tạo user rồi ghi nhật ký; lỗi nghiệp vụ thì dừng với thông báo tiếng Việt."""
    try:
        user = user_store.tao_user(db, tham_so.username, tham_so.display_name, tham_so.role, mat_khau,
                                   "script", bat_buoc_doi_mk=not tham_so.keep_password)
    except LoiNghiepVu as loi:
        sys.exit(THONG_BAO_LOI.get(loi.noi_dung, loi.noi_dung))
    write_audit(db, None, "user_create_script", user_store.COL_USERS, user["_id"],
                {"username": user["username"], "role": user["role"]})
    return user


def main() -> None:
    tham_so = doc_tham_so()
    mat_khau = hoi_mat_khau()
    db = lay_db()
    user_store.tao_chi_muc_user(db)
    session_store.tao_chi_muc_phien(db)
    tao_chi_muc_audit(db)
    user = tao(db, tham_so, mat_khau)
    print(f"Đã tạo tài khoản {user['username']} (vai trò {user['role']}).")


if __name__ == "__main__":
    main()
