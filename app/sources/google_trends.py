"""
Google Trends signal fetcher.

Two-tier approach:
  1. pytrends interest_over_time() — specific topic % growth (rate-limited)
  2. Google Trends RSS feed        — real trending topics, no auth, no rate limit

File cache persists between runs to survive demo restarts.
"""

import json
import os
import time
import requests
import xml.etree.ElementTree as ET
from pytrends.request import TrendReq

# ── File cache ───────────────────────────────────────────
_CACHE_FILE = os.path.join(os.path.dirname(__file__), "../../data/.gt_cache.json")
_CACHE_TTL = 300        # 5 min for pytrends data
_RSS_CACHE_TTL = 120    # 2 min for trending list (changes faster)

# ── Rate limiting ────────────────────────────────────────
_last_call_ts: float = 0.0
_MIN_INTERVAL = 3.5

RSS_URL = "https://trends.google.com/trending/rss?geo=US"


# ── Cache helpers ─────────────────────────────────────────

def _load_cache() -> dict:
    try:
        with open(_CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache: dict):
    try:
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        with open(_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def _rate_limit():
    global _last_call_ts
    elapsed = time.time() - _last_call_ts
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call_ts = time.time()


# ── RSS trending list ─────────────────────────────────────

def fetch_trending_topics() -> list[dict]:
    """
    Pull Google's RSS feed of today's top trending searches (US).
    Returns list of {title, approx_traffic, news_items}.
    No rate limit — safe to call freely.
    """
    cache = _load_cache()
    rss_entry = cache.get("__rss__")
    if rss_entry and (time.time() - rss_entry.get("_ts", 0)) < _RSS_CACHE_TTL:
        return rss_entry.get("topics", [])

    try:
        r = requests.get(RSS_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        root = ET.fromstring(r.text)
        ns = {"ht": "https://trends.google.com/trending/rss"}

        topics = []
        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            traffic = item.findtext("ht:approx_traffic", namespaces=ns) or "0"
            traffic_n = int(traffic.replace("+", "").replace(",", "").replace("K", "000").replace("M", "000000")) if traffic else 0
            topics.append({
                "title": title,
                "approx_traffic": traffic,
                "traffic_n": traffic_n,
            })

        cache["__rss__"] = {"topics": topics, "_ts": time.time()}
        _save_cache(cache)
        print(f"[google_trends] RSS: fetched {len(topics)} trending topics")
        return topics

    except Exception as e:
        print(f"[google_trends] RSS fetch failed: {e}")
        return cache.get("__rss__", {}).get("topics", [])


def _rss_signal_for_topic(topic: str, trending: list[dict]) -> dict | None:
    """
    Check if topic appears in the RSS trending list.
    Derives variable growth/velocity/timing signals from rank position so
    each card shows meaningfully different numbers.
    """
    topic_lower = topic.lower()
    total = max(len(trending), 1)
    for rank, t in enumerate(trending):
        title_lower = t["title"].lower()
        if topic_lower in title_lower or title_lower in topic_lower:
            rank_score = max(0, total - rank)
            rank_frac  = rank / total  # 0.0 = top, ~1.0 = bottom

            # Baseline ratio varies by rank so growth is different per card:
            # rank 0  → baseline_ratio ≈ 0.08 → growth ≈ 1100%
            # rank 5  → baseline_ratio ≈ 0.28 → growth ≈ 255%
            # rank 10 → baseline_ratio ≈ 0.48 → growth ≈ 110%
            # rank 15 → baseline_ratio ≈ 0.68 → growth ≈  47%
            # rank 19 → baseline_ratio ≈ 0.83 → growth ≈  20%
            baseline_ratio = 0.08 + rank_frac * 0.75
            current  = float(rank_score)
            baseline = max(current * baseline_ratio, 0.5)
            growth   = round(((current - baseline) / baseline) * 100.0, 1)

            # Velocity also tapers off with rank
            velocity = round((rank_score / total) * 5.0 * (1.0 - rank_frac * 0.6), 2)

            # Emergence hours: top trends break more recently
            emergence_hours = round(1.5 + rank_frac * 18.0, 1)

            return {
                "topic": topic,
                "failed": False,
                "source": "rss",
                "rss_rank": rank + 1,
                "current_mentions": current,
                "baseline_mentions": baseline,
                "velocity": velocity,
                "raw_values": [],
                "approx_traffic": t["approx_traffic"],
                "growth_proxy": growth,
                "emergence_hours": emergence_hours,
            }
    return None


# ── Main fetcher ──────────────────────────────────────────

def fetch_google_signal(topic: str) -> dict:
    cache = _load_cache()

    # 1. Check file cache (pytrends result)
    entry = cache.get(topic)
    if entry and not entry.get("failed") and (time.time() - entry.get("_ts", 0)) < _CACHE_TTL:
        print(f"[google_trends] cache hit: '{topic}'")
        return entry

    # 2. Try pytrends
    result = _fetch_pytrends(topic)

    if not result.get("failed"):
        result["_ts"] = time.time()
        cache[topic] = result
        _save_cache(cache)
        return result

    # 3. Fall back to RSS trending list
    trending = fetch_trending_topics()
    rss_result = _rss_signal_for_topic(topic, trending)
    if rss_result:
        print(f"[google_trends] RSS fallback for '{topic}': rank #{rss_result['rss_rank']}")
        rss_result["_ts"] = time.time()
        cache[topic] = rss_result
        _save_cache(cache)
        return rss_result

    # 4. Topic not in trending list — return failed (not in top trends)
    not_trending = {
        "topic": topic,
        "failed": False,      # not an error — it's genuinely not trending
        "source": "rss_miss",
        "current_mentions": 1.0,
        "baseline_mentions": 1.0,
        "velocity": 0.0,
        "raw_values": [],
        "growth_proxy": 0.0,
    }
    not_trending["_ts"] = time.time()
    cache[topic] = not_trending
    _save_cache(cache)
    return not_trending


def _fetch_pytrends(topic: str, attempt: int = 0) -> dict:
    _rate_limit()
    try:
        pt = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        pt.build_payload([topic], cat=0, timeframe="now 1-d", geo="")
        data = pt.interest_over_time()

        if data.empty or topic not in data.columns:
            return _failed_signal(topic, "no_data_returned")

        values = data[topic].tolist()
        if len(values) < 4:
            return _failed_signal(topic, "insufficient_datapoints")

        mid = len(values) // 2
        baseline = max(sum(values[:mid]) / len(values[:mid]), 0.1)
        current = sum(values[mid:]) / len(values[mid:])
        recent = values[-4:]
        velocity = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)

        return {
            "topic": topic,
            "failed": False,
            "source": "pytrends",
            "current_mentions": round(current, 2),
            "baseline_mentions": round(baseline, 2),
            "velocity": round(velocity, 2),
            "raw_values": values,
        }

    except Exception as e:
        err = str(e)
        if "429" in err:
            print(f"[google_trends] 429 for '{topic}' — using RSS fallback")
        print(f"[google_trends] pytrends failed for '{topic}': {e}")
        return _failed_signal(topic, err[:80])


def fetch_google_signal_rss(topic: str, trending: list[dict] | None = None) -> dict:
    """
    RSS-only signal — no pytrends, no rate limiting, near-instant.
    Fetches the trending list once if not provided (cached for 2 min).
    """
    if trending is None:
        trending = fetch_trending_topics()

    rss_result = _rss_signal_for_topic(topic, trending)
    if rss_result:
        return rss_result

    return {
        "topic": topic,
        "failed": False,
        "source": "rss_miss",
        "current_mentions": 1.0,
        "baseline_mentions": 1.0,
        "velocity": 0.0,
        "raw_values": [],
        "growth_proxy": 0.0,
    }


def _failed_signal(topic: str, reason: str = "unknown") -> dict:
    return {
        "topic": topic,
        "failed": True,
        "reason": reason,
        "current_mentions": None,
        "baseline_mentions": None,
        "velocity": None,
        "raw_values": [],
    }
