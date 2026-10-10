# F-SBR-001 SDD 橋接鏈乾淨真跑證據（2026-10-11，macOS）

> 對應規格：[../01_requirements/FRD_Sdd_Bridge_Real_Run.md](../01_requirements/FRD_Sdd_Bridge_Real_Run.md)（AC-SBR-008）。
> 這是橋接鏈（`TEST-CONTRACT-SPEC` → 真 FSM CLI 凍結 → `sdd_compile` → `python -m autoclaude`〔真 claude／haiku＋真 pytest evaluator〕→ RtmWritebackPlugin → `--last-run-summary`）第一次**乾淨隔離**的真跑；規格 §2.6 那次探針真跑已作廢，與本檔無關。
> 共真跑 4 次（`C1`～`C4`＝隔離目錄 `r1`～`r4`）：**C1** 主流程、**C2** 負向觀察（規格在 cwd 之外）、**C3** 主流程重跑、**C4** 修前對照（以 `git archive HEAD` 的編譯器編出**不含驗收閘**的 playbook；引擎、config、其餘欄位同版）。產物只落在隔離目錄與巢狀 claude 的逐字稿（皆不入庫）；本檔逐字抄錄機器輸出——`<ISO>` 是隔離根目錄 `/private/tmp/claude-501/sbr_iso_5535e815` 的縮寫、`~` 是使用者家目錄的縮寫，其餘不改。

## 1. 設定（模型釘 haiku、Brain off、cwd＝含規格的專案根）
- 環境：macOS（Darwin 25.6.0）、Python 3.11.15、`claude` 2.1.296、pytest 9.1.1；模型一律 `haiku`（`--model haiku`）。引擎開機自檢逐字：`開機自檢 | CLI 2.1.296 不在逐版清單、同家族 2.1.x 已驗證至 2.1.295 ⇒ 視為已驗證（patch 級差異不進 DRY_RUN）`。
- 入庫 fixture：`scripts/bridge_e2e/wordcount/`（`TEST-CONTRACT-SPEC-WordCount.md`，sha256 `0de6845eee4e1d63532a76aebd5049651f8e5fa061599d0b84aeeb9fe110f742`；2 AC／3 AT、全 Unit）。每次真跑都由入庫檔複製進隔離專案並驗 sha256。
- config：入庫範本 `config.template.yaml` 把 `__RUN_DIR__` 代換成 `<ISO>/rN`，**不列任何 `*_pct` 門檻**。解析後逐字（C1 的 `config_resolved.txt`；C2～C4 僅路徑不同）：
```
claude.command = claude
claude.extra_args = ['--permission-mode', 'bypassPermissions', '--model', 'haiku']
minimax.enable_kernel_brain = False
executor.backend = pty
storage.mode = yaml_only
playbook.goal_synthesis_enabled = False
token_guard.enabled = True
token_guard.halt_threshold_pct = 90.0
token_guard.quota_halt_pct = 98.0
token_guard.auto_resume = False
notification.enabled = False
log_dir = <ISO>/r1/logs
checkpoint_dir = <ISO>/r1/checkpoints
```
- `token_guard.quota_halt_pct = 98.0` 來自本機未入庫的 `.env`（`AUTOSDD_QUOTA_HALT_PCT`），config 不覆寫它；腳本預檢用的是同一個值（引擎自己的 `read_worst_pct()` 對引擎有效門檻），所以預檢與引擎行為一致。
- 額度：每次真跑前以 `python tools/session_resume_planner.py --pace` 現查——四次的最大水位依序 10%／11%／11%／12%（全軸 band=free；引擎額度 halt 門檻以 `config_resolved.txt` 為準——本機 98.0、出廠 95；「任一軸 ≥90% 即不跑」是本輪自訂的操作規則，不是引擎門檻）；腳本開頭另以引擎的量測器預檢，逐字：`read_worst_pct=10.0 kind=session quota_halt_pct=98.0`（C1）。
- 隔離：專案根與引擎 cwd 合一（C1／C3／C4；C2 刻意分開，見 §9）、放在與任何筆記目錄無關的 `<ISO>`；Brain 關閉（引擎 log 逐字：`未設定 MINIMAX_API_KEY：Brain 相關能力（步驟 correction／goal synthesis／自演化提案）本次停用，playbook 仍會照常執行`）；`--fresh`；`executor.backend: pty` 在 macOS 自動改 subprocess 模式（stderr 一行 `wexpect 未安裝，改用 subprocess 模式…` 屬正常提示）。
- C4 的編譯器：`PYTHONPATH` 指向 `git archive HEAD` 展開的鏡像（三支生產碼 `sdd_to_playbook_adapter.py`／`sdd_compile.py`／`policy.py` 經 `cmp` 與 `git show HEAD:` 逐位元組相同），只用於 `sdd_compile` 這一步；引擎本身仍是現行版。C4 與 C1 的 playbook 比對：`step_id`／`expected_output_regex`／`evaluator_command`／`max_retries`／`maintain_context`／`weak_regex`／`spec_digest` 逐欄相同，**唯一差異是 prompt 不含「驗收閘」段**。

