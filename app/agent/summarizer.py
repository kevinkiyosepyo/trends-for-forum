"""
LLM summarization — IPO framing.
Sources: Google Trends + Forum only.
"""

from app.config import (
    LLM_PROVIDER, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    ANTHROPIC_MAIN_MODEL, OPENAI_MAIN_MODEL,
)
from app.agent.recommender import signal_label


def summarize_topic(scored: dict) -> str:
    if scored.get("insufficient_data"):
        return f"Cannot assess {scored['topic']} — no data available from Google Trends or Forum."

    # Prefer the configured provider, but fall through to whichever key is actually set
    if LLM_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
        return _summarize_anthropic(scored)
    if LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        return _summarize_openai(scored)
    # Auto-detect fallback
    if ANTHROPIC_API_KEY:
        return _summarize_anthropic(scored)
    if OPENAI_API_KEY:
        return _summarize_openai(scored)
    return _summarize_fallback(scored)


def _fmt_pct(value) -> str:
    if value is None:
        return "unavailable"
    return f"+{value:.1f}%" if value >= 0 else f"{value:.1f}%"


def _build_prompt(scored: dict) -> str:
    g_str = _fmt_pct(scored.get("google_growth"))
    stage = scored.get("stage", "Unknown")
    hours = scored.get("hours_since_emergence", "?")
    verdict = scored.get("recommendation", "WATCH")
    forum_available = scored.get("forum_available", False)
    forum_str = f"{scored.get('forum_price', '?'):.0f} ({'live' if forum_available else 'estimated'})"
    g_failed = scored.get("source_health", {}).get("google") == "failed"

    return f"""You are a venture capitalist analyst for an attention market called Forum.
Users trade internet topics like stocks. Analyze this trend as a pre-IPO asset.

Write 2-3 punchy sentences explaining this opportunity. Use the actual numbers.
Tell the user WHY this is a {verdict}. Reference the stage, growth rate, and Forum pricing.
If Google Trends data was unavailable, mention that confidence is limited.
Do NOT say "it appears" or "it seems". Sound like a confident analyst.

Topic: {scored['topic']}
IPO Score: {scored.get('ipo_score', 0):.1f} / 100
Stage: {stage} (~{hours}h since emergence)
Google Trends: {g_str}{"  [rate-limited — using Forum momentum as proxy]" if g_failed else ""}
Forum Price: {forum_str}  (24h change: {_fmt_pct(scored.get('forum_change_pct'))})
Mispricing: {scored.get('mispricing', 'N/A')}
Verdict: {verdict}
"""


def _summarize_openai(scored: dict) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_MAIN_MODEL,
            messages=[{"role": "user", "content": _build_prompt(scored)}],
            max_tokens=180,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[summarizer] openai error: {e}")
        return _summarize_fallback(scored)


