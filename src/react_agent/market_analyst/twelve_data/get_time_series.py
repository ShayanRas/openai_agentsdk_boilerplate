from twelvedata import TDClient
import os
import dotenv
from typing import List, Dict, Any
import asyncio
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from typing_extensions import Annotated

dotenv.load_dotenv()

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
    # Define a synchronous helper function to run in the thread
    def _get_and_convert():
        # Instantiate client *inside* the thread function
        td = TDClient(apikey=os.getenv("TWELVE_DATA_API_KEY"))
        timeseries = td.time_series(
            symbol=symbol, interval=interval, outputsize=output_size
        )
        return timeseries.as_json()

    # Run the helper function in a separate thread
    json_result = await asyncio.to_thread(_get_and_convert)

    return json_result
