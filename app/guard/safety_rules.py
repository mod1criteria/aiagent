from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyRules:
    """
    MVP용 최소 안전 규칙 모음.

    - allowlist 기반 hotkey 통제
    - type 길이 제한
    - 민감/위험 키워드(비밀번호/OTP/결제/삭제/외부전송/설치/설정변경 등) 차단
    """

    max_type_length: int = 500
    allowed_hotkeys: frozenset[tuple[str, ...]] = frozenset(
        {
            ("alt", "f4"),  # 창 닫기
            ("alt", "n"),  # "저장 안 함" (Notepad save dialog)
        }
    )

    # 매우 보수적인 MVP 차단 키워드. (오탐 가능성 있음)
    # - 외부 전송/업로드/공유
    # - 삭제/제거
    # - 설치/업데이트/실행
    # - 시스템 설정 변경
    # - 결제/카드/계좌
    # - 비밀번호/OTP/2FA
    forbidden_text_patterns: tuple[re.Pattern[str], ...] = (
        re.compile(r"password|passcode|passwd", re.IGNORECASE),
        re.compile(r"otp|2fa|mfa|one[- ]?time", re.IGNORECASE),
        re.compile(r"비밀번호|패스워드", re.IGNORECASE),
        re.compile(r"인증코드|일회용", re.IGNORECASE),
        re.compile(r"결제|payment|checkout|card|credit", re.IGNORECASE),
        re.compile(r"삭제|delete|remove|rm\s", re.IGNORECASE),
        re.compile(r"전송|send|upload|share|export", re.IGNORECASE),
        re.compile(r"설치|install|setup|msi|exe\s", re.IGNORECASE),
        re.compile(r"설정|settings|control panel|regedit", re.IGNORECASE),
    )


def normalize_hotkey(keys: list[str]) -> tuple[str, ...]:
    return tuple(k.strip().lower() for k in keys if k.strip())

