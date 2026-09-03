# CrossPlatform R122 — 護欄層散文搬遷證據檔

本檔是 R122 守衛線搬遷抵銷包的**逐字保全**落點：`tools/tests/` 各鎖檔內的
歷史沿革敘事（「當時為什麼這樣改／前值序列／哪一輪誰抓到什麼」）自測試碼搬出，
原處只留一行指標。判準、斷言、常數值、字串字面、豁免 token 一律**未動**。

體例沿用 R104 的先例（`_platform_helpers.py` 三段 forensic 沿革搬至
`CrossPlatform_R104_Scan_Findings.md`）：以 `## <檔名>` / `### <原本掛在哪個符號上>`
分節，節內以 fenced block 逐字保全原文（含縮排）。

搬遷不改變任何判準的射程；被搬走的文字若日後需要回頭閱讀，循原處指標行找回本節。

🔴 各節「原處：… L<a>-<b>」記的是**搬遷前**的行號（同一次搬遷把後續行號整體上移），
不是搬遷後的座標。要找回原處請以該節標題點名的符號（函式／類別名）定位，不要用行號。

🔴 一筆刻意**未搬**的登記：`test_install_windows_nightly.py::
test_smoke_task_is_registered_alongside_nightly` 的 WHY 段留在原處。它逐字含
`test_windows_smoke_heartbeat_doc_sync._STALE_CLAIMS` 的宣稱字樣，而那道鎖要求「凡出現
該字樣的檔都必須登記在 `_CLAIM_SCAN_FILES`」；搬走會同時①讓原檔的登記變成過期登記、
②讓本檔成為未登記的宣稱檔（實測兩支測試各紅一次）。⇒ 依「有人在讀它就別搬」原則退回。

## test_archive_defect_log.py

### wholefile_text_notin_sites 認的形狀與誠實劃界

原處：`tools/tests/test_archive_defect_log.py` L182-198（17 行，docstring 說明段）

```text

    認的形狀＝`assertNotIn(<文字 needle>, <整份檔案內容>)`，haystack 會往回解析同一個
    函式內的區域變數賦值（Pkg-P12 的原始缺陷正是
    `header = dest.read_text(...)[:4000]` ＋ `assertNotIn(stale, header)` 這種間接形態，
    只看斷言那一行是抓不到的）。

    刻意**不**認 bytes needle：`assertNotIn(b"\\r", raw)` 是位元組級不變量（帳本不可能
    「合法地」含 CR），不受「文件合法引用該字樣」影響，本檔第 ~1300 行就有一處。

    誠實劃界（做不到的部分，別把本掃描器當完整覆蓋）：
      1. 只解析**同一個函式內**、目標為單純 `Name` 的賦值。經 `setUpClass` 存成
         `cls.xxx` 再由 `self.xxx` 取用、或包一層自訂 helper 函式的間接形態抓不到——
         `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `self.adr` 就是這種形狀（本輪
         已列為跨包請求，不在本檔所有權內）。
      2. 一支「具名但其實沒收窄」的抽取器（例如 `def _narrow(t): return t`）會被誤放。
         那種東西在 code review 前不隱形，而本鎖要擋的是「順手拿整檔去比對」這個真實
         復發路徑。
```

### TestStatusColumnIsHeaderPositionedNotLastCell 修復前實測

原處：`tools/tests/test_archive_defect_log.py` L809-821（13 行，docstring 說明段）

```text

    構造輸入沿用 Pkg-P6 在閘門側用的那兩個（(a)(b)），差別是這裡套在**本工具**的
    `classify_row()`／`_row_id()` 上。修復前實測（同一組輸入、未動任何 tracked 檔）：

      (a) 狀態欄空白 ＋ 分流去向＝「已於上游 fixed 故不另修」
          → `_cells()` 只切出 6 欄、`cells[-1]` 取到「分流去向」
          → `classify_row()` 回 `cls='fixed'`、`blockers=[]` ⇒ **判為可搬**
      (b) 狀態欄空白 ＋ 分流去向＝「open 待下輪處理」
          → 回 `cls='open'`，恰好擋下但**擋的理由是錯的**（讀的是別欄）

    🔴 (a) 的危害比閘門那一側更重：閘門只是把狀態讀錯並印出來，本工具會依這個裁決
    **真的把該列寫進 archive** —— 一筆狀態欄空白（＝狀態不明）的缺陷就此靜默下葬，
    正是 R60 立本工具要消滅的那個病（`DEF-101-517`／`526` 誤搬）的同型復發。
```

### test_reverting_row_cells_to_the_filtering_version_is_detected 實測校正

原處：`tools/tests/test_archive_defect_log.py` L878-890（13 行，docstring 說明段）

```text

        這一條把正樣本的鑑別力**釘在具體那一行**（`if c.strip()`）上：若有人主張「狀態欄
        本來就讀得對、跟濾不濾空欄無關」，本測試證明不是。

        🔴 實測校正（我原本的預期是錯的，記在此以免下輪重犯）：我原先預期突變後該列會像
        修復前一樣「被判可搬」。實際不會 —— 濾空欄使該列只切出 6 欄，於是**判準⑤ 的 arity
        守門（第二層縱深）當場攔下**。也就是說 Pkg-P7 對這個缺陷佈了兩道獨立防線：表頭定位
        ＋欄數守門，任一道單獨被破都還有另一道。故本測試斷言的是「突變被偵測到」（裁決改變、
        且改變成具名的欄位定位失效），而不是「突變後仍被擋下」那種恆真寫法。
        修復前**整條**管線（無 arity 守門）確實會判可搬，由姊妹測試
        `test_the_pre_p7_pipeline_would_have_judged_sample_a_movable` 逐步重建坐實。

        🔴 突變一律走 runtime monkeypatch（`try/finally` 復原），**不**就地改 tracked 檔。
```

### test_arity_check_body_comes_from_the_gate_not_a_local_copy 兩件事與實測校正

原處：`tools/tests/test_archive_defect_log.py` L1112-1121（10 行，docstring 說明段）

```text

        兩件事同時被坐實：
          (a) 判準(7) 真的在消費**閘門那支純函式**——掏空它之後，注入那一列的偵測訊息必須
              消失。若本檔偷偷自己算了一份，該訊息會照舊出現，本斷言就紅。
          (b) 掏空它**不會**讓稽核靜默轉綠：具名基線的 stale 自檢會全面翻紅（登記 N 筆、
              實測 0 筆）。這是刻意的——「把檢查關掉」必須是一個吵鬧的動作。

        🔴 實測校正（原本的預期是錯的）：我原先斷言突變後 rc 應變 0。實際是 rc 仍為 1，
        因為 stale 自檢先叫起來了。恆真式地斷言「rc 仍為 1」則毫無鑑別力，故改為比對
        **problem 訊息集合的差異**。
```

### test_residence_branch_hits_the_real_ledger_family 語料選型

原處：`tools/tests/test_archive_defect_log.py` L1223-1234（12 行，docstring 說明段）

```text

        R60 round 1 的測試自寫正則只認 `立帳見本表 DEF-x`，真實 6 個指針只驗到 1 個，
        漏掉的 5 筆全是「（現居 archive_NN）」形態——而那正是 Scan-G 反駁者 #2 抓到的
        缺陷型。故這裡刻意以真實語料當守門樣本，而不是只靠合成樣本。

        🔴 刻意**不**在此對 `立帳見主檔` 分支下同樣的語料斷言：帳本正在把該形態逐步
        統一成「（現居 archive_NN）」（本輪 round 2 已把最後幾處改完，語料歸零），
        對「正在被淘汰的形態」下語料下限＝把鎖綁在會合法消失的東西上，那是自製誤紅。
        該分支的覆蓋改由兩處承擔且都不依賴語料：`_CASES` 的合成樣本（含 `立帳見主檔
        **DEF-101-491**`）＋ `TestCheckModeBugInjection.
        test_stale_main_scope_pointer_inside_an_archive_is_caught` 的真注入（該支另以
        「R60 前的窄樣式對同一段文字不命中」反向坐實本分支確為本輪新增）。
```

### test_the_ledger_may_quote_the_retracted_wording_verbatim_without_a_false_red 立案

原處：`tools/tests/test_archive_defect_log.py` L1952-1966（15 行，docstring 說明段）

```text

        為何這一條比「消掉紅燈」重要：修復前的取樣範圍讓**帳本永遠無法逐字保存自己要
        消滅的那句話**——Pkg-P11 撞到同一支紅時的處置就是把 `DEF-101-584` 的現象散文從
        逐字引用改成描述性寫法、逐字原文只留在證據檔（實測：活體主檔現在對「共七項」
        零命中）。那是**在資料側繞道**：讓帳本為了討好一支有 bug 的載具而扭曲自己的缺陷
        描述，與「原文逐字保全、零刪除」的史料紀律直接衝突。本測試解除該限制並釘死它。

        構造：合成列的「現象與證據」欄逐字含 `_STALE_NEEDLES` **全部三項**（含被推翻的
        方案(乙) 全稱）→ 跑 `apply()` → 該列被逐字搬進 archive → 主鎖判準（同一支
        `_retracted_claims_in()`，不是另寫一套）必須回**空清單**。

        雙向自證（缺一則本測試恆真）：
          (i)  整份 archive 全文**確實含**那三項字面 ⇒ 事故形狀真的被重現到；
          (ii) 取樣範圍**不是**被收成空字串／極短片段（否則 assertNotIn 廉價全過）。
        紅向由 `test_the_retracted_claim_lock_has_teeth_on_a_header_borne_claim` 負責。
```

### TestNoAssertionSamplesALiveDocumentWholesale 紀律與既有先例

原處：`tools/tests/test_archive_defect_log.py` L2591-2616（26 行，docstring 說明段）

```text

    **紀律**：斷言「某字串不得出現」時，取樣範圍必須**排除「合法引用該字串的區域」**。
    讀活體治理文件（缺陷帳本、archive、ADR、ONBOARDING）的鎖尤其如此，因為**那些文件的
    職責就是引用缺陷字樣**——帳本存在的目的是記錄缺陷，而記錄一個「某處寫了 X」的缺陷，
    必然要逐字寫出 X。把整份文件當 haystack，等於要求文件永遠不准談論自己要消滅的東西。

    **本輪實際付過的代價**（不是假想風險）史料搬遷，原文＝Guard_Repin 證據檔 §E-14。

    **同族**：與本輪已立帳的「載具量測 production 盲區」（載具只認棄用路徑的 marker，
    真跑恆 0）、「驗證載具本身要被驗證」是同一族——**問題都在量測面而非被測面**，而綠燈／
    紅燈都無法自己指出這件事。判定一處是否屬本族，問兩個問題：
      (i)  haystack 是否含「該字串會合法出現」的區域？
      (ii) 那個區域是否**不是**被測對象？兩者皆是 ⇒ 取樣範圍畫錯了。

    **既有的正確做法**（本 repo 已有先例，不必另創）：
      - 結構收窄：`_generated_header_of()`（切到第一列可解析缺陷列之前）、
        `test_nightly_interpreter_determinism` 只取「零命中分支」的 body、
        `test_ps_engine_ssot` 取 `ast.unparse` 後的函式本體（不含 docstring／註解）、
        `test_find_git_bash_parity._code_only()`（剝掉註解）。
      - 逐行 ＋ 例外出口：`test_no_stale_criterion_seven_reference_remains_in_the_tool`
        允許「判準⑦」出現在**帶『訂正』字樣的行**——歷史紀錄與現行指涉分開判。
      - 生產側同型解法：`check()` 判準(4)(6) 的 (甲) code span ／ (丙) ``` 圍籬例外，
        存在的理由一模一樣（帳本條目本來就會逐字引述判準語法）。

    本類別把上述紀律機械化，並用**合成違規片段**自證掃描器真的會說話（否則「掃描面乾淨」
    與「掃描器壞了」在綠燈上長得一樣）。
```

### 判準④ 安全網 R74 重構為何不是放寬

原處：`tools/tests/test_archive_defect_log.py` L2937-2957（21 行，註解區塊）

```text
    # 判準④ 安全網的鑑別力鎖 —— 🔴 **R74 重構：驗證對象由「現行主檔的具名 DEF 樣本」改為
    # 構造輸入**。以下逐字記錄為何這**不是**把鎖放寬，以免下一輪誤讀成退讓：
    #
    #   · 舊設計把樣本釘成一組活體 DEF-ID，並對「還有幾筆沒被歸檔」設 fail-loud 下限。
    #     它防的是「鎖無聲退化到零樣本」——那個顧慮完全正確，處置方向卻與工具的目的衝突：
    #     `archive_defect_log.py` 存在的意義就是把已結列搬走，而樣本**只能**取自「已結
    #     ＋ 帶交棒字樣」的列，也就是判準④ 一旦被具名承認就會離開主檔的那一批。於是
    #     「把該歸檔的都歸檔」與「保住足夠樣本」在結構上不可能同時成立：R74 要做最大化
    #     歸檔時，存活樣本必然歸零，而鎖自己的訊息同時禁止 skip、禁止下修下限、只准補新
    #     樣本——可是能補的樣本正好也都在這一次歸檔清單裡。三條出路全被堵住。
    #   · 真正該被鎖住的性質是**函式的行為**（「散文帶交棒字樣的列必須落在 needs_ack、
    #     不得落進 movable」），那是 `classify_row()`／`plan()` 的性質，與現行主檔裡剛好
    #     還剩幾筆無關。改用構造輸入之後，這條鎖**永遠有驗證對象**，不會隨歸檔流失——
    #     形狀沿用本 repo 既有的「抽成純函式即可用構造輸入證明有牙」慣例
    #     （`conservation_problems()`／`status_first_word_problems()` 皆如此）。
    #   · 生產面沒有因此失去覆蓋：`test_live_needs_ack_rows_really_carry_their_marker()`
    #     對現行主檔逐筆驗「工具報的 marker 逐字存在於該列、且該列不在 movable」，且它在
    #     needs_ack 為空時**不是靜默通過**——那時它改為斷言「主檔確實不存在任何
    #     (已結 ∧ 判準①②③⑤⑥ 全過 ∧ 帶交棒字樣) 的列」，兩種狀態下都是真斷言。
    #
    # marker 詞彙表：逐項取自 `ADL.HANDOFF_PROSE_RE`，每個 alternative 一個樣本。
```

### test_headroom_matches_what_def676_claims R68 訂正

原處：`tools/tests/test_archive_defect_log.py` L3091-3103（13 行，docstring 說明段）

```text

        🔴 R68 訂正（本鎖原形態會逼出它自己要防的行為）：原斷言是「餘裕恆 ≥ 門檻」。
        它在 R68 當場失效——本輪十二維掃描 9 列入帳後，兩次合法輪替仍只買回約 8000
        bytes 餘裕。此時原鎖給的**唯一**轉綠路徑是「再具名承認幾列去湊過線」，而那
        正是 DEF-101-676 立這條判準要防的事（R67 round 4 已因「量測快照當判準」被四方
        交叉命中過一次）。一個只能靠做壞事才能轉綠的鎖，不是護欄。

        改為對帳型斷言（形狀取自 DEF-101-689「修復包自報 status ↔ 帳本狀態欄」）：
          · DEF-101-676 宣稱**已結** ⇒ 判準必須當場成立（抓的是假宣稱，這才是重點）；
          · 宣稱**未結** ⇒ 餘裕不足是誠實揭露、不轉紅，但仍強制它帶承接指派
            （硬規則② 後半句），不得變成沒人接的永久停車位。
        兩個方向都留了牙：把狀態改回 `fixed` 卻不解決容量 → 紅；改成未結卻不寫承接
        → 紅。唯一的綠燈路徑是「要嘛真的解決、要嘛誠實掛帳並指名承接」。
```

### archive 內未結列常設複驗的住所裁決與 R81 轉格

原處：`tools/tests/test_archive_defect_log.py` L3128-3144（17 行，註解區塊）

