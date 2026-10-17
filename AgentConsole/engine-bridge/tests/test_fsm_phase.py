"""T-G（FSM current_state → phase 純函式，app/fsm_phase.py）的單元測試。

兩部分：
  1. W4 dogfood 的七個 AT（真 claude haiku 依 TCS-TgPhase-20261017 寫出、SCG-4 審查通過），測試名
     保留 AT 編號（`test_AT_001_<AC>_<n>_…`）以利 RTM 追溯與 `pytest -k AT_001_1_1` 這類評估指令。
     搬入時只改了 import 路徑；AT-001-1-2 的第二個函式原本只取 4＋5 個狀態（審查表 E 節判為輕度弱
     化），這裡補成 TCS 字面的「AT-001-1-1 的十個狀態＋AT-001-1-2 的十一個狀態」。
  2. 契約 v1.5 §3.1.5 對映表逐鍵斷言：下面 CONTRACT 區是照契約表**獨立手抄**的一份（不從
     app/fsm_phase.py 衍生），所以表被改壞、漏掉或多出狀態都會紅；與 SDD LATEST 狀態集合的對拍是
     tests/test_sdd_integration_parity.py 的 F-5。
"""
from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType

import pytest

from app import fsm_phase
from app.fsm_phase import KNOWN_STATES, phase_of

PHASE_KEYS = {"name", "order", "blocking", "observation"}
UNKNOWN = {"name": "UNKNOWN", "order": 0, "blocking": False, "observation": False}

# ── CONTRACT：契約 §3.1.5 的三張表（主路徑階段／觀測狀態回歸階段／阻塞與過渡）────────────────────
#: (order, name, 包含的 current_state)
CONTRACT_MAIN = [
    (1, "INTAKE", ["INIT", "SCENARIO_DETECT", "AGENT_LOAD", "INTENT_DECOMPOSITION",
                   "BACKLOG_PRIORITIZED"]),
    (2, "SPECIFICATION", ["SPEC_DRAFTING", "SCG_VALIDATION"]),
    (3, "HUMAN_GATE", ["HUMAN_PENDING", "REMINDER", "SPEC_REGRESSION_CHECK"]),
    (4, "FROZEN", ["SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED"]),
    (5, "IMPLEMENTATION", ["IMPLEMENTATION", "SANDBOX_HARDENING_GATE", "EXECUTION_EVALUATION",
                           "ADVERSARIAL_EVALUATION"]),
    (6, "REVIEW", ["PR_REVIEW", "SPEC_AUDIT"]),
    (7, "VERIFICATION", ["RTM_VERIFY"]),
    (8, "RELEASE", ["RELEASE_READY", "RELEASE"]),
]
#: (回歸階段 name, order, 觀測狀態)
CONTRACT_OBSERVATION = [
    ("IMPLEMENTATION", 5, ["AUTOCLAUDE_DELEGATED", "EVALUATOR_AUDIT"]),
    ("SPECIFICATION", 2, ["SPEC_DEBATE"]),
    ("REVIEW", 6, ["SPEC_PATCH_PROPOSAL", "EXPERIMENT_REPLAY"]),
    ("RELEASE", 8, ["PRODUCTION_SIGNAL", "LEARNING_COMMIT", "SCAFFOLD_GC", "MEMORY_CONSOLIDATION",
                    "PRODUCTION_BEHAVIORAL_SIGNAL", "CAPABILITY_BENCHMARK"]),
    ("OBSERVATION", 0, ["HUB_SYNC", "TRAJECTORY_PREDICTED", "DRIFT_OBSERVATION",
                        "MONITOR_VIOLATION"]),
]
CONTRACT_BLOCKING = ["ESCALATION", "ESCALATION_FINAL", "TERMINATED", "TOKEN_BUDGET_CRITICAL"]
CONTRACT_TRANSIENT = ["AUTO_COMPACT_PENDING", "AUTO_RECOVERY_ATTEMPT", "RESUME_VERIFICATION"]


