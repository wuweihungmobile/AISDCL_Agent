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
  `--check` 只讀逐字稿，可以。
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
