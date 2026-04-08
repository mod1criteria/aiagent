import logging
import sys
from pathlib import Path


def setup_logging(log_dir: Path, level: str = "INFO") -> Path:
    """
    콘솔 + logs/agent.log 파일에 동시 기록.
    반환: 로그 파일 경로.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "agent.log"

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(level.upper())
    fh.setFormatter(fmt)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(level.upper())
    sh.setFormatter(fmt)

    root.addHandler(fh)
    root.addHandler(sh)

    logging.getLogger(__name__).debug("Logging initialized: %s", log_file)
    return log_file
