from broker import BrokerAPI
from strategy import TripleMAMACDStrategy
import time
import configparser

# Initialize the broker API
# Initialize configparser
config = configparser.ConfigParser()
config.read('/Users/mortezapoudat/projects/trading_bot_tripleMaMacd/config.ini')
print("Sections loaded:", config.sections())

# Fetch the API key, login, and password from the 'broker' section
api_key = config['broker']['api_key']
password = config['broker']['password']
account_id = config['broker']['account_id']
broker = BrokerAPI(api_key=api_key, login=account_id, password=password)


# Define symbols to monitor
symbols = ["BTCUSD", "ETHUSD", "LTCUSD", "BCHUSD", "EURUSD", "GBPUSD"]
#symbols = ["BTCUSD"]

# Initialize strategy object for each symbol
strategies = {}

def initialize_strategies():
    for symbol in symbols:
        print(f"Fetching initial 200 candles for {symbol}...")
        ohlc_data = broker.get_historical_data_in_chunks(epic=symbol, resolution="MINUTE_15", start_date="2024-09-15T00:00:00")
        strategies[symbol] = TripleMAMACDStrategy(ohlc_data)

# Main logic for fetching data, generating signals, and executing trades for multiple symbols
def main():
    # Step 1: Initialize strategies for each symbol
    initialize_strategies()

    while True:
        for symbol in symbols:

            # Step 5: Check for take-profit target
            if broker.check_take_profit(symbol):
                continue  # If TP reached, move to the next symbol
            
            # Step 2: Fetch the latest candle for each symbol
            print(f"Fetching latest candle for {symbol}...")
            latest_candle = broker.fetch_latest_candle(epic=symbol, resolution="MINUTE_15")
            if latest_candle is not None:
                # Step 3: Update strategy with the latest candle
                strategies[symbol].update_ohlc(latest_candle)
                
                # Step 4: Generate buy/sell signal
                signal = strategies[symbol].generate_signal()
                broker.update_positions()
                # Step 5: Execute order based on the signal
                if signal == "BUY":
                    broker.send_order(symbol=symbol, side="BUY", size=0.01)
                elif signal == "SELL":
                    broker.send_order(symbol=symbol, side="SELL", size=0.01)

        # Wait for the next cycle (5 minutes)
        time.sleep(300)

if __name__ == "__main__":
    main()
