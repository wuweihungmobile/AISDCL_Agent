# FRD_Sdd_Bridge_Real_Run：SDD 橋接鏈首次真跑（TCS → sdd_compile → playbook → 真 claude／pytest → RTM 回寫 → `--last-run-summary`）

| 項目 | 內容 |
|------|------|
| 功能編號 | F-SBR-001 |
| 版本／狀態 | v1.2（與實作、真跑證據同步）。實作與測試已完成；乾淨真跑 4 次已做完，逐字證據在 [證據檔](../03_testing/SddBridge_RealRun_Evidence_20261011.md)（C1～C4）。真跑 run1 仍**作廢**（§2.6），其事實只作歷史。§2.7 判決、§3 嚴重度與缺陷描述、§4 驗收準則、§5 RTM、§6、§7 已依實作與證據檔更新；§2.1～§2.6 的探針實錄保持原貌 |
| 角色／性質 | SA＋SD 單一文件：需求、探針實錄、缺陷、驗收、RTM、實作順序、劃界全在本檔，不另產 SRD／ADR |
| 路徑慣例 | 本檔相對路徑一律相對於 `AutoClaude/`，指令在 `AutoClaude/` 下執行；`<SB>`＝`<本機 session scratchpad>/sbr`（探針證據與腳本原檔，不入庫，會隨 session 消失） |
| 調查基準 | macOS Darwin 25.6.0；Python 3.11.15；pytest 9.1.1；claude 2.1.296（模型一律 haiku）；HEAD a0414602、探針期間 repo 唯一變動為本檔（量測值，Developer 動工前須自己重跑，不採信本檔）；§2～§3 的程式碼行號座標皆為該 HEAD 的值，實作後已位移（以符號名為準） |

> **三個結論（證據見 §2、§3）**
> 1. 橋接鏈**前半**（TCS→凍結→編譯）零 token 即可驗證且正確：2 AC／3 AT → 3 個 task，各欄位與 adapter 規則逐條相符（§2.3）。
> 2. **後半**（真 AI 能否過兩層驗收閘）的機制缺口已由探針證實：prompt 沒把評估指令、測試命名／位置、輸出契約、工作目錄交給 AI（H1～H4）。run1 雖作廢，仍證實三件事：(a) AI 把檔案寫進規格所在樹而非 cwd，在引擎 cwd 跑評估指令 rc=4（D-SBR-08）；(b) 第一層 regex 對 AT-001-1-1 是**偶然命中**（`cat` 只出現在 "Verification" 一字內），該層無鑑別力；(c) 額度軸 ≥95% 時引擎在 step 的第一個 attempt 後即硬 halt（run1 實測 step 1；程式依據 `policy.py:195`），log 卻印「context 18%」（D-SBR-09），此狀態下真跑走不完鏈。
> 3. 對派工書的兩處事實訂正：(a) 編譯實際產出的 evaluator 是**底線形式** `pytest tests -k "AT_001_1_1" -q`；(b) adapter 的 LOC 計價（只算斷言行，ADR-XPLAT-013）動工前為 **265／400**（完工後 279／400，見 AC-SBR-009），原始行數 405 不是判準，改 prompt 模板有 135 行餘裕。
> 4. （v1.2）乾淨真跑已做完（證據檔）：含驗收閘的 3 次真跑 rc=0、3／3 步通過（各步 attempt 數 1／3／1、1／2／1、1／1／1）；以 `git archive HEAD` 的編譯器編出**不含驗收閘**的修前對照（C4）在步驟 1 即 ESCALATION——自然命名使 `-k` 選 0 個測試（exit=5）、**同特徵碼 2 次即升級**（沒有用到 `max_retries` 的上限）。H1 因此在真 claude 上復現（樣本數 1），D-SBR-01 升 P1；D-SBR-04（`--fsm-state-path` 預檢）與 D-SBR-09（額度軸 halt 的 log）真跑沒有涉及，只有單元測試覆蓋。

---

## 1. 功能定義

### 1.1 一句話
**F-SBR-001**：讓「凍結的 `TEST-CONTRACT-SPEC` 經 `sdd_compile` 編成的 playbook」能被真 claude（haiku）跑到全綠——補上橋接產物 prompt 缺的驗收閘資訊（工作目錄、評估指令、測試位置與命名、輸出契約），並把一個迷你專案入庫成可重現的回歸載具；跑完後 RTM 逆向報告落檔、`--last-run-summary` 印 finished。

### 1.2 非目標
| # | 非目標 | 理由 |
|---|--------|------|
| N1 | 不改 Gherkin→regex 推導規則（`_gherkin_to_regex`，improving_29～42 家族） | 規則自成一族且有哨兵鎖；本案只讓 AI「知道」既有契約 |
| N2 | 不改 evaluator 模板（仍 `pytest <path> -k "<AT_底線>" -q`） | 模板是 §1.3 截斷點 1 的白名單；R52 已決定不帶 `python -m` |
| N3 | 不改 Kernel／Brain 重試語意 | Brain 關閉時重試無回饋屬設計取捨，登記為 D-SBR-07 |
| N4 | 不碰 PRD→Archy→`three_tier_to_playbook` 那條路（improving_95） | 本案只管 TCS→`sdd_compile` 這一條 |
| N5 | 不讓失敗 run 產出 RTM 報告 | 登記為 D-SBR-05，需另定「部分覆蓋」語意 |
| N6 | 不改 `AISDLC_SDD/**`（含 TEST-CONTRACT-SPEC 模板） | 模板不可直接改；LATEST 以外不可原地改 |
| N7 | 不新增 harness 腳本；不調任何額度／context 門檻 | 真跑指令寫進證據檔即可（Rule 2）；守衛的訊息就是答案 |

---

## 2. 探針實錄（產物皆在 `<SB>`；指令逐字、輸出摘自該處原檔）

### 2.1 迷你專案 WordCount
- 規格：`<SB>/fixture/TEST-CONTRACT-SPEC-WordCount.md`（137 行，照官方模板，含 `spec-format-version`、場景字樣 greenfield；run1 後 `<SB>/wc_proj/` 內多了 AI 寫的程式檔，故以 `fixture/` 這份純淨複本為準）；`shasum -a 256` ＝ `0de6845eee4e1d63532a76aebd5049651f8e5fa061599d0b84aeeb9fe110f742`（與編譯後 `spec_digest` 相同，因 digest＝文字的 sha256）。
- 介面：`wordcount(text: str) -> dict[str, int]`；2 AC、3 AT、全 Unit。

