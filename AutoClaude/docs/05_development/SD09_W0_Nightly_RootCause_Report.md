# SD_Improving_09 W0 — Nightly 反覆修不通的根本原因報告

| 項目 | 內容 |
|------|------|
| 報告版本 | v1.0 |
| 撰寫日期 | 2026-05-21 |
| 觸發事件 | 用戶手動執行 `tools\run_local_nightly.ps1` 觸發 W0 二次 zero-trust audit |
| 觸發問題 | "為何修這麼多次, 還無法執行, 根本問題是甚麼?" |
| 適用範圍 | SD_09 觀察期 #1（mutation） / #2（AC4） / #3（drift） + perf-baseline |

---

## 1. 表象事實：歷次修復一覽

| 輪次 | 觸發 | 修了什麼 | 修完仍存在的真問題 |
|------|------|---------|------------------|
| 首次 | SD_08 W6 G6 後 nightly 上線 | 初版 ps1 直接 `bash -c "..."` | here-string 截斷 → mutmut 命令參數遺失 |
| 第 1 輪 | 2026-05-19 nightly fail | PS here-string 截斷修為獨立 sh script | mutmut baseline 仍 crash；沒人發現 |
| 第 2 輪 | 2026-05-20 zero-trust audit FAIL | P0-1/P0-3/P1-1/P1-2/P1-3/P1-4 共 6 項（編碼、檔名、`alembic` DSN swap、AC4 collector 門檻判定） | mutmut 仍只是「載具修好了」但跑不通；`.mutmut-cache` 假 PASS |
| 第 3 輪 | 2026-05-20 23:47/23:56/00:01 多次重跑 | QA 二輪 audit「核准通過（含可接受殘留）」 | 文件聲稱「修復後 ✅」、實測 latest log 持續 `perf=1` |
| W0 二次 audit | **2026-05-21**（本報告） | P0-A/B/C/D/E + P1-F/G/I 共 8 項 — 改打根因 | 觀察期 #1 結構性測試覆蓋不足（S-1）；perf samples=7 統計噪音必然（S-2）|

> 「明明修了 6 次以上 + 文件聲稱已綠，為何 latest log 仍 `perf=1`、`mutation=0`？」 — 這就是本報告要回答的根本問題。

---

## 2. 根本原因：四個層次的系統性失靈

### S-1 載具修了，根因沒修 — mutmut 永遠是「假 PASS」

**直接觀察**：
- `run_mutmut_in_docker.sh` 尾端 `exit 0` 蓋過 `mutmut run exit=2`（baseline crash）
- ps1 用 `validate_mutmut_log` 通過 → 蓋過 docker rc
- mutmut 從**舊 `.mutmut-cache`** 撈出 `Survived 🙁 (64)` 騙過 regex 驗證
- stage 因此回報 `mutation=0`（PASS）— 觀察期 #1 累積 1/7「全綠紀錄」

**根因鏈**（前 3 輪沒人追到）：
1. 第 1 輪只看「ps1 改用 sh script，截斷問題沒了」就過關
2. 第 2 輪 QA audit 看 `mutation_token_guard.log` 含 `Survived (64)` 就視為「真實 run」
3. 沒有人問：「`mutmut run` 的 exit code 是什麼？」、「.mutmut-cache 從哪來？」
4. 沒人對齊「`mutation_baseline_lock.py` 報 64 vs `mutation_analysis.py` 報 11」這明擺著的不一致

### S-2 統計樣本不足 → perf 抖動屬必然，不是「偶然」

**直接觀察**：
- `.perf_baseline.toml` 各場景 `samples=7`，p95 == p99（樣本變異不足以分離分布）
- nightly 每次跑 1 個 batch 7 samples 與 baseline 比對 → **±20~80% 抖動是統計必然**
- 文件 §464 (a)「perf baseline 機器抖動屬 ADR-SD08-003 既知限制」是把「結構性問題」包裝成「已知不修」
- §451 同時又寫「修復後 perf exit=0」自相矛盾

**根因**：ADR-SD08-003 §2.6 鎖 baseline policy 是「連 7 次達標即鎖」，未約束**最小樣本數**；7 samples 對 ms-級 IO-bound 場景不足以提供穩定 p95，當然每次 nightly 都會至少一個場景跳超 ±15%。

