"""
Indian stock data via yfinance (Yahoo Finance wrapper).
No API key required. Use NSE ticker format: SYMBOL.NS (e.g. RELIANCE.NS)
or BSE format SYMBOL.BO.

Note: Yahoo Finance has no official supported API; yfinance scrapes
public endpoints. It works well in practice but can occasionally break
or rate-limit — this is the tradeoff for a free, no-key Indian equities
source. If it becomes unreliable, NSE's own (unofficial) data endpoints
or a paid provider are fallback options.
"""
import yfinance as yf
import pandas as pd
import logging

logger = logging.getLogger("yfinance_source")


def get_history(symbol: str, interval: str = "15m", period: str = "5d") -> pd.DataFrame:
    """
    Fetch OHLCV candles for an NSE/BSE symbol, e.g. 'RELIANCE.NS'.
    interval: 1m, 5m, 15m, 30m, 1h, 1d, etc. (intraday intervals limited to recent days)
    period: how far back to fetch (e.g. '5d', '1mo')
    Returns a DataFrame with columns: datetime, open, high, low, close, volume
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        raise RuntimeError(f"No data returned for {symbol}")

    df = df.reset_index()
    # yfinance names the datetime column "Datetime" for intraday, "Date" for daily
    dt_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={
        dt_col: "datetime", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume"
    })
    return df[["datetime", "open", "high", "low", "close", "volume"]]


def get_current_price(symbol: str) -> float:
    """Fetch the latest available close price for a symbol."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1d", interval="1m")
    if df.empty:
        # market may be closed; fall back to last daily close
        df = ticker.history(period="5d", interval="1d")
    return float(df["Close"].iloc[-1])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = get_history("RELIANCE.NS", "15m", "5d")
    print(df.tail())
    print("Current price:", get_current_price("RELIANCE.NS"))
