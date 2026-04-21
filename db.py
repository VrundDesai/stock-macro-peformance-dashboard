# db.py
"""
Simple SQLite helper layer for storing and retrieving historical
price data and symbol metadata. Keeps all SQL out of app.py so the UI stays clean.

Schema:
  prices(
      symbol TEXT NOT NULL,
      date   TEXT NOT NULL,   -- ISO YYYY-MM-DD
      close  REAL NOT NULL,
      PRIMARY KEY (symbol, date)
  )
  symbol_meta(
      symbol   TEXT PRIMARY KEY,
      sector   TEXT,
      industry TEXT
  )
"""

import sqlite3
from pathlib import Path
import pandas as pd

# Database file lives next to this script
DB_PATH = Path(__file__).with_name("portfolio.db")


def get_conn():
    """Return a new sqlite3 connection."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                symbol TEXT NOT NULL,
                date   TEXT NOT NULL,
                close  REAL NOT NULL,
                PRIMARY KEY (symbol, date)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS symbol_meta (
                symbol   TEXT PRIMARY KEY,
                sector   TEXT,
                industry TEXT
            );
            """
        )
        conn.commit()


def upsert_prices(df_wide: pd.DataFrame):
    """
    Insert or replace price rows from a wide DataFrame:
    index = dates (DatetimeIndex), columns = symbols, values = close prices.
    """
    if df_wide.empty:
        return

    df = df_wide.copy()
    df.index = pd.to_datetime(df.index)

    df_long = (
        df.reset_index()
          .melt(id_vars=df.index.name or "index", var_name="symbol", value_name="close")
          .rename(columns={df.index.name or "index": "date"})
    )

    df_long = df_long.dropna(subset=["close"])
    df_long["date"] = pd.to_datetime(df_long["date"]).dt.strftime("%Y-%m-%d")

    rows = [
        (row.symbol, row.date, float(row.close))
        for row in df_long.itertuples(index=False)
    ]

    with get_conn() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO prices (symbol, date, close)
            VALUES (?, ?, ?);
            """,
            rows,
        )
        conn.commit()


def fetch_prices(symbols, start=None, end=None) -> pd.DataFrame:
    """
    Fetch prices for a list of symbols between optional start/end (YYYY-MM-DD strings).
    Returns a wide DataFrame (index=date, columns=symbols).
    """
    if not symbols:
        return pd.DataFrame()

    placeholders = ",".join(["?"] * len(symbols))
    q = f"""
        SELECT date, symbol, close
        FROM prices
        WHERE symbol IN ({placeholders})
    """
    params = list(symbols)

    if start:
        q += " AND date >= ?"
        params.append(start)
    if end:
        q += " AND date <= ?"
        params.append(end)

    q += " ORDER BY date;"

    with get_conn() as conn:
        df = pd.read_sql(q, conn, params=params, parse_dates=["date"])

    if df.empty:
        return pd.DataFrame()

    return df.pivot(index="date", columns="symbol", values="close").sort_index()


def upsert_metadata_from_csv(path="metadata.csv"):
    """
    Load symbol metadata (sector, industry) from a CSV and upsert into DB.
    CSV should have columns: symbol,sector,industry
    """
    df = pd.read_csv(path)
    rows = df.itertuples(index=False, name=None)  # (symbol, sector, industry)
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO symbol_meta (symbol, sector, industry) VALUES (?, ?, ?);",
            rows
        )
        conn.commit()


def get_symbol_meta(symbol: str):
    """
    Returns (sector, industry) for a given symbol, or (None, None).
    """
    with get_conn() as conn:
        df = pd.read_sql(
            "SELECT sector, industry FROM symbol_meta WHERE symbol = ?;",
            conn, params=(symbol,), parse_dates=[]
        )
    if df.empty:
        return None, None
    return df.iloc[0]["sector"], df.iloc[0]["industry"]
