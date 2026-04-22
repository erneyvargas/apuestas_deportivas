import logging

from apuestas.infrastructure.persistence.postgres_config import PostgresConfig

logger = logging.getLogger(__name__)


class LeaguesConfigRepository:
    def save(
        self,
        league_db: str,
        term_key: str,
        league_slug: str,
        name: str,
        betplay_path: str,
    ) -> None:
        """Inserta o actualiza la configuración de una liga."""
        conn = PostgresConfig.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO leagues (league_db, term_key, league_slug, betplay_path, name)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (league_db) DO UPDATE
                        SET term_key     = EXCLUDED.term_key,
                            league_slug  = EXCLUDED.league_slug,
                            betplay_path = EXCLUDED.betplay_path,
                            name         = EXCLUDED.name
                    """,
                    (league_db, term_key, league_slug, betplay_path, name),
                )
            conn.commit()
            logger.info("Config guardada: %s", name)
        except Exception:
            conn.rollback()
            raise
        finally:
            PostgresConfig.put_connection(conn)

    def get_logo_url(self, league_db: str) -> str | None:
        """Retorna el logo_url cacheado en DB, o None si no está guardado."""
        conn = PostgresConfig.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT logo_url, api_football_id FROM leagues WHERE league_db = %s",
                    (league_db,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                logo_url, api_football_id = row
                if logo_url:
                    return logo_url
                # No hay caché — intentar obtenerla de API-Football
                if not api_football_id:
                    return None
                from apuestas.infrastructure.api_football import APIFootballClient
                fetched = APIFootballClient().get_league_logo(api_football_id)
                if fetched:
                    self._cache_logo_url(league_db, fetched, cur)
                    conn.commit()
                return fetched
        except Exception:
            conn.rollback()
            return None
        finally:
            PostgresConfig.put_connection(conn)

    def _cache_logo_url(self, league_db: str, url: str, cur) -> None:
        cur.execute(
            "UPDATE leagues SET logo_url = %s WHERE league_db = %s",
            (url, league_db),
        )

    def find_active(self) -> list[dict]:
        """Retorna solo las ligas con active=True."""
        return self._query("SELECT * FROM leagues WHERE active = TRUE")

    def find_all(self) -> list[dict]:
        """Retorna todas las ligas configuradas."""
        return self._query("SELECT * FROM leagues")

    def _query(self, sql: str) -> list[dict]:
        conn = PostgresConfig.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            PostgresConfig.put_connection(conn)
