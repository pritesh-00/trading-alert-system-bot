"""
Sends alert messages to a Discord channel via webhook.
No bot hosting, no gateway connection — just an HTTP POST.

To get a webhook URL:
  Discord -> your server -> channel settings (gear icon) -> Integrations
  -> Webhooks -> New Webhook -> Copy Webhook URL
"""
import requests
import time
import logging

logger = logging.getLogger("discord_notifier")

COLOR_BULLISH = 0x2ECC71   # green
COLOR_BEARISH = 0xE74C3C   # red
COLOR_INFO = 0x3498DB      # blue


def send_alert(webhook_url: str, title: str, description: str,
                color: int = COLOR_INFO, fields: list | None = None,
                max_retries: int = 3) -> bool:
    """
    Send a rich embed message to Discord.

    fields: optional list of {"name": str, "value": str, "inline": bool}
    Returns True on success, False on failure (after retries).
    """
    if not webhook_url or "PUT_YOUR" in webhook_url:
        logger.error("Discord webhook URL is not configured in config.yaml")
        return False

    embed = {
        "title": title,
        "description": description,
        "color": color,
    }
    if fields:
        embed["fields"] = fields

    payload = {"embeds": [embed]}

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            # Discord rate limit: 429 with "retry_after" in body
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 1)
                logger.warning(f"Discord rate limited, retrying after {retry_after}s")
                time.sleep(retry_after)
                continue
            if resp.status_code in (200, 204):
                return True
            logger.error(f"Discord webhook failed: {resp.status_code} {resp.text}")
        except requests.RequestException as e:
            logger.error(f"Discord webhook request error (attempt {attempt}): {e}")
            time.sleep(2 * attempt)

    return False
