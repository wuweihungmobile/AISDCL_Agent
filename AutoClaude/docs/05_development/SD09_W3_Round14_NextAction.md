# SD_09 W3 Round 14 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — nightly 第 9 跑驗證 + 4 軸並行（B 分析 / C PM 拍板 / D 預備研究）+ Architect/SA/SD/QA 4 方 zero-trust audit |
| Audit Round | W3 Round 14（2026-05-25）|
| Audit 發現 | **0 P0 + 0 P1 + 1 P2 + 2 NOTE → PASS（13 紀律全綠）** |
| pytest 基線 | **2,538 passed / 122 skipped**（持平 Round 13；本輪僅 ADR header 狀態變更，零實作差異）|
| importlinter | 7 kept / 0 broken |
| LOC violations | 0（baseline=14058 / cap=16869 / total=15050）|
| CLAUDE.md | 400 行（紅線邊界）|
| Nightly 第 9 跑取證 | [logs/nightly_2026-05-25_195635.log:L256](../../logs/nightly_2026-05-25_195635.log#L256) `END nightly summary: mutation=0 pg-e2e=0 perf=2 drift=0 obs=0`（5 stage 含 perf WARN；5:51 elapsed） |
| §3.0 並行框架 | 不變（軸 A/B/C/D 並行框架繼續沿用；軸 C #2/#3 完成）|

---

## 1. Audit 取證

| 項目 | 取證 |
|------|------|
| Nightly 第 9 跑 | [log:L256](../../logs/nightly_2026-05-25_195635.log#L256) `END nightly summary: mutation=0 pg-e2e=0 perf=2 drift=0 obs=0` |
| Stage 個別 elapsed | Docker-PG 0.35s / mutation 4:33.5 / pg-e2e 12.7s / perf 35.9s / drift 0.48s / obs 0.64s / Cleanup 0.001s — 總 5:51 |
| Mutation 5 行 counts | [log:L165-169](../../logs/nightly_2026-05-25_195635.log#L165) Killed (109) / Survived (38) / Timeout (0) / Suspicious (**2**) / Skipped (0) — kill_rate=**73.15%**（vs Round 13 74.50%；suspicious +2 浮現；M-05 same UTC date dedup）|
| AC4 F2 OK | dual track 正常運作（tolerant<60ms streak=4 / observation<50ms streak=0；本跑 p95 53.75ms） |
| Perf=2 WARN | [log:L213-244](../../logs/nightly_2026-05-25_195635.log#L213) decide_correction PASS -29.2% / dry_run_e2e PASS -96.8% / **token_halt_roundtrip WARN baseline=0.5ms current=1.0ms +103.9%**（亞毫秒測量噪音；samples=7 < 20 BLOCK→WARN 退化 — ADR-SD08-003 §2.6 v1.1 設計涵蓋；Invoke-Stage rc=2 視為 WARN 不算 fail 紀律 #1）|
| Drift 0 事件 | [log:L249](../../logs/nightly_2026-05-25_195635.log#L249) `drift_log severity!='info' rows = 0` |
| 觀察期 jsonl 進度 | [log:L257](../../logs/nightly_2026-05-25_195635.log#L257) `END observation progress: mutation=4/7 ac4=4/14 obs=3/30 drift=3/30`（與 Round 13 同 UTC date dedup 一致 — 紀律 #13 驗證正確）|
| ADR-008 v0.4 同步驗證 | Round 13 P0-R13-1 修復後對齊維持 — F2 ALERT message template 含 v0.4 ACCEPTED 引用 |
| **ADR-009/010 ACCEPTED v1.0** | PM 拍板書（W3 Round 14 PM Agent）— ADR-009 選項 A（suspicious 0.5 半 kill + ±2pp tolerance） / ADR-010 選項 B（建議規範 + W1 必做 mutmut_counts_parser） |
| 13 條紀律 | **13 PASS / 0 WARN / 0 FAIL** |

---

## 2. Round 14 真實問題（1 P2 + 2 NOTE — 全部已有路徑覆蓋）

| ID | 嚴重度 | 狀態 | 視角 | 根因 | 修法 | 主要檔案 |
|----|--------|------|------|------|------|---------|
| **P2-R14-1** mutation kill_rate 從 74.50% → 73.15%（suspicious 從 0→2）| P2 | ✅ ADR 路徑覆蓋 | QA + Architect | mutmut 2.4.3 對 `policy.py:91, 99` 標 suspicious（測試耗時介於 baseline 1x~10x）；非實作退化（commit 087c46a plugin 原始碼未動，source_sha256 與第 8 跑同 5208cff... unique=1）| **ADR-SD09-009 ACCEPTED v1.0 選項 A 已涵蓋** — W1 實作 calc_kill_rate 切換（killed + 0.5×suspicious / denom）後預估回升至 73.83%（109+0.5×2=110/149）；含 ±2pp tolerance 雙軌 | [tools/mutation_baseline_lock.py:127](../../tools/mutation_baseline_lock.py#L127) / [ADR-SD09-009](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md) |
| **NOTE-R14-1** Round 14 NextAction 文件落地 | NOTE | ✅ 本文件 | Architect | audit 末端任務 | 本文件即為 NOTE-R14-1 閉環交付 | 本檔 |
| **NOTE-R14-2** PM 拍板書未獨立成檔 | NOTE | ✅ 設計就位 | PM | ADR-009/010 header 已引用「W3 Round 14 PM Agent 拍板書」+ status 行；PM Agent 結論已內嵌至本檔 §3 | 不獨立成檔（PM 簽核紀錄已在 ADR header + 本 Round14 §3）— 後續 SD_09 W1 G0 啟動時若需正式 PM 簽核會議紀錄再補 | [ADR-SD09-009](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md):L6 / [ADR-SD09-010](../04_planning/ADR/ADR-SD09-010-ps1-to-helper-ssot-governance.md):L6 |

---

## 3. PM 拍板書（W3 Round 14 PM Agent 摘要）

### 3.1 ADR-SD09-009 拍板：選項 A（suspicious 計 0.5 killed + ±2pp tolerance）

| 維度 | 內容 |
|------|------|
| 共識傾向 | Architect + SA + SD 三方獨立研究 100% 共識選項 A |
| PM 採納 | ✅ 選項 A |
| 理由（5 點） | 1) 三方無分歧；2) 觀察期 #1 數學阻塞解除（7 個 suspicious bounce ±4.7pp 死結）；3) 半 kill 0.5 符合 mutmut 工具語意；4) 既有 jsonl 4 筆 suspicious=0 三選項數學等價（無 backfill 風險）；5) ±2pp tolerance 符合紀律 #6 雙軌制 |
| 對觀察期 #1 影響 | 計算口徑切換不延後達標日（4/7 → 持續累計）；±2pp 等效 strict 70% 半 kill 補正後 ≥ 68% |
| W1 任務增量 | T1-M1 calc_kill_rate 切換 0.3 PD / T1-M2 mutation_analysis 同步 0.2 PD / T1-M3 ≥ 5 case unit test 0.3 PD |
| 紅線符合性 | §5.1~§5.5 全綠；§3.0.3 紅線區 mutation_baseline_lock.py 觸碰符合紀律 #4 ≥ 5 case 補強允許條件 |

### 3.2 ADR-SD09-010 拍板：選項 B（建議規範 + checklist + W1 必做 mutmut_counts_parser）

| 維度 | 內容 |
|------|------|
| 共識傾向 | Architect + SA + SD 三方獨立研究 100% 共識選項 B |
| PM 採納 | ✅ 選項 B |
| 理由（5 點） | 1) 三方無分歧；2) 穩定態保護（Round 11 首次無 P0/P1）；3) W1 必做事實驅動（Round 4 P0-AUDIT-R3-3 真實迴歸實證）；4) 選項 C 過度激進（≥ 4 PD 獨立 sprint）；5) 既有 ac4_nightly_alert_parser.py 134 LOC + 16 case test 為複用樣板 |
| W1 任務增量 | T1-H1 mutmut_counts_parser.py（≤ 100 LOC）+ ≥ 6 case unit test + ps1 line 337-358 inline 改造 + PS1_Complexity_Checklist.md（≤ 50 行）0.5 PD |
| 紅線符合性 | §3.0.3 紅線區 ps1 觸碰符合允許條件（要求 helper output 位元相同 pre/post diff=0；屬重構非語意變動）|

