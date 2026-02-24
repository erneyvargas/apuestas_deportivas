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
