# EVOLUTION_LOG — AISDLC_SDD 版本演化紀錄

> 依 `docs/04_planning/AutoSDD_improving_01.md` §6 版本演化規則（Copy-on-Evolve）。
> 舊版 `AISDLC_SDD_v0.01/` / `AISDLC_SDD_v0.02/` / `AISDLC_SDD_v0.03/` 凍結唯讀；本目錄為演化後的可修改版本。

## v0.03 → v0.04

| 欄位 | 內容 |
|------|------|
| **版本** | v0.03 → v0.04 |
| **日期** | 2026-06-14（凍結來源：AutoSDD_improving_03.md，同日 🔴 人工確認凍結方案 A，W1/W2 啟動） |
| **delta 清單** | **框架程式 bugfix（DEF-02-002 回流，B 軌 dogfooding 發現於 improving_02 收尾複核）**：`tools/fsm_runtime/tlc_runner.py` 計數解析修正——① 抽出 module-level 純函式 `parse_tlc_summary(out)`，以 `re.findall(...)[-1]`（**last-match**）取最終 summary 行，取代舊版 `re.search`（**first-match**）誤抓 TLC 執行中途 progress 行致 raw 計數不可靠（曾出現 `distinct=855 > generated=706` 違反恆等不變量）；② 加 **fail-closed 斷言**：`generated >= distinct`（窮舉先生成後去重），兩值皆非零且違反時 `raise RuntimeError`（僅守不變量，零值/邊界容忍不誤殺）；③ `run_tlc` 改呼叫 `parse_tlc_summary`；④ 新增 `tools/fsm_runtime/tests/test_tlc_runner_parsing.py`（4 case：last-match/正常不誤報/畸形 raise/無匹配回 0）。**無 FSM 狀態/規則變更**（`_HAPPY_PATH` 與 `*.tla` 零改動，Rule 9.18.1 不啟動）；ID_REGISTRY 維持 next_free act=173 / rule="9.39"，**不取新 ACT/rule**（純工具 bugfix）。**整合層（A 軌）DEF-01-008 同輪修**：AutoClaude `main.py` flag-gated brain 注入（落 AutoClaude repo，非 v0.04 本體；見 improving_03 §2）。 |
| **TLC 證據** | 雖未觸發 Rule 9.18.1（無 `_HAPPY_PATH`/`.tla` 改動），仍跑五軌 TLC 驗證**修正本身正確**（last-match 取對最終 summary、generated ≥ distinct）。實測（2026-06-14，`python -m tools.fsm_runtime.tlc_runner --module <各軌>`，v0.04 目錄，exit 0 / No error found）：<br>• **SDD_FSM**：DISTINCT=855 / GENERATED=**4706** / DEPTH=14<br>• **META_FSM**：13 / 24 / 6<br>• **FLEET_FSM**：7 / 8 / 7<br>• **COMPOSITION_FSM**：21 / 28 / 7<br>• **OPTIMIZATION_FSM**：12 / 21 / 5<br>**DEF-02-002 修復鐵證**：SDD_FSM GENERATED 由舊 first-match 誤報 **706** 修正為 last-match 真值 **4706**，`generated(4706) >= distinct(855)` 恆等不變量**現已成立**（舊「distinct 855 > generated 706」錯配徹底消除），且 fail-closed 斷言未誤殺（因已合法）。五軌 liveness（EventuallyTerminal/ObservationsTransient）+ safety 全過、0 violation。 |
| **回退指引** | tlc_runner 修正為向後相容純函式重構（對外行為僅「計數更準 + 畸形 fail-closed」）；回退即把 `tlc_runner.py` 指回 v0.03（first-match 版，計數不可靠但停機判準 `No error has been found` 不受影響）。AutoClaude 端 DEF-01-008 回退：`config.yaml` 移除 / 設 `minimax.enable_kernel_brain=False`（預設）即恢復 brain=None production 行為，零 breaking change。 |

## v0.02 → v0.03

