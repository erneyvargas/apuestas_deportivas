import pandas as pd
import requests
from io import StringIO

BASE_URL = "https://www.football-data.co.uk/mmz4281"
LEAGUE_CODE = "E0"  # Premier League

# 10 temporadas: 2015-16 a 2024-25
SEASONS = ["1516", "1617", "1718", "1819", "1920", "2021", "2122", "2223", "2324", "2425"]

COLS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "HC", "AC", "B365H", "B365D", "B365A"]


class FootballDataClient:
    """Cliente para descargar datos históricos de football-data.co.uk"""

    def fetch_season(self, season: str) -> pd.DataFrame:
        url = f"{BASE_URL}/{season}/{LEAGUE_CODE}.csv"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        df = pd.read_csv(StringIO(response.text), usecols=lambda c: c in COLS)
        df["season"] = season
        return df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])

    def fetch_all(self, seasons: list[str] = SEASONS) -> pd.DataFrame:
        frames = []
        for season in seasons:
            try:
                df = self.fetch_season(season)
                frames.append(df)
                print(f"  ✅ Temporada {season}: {len(df)} partidos")
            except Exception as e:
                print(f"  ❌ Error en temporada {season}: {e}")

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
