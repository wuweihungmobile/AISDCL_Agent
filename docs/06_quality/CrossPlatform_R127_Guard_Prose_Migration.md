# CrossPlatform R127 — 護欄層散文搬遷證據檔

本檔是 R127 守衛線搬遷抵銷包的**逐字保全**落點：`tools/tests/` 三支鎖檔
（`test_context_budget_guard.py`／`test_quota_policy.py`／`test_doc_loc_baseline_freshness_r60.py`）
內的歷史沿革敘事（「當時為什麼這樣改／前值序列／哪一輪誰抓到什麼」）自程式碼搬出，原處只留
一行指標。判準、斷言、常數值、字串字面、豁免 token 一律**未動**。三支 `tools/lib/` 生產護欄檔
本輪只勘查未搬（座標見 `CrossPlatform_R127_Scan_Findings.md` §3）。

體例沿用 R122 的先例（`CrossPlatform_R122_Guard_Prose_Migration.md`）：以 `## <檔名>` /
`### <原本掛在哪個符號上>` 分節，節內以 fenced block 逐字保全原文（含縮排）。

搬遷不改變任何判準的射程；被搬走的文字若日後需要回頭閱讀，循原處指標行找回本節。

🔴 各節「原處：… L<a>-<b>」記的是**搬遷前**的行號（同一次搬遷把後續行號整體上移），
不是搬遷後的座標。要找回原處請以該節標題點名的符號（函式／類別名）定位，不要用行號。

🔴 本輪刻意**未搬**的登記（兩支鎖檔各一）：`test_context_budget_guard.py` 模組 docstring
的「被守的四類性質」段——下方多個測試類別的 docstring 以「性質 1」～「性質 4」引用它，
搬走會讓那些標籤失去同檔內的定義依據；同檔 `test_no_caller_passes_the_reserved_keys_any_more`
的 Pkg-P12 事故敘事——`test_archive_defect_log.py` 與 `test_claim_provenance_r86.py` 各有一份
同源引述，三處收斂屬另案，本輪不單搬一處製造漂移。`test_quota_policy.py`
`TestR98ModelScopedAxisDoesNotBindWithoutDispatch` 的 R98 事故段與 `tools/lib/quota_policy.py`
生產碼註解同源，同理未搬。

## test_context_budget_guard.py

### 模組 docstring：為何新增一支檔案而不是併進既有鎖檔（照實寫）

原處：`tools/tests/test_context_budget_guard.py` L22-28（7 行，模組 docstring 第二段）

```text
🔴 為何新增一支檔案而不是併進既有鎖檔（照實寫）
------------------------------------------------
`tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_GUARD_LINES` 是逐檔行數棘輪，
**任何**淨行數上升都會紅（不論新檔或擴充既有檔），合法出口只有「同一次變更刪等量的
行」或「重釘基準並在交件回報寫出淨額」。本包不刪別人的行，故走後者；而該棘輪自己
的紀律是「重釘一律由收尾包在所有包停工後做一次」⇒ **重釘不在本包射程內**，交由收尾者。
本檔因此可能讓該棘輪暫時紅，這是已知且已回報的狀態，不是漏看。
```

### _isolated_env：APPDATA／LOCALAPPDATA 為何要一起隔離（R96／B-5）

原處：`tools/tests/test_context_budget_guard.py` L202-208（7 行，dict 字面內的註解區塊）

```text
        # 🔴 R96／B-5：`DEF-200-153` 的根因自陳是「第三方在家目錄下的副作用」，而此前被
        # 隔離的只有 `USERPROFILE`／`HOME` 那一條路——`APPDATA`／`LOCALAPPDATA` 一律**原封
        # 繼承開發者的真家目錄**（實測：子行程看到的 APPDATA 逐字是
        # `C:\Users\<人>\AppData\Roaming`）。任何走 `%APPDATA%` 的第三方（PowerShell 模組
        # 快取、.NET、pip）因此仍會寫進**真的**那一棵樹：既污染開發者機器，又完全落在
        # 任何斷言的射程之外（沙箱目錄裡看不到 ⇒ 「沒有副作用」是假的）。
        # 一個家、兩個呼叫端（`_run_hook3` 與 `PlannerCliTest._run`）自動受益。
```

### test_the_principal_is_s4u_first_with_a_non_elevated_fallback：S4U 優先＋回退的立案

原處：`tools/tests/test_context_budget_guard.py` L1669-1674（6 行，docstring 全文）

```text
        """與 `tools/install_windows_nightly.ps1` 的兩支既有工作對齊（該檔 R69 S-5 段）：
        Interactive 的工作在使用者未登入時整輪不跑，且視窗開在使用者桌面上。

        兩個方向都要鎖：① S4U 必須是**先試的**那一支（回退分支才有意義，否則等於沒改）；
        ② 回退分支必須存在（非提權下 S4U 會被拒，只掛 S4U 會讓哨兵整條武裝斷掉——
        那是把一個干擾缺陷換成一個功能缺陷，不是修好）。"""
```

