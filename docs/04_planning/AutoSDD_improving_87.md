# AutoSDD_improving_87 — Brain 指揮 Claude Code self-correction 閉環「端到端真跑」首證（C 軌 × A 軌）

> **本輪柱位**：**C 軌（指揮官 AutoClaude 自身能力：self-correction loop 真跑接線）× A 軌（端到端真跑驗證）**。對齊北極星第 1 點——AutoClaude＝以狀態機管理執行流程／重試／**錯誤升級**的引擎；self-correction（Executor 失敗 → Brain 介入 → 修正 prompt 餵回 → 重試）是「圖靈完備自動化閉環」的關鍵環節。
> **下一份**：improving_88。
> **框架版**：本輪零碰 AISLDC_SDD 框架本體（生產碼／載具全在 AutoClaude）→ 免 Copy-on-Evolve、維持 v0.27。`L_合體=min(A,B,C)=L5` 不變（同源能力加固＋首次真跑取證，非成熟度推進）。
> **掌舵者裁示**：2026-06-27 明確排入（「Minimax 指揮 Claude Code……機制能否正常 work 的重要一環」），選「兩條都排（先 mock 驗機制、再真 Minimax 驗品質）」；並告知 `MINIMAX_API_KEY` 已設於 `AutoClaude/.env` → W-87-2 本輪亦可真跑。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 improving_86 結案狀態（RTM 收尾）
- improving_86＝A 軌 × C 軌 per-step token% 可觀測性 emit + 真跑填值（commit 4d6337c 前序，improving_86 commit a70c6cd）。
- 已完成 W 項：W-86-1（生產 Kernel `STEP_TOKEN_PEAK` emit）/ W-86-2（載具解析 + per-step 多輪聚合）/ W-86-3（N=2 pty/sdk A/B 真跑）。
- 未完成 W 項：無。上輪審計三鏡全 PASS。
- 上輪遺留候選（improving_86 §8）：(a) SD_09 W1 觀察期 source-sha 閘門（~6/29 成熟，今 6/27 未到 → 本輪不取）；(b) 更長 playbook 取多步驟 per-step token%（本輪不取）；(c) v2.0 不相容格式漂移閘 production 攔阻（本輪不取）。**本輪取掌舵者新指定標的：self-correction 閉環真跑（backlog improving_87 已備藍圖）。**

### 1.2 缺陷帳本 open / routed（本輪處置計畫）
| 缺陷 | 狀態 | 本輪處置 |
|------|------|---------|
| DEF-01-007（cc-switch GUI 環境缺裝 P3） | open | 不涉多後端切換 → 維持 |
| DEF-01-009（sdd_governance_plugin LOC watch P3） | open watch | 零碰 → 維持 |
| DEF-23-005（RFC 生命週期 P3） | open | 不涉 → 維持 |
| DEF-62-001（auto_recovery 註解滯後 P3） | open | 不涉 → 維持 |
| DEF-17-001（遙測） / DEF-19-001（catch 漸進） | routed | 不涉 → 維持 |
| DEF-35-001（goal_synthesis mutmut P2，繫 SD_09 W1） | routed | 本輪非 SD_09 W1 → 維持 |

### 1.3 上輪遺留候選處置
- 見 1.1。本輪專注 self-correction 閉環真跑（backlog `AutoSDD_improving_87_backlog.md`）。

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-27）

> 派 Explore agent 主樹親跑（非採信文件宣稱），硬閘 PASS 才進階段二。

| 項目 | 命令 | 實測 | 狀態 |
|------|------|------|------|
| (a) AutoClaude 全套 pytest | `python -m pytest tests/ -q`（Bash） | **3501 passed / 0 failed / 122 skipped**（總收集 3623；floor 3488 +13） | ✅ 硬閘 PASS |
| (b) lint-imports | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| (c) LOC budget | `python tools/check_loc_budget.py` | violations=0（total 19783 / cap 20438） | ✅ |
| (d) snapshot | `python tools/snapshot_sync.py --check` | OK（FRESH） | ✅ |
| (e) AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 / v0.27:1665 / scripts:129） | ✅ |
| (f) git 工作樹 | `git status --short` | 乾淨 | ✅ |
| (g) 上輪構件 | grep/開檔 | kernel.py:199 STEP_TOKEN_PEAK / ab_compare `_RE_STEP_TOKEN_PEAK` / test_kernel_step_token_peak.py 全存在 | ✅ 無虛報 |
| (h) 本輪資產 | ls/pytest | mock_brain_server.py 存在、test_mock_brain_server.py **6 passed**；correction_loop_smoke.yaml **不存在**（待建）；4 個 ab_config 皆 `enable_kernel_brain:false` | ✅ |
| (i) .env Minimax 形態 | grep（不印 key 值） | 7 個 `MINIMAX_*` 變數齊（API_KEY/BASE_URL/MODEL/GROUP_ID/EMBED_*）；config.local.yaml 無 minimax | ✅ |

