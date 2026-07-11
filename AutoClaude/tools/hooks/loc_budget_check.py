#!/usr/bin/env python
"""PostToolUse(Edit|Write) 事件 — 對剛修改的檔案做 LOC 預算檢查。

對應 ADR-SD07-001（LOC 分級政策）+ ADR-SD08-001（CLAUDE.md ≤ 400）。

行為：
  - 非 .py / 非 CLAUDE.md → exit 0
  - .py 檔超 tier budget → stderr warn（exit 1，不阻斷）
  - .py 檔超絕對紅線 750 → stderr warn（exit 1）
  - CLAUDE.md > 400 行 → stderr error（exit 2，阻斷）
  - CLAUDE.md 單行 > 800 codepoint → stderr error（exit 2，阻斷；流程改善 #10a）

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

# 對齊 tests/contract/test_claude_md_no_long_lines.py（MAX_LINE_CHARS=800，codepoint 計）
MAX_CLAUDE_MD_LINE_CHARS = 800

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
    # zh-TW Windows pipe 預設 cp950：裸 sys.stdin.read() 遇含中文的 UTF-8 payload 會拋
    # UnicodeDecodeError → 阻斷級 hook 靜默失效。改讀 bytes 端以 UTF-8+replace 解碼；
    # 無 buffer（如測試以 StringIO 替身）時回退文字端。
    stdin_buffer = getattr(sys.stdin, "buffer", None)
    if stdin_buffer is not None:
        raw = stdin_buffer.read().decode("utf-8", "replace").strip()
    else:
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
            f"[loc_budget_check] WARN: '{rel.as_posix()}' loc={loc} "
            f"超絕對紅線 {ABSOLUTE_LIMIT}（ADR-SD07-001）。",
            file=sys.stderr,
        )
        return 1
    if loc > budget:
        print(
            f"[loc_budget_check] WARN: '{rel.as_posix()}' loc={loc} "
            f"超 tier '{tier}' budget {budget}（ADR-SD07-001）。",
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
            f"（紅線 {max_lines}；剩 {remaining} 行 buffer）。"
            f"請考慮下沉至 docs/05_development/sprint_history.md "
            f"§1.x（W 期間骨架先行 SOP）或對應 docs/06_quality/。",
            file=sys.stderr,
        )
        # 預警不阻斷（rc=1 同 .py tier warn 語意）
        return 1
    return 0


def check_claude_md_line_length(rel: Path) -> int:
    """CLAUDE.md 單行 codepoint 上限檢查（流程改善 #10a；阻斷級 exit 2）。

    對齊 tests/contract/test_claude_md_no_long_lines.py（MAX_LINE_CHARS=800，`len(str)`
    codepoint 計，非 byte）。讓「累積敘事單行繞過 ≤ 400 行紅線」反模式在 edit 當下即被攔，
    而非僅在 pytest/CI 才失敗（根因：SD_09 R11-18 怪物段 / Improving_012 Phase 0 + F-A1
    Status 行 815cp 復發 — 編輯可過 hook 卻破 contract）。僅檢 root CLAUDE.md（與 contract
    test 同口徑；sprint_history.md 等累積敘事檔不受此單行限制）。
    """
    if rel.as_posix() != "CLAUDE.md":
        return 0
    abs_path = PROJECT_ROOT / rel
    if not abs_path.exists():
        return 0
    violations = [
        (i, len(line))
        for i, line in enumerate(abs_path.read_text(encoding="utf-8").splitlines(), start=1)
        if len(line) > MAX_CLAUDE_MD_LINE_CHARS
    ]
    if violations:
        detail = "; ".join(f"line {ln}={n}cp" for ln, n in violations[:5])
        print(
            f"[loc_budget_check] BLOCK: 'CLAUDE.md' 有 {len(violations)} 行 > "
            f"{MAX_CLAUDE_MD_LINE_CHARS} codepoint（{detail}）。累積敘事請下沉至 "
            f"docs/05_development/sprint_history.md §1.x（對齊 contract "
            f"test_claude_md_no_long_lines；流程改善 #10a）。",
            file=sys.stderr,
        )
        return 2
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
    # 1b) CLAUDE.md 單行 codepoint 上限（流程改善 #10a；與行數紅線同為阻斷級）
    if check_claude_md_line_length(rel) == 2:
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
