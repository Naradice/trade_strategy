from typing import List, Union
import logging

import asyncio
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner


from .agents import trend_analyst_generator, signal_refiner_generator
from .agents.utils import parse_json_string, call_agent_async
from .strategies.strategy_base import StrategyClient
from .signal import Trend, TREND_TYPE
from . import signal, utils

logger = logging.getLogger(__name__)

class TradingPipeline:
    def __init__(self, ohlc_tool, market_trend_update=True, signal_handling=True, trading_style="daily trade"):
        self._ohlc_tool = ohlc_tool
        self.session_service = InMemorySessionService()
        self.market_trend_update = market_trend_update
        self.signal_handling = signal_handling
        self.trading_style = trading_style

        if market_trend_update:
            trend_analyst = trend_analyst_generator(client_tool=ohlc_tool)
            self.trend_runner = Runner(app_name="Trend", agent=trend_analyst, session_service=self.session_service)
        if signal_handling:
            self.signal_analyst = signal_refiner_generator(client_tool=ohlc_tool)
            self.signal_runner = Runner(app_name="Signal", agent=self.signal_analyst, session_service=self.session_service)

    def before_signal(self, strategy: StrategyClient, symbols: Union[str, List[str]]):
        if self.market_trend_update:
            if isinstance(symbols, str):
                symbols = [symbols]
            for symbol in symbols:
                session = asyncio.run(self.session_service.get_session(app_name="Trend", user_id="system", session_id=symbol))
                if session is None:
                    # to reduce number of call times to generate reports, we create a new signal analyst for each symbol
                    asyncio.run(self.session_service.create_session(app_name="Trend", user_id="system", session_id=symbol))
                responses = asyncio.run(call_agent_async(query=f"Analyze the trend of {symbol} for {self.trading_style} based on market analysis", runner=self.trend_runner, user_id="system", session_id=symbol))
                if responses and len(responses) > 0:
                    trend_analysis = responses[-1]["text"]
                    logger.debug(f"Trend analysis for {symbol}: {trend_analysis}")
                    market_trend_dict = parse_json_string(trend_analysis)
                    if len(market_trend_dict) > 0:
                        market_trend = utils.trend_to_trend_obj(market_trend_dict)
                        strategy.set_market_trend(symbol, market_trend)
                    else:
                        logger.debug(f"No valid market trend data found in analysis for {symbol}: {trend_analysis}")

    def after_signal(self, signals: List[signal.Signal]):
        if self.signal_handling:
            new_signals = []
            for signal_item in signals:
                symbol = signal_item.symbol
                if symbol:
                    session = asyncio.run(self.session_service.get_session(app_name="Signal", user_id="system", session_id=symbol))
                    if session is None:
                        # to reduce number of call times to generate reports, we create a new signal analyst for each symbol
                        asyncio.run(self.session_service.create_session(app_name="Signal", user_id="system", session_id=symbol))
                    signal_str = "Buy" if signal_item.is_buy else "Sell"
                    new_signal = None
                    responses = asyncio.run(call_agent_async(query=f"Analyze the signal for {symbol} for {self.trading_style}\nSignal: {signal_str}", runner=self.signal_runner, user_id="system", session_id=symbol))
                    if responses and len(responses) > 0:
                        signal_analysis = responses[-1]["text"]
                        logger.debug(f"Signal analysis for {symbol}: {signal_analysis}")
                        signal_dict = parse_json_string(signal_analysis)
                        if len(signal_dict) > 0:
                            new_signal = utils.refine_signal(signal_item, signal_dict)
                        else:
                            logger.debug(f"No valid signal data found in analysis for {symbol}: {signal_analysis}")
                            logger.info("return original signal as failed to parse json")
                            new_signal = signal_item
                        if new_signal != signal_item:
                            logger.debug(f"Signal updated for {symbol}: {new_signal}")
                        if new_signal is not None:
                            new_signals.append(new_signal)
                    else:
                        new_signals.append(signal_item)
                else:
                    new_signals.append(signal_item)
            return new_signals
        else:
            return signals
