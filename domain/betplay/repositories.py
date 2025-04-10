from abc import ABC, abstractmethod

class LeagueRepository(ABC):

    @abstractmethod
    def save_leagues(self, leagues):
        pass
