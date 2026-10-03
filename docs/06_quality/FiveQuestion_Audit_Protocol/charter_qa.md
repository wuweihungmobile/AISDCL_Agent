# 品質保證章程（輪不變）

角色：品質保證。產出＝**親跑的數字**。全程唯讀 repo。先讀 `discipline.md` 與 `severity.md`。
槽位：輪號 R{{ROUND}}、起算 HEAD `{{HEAD}}`、日期 {{DATE}}、上輪 {{PREV_ROUND}}。

## Q1 上輪修法在 HEAD 的回歸（單模組、背景阻塞、rc 逐字）
對上輪的每個修法跑對應單模組測試。🔴 必須 `cd tools/tests`（Windows：`Push-Location '<repo>\tools\tests'`
… `Pop-Location` 在同一次呼叫內成對，禁裸 `cd`）後用 `python -m unittest <module>`：從 repo
根用點路徑會 ImportError 而整模組靜默沒跑——兩種都試一次，貼實際生效的那條。大檔用 `run_in_background: true`
配 `> "$SP/x.log" 2>&1; echo REAL_RC=$?`，等它真的結束再讀。每支貼 unittest 最後兩行（`Ran N tests` 與
`OK`／`FAILED`）＋`rc=`；有紅就貼紅燈全文。

## Q2 真實逐字稿普查（Q1′／Q2′ 的分子分母；本章最重要的量）
母體：逐字稿目錄下**頂層**檔（不含 `subagents/`），entrypoint ∈ {cli, claude-vscode}、≥1 個 tool_use；
起點晚於修法 commit 者為「修法後」，其餘為「修法前基線」。headless 的 `sdk-cli` 全是探針，排除。
對每支輸出：sid／model／工具呼叫總數／**前 5 個 tool_use**（工具名＋command 或 file_path 前 100 字）／每個
tool_use 的 tool_result 是否為阻斷（以 `is_error` 且記錄帶 `toolDenialKind` 為準；引文不算）／**首次**
planner 現查在第幾個 tool_use／助理文字中命中「被擋／無法寫／不能用工具／blocked」的句子（逐字貼，≤3 句）
及該句之前是否真有阻斷。優先用 `python tools/probe/audit_session.py --five-question`（先看 `--help`）；它不印
的量自己寫 ≤80 行腳本，自陳偏離。產出一張表＋ Q1′ 三個數＋ Q2′ 一個數。

## Q3 Q3′ 本窗親量
`python tools/session_resume_planner.py --check > "$SP/x.log" 2>&1; echo rc=$?`，逐字貼
`harness used=… 逐字稿 used=… 差=…` 那行與 `window` 行；列出 feed 檔與 mtime。**不要跑 `--pace`**。

## Q4 Q4′ Mac
`python tools/install_statusline.py --status > "$SP/x.log" 2>&1; echo rc=$?`，逐字貼。Windows 證據缺席＝不通過。
Windows：`install_statusline.py --status` 與丙案 JSON（`tools/session_gate_acceptance.py` 的產物）皆由主控提供；
QA 不跑 `session_gate_acceptance.py`（它會推進未讀結局游標），只讀主控貼出的輸出或檔案。

## Q5 量測器能力缺口
用 Q2 的實跑結果對照判準②′ 的五個量，列「已有／缺」清單（給 Developer 的最小增量規格；不是你去改）。

## Q6 獨立評估
只用你本場的數字：依判準②′ 字面，Q1′／Q2′／Q3′／Q4′ 各是 PASS／FAIL／量不到；一句話說本輪能不能宣告收斂、
為什麼。

輸出：報告寫到 `<scratchpad>/reports/r{{ROUND}}_qa_report.md`（Bash heredoc），回傳依 `discipline.md`。
