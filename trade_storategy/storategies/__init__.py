from trade_storategy.storategies.strategy_base import StorategyClient
from trade_storategy.storategies.storategy_client import *

def load_storategy_client(key:str, finance_client, idc_processes:list, options={}):
    availables = { MACDRenko.key: MACDRenko,
                  MACDCross.key: MACDCross,
                  MACDRenkoRangeSLByBB.key: MACDRenkoRangeSLByBB,
                  CCICross.key: CCICross,
                  CCIBoader.key: CCIBoader,
                  RangeTrade.key: RangeTrade,
                  MACDRenkoRange.key: MACDRenkoRange,
                  MACDRenkoRangeSLByBB.key: MACDRenkoRangeSLByBB
    }
    
    if key in availables:
        return availables[key].load(finance_client, idc_processes, options)
    else:
        raise Exception(f"{key} is not in availabe storategies {availables.keys()}")