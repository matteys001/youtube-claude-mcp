# CreatorOS – Privacy Policy

**Effective date:** 4 November 2026
**Applies to:** the CreatorOS YouTube Creator Intelligence extension for Claude Desktop ("CreatorOS"), published by Sumit Mattey.
**Canonical URL:** https://matteys.com/creatoros/privacy

## Summary

CreatorOS runs **entirely on your own computer**. It has no CreatorOS server, no account system, no analytics and no tracking. Your YouTube data travels only between your computer and Google, and is shown to Claude when you ask a question.

## 1. What data CreatorOS accesses

With your permission (Google sign-in, read-only), CreatorOS reads from Google's YouTube APIs:

- **Channel information:** name, description, public statistics, upload list.
- **Video information:** titles, descriptions, tags, duration, privacy status, public counts (views, likes, comments).
- **Private YouTube Analytics for your own channel:** views, watch time, average view duration and percentage, audience retention, subscribers gained and lost, likes, shares, traffic sources, YouTube search terms, countries, and subscriber vs non-subscriber viewing.
- **Public comments** on your videos (only if you add an optional YouTube API key).

CreatorOS requests only these Google permissions:
`youtube.readonly` and `yt-analytics.readonly`. It **cannot** upload, edit, delete, comment, or change anything on YouTube.

CreatorOS **never** sees or stores your Google password; sign-in happens on Google's own page.

## 2. How the data is used

Only to answer the questions you ask Claude about your channel: performance summaries, comparisons, bottleneck diagnosis, publishing-time estimates and audience questions. CreatorOS does not use your data for advertising, profiling, model training, or any other purpose.

## 3. Where the data is stored

All storage is **local, on your computer**, in the folder `.creatoros` in your user directory:

| Item | Purpose | Protection |
|---|---|---|
| Google sign-in tokens | Stay connected without signing in each time | Encrypted (Fernet/AES), file permissions restricted to your user |
| `creatoros.db` (SQLite) | Cached video list, analytics snapshots and past recommendations, so trends can be compared over time | Local file in your user folder |
| Logs (`logs/`) | Troubleshooting: tool name, success/failure, timing, error category | Never contain tokens, keys or video content |
| Optional `api_key.txt` / extension setting | Reading public comments | Stored by you; Claude Desktop stores the extension setting securely |

## 4. Sharing with third parties

- **Google (YouTube APIs):** CreatorOS sends requests to Google to retrieve your data. Google's handling is governed by the [Google Privacy Policy](https://policies.google.com/privacy), and use of YouTube data is subject to the [YouTube Terms of Service](https://www.youtube.com/t/terms).
- **Anthropic (Claude):** results of the tools you invoke are returned to Claude so it can answer you. Anthropic's handling is governed by the [Anthropic Privacy Policy](https://www.anthropic.com/legal/privacy).
- **No one else.** The publisher of CreatorOS does not receive, collect, sell or share any of your data. There is no telemetry.

CreatorOS's use of information received from Google APIs adheres to the [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy), including the Limited Use requirements.

## 5. Retention and deletion

Data stays on your computer until you delete it.

- **Disconnect a channel:** ask Claude to run `youtube_disconnect_channel` (it revokes Google's access and deletes the stored token), or revoke access at https://myaccount.google.com/permissions.
- **Delete everything:** remove the `.creatoros` folder in your user directory and uninstall the extension.
- Google may keep its own records according to its policies.

## 6. Children

CreatorOS is intended for channel owners aged 18+ (or the minimum age required by YouTube in their country) and does not knowingly process data of children.

## 7. Security

Read-only permissions, encrypted tokens, no secrets returned to Claude, no network services opened except a temporary local sign-in listener during Google sign-in.

## 8. Changes

Changes are published at the canonical URL and in this repository's history, with a new effective date.

## 9. Contact

Questions or requests: **sumit@matteys.com** · Issues: https://github.com/mattey2026/youtube-claude-mcp/issues