def _contract_phases() -> dict[str, tuple[str, int, bool, bool]]:
    """狀態 → (name, order, blocking, observation)。"""
    table: dict[str, tuple[str, int, bool, bool]] = {}
    for order, name, states in CONTRACT_MAIN:
        table.update({s: (name, order, False, False) for s in states})
    for name, order, states in CONTRACT_OBSERVATION:
        table.update({s: (name, order, False, True) for s in states})
    table.update({s: ("BLOCKED", 0, True, False) for s in CONTRACT_BLOCKING})
    table.update({s: ("TRANSIENT", 0, False, False) for s in CONTRACT_TRANSIENT})
    return table


CONTRACT_PHASES = _contract_phases()

AT_001_1_1_STATES = [
    "INIT", "SCENARIO_DETECT", "AGENT_LOAD", "INTENT_DECOMPOSITION", "BACKLOG_PRIORITIZED",
    "SPEC_DRAFTING", "SCG_VALIDATION", "HUMAN_PENDING", "REMINDER", "SPEC_REGRESSION_CHECK",
]
AT_001_1_2_STATES = [
    "SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED", "IMPLEMENTATION", "SANDBOX_HARDENING_GATE",
    "EXECUTION_EVALUATION", "ADVERSARIAL_EVALUATION", "PR_REVIEW", "SPEC_AUDIT", "RTM_VERIFY",
    "RELEASE_READY", "RELEASE",
]


# ══ 一、W4 dogfood 的七個 AT ═══════════════════════════════════════════════════════════════
# AT-001-1-1
# 對應 AC: AC-001-1 主路徑各狀態回傳正確階段且序號單調（立案至人工確認）
# 測試類型: Unit
def test_AT_001_1_1_intake_specification_human_gate_main_path():
    states = AT_001_1_1_STATES
    results = [phase_of(s) for s in states]

    for r in results:
        assert set(r.keys()) == PHASE_KEYS

    for r in results[:5]:
        assert r["name"] == "INTAKE"
        assert r["order"] == 1
    for r in results[5:7]:
        assert r["name"] == "SPECIFICATION"
        assert r["order"] == 2
    for r in results[7:10]:
        assert r["name"] == "HUMAN_GATE"
        assert r["order"] == 3

    for r in results:
        assert r["blocking"] is False
        assert r["observation"] is False

    orders = [r["order"] for r in results]
    assert orders == sorted(orders)


# AT-001-1-2
# 對應 AC: AC-001-1 主路徑各狀態回傳正確階段且序號單調（凍結至發布）
# 測試類型: Unit
def test_AT_001_1_2_frozen_to_release_main_path():
    states = AT_001_1_2_STATES
    results = [phase_of(s) for s in states]

    for r in results:
        assert set(r.keys()) == PHASE_KEYS

    for r in results[0:2]:
        assert r["name"] == "FROZEN"
        assert r["order"] == 4
    for r in results[2:6]:
        assert r["name"] == "IMPLEMENTATION"
        assert r["order"] == 5
    for r in results[6:8]:
        assert r["name"] == "REVIEW"
        assert r["order"] == 6
    assert results[8]["name"] == "VERIFICATION"
    assert results[8]["order"] == 7
    for r in results[9:11]:
        assert r["name"] == "RELEASE"
        assert r["order"] == 8

    for r in results:
        assert r["blocking"] is False
        assert r["observation"] is False

    orders = [r["order"] for r in results]
    assert orders == sorted(orders)
    # 相鄰階段差 1（主路徑）：依序去重後應為 4,5,6,7,8
    distinct = sorted(set(orders))
    assert distinct == [4, 5, 6, 7, 8]
    assert all(b - a == 1 for a, b in zip(distinct, distinct[1:], strict=False))


def test_AT_001_1_2_continues_from_intake_spec_gate_order():
    # TCS 字面：與 AT-001-1-1 的十個狀態合起來（共 21 個），order 沿主路徑單調不減、相鄰階段差 1。
    # （dogfood 原稿只取 4＋5 個狀態；審查表 E 節判為輕度弱化，這裡補成完整的 10＋11。）
    prior, later = AT_001_1_1_STATES, AT_001_1_2_STATES
    assert (len(prior), len(later)) == (10, 11)
    results = [phase_of(s) for s in prior + later]
    orders = [r["order"] for r in results]
    assert len(orders) == 21
    assert orders == sorted(orders)
    assert all(r["blocking"] is False and r["observation"] is False for r in results)
    distinct = sorted(set(orders))
    assert distinct == [1, 2, 3, 4, 5, 6, 7, 8]
    assert all(b - a == 1 for a, b in zip(distinct, distinct[1:], strict=False))


