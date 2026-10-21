"""SelfImproving 檔案樹 manifest（TCS-SelfImproving-P2 R84）：沙盒、held-out、pre／post 共用。

manifest 文字＝逐檔一行 `<posix 相對路徑，保留原大小寫>\t<hex 或 absent>\n`，依路徑的 UTF-8
位元組序排序，整體取 sha256 並加 `sha256:` 前綴。兩式：**原始位元組式**（每檔 sha256 原始位元組；
`sandbox_sha256` 與 held-out `digest` 用，機器本地證據、不跨機比對）與 **LF 正規化式**（每檔先
CRLF→LF 再 sha256，指名路徑缺檔記 `absent`；`pre_sha256`、`post_sha256` 用，使兩平台工作樹與 M 類
記憶檔得同一值）。只讀、純標準庫。
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

WIN_PATH_MAX = 259


def _digest(lines: list[tuple[str, str]]) -> str:
    text = "".join(f"{rel}\t{val}\n" for rel, val in sorted(lines, key=lambda x: x[0].encode()))
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def tree_files(root: Path) -> list[str]:
    """目錄樹下全部一般檔的 posix 相對路徑（遞迴；不含空目錄）。"""
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def tree_manifest(root: Path) -> str:
    """原始位元組式：目錄樹下全部一般檔。"""
    return _digest([(rel, hashlib.sha256((root / rel).read_bytes()).hexdigest())
                    for rel in tree_files(root)])


def paths_manifest(root: Path, paths, *, lf: bool = True, strip: str = "") -> str:
    """指名路徑的 manifest；`lf` 真＝LF 正規化式，假＝原始位元組式；缺檔一律記 `absent`。
    `strip`＝邏輯根前綴（M 類 `memory/`）：檔案取自去掉前綴後的路徑，manifest 仍記邏輯名。"""
    out = []
    for rel in sorted(set(paths)):
        p = root / (rel[len(strip):] if strip and rel.startswith(strip) else rel)
        if not p.is_file():
            out.append((rel, "absent"))
            continue
        raw = p.read_bytes()
        out.append((rel, hashlib.sha256(raw.replace(b"\r\n", b"\n") if lf else raw).hexdigest()))
    return _digest(out)


def path_too_long(root: Path, names) -> str | None:
    """Windows：`len(根)＋1＋最長成員相對路徑` 大於 259 ⇒ 回說明；POSIX 或未超限回 None。"""
    if not sys.platform.startswith("win"):
        return None
    longest = max((len(n) for n in names), default=0)
    total = len(str(root)) + 1 + longest
    return f"{total} > {WIN_PATH_MAX}" if total > WIN_PATH_MAX else None
