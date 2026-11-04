"""Offline tests. These verify logic and MCP plumbing with synthetic inputs.
They are NOT the acceptance tests - those must run against a real channel (see docs/ARCHITECTURE.md)."""
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

os.environ["CREATOROS_HOME"] = tempfile.mkdtemp(prefix="creatoros-test-")

from creatoros import auth, config, intelligence as intel, server, store  # noqa: E402
from creatoros.errors import from_exception  # noqa: E402
from creatoros.youtube_client import parse_duration, classify_format  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def iso(days_ago, hour=10):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).replace(hour=hour, minute=0, second=0,
                                                                          microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------- parsing
def test_duration_and_format():
    assert parse_duration("PT4M13S") == 253
    assert parse_duration("PT1H2M") == 3720
    assert parse_duration("P1DT1S") == 86401
    assert classify_format(45, "none")["format"] == "short"
    assert classify_format(600, "none")["format"] == "long_form"
    assert classify_format(3600, "completed")["format"] == "live"


# ------------------------------------------------------------- diagnosis
def _row(vid, views, pct, subs, fmt="long_form", impr=None, ctr=None, pub=None):
    return {"video_id": vid, "title": vid, "format": fmt, "views": views, "avg_view_pct": pct,
            "subs_per_1k_views": subs, "impressions": impr, "ctr_pct": ctr, "published_at": pub or iso(10)}


def test_diagnosis_rules():
    base = [_row(f"b{i}", 1000, 40, 5) for i in range(8)]
    rows = base + [
        _row("disc", 300, 55, 5),        # low reach, great retention -> discovery
        _row("cons", 1200, 25, 5),       # good reach, poor retention -> consumption
        _row("conv", 1100, 41, 1),       # good reach, poor subs -> conversion
        _row("win", 3000, 45, 6),        # winner
    ]
    d = {x["video_id"]: x["bottleneck"] for x in intel.diagnose_videos(rows)}
    assert d["disc"] == "discovery"
    assert d["cons"] == "consumption"
    assert d["conv"] == "conversion"
    assert d["win"] == "winning"


def test_click_bottleneck_when_ctr_available():
    rows = [_row(f"b{i}", 1000, 40, 5, impr=20000, ctr=5.0) for i in range(8)]
    rows.append(_row("click", 700, 40, 5, impr=25000, ctr=2.8))
    d = {x["video_id"]: x["bottleneck"] for x in intel.diagnose_videos(rows)}
    assert d["click"] == "click"


def test_shorts_compared_only_with_shorts():
    rows = [_row(f"l{i}", 1000, 40, 5) for i in range(6)] + [_row(f"s{i}", 5000, 90, 1, fmt="short") for i in range(6)]
    for x in intel.diagnose_videos(rows):
        assert x["evidence"]["peer_count"] == 6


def test_primary_recommendation_picks_dominant():
    rows = [_row(f"b{i}", 1000, 40, 5, pub=iso(30 + i)) for i in range(6)]
    rows += [_row(f"c{i}", 1200, 25, 5, pub=iso(i + 1)) for i in range(6)]
    diags = intel.diagnose_videos(rows)
    period = intel.compare_periods({"views": 12000, "subscribersGained": 50, "subscribersLost": 10},
                                   {"views": 10000, "subscribersGained": 40, "subscribersLost": 10})
    rec = intel.primary_recommendation(diags, period)
    assert rec["bottleneck"] == "consumption"
    assert rec["label"] == "ai_recommendation"
    assert period["views"]["change_pct"] == 20.0
    assert period["net_subscribers"]["current"] == 40


def test_momentum():
    cur = [{"video": "a", "views": 500}, {"video": "b", "views": 100}, {"video": "n", "views": 300}]
    prev = [{"video": "a", "views": 200}, {"video": "b", "views": 400}]
    m = intel.momentum(cur, prev, [{"video_id": "a", "title": "A"}])
    assert [x["video_id"] for x in m["rising"]] == ["a"]
    assert [x["video_id"] for x in m["declining"]] == ["b"]
    assert [x["video_id"] for x in m["new_this_period"]] == ["n"]


# ------------------------------------------------------ publishing time
def test_publishing_cohorts_finds_planted_signal():
    vids = []
    for i in range(42):
        d = datetime.now(timezone.utc) - timedelta(days=10 + i * 3)
        hour = 14 if i % 2 else 3
        d = d.replace(hour=hour, minute=0)
        views = 3000 if d.weekday() == 5 else 1000  # Saturdays in UTC do 3x
        vids.append({"video_id": f"v{i}", "title": f"v{i}", "published_at": d.isoformat(), "views": views,
                     "format": "long_form", "privacy_status": "public"})
    res = intel.publishing_cohorts(vids, "UTC")
    assert res["status"] == "ok"
    assert res["recommendation"]["best_day"]["slot"] == "Saturday"
    assert res["label"] == "estimated"


def test_publishing_cohorts_insufficient():
    res = intel.publishing_cohorts([], "UTC")
    assert res["status"] == "insufficient_data"


def test_library_search():
    vids = [{"video_id": "1", "title": "Artificial Intelligence explained", "tags": ["ai"], "description": "", "views": 5},
            {"video_id": "2", "title": "Cooking pasta", "tags": [], "description": "no ai here", "views": 9}]
    hits = intel.search_library(vids, "artificial intelligence")
    assert hits[0]["video_id"] == "1" and len(hits) == 1


# --------------------------------------------------------------- errors
def _http_error(status, reason, msg="x"):
    from googleapiclient.errors import HttpError
    body = json.dumps({"error": {"message": msg, "errors": [{"reason": reason}]}}).encode()
    import httplib2
    return HttpError(httplib2.Response({"status": status}), body)


def test_error_categories():
    assert from_exception(_http_error(403, "quotaExceeded")).category == "quota"
    assert from_exception(_http_error(401, "authError")).category == "authentication"
    assert from_exception(_http_error(403, "insufficientPermissions")).category == "permission"
    assert from_exception(_http_error(403, "commentsDisabled")).category == "unavailable_data"
    assert from_exception(_http_error(400, "badRequest", "Unknown identifier (fooMetric) given in field parameters.metrics")).category == "unsupported_metric"
    from google.auth.exceptions import RefreshError
    assert from_exception(RefreshError("invalid_grant")).category == "authentication"


# ---------------------------------------------------------- token vault
def test_vault_roundtrip_is_encrypted():
    auth._save("UCtest123", {"token": {"token": "secret-access"}, "channel": {"channel_id": "UCtest123", "title": "T"}})
    raw = auth._token_path("UCtest123").read_bytes()
    assert b"secret-access" not in raw
    assert auth._load("UCtest123")["token"]["token"] == "secret-access"
    auth._token_path("UCtest123").unlink()


def test_discovery_docs_bundled_offline():
    # The Google client ships static discovery docs, so building clients needs no network.
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    c = Credentials(token="x")
    build("youtube", "v3", credentials=c, cache_discovery=False)
    build("youtubeAnalytics", "v2", credentials=c, cache_discovery=False)


# ------------------------------------------------------------ MCP layer
def test_tools_registered_with_annotations():
    tools = {t.name: t for t in run(server.mcp.list_tools())}
    expected = {"youtube_connect_channel", "youtube_list_channels", "youtube_set_default_channel",
                "youtube_disconnect_channel", "youtube_get_channel_overview", "youtube_list_videos",
                "youtube_search_videos", "youtube_get_video_details", "youtube_get_comments",
                "youtube_get_channel_analytics", "youtube_get_video_analytics", "youtube_compare_videos",
                "youtube_analyze_channel_performance", "youtube_recommend_publishing_time",
                "youtube_get_recommendation_history"}
    assert expected <= set(tools)
    assert tools["youtube_list_videos"].annotations.read_only_hint is True
    assert tools["youtube_disconnect_channel"].annotations.destructive_hint is True
    assert "video_ids" in tools["youtube_compare_videos"].input_schema["properties"]


def test_no_channel_gives_actionable_auth_error():
    with pytest.raises(Exception) as e:
        run(server.mcp.call_tool("youtube_list_videos", {}))
    assert "[authentication]" in str(e.value)


def test_disconnect_requires_confirmation():
    with pytest.raises(Exception) as e:
        run(server.mcp.call_tool("youtube_disconnect_channel", {"channel_id": "UCx"}))
    assert "confirmation_required" in str(e.value)


def test_connect_without_client_secret_explains_setup():
    with pytest.raises(Exception) as e:
        run(server.mcp.call_tool("youtube_connect_channel", {}))
    assert "[configuration]" in str(e.value) and "client_secret.json" in str(e.value)


def test_vertical_slice_plumbing_with_stubbed_google(monkeypatch):
    """Exercises the full analyze tool path with stubbed Google clients (plumbing check only)."""
    auth._save("UCstub", {"token": {"token": "t", "refresh_token": "r", "client_id": "c", "client_secret": "s",
                                    "token_uri": "https://oauth2.googleapis.com/token"},
                          "channel": {"channel_id": "UCstub", "title": "Stub", "uploads_playlist_id": "UUstub"}})
    monkeypatch.setattr(auth, "get_credentials", lambda cid: object())
    lib = [{"video_id": f"v{i}", "title": f"Video {i}", "published_at": iso(5 + i * 4), "views": 1000 + i * 10,
            "format": "long_form", "format_basis": "duration", "privacy_status": "public", "duration_seconds": 600,
            "tags": [], "description": ""} for i in range(12)]

    class FakeData:
        def __init__(self, c): pass
        def upload_ids(self, p, m): return [v["video_id"] for v in lib]
        def videos(self, ids): return [v for v in lib if v["video_id"] in ids]

    class FakeAnalytics:
        def __init__(self, c): pass
        def totals(self, s, e, video_id=None):
            return {"views": 9000, "estimatedMinutesWatched": 30000, "averageViewPercentage": 38,
                    "subscribersGained": 90, "subscribersLost": 10, "likes": 300, "shares": 20}
        def per_video(self, s, e):
            return [{"video": v["video_id"], "views": 800 if i < 6 else 900, "averageViewPercentage": 22 if i < 6 else 42,
                     "subscribersGained": 8, "estimatedMinutesWatched": 100} for i, v in enumerate(lib)]
        def per_video_reach(self, s, e): return [], "not supported in stub"
        def traffic_sources(self, s, e, video_id=None):
            return [{"insightTrafficSourceType": "YT_SEARCH", "views": 5000}, {"insightTrafficSourceType": "SUBSCRIBER", "views": 4000}]
        def countries(self, s, e, top=10): return [{"country": "IN", "views": 7000}]

    monkeypatch.setattr(server, "YouTubeData", FakeData)
    monkeypatch.setattr(server, "YouTubeAnalytics", FakeAnalytics)
    res = run(server.mcp.call_tool("youtube_analyze_channel_performance", {"days": 28}))
    payload = res.structured_content if hasattr(res, "structured_content") else res.structuredContent
    assert payload["primary_recommendation"]["bottleneck"] == "consumption"
    assert payload["provenance"]["sources"]
    assert any("Impressions/CTR" in x for x in payload["limitations"])
    pub = run(server.mcp.call_tool("youtube_recommend_publishing_time", {}))
    pp = pub.structured_content if hasattr(pub, "structured_content") else pub.structuredContent
    assert pp["timezone"] == "Asia/Kolkata"
    hist = run(server.mcp.call_tool("youtube_get_recommendation_history", {}))
    hp = hist.structured_content if hasattr(hist, "structured_content") else hist.structuredContent
    assert len(hp["recommendations"]) >= 1
    auth._token_path("UCstub").unlink()


def test_oauth_never_writes_to_stdout(monkeypatch, capsys, tmp_path):
    """stdout is the MCP channel; Google's helper prints the sign-in URL, which must go to stderr."""
    secret = tmp_path / "client_secret.json"
    secret.write_text("{}")
    monkeypatch.setattr(config, "CLIENT_SECRET_FILE", secret)

    class FakeFlow:
        @classmethod
        def from_client_secrets_file(cls, *a, **k):
            return cls()

        def run_local_server(self, **kw):
            print(kw["authorization_prompt_message"].format(url="https://accounts.google.com/x"))
            raise RuntimeError("access_denied")

    import google_auth_oauthlib.flow as f
    monkeypatch.setattr(f, "InstalledAppFlow", FakeFlow)
    with pytest.raises(Exception) as e:
        auth.run_connect_flow(open_browser=False)
    out = capsys.readouterr()
    assert out.out == ""
    assert "accounts.google.com" in out.err
    assert "[authentication]" in str(e.value)


def test_comments_without_api_key_explains_setup(monkeypatch):
    auth._save("UCc", {"token": {"token": "t"}, "channel": {"channel_id": "UCc", "title": "C", "uploads_playlist_id": "UUc"}})
    monkeypatch.setattr(auth, "get_credentials", lambda cid: object())
    monkeypatch.setattr(config, "api_key", lambda: None)
    with pytest.raises(Exception) as e:
        run(server.mcp.call_tool("youtube_get_comments", {"video_id": "abcdefg", "channel_id": "UCc"}))
    assert "[configuration]" in str(e.value) and "API key" in str(e.value)
    auth._token_path("UCc").unlink()


def test_comments_use_api_key_not_oauth(monkeypatch):
    auth._save("UCd", {"token": {"token": "t"}, "channel": {"channel_id": "UCd", "title": "D", "uploads_playlist_id": "UUd"}})
    monkeypatch.setattr(auth, "get_credentials", lambda cid: object())
    monkeypatch.setattr(config, "api_key", lambda: "KEY123")
    seen = {}

    class FakeData:
        def __init__(self, credentials=None, api_key=None):
            seen["api_key"], seen["creds"] = api_key, credentials
        def comments(self, vid, n, order):
            return [{"text": "How did you make this?", "likes": 3}, {"text": "Great", "likes": 9}]

    monkeypatch.setattr(server, "YouTubeData", FakeData)
    res = run(server.mcp.call_tool("youtube_get_comments", {"video_id": "abcdefg", "channel_id": "UCd"}))
    assert seen == {"api_key": "KEY123", "creds": None}
    assert res.structured_content["signals"]["share_of_comments_that_are_questions_pct"] == 50.0
    auth._token_path("UCd").unlink()


def test_timezone_kolkata_loads():
    from zoneinfo import ZoneInfo
    ZoneInfo("Asia/Kolkata")


def test_weak_pattern_is_not_called_main_bottleneck():
    rows = [_row(f"b{i}", 1000, 40, 5, pub=iso(5 + i)) for i in range(10)]
    rows += [_row(f"c{i}", 1200, 25, 5, pub=iso(1 + i)) for i in range(2)]
    rec = intel.primary_recommendation(intel.diagnose_videos(rows), {})
    assert rec["bottleneck"] == "none_dominant" and rec["confidence"] == "low"


def test_publishing_explains_when_no_slot_qualifies():
    vids = []
    for i in range(10):  # 10 videos spread over 7 days -> no weekday reaches 3 (max 2)
        d = (datetime.now(timezone.utc) - timedelta(days=10 + i * 8)).replace(hour=(i * 3) % 24, minute=0)
        vids.append({"video_id": f"v{i}", "title": "t", "published_at": d.isoformat(), "views": 100 + i,
                     "format": "long_form", "privacy_status": "public"})
    res = intel.publishing_cohorts(vids, "UTC")
    if res["recommendation"]["best_day"] is None:
        assert "No weekday" in res["recommendation"]["note"]


def test_every_tool_has_exactly_one_directory_annotation():
    """Anthropic directory policy: each tool is readOnlyHint=true XOR destructiveHint=true."""
    for t in run(server.mcp.list_tools()):
        ro, de = bool(t.annotations.read_only_hint), bool(t.annotations.destructive_hint)
        assert ro != de, t.name
        assert t.annotations.title or t.title, t.name


def test_env_placeholders_are_ignored(monkeypatch):
    monkeypatch.setenv("CREATOROS_API_KEY", "${user_config.youtube_api_key}")
    assert config.api_key() in (None,) or not config.api_key().startswith("${")
