from __future__ import annotations

import logging
import subprocess
import sys
import time
from typing import Callable

import pyautogui

from app.config import Settings
from app.observer.window_info import (
    bring_window_to_foreground,
    enum_windows,
    get_foreground_window,
    is_foreground_pid,
    is_window_alive,
    send_wm_close,
    send_wm_close_and_wait,
    wait_for_save_dialog,
    wait_for_window_closed,
    wait_for_window_for_pid_or_descendant,
    wait_for_top_level_window_by_exe_after,
    wait_for_new_notepad_like_window,
 )
from app.models.action import (
    Action,
    ClickAction,
    DoneAction,
    DoubleClickAction,
    HotkeyAction,
    MoveAction,
    ScrollAction,
    TypeAction,
    WaitAction,
)

logger = logging.getLogger(__name__)


def apply_pyautogui_settings(settings: Settings) -> None:
    pyautogui.FAILSAFE = settings.failsafe
    pyautogui.PAUSE = settings.pyautogui_pause
    logger.info(
        "PyAutoGUI: FAILSAFE=%s, PAUSE=%s (화면 모서리로 마우스를 옮기면 중단될 수 있음)",
        pyautogui.FAILSAFE,
        pyautogui.PAUSE,
    )


def execute_action(action: Action, screen_size: tuple[int, int]) -> None:
    """단일 액션 실행 (MVP: Guard 없음, 화면 밖 좌표는 추후 Guard에서 검증 예정)."""
    _ = screen_size  # 시그니처 유지: 추후 Guard에서 화면 경계 검증에 전달 예정
    if isinstance(action, MoveAction):
        pyautogui.moveTo(action.x, action.y, duration=action.duration)
        return
    if isinstance(action, ClickAction):
        if action.x is not None and action.y is not None:
            pyautogui.click(action.x, action.y, clicks=action.clicks, button=action.button)
        else:
            pyautogui.click(clicks=action.clicks, button=action.button)
        return
    if isinstance(action, DoubleClickAction):
        if action.x is not None and action.y is not None:
            pyautogui.doubleClick(action.x, action.y, button=action.button)
        else:
            pyautogui.doubleClick(button=action.button)
        return
    if isinstance(action, ScrollAction):
        pyautogui.scroll(action.clicks)
        return
    if isinstance(action, TypeAction):
        pyautogui.write(action.text, interval=0.02)
        return
    if isinstance(action, HotkeyAction):
        pyautogui.hotkey(*action.keys)
        return
    if isinstance(action, WaitAction):
        time.sleep(action.seconds)
        return
    if isinstance(action, DoneAction):
        logger.info("done: %s", action.reason or "complete")
        return
    raise TypeError(f"Unsupported action: {type(action)!r}")


def run_action_sequence(
    actions: list[Action],
    screen_size: tuple[int, int],
    describe_screen: Callable[[], tuple[int, int]] | None = None,
    *,
    pre_action_check: Callable[[Action], bool] | None = None,
) -> None:
    for i, act in enumerate(actions):
        if pre_action_check is not None:
            if not pre_action_check(act):
                logger.error("Aborted before step %s due to focus verification failure.", i + 1)
                return
        logger.info("Step %s: %s", i + 1, act)
        execute_action(act, screen_size)
        if describe_screen and isinstance(act, (MoveAction, ClickAction, DoubleClickAction)):
            screen_size = describe_screen()


def open_notepad() -> None:
    """메모장 프로세스 시작 (실행 파일은 OS 기본)."""
    if sys.platform != "win32":
        raise RuntimeError("This smoke test targets Windows notepad.exe.")
    p = subprocess.Popen(["notepad.exe"], shell=False)
    logger.info("Launched notepad.exe via subprocess. pid=%s", p.pid)
    return p.pid


def default_smoke_actions(settings: Settings) -> list[Action]:
    """메모장 포커스 보장 후 하드코딩 타이핑(종료는 별도 verify 루틴)."""
    return [
        WaitAction(seconds=settings.notepad_wait_seconds),
        # 요구사항: 입력 문자열 끝 newline 제거
        TypeAction(text=settings.smoke_test_text),
        WaitAction(seconds=settings.post_type_wait_seconds),
        DoneAction(reason="smoke test: typed"),
    ]