### S-3 文件記錄與實測脫鉤 — 「修復後 ✅」是宣稱不是取證

**直接觀察**：
- SD_Improving_09.md §451 表格寫「修復後 perf exit=0」、「p95=45.57ms recall=0.999」
- 但 `logs/nightly_latest.log` END summary 持續是 `perf=1`、`.ac4_history.jsonl` 最新一筆是 `p95_ms=51.5/52.45`
- 表格用的是「某一輪歷史綠燈快照」，不是 latest 真實狀態

**根因**：W0 修復流程缺乏「single source of truth」紀律 —
- 沒人規定「PASS 聲稱必須引用具體 RunId log 行號」
- QA 二輪 audit 用「歷史快照」核章，沒比對 latest
- 「修復後狀態 ✅」用詞太誇張，把結構性風險用樂觀文字掩蓋

> **2026-05-21 W2 收尾更新（SD_09 W2 nightly zero-trust audit P0-4 修復）**：
> 本報告原文反映 W0 二次 audit 當下觀察（perf=1 / p95=51~52ms）。
> 最近一次 PG/Docker 可用 nightly run = `logs/nightly_2026-05-21_172704.log:L226`：
> `END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0`（全綠），
> 且 `:L176` `p95_ms=49.14`（嚴格 50ms 門檻已過一日）；
> 已由 [SD_Improving_09.md §7](../04_planning/SD_Improving_09.md) W2 收尾段落滾動取代，
> `logs/nightly_latest.log` 為單一真相（紀律 #3）。
>
> **2026-05-24 W3 nightly zero-trust audit 驗證更新（PM 派工 + Architect/SA/SD/QA 全能專家）**：
> 用戶手動執行 `tools\run_local_nightly.ps1` 觸發 W3 驗證；本次驗證涵蓋兩條 nightly 跑：
>   - 21:09 Docker daemon 未啟動：`logs/nightly_2026-05-24_210930.log:L109`
>     `END nightly summary: mutation=SKIP pg-e2e=SKIP perf=0 drift=0 obs=0`
>     → 暴露 **P0-DRIFT-1**：drift stage 在 Docker 不可用時跑 15ms、未寫 jsonl、未發 WARN，
>     但 stage rc=0 偽報「綠燈」（給人觀察期 #3 進帳一天假象）。違反紀律 #1 / #3 + 跨 stage 一致性。
>   - 21:14 Docker daemon 已啟動：`logs/nightly_2026-05-24_211446.log:L235`
>     `END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0`（全綠，真實取證）
>     - mutation: kill_rate=0.7449（觀察期 #1 累計第 N 天 ≥ 70%）✅
>     - AC4: recall=0.999 / p95=51.45ms（採集寬鬆 80ms PASS；嚴格 50ms 觀察期 #2 累計中）
>     - drift: severity!='info'=0（觀察期 #3 累計）✅
>     - perf: 3 scenarios green / undersample samples=7<20 BLOCK→WARN 降級（語意一致）
>     - obs: emit_count=3 / trace_continuity=true / KB 4-key schema ✅
>
> **修復**：`tools/run_local_nightly.ps1` drift stage 拆 if-else 對齊 mutation/pg-e2e SKIP 語意 +
> 寫一筆 table_missing=True jsonl record（passed=False 不計入觀察期 #3 天數）；
> ac4_junit.xml 跑前強制 fresh（紀律 #7）。
> **降級至 P1**：observability_emit_count 寫死 3 → 屬 proof-of-life heartbeat 語意（已澄清註解），
> runtime cumulative counter 入議題 G W2 PG 持久化 backlog。

### S-4 採集寬鬆 + 升級嚴格未分軌 — 把 80ms 放水當「pass」

**直接觀察**：
- ps1 設 `AUTOCLAUDE_TEST_P95_THRESHOLD_MS=80`（Windows + Docker 容忍）
- `ac4_progress_check.py` 同 env 讀 → 升級判定一併 80ms
- p95=51.5ms 在 80ms 環境下被判 pass，但 PM #2 拍板門檻是 **50ms**
- 觀察期 #2 第一筆「pass」是 80ms 放水換來的，不是真達標

**根因**：env override 設計時只考慮「採集容忍」沒分軌「升級嚴格」；單一 env var 同時控制兩種語義 = 必然出問題。

