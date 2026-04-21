import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import altair as alt


st.set_page_config(
    page_title="Stock Performance Explorer",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Helpers

def human_format(num):
    """Convert large number to human-readable string."""
    if num is None or pd.isna(num):
        return "N/A"
    num = float(num)
    for unit, scale in [("T",1e12),("B",1e9),("M",1e6),("K",1e3)]:
        if abs(num) >= scale:
            return f"{num/scale:.2f} {unit}"
    return f"{num:.0f}"

SECTOR_ETFS = {
    "Technology":              "XLK",
    "Communication Services":  "XLC",
    "Consumer Discretionary":  "XLY",
    "Consumer Staples":        "XLP",
    "Energy":                  "XLE",
    "Financials":              "XLF",
    "Healthcare":              "XLV",
    "Industrials":             "XLI",
    "Materials":               "XLB",
    "Real Estate":             "XLRE",
    "Utilities":               "XLU",
}

# Shorter axis labels for sector bar chart
SECTOR_SHORT = {
    "Technology": "Tech",
    "Communication Services": "Comm Svcs",
    "Consumer Discretionary": "Cons Disc",
    "Consumer Staples": "Cons Stap",
    "Energy": "Energy",
    "Financials": "Financials",
    "Healthcare": "Healthcare",
    "Industrials": "Industrials",
    "Materials": "Materials",
    "Real Estate": "Real Est",
    "Utilities": "Utilities",
}

# Title and sidebar
st.title("📊 Stock Performance Explorer")

st.sidebar.header("Search & Settings")
tickers_input = st.sidebar.text_input(
    "Ticker symbols (comma-separated)",
    "AAPL, MSFT, GOOG, NVDA"
).upper().strip()

period_option = st.sidebar.selectbox(
    "Timeframe",
    ["1y", "2y", "5y", "max"],
    index=0,
    help="How far back to pull price, macro & sector data."
)

roll_window = st.sidebar.slider(
    "Rolling window (trading days)",
    min_value=20,
    max_value=252,
    value=60,
    step=5,
    help="Used for rolling volatility & beta."
)

symbols = [s for s in (t.strip() for t in tickers_input.split(",")) if s]
if not symbols:
    st.sidebar.warning("Enter at least one ticker.")
    st.stop()

# Price series
with st.spinner(f"Fetching {period_option.upper()} price data..."):
    prices = yf.download(
        symbols,
        period=period_option,
        auto_adjust=True,
        progress=False
    )["Close"]

if isinstance(prices, pd.Series):
    prices = prices.to_frame(name=symbols[0])

if prices.empty:
    st.error("No price data returned—check ticker symbols.")
    st.stop()

normed  = prices / prices.iloc[0]
returns = prices.pct_change().dropna()


# Performance metrics
# Sharpe here assumes a 0% risk-free rate (a common simplification for
# cross-ticker comparison). Replace r.mean() with (r.mean() - rf_daily) if
# you want to incorporate a non-zero risk-free rate.
def sharpe(r):
    return (r.mean() / r.std()) * (252 ** 0.5)

period_label = period_option.upper()
perf_df = pd.DataFrame({
    f"{period_label} Return (%)": (normed.iloc[-1] - 1).mul(100).round(2),
    "Sharpe":                      returns.apply(sharpe).round(2)
})

col_price, col_perf = st.columns([3,1])
with col_price:
    st.subheader(f"Normalized Price (Base = 1) — Last {period_option.upper()}")
    st.line_chart(normed, use_container_width=True, height=380)
with col_perf:
    st.subheader("Performance Metrics")
    st.dataframe(perf_df)

# Fundamentals (Yahoo info) + CSV download
with st.spinner("Fetching fundamentals..."):
    fundamentals = []
    for s in symbols:
        info = yf.Ticker(s).info
        fundamentals.append({
            "Ticker":       s,
            "Trailing P/E": info.get("trailingPE"),
            "Forward P/E":  info.get("forwardPE"),
            "Beta":         info.get("beta"),
            "Market Cap":   human_format(info.get("marketCap")),
        })
funds_df = pd.DataFrame(fundamentals).set_index("Ticker")

st.subheader("Fundamentals")
st.dataframe(funds_df)
st.download_button(
    "📥 Download Fundamentals CSV",
    funds_df.to_csv(),
    "fundamentals.csv",
    mime="text/csv"
)

# Financial statement & ratio analysis
st.header("🏦 Financial Statement & Ratio Analysis")


def pick_col(df, names):
    """Return the first column name from `names` that exists in `df`, else None.

    yfinance has changed its field names over time (e.g. "Total Liab" became
    "Total Liabilities Net Minority Interest"), so we try modern names first
    and fall back to the older ones.
    """
    for n in names:
        if n in df.columns:
            return n
    return None


LIAB_NAMES      = ["Total Liabilities Net Minority Interest", "Total Liab"]
EQUITY_NAMES    = ["Stockholders Equity", "Common Stock Equity",
                   "Total Stockholder Equity"]
CUR_ASSET_NAMES = ["Current Assets", "Total Current Assets"]
CUR_LIAB_NAMES  = ["Current Liabilities", "Total Current Liabilities"]
ASSETS_NAMES    = ["Total Assets"]
NI_NAMES        = ["Net Income", "Net Income Common Stockholders"]
EBIT_NAMES      = ["EBIT", "Ebit", "Operating Income"]
INT_EXP_NAMES   = ["Interest Expense"]


for sym in symbols:
    st.subheader(f"{sym} — Last 4 Quarters")
    tkr  = yf.Ticker(sym)
    # Sort ascending so rolling-window sums (TTM) align with the correct quarter.
    q_fin = tkr.quarterly_financials.T.sort_index()
    q_bs  = tkr.quarterly_balance_sheet.T.sort_index()

    ratios = pd.DataFrame(index=q_fin.index)

    liab_c      = pick_col(q_bs,  LIAB_NAMES)
    eq_c        = pick_col(q_bs,  EQUITY_NAMES)
    ca_c        = pick_col(q_bs,  CUR_ASSET_NAMES)
    cl_c        = pick_col(q_bs,  CUR_LIAB_NAMES)
    ta_c        = pick_col(q_bs,  ASSETS_NAMES)
    ni_c        = pick_col(q_fin, NI_NAMES)
    ebit_c      = pick_col(q_fin, EBIT_NAMES)
    int_c       = pick_col(q_fin, INT_EXP_NAMES)

    # Point-in-time (single-quarter) metrics.
    if liab_c and eq_c:
        ratios["Debt/Equity"] = (q_bs[liab_c] / q_bs[eq_c]).round(2)

    if ca_c and cl_c:
        ratios["Current Ratio"] = (q_bs[ca_c] / q_bs[cl_c]).round(2)

    if ni_c:
        if ta_c:
            ratios["ROA (Q %)"] = (q_fin[ni_c] / q_bs[ta_c] * 100).round(2)
        if eq_c:
            ratios["ROE (Q %)"] = (q_fin[ni_c] / q_bs[eq_c] * 100).round(2)

    # Interest coverage. yfinance sometimes reports interest expense as a
    # positive number and sometimes as a negative one; abs() makes the ratio
    # sign-stable either way.
    if ebit_c and int_c:
        ratios["Interest Cov (Q)"] = (
            q_fin[ebit_c] / q_fin[int_c].abs()
        ).replace([np.inf, -np.inf], np.nan).round(2)

    # Trailing-twelve-month approximations. NI is summed over 4 quarters;
    # balance-sheet denominators are point-in-time (standard simplification
    # in place of an average-assets/average-equity calculation).
    if ni_c:
        ni_ttm = q_fin[ni_c].rolling(4).sum()
        if ta_c:
            ratios["ROA (TTM %)"] = (ni_ttm / q_bs[ta_c] * 100).round(2)
        if eq_c:
            ratios["ROE (TTM %)"] = (ni_ttm / q_bs[eq_c] * 100).round(2)

    st.dataframe(ratios.tail(4))
    st.divider()

# Macro & sector dashboard
st.header("🌐 Macro & Sector Dashboard")
with st.spinner("Loading macro & sector data..."):

    # 10-Year Treasury Yield (^TNX)
    tnx_df = yf.download(
        "^TNX",
        period=period_option,
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    if "Close" in tnx_df and not tnx_df["Close"].dropna().empty:
        tnx_clean = (
            tnx_df[["Close"]]
            .dropna()
            .rename(columns={"Close": "Yield"})
            .reset_index()         # index -> Date column
        )
        y_min = float(tnx_clean["Yield"].min())
        y_max = float(tnx_clean["Yield"].max())
        # Pad the y-axis by at least 10 bps so a flat period still renders nicely.
        pad = float(y_max - y_min) * 0.10
        if pad < 0.10:
            pad = 0.10

        tnx_chart = (
            alt.Chart(tnx_clean)
            .mark_line()
            .encode(
                x=alt.X("Date:T", title=None),
                y=alt.Y(
                    "Yield:Q",
                    title="10-Year Treasury Yield (%)",
                    scale=alt.Scale(domain=[y_min - pad, y_max + pad])
                ),
                tooltip=[
                    alt.Tooltip("Date:T", title="Date"),
                    alt.Tooltip("Yield:Q", format=".2f", title="Yield (%)")
                ]
            )
            .properties(height=250)
            .interactive()
        )
        st.subheader("10-Year Treasury Yield (%)")
        st.altair_chart(tnx_chart, use_container_width=True)

    else:
        st.warning("No 10-year yield data returned from Yahoo (^TNX). Chart omitted.")

    # Sector ETF returns, ranked
    etf_syms = list(SECTOR_ETFS.values())
    etf_px = yf.download(etf_syms, period=period_option,
                         auto_adjust=True, progress=False)["Close"]

    etf_ret = ((etf_px.iloc[-1] / etf_px.iloc[0]) - 1).mul(100).round(2)

    rev_map = {v:k for k,v in SECTOR_ETFS.items()}
    etf_df = (
        etf_ret.rename_axis("ETF").reset_index(name="Return")
               .assign(Sector=lambda d: d["ETF"].map(rev_map))
               .assign(Label=lambda d: d["Sector"].map(SECTOR_SHORT))
               .sort_values("Return", ascending=False)
    )

    ymin2, ymax2 = float(etf_df["Return"].min()), float(etf_df["Return"].max())
    if ymin2 >= 0:
        domain2 = [0, ymax2 * 1.1]
    else:
        pad2 = (ymax2 - ymin2) * 0.1
        domain2 = [ymin2 - pad2, ymax2 + pad2]

    bar = (
        alt.Chart(etf_df)
        .mark_bar()
        .encode(
            x=alt.X("Label:N", sort=etf_df["Label"].tolist(),
                    axis=alt.Axis(labelAngle=-25), title="Sector"),
            y=alt.Y("Return:Q",
                    title=f"ETF Return (%) — Last {period_option.upper()}",
                    scale=alt.Scale(domain=domain2)),
            color=alt.Color("Sector:N", legend=None, scale=alt.Scale(scheme="tableau20")),
            tooltip=["Sector:N","ETF:N",alt.Tooltip("Return:Q", format=".2f")]
        )
    )
    txt = bar.mark_text(dy=-5, color="white").encode(text=alt.Text("Return:Q", format=".1f"))
    st.altair_chart((bar + txt).properties(height=360), use_container_width=True)

# Rolling risk analytics
st.header("📉 Rolling Risk Analytics")

max_len = len(returns)
if roll_window > max_len:
    st.sidebar.warning(f"Window {roll_window} > data length ({max_len}); capping.")
    roll_window = max_len

# SPY as the beta benchmark
spy_df = yf.download("SPY", period=period_option, auto_adjust=True, progress=False)

if "Close" not in spy_df or spy_df["Close"].dropna().empty:
    st.warning("No SPY price data returned; rolling beta metrics disabled.")
    # Empty series keeps the rest of the pipeline alive; beta will be NaN.
    bench_ret = pd.Series(dtype=float, name="SPY")
    aligned = returns.copy()
else:
    spy_series = spy_df["Close"].dropna().squeeze()
    spy_series.name = "SPY"

    bench_ret = spy_series.pct_change().dropna()
    bench_ret.name = "SPY"

    # Inner-join so we only compare on dates where all series have returns.
    aligned = returns.join(bench_ret, how="inner")

# Rolling annualized volatility, expressed as a percentage.
roll_vol_pct = aligned[symbols].rolling(roll_window, min_periods=2).std() * np.sqrt(252) * 100

# Rolling beta vs SPY: cov(stock, spy) / var(spy) over the window.
def rolling_beta(col):
    cov = aligned[col].rolling(roll_window, min_periods=2).cov(aligned["SPY"])
    var = aligned["SPY"].rolling(roll_window, min_periods=2).var()
    return cov / var

roll_beta_df = pd.DataFrame({s: rolling_beta(s) for s in symbols})

# Drawdown from running peak, in percent.
drawdown = (prices[symbols].div(prices[symbols].cummax()) - 1) * 100

snapshot = pd.DataFrame({
    "Rolling Vol (%)":   roll_vol_pct.iloc[-1].round(2),
    "Rolling Beta":      roll_beta_df.iloc[-1].round(2),
    "Max Drawdown (%)":  drawdown.min().round(2)
})
st.subheader(f"Current Risk Snapshot (window = {roll_window} trading days)")
st.dataframe(snapshot)

vol_tab, beta_tab, dd_tab = st.tabs(["Rolling Volatility", "Rolling Beta", "Drawdowns"])

with vol_tab:
    st.write("Annualized rolling volatility (%).")
    vol_chart = (
        alt.Chart(
            roll_vol_pct.reset_index().melt("Date", var_name="Ticker", value_name="Vol")
        )
        .mark_line()
        .encode(
            x="Date:T",
            y=alt.Y("Vol:Q", title="Vol (%)", scale=alt.Scale(zero=False)),
            color="Ticker:N",
            tooltip=["Date:T","Ticker:N",alt.Tooltip("Vol:Q",format=".2f")]
        )
        .interactive()
    )
    st.altair_chart(vol_chart, use_container_width=True)

with beta_tab:
    st.write("Rolling beta vs SPY.")
    beta_chart = (
        alt.Chart(
            roll_beta_df.reset_index().melt("Date", var_name="Ticker", value_name="Beta")
        )
        .mark_line()
        .encode(
            x="Date:T",
            y=alt.Y("Beta:Q", scale=alt.Scale(zero=False)),
            color="Ticker:N",
            tooltip=["Date:T","Ticker:N",alt.Tooltip("Beta:Q",format=".2f")]
        )
        .interactive()
    )
    st.altair_chart(beta_chart, use_container_width=True)

with dd_tab:
    st.write("Drawdown from running peak (%).")
    dd_chart = (
        alt.Chart(
            drawdown.reset_index().melt("Date", var_name="Ticker", value_name="DD")
        )
        .mark_line()
        .encode(
            x="Date:T",
            y=alt.Y("DD:Q", title="Drawdown (%)",
                    scale=alt.Scale(domain=[drawdown.min().min(), 0])),
            color="Ticker:N",
            tooltip=["Date:T","Ticker:N",alt.Tooltip("DD:Q",format=".2f")]
        )
        .interactive()
    )
    st.altair_chart(dd_chart, use_container_width=True)
