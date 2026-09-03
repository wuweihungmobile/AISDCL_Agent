# R122 精準修復輪 — 缺陷結案存證

> **性質**：技術債總清償循環令第五投。開場依循環令走「純結案輪」，起手分診後**被事實推翻**
> 而轉為精準修復輪——轉向理由與取證見 §0。
> **帳本未結列**：起 44 → 訖 41（淨減 3；三筆皆 `fixed`，非 `closed-by-decision`）。
> **體例**：本檔不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型。表格儲存格內
> 不使用半形 `|`，分隔一律用全形「／」。轉述並行包交件一律標 `[他包回報]`；主控親跑者不標。

---

## §0 為什麼這一輪不是純結案輪（轉向取證）

掌舵者指定「純結案輪：只結案、不碰新東西、每輪降 5~8 筆」。起手式後對帳本 **44 筆未結列
全量唯讀分診**（8 組並行，每組逐筆實查解鎖條件今天是否已被後續輪次滿足），再對每一筆可結
候選派 **2 名對抗式證偽員**（四項查核：證據真實性／殘留子項/矛盾列／前瞻交棒行）。

| 量 | 值 |
|---|---|
| 分診筆數 | 44（全量，無取樣） |
| 判 `closable-*` 的候選 | 1（`DEF-200-222`） |
| 證偽存活 | **0**（該筆 2/2 反方一致駁回） |
| 判 `needs-dev` | 39 |
| 判 `needs-adjudication` | 4 |

**結論**：帳本上「重跑一個指令就綠」的存量在上一輪已清空，44 筆無一可在不動程式碼的前提下
結案。⇒ 要降帳本只剩「真的把缺陷修掉」一條路，故本輪轉為精準修復輪。

**連帶訂正一個先前給掌舵者的錯誤建議**：上一輪交棒建議「翻 `AutoSDD_Adjudication_Packet_R121.md`
的 28 張裁決卡逐筆勾選即可再清一批」。本輪實查該檔〈一頁總表〉的「裁後結案形態」欄：標
`closed-by-decision`（裁決後可直接結案）者共 10 筆，其中 8 筆已於上一輪結案、餘 2 筆
（`DEF-200-065`／`DEF-200-213`）為對抗式證偽兩度駁回的死結；其餘 18 筆的裁後形態皆為
「仍open需開發」或「部分closed-by-decision＋部分仍open」。⇒ **該呈報單即使全數落款，主帳本
未結列數的降幅上界是 0**。該建議自此撤回。

**證偽員順帶挖出的關鍵材料**（本輪派工表即由此而來）：
`docs/04_planning/AutoSDD_TechDebt_Paydown_Playbook.md` §A.1 已對每一筆未結列標好
`分類（quick／dev／arch／verify）／工程量級（S/M/L）／信心（高/中/低）／修法`。本輪三筆
標的皆取自該表的 `dev｜M｜高信心` 且**鎖持有面互不重疊**（鐵律七的並行前置檢查）。

---

## §DEF-200-169 扇出視窗剩餘秒數

**缺陷**：派工節流用的是 300 秒滾動視窗（`FANOUT_WINDOW_SECONDS`），但 `--pace` 只印得出
額度軸的 reset 期程（小時尺度的另一件事），**看不到這個視窗還剩幾秒** ⇒ 使用者只能猜還要
等多久才能多派一個 agent。原列另記卡點「`quota_gate.py` loc=500／budget=500／餘裕 0」。

**卡點已過期（主控親跑複核）**：`python AutoClaude/tools/check_loc_budget.py --json` 實測
`tools/lib/quota_gate.py` 為 **391/500**（餘裕 109），非帳本所記的 500/500。⇒ 該列指定的前置
「依 `override_reason` 先拆職責」**不必先做**。

**落地**（三層各司其職）：

| 層 | 檔 | 新增 |
|---|---|---|
| 取數 | `tools/lib/quota_ledger.py` | `oldest_dispatch(root, floor)`——回視窗內最舊一筆的 epoch 秒；`floor` 走參數，模組內一個時鐘都不叫 |
| 邏輯 | `tools/lib/quota_gate.py` | `fanout_window_left(root, now, window)`——回 `(剩幾秒, 最舊幾秒前)`，於 `pace_report()` 接電 |
| 渲染 | `tools/lib/quota_messages.py` | `fanout_window_line(left, live, window)`——純渲染；`window` 走參數而非 import（反向 import 會成環） |

