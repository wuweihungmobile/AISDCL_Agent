# SD_09 W3 Round 3 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — Architect+SA+SD+QA 全能修復 Round 3 audit 8 項發現 |
| Audit Round | W3 Round 3（2026-05-25） |
| Audit 發現 | 8 項（P0=1 / P1=3 / P2=4） |
| 真實修復 | 6 項（P0-1 / P1-1 / P1-2 / P1-3 / P2-2 / P2-4） |
| 列入 backlog | 2 項（P2-1 mutation history sha 舊紀錄 / P2-3 Invoke-Stage rc 字串混雜）|
| 接續 ADR | ADR-SD09-008 v0.1 PROPOSED（AC4 雙軌 p95，待 PM 拍板）|
| Commit / Tag | `987ae24` / `v2026.05.25-01` |
| Merge main | `13c197c` |
| Nightly 取證 | `logs/nightly_2026-05-24_233233.log:L238` `END nightly summary: mutation=0 pg-e2e=0 perf=2 drift=0 obs=0` |

---

## 1. 主執行檔案

| 檔案 | 內容 |
|------|------|
| [docs/05_development/SD09_Execution_Guide.md](SD09_Execution_Guide.md) v1.0 | SD_09 W0~W6 詳細執行計畫（基線升至 2,502）|
| [docs/04_planning/SD_Improving_09.md](../04_planning/SD_Improving_09.md) v1.2 | 主規劃（基線更新 2,502，含 ADR-SD09-008 待 PM 拍板說明）|
| [docs/04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md](../04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md) v0.1 | PROPOSED — AC4 雙軌 p95 設計（待 PM 拍板）|
| [docs/05_development/SD09_W3_Round2_NextAction.md](SD09_W3_Round2_NextAction.md) | Round 2 紀錄（本檔承接其 backlog）|

---

## 2. Round 3 真實修復（本次 commit 已 CLOSED）

| ID | 嚴重度 | 狀態 | 修法 | 主要檔案 |
|----|--------|------|------|---------|
| P0-1 AC4 p95 數學不可達標 | P0 | ✅ FIXED | 雙軌設計 strict 50ms + tolerant 60ms（PM 觀察用；不放寬 ready_for_labeled_pr）+ 10 case test | `tools/ac4_progress_check.py` / `tests/tools/test_ac4_progress_check.py` / `docs/04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md` |
| P1-1 pytest 基線三檔不一致 | P1 | ✅ FIXED | 手動同步三檔基線至實測 **2,502 passed / 122 skipped** | `CLAUDE.md` / `docs/05_development/SD09_Execution_Guide.md` / `docs/04_planning/SD_Improving_09.md` |
| P1-2 obs ga_check 舊紀錄 strict 拒絕 | P1 | ✅ FIXED | 改 cutoff-based：ts < 2026-05-24 寬鬆通過 + WARN；之後 strict + 2 case test | `tools/observability_ga_check.py` / `tests/tools/test_observability_ga_check.py` |
| P1-3 drift table_missing rc=0 假象綠燈 | P1 | ✅ FIXED | 內部 table_missing 分支改 rc=2 (WARN)，Invoke-Stage 自動歸類 WARN 不算 fail | `tools/run_local_nightly.ps1` |
| P2-2 Set-StrictMode 未啟用 | P2 | ✅ FIXED | 啟用 `Set-StrictMode -Version 3.0`（避免未初始化變數靜默通過；Latest 太嚴格暫不採）| `tools/run_local_nightly.ps1` |
| P2-4 mutation counts 未回流主 log | P2 | ✅ FIXED | mutation stage 末段加 5 行 counts 回流（`[mutation counts] Killed/Survived/...`），紀律 #3 取證強化 | `tools/run_local_nightly.ps1` |

---

## 3. Round 3 backlog（W1 啟動前處理）

| ID | 嚴重度 | 說明 | 預估工作量 |
|----|--------|------|-----------|
| P2-1 mutation history 前 2 筆缺 source_sha256 | P2 | W1 啟動前若連續新採集都正常會自動補上，但舊紀錄寬鬆放行可能持續削弱 P0-5 防護。需在 `mutation_baseline_lock.py` `should_lock` 邏輯確認「tail 7 筆 unique_source_sha256 >= 7」對舊紀錄的處理（目前實作：缺欄位算 unique，可能多算 1 個 unique → 偏寬鬆）。W1 範圍補一個 case test 確認此行為 | 0.25 PD |
| P2-3 Invoke-Stage rc 字串 'SKIP' 與整數混雜 | P2 | summary line `mutation=$rc1 ...` 可能出現 `mutation=SKIP perf=2` 混合型別，未來上游解析（如 nightly summary parser）需要型別一致。建議 W1 改 JSON summary 並把 SKIP 統一為 -1 整數哨兵；本次先列 backlog | 0.5 PD |

---

## 4. 未來 ADR 處置（PM 待拍板）

### 4.1 ADR-SD09-008 AC4 雙軌 p95（**待 PM 拍板**）

PROPOSED 三選項（cut-off 建議 2026-05-31）：
1. **(a)** 放寬 strict 至 60ms（推薦；與真實機器 baseline 對齊；需 PM 重新簽 ADR-SD08-003 §AC4）
2. **(b)** 保留 strict 50ms，重新 baseline 機器（性能調校 spike；風險：可能無 SLA 保證 < 50ms）
3. **(c)** 保留 strict 50ms，觀察期 #2 達標延 SD_10（W5 cutover 不會發生）

PM 觀察資料來源（本次修復後立即可用）：

```bash
$ python tools/ac4_progress_check.py --tolerant-p95-ms 60 --json
# 預期回傳：
#   "strict_streak": 0     ← p95 卡 50~60 neutral 區
#   "tolerant_streak": N   ← N 隨 nightly 累計
#   "ready_for_labeled_pr": false  ← 不放寬紅線
```

---

## 5. 取證

| 項目 | 結果 |
|------|------|
| pytest | **2,502 passed / 122 skipped / 0 failed**（含 Round 3 新增 12 case：ac4 +10 / obs +2）|
| importlinter | **7 kept / 0 broken** |
| LOC violations | **0** |
| CLAUDE.md | **391 行**（≤ 400 紅線）|
| ps1 parse | StrictMode 3.0 啟用後 `ParseFile` clean |

---

**版本紀錄**：v1.0 2026-05-25 — Round 3 audit 修復收尾；對應 commit `987ae24` / tag `v2026.05.25-01` / merge main `13c197c`。
