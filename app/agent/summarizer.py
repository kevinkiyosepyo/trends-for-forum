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
    stage = scored.get("stage", "Unknown")
    hours = scored.get("hours_since_emergence", "?")
    g_str = _fmt_pct(scored.get("google_growth"))
    verdict = scored.get("recommendation", "WATCH")
    sig = signal_label(scored.get("ipo_score") or 0)
    forum_available = scored.get("forum_available", False)
    g_failed = scored.get("source_health", {}).get("google") == "failed"

    data_note = " (Google rate-limited — using Forum momentum)" if g_failed else ""
    forum_note = (
        f"Forum price {scored.get('forum_price', '?'):.0f} ({'live' if forum_available else 'est.'}) — "
        f"{'underpriced' if (scored.get('mispricing') or 0) > 10 else 'fairly priced'}."
    )

    return (
        f"{scored['topic']} is a {stage}-stage trend with {sig} momentum{data_note}. "
        f"Google Trends: {g_str}, emerged ~{hours}h ago. "
        f"{forum_note} Verdict: {verdict}."
    )
