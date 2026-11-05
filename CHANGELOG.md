# Changelog

## 0.3.5 — 2026-11-05
- Plugin no longer declares settings, so the server starts in Cowork (which cannot collect plugin settings). Credentials are read from `.creatoros` (`client_secret.json`, optional `api_key.txt`).

## 0.3.4 — 2026-11-05
- Repository moved to github.com/matteys001/youtube-claude-mcp; all links updated.

## 0.3.3 — 2026-11-04
- Plugin settings are optional so the server starts in Cowork (which does not collect plugin settings); falls back to files in `.creatoros`.
- Fixed privacy-policy link formatting picked up by the directory listing.

## 0.3.2 — 2026-11-04
- Plugin settings passed with Claude's required names (`CLAUDE_PLUGIN_OPTION_<KEY>`).

## 0.3.1 — 2026-11-04
- Directory validation fixes: dependencies pinned in `uv.lock` and started with `uv run --locked`; server started by a shipped file (`python ${CLAUDE_PLUGIN_ROOT}/launch.py`).
- Google OAuth Client ID/Secret and API key are collected through plugin settings (`userConfig`, secrets in secure storage) instead of files.
- Built `.mcpb` removed from the repository (published on GitHub Releases instead).

## 0.3.0 — 2026-11-04
- Packaged as a **Claude plugin** for the Claude directory (Anthropic no longer lists local MCPB extensions on their own since 25 Sep 2026): `.claude-plugin/plugin.json`, `.mcp.json` (local server via `uv`), and the `youtube-channel-review` skill.
- Passes `claude plugin validate` directory checks.

## 0.2.0 — 2026-11-04
- Packaged as a **Claude Desktop extension** (MCPB, manifest 0.4, `uv` runtime): one-click install, no manual Python setup.
- Extension settings for the Google OAuth client file and optional YouTube API key.
- All tools carry directory-compliant annotations (`readOnlyHint` or `destructiveHint`) and titles.
- Added privacy policy, MIT license, icon, submission checklist.

## 0.1.2 — 2026-11-04
- Automatic retries with backoff for transient Google errors (5xx, rate limits).
- Health check no longer calls a pattern the "main bottleneck" when it appears in under 30% of recent videos.
- Publishing-time tool explains when no slot has enough videos yet.

## 0.1.1 — 2026-11-04
- Windows: bundled timezone data (`tzdata`).
- Comments read with a restricted API key so the Google connection stays read-only.

## 0.1.0 — 2026-11-04
- Phase 1 vertical slice: OAuth, channel discovery, video library, analytics, bottleneck diagnosis, publishing-time estimate, comments, 15 tools / 3 resources / 3 prompts.
