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

import re
from dataclasses import dataclass, field
from typing import Protocol

from ...models.playbook import PlaybookTask

# ADR-XPLAT-016 §8.1（D-115-16）：AT ID 文法的**唯一**定義。
# 正向 sdd_to_playbook_adapter 與逆向 playbook_to_rtm_adapter 都由它組 regex／判斷歸屬，
# 不得各寫一份（一份判準一個家，兩邊才不會悄悄漂移）。
# 前兩段數字＝所屬 AC（`AT-001-12-3-a` 屬 `AC-001-12`）；第三段起是任意個英數尾綴，
# 不影響歸屬。整串全比對、區分大小寫、`AT-` 須大寫；`AT-{NNN}-…` 這種模板佔位不算 AT 字樣。
AT_ID_PATTERN = r"AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*"


def ac_id_of_at(at_id: str) -> str | None:
    """AT id 前兩段數字推得所屬 AC id（`AT-001-12-3-a`→`AC-001-12`）；不合文法回 None。

    正向（列的 AC id 須等於本函式結果，否則該列未編成）與逆向（RTM 以前兩段歸 AC）共用這一處，
    「前兩段歸屬」的規則才不會在兩個 adapter 裡各有一份。
    """
    if not re.fullmatch(AT_ID_PATTERN, at_id):
        return None
    _, seg1, seg2, *_rest = at_id.split("-")
    return f"AC-{seg1}-{seg2}"


class SpecNotFrozenError(RuntimeError):
    """SDD 規格尚未凍結（FSM 未達 SPEC_FROZEN / frozen_stages 為空）。

    規格先行（Spec-First Gate）硬閘：未凍結的規格不得編譯為 PlaybookTask。
    """


class SpecDigestMismatchError(SpecNotFrozenError):
    """凍結後規格內容已變更：凍結時記下的摘要 ≠ 現檔摘要（ADR-XPLAT-016 §6.2，G-06）。

    是 SpecNotFrozenError 的子類，所以既有的 `except SpecNotFrozenError` 路徑（plugin 的 PRE_RUN
    veto、`sdd_compile` rc 2）自動 fail-closed；要區分「內容變了」與「根本沒凍結」的呼叫端
    （Bridge：409 `spec_digest_changed` vs 422 `spec_not_frozen`）先接這個子類即可。
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
    # improving_85 W-85-2：消費端表面化「已驗證的規格格式版本」（生產↔消費橋接閉合）。
    # 生產端（SDD 框架 v0.27+ TCS 模板）宣告 spec-format-version → adapter 驗證後寫入此欄，
    # 不再驗證即丟棄。缺欄 spec 維持 "1.0"（向後相容、零退化，與
    # _DEFAULT_SPEC_FORMAT_VERSION 一致）。
    spec_format_version: str = "1.0"
    # ADR-XPLAT-016 §6／§7.1／§8.2（improving_115）：三個加法式欄位，
    # 舊的位置／關鍵字建構不受影響。
    #   fsm_project        ：凍結閘實際採用的 FSM 狀態檔鍵（`FSM-STATE-<鍵>.yaml` 的鍵；
    #                        空＝未經閘門建構）。
    #   frozen_digest_status："verified"＝現檔與凍結時記下的摘要吻合；"absent"＝狀態檔沒有
    #                        任何階段帶摘要（舊狀態檔／凍結時沒帶 --digest），維持放行但已出聲。
    #                        預設 "absent"＝「沒有任何東西被驗證」的誠實值。
    #   unmapped_at_ids    ：規格宣告位置出現、卻沒編成 step 的 AT（首見順序）。
    #                        ⚠️ 與逆向 RTM 的同名欄是兩個不同層的欄位（那邊是「已編成的 AT
    #                        還原後無法歸屬 AC」）。
    fsm_project: str = ""
    frozen_digest_status: str = "absent"
    unmapped_at_ids: tuple[str, ...] = field(default=())


class ISpecSource(Protocol):
    """SDD 規格 → PlaybookTask 編譯的契約。

    實作（W3）：autoclaude.infra.adapters.sdd_to_playbook_adapter.SddToPlaybookAdapter
    """

    def load_spec(self, spec_dir: str) -> SddSpec:
        """解析 spec_dir 下已凍結的 SDD 文件（TEST-CONTRACT-SPEC）。

        spec_dir 本身若是**檔案**，視為指定的規格檔（引擎 PRE_RUN 以 playbook.workflow_path
        呼叫，port 簽名因此不必改）；實作可另收選填的 `spec_file`（相對 spec_dir 或絕對）。

        凍結判定（對齊 AISDLC_SDD fsm_runtime / state_loader 實際機制）：
        讀取 state_loader 管理的 FSM 狀態檔
        build/reports/fsm/FSM-STATE-{project}.yaml，確認下列任一成立：
          (a) fsm_state.frozen_stages 非空（record_spec_frozen 寫入
              {stage, frozen_at, compaction_report, spec_docs[, spec_doc_digests]}）；
          (b) fsm_state.current_state 已達 SPEC_FROZEN 之後狀態
              （TEST_CONTRACT_NEGOTIATED / IMPLEMENTATION / AUTOCLAUDE_DELEGATED / ...）。
        否則 raise SpecNotFrozenError。狀態檔不依字母序猜：以專案鍵（`SDD_PROJECT`）選檔，
        同目錄多檔又無鍵即 fail-closed。凍結時若記了 `spec_doc_digests`，現檔摘要必須吻合。

        Raises:
            SpecNotFrozenError: 規格未凍結（Spec-First 硬閘）。
            SpecDigestMismatchError: 凍結後規格內容已變更（SpecNotFrozenError 的子類）。
            SpecTaintedError: 規格含注入向量字元。
            SpecFormatVersionError: 規格宣告的格式版本不受支援（防漂移 fail-closed）。
        """
        ...

    def compile_tasks(self, spec: SddSpec) -> list[PlaybookTask]:
        """SddSpec → PlaybookTask 序列（含 regex + evaluator 雙重驗證綁定）。

        純函數、無 IO；evaluator_command 僅得由白名單模板內插生成。
        """
        ...
