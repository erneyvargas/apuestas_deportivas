from domain.models import League
from infrastructure.api_client import BetplayAPIClient
from infrastructure.persistence.mongo_repository import MongoLeagueRepository

class BetplayLeagueService:
    def __init__(self, repository=None):
        self.repository = repository or MongoLeagueRepository()

    def process_leagues(self):
        leagues_data = BetplayAPIClient.fetch_leagues()
        if not leagues_data:
            return False

        leagues = [
            League(
                group_id=league.get('id'),
                name=league.get('name'),
                term_key=league.get('termKey'),
                path_term_id=league.get('pathTermId'),
                sport=league.get('sport'),
                region=league.get('region')
            )
            for league in leagues_data if league.get('sport') == 'FOOTBALL'
        ]

        return self.repository.save_leagues(leagues)
