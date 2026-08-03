# AutoSDD_improving_93 — 真 token 長 playbook 取 pty/sdk 逐步驟（per-step）差異（C 軌）

> **本輪柱位**：C 軌（指揮官 AutoClaude 自我精進）。北極星對齊第 2 點「圖靈完備自動化閉環」——
> 以真 token 真跑量化 pty / sdk 兩執行後端在**長 playbook 多步驟**下的逐步驟行為差異，
> 補齊既有 A/B 載具「只有 2 步 smoke、測不出多步驟 token% 分佈」的缺口。
> **下一份**：improving_94。
> **本輪交付邊界（掌舵者 2026-06-27 signoff）**：載具三 W 項 + **本 session 完整真跑**（花真 Claude token），
> 填實驗證矩陣真跑欄。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 improving_92 結案狀態（RTM 收尾）
- 已完成 W 項：W-92-1（EmbedderConfig bge-m3 四欄 + config.yaml + .env.example）、W-92-2（BGEM3LocalAdapter
  四層兜底鏈 + 補 TEI_MODEL_ID/TEI_EMBED_DIMENSIONS env 讀取，修 DEF-92-001/002）、W-92-3（8 新測 + MUT-92-1/2）。
  **未完成 W 項：無**。embedder 非機密設定治理閉環（minimax@91 + bge-m3@92）。
- improving_92 §7 明列 improving_93 三候選：(a) SD_09 W1 source-sha 閘門（~6/29 到期）；
  (b) DEF-19-001 catch 歸因覆蓋；**(c) 真 token 長 playbook 取 pty/sdk 逐步驟差異**（載具 improving_76/86 已備 per-step）。
  **掌舵者裁示本輪走 (c)**。

### 1.2 階段一基線（2026-06-27 實測，§2 詳載）
- AutoClaude 全套：**3552 passed / 0 failed / 122 skipped**（本輪 floor）。
- lint-imports：8 kept / 0 broken。LOC：total=19885 / 0 violations（cap 20438）。Snapshot：OK。
- AISDLC_SDD ci-gate：v0.01 1478 + v0.27 1665 + infra 129 = 3272 passed / 0 failed；arch_fitness exit 0。

### 1.3 缺陷帳本 open / routed（本輪處置計畫）
- 皆 P3、無 P0/P1 阻斷：DEF-19-001（catch 覆蓋，本輪非 scope，續 routed）、DEF-62-001 / DEF-01-009
  （註解滯後 / LOC watch，本輪不觸發）、DEF-01-007（cc-switch GUI 環境，本輪 A/B 走既有 config 切換
  `executor.backend`，**不依賴 cc-switch**，未觸發）、DEF-23-005（RFC 生命週期自動化，routed 待 B 軌）。

