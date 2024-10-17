import pandas as pd
import pandas_ta as ta

class BollingerBandStrategy:
    def __init__(self, ohlc_data_4h, ohlc_data_1h):
        # Initialize with OHLC data (Open, High, Low, Close)
        self.ohlc_4h = pd.DataFrame(ohlc_data_4h)
        self.ohlc_1h = pd.DataFrame(ohlc_data_1h)
        self.calculate_indicators()

    def calculate_indicators(self):
        # Calculate Bollinger Bands with a 20-period moving average and 2 standard deviations
        bbands = ta.bbands(self.ohlc_4h['Close'], length=20, std=2)
        self.ohlc_4h["bb_upper"] = bbands["BBU_20_2.0"]
        self.ohlc_4h["bb_middle"] = bbands["BBM_20_2.0"]
        self.ohlc_4h["bb_lower"] = bbands["BBL_20_2.0"]

        # Calculate the Moving Average (Middle Band is essentially the 20-period moving average)
        self.ohlc_4h["ma20"] = self.ohlc_4h["bb_middle"]

    def scan_4h_chart(self):
        """
        Scan the 4-hour chart for two or more strong bars, expanding Bollinger Bands, and an angled moving average.
        """
        # Assuming OHLC data for the 4-hour timeframe is already present in the DataFrame
        last_row = self.ohlc_4h.iloc[-1]

        # Check for two long solid bars
        strong_bars = self.ohlc_4h['Close'][-2] - self.ohlc_4h['Open'][-2] > (self.ohlc_4h['High'][-2] - self.ohlc_4h['Low'][-2]) / 2 \
                      and self.ohlc_4h['Close'][-1] - self.ohlc_4h['Open'][-1] > (self.ohlc_4h['High'][-1] - self.ohlc_4h['Low'][-1]) / 2
        
        # Check if Bollinger Bands are expanding
        bands_expanding = last_row["bb_upper"] - last_row["bb_lower"] > (self.ohlc["bb_upper"] - self.ohlc["bb_lower"]).mean()

        # Check for angled moving average
        ma_angling_up = last_row["ma20"] > self.ohlc["ma20"].mean()

        if strong_bars and bands_expanding and ma_angling_up:
            return "STRONG_MOVE_UP"
        elif strong_bars and bands_expanding and not ma_angling_up:
            return "STRONG_MOVE_DOWN"
        return None

    def pullback_1h(self):
        """
        Look for a pullback on the 1-hour chart where the price touches or comes close to the moving average.
        """
        last_row = self.ohlc_1h.iloc[-1]
        
        # Check if price pulls back within 5 pips of the 20-period MA
        pullback = abs(last_row['Close'] - last_row['ma20']) <= 0.0005
        
        # Bollinger Bands should contract during the pullback
        bands_contracting = last_row["bb_upper"] - last_row["bb_lower"] < (self.ohlc["bb_upper"] - self.ohlc["bb_lower"]).mean()
        
        if pullback and bands_contracting:
            return True
        return False

    def check_entry_patterns(self):
        """
        Check for valid entry patterns like Engulfing Candle, Three-Bar Reversal, or Pin Bar.
        """
        # Get the last 3 candles for pattern analysis
        last_candles = self.ohlc_1h.iloc[-3:]

        # Engulfing Candle Pattern
        if (last_candles.iloc[-2]['Open'] < last_candles.iloc[-2]['Close']) and \
           (last_candles.iloc[-1]['Open'] > last_candles.iloc[-1]['Close']) and \
           (last_candles.iloc[-1]['Close'] < last_candles.iloc[-2]['Open']) and \
           (last_candles.iloc[-1]['Open'] > last_candles.iloc[-2]['Close']):
            return "ENGULFING"

        # Three-Bar Reversal Pattern (Bullish or Bearish)
        if (last_candles.iloc[-3]['Close'] < last_candles.iloc[-2]['Close'] > last_candles.iloc[-1]['Close']):
            return "THREE_BAR_BULLISH"
        elif (last_candles.iloc[-3]['Close'] > last_candles.iloc[-2]['Close'] < last_candles.iloc[-1]['Close']):
            return "THREE_BAR_BEARISH"
        
        # Pin Bar Pattern
        if abs(last_candles.iloc[-1]['High'] - last_candles.iloc[-1]['Close']) > 2 * abs(last_candles.iloc[-1]['Open'] - last_candles.iloc[-1]['Close']):
            return "PIN_BAR"
        
        return None

    def generate_signal(self):
        """
        Combine signals from different checks to generate buy/sell decisions.
        """
        # First check for strong move on the 4-hour chart
        strong_move = self.scan_4h_chart()
        
        # Wait for the 1-hour pullback
        if self.pullback_1h() and strong_move:
            # Check for entry patterns on the pullback
            entry_pattern = self.check_entry_patterns()
            
            # If a valid entry pattern is found, return a signal based on the strong move
            if entry_pattern:
                if strong_move == "STRONG_MOVE_UP":
                    return "BUY"
                elif strong_move == "STRONG_MOVE_DOWN":
                    return "SELL"
        
        return None

    def set_targets_and_stop_loss(self, signal):
        """
        Set stop loss and take profit based on recent swing points and 1:1 risk-reward ratio.
        """
        last_row = self.ohlc_1h.iloc[-1]
        
        # For a buy trade, stop loss is below the recent swing low, and for sell, it's above the recent swing high
        if signal == "BUY":
            stop_loss = last_row["Low"] - (last_row["High"] - last_row["Low"])  # Swing low stop loss
            take_profit = last_row["Close"] + (last_row["Close"] - stop_loss)   # 1:1 RR take profit
        elif signal == "SELL":
            stop_loss = last_row["High"] + (last_row["High"] - last_row["Low"]) # Swing high stop loss
            take_profit = last_row["Close"] - (stop_loss - last_row["Close"])   # 1:1 RR take profit
        else:
            stop_loss, take_profit = None, None
        
        return stop_loss, take_profit

    def update_ohlc(self, latest_candle_4h, latest_candle_1h):
        # Ensure the latest candle is in the correct format (DataFrame)
        if isinstance(latest_candle_4h, dict):
            latest_candle_4h = pd.DataFrame([latest_candle_4h])
        elif isinstance(latest_candle_4h, pd.Series):
            latest_candle_4h = pd.DataFrame([latest_candle_4h])
        # Ensure the latest candle is in the correct format (DataFrame)
        if isinstance(latest_candle_1h, dict):
            latest_candle_1h = pd.DataFrame([latest_candle_4h])
        elif isinstance(latest_candle_1h, pd.Series):
            latest_candle_1h = pd.DataFrame([latest_candle_4h])

        # Concatenate the latest candle to the existing OHLC data
        self.ohlc_4h = pd.concat([self.ohlc_4h, latest_candle_4h], ignore_index=True)
        self.ohlc_1h = pd.concat([self.ohlc_1h, latest_candle_1h], ignore_index=True)
        
        # Recalculate the indicators for the entire dataset
        self.calculate_indicators()
