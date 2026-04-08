from __future__ import annotations

from dataclasses import dataclass

from app.guard.safety_rules import SafetyRules, normalize_hotkey
from app.models.action import (
    Action,
    ClickAction,
    DoubleClickAction,
    HotkeyAction,
    MoveAction,
    TypeAction,
)


class GuardViolation(ValueError):
    pass


@dataclass(frozen=True)
class GuardContext:
    screen_size: tuple[int, int]


class ActionGuard:
    def __init__(self, rules: SafetyRules | None = None) -> None:
        self._rules = rules or SafetyRules()

    @property
    def rules(self) -> SafetyRules:
        return self._rules

    def validate(self, action: Action, ctx: GuardContext) -> None:
        """
        액션을 실행 전에 검증하고, 위반 시 GuardViolation을 raise한다.
        """
        if isinstance(action, (MoveAction, ClickAction, DoubleClickAction)):
            self._validate_coords(action, ctx.screen_size)
        if isinstance(action, HotkeyAction):
            self._validate_hotkey(action)
        if isinstance(action, TypeAction):
            self._validate_type(action)

    def _validate_coords(self, action: Action, screen_size: tuple[int, int]) -> None:
        width, height = screen_size
        if width <= 0 or height <= 0:
            raise GuardViolation(f"Invalid screen size: {screen_size!r}")

        def in_bounds(x: int, y: int) -> bool:
            return 0 <= x < width and 0 <= y < height

        if isinstance(action, MoveAction):
            if not in_bounds(action.x, action.y):
                raise GuardViolation(f"Move out of bounds: ({action.x},{action.y}) screen={screen_size}")
            return

        # Click/DoubleClick: None이면 현재 위치 클릭이므로 좌표 검증 스킵
        if isinstance(action, (ClickAction, DoubleClickAction)):
            if action.x is None or action.y is None:
                return
            if not in_bounds(int(action.x), int(action.y)):
                raise GuardViolation(
                    f"{action.type} out of bounds: ({action.x},{action.y}) screen={screen_size}"
                )
            return

    def _validate_hotkey(self, action: HotkeyAction) -> None:
        keys = normalize_hotkey(action.keys)
        if not keys:
            raise GuardViolation("Hotkey keys is empty after normalization.")
        if keys not in self._rules.allowed_hotkeys:
            raise GuardViolation(f"Hotkey not allowed: {list(keys)!r}")

    def _validate_type(self, action: TypeAction) -> None:
        text = action.text or ""
        if len(text) > int(self._rules.max_type_length):
            raise GuardViolation(
                f"Type text too long: len={len(text)} max={self._rules.max_type_length}"
            )
        for pat in self._rules.forbidden_text_patterns:
            if pat.search(text):
                raise GuardViolation(f"Type contains forbidden pattern: {pat.pattern!r}")

