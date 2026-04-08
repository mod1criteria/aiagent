from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)


def save_screenshot(image: Image.Image, screenshot_dir: Path, prefix: str = "screen") -> Path:
    """PNG로 저장하고 경로를 반환."""
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = screenshot_dir / f"{prefix}_{ts}.png"
    image.save(path, format="PNG")
    logger.info("Screenshot saved: %s", path)
    return path
