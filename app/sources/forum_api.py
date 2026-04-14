"""
Forum Market API client.
Fetches real market data from api.forum.market with HMAC auth.
Returns rich signals including 24h momentum for use as fallback when external sources fail.
"""

import hashlib
import hmac
import json
import time
import requests
from app.config import FORUM_API_KEY, FORUM_API_SECRET, FORUM_BASE_URL, TICKER_MAP_FILE

# ── Cache ─────────────────────────────────────────────────
_markets_cache: list[dict] | None = None
_markets_cache_ts: float = 0
_market_cache: dict[str, tuple[float, dict]] = {}  # ticker → (ts, data)
CACHE_TTL = 60


def _sign(method: str, path: str) -> dict:
    ts = str(int(time.time()))
    message = ts + method.upper() + path
    sig = hmac.new(
        FORUM_API_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return {
        "FORUM-ACCESS-KEY": FORUM_API_KEY,
        "FORUM-ACCESS-SIGN": sig,
        "FORUM-ACCESS-TIMESTAMP": ts,
    }


def _get(path: str, auth: bool = False) -> dict | list | None:
    url = FORUM_BASE_URL + path
    headers = _sign("GET", path) if auth else {}
    try:
        r = requests.get(url, headers=headers, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[forum_api] GET {path} failed: {e}")
        return None


def _load_ticker_map() -> dict:
    try:
        with open(TICKER_MAP_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def get_all_markets() -> list[dict]:
    global _markets_cache, _markets_cache_ts
    now = time.time()
    if _markets_cache and (now - _markets_cache_ts) < CACHE_TTL:
        return _markets_cache
    data = _get("/markets")
    if isinstance(data, list):
        _markets_cache = data
        _markets_cache_ts = now
        return data
    return []


def topic_to_ticker(topic: str) -> str | None:
    ticker_map = _load_ticker_map()
    topic_lower = topic.lower()

    if topic_lower in ticker_map:
        return ticker_map[topic_lower]

    markets = get_all_markets()
    for m in markets:
        name = (m.get("name") or "").lower()
        ticker = (m.get("ticker") or "").lower()
        if topic_lower in name or topic_lower in ticker or name in topic_lower:
            return m["ticker"]
    return None


def _raw_to_normalized(last: float, low: float, high: float) -> float:
    """
    Normalize Forum lastPrice to 0-100 scale using the day's high/low.
    50 = mid-range; 100 = at day high; 0 = at day low.
    """
    rng = max(high - low, 1.0)
    return round(max(0.0, min(100.0, ((last - low) / rng) * 100)), 2)


def get_market_price(topic: str) -> dict:
    ticker = topic_to_ticker(topic)
    if not ticker:
        return _stub_price(topic)

    # Check per-ticker cache
    now = time.time()
    if ticker in _market_cache:
        cached_ts, cached_data = _market_cache[ticker]
        if now - cached_ts < CACHE_TTL:
            return cached_data

    data = _get(f"/markets/{ticker}")
    if not data:
        return _stub_price(topic)

    last = data.get("lastPrice") or 0
    high = data.get("highPastDay") or last or 1
    low = data.get("lowPastDay") or 0
    change_pct = data.get("changePercentPastDay") or 0.0
    volume = data.get("volumePastDay") or 0
    funding_rate = data.get("movingFundingRate") or 0.0

    normalized = _raw_to_normalized(last, low, high)

    # Forum momentum signal: combines 24h price change + position in day's range
    # Positive funding rate = market longs paying shorts = bullish crowd
    # We derive a 0-100 "forum_momentum" score for use in IPO scoring
    change_clamped = max(-100.0, min(200.0, change_pct))  # cap outliers
    position_score = normalized  # 0-100: how close to day high
    momentum = round((change_clamped / 200.0 + 0.5) * 50 + position_score * 0.5, 1)
    # ^ blends: center of change range (50) scaled to 50pts + position (50pts)
    forum_momentum = max(0.0, min(100.0, momentum))

    result = {
        "topic": topic,
        "ticker": ticker,
        "raw_price": last,
        "normalized_price": normalized,
        "change_pct_day": change_pct,
        "volume_day": volume,
        "funding_rate": funding_rate,
        "forum_momentum": round(forum_momentum, 1),
        "forum_available": True,
    }
    _market_cache[ticker] = (now, result)
    return result


def get_candles(ticker: str, limit: int = 24) -> list[dict]:
    data = _get(f"/markets/{ticker}/candles?limit={limit}")
    return data if isinstance(data, list) else []


def _stub_price(topic: str) -> dict:
    seed = int(hashlib.md5(topic.lower().encode()).hexdigest()[:8], 16) % 100
    return {
        "topic": topic,
        "ticker": None,
        "raw_price": seed,
        "normalized_price": float(seed),
        "change_pct_day": 0.0,
        "volume_day": 0,
        "funding_rate": 0.0,
        "forum_momentum": 50.0,  # neutral when stubbed
        "forum_available": False,
    }


# need this for the stub
import hashlib