| AT | AC | Then 取材 | 預期推導的 `expected_output_regex` |
|----|----|-----------|-----------------------------------|
| AT-001-1-1 | AC-001-1 | 正向、兩個引號字面「the」「cat」 | `(?s)(?=.*the)(?=.*cat)` |
| AT-001-1-2 | AC-001-1 | 負向：`不應出現…「hello,」`＋正向「hello」 | `(?s)\A(?=.*hello)(?!.*hello,)` |
| AT-002-1-1 | AC-002-1 | `拋出 TypeError`（無引號、無狀態碼） | `\bPASS(ED)?\b`（weak 後備） |

### 2.2 凍結：走真 FSM CLI 入口，狀態目錄導向 scratchpad
- 指令（cwd＝`AISDLC_SDD/AISDLC_SDD_v0.30/`）：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<該目錄> SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 python <SB>/freeze/drive_fsm_cli.py <SB>/wc_proj` → `driver_rc=0`。
- 該腳本以 `fsm_runtime._cli()`（＝`python -m tools.fsm_runtime.fsm_runtime` 的入口）依序餵 argv，逐字輸出在 `<SB>/freeze/freeze_stdout.txt`，每步 `[rc=0]`：`transition --to SCENARIO_DETECT`→`AGENT_LOAD`→`SPEC_DRAFTING`→`SCG_VALIDATION`→`HUMAN_PENDING`（各印 `OK transitioned to …`），`spec-frozen --stage Stage-2 --doc docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md --project wordcount_sbr`（印 `OK spec frozen: Stage-2`），`show`（`current_state: SPEC_FROZEN`、`frozen_stages` 一筆）。
- 為何要多一行賦值：CLI 沒有 `--state-path`／環境變數出口，`state_loader.DEFAULT_STATE_DIR`（`state_loader.py:31`，指向 `AISDLC_SDD_v0.30/build/reports/fsm/`）是 import 期常數，直接跑會在 AISDLC_SDD 樹內留新檔。腳本於 import 後把它改指 `<SB>/wc_proj/build/reports/fsm`，其餘全走真 CLI 分派與真 `assert_transition`。這不是「純 CLI」，見 §7。
- 零污染證據：全 repo `git status --porcelain` 空；`find AISDLC_SDD -newer <marker> -type f` 只列 `AISDLC_SDD_v0.30/build/reports/fsm/CONTEXT-LEDGER-2026-10-10.yaml`——那是 harness 的 SDD hook（`SDD_ACTIVE_VERSION` 已設）每次工具呼叫都會更新、被 `AISDLC_SDD/.gitignore:313` 忽略的既有檔，不是本探針產物。

### 2.3 編譯：逐條核對
- 指令：`python -m autoclaude.tools.sdd_compile --spec-dir <SB>/wc_proj/docs --out <SB>/compile/playbook.yaml --project wordcount_sbr` → `compile_rc=0`，stdout `[sdd_compile] 已輸出 3 步驟 → …`；產物 sha256 `f8f19b541a18505a64716d357964888c5befa3676ec27eb9addc724f347f039b`（逐字存檔 `<SB>/compile/playbook.yaml`）。

| step_id | prompt | expected_output_regex | evaluator_command | max_retries | maintain_context | 符合派工書 §1？ |
|---------|--------|----------------------|-------------------|-------------|------------------|----------------|
| `sdd-greenfield-at-001-1-1` | 「依下列契約實作並使測試通過：」＋Gherkin 全文＋「規格出處：<絕對路徑>（digest 0de6845e）」 | `(?s)(?=.*the)(?=.*cat)` | `pytest tests -k "AT_001_1_1" -q` | 5 | false | 是 |
| `sdd-greenfield-at-001-1-2` | 同上 | `(?s)\A(?=.*hello)(?!.*hello,)` | `pytest tests -k "AT_001_1_2" -q` | 5 | true（同 AC 連續） | 是 |
| `sdd-greenfield-at-002-1-1` | 同上 | `\bPASS(ED)?\b`（`weak_regex: true`） | `pytest tests -k "AT_002_1_1" -q` | 5 | false（跨 AC） | 是 |

另：`workflow_type: aisdlc_sdd`、`workflow_path`＝spec_dir 絕對路徑、`evaluator_timeout_seconds: 120`、每 task 帶全值 `spec_digest`。**唯一不符**＝evaluator 為底線形式（`_build_evaluator_cmd`，`sdd_to_playbook_adapter.py:402-405` 把 `-` 換成 `_`）。prompt 內唯一出現的 ID 是標頭 `# AT-001-1-1`（連字號形）；執行時引擎另在前面加「總目標」錨點前綴（§2.6）。

### 2.4 H1／H3 探針矩陣（`<SB>/probe_h1/h1_matrix_raw.txt`）
指令模板：`(cd <layout> && pytest tests -k "<K>" -q -p no:cacheprovider)`；`<K>` 取連字號形與編譯實際產出的底線形。

| layout | `-k "AT-001-1-1"` | `-k "AT_001_1_1"`（編譯實際） |
|--------|-------------------|-------------------------------|
| a 函式 `test_AT_001_1_1` | `2 deselected`，rc=5 | `1 passed, 1 deselected`，rc=0 |
| b `pytest.param(..., id="AT-001-1-1")` | `1 passed, 1 deselected`，rc=0 | `2 deselected`，rc=5 |
| c 檔名 `tests/test_AT-001-1-1.py` | `1 passed`，rc=0 | `1 deselected`，rc=5 |
| d 一般語意名 `test_counts_repeated_words_case_insensitively` | `2 deselected`，rc=5 | `2 deselected`，rc=5 |
| e 無 `tests/` | `ERROR: file or directory not found: tests`，rc=4 | 同左 rc=4 |
| f 檔名 `tests/test_AT_001_1_1.py`（函式名通用） | 未測 | `1 passed`，rc=0 |
| g `@pytest.mark.AT_001_1_1` | 未測 | `1 passed, 1 warning`（PytestUnknownMarkWarning），rc=0 |

- 判讀：pytest 9.1.1 **接受**連字號 `-k` 表達式（b、c 連字號列 rc=0），故 `_build_evaluator_cmd` 註解「-k 不接受連字號」對此版已不成立；但底線化仍對（函式名不能含連字號）。**唯一能過關的命名含底線 token**（a、f、g），而 prompt 裡只看得到連字號形；照抄可見 ID 當檔名或 param id（c、b）反而 rc=5。
- H3：被測模組 `wordcount.py` 放 cwd 根、`tests/test_wc.py` 以 `from wordcount import wordcount` 匯入。無 `__init__.py`／`conftest.py`／`pytest.ini` 時，裸 `pytest tests -k "AT_001_1_1" -q` → `ModuleNotFoundError: No module named 'wordcount'`、`1 error`，**rc=2**；同目錄 `python -m pytest …` → `1 passed`，rc=0。補 `tests/__init__.py`、根 `conftest.py`、`pytest.ini` 的 `pythonpath = .` 任一，裸 pytest 即 rc=0。