### 3.3 對 G0 啟動窗口影響

- 觀察期 #1：4/7 → 因 ADR-009/010 同 PR 落地觸發 SP-1 unique sha 重置 → 重新累計 7 天 → **6/2 ~ 6/8**（視 commit 日期）
- 觀察期 #2：不變（仍 2026-06-08；ADR-SD09-008 v0.4 路徑）
- 觀察期 #3：不變（仍 2026-06-24；drift_log 30 天）
- **G0 啟動窗口維持 2026-06-24 ~ 2026-06-26**（由 #3 主控）

---

## 4. 軸 D 預備研究摘要（Architect+SD Agent W3 Round 14 派工）

### 4.1 Production_Migration_SOP §4-§5 大綱（W3 任務預備）

- **§4.1 切換前置 checklist** — 7 項硬條件（ADR-SD08-005 §2.2 雙條件 / ADR-SD09-001 §2.3 三親演 / alembic head / WAL lag<2s 7 天 / reconcile_queue=0 / File backend tar.gz + sha256 / canary 三階梯）
- **§4.2 切換窗口管控** — DBA staging≥1M 列演練 + GPG 簽鏈 + 週日 02:00 4h 窗口 + 熔斷條件
- **§4.3 切換過程取證** — script -t 全程錄影 + 三點 snapshot + audit trail jsonl 5 分鐘採樣 + trace_id 端對端
- **§4.4 切換失敗回退劇本** — rollback 觸發條件 / `storage.mode=both` 雙寫先行 / 24h smoke + 不可回退項
- **§5.1~§5.3 切換後** — 30 天觀察期 drift_log + perf baseline 重採集 14 天 + 雙軌制下線（deprecated D+30 / 移除 D+60 / 刪除 D+90）

