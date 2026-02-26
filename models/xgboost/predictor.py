from datetime import datetime, timezone

from models.poisson.data_loader import load_historical_matches, load_matches
from models.poisson.predictor import implied_prob, detect_value, devig, VALUE_THRESHOLD
from models.xgboost.feature_engineer import build_match_features
from models.xgboost.model import XGBoostResult
from infrastructure.telegram.telegram_notifier import TelegramNotifier
from infrastructure.gemini.gemini_client import generate_match_explanation
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

        # Probabilidades justas (sin margen de la casa)
        fair_h, fair_d, fair_a = devig(odd_1, odd_x, odd_2)
        fair = {"home_win": fair_h, "draw": fair_d, "away_win": fair_a}

        print(f"\n⚽ {match['partido']}")
        print(f"   {'Resultado':30s}  {'Modelo':>7}  {'Cuota':>6}  {'Fair%':>6}  {'Value':>5}")
        print(f"   {'-'*57}")

        value_bets = []
        for key in RESULT_KEYS:
            label    = labels[key]
            prob     = pred[key]
            odd      = odds[key]
            fair_p   = fair[key]
            is_value = fair_p is not None and prob - fair_p >= VALUE_THRESHOLD
            value    = "✅" if is_value else ""
            odd_str  = f"{odd:.2f}" if odd else "  N/A"
            fair_str = f"{fair_p*100:.1f}%" if fair_p else "  N/A"
            print(f"   {label:30s}  {prob*100:>6.1f}%  {odd_str:>6}  {fair_str:>6}  {value}")

            if is_value:
                value_bets.append((label, prob, odd, fair_p))

        if value_bets:
            winner_key = max(pred, key=pred.get)
            stats = {col: X[col].iloc[0] for col in X.columns}
            h2h_summary = h2h_doc.get("summary") if h2h_doc else None
            explanation = generate_match_explanation(home, away, winner_key, stats, h2h_summary)
            if not explanation:
                explanation = _generate_explanation(home, away, winner_key, X, h2h_doc)
            _notify(notifier, match["partido"], match.get("fecha_evento", ""), match.get("liga", ""), pred, labels, explanation, odds, fair)


