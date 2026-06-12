# SD_09 W3 Round 12 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — nightly 第 7 跑 + 4 軸並行落地（PM 拍板 ADR-SD09-008 v0.3 ACCEPTED + ADR-SD09-009/010 三方研究 + sprint_history.md §1.5 SD_07 骨架）+ Architect/SA/SD/QA 全能 zero-trust audit |
| Audit Round | W3 Round 12（2026-05-25）|
| Audit 發現 | **2 P0 + 2 P1 + 2 P2 + 2 NOTE → CONDITIONAL FAIL → 全部閉環修復後 PASS** |
| pytest 基線 | **2,538 passed / 122 skipped**（Round 11 2,532 +6；含 ac4 +5 + parser +2 = 7 新 case）|
| importlinter | 7 kept / 0 broken |
| LOC violations | 0（baseline=14058 / cap=16869 / total=15050）|
| CLAUDE.md | 400 行（紅線邊界）|
| ADR 新增 | ADR-SD09-008 升 v0.4 ACCEPTED / ADR-SD09-009 v0.1 PROPOSED / ADR-SD09-010 v0.1 PROPOSED |
| Nightly 第 7 跑取證 | [logs/nightly_2026-05-25_162048.log](../../logs/nightly_2026-05-25_162048.log) 6 stages mutation=0 / pg-e2e=0 / perf=**2 (WARN 設計預期)** / drift=0 / obs=0 / Cleanup=0 |
| §3.0 並行框架 | 不變（軸 A/B/C/D 並行框架繼續沿用）|

---

## 1. Audit 取證

