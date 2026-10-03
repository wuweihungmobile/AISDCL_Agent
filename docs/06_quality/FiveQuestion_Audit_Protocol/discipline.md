# 共同紀律（所有角色；輪不變）

違反即 REJECT 你自己的交件。槽位：輪號 R{{ROUND}}、起算 HEAD `{{HEAD}}`、日期 {{DATE}}、上輪 {{PREV_ROUND}}。

- 模型：角色一律 Sonnet。工具呼叫上限 **50 次**；禁跑根層全套（`tools/run_root_unittests.py`，約 14 分鐘）、
  禁跑 AutoClaude 全套；單模組測試可以。
- **唯讀 repo**（Developer 角色另有白名單，以當輪任務書為準）：不得改任何 tracked 檔；只能寫 scratchpad。
  禁止 `git stash`／`checkout -- `／`restore`／`reset --hard`／`clean`／`commit`／`push`／`worktree`。
- 單跑任何 `tools/tests` 模組前 **先 `export AUTOSDD_SENTINEL_OFF=1`**（否則隔離 HOME 的測試會卸載本機
  活哨兵），並 `unset AUTOSDD_PARALLEL_TESTS`。venv：`source <repo>/.venv/bin/activate`。Bash 工具每次呼叫
  shell state 不保留，每次都要重新 source。
- **禁打真實額度端點**：不得呼叫 `--pace`、`quota_meter`、`quota_gate` 的量測路徑（SA 章程另有專屬規則）。
  `--check` 只讀逐字稿，可以。🔴 但 `tools/session_gate_acceptance.py` 會推進「未讀結局」游標：審查角色
  不得跑它、只有主控跑（審查角色只讀主控貼出的輸出或 JSON）。
- 讀 rc 不接管線：`cmd > "$SP/x.log" 2>&1; echo rc=$?; tail -n 30 "$SP/x.log"`（接 `| head` 後讀 `$?`
  會被判準④擋下，那是守衛正確）。
- 寫報告：Write 工具對報告類檔名會被 harness 擋（`Subagents should return findings as text`）⇒ 一律
  `cat > 路徑 <<'EOF'` 落檔。報告路徑固定：`<scratchpad>/reports/r{{ROUND}}_<role>_report.md`
  （role＝arch／qa／sa／sd）。
- 回傳格式（純文字，不用 schema）：**首行固定 `VERDICT: APPROVE|CONDITIONAL|REJECT`**，第二行
  `NEW_P_LE_2: <整數>`（你判定的家族內新 P≤2 數），接著 ≤40 行摘要（每條發現：ID／嚴重度／file:line／
  一句話），最後一行 `REPORT: <絕對路徑>`。
- 判決規則：REJECT＝P1 本體缺陷；CONDITIONAL＝P2 本體缺陷；P3 與附屬細節（行號、措辭、歸屬）只列不改判。
  嚴重度口徑見 `severity.md`。
- 鐵律四：任何數字必須來自你本場親跑的輸出，逐字貼（含 rc）；轉述主控或前輪的數字一律標 `[前輪]`；
  你沒跑的標 `[未親跑]`。
- 主控在任務書裡寫的任何「根因判讀」都只是**待驗假設**，證據相反就駁回。
- 不要把 `R{{ROUND}}` 這類輪號寫進任何 repo 程式碼或註解。
- 收工前自陳：副作用（留下的逐字稿 sid、暫存目錄）、偏離本紀律之處、被守衛擋下幾次。

## Windows 形態（上面的指令範例是 Mac／zsh 形態；在 Windows 上一律改照本節）
- 載具：只用 PowerShell 工具——Windows 上 Bash 工具被鐵律一停用（hook 會擋）；讀檔、搜尋用 Read／Grep／Glob。
- 單跑 `tools/tests` 模組前：`$env:AUTOSDD_SENTINEL_OFF='1'; $env:AUTOSDD_PARALLEL_TESTS=$null`；venv 直接用
  完整路徑 `<repo>\.venv\Scripts\python.exe`（不 source 啟用）。
- 切目錄：禁行首裸 `cd`／`Set-Location`；改 `Push-Location '<絕對路徑>'; …; Pop-Location`，在**同一次呼叫內**
  成對（shell state 不跨呼叫存活）。
- 讀 rc 的前一句不接管線：`& $py … *> "$SP\x.log"; "rc=$LASTEXITCODE"`，之後再用 Read 工具讀 log。
- 報告落檔：用 PowerShell here-string（`@'…'@`，結尾的 `'@` 必須在行首）或 Write 工具寫到
  `$SP\reports\r{{ROUND}}_<role>_report.md`。`$SP` 是 scratchpad 的絕對路徑，由當輪任務書給。
- 工具呼叫上限 50 次、唯讀紀律、鐵律四等其餘條文不變。
