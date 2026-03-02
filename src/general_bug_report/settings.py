from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Settings:
    upload_root: Path
    max_bytes: int
    allowed_log_ext: set[str]
    allowed_save_ext: set[str]
    allowed_img_ext: set[str]
    allowed_files_ext: set[str]
    default_webhook: str
    default_app_id: str
    default_app_secret: str
    default_bitable_app_token: str
    default_bitable_table_id: str
    default_bitable_parent_node: str
    default_fields_map: dict[str, str]
    default_constants: dict[str, Any]
    projects: dict[str, dict[str, Any]]


def _load_local_config_module() -> dict[str, Any]:
    cfg_path = os.getenv("BUG_REPORT_CONFIG_PATH", "config.py")
    path = Path(cfg_path)
    if not path.exists():
        return {}
    spec = importlib.util.spec_from_file_location("local_bug_report_config", path)
    if not spec or not spec.loader:
        return {}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {k: getattr(mod, k) for k in dir(mod) if k.isupper()}


def load_settings() -> Settings:
    local_cfg = _load_local_config_module()

    default_fields_map = {
        "bug_title": "Bug Title",
        "version": "Version",
        "bug_type": "Bug Type",
        "stable": "Stable Reproducible",
        "player_id": "Player ID",
        "hardware": "Hardware",
        "name": "Name",
        "contact": "Contact",
        "description": "Description",
        "received": "Upload Time",
        "category": "Category",
        "files": "Files",
        "screenshot": "Screenshot",
    }

    settings = Settings(
        upload_root=Path(local_cfg.get("UPLOAD_ROOT", os.getenv("UPLOAD_ROOT", "./uploads"))).resolve(),
        max_bytes=int(local_cfg.get("MAX_BYTES", os.getenv("MAX_BYTES", str(6 * 1024 * 1024)))),
        allowed_log_ext=set(local_cfg.get("ALLOWED_LOG_EXT", {".log", ".zip", ".txt"})),
        allowed_save_ext=set(local_cfg.get("ALLOWED_SAVE_EXT", {".zip", ".sav"})),
        allowed_img_ext=set(local_cfg.get("ALLOWED_IMG_EXT", {".jpg", ".jpeg", ".png"})),
        allowed_files_ext=set(local_cfg.get("ALLOWED_FILES_EXT", {".zip"})),
        default_webhook=str(local_cfg.get("DEFAULT_WEBHOOK", os.getenv("DEFAULT_WEBHOOK", ""))),
        default_app_id=str(local_cfg.get("DEFAULT_APP_ID", os.getenv("DEFAULT_APP_ID", ""))),
        default_app_secret=str(local_cfg.get("DEFAULT_APP_SECRET", os.getenv("DEFAULT_APP_SECRET", ""))),
        default_bitable_app_token=str(local_cfg.get("DEFAULT_BITABLE_APP_TOKEN", os.getenv("DEFAULT_BITABLE_APP_TOKEN", ""))),
        default_bitable_table_id=str(local_cfg.get("DEFAULT_BITABLE_TABLE_ID", os.getenv("DEFAULT_BITABLE_TABLE_ID", ""))),
        default_bitable_parent_node=str(local_cfg.get("DEFAULT_BITABLE_PARENT_NODE", os.getenv("DEFAULT_BITABLE_PARENT_NODE", ""))),
        default_fields_map=dict(local_cfg.get("DEFAULT_FIELDS_MAP", default_fields_map)),
        default_constants=dict(local_cfg.get("DEFAULT_CONSTANTS", {"category_value": "Bug"})),
        projects=dict(local_cfg.get("PROJECTS", {})),
    )

    settings.upload_root.mkdir(parents=True, exist_ok=True)
    return settings


def validate_settings(settings: Settings) -> None:
    if not settings.projects:
        raise RuntimeError(
            "No project configuration found. Copy config.example.py to config.py and fill PROJECTS."
        )