## 2. 指令序列（逐字；C1 為例；C2 另設 `OUTSIDE=1`、C4 另設 `COMPILE_PYTHONPATH`，見 §1、§9、§10）
```bash
# 凍結：真 FSM CLI 入口（fsm_runtime._cli），狀態目錄以一行賦值導向專案根（FRD §2.2；驅動器 drive_fsm_cli.py 為不入庫的暫存腳本）
cd AISDLC_SDD/AISDLC_SDD_v0.30 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 python <drive_fsm_cli.py> <ISO>/r1/proj
# 編譯
python -m autoclaude.tools.sdd_compile --spec-dir <ISO>/r1/proj/docs --out <ISO>/r1/playbook.yaml --project wordcount_sbr
# 真跑（cwd＝<ISO>/r1/proj）
env -u MINIMAX_API_KEY PATH="<repo>/.venv/bin:$PATH" python -m autoclaude <ISO>/r1/playbook.yaml --config <ISO>/r1/config.yaml --fresh
# 讀回
env -u MINIMAX_API_KEY PATH="<repo>/.venv/bin:$PATH" python -m autoclaude --last-run-summary --config <ISO>/r1/config.yaml
```
上列四步由 `run_clean.sh` 串起（另含額度預檢、config 代換、規格 sha256 驗證與事後稽核；暫存腳本不入庫，見 §12）。四次真跑的呼叫差異只有環境變數與 run 名（皆在 repo 根執行、已 `source <repo>/.venv/bin/activate`）：
```bash
ISO_ROOT=<ISO> bash ~/.autosdd/plans/sbr_artifacts_5535e815/run_clean.sh r1 orig   # C1
OUTSIDE=1 ISO_ROOT=<ISO> bash ~/.autosdd/plans/sbr_artifacts_5535e815/run_clean.sh r2 orig   # C2：規格樹 <ISO>/r2/proj 與引擎 cwd <ISO>/r2/work 分開（§9）
ISO_ROOT=<ISO> bash ~/.autosdd/plans/sbr_artifacts_5535e815/run_clean.sh r3 orig   # C3
COMPILE_PYTHONPATH=<HEAD-mirror>/AutoClaude ISO_ROOT=<ISO> bash ~/.autosdd/plans/sbr_artifacts_5535e815/run_clean.sh r4 orig   # C4：只有「編譯」那一步改用 HEAD 版編譯器（§10）
# <HEAD-mirror> 的建法：mkdir -p <HEAD-mirror> && git -C <repo> archive HEAD AutoClaude tools .env.example | tar -x -C <HEAD-mirror>
```
凍結階段輸出（C1 `freeze_stdout.txt` 逐字，`show` 的 JSON 省略，其 `current_state` 為 `SPEC_FROZEN`；`AISDLC_SDD` 的 `git status --porcelain` 為空）：
```
$ python -m tools.fsm_runtime.fsm_runtime transition --to SCENARIO_DETECT --project wordcount_sbr
OK transitioned to SCENARIO_DETECT
[rc=0]
$ python -m tools.fsm_runtime.fsm_runtime transition --to AGENT_LOAD --project wordcount_sbr
OK transitioned to AGENT_LOAD
[rc=0]
$ python -m tools.fsm_runtime.fsm_runtime transition --to SPEC_DRAFTING --project wordcount_sbr
OK transitioned to SPEC_DRAFTING
[rc=0]
$ python -m tools.fsm_runtime.fsm_runtime transition --to SCG_VALIDATION --project wordcount_sbr
OK transitioned to SCG_VALIDATION
[rc=0]
$ python -m tools.fsm_runtime.fsm_runtime transition --to HUMAN_PENDING --project wordcount_sbr
OK transitioned to HUMAN_PENDING
[rc=0]
$ python -m tools.fsm_runtime.fsm_runtime spec-frozen --stage Stage-2 --doc docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md --project wordcount_sbr
OK spec frozen: Stage-2
[rc=0]
$ python -m tools.fsm_runtime.fsm_runtime show --project wordcount_sbr
[rc=0]
```

## 3. 引擎實際組出的 claude 指令（log 逐字；prompt 另列）
C1 共啟動 5 次 `claude`。`--continue` 只出現在步驟 2（`maintain_context: true`）；引擎在**每個步驟第 1 個 attempt** 的 prompt 前加總目標錨點（步驟 1 是長版 `=== 本次自動化任務的總目標 ===`，步驟 2、3 是一行 `[總目標方向] …`），重試不再帶：


| # | 時間 | 對應 | argv（不含 prompt） |
|---|------|------|--------------------|
| 1 | 02:46:49 | 步驟 1 attempt 1 | `['claude', '--permission-mode', 'bypassPermissions', '--model', 'haiku', '--output-format', 'json', '-p']` |
| 2 | 02:47:08 | 步驟 2 attempt 1 | `['claude', '--permission-mode', 'bypassPermissions', '--model', 'haiku', '--continue', '--output-format', 'json', '-p']` |
| 3 | 02:47:21 | 步驟 2 attempt 2 | `['claude', '--permission-mode', 'bypassPermissions', '--model', 'haiku', '--continue', '--output-format', 'json', '-p']` |
| 4 | 02:47:30 | 步驟 2 attempt 3 | `['claude', '--permission-mode', 'bypassPermissions', '--model', 'haiku', '--continue', '--output-format', 'json', '-p']` |
| 5 | 02:47:40 | 步驟 3 attempt 1 | `['claude', '--permission-mode', 'bypassPermissions', '--model', 'haiku', '--output-format', 'json', '-p']` |

C1 步驟 1 送給 claude 的完整 prompt（引擎組出，逐字；含引擎加的「總目標」錨點）：
```
=== 本次自動化任務的總目標 ===
完成 greenfield 場景全部 3 條 AT 契約（規格 digest 0de6845e）
以上為整體目標供你參考，請確保每個步驟的實作決策與此目標方向一致。
===========================

依下列契約實作並使測試通過：
# AT-001-1-1
# 對應 AC: AC-001-1 以空白分隔、不分大小寫統計每個單字的出現次數
# 測試類型: Unit
# 自動化工具: pytest

Feature: WordCount 詞頻統計

Scenario: 重複單字被累計且不分大小寫
  Given 輸入文字 "The cat and the hat"
  When 呼叫 wordcount(text)
  Then 回傳字典中「the」的次數為 2
  And 「cat」的次數為 1
規格出處：<ISO>/r1/proj/docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md（digest 0de6845e）
驗收閘（由引擎親自執行，AI 自稱完成不算）：
1. 程式與測試一律建立在「目前工作目錄」之下；規格出處只供閱讀，不要因它的路徑而把檔案寫到別處。
2. 完成前請在目前工作目錄親自執行評估指令，須通過（以裸 pytest 執行，不是 python -m pytest）：pytest tests -k "AT_001_1_1" -q
   測試檔須放在 tests/ 下，且測試函式、類別或檔名須含 AT_001_1_1（例：def test_AT_001_1_1_basic），否則 -k 篩選會選到 0 個測試而失敗。
3. 你的最後一則回覆須符合此 regex（Python re.search；(?=.*X) 表示須含 X、(?!.*X) 表示全文不得含 X，引述也算）：(?s)(?=.*the)(?=.*cat)
```

對照：C4（修前編譯器）步驟 1 的 prompt（逐字，無驗收閘）：
```
=== 本次自動化任務的總目標 ===
完成 greenfield 場景全部 3 條 AT 契約（規格 digest 0de6845e）
以上為整體目標供你參考，請確保每個步驟的實作決策與此目標方向一致。
===========================

依下列契約實作並使測試通過：
# AT-001-1-1
# 對應 AC: AC-001-1 以空白分隔、不分大小寫統計每個單字的出現次數
# 測試類型: Unit
# 自動化工具: pytest

Feature: WordCount 詞頻統計

Scenario: 重複單字被累計且不分大小寫
  Given 輸入文字 "The cat and the hat"
  When 呼叫 wordcount(text)
  Then 回傳字典中「the」的次數為 2
  And 「cat」的次數為 1
規格出處：<ISO>/r4/proj/docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md（digest 0de6845e）
```

