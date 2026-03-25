from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor

@tool
def get_dex_ohlcv(
    pair_symbol: Annotated[str, "Trading pair name, such as 'WETH/USDC'"], 
    tradedate: Annotated[str, "the date and time before which the data is requested, format 'YYYY-MM-DD HH:MM:SS'"],
    timeframe: Annotated[str, "timeframe of the OHLCV chart, Available values : day, hour, minute"],
    limit: Annotated[int, "number of OHLCV results to return, maximum 1000, default is 100"] = 100
    ) -> str:
    """
    Retrieve historical OHLCV time series data for a specified liquidity pool.
    
    :param pair_symbol: name of trading pairs, such as 'WETH/USDC'
    :param timeframe: timeframe, options are 'minute', 'hour', 'day'
    :param tradedate: the date and time before which the data is requested
    :param limit: number of data points to retrieve, GeckoTerminal free tier usually allows up to 1000 per request
    :return: string representation of the pandas DataFrame containing the time series data
    """
    return route_to_vendor("get_dex_ohlcv", pair_symbol, tradedate, timeframe, limit)