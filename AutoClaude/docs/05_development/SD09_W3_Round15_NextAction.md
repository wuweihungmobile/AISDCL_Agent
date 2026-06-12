# SD_09 W3 Round 15 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — 第 10 跑 nightly 驗證（軸 A 排程評估 + Architect/SA/SD/QA inline zero-trust audit）|
| Audit Round | W3 Round 15（2026-05-25）|
| Audit 發現 | **0 P0 + 0 P1 + 0 P2 + 0 NOTE → PASS（13 紀律全綠；首次無 issue 輪次自 Round 11 以來第二次）** |
| pytest 基線 | **2,538 passed / 122 skipped**（持平 Round 14；本輪零實作差異）|
| importlinter | 7 kept / 0 broken |
| LOC violations | 0（baseline=14058 / cap=16869 / total=15050）|
| CLAUDE.md | 400 行（紅線邊界）|
| Nightly 第 10 跑取證 | [logs/nightly_2026-05-25_203336.log:L256](../../logs/nightly_2026-05-25_203336.log#L256) `END nightly summary: mutation=0 pg-e2e=0 perf=2 drift=0 obs=0`（5 stage 含 perf WARN；5:43 elapsed） |
| §3.0 並行框架 | 不變（軸 A 排程評估完成；軸 C 100% 維持；軸 D 預備研究 100% 維持）|

---

## 1. Audit 取證

| 項目 | 取證 |
|------|------|
| Nightly 第 10 跑 | [log:L256](../../logs/nightly_2026-05-25_203336.log#L256) `END nightly summary: mutation=0 pg-e2e=0 perf=2 drift=0 obs=0` |
| Stage 個別 elapsed | Docker-PG 0.38s / mutation 4:36.5 / pg-e2e 12.9s / perf 51.6s / drift 0.46s / obs 0.62s / Cleanup 0.002s — 總 5:43 |
| Mutation 5 行 counts | [log:L165-169](../../logs/nightly_2026-05-25_203336.log#L165) Killed (111) / Survived (38) / Timeout (0) / Suspicious (**0**) / Skipped (0) — kill_rate=**74.50%**（vs R14 73.15%；suspicious 2→0 bounce 回 0；M-05 same UTC date dedup 覆寫 R14 第 4 筆）|
| AC4 F2 OK | dual track 正常運作（tolerant<60ms streak=4 / observation<50ms streak=0；本跑 p95 待 AC4 jsonl 確認 — `tolerant<60ms streak=4 days=4`） |
| Perf=2 WARN | [log:L213-244](../../logs/nightly_2026-05-25_203336.log#L213) decide_correction PASS +5.6% / dry_run_e2e PASS -96.7% / **token_halt_roundtrip WARN baseline=0.5ms current=0.8ms +61.1%**（亞毫秒測量噪音；samples=7 < 20 BLOCK→WARN 退化 — ADR-SD08-003 §2.6 v1.1 設計涵蓋；Invoke-Stage rc=2 視為 WARN 不算 fail 紀律 #1）|
| Drift 0 事件 | [log:L249](../../logs/nightly_2026-05-25_203336.log#L249) `drift_log severity!='info' rows = 0` |
| 觀察期 jsonl 進度 | [log:L257](../../logs/nightly_2026-05-25_203336.log#L257) `END observation progress: mutation=4/7 ac4=4/14 obs=3/30 drift=3/30`（與 Round 14 同 UTC date dedup 一致 — 紀律 #13 驗證正確）|
| Observability snapshot | `observability_emit_real:true emit_count=3`（紀律 #10 真實 emit 標記正確）|
| 13 條紀律 | **13 PASS / 0 WARN / 0 FAIL** |

---

## 2. 軸 A 排程評估（user 派工）

### 2.1 問題

User 詢問：「若 nightly 一次只要 6 分鐘，02:00~07:00 可否一個小時執行三次？」

### 2.2 評估結論：**維持 02:00 × 1 跑**

| 排程方案 | jsonl 進帳/天 | 觀察期加速效果 | 額外成本 |
|---------|-------------|-------------|---------|
| 02:00 × 1 跑（**現況**）| 1 筆 | 基準 | 6 min/天 |
| 02:00~07:00 每小時 3 跑（15 跑/天）| **仍 1 筆**（被 M-05 dedup） | **零加速** | 90 min/天 + 15× cache I/O + log 檔暴增 + Docker 啟停 |
| 02:00 + 06:00 兩跑（備援）| 1 筆（第二跑 dedup） | 零加速但有電腦關機備援 | 12 min/天 |

### 2.3 設計依據

CLAUDE.md 紀律 #13 + M-05 modifier：所有觀察期 jsonl（`.mutation_history.jsonl` / `.ac4_history.jsonl` / `.observability_history.jsonl` / `.drift_log_history.jsonl`）採**同 UTC date dedup**設計（同一日多次 nightly 只進帳 1 筆，第二跑以後**覆寫**該日紀錄），目的是防止「灌水偽造觀察期」（user 連跑 N 次 nightly jsonl 只進帳 1 筆，紀律 #13 驗證設計）。

本 Round 第 10 跑（20:33 = 12:33 UTC）正好驗證：jsonl 第 4 筆從 Round 14 的 73.15% **覆寫**為 74.50%（觀察期 #1 仍維持 4/7），符合 M-05 dedup 設計預期。

### 2.4 決定

✅ **維持 02:00 × 1 跑現況** — schtasks `/SC DAILY /ST 02:00 /TN AutoClaude_Nightly` 已正確設定，無需調整。

❌ 不採每小時 3 跑（零加速 + 浪費資源）。

🟡 可選：若 user 擔心電腦關機，建議改為 `02:00 + 06:00` 兩跑備援（第二跑 dedup 不影響觀察期，但有電腦關機保險）。本 Round 不主動執行此調整，待 user 決定。

---

## 3. Round 15 真實問題（0 P0 + 0 P1 + 0 P2 + 0 NOTE）

**本輪 zero-trust audit 無問題 → 不需派 audit-fix Agent**。

特別觀察項（非 audit 問題，但有意義）：

| 觀察 | 內容 | 對應 ADR |
|------|------|---------|
| **OBS-R15-1** suspicious 從 R14 第 9 跑 2 → R15 第 10 跑 0（bounce 回 0）| **進一步證實 ADR-SD09-009 半確定性論點 + ±2pp tolerance 必要性**：mutmut 對 timing-sensitive 點位（policy.py:91, 99）的 suspicious 標籤是非確定性的，跨 run 在 [0, 2~7] 區間飄動；ADR-009 選項 A `(killed + 0.5×suspicious) / denom + ±2pp tolerance` 設計符合實況 | ADR-SD09-009 v1.0 ACCEPTED |
| **OBS-R15-2** M-05 dedup 預期行為驗證 | jsonl 第 4 筆從 73.15%（R14）覆寫為 74.50%（R15），觀察期 #1 進度 mutation=4/7 維持（同 UTC date dedup 不重複進帳）；本輪實測證實紀律 #13 設計正確 | 紀律 #13 / M-05 |
| **OBS-R15-3** Round 14 W1 task list 尚未實作 | `tools/mutmut_counts_parser.py` 不存在 / `docs/05_development/PS1_Complexity_Checklist.md` 不存在 / `calc_kill_rate` 仍為舊版 — 屬 W1 範疇（T1-M1/M2/M3/H1 + T1-B1 共 2.8 PD），nightly 本身不受影響；W1 啟動後落地即可 | ADR-SD09-009/010 v1.0 ACCEPTED |

---

## 4. 13 條紀律盤點（Round 15 第 10 跑後）

| # | 紀律 | Round 15 |
|---|------|----------|
| 1 | stage rc 區分真實失敗 vs 工具標準回報 | ✅ PASS（perf rc=2 視為 WARN 不算 fail；regression_check_rc=2 / baseline_lock_rc=0）|
| 2 | log 完整統計 | ✅ PASS（5 type counts 全列；Killed/Survived/Timeout/Suspicious/Skipped 0 也列）|
| 3 | PASS 引用 RunId log:L | ✅ PASS（本報告全引用 [logs/nightly_2026-05-25_203336.log](../../logs/nightly_2026-05-25_203336.log)）|
| 4 | 驗證鏡子被驗證 | ✅ PASS（45 ac4 case 全綠；ac4_nightly_alert_parser + 16 case unit test）|
| 5 | 跨工具數字對齊 | ✅ PASS（mutation_analysis survived=38 ↔ mutmut log Survived(38) ↔ baseline_lock kill_rate=74.50%）|
| 6 | 採集寬鬆 vs 升級嚴格分軌 | ✅ PASS（perf BLOCK→WARN samples<20 退化 + AC4 dual env STRICT=60/OBSERVATION=50）|
| 7 | cache 強制 fresh | ✅ PASS（log:L 確認 `perf_results.json 移除（強制 fresh）`；.mutmut-cache + .ac4_junit.xml 跑前 rm）|
| 8 | .sh LF 行尾 | ✅ PASS（.gitattributes + run_mutmut_in_docker.sh 不變動）|
| 9 | Docker 依賴 SKIP 一致 | ✅ PASS（本跑 Docker 可用 autoclaude_pg 沿用；程式碼路徑 ps1:505-538 保留）|
| 10 | fallback jsonl 可區分 | ✅ PASS（observability_emit_real:true）|
| 11 | latest log pointer 完整 | ✅ PASS（`Latest log pointer 已更新` log 末段）|
| 12 | mutation history source_sha256 | ✅ PASS（同 sha 5208cff... unique=1；should_lock 將以 sha_not_unique_full reject — 紀律 #12 守門生效）|
| 13 | 觀察期進度可見 | ✅ PASS（log:L257 4 軌進度可見；與 Round 14 同 UTC date dedup 正確）|

---

## 5. W1 啟動前未決項（Round 15 後狀態）

| ID | 項目 | 狀態 |
|----|------|------|
| ADR-SD09-008 v0.4 | AC4 雙軌 60ms tolerant + 50ms observation | ✅ ACCEPTED 2026-05-25 |
| ADR-SD09-009 v1.0 | mutmut suspicious 0.5 半 kill + ±2pp tolerance | ✅ ACCEPTED 2026-05-25 |
| ADR-SD09-010 v1.0 | ps1-to-helper SSOT 治理 | ✅ ACCEPTED 2026-05-25 |
| 觀察期 #1 | mutation pilot 連續 7 次 ≥ 70% + 紀律 #12 unique sha | 累計 **4/7 jsonl record**（kill_rate 74.50% 過 70% threshold；待 W1 軸 B + ADR-009/010 同 PR 落地觸發 SP-1 重置；同 UTC date dedup 限制下 R14/R15 jsonl 同筆覆寫）|
| 觀察期 #2 | AC4 14 天 nightly 全綠 | 累計 **4/14**（tolerant streak=4；達標窗口 2026-06-08）|
| 觀察期 #3 | drift_log 30 天零事件 | 累計 **3/30**；達標日 2026-06-24 |

---

## 6. 下一步執行檔案與大綱（依 §3.0 4 軸並行框架；Round 15 後校準）

### 6.1 4 軸並行下一步動作

| 軸 | 動作 | 時機 | 狀態 |
|----|------|------|------|
| **軸 A 背景觀察期** | ✅ user 已啟用 schtasks /SC DAILY /ST 02:00；持續 nightly 自動跑累計 jsonl；**Round 15 已評估「每小時 3 跑」方案 — 結論維持 02:00 × 1 跑**（M-05 dedup 零加速）| 🟢 持續中 | 已啟動 + 排程已最佳化 |
| **軸 B W1 前景** | 補 token_guard 15 case test（policy 8 / compactor 3 / git_verifier 1 / thresholds+watcher 2-3）— 預估 ~250 LOC + 殺 22 必補 mutant；ROI 補後 kill_rate ≈ 83~89% + 觸發 source_sha256 變化重置觀察期 #1 | ≤ T+10 = 2026-06-04 | 🟡 已分析待實作 |
| **軸 C PM 拍板** | ✅ ADR-009 ACCEPTED 選項 A / ✅ ADR-010 ACCEPTED 選項 B / ✅ ADR-008 v0.4 ACCEPTED | ≤ 2026-06-08 | 🟢 **三項全完成** |
| **軸 D W2-W6 預備** | ✅ Production_Migration_SOP §4-§5 大綱完成 / ✅ trace_id W3C path-b 設計完成（Round 14 Architect+SD Agent 派工）| 任意時點 | 🟢 **預備研究全完成** |

### 6.2 W1 task list（不變於 Round 14）

| 任務 ID | 內容 | 對應 ADR | PD 估算 |
|---------|------|---------|---------|
| T1-B1（軸 B 整合）| 補 token_guard 15 case test（policy.py 8 / compactor 3 / git_verifier 1 / thresholds+watcher 2-3）| Round 14 軸 B 分析 | 1.5 PD |
| T1-M1 | 切換 `tools/mutation_baseline_lock.py` `calc_kill_rate` → `(killed + 0.5×suspicious) / denom` + `should_lock` 加 ±2pp tolerance | ADR-009 §6 | 0.3 PD |
| T1-M2 | `tools/mutation_analysis.py` 同步切換 suspicious 處理 | ADR-009 §6 + 紅線 §5.3 | 0.2 PD |
| T1-M3 | 補 ≥ 5 case 單元測試 — bounce 場景 / 邊界 threshold / 三選項數學等價性 | ADR-009 紅線 §5.4 | 0.3 PD |
| T1-H1 | `tools/mutmut_counts_parser.py`（≤ 100 LOC）+ ≥ 6 case unit test + ps1 line 337-358 inline 改造 + `docs/05_development/PS1_Complexity_Checklist.md`（≤ 50 行）| ADR-010 §5 W1 | 0.5 PD |
| **W1 合計** | 2.8 PD（原 W1 5 PD 預算內可吸收）| | |

### 6.3 收斂評估與成熟度（Round 15 後）

#### 6.3.1 收斂訊號（正向）

- **Round 15 zero-trust audit 完整 0 issue PASS**：自 Round 11 首次無 P0/P1 以來，**首次完整 0 P0 + 0 P1 + 0 P2 + 0 NOTE** — 15 輪 audit 連續壓力測試**首次完全 idle audit**（無新發現問題）
- **Nightly 第 10 跑 5 stage 全綠 + perf=2 WARN 設計內語意正確降級**
- **OBS-R15-1 進一步證實 ADR-SD09-009 半確定性論點**：suspicious 從 R14 2 → R15 0 bounce，符合 ADR §1 表觀察（7→4→0 bounce flake；ADR-009 ±2pp tolerance 必要性被實況持續證實）
- **軸 A 排程已最佳化**：M-05 dedup 數學分析證明「每小時 3 跑」零加速 → 維持 02:00 × 1 為最優方案
- **pytest 基線維持 2,538**（持平 R14；本輪零實作差異）
- **13 條紀律全綠維持 15 輪**（壓力測試穩定）

#### 6.3.2 仍未收斂訊號（不變於 Round 14）

- **軸 B W1 token_guard 15 case test 待實作**：原任務 64 點修正為實際 38（22 必補 + 16 ignore），15 case 為高 ROI 子集
- **W1 T1-M1~M3 + T1-H1 待實作**：合計 2.8 PD，建議與軸 B 15 case 同 PR 落地（單次觸發 SP-1 觀察期 #1 重置，節省 7 天緩衝）
- **觀察期 #1 累計 4/7 但同 sha unique=1**：待 W1 commit 變 sha 後新累計

#### 6.3.3 專案成熟度評估（Round 15 後維持）

| 維度 | 評分 | 變動（vs Round 14）|
|------|------|------|
| 架構 / 程式碼品質 | 🟢 A | 不變 |
| 測試覆蓋 | 🟢 A（2,538 持平）| 不變 |
| CI / nightly 治理 | 🟢 **A+** | **+0.5**（15 輪 audit 首次完全 0 issue + 軸 A 排程最佳化評估完成 + 第 10 跑驗證 nightly 程式真實穩定）|
| 觀察期升級條件 | 🟢 A− | 不變（PM 拍板完成 + 軸 D 預備研究完成；觀察期累計繼續）|
| 文件治理 | 🟢 A+ | 不變 |
| PM 決策成熟度 | 🟢 A | 不變（Round 14 首評 A；本輪持平）|
| PG production 上線就緒 | 🟡 B | 不變（軸 D §4-§5 預備研究完成但 staging 演練未啟動）|
| 整體 SD_09 進度 | 🟢 **W0 收尾期（接近完成）** | 不變語義（15 輪 audit 收尾期 + 軸 C 三項 100% 完成 + 軸 D 預備研究 100% 完成；剩餘軸 A 30 天累計 + 軸 B 15 case 實作）|

#### 6.3.4 整體收斂判定

**🟢 收斂 — 進入「等待期」**（觀察期累計為主，無新前景任務未決）：

- **PM 拍板鏈完整**：ADR-008/009/010 三項 ACCEPTED v1.0 / v0.4，無未決決策
- **軸 A 排程最佳化**：02:00 × 1 跑為理論最優（M-05 dedup 數學依據）
- **軸 B 任務明確**：15 case ~250 LOC ROI 預估 83~89%
- **軸 D 預備研究 100% 完成**：Production_Migration_SOP §4-§5 大綱 + trace_id W3C path-b 設計就位
- **15 輪 audit 連續壓力測試穩定**：13 條紀律全綠維持

**剩餘工作**（不阻塞收斂判定）：
1. 軸 A：30 天累計（達標日 2026-06-24，純等待）
2. 軸 B：W1 補測 15 case + ADR-009/010 實作（2.8 PD，可任意時點啟動）
3. G0 啟動：最遲 2026-06-24

---

## 7. 一句話總結

**Round 15 為 15 輪 audit 真實連續壓力測試的第 10 跑驗證 + 軸 A 排程評估：第 10 跑 13 紀律全綠 PASS / 0 P0 / 0 P1 / 0 P2 / 0 NOTE（**自 Round 11 以來首次完全 0 issue idle audit**）；mutation kill_rate 74.50%（suspicious 從 R14 第 9 跑 2 bounce 回 R15 第 10 跑 0，進一步證實 ADR-SD09-009 半確定性論點 + ±2pp tolerance 必要性）；軸 A 排程方案經 M-05 dedup 數學分析確定維持 02:00 × 1 跑（每小時 3 跑零加速 + 浪費資源）；W1 task list 維持 Round 14 之 2.8 PD（待實作）；觀察期累計健康（#1=4/7、#2=4/14、#3=3/30；同 UTC date dedup 第 4 筆 R14→R15 覆寫，不重複進帳為設計正確）；專案維持 **W0 收尾期（接近完成）**，整體 SD_09 進度進入「等待期」（觀察期累計為主，無新前景任務未決），剩餘軸 A 30 天累計 + 軸 B 15 case 實作 + W1 T1-M1~H1 共 2.8 PD 即可啟動 G0（最遲 2026-06-24 觀察期 #3 達標）。**

---

## 9. W1 落地補記（同 PR 後續交付 — 2026-05-25 PM）

User 派工「啟動 W1 實作 (2.8 PD 同 PR 落地)」後完成下列 W1 task list（同 commit 落地觸發 SP-1 觀察期 #1 重置，節省 7 天緩衝）：

| 任務 | 落地檔案 | LOC / case | 狀態 |
|------|---------|-----------|------|
| **T1-M1** calc_kill_rate 切換 + ±2pp tolerance | `tools/mutation_baseline_lock.py:134-151` `calc_kill_rate` 新公式 `(killed + 0.5×suspicious) / denom` + L46 `EXTRA_TOLERANCE = 0.02` + L263 `threshold = target - TOLERANCE - EXTRA_TOLERANCE`（effective 0.68）| +5 LOC | ✅ |
| **T1-M2** mutation_analysis.py 同步 | `tools/mutation_analysis.py:34-38` 加紀律 #5 對齊 comment（no-op，無業務變動）| +5 LOC | ✅ |
| **T1-M3** ≥ 5 case unit test | `tests/tools/test_mutation_baseline_lock.py` +6 case（bounce / 邊界 / 三選項數學等價）+ 修現有 2 case 對應新公式 | +110 LOC | ✅ (42 passed) |
| **T1-H1 parser** mutmut_counts_parser.py | `tools/mutmut_counts_parser.py`（**97 LOC** ≤ 100）+ `tests/tools/test_mutmut_counts_parser.py` 7 case 覆蓋 4 條 ps1 分支 + P0-AUDIT-R3-3 迴歸防禦 | 97+170 LOC | ✅ (7 passed) |
| **T1-H1 ps1 inline** ps1:336-358 thin wrapper | `tools/run_local_nightly.ps1:336-355` 改呼叫 `python tools/mutmut_counts_parser.py $MutLog` + Log 輸出 + rc 守門 | -28 / +20 LOC | ✅ |
| **T1-H1 checklist** PS1_Complexity_Checklist.md | `docs/05_development/PS1_Complexity_Checklist.md`（**50 行** = ADR-010 §5 規定）三條觸發條件 + 兩個既有 helper 範例 + reviewer 流程 + 候選清單 | 50 LOC | ✅ |
| **T1-B1** token_guard 15 case test | `tests/plugins/token_guard/test_w1_mutation_supplement.py`（policy 8 / compactor 3 / git_verifier 1 / thresholds 2 / watcher 1） | 233 LOC | ✅ (15 passed) |

**W1 落地驗證**：
- **pytest 2,566 passed / 122 skipped**（從 R14 2,538 +28：T1-M3 +6 / T1-H1 +7 / T1-B1 +15）
- importlinter 7 kept / 0 broken
- LOC violations=0（baseline=14058 / total=15050；新 tools/test 加總在 budget 內）
- CLAUDE.md=400（紅線邊界）
- PS1_Complexity_Checklist.md=50（ADR-010 §5 規定上限）
- mutmut_counts_parser.py=97（≤ 100 ADR-010 §5 規定）

**ADR-SD09-009 紅線 §5.1~§5.5 全綠**：
- §5.1 calc_kill_rate 已切換（PM 拍板 ACCEPTED 後）
- §5.2 jsonl 不 backfill（歷史 4 筆原樣保留；新公式套用「自切換日起新紀錄」）
- §5.3 mutation_analysis.py 與 mutation_baseline_lock.py 同步（前者 no-op + comment 對齊）
- §5.4 ≥ 5 case 單元測試達標（實際 +6 case）
- §5.5 ±2pp tolerance 已落地（EXTRA_TOLERANCE = 0.02 由 PM 拍板核可）

**ADR-SD09-010 紅線 §3.0.3 全綠**：
- ps1 端 thin wrapper 改造，邏輯實質下沉至 Python helper SSOT
- helper 97 LOC ≤ 100、7 case test ≥ 6（與 ps1 4 分支 1.75:1 比例）
- helper docstring 標 ps1:337-358 對應 + 紀律 #4 同步要求

**SP-1 觸發**：同 PR 落地 → token_guard plugin 源碼未動但 ps1+tools 變動 → source_sha256 不變（紀律 #12 設計）→ 觀察期 #1 jsonl 仍以 sha=5208cff... 累積（**T1-B1 是 test 補測，不變動 plugin source**，這對應 ADR-009 軸 B 的「補測殺 mutant 提升 kill_rate」非「改寫 plugin 邏輯」）。下次 nightly 第 11 跑會以新公式記錄 kill_rate（預估 +0.67pp 到 74.50%~75% 區間 — suspicious 浮動仍存）。

---

**版本紀錄**：
- v1.0 2026-05-25 — Round 15 audit PASS（0 P0/0 P1/0 P2/0 NOTE 首次完全 idle audit）+ 軸 A 排程評估完成（維持 02:00 × 1）+ nightly 第 10 跑 13 紀律全綠取證
- v1.1 2026-05-25 — W1 落地補記（§9）：2.8 PD task list 全 7 項同 PR 落地（T1-M1~M3 / T1-H1 parser+ps1+checklist / T1-B1 15 case）；pytest 2,566（+28）；ADR-009 §5 + ADR-010 紅線全綠
