# CrossPlatform_R85_Review_QA — R85 四方複審／QA 獨立複審（macOS）

> **本檔的資格**：R85 QA 獨立複審 findings 的唯一居所。**唯讀複審**：本輪 QA 一個既有檔都沒改、
> 一次 git 寫入都沒有；所有注入實驗都在 scratchpad 的拋棄式副本上做，並以 sha256 證明還原。
>
> 🔴 **體例**：每筆 finding 附 ①可重跑指令 ②**我這回合真跑出來的輸出** ③為什麼是問題
> ④修法草案 ⑤持有面（鐵律七）⑥嚴重度。**讀 rc 不接管線**；命令替換 `$(...)` 一律不用來包
> 受測指令（`echo "$(cmd) rc=$?"` 會洗掉 `$?`，P6 本輪實例）。
>
> 🔴 **平台劃界**：本輪在 **macOS**（darwin）。凡涉及 Windows 執行期行為者一律標
> 「**靜態推論、未在真機驗證**」。
>
> 🔴 **工作樹是移動標的（本檔最重要的閱讀前提）**：複審期間收尾單人窗口仍在寫檔。
> 本檔每一筆量測都附**時刻**；同一支指令在 09:5x 與 10:1x 會得到不同答案，這不是矛盾，
> 是兩個不同的磁碟狀態。凡本檔說「紅」，指的是**該時刻**為紅。

---

## §0 本包這回合真跑過的指令與 rc（取證清單，**不採信任何人貼的 rc**）

| # | 指令（絕對路徑 python，讀 rc 不接管線） | **我的 rc** | 時刻 | 與各包宣稱 |
|---|---|---|---|---|
| 1 | `.venv/bin/python tools/run_root_unittests.py` | **1**　`Ran 3284 / FAILED (failures=7, skipped=44)` | 10:02 | ❌ 與 improving_109 §2#1 的 `rc=0` **不符** |
| 2 | `cd tools/tests && ../../.venv/bin/python -m unittest discover` | **1**　`Ran 3284 / FAILED (failures=6, skipped=44)` | 10:02 | ❌ 兩載具**失敗支數不同**（見 QA-06） |
| 3 | `.venv/bin/python tools/check_defect_log_crossref.py` | **0**（warning 三類在線；未結 **89**） | 09:57 | rc 相符；**未結數不符 §5**（見 QA-04） |
| 4 | `.venv/bin/python tools/check_hooks_liveness.py` | **0** | 09:57 | ✅ 相符 |
| 5 | `.venv/bin/python tools/check_ntfs_paths.py` | **0** | 09:57 | ✅ 相符 |
| 6 | `.venv/bin/python AutoClaude/tools/check_loc_budget.py --json` | **0** | 09:57 | ✅ 相符 |
| 7 | `cd AutoClaude && ../.venv/bin/python -m pytest tests -q` | **0**　`4466 passed, 73 skipped in 109.55s` | 10:00 | ✅ 相符（73 skip 屬實） |
| 8 | `cd AutoClaude && ../.venv/bin/lint-imports` | **0**　`Contracts: 9 kept, 0 broken.` | 10:11 | ✅ 相符 |
| 9 | `cd AISDLC_SDD && bash scripts/ci-gate.sh` | **1**　`2 failed, 341 passed, 2 skipped, 31 subtests passed` | 10:12 | ❌ **未見任何包宣稱過它**（見 QA-03） |
| 10 | `.venv/bin/python tools/probe/reset_window_distribution.py` | **0**　母體 1069 支／7 個相異 reset 字面／15 episode | 10:11 | ✅ 可重跑 |
| 11 | `.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` | 0，但印 `82838, 83296, +458` | 09:53 | ❌ 與「(+0)」宣稱**直接矛盾**（見 QA-02） |

**§5 驗收條件對帳（我的判定）**：`護欄層淨額 ≤ 0` ❌ ／ `_REPIN_ROUND_NET_CAP ≤ 3200` ✅（已下修，但本輪淨額 482 > 0）／
`帳本未結 ≤ 80` ❌（89）／`bytes 餘裕 ≥ 13 KB` ✅（主檔 211,736 B，餘裕 ~33 KB）／`全樹閘門 rc=0` ❌（#1／#2／#9 皆 rc=1）。

---

## §A blocking

### QA-01 根層閘門在**兩種載具**上皆 rc=1，而 improving_109 §2 開場基線寫 `rc=0` 🔴 blocking

**現查**（前景阻塞、讀 rc 不接管線）：
```bash
.venv/bin/python tools/run_root_unittests.py; echo rc=$?
cd tools/tests && ../../.venv/bin/python -m unittest discover; echo rc=$?
```
**我這回合的輸出（10:02）**——runner：`Ran 3284 tests in 445.346s` → `FAILED (failures=7, skipped=44)`；
discover：`Ran 3284 tests in 446.868s` → `FAILED (failures=6, skipped=44)`。失敗聯集 7 支：