## 4. 四次真跑總表
| 真跑 | 用途 | prompt | engine rc | KernelResult | 各步 attempt | 耗時 | RTM 落檔 | 巢狀 claude tool_use 數／越界次數（允許根＝run 目錄）／越界次數（允許根＝cwd） |
|------|------|--------|-----------|--------------|--------------|------|----------|------------------------------------------------|
| C1 | 主流程（cwd＝專案根） | 含驗收閘 | 0 | success=true，3/3 步 | 1／3／1 | 67.0 秒 | 有 | 17／0／0 |
| C2 | 負向觀察（規格在 cwd 之外） | 含驗收閘 | 0 | success=true，3/3 步 | 1／2／1 | 56.5 秒 | 有 | 16／0／3 |
| C3 | 主流程重跑 | 含驗收閘 | 0 | success=true，3/3 步 | 1／1／1 | 43.9 秒 | 有 | 8／0／0 |
| C4 | 修前對照 | 無驗收閘（HEAD 編譯器） | 1 | ESCALATION，0/3 步 | —（步驟 1 失敗 2 次） | 29.2 秒 | **無**（`checkpoints/` 為空） | 8／0／0 |

三次含驗收閘的真跑**全部** `success=True`（步驟 1、3 在每次都是第 1 個 attempt 就過；步驟 2 的 attempt 數為 3／2／1，原因見 §8）；唯一不含驗收閘的 C4 在步驟 1 **ESCALATION**，原因見 §10。C2 的 strict 稽核「3 次越界」皆為讀取 prompt 明示的規格路徑，見 §9。

## 5. 引擎結束行（log 逐字）
**C1**（`rc.txt`＝0）：
```
2026-10-11 02:47:56 [INFO] autoclaude: Playbook 結束 | KernelResult(success=True, completed_steps=3, total_steps=3, reason='success', step_log=['[sdd-greenfield-at-001-1-1] AT-001-1-1 ✓ (attempt 1)', '[sdd-greenfield-at-001-1-2] AT-001-1-2 ✓ (attempt 3)', '[sdd-greenfield-at-002-1-1] AT-002-1-1 ✓ (attempt 1)'], completed_step_ids=['sdd-greenfield-at-001-1-1', 'sdd-greenfield-at-001-1-2', 'sdd-greenfield-at-002-1-1'], halted=False, escalated=False, veto_reasons=[], contributors=[], workflow='', scheduled_resume_at=None, evolved_playbook_path=None, evolution_fresh_required=False, halt_step_idx=None, peak_token_pct=12.8756)
```
**C2**（`rc.txt`＝0）：
```
2026-10-11 02:50:50 [INFO] autoclaude: Playbook 結束 | KernelResult(success=True, completed_steps=3, total_steps=3, reason='success', step_log=['[sdd-greenfield-at-001-1-1] AT-001-1-1 ✓ (attempt 1)', '[sdd-greenfield-at-001-1-2] AT-001-1-2 ✓ (attempt 2)', '[sdd-greenfield-at-002-1-1] AT-002-1-1 ✓ (attempt 1)'], completed_step_ids=['sdd-greenfield-at-001-1-1', 'sdd-greenfield-at-001-1-2', 'sdd-greenfield-at-002-1-1'], halted=False, escalated=False, veto_reasons=[], contributors=[], workflow='', scheduled_resume_at=None, evolved_playbook_path=None, evolution_fresh_required=False, halt_step_idx=None, peak_token_pct=13.0242)
```
**C3**（`rc.txt`＝0）：
```
2026-10-11 02:52:30 [INFO] autoclaude: Playbook 結束 | KernelResult(success=True, completed_steps=3, total_steps=3, reason='success', step_log=['[sdd-greenfield-at-001-1-1] AT-001-1-1 ✓ (attempt 1)', '[sdd-greenfield-at-001-1-2] AT-001-1-2 ✓ (attempt 1)', '[sdd-greenfield-at-002-1-1] AT-002-1-1 ✓ (attempt 1)'], completed_step_ids=['sdd-greenfield-at-001-1-1', 'sdd-greenfield-at-001-1-2', 'sdd-greenfield-at-002-1-1'], halted=False, escalated=False, veto_reasons=[], contributors=[], workflow='', scheduled_resume_at=None, evolved_playbook_path=None, evolution_fresh_required=False, halt_step_idx=None, peak_token_pct=12.9161)
```
**C4**（`rc.txt`＝1）：
```
2026-10-11 02:55:44 [INFO] autoclaude: Playbook 結束 | KernelResult(success=False, completed_steps=0, total_steps=3, reason='[sdd-greenfield-at-001-1-1] 評估指令失敗 (exit=5): pytest tests -k "AT_001_1_1" -q', step_log=[], completed_step_ids=[], halted=False, escalated=True, veto_reasons=[], contributors=[], workflow='', scheduled_resume_at=None, evolved_playbook_path=None, evolution_fresh_required=False, halt_step_idx=None, peak_token_pct=0.0)
```
C1 的 STEP_TOKEN_PEAK／評估行（log 逐字；步驟 2 的 attempt 1、2 之後**沒有**「執行評估指令」行＝失敗發生在第一層 regex，見 §8）：
```
02:47:08 [INFO] autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=sdd-greenfield-at-001-1-1 pct=12.1683 ===
02:47:08 [INFO] autoclaude.execution.evaluator: 執行評估指令: pytest tests -k "AT_001_1_1" -q (timeout=120s)
02:47:08 [INFO] autoclaude.execution.evaluator: 評估通過 [exit=0]
02:47:21 [INFO] autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=sdd-greenfield-at-001-1-2 pct=5.7843 ===
02:47:30 [INFO] autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=sdd-greenfield-at-001-1-2 pct=6.2275 ===
02:47:39 [INFO] autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=sdd-greenfield-at-001-1-2 pct=6.5022 ===
02:47:39 [INFO] autoclaude.execution.evaluator: 執行評估指令: pytest tests -k "AT_001_1_2" -q (timeout=120s)
02:47:40 [INFO] autoclaude.execution.evaluator: 評估通過 [exit=0]
02:47:56 [INFO] autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=sdd-greenfield-at-002-1-1 pct=12.8756 ===
02:47:56 [INFO] autoclaude.execution.evaluator: 執行評估指令: pytest tests -k "AT_002_1_1" -q (timeout=120s)
02:47:56 [INFO] autoclaude.execution.evaluator: 評估通過 [exit=0]
```

## 6. 工作目錄產物（AI 寫的檔案）
C1（專案根＝cwd）的 `tree_after.txt` 逐字：
```
--- proj tree (P=<ISO>/r1/proj):
./build/reports/fsm/FSM-STATE-wordcount_sbr.yaml
./build/reports/fsm/FSM-STATE-wordcount_sbr.yaml.bak
./docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md
./tests/conftest.py
./tests/test_AT_001_1_1.py
./tests/test_AT_001_1_2.py
./tests/test_AT_002_1_1.py
./wordcount.py
```
三次含驗收閘的真跑，AI 一律把測試放在 `tests/`、且檔名或函式名含底線 token（C1：`tests/test_AT_001_1_1.py` 等、函式 `test_AT_001_1_1_…`；C2：同形；C3：`tests/test_AT_001_1_1_wordcount.py` 等、函式 `test_AT_001_1_1_…`）。裸 pytest 匯入差異由 AI 自行處理：C1 補 `tests/conftest.py`（逐字如下，註解是 AI 寫的），C2／C3 補根目錄 `pytest.ini`（`pythonpath = .`）。
```python
import os
import sys

# 讓測試可以 import 專案根目錄下的模組（例如 wordcount），不依賴 python -m pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```
```ini
[pytest]
pythonpath = .
testpaths = tests
```

