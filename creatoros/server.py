"""CreatorOS MCP server (stdio).

Vertical slice: Connect YouTube -> Discover channel -> Retrieve videos -> Retrieve analytics
-> Analyze performance -> Return an evidence-based recommendation.

All tools are read-only except connect/disconnect (which only touch the local token vault).
Nothing here uploads, edits or deletes anything on YouTube.
"""
from __future__ import annotations

import asyncio
import functools
import json
import logging
import sys
import time
from datetime import date, datetime, timedelta, timezone
from statistics import median
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__, auth, config, intelligence as intel, store
from .analytics_client import YouTubeAnalytics, require, window
from .errors import CONFIRMATION_REQUIRED, INVALID_INPUT, CreatorOSError, from_exception
from .youtube_client import YouTubeData

log = logging.getLogger("creatoros")

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
LOCAL_WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=True)

INSTRUCTIONS = """CreatorOS connects you to the user's own YouTube channel (read-only in this version).
Start with youtube_list_channels; if nothing is connected, call youtube_connect_channel.
For 'how is my channel doing / what should I do', call youtube_analyze_channel_performance first.
Every result is labelled measured / derived / estimated / ai_recommendation - keep those labels
when you answer, quote the evidence, and never present a correlation as a proven cause.
If a tool returns an error, its [category] tells you whether it is authentication, permission,
quota, unsupported_metric, unavailable_data, configuration or system - relay the 'How to fix'."""

mcp = MCPServer(name="creatoros_mcp", title="CreatorOS - YouTube Creator Intelligence",
                instructions=INSTRUCTIONS, version=__version__)

ChannelId = Annotated[str | None, Field(default=None, description="YouTube channel ID (UC...). Omit to use the default connected channel.")]

COUNTRY_TZ = {  # main audience timezone per country (first guess only; user can override)
    "IN": "Asia/Kolkata", "US": "America/New_York", "GB": "Europe/London", "CA": "America/Toronto",
    "AU": "Australia/Sydney", "DE": "Europe/Berlin", "FR": "Europe/Paris", "BR": "America/Sao_Paulo",
    "MX": "America/Mexico_City", "ID": "Asia/Jakarta", "PH": "Asia/Manila", "PK": "Asia/Karachi",
    "BD": "Asia/Dhaka", "NG": "Africa/Lagos", "AE": "Asia/Dubai", "SA": "Asia/Riyadh", "JP": "Asia/Tokyo",
    "KR": "Asia/Seoul", "ES": "Europe/Madrid", "IT": "Europe/Rome", "NL": "Europe/Amsterdam",
    "SG": "Asia/Singapore", "MY": "Asia/Kuala_Lumpur", "ZA": "Africa/Johannesburg", "NP": "Asia/Kathmandu",
    "LK": "Asia/Colombo", "EG": "Africa/Cairo", "TR": "Europe/Istanbul", "VN": "Asia/Ho_Chi_Minh",
}


# ------------------------------------------------------------ plumbing ---
def _audit(tool: str, ok: bool, ms: int, err: dict | None = None) -> None:
    try:
        config.ensure_dirs()
        with open(config.LOG_DIR / "tool_calls.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": store.now(), "tool": tool, "ok": ok, "ms": ms, "error": err}) + "\n")
    except OSError:
        pass