| # | 失敗測試 | 成因 |
|---|---|---|
| 1 | `test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet.test_a_net_zero_swap_is_red` | 護欄層 +458（QA-02） |
| 2 | 同檔 `.test_the_line_ratchet_took_over_and_has_teeth` | 同上 |
| 3 | 同檔 `TestShrinkOnlyRatchet.test_ratchet_is_independent_of_git_state` | 同上 |
| 4 | `test_doc_loc_baseline_freshness_r60.TestR67R3…test_every_lock_in_this_file_holds_under_every_simulated_platform` | 本檔有鎖的結果隨 `sys.platform` 改變 |
| 5 | 同檔 `TestR74IronLawMechanismAccounting.test_the_two_floors_are_not_themselves_stale` | `_IRON_LAW3_COVERED_FLOOR=19` 落後現值 21（上限 1） |
| 6 | `test_platform_utils_dedup.TestR75StdioUtf8HasOneImplementation.test_both_public_names_have_real_consumers` | **只在 runner 版紅**＝並行污染（QA-06） |
| 7 | `test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_e501_debt_only_shrinks` | `139 → 140`（QA-05） |

**10:13 複查**：#4／#5 已被收尾窗口修掉（同兩支測試單獨重跑 rc=0）；#1~#3 轉成同檔**另外 7 支**紅（重釘進行中，見 QA-02）；#7 仍紅。

**為什麼是問題**：§5 逐字要求「全樹閘門 rc=0」，而本輪的開場基線表把 #1 寫成 `rc=0` —— 那一格若是
在派工前量的，它就已經過期；若是收尾後量的，它與磁碟不符。無論哪一種，**它今天不能拿來當通過的憑證**。
**修法草案**：收輪前由收尾單人窗口重跑一次並把 §2 那張表換成當回合值（或標明它是「派工前基線」而非「收輪憑證」）。
**持有面**：收尾單人窗口（跨 `tools/tests/**` 與 `docs/04_planning/`）。

---

### QA-02 §1／line 99「本輪護欄層淨額 +0、第一個非上升輪」是**假宣稱**；真值 **+482**，第九個連續上升輪 🔴 blocking

**現查**：
```bash
.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
cd tools/tests && ../../.venv/bin/python -m unittest test_adr_xplat001_c1c2_lock
```
**我這回合的輸出**：
- 09:53 —`# _GUARD_LINES_REPIN_LOG 新列：("R<n>", 82838, 83296, +458, …)`，逐檔漂移 4 支
  （`test_platform_neutral_paths.py 5959→6180`、`test_doc_loc_baseline_freshness_r60.py 7027→7165`、
  `test_block_destructive_git_r83.py 1889→1982`、`test_check_hooks_liveness.py 3366→3372`）。
- 10:13 — 該鎖自己印出逐輪淨額 `[(77,3505),(78,2243),(79,3120),(80,2334),(81,3033),(82,5400),(83,5260),(84,3755),(85,482)]`，
  並逐字失敗於 `整段稽核痕跡至今**一列都沒有下降過**……R85 起這句話為假（該輪是第一次淨減法輪）`。
- 同時 `[總量不符] docs/04_planning/AutoSDD_improving_109.md` — 該檔 `<!-- guard-total:R85 -->` 標記仍寫 `82838 → 82838（+0）`。

**為什麼是問題**：這是本輪的**主結論**（§1「R85 是減法輪」、§5 第一條驗收）。line 99 那句話還附了
「憑證＝`--print-guard-lines` 印 (+0) 且逐檔漂移 0」——**憑證與宣稱在同一支指令下互相否證**。
更關鍵的是形態：本 repo 已判過「重釘的唯一成本是補一列紀錄」，而本輪補的那一列自己承認
`本輪方向仍與 M1 相反（護欄層總量上升）`，卻同時在計畫書裡留著「(+0)」的舊句 ⇒ **同一份知識住兩個家、只有一個家被改**（R73 `Find-GitBash` 同型）。
**修法草案**：①line 99 與 §1 改寫成真值（+482，第九個上升輪），並明說款(11) 的連續上升計數**未**歸零；
②`_REPIN_ROUND_NET_CAP` 的到期義務改以「下一輪必須淨額 ≤ 0」承接並登記帳本列。
**持有面**：`docs/04_planning/AutoSDD_improving_109.md`（常數/宣稱）＋`tools/tests/test_adr_xplat001_c1c2_lock.py`（史料＋消費端）⇒ 收尾單人窗口一次做完。

---