## 7. RTM 逆向報告與 `--last-run-summary`
C1 的 `<checkpoint_dir>/rtm/`（C2、C3 的三個檔與 C1 **逐位元組相同**；C4 沒有這個目錄）：
`RTM-COVERAGE-wordcount_sbr.yaml`（逐字）：
```yaml
kind: rtm-coverage
scenario: greenfield
spec_digest: sha256:0de6845eee4e1d63532a76aebd5049651f8e5fa061599d0b84aeeb9fe110f742
summary:
  total_at: 3
  passed_at: 3
  at_coverage_pct: 100.0
  total_ac: 2
  covered_ac: 2
  ac_coverage_pct: 100.0
  fully_covered: true
ac_coverage:
- ac_id: AC-001-1
  passed_at: 2
  total_at: 2
- ac_id: AC-002-1
  passed_at: 1
  total_at: 1
failed_at_ids: []
weak_regex_at_ids:
- AT-002-1-1
```
`RTM-GAP-wordcount_sbr.md`（逐字）：
```markdown
# RTM Gap Analysis — greenfield

- AT 覆蓋率：3/3（100.0%）
- AC 覆蓋率：2/2（100.0%）
- SCG-5 RTM 閘門：✅ 通過（100% AC 覆蓋）

> 全部 AC/AT 已覆蓋，無 gap。
```
`RTM-COVERAGE-HISTORY-wordcount_sbr.jsonl` 另有一行同內容的 JSON（略）。`weak_regex_at_ids: [AT-002-1-1]` 即該 AT 的 Gherkin 推不出可驗斷言、退回 `\bPASS(ED)?\b`。

C1 的 `<log_dir>/last_run_summary.json`（逐字）：
```json
{
  "schema_version": 1,
  "status": "finished",
  "playbook": "<ISO>/r1/playbook.yaml",
  "started_at": "2026-10-10T18:46:49+00:00",
  "finished_at": "2026-10-10T18:47:56+00:00",
  "duration_seconds": 67.0,
  "outcome": "success",
  "success": true,
  "escalated": false,
  "halted": false,
  "reason": "success",
  "total_steps": 3,
  "completed_steps": 3,
  "halt_step_idx": null,
  "peak_token_pct": 12.88,
  "scheduled_resume_at": null,
  "veto_reasons": []
}
```
C1 的 `python -m autoclaude --last-run-summary --config <config>`（stdout 逐字，rc=0）：
```
最近一次執行摘要
Playbook：<ISO>/r1/playbook.yaml
開始時間：2026-10-11 02:46:49+08:00（耗時 67.0 秒）
結果：成功（SUCCESS）
步驟：通過 3 / 共 3 步
token 峰值：12.9%
ESCALATION：否
```
C2、C3 的同一指令 stdout 為 `結果：成功（SUCCESS）`、`步驟：通過 3 / 共 3 步`（耗時 56.5／43.9 秒、token 峰值 13.0%／12.9%）；C4 的見 §10。

## 8. 步驟 2（AT-001-1-2）為什麼 C1 要 3 次、C2 要 2 次：失敗在第一層 regex，不在程式碼
AT-001-1-2 的 Gherkin 含負向斷言（`鍵中不應出現帶標點的單字，例如「hello,」`），推導出的 `expected_output_regex` 是 `(?s)\A(?=.*hello)(?!.*hello,)`——它驗的是 **AI 的最後一則回覆文字**：必須含 `hello`、全文不得含 `hello,`。引擎 log 沒有任何一行記載 attempt 失敗的原因（見 §13 O-1），下表是對 `playbook_<step>.log` 裡每次 attempt 的 claude `result` 以同一條 regex 做 `re.search` 重算（與 `ShellEvaluator` 的第一層同判準）：

| 真跑 | attempt | regex 重算 | 含 `hello` | 含 `hello,` | 回覆中造成結果的句子（逐字節錄） |
|------|---------|-----------|-----------|------------|----------------------------------|
| C1 | 1 | **不符** | 是 | 是 | `` …so it has exactly 2 keys and no `hello,`. ``（在說明測試時引述了被禁字串） |
| C1 | 2 | **不符** | 否 | 否 | `` The gate regex forbids the punctuated form anywhere in this reply, so I have not written it out. ``（過度修正：整則回覆連 hello 都沒寫） |
| C1 | 3 | 符合 | 是 | 否 | `` …covers the key count, the count for `hello`, and the absence of the punctuated form. ``（含 hello、無 `hello,`） |
| C2 | 1 | **不符** | 是 | 是 | `` …checks that the result has exactly 2 keys, that `hello` maps to 2, that no key `hello,` exists… ``（引述被禁字串） |
| C2 | 2 | 符合 | 是 | 否 | （回覆不含 `hello,`、含 hello） |
| C3 | 1 | 符合 | 是 | 否 | `` …checks that the result has exactly 2 keys, that "hello" appears 2 times, and that the punctuated forms are absent. `` |

判讀：
- 程式與測試從第 1 次 attempt 起就是對的（C1 attempt 3 的 `評估通過 [exit=0]` 只是第一次輪到 evaluator 跑）；失敗的是「回覆文字要同時含 `hello`、又不能含 `hello,`」。AI 在回覆裡**明確知道這條規則**（C1 attempt 1 的結尾寫：`The gate regex requires the reply to contain "hello" and not contain "hello," anywhere, so I kept the phrasing in this reply to satisfy it.`——這句話本身就含 `hello,`）。驗收閘第 3 條告知了契約，但沒有擋住引述；擋不住的原因是結構性的——Gherkin 的負向斷言描述的是函式輸出（字典鍵），推導規則卻把它變成對 AI 回覆文字的約束，而「說明測試在驗什麼」恰好最自然地引述那個字串。
- Brain 關閉時 retry 不帶失敗回饋（D-SBR-07）：C1 attempt 2 與 3 的 prompt 逐字相同（離線以 `ast` 還原 log 的 argv 後比對，兩者相等；attempt 1 只多一行 `[總目標方向]` 錨點），AI 靠 `--continue` 的對話脈絡自己修正，第 2 次修過頭（整則回覆沒寫 hello）、第 3 次才碰對。
- 代價：額外 1～2 次 attempt（每次約數秒、不到 0.01 美元），未耗盡 `max_retries=5`；三次含驗收閘的真跑沒有任何一次因此失敗。

