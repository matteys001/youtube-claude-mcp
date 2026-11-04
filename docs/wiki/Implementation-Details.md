# Implementation Details

This page records implementation behaviour verified against the current source. Source code remains authoritative if documentation and implementation diverge.

## Runtime
- Python >=3.10.
- Package: `creatoros-mcp`.
- MCP SDK: `mcp>=2.3,<3`.
- CLI entry points: `creatoros-mcp` and `creatoros-connect`.
- Current local transport: MCP stdio.

## Configuration
| Variable | Purpose |
|---|---|
| `CREATOROS_HOME` | Override `~/.creatoros` |
| `CREATOROS_CLIENT_SECRET` | OAuth client JSON path |
| `CREATOROS_GOOGLE_CLIENT_ID` | OAuth desktop client ID |
| `CREATOROS_GOOGLE_CLIENT_SECRET` | OAuth desktop client secret |
| `CREATOROS_API_KEY` | Optional Data API key for public comments |

The configuration defines read-only OAuth scopes for Phase 1 and separate future publishing scopes. It also defines a six-hour library cache, an approximately two-day Analytics lag buffer and a 180-second duration heuristic for Shorts classification.

## Local directory layout
| Path | Purpose |
|---|---|
| `~/.creatoros/` | Local application home; override with `CREATOROS_HOME` |
| `tokens/` | Encrypted per-channel tokens |
| `.vault_key` | Fernet key |
| `creatoros.db` | SQLite database |
| `settings.json` | Local settings/default channel |
| `client_secret.json` | Optional OAuth client file |
| `api_key.txt` | Optional YouTube Data API key |
| `logs/` | Server and tool-call logs |

## MCP inventory verified in source

**Tools (15):** `youtube_connect_channel`, `youtube_list_channels`, `youtube_set_default_channel`, `youtube_disconnect_channel`, `youtube_get_channel_overview`, `youtube_list_videos`, `youtube_search_videos`, `youtube_get_video_details`, `youtube_get_comments`, `youtube_get_channel_analytics`, `youtube_get_video_analytics`, `youtube_compare_videos`, `youtube_analyze_channel_performance`, `youtube_recommend_publishing_time`, `youtube_get_recommendation_history`.

**Resources:** `creatoros://channels`, `creatoros://channels/{channel_id}/videos`, `creatoros://channels/{channel_id}/recommendations`.

**Prompts:** `channel_health_assessment`, `weekly_creator_review`, `video_performance_analysis`.

Use MCP discovery on the installed build for exact parameter schemas and response contracts.

## Quota-conscious implementation
- Enumerates uploads through the channel uploads playlist rather than broad `search.list`.
- Paginates playlist items.
- Fetches video metadata in batches of up to 50.
- Searches the local library without another YouTube search request.
- Uses a six-hour cache unless a refresh is requested.
- The documented library sync path is capped at 500 videos.

## Error categories
`authentication`, `permission`, `quota`, `unsupported_metric`, `unavailable_data`, `invalid_input`, `configuration`, `confirmation_required`, and `system`.

Errors should preserve the category, message and corrective action.

## Protocol safety
Handlers run blocking Google API and local database work through `asyncio.to_thread`. Do not write ordinary diagnostic output to stdout; stdout is reserved for MCP protocol messages.

## Related
- [Architecture](Architecture.md)
- [MCP Tool Reference](MCP-Tool-Reference.md)
- [Security & Privacy](Security-and-Privacy.md)