def guarded(fn):
    """Uniform error handling + audit log for every tool."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        t0 = time.monotonic()
        try:
            result = await fn(*args, **kwargs)
            _audit(fn.__name__, True, int((time.monotonic() - t0) * 1000))
            return result
        except ToolError:
            raise
        except Exception as exc:  # noqa: BLE001
            err = from_exception(exc)
            if err.category == "system":
                log.exception("Tool %s failed: %s", fn.__name__, err)
            else:
                log.warning("Tool %s failed: %s", fn.__name__, err)
            _audit(fn.__name__, False, int((time.monotonic() - t0) * 1000), err.to_dict())
            raise ToolError(str(err)) from exc
    return wrapper


def _ctx(channel_id: str | None):
    cid = auth.resolve_channel_id(channel_id)
    return cid, auth.get_credentials(cid)


def _library(cid: str, creds, refresh: bool = False, max_videos: int = 500):
    videos, synced = store.latest_videos(cid)
    if videos and not refresh and store.library_is_fresh(synced):
        return videos, synced, "local cache (synced from YouTube Data API)"
    yd = YouTubeData(creds)
    rec = auth.channel_record(cid)
    ids = yd.upload_ids(rec["uploads_playlist_id"], max_videos)
    videos = yd.videos(ids)
    ts = store.save_videos(cid, videos)
    videos.sort(key=lambda v: v.get("published_at") or "", reverse=True)
    return videos, ts, "YouTube Data API v3 (playlistItems.list + videos.list)"


def _envelope(cid: str, data: dict, sources: list[str], fetched_at: str | None = None,
              limitations: list[str] | None = None) -> dict[str, Any]:
    return {"channel_id": cid, **data,
            "provenance": {"sources": sources, "fetched_at": fetched_at or store.now()},
            "limitations": [x for x in (limitations or []) if x]}


async def _run(fn, *a, **kw):
    return await asyncio.to_thread(fn, *a, **kw)


# ------------------------------------------------------------- connect ---
@mcp.tool(name="youtube_connect_channel", title="Connect a YouTube channel", annotations=LOCAL_WRITE)
@guarded
async def youtube_connect_channel() -> dict[str, Any]:
    """Connect a YouTube channel via Google sign-in (OAuth 2.0, read-only permissions).

    Opens Google's consent screen in a browser on the computer running this server. The user signs in
    and picks the channel (or Brand Account). Tokens are encrypted locally and never returned here.
    Call again to connect additional channels.
    """
    ch = await _run(auth.run_connect_flow)
    return {"connected": True, "channel": {k: ch[k] for k in ("channel_id", "title", "custom_url", "connected_at")},
            "permissions": "read-only (youtube.readonly, yt-analytics.readonly)",
            "next_step": "Call youtube_analyze_channel_performance for a full health check."}


@mcp.tool(name="youtube_list_channels", title="List connected channels", annotations=READ)
@guarded
async def youtube_list_channels() -> dict[str, Any]:
    """List YouTube channels connected to CreatorOS and which one is the default."""
    conns = await _run(auth.list_connections)
    return {"channels": conns, "count": len(conns),
            "hint": None if conns else "No channel connected. Call youtube_connect_channel."}


@mcp.tool(name="youtube_set_default_channel", title="Set default channel", annotations=LOCAL_WRITE)
@guarded
async def youtube_set_default_channel(channel_id: Annotated[str, Field(description="Connected channel ID (UC...)")]) -> dict[str, Any]:
    """Choose which connected channel tools use when channel_id is omitted."""
    await _run(auth.set_default, channel_id)
    return {"default_channel_id": channel_id}


@mcp.tool(name="youtube_disconnect_channel", title="Disconnect a channel", annotations=DESTRUCTIVE)
@guarded
async def youtube_disconnect_channel(
    channel_id: Annotated[str, Field(description="Channel ID to disconnect")],
    confirm: Annotated[bool, Field(description="Must be true. Ask the user to confirm before setting it.")] = False,
) -> dict[str, Any]:
    """Revoke CreatorOS's Google access for a channel and delete its local token. Requires explicit confirmation."""
    if not confirm:
        raise CreatorOSError(CONFIRMATION_REQUIRED,
                             f"Disconnecting {channel_id} revokes Google access and deletes the stored token.",
                             "Ask the user to confirm, then call again with confirm=true.")
    return await _run(auth.disconnect, channel_id)