```text
# ------------------------------------------- archive 內未結列的常設複驗（本輪新增）
#: 存量具名基線：`(archive 檔名, DEF-ID)`，本輪實查現況釘死。**只准變小**。
#:
#: 🔴 本鎖為何住在測試檔、而不是 `archive_defect_log.py --check` 的第 (9) 項判準
#: （本輪實際撞到的硬約束，寫下來以免下一輪重走一次）：那支工具受
#: `AutoClaude/tools/check_loc_budget.py` 的 `SPECIAL_FILES` **raw-line 棘輪**管，
#: 本輪動工前實測 1501 行／上限 1507 ⇒ 餘裕 6 行，而一項新判準（常數＋docstring 條目
#: ＋`# (N)` 實作段，三者由 `TestCriteriaListIsASingleSsot` 綁死、缺一即紅）實測要
#: 73 行。合法出口只剩「調高棘輪」，而那是本輪明令禁止的方向（棘輪只准變少），
#: 且該棘輪住在別包持有的檔。⇒ 判準改以測試側落地：射程由「pre-push 守門迴圈＋
#: root-infra-ci 的 --check step」縮為「根層 unittest 樹」，**誠實記載這個縮小**。
#: 🔴 R81 帳本清債包轉動一格（4 → 3）：`("…archive_01.md", "DEF-42-001")` 移除。
#: 該列在主檔與 archive 各有一份，主檔那份本輪結為 `closed-by-decision`（凍結版 v0.17
#: 依 Copy-on-Evolve 不修、原文自記隔離 3/3 全綠＝非回歸 flaky），archive 那份同批訂正
#: 首詞、原文逐字接於後 ⇒ 已不再是未結列。**這一格是被本鎖自己逼出來的**：只改主檔的
#: 那一刻 `test_archive_ids_are_disjoint_from_or_consistent_with_main` 立刻紅並指名
#: 「兩邊各說各話，只讀主檔者會誤判」——正是它存在的理由。
```

### TestArchiveUnresolvedRowsAreRatcheted 原始缺陷與雙向棘輪

原處：`tools/tests/test_archive_defect_log.py` L3176-3185（10 行，docstring 說明段）

```text

    原始缺陷（本輪 Scan-G）：搬遷判準① 只在 `plan()`／`classify_row()` 執行一次，
    也就是**搬遷當下**；此後那一列的狀態欄怎麼變都沒有任何東西會看。而
    `--unresolved-count` 與三道承接判準又都只讀主檔 ⇒ 進了 archive 就等於離開稽核。
    實測現況：archive 內有未結分類列，全 repo 沒有任何閘門對它們說一個字。

    棘輪為何是**雙向**：只擋「表外新增」會讓具名基線變成只進不出的死名單，
    「archive 裡還剩幾列未結」永遠不會下降（同 crossref 的
    `stale_grandfather_problems()` 判例）。刻意不一次全紅：存量是歷史事實，
    硬擋會讓鎖上線即永紅（ARCH-R59-NB4），比沒有鎖更糟。
```

### TestArchiveIndexDocIsExternalized 原始缺陷與三項前提

原處：`tools/tests/test_archive_defect_log.py` L3352-3367（16 行，docstring 說明段）

```text

    **原始缺陷**：索引 bullet 是**單調增長且永遠無法靠歸檔回收**的一段（每次 `--apply`
    往主檔多寫約 0.9KB，近幾輪每輪建 3~5 支 archive），卻與缺陷總表共用主檔那條
    262,144 bytes 硬線。R69 動工時主檔距硬線只剩 250 bytes 而 `--plan` 可搬 **0 筆**
    ——把單調增長項放進有硬上限的檔，數學上保證撞牆，而歸檔吞吐再高也救不了它。

    **本鎖要守的是「搬出去之後守門沒有變弱」**，因為那才是這次外移的前提：
      (甲) 索引檔仍屬**帳本家族** ⇒ 指針稽核（判準④⑥）、體積守門、compat-CI 的
           `AutoSDD_Defect_Log_archive_*.md` `paths:` glob、沙箱複製面**全部零改動即涵蓋**。
           若有人把它改名成家族 glob 外的形態（例如 `..._INDEX.md` 不帶 `archive_`），
           這四道守門會同時、靜默地漏掉它 —— 正是 `DEF-101-587`「搬到另一支檔就繞過
           守門」的形狀，故用測試把「它必須在家族內」釘住。
      (乙) 索引檔**自己不需要 bullet**（它是目錄不是史料檔），判準⑤ 對它具名排除；
           排除若寫成「零表格列就跳過」這種模糊判準，真正忘記登記的史料檔也會被吞掉。
      (丙) 主檔內**不得再殘留**任何索引 bullet：殘留＝兩份索引並存，判準⑤ 只讀其中
           一份，另一份腐化零訊號。
```

## test_bash_probe_spec_contract.py

### _BASH fixture 探測的 R64／R69 沿革

原處：`tools/tests/test_bash_probe_spec_contract.py` L35-49（15 行，註解區塊）

```text
# 探測本機一支「真正可用」的 bash 供本檔 `_BASH` fixture 使用。
#
# WHY（R64／DEF-101-617）：舊版 `_BASH = shutil.which("bash")` 在「PATH 上 `bash`
# 解析到 WSL System32 佔位版、真正的 Git Bash 未直接掛在 PATH、只能透過 `git.exe`
# 相對路徑找到」這種真實可重現的 Windows 設定下，會把該被排除的佔位版錯當成可用
# bash——`_BASH` 本身就是錯的，本檔在這種機器上有 6/8 測試確定性失敗。
#
# R69 後續（DEF-101-753）：該修復當時以私有函式落在本檔，
# `test_macos_smoke_skip_honesty.py` 另有一份判準不一致的複本，而
# `test_smoke_ci_sync.py` 連探測都沒有 ⇒ 三處收斂至 `_platform_helpers.
# usable_bash_for_fixture()`。**這不違反本檔頭 docstring 的「三份消費者各自獨立
# 重寫」慣例**：那條慣例的射程是「驗證探測規則本身」的三份回歸鎖（本檔的
# `usable_bash_with_probe_spy()` 仍直呼生產端 `bash_probe.usable_bash()`，鑑別力
# 不受影響）；本行要的只是「給我一支能跑的 bash」當 fixture，用途不同。
# 找不到就 `@unittest.skipUnless(_BASH, ...)` 跳過，不是失敗。
```

### _PATH_HONOURING_BASH 為何不能沿用 _BASH

原處：`tools/tests/test_bash_probe_spec_contract.py` L52-62（11 行，註解區塊）

```text
# 手法 A（`env={"PATH": <只有空目錄>}` 讓 `dirname` 查不到）專用的載具，與 `_BASH` 分開取
# （DEF-101-762，R71 於 Windows 11 真機收斂 DEF-101-618(a) 的殘留）。
#
# WHY 不能沿用 `_BASH`：兩者要的性質不同，而在 Windows 上它們**經常不是同一支**。
# `_BASH` 要的是「跑得動 repo 的 .sh」，於是當呼叫端 ambient PATH 不含 coreutils 目錄時，
# `Git\usr\bin\bash.exe` 會因驗活找不到 `dirname` 被淘汰，`_BASH` 落到會自我注入
# `/mingw64/bin:/usr/bin` 的 `Git\bin\bash.exe`——那支**外部 PATH 管不住**，手法 A 對它
# 是 no-op（`_platform_helpers.honours_external_path()` docstring 有兩支的實測對照）。
# 於是同一份工作樹、同一支測試，在 Git Bash 殼層下跑是綠的、在 PowerShell 殼層下跑是紅的
# ——紅的那次量到的是載具失效，不是被測物缺陷。本常數改以「載具性質」機械挑選，讓結果
# 不再隨呼叫端殼層的 ambient PATH 漂移。
```

### _build_coreutils_less_bash_clone 手法 B 的 WHY 與複製品結構

原處：`tools/tests/test_bash_probe_spec_contract.py` L108-125（18 行，docstring 說明段）

```text
    WHY：`export PATH=` 限縮外部傳入 PATH 這招對真實 `Git\\bin\\bash.exe`
    完全無效——該啟動器啟動時會**無條件**把 `/mingw64/bin:/usr/bin`（相對自身
    安裝根目錄）注入到自己內部 PATH 最前面，不受外部傳入 PATH 內容影響（實測：
    `env={"PATH": <單一空目錄>}` 呼叫後，bash 內部 `echo $PATH` 仍印出
    `/mingw64/bin:/usr/bin:...`）。要讓這款啟動器對 `dirname` 確定性失敗，須讓
    它自我注入的目標目錄本身缺 coreutils，而非限縮外部 PATH（那是手法 A，只對
    `usr/bin/bash.exe` 這類不自我注入的解譯器有效，見 `TestProbeCmdRealSubprocessBehavior`）。

    複製品結構（皆複製自本機真實 Git 安裝，路徑相對 `tmp_root`）：
      bin/bash.exe          <- 啟動器本體（真實 `<install_root>/bin/bash.exe`）
      usr/bin/bash.exe      <- 真解譯器（真實 `<install_root>/usr/bin/bash.exe`）
      usr/bin/msys-2.0.dll  <- 解譯器執行期依賴（缺了會啟動失敗，非本測試要模擬
                                的「找不到 dirname」情境，兩者性質不同）
      etc/                  <- 空目錄（MSYS root 偵測標記）
      mingw64/bin/          <- 空目錄（自我注入目標之一，刻意不放 coreutils）

    找不到本機真實 Git 安裝（例如非 Windows 平台）回傳 `None`，呼叫端應
    `skipTest`。
```

### usable_bash_with_probe_spy WHY（R60 A-01／DEF-101-531）

原處：`tools/tests/test_bash_probe_spec_contract.py` L151-167（17 行，docstring 說明段）

```text

    WHY（R60 A-01／DEF-101-531）：生產端 `bash_probe.usable_bash()` 的 `except
    Exception: continue`（`AISDLC_SDD/scripts/bash_probe.py:79-80`）把兩種語意
    完全不同的情況壓成同一個 `None`——
      ① 子行程真的起來、跑完 `PROBE_CMD` 而**驗活失敗** → 候選被正確拒絕（我們要驗的）；
      ② 子行程**根本沒起來**（`OSError`）→ 載具壞掉，對生產端 wiring 零資訊。
    只用 `assertIsNone(result)` 的測試無法分辨兩者，於是可以在 ② 之下長年假綠。
    本 helper 把兩種來源分流回傳，讓斷言端**必須**表態。

    回傳 `(result, completed, spawn_errors)`：
      `completed`    = `[(returncode, stdout), ...]`（子行程起來並跑完）
      `spawn_errors` = `[OSError, ...]`（`CreateProcess`／`execve` 失敗，載具壞掉）

    `candidate_bash`（DEF-101-618(a) 新增，選用）：指定要驗的候選 bash 路徑；
    省略時沿用既有預設值 `_BASH`，對既有呼叫端零行為變化。用於讓
    `TestUsableBashRejectsCoreutilsLessBinBashClone` 可以指定手法 B 建構出的
    「缺 coreutils 複製品」作為候選，而非本檔 fixture 探測到的真實可用 bash。
```

### TestBinBashLauncherSelfInjectsPathContract 互補關係與 R71 收斂

原處：`tools/tests/test_bash_probe_spec_contract.py` L253-268（16 行，docstring 說明段）

```text
    對 `bin/bash.exe` 這類會自我注入 PATH 的啟動器無效，但讓 bash **自己**在
    啟動器完成自我注入之後、於自身行程內部執行 `export PATH=` 則可讓它確定性
    失敗」這個現象本身，證明 R64 殘留發現（`TestProbeCmdRealSubprocessBehavior`
    的兩支「拒絕」測試在 pwsh 下選到 `bin/bash.exe` 時失去鑑別力）的前提是真的，
    也證明手法 A 的解法（"export PATH= ; " 前綴）對它真的有效。

    此類與 `TestProbeCmdRealSubprocessBehavior`（驗證 `usr/bin/bash.exe` 這類
    不自我注入的解譯器）互補、不重複：兩者驗證的是兩款不同二進位對同一種模擬
    手法的不同反應，各自對不同候選類型維持鑑別力。

    🔴 **R71／DEF-101-762 收斂上述「R64 殘留發現」**：該殘留當時只被記載、沒被修，
    因為它在 macOS 與 Git Bash 殼層下不顯形。真正的觸發條件不是 pwsh，而是**呼叫端
    ambient PATH 有沒有 coreutils 目錄**——沒有時 `usr/bin/bash.exe` 會驗活失敗，
    `_BASH` 就落到這支自我注入的啟動器上。修法是讓那兩支「拒絕」測試改用依載具性質
    機械挑選的 `_PATH_HONOURING_BASH`，不再沿用 `_BASH`；上面那句「互補」因此從
    **巧合**變成**被強制**的事實。
```

### DEF-101-762 候選指定與 R60 A-01 載具修正

原處：`tools/tests/test_bash_probe_spec_contract.py` L395-407（13 行，註解區塊）

```text
        # DEF-101-762：候選明確指定 `_PATH_HONOURING_BASH`，不再沿用 `_BASH`。生產端
        # `usable_bash()` 把候選當黑盒子呼叫（argv 寫死 `[cand, "-c", PROBE_CMD]`），測試側
        # 唯一能施力的就是「餵它一個外部 PATH 管得住的候選」；餵到自我注入的啟動器時，
        # 下面那條 `assertNotEqual(rc, 0)` 量到的是載具失效（見類別上方 skip 述詞）。
        # R60 A-01 修正載具：舊版用 `{"PATH": ""}` + `clear=True`，在 Windows 上**兩段都壞**——
        #   ① Windows 的 `os.environ["PATH"] = ""` 是「**刪除**該變數」而非「設為空字串」
        #      （本機實測：設完 `GetEnvironmentVariableW("PATH")` 回 0／ERROR_ENVVAR_NOT_FOUND），
        #      而子 MSYS bash 在**完全沒有 PATH** 時會自行合成 `/usr/local/bin:/usr/bin:...`
        #      → `dirname` 照樣找得到、驗活成功 → 本測試該紅（pytest 載具下實測就是紅的）；
        #   ② 再加 `clear=True` 清空整個環境區塊 → `CreateProcess` 回 `[WinError 87]`，
        #      子行程根本沒起來、`except Exception` 吞掉 → `None` → 誤綠（官方 unittest 閘門）。
        # 改用「PATH 指向一個真實存在但空無一物的目錄」：兩平台皆讓 bash 用得到 PATH 這個
        # 變數、卻找不到 `dirname`（本機實測 rc=127 / `dirname: command not found`）。
```

### TestRestrictedPathCarrierCannotSilentlyVanish WHY 與誠實劃界

原處：`tools/tests/test_bash_probe_spec_contract.py` L524-535（12 行，docstring 說明段）

```text

    WHY（R69 教訓的直接套用）：上面兩支「拒絕」測試現在掛著 `_needs_path_honouring_bash`
    這個帶述詞的 skip。帶述詞的 skip 解決了「在無鑑別力載具上報誤導性紅燈」，卻開了另一
    個口子——**若哪天所有候選都變成自我注入形態，述詞會恆假、兩支測試永久空轉，而
    `run_root_unittests.py` 的 rc 仍是 0**。那正是 R69 付過學費的形狀（樣本被搬光後靜默
    skip），只是換成從載具側觸發。本類把「該 skip 述詞恆假」本身變成紅燈。

    誠實劃界：本類只看**手法 A**這條通道。手法 B（`TestUsableBashRejectsCoreutilsLess
    BinBashClone`，複製一份缺 coreutils 的 Git 樹）是對自我注入啟動器仍有效的互補通道，
    它自己的存活由該類 `setUp()` 的具名 `skipTest` 呈現，不併入本哨兵——兩條通道驗的是
    不同層（手法 A 兼顧 PROBE_CMD 本身與生產端 wiring，手法 B 只到 wiring 層），任一條
    斷掉都該各自具名，混成一條會讓「斷了哪一條」變得不可讀。
```

### TestWslStubIsNeverAcceptedAsRealBash WHY 與 DEF-101-754

原處：`tools/tests/test_bash_probe_spec_contract.py` L608-627（20 行，docstring 說明段）

```text

    WHY 這支測試要讓 stub「驗活成功」（Rule 9 — 鎖的是意圖不是行為）：真實世界的
    WSL 佔位 bash 在**未安裝發行版**時會 `exit 1`（R69 雲端實測輸出即為 UTF-16LE 的
    `Windows Subsystem for Linux has no installed distributions.`），於是任何帶驗活的
    探針都會**碰巧**拒絕它——收斂前 `test_macos_smoke_skip_honesty._usable_bash()`
    的裸 bash 分支根本沒有 System32 排除，卻一直是綠的，靠的正是這個僥倖。一旦機器
    真的裝了發行版，驗活就會在 Linux 裡成功，該探針便會把 repo 的 Windows 腳本丟進
    WSL 跑。本鎖因此刻意把僥倖拿掉：stub 驗活成功，**只剩路徑規則能救**。

    可在 macOS 上跑（`PureWindowsPath` 對 POSIX 路徑同樣依段切分，見
    `bash_probe_spec.SYSTEM32_SEGMENT` 的消費端註解），不需要 Windows 真機。

    🔴 **但「可在 macOS 上跑」不等於「在 Windows 上跑得起來」**（DEF-101-754）：
    本類最初把 stub 一律寫成 shebang 腳本、Windows 上只把檔名改成 `bash.exe`，
    於是下方正控在真 Windows 上以 `WinError 216` **error 收場**——本類自己就是
    `improving_103` §9.5 那條新規則（「只在某平台成立的判斷，回歸鎖必須有本機可
    重現該平台語意的路徑」）落地的第一個實例，而它違反了該規則的**對偶方向**：
    只顧本機重現得了，沒顧目標平台跑不跑得動。stub 形態改由 `_STUB_FORMS` 依
    `os.name` 分派，兩平台皆為真執行；形態本身由
    `TestStubFormIsLaunchableOnItsOwnPlatform` 在**任一平台**機械看守。
