from datetime import datetime

from infrastructure.football_data_org.football_data_org_client import FootballDataOrgClient
from infrastructure.persistence.mongo_config import MongoConfig

COLLECTION = "h2h_results"


class H2HService:
    """
    Servicio de enfrentamientos directos (H2H).

    Flujo:
    1. Recibe betplay_event_id, home_team y away_team.
    2. Busca en MongoDB usando betplay_event_id como clave de caché.
    3. Si existe → retorna el documento cacheado (sin llamada a la API).
    4. Si no existe → consulta football-data.org, construye el documento,
       lo persiste en MongoDB y lo retorna.
    """

    def __init__(self, db_name: str):
        self.client = FootballDataOrgClient()
        self.collection = MongoConfig.get_db(db_name)[COLLECTION]

    def get_h2h(
        self,
        betplay_event_id: int,
        home_team: str,
        away_team: str,
        limit: int = 10,
    ) -> dict | None:
        """
        Retorna los datos H2H del partido. Usa caché por betplay_event_id.

        Args:
            betplay_event_id: ID del evento en Betplay (clave de caché).
            home_team: Nombre del equipo local.
            away_team: Nombre del equipo visitante.
            limit: Cantidad máxima de enfrentamientos a retornar.

        Returns:
            Diccionario con los partidos y resumen H2H, o None si falla.
        """
        # 1. Verificar caché
        cached = self.collection.find_one({"betplay_event_id": betplay_event_id})
        if cached:
            print(f"✅ H2H desde caché: {home_team} vs {away_team}")
            cached.pop("_id", None)
            return cached

        # 2. Consultar API
        print(f"🌐 Consultando H2H en football-data.org: {home_team} vs {away_team}...")
        try:
            raw_matches = self.client.get_h2h_matches(home_team, away_team, limit=limit)
        except Exception as e:
            print(f"❌ Error obteniendo H2H: {e}")
            return None

        # 3. Parsear partidos
        matches = []
        for m in raw_matches:
            matches.append({
                "date": m["utcDate"],
                "home_team": m["homeTeam"]["name"],
                "away_team": m["awayTeam"]["name"],
                "home_goals": m["score"]["fullTime"]["home"],
                "away_goals": m["score"]["fullTime"]["away"],
                "winner": m["score"]["winner"],  # HOME_TEAM | AWAY_TEAM | DRAW
            })

        # 4. Calcular resumen
        home_wins = sum(
            1 for m in matches
            if (m["winner"] == "HOME_TEAM" and m["home_team"] == home_team)
            or (m["winner"] == "AWAY_TEAM" and m["away_team"] == home_team)
        )
        away_wins = sum(
            1 for m in matches
            if (m["winner"] == "HOME_TEAM" and m["home_team"] == away_team)
            or (m["winner"] == "AWAY_TEAM" and m["away_team"] == away_team)
        )
        draws = sum(1 for m in matches if m["winner"] == "DRAW")

        doc = {
            "betplay_event_id": betplay_event_id,
            "home_team": home_team,
            "away_team": away_team,
            "fetched_at": datetime.utcnow().isoformat(),
            "matches": matches,
            "summary": {
                "total": len(matches),
                "home_team_wins": home_wins,
                "draws": draws,
                "away_team_wins": away_wins,
            },
        }

        # 5. Persistir en MongoDB
        self.collection.insert_one(doc)
        doc.pop("_id", None)
        print(f"✅ H2H guardado en '{COLLECTION}': {len(matches)} partidos encontrados")
        return doc