def run_manual_smoke(settings: Settings) -> None:
    """
    수동 스모크: 메모장 실행 후 PyAutoGUI로 텍스트 입력.
    비밀번호/OTP/결제/삭제/외부전송 등은 본 MVP에서 수행하지 않음.
    """
    apply_pyautogui_settings(settings)
    screen_size = pyautogui.size()
    logger.info("Screen size: %sx%s", screen_size.width, screen_size.height)
    size_tuple = (screen_size.width, screen_size.height)

    def refresh_size() -> tuple[int, int]:
        s = pyautogui.size()
        return (s.width, s.height)

    launched_at = time.time()
    baseline_hwnds = {w.hwnd for w in enum_windows()}
    notepad_pid = open_notepad()

    # 4) PID 기반으로 notepad 윈도우 찾기
    w = wait_for_window_for_pid_or_descendant(notepad_pid, timeout_seconds=settings.notepad_window_timeout_seconds)
    # 일부 환경에서는 launcher PID != 실제 UI PID. 보조 경로로 notepad.exe 창을 찾는다.
    if w is None:
        w = wait_for_top_level_window_by_exe_after(
            "notepad.exe",
            created_after_epoch=max(0.0, launched_at - 1.0),
            timeout_seconds=settings.notepad_window_timeout_seconds,
        )
    if w is None:
        w = wait_for_new_notepad_like_window(
            baseline_hwnds,
            timeout_seconds=settings.notepad_window_timeout_seconds,
        )
    if w is None:
        logger.error("Notepad window not found for pid=%s within timeout.", notepad_pid)
        # 디버그 정보: notepad 관련 제목을 가진 top-level window 후보들
        try:
            candidates = []
            for win in enum_windows():
                t = (win.title or "").lower()
                if "notepad" in t or "메모장" in t:
                    candidates.append(win)
            for c in candidates[:20]:
                logger.error(
                    "Window candidate: hwnd=0x%X pid=%s visible=%s class=%r title=%r",
                    c.hwnd,
                    c.pid,
                    c.visible,
                    c.class_name,
                    c.title,
                )
            if not candidates:
                logger.error("No window candidates found with title containing 'notepad'/'메모장'.")
        except Exception as e:
            logger.exception("Failed to enumerate windows for debug: %s", e)
        return

    # 5) 해당 윈도우를 foreground로 올리기
    ok = bring_window_to_foreground(w.hwnd, timeout_seconds=settings.focus_timeout_seconds)
    fg = get_foreground_window()
    logger.info(
        "Focus attempt: ok=%s hwnd=0x%X pid=%s fg_pid=%s fg_title=%r",
        ok,
        w.hwnd,
        w.pid,
        (fg.pid if fg else None),
        (fg.title if fg else None),
    )

    # 6) 입력 직전에 foreground PID 검증 (실패 시 즉시 중단)
    effective_pid = w.pid
    if not is_foreground_pid(effective_pid):
        logger.error(
            "Abort: foreground is not notepad. No typing/hotkeys will be sent. expected_pid=%s",
            effective_pid,
        )
        return

    def focus_gate(act: Action) -> bool:
        # 6) 입력 직전 검증
        if isinstance(act, TypeAction):
            return is_foreground_pid(effective_pid)
        # 7) Alt+F4 직전 검증
        if isinstance(act, HotkeyAction) and [k.lower() for k in act.keys] == ["alt", "f4"]:
            return is_foreground_pid(effective_pid)
        return True

    run_action_sequence(
        default_smoke_actions(settings),
        size_tuple,
        describe_screen=refresh_size,
        pre_action_check=focus_gate,
    )

    # --- 종료 시나리오: action -> observe -> verify -> fallback ---
    target_hwnd = w.hwnd
    if not is_window_alive(target_hwnd):
        logger.info("Notepad window already closed after typing. hwnd=0x%X", target_hwnd)
        return

    # 7) Alt+F4 직전에도 foreground pid 검증
    if not is_foreground_pid(effective_pid):
        logger.error("Abort: foreground is not notepad before close. No close will be attempted. expected_pid=%s", effective_pid)
        return

    logger.info("Attempt close via Alt+F4. hwnd=0x%X pid=%s", target_hwnd, effective_pid)
    pyautogui.hotkey("alt", "f4")

    # 1) Alt+F4 후: 닫힘 or 저장 dialog 탐지
    dlg = wait_for_save_dialog(owner_hwnd=target_hwnd, timeout_seconds=settings.save_prompt_wait_seconds)
    closed = wait_for_window_closed(target_hwnd, timeout_seconds=settings.save_prompt_wait_seconds)
    if closed:
        logger.info("Close success: target window closed after Alt+F4. hwnd=0x%X", target_hwnd)
        return
    if dlg is None:
        logger.error("Close failure: after Alt+F4 neither window closed nor save dialog appeared. hwnd=0x%X", target_hwnd)

        # 3) fallback: WM_CLOSE
        logger.info("Fallback: send WM_CLOSE to target hwnd. hwnd=0x%X", target_hwnd)
        send_ok = send_wm_close(target_hwnd)
        logger.info("WM_CLOSE posted (async): ok=%s hwnd=0x%X", send_ok, target_hwnd)

        # 동기 경로도 한 번 더 시도 (hung 방지 timeout)
        sync_ok = send_wm_close_and_wait(target_hwnd, timeout_ms=500)
        logger.info("WM_CLOSE sent (sync): ok=%s hwnd=0x%X", sync_ok, target_hwnd)

        dlg = wait_for_save_dialog(owner_hwnd=target_hwnd, timeout_seconds=settings.save_prompt_wait_seconds)
        closed = wait_for_window_closed(target_hwnd, timeout_seconds=settings.save_prompt_wait_seconds)
        if closed:
            logger.info("Close success: target window closed after WM_CLOSE. hwnd=0x%X", target_hwnd)
            return
        if dlg is None:
            logger.error("Close failure: after WM_CLOSE neither window closed nor save dialog appeared. hwnd=0x%X", target_hwnd)
            return

    # 5) dialog가 실제로 탐지되고 foreground인 경우에만 Alt+N
    logger.info("Save dialog detected: hwnd=0x%X pid=%s title=%r", dlg.hwnd, dlg.pid, dlg.title)
    bring_window_to_foreground(dlg.hwnd, timeout_seconds=settings.focus_timeout_seconds)
    fg2 = get_foreground_window()
    if fg2 is None or fg2.hwnd != dlg.hwnd:
        logger.error("Abort: save dialog is not foreground; will NOT send Alt+N. dlg_hwnd=0x%X fg=%r", dlg.hwnd, fg2)
        return

    logger.info("Send Alt+N (Don't Save) to save dialog. dlg_hwnd=0x%X", dlg.hwnd)
    pyautogui.hotkey("alt", "n")

    # 7) 최종 성공 기준: target hwnd가 사라졌는지
    if wait_for_window_closed(target_hwnd, timeout_seconds=settings.close_wait_seconds):
        logger.info("Final success: target hwnd closed. hwnd=0x%X", target_hwnd)
        return
    logger.error("Final failure: target hwnd still alive after Alt+N. hwnd=0x%X", target_hwnd)
