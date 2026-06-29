import re


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]+", "", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def truncate(s: str, n: int) -> str:
    if n < 1:
        raise ValueError("n must be >= 1")
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"
