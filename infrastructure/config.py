import os
from pymongo import MongoClient
from pymongo.errors import PyMongoError


class Config:
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://root:pass134@localhost:27017/')
    DB_NAME = os.getenv('DB_NAME', 'apuestas_deportivas')
    API_URL = "https://us1.offering-api.kambicdn.com/offering/v2018/betplay/group/highlight.json"
    DEFAULT_PARAMS = {
        'lang': 'es_CO',
        'market': 'CO',
        'client_id': 2,
        'channel_id': 1,
        'depth': 0
    }
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }

    @staticmethod
    def get_db():
        try:
            client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            return client[Config.DB_NAME]
        except PyMongoError as e:
            print(f"[MongoDB Error] {str(e)}")
            raise
