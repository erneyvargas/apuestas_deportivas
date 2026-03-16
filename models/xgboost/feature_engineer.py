import pandas as pd
import numpy as np

WINDOW = 5
H2H_WINDOW = 5

H2H_DEFAULTS = {
    "h2h_home_win_rate": 0.45,
    "h2h_draw_rate":     0.25,
    "h2h_away_win_rate": 0.30,
    "h2h_home_goals":    1.5,
    "h2h_away_goals":    1.2,
}


def _points(result: str, is_home: bool) -> int:
    if result == "H":
        return 3 if is_home else 0
    if result == "A":
        return 0 if is_home else 3
    return 1


def _team_stats(team: str, before_date, df: pd.DataFrame, n: int = WINDOW) -> dict:
    """Stats de forma de un equipo en sus últimos N partidos antes de una fecha.
    Requiere que df esté ordenado por Date (ascendente).
    """
    mask = (
        ((df["HomeTeam"] == team) | (df["AwayTeam"] == team)) &
        (df["Date"] < before_date)
    )
    recent = df[mask].tail(n)

    if recent.empty:
        return {
            "gf5": np.nan, "ga5": np.nan, "pts5": np.nan,
            "home_gf5": np.nan, "home_ga5": np.nan,
            "away_gf5": np.nan, "away_ga5": np.nan,
        }

    is_home = (recent["HomeTeam"] == team).values
    fthg    = recent["FTHG"].values
    ftag    = recent["FTAG"].values
    ftr     = recent["FTR"].values

    gf  = np.where(is_home, fthg, ftag)
    ga  = np.where(is_home, ftag, fthg)
    pts = np.where(ftr == "H", np.where(is_home, 3, 0),
                   np.where(ftr == "A", np.where(is_home, 0, 3), 1))

    away_m = ~is_home

    return {
        "gf5":      np.mean(gf),
        "ga5":      np.mean(ga),
        "pts5":     np.mean(pts),
        "home_gf5": np.mean(gf[is_home])  if is_home.any()  else np.nan,
        "home_ga5": np.mean(ga[is_home])  if is_home.any()  else np.nan,
        "away_gf5": np.mean(gf[away_m])   if away_m.any()   else np.nan,
        "away_ga5": np.mean(ga[away_m])   if away_m.any()   else np.nan,
    }


def _role_stats(team: str, role: str, before_date, df: pd.DataFrame, n: int = WINDOW) -> dict:
    """Stats en sus últimos N partidos jugados exclusivamente como local o visitante.
    Requiere que df esté ordenado por Date (ascendente).
    """
    if role == "home":
        mask = (df["HomeTeam"] == team) & (df["Date"] < before_date)
    else:
        mask = (df["AwayTeam"] == team) & (df["Date"] < before_date)

    recent = df[mask].tail(n)

    if recent.empty:
        return {"role_gf5": np.nan, "role_ga5": np.nan, "role_pts5": np.nan}

    is_home = role == "home"
    fthg    = recent["FTHG"].values
    ftag    = recent["FTAG"].values
    ftr     = recent["FTR"].values

    gf  = fthg if is_home else ftag
    ga  = ftag if is_home else fthg
    pts = np.where(ftr == "H", 3 if is_home else 0,
                   np.where(ftr == "A", 0 if is_home else 3, 1))

    return {
        "role_gf5":  np.mean(gf),
        "role_ga5":  np.mean(ga),
        "role_pts5": np.mean(pts),
    }


