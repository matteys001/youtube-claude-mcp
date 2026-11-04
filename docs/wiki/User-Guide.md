# User Guide

This guide explains how to work with CreatorOS through Claude.

## 1. What CreatorOS can help you understand

The current Phase 1 release focuses on data from channels you own or are authorized to manage.

Typical questions include:

- How is my channel performing over the last 28 days?
- Which videos are gaining momentum?
- Which videos are declining?
- Compare two videos over their first 28 days.
- What is the traffic-source mix?
- What are viewers asking in comments?
- What publishing windows have performed best in my channel history?

Use the [MCP Tool Reference](MCP-Tool-Reference.md) for the current tool inventory.

## 2. Recommended first workflow

Start with a channel health assessment:

```text
Use CreatorOS to analyze my channel for the last 28 days.
Show:
1. Overall performance and comparison with the previous period.
2. Videos gaining and losing momentum.
3. The most common performance bottleneck.
4. Evidence and sample size behind the diagnosis.
5. Three prioritized actions for the next seven days.
Clearly distinguish measured facts, derived findings and estimates.
```

Then investigate the most important finding with targeted questions.

## 3. Video comparison

For a fair comparison, compare videos over equivalent ages rather than comparing lifetime totals.

Example:

> Compare my two latest long-form videos over their first 28 days. Compare views, watch time, average view duration, retention and subscriber conversion where available. Explain which video performed better and why the evidence supports that conclusion.

## 4. Audience questions and comments

Example:

> Review comments on my latest video. Summarize recurring questions, confusion points, positive reactions and requests for future content. Separate direct comment evidence from your interpretation.

Comment availability depends on YouTube API access, video settings and the optional API-key configuration documented in the README.

## 5. Publishing-time recommendations

Example:

> Recommend publishing windows for my next Short using my channel's own historical performance. Show the number of videos supporting each slot, the comparison method, confidence and any gaps in my publishing history.

Important: CreatorOS estimates publishing windows from historical performance cohorts. It does not access YouTube Studio's native audience-online heatmap.

## 6. How to interpret evidence labels

| Label | Meaning | Example |
|---|---|---|
| `measured` | Retrieved directly from an API or source | Views reported by YouTube Analytics |
| `derived` | Calculated from measured data | Percentage change between periods |
| `estimated` | Statistical estimate or inference | Publishing window based on historical cohorts |
| `ai_recommendation` | Suggested action generated from evidence | Test a different opening hook |

A recommendation is not proof of causality. Validate changes through subsequent channel performance.

## 7. Understand limitations

- Analytics availability and reporting delays vary by metric and report.
- Some reports require sufficient channel or video data.
- CTR and impression metrics may be unavailable for a particular query or report.
- Competitor private analytics are not accessible through the public YouTube APIs.
- The native YouTube Studio audience-online heatmap is not exposed through the current integration.
- The current release is read-only and cannot publish or edit videos.

## 8. Practical operating rhythm

A useful manual cadence:

- Weekly: run a channel health check.
- After each important upload: review early performance and comments.
- Monthly: compare content formats, topic groups and channel trends.
- Before changing publishing cadence: review sample size and confidence in historical recommendations.

Scheduled reporting is a roadmap capability unless implemented in the current release.

## Related guides

- [MCP Tool Reference](MCP-Tool-Reference.md)
- [Architecture](Architecture.md)
- [Roadmap](Roadmap.md)
