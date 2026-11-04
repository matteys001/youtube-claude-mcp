# Troubleshooting

Use this guide to diagnose common CreatorOS installation and runtime issues. Error messages and setup steps can change; the current README and logs are the first sources to check.

## 1. CreatorOS tools do not appear in Claude Desktop

Check:

1. The MCP server entry is inside the existing `mcpServers` object.
2. The Python executable path is absolute and correct.
3. The virtual environment exists and dependencies are installed.
4. The JSON configuration is valid.
5. Claude Desktop was fully quit and restarted.
6. The configured command can launch `python -m creatoros.server` outside Claude.

## 2. OAuth client configuration not found

Confirm that `client_secret.json` is located at:

- macOS: `~/.creatoros/client_secret.json`
- Windows: `%USERPROFILE%\.creatoros\client_secret.json`

Check spelling and file extension. Ensure the file is valid OAuth desktop-client JSON.

## 3. Google API not enabled

In Google Cloud Console, verify that both YouTube Data API v3 and YouTube Analytics API are enabled for the same project associated with the OAuth client.

## 4. Authentication expired or access denied

- Re-run `creatoros-connect`.
- Select the Google account that owns or manages the channel.
- Confirm the intended channel or Brand Account.
- If the OAuth application is in Testing mode, review Google's test-user and refresh-token restrictions.

## 5. Comments are unavailable

The documented design uses a restricted YouTube Data API key for public comment retrieval while retaining read-only OAuth scopes.

Check that:

- The optional API key is present in the expected local file.
- The key is restricted to YouTube Data API v3.
- The API is enabled for the key's Google Cloud project.
- The video has comments enabled and accessible.

## 6. Analytics data is missing

Possible causes include:

- The channel or video has insufficient data.
- The requested metric or dimension combination is not supported by that report.
- The selected date range is too recent or affected by reporting delay.
- The authorized account does not have access to the channel.
- YouTube returned a transient error.

Try a wider date range and inspect the exact structured error. Do not interpret unavailable data as zero.

## 7. Quota exceeded

Reduce repeated calls and use local library search where possible. Allow the applicable quota window to reset or review quota allocation in Google Cloud Console.

## 8. Timezone database errors on Windows

The project dependency list includes `tzdata` for systems without an operating-system timezone database. Reinstall the project dependencies:

```bat
.venv\Scripts\pip install -e .
```

## 9. Transient Google API errors

Retry transient server and network failures after a delay. Avoid aggressive retry loops. The repository's current client implementation and tests define the actual retry behaviour; check those before assuming a retry policy.

## 10. Logs and diagnostics

The architecture documents local logs under `~/.creatoros/logs/`, including server and tool-call logs. Review them for the relevant timestamp and error category.

Before sharing logs:

- Remove tokens, keys, email addresses and other sensitive identifiers.
- Include the OS, Python version, CreatorOS version and exact failing operation.
- Include a minimal reproduction and sanitized error message.

## 11. Still blocked?

Open a GitHub issue with:

- A concise problem statement.
- Steps to reproduce.
- Expected and actual behaviour.
- OS and Python version.
- CreatorOS version / commit.
- Sanitized logs.

Never attach OAuth client secrets, refresh tokens, API keys or an unredacted local database.

## Related guides

- [Getting Started](Getting-Started.md)
- [Security & Privacy](Security-and-Privacy.md)
