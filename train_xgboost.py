import numpy as np
import pandas as pd

from infrastructure.football_data.football_data_client import SEASONS
from models.xgboost.data_loader import load_historical_matches
from models.xgboost.feature_engineer import build_features
from models.xgboost.model import XGBoostResult

DB_NAME = "premier_league"

# Decaimiento por temporada: la temporada actual tiene peso 1.0,
# cada temporada anterior se multiplica por este factor.
# 0.8 → la temporada más antigua tiene ~0.8^9 ≈ 0.13 del peso actual.
SEASON_DECAY = 0.8

# Split temporal: 70% train · 10% calibración · 20% test
TRAIN_RATIO = 0.70
CAL_RATIO   = 0.10


def compute_weights(seasons: "pd.Series") -> np.ndarray:
    season_order = {s: i for i, s in enumerate(SEASONS)}
    max_idx = len(SEASONS) - 1
    return seasons.map(lambda s: SEASON_DECAY ** (max_idx - season_order.get(s, 0))).values


def main():
    print("📥 Cargando datos históricos...")
    df = load_historical_matches(DB_NAME)
    print(f"   {len(df)} partidos disponibles")

    print("⚙️  Construyendo features...")
    X, y, seasons = build_features(df)
    print(f"   {len(X)} partidos con features completas")
    print(f"   Distribución: H={( y==0).sum()}  D={(y==1).sum()}  A={(y==2).sum()}")

    weights = compute_weights(seasons)

    # Split temporal (sin shuffle para evitar data leakage)
    n       = len(X)
    n_train = int(n * TRAIN_RATIO)
    n_cal   = int(n * (TRAIN_RATIO + CAL_RATIO))

    X_train  = X.iloc[:n_train]
    y_train  = y.iloc[:n_train]
    w_train  = weights[:n_train]

    X_cal    = X.iloc[n_train:n_cal]
    y_cal    = y.iloc[n_train:n_cal]

    X_test   = X.iloc[n_cal:]
    y_test   = y.iloc[n_cal:]

    print(f"\n🏋️  Entrenando XGBoost ({len(X_train)} partidos, decay={SEASON_DECAY})...")
    print(f"   Peso temporada más antigua ({SEASONS[0]}): {SEASON_DECAY**(len(SEASONS)-1):.3f}")
    print(f"   Peso temporada actual      ({SEASONS[-1]}): 1.000")
    print(f"   Calibración: {len(X_cal)} partidos   Test: {len(X_test)} partidos")

    model = XGBoostResult()
    model.fit(X_train, y_train, sample_weight=w_train, X_cal=X_cal, y_cal=y_cal)

    print(f"\n📊 Evaluación en test ({len(X_test)} partidos):")
    model.evaluate(X_test, y_test)

    model.save()


if __name__ == "__main__":
    main()
