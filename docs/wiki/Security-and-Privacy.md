# Security & Privacy

> **Official privacy policy:** [PRIVACY.md](https://github.com/mattey2026/youtube-claude-mcp/blob/main/PRIVACY.md)


CreatorOS handles Google OAuth credentials and channel analytics. Protecting those credentials and respecting the user's consent are core product requirements.

## 1. Current permission model

The documented Phase 1 OAuth scopes are:

- `youtube.readonly`
- `yt-analytics.readonly`

The current release is read-only. It does not request permissions to upload, edit, delete or comment on videos.

Public comment retrieval may use a separately configured YouTube Data API key, as described in the README. Restrict that key to YouTube Data API v3.

## 2. Local data storage

The application stores its local data under:

- macOS: `~/.creatoros/`
- Windows: `%USERPROFILE%\.creatoros\`

The directory may contain:

- OAuth client configuration.
- Encrypted per-channel token files.
- A local encryption key.
- SQLite database and historical snapshots.
- Logs and tool-call audit records.
- Optional API key file.

Treat the entire directory as sensitive. Do not upload it to public repositories or share it without reviewing its contents.

## 3. Token protection

The current architecture documents Fernet encryption for OAuth token files.

Operational recommendations:

- Restrict local file permissions.
- Keep OAuth client secrets and API keys out of source control.
- Never paste access or refresh tokens into Claude chats, issues or logs.
- Protect device login and disk encryption.
- Review backups for accidental inclusion of credentials.
- Reauthorize through Google if credentials may have been exposed.

Local encryption is useful protection at rest, but it does not protect secrets from malware or an attacker who already controls the logged-in workstation.

## 4. Disconnecting a channel

Use the CreatorOS disconnect tool and confirm the action. The documented flow attempts to revoke the Google grant and removes the local token file.

If you suspect exposure, also review and revoke access through [Google Account third-party connections](https://myaccount.google.com/permissions).

## 5. Data minimization

Channel analytics, comments and logs can reveal sensitive business or audience information.

- Share only the data required for the task.
- Avoid including secrets in diagnostic reports.
- Review logs before attaching them to issues.
- Do not commit local database files or token directories.
- Apply retention and deletion controls as the product evolves.

## 6. Future write capabilities

Publishing, editing metadata, managing playlists or replying to comments are not current Phase 1 capabilities.

Any future write workflow must include:

1. Separate and incremental OAuth scopes.
2. Explicit user consent.
3. Human confirmation before externally visible actions.
4. Idempotency and safe retry handling.
5. Audit records.
6. Clear rollback or recovery guidance where possible.

## 7. Future hosted deployment

A hosted multi-user service will require a stronger control plane, including tenant isolation, RBAC, managed key storage, secure secret rotation, data retention controls, monitoring, incident response and an independently reviewed threat model.

## Related guides

- [Getting Started](Getting-Started.md)
- [Architecture](Architecture.md)
