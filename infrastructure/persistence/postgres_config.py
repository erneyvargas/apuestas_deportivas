import json
import logging
import os

import psycopg2
import psycopg2.extras
import psycopg2.pool

logger = logging.getLogger(__name__)

# Registra adaptadores JSON globalmente para serializar/deserializar JSONB automáticamente
psycopg2.extras.register_default_jsonb(globally=True, loads=json.loads)


class PostgresConfig:
    POSTGRES_URI = os.getenv(
        "POSTGRES_URI",
        "postgresql://postgres:postgres@localhost:5432/apuestas_deportivas",
    )

    _pool: psycopg2.pool.ThreadedConnectionPool | None = None

    @classmethod
    def get_pool(cls) -> psycopg2.pool.ThreadedConnectionPool:
        if cls._pool is None:
            logger.info("Inicializando pool de conexiones PostgreSQL...")
            cls._pool = psycopg2.pool.ThreadedConnectionPool(2, 10, cls.POSTGRES_URI)
            logger.info("Pool PostgreSQL listo")
        return cls._pool

    @classmethod
    def get_connection(cls) -> psycopg2.extensions.connection:
        return cls.get_pool().getconn()

    @classmethod
    def put_connection(cls, conn: psycopg2.extensions.connection) -> None:
        cls.get_pool().putconn(conn)

    @classmethod
    def get_league_id(cls, league_db: str) -> int:
        """Retorna el id entero de la liga dado su league_db."""
        conn = cls.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM leagues WHERE league_db = %s", (league_db,))
                row = cur.fetchone()
                if row is None:
                    raise ValueError(f"Liga no encontrada en BD: '{league_db}'")
                return row[0]
        finally:
            cls.put_connection(conn)

    @classmethod
    def init_schema(cls) -> None:
        """Ejecuta schema.sql para crear tablas si no existen."""
        schema_path = os.path.join(
            os.path.dirname(__file__), "schema.sql"
        )
        with open(schema_path) as f:
            sql = f.read()

        conn = cls.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            logger.info("Schema PostgreSQL inicializado correctamente")
        except Exception:
            conn.rollback()
            raise
        finally:
            cls.put_connection(conn)
