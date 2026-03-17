import pandas as pd

from infrastructure.persistence.postgres_config import PostgresConfig

# Mapeo de nombres Betplay → FBRef
TEAM_NAME_MAP = {
    "AFC Bournemouth": "Bournemouth",
    "Manchester United": "Manchester Utd",
    "West Ham": "West Ham United",
    "Tottenham": "Tottenham Hotspur",
}

# Mapeo de nombres football-data.co.uk → FBRef
FOOTBALL_DATA_TEAM_MAP = {
    "Man United": "Manchester Utd",
    "Man City": "Manchester City",
    "Tottenham": "Tottenham Hotspur",
    "West Ham": "West Ham United",
    "Wolves": "Wolverhampton Wanderers",
    "Sheffield United": "Sheffield Utd",
    "Leeds": "Leeds United",
    "Nott'm Forest": "Nottingham Forest",
    "Leicester": "Leicester City",
    "Ipswich": "Ipswich Town",
}


def normalize_team(name: str) -> str:
    return TEAM_NAME_MAP.get(name.strip(), name.strip())


def _normalize_fd_team(name: str) -> str:
    return FOOTBALL_DATA_TEAM_MAP.get(name.strip(), name.strip())


def load_historical_matches(db_name: str) -> pd.DataFrame:
    """Carga partidos históricos de football-data.co.uk desde PostgreSQL."""
    conn = PostgresConfig.get_connection()
    try:
        league_id = PostgresConfig.get_league_id(db_name)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT date, home_team, away_team,
                       fthg, ftag, ftr, hc, ac, b365h, b365d, b365a, season
                FROM historical_matches
                WHERE league_id = %s
                ORDER BY date
                """,
                (league_id,),
            )
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    finally:
        PostgresConfig.put_connection(conn)

    if not rows:
        raise RuntimeError(
            "No hay datos históricos. Ejecuta: uv run python sync_historical.py"
        )

    df = pd.DataFrame(rows, columns=cols)

    # Renombrar a los nombres que espera el resto del código
    df = df.rename(columns={
        "date": "Date",
        "home_team": "HomeTeam",
        "away_team": "AwayTeam",
        "fthg": "FTHG",
        "ftag": "FTAG",
        "ftr": "FTR",
        "hc": "HC",
        "ac": "AC",
        "b365h": "B365H",
        "b365d": "B365D",
        "b365a": "B365A",
    })

    for col in ["HomeTeam", "AwayTeam"]:
        df[col] = df[col].apply(_normalize_fd_team)

    df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=True)
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def load_matches(db_name: str) -> pd.DataFrame:
    """Carga el último snapshot de cuotas desde betplay_odds_history."""
    league_id = PostgresConfig.get_league_id(db_name)
    conn = PostgresConfig.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_id AS id, registered_at AS fecha_registro,
                       event_at AS fecha_evento, league_name AS liga,
                       match_name AS partido, odds
                FROM betplay_odds_history
                WHERE league_id = %s
                """,
                (league_id,),
            )
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    finally:
        PostgresConfig.put_connection(conn)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=cols)

    # Expandir columna JSONB `odds` al nivel del DataFrame
    odds_df = pd.json_normalize(df["odds"].tolist())
    df = pd.concat([df.drop(columns=["odds"]), odds_df], axis=1)

    df[["home_team", "away_team"]] = df["partido"].str.split(" - ", expand=True)
    df["home_team"] = df["home_team"].apply(normalize_team)
    df["away_team"] = df["away_team"].apply(normalize_team)

    return df
