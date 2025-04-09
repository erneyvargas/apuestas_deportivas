from datetime import datetime

class League:
    def __init__(self, group_id, name, term_key, path_term_id, sport, region, last_updated=None):
        self.group_id = group_id
        self.name = name
        self.term_key = term_key
        self.path_term_id = path_term_id
        self.sport = sport
        self.region = region
        self.last_updated = last_updated or datetime.utcnow()

    def to_dict(self):
        return vars(self)