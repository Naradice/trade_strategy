import logging

from . import signal

logger = logging.getLogger(__name__)

def trend_to_trend_obj(trend_dict: dict) -> signal.Trend:
    """Convert a trend dictionary to a Trend object.

    Args:
        trend_dict (dict): Dictionary containing trend information.

    Returns:
        signal.Trend: Trend object.
    """
    trend_str = trend_dict.get("trend", "unknown")
    if "up" in trend_str.lower():
        market_trend = signal.Trend(
            direction=signal.TREND_TYPE.up,
            reason=trend_dict.get("reason", ""),
            strength=trend_dict.get("strength", ""),
        )
    elif "down" in trend_str.lower():
        market_trend = signal.Trend(
            direction=signal.TREND_TYPE.down,
            reason=trend_dict.get("reason", ""),
            strength=trend_dict.get("strength", ""),
        )
    elif "rang" in trend_str.lower():
        market_trend = signal.Trend(
            direction=signal.TREND_TYPE.range,
            reason=trend_dict.get("reason", ""),
            strength=trend_dict.get("strength", ""),
        )
    elif "side" in trend_str.lower():
        market_trend = signal.Trend(
            direction=signal.TREND_TYPE.sideways,
            reason=trend_dict.get("reason", ""),
            strength=trend_dict.get("strength", ""),
        )
    else:
        logger.debug(f"Unknown trend type: {trend_str}")
        market_trend = signal.Trend(
            direction=signal.TREND_TYPE.unknown,
            reason=trend_dict.get("reason", ""),
            strength=trend_dict.get("strength", ""),
        )
    return market_trend

def refine_signal(org_signal: signal.Signal, signal_dict: dict) -> signal.Signal:
    """refine signal based on the provided signal_dict. Typically the dict is created with an agent.

    Args:
        org_signal (signal.Signal): original signal raised by indicators
        signal_dict (dict): dictionary containing refined signal information

    Returns:
        signal.Signal: refined signal
    """
    org_is_close = org_signal.is_close
    org_std_name = org_signal.std_name
    org_amount = org_signal.amount
    symbol = org_signal.symbol
    
    is_buy = "buy" in signal_dict.get("signal", "None").lower()
    is_sell = "sell" in signal_dict.get("signal", "None").lower()
    order_type = signal_dict.get("order_type", "market")
    confidence = signal_dict.get("confidence", 1.0)
    price = signal_dict.get("price", 0.0)
    stop_loss = signal_dict.get("stop_loss", 0.0)
    take_profit = signal_dict.get("take_profit", 0.0)

    if is_buy:
        if org_is_close:
            new_signal = signal.CloseSignal(std_name=org_std_name, price=price, symbol=symbol, confidence=confidence)
        elif "limit" in order_type.lower() or "stop" in order_type.lower():
            new_signal = signal.BuyPendingOrderSignal(std_name=org_std_name, price=price, amount=org_amount, sl=stop_loss, tp=take_profit, symbol=symbol, confidence=confidence)
        else:
            new_signal = signal.BuySignal(std_name=org_std_name, price=price, amount=org_amount, symbol=symbol, sl=stop_loss, tp=take_profit, confidence=confidence)
    elif is_sell:
        if org_is_close:
            new_signal = signal.CloseSignal(std_name=org_std_name, price=price, symbol=symbol, confidence=confidence)
        elif "limit" in order_type.lower() or "stop" in order_type.lower():
            new_signal = signal.SellPendingOrderSignal(std_name=org_std_name, price=price, amount=org_amount, sl=stop_loss, tp=take_profit, symbol=symbol, confidence=confidence)
        else:
            new_signal = signal.SellSignal(std_name=org_std_name, price=price, amount=org_amount, symbol=symbol, sl=stop_loss, tp=take_profit, confidence=confidence)
    else:
        logger.debug(f"Unknown signal type: {signal_dict}")
        new_signal = None
    return new_signal