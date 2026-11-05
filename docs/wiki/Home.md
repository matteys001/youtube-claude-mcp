# CreatorOS Wiki

> **YouTube Creator Intelligence for Claude**  
> Connect your YouTube channel, understand performance, and turn real channel data into better creator decisions.

Welcome to the CreatorOS documentation wiki. This is the central guide for users, developers, and contributors.

## What is CreatorOS?

CreatorOS is a local-first, read-only YouTube Creator Intelligence MCP server. It connects an owner's YouTube channel through Google OAuth, retrieves channel data and available private analytics from official YouTube APIs, stores local snapshots, and makes the resulting intelligence available to Claude through MCP.

CreatorOS is designed to help answer:

- How is my channel performing?
- Which videos are rising or declining?
- What is limiting channel performance?
- What are viewers asking in my comments?
- When should I publish, based on my own historical results?
- What should I prioritize next?

## Documentation

| Guide | Description |
|---|---|
| [Getting Started](Getting-Started.md) | Requirements, Google Cloud setup, installation and Claude Desktop connection |
| [User Guide](User-Guide.md) | How to use CreatorOS and interpret its outputs |
| [MCP Tool Reference](MCP-Tool-Reference.md) | Current tools, resources, prompts and usage patterns |
| [Architecture](Architecture.md) | Current solution, technical architecture and data flows |
| [Security & Privacy](Security-and-Privacy.md) | OAuth scopes, local storage, token protection and data boundaries |
| [Troubleshooting](Troubleshooting.md) | Common installation, authentication and API errors |
| [Roadmap](Roadmap.md) | Current maturity, planned capabilities and API feasibility |
| [Contributing](Contributing.md) | Development workflow, testing and documentation standards |
| [Implementation Details](Implementation-Details.md) | Runtime, configuration, local paths, MCP inventory and error taxonomy |
| [Data Model and Analytics](Data-Model-and-Analytics.md) | SQLite schema, metrics, provenance and reporting limits |
| [Intelligence Methods](Intelligence-Methods.md) | Momentum, bottleneck and publishing-time methodology |
| [Claude Integration](Claude-Integration.md) | MCP server identity, prompts, resources and Claude workflows |
| [Release and Operations](Release-and-Operations.md) | Testing, acceptance, release and operational practices |

## Project links

- [GitHub repository](https://github.com/matteys001/youtube-claude-mcp)
- [README and quick setup](../../README.md)
- [Solution and Technical Architecture](../SOLUTION_AND_TECHNICAL_ARCHITECTURE.md)
- [Phase 0 Design and Phase 1 Status](../ARCHITECTURE.md)

## Product principles

1. **Evidence before opinion:** distinguish API measurements from calculations and recommendations.
2. **Read-only by design:** the current release does not upload, edit, delete or comment.
3. **Creator-specific intelligence:** compare a channel with its own relevant historical baselines.
4. **Honest limitations:** never invent private competitor analytics or unavailable YouTube Studio metrics.
5. **Local-first privacy:** channel tokens and local snapshots are stored on the user's workstation.

## Current status

The repository documents a Phase 1 implementation. Always check the source code, tests, release notes and current README before assuming a feature or tool count is unchanged. The roadmap includes capabilities that are not yet implemented.

## First steps

1. Follow [Getting Started](Getting-Started.md).
2. Connect the Google account that owns or manages the YouTube channel.
3. Configure CreatorOS in Claude Desktop.
4. Run the channel health-check prompt in the [User Guide](User-Guide.md).
