"""
api_intelligence.py — Spidy AI API Intelligence Hub
Integrates 10 premium financial & news APIs with smart caching,
rate-limit management, fallback chains, and unified sentiment scoring.

APIs Integrated:
  Financial: Alpha Vantage, Finnhub, Twelve Data, FMP, MarketStack, Massive
  News:      NewsAPI.org, GNews, NewsData.io, WorldNewsAPI
"""

import os
import time
import json
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Optional

# Load env (support both project root and Shared_Data configs locations)
try:
    from dotenv import load_dotenv
    _env_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Shared_Data/configs/.env")),
    ]
    for _p in _env_paths:
        if os.path.exists(_p):
            load_dotenv(dotenv_path=_p)
            break
except Exception:
    pass

# ── Sentiment Keyword Weights (shared) ────────────────────────────────────────
_POSITIVE = {
    "surges": 3, "soars": 3, "skyrockets": 3, "record high": 3, "breakout": 3,
    "massive rally": 3, "blowout": 3, "crushes estimates": 3,
    "rally": 2, "jumps": 2, "gains": 2, "bullish": 2, "optimism": 2,
    "strong growth": 2, "beats estimates": 2, "upgrades": 2, "outperforms": 2,
    "recovery": 2, "rebound": 2, "rate cut": 2,
    "rises": 1, "up": 1, "high": 1, "positive": 1, "increase": 1,
    "growth": 1, "steady": 1, "confidence": 1, "eases": 1,
}
_NEGATIVE = {
    "crashes": 3, "collapses": 3, "plummets": 3, "recession": 3, "crisis": 3,
    "default": 3, "catastrophic": 3, "massive drop": 3, "black swan": 3,
    "drops": 2, "falls": 2, "plunge": 2, "bearish": 2, "fear": 2,
    "sells off": 2, "misses estimates": 2, "downgrades": 2, "slowdown": 2,
    "tariff": 2, "sanction": 2, "rate hike": 2, "inflation surge": 2,
    "decline": 1, "low": 1, "weak": 1, "concern": 1, "uncertainty": 1,
    "volatile": 1, "risk": 1, "caution": 1, "pressure": 1,
}

# ── Source Credibility Weights ─────────────────────────────────────────────────
SOURCE_WEIGHTS = {
    # News providers
    "finnhub":       1.5,   # Real-time financial news
    "newsapi":       1.2,
    "worldnews":     1.1,
    "newsdata":      1.0,
    "gnews":         1.0,
    "massive":       0.9,
    # RSS fallbacks
    "reuters":       1.3,
    "yahoo finance": 1.0,
    "marketwatch":   1.0,
    "fxempire":      0.9,
    "investing.com": 0.9,
}

_lock = threading.Lock()


def _score_headline(title: str) -> tuple:
    """Returns (raw_score, sentiment_label) for a headline."""
    lower = title.lower()
    score = 0.0
    for kw, w in _POSITIVE.items():
        if kw in lower:
            score += w
    for kw, w in _NEGATIVE.items():
        if kw in lower:
            score -= w
    if score >= 2:
        label = "positive"
    elif score <= -2:
        label = "negative"
    elif score > 0:
        label = "slightly_positive"
    elif score < 0:
        label = "slightly_negative"
    else:
        label = "neutral"
    return round(score, 2), label


def _impact(score: float) -> str:
    a = abs(score)
    if a >= 4:
        return "HIGH"
    elif a >= 2:
        return "MEDIUM"
    return "LOW"


# ══════════════════════════════════════════════════════════════════════════════
#  CACHE MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class _Cache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if entry and time.time() < entry["expires"]:
                return entry["data"]
        return None

    def set(self, key: str, data, ttl: int):
        with self._lock:
            self._store[key] = {"data": data, "expires": time.time() + ttl}

    def clear(self, key: str):
        with self._lock:
            self._store.pop(key, None)


_cache = _Cache()


