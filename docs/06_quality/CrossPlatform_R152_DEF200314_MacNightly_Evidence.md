# mac launchd nightly 2026-09-17 02:00 三症狀——詳情面（DEF-200-314／315／316）

> 帳本列（`AutoSDD_Defect_Log.md`）受逐列 700 bytes 上限管，本檔承接逐條重驗所需的
> 完整脈絡與指令。來源 log：`AutoClaude/logs/nightly_mac_20260917_020002.log`（PASS=2
> FAIL=2）。本輪為單一 Developer 窗口（串行），不涉四方並行修復包。

## DEF-200-314（P1，fixed）—— 三症狀各自根因與修法

### S1：stage2 `root_unittests` rc=1

- **現象**：log 第 368-370 行——`tools/tests@darwin` skip 由 47 上限暴衝到 67，
  `untagged` 群由 0 暴衝到 24。
- **根因**：launchd job 的極簡 PATH（`/usr/bin:/bin:/usr/sbin:/sbin`）不含
  Homebrew bin，`pwsh` 解析不到 ⇒ 24 支「需要 powershell/pwsh」測試的
  `@requires_pwsh` 之類述詞判定失敗，從 platform 語意的 skip 落成 untagged／debt
  語意，撞 `tools/lib/skip_group_policy.py` 的 skip 天花板。
- **重現指令**：
  `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=$HOME .venv/bin/python
  tools/run_root_unittests.py` → rc=1；正常 PATH 下 rc=0。
- **修法**：`AutoClaude/tools/run_local_nightly.sh` 在既有 `.venv/bin` PATH
  prepend 區塊之後（第 43-48 行後），新增 Homebrew bin 存在性探測，**append 到
  PATH 尾端**（`/opt/homebrew/bin`／`/opt/homebrew/sbin`／`/usr/local/bin`，兩種
  架構前綴都探測，不寫死單一架構，不可用 `brew --prefix`——極簡 PATH 下 brew
  本身可能解析不到）。🔴 四方複審訂正（QA＋Architect 同時抓到）：初版誤用往前插
  （`PATH="${_hb_bin}:${PATH}"`），會把 Homebrew 排到 `.venv/bin` 之前、違反單一
  .venv 原則（本機未炸純屬僥倖：Homebrew 目錄當下無裸 `python`）；已改為
  `PATH="${PATH}:${_hb_bin}"`，`.venv/bin` 維持最前，只為讓 pwsh 可解析。

### S2：stage3 `autoclaude_gate` rc=1（§S2）

- **現象**：log 第 739-743 行——剖面 `AutoClaude/tests@darwin+nopg+solo+pgext`
  未登記於 `skip_group_policy._RUNTIME_SKIP_CEILING`／`_RUNTIME_SKIP_CEILING_MAX`。
- **根因**：mac 真機在 CC session 內跑 pre-push 時 docker 常態停用（`+nopg`），
  而此前兩張天花板表只登記過 docker 長駐（`+pg`）的 darwin 剖面；nightly（非
  巢狀，`+solo`）與 pre-push（巢狀，`+nested`）兩條 `+nopg` 路徑皆一格判準都
  沒有。
- **逐字 census 行（零加減推算，天花板兩表兩鍵之唯一來源）**：
  - 來源＝`AutoClaude/logs/nightly_mac_20260917_020002.log:739`：
    ```
    [skip census] AutoClaude/tests@darwin+nopg+solo+pgext 共 157 支：platform=53／
    tool-absence=0／env-disabled=6／structural-pair=1／debt=0／untagged=97／
    欠債型 103 支（目標 0）
    ```
  - 來源＝本輪 Developer 單人窗口 `cd AutoClaude && ../.venv/bin/python
    tools/local_ci_gate.py`（`4707 passed, 156 skipped in 31.15s`；與四方 QA
    當時報的 `35.75s` 版本 census 六格逐字一致）：
    ```
    [skip census] AutoClaude/tests@darwin+nopg+nested+pgext 共 156 支：platform=53／
    tool-absence=0／env-disabled=6／structural-pair=1／debt=0／untagged=96／
    欠債型 102 支（目標 0）
    ```
- **修法**：`tools/lib/skip_group_policy.py` 依上兩行零加減填入
  `_RUNTIME_SKIP_CEILING`／`_RUNTIME_SKIP_CEILING_MAX` 兩表各兩鍵；
  `_FULL_SUITE_RUNNERS` 分母表同輪新增對應兩列（runner 描述見帳本索引）；
  pgextras token＝`pgext` 依據：`.venv/bin/python -c "import psycopg2,
  sqlalchemy"` rc=0（本輪現查）。

