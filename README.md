# local-pc-agent (MVP)

Windows 단일 PC에서 PyAutoGUI로 마우스/키보드를 제어하는 **최소 실행 루프**입니다.  
이 단계에서는 **LLM·OCR·UIA·브라우저 자동화·OpenAI API를 연결하지 않습니다.**

## 사전 요구 사항

- Windows 10/11
- Python 3.10+
- 가상 환격 권장 (`python -m venv .venv` 후 활성화)

## 설치

프로젝트 루트(`pyproject.toml`이 있는 디렉터리)에서:

```powershell
pip install -e .
```

또는:

```powershell
pip install pyautogui pydantic pydantic-settings Pillow
```

## 실행

프로젝트 루트에서:

```powershell
python -m app.main
```

동작 요약:

1. `logs/`에 `agent.log` 기록
2. `screenshots/`에 `before_smoke_*.png`, `after_smoke_*.png` 저장
3. `notepad.exe` 실행 후 하드코딩된 문자열을 **PyAutoGUI `write`**로 입력

## 확인 방법

- 메모장 창에 설정(`SMOKE_TEST_TEXT` 또는 `.env`의 `smoke_test_text`)에 해당하는 문구가 보이는지 확인
- `logs/agent.log`에 단계 로그가 쌓였는지 확인
- `screenshots/`에 실행 전·후 PNG가 생성되었는지 확인

## Fail-safe 및 안전 주의

- **PyAutoGUI fail-safe (기본 ON)**: 마우스 포인터를 **화면 네 모서리** 중 하나로 빠르게 이동하면 예외가 나며 자동화가 멈출 수 있습니다. 테스트 중에는 모서리로 드래그하지 마세요.
- 설정의 `FAILSAFE=true`(기본)를 유지하는 것을 권장합니다. 끄려면 `.env`에서 `FAILSAFE=false`(비권장)로 바꿀 수 있습니다.
- 본 MVP는 **비밀번호·OTP·결제·파일 삭제·외부 전송·설치 프로그램·시스템 설정 변경** 자동화를 대상으로 하지 않습니다.

## 설정 (.env)

| 변수 | 설명 |
|------|------|
| `LOG_LEVEL` | 로깅 레벨 (예: INFO) |
| `LOG_DIR` | 로그 디렉터리 |
| `SCREENSHOT_DIR` | 스크린샷 디렉터리 |
| `PYAUTOGUI_PAUSE` | PyAutoGUI 각 호출 사이 지연(초) |
| `FAILSAFE` | PyAutoGUI fail-safe 사용 여부 |

`app.config.Settings`의 필드명은 소문자 스네이크 케이스이며, 환경 변수와 매핑됩니다.

## 테스트 (선택)

```powershell
pip install -e ".[dev]"
pytest
```

## 다음 단계

- `guard/`: 액션 스키마·화면 밖 좌표·위험 액션 차단
- `runner.py`: 관찰 → (향후 Planner) → Guard → Executor 루프
- `observer/`: 활성 창 제목·해상도 메타데이터 확장
- 마지막에 `planner/` LLM 연결
