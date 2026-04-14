"""
Trends for Forum — IPO scoring engine.
Sources: Google Trends + Forum API only.

Score breakdown (0-100):
  growth_component    0-50  log-scaled Google Trends growth %
  velocity_component  0-10  rate of change (acceleration)
  recency_component   0-25  earlier = more upside potential
  mispricing_component 0-15 underpriced vs Forum = alpha
  saturation_penalty  0-10  negative adjustment for overpriced/late
  ─────────────────────────
  max possible        100
"""

import math

from app.config import (
    STAGE_SEED_MAX_HOURS,
    STAGE_SERIES_A_MAX_HOURS,
    STAGE_PRE_IPO_MAX_HOURS,
)


def classify_stage(hours: float) -> str:
    if hours <= STAGE_SEED_MAX_HOURS:
        return "Seed"
    if hours <= STAGE_SERIES_A_MAX_HOURS:
        return "Series A"
    if hours <= STAGE_PRE_IPO_MAX_HOURS:
        return "Pre-IPO"
    return "Public"


def estimate_emergence_hours(google_signal: dict) -> float:
    raw = google_signal.get("raw_values", [])
    if not raw or len(raw) < 3:
        return 12.0
    peak = max(raw)
    if peak == 0:
        return 24.0
    threshold = peak * 0.20
    total = len(raw)
    for i, val in enumerate(raw):
        if val >= threshold:
            return float(total - i)
    return 24.0


def _estimate_hours_from_forum(forum_data: dict) -> float:
    momentum = forum_data.get("forum_momentum", 50.0)
    price = forum_data.get("normalized_price", 50.0)
    if momentum > 75 and price < 30:
        return 4.0
    if momentum > 60:
        return 10.0
    return 16.0


def _growth_component(growth_pct: float) -> float:
    """
    Log-scaled growth score (0-50 pts).

    Calibration:
      0%   →  0.0
      50%  → 13.9
      100% → 22.0
      150% → 27.7
      300% → 38.9
      500% → 47.9
      750%+ → capped at 50
    """
    if growth_pct <= 0:
        return 0.0
    return min(50.0, math.log(1.0 + growth_pct / 50.0) * 20.0)


def _velocity_component(velocity: float) -> float:
    """
    Linear velocity score (0-10 pts).
    velocity=1 → 2 pts, velocity=3 → 6 pts, velocity=5+ → 10 pts.
    """
    if velocity <= 0:
        return 0.0
    return min(10.0, velocity * 2.0)


def _recency_component(hours: float) -> float:
    """
    Recency score (0-25 pts). Decay over 24h.
    0h → 25, 6h → 18.75, 12h → 12.5, 18h → 6.25, 24h+ → 0
    """
    return max(0.0, 25.0 * (1.0 - hours / 24.0))


def _mispricing_component(forum_price: float) -> float:
    """
    Underpricing alpha (0-15 pts).
    Low Forum price relative to 100 = alpha opportunity.
    price=0 → 15, price=50 → 7.5, price=100 → 0
    """
    return max(0.0, (1.0 - forum_price / 100.0) * 15.0)


def _saturation_penalty(forum_price: float, growth_pct: float | None) -> float:
    """
    Penalty (0-10 pts deducted) for high-price topics with weak growth.
    Rewards cheap underpriced entries; punishes overpriced with no growth.
    """
    if forum_price < 60:
        return 0.0
    # High-priced topic: only penalize if growth is also weak
    g = growth_pct if growth_pct is not None else 0.0
    if g >= 100:
        return 0.0
    # Linear penalty: price=60+, growth=0 → full 10pt penalty
    price_factor = (forum_price - 60.0) / 40.0   # 0 at 60, 1.0 at 100
    growth_offset = min(1.0, g / 100.0)           # reduces penalty when growth exists
    return round(min(10.0, price_factor * 10.0 * (1.0 - growth_offset)), 1)


