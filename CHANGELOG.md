# Changelog

## 1.0.0 - 2026-07-07

### Changed
- Migrated the project from GitLab to GitHub, including repository links,
  documentation links, and GitHub Actions CI.
- Promoted package metadata from Beta to Production/Stable.
- Updated installation and development instructions for the GitHub repository.

### Fixed
- Fixed ruff line-length failures in the realistic CLI export tests.
- Removed stale GitLab-specific reporting guidance from security docs.

### Verified
- Confirmed GitHub Actions CI passes on the pushed workflow.
- Ran a realistic end-to-end smoke test across ChatGPT, Claude, and Gemini
  ZIP exports, auto-detection, incremental re-import, search, Markdown export,
  and direct SQLite count checks.

## 0.4.0 - 2026-07-06

### Added
- End-to-end CLI test suite against realistic synthetic exports:
  branched ChatGPT mappings, system/tool noise, multimodal parts,
  Arabic content, ZIP round-trip, merge-on-reimport, all error paths
- Edge-case tests for importers, FTS quoting, and host validation
- Keyboard accessibility: chips and list items are focusable and
  activatable; visible focus outlines; prefers-reduced-motion support;
  ARIA labels on search and theme controls
- PyPI metadata: project URLs and Beta classifier

### Fixed
- Host validation now handles bracketed IPv6 literals ([::1]) correctly
- Server misconfiguration returns HTTP 500 instead of relying on assert
  (asserts are stripped under `python -O`)

## 0.3.0 - 2026-07-06

### Added
- Import directly from platform export ZIP files (no extracting needed)
- `hadid import auto <file>` detects the platform automatically
- Incremental re-import: only new messages are merged into existing conversations
- Dashboard home in the web app: stat cards + monthly activity chart
- Light / dark theme toggle (persisted)
- `/api/activity` endpoint; `--verbose` flag for debug logging
- SECURITY.md and a documented local-first threat model

### Changed
- Full type annotations across the codebase
- `Archive` is a context manager; used via `with` everywhere
- Web server is threaded (with a lock) and sends security headers
- CI now lints with ruff and tests on Python 3.9, 3.11, and 3.13

### Fixed
- `PRAGMA foreign_keys` is now enabled (ON DELETE CASCADE was silently
  inert before); WAL journal mode enabled for reliability
- Host header validation blocks DNS-rebinding against the local server

## 0.2.0 - 2026-07-06

### Added
- Gemini importer (Google Takeout `MyActivity.json`)
- `hadid export` — export one conversation or `--all` to Markdown
- `hadid favorite` — star conversations; `--favorites` / `--source` filters
- Completely redesigned local web UI: filters, favorites, live stats,
  keyboard shortcuts, search highlighting, per-message copy, `.md` download
- `/api/stats` endpoint
- Automatic schema migration for archives created with 0.1.0

## 0.1.0 - 2026-07-06

- Initial release: ChatGPT and Claude importers, SQLite + FTS5 archive,
  CLI (import / search / list / stats / serve), zero-dependency web UI
