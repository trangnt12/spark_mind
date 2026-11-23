"""Đo bộ nhớ (RSS) của tiến trình hiện tại, chỉ dùng thư viện chuẩn (không thêm psutil)."""
import ctypes
import sys
from ctypes import wintypes


def _rss_linux() -> float:
    """Linux (Render): đọc dòng VmRSS (đơn vị kB) trong /proc/self/status."""
    with open("/proc/self/status", encoding="ascii") as f:
        for dong in f:
            if dong.startswith("VmRSS:"):
                return int(dong.split()[1]) / 1024
    raise OSError("Không thấy VmRSS")


class _ThongTinBoNho(ctypes.Structure):
    """Cấu trúc PROCESS_MEMORY_COUNTERS của Windows."""
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def _rss_windows() -> float:
    """Windows (máy dev): gọi GetProcessMemoryInfo, lấy WorkingSetSize."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThongTinBoNho), wintypes.DWORD]
    tt = _ThongTinBoNho()
    tt.cb = ctypes.sizeof(tt)
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(tt), tt.cb):
        raise OSError("GetProcessMemoryInfo lỗi")
    return tt.WorkingSetSize / (1024 * 1024)


def rss_mb() -> float:
    """Bộ nhớ đang dùng của tiến trình, đơn vị MB."""
    return round(_rss_windows() if sys.platform == "win32" else _rss_linux(), 1)
