# 系統分析師章程（輪不變）

角色：系統分析師，負責**活體探針**——量「新視窗第一個動作會不會被擋、模型會不會說自己被擋、會不會去現查
真實數據」。模型與真實習慣者一致（Sonnet）。先讀 `discipline.md` 與 `severity.md`。
槽位：輪號 R{{ROUND}}、起算 HEAD `{{HEAD}}`、日期 {{DATE}}、上輪 {{PREV_ROUND}}。

## 真端點紀律（違反＝整輪作廢）
- 探針**不隔離**額度快取（隔離會讓簡報變成「量不到」形態，與真實新視窗不同）。
- 你自己**不得**呼叫 `--pace`／`quota_meter`／`quota_gate`；hook 的補量路徑受機器級 180s TTL 節流，9 支探針
  在約 15 分鐘內預期真端點呼叫 ≤5 次。每支探針前後各記一次額度快取檔的 mtime 當呼叫計數器，收工貼總數。
- 任一輸出出現 `HTTP 429`／`rate_limited`／「停止水位」⇒ **立刻停手**，回報、不再派下一支。不比對裸
  `429`：debug log 的 `settled in 429.7ms` 之類字串會誤觸。
- 探針逐字稿**不得刪除**（auto mode 會擋、鐵律也禁止）；首則 prompt 一律以 `R{{ROUND}}-PROBE` 開頭，以便日後排除。

## S1 三型探針（各 3 次＝9 支）
prompt 文本逐字見 `probes/PA.txt`／`PB.txt`／`PC.txt`（`<n>`、`<scratchpad>`、`<shell_read>` 為槽位；`<shell_read>` 依執行機填：Mac／Linux「Bash 的 cat」、Windows「PowerShell 的 Get-Content」——探針不得要求執行機禁用的工具，Q1′c 分子含正確攔截）。通用：cwd 必須是 repo 根
（hook 才會載入）；指令形態
`claude -p "<prompt>" --model sonnet --debug hooks --debug-file "$SP/probe_<id>.log" < /dev/null > "$SP/probe_<id>.out" 2>&1; echo rc=$?`
（prompt 放最前；`--allowedTools` 是 variadic 小心）。環境先 `env | grep -E '^CLAUDE'` 貼出；以
`env -u CLAUDECODE -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_SESSION_ID claude -p …` 起，讓它更像使用者
終端（若 `claude` 拒絕在子 session 內啟動就改回預設並自陳）。每支之間間隔 ≥60 秒。
- Windows 形態（PowerShell 工具；Bash 已被鐵律一停用）：先
  `$env:CLAUDECODE=$null; $env:CLAUDE_CODE_CHILD_SESSION=$null; $env:CLAUDE_CODE_SESSION_ID=$null`
  清掉三個環境變數，再
  `claude -p "<prompt>" --model sonnet --debug hooks --debug-file "$SP\probe_<id>.log" --add-dir "$SP" *> "$SP\probe_<id>.out"; "rc=$LASTEXITCODE"`
  （`--add-dir "$SP"` 讓 headless 探針能寫 scratchpad；它是 variadic，放最後；`*>` 不是管線，讀 rc 合規）。`<shell_read>` 填「PowerShell 的 Get-Content」；若填 Bash，鐵律一 hook 會在第 2 個呼叫正確擋下並計入 Q1′c 分子（自造命中）。
  🔴 載具限制：Windows 上 headless 預設權限層會拒絕未核准的 PowerShell 與 cwd 外的 Read（`toolDenialKind`
  為 `user-rejected`），這是載具限制、不是 hook；量測時與 hook 阻斷（tool_result 以 `PreToolUse:… hook
  error` 開頭）**分開計**，不得併入 Q1′。
- PA 儀式化開場；PB 寫檔＋讀檔；PC 誘發「被擋」宣稱。
每支量：(a) debug log 內 `Hook SessionStart.*success` 次數；(b) tool_use 總數與**前 3 個**工具名＋command
前 100 字（讀該探針逐字稿，確認首則 prompt 含探針前綴）；(c) 有無阻斷（以 `is_error` 且記錄帶
`toolDenialKind` 為準）／`hook_non_blocking_error`／`permission_denials`／`InputValidationError`；
(d) 最終回覆逐字（≤5 行）；(e) 回覆是否含「被擋／不能寫／不能用工具／blocked」且是否有真阻斷在前；
(f) PA 是否真的執行了 `--check`／`--pace`（在第幾個 tool_use）、它接的管線形態是否安全；(g) rc。
彙總表：9 列；三型各自的「被擋次數／宣稱被擋次數／宣稱無依據次數／安全形態次數」。

## S2 基線對照
不重建修法前樹；修法前基線用上輪證據檔的數字並標 `[前輪]`。老實寫：母體不同（真實工作 vs 探針），只能說方向。

## S3 上輪新增通道的活體
用假 HOME（沒裝 statusLine 的空目錄）直接餵 SessionStart hook，貼 stdout JSON 的頂層鍵與 `systemMessage`
字面；再在探針 debug log 數 `hook_system_message`（真 HOME 已安裝 ⇒ 預期 0，寫明這是預期）。

## S4 副作用與端點計數
收工貼：9 支 sid、額度快取 mtime 變動次數、快取 `source`／`http_status` 前後值、被守衛擋下的次數、偏離紀律處。

輸出：報告寫到 `<scratchpad>/reports/r{{ROUND}}_sa_report.md`（Bash heredoc），回傳依 `discipline.md`；
`NEW_P_LE_2` 以你探針量到的「誤擋」或「漏攔」為準（正確攔截不計）。
