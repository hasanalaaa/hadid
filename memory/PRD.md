# Hadid (حديد) — PRD

## Original Problem Statement
User uploaded `hadid-main.rar` — a Python CLI tool + minimal local web server ("Hadid": imports AI conversation exports from ChatGPT/Claude/Gemini/DeepSeek/Grok/Perplexity into SQLite FTS5, CLI search, local web UI). User asked (Arabic/Iraqi): full audit, fix all issues, improve old features, and per clarification answers:
1. Convert to a FULL web app (React + FastAPI)
2. Fix everything + add new features + improve old ones
3. Agent chooses best features; REMOVE anything payment/money/PayPal related
4. Deliver as downloadable ZIP + upload to GitHub (user directed to "Save to GitHub" button)

## Audit Findings (original project)
- Well-written core, but CLI-only UX; web UI was a single static page over stdlib http.server (loopback only)
- Only payment-related content found: `pro_subscriptions.json` mention in perplexity importer docstring — removed
- Features dropped in web conversion (not applicable server-side): file encryption (crypto.py), folder watcher, semantic embeddings (needs sentence-transformers), plugin loader, CLI

## Architecture (new)
- **Backend**: FastAPI + Motor (async MongoDB) at /app/backend
  - `server.py` — all /api routes; `importers.py` — 6 platform parsers + auto-detect; `tagger.py` — AR+EN topic tagger; `export_utils.py` — MD/Obsidian renderers; `demo_data.py` — 9 bilingual demo conversations
  - MongoDB: `conversations` (uuid _id, source+source_id unique idx, tags array, favorite, message_count), `messages` (conversation_id, idx, content_hash, text index default_language="none" for AR+EN search)
  - Incremental import: content-hash dedupe (identical→skip, prefix→append, diverged→reinsert)
- **Frontend**: React 19 + Tailwind + Recharts + framer-motion + sonner + react-icons
  - Bilingual AR (default, RTL) / EN via context + i18n.js; dark (default) / light themes; Cairo/Tajawal/JetBrains Mono fonts; glassmorphism "Crystal" design with ember-orange accent (design_guidelines.json)
  - Pages: Dashboard (bento stats/chart/sources/wordcloud/recent), Conversations (filters/pagination), ConversationDetail (chat bubbles, copy, tags, export, delete), ImportPage (dropzone + how-to), Settings (lang/theme, exports, restore, autotag, danger zone)
  - ⌘K SearchOverlay with debounced search + «»→<mark> highlights

## What's Implemented (2026-06 / session 1)
- All API endpoints: import (multipart, auto-detect), demo, conversations CRUD+filters+pagination, favorite, tags CRUD, search (text index + regex fallback, snippets), stats, activity, wordcloud, export (single MD, all-ZIP, archive JSON), import/archive restore, autotag, clear archive
- Full bilingual frontend with all pages, data-testids everywhere
- Testing: 31/31 backend pytest pass (serial `-n 0`; pytest.ini mandates -n 2 which races on the stateful clear test — do NOT modify pytest.ini per its own note); frontend 100% via testing agent (iteration_1.json)
- Fixed HIGH issue: clipboard writeText wrapped in try/catch + execCommand fallback
- Deliverable ZIP: /app/frontend/public/hadid-project.zip (507KB, excludes node_modules/.git) — downloadable at {REACT_APP_BACKEND_URL}/hadid-project.zip
- Test fixtures: /app/tests/fixtures/chatgpt_sample.json, claude_sample.json

## Backlog / Next
- P1: Search results pagination + consistent {items,total} shape; date-range filters in UI (backend list supports date_from/date_to? — NOT ported, only source/fav/tag/q)
- P1: Semantic search (optional, via embeddings) — was optional in original
- P2: Obsidian/Logseq export formats in UI (backend supports obsidian via ?format=)
- P2: Optional auth if user ever wants multi-user / protected wipe endpoint
- P2: Recharts initial-render width warning (cosmetic console noise)

## Notes
- No auth (user never requested); DELETE /api/archive guarded only by confirm modal
- Demo data loaded: 9 conversations / 26 messages