---

## 3. 為何修這麼多次仍無法執行？三層失靈疊加

| 層次 | 失靈內容 |
|------|---------|
| **載具層** | 第 1~3 輪修「PS quoting / log encoding / 檔名 / DSN」— 都是表面 |
| **驗證層** | `validate_mutmut_log.py` regex 過寬（容忍 cache dump）+ ps1 用 log validity 蓋過 docker rc + ac4_collector 用同 env 判定升級 = **驗證機制本身有 bug 還在當鏡子用** |
| **流程層** | 沒人對齊「latest log」+ 「mutation_analysis vs baseline_lock 數字不一致」+ 「perf samples=7 抖動」之間的證據鏈 |

**簡言之**：前幾輪修的都是看得見的問題；看不見的（驗證鏡子本身有偏差）一直被當真相用，所以每修一輪「聲稱已綠」一次，下一輪再被新 audit 暴露為「其實沒綠」。

---

## 4. 本輪 W0 二次 audit 修復（已 APPROVED）

| 級別 | 缺陷 | 修法 | 取證 |
|------|------|------|------|
| P0-A | mutmut baseline crash 假 PASS | `rm -rf .mutmut-cache` + `exit "${MUTMUT_RC}"` | latest log `cache cleared` |
| P0-B | ps1 log validity 蓋 docker rc | `if ($dockerRc -ne 0) { ERROR + return }` | （由 P0-F 取代修正）|
| P0-C | Python stdout 中文亂碼 | `[Console]::OutputEncoding=UTF8` + `PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1` | latest log 中文全正確 |
| P0-D | survived 64 vs 11 不一致 | `_expand_id_tokens` 展開 dash range + summary assertion | parsed=64 與 summary 一致 |
| P0-E | SD_09.md §451 表格與實測矛盾 | 重寫 §431-490 引入 single-source-of-truth 紀律 | 表格已改為真實狀態 |
| P1-F | perf samples=7 無提示 | `MIN_BASELINE_SAMPLES=20` 警示（不阻塞） | 三 scenario 全列 warning |
| P1-G | 採集寬+升級嚴未分軌 | 雙軌：採集 80ms / progress_check 強制 50ms | `status=pass` + `consecutive_failures=1` |
| P1-I | drift_log 表不存在仍計入 | `information_schema.tables` 驗證；不存在標 N/A | `rows=0`（表存在則正常計） |

**QA 複審 V-1 ~ V-10 全 PASS — APPROVED**。

## 4.5 本輪 W0 三次 audit 補修（2026-05-21 PM 派工）

QA APPROVED 後使用者問「mutation 4 分鐘是否完整跑完」— 調查發現 P0-B 修正過度嚴格，把 mutmut 標準回報碼 `exit=2`（有 survived）當 crash → 觀察期 #1 永遠 fail，且 `mutation_token_guard.log` 缺 `Killed (N)` 行 → kill_rate=0% **假象**。

| 級別 | 缺陷 | 修法 | 取證 |
|------|------|------|------|
| P0-F | mutmut exit code 是 bitmask（bit0=exception, bit1=survived, bit2=timeout, bit3=suspicious），不是固定值 | sh `(MUTMUT_RC & 1) == 0` 判定；ps1 `if (($dockerRc -band 1) -ne 0)` 才算 fail | 手動 docker 跑 mutmut → progress 末行 `🎉 85 ⏰ 0 🤔 0 🙁 64 🔇 0` total=149 |
| P0-G | `mutmut results` 不列 Killed 數 → baseline_lock 算 kill_rate=0% | sh 用 sqlite3 直接 query `.mutmut-cache` 的 `Mutant` 表，產出完整 5 行 counts 寫在 log **末尾**（raw + dash range 於前段給 mutation_analysis；末尾 counts 給 baseline_lock） | 手動驗證 `kill_rate=53.69%`（80/149），`mutation_analysis.py` parsed=64 與 summary 一致 |

**重要發現**：mutation 跑 ~4 分鐘是**正常**（149 mutation × pytest token_guard <1s/test = 約 3~4 分鐘，加 baseline + pip ~1~2 分鐘）；不是 crash 提前結束。

---

