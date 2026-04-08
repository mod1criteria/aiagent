from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 변수(.env) 및 기본값에서 로드하는 실행 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = "INFO"
    log_dir: Path = Path("logs")
    screenshot_dir: Path = Path("screenshots")
    pyautogui_pause: float = 0.15
    failsafe: bool = True
    notepad_wait_seconds: float = 1.5
    post_type_wait_seconds: float = 0.7
    close_wait_seconds: float = 0.4
    save_prompt_wait_seconds: float = 0.6
    notepad_window_timeout_seconds: float = 5.0
    focus_timeout_seconds: float = 2.0
    smoke_test_text: str = "local-pc-agent MVP smoke test (PyAutoGUI type)"

    def ensure_directories(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    return Settings()
