"""Intelligence engine: pure, testable functions with no API calls.

Every output is labelled:
  measured          - read directly from YouTube
  derived           - arithmetic on measured data (ratios, medians, % change)
  estimated         - statistical inference from your history (has a confidence score)
  ai_recommendation - a suggested action; a hypothesis to test, not a proven cause
Correlation is never presented as causation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import median
from zoneinfo import ZoneInfo

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ------------------------------------------------------------ helpers -----
def pct_change(cur, prev) -> float | None:
    if cur is None or prev in (None, 0):
        return None
    return round((cur - prev) / prev * 100, 1)


def _med(values) -> float | None:
    vals = [v for v in values if v is not None]
    return median(vals) if vals else None


def _ratio(a, b) -> float | None:
    if a is None or b in (None, 0):
        return None
    return round(a / b, 2)


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def compare_periods(current: dict, previous: dict) -> dict:
    keys = ["views", "estimatedMinutesWatched", "averageViewDuration", "averageViewPercentage",
            "subscribersGained", "subscribersLost", "likes", "comments", "shares"]
    out = {}
    for k in keys:
        c, p = current.get(k), previous.get(k)
        out[k] = {"current": c, "previous": p, "change_pct": pct_change(c, p), "label": "measured/derived"}
    net_c = (current.get("subscribersGained") or 0) - (current.get("subscribersLost") or 0)
    net_p = (previous.get("subscribersGained") or 0) - (previous.get("subscribersLost") or 0)
    out["net_subscribers"] = {"current": net_c, "previous": net_p, "change_pct": pct_change(net_c, net_p),
                              "label": "derived"}
    return out


# --------------------------------------------------- per-video merge -----
def merge_video_metrics(meta: list[dict], analytics_rows: list[dict], reach_rows: list[dict] | None = None) -> list[dict]:
    """Join library metadata with per-video Analytics rows for the same window."""
    by_id = {v["video_id"]: v for v in meta}
    reach = {r["video"]: r for r in (reach_rows or [])}
    merged = []
    for r in analytics_rows:
        vid = r.get("video")
        m = by_id.get(vid, {})
        rr = reach.get(vid, {})
        views = r.get("views") or 0
        merged.append({
            "video_id": vid,
            "title": m.get("title", "(not in cached library - private/deleted or older than sync limit)"),
            "url": f"https://www.youtube.com/watch?v={vid}",
            "published_at": m.get("published_at"),
            "format": m.get("format", "unknown"),
            "duration_seconds": m.get("duration_seconds"),
            "views": views,
            "watch_minutes": r.get("estimatedMinutesWatched"),
            "avg_view_duration_s": r.get("averageViewDuration"),
            "avg_view_pct": r.get("averageViewPercentage"),
            "subscribers_gained": r.get("subscribersGained"),
            "subs_per_1k_views": round((r.get("subscribersGained") or 0) / views * 1000, 2) if views else None,
            "likes": r.get("likes"),
            "comments": r.get("comments"),
            "shares": r.get("shares"),
            "impressions": rr.get("videoThumbnailImpressions"),
            "ctr_pct": rr.get("videoThumbnailImpressionsClickRate"),
        })
    return merged


# --------------------------------------------------- bottleneck engine ---
PLAYBOOK = {
    "click": {
        "stage": "Click (packaging)",
        "meaning": "YouTube is showing the thumbnail, but fewer people than usual click it.",
        "actions": [
            "Rewrite the title so the viewer benefit is clear in the first 40 characters.",
            "Redesign the thumbnail: one subject, max 3-4 words, high contrast, readable on a phone.",
            "Use YouTube Studio 'Test & Compare' to test up to 3 thumbnails/titles (native A/B test).",
        ],
    },
    "discovery": {
        "stage": "Discovery",
        "meaning": "People who watch it stay longer than usual, but it reached fewer people than your typical video.",
        "actions": [
            "The content works; improve reach: re-package title/thumbnail around a clearer search or browse intent.",
            "Link to it from end screens and pinned comments of your best-performing videos.",
            "Add it to a relevant playlist and consider a Short that teases it.",
        ],
    },
    "consumption": {
        "stage": "Consumption (retention)",
        "meaning": "It attracts viewers, but they leave earlier than on your typical video.",
        "actions": [
            "Check the retention curve for the first big drop; tighten the first 30 seconds.",
            "Make sure the opening delivers the exact promise of the title and thumbnail (expectation match).",
            "Cut long intros, logos and 'before we start' sections.",
        ],
    },
    "conversion": {
        "stage": "Conversion (subscribers)",
        "meaning": "Plenty of views, but fewer subscribers per 1,000 views than your typical video.",
        "actions": [
            "Add a specific subscribe reason right after the main value moment, not at the start.",
            "Connect the video to a series or playlist so viewers see a reason to come back.",
            "Check whether the topic matches what the channel is known for (positioning).",
        ],
    },
    "packaging_and_content": {
        "stage": "Discovery + Consumption",
        "meaning": "Below your usual reach AND below your usual retention.",
        "actions": [
            "Treat as a topic-fit signal: compare against your winning topics before making similar videos.",
            "If the topic matters, remake it with a sharper angle rather than re-promoting it.",
        ],
    },
    "winning": {
        "stage": "All stages healthy",
        "meaning": "Above your typical reach with healthy retention.",
        "actions": [
            "Make a follow-up or part 2 on the same topic within 2 weeks.",
            "Reuse its title/thumbnail structure as a template.",
            "Cut 2-3 Shorts from its strongest moments.",
        ],
    },
    "healthy": {"stage": "No clear bottleneck", "meaning": "Performing within your normal range.", "actions": []},
}


def _confidence_from_views(views: int | None, peers: int) -> str:
    if peers < 5 or not views or views < 200:
        return "low"
    if views < 2000 or peers < 10:
        return "medium"
    return "high"


def diagnose_videos(rows: list[dict]) -> list[dict]:
    """Classify each video's bottleneck relative to its OWN format peers (Shorts vs Shorts, long vs long)."""
    by_fmt: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_fmt[r.get("format", "unknown")].append(r)
    out = []
    for fmt, group in by_fmt.items():
        base = {
            "views": _med(r["views"] for r in group),
            "avg_view_pct": _med(r.get("avg_view_pct") for r in group),
            "subs_per_1k_views": _med(r.get("subs_per_1k_views") for r in group),
            "impressions": _med(r.get("impressions") for r in group),
            "ctr_pct": _med(r.get("ctr_pct") for r in group),
        }
        for r in group:
            vr = _ratio(r["views"], base["views"])
            rr = _ratio(r.get("avg_view_pct"), base["avg_view_pct"])
            cr = _ratio(r.get("subs_per_1k_views"), base["subs_per_1k_views"])
            ir = _ratio(r.get("impressions"), base["impressions"])
            ctr = _ratio(r.get("ctr_pct"), base["ctr_pct"])
            b = "healthy"
            if ir is not None and ctr is not None and ir >= 0.8 and ctr < 0.8:
                b = "click"
            elif vr is not None and rr is not None and vr < 0.6 and rr >= 1.0:
                b = "discovery"
            elif vr is not None and rr is not None and vr < 0.6 and rr < 0.85:
                b = "packaging_and_content"
            elif vr is not None and rr is not None and vr >= 0.8 and rr < 0.8:
                b = "consumption"
            elif vr is not None and cr is not None and vr >= 0.8 and cr < 0.6 and (base["subs_per_1k_views"] or 0) > 0:
                b = "conversion"
            elif vr is not None and rr is not None and vr >= 1.5 and rr >= 0.95:
                b = "winning"
            evidence = {
                "views_vs_format_median": vr,
                "retention_vs_format_median": rr,
                "subs_per_1k_vs_format_median": cr,
                "impressions_vs_format_median": ir,
                "ctr_vs_format_median": ctr,
                "format_baseline": base,
                "peer_count": len(group),
            }
            out.append({**r, "bottleneck": b, "stage": PLAYBOOK[b]["stage"], "meaning": PLAYBOOK[b]["meaning"],
                        "evidence": evidence, "label": "estimated",
                        "confidence": _confidence_from_views(r["views"], len(group))})
    out.sort(key=lambda x: x["views"] or 0, reverse=True)
    return out


