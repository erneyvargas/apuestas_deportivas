import logging
from contextlib import contextmanager
from datetime import datetime
from difflib import SequenceMatcher

from psycopg2.extras import Json

from infrastructure.api_football.api_football_client import APIFootballClient
from infrastructure.persistence.postgres_config import PostgresConfig

logger = logging.getLogger(__name__)


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _season_for(fecha: str) -> int:
    """Año de inicio de la temporada: >= julio → mismo año, < julio → año anterior."""
    dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
    return dt.year if dt.month >= 7 else dt.year - 1


class LineupService:
    """Obtiene alineaciones confirmadas de API-Football y calcula la fortaleza
    del XI comparándolo con el mejor once posible según ratings de temporada.

    Cachea fixture IDs y ratings en PostgreSQL para minimizar llamadas a la API.
    """

    def __init__(self, db_name: str, league_id: int):
        self.client = APIFootballClient()
        self.league_db = db_name
        self.league_id = league_id

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

    def _get_conn(self):
        return PostgresConfig.get_connection()

    def _put_conn(self, conn):
        PostgresConfig.put_connection(conn)

    # ------------------------------------------------------------------ #
    #  Fixture lookup                                                       #
    # ------------------------------------------------------------------ #

    def _find_fixture(self, home: str, away: str, fecha: str) -> dict | None:
        """Busca el fixture en API-Football por fecha y nombres de equipo.
        Usa fuzzy matching (≥ 60% similitud) y cachea el resultado.
        """
        date = fecha[:10]

        cached = self._fixture_cache_get(home, away, date)
        if cached:
            logger.debug("Fixture cache hit — %s vs %s (%s)", home, away, date)
            return cached

        logger.info("Buscando fixture en API-Football — %s vs %s (%s)", home, away, date)
        season = _season_for(fecha)
        fixtures = self.client.get_fixtures_by_date(self.league_id, season, date)
        logger.debug("Fixtures devueltos por API: %d", len(fixtures))

        for f in fixtures:
            fh = f["teams"]["home"]["name"]
            fa = f["teams"]["away"]["name"]
            sim_h = _sim(home, fh)
            sim_a = _sim(away, fa)
            logger.debug("Comparando '%s' vs '%s' (%.0f%%) | '%s' vs '%s' (%.0f%%)",
                         home, fh, sim_h * 100, away, fa, sim_a * 100)
            if sim_h >= 0.6 and sim_a >= 0.6:
                doc = {
                    "home": home, "away": away, "date": date,
                    "fixture_id":   f["fixture"]["id"],
                    "home_team_id": f["teams"]["home"]["id"],
                    "away_team_id": f["teams"]["away"]["id"],
                    "home_api":     fh,
                    "away_api":     fa,
                }
                self._fixture_cache_upsert(doc)
                logger.info("Fixture encontrado: id=%s ('%s' — '%s')",
                            doc["fixture_id"], fh, fa)
                return doc

        logger.warning("Fixture no encontrado para %s vs %s (%s)", home, away, date)
        return None

    def _fixture_cache_get(self, home: str, away: str, date: str) -> dict | None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT home, away, date, fixture_id, home_team_id,
                           away_team_id, home_api, away_api
                    FROM lineup_fixtures_cache
                    WHERE home = %s AND away = %s AND date = %s
                    """,
                    (home, away, date),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
        finally:
            self._put_conn(conn)

    def _fixture_cache_upsert(self, doc: dict) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO lineup_fixtures_cache
                    (home, away, date, fixture_id, home_team_id, away_team_id, home_api, away_api)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (home, away, date) DO UPDATE
                    SET fixture_id   = EXCLUDED.fixture_id,
                        home_team_id = EXCLUDED.home_team_id,
                        away_team_id = EXCLUDED.away_team_id,
                        home_api     = EXCLUDED.home_api,
                        away_api     = EXCLUDED.away_api
                """,
                (
                    doc["home"], doc["away"], doc["date"],
                    doc["fixture_id"], doc["home_team_id"], doc["away_team_id"],
                    doc["home_api"], doc["away_api"],
                ),
            )

    # ------------------------------------------------------------------ #
    #  Player ratings                                                       #
    # ------------------------------------------------------------------ #

    def _get_ratings(self, team_id: int, season: int) -> dict:
        """Devuelve {player_id: rating} cacheado en PostgreSQL."""
        cache_key = f"{team_id}_{season}"

        cached = self._ratings_cache_get(cache_key)
        if cached is not None:
            logger.debug("Ratings cache hit — team_id=%s season=%s (%d jugadores)",
                         team_id, season, len(cached))
            return cached

        logger.info("Fetching ratings — team_id=%s season=%s", team_id, season)
        players = self.client.get_squad_stats(team_id, self.league_id, season)
        ratings = {}
        for p in players:
            pid = p["player"]["id"]
            stats = (p.get("statistics") or [{}])[0]
            r = stats.get("games", {}).get("rating")
            if r:
                ratings[pid] = float(r)

        self._ratings_cache_upsert(cache_key, ratings)
        logger.info("Ratings guardados — team_id=%s: %d jugadores con rating", team_id, len(ratings))
        return ratings

    def _ratings_cache_get(self, key: str) -> dict | None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ratings FROM lineup_ratings_cache WHERE key = %s",
                    (key,),
                )
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            self._put_conn(conn)

    def _ratings_cache_upsert(self, key: str, ratings: dict) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO lineup_ratings_cache (key, ratings)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET ratings = EXCLUDED.ratings
                """,
                (key, Json(ratings)),
            )

    # ------------------------------------------------------------------ #
    #  Strength calculation                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _strength(xi_ids: list, ratings: dict) -> float:
        """Ratio entre la suma de ratings del XI anunciado y el mejor XI posible."""
        if not ratings:
            return 1.0
        xi_total    = sum(ratings.get(pid, 6.5) for pid in xi_ids)
        top11_total = sum(sorted(ratings.values(), reverse=True)[:11])
        return xi_total / top11_total if top11_total else 1.0

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def get_lineup_strength(self, home: str, away: str, fecha: str) -> dict | None:
        if not self.client.enabled:
            logger.debug("API-Football deshabilitada (sin API key)")
            return None

        fixture = self._find_fixture(home, away, fecha)
        if not fixture:
            return None

        lineups = self.client.get_lineups(fixture["fixture_id"])
        if not lineups:
            logger.info("Alineaciones aún no confirmadas — fixture_id=%s", fixture["fixture_id"])
            return None

        season = _season_for(fecha)
        home_ratings = self._get_ratings(fixture["home_team_id"], season)
        away_ratings = self._get_ratings(fixture["away_team_id"], season)

        def _parse(api_name: str) -> tuple:
            for t in lineups:
                if t["team"]["name"] == api_name:
                    ids   = [p["player"]["id"]   for p in t.get("startXI", [])]
                    names = [p["player"]["name"]  for p in t.get("startXI", [])]
                    return ids, names
            return [], []

        home_ids, home_names = _parse(fixture["home_api"])
        away_ids, away_names = _parse(fixture["away_api"])

        if not home_ids or not away_ids:
            logger.warning("No se pudo parsear XI para fixture_id=%s", fixture["fixture_id"])
            return None

        h_str = self._strength(home_ids, home_ratings)
        a_str = self._strength(away_ids, away_ratings)
        logger.info("Fortaleza XI — %s: %.0f%%  |  %s: %.0f%%",
                    home, h_str * 100, away, a_str * 100)

        return {
            "home_strength": h_str,
            "away_strength": a_str,
            "home_xi": home_names,
            "away_xi": away_names,
        }
