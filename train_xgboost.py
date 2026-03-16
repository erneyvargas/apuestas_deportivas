import logging

import numpy as np
import pandas as pd

from infrastructure.football_data.football_data_client import SEASONS
from models.xgboost.data_loader import load_historical_matches
from models.xgboost.feature_engineer import build_features
from models.xgboost.model import XGBoostResult

logger = logging.getLogger(__name__)

DB_NAME = "premier_league"

SEASON_DECAY = 0.8
TRAIN_RATIO = 0.70
CAL_RATIO   = 0.10


def compute_weights(seasons: "pd.Series") -> np.ndarray:
    season_order = {s: i for i, s in enumerate(SEASONS)}
    max_idx = len(SEASONS) - 1
    return seasons.map(lambda s: SEASON_DECAY ** (max_idx - season_order.get(s, 0))).values


def run(db_name: str):
    logger.info("Cargando datos históricos (%s)...", db_name)
    df = load_historical_matches(db_name)
    logger.info("%d partidos disponibles", len(df))

    logger.info("Construyendo features...")
    X, y, seasons = build_features(df)
    logger.info("%d partidos con features completas  |  H=%d  D=%d  A=%d",
                len(X), (y == 0).sum(), (y == 1).sum(), (y == 2).sum())

    weights = compute_weights(seasons)

    n       = len(X)
    n_train = int(n * TRAIN_RATIO)
    n_cal   = int(n * (TRAIN_RATIO + CAL_RATIO))

    X_train = X.iloc[:n_train];  y_train = y.iloc[:n_train];  w_train = weights[:n_train]
    X_cal   = X.iloc[n_train:n_cal]; y_cal = y.iloc[n_train:n_cal]
    X_test  = X.iloc[n_cal:];   y_test  = y.iloc[n_cal:]

    logger.info("Split — train: %d  cal: %d  test: %d  (decay=%.1f)",
                len(X_train), len(X_cal), len(X_test), SEASON_DECAY)
    logger.info("Peso temporada más antigua (%s): %.3f  |  actual (%s): 1.000",
                SEASONS[0], SEASON_DECAY ** (len(SEASONS) - 1), SEASONS[-1])

    logger.info("Entrenando XGBoost...")
    model = XGBoostResult()
    model.fit(X_train, y_train, sample_weight=w_train, X_cal=X_cal, y_cal=y_cal)

    logger.info("Evaluando en test (%d partidos)...", len(X_test))
    model.evaluate(X_test, y_test)

    model.save()
    logger.info("Modelo guardado correctamente")


def main():
    run(DB_NAME)


if __name__ == "__main__":
    main()
