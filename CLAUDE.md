# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start MongoDB (required before running)
docker compose up -d

# Run the main pipeline
uv run python main.py

# Add a dependency
uv add <package>
```

Environment variables (with defaults):
- `MONGO_URI` → `mongodb://root:pass134@localhost:27017/`
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
- `infrastructure/persistence/mongo_config.py` — MongoDB connection via `pymongo`.
- `infrastructure/persistence/mongo_db_repository.py` — `save_dataframe_to_collection()` converts a pandas DataFrame to records and inserts them into a named MongoDB collection. Supports optional pre-insert clear.

**Application services:**
- `BetplayService` — Fetches all football leagues from Betplay, then for each league fetches full match data (merging 8 bet-category DataFrames) and upserts to a per-league MongoDB collection.
- `FbrefService` — Fetches and prints FBRef DataFrames (currently commented out in `main.py`).

**Data flow (Betplay):**
1. `fetch_leagues()` → list of groups → filter by `sport == FOOTBALL` → save to `ligas_betplay` collection
2. For each league: `get_full_data(pathTermId)` → `get_datos_partidos()` merges base match DataFrame with 8 category DataFrames → saved to a per-league-named collection

Bet category IDs used in API calls: `11942`, `12220`, `11927`, `11929`, `12319`, `11930`, `11931`, `19260`.