def _summarize_anthropic(scored: dict) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=ANTHROPIC_MAIN_MODEL,
            max_tokens=180,
            messages=[{"role": "user", "content": _build_prompt(scored)}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[summarizer] anthropic error: {e}")
        return _summarize_fallback(scored)


def _summarize_fallback(scored: dict) -> str:
    topic      = scored["topic"]
    verdict    = scored.get("recommendation", "WATCH")
    stage      = scored.get("stage", "Unknown")
    hours      = scored.get("hours_since_emergence", 12.0)
    growth     = scored.get("google_growth")
    mispricing = scored.get("mispricing") or 0
    forum_price= scored.get("forum_price", 50)
    velocity   = scored.get("velocity") or 0

    # Opening based on verdict
    if verdict == "STRONG BUY":
        opener = f"{topic} is exploding on Google Trends"
    elif verdict == "BUY":
        opener = f"{topic} is gaining serious traction"
    elif verdict == "WATCH":
        opener = f"{topic} is showing early momentum"
    else:
        opener = f"{topic} has been trending"

    # Growth clause
    if growth and growth > 0:
        growth_clause = f" with +{growth:.0f}% growth"
    elif growth and growth < 0:
        growth_clause = f" but interest is fading ({growth:.0f}%)"
    else:
        growth_clause = ""

    # Timing clause
    try:
        h = float(hours)
        timing = f", {h:.0f}h in and still in the {stage} window"
    except Exception:
        timing = f" in the {stage} stage"

    # Velocity note
    if velocity > 3:
        vel_note = " Momentum is accelerating fast."
    elif velocity > 1:
        vel_note = " Still picking up speed."
    else:
        vel_note = ""

    # Pricing clause
    if mispricing > 15:
        price_clause = f"Forum is pricing this at {forum_price:.0f} — well behind where attention already is."
    elif mispricing > 5:
        price_clause = f"At Forum price {forum_price:.0f}, attention is ahead of the market."
    elif mispricing < -10:
        price_clause = f"Forum has already priced in the hype at {forum_price:.0f}. Late entry risk."
    else:
        price_clause = f"Forum price of {forum_price:.0f} looks fairly valued relative to attention."

    return f"{opener}{growth_clause}{timing}.{vel_note} {price_clause} Verdict: {verdict}."


def deep_analyze_topic(scored: dict) -> dict:
    """
    Generate a detailed multi-section analysis for the detail page.
    Returns a dict with section keys. Uses LLM if available, rule-based fallback otherwise.
    """
    if LLM_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
        return _deep_analyze_anthropic(scored)
    if LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        return _deep_analyze_openai(scored)
    if ANTHROPIC_API_KEY:
        return _deep_analyze_anthropic(scored)
    if OPENAI_API_KEY:
        return _deep_analyze_openai(scored)
    return _deep_analyze_fallback(scored)


def _build_deep_prompt(scored: dict) -> str:
    topic      = scored["topic"]
    verdict    = scored.get("recommendation", "WATCH")
    stage      = scored.get("stage", "Unknown")
    hours      = scored.get("hours_since_emergence", "?")
    growth     = scored.get("google_growth")
    velocity   = scored.get("velocity") or 0
    score      = scored.get("ipo_score", 0)
    mispricing = scored.get("mispricing") or 0
    forum_price= scored.get("forum_price", 50)
    forum_chg  = scored.get("forum_change_pct")
    components = scored.get("score_components", {})

    g_str = f"+{growth:.1f}%" if growth and growth >= 0 else (f"{growth:.1f}%" if growth else "unavailable")
    chg_str = f"+{forum_chg:.1f}%" if forum_chg and forum_chg >= 0 else (f"{forum_chg:.1f}%" if forum_chg else "flat")

    return f"""You are a sharp analyst for Forum, an attention market where internet trends trade like stocks.

Analyze "{topic}" and return a JSON object with exactly these 4 keys:

{{
  "driving_force": "2-3 sentences on WHAT is making this trend happen right now. Be specific — mention events, context, or cultural reasons if you know them. If you don't know specifics, explain the pattern the data shows.",
  "forum_opportunity": "2-3 sentences on WHY this is an opportunity (or not) on Forum specifically. Reference the price, mispricing gap, and timing window. Be concrete.",
  "risks": "2 sentences on what could make this miss. What would cause this trend to fizzle before Forum prices it in?",
  "bottom_line": "1 punchy sentence. A specific, confident action: what should the reader do right now?"
}}

Data:
- Topic: {topic}
- IPO Score: {score:.1f}/100
- Verdict: {verdict}
- Stage: {stage} (~{hours}h since emergence)
- Google Trends growth: {g_str}
- Velocity (acceleration): {velocity:.1f}
- Forum price: {forum_price:.0f}
- Forum 24h change: {chg_str}
- Attention mispricing: {mispricing:+.1f} (positive = underpriced on Forum)
- Score breakdown: growth={components.get('growth_component', '?')}, velocity={components.get('velocity_component', '?')}, recency={components.get('recency_component', '?')}, mispricing={components.get('mispricing_component', '?')}, saturation_penalty=-{components.get('saturation_penalty', '?')}

Return ONLY the JSON object. No markdown, no explanation outside the JSON."""


def _deep_analyze_anthropic(scored: dict) -> dict:
    try:
        import anthropic, json as _json
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=ANTHROPIC_MAIN_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": _build_deep_prompt(scored)}],
        )
        text = msg.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return _json.loads(text)
    except Exception as e:
        print(f"[summarizer] deep anthropic error: {e}")
        return _deep_analyze_fallback(scored)


