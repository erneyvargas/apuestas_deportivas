import os
import joblib
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, log_loss

MODEL_PATH = "models/xgboost/saved/xgb_1x2.pkl"

LABELS = {0: "Local", 1: "Empate", 2: "Visitante"}


class XGBoostResult:
    """
    Modelo XGBoost para predicción de resultado 1X2.
    Entrena con features de forma reciente (últimos 5 partidos) y cuotas de mercado.
    """

    def __init__(self):
        self.clf = XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        )

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "XGBoostResult":
        self.clf.fit(X, y)
        return self

    def predict(self, X: pd.DataFrame) -> dict:
        """Retorna probabilidades {home_win, draw, away_win} para una fila de features."""
        proba = self.clf.predict_proba(X)[0]
        return {
            "home_win": round(float(proba[0]), 4),
            "draw":     round(float(proba[1]), 4),
            "away_win": round(float(proba[2]), 4),
        }

    def evaluate(self, X: pd.DataFrame, y: pd.Series):
        preds = self.clf.predict(X)
        probas = self.clf.predict_proba(X)
        acc = accuracy_score(y, preds)
        ll = log_loss(y, probas)
        print(f"  Accuracy : {acc*100:.1f}%")
        print(f"  Log-loss : {ll:.4f}")
        print(f"  Partidos test: {len(y)}")

    def save(self, path: str = MODEL_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(self.clf, path)
        print(f"✅ Modelo guardado en '{path}'")

    def load(self, path: str = MODEL_PATH) -> "XGBoostResult":
        if not os.path.exists(path):
            raise RuntimeError(
                f"Modelo no encontrado en '{path}'. Ejecuta: uv run python train_xgboost.py"
            )
        self.clf = joblib.load(path)
        return self
