
# generating exchange to ids map
# from poloniex.api import Poloniex
# client = Poloniex()
# ticker = client.ticker()
# exchange_ids_to_names = {v['id']: i for i, v in ticker.items()}
from pathlib import Path


ws_fields_in_order = [
    'id', 'last', 'lowestAsk', 'highestBid', 'percentChange', 'baseVolume',
    'quoteVolume', 'isFrozen', 'high24hr', 'low24hr'
]

ws_protocol_url = 'wss://api2.poloniex.com:443'
trading_url = 'https://poloniex.com/tradingApi'
public_url = 'https://poloniex.com/public?'
secret_json_path = Path.joinpath(Path.home(), Path('poloniex/secret.json'))
api_rate_limit = 5
