"""ADR-SD09-010 §5 W1 — mutmut counts marker section SSOT helper（紀律 #4 / #5）。

ps1 line 337-358 mutation counts parsing 之 Python pure-function 同構樣板（SSOT）。
Round 4 P0-AUDIT-R3-3 真實迴歸實證有風險 → 強制 ≥ 6 case unit test 覆蓋。
ps1 邏輯變動須同步更新本 helper + 重跑 tests/tools/test_mutmut_counts_parser.py。
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_COUNTS_BEGIN_MARKER = re.compile(
    r"^---\s*mutmut full counts(?!\s*\(end\))[^\n]*---\s*$", re.IGNORECASE
)
_COUNTS_END_MARKER = re.compile(r"^---\s*mutmut full counts\s*\(end\)\s*---\s*$", re.IGNORECASE)
_COUNTS_LINE = re.compile(r"^(Killed|Survived|Timeout|Suspicious|Skipped)\b[^\(]*\((\d+)\)")


@dataclass(frozen=True)
class MutmutCountsResult:
    """ps1 line 337-358 解析結果。

    對應 4 條件分支：
      - section_found=True + emitted=5 → 正常 OK
      - section_found=True + emitted<5 → 部分 counts 缺失（理論上 mutmut 5 type 全列）
      - section_found=False → 無 marker → WARN（ps1 line 360）
      - 任何 case emitted=0 → 無 counts → WARN
    """

    counts: dict[str, int] = field(default_factory=dict)  # 5 type → 數量
    emitted: int = 0                                       # 實際命中的 counts line 數
    section_found: bool = False                            # 是否找到 marker section
    warning: str | None = None                             # 0 emit 時的 WARN 訊息
    formatted_lines: tuple[str, ...] = field(default_factory=tuple)  # ps1 端 `[mutation counts] X` 行


def parse_mutmut_counts(log_text: str) -> MutmutCountsResult:
    """解析 mutmut log 內 marker section 的 5 行 counts。

    對齊 ps1 line 337-358 邏輯：
      1. 逐行掃描，遇 begin marker 啟動 section
      2. 在 section 內匹配 5 type counts line（Killed/Survived/Timeout/Suspicious/Skipped）
      3. 遇 end marker 結束（break）
      4. emitted=0 → WARN 訊息（ps1 line 360）
    """
    counts: dict[str, int] = {}
    formatted: list[str] = []
    in_section = False
    section_found = False
    for line in log_text.splitlines():
        if not in_section and _COUNTS_BEGIN_MARKER.match(line):
            in_section = True
            section_found = True
            continue
        if in_section and _COUNTS_END_MARKER.match(line):
            break
        if in_section:
            m = _COUNTS_LINE.match(line.strip())
            if m:
                kind = m.group(1)
                counts[kind.lower()] = int(m.group(2))
                formatted.append(f"[mutation counts] {line.strip()}")
    emitted = len(formatted)
    warning = None
    if emitted == 0:
        warning = "no marker section found in mutation log (ADR-SD09-010 W1 / P0-AUDIT-R3-3)"
    return MutmutCountsResult(
        counts=counts,
        emitted=emitted,
        section_found=section_found,
        warning=warning,
        formatted_lines=tuple(formatted),
    )


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：解析 log → 印 ps1 等價 `[mutation counts] X` 行至 stdout；WARN 至 stderr。"""
    parser = argparse.ArgumentParser(description="Parse mutmut counts marker section (ADR-SD09-010)")
    parser.add_argument("log", type=Path, help="mutmut results log path")
    args = parser.parse_args(argv)
    if not args.log.exists():
        sys.stderr.write(f"[mutmut_counts_parser] ERROR: log not found: {args.log}\n")
        return 1
    text = args.log.read_text(encoding="utf-8", errors="replace")
    result = parse_mutmut_counts(text)
    for line in result.formatted_lines:
        print(line)
    if result.warning:
        sys.stderr.write(f"[mutmut_counts_parser] WARN: {result.warning}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
