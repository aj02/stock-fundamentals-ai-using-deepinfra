# fundamentals-ai

> **DISCLAIMER — read first.**
> This project is an **educational and engineering demo**. It is **NOT investment advice** and **NOT a recommendation to buy or sell** any security. The output is a structured summary of publicly available information for analytical study. Markets move on information this system does not see; the analysis can be wrong, stale, or incomplete. Do your own research and consult a SEBI-registered investment adviser before making any financial decision.

A multi-agent fundamental analysis system for Indian equities (NSE/BSE). Given a ticker (e.g. `RELIANCE`, `INFY`, `HDFCBANK`), it orchestrates specialised PydanticAI agents and produces a comprehensive, evidence-linked investment analysis report — financials, valuation, management, risks, and a synthesised bull/bear thesis.

Built as a public showcase of:

- **PydanticAI orchestration-as-code** — the agent graph is just an `asyncio.gather` call you can read in 30 seconds, not a graph DSL.
- **Strict Pydantic v2 typing** end-to-end — every agent input, output, dependency, and API schema is a validated model.
- **A streaming UI** that lets you watch the agents think — tools called, partial results streamed via WebSocket, results cards animating in as each agent completes.

---

## Get running in 3 minutes

> Prerequisite: Docker Desktop with Compose v2.

```bash
git clone https://github.com/your-org/fundamentals-ai.git
cd fundamentals-ai
cp .env.example .env
# Open .env, choose your LLM provider, and paste an API key.
#   LLM_PROVIDER=anthropic  →  set ANTHROPIC_API_KEY
#   LLM_PROVIDER=deepinfra  →  set DEEPINFRA_API_KEY (cheaper, runs Kimi K2)
docker compose up
```

Then open:

- **Frontend** (Next.js 15) — http://localhost:3000
- **Backend** (FastAPI docs) — http://localhost:8000/docs

`docker compose up` brings up five services in dependency order: postgres
(with pgvector), redis, alembic-migrate (one-shot, exits 0 once schema is
current), backend (FastAPI healthchecked), frontend (Next.js healthchecked).
Backend depends on `alembic-migrate: service_completed_successfully`, so the
API literally cannot boot before the schema is up-to-date.

```bash
docker compose ps
# postgres / redis / backend / frontend should all show STATUS=healthy
# alembic-migrate should show Exited (0)
```

> **Port conflicts?** If you already run something on `3000` / `8000` / `5432`
> / `6379`, override the host ports in `.env`:
> ```bash
> POSTGRES_PORT=5434
> REDIS_PORT=6382
> BACKEND_PORT=8002
> FRONTEND_PORT=3002
> ```
> Note: `NEXT_PUBLIC_*` env vars are inlined into the frontend bundle at
> build time, so changing `BACKEND_PORT` requires `docker compose build
> frontend` to re-bake the URL.

---

## Choosing an LLM provider

Toggle in `.env`:

```bash
# Anthropic Claude (Sonnet for analysis agents, Haiku for fast tasks).
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OR — DeepInfra-hosted open models (Kimi K2, etc.) via OpenAI-compat API.
LLM_PROVIDER=deepinfra
DEEPINFRA_API_KEY=...
DEEPINFRA_AGENT_MODEL=moonshotai/Kimi-K2.6
```

| Provider              | Speed (single run) | $ per ticker | Trade-off                                        |
|-----------------------|--------------------|--------------|--------------------------------------------------|
| Anthropic Sonnet 4.6  | ~1–2 min           | ~$0.10       | Polished prose, fastest concurrent throughput.   |
| DeepInfra Kimi K2.6   | ~5–7 min           | ~$0.02       | Reasoning model — slower, much cheaper.          |

The chosen provider's model **must support OpenAI-style tool calling** —
every agent in this repo uses PydanticAI's structured-output pattern, which
under the hood is a forced tool call.

---

## What it does