# AT-001-2-1
# 對應 AC: AC-001-2 觀測狀態回傳觀測旗標與回歸階段
# 測試類型: Unit
def test_AT_001_2_1_fifteen_observation_states_flags_and_regression_phase():
    states = [
        "AUTOCLAUDE_DELEGATED",
        "EVALUATOR_AUDIT",
        "SPEC_DEBATE",
        "SPEC_PATCH_PROPOSAL",
        "EXPERIMENT_REPLAY",
        "PRODUCTION_SIGNAL",
        "LEARNING_COMMIT",
        "SCAFFOLD_GC",
        "MEMORY_CONSOLIDATION",
        "PRODUCTION_BEHAVIORAL_SIGNAL",
        "CAPABILITY_BENCHMARK",
        "HUB_SYNC",
        "TRAJECTORY_PREDICTED",
        "DRIFT_OBSERVATION",
        "MONITOR_VIOLATION",
    ]
    results = [phase_of(s) for s in states]
    assert len(results) == 15

    for r in results:
        assert set(r.keys()) == PHASE_KEYS
        assert r["observation"] is True
        assert r["blocking"] is False

    # 回歸階段：IMPLEMENTATION／5
    for r in (results[0], results[1]):
        assert r["name"] == "IMPLEMENTATION"
        assert r["order"] == 5

    # SPECIFICATION／2
    assert results[2]["name"] == "SPECIFICATION"
    assert results[2]["order"] == 2

    # REVIEW／6
    for r in (results[3], results[4]):
        assert r["name"] == "REVIEW"
        assert r["order"] == 6

    # RELEASE／8
    for r in results[5:11]:
        assert r["name"] == "RELEASE"
        assert r["order"] == 8

    # 回歸點不可由狀態字串靜態判定：OBSERVATION／0
    for r in results[11:15]:
        assert r["name"] == "OBSERVATION"
        assert r["order"] == 0


# AT-001-3-1
# 對應 AC: AC-001-3 阻塞狀態回傳 BLOCKED 與阻塞旗標
# 測試類型: Unit
def test_AT_001_3_1_four_blocking_states_return_blocked_with_blocking_flag():
    states = [
        "ESCALATION",
        "ESCALATION_FINAL",
        "TERMINATED",
        "TOKEN_BUDGET_CRITICAL",
    ]
    results = [phase_of(s) for s in states]
    assert len(results) == 4

    for r in results:
        assert r["name"] == "BLOCKED"
        assert r["order"] == 0
        assert r["blocking"] is True
        assert r["observation"] is False


# AT-001-4-1
# 對應 AC: AC-001-4 無法辨識的輸入一律 UNKNOWN 且不拋例外（未知字串與非字串型別）
# 測試類型: Unit
def test_AT_001_4_1_unknown_and_non_string_inputs_return_unknown_without_exception():
    inputs = [
        "BOGUS_STATE",
        "init",
        42,
        1.5,
        True,
        None,
    ]
    results = []
    for value in inputs:
        result = phase_of(value)
        assert isinstance(result, dict)
        results.append(result)
    assert len(results) == 6

    for r in results:
        assert r["name"] == "UNKNOWN"
        assert r["order"] == 0
        assert r["blocking"] is False
        assert r["observation"] is False


# AT-001-4-2
# 對應 AC: AC-001-4 無法辨識的輸入一律 UNKNOWN 且不拋例外（空白、前後帶空白與容器型別）
# 測試類型: Unit
def test_AT_001_4_2_blank_padded_and_container_inputs_return_unknown_without_exception():
    inputs = [
        "",
        "   ",
        " INIT ",
        ["INIT"],
        {"state": "INIT"},
        {"INIT"},
    ]
    results = []
    for value in inputs:
        result = phase_of(value)
        assert isinstance(result, dict)
        results.append(result)
    assert len(results) == 6

    for r in results:
        assert r["name"] == "UNKNOWN"
        assert r["order"] == 0
        assert r["blocking"] is False
        assert r["observation"] is False


