from application.football_data.football_data_service import FootballDataService
from infrastructure.persistence.leagues_config_repository import LeaguesConfigRepository


def main():
    leagues = LeaguesConfigRepository().find_active()

    for league in leagues:
        print(f"\n🏆 {league['name']}")
        FootballDataService(db_name=league['league_db']).sync()


if __name__ == "__main__":
    main()
