from datetime import datetime, timezone

from models.poisson.data_loader import load_historical_matches, load_matches
from models.poisson.predictor import implied_prob, detect_value
from models.xgboost.feature_engineer import build_match_features
from models.xgboost.model import XGBoostResult
from infrastructure.telegram.telegram_notifier import TelegramNotifier
from application.football_data_org.h2h_service import H2HService

RESULT_KEYS = ["home_win", "draw", "away_win"]

DAYS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MONTHS_ES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _format_date(iso_date: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        day = DAYS_ES[dt.weekday()]
        month = MONTHS_ES[dt.month]
        return f"{day} {dt.day} {month} · {dt.strftime('%H:%M')} UTC"
    except Exception:
        return iso_date


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
    h2h_service = H2HService(db_name)

    print(f"\n{'='*65}")
    print(f"  XGBOOST 1X2 — {db_name.upper().replace('_', ' ')}")
    print(f"{'='*65}")

    for _, match in df_matches.iterrows():
        home = match["home_team"]
        away = match["away_team"]

        odd_1 = match.get("Resultado Final 1")
        odd_x = match.get("Resultado Final X")
        odd_2 = match.get("Resultado Final 2")

        h2h_doc = h2h_service.get_h2h(int(match["id"]), home, away)
        X = build_match_features(home, away, odd_1, odd_x, odd_2, df_history, h2h_doc)
        pred = model.predict(X)

        labels = {
            "home_win": home,
            "draw":     "Empate",
            "away_win": away,
        }
        odds = {"home_win": odd_1, "draw": odd_x, "away_win": odd_2}

        print(f"\n⚽ {match['partido']}")
        print(f"   {'Resultado':30s}  {'Modelo':>7}  {'Cuota':>6}  {'Impl%':>6}  {'Value':>5}")
        print(f"   {'-'*57}")

        value_bets = []
        for key in RESULT_KEYS:
            label = labels[key]
            prob  = pred[key]
            odd   = odds[key]
            impl  = implied_prob(odd) if odd else None
            is_value = detect_value(prob, odd)
            value    = "✅" if is_value else ""
            odd_str  = f"{odd:.2f}" if odd else "  N/A"
            impl_str = f"{impl*100:.1f}%" if impl else "  N/A"
            print(f"   {label:30s}  {prob*100:>6.1f}%  {odd_str:>6}  {impl_str:>6}  {value}")

            if is_value:
                value_bets.append((label, prob, odd, impl))

        if value_bets:
            _notify(notifier, match["partido"], match.get("fecha_evento", ""), match.get("liga", ""), value_bets)


def _notify(notifier: TelegramNotifier, partido: str, fecha: str, liga: str, value_bets: list):
    sep = "━━━━━━━━━━━━━━━━━━━━"
    lines = [
        f"🎯 <b>VALUE BET DETECTADO</b>",
        f"",
        f"⚽ <b>{partido}</b>",
        f"📅 {_format_date(fecha)}",
        f"🏆 {liga}",
        f"{sep}",
    ]
    for label, prob, odd, impl in value_bets:
        edge = (prob - impl) * 100
        lines += [
            f"",
            f"🔵 <b>{label}</b>",
            f"   Modelo:  <b>{prob*100:.1f}%</b>",
            f"   Cuota:   <b>{odd:.2f}</b>   Impl: {impl*100:.1f}%",
            f"   Edge:    <b>+{edge:.1f}%</b> ✅",
        ]
    lines.append(f"{sep}")
    notifier.send("\n".join(lines))