### 2.5 其他零 token 探針（`<SB>/probe_adapter/probe_adapter_out.txt`、`<SB>/veto_probe/`）
- (a) `_scenario_of`：官方模板原樣 → `integration`；我方規格移除 greenfield 字樣 → `testing`；含 greenfield → `greenfield`。
- (b) `--fsm-state-path` 不隨 playbook 帶到執行期：狀態檔放在 spec_dir 祖先鏈之外，`sdd_compile … --fsm-state-path <樹外>` 得 `compile_rc=0`；再 `python -m autoclaude <pb> --config <cfg> --fresh`（cwd＝空目錄；僅 `claude --version`，未呼叫模型）得 `engine_rc=1`、`KernelResult(success=False, completed_steps=0, total_steps=3, reason='vetoed_at_pre_run', …veto_reasons=['[sdd_governance] SDD-VIOLATION[SPEC_NOT_FROZEN] …找不到 FSM 狀態檔…'])`，耗時 0.0 秒；`--last-run-summary` rc=0 印 `結果：失敗（FAILED）；原因：vetoed_at_pre_run；否決原因：…`。
- (c) regex 純事實（構造輸入，**不代表任何模型的實際輸出**）：`\bPASS(ED)?\b` 對 `3 passed in 0.02s`、`All tests passed`、`Passed` 皆 no match，對 `PASS`、`PASSED`、`test_x PASSED` 為 MATCH；`(?s)\A(?=.*hello)(?!.*hello,)` 對 `hello, world` no match、對 `hello world counted` MATCH。

### 2.6 真跑 run1（**作廢：cwd 被探針筆記污染＋額度 95% 硬 halt**；其中已證實的事實照列）
- 指令：`bash <SB>/run_real.sh run1 <SB>/compile/playbook.yaml`（cwd＝`<SB>/run1/work` 空目錄；config 同上一輪證據檔 §1，省略 `minimax.api_key: "dummy"`，以 `env -u MINIMAX_API_KEY` 保證 Brain 關閉）。第 1 個 attempt 後引擎 halt 並進入 1800 秒等待，我以 TaskStop 停掉（`pgrep` 確認無殘留行程）；`last_run_summary.json` 停在 `"status": "running"`，`<checkpoint_dir>/rtm/` 不存在。
- 引擎 log 逐字（`<SB>/run1/logs/autoclaude.log` 第 64／65／67／73 行；`…` 為省略，`<SB>` 為路徑縮寫）：
  ```
  23:32:44 [INFO] autoclaude.perception: subprocess 模式啟動：['claude', '--permission-mode', 'bypassPermissions', '--model', 'haiku', '--output-format', 'json', '-p', '=== 本次自動化任務的總目標 ===\n完成 greenfield 場景全部 3 條 AT 契約（規格 digest 0de6845e）\n…\n依下列契約實作並使測試通過：\n# AT-001-1-1 … 規格出處：<SB>/wc_proj/docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md（digest 0de6845e）']
  23:33:13 [INFO] autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=sdd-greenfield-at-001-1-1 pct=17.6421 ===
  23:33:13 [WARNING] autoclaude.core.kernel: === STATE: TOKEN_HALT | [sdd-greenfield-at-001-1-1] context 18% >= halt 門檻 ===
  23:33:13 [INFO] autoclaude.core.services.auto_resume: AutoResumeService | AUTO_RESUME #1/10 | 排定等待 1800s
  ```
- claude json（`<SB>/run1/logs/playbook_sdd-greenfield-at-001-1-1.log`）：`num_turns 9`、`duration_ms 23776`、`total_cost_usd 0.00821209`、`usage`＝input 12／cache_creation 22470／cache_read 153939、`contextWindow 1000000`。`result` 逐字節錄（`…` 為省略）：
  ```
  AT-001-1-1 is implemented and its test passes.
  **Files (in `wc_proj/`):** … `tests/test_AT-001-1-1.py` … The function is `test_AT_001_1_1`. … `conftest.py`: an empty root conftest … under a bare `pytest` run. Without it, the import fails.
  - … names carry both the hyphenated and underscored forms … A prior probe showed that only one spelling matches with a single name.
  - I did not change the spec's status checkboxes or touch the `STATE.md` / run scripts in the scratchpad.
  ```
- **污染證據**（巢狀逐字稿 `~/.claude/projects/…-sbr-run1-work/0eefddef-cce4-4d4f-95f5-f0ee37abdb1b.jsonl`，8 次 tool_use）：#1 `cd <SB> && ls -la . run1/work; find . -maxdepth 4 …`；#3 `… cat STATE.md …`；#4 `cat probe_h1/h1_matrix_raw.txt | head -80`（我的探針矩陣，含命名與 import 的答案）；#5～7 `Write` 到 `<SB>/wc_proj/{wordcount.py,conftest.py,tests/test_AT-001-1-1.py}`。`<SB>/audit_nested_transcript.py` 判 8／8 越界。
- 離線重算（零 token；對 run1 結束時的實際檔案）：
  - 引擎 cwd（`<SB>/run1/work`，空）跑評估指令 `pytest tests -k "AT_001_1_1" -q` → `ERROR: file or directory not found: tests`，**rc=4**；AI 寫檔處 `<SB>/wc_proj` 跑同一指令 → `1 passed in 0.06s`，rc=0。
  - 第一層 regex `(?s)(?=.*the)(?=.*cat)` 對 `result` 全文 `re.search` → **MATCH**；`the` 13 處，`cat` 只 1 處，在 "Verification:" 的 "Veri**cat**ion" 內。
  - `STEP_TOKEN_PEAK pct=17.6421`＝(12＋22470＋153939)／1,000,000，是整個 `claude -p` 工作階段各輪用量加總（`token_tracker.py:96`，自述近似）；最後一輪 `iterations[0]` 約 33,919。
  - halt 真因：`FileQuotaMeterAdapter.read_worst_pct()` → `QuotaReading(pct=95.0, kind='weekly_all', resets_at='2026-10-10T17:59:59.799057+00:00')`，`TokenGuardConfig.quota_halt_pct=95.0`（`policy.py:195`）。
