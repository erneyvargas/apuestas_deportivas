import pandas as pd
from infrastructure.persistence.mongo_config import MongoConfig

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
    """Carga partidos históricos de football-data.co.uk desde MongoDB."""
    db = MongoConfig.get_db(db_name)
    df = pd.DataFrame(list(db["historical_matches"].find({}, {"_id": 0})))

    if df.empty:
        raise RuntimeError(
            "No hay datos históricos. Ejecuta: uv run python sync_historical.py"
        )

    for col in ["HomeTeam", "AwayTeam"]:
        df[col] = df[col].apply(_normalize_fd_team)

    return df


def load_matches(db_name: str) -> pd.DataFrame:
    """Carga partidos actuales desde la colección betplay de MongoDB."""
    db = MongoConfig.get_db(db_name)
    df = pd.DataFrame(list(db["betplay"].find({}, {"_id": 0})))

    df[["home_team", "away_team"]] = df["partido"].str.split(" - ", expand=True)
    df["home_team"] = df["home_team"].apply(normalize_team)
    df["away_team"] = df["away_team"].apply(normalize_team)

    return df