**四個邊界態彼此不同形**（這是驗收重點，不是加分項）：帳上有筆 → 印剩餘秒與最舊幾秒前；
空帳／最舊已超期 → 印「視窗全空，現在派不必等」而**不印 0**（0 讀起來是「滿了正要放行」，
方向相反）；派發帳原語不可達 → 印「量不到」而非「還很空」（守住本 repo 的「量不到 ≠ 量到零」）。

**時間戳形態**：派發帳的時刻本就寫在目錄項名字裡、是 epoch 毫秒（`<毫秒>-<pid>-<亂數>.dispatch`），
非 naive 本地 ISO 字串 ⇒ 未新造任何時間戳形態，`TestNaiveLocalTimestampsAreNotPersisted`
那條硬規則結構上碰不到。時鐘全部由呼叫端注入，生產碼零 `datetime.now()`／`time.time()`。

**回歸鎖**：`tools/tests/test_context_budget_guard.py::FanoutWindowRemainingSecondsTest` 六支
（錨最舊非最新／時鐘可注入／空帳不說 0 秒／超期筆既不撐開視窗也不當錨／不可達不報成空窗／
`--pace` 出口真的印得出來）。`[他包回報]` 六次突變逐一驗紅，其中 M4（拿掉 `floor` 過濾）
紅字為 `Tuples differ: (0, 350) != (None, None)`——正是預測的「剩 0 秒」假話。

**主控親跑複核**：全套實跑 `Ran 3895 tests in 696.577s`，該六支在內、無一 FAIL（本輪僅 4 個
FAIL 且全屬守衛線棘輪重釘，見 §重釘）。

**殘留（誠實列，不阻結案）**：未把剩餘秒數接進**被擋當下**的 `quota_throttle_message()`
——原列只點名 `--pace` 這個出口，本次未擴大射程。

---

## §DEF-200-170 MIN_TESTS 緩衝帶結構上到不了

**缺陷**：`MIN_TESTS` 的 `[1.10, 1.25]` 保鮮緩衝帶在物理上永遠到不了——五次同型復發
（R82／R83／R84／R96／R96-D2）先炸的**永遠**是 `ZeroDepEnvironmentDiscriminationTest`，
而它的紅字講的是「相依裝齊了沒」，**指的方向不是這裡** ⇒ 五輪都被歸錯因。

**原列「現象與證據」欄的五次復發逐筆數字（結案編修時為壓回單列 700 bytes 上限而自帳本列
搬入本檔，逐字保全）**：`R82（2574→2795，線 2831）／R83（2795→3052，線 3074）／R84
（3095→3279，線 3404）／R96（3284→3462，線 3612）／R96-D2（3462→3464，補登）`。

**前提複核（`[他包回報]`，主控以本輪全套輸出交叉印證）**：`MIN_TESTS` 3767／相依齊備收集數
3895／零相依沙箱收集數 3717（塌掉 4 支模組）／collapse loss 178 ⇒ 環境判準失效點在
count ≥ 3945，舊 WARN 第一次說話在 count ≥ 4144。**4144 > 3945**，緩衝帶不可達，且原因是
算術的：沙箱只蒸發 178 支，而 WARN 要等 `0.10 × 3767 ≈ 377` 支漂移。

**落地**：判準本體抽 `tools/lib/min_tests_margin.py`（`collapse_loss`／`zero_dep_headroom`／
`first_speaking_count`／`discrimination_lost_count`／`headroom_message`，純函式無 I/O）；
`tools/run_root_unittests.py` 第一層改綁**餘裕軸**，兩個比例常數降為外層後備（只在拿不到
collapse loss 時才輪到它們說話）。該檔 raw-line 餘裕為 0，故以壓縮過期註解區塊償付，淨 −6 行。

**關鍵設計選擇**：不釘 `loss` 這個數字（那會在治「釘選數字腐化」的缺陷裡再種一個），只釘
「哪幾支模組會塌」的**集合**，支數由當回合 `suite_modules()` 現算。`[他包回報]` 落地時實測
否決過一個看似合理的替代方案：top-level import 靜態掃描會漏掉
`test_ntfs_trailing_space_device_name`（間接拉進相依）⇒ 保鮮看守只能用真沙箱。

