from pydantic import BaseModel
from typing import Optional


class SourceSignal(BaseModel):
    current_mentions: float = 0.0
    baseline_mentions: float = 0.0
    velocity: float = 0.0  # rate of change over last window


class TopicSignal(BaseModel):
    topic: str
    google_score: float = 0.0
    reddit_score: float = 0.0
    news_score: float = 0.0
    combined_score: float = 0.0
    acceleration_score: float = 0.0
    cross_platform_confirmation: float = 0.0
    forum_price: Optional[float] = None
    mispricing_score: Optional[float] = None
    recommendation: Optional[str] = None  # "LONG" | "WATCH" | "SHORT"
    explanation: Optional[str] = None


class AgentResponse(BaseModel):
    topics_analyzed: int
    results: list[TopicSignal]
    top_pick: Optional[str] = None
