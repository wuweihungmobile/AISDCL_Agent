"""Compute current source_sha256 for plugins/token_guard (SD_09 W3 audit helper)."""
from __future__ import annotations

import hashlib
from pathlib import Path


def main() -> None:
    h = hashlib.sha256()
    files = []
    # key= 不可省（R81 XPL-S1-06）：裸 `sorted(Path)` 比的是 `PurePath._str_normcase`，
    # Windows 走 case-fold、POSIX 走原字元序 ⇒ 檔名一旦有大小寫混排，同一批位元組會在
    # 兩平台算出不同的 sha，而這個 sha 正是 mutation baseline lock 的 `source_sha256`。
    root = Path("autoclaude/plugins/token_guard")
    for p in sorted(root.rglob("*.py"), key=lambda q: q.as_posix()):
        if "__pycache__" in str(p):
            continue
        files.append(p)
        h.update(p.read_bytes())
    print("files:", [str(p) for p in files])
    print("current_sha256_full:", h.hexdigest())
    print("truncated_16:", h.hexdigest()[:16])


if __name__ == "__main__":
    main()
