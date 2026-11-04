"""YouTube Data API v3 wrapper (read-only).

Quota-conscious by design:
- Uploads are listed via playlistItems.list (1 unit/page) instead of search.list (100 units).
- Video details are fetched in batches of 50 (1 unit/batch).
- Searching your own library is done locally on the cached library (0 units).
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from googleapiclient.discovery import build

from . import config

_DUR = re.compile(r"P(?:(?P<d>\d+)D)?(?:T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?)?")


def parse_duration(iso: str | None) -> int:
    """ISO-8601 duration (e.g. PT4M13S) -> seconds."""
    if not iso:
        return 0
    m = _DUR.fullmatch(iso)
    if not m:
        return 0
    g = {k: int(v) if v else 0 for k, v in m.groupdict().items()}
    return g["d"] * 86400 + g["h"] * 3600 + g["m"] * 60 + g["s"]


def classify_format(duration_seconds: int, live_status: str | None) -> dict:
    if live_status in ("live", "upcoming") or live_status == "completed":
        return {"format": "live", "format_basis": "Data API liveBroadcastContent/liveStreamingDetails"}
    if 0 < duration_seconds <= config.SHORTS_MAX_SECONDS:
        return {"format": "short",
                "format_basis": f"heuristic: duration <= {config.SHORTS_MAX_SECONDS}s (the Data API has no explicit Shorts flag)"}
    return {"format": "long_form", "format_basis": "duration"}


def _chunks(seq: list, n: int) -> Iterable[list]:
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _int(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


class YouTubeData:
    def __init__(self, credentials=None, api_key: str | None = None):
        if api_key:
            self.yt = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
        else:
            self.yt = build("youtube", "v3", credentials=credentials, cache_discovery=False)

    # ---------------------------------------------------------- channel --
    def channel(self) -> dict:
        resp = self.yt.channels().list(part="snippet,statistics,contentDetails,brandingSettings", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            return {}
        c = items[0]
        st = c.get("statistics", {})
        return {
            "channel_id": c["id"],
            "title": c["snippet"].get("title"),
            "description": (c["snippet"].get("description") or "")[:1000],
            "custom_url": c["snippet"].get("customUrl"),
            "country": c["snippet"].get("country"),
            "created_at": c["snippet"].get("publishedAt"),
            "thumbnail": (c["snippet"].get("thumbnails", {}).get("high") or {}).get("url"),
            "subscribers": None if st.get("hiddenSubscriberCount") else _int(st.get("subscriberCount")),
            "subscribers_note": "YouTube rounds public subscriber counts to 3 significant figures",
            "total_views": _int(st.get("viewCount")),
            "video_count": _int(st.get("videoCount")),
            "uploads_playlist_id": c["contentDetails"]["relatedPlaylists"]["uploads"],
            "keywords": (c.get("brandingSettings", {}).get("channel", {}) or {}).get("keywords"),
            "url": f"https://www.youtube.com/channel/{c['id']}",
        }

    # ----------------------------------------------------------- videos --
    def upload_ids(self, uploads_playlist_id: str, max_videos: int = 500) -> list[str]:
        ids: list[str] = []
        token = None
        while len(ids) < max_videos:
            resp = self.yt.playlistItems().list(
                part="contentDetails", playlistId=uploads_playlist_id, maxResults=50, pageToken=token).execute()
            ids += [i["contentDetails"]["videoId"] for i in resp.get("items", [])]
            token = resp.get("nextPageToken")
            if not token:
                break
        return ids[:max_videos]

    def videos(self, video_ids: list[str]) -> list[dict]:
        out: list[dict] = []
        for batch in _chunks(list(dict.fromkeys(video_ids)), 50):
            resp = self.yt.videos().list(
                part="snippet,contentDetails,statistics,status,liveStreamingDetails", id=",".join(batch),
                maxResults=50).execute()
            out += [self._normalize(v) for v in resp.get("items", [])]
        return out

    @staticmethod
    def _normalize(v: dict) -> dict:
        sn, cd, st, status = v.get("snippet", {}), v.get("contentDetails", {}), v.get("statistics", {}), v.get("status", {})
        dur = parse_duration(cd.get("duration"))
        live = sn.get("liveBroadcastContent")
        if live == "none" and v.get("liveStreamingDetails"):
            live = "completed"
        thumbs = sn.get("thumbnails", {})
        thumb = (thumbs.get("maxres") or thumbs.get("high") or thumbs.get("default") or {}).get("url")
        return {
            "video_id": v["id"],
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "title": sn.get("title"),
            "description": sn.get("description") or "",
            "published_at": sn.get("publishedAt"),
            "duration_seconds": dur,
            **classify_format(dur, live),
            "category_id": sn.get("categoryId"),
            "tags": sn.get("tags") or [],
            "default_language": sn.get("defaultLanguage") or sn.get("defaultAudioLanguage"),
            "thumbnail": thumb,
            "privacy_status": status.get("privacyStatus"),
            "made_for_kids": status.get("madeForKids"),
            "has_captions": cd.get("caption") == "true",
            "views": _int(st.get("viewCount")),
            "likes": _int(st.get("likeCount")),
            "comments": _int(st.get("commentCount")),
        }

    # --------------------------------------------------------- comments --
    def comments(self, video_id: str, max_results: int = 50, order: str = "relevance") -> list[dict]:
        out: list[dict] = []
        token = None
        while len(out) < max_results:
            resp = self.yt.commentThreads().list(
                part="snippet", videoId=video_id, maxResults=min(100, max_results - len(out)),
                order=order, textFormat="plainText", pageToken=token).execute()
            for t in resp.get("items", []):
                top = t["snippet"]["topLevelComment"]["snippet"]
                out.append({
                    "comment_id": t["id"],
                    "author": top.get("authorDisplayName"),
                    "text": top.get("textDisplay"),
                    "likes": top.get("likeCount", 0),
                    "published_at": top.get("publishedAt"),
                    "reply_count": t["snippet"].get("totalReplyCount", 0),
                    "creator_has_replied": None,  # requires replies fetch; Phase 5
                })
            token = resp.get("nextPageToken")
            if not token:
                break
        return out