### QA-03 `AISDLC_SDD/scripts/ci-gate.sh` rc=1：新根層消費檔未列入兩支 compat-CI 的 paths 🔴 blocking

**現查**：
```bash
cd AISDLC_SDD && bash scripts/ci-gate.sh; echo rc=$?
grep -c "unattended_authz" .github/workflows/macos-compat-ci.yml .github/workflows/windows-compat-ci.yml
```
**我這回合的輸出（10:12 / 10:13）**：`2 failed, 341 passed`；逐字
`根層消費檔未列入 macos-compat-ci.yml paths（只改該檔時其回歸鎖不會跑，DEF-101-042 同構）：['tools/lib/unattended_authz.py']`（windows 同）；
grep 兩檔皆 **0**。

**為什麼是問題**：①它是本輪**唯一一支 rc=1 而沒有任何包宣稱過**的閘門——沒有人跑它；
②`tools/lib/unattended_authz.py` 是 P3 新建的檔，而 P3 在 §3 登記的持有面逐字是 `AutoClaude/**` ⇒
**本輪自己就是鐵律七的反例**：一個包把檔案落在別人的持有面，於是「常數在這裡、CI paths 消費端在那裡」，
單包結構上補不完。
**修法草案**：把 `tools/lib/unattended_authz.py` 補進兩支 workflow 的 `paths:`（＋`root-infra-ci` 若同表要求）。
**持有面**：`.github/workflows/**` ⇒ 收尾單人窗口。**嚴重度**：blocking（CI paths 缺口＝該鎖在雲端結構上不會跑）。

---

### QA-04 §5「帳本未結 ≤ 80」未達成：實測 **89**，比開場基線（88）**更高** 🔴 blocking（對驗收條件）

**現查**：`.venv/bin/python tools/check_defect_log_crossref.py --unresolved-count`
**輸出（09:58）**：`未結列數＝89／全部 181 列｜warn=86 fail=98`，並印
`⚠️ 未結列 89 筆……已逼近 fail 線 98（距 9 筆）`。
**為什麼是問題**：P1 的派工主題逐字是「未結 88→≤80」。本輪新增的 `DEF-200-095`~`DEF-200-104` 十列
把它推到 89 ⇒ **淨效果是反向的**。這不必然是 P1 的錯（新缺陷本來就該登記），但它讓 §5 那一條在帳面上不成立，
而目前沒有任何文字承認這件事。
**修法草案**：把 §5 那一條改成「**淨**未結 ≤ 80」或「本輪結掉 ≥ N 筆」（分子分母分離，同鐵律三覆蓋率棘輪的教訓：
把「還有幾筆沒結」與「我們知道有幾筆」綁成同一個數字，會讓誠實登記變成有代價的事）。
**持有面**：`docs/04_planning/AutoSDD_improving_109.md` ＋ `docs/06_quality/AutoSDD_Defect_Log.md`。

---

### QA-05 `test_e501_debt_only_shrinks` 棘輪被違反：139 → 140 🔴 blocking（單邊棘輪）

**現查**：`cd tools/tests && ../../.venv/bin/python -m unittest test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_e501_debt_only_shrinks`
**輸出（10:13，仍紅）**：`AssertionError: 140 not less than or equal to 139 : tools/tests/ 的過長行由 139 增至 140 —— 本棘輪只准往下改`
**為什麼是問題**：這正是 §6 禁止事項 3「不准為了讓紅變綠而放寬棘輪」在防的那條線的另一側——它今天是紅的，
而它紅的原因是本輪新寫的行沒折。**修法**＝把新寫的那一行折掉（不是調高 139）。
**持有面**：`tools/tests/**` ⇒ 收尾單人窗口。

---

### QA-06 測試在 **repo 根**建臨時目錄，兩支並行跑同一棵樹會互相污染 🔴 blocking（取證可信度）

**現查**：`grep -n "_scan_surface_probe" tools/tests/test_platform_utils_dedup.py`
**輸出**：`588: probe_dir = _REPO_ROOT / f"_scan_surface_probe_{os.getpid()}"`
**本回合的直接證據**：同一份磁碟狀態下，runner 版比 discover 版**多一支** FAIL，且那支的 traceback 逐字是
`FileNotFoundError: …/AISDCL_Agent/_scan_surface_probe_46659/probe_platform_helper.py` ——
`46659` **不是我的行程**（我的兩支跑在別的 pid），它是同時在跑的另一個複審者的探針目錄，
在我的掃描器讀它的瞬間被對方清掉了。
**為什麼是問題**：①四方複審**本來就是並行的**，而這使「全樹閘門 rc」在複審期間**不可重現**——
失敗與否取決於別人跑到哪一步；②失效表徵是一個看起來很像真缺陷的 `FileNotFoundError`
（「掃描面已縮小，本棘輪的凍結值不再有意義」），會把人指往完全錯的方向；
③它同時**污染工作樹**（探針目錄短暫出現在 repo 根，`git status` 會看到）。
**修法草案**：探針目錄改建在 `tempfile.mkdtemp()` 下，並把「掃描面必須看得到它」這件事改用
明文注入的掃描根（把 `_REPO_ROOT` 參數化）而不是真的往 repo 根寫檔。
**持有面**：`tools/tests/test_platform_utils_dedup.py`（常數＋消費端同檔）⇒ 可單包做完。
**嚴重度**：blocking（它讓本輪所有「全綠」宣稱在並行期間結構上不可複驗）。

