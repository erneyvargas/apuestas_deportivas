import os
from pymongo import MongoClient
from pymongo.errors import PyMongoError


class MongoConfig:
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://root:pass134@localhost:27017/')

    @staticmethod
    def get_db(db_name: str):
        try:
            client = MongoClient(MongoConfig.MONGO_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            return client[db_name]
        except PyMongoError as e:
            print(f"[MongoDB Error] {str(e)}")
            raise