def momentum(current_rows: list[dict], previous_rows: list[dict], meta: list[dict], min_views: int = 50) -> dict:
    prev = {r["video"]: r.get("views") or 0 for r in previous_rows}
    titles = {v["video_id"]: v.get("title") for v in meta}
    rising, declining, new = [], [], []
    for r in current_rows:
        vid, cur = r["video"], r.get("views") or 0
        p = prev.get(vid, 0)
        item = {"video_id": vid, "title": titles.get(vid), "views_current": cur, "views_previous": p,
                "change_pct": pct_change(cur, p)}
        if p == 0:
            if cur >= min_views:
                new.append(item)
        elif cur >= min_views and cur >= 1.3 * p:
            rising.append(item)
        elif p >= min_views and cur <= 0.6 * p:
            declining.append(item)
    for r in previous_rows:  # dropped out of the current top list entirely
        vid = r["video"]
        if vid not in {c["video"] for c in current_rows} and (r.get("views") or 0) >= min_views * 2:
            declining.append({"video_id": vid, "title": titles.get(vid), "views_current": None,
                              "views_previous": r.get("views"), "change_pct": None,
                              "note": "not in current top-200 list"})
    key = lambda x: abs(x["change_pct"] or 0)  # noqa: E731
    return {"rising": sorted(rising, key=key, reverse=True)[:10],
            "declining": sorted(declining, key=key, reverse=True)[:10],
            "new_this_period": sorted(new, key=lambda x: x["views_current"], reverse=True)[:10],
            "label": "derived", "rule": "rising >= +30% vs previous window; declining <= -40%; min 50 views"}


