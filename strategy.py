import pandas as pd
import numpy as np
import pandas_ta as ta
import talib

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
        #macd = self.ohlc.ta.macd(close='Close', fast=12, slow=26, signal=9)
        macd, signal, hist = talib.MACD(self.ohlc["Close"], fastperiod=12, slowperiod=26, signalperiod=9)
        self.ohlc["macd_signal"] = signal
        self.ohlc["macd"] = macd

        # calculate rsi
        self.ohlc["rsi"] = ta.rsi(self.ohlc["Close"], length=14)

        # Calculate the slopes of the EMAs 
        rolling_period = 10

        self.ohlc["slope_ema21"] = self.ohlc["ema21"].diff(periods=1)
        self.ohlc["slope_ema50"] = self.ohlc["ema50"].diff(periods=1)
        self.ohlc["slope_ema200"] = self.ohlc["ema200"].diff(periods=1)

        self.ohlc["slope_ema21"] = self.ohlc["slope_ema21"].rolling(window=rolling_period).mean()
        self.ohlc["slope_ema50"] = self.ohlc["slope_ema50"].rolling(window=rolling_period).mean()
        self.ohlc["slope_ema200"] = self.ohlc["slope_ema200"].rolling(window=rolling_period).mean()

    def generate_signal(self):
        # Calculate buy/sell signals based on Triple MA and MACD
        ema_signal = self.get_ema_signal()
        macd_signal = self.get_macd_signal()

        # Fetch the latest RSI value
        last_rsi = self.ohlc.iloc[-1]["rsi"]

        # Define RSI levels for overbought and oversold
        rsi_overbought = 70
        rsi_oversold = 30


        # Filter the signals based on RSI
        if ema_signal == "BUY" and macd_signal == "BUY":
            # Check if RSI is not overbought
            if last_rsi < rsi_overbought:
                return "BUY"
            else:
                print(f"Ignoring BUY signal due to RSI overbought: {last_rsi}")
                return None
        elif ema_signal == "SELL" and macd_signal == "SELL":
            # Check if RSI is not oversold
            if last_rsi > rsi_oversold:
                return "SELL"
            else:
                print(f"Ignoring SELL signal due to RSI oversold: {last_rsi}")
                return None
        elif ema_signal == "CLOSEBUY":
            return "CLOSEBUY"
        elif ema_signal == "CLOSESELL":
            return "CLOSESELL"
        return None

    def get_ema_signal(self):
        # Generate EMA signal based on crossover

        # Generate the ema signal
        # conditions = [
        #     ( (ohlc['ema21']<ohlc['ema50']) & (ohlc['ema50']<ohlc['ema200']) & (ohlc['slope_ema21']<0) & (ohlc['slope_ema50']<0) & (ohlc['slope_ema200']<0) ),
        #     ( (ohlc['ema21']>ohlc['ema50']) & (ohlc['ema50']>ohlc['ema200']) & (ohlc['slope_ema21']>0) & (ohlc['slope_ema50']>0) & (ohlc['slope_ema200']>0) )
        #         ]

        last = self.ohlc.iloc[-1]
        print(f'EMA21:{last['ema21']} & EMA50:{last['ema50']} & EMA200:{last['ema200']} & SLOPE 21: {last['slope_ema21']} & SLOPE 50: {last['slope_ema50']} & SLOPE 200: {last['slope_ema200']}' )
        if (last['ema21']>last['ema50']) & (last['ema50']>last['ema200']) & (last['slope_ema21']>0) & (last['slope_ema50']>0) & (last['slope_ema200']>0):
            print("EMA SIGNAL:BUY")
            return "BUY"
        elif (last['ema21']<last['ema50']) & (last['ema50']<last['ema200']) & (last['slope_ema21']<0) & (last['slope_ema50']<0) & (last['slope_ema200']<0):
            print("EMA SIGNAL:SELL")
            return "SELL"
        elif (last["ema21"] < last["ema50"]) and (last["ema21"]  > last["ema200"]) and (last["ema50"]  > last["ema200"]):
            print("EMA SIGNAL:CLOSEBUY")
            return "CLOSEBUY"
        elif (last["ema21"] > last["ema50"]) and (last["ema21"]  < last["ema200"]) and (last["ema50"]  < last["ema200"]):
            print("EMA SIGNAL:CLOSESELL")
            return "CLOSESELL"
        return None

    def get_macd_signal(self):
        # Generate MACD signal based on crossover
        last = self.ohlc.iloc[-1]
        if last["macd"] > last["macd_signal"]:
            print(f'MACD BUY:{last["macd"]} : {last["macd_signal"]}' )
            return "BUY"
        elif last["macd"] < last["macd_signal"]:
            print(f'MACD SELL:{last["macd"]} : {last["macd_signal"]}' )
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