### 2.1 接線實測（決定本輪設計的關鍵事實）
- **CORRECTION 路徑**（`core/kernel.py:230-260`）：step evaluator 失敗 → `failure_reason` 非 None → `if self._brain is not None and attempt < max_retries:` → `c = self._brain.decide_correction(...)`（→ MinimaxBrainAdapter → MinimaxClient POST `base_url`）→ 若 `c is None`（API 故障）回 ESCALATE；否則 emit `=== STATE: CORRECTION | step=Sxx attempt=N ===`（kernel.py:255-258）→ `task.prompt = c.correction_prompt`（kernel.py:259-260，修正 prompt 真餵回）→ 重試同一 step。
- **雙重驗證**（`shell_evaluator.py:26-45`）：先比對 `expected_output_regex`，再跑 `evaluator_command`；任一失敗即回 failure_reason。→ 故意失敗 playbook 可讓 regex 過、evaluator 擋（pytest 真跑判定）。
- **brain 注入**（`main.py:130-133`）：`brain = MinimaxBrainAdapter(minimax) if cfg.minimax.enable_kernel_brain else None`。→ 必須 `enable_kernel_brain: true` 才有 self-correction（既有 4 config 皆 false，故閉環從未在真跑被走過）。
- **base_url / api_key 來源**（`main.py:103-107`）：`os.environ.get("MINIMAX_BASE_URL") or cfg.minimax.base_url`（env 優先於 config）；**autoclaude 不自動載入 .env**（main.py 無 `load_dotenv`，僅讀 `os.environ`）。→ W-87-1 mock：不載 .env，config `base_url=localhost:9100` 生效（為確定性，真跑顯式傳 `MINIMAX_BASE_URL=localhost mock` 覆蓋環境）；W-87-2 真：先把 .env 匯入環境，真 base_url/key 生效。

**硬閘 PASS** → 進階段二。

---

## §3 階段二增量設計

### 3.1 W 項（≤3）

| W 項 | 軌道 | 內容 | LOC 落點 |
|------|------|------|---------|
| **W-87-1**（主案例，機制接線真跑） | C 軌 × A 軌 | (1) 故意失敗 playbook `scripts/correction_loop_smoke.yaml`（TDD red stub → 第一次必失敗、修正後成功）；(2) mock config `scripts/ab_configs/correction_mock_config.yaml`（`enable_kernel_brain:true`、`base_url=localhost:9100`）；(3) 給 `tools/mock_brain_server.py` 加 additive 請求計數 + `GET /stats`（Brain 端互動客觀觀測）；(4) 驗證載具 `tools/correction_loop_verify.py`（pure `parse_correction_evidence` + 真跑 orchestration）；(5) 單元測試 `tests/tools/test_correction_loop_verify.py`；(6) **mock brain × 真 Claude 端到端 correction 真跑取證** | mock_brain_server +~20 行（≤data 150）；carrier ~ tool 新檔 ≤300；playbook/config 非 .py |
| **W-87-2**（驗品質，真模型真跑） | A 軌 | 同 playbook + 真 config（`enable_kernel_brain:true`、不設 base_url→走真 Minimax），.env 匯入環境後真跑：**真 Minimax × 真 Claude** 驗修正品質（首次失敗後真 Minimax 回的修正使其通過） | 無新生產碼（真跑取證；key 絕不入庫） |

> W-87-1 不需任何憑證（mock 零成本）；W-87-2 用掌舵者 .env 既有 key（只經環境變數傳入，絕不寫進任何提交檔案）。

