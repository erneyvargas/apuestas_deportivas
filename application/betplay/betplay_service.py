import pandas as pd
from infrastructure.betplay.betplay_api_client import BetplayAPIClient
from infrastructure.persistence.mongo_db_repository import MongoDBRepository


class BetplayService:
    def __init__(self, league_term_key: str):
        self.league_term_key = league_term_key
        self.api_client = BetplayAPIClient()
        self.repository = MongoDBRepository(db_name=league_term_key)

    def save_league_odds(self):
        """Obtiene y guarda las cuotas de la liga en la colección 'betplay'"""
        leagues_data = self.api_client.fetch_leagues()
        if not leagues_data:
            print("❌ No se pudieron obtener las ligas de Betplay")
            return

        df_leagues = pd.DataFrame(leagues_data)
        league = df_leagues[df_leagues['termKey'] == self.league_term_key]

        if league.empty:
            print(f"❌ Liga '{self.league_term_key}' no encontrada en Betplay")
            return

        path_term_id = league.iloc[0]['pathTermId']
        print(f"📌 Procesando: {self.league_term_key}")

        df_betplay = self.api_client.get_full_data(path_term_id)
        if df_betplay.empty:
            print(f"❌ No se encontraron datos para {self.league_term_key}")
            return

        self.repository.save_dataframe_to_collection(
            collection_name='betplay',
            df=df_betplay,
            clear_collection=True
        )