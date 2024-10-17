import http.client
import json
from broker import BrokerAPI
from strategy import TripleMAMACDStrategy
import time
import configparser
from trailing import TakeProfitStopLossHandler

# Initialize configparser to load the config file
config = configparser.ConfigParser()
config.read('/home/botuser/macd_ema/mac_triplema/config.ini')
print("Sections loaded:", config.sections())

# Fetch the API key, login, and password from the 'broker' section
api_key = config['broker']['api_key']
password = config['broker']['password']
account_id = config['broker']['account_id']
broker = BrokerAPI(api_key=api_key, login=account_id, password=password,acc_id=None)

# Fetch account IDs from the Capital.com API
def get_account_ids(broker):
    conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")
    headers = {
        'X-SECURITY-TOKEN': broker.x_security_token,  # Use the token from your BrokerAPI session
        'CST': broker.cst,  # Use the CST from your BrokerAPI session
        'Content-Type': 'application/json'
    }
    
    # Make the GET request to retrieve the list of accounts
    conn.request("GET", "/api/v1/accounts", headers=headers)
    res = conn.getresponse()
    data = res.read()
    
    # Decode the response and convert it to JSON
    accounts = json.loads(data.decode("utf-8"))
    
    # Print account information
    print("Available Accounts:")
    for account in accounts['accounts']:
        account_id = account['accountId']
        account_type = account['accountType']
        account_balance = account['balance']['available']
        print(f"Account ID: {account_id}, Type: {account_type}, Available Balance: {account_balance}")
    
    conn.close()

# Run the function to fetch and display account IDs
get_account_ids(broker)
