"""Quick CLAUDE.md long-line check (codepoint-based)."""
from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("CLAUDE.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    viol = [(i + 1, len(line)) for i, line in enumerate(lines) if len(line) > 800]
    print("violations:", viol)
    print("line 4 codepoints:", len(lines[3]))
    print("total lines:", len(lines))


if __name__ == "__main__":
    main()