```

### TestStubFormIsLaunchableOnItsOwnPlatform WHY（§9.5 的對偶方向）

原處：`tools/tests/test_bash_probe_spec_contract.py` L712-721（10 行，docstring 說明段）

```text

    WHY（DEF-101-754，Rule 9 — 鎖的是意圖不是行為）：`improving_103` §9.5 訂立
    「凡只在某平台才成立的判斷，回歸鎖必須有一條能在本機重現該平台語意的路徑」，
    而 `TestWslStubIsNeverAcceptedAsRealBash` 是它落地的第一個實例——**結果它自己
    只在 macOS 跑得動，在 Windows 上以 `WinError 216` 炸掉**。這揭露 §9.5 的規則
    寫得不完整：只要求「本機重現得了」，沒要求「目標平台上真的執行得起來」，於是
    規則只活在文件裡，沒有任何機械物在看它。

    本類就是那個機械物：它把「某形態能不能被某平台啟動」變成**在任何平台上都可判
    定**的斷言，因此 macOS 上的開發者不必等雲端 CI 就會知道 Windows 分支寫壞了。
```

### test_windows_form_is_findable_by_the_production_helper 為何獨立一支

原處：`tools/tests/test_bash_probe_spec_contract.py` L775-785（11 行，docstring 說明段）

```text

        WHY 這支獨立於上一支：上一支只看副檔名字串，看不到「生產端 helper 到底找
        不找得到它」。若 Windows 形態改名成 `bash.sh`，`usable_bash_for_fixture()`
        會回 `None`，於是 `test_system32_stub_is_rejected` 的 `assertIsNone` 會因為
        **根本沒找到任何候選**而通過＝假綠，主判準（System32 段規則）一次都沒被執行。

        本機 macOS 以 `sys.platform` + `PATHEXT` 驅動**真正的** `shutil.which()`
        （不是重寫一份它的邏輯）來重現 Windows 解析語意。誠實劃界：這裡重現的是
        「PATHEXT 展開」這一段，**不含** `CreateProcess` 真的把 `.cmd` 交給 cmd.exe
        執行那一段——後者本機無法重現，由 Windows CI 上的
        `test_stub_is_live_so_only_the_path_rule_can_reject_it` 真執行覆蓋。
```

## test_check_hooks_liveness.py

### _child_env 沿革（DEF-101-789／DEF-101-803）

原處：`tools/tests/test_check_hooks_liveness.py` L237-251（15 行，docstring 說明段）

```text

    🔴 為何不能靠繼承（DEF-101-789）：`_run_hook` 原本不傳 `env=`，於是子行程的
    UTF-8 串流設定由**外層環境供應**——本機唯一來源是 `.claude/settings.json` 的
    `env.PYTHONUTF8=1`（User/Machine scope 實測皆空），也就是說這支鎖的綠燈是
    agent harness 注入的，不是被測物的性質。同一份知識 repo 內早有兩處落地：
    `test_find_git_bash_parity.py` 對 `PYTHONUTF8` 的 `env.pop`（該處逐字寫明
    「不能靠繼承而假綠」）與 `test_git_hooks_install_common.py` 的
    `_env_without_utf8_overrides()`。**知識在樹裡、只有一處有鎖，新站點照樣踩進去**
    ——本函式把它補齊到第三處。

    🔴 R75 補記（DEF-101-803）：上一段逐字指名「本機唯一 UTF-8 來源是
    `.claude/settings.json` 的 `env.PYTHONUTF8=1`」，而那個 env 條目**當時零鎖看守**
    ——被誰刪掉都不會有任何測試變紅，R74 P0 就靜默復發。**在註記裡指出一個關鍵依賴
    卻不給它鎖，等於把它標成「已知且已接受」**。該鎖現在在
    `TestSettingsProvideUtf8ForHookChildren`。
```

### _run_hook 走子行程與 force_os_name 的立案

原處：`tools/tests/test_check_hooks_liveness.py` L267-280（14 行，docstring 說明段）

```text

    刻意走子行程而非 import + monkeypatch：hook 的契約是「被 Claude Code 以獨立行程
    呼叫、讀 stdin、以 exit code 表態」，import 進來直接呼叫 `main()` 會繞過
    `sys.stdin` 與 exit code 這兩個契約面（本 repo 有「驗證載具必須對齊 production
    真正執行路徑」的既有紀律）。

    子行程環境一律走 `_child_env()`（剝除 UTF-8 覆寫），理由見該函式。`env_extra`
    用來**指定**一個非 UTF-8 的 locale 編碼，重現 en-US Windows／GitHub
    windows-latest 的條件。

    `force_os_name` 用來驗非 Windows 分支：hook 讀 `os.name`，而測試機是 Windows。
    以 `-c` 前置注入假 `os.name` 再 exec hook 本體，是唯一能在單一平台上驗到
    **兩個平台方向**的做法（同 `test_ps_engine_ssot.py` 用合成 `shutil.which`
    偽造雙引擎的理由：判準的方向不該取決於這台機器剛好是什麼）。
```

### 退化 payload × matcher 射程兩道鎖交界的立案

原處：`tools/tests/test_check_hooks_liveness.py` L299-321（23 行，註解區塊）

```text
# ══════════════════════════════════════════════════════════════════════════
# 退化 payload × matcher 射程：兩道鎖的交界（本輪，DEF 待登記）
# ══════════════════════════════════════════════════════════════════════════
# 這一段取代了此前兩條「退化 payload 一律 exit 2」的平坦斷言。**不是放寬**，是把
# 它們真正要防的東西寫清楚，順便解掉一組互鎖。
#
#   · 那兩條要防的是**守衛靜默失效**：讀不懂輸入時放行，等於讓「送壞 payload」
#     成為讓守衛整支消失的免費手段，而且失效不會有任何人看見。這個意圖不變。
#   · 但它們寫成「一律 exit 2」，於是硬擋的爆炸半徑完全由**註冊面的 matcher**
#     決定，而 matcher 由另一道鎖在管（子代理注入曾要求每個 matcher 都含 Task）。
#     兩者相乘的結果：一份解析不出工具名的 payload 會讓一支與子代理無關的守衛
#     硬擋派工，訊息還指向不相干的原因。七輸入實測逐字重現過該狀態。
#
# 新判準把兩件事綁成一個不可拆的組合：
#   ① 退化 payload **不得被靜默放行**（rc==0 即紅——原意保住）；
#   ② 若守衛選擇硬擋（rc==2），它註冊的 matcher **不得圈到射程外的工具**。
# 想放寬 matcher 的人會被逼著同時面對退化行為，反之亦然，交界處不再有無人同意的
# 狀態。對稱的另一半在 AISDLC_SDD/scripts/tests/test_pretooluse_matcher_task.py
# （全稱約定收斂為只約束承載子代理注入的那些條目）。
#
# 誠實劃界：本判準**不**釘住「某支守衛必須選 rc==2 而不是 rc==1」。rc 2→1 是行為
# 變更但不是靜默失效（仍會出聲），要不要那樣改屬設計決定，記在各 hook 自己的
# docstring 裡；本判準只保證兩者永遠是配套的。
```

### TestBlockBashHookGuidanceSurvivesNonUtf8Locale WHY

原處：`tools/tests/test_check_hooks_liveness.py` L473-486（14 行，docstring 說明段）

```text

    WHY：`sys.stderr` 的預設 `errors` 是 `backslashreplace`，所以 locale 編碼
    表達不了 CJK 時（en-US Windows／GitHub windows-latest 的 cp1252）整段指引
    會變成 `\\uXXXX` 逃脫字面；locale 表達得了但不是 UTF-8 時（zh-TW 的 cp950）
    則是讀者端亂碼。兩種都不是「測試紅」而是**功能缺陷**：這支 hook 的存在理由
    就是「純文件約束無攔阻力」，指引不可讀＝阻斷有了、教學沒了，使用者被 exit 2
    硬擋卻拿不到替代指令。

    判準刻意寫在**測試名**上，不隱含在環境裡——上一版的綠燈來自 harness 注入的
    `PYTHONUTF8`，而環境是會變的，沒有人會去讀它。

    兩案皆以 `force_os_name="nt"` 驅動，因此在 mac/Linux 也真的會跑：這個缺陷
    的成因是「locale 不是 UTF-8」，不是「作業系統是 Windows」（`DEF-101-766`
    的反面教訓——判準的射程不該被當下這台機器的平台綁住）。
```

### TestSettingsProvideUtf8ForHookChildren WHY

原處：`tools/tests/test_check_hooks_liveness.py` L669-682（14 行，docstring 說明段）

```text

    WHY 這道非有不可：本檔上方 `_child_env()` 的註記逐字宣告「本機唯一 UTF-8 來源
    是 `.claude/settings.json` 的 `env.PYTHONUTF8=1`」，而該 env 條目此前**零鎖
    看守**（R75 QA 全域搜尋 `tools/tests` 內對 settings.json 的 `PYTHONUTF8` 斷言：
    零命中；旁邊那道 `TestBlockBashHookIsActuallyRegistered` 只驗 hook 註冊）。
    也就是說：把那三行刪掉，全庫測試一片綠，而 R74 那筆 P0（hook 中文指引在非
    UTF-8 codepage 下降解）就靜默復發。**在註記裡點名一個關鍵依賴、卻不給它鎖，
    等於把它登記成「已知且已接受」。**

    🔴 為何注入案走「讀真實內容 → 在記憶體裡拿掉那把鑰匙」而不是真的改磁碟上的
    settings.json：該檔自己記載過 P0「hook 誤觸 PreToolUse deny 會把所有工具硬鎖
    死」，而 R75 是多 agent 同時在同一棵樹作業的輪次——把 hook 子行程的編碼設定
    真的拔掉幾秒鐘，影響面是**全部** agent 的工具呼叫。記憶體注入對「判準有沒有
    鑑別力」的證明力完全相同（被注入的是真實檔案的內容），風險卻是零。
```

### lint_powershell_command 回歸鎖的立案量測

原處：`tools/tests/test_check_hooks_liveness.py` L739-753（15 行，註解區塊）

```text
# ══════════════════════════════════════════════════════════════════════════
# `.claude/hooks/lint_powershell_command.py` 的回歸鎖（本輪新增）
# ══════════════════════════════════════════════════════════════════════════
# 為何併進本檔：`tools/tests/` 檔數是 shrink-only 棘輪，明文禁止新增鎖檔；而本檔
# 本來就是「hook 有沒有註冊、是不是活的」那一層的家。
#
# 為何非有這支守衛不可（本輪立案量測）：session 逐字稿實測到一組乾淨的對照——
# **有觀測者的那條規則違規 1 次且被當場擋下，沒有觀測者的那些違規率 20~35%**。
# PowerShell 工具面在它出現之前**零觀測者**：禁裸 cd 那條規則的違規面在**指令
# 字串的內容**裡，而那個字串永遠不會變成 repo 裡的檔案，於是全庫靜態掃描器
# 結構上都看不見它。差別不在紀律寫得夠不夠嚴厲。
#
# 本鎖守五件事：①三條檢查各自真的會擋；②合法形態不得誤擋（誤報會讓整個機制被
# 關掉，那比漏擋更糟）；③不早退——三條命中要一次報齊；④射程不得擴大；
# ⑤退化 payload 走「出聲但不阻斷」，且與 matcher 射程配套（見上方判準）。
```

### R79 Auto Pilot commit／push 阻斷的立案

原處：`tools/tests/test_check_hooks_liveness.py` L1070-1085（16 行，註解區塊）

```text
# ══════════════════════════════════════════════════════════════════════════
# R79 Auto Pilot：無人看管那一跑的 commit／push 阻斷
# ══════════════════════════════════════════════════════════════════════════
# 為何併進本檔：`tools/tests/` 檔數是 shrink-only 棘輪（禁新增鎖檔），而這條規則
# 住在本檔已經在守的那支 hook 裡。
#
# 立案：掌舵者 R79 逐字裁決「現在開，但禁止 commit/push」——開的是 planner 的
# `--allow-resume` 預設。條件不是建議，所以它必須有牙；而「那一跑要遵守任務書第 4 節」
# 是散文，本 repo 對散文的攔阻力已有三次實證（都是 0）。
#
# 本鎖守四件事，**每一件都帶反向**（只帶一個方向的鎖必然在另一個方向恆綠）：
#   ① 有訊號 × 會動 git 歷史 → 必須 exit 2；
#   ② **沒有訊號** × 同一條指令 → 必須 exit 0（互動 session 零附帶面。這一條若壞掉，
#      掌舵者自己的 commit 會被鎖死，而那會讓整個機制當場被關掉）；
#   ③ 有訊號 × 無關指令（`git status`／`git log`）→ 必須 exit 0；
#   ④ 行內豁免對本條**無效**（無人看管的那個回合可以自己寫豁免註解）。
```

### 失誤歸因分群器契約鎖的立案

原處：`tools/tests/test_check_hooks_liveness.py` L1565-1574（10 行，註解區塊）

```text
# ══════════════════════════════════════════════════════════════════════════
# 失誤歸因分群器的契約鎖（R79 新增）
# ══════════════════════════════════════════════════════════════════════════
# 為何住在本檔：`tools/tests/` 不得新增鎖檔（DEF-101-561③），而這支分群器是同一組
# 觀測者的第三件——攔截（hook）／量測（probe）／歸因（本項）。
#
# 🔴 它要守的那件事很窄但很關鍵：根 CLAUDE.md 逐字要求「每輪重跑一次，分群腳本與桶的
# 判準要具名可重跑」，而 R77 那次分群**沒有留下任何產物**（來源清單不在 repo 內、
# 全庫零分群腳本）⇒ 那條要求結構上永遠滿足不了，於是那組百分比變成不可稽核的常數，
# 正是 R71 的 n=8 模型被當現行結論用五輪的同一個形態。
```

### 攔截器 × 量測器兩份複本綁定的立案（R78／SA-02）

原處：`tools/tests/test_check_hooks_liveness.py` L1645-1662（18 行，註解區塊）

```text
# ══════════════════════════════════════════════════════════════════════════
# 攔截器 × 量測器：同一條規則的兩份複本必須綁在一起（R78／SA-02）
# ══════════════════════════════════════════════════════════════════════════
# 現象：`lint_powershell_command.py`（事中攔截）與 `tools/probe/audit_session.py`
# （事後量測）判的是同一組規則，卻各存一份判準字面，而 R77 交付時**已經不一致**
# ——hook 那份有 `Tee-Object`、探針那份沒有，兩份零比對。後果不是「少擋一種」而是
# 更難看見的那一種：同一段違規**攔得下、卻量不到**，於是量出來的違規率偏低，
# 而那個數字正是拿來寫進根 CLAUDE.md 下結論用的。
#
# 為何不抽共用模組：hook 由 `runpy.run_path` 起，`sys.path` 上沒有 `tools/`，
# import 期爆掉會破壞它的 fail-open 契約（settings.json 記載過的 P0）。複本是
# **結構上被逼出來的**。既然只能留複本，就把複本的一致性變成會轉紅的事件。
#
# 兩向都要，缺一即有繞道：
#   ① 字面相等——兩份 `SHARED_PATTERN_SOURCE` 必須逐字相同。抽不到（改名／改寫成
#      非字面）也算紅，否則「把常數拿掉」就是一條無聲的出口。
#   ② 行為一致——同一批指令餵進兩邊，判定必須相同。這一向抓得到「字典同步了，
#      但某一邊另外藏了第二份複本／組裝時漏接」，字面相等抓不到那個。
```

### 註冊面棘輪的立案與分工（R78／QA-03）

原處：`tools/tests/test_check_hooks_liveness.py` L1783-1812（30 行，註解區塊）

```text
# ══════════════════════════════════════════════════════════════════════════
# 註冊面棘輪：hook 的觸發射程只准擴大、不准縮小（R78／QA-03）
# ══════════════════════════════════════════════════════════════════════════
# 🔴 這一筆比「鎖沒有鑑別力」再深一層：**鎖本身可以被無聲拆掉**。
#
# QA 的突變測試 M4 實測：把根 `.claude/settings.json` 的 PostToolUse
# `matcher: "Write|Edit"` 改成 `"Write"`——這會讓 `check_ps1_encoding.py` 與
# `check_sh_eol.py` 對 **Edit 工具整支失效**（Edit 寫出的 CRLF `.sh`、無 BOM `.ps1`
# 從此無人守）——全套閘門 **rc=0 全綠，零鑑別力**。同時實查：本檔上方的
# `matchers_for_script()` 只掃 PreToolUse；全 `tools/tests/` 除本輪新建的
# `test_context_budget_guard.py` 外，沒有任何檔案提到 `PostToolUse`。
# ⇒ PostToolUse 的註冊面（matcher 射程、條目存在性）在此之前**完全無人守**，
# 而根 CLAUDE.md 花了整整一節在講「已橋接的 2 支 hook 在根 session 會跑」。
#
# 與 `test_doc_loc_baseline_freshness_r60.py::TestR74RootClaudeMdHookClaimsMatchRegistration`
# 的**分工**（兩者都讀同一份 settings.json，但問的問題不同，不重複）：
#   · 那一道守「**文件怎麼寫**」——根 CLAUDE.md 對某支 hook 的射程宣稱，與它在
#     settings.json 裡「有沒有被註冊」是否雙向一致。它的判定面是**腳本 basename 的
#     存在性**，對 matcher 圈了哪些工具、掛在哪個事件**完全不看**（M4 那個突變在它
#     眼裡毫無變化：hook 還在，只是不再對 Edit 觸發）。
#   · 本道守「**註冊面怎麼變**」——每支已註冊 hook 的 (事件, 觸發工具集合) 相對釘選
#     基準只准擴大。它不讀任何 .md，不管文件怎麼寫。
#
# 🔴 為何是「釘現況＋只硬擋劣化方向」而不是「必須等於某個理想集合」：本 repo 明文
# 判例——**永紅的閘門會被整個關掉，比沒有鎖更糟**。擴大 matcher（多守一個工具）與
# 換成 `*` 一律綠；只有「某支 hook 不再被它原本守著的工具觸發」與「條目整個消失」
# 會紅。要合法縮小射程，就得在同一次變更裡動下面那張表，讓那個決定被複審看見。
#
# 誠實劃界：本鎖只讀 repo 內的 `.claude/settings.json`。`settings.local.json`／
# 使用者層設定的合併結果不在射程內（那些不進版控，鎖不到也不該鎖）。
```

### R83 毀滅性 git 阻斷器註冊面回填的立案

原處：`tools/tests/test_check_hooks_liveness.py` L1859-1873（15 行，註解區塊）

```text
    # 🔴 R83 新增：毀滅性 git 指令阻斷器的**註冊面回填**（由並行的另一個包新增條目，
    # `.claude/settings.json` 不在那個包的檔案所有權內時本表就會落後——同上方 R79 那格的
    # 既有紀律，收輪者負責讓帳對得上）。
    # 立案是本輪的真實事故：一個 subagent 在**六包並行共用的工作樹**上跑
    # `git stash -q -u --keep-index`，瞬間清空 16 個修改檔 + 4 個未追蹤檔（含其他包正在
    # 寫的檔），靠 `stash pop` 還原、未偵測到資料遺失——**但那是運氣不是設計**。
    # 任務書當時已寫「不要 git add / commit / push」⇒ **禁令沒涵蓋到的那個動詞就是被踩的
    # 那個**，而 R71 已實證純文件約束對「當下的模型」零攔阻力。
    # matcher 取 `{Bash, PowerShell}` 的依據是**逐字稿實查**而非推測：本機 60 份逐字稿、
    # 7,189 次 tool_use 中 Bash 4,083 次、PowerShell 0 次（Windows 側是另一個 project dir，
    # 且該平台依鐵律一禁用 Bash ⇒ 一律走 PowerShell）。兩者相加＝腳本自己的 OWN_TOOLS；
    # 🔴 R95 起 matcher＝OWN_TOOLS ∪ GOV_TOOLS（治理檔禁寫；下限同步升格，射程縮回即紅）。
    # 該守衛對退化 payload 走 rc=1（出聲不阻斷）故不受「rc==2 必須配窄 matcher」那條約束，
    # 但仍取窄 matcher；且腳本內**刻意沒有 `os.name` 閘**——照抄
    # `block_bash_on_windows.py` 的平台閘等於「在事故現場（macOS）把它關掉」。
