import pandas as pd
import numpy as np

WINDOW = 5  # últimos N partidos para calcular forma


def _points(result: str, is_home: bool) -> int:
    if result == "H":
        return 3 if is_home else 0
    if result == "A":
        return 0 if is_home else 3
    return 1  # D


def _team_stats(team: str, before_date, df: pd.DataFrame, n: int = WINDOW) -> dict:
    """
    Calcula stats de forma de un equipo en sus últimos N partidos antes de una fecha.
    Retorna dict con goles marcados/recibidos, puntos, y splits home/away.
    """
    mask = (
        ((df["HomeTeam"] == team) | (df["AwayTeam"] == team)) &
        (df["Date"] < before_date)
    )
    recent = df[mask].sort_values("Date").tail(n)

    if recent.empty:
        return {
            "gf5": np.nan, "ga5": np.nan, "pts5": np.nan,
            "home_gf5": np.nan, "home_ga5": np.nan,
            "away_gf5": np.nan, "away_ga5": np.nan,
        }

    gf, ga, pts = [], [], []
    home_gf, home_ga = [], []
    away_gf, away_ga = [], []

    for _, row in recent.iterrows():
        is_home = row["HomeTeam"] == team
        scored = row["FTHG"] if is_home else row["FTAG"]
        conceded = row["FTAG"] if is_home else row["FTHG"]
        gf.append(scored)
        ga.append(conceded)
        pts.append(_points(row["FTR"], is_home))
        if is_home:
            home_gf.append(scored)
            home_ga.append(conceded)
        else:
            away_gf.append(scored)
            away_ga.append(conceded)

    return {
        "gf5":      np.mean(gf),
        "ga5":      np.mean(ga),
        "pts5":     np.mean(pts),
        "home_gf5": np.mean(home_gf) if home_gf else np.nan,
        "home_ga5": np.mean(home_ga) if home_ga else np.nan,
        "away_gf5": np.mean(away_gf) if away_gf else np.nan,
        "away_ga5": np.mean(away_ga) if away_ga else np.nan,
    }


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Construye X (features) e y (target) para todos los partidos históricos.
    Requiere columnas: Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR, B365H, B365D, B365A
    Target: H=0, D=1, A=2
    """
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=True)
    df = df.sort_values("Date").reset_index(drop=True)

    # Eliminar filas sin odds históricas o resultado
    df = df.dropna(subset=["FTR", "B365H", "B365D", "B365A"])

    rows = []
    for _, match in df.iterrows():
        home = match["HomeTeam"]
        away = match["AwayTeam"]
        date = match["Date"]

        hs = _team_stats(home, date, df)
        aws = _team_stats(away, date, df)

        # Saltar si hay demasiados NaN (equipos sin historial suficiente)
        if pd.isna(hs["gf5"]) or pd.isna(aws["gf5"]):
            continue

        rows.append({
            "home_gf5":      hs["gf5"],
            "home_ga5":      hs["ga5"],
            "home_pts5":     hs["pts5"],
            "home_home_gf5": hs["home_gf5"] if not pd.isna(hs["home_gf5"]) else hs["gf5"],
            "home_home_ga5": hs["home_ga5"] if not pd.isna(hs["home_ga5"]) else hs["ga5"],
            "away_gf5":      aws["gf5"],
            "away_ga5":      aws["ga5"],
            "away_pts5":     aws["pts5"],
            "away_away_gf5": aws["away_gf5"] if not pd.isna(aws["away_gf5"]) else aws["gf5"],
            "away_away_ga5": aws["away_ga5"] if not pd.isna(aws["away_ga5"]) else aws["ga5"],
            "odd_h":         float(match["B365H"]),
            "odd_d":         float(match["B365D"]),
            "odd_a":         float(match["B365A"]),
            "result":        0 if match["FTR"] == "H" else (1 if match["FTR"] == "D" else 2),
        })

    features_df = pd.DataFrame(rows)
    X = features_df.drop(columns=["result"])
    y = features_df["result"]
    return X, y


def build_match_features(
    home: str,
    away: str,
    odd_h: float,
    odd_d: float,
    odd_a: float,
    df_history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construye features para un partido futuro (de Betplay) usando el historial disponible.
    Usa todos los partidos disponibles como referencia de forma (sin corte de fecha).
    """
    df_history = df_history.copy()
    df_history["Date"] = pd.to_datetime(df_history["Date"], format="mixed", dayfirst=True)
    future_date = df_history["Date"].max() + pd.Timedelta(days=1)

    hs = _team_stats(home, future_date, df_history)
    aws = _team_stats(away, future_date, df_history)

    return pd.DataFrame([{
        "home_gf5":      hs["gf5"]  if not pd.isna(hs["gf5"])  else 1.5,
        "home_ga5":      hs["ga5"]  if not pd.isna(hs["ga5"])  else 1.5,
        "home_pts5":     hs["pts5"] if not pd.isna(hs["pts5"]) else 1.0,
        "home_home_gf5": hs["home_gf5"] if not pd.isna(hs["home_gf5"]) else hs.get("gf5", 1.5),
        "home_home_ga5": hs["home_ga5"] if not pd.isna(hs["home_ga5"]) else hs.get("ga5", 1.5),
        "away_gf5":      aws["gf5"]  if not pd.isna(aws["gf5"])  else 1.5,
        "away_ga5":      aws["ga5"]  if not pd.isna(aws["ga5"])  else 1.5,
        "away_pts5":     aws["pts5"] if not pd.isna(aws["pts5"]) else 1.0,
        "away_away_gf5": aws["away_gf5"] if not pd.isna(aws["away_gf5"]) else aws.get("gf5", 1.5),
        "away_away_ga5": aws["away_ga5"] if not pd.isna(aws["away_ga5"]) else aws.get("ga5", 1.5),
        "odd_h":         odd_h if odd_h else 2.5,
        "odd_d":         odd_d if odd_d else 3.3,
        "odd_a":         odd_a if odd_a else 2.5,
    }])
