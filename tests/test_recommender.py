from app.agent.recommender import recommend, confidence_label, signal_label


def test_strong_buy():
    assert recommend(ipo_score=80, signal_score=80, mispricing_score=20, healthy_sources=2, stage="Series A") == "STRONG BUY"

def test_buy():
    assert recommend(ipo_score=60, signal_score=60, mispricing_score=10, healthy_sources=2, stage="Series A") == "BUY"

def test_watch():
    assert recommend(ipo_score=40, signal_score=40, mispricing_score=5, healthy_sources=2, stage="Pre-IPO") == "WATCH"

def test_avoid():
    assert recommend(ipo_score=20, signal_score=20, mispricing_score=-5, healthy_sources=2, stage="Pre-IPO") == "AVOID"

def test_insufficient_data():
    assert recommend(ipo_score=90, signal_score=90, insufficient_data=True) == "INSUFFICIENT DATA"

def test_no_healthy_sources():
    assert recommend(ipo_score=80, signal_score=80, healthy_sources=0) == "INSUFFICIENT DATA"

def test_public_stage_caps_to_buy():
    # Public stage: explosive score (80) → BUY (capped from STRONG BUY)
    assert recommend(ipo_score=80, signal_score=80, healthy_sources=2, stage="Public") == "BUY"
    # Public stage: moderate score (50) → AVOID (late, window mostly passed)
    assert recommend(ipo_score=50, signal_score=50, healthy_sources=2, stage="Public") == "AVOID"

def test_confidence_labels():
    assert confidence_label(80) == "HIGH"
    assert confidence_label(55) == "MEDIUM"
    assert confidence_label(20) == "LOW"

def test_signal_labels():
    assert signal_label(80) == "explosive"
    assert signal_label(60) == "strong"
    assert signal_label(40) == "moderate"
    assert signal_label(10) == "weak"
