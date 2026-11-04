"""Google OAuth 2.0 + encrypted local token vault.

- Never sees or stores a Google password (Google's own consent screen handles login).
- Requests only read-only scopes in Phase 1.
- Tokens are encrypted at rest (Fernet / AES) and never returned to the MCP client.
- One token file per connected channel, so several channels can be connected side by side.
"""
from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from . import config
from .errors import (AUTHENTICATION, CONFIGURATION, INVALID_INPUT, UNAVAILABLE_DATA,
                     CreatorOSError)

log = logging.getLogger("creatoros.auth")


# ---------------------------------------------------------------- vault ----
def _fernet() -> Fernet:
    config.ensure_dirs()
    if not config.KEY_FILE.exists():
        config.KEY_FILE.write_bytes(Fernet.generate_key())
        try:
            os.chmod(config.KEY_FILE, 0o600)
        except OSError:
            pass
    return Fernet(config.KEY_FILE.read_bytes())


def _token_path(channel_id: str):
    safe = "".join(c for c in channel_id if c.isalnum() or c in "-_")
    return config.TOKENS_DIR / f"{safe}.bin"


def _save(channel_id: str, payload: dict) -> None:
    path = _token_path(channel_id)
    path.write_bytes(_fernet().encrypt(json.dumps(payload).encode("utf-8")))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _load(channel_id: str) -> dict:
    path = _token_path(channel_id)
    if not path.exists():
        raise CreatorOSError(AUTHENTICATION, f"Channel {channel_id} is not connected.",
                             "Call youtube_connect_channel to connect it.")
    try:
        return json.loads(_fernet().decrypt(path.read_bytes()).decode("utf-8"))
    except InvalidToken as exc:
        raise CreatorOSError(AUTHENTICATION, "Stored token could not be decrypted (key changed or file corrupted).",
                             "Reconnect the channel with youtube_connect_channel.") from exc


# ------------------------------------------------------------ settings ----
def _settings() -> dict:
    if config.SETTINGS_FILE.exists():
        try:
            return json.loads(config.SETTINGS_FILE.read_text())
        except Exception:
            return {}
    return {}


def _write_settings(s: dict) -> None:
    config.ensure_dirs()
    config.SETTINGS_FILE.write_text(json.dumps(s, indent=2))


# ----------------------------------------------------------- connect ------
def run_connect_flow(open_browser: bool = True) -> dict:
    """Open Google's consent screen in the browser, then identify the channel that was authorized."""
    config.ensure_dirs()
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_cfg = config.oauth_client_config()
    if client_cfg:
        flow = InstalledAppFlow.from_client_config(client_cfg, scopes=config.READ_SCOPES)
    elif not config.CLIENT_SECRET_FILE.exists():
        raise CreatorOSError(
            CONFIGURATION,
            f"Google OAuth client file not found at {config.CLIENT_SECRET_FILE}.",
            "Create a 'Desktop app' OAuth client in Google Cloud (README > Configuration). Then enter its Client ID "
            "and Client Secret in the CreatorOS plugin settings, or select the JSON in the extension settings, "
            f"or save it as client_secret.json in {config.APP_DIR}.")
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(config.CLIENT_SECRET_FILE), scopes=config.READ_SCOPES)
    try:
        # stdout carries the MCP protocol; send Google's printed sign-in link to stderr instead.
        with contextlib.redirect_stdout(sys.stderr):
            creds = flow.run_local_server(
                port=0,
                open_browser=open_browser,
                timeout_seconds=300,          # give up after 5 minutes instead of hanging
                prompt="consent",            # guarantees a refresh token is issued
                access_type="offline",
                include_granted_scopes="true",  # incremental authorization for later phases
                authorization_prompt_message="CreatorOS: opening Google sign-in in your browser...\n{url}",
                success_message="CreatorOS is connected. You can close this tab and return to Claude.",
            )
    except Exception as exc:  # noqa: BLE001
        if "Timeout" in type(exc).__name__:
            raise CreatorOSError(AUTHENTICATION, "Google sign-in was not completed within 5 minutes.",
                                 "Call youtube_connect_channel again and finish sign-in in the browser tab.") from exc
        if "access_denied" in str(exc):
            raise CreatorOSError(AUTHENTICATION, "Access was denied on Google's consent screen.",
                                 "Reconnect and click 'Allow'. If you see 'app not verified', add your Gmail as a "
                                 "Test user in Google Cloud (README Step 1.4).") from exc
        raise
    granted = set(creds.scopes or [])
    missing = [s for s in config.READ_SCOPES if s not in granted]
    if missing:
        raise CreatorOSError(AUTHENTICATION, f"You did not grant all required permissions: {missing}",
                             "Reconnect and tick every checkbox on Google's consent screen.")

    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    resp = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute(num_retries=3)
    items = resp.get("items", [])
    if not items:
        raise CreatorOSError(UNAVAILABLE_DATA, "This Google account has no YouTube channel.",
                             "Sign in with the account (or pick the Brand Account) that owns the channel.")
    ch = items[0]
    channel = {
        "channel_id": ch["id"],
        "title": ch["snippet"].get("title"),
        "custom_url": ch["snippet"].get("customUrl"),
        "uploads_playlist_id": ch["contentDetails"]["relatedPlaylists"]["uploads"],
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "scopes": sorted(granted),
    }
    _save(ch["id"], {"token": json.loads(creds.to_json()), "channel": channel})
    s = _settings()
    s.setdefault("default_channel_id", ch["id"])
    _write_settings(s)
    log.info("Connected channel %s (%s)", channel["title"], channel["channel_id"])
    return channel