---

## §B AC-(c) 裁決複驗（掌舵者本輪指定 QA 驗的那一題）

**我的合成注入（在 scratchpad 拋棄式副本 `…/scratchpad/AC_mut` 上做，tracked 檔一個都沒動）**：

| 注入 | 內容 | 我的 rc | 打中誰 |
|---|---|---|---|
| 基線 | 未注入 | **0** | `16 passed in 1.99s` |
| M1 | 拿掉 `notifier.notify()` 的 `if not enabled: … return` | **0** ⚠️ | AC-(c) 鎖**全綠**；改跑 `tests/utils/test_notifier.py` 才紅（`TestNotifyDisabled::test_disabled_skips_all_backends`，**既有**測試而非本鎖） |
| M2 | `daemon=True` → `daemon=False` | **1** | 僅 `TestSessionEndIsNotHeldHostageByThePopup::test_platform_backend_runs_inside_a_daemon_thread` |
| M3 | 追加 `ctypes.windll.user32.MessageBoxW` 降級路徑 | **1** | 僅 `TestDegradationNeverEscalatesToAModalWindow::test_no_modal_dialog_api_anywhere_in_the_notification_path` |
| M4 | 某一分支漏傳 `enabled=self._enabled` | **1** | 僅 `TestEveryBranchPassesEnabledExplicitly::…[evolution]` |

**還原證明**：`shasum -a 256` 對 `notifier.py`／`notification_plugin.py` 逐字等於工作樹本尊
（`f4e79bdb…f68ec`／`53f9131d…1f268`）。

### 三條判準逐條

| 判準 | P3 的裁決 | **我的裁決** | 依據 |
|---|---|---|---|
| ① 有會紅的鎖 | 是 | **維持：是** | M2／M3／M4 各自 rc=1 且**只**打中該打的一支，零串音。**但補一筆**：M1（拿掉 notifier 側 `enabled` 守門）**這支鎖抓不到**——它的 docstring 逐字宣稱「判準刻意下沉到 `utils.notifier` 的平台後端……證得到 `enabled` 有沒有被傳下去」，而真正抓到 M1 的是既有的 `tests/utils/test_notifier.py`。⇒ 該 docstring 對自己的鑑別力**多報了一層**（防禦縱深的第二層其實由別人守）。這不改變①的結論，但那句 WHY 應訂正。 |
| ② 生產碼落在**所報症狀**的因果鏈上 | 未成立 | **維持：未成立** | 所報症狀＝`DEF-200-060` 逐字「黑框一閃即消、**約每 15 分鐘一次**」。逐行讀 `notifier.py`：三條後端是 plyer（in-process）／`osascript`（**darwin 專用**）／win10toast（in-process），**Windows 路徑上沒有任何會生 console 視窗的 spawn**；15 分鐘節律的 SSOT 是 `tools/session_resume_planner.py:319 SENTINEL_INTERVAL_SECONDS = 900`，完全在 AutoClaude 之外（同檔 `:726` 逐字記載「掌舵者當場回報：哨兵每 15 分鐘彈一個 console 視窗」）。⇒ AC-(c) 的 R84 交付治的是**另一個**彈窗（toast 泡泡、session 內），不是所報症狀。**靜態推論、未在 Windows 真機驗證。** |
| ③ 殘留風險有登記 | **否** | 🔴 **推翻：是（但附一個到期條件）** | `DEF-200-063` 在帳本 `:210`，狀態 `open（承接輪次：**R85**）`，逐字列出三項未驗與三項剩餘失明（載具可能不存在 ⇒ 守衛 fail-open／29 份凍結 settings 不判形態 A~F／`claude_md_freshness.py` 子行程未帶 `CREATE_NO_WINDOW`）。⇒ 殘留風險**有**登記，P3 這一格判錯。**到期條件**：本輪（R85）同樣零 Windows 真機 ⇒ 收輪時該列若不改派 R86，就會落回 `lagging_clock_notes()` 的 fail-open 窗口（`check_defect_log_crossref.py` 已對它印 warning），變成「登記了但沒人承接」。 |

