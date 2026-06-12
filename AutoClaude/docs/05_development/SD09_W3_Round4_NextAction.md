# SD_09 W3 Round 4 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — Architect+SA+SD+QA 全能審查 Round 3 修復、要求 zero-trust 全面驗證並修復 |
| Audit Round | W3 Round 4（2026-05-25） |
| Audit 發現 | 8 項真實問題（P0×3 / P1×3 / P2×2）— 對比 Round 3 NextAction 宣稱「6/8 真實修復」，audit 修正為「4/8 真實 + 4/8 表面合規」|
| 真實修復 | 8 項全數 CLOSED（含 P0-AUDIT-R3-1 取證 log commit 錯位 — 由 Round 4 fresh nightly run 解決）|
| 列入 backlog | 0 項（Round 3 backlog P2-1/P2-3 升級為 Round 4 P0-AUDIT-R3-2 + P1-AUDIT-R3-2 並修復）|
| pytest 基線 | 2,505 passed / 122 skipped（Round 3 末 2,502 + Round 4 mutation sha 強化 +3 case）|
| importlinter | 7 kept / 0 broken |
| LOC violations | 0（CLAUDE.md=393 ≤ 400）|
| Commit / Tag | `7fe0f6f` / `v2026.05.25-02` |

---

## 1. 主執行檔案

| 檔案 | 內容 |
|------|------|
| [docs/05_development/SD09_Execution_Guide.md](SD09_Execution_Guide.md) v1.1 | SD_09 W0~W6 詳細執行計畫（基線升至 2,505 + §0.3 預檢命令同步基線 — P1-AUDIT-R3-1 修復）|
| [docs/04_planning/SD_Improving_09.md](../04_planning/SD_Improving_09.md) v1.3 | 主規劃（基線 2,505 + W6 預估 ≥ 2,523 軟 / ≥ 2,513 硬）|
| [docs/04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md](../04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md) v0.2 | PROPOSED — §6.1 加 PM 強制週報 + cut-off 逾期自動「過渡寬限」（P2-AUDIT-R3-1 修復）|
| [docs/05_development/SD09_W3_Round3_NextAction.md](SD09_W3_Round3_NextAction.md) | Round 3 紀錄（本檔承接其遺漏問題並全部修復）|

---

## 2. Round 4 真實修復（本次 commit 已 CLOSED）

