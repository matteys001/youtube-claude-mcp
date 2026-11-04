# Claude Integration

## Integration model

CreatorOS is a local MCP process. Claude communicates with it through MCP stdio. It is not a hosted web service and does not automatically appear in ordinary claude.ai web chat.

The repository README documents these local integration routes: Claude Desktop extension package (`.mcpb`), Claude Cowork plugin, Claude Code using a local plugin directory, and manual Claude Desktop MCP configuration. Follow the current README for the release-specific steps.

## Server identity

- Name: `creatoros_mcp`
- Title: `CreatorOS - YouTube Creator Intelligence`
- Current local transport: stdio
- Version: package version in the installed build

## AI-client instructions

The server guides Claude to list connected channels first, connect a channel if none is available, use channel performance analysis for broad health questions, preserve evidence labels, quote supporting evidence, avoid causal overclaims, and relay structured error categories with corrective guidance.

## Built-in MCP prompts

- `channel_health_assessment`
- `weekly_creator_review`
- `video_performance_analysis`

## MCP resources

| URI | Purpose |
|---|---|
| `creatoros://channels` | Connected channels |
| `creatoros://channels/{channel_id}/videos` | Cached video library |
| `creatoros://channels/{channel_id}/recommendations` | Recommendation history |

## Suggested Claude workflows

**Channel health:** Run a 28-day health check, compare with the previous 28 days, identify the main bottleneck, show evidence and confidence, and recommend three actions.

**Weekly review:** Identify strongest content, declining videos, audience signals and next week's priorities. Separate facts from hypotheses.

**Video deep dive:** Analyze the video's first 28 days, including retention, traffic sources, search terms and subscriber conversion where data is available.

**Publishing strategy:** Recommend a publishing window from historical results, with sample size, confidence, timezone and limitations.

## Safety

OAuth may open a browser on the computer running the MCP server. Ask before disconnecting a channel. Current YouTube content operations are read-only. Never ask users to paste credentials or tokens into chat.

## Related

- [Getting Started](Getting-Started.md)
- [MCP Tool Reference](MCP-Tool-Reference.md)
- [Security and Privacy](Security-and-Privacy.md)
