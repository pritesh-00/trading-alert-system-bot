"""
Crypto data via Coinbase Exchange public REST API.
No API key required for market data endpoints.
Docs: https://docs.cdp.coinbase.com/exchange/docs/welcome

Switched from Binance because Binance's public API returns HTTP 451
("Unavailable For Legal Reasons") for requests from many US-based cloud
provider IP ranges, including GitHub Actions runners. Coinbase, being a
US-based exchange, does not impose that same restriction.

Symbol format: 'BTC-USD', 'ETH-USD' (hyphenated, not 'BTCUSDT' like Binance).
"""
import requests
import pandas as pd
import logging

logger = logging.getLogger("coinbase_source")

BASE_URL = "https://api.exchange.coinbase.com"

# Coinbase only accepts a fixed set of granularities, in seconds.
_GRANULARITY_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "6h": 21600,
    "1d": 86400,
}


def get_klines(symbol: str, interval: str = "5m", limit: int = 100) -> pd.DataFrame:
    """
    Fetch OHLCV candles for a crypto symbol, e.g. 'BTC-USD'.
    interval: one of '1m', '5m', '15m', '1h', '6h', '1d'
    Returns a DataFrame with columns: open_time, open, high, low, close, volume
    (same shape as the old binance_source.get_klines, so callers don't change)
    """
    if interval not in _GRANULARITY_SECONDS:
        raise ValueError(
            f"Unsupported interval '{interval}' for Coinbase. "
            f"Supported: {list(_GRANULARITY_SECONDS)}"
        )
    granularity = _GRANULARITY_SECONDS[interval]

    url = f"{BASE_URL}/products/{symbol}/candles"
    params = {"granularity": granularity}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise RuntimeError(f"No candle data returned for {symbol}")

    # Coinbase returns: [time, low, high, open, close, volume], newest first
    df = pd.DataFrame(data, columns=["time", "low", "high", "open", "close", "volume"])
    df = df.sort_values("time").reset_index(drop=True)  # oldest -> newest
    df["open_time"] = pd.to_datetime(df["time"], unit="s")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df.tail(limit).reset_index(drop=True)
    return df[["open_time", "open", "high", "low", "close", "volume"]]


def get_current_price(symbol: str) -> float:
    """Fetch the latest traded price for a symbol, e.g. 'BTC-USD'."""
    url = f"{BASE_URL}/products/{symbol}/ticker"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return float(resp.json()["price"])


if __name__ == "__main__":
    # quick manual test
    logging.basicConfig(level=logging.INFO)
    df = get_klines("BTC-USD", "5m", 10)
    print(df)
    print("Current price:", get_current_price("BTC-USD"))