def primary_recommendation(diagnoses: list[dict], period: dict, recent_n: int = 12) -> dict:
    """Pick the channel's main bottleneck from its most recent videos and turn it into actions."""
    recent = sorted([d for d in diagnoses if d.get("published_at")], key=lambda d: d["published_at"], reverse=True)[:recent_n]
    pool = recent or diagnoses[:recent_n]
    counts = Counter(d["bottleneck"] for d in pool if d["bottleneck"] not in ("healthy", "winning"))
    winners = [d for d in pool if d["bottleneck"] == "winning"]
    trend_notes = []
    v = period.get("views", {}).get("change_pct")
    if v is not None:
        trend_notes.append(f"Views {'+' if v >= 0 else ''}{v}% vs the previous period.")
    ns = period.get("net_subscribers", {})
    if ns.get("current") is not None:
        trend_notes.append(f"Net subscribers this period: {ns['current']} (previous: {ns.get('previous')}).")
    if not counts:
        return {
            "label": "ai_recommendation", "bottleneck": "none_dominant",
            "headline": "No single dominant bottleneck in your recent videos.",
            "actions": (PLAYBOOK["winning"]["actions"] if winners else
                        ["Keep a consistent schedule and collect 4-6 more uploads so patterns become measurable."]),
            "evidence": trend_notes + [f"Reviewed {len(pool)} recent videos with analytics in this window."],
            "examples": [{"video_id": w["video_id"], "title": w["title"]} for w in winners[:3]],
            "confidence": "low" if len(pool) < 6 else "medium",
        }
    top, n = counts.most_common(1)[0]
    share = n / max(len(pool), 1)
    examples = [d for d in pool if d["bottleneck"] == top][:3]
    confidence = "high" if share >= 0.5 and len(pool) >= 8 else "medium" if share >= 0.3 and len(pool) >= 5 else "low"
    return {
        "label": "ai_recommendation",
        "bottleneck": top,
        "stage": PLAYBOOK[top]["stage"],
        "headline": f"Main bottleneck: {PLAYBOOK[top]['stage']} - {n} of your last {len(pool)} videos show this pattern.",
        "meaning": PLAYBOOK[top]["meaning"],
        "actions": PLAYBOOK[top]["actions"],
        "evidence": trend_notes + [
            f"{n}/{len(pool)} recent videos classified as '{top}' (compared with your own same-format median)."],
        "examples": [{"video_id": e["video_id"], "title": e["title"], "evidence": e["evidence"]} for e in examples],
        "replicate_these": [{"video_id": w["video_id"], "title": w["title"]} for w in winners[:3]],
        "confidence": confidence,
        "caveat": "Pattern-based hypothesis from your own data; test the change on your next 2-3 uploads and compare.",
    }


