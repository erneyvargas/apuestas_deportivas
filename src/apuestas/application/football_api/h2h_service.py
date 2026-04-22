import logging
from contextlib import contextmanager
from datetime import datetime

from psycopg2.extras import Json

from apuestas.infrastructure.football_api import FootballDataOrgClient
from apuestas.infrastructure.persistence import PostgresConfig

logger = logging.getLogger(__name__)


class H2HService:
    """
    Servicio de enfrentamientos directos (H2H).

    Flujo:
    1. Recibe betplay_event_id, home_team y away_team.
    2. Busca en PostgreSQL usando betplay_event_id como clave de caché.
    3. Si existe → retorna el documento cacheado (sin llamada a la API).
    4. Si no existe → consulta football-data.org, construye el documento,
       lo persiste en PostgreSQL y lo retorna.
    """

    def __init__(self, db_name: str):
        self.client = FootballDataOrgClient()
        self._league_id = PostgresConfig.get_league_id(db_name)

    @contextmanager
    def _cursor(self):
        conn = PostgresConfig.get_connection()
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            PostgresConfig.put_connection(conn)

    def get_h2h(
        self,
        betplay_event_id: int,
        home_team: str,
        away_team: str,
        limit: int = 10,
    ) -> dict | None:
        # 1. Verificar caché
        cached = self._find_cached(betplay_event_id)
        if cached:
            logger.debug("H2H cache hit — %s vs %s", home_team, away_team)
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

        # 5. Persistir en PostgreSQL
        self._insert(doc)
        logger.info(
            "H2H guardado — %s vs %s: %d partidos (W%d D%d L%d)",
            home_team, away_team, len(matches), home_wins, draws, away_wins,
        )
        return doc

    # ------------------------------------------------------------------ #
    #  Acceso a datos                                                      #
    # ------------------------------------------------------------------ #

    def _find_cached(self, betplay_event_id: int) -> dict | None:
        conn = PostgresConfig.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT betplay_event_id, home_team, away_team,
                           fetched_at, matches, summary
                    FROM h2h_results
                    WHERE league_id = %s AND betplay_event_id = %s
                    """,
                    (self._league_id, betplay_event_id),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cols = [d[0] for d in cur.description]
                doc = dict(zip(cols, row))
                if isinstance(doc.get("fetched_at"), datetime):
                    doc["fetched_at"] = doc["fetched_at"].isoformat()
                return doc
        finally:
            PostgresConfig.put_connection(conn)

    def _insert(self, doc: dict) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO h2h_results
                    (league_id, betplay_event_id, home_team, away_team,
                     fetched_at, matches, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (league_id, betplay_event_id) DO UPDATE
                    SET home_team  = EXCLUDED.home_team,
                        away_team  = EXCLUDED.away_team,
                        fetched_at = EXCLUDED.fetched_at,
                        matches    = EXCLUDED.matches,
                        summary    = EXCLUDED.summary
                """,
                (
                    self._league_id,
                    doc["betplay_event_id"],
                    doc["home_team"],
                    doc["away_team"],
                    doc["fetched_at"],
                    Json(doc["matches"]),
                    Json(doc["summary"]),
                ),
            )