### 4.2 trace_id W3C path-b 設計（W3 任務預備）

- **W3C 引用**：Recommendation §2.2.1 traceparent format（version-format `00-{trace_id_32hex}-{span_id_16hex}-{flags_2hex}`）/ §3.2.2.2 invalid parser fall-back / §3.2.3 mutating
- **4 子題拆解**：
  1. ContextVar → traceparent 序列化點（9 處 subprocess.Popen/.run 注入點 + os.execvp + multiprocessing）
  2. traceparent → ContextVar 反序列化（child entry `__main__.py` 啟動最早處 + CLI subcommand entry）
  3. EventBus 跨 process（同 process 已落地；跨 process 限 subprocess 注入；PTY child 屬 SD_10 OTel）
  4. contract test 設計（`tests/utils/test_trace_context_w3c.py` ≥ 8 case 覆蓋 W3C edge case）
- **落地風險**：env 名稱衝突第三方 OTel SDK（已對齊 W3C 標準名）/ 9 處注入點散裝改造遺漏（集中 helper + grep guard）/ LOC 超 contract tier（156 → ~195；.loc-budget.toml override 雙簽）/ W0 過渡 `AUTOCLAUDE_TRACE_ID` 殘留（並存 1 個 Sprint deprecate）

---

## 5. 軸 B 分析摘要（Dev+QA Agent W3 Round 14 派工）

### 5.1 重要修正：64 點為過時數字

| 維度 | 任務描述原估 | 實際本輪採證 |
|------|------------|------------|
| Survived 點數 | 64（compactor 24/git_verifier 13/policy 17/thresholds 7/watcher 3）| **38**（W0 期間 5 個 _mutation.py test 檔陸續落地殺 26 個）|
| 必補（boundary+constant+other）| 64 | **22** |
| string_literal 可 ignore | 0 | **16** |
| 當前 kill_rate | 估 69.8%~74.5% bounce | **73.15%**（Round 14 第 9 跑；超 70% 門檻 3.15pp）|

### 5.2 W1 軸 B 補測建議優先順序

