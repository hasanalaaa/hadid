# Hadid — حديد

**Own your AI conversations. | أرشيفك الخاص لمحادثات الذكاء الاصطناعي**

Hadid is a full-stack web application that imports your conversation history from **ChatGPT, Claude, Gemini, DeepSeek, Grok, and Perplexity**, archives it in one place, and gives you instant full-text search (Arabic + English) with a beautiful bilingual RTL/LTR glassmorphism interface.

تطبيق ويب متكامل يستورد محادثاتك من كل منصات الذكاء الاصطناعي، يؤرشفها بمكان واحد، ويوفر بحث نصي فوري بالعربي والإنجليزي مع واجهة ثنائية اللغة.

## Features | المميزات

- **Import from 6 platforms** — drag & drop any export ZIP/JSON, auto-detected | استيراد من 6 منصات مع كشف تلقائي
- **Instant full-text search** — Arabic & English, with highlighted snippets (⌘K) | بحث فوري مع تظليل النتائج
- **Dashboard** — stat cards, monthly activity chart, per-platform breakdown, word cloud | لوحة تحكم شاملة
- **Auto-tagging by topic** — coding, design, writing, business, learning, life | وسم تلقائي حسب الموضوع
- **Favorites, tags, filters** — organize everything | مفضلة ووسوم وفلاتر
- **Export** — single conversation to Markdown, all as ZIP, full JSON backup & restore | تصدير ونسخ احتياطي كامل
- **Bilingual UI** — Arabic (RTL) / English (LTR), dark / light themes | واجهة عربية/إنجليزية وسمات داكنة/فاتحة

## Tech Stack

- **Frontend:** React 19, Tailwind CSS, Recharts, Framer Motion, lucide-react
- **Backend:** FastAPI (Python), Motor (async MongoDB)
- **Database:** MongoDB with `none`-language text index (Arabic + English full-text search)

## Project structure

```
backend/
├── server.py        # FastAPI app — all /api routes
├── importers.py     # 6 platform parsers + auto-detection
├── tagger.py        # heuristic topic tagger (AR + EN keywords)
├── export_utils.py  # Markdown / Obsidian renderers
└── demo_data.py     # bilingual demo conversations

frontend/src/
├── pages/           # Dashboard, Conversations, ConversationDetail, Import, Settings
├── components/      # Layout, SearchOverlay (⌘K), ConversationRow, PlatformIcon
├── context/         # language + theme provider
└── i18n.js          # AR/EN translations
```

## Running locally

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend
cd frontend
yarn install
yarn start
```

Environment variables: `backend/.env` needs `MONGO_URL` and `DB_NAME`; `frontend/.env` needs `REACT_APP_BACKEND_URL`.

## Getting your export files | ملفات التصدير

| Platform | How to export |
|---|---|
| **ChatGPT** | Settings → Data controls → Export data (ZIP arrives by email) |
| **Claude** | Settings → Privacy → Export data |
| **Gemini** | [Google Takeout](https://takeout.google.com) → My Activity → Gemini (JSON) |
| **DeepSeek** | Settings → Data → Export data |
| **Grok** | xAI settings → Download your data |
| **Perplexity** | Settings → Request data export |

## API overview

| Endpoint | Description |
|---|---|
| `POST /api/import` | Upload export file (ZIP/JSON), auto-detect platform |
| `GET /api/search?q=` | Full-text search with highlighted snippets |
| `GET /api/conversations` | List with source/favorites/tag/title filters + pagination |
| `GET /api/stats` · `/api/activity` · `/api/wordcloud` | Dashboard data |
| `GET /api/export/all` | Download entire archive as Markdown ZIP |
| `GET /api/export/archive` · `POST /api/import/archive` | Full JSON backup / restore |
| `POST /api/autotag` | Topic-tag all conversations |

## License

MIT
