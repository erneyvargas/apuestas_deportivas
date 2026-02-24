from application.betplay.betplay_service import BetplayService
from application.fbref.fbref_service import FbrefService


def main():

    fbref_service = FbrefService("Estadisticas-de-Premier-League")
    fbref_service.get_data_frame()


    #service = BetplayService()
    #service.leagues_betplay()
    #print("✅ Proceso completado")



if __name__ == "__main__":
    main()