def _deep_analyze_openai(scored: dict) -> dict:
    try:
        from openai import OpenAI
        import json as _json
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_MAIN_MODEL,
            messages=[{"role": "user", "content": _build_deep_prompt(scored)}],
            max_tokens=600,
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        return _json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[summarizer] deep openai error: {e}")
        return _deep_analyze_fallback(scored)


def _deep_analyze_fallback(scored: dict) -> dict:
    topic      = scored["topic"]
    verdict    = scored.get("recommendation", "WATCH")
    stage      = scored.get("stage", "Unknown")
    hours      = scored.get("hours_since_emergence", 12.0)
    growth     = scored.get("google_growth")
    velocity   = scored.get("velocity") or 0
    mispricing = scored.get("mispricing") or 0
    forum_price= scored.get("forum_price", 50)
    score      = scored.get("ipo_score", 0)
    components = scored.get("score_components", {})

    # Driving force
    if growth and growth > 100:
        driving = (f"{topic} is seeing a surge in Google search interest with {growth:.0f}% growth. "
                   f"This kind of spike typically signals a breaking news event, viral moment, or sudden cultural relevance. "
                   f"{'The acceleration is still climbing, suggesting the peak hasn\\'t hit yet.' if velocity > 2 else 'The momentum appears to be in early stages.'}")
    elif growth and growth > 30:
        driving = (f"{topic} is building steady traction on Google Trends with {growth:.0f}% growth. "
                   f"This is organic interest accumulating rather than a single viral spike — "
                   f"{'the velocity suggests momentum is accelerating.' if velocity > 1 else 'growth is gradual and consistent.'}")
    else:
        driving = (f"{topic} is showing up in trending data, though Google Trends signal is limited. "
                   f"Forum market momentum and pricing data suggest there is real attention behind this. "
                   f"The {stage} stage classification puts it in early discovery territory.")

    # Forum opportunity
    if mispricing > 15:
        opportunity = (f"This is the clearest signal: attention on {topic} is running well ahead of its Forum price of {forum_price:.0f}. "
                       f"A mispricing gap of {mispricing:+.0f} points means the market hasn't caught up yet. "
                       f"With {hours:.0f}h elapsed and still in the {stage} window, there's meaningful upside before price discovery closes the gap.")
    elif mispricing > 5:
        opportunity = (f"Forum price of {forum_price:.0f} is slightly behind where attention is tracking. "
                       f"The {mispricing:+.0f} point gap isn't huge, but combined with the {stage} timing, "
                       f"there's room for appreciation if the trend continues to accelerate.")
    elif mispricing < -10:
        opportunity = (f"Forum has already run ahead of the underlying attention at price {forum_price:.0f}. "
                       f"The market has priced in optimism that Google Trends data doesn't fully support yet. "
                       f"Entry here means paying a premium — you'd need strong continued growth to justify it.")
    else:
        opportunity = (f"Forum price of {forum_price:.0f} is roughly aligned with the attention signal. "
                       f"There's no glaring mispricing edge here — the opportunity is in the trend growth "
                       f"itself rather than a pricing inefficiency.")

    # Risks
    if stage in ("Public", "Pre-IPO"):
        risks = (f"At {hours:.0f}h, this trend is entering late-stage territory where most early gains have been made. "
                 f"If the triggering event resolves or the news cycle moves on, interest could drop sharply before the market reacts.")
    else:
        risks = (f"Early-stage trends can spike and fade quickly — if the underlying event is a one-day story, "
                 f"Google Trends interest could normalize within 24h. "
                 f"Forum liquidity on newer topics can also be thin, making exits harder.")

    # Bottom line
    if verdict == "STRONG BUY":
        bottom = f"Get in now — {topic} is in the sweet spot of high growth, early timing, and Forum underpricing."
    elif verdict == "BUY":
        bottom = f"This is a solid entry on {topic} — momentum and pricing both favor a position here."
    elif verdict == "WATCH":
        bottom = f"Set an alert on {topic} and wait for a clearer breakout signal before committing."
    else:
        bottom = f"Pass on {topic} for now — the risk/reward doesn't justify entry at this stage."

    return {
        "driving_force": driving,
        "forum_opportunity": opportunity,
        "risks": risks,
        "bottom_line": bottom,
    }
