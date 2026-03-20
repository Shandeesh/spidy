"""
news_fetcher.py — Spidy AI Multi-Source News Intelligence
Fetches headlines from multiple financial RSS feeds with weighted sentiment scoring.
"""

import json
import time
from datetime import datetime

# ── Weighted Keyword Scoring ──────────────────────────────────────────────────
POSITIVE_KEYWORDS = {
    # High Impact (+3)
    "surges": 3, "soars": 3, "skyrockets": 3, "record high": 3, "breakout": 3,
    "massive rally": 3, "blowout": 3, "crushes estimates": 3,
    # Medium Impact (+2)
    "rally": 2, "jumps": 2, "gains": 2, "bullish": 2, "optimism": 2,
    "strong growth": 2, "beats estimates": 2, "upgrades": 2, "outperforms": 2,
    "recovery": 2, "rebound": 2, "rate cut": 2,
    # Low Impact (+1)
    "rises": 1, "up": 1, "high": 1, "positive": 1, "increase": 1,
    "growth": 1, "steady": 1, "confidence": 1, "eases": 1,
}

NEGATIVE_KEYWORDS = {
    # High Impact (-3)
    "crashes": 3, "collapses": 3, "plummets": 3, "recession": 3, "crisis": 3,
    "default": 3, "catastrophic": 3, "massive drop": 3, "black swan": 3,
    # Medium Impact (-2)
    "drops": 2, "falls": 2, "plunge": 2, "bearish": 2, "fear": 2,
    "sells off": 2, "misses estimates": 2, "downgrades": 2, "slowdown": 2,
    "tariff": 2, "sanction": 2, "rate hike": 2, "inflation surge": 2,
    # Low Impact (-1)
    "decline": 1, "low": 1, "weak": 1, "concern": 1, "uncertainty": 1,
    "volatile": 1, "risk": 1, "caution": 1, "pressure": 1,
}

# ── RSS Sources ───────────────────────────────────────────────────────────────
RSS_SOURCES = [
    {
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/news/rssindex",
        "weight": 1.0,
    },
    {
        "name": "Reuters Business",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "weight": 1.2,  # Reuters is higher quality
    },
    {
        "name": "FX Empire",
        "url": "https://www.fxempire.com/api/v1/en/articles/rss",
        "weight": 1.1,
    },
    {
        "name": "Investing.com",
        "url": "https://www.investing.com/rss/news.rss",
        "weight": 1.0,
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "weight": 1.0,
    },
]


def _score_headline(title: str) -> tuple[float, str]:
    """
    Scores a headline using weighted keyword matching.
    Returns (score, sentiment_label).
    """
    lower = title.lower()
    score = 0.0

    for kw, weight in POSITIVE_KEYWORDS.items():
        if kw in lower:
            score += weight

    for kw, weight in NEGATIVE_KEYWORDS.items():
        if kw in lower:
            score -= weight

    if score >= 2:
        sentiment = "positive"
    elif score <= -2:
        sentiment = "negative"
    elif score > 0:
        sentiment = "slightly_positive"
    elif score < 0:
        sentiment = "slightly_negative"
    else:
        sentiment = "neutral"

    return round(score, 2), sentiment


