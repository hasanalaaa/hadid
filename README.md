# Hadid

**Own your AI conversations.**

[![CI](https://github.com/hasanalaaa/hadid/actions/workflows/ci.yml/badge.svg)](https://github.com/hasanalaaa/hadid/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-6366f1.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](pyproject.toml)
[![Dependencies: zero](https://img.shields.io/badge/dependencies-zero-success.svg)](pyproject.toml)

Hadid imports your conversation history from **ChatGPT, Claude, and Gemini**, stores it **locally on your machine** in a single SQLite file, and gives you instant full-text search across all of it — from a beautiful local web app or straight from your terminal.

Your prompts and answers are some of your most valuable notes. Today they are locked inside separate platforms, impossible to search together, and gone if an account is lost. Hadid fixes that.

## Why Hadid?

- **Local-first & private** — everything stays on your disk. No accounts, no cloud, no telemetry. Ever.
- **One archive for every platform** — ChatGPT, Claude, and Gemini today; more importers coming.
- **Instant full-text search** — SQLite FTS5 searches tens of thousands of messages in milliseconds, with highlighted matches.
- **A web UI you actually want to use** — dark glassmorphism design, source filters, favorites, live stats, keyboard shortcuts, one-click copy and Markdown export.
- **Your data stays portable** — export any conversation (or all of them) to plain Markdown.
- **Zero dependencies** — pure Python standard library. `pip install` and go. Nothing to break.

## Quickstart

```bash
pip install git+https://github.com/hasanalaaa/hadid.git

# Or, from a local clone:
git clone https://github.com/hasanalaaa/hadid.git
cd hadid
pip install -e .

# 1. Export your data (see below), then import it.
#    Platform is auto-detected - straight from the ZIP:
hadid import auto path/to/export.zip

# 2. Search everything from your terminal:
hadid search "vector database"

# 3. Or browse it in your browser:
hadid serve             # opens http://127.0.0.1:8642
```

## The web app

Run `hadid serve` and you get a full local application:

- **Live search** with highlighted matches as you type
- **Filter chips** per platform (ChatGPT / Claude / Gemini) and a **Favorites** view
- **Conversation view** with role avatars, per-message **Copy**, and **Export .md**
- **Dashboard** with stat cards and a monthly activity chart
- **Light / dark themes**, remembered between sessions
- **Archive stats** always visible in the header
- **Keyboard shortcuts**: press `/` to search, `Esc` to clear

## Getting your export files

| Platform | How to export | File to import |
|---|---|---|
| **ChatGPT** | Settings → Data controls → Export data (ZIP arrives by email) | `conversations.json` |
| **Claude** | Settings → Privacy → Export data | `conversations.json` |
| **Gemini** | [Google Takeout](https://takeout.google.com) → My Activity → Gemini (JSON format) | `MyActivity.json` |

> **Note:** Google Takeout includes your Gemini prompts and only brief response snippets — that is a Google limitation, not a Hadid one.

## CLI reference

| Command | Description |
|---|---|
| `hadid import <platform> <file>` | Import an export file or ZIP (`chatgpt`, `claude`, `gemini`, `auto`) |
| `hadid search "<query>" [--source X]` | Full-text search across all messages |
| `hadid list [--source X] [--favorites]` | List archived conversations |
| `hadid export <id> [--out file.md]` | Export one conversation to Markdown |
| `hadid export --all [--dir exports/]` | Export the entire archive to Markdown |
| `hadid favorite <id>` | Star / unstar a conversation |
| `hadid stats` | Archive statistics |
| `hadid serve [--port N]` | Start the local web app |

All commands accept `--db <path>` (default: `~/.hadid/hadid.db`).

Example session:

```console
$ hadid import auto chatgpt-export.zip
Detected platform: chatgpt
Added 128, updated 0, skipped 0 conversation(s); 3412 new message(s).

$ hadid search "prompt caching"
[chatgpt] Reducing API costs  (conversation #42)
  assistant: …enable «prompt» «caching» to cut latency and cost …

$ hadid serve
Hadid is running at http://127.0.0.1:8642  (Ctrl+C to stop)
```

## Architecture

One SQLite file. One Python package. Zero dependencies.

```
hadid/
├─ importers/     # chatgpt.py, claude.py, gemini.py — add yours here
├─ db.py          # SQLite + FTS5 archive with schema migrations
├─ export.py      # Markdown export
├─ web/           # local web app package (server.py + templates.py + static/)
└─ cli.py         # argparse CLI
```

## Development

```bash
git clone https://github.com/hasanalaaa/hadid.git && cd hadid
pip install -e .[dev]
python3 -m pytest -v      # full suite, incl. end-to-end CLI tests
python3 -m ruff check .   # lint
```

CI lints and runs the test suite on Python 3.9, 3.11, and 3.13 for every
change on the default branch and merge requests.

## Roadmap

- [x] ChatGPT, Claude, and Gemini importers
- [x] Markdown export (single + bulk)
- [x] Favorites and platform filters
- [x] Incremental re-import — only new messages are merged
- [x] Auto-detect platform + import straight from the export ZIP
- [x] Dashboard, activity chart, and light/dark themes
- [x] Publish on PyPI (`pip install hadid`)
- [ ] Tags and date-range filters
- [ ] Optional semantic search (fully local)

## Security

Hadid is local-first by design: no cloud, no accounts, no telemetry. The
local web server validates the `Host` header (anti DNS-rebinding) and sends
strict security headers. See [SECURITY.md](SECURITY.md) for the full threat
model and how to report issues.

## Contributing

Contributions are very welcome — especially new platform importers. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
