# SD_09 W3 Round 7 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — Architect/SA/SD/QA 全能 zero-trust audit Round 6 修復成果 + nightly 第 2 跑（commit 8c5ed75）三維驗證 |
| Audit Round | W3 Round 7（2026-05-25）|
| Audit 發現 | **0 P0 + 0 P1 + 2 P2**（防禦性編碼一致性，全部本輪修復）|
| pytest 基線 | **2,505 passed / 122 skipped**（與 Round 6 同；P2 修復未動測試）|
| importlinter | 7 kept / 0 broken |
| LOC violations | 0（CLAUDE.md=400 ≤ 400 / total 15,050 ≤ cap 16,869）|
| Nightly 真實取證 | [logs/nightly_2026-05-25_110459.log](../../logs/nightly_2026-05-25_110459.log) 6 stages 全綠 / 觀察期進度 mutation=4/7 ac4=4/14 obs=3/30 drift=3/30 |
| §3.0 並行框架 | 4 軸並行驗證真實可執行（軸 B/C/D 隨時可推進，軸 A 待 schtasks 啟用）|

---

## 1. Audit 取證

| 項目 | 取證 |
|------|------|
| Nightly run 1 (Round 6 基準) | [logs/nightly_2026-05-25_090013.log:L242-244](../../logs/nightly_2026-05-25_090013.log) |
| Nightly run 2 (Round 7 第 2 跑) | [logs/nightly_2026-05-25_110459.log](../../logs/nightly_2026-05-25_110459.log) 5:50 全程；perf=2 為 BLOCK→WARN undersampled 退化（紀律 #1 符合）|
| 觀察期 jsonl 累計 | mutation 4 / ac4 4 / obs 3 / drift 3（M-05 同 UTC date dedup → run 2 同日不進帳，符合設計）|
| 紀律 13 條 | **全數通過**（Audit Agent 逐條檢查；詳見第 4 節）|

---

## 2. Round 7 真實修復（本輪 commit 已 CLOSED）

