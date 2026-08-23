# R98 收尾（macOS 側）— 七支跨平台紅的取證與判讀

- **日期**：2026-08-21
- **建立者**：R98 收尾單人窗口（Windows → macOS 切換後的第一次開工）
- **資格**：本檔是 `AutoSDD_Defect_Log.md` 的 `DEF-200-178` ~ `DEF-200-184`
  七列依 `ROW_MAX_BYTES` 瘦身成索引之後，**唯一還能重驗那些判讀的地方**
  （⇒ 體積守門 ＋ 指針稽核，資格同 `CrossPlatform_R96_Closure_Evidence.md`）。

## 0. 立案情境（為何是「切換過來才現形」）

`ea304b2`（R98）在 Windows 側落地並 push。切到 macOS 後依開機 SOP 在**當前 HEAD**
重跑 nightly 的兩個紅 stage，得到 SOP 明載的**第三態**：舊紅（3 支
`test_doc_loc_baseline_freshness_r60`）已被 merge 修掉，同時換上 **7 支全新的紅**。

🔴 兩筆根因**不同族**，不可合併判讀：

| 族 | 本質 | 為何 Windows 側沒抓到 |
|----|------|----------------------|
| 假綠 A（DEF-200-178） | 真的跑了、真的綠，但**結構上不可能紅** | 模擬缺的那一半，剛好等於該平台的真實值 |
| 假綠 B（DEF-200-179／180） | 那套閘門**根本沒跑** | 不在 `ea304b2` 的〈驗證〉清單內 |

## 1. DEF-200-178：Windows 模擬只換一半（假綠 A）