### **QA 最終裁決：修正為「部分交付，且交付的不是所報症狀那一半」**

- **是交付**：`enabled` gating 與 daemon 化這兩件事今天有牙、可注入證偽（M2/M3/M4）、生產碼同 commit 落地。
- **不是交付**：它與掌舵者所報的「黑框／15 分鐘」**沒有因果關係**。⇒ `AC-(c)` 在驗收表上
  **不得記為「已交付」，也不得記為「零交付」**；正確的記法是
  「**已交付一個相鄰缺陷（session 內 toast 的 gating 與吊住 exit）；所報症狀（黑框 ×15 分鐘）仍為已定位、未驗證**」。
- **與 P3 的差異**：僅在判準③（我判「有登記」）。整體結論方向一致。
- **本裁決的邊界**：Windows 真機零驗證 ⇒ 「修好了沒」這件事本輪**任何人都答不了**，包括我。

---

## §C 假宣稱清單（成熟度 M2 的分子）

逐筆去驗本輪 12 包報告與 findings 檔的「已驗證／rc=0／實測」宣稱，**證偽 5 筆**：

| # | 宣稱（出處） | 逐字 | 我的反證 | 型 |
|---|---|---|---|---|
| F1 | `AutoSDD_improving_109.md:99` | 「本輪護欄層累積淨額＝ 82838 → 82838（+0）……憑證＝`--print-guard-lines` 印 (+0) 且逐檔漂移 0」 | 同一支指令印 `82838, 83296, +458`；該鎖自己印 `(85, 482)` | **數字被寫成常數而其實是量測值** |
| F2 | `AutoSDD_improving_109.md:11,22` | 「R85 是**減法輪**……本輪的成敗判準就是這個數字」／`<!-- guard-total:R85 -->`「第一個非上升輪」 | 逐輪淨額 `(85, 482)`＝第九個連續上升輪；款(11) 連續計數**未**歸零 | **主結論被證偽** |
| F3 | `AutoSDD_improving_109.md:30`（§2#1） | `rc=0`；`[skip census] … 44 支` | skip census 那一半**屬實**（我實測逐字相同）；`rc=0` 那一半**不真**（我兩種載具皆 rc=1） | **半真半假的取證行**（最難看見的一種） |
| F4 | `AutoSDD_improving_109.md:79`（§5） | 「帳本未結 ≤ 80」列為驗收條件 | 實測 89，且比基線 88 更高 | **驗收條件未達成而無人承認** |
| F5 | `CrossPlatform_R85_Scan_Findings.md` §A-1 的「現查」 | `grep -n "_SAFE_COND_PATTERN" AutoClaude/autoclaude/execution/mutation_applier/_conditional.py` | 該檔今天**零命中**——同輪 P3 已把它改名並搬到 `AutoClaude/autoclaude/utils/shell_deny_chars.py:12` | **現查指令在同一輪內失效**（P4 是唯讀包，非其過失；但該 finding 的唯一居所現在指向不存在的符號） |

**同時查的三個特定形態，結果**：
- **有沒有人用「已交棒」代替結算？** 本輪**沒有**（`R84_HANDOFF.md:111` 已把這條寫成禁令，本輪各檔皆逐列給狀態）。
- **有沒有把靜態推論寫成事實（Windows）？** **沒有**。`CrossPlatform_R85_Scan_Findings.md` 檔頭與逐節都標「靜態推論、未在真機驗證」；
  `improving_109 §4.1` 逐字「訴求 7 本輪一律標『已定位、未驗證』，不得升級為『已修復』」。這一項紀律本輪守住了。
- **有沒有數字被寫成常數而其實是量測值？** **有**，即 F1／F2（且它們就住在專門講「會漂移的量測值一律不寫死」的那份檔裡）。

**取數管道自證（對照組）**：本節「證偽 5 筆」不是「掃不到就說沒有」——同一批檔內我也逐筆**證實**了
會命中的對照：§2#3~#6 四支 rc=0 我獨立重跑皆相符、`73 skipped` 相符、`Contracts: 9 kept` 相符、
P4 取證 #6 的六句 regex 判決我逐句真跑**逐字相同**（`python -c "print(1)"`→False、`rm -rf /`→True）。
⇒ 我的驗證管道對「宣稱為真」也會回真，不是恆紅。

---

## §D skip 與測試品質（訴求 S1／M6）

