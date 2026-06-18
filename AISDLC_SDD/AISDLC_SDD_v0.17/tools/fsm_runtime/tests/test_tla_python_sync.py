# enforces (governance rules): R-9.18
"""Phase G M5 / QA 修 2 — TLA+ ↔ transition_rules.py 雙源一致性 enforce.

對應 CLAUDE.md Rule 9.18.1：每次 _HAPPY_PATH 變更必須同步更新 SDD_FSM.tla。
本測試由 CI base layer 觸發，把「事後值偵測（reachable 數異常）」升級為
「事前結構偵測（pair-by-pair sync check）」。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from tools.fsm_runtime.transition_rules import (
    AUTO_COMPACT_SOURCES,
    OBSERVATION_STATES,
    _EMERGENCY_TARGETS,
    _HAPPY_PATH,
)

ROOT = Path(__file__).resolve().parent.parent
TLA_PATH = ROOT / "formal" / "SDD_FSM.tla"


# ---------------------------------------------------------------------------
# .tla 解析 — best-effort regex（不依賴 TLA+ AST）
# ---------------------------------------------------------------------------


def _read_tla() -> str:
    return TLA_PATH.read_text(encoding="utf-8")


def _named_sets(tla_text: str) -> dict[str, frozenset[str]]:
    """抽出 `NAME == { "X", "Y", ... }` 形式的命名集合（multi-line 容忍）。"""
    out: dict[str, frozenset[str]] = {}
    for m in re.finditer(r"^([A-Z][A-Za-z_]*)\s*==\s*\{([^}]+)\}", tla_text, re.MULTILINE):
        name = m.group(1)
        items = re.findall(r'"([A-Z_]+)"', m.group(2))
        if items:
            out[name] = frozenset(items)
    return out


def _resolve_set(expr: str, named: dict[str, frozenset[str]]) -> set[str]:
    """解析 set 表達式（inline / named / A \\cup B）。"""
    e = expr.strip().strip("()").strip()
    if e.startswith("{"):
        return set(re.findall(r'"([A-Z_]+)"', e))
    if r"\cup" in e:
        result: set[str] = set()
        for part in re.split(r"\\cup", e):
            result |= _resolve_set(part, named)
        return result
    if e in named:
        return set(named[e])
    return set()


def _extract_pairs(tla_text: str) -> set[tuple[str, str]]:
    """抽出所有 (src, dst) state transition pair。"""
    pairs: set[tuple[str, str]] = set()
    sets = _named_sets(tla_text)

    # 1) Move("X","Y") / JumpKeep("X","Y") / GateRetry("X","Y")
    for m in re.finditer(
        r"\b(?:Move|JumpKeep|GateRetry)\(\s*\"([A-Z_]+)\"\s*,\s*\"([A-Z_]+)\"\s*\)",
        tla_text,
    ):
        pairs.add((m.group(1), m.group(2)))

    # 2) GateExhaust("X") → (X, ESCALATION)
    for m in re.finditer(r"\bGateExhaust\(\s*\"([A-Z_]+)\"\s*\)", tla_text):
        pairs.add((m.group(1), "ESCALATION"))

    # 3) Operator blocks: T_Foo == <body> 直到下一個 T_ 或區塊註解
    block_re = re.compile(
        r"^(T_[A-Za-z_]+)\s*==\s*((?:.|\n)*?)(?=\n(?:T_[A-Za-z_]+\s*==|\(\*\*+|====|---))",
        re.MULTILINE,
    )
    for m in block_re.finditer(tla_text):
        body = m.group(2)

        # Pattern A: \E src \in <set_expr> : ... state' = "DST"
        a = re.search(r"\\E\s+src\s+\\in\s+(.+?)\s*:\s*((?:.|\n)+)", body, re.DOTALL)
        if a:
            src_set = _resolve_set(a.group(1), sets)
            d = re.search(r"state'\s*=\s*\"([A-Z_]+)\"", a.group(2))
            if d:
                for s in src_set:
                    pairs.add((s, d.group(1)))
            continue

        # Pattern B: \E dst \in <set_expr> : ... state = "SRC"
        b = re.search(r"\\E\s+dst\s+\\in\s+(.+?)\s*:\s*((?:.|\n)+)", body, re.DOTALL)
        if b:
            dst_set = _resolve_set(b.group(1), sets)
            s = re.search(r"(?<!')\bstate\s*=\s*\"([A-Z_]+)\"", b.group(2))
            if s:
                for d in dst_set:
                    pairs.add((s.group(1), d))
            continue

        # Pattern C: 直接 state = "X" /\ ... /\ state' = "Y"
        s = re.search(r"(?<!')\bstate\s*=\s*\"([A-Z_]+)\"", body)
        d = re.search(r"state'\s*=\s*\"([A-Z_]+)\"", body)
        if s and d:
            pairs.add((s.group(1), d.group(1)))

    return pairs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _python_happy_pairs() -> set[tuple[str, str]]:
    return {(src, dst) for src, dsts in _HAPPY_PATH.items() for dst in dsts}


def test_tla_covers_every_happy_path_pair():
    """Rule 9.18.1: _HAPPY_PATH 中每條 (src, dst) 必須出現在 SDD_FSM.tla。

    豁免：dst ∈ _EMERGENCY_TARGETS 可由 .tla 中的 wildcard transition
    （例如 T_TokenCriticalEnter accepts HappyStates \\cup ObservationStates）
    覆蓋；只要 .tla 有任意一條進入該 dst 的 transition，即視為 covered。
    """
    tla_text = _read_tla()
    tla_pairs = _extract_pairs(tla_text)
    py_pairs = _python_happy_pairs()

    tla_dsts = {d for (_s, d) in tla_pairs}

    missing: list[tuple[str, str]] = []
    for src, dst in py_pairs:
        if (src, dst) in tla_pairs:
            continue
        if dst in _EMERGENCY_TARGETS and dst in tla_dsts:
            # 由 .tla 中的 emergency wildcard transition 覆蓋
            continue
        missing.append((src, dst))

    assert not missing, (
        f"Rule 9.18.1 violation: {len(missing)} (src, dst) pairs declared in "
        f"transition_rules._HAPPY_PATH 但 SDD_FSM.tla 沒有對應 transition。\n"
        f"漏失樣本（前 10 筆）: {sorted(missing)[:10]}"
    )


def test_all_python_states_declared_in_tla_state_sets():
    """每個 _HAPPY_PATH 涉及的 state 必須在 .tla 的 4 大集合
    （HappyStates / ObservationStates / EmergencyStates / Terminals）任一中宣告。
    """
    tla_text = _read_tla()
    sets = _named_sets(tla_text)

    tla_states: set[str] = set()
    for key in ("HappyStates", "ObservationStates", "EmergencyStates", "Terminals"):
        tla_states |= sets.get(key, set())

    py_states: set[str] = set(_HAPPY_PATH.keys()) | _EMERGENCY_TARGETS
    for dsts in _HAPPY_PATH.values():
        py_states |= dsts

    missing = py_states - tla_states
    assert not missing, (
        f"Rule 9.18.1 violation: {len(missing)} state(s) used in transition_rules "
        f"but not declared in SDD_FSM.tla state sets: {sorted(missing)}"
    )


def test_tla_extra_pairs_have_python_basis():
    """反向檢查：.tla 中每條 (src, dst) pair 應該能在 transition_rules 找到合法依據，
    避免 .tla 引入了 transition_rules 不允許的虛構 transition。

    合法依據（任一即可）：
    1. (src, dst) ∈ _HAPPY_PATH
    2. dst ∈ _EMERGENCY_TARGETS（emergency wildcard 由 runtime 守門）
    3. dst ∈ OBSERVATION_STATES ∪ {AUTO_COMPACT_PENDING}：透過 FSMRuntime.enter_X()
       runtime API 進入，繞過 _HAPPY_PATH（per transition_rules 註解設計）
    4. src == "AUTO_COMPACT_PENDING" 且 dst ∈ AUTO_COMPACT_SOURCES：.tla 模型容許
       完整 resume_state 集合作為退場目標（_HAPPY_PATH 為了 permissions 列得較窄，
       runtime 用 resume_state 守門精確值）
    """
    tla_text = _read_tla()
    tla_pairs = _extract_pairs(tla_text)
    py_pairs = _python_happy_pairs()

    runtime_entry_dsts = OBSERVATION_STATES | {"AUTO_COMPACT_PENDING"}

    extra: list[tuple[str, str]] = []
    for src, dst in tla_pairs:
        if (src, dst) in py_pairs:
            continue
        if dst in _EMERGENCY_TARGETS:
            continue
        if dst in runtime_entry_dsts:
            # 觀測態 / AUTO_COMPACT_PENDING 由 runtime API 進入
            continue
        if src == "AUTO_COMPACT_PENDING" and dst in AUTO_COMPACT_SOURCES:
            continue
        extra.append((src, dst))

    assert not extra, (
        f"Rule 9.18.1 violation: {len(extra)} (src, dst) pair(s) in SDD_FSM.tla "
        f"沒有在 transition_rules._HAPPY_PATH / _EMERGENCY_TARGETS / "
        f"OBSERVATION_STATES / AUTO_COMPACT_SOURCES 找到合法依據。\n"
        f"虛構 transition 樣本（前 10 筆）: {sorted(extra)[:10]}"
    )


# ---------------------------------------------------------------------------
# 離線可達性窮舉（本地機器驗證，無需 Java/TLC）— 把「推算 reachable=N/N」升級為
# 每次 pytest 強制的不變量。TLC（run_tlc）仍在 CI/有 Java 時做完整時序+計數器窮舉；
# 此處以 state-level BFS 提供零依賴的本地必要條件守門（Rule 9.18.3 reachable coverage）。
# ---------------------------------------------------------------------------


def _declared_states(sets) -> set[str]:
    out: set[str] = set()
    for k in ("HappyStates", "ObservationStates", "EmergencyStates", "Terminals"):
        out |= sets.get(k, set())
    return out


def test_all_declared_states_reachable_from_init_offline():
    """從 INIT 沿 SDD_FSM.tla 全部 transition BFS，必達所有宣告狀態（reachable=N/N=100%，
    無死狀態）。等價 TLC 的 reachable coverage，但零 Java 依賴、每次 pytest 強制。"""
    tla = _read_tla()
    pairs = _extract_pairs(tla)
    declared = _declared_states(_named_sets(tla))

    fwd: dict[str, set[str]] = {}
    for s, d in pairs:
        fwd.setdefault(s, set()).add(d)

    seen = {"INIT"}
    stack = ["INIT"]
    while stack:
        for nxt in fwd.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)

    dead = declared - seen
    assert not dead, (
        f"reachable coverage < 100%：從 INIT 不可達的死狀態 {sorted(dead)}"
    )


def test_every_state_can_reach_a_terminal_offline():
    """反向 BFS 自 Terminals，必覆蓋所有宣告狀態 — 任一狀態都能抵達
    {RELEASE, TERMINATED, ESCALATION_FINAL}。EventuallyTerminal 的結構必要條件
    （防無界停機），離線可驗。"""
    tla = _read_tla()
    pairs = _extract_pairs(tla)
    sets = _named_sets(tla)
    declared = _declared_states(sets)
    terminals = sets.get("Terminals", set())

    rev: dict[str, set[str]] = {}
    for s, d in pairs:
        rev.setdefault(d, set()).add(s)

    can_reach = set(terminals)
    stack = list(terminals)
    while stack:
        for prv in rev.get(stack.pop(), ()):
            if prv not in can_reach:
                can_reach.add(prv)
                stack.append(prv)

    stuck = declared - can_reach
    assert not stuck, (
        f"無法抵達任何 terminal 的狀態（潛在無界停機）：{sorted(stuck)}"
    )


@pytest.mark.tlc
def test_tlc_full_verification_opt_in():
    """完整 TLA+/TLC 窮舉（時序 + 計數器 + 4 safety invariant + 2 liveness）。

    opt-in：需 `SDD_RUN_TLC=1` 顯式啟用（避免拖慢 PR fast gate），且需 java + jar。
    未啟用/缺環境則 skip — 上方離線可達性不變量已提供常駐零依賴守門。
    """
    if os.environ.get("SDD_RUN_TLC") != "1":
        pytest.skip("set SDD_RUN_TLC=1 to run full TLC（離線可達性不變量已常駐守門）")
    from tools.fsm_runtime import tlc_runner as T
    if T.find_java() is None or not T.jar_path().exists():
        pytest.skip("java 或 tla2tools.jar 不存在（CI/有 jar 環境才跑完整 TLC）")
    res = T.run_tlc(depth=50)
    assert res["ok"], f"TLC 驗證失敗：{res.get('log_tail') or res.get('error')}"
    assert res["distinct"] > 0