```

### R80 exec form 與載具存在性回歸鎖的立案

原處：`tools/tests/test_check_hooks_liveness.py` L2073-2084（12 行，註解區塊）

```text
# ══════════════════════════════════════════════════════════════════════════
# R80：hook 條目形態（exec form）與載具存在性的回歸鎖
# ══════════════════════════════════════════════════════════════════════════
# 病：Windows 上 shell form 的 hook 經 Git Bash 的 `bash.exe -c` 起，而 `bash.exe`
# 是 console 子系統程式 ⇒ **每觸發一次 hook 就閃一個 console 視窗**（實測：一個量測
# 視窗內 39 支 bash.exe、其中 22 支自帶 conhost＝22 次閃窗）。exec form（條目帶
# `args`）不經 shell、直接 spawn，指到 GUI 子系統的 `pythonw.exe` 即零視窗。
#
# 🔴 這道鎖真正在防的**不是**「有人把形態改回去」，是**修好與全毀的表徵相同**：
# exec form 的載具解析不到時 CC 只記一行 ERROR、工具照跑（**fail-open**），螢幕上
# 看起來就是「終於不閃窗了」。所以本節每一條判準的方向都是「少一半也要有人喊」，
# 而不是「壞了會紅」。
```

### _same_path 為何不能比字面（R83 真 Mac 首跑）

原處：`tools/tests/test_check_hooks_liveness.py` L2090-2130（41 行，docstring 說明段）

```text

    🔴 **為什麼不能比字面**（R83 於真 Mac 首跑抓到，判準本身是跨平台缺陷）：
    「我把 cwd 設成 X」與「子行程回報 cwd 是 X」之間隔著一層核心正規化，**兩個平台
    各有一種讓字面不等、語意相同的機制**，而且兩種都出現在測試最常用的暫存目錄上：

      · **macOS**：`/var` 是 `/private/var` 的 symlink。`tempfile.mkdtemp()` 回
        `/var/folders/.../T/xxx`（未解析），而 POSIX `getcwd(3)` 依規格回**已解析**
        的絕對路徑 ⇒ 子行程必然回 `/private/var/folders/.../T/xxx`。實測本機
        `os.path.samefile()` 為 True、字串比較為 False。
      · **Windows**：`%TEMP%` 在多數機器上是 `C:\\Users\\<user>\\AppData\\Local\\Temp`，
        使用者名稱超過 8 字元時 API 之間會混用 8.3 短檔名（`RUNNE~1`）；再加上
        NTFS 大小寫不敏感（`C:\\` vs `c:\\`）與 GitHub runner 的目錄 junction，
        同樣是「語意相同、字面不等」。

    ⇒ 本判準要問的事情從頭到尾都是**「是不是同一個目錄」**，那件事的平台中立量法
    只有一種：問檔案系統，不要問字串。`os.path.samefile()` 兩個平台都走
    `os.stat()` 的 `(st_dev, st_ino)`——POSIX 是 device+inode；**Windows 上 CPython
    的 `os.stat()` 走 `GetFileInformationByHandle`**，`st_ino` 是檔案索引、`st_dev`
    是磁碟區序號，兩者都是**開檔後由核心回報的實體身分**，所以 8.3 短檔名／大小寫／
    junction 三種變形全部自動被吃掉，不需要為 Windows 另寫一欄。

    🔴 **刻意不用 `Path.resolve()` 當正規化**：它在 Windows 上是「字串正規化 + 查詢」
    的混合體，行為隨版本與路徑是否存在而變（不存在的路徑會 fallback 成純字串處理）；
    而 `samefile` 的語意只有一種、且在路徑不存在時是**明確失敗**而不是悄悄退化——
    後者正是本 repo 反覆判過的「判準悄悄變成恆綠」形態。

    OSError（任一側不存在／權限不足）一律回 `False`＝**fail-closed**：測試寧可紅在
    「兩個路徑對不起來」，也不要因為量測失敗而放行。

    🔴 **`samefile` 唯一會 fail-OPEN 的那個縫，以及誰在守它**（獨立複驗 R83 補記）：
    上面「比 inode」的前提是**檔案系統真的給得出檔案 ID**。MSDN 對
    `BY_HANDLE_FILE_INFORMATION` 逐字載明「不支援 file ID 的檔案系統一律回 0」——
    FAT／部分 SMB 網路磁碟即屬此類 ⇒ 那種機器上 `st_ino` 兩邊同為 0、`st_dev` 又是
    同一個磁碟區序號，`samefile` 會把**兩個不同的檔案判成同一個**。方向是放行，
    不是誤擋，所以它不會自己叫出來（本輪只有 darwin，這一段是 MSDN 文件語意，
    **不是實測值**）。
    ⇒ 守它的是 `TestSamePathIsNotVacuous.test_two_different_directories_are_not_the_same`：
    那一格在**本機真正的暫存檔案系統**上建兩個貨真價實不同的目錄再問一次，
    檔案 ID 退化時它就地轉紅。**所以那一格不是可有可無的形式主義，刪掉它等於把
    Windows 側唯一的 fail-open 偵測器一起刪掉**（本 repo 反覆踩的「鎖還在、但沒人
    知道它在守什麼，於是下一輪被當成廢話刪掉」）。
```

### _make_directory_link 為何分平台（junction vs symlink）

原處：`tools/tests/test_check_hooks_liveness.py` L2345-2364（20 行，docstring 說明段）

```text

    🔴 **為什麼要分平台，而不是兩邊都 `os.symlink`**（鐵律三「這在另一個平台是什麼
    值？」）：`os.symlink` 在 Windows 上**存在**（不是 `AttributeError`），但底層的
    `CreateSymbolicLinkW` 需要開發者模式或 `SeCreateSymbolicLinkPrivilege`，一般
    Windows 機器與未開啟開發者模式的 runner 上必回 `OSError`（WinError 1314）。
    ⇒ 只寫 `os.symlink` 的話，Windows 側的結果**恆為 skip**——而 skip 不是覆蓋，
    它只是把「這台機器從來沒驗過」寫得比較好看（`DEF-101-343~345` 的形態：連續
    5+ 輪全 APPROVE、卻一次都沒在原生 Windows 上跑過）。

    Windows 上**不需要任何權限**、且語意等價的機制是**目錄 junction**：`_same_path`
    的 docstring 逐字點名「GitHub runner 的目錄 junction」是讓字面比較失效的三種
    Windows 變形之一 ⇒ junction 正是這一格要涵蓋的真實情境，不是為了繞過權限硬找的
    替代品。junction 沒有 `os` 公開 API（`_winapi.CreateJunction` 是私有的），標準
    建法是 cmd 內建的 `mklink /J`。

    🔴 **誠實劃界**：Windows 那一支在本輪的開發機（darwin）上**只驗到分派**（見
    `test_the_windows_branch_uses_a_junction_not_a_symlink`）；`mklink /J` 的實際 rc、
    以及 `samefile(junction, target)` 是否為 True，**未在原生 Windows 上實測**
    （junction 是 reparse point，開檔預設會跟隨 ⇒ `GetFileInformationByHandle` 應回
    目標的檔案索引，這是文件語意推論，不是量測值）。
```

### TestDeclaredWindowsCarrierExists 立案與 R80 ARCH-01 訂正

原處：`tools/tests/test_check_hooks_liveness.py` L2581-2611（31 行，docstring 說明段）

```text

    為什麼這個缺口比閃窗嚴重：載具解析不到 ⇒ 六支守衛**全部靜默失效**，而螢幕上的
    表徵就是「終於不閃窗了」。把缺口寫下來卻不給判準，等於把它登記成「已知且已接受」。

    判準的形狀是**宣告 ↔ 實況雙向綁定**（不是硬編一個路徑）：settings.json 宣告了
    venv 載具 ⇒ 那個路徑必須存在。這樣「有人把載具改成別的東西」也會被同一條守到。

    🔴 為何不用 `skipUnless`／不用「偵測到 CI 就跳過」：
      · 判準本體 `carrier_liveness_problems()` 自帶 `on_windows` 參數，兩個平台方向
        都在**同一台機器上**以注入驗到（`DEF-101-766`：單平台判準不可無條件外推）；
        用 `skipUnless` 反而會讓另一個方向永遠沒人跑過。
      · 非 Windows 不看 venv 載具是**語意上的**理由：`.venv/Scripts/pythonw.exe` 在
        mac/Linux 本來就不存在，那條在該平台是設計上的 fail-open，不是缺陷。
        （該平台自己那條載具另有 `TestPosixCarrierLiveness`。）
      · CI 的豁免同樣是語意的、且不由本測試負責：hook 只在「Claude Code 會跑的地方」
        有意義，CI 從不跑 hook——所以會出聲的那一層落在
        `tools/check_hooks_liveness.py`（開發機的閘門會跑、CI 由呼叫端整段跳過），
        本測試只負責證明那個判準有牙。

    🔴 **R80 ARCH-01：本類刻意不再有「這台機器上載具在不在」那一格**。原本那一格是
    `assertEqual(carrier_liveness_problems(real, repo_root), [])`，它量的是**機器狀態**
    而不是 repo 內容，於是在兩種完全正常的情境下必紅：
      · windows-compat-ci／windows-smoke：`python tools/run_root_unittests.py` 跑在
        `./tools/bootstrap.ps1` **之前**，那時 `.venv` 還不存在；而且該 workflow 稍後
        會把 `.venv` 更名為 `.venv-cache-windows`——所以「把測試挪到 bootstrap 之後」
        只是換一種方式再紅一次，不是修法。
      · 任何**尚未跑過 bootstrap 的全新 clone**（含開發者第一次 clone 後直接跑根層
        unittest）。複驗實測：project_dir 指向無 `.venv` 的暫存目錄 → problems len = 1。
    機器狀態的正確通報者是 `tools/check_hooks_liveness.py`（advisory：印警告、不阻擋，
    四個呼叫端在 `$CI` 有值時整段跳過）。判準本體**一個字都沒有放寬**——牙由下面三格
    注入自證；換上來的是一件機器無關、而且原本沒有任何人在守的事（見下一格）。
```

### TestPosixCarrierLiveness 立案（與 Windows 側不對稱）

原處：`tools/tests/test_check_hooks_liveness.py` L2687-2696（10 行，docstring 說明段）

```text

    🔴 立案理由（缺口與 Windows 側**不對稱**，所以不是「順手補對稱」）：Windows 條目
    釘死一個確定的檔案，POSIX 條目吃的是 **`PATH` 上任意一個 `python3`**——macOS 內建
    那支常年是 3.9，而本 repo 的 bootstrap 門檻是 3.11。此前 `carrier_liveness_problems()`
    在非 Windows **一律回空**，等於把「這個平台沒有 Windows 載具」寫成「這個平台沒有
    載具問題」。三種失效（檔不在／沒有執行位元／直譯器太舊）表徵完全相同：CC 只記一行
    ERROR 就放行，六支守衛一起消失，螢幕上就是「終於不閃窗了」。

    四格全部以注入驅動、`on_windows=False` 強制走 POSIX 分支——判準的方向不該取決於
    這台機器剛好是什麼（同本檔 `TestBlockBashHookDoesNotHurtOtherPlatforms` 的理由）。
