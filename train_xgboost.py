import numpy as np
from sklearn.model_selection import train_test_split

from infrastructure.football_data.football_data_client import SEASONS
from models.poisson.data_loader import load_historical_matches
from models.xgboost.feature_engineer import build_features
from models.xgboost.model import XGBoostResult

DB_NAME = "premier_league"

# Decaimiento por temporada: la temporada actual tiene peso 1.0,
# cada temporada anterior se multiplica por este factor.
# 0.8 → la temporada más antigua tiene ~0.8^9 ≈ 0.13 del peso actual.
SEASON_DECAY = 0.8


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

    # Split temporal (no aleatorio) para evitar data leakage
    X_train, X_test, y_train, y_test, w_train, _ = train_test_split(
        X, y, weights, test_size=0.2, shuffle=False
    )

    print(f"\n🏋️  Entrenando XGBoost ({len(X_train)} partidos, decay={SEASON_DECAY})...")
    print(f"   Peso temporada más antigua ({SEASONS[0]}): {SEASON_DECAY**(len(SEASONS)-1):.3f}")
    print(f"   Peso temporada actual      ({SEASONS[-1]}): 1.000")

    model = XGBoostResult()
    model.fit(X_train, y_train, sample_weight=w_train)

    print(f"\n📊 Evaluación en test ({len(X_test)} partidos):")
    model.evaluate(X_test, y_test)

    model.save()


if __name__ == "__main__":
    main()
