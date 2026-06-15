"""SDD_FSM_ENGINE.md 狀態轉換表的共用解析器（單一真實來源）。

由 `tests/test_md_python_sync.py`（happy-path 同步測試）與 `arch_fitness` FF-1
（三源一致性適應度函式，roadmap R2）共用。把 MD 解析集中在這裡，避免兩份各自
漂移的 parser —— 那本身就是一個 FF-1 型（多源手動同步）脆弱點。

慣例（沿用 ACT-022）：
- 僅解析 `## ... 狀態轉換表` 區段，邊界以下一個 H2 標題判定（非 ``---``，因其與
  markdown 表格分隔列衝突）。
- 來源欄取第一個 ALL_CAPS state token；目標欄取所有 ALL_CAPS token（可複合，如
  ``HUMAN_PENDING（...）``）。
- 來源為「任意狀態」者不描述具體 source，跳過。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
FSM_ENGINE_MD = FRAMEWORK_ROOT / "workflow" / "sdd-fsm-engine" / "SDD_FSM_ENGINE.md"

STATE_TOKEN = re.compile(r"[A-Z][A-Z0-9_]{2,}")

# 出現在 happy-path 表、但在 Python 被建模為 emergency/terminal（轉換為全域允許、
# 不在 _HAPPY_PATH）的目標。
_EMERGENCY_TARGETS_IN_MD = {
    "ESCALATION",
    "TERMINATED",
    "TOKEN_BUDGET_CRITICAL",
    "AUTO_COMPACT_PENDING",
}


def _extract_state_token(text: str):
    """Return the first ALL_CAPS state token or None."""
    m = STATE_TOKEN.search(text)
    return m.group(0) if m else None


def _extract_all_state_tokens(text: str):
    """Return every ALL_CAPS state token in the cell (ordered)."""
    return STATE_TOKEN.findall(text)


def parse_md_transitions(md_path: Path = FSM_ENGINE_MD):
    """Extract happy-path + error-path arrows from the markdown tables.

    Returns a dict src -> set(dst). Only ALL_CAPS state tokens are kept.
    """
    md_path = Path(md_path)
    if not md_path.exists():
        raise FileNotFoundError(f"FSM engine MD not found: {md_path}")
    text = md_path.read_text(encoding="utf-8")
    start_match = re.search(r"^##\s+.*狀態轉換表", text, flags=re.MULTILINE)
    if not start_match:
        raise RuntimeError("cannot locate 狀態轉換表 section in SDD_FSM_ENGINE.md")
    start = start_match.start()
    after = text[start_match.end():]
    next_h2 = re.search(r"^##\s+", after, flags=re.MULTILINE)
    end = start_match.end() + next_h2.start() if next_h2 else len(text)
    section = text[start:end]

    transitions: dict[str, set[str]] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if stripped.startswith("| 來源"):
            continue
        if re.match(r"^\|[\s:\-|]+\|\s*$", stripped):
            continue
        parts = [p.strip() for p in stripped.split("|")]
        parts = [p for p in parts if p != ""]
        if len(parts) < 3:
            print(
                f"[WARN] parse_md_transitions: skip malformed row (cells={len(parts)}): {line!r}",
                file=sys.stderr,
            )
            continue
        src_cell, _cond_cell, dst_cell = parts[0], parts[1], parts[2]
        if "任意狀態" in src_cell:
            continue
        src = _extract_state_token(src_cell)
        dsts = _extract_all_state_tokens(dst_cell)
        if not src or not dsts:
            continue
        for dst in dsts:
            transitions.setdefault(src, set()).add(dst)
    return transitions


def filter_to_happy_path(md_transitions):
    """Exclude edges whose destination is an emergency/terminal target."""
    filtered: dict[str, set[str]] = {}
    for src, dsts in md_transitions.items():
        kept = {d for d in dsts if d not in _EMERGENCY_TARGETS_IN_MD}
        if kept:
            filtered[src] = kept
    return filtered


def md_source_states(md_path: Path = FSM_ENGINE_MD):
    """轉換表的所有來源狀態 token（單一、結構乾淨的欄位）。"""
    return set(parse_md_transitions(md_path).keys())


def md_state_universe(md_path: Path = FSM_ENGINE_MD):
    """轉換表出現的所有狀態 token（來源 ∪ 目標）。"""
    md = parse_md_transitions(md_path)
    dst = set().union(*md.values()) if md else set()
    return set(md.keys()) | dst
