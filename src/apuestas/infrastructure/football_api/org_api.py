import os
import time
import requests

BASE_URL = "https://api.football-data.org/v4"

# Plan gratuito: 10 requests/minuto → 1 request cada 6 s (7 s para margen)
_REQUEST_INTERVAL = 7.0
_last_request_at: float = 0.0


def _throttle():
    """Espera lo necesario para respetar el rate limit del plan gratuito."""
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    wait = _REQUEST_INTERVAL - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


class FootballDataOrgClient:
    """Cliente para la API REST de football-data.org (H2H y datos de equipos)."""

    def __init__(self):
        self.headers = {"X-Auth-Token": os.getenv("FOOTBALL_DATA_API_KEY", "")}

    def search_team(self, name: str) -> int | None:
        """Busca un equipo por nombre y retorna su ID, o None si no se encuentra."""
        try:
            _throttle()
            response = requests.get(
                f"{BASE_URL}/teams",
                params={"name": name},
                headers=self.headers,
                timeout=10,
            )
            if response.status_code != 200:
                print(f"⚠️ No se pudo buscar equipo '{name}': HTTP {response.status_code}")
                return None
            teams = response.json().get("teams", [])
            return teams[0]["id"] if teams else None
        except requests.RequestException as e:
            print(f"❌ Error buscando equipo '{name}': {e}")
            return None

    def get_team_matches(self, team_id: int, limit: int = 50) -> list[dict]:
        """Retorna los últimos partidos finalizados de un equipo."""
        _throttle()
        response = requests.get(
            f"{BASE_URL}/teams/{team_id}/matches",
            params={"status": "FINISHED", "limit": limit},
            headers=self.headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("matches", [])

    def get_h2h_matches(self, home_team: str, away_team: str, limit: int = 10) -> list[dict]:
        """
        Retorna los últimos `limit` enfrentamientos directos entre home_team y away_team.
        Busca los IDs de ambos equipos y filtra los partidos del equipo local
        donde el rival sea el equipo visitante.
        """
        home_id = self.search_team(home_team)
        if home_id is None:
            raise ValueError(f"Equipo no encontrado en football-data.org: '{home_team}'")

        away_id = self.search_team(away_team)
        if away_id is None:
            raise ValueError(f"Equipo no encontrado en football-data.org: '{away_team}'")

        matches = self.get_team_matches(home_id, limit=50)

        h2h = [
            m for m in matches
            if m["homeTeam"]["id"] == away_id or m["awayTeam"]["id"] == away_id
        ]
        return h2h[:limit]