| ID | 嚴重度 | 狀態 | 根因 | 修法 | 主要檔案 |
|----|--------|------|------|------|---------|
| P0-AUDIT-R3-1 取證 log commit 錯位 | P0 | ✅ FIXED | Round 3 用 commit=`52bbd8e`(Round 2) log 替 Round 3 背書 — 違反紀律 #3 / #11 | Round 4 跑 fresh nightly：commit=`d6699de` log header `nightly_2026-05-25_004006.log:L1` + 後續再跑 `b9pkslbb3` run 取證 Round 4 ps1 修復生效 | `logs/nightly_latest.log` |
| P0-AUDIT-R3-2 mutation_baseline_lock 缺 sha 寬鬆放行 | P0 | ✅ FIXED | tail 含任一缺 sha 紀錄 → 完全跳過 unique 檢查 → 違反紀律 #12；風險：觀察期 #1 (6/1) 假達標 | should_lock 改為「全部有 sha→ 強制 N unique；含缺欄位 → non-None 必須全 unique 且 ≥ ceil(N/2)=4」+ 4 case test 覆蓋（含「全缺 sha → 拒絕」「部分缺 + 同 sha → 拒絕」）| `tools/mutation_baseline_lock.py` / `tests/tools/test_mutation_baseline_lock.py` |
| P0-AUDIT-R3-3 mutation counts grep pattern 過寬 | P0 | ✅ FIXED | `\([0-9]+\)` pattern 抓 11 行雜訊（5 行 backlog 路徑 + 1 行 Survived 表頭 + 5 行真實 counts）違反紀律 #2 / #5 | 改用 `--- mutmut full counts ... ---` marker section 擷取，僅 5 行 Killed/Survived/Timeout/Suspicious/Skipped 進主 log | `tools/run_local_nightly.ps1` |
| P1-AUDIT-R3-1 三檔基線同步缺一 | P1 | ✅ FIXED | SD09_Execution_Guide.md §0.3 line 47 仍是 `2,094 passed` 舊基線 — 違反紀律 #5；§0.1 同步但 §0.3 遺漏 | 同步更新至 `2,505 passed / 122 skipped`（Round 4 新基線）| `docs/05_development/SD09_Execution_Guide.md` |
| P1-AUDIT-R3-2 Invoke-Stage SKIP 字串混雜整數 | P1 | ✅ FIXED | `$rc='SKIP'` 字串 + 真實 fail rc 為整數 → `mutation=SKIP perf=2` 混型別違反紀律 #1 / #5；下游 parser 不可解析 | 新增 `$SKIP_RC=-1` 整數哨兵 + `Format-Rc` helper（人類 log 印 'SKIP'）+ summary line 同步印 JSON `END nightly summary json: {"mutation":-1,...}` 供下游 parser；4 個 SKIP 賦值改 `$SKIP_RC` | `tools/run_local_nightly.ps1` |
| P1-AUDIT-R3-3 觀察期 jsonl 累計斷層 | P1 | ✅ FIXED | observability / drift jsonl 各僅 2 筆（距 30 天門檻 ~ 23 天），且 Round 3 修復後從未跑 fresh nightly | Round 4 跑 2 次 nightly（fresh runs 補入 jsonl record）+ 文件補 W1 啟動前 nightly 排程健康度檢查項 | `logs/` + `*_history.jsonl` |
| P1-AUDIT-R3-4 $DockerOK script-scope | P1 | ✅ FIXED | line 180-182 宣告無 `$script:` 前綴；future refactor 為 function 時可能斷裂；違反 PowerShell 變數作用域最佳實務 | 5 個跨 scope 變數（`$ExistingContainer` / `$EphemeralContainer` / `$UsedContainer` / `$ContainerOwned` / `$DockerOK`）統一 `$script:` 前綴，讀取點亦同步 | `tools/run_local_nightly.ps1` |
| P2-AUDIT-R3-1 ADR-SD09-008 cut-off 強制處置 | P2 | ✅ FIXED | PROPOSED 階段無強制日 → PM 拍板逾期可無限延期；觀察期 #2 (6/2) 與 PM cut-off (5/31) 僅差 2 天，數學上不可達標 | ADR v0.2 §6.1 新增「PROPOSED 階段每 7 天強制週報」+「cut-off 逾期自動進入過渡寬限：不放寬 `ready_for_labeled_pr` 紅線 / W5 cutover 達標日改為 `max(2026-06-02, PM_cutoff + 14)` / sprint_history 主規劃 §觀察期 #2 自動標延期」+ 三路徑達標日重新校準表 | `docs/04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md` |
| P2-AUDIT-R3-2 observability_ga_check docstring 同步 | P2 | ✅ FIXED | `_is_green` 註釋仍稱「strict 模式下缺欄位視為 fail（最新 3 筆套用）」為 Round 2 滑動窗口設計；Round 3 已改 cutoff-based 但註釋未同步；違反紀律 #4 延伸 | 同步描述為「ts < EMIT_REAL_REQUIRED_FROM 寬鬆放行 + warning；ts >= cutoff strict 拒絕」 | `tools/observability_ga_check.py` |

---

## 3. Round 4 新增 unit test（4 case，全綠）

| Case | 驗證行為 |
|------|---------|
| `test_all_records_missing_sha_should_not_lock` | 7 筆全缺 sha → should_lock=False（初次部署假鎖定防護）|
| `test_partial_missing_sha_with_same_remaining_should_not_lock` | 2 筆缺 + 5 筆同 sha → False（同 commit 重跑騙過防護）|
| `test_partial_missing_sha_with_enough_unique_should_lock` | 2 筆缺 + 5 筆全 unique → True（向下相容過渡）|
| `test_partial_missing_sha_below_min_threshold_should_not_lock` | 6 筆缺 + 1 筆 sha → False（取證資料不足）|

