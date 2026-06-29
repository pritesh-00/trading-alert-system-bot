"""
Forex data via Twelve Data free API.
Free tier: 800 requests/day, 8 requests/minute.
Sign up free at https://twelvedata.com/ to get an API key.
"""
import requests
import pandas as pd
import logging

logger = logging.getLogger("twelvedata_source")

BASE_URL = "https://api.twelvedata.com"


def get_time_series(symbol: str, api_key: str, interval: str = "15min",
                     outputsize: int = 100) -> pd.DataFrame:
    """
    Fetch OHLC candles for a forex pair, e.g. 'EUR/USD'.
    interval: 1min, 5min, 15min, 30min, 1h, 1day, etc.
    Returns a DataFrame with columns: datetime, open, high, low, close
    """
    url = f"{BASE_URL}/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": api_key,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") == "error":
        raise RuntimeError(f"Twelve Data error for {symbol}: {data.get('message')}")

    values = data.get("values", [])
    if not values:
        raise RuntimeError(f"No data returned for {symbol}")

    df = pd.DataFrame(values)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df["datetime"] = pd.to_datetime(df["datetime"])
    # Twelve Data returns newest-first; reverse to chronological order
    df = df.sort_values("datetime").reset_index(drop=True)
    return df[["datetime", "open", "high", "low", "close"]]


def get_current_price(symbol: str, api_key: str) -> float:
    """Fetch the latest exchange rate for a forex pair."""
    url = f"{BASE_URL}/price"
    resp = requests.get(url, params={"symbol": symbol, "apikey": api_key}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "price" not in data:
        raise RuntimeError(f"Twelve Data error for {symbol}: {data}")
    return float(data["price"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    KEY = "demo"  # replace with your real key for non-trial symbols
    df = get_time_series("EUR/USD", KEY, "15min", 10)
    print(df)
