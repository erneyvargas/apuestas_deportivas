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
    """Normaliza nombres de football-data.co.uk al estándar FBRef"""
    return FOOTBALL_DATA_TEAM_MAP.get(name.strip(), name.strip())


def load_corners_stats(db_name: str) -> pd.DataFrame:
    """
    Carga stats de corners desde MongoDB.
    Usa Performance_Crs (crosses) de las tablas misc de FBRef como proxy
    de corners for/against (FBRef restringe la columna CK a cuentas premium).
    Retorna DataFrame con columnas: Squad, MP, CK_for, CK_against
    """
    db = MongoConfig.get_db(db_name)
    collections = db.list_collection_names()

    col_for = next((c for c in collections if "misc_for" in c), None)
    col_against = next((c for c in collections if "misc_against" in c), None)

    if not col_for or not col_against:
        raise RuntimeError(
            "No se encontraron colecciones misc_for/misc_against. "
            "Ejecuta main.py para scrapearlo desde FBRef."
        )

    df_for = pd.DataFrame(list(db[col_for].find({}, {"_id": 0})))
    df_against = pd.DataFrame(list(db[col_against].find({}, {"_id": 0})))

    # misc_against tiene nombres como "vs Arsenal" → normalizar
    df_against = df_against.copy()
    df_against["Squad"] = df_against["Squad"].str.removeprefix("vs ").str.strip()

    df = pd.DataFrame({
        "Squad": df_for["Squad"],
        "MP": pd.to_numeric(df_for["90s"], errors="coerce"),
        "CK_for": pd.to_numeric(df_for["Performance_Crs"], errors="coerce"),
        "CK_against": pd.to_numeric(
            df_for["Squad"].map(df_against.set_index("Squad")["Performance_Crs"]),
            errors="coerce"
        ),
    }).dropna()

    df["Squad"] = df["Squad"].apply(normalize_team)
    return df


def load_historical_matches(db_name: str) -> pd.DataFrame:
    """Carga partidos históricos de football-data.co.uk desde MongoDB"""
    db = MongoConfig.get_db(db_name)
    df = pd.DataFrame(list(db["historical_matches"].find({}, {"_id": 0})))

    if df.empty:
        raise RuntimeError(
            "No hay datos históricos. Ejecuta: uv run python sync_historical.py"
        )

    for col in ["HomeTeam", "AwayTeam"]:
        df[col] = df[col].apply(_normalize_fd_team)

    return df


def load_home_away_historical(db_name: str) -> pd.DataFrame:
    """
    Calcula stats home/away agregadas por equipo desde partidos históricos.
    Retorna DataFrame con columnas: Squad, Home_MP, Home_GF, Home_GA, Away_MP, Away_GF, Away_GA
    """
    df = load_historical_matches(db_name)
    df["FTHG"] = pd.to_numeric(df["FTHG"], errors="coerce")
    df["FTAG"] = pd.to_numeric(df["FTAG"], errors="coerce")
    df = df.dropna(subset=["FTHG", "FTAG"])

    home = df.groupby("HomeTeam").agg(
        Home_MP=("FTHG", "count"),
        Home_GF=("FTHG", "sum"),
        Home_GA=("FTAG", "sum"),
    ).reset_index().rename(columns={"HomeTeam": "Squad"})

    away = df.groupby("AwayTeam").agg(
        Away_MP=("FTAG", "count"),
        Away_GF=("FTAG", "sum"),
        Away_GA=("FTHG", "sum"),
    ).reset_index().rename(columns={"AwayTeam": "Squad"})

    return home.merge(away, on="Squad")


def load_corners_stats_historical(db_name: str) -> pd.DataFrame:
    """
    Calcula stats de corners reales (HC/AC) por equipo desde partidos históricos.
    Retorna DataFrame con columnas: Squad, MP, CK_for, CK_against
    """
    df = load_historical_matches(db_name)
    df["HC"] = pd.to_numeric(df["HC"], errors="coerce")
    df["AC"] = pd.to_numeric(df["AC"], errors="coerce")
    df = df.dropna(subset=["HC", "AC"])

    home = df.groupby("HomeTeam").agg(
        MP_h=("HC", "count"),
        CK_for_h=("HC", "sum"),
        CK_against_h=("AC", "sum"),
    ).reset_index().rename(columns={"HomeTeam": "Squad"})

    away = df.groupby("AwayTeam").agg(
        MP_a=("AC", "count"),
        CK_for_a=("AC", "sum"),
        CK_against_a=("HC", "sum"),
    ).reset_index().rename(columns={"AwayTeam": "Squad"})

    merged = home.merge(away, on="Squad")
    merged["MP"] = merged["MP_h"] + merged["MP_a"]
    merged["CK_for"] = merged["CK_for_h"] + merged["CK_for_a"]
    merged["CK_against"] = merged["CK_against_h"] + merged["CK_against_a"]

    return merged[["Squad", "MP", "CK_for", "CK_against"]]


def load_home_away(db_name: str) -> pd.DataFrame:
    db = MongoConfig.get_db(db_name)
    col_name = next(c for c in db.list_collection_names() if c.endswith("_home_away"))
    df = pd.DataFrame(list(db[col_name].find({}, {"_id": 0})))
    return df


def load_matches(db_name: str) -> pd.DataFrame:
    db = MongoConfig.get_db(db_name)
    df = pd.DataFrame(list(db["betplay"].find({}, {"_id": 0})))

    df[["home_team", "away_team"]] = df["partido"].str.split(" - ", expand=True)
    df["home_team"] = df["home_team"].apply(normalize_team)
    df["away_team"] = df["away_team"].apply(normalize_team)

    return df
