# AutoClaude_Improving_001 — Mock-First 閉環狀態機實作計畫

**文檔版本**: v1.2
**建立日期**: 2026-04-29
**更新日期**: 2026-04-30
**狀態**: ✅ Completed（含 QA 閉環修復）
**執行角色**: dev-developer (首席 AI 基礎設施工程師)

---

## 📋 任務背景

AutoClaude 已完成以下核心模組（58 tests pass）：
- `autoclaude/execution/playbook_runner.py` — STATE 0-5 多步驟狀態機
- `autoclaude/perception/pty_wrapper.py` — Windows PTY/subprocess I/O 包裝器
- `autoclaude/decision/minimax_client.py` — Minimax 修正決策客戶端
- `autoclaude/utils/checkpoint_manager.py` — 斷點續傳管理
- `autoclaude/utils/token_tracker.py` — Token 使用率追蹤與 compact/halt

**本次任務目標**：補齊 Mock-First 測試環境的 3 個交付物：
1. `dummy_cli.py` — 模擬目標 CLI 工具（含授權提示、flush、stderr）
2. `io_interceptor.py` — 跨平台非阻塞 I/O 攔截器（獨立模組）
3. `autoclaude_core.py` — 精簡狀態機引擎（整合上述兩者，目標指向 dummy_cli.py）
4. `autoclaude_playbook.yaml` — 至少 2 步驟的測試劇本
5. 對應單元測試

---

## 🔴 Self-Verification (Chain of Thought)

### 問題 1：`dummy_cli.py` stdout buffer 卡住問題

**分析**：
- Python subprocess 模式下，若 child process 使用 `print()` 但 stdout 未設為 line-buffered，輸出會積累在緩衝區，直到緩衝區滿或程式結束才 flush。
- 這會導致主程式 readline 永遠讀不到輸出 → **死鎖**。

**解決方案**：
```python
# dummy_cli.py 啟動時設定行緩衝
import sys
sys.stdout.reconfigure(line_buffering=True)
# 或每次 print 加 flush=True
print("[INIT_DONE]", flush=True)
```
- 另外，呼叫端可以使用 `python -u dummy_cli.py`（unbuffered mode）。
- `io_interceptor.py` 啟動子程序時加 `-u` 旗標確保安全。

### 問題 2：STATE 3 EVALUATION 的 ANSI 顏色代碼處理

**分析**：
- Claude Code 等 CLI 工具輸出包含 ANSI escape codes（顏色、游標移動等）。
- 若直接對含 ANSI 的輸出跑 regex，可能誤匹配或漏掉 keyword。
- 例如：`\x1B[32m[INIT_DONE]\x1B[0m` 若 regex 為 `\[INIT_DONE\]` 則可以匹配，但若有其他控制字元插入則不行。

**解決方案**：在 EVALUATE 前先 strip ANSI：
```python
import re
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub('', text)
```

---

## 📦 交付物清單

> **實作說明**：部分交付物整合至既有模組（詳見備註欄），而非獨立新增檔案。

### Step 1：建立 Mock 環境與規格

- [x] `tests/fixtures/mock_playbook.yaml` — 3 步驟測試劇本（T01/T02/T03），含 Prompt 與 Expected Keyword
- [x] `tests/fixtures/dummy_cli.py` — 模擬 CLI 工具
  - [x] `input()` 接收 stdin
  - [x] 延遲 1-2 秒（`time.sleep`）
  - [x] 隨機授權提示（Y/n，`AUTH_RANDOM_PROB=0.6`），只接受 'y'/'Y'
  - [x] 成功輸出 keyword（stdout）— `[INIT_DONE]`, `[TEST_CREATED]`, `[TASK_COMPLETE]`, `[PONG]`
  - [x] 失敗輸出錯誤訊息（stderr）
  - [x] 啟動時設定 line-buffering（`sys.stdout.reconfigure`）

### Step 2：開發 I/O 攔截器

> **備註**：原規劃為獨立 `io_interceptor.py`，實際整合至既有 `autoclaude/perception/pty_wrapper.py`。

- [x] `autoclaude/perception/pty_wrapper.py` — `PtyWrapper` 類別（含 I/O 攔截功能）
  - [x] 使用 `subprocess.Popen` + `-u` 旗標（wexpect 可選）
  - [x] `NonBlockingStreamReader` 獨立執行緒讀取 stdout（避免死鎖）
  - [x] 自動偵測授權提示模式（`auth_patterns`），寫入 `auth_response`
  - [x] `strip_ansi(text)` 工具函式（ANSI strip 在 readline 前執行）
  - [x] `send(cmd)` 方法（寫入 stdin + flush）
  - [x] `readline(timeout)` 非阻塞讀取
  - [x] `close()` 優雅關閉（terminate + 執行緒 join）

### Step 3：開發狀態機引擎

> **備註**：原規劃為獨立 `autoclaude_core.py`，實際整合至既有 `autoclaude/execution/playbook_runner.py`。

