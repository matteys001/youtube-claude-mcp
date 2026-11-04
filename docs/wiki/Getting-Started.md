# Getting Started

This guide installs the local CreatorOS MCP server and connects it to Claude Desktop.

## 1. Prerequisites

- Windows or macOS computer.
- Claude Desktop installed.
- Python 3.10 or newer.
- Google account with access to the YouTube channel.
- Internet access for Google OAuth and YouTube API requests.

## 2. Configure Google Cloud

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project, for example `CreatorOS`.
3. Enable **YouTube Data API v3** and **YouTube Analytics API**.
4. Configure Google Auth Platform / OAuth consent screen.
5. Add your Google account as a test user if the OAuth application is in Testing mode.
6. Create an OAuth client with application type **Desktop app**.
7. Download the client JSON file.
8. Rename it to `client_secret.json`.

Store it outside the repository:

- macOS: `~/.creatoros/client_secret.json`
- Windows: `%USERPROFILE%\.creatoros\client_secret.json`

Do not commit this file or share it publicly.

> While the OAuth application remains in Google's Testing mode, refresh-token access may require reauthorization every seven days, depending on Google's OAuth rules and account configuration.

## 3. Install CreatorOS

Clone the repository:

```bash
git clone https://github.com/mattey2026/youtube-claude-mcp.git
cd youtube-claude-mcp
```

### macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e .
```

### Windows

```bat
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -e .
```

## 4. Connect a YouTube channel

### macOS

```bash
.venv/bin/creatoros-connect
```

### Windows

```bat
.venv\Scripts\creatoros-connect
```

A browser window opens for Google authorization. Select the correct Google account and channel. The terminal should confirm the connected channel.

Run the command again if you want to connect another channel.

## 5. Optional: configure public comment access

The project README documents an optional YouTube Data API key for reading public comments while retaining read-only OAuth scopes.

1. Create an API key in the same Google Cloud project.
2. Restrict it to **YouTube Data API v3**.
3. Save it as `api_key.txt` in the local `.creatoros` directory.

Never commit the API key. Follow the current README for exact platform-specific commands.

## 6. Configure Claude Desktop

Open Claude Desktop → **Settings → Developer → Edit Config**.

Add the CreatorOS server entry to the existing `mcpServers` object. Preserve other MCP server entries.

### macOS example

```json
{
  "mcpServers": {
    "creatoros": {
      "command": "/Users/YOUR-NAME/path/to/youtube-claude-mcp/.venv/bin/python",
      "args": ["-m", "creatoros.server"]
    }
  }
}
```

### Windows example

```json
{
  "mcpServers": {
    "creatoros": {
      "command": "C:\\Users\\YOUR-NAME\\path\\to\\youtube-claude-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "creatoros.server"]
    }
  }
}
```

Replace the example path with the actual absolute path on your computer.

Save the file, fully quit Claude Desktop, and reopen it. Verify that CreatorOS appears in the available tools.

## 7. First prompt

Try this in a new Claude conversation:

> Use CreatorOS to run a full health check on my YouTube channel for the last 28 days. Identify the main performance bottleneck, show the supporting evidence, explain confidence and limitations, and recommend three actions for this week.

## 8. Verify the installation

Run the offline tests from the repository root:

```bash
pip install -e ".[dev]"
pytest -q
```

For live API acceptance tests, follow the current README and inspect the generated report. Offline tests do not prove that live Google OAuth and every YouTube API report work for a specific channel.

## 9. Local data location

CreatorOS stores its local configuration, encrypted tokens, database and logs under:

- macOS: `~/.creatoros/`
- Windows: `%USERPROFILE%\.creatoros\`

See [Security & Privacy](Security-and-Privacy.md) before backing up, moving or deleting this directory.

## Related guides

- [User Guide](User-Guide.md)
- [Troubleshooting](Troubleshooting.md)
- [Security & Privacy](Security-and-Privacy.md)
