def truncate(text: str, max_len: int = 200) -> str:
    return text if len(text) <= max_len else text[:max_len].rstrip() + "..."


def fmt_pct(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def fmt_score(value: float) -> str:
    return f"{value:.1f}/100"
