from models.poisson.data_loader import load_historical_matches, load_matches
from models.poisson.predictor import implied_prob, detect_value
from models.xgboost.feature_engineer import build_match_features
from models.xgboost.model import XGBoostResult


def run(db_name: str):
    try:
        df_history = load_historical_matches(db_name)
    except RuntimeError as e:
        print(f"\n❌ XGBoost no disponible: {e}")
        return

    try:
        model = XGBoostResult().load()
    except RuntimeError as e:
        print(f"\n❌ {e}")
        return

    df_matches = load_matches(db_name)

    print(f"\n{'='*65}")
    print(f"  XGBOOST 1X2 — {db_name.upper().replace('_', ' ')}")
    print(f"{'='*65}")

    for _, match in df_matches.iterrows():
        home = match["home_team"]
        away = match["away_team"]

        odd_1 = match.get("Resultado Final 1")
        odd_x = match.get("Resultado Final X")
        odd_2 = match.get("Resultado Final 2")

        X = build_match_features(home, away, odd_1, odd_x, odd_2, df_history)
        pred = model.predict(X)

        print(f"\n⚽ {match['partido']}")
        print(f"   {'Resultado':30s}  {'Modelo':>7}  {'Cuota':>6}  {'Impl%':>6}  {'Value':>5}")
        print(f"   {'-'*57}")

        for label, prob, odd in [
            ("1 (Local)",     pred["home_win"], odd_1),
            ("X (Empate)",    pred["draw"],     odd_x),
            ("2 (Visitante)", pred["away_win"], odd_2),
        ]:
            impl = implied_prob(odd) if odd else None
            value = "✅" if detect_value(prob, odd) else ""
            odd_str  = f"{odd:.2f}" if odd else "  N/A"
            impl_str = f"{impl*100:.1f}%" if impl else "  N/A"
            print(f"   {label:30s}  {prob*100:>6.1f}%  {odd_str:>6}  {impl_str:>6}  {value}")
