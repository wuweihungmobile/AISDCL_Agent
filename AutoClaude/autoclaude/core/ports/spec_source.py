"""ISpecSource — SDD 規格來源契約（contract tier ≤400 LOC）。

對應 AutoSDD_improving_01.md §2.2（AISDLC-SDD × AutoClaude 深度整合 W1）。

core 僅依賴本介面；SDD 文件格式知識封裝於 infra adapter
（autoclaude.infra.adapters.sdd_to_playbook_adapter）。

PlaybookTask 引用模式與既有 IEvaluator（core/ports/evaluator.py:17）完全相同：
Protocol + runtime 相對 import models。core-purity contract（.importlinter
core-purity 條款）的 forbidden_modules 僅含 autoclaude.execution /
autoclaude.infra，不含 autoclaude.models，故此模式不破壞 core 純度。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ...models.playbook import PlaybookTask


class SpecNotFrozenError(RuntimeError):
    """SDD 規格尚未凍結（FSM 未達 SPEC_FROZEN / frozen_stages 為空）。

    規格先行（Spec-First Gate）硬閘：未凍結的規格不得編譯為 PlaybookTask。
    """


class SpecTaintedError(RuntimeError):
    """SDD 規格內容含黑名單字元 / 非白名單 evaluator 模板（疑似注入向量）。

    對應 AutoSDD_improving_01.md §1.3 鏈式攻擊截斷點 2（參數消毒）。
    """


class SpecFormatVersionError(RuntimeError):
    """SDD 規格宣告的格式版本不在 adapter 支援集（防漂移 fail-closed）。

    對應 AutoSDD_improving_67.md W-67-2：SDD 框架跨版（v0.01→v0.26）AT 表/Gherkin
    格式演進，未來不相容規格須被擋下而非靜默誤解析。缺版本欄者向後相容（預設 1.0 放行）。
    """


@dataclass(frozen=True)
class SpecContract:
    """單條 AC→AT 契約（自 TEST-CONTRACT-SPEC 解析）。"""

    ac_id: str          # AC-XXX-Y
    at_id: str          # AT-XXX-Y-Z
    gherkin: str        # Given-When-Then 全文
    expected_regex: str  # 轉譯後的 expected_output_regex
    evaluator_cmd: str  # 白名單模板生成的 evaluator_command
    scg_gate: str       # 所屬閘門（SCG-3/4/5）
    weak_regex: bool = False  # Then 斷言不可推導 → fallback 標記（§3.1）


@dataclass(frozen=True)
class SddSpec:
    """凍結後的規格快照。digest 寫入 checkpoint 防 drift。"""

    spec_path: str
    digest: str         # "sha256:..."（規格全文指紋）
    scenario: str       # 10 場景之一（greenfield/brownfield/...）
    contracts: tuple[SpecContract, ...] = field(default=())


class ISpecSource(Protocol):
    """SDD 規格 → PlaybookTask 編譯的契約。

    實作（W3）：autoclaude.infra.adapters.sdd_to_playbook_adapter.SddToPlaybookAdapter
    """

    def load_spec(self, spec_dir: str) -> SddSpec:
        """解析 spec_dir 下已凍結的 SDD 文件（TEST-CONTRACT-SPEC）。

        凍結判定（對齊 AISDLC_SDD fsm_runtime / state_loader 實際機制）：
        讀取 state_loader 管理的 FSM 狀態檔
        build/reports/fsm/FSM-STATE-{project}.yaml，確認下列任一成立：
          (a) fsm_state.frozen_stages 非空（record_spec_frozen 寫入
              {stage, frozen_at, compaction_report, spec_docs}）；
          (b) fsm_state.current_state 已達 SPEC_FROZEN 之後狀態
              （TEST_CONTRACT_NEGOTIATED / IMPLEMENTATION / ...）。
        否則 raise SpecNotFrozenError。

        Raises:
            SpecNotFrozenError: 規格未凍結（Spec-First 硬閘）。
            SpecTaintedError: 規格含注入向量字元。
            SpecFormatVersionError: 規格宣告的格式版本不受支援（防漂移 fail-closed）。
        """
        ...

    def compile_tasks(self, spec: SddSpec) -> list[PlaybookTask]:
        """SddSpec → PlaybookTask 序列（含 regex + evaluator 雙重驗證綁定）。

        純函數、無 IO；evaluator_command 僅得由白名單模板內插生成。
        """
        ...
