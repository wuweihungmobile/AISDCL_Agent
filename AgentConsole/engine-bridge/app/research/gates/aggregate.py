"""四方審查的確定性聚合與判定（模板 ADVERSARIAL-REVIEW-CARD §2；D-42、D-14；AC-R2P-08-1／08-2）。

整數式 `W100＝30A＋25P＋25Q＋20S`，顯示值 `weighted_total＝W100／100`（精確兩位小數、
**不四捨五入**）：權重是 0.05 的倍數，所以 W100 除以 100 本來就恰有兩位小數，用
`Decimal.scaleb` 位移指數即可，不經浮點、不需要任何舍入常數。例：A=85、P=85、Q=84、S=86 時
W100＝8495、顯示 84.95，**不過**（若先四捨五入成 85.0 就會假通過——這正是整數判定存在的原因）。

判定路徑只用整數比較：`W100 ≥ 100×門檻`（8500）。本檔不含 `round(`、`float(` 與任何 `ROUND_` 常數，
由 `tests/test_research_gates.py` 以 AST 掃描釘住（AT-960-12-1）。

通過（`passed`）＝四條件之且：預檢通過、W100 不低於門檻、最低維度不低於地板、本輪未結 P1 為 0。
`verdict`：通過→`PASS`；否則 FSM 回報預算耗盡→`ESCALATE`，其餘→`REVISE`（取自 FSM `gate` 的回傳，
Bridge 不自建重試計數）。
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .schemas import DIMENSION_FLOOR, DIMENSIONS, REVIEW_THRESHOLD, SCG_RETRY_LIMIT, W100_WEIGHTS

THRESHOLD_W100 = 100 * REVIEW_THRESHOLD
VERDICTS: tuple[str, ...] = ("PASS", "REVISE", "ESCALATE")
CONDITION_KEYS: tuple[str, ...] = (
    "precheck_passed", "weighted_ge_threshold", "all_dimensions_ge_floor", "no_open_p1")


@dataclass(frozen=True)
class RoundInputs:
    """一輪判定的輸入：預檢結果、四維整數分（預檢不過時為 None＝不計分）、本輪未結 P1 數。"""

    precheck_passed: bool
    scores: Mapping[str, int] | None
    open_p1_count: int = 0


@dataclass(frozen=True)
class Judgement:
    """一輪的算術結果（尚未看 FSM）。不計分時 `weighted_total` 與 `min_dimension_score`
    為 None。"""

    w100: int | None
    weighted_total: Decimal | None
    min_dimension_score: int | None
    conditions: Mapping[str, bool]
    open_p1_count: int
    passed: bool


@dataclass(frozen=True)
class Decision:
    """一輪的最終判定。`gate_call` 是 Bridge 該對 FSM 做的事：`PASS`／`FAIL`／None
    （POST_HUMAN 通過輪依設計不呼叫 `gate`，D-50）。"""

    judgement: Judgement
    verdict: str
    gate_call: str | None
    escalated: bool


def w100_of(scores: Mapping[str, int]) -> int:
    """`30A＋25P＋25Q＋20S`（維度缺漏或型別不對丟 `ValueError`；不以 0 補）。"""
    total = 0
    for dimension in DIMENSIONS:
        value = scores.get(dimension)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"維度 {dimension} 缺分數或不是整數：{value!r}")
        total += W100_WEIGHTS[dimension] * value
    return total


def weighted_total_of(w100: int) -> Decimal:
    """顯示值＝`W100／100`：精確兩位小數（`Decimal.scaleb` 位移指數，不舍入）。"""
    return Decimal(w100).scaleb(-2)


def format_weighted(value: Decimal | None) -> str | None:
    """固定兩位小數的文字（`84.95`、`85.00`）；不計分為 None。"""
    return None if value is None else format(value, ".2f")


def judge(inputs: RoundInputs) -> Judgement:
    """算 W100、顯示值、最低維度與四個條件旗標（整數比較）。預檢不過＝不計分、分數相關旗標為假。"""
    if not inputs.precheck_passed or inputs.scores is None:
        conditions = {"precheck_passed": bool(inputs.precheck_passed),
                      "weighted_ge_threshold": False, "all_dimensions_ge_floor": False,
                      "no_open_p1": inputs.open_p1_count == 0}
        return Judgement(None, None, None, conditions, inputs.open_p1_count, False)
    w100 = w100_of(inputs.scores)
    lowest = min(inputs.scores[d] for d in DIMENSIONS)
    conditions = {"precheck_passed": True, "weighted_ge_threshold": w100 >= THRESHOLD_W100,
                  "all_dimensions_ge_floor": lowest >= DIMENSION_FLOOR,
                  "no_open_p1": inputs.open_p1_count == 0}
    return Judgement(w100, weighted_total_of(w100), lowest, conditions, inputs.open_p1_count,
                     all(conditions[key] for key in CONDITION_KEYS))


def _escalated_by(gate_result: Mapping[str, Any] | None) -> bool:
    """FSM `gate FAIL` 的回傳是否表示預算耗盡。以回傳為準：`escalated` 鍵優先；缺鍵時才看
    `retry_count` 是否達上限（Bridge 自己不計數）。"""
    if not gate_result:
        return False
    if "escalated" in gate_result and gate_result["escalated"] is not None:
        return bool(gate_result["escalated"])
    count = gate_result.get("retry_count")
    return isinstance(count, int) and not isinstance(count, bool) and count >= SCG_RETRY_LIMIT


def decide(inputs: RoundInputs, fsm_gate_result: Mapping[str, Any] | None = None, *,
           post_human: bool = False) -> Decision:
    """通過→`PASS`（要呼叫 `gate PASS`；POST_HUMAN 的通過輪不呼叫）；未通過→`FAIL`，verdict 依 FSM
    `gate FAIL` 的回傳為 `REVISE` 或 `ESCALATE`（回傳尚未取得時暫為 `REVISE`）。"""
    judgement = judge(inputs)
    if judgement.passed:
        return Decision(judgement, "PASS", None if post_human else "PASS", False)
    escalated = _escalated_by(fsm_gate_result)
    return Decision(judgement, "ESCALATE" if escalated else "REVISE", "FAIL", escalated)
