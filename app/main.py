"""
Windows 로컬 PC 제어 MVP 진입점.

- LLM/OCR/UIA/브라우저 자동화/API 연결 없음.
- PyAutoGUI fail-safe: 기본적으로 마우스를 화면 모서리로 이동하면 AbortException이 발생할 수 있음.
"""
from __future__ import annotations

import logging

import pyautogui

from app.config import load_settings
from app.executor.manual_smoke import close_notepad_actions, default_smoke_actions
from app.runner import Runner
from app.storage.logger import setup_logging
from app.storage.screenshot_store import save_screenshot

logger = logging.getLogger(__name__)


def main() -> None:
    settings = load_settings()
    settings.ensure_directories()
    setup_logging(settings.log_dir, settings.log_level)

    logger.warning(
        "안전(Fail-safe): 마우스를 화면 네 모서리 중 하나로 빠르게 옮기면 PyAutoGUI가 중단할 수 있습니다. "
        "테스트 전 마우스를 중앙 근처에 두는 것을 권장합니다."
    )
    logger.warning(
        "MVP 금지 정책: 비밀번호·OTP·결제·파일 삭제·외부 전송·설치 프로그램·시스템 설정 변경 자동화는 하지 않습니다."
    )

    shot_before = pyautogui.screenshot()
    save_screenshot(shot_before, settings.screenshot_dir, prefix="before_smoke")

    try:
        runner = Runner()
        result = runner.run_notepad_scenario(
            settings,
            actions=default_smoke_actions(settings),
            close_actions=close_notepad_actions(settings),
        )
        logger.info("RunResult: %s", result)
    finally:
        shot_after = pyautogui.screenshot()
        save_screenshot(shot_after, settings.screenshot_dir, prefix="after_smoke")

    logger.info("Smoke run finished. Check Notepad window and logs/screenshots.")


if __name__ == "__main__":
    main()
