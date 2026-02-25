"""
Sincroniza datos históricos de football-data.co.uk en MongoDB.

Uso:
  uv run python sync_historical.py          # descarga completa (10 temporadas)
  uv run python sync_historical.py --update # solo actualiza la temporada actual
"""
import sys

from application.football_data.football_data_service import FootballDataService
from infrastructure.persistence.leagues_config_repository import LeaguesConfigRepository


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