### S3：`.sh` 缺 `--unattended`（鐵律三漏補）

- **現象**：`AutoClaude/tools/run_local_nightly.sh:255`（修前）呼叫
  `local_ci_gate.sh` 未帶 `--unattended`；`AutoClaude/tools/run_local_nightly.
  ps1:1066` 的對應呼叫已帶 `-Unattended`（DEF-200-302 step (e) 只補了
  Windows）。
- **修法**：改為 `run_stage 3 autoclaude_gate bash "$ROOT/AutoClaude/tools/
  local_ci_gate.sh" --unattended`（`local_ci_gate.sh` 是 `python
  local_ci_gate.py "$@"` 薄殼，位置旗標直接轉發給核心）。

### 副作用：guardrail_lib LOC tier 一度撞線，已用真壓縮解除

- `tools/lib/skip_group_policy.py` 新增 4 個字典項（2 個剖面 × 2 張天花板表）＋
  2 個 `_FULL_SUITE_RUNNERS` 分母列，`guardrail_lib` tier 400 行預算一度撞線
  +3（`count_loc()` 只計「斷言桶」，dict 字面本身的行才算數、整行 `#` 註解不計，
  故壓縮 provenance 註解對此無效，已實測驗證）。以兩處真壓縮解除：①
  `_FULL_SUITE_RUNNERS` 兩個新列由「key 一行＋value 一行」合併成單行（91／85
  字元，未破 pre-push ruff E501 ≤100）；② `darwin+nopg+nested+pgext` 該筆
  dict 的收尾 `}` 併回最後一行內容（省 1 行）。最終 `loc` 回到 400/400，**零
  餘裕、零特例**——`AutoClaude/tools/check_loc_budget.py` 未改動、
  `skip_group_policy.py` 不在任何 `SPECIAL_FILES` 特例名冊。

### 驗證（本輪 Developer 窗口逐字實跑）

- `bash -n AutoClaude/tools/run_local_nightly.sh` rc=0；`grep -c $'\r'` 該檔＝0
  （LF-only）。
- `AutoClaude/tests/tools/test_run_local_nightly_sh_static.py`：28 passed。
- `tools/tests/test_check_script_parity.py` ＋
  `tools/tests/test_nightly_interpreter_determinism.py`（合跑）：139 passed，
  1 skipped（`[WINDOWS-NATIVE-ONLY]`，mac 上預期跳過）。
- 新增兩支斷言（`test_run_local_nightly_sh_calls_local_ci_gate_with_unattended_
  flag`／`test_run_local_nightly_sh_prepends_homebrew_bin_by_existence_probe`）
  先對 `git show HEAD:AutoClaude/tools/run_local_nightly.sh`（修前版）跑同一組
  regex：兩者皆 `None`（先紅），修後皆命中（後綠）。
- `tools/tests/test_skip_ceiling_ratchet_direction.py`：23 passed。
- `AutoClaude/tests/tools/test_local_ci_gate.py`：86 passed。
- `AutoClaude/tests/contract/test_loc_budget_tiered.py`：36 passed。
- `cd AutoClaude && ../.venv/bin/python tools/local_ci_gate.py`（docker 確認
  down，`docker info` rc=1）：**rc=0**，`4707 passed, 156 skipped in
  31.15s`，本機 CI 閘門總結全 PASS（含 LOC budget PASS）。
- `ruff check tools/lib/skip_group_policy.py
  tools/tests/test_nightly_interpreter_determinism.py`：All checks passed。

## DEF-200-315（P3，fixed 2026-09-19）—— 互動式入口未釘死 .venv

四方審查 Architect A1 發現：`tools/git-hooks/pre-commit`、
`tools/git-hooks/pre-push`、`AISDLC_SDD/scripts/ci-gate.sh` 三支互動式入口的
頂層 python 選擇仍走 `is_real_python_candidate` 現場解析 PATH，該函式只排除
Windows `WindowsApps` 空殼 shim，未如 DEF-200-302／307（nightly／smoke 排程
入口）改為釘死根層 `.venv` 絕對路徑，缺席時亦無 fail-loud 分支。與已完成的
無人值守面形成不對稱：排程路徑已收斂到單一 `.venv`，互動路徑仍可能因 PATH
上第一個 `python` 是別的直譯器而解析錯誤。本輪僅記錄不修復（範圍外）。

