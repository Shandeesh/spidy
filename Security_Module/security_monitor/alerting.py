"""
Spidy AI — Real-Time Failure Alerting
Supports: Telegram Bot API (primary), Desktop Notification (fallback)
"""
import os
import sys
import json
import time
import logging
import threading
from datetime import datetime

logger = logging.getLogger("spidy.alerting")

# --- Telegram Alerting ---
def _send_telegram(message: str, severity: str = "INFO") -> bool:
    """Send alert via Telegram Bot API."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        return False
    try:
        import urllib.request
        emoji = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "ℹ️"}.get(severity, "")
        text = f"{emoji} *Spidy Alert [{severity}]*\n\n{message}\n\n_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")
        return False

# --- Desktop Notification Fallback ---
def _send_desktop(message: str, severity: str = "INFO") -> bool:
    """Send desktop notification (Windows toast)."""
    try:
        if sys.platform.startswith('win'):
            import subprocess
            title = f"Spidy Alert [{severity}]"
            short_msg = message[:200] if len(message) > 200 else message
            ps_cmd = f'''powershell -Command "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(1); $text = $xml.GetElementsByTagName('text'); $text[0].AppendChild($xml.CreateTextNode('{title}')) | Out-Null; $text[1].AppendChild($xml.CreateTextNode('{short_msg.replace(chr(39), "")}')) | Out-Null; $toast = [Windows.UI.Notifications.ToastNotification]::new($xml); [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Spidy AI').Show($toast)"'''
            subprocess.Popen(ps_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception as e:
        logger.warning(f"Desktop notification failed: {e}")
    return False

# --- Main Alert Interface ---
_alert_lock = threading.Lock()
_last_alerts: dict = {}  # Throttle: {message_hash: timestamp}
_THROTTLE_SECONDS = 60  # Don't repeat same alert within 60s

def alert(message: str, severity: str = "WARNING", throttle: bool = True) -> bool:
    """
    Send an alert via available channels.
    Severity: 'INFO', 'WARNING', 'CRITICAL'
    Returns True if at least one channel succeeded.
    """
    with _alert_lock:
        if throttle:
            msg_hash = hash(message)
            now = time.time()
            if msg_hash in _last_alerts and (now - _last_alerts[msg_hash]) < _THROTTLE_SECONDS:
                return False
            _last_alerts[msg_hash] = now
            _last_alerts.update({k: v for k, v in _last_alerts.items() if now - v < _THROTTLE_SECONDS * 10})
    
    log_fn = getattr(logger, severity.lower(), logger.warning)
    log_fn(f"ALERT: {message}")
    
    sent = _send_telegram(message, severity)
    if not sent:
        sent = _send_desktop(message, severity)
    
    try:
        from audit_log import audit_log
        audit_log("ALERT", message, severity)
    except ImportError:
        pass
    
    return sent