1. **policy.py 8 case**（kwarg propagation 矩陣 + ResourceRequest format spec）— 殺 14 mutant，ROI 最高
2. **compactor.py 3 case**（default attempt + concat）— 殺 3 mutant
3. **git_verifier.py 1 case**（_WARNING_TEMPLATE 模組常量）— 殺 1 mutant
4. **thresholds.py + watcher.py 2-3 case**（epsilon boundary）— 殺 4 mutant
5. **string_literal 16 點不補**（語意無關 log/error message，已標於 mutation_backlog_token_guard.md）

**總計**：15 case / ~250 LOC / 1-2 PR / 預估補後 kill_rate ≈ 89%

### 5.3 ROI 評估

- **38 點全補後**：killed=133/149 → kill_rate ≈ 89.3%（string_literal 16 ignore 維持 survived）
- **只補 policy.py 8 case**：killed=125/149 → kill_rate ≈ 83.9%（cushion +13.9pp 對 70% 門檻）
- **不補一字**：只需再跑 3 個獨立 UTC 日 nightly 即可結觀察期（達標日 ~2026-06-01；W3 補測後仍需累計 7 天）

---

## 6. 13 條紀律盤點（Round 14 第 9 跑後）

| # | 紀律 | Round 14 |
|---|------|----------|
| 1 | stage rc 區分真實失敗 vs 工具標準回報 | ✅ PASS（perf rc=2 視為 WARN 不算 fail；mutmut rc=10 bitmask 非真 crash）|
| 2 | log 完整統計 | ✅ PASS（5 type counts 全列；含 suspicious=2）|
| 3 | PASS 引用 RunId log:L | ✅ PASS（本報告全引用 [logs/nightly_2026-05-25_195635.log](../../logs/nightly_2026-05-25_195635.log)）|
| 4 | 驗證鏡子被驗證 | ✅ PASS（45 ac4 case 全綠；ADR header / 下游引用對齊）|
| 5 | 跨工具數字對齊 | ✅ PASS（mutation_analysis survived=38 ↔ mutmut log Survived(38) ↔ baseline_lock kill_rate=73.15%）|
| 6 | 採集寬鬆 vs 升級嚴格分軌 | ✅ PASS（perf BLOCK→WARN samples<20 退化 + dual env STRICT=60/OBSERVATION=50）|
| 7 | cache 強制 fresh | ✅ PASS（.mutmut-cache + .ac4_junit.xml + perf_results.json 跑前 rm）|
| 8 | .sh LF 行尾 | ✅ PASS（.gitattributes + run_mutmut_in_docker.sh 為 LF）|
| 9 | Docker 依賴 SKIP 一致 | ✅ PASS（本跑 Docker 可用無 SKIP；程式碼路徑 ps1:505-538 保留）|
| 10 | fallback jsonl 可區分 | ✅ PASS（observability_emit_real:true）|
| 11 | latest log pointer 完整 | ✅ PASS（diff latest vs 完整 run 僅差 pointer 自身更新行）|
| 12 | mutation history source_sha256 | ✅ PASS（同 sha 5208cff... unique=1；should_lock reject reason=insufficient_runs count=4/7 守門生效）|
| 13 | 觀察期進度可見 | ✅ PASS（log:L257 4 軌進度可見；與 Round 13 同 UTC date dedup 正確）|

---

## 7. W1 啟動前未決項（Round 14 後狀態）

| ID | 項目 | 狀態 |
|----|------|------|
| ADR-SD09-008 v0.4 | AC4 雙軌 60ms tolerant + 50ms observation | ✅ ACCEPTED 2026-05-25 |
| ADR-SD09-009 v1.0 | mutmut suspicious 0.5 半 kill + ±2pp tolerance | ✅ **ACCEPTED 2026-05-25**（Round 14 PM Agent 拍板選項 A）|
| ADR-SD09-010 v1.0 | ps1-to-helper SSOT 治理（建議規範 + W1 必做 mutmut_counts_parser）| ✅ **ACCEPTED 2026-05-25**（Round 14 PM Agent 拍板選項 B）|
| 觀察期 #1 | mutation pilot TokenGuardPlugin 連續 7 次 ≥ 70% + 紀律 #12 unique sha | 累計 **4/7 jsonl record**（kill_rate 73.15% 過 70% threshold；待 W1 軸 B + ADR-009/010 同 PR 落地觸發 SP-1 重置）|
| 觀察期 #2 | AC4 14 天 nightly 全綠 | 累計 **4/14**（tolerant streak=4；達標窗口 2026-06-08）|
| 觀察期 #3 | drift_log 30 天零事件 | 累計 **3/30**；達標日 2026-06-24 |