```

### TestExecFormConversionScope 史實與 R84 訂正

原處：`tools/tests/test_check_hooks_liveness.py` L2752-2766（15 行，docstring 說明段）

```text

    🔴 立案理由（史實）：R80 只轉了**根層**那一份，根 `CLAUDE.md`〈鐵律一之二〉一度寫成
    通則。兩個後果：①AutoClaude 子專案 session 下閃窗一次都沒少；②「那 6 條退回 shell
    form」永遠不會轉紅。處置＝把「還沒轉的有幾條」變成**可查的量測值**：掃描面現查磁碟，
    判準是相等——多了＝退步、少了＝轉好了卻沒回來改表。凍結版（Copy-on-Evolve）具名排除。
    R81 已把 AutoClaude 那份轉完（普查表兩格皆 0）⇒ 本類職責由「登記還沒轉的」變成
    「不准有人退回去」。

    🔴 R84 訂正上一段那個「兩格皆 0」——**它是假的安心**（訴求 7「session 結束仍有彈跳
    視窗」窮舉出來的第一名）：`FROZEN_SETTINGS_PREFIX` 把 `AISDLC_SDD/AISDLC_SDD_v*` 這
    **30 份**全部結構性排除在掃描面之外，而其中一份是 **LATEST**——真的會被 Claude Code
    載入的活躍檔（框架 skills 掛在版本目錄下，以它為 cwd 開 session 是常態）。實測那 30
    份**全數仍是 shell form** ⇒ 對那種 session，R80／R81 的修法一次都沒生效，而普查表
    照樣兩格全綠。處置分兩半：LATEST 進掃描面（以**版本中性鍵**登記，不把版號寫成常數）、
    凍結歷史面登記成 shrink-only 的已知豁免（`TestFrozenShellFormIsAShrinkOnlyExemption`）。
```

### _certified_carrier_names R84／SD-05 沿革

原處：`tools/tests/test_check_hooks_liveness.py` L3194-3207（14 行，docstring 說明段）

```text

    🔴 R84／SD-05：舊判準是 `_GUI_CARRIER_SYMBOL in text` ——那是**整檔通行證**，只要
    檔案裡任何地方（連註解）出現過 `quiet_python` 這七個字，該檔所有內插載具一律放行。
    實測注入：只在**註解**提到它 ＋ 一個內插出 `powershell.exe` 的 Action ⇒ **0 筆命中**，
    而 `windowless_action_problems` 自己的 docstring 分支③ 逐字寫著「白名單不得變成
    萬用通行證」⇒ 宣稱射程 ≠ 實作射程。這比沒有鎖更難看見：檔案在、判準在、測試全綠。

    `.py` 走 AST：註解結構上不可能出現在 `ast.Assign.value` 裡 ⇒「註解不得認證」是
    **性質**，不是靠剝註解的正則去逼近（`_decommented` 對 `.py` 只剝整行註解，行尾註解
    照樣留著，用它會把同一個洞縮小而不是關掉）。`.ps1` 沒有現成 parser，退回「剝過註解
    的行首賦值」比對。
    誠實劃界：只追**一層**賦值——`x = _q(guard.quiet_python())` 認得，
    `a = quiet_python(); x = a` 不認得（會判紅）。今日全庫唯一的內插站點是前者；
    追賦值鏈要的是資料流分析，射程遠大於本輪，且假紅方向是安全的那一邊。
```

## test_context_budget_guard.py

### 沙箱要清哪幾個旗標（R81／R91／R96）

原處：`tools/tests/test_context_budget_guard.py` L217-226（10 行，註解區塊）

```text
    # 🔴 R81：額度那兩個旗標也要清。少清它們時，開發者自己機器上設過 `AUTOSDD_QUOTA_
    # GUARD_OFF=1` 就會讓下面所有 quota e2e **靜默轉綠**（守衛整支被關掉，rc 一律 0），
    # 而在 CI 上又是紅的——「污染的方向正好是看起來通過」同一條紀律。
    # 🔴 R91 補 `AUTOSDD_CONTEXT_SIGNAL_OFF`：它關掉的正是本輪新增的那條 stdout 通道 ⇒
    # 開發者機器上設過就會讓每一條「訊息必須送進模型」的 e2e **靜默轉綠**，方向同上。
    # 🔴 R96／B-4 尾項補 `AUTOSDD_TRACE_DIR`：開發者機器上設過它，`endurance_env.trace_dir()`
    # 就會把痕跡（含 `quota_gate.burn_ledger_path()` 的落款）整個寫到**沙箱之外** ⇒ 下面
    # `PlannerCliTest` 那道「`--check` 不寫檔」的全樹相等判準會**靜默轉綠**（方向同上面那
    # 兩條旗標：污染的方向正好是看起來通過）。pop 掉之後它落回 `HOME/.autosdd/traces`，
    # 而 `HOME` 已經在沙箱裡 ⇒ 真的寫了痕跡就會被看見。
```

### test_every_home_shaped_env_key_points_inside_the_sandbox SD 二審注射實測

原處：`tools/tests/test_context_budget_guard.py` L564-573（10 行，docstring 說明段）

```text

        SD 二審注射實測：把 `_isolated_env()` 的 `APPDATA`／`LOCALAPPDATA` 兩行還原成
        「原封繼承開發者的真家目錄」⇒ **GREEN**；`tools/tests` 全樹對這幾個鍵零斷言，也就是
        那兩行可以被無聲刪掉而沒有任何東西轉紅。而它們正是「走 `%APPDATA%` 的第三方
        （PowerShell 模組快取／.NET／pip）寫進**真的**那一棵樹」這件事的唯一擋板：副作用既
        污染開發者機器，又完全落在任何斷言的射程之外（沙箱目錄裡看不到 ⇒ 「沒有副作用」
        是假的）。形態與第一輪 D7 點名的「修法沒有具名回歸鎖」同構。
        XDG 那一族同理：開發者若顯式匯出過絕對路徑，它們**不隨 `HOME` 走**。
        判準是「每一個家目錄形狀的鍵都必須落在沙箱底下」而不是逐鍵比對字面值——後者會在
        沙箱佈局微調時假紅，前者只在「某個鍵指回真家目錄」時才紅，正是要守的那一件事。
```

### _tick 的 DEF-200-239 沿革

原處：`tools/tests/test_context_budget_guard.py` L2028-2038（11 行，docstring 說明段）

```text

        🔴 DEF-200-239：`register_endurance`／`_schtasks_remove` 是 planner 層級的假貨，
        但 `patrol_housekeeping()` → `_heal_armed_drift()` 摸到的 `schedule_backend.
        select()` 此前完全沒被注入，落到**真的**後端（`list_jobs()`／條件式 `arm()`）
        ——`task` 預設字面 `"T-r95"` 從不符合 `AutoSDD_Sentinel_` 前綴查詢，真後端因此
        結構上永遠判定「這支工作不在」⇒ 每次呼叫都真的重新 `.arm()`，在 Windows 上
        真跑 `schtasks /create`，於真機種下自續排程工作（見 `_StatefulFakeSchedulerBackend`
        docstring）。`scheduler` 未提供時一律套用該惰性替身；需要控制排程器現查回什麼
        （如 `ArmedDriftSelfHealTest` 的漂移／非漂移情境）的呼叫端改走本參數注入自己的
        替身，不再對 `sb.select` 額外掛一層外部 patch（那會與本函式的內部 patch 疊加、
        誰蓋過誰取決於巢狀順序，改參數注入才是單一真相源）。
```

### test_the_same_source_does_not_shout_on_every_call R100 觀測面訂正

原處：`tools/tests/test_context_budget_guard.py` L7231-7240（10 行，docstring 說明段）

```text

        🔴 R100 訂正判準的**觀測面**（不是放寬）：從「後續呼叫零 stderr」換成「後續呼叫
        零新增痕跡」。兩個理由：
          1. `degraded_cap` 依 PRD §4.1.5 收到 2 之後，第 3、4 次扇出會**合法地**被節流
             而說出**節流**訊息——那是另一個發言者（同檔
             `test_the_throttle_message_is_not_the_degraded_message` 就是在守兩者要分得
             開）。拿 stderr 當判準會把它誤讀成閂鎖壞掉。
          2. 兩個發言者的字面**互相包含**（節流訊息裡也有「額度量不到（reason=…）」）
             ⇒ 用措辭去分辨它們本來就不可靠。痕跡才是 `note_degraded()` 專屬的觀測面
             （節流那條路實測 `trace == []`，見上一支控制組）。
```

### test_a_good_reading_carries_ok_and_the_narrow_measure_is_unchanged R82／R96 訂正

原處：`tools/tests/test_context_budget_guard.py` L7366-7376（11 行，docstring 說明段）

```text

        🔴 R82：讀數形狀由頂層 `pct` 純量換成 `axes[]`，斷言跟著換到**每一軸自帶**
        `resets_at` 那一層——那正是該輪的缺陷本體（舊形狀在投影時把它丟掉）。
        🔴 R82：最後那一行驗的是**窄介面**（`measure()` 只吃 timeout、仍回 dict／None，
        新參數沒有改掉它）。替身必須掛在 `measure()` **真正的取數點**上，否則判準會退化成
        「這台機器現在登入了沒有」，而判準不得依賴一台機器的登入狀態（憑證來源本身的覆蓋
        在上面的雙欄矩陣，不在這一行）。
        🔴 R96 訂正：替身原掛 `access_token`，而 R82 把平台分支併回 `token_detail()` 後它
        已不在 `measure()` 的鏈上 ⇒ 自 R82 起一次都沒生效（mac 靠主機真實 Keychain 憑證假綠、
        Windows 真紅）。鏈路、成因與實測見
        `CrossPlatform_R96_Closure_Evidence.md` §2①。
```

### R96／B-3 兩個出口必須說同一句話的立案

原處：`tools/tests/test_context_budget_guard.py` L9214-9224（11 行，註解區塊）

```text
# ═══════════════════════════════════════════════════════════════════════════
# 🔴 R96／B-3：兩個出口（派工**前**查的 `--pace`、被擋**當下**的節流訊息）必須說同一句話
# ═══════════════════════════════════════════════════════════════════════════
# 立案（QA 當回合實測）：本組落地之前，`tools/tests/` 全樹 grep `本視窗已用` **零命中**
# ⇒ 把那兩行 revert 回去沒有任何一支測試會紅（唯一觸及 Workflow 分支的
# `test_the_throttle_message_qualifies_every_percentage` 只斷言「每個百分比都帶 kind 與
# 分鐘」，`live` 印不印完全不判）。同一份實測還量到：`recommended_fanout` 22 處全在
# `test_quota_policy.py`、`live_dispatches` 8 處全在本檔 ⇒ **兩組永不相遇**，於是
# 「cap 側說可派 N 個」與「派發帳說已用 N 次」可以無限期互相矛盾而沒有東西轉紅。
# 本類的全部價值就是讓它們相遇：三條分別守渲染面、呼叫點、跨層一致性，缺一個就會留下
# 一種「改壞了照樣綠」的形態（下面每一條的 docstring 各自寫出它守的是哪一種）。
```

### test_an_empty_window_is_paced_by_the_recommendation_not_by_the_raw_cap 兩格設計

原處：`tools/tests/test_context_budget_guard.py` L9319-9333（15 行，docstring 說明段）

```text

        `pace_line()` 上方那一整段 WHY 逐字宣稱「畫面數字恆 ≤ 守衛真的會放行的量
        （`live_dispatches() >= cap` 即擋），也恆 ≤ 配速建議」，而 R96 落地當時**沒有任何
        測試在守這個公式**：SD 與 QA 各自獨立把它注射成純差值 `max(0, cap−live)`，四支新增
        鎖全部 GREEN。結構成因是 ③ 刻意構造 `live == cap`，而在那一格 `min(rec, cap−live)`
        與純差值同為 0 ⇒ 兩式在唯一被斷言的格子上重合；①②則一格都不碰 `--pace` 的數字。

        本條用**兩格**把三種實作分開，缺一格就會漏掉一種：
          · `live=0`（視窗還空著）⇒ 必須印 `rec`。純差值在這裡印 `cap`＝**放大**（實測
            cap=8／rec=4 時放大 2 倍），而放大是這一族唯一不准無證據發生的方向。
          · `live = cap − (rec − 1)`（視窗吃掉一部分、剩餘刻意壓到 `rec` 以下）⇒ 必須印
            `rec − 1`。`rec` 純量在這裡印 `rec`＝報一個守衛當場就會擋下的數字（B-2 立案的
            那個病）。
        兩道前提斷言（`cap > rec >= 2`、且 `rec != rec − 1`）是刻意的：階梯常數哪天一改讓
        `cap == rec`，三式在兩格上就會全部重合而本條靜默失去鑑別力。
```

### DEF-200-169 滾動視窗剩餘秒數的立案

原處：`tools/tests/test_context_budget_guard.py` L9364-9374（11 行，註解區塊）

```text
# ═══════════════════════════════════════════════════════════════════════════
# 🔴 `DEF-200-169`：滾動視窗**還剩幾秒**——`--pace` 上此前既無實作也無任何觀測者
# ═══════════════════════════════════════════════════════════════════════════
# 立案（帳本列逐字）：`DEF-200-156` 修前診斷寫的是「沒有印 `live`、**也沒印視窗剩餘
# 秒數**」，而那一輪只補了 `live`。畫面上唯一與時間有關的那一行是
# `throttle_horizon_line()`，它報的是**額度軸的 reset 期程**（五小時／七天尺度），不是
# `FANOUT_WINDOW_SECONDS`＝300 這個滾動視窗還剩幾秒 ⇒ 被擋下的人看得到「幾小時後
# reset」，卻看不到「再等 137 秒就能多派一個」，只能猜。
# 兩個量差三個數量級，而 `tools/tests/` 全樹在本組落地前 grep `扇出視窗` **零命中**
# ⇒ 把這一行整段拿掉不會有任何東西轉紅。本類的四個面（推算／注入時鐘／兩個邊界／
# 接電）各守一種「改壞了照樣綠」的形態。
```

## test_dev_start.py

### mac nightly 判準為何長在 test_dev_start.py／退化 plist 來源

原處：`tools/tests/test_dev_start.py` L3649-3661（13 行，註解區塊）

```text
# 為何長在 test_dev_start.py 而不是自成一支 test_install_mac_nightly.py：
# `DEF-101-561③`／`DEF-101-565` 已裁定「R61 開輪起 tools/tests 禁止新增鎖檔、只准
# 合併／刪除」，並由 test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet 機械強制
# （當時的實測：新開一支檔案即翻紅）。
# 🔴 R78 ARCH-03 訂正：那道棘輪 R77 起改量逐檔行數的**淨額**、也不再比 HEAD——
# 新增檔案本身不違規，淨行數上升才違規。本節併入本檔的理由與量測面無關，仍然成立。
# 本檔本來就是 install_mac_nightly.sh 三道跨站鎖的所在地（`test_installer_third_
# site_filename_and_threshold`／`TestCrossSiteLiteralLocks`／上方的行為等價鎖），
# 新判準擴充進來與既有同源鎖相鄰，正是該裁定指定的「合法作法」。
#
# 退化 plist：逐字重現「R15 之前安裝、且 repo 已搬過家」的機器實況——無 RunAtLoad、
# ProgramArguments 指向不存在的舊 checkout、StandardOutPath 導 /tmp（R14 ARCH-GAP-3
# 遷出前的落點，會被 macOS 週期清理）。三個缺陷都真實發生過，非杜撰。
```

### pmset stub 這道縫的 R82 立案

原處：`tools/tests/test_dev_start.py` L3742-3754（13 行，註解區塊）

```text
        # stub pmset：與 launchctl stub 同理由、同預設姿態（預設回報「健康」，讓
        # 其餘維度的訊號不被機器狀態掩蓋）。
        #
        # 🔴 R82 這道縫為何非有不可：WakeToRun／NextRunTime 兩列的輸入是**這台機器的
        # 電源排程狀態**（`pmset -g sched`），不是 plist 檔案內容。沒有這道縫，
        # `install_healthy_plist()` 就只定義了「健康」的一半，而
        # `test_healthy_plist_passes_every_capability_row` 那句「每列皆 ✅」實際上
        # 隱含要求「跑測試這台 Mac 剛好排過 pmset repeat」——那需要 sudo、安裝器
        # 刻意不代跑，是多數 Mac 的**非**常態 ⇒ 該鎖在真 mac 上結構性必紅。
        # 實證：本輪之前這兩支測試從未在真 mac 上跑綠過（R82 及更早都在 Windows
        # 完成，整組被 class 上的 @skipUnless(darwin) 跳掉），紅是第一次真的跑才浮出來的。
        # 縫換掉的是**量測面的來源**，不是覆蓋：兩列仍在「每列皆 ✅」的斷言裡，
        # 而且下面另有一組把它們打成 ⚠️ 的紅控制組，證明這裡不是橡皮圖章。