# ══════════════════════════════════════════════════════════════════════════════
#  HTTP HELPER
# ══════════════════════════════════════════════════════════════════════════════
def _get(url: str, params: dict = None, headers: dict = None, timeout: int = 8):
    """Safe HTTP GET returning parsed JSON or None."""
    try:
        import requests
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[APIHub] GET {url} → HTTP {resp.status_code}")
    except Exception as e:
        print(f"[APIHub] GET error {url[:60]}: {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  FINANCIAL DATA PROVIDERS
# ══════════════════════════════════════════════════════════════════════════════

class _FinnhubProvider:
    """
    Finnhub: Real-time quotes, company news, market news.
    Free: 60 req/min. TTL: 60s for quotes, 120s for news.
    """
    BASE = "https://finnhub.io/api/v1"

    def __init__(self):
        self.key = os.getenv("FINNHUB_API_KEY", "")

    def _h(self):
        return {"X-Finnhub-Token": self.key}

    def get_quote(self, symbol: str) -> Optional[dict]:
        if not self.key:
            return None
        ck = f"finnhub_quote_{symbol}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        # Finnhub uses different symbol formats for forex: OANDA:EUR_USD
        fh_sym = self._convert_symbol(symbol)
        data = _get(f"{self.BASE}/quote", params={"symbol": fh_sym}, headers=self._h())
        if data and "c" in data:
            result = {
                "symbol": symbol,
                "price": data.get("c"),
                "open": data.get("o"),
                "high": data.get("h"),
                "low": data.get("l"),
                "prev_close": data.get("pc"),
                "change_pct": round(((data["c"] - data["pc"]) / data["pc"]) * 100, 4) if data.get("pc") else 0,
                "source": "finnhub",
                "updated": datetime.now().isoformat(),
            }
            _cache.set(ck, result, ttl=60)
            return result
        return None

    def get_market_news(self, category: str = "forex") -> list:
        if not self.key:
            return []
        ck = f"finnhub_news_{category}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/news", params={"category": category}, headers=self._h())
        results = []
        if isinstance(data, list):
            for item in data[:15]:
                title = item.get("headline", "")
                if not title:
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * SOURCE_WEIGHTS.get("finnhub", 1.5), 2)
                results.append({
                    "title": title,
                    "summary": item.get("summary", "")[:200],
                    "url": item.get("url", ""),
                    "source": "Finnhub",
                    "source_key": "finnhub",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "published_at": datetime.fromtimestamp(item.get("datetime", 0)).isoformat() if item.get("datetime") else "",
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=120)
        return results

    def get_company_news(self, symbol: str) -> list:
        if not self.key:
            return []
        ck = f"finnhub_cnews_{symbol}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        data = _get(
            f"{self.BASE}/company-news",
            params={"symbol": symbol, "from": week_ago, "to": today},
            headers=self._h()
        )
        results = []
        if isinstance(data, list):
            for item in data[:10]:
                title = item.get("headline", "")
                if not title:
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * 1.5, 2)
                results.append({
                    "title": title,
                    "summary": item.get("summary", "")[:200],
                    "url": item.get("url", ""),
                    "source": "Finnhub",
                    "source_key": "finnhub",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=300)
        return results

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        """Convert MT5 symbol to Finnhub format."""
        mapping = {
            "EURUSD": "OANDA:EUR_USD",
            "GBPUSD": "OANDA:GBP_USD",
            "USDJPY": "OANDA:USD_JPY",
            "AUDUSD": "OANDA:AUD_USD",
            "USDCAD": "OANDA:USD_CAD",
            "XAUUSD": "OANDA:XAU_USD",
            "BTCUSD": "BINANCE:BTCUSDT",
            "ETHUSD": "BINANCE:ETHUSDT",
        }
        return mapping.get(symbol.upper(), symbol)

    def get_sentiment(self, symbol: str) -> Optional[dict]:
        """Get Finnhub's own news sentiment for a stock symbol."""
        if not self.key:
            return None
        ck = f"finnhub_sentiment_{symbol}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/news-sentiment", params={"symbol": symbol}, headers=self._h())
        if data:
            result = {
                "symbol": symbol,
                "buzz_articles": data.get("buzz", {}).get("articlesInLastWeek", 0),
                "weekly_average": data.get("buzz", {}).get("weeklyAverage", 0),
                "company_score": data.get("companyNewsScore", 0),
                "sector_score": data.get("sectorAverageBullishPercent", 0),
                "source": "finnhub",
            }
            _cache.set(ck, result, ttl=3600)
            return result
        return None


