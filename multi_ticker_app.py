# multi_ticker_app.py

import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(
    page_title="Multi-Ticker Explorer",
    layout="wide"
)

st.title("📊 Multi-Ticker Performance & Fundamentals")

# Tickers come in as a comma-separated list in the sidebar.
tickers_input = st.sidebar.text_input(
    "Enter tickers (comma-separated)",
    "AAPL, MSFT, GOOG, NVDA"
)
symbols = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
if not symbols:
    st.error("Please enter at least one ticker.")
    st.stop()

# One yf.download call pulls all tickers at once. Using period= instead of
# start/end keeps the call simple and avoids the period/start conflict yfinance
# silently resolves in favour of one side.
prices = yf.download(
    symbols,
    period="1y",
    auto_adjust=True,
    progress=False
)["Close"]

if prices.empty:
    st.error("No price data returned. Check your tickers.")
    st.stop()

# Normalize each series so they share a base of 1 on the first day.
normed = prices.div(prices.iloc[0])
st.subheader("Normalized Price (Base = 1)")
st.line_chart(normed, use_container_width=True, height=400)

# Simple total return and annualized Sharpe (rf assumed = 0).
returns = prices.pct_change().dropna()
def sharpe(s): return (s.mean() / s.std()) * (252 ** 0.5)

perf = {
    sym: {
        "1Y Return (%)": (normed[sym].iloc[-1] - 1) * 100,
        "Sharpe Ratio": sharpe(returns[sym])
    }
    for sym in symbols
}
perf_df = pd.DataFrame(perf).T.round(2)
st.subheader("Performance Metrics")
st.dataframe(perf_df)

funds_data = []
for sym in symbols:
    info = yf.Ticker(sym).info
    funds_data.append({
        "Ticker": sym,
        "Trailing P/E":    info.get("trailingPE"),
        "Forward P/E":     info.get("forwardPE"),
        "Beta":            info.get("beta"),
        "Market Cap":      info.get("marketCap"),
        "Dividend Yield":  info.get("dividendYield")
    })

funds_df = pd.DataFrame(funds_data).set_index("Ticker")
st.subheader("Fundamentals")
st.dataframe(funds_df)

csv = funds_df.to_csv()
st.download_button(
    label="📥 Download Fundamentals as CSV",
    data=csv,
    file_name="fundamentals.csv",
    mime="text/csv"
)