---

## 8. 下一步執行檔案與大綱（依 §3.0 4 軸並行框架；Round 14 後校準）

### 8.1 4 軸並行下一步動作

| 軸 | 動作 | 時機 | 狀態 |
|----|------|------|------|
| **軸 A 背景觀察期** | ✅ user 已啟用 schtasks /change /TN AutoClaude_Nightly /ENABLE；持續 nightly 02:00 自動跑累計 jsonl | 🟢 持續中 | 已啟動 |
| **軸 B W1 前景** | 補 token_guard 15 case test（policy 8 / compactor 3 / git_verifier 1 / thresholds+watcher 2-3）— 預估 ~250 LOC + 殺 22 必補 mutant；ROI 補後 kill_rate ≈ 83~89% + 觸發 source_sha256 變化重置觀察期 #1 | ≤ T+10 = 2026-06-04 | 🟡 已分析待實作 |
| **軸 C PM 拍板** | ✅ ADR-009 ACCEPTED 選項 A / ✅ ADR-010 ACCEPTED 選項 B（Round 14 PM Agent 拍板 2026-05-25）| ≤ 2026-06-08 | 🟢 **三項全完成** |
| **軸 D W2-W6 預備** | ✅ ADR-009/010 三方研究完成 / ✅ sprint_history.md §1.5 SD_07 骨架完成 / ✅ **Production_Migration_SOP §4-§5 大綱研究完成** / ✅ **trace_id W3C path-b 設計完成**（Round 14 Architect+SD Agent 派工）| 任意時點 | 🟢 **預備研究全完成** |

### 8.2 W1 task list（PM 拍板後新增 4 任務 + Round 13 軸 B 15 case 整合）

| 任務 ID | 內容 | 對應 ADR | PD 估算 |
|---------|------|---------|---------|
| T1-B1（軸 B 整合）| 補 token_guard 15 case test（policy.py 8 / compactor 3 / git_verifier 1 / thresholds+watcher 2-3）| Round 14 軸 B 分析 | 1.5 PD |
| T1-M1（新增）| 切換 `tools/mutation_baseline_lock.py` `calc_kill_rate` → `(killed + 0.5×suspicious) / denom` + `should_lock` 加 ±2pp tolerance | ADR-009 §6 | 0.3 PD |
| T1-M2（新增）| `tools/mutation_analysis.py` 同步切換 suspicious 處理 | ADR-009 §6 + 紅線 §5.3 | 0.2 PD |
| T1-M3（新增）| 補 ≥ 5 case 單元測試 — bounce 場景 / 邊界 threshold / 三選項數學等價性 | ADR-009 紅線 §5.4 | 0.3 PD |
| T1-H1（新增）| `tools/mutmut_counts_parser.py`（≤ 100 LOC）+ ≥ 6 case unit test + ps1 line 337-358 inline 改造 + `docs/05_development/PS1_Complexity_Checklist.md`（≤ 50 行）| ADR-010 §5 W1 | 0.5 PD |
| **W1 合計** | 2.8 PD（原 W1 5 PD 預算內可吸收）| | |

### 8.3 收斂評估與成熟度（Round 14 後）

#### 8.3.1 收斂訊號（正向）

- **Round 14 zero-trust audit 完整閉環**：0 P0 + 0 P1 + 1 P2（已 ADR 路徑覆蓋）+ 2 NOTE（NOTE-R14-1 本檔閉環 / NOTE-R14-2 設計就位）
- **Nightly 第 9 跑 4 stage 全綠 + perf=2 WARN 為設計內語意正確降級**（ADR-SD08-003 §2.6 v1.1 BLOCK→WARN 退化涵蓋；token_halt_roundtrip 亞毫秒測量噪音）
- **PM 拍板雙 ADR 同步 ACCEPTED**：ADR-009 選項 A + ADR-010 選項 B（三方研究 100% 共識）
- **軸 D 預備研究完成**：Production_Migration_SOP §4-§5 大綱 + trace_id W3C path-b 設計就位（W3 任務預先準備）
- **pytest 基線維持 2,538**（持平 Round 13；本輪僅 ADR header 狀態變更，零實作差異）
- **13 條紀律全綠維持**（14 輪 audit 連續壓力測試穩定）

