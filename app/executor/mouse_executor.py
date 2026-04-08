from __future__ import annotations

import pyautogui

from app.models.action import ClickAction, DoubleClickAction, MoveAction, ScrollAction


class MouseExecutor:
    def move(self, action: MoveAction) -> None:
        pyautogui.moveTo(action.x, action.y, duration=action.duration)

    def click(self, action: ClickAction) -> None:
        if action.x is not None and action.y is not None:
            pyautogui.click(action.x, action.y, clicks=action.clicks, button=action.button)
            return
        pyautogui.click(clicks=action.clicks, button=action.button)

    def double_click(self, action: DoubleClickAction) -> None:
        if action.x is not None and action.y is not None:
            pyautogui.doubleClick(action.x, action.y, button=action.button)
            return
        pyautogui.doubleClick(button=action.button)

    def scroll(self, action: ScrollAction) -> None:
        pyautogui.scroll(action.clicks)

