"""
Sincroniza datos históricos de football-data.co.uk en PostgreSQL.

Uso:
  uv run python -m apuestas.entrypoints.sync          # descarga completa (10 temporadas)
  uv run python -m apuestas.entrypoints.sync --update # solo actualiza la temporada actual
"""
import sys

from apuestas.application.football_api import FootballDataService
from apuestas.infrastructure.persistence import LeaguesConfigRepository


def main():
    update_only = "--update" in sys.argv
    leagues = LeaguesConfigRepository().find_active()

    for league in leagues:
        print(f"\n🏆 {league['name']}")
        service = FootballDataService(db_name=league['league_db'])

        if update_only:
            service.update_current_season()
        else:
            service.sync()


if __name__ == "__main__":
    main()
