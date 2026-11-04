# Claude Directory Submission — CreatorOS

## Which route

Since **25 September 2026** the Claude directory takes submissions through the developer portal
(https://claude.ai/directory/manage, paid plans). It offers two options:

| Option | For | CreatorOS? |
|---|---|---|
| **MCP connector** | A remote server reachable at an `https://` URL | ❌ Not yet — CreatorOS runs locally (Phase 6 would host it) |
| **Plugin bundle** | A GitHub repo with `.claude-plugin/plugin.json` (skills, local or remote MCP servers) | ✅ **Use this** |

Local desktop extensions (MCPB) are no longer accepted as standalone listings; a local server must ship inside a plugin.
Local MCP servers in plugins load in **Cowork (on the user's computer) and Claude Code**, not in claude.ai web chat.

## Readiness

| Check | Status |
|---|---|
| `.claude-plugin/plugin.json` (name, version, description, author, license) | ✅ |
| `.mcp.json` local server (`uv run --directory ${CLAUDE_PLUGIN_ROOT} main.py`) | ✅ |
| Skill: `skills/youtube-channel-review/SKILL.md` | ✅ |
| README ≥ 40 words, says what it does, how to use, what data goes where | ✅ |
| LICENSE (MIT) | ✅ |
| `claude plugin validate` | ✅ Validation passed, nothing to report |
| Every tool has `title` + `readOnlyHint` or `destructiveHint` | ✅ (enforced by tests) |
| Privacy policy URL | ✅ https://github.com/mattey2026/youtube-claude-mcp/blob/main/PRIVACY.md (move to own domain before Google OAuth verification) |
| Tested in Cowork on Windows and macOS | ⚠️ To do (upload ZIP: Customize → Plugins → Add → Upload plugin) |
| Google OAuth: shared, verified client | ⚠️ Recommended before wide release (see below) |

## Portal steps (Plugin bundle)

1. Connect your GitHub account to claude.ai (the account needs push access to `mattey2026/youtube-claude-mcp`).
2. Portal → **Submit** → **Plugin bundle**.
3. **Repository:** `mattey2026/youtube-claude-mcp` · **Plugin path:** leave empty (repo root) · **Branch:** `main`.
4. **Validate.**
5. **Data-handling answers:**
   - Reads personal data? **Yes** — the user's own YouTube channel data (channel/video metadata, private YouTube Analytics, public comments with optional API key), read-only via Google OAuth.
   - Stores data? **Yes, locally only** on the user's computer (`~/.creatoros`: encrypted OAuth tokens, SQLite history, logs without secrets). Nothing stored by the publisher.
   - Sends data anywhere other than declared connectors? **Only Google's YouTube APIs** (`youtube.googleapis.com`, `youtubeanalytics.googleapis.com`, `oauth2.googleapis.com`). No telemetry, no publisher servers.
   - Retention: until the user deletes `~/.creatoros` or disconnects; revocable at myaccount.google.com/permissions.
   - Intended for under-18s? **No.**
6. Submit; watch the scan result and reviewer notes in the portal. Updates later ship by merging to `main`.

## Google OAuth (for a smooth public release)

Today each user creates their own Google Cloud OAuth client and, in Testing mode, re-signs in every 7 days.
For broad use: create one CreatorOS **Desktop app** client, ship it as `creatoros/oauth_client.json` (the code picks it up automatically),
publish the Google app and complete Google verification for `youtube.readonly` and `yt-analytics.readonly`
(needs homepage, privacy policy on your domain, scope justification, demo video).

## Future: MCP connector listing (Phase 6)

Host CreatorOS as a remote server (Streamable HTTP, OAuth 2.0, per-user tenant isolation) to work in claude.ai chat and on mobile,
then submit it as an **MCP connector** and pair it with this plugin.

## Validation report (portal) — how each item is handled

| Portal item | Type | Resolution |
|---|---|---|
| Unpinned uvx launcher | **Blocking** | Fixed in 0.3.1: `uv.lock` committed, `uv run --locked` |
| Server start line not accepted | Info | Fixed: `.mcp.json` runs `python ${CLAUDE_PLUGIN_ROOT}/launch.py` |
| MCP server command wasn't read | Policy hold | Fixed: literal path under `${CLAUDE_PLUGIN_ROOT}` |
| Uses a credential from the user's machine | Policy hold | Credentials now come from `userConfig` (secret marked `sensitive`). File fallbacks remain only for manual (non-plugin) installs — explain to reviewer |
| Files the validator couldn't inspect (`dist/*.mcpb`) | Policy hold | Fixed: removed from repo |
| Image file the code could run (`icon.png`) | Policy hold | Plain PNG used only as the listing/extension icon — reviewer confirms |
| Contains a download-and-run command | Note | Only in README install instructions for `uv`; nothing to change |
| Local MCP server: not on claude.ai | Info | Expected: works in Cowork and Claude Code |
| Server env name not accepted | Fix | Fixed in 0.3.2: env vars use `CLAUDE_PLUGIN_OPTION_<KEY>` |
| `uv.lock` too large to inspect | Policy hold | Standard lockfile (pins every package + hashes); required by the pinning rule — reviewer checks |
| `launch.py` not followed | Policy hold | Small readable Python launcher that runs `uv run --locked` — reviewer checks |
| Local MCP servers accepted only from Verified organizations | Info (future) | Not refused yet. Long-term path: host CreatorOS remotely (Phase 6) and submit as an MCP connector, or get the organization verified |
