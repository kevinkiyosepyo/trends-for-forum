# Trends for Forum: https://trends-for-forum.vercel.app/

An AI-powered trend detection agent that identifies emerging internet trends before [Forum](https://forum.market) (YC W26) prices them in.

Forum is an attention market where you trade on what people are paying attention to. This agent finds trends early, scores them like IPO opportunities, and tells you which ones are underpriced.

## How It Works

**Data Sources**
- **Google Trends** — real-time trending topics via RSS + pytrends API with file-based caching
- **Forum Market API** — live market prices, 24h momentum, and volume data with HMAC-SHA256 auth

**Scoring Engine**

Every topic gets an IPO Score (0-100) based on:

| Component | Weight | What it measures |
|---|---|---|
| Growth | 0-50 pts | Google Trends growth %, log-scaled |
| Velocity | 0-10 pts | Rate of change / acceleration |
| Recency | 0-25 pts | How recently the trend emerged |
| Mispricing | 0-15 pts | Gap between attention and Forum price |
| Saturation | 0-10 pts penalty | Overpriced topics with weak growth |

**Verdicts**
- **STRONG BUY** (75+) — explosive early mover with upside
- **BUY** (58-74) — strong trend with good timing
- **WATCH** (40-57) — emerging but uncertain
- **AVOID** (<40) — stale, no momentum, or overpriced

**Stage Classification**
- Seed (0-3h) -> Series A (3-8h) -> Pre-IPO (8-16h) -> Public (16h+)

## Features

- **Trending Tab** — auto-loads today's top Google Trends and scores them
- **Forum Markets Tab** — scores every live Forum market for attention mispricing
- **Search** — analyze any topic on demand
- **Dark terminal UI** — trading dashboard with verdict badges, score bars, and source health indicators
- **LLM Explanations** — Claude or GPT-4o generates analyst-style summaries (falls back to rule-based if no API key)
- **Two-tier Google Trends** — pytrends first, RSS fallback on rate limit, file-based cache between runs

## Setup

```bash
git clone https://github.com/kevinkiyosepyo/trends-for-forum.git
cd trends-for-forum
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure API keys (all optional - the app works without them)
cp .env.example .env
# Edit .env with your keys:
#   FORUM_API_KEY / FORUM_API_SECRET - for live Forum market data
#   ANTHROPIC_API_KEY - for Claude-powered explanations
#   OPENAI_API_KEY - alternative LLM provider

# Run
python -m uvicorn app.main:app --reload --port 8000
# Open http://localhost:8000
```

## Tech Stack

- **Backend**: Python, FastAPI, Pydantic
- **Data**: pytrends, Google Trends RSS, Forum Market REST API
- **LLM**: Claude Opus / GPT-4o (auto-detected, optional)
- **Frontend**: Vanilla HTML/CSS/JS, no build step

## Architecture

```
app/
  main.py                 # FastAPI routes + static serving
  config.py               # All settings, thresholds, API keys
  sources/
    google_trends.py      # Two-tier Google Trends fetcher + cache
    forum_api.py          # Forum API client with HMAC auth
  agent/
    orchestrator.py       # Main pipeline: fetch -> score -> recommend -> explain
    ipo_scorer.py         # Log-scaled scoring engine with debug components
    recommender.py        # Verdict thresholds + stage logic
    summarizer.py         # LLM explanation layer (Claude/GPT/rule-based)
  static/
    index.html            # Trading terminal dashboard
scripts/
  run_agent_once.py       # CLI demo script
data/
  topics.json             # Default topic list
  ticker_map.json         # Topic -> Forum ticker overrides
```

## Built For

[Forum](https://forum.market) (YC W26) hackathon — an attention market where internet trends are tradeable assets.
