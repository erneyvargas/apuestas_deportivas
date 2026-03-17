-- Schema PostgreSQL para apuestas_deportivas
-- Compatible con PostgreSQL 18

-- Ligas configuradas (equivalente a config.leagues en MongoDB)
CREATE TABLE IF NOT EXISTS leagues (
    id              SERIAL PRIMARY KEY,
    league_db       VARCHAR(100) NOT NULL UNIQUE,
    term_key        VARCHAR(100),
    league_slug     VARCHAR(100),
    betplay_path    VARCHAR(200),
    name            VARCHAR(200),
    active          BOOLEAN DEFAULT FALSE,
    api_football_id INTEGER
);

-- Snapshot actual de cuotas Betplay (se reemplaza en cada ejecución)
CREATE TABLE IF NOT EXISTS betplay (
    id              BIGSERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    event_id        BIGINT NOT NULL,
    registered_at   TIMESTAMP,
    event_at        TIMESTAMP,
    league_name     VARCHAR(200),
    match_name      VARCHAR(300),
    odds            JSONB,
    UNIQUE (league_id, event_id)
);

-- Historial acumulado de movimientos de cuotas
CREATE TABLE IF NOT EXISTS betplay_odds_history (
    id              BIGSERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    event_id        BIGINT NOT NULL,
    registered_at   TIMESTAMP,
    event_at        TIMESTAMP,
    league_name     VARCHAR(200),
    match_name      VARCHAR(300),
    odds            JSONB
);
CREATE INDEX IF NOT EXISTS idx_betplay_history_lookup
    ON betplay_odds_history (league_id, event_id, registered_at);

-- Partidos históricos de football-data.co.uk
CREATE TABLE IF NOT EXISTS historical_matches (
    id          BIGSERIAL PRIMARY KEY,
    league_id   INTEGER NOT NULL REFERENCES leagues(id),
    date        VARCHAR(20),
    home_team   VARCHAR(200),
    away_team   VARCHAR(200),
    fthg        INTEGER,
    ftag        INTEGER,
    ftr         CHAR(1),
    hc          INTEGER,
    ac          INTEGER,
    b365h       NUMERIC(8, 4),
    b365d       NUMERIC(8, 4),
    b365a       NUMERIC(8, 4),
    season      VARCHAR(10)
);
CREATE INDEX IF NOT EXISTS idx_historical_league
    ON historical_matches (league_id);
CREATE INDEX IF NOT EXISTS idx_historical_season
    ON historical_matches (league_id, season);

-- Caché de enfrentamientos directos (H2H)
CREATE TABLE IF NOT EXISTS h2h_results (
    id               BIGSERIAL PRIMARY KEY,
    league_id        INTEGER NOT NULL REFERENCES leagues(id),
    betplay_event_id BIGINT,
    home_team        VARCHAR(200),
    away_team        VARCHAR(200),
    fetched_at       TIMESTAMP,
    matches          JSONB,
    summary          JSONB
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_h2h_event_league
    ON h2h_results (league_id, betplay_event_id);

-- Caché de fixture IDs de API-Football
CREATE TABLE IF NOT EXISTS lineup_fixtures_cache (
    id           BIGSERIAL PRIMARY KEY,
    home         VARCHAR(200),
    away         VARCHAR(200),
    date         VARCHAR(20),
    fixture_id   INTEGER,
    home_team_id INTEGER,
    away_team_id INTEGER,
    home_api     VARCHAR(200),
    away_api     VARCHAR(200)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_lineup_fixture_key
    ON lineup_fixtures_cache (home, away, date);

-- Caché de ratings de jugadores por equipo/temporada
CREATE TABLE IF NOT EXISTS lineup_ratings_cache (
    id      SERIAL PRIMARY KEY,
    key     VARCHAR(100) NOT NULL UNIQUE,
    ratings JSONB
);
