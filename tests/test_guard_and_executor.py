from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.executor.action_executor import ActionExecutor
from app.guard.action_guard import ActionGuard, GuardContext, GuardViolation
from app.models.action import HotkeyAction, TypeAction, WaitAction


def test_guard_blocks_disallowed_hotkey() -> None:
    guard = ActionGuard()
    ctx = GuardContext(screen_size=(1920, 1080))
    with pytest.raises(GuardViolation):
        guard.validate(HotkeyAction(keys=["ctrl", "l"]), ctx)


def test_guard_blocks_overlong_type() -> None:
    guard = ActionGuard()
    ctx = GuardContext(screen_size=(1920, 1080))
    # Pydantic 모델에서 먼저 길이가 차단되므로(500), Guard까지 도달하지 않는다.
    with pytest.raises(ValidationError):
        guard.validate(TypeAction(text="x" * 501), ctx)


def test_guard_allows_allowed_hotkey() -> None:
    guard = ActionGuard()
    ctx = GuardContext(screen_size=(1920, 1080))
    guard.validate(HotkeyAction(keys=["alt", "f4"]), ctx)


def test_executor_wait_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        calls.append(seconds)

    import time as time_module

    monkeypatch.setattr(time_module, "sleep", fake_sleep)

    ex = ActionExecutor()
    ex.execute_one(WaitAction(seconds=0.2))
    assert calls == [0.2]