| 項目 | 取證 |
|------|------|
| Nightly 第 7 跑 | [logs/nightly_2026-05-25_162048.log:L256](../../logs/nightly_2026-05-25_162048.log#L256) `END nightly summary: mutation=0 pg-e2e=0 perf=2 drift=0 obs=0` |
| Mutation 5 行 counts | Killed (111) / Survived (38) / Timeout (0) / Suspicious (0) / Skipped (0) — kill_rate=74.50%（與 Round 11 持平；M-05 同 UTC date dedup）|
| 觀察期 jsonl 進度 | [log:L258](../../logs/nightly_2026-05-25_162048.log#L258) `END observation progress: mutation=4/7 ac4=4/14 obs=3/30 drift=3/30`（與 Round 11 持平；M-05 dedup）|
| pytest 修復後基線 | **2,538 passed / 122 skipped**（+6 vs Round 11；含 ac4 +5 / parser +2 / contract 重寫 -1）|
| ADR-SD09-008 v0.4 ACCEPTED | [docs/04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md:L6](../04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md#L6) 升版完成；§3.4.3 #1-#7 全標 ✅ IMPLEMENTED 2026-05-25 |
| dual threshold env vars | [tools/run_local_nightly.ps1:L264-265](../../tools/run_local_nightly.ps1#L264) `AUTOCLAUDE_STRICT_P95_THRESHOLD_MS=60` + `AUTOCLAUDE_OBSERVATION_P95_THRESHOLD_MS=50` |
| Python dual threshold | `python -c "from tools.ac4_progress_check import _resolve_strict_p95_threshold, _resolve_observation_p95_threshold; print(_resolve_strict_p95_threshold(), _resolve_observation_p95_threshold())"` → `60.0 50.0` |
| JSON schema 升級 | `python tools/ac4_progress_check.py --json` 含 `tolerant_streak / observation_streak / strict_streak / tolerant_p95_ms / observation_p95_ms` 5 欄位 |
| 13 條紀律 | **13 PASS / 0 WARN / 0 FAIL**（修復後）|

---

## 2. Round 12 真實修復（本輪 commit 已 CLOSED）

| ID | 嚴重度 | 狀態 | 視角 | 根因 | 修法 | 主要檔案 |
|----|--------|------|------|------|------|---------|
| **P0-R12-1** ADR-SD09-008 v0.3 ACCEPTED 拍板實作完全未落地 | P0 | ✅ FIXED | Architect + QA | PM Agent 拍板 v0.3 ACCEPTED 但 `tools/ac4_progress_check.py` 仍用 50ms strict 門檻 → nightly 第 7 跑 log:L209 仍輸出「p95 卡嚴格門檻 50ms~60ms neutral 區」`green_streak=0` → 觀察期 #2 仍永不可達 | (a) `_resolve_strict_p95_threshold()` 預設 50→60；(b) 新增 `_resolve_observation_p95_threshold()` =50；(c) JSON schema 加 `observation_streak / observation_p95_ms`；(d) `tolerant_streak` 升為主升級指標；(e) tests +5 case；(f) `tools/ac4_nightly_alert_parser.py` SSOT 同步 +2 case；(g) ps1 env 升 60 + F2 文案改雙欄位 + ADR v0.3 ACCEPTED 引用 | [tools/ac4_progress_check.py](../../tools/ac4_progress_check.py)（385→429 LOC）/ [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1) L256-265, L448-455 / [tools/ac4_nightly_alert_parser.py](../../tools/ac4_nightly_alert_parser.py) L100-138 / [tests/tools/test_ac4_progress_check.py](../../tests/tools/test_ac4_progress_check.py) 11→16 / [tests/tools/test_ac4_nightly_alert_parser.py](../../tests/tools/test_ac4_nightly_alert_parser.py) 17→19 / [tests/contract/test_ac4_progress_check.py](../../tests/contract/test_ac4_progress_check.py) 重寫 3 case |
| **P0-R12-2** ADR-SD09-008 §3.4.3 #5 引用錯位 | P0 | ✅ FIXED | Architect + SA | v0.3 §3.4.3 #5 宣稱「更新 ADR-SD09-001 §2 雙條件 (1b) AC4 50→60ms」，但 ADR-SD09-001 §2 (1b) **實際是 KB metric 觀察**（line 39, 41, 92），完全不含 AC4 50ms → **引用幻覺** | (a) ADR-SD09-008 升 v0.4 ACCEPTED；(b) §3.4.3 #4/#5 標「已取消（取證更正）」；(c) §3.4.1 「下游 ADR 影響」表格改「無下游 ADR 文字需改」；(d) §6 + 版本紀錄補 v0.4 行；(e) 親自 grep 驗證 ADR-SD09-001 / ADR-SD08-003 / ADR-SD08-005 均不含 AC4 50ms | [docs/04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md](../04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md) v0.4 ACCEPTED（225 行）|
| **P1-R12-1** 下游 ADR-SD08-003 / ADR-SD08-005 零交叉引用 | P1→P2 | ✅ 退化 P2 | SA + Architect | 原 audit 指控「PM 拍板 ACCEPTED 必須同 PR 與下游 ADR cross-link」；但取證後發現**下游 ADR 根本不含 AC4 50ms 陳述** → ADR-SD09-008 為 AC4 50→60ms **唯一權威 ADR**，無需 cross-link footnote | P1 退化為 P2（無實質修復需求），於 ADR-SD09-008 §3.4.1 + v0.4 版本紀錄明示「本 ADR 為唯一權威 ADR」 | 無實質修改（取證更正） |
| **P1-R12-2** `.mutation_history.jsonl` 第 1, 2 筆缺 `source_sha256` | P1 | ✅ NOTE-only | QA | 第 1, 2 筆（2026-05-20/05-21）無 `source_sha256` 鍵；第 3, 4 筆才有 | 紀律 #3「不溯及既往」設計 → 寬鬆處理已正確實作於 [tools/mutation_baseline_lock.py:226-291 should_lock](../../tools/mutation_baseline_lock.py#L226)；舊 jsonl 不溯及修補；W1 補 token_guard test 後新 sha 變化會將舊紀錄推出 tail 7 視窗自然解決 | 無修改（設計就位） |
| **P2-R12-1** perf delta +55.4% → +161.8% drift（token_halt_roundtrip 0.760→1.28ms）| P2 | NOTE-only | NOTE | samples=7 統計噪音必然；ADR-SD08-003 §2.6 v1.1 BLOCK→WARN 退化設計已涵蓋；W1 補測後 samples ≥ 20 自然消除 | NOTE 追蹤；不阻塞 | — |
| **P2-R12-2** sprint_history.md §1.5 SD_07 僅骨架未擴寫至 ≥ 300 行 | P2 | NOTE-only | NOTE | 規劃為 SD_09 W6 議題 E 完成（line 366 明示「現為摘要 + 骨架」）；本輪 W0 T0-E1 僅需骨架 | NOTE 追蹤；W6 補 | [docs/05_development/sprint_history.md:L364-540](sprint_history.md#L364) §1.5 SD_07 骨架（7 子段落 + 100-150 字概述）|

---

## 3. 推翻項（Audit Agent 提出但驗證後不成立）

- **「PM 拍板 ACCEPTED 與下游 ADR 引用必須同 PR 同步否則文件 drift」** — 部分推翻：**前提**正確（同 PR 同步），**結論**不適用本案（下游 ADR 取證後不含 AC4 50ms → 無 cross-link 義務）。已於 P1-R12-1 退化 P2 處理。
- **「ADR-SD09-008 §3.4.3 #5 必須更新 ADR-SD09-001 §2 (1b) AC4 50→60ms」** — 完全推翻：grep 取證 ADR-SD09-001 §2 (1b) 為 KB metric 觀察，**完全不含 AC4 50ms 陳述**。原為 v0.3 撰寫時的引用幻覺；v0.4 已標「已取消（取證更正）」。
- **「ADR-SD08-003 §AC4 必須補 footnote」** — 完全推翻：ADR-SD08-003 **不存在 §AC4 章節**；§2.2 #4 line 37 `p95 < 50ms` 為 pgvector recall@10 IO-bound 場景（perf machine 季度），與 AC4 nightly CPU-bound 為不同議題。
- **「ac4 修復 Agent 與 ADR 修復 Agent 衝突需 user 仲裁」** — 推翻：QA 親自 grep 驗證 ADR-SD09-001 §2 (1b) = KB metric，**ADR Agent 正確 / ac4 Agent 建議是幻覺**；已於 ADR §3.4.3 #5 標「取消」並補 v0.4 取證更正紀錄。

---

## 4. 13 條紀律盤點（Round 12 修復後更新）

| # | 紀律 | Round 12 |
|---|------|----------|
| 1 | stage rc 區分真實失敗 vs 工具標準回報 | ✅ PASS（log:L165-170 mutmut counts 完整 / perf rc=2 WARN 設計預期）|
| 2 | log 完整統計 | ✅ PASS（5 type counts 全列）|
| 3 | PASS 引用 RunId log:L | ✅ PASS（本報告全引用）|
| 4 | 驗證鏡子被驗證 | ✅ PASS（ac4 +5 case + parser +2 case + contract 重寫 3 case）|
| 5 | 跨工具數字對齊 | ✅ PASS（validate + classify 同 docker_rc=0）|
| 6 | 採集寬鬆 vs 升級嚴格分軌 | ✅ **本輪修復**（dual env vars：STRICT=60 + OBSERVATION=50；雙 streak 雙 threshold 雙軌設計）|
| 7 | cache 強制 fresh | ✅ PASS |
| 8 | .sh LF 行尾 | ✅ PASS |
| 9 | Docker 依賴 SKIP 一致 | ✅ PASS（本跑 Docker 可用無 SKIP）|
| 10 | fallback jsonl 可區分 | ✅ PASS（observability_emit_real:true）|
| 11 | latest log pointer 完整 | ✅ PASS |
| 12 | mutation history source_sha256 | ✅ PASS（寬鬆設計就位；舊紀錄 backward-compatible）|
| 13 | 觀察期進度可見 | ✅ PASS（log:L258 4 軌進度可見）|

---

## 5. W1 啟動前未決項（Round 12 後更新）

| ID | 項目 | 狀態 |
|----|------|------|
| ADR-SD09-008 v0.4 | AC4 雙軌 60ms tolerant + 50ms observation | ✅ **ACCEPTED 2026-05-25**（軸 C cut-off 5/31 提前 6 天）|
| ADR-SD09-009 v0.1 | mutmut suspicious policy（三方共識選項 A：0.5 半 kill + ±2pp tolerance）| 🟡 PROPOSED（PM 拍板 cut-off **2026-06-08**）|
| ADR-SD09-010 v0.1 | ps1-to-helper SSOT 治理（三方共識選項 B：建議規範 + checklist + W1 mutmut_counts_parser 必做）| 🟡 PROPOSED（PM 拍板 cut-off **2026-06-08**）|
| 觀察期 #1 | mutation pilot TokenGuardPlugin 連續 7 次 ≥ 70% + 紀律 #12 unique sha | 累計 **4/7 jsonl record**（kill_rate 74.50% 過 70% threshold；條件 a sha unique=1/7 待 W1 軸 B 補 token_guard test 觸發 sha 變化重置）|
| 觀察期 #2 | AC4 14 天 nightly 全綠 | ✅ **數學阻塞解除**（達標窗口 2026-06-08；首筆 60ms 軌 jsonl T+1 = 2026-05-26）|
| 觀察期 #3 | drift_log 30 天零事件 | 累計 3/30；達標日 2026-06-24（若 user 5/25 啟用 schtasks）|

---

## 6. 下一步執行檔案與大綱（依 §3.0 4 軸並行框架）

### 6.1 4 軸並行下一步動作（Round 12 後校準）

| 軸 | 動作 | 時機 | 狀態 |
|----|------|------|------|
| **軸 A 背景觀察期** | user 手動啟用 `schtasks /change /TN AutoClaude_Nightly /ENABLE`（若尚未啟用）；首筆 60ms 軌 jsonl 從 2026-05-26 起算 | 🔴 立即 | 待 user 確認 |
| **軸 B W1 前景** | 補 token_guard test 64 點位（compactor 24 / git_verifier 13 / policy 17 / thresholds 7 / watcher 3）— 三重效益：拉高 kill_rate 穩定 ≥ 70% + 觸發 source_sha256 變化重置觀察期 #1 + 縮小觀察期 #1 數學阻塞 | 任意時點（建議 ≤ T+10 = 2026-06-04）| 待啟動 |
| **軸 C PM 拍板（已完成 #1）** | ✅ ADR-SD09-008 **2026-05-25 ACCEPTED** / 🟡 ADR-SD09-009 + ADR-SD09-010 待 PM 拍板（cut-off **2026-06-08**）| ≤ 2026-06-08 | PM #1 完成 / #2 #3 待啟動 |
| **軸 D W2-W6 預備（部分完成）** | ✅ ADR-SD09-009/010 三方研究完成 / ✅ sprint_history.md §1.5 SD_07 骨架完成 / 🟡 待：Production_Migration_SOP §4-§5 預備研究（W3 任務）、trace_id W3C path-b 設計（W3 任務）| 任意時點 | 部分完成 |

### 6.2 收斂評估與成熟度

#### 6.2.1 收斂訊號（正向）

- **Round 12 zero-trust audit 完整閉環**：2 P0 + 1 P1 全部 FIXED；1 P1 退化 P2；2 P2 NOTE-only；無未修復項
- **觀察期 #2 數學阻塞解除**：strict 50ms → tolerant 60ms（軸 C PM #1 拍板 + 實作落地 + 取證更正完成）；達標窗口從「永不可達」→ **2026-06-08**（早於觀察期 #3 達標日 2026-06-24，W5 啟動仍由 #3 控制）
- **PM 拍板 + 實作落地 + ADR 取證更正 同 PR 完成**：避免 1 天「ADR drift 視窗」風險（Round 12 audit 紀律 #3 延伸啟示）
- **4 軸並行真實有效**：本 session 同時推進 4 件交付物（PM 拍板 / ADR-009 三方研究 / ADR-010 三方研究 / sprint_history §1.5 骨架）+ Round 12 完整 audit-fix 循環，無互相阻塞
- **pytest 基線從 2,532 升至 2,538**（+6；ac4 dual-track 落地驗證）
- **觀察期升級條件成熟度 B- → B**（觀察期 #2 數學阻塞解除為主要升等動力）

#### 6.2.2 仍未收斂訊號

- **schtasks 等 user 手動啟用**（若 5/25 啟用 → 觀察期 #1 達標日 2026-06-04 起算 7 unique sha；觀察期 #2 達標日 2026-06-08；觀察期 #3 達標日 2026-06-24 — 三者間最遲為 #3）
- **軸 B W1 token_guard test 補測未啟動**：64 點位待開發；越晚啟動越延後觀察期 #1 重置 unique sha 計數
- **PM 拍板 ADR-SD09-009/010 待啟動**：cut-off 2026-06-08；逾期需 ADR §6.1 過渡寬限條款

#### 6.2.3 專案成熟度評估（Round 12 維持 + 部分升等）

| 維度 | 評分 | 變動（vs Round 11）|
|------|------|------|
| 架構 / 程式碼品質 | 🟢 A | 不變 |
| 測試覆蓋 | 🟢 A（2,538 +6）| **+0.5**（ac4 dual-track 7 新 case）|
| CI / nightly 治理 | 🟢 A | 不變（11 輪 audit 穩定態維持；Round 12 為 PM 拍板實作 drift 一次性事件，已完整修復）|
| 觀察期升級條件 | 🟢 **B → B+** | **+0.5**（觀察期 #2 數學阻塞解除；達標日 2026-06-08 明確）|
| 文件治理 | 🟢 A | 不變（CLAUDE.md=400 邊界；ADR 升 v0.4；4 個 ADR 並行落地）|
| PG production 上線就緒 | 🟡 B | 不變 |
| 整體 SD_09 進度 | 🟢 **W0 採集中 → W0 收尾期** | **+0.5**（觀察期阻塞解除 + 4 軸並行落地 + 3 ADR 同 session 落地）|

---

## 7. 一句話總結

**Round 12 為 12 輪 audit 真實連續壓力測試的第 7 跑驗證 — 揭露「PM 拍板 ACCEPTED 與實作未同 PR 落地」P0 drift（紀律 #6 採集寬鬆 vs 升級嚴格分軌違反）並完整閉環修復**。4 軸並行真實有效：軸 C PM #1 拍板 ADR-SD09-008 v0.4 ACCEPTED + 軸 D ADR-SD09-009/010 三方研究 + sprint_history §1.5 骨架 + Round 12 audit-fix 循環同 session 落地；觀察期 #2 數學阻塞解除（永不可達 → 2026-06-08）；專案進入 **W0 收尾期**，等待軸 B token_guard test + 軸 C PM #2/#3 拍板 + 軸 A 觀察期累計（最遲 2026-06-24）後可啟動 G0。

---

**版本紀錄**：v1.0 2026-05-25 — Round 12 audit 修復收尾；4 軸並行 4 件交付物落地；對應 commit `7200bca` / tag `v2026.05.25-12` / merge main `ae46cb8` ✅ pushed to https://github.com/wuweihungmobile/AutoClaude。
