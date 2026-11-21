"""OIR 掃描器（M0，唯讀；DES §3.5、REQ-WP-04）。

對 `scan_globs` 命中的檔跑 `marker_regex`，逐行報告每處標記是否帶 `OI-YYYYMMDD-NNN`。
`vocabulary_definers` 名單內的檔不判（詞彙的定義文件，不是待驗的使用處）。
`immutable_records`（選填 glob）命中的檔也不判：那是逐字封存的歷史紀錄
（SI 觀察帳本既有列、四問審視答案檔），改一個字就破壞列雜湊或答案檔雜湊，
措辭是歷史事實、不是現行待驗項。每個含標記的行算一處（一行多個標記仍算一處）。
檔案母體＝git 追蹤的檔（quotepath 安全，取數層＝`lib.git_paths`）；
不在 git 工作樹內時退回走檔案系統（沙盒、單元測試用）。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from lib import git_paths

OI_RE = re.compile(r"OI-\d{8}-\d{3,}")
_PRUNE = {".git", "node_modules", ".venv", "venv", "__pycache__"}


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    mapped: bool
    text: str


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """`**/` 跨目錄（含零層）、`*` 不跨 `/`、`?` 一個非 `/` 字元；其餘字面。"""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def candidate_files(root: Path) -> list[str]:
    """repo 相對（正斜線）的檔案母體：git 追蹤檔；不是 git 工作樹（rc≠0）時走檔案系統。"""
    proc = git_paths.run(root, "ls-files")
    if proc.returncode == 0:
        return [ln for ln in proc.stdout.splitlines() if ln]
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _PRUNE]
        found += [(Path(base) / f).relative_to(root).as_posix() for f in files]
    return sorted(found)


def scan(root: Path, params: dict, files: list[str] | None = None) -> list[Hit]:
    root = Path(root)
    globs = [glob_to_regex(g) for g in params["scan_globs"]]
    definers = {d.replace("\\", "/") for d in params["vocabulary_definers"]}
    immutable = [glob_to_regex(g) for g in params.get("immutable_records", [])]
    marker = re.compile(params["marker_regex"])
    hits: list[Hit] = []
    for rel in sorted(files if files is not None else candidate_files(root)):
        if rel in definers or not any(g.match(rel) for g in globs):
            continue
        if any(g.match(rel) for g in immutable):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue  # 追蹤中但工作樹已刪：不是標記，略過
        for lineno, line in enumerate(text.splitlines(), start=1):
            if marker.search(line):
                hits.append(Hit(rel, lineno, bool(OI_RE.search(line)), line.strip()[:160]))
    return hits


def summary_line(hits: list[Hit]) -> str:
    mapped = sum(1 for h in hits if h.mapped)
    return f"OPENITEMS_SCAN=mapped={mapped} unmapped={len(hits) - mapped}"