### D-1 根層 44 支：分類抽樣**正確**，`debt=0`／`untagged=0` 屬實
`run_root_unittests.py` 當回合逐字印
`[skip census] tools/tests@darwin 共 44 支：platform=44／tool-absence=0／env-disabled=0／structural-pair=0／debt=0／untagged=0／欠債型 0 支（目標 0）`。
標籤面獨立抽樣（`grep -ohE "\[[A-Z-]+\]" tools/tests/*.py | sort | uniq -c`）：
`[WINDOWS-NATIVE-ONLY] 32`／`[POSIX-NATIVE-ONLY] 12`／`[MAC-NATIVE-ONLY] 6`／`[TOOL-ABSENCE] 10`……
—— 站點數 ≠ 執行期支數（一個站點可涵蓋多支），但**沒有任何一支被錯分成 platform 而其實是欠債**：
44 支的 reason 全部帶 `[WINDOWS-NATIVE-ONLY]`，其述詞是 `os.name != "nt"` 這一族，在 mac 上結構性不可執行。

### D-2 🔴 「那 44 支今天有沒有憑證證明它們在 Windows 上真的跑過？」——**沒有。明確答案：否。**

兩層理由，第二層是結構性的：

1. **時間軸**：`tools/lib/skip_group_policy.py:331` 那段註解逐字寫著
   「當回合實測：`[skip census] tools/tests@win32 共 38 支：platform=37／env-disabled=1／其餘 0`」，
   而該段的落款是 **R82**。本輪（R85）零 Windows 真機 ⇒ win32 那一格已**三輪未量**，
   期間 `tools/tests/` 至少有 4 支檔改動（QA-02 的逐檔漂移表）。
2. **粒度**（更致命）：`skip_group_policy.py` 自己在 `_TAG_HOME_PLATFORMS` 上方的〈誠實劃界〉節逐字承認——
   「本判準的粒度是**剖面**不是**測試**——它證明得了『win32 這個剖面有人量過健康值』，
   **證明不了『那 44 支逐一在 win32 真的執行過』**（win32 當回合的 `platform=37` 支 skip 裡有沒有混進其中幾支，
   分群粒度看不出來）」。⇒ 即使**明天**在 Windows 真機重量一次，也仍然回答不了 M6，
   因為兩邊比對的是**計數**不是**測試 id 集合**。
   同檔還登記了達成判準：「兩個以上剖面各自留下可 diff 的 id 清單檔，且判準讀清單而不是讀計數」。
   另有 `tools/tests/test_dev_start.py:5711` 逐字自陳「這一支目前仍無覆蓋證據」。

⇒ **M6（從未在任何平台執行的測試歸零）今天不僅未達成，連「達成了沒」都量不出來。**
**修法草案**：`run_root_unittests.py` 增 `--emit-executed-ids <path>`（每個剖面落一份可 diff 的 test-id 清單），
判準改成「全集 − 各剖面 id 聯集 = ∅」。**持有面**：`tools/run_root_unittests.py`（產出端）＋
`tools/lib/skip_group_policy.py`（判準端）＋`tools/tests/`（鎖）——**三者不同檔，依鐵律七不得切給不同並行包**。
**嚴重度**：major（訴求 S1 的真門檻）。

### D-3 AutoClaude 側 73 支：`[ENV-DISABLED]` 那 11 支 claude-CLI 測試，**分類存疑** major

**現查**：`cd AutoClaude && ../.venv/bin/python -m pytest tests -rs -q`
**輸出（逐字節錄）**：`tests/test_gap014_020.py` 8 支 ＋ `tests/test_gap039_049.py` 3 支＝11 支，reason 逐字：
> `[ENV-DISABLED]` 【未啟用，非缺件】需要 claude CLI binary 且非巢狀 Claude Code session。🔴 成因**因平台而異**：
> Windows 上是 wexpect pty spawn 掛住不回（…DEF-101-913）；macOS 上 wexpect 根本沒安裝、該機制結構上到不了，
> 但 R85 實測 `env -u CLAUDECODE pytest` 仍逾 600s 未完成 ⇒ mac 側成因**未知且未歸因**（不得寫成已歸因）。

**我的判定：這是**合理的 skip、**不**合理的**分類**。三個理由：
1. **標籤語意與內容互相矛盾**：`[ENV-DISABLED]` 的括號註解逐字是「**未啟用，非缺件**」，
   而同一段 reason 自己說 mac 側「成因未知且未歸因」。**一個未歸因的 600 秒吊住是缺件（欠債），不是「沒開開關」。**
   照現行分類它計入 `env-disabled` 桶 ⇒ 對 `open_debt()` 貢獻 0 ⇒ **它在治理數字上是隱形的**。
2. **它給的跑法在本平台不可執行**：逐字「在**非** Claude Code session 的 **PowerShell** 執行」——
   這是 Windows 指示，而本輪機器是 mac。⇒ 在 mac 上這 11 支**沒有任何已知的跑法**。
