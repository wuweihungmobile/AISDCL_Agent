# R125 交棒書（純結案輪）

- **輪籤**：R125
- **主線**：延續掌舵者裁決的「純結案輪」方法論——一筆一筆結、挑重跑指令就綠的先清、不順便挖新坑。
  本輪**不做任何新功能／新設計**，只針對既有未結帳本列做唯讀查證＋單線結案。
- **帳本**：未結列 **57 → 49**（淨降 8）。commit＝`94b06f5`，**已 push**，雲端三支全綠
  （root-infra-ci／macos-compat-ci／windows-compat-ci；AutoClaude CI 因本次只動
  `docs/06_quality/AutoSDD_Defect_Log.md` 一份文件、路徑過濾未觸發，非遺漏）。

## 本輪方法

1. 用 Workflow 工具派出兩波**唯讀**分診（第一波 4 個、第二波 6 個 sonnet 小包，皆
   `model:'sonnet'`），逐筆核實候選帳本列的「帳本描述」是否仍對應現況、或已被後續輪次
   順手解決。兩波共查了 48 筆（57 筆未結列中扣掉本輪自己拆出/裁決型後的候選集合）。
2. 分診本身**只讀不寫**；找出真正 closeable-now 的候選後，由本人（單一窗口）逐筆親自
   重跑驗證指令、確認 rc=0，才動筆改帳本狀態欄——全程**未平行寫帳本**（鐵律七檢查表第
   1 項）。
3. 對於「已被裁決但方向與帳本原文相反」的列（如 DEF-200-258），依裁決文件改判
   `closed-by-decision`，不強行照字面執行已被否決的方案。

## 本輪結案 8 筆

| ID | 原描述 | 結案理由 | 驗證 |
|---|---|---|---|
| `DEF-200-065` | `skip_group_policy.py` 399/400 貼牆 | 已隨 R123（`DEF-200-183`）副作用抽出 `skip_profile_key.py` 而解除，現 364/400 | `check_loc_budget.py --json` |
| `DEF-200-167` | `DEF-200-150` 未採用 R91 §I-22 正解 | 已改走 `_fetch_token(platform, runner)` 單一注入點 | `pytest -k MacCredentialSourceTest` → 6 passed |
| `DEF-200-249` | NTFS 大小寫閘無永久回歸鎖 | `test_ntfs_trailing_space_device_name.py` 已是常設鎖 | 38 passed, 45 subtests |
| `DEF-200-250` | 29 支 AC matrix skip reason 與 docstring 矛盾 | 已重寫，現況 0 skip，問題母體不存在 | 32 passed, 0 skipped |
| `DEF-200-254` | Linux 剖面 untagged 未清 | 已於 R100 由 9→0 並鎖住 | `test_skip_ceiling_ratchet_direction.py` 23 passed |
| `DEF-200-258` | `_HOME_ARTIFACT_DIRS` 豁免面過寬 | R115 已裁決刻意維持現寬度（見 `Guard_Line_History.md`），判 closed-by-decision | 讀該節裁決理由 |
| `DEF-200-261` | 沙箱鎖 docstring 與實作不符 | 過度宣稱文字已隨 R122 Guard Prose Migration 移出即時原始碼 | Read 現行 docstring |
| `DEF-200-262` | 舊字串包含判準對 `..` 失明 | 已抽成 `worktree_paths.is_under_disposable_worktree()`，改用 realpath+normcase 前綴比對 | `test_worktree_paths.py` 9 passed |

## 已驗證（本 session 實測）

- `check_defect_log_crossref.py`（不帶參數）rc=0：帳本 192 筆有效狀態紀錄、未結存量 **49
  列**、逐列位元組上限全數通過（本輪過程中曾撞到 DEF-200-167 872B 超標，已trim至合法值；
  DEF-200-258 措辭曾觸發「已結列殘留待辦」假陽性，已改寫措辭排除，同 R124 handoff-carrier
  假陽性同一類坑）。
- `check_archive_required.py` rc=0、`check_handoff_carriers.py` rc=0、
  `--print-guard-lines` 淨額 `91990→91990 (+0)`（本輪只改帳本文字，未動任何程式碼）。
- 目標 pytest：`test_check_defect_log_crossref.py` + `test_archive_defect_log.py` →
  439 passed（兩次跑，分別 391／398 subtests，皆 rc=0）。
- **全套 `python tools/run_root_unittests.py`**（本輪跑了兩次，分別在 DEF-200-065 單筆結案後、
  以及 7 筆追加結案後）：兩次皆 `Ran 3911 tests ... OK (skipped=42)`，rc=0（親自讀 log 尾端
  確認，未採信 harness 摘要字面）。
