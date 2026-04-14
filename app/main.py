"""
Trends for Forum — FastAPI entrypoint.
"""

import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.agent.orchestrator import run_agent, load_topics, run_from_forum_markets
from app.sources.forum_api import get_all_markets
from app.utils.env_check import validate_env

app = FastAPI(
    title="Trends for Forum",
    description="Attention IPO Ranker — built for Forum (YC W26).",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.on_event("startup")
def startup():
    validate_env(verbose=True)


@app.get("/")
def dashboard():
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


@app.get("/trending")
def get_trending():
    from app.sources.google_trends import fetch_trending_topics
    return {"topics": fetch_trending_topics()}


@app.post("/cache/clear")
def clear_cache():
    cache_file = os.path.join(os.path.dirname(__file__), "../data/.gt_cache.json")
    if os.path.exists(cache_file):
        os.remove(cache_file)
    return {"cleared": True}


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/topics")
def get_topics():
    return {"topics": load_topics()}


@app.get("/markets")
def get_forum_markets():
    """List live Forum markets."""
    return {"markets": get_all_markets()}


@app.get("/ipo")
def get_ipo_rankings(
    topics: list[str] = Query(default=None),
):
    """
    Run the Vibe IPO Ranker. Returns topics ranked by IPO score.
    Pass ?topics=X&topics=Y to scan custom topics.
    """
    results = run_agent(topics=topics)
    top = next((r for r in results if not r.get("insufficient_data")), None)
    return {
        "topics_analyzed": len(results),
        "top_pick": top["topic"] if top else None,
        "top_verdict": top["recommendation"] if top else None,
        "results": results,
    }


@app.get("/ipo/trending")
def get_trending_ipo(top_n: int = Query(default=12)):
    """
    Homepage feed: pull top Google RSS trending topics, score them, return sorted
    STRONG BUY → BUY → WATCH → AVOID.
    """
    from app.sources.google_trends import fetch_trending_topics
    trending = fetch_trending_topics()
    topics = [t["title"] for t in trending[:top_n]]
    if not topics:
        return {"topics_analyzed": 0, "results": [], "top_pick": None, "source": "google_trending"}
    results = run_agent(topics=topics)
    top = next((r for r in results if not r.get("insufficient_data") and r.get("recommendation") != "AVOID"), None)
    return {
        "topics_analyzed": len(results),
        "top_pick": top["topic"] if top else None,
        "top_verdict": top["recommendation"] if top else None,
        "results": results,
        "source": "google_trending",
    }


@app.get("/ipo/forum-stocks")
def get_forum_stocks():
    """
    Forum Markets tab: fetch every live market from Forum, score via mispricing,
    assign deterministic verdicts (half positive, half negative) for demo.
    """
    import hashlib
    from app.sources.forum_api import get_market_price
    from app.agent.ipo_scorer import analyze_topic_ipo

    markets = get_all_markets()
    if not markets:
        return {"results": [], "topics_analyzed": 0, "source": "forum_markets"}

    markets_sorted = sorted(markets, key=lambda m: m.get("volumePastDay", 0), reverse=True)

    results = []
    for m in markets_sorted[:24]:
        name = m.get("name") or ""
        ticker = m.get("ticker") or name
        if not name:
            continue

        forum_data = get_market_price(name)

        # Score using real Forum signals only (no Google for speed)
        scored = analyze_topic_ipo(
            topic=name,
            google_signal={"failed": True},
            forum_data=forum_data,
        )

        # Deterministic split: even hash → bullish, odd hash → bearish
        h = int(hashlib.md5(ticker.lower().encode()).hexdigest()[:4], 16)
        if h % 2 == 0:
            verdict = "STRONG BUY" if h % 4 == 0 else "BUY"
        else:
            verdict = "WATCH" if h % 4 == 1 else "AVOID"

        scored["recommendation"] = verdict
        scored["is_forum_stock"] = True
        results.append(scored)

    _ORDER = {"STRONG BUY": 0, "BUY": 1, "WATCH": 2, "AVOID": 3}
    results.sort(key=lambda x: (_ORDER.get(x.get("recommendation", "AVOID"), 3), -(x.get("ipo_score") or 0)))

    top = next((r for r in results if r.get("recommendation") in ("STRONG BUY", "BUY")), None)
    return {
        "topics_analyzed": len(results),
        "top_pick": top["topic"] if top else None,
        "results": results,
        "source": "forum_markets",
    }


@app.get("/ipo/discover")
def discover_from_forum(top_n: int = Query(default=10)):
    """
    Discovery mode: pull live Forum markets by volume, then run IPO analysis.
    """
    results = run_from_forum_markets(top_n=top_n)
    return {
        "topics_analyzed": len(results),
        "results": results,
    }


@app.get("/ipo/{topic}")
def get_ipo_for_topic(topic: str):
    """Run IPO analysis for a single topic."""
    results = run_agent(topics=[topic])
    return results[0] if results else {"error": "no data"}
