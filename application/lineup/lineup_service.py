from datetime import datetime
from difflib import SequenceMatcher

from infrastructure.api_football.api_football_client import APIFootballClient
from infrastructure.persistence.mongo_config import MongoConfig


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _season_for(fecha: str) -> int:
    """Año de inicio de la temporada: >= julio → mismo año, < julio → año anterior."""
    dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
    return dt.year if dt.month >= 7 else dt.year - 1


class LineupService:
    """Obtiene alineaciones confirmadas de API-Football y calcula la fortaleza
    del XI comparándolo con el mejor once posible según ratings de temporada.

    Cachea fixture IDs y ratings en MongoDB para minimizar llamadas a la API.
    """

    def __init__(self, db_name: str, league_id: int):
        self.client = APIFootballClient()
        self.db = MongoConfig.get_db(db_name)
        self.league_id = league_id

    # ------------------------------------------------------------------ #
    #  Fixture lookup                                                       #
    # ------------------------------------------------------------------ #

    def _find_fixture(self, home: str, away: str, fecha: str) -> dict | None:
        """Busca el fixture en API-Football por fecha y nombres de equipo.
        Usa fuzzy matching (≥ 60% similitud) y cachea el resultado.
        """
        date = fecha[:10]

        cached = self.db["lineup_fixtures_cache"].find_one(
            {"home": home, "away": away, "date": date}, {"_id": 0}
        )
        if cached:
            return cached

        season = _season_for(fecha)
        fixtures = self.client.get_fixtures_by_date(self.league_id, season, date)

        for f in fixtures:
            fh = f["teams"]["home"]["name"]
            fa = f["teams"]["away"]["name"]
            if _sim(home, fh) >= 0.6 and _sim(away, fa) >= 0.6:
                doc = {
                    "home": home, "away": away, "date": date,
                    "fixture_id":   f["fixture"]["id"],
                    "home_team_id": f["teams"]["home"]["id"],
                    "away_team_id": f["teams"]["away"]["id"],
                    "home_api":     fh,
                    "away_api":     fa,
                }
                self.db["lineup_fixtures_cache"].update_one(
                    {"home": home, "away": away, "date": date},
                    {"$set": doc}, upsert=True,
                )
                return doc

        return None

    # ------------------------------------------------------------------ #
    #  Player ratings                                                       #
    # ------------------------------------------------------------------ #

    def _get_ratings(self, team_id: int, season: int) -> dict:
        """Devuelve {player_id: rating} cacheado en MongoDB."""
        cache_key = f"{team_id}_{season}"
        cached = self.db["lineup_ratings_cache"].find_one(
            {"key": cache_key}, {"_id": 0}
        )
        if cached:
            return cached["ratings"]

        players = self.client.get_squad_stats(team_id, self.league_id, season)
        ratings = {}
        for p in players:
            pid = p["player"]["id"]
            stats = (p.get("statistics") or [{}])[0]
            r = stats.get("games", {}).get("rating")
            if r:
                ratings[pid] = float(r)

        self.db["lineup_ratings_cache"].update_one(
            {"key": cache_key},
            {"$set": {"key": cache_key, "ratings": ratings}},
            upsert=True,
        )
        return ratings

    # ------------------------------------------------------------------ #
    #  Strength calculation                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _strength(xi_ids: list, ratings: dict) -> float:
        """Ratio entre la suma de ratings del XI anunciado y el mejor XI posible.
        1.0 = mismo XI óptimo  |  < 1.0 = equipo debilitado.
        Jugadores sin rating registrado se valoran con 6.5 (nota media).
        """
        if not ratings:
            return 1.0
        xi_total    = sum(ratings.get(pid, 6.5) for pid in xi_ids)
        top11_total = sum(sorted(ratings.values(), reverse=True)[:11])
        return xi_total / top11_total if top11_total else 1.0

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def get_lineup_strength(self, home: str, away: str, fecha: str) -> dict | None:
        """Retorna información de alineaciones o None si no están disponibles.

        Returns:
            {
                "home_strength": float,   # ratio vs mejor XI (1.0 = plena fortaleza)
                "away_strength": float,
                "home_xi": list[str],     # nombres de los 11 titulares local
                "away_xi": list[str],
            }
        """
        if not self.client.enabled:
            return None

        fixture = self._find_fixture(home, away, fecha)
        if not fixture:
            return None

        lineups = self.client.get_lineups(fixture["fixture_id"])
        if not lineups:
            return None  # aún no confirmadas

        season = _season_for(fecha)
        home_ratings = self._get_ratings(fixture["home_team_id"], season)
        away_ratings = self._get_ratings(fixture["away_team_id"], season)

        def _parse(api_name: str) -> tuple:
            for t in lineups:
                if t["team"]["name"] == api_name:
                    ids   = [p["player"]["id"]   for p in t.get("startXI", [])]
                    names = [p["player"]["name"]  for p in t.get("startXI", [])]
                    return ids, names
            return [], []

        home_ids, home_names = _parse(fixture["home_api"])
        away_ids, away_names = _parse(fixture["away_api"])

        if not home_ids or not away_ids:
            return None

        return {
            "home_strength": self._strength(home_ids, home_ratings),
            "away_strength": self._strength(away_ids, away_ratings),
            "home_xi": home_names,
            "away_xi": away_names,
        }
