import os


def validate_env(verbose: bool = True) -> dict[str, bool]:
    checks = {
        "FORUM_API_KEY": bool(os.getenv("FORUM_API_KEY")),
        "FORUM_API_SECRET": bool(os.getenv("FORUM_API_SECRET")),
        "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
    }

    if verbose:
        print("\n[env] Credential check:")
        for key, present in checks.items():
            print(f"  {key}: {'✓ set' if present else '✗ missing'}")

        if checks.get("ANTHROPIC_API_KEY"):
            print(f"  LLM: claude-opus-4-6 (Anthropic)")
        elif checks.get("OPENAI_API_KEY"):
            print(f"  LLM: gpt-4o (OpenAI)")
        else:
            print(f"  [warn] No LLM key set — rule-based summaries will be used")
        if not checks["FORUM_API_KEY"]:
            print("  [warn] No Forum API key — prices will be estimated")
        print()

    return checks
