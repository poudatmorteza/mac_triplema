class Position:
    def __init__(self, position_id, symbol, account_balance):
        self.position_id = position_id  # The unique position ID
        self.symbol = symbol  # Symbol of the asset
        self.current_profit = 0  # UPL, which will be updated each cycle
        self.stop_level = 0  # Stop level, which will be dynamically updated
        self.account_balance = account_balance  # Account balance to calculate milestones
        self.step_value = account_balance * 0.001  # 0.001% of account balance (e.g., $1 for $1000 balance)

    def update_profit(self, new_profit):
        self.current_profit = new_profit

        # Check if the profit has reached a milestone and update the stop level accordingly
        if self.current_profit >= self.step_value:
            # Calculate how many steps (0.001% increments) have been reached
            milestones_reached = int(self.current_profit // self.step_value)
            self.stop_level = (milestones_reached - 1) * self.step_value
            print(f"Updated stop level for {self.symbol} to {self.stop_level}")

    def is_below_stop_level(self):
        # Return True if the profit drops below the stop level
        return self.current_profit < self.stop_level