# MCP Tool Reference

This page describes the documented Phase 1 MCP surface. Always verify tool names and input schemas against the current `creatoros/server.py` implementation because the source code is authoritative.

## 1. Tool inventory

The architecture documentation records the following 15 tools:

| Tool | Purpose |
|---|---|
| `youtube_connect_channel` | Start Google sign-in and connect a channel |
| `youtube_list_channels` | List connected channels and the default |
| `youtube_set_default_channel` | Select the default channel |
| `youtube_disconnect_channel` | Revoke access and remove a local token, with confirmation |
| `youtube_get_channel_overview` | Retrieve channel profile, statistics and upload cadence |
| `youtube_list_videos` | List owned-channel videos with filters, sorting and pagination |
| `youtube_search_videos` | Search the locally synchronized video library |
| `youtube_get_video_details` | Retrieve video metadata and stored stat history |
| `youtube_get_comments` | Retrieve accessible comments and viewer questions |
| `youtube_get_channel_analytics` | Retrieve channel analytics and period comparisons |
| `youtube_get_video_analytics` | Retrieve per-video analytics, retention and traffic data where available |
| `youtube_compare_videos` | Compare videos over equivalent first-N-day windows |
| `youtube_analyze_channel_performance` | Diagnose channel performance and prioritize a recommendation |
| `youtube_recommend_publishing_time` | Infer publishing windows from the channel's historical performance |
| `youtube_get_recommendation_history` | Review previously saved recommendations |

The exact parameter names, required fields, enums and response schemas must be taken from the current MCP tool definitions. Do not infer or fabricate a schema from this summary.

## 2. Resources and prompts

The repository's architecture documents a baseline of three MCP resources and three MCP prompts. Their exact URI and prompt contracts should be verified from the current server implementation and MCP client discovery.

## 3. Tool selection patterns

| User intent | Start with |
|---|---|
| Connect or switch a channel | Channel connection/list/default tools |
| Understand overall performance | `youtube_get_channel_overview` and `youtube_analyze_channel_performance` |
| Find a video | `youtube_list_videos` or `youtube_search_videos` |
| Investigate one video | `youtube_get_video_details` and `youtube_get_video_analytics` |
| Compare two uploads | `youtube_compare_videos` |
| Understand viewer feedback | `youtube_get_comments` |
| Decide when to publish | `youtube_recommend_publishing_time` |
| Review past advice | `youtube_get_recommendation_history` |

## 4. Tool-use expectations for AI clients

When using CreatorOS:

1. Select the correct connected channel before analysis.
2. Specify a date range and timezone when relevant.
3. Use equivalent observation windows for video comparisons.
4. Explain missing or unavailable metrics.
5. Preserve provenance labels.
6. Show sample sizes and confidence for estimates.
7. Do not present a recommendation as a guaranteed outcome.
8. Never claim to have performed write operations; the current release is read-only.

## 5. API quota considerations

YouTube Data API methods consume quota. Avoid unnecessary repeated synchronization and broad searches. The current implementation documents a six-hour library cache and local-library search that does not require a YouTube search API call.

Some Data API search operations can be significantly more expensive than listing an uploads playlist. Prefer the existing library and targeted lookups when possible.

## Related guides

- [User Guide](User-Guide.md)
- [Architecture](Architecture.md)
- [Roadmap](Roadmap.md)
