"""Pydantic 액션 모델 파싱 스모크 테스트 (네트워크 없음)."""

import pytest
from pydantic import TypeAdapter, ValidationError

from app.models.action import Action


def test_valid_type_action_json() -> None:
    adapter = TypeAdapter(Action)
    a = adapter.validate_python({"type": "type", "text": "hello"})
    assert a.type == "type"
    assert a.text == "hello"


def test_invalid_action_rejected() -> None:
    adapter = TypeAdapter(Action)
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "type", "text": ""})
