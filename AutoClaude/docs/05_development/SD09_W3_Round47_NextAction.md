# SD_09 W3 Round 47 — nightly 機制二十四度閉環 + 四方 zero-trust audit OVERALL PASS（0 P0；1 P1 已併修：unique sha 源碼演進閘門訂正）

| 項目 | 內容 |
|------|------|
| Round | 47（接續 R46 二十三度閉環）|
| 日期 | 2026-05-29（CST 08:55→09:01 = UTC 00:55→01:01，run_id=085526，commit=a8c0cf8，elapsed 5:35）|
| 觸發 | 用戶要求「徹底解決 + 派 PM 與對應 Agent + 完全不信任 zero-trust audit + 全面徹底補做 + 確認 AutoClaude_Nightly 可完整測試與正確結果 + 加速進入 SD10」|
| 結果 | ✅ **OVERALL PASS** — 0 P0 / 1 P1（SA+Architect 雙確認，已併修）/ 3 P2（併修或 SD_10 backlog）；QA 覆審全綠 |
| Agents | 主 agent 親自查證 + Architect Agent + SA Agent + SD Agent + QA Agent（四方並行 zero-trust audit）|

---

## 1. 第 44 跑 nightly 取證（run_id=085526，commit=a8c0cf8）

> **執行教訓（紀律 #15）**：主 agent 首次以 Bash 工具反斜線 `tools\run_local_nightly.ps1` 觸發反斜線吞噬（`toolsrun_local_nightly.ps1` 找不到、腳本未跑、`EXITCODE=0` 來自 tee pipe 偽綠）→ 立即依紀律 #15 改用 **PowerShell 工具正斜線 `tools/run_local_nightly.ps1`** 重跑成功。

`logs/nightly_2026-05-29_085526.log` → `END nightly summary: mutation=0 pg-e2e=0 perf=2 drift=0 obs=0` **6 stage 5 綠 + 1 perf WARN**

| Stage | rc | elapsed | 說明 |
|-------|----|---------|------|
| Docker-PG-bring-up | 0 | 0.460s | 沿用既有 autoclaude_pg |
| mutation-test | 0 | 4:54.162 | mutmut bitmask bit0=0；**kill_rate=76.17%**（killed 113 / survived 35 / suspicious 1 / 0 timeout）|
| pg-e2e + AC4 | 0 | 13.486s | p95=54.2ms recall=0.999 cb_open=0；tolerant<60ms streak=8/14 |
| perf-baseline | **2 WARN** | 55.542s | regression_check_rc=2 baseline_lock_rc=0；`green=1 warn=2 block=0`；token_halt +56.4% + decide_correction +13.2% 皆 samples=7<20 BLOCK→WARN；**decide_correction/dry_run_e2e samples 7→20 合法自校準鎖定** |
| drift_log-scan | 0 | 0.492s | severity!='info'=0 |
| observability-snapshot | 0 | 0.602s | emit_real=true |

- kill_rate=76.17% = (113+0.5×1)/149 = 113.5/149 = 0.761745，與 `.mutation_history.jsonl` 最新筆（ts 2026-05-29T01:00:21）bit-perfect 一致；raw 75.84%≠76.17 證實確用 ADR-SD09-009 半 kill 公式
- source_sha256=20940e1b（凍結）→ tail7 non-None=6 僅 2 unique → `should_lock reject reason=sha_partial_duplicate unique=2/6` 正確阻 lock（紀律 #12）
- **觀察期跨 UTC 日全 +1 真實進帳**：pre=`mutation=7 ac4=7 obs=6 drift=6` → post=`mutation=8/7 ac4=8/14 obs=7/30 drift=7/30 (delta=1)`，因本輪 UTC 日（2026-05-29）異於前進帳 UTC 日（2026-05-28）、M-05 同日去重未觸發

### perf WARN 合法性 + baseline 自校準查證

兩條 WARN（token_halt 0.5→0.8ms +56.4% sub-ms jitter；decide_correction 2426.8→2747.2ms +13.2%）皆 `baseline samples=7 <20` undersampled BLOCK→WARN 降級（ADR-SD08-003 §2.6 v1.1），非真實 regression。本輪 perf_baseline_lock 偵測 decide_correction/dry_run_e2e history tail7 samples=20 → 觸 §2.6 政策(2)連續達標 overwrite，將 W0 commit 4658cfb 殘留的 samples=7 違規 baseline 升級為 samples=20（p95 取 tail max 最保守），屬合法自校準（SD audit 確認，非紅線、不影響三觀察期）。

---

## 2. 四方專家並行 audit 結論（zero-trust，主 agent 逐項 trust-but-verify 複核）