# AT-001-5-1
# 對應 AC: AC-001-5 過渡狀態回傳 TRANSIENT
# 測試類型: Unit
def test_AT_001_5_1_transient_states_return_transient_phase():
    states = ["AUTO_COMPACT_PENDING", "AUTO_RECOVERY_ATTEMPT", "RESUME_VERIFICATION"]
    results = [phase_of(state) for state in states]
    assert len(results) == 3

    for r in results:
        assert r["name"] == "TRANSIENT"
        assert r["order"] == 0
        assert r["blocking"] is False
        assert r["observation"] is False


# ══ 二、契約 §3.1.5 對映表逐鍵斷言 ═══════════════════════════════════════════════════════════
@pytest.mark.parametrize(("state", "expected"), sorted(CONTRACT_PHASES.items()),
                         ids=[s for s, _ in sorted(CONTRACT_PHASES.items())])
def test_every_contract_state_maps_exactly_as_the_contract_table(
        state: str, expected: tuple[str, int, bool, bool]) -> None:
    name, order, blocking, observation = expected
    got = phase_of(state)
    assert got == {"name": name, "order": order, "blocking": blocking,
                   "observation": observation}, state
    assert set(got) == PHASE_KEYS
    # 型別也是契約的一部分（openapi SddFsmPhase：integer／boolean，不是 bool 冒充 int）
    assert type(got["name"]) is str and type(got["order"]) is int
    assert type(got["blocking"]) is bool and type(got["observation"]) is bool


def test_the_function_knows_exactly_the_contract_states() -> None:
    """表被偷加或漏掉任何一個狀態都紅（現況 43 個：主路徑 21、觀測 15、阻塞 4、過渡 3）。"""
    assert KNOWN_STATES == set(CONTRACT_PHASES)
    sizes = [sum(len(s) for _, _, s in CONTRACT_MAIN),
             sum(len(s) for _, _, s in CONTRACT_OBSERVATION),
             len(CONTRACT_BLOCKING), len(CONTRACT_TRANSIENT)]
    assert sizes == [21, 15, 4, 3]
    assert len(CONTRACT_PHASES) == sum(sizes), "契約四組互不相交：沒有狀態同時落在兩組"


def test_the_four_groups_inside_the_module_are_disjoint_and_have_the_contract_sizes() -> None:
    groups = [set(fsm_phase._MAIN_PATH), set(fsm_phase._OBSERVATION),
              set(fsm_phase._BLOCKING), set(fsm_phase._TRANSIENT)]
    assert [len(g) for g in groups] == [21, 15, 4, 3]
    assert sum(len(g) for g in groups) == len(set().union(*groups)) == len(KNOWN_STATES)


def test_main_path_orders_cover_one_to_eight_without_gaps() -> None:
    """order 沿主路徑單調不減、相鄰階段差 1：八個階段的 order 恰為 1～8。"""
    orders = sorted({order for order, _, _ in CONTRACT_MAIN})
    assert orders == list(range(1, 9))
    names = [name for _, name, _ in sorted(CONTRACT_MAIN)]
    assert names == ["INTAKE", "SPECIFICATION", "HUMAN_GATE", "FROZEN", "IMPLEMENTATION",
                     "REVIEW", "VERIFICATION", "RELEASE"]


def test_flags_never_overlap_and_only_the_documented_groups_set_them() -> None:
    for state in KNOWN_STATES:
        got = phase_of(state)
        assert not (got["blocking"] and got["observation"]), state
    assert {s for s in KNOWN_STATES if phase_of(s)["blocking"]} == set(CONTRACT_BLOCKING)
    assert {s for s in KNOWN_STATES if phase_of(s)["observation"]} == {
        s for _, _, states in CONTRACT_OBSERVATION for s in states}


