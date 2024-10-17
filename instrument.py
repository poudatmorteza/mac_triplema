import json
from broker import BrokerAPI
from broker_live import BrokerAPILIVE
from strategy import TripleMAMACDStrategy
import time
import configparser
from trailing import TakeProfitStopLossHandler

# Initialize the broker API
# Initialize configparser
config = configparser.ConfigParser()
config.read('/home/botuser/macd_ema/mac_triplema/config.ini')
print("Sections loaded:", config.sections())

# Fetch the API key, login, and password from the 'broker' section
api_key = config['broker']['api_key']
password = config['broker']['password']
account_id = config['broker']['account_id']
broker = BrokerAPI(api_key=api_key, login=account_id, password=password)
broker_live = BrokerAPILIVE(api_key=api_key, login=account_id, password=password)

instruments = broker_live.instrument_list()
# # with open("/home/botuser/macd_ema/instruments.json", "w") as inst_file:
    # json.dump(instruments,inst_file, indent=4)
#broker_live.get_market_data(symbol="OIL_CRUDE")
broker_live.calculate_stop_distance(symbol="OIL_CRUDE", side="BUY")
#broker.close_position(symbol="ETHUSD")
#broker_live.calculate_trade_size(symbol="OIL_CRUDE")
broker_live.send_order(symbol="OIL_CRUDE", side="SELL", size=1.0, trailing=True)
#broker_live.calculate_stop_distance(symbol="GOLD")
#broker_live.send_order(symbol="OIL_CRUDE", side="SELL", size=1.0)
#broker.send_order(symbol="OIL_CRUDE", side="SELL", size=1.0)
#broker.send_order(symbol="OIL_CRUDE", side="SELL", size=1.0)

# Fetch open positions
#positions = broker.update_positions()
#print(f"Current Positions: {broker.open_positions}")

# Place a buy order for EURUSD