import numpy as np
import pandas as pd
from scipy.stats import poisson


class CornersPoisson:
    """
    Modelo de Poisson para predicción de corners.
    Usa corner kicks for/against por equipo (de FBRef passing stats)
    para estimar xCorners de cada equipo y calcular P(total > N.5).
    """

    MAX_CORNERS = 25
    # Media real de corners por equipo por partido en PL (~5.25 = 10.5 totales).
    # Se usa para calibrar la salida, ya que el proxy de entrada (cruces) está
    # en unidades distintas. Los factores ataque/defensa son adimensionales.
    CORNERS_PER_GAME = 5.25

    def __init__(self):
        self.avg_corners = None
        self.attack = {}
        self.defense = {}

    def fit(self, df: pd.DataFrame):
        """
        Entrena el modelo con las stats de corners por equipo.
        df debe tener columnas: Squad, MP, CK_for, CK_against
        """
        df = df[df["MP"] > 0].copy()

        total_corners = df["CK_for"].sum()
        total_games = df["MP"].sum()
        self.avg_corners = total_corners / total_games

        for _, row in df.iterrows():
            team = row["Squad"]
            mp = row["MP"]
            self.attack[team] = (row["CK_for"] / mp) / self.avg_corners
            self.defense[team] = (row["CK_against"] / mp) / self.avg_corners

        return self

    def predict(self, home_team: str, away_team: str) -> dict:
        """Predice xCorners y probabilidades Over/Under para un partido."""
        if home_team not in self.attack or away_team not in self.attack:
            missing = home_team if home_team not in self.attack else away_team
            raise ValueError(f"Equipo no encontrado en el modelo de corners: '{missing}'")

        # Usamos CORNERS_PER_GAME como baseline para convertir los factores
        # (calculados con cruces como proxy) a unidades de corners reales.
        xc_home = self.attack[home_team] * self.defense[away_team] * self.CORNERS_PER_GAME
        xc_away = self.attack[away_team] * self.defense[home_team] * self.CORNERS_PER_GAME
        xc_total = xc_home + xc_away

        # Suma de dos Poisson independientes = Poisson(lambda1 + lambda2)
        probs = np.array([poisson.pmf(i, xc_total) for i in range(self.MAX_CORNERS + 1)])
        cdf = np.cumsum(probs)

        def over(line):
            n = int(line + 0.5)  # 9.5 → 9, 10.5 → 10, etc.
            return round(float(1 - cdf[n]), 4)

        def under(line):
            return round(float(1 - over(line)), 4)

        return {
            "xc_home": round(xc_home, 2),
            "xc_away": round(xc_away, 2),
            "xc_total": round(xc_total, 2),
            "over_95":  over(9.5),
            "under_95": under(9.5),
            "over_105": over(10.5),
            "under_105": under(10.5),
            "over_115": over(11.5),
            "under_115": under(11.5),
        }