# ------------------------------------------------------- channel + videos -
@mcp.tool(name="youtube_get_channel_overview", title="Channel overview", annotations=READ)
@guarded
async def youtube_get_channel_overview(channel_id: ChannelId = None) -> dict[str, Any]:
    """Channel profile, public stats, library composition (Shorts vs long-form) and upload cadence."""
    def work():
        cid, creds = _ctx(channel_id)
        ch = YouTubeData(creds).channel()
        store.save_channel(cid, ch)
        videos, synced, src = _library(cid, creds)
        public = [v for v in videos if v.get("privacy_status") == "public"]
        fmt = {f: sum(1 for v in public if v.get("format") == f) for f in ("short", "long_form", "live")}
        dates = sorted((intel._parse_ts(v["published_at"]) for v in public if v.get("published_at")), reverse=True)
        gaps = [(dates[i] - dates[i + 1]).days for i in range(min(10, len(dates) - 1))]
        cadence = {"median_days_between_last_uploads": median(gaps) if gaps else None,
                   "last_upload": dates[0].isoformat() if dates else None,
                   "days_since_last_upload": (datetime.now(timezone.utc) - dates[0]).days if dates else None,
                   "label": "derived"}
        return _envelope(cid, {"channel": ch, "library": {"videos_synced": len(videos), "public": len(public),
                                                          "by_format": fmt, "format_note": videos[0]["format_basis"] if videos else None},
                               "upload_cadence": cadence},
                         ["YouTube Data API v3: channels.list", src], synced)
    return await _run(work)


@mcp.tool(name="youtube_list_videos", title="List channel videos", annotations=READ)
@guarded
async def youtube_list_videos(
    channel_id: ChannelId = None,
    format: Annotated[Literal["all", "short", "long_form", "live"], Field(description="Filter by format")] = "all",
    sort: Annotated[Literal["newest", "oldest", "most_viewed", "least_viewed"], Field(description="Sort order")] = "newest",
    limit: Annotated[int, Field(ge=1, le=100, description="Max videos to return")] = 25,
    offset: Annotated[int, Field(ge=0, description="Pagination offset")] = 0,
    refresh: Annotated[bool, Field(description="Force a fresh sync from YouTube instead of the 6-hour cache")] = False,
) -> dict[str, Any]:
    """List the channel's uploaded videos with lifetime public stats (views, likes, comments)."""
    def work():
        cid, creds = _ctx(channel_id)
        videos, synced, src = _library(cid, creds, refresh=refresh)
        vs = [v for v in videos if format == "all" or v.get("format") == format]
        keyf = {"newest": (lambda v: v.get("published_at") or "", True), "oldest": (lambda v: v.get("published_at") or "", False),
                "most_viewed": (lambda v: v.get("views") or 0, True), "least_viewed": (lambda v: v.get("views") or 0, False)}[sort]
        vs.sort(key=keyf[0], reverse=keyf[1])
        page = vs[offset:offset + limit]
        return _envelope(cid, {"total": len(vs), "count": len(page), "offset": offset,
                               "has_more": offset + limit < len(vs), "next_offset": offset + limit if offset + limit < len(vs) else None,
                               "videos": [intel.slim_video(v) for v in page]}, [src], synced)
    return await _run(work)


@mcp.tool(name="youtube_search_videos", title="Search my videos", annotations=READ)
@guarded
async def youtube_search_videos(
    query: Annotated[str, Field(min_length=2, description="Words to find in titles, tags and descriptions, e.g. 'artificial intelligence'")],
    channel_id: ChannelId = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 15,
) -> dict[str, Any]:
    """Search the connected channel's own video library (keyword match; uses no YouTube quota)."""
    def work():
        cid, creds = _ctx(channel_id)
        videos, synced, src = _library(cid, creds)
        hits = intel.search_library(videos, query, limit)
        return _envelope(cid, {"query": query, "results": hits, "count": len(hits)}, [src], synced,
                         ["Keyword matching on title/tags/description. Transcript and semantic search arrive in Phase 3."])
    return await _run(work)