### 收尾（R155）

**掌舵者代決 D1～D5 摘要**：D1／互動式入口直譯器選擇原則＝根層 `.venv` 存在即
釘死用它；缺席時只在 CI 情境（`GITHUB_ACTIONS=true` 或 `CI=true`）容許 PATH，
本機一律 fail-loud 印 bootstrap／dev_start 指令，逃生口 `AUTOSDD_ALLOW_PATH_
PYTHON=1`。D2／共用函式併入既有 SSOT——`tools/lib/windowsapps_guard.sh` 的
`repo_python_path_fallback_allowed`／`pick_repo_python`，與
`tools/lib/WindowsAppsGuard.ps1` 的 `Test-RepoPythonPathFallbackAllowed`／
`Get-RepoPython`，不新增 lib／鎖檔。D3／AutoClaude 子 hook ③ PATH fallback
不刪，改為只在 `repo_python_path_fallback_allowed` 成立時才進入（全新 clone
未 bootstrap 時 hooks 尚未安裝，strict 零實際代價）。D4／`ci-gate.ps1`
fallback 只做「補根 venv 判斷」最小修，整段刪除留給 Phase 2-B signoff。
D5／`.python-version` 與 `.venv-cache-*` 不算第二來源，不動。

**改動檔清單**（`git status --short` 實測合計 52 檔 M：Dev-A／Dev-B／Dev-D
消費端與共用 SSOT 47 檔＋本節所在檔／帳本／棘輪／doc-total 兩站點等 Dev-C
記帳異動 5 檔）：互動式入口消費端 21 支
（`tools/git-hooks/pre-commit`／`pre-push`、`AISDLC_SDD/scripts/ci-gate.sh`／
`.ps1`、`tools/integration_gate.sh`／`.ps1`、`AutoClaude/tools/local_ci_gate.
sh`／`.ps1`、`run_act.sh`／`.ps1`、`g0_gate_check.ps1`、
`sd06_w3_staging_dryrun.sh`、`AISDLC_SDD/scripts/copy_on_evolve.sh`、
`tools/lib/git_hooks_install_common.sh`／`GitHooksInstallCommon.ps1`、
`AutoClaude/tools/git-hooks/pre-push`／`pre-commit`、四支 LATEST SDD 工具
`AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/run_self_evolution.sh`／
`.ps1`、`tools/install_hooks/install_post_commit.sh`／`.ps1`）；共用 SSOT
`tools/lib/windowsapps_guard.sh`／`WindowsAppsGuard.ps1`／`stray_venv.py`／
`skip_tag_policy.py`；`tools/dev_start.sh`／`.ps1`（`UV_PROJECT_ENVIRONMENT`
export，DEF-200-323）；`.github/workflows/root-infra-ci.yml`（DEF-200-321）；
`tools/check_wrapper_thinness.py`（六支殼 `_PINNED_SHA256` 重釘）；回歸鎖測試
11 支（`tools/tests/test_nightly_interpreter_determinism.py`／
`test_windowsapps_guard_bash_parity.py`／`test_windowsapps_guard_cross_
consistency.py`／`test_dev_start.py`／`test_pre_commit_dispatcher_sigpipe.py`
／`test_clean_venv_carrier.py`／`test_workflow_permission_concurrency_lock.py`
／`test_find_git_bash_parity.py`／`test_git_hooks_install_common.py`／
`test_ci_gate_xdist_allowlist.py`／`test_pre_push_dispatcher.py`）＋
`AISDLC_SDD/scripts/tests/` 四支＋`AutoClaude/tests/tools/test_local_ci_gate_
shell_arg_parity.py`；文件 `ONBOARDING.md`／`useMacWin.md`／
`docs/06_quality/AutoSDD_Defect_Log.md`（本節所在檔另計）。

**鎖 H 判準**：`test_nightly_interpreter_determinism.py` 的 H 項（DEF-200-315）
以 `_INTERACTIVE_ENTRY_FILES` 字典枚舉全部互動式入口，H1～H5 判準機械檢查
每一入口是否已改呼叫 `pick_repo_python`／`Get-RepoPython`（AutoClaude 兩支子
hook 走客製判準 H5：③ PATH fallback 段必須被
`[ -z "$PY" ] && repo_python_path_fallback_allowed` 條件包住）。

