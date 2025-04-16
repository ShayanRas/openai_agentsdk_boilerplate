from alpha_vantage.econindicators import EconIndicators
import os
import dotenv
from typing import Dict, Any, Optional, List, Union
import asyncio
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from typing_extensions import Annotated

dotenv.load_dotenv()

async def av_get_econ_data(
    indicator: str,
    interval: Optional[str] = None,
    maturity: Optional[str] = None,
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> Dict[str, Any]:
    """Get economic indicator data from Alpha Vantage.

    Use this tool to retrieve various US economic indicators such as GDP, inflation,
    treasury yields, unemployment, and more. The data is sourced from Alpha Vantage's
    Economic Indicators API.

    Args:
        indicator: The economic indicator to retrieve. Options include 'real_gdp', 'real_gdp_per_capita', 'treasury_yield', 'federal_funds_rate', 'cpi', 'inflation', 'retail_sales', 'durables', 'unemployment', 'nonfarm_payroll'.
        interval: The time interval for data points. Options: 'real_gdp': 'annual'/'quarterly'; 'treasury_yield': 'daily'/'weekly'/'monthly'; 'federal_funds_rate': 'daily'/'weekly'/'monthly'; 'cpi': 'semiannual'/'monthly'.
        maturity: For treasury_yield only - the maturity period of the treasury bond.
        config: Runtime configuration (automatically injected).

    Returns:
        A dictionary containing the economic indicator data and metadata.
    """
    # Define a synchronous helper function to run in the thread
    def _get_and_convert():
        # Instantiate client *inside* the thread function
        ei = EconIndicators(key=os.getenv("ALPHA_VANTAGE_API_KEY"), output_format='json')
        
        # Map indicator to appropriate method
        if indicator == 'real_gdp':
            if interval and interval in ['annual', 'quarterly']:
                data, meta_data = ei.get_real_gdp(interval=interval)
            else:
                data, meta_data = ei.get_real_gdp()  # Default is annual
        
        elif indicator == 'real_gdp_per_capita':
            data, meta_data = ei.get_real_gdp_per_capita()
        
        elif indicator == 'treasury_yield':
            if interval and maturity:
                data, meta_data = ei.get_treasury_yield(interval=interval, maturity=maturity)
            elif interval:
                data, meta_data = ei.get_treasury_yield(interval=interval)  # Default maturity is 10year
            elif maturity:
                data, meta_data = ei.get_treasury_yield(maturity=maturity)  # Default interval is monthly
            else:
                data, meta_data = ei.get_treasury_yield()  # Default is monthly, 10year
        
        elif indicator == 'federal_funds_rate':
            if interval and interval in ['daily', 'weekly', 'monthly']:
                data, meta_data = ei.get_ffr(interval=interval)
            else:
                data, meta_data = ei.get_ffr()  # Default is monthly
        
        elif indicator == 'cpi':
            if interval and interval in ['semiannual', 'monthly']:
                data, meta_data = ei.get_cpi(interval=interval)
            else:
                data, meta_data = ei.get_cpi()  # Default is monthly
        
        elif indicator == 'inflation':
            data, meta_data = ei.get_inflation()
        
        elif indicator == 'retail_sales':
            data, meta_data = ei.get_retail_sales()
        
        elif indicator == 'durables':
            data, meta_data = ei.get_durables()
        
        elif indicator == 'unemployment':
            data, meta_data = ei.get_unemployment()
        
        elif indicator == 'nonfarm_payroll':
            data, meta_data = ei.get_nonfarm()
        
        else:
            raise ValueError(f"Unknown indicator: {indicator}")
        
        # Combine data and metadata into a single dictionary
        result = {
            "data": data,
            "metadata": meta_data
        }
        
        return result

    # Run the helper function in a separate thread
    result = await asyncio.to_thread(_get_and_convert)

    return result