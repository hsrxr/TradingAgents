from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor

@tool
def get_dex_indicators(
    pair: Annotated[str, "The trading pair for which to fetch indicators"],
    indicators: Annotated[list, "The list of indicators to calculate"]
):
    """
    Fetch technical indicators for a given trading pair from the configured DEX indicators vendor.
        
    Args:
            pair (str): The trading pair, e.g. 'WETH/USDC'
            indicators (list): A list of technical indicators to calculate, e.g. ['rsi', 'macd']
    Returns:
            str: A formatted string containing the requested technical indicators for the specified trading pair.
    """
    return route_to_vendor("get_dex_indicators", pair=pair, indicators=indicators)