- 未驗證：step 2／3、RTM 報告落檔、`--last-run-summary` 印 finished、補驗收閘後的行為。依主控裁決不再真跑；一鍵乾淨重跑備於 `<SB>/run_clean.sh`（開頭用引擎自己的量測器預檢，額度軸 ≥ `quota_halt_pct` 即拒跑，DRYRUN=1 已驗備料／凍結／編譯／config 不呼叫模型）。（v1.2 註：這些未驗證項已由證據檔 C1～C3 補上；本節保留為歷史。）

### 2.7 判決
- **H1（命名／位置）**：機制成立（§2.4）。現象：run1 的 AI 把測試函式命名為 `test_AT_001_1_1`（恰好過關），但它事先讀過探針矩陣，**不能當自然行為證據**。**v1.2 判決（證據檔 §10、§11）**：修前對照 C4（不含驗收閘）的 AI 用自然命名 `test_repeated_words_are_counted_case_insensitively`，`-k "AT_001_1_1"` 選 0 個測試、exit=5，同特徵碼 2 次即 ESCALATION——現象在真 claude 上**復現**（樣本數 1），升級條款成立，D-SBR-01 升 P1（主控裁決）；含驗收閘的 C1～C3，三步的測試檔名或函式名一律含底線 token。
- **H2（輸出契約）**：「第一層對 AT-001-1-1 會失敗」的預測**被證偽**（離線重算 MATCH）；但同時**證實該層無鑑別力**——`cat` 靠 "Verification" 的子字串命中，任何含子字串 `the` 與 `cat` 的文字（例如含 "Verification" 的空洞總結）都會過。weak（大小寫敏感）與負向兩型：**v1.2 判決（證據檔 §8、§11）**——weak 型（AT-002-1-1）在 C1～C3 的第 1 個 attempt 即過（AI 依 prompt 在回覆中寫出大寫 `PASSED`）；負向型（AT-001-1-2）在 C1、C2 的第 1 個 attempt 因回覆引述 `hello,` 而在 regex 層失敗、`max_retries` 內自癒，殘留的是「regex 約束 AI 回覆文字、卻源自 Gherkin 對函式輸出的描述」這個推導語意問題（N1 禁區；證據檔 O-2）。
- **H3（裸 pytest）**：機制成立；run1 的 AI 補了根 `conftest.py` 並自述 "Without it, the import fails"，但同樣受污染。**v1.2 判決（證據檔 §6、§11）**：含驗收閘的 C1～C3，AI 自行補 `tests/conftest.py`（C1）或 `pytest.ini` 的 `pythonpath = .`（C2、C3）；C4 的 AI 在測試檔內 `sys.path.insert` 自救，失敗原因是 exit=5 而不是 exit=2——exit=2 的現象本次**未**在真跑復現，措辭鎖（AC-SBR-004）只在單元層承擔。
- **H4（工作目錄，新）**：run1 觀察到 AI 寫檔於規格所在樹、不在 cwd（逐字稿 #1～#3 都在確認專案根）；成因推定為 prompt 只給規格絕對路徑、沒給工作目錄。無污染下是否重現：**v1.2 判決（證據檔 §9、§11）**——C2（規格樹與引擎 cwd 分開，含驗收閘）AI 的 Write／Edit 全落在 cwd、規格樹零新增檔（樣本數 1）；但**沒有修前對照**（HEAD 編譯器＋規格在 cwd 之外沒跑），只能說「修後的這一次沒有錯置」，不能說「修前必錯置」（證據檔 TH-01）。

### 2.8 原型驗證（設計驗證，`<SB>/proto_tests/`，不入庫，零 token）
- `test_proto_acceptance_gate.py`（AC-SBR-001～005 的測試設計＋D-SBR-01 參考實作）：`ADAPTER=real`＝`6 failed, 1 passed`；`ADAPTER=patched`＝`7 passed`。
- `test_proto_halt_label.py`（AC-SBR-011）：`GUARD=real`＝`1 failed`（log 只有 `kernel.py:353 === STATE: TOKEN_HALT | [T01] context 18% >= halt 門檻 ===`）；`GUARD=patched`＝`1 passed`。

---

## 3. 缺陷清單（P1～P3 的列格式可直接抄進缺陷帳本；P4 理論洞不入帳本，登記於證據檔〈13〉）

**D-SBR-01（P1；主控裁決：升級條款已由證據檔 C4 修前對照觸發——自然命名使 `-k` 選 0 個、同特徵碼兩次即 ESCALATION）prompt 不含評估指令、測試位置與命名規則（H1）**
- 症狀：§2.4——自然命名 `-k` 選 0 個測試（rc=5）；無 `tests/`（rc=4）。Brain 關閉時 `kernel.py:243` 的 CORRECTION 分支整段跳過，評估輸出不回饋 AI，重送的 prompt 與第 1 次相同（僅第 1 次多一段總目標錨點）。**C4 實測（證據檔 §10）：同一個失敗特徵碼（exit=5、`1 deselected`）連續 2 次即 ESCALATION**（`FailureTracker.is_stuck(consecutive_threshold=2)` 路徑，程式路徑推斷），沒有用到 `max_retries=5`＋`kernel.py:171` 的 `while attempt <= max_retries` 所允許的 6 次嘗試。run1 現象：見 §2.6／§2.7（命名過關但受污染）。
- 根因座標：`autoclaude/infra/adapters/sdd_to_playbook_adapter.py:155-158`（prompt 模板）與 `:402-405`（evaluator 底線化沒同步進 prompt）；屬 adapter prompt 模板面（SDD 模板 §2.1 無命名欄屬次要面，N6 不改）。
- 最小修法：`compile_tasks` 在現有 prompt 之後附「驗收閘」段，純字串、不動 evaluator 模板與 `SpecContract`；**一處改動同時覆蓋 D-SBR-01／02／03／08**。參考實作（`self._test_path` 即 `--test-path`，預設 `tests`）：
  ```python
  tok = c.at_id.replace("-", "_")  # 與 _build_evaluator_cmd 同一個底線化
  gate = ("\n驗收閘（由引擎親自執行，AI 自稱完成不算）：\n"
          "1. 檔案一律建立在「目前工作目錄」之下，不要寫進規格出處所在的目錄。\n"
          f"2. 評估指令（以裸 pytest 在目前工作目錄執行，不是 python -m pytest）：{c.evaluator_cmd}\n"
          f"   測試檔須放在 {self._test_path}/ 下，測試函式、類別或檔名須含 {tok}（例：def test_{tok}_basic），"
          "否則 -k 篩選會選到 0 個測試而失敗。\n"
          "3. 你的最後一則回覆須符合此 regex（Python re.search；(?=…) 必須出現、(?!…) 不得出現）："
          f"{c.expected_regex}")
  ```
  adapter `count_loc` 預計 +6～8 行（現 265／400）。措辭可調，契約以 §4 為準。**實作（v1.2）**：`sdd_to_playbook_adapter.py::_acceptance_gate`，措辭與上列參考實作略有不同（第 1 條多「規格出處只供閱讀」、第 2 條多「完成前請親自執行」、第 3 條多正負語意說明），`count_loc` 265→279／400。
