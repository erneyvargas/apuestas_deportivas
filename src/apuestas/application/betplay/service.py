import logging

from apuestas.infrastructure.betplay import BetplayAPIClient
from apuestas.infrastructure.persistence import PostgresRepository

logger = logging.getLogger(__name__)


class BetplayService:
    def __init__(self, league_db: str, betplay_path: str):
        self.betplay_path = betplay_path
        self.api_client = BetplayAPIClient()
        self.repository = PostgresRepository(league_db=league_db)

    def save_league_odds(self):
        """Obtiene y persiste las cuotas en el historial acumulado."""
        logger.info("Fetching odds — path: %s", self.betplay_path)

        df_betplay = self.api_client.get_full_data(self.betplay_path)
        if df_betplay.empty:
            logger.warning("No se encontraron partidos para path: %s", self.betplay_path)
            return

        logger.info("Partidos obtenidos: %d", len(df_betplay))

        self.repository.save_dataframe_to_collection(
            collection_name='betplay_odds_history',
            df=df_betplay,
            clear_collection=False
        )
