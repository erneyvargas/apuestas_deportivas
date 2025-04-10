class Config:
    API_URL = "https://us1.offering-api.kambicdn.com/offering/v2018/betplay"
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
