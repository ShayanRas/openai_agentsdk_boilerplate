# Alpha Vantage Python Library Capabilities (`alpha-vantage`)

This document provides a summary of the capabilities of the `alpha-vantage` Python library, based on an analysis of its source code. It focuses particularly on the **Economic Indicators** module but also covers other data types.

**Note:** This analysis is based on the source code provided. The version installed via `pip` might have variations or updates.

## Installation

This library is typically installed via pip:

```bash
pip install alpha-vantage
```

## Core Usage (`AlphaVantage` Base Class)

The library is structured around a base class, `AlphaVantage`, and several specialized classes inheriting from it (e.g., `TimeSeries`, `EconIndicators`).

**Initialization:**

When using any specialized class, you first need to instantiate it. The base class constructor (which the specialized classes use) requires an Alpha Vantage API key and allows setting the output format:

```python
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.econindicators import EconIndicators
import os

# Key can be passed directly or read from environment variable ALPHAVANTAGE_API_KEY
api_key = os.getenv('ALPHAVANTAGE_API_KEY') 
# Or api_key = 'YOUR_API_KEY'

# Example instantiation (using TimeSeries)
ts = TimeSeries(key=api_key, output_format='pandas') # Or 'json', 'csv'
ei = EconIndicators(key=api_key, output_format='json') 

# Optional: Use RapidAPI key
# ts_rapid = TimeSeries(key='YOUR_RAPIDAPI_KEY', rapidapi=True)
```

*   **`key`**: Your Alpha Vantage API key (required).
*   **`output_format`**: `'json'` (default, returns dicts/lists), `'pandas'` (returns pandas DataFrames, requires `pandas` installed), `'csv'` (returns list of lists, *not supported by all modules*).
*   **`rapidapi`**: Set to `True` if using a key from the RapidAPI platform.
*   **`proxy`**: Optional dictionary for proxy configuration.

**Return Format:**

Most data-fetching methods return a tuple: `(data, meta_data)`.

*   `data`: The requested data in the specified `output_format`.
*   `meta_data`: Metadata provided by the API (can be `None` for some calls).

## Economic Indicators (`EconIndicators`)

This module provides access to various US economic indicators. Instantiate the `EconIndicators` class first.

```python
from alpha_vantage.econindicators import EconIndicators
import os

ei = EconIndicators(key=os.getenv('ALPHAVANTAGE_API_KEY'), output_format='json')
```

**Available Methods:**

*   `get_real_gdp(interval='annual')`: US Real GDP.
    *   `interval`: `'annual'` (default), `'quarterly'`.
*   `get_real_gdp_per_capita()`: US Quarterly Real GDP per Capita.
*   `get_treasury_yield(interval='monthly', maturity='10year')`: US Treasury Yield.
    *   `interval`: `'daily'`, `'weekly'`, `'monthly'` (default).
    *   `maturity`: `'3month'`, `'2year'`, `'5year'`, `'7year'`, `'10year'` (default), `'30year'`.
*   `get_ffr(interval='monthly')`: US Federal Funds Rate.
    *   `interval`: `'daily'`, `'weekly'`, `'monthly'` (default).
*   `get_cpi(interval='monthly')`: US Consumer Price Index.
    *   `interval`: `'semiannual'`, `'monthly'` (default).
*   `get_inflation()`: US Annual Inflation Rate.
*   `get_retail_sales()`: US Monthly Advance Retail Sales.
*   `get_durables()`: US Monthly Durable Goods Orders.
*   `get_unemployment()`: US Monthly Unemployment Rate.
*   `get_nonfarm()`: US Monthly Total Nonfarm Payroll.

**Example:**

```python
try:
    cpi_data, meta_data = ei.get_cpi(interval='monthly')
    print(cpi_data)
except Exception as e:
    print(f"Error fetching CPI data: {e}")
```

## Other Data Modules (Overview)

Instantiate the respective class (e.g., `TimeSeries`, `ForeignExchange`) similar to `EconIndicators`.

### Time Series (`TimeSeries`)

Provides stock time series data.

