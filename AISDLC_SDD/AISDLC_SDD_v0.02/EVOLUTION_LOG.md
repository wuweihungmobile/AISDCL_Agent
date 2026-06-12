# EVOLUTION_LOG — AISDLC_SDD 版本演化紀錄

> 依 `docs/04_planning/AutoSDD_improving_01.md` §6 版本演化規則（Copy-on-Evolve）。
> 舊版 `AISDLC_SDD_v0.01/` 凍結唯讀；本目錄為演化後的可修改版本。

## v0.01 → v0.02

| 欄位 | 內容 |
|------|------|
| **版本** | v0.01 → v0.02 |
| **日期** | 2026-06-12（凍結來源：AutoSDD_improving_01.md，同日 🔴 人工確認凍結） |
| **delta 清單** | **新增 ACT-162~171（Phase Z，自 ID_REGISTRY next_free=162 起算）**：① `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`（SDD→Playbook 標準作業，ACT-162）② `agent/specialized/sdd-playbook-compiler-zh.yaml`（編譯者角色，ACT-163）③ `governance/rules/R-9.38-playbook-translation-fidelity.yaml`（AT↔step 100% 雙向映射，違反→SPEC_AUDIT，ACT-164）④ 10 場景 SOP 各加「§AutoClaude 自動化執行」小節 + QuickRef 同步（ACT-165~171）。**新增 FSM 狀態：無**（`AUTOCLAUDE_DELEGATED` 維持提案，落地前置條件見 BRIDGE.md §5）。**缺陷修正（自 AutoSDD_Defect_Log 分流）**：DEF-01-001（RULES_INDEX.md 計數 35→39 檔 + next-act/next-rule 前緣同步）、DEF-01-002（run_tlc.sh 補「五軌請走 tlc_runner.py」legacy 註記）、DEF-01-003（`tools/__init__.py` 顯式 package 宣告）。ID_REGISTRY：Phase Z range [162,171] 登記、next_free 推進 act=172 / rule="9.39"。**根層文件計數同步（三專家審查 DEF-01-010）**：`AISDLC_SDD_INIT.md` / `README.md` 等根層文件 agent 計數 25/18 → 26/19 同步（v0.02 +sdd-playbook-compiler） |
| **TLC 證據** | **N/A** — `_HAPPY_PATH` 與全部 `*.tla` 零修改（diff 為空），依 Rule 9.18.1 無重跑義務；五軌 TLC 既有證明維持有效。`AUTOCLAUDE_DELEGATED` 落地時（v0.03+）必附五軌 TLC_DISTINCT/GENERATED/DEPTH 輸出 |
| **回退指引** | AutoClaude 端：`sdd_compile --spec-dir` 與 SddGovernancePlugin 的 `workflow_path` 指回 `AISDLC_SDD_v0.01/` 下的專案 docs 即完成回退（v0.02 對 AutoClaude 介面零 breaking change）。已知不相容點：v0.01 無 R-9.38 與 sdd-autoclaude-bridge workflow——回退後 AT↔step 保真檢查無治理規則承載（僅靠 AutoClaude 側 adapter 測試守護）；v0.01 `RULES_INDEX.md:9` 計數仍為過期值（屬凍結基線既有債務，不回改）。回退驗證：根層 `tools/integration_gate.ps1` 的 **[4/5] 回退驗證段**（`AutoClaude/tests/integration/test_sdd_bridge/test_rollback_compat.py`）——以 subprocess 用 v0.01 / v0.02 **各自的** `tools.fsm_runtime.state_loader` 產出真品 FSM 狀態檔（load_state → record_spec_frozen → save_state），再由 `autoclaude.tools.sdd_compile.compile_spec` 消費並斷言編譯出 3 步驟，證明指回 v0.01 後規格鏈路仍可編譯；[3/5] test_sdd_bridge 煙霧亦須全綠 |