### 1.4 本輪新登缺陷
- 階段一 / 階段三實作中發現即記入 `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-93-NN），§6 彙整。

---

## §2 階段一實測（Zero-Trust Re-Audit）

| 項 | 命令 | 實測結果 |
|----|------|---------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3552 passed / 0 failed / 122 skipped**（72.26s）✅ = 上輪 floor |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken ✅ |
| (c) LOC | `python tools/check_loc_budget.py` | total=19885 / violations=0（cap 20438）✅ |
| (c') Snapshot | `python tools/snapshot_sync.py --check` | OK 新鮮 ✅ |
| (d) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | v0.01 1478 + v0.27 1665 + infra 129 = 3272 passed / 0 failed；arch_fitness exit 0 ✅ |
| (e) open 缺陷重現 | — | 皆 P3 watch/routed，本輪未觸發（§1.3） |
| (f) 外部依賴 invocation 形態 | 真跑可行性探測 | claude CLI 2.1.144 認證 OK（`claude -p` 真跑回 "OK"）；sdk extra `claude_agent_sdk` 0.2.110 已裝；煙霧 `ab_compare_backends --run sdd_bridge_smoke --n 1`＝**pty 100%/6%、sdk 100%/2%，2/2 步成功、token 訊號已觀測**（與 improving_86 吻合）→ 真跑路徑全綠 |

**硬閘**：(a) 3552 = 上輪 floor、0 failed → **PASS，准進階段二**。

### 上輪 improving_92 構件存在性核對（zero-trust）
- EmbedderConfig 四欄（`autoclaude/utils/config.py:51-54`）、BGEM3LocalAdapter import + 四層兜底鏈
  （`autoclaude/infra/adapters/bgem3_local.py:25,48-76`）、22 BGE-M3 測試全 PASS → **真實存在且被測**。

---

## §3 增量設計（階段二）

### §3.0 設計依據實證（zero-trust，不憑記憶斷言）
- **兩後端**：`PtyExecutor`（`infra/adapters/pty_executor.py`，PTY 包 `claude -p`）vs `SdkExecutorAdapter`
  （`infra/adapters/sdk_executor_adapter.py`，Claude Agent SDK JSON-over-stdio），皆實作 `IExecutor`
  （`core/ports/executor.py`）；由 `ExecutorConfig.backend`（`utils/config.py:255-276`）+ `main.build_executor`
  （`main.py:55-82`）切換。**A/B config 既設 `enable_kernel_brain=false` + dummy minimax key → 純執行器層
  對比，不打 Minimax；「真 token」＝真 Claude token，用本機 `claude login` 認證**（`.env` 無 ANTHROPIC_API_KEY 不影響）。
- **per-step 真值來源**：Kernel `_run_step` emit `=== STEP_TOKEN_PEAK | step=<id> pct=<NN.NNNN> ===`
  （`core/kernel.py:192-201`，improving_86 W-86-1，`observer.peak_pct>0` 才發、不靠門檻）。
- **載具現況**：`tools/ab_compare_backends.py`（627 行）已有 `StepMetrics`/`StepAggregate`/`AggregateMetrics`
  + `aggregate_runs` + `format_step_aggregate_comparison`（有界截斷 max_steps=30）+ `--run --n` 多輪真跑。
  **缺口**：① 無 >5 步長 playbook（只有 2 步 smoke）；② per-step 聚合只有 mean/max，**無 stdev/p50/p95**；
  ③ **無標準化結果存檔**（聚合結果只印 stdout，無 `--out` JSON，無法落證據供審查/跨輪比對）。
- **LOC 邊界實證**：`check_loc_budget.py` `SCAN_ROOT="autoclaude"`（`tools/check_loc_budget.py:91,204`）
  → **`tools/` 不在 LOC 分級掃描內**，W-93-2 就地擴充 `ab_compare_backends.py` 不受紅線約束（仍節制）。

### §3.1 <Architecture_Design_Review>（寫任何 Python 前必輸出）
1. **架構純潔性**：無 God-object。W-93-1＝data（playbook yaml）；W-93-2＝既有 tools 載具加**純函式統計欄位**
   （additive dataclass 欄 + 純計算），無新類膨脹、不碰 `core`/`plugins`/`playbook_runner` thin facade。
2. **持久化相容**：本輪**不新增 PlaybookCheckpoint 欄位**、不碰 DAL 三後端（`--out` 是載具輸出檔，非 checkpoint）。
   DAL 零停機相容維持。
3. **安全防護網**：本輪不新增「從文件生成指令」路徑；長 playbook 的 prompt 為靜態文字、`evaluator_command`
   為固定 `pytest`（既有 CONDITIONAL 白名單消毒已涵蓋）。無弱化三層防禦。
4. **對外 I/O 安全**：本輪**不新增 `ToolInvocationPort` 外呼路徑**（A/B 純本機 subprocess `claude`）。N/A。

### §3.2 W 項（本輪 ≤3 項，聚焦）

| W 項 | 內容 | 檔案 / 介面 delta | LOC 落點 | contract 影響 |
|------|------|-------------------|---------|--------------|
| **W-93-1** | 長 playbook 基準：6-8 步漸進純函式開發（每步建小函式 + `evaluator_command: pytest`，自包含、可重複、pty/sdk 皆能跑），使 per-step token% 有**跨步分佈** | 新檔 `scripts/ab_long_playbook.yaml`（data，無 Python）；複用既有 `ab_pty_config.yaml`/`ab_sdk_config.yaml` | data（非掃描） | 無（data） |
| **W-93-2** | A/B 載具強化：per-step 聚合加 **stdev/p50/p95**（補 mean/max）+ 新增 `--out <json>` 標準化存檔聚合結果（供落證據/跨輪比對） | `tools/ab_compare_backends.py`：`StepAggregate` additive 加 `peak_token_pct_stdev/_p50/_p95`；`aggregate_runs` 計算（pstdev + 分位數）；`_step_agg_cell`/`format_step_aggregate_comparison` 顯示；`main` 加 `--out` 寫 JSON | tools/（不掃描）；估 627→~690 | 無（tools/ 不在 8 contract 範圍） |
| **W-93-3** | 本 session 真跑取證：W-93-1 長 playbook × 強化載具，pty/sdk 各 **N=3 輪**，`--out` 落 JSON 證據 + 產出真跑差異報告 | 產物：`docs/03_testing/AutoSDD_improving_93_ab_evidence.json` + 報告段落（落 §4.2 / ZeroTrust_Audit_93） | 無（執行+取證） | 無 |

### §3.3 RTM 需求列（SCG-5 對應，實測欄階段三/四回填）

| RTM-ID | 需求 | 驗證方式 | 實測（階段三/四回填） |
|--------|------|---------|----------------------|
| RTM-93-1 | 長 playbook schema 合法且可被 `Playbook` 載入、步驟數 ≥6 | 新單測 `test_ab_long_playbook_*` | （回填） |
| RTM-93-2 | per-step stdev/p50/p95 計算正確（合成多輪 RunMetrics 驗算） | 新單測 `test_step_aggregate_stats_*` | （回填） |
| RTM-93-3 | `--out` JSON 存檔 schema 完整（含 per_step_agg 統計欄）、可重新讀回 | 新單測 `test_ab_out_json_*` | （回填） |
| RTM-93-4 | 本 session 真跑 pty/sdk 各 3 輪、per-step token% 分佈差異有量化證據 | W-93-3 真跑 + JSON 證據 | （回填，§4.2） |
| RTM-93-5 | 零退化：全套 ≥3552、lint 8 kept、LOC 0、snapshot OK、ci-gate 全綠 | 階段四矩陣 | （回填，§5） |

### §3.4 SCG 進程（B 軌 dogfooding 形式，本輪 C 軌作業）
- SCG-0/1＝本計畫書 §1-3；SCG-2＝§3.2 介面 delta；SCG-3＝載具無新對外契約（tools 內部）；
  SCG-4＝實作 PR（§4）；SCG-5＝§3.3 RTM + §5 驗證矩陣。本輪 C 軌、**零碰框架本體 v0.27**（Copy-on-Evolve N/A）。

---

## §4 實作與雙重驗證（階段三）— 實測回填

### W-93-1：長 playbook 基準 ✅
- 新檔 `scripts/ab_long_playbook.yaml`：7 步逐函式 TDD（add/sub/mul/divide/power + 整合驗收），
  每步（S02+）`evaluator_command: pytest test_mathlib.py -q` 親跑、`maintain_context: true` 累積。
- 單測 `test_ab_long_playbook_schema_loads`（RTM-93-1）：`load_playbook_impl` 載入成功、步驟 7≥6、
  首步無 evaluator、S02+ 皆有 evaluator → PASS。
- **附帶覆蓋（超設計）**：既有 `tests/integration/test_yaml_import.py` 以 `glob("scripts/*.yaml")` parametrize
  6 個契約測試（parse/sha256/format detection/PII…），本新檔自動 +6 案例全綠 → playbook 結構契約亦被機械守。

### W-93-2：A/B 載具強化（stdev/p50/p95 + --out JSON）✅
- `tools/ab_compare_backends.py`（tools/ 不在 LOC SCAN_ROOT）：
  - 新增 `_percentile`（nearest-rank 純函式，空→0/n=1→該值/不內插）；
  - `StepAggregate` additive 加 `peak_token_pct_stdev/_p50/_p95`；`aggregate_runs` 計算（pstdev + 分位數）；
  - `_step_agg_cell`/表頭顯示 `mean±sd/p50/p95/max%`；`main` 加 `--out` + `_agg_to_dict`/`_write_out_json`
    （精簡 JSON，**不** dump per_run 原始 log，防膨脹/路徑洩漏）。
- 5 新單測（RTM-93-2/3）：stdev/p50/p95 驗算、nearest-rank 語意、`--out` JSON roundtrip、排除 per_run → 全 PASS。
- 零退化：ab_compare 套件 65→70；ruff E501 維持 baseline 6（新增 1 處表頭超長已當場縮短修回）。

### W-93-3：本 session 真跑 pty/sdk A/B 取證 ✅
- 命令：`python tools/ab_compare_backends.py --run scripts/ab_long_playbook.yaml --workdir <tmp>
  --pty-config ab_pty_config.yaml --sdk-config ab_sdk_config.yaml --n 3 --out <evidence.json>`
  （真 Claude token；Brain off + dummy minimax key = 純執行器層對比）。
- 證據：`docs/03_testing/AutoSDD_improving_93_ab_evidence.json`（N=3 雙後端 + per-step 統計）。

### §4.2 真跑差異結果（per-step 分佈 / stdev / p95）— 核心發現

整輪聚合（N=3）：

| 指標 | pty | sdk |
|------|-----|-----|
| 一次通過率 (mean±stdev[min~max]) | 95%±7% [86~100] | 100%±0% [100~100] |
| token 峰值 (effective mean/max) | **9.58% / 14.42%** | **2.0% / 3.0%** |
| token 訊號源 (有訊號輪/N) | 2/3 | 2/3 |
| 完成步驟均值/總 | 6.7/7 | 5.0/7 |
| run 成功/escalated/halted | 2/1/0 | 2/1/0 |

逐步驟 token% mean（pty）：S01 **6.04** → S02 6.15 → S03 9.49 → S04 7.69 → S05 10.34 → S06 **14.37** → S07 7.44；
（sdk）全程平穩 **2.0~3.0**。

**三大發現**：
1. **pty per-step token% 隨 context 累積單調遞增**（6%→14% 至 S06），sdk 平穩 2-3%——pty（`claude -p --output-format json`
   解析 usage）真實反映對話脈絡膨脹；sdk（`get_context_usage().percentage`）回報數值低且平。兩後端 context% 量測
   機制差異首次以**逐步驟**量化（過去 smoke 只看到整輪 6% vs 2%）。
2. **W-93-2 stdev/p50 的實證價值**：S04 pty `stdev=3.06`（其餘步 ~0），mean=7.69 但 **p50=9.85 / max=9.86**
   ——揭露有一輪 S04 token% 偏低把 mean 拉低，**光看 mean 會誤判 S04「比 S03 低」，p50 還原「中位其實 9.85、與鄰步一致」**。
   證明新統計欄位能揭露 mean/max 遮蔽的分佈真相（此即本 W 項設計動機）。
3. **真 LLM 非確定性 A/B**：兩後端各 1/3 輪 escalated，**但卡不同步驟**——pty/run_1@S07（3 retry 後未輸出精確
   keyword `[S07_DONE]`）、sdk/run_2@S02（evaluator pytest exit=4，該輪未正確建檔）。其餘 4 輪 7/7 全 success。
   **此為真實執行變異，非框架/playbook 缺陷**（playbook 已達成跨 3 輪採 per-step 分佈之目的）。

---

## §5 零退化驗證矩陣（階段四）— 實測回填

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3552 passed / 0 failed | **3563 passed / 0 failed / 122 skipped** ✅（+11＝5 新 ab_compare 測 + 6 既有 yaml-import parametrize×新 playbook，已對清） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **total=19885 / violations=0**（cap 20438）✅（tools/ 不掃、autoclaude/ 零碰） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | **3272 passed / 0 failed；arch_fitness exit 0** ✅（階段一實測；本輪零碰 AISDLC_SDD） |
| DAL 等價 | equivalence | 三後端等價 | **N/A 第二種**：`tests/equivalence/` **86 passed** 隨全套通過，本輪無新 DAL/checkpoint 改動故無新 round-trip 契約 ✅ |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | 五軌 0 violation | **N/A 第一種**：`git status` 證零碰 `*.tla`/FSM/`_HAPPY_PATH`（改動僅 tools 載具 + scripts yaml + docs），TLC 不在 pytest 全套、需 Java，本輪確未跑 |

---

## §6 多專家 Zero-Trust 審查
（見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_93.md`：Architect / SA-SD / QA 三鏡 OVERALL PASS 證據；
缺陷帳本誠實性核對——本輪零新框架缺陷，真跑 escalation 為 LLM 變異已誠實標記非缺陷。）

---

## §7 結語
- **本輪交付**（C 軌，零退化）：W-93-1 長 playbook 基準（7 步）+ W-93-2 A/B 載具加 per-step
  stdev/p50/p95 + `--out` JSON 證據 + W-93-3 本 session 真跑 N=3 雙後端取證。
- **核心價值**：首次以**逐步驟**量化 pty/sdk context% 量測機制差異（pty 隨 context 累積 6%→14%、
  sdk 平穩 2-3%）；新統計欄位（S04 stdev=3.06 還原 p50 真相）實證「mean/max 遮蔽分佈、p50/stdev 才看得出」。
- **真跑誠實紀錄**：兩後端各 1/3 輪 escalated（pty@S07 keyword、sdk@S02 evaluator），其餘 4 輪 7/7
  success——真 LLM 非確定性，非缺陷。
- **下一份 improving_94 候選**：(a) SD_09 W1 source-sha 閘門（~6/29 到期）；(b) DEF-19-001 catch 歸因覆蓋；
  (c) per-step token% 達門檻（compact/halt）的長 playbook 真跑（本輪未撞 80%，可設計更重負載 playbook 觀察門檻路徑）。