- 紅綠測試：`tests/infra/test_sdd_to_playbook_adapter.py::TestPromptCarriesTheAcceptanceGate`（既有檔新增類別，未新開檔）；見 AC-SBR-001／002。

**D-SBR-02（P1；weak 型現象已由證據檔 C1～C3 驗證，負向型殘留見證據檔 O-2）prompt 沒有輸出契約，第一層 regex 驗收對象卻是 AI 的最後回覆（H2）**
- 症狀：`shell_evaluator.py:31` 對 `strip_ansi(output)` 做 `re.search(expected_output_regex)`，output＝claude json 的 `result`（`pty_executor.py:164`）。三型：引號正向（碰巧提到才過；run1 實測靠 "Verification" 內的 `cat` 子字串偶然命中）；正負併存（負向 `(?!.*hello,)` 對敘述文字生效，AI 引述 `hello,` 反而失敗）；weak 後備（`:75` 的 `\bPASS(ED)?\b` 區分大小寫，`3 passed` 不過，§2.5c）。手寫 playbook 全部明寫「完成後輸出 Keyword」，橋接產物沒有。
- 根因座標：同 D-SBR-01 的 `:155-158`；regex 推導（`:301-368`）以「AI 回覆文字」為驗證對象卻不交付契約。倉內有先例：`core/kernel.py:307` `_preserve_output_contract` 在 Brain CORRECTION 時把 regex 以「[硬約束·勿遺漏]…」補回 prompt（DEF-87-001），首次嘗試的橋接 prompt 漏了同一件事。
- 最小修法：驗收閘第 3 條（原文附上 `c.expected_regex`）。不改推導規則（N1）。
- 紅綠測試：同類別（`TestPromptCarriesTheAcceptanceGate`），見 AC-SBR-003。

**D-SBR-03（P2）裸 `pytest` 與 `python -m pytest` 的 import 差異，AI 自驗綠而引擎紅（H3）**
- 症狀：§2.4 H3，rc=2 `ModuleNotFoundError`；greenfield／迷你專案（模組在 cwd 根、無 conftest）必踩，有 `pyproject`／`conftest` 的真專案多半不觸發。
- 根因座標：`:47` `_EVALUATOR_TEMPLATE` 刻意不帶 `python -m`（R52，理由成立：編譯期與執行期環境可能不同）；prompt 沒告知差異。
- 最小修法：驗收閘第 2 條貼完整指令並明寫「不是 python -m pytest」，AI 依該指令自驗會遇到同一個錯並自行補 `conftest.py`／`pythonpath`。不改 evaluator 模板（N2）。
- 紅綠測試：同類別，見 AC-SBR-004（措辭綁定的輕量斷言；現象層由 AC-SBR-008 承擔——乾淨真跑未復現 exit=2，見 §2.7 H3）。

**D-SBR-04（P3）`sdd_compile --fsm-state-path` 不隨 playbook 帶到執行期，編譯綠、執行 PRE_RUN 被否決**
- 症狀：§2.5b，`compile_rc=0` → `engine_rc=1`、`vetoed_at_pre_run`、0 步、0.0 秒；訊息響亮、有變通（狀態檔放 spec_dir 祖先鏈的 `build/reports/fsm/`），且需非預設旗標。
- 根因座標：`autoclaude/core/wiring.py:290` `SddToPlaybookAdapter(observability=observability)` 不帶 `fsm_state_path`；執行期只能走 `_find_fsm_state`（`:220-231`）自 `workflow_path` 向上找；Playbook 無欄位承載（`autoclaude/tools/sdd_compile.py:46-57`）。
- 最小修法（建議 A）：`sdd_compile.main` 在寫檔前以執行期等價呼叫 `SddToPlaybookAdapter().load_spec(spec_dir)`（不帶 fsm_state_path）自驗，失敗則 rc=2、stderr 說明「執行期 PRE_RUN 找不到 FSM 狀態檔」，並不寫出 `--out`（約 6 行，fail-fast 於編譯期）。B＝在 Playbook 增欄位並讓 governance 讀它（schema＋plugin＋wiring 三處），只有要支援樹外狀態檔時才做。
- 紅綠測試：`tests/tools/test_sdd_compile_cli.py::TestCliMain` 新增兩例——`test_fsm_state_outside_runtime_search_path_exit_code_2` 與對照 `test_explicit_fsm_state_path_the_runtime_would_also_find_still_compiles`（防誤擋），見 AC-SBR-006（修前 rc=0＝紅）。

**D-SBR-05（P4，登記不修；主控裁決：plugin docstring 已文件化此設計取捨；失敗時可查的來源＝`--last-run-summary` 的失敗原因＋`autoclaude.log` 的評估失敗行。v1.2 訂正：原稱的「escalation dump」在 Kernel 路徑不會產生，見證據檔 O-5）逆向 RTM 報告只在 run 正常走完才落檔**
- 症狀：`rtm_writeback_plugin.py` 只訂閱 POST_RUN，kernel 僅在正常走完時發布（`kernel.py:134`）；ESCALATION／TOKEN_HALT 時 `<checkpoint_dir>/rtm/` 無任何報告（run1 實況：目錄不存在；證據檔 C4 再次實測：`<checkpoint_dir>` 為空目錄、`rtm/` 不存在），失敗當下最需要的「已覆蓋 AC／AT」看不到。失敗當下實際可查的來源（C4，ESCALATION）只有兩處：`--last-run-summary` 的原因行（`[sdd-greenfield-at-001-1-1] 評估指令失敗 (exit=5): pytest tests -k "AT_001_1_1" -q`）與 `autoclaude.log` 的 `評估失敗 [exit=5]` 行；**沒有 escalation dump**。
- 修法：屬 plugin 自述的設計取捨；要改須訂閱失敗路徑並定義「部分覆蓋」語意，超出本案（N5）。再開症狀：真跑 escalated 後操作者需要覆蓋快照而 `rtm/` 為空。

