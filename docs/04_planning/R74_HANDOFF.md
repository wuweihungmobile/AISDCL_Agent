# R74 交棒任務書（跨平台輪 — Mac × Windows 11 相容性）

> 建立時間：2026-08-04。建立原因：本輪兩支收尾 agent 因 **session 額度上限**中止
> （重置 04:00 Asia/Taipei），主控改為親自收尾並停止再派 agent。
> 本檔依根 `CLAUDE.md`〈Token 將耗盡時的無害暫停 SOP〉「可重啟點四條件」撰寫。
>
> 🔴 **重啟後第一件事是重驗，不採信本檔任何「已通過」宣稱**（同 Nightly 取證紀律 #17
> zero-trust 雙向：對自己上一段的宣稱也要 zero-trust）。

---

## 1. 已驗證什麼（附實測數字與 rc）

主控**親自跑過**的（非採信 agent 宣稱）：

| 項目 | 實測 |
|------|------|
| P0 hook 修復（`block_bash_on_windows.py`） | `PYTHONIOENCODING=cp1252` ＋剝除 `PYTHONUTF8` 下：rc=2、中文可讀、無 `\uXXXX`；`{"tool_name":"Read"}` rc=0（射程未擴大） |
| P0 根因重現（修復前） | 同環境下輸出 `\U0001f534 Windows \u4e0a\u5df2...`，與 CI run 30838711666 log 逐字相同；`sys.stderr.errors=backslashreplace` |
| 新行尾閘（`check_sh_eol.py` 射程上移） | repo 內三棵樹（`tools/`、`AutoClaude/`、`AISDLC_SDD/scripts/`）CRLF `.sh` 皆 rc=2 阻斷；LF 對照 rc=0 |
| `.claude/settings.json` | JSON 合法、PreToolUse 2 個 block、沿用既有 shim（缺檔 fail-open） |
| 排程漂移偵測器（新建） | rc=1，逐項列出 5 筆漂移（Nightly 2／Smoke 3）；`ExecutionTimeLimit` 實機為 `<missing>` |
| AC4 觀察期 | `status=ready`、`green_streak=43/14`、`ready_for_labeled_pr=True`、`staleness_days=0/30`、rc=0 |
| ruff（本輪 AutoClaude 變更檔） | rc=0 |
| AC4 測試 | 39 passed、rc=0 |
| `ruff check tools/ .claude/hooks/`（＝CI 第 16 道） | rc=0 |
| 缺陷帳本 crossref | rc=0 |
| `archive_defect_log.py --check` | rc=0 |
| `current_round()` | **74**（R74 帳本列已寫入） |
| 帳本規模 | 🔴 **R75 訂正**：本格原記的兩個數字是**中間態**（量在「archive_55 已搬出、本輪帳目還沒寫進去」那一瞬），不是 commit 狀態；`a371068` 的實測是 **252,067 bytes／119 列**（`git cat-file -s a371068:docs/06_quality/AutoSDD_Defect_Log.md`），比動工前的 248,048 **淨增 4,019**。warn=245,760／fail=262,144 ⇒ 收輪時距 fail 僅 10,077 bytes。同一組中間態數字也被抄進 R74 commit 訊息與 `tools/lib/defect_ledger_index.py` 的門檻註解（後者已於 R75 訂正） |

收輪前最終全套（皆在最終工作樹、序列化執行，無並行競爭）：

| 閘門 | 實測 |
|------|------|
| 根層 `run_root_unittests.py` | **rc=0**，`Ran 1819 tests` `OK (skipped=43)`，211s |
| AutoClaude `pytest tests/` | **rc=0**，3878 passed / 224 skipped，73.7s |
| `sync_onboarding_baselines.py --check` | rc=0 |
| `sync_onboarding_baselines.py --check-snapshot` | rc=0（🔴 兩個變體都跑了——R73 曾只報綠的那個） |
| `check_defect_log_crossref.py` | rc=0 |
| `archive_defect_log.py --check` | rc=0 |
| `ruff check tools/ .claude/hooks/` | rc=0 |
| `lint-imports` | rc=0（8 kept / 0 broken） |
| `check_loc_budget.py` | rc=0 |
| `check_scheduled_task_drift.py` | **rc=1（預期）**——5 項設定待提權套用，見第 2 節第 2 點 |

