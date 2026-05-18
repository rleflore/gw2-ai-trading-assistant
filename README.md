# Guild Wars 2 AI Trading Assistant

An AI-powered trading signal generator for Guild Wars 2's Trading Post. Uses local LLMs with RAG (Retrieval-Augmented Generation) to analyze patch notes, community sentiment, and market context to produce actionable buy/sell signals.

## Project Status

**Current Phase:** Phase 2 — LLM / RAG Engine (Steps 1–4 complete)

### Phase 1 — Data Foundation ✅ COMPLETE
- ✅ Project structure, dependencies, config
- ✅ SQLite schema (items, price_snapshots, patch_notes, reddit_posts)
- ✅ GW2 API price collector (async, batched, with backoff)
- ✅ Wiki patch notes collector
- ✅ Reddit collector (public JSON endpoint, no auth required)
- ✅ Unified scheduler + data validation

### Phase 2 — LLM / RAG Engine (In Progress)
- ✅ Ollama setup + llama3:8b model
- ✅ Price context module (pandas market analytics)
- ✅ Document ingestion + chunking pipeline
- ✅ ChromaDB vector store with local embeddings (nomic-embed-text)
- ⬜ GW2 knowledge base (static reference docs)
- ⬜ RAG pipeline (retrieval → prompt → structured output)
- ⬜ Signal ranking & filtering
- ⬜ End-to-end testing

## Quick Start

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Copy env template and fill in Reddit creds (when needed)
copy .env.template .env

# Run all collectors (prices + wiki + reddit, scheduled polling)
python scripts/run_collectors.py

# Validate data health
python scripts/validate_data.py
```

## Project Structure

```
GuildWars2Project/
├── pyproject.toml              # Package config + dependencies
├── .env.template               # Secrets template
├── src/gw2trading/
│   ├── config.py               # Settings (pydantic-settings, loads .env)
│   ├── collectors/
│   │   ├── price_collector.py  # Async GW2 API price fetcher
│   │   ├── wiki_collector.py   # GW2 Wiki patch notes fetcher
│   │   ├── reddit_collector.py # Reddit public JSON collector (no auth)
│   │   └── tracked_items.py    # Item IDs to track (top 20 / top 200)
│   ├── db/
│   │   ├── database.py         # SQLite connection + schema management
│   │   └── schema.sql          # Table definitions
│   └── utils/
│       └── logging.py          # Logging config
├── scripts/
│   ├── run_collectors.py       # Unified scheduler (all collectors)
│   ├── run_price_collector.py  # Price-only entry point (legacy)
│   └── validate_data.py        # Data health check script
├── tests/
└── data/                       # SQLite DB lives here (gitignored)
```

## Tech Stack

- **Python 3.11+**
- **httpx** — Async HTTP client for GW2 API
- **APScheduler** — Timed polling jobs
- **SQLite** — Data storage (WAL mode)
- **pydantic-settings** — Configuration management
- **Ollama** — Local LLM inference (Phase 2)
- **LangChain + ChromaDB** — RAG pipeline (Phase 2)
- **Streamlit** — Dashboard (Phase 3)

## Documentation

Detailed architecture, design decisions, and risk analysis:
```
C:\Obsidian\Main\Guild Wars Project
```

## Attribution

This project uses the Guild Wars 2 API, provided by ArenaNet.
