# Data Model and Analytics

## SQLite tables

| Table | Purpose |
|---|---|
| `video_snapshot` | Append-only video metadata and public-stat snapshots |
| `channel_snapshot` | Channel profile and statistics snapshots |
| `analytics_snapshot` | Analytics report payloads and date ranges |
| `recommendation` | Saved recommendation records |
| `sync_state` | Last sync timestamp per channel and item |

Snapshots retain channel ID, fetch time, source and serialized data. Latest video records are selected for the current library view while earlier snapshots remain available.

## Data provenance

Typical source identifiers include `youtube.data.v3:channels.list`, `youtube.data.v3:videos.list` and `youtubeAnalytics.v2:reports.query`. Preserve source, fetch timestamp and limitation fields when presenting results.

## Analytics metrics

Core metrics include views, estimated minutes watched, average view duration, average view percentage, subscribers gained and lost, likes, comments and shares. Optional reach metrics include `videoThumbnailImpressions` and `videoThumbnailImpressionsClickRate`. These may be unavailable for a particular report combination. Missing metrics are not zero.

Report dimensions used by the implementation include day, video, traffic-source type and country, with other breakdowns where supported.

## Reporting windows

The Analytics helper builds equal-length date windows ending approximately two days before the current date to account for reporting latency. This is a default buffer, not a guarantee that all reports are final.

## Video format classification

The current integration uses broadcast metadata for live content, a duration heuristic of up to 180 seconds for Shorts, and long-form for other non-live videos. The output includes a format-basis explanation. This is not a definitive statement about YouTube Shorts eligibility or distribution.

## Derived metrics

Period percentage change is `(current - previous) / previous * 100`. If the previous value is zero or missing, percentage change is undefined and should remain null. Net subscribers are gained minus lost.

Per-video Analytics rows are joined to cached metadata by video ID. A title can be unavailable if the video is not in the synchronized library.

## Retention and traffic

Video Analytics can include a retention curve and largest sampled drop-off. Traffic-source reports describe view origins. Search terms are returned only when the report supports them and YouTube provides data. These are diagnostic signals, not proof of why a viewer left or why a video performed a certain way.

## Historical limitations

- Snapshots begin when CreatorOS starts collecting them.
- The documented local library sync is capped at 500 videos.
- Analytics can omit low-volume data.
- Metric and dimension combinations vary by report.
- Private analytics require an authorized account with access to the channel.

## Related

- [Intelligence Methods](Intelligence-Methods.md)
- [Architecture](Architecture.md)
- [User Guide](User-Guide.md)