@mcp.tool(name="youtube_get_video_details", title="Video details", annotations=READ)
@guarded
async def youtube_get_video_details(
    video_id: Annotated[str, Field(min_length=6, description="YouTube video ID, e.g. dQw4w9WgXcQ")],
    channel_id: ChannelId = None,
) -> dict[str, Any]:
    """Full metadata for one video (title, description, tags, duration, format, stats) plus stored stat history."""
    def work():
        cid, creds = _ctx(channel_id)
        vids = YouTubeData(creds).videos([video_id])
        if not vids:
            raise CreatorOSError("unavailable_data", f"Video {video_id} not found or not visible to this channel.",
                                 "Check the ID; private videos of other channels are not accessible.")
        ts = store.save_videos(cid, vids)
        return _envelope(cid, {"video": vids[0], "stat_history": store.video_history(cid, video_id)},
                         ["YouTube Data API v3: videos.list"], ts)
    return await _run(work)


@mcp.tool(name="youtube_get_comments", title="Video comments", annotations=READ)
@guarded
async def youtube_get_comments(
    video_id: Annotated[str, Field(min_length=6, description="YouTube video ID")],
    max_results: Annotated[int, Field(ge=1, le=300)] = 100,
    order: Annotated[Literal["relevance", "time"], Field(description="'relevance' (top) or 'time' (newest)")] = "relevance",
    channel_id: ChannelId = None,
) -> dict[str, Any]:
    """Top-level comments on a video, with quick derived signals (questions, most-liked) for audience analysis."""
    def work():
        cid, creds = _ctx(channel_id)
        cs = YouTubeData(creds).comments(video_id, max_results, order)
        questions = [c for c in cs if "?" in (c["text"] or "")]
        return _envelope(cid, {
            "video_id": video_id, "count": len(cs), "comments": cs,
            "signals": {"label": "derived",
                        "questions_from_viewers": [{"text": c["text"], "likes": c["likes"]} for c in
                                                   sorted(questions, key=lambda c: c["likes"], reverse=True)[:15]],
                        "most_liked": [{"text": c["text"], "likes": c["likes"]} for c in
                                       sorted(cs, key=lambda c: c["likes"], reverse=True)[:5]],
                        "share_of_comments_that_are_questions_pct": round(len(questions) / len(cs) * 100, 1) if cs else 0}},
            ["YouTube Data API v3: commentThreads.list"], None,
            ["Replies are not included. Read-only: this tool never posts or moderates."])
    return await _run(work)


# ------------------------------------------------------------ analytics --
@mcp.tool(name="youtube_get_channel_analytics", title="Channel analytics", annotations=READ)
@guarded
async def youtube_get_channel_analytics(
    days: Annotated[int, Field(ge=7, le=365, description="Window length in days (compared with the previous window of the same length)")] = 28,
    channel_id: ChannelId = None,
) -> dict[str, Any]:
    """Private channel analytics: totals vs previous period, daily trend, traffic sources, countries, subscriber split."""
    def work():
        cid, creds = _ctx(channel_id)
        a = YouTubeAnalytics(creds)
        s, e = window(days)
        ps, pe = window(days, 1)
        cur, prev = a.totals(s, e), a.totals(ps, pe)
        require(cur, "channel analytics")
        reach, reach_note = a.reach_totals(s, e)
        subs, subs_note = a.subscribed_status(s, e)
        data = {"window": {"current": [s, e], "previous": [ps, pe]},
                "comparison": intel.compare_periods(cur, prev),
                "reach": reach or None,
                "daily": a.daily(s, e),
                "traffic_sources": a.traffic_sources(s, e),
                "top_countries": a.countries(s, e),
                "subscriber_vs_non_subscriber": subs or None}
        ts = store.save_analytics(cid, "channel_analytics", s, e, data)
        return _envelope(cid, data, ["YouTube Analytics API v2: reports.query"], ts, [
            f"Data ends {config.ANALYTICS_LAG_DAYS} days ago because YouTube Analytics lags ~48 hours.",
            reach_note and f"Impressions/CTR unavailable: {reach_note}", subs_note])
    return await _run(work)


