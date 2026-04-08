from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class MoveAction(BaseModel):
    type: Literal["move"] = "move"
    x: int = Field(..., ge=0, description="대상 X (픽셀)")
    y: int = Field(..., ge=0, description="대상 Y (픽셀)")
    duration: float = Field(default=0.0, ge=0.0, description="이동 애니메이션 시간(초)")


class ClickAction(BaseModel):
    type: Literal["click"] = "click"
    x: int | None = Field(default=None, description="None이면 현재 위치")
    y: int | None = Field(default=None, description="None이면 현재 위치")
    button: Literal["left", "right", "middle"] = "left"
    clicks: int = Field(default=1, ge=1, le=3)


class DoubleClickAction(BaseModel):
    type: Literal["double_click"] = "double_click"
    x: int | None = None
    y: int | None = None
    button: Literal["left", "right", "middle"] = "left"


class ScrollAction(BaseModel):
    type: Literal["scroll"] = "scroll"
    clicks: int = Field(..., description="양수: 위, 음수: 아래(클릭 단위)")


class TypeAction(BaseModel):
    type: Literal["type"] = "type"
    text: str = Field(..., min_length=1, max_length=500, description="입력할 문구 (MVP 길이 제한)")


class HotkeyAction(BaseModel):
    type: Literal["hotkey"] = "hotkey"
    keys: list[str] = Field(..., min_length=1, description="PyAutoGUI 키 이름 순서")


class WaitAction(BaseModel):
    type: Literal["wait"] = "wait"
    seconds: float = Field(..., gt=0.0, le=300.0, description="대기(초)")


class DoneAction(BaseModel):
    type: Literal["done"] = "done"
    reason: str | None = Field(default=None, description="종료 사유(로그용)")


Action = Annotated[
    Union[
        MoveAction,
        ClickAction,
        DoubleClickAction,
        ScrollAction,
        TypeAction,
        HotkeyAction,
        WaitAction,
        DoneAction,
    ],
    Field(discriminator="type"),
]
