import time
import pandas as pd
from infrastructure.betplay.betplay_api_client import BetplayAPIClient
from infrastructure.persistence.mongo_config import MongoConfig
from infrastructure.persistence.mongo_db_repository import MongoDBRepository


class BetplayService:
    def __init__(self):
        self.db = MongoConfig.get_db()
        self.api_client = BetplayAPIClient()
        self.repository = MongoDBRepository()
    def process_leagues(self):
        """Procesa y guarda las ligas en la base de datos directamente desde DataFrame"""
        leagues_data = self.api_client.fetch_leagues()
        if not leagues_data:
            return False

        # Convertir a DataFrame y filtrar fútbol
        df_leagues = pd.DataFrame(leagues_data)
        df_leagues = df_leagues[df_leagues['sport'] == 'FOOTBALL']

        self.repository.save_dataframe_to_collection(
            collection_name='ligas_betplay',
            df=df_leagues,
            clear_collection=True
        )
        return True

    def leagues_betplay(self):
        """Procesa ligas y sus eventos en MongoDB"""
        self.process_leagues()

        collection_leagues = self.db['ligas_betplay']
        leagues = collection_leagues.find({"sport": "FOOTBALL"})

        for league in leagues:
            name_league = league["termKey"]
            print(f"📌 Procesando liga: {name_league}")

            collection = self.db[name_league]
            if name_league not in self.db.list_collection_names():
                self.db.create_collection(name_league)
                collection = self.db[name_league]

            df_betplay = self.api_client.get_full_data(league['pathTermId'])
            if df_betplay.empty:
                print(f"❌ No se encontraron datos para {name_league}")
                continue

            self.repository.save_dataframe_to_collection(
                collection_name=name_league,
                df=df_betplay,
                clear_collection=False
            )
            time.sleep(2)  # Respetar el rate limit de la API