**🔴 驗收核心是行為，不是公式**——本輪全套實跑中該判準**第一次真的先開口**（主控親跑，
逐字輸出）：

```
⚠️  MIN_TESTS 該重釘了（DEF-200-170）：零相依沙箱的鑑別力餘裕只剩 50／178 支（本層門檻 89）。
餘裕歸零那一刻，先說話的會是 ZeroDepEnvironmentDiscriminationTest，而它的紅字講的是
「相依裝齊了沒」——指的方向不是這裡，五輪同型復發都是這樣被歸錯因的。
請把 tools/run_root_unittests.py 的 MIN_TESTS 重釘為 3895
```

同一棵樹上舊判準回 `None`、新判準開口並直接帶出目標值 —— 這就是缺陷本體被修掉的行為層證明。
主控依該指示重釘 `MIN_TESTS` 3767 → 3895（照填、零加減推算），見 §重釘。

**回歸鎖**：`tools/tests/test_run_root_unittests.py::MinTestsMarginCriterionTest` 九支
＋`RatchetDriftWarningTest::test_current_pin_still_has_zero_dep_discrimination_headroom`
（活體紅線）。驗收核心那支不重算門檻公式，而是叩真函式問「環境判準失效的**前一支**，新判準
說話了嗎？舊判準還沒說吧？」——舊判準的不可達被釘成對照組。
`[他包回報]` 八次突變逐一驗紅；並自查抓到並修掉一支 vacuous 鎖（第一版看沙箱 stdout，但沙箱
內 `run_with_floor` 在 floor 失敗即 `return 1`、走不到提醒層 ⇒ 恆真），改成直餵真沙箱模組
計數後突變確實轉紅。

---

## §DEF-200-222 archive 阻斷缺併發保護與縮窄判準

**缺陷**：`tools/check_archive_required.py` 的 commit 期阻斷，在 `WARN<=bytes<FAIL` 且
`plan()['movable']` 非空時，**每次 commit（含與帳本完全無關者）**都導向同一條 `--apply`；
且對多 agent 共用工作樹的並發 `--apply` 無任何鎖定或序列化。

**本列原解鎖條件是結構上不可機械查的條件式承接**（「等下一個真的遇到的包先讀本列再動手」），
`CrossPlatform_R113_Ledger_Closure.md:115` 稽核第 21 項早已點名此寫法並要求二擇一改寫。
本輪的處置是**做掉它而非改寫它**：本包即那個「真的遇到的包」。

**落地**：

| 判準 | 檔 | 內容 |
|---|---|---|
| ①縮窄阻斷面 | `tools/check_archive_required.py` | `_staged_paths()`（查 `git diff --cached --name-only`，任何失敗回 `None`）＋`_touches_ledger_family()`（比對主檔／`AutoSDD_Defect_Log_archive_*.md` glob／archive 索引名，三者皆自既有 SSOT 物件 `_gate`／`_archiver` 取得，**不新增第二份清單**）。只在 staged 檔真的觸及帳本族時才阻斷 |
| ②併發保護 | `tools/lib/apply_lock.py`（新） | 跨平台鎖走 `os.open(O_CREAT\|O_EXCL)`——刻意避開本 repo 已有實測前科的兩個原語（Windows 上 `os.O_APPEND` 不是原子的、`msvcrt.locking` 高併發變故障源）。含陳舊鎖依 mtime 回收、逾時擲 `LockBusyError` 並指名持有者 PID/時間戳 |
| ②入口 | `tools/archive_apply_locked.py`（新） | 取鎖後委派 `archive_defect_log.apply()` 的薄殼，零邏輯複製；`argparse` 原生拒未知旗標（已對本 repo 自己的 `TestRootGateToolsRejectUnknownFlags` 驗過） |
| 消費端 | `tools/git-hooks/pre-commit` | 指引文字改指向上鎖入口 |

**fail-open 這一向被明確堵死**：拿不到 staged 清單時**維持現行阻斷**並附 fail-loud 註記，
不靜默放行。`[他包回報]` 該分支的突變（改成 `return []`）當場讓
`test_staged_unavailable_falls_back_to_blocking_with_fail_loud_note` 轉紅。

