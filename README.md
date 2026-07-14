![CI](https://github.com/ArchanaChetan07/Multi-Agent-AI-System/actions/workflows/ci.yml/badge.svg)

Multi-agent task orchestrator — plan → route → observe → revise loop across finance and web-search tasks. Python, structured tracing, DEMO_MODE offline stubs.

**Deterministic CI/demo harness:** **96.9% task completion** — **90.3% routing accuracy** — **0.0% revision rate** (DEMO stubs always return populated observations) — **~0.0001s avg latency (DEMO_MODE)** — **24 tests passing**. These are reproducible harness results, not live-LLM performance.

```bash
docker compose up --build
# DEMO_MODE=1 by default — no API key required
# Or: DEMO_MODE=1 python scripts/batch_eval.py
```

## Overview

This repo is a compact, framework-light multi-agent orchestrator. A natural-language task is decomposed into specialized **Finance** and/or **Web Search** agent steps, observations are collected, the plan is revised when tools return empty signals, and a structured answer is emitted with a full execution trace.

It is designed to stay green in CI without live API keys (`DEMO_MODE=1`).

## Orchestrator Design

Pipeline: **plan → route → observe → revise → synthesize**.

| Stage | What happens |
|---|---|
| **Plan** | Keyword/intent scan of the task text → ordered list of agent steps |
| **Route** | Each step is dispatched to `FinanceAgent` or `WebSearchAgent` |
| **Observe** | Tool outputs (price/recommendation or search hits) appended to the run |
| **Revise** | If finance lacks a symbol or web search lacks hits (or observations are empty), the planner schedules fallback steps and re-executes |
| **Synthesize** | Observations assembled into a final answer string |

**How routing chooses finance vs web-search** (`AgentOrchestrator.plan`):

- **Finance path** when the text contains triggers such as `stock`, `analyst`, `recommendation`, `price`, `finance`, `fundament`, `ticker`, or known tickers (`NVDA`, `AAPL`, `MSFT`, …).
- **Web-search path** when the text contains `news`, `latest`, `search`, `web`, `summarize`, *or* when no finance step was planned (default).
- **Both** (finance then web-search) when finance *and* news/search triggers are present.

**Honest failure pattern:** keyword routing misroutes general-knowledge questions that merely *mention* finance tokens (e.g. “historical **price** of art auctions”, “**MSFT** Excel tips”, “restaurant **recommendation**”). Those cases are included in the batch eval and pull routing accuracy below 100%.

## Results

Measured with the deterministic `DEMO_MODE=1` CI harness via `python scripts/batch_eval.py` (N=32 labeled tasks: finance, web-search, dual-path, adversarial, plus one empty-task failure case). Completion, routing, and latency below describe synthetic local tool responses; they are not live-LLM or live-service measurements.

| Metric | DEMO_MODE | Notes |
|---|---|---|
| Task completion rate | **96.9%** (31/32) | Empty/whitespace task correctly rejected |
| Routing accuracy | **90.3%** (28/31 scored) | 3 adversarial keyword misroutes |
| Revision rate | **0.0%** | DEMO stubs always return symbol + hits; revise still covered by unit tests |
| Avg revisions / run | **0.0** | Same |
| Avg end-to-end latency | **~0.0001 s** | Local DEMO stubs |
| Automated tests | **24 passed** | `pytest tests/` |

Full dump: [`artifacts/batch_metrics.json`](artifacts/batch_metrics.json).

Live-LLM/API mode is supported but **not measured** here. A genuine live validation attempt on 2026-07-14 produced no publishable metrics: Groq rejected the configured credential with HTTP 401, DuckDuckGo returned HTTP 202 rate limiting, and the local yfinance path hit a NumPy 2.x/native-extension ABI mismatch. The application then used its documented deterministic fallbacks, so those timings were discarded rather than reported as live results. Optional Groq, yfinance, and DuckDuckGo paths remain available outside `DEMO_MODE`; `scripts/batch_eval.py --live` labels an artifact `LIVE_WITH_DEMO_FALLBACK` when it detects fallback data.

## Known Limitations

- The planner uses substring keyword matching rather than semantic intent classification. Non-finance requests containing finance-trigger substrings such as `MSFT`, `price`, or `recommendation` can be routed to the Finance agent.
- The included adversarial tasks `adv-00` through `adv-02` exercise these failure patterns (for example, MSFT Excel tips, historical art-auction prices, and restaurant recommendations). They account for the three documented misroutes and the 90.3% DEMO_MODE routing accuracy in [`artifacts/batch_metrics.json`](artifacts/batch_metrics.json).
- Live tools currently fall back to deterministic demo results when dependencies, credentials, rate limits, or services fail. A requested live run must not be treated as a measured live run unless its artifact reports `mode: "LIVE"` and `live_fallback_detected: false`.
- The `~0.0001 s` latency is only the local deterministic demo harness. It says nothing about production network, provider, or LLM latency.

## Tracing / Observability

`Tracer` records structured events on every run:

| Kind | Meaning |
|---|---|
| `start` | Task received |
| `plan` | Decomposed steps |
| `route` | Agent selected + objective |
| `observe` | Tool/agent observation summary |
| `revise` | Plan rewritten after empty/missing signals |
| `finish` | Answer synthesized |
| `error` / `route_error` | Empty task or unknown role |

## How to Run

### Docker (recommended)

```bash
docker compose up --build
# writes artifacts/batch_metrics.json from the eval service
```

One-shot task demo:

```bash
docker compose run --rm demo "What is the stock price of AAPL?"
```

### Local

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
set DEMO_MODE=1
python main.py "Summarize analyst recommendation and share the latest news for NVDA"
python scripts/batch_eval.py
```

## Tests

```bash
set DEMO_MODE=1
pytest tests/ -v
```

Includes original orchestrator/tool tests plus batch-eval coverage for completion-rate and routing-accuracy helpers.

## Tech Stack

- Python 3.10+
- In-repo `AgentOrchestrator` (no heavy agent SDK required for DEMO/CI)
- Deterministic DEMO stubs for finance + web search
- Optional live: yfinance, DuckDuckGo, Groq (see `requirements-optional.txt`)
- pytest, GitHub Actions, Docker Compose

## License

See repository license file if present.