**D-SBR-06（P4，登記不修）`_scenario_of` 以子字串猜場景**
- 症狀：§2.5a——官方模板原樣得 `integration`、移除 greenfield 字樣得 `testing`；step_id 前綴因此成為 `sdd-integration-…`／`sdd-testing-…`，與場景語意無關（編譯、執行、RTM 同一函式，前後一致，無功能影響）。
- 根因座標：`sdd_to_playbook_adapter.py:259-264`。再開症狀：RTM 報告或操作者回報的場景標籤與規格宣稱不符而造成誤判。

**D-SBR-07（P4，登記不修；主控裁決：出廠 `enable_kernel_brain=false` 為刻意零退化姿態、開 Brain 即有回饋〔該路徑未經真跑，見 §7、證據檔 TH-02〕）Brain 關閉時重試不帶失敗回饋**
- 症狀：`kernel.py:243` 以 `self._brain is not None` 為 CORRECTION 條件；出廠預設（`enable_kernel_brain=false`，也是本環境唯一可用組態）下評估輸出只進 `failure_history`，不進下一次 prompt。D-SBR-01／02 的修法讓第一次 prompt 自足，重試仍盲。
- 修法：另案（確定性回饋後綴，評估輸出前 N 字）；本案不做（N3）。再開症狀（超出本輪觀察的閾值，與證據檔〈13〉一致）：**含驗收閘的 playbook** 上，同一步 `max_retries` 用盡或 ESCALATION，而重送的 prompt 不含任何失敗資訊。本輪已見弱形態：C4（刻意不含驗收閘的修前對照）步驟 1 同特徵碼 2 次即升級；C1 步驟 2 在 `max_retries` 內自癒。

**D-SBR-08（P2，新）prompt 沒告知工作目錄，「規格出處」絕對路徑把 AI 帶去規格所在樹寫檔，引擎 cwd 內評估 rc=4（H4）**
- 症狀（run1 逐字，§2.6；`<SB>/run1/logs/playbook_sdd-greenfield-at-001-1-1.log` 的 `result`）：`result`＝"**Files (in `wc_proj/`):**"；逐字稿 #5～7 `Write` 到 `<SB>/wc_proj/…`，而引擎 cwd＝`<SB>/run1/work`（`ls -laR` 為空）；在 cwd 跑評估指令 `ERROR: file or directory not found: tests`，rc=4，在 `wc_proj/` 跑 rc=0。Brain 關閉時（D-SBR-07）此錯重試也不會自癒（重送的 prompt 不含失敗資訊；C4 實測同特徵碼 2 次即升級，見 D-SBR-01）。**推論（未驗證）**：本 monorepo 的規格（`AISDLC_SDD/**`）與程式（`AutoClaude/`）分屬兩棵樹，若引擎從程式樹啟動而 prompt 指向規格樹，AI 可能把程式寫進框架樹。
- 根因座標：`sdd_to_playbook_adapter.py:155-158`（唯一的位置錨點是 `spec.spec_path`）；claude 與 evaluator 都繼承引擎 cwd（`infra/adapters/pty_executor.py:86-93` 的 `PtyWrapper` 無 cwd、`execution/evaluator.py:165-171` 的 `Popen` 無 cwd）——cwd 是執行時才知道的量，編譯期寫不進 playbook。
- 嚴重度評 P2：靜默錯置（AI 自認完成）＋可能寫進非預期樹；變通＝從含規格的專案根啟動引擎。
- 最小修法：驗收閘第 1 條（見 D-SBR-01 參考實作）。不加編譯期檢查（編譯時的 cwd 不等於執行時的 cwd）。
- 紅綠測試：AC-SBR-004 斷言 prompt 含「目前工作目錄」；現象層由 AC-SBR-008 在隔離專案根驗，並於證據檔補一次「規格在 cwd 之外」的負向觀察（v1.2：已做＝證據檔 C2，樣本數 1、無修前對照；修法是 prompt 層請求、不是機械約束，見證據檔 TH-01）。

**D-SBR-09（P3，新）TokenGuard 因額度軸 halt 時，log 印「context N% >= halt 門檻」，真因被掩蓋**
- 症狀（run1 逐字，§2.6；`<SB>/run1/logs/autoclaude.log:67`）：`=== STATE: TOKEN_HALT | [sdd-greenfield-at-001-1-1] context 18% >= halt 門檻 ===`，而 `halt_threshold_pct`＝90.0；真因是 `weekly_all` 95.0% ≥ `quota_halt_pct` 95.0。「18%」是整個工作階段各輪用量加總（§2.6），不是 context 大小。操作者會去查 context，查不到。
- 根因座標：`core/kernel.py:352-356`（固定文字，不分 halt 來源）；`plugins/token_guard/policy.py:195-203`（`hard` 條件與含 `quota_pct=… kind=…` 的 `ResourceRequest.reason`）；`core/resolution_policy.py:89-92`（merge 只保留 `request_halt` 布林，`reason` 從未被記錄）。
- 最小修法（B，建議）：`evaluate_quota` 在回傳 `ResourceRequest` 前 `logger.warning("TokenGuard 額度軸 halt：%s", reason)`（+2 行，**marker 文字不動**：`tools/ab_compare_backends.py:228` 以 `"TOKEN_HALT" in line` 計數並自該行取 context%（`tests/tools/test_ab_compare_backends.py:514`），`tests/core/test_kernel_token_halt.py:92`、`test_kernel_token_compact.py:115` 斷言前綴 `=== STATE: TOKEN_HALT`）。A＝`MergedResult` 增 `halt_reasons` 並讓 kernel marker 附原因（兩檔、約 6 行，須同步 A/B 解析器，風險較大）。
- 紅綠測試：`tests/core/test_kernel_token_halt.py` 新增 `test_quota_driven_halt_names_the_quota_axis_not_just_context`，見 AC-SBR-011（原型已驗修前紅、修後綠，§2.8；另加對照例 `test_context_driven_halt_does_not_claim_the_quota_axis`：context 軸 halt 不得冒稱額度軸）。真 halt 場景未真跑（證據檔 §11）。

---

## 4. 驗收準則（可機械驗證）