### 3.2 故意失敗 playbook 設計（`scripts/correction_loop_smoke.yaml`）
- **S01**（`maintain_context:false`，無 evaluator → 必過）：請 Claude 建 `calc_test.py`，含 `multiply(3,4)==12`、`multiply(0,7)==0`、`multiply(-2,5)==-10` 三斷言；**先不建 calc.py**（TDD red）；輸出 `[TEST_READY]`。
- **S02**（`maintain_context:true`，`evaluator_command: pytest calc_test.py -q`）：請 Claude **先建佔位 stub `def multiply(a, b): return 0`**（明確標示為 TDD red 階段刻意未完成實作）；輸出 `[IMPL_DONE]`。
  - **attempt 0**：Claude 照指令寫 stub → regex `[IMPL_DONE]` 過 → evaluator pytest 失敗（`0 != 12`）→ failure_reason → 觸發 Brain CORRECTION → `task.prompt` 換成 Brain 修正 prompt。
  - **attempt 1**：Claude（`--continue` 帶 attempt 0 脈絡＝看見自己的 stub + 失敗的 pytest 期望 multiply 行為）+ 修正 prompt 提示 → 改寫 `return a * b` → pytest 過 → success。
  - `max_retries: 3`（足夠修正空間）。
- **為何用「stub」而非「故意寫 bug」**（降 flaky）：要求 Claude 寫佔位 stub 是自然的 TDD red 指令（非要求它寫錯誤邏輯），真 Claude 必確定性照做 → **保證 attempt 0 失敗**；修正方向（multiply 應為乘法、pytest 已明示期望值）明確到 attempt 1 必改對 → 降低端到端 flaky。

### 3.3 介面 delta
- **`tools/mock_brain_server.py`**（W-87-1.3，additive）：
  - 模組級 `_STATS = {"post_count": 0, "decisions": []}`；`do_POST` 內 `_STATS["post_count"] += 1` 並 append 決策型別摘要（不存敏感內容）。
  - `do_GET`：`/stats` → 回 `_STATS`（既有 `/health` 不變）。
  - 既有 `build_decision` / `_envelope` / correction Hallucination Guard 邏輯**零改**（向後相容，既有 6 單測不退化）。
- **`tools/correction_loop_verify.py`**（W-87-1.4，新檔）：
  - `parse_correction_evidence(log_text: str) -> dict`（**pure、無副作用、可單元測**）：以 regex 數 `=== STATE: CORRECTION |` 行數 → `correction_count`；偵測末段 `KernelResult(...success=True...)` / `Playbook 結束` 行 → `final_success: bool`；回 `{correction_count, final_success, escalated}`。
  - `main`（orchestration，非單元測；真跑時手動執行、耗 claude 額度）：起 mock server 子程序 → 等 `/health` → 臨時 workdir 跑 `autoclaude correction_loop_smoke.yaml --config <mock/real> --fresh` → 讀 autoclaude log → `parse_correction_evidence` → GET `/stats` 取 `post_count` → 印 evidence 並回退碼（閉環成立 0 / 否則非 0）。`--mock`（起 mock server + 設 env 指 localhost）vs 預設（假設環境已有真 MINIMAX_*）。
- **`scripts/correction_loop_smoke.yaml`** / **`scripts/ab_configs/correction_mock_config.yaml`**：YAML 載具，非 .py、不在 importlinter/LOC 掃描範圍。

### 3.4 `.importlinter` 各 contract 影響分析
- W-87-1 生產碼改動＝**零**（`autoclaude/` 套件未動一行；改的是 `tools/`＝載具，不在 importlinter 8 contract 掃描範圍）。playbook/config＝YAML。→ 8 contract 全不受影響。

### 3.5 checkpoint additive 欄位需求
- **無**。本輪不寫 PlaybookCheckpoint、不碰 DAL 三後端（mock server 計數是程序內記憶體、carrier 是外部觀測載具）→ 持久化零影響、三後端零停機維持。