# ── 純函式性質（NFR-001-1）：無全域可變狀態 ───────────────────────────────────────────────────
def test_each_call_returns_a_fresh_dict_so_callers_cannot_poison_later_calls() -> None:
    first = phase_of("INIT")
    first["name"] = "TAMPERED"
    first["order"] = 99
    assert phase_of("INIT") == {"name": "INTAKE", "order": 1, "blocking": False,
                                "observation": False}
    assert phase_of("INIT") is not phase_of("INIT")
    assert phase_of(None) is not phase_of(None)


def test_the_mapping_tables_are_read_only() -> None:
    assert isinstance(fsm_phase._MAIN_PATH, MappingProxyType)
    assert isinstance(fsm_phase._OBSERVATION, MappingProxyType)
    with pytest.raises(TypeError):
        fsm_phase._MAIN_PATH["INIT"] = ("TAMPERED", 9)  # type: ignore[index]
    with pytest.raises(TypeError):
        del fsm_phase._OBSERVATION["HUB_SYNC"]  # type: ignore[attr-defined]
    assert isinstance(fsm_phase._BLOCKING, frozenset)
    assert isinstance(fsm_phase._TRANSIENT, frozenset)
    assert isinstance(KNOWN_STATES, frozenset)
    assert phase_of("INIT")["name"] == "INTAKE", "上面的失敗嘗試沒有改到任何東西"


# ── 容錯（AC-001-4 的延伸）：任何輸入都不拋例外 ───────────────────────────────────────────────
class _TaggedStr(str):
    """str 子類別（例如列舉的字串成員）仍是字串：照值查表。"""


class _State(StrEnum):
    FROZEN_STATE = "SPEC_FROZEN"
    BLOCKING_STATE = "ESCALATION"


# 注意：參數化的 id 一律手寫固定字串。xdist 每個 worker 各自收集，id 只要含物件 repr（`object()`
# 的記憶體位址在 Linux 每個行程都不同）、集合順序或雜湊值，worker 之間收集到的測試清單就不一致，
# 整個 pytest 直接中止（「Different tests were collected between gw0 and gw1」）。
@pytest.mark.parametrize("value", [
    pytest.param(b"INIT", id="bytes"),
    pytest.param(bytearray(b"INIT"), id="bytearray"),
    pytest.param(object(), id="object"),
    pytest.param(float("nan"), id="float-nan"),
    pytest.param((1, 2), id="tuple"),
    pytest.param(frozenset({"INIT"}), id="frozenset"),
    pytest.param(range(3), id="range"),
    pytest.param(Ellipsis, id="ellipsis"),
    pytest.param(-1, id="int-negative"),
    pytest.param(0, id="int-zero"),
    pytest.param(10**30, id="int-huge"),
    pytest.param("x" * 10_000, id="str-10k-chars"),
    pytest.param("INIT\x00", id="str-nul-suffix"),
    pytest.param("INIT\n", id="str-newline-suffix"),
    pytest.param("\tINIT", id="str-tab-prefix"),
    pytest.param("Init", id="str-mixed-case"),
    pytest.param("init", id="str-lower-case"),
    pytest.param("ＩＮＩＴ", id="str-fullwidth-letters"),
    pytest.param("INIT ", id="str-trailing-space"),
    pytest.param("\N{IDEOGRAPHIC SPACE}", id="str-ideographic-space"),
    pytest.param("\N{ZERO WIDTH SPACE}", id="str-zero-width-space"),
])
def test_unrecognised_inputs_of_any_type_are_unknown_and_never_raise(value: object) -> None:
    assert phase_of(value) == UNKNOWN


def test_string_subclasses_are_looked_up_by_value() -> None:
    assert phase_of(_TaggedStr("PR_REVIEW")) == {
        "name": "REVIEW", "order": 6, "blocking": False, "observation": False}
    assert phase_of(_State.FROZEN_STATE)["name"] == "FROZEN"
    assert phase_of(_State.BLOCKING_STATE)["blocking"] is True
    assert phase_of(_TaggedStr("  ")) == UNKNOWN
