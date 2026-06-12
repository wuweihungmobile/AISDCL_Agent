# SD_09 W3 Round 5 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — Architect/SA/SD/QA 全能 zero-trust audit Round 4 修復成果 + nightly 程式/過程/結果驗證 |
| Audit Round | W3 Round 5（2026-05-25）|
| Audit 發現 | 2 項 P1 + 2 項 P2；P0=0；**Round 4 三項核心修復全部真實落地，無假象綠燈** |
| 真實修復 | P1-1 / P1-2 已 CLOSED；P2 入 W1 backlog |
| pytest 基線 | 2,505 passed / 122 skipped（與 Round 4 同；本輪未動測試集）|
| importlinter | 7 kept / 0 broken |
| LOC violations | 0（CLAUDE.md=393 ≤ 400 / total 15,050 ≤ cap 16,869）|
| Commit / Tag | `07d9af4` / `v2026.05.25-03` / merge main `995321d` |

---

## 1. Audit 取證

| 項目 | 取證 |
|------|------|
| Nightly run #1（修復前） | `logs/nightly_2026-05-25_012124.log:L242` `END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0`（6 stages 全綠，elapsed ~6min）|
| Nightly run #2（修復後驗證） | `logs/nightly_latest.log` `END nightly summary: ...` + 新增 `END observation progress: mutation=N/7 ac4=N/14 obs=N/30 drift=N/30` |
| mutation 真實取證 | Killed=111 / Survived=38 / kill_rate=74.5%（≥ 70% 容忍門檻）；docker bitmask exit 屬 survived 預期 |
| ac4 真實取證 | recall=0.999 / p95=51.69ms / cb=0 → status=observing（嚴格 50ms neutral 區）|
| drift 真實取證 | table 存在 + severity!='info' count=0 |
| obs 真實取證 | emit_count=3 / trace_id_continuity=true / KB 4-key schema |
| perf 真實取證 | 3 場景全綠（採集 samples=20 連續累計中；baseline 仍鎖 c964328 samples=7 待 7 次新 baseline 後重 lock）|

---

## 2. Round 5 真實修復（本輪 commit 已 CLOSED）

| ID | 嚴重度 | 狀態 | 根因 | 修法 | 主要檔案 |
|----|--------|------|------|------|---------|
| P1-AUDIT-R4-1 `$UsedContainer` 漏 `$script:` 前綴 | P1 | ✅ FIXED | Round 4 P1-AUDIT-R3-4 修了 5 個變數但遺漏 Cleanup else 分支 line 544；PS scope inheritance 目前能讀到值，但破壞紀律一致性，未來重構為 function 後將讀不到 → 觸 紀律 #1 stage rc 假象風險 | 統一補 `$script:UsedContainer` | `tools/run_local_nightly.ps1:544` |
| P1-AUDIT-R4-2 nightly summary 缺觀察期累計進度 | P1 | ✅ FIXED | jsonl 同 UTC date dedup（M-05 設計意圖防同日多 run 灌水）→ user 連跑 N 次 nightly jsonl 只進帳 1 筆；user 對「進帳成功」判斷失準（Round 4 audit user 描述「3→4」實際「3→3」）違紀律 #3 取證可見性 | nightly summary 新增一行 `END observation progress: mutation=N/7 ac4=N/14 obs=N/30 drift=N/30 (jsonl records; same UTC-date dedup per M-05)`；Count-JsonlLines helper 略過空行 | `tools/run_local_nightly.ps1:566-580` |

---

## 3. Round 5 W1 backlog（2 項 P2，不阻塞 G0）

| ID | 項目 | 建議啟動時機 |
|----|------|------------|
| P2-AUDIT-R4-1 | `mutation_baseline_lock.append_history` dedup 後印 `[DEDUP] replaced existing YYYY-MM-DD record` 至 stderr，讓人類即時看到覆寫動作 | W1 啟動前 |
| P2-AUDIT-R4-2 | AC4 jsonl 拆 `collector_status=pass / strict_status=neutral` 雙欄，避免 collector pass vs progress observing 字串混淆 | W1 啟動前（不破 schema：新欄寫入舊欄保留向下相容）|

---

## 4. Round 4 三項核心修復 zero-trust 驗證

| Round 4 修復項 | 驗證方式 | 結果 |
|---|---|------|
| P0-AUDIT-R3-2 mutation sha 強化 `should_lock` | 模擬本次 jsonl 4 筆「前 2 缺 sha + 後 2 同 sha 5208cff397beecc5」+ 補 3 筆同 sha → unique=1 < non-None ≥ 4 → 拒絕鎖定 | ✅ 真實生效（行為符合紀律 #12 強化）|
| P0-AUDIT-R3-3 marker section grep | grep `mutation counts` 於 nightly latest log L158-162 只 emit 純 5 行 counts（無 `compactor.py (13)` 雜訊） | ✅ 真實生效 |
| P1-AUDIT-R3-2 SKIP→-1 哨兵 + Format-Rc | summary JSON `skip_sentinel:-1` + 所有 rc 為整數 type；本次 Docker 可用全 stage rc=0 | ✅ 真實生效 |

---

## 5. 推翻項（zero-trust audit 提出但驗證後不成立）

