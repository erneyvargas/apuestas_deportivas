import logging
import math
from contextlib import contextmanager
from typing import List, Tuple

import pandas as pd
from psycopg2.extras import Json, execute_values

from infrastructure.persistence.postgres_config import PostgresConfig

logger = logging.getLogger(__name__)

# Columnas fijas de la tabla betplay (nombres del DataFrame → columnas SQL renombradas)
# DataFrame: id, fecha_registro, fecha_evento, liga, partido
# SQL:       event_id, registered_at, event_at, league_name, match_name
_BETPLAY_BASE = {"id", "fecha_registro", "fecha_evento", "liga", "partido"}

# Mapeo de columnas del DataFrame (football-data.co.uk) a columnas SQL
_HISTORICAL_COL_MAP = {
    "Date": "date",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "FTHG": "fthg",
    "FTAG": "ftag",
    "FTR": "ftr",
    "HC": "hc",
    "AC": "ac",
    "B365H": "b365h",
    "B365D": "b365d",
    "B365A": "b365a",
    "season": "season",
}


def _clean(val):
    """Convierte NaN/None a None para compatibilidad con SQL."""
    if val is None:
        return None
    try:
        if math.isnan(float(val)):
            return None
    except (TypeError, ValueError):
        pass
    return val


class PostgresRepository:
    """Repositorio PostgreSQL para persistencia de datos del proyecto."""

    def __init__(self, league_db: str):
        self.league_db = league_db
        self._league_id = PostgresConfig.get_league_id(league_db)

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

    # ------------------------------------------------------------------ #
    #  Interfaz pública                                                   #
    # ------------------------------------------------------------------ #

    def save_dataframe_to_collection(
        self,
        collection_name: str,
        df: pd.DataFrame,
        clear_collection: bool = True,
    ) -> Tuple[bool, int]:
        try:
            if df.empty:
                logger.warning("DataFrame vacío recibido para '%s'", collection_name)
                return True, 0

            if collection_name == "betplay_odds_history":
                count = self._save_betplay(df, clear_collection)
            elif collection_name == "historical_matches":
                count = self._save_historical_matches(df, clear_collection)
            else:
                logger.warning("Colección desconocida: '%s'", collection_name)
                return False, 0

            logger.info("'%s' — %d filas insertadas", collection_name, count)
            return True, count
        except Exception as e:
            logger.error("Error guardando en '%s': %s", collection_name, e, exc_info=True)
            return False, 0

    def ensure_index(self, collection_name: str, keys: List[Tuple[str, int]]) -> None:
        """No-op: los índices ya están definidos en schema.sql."""

    def delete_historical_season(self, season: str) -> int:
        """Elimina los partidos históricos de una temporada específica."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM historical_matches WHERE league_id = %s AND season = %s",
                (self._league_id, season),
            )
            deleted = cur.rowcount
        logger.debug("Temporada %s: %d filas eliminadas de historical_matches", season, deleted)
        return deleted

    # ------------------------------------------------------------------ #
    #  Handlers por tabla                                                  #
    # ------------------------------------------------------------------ #

    def _save_betplay(self, df: pd.DataFrame, clear: bool) -> int:
        rows = df.to_dict("records")
        values = []
        for row in rows:
            base = {k: _clean(row.get(k)) for k in _BETPLAY_BASE}
            odds = {
                k: _clean(v)
                for k, v in row.items()
                if k not in _BETPLAY_BASE
            }
            values.append((
                base["id"],
                self._league_id,
                base["fecha_registro"],
                base["fecha_evento"],
                base["liga"],
                base["partido"],
                Json(odds),
            ))

        with self._cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO betplay_odds_history
                    (event_id, league_id, registered_at, event_at, league_name, match_name, odds)
                VALUES %s
                ON CONFLICT (event_id) DO UPDATE
                    SET league_id     = EXCLUDED.league_id,
                        registered_at = EXCLUDED.registered_at,
                        event_at      = EXCLUDED.event_at,
                        league_name   = EXCLUDED.league_name,
                        match_name    = EXCLUDED.match_name,
                        odds          = EXCLUDED.odds
                """,
                values,
                page_size=500,
            )
        return len(values)

    def _save_historical_matches(self, df: pd.DataFrame, clear: bool) -> int:
        df = df.rename(columns=_HISTORICAL_COL_MAP)
        rows = df.to_dict("records")

        values = [
            (
                self._league_id,
                _clean(row.get("date")),
                _clean(row.get("home_team")),
                _clean(row.get("away_team")),
                _clean(row.get("fthg")),
                _clean(row.get("ftag")),
                _clean(row.get("ftr")),
                _clean(row.get("hc")),
                _clean(row.get("ac")),
                _clean(row.get("b365h")),
                _clean(row.get("b365d")),
                _clean(row.get("b365a")),
                _clean(row.get("season")),
            )
            for row in rows
        ]

        with self._cursor() as cur:
            if clear:
                cur.execute(
                    "DELETE FROM historical_matches WHERE league_id = %s",
                    (self._league_id,),
                )

            execute_values(
                cur,
                """
                INSERT INTO historical_matches
                    (league_id, date, home_team, away_team,
                     fthg, ftag, ftr, hc, ac, b365h, b365d, b365a, season)
                VALUES %s
                """,
                values,
                page_size=500,
            )
        return len(values)
