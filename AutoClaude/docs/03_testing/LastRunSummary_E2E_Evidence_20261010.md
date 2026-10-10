# F-LRS-001 `--last-run-summary` 端到端真跑證據（2026-10-10，macOS）

> 對應規格：[../01_requirements/FRD_Last_Run_Summary.md](../01_requirements/FRD_Last_Run_Summary.md)。
> 這是「AutoClaude 驅動真實開發」北極星 A 柱的**第一次真跑**：引擎以 `claude --model haiku` 跑完一支兩步 playbook，
> 再由新旗標讀回落檔摘要。所有產物只落在 session scratchpad（不入庫）；本檔逐字抄錄機器輸出。

## 1. 設定（模型釘 haiku、Brain off、產物落暫存）
- config：`executor.backend: pty`（macOS 無 wexpect ⇒ 自動改 subprocess 模式）、`claude.extra_args: ["--permission-mode", "bypassPermissions", "--model", "haiku"]`、`minimax.enable_kernel_brain: false`、`log_dir`／`checkpoint_dir` 指向 scratchpad。
- playbook：T01 建 `calc.py`（`add(a, b)`）；T02 寫 `test_calc.py` 並以 `evaluator_command: python -m pytest test_calc.py -q` 雙重驗收。
- 指令：`python -m autoclaude e2e_playbook.yaml --config e2e_config.yaml --fresh`（cwd＝工作目錄）。

## 2. 引擎實際組出的 claude 指令（log 逐字，prompt 省略）
```
['claude', '--permission-mode', 'bypassPermissions', '--model', 'haiku', '--output-format', 'json', '-p', '<prompt>']
```

## 3. 引擎結束行（log 逐字）
```
Playbook 結束 | KernelResult(success=True, completed_steps=2, total_steps=2, reason='success', step_log=['[T01] 建立 calc.py ✓ (attempt 1)', '[T02] 撰寫並通過 pytest ✓ (attempt 1)'], completed_step_ids=['T01', 'T02'], halted=False, escalated=False, veto_reasons=[], contributors=[], workflow='', scheduled_resume_at=None, evolved_playbook_path=None, evolution_fresh_required=False, halt_step_idx=None, peak_token_pct=6.7158)
e2e_rc=0
```
STEP_TOKEN_PEAK：T01 pct=4.4086、T02 pct=6.7158；T02 評估 `評估通過 [exit=0]`。工作目錄產物：`calc.py`、`test_calc.py`、`__pycache__/`。

## 4. 落檔 `<log_dir>/last_run_summary.json`（逐字）
```json
{
  "schema_version": 1,
  "status": "finished",
  "playbook": "/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/06ddd1a2-a1e9-4c74-b282-f13ef6548a0c/scratchpad/e2e_work/e2e_playbook.yaml",
  "started_at": "2026-10-10T11:18:41+00:00",
  "finished_at": "2026-10-10T11:19:01+00:00",
  "duration_seconds": 19.6,
  "outcome": "success",
  "success": true,
  "escalated": false,
  "halted": false,
  "reason": "success",
  "total_steps": 2,
  "completed_steps": 2,
  "halt_step_idx": null,
  "peak_token_pct": 6.72,
  "scheduled_resume_at": null,
  "veto_reasons": []
}
```

## 5. `python -m autoclaude --last-run-summary --config e2e_config.yaml`（stdout 逐字，rc=0）
```
最近一次執行摘要
Playbook：/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/06ddd1a2-a1e9-4c74-b282-f13ef6548a0c/scratchpad/e2e_work/e2e_playbook.yaml
開始時間：2026-10-10 19:18:41+08:00（耗時 19.6 秒）
結果：成功（SUCCESS）
步驟：通過 2 / 共 2 步
token 峰值：6.7%
ESCALATION：否
```

## 6. 誠實劃界
- 只在 macOS 真跑；Windows（pty／wexpect 路徑、cp950 主控台）未驗證。
- 本次只覆蓋「成功」結局的真跑；ESCALATION／TOKEN_HALT／running 三態由 `tests/cli/test_last_run_summary.py` 以替身 AutoResumeService 回傳預組 KernelResult 覆蓋（未經 Kernel、未用真 claude 重現）。
- 查詢路徑 stderr 會印一行 `wexpect 未安裝，改用 subprocess 模式…`（main.py 既有 import 鏈的平台提示，非本功能新增；stdout 不受影響，AC-LRS-001 以 subprocess 測試釘住）。

## 7. QA 零信任審查結果（Sonnet 唯讀鏡，2026-10-10）：VERDICT APPROVE
- 全套 `python -m pytest tests/ -q`：全綠、0 failed（通過／略過的計數不在本檔重抄，基線唯一出處＝根層 ONBOARDING.md §7 表②；略過者為 PG 未啟動與 Windows 專屬）；42 個突變全數被測試擊殺；既有三種 CLI 呼叫形態與 HEAD 逐字相同（stdout／stderr／rc）。
- P3 四條皆當輪就地處置：QA-01 本檔 §6 措辭；QA-02 FRD 狀態與預估值；QA-03 `auto_resume.py` 存 HALT checkpoint 的降級分支對真實後端為死分支（實況 fail-loud），改註解如實描述、刻意不擴攔；QA-04 測試檔區段標號跳號。
- P4 兩條已順手修（一行級）：QA-05 讀檔只攔 JSONDecodeError（構造的 5000 位整數會印 Traceback）→ 攔 `(ValueError, RecursionError)`；QA-06 fsync 時 KeyboardInterrupt 留 `.tmp` 孤兒 → BaseException 清 tmp 後 re-raise。
- **理論洞清單（P4，只登記；各附可觀測再開症狀）**：
  - QA-07 `--fresh` 續跑語意假設「halt 一定存了本 run 的 checkpoint」；生產兩處產 halted 皆帶 halt_step_idx、存檔失敗為崩潰，故不可達。再開症狀：`--fresh` 的 AUTO_RESUME 第二輪印「從檢查點繼續」而本 run 從未印「已存 token HALT checkpoint」。
  - QA-08 `FileStateRepository.clear_checkpoint` 只 unlink 主檔，保留版本 `.v1～.v5` 留在磁碟（load 回 None、無症狀）。再開症狀：log 出現「checkpoint 損毀…已退回保留版本」且其 step_idx 早於最近一次成功完成。
  - QA-09 `newline="\n"` 的 LF 斷言在 macOS 盲（只有 AST 鎖 `test_no_new_text_write_sites_without_explicit_newline` 與 Windows CI 承擔）。再開症狀：Windows 上 `last_run_summary.json` 含 `\r\n`。
  - QA-10 `test_sliced_sleep.py` 四支改後對「halt 等待被整個跳過」失去專屬鑑別力（續跑輪補睡同一段，加總不變；全套仍由 `test_auto_resume_halt_persist.py` 殺得到）。再開症狀：該四支全綠而 `test_auto_resume_loop_waits_instead_of_burning_every_retry_at_once` 紅。
