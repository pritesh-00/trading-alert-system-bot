# Discord Trading Alerts Bot — Forex, Crypto & Indian Stocks

A free, self-hosted Python alert system that watches crypto, forex, and
Indian (NSE) stocks, and posts price-cross + technical-signal alerts to
your Discord server via webhook.

**Total cost: ₹0 / $0.** No paid API, no paid hosting required (with caveats
on hosting — see below).

---

## What it does

- **Price alerts**: "tell me when BTC crosses ₹/$ X"
- **Technical signals**, checked automatically on every poll:
  - RSI overbought/oversold
  - Fast/slow moving average crossover (golden cross / death cross)
  - N-candle breakout (price breaks above/below recent high/low)
- Sends nicely formatted embeds to a Discord channel
- Avoids spamming you — each signal type has a cooldown, and price alerts
  disarm themselves after firing once

## Data sources (all free)

| Market         | Source              | API key needed? | Free limit                          |
|----------------|----------------------|------------------|--------------------------------------|
| Crypto         | Binance public API   | No               | Very high (thousands/min)            |
| Forex          | Twelve Data          | Yes (free signup)| 800 requests/day, 8/min              |
| Indian stocks  | yfinance (Yahoo Finance) | No           | Unofficial, generally reliable but not guaranteed/SLA-backed |

---

## Setup

### 1. Install Python dependencies

```bash
pip install yfinance pandas requests pyyaml --break-system-packages
```

(Drop `--break-system-packages` if you're using a virtual environment,
which is recommended: `python3 -m venv venv && source venv/bin/activate`)

### 2. Create a Discord webhook

1. Open your Discord server → pick the channel you want alerts in
2. Click the gear icon (Edit Channel) → **Integrations** → **Webhooks**
3. **New Webhook** → name it (e.g. "Trading Alerts") → **Copy Webhook URL**
4. Paste it into `config.yaml` under `discord.webhook_url`

### 3. Get a free Twelve Data API key (for forex only)

1. Sign up free at https://twelvedata.com/
2. Copy your API key from the dashboard
3. Paste it into `config.yaml` under `twelvedata.api_key`

If you don't care about forex, you can skip this — just remove symbols
from `forex.symbols` in the config, or ignore forex errors in the logs.

### 4. Edit `config.yaml`

- Add/remove symbols under `crypto`, `forex`, `indian_stocks`
- Add price alerts under `price_alerts` (set `armed: true`)
- Tune RSI/MA/breakout thresholds under `technical_signals`

Symbol formats:
- Crypto (Binance): `BTCUSDT`, `ETHUSDT` (no slash)
- Forex (Twelve Data): `EUR/USD`, `USD/JPY` (with slash)
- Indian stocks (yfinance): `RELIANCE.NS`, `TCS.NS` (NSE suffix `.NS`, BSE is `.BO`)

### 5. Run it

```bash
python main.py
```

You should immediately get a "✅ Trading Alerts Bot Started" message in
your Discord channel. Leave it running — it polls in the background and
posts alerts as they trigger.

Stop with `Ctrl+C`.

---

## Running it 24/7 for free

The script needs to keep running to keep alerting. Options, cheapest first:

1. **Your own PC**, left on — free, but stops if your PC sleeps/shuts down.
2. **Oracle Cloud Free Tier** — genuinely free-forever small VM (ARM
   Ampere, 4 vCPU/24GB RAM tier exists at the time of writing). Best free
   "always-on" option if you want a real server. Search "Oracle Cloud
   Always Free" for current signup details and limits.
3. **Railway / Render free tier** — easiest to deploy, but free tiers on
   these platforms tend to sleep idle services or cap monthly hours;
   check current terms before relying on it.
4. **A Raspberry Pi or old laptop at home** — free if you already own the
   hardware.

To keep it running in the background on a Linux server:

```bash
nohup python3 main.py > alerts.log 2>&1 &
```

Or better, use a `systemd` service so it auto-restarts on crash/reboot —
ask if you'd like a ready-made systemd unit file for this.

---

## Project structure

```
trading-alerts/
├── config.yaml              # <-- you edit this for symbols/alerts
├── main.py                   # main engine, run this
├── state.json                # auto-created, tracks fired alerts (don't edit)
├── sources/
│   ├── binance_source.py      # crypto data
│   ├── twelvedata_source.py   # forex data
│   └── yfinance_source.py     # Indian stocks data
├── utils/
│   ├── discord_notifier.py    # sends Discord webhook messages
│   ├── indicators.py          # RSI, MA crossover, breakout math
│   └── state_manager.py       # alert cooldown/dedup tracking
└── test_indicators.py         # standalone test for the indicator math
```

## Notes & honest limitations

- **yfinance** has no official supported API — it works well in practice
  for NSE tickers but Yahoo can change things without notice. If Indian
  stock data starts failing, check for a `yfinance` package update first
  (`pip install --upgrade yfinance`).
- **Twelve Data free tier** is rate-limited (800 calls/day). The default
  config polls forex every 15 minutes to stay safely within that — don't
  drop this much lower without also reducing your forex symbol count.
- This is **not investment advice software** — it's a signal/notification
  tool. RSI/MA/breakout are common but simplistic indicators; treat alerts
  as a starting point for your own research, not a buy/sell instruction.
- Markets close (Indian markets, forex on weekends) — expect quiet
  periods where no new candles/alerts arrive; that's expected behavior,
  not a bug.

## Extending it

Want any of these next? Just ask:
- Slash commands in Discord to add/remove alerts without editing the YAML
- MACD, Bollinger Bands, or other indicators
- A Discord bot (instead of webhook-only) so you can query "what's BTC at
  right now?" interactively
- SQLite instead of JSON for state, if your watchlist grows large