收輪期間修掉的三筆「閘門自己壞掉」：
1. `MIN_TESTS` 停在 1663 而實測 1819 ⇒ 零相依探針失去提前判紅能力、改為實跑整棵樹。
   **R69 的註記早已逐字預告過這個失效模式**，本輪應驗。已重釘為 1819。
2. 探針**遞迴**（探針跑整套、整套裡又有探針）⇒ 放寬逾時只是放大：牆鐘 823s→3813s 且仍逾時。
   已改為子行程帶旗標、本類別見旗標自我 skip。修完整套 **3813s → 211s**。
3. 兩支 compat-CI 的 `paths:` 漏列 5 支根層消費檔（含本輪新建的排程漂移偵測器）⇒ 只改那些檔時
   鎖不會被觸發。由 `test_ci_paths_cover_root_consumers.py` 當場攔下，已雙邊補齊。

---

## 2. 還沒做什麼

1. 🔴 **四方複審（Architect／SA／SD／QA）完全未執行** — 已登記為 `DEF-101-801`（P1，承接 R75）。
   本輪 54 個 tracked 檔改動 ＋ 4 個新檔未經獨立對抗式複審。
   **不得以「閘門全綠」替代**：本輪頭號發現正是「本機全綠而雲端紅」。
2. **五項排程設定未套上線** — 需系統管理員提權（`DEF-101-794`，承接輪次：未指派，屬掌舵者親執行類）。
3. 各修復包明列的 `not_done` — 已彙總於 `DEF-101-802`（P2，承接 R75）。
4. `partial@R74` 共 **7 筆**（🔴 R75 訂正：本項原漏列 `DEF-101-803`）——
   `DEF-101-790/792/795/796/797/798/803`，解鎖條件已逐列寫在帳本。
5. 本輪實配缺陷號為 DEF-101-787 ~ **DEF-101-803**（**17 列**；🔴 R75 訂正：原記的上界與列數都少算一列，
   實查 `a371068` 帳本 787~803 連續 17 列無缺號）。根 `CLAUDE.md` 的引用已於收輪前對齊為實號
   —— 佔位形態（家族號＋尾碼 x）有機械鎖 `tools/tests/test_defect_id_reference_integrity.py` 在管擴散，收輪前必須清乾淨。

---

## 3. 下一步的確切指令

```powershell
# 一、重驗全套（依序，不要並行——並行跑會互踩 __pycache__ 造成假紅）
$r='D:\CursorProject\AISDCL_Agent'; $py="$r\.venv\Scripts\python.exe"; $env:PYTHONUTF8='1'
& $py $r\tools\run_root_unittests.py                       # 期望 rc=0
Push-Location "$r\AutoClaude"; & $py -m pytest tests/ -q; Pop-Location
Push-Location "$r\AutoClaude"; & "$r\.venv\Scripts\lint-imports.exe"; Pop-Location
Push-Location "$r\AutoClaude"; & $py tools\check_loc_budget.py; Pop-Location
& $py $r\tools\sync_onboarding_baselines.py --check
& $py $r\tools\sync_onboarding_baselines.py --check-snapshot   # 🔴 兩個變體都要跑，別只報綠的那個

# 二、四方複審（R75 第一件事）
#    對本輪 diff 派 Architect / SA / SD / QA 獨立審查，收斂全部 blocking

# 三、掌舵者親執行（需「以系統管理員身分執行」）
powershell -ExecutionPolicy Bypass -File tools\install_windows_nightly.ps1 -NightlyAt 22:30 -SmokeAt 23:30
powershell -ExecutionPolicy Bypass -File tools\install_windows_nightly.ps1 -Status
& $py $r\tools\check_scheduled_task_drift.py               # 期望套用後 rc=0

# 四、push 後必驗雲端（本輪的頭號教訓：本機綠 ≠ 全綠）
gh run list --limit 4
```

---

## 4. 禁止事項