3. **它宣稱的覆蓋憑證是外部且過期的**：「2026-08-06 nightly log 實測會真的跑」——距今 6 天、在 Windows、
   本輪無法複驗。**靜態推論、未在真機驗證。**

⇒ 這 11 支正是 D-2 那個問題的具體實例：**它們今天在 mac 上不跑，在 Windows 上「據說」會跑，而沒有人能出示 id 級憑證。**
**修法草案**：mac 側那一半改標 `[DEBT]` 並開一列帳本承接「600s 吊住未歸因」；
或照 reason 自己指的治本方向（SD_10 P3-R56-2 fake-executor 重寫）落地，使兩平台都跑得到。
**持有面**：`AutoClaude/tests/test_gap014_020.py`／`test_gap039_049.py`（標籤）＋`tools/lib/skip_tag_policy.py`（分類判準）
＋帳本 —— **三處不同持有面**。

---

## §E 挖深：「測試存在但沒有驗到東西」

**方法**：AST 掃全 `tools/tests/*.py` ＋ `AutoClaude/tests/**/test_*.py`，找
①無 assert／raises／fail 且不委派 helper 的測試 ②`assert True` 變形 ③常數引數的 `assertTrue/False`。
**對照組自證**：粗掃回 206 筆「無 assert」——逐筆判讀後**絕大多數是假陽性**（委派給 `self._expect_red(...)` 這類 helper）；
加上「不委派 helper」這一條後收斂到 **13 筆**。⇒ 我的掃描器對「有牙的測試」不會誤報，數字可用。

| 發現 | 座標 | 判定 |
|---|---|---|
| `assert True` 恆真斷言 **2 處** | `AutoClaude/tests/integration/test_pgvector_real_recall.py:299`、`AutoClaude/tests/test_conftest_windows_native_skip_report.py:48` | **不是新缺陷**：前者的 skip reason 自己逐字點名「本 case 在 fixture 存在時落到的是下面那句 `assert True`，那是一個恆真斷言，量不到任何 RTO」，並把「同時把它改成真實量測」寫成解除條件之一。**這是本 repo 做得最好的一類自我登記，予以肯定。** |
| 無斷言且不委派 helper | 13 筆，主要在 `test_run_root_unittests.py`（`test_tagged`/`test_plain`/`test_skipped`/`test_ran`）與 `AutoClaude/tests/core/ports/test_observability_port.py::test_null_observability_is_pure_noop` | 前者是**餵給 discovery 的合成夾具**（不是真測試，被別的測試當語料用）＝合理；後者是「no-op 不得拋例外」的 smoke，鑑別力弱但語意正確。**皆不列 blocking。** |
| 被 mock 掉受測對象本身 | 未發現（AC-(c) 鎖刻意**避開**這個陷阱：它 patch 的是 `_try_plyer` 等**後端**而不是 `notification_plugin.notify`，docstring 並逐字解釋了為什麼——這是正面示範） | — |

### E-1 subTest 併表「一個不少」——**P2 的宣稱屬實，我數給你看**

| 併表族 | 拿掉的測試方法 | 併成 | 表內樣本數 | 對帳 |
|---|---|---|---|---|
| `test_check_wrapper_thinness.py` 禁用樣板 | **10** 支（`test_forbidden_*_detected`） | `test_forbidden_patterns_are_detected` | `_FORBIDDEN_CASES` = **10** | ✅ 10→10 |
| `test_dev_start.py` R23 假陰性 | **3** 支 | `test_r23_false_negative_variants_are_still_detected` | `_FALSE_NEGATIVE_CASES` = **3** | ✅ 3→3 |
| `test_dev_start.py` R25 假陽性 | **2** 支 | `test_r25_end_suffixed_words_do_not_false_trigger` | `_FALSE_POSITIVE_CASES` = **2** | ✅ 2→2 |

**加分**：`test_forbidden_patterns_are_detected` 內含
`assertEqual(len(self._FORBIDDEN_CASES), 10, "注入樣本數變了——本族是史料回歸鎖，樣本只准增不准減")`
—— **併表的同時把「樣本數會靜默縮水」這個新風險自己補上了鎖**。這正是本輪減法應有的做法。
另兩族（`test_check_script_parity.py` 124→124、`test_windowsapps_guard_*` 28/71→28/71、`test_schedule_capability_parity.py` 19→19）
方法數零變動，無縮水風險。

---

## §F `run_root_unittests.py` 的早退分支：合理嗎？

**P11 的觀察屬實**（`main()` 在 `report_min_tests_note_stale_tokens()`／`report_missing_third_party_prereqs()`／
`report_untagged_windows_skip_decorators()` 任一為真時 `return 1`，一支測試都不跑，畫面上沒有 `FAIL` 行）。
**但我的判定是：這個早退在 rc 這一軸上是安全的，風險只在閱讀面。**