def _generate_explanation(home: str, away: str, winner_key: str, X, h2h_doc: dict | None) -> str:
    reasons = []

    # Forma general (últimos 5 sin importar rol)
    home_pts = X["home_pts5"].iloc[0]
    away_pts = X["away_pts5"].iloc[0]
    home_gf  = X["home_gf5"].iloc[0]
    away_gf  = X["away_gf5"].iloc[0]
    home_ga  = X["home_ga5"].iloc[0]
    away_ga  = X["away_ga5"].iloc[0]

    # Forma específica por rol (local/visitante)
    home_role_pts = X["home_role_pts5"].iloc[0]
    away_role_pts = X["away_role_pts5"].iloc[0]
    home_role_gf  = X["home_role_gf5"].iloc[0]
    away_role_gf  = X["away_role_gf5"].iloc[0]
    home_role_ga  = X["home_role_ga5"].iloc[0]
    away_role_ga  = X["away_role_ga5"].iloc[0]

    if winner_key == "home_win":
        # Forma por rol primero; forma general como respaldo
        if home_role_pts > away_role_pts + 0.3:
            reasons.append(
                f"{home} suma {home_role_pts:.1f} pts/partido como local, "
                f"frente a {away_role_pts:.1f} de {away} como visitante"
            )
        elif home_pts > away_pts + 0.3:
            reasons.append(
                f"{home} llega con mejor forma general "
                f"({home_pts:.1f} pts/partido vs {away_pts:.1f} de {away})"
            )

        # Ataque local vs defensa visitante del rival
        if home_role_gf > away_role_ga + 0.2:
            reasons.append(
                f"su ataque en casa ({home_role_gf:.1f} goles/partido) "
                f"supera la defensa de {away} fuera ({away_role_ga:.1f} concedidos)"
            )
        elif home_gf > away_ga + 0.2:
            reasons.append(
                f"su ataque ({home_gf:.1f} goles/partido) "
                f"supera la defensa visitante ({away_ga:.1f} concedidos)"
            )

    elif winner_key == "away_win":
        # Forma por rol primero; forma general como respaldo
        if away_role_pts > home_role_pts + 0.3:
            reasons.append(
                f"{away} suma {away_role_pts:.1f} pts/partido como visitante, "
                f"frente a {home_role_pts:.1f} de {home} como local"
            )
        elif away_pts > home_pts + 0.3:
            reasons.append(
                f"{away} llega con mejor forma general "
                f"({away_pts:.1f} pts/partido vs {home_pts:.1f} de {home})"
            )

        # Ataque visitante vs defensa local del rival
        if away_role_gf > home_role_ga + 0.2:
            reasons.append(
                f"su ataque fuera ({away_role_gf:.1f} goles/partido) "
                f"supera la defensa de {home} en casa ({home_role_ga:.1f} concedidos)"
            )
        elif away_gf > home_ga + 0.2:
            reasons.append(
                f"su ataque ({away_gf:.1f} goles/partido) "
                f"supera la defensa local ({home_ga:.1f} concedidos)"
            )

    else:  # draw
        if abs(home_role_pts - away_role_pts) <= 0.4:
            reasons.append(
                f"ambos equipos muestran una forma muy pareja en su rol "
                f"({home_role_pts:.1f} vs {away_role_pts:.1f} pts/partido)"
            )
        elif abs(home_pts - away_pts) <= 0.4:
            reasons.append(
                f"ambos equipos presentan una forma muy similar "
                f"({home_pts:.1f} vs {away_pts:.1f} pts/partido)"
            )

        avg_role_gf = (home_role_gf + away_role_gf) / 2
        if avg_role_gf < 1.4:
            reasons.append("sus encuentros en estos roles suelen ser disputados y de pocos goles")
        elif (home_gf + away_gf) / 2 < 1.4:
            reasons.append("sus encuentros suelen ser disputados y de pocos goles")

    # H2H
    if h2h_doc and h2h_doc.get("matches"):
        summary = h2h_doc.get("summary", {})
        total   = summary.get("total", 0)
        if total >= 3:
            if winner_key == "home_win":
                wins = summary.get("home_team_wins", 0)
                if wins / total >= 0.4:
                    reasons.append(f"historial favorable: ganó {wins} de {total} enfrentamientos directos")
            elif winner_key == "away_win":
                wins = summary.get("away_team_wins", 0)
                if wins / total >= 0.4:
                    reasons.append(f"historial favorable: ganó {wins} de {total} enfrentamientos directos")
            else:
                draws = summary.get("draws", 0)
                if draws / total >= 0.33:
                    reasons.append(f"{int(draws * 100 / total)}% de sus encuentros previos terminaron en empate")

    if not reasons:
        reasons.append("el modelo detecta ventaja combinando forma reciente, H2H y cuotas de mercado")

    return " · ".join(reasons)


def _notify(notifier: TelegramNotifier, partido: str, fecha: str, liga: str, pred: dict, labels: dict, explanation: str, odds: dict, fair: dict):
    sep = "━━━━━━━━━━━━━━━━━━━━"

    winner_key = max(pred, key=pred.get)
    winner_label = labels[winner_key]
    winner_prob = pred[winner_key] * 100
    winner_emoji = "🏠" if winner_key == "home_win" else ("✈️" if winner_key == "away_win" else "🤝")

    lines = [
        f"🎯 <b>VALUE BET DETECTADO</b>",
        f"",
        f"⚽ <b>{partido}</b>",
        f"📅 {_format_date(fecha)}",
        f"🏆 {liga}",
        f"{sep}",
        f"",
        f"{winner_emoji} Pronóstico: <b>{winner_label}</b> ({winner_prob:.1f}%)",
        f"",
        f"💡 <i>{explanation}</i>"
    ]
    def _prob_line(label: str, model_p: float, odd, fair_p) -> str:
        odd_str  = f"{odd:.2f}" if odd else "N/A"
        fair_str = f"{fair_p*100:.1f}%" if fair_p else "N/A"
        return f"   {label}: <b>{model_p*100:.1f}%</b>  |  {odd_str} → <b>{fair_str}</b>"

    lines += [
        f"",
        f"{sep}",
        f"📊 Modelo vs Betplay (sin margen):",
        _prob_line(labels["home_win"], pred["home_win"], odds["home_win"], fair["home_win"]),
        _prob_line("Empate",           pred["draw"],     odds["draw"],     fair["draw"]),
        _prob_line(labels["away_win"], pred["away_win"], odds["away_win"], fair["away_win"]),
        f"{sep}",
    ]
    notifier.send("\n".join(lines))