## 4.7 W3 zero-trust audit Round 2（2026-05-24 22:30 clean nightly run）

**觸發**：使用者重跑 nightly（無 tail -F 干擾）→ `logs/nightly_2026-05-24_223310.log`（22:33~22:38, 13383 bytes, 6 stages 全綠 `mutation=0 pg-e2e=0 perf=0 drift=0 obs=0`）。Audit Agent 找出 **28 項（P0=7 / P1=10 / P2=11）**。

### 推翻項（clean run 取證）

| 原指控 | 取證 | 結論 |
|--------|------|------|
| **P0-7 編碼** Round 1 ps1 中文破壞 | `nightly_2026-05-24_223310.log` line 5 「沿用既有 container」/ line 76「觀察期」/ line 180「比對結果」/ line 231「保留」均正常顯示 | **推翻** |
| **P0-4 F2 alert 不觸發** | log line 220 `[2026-05-24 22:38:05][INFO] [F2 OK] AC4 觀察期 #2 累計中 status=observing green_streak=0 days=3` | **推翻** |
| **P0-1 latest pointer 不指最新** | `logs/nightly_latest.log` 已指向 13272 bytes 完整 22:38 run | **暫時 OK**（後續硬化） |

### 真實修復項（本次 commit）

| 級別 | 缺陷 | 修法 | 取證 |
|------|------|------|------|
| P0-2 | `Add-Content -Encoding utf8` 內部以 FileShare.Read 開檔 → 與 tail -F 同時讀時 Windows file lock 互卡 → 偶發 IOException stage crash | 新增 `Add-LogLineSafe`：`[System.IO.File]::Open` + `FileShare.ReadWrite` + retry 5 次（50/100/150/200/250ms 指數退避，上限 750ms）；Log / Invoke-Native 全改呼叫此 helper；UTF-8 無 BOM | `tools/run_local_nightly.ps1:62-110` |
| P0-3 | `drift_log_ga_check.py` 不存在 → 觀察期 #3 無 GA 工具 + drift_log_snapshot 同日去重 SKIP 覆寫真實取值 | 新建 `tools/drift_log_ga_check.py`（166 LOC ≤ 200 data tier，仿 observability_ga_check）；`drift_log_snapshot.append_snapshot` 加 `kept_existing` 分支：同日新紀錄 `table_missing=True` 但舊紀錄 `table_exists=True` → 保留舊（紀律 #9 跨 stage 一致性） | 新檔 `tools/drift_log_ga_check.py` + `tests/tools/test_drift_log_ga_check.py` 14 case + drift_log_snapshot 補 2 case |
| P0-5 | mutation history 缺 source_sha256 → 同 commit 跑 7 次可騙過 lock | `mutation_baseline_lock.py` 加 `compute_source_sha256()`（plugin 目錄所有 .py sha256 截 16 chars）；`should_lock` 強制 tail 7 筆 `unique sha ≥ 7`（缺欄寬鬆相容） | `tests/tools/test_mutation_baseline_lock.py` 補 4 case |
| P0-6 | perf summary `perf=0` 同時表示「真綠」與「BLOCK→WARN 退化」 → 觀察期等待無法區分 | `perf_regression_check.py` rc 三態 0=綠 / 2=warn / 1=block；`Invoke-Stage` rc=2 標 WARN 不算 fail | `tests/tools/test_perf_regression_check.py` 補 2 case |
| P1-1 | observability `emit_real` 欄位於舊紀錄缺失 → 新 nightly 漏寫欄位假象綠燈 | `_is_green()` 加 `strict_emit_real` 參數；`_compute_green_streak()` 最新 3 筆強制 strict；新建 `tools/_backfill_emit_real.py` 一次性 backfill 工具（dry-run / --apply） | `tests/tools/test_observability_ga_check.py` 補 2 case |
| P1-2 | mutation log mtime 未守 → 讀到 stale 殘留 log 可能假 PASS | `--require-log-mtime-within-seconds 3600` 參數；ps1 stage 呼叫加此參數；超時 exit 1 | 2 case |
| P1-7 | samples=20 邊界未測試 | `test_check_block_at_min_samples_exact`（必須觸發真 BLOCK rc=1）+ `test_check_warn_alone_emits_rc_2` | tests |
| P1-8 | `_emit_heartbeat_and_count` 單一 emit 失敗 → 整段 fallback 損失 partial-success 信號 | Step 1 import 失敗才走 fallback；Step 2 三段 emit 各自 try/except，count 累計 partial success | `tests/tools/test_observability_snapshot.py` 補 2 case |