### 3.6 RTM 需求列（測試意圖，Rule 9）
| RTM | 意圖（守什麼） | 驗證方式 |
|-----|--------------|---------|
| RTM-87-1 | correction 閉環真跑：autoclaude log 含 ≥1 `STATE: CORRECTION` marker（Brain 真被 Kernel 呼叫、非死碼） | 真跑 log（W-87-1/2）+ `test_parse_correction_evidence_counts_markers`（合成 log 確定性驗 parser） |
| RTM-87-2 | 指揮真的傳達 + Brain 端互動：mock server `/stats.post_count ≥1`（Brain 收到 ≥1 次諮詢 POST；修正 prompt 確由 Brain 產出並餵回，非空轉） | 真跑 GET /stats（W-87-1）+ `test_mock_server_stats_counts_posts`（單元） |
| RTM-87-3 | 閉環收斂（誠實兩態）：修正後最終 success；或達 max_retries 誠實 escalate（不虛報成功） | 真跑 final_success（W-87-1/2）+ `test_parse_correction_evidence_detects_success_and_escalation`（合成 log 兩態） |
| RTM-87-4（W-87-2） | 真 Minimax 修正品質：首次失敗後真 Minimax 回的修正使其通過 | 真跑取證（真 Minimax × 真 Claude，條件＝.env key 有效） |

### 3.7 <Architecture_Design_Review>
1. **架構純潔性**：本輪零碰 `autoclaude/` 生產碼（Kernel/ports/plugins/Thin Facade 全不動）；改動限 `tools/` 載具（mock server 計數 + 新 verify carrier）+ YAML 載具。無 God-object、Thin Facade 維持。✅
2. **持久化相容**：無新 checkpoint 欄位（mock 計數是程序內、carrier 是外部觀測）；DAL 三後端零影響、零停機維持。✅
3. **安全防護網**：mock server `/stats` 只回計數/型別摘要（不回敏感 body）；無新 CONDITIONAL 路徑（playbook prompt 是給 claude 的自然語言，非「從文件生成 shell 指令」；evaluator_command 是固定 `pytest calc_test.py -q` 靜態字串，非動態合成）。白名單消毒無新攻擊面。✅
4. **對外 I/O 安全**：mock_brain_server 綁 `127.0.0.1`（既有，本機 loopback）；無新 `ToolInvocationPort` 外呼路徑。W-87-2 對真 Minimax 的 HTTP 走既有 MinimaxClient（improving 系列既有路徑，本輪不新增外呼能力）；key 只經環境變數傳入、絕不寫入任何提交檔案。✅

### 3.8 B 軌 dogfooding scope
- 本輪零碰 AISLDC_SDD 框架本體 → 免 Copy-on-Evolve、免五軌 TLC（零碰 `*.tla`/FSM/`_HAPPY_PATH`）。
- 計畫書（本檔）＝ SCG-0/1 載體；§3.2/3.3 介面 delta ＝ SCG-2；§3.6 RTM ＝ SCG-5 雛形。

---

## §4 實作與雙重驗證（階段三回填）

### 4.1 實作進度
- **W-87-1 構件**（全在 `tools/`/`scripts/`，零碰 `autoclaude/` 生產碼）：
  - `scripts/correction_loop_smoke.yaml`（故意失敗 playbook，TDD red stub；S02 **刻意不設** `expected_output_regex`，見 DEF-87-001）。
  - `scripts/ab_configs/correction_mock_config.yaml`（`enable_kernel_brain:true` + `base_url=localhost`）/ `correction_real_config.yaml`（`enable_kernel_brain:true`，base_url/key 由 .env 環境變數提供）。
  - `tools/mock_brain_server.py`：additive `_STATS` 計數 + `GET /stats`（既有 6 單測零退化）。
  - `tools/correction_loop_verify.py`：純函式 `parse_correction_evidence` + 真跑 orchestration（同程序 threaded mock server，PTY-safe 讀 file log）。
  - `tests/tools/test_correction_loop_verify.py`：**7 新測**（RTM-87-1/3 parser 5 測 + RTM-87-2 mock /stats 2 測）。
- **零退化測試帳**：全套 3501→**3514**（+13 精確歸因＝7 新測檔 + **6 既有 `tests/integration/test_yaml_import.py` 參數化 YAML 契約測試自動覆蓋新 `scripts/correction_loop_smoke.yaml`**：parse/sha256/format/process/roundtrip/build_diffs 各 1，全過——新 playbook 被既有契約測試自動納管，非新增業務測）。