# ------------------------------------------------------- credentials ------
def get_credentials(channel_id: str) -> Credentials:
    payload = _load(channel_id)
    creds = Credentials.from_authorized_user_info(payload["token"], scopes=config.READ_SCOPES)
    if not creds.valid:
        if creds.refresh_token:
            creds.refresh(Request())  # RefreshError -> mapped to 'authentication' upstream
            payload["token"] = json.loads(creds.to_json())
            _save(channel_id, payload)
        else:
            raise CreatorOSError(AUTHENTICATION, "No refresh token stored for this channel.",
                                 "Reconnect with youtube_connect_channel.")
    return creds


def list_connections() -> list[dict]:
    config.ensure_dirs()
    out = []
    default = _settings().get("default_channel_id")
    for p in sorted(config.TOKENS_DIR.glob("*.bin")):
        try:
            ch = _load(p.stem)["channel"]
            ch = {k: v for k, v in ch.items() if k != "scopes"} | {"is_default": ch["channel_id"] == default}
            out.append(ch)
        except CreatorOSError:
            out.append({"channel_id": p.stem, "status": "unreadable - reconnect"})
    return out


def channel_record(channel_id: str) -> dict:
    return _load(channel_id)["channel"]


def resolve_channel_id(channel_id: str | None) -> str:
    conns = list_connections()
    if not conns:
        raise CreatorOSError(AUTHENTICATION, "No YouTube channel is connected yet.",
                             "Call youtube_connect_channel; a Google sign-in window will open.")
    ids = [c["channel_id"] for c in conns]
    if channel_id:
        if channel_id not in ids:
            raise CreatorOSError(INVALID_INPUT, f"Channel {channel_id} is not connected.",
                                 f"Connected channels: {ids}")
        return channel_id
    default = _settings().get("default_channel_id")
    if default in ids:
        return default
    if len(ids) == 1:
        return ids[0]
    raise CreatorOSError(INVALID_INPUT, "Several channels are connected; specify channel_id.",
                         f"Connected channels: {ids}")


def disconnect(channel_id: str) -> dict:
    """Revoke the grant at Google and delete the local token."""
    import requests
    revoked: Any = False
    try:
        payload = _load(channel_id)
        token = payload["token"].get("refresh_token") or payload["token"].get("token")
        if token:
            r = requests.post("https://oauth2.googleapis.com/revoke", params={"token": token},
                              headers={"content-type": "application/x-www-form-urlencoded"}, timeout=15)
            revoked = r.status_code == 200 or f"google returned {r.status_code} (token may already be invalid)"
    except CreatorOSError:
        pass
    path = _token_path(channel_id)
    existed = path.exists()
    if existed:
        path.unlink()
    s = _settings()
    if s.get("default_channel_id") == channel_id:
        s.pop("default_channel_id")
        remaining = list_connections()
        if remaining:
            s["default_channel_id"] = remaining[0]["channel_id"]
        _write_settings(s)
    return {"channel_id": channel_id, "local_token_deleted": existed, "google_grant_revoked": revoked}


def set_default(channel_id: str) -> None:
    resolve_channel_id(channel_id)
    s = _settings()
    s["default_channel_id"] = channel_id
    _write_settings(s)