## 9. 負向觀察（C2）：規格放在 cwd 之外時，AI 是否仍把檔案寫在 cwd
設計：規格與凍結狀態在 `<ISO>/r2/proj`，引擎 cwd 是空目錄 `<ISO>/r2/work`（playbook 的 `workflow_path` 與 prompt 的「規格出處」都指向 `proj`——這正是 D-SBR-08 的情境）。結果（C2 `tree_after.txt` 逐字）：
```
--- proj tree (P=<ISO>/r2/proj):
./build/reports/fsm/FSM-STATE-wordcount_sbr.yaml
./build/reports/fsm/FSM-STATE-wordcount_sbr.yaml.bak
./docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md
--- cwd tree (W=<ISO>/r2/work):
./pytest.ini
./tests/test_AT_001_1_1.py
./tests/test_AT_001_1_2.py
./tests/test_AT_002_1_1.py
./wordcount.py
```
規格樹 `proj` 沒有任何 AI 產生的檔案（只有規格與 FSM 狀態）；AI 的所有檔案都在 cwd `work`（含 `pytest.ini` 的 `pythonpath = .`），引擎在 cwd 跑 `pytest tests -k "AT_…" -q` 三步皆過。驗收閘第 1 條（「程式與測試一律建立在目前工作目錄之下；規格出處只供閱讀」）在此情境**有效**（樣本數 1）。
稽核（`audit_nested_transcript.py`，啟發式）——允許根＝run 目錄（`audit_nested.txt`，逐字）：
```
## ~/.claude/projects/-private-tmp-claude-501-sbr-iso-5535e815-r2-work/597a72ee-4e34-4fde-9747-0013cac4f57f.jsonl
## ~/.claude/projects/-private-tmp-claude-501-sbr-iso-5535e815-r2-work/80793cb5-dbf9-406e-9b2b-623c259d13fd.jsonl
tool_use 共 16 次；越界 0 次 ⇒ 乾淨
audit_rc=0
```
允許根＝cwd（`audit_nested_strict_cwd.txt`，逐字）：
```
## ~/.claude/projects/-private-tmp-claude-501-sbr-iso-5535e815-r2-work/597a72ee-4e34-4fde-9747-0013cac4f57f.jsonl
  越界 call#1 Bash: ['<ISO>/r2/proj/docs/03_testing/contracts/']
  越界 call#2 Read: ['<ISO>/r2/proj/docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md']
## ~/.claude/projects/-private-tmp-claude-501-sbr-iso-5535e815-r2-work/80793cb5-dbf9-406e-9b2b-623c259d13fd.jsonl
  越界 call#8 Bash: ['<ISO>/r2/proj/docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md']
tool_use 共 16 次；越界 3 次 ⇒ 有越界（不可當乾淨證據）
audit_rc=3
```
strict 版的 3 次「越界」全是**讀取** prompt 明示的規格路徑（巢狀逐字稿：`ls …/contracts/`、`Read …/TEST-CONTRACT-SPEC-WordCount.md`、`cat …/TEST-CONTRACT-SPEC-WordCount.md`），沒有任何寫入；C2 這個佈局本來就要求 AI 讀 cwd 之外的規格，所以 strict 判準對 C2 不適用，C1／C3／C4 的 strict 稽核為 0 次越界。

## 10. 修前對照（C4）：不含驗收閘的 prompt，真 claude 的自然行為
C4 的 playbook 與 C1 只差 prompt（見 §1）。結果：**步驟 1 ESCALATION，0/3 步**，rc=1。引擎 log 逐字（評估階段）：
```
02:55:31 [INFO] autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=sdd-greenfield-at-001-1-1 pct=10.1978 ===
02:55:31 [INFO] autoclaude.execution.evaluator: 執行評估指令: pytest tests -k "AT_001_1_1" -q (timeout=120s)
02:55:31 [WARNING] autoclaude.execution.evaluator: 評估失敗 [exit=5]
1 deselected in 0.06s
02:55:44 [INFO] autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=sdd-greenfield-at-001-1-1 pct=9.6960 ===
02:55:44 [INFO] autoclaude.execution.evaluator: 執行評估指令: pytest tests -k "AT_001_1_1" -q (timeout=120s)
02:55:44 [WARNING] autoclaude.execution.evaluator: 評估失敗 [exit=5]
1 deselected in 0.06s
```
（結束行見 §5。）
AI 的測試是 `tests/test_wordcount.py::test_repeated_words_are_counted_case_insensitively`（自然命名，不含 `AT_001_1_1`），而引擎的評估指令是 `pytest tests -k "AT_001_1_1" -q`——`-k` 選到 0 個測試（`1 deselected`）、exit=5，與 FRD §2.4 的 layout d 矩陣列完全一致。AI 自己用 `python3 -m pytest tests/test_wordcount.py -v` 驗過所以自認完成；第 1 次 attempt 的 regex 第一層（`(?=.*the)(?=.*cat)`）碰巧通過，才輪到 evaluator 紅。
第 2 次 attempt（Brain 關閉、不帶失敗回饋）AI 回報 `The implementation and test were already in the project, so I ran the test rather than writing new code.`，同一個特徵碼（exit=5、`1 deselected`）連續出現 2 次，ESCALATION 在 `max_retries=5` 用完之前就發生。log 沒有直接記載升級原因；`KernelResult.reason` 的格式是 `[<step_id>] <失敗原因>`（Kernel 的 `request_escalation` 分支所寫，retry 用盡的分支會寫成 `max_retries_exhausted: …`），加上特徵碼連續 2 次相同，與原始碼的 `FailureTracker.is_stuck(consecutive_threshold=2)` → ConvergenceMonitor 回 `escalate` → ConvergencePlugin 要求升級這條路徑一致（程式路徑推斷，未另以除錯 log 證實）。
`--last-run-summary`（C4 stdout 逐字，rc=0）與 `last_run_summary.json`：
```
最近一次執行摘要
Playbook：<ISO>/r4/playbook.yaml
開始時間：2026-10-11 02:55:15+08:00（耗時 29.2 秒）
結果：失敗（ESCALATION）；原因：[sdd-greenfield-at-001-1-1] 評估指令失敗 (exit=5): pytest tests -k "AT_001_1_1" -q
步驟：通過 0 / 共 3 步
token 峰值：未記錄（此結果型態不攜帶 token 峰值）
ESCALATION：是
```
```json
{
  "schema_version": 1,
  "status": "finished",
  "playbook": "<ISO>/r4/playbook.yaml",
  "started_at": "2026-10-10T18:55:15+00:00",
  "finished_at": "2026-10-10T18:55:44+00:00",
  "duration_seconds": 29.2,
  "outcome": "escalation",
  "success": false,
  "escalated": true,
  "halted": false,
  "reason": "[sdd-greenfield-at-001-1-1] 評估指令失敗 (exit=5): pytest tests -k \"AT_001_1_1\" -q",
  "total_steps": 3,
  "completed_steps": 0,
  "halt_step_idx": null,
  "peak_token_pct": 0.0,
  "scheduled_resume_at": null,
  "veto_reasons": []
}
```
C4 的 `<checkpoint_dir>` 是空目錄、`rtm/` 不存在：逆向 RTM 報告在失敗的 run 完全不落檔（D-SBR-05 的實況，見 §13）；同一個空目錄也表示**沒有 escalation dump**（見 §13 O-5）。

