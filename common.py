"""Shared helpers: config, state, logging."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Works both with src/, config/, state/ folders and with all files flat in the repo root.
_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent if _HERE.name == "src" else _HERE
CONFIG_DIR = ROOT / "config" if (ROOT / "config").is_dir() else ROOT
STATE_FILE = ROOT / "state" / "history.json" if (ROOT / "state").is_dir() else ROOT / "history.json"
DRAFTS_DIR = ROOT / "drafts"


def load_settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    # Environment overrides
    if os.getenv("REPLICATE_MODEL"):
        settings["replicate_model"] = os.environ["REPLICATE_MODEL"]
    if os.getenv("POST_MODE"):
        settings["mode"] = os.environ["POST_MODE"]
    return settings


def load_scenes() -> list[dict]:
    with open(CONFIG_DIR / "scenes.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["scenes"]


def load_history() -> list[dict]:
    if not STATE_FILE.exists():
        return []
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_history(history: list[dict]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Eksik ortam değişkeni / GitHub secret: {name}")
    return value


def log(msg: str) -> None:
    print(f"[{now_utc():%H:%M:%S}] {msg}", flush=True)
