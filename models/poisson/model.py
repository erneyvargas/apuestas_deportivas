import numpy as np
import pandas as pd
from scipy.stats import poisson


class FootballPoisson:
    """
    Modelo de Poisson para predicción de partidos de fútbol.
    Calcula la fuerza de ataque y defensa de cada equipo (local/visitante)
    y genera distribuciones de probabilidad para todos los resultados posibles.
    """

    MAX_GOALS = 8

    def __init__(self):
        self.avg_home_goals = None
        self.avg_away_goals = None
        self.attack_home = {}
        self.defense_home = {}
        self.attack_away = {}
        self.defense_away = {}

    def fit(self, df: pd.DataFrame):
        """
        Entrena el modelo con las stats de home/away de la temporada.
        df debe tener columnas: Squad, Home_MP, Home_GF, Home_GA, Away_MP, Away_GF, Away_GA
        """
        df = df[df["Home_MP"] > 0].copy()

        total_home_goals = df["Home_GF"].sum()
        total_away_goals = df["Away_GF"].sum()
        total_home_games = df["Home_MP"].sum()
        total_away_games = df["Away_MP"].sum()

        self.avg_home_goals = total_home_goals / total_home_games
        self.avg_away_goals = total_away_goals / total_away_games

        for _, row in df.iterrows():
            team = row["Squad"]
            home_mp = row["Home_MP"]
            away_mp = row["Away_MP"]

            self.attack_home[team] = (row["Home_GF"] / home_mp) / self.avg_home_goals
            self.defense_home[team] = (row["Home_GA"] / home_mp) / self.avg_away_goals
            self.attack_away[team] = (row["Away_GF"] / away_mp) / self.avg_away_goals
            self.defense_away[team] = (row["Away_GA"] / away_mp) / self.avg_home_goals

        return self

    def predict(self, home_team: str, away_team: str) -> dict:
        """Predice probabilidades para un partido dado."""
        if home_team not in self.attack_home or away_team not in self.attack_away:
            missing = home_team if home_team not in self.attack_home else away_team
            raise ValueError(f"Equipo no encontrado en el modelo: '{missing}'")

        xg_home = self.attack_home[home_team] * self.defense_home[away_team] * self.avg_home_goals
        xg_away = self.attack_away[away_team] * self.defense_away[home_team] * self.avg_away_goals

        home_probs = np.array([poisson.pmf(i, xg_home) for i in range(self.MAX_GOALS + 1)])
        away_probs = np.array([poisson.pmf(i, xg_away) for i in range(self.MAX_GOALS + 1)])
        matrix = np.outer(home_probs, away_probs)

        home_win = float(np.sum(np.tril(matrix, -1)))
        draw = float(np.sum(np.diag(matrix)))
        away_win = float(np.sum(np.triu(matrix, 1)))

        over_25 = float(sum(
            matrix[i][j]
            for i in range(self.MAX_GOALS + 1)
            for j in range(self.MAX_GOALS + 1)
            if i + j > 2
        ))
        btts = float(sum(
            matrix[i][j]
            for i in range(1, self.MAX_GOALS + 1)
            for j in range(1, self.MAX_GOALS + 1)
        ))

        return {
            "xg_home": round(xg_home, 2),
            "xg_away": round(xg_away, 2),
            "home_win": round(home_win, 4),
            "draw": round(draw, 4),
            "away_win": round(away_win, 4),
            "over_25": round(over_25, 4),
            "under_25": round(1 - over_25, 4),
            "btts_yes": round(btts, 4),
            "btts_no": round(1 - btts, 4),
        }