| AC | 前置／動作 | 期望 |
|----|-----------|------|
| **AC-SBR-001** | 以 §2.1 規格（fixture 或 `tests/infra/test_sdd_to_playbook_adapter.py::_write_spec` 同款）編譯 | 每個 task：`task.evaluator_command` 逐字出現在 `task.prompt`；prompt 內可擷取到 `-k "<token>"`，token＝`at_id` 的底線化（如 `AT_001_1_1`） |
| **AC-SBR-002** | 「字面讀者」模擬：只依 **prompt 內擷取的 token** 在 tmp 建 `tests/test_x.py::test_<token>_x`（空測試），以 `task.evaluator_command` 於該 tmp 以 subprocess 執行 | rc=0；修前 prompt 無 token ⇒ 擷取失敗＝紅（測試要能因 prompt 改動而失敗，Rule 9） |
| **AC-SBR-003** | 同編譯；參數化三型（引號正向／正負併存／weak） | 每個 task：`task.expected_output_regex` 逐字出現在 `task.prompt` |
| **AC-SBR-004** | 同編譯 | prompt 含「目前工作目錄」與裸 pytest 對照語（字面 `python -m pytest`） |
| **AC-SBR-005** | 相容 | 既有 prompt 內容不退化（開頭語、Gherkin 全文、`規格出處…digest8`）；既有測試案例**不得被改且全綠**：`tests/infra/test_sdd_to_playbook_adapter.py`、`tests/tools/test_sdd_compile_cli.py` 只新增案例（刪除行 0），`tests/integration/test_sdd_bridge/`、`tests/plugins/test_rtm_writeback_plugin.py` 不動（v1.1 的「零修改」字面在兩檔新增案例時不成立，此詮釋已獲主控接受） |
| **AC-SBR-006** | `--fsm-state-path` 指向 spec_dir 祖先鏈之外的有效凍結狀態檔 | `sdd_compile` rc=2；stderr 含「執行期」；`--out` 不存在。修前 rc=0＝紅 |
| **AC-SBR-007** | fixture 入庫 `scripts/bridge_e2e/wordcount/docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md`（逐字複製自 `<SB>/fixture/`，`sha256` 須為 `0de6845e…f742`）；測試把複本放 tmp、以 `_write_fsm_state` 補凍結狀態後編譯 | rc=0；3 個 task 的 step_id／evaluator_command／expected_output_regex／max_retries／maintain_context／weak_regex／spec_digest 逐欄等於 §2.3 表；不斷言含絕對路徑的欄位 |
| **AC-SBR-008** | 於互動視窗以入庫 fixture 與 `config.template.yaml`、`run_clean.sh <run> orig` 真跑（隔離專案根＝cwd、Brain 關閉、haiku、`--fresh`；預檢通過＝無訂閱軸 ≥ `quota_halt_pct`）。**v1.2 實際執行（證據檔 §2、§4）**：**C1** 主流程、**C3** 重跑、**C2** 負向觀察（規格在 cwd 之外，`OUTSIDE=1`）、**C4** 修前對照（`COMPILE_PYTHONPATH` 指向 `git archive HEAD` 的編譯器，編出不含驗收閘的 playbook，取代原定的 `patched` 變體），共 4 次 | C1／C2／C3：rc=0；log 含 `KernelResult(success=True, completed_steps=3, total_steps=3`；`<checkpoint_dir>/rtm/RTM-COVERAGE-<project>.yaml` 與 `RTM-GAP-<project>.md` 存在且顯示 2 AC／3 AT 全覆蓋；`--last-run-summary` rc=0 含 `結果：成功（SUCCESS）`、`步驟：通過 3 / 共 3 步`；`audit_nested.txt` 越界 0 次；逐字貼入證據檔 `docs/03_testing/SddBridge_RealRun_Evidence_20261011.md`。C4（修前對照）：預期失敗——步驟 1 ESCALATION、rc=1、`rtm/` 不存在 |
| **AC-SBR-009** | 護欄 | §6 第 6 步五道指令全部 rc=0；adapter `count_loc`≤400（動工前 265、完工後 279；量測值，現查 `python tools/check_loc_budget.py --json`）；改到的檔 `ruff check` rc=0 |
| **AC-SBR-010** | 零污染 | 完工後 `git status --porcelain` 只含：被改的 adapter／`sdd_compile.py`／`token_guard/policy.py`；既有測試檔的新增例（`tests/infra/test_sdd_to_playbook_adapter.py`、`tests/tools/test_sdd_compile_cli.py`、`tests/core/test_kernel_token_halt.py`，**不新開測試檔**）；`.env` 隔離修復的 `tests/conftest.py` 與 `tests/test_conftest_quota_env_isolation.py`（8 個 `test_r82_*` 因本機 `.env` 洩漏而紅，主控授權納入本案）；fixture（`scripts/bridge_e2e/wordcount/`）、本 FRD、證據檔、缺陷帳本；`AISDLC_SDD/**` 零差異。`tests/core/test_kernel_token_halt.py` 另有 3 行刪除＝清掉 HEAD 版就存在的 2 個 ruff 錯誤（`F401` 未用 import、`UP045` `Optional[float]`），語意不變 |
| **AC-SBR-011** | 額度軸 96%（測試內的 `_QuotaMeter` 替身）＋executor 回報 context 18% | 仍 HALT，且 caplog 含 `=== STATE: TOKEN_HALT` 前綴、`quota_pct=96`、`weekly_all`；修前沒有任何一行點名真因＝紅 |

---

## 5. RTM（AC → 測試；v1.2：測試已建，下列節點為實際名稱，一對一可追溯）

| AC | 缺陷 | 測試（已建） |
|----|------|--------------|
| AC-SBR-001 | D-SBR-01 | `tests/infra/test_sdd_to_playbook_adapter.py::TestPromptCarriesTheAcceptanceGate::test_evaluator_command_and_k_token_are_in_the_prompt` |
| AC-SBR-002 | D-SBR-01 | 同類別 `::test_a_literal_reader_of_the_prompt_passes_the_evaluator` |
| AC-SBR-003 | D-SBR-02 | 同類別 `::test_output_contract_regex_is_in_the_prompt_for_all_three_shapes` |
| AC-SBR-004 | D-SBR-03／08 | 同類別 `::test_prompt_pins_cwd_and_contrasts_bare_pytest_with_python_m_pytest` |
| AC-SBR-005 | 相容 | 同類別 `::test_the_original_prompt_is_kept_in_front_of_the_gate`、`::test_gate_and_evaluator_agree_on_a_custom_test_path`（`--test-path` 自訂時驗收閘與 evaluator 一致）＋既有四組測試（案例不得被改、全綠）＋既有 `test_prompt_contains_gherkin_and_digest` |
| AC-SBR-006 | D-SBR-04 | `tests/tools/test_sdd_compile_cli.py::TestCliMain::test_fsm_state_outside_runtime_search_path_exit_code_2`（＋對照 `::test_explicit_fsm_state_path_the_runtime_would_also_find_still_compiles`） |
| AC-SBR-007 | fixture | `tests/tools/test_sdd_compile_cli.py::TestBridgeWordcountFixture::test_fixture_compiles_to_the_golden_tasks`（＋`::test_real_run_config_template_keeps_brain_off_and_leaves_guard_thresholds_alone`：範本不得調任何門檻） |
| AC-SBR-008 | H1～H4 現象層 | 證據檔（人工真跑，非 CI；花真 token） |
| AC-SBR-009／010 | 護欄 | §6 指令；AC-SBR-010 的 `.env` 隔離另有鎖 `tests/test_conftest_quota_env_isolation.py::TestEnvFilesAreNotReadInTests::test_the_engine_reads_no_env_file_during_a_test`（釘 `tests/conftest.py` 的 `_hermetic_env_files`） |
| AC-SBR-011 | D-SBR-09 | `tests/core/test_kernel_token_halt.py::test_quota_driven_halt_names_the_quota_axis_not_just_context`（＋對照 `::test_context_driven_halt_does_not_claim_the_quota_axis`） |

