from infrastructure.football_data.football_data_client import FootballDataClient, SEASONS
from infrastructure.persistence.mongo_db_repository import MongoDBRepository
from infrastructure.persistence.mongo_config import MongoConfig

COLLECTION = "historical_matches"
CURRENT_SEASON = SEASONS[-1]  # temporada más reciente, ej: "2425"


class FootballDataService:
    """Descarga y persiste datos históricos de partidos desde football-data.co.uk"""

    def __init__(self, db_name: str):
        self.client = FootballDataClient()
        self.repo = MongoDBRepository(db_name)
        self.db_name = db_name

    def sync(self, seasons: list[str] = SEASONS):
        """Descarga todas las temporadas y reemplaza la colección completa."""
        print(f"📥 Descargando {len(seasons)} temporadas de football-data.co.uk...")
        df = self.client.fetch_all(seasons)

        if df.empty:
            print("❌ No se obtuvieron datos históricos")
            return

        self.repo.save_dataframe_to_collection(COLLECTION, df, clear_collection=True)
        print(f"✅ {len(df)} partidos históricos guardados en '{COLLECTION}'")

    def update_current_season(self, season: str = CURRENT_SEASON):
        """
        Actualiza solo la temporada actual: borra los registros de esa temporada
        en MongoDB y descarga el CSV actualizado de football-data.co.uk.
        Útil para sincronizar resultados de la jornada más reciente.
        """
        print(f"🔄 Actualizando temporada {season}...")
        df = self.client.fetch_season(season)

        if df.empty:
            print(f"❌ No se obtuvieron datos para la temporada {season}")
            return

        db = MongoConfig.get_db(self.db_name)
        db[COLLECTION].delete_many({"season": season})
        db[COLLECTION].insert_many(df.to_dict("records"))
        print(f"✅ {len(df)} partidos de la temporada {season} actualizados")