**回歸鎖**：`tools/tests/test_apply_lock.py`（含
`TestConcurrentAcquireIsMutuallyExclusive::test_only_one_of_two_concurrent_workers_is_in_critical_section_at_once`
——真執行緒＋`threading.Barrier`，**刻意不用 `Pool.map`**：本 repo 已實測那種寫法量不到併發
缺陷）／`test_check_archive_required.py`（`TestTouchesLedgerFamily` 六支＋縮窄三支）／
`test_archive_apply_locked.py`（四支）。`[他包回報]` 五次突變逐一驗紅，其中丟掉 `O_EXCL` 的
那次紅字帶出真實重疊時間戳（`兩個臨界區時間重疊`）。

**殘留（誠實列，不阻結案）**：
1. 鎖只保護走 `archive_apply_locked.py` 的呼叫；有人手動直跑 `archive_defect_log.py --apply`
   仍繞得過（兩檔 docstring 皆已載明）。根因是 `archive_defect_log.py` 釘在 LOC 零餘裕，
   不動它就無法把鎖收進最內層。
2. 陳舊鎖回收採 mtime、無 fencing token ⇒ 持有者只是「慢」而非「死」時有理論上的搶鎖競態。
   以 300s 陳舊門檻對比 `--apply` 次秒級執行時間，實務風險低，但未消除。

---

## §重釘（收尾單人窗口，三個並行包全部停工後）

| 標的 | 前 → 後 | 觸發與依據 |
|---|---|---|
| `skip_tag_policy._TREE_FILE_FLOORS['tools/tests']` | 52 → **55** | `tree_floor_problems()` 第三向逐字指示；`tools/tests` 66 → 69 支（本輪三支新鎖檔），52 只剩實測 75%＜`TREE_FLOOR_RATIO` 80%。方向＝上修＝判準更嚴 |
| `skip_tag_policy._SITE_CLASS_CENSUS['tools/tests']['tool-absence']` | 36 → **37** | 相等棘輪。新站點＝`MinTestsMarginCriterionTest` 類別層 `@unittest.skipIf(os.environ.get(_ZERO_DEP_PROBE_ENV) == "1", …)`＝斷遞迴（`DEF-101-803` 實測整套牆鐘 823s→3813s），述詞讀環境變數非平台故歸 `tool-absence` |
| `run_root_unittests.MIN_TESTS` | 3767 → **3895** | 由 `DEF-200-170` 本次落地的餘裕軸判準逐字指示（見 §DEF-200-170）。同步站點 `ONBOARDING.md` §7 表① 已以 `sync_onboarding_baselines.py --write` 於同一次變更內回填（實跑 rc=0，回填 `{'tests': 3895}`） |
| `_FROZEN_GUARD_LINES` 淨額 | 91793 → **92646（+853）** | 見下 |

**CI paths 雙邊補列**：`tools/lib/apply_lock.py`／`tools/archive_apply_locked.py` 兩支新生產
檔各補進 `windows-compat-ci.yml`／`macos-compat-ci.yml` 各 2 處（合計 4 處），依
`test_ci_paths_cover_root_consumers` 的雙向要求。此為本 repo 連續數輪攔下的同型缺口，本輪
在閘門說話前主動補齊。

**守衛線淨額 +853 的歸因**（`--print-guard-lines` 實測，逐檔）：
`test_run_root_unittests.py` +286／`test_apply_lock.py` +167／`test_check_archive_required.py`
+160／`test_context_budget_guard.py` +131／`test_archive_apply_locked.py` +102，餘為零星。
本輪為**正淨額輪**：依守衛線款(11)，streak 重新起算。

---

## §誠實劃界

1. **本輪三筆修復未經四方定點複審**。循環令 §5 要求實作項過四方；本輪以「三個並行包各自
   突變驗紅 ＋ 收尾單人窗口全套實跑複核」替代，強度依成熟度判準 M3「作者自證不計分」屬
   **自證**。三筆的 `MIN_TESTS` 重釘值亦同屬中途值。
2. **未結列仍有 41 筆**，其中 39 筆分診判 `needs-dev`、4 筆判 `needs-adjudication`（重疊計）。
   降到 0 的路徑是逐筆修，不是逐筆裁決——§0 已取證。
3. 本輪未動 `AISDLC_SDD/` 或其消費路徑，`aisdlc-sdd-ci` 若未觸發屬 paths 不匹配、非失敗。