def _h2h_stats(home: str, away: str, before_date, df: pd.DataFrame, n: int = H2H_WINDOW) -> dict:
    """Stats H2H entre home y away expresadas desde la perspectiva de home.
    Requiere que df esté ordenado por Date (ascendente).
    """
    mask = (
        ((df["HomeTeam"] == home) & (df["AwayTeam"] == away)) |
        ((df["HomeTeam"] == away) & (df["AwayTeam"] == home))
    ) & (df["Date"] < before_date)

    recent = df[mask].tail(n)

    if recent.empty:
        return H2H_DEFAULTS.copy()

    home_is_home = (recent["HomeTeam"] == home).values
    fthg = recent["FTHG"].values
    ftag = recent["FTAG"].values
    ftr  = recent["FTR"].values

    hg = np.where(home_is_home, fthg, ftag)
    ag = np.where(home_is_home, ftag, fthg)

    home_wins = int(np.where(home_is_home, ftr == "H", ftr == "A").sum())
    away_wins = int(np.where(home_is_home, ftr == "A", ftr == "H").sum())
    draws     = int((ftr == "D").sum())
    total     = len(recent)

    return {
        "h2h_home_win_rate": home_wins / total,
        "h2h_draw_rate":     draws     / total,
        "h2h_away_win_rate": away_wins / total,
        "h2h_home_goals":    np.mean(hg),
        "h2h_away_goals":    np.mean(ag),
    }


