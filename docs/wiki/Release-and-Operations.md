# Release and Operations

## Test commands

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
pytest -q
```

Use the current README and repository release workflow for packaging instructions. A local editable install is not the same as validating a packaged Claude extension or plugin.

## Validation layers

| Layer | What it validates |
|---|---|
| Unit tests | Pure functions and helpers |
| Component tests | Persistence, OAuth vault, API wrappers and error mapping |
| MCP protocol tests | Initialize, discover and invoke tools/resources/prompts |
| Package tests | Clean installation and launch |
| Live acceptance | Real OAuth, channel access and API report behaviour |
| Client acceptance | Actual use in the Claude clients claimed by the release |

Passing offline tests does not prove live Google API access for every account or channel.

## Live acceptance checklist

- [ ] Install in a clean environment.
- [ ] Configure Google OAuth desktop credentials.
- [ ] Complete Google consent.
- [ ] Discover the connected channel.
- [ ] Synchronize the uploads library.
- [ ] Validate channel overview and video metadata.
- [ ] Validate channel and per-video Analytics reports.
- [ ] Validate retention and optional reach metrics where available.
- [ ] Test unavailable data and low-volume channels.
- [ ] Test quota and transient errors.
- [ ] Verify encrypted token storage and disconnect.
- [ ] Test supported Claude client installation paths.
- [ ] Review logs for secrets and unnecessary personal data.
- [ ] Update release notes and wiki.

## Quota and reliability

Use uploads playlist enumeration instead of broad search where possible, batch video metadata requests, use local caching and local library search, respect quota errors and avoid aggressive retry loops. Explain report limitations and distinguish unavailable metrics from measured zeroes.

## Logs

The local application logs tool-call outcomes, duration and structured error details. Logs must not include OAuth token payloads, client secrets or API keys. Sanitize personal identifiers before attaching logs to issues.

## Release notes

Every release should record version and date, new features, behaviour changes, OAuth scope changes, API limitations, offline test results, live acceptance results separately, known issues and migration steps.

## Credential incident response

If a credential may have been exposed, revoke CreatorOS access from the Google Account security page, rotate exposed API keys or OAuth client credentials, remove exposed files from unsafe locations, review repository history and logs, and reconnect through Google's consent flow.

## Related

- [Getting Started](Getting-Started.md)
- [Security and Privacy](Security-and-Privacy.md)
- [Contributing](Contributing.md)
