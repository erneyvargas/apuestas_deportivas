import logging

from apuestas.infrastructure.football_api import FootballDataClient, SEASONS
from apuestas.infrastructure.persistence import PostgresRepository

logger = logging.getLogger(__name__)

COLLECTION = "historical_matches"
CURRENT_SEASON = SEASONS[-1]


class FootballDataService:
    """Descarga y persiste datos históricos de partidos desde football-data.co.uk"""

    def __init__(self, db_name: str):
        self.client = FootballDataClient()
        self.repo = PostgresRepository(db_name)

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
        """Actualiza solo la temporada actual en PostgreSQL."""
        logger.info("Actualizando temporada %s...", season)
        df = self.client.fetch_season(season)

        if df.empty:
            logger.error("No se obtuvieron datos para la temporada %s", season)
            return

        deleted = self.repo.delete_historical_season(season)
        logger.debug("Temporada %s: %d filas eliminadas antes de reinsertar", season, deleted)
        self.repo.save_dataframe_to_collection(COLLECTION, df, clear_collection=False)
        logger.info("Temporada %s actualizada: %d partidos insertados", season, len(df))
