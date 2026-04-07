"""
market_intelligence.py — Spidy AI Market Intelligence Module
Gathers live macro signals enriched by 10 premium APIs:
  - Fear & Greed Index (CNN + Alternative.me)
  - Economic Calendar (FMP primary, ForexFactory RSS fallback)
  - Real-Time Quotes (Finnhub / Twelve Data / FMP chain)
  - Technical Indicators (RSI, MACD via Twelve Data / Alpha Vantage)
  - Upcoming Events blocking filter
"""

import json
import time
import re
import os
import sys
from datetime import datetime, timedelta

# ── API Intelligence Hub ──────────────────────────────────────────────────────
_hub = None
_hub_enabled = True
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from api_intelligence import get_hub
    _hub = get_hub()
except Exception as e:
    print(f"[MarketIntel] API Hub unavailable: {e}")
    _hub_enabled = False

# ── Cache ─────────────────────────────────────────────────────────────────────
_cache = {}
_cache_ttl = {
    "fear_greed": 600,        # 10 min (CNN updates ~hourly)
    "calendar": 300,           # 5 min (upcoming events)
    "real_quote": 60,          # 1 min (real-time prices)
    "technical": 120,          # 2 min (RSI/MACD)
    "api_calendar": 300,       # 5 min (FMP calendar)
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
HIGH_IMPACT_PATTERNS = [
    "nfp", "non-farm", "fomc", "fed decision", "interest rate decision",
    "cpi", "inflation", "gdp", "unemployment", "jobless claims",
    "pmi", "ism", "retail sales", "ecb", "boe", "rba", "boj",
    "fed chair", "powell", "lagarde", "central bank",
    "trade balance", "current account", "housing starts",
]


def get_upcoming_events(hours_ahead: int = 4) -> list:
    """
    Fetches upcoming high-impact economic events.
    Primary: FMP API (structured data with impact labels).
    Fallback: ForexFactory RSS feed.
    Returns list of { event, time_utc, impact, minutes_away }
    """
    ck = "api_calendar"
    if _is_cache_valid(ck):
        return _cache[ck]["data"]

    events = []

    # PRIMARY: FMP Economic Calendar
    if _hub_enabled and _hub:
        try:
            fmp_events = _hub.get_economic_calendar()
            now = datetime.utcnow()
            for ev in fmp_events:
                try:
                    ev_date_str = ev.get("date", "")
                    if not ev_date_str:
                        continue
                    ev_dt = datetime.strptime(ev_date_str[:19], "%Y-%m-%d %H:%M:%S")
                    if ev_dt < now or ev_dt > now + timedelta(hours=hours_ahead):
                        continue
                    minutes_away = int((ev_dt - now).total_seconds() / 60)
                    events.append({
                        "event": ev.get("event", ""),
                        "time_utc": ev_dt.strftime("%Y-%m-%d %H:%M UTC"),
                        "impact": ev.get("impact", "MEDIUM"),
                        "minutes_away": minutes_away,
                        "country": ev.get("country", ""),
                        "actual": ev.get("actual"),
                        "estimate": ev.get("estimate"),
                        "previous": ev.get("previous"),
                        "source": "fmp",
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[MarketIntel] FMP Calendar error: {e}")

    # FALLBACK: ForexFactory RSS
    if not events:
        try:
            import feedparser
            feed = feedparser.parse("https://nfs.faireconomy.media/ff_calendar_thisweek.xml")
            now = datetime.utcnow()
            cutoff = now + timedelta(hours=hours_ahead)
            for entry in feed.entries:
                try:
                    title = entry.get("title", "")
                    published = entry.get("published_parsed", None)
                    if not published:
                        continue
                    event_dt = datetime(*published[:6])
                    if event_dt < now or event_dt > cutoff:
                        continue
                    minutes_away = int((event_dt - now).total_seconds() / 60)
                    title_lower = title.lower()
                    is_high = any(p in title_lower for p in HIGH_IMPACT_PATTERNS)
                    impact = "HIGH" if is_high else "MEDIUM"
                    events.append({
                        "event": title,
                        "time_utc": event_dt.strftime("%Y-%m-%d %H:%M UTC"),
                        "impact": impact,
                        "minutes_away": minutes_away,
                        "country": "",
                        "source": "forexfactory_rss",
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[MarketIntel] Calendar RSS fallback failed: {e}")

    events.sort(key=lambda x: x.get("minutes_away", 9999))
    _cache[ck] = {"data": events, "ts": time.time()}
    return events


def get_next_high_impact_event() -> dict:
    """Returns the next HIGH-impact event within 4 hours, or {}."""
    for ev in get_upcoming_events(hours_ahead=4):
        if ev.get("impact") == "HIGH":
            return ev
    return {}


def is_near_high_impact_event(symbol: str = "", buffer_minutes: int = 5) -> tuple:
    """
    Returns (True, event_name) if a HIGH-impact event is within buffer_minutes.
    Used in validate_entry() to hard-block new trades before major news.
    """
    events = get_upcoming_events(hours_ahead=1)

    currency_map = {
        "USD": ["nfp", "fomc", "fed", "cpi", "gdp", "ism", "jobless", "non-farm", "powell"],
        "EUR": ["ecb", "lagarde", "eurozone", "euro"],
        "GBP": ["boe", "uk cpi", "uk gdp", "uk pmi", "united kingdom"],
        "JPY": ["boj", "japan", "boj governor"],
        "AUD": ["rba", "australia"],
        "CAD": ["boc", "canada", "bank of canada"],
        "XAU": ["fomc", "fed", "cpi", "inflation"],
    }

    symbol_upper = symbol.upper()
    relevant_keywords = []
    for currency, keywords in currency_map.items():
        if currency in symbol_upper:
            relevant_keywords.extend(keywords)

    for ev in events:
        if ev.get("minutes_away", 999) > buffer_minutes:
            continue
        if ev.get("impact") != "HIGH":
            continue
        if not relevant_keywords:
            return True, ev["event"]
        event_lower = ev["event"].lower()
        if any(kw in event_lower for kw in relevant_keywords):
            return True, ev["event"]

    return False, ""


# ── Real-Time Quotes ──────────────────────────────────────────────────────────
def get_real_time_quote(symbol: str) -> dict:
    """
    Fetches the best available real-time quote for a symbol.
    Uses Finnhub → Twelve Data → FMP chain via API hub.
    Returns: { symbol, price, change_pct, source, updated }
    """
    ck = f"real_quote_{symbol}"
    if _is_cache_valid(ck):
        return _cache[ck]["data"]

    result = {"symbol": symbol, "price": None, "change_pct": None, "source": "unavailable"}

    if _hub_enabled and _hub:
        try:
            q = _hub.get_best_quote(symbol)
            if q and q.get("price"):
                result = q
        except Exception as e:
            print(f"[MarketIntel] Quote fetch error for {symbol}: {e}")

    _cache[ck] = {"data": result, "ts": time.time()}
    return result


# ── Technical Indicators ──────────────────────────────────────────────────────
def get_technical_indicators(symbol: str) -> dict:
    """
    Gets RSI and MACD for a symbol via Twelve Data API (Alpha Vantage fallback).
    Returns: { rsi, rsi_signal, macd, macd_signal }
    """
    ck = f"technical_{symbol}"
    if _is_cache_valid(ck):
        return _cache[ck]["data"]

    result = {"rsi": None, "rsi_signal": "NEUTRAL", "macd": None, "macd_signal": "NEUTRAL"}

    if _hub_enabled and _hub:
        try:
            snap = _hub.get_technical_snapshot(symbol)
            result = {
                "rsi": snap.get("rsi"),
                "rsi_signal": snap.get("rsi_signal", "NEUTRAL"),
                "macd": snap.get("macd"),
                "macd_signal": snap.get("macd_signal", "NEUTRAL"),
            }
        except Exception as e:
            print(f"[MarketIntel] Technical fetch error for {symbol}: {e}")

    _cache[ck] = {"data": result, "ts": time.time()}
    return result


# ── Market Pulse (combined) ───────────────────────────────────────────────────
def get_market_pulse() -> dict:
    """
    Returns a rich combined market intelligence snapshot.
    Called by bridge_server.py /market_intelligence endpoint.
    Now powered by 10 APIs + Fear & Greed + Economic Calendar.
    """
    fg = get_fear_greed()
    next_event = get_next_high_impact_event()

    score = fg.get("score", 50)
    if score <= 25:
        macro_bias = "STRONG_BUY"
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
        macro_bias = "STRONG_SELL"
        macro_note = "Extreme Greed — contrarian SELL signal"

    news_sentiment = None
    eurusd_quote = None
    eurusd_tech = None

    if _hub_enabled and _hub:
        try:
            news_sentiment = _hub.get_aggregate_news_sentiment()
        except Exception:
            pass
        try:
            eurusd_quote = _hub.get_best_quote("EUR/USD")
        except Exception:
            pass
        try:
            eurusd_tech = _hub.get_technical_snapshot("EUR/USD")
        except Exception:
            pass

    # Blend news sentiment into macro bias (only if currently NEUTRAL from F&G)
    if news_sentiment and macro_bias == "NEUTRAL":
        news_label = news_sentiment.get("label", "NEUTRAL")
        news_score = news_sentiment.get("score", 0)
        if news_label == "BULLISH":
            macro_bias = "BUY"
            macro_note += f" | News: {news_label} ({news_score:+.2f})"
        elif news_label == "BEARISH":
            macro_bias = "SELL"
            macro_note += f" | News: {news_label} ({news_score:+.2f})"

    # Build top_headlines list for the frontend (MarketIntelligence.js expects article objects)
    top_headlines = []
    if _hub_enabled and _hub:
        try:
            top_headlines = _hub.get_all_news(max_per_source=3)[:8]
        except Exception:
            pass
    if not top_headlines and news_sentiment:
        # Fallback: wrap title strings from aggregate sentiment if no full articles
        top_headlines = [
            {"title": t, "sentiment": "neutral", "source": "News Hub", "impact": "MEDIUM", "url": ""}
            for t in news_sentiment.get("top_headlines", [])
        ]

    return {
        "fear_greed": fg,
        "macro_bias": macro_bias,
        "macro_note": macro_note,
        "next_high_impact_event": next_event,
        "news_sentiment": news_sentiment,
        "top_headlines": top_headlines,
        "eurusd_quote": eurusd_quote,
        "eurusd_technicals": {
            "rsi": eurusd_tech.get("rsi") if eurusd_tech else None,
            "rsi_signal": eurusd_tech.get("rsi_signal", "NEUTRAL") if eurusd_tech else "NEUTRAL",
            "macd_signal": eurusd_tech.get("macd_signal", "NEUTRAL") if eurusd_tech else "NEUTRAL",
        } if eurusd_tech else None,
        "api_sources_active": 10 if _hub_enabled else 0,
        "timestamp": datetime.now().isoformat(),
    }




# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== FEAR & GREED ===")
    fg = get_fear_greed()
    print(json.dumps(fg, indent=2))

    print("\n=== UPCOMING EVENTS (FMP + ForexFactory) ===")
    events = get_upcoming_events()
    print(json.dumps(events[:5], indent=2))

    print("\n=== REAL-TIME QUOTE (EURUSD) ===")
    q = get_real_time_quote("EUR/USD")
    print(json.dumps(q, indent=2))

    print("\n=== TECHNICAL INDICATORS (EURUSD) ===")
    tech = get_technical_indicators("EUR/USD")
    print(json.dumps(tech, indent=2))

    print("\n=== MARKET PULSE ===")
    pulse = get_market_pulse()
    print(json.dumps(pulse, indent=2, default=str))
