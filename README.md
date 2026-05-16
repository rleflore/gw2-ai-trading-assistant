# Guild Wars 2 AI Trading Assistant

An AI-powered trading signal generator for Guild Wars 2's Trading Post. Uses local LLMs with RAG (Retrieval-Augmented Generation) to analyze patch notes, community sentiment, and market context to produce actionable buy/sell signals.

## Documentation

All project documentation lives in:

```
C:\Obsidian\Main\Guild Wars Project
```

**Read this first** to understand the architecture, design decisions, risk analysis, and project phases.

## Tech Stack

- **Python 3.11+**
- **Ollama** — Local LLM inference (Llama 3 / Mistral)
- **LangChain** — RAG pipeline orchestration
- **ChromaDB** — Vector store
- **Streamlit** — Dashboard
- **SQLite** — Data storage

## Attribution

This project uses the Guild Wars 2 API, provided by ArenaNet.