def _downsample(curve: list[dict], points: int = 20) -> list[dict]:
    if len(curve) <= points:
        return curve
    step = len(curve) / points
    return [curve[int(i * step)] for i in range(points)] + [curve[-1]]


@mcp.tool(name="youtube_get_video_analytics", title="Video analytics", annotations=READ)
@guarded
async def youtube_get_video_analytics(
    video_id: Annotated[str, Field(min_length=6, description="YouTube video ID")],
    days: Annotated[int | None, Field(ge=7, le=3650, description="Window in days. Omit for lifetime (since publish).")] = None,
    channel_id: ChannelId = None,
) -> dict[str, Any]:
    """Private analytics for one video: totals, impressions/CTR (if available), traffic sources,
    audience-retention curve with the biggest drop-off, and YouTube search terms that found it."""
    def work():
        cid, creds = _ctx(channel_id)
        vids = YouTubeData(creds).videos([video_id])
        if not vids:
            raise CreatorOSError("unavailable_data", f"Video {video_id} not found on this channel.", "Check the ID.")
        v = vids[0]
        a = YouTubeAnalytics(creds)
        end = (date.today() - timedelta(days=config.ANALYTICS_LAG_DAYS)).isoformat()
        start = (intel._parse_ts(v["published_at"]).date().isoformat() if days is None
                 else window(days)[0])
        totals = a.totals(start, end, video_id)
        reach, reach_note = a.reach_totals(start, end, video_id)
        curve, ret_note = a.retention(video_id, start, end)
        drop = None
        if len(curve) > 5:
            diffs = [(curve[i]["elapsedVideoTimeRatio"], curve[i - 1]["audienceWatchRatio"] - curve[i]["audienceWatchRatio"])
                     for i in range(2, len(curve))]
            at, size = max(diffs, key=lambda x: x[1])
            secs = round(at * (v["duration_seconds"] or 0))
            drop = {"at_ratio": at, "at_seconds": secs, "drop_in_watch_ratio": round(size, 3), "label": "derived"}
        terms, terms_note = a.search_terms(video_id, start, end)
        data = {"video": intel.slim_video(v), "window": [start, end], "totals": totals or None, "reach": reach or None,
                "traffic_sources": a.traffic_sources(start, end, video_id),
                "retention": {"curve": _downsample(curve), "biggest_drop": drop,
                              "how_to_read": "audienceWatchRatio = share of viewers still watching at that point; "
                                             "relativeRetentionPerformance compares with similar-length YouTube videos (0.5 = median)."},
                "youtube_search_terms": terms}
        ts = store.save_analytics(cid, f"video:{video_id}", start, end, data)
        return _envelope(cid, data, ["YouTube Data API v3: videos.list", "YouTube Analytics API v2: reports.query"], ts,
                         [reach_note and f"Impressions/CTR unavailable: {reach_note}",
                          ret_note and f"Retention unavailable: {ret_note}",
                          terms_note and f"Search terms unavailable: {terms_note}"])
    return await _run(work)


