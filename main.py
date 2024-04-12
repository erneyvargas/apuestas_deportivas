from services.betplay.betplay_service import BetplayService
from services.fbref.fbref_service import FbrefService


def main():
    #BetplayService.leagues_betplay()
    fbref_service = FbrefService()
    fbref_service.get_data_frame()


if __name__ == "__main__":
    main()
