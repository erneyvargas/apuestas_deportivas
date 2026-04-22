# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start PostgreSQL (required before running)
docker compose up -d

# Run the main pipeline
uv run python main.py

# Add a dependency
uv add <package>
```

Environment variables (with defaults):
- `POSTGRES_URI` → `postgresql://postgres:postgres@localhost:5432/apuestas_deportivas`
- `DB_NAME` → `apuestas_deportivas`

## Architecture

The project follows a hexagonal/clean architecture with two main layers:

```
application/   ← Use-case/service layer
infrastructure/ ← External integrations (API clients, DB, scrapers)
main.py        ← Entry point
```

**Data sources:**
- **Betplay (Kambi API)** — `infrastructure/betplay/betplay_api_client.py`: Fetches football leagues and match betting odds from the Kambi sportsbook API (`us1.offering-api.kambicdn.com`). Makes one request for the main match list and separate requests per bet category (both teams to score, double chance, first half, draw no bet, Asian handicap, home/away goals, corners).
- **FBRef** — `infrastructure/fbref/fbref_data.py`: Scrapes football statistics tables via `pandas.read_html` from the FBRef Premier League page.

**Persistence:**
- `infrastructure/persistence/postgres_config.py` — PostgreSQL connection pool via `psycopg2`.
- `infrastructure/persistence/postgres_repository.py` — `save_dataframe_to_collection()` converts a pandas DataFrame to records and inserts them into a named PostgreSQL table. Supports optional pre-insert clear.
- `infrastructure/persistence/schema.sql` — PostgreSQL 18 schema, loaded on first container start.

**Application services:**
- `BetplayService` — Fetches all football leagues from Betplay, then for each league fetches full match data (merging 8 bet-category DataFrames) and upserts to a per-league PostgreSQL table.
- `FbrefService` — Fetches and prints FBRef DataFrames (currently commented out in `main.py`).

**Data flow (Betplay):**
1. `fetch_leagues()` → list of groups → filter by `sport == FOOTBALL` → save to `ligas_betplay` table
2. For each league: `get_full_data(pathTermId)` → `get_datos_partidos()` merges base match DataFrame with 8 category DataFrames → saved to a per-league-named table

Bet category IDs used in API calls: `11942`, `12220`, `11927`, `11929`, `12319`, `11930`, `11931`, `19260`.