def _h2h_from_api_doc(home_team: str, h2h_doc: dict | None) -> dict:
    if not h2h_doc or not h2h_doc.get("matches"):
        return H2H_DEFAULTS.copy()

    matches = h2h_doc["matches"]
    home_wins = draws = away_wins = 0
    home_goals_list, away_goals_list = [], []

    for m in matches:
        if m["home_team"] == home_team:
            hg, ag = m["home_goals"] or 0, m["away_goals"] or 0
            winner = m["winner"]
            if winner == "HOME_TEAM":   home_wins += 1
            elif winner == "DRAW":      draws += 1
            else:                       away_wins += 1
        else:
            hg, ag = m["away_goals"] or 0, m["home_goals"] or 0
            winner = m["winner"]
            if winner == "AWAY_TEAM":   home_wins += 1
            elif winner == "DRAW":      draws += 1
            else:                       away_wins += 1
        home_goals_list.append(hg)
        away_goals_list.append(ag)

    total = len(matches)
    return {
        "h2h_home_win_rate": home_wins / total,
        "h2h_draw_rate":     draws / total,
        "h2h_away_win_rate": away_wins / total,
        "h2h_home_goals":    np.mean(home_goals_list),
        "h2h_away_goals":    np.mean(away_goals_list),
    }


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Construye X (features) e y (target) para todos los partidos históricos.
    Requiere columnas: Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR, B365H, B365D, B365A
    Target: H=0, D=1, A=2
    """
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=True)
    df = df.sort_values("Date").reset_index(drop=True)
    df = df.dropna(subset=["FTR", "B365H", "B365D", "B365A"])

    rows = []
    # itertuples es ~10x más rápido que iterrows para acceso a columnas
    for match in df.itertuples(index=False):
        home = match.HomeTeam
        away = match.AwayTeam
        date = match.Date

        hs      = _team_stats(home, date, df)
        aws     = _team_stats(away, date, df)
        hs_rol  = _role_stats(home, "home", date, df)
        aws_rol = _role_stats(away, "away", date, df)
        h2h     = _h2h_stats(home, away, date, df)

        if pd.isna(hs["gf5"]) or pd.isna(aws["gf5"]):
            continue

        rows.append({
            "home_gf5":      hs["gf5"],
            "home_ga5":      hs["ga5"],
            "home_pts5":     hs["pts5"],
            "home_home_gf5": hs["home_gf5"] if not pd.isna(hs["home_gf5"]) else hs["gf5"],
            "home_home_ga5": hs["home_ga5"] if not pd.isna(hs["home_ga5"]) else hs["ga5"],
            "home_role_gf5":  hs_rol["role_gf5"]  if not pd.isna(hs_rol["role_gf5"])  else hs["gf5"],
            "home_role_ga5":  hs_rol["role_ga5"]  if not pd.isna(hs_rol["role_ga5"])  else hs["ga5"],
            "home_role_pts5": hs_rol["role_pts5"] if not pd.isna(hs_rol["role_pts5"]) else hs["pts5"],
            "away_gf5":      aws["gf5"],
            "away_ga5":      aws["ga5"],
            "away_pts5":     aws["pts5"],
            "away_away_gf5": aws["away_gf5"] if not pd.isna(aws["away_gf5"]) else aws["gf5"],
            "away_away_ga5": aws["away_ga5"] if not pd.isna(aws["away_ga5"]) else aws["ga5"],
            "away_role_gf5":  aws_rol["role_gf5"]  if not pd.isna(aws_rol["role_gf5"])  else aws["gf5"],
            "away_role_ga5":  aws_rol["role_ga5"]  if not pd.isna(aws_rol["role_ga5"])  else aws["ga5"],
            "away_role_pts5": aws_rol["role_pts5"] if not pd.isna(aws_rol["role_pts5"]) else aws["pts5"],
            "odd_h":         float(match.B365H),
            "odd_d":         float(match.B365D),
            "odd_a":         float(match.B365A),
            **h2h,
            "season":        match.season,
            "result":        0 if match.FTR == "H" else (1 if match.FTR == "D" else 2),
        })

    features_df = pd.DataFrame(rows)
    X = features_df.drop(columns=["result", "season"])
    y = features_df["result"]
    seasons = features_df["season"]
    return X, y, seasons


def build_match_features(
    home: str,
    away: str,
    odd_h: float,
    odd_d: float,
    odd_a: float,
    df_history: pd.DataFrame,
    h2h_doc: dict | None = None,
    future_date=None,
) -> pd.DataFrame:
    """Construye features para un partido futuro (de Betplay) usando el historial.

    Args:
        future_date: fecha de corte precalculada. Si None se calcula internamente.
                     Pasar este valor evita recalcularlo en cada llamada del loop.
    """
    if future_date is None:
        future_date = df_history["Date"].max() + pd.Timedelta(days=1)

    hs      = _team_stats(home, future_date, df_history)
    aws     = _team_stats(away, future_date, df_history)
    hs_rol  = _role_stats(home, "home", future_date, df_history)
    aws_rol = _role_stats(away, "away", future_date, df_history)
    h2h     = _h2h_from_api_doc(home, h2h_doc)

    def _v(val, fallback):
        return val if not pd.isna(val) else fallback

    return pd.DataFrame([{
        "home_gf5":       _v(hs["gf5"],   1.5),
        "home_ga5":       _v(hs["ga5"],   1.5),
        "home_pts5":      _v(hs["pts5"],  1.0),
        "home_home_gf5":  _v(hs["home_gf5"], _v(hs["gf5"], 1.5)),
        "home_home_ga5":  _v(hs["home_ga5"], _v(hs["ga5"], 1.5)),
        "home_role_gf5":  _v(hs_rol["role_gf5"],  _v(hs["gf5"], 1.5)),
        "home_role_ga5":  _v(hs_rol["role_ga5"],  _v(hs["ga5"], 1.5)),
        "home_role_pts5": _v(hs_rol["role_pts5"], _v(hs["pts5"], 1.0)),
        "away_gf5":       _v(aws["gf5"],  1.5),
        "away_ga5":       _v(aws["ga5"],  1.5),
        "away_pts5":      _v(aws["pts5"], 1.0),
        "away_away_gf5":  _v(aws["away_gf5"], _v(aws["gf5"], 1.5)),
        "away_away_ga5":  _v(aws["away_ga5"], _v(aws["ga5"], 1.5)),
        "away_role_gf5":  _v(aws_rol["role_gf5"],  _v(aws["gf5"], 1.5)),
        "away_role_ga5":  _v(aws_rol["role_ga5"],  _v(aws["ga5"], 1.5)),
        "away_role_pts5": _v(aws_rol["role_pts5"], _v(aws["pts5"], 1.0)),
        "odd_h": odd_h if odd_h else 2.5,
        "odd_d": odd_d if odd_d else 3.3,
        "odd_a": odd_a if odd_a else 2.5,
        **h2h,
    }])
