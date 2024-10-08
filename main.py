import time
from threading import Thread
from broker import BrokerAPI
from strategy import TripleMAMACDStrategy
import time
import configparser
from datetime import datetime, timedelta

# Function to calculate time until the next :15, :30, :45, or :00 minute mark
def get_seconds_until_next_quarter_plus_5_seconds():
    now = datetime.now()
    # Get the next quarter (15-minute interval)
    next_quarter_minute = ((now.minute // 15) + 1) * 15
    if next_quarter_minute == 60:
        next_quarter_minute = 0
        next_run_time = (now + timedelta(hours=1)).replace(minute=0, second=5, microsecond=0)
    else:
        next_run_time = now.replace(minute=next_quarter_minute, second=5, microsecond=0)

    # Calculate the time difference between now and the next run time
    time_difference = next_run_time - now
    return time_difference.total_seconds()

# Main function for strategy logic
def strategy_logic():
    while True:
        for symbol in symbols:
            # Fetch the latest candle for each symbol every 15 minutes
            print(f"Fetching latest candle for {symbol}...")
            latest_candle = broker.fetch_latest_candle(epic=symbol, resolution="MINUTE_15")
            
            if latest_candle is not None:
                # Update strategy with the latest candle
                strategies[symbol].update_ohlc(latest_candle)
                
                # Generate buy/sell signal
                signal = strategies[symbol].generate_signal()
                
                # Execute order based on the signal
                broker.update_positions()  # Ensure we have the latest positions
                if signal == "BUY":
                    broker.send_order(symbol=symbol, side="BUY", size=0.01)
                elif signal == "SELL":
                    broker.send_order(symbol=symbol, side="SELL", size=0.01)

        # Sleep until the next :15, :30, :45, or :00 on the clock + 5 seconds
        sleep_time = get_seconds_until_next_quarter_plus_5_seconds()
        print(f"Sleeping for {sleep_time} seconds until the next quarter-hour mark.")
        time.sleep(sleep_time)

# Position management logic (UPL checking, take-profit, stop-loss, etc.)
def position_management():
    while True:
        for symbol in broker.open_positions.keys():
            # Check if the UPL has reached the take-profit level or stop level
            if broker.check_take_profit(symbol):
                print(f"Take-profit reached for {symbol}, closing the position.")
                continue
            
            # Optionally, handle trailing stop or other position management checks here
            
        # Sleep for 1-2 minutes before checking again
        time.sleep(30)

# Initialize strategies for all symbols
def initialize_strategies():
    for symbol in symbols:
        print(f"Fetching initial 200 candles for {symbol}...")
        ohlc_data = broker.get_historical_data_in_chunks(epic=symbol, resolution="MINUTE_15", start_date="2024-09-15T00:00:00")
        strategies[symbol] = TripleMAMACDStrategy(ohlc_data)

if __name__ == "__main__":
    # Define symbols to monitor
    symbols = ["BTCUSD", "ETHUSD", "EURUSD", "GBPUSD", "GOLD", "US100", "US30", "US500", "OIL_BRENT"]
    strategies = {}

    # Initialize the broker API
    config = configparser.ConfigParser()
    config.read('/home/botuser/macd_ema/mac_triplema/config.ini')
    api_key = config['broker']['api_key']
    password = config['broker']['password']
    account_id = config['broker']['account_id']
    broker = BrokerAPI(api_key=api_key, login=account_id, password=password)

    # Initialize strategies
    initialize_strategies()

    # Run the strategy logic in one thread (for generating signals every 15 minutes)
    strategy_thread = Thread(target=strategy_logic)
    strategy_thread.start()

    # Run the position management logic in another thread (for UPL checking every minute or two)
    position_thread = Thread(target=position_management)
    position_thread.start()

    # Join both threads to ensure they continue running
    strategy_thread.join()
    position_thread.join()
