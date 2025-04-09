from application.betplay_service import BetplayService
from application.fbref_service import FbrefService


def main():

    #fbref_service = FbrefService()
    #fbref_service.get_data_frame()


    service = BetplayService()
    service.leagues_betplay()
    print("✅ Proceso completado")



if __name__ == "__main__":
    main()
