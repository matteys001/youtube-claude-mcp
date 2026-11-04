# Contributing

Thank you for helping improve CreatorOS. The project prioritizes correctness, security, maintainability and creator value.

## 1. Before making a change

- Read the [Architecture](Architecture.md) and [Roadmap](Roadmap.md).
- Inspect the existing implementation before proposing a new abstraction.
- Confirm whether the requirement belongs to the current release or a future phase.
- Check official YouTube and Google API documentation for API-dependent changes.

## 2. Engineering standards

- Use clear, typed Python interfaces.
- Keep business logic separate from MCP transport.
- Use structured errors and safe logging.
- Handle pagination, quota limits, transient failures and unavailable reports.
- Keep secrets and local user data out of source control.
- Preserve backward compatibility unless a breaking change is intentional and documented.
- Avoid adding dependencies without a clear need.

## 3. Testing

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest -q
```

Add tests for:

- Happy paths.
- Missing or malformed inputs.
- API errors and unavailable reports.
- Pagination and quota behaviour where applicable.
- Token handling and confirmation gates.
- Data provenance and limitations.
- Regression scenarios.

Offline tests must not be described as live API acceptance tests.

## 4. Security checklist

Before submitting a change, verify:

- No secrets, OAuth files, API keys or personal data are committed.
- OAuth scopes remain least-privilege.
- No new write operation bypasses explicit user confirmation.
- Logs do not expose credentials or unnecessary sensitive data.
- Local data handling and deletion behaviour are understood.

## 5. Documentation

Update the relevant wiki and architecture pages when a change affects:

- Setup or configuration.
- MCP tools, resources or prompts.
- Data flows or persistence.
- OAuth scopes or security.
- API feasibility or limitations.
- User-facing behaviour.
- Roadmap status.

Use Mermaid for editable diagrams where useful. Clearly label components as implemented, partially implemented, planned or proposed.

## 6. Pull request expectations

A useful pull request includes:

- Problem and user value.
- Summary of the implementation.
- Architecture impact.
- Security and API-scope impact.
- Tests executed and results.
- Documentation updates.
- Known limitations and follow-up work.

Never claim that a feature was tested against live YouTube data unless that test actually ran and its result is recorded.