---

## 6. 給 Developer 的實作順序與必跑驗證指令（均在 `AutoClaude/` 下；動工前自己重跑 §2 的探針，不採信本檔）

1. 重驗基線：`python tools/check_loc_budget.py --json`（adapter 的 `count_loc`、`tier_violations`）、`git status --porcelain`。
2. **先紅**：在 `tests/infra/test_sdd_to_playbook_adapter.py` 新增 `TestPromptCarriesTheAcceptanceGate`（AC-SBR-001～004）、在 `tests/core/test_kernel_token_halt.py` 新增 AC-SBR-011 那一例，`python -m pytest <該檔> -q` 須失敗，記下失敗行。設計可直接參照 `<SB>/proto_tests/`。
3. **後綠**：改 `compile_tasks` 的 prompt（D-SBR-01／02／03／08，一處改動）；`token_guard/policy.py` 加 2 行 log（D-SBR-09）；同檔轉綠。
4. D-SBR-04：先在 `tests/tools/test_sdd_compile_cli.py` 加紅測試，再改 `sdd_compile.py`（`count_loc` 現 98，絕對線 750）。
5. fixture 入庫（AC-SBR-007）：逐字複製 `<SB>/fixture/TEST-CONTRACT-SPEC-WordCount.md`，入庫後 `shasum -a 256` 須為 `0de6845e…f742`。注意：`AutoClaude/.gitignore:9` 的 `build/` 會忽略凍結狀態檔，故**狀態檔不入庫**，測試以既有 helper `_write_fsm_state` 在 tmp 重建。
6. 全套驗證：
   ```
   python -m pytest tests/ -q
   PYTHONUTF8=1 lint-imports
   ruff check autoclaude/infra/adapters/sdd_to_playbook_adapter.py autoclaude/tools/sdd_compile.py autoclaude/plugins/token_guard/policy.py tests/infra/test_sdd_to_playbook_adapter.py tests/tools/test_sdd_compile_cli.py tests/core/test_kernel_token_halt.py tests/conftest.py tests/test_conftest_quota_env_isolation.py
   python tools/check_loc_budget.py --json
   python tools/snapshot_sync.py --check
   ```
7. 真跑（AC-SBR-008；**額度 reset 後於互動視窗**，不要在 `--pace` 顯示任一訂閱軸 ≥95% 時跑）：`bash <SB>/run_clean.sh r1 orig`，再 `bash <SB>/run_clean.sh r2 patched`（需先 `python tools/session_resume_planner.py --pace` 現查）。腳本把專案根與 cwd 合一、放在筆記目錄之外、config 每鍵明寫、跑完稽核巢狀 claude 有無越界讀檔；`<SB>` 若已消失，照本檔 §2.2～§2.3 與 §3 D-SBR-01 參考實作重建。寫證據檔。**（v1.2：已完成——實際跑 C1～C4，取代原定的 `orig`／`patched` 兩跑；入庫 fixture 與 `config.template.yaml` 在 `scripts/bridge_e2e/wordcount/`，指令與結果見證據檔 §1～§4。）**
8. 缺陷入帳：D-SBR-01～04、08、09 修復列。**P4 理論洞依範本規則登記於證據檔〈13〉，不入缺陷帳本；帳本只收 P≤3 修復列與 P≤2 未結列**——D-SBR-05～07、證據檔 O-1～O-4 與 TH-01～TH-11 都屬此類（各附再開症狀）。唯一例外是證據檔 O-5 所指的底層缺口（Kernel 路徑 ESCALATION 不產 dump／通知／演化提案）：症狀已在 C4 實際發生，依範本規則改入缺陷帳本 DEF-200-518（open）。

---

## 7. 誠實劃界

- 只在 macOS、只用 haiku（`claude` 2.1.296）。run1 作廢（污染＋額度硬 halt）；**乾淨真跑已做 4 次**（證據檔 C1～C4：含驗收閘 3 次成功、修前對照 1 次 ESCALATION）。樣本數很小、AI 行為是機率性的，證據檔不宣稱任何失敗率，也不宣稱「驗收閘保證通過」。仍未驗證：D-SBR-04（`--fsm-state-path` 預檢）與 D-SBR-09（額度軸 halt 的 log）沒有真跑層證據（只有單元測試；真跑的額度水位 10～12%，未觸發任何 halt）；D-SBR-08 的現象層只有 C2 一次且無修前對照；D-SBR-03 的 exit=2 現象未復現（見 §2.7）。
- 污染是我的實驗設計錯誤（把探針與筆記放在 AI 讀得到的同一棵樹）；`run_clean.sh` 的隔離與稽核是補救，稽核為啟發式（路徑字面比對），不是證明。
- 凍結不是純 CLI：狀態目錄以一行賦值導向 scratchpad（§2.2）；CLI 自身沒有可指定狀態檔的出口，這屬 SDD 側事實，本案不處理（N6）。
- Windows（cmd.exe 下含雙引號的 `-k "AT_…"`、wexpect／cp950）未驗證；Brain 開啟（MiniMax）路徑未驗證；E2E／Integration／Contract 測試型別（retry 2／5 映射）未經真跑，只驗 Unit；「連字號 `-k` 被接受」只在 pytest 9.1.1 驗過。
- 構造的 regex 輸入（§2.5c）與原型測試（§2.8）只說明 regex 語意與測試設計，不是對模型行為的量測。
- 探針與 run1 在額度「停止帶」（weekly_all／seven_day 95%）執行，其結論只作歷史；補丁版的行為結論一律以證據檔 C1～C4（額度 band=free）為準。