| 原指控 | 取證 | 結論 |
|--------|------|------|
| `.mutation_history.jsonl` / `.observability_history.jsonl` / `.drift_log_history.jsonl` 本次 nightly 後筆數未增加（user 描述「N→N+1」實際「N→N」）| `append_history` / `append_snapshot` 同 UTC date dedup 是 **M-05 設計意圖**（防同日多 run 灌水偽造觀察期）；非 bug | 推翻；改由 P1-AUDIT-R4-2 加印觀察期進度解決 user 體感失準 |

---

## 6. W1 啟動前未決項（沿用 Round 4）

| ID | 項目 | 狀態 |
|----|------|------|
| ADR-SD09-008 | AC4 雙軌 p95 — 三選項 (a)/(b)/(c) PM 拍板 | PROPOSED v0.2（cut-off 強制 2026-05-31；逾期自動「過渡寬限」）|
| 觀察期 #1 | mutation pilot TokenGuardPlugin 連續 7 次 ≥ 70% + Round 4 強化 unique sha | 累計中（4/7 jsonl 但因前 3 筆同 source 實質無法 lock；待 W1 補 token_guard test 提升 kill_rate 後重置觀察期）|
| 觀察期 #2 | AC4 14 天 nightly 全綠（strict 50ms）| **數學上不可達標** — 待 PM 拍板 ADR-SD09-008 後重新校準 |
| 觀察期 #3 | drift_log 30 天零事件 | 累計中（4/30；達標日 2026-06-17）|

---

## 7. 下一步執行檔案與大綱

### 7.1 接下來 30 天 7 大動作（沿用 Round 4 NextAction §6.1，無變更）

| # | 時間 | 動作 |
|---|------|------|
| 1 | 每日 02:00（Task Scheduler `AutoClaude_Nightly`）| 自動跑 `tools/run_local_nightly.ps1`（含 Round 5 新增觀察期進度行）|
| 2 | **≤ 2026-05-31** | PM 拍板 ADR-SD09-008 三選項 |
| 3 | 2026-06-01 觀察期 #1 | mutation 連 7 次 ≥ 70% + unique sha 紀律 #12 + Round 4 強化 → 鎖 baseline |
| 4 | 2026-06-02 觀察期 #2 | ac4_progress_check ready_for_labeled_pr=true（依 PM 拍板）|
| 5 | 2026-06-17 觀察期 #3 | drift_log_ga_check --window 30 |
| 6 | 2026-06-18 ~ 2026-06-26 | G0 啟動窗口 → W1 GoalSynthesisPlugin mutation pilot |
| 7 | 每次新 session 前 | 依 SD09_Execution_Guide.md §0.3 5 條檢查（pytest ≥ 2,505）|

### 7.2 W1 啟動前 backlog（2 項 P2）

- P2-AUDIT-R4-1 mutation_baseline_lock dedup 印 stderr
- P2-AUDIT-R4-2 AC4 jsonl 雙 status 欄

---

## 8. 收斂評估與成熟度

### 8.1 收斂訊號（正向）

- **連續 5 輪 audit 已將「nightly 取證紀律」鎖緊**：紀律 12 條 + Round 5 新增「觀察期進度可見性」
- **Round 4 三項核心修復 zero-trust 驗證真實生效**：mutation sha 強化 / marker grep / SKIP 哨兵 全數通過實測
- **無破壞 SD_07/SD_08 收斂**：未動 importlinter rules / LOC budget / Plugin 結構 / 公開 API；僅修 nightly 載具 + 觀察期可見性
- **nightly 全綠真實**：6 stages exit=0 對應具體 log 行號（L113/163/203/231/235/238/242）

### 8.2 仍未收斂訊號（風險，沿用 Round 4 §7.2）

- **觀察期 #2 數學上不可達標**：strict 50ms vs 真實 51–53ms 永久衝突；依賴 ADR-SD09-008 PM 拍板（cut-off 5/31）
- **觀察期 #1 真實 kill_rate ≈ 74.5%**（已 ≥ 70% 容忍門檻）但 source 未變 → unique sha 紀律 #12 永遠拒鎖；**W1 必須補 token_guard test 提升至 unique source 才能進入觀察期**
- **觀察期 jsonl 排程健康度** — W1 補 hook 監控 schtasks 是否每日觸發

### 8.3 專案成熟度評估（與 Round 4 同基準）

| 維度 | 評分 | 變動 |
|------|------|------|
| 架構 / 程式碼品質 | 🟢 A | 不變 |
| 測試覆蓋 | 🟢 A | 不變（2,505）|
| CI / nightly 治理 | 🟢 **A-** | **由 B+ 升 A-**（Round 5 新增觀察期進度可見性 / 紀律 12 條全綠 / 5 輪 audit 鎖緊收斂）|
| 觀察期升級條件 | 🔴 C | 不變（依賴 PM 拍板 + W1 補測）|
| 文件治理 | 🟢 A | 不變 |
| PG production 上線就緒 | 🟡 B | 不變 |
| 整體 SD_09 進度 | 🟡 W0 採集中 | 不變 |

**結論**：**架構 / 文件 / 測試 / CI nightly 治理皆已達 production-grade 成熟度（A 或 A-）**；W5 production cutover 仍受觀察期 #2 數學阻塞，依賴 PM 拍板 ADR-SD09-008（cut-off 2026-05-31）；觀察期 #1 收斂需 W1 補 token_guard test 至 unique source（kill_rate 已過 70% 容忍門檻，僅卡 source unique 紀律）。

---

**版本紀錄**：v1.0 2026-05-25 — Round 5 audit 修復收尾；對應 commit `07d9af4` / tag `v2026.05.25-03` / merge main `995321d`。
