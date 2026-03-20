"""
market_intelligence.py — Spidy AI Market Intelligence Module
Gathers live macro signals: Fear & Greed Index + Economic Calendar warnings.
Designed to be called from bridge_server.py to enrich trade decisions.
"""

import json
import time
import re
from datetime import datetime, timedelta

# ── Cache ─────────────────────────────────────────────────────────────────────
_cache = {}
_cache_ttl = {
    "fear_greed": 600,       # 10 min (CNN updates ~hourly)
    "calendar": 300,          # 5 min (upcoming events)
}


def _is_cache_valid(key: str) -> bool:
    if key not in _cache:
        return False
    return (time.time() - _cache[key]["ts"]) < _cache_ttl.get(key, 300)


# ── Fear & Greed Index ────────────────────────────────────────────────────────
def get_fear_greed() -> dict:
    """
    Fetches CNN Fear & Greed Index from the official CNN API.
    Returns: { score: int (0-100), label: str, timestamp: str }
    """
    if _is_cache_valid("fear_greed"):
        return _cache["fear_greed"]["data"]

    result = {"score": 50, "label": "Neutral", "timestamp": datetime.now().isoformat()}

    try:
        import requests
        # CNN Fear & Greed API (public endpoint)
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://edition.cnn.com/markets/fear-and-greed",
        }
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            score_raw = data.get("fear_and_greed", {}).get("score", 50)
            rating = data.get("fear_and_greed", {}).get("rating", "Neutral")

            score = round(float(score_raw))
            result = {
                "score": score,
                "label": rating.title(),
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        print(f"[MarketIntel] Fear&Greed fetch failed: {e}")
        # Fallback: try alternative API
        try:
            import requests
            alt_url = "https://api.alternative.me/fng/?limit=1&format=json"
            resp = requests.get(alt_url, timeout=6)
            if resp.status_code == 200:
                data = resp.json()["data"][0]
                result = {
                    "score": int(data.get("value", 50)),
                    "label": data.get("value_classification", "Neutral"),
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e2:
            print(f"[MarketIntel] Fear&Greed alt fetch failed: {e2}")

    _cache["fear_greed"] = {"data": result, "ts": time.time()}
    return result


# ── Economic Calendar ─────────────────────────────────────────────────────────
# Known HIGH-impact event patterns that move markets significantly
HIGH_IMPACT_PATTERNS = [
    "nfp", "non-farm", "fomc", "fed decision", "interest rate decision",
    "cpi", "inflation", "gdp", "unemployment", "jobless claims",
    "pmi", "ism", "retail sales", "ecb", "boe", "rba", "boj",
    "fed chair", "powell", "lagarde", "central bank",
    "trade balance", "current account", "housing starts",
]


def get_upcoming_events(hours_ahead: int = 4) -> list:
    """
    Fetches upcoming high-impact economic events from ForexFactory (RSS).
    Returns list of { event, time, impact, minutes_away }
    """
    if _is_cache_valid("calendar"):
        return _cache["calendar"]["data"]

    events = []

    try:
        import feedparser
        # ForexFactory RSS (public)
        feed = feedparser.parse("https://nfs.faireconomy.media/ff_calendar_thisweek.xml")
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)

        for entry in feed.entries:
            try:
                title = entry.get("title", "")
                # Parse time from entry
                published = entry.get("published_parsed", None)
                if not published:
                    continue

                event_dt = datetime(*published[:6])
                if event_dt < now or event_dt > cutoff:
                    continue

                minutes_away = int((event_dt - now).total_seconds() / 60)

                # Classify impact
                title_lower = title.lower()
                is_high_impact = any(p in title_lower for p in HIGH_IMPACT_PATTERNS)
                impact = "HIGH" if is_high_impact else "MEDIUM"

                events.append({
                    "event": title,
                    "time_utc": event_dt.strftime("%Y-%m-%d %H:%M UTC"),
                    "impact": impact,
                    "minutes_away": minutes_away,
                })

            except Exception:
                continue

        # Sort by time
        events.sort(key=lambda x: x["minutes_away"])

    except Exception as e:
        print(f"[MarketIntel] Calendar fetch failed: {e}")

    _cache["calendar"] = {"data": events, "ts": time.time()}
    return events


def get_next_high_impact_event() -> dict:
    """
    Returns the next HIGH-impact event within 4 hours, or None.
    """
    events = get_upcoming_events(hours_ahead=4)
    for ev in events:
        if ev.get("impact") == "HIGH":
            return ev
    return {}


def is_near_high_impact_event(symbol: str = "", buffer_minutes: int = 5) -> tuple:
    """
    Returns (True, event_name) if a HIGH-impact event is within buffer_minutes.
    Used in validate_entry() to hard-block new trades before major news.
    """
    events = get_upcoming_events(hours_ahead=1)  # Only look 1h ahead for blocking

    # Currency mapping — which news affects which symbol
    symbol_upper = symbol.upper()
    currency_map = {
        "USD": ["nfp", "fomc", "fed", "cpi", "gdp", "ism", "jobless", "non-farm", "powell"],
        "EUR": ["ecb", "lagarde", "eurozone", "euro"],
        "GBP": ["boe", "uk cpi", "uk gdp", "uk pmi", "united kingdom"],
        "JPY": ["boj", "japan", "boj governor"],
        "AUD": ["rba", "australia"],
        "CAD": ["boc", "canada", "bank of canada"],
        "XAU": ["fomc", "fed", "cpi", "inflation"],  # Gold affected by USD events
    }

    # Find relevant currencies from symbol
    relevant_keywords = []
    for currency, keywords in currency_map.items():
        if currency in symbol_upper:
            relevant_keywords.extend(keywords)

    for ev in events:
        if ev.get("minutes_away", 999) > buffer_minutes:
            continue
        if ev.get("impact") != "HIGH":
            continue

        # If no symbol given, any HIGH event triggers
        if not relevant_keywords:
            return True, ev["event"]

        event_lower = ev["event"].lower()
        if any(kw in event_lower for kw in relevant_keywords):
            return True, ev["event"]

    return False, ""


# ── Market Pulse (combined) ───────────────────────────────────────────────────
def get_market_pulse() -> dict:
    """
    Returns a combined market intelligence snapshot.
    Called by bridge_server.py /market_intelligence endpoint.
    """
    fg = get_fear_greed()
    next_event = get_next_high_impact_event()

    # Interpret Fear & Greed for trading bias
    score = fg.get("score", 50)
    if score <= 25:
        macro_bias = "STRONG_BUY"      # Extreme Fear = buy opportunity
        macro_note = "Extreme Fear — contrarian BUY signal"
    elif score <= 40:
        macro_bias = "BUY"
        macro_note = "Fear zone — lean long"
    elif score <= 60:
        macro_bias = "NEUTRAL"
        macro_note = "Greed neutral zone"
    elif score <= 75:
        macro_bias = "SELL"
        macro_note = "Greed zone — lean short"
    else:
        macro_bias = "STRONG_SELL"     # Extreme Greed = sell opportunity
        macro_note = "Extreme Greed — contrarian SELL signal"

    return {
        "fear_greed": fg,
        "macro_bias": macro_bias,
        "macro_note": macro_note,
        "next_high_impact_event": next_event,
        "timestamp": datetime.now().isoformat(),
    }


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== FEAR & GREED ===")
    fg = get_fear_greed()
    print(json.dumps(fg, indent=2))

    print("\n=== UPCOMING EVENTS ===")
    events = get_upcoming_events()
    print(json.dumps(events[:5], indent=2))

    print("\n=== MARKET PULSE ===")
    pulse = get_market_pulse()
    print(json.dumps(pulse, indent=2))
