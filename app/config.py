import os
from dotenv import load_dotenv

load_dotenv()

# LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")

# Model selection
# Opus for rich per-topic explanations (called once per topic)
# Haiku for anything bulk / fast / cheap
ANTHROPIC_MAIN_MODEL = "claude-opus-4-6"
ANTHROPIC_FAST_MODEL = "claude-haiku-4-5-20251001"
OPENAI_MAIN_MODEL = "gpt-4o"
OPENAI_FAST_MODEL = "gpt-4o-mini"

# Forum Market API
FORUM_API_KEY = os.getenv("FORUM_API_KEY", "")
FORUM_API_SECRET = os.getenv("FORUM_API_SECRET", "")
FORUM_BASE_URL = os.getenv("FORUM_BASE_URL", "https://api.forum.market/v1")

# File paths
TOPICS_FILE = os.path.join(os.path.dirname(__file__), "../data/topics.json")
TICKER_MAP_FILE = os.path.join(os.path.dirname(__file__), "../data/ticker_map.json")

# IPO scoring
STRONG_BUY_THRESHOLD = 75
BUY_THRESHOLD = 58
WATCH_THRESHOLD = 40

# Stage hours
STAGE_SEED_MAX_HOURS = 3
STAGE_SERIES_A_MAX_HOURS = 8
STAGE_PRE_IPO_MAX_HOURS = 16

# kept for any remaining imports
GOOGLE_WEIGHT = 0.45
REDDIT_WEIGHT = 0.0
ACCELERATION_WEIGHT = 0.20
CROSS_PLATFORM_WEIGHT = 0.0
LONG_SCORE_THRESHOLD = 75
LONG_MISPRICING_THRESHOLD = 15
SHORT_SCORE_THRESHOLD = 30
SHORT_MISPRICING_THRESHOLD = -10
