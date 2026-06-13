# ADR-AGT-004 — 閉環強化：AlertLadder 漸進升級 + Correction 效果本地驗證

| 項目 | 內容 |
|------|------|
| 編號 | ADR-AGT-004 |
| 狀態 | **ACCEPTED — koalawu 2026-06-13（SCG-2 🔴 AskUserQuestion 互動確認）** |
| 落地狀態 | **LANDED**（2026-06-13 Phase 2 交付；AlertLadder + CorrectionVerifier + checkpoint additive + 五存檔路徑接線；三方 audit + QA 複審 PASS） |
| 提出者 | sd-architect（Improving_012 Phase 2） |
| 提出日期 | 2026-06-13 |
| 對應計畫 | [AutoClaude_Improving_012.md](../AutoClaude_Improving_012.md) §5 Phase 2（SCG-0 已凍結） |
| 相依 ADR | ADR-AGT-003（記憶分層 L1/L2 落地通道）/ ADR-SD07-001（LOC 分級） |

## 1. 背景

B 能力（觀察→調整）判定 🟢 大致滿足，但收斂信號一觸發即 ESCALATION（單級跳），且 mutation/correction 套用後無效果事後比對——Brain 可能連續產出無效修正而系統無感知，直到重試耗盡。缺口：漸進升級、效果驗證、KB 策略失效回寫（凍結計畫 §1 F-B1/F-B2）。

## 2. 決策

1. **AlertLadder 三階梯**（WARNING→HINT→ESCALATE）攔截收斂升級唯一 call site（`_impl.py:278`），feature flag `alert_ladder.enabled` **預設 off**；階梯消耗既有 attempt 預算（不增加重試）、`max_retries`/ErrorBudget 保底不動 → 有界（對齊 R-9.23 / Rule 8 精神）。`environment_error` 與 F-B2 提前升級直接 bypass。
2. **HINT 為本地文字生成**，經既有 `strategy_hint` 通道注入，**不呼叫 Brain**（「code 能答就 code 答」；亦避免 Brain/Executor 邊界違規）。
3. **CorrectionVerifier 純本地效果比對**（signature / fail_count / exit_code 三分量），同 signature 無改善連續 N=2（可配置 1~5）→ 穿透階梯提前升級；每次無改善即回寫 KB `record_strategy_failure`（skip_strategies merge + 失效時清除 successful_strategy），回寫常開、控制流變更僅在 flag on 時生效。
4. **持久化零 migration**：階梯/streak 計數落 `PlaybookCheckpoint.alert_ladder` additive 欄位（File）+ PG `checkpoints.counters` JSONB 子鍵（既有欄，`_pg_models.py:95`）——**推翻原規劃之 alembic 0017**（實證見 SRD §0）。

## 3. 替代方案

| 方案 | 採用 | 理由 |
|------|-----|------|
| (a) 三階梯攔截 + 本地驗證（本案） | ✅ | 零回歸（flag off byte-level 不變）、有界、不增 Brain 成本 |
| (b) HINT 階呼叫 Brain 生成客製提示 | ❌ | Token 成本 + Brain 失效時階梯卡死；本地模板已含 trend/reasoning 足夠 |
| (c) 階梯計數獨立新表（alembic 0017） | ❌ | `counters` JSONB 既有且為 Gap-042 同類資料的既定落地點；新表/新欄違反 Rule 2 |
| (d) 效果驗證交由 ConvergenceMonitor 擴充 | ❌ | Monitor 職責是「趨勢判定」，效果驗證是「單次修正歸因」，混入將破壞 8 信號優先級語意；獨立模組各自可測 |
| (e) F-B2 提前升級不設 flag、立即常開 | ❌ | 與 is_stuck(2) 重疊區外的觸發時機會改變既有 escalation 時序，違反「既有測試零回歸」驗收 |

## 4. 後果

- 正面：收斂失敗獲得 2 次額外自救機會（HINT 注入強制換法）；無效修正最多 2 次即被本地偵測，不再吃滿重試預算；KB 品質隨失效回寫持續校正。
- 負面：execution 層 +2 模組；checkpoint dict 增 1 鍵；escalation 路徑分支複雜度 +1（以 flag off 直通與獨立模組測試緩解）。
- **LOC baseline 重鎖**：Phase 2 增量（~300 LOC，凍結計畫內範圍）使總量觸 SD_07 鎖定之 cap（17,032 > 14,058×1.2=16,869）；經 koalawu 2026-06-13 🔴 互動確認重鎖 `.loc_baseline=17,032`（新 cap=20,438，`check_loc_budget.py --update` 既定程序），棘輪繼續防爆漲。
- 風險：階梯緩階期間多消耗 1~2 次 Brain correction 呼叫 → 緩解：僅 flag on 生效，SCG-6 nightly 觀察 7 天後才轉正。

## 5. 參考

- [SRD_AGT_Phase2_Closedloop.md](../../02_architecture/SRD_AGT_Phase2_Closedloop.md)（SCG-1 介面規格 + 擴充點實證表）
- [ADR-AGT-003](ADR-AGT-003-memory-layering.md) / [ADR-SD07-001](ADR-SD07-001-loc-policy.md)

---

**文檔元數據**：v1.0 ACCEPTED | 建立 2026-06-13 | SCG-2 🔴 確認欄：koalawu 2026-06-13（互動確認，與表頭狀態一致）