class _TwelveDataProvider:
    """
    Twelve Data: OHLCV, technical indicators, forex, crypto.
    Free: 800 req/day. TTL: 120s.
    """
    BASE = "https://api.twelvedata.com"

    def __init__(self):
        self.key = os.getenv("TWELVE_DATA_API_KEY", "")

    def get_quote(self, symbol: str) -> Optional[dict]:
        if not self.key:
            return None
        ck = f"twelve_quote_{symbol}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/quote", params={"symbol": symbol, "apikey": self.key})
        if data and "close" in data:
            result = {
                "symbol": symbol,
                "price": float(data.get("close", 0)),
                "open": float(data.get("open", 0)),
                "high": float(data.get("high", 0)),
                "low": float(data.get("low", 0)),
                "prev_close": float(data.get("previous_close", 0)),
                "change_pct": float(data.get("percent_change", 0)),
                "volume": data.get("volume"),
                "source": "twelve_data",
                "updated": datetime.now().isoformat(),
            }
            _cache.set(ck, result, ttl=120)
            return result
        return None

    def get_rsi(self, symbol: str, interval: str = "1min", period: int = 14) -> Optional[float]:
        """Fetch RSI from Twelve Data."""
        if not self.key:
            return None
        ck = f"twelve_rsi_{symbol}_{interval}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(
            f"{self.BASE}/rsi",
            params={"symbol": symbol, "interval": interval, "time_period": period, "apikey": self.key}
        )
        if data and "values" in data and data["values"]:
            rsi = float(data["values"][0].get("rsi", 50))
            _cache.set(ck, rsi, ttl=120)
            return rsi
        return None

    def get_macd(self, symbol: str, interval: str = "1min") -> Optional[dict]:
        """Fetch MACD from Twelve Data."""
        if not self.key:
            return None
        ck = f"twelve_macd_{symbol}_{interval}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(
            f"{self.BASE}/macd",
            params={"symbol": symbol, "interval": interval, "apikey": self.key}
        )
        if data and "values" in data and data["values"]:
            v = data["values"][0]
            result = {
                "macd": float(v.get("macd", 0)),
                "signal": float(v.get("macd_signal", 0)),
                "histogram": float(v.get("macd_hist", 0)),
            }
            _cache.set(ck, result, ttl=120)
            return result
        return None

    def get_time_series(self, symbol: str, interval: str = "1min", outputsize: int = 50) -> Optional[list]:
        """Fetch OHLCV time series."""
        if not self.key:
            return None
        ck = f"twelve_ts_{symbol}_{interval}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(
            f"{self.BASE}/time_series",
            params={"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": self.key}
        )
        if data and "values" in data:
            _cache.set(ck, data["values"], ttl=120)
            return data["values"]
        return None


