"""Phase X / ACT-157 — Embodied Grounding Oracle（具身接地評估器，generator 不可見）.

GAP-X1 解（由 Phase X 切片 FF-16 量測 surface）：Phase L~W 把元迴圈自我演化能力推到 meta⁸，但
「評估」端一路是 dimension_necessity_oracle 的**合成語料勝率**——從不啟動沙箱、從不查真實日誌、
從不跑真 App。本模組把元迴圈的生成-評估分離**接地**到具身觀測：給定一個自我發明能力在固定沙箱
基準 spec 上的 baseline 與 candidate `ExecutionObservation`，用 `output_quality_scorer` 客觀計分，
產出 **grounded-verdict**（具身增益判據：OQS 不退步 ∧ 無新增 runtime_fail）。

對抗分離（Rule 9.36，承 Phase O~W 反 Goodhart 地基）：本模組結構性**不 import** 任何 generator
（operator_*_genesis / dimension_semantics_synthesizer / vocabulary_genesis）——具身 oracle 對
generator 不可見，由 test ast/import 隔離斷言守（test_phase_x）。本模組只依賴 output_quality_scorer
（客觀計分器，rule-based / 零 LLM）。

停機接地（Rule 9.36 EmbodiedGroundingBounded 緊語意）：具身接地的停機反諷在於——為讓元迴圈在真實
環境驗證，引入了「真實沙箱可能 hang」這個新不停機源。故 `sandbox_timed_out` 一律映為 grounded_fail
（FSM 收 verdict 而非等沙箱）；無客觀觀測（OQS inconclusive）的 verdict 由 guard_embodied_grounding
fail-closed 拒絕。本 oracle 只**產出** verdict，**有界停機強制**由 meta_halt_monitor.guard_embodied_
grounding 負責（與 TLA+ EmbodiedGroundingBounded 100% 同構）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import output_quality_scorer as _oqs

GROUNDED_PASS = "grounded_pass"
GROUNDED_FAIL = "grounded_fail"
GROUNDED_SPEC_DEFECT = "spec_defect"
GROUNDED_INCONCLUSIVE = "inconclusive"   # 無客觀觀測 → guard fail-closed


@dataclass
class GroundedVerdict:
    """具身接地裁決——duck-typed 給 meta_halt_monitor.guard_embodied_grounding 消費.

    `observation` 為 candidate 的客觀 `ExecutionObservation`（guard 會獨立重新計分驗證，
    不盲信本 oracle 的 `grounded_verdict` 標籤）。
    """
    observation: Optional[_oqs.ExecutionObservation]
    grounded_verdict: str
    oqs: float
    baseline_oqs: float
    spec_defect: bool = False
    sandbox_timed_out: bool = False
    reason: str = ""


def _has_new_runtime_fail(baseline: _oqs.ExecutionObservation,
                          candidate: _oqs.ExecutionObservation) -> bool:
    """candidate 是否相對 baseline 新增 runtime 失敗（更多 runtime 錯誤 / 由 0-exit 變非零 exit）。"""
    more_errors = candidate.runtime_errors > baseline.runtime_errors
    newly_nonzero = candidate.nonzero_exit and not baseline.nonzero_exit
    return more_errors or newly_nonzero


def evaluate_embodied_grounding(
    baseline_obs: _oqs.ExecutionObservation,
    candidate_obs: Optional[_oqs.ExecutionObservation],
    *,
    spec_defect: bool = False,
    sandbox_timed_out: bool = False,
) -> GroundedVerdict:
    """產出具身 grounded-verdict（generator 不可見的接地評估）.

    判據（具身增益，非合成勝率）：
      - 沙箱硬 timeout → grounded_fail（FSM 不 wall-clock wait）。
      - candidate 無客觀觀測（OQS inconclusive）→ inconclusive（guard 會 fail-closed → ESCALATION）。
      - spec_defect → spec_defect（實作對、契約矛盾，route SPEC_AUDIT，非 IMPLEMENTATION 重試）。
      - grounded_pass ⟺ candidate OQS verdict==pass ∧ OQS 不退步（>= baseline）∧ 無新增 runtime_fail。
      - 其餘 → grounded_fail。
    """
    base_res = _oqs.score(baseline_obs)
    base_oqs = base_res.score

    if candidate_obs is None:
        return GroundedVerdict(
            observation=None, grounded_verdict=GROUNDED_INCONCLUSIVE,
            oqs=0.0, baseline_oqs=base_oqs,
            reason="candidate 無 ExecutionObservation（具身評估缺客觀資料，guard fail-closed）")

    if sandbox_timed_out:
        cand_res = _oqs.score(candidate_obs, spec_defect=spec_defect)
        return GroundedVerdict(
            observation=candidate_obs, grounded_verdict=GROUNDED_FAIL,
            oqs=cand_res.score, baseline_oqs=base_oqs, sandbox_timed_out=True,
            reason="沙箱硬 timeout → grounded_fail（FSM 不 wall-clock wait，收 verdict 而非等沙箱）")

    cand_res = _oqs.score(candidate_obs, spec_defect=spec_defect)

    if cand_res.verdict == "spec_defect":
        return GroundedVerdict(
            observation=candidate_obs, grounded_verdict=GROUNDED_SPEC_DEFECT,
            oqs=cand_res.score, baseline_oqs=base_oqs, spec_defect=True,
            reason="具身實跑證明契約矛盾（spec_defect）→ route SPEC_AUDIT，非 IMPLEMENTATION 重試")

    if cand_res.verdict == "inconclusive":
        return GroundedVerdict(
            observation=candidate_obs, grounded_verdict=GROUNDED_INCONCLUSIVE,
            oqs=cand_res.score, baseline_oqs=base_oqs,
            reason="candidate 無客觀觀測（沙箱從未真正跑過/壞過）→ guard fail-closed")

    no_regress = cand_res.score >= base_oqs - 1e-9
    no_new_runtime_fail = not _has_new_runtime_fail(baseline_obs, candidate_obs)

    if cand_res.verdict == "pass" and no_regress and no_new_runtime_fail:
        return GroundedVerdict(
            observation=candidate_obs, grounded_verdict=GROUNDED_PASS,
            oqs=cand_res.score, baseline_oqs=base_oqs,
            reason=f"具身接地通過：OQS={cand_res.score:.4f}>=baseline={base_oqs:.4f} ∧ 無新增 runtime_fail")

    return GroundedVerdict(
        observation=candidate_obs, grounded_verdict=GROUNDED_FAIL,
        oqs=cand_res.score, baseline_oqs=base_oqs,
        reason=f"具身接地未通過（verdict={cand_res.verdict} / regress={not no_regress} / "
               f"new_runtime_fail={not no_new_runtime_fail}）→ REJECT 不 churn")
