"""Băm và kiểm tra mật khẩu bằng hashlib.scrypt (thư viện chuẩn của Python, không cần cài thêm).

Chuỗi lưu: scrypt$n$r$p$muối_hex$băm_hex  (có tham số, nên sau này đổi tham số vẫn kiểm tra được hash cũ).
"""
import hashlib
import hmac
import secrets

N, R, P, DKLEN = 2 ** 14, 8, 1, 32   # tham số scrypt (mức tối thiểu OWASP khuyến nghị: N=2^14, r=8, p=1)
DO_DAI_TOI_THIEU = 12
DO_DAI_TOI_DA = 128                   # chặn mật khẩu quá dài làm nặng server
_BANG_MAT_KHAU_TAM = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


def kiem_tra_do_manh(mat_khau: str, username: str = "") -> str | None:
    """Trả mã lỗi ("too_short", "too_long", "same_as_username") hoặc None nếu mật khẩu đạt."""
    if len(mat_khau) < DO_DAI_TOI_THIEU:
        return "too_short"
    if len(mat_khau) > DO_DAI_TOI_DA:
        return "too_long"
    if username and mat_khau.lower() == username.lower():
        return "same_as_username"
    return None


def _scrypt(mat_khau: str, muoi: bytes, n: int, r: int, p: int) -> bytes:
    bo_nho = 128 * n * r * 2 + 1024 * 1024   # OpenSSL cần ~128*n*r byte; cho dư gấp đôi
    return hashlib.scrypt(mat_khau.encode("utf-8"), salt=muoi, n=n, r=r, p=p, dklen=DKLEN, maxmem=bo_nho)


def bam(mat_khau: str) -> str:
    """Băm mật khẩu với muối ngẫu nhiên 16 byte."""
    muoi = secrets.token_bytes(16)
    return f"scrypt${N}${R}${P}${muoi.hex()}${_scrypt(mat_khau, muoi, N, R, P).hex()}"


_HASH_GIA = []


def _hash_gia() -> str:
    """Hash giả để user không tồn tại cũng tốn đúng thời gian như user có thật (chống dò tên tài khoản)."""
    if not _HASH_GIA:
        _HASH_GIA.append(bam(secrets.token_urlsafe(16)))
    return _HASH_GIA[0]


def xac_minh(mat_khau: str, chuoi_hash: str | None) -> bool:
    """True nếu mật khẩu đúng. chuoi_hash=None (không có user) vẫn chạy scrypt rồi trả False. So sánh hằng thời gian."""
    that = chuoi_hash is not None
    try:
        _, n, r, p, muoi, bam_goc = (chuoi_hash if that else _hash_gia()).split("$")
        tinh = _scrypt(mat_khau[:DO_DAI_TOI_DA + 1], bytes.fromhex(muoi), int(n), int(r), int(p))
        trung = hmac.compare_digest(tinh, bytes.fromhex(bam_goc))
    except (ValueError, TypeError):
        return False
    return trung and that and len(mat_khau) <= DO_DAI_TOI_DA


def tao_mat_khau_tam(do_dai: int = 16) -> str:
    """Mật khẩu tạm ngẫu nhiên (bỏ ký tự dễ nhầm), luôn đủ dài hơn mức tối thiểu."""
    return "".join(secrets.choice(_BANG_MAT_KHAU_TAM) for _ in range(max(do_dai, DO_DAI_TOI_THIEU)))
