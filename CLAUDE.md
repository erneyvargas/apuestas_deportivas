# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start PostgreSQL (required before running)
docker compose up -d

# Run the FastAPI entrypoint (scheduler + HTTP API)
uv run python -m apuestas.entrypoints.api

# One-off historical sync
uv run python -m apuestas.entrypoints.sync

# Train XGBoost model
uv run python -m apuestas.entrypoints.train

# Tests
uv run pytest

# Add a dependency
uv add <package>
```

Environment variables (with defaults):
- `POSTGRES_URI` → `postgresql://postgres:postgres@localhost:5432/apuestas_deportivas`
- `DB_NAME` → `apuestas_deportivas`

## Architecture

Hexagonal/clean architecture under `src/apuestas/`:

```
src/apuestas/
├── entrypoints/     ← CLI/HTTP entry points (api, train, sync)
├── application/     ← Use-case/service layer
│   ├── betplay/           — BetplayService
│   ├── fbref/             — FbrefService
│   ├── football_api/      — FootballDataService, H2HService
│   └── scheduler.py       — apscheduler jobs
├── infrastructure/  ← External integrations
│   ├── betplay/           — Kambi API client
│   ├── fbref/             — FBRef scraper
│   ├── football_api/      — football-data.co.uk (uk_historical) + football-data.org (org_api)
│   ├── api_football/      — api-football.com (RapidAPI)
│   ├── groq/              — LLM explanations
│   ├── telegram/          — notifier + card_generator
│   ├── persistence/       — Postgres pool, repositories, schema.sql
│   └── logging_config.py
└── ml/
    └── xgboost/           — predictor, feature_engineer, data_loader, model, odds_utils
```

Layer dependency rule: `ml → infrastructure`, `application → infrastructure`, `entrypoints → application`. `ml` must not import from `application` (H2HService is injected via `H2HProvider` protocol).

**Data sources:**
- **Betplay (Kambi API)** — `infrastructure/betplay/client.py`: Fetches football leagues and match betting odds from the Kambi sportsbook API (`us1.offering-api.kambicdn.com`). Makes one request for the main match list and separate requests per bet category (both teams to score, double chance, first half, draw no bet, Asian handicap, home/away goals, corners).
- **FBRef** — `infrastructure/fbref/scraper.py`: Scrapes football statistics tables via `pandas.read_html`.
- **football-data.co.uk** — `infrastructure/football_api/uk_historical.py`: Historical season CSVs for model training.
- **football-data.org** — `infrastructure/football_api/org_api.py`: REST API for H2H lookups (rate-limited).

**Persistence:**
- `infrastructure/persistence/postgres_config.py` — PostgreSQL connection pool via `psycopg2`.
- `infrastructure/persistence/postgres_repository.py` — `save_dataframe_to_collection()` converts a pandas DataFrame to records and inserts them into a named PostgreSQL table. Supports optional pre-insert clear.
- `infrastructure/persistence/schema.sql` — PostgreSQL 18 schema, loaded on first container start.

**Data flow (Betplay):**
1. `fetch_leagues()` → list of groups → filter by `sport == FOOTBALL` → save to `ligas_betplay` table
2. For each league: `get_full_data(pathTermId)` → `get_datos_partidos()` merges base match DataFrame with 8 category DataFrames → saved to a per-league-named table

Bet category IDs used in API calls: `11942`, `12220`, `11927`, `11929`, `12319`, `11930`, `11931`, `19260`.
