"""
Security Monitor: Thread-safe audit log with brute-force detection.
Records every API call and raises alerts on repeated auth failures.
"""
import threading
import time
import hashlib
import os
from collections import defaultdict, deque
from datetime import datetime

_DEFAULT_LOG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../Shared_Data/configs/audit.log")
)

class AuditLog:
    """
    Append-only audit log for all API requests.
    - Logs endpoint, hashed API key, timestamp, IP, and success/failure.
    - Detects brute-force: >10 failed auth attempts within 60s from same IP.
    """

    def __init__(self, log_path: str = _DEFAULT_LOG, alert_threshold: int = 10, window_secs: int = 60):
        self._lock    = threading.Lock()
        self._path    = log_path
        self._thresh  = alert_threshold
        self._window  = window_secs
        # { ip: deque of failure timestamps }
        self._failures: dict[str, deque] = defaultdict(lambda: deque())
        self._alert_ips: set = set()
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def _hash_key(self, key: str | None) -> str:
        if not key:
            return "NONE"
        return "sha:" + hashlib.sha256(key.encode()).hexdigest()[:12]

    def record(self, endpoint: str, method: str, api_key: str | None,
               success: bool, ip: str = "unknown") -> None:
        """
        Record one API request to the audit log.
        Args:
            endpoint: e.g. '/trade'
            method:   e.g. 'POST'
            api_key:  raw key value (will be hashed before storage)
            success:  True = auth passed, False = auth failed / 403
            ip:       client IP address
        """
        ts      = datetime.utcnow().isoformat() + "Z"
        status  = "OK" if success else "FAIL"
        key_ref = self._hash_key(api_key)
        line    = f"{ts} | {status} | {method:6s} {endpoint:30s} | ip={ip} key={key_ref}\n"

        with self._lock:
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass  # Audit failure must never crash the API

            if not success:
                now = time.time()
                q   = self._failures[ip]
                q.append(now)
                # Evict entries older than window
                while q and (now - q[0]) > self._window:
                    q.popleft()

                if len(q) >= self._thresh and ip not in self._alert_ips:
                    self._alert_ips.add(ip)
                    alert = (
                        f"[SECURITY ALERT] Brute-force detected from {ip}: "
                        f"{len(q)} failures in {self._window}s — {endpoint}\n"
                    )
                    print(alert, flush=True)
                    try:
                        with open(self._path, "a", encoding="utf-8") as f:
                            f.write(alert)
                    except Exception:
                        pass

    def get_recent(self, lines: int = 100) -> list[str]:
        """Return the last N lines from the audit log."""
        with self._lock:
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return f.readlines()[-lines:]
            except Exception:
                return []

    def is_flagged(self, ip: str) -> bool:
        """Returns True if this IP has triggered a brute-force alert."""
        return ip in self._alert_ips


# Module-level singleton
audit_log = AuditLog()
