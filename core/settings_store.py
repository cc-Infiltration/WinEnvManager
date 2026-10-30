"""应用数据目录与设置持久化。"""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "VarManager"
BACKUPS_DIR = APP_DIR / "backups"
SETTINGS_PATH = APP_DIR / "settings.json"

DEFAULT_SETTINGS = {"broadcast": True}


def ensure_dirs() -> None:
    try:
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # 数据目录不可用时功能降级，主界面仍可运行


def load_settings() -> dict:
    try:
        data = json.loads(SETTINGS_PATH.read_text("utf-8"))
        if isinstance(data, dict):
            merged = dict(DEFAULT_SETTINGS)
            merged.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
            return merged
    except (OSError, ValueError):
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    ensure_dirs()
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), "utf-8"
    )
