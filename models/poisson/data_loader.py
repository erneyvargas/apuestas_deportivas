import pandas as pd
from infrastructure.persistence.mongo_config import MongoConfig

# Mapeo de nombres Betplay → FBRef
TEAM_NAME_MAP = {
    "AFC Bournemouth": "Bournemouth",
    "Manchester United": "Manchester Utd",
    "West Ham": "West Ham United",
    "Tottenham": "Tottenham Hotspur",
}


def normalize_team(name: str) -> str:
    return TEAM_NAME_MAP.get(name.strip(), name.strip())


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
