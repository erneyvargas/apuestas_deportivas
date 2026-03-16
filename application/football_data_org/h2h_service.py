import logging
from datetime import datetime

from infrastructure.football_data_org.football_data_org_client import FootballDataOrgClient
from infrastructure.persistence.mongo_config import MongoConfig

logger = logging.getLogger(__name__)

COLLECTION = "h2h_results"


class H2HService:
    """
    Servicio de enfrentamientos directos (H2H).

    Flujo:
    1. Recibe betplay_event_id, home_team y away_team.
    2. Busca en MongoDB usando betplay_event_id como clave de caché.
    3. Si existe → retorna el documento cacheado (sin llamada a la API).
    4. Si no existe → consulta football-data.org, construye el documento,
       lo persiste en MongoDB y lo retorna.
    """

    def __init__(self, db_name: str):
        self.client = FootballDataOrgClient()
        self.collection = MongoConfig.get_db(db_name)[COLLECTION]

    def get_h2h(
        self,
        betplay_event_id: int,
        home_team: str,
        away_team: str,
        limit: int = 10,
    ) -> dict | None:
        # 1. Verificar caché
        cached = self.collection.find_one({"betplay_event_id": betplay_event_id})
        if cached:
            logger.debug("H2H cache hit — %s vs %s", home_team, away_team)
            cached.pop("_id", None)
            return cached

        # 2. Consultar API
        logger.info("H2H API fetch — %s vs %s", home_team, away_team)
        try:
            raw_matches = self.client.get_h2h_matches(home_team, away_team, limit=limit)
        except Exception as e:
            logger.error("Error obteniendo H2H (%s vs %s): %s", home_team, away_team, e)
            return None

        # 3. Parsear partidos
        matches = []
        for m in raw_matches:
            matches.append({
                "date": m["utcDate"],
                "home_team": m["homeTeam"]["name"],
                "away_team": m["awayTeam"]["name"],
                "home_goals": m["score"]["fullTime"]["home"],
                "away_goals": m["score"]["fullTime"]["away"],
                "winner": m["score"]["winner"],
            })

        # 4. Calcular resumen
        home_wins = sum(
            1 for m in matches
            if (m["winner"] == "HOME_TEAM" and m["home_team"] == home_team)
            or (m["winner"] == "AWAY_TEAM" and m["away_team"] == home_team)
        )
        away_wins = sum(
            1 for m in matches
            if (m["winner"] == "HOME_TEAM" and m["home_team"] == away_team)
            or (m["winner"] == "AWAY_TEAM" and m["away_team"] == away_team)
        )
        draws = sum(1 for m in matches if m["winner"] == "DRAW")

        doc = {
            "betplay_event_id": betplay_event_id,
            "home_team": home_team,
            "away_team": away_team,
            "fetched_at": datetime.utcnow().isoformat(),
            "matches": matches,
            "summary": {
                "total": len(matches),
                "home_team_wins": home_wins,
                "draws": draws,
                "away_team_wins": away_wins,
            },
        }

        # 5. Persistir en MongoDB
        self.collection.insert_one(doc)
        doc.pop("_id", None)
        logger.info("H2H guardado — %s vs %s: %d partidos (W%d D%d L%d)",
                    home_team, away_team, len(matches), home_wins, draws, away_wins)
        return doc