```

### test_status_prints_exactly_the_rows_static_extraction_predicts 三項對帳

原處：`tools/tests/test_dev_start.py` L3951-3961（11 行，docstring 說明段）

```text

        跨平台對稱斷言（mac 列數 ≥ Windows 列數）住
        `test_schedule_capability_parity.py`（兩側只讀原始碼、不需要 Darwin）。
        留在這裡的是**只有 macOS 才做得到的那一半**，且刻意做成對帳而非重複斷言：
        真跑一次 `--status`，驗 ① 能力表整段印得出來、② 每一列 `(expected …)` 都是
        ✅（健康 plist 不該有任何告警）、③ **執行期列數逐一等於**靜態抽取器對同一支
        安裝器的預測。③ 才是關鍵——靜態抽取器是那道跨平台鎖的量測面，而量測面本身
        必須被驗證（若它多算/少算，跨平台鎖會在 mac 以外的所有平台默默失準，
        而沒有任何人有辦法發現）。② 同樣吃 plist 內容與 pmset 排程兩個自變數，
        夾具的 stub 已把後者收進測試手裡；③ 不受影響（它比的是列**數**）。
        搬遷前的原文＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
```

### test_a_one_shot_wake_event_does_not_count_as_the_daily_repeat 射程與未守的一半

原處：`tools/tests/test_dev_start.py` L4043-4059（17 行，docstring 說明段）

```text

        macOS 自己就常年掛著 user-invisible 的一次性 wake（本機
        `plutil -p /Library/Preferences/SystemConfiguration/com.apple.AutoWake.plist`
        實查到 calaccessd／osanalytics 兩則）。修前的判準對 `pmset -g sched` **全文**
        做子字串比對 ⇒ 只要輸出裡出現那個字樣就算數，不分區段。一次性事件跑完就沒了，
        撐不起「每天 02:00 前把機器叫醒」這個語意；把它算成已排定，等於在唯一的每日
        回饋通道上宣告一個不存在的保護。

        🔴 本鎖的鑑別力射程（**複審實測訂正**，不是推論）：本測試此前自陳的鑑別力宣稱
        經複審實測證偽，本支保留的價值是情境覆蓋而非形態鑑別力（原文＝Guard_Repin
        證據檔 §D-17）；真正吃得下全文比對假綠的輸入已補成獨立一支
        （`test_a_one_shot_wakeorpoweron_is_not_mistaken_for_the_daily_repeat`）。

        🔴 仍然沒有測試在守的那一半（不變）：合成注入「只拿掉安裝器的區段錨定、保留
        tolower($1) 欄位判準」→ 全綠。因為一次性段的 $1 結構上恆為 `[N]`
        （樣板 ` [%ld]  %s at %s`），欄位判準單獨就排除了它。區段錨定是縱深防禦、
        目前無鎖——寫在這裡是因為「以為有鎖在守」比「知道沒有」更貴。
```

### test_a_one_shot_wakeorpoweron_is_not_mistaken_for_the_daily_repeat 為何要獨立一支

原處：`tools/tests/test_dev_start.py` L4072-4084（13 行，docstring 說明段）

```text

        為何非要獨立一支（上一支不是已經測過一次性事件了嗎）：上一支的 eventtype 是
        `wake`，**不是**詞彙表任何一項的子字串 ⇒ 連最爛的全文比對都不會在它身上出錯，
        它證不了任何形態上的鑑別力（複審實測：忠實還原全文比對 → 24 tests OK）。
        本支的輸入才會讓全文比對回報「已排定」，也就是修前那個判準真正的破口。

        情境是真的會發生的：`pmset schedule`（一次性）與 `pmset repeat`（重複）只差一個
        動詞，打錯就落在這一格。一次性事件跑完就沒了，撐不起「每天 02:00 前把機器叫醒」；
        把它算成已排定，等於在唯一的每日回饋通道上宣告一個不存在的保護——而使用者會
        因為看到 ✅ 而**停止**去做那件他其實還沒做的事。

        輸入不是編的（見 `PMSET_ONESHOT_WAKEORPOWERON` 上方的反組譯證據鏈）：一次性段
        會把 eventtype `wakepoweron` 代換成字面值 `wakeorpoweron` 再印，重複段則直印原值。
```

### test_the_installer_does_not_pin_a_prose_marker_that_pmset_never_prints

原處：`tools/tests/test_dev_start.py` L4109-4117（9 行，docstring 說明段）

```text
        本斷言與那幾支行為測試不是重複——行為測試用的是 stub 的輸出，
        stub 可以被改成配合任何字面值；這一支直接讀原始碼，釘的是
        「判準不得押一個 OS 不會產出的字串」這件事本身。

        🔴 判斷面刻意**剝掉註解行**（同 test_mac_readiness_r82.pmset_capability_rows
        的既有慣例）：訂正紀錄本來就得逐字寫出被撤回的那個字面值，否則下一位讀者
        無從知道當初錯在哪、也就會再錯一次。本判準要禁的是「拿它當判準／印給使用者
        去找」，不是「提到它」。第一版沒剝，於是它把本檔自己的訂正註解判成違規——
        那種鎖的下場是被人把註解刪掉來滿足它，等於用刪除歷史換綠燈。
```

### R71 假直譯器依 os.name 分派的立案

原處：`tools/tests/test_dev_start.py` L5534-5548（15 行，註解區塊）

```text
# ── R71（DEF-101-755 解鎖）：PowerShell 行為鎖用的假直譯器，依 `os.name` 分派 ──
#
# 為何 `os.name` 而不是 `sys.platform`：要分的是**行程建立語意**——POSIX 的 `execve`
# 認 shebang，Windows 的 `CreateProcess` 只認 PE 映像＋PATHEXT 副檔名。判例＝
# `tools/tests/test_bash_probe_spec_contract.py::_STUB_FORMS`（DEF-101-754）。
#
# 為何 Windows 的 3.9 冒充者拆成「`.cmd` ＋ 旁邊一支 `.py`」而不是把 spoof 程式塞進
# `.cmd` 一行：`.cmd` 內若再寫一層 `-c "<python 程式碼>"`，cmd.exe 的跳脫規則會疊在
# PowerShell 重組命令列的規則上——而本類要驗的正是「引數原封不動送到直譯器」
# （DEF-101-760），載具自己絕不能引入第二層引號變因。`%*` 只是把 PowerShell 交來的
# 參數原樣轉手，不新增任何一層。
#
# 內文全 ASCII（WHY 一律寫在本 Python 檔）：`.cmd` 由 cmd.exe 以 OEM code page 解讀，
# 本機為 CP950，寫中文註解等於自找亂碼。換行 CRLF：cmd.exe 對純 LF 批次檔的行為在
# 部分構造下未定義。兩項皆同 DEF-101-754 判例。
```

### _sub_min_interpreter_candidates 三種發現路徑

原處：`tools/tests/test_dev_start.py` L5734-5745（12 行，docstring 說明段）

```text

    🔴 R81 包 F（S3-06）：原本只有一串 PATH 名稱，而那串在 Windows 上結構上找不到
    任何可用的東西（pyenv-win shim 本機實測細節，原文＝Guard_Repin 證據檔 §D-13）。

    三種發現路徑並存，缺一都會在某類機器上失明：
      · `/usr/bin/python3`：macOS 主場（3.9.x），POSIX 上第一順位就命中。
      · pyenv：win 佈局 `<root>/versions/<ver>/python.exe` 與 posix 佈局
        `<root>/versions/<ver>/bin/python3` 兩種都掃，不存在的那一種自然掃不到東西
        （鐵律三：判準不得只在一個平台成立）。
      · Windows Python Launcher `py -3.X`：本機今天 `Get-Command py` 為空，所以它
        **不能**是唯一依靠，但別的 Windows 機器上常常只有它。
      · PATH 上的 `python3.X` 名稱：保留原行為（它在 CI 的 Linux 映像上就是主場）。
```

### DEF-101-766 非 Windows 平台短路的立案與被否決作法

原處：`tools/tests/test_dev_start.py` L6223-6248（26 行，註解區塊）

```text
# ================================================ 非 Windows 平台短路（DEF-101-766）
# 缺陷本體：PATHEXT 過濾在非 Windows 上讓 Get-PythonGeMin 恆回 $null（與 DEF-101-759
# 同病換平台發作），原文＝Guard_Repin 證據檔 §D-11。
#
# 🔴 為何用「參數化 harness」而不是真的起一支 PS Core：缺陷只在
# 「`$PSVersionTable.PSVersion.Major >= 6` 且 `$IsWindows` 為假」時顯形，而在 Windows
# 上**任何**引擎都讓 `$IsWindows` 為真（它是唯讀常數），故那個組合在此平台結構性
# 不可達——引擎裝了什麼一律現查 `tools/tests/_ps_engine.py::available_engines()`，
# 不寫進本檔（R74：原句把量測當時的機器屬性寫成了常數，DEF-101-777 同型）。
# 替身變數這條路本包**實測走不通**：`$PSVersionTable` 在
# PS 5.1 是 read-only，`$PSVersionTable = …`／`$local:PSVersionTable = …`／
# `New-Variable -Force` 三種寫法皆回 `Cannot overwrite variable PSVersionTable because
# it is read-only or constant.`，連子作用域都蓋不掉（函式內看到的仍是 Major=5）。
# 故改為把**生產函式原始碼原封搬進 harness**，只把那一個蓋不掉的運算式換成可設定的
# `$FakePsMajor`（替換恰 1 處，數目不對即 fail-loud）。`$IsWindows` 不必替換——它在
# PS 5.1 本來就是未定義變數，harness 直接賦值即可，模擬 5.1 時則刻意**不定義**它。
#
# 🔴 被否決的第三種做法（誠實記錄，免下一個人再走一遍；本包實測結果原文＝
# Guard_Repin 證據檔 §D-11）：「在 PS 5.1 下清空 `$env:PATHEXT` 跑生產函式、斷言
# 它不回 $null」**零鑑別力**。
#
# 兩道鎖分工（缺一即有缺口，且此處**不是**「行為＋字面」的例行搭配）：①行為鎖真的執行
# 函式本體，抓「短路不存在／不生效」；②順序鎖抓「短路存在但落在 PATHEXT 過濾之後」。
# ②不是①的字面備援：本包實測把短路整段**搬到 PATHEXT 迴圈之後**，①仍回
# `RESULT_NULL=False`（迴圈在 POSIX 上濾光後落空、短路照樣接住）＝①對這種改法全綠，
# 只有②看得見。反之刪掉整段短路時①當場紅（實測 `RESULT_NULL=True`）。
```

## test_install_windows_nightly.py

### 模組背景與靜態驗證的設計取捨

原處：`tools/tests/test_install_windows_nightly.py` L4-14（11 行，docstring 說明段）

```text
背景：mac 側 tools/install_mac_nightly.sh 提供一鍵 install/uninstall/status/
render-only 排程安裝器；Windows 側先前只有 AutoClaude/tools/fix_nightly_catchup.ps1
——假設 AutoClaude_Nightly 這個 schtasks 任務已存在，只能校正設定、不能從零建立。
本測試驗證新補上的 tools/install_windows_nightly.ps1 結構正確且與既有生態系（
fix_nightly_catchup.ps1 的補跑保護目標值、run_local_nightly.ps1 檔頭記載的排程慣例）
不漂移。

`Register-ScheduledTask`/`Get-ScheduledTask` 屬 Windows ScheduledTasks 模組，非
Windows 主機（含本專案開發常用的 macOS/Linux pwsh）無法真的執行——本測試刻意只做
靜態文字結構驗證（＋若本機有 powershell/pwsh 則額外做語法解析，純解析不執行，
跨平台安全），不嘗試真的呼叫排程 API。
```

### DEF-101-249 兩支腳本參數名極性相反的沿革

原處：`tools/tests/test_install_windows_nightly.py` L170-179（10 行，docstring 說明段）

```text
        DEF-101-249（R20 真 Windows 機器驗證）：`fix_nightly_catchup.ps1` 讀寫既有
        任務走「物件屬性賦值」（`$t.Settings.DisallowStartIfOnBatteries = $false`），
        物件屬性名就是 DisallowStartIfOnBatteries／StopIfGoingOnBatteries，那裡沒錯；
        但 `install_windows_nightly.ps1` 是用「建構」cmdlet
        `New-ScheduledTaskSettingsSet` 從零產生同一份設定，這個 cmdlet 的參數名
        極性相反、名稱也不同——`-AllowStartIfOnBatteries`／
        `-DontStopIfGoingOnBatteries`，原參數名在此 cmdlet 上根本不存在，真機呼叫
        會拋 ParameterBindingException（見同檔 TestInstallWindowsNightlySettingsConstruction
        的真機呼叫驗證）。此處只做語意對齊靜態檢查：目標值透過描述性註解與正確的
        cmdlet 參數名雙重確認一致，不斷言（也不可斷言）兩支腳本使用同一組參數字面。
```

### test_help_block_contains_no_hardcoded_clock_time 意圖

原處：`tools/tests/test_install_windows_nightly.py` L285-294（10 行，docstring 說明段）

```text
        意圖（Rule 9）：DEF-101-779 把觸發時刻從程式碼裡的寫死值改成參數，但 R73 首版
        **同時在 help 區塊寫下一組錯的預設值**（`② … 預設 23:30`，實際 param 是 21:30），
        且同段又寫「預設值＝本機現行實況」——與 param 區塊「刻意不把兩個預設都設成現況」
        直接互相打臉。方向仍是危險側：讀 help 的人以為不帶參數跑不會動 smoke，實際會被
        搬走。**「靜默改掉時間」這個陷阱沒被消滅，只是從程式碼搬進了說明文字**
        （Architect／SA／SD 三方二審獨立命中同一筆）。

        所以鎖的判準不是「說明要正確」（那無法機械判定），而是「說明裡**不准有時刻**」
        ——預設值只有 param 區塊一個權威源，現行排程只有 `Get-ScheduledTaskInfo` 一個
        權威源。只靠自律的話，這個形態已證實會在同一支檔、同一個 commit 內重生。
```

### test_status_exit_code_reflects_task_existence R60 DEF-101-542 訂正

原處：`tools/tests/test_install_windows_nightly.py` L345-352（8 行，docstring 說明段）

```text
        🔴 R60 DEF-101-542：本斷言原文要求 `$loaded = Show-NightlyStatus`，而該修法
        **在 PowerShell 上根本不成立**——函式內所有 `Write-Output` 都會併入回傳值，
        `$loaded` 實得 `Object[]`（報表字串 + 布林），`if ($loaded)` 對非空陣列恆為真
        ⇒ `-Status` 又變回「恆 exit 0」，DEF-101-248 的修復被語意打敗且**本測試看不到**
        （它只比對原始碼字面，從不執行）。修法：把「印報表」與「判定存在」拆成兩支
        函式（`Show-TaskDetail`／`Test-TaskPresent`，沿用 run_root_unittests.py
        `report_windows_native_skips`／`windows_native_skips` 的既有慣例），並由
        `TestStatusExitCodeRuntime` 以真的執行取代字面比對來守這條不變量。
```

### test_uninstall_branch_does_not_depend_on_carrier_script_existence 結構不變量與錨點修訂

原處：`tools/tests/test_install_windows_nightly.py` L400-412（13 行，docstring 說明段）

```text
        本測試鎖住結構層不變量：真正的 `-Uninstall` 處理區塊——以行首（無縮排）的
        `if ($Uninstall) {` 為起點錨點（真正區塊頂格書寫；`-Status` 區塊內那個只印
        警告、同名但不同語意的巢狀 `if ($Uninstall)` 有縮排，`^` + `re.MULTILINE`
        會跳過它），以其內含的 `foreach ($name in @($TaskName, $SmokeTaskName))`
        迴圈為終點錨點——本體不得包含任何 `Test-Path -LiteralPath $NightlyPs1` /
        `$SmokePs1` 呼叫，且兩個存在性檢查必須出現在該區塊**之後**（即收斂進
        install-only 段落）。

        錨點修訂記錄：原始版本起點無 `^`／`re.MULTILINE`，`re.search` 實際抓到的是
        `-Status` 區塊內那個縮排的巢狀 `if ($Uninstall)`（第一個出現的匹配），而非
        本文件宣稱排除的對象；因兩者在原始碼中相鄰、捕獲範圍恰好完整涵蓋真正區塊，
        對 DEF-101-619 這個特定回歸仍有鑑別力，但與文件描述的機制不符（Review round
        1 發現）。加 `^` 錨點後才是文件宣稱的行為。
