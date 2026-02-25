from sklearn.model_selection import train_test_split

from models.poisson.data_loader import load_historical_matches
from models.xgboost.feature_engineer import build_features
from models.xgboost.model import XGBoostResult

DB_NAME = "premier_league"


def main():
    print("📥 Cargando datos históricos...")
    df = load_historical_matches(DB_NAME)
    print(f"   {len(df)} partidos disponibles")

    print("⚙️  Construyendo features...")
    X, y = build_features(df)
    print(f"   {len(X)} partidos con features completas")
    print(f"   Distribución: H={( y==0).sum()}  D={(y==1).sum()}  A={(y==2).sum()}")

    # Split temporal (no aleatorio) para evitar data leakage
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    print(f"\n🏋️  Entrenando XGBoost ({len(X_train)} partidos)...")
    model = XGBoostResult()
    model.fit(X_train, y_train)

    print(f"\n📊 Evaluación en test ({len(X_test)} partidos):")
    model.evaluate(X_test, y_test)

    model.save()


if __name__ == "__main__":
    main()