def ipo_score(
    growth_pct: float | None,
    hours: float,
    forum_normalized_price: float,
    velocity: float = 0.0,
    forum_change_pct: float | None = None,
    forum_momentum: float | None = None,
) -> tuple[float, str, dict]:
    """
    Returns (score 0-100, primary_signal_source, components_dict).
    components_dict is for debug / transparency.
    """

    # ── Growth component ─────────────────────────────────────
    if growth_pct is not None:
        primary_source = "google"
        growth_comp = _growth_component(growth_pct)
    elif forum_change_pct is not None and forum_change_pct != 0:
        primary_source = "forum_change"
        # Forum day-change is on a smaller scale; map to proxy growth
        proxy = max(0.0, forum_change_pct * 2.0)
        growth_comp = _growth_component(proxy)
    elif forum_momentum is not None:
        primary_source = "forum_momentum"
        # Momentum 0-100 → treat as a proxy growth %
        proxy = max(0.0, (forum_momentum - 40.0) * 3.0)
        growth_comp = _growth_component(proxy)
    else:
        primary_source = "none"
        growth_comp = 0.0

    # ── Other components ─────────────────────────────────────
    vel_comp = _velocity_component(velocity)
    rec_comp = _recency_component(hours)
    mis_comp = _mispricing_component(forum_normalized_price)
    sat_pen = _saturation_penalty(forum_normalized_price, growth_pct)

    raw = growth_comp + vel_comp + rec_comp + mis_comp - sat_pen
    score = round(min(max(raw, 0.0), 100.0), 1)

    components = {
        "growth_component": round(growth_comp, 1),
        "velocity_component": round(vel_comp, 1),
        "recency_component": round(rec_comp, 1),
        "mispricing_component": round(mis_comp, 1),
        "saturation_penalty": round(sat_pen, 1),
        "raw_sum": round(raw, 1),
        "final_score": score,
    }

    return score, primary_source, components


def analyze_topic_ipo(
    topic: str,
    google_signal: dict,
    forum_data: dict,
    debug: bool = False,
) -> dict:
    g_failed = google_signal.get("failed", False)
    forum_available = forum_data.get("forum_available", False)

    # ── Google growth ─────────────────────────────────────────
    google_growth = None
    if not g_failed:
        cur = google_signal.get("current_mentions")
        base = google_signal.get("baseline_mentions")
        if cur is not None and base and base > 0:
            google_growth = round(((cur - base) / base) * 100.0, 1)

    # ── Emergence timing ──────────────────────────────────────
    if not g_failed and google_signal.get("raw_values"):
        hours = estimate_emergence_hours(google_signal)
    elif forum_available:
        hours = _estimate_hours_from_forum(forum_data)
    else:
        hours = 12.0

    stage = classify_stage(hours)
    velocity = google_signal.get("velocity") or 0.0

    forum_price = forum_data.get("normalized_price", 50.0)
    forum_change = forum_data.get("change_pct_day", 0.0)
    forum_momentum = forum_data.get("forum_momentum", 50.0)
    ticker = forum_data.get("ticker")

    score, primary_source, components = ipo_score(
        growth_pct=google_growth,
        hours=hours,
        forum_normalized_price=forum_price,
        velocity=velocity,
        forum_change_pct=forum_change if g_failed else None,
        forum_momentum=forum_momentum if g_failed else None,
    )

    if debug:
        print(f"\n[score debug] {topic}")
        print(f"  google_growth={google_growth}%  velocity={velocity}  hours={hours:.1f}  forum_price={forum_price}")
        for k, v in components.items():
            print(f"  {k}: {v}")

    source_health = {
        "google": "failed" if g_failed else "ok",
        "forum": "live" if forum_available else "stub",
    }
    healthy_sources = sum(1 for v in source_health.values() if v in ("ok", "live", "stub"))

    if primary_source == "none":
        confidence = 0.0
    elif primary_source == "forum_momentum":
        confidence = 40.0
    elif primary_source == "forum_change":
        confidence = 50.0
    else:
        confidence = round((healthy_sources / 2) * 100, 1)

    mispricing = round(score - forum_price, 1)

    return {
        "topic": topic,
        "ticker": ticker,
        "ipo_score": score,
        "stage": stage,
        "hours_since_emergence": round(hours, 1),
        "google_growth": google_growth,
        "velocity": round(velocity, 2),
        "forum_price": forum_price,
        "forum_change_pct": forum_change,
        "forum_momentum": forum_momentum,
        "forum_available": forum_available,
        "mispricing": mispricing,
        "primary_signal": primary_source,
        "source_health": source_health,
        "healthy_sources": healthy_sources,
        "insufficient_data": healthy_sources == 0,
        "signal_score": score,
        "confidence_score": confidence,
        "combined_score": score,
        "acceleration": round(velocity, 2),
        "mispricing_score": mispricing,
        # Score subcomponents for debug/transparency
        "score_components": components,
    }