### 4.2 受控突變實證（非空殼，禁 git checkout，遵 [[git-checkout-mutation-revert-hazard]]）
| 突變 | 改動 | 預期轉紅 | 實測 |
|------|------|---------|------|
| MUT-87-1 | parser `correction_count` 恆 0（不數 marker） | RTM-87-1/3 | ✅ 3 測轉紅，Edit 還原復綠 |
| MUT-87-2 | mock server `post_count += 0`（不計數） | RTM-87-2 | ✅ 轉紅（assert 0==2），Edit 還原復綠 |
| MUT-87-3 | parser `success=True` 誤判為 False | RTM-87-3 | ✅ 2 測轉紅，Edit 還原復綠 |

還原後 13 passed（7 carrier + 6 mock server）；git diff 僅 mock_brain_server +22/-1（純 /stats），無突變殘留。

### 4.3 真跑取證（self-correction 閉環端到端首證）
> 閉環 5 環節：①真 Claude stub 失敗 → ②Kernel 呼 Brain → ③Brain 回 CORRECTION → ④修正 prompt 餵回 → ⑤真 Claude 改對 → 成功。

**W-87-1（mock brain × 真 Claude，連 3 跑穩定收斂，flaky 風險閉合）**：
- 鐵證（典型一跑）：`=== STATE: CORRECTION | step=S02 attempt=1 ===`（②③④真）+ `KernelResult(success=True, completed_steps=2, total_steps=2, reason='success', escalated=False, peak_token_pct≈6.0)`（⑤收斂）+ `[S02] ... ✓ (attempt 2)`（修正後 attempt 通過）+ autoclaude exit 0。
- carrier 證據：`CORRECTION marker 次數=1`（RTM-87-1）/ `最終 success=True`（RTM-87-3）/ `escalated=False` / `mock _STATS.post_count=1 decision_types=['correction']`（RTM-87-2，Brain 端真互動）。
- 連 3 跑皆收斂（peak_token_pct 6.02/9.46/9.38 真跑浮動，不變式 success=True/correction=1 恆成立）。

**W-87-2（真 Minimax × 真 Claude，驗修正品質，RTM-87-4）**：
- 環境：`set -a && . ./.env && set +a` 匯入真 key（`MINIMAX_BASE_URL` host=`https://api.minimax.io`，**非 mock**；key 只經環境變數、絕不入庫）；config=`correction_real_config.yaml`。
- 鐵證：`=== STATE: CORRECTION | step=S02 attempt=1 ===`（真 Minimax 真被呼叫）+ `KernelResult(success=True, 2/2, reason='success', escalated=False, peak_token_pct≈6.2)` + exit 0。
- **意義**：真 Minimax 首次失敗後回的修正品質，足以驅動真 Claude 在 attempt 2 改對收斂——機制（mock 驗）與品質（真 Minimax 驗）雙證。

### 4.4 真跑揭露之缺陷（dogfooding，發現即記入帳本）
| DEF | 嚴重度 | 摘要 | 狀態 |
|-----|--------|------|------|
| DEF-87-001 | P2 | self-correction × `expected_output_regex` 交互：Brain 修正取代 task.prompt 丟 keyword → regex 閘修正後永不過 → escalate | smoke 端即修（S02 移 regex、evaluator 權威閘）+ production routed 待決策 |
| DEF-87-002 | P3 | autoclaude 生產 logger console handler cp950 撞 `✓` 崩潰（非致命、file handler utf-8 完整）；DEF-82-001 家族生產側 | routed 下輪 C 軌 |
| DEF-87-003 | P3 | 新建載具 cp950 print 崩潰（自犯，DEF-82-001 家族） | fixed@improving_87（reconfigure utf-8 + ASCII 輸出） |
| DEF-87-004 | P3 | 新建載具 subprocess mock server Windows terminate 殺不掉 → 殘留埠 → /stats 失準 | fixed@improving_87（同程序 threaded server + 直讀 _STATS） |

---

## §5 零退化驗證矩陣（階段四實測）

