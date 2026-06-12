# AutoSDD 缺陷帳本（Defect Log）— 跨輪累積、只增不刪

> **用途**：AutoSDD 雙軌迭代（A 軌整合 / B 軌 Dogfooding）行進中發現的框架缺點/Bug/摩擦，
> 依「發現即記、絕不累積」紀律入帳，並依分流規則回流改進（見
> `docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` 的「🐶 自我迭代模式」）。
> **建立**：2026-06-12（首輪 N=01；首輪或帳本不存在時於階段一建立含表頭的帳本）。
>
> **格式定義**（每筆一列）：
> `ID`｜`發現日期`｜`發現情境`（FSM 狀態 / SCG 閘門 / hook / skill / nightly stage / 審計）｜
> `現象與證據`（file:line 或命令輸出）｜`嚴重度`｜`分流去向`｜`狀態`
> - **ID**：`DEF-{{N}}-{seq}`，N = 迭代輪編號（01/02…），seq 為該輪流水號。
> - **嚴重度**：依 v0.01 官方
>   `docs_template/sdd/testing/DEFECT-CLASSIFICATION-SPEC-TEMPLATE.md` 之 Priority 分級：
>   **P0**（Urgent — 必須立即修復，阻擋當前測試/發布）/ **P1**（High — 當前 Sprint 修復）/
>   **P2**（Normal — 下個 Sprint 修復）/ **P3**（Low — Backlog，擇機修復）。
> - **狀態**：`open`（未分流）/ `routed`（已分流待修）/ `fixed@<版本或載體>`（已修，附證據）/
>   `wontfix+理由`。
> - **分流去向**（對應官方回流機制）：規格/文檔缺陷 → Phase J SPEC-PATCH（併入 v0.0(X+1)）；
>   治理規則缺陷 → FPL→SLV→LEARNING_COMMIT；框架程式/模板/hook 缺陷 → RFC + v0.0(X+1)；
>   整合層（AutoClaude 側）缺陷 → 下輪 A 軌 W 項。

## 缺陷總表

| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |
|----|----------|----------|------------------------|--------|----------|------|
| DEF-01-001 | 2026-06-12 | zero-trust 審計 | `AISDLC_SDD_v0.01/governance/RULES_INDEX.md:9` 表頭「共 35 檔」過期——`ls governance/rules/` 實數為 38 檔（R-9.x 37 條 + R-SELF-STRIDE）；2026-06-12 複驗仍存在 | P2 | v0.02（凍結本體文檔修正，Copy-on-Evolve） | fixed@v0.02（證據：`AISDLC_SDD_v0.02/governance/RULES_INDEX.md:8-11` 改記 39 檔〔R-9.1~9.38 + R-SELF-STRIDE〕+ next-act/next-rule 前緣同步 172/9.39；v0.01 凍結基線依紀律不回改） |
| DEF-01-002 | 2026-06-12 | zero-trust 審計（nightly/CI 腳本） | `AISDLC_SDD_v0.01/tools/fsm_runtime/formal/run_tlc.sh` 僅實裝 2 軌（SDD_FSM L73-77 + FLEET_FSM L119-137），與五軌真相源 `tlc_runner.py` 不對稱且全檔無說明註記；2026-06-12 複驗仍存在 | P3 | v0.02（補註記「五軌請走 tlc_runner.py」或補齊五軌） | fixed@v0.02（證據：`AISDLC_SDD_v0.02/tools/fsm_runtime/formal/run_tlc.sh:4-7` LEGACY 兩軌快驗註記 + 指向 tlc_runner 五軌） |
| DEF-01-003 | 2026-06-12 | zero-trust 審計（nightly/CI 腳本） | `AISDLC_SDD_v0.01/tools/` 缺顯式 `__init__.py`（`Test-Path` = False，2026-06-12 複驗），`python -m tools.…` 依賴 py3.3+ implicit namespace package | P3 | v0.02 | fixed@v0.02（證據：`AISDLC_SDD_v0.02/tools/__init__.py` 已建立，v0.02 pytest not-chaos 全綠驗證無回歸） |
| DEF-01-004 | 2026-06-12 | zero-trust 審計（AutoClaude CI） | AutoClaude `.github/workflows/ci.yml:189` pg-e2e-nightly 的 `if` 僅檢 `github.event_name == 'schedule'`，未以 `github.event.schedule` 過濾 cron——03:00 UTC 的 mutation cron（`ci.yml:11-13` 兩條 cron）也會觸發 pg-e2e，每晚雙跑（隱性成本，非錯誤）；2026-06-12 複驗仍存在 | P3 | 下輪 A 軌 W 項（AutoSDD_improving_02.md） | routed |
| DEF-01-005 | 2026-06-12 | 整合規劃流程（原始 Prompt vs 系統實況比對） | 原始整合 Prompt 假設與系統實況偏差：`GoalSynthesisPlugin` 已存在（`goal_synthesis_plugin.py:29`）卻被假設為待建；Port 實名為 `IBrain`/`IEvaluator`（`core/ports/brain.py:72`、`core/ports/evaluator.py:20`）卻寫作 BrainPort/EvaluatorPort——屬流程缺陷「規劃前未做 zero-trust 偵察」（證據：`AutoSDD_ZeroTrust_Audit_01.md` §2 比對表） | P2 | 已由迭代範本「階段一強制重偵察」修復 | fixed@範本v2（證據：`AutoSDD_Iteration_Prompt_Template.md` 階段一「Zero-Trust Re-Audit」條款 + 硬閘） |
| DEF-01-006 | 2026-06-12 | W6 實作（zero-trust 開檔複驗 kernel 派發實況） | 凍結計畫 §4.1/§4.2 錨定之 `POST_EVALUATE` / `ON_ESCALATION` 為合法 `KernelPhase` 枚舉（`hookspec.py:33,39`）但 **kernel 現況不派發**——全 codebase `phase=KernelPhase.X` emit 點僅 11 處（`kernel.py:87,120,136,153,174,176,204,222` + auto_resume/checkpoint 3 處），評估後實際派發為 `POST_ATTEMPT`/`ON_FAILURE`/`ON_SUCCESS`。計畫凍結前複驗只驗了「枚舉存在」未驗「實際派發」 | P2 | W6 已實作補償：`SddGovernancePlugin` 雙訂閱（計畫 phase 向前相容 + 實際派發 phase 真實載體，`sdd_governance_plugin.py` docstring 載明）；計畫文件已凍結不回改，偏差記入 `AutoSDD_ZeroTrust_Audit_01.md` §7；下輪迭代範本「階段一」應加「枚舉存在 ≠ 實際派發」檢核項 | fixed@W6（證據：`tests/plugins/test_sdd_governance.py` 22 case 以實際派發 phase 驗證全行為） |
| DEF-01-007 | 2026-06-12 | W8 整合驗收 | `cc-switch` 未安裝（`Get-Command cc-switch` 不存在），計畫 §5.2 多模型後端 A/B 驗收無法執行；`integration_gate.ps1` [4/4] 段落以 SKIP + 指引處理（非偽綠：SKIP 明示於輸出） | P3 | 環境工具補裝後依 §5.2 手動執行 A/B（指標：一次通過率 / CORRECTION 次數 / SDD_CONTRACT_VIOLATION 次數 / token 峰值）；列下輪 W 項前置檢查 | open |
| DEF-01-008 | 2026-06-12 | 三專家審查（Architect） | production 入口 main.py 呼叫 build_kernel 未傳 brain=（grep 證實非測試呼叫點僅 wiring 內部）→ SddGovernancePlugin._on_failure 的 IBrain.decide_escalation 升級諮詢於正式 CLI 路徑為死碼（plugin 已優雅降級 brain=None 直接 return，既有 EvolutionPlugin 升級鏈不受影響）。main.py 注入 MinimaxBrain 會同時啟用 kernel.decide_correction 路徑、改變既有修正行為，須獨立評估 | P1 | 下輪 A 軌 W 項（AutoSDD_improving_02：main.py brain 注入影響評估 + e2e） | routed |
| DEF-01-009 | 2026-06-12 | 三專家審查（Architect） | sdd_governance_plugin.py raw 250 行恰貼 plugin_entry ≤250 上限（工具計非空行 217 過關）——後續任何擴充必須先拆 <feature>_plugin/ package | P3 | 下輪擴充前置作業（watch item） | open |
| DEF-01-010 | 2026-06-12 | 三專家審查（SA-SD） | v0.02 新增 compiler agent 後 AISDLC_SDD_INIT.md 仍宣稱 25 Agents / 18 specialized（磁碟實數 26/19），arch_fitness FF-7 advisory 已偵測 | P2 | 本輪即修（v0.02 文件計數同步） | fixed@v0.02（證據：INIT.md 計數更正 + EVOLUTION_LOG delta 補記） |
