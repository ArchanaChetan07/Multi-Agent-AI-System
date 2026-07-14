# Multi-Agent AI System

Lightweight orchestrator that routes a task to **web search** and **finance** agents, observes results, and may revise the plan. Works offline in `DEMO_MODE` (default when `GROQ_API_KEY` is missing).

## Architecture

```
task → AgentOrchestrator.plan()
     → route to WebSearchAgent / FinanceAgent tools
     → observe results (+ structured trace)
     → revise if observations are incomplete
     → synthesize answer
```

| Piece | Role |
|-------|------|
| `multi_agent/orchestrator.py` | Plan → route → observe → revise |
| `multi_agent/agents.py` | Explicit `web_search` and `finance` agent roles |
| `multi_agent/tools/` | Demo stubs + optional DuckDuckGo / yfinance |
| `multi_agent/tracing.py` | Structured step events |
| `main.py` | CLI entrypoint |

This repo does **not** require the Phi framework for tests or the default demo path. Optional Groq polishing is available via `--groq-polish` when a key is set.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

For live search/quotes (optional):

```bash
pip install -r requirements-optional.txt
# set DEMO_MODE=0 and GROQ_API_KEY in .env, then:
python main.py --live "Summarize analyst recommendation and share the latest news for NVDA"
```

## Run

```bash
python main.py "Summarize analyst recommendation and share the latest news for NVDA"
python main.py --json "NVDA analyst recommendations and latest news"
```

## Tests

```bash
pytest tests/ -v --tb=short
```

CI runs the same command strictly (no soft-fail).
