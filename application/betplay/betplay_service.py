from infrastructure.betplay.betplay_api_client import BetplayAPIClient
from infrastructure.persistence.mongo_db_repository import MongoDBRepository


class BetplayService:
    def __init__(self, league_db: str, betplay_path: str):
        self.betplay_path = betplay_path
        self.api_client = BetplayAPIClient()
        self.repository = MongoDBRepository(db_name=league_db)

    def save_league_odds(self):
        """Obtiene y guarda las cuotas de la liga en la colección 'betplay'"""
        print(f"📌 Betplay: {self.betplay_path}")

        df_betplay = self.api_client.get_full_data(self.betplay_path)
        if df_betplay.empty:
            print(f"❌ No se encontraron datos para {self.betplay_path}")
            return

        self.repository.save_dataframe_to_collection(
            collection_name='betplay',
            df=df_betplay,
            clear_collection=True
        )