## 11. 逐缺陷判讀（只寫本次真跑看得到的）
| 缺陷 | 真跑觀察 | 判讀 |
|------|----------|------|
| D-SBR-01 命名／位置（H1） | C4（修前）：自然命名 → `-k` 選 0 個測試 → exit=5 → 同特徵碼 2 次 → ESCALATION。C1～C3（含驗收閘）：三次 × 三步，測試檔名或函式名一律含底線 token，步驟 1、3 的 evaluator 皆第 1 個 attempt 即過 | 修前的失敗現象**在真 claude 上復現**（樣本數 1）；FRD §2.7 的升級條款（「乾淨重跑若見命名／位置失敗則升 P1」）已觸發，主控已裁決 D-SBR-01 由 P2 升 P1（FRD §3） |
| D-SBR-02 輸出契約（H2） | 引號正向與 weak 型：AI 依 prompt 在回覆含 `the`／`cat`、並在回覆中寫出大寫 `PASSED`（C1 為末行單獨一行），三次皆第 1 個 attempt 通過。負向型（AT-001-1-2）：三次中兩次第 1 個 attempt 因回覆引述 `hello,` 而在 regex 層失敗（§8） | 「交付契約」有效；負向型殘留的是推導語意問題（regex 約束 AI 回覆文字、卻源自 Gherkin 對函式輸出的描述），不是措辭問題（N1 禁區，需另案裁決） |
| D-SBR-03 裸 pytest（H3） | AI 自行補 `tests/conftest.py`（C1，註解自述「不依賴 python -m pytest」）或 `pytest.ini` 的 `pythonpath = .`（C2、C3）；C4 的 AI 在測試檔內 `sys.path.insert` 自救，失敗原因是 exit=5 而非 exit=2 | 裸 pytest 匯入差異在含驗收閘的三次真跑都被 AI 預先處理；C4 沒踩到 exit=2（AI 的自救方式剛好避開），因此 H3 的 exit=2 現象本次**未**真跑復現 |
| D-SBR-08 工作目錄（H4） | C2：規格在 cwd 之外，AI 檔案全在 cwd、規格樹零新增檔 | 驗收閘第 1 條在該情境有效（樣本數 1）；C1／C3／C4 的 cwd＝專案根，不能區分 |
| D-SBR-04 `--fsm-state-path`、D-SBR-09 額度軸 halt 點名 | 真跑未涉及（沒有 `--fsm-state-path`；額度水位 10～12% 未觸發任何 halt） | 僅由單元測試覆蓋；真 halt 場景的 log 行為**未**在真跑觀察 |

## 12. 誠實劃界
- 只在 macOS、只用 haiku（`claude` 2.1.296）；Windows（cmd.exe 引號、wexpect／cp950）未驗證。只覆蓋 Unit 型 AT（retry 5）；E2E／Integration／Contract（retry 2／5 映射）未經真跑。
- Brain 關閉；Brain 開啟（MiniMax）路徑未驗證。
- 樣本數很小：含驗收閘 3 次（其中 1 次佈局不同）、修前對照 1 次。AI 行為是機率性的（AT-001-1-2 的 attempt 數是 3／2／1），本檔不宣稱任何失敗率，也不宣稱「驗收閘保證通過」——只陳述這 4 次的逐字結果與可重算的判讀。
- C4 是「同一個引擎、同一份 config、只換 prompt」的單次對照；它證明修前失敗現象**可在真 claude 上出現**，不證明它**必然**出現。
- 巢狀 claude 以 `--permission-mode bypassPermissions` 執行，實際上可讀寫任何路徑；隔離靠「目錄與無關」加事後稽核。稽核腳本是啟發式（比對 tool_use 內的絕對路徑字面與 Bash 的 `../`），不是證明；巢狀逐字稿在 `~/.claude/projects/-private-tmp-claude-501-sbr-iso-5535e815-r{1..4}-{proj,work}/`。AI 讀了專案內的 `build/reports/fsm/FSM-STATE-wordcount_sbr.yaml`（C1 第 3 個、C4 第 2 個 tool_use），屬專案樹內，未計為越界。
- 額度預檢與引擎有效門檻同為 98.0（來自本機 `.env`）；本機 `.env` 不入庫，別台機器的預設是 95，哪個值生效以 `config_resolved.txt` 為準。
- `rtm/` 內三份檔案在 C1～C3 逐位元組相同，是因為三次的結局（3/3 AT 通過、weak 只有 AT-002-1-1）相同，不是因為報告不看內容。
- §3 的 argv／prompt 還原與 §8 的 regex 重算，都是離線讀隔離目錄內 log 的臨時腳本（不入庫）；輸入檔逐字保留在隔離目錄。本檔不含任何 pytest 通過／略過的總數（`1 deselected` 是 `-k` 篩掉單一測試的機器輸出行，不是基線數字）。
- **本檔的可重放性與暫存腳本**：`run_clean.sh`（串起 §2 的指令序列、額度預檢、config 代換、事後稽核）、`drive_fsm_cli.py`（凍結驅動器）、`audit_nested_transcript.py`（§9 稽核）、`make_patched_playbook.py`（本輪未用）都是不入庫的暫存腳本（FRD N7）。真跑用的**修改版** `run_clean.sh` 正本是 `~/.autosdd/plans/sbr_artifacts_5535e815/run_clean.sh`（sha256 `b43a624e61719471ebd2a4e4d6a8319bac368ff49b1b9b94bcd1f2e4640fa044`；同目錄另存其餘三支腳本與規格 fixture）。該檔最後一次修改在 2026-10-11 02:54:49（加入檔頭 (E) 的 `COMPILE_PYTHONPATH` 開關，預設為空、不改編譯行為），所以 C4 用的是這一版，C1～C3 用的是 02:46:05 的版本（與正本只差那一處，中間版本未另存）。工作階段暫存區內另有一份**修改前**的原版（明寫 `quota_halt_pct: 95.0`），**不是**真跑用的版本。重放依據是本檔 §1 的 config 解析結果與 §2 的逐字指令與呼叫，不是那些腳本；腳本內寫死了本機 repo 路徑，凍結步驟「狀態目錄導向專案根」的那一行賦值也只在 `drive_fsm_cli.py` 內（文字描述見 FRD §2.2）。