# --------------------------------------------- publishing-time engine ----
def publishing_cohorts(videos: list[dict], tz_name: str = "UTC", fmt: str | None = None,
                       min_age_days: int = 7, k: int = 10, block_hours: int = 3) -> dict:
    """Estimate the best publishing day/time from YOUR historical cohorts.

    YouTube's Studio 'when your viewers are on YouTube' heatmap is NOT available
    through the public API, so we infer from outcomes: each video's lifetime views
    are divided by the median of its k nearest same-format neighbours by publish date
    (controls for channel growth over time and video age). We then compare these
    performance indices by weekday and time block in the audience time zone.
    """
    tz = ZoneInfo(tz_name)
    now = datetime.now(timezone.utc)
    pool = [v for v in videos
            if v.get("published_at") and v.get("views") is not None and v.get("privacy_status", "public") == "public"
            and (fmt is None or v.get("format") == fmt)
            and (now - _parse_ts(v["published_at"])).days >= min_age_days]
    pool.sort(key=lambda v: v["published_at"])
    result = {"label": "estimated", "timezone": tz_name, "format": fmt or "all", "videos_analyzed": len(pool),
              "method": ("Performance index = video views / median views of its nearest same-format videos by "
                         "publish date; grouped by weekday and time block in the chosen timezone."),
              "limitation": ("YouTube's audience-online heatmap is not exposed by the public API. "
                             "This is inferred from outcomes of your past uploads, not from live audience presence.")}
    if len(pool) < 8:
        return {**result, "status": "insufficient_data",
                "message": f"Only {len(pool)} eligible videos (need 8+ older than {min_age_days} days).",
                "suggestion": "Publish on 2-3 different days/times over the next month so the engine can compare."}
    index = []
    for i, v in enumerate(pool):
        same = [w for w in pool if w is not v and w.get("format") == v.get("format")]
        same.sort(key=lambda w: abs((_parse_ts(w["published_at"]) - _parse_ts(v["published_at"])).total_seconds()))
        neigh = [w["views"] for w in same[:k]]
        base = median(neigh) if neigh else None
        if not base:
            continue
        local = _parse_ts(v["published_at"]).astimezone(tz)
        index.append({"video_id": v["video_id"], "title": v.get("title"), "weekday": WEEKDAYS[local.weekday()],
                      "block_start": (local.hour // block_hours) * block_hours,
                      "perf_index": v["views"] / base})
    overall = median(i["perf_index"] for i in index)

    def summarize(key):
        groups = defaultdict(list)
        for i in index:
            groups[i[key]].append(i["perf_index"])
        rows = [{"slot": g, "videos": len(vals), "median_perf_index": round(median(vals), 2),
                 "lift_vs_typical_pct": round((median(vals) / overall - 1) * 100, 1)} for g, vals in groups.items()]
        return sorted(rows, key=lambda r: r["median_perf_index"], reverse=True)

    days, blocks = summarize("weekday"), summarize("block_start")
    for b in blocks:
        b["slot"] = f"{b['slot']:02d}:00-{(b['slot'] + block_hours) % 24:02d}:00"

    def pick(rows):
        eligible = [r for r in rows if r["videos"] >= 3]
        if not eligible:
            return None, "low"
        best = eligible[0]
        lift = best["lift_vs_typical_pct"]
        n = best["videos"]
        conf = "high" if n >= 6 and len(index) >= 30 and lift >= 25 else "medium" if n >= 4 and lift >= 15 else "low"
        return best, conf

    best_day, day_conf = pick(days)
    best_block, block_conf = pick(blocks)
    habit_day = Counter(i["weekday"] for i in index).most_common(1)[0]
    habit_block = Counter(i["block_start"] for i in index).most_common(1)[0]
    untested_days = [d for d in WEEKDAYS if d not in {r["slot"] for r in days if r["videos"] >= 3}]
    rec = {
        "label": "ai_recommendation",
        "best_day": best_day, "best_day_confidence": day_conf,
        "best_time_block": best_block, "best_time_block_confidence": block_conf,
        "your_current_habit": {"most_common_day": habit_day[0], "videos": habit_day[1],
                               "most_common_block_start_hour": habit_block[0], "videos_in_block": habit_block[1],
                               "label": "measured"},
        "untested_or_undersampled_days": untested_days,
        "how_to_validate": ("Publish the next 4 comparable videos alternating the recommended slot and your usual "
                            "slot, then call youtube_recommend_publishing_time again to compare."),
    }
    if best_day and best_day["lift_vs_typical_pct"] < 10:
        rec["note"] = "Differences between days are small (<10%); timing is probably not your main growth lever."
    return {**result, "status": "ok", "by_weekday": days, "by_time_block": blocks, "recommendation": rec}


# --------------------------------------------------- local search --------
def search_library(videos: list[dict], query: str, limit: int = 20) -> list[dict]:
    """Keyword relevance over title/tags/description. Semantic (vector) search arrives in Phase 3."""
    terms = [t for t in query.lower().split() if len(t) > 1]
    scored = []
    for v in videos:
        title = (v.get("title") or "").lower()
        tags = " ".join(v.get("tags") or []).lower()
        desc = (v.get("description") or "").lower()
        score = sum(3 * title.count(t) + 2 * tags.count(t) + min(desc.count(t), 3) for t in terms)
        if query.lower() in title:
            score += 5
        if score:
            scored.append((score, v))
    scored.sort(key=lambda x: (x[0], x[1].get("views") or 0), reverse=True)
    return [{**slim_video(v), "match_score": s} for s, v in scored[:limit]]


def slim_video(v: dict) -> dict:
    keep = ("video_id", "url", "title", "published_at", "format", "duration_seconds", "views", "likes",
            "comments", "privacy_status")
    return {k: v.get(k) for k in keep}
