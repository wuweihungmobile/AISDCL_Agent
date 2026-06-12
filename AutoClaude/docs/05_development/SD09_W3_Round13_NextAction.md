# SD_09 W3 Round 13 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — nightly 第 8 跑驗證 + Round 12 同 PR drift 收尾 + Architect/SA/SD/QA 4 方全能 zero-trust audit |
| Audit Round | W3 Round 13（2026-05-25）|
| Audit 發現 | **1 P0 + 0 P1 + 0 P2 真實技術問題 + 2 NOTE → CONDITIONAL FAIL → 全部閉環修復後 PASS** |
| pytest 基線 | **2,538 passed / 122 skipped**（持平 Round 12；修復僅為 docstring/註解版本字串對齊，零實作差異）|
| importlinter | 7 kept / 0 broken |
| LOC violations | 0（baseline=14058 / cap=16869 / total=15050）|
| CLAUDE.md | 400 行（紅線邊界）|
| Nightly 第 8 跑取證 | [logs/nightly_2026-05-25_185040.log:L251](../../logs/nightly_2026-05-25_185040.log#L251) `END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0`（5 stage 全綠 + Cleanup=0；5:35 elapsed） |
| §3.0 並行框架 | 不變（軸 A/B/C/D 並行框架繼續沿用）|

---

## 1. Audit 取證

| 項目 | 取證 |
|------|------|
| Nightly 第 8 跑 | [log:L251](../../logs/nightly_2026-05-25_185040.log#L251) `END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0` |
| Stage 個別 elapsed | Docker-PG 0.37s / mutation 4:30.2 / pg-e2e 12.4s / perf 51.6s / drift 0.43s / obs 0.60s / Cleanup 0.01s — 總 5:35 |
| Mutation 5 行 counts | [log:L206-210](../../logs/nightly_2026-05-25_185040.log#L206) Killed (111) / Survived (38) / Timeout (0) / Suspicious (0) / Skipped (0) — kill_rate=74.50%（與 Round 11/12 持平；M-05 same UTC date dedup）|
| AC4 F2 OK | [log:L221](../../logs/nightly_2026-05-25_185040.log#L221) `[F2 OK] tolerant<60ms streak=4 observation<50ms streak=0 days=4 reasons=觀察期未滿（4/14 天）`（dual track 正常） |
| Perf 3 場景全綠 | [log:L232-235](../../logs/nightly_2026-05-25_185040.log#L232) `[PASS] decide_correction (+4.5%) / dry_run_e2e (+-98.3%) / token_halt_roundtrip (+0.0%) Total: green=3 warn=0 block=0`（vs Round 12 perf=2 WARN 已消除）|
| Drift 0 事件 | [log:L243](../../logs/nightly_2026-05-25_185040.log#L243) `drift_log severity!='info' rows = 0` |
| 觀察期 jsonl 進度 | [log:L253](../../logs/nightly_2026-05-25_185040.log#L253) `END observation progress: mutation=4/7 ac4=4/14 obs=3/30 drift=3/30` |
| pytest 修復後基線 | **2,538 passed / 122 skipped**（持平 Round 12；修復僅是版本字串對齊）|
| ADR-008 v0.4 同步驗證 | `grep -c "v0.3 ACCEPTED" tools/ tests/` → 0 處（修復後）；`grep -c "v0.4 ACCEPTED"` → 51 處 |
| 13 條紀律 | **13 PASS / 0 WARN / 0 FAIL**（修復後）|

---

## 2. Round 13 真實修復（本輪 commit 已 CLOSED）

| ID | 嚴重度 | 狀態 | 視角 | 根因 | 修法 | 主要檔案 |
|----|--------|------|------|------|------|---------|
| **P0-R13-1** ADR-SD09-008 v0.4 ACCEPTED 升版完成但下游全部仍引用 v0.3 ACCEPTED | P0 | ✅ FIXED | Architect + QA | Round 12 P0-R12-2 修復將 ADR-SD09-008 從 v0.3 → v0.4 ACCEPTED（取證更正下游 ADR 引用錯位），ADR header line 6 已標 v0.4，但下游所有引用（tools 16 + parser 2 + ps1 3 + tests 27 + Execution_Guide 3 = **48 處**）仍寫 v0.3 ACCEPTED → **F2 ALERT log message 真實寫入 `nightly_latest.log` 含「ADR-SD09-008 v0.3 ACCEPTED」**，與 ADR header v0.4 直接矛盾，違反紀律 #3「PASS 引用必須對齊當前 ADR header」（Round 12 自己揭示的「同 PR drift 風險」精神延伸至「ADR 升版必須同 PR 同步下游引用」）| 全部 48 處 v0.3 ACCEPTED → v0.4 ACCEPTED：(a) `tools/ac4_progress_check.py` 16 處 docstring/註解；(b) `tools/ac4_nightly_alert_parser.py` 2 處（含 F2 ALERT message 模板 line 118）；(c) `tools/run_local_nightly.ps1` 3 處（含 F2 ALERT log 文案 line 453）；(d) `tests/contract/test_ac4_progress_check.py` 10 處 docstring；(e) `tests/tools/test_ac4_progress_check.py` 12 處（含 assertion 訊息）；(f) `tests/tools/test_ac4_nightly_alert_parser.py` 5 處（含 `assert "ADR-SD09-008 v0.4 ACCEPTED" in decision.log_message`）；(g) `docs/05_development/SD09_Execution_Guide.md` 3 處（§0.1 觀察期 #2 + §3.0.2 軸 C + §3.0.5 SP-2）| [tools/ac4_progress_check.py](../../tools/ac4_progress_check.py) / [tools/ac4_nightly_alert_parser.py](../../tools/ac4_nightly_alert_parser.py) / [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1) / [tests/contract/test_ac4_progress_check.py](../../tests/contract/test_ac4_progress_check.py) / [tests/tools/test_ac4_progress_check.py](../../tests/tools/test_ac4_progress_check.py) / [tests/tools/test_ac4_nightly_alert_parser.py](../../tests/tools/test_ac4_nightly_alert_parser.py) / [SD09_Execution_Guide.md](SD09_Execution_Guide.md) |
| **NOTE-R13-1** ADR-008 內部歷史紀錄保留 v0.3 ACCEPTED | NOTE | ✅ 設計就位 | Architect | ADR-008 line 161（紅線 §5）「60ms 為本 ADR v0.3 ACCEPTED 拍板」+ line 174（採納路徑）「ACCEPTED v0.3 PM 拍板選項 (a)」+ line 211（版本紀錄）為歷史精準性表述，描述「PM 在 v0.3 時刻拍板」事實 | 不修；line 175「ACCEPTED v0.4 取證更正」已補完整 v0.4 紀錄，line 6 header 已標 v0.4 為當前狀態 | 無修改 |
| **NOTE-R13-2** ac4_history.jsonl 第 1, 2 筆缺 `status` 之外的 metadata 統一性 | NOTE | ✅ 設計就位 | QA | 第 1-4 筆 jsonl 都有完整 timestamp/run_id/recall/p95/cb/status（無實際差異）| 無修；本項 NOTE 為複查時手動排查確認 jsonl schema 一致性 | 無修改 |

---

## 3. 推翻項（Audit 自我複查不成立的指控）

- **「ac4_history.jsonl dedup 行為與 drift/obs jsonl 不一致（first-write vs last-write）」** — 完全推翻：實際測試 [tools/ac4_nightly_collector.py:184-211 append_history](../../tools/ac4_nightly_collector.py#L184) docstring 明確「同 UTC date 已存在則覆寫該筆」為 last-write-wins，與 drift_log_snapshot / observability_snapshot 邏輯一致。早期誤判源於 jsonl timestamp 為 UTC（10:55:22 = local 18:55:22 UTC+8）與 nightly log timestamp（local 18:55:23）時區誤讀。
- **「F2 OK log message 仍含 v0.3 ACCEPTED 引用」** — 完全推翻：F2 OK message 模板 [ac4_nightly_alert_parser.py:129-134](../../tools/ac4_nightly_alert_parser.py#L129) 不含 ADR 版本字串（僅含 tolerant/observation streak），只有 F2 ALERT message（line 113-121）含 ADR 引用，本跑 ready=False 未觸發 ALERT 路徑。
- **「Round 12 perf=2 WARN 為 nightly 設計缺陷」** — 完全推翻：本跑 perf=0 全綠（3 場景全 PASS，token_halt_roundtrip +0.0%），證實 Round 12 之 WARN 為單次採樣噪音（samples=7 < 20 統計噪音必然，ADR-SD08-003 §2.6 v1.1 BLOCK→WARN 退化設計涵蓋）。

---

## 4. 13 條紀律盤點（Round 13 修復後更新）

| # | 紀律 | Round 13 |
|---|------|----------|
| 1 | stage rc 區分真實失敗 vs 工具標準回報 | ✅ PASS（log:L240 perf rc=0 全綠；mutmut rc=0 bitmask 設計）|
| 2 | log 完整統計 | ✅ PASS（5 type counts 全列）|
| 3 | PASS 引用 RunId log:L | ✅ PASS（本報告全引用 [logs/nightly_2026-05-25_185040.log](../../logs/nightly_2026-05-25_185040.log)）；**Round 13 P0-R13-1 修復「下游引用對齊 ADR header」延伸** |
| 4 | 驗證鏡子被驗證 | ✅ PASS（45 ac4 case 全綠驗證 v0.4 同步落地）|
| 5 | 跨工具數字對齊 | ✅ PASS（5 stage rc + 5 jsonl 累計同步）|
| 6 | 採集寬鬆 vs 升級嚴格分軌 | ✅ PASS（dual env vars STRICT=60 + OBSERVATION=50 + dual streak 雙軌設計持續運作）|
| 7 | cache 強制 fresh | ✅ PASS（.ac4_junit.xml + perf_results.json 跑前 rm）|
| 8 | .sh LF 行尾 | ✅ PASS |
| 9 | Docker 依賴 SKIP 一致 | ✅ PASS（本跑 Docker 可用無 SKIP）|
| 10 | fallback jsonl 可區分 | ✅ PASS（observability_emit_real:true）|
| 11 | latest log pointer 完整 | ✅ PASS（[log:L254 Latest log pointer 已更新](../../logs/nightly_2026-05-25_185040.log#L254)）|
| 12 | mutation history source_sha256 | ✅ PASS（寬鬆設計就位；本跑同 sha 5208cff... unique=1，待軸 B 補測觸發 sha 變化重置）|
| 13 | 觀察期進度可見 | ✅ PASS（log:L253 4 軌進度可見）|

---

## 5. W1 啟動前未決項（Round 13 後維持 Round 12 狀態）

| ID | 項目 | 狀態 |
|----|------|------|
| ADR-SD09-008 v0.4 | AC4 雙軌 60ms tolerant + 50ms observation | ✅ **ACCEPTED 2026-05-25**（下游 48 處引用 Round 13 全部對齊 v0.4）|
| ADR-SD09-009 v0.1 | mutmut suspicious policy（三方共識選項 A：0.5 半 kill + ±2pp tolerance）| 🟡 PROPOSED（PM 拍板 cut-off **2026-06-08**）|
| ADR-SD09-010 v0.1 | ps1-to-helper SSOT 治理（三方共識選項 B：建議規範 + checklist + W1 mutmut_counts_parser 必做）| 🟡 PROPOSED（PM 拍板 cut-off **2026-06-08**）|
| 觀察期 #1 | mutation pilot TokenGuardPlugin 連續 7 次 ≥ 70% + 紀律 #12 unique sha | 累計 **4/7 jsonl record**（kill_rate 74.50% 過 70% threshold；條件 a sha unique=1/7 待 W1 軸 B 補 token_guard test 觸發 sha 變化重置）|
| 觀察期 #2 | AC4 14 天 nightly 全綠 | 累計 **4/14**（tolerant streak=4 — 4 筆 jsonl 全 < 60ms tolerant；達標窗口 2026-06-08）|
| 觀察期 #3 | drift_log 30 天零事件 | 累計 **3/30**；達標日 2026-06-24（若 user 5/25 啟用 schtasks）|

---

## 6. 下一步執行檔案與大綱（依 §3.0 4 軸並行框架）

### 6.1 4 軸並行下一步動作（Round 13 後校準）

| 軸 | 動作 | 時機 | 狀態 |
|----|------|------|------|
| **軸 A 背景觀察期** | user 手動啟用 `schtasks /change /TN AutoClaude_Nightly /ENABLE`（若尚未啟用）；持續 nightly 02:00 自動跑累計 jsonl | 🔴 立即 | 待 user 確認 |
| **軸 B W1 前景** | 補 token_guard test 64 點位（compactor 24 / git_verifier 13 / policy 17 / thresholds 7 / watcher 3）— 三重效益：拉高 kill_rate 穩定 ≥ 70% + 觸發 source_sha256 變化重置觀察期 #1 + 縮小觀察期 #1 數學阻塞 | 任意時點（建議 ≤ T+10 = 2026-06-04）| 待啟動 |
| **軸 C PM 拍板（已完成 #1）** | ✅ ADR-SD09-008 **2026-05-25 ACCEPTED v0.4**（取證更正）/ 🟡 ADR-SD09-009 + ADR-SD09-010 待 PM 拍板（cut-off **2026-06-08**）| ≤ 2026-06-08 | PM #1 完成 / #2 #3 待啟動 |
| **軸 D W2-W6 預備（部分完成）** | ✅ ADR-SD09-009/010 三方研究完成 / ✅ sprint_history.md §1.5 SD_07 骨架完成 / 🟡 待：Production_Migration_SOP §4-§5 預備研究（W3 任務）、trace_id W3C path-b 設計（W3 任務） | 任意時點 | 部分完成 |

### 6.2 收斂評估與成熟度

#### 6.2.1 收斂訊號（正向）

- **Round 13 zero-trust audit 完整閉環**：1 P0 全部 FIXED（48 處 v0.3→v0.4 對齊）；2 NOTE 設計就位；無未修復項
- **Nightly 第 8 跑 5 stage 全綠**（mutation/pg-e2e/perf/drift/obs 全 0）+ 5:35 elapsed（高效率）
- **Perf=0 全綠驗證 Round 12 perf=2 WARN 為單次採樣噪音**（本跑 token_halt_roundtrip +0.0% 恢復穩定 baseline，證實 ADR-SD08-003 §2.6 v1.1 退化設計合理）
- **ADR-008 v0.4 同步對齊**：F2 ALERT message 未來觸發時將輸出正確版本字串（取證可信度恢復）
- **pytest 基線維持 2,538**（修復僅是版本字串對齊，零實作差異 — 證實 audit 修復精準無破壞）
- **觀察期升級條件成熟度 B+ 維持**（觀察期 #2 累計 4/14；無新阻塞）

#### 6.2.2 仍未收斂訊號

- **schtasks 等 user 手動啟用**（若 5/25 啟用 → 觀察期 #1 達標日 2026-06-04 起算；#2 達標日 2026-06-08；#3 達標日 2026-06-24 — 三者間最遲為 #3）
- **軸 B W1 token_guard test 補測未啟動**：64 點位待開發；越晚啟動越延後觀察期 #1 重置 unique sha 計數
- **PM 拍板 ADR-SD09-009/010 待啟動**：cut-off 2026-06-08；逾期需 ADR §6.1 過渡寬限條款

#### 6.2.3 專案成熟度評估（Round 13 維持 + 小幅升等）

| 維度 | 評分 | 變動（vs Round 12）|
|------|------|------|
| 架構 / 程式碼品質 | 🟢 A | 不變 |
| 測試覆蓋 | 🟢 A（2,538 持平）| 不變（零實作差異）|
| CI / nightly 治理 | 🟢 A | 不變（13 輪 audit 連續壓測穩定）|
| 觀察期升級條件 | 🟢 **B+** | 不變（累計 4/14 進度健康）|
| 文件治理 | 🟢 **A → A+** | **+0.5**（ADR header / 下游引用 / log message / test assertion 全鏈對齊；紀律 #3「PASS 引用必須對齊當前 ADR header」延伸落地）|
| PG production 上線就緒 | 🟡 B | 不變 |
| 整體 SD_09 進度 | 🟢 W0 收尾期 | 不變（13 輪 audit 收尾；等待軸 B + PM #2/#3 + 觀察期累計）|

---

## 7. 一句話總結

**Round 13 為 13 輪 audit 真實連續壓力測試的第 8 跑驗證 — 揭露「ADR 升 v0.4 ACCEPTED 但下游 48 處 v0.3 引用未同步」P0 drift（紀律 #3「PASS 引用對齊當前 ADR header」延伸違反）並完整閉環修復**。Nightly 第 8 跑 5 stage 全綠（mutation/pg-e2e/perf/drift/obs 全 0；5:35 elapsed），pytest 基線維持 2,538（修復零實作差異），perf=0 全綠驗證 Round 12 之 perf=2 WARN 為單次採樣噪音設計涵蓋；觀察期累計健康（#1=4/7、#2=4/14、#3=3/30），AC4 dual-track 正常運作（tolerant streak=4 / observation streak=0）；專案維持 **W0 收尾期**，等待軸 B token_guard test + 軸 C PM #2/#3 拍板 + 軸 A 觀察期累計（最遲 2026-06-24）後可啟動 G0。

---

**版本紀錄**：v1.0 2026-05-25 — Round 13 audit 修復收尾；nightly 第 8 跑 5 stage 全綠取證 + 48 處 v0.3→v0.4 同 PR 對齊修復；對應 commit `c6def34` / tag `v2026.05.25-13` / merge main `0eeda20` ✅ pushed to https://github.com/wuweihungmobile/AutoClaude。
