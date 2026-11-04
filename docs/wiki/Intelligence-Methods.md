# Intelligence Methods

CreatorOS separates facts, calculations, estimates and hypotheses.

## Evidence labels

| Label | Meaning |
|---|---|
| `measured` | Directly returned by YouTube |
| `derived` | Deterministic calculation on measured data |
| `estimated` | Statistical inference from historical observations |
| `ai_recommendation` | Suggested action to test, not a proven cause |

## Period comparison

The engine compares equal-length current and previous windows. It reports values and percentage change where calculable. A zero or missing previous value must not produce a fabricated percentage.

## Momentum

The current implementation compares video views in current and previous periods. Documented rules include rising at 30% or more above the previous period and declining at 40% or more below it, subject to minimum view thresholds. New-this-period videos require sufficient current views and no prior-period views. These are operational heuristics, not universal definitions of growth.

## Bottleneck diagnosis

Videos are compared with the channel's own same-format median where applicable. The playbook covers click/packaging, discovery, packaging plus content, consumption/retention and subscriber conversion. Low CTR relative to a baseline may indicate a packaging opportunity, but traffic source, audience and topic mix can also affect CTR. A diagnosis is a signal to investigate, not proof of causality.

## Publishing-time inference

The current method separates uploads by format, normalizes views against nearby same-format peers by publication date, groups upload times by weekday and three-hour block in the selected timezone, requires a minimum sample, and reports sample size and confidence.

This is an observational association, not a causal experiment. It does not access YouTube Studio's native audience-online heatmap. If evidence is insufficient, CreatorOS should say so rather than invent a best time.

## Recommendation quality

A useful recommendation should include the action, supporting measurements, baseline and observation window, sample size, confidence, limitations and a validation step. Do not claim causal lift without a controlled experiment.

## Interpretation guardrails

- Do not compare Shorts and long-form without qualification.
- Do not compare lifetime totals when video ages differ.
- Do not interpret missing metrics as zero.
- Do not treat a small sample as robust evidence.
- Do not promise a recommendation will increase views.
- Do not present public competitor metrics as private analytics.

## Related

- [Data Model and Analytics](Data-Model-and-Analytics.md)
- [User Guide](User-Guide.md)
- [Roadmap](Roadmap.md)
