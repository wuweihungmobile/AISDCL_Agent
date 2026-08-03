# AutoSDD_improving_87 backlog — Brain 指揮 Claude Code self-correction 閉環真跑驗證

> **性質**：improving_87 前期規劃 backlog（非正式計畫書——正式 `AutoSDD_improving_87.md` 於動工那輪走規格先行時建）。
> **來源**：掌舵者 2026-06-27 明確指定排入（「Minimax 指揮 Claude Code 的測試案例……這個才是機制能否正常 work 的重要一環」），選「兩條都排（先 mock 驗機制、再真 Minimax 驗品質）」。
> **柱位**：C 軌（指揮官 AutoClaude 自身能力，self-correction loop 接線）× A 軌（端到端真跑驗證）。對齊北極星第 1 點（AutoClaude＝以狀態機管理重試／錯誤升級的引擎）。

---

## 1 背景與盲區（為何重要）

AutoClaude 的核心價值＝**狀態機管理執行流程／重試／錯誤升級**：Executor（Claude Code）執行失敗 → Brain（Minimax）介入產生 CORRECTION 修正 prompt → Executor 帶新 prompt 重試。這是 self-correction loop，是「圖靈完備自動化閉環」的關鍵環節。

**盲區（improving_86 同源 pattern：資產備好但沒端到端串起來真跑）**：
- 歷輪所有真跑（improving_72/77/86）皆 `enable_kernel_brain: false` + smoke playbook 一次過（first_pass 100%、CORRECTION=0）→ **「Brain 指揮 Executor 修正」這條閉環在真跑下從未被走過**，只有單元測試（FakeBrain）+ 紙上覆蓋。
- 既有資產盤點：`tools/mock_brain_server.py`（高擬真本地 Brain mock，OpenAI-compatible、與 `minimax_client._parse_response` 契約一致）**已備且有單元測試** `tests/tools/test_mock_brain_server.py`；但**缺**：(a) 會觸發 CORRECTION 的故意失敗 playbook；(b) 「mock brain + 真 Claude Executor」端到端 correction 真跑測試/腳本（`tests/integration/` 零命中）。

## 2 關鍵設計區分（機制接線 vs 真模型品質）

「Minimax 指揮 Claude Code」閉環 5 環節：①真 Claude 執行失敗 → ②Kernel 呼叫 Brain → ③Brain 回 CORRECTION → ④Kernel 把修正 prompt 餵回 Executor → ⑤真 Claude 改行為重試。
- **機制（接線）能否 work ＝ ①②④⑤ 是否真串起來**——與 ③ 的 Brain 是真 Minimax 或 mock **無關**。
- 用 **mock brain + 真 Claude**：①②④⑤ 全真，③ 確定性 mock → **精準驗「機制接線」、確定性、可重複、可進 CI、零憑證零成本**。
- 用 **真 Minimax + 真 Claude**：額外驗 ③「真模型修正品質」——引入模型不確定性，驗「修正得好不好」而非「機制接線」。

## 3 W 項

| W 項 | 軌道 | 內容 | 前提 |
|------|------|------|------|
| **W-87-1**（主案例，可進 CI） | C 軌 × A 軌 | mock brain 當指揮官 + 真 Claude Executor 的 correction 閉環真跑：建故意失敗 playbook + config 接 `mock_brain_server`（`base_url=localhost:9100`、`enable_kernel_brain:true`）+ 驗證載具/整合測試 | 無（mock 零憑證、本機 claude 訂閱已驗可用） |
| **W-87-2**（條件觸發，驗品質） | A 軌 | 真 Minimax + 真 Claude smoke：同 playbook 接真 Minimax 驗修正品質 | **需掌舵者提供 `MINIMAX_API_KEY`（環境目前無）**；無憑證據實 PENDING（improving_68 紀律、不假裝） |

## 4 測試案例設計藍圖

### 4.1 故意失敗 playbook（`scripts/correction_loop_smoke.yaml`，待建）
- S01：prompt 故意誤導 Claude 寫一個**會被 evaluator 擋下的實作**（例如要求「先寫一個刻意有 off-by-one bug 的 `add`」或 prompt 模糊），`evaluator_command` 嚴格 pytest → 第一次 attempt 必失敗。
- CORRECTION：Kernel 呼叫 Brain → Brain 回明確修正 prompt（mock server 的 correction 回應刻意滿足 Hallucination Guard：≥50 字元、含 `.py`/line、每次變化）→ Claude 帶新 prompt 改對 → 第二次成功。
- `max_retries` 設足（如 2~3），確保有修正空間；但也須測「修正方向明確到 Claude 必改對」避免 flaky。

### 4.2 config（待建 `scripts/ab_configs/correction_mock_config.yaml`）
```yaml
minimax:
  base_url: "http://localhost:9100/v1/chat/completions"
  api_key: "mock"
  enable_kernel_brain: true        # 🔴 關鍵：開 Brain（與既有 A/B config 的 false 相反）
executor:
  backend: "pty"                   # 真 Claude CLI
claude:
  extra_args: ["--permission-mode", "bypassPermissions"]
storage:
  mode: "yaml_only"
```

### 4.3 驗證載具/整合測試
- 啟動 mock_brain_server（背景）→ 真跑 playbook → 解析 log。
- 確認：log 含 `=== STATE: CORRECTION | step=... ===`（Brain 真被呼叫）＋ mock server 收到 ≥1 次 POST（Brain 端有互動）＋ 最終 `success=True`（修正後成功）。

## 5 RTM 雛形

| RTM | 意圖（守什麼） |
|-----|--------------|
| RTM-87-1 | correction 閉環真跑：log 含 STATE: CORRECTION marker（Brain 真被 Kernel 呼叫、非死碼） |
| RTM-87-2 | 指揮真的傳達：修正後 Executor 收到的 prompt ≠ 原 prompt（Brain 的 correction_prompt 真的接回 Executor） |
| RTM-87-3 | 閉環收斂（誠實兩態）：修正後最終 success；或達 max_retries 誠實 escalate（不虛報成功） |
| RTM-87-4（W-87-2 條件） | 真 Minimax 修正品質：首次失敗後真 Minimax 回的修正使其通過（條件觸發、需憑證） |

## 6 前提 / 風險

- **真 Minimax 憑證**：環境無 `MINIMAX_API_KEY`、config.local 僅 DB 設定 → W-87-2 條件觸發、無憑證 PENDING（不假裝，improving_68）。
- **mock server correction 內容**：須確認 `mock_brain_server` 的 correction 回應能讓真 Claude 真的改對（可能需調 mock 回應或 playbook 設計使「修正方向夠明確」）。
- **真 Claude 行為變異（flaky 風險）**：playbook 須設計成「第一次因明確原因失敗、修正方向明確到 Claude 必改對」，否則端到端真跑會 flaky；mock 路線可多輪驗穩定性。
- **階段一 (f) 紀律**：mock_brain_server 是 HTTP 本地服務（非 GUI/PATH CLI），可 headless 啟動（已確認 `--port 9100` + `/health`）。

## 7 既有資產（可重用，免重造）
- `tools/mock_brain_server.py`：高擬真 Brain mock（已備、有單元測試）。
- `tools/ab_compare_backends.py`：log 解析載具（improving_71~86，可重用 CORRECTION 計數 / run_backend 真跑）。
- `scripts/sdd_bridge_smoke.yaml`：可作 correction playbook 的改造起點。
