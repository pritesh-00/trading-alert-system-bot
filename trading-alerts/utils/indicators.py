"""
Technical indicator calculations: RSI, moving average crossover, breakout.
Pure pandas/numpy, no external TA library needed (keeps dependencies minimal).
"""
import pandas as pd
import numpy as np


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Standard Wilder's RSI.
    Returns a Series aligned with `close`, first `period` values will be NaN.
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    # When avg_loss is 0, RSI should be 100 (all gains)
    rsi = rsi.where(avg_loss != 0, 100)
    return rsi


def calculate_ma_crossover(close: pd.Series, fast_period: int = 9,
                            slow_period: int = 21) -> dict:
    """
    Detects the most recent crossover event between fast and slow SMA.
    Returns: {"fast": float, "slow": float, "crossed": "bullish"|"bearish"|None}
    "bullish" = fast crossed above slow on the latest candle (golden cross)
    "bearish" = fast crossed below slow on the latest candle (death cross)
    """
    fast_ma = close.rolling(fast_period).mean()
    slow_ma = close.rolling(slow_period).mean()

    if len(close) < slow_period + 1:
        return {"fast": None, "slow": None, "crossed": None}

    prev_fast, prev_slow = fast_ma.iloc[-2], slow_ma.iloc[-2]
    curr_fast, curr_slow = fast_ma.iloc[-1], slow_ma.iloc[-1]

    crossed = None
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        crossed = "bullish"
    elif prev_fast >= prev_slow and curr_fast < curr_slow:
        crossed = "bearish"

    return {"fast": curr_fast, "slow": curr_slow, "crossed": crossed}


def detect_breakout(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    Checks if the latest close broke above the highest high or below the
    lowest low of the prior `lookback` candles (excluding the current one).
    df must have columns: high, low, close
    Returns: {"breakout": "up"|"down"|None, "level": float}
    """
    if len(df) < lookback + 1:
        return {"breakout": None, "level": None}

    prior = df.iloc[-(lookback + 1):-1]
    latest_close = df["close"].iloc[-1]
    prior_high = prior["high"].max()
    prior_low = prior["low"].min()

    if latest_close > prior_high:
        return {"breakout": "up", "level": prior_high}
    elif latest_close < prior_low:
        return {"breakout": "down", "level": prior_low}
    return {"breakout": None, "level": None}
