# `block_destructive_git.py` 誤用 rc=1 當「出聲不阻斷」的合法出口

- **發現日期**：2026-09-07
- **發現情境**：使用者實測（本場逐字稿 Stop hook 出聲），非本輪工作內容，屬旁支發現
- **狀態**：未落款主帳本（`AutoSDD_Defect_Log.md`）的獨立發現記錄
- 🔴 **誠實劃界**：本檔案原本想落款進 `AutoSDD_Defect_Log.md` 取一個 DEF-200-27x 編號，
  但落款會撞上帳本自己的「淨額棘輪」（本輪新增未結列須有對應結案列，否則需設
  `AUTOSDD_NET_RATCHET_OFF=1`），而該環境變數若對整個 `git push`／
  `run_root_unittests.py` 行程生效，會滲進 `test_check_defect_log_crossref.py` 自己的
  `TestNetNewVsClosedRatchet` 等測試（它們用 `{**os.environ, …}` 複製環境、未顯式清掉
  這個變數，假設環境乾淨），造成那些測試的正樣本斷言失效（已現查重現：單獨跑
  `TestNetNewVsClosedRatchet` 並設該環境變數，5/7 支測試失效）。這個環境變數滲漏本身
  也是一個值得後續處理的小缺口，但範圍已經超出本次要處理的規則6修復，故本檔**只以
  獨立發現記錄存在，不佔用 DEF-ID、不落款主帳本**——下一輪若要正式收進帳本：先修好
  這個滲漏（測試改用顯式 `os.environ.pop` 隔離，或落款時單獨跑
  `check_defect_log_crossref.py`、不與 `run_root_unittests.py` 共用同一個 shell 環境），
  再取用當時帳本的下一個可用 DEF-ID（現查，不得沿用本檔曾經預留的號碼）。

## 現象

Claude Code 的 PreToolUse hook 契約只認兩種 exit code：

- `exit 0`：允許。若寫了純文字到 stdout，會併入 Claude 的 context。
- `exit 2`：阻斷。stderr 內容當成回饋給 Claude。
- **其餘任何 exit code（含 1、3…）一律被判成「hook 本身出錯」**，不是第三種合法結果。

來源：`https://code.claude.com/docs/en/hooks-guide.md`〈Hook output〉節；本場由
claude-code-guide agent 查證確認。

`.claude/hooks/block_destructive_git.py` 目前用 `return 1` + `sys.stderr.write(...)`
來表達「這裡有話要說，但不阻斷這次動作」——這個意圖本身沒有問題，**但用錯了 exit code**。
實測後果：Claude Code 的轉錄印出「Failed with non-blocking status code」，把這次呼叫記成
「hook 載具失敗」，即使 hook 其實有跑、也印了它原本要印的提醒文字。

本場實測：編輯 `tools/session_resume_planner.py`／`tools/lib/quota_escalation.py`
（PRD §15.5 紅線 10 治理檔）各觸發此路徑，皆被記成「本平台自己那條 hook 載具失敗」，
表徵與「hook 沒有真的執行」完全相同——這正是使用者原始疑慮的根源。

## 受影響站點

`.claude/hooks/block_destructive_git.py`（均 `return 1` + `sys.stderr.write`）：

- L1227-1231：payload 讀不出 `tool_name`
- L1245-1246：GOVWRITE 治理檔提醒（本場實測觸發的那一支）
- L1255-1257：缺 `command` 字串
- L1296-1298：`stash_ref_sentinel` 偵測層 note

## 同一套錯誤假設也寫死在測試面

- `tools/tests/test_block_destructive_git_r83.py` 的 `TestDegradedPayloadIsLoudButNotBlocking`／
  `TestGovernanceFilesAreReadOnlyWhenUnattended::test_attended_is_loud_but_not_blocking`／
  `TestR84SentinelAckIsNotASubstring`／`TestR84StashRefSentinel` 四組共 7 支測試斷言
  `returncode == 1` 為正確行為。
- `tools/tests/test_check_hooks_liveness.py::degraded_payload_verdict()`（「共用判準」）
  把 `degraded_rc != 2`（含 1）判為「出聲但不阻斷：爆炸半徑為零，合法」，卻反過來把
  `degraded_rc == 0` 判為「靜默放行」而判紅——這個共用判準完全沒有考慮「rc=0 配 stdout
  輸出」這個實際上才正確的第三種形態。
- **可能被其他 hook 共用同一套錯誤假設**（`context_budget_guard.py`／
  `lint_powershell_command.py`／`block_bash_on_windows.py` 尚未逐一稽核，範圍未知）。

## 本場已嘗試修復並復原（誠實記錄，非放棄）

本場曾把上述 4 個站點改為 `return 0` + `sys.stdout.write`，7 支既有測試如預期由
「斷言 rc==1」變成「斷言失敗（rc 變 0）」——證實了診斷正確。但發現
`degraded_payload_verdict()` 的判準邏輯本身尚未同步更新（它現在的二分法無法正確辨識
「rc=0 且真的印了 stdout」與「rc=0 完全靜默」的差異），若只改本檔會與這個共用判準的假設
互相矛盾、且範圍已知會牽動其他 hook——對「本場只是要修規則 6」而言風險過大，**已完整復原
到修改前狀態**（`git diff` 對 `block_destructive_git.py` 淨零）。

## 待辦（下一輪承接）

1. 比照本則證據修正 `block_destructive_git.py` 4 個站點（`return 1` → `return 0`，
   `sys.stderr.write` → `sys.stdout.write`）。
2. 同步改寫 `degraded_payload_verdict()` 的判準邏輯，使其能分辨「rc=0 靜默」（仍應判紅）
   與「rc=0 但有 stdout 輸出」（應判合法）——可能需要改函式簽章多收一個「是否有輸出」參數。
3. 同步更新 `test_block_destructive_git_r83.py` 內 7 支斷言 `rc==1` 的既有測試。
4. 稽核 `context_budget_guard.py`／`lint_powershell_command.py`／`block_bash_on_windows.py`
   是否有同款誤用。
5. 全部改完後跑 `test_block_destructive_git_r83.py` + `test_check_hooks_liveness.py` 全綠
   再收尾。

建議獨立成一輪、有完整回歸測試再落地——這是安全關鍵的 git 防護 hook，不建議倉促夾帶在
其他任務內。
