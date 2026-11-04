"""Local persistence (SQLite).

Append-only snapshots: analytics are never overwritten, so history and
'what changed since last time' are always available. Every row carries
fetched_at + source for provenance. Phase 6 swaps this for PostgreSQL/pgvector
behind the same functions.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS video_snapshot (
  channel_id TEXT NOT NULL, video_id TEXT NOT NULL, fetched_at TEXT NOT NULL,
  source TEXT NOT NULL, data TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_video ON video_snapshot(channel_id, video_id, fetched_at);
CREATE TABLE IF NOT EXISTS channel_snapshot (
  channel_id TEXT NOT NULL, fetched_at TEXT NOT NULL, source TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS analytics_snapshot (
  channel_id TEXT NOT NULL, report TEXT NOT NULL, start_date TEXT, end_date TEXT,
  fetched_at TEXT NOT NULL, source TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recommendation (
  channel_id TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sync_state (
  channel_id TEXT NOT NULL, item TEXT NOT NULL, synced_at TEXT NOT NULL, PRIMARY KEY (channel_id, item));
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def db():
    config.ensure_dirs()
    con = sqlite3.connect(config.DB_PATH)
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def save_videos(channel_id: str, videos: list[dict]) -> str:
    ts = now()
    with db() as con:
        con.executemany(
            "INSERT INTO video_snapshot VALUES (?,?,?,?,?)",
            [(channel_id, v["video_id"], ts, "youtube.data.v3:videos.list", json.dumps(v)) for v in videos])
        con.execute("INSERT OR REPLACE INTO sync_state VALUES (?,?,?)", (channel_id, "library", ts))
    return ts


def latest_videos(channel_id: str) -> tuple[list[dict], str | None]:
    with db() as con:
        rows = con.execute("""
          SELECT v.data FROM video_snapshot v
          JOIN (SELECT video_id, MAX(fetched_at) m FROM video_snapshot WHERE channel_id=? GROUP BY video_id) l
            ON v.video_id=l.video_id AND v.fetched_at=l.m
          WHERE v.channel_id=?""", (channel_id, channel_id)).fetchall()
        synced = con.execute("SELECT synced_at FROM sync_state WHERE channel_id=? AND item='library'",
                             (channel_id,)).fetchone()
    vids = [json.loads(r[0]) for r in rows]
    vids.sort(key=lambda v: v.get("published_at") or "", reverse=True)
    return vids, (synced[0] if synced else None)


def library_is_fresh(synced_at: str | None) -> bool:
    if not synced_at:
        return False
    return datetime.fromisoformat(synced_at) > datetime.now(timezone.utc) - timedelta(hours=config.LIBRARY_TTL_HOURS)


def save_channel(channel_id: str, data: dict) -> str:
    ts = now()
    with db() as con:
        con.execute("INSERT INTO channel_snapshot VALUES (?,?,?,?)",
                    (channel_id, ts, "youtube.data.v3:channels.list", json.dumps(data)))
    return ts


def save_analytics(channel_id: str, report: str, start: str | None, end: str | None, data) -> str:
    ts = now()
    with db() as con:
        con.execute("INSERT INTO analytics_snapshot VALUES (?,?,?,?,?,?,?)",
                    (channel_id, report, start, end, ts, "youtubeAnalytics.v2:reports.query", json.dumps(data)))
    return ts


def save_recommendation(channel_id: str, kind: str, data: dict) -> str:
    ts = now()
    with db() as con:
        con.execute("INSERT INTO recommendation VALUES (?,?,?,?)", (channel_id, kind, ts, json.dumps(data)))
    return ts


def recommendations(channel_id: str, limit: int = 20) -> list[dict]:
    with db() as con:
        rows = con.execute("SELECT kind, created_at, data FROM recommendation WHERE channel_id=? "
                           "ORDER BY created_at DESC LIMIT ?", (channel_id, limit)).fetchall()
    return [{"kind": k, "created_at": c, **json.loads(d)} for k, c, d in rows]


def video_history(channel_id: str, video_id: str) -> list[dict]:
    with db() as con:
        rows = con.execute("SELECT fetched_at, data FROM video_snapshot WHERE channel_id=? AND video_id=? "
                           "ORDER BY fetched_at", (channel_id, video_id)).fetchall()
    out = []
    for ts, d in rows:
        v = json.loads(d)
        out.append({"fetched_at": ts, "views": v.get("views"), "likes": v.get("likes"), "comments": v.get("comments")})
    return out
