"""
IPO verdict engine.
Maps IPO score + stage + confidence to a trading verdict.
"""

from app.config import STRONG_BUY_THRESHOLD, BUY_THRESHOLD, WATCH_THRESHOLD

MIN_HEALTHY_SOURCES = 1


def recommend(
    signal_score: float = 0,
    mispricing_score: float | None = None,
    confidence_score: float = 100.0,
    healthy_sources: int = 2,
    insufficient_data: bool = False,
    # IPO-specific
    ipo_score: float | None = None,
    stage: str | None = None,
    **kwargs,
) -> str:
    score = ipo_score if ipo_score is not None else signal_score

    if insufficient_data or healthy_sources < MIN_HEALTHY_SOURCES:
        return "INSUFFICIENT DATA"

    # Public/saturated — late entry, cap at WATCH unless strong growth
    if stage == "Public":
        if score >= STRONG_BUY_THRESHOLD:
            return "BUY"    # still worth it if explosive
        if score >= BUY_THRESHOLD:
            return "WATCH"  # late but some momentum
        return "AVOID"

    if score >= STRONG_BUY_THRESHOLD:
        return "STRONG BUY"
    if score >= BUY_THRESHOLD:
        return "BUY"
    if score >= WATCH_THRESHOLD:
        return "WATCH"
    return "AVOID"


def confidence_label(confidence_score: float) -> str:
    if confidence_score >= 75:
        return "HIGH"
    if confidence_score >= 40:
        return "MEDIUM"
    return "LOW"


def signal_label(score: float) -> str:
    if score >= 75:
        return "explosive"
    if score >= 58:
        return "strong"
    if score >= 40:
        return "moderate"
    return "weak"