**取證**：`grep -n "return 0" tools/run_root_unittests.py` 全檔只有 **2 處**（`:340`／`:344`），
兩處都在 `report_skip_census()` 內——那是**跑完之後**的統計，不在早退路徑上。
三條早退全部 `return 1`。⇒ **早退路徑結構上做不出 rc=0**，任何正確讀 rc 的呼叫端
（pre-push root-infra leg、三支 CI step）都不可能被騙成綠。

**⇒ 對「它讓多少次『全綠』宣稱其實沒有意義」的答案：0 次**，只要那個宣稱是**讀 rc** 得來的。
真正的風險是**讀畫面**：早退時 stderr 有訊息但沒有 `Ran N tests` 也沒有 `FAIL`，
一個以「有沒有 FAIL 行」判斷的人（或模型）會判成通過。這與鐵律六「等待／確認的機制自己壞掉，
失敗表徵與正常進行相同」同型，只是換成「**成功**的表徵與**沒跑**相同」。
**修法草案（minor）**：三條早退在 return 前多印一行醒目句，逐字說明「**本次一支測試都沒有執行**」。
**持有面**：`tools/run_root_unittests.py` 單檔。**嚴重度**：minor。

---

## §G blocking 清單（附持有面）

| # | 標題 | 持有面（常數／史料／消費端） | 可否派並行包 |
|---|---|---|---|
| QA-01 | 兩種載具的根層閘門皆 rc=1，§2 基線表寫 rc=0 | `tools/tests/**` ＋ `docs/04_planning/AutoSDD_improving_109.md` | ❌ 收尾單人窗口 |
| QA-02 | 「淨額 +0／第一個非上升輪」為假；真值 +482 | `AutoSDD_improving_109.md`（宣稱）／`test_adr_xplat001_c1c2_lock.py`（史料＋消費端） | ❌ 收尾單人窗口（重釘是其專屬動作） |
| QA-03 | SDD ci-gate rc=1：`tools/lib/unattended_authz.py` 未入兩支 compat-CI paths | `.github/workflows/{macos,windows}-compat-ci.yml` | ✅ 單包可做（但**不得**與 P3 同包，見鐵律七） |
| QA-04 | 未結 89 > 驗收線 80，且高於基線 88 | `AutoSDD_improving_109.md` ＋ `AutoSDD_Defect_Log.md` | ❌（帳本 ceiling 與登記面跨檔，R84 已有判例） |
| QA-05 | `test_e501_debt_only_shrinks` 139→140 | `tools/tests/**`（折行即可） | ✅ 單包可做 |
| QA-06 | 測試往 repo 根寫 `_scan_surface_probe_<pid>`，並行複審互相污染 | `tools/tests/test_platform_utils_dedup.py` 單檔 | ✅ 單包可做 |

**major（非 blocking，但要有承接列）**：D-2（M6 結構上量不出來）／D-3（11 支 `[ENV-DISABLED]` 分類存疑）／
§B 判準①的 docstring 多報一層鑑別力／F5（P4 findings 的現查指令已 stale）。

---

## §H 誠實劃界（本次複審**沒有**做到什麼）

1. **Windows 真機零驗證。** 本檔任何涉及 Windows 執行期的結論（AC-(c) 的黑框歸因、win32 skip 剖面、
   `pythonw.exe` 載具是否解析得到）**全部是靜態推論**。
2. **工作樹是移動標的。** 收尾窗口在我量測期間持續改檔（QA-01 的 #4/#5 在 11 分鐘內由紅轉綠，
   QA-02 的重釘在我兩次量測之間發生）。⇒ **本檔的 rc 是時刻快照，不是收輪憑證**；
   收輪時必須由收尾窗口在**所有包停工後**重跑一次，那一次才是憑證。
3. **並行污染未被排除。** 因 QA-06，我的兩次全樹跑與其他複審者的跑互相干擾過至少一次
   （已定位到具體 pid 與檔名）。我沒有重跑到「獨占工作樹」的乾淨一次。
4. **12 包報告我只抽樣。** 本輪 `docs/06_quality/CrossPlatform_R85_*.md` 磁碟上只有 **2** 支
   （`Scan_Findings`／`Ledger_Closure`；另有 `AutoSDD_R85_Archive_Proposal.md` 不同前綴），
   其餘各包的交件回報**不在磁碟上**
   ⇒ 我只驗得到落檔的宣稱。**「報告不落檔」本身就讓 M2 的分母不可稽核**，列入建議。
5. **`AutoClaude pytest` 我沒有跑 `-m pg_real` 與 `perf`**（前者需 `SD07_REAL_PG_E2E_ENABLED`，
   後者對機器負載敏感且本輪機器忙碌）。
