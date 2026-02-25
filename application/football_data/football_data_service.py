from infrastructure.football_data.football_data_client import FootballDataClient, SEASONS
from infrastructure.persistence.mongo_db_repository import MongoDBRepository

COLLECTION = "historical_matches"


class FootballDataService:
    """Descarga y persiste datos históricos de partidos desde football-data.co.uk"""

    def __init__(self, db_name: str):
        self.client = FootballDataClient()
        self.repo = MongoDBRepository(db_name)

    def sync(self, seasons: list[str] = SEASONS):
        print(f"📥 Descargando {len(seasons)} temporadas de football-data.co.uk...")
        df = self.client.fetch_all(seasons)

        if df.empty:
            print("❌ No se obtuvieron datos históricos")
            return

        self.repo.save_dataframe_to_collection(COLLECTION, df, clear_collection=True)
        print(f"✅ {len(df)} partidos históricos guardados en '{COLLECTION}'")