| 欄位 | 內容 |
|------|------|
| **版本** | v0.02 → v0.03 |
| **日期** | 2026-06-13（凍結來源：AutoSDD_improving_02.md，同日 🔴 人工確認凍結，W1 啟動） |
| **delta 清單** | **新增 ACT-172（Phase Z′，自 ID_REGISTRY next_free=172 起算）— `AUTOCLAUDE_DELEGATED` 觀察態落地**（improving_01 §6 Phase Z 提案 → 本輪正式落地，BRIDGE.md §5 三前置條件全數滿足）：① `tools/fsm_runtime/transition_rules.py` — `_HAPPY_PATH` 新增 key `AUTOCLAUDE_DELEGATED`（出邊 `{IMPLEMENTATION, ESCALATION}`，入口走 runtime enter_* 故不改 IMPLEMENTATION 出邊集）+ `OBSERVATION_STATES` frozenset 新增成員；② `tools/fsm_runtime/fsm_runtime.py` — 新增 `enter_autoclaude_delegated()` / `exit_autoclaude_delegated()`（forced-transition，比照 `enter_memory_consolidation`；done→IMPLEMENTATION / failed→ESCALATION）；③ `tools/fsm_runtime/formal/SDD_FSM.tla` — `ObservationStates` + 入口 action `T_EnterAutoclaudeDelegated` + 出口 `T_AutoDelegToImpl`/`T_AutoDelegToEsc` + `Next` disjunction + Fairness `SF_vars(T_AutoDelegToImpl)`（破 IMPLEMENTATION↔AUTOCLAUDE_DELEGATED 2-cycle，保 EventuallyTerminal）；④ `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` 狀態轉換表新增兩出口列；⑤ `tools/fsm_runtime/tests/test_phase_z.py`（8 case 驗 enter/exit/邊界/不變量）。**新增 FSM 狀態：AUTOCLAUDE_DELEGATED（1 個觀測態）**。ID_REGISTRY：Phase Z′ range [172,172] 登記、next_free 推進 act=173 / rule="9.39"（本輪不取新 rule，state 受 R-9.18 既有規則治理）。**整合層（A 軌）DEF-01-004 同輪修**：AutoClaude `ci.yml:189` pg-e2e cron 過濾（落 AutoClaude repo，非 v0.03 本體）。 |
| **TLC 證據** | **五軌 TLC 重跑全綠**（`_HAPPY_PATH` + `SDD_FSM.tla` 變更觸發 Rule 9.18.1 義務）。實測（2026-06-13，`python -m tools.fsm_runtime.tlc_runner --module <各軌>`，exit 0 / No error found）：<br>• **SDD_FSM**：DISTINCT=855 / GENERATED=706 / DEPTH=15<br>• **META_FSM**：DISTINCT=13 / GENERATED=24 / DEPTH=6<br>• **FLEET_FSM**：DISTINCT=7 / GENERATED=8 / DEPTH=7<br>• **COMPOSITION_FSM**：DISTINCT=21 / GENERATED=28 / DEPTH=7<br>• **OPTIMIZATION_FSM**：DISTINCT=12 / GENERATED=21 / DEPTH=5<br>liveness（EventuallyTerminal / ObservationsTransient）+ safety（含 ObservationStates ∩ Terminals = ∅）全過。<br>🔸 raw DISTINCT/GENERATED 為 `tlc_runner` 自報值（SDD_FSM 855/706 經 2026-06-14 親跑重現一致）；惟 `distinct > generated` 違反 TLC 不變量，係 `_grp` re.search 取首個 progress 行非最終 summary 之工具瑕疵（記 **DEF-02-002**，routed v0.0Y），**權威停機判準以穩定且跨 agent 一致的 `No error has been found / 0 violation` 為準**，raw 計數僅供參考。 |
| **回退指引** | AutoClaude 端：`sdd_compile --spec-dir` 與 SddGovernancePlugin 的 `workflow_path` 指回 `AISDLC_SDD_v0.02/`（或更早 v0.01）即完成回退（v0.03 對 AutoClaude 介面零 breaking change——新增的 `AUTOCLAUDE_DELEGATED` 為 SDD 框架內部 FSM 觀測態，AutoClaude 側不依賴其存在）。已知不相容點：v0.02 無 `AUTOCLAUDE_DELEGATED` 狀態與 `enter_autoclaude_delegated` API——回退後若有委派執行語意需求，僅能停留 IMPLEMENTATION（無專屬觀測態追蹤）；既有 FSM-STATE 狀態檔（未含此態）載入 v0.03 完全相容（純加法，舊 decision_trace 不變）。 |

