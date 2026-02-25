from application.betplay.betplay_service import BetplayService
from application.fbref.fbref_service import FbrefService
from infrastructure.persistence.leagues_config_repository import LeaguesConfigRepository


def main():
    leagues = LeaguesConfigRepository().find_active()

    for league in leagues:
        print(f"\n🏆 Liga: {league['name']}")

        BetplayService(league_db=league['league_db'], betplay_path=league['betplay_path']).save_league_odds()

        fbref = FbrefService(
            league_slug=league['league_slug'],
            db_name=league['league_db']
        )
        fbref.get_data_frame()
        fbref.get_passing_data()



if __name__ == "__main__":
    main()
