"""
Vibe IPO Ranker — main agent loop.
Sources: Google Trends + Forum API.
"""

import json
from app.sources.google_trends import fetch_google_signal
from app.sources.forum_api import get_market_price, get_all_markets
from app.agent.ipo_scorer import analyze_topic_ipo
from app.agent.recommender import recommend
from app.agent.summarizer import summarize_topic
from app.config import TOPICS_FILE


def load_topics() -> list[str]:
    try:
        with open(TOPICS_FILE) as f:
            return json.load(f).get("topics", [])
    except Exception:
        return ["AI agents", "Claude", "Cursor", "GPT-5", "Drake"]


def run_agent(topics: list[str] | None = None) -> list[dict]:
    if topics is None:
        topics = load_topics()

    results = []
    first = True
    for topic in topics:
        print(f"[agent] analyzing: {topic}")
        google_signal = fetch_google_signal(topic)
        forum_data = get_market_price(topic)

        scored = analyze_topic_ipo(
            topic=topic,
            google_signal=google_signal,
            forum_data=forum_data,
            debug=first,   # print subcomponents for the first topic each run
        )
        first = False
        scored["recommendation"] = recommend(**scored)
        scored["explanation"] = summarize_topic(scored)
        results.append(scored)

    _VERDICT_ORDER = {"STRONG BUY": 0, "BUY": 1, "WATCH": 2, "AVOID": 3, "INSUFFICIENT DATA": 4}
    return sorted(
        results,
        key=lambda x: (
            _VERDICT_ORDER.get(x.get("recommendation", "AVOID"), 3),
            -(x.get("ipo_score") or 0),
        ),
    )


def run_from_forum_markets(top_n: int = 10) -> list[dict]:
    markets = get_all_markets()
    if not markets:
        print("[agent] No Forum markets returned — check API credentials")
        return []
    markets_sorted = sorted(markets, key=lambda m: m.get("volumePastDay", 0), reverse=True)
    topics = [m["name"] for m in markets_sorted[:top_n]]
    return run_agent(topics=topics)
