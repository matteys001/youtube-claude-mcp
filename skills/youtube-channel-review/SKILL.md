---
name: youtube-channel-review
description: Analyze the user's own YouTube channel with CreatorOS. Use when the user asks how their YouTube channel or a video is performing, why views or subscribers changed, what is holding a video back, which videos are rising or declining, when to publish, what viewers ask in comments, or wants a weekly creator review.
---

# YouTube channel review with CreatorOS

CreatorOS gives read-only access to the user's own YouTube channel. It cannot upload, edit, delete or comment.

## 1. Make sure a channel is connected
1. Call `youtube_list_channels`.
2. If none is connected, call `youtube_connect_channel` and tell the user a Google sign-in tab will open. If they see "Google hasn't verified this app", they can click **Continue** (it is their own Google Cloud app).
3. If several channels are connected, ask which one, or use the default.

## 2. Pick the right tool for the question

| User asks | Call |
|---|---|
| "How is my channel doing?", "What should I fix?" | `youtube_analyze_channel_performance` (days=28), then `youtube_get_channel_overview` |
| Numbers for a period | `youtube_get_channel_analytics` |
| One video: drop-off, discovery, search terms | `youtube_get_video_analytics` (omit `days` for lifetime) |
| "Compare video A and B" | `youtube_compare_videos` with `first_days` (equal windows) |
| "When should I publish?" | `youtube_recommend_publishing_time` — pass the audience's IANA timezone and `format` (short/long_form) |
| "What are viewers asking?" | `youtube_list_videos` (most_viewed or newest) → `youtube_get_comments` |
| Find videos on a topic | `youtube_search_videos` |
| "Did your last advice work?" | `youtube_get_recommendation_history`, then rerun the analysis and compare with the stored baseline |

## 3. Answer well
- Lead with the headline trend in one sentence, then the main bottleneck, the evidence (numbers, period), and at most three concrete actions.
- Keep CreatorOS's labels: **measured** (from YouTube), **derived** (arithmetic), **estimated** (pattern inference with confidence), **ai_recommendation** (suggestion to test). Never present a correlation as a proven cause.
- State the confidence and sample size. With few videos or low views, say the evidence is thin rather than over-advising.
- Mention relevant `limitations` from the tool result (e.g. ~48-hour analytics lag, impressions/CTR not available for that report, Shorts detected by duration).
- Never invent metrics. If a tool returns no data, say so and suggest a longer period.

## 4. Handling errors
Each error starts with a category. Relay the "How to fix" text:
- `[authentication]` → reconnect (Google testing-mode apps expire every 7 days).
- `[configuration]` → OAuth client file or API key missing; point to the README Configuration section.
- `[permission]` → wrong Google account or Brand Account.
- `[quota]` → wait for the daily reset (midnight US Pacific).
- `[unavailable_data]` → YouTube has no data for that request.
- `youtube_disconnect_channel` requires explicit user confirmation before `confirm=true`.
