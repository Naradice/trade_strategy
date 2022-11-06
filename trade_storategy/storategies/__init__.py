from trade_storategy.storategies.strategy_base import StorategyClient
from trade_storategy.storategies.storategy_client import *

def load_storategy_client(key):
    availables = { MACDRenko.key: MACDRenko,
                  MACDCross.key: MACDCross,
                  MACDRenkoRangeSLByBB.key: MACDRenkoRangeSLByBB,
                  CCICross.key: CCICross,
                  CCIBoader.key: CCIBoader,
                  RangeTrade.key: RangeTrade,
                  MACDRenkoRange.key: MACDRenkoRange,
                  MACDRenkoRangeSLByBB.key: MACDRenkoRangeSLByBB
    }