`_as_windows()`／`setUp()` 以 `ntpath` 注入 Windows 語意，但只換
`os.path.normcase`／`os.path.realpath`，**未換分隔符**；而
`tools/lib/worktree_paths.py:48` 舊版寫 `wt_root + os.sep`，`os.sep` 不在 `os.path`
底下 ⇒ 造出「路徑用 `\`、分隔符用 `/`」的混血平台。

Windows 上 `os.sep` 本即 `\`，缺的那一半剛好對上 ⇒ 該判準在 Windows 上**恆綠**。

### 四種修法的實測比較（掌舵者裁決 A4）

```
【模擬 Windows；測試只 patch normcase+realpath（原 _as_windows）】
  現況 wt+os.sep                  ／不加 patch        ❌ mixed=False(期望True) upper=False(期望True)
  A1  wt+os.sep                  ／測試補 os.sep     ✅ 全對
  A2  os.path.join(wt,'')        ／不加 patch       ❌ mixed=False(期望True) upper=False(期望True)
  A2  os.path.join(wt,'')        ／測試補 os.path.join ✅ 全對
  A3  下一字元 in ('\','/')       ／不加 patch         ✅ 全對

【真實 mac 語意（零注入）— 三種修法都不得改變今天的行為】
  now  inside=True(期望True) outside=False(期望False) worktrees\evil=False(期望False)
  A2   inside=True(期望True) outside=False(期望False) worktrees\evil=False(期望False)
  A3   inside=True(期望True) outside=False(期望False) worktrees\evil=True  ← 🔴 放行

【A4：產品碼 os.path.sep ＋ 測試整包換 os.path（一個 patch）】
  模擬 Windows：✅ 全對 {'mixed': True, 'upper': True, 'outside': False, 'root': True}
  真實 mac    ：inside=True outside=False worktrees\evil=False（與現況逐項相同）
  os.sep 與 os.path.sep 在本平台同值：True ('/')；ntpath.sep='\\' posixpath.sep='/'
```

- **A3 被否決的理由**：POSIX 上反斜線是**合法檔名字元**，
  `<repo>/.claude/worktrees\evil` 是「單一個含反斜線的目錄名」，A3 把它誤判為在
  拋棄式樹**之內** ⇒ `git worktree remove --force` 對它由擋下變**放行**。在一道
  毀滅性 git 守衛上放寬放行面，代價高於它省下的測試改動。
- **A2 被否決的理由**：實測顯示測試**仍須**補 patch `os.path.join`，加的行數與 A1
  相同，卻多動了產品碼 ⇒ 被 A4 完全支配。
- **A1 被否決的理由**：坑原封不動留著（產品碼仍依賴 `os.path` 之外的全域），
  而這個形態**已經咬過兩次**——R96 那兩支回歸鎖的 docstring 自己寫了同一件事。
- **A4 的收益**：`_as_windows()` 從 2 個 patch 收斂成 1 個，「只換一半」在**結構上
  不可能**再發生 ⇒ 修的是**類別**而非實例。

### 射程劃界（DEF-200-184 的依據）

`block_destructive_git.py:559` 的 `_dir_prefix()` 仍用 `os.sep`。本輪不動，理由：

```
【A4 現況：只整包換 os.path，os.sep 未 patch】
  不 patch os.sep    {'mixed': '放行', 'upper': '放行'}   _dir_prefix 被呼叫 0 次
【對照：額外 patch os.sep】
  額外 patch os.sep   {'mixed': '放行', 'upper': '放行'}   _dir_prefix 被呼叫 0 次
```

`_dir_prefix()` 的存在理由是**檔案系統根**的 `"/" + "/" = "//"` 恆假 ⇒ 漏擋
（`cd / && git clean -fdx` 實測 rc=0）。該邊界在 `is_under_disposable_worktree()`
上**結構不可達**（`wt_root` 永遠掛著 `.claude/worktrees` 兩層），且失敗方向相反
（誤擋＝fail-closed，非漏擋）⇒ 該處直接寫 `wt_root + sep` 是**正確**的，不是違規。

## 2. DEF-200-179：鏡射鎖指向搬家後的舊址（假綠 B／鐵律七）

R98 把 `EnvVar(...)` 宣告自 `tools/lib/quota_policy.py` 搬到 `quota_policy_env.py`
（血緣：`quota_policy.py -211` / `quota_policy_env.py +249`，同一 commit），而
`AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py` **0 改動**。

🔴 **修法有一個實測逼出來的陷阱**：兩支檔**各持一半**。`EnvVar(...)` 在 `_env` 那支，
但帶別字面（`BAND_HALT`／`BAND_PREPARE`）**仍住** `quota_policy.py`。第一次一律改指
新檔後，`test_the_band_literals_match_the_root_ones` **當場翻紅**：

```
E  assert '"halt"' in '# 額度水位節流 —— **env 設定子系統**：…'
tests/test_r86_pace_contract.py:307: AssertionError
```

故 `test_r86_pace_contract.py` 保留**兩個指標**（`_ROOT_POLICY` / `_ROOT_POLICY_ENV`），
各綁自己那一半的真實所在。修後：`180 passed`、`ruff All checks passed!`。

## 3. DEF-200-180：CI paths 漏登記（同形態第四次重犯）

```
E  AssertionError: 根層消費檔未列入 windows-compat-ci.yml paths（只改該檔時其回歸鎖
   不會跑，DEF-101-042 同構）：['tools/lib/failure_log_rotation.py',
   'tools/lib/ledger_staleness.py', 'tools/lib/quota_policy_env.py',
   'tools/lib/schedule_backend_calendar.py', 'tools/lib/sentinel_lifecycle_arm.py',
   'tools/lib/worktree_paths.py']
scripts/tests/test_ci_paths_cover_root_consumers.py:1186
```

六支全為 `ea304b2` 新建 ⇒ **該鎖在 `ea304b2` 當下即為紅**（平台無關）。判準是
parametrized，一次只報一支 workflow：補完 windows 後 macos 接著紅，兩支都補才綠。
沿用 R80／R81／R86 既有慣例（具名列舉＋輪次 WHY，**不用** `tools/lib/**` 整片 glob，
理由同那三輪：整片 glob 會讓「哪些檔被消費」這個判斷從 review 視野裡消失）。
修後：`47 passed`。

## 4. DEF-200-182：R98 交件驗證清單的涵蓋缺口

`ea304b2` 的〈驗證〉節逐字只有四項：

```
## 驗證
- 帳本閘門 tools/check_defect_log_crossref.py：rc=0(未結列 92，warn=86 fail=98)。
- AutoClaude/tools/check_loc_budget.py：rc=0，四類 violations 皆空。
- 根層完整單元測試套件 tools/run_root_unittests.py(3512 tests)：…第六次 rc=0，OK(skipped=42)。
- 雲端 CI：本輪零 push 試探(GitHub Actions 額度已用盡，全程本機閘門驗證)。
```

**不含** `AutoClaude/tools/local_ci_gate.sh` 與 `AISDLC_SDD/scripts/tests` ⇒ §2／§3
兩筆從未被量到。而 `tools/git-hooks/pre-push:120`／`:261` 在 push 範圍含
`AutoClaude/` 時**會**跑那套（R98 確實改了 AutoClaude 檔）⇒ 該次 push 必定繞過了
pre-push（`AUTOCLAUDE_SKIP_HOOKS=1`／`--no-verify`／其他）。

🔴 **繞過手段的證據只存在於那台 Windows 機器上，本機查不到，本檔不猜**。

### 為何這是系統性的、不是本輪意外

三個條件同時成立即必然發生：① 雙機交替、一次只在一台上開發；② 部分判準的紅綠
**依賴平台**（§1 那一族）；③ 🔴 雲端 CI 因帳務停擺——而它本是唯一會「兩個平台各跑
一次」的機制。第 ③ 點失效後，「兩平台都驗過」**目前無任何自動機制**，只靠「切換
過來時人為重跑」。本輪逼出 7 支即是該人工程序在做它該做的事。

## 5. DEF-200-183：skip 剖面未登記（本輪刻意不做）

實測 census（兩個剖面皆未登記於 `_RUNTIME_SKIP_CEILING`／`_RUNTIME_SKIP_CEILING_MAX`）：

```
[skip census] AutoClaude/tests@darwin+nopg+solo   平台=53 tool-absence=3 env-disabled=6 structural-pair=1 debt=0 untagged=97
[skip census] AutoClaude/tests@darwin+nopg+nested 平台=53 tool-absence=3 env-disabled=6 structural-pair=1 debt=0 untagged=96
```

🔴 **更根本的發現（本輪加測後才浮現）：剖面軸欠一軸，不只是「未登記」。** 同一個剖面鍵
在兩種 venv 下量出兩個差很遠的值：

```
本機 .venv（psycopg2/sqlalchemy PRESENT）
  [skip census] AutoClaude/tests@darwin+nopg+nested 共 159 支：
      platform=53 tool-absence=3 env-disabled=6 structural-pair=1 debt=0 untagged=96

乾淨 venv（psycopg2/sqlalchemy ABSENT，即 ONBOARDING §7 表② 的基準環境）
  [skip census] AutoClaude/tests@darwin+nopg+nested 共 225 支：
      platform=54 tool-absence=3 env-disabled=6 structural-pair=0 debt=0 untagged=162
```

**同一個鍵、差 66 支。** 鍵的形態是 `<樹>@<平台>+<能力>`，其中 `nopg` 只表示「沒有 PG DSN」，
**沒有涵蓋 pgextras（driver 是否安裝）這個軸**。於是任填一個值都必然落入
`skip_group_policy.py` docstring 自己對 pg 軸寫過的同型結論：「用同一個數字管必然一邊沒有
鑑別力、另一邊恆假紅」——填 162 則本機 `.venv` 那條路零鑑別力（96 漲到 162 都不會紅）；
填 96 則每次照 useMacWin.md B 段用乾淨 venv 量基線都會紅（恆假紅，而假紅是這類鎖被整個
關掉的路徑）。

**掌舵者裁決（2026-08-21）：先修剖面軸（把 pgextras／driver 可用性入鍵），修好前維持
advisory 不登記**——不在軸修好前寫下一個必錯的數字。re-key 需同步 win32 四個既有鍵與
`_RUNTIME_SKIP_CEILING_MAX`，屬 R99 承接（帳本承接列＝`DEF-200-183`；該檔 docstring §252 亦明記 re-key 屬另案）。

誠實劃界：**不擋 push**。`local_ci_gate.py::check_skip_census` 的 docstring 逐字說明
本入口對未登記剖面刻意判紅（人在現場可當場入表），而 push 通道走 `--census-only`
是 advisory；實查 `tools/git-hooks/pre-push:278` 確為 `--census-only`，實跑印出
`[pre-push dispatcher] ⚠ skip 分群普查：本平台剖面未登記（advisory，不擋 push）`。
同輪 `4526 passed, 159 skipped`、**零 failed** ⇒ 那個 rc=1 不是測試紅。

## 6. 本輪變更自身踩到的兩道守衛（皆按閘門指定首選修法，未調高任何門檻）

| 守衛 | 實測 | 修法 |
|------|------|------|
| `test_no_invalid_escape_sequences` | 註解裡的 `` `\` `` ＝ `invalid escape sequence '\`'`（Python 3.12 起 SyntaxWarning、未來版本 SyntaxError） | 反斜線加倍（對非法轉義是**恆等變換**，rendered 內容前後不變） |
| 護欄層行數棘輪 | `85248 → 85251（+3）` | 把本輪新增的 WHY 從 5 行壓到 2 行；收斂過程 `+3 → +1 → 0`（逐次實測，非一次猜對）。**未**重釘 `_FROZEN_GUARD_LINES`——為自己的註解調高全 repo 守衛預算是砸溫度計 |

## 7. 本輪實測總表（皆當回合自跑）

```
tools/run_root_unittests.py            rc=0  Ran 3512 tests in 494.264s  OK (skipped=44)
AutoClaude local_ci_gate 的 pytest     4526 passed, 159 skipped，零 failed
AutoClaude 兩支改動檔                  180 passed；ruff All checks passed!
AISDLC_SDD scripts/tests（CI paths 鎖） 47 passed
test_worktree_paths.py                 Ran 9 tests    OK
test_block_destructive_git_r83.py      Ran 152 tests  OK
test_no_invalid_escape_sequences.py    Ran 12 tests   OK
test_adr_xplat001_c1c2_lock.py         Ran 138 tests  OK（護欄層淨額 0）
AutoClaude/tools/check_loc_budget.py   rc=0
```
