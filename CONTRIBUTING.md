# Contributing to Hadid

Thanks for your interest! The most valuable contributions right now:

1. **New importers** (Gemini, Copilot, Mistral...) — add a module in `hadid/importers/` that yields conversation dicts (see `chatgpt.py` for the expected shape) and register it in `hadid/cli.py`.
2. **Real-world export samples** — export formats change; if an import fails, open an issue with the error (never attach private data).
3. **Bug fixes and tests.**

## Development setup

```bash
git clone https://github.com/USERNAME/hadid.git
cd hadid
pip install -e .[dev]
pytest
```

## Guidelines

- Standard library only in runtime code (zero dependencies is a core feature).
- Every importer must have tests with a small synthetic fixture.
- Keep the web UI a single self-contained HTML string — no build step.
