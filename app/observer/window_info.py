from __future__ import annotations

import ctypes
import logging
import time
from dataclasses import dataclass
from typing import Iterable
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

logger = logging.getLogger(__name__)

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND

user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

user32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
]
user32.SendMessageTimeoutW.restype = wintypes.LPARAM

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL

user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND

user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL

kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
kernel32.Process32FirstW.restype = wintypes.BOOL

kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
kernel32.Process32NextW.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.GetProcessTimes.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.FILETIME),
    ctypes.POINTER(wintypes.FILETIME),
    ctypes.POINTER(wintypes.FILETIME),
    ctypes.POINTER(wintypes.FILETIME),
]
kernel32.GetProcessTimes.restype = wintypes.BOOL

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

kernel32.QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    pid: int
    title: str
    class_name: str
    visible: bool


def is_window_alive(hwnd: int) -> bool:
    return bool(user32.IsWindow(wintypes.HWND(hwnd)))


def wait_for_window_closed(hwnd: int, timeout_seconds: float = 3.0, poll_interval: float = 0.05) -> bool:
    start = time.time()
    while time.time() - start < timeout_seconds:
        if not is_window_alive(hwnd):
            return True
        time.sleep(poll_interval)
    return not is_window_alive(hwnd)


def send_wm_close(hwnd: int) -> bool:
    WM_CLOSE = 0x0010
    ok = bool(user32.PostMessageW(wintypes.HWND(hwnd), WM_CLOSE, 0, 0))
    return ok


def send_wm_close_and_wait(hwnd: int, *, timeout_ms: int = 500) -> bool:
    """
    WM_CLOSE를 동기적으로 보내고(응답 대기), 호출 자체가 완료되었는지 반환.
    창이 실제로 닫혔는지는 wait_for_window_closed로 별도 검증해야 한다.
    """
    WM_CLOSE = 0x0010
    SMTO_ABORTIFHUNG = 0x0002
    # result는 사용하지 않음
    r = user32.SendMessageTimeoutW(
        wintypes.HWND(hwnd),
        WM_CLOSE,
        0,
        0,
        SMTO_ABORTIFHUNG,
        int(timeout_ms),
        None,
    )
    return bool(r)


def _get_owner_hwnd(hwnd: int) -> int:
    GW_OWNER = 4
    return int(user32.GetWindow(wintypes.HWND(hwnd), GW_OWNER))


def wait_for_save_dialog(
    *,
    owner_hwnd: int | None = None,
    target_pid: int | None = None,
    timeout_seconds: float = 2.0,
    poll_interval: float = 0.05,
) -> WindowInfo | None:
    """
    저장 여부 팝업(일반적으로 class '#32770')을 best-effort로 탐지.
    - owner_hwnd가 주어지면 GW_OWNER가 해당 hwnd인 다이얼로그 우선
    - target_pid가 주어지면 pid가 일치하는 다이얼로그 우선
    """
    start = time.time()
    while time.time() - start < timeout_seconds:
        for w in enum_windows():
            if not w.visible:
                continue
            cls = (w.class_name or "").lower()
            if cls != "#32770":
                continue
            if owner_hwnd is not None:
                if _get_owner_hwnd(w.hwnd) != int(owner_hwnd):
                    continue
            if target_pid is not None and w.pid != int(target_pid):
                continue
            return w
        time.sleep(poll_interval)
    return None


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    parent_pid: int
    exe: str


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def list_processes() -> list[ProcessInfo]:
    TH32CS_SNAPPROCESS = 0x00000002
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == wintypes.HANDLE(-1).value:
        return []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        procs: list[ProcessInfo] = []
        while ok:
            procs.append(
                ProcessInfo(
                    pid=int(entry.th32ProcessID),
                    parent_pid=int(entry.th32ParentProcessID),
                    exe=str(entry.szExeFile),
                )
            )
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
        return procs
    finally:
        kernel32.CloseHandle(snap)

def _filetime_to_epoch_seconds(ft: wintypes.FILETIME) -> float:
    # FILETIME: 100-ns intervals since 1601-01-01 UTC
    val = (int(ft.dwHighDateTime) << 32) + int(ft.dwLowDateTime)
    return (val / 10_000_000.0) - 11644473600.0


def get_process_create_time(pid: int) -> float | None:
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, wintypes.DWORD(pid))
    if not h:
        return None
    try:
        c = wintypes.FILETIME()
        e = wintypes.FILETIME()
        k = wintypes.FILETIME()
        u = wintypes.FILETIME()
        if not kernel32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
            return None
        return _filetime_to_epoch_seconds(c)
    finally:
        kernel32.CloseHandle(h)