| 方 | 判定 | 重點 |
|----|------|------|
| Architect | CONDITIONAL PASS（0 P0）| perf=2 合法 BLOCK→WARN / git 僅 4 自動 artifact 未觸 §3.0.3 紅線 / importlinter 7 kept / LOC=0 / 5 hooks 各有測試；**揪出 P1-OBS：unique sha idle 期數學死鎖**（源碼凍結則 tail7 永不全 unique）|
| SA | CONDITIONAL PASS | kill_rate 半 kill bit-perfect / ADR=17 / drift schema 對齊 alembic 0013 / #2 p95=54.2<60ms tolerant_streak=8；**獨立揪出同一 P1-R47-1**：ADR §11.3 line 230「自然多日 commit ~6/2-3 達標」與 line 231「sha 由 plugin 源碼計算」自相矛盾、達標路徑事實上無效 |
| SD | PASS（0 P0/P1）| 源碼零異動 / compactor.py:38=`""` / 13 plugins 9 ports 7 rules / trace_context 3 W3C helper + L215 不覆蓋 / storage.mode 三後端；**perf baseline 鎖定為 §2.6 合法 samples 7→20 自校準非紅線** |
| QA | PASS（0 P0/P1）| pytest 親跑 **2,716/122** 99.47s（pytest-randomly not found）/ kill_rate 手算 0.7617450 匹配 / contract test_claude_md_budget 16 passed / CLAUDE.md 384/721cp / 觀察期 delta=1 為跨 UTC 日真實進帳；vs R46 無 regression |

**收斂發現**：Architect 與 SA **獨立指向同一個 P1 核心問題**——觀察期 #1 unique sha 達標路徑的「時間閘門 / 自然多日 commit」心智模型錯誤。這正是「為何無法收斂」的根因之一。

---

## 3. 問題清單與處理（0 P0；1 P1 已併修；3 P2）

| ID | 級 | 類型 | 根因 / 處理 | 狀態 |
|----|----|------|------------|------|
| **P1-R47-1** | P1 | 文件心智模型校正 | #1 unique sha 達標路徑誤導：原述「時間閘門 / 靠自然多日 commit ~2026-06-02~03」與機制矛盾（`compute_source_sha256` 只對 token_guard plugin 源碼計算，idle 期源碼凍結則 unique sha 永不增）→ 訂正為「**源碼演進閘門**：需 W1 active 改 token_guard 源碼產生 ≥7 相異 UTC 日版本，否則依 R-SD08-PM-#3 延 SD_10」。修 **3 處 SSOT**：ADR-SD09-009（§11.3 line 230 + 新增 §11.6 + line 127 + 升 v1.2）/ SD09_Execution_Guide.md（§0.1 + §3.0.1/2/3）/ SD_Improving_09.md（§8.1/§8.2 三處）。`should_lock` 守門邏輯與紀律 #12 反作弊不放寬（純文件校正不改程式碼）| ✅ 已併修 |
| **P2-R47-1** | P2 | jsonl 欄位缺失 | .mutation_history.jsonl 2026-05-20/21 兩筆 legacy 缺 source_sha256（tail7 已僅剩 5/21 一筆 legacy）| 📋 SD_10 backfill |
| **P2-R47-2（沿用 P2-R40-A1）** | P2 | 架構 | run_local_nightly.ps1 超 service tier 500；補 ADR-SD07-001 ps1 tier | 📋 SD_10 backlog |
| **P2-R47-3** | P2 | 文件據實記錄 | 本輪 perf green=1/warn=2（兩條 WARN）非沿用 R46 green=2/warn=1 → banner/H3/metadata/§1.7.3 據實標 | ✅ 已併修 |

---

## 4. 收斂判定（QA 覆審 PASS — 重跑非引述）

| 指標 | R46 | R47 | 收斂 |
|------|-----|-----|------|
| pytest passed | 2,716 | 2,716（99.47s） | PASS |
| pytest skipped | 122 | 122 | PASS |
| nightly stage | 5 綠 + 1 perf WARN | 5 綠 + 1 perf WARN（green=1/warn=2 皆合法）| PASS（非 regression）|
| mutation kill_rate | 73.83% | 76.17%（同 sha suspicious 8→1 bounce）| PASS（>68% effective）|
| 觀察期進帳 | delta=0（M-05 去重）| **delta=1（跨 UTC 日真實 +1）** | PASS（推進）|
| importlinter | 7 kept | 7 kept / 0 broken | PASS |
| LOC violations | 0 | 0（total=15117 baseline=14058 cap=16869）| PASS |
| CLAUDE.md 行數 / 最長行 | 384 / 721cp | 384 / 721cp ≤ 800 | PASS |
| ADR 條數 | 17 | 17 | PASS |
| 源碼異動 | 無 | 無（純文件 + 自動 artifact）| PASS |

**收斂達成** — 本輪純文件滑動（P1 訂正 3 SSOT + R47 滾動更新），無源碼異動。nightly 第 44 跑 5 綠 + 1 合法 perf WARN，零 regression，且觀察期跨 UTC 日真實推進。

---

## 5. 架構分析（為何 #1 觀察期「無法收斂」？修復方向是否正確？）

**根因（SA+Architect 雙確認）**：觀察期 #1 達標的兩條件中，kill_rate 已達標（76% > 68% effective），**唯一卡點 unique sha 閘門先前被誤述為「時間閘門」**——以為靠等待自然多日 commit 即可在 ~2026-06-02~03 達標。實際上 `source_sha256` 只反映 token_guard plugin 源碼，idle 觀察期源碼凍結（20940e1b 自 2026-05-27），每跑只追加相同 sha，unique 數學上永遠停在 2，**等待無法解決**。