## 13. 理論洞清單（只登記、不在本輪處理；各附可觀測再開症狀）
> 登記規則：P4 理論洞依範本規則（根層 `docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`〈終止條件・休眠・再開〉與 `docs/06_quality/FiveQuestion_Audit_Protocol/severity.md`〈暴露度〉）登記於本證據檔〈13〉，**不入缺陷帳本；帳本只收 P≤3 修復列與 P≤2 未結列**。每條附一個**超出本輪觀察**的可觀測再開症狀：該症狀實際發生時，才依暴露證據升 P2 並入帳。「本輪已見弱形態」＝本輪真跑已看到較輕的同類現象（附位置），但未達再開門檻。
- **D-SBR-05**（P4，登記不修）逆向 RTM 報告只在 run 正常走完才落檔（`rtm_writeback_plugin.py` 只訂閱 POST_RUN，plugin docstring 已把它文件化為設計取捨）。C4 已實測：失敗的 run 之後 `<checkpoint_dir>` 是空目錄、`rtm/` 不存在（§10）。失敗當下**實際可查**的來源只有兩處：`--last-run-summary` 的失敗原因行，與 `autoclaude.log` 的評估失敗行（C4：`評估失敗 [exit=5]`）；**沒有 escalation dump**（見 O-5）——降 P4 的理據因此是「這兩處來源足以判斷失敗原因」，不是「有 dump 可查」。本輪已見的是狀態（C4 的 `rtm/` 不存在），尚未見「操作者需要覆蓋快照而查不到」。再開症狀：真跑 ESCALATION／TOKEN_HALT 後，操作者需要「已覆蓋哪些 AC／AT」的快照，而 `rtm/` 為空。
- **D-SBR-06**（P4，登記不修）`_scenario_of` 以子字串猜場景。本次規格含 greenfield 字樣，三處（編譯、執行、RTM）一致為 `greenfield`，沒有觀察到錯標。再開症狀：RTM 報告或 step_id 前綴（`sdd-<場景>-…`）的場景標籤與規格宣稱不符而造成誤判。
- **D-SBR-07**（P4，登記不修）Brain 關閉時重試不帶失敗回饋。**本輪已見弱形態**：C4 步驟 1 的第 2 次 attempt 與第 1 次除了錨點行之外 prompt 相同、AI 因而回報測試與實作「已經在專案裡」、只重跑測試而沒有改程式（§10 逐字），同一個失敗特徵碼連續 2 次後升級；C1 步驟 2 的第 2、3 次 prompt 逐字相同，AI 靠 `--continue` 的對話脈絡自己修正（§8）。兩例都未達門檻：C4 是**刻意不含驗收閘**的修前對照，C1 在 `max_retries` 內自癒。再開症狀（超出本輪觀察）：**含驗收閘的 playbook** 上，同一步 `max_retries` 用盡或 ESCALATION，而重送的 prompt 不含任何失敗資訊。
- **O-1**（P4，新觀察）Brain 關閉時 attempt 失敗的**原因不落 log**：regex 層失敗在 `autoclaude.log` 只有 `STEP_TOKEN_PEAK`、沒有「輸出未符合期望 regex」那一行，只能從「兩個 STEP_TOKEN_PEAK 之間沒有 `autoclaude.execution.evaluator` 的『執行評估指令:』行」推論；本檔 §8 是離線重算才確定原因。**本輪已見弱形態**：C1 步驟 2（連續 2 次 regex 層失敗後第 3 次通過）、C2 步驟 2（1 次失敗後通過）。再開症狀（超出本輪觀察）：同一步連續 ≥3 次 attempt 失敗、或 `max_retries` 用盡／ESCALATION，而操作者在 `autoclaude.log` 與 `last_run_summary.json` 都找不到第一層（regex）失敗的原因。
- **O-2**（P4，新觀察）負向引號斷言推導出的 `(?!.*X)` 約束的是 AI 的最後回覆文字（§8）：AI 說明自己的測試時最自然地引述 `X`。**本輪已見弱形態**：三次含驗收閘的真跑中 2 次（C1、C2 的步驟 2）第 1 個 attempt 因此在 regex 層失敗，皆在 `max_retries` 內自癒。再開症狀（超出本輪觀察）：含負向斷言的 AT 連續 ≥3 次 attempt 因同一原因在 regex 層失敗（log 的 STEP_TOKEN_PEAK 行數比 `autoclaude.execution.evaluator` 的「執行評估指令:」行數多），或 `max_retries` 在這一步被用盡／ESCALATION。
- **O-3**（P4，新觀察）引擎的 subprocess 路徑以 `stdin=subprocess.PIPE` 開 `claude -p`（供 `_auto_respond` 寫入），送出 prompt 後沒有關閉它，`claude` 每次都先等 3 秒才放棄 stdin：每個 `playbook_<step>.log` 在每次 attempt 前都有 `Warning: no stdin data received in 3s, proceeding without it.`（C1 共 5 次）。單次成本固定 3 秒、無功能影響。再開症狀：該警告出現，且某個步驟的牆鐘耗時接近「3 秒 × attempt 數」而 `duration_ms` 極短。
- **O-4**（P4，新觀察）`last_run_summary.json` 在 ESCALATION 的 `peak_token_pct` 為 `0.0`、`--last-run-summary` 印 `token 峰值：未記錄（此結果型態不攜帶 token 峰值）`（C4），而同一 run 的 log 其實有兩筆 `STEP_TOKEN_PEAK`（10.1978、9.6960）。再開症狀：失敗 run 的摘要說「未記錄」，操作者卻需要判斷失敗當下的 context 水位。
- **O-5**（P4〔指對本案的影響面〕，新觀察）Kernel 唯一正式路徑上的 ESCALATION，沒有任何 `ON_ESCALATION`／`ON_ESCALATION_DUMP_REQUEST` 的發布點（`autoclaude/core/kernel.py` 在 `StepAction.ESCALATE` 分支直接 `return KernelResult.escalated_(…)`；`autoclaude/` 內這兩個 phase 沒有任何發布端，只有枚舉定義、訂閱端與說明文字，`sdd_governance_plugin.py` 檔頭也自陳 `ON_ESCALATION` 是合法枚舉但 kernel 現況不派發），所以依賴它們的處理器——checkpoint 的 escalation dump、notification 的升級通知、knowledge_base 的升級紀錄、evolution 的演化提案——在這條路徑上不會被觸發；這與 `AutoClaude/CLAUDE.md` 對 ESCALATION 的描述（桌面通知＋`EscalationDump`＋`PlaybookEvolver` 嘗試自動演化）不符。C4 實測支持 dump 這一項：`<checkpoint_dir>` 是空目錄（`ls -la` 為 `total 0`）、`autoclaude.log` 對 `EscalationDump` 零命中、隔離目錄內沒有檔名含 `escalat` 或 `dump` 的檔案（`autoclaude.log` 只有各 plugin「訂閱 ON_ESCALATION」的啟動行）；通知、知識庫、演化提案三項只由原始碼推論（C4 的 config 關閉了 notification，也沒有另行檢查後兩者的產出）。此缺口早於本變更、不由本變更造成，且症狀已在 C4 實際發生，所以**底層缺口不留在理論洞清單，由缺陷帳本列 DEF-200-518（open）追蹤**；本條只登記它對本案的影響：D-SBR-05 原先「失敗時有 escalation dump 可查」的降級理據不成立（已改為上述兩處實際可查的來源）。再開症狀（針對這個影響面，超出本輪觀察）：失敗 run 的 `--last-run-summary` 與 `autoclaude.log` 兩處來源不足以讓操作者判斷失敗原因，而又沒有 dump、通知或演化提案可查。
- **TH-01**（P4，新觀察）D-SBR-08 的修法是 prompt 文字（驗收閘第 1 條），**不是機械約束**（`bypassPermissions` 下 AI 仍可寫任何路徑）；現象層驗證只有 C2 一次（樣本數 1），且**沒有修前對照**（HEAD 版編譯器＋規格在 cwd 之外沒跑）。再開症狀：bridge 真跑後 `git -C <規格樹> status --porcelain`（尤其規格在 `AISDLC_SDD/**`、引擎 cwd 在 `AutoClaude/`）出現 AI 產物，或 evaluator 在 cwd 回 rc=4（`ERROR: file or directory not found: tests`）。
- **TH-02**（P4，新觀察）Brain 開啟時 CORRECTION 會整個取代 `task.prompt`，`autoclaude/core/kernel.py` 的 `_preserve_output_contract` 只把 regex 補回；驗收閘第 1／2 條（cwd、命名、評估指令）不保證保留。本輪 Brain 全程關閉（§12）。再開症狀：`enable_kernel_brain=true` 的真跑，第 1 個 attempt（含驗收閘）已寫出測試，經 CORRECTION 後 evaluator 回 rc=5（`N deselected`）或 rc=4。
- **TH-03**（P4，新觀察）`-k` 是子字串比對：在隔離目錄實測 `pytest tests -k "AT_001_1_1"` 同時選到 `test_AT_001_1_10_basic`（一個失敗、一個通過，rc=1）。驗收閘要求名稱含底線 token，使 `…_1` 與 `…_10`／`…_11` 並存時互相污染（evaluator 模板屬 FRD N2 禁區，本案不改）；本輪規格只有 3 個 AT，碰不到。再開症狀：同一 AC 下 ≥10 個 AT 的規格，前面步驟的 evaluator 因後面 AT 的測試（resume 重跑或 AI 預寫）被多選進來而轉紅。
- **TH-04**（P4，新觀察）`--test-path` 給的是檔案時（evaluator 白名單的 `_SAFE_FRAGMENT` 允許檔案路徑），驗收閘印出「測試檔須放在 tests/test_wordcount.py/ 下」（以 `SddToPlaybookAdapter(test_path="tests/test_wordcount.py")` 編譯實測）。再開症狀：AI 依字面建出以 `.py` 結尾的資料夾。
- **TH-05**（P4，新觀察）`autoclaude/plugins/token_guard/policy.py` 屬 `AutoClaude/autoclaude/plugins/token_guard/**`，push 會觸發 `.github/workflows/autoclaude-mutation-on-change.yml`；其變異測試選集 `tests/plugins/token_guard` 沒有任何 `evaluate_quota`／`quota_meter`／`QuotaReading` 測試（`evaluate_quota` 本就未被選集覆蓋），D-SBR-09 新增的 `logger.warning` 的變異體預期存活；本案的新測試在 `tests/core`，選集看不到。再開症狀：push 後該 workflow 的 kill_rate 較前一筆 history 下降，或 `mutation_backlog_token_guard.md` 列出 `policy.py` 該行 survived。
- **TH-06**（非缺陷，登記備查）`test_fsm_state_outside_runtime_search_path_exit_code_2` 對 stderr 只斷言含子字串「執行期」，而預檢訊息內「執行期」出現兩處：突變實驗拿掉第一處測試仍綠，兩處都拿掉才紅。AC-SBR-006 字面只要求含「執行期」，故非缺陷。再開症狀：訊息被改寫成不再說明「執行期 PRE_RUN」找不到凍結狀態檔的原因，但別處仍帶「執行期」字樣而測試不紅。
- **TH-07**（P4，新觀察）本檔**不能單靠檔內內容重放**：`run_clean.sh`、`drive_fsm_cli.py`、`audit_nested_transcript.py`、`make_patched_playbook.py` 都是不入庫的暫存腳本（FRD N7）；真跑用的修改版 `run_clean.sh` 正本與其 sha256 見 §12，暫存區內修改前的原版仍明寫 `quota_halt_pct: 95.0`、與 §1 的 98.0 不同。重放依據是 §1 的 config 解析結果與 §2 的逐字指令與呼叫。再開症狀：他人依本檔重放，`config_resolved.txt` 的 `quota_halt_pct` 與 §1 不同（拿到了原版腳本），或凍結步驟因缺 `drive_fsm_cli.py` 的那一行賦值而把狀態檔寫進 `AISDLC_SDD` 樹內。
- **TH-08**（P4，新觀察）在 AutoClaude 子專案的 session 下，`AutoClaude/tools/hooks/enforce_docs_path.py`（PreToolUse／Write）的 `.md` 白名單不含 `scripts/**`：以 Write 工具修改 fixture（`scripts/bridge_e2e/wordcount/docs/03_testing/contracts/TEST-CONTRACT-SPEC-WordCount.md`）會被擋（`is_allowed_md` 對該路徑回 False；Bash 可繞）。fixture 有 sha256 釘著，修改本應走審查。再開症狀：Write 寫該 fixture 回 exit 2。
- **TH-09**（P4，新觀察）`test_the_engine_reads_no_env_file_during_a_test` 只釘**狀態**（`_ENV_FILES == ()`），不釘行為；今天 `_ENV_FILES` 是引擎唯一的 `.env` 讀取點（`autoclaude/utils/config.py`），所以兩者等價。再開症狀：`config.py` 新增第二個 `.env` 讀取點後，鎖仍綠，而有 `.env` 的機器上「出廠預設」類測試轉紅。
- **TH-10**（P4，新觀察）`test_a_literal_reader_of_the_prompt_passes_the_evaluator` 在測試內真 spawn 巢狀 `pytest`（沿用外層全部環境變數）；外層帶 `PYTEST_ADDOPTS` 或 coverage 環境變數時的行為未驗。再開症狀：CI 上該測試 rc≠0，且 stderr 出現 `unrecognized arguments` 或 coverage 訊息。
- **TH-11**（P4，新觀察）adapter `_build_evaluator_cmd` 的註解「pytest -k 表達式不接受連字號」對 pytest 9.1.1 已不成立（FRD §2.4 b／c 列 rc=0）；底線化仍必要（函式名不能含連字號）。再開症狀：有人據該註解或據 FRD §2.4 的判讀改動底線化，破壞「函式名不能含連字號」的命名指示（`test_evaluator_command_and_k_token_are_in_the_prompt` 與 `test_a_literal_reader_of_the_prompt_passes_the_evaluator` 會紅）。
