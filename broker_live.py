import pandas as pd
import requests
import http.client
import csv
from datetime import datetime, timedelta
import json


# Broker API class to handle communication with Capital.com
class BrokerAPILIVE:
    BASE_URL = "https://api-capital.backend-capital.com/api/v1"
    
    def __init__(self, api_key, login, password, acc_id=None):
        self.api_key = api_key
        self.login = login
        self.password = password
        self.cst = None
        self.x_security_token = None
        self.open_positions = {}
        self.session = self.start_session()

    def instrument_list(self):
        """
        Fetch the list of available instruments.
        """
        conn = http.client.HTTPSConnection("api-capital.backend-capital.com")
        
        # Construct the URL to get instruments
        url = "/api/v1/markets"  # Adjust the endpoint as needed
        headers = {
            'X-SECURITY-TOKEN': self.x_security_token,
            'CST': self.cst
        }

        # Make the API request to get the list of instruments
        conn.request("GET", url, body="", headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        conn.close()

        if response.status == 200:
            instruments_data = json.loads(data)
            
            # Print out the available instruments
            for market in instruments_data.get("markets", []):
                print(f"Instrument: {market['instrumentName']} (Epic: {market['epic']})")
                
            return instruments_data
        else:
            print(f"Error fetching instruments: {response.status} - {data}")
            return None
    
    def get_instrument_type(self, symbol):
        instrument_data = self.instrument_list()
        for epic in instrument_data:
            if symbol == epic["symbo"]:
                return epic["instrumentType"]
        

    # Start a session (log in)
    def start_session(self):
        headers = {
            "X-CAP-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "identifier": self.login,
            "password": self.password,
            "encryptedPassword": False
        }

        response = requests.post(f"{self.BASE_URL}/session", headers=headers, json=payload)
        
        if response.status_code == 200:
            print("Login successful")
            self.cst = response.headers.get('CST')
            self.x_security_token = response.headers.get('X-SECURITY-TOKEN')

            # Properly assign self.session as a requests.Session() object
            self.session = requests.Session()
            self.session.headers.update({
                "X-CAP-API-KEY": self.api_key,
                "CST": self.cst,
                "X-SECURITY-TOKEN": self.x_security_token
            })
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
        return self.session

    def get_historical_data_in_chunks(self, epic="EURUSD", resolution="MINUTE_5", start_date="2023-01-01T00:00:00", max=1000):
        conn = http.client.HTTPSConnection("api-capital.backend-capital.com")
        
        # Construct request headers
        headers = {
            'X-SECURITY-TOKEN': self.x_security_token,
            'CST': self.cst
        }

        # Initialize date objects
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%S')
        end_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S')

        all_data = []  # List to store all chunks of price data

        # Loop through the date range in 1-day chunks (you can reduce this to a few hours if necessary)
        while start_date_obj < end_date_obj:
            # Set chunk end date to 1 day after the start date (you can use smaller intervals if necessary)
            chunk_end_date_obj = start_date_obj + timedelta(days=1)
            if chunk_end_date_obj > end_date_obj:
                chunk_end_date_obj = end_date_obj

            # Convert date objects to strings
            start_date_str = start_date_obj.strftime('%Y-%m-%dT%H:%M:%S')
            chunk_end_date_str = chunk_end_date_obj.strftime('%Y-%m-%dT%H:%M:%S')

            # Construct request URL for the chunk
            url = f"/api/v1/prices/{epic}?resolution={resolution}&max={max}&from={start_date_str}&to={chunk_end_date_str}"

            # Make the API request for the current chunk
            conn.request("GET", url, '', headers)
            res = conn.getresponse()
            data = res.read().decode("utf-8")

            # Assuming the response is in JSON format
            price_data = json.loads(data).get('prices', [])
            
            if price_data:
                all_data.extend(price_data)  # Collect all price data

            # Move to the next chunk
            start_date_obj = chunk_end_date_obj

        # If no data is collected, return an empty DataFrame
        if not all_data:
            print("No data fetched.")
            return pd.DataFrame()

        # Convert the collected data to a pandas DataFrame
        df = pd.DataFrame(all_data)
        
        # Expand nested dictionary columns like openPrice, closePrice, etc.
        df = pd.concat([df.drop(['openPrice', 'closePrice', 'highPrice', 'lowPrice'], axis=1),
                        df['openPrice'].apply(pd.Series).rename(columns={'bid': 'open_bid', 'ask': 'open_ask'}),
                        df['closePrice'].apply(pd.Series).rename(columns={'bid': 'close_bid', 'ask': 'close_ask'}),
                        df['highPrice'].apply(pd.Series).rename(columns={'bid': 'high_bid', 'ask': 'high_ask'}),
                        df['lowPrice'].apply(pd.Series).rename(columns={'bid': 'low_bid', 'ask': 'low_ask'})],
                       axis=1)

        # Convert time to datetime
        df['snapshotTime'] = pd.to_datetime(df['snapshotTime'])
        # Rename columns to standard trading terms
        df = df.rename(columns={
            'snapshotTime': 'Date',
            'open_bid': 'Open',
            'close_bid': 'Close',
            'high_bid': 'High',
            'low_bid': 'Low',
            'lastTradedVolume': 'Volume'
        })

        # Return the final DataFrame with desired columns
        return df[['Date', 'Open', 'Close', 'High', 'Low', 'Volume']]

    # Fetch latest candle
    def fetch_latest_candle(self, epic="EURUSD", resolution="MINUTE_5"):
        conn = http.client.HTTPSConnection("api-capital.backend-capital.com" )
        url = f"/api/v1/prices/{epic}?resolution={resolution}&max=1"
        headers = {
            'X-SECURITY-TOKEN': self.x_security_token,
            'CST': self.cst
        }

        conn.request("GET", url, body="", headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        conn.close()

        if response.code == 200:
            price_data = json.loads(data).get('prices', [])
            if price_data:
                # Convert raw data to a DataFrame
                df = pd.DataFrame(price_data)

                # Extract 'bid' prices from nested dictionaries (openPrice, closePrice, etc.)
                df['Open'] = df['openPrice'].apply(lambda x: x['bid'] if isinstance(x, dict) else None)
                df['Close'] = df['closePrice'].apply(lambda x: x['bid'] if isinstance(x, dict) else None)
                df['High'] = df['highPrice'].apply(lambda x: x['bid'] if isinstance(x, dict) else None)
                df['Low'] = df['lowPrice'].apply(lambda x: x['bid'] if isinstance(x, dict) else None)
                df['Volume'] = df['lastTradedVolume']

                # Convert time to datetime
                df['Date'] = pd.to_datetime(df['snapshotTime'])

                # Return the final DataFrame with desired columns
                return df[['Date', 'Open', 'Close', 'High', 'Low', 'Volume']].iloc[-1:]
            else:
                print("No candle data found.")
                return None
        else:
            print(f"Error fetching latest candle: {response.code} - {data}")
            return None

    def update_positions(self):
        """
        Fetch open positions from the broker and update self.open_positions.
        """
        conn = http.client.HTTPSConnection("api-capital.backend-capital.com")

        # Construct the URL
        url = "/api/v1/positions"

        # Prepare the headers
        headers = {
            "X-SECURITY-TOKEN": self.x_security_token,
            "CST": self.cst,
            "Content-Type": "application/json"
        }

        # Send the GET request
        conn.request("GET", url, body='', headers=headers)

        # Get the response
        response = conn.getresponse()
        data = response.read().decode("utf-8")

        # Close the connection
        conn.close()

        if response.status == 200:
            # Parse the response data as JSON
            data_json = json.loads(data)

            # Clear the previous positions
            self.open_positions = {}

            # Loop through the positions and update self.open_positions
            for pos in data_json.get("positions", []):
                symbol = pos['market']['epic']
                position_id = pos['position']['dealId']
                direction = pos['position']['direction']
                size = pos['position']['size']
                upl = pos['position']['upl']

                # Save the position details (ID, direction, and size)
                self.open_positions[symbol] = {
                    "position_id": position_id,
                    "direction": direction,
                    "size": size,
                    "upl": upl
                }
        else:
            print(f"Error fetching positions: {response.status} - {data}")
            return None

    def get_contract_size(self, symbol):
        """
        Fetch the contract size (lot size) for the given symbol from the broker's API.
        """
        url = f"{self.BASE_URL}/markets?searchTerm={symbol}&epics={symbol}"
        response = self.session.get(url)
        
        if response.status_code == 200:
            market_data = response.json()
            markets = market_data.get("markets", [])
            if markets:
                # Extract the contract size (lot size) for the first matching market
                contract_size = markets[0].get("lotSize", None)
                return contract_size
            else:
                market_data = self.get_market_data(symbol)
                if market_data:
                    contract_size = market_data["instrument"].get("lotSize", None)
                    return contract_size
                else:
                    print(f"No market data found for {symbol}.")
                    return None
        else:
            print(f"Error fetching contract size: {response.status_code}, {response.text}")
            return None

    def get_leverage_by_symbol(self, symbol):
        """
        Fetch the leverage for the symbol based on its instrument type, using account preferences.
        
        :param symbol: The trading symbol (e.g., 'SILVER', 'EURUSD')
        :return: The leverage for the symbol's instrument type.
        """
        # Step 1: Fetch market details for the symbol to get the instrument type
        conn = http.client.HTTPSConnection("api-capital.backend-capital.com")
        payload = ''
        headers = {
            'X-SECURITY-TOKEN': self.x_security_token,
            'CST': self.cst
        }

        # Fetch market details (epic is the symbol, like 'SILVER')
        url = f"/api/v1/markets?searchTerm={symbol}&epics={symbol}"
        conn.request("GET", url, payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        market_data = json.loads(data)

        # Extract the instrument type from the response
        markets = market_data.get('markets', [])
        if not markets:
            print(f"No market data found for {symbol}.")
            market_data = self.get_market_data(symbol)
            if market_data:
                instrument_type = market_data["instrument"].get("type", None)
            else:
                return None
        else:
            instrument_type = markets[0].get('instrumentType', None)
        if not instrument_type:
            print(f"Instrument type not found for {symbol}.")
            return None

        # Step 2: Fetch account preferences to get leverage for the instrument type
        conn.request("GET", "/api/v1/accounts/preferences", payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        preferences = json.loads(data)

        # Extract leverage for the instrument type
        leverages = preferences.get('leverages', {})
        asset_leverage = leverages.get(instrument_type, {}).get('current', None)

        if asset_leverage:
            if instrument_type == "COMMODITIES":
                if symbol != "GOLD":
                    asset_leverage = 10
            print(f"Leverage for {symbol} ({instrument_type}): {asset_leverage}")
            return asset_leverage
        else:
            print(f"Leverage for instrument type {instrument_type} not found.")
            return None
        
    def calculate_trade_size(self, symbol):
        """
        Calculate the trade size based on 1% of the account balance.
        """
        # Step 1: Fetch the account balance
        balance = self.get_account_balance()
        if balance is None:
            print("Could not retrieve account balance.")
            return None

        # Step 2: Calculate 1% of the balance
        leverage = self.get_leverage_by_symbol(symbol) 
        trade_value = balance["balance"] * 0.04 * leverage

        # Step 3: Fetch the current price of the asset (epic)
        live_price = self.get_live_price(symbol)
        if live_price is None:
            print(f"Could not fetch live price for {symbol}.")
            return None

        # Assume bid price as the current price
        current_price = live_price['prices'][0]['closePrice']['bid']
        
        # Step 4: Fetch the contract size from the API
        contract_size = self.get_contract_size(symbol)
        if contract_size is None:
            print(f"Could not fetch contract size for {symbol}.")
            return None
        
        # Step 4: Calculate the size of the trade (trade_value / current_price)
        trade_size = trade_value / (contract_size * current_price)
        return trade_size

    def send_order(self, symbol="EURUSD", side="BUY", size=1.0, tp=None, sl=None):

        self.update_positions()
        # Check if there's already an open position for this symbol
        if symbol in self.open_positions:
            # Check if the direction is the same, if not, close the existing position
            current_position = self.open_positions[symbol]
            if current_position["direction"] != side:
                print(f"Opposite position exists for {symbol}. Closing current {current_position['direction']} position.")
                self.close_position(symbol)  # Close the current opposite position
            else:
                return
        
        # Calculate the trade size based on 1% of the account balance
        size = self.calculate_trade_size(symbol)
        if size is None:
            print(f"Unable to calculate trade size for {symbol}.")
            return
        min_size = self.get_minimum_size(symbol)
        if min_size is not None and size < min_size:
            print(f"Order size for {symbol}:{size} is below the minimum allowed ({min_size}). Adjusting size to minimum.")
            size = min_size  # Adjust size to the minimum allowed
        
        conn = http.client.HTTPSConnection("api-capital.backend-capital.com")

        # Construct the URL
        url = "/api/v1/positions"

        # Prepare the headers
        headers = {
            "X-SECURITY-TOKEN": self.x_security_token,
            "CST": self.cst,
            "Content-Type": "application/json"
        }

        # Prepare the payload (order details)
        payload = {
            "epic": symbol,
            "direction": side,  # "BUY" or "SELL"
            "size": size,
            "orderType": "MARKET",
            "guaranteedStop": False,
            "forceOpen": True,
            "currencyCode": "USD",
            "timeInForce": "FILL_OR_KILL"
        }

        
        # Convert the payload to a JSON string
        body = json.dumps(payload)

        # Send the POST request
        conn.request("POST", url, body=body, headers=headers)

        # Get the response
        response = conn.getresponse()
        data = response.read().decode("utf-8")

        # Handle the response
        if response.status == 200:
            print(f"Order placed successfully: {json.loads(data)}")

        else:
            print(f"Error placing order: {response.status} - {data}")

        conn.close()

    def close_position(self, symbol="EURUSD"):
        # Check if there is an open position for the symbol
        if symbol not in self.open_positions:
            print(f"No open position for {symbol} to close.")
            return

        # Fetch the position ID (deal ID)
        position_id = self.open_positions[symbol].get("position_id")
        if not position_id:
            print(f"Error: No position ID found for {symbol}.")
            return

        conn = http.client.HTTPSConnection("api-capital.backend-capital.com")

        # Construct the URL to close the position
        url = f"/api/v1/positions/{position_id}"

        # Prepare the headers
        headers = {
            "X-SECURITY-TOKEN": self.x_security_token,
            "CST": self.cst,
            "Content-Type": "application/json"
        }

        # Prepare the payload to close the full position
        payload = {
            "size": "full"  # Close the full position
        }

        # Convert the payload to JSON
        body = json.dumps(payload)

        try:
            # Send the POST request to close the position
            conn.request("DELETE", url, body=body, headers=headers)

            # Get the response
            response = conn.getresponse()
            data = response.read().decode("utf-8")

            if response.status == 200:
                print(f"Position for {symbol} closed successfully.")
                # Remove the closed position from open_positions
                del self.open_positions[symbol]
            else:
                print(f"Error closing position for {symbol}: {response.status} - {data}")
        
        except Exception as e:
            print(f"Exception occurred while closing the position: {e}")
        
        finally:
            conn.close()
            
    # Fetch live price quotes
    def get_live_price(self, symbol="EURUSD"):
        url = f"{self.BASE_URL}/prices/{symbol}/"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching live price: {response.status_code} - {response.text}")
            return None

    def calculate_stop_distance(self, symbol, side):
        """
        Calculate the stop distance based on 0.1% of the account balance, adjusted for symbol-specific price and tick size.
        :param symbol: The trading symbol (e.g., 'EURUSD', 'GOLD')
        :return: Calculated stop distance in pips/points
        """
        # Step 1: Fetch the account balance
        balance = self.get_account_balance()
        if balance is None:
            print("Could not retrieve account balance.")
            return None
        leverage = self.get_leverage_by_symbol(symbol=symbol)
        # Step 2: Calculate 0.1% of the balance
        stop_value = balance["balance"] * 0.001  # 0.1% of the account balance
        stop_value_leveraged = stop_value * leverage

        # Step 3: Fetch market data for the asset
        market_data = self.get_market_data(symbol)
        if market_data is None:
            print(f"Error fetching market data for {symbol}.")
            return None

        # Step 4: Extract necessary values from the market data
        current_price = market_data["snapshot"]["bid"]  # Bid price of the asset
        pip_position = market_data["snapshot"]["decimalPlacesFactor"]  # Decimal position for price
        tick_size = market_data["dealingRules"]["minSizeIncrement"]["value"]  # Minimum tick size

        # Step 6: Calculate the price movement that equals 0.1% of the account balance, adjusted for leverage
        stop_distance_in_price = stop_value_leveraged / current_price

        # Convert stop distance to pips/points
        stop_distance_in_pips = stop_distance_in_price / tick_size

        # Adjust based on pip position
        stop_distance_adjusted = round(stop_distance_in_pips, pip_position)

        # Step 7: Determine stop loss level based on order type
        if side == 'BUY':
            stop_loss_price = current_price - stop_distance_in_price
        elif side == 'SELL':
            stop_loss_price = current_price + stop_distance_in_price
        else:
            print("Invalid order type. Please specify 'BUY' or 'SELL'.")
            return None

        print(f"Calculated stop distance for {symbol}: {stop_distance_adjusted} pips. Stop loss level: {stop_loss_price}")
        return stop_distance_adjusted, stop_loss_price

    def get_market_data(self, symbol):
        url = f"{self.BASE_URL}/markets/{symbol}"
        response = self.session.get(url)
        if response.status_code == 200:
            market_data = response.json()
            return market_data  # Assuming you're working with the first result
        else:
            print(f"Error fetching market data: {response.status_code} - {response.text}")
            return None
        
    def get_minimum_size(self, epic):
        """
        Fetch minimum order size for the given symbol (epic).
        """
        conn = http.client.HTTPSConnection("api-capital.backend-capital.com")
        url = f"/api/v1/markets/{epic}"  # Adjust the endpoint if needed
        headers = {
            'X-SECURITY-TOKEN': self.x_security_token,
            'CST': self.cst
        }

        conn.request("GET", url, body="", headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        conn.close()


        if response.status == 200:
            market_data = json.loads(data)
            min_size = market_data["dealingRules"]['minDealSize']['value']  # Fetch the minimum deal size if available
            return min_size
        else:
            print(f"Error fetching minimum size: {response.status} - {data}")
            return None
    
    def get_account_balance(self):
        """
        Fetch the current account balance from the broker.
        """
        conn = http.client.HTTPSConnection("api-capital.backend-capital.com")

        # Construct the URL
        url = "/api/v1/accounts"

        # Prepare the headers
        headers = {
            "X-SECURITY-TOKEN": self.x_security_token,
            "CST": self.cst,
            "Content-Type": "application/json"
        }

        # Send the GET request
        conn.request("GET", url, body="", headers=headers)

        # Get the response
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        conn.close()

        if response.status == 200:
            account_data = json.loads(data)
            balance = account_data['accounts'][0]['balance']  # Assuming there's one account
            return balance
        else:
            print(f"Error fetching account balance: {response.status} - {data}")
            return None
    

    def check_take_profit(self, symbol):
        """
        Check if the open position for the symbol has reached the take-profit level.
        """
        if symbol not in self.open_positions:
            print(f"No open position for {symbol} to check TP.")
            return False

        # Get the current account balance
        balance = self.get_account_balance()
        if balance is None:
            print("Could not retrieve account balance.")
            return False

        # Calculate 1% TP target
        take_profit_target = self.calculate_take_profit(balance)

        # Fetch the current open positions (including unrealized profit)
        conn = http.client.HTTPSConnection("api-capital.backend-capital.com")
        url = f"/api/v1/positions"
        headers = {
            "X-SECURITY-TOKEN": self.x_security_token,
            "CST": self.cst,
            "Content-Type": "application/json"
        }

        conn.request("GET", url, body="", headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        conn.close()

        if response.status == 200:
            positions_data = json.loads(data)

            for pos in positions_data.get('positions', []):
                if pos['market']['epic'] == symbol:
                    unrealized_profit=0
                    unrealized_profit += pos['position']['upl']  # Unrealized profit

            print(f"Unrealized profit for {symbol}: {unrealized_profit}")
            if unrealized_profit >= take_profit_target:
                print(f"Take-profit reached for {symbol}. Closing position.")
                self.close_position(symbol)
                return True
            else:
                print(f"Take-profit not reached for {symbol}:{take_profit_target}$. Current profit: {unrealized_profit}")
                return False
        else:
            print(f"Error checking take-profit: {response.status} - {data}")
            return False
    

    def calculate_take_profit(self, balance):
        """
        Calculate 1% of the account balance for the take-profit target.
        """
        return balance["balance"] * 0.001
    
    def monitor_dynamic_take_profit(self, symbol):
        """
        Monitor open positions dynamically based on profit milestones:
        - Start monitoring once the profit reaches 1x.
        - Close the position only if profit drops below the dynamic stop level.
        """
        if symbol not in self.open_positions:
            print(f"No open position for {symbol} to check TP.")
            return False

        # Get the current account balance
        balance = self.get_account_balance()
        if balance is None:
            print("Could not retrieve account balance.")
            return False

        # Calculate the base target (1% of the balance)
        base_tp_target = balance["balance"] * 0.001
        base_sl_target = balance["balance"] * 0.01
        # Fetch open positions and their unrealized profit
        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")
        url = f"/api/v1/positions"
        headers = {
            "X-SECURITY-TOKEN": self.x_security_token,
            "CST": self.cst,
            "Content-Type": "application/json"
        }

        conn.request("GET", url, body='', headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        conn.close()

        if response.status == 200:
            positions_data = json.loads(data)

            for pos in positions_data.get('positions', []):
                if pos['market']['epic'] == symbol:
                    # Get the current unrealized profit
                    unrealized_profit = pos['position']['upl']

                    # Check if we are tracking this position's stop level
                    if 'dynamic_stop_level' not in self.open_positions[symbol]:
                        # Only track dynamic stop levels once profit exceeds 1x
                        if unrealized_profit >= base_tp_target:
                            # Initialize the stop level to breakeven (0)
                            self.open_positions[symbol]['dynamic_stop_level'] = 0
                            print(f"Profit for {symbol} has reached 1x({base_tp_target}$). Starting to track dynamic stop.")
                        else:
                            # Do not close position; profit hasn't reached the first target yet
                            print(f"Profit for {symbol} is below 1x({base_tp_target}$), no action taken.")
                            if unrealized_profit< -1 * base_sl_target:
                                print(f"STOP LOSS Reached. Cloing Position for symbol: {symbol}")
                                self.close_position(symbol)


                    # If we are already tracking, continue dynamic take profit management
                    try:
                        current_stop_level = self.open_positions[symbol]['dynamic_stop_level']
                        milestone_reached = int(unrealized_profit // base_tp_target)
                        print(f'{symbol} Profit: {unrealized_profit}, Stop Level: {current_stop_level}:{current_stop_level*base_tp_target}')
                        if milestone_reached > current_stop_level:
                            # Update the stop level to one milestone below the current milestone
                            self.open_positions[symbol]['dynamic_stop_level'] = milestone_reached - 1
                            print(f"Profit for {symbol} reached {milestone_reached}x. Stop level set to {milestone_reached - 1}x({base_tp_target}$):{current_stop_level}.")
                        # Close the position if the profit drops below the dynamic stop level
                        stop_level_profit = self.open_positions[symbol]['dynamic_stop_level'] * base_tp_target
                        if unrealized_profit < stop_level_profit:
                            print(f"Profit for {symbol} dropped below the stop level ({stop_level_profit}). Closing position.")
                            self.close_position(symbol)
                    except Exception as e:
                        print(f"Error in fetching data positin {symbol}:{e}")  

                    


            print(f"Profit for {symbol} is still running.")

        else:
            print(f"Error checking take-profit: {response.status} - {data}")
        
# Main function
if __name__ == "__main__":
    broker = BrokerAPILIVE(api_key="your_api_key", login="your_login", password="your_password")
    
    # Step 1: Start the session
    broker.start_session()

    # Step 4: Fetch open positions
    positions = broker.get_positions()
    print(f"Current Positions: {positions}")

    # Step 5: Place a buy order for EURUSD
    broker.send_order(symbol="EURUSD", side="BUY", size=1.0)