def get_process_image_basename(pid: int) -> str | None:
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, wintypes.DWORD(pid))
    if not h:
        return None
    try:
        buf_len = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(buf_len.value)
        if not kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(buf_len)):
            return None
        path = buf.value
        return path.split("\\")[-1]
    finally:
        kernel32.CloseHandle(h)


def find_descendant_pids(root_pid: int, *, exe_name: str | None = None, max_depth: int = 3) -> list[int]:
    """
    root_pid의 자식/손자 프로세스 pid를 찾아 반환.
    modern notepad이 launcher pid를 만들고 실제 UI pid를 별도로 띄우는 케이스를 흡수하기 위함.
    """
    procs = list_processes()
    children_map: dict[int, list[ProcessInfo]] = {}
    for p in procs:
        children_map.setdefault(p.parent_pid, []).append(p)

    result: list[int] = []
    frontier = [(root_pid, 0)]
    seen: set[int] = {root_pid}
    while frontier:
        pid, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for child in children_map.get(pid, []):
            if child.pid in seen:
                continue
            seen.add(child.pid)
            if exe_name is None or child.exe.lower() == exe_name.lower():
                result.append(child.pid)
            frontier.append((child.pid, depth + 1))
    return result

def _get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(wintypes.HWND(hwnd))
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(wintypes.HWND(hwnd), buf, length + 1)
    return buf.value


def _get_window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(pid))
    return int(pid.value)

def _get_window_class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(wintypes.HWND(hwnd), buf, 256)
    return buf.value

def _get_window_thread_id(hwnd: int) -> int:
    pid = wintypes.DWORD(0)
    tid = user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(pid))
    return int(tid)

def enum_windows() -> Iterable[WindowInfo]:
    items: list[WindowInfo] = []

    @EnumWindowsProc
    def _cb(hwnd: wintypes.HWND, lparam: wintypes.LPARAM) -> wintypes.BOOL:
        try:
            ihwnd = int(hwnd)
            visible = bool(user32.IsWindowVisible(hwnd))
            pid = _get_window_pid(ihwnd)
            title = _get_window_text(ihwnd)
            cls = _get_window_class_name(ihwnd)
            items.append(WindowInfo(hwnd=ihwnd, pid=pid, title=title, class_name=cls, visible=visible))
        except Exception:
            # best-effort: keep enumerating
            return True
        return True

    user32.EnumWindows(_cb, 0)
    return items


def find_top_level_windows_by_pid(pid: int, *, require_visible: bool = True) -> list[WindowInfo]:
    wins = []
    for w in enum_windows():
        if w.pid != pid:
            continue
        if require_visible and not w.visible:
            continue
        wins.append(w)
    # title 있는 창을 우선
    wins.sort(key=lambda x: (x.title == "", x.hwnd))
    return wins


def get_foreground_window() -> WindowInfo | None:
    hwnd = int(user32.GetForegroundWindow())
    if hwnd == 0:
        return None
    pid = _get_window_pid(hwnd)
    title = _get_window_text(hwnd)
    cls = _get_window_class_name(hwnd)
    visible = bool(user32.IsWindowVisible(hwnd))
    return WindowInfo(hwnd=hwnd, pid=pid, title=title, class_name=cls, visible=visible)


def is_foreground_pid(pid: int) -> bool:
    fg = get_foreground_window()
    return fg is not None and fg.pid == pid


def _attach_thread_input(fg_hwnd: int, target_hwnd: int) -> tuple[int, int, int]:
    fg_tid = _get_window_thread_id(fg_hwnd)
    target_tid = _get_window_thread_id(target_hwnd)
    current_tid = int(kernel32.GetCurrentThreadId())
    return fg_tid, target_tid, current_tid


def bring_window_to_foreground(hwnd: int, *, timeout_seconds: float = 2.0) -> bool:
    """
    가능한 범위에서 HWND를 포그라운드로 올린다.
    Win32 정책상 100% 보장은 어렵지만, AttachThreadInput+ShowWindow로 성공률을 높인다.
    """
    if hwnd == 0:
        return False

    # 최소화된 창이면 복원
    SW_RESTORE = 9
    user32.ShowWindow(wintypes.HWND(hwnd), SW_RESTORE)

    # 포그라운드 윈도우가 없으면 그냥 시도
    start = time.time()
    while time.time() - start < timeout_seconds:
        fg_hwnd = int(user32.GetForegroundWindow())
        if fg_hwnd == hwnd:
            return True

        if fg_hwnd != 0:
            fg_tid, target_tid, _cur_tid = _attach_thread_input(fg_hwnd, hwnd)
            try:
                user32.AttachThreadInput(fg_tid, target_tid, True)
                user32.SetForegroundWindow(wintypes.HWND(hwnd))
                user32.BringWindowToTop(wintypes.HWND(hwnd))
                user32.SetFocus(wintypes.HWND(hwnd))
            finally:
                user32.AttachThreadInput(fg_tid, target_tid, False)
        else:
            user32.SetForegroundWindow(wintypes.HWND(hwnd))
            user32.BringWindowToTop(wintypes.HWND(hwnd))
            user32.SetFocus(wintypes.HWND(hwnd))

        time.sleep(0.05)

    return int(user32.GetForegroundWindow()) == hwnd


