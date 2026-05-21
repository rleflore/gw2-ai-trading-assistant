# Guild Wars 2 AI Trading Assistant

An AI-powered trading signal generator for Guild Wars 2's Trading Post. Uses local LLMs with RAG (Retrieval-Augmented Generation) to analyze patch notes, community sentiment, and market context to produce actionable buy/sell signals.

**Portfolio project demonstrating:** Applied AI Engineering (RAG pipelines, structured output parsing, prompt engineering), data engineering (async collectors, scheduling, ETL), and full-stack development (Streamlit dashboard, desktop overlay).

## Features

- **RAG Pipeline** — Retrieves relevant docs from vector store, builds context-rich prompts, and generates structured trading signals via local LLM
- **Automated Data Collection** — Prices (GW2 API), patch notes (Wiki), community posts (Reddit), all on scheduled intervals
- **Signal Accuracy Tracking** — Validates predictions against actual price movements, tracks model accuracy over time
- **Interactive Dashboard** — Market overview with charts, active signals, signal history, patch analysis, and community buzz
- **Desktop Overlay** — Transparent always-on-top HUD that appears when Guild Wars 2 launches, showing active signals in-game
- **Confidence Calibration** — Multi-source agreement scoring, strict thresholds (≥75% confidence, ≥20% expected move) to minimize false signals

## Quick Start

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Copy env template and fill in Reddit creds (when needed)
copy .env.template .env

# Start Ollama and pull required models
ollama pull llama3:8b
ollama pull nomic-embed-text

# Ingest knowledge base into vector store
python scripts/ingest_knowledge_base.py

# Run all collectors (prices + wiki + reddit + daily RAG pipeline + accuracy checks)
python scripts/run_collectors.py

# Launch the dashboard
streamlit run scripts/run_dashboard.py

# Validate data health
python scripts/validate_data.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA COLLECTION                          │
│  GW2 API (15min/1hr) │ Wiki (1hr) │ Reddit (1hr)           │
└────────────┬──────────────┬──────────────┬──────────────────┘
             │              │              │
             ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                           │
│  SQLite (prices, patches, posts, signals)                   │
│  ChromaDB (embeddings for RAG retrieval)                    │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ▼                                ▼
┌──────────────────────────┐    ┌─────────────────────────────┐
│     RAG PIPELINE         │    │     SIGNAL VALIDATION       │
│  Retrieve → Prompt →     │    │  Check expired signals vs   │
│  LLM (llama3:8b) →      │    │  actual price movements     │
│  Parse → Rank → Store    │    │  (daily at 11 AM)           │
└────────────┬─────────────┘    └─────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                      OUTPUT LAYER                            │
│  Streamlit Dashboard │ Desktop Overlay (tkinter HUD)        │
└─────────────────────────────────────────────────────────────┘
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
│   │   ├── reddit_collector.py # Reddit public JSON collector
│   │   ├── datawars2_collector.py # Historical price backfill
│   │   └── tracked_items.py    # Item IDs to track (top 20 / top 200)
│   ├── analysis/
│   │   ├── price_context.py    # Market analytics (pandas)
│   │   ├── signal_ranker.py    # Signal filtering, ranking & DB storage
│   │   └── accuracy_tracker.py # Validates predictions vs actual outcomes
│   ├── db/
│   │   ├── database.py         # SQLite connection + schema management
│   │   └── schema.sql          # Table definitions
│   ├── rag/
│   │   ├── ingestion.py        # Document chunking
│   │   ├── vectorstore.py      # ChromaDB wrapper (nomic-embed-text)
│   │   ├── models.py           # Pydantic schemas (TradingSignal, PipelineOutput)
│   │   ├── prompts.py          # Prompt templates with confidence calibration
│   │   └── pipeline.py         # RAG orchestration
│   ├── dashboard/
│   │   ├── app.py              # Streamlit main app + navigation
│   │   └── views/
│   │       ├── market.py       # Market overview (prices, charts)
│   │       ├── signals.py      # Trading signals + accuracy stats + community buzz
│   │       └── patches.py      # Patch analysis (market-relevant only)
│   └── utils/
│       └── logging.py          # Logging config
├── scripts/
│   ├── run_collectors.py       # Unified scheduler (collectors + RAG + accuracy)
│   ├── run_pipeline.py         # Manual RAG pipeline trigger
│   ├── run_dashboard.py        # Streamlit entry point
│   ├── signal_overlay.py       # Desktop overlay (transparent HUD)
│   ├── watch_gw2.pyw          # GW2 process watcher (launches overlay)
│   ├── backfill_history.py     # Historical backfill + cleanup
│   ├── ingest_knowledge_base.py # Embed knowledge base into ChromaDB
│   └── validate_data.py        # Data health check
├── data/
│   ├── knowledge_base/         # Static GW2 reference docs for RAG
│   ├── chromadb/               # Vector store (gitignored)
│   └── gw2trading.db           # SQLite DB (gitignored)
└── tests/
```

## Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.11+ |
| LLM | Ollama (llama3:8b, local inference) |
| Embeddings | nomic-embed-text (768-dim, local) |
| Vector Store | ChromaDB |
| Database | SQLite (WAL mode) |
| HTTP | httpx (async) |
| Scheduling | APScheduler |
| Validation | Pydantic v2 |
| Dashboard | Streamlit + Plotly |
| Desktop Overlay | tkinter |
| Config | pydantic-settings |

## Key Design Decisions

- **Local-first** — All inference runs locally via Ollama. No API keys, no cloud costs, no rate limits.
- **Conservative signals** — High confidence threshold (≥75%) and minimum expected move (≥20%) to reduce false positives. The model is told to produce zero signals when uncertain.
- **Automated validation** — Signals are automatically checked against actual price data after their time horizon expires. This creates a feedback loop for measuring model quality.
- **Market relevance filtering** — Patch notes are filtered by keyword before triggering the pipeline. Non-market patches trigger a generic "daily scan" instead.
- **Tax-aware** — The 15% TP tax is baked into the prompt and the ranker threshold, so signals only fire for moves large enough to be profitable.

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Top 20 prices | Every 15 min | High-frequency tracking of most traded items |
| Top 200 prices | Every 1 hour | Broader market coverage |
| Wiki patch notes | Every 1 hour | Detect new game updates |
| Reddit posts | Every 1 hour | Community sentiment |
| RAG pipeline | Daily 10 AM | Generate trading signals |
| Accuracy check | Daily 11 AM | Validate expired signals |

## Attribution

This project uses the Guild Wars 2 API, provided by ArenaNet.
