"""
Forum market price stub.
Returns a simulated market momentum score for a topic (0-100).
Replace with real Forum API calls when available.
"""

import json
import os
import random

PRICES_FILE = os.path.join(os.path.dirname(__file__), "../../data/sample_forum_prices.json")


def _load_prices() -> dict:
    try:
        with open(PRICES_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def get_forum_price(topic: str) -> float:
    """
    Returns a 0-100 score representing current Forum market momentum.
    Higher = market already pricing in the trend.
    Lower = market has not reacted yet (potential alpha).
    """
    prices = _load_prices()
    topic_lower = topic.lower()

    # Exact match first
    if topic_lower in prices:
        return float(prices[topic_lower])

    # Partial match
    for key, val in prices.items():
        if key in topic_lower or topic_lower in key:
            return float(val)

    # Default: random moderate value so demo always works
    return round(random.uniform(20, 60), 2)
