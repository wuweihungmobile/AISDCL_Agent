# `tools/sync_onboarding_baselines.py` — R60/R67 設計史料搬遷

> R99 收尾單人窗口為釋出 `SPECIAL_FILES` raw-line 棘輪餘裕（`TestActionableMessagesHaveLocHeadroom`
> 要求 ≥5 行），把該檔模組 docstring 內的 R60 round 3／R67 歷史論證段**逐字搬到本檔**，
> docstring 內只留精簡指標。內容未刪一字，僅換家；程式行為、判準、測試皆未變動。

## R60 round 3 補的兩件事（四方複審 round 2 全數 REJECT 的兩個根因）

- **A. 受鎖行的散文也要受管**（ARCH-R60R2-03／SA-R60R2-02／SD-R60-R2-03／QA2-R60-02，
  四方獨立全數命中）：round 1 落地本產生器後，受鎖行的 token 已是 845，而**同一行的
  散文仍寫「R60=756」**。⇒ **產生器 ＋ `--check` 只保證「被抽取的那個 token」新鮮，
  完全不保證同一行的散文新鮮**——這是本 repo 對「機械鎖已落地」的認定門檻必須修正的
  地方（DEF-101-562）。兩道判準（見 `prose_problems()`）：
  1. **受管值不得在受鎖行出現第二次**（≥3 位數才判，見該函式的位數門檻 WHY）：
     散文裡複製一份當輪值，下一次變動時它就是新的 stale 站點。
  2. **同量宣稱**：值 ≠ live 者必須登記進 `Spec.historical` 並附 WHY，否則紅。
     歷史值放行、當輪值一律不得寫進散文。

## R60 round 3 **四方複審之後**回補的三筆（四方獨立命中，非本檔自查）

- **C. `Spec.historical` 補上 stale 自檢**（QA-R60R3-02／ARCH-R60R3-01 附帶／
  SA-R60R3-04／SD-R60R3-02，**四方全數獨立命中同一筆**）：判準(2) 在 round 2 新增了
  這張豁免表卻沒給它任何反向檢查——注入一筆文件裡從未出現的死登記，`--check` 照樣
  rc=0。而**同一個函式的判準(1)** 錯誤訊息自己就寫著「本鎖刻意不設個別豁免——豁免表
  本身就是下一個 stale 站點」，判準(2) 卻正好設了一張。見 `historical_problems()`。
- **D. 判準(2) 不再綁死 `=` 標點**（ARCH-R60R3-01／SD-R60R3-01 二方命中）：原形只認
  `R<輪號>=<數字>` 字面，中文同義散文整類逸出，而受鎖行上當時就躺著未登記的舊值。
  改為「主詞 × 連接」兩段式，並補一道**無輪號主詞**的量測宣稱判準。落地當下即在兩條
  受鎖行各抓到一筆未登記歷史值（其一正是 ARCH 指認的活體證據），皆改以登記收編。
- **E. 指紋觸發器四棵 glob 對齊為遞迴**（SD-R60R3-03）：見 `_FINGERPRINT_TREES` 的 WHY。
- **F. 指紋改為行尾無關**（DEF-101-613）：原版 hash 原始 bytes，而本機 Windows 工作樹
  有 48／72／92 檔是 CRLF、索引卻因 `.gitattributes` 的 `* text=auto eol=lf` 一律 LF
  ⇒ **fresh clone／CI runner／macOS 上四格必然全部對不上，`--check-snapshot` 開箱即紅**。
  修法＝hash 前先在 bytes 層折行尾，見 `_normalize_eol`。本輪主題正是跨平台相容性，
  故不交棒。
- **B. 表②（dated snapshot）從「靠人記得」升為「一條指令 ＋ 因果式 stale 觸發器」**
  （ARCH-R60R2-02③／SA-R60R2-02②）：round 1 填了 v0.30=1736，round 2 動了 v0.30
  測試樹使實測變 1747，**沒人記得回填**，而表頭同時宣稱「四格皆經獨立覆核」⇒ 假宣稱。
  - `--write --with-slow`：實跑 ci-gate（解析其 `逐軌計數：vX:N` 自證行）＋ AutoClaude
    pytest，四格一次填完（`_SLOW_SPECS`）。
  - `--check-snapshot`：重算四套**測試樹內容指紋**與文件記載比對，指紋一變即判
    presumed stale。判準是**因果的**（計數只可能因測試樹變動而變），同
    `ADR-SD09-011`「把證據從日曆解綁、改綁源碼變動」的既有先例。
  - 接線刻意只到 **pre-push**（收輪＝push 時點付這個代價才合理），**不**接根層 unittest
    閘門——那支每輪跑數十次，會養成忽略紅燈的習慣。
  - 🔴 **對 ARCH-R60R2-06（護欄層成長過快）的正面回應**：本次擴充**零新增鎖檔、零新增
    測試檔**——全部落在本檔既有 `_SPECS` 機制與既有
    `tools/tests/test_doc_loc_baseline_freshness_r60.py` 內，且淨效果是**把表② 那 4 格
    「零機制」的欄位收進既有機制** ⇒ 未受檢面淨減少。這是對「禁止新增鎖、只准合併」
    的遵守，不是規避。

## R67 補的兩件事（本輪 R67-D1〔P1〕／R67-D6／R67-D20；WHY 見各自區塊）