```

### TestStatusExitCodeRuntime 為何要用執行而非字面比對

原處：`tools/tests/test_install_windows_nightly.py` L616-624（9 行，docstring 說明段）

```text
    WHY 一定要用執行而不能用字面比對：原本的靜態斷言（比對 `$loaded = Show-...`）
    在腳本行為完全壞掉（恆 exit 0）的情況下照樣全綠——R60 實測把 `$TaskName` 換成
    一個不存在的名字後跑 `-Status`，真實結束代碼是 **0**。「字面對了但語意反了」
    是 PowerShell 特有的陷阱（函式輸出串併入回傳值），只有跑起來才看得到。

    方法：把安裝器複製到 temp、把兩個任務名改寫成保證不存在的名字後執行——
    **不註冊、不移除任何排程任務**（純唯讀查詢；本 repo 紀律：真安裝屬使用者 ops，
    須另行核可）。`-Status` 區塊在腳本中位於載體存在性檢查之前，故複本雖然算出錯的
    $RepoRoot 也不影響本測試（R60 實測確認）。
```

### R75「部分缺席」這一格的缺陷實測

原處：`tools/tests/test_install_windows_nightly.py` L1072-1082（11 行，註解區塊）

```text
    # ──────────────────────────────────────────────────────────────────────
    # 🔴 R75（SD 複審 blocking）：「部分缺席」這一格此前沒有登記、沒有判準、沒有測試
    #
    # 缺陷實測（修復前，唯讀即可證）：一支存在且七項設定全符 ＋ 一支整支不存在
    #   → status=ok、drifts=[]、main() rc=0（全綠），
    #     而同一份人類可讀輸出照實印著「AutoClaude_WindowsSmoke: 不存在（未安裝）」。
    # 也就是**印得出來卻判它綠**：判準與被判準物錯配——偵測器要守的是「排程會不會漏
    # 跑」，而「任務不見了」是漏跑的最強形態（R71 真的從本機移除過一支 AutoClaude*
    # 任務），卻是它唯一看不到的形態。上方 test_absent_tasks_are_skip_not_drift 只覆蓋
    # **全**缺席，剛好把這一格繞過去。
    # ──────────────────────────────────────────────────────────────────────
```

### TestNamedExemptionRetiresWhenItsUnlockConditionHolds 缺陷本體與三個方向

原處：`tools/tests/test_install_windows_nightly.py` L1246-1265（20 行，docstring 說明段）

```text

    🔴 缺陷本體（DEF-101-794 的第二段）：R75 為排程漂移立了一條具名豁免（`status=drift`
    只印 WARN、不計 nightly 失敗），理由是修法卡在未執行的系統管理員提權。那條豁免**自己
    寫下了**可判定的解除條件——「偵測器回報 status=ok 之後，本項應移回 finalFailures」
    ——並且只安排了一個承接者：nightly log 裡一行給人看的 WARN。提權於 2026-08-05 執行、
    偵測器實測 `status=ok` / rc=0 之後，那行 WARN 每晚都在印，而豁免**照樣生效**。
    ⇒ 承接者是「人記得讀一行 WARN」的豁免，一律等於永久豁免。

    本鎖是那個教訓的一般化：**豁免的解除條件必須有東西在條件成立當天說話**。三個方向：
      ① 靜態（平台中立，三個平台都說話）：接線層已記載那次觀測 ⇒ 白名單不得再含 drift。
      ② 真機交叉核對：偵測器**現在**若也回 status=ok，同一結論必須成立。
      ③ 鑑別力（合成輸入）：把豁免加回去的白名單必須被本鎖判紅——否則①②都只是恆綠。

    🔴 為何本鎖**不用 `skipUnless` / `skipTest`**（誠實劃界，這是刻意的取捨）：
    ② 在非 Windows／未安裝受管排程的機器上量不出來，慣例作法是 `self.skipTest`。但
    `tools/lib/skip_tag_policy.py::_SITE_CLASS_CENSUS` 是**相等**棘輪，新增任何一個字面
    reason 的 skip 站點都必須同步重釘那張表，而該檔不在本包的檔案所有權內（跨界改動＝
    並行包互踩）。故 ② 改為「量不出來時退回①的靜態結論並把原因印到 stderr」——**兩條
    分支都真的斷言**，沒有任何一條是 `return` 靜默通過。代價誠實記在這裡：量不出來這件
    事不會出現在 unittest 的 skipped 統計裡，只會出現在 stderr。
```

### TestWindowsSmokeTaskHasWrittenExitCriteria 缺陷本體與三件事

原處：`tools/tests/test_install_windows_nightly.py` L1366-1375（10 行，docstring 說明段）

```text

    🔴 缺陷本體：該任務自 R60 建立起，全庫查不到任何一條退出判準——於是「這個測試
    測完了嗎、能不能結束」這個問題**在結構上無法回答**，使用者連問三輪都得不到答案。
    補償控制沒有退場條件，就會從「暫時的補償」腐化成「永久的儀式」。

    本鎖釘住三件事（都在 tools/windows_smoke_local.ps1 的檔頭）：
      ① 判準存在且分清「腳本（永久）」與「每日排程任務（有退場）」；
      ② 判準是可機械查的（點名 gh 查詢與既有的兩支檢查器），不是「覺得夠了就撤」；
      ③ **不得**以「連續 N 天零發現」當退場依據——R74 同輪雲端 windows-compat-ci
         抓到一筆本機十道閘門全綠的 P0，證明零發現只代表這一層看不到那一類缺陷。
```

## test_run_root_unittests.py

### UntaggedWindowsLikeSkipsTest WHY（低報 33% 的實測）

原處：`tools/tests/test_run_root_unittests.py` L279-290（12 行，docstring 說明段）

```text

    WHY（為何上面那組鎖不夠）：`ReportWindowsNativeSkipsTest` 全組都只驗「已經帶
    標籤的 skip 會被點名」——對「該帶而沒帶」結構性盲目，而那正是低報的來源。
    R67 動工實測：macOS 上 15 支 skip 全為 Windows 專屬，標題只印 10（低報 33%），
    其中 4 支是 R65（`01fd8c3`）、1 支是 R66（`8654975`）落地時漏標；R59 已在
    `tools/tests/test_install_windows_nightly.py:344-350` 逐字記過同一形態，兩輪後
    原地復發。掃描員動工前另做過反證：把一支帶滿 Windows 關鍵詞、**未標籤**的
    skip 附加進既有鎖檔，全套 1140 支測試**無一支轉紅**（rc=0）——前瞻鎖確實不存在。

    本組鎖的是那個新判準本身，含四個方向：命中要抓、標籤要放行、不相關的 skip
    不得誤殺、以及「在 Windows 上必須整組閉嘴」（否則 POSIX-only skip 的理由幾乎
    都會提到 Windows，會在真 Windows 機器上製造整片假紅）。
```

### StaticWindowsSkipTagScanTest WHY（三道閘門同一個瞎點）

原處：`tools/tests/test_run_root_unittests.py` L753-769（17 行，docstring 說明段）

```text

    WHY（為何上面那組 runtime 鎖不夠——而且不是它寫錯）：
    `untagged_windows_like_skips` 在 Windows 上整組早退（`if on_windows: return []`），
    上面 `test_on_windows_the_check_is_silent` 正是在**要求**它這麼做，理由也成立
    （Windows 上會 skip 的是 POSIX-only 測試，其 reason 幾乎必然提到 Windows，照掃
    必然假紅）。但代價是結構性的：三道 Windows 側閘門（本機 pytest／pre-push／
    windows-compat-ci）從此是**同一個瞎點的三份複本**——R71 在 Windows 落地的漏標，
    三處都看不見，只能等別的平台跑到才發現，而那正好是 R43 DEF-101-348 那條
    「Windows 專屬測試連續 5+ 輪全 APPROVE 卻從未在 Windows 跑過」的同款延遲。

    本組鎖的是那個補位判準：不看「現在跑在哪個平台」，改看 skip 條件的**方向**
    （`skipUnless(<Windows 述詞>)` vs `skipIf(<Windows 述詞>)`）。方向資訊寫在原始碼
    裡，三個平台讀到的是同一份，所以這道掃描在哪裡跑都會說話。

    落地前的鑑別力反證（Windows 11 實測）：不含方向判準的版本對同一棵樹報 **7 筆**
    假紅，全數是 `skipIf(os.name == "nt")` 的 POSIX-only 測試；加上方向判準後歸零。
    也就是說「方向」不是可有可無的精緻化，它是這道鎖能不能存在的前提。
```

### ProblemReportItemizationTest 修前實況

原處：`tools/tests/test_run_root_unittests.py` L1034-1048（15 行，docstring 說明段）

```text

    修前實況：`report_untagged_windows_skip_decorators` 的 `problems` 是**七個類別的
    總和**，總表頭印 `len(problems)`，而它後面的明細迴圈只涵蓋 `unregistered` 與
    `offenders` ⇒ 唯一的問題落在別的類別時，讀者看到「發現 1 個問題：」之後一片空白，
    於是去找一個根本不存在的第二筆。七類之中 `掃描面為空` 更是從頭到尾**沒有任何一段
    程式碼印它**，而既有的 `test_empty_scan_surface_is_fail_closed` 只讀回傳值、把
    stderr 丟進垃圾桶 ⇒ 結構上看不到這件事（一道鎖看得見缺陷的一半，就會讓人以為
    整件事有人在守）。

    本組鎖的是**不變量本身**，不是今天那一筆：
      ① 進到 buckets 的每一筆明細都必須逐字出現在輸出裡——**含未登記的類別**；
      ② 表頭數字必須等於印出來的明細行數（同一個來源，不得再各算一次而脫鉤）；
      ③ 生產端的類別鍵 ↔ `_PROBLEM_CATEGORY_WHY` 必須**雙向**相等 ⇒ 「新增一類卻忘了
         印」在寫出來的**當回合**就轉紅，不必等那一類真的觸發（`掃描面為空` 在真 repo
         上永遠不觸發，靠「等它發生」等於永遠不會發現）。
```

### test_the_returned_problems_are_derived_only_from_the_buckets 三形態與 R83 補款

原處：`tools/tests/test_run_root_unittests.py` L1137-1154（18 行，docstring 說明段）

```text

        `render_problem_report` 只保證「進到 buckets 的一定被印」；若有人另攢一份扁平
        清單再併進 return（修前正是那個形狀：`problems` 同時裝七類、印列面只走兩類），
        不變量①②當場失效而本檔其他測試都看不到。故判三件**形態**：
          ① 函式內沒有名為 `problems` 的累積器（修前那個名字，也是最可能的復發形）；
          ② 每一條非空 return 都必須取自 `buckets`——這一條才是通則，換個變數名也擋得住；
          ③ 非空 return 不得是**併接**（`A + B` 或多個 `*` 展開）。

        🔴 ③ 是獨立複審實測補上的（R83 驗證者注入 case G）：只判 ②「dump 裡出現
        `buckets`」時，`return [… for … in buckets …] + bypass` 這個形狀**照樣通過**
        ——`buckets` 確實出現了，旁路那一半卻沒有任何人印它。該注入當時是靠兩支**行為**
        鎖轉紅才被抓到，而那兩支只在旁路那一筆**恰好在本次觸發**時才有鑑別力（條件式的
        旁路仍會靜默溜過）⇒ 形態面必須自己封住。今天的實作既非併接也無 `*` 展開，故 ③
        是零成本；`return list(_flatten(buckets))` 這類正當重構仍然放行（不判「必須是
        某個特定形狀」，只判「buckets 之外還有第二個來源」這一件事）。

        🔴 刻意判 AST 而非 grep 字串：本函式的註解逐字提到 `problems.append` 以說明
        修前形態，第一版用字串比對時被自己的散文判紅（實測），而守的標的是**程式碼**。
```

### CollectionIntegrityTest WHY（894／906／916 三個時間切片）

原處：`tools/tests/test_run_root_unittests.py` L1292-1301（10 行，docstring 說明段）

```text

    WHY（測意圖，非僅行為）：R60 並行修復期間三次量測分別得到 894／906／916，被立案
    當成「並行負載下 discovery 收集數不決定性、疑為第四個並行假紅成因」追查。實際根因
    是**磁碟真的變了**——同一支 `test_check_defect_log_crossref.py` 被另一個並行包從
    29 支測試逐步擴充到 51 支，而其餘 52 支檔固定貢獻 865 支，故
    865+29=894、865+41=906、865+51=916，三個數字是三個時間切片，沒有一次是 race。
    追查過程暴露兩個**與該事件無關、但真實存在且當時完全無守門**的缺口，本類別鎖住：
      ① **下限語意的盲區**：實況 916 vs 下限 845 ⇒ 可靜默蒸發 71 支測試仍印 ✅；
      ② **沒被收集的測試不出現在任何一行輸出裡**——它從未被 loader 交給 runner，
         故既不在 `skipped=N`、也不在 `report_all_skips` 明細裡（這就是「靜默」的核心）。
```

### R68 零相依環境鑑別力鎖的立案與模擬手法

原處：`tools/tests/test_run_root_unittests.py` L1628-1640（13 行，註解區塊）

```text
# ── R68：零相依環境（＝CI 實況）的鑑別力鎖 ────────────────────────────────────
#
# 缺陷（三支 CI 自 2026-07-14 起連續全紅，無人察覺）：`tools/tests/` 有三支測試
# import `autoclaude.*`，連帶拉進 yaml→pydantic→httpx；而 CI 三個 job 都不裝任何
# 第三方套件。缺相依時 `unittest` discovery **不報錯**，只把該模組整份覆蓋塌成一支
# `_FailedTest` 佔位測試——122 支 Windows 迴歸鎖靜默不跑，而閘門紅在一句「測試疑似
# 大規模靜默消失（目錄改名/pattern 不符/路徑錯）」上，三條指路全錯。
#
# 本組鎖的**模擬手法**：往 `sys.meta_path` 插一個對指定 top-level 模組拋
# `ModuleNotFoundError` 的 finder，即可在**任何**環境裡重現零相依環境，不需要真的
# 建一個乾淨 venv。落地時實測：此法對真實 `tools/tests/` 樹產生的收集數與佔位模組
# 集合，與 stdlib-only venv 實跑、以及三個 CI 平台回報的數字**三方完全一致**。
# 因為要隔離 `sys.meta_path` 與 `sys.modules` 的污染，一律在子行程裡跑。
```

### MinTestsMarginCriterionTest 四個方向

原處：`tools/tests/test_run_root_unittests.py` L1734-1748（15 行，docstring 說明段）

```text

    缺陷本體與可達性的算術證明全文＝`tools/lib/min_tests_margin.py` 檔頭（本處不複寫）。
    一句話：舊的 [1.10, 1.25] 緩衝帶比的是「相依齊備收集數 ÷ MIN_TESTS」，與真正先失效
    的那根軸不同，五輪逐次驗算一次都沒跨過，每次先炸的都是環境判準且歸錯因。

    本組鎖四個方向（Rule 9 — 鎖的是意圖不是行為）：
      ① **可達性**（驗收核心）：兩層門檻都必須嚴格早於環境判準失效，且同一支斷言把
         舊判準的**不可達**釘成對照組——只換公式沒換到「先說話」，這一支就紅；
      ② 成長進 WARN 帶時真的說話，且說的是「重釘 MIN_TESTS 為 N」而非環境歸因；
      ③ 環境判準沒被蓋掉：相依真缺席時它照樣紅，新判準在該場景**閉嘴**（loss 歸零
         ⇒ 不適用），兩者射程正交、不互搶歸因；
      ④ 唯一的釘選面（會塌的模組**集合**）由真沙箱保鮮，不是第二份靜態猜測。

    另有一層順序保險：`unittest` 依類別名排序載入，`MinTests…` < `ZeroDep…`，
    故兩者同輪一起紅時，畫面上先出現的是講「重釘」的這一組。
```

### ZeroDepProbeFlagIsNotAFailOpenTest WHY（fail-open 看守者）

原處：`tools/tests/test_run_root_unittests.py` L2085-2100（16 行，docstring 說明段）

```text

    WHY（Rule 12 fail-loud）：用 `RRU_IN_ZERO_DEP_PROBE=1` 斷遞迴本身是對的（R74 實測：
    探針在套件內重跑整棵樹，放寬逾時只把整套牆鐘從 823s 放大到 3813s 且仍 TimeoutExpired）。
    問題在**沒有任何東西斷言「外層那一次真的跑了」**：`unittest` 的 `Ran N tests` 把 skipped
    計入，所以 `MIN_TESTS` 下限對「整組被 skip 掉」結構性失明；而該變數全 repo 只出現在本檔
    數行，一旦以任何方式漏進外層環境（開發者 shell／CI 的 `env:`／包裝腳本／schtasks 排程的
    使用者環境），那三支「零相依鑑別力鎖」會靜默全滅而閘門照樣印綠——**閘門自己壞掉卻不吭聲**。
    實測（本輪）：`$env:RRU_IN_ZERO_DEP_PROBE='1'` 後跑那個類別得到 `Ran 3 tests / OK
    (skipped=3) / rc=0`，三支鑑別力鎖等於不存在。

    🔴 本組刻意**不 spawn 任何子行程**（唯讀環境查詢），所以它不可能遞迴、也因此**不需要**
    自我 skip——它在探針內部與外部都跑得起來，兩種環境各有一條為真的斷言。這正是它有資格
    看守 fail-open 的前提：看守者自己若也帶同一個豁免，等於沒有看守者。

    誠實劃界：若外層環境**同時**漏了旗標又真的缺相依，本組不會紅（兩側都成立）。那種環境
    早已被 `main()` 的 fail-fast 與 `report_missing_third_party_prereqs()` 判紅，不是靜默面。