class _AlphaVantageProvider:
    """
    Alpha Vantage: Forex, Stocks, Crypto, Technical Indicators.
    Free: 25 req/day — used sparingly for RSI/MACD only.
    TTL: 300s.
    """
    BASE = "https://www.alphavantage.co/query"

    def __init__(self):
        self.key = os.getenv("ALPHA_VANTAGE_API_KEY", "")

    def get_rsi(self, symbol: str, interval: str = "5min", period: int = 14) -> Optional[float]:
        if not self.key:
            return None
        ck = f"av_rsi_{symbol}_{interval}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        # Convert from MT5 format: EURUSD → EUR / USD
        from_sym = symbol[:3] if len(symbol) == 6 else symbol
        to_sym = symbol[3:] if len(symbol) == 6 else "USD"
        data = _get(self.BASE, params={
            "function": "RSI",
            "symbol": f"{from_sym}{to_sym}",
            "interval": interval,
            "time_period": period,
            "series_type": "close",
            "apikey": self.key,
        })
        if data:
            ts_data = data.get("Technical Analysis: RSI", {})
            if ts_data:
                latest_key = sorted(ts_data.keys(), reverse=True)[0]
                rsi = float(ts_data[latest_key].get("RSI", 50))
                _cache.set(ck, rsi, ttl=300)
                return rsi
        return None

    def get_forex_rate(self, from_sym: str, to_sym: str) -> Optional[dict]:
        if not self.key:
            return None
        ck = f"av_forex_{from_sym}{to_sym}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(self.BASE, params={
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_sym,
            "to_currency": to_sym,
            "apikey": self.key,
        })
        if data:
            info = data.get("Realtime Currency Exchange Rate", {})
            if info:
                result = {
                    "from": from_sym,
                    "to": to_sym,
                    "price": float(info.get("5. Exchange Rate", 0)),
                    "last_refreshed": info.get("6. Last Refreshed", ""),
                    "source": "alpha_vantage",
                }
                _cache.set(ck, result, ttl=300)
                return result
        return None

    def get_news_sentiment(self, tickers: str = "FOREX:EUR") -> list:
        """Alpha Vantage News Sentiment endpoint (premium feature, try anyway)."""
        if not self.key:
            return []
        ck = f"av_news_{tickers}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(self.BASE, params={
            "function": "NEWS_SENTIMENT",
            "tickers": tickers,
            "apikey": self.key,
            "limit": 10,
        })
        results = []
        if data and "feed" in data:
            for item in data["feed"][:10]:
                title = item.get("title", "")
                if not title:
                    continue
                score, sentiment = _score_headline(title)
                results.append({
                    "title": title,
                    "summary": item.get("summary", "")[:200],
                    "url": item.get("url", ""),
                    "source": "Alpha Vantage",
                    "source_key": "alphavantage",
                    "sentiment": sentiment,
                    "score": round(score * 1.2, 2),
                    "impact": _impact(score * 1.2),
                    "overall_sentiment": item.get("overall_sentiment_label", ""),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=300)
        return results


class _FMPProvider:
    """
    Financial Modeling Prep: Macro data, economic calendar, market indices.
    Free: 250 req/day. TTL: 300s.
    """
    BASE = "https://financialmodelingprep.com/api/v3"

    def __init__(self):
        self.key = os.getenv("FMP_API_KEY", "")

    def get_economic_calendar(self) -> list:
        if not self.key:
            return []
        ck = "fmp_econ_calendar"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        today = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        data = _get(f"{self.BASE}/economic_calendar",
                    params={"from": today, "to": end, "apikey": self.key})
        results = []
        if isinstance(data, list):
            for ev in data:
                impact = ev.get("impact", "").upper()
                if impact in ("HIGH", "MEDIUM"):
                    results.append({
                        "event": ev.get("event", ""),
                        "date": ev.get("date", ""),
                        "country": ev.get("country", ""),
                        "impact": impact,
                        "actual": ev.get("actual"),
                        "estimate": ev.get("estimate"),
                        "previous": ev.get("previous"),
                        "source": "fmp",
                    })
        _cache.set(ck, results, ttl=300)
        return results

    def get_market_overview(self) -> Optional[dict]:
        if not self.key:
            return None
        ck = "fmp_market_overview"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        # Market hours + gainers/losers
        data = _get(f"{self.BASE}/market-hours", params={"apikey": self.key})
        result = {"market_hours": data or {}, "source": "fmp", "updated": datetime.now().isoformat()}
        _cache.set(ck, result, ttl=300)
        return result

    def get_quote(self, symbol: str) -> Optional[dict]:
        if not self.key:
            return None
        ck = f"fmp_quote_{symbol}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/quote/{symbol}", params={"apikey": self.key})
        if isinstance(data, list) and data:
            q = data[0]
            result = {
                "symbol": symbol,
                "price": q.get("price"),
                "change_pct": q.get("changesPercentage"),
                "volume": q.get("volume"),
                "market_cap": q.get("marketCap"),
                "pe": q.get("pe"),
                "source": "fmp",
                "updated": datetime.now().isoformat(),
            }
            _cache.set(ck, result, ttl=120)
            return result
        return None

    def get_forex_news(self) -> list:
        if not self.key:
            return []
        ck = "fmp_forex_news"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/forex_news", params={"apikey": self.key, "limit": 15})
        results = []
        if isinstance(data, list):
            for item in data:
                title = item.get("title", "")
                if not title:
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * 1.2, 2)
                results.append({
                    "title": title,
                    "url": item.get("url", ""),
                    "source": "FMP",
                    "source_key": "fmp",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "published_at": item.get("publishedDate", ""),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=300)
        return results

    def get_crypto_news(self) -> list:
        if not self.key:
            return []
        ck = "fmp_crypto_news"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/crypto_news", params={"apikey": self.key, "limit": 10})
        results = []
        if isinstance(data, list):
            for item in data:
                title = item.get("title", "")
                if not title:
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * 1.1, 2)
                results.append({
                    "title": title,
                    "url": item.get("url", ""),
                    "source": "FMP",
                    "source_key": "fmp",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "published_at": item.get("publishedDate", ""),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=300)
        return results


class _MarketStackProvider:
    """
    MarketStack: EOD price data + limited intraday.
    Free: 100 req/month — last-resort only.
    TTL: 3600s.
    """
    BASE = "http://api.marketstack.com/v1"

    def __init__(self):
        self.key = os.getenv("MARKETSTACK_API_KEY", "")

    def get_eod(self, symbol: str) -> Optional[dict]:
        if not self.key:
            return None
        ck = f"ms_eod_{symbol}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/eod/latest",
                    params={"access_key": self.key, "symbols": symbol, "limit": 1})
        if data and "data" in data and data["data"]:
            d = data["data"][0]
            result = {
                "symbol": symbol,
                "date": d.get("date"),
                "open": d.get("open"),
                "high": d.get("high"),
                "low": d.get("low"),
                "close": d.get("close"),
                "volume": d.get("volume"),
                "source": "marketstack",
            }
            _cache.set(ck, result, ttl=3600)
            return result
        return None


