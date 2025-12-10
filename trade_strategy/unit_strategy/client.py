from finance_client import ClientBase

class UnitStrategyClient:
    def __init__(self, symbol: str, open_units: list, close_units: list, finance_client:ClientBase,
                 length:int, amount: float, threshold: float = 0.5):
        self.symbol = symbol
        self.open_units = open_units
        self.close_units = close_units

        ohlc_columns = finance_client.get_ohlc_columns()
        open_column = ohlc_columns.get('Open')
        high_column = ohlc_columns.get('High')
        low_column = ohlc_columns.get('Low')
        close_column = ohlc_columns.get('Close')
        volume_column = ohlc_columns.get('Volume')
        spread_column = ohlc_columns.get('Spread')
        self.finance_client = finance_client
        self.open_column = open_column
        self.high_column = high_column
        self.low_column = low_column
        self.close_column = close_column
        self.volume_column = volume_column
        self.spread_column = spread_column
        self.length = length
        self.amount = amount
        self.threshold = threshold

    def execute_strategy(self, data):
        # Placeholder for strategy execution logic
        print(f"Executing strategy with data: {data}")
        data = self.finance_client.get_ohlc(symbols=self.symbol, length=self.length)

        positions = self.finance_client.get_positions()

        if len(positions) == 0:
            for open_unit in self.open_units:
                # Implement the actual strategy logic here
                print(f"Processing open unit: {open_unit}")
                signal = open_unit(data=data,
                        open_column=self.open_column,
                        high_column=self.high_column,
                        low_column=self.low_column,
                        close_column=self.close_column,
                        volume_column=self.volume_column,
                        spread_column=self.spread_column)
                if signal >= self.threshold:
                    print("Generate Buy Signal")
                    self.finance_client.open_trade(is_buy=True, symbol=self.symbol, amount=self.amount)
                    break
                elif signal <= -self.threshold:
                    print("Generate Sell Signal")
                    self.finance_client.open_trade(is_buy=False, symbol=self.symbol, amount=self.amount)
                    break
        else:
            for close_unit in self.close_units:
                # Implement the actual strategy logic here 
                print(f"Processing close unit: {close_unit}")
                for close_unit in self.close_units:
                    # Implement the actual strategy logic here
                    print(f"Processing close unit: {close_unit}")
                    _positions = positions.copy()
                    for position in _positions:
                        signal = close_unit(position=position.position_type.value,
                            price=position.price,
                            data=data,
                            open_column=self.open_column,
                            high_column=self.high_column,
                            low_column=self.low_column,
                            close_column=self.close_column,
                            volume_column=self.volume_column,
                            spread_column=self.spread_column)
                        if signal == 1 or signal == -1:
                            print(f"Closing Short Position ID: {position.id}")
                            # need to remove position from positions list to avoid multiple close attempts
                            self.finance_client.close_position(position=position)
                            positions.remove(position)

        # Implement the actual strategy logic here
        print(f"Result of strategy")
        result = None
        return result