import http
import json
import time

class TakeProfitStopLossHandler:
    def __init__(self, broker, account_balance, trailing_step=10):
        """
        :param broker: The broker API instance
        :param account_balance: Initial account balance (e.g., $10,000)
        :param trailing_step: The step size for trailing the stop-loss (e.g., $10)
        """
        self.broker = broker
        self.trailing_step = trailing_step
        self.account_balance = account_balance

    def monitor_positions(self):
        """
        Monitor open positions and apply trailing stop-loss based on unrealized profit.
        """
        while True:
            # Step 1: Fetch current open positions
            self.broker.update_positions()

            # Step 2: Iterate through each open position
            for symbol, position in self.broker.open_positions.items():
                # Fetch unrealized profit (upl) for the position
                upl = self.get_upl_for_position(symbol)

                if upl is not None:
                    print(f"Monitoring {symbol}: UPL = {upl}")
                    # Step 3: Apply trailing stop-loss
                    self.apply_trailing_stop_loss(symbol, upl)

            # Sleep for a while before the next check (e.g., every 5 minutes)
            time.sleep(300)

    def get_upl_for_position(self, symbol):
        """
        Fetch unrealized profit/loss (upl) for the symbol.
        """
        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")
        url = "/api/v1/positions"
        headers = {
            "X-SECURITY-TOKEN": self.broker.x_security_token,
            "CST": self.broker.cst,
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
                    return pos['position']['upl']  # Return the unrealized profit (upl)
        else:
            print(f"Error fetching upl for {symbol}: {response.status} - {data}")
            return None

    def apply_trailing_stop_loss(self, symbol, upl):
        """
        Apply trailing stop-loss based on the current unrealized profit.
        """
        current_position = self.broker.open_positions[symbol]

        # Calculate the target upl levels for trailing stop-loss
        trailing_levels = [self.trailing_step * i for i in range(1, 100)]  # Generate trailing levels in steps

        # Determine the new stop-loss based on the current upl
        for level in trailing_levels:
            if upl >= level:
                new_stop_loss = level - self.trailing_step
                print(f"Setting stop-loss for {symbol} to {new_stop_loss}")
                self.set_stop_loss(symbol, new_stop_loss)

    def set_stop_loss(self, symbol, new_stop_loss):
        """
        Set the stop-loss for the given symbol.
        """
        conn = http.client.HTTPSConnection("demo-api-capital.backend-capital.com")
        url = f"/api/v1/positions/{self.broker.open_positions[symbol]['position_id']}/stop"
        headers = {
            "X-SECURITY-TOKEN": self.broker.x_security_token,
            "CST": self.broker.cst,
            "Content-Type": "application/json"
        }

        payload = {
            "stopLevel": new_stop_loss
        }

        body = json.dumps(payload)
        conn.request("POST", url, body=body, headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        conn.close()

        if response.status == 200:
            print(f"Stop-loss updated successfully for {symbol}: {new_stop_loss}")
        else:
            print(f"Error setting stop-loss for {symbol}: {response.status} - {data}")
