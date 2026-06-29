import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
from utils import indicators

np.random.seed(42)

# --- Test RSI ---
# Build a series that trends up strongly then down strongly
up = np.linspace(100, 150, 30) + np.random.normal(0, 0.5, 30)
down = np.linspace(150, 100, 30) + np.random.normal(0, 0.5, 30)
close = pd.Series(np.concatenate([up, down]))

rsi = indicators.calculate_rsi(close, period=14)
print("RSI tail (should be LOW after the downtrend):")
print(rsi.tail(5).round(2).tolist())
print("RSI mid (should be HIGH after the uptrend):")
print(rsi.iloc[28:33].round(2).tolist())
assert rsi.iloc[29] > 60, "RSI should be high after sustained uptrend"
assert rsi.iloc[-1] < 40, "RSI should be low after sustained downtrend"
print("RSI test PASSED\n")

# --- Test MA crossover ---
# Flat prices, then a single sharp spike on the very last candle so the
# fast MA (period 3) jumps above the slow MA (period 10) only at index -1.
base = np.full(30, 100.0)
base[-1] = 140.0
close2 = pd.Series(base)
cross = indicators.calculate_ma_crossover(close2, fast_period=3, slow_period=10)
print("MA crossover result:", cross)
assert cross["crossed"] == "bullish", "Expected a bullish crossover"
print("MA crossover test PASSED\n")

# --- Test breakout ---
df = pd.DataFrame({
    "high": [100]*20 + [105],
    "low": [95]*20 + [104],
    "close": [98]*20 + [106],  # breaks above 20-candle high of 100
})
result = indicators.detect_breakout(df, lookback=20)
print("Breakout result:", result)
assert result["breakout"] == "up", "Expected upward breakout"
print("Breakout test PASSED\n")

print("ALL INDICATOR TESTS PASSED")