1. You enter a ticker.
2. The **Coordinator** (plain-Python orchestrator) validates the ticker, opens a run record, and fans out four agents in parallel via `asyncio.gather`:
   - **Financials Agent** — 5-year statements, ratios, evidence-linked qualitative assessment
   - **Valuation Agent** — current multiples vs 5-year median vs peer median
   - **Management Agent** — MD&A + governance extracts from the latest annual report
   - **Risk Agent** — categorised risks (business / financial / regulatory / operational) with severity tags
3. Once those four return, the **Thesis Agent** synthesises a bull case, bear case, and neutral summary — every point cites which prior-agent finding it came from.
4. The UI streams every agent's start, tool calls, and completion over WebSocket. Result cards animate in as each agent finishes.

Architecture deep-dive in [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Tech stack

**Backend** — Python 3.12 · FastAPI · PydanticAI · Anthropic Claude (Sonnet for agents, Haiku for fast tasks) **or** DeepInfra-hosted open models (Kimi K2 etc.) toggled via `LLM_PROVIDER` · PydanticAI's OpenAI provider as configurable fallback · Pydantic v2 · httpx · yfinance · selectolax · pypdf + pdfplumber · Postgres 16 + pgvector · Redis · structlog · pytest · ruff · mypy strict.

**Frontend** — Next.js 15 (App Router) · TypeScript strict · Tailwind v4 · shadcn/ui · lucide-react · Recharts · Framer Motion · TanStack Query · Zod · WebSocket client.

**Infra** — Docker Compose · pgvector/pgvector:pg16 · redis:7-alpine · healthchecks on every service · alembic-migrate one-shot before backend boots.

---

## Why PydanticAI (not LangGraph / LangChain)

The orchestration is a 30-line async function:

```python
financials, valuation, management, risk = await asyncio.gather(
    financials_agent.run(prompt, deps=deps),
    valuation_agent.run(prompt, deps=deps),
    management_agent.run(prompt, deps=deps),
    risk_agent.run(prompt, deps=deps),
    return_exceptions=True,
)
thesis = await thesis_agent.run(synthesis_prompt(...), deps=deps)
```

No graph DSL, no state machine to draw. Pydantic v2 enforces every agent's output shape; PydanticAI provides typed `deps`, `@agent.tool` binding, and a `TestModel` that makes unit-testing agents trivial.

---

## Caching strategy

| Layer                | TTL         | Why                                                        |
|----------------------|-------------|------------------------------------------------------------|
| yfinance responses   | 6h          | Prices/financials don't move that fast intraday for fundamentals work. |
| Screener.in scrapes  | 24h        | Be a polite citizen of someone else's site.                |
| Annual report PDFs   | indefinite  | These don't change after publication; download once.       |
| Full agent run       | 12h         | Re-running the LLM stack on identical inputs is wasteful.  |

Cache layer is explicit and observable — every cache hit/miss is logged with the run_id.

**`POST /analyze` is cache-first by default.** It returns the most recent
completed run for the requested ticker if it's within `CACHE_TTL_REPORT_SECONDS`
(12h). Pass `{"force_refresh": true}` (or click **Refresh analysis** in the UI)
to skip the cache and re-run the agents.

---

## Stopping a run mid-flight (kill switch)

LLM runs are fire-and-forget — they keep consuming tokens even if you close
the browser tab. Three ways to cancel:

- **UI: "Cancel" button** on `/analyze/[ticker]` while the run is live.
- **UI: "Stop all" button in the site header** — works site-wide, on any page.
- **API:** `DELETE /runs/{run_id}` (one run) or `POST /runs/cancel-all`
  (every in-flight run on the backend).

When a run is cancelled, the orchestrator catches `CancelledError`, marks
the DB row as `'cancelled'`, closes the WebSocket, and stops issuing
LLM HTTP calls within seconds. No partial tokens are spent after the cancel.

---

## Data sources & ethics

- **yfinance** — prices and basic financials. Used per Yahoo's terms, no aggressive polling.
- **Screener.in** — additional financials and peer data. The scraper:
  - sends a clear identifying `User-Agent` (`fundamentals-ai/<version>` + project URL) so the host can contact us;
  - is **rate-limited to 1 request per 3 seconds** (configurable via `SCRAPER_MIN_INTERVAL_SECONDS`);
  - **respects `robots.txt`**;
  - caches aggressively (24h) to minimise hits;
  - **degrades gracefully** — if scraping fails, the run continues with partial data and the missing section is marked `unavailable` in the report.
- **Annual reports** — fetched directly from the issuer's investor-relations page or the exchange filing, then parsed locally.

If you operate one of the sites we read from and want us to change anything, please open an issue.

---

## Ticker universe

The autocomplete is backed by a curated **~320 NSE-listed equities**
covering the Nifty 50, Nifty Next 50, broad Nifty 500 representation by
sector, plus a handful of frequently-requested mid/small caps. See
[backend/app/data/tickers_seed.py](./backend/app/data/tickers_seed.py).

Free-text input still works for anything outside the curated list —
yfinance validates the symbol when the orchestrator runs, so e.g.
`POLYCAB`, `KARURVYSYA`, `SUVENPHAR` or any `.NS` / `.BO` ticker not in
the autocomplete will still resolve correctly.

---

## API surface

```
POST /analyze              { ticker, depth, force_refresh? }
                           → { run_id, websocket_url, status_url, cached }
GET  /runs/{run_id}        → { run_id, report }
DELETE /runs/{run_id}      → { cancelled: [run_id] | [] }
POST /runs/cancel-all      → { cancelled: [...] }
GET  /runs                 → { active_run_ids: [...] }
GET  /tickers/search?q=    → { results: TickerInfo[] }
WS   /ws/runs/{run_id}     → streamed RunEvent JSON

GET  /health               → 200 always (cheap liveness)
GET  /ready                → DB + Redis pinged (readiness)
```

Every JSON response carries a top-level `disclaimer` field.

---

## What this is NOT

- Not investment advice, not a recommendation, no buy/sell signals, no price targets, no "score out of 10."
- No portfolio tracking, no watchlist, no paper trading, no user accounts, no auth.
- No news/sentiment, no options, no insider-trading data.
- No multi-ticker comparison — one ticker per analysis (peer numbers appear inside the report; you don't compare two reports).
- No chat / "ask follow-up questions" interface.

These are deliberate scope choices, not roadmap items.

---

## Repository layout

```
backend/
  app/
    api/                    # FastAPI routes
      analyze.py            # POST /analyze + GET /runs + DELETE + cancel-all
      ws.py                 # WS /ws/runs/{run_id}
      tickers.py            # GET /tickers/search
      agents.py             # per-agent dev endpoints (steps 4–7)
      health.py
    agents/                 # PydanticAI agent definitions
      orchestrator.py       # asyncio.gather + partial-failure path
      financials.py / valuation.py / management.py / risk.py / thesis.py
      deps.py               # AgentDeps factory
      llm.py                # Anthropic | DeepInfra model factory
      events.py             # WS event types
    data/                   # data sources
      yfinance_client.py    # async wrapper (cached)
      screener_scraper.py   # selectolax-based, polite, rate-limited
      annual_report.py      # PDF discovery + section extraction
      tickers_seed.py       # curated ~320-stock NSE universe
    services/               # cache, ratios, valuation math, run registry, runs repo
    schemas/                # Pydantic v2 input/output models
    core/                   # config, db, structlog, disclaimer
  tests/
  alembic/                  # async-mode migrations
  scripts/                  # smoke runners
  Dockerfile
  pyproject.toml
web/                        # Next.js 15 App Router
  app/                      # / · /analyze/[ticker] · /report/[run_id] · /about
  components/
    report/                 # tabbed report sections + thesis card
    ui/                     # shadcn-style primitives (button, card, ...)
    agent-activity-panel.tsx
    kill-switch.tsx
  lib/                      # api client, WS hook, Zod schemas, utils
  Dockerfile
docker-compose.yml
.env.example                # documented env keys
README.md
ARCHITECTURE.md
```

---

## License & attribution

TBD. This is a showcase repo; treat the code as reference material rather than a production system.

---

> **Reminder.** Nothing in this repo, its UI, or its output constitutes investment advice. See the disclaimer at the top of this README.