### test_the_audit_timestamp_cannot_be_overwritten_by_a_caller：R79 補洞包實測抓到的真缺陷

原處：`tools/tests/test_context_budget_guard.py` L1974-1980（7 行，docstring 全文）

```text
        """🔴 R79 補洞包端到端實測抓到的真缺陷（既有 `_resume_tick` 也中招）。

        `append_log(..., at=decision["at"])` 那個 kwarg 直接覆寫了記錄自己的時間戳
        ⇒ 痕跡上寫著一個**未來**的時刻（實測：事件發生在 21:24、記錄寫成 23:26）。
        「這件事何時發生」正是整條稽核痕跡唯一在回答的問題——讓「觸發了但失敗」與
        「根本沒觸發」分得開的那一格。把 `at`／`event` 移回 `**fields` 之前即紅。
        """
```

### SpendLimitReachesAHumanTest._tick：R115 注入確定性假後端的理由

原處：`tools/tests/test_context_budget_guard.py` L4737-4745（9 行，註解區塊）

```text
        # 🔴 R115 修復（同 DEF-200-239／`SentinelDecisionTest._tick` 既有藥方） round-label-ok
        # 本類別的 `task_name` 是固定字面 "T_R81"，永遠不符合任何真後端的 `AutoSDD_Sentinel_`
        # 前綴查詢 ⇒ `patrol_housekeeping()` → `_heal_armed_drift()` 摸到未注入的
        # `schedule_backend.select()` 時，真後端會結構上判定「這支工作不在」並嘗試真的
        # `.arm()`——posix 上真後端無條件失敗（`NoCarrierBackend`／CI 沙箱裡的
        # `LaunchdBackend`），觸發本輪新增的 rc≠0 loud alert 分支，於是普通的排程／靜默
        # 下班 tick 也被誤判成「漂移重掛失敗」而騷擾人（雲端 posix 首跑才紅，Windows
        # 本機因真後端行為不同而看不見）。與 `SentinelDecisionTest._tick` 同一帖藥：
        # 注入一支確定性假後端，讓漂移健檢摸到的是可控的假象，不是真排程器。
```

### test_a_dead_endpoint_with_no_evidence_falls_back_to_the_degraded_cap：R82 裁決 D-8 的三層拆解

原處：`tools/tests/test_context_budget_guard.py` L6484-6491（8 行，docstring 全文）

```text
        """🔴 R82 具名改寫（裁決 D-8，駁回本條 R81 版的斷言；R81 版斷言原文與複審探針
        數字＝Resume 證據檔 §L-3.16）。裁決把那個矛盾拆成三層，各自的失效方向不同：
          · 守衛**行程**：永遠不得崩、不得誤 deny ⇒ fail-open（**這一層一行都沒動**）；
          · **節流決策**：不得靜默全放行 ⇒ 量不到時 `cap = degraded_cap`；
          · **halt 決策**：絕不對沒量到的值開火 ⇒ 量不到時**永不** halt。
        改判之後 cap 之內仍然全放行（所以「網路壞了 ≠ 停機」還在），
        超出 cap 才擋——而且它**永遠不會變成 0**（`decide` 保證 `>=1`，禁止靜默鎖死）。
        """
```

### QuotaDegradationIsAudibleTest.setUp：為何要另 swap endurance_env.trace_dir

原處：`tools/tests/test_context_budget_guard.py` L7141-7148（8 行，註解區塊）

```text
        # 🔴 活體隔離：availability／stability 兩台狀態機的持久檔（含 `.lock`）住
        # `endurance_env.trace_dir()`（帳號級，如 `~/.autosdd/traces`），**不經** qg 的
        # 路徑函式 ⇒ 上面六個 swap 蓋不到。不 swap 這兩個，本類讀寫的是開發機的真實
        # 狀態：真 hook（或本類 throttle 測試自己）把 stability cap 釘 0 之後，unmeasured
        # 封鎖放寬方向 ⇒ `live(1) > cap(0)` ⇒ rc=2——同一棵樹的紅綠隨活體檔內容翻動
        # （實測三次量測互相矛盾的根因）。swap 對象是 `endurance_env`（兩台狀態機都在
        # 呼叫時做屬性查找），一次蓋住 state／lock 兩面；`degraded=False` 讓「持久目錄
        # 退化」那條收緊側旁路（它會無條件回 unmeasured）也不受本機姿態影響。
```

### EnvFileReachesEveryEscapeHatchTest._FLAGS：手寫清單的沿革（R91／R97）