class NewsFetcher:
    def __init__(self):
        self._cache = []
        self._cache_ts = 0
        self._cache_ttl = 180  # 3 minutes cache

    def get_latest_headlines(self, max_per_source: int = 5) -> list:
        """
        Fetches and scores headlines from multiple financial RSS sources.
        Returns list of { title, sentiment, score, source, impact, url }.
        Caches results for 3 minutes to avoid hammering upstream servers.
        """
        # Return cache if fresh
        if self._cache and (time.time() - self._cache_ts) < self._cache_ttl:
            return self._cache

        headlines = []

        try:
            import feedparser
        except ImportError:
            return [{"title": "System: feedparser not installed (pip install feedparser)",
                     "sentiment": "neutral", "score": 0.0, "source": "System",
                     "impact": "LOW", "url": ""}]

        for source in RSS_SOURCES:
            try:
                feed = feedparser.parse(source["url"])
                entries = feed.entries[:max_per_source]

                for entry in entries:
                    title = getattr(entry, "title", "").strip()
                    url = getattr(entry, "link", "")

                    if not title:
                        continue

                    raw_score, sentiment = _score_headline(title)
                    # Adjust score by source weight
                    weighted_score = round(raw_score * source["weight"], 2)

                    # Determine impact level
                    abs_score = abs(weighted_score)
                    if abs_score >= 4:
                        impact = "HIGH"
                    elif abs_score >= 2:
                        impact = "MEDIUM"
                    else:
                        impact = "LOW"

                    headlines.append({
                        "title": title,
                        "sentiment": sentiment,
                        "score": weighted_score,
                        "source": source["name"],
                        "impact": impact,
                        "url": url,
                        "fetched_at": datetime.now().isoformat(),
                    })

            except Exception as e:
                headlines.append({
                    "title": f"System: {source['name']} unavailable ({str(e)[:60]})",
                    "sentiment": "neutral",
                    "score": 0.0,
                    "source": source["name"],
                    "impact": "LOW",
                    "url": "",
                })

        # Sort by absolute score (most impactful first)
        headlines.sort(key=lambda x: abs(x["score"]), reverse=True)

        # Update cache
        self._cache = headlines
        self._cache_ts = time.time()

        return headlines

    def get_aggregate_sentiment(self) -> dict:
        """
        Returns an aggregate market sentiment score from all headlines.
        Returns: { score: float, label: str, bullish_count: int, bearish_count: int }
        """
        headlines = self.get_latest_headlines()
        if not headlines:
            return {"score": 0.0, "label": "NEUTRAL", "bullish_count": 0, "bearish_count": 0, "total": 0}

        scores = [h["score"] for h in headlines if isinstance(h["score"], (int, float))]
        if not scores:
            return {"score": 0.0, "label": "NEUTRAL", "bullish_count": 0, "bearish_count": 0, "total": 0}

        avg = sum(scores) / len(scores)
        bullish = sum(1 for s in scores if s > 0)
        bearish = sum(1 for s in scores if s < 0)

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

        return {
            "score": round(avg, 3),
            "label": label,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "total": len(scores),
        }

    def get_dxy_status(self) -> dict:
        """
        Fetches the US Dollar Index (DXY) status using yfinance.
        Returns: { price, change_pct, status }
        """
        try:
            import yfinance as yf
            ticker = yf.Ticker("DX-Y.NYB")
            hist = ticker.history(period="1d", interval="1m")

            if hist.empty:
                hist = ticker.history(period="5d")

            if not hist.empty:
                current = hist["Close"].iloc[-1]
                open_price = hist["Open"].iloc[0]
                change = current - open_price
                change_pct = (change / open_price) * 100

                status = "NEUTRAL"
                if change_pct > 0.1:
                    status = "BULLISH"
                elif change_pct < -0.1:
                    status = "BEARISH"

                return {
                    "price": round(current, 3),
                    "change_pct": round(change_pct, 4),
                    "status": status,
                }

        except ImportError:
            pass
        except Exception as e:
            print(f"DXY Fetch Error: {e}")

        return {"price": 0.0, "change_pct": 0.0, "status": "NEUTRAL"}


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    fetcher = NewsFetcher()
    print("\n=== TOP HEADLINES ===")
    headlines = fetcher.get_latest_headlines()
    print(json.dumps(headlines[:10], indent=2))

    print("\n=== AGGREGATE SENTIMENT ===")
    agg = fetcher.get_aggregate_sentiment()
    print(json.dumps(agg, indent=2))

    print("\n=== DXY STATUS ===")
    dxy = fetcher.get_dxy_status()
    print(json.dumps(dxy, indent=2))
