# Stock Performance Explorer

A Streamlit dashboard for exploring stock performance, fundamentals, macro indicators, and rolling risk analytics. Enter any set of tickers and get normalized price charts, Sharpe ratios, quarterly financial ratios, sector comparisons, and rolling volatility/beta vs. SPY.

## Features

- **Normalized price chart** across any number of tickers, with selectable timeframe (1Y / 2Y / 5Y / max).
- **Performance metrics**: period return and annualized Sharpe ratio.
- **Fundamentals snapshot** pulled from Yahoo Finance (P/E, forward P/E, beta, market cap), with CSV export.
- **Quarterly financial ratio analysis**: Debt/Equity, Current Ratio, point-in-time and TTM ROA/ROE, Interest Coverage.
- **Macro & sector dashboard**: 10-Year Treasury yield time series, plus a ranked comparison of the 11 SPDR sector ETFs over the chosen window.
- **Rolling risk analytics**: annualized volatility, beta vs. SPY, and max drawdown — presented as a snapshot table plus interactive tabs.

## Tech stack

Python, Streamlit, pandas, NumPy, yfinance, Altair. Optional SQLite layer (`db.py`) for caching historical prices locally.

## Running it

### Windows (one click)

Double-click `launch.bat`. It will create a virtual environment, install dependencies, and start the app. Your browser should open automatically at `http://localhost:8501`.

### Manual setup (any OS)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Project layout

```
app.py                 # Main Streamlit dashboard
multi_ticker_app.py    # Slimmer variant: performance + fundamentals only
db.py                  # SQLite helpers for caching prices and metadata
metadata.csv           # Seed sector/industry data for symbol_meta table
requirements.txt       # Python dependencies
launch.bat             # Windows one-click launcher
```

## Notes on methodology

- Sharpe ratio is annualized with a risk-free rate of 0 (a common simplification for cross-ticker comparison).
- ROA/ROE use point-in-time balance-sheet denominators rather than period averages.
- Rolling beta is computed as `cov(stock, SPY) / var(SPY)` over the selected window.
- Rolling volatility is the annualized standard deviation of daily returns, scaled by `sqrt(252)`.
- Drawdown is measured from the running peak of the selected window.

## Data source

All market and fundamentals data comes from Yahoo Finance via the `yfinance` library. No API key required. The app is subject to Yahoo's rate limits.

## License

MIT
