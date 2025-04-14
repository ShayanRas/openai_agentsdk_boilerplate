from twelvedata import TDClient
import os
import dotenv
from typing import List, Dict, Any
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from typing_extensions import Annotated

dotenv.load_dotenv()

td = TDClient(apikey=os.getenv("TWELVEDATA_API_KEY"))

async def get_time_series(
    symbol: str,
    interval: str,
    output_size: int,
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> List[Dict[str, Any]]: 
    """Get historical time series data for a financial symbol.

    Use this tool to retrieve historical price data (like open, high, low, close, volume)
    for a specific stock symbol (e.g., 'AAPL', 'GOOG'), currency pair (e.g., 'EUR/USD'),
    or other financial instrument supported by TwelveData.

    Args:
        symbol: The symbol of the financial instrument (e.g., 'AAPL', 'MSFT', 'EUR/USD').
        interval: The time interval between data points (e.g., '1min', '5min', '1h', '1day').
        output_size: The number of data points to retrieve.
        config: Runtime configuration (automatically injected).

    Returns:
        A list of dictionaries, where each dictionary represents a data point
        with keys like 'datetime', 'open', 'high', 'low', 'close', 'volume'.
    """
    timeseries = td.time_series(symbol=symbol, interval=interval, outputsize=output_size)
    return timeseries.as_json()
