"""
Main trading alerts engine.
Polls crypto (Binance), forex (Twelve Data), and Indian stocks (yfinance),
checks price-cross and technical signal conditions, and sends Discord
webhook alerts when conditions trigger.

Run with:  python main.py

Stop with Ctrl+C. For 24/7 operation, run this under a process manager
(see README.md for systemd / screen / nohup options) or deploy it to a
free-tier always-on host.
"""
import time
import logging
import yaml
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sources import binance_source, twelvedata_source, yfinance_source
from utils import indicators, state_manager
from utils.discord_notifier import send_alert, COLOR_BULLISH, COLOR_BEARISH, COLOR_INFO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def save_config(cfg: dict):
    """Used to persist 'armed: false' after a price alert fires."""
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)


# ----------------------------------------------------------------------
# Technical signal checks (shared across markets, operates on a DataFrame
# with at minimum an 'open'/'high'/'low'/'close' set of columns)
# ----------------------------------------------------------------------

def check_technical_signals(df, symbol: str, market: str, webhook_url: str, cfg: dict):
    tech_cfg = cfg["technical_signals"]
    close = df["close"]

    # --- RSI ---
    if tech_cfg["rsi"]["enabled"]:
        rsi_series = indicators.calculate_rsi(close, tech_cfg["rsi"]["period"])
        latest_rsi = rsi_series.iloc[-1]
        if pd_notna(latest_rsi):
            if latest_rsi >= tech_cfg["rsi"]["overbought"]:
                key = f"{symbol}_rsi_overbought"
                if state_manager.should_fire(key, "rsi"):
                    send_alert(
                        webhook_url,
                        title=f"🔴 RSI Overbought — {symbol} ({market})",
                        description=f"RSI is at **{latest_rsi:.1f}** (overbought threshold: {tech_cfg['rsi']['overbought']})",
                        color=COLOR_BEARISH,
                    )
                    state_manager.mark_fired(key)
            elif latest_rsi <= tech_cfg["rsi"]["oversold"]:
                key = f"{symbol}_rsi_oversold"
                if state_manager.should_fire(key, "rsi"):
                    send_alert(
                        webhook_url,
                        title=f"🟢 RSI Oversold — {symbol} ({market})",
                        description=f"RSI is at **{latest_rsi:.1f}** (oversold threshold: {tech_cfg['rsi']['oversold']})",
                        color=COLOR_BULLISH,
                    )
                    state_manager.mark_fired(key)

    # --- Moving Average Crossover ---
    if tech_cfg["moving_average_crossover"]["enabled"]:
        cross = indicators.calculate_ma_crossover(
            close,
            tech_cfg["moving_average_crossover"]["fast_period"],
            tech_cfg["moving_average_crossover"]["slow_period"],
        )
        if cross["crossed"] == "bullish":
            key = f"{symbol}_ma_bullish_{int(time.time() // 300)}"  # dedupe within 5-min bucket
            send_alert(
                webhook_url,
                title=f"🟢 Golden Cross — {symbol} ({market})",
                description=(
                    f"Fast MA ({tech_cfg['moving_average_crossover']['fast_period']}) crossed "
                    f"**above** Slow MA ({tech_cfg['moving_average_crossover']['slow_period']})"
                ),
                color=COLOR_BULLISH,
                fields=[
                    {"name": "Fast MA", "value": f"{cross['fast']:.4f}", "inline": True},
                    {"name": "Slow MA", "value": f"{cross['slow']:.4f}", "inline": True},
                ],
            )
        elif cross["crossed"] == "bearish":
            send_alert(
                webhook_url,
                title=f"🔴 Death Cross — {symbol} ({market})",
                description=(
                    f"Fast MA ({tech_cfg['moving_average_crossover']['fast_period']}) crossed "
                    f"**below** Slow MA ({tech_cfg['moving_average_crossover']['slow_period']})"
                ),
                color=COLOR_BEARISH,
                fields=[
                    {"name": "Fast MA", "value": f"{cross['fast']:.4f}", "inline": True},
                    {"name": "Slow MA", "value": f"{cross['slow']:.4f}", "inline": True},
                ],
            )

    # --- Breakout ---
    if tech_cfg["breakout"]["enabled"]:
        breakout = indicators.detect_breakout(df, tech_cfg["breakout"]["lookback_candles"])
        if breakout["breakout"] == "up":
            key = f"{symbol}_breakout_up"
            if state_manager.should_fire(key, "breakout"):
                send_alert(
                    webhook_url,
                    title=f"🚀 Breakout UP — {symbol} ({market})",
                    description=f"Price broke above the {tech_cfg['breakout']['lookback_candles']}-candle high of **{breakout['level']:.4f}**",
                    color=COLOR_BULLISH,
                )
                state_manager.mark_fired(key)
        elif breakout["breakout"] == "down":
            key = f"{symbol}_breakout_down"
            if state_manager.should_fire(key, "breakout"):
                send_alert(
                    webhook_url,
                    title=f"⚠️ Breakout DOWN — {symbol} ({market})",
                    description=f"Price broke below the {tech_cfg['breakout']['lookback_candles']}-candle low of **{breakout['level']:.4f}**",
                    color=COLOR_BEARISH,
                )
                state_manager.mark_fired(key)


