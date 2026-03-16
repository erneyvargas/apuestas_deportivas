import logging
from datetime import datetime, timezone, timedelta

import pandas as pd

from models.xgboost.data_loader import load_historical_matches, load_matches
from models.xgboost.odds_utils import implied_prob, detect_value, devig, VALUE_THRESHOLD
from models.xgboost.feature_engineer import build_match_features
from models.xgboost.model import XGBoostResult
from infrastructure.telegram.telegram_notifier import TelegramNotifier
from infrastructure.groq.groq_client import generate_match_explanation
from application.football_data_org.h2h_service import H2HService
from application.lineup.lineup_service import LineupService

logger = logging.getLogger(__name__)

RESULT_KEYS = ["home_win", "draw", "away_win"]

DAYS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MONTHS_ES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

COL_OFFSET = timedelta(hours=-5)


def _format_date(iso_date: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        dt = dt + COL_OFFSET
        day = DAYS_ES[dt.weekday()]
        month = MONTHS_ES[dt.month]
        return f"{day} {dt.day} {month} · {dt.strftime('%H:%M')} Col"
    except Exception:
        return iso_date


def _minutes_until(fecha: str) -> float | None:
    try:
        dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
        return (dt - datetime.now(timezone.utc)).total_seconds() / 60
    except Exception:
        return None


def _adjust_for_lineups(pred: dict, lineup: dict) -> dict:
    h = lineup["home_strength"]
    a = lineup["away_strength"]
    adjusted = {
        "home_win": pred["home_win"] * h,
        "draw":     pred["draw"],
        "away_win": pred["away_win"] * a,
    }
    total = sum(adjusted.values())
    return {k: round(v / total, 4) for k, v in adjusted.items()}


def run(db_name: str, api_football_id: int | None = None):
    logger.info("=== Predictor XGBoost — %s ===", db_name)

    try:
        df_history = load_historical_matches(db_name)
    except RuntimeError as e:
        logger.error("XGBoost no disponible — sin datos históricos: %s", e)
        return

    try:
        model = XGBoostResult().load()
    except RuntimeError as e:
        logger.error("No se pudo cargar el modelo: %s", e)
        return

    df_matches = load_matches(db_name)
    if df_matches.empty:
        logger.warning("No hay partidos en 'betplay' para predecir (%s)", db_name)
        return

    if "fecha_evento" in df_matches.columns:
        df_matches = df_matches.sort_values("fecha_evento").reset_index(drop=True)

    logger.info("Partidos a evaluar: %d", len(df_matches))

    # Precalcular future_date una sola vez para todos los partidos del loop
    future_date = df_history["Date"].max() + pd.Timedelta(days=1)

    notifier = TelegramNotifier()
    h2h_service = H2HService(db_name)
    lineup_service = LineupService(db_name, api_football_id) if api_football_id else None

    value_bets_total = 0

    for _, match in df_matches.iterrows():
        home = match["home_team"]
        away = match["away_team"]

        odd_1 = match.get("Resultado Final 1")
        odd_x = match.get("Resultado Final X")
        odd_2 = match.get("Resultado Final 2")

        logger.debug("Procesando: %s vs %s (odds: %.2f / %.2f / %.2f)",
                     home, away,
                     odd_1 or 0, odd_x or 0, odd_2 or 0)

        h2h_doc = h2h_service.get_h2h(int(match["id"]), home, away)
        X = build_match_features(home, away, odd_1, odd_x, odd_2, df_history, h2h_doc, future_date)
        pred = model.predict(X)

        # Ajuste por alineación (solo ≤75 min antes del partido)
        lineup = None
        fecha = match.get("fecha_evento", "")
        if lineup_service and fecha:
            mins = _minutes_until(fecha)
            if mins is not None and 0 < mins <= 75:
                logger.info("Buscando alineación — %s vs %s (%.0f min para el partido)",
                            home, away, mins)
                lineup = lineup_service.get_lineup_strength(home, away, fecha)
                if lineup:
                    pred_before = dict(pred)
                    pred = _adjust_for_lineups(pred, lineup)
                    logger.info("Ajuste por XI — antes: H=%.1f%% D=%.1f%% A=%.1f%%  →  "
                                "después: H=%.1f%% D=%.1f%% A=%.1f%%",
                                pred_before["home_win"] * 100, pred_before["draw"] * 100,
                                pred_before["away_win"] * 100,
                                pred["home_win"] * 100, pred["draw"] * 100, pred["away_win"] * 100)

        labels = {"home_win": home, "draw": "Empate", "away_win": away}
        odds   = {"home_win": odd_1, "draw": odd_x, "away_win": odd_2}

        fair_h, fair_d, fair_a = devig(odd_1, odd_x, odd_2)
        fair = {"home_win": fair_h, "draw": fair_d, "away_win": fair_a}

        # Log tabla de predicción
        logger.info(
            "%s vs %s  |  H=%.1f%%(%.2f)  D=%.1f%%(%.2f)  A=%.1f%%(%.2f)",
            home, away,
            pred["home_win"] * 100, odd_1 or 0,
            pred["draw"]     * 100, odd_x or 0,
            pred["away_win"] * 100, odd_2 or 0,
        )

        value_bets = []
        for key in RESULT_KEYS:
            prob     = pred[key]
            fair_p   = fair[key]
            odd      = odds[key]
            is_value = fair_p is not None and prob - fair_p >= VALUE_THRESHOLD
            if is_value and odd and odd > 1.6:
                edge = (prob * odd - 1) * 100
                logger.info("VALUE BET detectado — %s [%s]: modelo=%.1f%% fair=%.1f%% cuota=%.2f edge=+%.0f%%",
                            match["partido"], labels[key],
                            prob * 100, fair_p * 100, odd, edge)
                value_bets.append((labels[key], prob, odd, fair_p))
                value_bets_total += 1

        if not value_bets:
            continue

        winner_key = max(pred, key=pred.get)
        stats = {col: X[col].iloc[0] for col in X.columns}
        h2h_summary = h2h_doc.get("summary") if h2h_doc else None
        explanation = generate_match_explanation(home, away, winner_key, stats, h2h_summary)
        if not explanation:
            explanation = _generate_explanation(home, away, winner_key, X, h2h_doc)
        _notify(notifier, match["partido"], match.get("fecha_evento", ""), match.get("liga", ""),
                pred, labels, explanation, odds, fair, value_bets, lineup)

    logger.info("Predictor finalizado — %d value bets detectados en %d partidos",
                value_bets_total, len(df_matches))


def _generate_explanation(home: str, away: str, winner_key: str, X, h2h_doc: dict | None) -> str:
    reasons = []

    home_pts = X["home_pts5"].iloc[0]
    away_pts = X["away_pts5"].iloc[0]
    home_gf  = X["home_gf5"].iloc[0]
    away_gf  = X["away_gf5"].iloc[0]
    home_ga  = X["home_ga5"].iloc[0]
    away_ga  = X["away_ga5"].iloc[0]

    home_role_pts = X["home_role_pts5"].iloc[0]
    away_role_pts = X["away_role_pts5"].iloc[0]
    home_role_gf  = X["home_role_gf5"].iloc[0]
    away_role_gf  = X["away_role_gf5"].iloc[0]
    home_role_ga  = X["home_role_ga5"].iloc[0]
    away_role_ga  = X["away_role_ga5"].iloc[0]

    if winner_key == "home_win":
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


def _bar(prob: float, width: int = 10) -> str:
    filled = round(prob * width)
    return "█" * filled + "░" * (width - filled)


def _notify(notifier: TelegramNotifier, partido: str, fecha: str, liga: str, pred: dict,
            labels: dict, explanation: str, odds: dict, fair: dict,
            value_bets: list = None, lineup: dict = None):
    sep = "━━━━━━━━━━━━━━━━━━━━━━━━"
    is_value = bool(value_bets)

    header = "🔥 <b>VALUE BET</b>" if is_value else "📋 <b>Análisis</b>"

    EMOJIS = {"home_win": "🏠", "draw": "🤝", "away_win": "✈️"}
    vb_set = {label for label, *_ in (value_bets or [])}

    lines = [
        header,
        "",
        f"⚽ <b>{partido}</b>",
        f"📅 {_format_date(fecha)}  ·  {liga}",
        sep,
    ]

    if lineup:
        h_pct   = f"{lineup['home_strength']*100:.0f}%"
        a_pct   = f"{lineup['away_strength']*100:.0f}%"
        h_names = "  ·  ".join(lineup["home_xi"][:5]) + ("..." if len(lineup["home_xi"]) > 5 else "")
        a_names = "  ·  ".join(lineup["away_xi"][:5]) + ("..." if len(lineup["away_xi"]) > 5 else "")
        lines += [
            f"🧩 <b>Alineaciones</b>  —  🏠 {h_pct}  ✈️ {a_pct}",
            f"🏠 {h_names}",
            f"✈️  {a_names}",
            sep,
        ]

    for key in RESULT_KEYS:
        label   = labels[key]
        model_p = pred[key]
        bar     = _bar(model_p)
        pct     = f"{model_p*100:.0f}%"

        if label in vb_set and odds[key]:
            edge   = (model_p * odds[key] - 1) * 100
            suffix = f"  ✅ <b>+{edge:.0f}%</b>"
        else:
            suffix = ""

        lines.append(f"{EMOJIS[key]} {label}  {bar}  <b>{pct}</b>{suffix}")

    lines.append(sep)

    def _fmt_odd(o): return f"{o:.2f}" if o else "N/A"
    def _fmt_fair(f): return f"{f*100:.0f}%" if f else "N/A"

    odds_str = "  /  ".join(_fmt_odd(odds[k]) for k in RESULT_KEYS)
    fair_str = "  /  ".join(_fmt_fair(fair[k]) for k in RESULT_KEYS)

    lines += [
        f"Cuotas  {odds_str}",
        f"Fair    {fair_str}",
        sep,
        f"💡 <i>{explanation}</i>",
        sep,
    ]

    notifier.send("\n".join(lines))
    logger.debug("Notificación enviada para '%s'", partido)
