import logging
from finance_client.position import Position
from finance_client.fprocess.fprocess.indicaters import technical

logger = logging.getLogger("trade_strategy.trailingstop")

class TrailingStopBase:

    def __init__(self, ohlc_columns: list):
        self.ohlc_columns = ohlc_columns

    def __call__(self, ohlc_df, positions: list[Position], *args, **kwds):
        close_column = self.ohlc_columns[-1]
        current_price = ohlc_df.iloc[-1]
        target_positions = []
        for position in positions:
            if position.position_type.value == 1 and current_price[close_column] > position.price:
                target_positions.append(position)
            elif position.position_type.value == -1 and current_price[close_column] < position.price:
                target_positions.append(position)
        if len(target_positions) == 0:
            return {}
        logger.debug(f"Updating trailing stops for positions: {len(target_positions)}")
        return self.update_stops(ohlc_df, target_positions, *args, **kwds)
    
    def update_stops(self, df, positions: list[Position], *args, **kwds):
        raise NotImplementedError("Please implement this method in subclass.")

class TrailingStopByATR(TrailingStopBase):
    def __init__(self, ohlc_columns: list, atr_window: int =14, atr_multiplier: float =3.0, clip_with_price: bool =False):
        """Apply trailing stop based on ATR for given positions.

        Args:
            atr_window (int, optional): Window size for ATR calculation. Defaults to 14.
            atr_multiplier (float, optional): Multiplier for ATR to set stop distance. Defaults to 3.0.
            ohlc_columns (list): List of OHLC column names.
            clip_with_price (bool, optional): If True, ensures stop does not exceed order price. Defaults to False.
        """
        self.atr_window = atr_window
        self.atr_multiplier = atr_multiplier
        self.ohlc_columns = ohlc_columns
        self.clip_with_price = clip_with_price
    
    def update_stops(self, df, positions: list[Position], *args, **kwds) -> dict:
        try:
            atr_series = technical.ATRFromOHLC(
                data=df,
                ohlc_columns=self.ohlc_columns,
                window=self.atr_window
            )['ATR']
        except Exception as e:
            logger.exception(f"Error calculating ATR")
            return {}

        new_stops = {}
        close_column = self.ohlc_columns[-1]
        last_price = df.iloc[-1][close_column]
        latest_atr = atr_series.iloc[-1]

        for position in positions:
            if position.position_type.value == 1:  # Long position
                new_stop = last_price - (self.atr_multiplier * latest_atr)
                if self.clip_with_price and new_stop < position.price:
                    new_stop = position.price
                if position.sl is None or new_stop > position.sl:
                    new_stops[position.id] = new_stop
            else:
                new_stop = last_price + (self.atr_multiplier * latest_atr)
                if self.clip_with_price and new_stop > position.price:
                    new_stop = position.price
                if position.sl is None or new_stop < position.sl:
                    new_stops[position.id] = new_stop

        return new_stops