from application.betplay.betplay_service import BetplayService
from application.fbref.fbref_service import FbrefService

LEAGUE_DB = "premier_league"


def main():
    betplay_service = BetplayService(league_term_key=LEAGUE_DB)
    betplay_service.save_league_odds()

    fbref_service = FbrefService(
        league_slug="/09/Estadisticas-de-Premier-League",
        db_name=LEAGUE_DB
    )
    fbref_service.get_data_frame()



if __name__ == "__main__":
    main()