- **G. 平台維度升為一等公民**（R67-D1，本輪唯一 P1）：本檔在 R67 之前**全檔零平台偵測**
  （`grep -E "platform|sys.platform|os.name|darwin|win32"` 零命中），而表② 四格的
  欄位正則一律以 `**…**` 粗體錨定「Windows 11」那一欄（原註解自陳「以 `**` 包裝限定
  在 Windows 欄」）。⇒ **在 macOS 上執行文件與 `--check-snapshot` 紅燈訊息都指路的
  `--write --with-slow`，會把 macOS 實測值靜默寫進標示「Windows 11 實測」的格子**，
  摧毀該表存在的唯一理由（讓開發者分辨「平台差異」與「退化」）並產生一句假 provenance。
  修法**不是**「照平台換一組正則」（那是同一語意兩份實作，本檔一直在治的病），而是
  **改以 markdown 欄位座標定位**：`_PLATFORM_COLUMN_LABELS` 只記「平台鍵 → 表頭識別字」，
  真正的欄號由 `platform_cell_index()` **當場從表頭推導**（欄號寫死才會在表格增欄時
  靜默抽錯欄——正是 SA-R60-01 的形態）；讀寫一律先 `_split_row()` 切格、只在自己那
  一格內做 `findall`／`sub`（見 `slow_documented`／`render_slow`）⇒ **寫到別欄在結構
  上不可能發生**，且兩欄共用同一組 Field 正則（少一份會漂移的東西）。回填路徑另加
  兩道守門：(a) 無對應欄的平台（例：Linux CI runner）**fail-loud rc=2**，絕不猜一欄
  來寫；(b) `--platform` 只准用於唯讀稽核，**不得**與 `--write` 併用——跨平台代填
  產生的正是一句假 provenance，那就是 R67-D1 本體。
- **H. 指紋記帳改為 per-platform**（R67-D6）：原版只有一條全域 `snapshot-fingerprints`
  錨，語意是「上一次回填時的測試樹」；但回填只寫得到一欄 ⇒ **另一欄的 stale 在結構上
  永遠測不到**（實測：macOS 欄三格灌成 9999，`--check-snapshot` 照樣印 ✅ rc=0）。
  改為每平台一條 `snapshot-fingerprints-<平台鍵>:` 錨，各自記「**該欄的數字是在哪一棵
  測試樹上量的**」＋ `measured-at`／`host`／`docker`／`pgextras` provenance（何時、哪台
  機器、docker daemon 狀態、venv 有無 PG extras——後兩者各自都會改變計數：docker 停用
  時 v0.01／v0.30 各 −3〔§7 既有容差段〕、PG extras 存在時 AutoClaude 的 PG-gated 測試
  由 skip 轉 pass 使 passed 虛高，兩者不入帳就是下一個「把環境差異誤判為退化」）。
  判準：**當前平台欄的記錄指紋 ≠ live 指紋 ⇒ 該欄 presumed stale（紅）**；
  其他欄只做 ⚠️ 告知不影響 rc（別台機器的欄不是本機修得動的東西，硬紅只會養成忽略
  紅燈的習慣）。無對應欄的平台（Linux CI runner）判準**退化為舊語意**：
  「沒有任何一欄是新鮮的」才紅——嚴格弱於逐欄判準，如實劃界寫在 `check_snapshot()`。
- **I. `main()` argparse 化 ＋ 未知旗標 fail-loud**（R67-D20）：原版用 `"--flag" in argv`
  手搓解析，未知旗標一律靜默掉進 default 分支並 rc=0。實測後果：`--check-snapsho`
  （少一字）在「表② 確實過期」的工作樹上回 **rc=0 假綠**，而正確拼法 rc=1；
  文件到處引用的 `--check` 根本不是實存旗標，只是恰好掉進 default 才「看起來對」。
  修法＝argparse（未知旗標 rc=2、`--help` 印用法）＋**把 `--check` 實作為顯式旗標**
  （選它而非改文件：`--check` 已被 ONBOARDING §7、`CrossPlatform_Scan_Dimensions.md`、
  `ADR-XPLAT-002` 三份文件引用，且「產生器 ＋ `--check`」正是本 repo 既有慣例
  〔`snapshot_sync.py`〕——讓字面成真比讓三份文件改口更小、更對）。
- **J. 指紋夾住慢量測窗口**（DEF-101-677，R67 收尾 Scan-H）：原本是「先跑分鐘級的
  `measure_slow()`、**跑完之後**才 `measure_fingerprints()`」⇒ 樹若在那段窗口內被改動
  （並行的修復包還在寫測試檔），錨記下**改動後**的樹、四格計數卻留在**改動前**的樹，
  事後 `--check-snapshot` 指紋相符判 ✅ rc=0 而計數已 stale。**回填路徑親手把觸發器
  拆掉**：樹確實變動了（那正是本觸發器唯一認得的事件），卻被寫成基準。修法＝
  `measure_slow_on_stable_tree()` 前後各取一次指紋，不同即 fail-loud 且**一個字都不寫**
  （見該函式的完整 WHY／代價／劃界）。同型收斂：`--check-snapshot` 與 `--json` 原本在
  單次呼叫內把 live 指紋量 2～3 次 ⇒ 判決與取證可能來自不同時點；改為一次量、注入共用。
