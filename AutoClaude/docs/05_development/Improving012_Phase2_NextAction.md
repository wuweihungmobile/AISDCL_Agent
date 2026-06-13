# Improving012 Phase 2（閉環強化 B 能力）完成後 Next Action

**日期**: 2026-06-13 | **狀態**: Phase 2 ✅ 完成（F-B1 AlertLadder + F-B2 CorrectionVerifier 全交付 + zero-trust audit 修復收斂）
**權威計畫**: [AutoClaude_Improving_012.md](../04_planning/AutoClaude_Improving_012.md)（SCG-0 凍結；Phase 2 checkbox 已勾）

## Phase 2 結果摘要

- **閘門**：SCG-1（[SRD_AGT_Phase2_Closedloop](../02_architecture/SRD_AGT_Phase2_Closedloop.md)）+ SCG-2（[ADR-AGT-004](../04_planning/ADR/ADR-AGT-004-alert-ladder-correction-verify.md) ACCEPTED/LANDED）皆經 koalawu 🔴 互動確認。
- **交付**：F-B1 AlertLadder 三階梯（WARNING→HINT→ESCALATE，feature flag `alert_ladder.enabled` 預設 off）攔截 `_impl.py:297` 收斂升級唯一 call site，HINT 為本地文字（不呼叫 Brain）經既有 `strategy_hint` 通道注入；F-B2 CorrectionVerifier（signature/fail_count/exit_code 三分量純本地比對）+ no_improve_streak 提前升級（門檻 1~5 可配置，預設 2）+ KB `record_strategy_failure` 失效回寫（常開 additive）。**無新 port/plugin、零 alembic**：階梯/streak 計數落 `PlaybookCheckpoint.alert_ladder` additive 欄（File）+ PG `checkpoints.counters` JSONB 子鍵；五條存檔路徑接線（interrupt / token-halt / evolution×3 / Kernel payload）。
- **Zero-trust audit**（三方並行 Architect / SA·SD / QA）：P0=0 / P1×3（evolution-resume 漏傳接線、PG mock 往返測試缺、config bounds 裸 Exception）/ P2×4 → **全數修復**。evolution-resume 修法經 koalawu 🔴 拍板採「接線修復」（讓實作符合凍結 SRD §1.4 三條 additive 路徑承諾）。
- **QA 最終複審 PASS**：變異實證 4/4（逐一回退修復點驗測試真會紅 → 確認非 tautology，還原後 byte-level 復原）；F-B1/F-B2 原設計目標完整、無破壞收斂閉環（flag-off byte-level 零回歸 + F-B2 常開副作用經 `TestFlagOffKbInvariant` 證明不污染 strategy 選擇）。
- **最終閘門（親跑複核）**：full pytest **3,020 passed / 122 skipped**（前基線 2,972，+48 零回歸）、新模組 coverage **100%**（alert_ladder 52 stmts / correction_verifier 45 stmts 均 0 miss）、importlinter **8 kept / 0 broken**、LOC=0（total 17,041 ≤ cap 20,438）、snapshot OK。

## Next Action（依凍結計畫順序）

1. **SCG-6（Phase 2 flag 轉正）**：F-B1 `alert_ladder.enabled` 預設 off → **nightly 連續 7 天綠後轉預設 on**（凍結計畫 §5 Phase 2 + SCG-6）。轉正前須確認 nightly 5 stage 不受新 .jsonl/checkpoint 欄位干擾（QA 查核：Phase 2 對 nightly 5 stage 零影響、載具無需調整）。
2. **Phase 3 — 自主拆解與工具（A 能力，風險最高最後）**：先過 SCG-1（SRD 增補：ToolInvocationPort 介面 + allowlist 安全閘規格 🔴）→ SCG-2（ADR-AGT-001 工具安全閘 / ADR-AGT-002 拆解有界性 🔴）→ F-A2 ToolInvocationPort + allowlist（先行）→ F-A1 GoalDecomposer（goal→步驟 DAG，硬上限 ≤24 步 + 無環檢查 + 🔴 人工 signoff 後執行）。

## Audit / 觀察 backlog

| 項目 | 說明 | 建議時點 |
|------|------|---------|
| 新模組 mutation 強度 | alert_ladder / correction_verifier 不在 token_guard mutation 範圍，僅行覆蓋 100%（無變異強度保證） | Phase 3 期間搭 nightly mutation stage 擴範圍 |
| ruff 鎖版 + 全量清理 | 沿前輪 backlog（~1,330 errors；ci.yml 不跑 ruff）；本輪僅守住新增檔零違規 | 另開工作項 |
| PG adapter pg_real e2e | alert_ladder counters 子鍵已有 mock 往返防線，真 PG e2e 待 `SD07_REAL_PG_E2E_ENABLED` | Phase 3 期間搭 nightly pg-e2e |
| perf 載具偽陽性根治 | agent PowerShell 載具 CPU 膨脹（Phase 0/1/2 模式穩定）；建議 perf stage 內建 BLOCK 時自動 Bash 載具對照重測 | nightly 強化項 |

## AISDLC_SDD_v0.01 開發流程問題記錄（下輪改善，依使用者指示）

| # | 問題 | 證據（本輪實證） | 建議改善 |
|---|------|----------------|---------|
| 5 | **SCG-1「擴充點實證表」未涵蓋持久化/存檔路徑** | SRD §1.4 文字承諾「三條 additive 存檔路徑（interrupt / evolution / token-halt）」，但 §0 擴充點實證表只列注入/hook 點，未把三條 save 路徑當作須附 `檔案:行號` + 觸發實證的擴充點 → evolution-resume 漏傳 alert_ladder 直到 audit 才發現 | 擴充點實證表範圍擴及「所有宣稱會持久化新欄位的 save 路徑」，每條附呼叫端 `檔案:行號` 並要求一條往返測試覆蓋（延伸流程改善 #1） |
| 6 | **SRD §4 列出的 TC 未被 SCG-4 機械核對是否存在** | SRD §4 明列「checkpoint 持久化往返（File+**PG mock**）」為驗收 TC，但實作初版只做 File、PG mock 缺漏；RTM 未在凍結→交付間機械比對「§4 每條 TC 是否真有對應測試檔/case」，直到 audit 才補 | SCG-4 閘門增「SRD §4 驗收 TC 清單 vs 實際測試函式」自動對照檢查（缺一條即 fail），不靠人工目視 RTM |
| 7 | **SRD 文件內測試路徑與實際落點未校驗** | SRD §4 宣稱 `tests/execution/test_alert_ladder.py`，實際落 `tests/test_alert_ladder.py` → RTM 路徑追溯失準 | SCG-1 凍結前/SCG-4 交付時，文件內所有 `tests/...` 路徑須 glob 實證存在（可機械化，比照紀律 #17） |

---
**產出**: 主 agent（Claude Code）依 AISDLC_SDD SCG 流程執行；audit 取證見 [sprint_history.md §1.7.3](sprint_history.md) Improving_012 Phase 2 段。