class _MassiveProvider:
    """
    Massive API: Financial data and news.
    TTL: 300s.
    """
    BASE = "https://api.massive.app/v1"  # Update if different

    def __init__(self):
        self.key = os.getenv("MASSIVE_API_KEY", "")

    def get_news(self, query: str = "forex trading") -> list:
        if not self.key:
            return []
        ck = f"massive_news_{hashlib.md5(query.encode()).hexdigest()}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        # Try as generic financial news API
        data = _get(
            f"{self.BASE}/search",
            params={"q": query, "apikey": self.key, "limit": 10},
            headers={"Authorization": f"Bearer {self.key}"}
        )
        results = []
        if isinstance(data, dict):
            items = data.get("results", data.get("articles", data.get("items", [])))
            for item in items[:10]:
                title = item.get("title", item.get("headline", ""))
                if not title:
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * SOURCE_WEIGHTS.get("massive", 0.9), 2)
                results.append({
                    "title": title,
                    "url": item.get("url", item.get("link", "")),
                    "source": "Massive",
                    "source_key": "massive",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=300)
        return results


# ══════════════════════════════════════════════════════════════════════════════
#  NEWS PROVIDERS
# ══════════════════════════════════════════════════════════════════════════════

class _NewsAPIProvider:
    """
    NewsAPI.org: Top financial headlines.
    Free: 100 req/day. TTL: 180s.
    """
    BASE = "https://newsapi.org/v2"

    def __init__(self):
        self.key = os.getenv("NEWSAPI_KEY", "")

    def get_headlines(self, query: str = "forex stock market financial") -> list:
        if not self.key:
            return []
        ck = f"newsapi_{hashlib.md5(query.encode()).hexdigest()}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/everything", params={
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 15,
            "apiKey": self.key,
        })
        results = []
        if data and "articles" in data:
            for item in data["articles"]:
                title = item.get("title", "")
                if not title or title.lower() == "[removed]":
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * SOURCE_WEIGHTS.get("newsapi", 1.2), 2)
                results.append({
                    "title": title,
                    "summary": (item.get("description") or "")[:200],
                    "url": item.get("url", ""),
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "source_key": "newsapi",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "published_at": item.get("publishedAt", ""),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=180)
        return results

    def get_top_business(self) -> list:
        if not self.key:
            return []
        ck = "newsapi_top_business"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/top-headlines", params={
            "category": "business",
            "language": "en",
            "pageSize": 10,
            "apiKey": self.key,
        })
        results = []
        if data and "articles" in data:
            for item in data["articles"]:
                title = item.get("title", "")
                if not title or title.lower() == "[removed]":
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * 1.2, 2)
                results.append({
                    "title": title,
                    "summary": (item.get("description") or "")[:200],
                    "url": item.get("url", ""),
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "source_key": "newsapi",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "published_at": item.get("publishedAt", ""),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=180)
        return results


class _GNewsProvider:
    """
    GNews API: Financial news.
    Free: 100 req/day. TTL: 180s.
    """
    BASE = "https://gnews.io/api/v4"

    def __init__(self):
        self.key = os.getenv("GNEWS_API_KEY", "")

    def get_headlines(self, query: str = "forex market finance") -> list:
        if not self.key:
            return []
        ck = f"gnews_{hashlib.md5(query.encode()).hexdigest()}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/search", params={
            "q": query,
            "lang": "en",
            "country": "us",
            "max": 10,
            "apikey": self.key,
        })
        results = []
        if data and "articles" in data:
            for item in data["articles"]:
                title = item.get("title", "")
                if not title:
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * SOURCE_WEIGHTS.get("gnews", 1.0), 2)
                results.append({
                    "title": title,
                    "summary": (item.get("description") or "")[:200],
                    "url": item.get("url", ""),
                    "source": item.get("source", {}).get("name", "GNews"),
                    "source_key": "gnews",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "published_at": item.get("publishedAt", ""),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=180)
        return results

    def get_top_headlines(self, topic: str = "business") -> list:
        if not self.key:
            return []
        ck = f"gnews_top_{topic}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/top-headlines", params={
            "topic": topic,
            "lang": "en",
            "max": 10,
            "apikey": self.key,
        })
        results = []
        if data and "articles" in data:
            for item in data["articles"]:
                title = item.get("title", "")
                if not title:
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * 1.0, 2)
                results.append({
                    "title": title,
                    "summary": (item.get("description") or "")[:200],
                    "url": item.get("url", ""),
                    "source": item.get("source", {}).get("name", "GNews"),
                    "source_key": "gnews",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "published_at": item.get("publishedAt", ""),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=180)
        return results


class _NewsDataProvider:
    """
    NewsData.io: Financial and global news.
    Free: 200 req/day. TTL: 180s.
    """
    BASE = "https://newsdata.io/api/1"

    def __init__(self):
        self.key = os.getenv("NEWSDATA_API_KEY", "")

    def get_headlines(self, query: str = "forex trading market") -> list:
        if not self.key:
            return []
        ck = f"newsdata_{hashlib.md5(query.encode()).hexdigest()}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/news", params={
            "apikey": self.key,
            "q": query,
            "language": "en",
            "category": "business",
        })
        results = []
        if data and "results" in data:
            for item in data["results"][:12]:
                title = item.get("title", "")
                if not title:
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * SOURCE_WEIGHTS.get("newsdata", 1.0), 2)
                results.append({
                    "title": title,
                    "summary": (item.get("description") or "")[:200],
                    "url": item.get("link", ""),
                    "source": item.get("source_id", "NewsData.io"),
                    "source_key": "newsdata",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "published_at": item.get("pubDate", ""),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=180)
        return results


class _WorldNewsProvider:
    """
    World News API: Global financial news.
    Free: 500 req/day. TTL: 180s.
    """
    BASE = "https://api.worldnewsapi.com"

    def __init__(self):
        self.key = os.getenv("WORLDNEWS_API_KEY", "")

    def get_headlines(self, query: str = "forex stock market financial trading") -> list:
        if not self.key:
            return []
        ck = f"worldnews_{hashlib.md5(query.encode()).hexdigest()}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached
        data = _get(f"{self.BASE}/search-news", params={
            "api-key": self.key,
            "text": query,
            "language": "en",
            "number": 12,
            "sort": "publish-time",
            "sort-direction": "DESC",
        })
        results = []
        if data and "news" in data:
            for item in data["news"]:
                title = item.get("title", "")
                if not title:
                    continue
                score, sentiment = _score_headline(title)
                weighted = round(score * SOURCE_WEIGHTS.get("worldnews", 1.1), 2)
                results.append({
                    "title": title,
                    "summary": (item.get("summary") or item.get("text", ""))[:200],
                    "url": item.get("url", ""),
                    "source": item.get("author", "WorldNewsAPI"),
                    "source_key": "worldnews",
                    "sentiment": sentiment,
                    "score": weighted,
                    "impact": _impact(weighted),
                    "published_at": item.get("publish_date", ""),
                    "fetched_at": datetime.now().isoformat(),
                })
        _cache.set(ck, results, ttl=180)
        return results


# ══════════════════════════════════════════════════════════════════════════════
#  API INTELLIGENCE HUB  (Main Interface)
# ══════════════════════════════════════════════════════════════════════════════

class APIIntelligenceHub:
    """
    Unified entry point for all financial and news API data.
    Use this class from news_fetcher.py, market_intelligence.py, and bridge_server.py.
    """

    def __init__(self):
        # Financial providers
        self.finnhub = _FinnhubProvider()
        self.twelve = _TwelveDataProvider()
        self.alpha = _AlphaVantageProvider()
        self.fmp = _FMPProvider()
        self.marketstack = _MarketStackProvider()
        self.massive = _MassiveProvider()

        # News providers
        self.newsapi = _NewsAPIProvider()
        self.gnews = _GNewsProvider()
        self.newsdata = _NewsDataProvider()
        self.worldnews = _WorldNewsProvider()

    # ── News Aggregation ──────────────────────────────────────────────────────

    def get_all_news(self, max_per_source: int = 8) -> list:
        """
        Fetches news from ALL API sources concurrently and deduplicates by title hash.
        Returns sorted list of headlines (most impactful first).
        """
        ck = "hub_all_news"
        cached = _cache.get(ck)
        if cached is not None:
            return cached

        import concurrent.futures
        all_articles = []
        seen_hashes = set()

        def _fetch_safe(fn, *args):
            try:
                return fn(*args) or []
            except Exception as e:
                print(f"[APIHub] News fetch error ({fn.__name__}): {e}")
                return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(_fetch_safe, self.finnhub.get_market_news, "general"): "finnhub_general",
                pool.submit(_fetch_safe, self.finnhub.get_market_news, "forex"): "finnhub_forex",
                pool.submit(_fetch_safe, self.newsapi.get_headlines, "forex market financial"): "newsapi",
                pool.submit(_fetch_safe, self.newsapi.get_top_business): "newsapi_biz",
                pool.submit(_fetch_safe, self.gnews.get_headlines, "forex trading market"): "gnews",
                pool.submit(_fetch_safe, self.gnews.get_top_headlines, "business"): "gnews_biz",
                pool.submit(_fetch_safe, self.newsdata.get_headlines, "forex trading market"): "newsdata",
                pool.submit(_fetch_safe, self.worldnews.get_headlines): "worldnews",
                pool.submit(_fetch_safe, self.fmp.get_forex_news): "fmp_forex",
                pool.submit(_fetch_safe, self.massive.get_news, "forex market"): "massive",
            }
            for future, name in futures.items():
                try:
                    articles = future.result(timeout=10)
                    for art in articles[:max_per_source]:
                        title = art.get("title", "")
                        h = hashlib.md5(title.lower().strip().encode()).hexdigest()
                        if h not in seen_hashes and title:
                            seen_hashes.add(h)
                            all_articles.append(art)
                except Exception as e:
                    print(f"[APIHub] Worker {name} error: {e}")

        # Sort by absolute impact score
        all_articles.sort(key=lambda x: abs(x.get("score", 0)), reverse=True)

        _cache.set(ck, all_articles, ttl=120)
        return all_articles

    def get_aggregate_news_sentiment(self) -> dict:
        """
        Returns aggregated sentiment from all API sources.
        """
        ck = "hub_agg_sentiment"
        cached = _cache.get(ck)
        if cached is not None:
            return cached

        articles = self.get_all_news()
        if not articles:
            return {"score": 0.0, "label": "NEUTRAL", "bullish": 0, "bearish": 0, "total": 0, "source_count": 0}

        scores = [a["score"] for a in articles if isinstance(a.get("score"), (int, float))]
        if not scores:
            return {"score": 0.0, "label": "NEUTRAL", "bullish": 0, "bearish": 0, "total": 0, "source_count": 0}

        avg = sum(scores) / len(scores)
        bull = sum(1 for s in scores if s > 0)
        bear = sum(1 for s in scores if s < 0)
        sources = len(set(a.get("source_key", "") for a in articles))

        if avg >= 1.5:
            label = "BULLISH"
        elif avg <= -1.5:
            label = "BEARISH"
        elif avg > 0.3:
            label = "SLIGHTLY_BULLISH"
        elif avg < -0.3:
            label = "SLIGHTLY_BEARISH"
        else:
            label = "NEUTRAL"

        result = {
            "score": round(avg, 3),
            "label": label,
            "bullish": bull,
            "bearish": bear,
            "total": len(scores),
            "source_count": sources,
            "top_headlines": [a["title"] for a in articles[:5]],
        }
        _cache.set(ck, result, ttl=120)
        return result

    # ── Quote Aggregation ─────────────────────────────────────────────────────

    def get_best_quote(self, symbol: str) -> dict:
        """
        Returns the best available real-time quote using provider fallback chain:
        Finnhub → Twelve Data → FMP → MarketStack (last resort).
        """
        ck = f"hub_quote_{symbol}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached

        # Provider chain
        for provider_fn in [
            self.finnhub.get_quote,
            self.twelve.get_quote,
            self.fmp.get_quote,
        ]:
            try:
                q = provider_fn(symbol)
                if q and q.get("price"):
                    _cache.set(ck, q, ttl=60)
                    return q
            except Exception:
                continue

        # Last resort: MarketStack EOD
        try:
            eod = self.marketstack.get_eod(symbol)
            if eod:
                result = {
                    "symbol": symbol,
                    "price": eod.get("close"),
                    "source": "marketstack_eod",
                    "note": "EOD data — not real-time",
                }
                _cache.set(ck, result, ttl=3600)
                return result
        except Exception:
            pass

        return {"symbol": symbol, "price": None, "source": "unavailable"}

    def get_multi_source_quotes(self, symbol: str) -> list:
        """
        Returns quotes from ALL financial data providers for comparison.
        """
        results = []
        for name, fn in [
            ("Finnhub", self.finnhub.get_quote),
            ("TwelveData", self.twelve.get_quote),
            ("FMP", self.fmp.get_quote),
        ]:
            try:
                q = fn(symbol)
                if q:
                    q["provider"] = name
                    results.append(q)
            except Exception:
                pass
        return results

    # ── Technical Indicators ──────────────────────────────────────────────────

    def get_rsi(self, symbol: str, interval: str = "1min") -> Optional[float]:
        """
        Fetches RSI with fallback: Twelve Data → Alpha Vantage.
        """
        ck = f"hub_rsi_{symbol}_{interval}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached

        # Try Twelve Data first (800 req/day)
        try:
            rsi = self.twelve.get_rsi(symbol, interval)
            if rsi is not None:
                _cache.set(ck, rsi, ttl=120)
                return rsi
        except Exception:
            pass

        # Fallback: Alpha Vantage (25 req/day — conserve)
        try:
            rsi = self.alpha.get_rsi(symbol)
            if rsi is not None:
                _cache.set(ck, rsi, ttl=300)
                return rsi
        except Exception:
            pass

        return None

    def get_macd(self, symbol: str, interval: str = "1min") -> Optional[dict]:
        """Fetches MACD from Twelve Data."""
        return self.twelve.get_macd(symbol, interval)

    def get_technical_snapshot(self, symbol: str) -> dict:
        """
        Returns a combined technical snapshot: RSI + MACD + Quote.
        """
        ck = f"hub_tech_{symbol}"
        cached = _cache.get(ck)
        if cached is not None:
            return cached

        quote = self.get_best_quote(symbol)
        rsi = self.get_rsi(symbol)
        macd = self.get_macd(symbol)

        # Determine signal bias from RSI
        rsi_signal = "NEUTRAL"
        if rsi is not None:
            if rsi >= 70:
                rsi_signal = "OVERBOUGHT"
            elif rsi <= 30:
                rsi_signal = "OVERSOLD"
            elif rsi > 55:
                rsi_signal = "BULLISH"
            elif rsi < 45:
                rsi_signal = "BEARISH"

        # Determine MACD bias
        macd_signal = "NEUTRAL"
        if macd:
            if macd["histogram"] > 0:
                macd_signal = "BULLISH"
            elif macd["histogram"] < 0:
                macd_signal = "BEARISH"

        result = {
            "symbol": symbol,
            "quote": quote,
            "rsi": rsi,
            "rsi_signal": rsi_signal,
            "macd": macd,
            "macd_signal": macd_signal,
            "updated": datetime.now().isoformat(),
        }
        _cache.set(ck, result, ttl=60)
        return result

    # ── Economic Calendar ─────────────────────────────────────────────────────

    def get_economic_calendar(self) -> list:
        """Returns upcoming economic events from FMP."""
        return self.fmp.get_economic_calendar()

    # ── API Health Check ──────────────────────────────────────────────────────

    def get_api_health(self) -> dict:
        """
        Checks which API keys are configured and returns status.
        """
        def _check(env_var: str) -> str:
            v = os.getenv(env_var, "")
            return "configured" if v else "missing"

        return {
            "financial": {
                "alpha_vantage": _check("ALPHA_VANTAGE_API_KEY"),
                "finnhub": _check("FINNHUB_API_KEY"),
                "twelve_data": _check("TWELVE_DATA_API_KEY"),
                "fmp": _check("FMP_API_KEY"),
                "marketstack": _check("MARKETSTACK_API_KEY"),
                "massive": _check("MASSIVE_API_KEY"),
            },
            "news": {
                "newsapi": _check("NEWSAPI_KEY"),
                "gnews": _check("GNEWS_API_KEY"),
                "newsdata": _check("NEWSDATA_API_KEY"),
                "worldnews": _check("WORLDNEWS_API_KEY"),
            },
            "checked_at": datetime.now().isoformat(),
        }

    def get_market_context_for_ai(self, symbol: str = "EURUSD") -> str:
        """
        Returns a rich natural-language market context string
        suitable for injection into an LLM prompt.
        """
        lines = []

        # News sentiment
        agg = self.get_aggregate_news_sentiment()
        lines.append(f"[MARKET SENTIMENT] Score: {agg['score']:.2f} | Bias: {agg['label']}")
        lines.append(f"  Bullish articles: {agg['bullish']} | Bearish: {agg['bearish']} | Sources: {agg['source_count']}")
        if agg.get("top_headlines"):
            lines.append("  Top Headlines:")
            for h in agg["top_headlines"][:3]:
                lines.append(f"   - {h}")

        # Technical snapshot
        tech = self.get_technical_snapshot(symbol)
        q = tech.get("quote", {})
        if q.get("price"):
            lines.append(f"\n[{symbol} QUOTE] Price: {q['price']} | Change: {q.get('change_pct', 'N/A')}% | Source: {q.get('source', 'N/A')}")
        if tech.get("rsi") is not None:
            lines.append(f"  RSI({symbol}): {tech['rsi']:.1f} → {tech['rsi_signal']}")
        if tech.get("macd"):
            m = tech["macd"]
            lines.append(f"  MACD: {m['macd']:.5f} | Signal: {m['signal']:.5f} | Hist: {m['histogram']:.5f} → {tech['macd_signal']}")

        # Upcoming economic events
        try:
            events = self.get_economic_calendar()
            high_events = [e for e in events if e.get("impact") == "HIGH"][:3]
            if high_events:
                lines.append("\n[UPCOMING HIGH-IMPACT EVENTS]")
                for ev in high_events:
                    lines.append(f"  - {ev['event']} ({ev['country']}) on {ev['date']}")
        except Exception:
            pass

        return "\n".join(lines)


