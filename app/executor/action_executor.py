from __future__ import annotations

import logging
import time

import pyautogui

from app.config import Settings
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
from app.executor.keyboard_executor import KeyboardExecutor
from app.executor.mouse_executor import MouseExecutor

logger = logging.getLogger(__name__)


def apply_pyautogui_settings(settings: Settings) -> None:
    pyautogui.FAILSAFE = settings.failsafe
    pyautogui.PAUSE = settings.pyautogui_pause
    logger.info(
        "PyAutoGUI: FAILSAFE=%s, PAUSE=%s (화면 모서리로 마우스를 옮기면 중단될 수 있음)",
        pyautogui.FAILSAFE,
        pyautogui.PAUSE,
    )


class ActionExecutor:
    def __init__(
        self,
        *,
        mouse: MouseExecutor | None = None,
        keyboard: KeyboardExecutor | None = None,
        type_interval_seconds: float = 0.02,
    ) -> None:
        self._mouse = mouse or MouseExecutor()
        self._keyboard = keyboard or KeyboardExecutor()
        self._type_interval_seconds = float(type_interval_seconds)

    def execute_one(self, action: Action) -> None:
        if isinstance(action, MoveAction):
            self._mouse.move(action)
            return
        if isinstance(action, ClickAction):
            self._mouse.click(action)
            return
        if isinstance(action, DoubleClickAction):
            self._mouse.double_click(action)
            return
        if isinstance(action, ScrollAction):
            self._mouse.scroll(action)
            return
        if isinstance(action, TypeAction):
            self._keyboard.type_text(action, interval=self._type_interval_seconds)
            return
        if isinstance(action, HotkeyAction):
            self._keyboard.hotkey(action)
            return
        if isinstance(action, WaitAction):
            time.sleep(action.seconds)
            return
        if isinstance(action, DoneAction):
            logger.info("done: %s", action.reason or "complete")
            return
        raise TypeError(f"Unsupported action: {type(action)!r}")

    def execute_many(self, actions: list[Action]) -> None:
        for i, action in enumerate(actions):
            logger.info("Step %s: %s", i + 1, action)
            self.execute_one(action)

