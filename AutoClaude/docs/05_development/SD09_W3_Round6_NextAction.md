# SD_09 W3 Round 6 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — Architect/SA/SD/QA 全能 zero-trust audit Round 5 修復成果 + nightly 程式 / 過程 / 結果驗證 |
| Audit Round | W3 Round 6（2026-05-25）|
| Audit 發現 | 1 項 P0 真實 bug + 2 項 P0 文件 / 環境校準；P1=0；P2=0 |
| 真實修復 | P0-AUDIT-R5-B 已 CLOSED；P0-A / P0-C 為文件 / 環境同步項 |
| pytest 基線 | **2,505 passed / 122 skipped**（與 Round 5 同；P0-B 修復前 5 failed / 2,500 passed，修復後恢復）|
| importlinter | 7 kept / 0 broken |
| LOC violations | 0（CLAUDE.md=394 ≤ 400 / total 15,050 ≤ cap 16,869）|
| Nightly 真實取證 | [logs/nightly_2026-05-25_090013.log](../../logs/nightly_2026-05-25_090013.log) `L242` `END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0`；`L244` `END observation progress: mutation=4/7 ac4=4/14 obs=3/30 drift=3/30` |

---

## 1. Audit 取證

| 項目 | 取證 |
|------|------|
| Nightly run | `logs/nightly_2026-05-25_090013.log:L242-244` 6 stages exit=0 + 觀察期進度行 |
| mutation 真實取證 | `L158-162` Killed=111 / Survived=38 / Timeout=0 / Suspicious=0 / Skipped=0；kill_rate=74.5% ≥ 70%；mutation stage elapsed=04:58.128（真實 149 mutant × ~2sec/each ≈ 5min；非 cache fake — `source_sha256=5208cff397beecc5` 未變所以數字與 5/24 同）|
| pg-e2e + AC4 collector | `L203` exit=0 elapsed=00:12.959；recall=0.999 / p95=51.69ms / cb=0 |
| perf-baseline | `L231` exit=0 elapsed=00:34.686；3 場景全綠 |
| drift / observability / Cleanup | `L235/238/241` 全 exit=0 |
| pytest 修復後重跑 | `2505 passed, 122 skipped in 94.49s` |
| schtasks 現況 | `schtasks /query /TN "AutoClaude_Nightly"` Status=Disabled / Last Run=1999/11/30 — **user 確認尚未啟用**（等 Round 6 修完後手動開）|

---

## 2. Round 6 真實修復（本輪 commit 已 CLOSED）