**修復方向正確性**：✅ 修復方向正確。技術機制（`should_lock` 反作弊）**本身無誤**，問題純在文件心智模型誤導。正確路徑為：(1) W1 active 開發合法改動 token_guard 源碼時自然累積相異 sha；(2) 若 W1 不觸碰 token_guard 則 #1 unique sha 依 R-SD08-PM-#3 延 SD_10。**絕不可人工 churn 源碼衝 sha**（違紀律 #12 反作弊）。本輪將此校正落地 3 處 SSOT，使團隊獲得正確預期。

---

## 6. 4 軸並行下一步規劃（R47 後）

| 軸 | 動作 | 達標日 | 狀態 |
|----|------|--------|------|
| **A 背景觀察期** | schtasks 02:00 持續累計；#2 ac4 8/14（2026-06-08）、#3 obs/drift 7/30（2026-06-24）跨 UTC 日 +1 推進 | 自然累計 | 🟢 軌道內 |
| **B（已訂正）** | W1 已落地；#1 kill_rate 達標。**unique sha 待 W1 active 改 token_guard 源碼（idle 凍結不達標）**，停止人工 churn | 待 W1 / 或延 SD_10 | ✅ 方向訂正 |
| **C PM 拍板** | 17 ADR 全 ACCEPTED（含 ADR-SD09-009 升 v1.2），無待拍板項 | 完成 | ✅ |
| **D W2-W6 預備** | R41 4 項預研全落地；W2-W6 turnkey 清單就緒 | 持續 | 🟢 |

**下一步優先序**：
1. **軸 A 自然累計**（無人介入）：#2 ac4（2026-06-08）+ #3 obs/drift（2026-06-24）跨 UTC 日 +1 推進；#1 unique sha 待 W1 改 token_guard 源碼或延 SD_10
2. 三觀察期（#2/#3）達標 → **G0 啟動**（最遲 2026-06-26）→ 進 W1 正式 Wave
3. W1 起依 [SD09_Execution_Guide.md §W1](SD09_Execution_Guide.md) 執行（GoalSynthesis mutation pilot；**W1 觸碰 token_guard 時順帶推進 #1 unique sha**）；W2 kb_metric port 落地

**下一步執行檔案**：[SD09_Execution_Guide.md](SD09_Execution_Guide.md) §W0 G0 驗證 → §W1（待 G0）；軸 D turnkey 清單見 [SD09_AxisD_Prep_Research.md](../06_quality/SD09_AxisD_Prep_Research.md)。

---

## 7. 成熟度評估（R47 後）

| 維度 | 評級 | 證據 |
|------|------|------|
| nightly 機制穩定性 | **A+** | R24~R47 連 24 輪閉環，第 44 跑 5 綠 + 1 合法 perf WARN |
| 紀律治理 | **A+** | 16 條全合規；本輪即時依紀律 #15 改 PowerShell 工具避反斜線吞噬 |
| zero-trust audit 自我反證能力 | **A+** | Architect + SA 獨立雙確認同一 P1 文件誤導（時間閘門 vs 源碼演進閘門）|
| 軸 D 預備就緒度 | **A+** | R41 4 項預研全落地，W2-W6 turnkey 清單就緒 |
| 觀察期推進 | **A** | 本輪跨 UTC 日全 +1 真實進帳（#1 8/7、#2 8/14、#3 obs/drift 7/30）|
| 加速 SD_10 就緒度 | **NOT_READY**（時間 + 源碼演進閘門制約）| #2/#3 純時間閘門（最遲 6/24）；#1 unique sha 需 W1 改源碼，皆非設計缺陷 |
| 整體 | **A+ 級** | 24 輪閉環 + 本輪 P1 文件誤導訂正 OVERALL PASS |

**是否收斂**：✅ 已收斂（pytest 2,716/122 R36~R47 持平，nightly 機制 24 輪閉環，本輪 0 P0）。**唯一未達 SD_10 的是 #2/#3 時間閘門（最遲 6/24）+ #1 unique sha 源碼演進閘門（待 W1）**，皆非設計缺陷、無法靠工程加速繞過（紀律 #12 禁人工 churn）。

---

**結論**：✅ **R47 二十四度閉環 OVERALL PASS — Architect/SA/SD/QA 四方並行 zero-trust audit 0 P0 + SA+Architect 雙確認 P1 unique sha「源碼演進閘門」誤導訂正里程碑**。nightly 第 44 跑 5 stage 全綠 + 1 perf WARN（兩條 undersampled BLOCK→WARN 合法降級非 regression），pytest 2,716/122，kill_rate 76.17%，contract 16 綠，importlinter 7 kept，LOC=0，CLAUDE.md ≤ 400 / 單行 ≤ 800 codepoints，ADR 17。觀察期跨 UTC 日全 +1 真實進帳。P1 文件誤導已修 3 SSOT。下一步靠背景 schtasks 累計 #2/#3 至 2026-06-24 → G0 啟動。
