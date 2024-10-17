import time
from threading import Thread
from broker import BrokerAPI
from strategy import TripleMAMACDStrategy
import time
import configparser
from datetime import datetime, timedelta
from position import Position

position_container = {}
class Position:
    def __init__(self, position_id, symbol, account_balance):
        self.position_id = position_id  # The unique position ID
        self.symbol = symbol  # Symbol of the asset
        self.current_profit = 0  # UPL, which will be updated each cycle
        self.stop_level = 0  # Stop level, which will be dynamically updated
        self.account_balance = account_balance  # Account balance to calculate milestones
        self.step_value = account_balance * 0.001  # 0.001% of account balance (e.g., $1 for $1000 balance)
        self.is_break_even=False
        self.milestones_reached = 0

    def need_to_be_updated(self, current_profit):
        pass

    def update_profit(self, new_profit):
        self.current_profit = new_profit
        milestones_now = int(self.current_profit // self.step_value)

        # Check if the profit has reached a milestone and update the stop level accordingly
        if milestones_now > self.milestones_reached:
            self.is_break_even = True
            self.milestones_reached = milestones_now
            self.stop_level = (milestones_now - 1) * self.step_value
            print(f"Updated stop level for {self.symbol} to {self.stop_level}")
        else:
            print(f"Milestone not reached {self.symbol}:{self.current_profit}X{self.milestones_reached} will stops at {self.stop_level}")

    def is_below_stop_level(self):
        # Return True if the profit drops below the stop level
        if self.is_break_even:
            return self.current_profit < self.stop_level
        else:
            return False
        
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
            broker.start_session()
            latest_candle = broker.fetch_latest_candle(epic=symbol, resolution="MINUTE_15")
            
            if latest_candle is not None:
                # Update strategy with the latest candle
                strategies_tiple_ema[symbol].update_ohlc(latest_candle)
                
                # Generate buy/sell signal
                signal = strategies_tiple_ema[symbol].generate_signal()
                
                # Execute order based on the signal
                broker.update_positions()  # Ensure we have the latest positions
                if signal == "BUY":
                    broker.send_order(symbol=symbol, side="BUY", size=0.01)
                elif signal == "SELL":
                    broker.send_order(symbol=symbol, side="SELL", size=0.01)
                elif symbol in broker.open_positions:
                    if (broker.open_positions[symbol]["direction"]=="BUY" and signal == "CLOSEBUY") or (broker.open_positions[symbol]["direction"]=="SELL" and signal== "CLOSESELL‚"):
                        broker.close_position(symbol=symbol)
                        
        # Sleep until the next :15, :30, :45, or :00 on the clock + 5 seconds
        sleep_time = get_seconds_until_next_quarter_plus_5_seconds()
        print(f"Sleeping for {sleep_time} seconds until the next quarter-hour mark.")
        time.sleep(sleep_time)

# Position management logic (UPL checking, take-profit, stop-loss, etc.)
def position_management_():
    while True:
        positions_copy = list(broker.open_positions.keys()) 
        for symbol in positions_copy:
            # Check if the UPL has reached the take-profit level or stop level
            if broker.check_take_profit(symbol):
                print(f"Take-profit reached for {symbol}, closing the position.")
                continue

            
            # Optionally, handle trailing stop or other position management checks here
            
        # Sleep for 1-2 minutes before checking again
        time.sleep(10)

def position_management_():
    while True:
        positions_copy = list(broker.open_positions.keys()) 
        for symbol in positions_copy:
            # Check the dynamic take-profit for each open position
            broker.monitor_dynamic_take_profit(symbol)
            
        # Sleep for 30 seconds before checking again
        time.sleep(15)

# Position management logic (UPL checking, take-profit, stop-loss, etc.)
def position_management():
    # Dictionary to store open positions (position_id: Position object)
    positions = {}

    while True:
        # Get all open positions from the broker
        broker.update_positions()
        open_positions = broker.open_positions


        positions_to_remove = [existing_position for existing_position in positions if existing_position not in open_positions]
        
        for existing_position in positions_to_remove:
            print(f"Position {existing_position} is closed externally, removing from tracking.")
            del positions[existing_position]

        for symbol, position in open_positions.items():
            
            # Get the position details from the broker
            position_id = position["position_id"]
            current_profit = position["upl"]  # Fetch current UPL
            if position_id not in position_container:
                account_balance = broker.get_account_balance()["balance"]  # Fetch account balance
                inst = Position(position_id, symbol, account_balance)
                inst.update_profit(current_profit)
                position_container[position_id]=inst
            else:
                position_container[position_id].update_profit(current_profit)

            # Check if the position's profit has dropped below the stop level
            if position_container[position_id].is_below_stop_level():
                print(f"Profit for {symbol} dropped below the stop level, closing position.")
                broker.close_position(symbol)  # Close the position
                del positions[position_id]  # Remove the position from the local dictionary

        # Sleep for 10 seconds before checking again
        time.sleep(10)

# Initialize strategies for all symbols
def initialize_strategies():
    for symbol in symbols:
        print(f"Fetching initial 200 candles for {symbol}...")
        ohlc_data = broker.get_historical_data_in_chunks(epic=symbol, resolution="MINUTE_15", start_date="2024-09-15T00:00:00")
        strategies_tiple_ema[symbol] = TripleMAMACDStrategy(ohlc_data)

if __name__ == "__main__":
    # Define symbols to monitor
    symbols = [
        "BTCUSD", 
        "ETHUSD","AUDUSD","GBPJPY","USDCAD","USDCHF", "EURUSD", "GBPUSD", 
        "GOLD", "US100", "US30", "US500", "OIL_CRUDE","NATURALGAS","SILVER","COPPER"]
    strategies_tiple_ema = {}

    # Initialize the broker API
    config = configparser.ConfigParser()
    config.read('/home/botuser/macd_ema/mac_triplema/config.ini')
    api_key = config['broker']['api_key']
    password = config['broker']['password']
    account_id = config['broker']['account_id']
    broker = BrokerAPI(api_key=api_key, login=account_id, password=password,acc_id="243609514238366878")

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
