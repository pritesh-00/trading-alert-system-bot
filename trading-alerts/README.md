# Trading Alert System Bot

Polls crypto (Binance), forex (Twelve Data), and Indian stocks (yfinance),
checks technical signals (RSI, MA crossover, breakout) and price-cross
alerts, and sends Discord alerts when conditions trigger.

## Running 24/7 via GitHub Actions (recommended, free)

This repo includes `.github/workflows/alerts.yml`, which runs `main.py --once`
automatically every 10 minutes using GitHub's own infrastructure — no
server, VPS, or always-on PC required.

### One-time setup

**1. Move your secrets out of `config.yaml` into GitHub Secrets**

`config.yaml` is committed to this public repo, so it must never contain
real secrets — only the placeholders you see in it now. The real Discord
webhook URL and Twelve Data API key instead go into GitHub's encrypted
Secrets:

1. Go to your repo on GitHub → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**
2. Add a secret named `DISCORD_WEBHOOK_URL` with your Discord webhook URL
   as the value
3. Add a second secret named `TWELVEDATA_API_KEY` with your Twelve Data
   API key

> ⚠️ If your old webhook URL or API key were ever committed to this repo
> in plaintext (including in earlier commit history), **regenerate both**:
> - Discord: channel settings → Integrations → Webhooks → delete the old
>   one, create a new one
> - Twelve Data: dashboard → regenerate API key
>
> A leaked secret in a public repo's history is permanently exposed even
> if you later remove it from the latest commit — regenerating is the
> only real fix.

**2. Enable Actions on the repo** (usually on by default for repos you own)
   Go to the **Actions** tab and confirm workflows are enabled.

**3. That's it.** The workflow will now run automatically every 10 minutes.
   You can also trigger a run manually any time from the **Actions** tab →
   **Trading Alerts (every 10 minutes)** → **Run workflow**.

### How it works

- Every 10 minutes, GitHub spins up a temporary Ubuntu VM, checks out this
  repo, installs dependencies, and runs `python main.py --once`.
- `--once` checks all markets a single time (instead of looping forever),
  since the workflow's schedule handles repetition.
- `state.json` (which tracks cooldowns so the bot doesn't spam the same
  alert every cycle) and any `armed: false` changes to `price_alerts` in
  `config.yaml` are committed back to the repo at the end of each run, so
  state persists between runs.
- The VM shuts down after the run. No idle cost, no server to maintain.

### Limitations to know about

- **Not millisecond-precise.** GitHub's cron scheduler is best-effort; under
  heavy load a run can be delayed by a few minutes. Fine for this use case.
- **GitHub Actions minutes.** Free for public repos (which this is) with a
  generous quota. If you ever make the repo private, scheduled runs consume
  your monthly Actions minutes allowance.
- **No sub-10-minute granularity** with this setup. If you need faster
  checks, a real always-on host (VPS, Railway, etc.) running continuous
  mode (see below) is the better fit.

## Running continuously (local / VPS / always-on host)

If you prefer one long-running process instead of scheduled single-shot
runs (e.g. on a VPS), run without `--once`:

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export TWELVEDATA_API_KEY="your_key_here"
python main.py
```

This polls each market on its own interval internally (defined in
`config.yaml` under `poll_interval_seconds`) using background threads, and
runs until stopped with Ctrl+C. For real 24/7 uptime this way, run it under
a process manager such as `systemd`, `screen`, `tmux`, or `nohup` so it
survives terminal disconnects and restarts on crash/reboot.

## Configuration

All non-secret settings live in `config.yaml`:

- `crypto.symbols` / `forex.symbols` / `indian_stocks.symbols` — what to track
- `technical_signals` — enable/disable and tune RSI, MA crossover, breakout
- `price_alerts` — one-shot price-cross alerts (auto-disarm after firing)
- `poll_interval_seconds` / `candle_interval` — only used in continuous mode

## Local development setup

```bash
pip install -r requirements.txt
cp config.yaml config.local.yaml   # optional: keep secrets out of config.yaml entirely
export DISCORD_WEBHOOK_URL="..."
export TWELVEDATA_API_KEY="..."
python main.py --once     # single check, good for testing
python main.py            # continuous mode
```
