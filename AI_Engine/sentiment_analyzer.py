"""
Phase 2: The "Brain" - Sentiment Analysis Engine
Scrapes financial news and outputs market sentiment score.
"""

import feedparser
import time
from datetime import datetime, timedelta
from textblob import TextBlob
import json
import os
import threading
from collections import deque

class SentimentAnalyzer:
    def __init__(self, update_interval=300):  # 5 minutes default
        self.update_interval = update_interval
        self.sentiment_score = 0.0  # -1 (Bearish) to +1 (Bullish)
        self.recent_headlines = deque(maxlen=50)  # Keep last 50 headlines
        self.running = False
        self._thread = None
        
        # FIX 10: Replaced broken/paywalled feeds (Bloomberg=400, Reuters=404, Investing=bot-blocked)
        # with reliable free RSS sources
        self.news_feeds = [
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",                              # WSJ Markets
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",                       # CNBC Markets
            "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",                   # NYT Business
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",# Yahoo Finance
        ]
        
        # Keyword weights for financial impact
        self.bullish_keywords = [
            'rally', 'surge', 'gains', 'positive', 'optimistic', 'upgrade',
            'growth', 'higher', 'strong', 'buy', 'bullish', 'breakout'
        ]
        
        self.bearish_keywords = [
            'crash', 'plunge', 'losses', 'negative', 'pessimistic', 'downgrade',
            'recession', 'lower', 'weak', 'sell', 'bearish', 'breakdown'
        ]
        
    def start(self):
        """Start the background sentiment monitoring thread."""
        if self.running:
            return
        print("📰 Sentiment Analyzer: Starting...")
        self.running = True
        self._thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop the analyzer."""
        self.running = False
        
    def _fetch_headlines(self):
        """Scrape headlines from RSS feeds."""
        headlines = []
        for feed_url in self.news_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:  # Top 10 from each source
                    title = entry.get('title', '')
                    published = entry.get('published', '')
                    
                    # Only process recent news (last 6 hours)
                    # Note: published parsing is complex, we'll accept all for now
                    headlines.append({
                        'title': title,
                        'source': feed_url,
                        'time': published
                    })
            except Exception as e:
                print(f"Feed Error ({feed_url}): {e}")
                
        return headlines
        
    def _analyze_sentiment(self, text):
        """
        Analyze sentiment of a single text.
        Returns: (-1 to +1) score.
        """
        try:
            # TextBlob basic sentiment
            blob = TextBlob(text.lower())
            polarity = blob.sentiment.polarity  # -1 to +1
            
            # Boost signal with keyword detection
            text_lower = text.lower()
            bull_count = sum(1 for kw in self.bullish_keywords if kw in text_lower)
            bear_count = sum(1 for kw in self.bearish_keywords if kw in text_lower)
            
            # Apply keyword weight (each keyword = 0.1 boost)
            # FIX 11: Clamp keyword_bias to [-1, 1] before averaging to prevent skew
            keyword_bias = max(-1.0, min(1.0, (bull_count - bear_count) * 0.1))
            
            # Combined score (weighted average of TextBlob + keyword)
            final_score = (polarity + keyword_bias) / 2.0
            
            # Clamp to [-1, 1]
            final_score = max(-1.0, min(1.0, final_score))
            
            return final_score
        except Exception as e:
            print(f"Sentiment Analysis Error: {e}")
            return 0.0
            
    def _calculate_market_sentiment(self, headlines):
        """
        Aggregate sentiment from all headlines.
        Returns: Overall market sentiment score.
        """
        if not headlines:
            return 0.0
            
        scores = []
        for h in headlines:
            score = self._analyze_sentiment(h['title'])
            scores.append(score)
            
        # Weighted average (recent news has more weight)
        # For simplicity, we just use mean
        avg_score = sum(scores) / len(scores)
        
        return avg_score
        
    def _analysis_loop(self):
        """Background loop that updates sentiment periodically."""
        print("📰 Sentiment Analyzer: Active.")
        
        while self.running:
            try:
                # 1. Fetch Headlines
                headlines = self._fetch_headlines()
                
                if headlines:
                    # 2. Calculate Sentiment
                    sentiment = self._calculate_market_sentiment(headlines)
                    self.sentiment_score = sentiment
                    
                    # Store headlines for debugging
                    self.recent_headlines.extend(headlines)
                    
                    # 3. Classify
                    if sentiment > 0.2:
                        label = "BULLISH"
                    elif sentiment < -0.2:
                        label = "BEARISH"
                    else:
                        label = "NEUTRAL"
                        
                    print(f"📊 Market Sentiment: {label} (Score: {sentiment:.2f})")
                    
                    # 4. Write to Shared File (for Bridge consumption)
                    self._export_sentiment(sentiment, label)
                else:
                    print("📰 No headlines fetched this cycle.")
                    
            except Exception as e:
                print(f"Sentiment Loop Error: {e}")
                
            # Sleep until next update
            time.sleep(self.update_interval)
            
    def _export_sentiment(self, score, label):
        """
        Export sentiment to a JSON file for trading bridges to consume.
        Format: {"sentiment": "BULLISH", "score": 0.5, "timestamp": 123456}
        """
        try:
            # Write to AI_Engine/sentiment.json
            base_path = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_path, "sentiment.json")
            
            data = {
                "sentiment": label,
                "score": score,
                "timestamp": time.time(),
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Atomic write
            temp_path = file_path + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
                
            os.replace(temp_path, file_path)
            
        except Exception as e:
            print(f"Sentiment Export Error: {e}")
            
    def get_current_sentiment(self):
        """Returns the latest sentiment score and label."""
        if self.sentiment_score > 0.2:
            label = "BULLISH"
        elif self.sentiment_score < -0.2:
            label = "BEARISH"
        else:
            label = "NEUTRAL"
            
        return {
            "score": self.sentiment_score,
            "label": label
        }


# Standalone Execution
if __name__ == "__main__":
    analyzer = SentimentAnalyzer(update_interval=60)  # Every 1 minute for testing
    analyzer.start()
    
    try:
        # Keep running
        while True:
            time.sleep(10)
            current = analyzer.get_current_sentiment()
            print(f"Current Market Sentiment: {current['label']} ({current['score']:.2f})")
    except KeyboardInterrupt:
        print("\nShutting down Sentiment Analyzer...")
        analyzer.stop()