| ID | 嚴重度 | 狀態 | 根因 | 修法 | 主要檔案 |
|----|--------|------|------|------|---------|
| **P0-AUDIT-R5-B** `test_main_tolerant_flag_prints_extra_line` 跨日 flaky | P0 | ✅ FIXED | 測試造的 14 筆 records 寫死 ts=2026-05-11~24；今日跨過 2026-05-25 後 `filter_recent(days=14)` 用 `now-timedelta(days=14)` cutoff 剛好 = 2026-05-11 邊界 → 第一筆被嚴格 `>=` 過濾 → tolerant_streak=13 ≠ 14；time-dependent test 違反測試可重複性 | 改用相對時間 `now - timedelta(days=13-i) for i in range(14)`，保證 14 筆全在 cutoff 內；新增 import `datetime as _dt`；其他 evaluate() 直接呼叫的測試不過 filter_recent，不受影響 | [tests/tools/test_ac4_progress_check.py:113-131](../../tests/tools/test_ac4_progress_check.py#L113-L131) |

---

## 3. Round 6 文件 / 環境校準項（非技術 bug，但需 user 知悉）

| ID | 類別 | 狀態 | 說明 |
|----|------|------|------|
| **P0-AUDIT-R5-A** `AutoClaude_Nightly` schtasks Disabled | 環境校準 | 🟡 USER-PENDING | `schtasks /query` 顯示 Status=Disabled / Last Run=1999/11/30（從未真正執行過）；user 確認**尚未啟用**（刻意等 Round 6 修復完成）。Round 5 §7.1 #1 描述「每日 02:00 自動跑」需在 Round 6 修復通過後由 user 執行 `schtasks /change /TN "AutoClaude_Nightly" /ENABLE`。觀察期 #1/#2/#3 累計時間軸（2026-06-01/06-02/06-17）受此影響 — 若 5/25 啟用，實際達標日順延至 6/02 / 6/08 / 6/24 |
| **P0-AUDIT-R5-C** Round 5 聲稱 pytest 2,505 但實測 5 failed | 文件取證 | ✅ CLEARED | 修復前實測 `5 failed / 2,500 passed`；其中 4 個是並行 nightly Docker mount 與本地 pytest 同時跑造成 file lock / .pyc 副作用（單獨重跑即 PASS），1 個是 P0-B 真實 bug。Round 6 P0-B 修完後重跑 `2505 passed / 122 skipped` ✅ 達標。Round 5 聲稱無誤，僅當時測量過程含 Docker 副作用未拆分 |

---

## 4. Round 5 三項取證 zero-trust 驗證

| Round 5 修復項 | 驗證方式 | 結果 |
|---|---|------|
| P1-AUDIT-R4-1 `$script:UsedContainer` 補前綴 | grep `\$UsedContainer` in `tools/run_local_nightly.ps1` → 僅 line 544 `$script:` 完整版本 | ✅ 真實生效 |
| P1-AUDIT-R4-2 nightly summary 觀察期進度行 | [logs/nightly_2026-05-25_090013.log:L244](../../logs/nightly_2026-05-25_090013.log#L244) `END observation progress: mutation=4/7 ac4=4/14 obs=3/30 drift=3/30` | ✅ 真實生效 |
| 紀律 #13 同 UTC date dedup | 連跑 2 次 nightly (run 1 = 5/24 17:42 寫入；run 2 = 5/25 09:06)，jsonl 各檔 +1（mutation 3→4, ac4 3→4, obs 2→3, drift 2→3）— 跨日新增、同日覆寫設計符合 M-05 | ✅ 真實生效 |

---

## 5. 推翻項（zero-trust audit 提出但驗證後不成立）

| 原指控 | 取證 | 結論 |
|--------|------|------|
| Nightly 5 分鐘完成過短，疑為 fake | mutation stage 04:58.128 = 149 mutant × ~2sec；token_guard 子目錄 source_sha256 未變所以 Killed/Survived 數字與 5/24 同；pg-e2e=13s（pg_real marker 測試集小）/ perf=35s / drift=0.5s / obs=0.6s 皆合理 | 推翻；nightly 真實跑完整測試 |
| pytest 5 failed 為基線回退 | 重跑 5 failed 中 4 個為 Docker mutation 跑時 file lock / .pyc cache 副作用（test_cli_compatibility / test_token_guard_thresholds / test_validate_mutmut_log 單獨重跑 PASS）；1 個為 P0-B time-flaky 真實 bug | 部分推翻；只有 P0-B 為真實 bug，其他為測試環境 race |

---

## 6. W1 啟動前未決項（沿用 Round 5）

| ID | 項目 | 狀態 |
|----|------|------|
| ADR-SD09-008 | AC4 雙軌 p95 — 三選項 (a)/(b)/(c) PM 拍板 | PROPOSED v0.2（cut-off **2026-05-31**；逾期自動「過渡寬限」）|
| 觀察期 #1 | mutation pilot TokenGuardPlugin 連續 7 次 ≥ 70% + 紀律 #12 unique sha | 累計 4/7 jsonl（4 筆中前 2 缺 sha + 後 2 sha=5208cff397beecc5）→ unique sha 紀律永遠拒鎖；**W1 必須補 token_guard test 提升 kill_rate 至 unique source 才能進入觀察期** |
| 觀察期 #2 | AC4 14 天 nightly 全綠（strict 50ms）| **數學上不可達標**（真實 p95 51-53ms）— 待 PM 拍板 ADR-SD09-008 後重新校準 |
| 觀察期 #3 | drift_log 30 天零事件 | 累計 3/30；達標日 2026-06-17（若 user 5/25 啟用 schtasks 順延至 6/24）|

---

## 7. 下一步執行檔案與大綱

### 7.1 接下來 30 天 7 大動作

| # | 時間 | 動作 |
|---|------|------|
| 1 | **2026-05-25 Round 6 修復通過後** | **user 手動啟用 schtasks**：`schtasks /change /TN "AutoClaude_Nightly" /ENABLE` — 觀察期累計起算 |
| 2 | 每日 02:00（Task Scheduler `AutoClaude_Nightly`，啟用後）| 自動跑 `tools/run_local_nightly.ps1`（含 Round 5 觀察期進度行）|
| 3 | **≤ 2026-05-31** | PM 拍板 ADR-SD09-008 三選項 |
| 4 | 2026-06-08（5/25 啟用 +14）| 觀察期 #2：ac4_progress_check ready_for_labeled_pr=true（依 PM 拍板）|
| 5 | 2026-06-02（5/25 啟用 +7 — 但需 W1 補 token_guard test 後重置）| 觀察期 #1：mutation 連 7 次 ≥ 70% + unique sha 鎖 baseline |
| 6 | 2026-06-24（5/25 啟用 +30）| 觀察期 #3：drift_log_ga_check --window 30 |
| 7 | 2026-06-25 ~ 2026-07-03 | G0 啟動窗口 → W1 GoalSynthesisPlugin mutation pilot |
| 8 | 每次新 session 前 | 依 [SD09_Execution_Guide.md §0.3](SD09_Execution_Guide.md#03-每次開啟新-session-前必跑) 5 條檢查（pytest ≥ 2,505）|

### 7.2 W1 啟動前 backlog（沿用 Round 5，本輪未新增）

- P2-AUDIT-R4-1 mutation_baseline_lock dedup 印 stderr
- P2-AUDIT-R4-2 AC4 jsonl 拆 collector_status / strict_status 雙欄

---

## 8. 收斂評估與成熟度

### 8.1 收斂訊號（正向）

- **連續 6 輪 audit 已將「nightly 取證紀律」鎖緊**：紀律 13 條（Round 6 未新增）
- **Round 5 三項取證修復 zero-trust 驗證真實生效**：$script:UsedContainer / 觀察期進度行 / 同 UTC date dedup 全數通過
- **Round 6 真實 bug 1 項全數 CLOSED**：P0-B time-flaky test 改相對 now → 永久解決跨日邊界 race
- **無破壞 SD_07/SD_08/Round1-5 收斂**：未動 importlinter / LOC budget / Plugin 結構 / 公開 API；僅修 1 個 test fixture + 文件取證
- **nightly 全綠真實**：6 stages exit=0；mutation stage 4分58秒真實跑完 149 mutants；jsonl 跨日新增同日覆寫設計符合 M-05

### 8.2 仍未收斂訊號（風險，沿用 Round 5 §8.2）

- **schtasks 等 user 手動啟用**：Round 6 修復通過為前提；user 於 5/25 啟用後觀察期時間軸順延 7 天（從 5/20 改 5/25 起算）
- **觀察期 #2 數學上不可達標**：strict 50ms vs 真實 51-53ms 永久衝突；依賴 ADR-SD09-008 PM 拍板（cut-off 5/31）
- **觀察期 #1 真實 kill_rate 74.5%**（已 ≥ 70% 容忍門檻）但 source 未變 → unique sha 紀律 #12 永遠拒鎖；**W1 必須補 token_guard test 提升至 unique source 才能進入觀察期**

### 8.3 專案成熟度評估（與 Round 5 同基準，CI 治理維持 A-）

| 維度 | 評分 | 變動 |
|------|------|------|
| 架構 / 程式碼品質 | 🟢 A | 不變 |
| 測試覆蓋 | 🟢 A（2,505）| 不變（P0-B 修復恢復基線）|
| CI / nightly 治理 | 🟢 A- | 不變（6 輪 audit 鎖緊收斂；schtasks 啟用後可進入「持續累計」）|
| 觀察期升級條件 | 🔴 C | 不變（依賴 PM 拍板 + W1 補測）|
| 文件治理 | 🟢 A | 不變 |
| PG production 上線就緒 | 🟡 B | 不變 |
| 整體 SD_09 進度 | 🟡 W0 採集中 | 不變 |

**結論**：**Round 6 為 6 輪 audit 收尾**。架構 / 文件 / 測試 / CI nightly 治理皆達 production-grade 成熟度（A 或 A-）；P0-B time-flaky 測試已修復永久根因；schtasks 等 user 在 Round 6 通過後手動啟用即可開始觀察期 30 天計時；W5 production cutover 仍受觀察期 #2 數學阻塞，依賴 PM 拍板 ADR-SD09-008（cut-off 2026-05-31）。

---

**版本紀錄**：v1.0 2026-05-25 — Round 6 audit 修復收尾；對應 commit `<填入>` / tag `<填入>` / merge main `<填入>`。
