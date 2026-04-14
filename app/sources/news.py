"""
News/RSS signal fetcher.
Uses NewsAPI or falls back to RSS feeds for extra confidence signal.
"""

import os
import feedparser
import requests
from datetime import datetime, timezone, timedelta

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

RSS_FEEDS = [
    "https://feeds.feedburner.com/TechCrunch",
    "https://hnrss.org/frontpage",
    "https://www.reddit.com/r/technology/.rss",
]


def fetch_news_signal(topic: str) -> dict:
    if NEWS_API_KEY:
        return _fetch_newsapi(topic)
    return _fetch_rss(topic)


def _fetch_newsapi(topic: str) -> dict:
    try:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": topic,
            "from": yesterday,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": NEWS_API_KEY,
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        total = data.get("totalResults", 0)
        articles = data.get("articles", [])

        mid = len(articles) // 2
        baseline = max(mid, 1)
        current = max(len(articles) - mid, 1)

        return {
            "topic": topic,
            "current_mentions": float(current),
            "baseline_mentions": float(baseline),
            "velocity": float(current - baseline),
            "total_articles": total,
        }

    except Exception as e:
        print(f"[news] newsapi error for '{topic}': {e}")
        return _empty_signal(topic)


def _fetch_rss(topic: str) -> dict:
    matches = []
    topic_lower = topic.lower()

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = (entry.get("title") or "").lower()
                summary = (entry.get("summary") or "").lower()
                if topic_lower in title or topic_lower in summary:
                    matches.append(entry)
        except Exception:
            continue

    count = len(matches)
    baseline = max(count // 2, 1)
    current = max(count - baseline, 1)

    return {
        "topic": topic,
        "current_mentions": float(current),
        "baseline_mentions": float(baseline),
        "velocity": float(current - baseline),
        "total_articles": count,
    }


def _empty_signal(topic: str) -> dict:
    return {
        "topic": topic,
        "current_mentions": 0.0,
        "baseline_mentions": 1.0,
        "velocity": 0.0,
        "total_articles": 0,
    }
