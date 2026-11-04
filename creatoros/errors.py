"""Structured errors. Every failure says WHAT kind of problem it is and HOW to fix it."""
from __future__ import annotations

import json
from typing import Any

AUTHENTICATION = "authentication"
PERMISSION = "permission"
QUOTA = "quota"
UNSUPPORTED_METRIC = "unsupported_metric"
UNAVAILABLE_DATA = "unavailable_data"
INVALID_INPUT = "invalid_input"
CONFIGURATION = "configuration"
CONFIRMATION_REQUIRED = "confirmation_required"
SYSTEM = "system"


class CreatorOSError(Exception):
    def __init__(self, category: str, message: str, fix: str = "", details: Any = None):
        super().__init__(message)
        self.category = category
        self.message = message
        self.fix = fix
        self.details = details

    def to_dict(self) -> dict:
        return {"category": self.category, "message": self.message, "how_to_fix": self.fix, "details": self.details}

    def __str__(self) -> str:
        return f"[{self.category}] {self.message}" + (f" | How to fix: {self.fix}" if self.fix else "")


QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", "userRateLimitExceeded", "RATE_LIMIT_EXCEEDED"}
PERMISSION_REASONS = {"forbidden", "insufficientPermissions", "channelNotFound", "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}
NOT_ENABLED_REASONS = {"accessNotConfigured", "SERVICE_DISABLED"}


def _google_reasons(exc: Any) -> tuple[int, list[str], str]:
    status = int(getattr(getattr(exc, "resp", None), "status", 0) or 0)
    reasons: list[str] = []
    message = str(exc)
    try:
        payload = json.loads(exc.content.decode("utf-8"))
        err = payload.get("error", {})
        message = err.get("message", message)
        for e in err.get("errors", []) or []:
            if e.get("reason"):
                reasons.append(e["reason"])
        for d in err.get("details", []) or []:
            if d.get("reason"):
                reasons.append(d["reason"])
    except Exception:
        pass
    return status, reasons, message


def from_exception(exc: Exception) -> CreatorOSError:
    """Translate Google/HTTP/auth exceptions into a CreatorOSError with a clear category."""
    if isinstance(exc, CreatorOSError):
        return exc
    name = type(exc).__name__
    if name == "RefreshError":
        return CreatorOSError(
            AUTHENTICATION,
            "Your YouTube authorization has expired or was revoked.",
            "Reconnect the channel: call youtube_connect_channel (or run `creatoros-connect`). "
            "Apps left in Google 'Testing' mode must reconnect every 7 days.",
        )
    if name == "HttpError":
        status, reasons, message = _google_reasons(exc)
        rs = set(reasons)
        if rs & QUOTA_REASONS or status == 429:
            return CreatorOSError(
                QUOTA, f"YouTube API quota exhausted: {message}",
                "Wait for the daily quota reset (midnight US Pacific Time) or request more quota in Google Cloud Console.",
                reasons)
        if "commentsDisabled" in rs:
            return CreatorOSError(UNAVAILABLE_DATA, "Comments are disabled on this video.",
                                  "Pick a video with comments enabled.", reasons)
        if rs & NOT_ENABLED_REASONS:
            return CreatorOSError(
                CONFIGURATION, f"A required Google API is not enabled: {message}",
                "Google Cloud Console > APIs & Services > Library: enable 'YouTube Data API v3' and 'YouTube Analytics API'.",
                reasons)
        if status == 401:
            return CreatorOSError(AUTHENTICATION, f"Google rejected the credentials: {message}",
                                  "Reconnect the channel with youtube_connect_channel.", reasons)
        if status == 403 or rs & PERMISSION_REASONS:
            return CreatorOSError(
                PERMISSION, f"Permission denied by YouTube: {message}",
                "Authorize the Google account (or Brand Account) that owns this channel, then reconnect.", reasons)
        low = message.lower()
        if status == 400 and ("metric" in low or "dimension" in low or "unknown identifier" in low or "not supported" in low):
            return CreatorOSError(
                UNSUPPORTED_METRIC, f"YouTube does not support this metric/dimension combination: {message}",
                "This report is not available through the public API for this query.", reasons)
        if status == 404:
            return CreatorOSError(UNAVAILABLE_DATA, f"Not found: {message}", "Check the video or channel ID.", reasons)
        return CreatorOSError(SYSTEM, f"YouTube API error {status}: {message}",
                              "Try again shortly; if it persists, check ~/.creatoros/logs/server.log.", reasons)
    if name in ("ConnectionError", "Timeout", "TimeoutError", "ServerNotFoundError", "TransportError"):
        return CreatorOSError(SYSTEM, f"Network problem reaching Google: {exc}",
                              "Check your internet connection and try again.")
    return CreatorOSError(SYSTEM, f"Unexpected error: {name}: {exc}",
                          "Check ~/.creatoros/logs/server.log for details.")
