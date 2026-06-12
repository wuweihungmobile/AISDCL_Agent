#!/usr/bin/env python
"""PostToolUse(Edit|Write) 事件 — 對剛修改的檔案做 LOC 預算檢查。

對應 ADR-SD07-001（LOC 分級政策）+ ADR-SD08-001（CLAUDE.md ≤ 400）。

行為：
  - 非 .py / 非 CLAUDE.md → exit 0
  - .py 檔超 tier budget → stderr warn（exit 1，不阻斷）
  - .py 檔超絕對紅線 750 → stderr warn（exit 1）
  - CLAUDE.md > 400 行 → stderr error（exit 2，阻斷）

複用 tools/check_loc_budget.py 的 LOC_TIERS / classify_file / count_loc / count_raw_lines。
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path


def _init_utf8_streams() -> None:
    """Windows console UTF-8；只在 __main__ 觸發，避免污染 pytest stdout/stderr。"""
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

try:
    from check_loc_budget import (  # type: ignore[import-not-found]
        ABSOLUTE_LIMIT,
        SPECIAL_FILES,
        classify_file,
        count_loc,
        count_raw_lines,
    )
except ImportError as exc:  # pragma: no cover — 安全 fallback
    print(f"[loc_budget_check] 無法 import check_loc_budget：{exc}", file=sys.stderr)
    sys.exit(0)


def read_hook_payload() -> dict:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def normalize_rel_path(file_path: str) -> Path | None:
    if not file_path:
        return None
    try:
        p = Path(file_path)
        if p.is_absolute():
            return p.resolve().relative_to(PROJECT_ROOT)
        return p
    except (ValueError, OSError):
        return None


def check_python_file(rel: Path) -> int:
    abs_path = PROJECT_ROOT / rel
    if not abs_path.exists():
        return 0
    loc = count_loc(abs_path)
    tier, budget = classify_file(rel)
    if loc > ABSOLUTE_LIMIT:
        print(
            f"[loc_budget_check] WARN: '{rel.as_posix()}' loc={loc} 超絕對紅線 {ABSOLUTE_LIMIT}（ADR-SD07-001）。",
            file=sys.stderr,
        )
        return 1
    if loc > budget:
        print(
            f"[loc_budget_check] WARN: '{rel.as_posix()}' loc={loc} 超 tier '{tier}' budget {budget}（ADR-SD07-001）。",
            file=sys.stderr,
        )
        return 1
    return 0


def check_special_file(rel: Path) -> int:
    """CLAUDE.md / Migration SOP / sprint_history — 走 raw line count。

    SD_09 R18 抗膨脹保險 #3：CLAUDE.md ≥ (max_lines - 20) 印 WARN（不阻斷），讓 user
    在撞紅線前看到「剩 ≤ 20 行 buffer」預警，被動觸發「該下沉了」意識。
    """
    rel_posix = rel.as_posix()
    max_lines = SPECIAL_FILES.get(rel_posix)
    if max_lines is None:
        return 0
    abs_path = PROJECT_ROOT / rel
    if not abs_path.exists():
        return 0
    actual = count_raw_lines(abs_path)
    if actual > max_lines:
        print(
            f"[loc_budget_check] BLOCK: '{rel_posix}' 行數 {actual} > 上限 {max_lines}"
            f"（ADR-SD08-001 §3.1）。請精簡或拆分至 docs/05_development/。",
            file=sys.stderr,
        )
        return 2
    # 預警閾值：max_lines - 20（如 CLAUDE.md ≤ 400 → ≥ 380 印 WARN）
    warn_threshold = max_lines - 20
    if actual >= warn_threshold:
        remaining = max_lines - actual
        print(
            f"[loc_budget_check] WARN: '{rel_posix}' 行數 {actual} ≥ 預警閾值 {warn_threshold} "
            f"（紅線 {max_lines}；剩 {remaining} 行 buffer）。請考慮下沉至 docs/05_development/sprint_history.md "
            f"§1.x（W 期間骨架先行 SOP）或對應 docs/06_quality/。",
            file=sys.stderr,
        )
        # 預警不阻斷（rc=1 同 .py tier warn 語意）
        return 1
    return 0


def main() -> int:
    payload = read_hook_payload()
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        return 0

    rel = normalize_rel_path(file_path)
    if rel is None:
        return 0

    # 1) Special files（CLAUDE.md 等）優先於 .py 檢查；rc=2 阻斷 / rc=1 預警不阻斷
    rc = check_special_file(rel)
    if rc == 2:
        return 2
    if rc == 1:
        # 預警；繼續走 .py 檢查（理論上 .md 不會走到，但保險起見）
        pass

    # 2) Python 檔 tier 檢查（warn-only）
    if rel.suffix == ".py":
        return check_python_file(rel)

    return rc


if __name__ == "__main__":
    _init_utf8_streams()
    sys.exit(main())
