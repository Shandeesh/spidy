"""
agents/researcher.py
=====================
Agent 2 — Researcher

What it does
------------
  Subscribes to MARKET_SNAPSHOT.  On each new snapshot it:
    1. Fetches the 15 most-recent macro headlines via NewsFetcher.
    2. Builds a structured prompt with the headline list + key M5 features.
    3. Sends the prompt to Gemini 2.0 Flash.
    4. Parses the JSON response into a typed Sentiment payload.
    5. Publishes on Topic.SENTIMENT.

  The "hold_off" flag in the sentiment payload is the most critical output —
  it tells RiskManager "there is a known risk event right now, don't trade."
  Examples: FOMC meeting in 90 minutes, NFP release imminent, war escalation.

Publishes
---------
  Topic.SENTIMENT → {
    "symbol":      str,
    "sentiment":   "BULLISH" | "BEARISH" | "NEUTRAL",
    "confidence":  float (0.0 – 1.0),
    "key_reasons": list[str],
    "risk_events": list[str],    # e.g. ["FOMC in 90 min"]
    "hold_off":    bool,         # True = do not trade right now
  }

Safe defaults
-------------
  If Gemini is unavailable or returns unparseable JSON, the agent defaults
  to {"sentiment": "NEUTRAL", "hold_off": True} — the safe side.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from .base_agent import BaseAgent
from .message_bus import AgentMessage, MessageBus, Topic


# ── Gemini prompt ─────────────────────────────────────────────────────────────

_PROMPT = """
You are a professional forex macro analyst specialising in short-term (intraday)
directional sentiment for {symbol}.

Current market state (latest M5 candle features):
{features_json}

Latest macro & news headlines:
{headlines}

Based on these inputs, assess the directional sentiment for {symbol} over the
NEXT 1–4 HOURS.

Rules:
- If there is a major risk event (central bank decision, CPI, NFP, war news,
  regulatory shock) within the next 2 hours, set hold_off to true regardless
  of sentiment.
- Confidence should reflect how strong and unambiguous the signal is (0.0–1.0).
- Keep key_reasons to 2–3 concise bullet points.

Respond with VALID JSON ONLY — no markdown fences, no extra text:
{{
  "sentiment":   "BULLISH" | "BEARISH" | "NEUTRAL",
  "confidence":  <float 0.0–1.0>,
  "key_reasons": ["<reason 1>", "<reason 2>"],
  "risk_events": ["<event if any>"],
  "hold_off":    true | false
}}
"""

# Features to include in the prompt (subset to keep context concise)
_PROMPT_FEATURES = (
    "close", "RSI", "ATR", "EMA_20", "EMA_50",
    "MACD", "ADX", "BB_upper", "BB_lower",
)


class ResearcherAgent(BaseAgent):

    def __init__(self, bus: MessageBus, config: dict[str, Any]) -> None:
        super().__init__("Researcher", bus, config)
        self._inbox:        asyncio.Queue[AgentMessage] | None = None
        self._gemini:       Any = None
        self._news_fetcher: Any = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def setup(self) -> None:
        from google import genai
        from google.genai import types as genai_types
        from AI_Engine.internet_gathering.news_fetcher import NewsFetcher

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "[Researcher] GOOGLE_API_KEY not found in environment."
            )

        # New google-genai SDK (replaces deprecated google.generativeai)
        self._gemini_client = genai.Client(api_key=api_key)
        self._gemini_model  = "gemini-2.0-flash"
        self._genai_types   = genai_types
        # Keep self._gemini as a convenience alias for _call_gemini
        self._gemini = self._gemini_client

        self._news_fetcher = NewsFetcher()
        self._inbox = await self.bus.subscribe(Topic.MARKET_SNAPSHOT)
        self.logger.info("[Researcher] Ready — using Gemini 2.0 Flash (google-genai SDK).")

    # ── Step ──────────────────────────────────────────────────────────────────

    async def step(self) -> None:
        # Wait for the next snapshot from DataEngineer
        msg: AgentMessage | None = await self.receive(self._inbox)
        if msg is None:
            return

        snapshot = msg.payload
        symbol   = snapshot.get("symbol", "EURUSD")

        # Fetch headlines concurrently with anything else we might do
        headlines_raw: list[str] = await asyncio.to_thread(
            self._news_fetcher.get_latest_headlines
        )
        headlines_text = (
            "\n".join(f"- {h}" for h in headlines_raw[:15])
            or "No headlines available at this time."
        )

        # Build the feature snippet (M5 only — most actionable for intraday)
        m5 = snapshot.get("timeframes", {}).get("M5", {})
        features_subset = {
            k: round(m5[k], 5) for k in _PROMPT_FEATURES if k in m5
        }

        prompt = _PROMPT.format(
            symbol=symbol,
            features_json=json.dumps(features_subset, indent=2),
            headlines=headlines_text,
        )

        # Call Gemini in thread (blocking SDK call)
        raw_response = await asyncio.to_thread(self._call_gemini, prompt)

        sentiment = self._parse(raw_response, symbol)
        await self.publish(Topic.SENTIMENT, sentiment)

        self.logger.info(
            "[Researcher] %s → sentiment=%s conf=%.2f hold_off=%s reasons=%s",
            symbol,
            sentiment["sentiment"],
            sentiment["confidence"],
            sentiment["hold_off"],
            sentiment["key_reasons"],
        )

    # ── Gemini call ───────────────────────────────────────────────────────────

    def _call_gemini(self, prompt: str) -> str:
        """Synchronous Gemini call — run via asyncio.to_thread."""
        try:
            response = self._gemini_client.models.generate_content(
                model=self._gemini_model,
                contents=prompt,
                config=self._genai_types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=512,
                ),
            )
            return response.text or ""
        except Exception as exc:
            self.logger.error("[Researcher] Gemini call failed: %s", exc)
            return ""

    # ── Response parsing ──────────────────────────────────────────────────────

    def _parse(self, raw: str, symbol: str) -> dict[str, Any]:
        """
        Parse Gemini's JSON response.  Defaults to safe NEUTRAL/hold_off=True
        if parsing fails for any reason.
        """
        safe_default: dict[str, Any] = {
            "symbol":      symbol,
            "sentiment":   "NEUTRAL",
            "confidence":  0.0,
            "key_reasons": ["Parsing failed — defaulting to neutral"],
            "risk_events": [],
            "hold_off":    True,
        }
        if not raw.strip():
            return safe_default

        try:
            clean = (
                raw.strip()
                   .removeprefix("```json")
                   .removeprefix("```")
                   .removesuffix("```")
                   .strip()
            )
            data = json.loads(clean)
        except (json.JSONDecodeError, ValueError) as exc:
            self.logger.warning(
                "[Researcher] JSON parse error: %s | raw=%r", exc, raw[:200]
            )
            return safe_default

        # Validate and coerce fields
        sentiment = data.get("sentiment", "NEUTRAL").upper()
        if sentiment not in ("BULLISH", "BEARISH", "NEUTRAL"):
            sentiment = "NEUTRAL"

        return {
            "symbol":      symbol,
            "sentiment":   sentiment,
            "confidence":  float(data.get("confidence", 0.0)),
            "key_reasons": list(data.get("key_reasons", [])),
            "risk_events": list(data.get("risk_events", [])),
            "hold_off":    bool(data.get("hold_off", True)),
        }
