# Anthropic Directory Submission — CreatorOS

Path: **Desktop extension (local MCP server, MCPB)**, not a remote connector.
Guide: https://support.claude.com/en/articles/12922832-local-mcp-server-submission-guide
Form: https://forms.gle/tyiAZvch1kDADKoP9

## 1. Mandatory requirements

| Requirement | Status | Where |
|---|---|---|
| Working MCPB bundle | ✅ Built and launched via `uv` like Claude Desktop | `creatoros-youtube-0.2.0.mcpb` (GitHub Release) |
| Every tool has `readOnlyHint` **or** `destructiveHint` (+ title) | ✅ Enforced by test `test_every_tool_has_exactly_one_directory_annotation` | `creatoros/server.py` |
| Privacy policy in README **and** `manifest.json`, HTTPS on own domain, manifest ≥ 0.3 | ⚠️ Text ready (`PRIVACY.md`), manifest 0.4 points to `https://matteys.com/creatoros/privacy` — **must be published on matteys.com** | `PRIVACY.md`, `manifest.json` |
| ≥ 3 working examples in README | ✅ 5 examples | `README.md` → Examples |
| README sections: Description, Features, Installation, Configuration, Examples, Privacy, Support | ✅ | `README.md` |
| Test credentials (extension uses an external API + auth) | ⚠️ **To prepare** — see §3 | Submission form |
| LICENSE, 512×512 icon, CHANGELOG | ✅ | repo root |
| Tested on Windows **and** macOS, clean machine | ⚠️ Windows live-tested (12/15 + 2 by design + 1 offline). **macOS clean install still to do** | |

## 2. Blockers before submitting (owner actions)

1. **Publish the privacy policy** at `https://matteys.com/creatoros/privacy` (copy `PRIVACY.md`). Must be your domain, HTTPS, publicly reachable.
2. **Google OAuth verification (strongly recommended).** Today every user must create their own Google Cloud OAuth client, and apps in *Testing* mode force re-sign-in every 7 days. For a public listing:
   - Publish one CreatorOS **Desktop app** OAuth client and ship it as `creatoros/oauth_client.json` (the code already uses it automatically when present; desktop-app client secrets are not confidential per Google's installed-app guidance).
   - In Google Cloud → Google Auth Platform → **Audience → Publish app**, then complete **verification** for the YouTube scopes (needs: homepage, privacy policy on your verified domain, scope justification, demo video of the consent flow). Expect several weeks.
   - Without this, reviewers and users face a heavy setup; a submission may be returned.
3. **Reviewer test account**: a dedicated Google account that owns a YouTube channel with some uploads and analytics, added as a Test user (or verified app). Give credentials + the OAuth client file (if not bundled) via the form's secure field.
4. **macOS clean-machine test**: install the `.mcpb`, configure, run the 5 README examples.

## 3. Draft form answers

- **Name:** CreatorOS – YouTube Creator Intelligence
- **Type:** Desktop extension (MCPB)
- **Short description:** Ask Claude how your YouTube channel is really doing — analytics, bottlenecks, best publishing times and audience questions. Read-only.
- **External services:** Google YouTube Data API v3 and YouTube Analytics API v2 (OAuth 2.0, scopes `youtube.readonly`, `yt-analytics.readonly`); optional API key for public comments.
- **Data handling:** Local only; tokens encrypted; no publisher servers, no telemetry. Privacy: https://matteys.com/creatoros/privacy
- **Write operations:** None on YouTube. Only local writes (token vault/settings) — those three tools are marked `destructiveHint: true`; disconnect requires explicit `confirm=true`.
- **Examples:** README → Examples 1–5.
- **Repository:** https://github.com/mattey2026/youtube-claude-mcp
- **Support:** sumit@matteys.com · GitHub Issues
- **Test credentials:** (see §2.3)

## 4. Rebuilding the bundle

```bash
npm install -g @anthropic-ai/mcpb
mcpb validate manifest.json
mcpb pack . creatoros-youtube-<version>.mcpb
mcpb info creatoros-youtube-<version>.mcpb
```