@mcp.tool(name="youtube_compare_videos", title="Compare videos fairly", annotations=READ)
@guarded
async def youtube_compare_videos(
    video_ids: Annotated[list[str], Field(min_length=2, max_length=5, description="2-5 video IDs from this channel")],
    first_days: Annotated[int, Field(ge=1, le=365, description="Compare each video's first N days after publishing")] = 28,
    channel_id: ChannelId = None,
) -> dict[str, Any]:
    """Compare videos on equal footing: each video is measured over its own first N days after publishing."""
    def work():
        cid, creds = _ctx(channel_id)
        meta = {v["video_id"]: v for v in YouTubeData(creds).videos(video_ids)}
        a = YouTubeAnalytics(creds)
        last = date.today() - timedelta(days=config.ANALYTICS_LAG_DAYS)
        rows = []
        for vid in video_ids:
            v = meta.get(vid)
            if not v:
                rows.append({"video_id": vid, "error": "not found on this channel"})
                continue
            pub = intel._parse_ts(v["published_at"]).date()
            end = min(pub + timedelta(days=first_days - 1), last)
            if end < pub:
                rows.append({**intel.slim_video(v), "error": "published too recently for analytics"})
                continue
            t = a.totals(pub.isoformat(), end.isoformat(), vid)
            r, _ = a.reach_totals(pub.isoformat(), end.isoformat(), vid)
            views = t.get("views") or 0
            rows.append({**intel.slim_video(v), "window": [pub.isoformat(), end.isoformat()],
                         "partial_window": (end - pub).days + 1 < first_days,
                         "views": views, "watch_minutes": t.get("estimatedMinutesWatched"),
                         "avg_view_pct": t.get("averageViewPercentage"), "avg_view_duration_s": t.get("averageViewDuration"),
                         "subscribers_gained": t.get("subscribersGained"),
                         "subs_per_1k_views": round((t.get("subscribersGained") or 0) / views * 1000, 2) if views else None,
                         "likes_per_1k_views": round((t.get("likes") or 0) / views * 1000, 2) if views else None,
                         "impressions": r.get("videoThumbnailImpressions"), "ctr_pct": r.get("videoThumbnailImpressionsClickRate")})
        ok = [r for r in rows if "error" not in r]
        leaders = {}
        for m in ("views", "avg_view_pct", "subs_per_1k_views", "ctr_pct"):
            vals = [r for r in ok if r.get(m) is not None]
            if vals:
                b = max(vals, key=lambda r: r[m])
                leaders[m] = {"video_id": b["video_id"], "title": b["title"], "value": b[m]}
        return _envelope(cid, {"method": f"Each video measured over its first {first_days} days (label: measured/derived).",
                               "videos": rows, "leaders": leaders},
                         ["YouTube Analytics API v2: reports.query (filtered per video)"], None,
                         ["Different formats (Short vs long-form) are not directly comparable on retention %."]
                         if len({r.get("format") for r in ok}) > 1 else [])
    return await _run(work)


