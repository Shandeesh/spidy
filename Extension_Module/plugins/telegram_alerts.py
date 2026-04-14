"""
Telegram Alerts Plugin — sends real-time trade notifications to a Telegram bot.

Setup:
  1. Create a bot via @BotFather and get your token.
  2. Get your chat ID (send /start to @userinfobot).
  3. Add to Shared_Data/configs/.env:
       TELEGRAM_BOT_TOKEN=your_bot_token_here
       TELEGRAM_CHAT_ID=your_chat_id_here
  4. The plugin auto-loads on next bridge restart.
"""
import os
import sys
import threading

# Add paths
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "../../")))

from plugin_base import SpidyPlugin


class TelegramAlertPlugin(SpidyPlugin):
    """
    Sends Telegram messages on trade open, trade close, and system alerts.
    Silently disables itself if no token/chat_id is configured.
    """

    name    = "TelegramAlerts"
    enabled = True

    _EMOJIS = {"BUY": "🟢", "SELL": "🔴", "INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "🚨"}

    def __init__(self):
        from dotenv import load_dotenv
        _env = os.path.abspath(
            os.path.join(_HERE, "../../Shared_Data/configs/.env")
        )
        load_dotenv(dotenv_path=_env)

        self._token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        if not self._token or not self._chat_id:
            print(
                "[TelegramAlerts] No TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env — "
                "plugin loaded but notifications disabled."
            )
            self.enabled = False
            return

        # Verify telegram is importable
        try:
            import telegram
            self._tg_available = True
        except ImportError:
            print("[TelegramAlerts] python-telegram-bot not installed — notifications disabled.")
            self._tg_available = False

    def _send(self, text: str) -> None:
        """Fire-and-forget message in a daemon thread."""
        if not self.enabled or not getattr(self, "_tg_available", False):
            return

        def _dispatch():
            try:
                import asyncio
                import telegram
                async def _send_async():
                    bot = telegram.Bot(token=self._token)
                    await bot.send_message(chat_id=self._chat_id, text=text, parse_mode="HTML")
                asyncio.run(_send_async())
            except Exception as e:
                print(f"[TelegramAlerts] Send failed: {e}")

        threading.Thread(target=_dispatch, daemon=True).start()

    def on_trade_open(self, symbol: str, action: str, volume: float,
                      price: float, ticket: int, strategy: str) -> None:
        emoji = self._EMOJIS.get(action, "📊")
        msg = (
            f"{emoji} <b>TRADE OPENED</b>\n"
            f"📍 {symbol} <b>{action}</b> @ {price:.5f}\n"
            f"📦 Vol: {volume} | ID: #{ticket}\n"
            f"🤖 Strategy: {strategy}"
        )
        self._send(msg)

    def on_trade_close(self, symbol: str, action: str, profit: float,
                       ticket: int, reason: str) -> None:
        sign  = "+" if profit >= 0 else ""
        emoji = "💰" if profit >= 0 else "📉"
        msg = (
            f"{emoji} <b>TRADE CLOSED</b>\n"
            f"📍 {symbol} {action} #{ticket}\n"
            f"💵 P&L: <b>{sign}${profit:.2f}</b>\n"
            f"📌 Reason: {reason}"
        )
        self._send(msg)

    def on_alert(self, level: str, message: str) -> None:
        emoji = self._EMOJIS.get(level, "⚡")
        msg   = f"{emoji} <b>[{level}]</b> {message}"
        self._send(msg)

    def on_bridge_start(self) -> None:
        self._send("🚀 <b>Spidy Bridge Started</b> — Monitoring active.")