def pd_notna(value) -> bool:
    import pandas as pd
    return pd.notna(value)


# ----------------------------------------------------------------------
# Price-cross alert checks
# ----------------------------------------------------------------------

def check_price_alerts(current_prices: dict, webhook_url: str, cfg: dict):
    """
    current_prices: {symbol: latest_price}
    Mutates cfg in place (disarms triggered alerts) and persists to disk.
    """
    changed = False
    for alert in cfg.get("price_alerts", []):
        if not alert.get("armed", True):
            continue
        symbol = alert["symbol"]
        if symbol not in current_prices:
            continue
        price = current_prices[symbol]
        level = alert["level"]
        direction = alert["direction"]

        triggered = (direction == "above" and price >= level) or \
                    (direction == "below" and price <= level)

        if triggered:
            send_alert(
                webhook_url,
                title=f"🔔 Price Alert — {symbol}",
                description=f"Price is now **{price:.4f}**, crossed {direction} **{level}**",
                color=COLOR_INFO,
            )
            alert["armed"] = False
            changed = True

    if changed:
        save_config(cfg)


# ----------------------------------------------------------------------
# Per-market polling loops (run in separate threads so a slow/broken
# source for one market never delays the others)
# ----------------------------------------------------------------------

def crypto_loop(cfg: dict):
    webhook_url = cfg["discord"]["webhook_url"]
    interval = cfg["candle_interval"]["crypto"]
    poll_sec = cfg["poll_interval_seconds"]["crypto"]

    while True:
        try:
            current_prices = {}
            for symbol in cfg["crypto"]["symbols"]:
                df = binance_source.get_klines(symbol, interval, limit=100)
                current_prices[symbol] = df["close"].iloc[-1]
                check_technical_signals(df, symbol, "crypto", webhook_url, cfg)
            check_price_alerts(current_prices, webhook_url, cfg)
        except Exception as e:
            logger.error(f"Crypto loop error: {e}")
        time.sleep(poll_sec)


def forex_loop(cfg: dict):
    webhook_url = cfg["discord"]["webhook_url"]
    interval = cfg["candle_interval"]["forex"]
    poll_sec = cfg["poll_interval_seconds"]["forex"]
    api_key = cfg["twelvedata"]["api_key"]

    while True:
        try:
            current_prices = {}
            for symbol in cfg["forex"]["symbols"]:
                df = twelvedata_source.get_time_series(symbol, api_key, interval, outputsize=100)
                current_prices[symbol] = df["close"].iloc[-1]
                check_technical_signals(df, symbol, "forex", webhook_url, cfg)
            check_price_alerts(current_prices, webhook_url, cfg)
        except Exception as e:
            logger.error(f"Forex loop error: {e}")
        time.sleep(poll_sec)


def indian_stocks_loop(cfg: dict):
    webhook_url = cfg["discord"]["webhook_url"]
    interval = cfg["candle_interval"]["indian_stocks"]
    poll_sec = cfg["poll_interval_seconds"]["indian_stocks"]

    while True:
        try:
            current_prices = {}
            for symbol in cfg["indian_stocks"]["symbols"]:
                df = yfinance_source.get_history(symbol, interval, period="5d")
                current_prices[symbol] = df["close"].iloc[-1]
                check_technical_signals(df, symbol, "indian_stocks", webhook_url, cfg)
            check_price_alerts(current_prices, webhook_url, cfg)
        except Exception as e:
            logger.error(f"Indian stocks loop error: {e}")
        time.sleep(poll_sec)


def main():
    cfg = load_config()

    if "PUT_YOUR" in cfg["discord"]["webhook_url"]:
        logger.error("Set your Discord webhook_url in config.yaml before running.")
        return

    logger.info("Starting trading alerts engine...")
    send_alert(
        cfg["discord"]["webhook_url"],
        title="✅ Trading Alerts Bot Started",
        description="Now monitoring crypto, forex, and Indian stocks.",
        color=COLOR_INFO,
    )

    threads = [
        threading.Thread(target=crypto_loop, args=(cfg,), daemon=True, name="crypto"),
        threading.Thread(target=forex_loop, args=(cfg,), daemon=True, name="forex"),
        threading.Thread(target=indian_stocks_loop, args=(cfg,), daemon=True, name="indian_stocks"),
    ]
    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down.")


if __name__ == "__main__":
    main()