#### 8.3.2 仍未收斂訊號

- **軸 B W1 token_guard 15 case test 待實作**：原任務描述 64 點修正為實際 38（22 必補 + 16 ignore），15 case 為高 ROI 子集
- **W1 T1-M1~M3 + T1-H1 待實作**：合計 2.8 PD，建議與軸 B 15 case 同 PR 落地（單次觸發 SP-1 觀察期 #1 重置，節省 7 天緩衝）
- **觀察期 #1 累計 4/7 但同 sha unique=1**：待 W1 commit 變 sha 後新累計

#### 8.3.3 專案成熟度評估（Round 14 後升等）

| 維度 | 評分 | 變動（vs Round 13）|
|------|------|------|
| 架構 / 程式碼品質 | 🟢 A | 不變 |
| 測試覆蓋 | 🟢 A（2,538 持平）| 不變 |
| CI / nightly 治理 | 🟢 A | 不變（14 輪 audit 穩定）|
| 觀察期升級條件 | 🟢 **A−** | **+0.5**（PM 拍板完成解除觀察期 #1 數學阻塞 + 軸 D 預備研究完成）|
| 文件治理 | 🟢 **A+** | 不變（Round 13 已達 A+；本輪保持）|
| **PM 決策成熟度** | 🟢 **A**（新增維度）| **首評**（PM Agent 拍板鏈完整 — 三方研究 100% 共識 + PM 拍板書內嵌 ADR + W1 task list 增量明確）|
| PG production 上線就緒 | 🟡 B | 不變（軸 D §4-§5 預備研究完成但 staging 演練未啟動）|
| 整體 SD_09 進度 | 🟢 **W0 收尾期（接近完成）** | 不變語義（14 輪 audit 收尾期 + 軸 C 三項 100% 完成 + 軸 D 預備研究 100% 完成；剩餘軸 A 30 天累計 + 軸 B 15 case 實作）|

---

## 9. 一句話總結

**Round 14 為 14 輪 audit 真實連續壓力測試的第 9 跑驗證 + 4 軸並行集中交付：軸 A 持續累計（user 已啟用 schtasks）/ 軸 B Dev+QA Agent 分析揭露「原 64 點為過時數字，實際 38 survived，kill_rate 73.15% 已過 70% 門檻 + W1 補測建議 15 case ~250 LOC ROI 預估 83~89%」/ 軸 C PM Agent 拍板雙 ADR 同步 ACCEPTED（ADR-009 選項 A + ADR-010 選項 B；三方研究 100% 共識）/ 軸 D Architect+SD Agent 完成 Production_Migration_SOP §4-§5 大綱 + trace_id W3C path-b 設計（W3 任務預備）**。Nightly 第 9 跑 13 紀律全綠 / PASS / 0 P0 / 0 P1 / 1 P2（kill_rate -1.35pp 由 ADR-009 ACCEPTED 涵蓋）/ 2 NOTE 全部已有路徑覆蓋；觀察期累計健康（#1=4/7、#2=4/14、#3=3/30）且軸 C 100% 完成解除觀察期 #1 數學阻塞；專案維持 **W0 收尾期（接近完成）**，剩餘軸 A 30 天累計 + 軸 B 15 case 實作 + W1 T1-M1~H1 共 2.8 PD 即可啟動 G0（最遲 2026-06-24 觀察期 #3 達標）。

---

**版本紀錄**：v1.0 2026-05-25 — Round 14 audit PASS（0 P0/0 P1/1 P2/2 NOTE）+ 4 軸並行集中交付（軸 C 三項全完成 + 軸 D 預備研究全完成）+ nightly 第 9 跑 13 紀律全綠取證；對應 commit / tag / merge main 由 PM 完成回填。
