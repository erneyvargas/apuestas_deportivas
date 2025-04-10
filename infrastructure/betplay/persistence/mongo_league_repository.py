from pymongo.errors import PyMongoError
from domain.betplay.repositories import LeagueRepository
from infrastructure.betplay.persistence.mongo_config import MongoConfig


class MongoLeagueRepository(LeagueRepository):
    def __init__(self):
        self.db = MongoConfig.get_db()
        self.collection = self.db['ligas_betplay']

    def save_leagues(self, leagues):
        try:
            self.collection.delete_many({})
            result = self.collection.insert_many([league.to_dict() for league in leagues])
            print(f"✅ Se actualizaron {len(result.inserted_ids)} ligas")
            return True
        except PyMongoError as e:
            print(f"[MongoDB Insert Error] {str(e)}")
            return False