- commit `94b06f5` 已 push（`f5faf12..94b06f5`），push 指令本身因 pre-push 全套閘門耗時
  過久（首次前景等待 9m30s 逾時、rc=143 即工具逾時砍掉，非 hook 失敗）改用背景執行，
  背景 log 尾端讀到 `push_rc=0`＋`[pre-push dispatcher] ✅ 本次 push 觸發的所有 leg 皆通過`。
  雲端三支（root-infra-ci／macos-compat-ci／windows-compat-ci）逐支查 conclusion=success，
  非只看有無觸發。

## 還沒做（不塗綠）

1. **DEF-200-247（死碼刪除）尚未執行**——本輪已親自 `git grep` 確認
   `AutoClaude/tools/verify_token_guard_e2e.py` 全庫零消費者（僅自身與其單元測試命中），
   且 R81／R121 兩份既有文件皆已獨立裁決應刪除，但實際刪除**從未執行**。本輪判斷刪除
   須「同步 5 檔 7 處」（`MIN_TESTS` 收集數、`check_script_parity` 登記面等，見
   `CrossPlatform_R81_Ledger_Triage.md` §`LDG-S1-22`）屬真實重構工作，與本輪「純查證即結案」
   性質不同，故未在本輪動手，帳本列保持 open。現查零消費者：
   `git grep -n "verify_token_guard_e2e" -- AutoClaude .github`（預期只命中該檔自身與其單元測試）。
   下一個真的執行刪除的窗口完成後，請在任一 tracked 檔留下對應紀錄，本節宣稱即可被下方
   標記機械打臉。
   <!-- absent-if: verify_token_guard_e2e.py 已刪除 -->
2. **31 筆候選中的 19 筆 needs-work、3 筆 needs-decision 未結案**——完整逐筆證據存在本輪
   兩個 Workflow 的 journal（未落盤進 repo，僅存於本機 session 暫存，見下方〈證據位置〉），
   下一輪若要挑其中幾筆進落地輪，建議先讀 journal 而非重新分診。needs-decision 3 筆
   （`DEF-200-259`／`DEF-200-182`／`DEF-101-736`）皆需掌舵者或四方在多個方案間選一個，
   不是單純未動工。
3. **帳本仍有 49 筆未結**，其中不少（如 `DEF-200-242`／`243`／`244`）帳本文字本身已過期
   ——R121 裁決包（`AutoSDD_Adjudication_Packet_R121.md`）已對這幾筆選定落地方向，但帳本
   列狀態欄措辭仍停在「待裁決」，尚未更新反映裁決包已存在。現查：
   `Select-String -Path docs/06_quality/AutoSDD_Defect_Log.md -Pattern "^\| DEF-200-(242|243|244) \|"`。

## 證據位置（未落盤，session 暫存）

- 第一波分診（17 筆）：run ID `wf_77b597a7-d91`，
  journal＝`subagents\workflows\wf_77b597a7-d91\journal.jsonl`。
- 第二波分診（31 筆）：run ID `wf_e91a601c-84a`，
  journal＝`subagents\workflows\wf_e91a601c-84a\journal.jsonl`；完整結果另存
  `C:\Users\wuwei\AppData\Local\Temp\claude\d--CursorProject-AISDCL-Agent\06deae09-348a-4bcc-87ae-dd4ec117a57c\tasks\wp0fe9xy1.output`。
- 兩者皆屬本機 session 暫存，**不隨 repo 走**，下一個 session 若要複用需自行從本機路徑撈取，
  或視為過期直接重查。

## 下一步（下一個窗口）

- 若要繼續降帳本：優先挑 `DEF-200-242`／`243`／`244`（措辭過期，R121 裁決包已選方向，
  轉入落地輪派工）；或評估是否要動手完成 `DEF-200-247` 的死碼刪除（含 5 檔 7 處同步）。
- 若要繼續純結案：剩餘 49 筆中，本輪兩波分診已覆蓋 48 筆（除 `DEF-200-065` 已結），
  基本上已無更多「重跑指令就綠」型的低垂candidates，下一輪要再有產出，可能需要先真的
  動工修幾筆 needs-work 才能反過來結案。

## 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`。
- 不准把本輪 needs-work／needs-decision 的 31-8=23 筆順手改成已結——皆已逐筆核實仍需真實
  動工或等裁決，硬結會製造假結案。
- 不准同時派多個 agent 平行編修帳本（鐵律七檢查表第 1 項：結案編修只准單一窗口做）。
- push 前務必先跑全套 `tools/run_root_unittests.py` 並親自讀 log 尾端 rc，不可只看
  harness 的 task-notification 摘要字面（本輪已兩次驗證過這個習慣的必要性）。
- push 指令務必背景執行（`run_in_background: true`），前景等待常在 9~10 分鐘內逾時而不代表
  失敗；逾時後改用 `git fetch` + `git log origin/main..HEAD` 判斷是否真的送達，不要盲目重推。