*   `get_intraday(symbol, interval='15min', ...)`: Intraday stock data.
*   `get_daily(symbol, outputsize='compact')`: Daily stock data.
*   `get_daily_adjusted(symbol, outputsize='compact')`: Adjusted daily stock data.
*   `get_weekly(symbol)`: Weekly stock data.
*   `get_weekly_adjusted(symbol)`: Adjusted weekly stock data.
*   `get_monthly(symbol)`: Monthly stock data.
*   `get_monthly_adjusted(symbol)`: Adjusted monthly stock data.
*   `get_quote_endpoint(symbol)`: Latest price/volume quote.
*   `get_symbol_search(keywords)`: Search for stock symbols.
*   `get_market_status()`: Status of major trading venues.

### Foreign Exchange (`ForeignExchange`)

Provides FX rates. ***Note: CSV output is not supported.***

*   `get_currency_exchange_rate(from_currency, to_currency)`: Real-time exchange rate (physical or crypto).
*   `get_currency_exchange_intraday(from_symbol, to_symbol, interval='15min', ...)`: Intraday FX rates.
*   `get_currency_exchange_daily(from_symbol, to_symbol, ...)`: Daily FX rates.
*   `get_currency_exchange_weekly(from_symbol, to_symbol, ...)`: Weekly FX rates.
*   `get_currency_exchange_monthly(from_symbol, to_symbol, ...)`: Monthly FX rates.

### Cryptocurrencies (`CryptoCurrencies`)

Provides cryptocurrency data.

*   `get_digital_currency_daily(symbol, market)`: Daily crypto data for a specific market.
*   `get_digital_currency_weekly(symbol, market)`: Weekly crypto data.
*   `get_digital_currency_monthly(symbol, market)`: Monthly crypto data.
*   `get_digital_currency_exchange_rate(from_currency, to_currency)`: Real-time exchange rate (crypto or physical).
*   `get_crypto_intraday(symbol, market, interval, ...)`: Intraday crypto data.

### Fundamental Data (`FundamentalData`)

Provides company fundamental data. ***Note: CSV output is not supported.***

*   `get_company_overview(symbol)`: Company info, ratios, metrics.
*   `get_dividends(symbol)`: Historical and declared dividends.
*   `get_splits(symbol)`: Historical stock splits.
*   `get_income_statement_annual(symbol)` / `_quarterly(symbol)`: Income statements.
*   `get_balance_sheet_annual(symbol)` / `_quarterly(symbol)`: Balance sheets.
*   `get_cash_flow_annual(symbol)` / `_quarterly(symbol)`: Cash flow statements.
*   `get_earnings_annual(symbol)` / `_quarterly(symbol)`: Company earnings (EPS).

### Commodities (`Commodities`)

Provides commodity price data.

*   `get_wti(interval='monthly')`: West Texas Intermediate Crude Oil prices.
*   `get_brent(interval='monthly')`: Brent Crude Oil prices.
*   `get_natural_gas(interval='monthly')`: Natural Gas prices.
*   `get_copper(interval='monthly')`: Copper prices.
*   `get_aluminum(interval='monthly')`: Aluminum prices.
*   `get_wheat(interval='monthly')`: Wheat prices.
*   `get_corn(interval='monthly')`: Corn prices.
*   `get_cotton(interval='monthly')`: Cotton prices.
*   `get_sugar(interval='monthly')`: Sugar prices.
*   `get_coffee(interval='monthly')`: Coffee prices.
*   `get_price_index(interval='monthly')`: Global All Commodities Price Index.

### Technical Indicators (`TechIndicators`)

Provides a wide range of technical indicators. ***Note: CSV output is not supported.***

This module contains numerous functions (SMA, EMA, MACD, RSI, Bollinger Bands, etc.).

*   **Common Parameters:** `symbol`, `interval`, `time_period`, `series_type`.
*   **Example:** `get_sma(symbol, interval='daily', time_period=20, series_type='close')`

Refer to the source code or official Alpha Vantage documentation for the full list and specific parameters of each indicator.

## Asynchronous Support

The presence of an `async_support` directory in the source code suggests that asynchronous versions of these API calls might be available in the pip-installed package, likely used via `async/await` syntax. This analysis did not delve into the specifics of the async implementation.

## Summary

The `alpha-vantage` library offers a structured way to access a wide variety of financial data through Python, including economic indicators, stock time series, FX, crypto, commodities, fundamental data, and technical indicators. Remember to handle potential errors (e.g., invalid API key, network issues, API limits) using try-except blocks.
