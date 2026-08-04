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
| 帳本規模 | 248,048 → 233,559（歸檔 archive_55）→ **250,596**（寫入 16 列 R74 帳目後）。warn=245,760／fail=262,144 |

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
4. `DEF-101-790/792/795/796/797/798` 皆為 `partial@R74`，解鎖條件已逐列寫在帳本。
5. 本輪實配缺陷號為 DEF-101-787 ~ DEF-101-802（16 列）。根 `CLAUDE.md` 的引用已於收輪前對齊為實號
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
- ❌ **不准把 R74 自己的已結列搬進 archive**。`archive_defect_log.py --plan` 會把它們列為可搬，
  但搬走會讓 `current_round()` 由 74 倒退，使「原始碼自稱輪號 ≤ 帳本當前輪號」那道鎖轉紅。
  本輪實測遇到此互動，刻意不搬（帳本因此停在 250,596，越 warn 線但遠低於 fail 線 262,144）。
- ❌ Windows 側不准用 Bash 工具（有 PreToolUse 阻斷）；不准裸 `cd`；不准裸 `bash <script>`。
- ❌ 訂正假話時不准逐字重述那句假話（樹裡不留假句子，已有鎖在抓）。

---

## 5. 工作樹狀態

- 分支 `main`，未 commit。改動：54 個 tracked 檔 ＋ 4 個新檔
  （`docs/06_quality/AutoSDD_Defect_Log_archive_55.md`、`tools/_cli_flags.py`、
  `tools/check_scheduled_task_drift.py`、`tools/scheduled_task_expectations.json`）。
- 若需保全：`git stash create` ＋ `git tag r74-wip-preserved <sha>`。
