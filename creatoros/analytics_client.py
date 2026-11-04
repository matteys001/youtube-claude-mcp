"""YouTube Analytics API v2 wrapper (authorized channel's own data only)."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from googleapiclient.discovery import build

from . import config
from .errors import UNSUPPORTED_METRIC, CreatorOSError, from_exception

log = logging.getLogger("creatoros.analytics")

CORE_METRICS = ("views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
                "subscribersGained,subscribersLost,likes,comments,shares")
VIDEO_METRICS = ("views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
                 "subscribersGained,likes,comments,shares")
REACH_METRICS = "videoThumbnailImpressions,videoThumbnailImpressionsClickRate"


def window(days: int, offset_periods: int = 0) -> tuple[str, str]:
    """Date window that ends ANALYTICS_LAG_DAYS ago (YouTube data lags ~48h)."""
    end = date.today() - timedelta(days=config.ANALYTICS_LAG_DAYS) - timedelta(days=days * offset_periods)
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


class YouTubeAnalytics:
    def __init__(self, credentials):
        self.api = build("youtubeAnalytics", "v2", credentials=credentials, cache_discovery=False)

    def query(self, start: str, end: str, metrics: str, dimensions: str | None = None,
              filters: str | None = None, sort: str | None = None, max_results: int | None = None) -> list[dict]:
        kw = dict(ids="channel==MINE", startDate=start, endDate=end, metrics=metrics)
        if dimensions:
            kw["dimensions"] = dimensions
        if filters:
            kw["filters"] = filters
        if sort:
            kw["sort"] = sort
        if max_results:
            kw["maxResults"] = max_results
        resp = self.api.reports().query(**kw).execute()
        cols = [h["name"] for h in resp.get("columnHeaders", [])]
        return [dict(zip(cols, row)) for row in resp.get("rows", []) or []]

    def optional_query(self, *args, **kwargs) -> tuple[list[dict], str | None]:
        """Run a query that may be unsupported for this channel/report; return (rows, limitation_note)."""
        try:
            return self.query(*args, **kwargs), None
        except Exception as exc:  # noqa: BLE001
            err = from_exception(exc)
            if err.category in (UNSUPPORTED_METRIC, "system", "permission"):
                log.info("Optional analytics query unavailable: %s", err)
                return [], err.message
            raise err

    # --------------------------------------------------------- reports ---
    def totals(self, start: str, end: str, video_id: str | None = None) -> dict:
        rows = self.query(start, end, CORE_METRICS, filters=f"video=={video_id}" if video_id else None)
        return rows[0] if rows else {}

    def reach_totals(self, start: str, end: str, video_id: str | None = None) -> tuple[dict, str | None]:
        rows, note = self.optional_query(start, end, REACH_METRICS,
                                         filters=f"video=={video_id}" if video_id else None)
        return (rows[0] if rows else {}), note

    def daily(self, start: str, end: str) -> list[dict]:
        return self.query(start, end, "views,estimatedMinutesWatched,subscribersGained,subscribersLost",
                          dimensions="day", sort="day")

    def per_video(self, start: str, end: str, max_results: int = 200) -> list[dict]:
        return self.query(start, end, VIDEO_METRICS, dimensions="video", sort="-views",
                          max_results=min(max_results, 200))

    def per_video_reach(self, start: str, end: str, max_results: int = 200) -> tuple[list[dict], str | None]:
        return self.optional_query(start, end, REACH_METRICS, dimensions="video",
                                   sort="-videoThumbnailImpressions", max_results=min(max_results, 200))

    def traffic_sources(self, start: str, end: str, video_id: str | None = None) -> list[dict]:
        return self.query(start, end, "views,estimatedMinutesWatched", dimensions="insightTrafficSourceType",
                          filters=f"video=={video_id}" if video_id else None, sort="-views")

    def countries(self, start: str, end: str, top: int = 10) -> list[dict]:
        return self.query(start, end, "views,estimatedMinutesWatched", dimensions="country",
                          sort="-views", max_results=top)

    def subscribed_status(self, start: str, end: str) -> tuple[list[dict], str | None]:
        return self.optional_query(start, end, "views,averageViewDuration", dimensions="subscribedStatus")

    def retention(self, video_id: str, start: str, end: str) -> tuple[list[dict], str | None]:
        return self.optional_query(start, end, "audienceWatchRatio,relativeRetentionPerformance",
                                   dimensions="elapsedVideoTimeRatio", filters=f"video=={video_id}")

    def search_terms(self, video_id: str, start: str, end: str, top: int = 15) -> tuple[list[dict], str | None]:
        return self.optional_query(start, end, "views", dimensions="insightTrafficSourceDetail",
                                   filters=f"video=={video_id};insightTrafficSourceType==YT_SEARCH",
                                   sort="-views", max_results=top)


def require(value, what: str):
    if value in (None, {}, []):
        raise CreatorOSError("unavailable_data", f"YouTube returned no {what} for this period.",
                             "The channel may be new, private, or have no activity in this window; try a longer period.")
    return value