- ❌ 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准跳過或註解掉失敗測試。
- ⚠️ ~~不准把 R74 自己的已結列搬進 archive~~ → 🔴 **R75 撤銷這條禁令（範圍過寬，代價不對等）**。
  原禁令的理由是「搬走會讓 `current_round()` 由 74 倒退」，但 R75 實測那只在**把 R74 全部列都搬走**時成立：
  `current_round()` 取的是帳本「發現情境」欄的最大 `R\d+`，而 R74 的**未結**列（`790/792/794/795/796/797/798/801/802/803`）
  在結構上不可歸檔、必然留在主檔 ⇒ 只搬 R74 的**已結**列時時鐘不動。R75 實搬 archive_56（含 787/788/789/791/793/799/800
  七筆 R74 已結列）後現測 `current_round()` 仍為 **74**、`check_defect_log_crossref.py` rc=0。
  ⇒ 正確的禁令是「不准搬到主檔再無任何該輪列」，而不是「不准搬該輪已結列」。
  代價不對等的證據：為維持一個可由聯集推導的時鐘，付出的是帳本 bytes 逼近硬閘（收輪時距 fail 僅 10,077）。
- 🔴 **更根本的處置（R75 未實作，列交棒）**：`current_round()` 目前只讀**主檔**，所以它的值會隨歸檔動作變小
  ——一個歷史事實（「最新輪號是幾」）被實作成一個會因搬檔而倒退的量。正解＝改由**帳本家族聯集**
  （主檔 ∪ `AutoSDD_Defect_Log_archive_*.md`）取最大值：archive 是 append-only 史料，聯集的最大值單調不減，
  於是「歸檔會讓時鐘倒退」這個耦合從根上消失，也不必再靠「留幾列在主檔」這種紀律。
  **R75 未動手的理由（非不值得做）**：該函式住在 `tools/check_defect_log_crossref.py`，本輪由另一個 agent 持有
  （已有 LOC 棘輪衝突實例），跨界改會撞編輯衝突；且 `archive_defect_log.py --check` 判準(8) 已有「帳本家族＝
  主檔 ∪ archive」的既有解析先例可直接沿用，實作成本低、風險集中在協調而不在設計。
- ❌ Windows 側不准用 Bash 工具（有 PreToolUse 阻斷）；不准裸 `cd`；不准裸 `bash <script>`。
- ❌ 訂正假話時不准逐字重述那句假話（樹裡不留假句子，已有鎖在抓）。

---

## 5. 工作樹狀態

- 分支 `main`，未 commit。改動：54 個 tracked 檔 ＋ 4 個新檔
  （`docs/06_quality/AutoSDD_Defect_Log_archive_55.md`、`tools/_cli_flags.py`、
  `tools/check_scheduled_task_drift.py`、`tools/scheduled_task_expectations.json`）。
- 若需保全：`git stash create` ＋ `git tag r74-wip-preserved <sha>`。

---

## 6. R75 帳本收斂結果與交棒（Developer D 追記）

### 6.1 兩軸現況（皆為 R75 工作樹實測）

| 量 | R74 收輪（`a371068`） | R75 收斂後 | 門檻 |
|----|---------------------|-----------|------|
| 未結列數 | 97（距 fail **1 筆**） | **81** | warn 86／fail 98 |
| 主檔 bytes | 252,067（距 fail 10,077） | **247,135**（距 fail **15,009**） | warn 245,760／fail 262,144 |
| 表格列總數 | 119 | 109 | — |
| 未結列 bytes | 198,184＝硬線 75.6% | **152,287＝硬線 58.1%** | — |
| 未結列平均 bytes | 2,043 | **1,880** | — |
| 存量豁免棘輪 | 48 | **36** | shrink-only |

取得方式：結案 16 筆（逐筆回樹複驗，指令＋rc 寫在帳本各列「R75 複驗」段）＋
`DEF-101-769` 部分回執＋改派＋歸檔 `archive_56`（10 筆／17,911 bytes）。
**兩軸同時改善**：列數 −16、bytes −4,932，且 bytes 的降幅是**淨值**（已含 16 筆複驗註記的新增量）。

### 6.2 🔴 新缺陷列的體積上限建議（給舵手拍板）

本輪四方複審有十餘筆新缺陷要登錄。以現行未結列平均 **1,880 bytes** 推算，
15 筆照既往寫法即約 **28KB**，會直接撞 bytes 硬閘（餘裕只有 15,009）。建議：

- **每列上限 1,000 bytes**（約現行均值的一半）。15 筆 ⇒ ≤15KB，仍會吃掉幾乎全部餘裕
  ⇒ 收輪前**必須**再跑一次 `archive_defect_log.py`；若餘裕仍不足，優先動 `DEF-101-676`
  點名的索引 bullet 去重槓桿（估可回收 ~26KB），而**不是**調門檻。
