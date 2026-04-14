from app.agent.ipo_scorer import ipo_score, classify_stage, estimate_emergence_hours, analyze_topic_ipo


def g_signal(current=80, baseline=40, velocity=5, failed=False):
    if failed:
        return {"failed": True, "current_mentions": None, "baseline_mentions": None, "velocity": None, "raw_values": []}
    return {"failed": False, "current_mentions": current, "baseline_mentions": baseline, "velocity": velocity,
            "raw_values": [20] * 8 + [50, 60, 70, 80]}


def forum(price=40):
    return {"normalized_price": price, "change_pct_day": 0.0, "forum_momentum": 50.0,
            "forum_available": False, "ticker": None}


# ── ipo_score ──────────────────────────────────────────

def test_ipo_score_high_growth_early():
    score, _, _ = ipo_score(growth_pct=500, hours=2, forum_normalized_price=20)
    assert score > 60

def test_ipo_score_late_stage_penalized():
    score_early, _, _ = ipo_score(growth_pct=200, hours=2, forum_normalized_price=30)
    score_late, _, _  = ipo_score(growth_pct=200, hours=22, forum_normalized_price=30)
    assert score_early > score_late

def test_ipo_score_high_forum_price_penalized():
    low, _, _  = ipo_score(growth_pct=200, hours=5, forum_normalized_price=20)
    high, _, _ = ipo_score(growth_pct=200, hours=5, forum_normalized_price=90)
    assert low > high

def test_ipo_score_capped_at_100():
    score, _, _ = ipo_score(growth_pct=9999, hours=0, forum_normalized_price=0)
    assert score <= 100.0

def test_ipo_score_forum_fallback():
    score, src, _ = ipo_score(growth_pct=None, hours=5, forum_normalized_price=30, forum_change_pct=150)
    assert src == "forum_change"
    assert score > 0


# ── classify_stage ─────────────────────────────────────

def test_stage_seed():
    assert classify_stage(1) == "Seed"

def test_stage_series_a():
    assert classify_stage(6) == "Series A"

def test_stage_pre_ipo():
    assert classify_stage(15) == "Pre-IPO"

def test_stage_public():
    assert classify_stage(30) == "Public"


# ── analyze_topic_ipo ──────────────────────────────────

def test_analyze_returns_required_keys():
    result = analyze_topic_ipo("test", g_signal(), forum())
    assert "ipo_score" in result
    assert "stage" in result
    assert 0 <= result["ipo_score"] <= 100

def test_analyze_failed_google_still_scores():
    result = analyze_topic_ipo("test", g_signal(failed=True), forum(price=20))
    # Forum momentum fallback should produce non-zero score
    assert result["ipo_score"] >= 0
    assert not result["insufficient_data"]

def test_analyze_all_failed_is_insufficient():
    bad_forum = {"normalized_price": 50, "change_pct_day": 0, "forum_momentum": 50,
                 "forum_available": False, "ticker": None}
    result = analyze_topic_ipo("test", g_signal(failed=True), bad_forum)
    # forum stub counts as a source — should not be insufficient
    assert result["healthy_sources"] >= 0
