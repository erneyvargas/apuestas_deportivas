import logging
from datetime import datetime, timezone, timedelta

import pandas as pd

from models.xgboost.data_loader import load_historical_matches, load_matches
from models.xgboost.odds_utils import devig, VALUE_THRESHOLD
from models.xgboost.feature_engineer import build_match_features
from models.xgboost.model import XGBoostResult
from infrastructure.telegram.telegram_notifier import TelegramNotifier
from infrastructure.telegram.card_generator import generate_match_card
from infrastructure.groq.groq_client import generate_match_explanation
from infrastructure.persistence.leagues_config_repository import LeaguesConfigRepository
from application.football_data_org.h2h_service import H2HService

logger = logging.getLogger(__name__)

RESULT_KEYS = ["home_win", "draw", "away_win"]

_NOTIFICATION_INTERVAL = timedelta(hours=12)
_last_notified: dict[str, datetime] = {}

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



def run(db_name: str):
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
    league_logo_url = LeaguesConfigRepository().get_logo_url(db_name)

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

        partido_key = match["partido"]
        now = datetime.now(timezone.utc)
        last = _last_notified.get(partido_key)
        if last and now - last < _NOTIFICATION_INTERVAL:
            logger.debug("Notificación omitida para '%s' (dentro del intervalo de %s)", partido_key, _NOTIFICATION_INTERVAL)
            continue

        winner_key = max(pred, key=pred.get)
        stats = {col: X[col].iloc[0] for col in X.columns}
        h2h_summary = h2h_doc.get("summary") if h2h_doc else None
        explanation = generate_match_explanation(home, away, winner_key, stats, h2h_summary)
        if not explanation:
            explanation = _generate_explanation(home, away, winner_key, X, h2h_doc)
        _notify(notifier, match["partido"], match.get("fecha_evento", ""), match.get("liga", ""),
                pred, labels, explanation, odds, fair, value_bets, league_logo_url)
        _last_notified[partido_key] = now
        # Purgar entradas expiradas para evitar crecimiento ilimitado
        for k in [k for k, v in _last_notified.items() if now - v >= _NOTIFICATION_INTERVAL]:
            del _last_notified[k]

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


_GRADIENT = ["🟥", "🟧", "🟨", "🟨", "🟩", "🟩", "🟦", "🟦"]


def _bar(prob: float, width: int = 8, is_value: bool = False, market: bool = False) -> str:
    filled = round(prob * width)
    if market:
        blocks = ["⬛"] * filled
    elif is_value:
        blocks = ["🟩"] * filled
    else:
        blocks = [_GRADIENT[i] for i in range(min(filled, width))]
    return "".join(blocks) + "⬜" * (width - filled)


def _notify(notifier: TelegramNotifier, partido: str, fecha: str, liga: str, pred: dict,
            labels: dict, explanation: str, odds: dict, fair: dict,
            value_bets: list = None, league_logo_url: str | None = None):
    SEP  = "━━━━━━━━━━━━━━━━━━━━━━━━━"
    SEP2 = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    is_value = bool(value_bets)

    EMOJIS = {"home_win": "🏠", "draw": "🤝", "away_win": "✈️"}
    vb_set = {label for label, *_ in (value_bets or [])}

    def _fmt_odd(o):  return f"<code>{o:.2f}</code>" if o else "<code>—</code>"
    def _fmt_fair(f): return f"{f*100:.0f}%" if f else "—"

    header = "🔥 <b>VALUE BET DETECTADO</b>" if is_value else "📋 <b>Análisis de partido</b>"

    lines = [
        header,
        SEP,
        f"⚽ <b>{partido}</b>",
        f"📅 {_format_date(fecha)}",
        f"🏆 {liga}",
        SEP,
    ]

    for key in RESULT_KEYS:
        label   = labels[key]
        model_p = pred[key]
        fair_p  = fair[key]
        odd     = odds[key]
        is_vb   = label in vb_set and odd
        bar     = _bar(model_p, is_value=is_vb)

        bar_market = _bar(fair_p, market=True) if fair_p else "⬜" * 8

        lines.append(f"{EMOJIS[key]} <b>{label}</b>")
        lines.append(f"   {bar}  <b>{model_p*100:.0f}%</b>  modelo")
        lines.append(f"   {bar_market}  <b>{_fmt_fair(fair_p)}</b>  betplay  {_fmt_odd(odd)}")
        if is_vb:
            edge = (model_p * odd - 1) * 100
            lines.append(f"   ✅ <b>Edge: +{edge:.0f}%</b>")
        lines.append("")

    if value_bets:
        lines += [SEP2, "💰 <b>Apuesta recomendada</b>"]
        for label, prob, odd, _ in value_bets:
            edge = (prob * odd - 1) * 100
            lines.append(
                f"   🎯 <b>{label}</b>  ·  @<b>{odd:.2f}</b>"
                f"  ·  modelo <b>{prob*100:.0f}%</b>  ·  edge <b>+{edge:.0f}%</b>"
            )
        lines.append("")

    try:
        card_bytes = generate_match_card(
            partido, _format_date(fecha), liga,
            pred, labels, odds, fair, value_bets, league_logo_url,
        )
        notifier.send_photo_bytes(card_bytes)
    except Exception as e:
        logger.warning("No se pudo generar el card — usando texto: %s", e)
        notifier.send("\n".join(lines))
        return

    # Explicación como mensaje de texto independiente
    notifier.send(f"💡 <i>{explanation}</i>")
    logger.debug("Notificación enviada para '%s'", partido)
