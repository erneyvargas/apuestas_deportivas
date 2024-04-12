from pymongo import MongoClient
import json
import time

from data.betplay.betplay_data import BetplayApi


class BetplayService:

    def leagues_betplay(self):
        client = MongoClient('mongodb://54.208.165.109:27017/')
        db = client['apuestas_deportivas']

        collection_leagues = db['ligas_betplay']
        resp_leagues = collection_leagues.find({"sport": "FOOTBALL"})

        betplay = BetplayApi()

        for league in resp_leagues:
            name_league = league["termKey"]
            print(name_league)
            collection = db[name_league]
            if collection is None:
                db.create_collection(name_league)
                collection = db[name_league]

            df_betplay = betplay.get_full_data(league['pathTermId'])
            records = json.loads(df_betplay.T.to_json()).values()
            collection.insert_many(records)
            time.sleep(2)
            print(df_betplay.columns)
            break