# ── Singleton Instance ────────────────────────────────────────────────────────
_hub_instance: Optional[APIIntelligenceHub] = None
_hub_lock = threading.Lock()


def get_hub() -> APIIntelligenceHub:
    """Returns the singleton APIIntelligenceHub instance."""
    global _hub_instance
    if _hub_instance is None:
        with _hub_lock:
            if _hub_instance is None:
                _hub_instance = APIIntelligenceHub()
    return _hub_instance


# ── Standalone Test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    print("\n" + "=" * 60)
    print("  Spidy API Intelligence Hub — Self Test")
    print("=" * 60)

    hub = get_hub()

    print("\n📡 API Health Check:")
    health = hub.get_api_health()
    for category, apis in health.items():
        if isinstance(apis, dict):
            print(f"  {category.upper()}:")
            for api, status in apis.items():
                icon = "✅" if status == "configured" else "❌"
                print(f"    {icon} {api}: {status}")

    print("\n📰 Fetching News from All Sources...")
    news = hub.get_all_news(max_per_source=3)
    print(f"  Total articles: {len(news)}")
    for art in news[:5]:
        print(f"  [{art['source_key'].upper()}] {art['title'][:80]} → {art['sentiment']}")

    print("\n📊 Aggregate Sentiment:")
    agg = hub.get_aggregate_news_sentiment()
    print(json.dumps(agg, indent=2))

    print("\n💹 Technical Snapshot (EURUSD):")
    snap = hub.get_technical_snapshot("EUR/USD")
    print(json.dumps(snap, indent=2, default=str))

    print("\n🤖 AI Context String:")
    ctx = hub.get_market_context_for_ai("EUR/USD")
    print(ctx)

    print("\n" + "=" * 60)
    print("  Test Complete!")
    print("=" * 60)
