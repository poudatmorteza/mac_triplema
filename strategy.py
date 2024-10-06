import pandas as pd
import numpy as np
import pandas_ta as ta

class TripleMAMACDStrategy:
    def __init__(self, ohlc_data):
        self.ohlc = pd.DataFrame(ohlc_data)
        self.calculate_indicators()

    def calculate_indicators(self):
        # Calculate EMAs
        self.ohlc["ema50"] = ta.ema(self.ohlc["Close"], length=50)
        self.ohlc["ema21"] = ta.ema(self.ohlc["Close"], length=21)
        self.ohlc["ema200"] = ta.ema(self.ohlc["Close"], length=200)

        # Calculate MACD
        macd = self.ohlc.ta.macd()
        self.ohlc["macd_signal"] = macd["MACDs_12_26_9"]
        self.ohlc["macd"] = macd["MACD_12_26_9"]

    def generate_signal(self):
        # Calculate buy/sell signals based on Triple MA and MACD
        ema_signal = self.get_ema_signal()
        macd_signal = self.get_macd_signal()

        if ema_signal == "BUY" and macd_signal == "BUY":
            return "BUY"
        elif ema_signal == "SELL" and macd_signal == "SELL":
            return "SELL"
        return None

    def get_ema_signal(self):
        # Generate EMA signal based on crossover
        last = self.ohlc.iloc[-1]
        if last["ema21"] > last["ema50"] > last["ema200"]:
            return "BUY"
        elif last["ema21"] < last["ema50"] < last["ema200"]:
            return "SELL"
        return None

    def get_macd_signal(self):
        # Generate MACD signal based on crossover
        last = self.ohlc.iloc[-1]
        if last["macd"] > last["macd_signal"]:
            return "BUY"
        elif last["macd"] < last["macd_signal"]:
            return "SELL"
        return None

    def update_ohlc(self, latest_candle):
        # Ensure the latest candle is in the correct format (DataFrame)
        if isinstance(latest_candle, dict):
            latest_candle = pd.DataFrame([latest_candle])
        elif isinstance(latest_candle, pd.Series):
            latest_candle = pd.DataFrame([latest_candle])
        
        # Concatenate the latest candle to the existing OHLC data
        self.ohlc = pd.concat([self.ohlc, latest_candle], ignore_index=True)
        
        # Recalculate the indicators for the entire dataset
        self.calculate_indicators()