- [x] `autoclaude/execution/playbook_runner.py` — `PlaybookRunner` 類別（STATE 0-5 狀態機）
  - [x] STATE 0 (INIT): 讀取 YAML 劇本，驗證 Pydantic 模型
  - [x] STATE 1 (CONTEXT_NEGOTIATION): 送出初始 Prompt，等待 `expected_keyword` 確認（QA 修復：原實作遺漏，已補入 `_run_steps()` 前置段落）
  - [x] STATE 2 (SEQUENTIAL_EXECUTION): 依序送出步驟 prompt
  - [x] STATE 3 (EVALUATION): strip ANSI → regex 比對 → 失敗包裝重送給 Minimax
  - [x] STATE 4 (CONTEXT_RESET): 每 `auto_compact_interval` 步驟送 `/compact`
  - [x] STATE 5 (ESCALATION): 超過 `max_retries` 凍結並發送桌面通知，回傳 `success=False`
  - [x] `dry_run=True` 模式：跳過真實 CLI，以 regex keyword 合成輸出（供單元測試使用）

### Step 4：單元測試

- [x] `tests/test_io_interceptor.py` — 感知層 I/O 單元測試
  - [x] `TestStripAnsi`：8 個測試案例，涵蓋顏色碼、粗體、游標移動、keyword 存活驗證
  - [x] `TestPtyWrapper`：10 個測試案例，涵蓋 readline、EOF、send、授權自動回應（含 ANSI）、is_alive、close、自訂授權 pattern
- [x] `tests/test_autoclaude_core.py` — PlaybookRunner 狀態機引擎單元測試
  - [x] `TestPlaybookModelNewFields`：6 個測試，驗證 `command`、`context_negotiation` 欄位與 YAML 載入
  - [x] `TestPlaybookRunnerEvaluate`：4 個測試，驗證 `_evaluate()` ANSI strip 邏輯
  - [x] `TestPlaybookRunnerDryRun`：6 個測試，涵蓋單步驟/多步驟成功路徑、step_log、FileNotFoundError
  - [x] `test_escalation_on_max_retries`：ESCALATION 觸發驗證（mock PtyWrapper）
  - [x] `TestPlaybookResultRepr`：repr 格式驗證
  - [x] `TestContextNegotiationRunner`：4 個測試，驗證 CONTEXT_NEGOTIATION 執行行為（dry_run 略過、無 CN 不受影響、keyword 找到繼續、keyword 缺失失敗）

### Step 5：更新文件

- [x] `CLAUDE.md` — 已加入 AutoClaude 專案說明、核心目錄結構、模型欄位說明、PlaybookRunner 關鍵行為、測試執行指令、Mock CLI 整合測試說明

---

## 🏗️ 架構圖（最終實作版）

```
tests/fixtures/mock_playbook.yaml
         │
         ▼
  autoclaude/execution/playbook_runner.py (PlaybookRunner, STATE 0-5)
         │ 實例化（dry_run=False 時）
         ▼
   autoclaude/perception/pty_wrapper.py (PtyWrapper)
         │ 啟動子程序
         ▼
    tests/fixtures/dummy_cli.py (Mock CLI Target)
```

**資料流**：
```
YAML 劇本 → INIT → NEGOTIATE → EXECUTE[step_i]
                                    │
                          ┌─────────┴─────────┐
                          │                   │
                      成功輸出            失敗/auth提示
                          │                   │
                      EVALUATE          auto_respond(Y)
                          │                   │
                      regex 匹配         包裝錯誤重送
                          │
                    next_step or DONE
```

---

## 🔧 技術決策

| 決策項目 | 選擇 | 原因 |
|---------|------|------|
| I/O 機制 | `subprocess.Popen` + `Thread` | Windows 跨平台，wexpect 可選但 subprocess 更穩定 |
| 緩衝區問題 | `python -u` 啟動 + `flush=True` | 雙重保障確保即時輸出 |
| ANSI 處理 | regex strip 在 EVALUATE 前執行 | 不影響原始日誌，只影響 regex 匹配 |
| 狀態機設計 | `Enum` + Pydantic `dataclass` | 類型安全，易於 debug |
| 日誌 | `logging` + `RotatingFileHandler` | 與現有 logger.py 一致 |
| 模組整合 | 整合至既有 `pty_wrapper.py` / `playbook_runner.py` | 避免重複抽象，符合 CLAUDE.md 規範 |

---

## ⏱️ 執行紀錄

| 項目 | 狀態 | 備註 |
|------|------|------|
| 執行計畫建立 | ✅ 完成 | 本文件 (v1.0) |
| `tests/fixtures/dummy_cli.py` | ✅ 完成 | 含 line-buffering、auth prompt、COMMAND_MAP |
| `autoclaude/perception/pty_wrapper.py`（I/O 攔截） | ✅ 完成 | 整合 strip_ansi、NonBlockingStreamReader、auth 自動回應 |
| `tests/fixtures/mock_playbook.yaml` | ✅ 完成 | 3 步驟（T01/T02/T03） |
| `autoclaude/execution/playbook_runner.py`（狀態機） | ✅ 完成 | STATE 0-5 + dry_run 模式 |
| `tests/test_io_interceptor.py` | ✅ 完成 | 18 個測試案例 |
| `tests/test_autoclaude_core.py` | ✅ 完成 | 23 個測試案例（含 4 個 CONTEXT_NEGOTIATION 執行行為測試） |
| `CLAUDE.md` 更新 | ✅ 完成 | 已加入完整架構說明 |
| **QA 閉環修復** | ✅ 完成 | Bug1: 補實作 CONTEXT_NEGOTIATION；Bug2: PtyWrapper.close() 加 reader join |