# ------------------------------------------------------ intelligence -----
@mcp.tool(name="youtube_analyze_channel_performance", title="Analyze channel & recommend", annotations=READ)
@guarded
async def youtube_analyze_channel_performance(
    days: Annotated[int, Field(ge=14, le=180, description="Analysis window in days (compared with the previous window)")] = 28,
    channel_id: ChannelId = None,
) -> dict[str, Any]:
    """End-to-end health check: syncs videos, pulls analytics for this and the previous period, diagnoses each
    video's bottleneck (click / discovery / retention / conversion) against the channel's own same-format
    baseline, finds rising and declining videos, and returns ONE prioritized, evidence-backed recommendation."""
    def work():
        cid, creds = _ctx(channel_id)
        videos, synced, lib_src = _library(cid, creds)
        a = YouTubeAnalytics(creds)
        s, e = window(days)
        ps, pe = window(days, 1)
        cur, prev = a.totals(s, e), a.totals(ps, pe)
        require(cur, "channel analytics")
        per_cur, per_prev = a.per_video(s, e), a.per_video(ps, pe)
        reach_rows, reach_note = a.per_video_reach(s, e)
        traffic, countries = a.traffic_sources(s, e), a.countries(s, e, 5)
        period = intel.compare_periods(cur, prev)
        merged = intel.merge_video_metrics(videos, per_cur, reach_rows)
        diagnoses = intel.diagnose_videos(merged)
        rec = intel.primary_recommendation(diagnoses, period)
        mom = intel.momentum(per_cur, per_prev, videos)
        total_views = sum(t.get("views") or 0 for t in traffic) or 1
        result = {
            "window": {"current": [s, e], "previous": [ps, pe]},
            "headline_metrics": {k: period[k] for k in ("views", "estimatedMinutesWatched", "averageViewPercentage",
                                                         "net_subscribers", "likes", "shares")},
            "traffic_sources": [{"source": t["insightTrafficSourceType"], "views": t["views"],
                                 "share_pct": round(t["views"] / total_views * 100, 1)} for t in traffic[:6]],
            "top_countries": countries,
            "primary_recommendation": rec,
            "video_diagnoses": [{k: d.get(k) for k in ("video_id", "title", "format", "published_at", "views",
                                                         "avg_view_pct", "subs_per_1k_views", "ctr_pct", "bottleneck",
                                                         "stage", "confidence")} | {"evidence": d["evidence"]}
                                for d in diagnoses[:15]],
            "momentum": mom,
            "labels_legend": {"measured": "read from YouTube", "derived": "arithmetic on measured data",
                              "estimated": "pattern inference with a confidence level",
                              "ai_recommendation": "suggested action to test - not a proven cause"},
        }
        ts = store.save_analytics(cid, "channel_performance", s, e, result)
        store.save_recommendation(cid, "channel_performance", {"window": [s, e], "recommendation": rec,
                                                                 "baseline": {"views": cur.get("views"),
                                                                              "avg_view_pct": cur.get("averageViewPercentage")}})
        return _envelope(cid, result, [lib_src, "YouTube Analytics API v2: reports.query"], ts, [
            f"Analytics end {config.ANALYTICS_LAG_DAYS} days ago (YouTube processing lag).",
            reach_note and f"Impressions/CTR per video unavailable ({reach_note}); the 'click' stage could not be "
                           "diagnosed - check YouTube Studio > Analytics > Content for CTR.",
            "Per-video analytics cover up to the 200 most-viewed videos in the window.",
            "Short vs long-form classification uses a duration heuristic (see format_basis on each video)."])
    return await _run(work)


@mcp.tool(name="youtube_recommend_publishing_time", title="Best time to publish", annotations=READ)
@guarded
async def youtube_recommend_publishing_time(
    timezone_name: Annotated[str | None, Field(description="IANA timezone of the main audience, e.g. 'Asia/Kolkata'. "
                                                           "Omit to infer from the top audience country.")] = None,
    format: Annotated[Literal["all", "short", "long_form"], Field(description="Analyze Shorts and long-form separately for best results")] = "all",
    channel_id: ChannelId = None,
) -> dict[str, Any]:
    """Recommend the best weekday and time block to publish, estimated from how your past uploads performed
    relative to neighbouring uploads. Includes confidence, sample sizes and how to validate it."""
    def work():
        from zoneinfo import ZoneInfo
        cid, creds = _ctx(channel_id)
        videos, synced, src = _library(cid, creds)
        tz_src = "provided by user"
        countries = []
        tzn = timezone_name
        if tzn:
            try:
                ZoneInfo(tzn)
            except Exception as exc:
                raise CreatorOSError(INVALID_INPUT, f"Unknown timezone '{tzn}'.", "Use an IANA name like 'Asia/Kolkata'.") from exc
        else:
            s, e = window(90)
            countries = YouTubeAnalytics(creds).countries(s, e, 5)
            top = countries[0]["country"] if countries else None
            tzn = COUNTRY_TZ.get(top, "UTC")
            tz_src = (f"inferred from top audience country {top} (last 90 days)" if top in COUNTRY_TZ
                      else "defaulted to UTC (top country not mapped); pass timezone_name for accuracy")
        res = intel.publishing_cohorts(videos, tzn, None if format == "all" else format)
        res["timezone_source"] = tz_src
        if countries:
            res["audience_countries_90d"] = countries
        if res.get("status") == "ok":
            store.save_recommendation(cid, "publishing_time", {"timezone": tzn, "format": format,
                                                                "recommendation": res["recommendation"]})
        return _envelope(cid, res, [src] + (["YouTube Analytics API v2 (country)"] if countries else []), synced)
    return await _run(work)


