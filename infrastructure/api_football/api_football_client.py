import os

import requests


class APIFootballClient:
    """Cliente para API-Football v3 (RapidAPI).

    Requiere variable de entorno API_FOOTBALL_KEY.
    Tier gratuito: 100 requests/día.
    """

    BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"

    def __init__(self):
        self.api_key = os.getenv("API_FOOTBALL_KEY")
        self.headers = {
            "X-RapidAPI-Key": self.api_key or "",
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com",
        }
        self.enabled = bool(self.api_key)

    def _get(self, endpoint: str, params: dict) -> list:
        if not self.enabled:
            return []
        try:
            r = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                headers=self.headers,
                params=params,
                timeout=10,
            )
            r.raise_for_status()
            return r.json().get("response", [])
        except Exception as e:
            print(f"⚠️  API-Football [{endpoint}]: {e}")
            return []

    def get_fixtures_by_date(self, league_id: int, season: int, date: str) -> list:
        """Retorna fixtures de una liga en una fecha (YYYY-MM-DD)."""
        return self._get("fixtures", {
            "league": league_id,
            "season": season,
            "date": date,
        })

    def get_lineups(self, fixture_id: int) -> list:
        """Retorna alineaciones confirmadas de un fixture.
        Lista vacía si aún no están disponibles.
        """
        return self._get("fixtures/lineups", {"fixture": fixture_id})

    def get_squad_stats(self, team_id: int, league_id: int, season: int) -> list:
        """Retorna estadísticas de jugadores de un equipo en la temporada."""
        return self._get("players", {
            "team": team_id,
            "league": league_id,
            "season": season,
        })
