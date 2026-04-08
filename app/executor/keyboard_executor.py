from __future__ import annotations

import pyautogui

from app.models.action import HotkeyAction, TypeAction


class KeyboardExecutor:
    def type_text(self, action: TypeAction, *, interval: float = 0.02) -> None:
        pyautogui.write(action.text, interval=interval)

    def hotkey(self, action: HotkeyAction) -> None:
        pyautogui.hotkey(*action.keys)

