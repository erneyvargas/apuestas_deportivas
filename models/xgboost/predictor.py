from models.poisson.data_loader import load_historical_matches, load_matches
from models.poisson.predictor import implied_prob, detect_value
from models.xgboost.feature_engineer import build_match_features
from models.xgboost.model import XGBoostResult
from infrastructure.telegram.telegram_notifier import TelegramNotifier

RESULT_LABELS = {
    "home_win": "1 (Local)",
    "draw":     "X (Empate)",
    "away_win": "2 (Visitante)",
}


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
    notifier = TelegramNotifier()

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

        value_bets = []
        for key, label in RESULT_LABELS.items():
            prob = pred[key]
            odd = {"home_win": odd_1, "draw": odd_x, "away_win": odd_2}[key]
            impl = implied_prob(odd) if odd else None
            is_value = detect_value(prob, odd)
            value = "✅" if is_value else ""
            odd_str  = f"{odd:.2f}" if odd else "  N/A"
            impl_str = f"{impl*100:.1f}%" if impl else "  N/A"
            print(f"   {label:30s}  {prob*100:>6.1f}%  {odd_str:>6}  {impl_str:>6}  {value}")

            if is_value:
                value_bets.append((label, prob, odd, impl))

        if value_bets:
            _notify(notifier, match["partido"], value_bets)


def _notify(notifier: TelegramNotifier, partido: str, value_bets: list):
    lines = [f"🎯 <b>VALUE BET</b> — {partido}\n"]
    for label, prob, odd, impl in value_bets:
        edge = (prob - impl) * 100
        lines.append(
            f"  {label}\n"
            f"  Modelo: {prob*100:.1f}%  |  Cuota: {odd:.2f}  |  Edge: +{edge:.1f}%"
        )
    notifier.send("\n".join(lines))