```

### CiPrereqInstallLockTest WHY 與判準邊界

原處：`tools/tests/test_run_root_unittests.py` L2170-2179（10 行，docstring 說明段）

```text

    WHY（本組最重要的一道；測意圖非僅行為）：前面幾道鎖只讓失敗**可讀**，攔不住
    「下次再多一個相依、CI 又沒裝」的復發——本輪的缺陷正是這個形狀，而且它躲過了
    連續多輪的四方複審。本鎖把「`_THIRD_PARTY_PREREQS` 這份宣告」與「CI 實際安裝
    的東西」機械綁在一起：往常數加一個相依而忘了改 workflow，這裡立刻紅。

    🔴 判準邊界（誠實劃界）：以純文字掃描認「同一個 job 內、該 step 之前出現的
    `pip install` 行」，刻意不引 YAML parser（本檔須能在最小環境下自我檢查）。
    因此它**不涵蓋**：把安裝寫進 composite action／reusable workflow／外部腳本、
    或以 `requirements.txt` 間接安裝——那些形態它一律看不到，仍是人審責任。
```

### test_every_ci_job_running_the_runner_installs_all_external_tools

原處：`tools/tests/test_run_root_unittests.py` L2251-2262（12 行，docstring 說明段）

```text

        WHY（R69 終審 SD 實測；測意圖非僅行為）：上面那道鎖只看得見 import 相依，對
        「PATH 上要有某支執行檔」結構性盲目。R69 把 `ruff check tools/` 接進 pre-push
        快層（缺 ruff＝fail-loud），而 `test_pre_push_dispatcher.py` 有 5 支測試在 tmp
        repo 內真跑該 dispatcher 並斷言 rc==0 ⇒ tools/tests 自此隱性需要 ruff。當時
        三支跑本 runner 的 workflow 只有 root-infra-ci 裝了 ruff ⇒ **同一批測試在三個
        平台有兩種結果**，而且原本綠著的 macos-compat-ci 會被打紅（SD 單變因 A/B：
        PATH 上放假 ruff → Ran 17 OK；唯一差別拿掉 ruff → FAILED〔failures=5〕）。

        本鎖擋的不是那一次，是**下一次**：再往清單加一個外部工具而忘了同步某一支
        workflow，這裡立刻紅並點名是哪一支。判準邊界同上面那道（純文字掃描，看不到
        composite action／requirements.txt 間接安裝）。
```

### CarrierVerdictParityTest WHY 與射程

原處：`tools/tests/test_run_root_unittests.py` L2377-2395（19 行，docstring 說明段）

```text

    WHY（實測，不是理論）：`UntaggedWindowsLikeSkipsTest::test_real_run_with_floor_reds_
    on_an_untagged_windows_skip` 自稱是本 repo 的**常駐缺陷注入對照組**，而複審者當回合
    量到它在 `pytest tools/tests` 下 FAIL、在 `python -m unittest` 下 OK。根因是那支測試
    用 `mock.patch.object(windows_skip_tags.os, "name", "posix")` 改掉**行程全域**的
    `os.name`（再匯出的 `os` 就是 stdlib 那一個模組物件），而 CPython 3.11 的
    `pathlib.Path.__new__` 靠它挑 flavour ⇒ patch 期間任何 `Path()` 都會拋
    `NotImplementedError`。unittest 載具下沒有人在那段期間呼叫 `Path()`，pytest 載具下
    `AssertionRewritingHook.find_spec()` 對每一支新 import 的模組都會呼叫 ⇒ 合成樹
    import 失敗、塌成 `_FailedTest`、收集數低於下限：**該紅的那一半紅得理由是錯的
    （不是漏標，是 import 炸了），該綠的那一半永遠綠不了。**

    為何非有這道鎖不可：push 閘門（`tools/run_root_unittests.py`／pre-push／三支
    compat-CI）走的**只有 unittest**，所以 pytest 那一側是紅是綠沒有任何人會看到。
    「有鎖在守假話」＋「驗證載具本身要被驗證」——本 repo 已判過的兩條，這次同時發生。

    射程（誠實劃界）：本鎖只覆蓋**會 monkeypatch 模組屬性**的類別（由
    `classes_that_monkeypatch()` 自原始碼機械抽出，不是手寫清單），因為那是已知會製造
    載具分歧的那一類動作。全檔逐類跑兩個載具在時間上不划算，且分母會隨檔案成長而漂移。
```

### test_a_synthesized_carrier_divergence_is_caught 注入體選型

原處：`tools/tests/test_run_root_unittests.py` L2482-2492（11 行，docstring 說明段）

```text

        注入體刻意是**平台中立且決定性**的（斷言「跑我的人不是 pytest」）：unittest 下綠、
        pytest 下紅，在三個平台都成立。不用讓本鎖誕生的那個真實形態當注入體，是實測後的
        決定，不是偷懶——那個形態（`mock.patch.object(<模組>.os, "name", …)` ＋ 期間 import
        新模組）的**觸發**是 Windows 專屬的：pytest 的 `fnmatch_ex` 在 `PurePosixPath`
        誤解析反斜線路徑後才落到 `absolutepath()` → `Path()` 而爆炸；POSIX 上
        `PureWindowsPath` 認得 `/`，同一條路走得通、不會分歧（當回合實測：Windows 上
        rc 0/1 分歧，改用非 `test_*.py` 的目標模組名則 0/0 不分歧）。拿一個只在單一平台
        成立的注入體當紅綠自證，等於在另外兩個平台上讓這支測試恆綠——鐵律三。
        真實形態由 `test_the_live_monkeypatching_locks_agree_across_carriers` 承接
        （它跑的是活體類別，缺陷一旦被寫回去，在 Windows 上當場分歧）。
```

## test_smoke_ci_sync.py

### TestWindowsCiShellClaimConsistency WHY（同一句宣稱三度失實）

原處：`tools/tests/test_smoke_ci_sync.py` L153-173（21 行，docstring 說明段）

```text
    WHY（DEF-101-540，R60 Scan-C C-02）：同一句宣稱已**三度失實**——R5 原文寫死、
    R57 round 1 改寫成「windows-latest 的步驟一律」仍被 pyyaml 稽核證偽、R57 收輪只改
    了檔頭而 step name 與兩處 step 註解逐字存活到 R60。實測分佈：windows-smoke
    ＝pwsh 19／bash 1，windows-nightly-full＝powershell 2／pwsh 3（其中 2 步原生
    PS 5.1 正是該宣稱的直接反例，且其中一步的 name 自己就掛著那句宣稱）。
    現行機械鎖 `test_gha_action_versions.py::TestWindowsCiHeaderSnapshotLock` 只比對
    **檔頭那張快照表** vs YAML 實況，對散文（step name／註解）零訊號。

    為何鎖住「措辭」而不是「數字」：R57 已立政策——不得寫死支數（寫死＝下一輪必再
    過期）。本鎖因此不驗任何計數，只禁止「一律／全部」這種不依賴實測就成立不了的
    絕對詞出現在宣稱句裡；要陳述分佈就去看檔頭那張由姊妹鎖看守的實測表。

    為何住在本檔：本檔 docstring 立的正是「四份手寫實作互相宣稱同步維護、零機械
    互鎖」這條軸，且本檔已在 `test_sync_maintenance_comments_present` 讀取
    `_WIN_CI` 做散文斷言——同一條軸、同一份輸入。姊妹鎖（檔頭快照表 vs YAML 實況）
    在 `tools/tests/test_gha_action_versions.py::TestWindowsCiHeaderSnapshotLock`，
    兩者互補：那支管「表要對」，本支管「別在表以外再自己講一遍」。

    鑑別力（鏡子自證，不靠改壞檔案）：豁免區內**必須**至少命中一次——那裡刻意逐字
    引述舊宣稱以資訂正。若有人把 `_ABSOLUTE_SHELL_CLAIM_RE` 改寬鬆到抓不到東西，
    正控會先紅；sentinel 兩端缺一、或豁免區被撐大到超過上限，也都會紅。
```

### test_engine_mismatch_guard_present_and_before_any_work WHY

原處：`tools/tests/test_smoke_ci_sync.py` L260-270（11 行，docstring 說明段）

```text

        WHY 與上一支同構（QA-R59-04 的原話直接適用）：「守門本身若沒有鎖，刪掉它
        全套照綠——那就與註解同級，主張自我否定」。R73 為 DEF-101-776 補了守門
        卻**沒補鎖**，而同一輪的 DEF-101-773 結案語才剛寫下「已知缺口不得只以劃界
        結案（DEF-101-757）」——同輪自我違反，QA 二審點名。實測本鎖之前全庫
        `*test*.py` 對 `ENGINE-MISMATCH` **零命中**。

        為何這個守門特別需要鎖：它的鑑別力來源是「[1/9] 的 Parser 解析必須用 5.1
        的文法」，而 5.1 對「UTF-8 無 BOM ＋ 中文註解」的 .ps1 會 parse 死、pwsh 7
        不會（R73 全庫 137 支實測 5.1 ERR=29 / 7.6.4 ERR=0）。守門被刪掉時**不會
        有任何紅燈**——本機照跑、CI 不執行這支腳本——直到某天有人在 mac/CI 上炸掉。
```

### test_min_pass_equals_actual_step_count 為何用登記表不用剖析器

原處：`tools/tests/test_smoke_ci_sync.py` L359-365（7 行，docstring 說明段）

```text
        兩腳本「原始碼字面 pass/Pass-Item 次數」與「實際執行到的步驟數」不直接相等：
        - macos_smoke_local.sh 有互斥分支（兩條路徑各一次 pass、實際命中其一）⇒ 字面偏多；
        - windows_smoke_local.ps1 有共用函式被呼叫多次、函式體內只 1 個字面 ⇒ 字面偏少。
        故不寫通用剖析器（易在改版時悄悄算錯而製造假的安全感），改用顯式登記表 ＋
        fail-loud 存在性檢查：錨點消失（訊息改寫／函式改名）即紅，逼人工重新核算。
        立案史料（含 QA 二審 bug-injection 的實測）＝
        `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
```

### test_registry_discloses_its_evidentiary_boundary WHY 與切片兩端錨定

原處：`tools/tests/test_smoke_ci_sync.py` L860-873（14 行，docstring 說明段）

```text
        WHY 這也要上鎖：R67 之前，「windows-smoke 那半張表是零 Windows 實機的讀碼推論」
        與「這些鎖只驗載具存在、不驗它真的做了那件事」兩項限制**只存在於當輪的修復回報
        JSON 裡**，repo 內 `grep` 零命中。下一輪的讀者只看得到一張兩邊等寬的表，會把推論
        讀成實測——而本輪各處（`snapshot-fingerprints-win32` 整欄 `unrecorded`、
        ADR-XPLAT-002 §6 逐輪覆蓋表、DEF-101-659）都已逐項標示推論／實測，體例是存在的，
        只有這裡漏了。註解被刪掉就會退回零揭露，故機械守住它還在。

        🔴 **判定範圍刻意只取登記表之前那段註解**，不是整檔 `in src`：本測試自己的 marker
        清單就寫著那幾個詞，整檔比對會被**自己**滿足而恆真——那正是本輪三度踩到的「換上的
        驗證自己也是假驗證」。實測佐證：整檔版在「把註解裡的字樣改掉」的注入下仍 rc=0
        （自我滿足），改成本段切片後同一注入 rc=1。**第二次踩到同一形態**：改成「登記表
        之前的全部原始碼」仍 rc=0——本檔第 638 行另一支測試的失敗訊息裡剛好也寫著「已實測
        涵蓋／已實測不涵蓋」（那是 Get-ChildItem 列舉途徑的邊界說明，與本表無關）。故切片
        **兩端都要錨**：只取取證邊界那一段註解本身。
```

### test_registered_smoke_groups_exist_in_that_script WHY 與未買到的部分

原處：`tools/tests/test_smoke_ci_sync.py` L896-905（10 行，docstring 說明段）

```text

        WHY（R67 round 2 / QA-R67-04）：`test_named_local_carriers_actually_exist` 只驗
        「檔名存在」——smoke 腳本本身幾乎不可能被刪，所以那條鎖在實務上**接近恆真**；而真正
        會發生的腐化是「情境分組被重新編號／被刪掉一組」，此時檔案還在、登記卻已指向不存在
        的組號，這張表就開始說謊而無人知曉。本鎖把判準往前推到組號層級（`[3/7]` 這種標籤
        本來就是腳本自己 echo 出來的字面，`_GROUP_RE` 已在本檔他處消費同一來源）。

        **仍未買到的**（誠實劃界，見上方 `_CI_STEP_LOCAL_CARRIER` 邊界 (c)）：本鎖不驗
        「[3/7] 那一組做的事＝該 CI step 做的事」。語意等價要嘛實跑（破壞性、分鐘級），
        要嘛比對散文（另一種推論）——兩者都不是本鎖能誠實宣稱的東西。
```

### _run 的 DEF-101-753 沿革

原處：`tools/tests/test_smoke_ci_sync.py` L1024-1034（11 行，docstring 說明段）

```text

        🔴 R69 後續（DEF-101-753）：本方法原本寫死 `shell: str = "bash"`，把**裸名**
        交給 `subprocess`。Windows 上這條路必敗——`CreateProcess` 解析裸名時把
        `System32` 排在 PATH **之前**，於是 `C:\\Windows\\System32\\bash.exe`
        （WSL 啟動器）必定先命中，無發行版時以 UTF-16LE 印
        `Windows Subsystem for Linux has no installed distributions.` 並 `exit 1`。
        受測腳本**一行都沒被執行**，本組三支卻據此斷言「腳本回了非預期 rc」——
        雲端 windows-compat-ci 上是三筆歸因完全錯誤的紅燈（本機 macOS 全綠、
        R69 四輪四方複審亦未發現）。改走 `_platform_helpers.usable_bash_for_fixture()`
        單一真相源（回傳**絕對路徑**：git 相鄰優先 + System32 整段排除 + coreutils
        驗活；完整機制與同輪對照組取證見該函式 docstring）。
```

### act 地端通道 Scan-F 的立案與邊界

原處：`tools/tests/test_smoke_ci_sync.py` L1154-1170（17 行，註解區塊）

```text
# --- act 地端通道：workflow 可達性 ＋ 零通道 job 逐個具名登記（本輪 Scan-F）--------
#
# WHY：`AutoClaude/tools/run_act_core.py` 原先把 workflow 寫死成模組常數，於是薄殼
# 只指得到 autoclaude-ci.yml 一支；同一時間根層有 11 支 workflow 共 25 個 job，其中
# root-infra-ci.yml（承載根層全部守門）與兩支 compat-CI 的 nightly 告警鏈**一個都碰
# 不到**。本輪實測：`run_act.ps1 -List` 印 9 個 job、repo 根 `act -l` 印 25 個。而根
# CLAUDE.md 與 ONBOARDING 都把 act 寫成「Linux 容器跑真 CI」且無任何限定詞 ⇒ 讀者會
# 把 9/25 讀成全部。雲端帳務停擺期間，這個差是實質的驗證真空。
#
# 本節鎖三件事：
#   ① 每一支帶 ubuntu runs-on 的 workflow 都指得到（`--workflow` 真的被消費）；
#   ② 未指定旗標時的執行標的**維持原值**——零行為變更的機械證明，不是宣稱；
#   ③ runs-on 非 ubuntu 的 job 逐個具名登記為「結構上零本機通道」，不留白。
#
# 邊界（誠實劃界）：只驗「指得到」與「登記完整」，**不驗那支在 act 上跑得完**。跑得完
# 與否取決於 runner 映像缺件（pwsh/gh/ruff）與 act 0.2.89 對 `services:` 的上游 panic，
# 兩者由 `run_act_core.preflight()` 在燒掉幾分鐘之前逐項講明，不由本節代為裁決。
```