| ID | 嚴重度 | 狀態 | 根因 | 修法 | 主要檔案 |
|----|--------|------|------|------|---------|
| **P2-AUDIT-R6-A** 裸 `$ExistingContainer`/`$EphemeralContainer` 7 處讀取 | P2 | ✅ FIXED | Round 4 P1-AUDIT-R3-4 修了 `$DockerOK`/`$UsedContainer`/`$ContainerOwned`，但漏 `$ExistingContainer`/`$EphemeralContainer` 7 處讀取（line 206/208/209/210/213/214/216）→ 違反「跨 scope 變數統一 `$script:` 前綴」一致性紀律；當前 dynamic scope 可解析（strict mode 不 trigger），但後續若抽 function 會壞 | 統一補 `$script:` 前綴 + 註明 Round 4 R3-4 一致性紀律補完 | [tools/run_local_nightly.ps1:206-216](../../tools/run_local_nightly.ps1#L206-L216) |
| **P2-AUDIT-R6-B** `if ($LASTEXITCODE)` PS truthy 對負值誤判 | P2 | ✅ FIXED | PowerShell `if (-1)` 為 true → 若內部 scriptblock 顯式設 `$global:LASTEXITCODE=-1`（如 SKIP_RC=-1 內部使用），$rc 會變 -1 進入 ERROR 分支；當前無 trigger 但語意不明 | 改 `if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0)` 明示語意 | [tools/run_local_nightly.ps1:139](../../tools/run_local_nightly.ps1#L139) |

---

## 3. 推翻項（Audit Agent 提出但驗證後不成立）

| 原指控 | 取證 | 結論 |
|--------|------|------|
| `test_evaluate_dual_track_*` 三個 evaluate-直呼測試疑為 time-flaky | 深查 evaluate() 函式無 datetime.now 依賴（不過 filter_recent），測試造的 records 直接傳入 evaluate() 不會被 cutoff 過濾 | 推翻；偽報撤回 |

---

## 4. 13 條紀律盤點（全數通過）

| # | 紀律 | 通過 | 取證 |
|---|------|------|------|
| 1 | stage rc 區分真實失敗 vs 工具標準回報（mutmut bitmask）| ✅ | `mutmut_exit_code.py classify` bit0 判定；本輪 P2-B 修復語意更明確 |
| 2 | log 含完整統計（cache 5 行 counts）| ✅ | L158-162 5 行 marker section 擷取 |
| 3 | PASS 引用 RunId log:L | ✅ | 本報告所有 PASS 均引取證 |
| 4 | 驗證鏡子自身要被驗證 | ✅ | tests/tools/ 183 passed（mutmut_exit_code / validate_mutmut_log / mutation_baseline_lock / ac4_progress_check / observability_ga_check 全有單元測試）|
| 5 | 跨工具數字對齊 | ✅ | mutation_analysis / baseline_lock 共用 marker section 為單一真相 |
| 6 | 採集寬鬆 + 升級嚴格分軌 | ✅ | _COLLECTOR_P95 (80) / _STRICT_P95 (50) 兩條獨立 env |
| 7 | cache fresh | ✅ | .mutmut-cache / .pytest_cache / .ac4_junit.xml / perf_results.json 跑前 rm |
| 8 | .sh LF 行尾 | ✅ | `file run_mutmut_in_docker.sh` = text executable 無 CRLF |
| 9 | 跨 stage SKIP 一致性 | ✅ | mutation/pg-e2e/drift 三 stage Docker 不可用時統一 `$SKIP_RC=-1` |
| 10 | fallback 路徑 jsonl 布林標記 | ✅ | observability_emit_real 欄位；strict 模式拒絕 False |
| 11 | latest log pointer 完整 run | ✅ | ps1 L584 末段 `Copy-Item` + FileShare.ReadWrite + retry |
| 12 | mutation history unique sha | ✅ | should_lock 4 case test 全綠；當前 jsonl 永遠拒鎖（符合設計）|
| 13 | 觀察期 jsonl 累計進度可見 | ✅ | `END observation progress: mutation=4/7 ac4=4/14 obs=3/30 drift=3/30` |

---

## 5. W1 啟動前未決項（沿用 Round 6，本輪未新增）

| ID | 項目 | 狀態 |
|----|------|------|
| ADR-SD09-008 | AC4 雙軌 p95 三選項 PM 拍板 | PROPOSED v0.2（cut-off **2026-05-31**；逾期自動「過渡寬限」）|
| 觀察期 #1 | mutation pilot TokenGuardPlugin 連續 7 次 ≥ 70% + 紀律 #12 unique sha | 累計 4/7 jsonl（後 2 同 sha=5208cff397beecc5）→ 永遠拒鎖；**W1 必須補 token_guard test 提升 unique source** |
| 觀察期 #2 | AC4 14 天 nightly 全綠（strict 50ms）| **數學上不可達標**（真實 p95 51-53ms）— 待 PM 拍板 ADR-SD09-008 |
| 觀察期 #3 | drift_log 30 天零事件 | 累計 3/30；達標日 2026-06-24（若 user 5/25 啟用 schtasks）|
| P2-AUDIT-R4-1 | mutation_baseline_lock dedup stderr | W1 backlog |
| P2-AUDIT-R4-2 | AC4 jsonl 雙 status 欄 | W1 backlog |

---

## 6. 下一步執行檔案與大綱（依 §3.0 4 軸並行框架）

### 6.1 接下來 30 天 8 大動作（沿用 Round 6 + schtasks 啟用前置）

| # | 時間 | 動作 | 軸 |
|---|------|------|----|
| 1 | **🔴 立即（2026-05-25 Round 7 修復通過後）** | **user 手動啟用 schtasks**：`schtasks /change /TN "AutoClaude_Nightly" /ENABLE` — 觀察期累計起算 | 軸 A 前置 |
| 2 | 每日 02:00（Task Scheduler `AutoClaude_Nightly`，啟用後）| 自動跑 `tools/run_local_nightly.ps1`（含 R5 觀察期進度行 + R7 P2 修復）| 軸 A |
| 3 | **≤ 2026-05-31** | PM 拍板 ADR-SD09-008 三選項 | 軸 C |
| 4 | 任意時點（建議 ≤ T+10）| **軸 B**：補 token_guard test 64 點位 → source_sha256 變動 → 觀察期 #1 重置 unique sha | 軸 B |
| 5 | 2026-06-08（5/25 啟用 +14）| 觀察期 #2：ac4_progress_check ready_for_labeled_pr（依 PM 拍板）| 軸 A #2 |
| 6 | 2026-06-02 → 軸 B 完成後 +7 | 觀察期 #1：mutation 連 7 次 ≥ 70% + unique sha | 軸 A #1 |
| 7 | 2026-06-24（5/25 啟用 +30）| 觀察期 #3：drift_log_ga_check --window 30 | 軸 A #3 |
| 8 | 2026-06-25 ~ 2026-07-03 | G0 啟動窗口 → W1 GoalSynthesisPlugin mutation pilot | 軸 D 收斂 |
| 9 | 每次新 session 前 | 依 [SD09_Execution_Guide.md §0.3](SD09_Execution_Guide.md#03-每次開啟新-session-前必跑) 5 條檢查（pytest ≥ 2,505）| 全軸 |

### 6.2 W1 啟動前 backlog（沿用 Round 6，本輪未新增）

- P2-AUDIT-R4-1 mutation_baseline_lock dedup 印 stderr
- P2-AUDIT-R4-2 AC4 jsonl 拆 collector_status / strict_status 雙欄

---

## 7. 收斂評估與成熟度

### 7.1 收斂訊號（正向）

- **連續 7 輪 audit 已將「nightly 取證紀律」鎖緊**：13 條全數通過（Round 7 未新增紀律 — 已飽和）
- **Round 6 三項取證修復 zero-trust 驗證真實生效**：time-flaky 永久解決 / 6 stages 全綠 / 13 條紀律
- **Round 7 真實 0 P0 / 0 P1**：僅 2 項 P2 防禦性編碼，本輪修畢；無破壞 SD_07/SD_08/Round1-6 收斂
- **無破壞 §3.0 並行框架**：未動 importlinter / LOC budget / Plugin / 公開 API；僅修 1 個 PS 變數命名 + 1 個條件式語意
- **Nightly 真實全綠**：第 2 跑（commit 8c5ed75）6 stages 全綠 + M-05 dedup 正確未灌水

### 7.2 仍未收斂訊號（沿用 Round 6 §8.2）

- **schtasks 等 user 手動啟用**：Round 7 修復通過為前提；user 於 5/25 啟用後觀察期時間軸從 5/25 起算
- **觀察期 #2 數學上不可達標**：strict 50ms vs 真實 51-53ms；依賴 PM 拍板 ADR-SD09-008（cut-off 5/31）
- ~~**觀察期 #1 真實 kill_rate 74.5%** 已 ≥ 70% 容忍門檻但 source 未變 → 紀律 #12 永遠拒鎖；**W1 必須補 token_guard test**~~

> **⚠️ Round 8 audit 推翻（2026-05-25）**：本條敘述「kill_rate 74.5% 已 ≥ 70%」已過時。Round 8 nightly run 3（commit 9896c9b, run_id=114142）取得 kill_rate=69.80%（killed=104 / suspicious=7 / mutmut timing noise），**已跌破 threshold=target-tolerance=0.75-0.05=0.70**；should_lock line 246 short-circuit 先行拒鎖（非 unique sha 不足）。觀察期 #1 真實阻塞點修正為「unique sha 不足 + kill_rate timing noise 跌破門檻」**雙重數學阻塞**。詳見 [SD09_W3_Round8_NextAction.md §2 P1-NEW-1](SD09_W3_Round8_NextAction.md#2-round-8-真實修復本輪-commit-已-closed)。

### 7.3 專案成熟度評估（與 Round 6 同基準）

| 維度 | 評分 | 變動 |
|------|------|------|
| 架構 / 程式碼品質 | 🟢 A | 不變 |
| 測試覆蓋 | 🟢 A（2,505）| 不變（P2 修復未動測試）|
| CI / nightly 治理 | 🟢 A- | 不變（**7 輪 audit 鎖緊收斂，13 條紀律飽和**；schtasks 啟用後進入「持續累計」）|
| 觀察期升級條件 | 🔴 C | 不變（依賴 PM 拍板 + W1 補測）|
| 文件治理 | 🟢 A | 不變（CLAUDE.md 400 ≤ 400）|
| PG production 上線就緒 | 🟡 B | 不變 |
| 整體 SD_09 進度 | 🟡 W0 採集中 | 不變 |

**結論**：**Round 7 為 7 輪 audit 終極收尾**。13 條紀律全數通過（已飽和，難以新增）；P2 防禦性編碼順手修復；nightly 第 2 跑真實全綠；§3.0 4 軸並行框架驗證真實可執行。**架構 / 文件 / 測試 / CI nightly 治理皆達 production-grade 成熟度（A 或 A-）**；P0-B time-flaky 測試永久根因已修；user 5/25 啟用 schtasks 後即啟動觀察期 30 天計時；W5 production cutover 仍受觀察期 #2 數學阻塞，依賴 PM 拍板 ADR-SD09-008（cut-off 2026-05-31）。

---

**版本紀錄**：v1.0 2026-05-25 — Round 7 audit 修復收尾；對應 commit `9a3516c` / tag `v2026.05.25-06` / merge main `2fd8b43` ✅ pushed to https://github.com/wuweihungmobile/AutoClaude。
