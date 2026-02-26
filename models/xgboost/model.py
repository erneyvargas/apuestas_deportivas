import os
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.preprocessing import label_binarize
from sklearn.metrics import accuracy_score, log_loss

MODEL_PATH = "models/xgboost/saved/xgb_1x2.pkl"

LABELS = {0: "Local", 1: "Empate", 2: "Visitante"}


class XGBoostResult:
    """
    Modelo XGBoost para predicción de resultado 1X2.
    Entrena con features de forma reciente (últimos 5 partidos), cuotas y H2H.
    Las probabilidades finales se calibran con regresión isotónica sobre un
    conjunto de calibración separado para evitar el efecto de "probabilidades planas".
    """

    def __init__(self):
        self.clf = XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        )
        self._calibrators = None  # lista de IsotonicRegression por clase

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weight=None,
        X_cal: pd.DataFrame = None,
        y_cal: pd.Series = None,
    ) -> "XGBoostResult":
        """
        Entrena el modelo y, si se proveen X_cal/y_cal, calibra las probabilidades
        con regresión isotónica por clase sobre ese conjunto separado.
        Esto corrige la tendencia de XGBoost a producir probabilidades "planas"
        muy cercanas a las frecuencias base del entrenamiento.
        """
        self.clf.fit(X, y, sample_weight=sample_weight)

        if X_cal is not None and y_cal is not None:
            raw_proba = self.clf.predict_proba(X_cal)          # (n, 3)
            y_bin = label_binarize(y_cal, classes=[0, 1, 2])   # (n, 3)

            self._calibrators = []
            for i in range(3):
                iso = IsotonicRegression(out_of_bounds="clip")
                iso.fit(raw_proba[:, i], y_bin[:, i])
                self._calibrators.append(iso)

            print("  📐 Probabilidades calibradas con regresión isotónica")

        return self

    def _calibrated_proba(self, raw: np.ndarray) -> np.ndarray:
        """Aplica calibración isotónica y renormaliza a suma 1."""
        if self._calibrators is None:
            return raw
        cal = np.array([self._calibrators[i].predict(raw[:, i]) for i in range(3)]).T
        totals = cal.sum(axis=1, keepdims=True)
        totals = np.where(totals == 0, 1, totals)
        return cal / totals

    def predict(self, X: pd.DataFrame) -> dict:
        """Retorna probabilidades {home_win, draw, away_win} para una fila de features."""
        raw   = self.clf.predict_proba(X)
        proba = self._calibrated_proba(raw)[0]
        return {
            "home_win": round(float(proba[0]), 4),
            "draw":     round(float(proba[1]), 4),
            "away_win": round(float(proba[2]), 4),
        }

    def evaluate(self, X: pd.DataFrame, y: pd.Series):
        raw    = self.clf.predict_proba(X)
        probas = self._calibrated_proba(raw)
        preds  = probas.argmax(axis=1)
        acc = accuracy_score(y, preds)
        ll  = log_loss(y, probas)
        print(f"  Accuracy : {acc*100:.1f}%")
        print(f"  Log-loss : {ll:.4f}")
        print(f"  Partidos test: {len(y)}")

    def save(self, path: str = MODEL_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({"clf": self.clf, "calibrators": self._calibrators}, path)
        print(f"✅ Modelo guardado en '{path}'")

    def load(self, path: str = MODEL_PATH) -> "XGBoostResult":
        if not os.path.exists(path):
            raise RuntimeError(
                f"Modelo no encontrado en '{path}'. Ejecuta: uv run python train_xgboost.py"
            )
        data = joblib.load(path)
        # Compatibilidad con modelo guardado antes de la calibración
        if isinstance(data, dict):
            self.clf = data["clf"]
            self._calibrators = data.get("calibrators")
        else:
            self.clf = data
            self._calibrators = None
        return self
