from infrastructure.persistence.mongo_config import MongoConfig

CONFIG_DB = "config"
LEAGUES_COLLECTION = "leagues"


class LeaguesConfigRepository:
    def __init__(self):
        self.collection = MongoConfig.get_db(CONFIG_DB)[LEAGUES_COLLECTION]

    def save(self, league_db: str, term_key: str, league_slug: str, name: str, betplay_path: str):
        """Inserta o actualiza la configuración de una liga"""
        self.collection.update_one(
            {"league_db": league_db},
            {"$set": {
                "league_db": league_db,
                "term_key": term_key,
                "league_slug": league_slug,
                "betplay_path": betplay_path,
                "name": name,
            }},
            upsert=True
        )
        print(f"✅ Config guardada: {name}")

    def find_all(self) -> list[dict]:
        """Retorna todas las ligas configuradas"""
        return list(self.collection.find({}, {"_id": 0}))
