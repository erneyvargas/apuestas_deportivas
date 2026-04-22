import os
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_client: Groq | None = None

# Free tier Groq: 30 req/min → usamos 3 s de margen entre llamadas
_REQUEST_INTERVAL = 3.0
_last_request_at: float = 0.0


def _get_client() -> Groq | None:
    global _client
    if _client is None:
        key = os.getenv("GROQ_KEY")
        if not key:
            return None
        _client = Groq(api_key=key)
    return _client


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    wait = _REQUEST_INTERVAL - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def generate_match_explanation(
    home: str,
    away: str,
    winner_key: str,
    stats: dict,
    h2h_summary: dict | None = None,
) -> str:
    """
    Usa Groq (Llama 3.3 70B) para generar una explicación de la predicción
    en lenguaje natural incluyendo los datos estadísticos específicos.

    Returns:
        Explicación en texto plano. Si falla, retorna cadena vacía para usar fallback.
    """
    client = _get_client()
    if not client:
        return ""

    winner_label = {
        "home_win": f"victoria de {home}",
        "away_win": f"victoria de {away}",
        "draw":     "empate",
    }.get(winner_key, "el resultado predicho")

    stats_lines = [
        f"- {home} (local): {stats['home_role_pts5']:.2f} pts/partido como local, "
        f"{stats['home_role_gf5']:.2f} goles marcados/partido, {stats['home_role_ga5']:.2f} goles recibidos/partido.",
        f"- {away} (visitante): {stats['away_role_pts5']:.2f} pts/partido como visitante, "
        f"{stats['away_role_gf5']:.2f} goles marcados/partido, {stats['away_role_ga5']:.2f} goles recibidos/partido.",
        f"- {home} (forma general): {stats['home_pts5']:.2f} pts/partido, "
        f"{stats['home_gf5']:.2f} goles marcados/partido, {stats['home_ga5']:.2f} goles recibidos/partido.",
        f"- {away} (forma general): {stats['away_pts5']:.2f} pts/partido, "
        f"{stats['away_gf5']:.2f} goles marcados/partido, {stats['away_ga5']:.2f} goles recibidos/partido.",
    ]

    if h2h_summary and h2h_summary.get("total", 0) >= 3:
        total  = h2h_summary["total"]
        h_wins = h2h_summary.get("home_team_wins", 0)
        draws  = h2h_summary.get("draws", 0)
        a_wins = h2h_summary.get("away_team_wins", 0)
        stats_lines.append(
            f"- Historial directo ({total} partidos): {home} ganó {h_wins}, "
            f"empates {draws}, {away} ganó {a_wins}."
        )

    stats_block = "\n".join(stats_lines)

    prompt = (
        f"El modelo predictivo señala como resultado más probable: {winner_label}.\n\n"
        f"Estadísticas del partido:\n{stats_block}\n\n"
        "Con base en estos datos, redacta en español una explicación de 2 o 3 frases que justifique el pronóstico. "
        "OBLIGATORIO: menciona los valores numéricos más relevantes (pts/partido, goles marcados/recibidos) "
        "para que el lector entienda por qué el modelo favorece ese resultado. "
        "El tono debe ser directo, como un analista que habla con un apostador. "
        "No uses markdown, asteriscos, guiones como viñetas ni emojis. "
        "Solo devuelve el texto, sin encabezados ni explicaciones adicionales."
    )

    try:
        _throttle()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Eres un analista de fútbol experto que explica predicciones de forma concisa y con datos específicos."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=200,
        )
        text = response.choices[0].message.content.strip()
        return text if text else ""
    except Exception as e:
        print(f"⚠️  Groq error: {e}")
        return ""
