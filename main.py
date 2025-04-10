from application.betplay.betplay_service import BetplayService


def main():

    #fbref_service = FbrefService()
    #fbref_service.get_data_frame()


    service = BetplayService()
    service.leagues_betplay()
    print("✅ Proceso completado")



if __name__ == "__main__":
    main()