def wait_for_window_for_pid(pid: int, *, timeout_seconds: float = 5.0, poll_interval: float = 0.1) -> WindowInfo | None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        wins = find_top_level_windows_by_pid(pid, require_visible=True)
        if wins:
            return wins[0]
        time.sleep(poll_interval)
    return None


def wait_for_window_for_pid_or_descendant(
    pid: int,
    *,
    timeout_seconds: float = 5.0,
    poll_interval: float = 0.1,
    exe_name: str | None = "notepad.exe",
) -> WindowInfo | None:
    """
    1) pid의 top-level window를 기다린다.
    2) 없으면 pid의 자식/손자 프로세스들(선택적으로 exe_name 필터)을 따라가며 window를 찾는다.
    """
    start = time.time()
    checked_descendants_at = 0.0
    while time.time() - start < timeout_seconds:
        w = wait_for_window_for_pid(pid, timeout_seconds=poll_interval, poll_interval=poll_interval)
        if w is not None:
            return w

        # 너무 자주 프로세스 스냅샷을 뜨지 않도록 (poll_interval의 5배 정도)
        now = time.time()
        if now - checked_descendants_at >= max(0.2, poll_interval * 5):
            checked_descendants_at = now
            # 1차: exe_name 필터 적용(기본 notepad.exe)
            candidate_pids = find_descendant_pids(pid, exe_name=exe_name, max_depth=4)
            # 2차: modern notepad이 호스트 프로세스(ApplicationFrameHost 등)에 window를 두는 경우를 위해 필터 없이도 시도
            if not candidate_pids:
                candidate_pids = find_descendant_pids(pid, exe_name=None, max_depth=4)

            for child_pid in candidate_pids:
                cw = wait_for_window_for_pid(child_pid, timeout_seconds=poll_interval, poll_interval=poll_interval)
                if cw is not None:
                    return cw

        time.sleep(poll_interval)

    return None


def wait_for_top_level_window_by_exe_after(
    exe_basename: str,
    *,
    created_after_epoch: float,
    timeout_seconds: float = 5.0,
    poll_interval: float = 0.1,
) -> WindowInfo | None:
    """
    notepad.exe launcher PID가 실제 UI PID와 다른 환경을 위한 보조 경로.
    EnumWindows로 모든 window를 훑고, pid -> exe basename, create time을 확인해 가장 최근 창을 고른다.
    """
    exe_basename = exe_basename.lower()
    start = time.time()
    best: tuple[float, WindowInfo] | None = None  # (create_time, win)
    while time.time() - start < timeout_seconds:
        for w in enum_windows():
            if not w.visible:
                continue
            img = get_process_image_basename(w.pid)
            if not img or img.lower() != exe_basename:
                continue
            ct = get_process_create_time(w.pid)
            if ct is None or ct < created_after_epoch:
                continue
            if best is None or ct > best[0]:
                best = (ct, w)
        if best is not None:
            return best[1]
        time.sleep(poll_interval)
    return None


def wait_for_new_notepad_like_window(
    baseline_hwnds: set[int],
    *,
    timeout_seconds: float = 5.0,
    poll_interval: float = 0.1,
) -> WindowInfo | None:
    """
    실행 직전의 top-level window 목록(baseline)과 비교해서,
    새로 생긴 notepad-like 창을 찾는다.
    - title에 'Notepad' 또는 '메모장' 포함
    - 또는 class_name이 'Notepad'
    """
    start = time.time()
    while time.time() - start < timeout_seconds:
        for w in enum_windows():
            if w.hwnd in baseline_hwnds:
                continue
            if not w.visible:
                continue
            t = (w.title or "").lower()
            cls = (w.class_name or "").lower()
            if "notepad" in t or "메모장" in (w.title or "") or cls == "notepad":
                return w
        time.sleep(poll_interval)
    return None

