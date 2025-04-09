import json
import time
from infrastructure.config import Config
from application.betplay_league_service import BetplayLeagueService
from infrastructure.api_client import BetplayAPIClient
from infrastructure.persistence.mongo_repository import MongoLeagueRepository

class BetplayService:
    def __init__(self):
        self.db = Config.get_db()
        self.league_service = BetplayLeagueService(repository=MongoLeagueRepository())
        self.api_client = BetplayAPIClient()

    def leagues_betplay(self):
        """Procesa ligas y sus eventos en MongoDB"""
        try:
            self.league_service.process_leagues()  # ✅ Llamada sin argumentos

            collection_leagues = self.db['ligas_betplay']
            leagues = collection_leagues.find({"sport": "FOOTBALL"})

            for league in leagues:
                name_league = league["term_key"]
                print(f"📌 Procesando liga: {name_league}")

                collection = self.db[name_league]
                if name_league not in self.db.list_collection_names():
                    self.db.create_collection(name_league)
                    collection = self.db[name_league]

                df_betplay = self.api_client.get_full_data(league['path_term_id'])
                if df_betplay.empty:
                    print(f"❌ No se encontraron datos para {name_league}")
                    continue

                records = json.loads(df_betplay.T.to_json()).values()
                collection.insert_many(records)
                print(f"✅ Datos insertados para {name_league}")
                time.sleep(2)  # Respetar el rate limit de la API

        except Exception as e:
            print(f"❌ Error en `leagues_betplay`: {e}")
