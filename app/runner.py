from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from app.config import Settings
from app.executor.action_executor import ActionExecutor, apply_pyautogui_settings
from app.guard.action_guard import ActionGuard, GuardContext, GuardViolation
from app.models.action import Action, HotkeyAction, TypeAction
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

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunResult:
    ok: bool
    steps_executed: int
    blocked_by_guard: bool
    reason: str | None = None
    notepad_pid: int | None = None
    notepad_hwnd: int | None = None
    used_fallback_wm_close: bool = False


class Runner:
    def __init__(
        self,
        *,
        guard: ActionGuard | None = None,
        executor: ActionExecutor | None = None,
    ) -> None:
        self._guard = guard or ActionGuard()
        self._executor = executor or ActionExecutor()

    def _get_screen_size(self) -> tuple[int, int]:
        import pyautogui

        sz = pyautogui.size()
        return (int(sz.width), int(sz.height))

    def _prepare_notepad_target(self, settings: Settings) -> tuple[int, int] | None:
        """
        관찰 → 메모장 실행 → 윈도우 찾기 → 포커스.
        반환: (effective_pid, hwnd) or None
        """
        import subprocess
        import sys

        if sys.platform != "win32":
            raise RuntimeError("Runner currently targets Windows notepad.exe.")

        launched_at = time.time()
        baseline_hwnds = {w.hwnd for w in enum_windows()}

        p = subprocess.Popen(["notepad.exe"], shell=False)
        notepad_pid = int(p.pid)
        logger.info("Launched notepad.exe via subprocess. pid=%s", notepad_pid)

        w = wait_for_window_for_pid_or_descendant(notepad_pid, timeout_seconds=settings.notepad_window_timeout_seconds)
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
            return None

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
        return (int(w.pid), int(w.hwnd))

    def run_notepad_scenario(
        self,
        settings: Settings,
        *,
        actions: list[Action],
        close_actions: list[Action],
    ) -> RunResult:
        """
        - 관찰
        - 타겟 준비(메모장 실행/포커스)
        - Action 리스트 수신
        - Guard 검증
        - Executor 실행
        - 결과 확인(닫힘)
        - 종료 판단
        """
        apply_pyautogui_settings(settings)
        screen_size = self._get_screen_size()
        ctx = GuardContext(screen_size=screen_size)
        logger.info("Screen size: %sx%s", screen_size[0], screen_size[1])

        prepared = self._prepare_notepad_target(settings)
        if prepared is None:
            return RunResult(
                ok=False,
                steps_executed=0,
                blocked_by_guard=False,
                reason="target_prepare_failed",
            )
        effective_pid, hwnd = prepared

        if not is_foreground_pid(effective_pid):
            return RunResult(
                ok=False,
                steps_executed=0,
                blocked_by_guard=False,
                reason="notepad_not_foreground_before_actions",
                notepad_pid=effective_pid,
                notepad_hwnd=hwnd,
            )

        steps = 0
        for i, act in enumerate(actions):
            if isinstance(act, TypeAction) and not is_foreground_pid(effective_pid):
                return RunResult(
                    ok=False,
                    steps_executed=steps,
                    blocked_by_guard=False,
                    reason="notepad_not_foreground_before_type",
                    notepad_pid=effective_pid,
                    notepad_hwnd=hwnd,
                )
            try:
                self._guard.validate(act, ctx)
            except GuardViolation as e:
                logger.error("Guard blocked step %s: %s action=%s", i + 1, e, act)
                return RunResult(
                    ok=False,
                    steps_executed=steps,
                    blocked_by_guard=True,
                    reason=str(e),
                    notepad_pid=effective_pid,
                    notepad_hwnd=hwnd,
                )
            self._executor.execute_one(act)
            steps += 1

        if not is_window_alive(hwnd):
            # typing 이후 이미 닫힌 경우도 ok로 간주(시나리오/환경에 따라)
            return RunResult(
                ok=True,
                steps_executed=steps,
                blocked_by_guard=False,
                reason="window_already_closed_after_actions",
                notepad_pid=effective_pid,
                notepad_hwnd=hwnd,
            )

        if not is_foreground_pid(effective_pid):
            return RunResult(
                ok=False,
                steps_executed=steps,
                blocked_by_guard=False,
                reason="notepad_not_foreground_before_close",
                notepad_pid=effective_pid,
                notepad_hwnd=hwnd,
            )

        used_fallback = False
        for i, act in enumerate(close_actions):
            if (
                isinstance(act, HotkeyAction)
                and [k.lower() for k in act.keys] == ["alt", "f4"]
                and not is_foreground_pid(effective_pid)
            ):
                return RunResult(
                    ok=False,
                    steps_executed=steps,
                    blocked_by_guard=False,
                    reason="notepad_not_foreground_before_alt_f4",
                    notepad_pid=effective_pid,
                    notepad_hwnd=hwnd,
                )
            try:
                self._guard.validate(act, ctx)
            except GuardViolation as e:
                logger.error("Guard blocked close step %s: %s action=%s", i + 1, e, act)
                return RunResult(
                    ok=False,
                    steps_executed=steps,
                    blocked_by_guard=True,
                    reason=str(e),
                    notepad_pid=effective_pid,
                    notepad_hwnd=hwnd,
                )
            self._executor.execute_one(act)
            steps += 1

        dlg = wait_for_save_dialog(owner_hwnd=hwnd, timeout_seconds=settings.save_prompt_wait_seconds)
        closed = wait_for_window_closed(hwnd, timeout_seconds=settings.save_prompt_wait_seconds)
        if closed:
            return RunResult(
                ok=True,
                steps_executed=steps,
                blocked_by_guard=False,
                reason="closed_after_alt_f4",
                notepad_pid=effective_pid,
                notepad_hwnd=hwnd,
                used_fallback_wm_close=False,
            )
        if dlg is None:
            logger.error("Close failure: after Alt+F4 neither window closed nor save dialog appeared. hwnd=0x%X", hwnd)
            used_fallback = True
            send_ok = send_wm_close(hwnd)
            logger.info("Fallback: WM_CLOSE posted (async): ok=%s hwnd=0x%X", send_ok, hwnd)
            sync_ok = send_wm_close_and_wait(hwnd, timeout_ms=500)
            logger.info("Fallback: WM_CLOSE sent (sync): ok=%s hwnd=0x%X", sync_ok, hwnd)
            dlg = wait_for_save_dialog(owner_hwnd=hwnd, timeout_seconds=settings.save_prompt_wait_seconds)
            closed = wait_for_window_closed(hwnd, timeout_seconds=settings.save_prompt_wait_seconds)
            if closed:
                return RunResult(
                    ok=True,
                    steps_executed=steps,
                    blocked_by_guard=False,
                    reason="closed_after_wm_close",
                    notepad_pid=effective_pid,
                    notepad_hwnd=hwnd,
                    used_fallback_wm_close=True,
                )
            if dlg is None:
                return RunResult(
                    ok=False,
                    steps_executed=steps,
                    blocked_by_guard=False,
                    reason="close_failed_no_dialog_no_close",
                    notepad_pid=effective_pid,
                    notepad_hwnd=hwnd,
                    used_fallback_wm_close=True,
                )

        # 저장 다이얼로그가 떠 있으면 Alt+N (Don't Save)
        bring_window_to_foreground(dlg.hwnd, timeout_seconds=settings.focus_timeout_seconds)
        fg = get_foreground_window()
        if fg is None or fg.hwnd != dlg.hwnd:
            return RunResult(
                ok=False,
                steps_executed=steps,
                blocked_by_guard=False,
                reason="save_dialog_not_foreground",
                notepad_pid=effective_pid,
                notepad_hwnd=hwnd,
                used_fallback_wm_close=used_fallback,
            )

        act = HotkeyAction(keys=["alt", "n"])
        try:
            self._guard.validate(act, ctx)
        except GuardViolation as e:
            logger.error("Guard blocked Alt+N: %s action=%s", e, act)
            return RunResult(
                ok=False,
                steps_executed=steps,
                blocked_by_guard=True,
                reason=str(e),
                notepad_pid=effective_pid,
                notepad_hwnd=hwnd,
                used_fallback_wm_close=used_fallback,
            )
        self._executor.execute_one(act)
        steps += 1

        if wait_for_window_closed(hwnd, timeout_seconds=settings.close_wait_seconds):
            return RunResult(
                ok=True,
                steps_executed=steps,
                blocked_by_guard=False,
                reason="closed_after_alt_n",
                notepad_pid=effective_pid,
                notepad_hwnd=hwnd,
                used_fallback_wm_close=used_fallback,
            )

        return RunResult(
            ok=False,
            steps_executed=steps,
            blocked_by_guard=False,
            reason="final_close_failed",
            notepad_pid=effective_pid,
            notepad_hwnd=hwnd,
            used_fallback_wm_close=used_fallback,
        )

