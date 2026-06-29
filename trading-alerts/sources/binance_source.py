"""
Crypto data via Binance public REST API.
No API key required for market data endpoints.
Docs: https://binance-docs.github.io/apidocs/spot/en/
"""
import requests
import pandas as pd
import logging

logger = logging.getLogger("binance_source")

BASE_URL = "https://api.binance.com"


def get_klines(symbol: str, interval: str = "5m", limit: int = 100) -> pd.DataFrame:
    """
    Fetch OHLCV candles for a crypto symbol, e.g. 'BTCUSDT'.
    interval: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d, etc.
    Returns a DataFrame with columns: open_time, open, high, low, close, volume
    """
    url = f"{BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    return df[["open_time", "open", "high", "low", "close", "volume"]]


def get_current_price(symbol: str) -> float:
    """Fetch the latest traded price for a symbol."""
    url = f"{BASE_URL}/api/v3/ticker/price"
    resp = requests.get(url, params={"symbol": symbol}, timeout=10)
    resp.raise_for_status()
    return float(resp.json()["price"])


if __name__ == "__main__":
    # quick manual test
    logging.basicConfig(level=logging.INFO)
    df = get_klines("BTCUSDT", "5m", 10)
    print(df)
    print("Current price:", get_current_price("BTCUSDT"))