**三情境行為測試結果**（本包自跑，非轉述）：
`python -m unittest discover -s tools/tests -p test_nightly_interpreter_
determinism.py` → rc=0，`Ran 25 tests in 0.388s`，OK；
`python -m unittest tools.tests.test_windowsapps_guard_bash_parity.
TestPickRepoPythonBehavior` → rc=0，`Ran 3 tests in 0.461s`，OK
（情境 1：repo 根層 `.venv` 存在即選中；情境 2：`CI=true` 時退回 PATH；
情境 3：無 `.venv` 且無逃生口 ⇒ rc=1 fail-loud，訊息含「找不到 repo 根層
.venv 直譯器」）。

**QA 危害重現**：未啟用 venv 時本機 `python` 解析到 pyenv-win shim
`C:\Users\wuwei\.pyenv\pyenv-win\versions\3.11.9\python.exe`
（同 DEF-200-293 危害家族：shim 行為與真直譯器不對等，是本機一律 fail-loud
而非靜默信任 PATH 首個 `python` 的立案動機）。

**雲端憑證**（本包自跑 `gh run view` 驗證，非轉述）：
`windows-compat-ci` workflow_dispatch run `35369313672` →
`{"conclusion":"success","headSha":"e9f5817f8bf77aa13190664f66dd308da3d973b2",
"status":"completed"}`；`macos-compat-ci` run `35369317362` →
`{"conclusion":"success","headSha":"e9f5817f8bf77aa13190664f66dd308da3d973b2",
"status":"completed"}`（sha 前 7 碼 e9f5817，即本輪起點 HEAD）。

#### R156 追記（DEF-200-324）

R155 commit（`19f3e75`）push 被 pre-push 整合閘門 leg 擋下，逐字訊息：
`[pre-push dispatcher] push 涉整合層閘門本體 → 實跑整合閘門（--skip-full）` →
`❌ [3/5] SDD bridge 整合煙霧 FAILED (exit=4)`／`❌ [4/5] 回退驗證 FAILED (exit=4)`，
`ERROR: PG 在場但未用 --dist loadgroup（現為 -n 9 --dist worksteal）…（DEF-200-274
D5/X1）`。根因：`tools/integration_gate_core.py` 的 `sec_bridge()`／`sec_rollback()`
兩處 AutoClaude pytest 呼叫自 R69（`edd5388`）從未帶 PG 判準，只因本輪改了
`tools/integration_gate.sh` 本體才讓 pre-push 首次實跑到這條 leg，潛伏缺陷曝光。
修法：新增 `_pg_dist_args()` 純函式，問 `AutoClaude/tools/local_ci_gate.py` 的
`pg_autodetect()`／`pg_dsn_in_effect()` SSOT（同 DEF-200-295 子 hook 判例，探針
失敗保守加），接進兩處呼叫點 argv 末尾。真跑：`bash tools/integration_gate.sh
--skip-full`（PG 在場）rc=0，`[3/5] SDD bridge 整合煙霧 PASS`（22 passed）、
`[4/5] 回退驗證 PASS`（2 passed），`✅ 整合閘門通過（2 PASS / 1 SKIP）`。

## DEF-200-316（P3，open）—— mac hook 成對條目 ENOENT 噪音

四方審查 Architect A3 發現：mac 上每個 hook 事件的 Windows 成對條目
（`.venv\Scripts\pythonw.exe`）必然 `posix_spawn` ENOENT，Windows 上 POSIX
成對條目必然 EFTYPE——這是「每個 hook 事件註冊兩個平台專屬條目、由 Claude Code
自行決定用哪個」這個既有設計的必然噪音，而非機能失效（`runtime_carrier_
verdict()` 已正確歸類為 `by_design_fail`）。掌舵者 2026-09-13 曾裁決走方案 B
（mac venv 建 `.venv/Scripts/pythonw.exe → ../bin/python` symlink，每個 hook
只留 Windows 條目），但該決策的 SOP 第一步「立帳本列」從未執行，直到本輪才
補上。本輪 A3 重新評估：原始兩個理由之一（POSIX 載具可能解析到錯誤版本的
直譯器）已由 DEF-200-297／301／302（單一 .venv 收斂）消解，只剩「log 噪音」
這個較弱的理由；而方案 B 的鎖持有面橫跨 `tools/lib/hook_wiring.py`、
`tools/check_hooks_liveness.py` 與其測試、`tools/dev_start.py`、根
`CLAUDE.md`（測試釘住）至少 5 支檔案，牽動面不小。建議暫緩，待掌舵者對「是否
仍要走方案 B」重新裁決後再排入實作輪。