@mcp.tool(name="youtube_get_recommendation_history", title="Past recommendations", annotations=READ)
@guarded
async def youtube_get_recommendation_history(channel_id: ChannelId = None,
                                             limit: Annotated[int, Field(ge=1, le=50)] = 10) -> dict[str, Any]:
    """Recommendations CreatorOS made earlier (with their baselines) so you can check them against what happened next."""
    def work():
        cid = auth.resolve_channel_id(channel_id)
        return _envelope(cid, {"recommendations": store.recommendations(cid, limit)}, ["CreatorOS local history"])
    return await _run(work)


# ------------------------------------------------------------ resources --
@mcp.resource("creatoros://channels", name="connected_channels", title="Connected channels", mime_type="application/json")
def res_channels() -> str:
    return json.dumps(auth.list_connections(), indent=2)


@mcp.resource("creatoros://channels/{channel_id}/videos", name="video_library", title="Cached video library",
              mime_type="application/json")
def res_videos(channel_id: str) -> str:
    vids, synced = store.latest_videos(channel_id)
    return json.dumps({"synced_at": synced, "videos": [intel.slim_video(v) for v in vids]}, indent=2)


@mcp.resource("creatoros://channels/{channel_id}/recommendations", name="recommendation_history",
              title="Recommendation history", mime_type="application/json")
def res_recs(channel_id: str) -> str:
    return json.dumps(store.recommendations(channel_id, 50), indent=2)


# -------------------------------------------------------------- prompts --
@mcp.prompt(name="channel_health_assessment", title="Channel health assessment")
def p_health(channel_id: str = "") -> str:
    target = f"channel {channel_id}" if channel_id else "my default channel"
    return (f"Assess the health of {target}. Call youtube_analyze_channel_performance (28 days), then "
            "youtube_get_channel_overview. Report: 1) headline trend in plain English, 2) the main bottleneck "
            "with its evidence, 3) three actions for this week, 4) which videos to replicate. Keep the "
            "measured / estimated / ai_recommendation labels and state the confidence.")


@mcp.prompt(name="weekly_creator_review", title="Weekly creator review")
def p_weekly(channel_id: str = "") -> str:
    return ("Run my weekly YouTube review: youtube_get_channel_analytics with days=7, "
            "youtube_analyze_channel_performance with days=28, and youtube_recommend_publishing_time. "
            "Summarize what changed this week, what is rising or declining, and give a 7-day plan "
            f"with publishing slots. Channel: {channel_id or 'default'}.")


@mcp.prompt(name="video_performance_analysis", title="Video performance analysis")
def p_video(video_id: str) -> str:
    return (f"Analyze video {video_id}: call youtube_get_video_analytics (lifetime) and youtube_get_comments. "
            "Identify where viewers drop off, how people found it, what the comments ask for, and the single "
            "change most likely to improve the next similar video. Label evidence vs hypothesis.")


# ------------------------------------------------------------------ main --
def setup_logging() -> None:
    config.ensure_dirs()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    err = logging.StreamHandler(sys.stderr)  # stdout is reserved for the MCP protocol
    err.setFormatter(fmt)
    fh = logging.FileHandler(config.LOG_DIR / "server.log", encoding="utf-8")
    fh.setFormatter(fmt)
    root.handlers = [err, fh]
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


def main() -> None:
    setup_logging()
    log.info("CreatorOS MCP %s starting (home: %s)", __version__, config.APP_DIR)
    mcp.run("stdio")


if __name__ == "__main__":
    main()
