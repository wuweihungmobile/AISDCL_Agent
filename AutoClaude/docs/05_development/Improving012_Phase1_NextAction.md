# Improving012 Phase 1（記憶基座）完成後 Next Action

**日期**: 2026-06-13 | **狀態**: Phase 1 ✅ 完成（F-C3 / F-C1 / F-C2 全交付 + zero-trust audit 修復收斂）
**權威計畫**: [AutoClaude_Improving_012.md](../04_planning/AutoClaude_Improving_012.md)（SCG-0 凍結；Phase 1 checkbox 已勾）

## Phase 1 結果摘要

- **閘門**：SCG-1（[SRD_AGT_Phase1_Memory](../02_architecture/SRD_AGT_Phase1_Memory.md)）+ SCG-2（[ADR-AGT-003](../04_planning/ADR/ADR-AGT-003-memory-layering.md) ACCEPTED）皆經 koalawu 🔴 互動確認。
- **交付**：F-C3 採 ACCEPTED ADR-SD09-006 canonical（IKbMetricStore + Local/Pg adapter + alembic 0016 + importlinter Rule 8，7→8 kept）；F-C1（IPreferenceStore + PreferenceMemoryPlugin + Kernel 補發 PRE_CORRECTION + correction prompt 注入鏈）；F-C2（GoalProgressLedger File/Pg + GoalProgressPlugin + POST_RUN payload）。ports 10→12、plugins 14→16 active、PG 3 新表。
- **Zero-trust audit**（三方並行，2 輪複審）：第 1 輪 QA 條件式 PASS（P0=0 / P1×7 / P2×6）→ 全數修復（coverage 92% 出證 / mutation 隔離樹紀律 #18）；Architect / SA·SD agent 遭 session 額度截斷 → 主 agent 補位複核並**修復 PG UPSERT `"now()"` 字面字串 bug**。第 2 輪：QA 複審 **OVERALL PASS**（13 項修復全真實收斂、無設計破壞）；Architect+SA·SD 複驗揪出 **P1-1 resume 進度口徑缺口** → 即修（kernel POST_RUN 補 resume_prior_ids + 去重 + 3 測試 + SRD 口徑）+ P2×4 全修（Rule 1 清單補齊 / ADR 元數據 / wiring docstring / run_id 接縫明示）；攻擊 6 點全敗。
- **Nightly**：紀律 #18（mutation 隔離樹）落地後實跑驗證 — kill_rate 76.51% 與隔離前基線一致（隔離未破壞突變耦合）；perf stage 一次 BLOCK（decide_correction +30.1%）經 Bash 載具對照實驗（p95 2495.7ms，+4.2% PASS）證實為 PowerShell 載具 CPU 膨脹偽陽性（與 Phase 0 取證同模式），非源碼回歸。
- **最終閘門（修復後親跑）**：full pytest **2,972 passed / 122 skipped**（前基線 2,853，+119 零回歸）、importlinter **8 kept / 0 broken**、LOC=0（total 16,736 ≤ cap 16,869）、snapshot OK；nightly run_id=040216 六 stage 全綠。

## Next Action（依凍結計畫順序）

1. **Phase 2 — 閉環強化（B 能力）**：先過 SCG-1（SRD 增補：AlertLadder 三階梯 + Correction 效果驗證介面 🔴）→ SCG-2（ADR-AGT-00x 🔴）→ F-B1 AlertLadder（feature flag 預設 off → nightly 觀察 7 天 → 預設 on）→ F-B2 Correction 效果事後驗證 + KB 失效回寫。**前置注意**：F-B1 需 checkpoint 增 alert_ladder 欄位（alembic 0017）；F-B2 error_signature 比對走本地不呼叫 Brain。
2. **Phase 3 — 自主拆解與工具（A 能力）**：F-A2 ToolInvocationPort + allowlist → F-A1 GoalDecomposer（🔴 signoff）。
3. **SCG-6（Phase 1 殘留）**：Phase 1 無 feature flag 項，SCG-6 以「nightly 連續 7 天綠（含新 .jsonl 落地檔不干擾 drift/obs 判定）」為觀察口徑。

## Audit / 觀察 backlog

| 項目 | 說明 | 建議時點 |
|------|------|---------|
| ruff 鎖版 + 全量清理 | 沿前輪 backlog（~1,330 errors；ci.yml 不跑 ruff）；本輪僅守住新增檔零違規 | 另開工作項 |
| PG adapter pg_real e2e | Phase 1 三 PG adapter 已有 mock 單元防線（92% coverage），真 PG e2e（alembic 0016 upgrade + UPSERT 實打）待 `SD07_REAL_PG_E2E_ENABLED` 環境跑 pg_real marker | Phase 2 期間搭 nightly pg-e2e stage |
| perf 載具偽陽性根治 | agent PowerShell 載具 CPU 膨脹（Phase 0 + Phase 1 各取證一次，模式穩定）；建議 perf stage 內建「BLOCK 時自動 Bash 載具對照重測」 | Phase 2 nightly 強化項 |
| audit agent 額度韌性 | 三方並行 audit 兩個 agent 於輸出階段遭 session limit 截斷（62/52 工具呼叫的審查工作丟失）；建議 audit prompt 要求「中途分段落盤結論」 | 下輪 audit SOP |

## AISDLC_SDD_v0.01 開發流程問題記錄（下輪改善，依使用者指示）

| # | 問題 | 證據（本輪實證） | 建議改善 |
|---|------|----------------|---------|
| 1 | **SCG-1 規格模板缺「擴充點實證」檢查項** | SRD §2.3 凍結時假設 `PRE_CORRECTION` 有 dispatch，實際 hookspec 僅定義、Kernel 從未發布；至實作期才發現，被迫凍結後修正留痕 | SRD 模板 / SCG-1 checklist 增列「所有宣稱之 hook/注入/擴充點必須附源碼 `檔案:行號` 實證其存在且被觸發」 |
| 2 | **ACCEPTED ADR 的落地承諾無追蹤機制** | ADR-SD09-006（2026-05-20 ACCEPTED）承諾 W2/W3 落地 port + alembic 0015 + Rule 8，從未落地且無人發現（0015 還被 merge revision 佔用），直到本輪 gap 分析撞上才整併 | governance 增 R-* 規則：ADR 含工程落地承諾者必須有「落地狀態欄」（PLANNED/LANDED/SUPERSEDED）+ 定期（每 Sprint 末）drift 稽核 ADR 承諾 vs 源碼實況 |
| 3 | **多 agent 並行 audit 與取證載具互踩** | nightly mutation 就地突變主機樹期間 QA agent 親跑 pytest 出現 2 假紅（mutmut 變異特徵字串）；audit 可信度帶噪 | AISDLC_SDD 多 agent 編排規範增「破壞性取證載具（mutation/chaos）必須隔離執行樹，且執行期間禁止並行驗證」（AutoClaude 已立紀律 #18 可移植） |
| 4 | **🔴 人工閘門的互動時序未定義** | SCG-1/SCG-2 🔴 確認以 AskUserQuestion 互動完成有效率；但凍結文件「checkbox 勾選」與「互動核准」兩種形式並存，RTM 追溯時需翻對話紀錄 | SCG 閘門規範明定：互動核准後必須立即回填文件確認欄（確認人/日期/方式），文件為唯一追溯源 |

---
**產出**: 主 agent（Claude Code）依 AISDLC_SDD SCG 流程執行；audit 取證見 [sprint_history.md §1.7.3](sprint_history.md) Improving_012 Phase 1 段。