- **帳本列只放四件事**：① 現象一句話 ＋ `file:line`；② 嚴重度；③ 承接輪次或字面「未指派」；
  ④ **可直接執行**的解鎖條件。逐輪複驗史、佐證推導、反駁記錄一律進輪次報告
  （`docs/06_quality/CrossPlatform_R75_*.md` 之類的具名治理文件），帳本只留一個指標。
- **這樣做會不會違反帳本既有的資訊完整性要求？不會，但有一個前提**：帳本自己的體例
  （〈缺陷總表〉指路段）已經在用「主檔＝live SSOT、細節在別處」這個分工——`DEF-101-702`
  就是先例（69 筆掃描發現不逐筆入主檔，改指向具名詳情檔，理由逐字寫在該列）。
  前提＝**那份詳情檔必須登記為具名治理文件**，否則會退化成 `DEF-101-569` 記載過的
  「只讀主檔的人不知道本輪做了什麼」。指針另受 crossref 的「登記面 ↔ 發現面雙向核對」管。
- ⚠️ **不建議**的省法：把多筆發現合寫成一列（`DEF-101-263` 六項合列的後果是「列內子項滯後
  無人偵測」，該列自己記載過此侷限，且它花了 R25／R27 兩輪才收斂完）。

### 6.3 🔴 BLOCKING：R75 的第一列帳本列**必須先落地**，否則全樹輪號鎖是紅的

實測（R75 工作樹）：`python -m unittest tools.tests.test_check_defect_log_crossref` → **rc=1**，
`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound` 列出 **57 處**「自稱 R75 > 帳本當前輪 R74」。

- **不是帳本收斂造成的**：`git grep -l 'R75' a371068 -- '*.py'` → **0 檔**；工作樹同指令 → **13 檔**
  ⇒ 這 57 處全是本輪其他工作者寫進程式碼註解的 R75 標籤，而帳本還沒有任何 R75 列。
- **解法只有一個，且已驗證安全**：把本輪第一列缺陷帳目寫進主檔（其「發現情境」欄含 `R75`），
  `current_round()` 即由 74 變 75。以 `current_round` 假設為 75 重跑該測試 → **failures=0 errors=0**。
- **時鐘跳到 75 不會連帶轉紅任何東西**（動工前先做的探針，收斂後複驗）：合成一列 R75 後
  `orphan_backlog_problems=0`／`unpinned_handover_problems=0`／`stale_grandfather_problems=0`。
  R74 遺留的兩筆孤兒（承接欄寫 R74 且未結）本輪已各自處理：`DEF-101-786` 複驗後結案並隨
  archive_56 歸檔、`DEF-101-769` 就地追加「部分回執＋改派為：未指派」。
  ⇒ **先寫帳本列、再跑全樹閘門**，順序反了會看到一次與內容無關的假紅。

### 6.4 交棒項（R75 未做，附未做的理由）

1. **`current_round()` 改由帳本家族聯集推導** —— 見第 4 節該項。宿主檔本輪由他人持有。
2. **禁止把「現況實測」寫回 `tools/lib/defect_ledger_index.py` 註解的掃描器** ——
   理由與可行/不可行的劃界寫在該檔 `UNRESOLVED_ROWS_WARN` 上方的 R75 附註；
   卡點＝`tools/tests/` 檔數為 shrink-only 棘輪（不得新增 .py），唯一合適宿主
   `test_doc_loc_baseline_freshness_r60.py` 本輪由他人持有。
3. **9 筆帶交棒字樣的已結列仍未歸檔**（`DEF-101-556/652/674/699/710/721/765/770/777`，
   合計約 18KB）—— 需逐筆確認其交棒字樣是否還有活的承接者，才可加 `--ack-handoff`。
   本輪只 ack 了自己複驗過的三筆（`646/706/786`）。這是下一個可用的 bytes 槓桿。
4. **`_UNPINNED_HANDOVER_GRANDFATHERED` 剩 36 筆** —— 其中不少可能同屬「早就修好、
   只有首詞沒跟上」。R75 只掃了「狀態欄自己已宣告解決」這一種形態（12 筆全中）；
   另一種形態（狀態欄沒宣告、但磁碟現況已不成立）本輪只抽查了 4 筆
   （`101-740`／`101-758`／`101-402`／`101-764` 皆**確認仍成立**，故未結），未窮舉。
