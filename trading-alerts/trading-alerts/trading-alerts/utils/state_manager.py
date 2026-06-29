"""
Tracks which alerts have already fired so we don't spam Discord every
poll cycle with the same signal. Persisted to a local JSON file so
state survives restarts.
"""
import json
import os
import time
import logging

logger = logging.getLogger("state_manager")

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.json")

# Minimum seconds before the same signal type for the same symbol can
# fire again (prevents re-alerting every single poll while a condition
# remains true, e.g. RSI staying above 70 for hours).
COOLDOWN_SECONDS = {
    "rsi": 3600,        # 1 hour
    "ma_crossover": 0,  # crossovers are already one-shot events, no cooldown needed
    "breakout": 3600,   # 1 hour
    "price_alert": 0,   # one-shot, disarmed after firing
}


def _load() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read state file, starting fresh: {e}")
        return {}


def _save(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except OSError as e:
        logger.error(f"Could not write state file: {e}")


def should_fire(signal_key: str, signal_type: str) -> bool:
    """
    signal_key: unique identifier, e.g. "BTCUSDT_rsi_overbought"
    signal_type: one of the COOLDOWN_SECONDS keys, determines cooldown duration
    Returns True if enough time has passed (or never fired before).
    """
    state = _load()
    last_fired = state.get(signal_key)
    cooldown = COOLDOWN_SECONDS.get(signal_type, 0)

    if last_fired is None:
        return True
    return (time.time() - last_fired) >= cooldown


def mark_fired(signal_key: str):
    """Record that a signal just fired, for cooldown tracking."""
    state = _load()
    state[signal_key] = time.time()
    _save(state)
