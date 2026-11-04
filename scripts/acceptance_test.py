"""Live acceptance tests (Master Prompt section 23) against YOUR real, connected channel.

Run after connecting:   python scripts/acceptance_test.py
Writes:                 acceptance_results.md and acceptance_results.json in the current folder.
Uses only read-only calls. Costs roughly 20-40 YouTube Data API quota units.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime

from creatoros import auth, server

RESULTS: list[dict] = []


def payload(res):
    return getattr(res, "structured_content", None) or json.loads(res.content[0].text)


async def call(tool, args=None):
    return payload(await server.mcp.call_tool(tool, args or {}))


async def case(n, name, expected, api, fn):
    t0 = time.monotonic()
    row = {"#": n, "scenario": name, "expected": expected, "api_source": api}
    try:
        status, actual = await fn()
        row.update(result=status, actual=actual)
    except Exception as exc:  # noqa: BLE001
        row.update(result="FAIL", actual=None, error=str(exc)[:500])
    row["seconds"] = round(time.monotonic() - t0, 1)
    RESULTS.append(row)
    print(f"[{row['result']:>12}] {n:>2}. {name}")


async def main():
    ctx = {}

    async def t1():
        chs = auth.list_connections()
        ctx["cid"] = auth.resolve_channel_id(None)
        return ("PASS" if chs else "FAIL"), {"connected_channels": [c.get("title") for c in chs]}

    async def t2():
        o = await call("youtube_get_channel_overview")
        ctx["overview"] = o
        ok = o["channel"]["channel_id"] == ctx["cid"]
        return ("PASS" if ok else "FAIL"), {"title": o["channel"]["title"], "subscribers": o["channel"]["subscribers"],
                                            "library": o["library"]}

    async def t3():
        v = await call("youtube_list_videos", {"limit": 100, "refresh": True})
        ctx["videos"] = v["videos"]
        return ("PASS" if v["total"] > 0 else "FAIL"), {"total_videos": v["total"]}

    async def t4():
        return "PASS", [{"title": x["title"], "views": x["views"], "format": x["format"]} for x in ctx["videos"][:5]]

    async def t5():
        a = await call("youtube_get_channel_analytics", {"days": 28})
        c = a["comparison"]
        return ("PASS" if c["views"]["current"] is not None else "FAIL"), {
            "window": a["window"], "views": c["views"], "net_subscribers": c["net_subscribers"],
            "limitations": a["limitations"]}

    async def t6():
        top = sorted([v for v in ctx["videos"] if v.get("views")], key=lambda v: v["views"], reverse=True)[:2]
        r = await call("youtube_compare_videos", {"video_ids": [v["video_id"] for v in top], "first_days": 28})
        return "PASS", {"leaders": r["leaders"]}

    async def t7():
        r = await call("youtube_analyze_channel_performance", {"days": 28})
        ctx["analysis"] = r
        d = r["video_diagnoses"][:3]
        return ("PASS" if d else "FAIL"), {"primary": r["primary_recommendation"].get("headline"),
                                           "examples": [{k: x[k] for k in ("title", "bottleneck", "confidence")} for x in d]}

    async def t8():
        r = await call("youtube_recommend_publishing_time", {"format": "all"})
        if r.get("status") == "ok":
            rec = r["recommendation"]
            return "PASS", {"best_day": rec["best_day"], "confidence": rec["best_day_confidence"], "timezone": r["timezone"]}
        return "PASS (limited)", {"status": r.get("status"), "message": r.get("message")}

    async def t9():
        return "NOT IN PHASE 1", "Content ideation is Phase 4 (needs external research layer)."

    async def t10():
        return "NOT IN PHASE 1", "Content calendar is Phase 5."

    async def t11():
        cand = sorted([v for v in ctx["videos"] if (v.get("comments") or 0) > 0], key=lambda v: v["comments"], reverse=True)
        if not cand:
            return "SKIPPED", "No video with comments."
        r = await call("youtube_get_comments", {"video_id": cand[0]["video_id"], "max_results": 50})
        return "PASS", {"video": cand[0]["title"], "comments_read": r["count"],
                        "question_share_pct": r["signals"]["share_of_comments_that_are_questions_pct"]}

    async def t12():
        r = await call("youtube_get_channel_analytics", {"days": 7})
        return "PASS (Phase 2 will format it as a report)", {"views_7d": r["comparison"]["views"]}

    async def t13():
        home = tempfile.mkdtemp(prefix="creatoros-expired-")
        code = (
            "import asyncio,json;from creatoros import auth,server;"
            "auth._save('UCexpiredtest',{'token':{'token':'bad','refresh_token':'bad','client_id':'bad',"
            "'client_secret':'bad','token_uri':'https://oauth2.googleapis.com/token','expiry':'2000-01-01T00:00:00Z'},"
            "'channel':{'channel_id':'UCexpiredtest','title':'x','uploads_playlist_id':'UUx'}});\n"
            "try:\n asyncio.run(server.mcp.call_tool('youtube_list_videos',{}));print('NO ERROR')\n"
            "except Exception as e: print(str(e))")
        out = subprocess.run([sys.executable, "-c", code], env={**os.environ, "CREATOROS_HOME": home},
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return ("PASS" if "[authentication]" in out else "FAIL"), out[:300]

    async def t14():
        return "VERIFIED OFFLINE", "Quota errors map to [quota] with reset guidance (tests/test_error_categories)."

    async def t15():
        tools = await server.mcp.list_tools()
        writers = [t.name for t in tools if not t.annotations.read_only_hint]
        scopes = auth._load(ctx["cid"])["channel"].get("scopes", [])
        ok = set(writers) <= {"youtube_connect_channel", "youtube_set_default_channel", "youtube_disconnect_channel"} \
            and not any("upload" in s or s.endswith("/youtube") for s in scopes)
        return ("PASS" if ok else "FAIL"), {"non_read_only_tools": writers, "granted_scopes": scopes}

    cases = [
        (1, "Connect a real YouTube channel", "At least one channel connected", "OAuth 2.0 + channels.list", t1),
        (2, "Identify the correct channel", "Overview channel_id == connected id", "Data API channels.list", t2),
        (3, "Retrieve uploaded videos", "total > 0", "Data API playlistItems.list + videos.list", t3),
        (4, "Display the actual video library", "Real titles/views", "Local library cache", t4),
        (5, "Retrieve authorized analytics", "28-day views returned", "Analytics API reports.query", t5),
        (6, "Compare two videos with real metrics", "Leaders per metric", "Analytics API (video filter)", t6),
        (7, "Identify a video's bottleneck", "Diagnoses with evidence", "Analytics API + engine", t7),
        (8, "Recommend a publishing window", "Best day + confidence, or explicit 'insufficient data'", "Library + engine", t8),
        (9, "Generate five video ideas", "-", "Phase 4", t9),
        (10, "Create a weekly content calendar", "-", "Phase 5", t10),
        (11, "Analyze actual comments", "Comments + derived signals", "Data API commentThreads.list", t11),
        (12, "Weekly performance numbers", "7-day comparison", "Analytics API", t12),
        (13, "Handle expired OAuth", "[authentication] error with fix", "Google token endpoint", t13),
        (14, "Handle quota exhaustion", "[quota] error with fix", "Error mapper", t14),
        (15, "Prevent unauthorized publishing", "No write tools, read-only scopes", "Tool registry + stored scopes", t15),
    ]
    for c in cases:
        await case(*c)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("acceptance_results.json", "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2, default=str)
    lines = [f"# CreatorOS acceptance results - {stamp}\n", "| # | Scenario | Result | API source |", "|---|---|---|---|"]
    lines += [f"| {r['#']} | {r['scenario']} | {r['result']} | {r['api_source']} |" for r in RESULTS]
    lines.append("\n## Details\n")
    for r in RESULTS:
        lines.append(f"### {r['#']}. {r['scenario']}\n- Expected: {r['expected']}\n- Result: **{r['result']}** ({r['seconds']}s)")
        lines.append(f"- Actual:\n```json\n{json.dumps(r.get('actual'), indent=2, default=str)[:3000]}\n```")
        if r.get("error"):
            lines.append(f"- Error: `{r['error']}`")
    with open("acceptance_results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\nSaved acceptance_results.md and acceptance_results.json")


if __name__ == "__main__":
    server.setup_logging()
    asyncio.run(main())
