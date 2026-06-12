"""Compute current source_sha256 for plugins/token_guard (SD_09 W3 audit helper)."""
from __future__ import annotations
import hashlib
from pathlib import Path


def main() -> None:
    h = hashlib.sha256()
    files = []
    for p in sorted(Path("autoclaude/plugins/token_guard").rglob("*.py")):
        if "__pycache__" in str(p):
            continue
        files.append(p)
        h.update(p.read_bytes())
    print("files:", [str(p) for p in files])
    print("current_sha256_full:", h.hexdigest())
    print("truncated_16:", h.hexdigest()[:16])


if __name__ == "__main__":
    main()
