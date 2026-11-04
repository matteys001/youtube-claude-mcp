"""Central configuration. Everything local lives under ~/.creatoros (override with CREATOROS_HOME)."""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(os.environ.get("CREATOROS_HOME", str(Path.home() / ".creatoros"))).expanduser()
CLIENT_SECRET_FILE = Path(os.environ.get("CREATOROS_CLIENT_SECRET", str(APP_DIR / "client_secret.json"))).expanduser()
TOKENS_DIR = APP_DIR / "tokens"
LOG_DIR = APP_DIR / "logs"
DB_PATH = APP_DIR / "creatoros.db"
KEY_FILE = APP_DIR / ".vault_key"
SETTINGS_FILE = APP_DIR / "settings.json"

# Phase 1 is strictly read-only. Publishing scopes are added later through
# incremental authorization, never requested up front.
READ_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
PUBLISH_SCOPES_PHASE5 = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

# YouTube Analytics data is typically complete only up to ~2 days ago.
ANALYTICS_LAG_DAYS = 2
# Re-sync the video library from the Data API only when the cache is older than this.
LIBRARY_TTL_HOURS = 6
# Heuristic used only when YouTube does not tell us the format explicitly.
SHORTS_MAX_SECONDS = 180


def ensure_dirs() -> None:
    for d in (APP_DIR, TOKENS_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(d, 0o700)
        except OSError:
            pass
