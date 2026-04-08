from __future__ import annotations

from app.config import Settings
from app.models.action import (
    Action,
    HotkeyAction,
    WaitAction,
    DoneAction,
    TypeAction,
)

def default_smoke_actions(settings: Settings) -> list[Action]:
    """메모장 포커스 보장 후 하드코딩 타이핑."""
    return [
        WaitAction(seconds=settings.notepad_wait_seconds),
        # 요구사항: 입력 문자열 끝 newline 제거
        TypeAction(text=settings.smoke_test_text),
        WaitAction(seconds=settings.post_type_wait_seconds),
        DoneAction(reason="smoke test: typed"),
    ]

def close_notepad_actions(settings: Settings) -> list[Action]:
    return [
        HotkeyAction(keys=["alt", "f4"]),
        WaitAction(seconds=min(1.0, max(0.1, settings.save_prompt_wait_seconds))),
        DoneAction(reason="smoke test: close attempted"),
    ]
