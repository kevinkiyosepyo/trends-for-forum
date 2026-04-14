#!/usr/bin/env python3
"""
Trends for Forum — terminal demo.

Usage:
  python scripts/run_agent_once.py
  python scripts/run_agent_once.py --topics "AI agents" "Claude"
  python scripts/run_agent_once.py --forum-discover
"""

import sys
import argparse

sys.path.insert(0, __file__.rsplit("/scripts", 1)[0])

from app.utils.env_check import validate_env
from app.agent.orchestrator import run_agent, run_from_forum_markets

C = {
    "STRONG BUY":        "\033[92m\033[1m",
    "BUY":               "\033[92m",
    "WATCH":             "\033[93m",
    "AVOID":             "\033[91m",
    "INSUFFICIENT DATA": "\033[90m",
    "RESET": "\033[0m",
    "BOLD":  "\033[1m",
    "DIM":   "\033[2m",
    "CYAN":  "\033[96m",
    "GRAY":  "\033[90m",
}

STAGE_ICONS = {"Seed": "🌱", "Series A": "🚀", "Pre-IPO": "📈", "Public": "📊"}

SOURCE_ICONS = {
    "google":         "📡 Google Trends",
    "forum_momentum": "⚡ Forum momentum",
    "none":           "❌ no signal",
}


def _bar(score: float, width: int = 20) -> str:
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _fmt(v, suffix="%"):
    if v is None:
        return C["GRAY"] + "n/a" + C["RESET"]
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}{suffix}"


def print_result(r: dict, rank: int):
    verdict = r.get("recommendation", "WATCH")
    color = C.get(verdict, "")
    reset = C["RESET"]
    bold = C["BOLD"]
    dim = C["DIM"]
    cyan = C["CYAN"]

    stage = r.get("stage", "?")
    icon = STAGE_ICONS.get(stage, "")
    score = r.get("ipo_score", 0)
    hours = r.get("hours_since_emergence", "?")
    ticker = f"  [{r['ticker']}]" if r.get("ticker") else ""
    primary = SOURCE_ICONS.get(r.get("primary_signal", "none"), "")
    conf = r.get("confidence_score", 0)

    health = r.get("source_health", {})
    src_line = "  ".join(
        f"{k}:{'✓' if v in ('ok', 'live') else ('~' if v == 'stub' else '✗')}"
        for k, v in health.items()
    )

    print(f"\n{bold}#{rank}  {r['topic']}{ticker}{reset}")
    print(f"  {color}{bold}{verdict}{reset}  │  IPO Score: {score:.1f}/100  [{_bar(score)}]  {dim}Conf: {conf:.0f}%{reset}")
    print(f"  {icon} Stage: {stage}  │  ~{hours}h ago  │  Forum: {r.get('forum_price', '?'):.0f}  │  Δ24h: {_fmt(r.get('forum_change_pct'))}")
    print(f"  {cyan}Google: {_fmt(r.get('google_growth'))}  Velocity: {r.get('velocity', 0):.1f}  Mispricing: {_fmt(r.get('mispricing'), suffix='')}{reset}")
    print(f"  {dim}Signal: {primary}  │  Sources: {src_line}{reset}")
    print(f"  {r.get('explanation', '')}")


def main():
    parser = argparse.ArgumentParser(description="Trends for Forum")
    parser.add_argument("--topics", nargs="+", default=None)
    parser.add_argument("--forum-discover", action="store_true",
                        help="Pull topics from live Forum markets by volume")
    args = parser.parse_args()

    print(f"\n{'═'*62}")
    print(f"  {'TRENDS FOR FORUM':^58}")
    print(f"  {'Attention IPO Ranker  ×  Forum (YC W26)':^58}")
    print(f"{'═'*62}")

    validate_env(verbose=True)
    print("Scanning signals...\n")

    results = run_from_forum_markets(top_n=8) if args.forum_discover else run_agent(topics=args.topics)

    for i, r in enumerate(results, 1):
        print_result(r, i)

    print(f"\n{'═'*62}")
    actionable = [r for r in results if r.get("recommendation") in ("STRONG BUY", "BUY")]
    if actionable:
        top = actionable[0]
        print(f"  TOP PICK:  {top['topic']}  →  {top['recommendation']}")
        print(f"  Stage: {top.get('stage')}  │  Score: {top.get('ipo_score', 0):.1f}  │  {SOURCE_ICONS.get(top.get('primary_signal', 'none'), '')}")
    else:
        print("  No strong buys right now. Add Forum API keys for live market data.")
    print(f"{'═'*62}\n")


if __name__ == "__main__":
    main()