### P2 列入 W1 backlog（11 項）

`logs/nightly_latest.log` pointer 硬化 / `.mutmut-cache` 共享 + sqlite3 query helper 抽出 / drift_log table 自動 alembic upgrade / perf samples > 20 後自動切回嚴格 BLOCK / ps1 各 stage 對 LOG_FILE env 一致命名 / observability snapshot 改注入 IKbMetricStore.read_latest() 取得真實跨 session counter / 等。

### Clean run 取證行號

- `logs/nightly_2026-05-24_223310.log:L237` `END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0`
- 6 stages 全綠，elapsed 5min 46s（紀律 #3 RunId log:L 引用）

---

## 5. Next Action（W1 / W2 / ADR 修訂）

| 動作 | 範疇 | 對應問題 | 啟動時機 |
|------|------|---------|---------|
| **A-1** 補 token_guard test 對 64 survived mutation 點位（compactor 24 / git_verifier 13 / policy 17 / thresholds 7 / watcher 3）；目標將 kill_rate 從 ~54% 提升至 ≥ 70% | W1 範疇 | 觀察期 #1 結構性測試覆蓋不足 | W1 G0 前盤點 `mutation_backlog_token_guard.md` |
| **A-2** ADR-SD08-003 §2.6 修訂 — baseline lock policy 升至 `samples ≥ 20` | ADR 修訂 | S-2 perf 統計噪音 | 觀察期 #2/#3 完成前 |
| **A-3** 連續累積 13 次 nightly 後重新 lock perf baseline（samples ≥ 20）再啟用 BLOCK 判定 | W2 範疇 | S-2 perf | W2 啟動 |
| **A-4** 真實 PG（非 mock）後驗證 50ms 是否在 Windows + Docker Desktop 可重現達標；不可達則回 PM 重議 50/60/80 三選一 | W1 範疇 | S-4 雙軌嚴格門檻 | 觀察期 #2 採集 14 天後 |
| **A-5** 自訂 Docker image 預灌 [dev,postgres,pgvector,lint] + mutmut 2.4.3 推 GHCR | P2 加速優化 | T-7 每次重灌 17.7s | 不阻塞，加速優化 |
| **A-6** `LASTEXITCODE` race 累計修補（每個 `Invoke-Native` 後保留 rc） | P2 follow-up | T-8 | 不阻塞 |

---

## 6. 流程改善建議（避免下一輪「修了又沒修」）

1. **PASS 聲稱必須引用 RunId log 行號** — 不接受概括「修復後 ✅」表述（已寫入 SD_09.md §「單一真相取證」）
2. **驗證鏡子本身要被驗證** — 引入 `validate_mutmut_log.py` 單元測試（已 15 case），未來新 collector 同樣需要對「真實 run vs cache dump」的判別測試
3. **跨工具數字對齊 assertion** — `mutation_analysis` vs `mutation_baseline_lock` 任何時候 survived 數字不一致 → 印 WARN（本輪已落地）
4. **採集寬鬆 vs 升級嚴格分軌** — 任何 env override 必須明示「採集 / 升級」雙軌語義（本輪已落地）

---

## 7. 結論

「修這麼多次仍無法執行」的根本原因 = **驗證鏡子本身有偏差 + 文件以宣稱代替取證 + 結構性問題（樣本不足、測試覆蓋不足）被當「已知殘留」掩蓋**。

本輪 W0 二次 audit 不是再修一次「載具」，而是**直接打驗證鏡子本身的 bug + 加紀律**。後續觀察期 #1 達標需要的是補 token_guard test（A-1，W1 範疇）；perf 需要的是升 baseline samples（A-2/A-3，ADR 修訂）；這兩者**都不在 nightly 工具範圍內**。

---

**文檔元數據**：v1.0 | 2026-05-21 | QA 二次 audit 後產出 | 撰寫者 Tech Lead 場景 A 個人開發 | 對應 SD_Improving_09.md §附錄 W0 二次 audit + CLAUDE.md SD_09 段