原處：`tools/tests/test_context_budget_guard.py` L8406-8412（7 行，註解區塊）

```text
    # 🔴 R91 加入第五個逃生口 `AUTOSDD_CONTEXT_SIGNAL_OFF`（送達形態）。本清單是**手寫**
    # 的：新增一個逃生口卻忘了補這一列時，本組不會紅（它只走自己列的那幾個）——所以真正
    # 守「宣告過的逃生口都要在 `ENV_SPEC` 裡」的是
    # `EveryHookEscapeHatchIsDeclaredTest`（R91 新增，分母現查 `.claude/hooks/*.py`）。
    # 🔴 R97：`AUTOSDD_RESUME_OFF` 的讀取點不住這支 hook（住 round-label-ok
    # `tools/session_resume_planner.py`），但 `qg.apply_env_defaults` 是它們共用的同一份
    # 前置填充機制——併進這張清單一併驗證泛用性，不必為它另開一組測試。
```

## test_quota_policy.py

### TestM6TheGeneratedFileSurvivesItsOwnConsumer：R82／C1 round-trip 的病與複審鏡實測

原處：`tools/tests/test_quota_policy.py` L1122-1124（3 行，區段旗標下的註解）

```text
#
# 病：判準拿生成物跟自己比、從不呼叫消費者的解析器 ⇒ 兩個家互相一致、都沒對消費者測。
# 複審鏡實測（12 個帶值鍵全部解析失敗、照抄範例檔會關掉整條節流）原文＝R95 Pace 證據檔 §7.5。
```

### TestAmortizationNamesTheAxisItActuallyUsed：explain() 具名軸的立案

原處：`tools/tests/test_quota_policy.py` L2430-2434（5 行，區段旗標內的註解）

```text
# 攤提（`quota_pace.amortize`）與 binding（`_in_cap_gate`，R98）對 `MODEL_SCOPED_KINDS`
# 的處置**刻意不同**，而 `explain()` 的字面把兩件事混成一句假話：實測 `--pace` 逐字
# 「攤提：kind=weekly_all 剩 39pp」，而 weekly_all 當時 52%（剩 48pp）——39pp 來自
# weekly_scoped(61%，Fable，binding 側已排除)。兩條鎖：① 具名必須是真的被用到的那一軸；
# ② 納入的方向必須是**保守側**（只會更緊）＝不排除它的實質判詞，見 `amortize()` 上方。
```

### _USAGE_URL_HALVES：DEF-200-230 額度取數端點「單一家」的立案敘事

原處：`tools/tests/test_quota_policy.py` L3122-3127（6 行，常數上方的註解）

```text
#
# 立案（帳本 DEF-200-230 逐字）：紅線 1 要求額度取數只有一個站點，而在本鎖之前那件事
# **只是散文**——任何人在別處再貼一份 `USAGE_URL` 就多一個取數端點，而兩份字面一旦漂移
# （版本路徑不同、少一段 `/api`），失效方向是「本機恆綠、真的量到的是兩個不同的數」。
# 現況不變式（落地當回合實測）：全庫 tracked `*.py` 中帶完整端點 URL 字面者恰 1 支＝
# `tools/lib/quota_meter.py`。
```

## test_doc_loc_baseline_freshness_r60.py

### 模組 docstring：WHY（為何非得有這道鎖）與 R60 round 2 改形三件事

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L5-25（21 行，模組 docstring）

```text
WHY（為何非得有這道鎖）：
  「文件裡寫死機器可以現場算出來的數字」在本 repo 已是**慣犯家族**——
    - DEF-101-289：ONBOARDING §7 基線落後實測（P3）；
    - DEF-101-515：§7 整張表只有 macOS 單邊、容差宣稱主動誤導（P2）；
    - R60 Scan-D D-01：§7 Windows 基線表的 LOC 那格寫 `total=20356`，實測 `20359`
      ——而且在 **R59 自己的收尾 commit 樹上就已經 stale**；
    - R60 ARCH-R60-03／SA-R60-01：**本鎖的第一版只鎖一格**，同一張表另外四格全部
      stale（3740→3756、661→756、1725→1736、248→249），其中根層那格更與同 repo 的
      `tools/run_root_unittests.MIN_TESTS`（已重釘 756）直接矛盾。「為一格加鎖」反而
      讓另外四格更容易被誤讀成「有鎖所以可信」。
  歷輪的處置全是「人工回填一次」，所以家族每隔幾輪就原地復發。

本輪（R60 round 2）改形三件事：
  1. **改為錨點表驅動**：判定邏輯與「有幾格受鎖」解耦，收在
     `tools/sync_onboarding_baselines.py::_SPECS`。表格新增一格 ≠ 新增一支鎖
     （ARCH-R60-09(d) 的方向），只需在該處加一筆錨點。
  2. **新增第二格**：根層 `run_root_unittests` 測試數，取值來源＝該檔的 `MIN_TESTS`
     （現成 SSOT，import 後比對，成本近零）。
  3. **補上產生器那半邊**（SD-R60-09）：`sync_onboarding_baselines.py --write` 一鍵
     回填，`--check` 供本鎖與人工消費，兩者共用同一份取值邏輯 ⇒ 不可能一邊算 A、
     另一邊算 B。形狀對齊 repo 既有慣例（`snapshot_sync.py` + CI `--check`）。
```

### 模組 docstring：檔名說明

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L47-50（4 行，模組 docstring）

```text
檔名說明：本檔名沿用 R60 落地時的 `..._loc_baseline_...`，內容已泛化為整張表①。
  刻意不改名——改名會動到 ONBOARDING §7 內對本檔的具名引用與其他包的並行變更面，
  屬無淨收益的擾動（Rule 3）。要判斷本鎖實際守了哪幾格，看
  `sync_onboarding_baselines._SPECS`，不要看檔名。
```

### R69：ADR 內量測 token ↔ 現查——為何非得有這一條

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L1999-2009（11 行，區段旗標下的註解）

```text
# 🔴 為何非得有這一條（R69 Architect 實測命中，同型第三次復發）：
#   R68 把「閘門全綠」寫進 commit message，事後複現不出來；R69 的 `ADR-XPLAT-003` 把同一個
#   毛病**搬進了 ADR**——該 ADR 表頭自陳「記錄的是已合入工作樹並實測綠的異動」、§3 又逐字
#   引述 `ADR-XPLAT-002` §1.1「以行數下降為成果的宣稱必須前後各量一次」並宣稱「本節照辦」，
#   而它寫下的 `total=20415`／`3923 passed` 在交付樹上一個都複現不出來（實測 20436／3929）。
#   受害者不是潔癖：ADR 是**寫給未來每一輪照抄重跑**的文件，數字錯了，照它驗證的人會把
#   正常狀態讀成退化，或反過來把凍結讀成已解除（本例正是後者：「餘裕 23 行」讓讀者以為
#   生產碼可以再寫，實際餘裕 2 行、凍結完全沒解除）。
#   同族前科：DEF-101-289／DEF-101-515（ONBOARDING §7）、`ADR-XPLAT-002` §4.3.1 的成長率
#   常數（R67 round 4 拔除）、`run_root_unittests.MIN_TESTS` 一輪三釘。**共同形態＝
#   「文件寫死機器當場可以算出來的數字」**，故本鎖與本檔正職同源、同檔、共用取值來源。
```

### _REAL_WIN_NIGHTLY_TAIL：provenance 訂正（七行曾只放六行）

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L2403-2410（8 行，常數上方的 `#:` 註解）

```text
#:
#: 🔴 provenance 訂正（本批）：上一批的同一句註解宣稱「488~494 行」，實際**靜默丟掉了第
#: 493 行**（`END observation progress: …`）——七行只放了六行。這種「宣稱逐字、其實刪過」
#: 正是本檔整章在治的病（宣稱與資料不符），且丟掉的偏偏是**唯一帶 `unique-sha` 觀察期進度
#: 的那行**：它與 win32 strict 樣式擦身而過（`END observation …` 不是 `END nightly
#: summary:`），若當初就在樣本裡，反而能多證一件事——strict 不會誤吃同前綴的鄰行。現已補回。
#: 該檔 untracked（`AutoClaude/.gitignore: logs/`）故本測試不能讀它比對；落地當下以
#: `python -c "...read().splitlines()[487:494]"` 逐行核對過，輸出貼在本批回報中。
```

### 鐵律三「無機械物」清單：R79／R80／R85 三筆移出的沿革

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L2666-2690（25 行，tuple 定義內的註解）

```text
    # 🔴 R85：`shell=True` 的原生殼差異**已補上機械物**，故自本清單移出 ⇒ 分子 +1
    # （合法路徑：補了掃描器就改該列的機械物欄，不是把整列拿掉——拿掉會讓分母降而轉紅）。
    # 機械物＝`AutoClaude/tests/execution/test_shell_portability_contract_r85.py`
    # （執行期診斷 `portability_note()` ＋ 兩個執行面的射程普查 ＋ 以真實 playbook 為母體
    # 的假紅普查）。同時訂正 R80 登記時寫下的兩句話：①「存量掃描**結構上**量不到它」
    # 過寬——指令內容確實不在 repo 裡，但**入口只有 2 個、可列舉**，且 `evaluator_command`
    # 的真實母體就在 repo 裡（實測 9 支 playbook／19 值）；真正不在 repo 裡的只有
    # `condition_evaluator`（全庫 YAML 內 0 次，唯一產生者是 LLM 突變 schema），已由該段
    # prompt 的正規化涵蓋。②與 `test_evaluator_kill_tree.py` 的「同關鍵字不同主題」判讀
    # 仍然成立，故那筆留在證偽探針的「已審視並判定不算」清單裡——**不是**因為它被推翻，
    # 而是那張清單隨本列一起移除（見 `_IRON_LAW3_UNCOVERED_EVIDENCE` 的 stale 判準）。
    # 🔴 R79：`.ps1` 方向的行尾**已補上機械物**（PostToolUse hook 寫入當下補回 CRLF ＋
    # 根層 unittest 事後量工作樹），故從本清單移出、該列的機械物欄同步改寫 ⇒ 分子 +1。
    # 這是本表雙單邊棘輪設計裡唯一合法的「分子上升」路徑：補了掃描器就改機械物欄，
    # 不是把整列拿掉（拿掉會讓分母降而轉紅）。
    #
    # 🔴 R80（包 B）：`行尾（**`.py` 方向**` 也自本清單移出——但它與上面三項的成因不同，
    # 值得分開記：R79 把它登記成「新發現的無守門危害類」，而**那句話本身就不真**。
    # 守門的類別（`TestWorktreeEolMatchesPolicy`）一直都在，只是被 `_EOL_LF_SCOPE` 窄化成
    # 只看 `.sh`／`.bash`，而且該類還有一條 `assertNotIn(".py", policy)` 把「`.py` 必須被
    # 放行」釘成契約 ⇒ **有鎖在守假話**：檔案在、判準在、測試全綠，只有讀完那個常數才知道
    # `.py` 從來不在射程裡。本輪以獨立射程承接（`TestActiveSourceEolIsRatchetedSeparately…`：
    # 活躍面止血、凍結面只登記），分子 +1。
    # 同時訂正它的量：R79 記的 4,176 只是 `.py` 這一塊，全庫工作樹行尾與宣告不符者當回合
    # 實測 18,255 支、其中約 95% 落在 Copy-on-Evolve 凍結面 ⇒「全部就地轉 LF」不是修法。
```

### _IRON_LAW3_COVERED_FLOOR：R81／R84／R85 逐格沿革

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L2707-2728（22 行，常數上方的 `#:` 註解）

```text
#: R81（包 G）：12 → 17。分子 +5＝git 路徑列舉的非 ASCII 引號化、BSD/GNU coreutils
#: （`.sh` 那面本來就有掃描器，本輪補上 workflow inline `run:` 這第二個掃描面）、
#: 單平台專屬 API 詞彙表（表驅動＋後設鎖）、排序鍵影響雜湊、文字模式檔案 I/O 編碼
#: （最後一項是**訂正低報分子**：判準與逐檔棘輪早就在，R81 掃描路把它讀成「無人守」）。
#: 實際分子為 18，仍照既有慣例留一格給並行包。
#: 🔴 R84（W8／SD-08）：17 → **18**（＝當輪現值，緩衝歸零）。理由是實測的：
#: `iron_law3_coverage()` 回 `(18, 20)` 而兩個 floor 是 `(17, 19)` ⇒ CLAUDE.md 該段逐字
#: 承諾的「拆掉一支掃描器 ⇒ 分子降 ⇒ 紅」「刪掉一列已知危害 ⇒ 分母降 ⇒ 紅」**今天各有
#: 一次免費額度**（18→17、20→19 皆靜默通過），而單向性正是這條棘輪唯一的存在理由。
#: 落後的成因是結構性的、會反覆發生：補了掃描器的人只改表，沒有任何東西提醒他調 floor
#: ⇒ 同輪一併補上「floor 自己過期」的上界判準（`_IRON_LAW3_FLOOR_STALE_SLACK`），
#: 讓下一次忘記調 floor 當場轉紅，而不是又留一格給下一輪。
#: 🔴 R84（C2 收斂）：18 → **19**（＝重釘為當輪現值）。分子 +1＝新登記的「hook 行程生出來
#: 的子行程配到 console 視窗」那一列**連同兩支掃描器一起落地** ⇒ 分子與分母同步各 +1。
#: 🔴 R85 收尾單人窗口：19 → **21**（＝當輪現值，`_IRON_LAW3_FLOOR_STALE_SLACK` 逐字指示）。
#: 分子 +2，兩筆成因不同，刻意分開記：
#:   ① `shell=True` 原生殼差異——R80 誠實登記為無人守（分母 +1 分子不動），**R85 補上機械物**
#:      （`AutoClaude/tests/execution/test_shell_portability_contract_r85.py`）
#:      ⇒ 分子 +1 而分母不動。
#:      這是本表雙單邊棘輪唯一合法的「只有分子上升」路徑。
#:   ② 新登記的危害類「單平台專屬**外部執行檔的 argv[0] 字面**」**連同掃描器一起落地**
#:      ⇒ 分子分母同步 +1（同 R84 console 視窗那一列的形狀）。
```

### _IRON_LAW3_KNOWN_FLOOR：R79～R85 逐格沿革

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L2732-2743（12 行，常數上方的 `#:` 註解）

```text
#: R79：8 → 12（`.py` 行尾、exec bit、目錄項原語三類新登記；`.ps1` 行尾那一列原本就在表上）。
#: R80（包 B）：12 → 14。分母 +3＝shebang×行尾、naive 本地時間戳被持久化、
#: `shell=True` 原生殼差異（三類此前一格判準都沒有，前兩類本輪連同掃描器一起落地、
#: 第三類誠實登記為無人守）。同上，釘到比現值低一格以容忍並行包同時擴表。
#: R81（包 G）：14 → 19。分母 +5＝與上面同五列（五類此前一格都不在這張表上，
#: 其中四類本輪連同掃描器一起落地、一類是訂正低報）。實際分母為 20，同樣留一格。
#: 🔴 R84（W8／SD-08）：19 → **20**（＝當輪現值）。理由同上一個常數，不重複。
#: 🔴 R84（C2 收斂）：20 → **21**。分母 +1＝上一個常數註解裡那一列（新危害類「hook 子行程
#: 配到 console 視窗」），該列本輪連同掃描器一起落地，故分子分母同升。
#: 🔴 R85 收尾單人窗口：21 → **22**。分母 +1＝新危害類「單平台專屬外部執行檔的 argv[0]
#: 字面」（見上一個常數的 ② 條）。**注意分子本輪 +2 而分母只 +1**——差額來自 `shell=True`
#: 那一列由「已登記但無人守」轉為「已登記且有人守」，那一列早在 R80 就進了分母。
```

### _IRON_LAW3_FLOOR_STALE_SLACK：缺陷本體與 R84 實測

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L2747-2752（6 行，常數上方的 `#:` 註解）

```text
#:
#: 缺陷本體與 `SPECIAL_STALE_SLACK`／`_GUARD_LINE_STALE_SLACK` 逐字同型：單邊棘輪只會腐化
#: ——現值往上跑而 floor 留在原地時，那段落差就是**預先發放的成長額度**，日後可以無聲地
#: 用回去，而 CLAUDE.md 對外承諾的單向性在那段區間內是假的。R84 實測：落差各 1 格，
#: 於是「拆掉一支掃描器就紅」需要拆**兩支**才會紅。
#:
```

### hook 宣稱第三向（已註冊但文件沒提）：立案實測

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L2993-3001（9 行，docstring 說明段）

```text
    🔴 **這是 `hook_claim_problems()` 的第三向（R79 收斂包）**。前兩向的掃描面都是
    `hook_scripts_named_in(CLAUDE.md, …)`——**只檢查文件裡有被點名的那幾支**。於是
    「已註冊、但文件從頭到尾沒提」這個組合結構上落在兩向之外：兩向都不會觸及它。

    代價已實測：`lint_powershell_command.py` 自 R77 上線起就在根層攔 PowerShell 指令
    （鐵律二與「讀 rc 不接管線」的唯一機械物），而 R79 掃描時根 CLAUDE.md 全檔提到
    hook 的地方只有鐵律一那一處 ⇒ 那兩節讀起來都像純自律。方向與慣見的相反但同樣是
    假圖像：不是「宣稱一個不存在的機械物」，是**有機械物卻被記成沒有**，而下一輪很
    可能為它們再蓋一支攔截器（同一份知識住兩個家，R73 `Find-GitBash` 的復發形態）。
```

### R75 訂正：具名機械物鎖三面擴張的缺陷本體（四縫、逃逸四筆）

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L3072-3085（14 行，區段旗標下的註解）

```text
# 🔴 缺陷本體：原判準是「掃根 CLAUDE.md、要求反引號、副檔名只認 `.py`、只斷言檔案存在」。
# 四個縫各自漏了東西，實測逃逸 4 筆（Architect／SA 實查，本輪以探針全部重現）：
#   ① 掃描面只有根 CLAUDE.md ⇒ `tools/*.py` 註解與 `tools/*.json` 的 `_why` 裡指認機械物
#      的宣稱完全不在視野內。逃逸：`archive_defect_log.py` 與 `check_defect_log_crossref.py`
#      各指向一支從未存在的 `test_defect_log_capacity_policy_r68.py`（R68 落地時
#      `tools/tests` 鎖檔數棘輪擋下新增鎖檔，判準併進了 `test_archive_defect_log.py`，
#      指標卻留在原本打算開的檔名上）；`scheduled_task_expectations.json` 同型。
#   ② 副檔名只認 `.py` ⇒ 根 CLAUDE.md 對 `install_windows_nightly.ps1` 寫了 `AutoClaude/`
#      前綴（該安裝器住 monorepo 根層 `tools/`），三個解析基準都找不到，卻因為是 `.ps1`
#      而不被檢查。
#   ③ 只斷言「檔案存在」⇒ **「檔案在、但守的是別的東西」照樣通過**。鐵律三 `行尾` 列
#      具名 `test_ps1_bom.py`，而該檔全篇是 .ps1 的 UTF-8 BOM 政策，對 CRLF／行尾零判準。
#      這一種比指向不存在的檔更難看見：路徑點得開、檔案打得開，只有讀完才知道守錯東西。
#   ④ `::Symbol` 從不驗證 ⇒ 類別改名／搬家後指標靜默失效。
```

### _SYMBOL_REF_GLOBS：R79 擴面（第二條逃逸縫）

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L3658-3665（8 行，常數上方的 `#:` 註解）

```text
#:
#: 🔴 **R79 收斂包擴面（第二條逃逸縫）**：R78 把判準的**token 形狀**由「反引號路徑」擴到
#: 「反引號 Python 識別字」，但引用面自始至終只有 `.py`。實測後果：引發整個 R78 C 包的
#: 那個常數（護欄層檔數棘輪，全庫零定義）當時仍活在 10 支 `docs/` 檔共 14 處，其中
#: `Skipped_Test_Inventory_R76.md` 把它當**現行**約束在陳述，而那個語意早已被推翻
#: ——照著讀的人會把新鎖放到別的樹去（R79 實測這件事已經發生）。
#: 「形狀對了、但那個形狀出現的地方不在掃描面內」＝同一個病的第二個住所。
#:
```

### _SYMBOL_DEF_GLOBS：R79 補三棵樹

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L3679-3687（9 行，常數上方的 `#:` 註解）

```text
#:
#: 🔴 **R79 收斂包補三棵樹**（每一棵都是當回合實測抓到的偽陽性來源，不是預防性擴面）：
#:   · `.claude/hooks/*.py`——**整個 hook 層的符號在本索引裡等於不存在**。實證：R79 的
#:     觀測者包在鎖檔裡以反引號指名 `_RC_RESET_RE`（真的定義在
#:     `.claude/hooks/lint_powershell_command.py`），主牙把它判成幽靈符號並讓根層閘門轉紅。
#:     偽陽性比漏報更致命——它會逼下一個人把整道鎖關掉（本檔上方已為此付過學費）。
#:   · `AutoClaude/tests/**/*.py`／`AISDLC_SDD/scripts/**/*.py`——skip 盤點與 ADR 大量以
#:     **模組名**指認測試（`test_pgvector_recall_perf` 這種），那些模組真的存在、只是住在
#:     這兩棵沒被收進來的樹裡。擴面後 20 個此類名字一次消失。
```