| 檢查 | 命令 | 通過條件（floor=improving_86 實測） | 實測 |
|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3501 passed / 0 failed（新測只增不減） | ✅ **3514 / 0 / 122 skipped**（+13＝7 新測 + 6 既有 YAML 契約測試自動覆蓋；兩次連跑同值穩定） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ 8 kept / 0 broken |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | ✅ violations=0（total **19783 不變**＝零碰 `autoclaude/` 生產碼 LOC） |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | ✅ OK |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | ✅ **N/A 類型①**——`git status --short` 僅 `AutoClaude/` + `docs/`，零碰 `AISDLC_SDD/`（鐵證）；階段一已實測 exit 0 |
| DAL 等價 | equivalence job | 三後端等價 | ✅ **N/A 類型②**——`tests/equivalence/` 隨全套 3514 通過、本輪零 DAL/checkpoint 改動、無新 round-trip 契約 |
| 五軌 TLC | （僅 FSM 變更時） | 五軌 0 violation | ✅ **N/A 類型①**——零碰 `*.tla`/FSM/`_HAPPY_PATH`（git diff 僅 `tools/`+`scripts/`+`tests/`+`docs/`）、TLC 不在 pytest 全套需 Java |

---

## §6 缺陷帳本本輪更新
- **本輪新增 4 筆**：DEF-87-001（P2，self-correction × regex 交互，smoke 緩解 + production routed）/ DEF-87-002（P3，生產 logger cp950，routed）/ DEF-87-003（P3，載具 cp950 print，fixed）/ DEF-87-004（P3，載具殘留埠，fixed）。詳見 [docs/06_quality/AutoSDD_Defect_Log.md](../06_quality/AutoSDD_Defect_Log.md)。
- **open/routed 複驗**：DEF-01-007 / DEF-01-009 / DEF-23-005 / DEF-62-001（open）+ DEF-17-001 / DEF-19-001 / DEF-35-001（routed）全維持原狀態——本輪只動 `tools/`+`scripts/`+`tests/`，未觸碰任一缺陷標的。

## §7 結案總結
本輪＝**C 軌 × A 軌：self-correction 閉環「端到端真跑」首證**。閉合歷輪「資產備好但沒端到端串起來真跑」盲區（improving_72/77/86 同源 pattern）——「Brain 指揮 Executor 修正」這條閉環**首次在真跑下被走過並驗證收斂**（過去僅 FakeBrain 單元測 + 紙上覆蓋）。
- W-87-1（機制接線，mock brain × 真 Claude）：故意失敗 playbook + mock /stats + 驗證載具；連 3 跑 correction=1→success=True→post_count=1 穩定收斂。
- W-87-2（修正品質，真 Minimax × 真 Claude）：真 Minimax 修正驅動真 Claude 改對收斂（RTM-87-4）。
- 零退化 3514/0/122、lint 8 kept、LOC 0（生產碼零變動）、snapshot OK；3 受控突變全轉紅還原；零碰 `AISLDC_SDD/`。`L_合體=L5` 維持（C 軌指揮官能力真跑取證加固，非成熟度推進）。
- dogfooding 揪 4 缺陷（2 即修、2 routed），其中 DEF-87-001 是真實 production 級交互發現（regex 閘 × Brain correction 收斂性）。

## §8 誠實限制與遞延候選
- **誠實限制**：(1) smoke 刻意以「TDD red stub→修正」保證確定性收斂，是「機制能否串起」的最小可信證，**非**壓力測試（單 step 單次 correction）；真實多輪/多 step correction 的收斂率非本輪標的。(2) W-87-1 為驗機制，S02 移除 `expected_output_regex`（DEF-87-001）——故本輪未驗「regex+Brain correction 並存收斂」，該議題隨 DEF-87-001 routed。(3) RTM-87-4 真 Minimax 僅 1 跑成功；真模型修正品質的統計穩定度（多跑成功率）未取，屬條件加碼。
- **遞延候選 improving_88**：(a) DEF-87-001 production 決策——Kernel 套 correction 時是否自動保留 `expected_output_regex` 要求；(b) DEF-87-002 生產 logger cp950 韌性修復（含測試設計）；(c) SD_09 W1 觀察期 source-sha 閘門（時間閘 ~6/29 成熟）；(d) self-correction 壓力場景（多 step／多輪 correction／step_mutation 路徑）真跑收斂率取證。
