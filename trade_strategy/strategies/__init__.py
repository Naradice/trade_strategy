from .strategy_base import StrategyClient
from .strategy_client import *

def load_strategy_client(key:str, finance_client, idc_processes:list, options:dict=None):
    availables = { MACDRenko.key: MACDRenko,
                  MACDCross.key: MACDCross,
                  MACDRenkoRangeSLByBB.key: MACDRenkoRangeSLByBB,
                  CCICross.key: CCICross,
                  CCIBoader.key: CCIBoader,
                  RangeTrade.key: RangeTrade,
                  MACDRenkoRange.key: MACDRenkoRange,
                  MACDRenkoRangeSLByBB.key: MACDRenkoRangeSLByBB
    }
    
    if idc_processes is None:
        idc_processes = []
    if options is None:
        options = {}
    
    if key in availables:
        return availables[key].load(finance_client, idc_processes, options)
    else:
        raise Exception(f"{key} is not in availabe strategies {availables.keys()}")