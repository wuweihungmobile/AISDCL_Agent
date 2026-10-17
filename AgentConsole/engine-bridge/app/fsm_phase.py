"""FSM `current_state` → 階段 `phase{name, order, blocking, observation}` 的純函式
（契約 v1.5 §3.1.5；G-13；D-115-08）。

來歷：這是 W4 dogfood（improving_115 §4.2 的標的 T-G）的產物——由真 claude haiku 依
TCS-TgPhase-20261017 的 FRD-lite 寫出，經 SCG-4 審查通過（審查表 0 項不符；14 個單行突變全數被測
試殺死），主控再搬進 Bridge。搬入時只做了：檔名與 import 路徑、型別標註、docstring、對映表改以唯
讀 `MappingProxyType` 包裝（內容與順序不變）、新增 `KNOWN_STATES`；演算法與對映表原樣保留。

判定順序（先命中者勝；契約 §3.1.5 逐條）：
  1. 不是字串、或為空白 → UNKNOWN（不做 strip：前後帶空白的合法狀態名也算不在表內）；
  2. 阻塞狀態 → BLOCKED／0，blocking=true；
  3. 觀測狀態（SDD 的 OBSERVATION_STATES）→ observation=true，name／order 取「回歸階段」；回歸點只
     能由執行期的 resume_state 決定者回 OBSERVATION／0；
  4. 過渡狀態 → TRANSIENT／0；
  5. 主路徑 → 八個階段之一（order 1～8，相鄰階段差 1）；
  其餘（不在表內）→ UNKNOWN。
任何輸入都不拋例外；無 I/O、無全域可變狀態、只用標準庫（NFR-001-1）。表的集合與 SDD LATEST 是否一
致由 tests/test_sdd_integration_parity.py 的 F-5 對拍守：SDD 新增狀態而這裡沒有對映 ⇒ 紅，而不是
靜默落到 UNKNOWN。
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import TypedDict


class SddFsmPhase(TypedDict):
    """回應裡 `phase` 的形狀（openapi `SddFsmPhase`）：恰這四個鍵。"""

    name: str
    order: int
    blocking: bool
    observation: bool


#: 主路徑：狀態 → (階段名, order)。order 沿主路徑單調不減、相鄰階段差 1。
_MAIN_PATH: Mapping[str, tuple[str, int]] = MappingProxyType({
    # order 1 INTAKE
    "INIT": ("INTAKE", 1),
    "SCENARIO_DETECT": ("INTAKE", 1),
    "AGENT_LOAD": ("INTAKE", 1),
    "INTENT_DECOMPOSITION": ("INTAKE", 1),
    "BACKLOG_PRIORITIZED": ("INTAKE", 1),
    # order 2 SPECIFICATION
    "SPEC_DRAFTING": ("SPECIFICATION", 2),
    "SCG_VALIDATION": ("SPECIFICATION", 2),
    # order 3 HUMAN_GATE
    "HUMAN_PENDING": ("HUMAN_GATE", 3),
    "REMINDER": ("HUMAN_GATE", 3),
    "SPEC_REGRESSION_CHECK": ("HUMAN_GATE", 3),
    # order 4 FROZEN
    "SPEC_FROZEN": ("FROZEN", 4),
    "TEST_CONTRACT_NEGOTIATED": ("FROZEN", 4),
    # order 5 IMPLEMENTATION
    "IMPLEMENTATION": ("IMPLEMENTATION", 5),
    "SANDBOX_HARDENING_GATE": ("IMPLEMENTATION", 5),
    "EXECUTION_EVALUATION": ("IMPLEMENTATION", 5),
    "ADVERSARIAL_EVALUATION": ("IMPLEMENTATION", 5),
    # order 6 REVIEW
    "PR_REVIEW": ("REVIEW", 6),
    "SPEC_AUDIT": ("REVIEW", 6),
    # order 7 VERIFICATION
    "RTM_VERIFY": ("VERIFICATION", 7),
    # order 8 RELEASE
    "RELEASE_READY": ("RELEASE", 8),
    "RELEASE": ("RELEASE", 8),
})

#: 觀測狀態（SDD 的 OBSERVATION_STATES，現況 15 個）：狀態 → 回歸階段 (name, order)。
_OBSERVATION: Mapping[str, tuple[str, int]] = MappingProxyType({
    "AUTOCLAUDE_DELEGATED": ("IMPLEMENTATION", 5),
    "EVALUATOR_AUDIT": ("IMPLEMENTATION", 5),
    "SPEC_DEBATE": ("SPECIFICATION", 2),
    "SPEC_PATCH_PROPOSAL": ("REVIEW", 6),
    "EXPERIMENT_REPLAY": ("REVIEW", 6),
    "PRODUCTION_SIGNAL": ("RELEASE", 8),
    "LEARNING_COMMIT": ("RELEASE", 8),
    "SCAFFOLD_GC": ("RELEASE", 8),
    "MEMORY_CONSOLIDATION": ("RELEASE", 8),
    "PRODUCTION_BEHAVIORAL_SIGNAL": ("RELEASE", 8),
    "CAPABILITY_BENCHMARK": ("RELEASE", 8),
    "HUB_SYNC": ("OBSERVATION", 0),
    "TRAJECTORY_PREDICTED": ("OBSERVATION", 0),
    "DRIFT_OBSERVATION": ("OBSERVATION", 0),
    "MONITOR_VIOLATION": ("OBSERVATION", 0),
})

#: 阻塞狀態（＝SDD 的 `FSMRuntime._BLOCKING_STATES`）。
_BLOCKING: frozenset[str] = frozenset(
    {"ESCALATION", "ESCALATION_FINAL", "TERMINATED", "TOKEN_BUDGET_CRITICAL"})

#: 過渡狀態。
_TRANSIENT: frozenset[str] = frozenset(
    {"AUTO_COMPACT_PENDING", "AUTO_RECOVERY_ATTEMPT", "RESUME_VERIFICATION"})

#: 這支函式認得的全部狀態（現況 43 個＝SDD `_HAPPY_PATH` 的全部鍵；F-5 對拍用）。
KNOWN_STATES: frozenset[str] = (
    frozenset(_MAIN_PATH) | frozenset(_OBSERVATION) | _BLOCKING | _TRANSIENT)


def _phase(name: str, order: int, blocking: bool = False,
           observation: bool = False) -> SddFsmPhase:
    return {"name": name, "order": order, "blocking": blocking, "observation": observation}


def phase_of(current_state: object) -> SddFsmPhase:
    """回傳 current_state 所屬的 phase dict（name、order、blocking、observation）。

    每次呼叫回傳新的 dict（呼叫端改它不會影響之後的呼叫）。任何輸入都不拋例外；無法辨識者一律回傳
    UNKNOWN（包含 None、非字串、容器、空白、前後帶空白的合法狀態名、不在表內的字串）。
    """
    if not isinstance(current_state, str) or current_state.strip() == "":
        return _phase("UNKNOWN", 0)

    if current_state in _BLOCKING:
        return _phase("BLOCKED", 0, blocking=True)

    if current_state in _OBSERVATION:
        name, order = _OBSERVATION[current_state]
        return _phase(name, order, observation=True)

    if current_state in _TRANSIENT:
        return _phase("TRANSIENT", 0)

    if current_state in _MAIN_PATH:
        name, order = _MAIN_PATH[current_state]
        return _phase(name, order)

    return _phase("UNKNOWN", 0)