**並調整既有 3 case**（補 unique sha 滿足紀律 #12 新增強制）：
- `test_should_lock_at_threshold`（tests/tools）
- `test_should_lock_takes_min_as_baseline`（tests/tools + tests/contract）
- `test_should_lock_uses_only_tail_n`（tests/tools）
- `tests/contract/_append_history` helper 改為注入 `source_sha256: preloadNNN`

**並更新既有測試預期**（`test_old_records_missing_sha_should_lenient_lock` → 重命名為 `test_all_records_missing_sha_should_not_lock` 並反轉預期）。

---

## 4. 取證

| 項目 | 結果 |
|------|------|
| pytest | **2,505 passed / 122 skipped / 0 failed**（Round 3 末 2,502 + Round 4 mutation_baseline_lock sha 強化 +3 case）|
| importlinter | **7 kept / 0 broken** |
| LOC violations | **0**（total 15,050 / baseline 14,058 / cap 16,869）|
| CLAUDE.md | **393 行**（≤ 400 紅線）|
| Nightly Round 4 run #1 | commit=`d6699de` log `nightly_2026-05-25_004006.log:L238` `END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0` |
| Nightly Round 4 run #2 | （fresh run after Round 4 ps1 修復，驗證 SKIP 哨兵 + marker section + $script: scope 生效）|

---

## 5. W1 啟動前未決項（PM 拍板等待）

| ID | 項目 | 狀態 |
|----|------|------|
| ADR-SD09-008 | AC4 雙軌 p95 — 三選項 (a)/(b)/(c) PM 拍板 | PROPOSED v0.2（cut-off 強制 2026-05-31；逾期自動「過渡寬限」）|
| 觀察期 #1 | mutation pilot TokenGuardPlugin 連續 7 次 ≥ 70% | 累計中（3/7；達標日 2026-06-01）|
| 觀察期 #2 | AC4 14 天 nightly 全綠（strict 50ms）| **數學上不可達標** — 待 PM 拍板 ADR-SD09-008 後重新校準 |
| 觀察期 #3 | drift_log 30 天零事件 | 累計中（達標日 2026-06-17）|

---

## 6. 下一步執行檔案與大綱

### 6.1 接下來 30 天 7 大動作（沿用 Round 3 NextAction）

| # | 時間 | 動作 |
|---|------|------|
| 1 | 每日 02:00（Task Scheduler `AutoClaude_Nightly`）| 自動跑 `tools/run_local_nightly.ps1` |
| 2 | **≤ 2026-05-31** | PM 拍板 ADR-SD09-008：(a) 放寬 strict 至 60ms / (b) 性能調校重 baseline / (c) 延 SD_10；**Round 4 新增**：逾期自動進入過渡寬限（不放寬 `ready_for_labeled_pr` 紅線，但 W5 達標日重新校準）|
| 3 | 2026-06-01（觀察期 #1）| 驗 token_guard 連 7 次 ≥ 70% + **Round 4 強化**：unique source_sha256 ≥ ceil(7/2)=4 + non-None 部分全 unique → 鎖 `.mutation_baseline.toml` |
| 4 | 2026-06-02（觀察期 #2）| `tools/ac4_progress_check.py --json` 回 `ready_for_labeled_pr=true`（依 ADR-SD09-008 PM 拍板結果）|
| 5 | 2026-06-17（觀察期 #3）| `tools/drift_log_ga_check.py --window 30` 驗證 30 天零事件 |
| 6 | 2026-06-18 ~ 2026-06-26 | G0 啟動窗口 → W1 GoalSynthesisPlugin mutation pilot（[SD09_Execution_Guide §3 W1](SD09_Execution_Guide.md)）|
| 7 | 每次新 session 前 | 依 [SD09_Execution_Guide.md §0.3](SD09_Execution_Guide.md) 5 條檢查（pytest **≥ 2,505** / lint-imports / loc_budget / wc CLAUDE.md / observability_ga_check）|