## v0.01 → v0.02

| 欄位 | 內容 |
|------|------|
| **版本** | v0.01 → v0.02 |
| **日期** | 2026-06-12（凍結來源：AutoSDD_improving_01.md，同日 🔴 人工確認凍結） |
| **delta 清單** | **新增 ACT-162~171（Phase Z，自 ID_REGISTRY next_free=162 起算）**：① `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`（SDD→Playbook 標準作業，ACT-162）② `agent/specialized/sdd-playbook-compiler-zh.yaml`（編譯者角色，ACT-163）③ `governance/rules/R-9.38-playbook-translation-fidelity.yaml`（AT↔step 100% 雙向映射，違反→SPEC_AUDIT，ACT-164）④ 10 場景 SOP 各加「§AutoClaude 自動化執行」小節 + QuickRef 同步（ACT-165~171）。**新增 FSM 狀態：無**（`AUTOCLAUDE_DELEGATED` 維持提案，落地前置條件見 BRIDGE.md §5）。**缺陷修正（自 AutoSDD_Defect_Log 分流）**：DEF-01-001（RULES_INDEX.md 計數 35→39 檔 + next-act/next-rule 前緣同步）、DEF-01-002（run_tlc.sh 補「五軌請走 tlc_runner.py」legacy 註記）、DEF-01-003（`tools/__init__.py` 顯式 package 宣告）。ID_REGISTRY：Phase Z range [162,171] 登記、next_free 推進 act=172 / rule="9.39"。**根層文件計數同步（三專家審查 DEF-01-010）**：`AISDLC_SDD_INIT.md` / `README.md` 等根層文件 agent 計數 25/18 → 26/19 同步（v0.02 +sdd-playbook-compiler） |
| **TLC 證據** | **N/A** — `_HAPPY_PATH` 與全部 `*.tla` 零修改（diff 為空），依 Rule 9.18.1 無重跑義務；五軌 TLC 既有證明維持有效。`AUTOCLAUDE_DELEGATED` 落地時（v0.03+）必附五軌 TLC_DISTINCT/GENERATED/DEPTH 輸出 |
| **回退指引** | AutoClaude 端：`sdd_compile --spec-dir` 與 SddGovernancePlugin 的 `workflow_path` 指回 `AISDLC_SDD_v0.01/` 下的專案 docs 即完成回退（v0.02 對 AutoClaude 介面零 breaking change）。已知不相容點：v0.01 無 R-9.38 與 sdd-autoclaude-bridge workflow——回退後 AT↔step 保真檢查無治理規則承載（僅靠 AutoClaude 側 adapter 測試守護）；v0.01 `RULES_INDEX.md:9` 計數仍為過期值（屬凍結基線既有債務，不回改）。回退驗證：根層 `tools/integration_gate.ps1` 的 **[4/5] 回退驗證段**（`AutoClaude/tests/integration/test_sdd_bridge/test_rollback_compat.py`）——以 subprocess 用 v0.01 / v0.02 **各自的** `tools.fsm_runtime.state_loader` 產出真品 FSM 狀態檔（load_state → record_spec_frozen → save_state），再由 `autoclaude.tools.sdd_compile.compile_spec` 消費並斷言編譯出 3 步驟，證明指回 v0.01 後規格鏈路仍可編譯；[3/5] test_sdd_bridge 煙霧亦須全綠 |
