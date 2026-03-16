import logging

from infrastructure.football_data.football_data_client import FootballDataClient, SEASONS
from infrastructure.persistence.mongo_db_repository import MongoDBRepository
from infrastructure.persistence.mongo_config import MongoConfig

logger = logging.getLogger(__name__)

COLLECTION = "historical_matches"
CURRENT_SEASON = SEASONS[-1]


class FootballDataService:
    """Descarga y persiste datos históricos de partidos desde football-data.co.uk"""

    def __init__(self, db_name: str):
        self.client = FootballDataClient()
        self.repo = MongoDBRepository(db_name)
        self.db_name = db_name

    def sync(self, seasons: list[str] = SEASONS):
        """Descarga todas las temporadas y reemplaza la colección completa."""
        logger.info("Descargando %d temporadas de football-data.co.uk...", len(seasons))
        df = self.client.fetch_all(seasons)

        if df.empty:
            logger.error("No se obtuvieron datos históricos")
            return

        self.repo.save_dataframe_to_collection(COLLECTION, df, clear_collection=True)
        logger.info("%d partidos históricos guardados en '%s'", len(df), COLLECTION)

    def update_current_season(self, season: str = CURRENT_SEASON):
        """Actualiza solo la temporada actual en MongoDB."""
        logger.info("Actualizando temporada %s...", season)
        df = self.client.fetch_season(season)

        if df.empty:
            logger.error("No se obtuvieron datos para la temporada %s", season)
            return

        db = MongoConfig.get_db(self.db_name)
        deleted = db[COLLECTION].delete_many({"season": season})
        logger.debug("Temporada %s: %d docs eliminados antes de reinsertar", season, deleted.deleted_count)
        db[COLLECTION].insert_many(df.to_dict("records"))
        logger.info("Temporada %s actualizada: %d partidos insertados", season, len(df))