### _GHOST_SYMBOL_BASELINE：為何不是「一上線就全紅」＋R79「刪四加五」

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L3699-3702 與 L3709-3717（4＋9 行，常數上方的 `#:` 註解）

```text
#: 為何不是「一上線就全紅」：本判準落地當回合實測，`tools/**` 既有的幽靈符號有數十個
#: 名字、散在六十餘處，全部來自歷輪的重構與改名。鎖若一上線就對它們全紅，下一個人會直接
#: 把鎖關掉／加 `@skip`——那樣連「硬擋新幽靈」這個真正的價值也一起賠掉（R60 為同一個取捨
#: 寫過同一段話）。
```

```text
#: 🔴 **R79 收斂包同一次變更的兩個方向**（兩個方向都必須做，只做一半會是假帳）：
#:   · **刪 4 筆**（`_ADDITIONAL_RISKY_NAMES`／`_PG_REAL_ENABLED`／`_SDD_PRESENT`／
#:     `test_enforce_docs_path_blocks_chinese_path_under_cp950`）——定義面擴到三棵新樹之後
#:     它們**解析得到了**，(b) 那道 stale 自檢會直接判紅要求刪除。
#:   · **加 5 筆**（下方標 `R79-docs` 者）——引用面擴到 `docs/` 活文件之後才**第一次看得見**
#:     的存量。這不是「問題變多」而是「視野變大」，同 `_IRON_LAW3_KNOWN_FLOOR` 那條雙單邊
#:     棘輪的立案理由；為了不讓這個藉口被重複使用，加筆的代價由下方
#:     `_GHOST_SYMBOL_BASELINE_CEILING` 這道 shrink-only 天花板承擔（形狀抄
#:     `test_subprocess_encoding_hygiene._ENTRY_WAIVER_CEILING`）。
```

### _GHOST_SYMBOL_BASELINE_CEILING：33→29 逐格收緊沿革

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L3756-3767（12 行，常數上方的 `#:` 註解）

```text
#: 🔴 R85 P2：33→32（**收緊**）。TREE_FLOOR_RATIO 那一筆已無引用（本輪把 schedule
#: parity 的下限第二個家改成直取 SSOT）⇒ 依 stale 向的指示刪除，天花板同步降到現值。
#: 🔴 R89 收尾：32→31（**收緊**）。`test_main_separates_vague_rows_from_valid_count_and_
#: does_not_fail` 那一筆的唯一引用是一段史料敘述，該段本輪已遷入 R89 收尾證據檔 ⇒ 全引用
#: 面歸零、幽靈清乾淨，依 stale 向的指示刪除，天花板同步降到現值。
#: 🔴 R95 收尾：31→30（收緊，體例同上）——DescendantWatcher 樣本類的唯一引用已隨史料搬遷離開掃描面。
#: 🔴 R115 收斂棒 round-label-ok：30→29（收緊，體例同上）——上一筆已刪除那個舊測試類名字的唯一引用
#: （`test_dev_start.py` 內某類 docstring 的一句歷史敘述）本輪隨類級 docstring 沿革
#: 搬遷（見 CrossPlatform_Guard_Line_History.md〈R115 round-label-ok dev_start
#: TestAcquireBootstrapLockPartialAliveMiddleState WHY〉節）離開掃描面，全引用面歸零、
#: 幽靈清乾淨，依 stale 向的指示刪除，天花板同步降到現值（本行刻意不覆述那個名字本身
#: ——反引號包住它會讓本檔自己的幽靈符號掃描器把這句 WHY 誤判成新的一筆待清幽靈）。
```

### is_machine_local_artifact：第三態的立案（R82／P4）與兩種錯誤修法

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L4304-4319（16 行，docstring 說明段）

```text
    🔴 這是幽靈路徑判準的**第三態**，不是豁免，兩者的差別是本函式存在的全部理由。
    立案（R82／P4，mac 側實測 3 支紅）：
      · `AutoClaude/.g0_readiness.json` 是每晚重生的量測檔且已 gitignore ⇒ 在跑過
        nightly 的那台 Windows 上**檔在**、在剛 clone 的 mac 上**檔不在**。
      · `AISDLC_SDD/.claude/settings.local.json` 是 Claude Code 的機器本地設定 ⇒ 方向
        **恰好相反**（Windows 沒有、mac 有），於是它被登記進豁免表之後，在 mac 上被
        `stale_path_baseline_problems()` 判成「已解析得到，請刪除登記」。
    兩筆是同一個病的兩個方向：**判準的分母含機器本地狀態**。舊判準只問「這台機器的檔案
    系統上現在有沒有這個檔」，所以同一棵樹在兩個平台上一個綠一個紅——而「幽靈與否」本該
    是 repo 的性質，不是這台機器跑過什麼的性質。

    正解是換掉量測面而不是換掉常數：問 **repo 自己**（`.gitignore` 是 tracked 內容，每台
    機器逐字相同）「這條路徑是不是生成物」。答 True 的既不是幽靈也不是實體——它是**第三態**：
    指向它的文件沒有寫錯（讀者在產出它的機器上真的找得到），但這棵樹不保證有它。
    ⇒ 逐筆加豁免是錯的修法（同一筆登記在 A 機器必要、在 B 機器 stale，兩邊都紅）；
    ⇒ 改成「mac 上量到的值」更錯（那只是把紅從 mac 搬去 Windows）。
```

### _GIT_CHECK_IGNORE_UNAVAILABLE：為何 fail-loud（證據 vs 判準輸入）

原處：`tools/tests/test_doc_loc_baseline_freshness_r60.py` L4143-4149（7 行，常數上方的 `#:` 註解）

```text
#: git 取數失敗時的紅燈訊息。🔴 **為何這一條 fail-loud，而同檔的 `_git()` 對「git 不在」
#: 是回 None**——兩種政策不衝突，因為 git 在兩處扮演的角色根本不同：
#:   · `_git()` 拿 git 當**證據**（這個 sha 是不是真 commit）。驗不動時「未驗證」不等於
#:     「宣稱為假」，硬判紅就是 `DEF-101-756` 那個誤讀（本機沒有心跳檔 ≠ 該平台沒跑）。
#:   · 這裡的 git 是**判準本身的輸入**。沒有它就沒有第三態，而少了第三態的判準會靜默
#:     退回舊行為——也就是「Windows 綠、mac 紅」那個本節正在治的缺陷本體。降級無聲、
#:     失效方向又是假綠假紅各半（生成物在的機器假綠、不在的機器假紅）⇒ 只能出聲。
```
