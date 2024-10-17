import configparser
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas_ta as ta
from broker import BrokerAPI

config = configparser.ConfigParser()
config.read('/home/botuser/macd_ema/mac_triplema/config.ini')
api_key = config['broker']['api_key']
password = config['broker']['password']
account_id = config['broker']['account_id']
broker = BrokerAPI(api_key=api_key, login=account_id, password=password, acc_id="243609514238366878")
ohlc_data = broker.get_historical_data_in_chunks(epic="EURUSD", resolution="MINUTE_15", start_date="2024-09-15T00:00:00")


# Define the strategy based on TripleMAMACDStrategy
class TripleMAMACDStrategy(Strategy):
    def init(self):
        # Initialize EMAs
        self.ema50 = self.I(ta.ema, self.data.Close, length=50)
        self.ema21 = self.I(ta.ema, self.data.Close, length=21)
        self.ema200 = self.I(ta.ema, self.data.Close, length=200)

        # Initialize MACD
        self.macd = self.I(lambda x: ta.macd(x)["MACD_12_26_9"], self.data.Close)
        self.macd_signal = self.I(lambda x: ta.macd(x)["MACDs_12_26_9"], self.data.Close)

        # Initialize RSI
        self.rsi = self.I(ta.rsi, self.data.Close, length=14)

    def next(self):
        # EMA crossover logic
        if crossover(self.ema21, self.ema50) and crossover(self.ema50, self.ema200):
            if self.rsi[-1] < 70 and self.macd[-1] > self.macd_signal[-1]:
                self.buy()  # BUY signal
        elif crossover(self.ema50, self.ema21) and crossover(self.ema200, self.ema50):
            if self.rsi[-1] > 30 and self.macd[-1] < self.macd_signal[-1]:
                self.sell()  # SELL signal

# Set up and run the backtest
bt = Backtest(ohlc_data, TripleMAMACDStrategy, cash=10000, commission=0.001, trade_on_close=True)

# Run the backtest
stats = bt.run()

# Print stats
print(stats)

# Plot results
bt.plot()
