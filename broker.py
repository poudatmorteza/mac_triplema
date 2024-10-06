import pandas as pd
import requests
import http.client
import csv
from datetime import datetime, timedelta
import json

"https://demo-api-capital.backend-capital.com/"
# Broker API class to handle communication with Capital.com
class BrokerAPI:
    BASE_URL = "https://demo-api-capital.backend-capital.com/api/v1"
    
    def __init__(self, api_key, login, password):
        self.api_key = api_key
        self.login = login
        self.password = password
        self.cst = None
        self.x_security_token = None
        self.open_positions = {}
        self.session = self.start_session()

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
        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")
        
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
        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com" )
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
            print(f"Error fetching latest candle: {response.status_code} - {data}")
            return None

    # Save the fetched data to a CSV file
    def save_data_to_csv(self, data, epic):
        filename = f'{epic}.csv'
        prices = data.get('prices', [])
        
        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                writer.writerow(["snapshotTime", "openPrice_bid", "openPrice_ask", "closePrice_bid", "closePrice_ask", "highPrice_bid", "highPrice_ask", "lowPrice_bid", "lowPrice_ask", "lastTradedVolume"])
            for price in prices:
                writer.writerow([
                    price.get('snapshotTime'),
                    price['openPrice']['bid'],
                    price['openPrice']['ask'],
                    price['closePrice']['bid'],
                    price['closePrice']['ask'],
                    price['highPrice']['bid'],
                    price['highPrice']['ask'],
                    price['lowPrice']['bid'],
                    price['lowPrice']['ask'],
                    price.get('lastTradedVolume')
                ])

    def update_positions(self):
        """
        Fetch open positions from the broker and update self.open_positions.
        """
        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")

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

                # Save the position details (ID, direction, and size)
                self.open_positions[symbol] = {
                    "position_id": position_id,
                    "direction": direction,
                    "size": size
                }
        else:
            print(f"Error fetching positions: {response.status} - {data}")
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
        trade_value = balance["balance"] * 0.01

        # Step 3: Fetch the current price of the asset (epic)
        live_price = self.get_live_price(symbol)
        if live_price is None:
            print(f"Could not fetch live price for {symbol}.")
            return None

        # Assume bid price as the current price
        current_price = live_price['prices'][0]['closePrice']['bid']
        
        # Step 4: Calculate the size of the trade (trade_value / current_price)
        trade_size = trade_value / current_price
        return trade_size

    def send_order(self, symbol="EURUSD", side="BUY", size=1.0):

        self.update_positions()
        # Check if there's already an open position for this symbol
        if symbol in self.open_positions:
            # Check if the direction is the same, if not, close the existing position
            current_position = self.open_positions[symbol]
            if current_position["direction"] != side:
                print(f"Opposite position exists for {symbol}. Closing current {current_position['direction']} position.")
                self.close_position(symbol)  # Close the current opposite position
            return
            # Calculate the trade size based on 1% of the account balance

        trade_size = self.calculate_trade_size(symbol)
        if trade_size is None:
            print(f"Unable to calculate trade size for {symbol}.")
            return
        min_size = self.get_minimum_size(symbol)
        if min_size is not None and size < min_size:
            print(f"Order size for {symbol} is below the minimum allowed ({min_size}). Adjusting size to minimum.")
            size = min_size  # Adjust size to the minimum allowed

        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")

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
        if symbol not in self.open_positions:
            print(f"No open position for {symbol} to close.")
            return

        # Fetch the position ID
        position_id = self.open_positions[symbol]["position_id"]

        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")

        # Construct the URL to close the position
        url = f"/api/v1/positions/otc/{position_id}/close"

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

        # Send the POST request
        conn.request("POST", url, body=body, headers=headers)

        # Get the response
        response = conn.getresponse()
        data = response.read().decode("utf-8")

        if response.status == 200:
            print(f"Position for {symbol} closed successfully.")
            del self.open_positions[symbol]  # Remove the closed position from open_positions
        else:
            print(f"Error closing position: {response.status} - {data}")

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

    def get_minimum_size(self, epic):
        """
        Fetch minimum order size for the given symbol (epic).
        """
        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")
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
            print(f"Error fetching minimum size: {response.status_code} - {data}")
            return None
    
    def get_account_balance(self):
        """
        Fetch the current account balance from the broker.
        """
        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")

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
            print(f"Error fetching account balance: {response.status_code} - {data}")
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
        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")
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
                print(f"Take-profit not reached for {symbol}. Current profit: {unrealized_profit}")
                return False
        else:
            print(f"Error checking take-profit: {response.status_code} - {data}")
            return False
    

    def calculate_take_profit(self, balance):
        """
        Calculate 1% of the account balance for the take-profit target.
        """
        return balance["balance"] * 0.01
# Main function
if __name__ == "__main__":
    broker = BrokerAPI(api_key="your_api_key", login="your_login", password="your_password")
    
    # Step 1: Start the session
    broker.start_session()

    # Step 4: Fetch open positions
    positions = broker.get_positions()
    print(f"Current Positions: {positions}")

    # Step 5: Place a buy order for EURUSD
    broker.send_order(symbol="EURUSD", side="BUY", size=1.0)