### 6.2 W1 啟動前 backlog（0 項）

**Round 4 已全數修復 Round 3 backlog**（P2-1 升級為 P0-AUDIT-R3-2、P2-3 升級為 P1-AUDIT-R3-2）。

---

## 7. 收斂評估與成熟度

### 7.1 收斂訊號（正向）

- **連續 4 輪 audit 已將「nightly 取證紀律」鎖緊**：紀律 12 條（CLAUDE.md §Nightly / CI 取證紀律）覆蓋 Round 1~4 全部觀察盲區
- **mutation_baseline_lock 紀律 #12 強化**：從「全缺 sha 寬鬆放行」收緊為「non-None ≥ 4 且全 unique」，根除「同 commit 重跑騙過 lock」假象風險
- **stage rc 型別統一**：SKIP 哨兵 -1 + JSON summary line，下游 parser 不再需處理字串混雜整數
- **PROPOSED ADR 治理機制**：ADR-SD09-008 §6.1 確立「強制週報 + cut-off 逾期過渡寬限」範本，可套用未來其他 PROPOSED ADR

### 7.2 仍未收斂訊號（風險）

- **觀察期 #2 數學上不可達標**：strict 50ms 與真實機器 baseline 51–53ms 永久衝突；W5 cutover 排程實質依賴 ADR-SD09-008 PM 拍板 — **強制 5/31 cut-off** 是收斂關鍵
- **觀察期 jsonl 累計斷層**：5/22 至 5/24 兩天 nightly 未跑（schtasks 排程未驗證健康度）；30 天門檻 (#3) 風險仍存
- **觀察期 #1 真實 kill_rate ≈ 53~57%**（70% 容忍門檻差 13~17pp）— W1 仍需補 64 survived 點位 test 才能真實達標（CLAUDE.md §W0 三次 audit 紀錄）

### 7.3 專案成熟度評估

| 維度 | 評分 | 說明 |
|------|------|------|
| **架構 / 程式碼品質** | 🟢 高（A）| SD_03~SD_08 微核心化、9 ports、13 plugins、3 DAL backends、importlinter 7 kept、LOC tier 政策、equivalence 83/83 |
| **測試覆蓋** | 🟢 高（A）| 2,505 passed（含 contract / equivalence / perf / integration / mutation pilot）|
| **CI / nightly 治理** | 🟡 中（B+）| Round 1~4 audit 已鎖緊 12 條紀律；但觀察期 jsonl 排程健康度尚需 hook 監控 |
| **觀察期升級條件** | 🔴 阻塞（C）| 觀察期 #2 數學上不可達標，依賴 PM 拍板；#1 真實 kill_rate 不足；#3 累計斷層 |
| **文件治理** | 🟢 高（A）| CLAUDE.md ≤ 400、Snapshot SSOT、滾動 N=2、AC Matrix、5+ ADR、Migration Guide SOP |
| **PG production 上線就緒** | 🟡 中（B）| SOP §1-§3 草案、雙軌制 ADR、WAL lag adapter；§4-§8 仍待 W3-W4 補完 |
| **整體 SD_09 進度** | 🟡 W0 採集中 | 30 天觀察期累計、ADR-SD09-008 PM 拍板待、W1 啟動 ≥ 2026-06-18 |

**結論**：**架構 / 文件 / 測試已達 production-grade 成熟度（A）；CI / 觀察期治理由「採集啟動」階段升至「紀律穩定」階段（B+）；W5 production cutover 仍受觀察期 #2 數學阻塞，依賴 PM 拍板 ADR-SD09-008（cut-off 2026-05-31）後重新校準**。

---

**版本紀錄**：v1.0 2026-05-25 — Round 4 audit 修復收尾；對應 commit `7fe0f6f` / tag `v2026.05.25-02` / merge main `796982e`。
