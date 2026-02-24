import os
from pymongo import MongoClient
from pymongo.errors import PyMongoError


class MongoConfig:
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://root:pass134@localhost:27017/')
    DB_NAME = os.getenv('DB_NAME', 'apuestas_deportivas')
    FBREF_DB_NAME = os.getenv('FBREF_DB_NAME', 'fbref_stats')

    @staticmethod
    def get_db(db_name: str = None):
        try:
            name = db_name or MongoConfig.DB_NAME
            client = MongoClient(MongoConfig.MONGO_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            return client[name]
        except PyMongoError as e:
            print(f"[MongoDB Error] {str(e)}")
            raise
