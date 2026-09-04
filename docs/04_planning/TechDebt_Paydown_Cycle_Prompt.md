# 技術債總清償循環令（可重複投放；流程定義版）

> 用途：掌舵者開新 session 時，將〈Prompt 本體〉整段貼入即可；可重複投放，直到
> 帳本降到〈終止條件〉由執行者宣告 DONE。
>
> **版本紀事** v2（2026-09-04，R125 收輪後）：移除 2026-09-01 D1~D7 一次性裁決與
> R114/R115 特定數字快照。核對後發現：多數已執行完畢（`DEF-200-211`／`212`／
> `236`、CLAUDE.md 並行派工檢查表）；少數仍卡著（`DEF-200-234`／`241`）；甚至
> 有帳本自己的「closed-by-decision」宣告與原始檔案內容對不上（某 ADR 頂層
> Status 已寫 Adopted，內文某節卻仍是 Proposed）。這正是「把某一刻的狀態寫死
> 進可重複使用的 prompt」必然發生的事——資訊會過時，而過時資訊比沒有資訊更
> 危險（會被誤當成「已驗證」直接採信）。**v2 起本檔只定義流程，不記錄現況**；
> 現況一律現查，包括帳本自己「已結案」的宣告，起疑就回頭讀原始檔案驗證。
> 歷史裁決存證：`docs/04_planning/AutoSDD_Adjudication_*.md`（現查最新檔名）
> 與各輪 `docs/04_planning/R*_HANDOFF.md`。v2 生效時未結列數＝**49**（起點，
> 見〈終止條件〉）。

---

## Prompt 本體（自此行起整段複製投放）

# 技術債總清償循環令
本指令可重複投放：每次開新 session 貼入即可，直到達成〈終止條件〉宣告 DONE。
**本檔不含任何「現在狀態」的快照**——「現在幾筆未結」「哪個裁決生效了沒」
「某 ADR 是什麼狀態」一律現查，不要相信本檔或記憶裡的舊數字。與記憶／舊
交棒書衝突時以**現查結果**為準；帳本裡「closed-by-decision」的宣告也可能是
錯的，起疑就直接讀該宣告指向的原始檔案核對。

## 0. 角色：舵手，讀寫分流
- **唯讀查證／分診**：可平行派多個小包（`model:'sonnet'`，每包 ≤6~8 項、
  schema 化輸出）——安全、鼓勵的用法。
- **帳本編修／實際結案／commit**：只准**單一窗口序列處理**，不得平行派工
  （根 CLAUDE.md〈並行派工防互踩檢查表〉第 1 項；此為其具體實踐）。
- 只有「毀滅性／不可逆」或需要掌舵者拍板的設計分歧才互動問；其餘自行判斷
  推進。pace band=notice 起改逐一 Agent 派工。
- 若本 session 在 Windows：mac 專屬未結列（標籤含 darwin／mac 或需要 mac
  真機）只能唯讀分診整理，不能結案，留給 mac session。

## 1. 開工程序（機械化，缺一不動工）
1. 找最新交棒書：**用數字排序**，不要用檔名字典序——
   🔴 `Sort-Object Name` 會把 `R124` 排在 `R90` 前面（實際踩過的坑）：
   ```powershell
   Get-ChildItem docs/04_planning -Filter "R*_HANDOFF.md" |
     ForEach-Object { [PSCustomObject]@{ Num = [int]($_.Name -replace '^R(\d+)_.*','$1'); Name = $_.Name } } |
     Sort-Object Num -Descending | Select-Object -First 1
   ```
2. 讀該交棒書＋其指向的證據檔／journal。
3. 現查三本帳：
   ```powershell
   python tools/check_defect_log_crossref.py --unresolved-count
   python tools/check_archive_required.py
   python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
   python tools/session_resume_planner.py --pace
   ```
4. 若要引用某個歷史裁決是否已生效：現查 `docs/04_planning/AutoSDD_Adjudication_*.md`
   最新內容，或直接讀該裁決指向的 ADR／PRD 原始檔案的 Status 欄——不要相信
   帳本字面。

## 2. 每次投放：判斷這輪是「落地輪」還是「結案輪」
- **落地輪**：未結列裡有「裁決已存在、只差實作」的項目（現查候選：帳本狀態欄
  提到某個 `AutoSDD_Adjudication_Packet_R*.md` 已選定方向，但列本身仍 open）
  → 實作 → 過四方定點複審 → 結案。計「解鎖件落地數」，不強求淨減。
- **結案輪**（優先；目標每輪淨減 5~8）：只查證、只結案，不開新戰場。

### 純結案輪三訣竅（R121~R125 實戰驗證有效）
1. **一筆一筆結，不要派一堆幫手同時衝寫帳本**（唯讀分診可平行，見上方 0）。
2. **挑「重跑一個指令就綠＝結案」的先清**——最快、風險最低。
3. **結案時不順便挖新問題**——找到就記下來留給落地輪，當場不展開。

### 結案輪標準流程
1. 現查未結列表全貌（`--unresolved-count` 印出的 ID 清單）。
2. 唯讀分診：把候選 ID 分成幾個小包（Workflow 工具 `parallel()`，
   每包 ≤6~8 項、`model:'sonnet'`），逐筆判 `closeable-now` /
   `needs-work` / `needs-decision`，附 `evidence` 與 `verify_command`。
3. 單線逐筆：親自重跑每個 `verify_command`，確認 rc=0 才動筆改帳本狀態欄
   （一次一筆，不平行）。每改完一批立刻跑一次
   `check_defect_log_crossref.py`（不帶參數）——某列超過 700 bytes 就當場
   刪減文字，**不要**塞進 grandfather／豁免清單。
4. 全部改完：`check_archive_required.py` / `check_handoff_carriers.py` /
   `--print-guard-lines` 皆 rc=0 → 全套 `python tools/run_root_unittests.py`
   （背景跑，見下方 4）全綠才 commit。
5. 寫交棒書前先過下方〈交棒書自查清單〉，避免自己製造新回歸。
6. commit → 背景 push → 背景輪詢雲端 CI 到全部 completed，逐支查
   `conclusion`（不是只看有沒有觸發）。

## 3. 交棒書自查清單（R125 實戰踩過，皆為真回歸不是雜訊）
寫完交棒書、commit 前，這三類寫法**必定**被機械鎖攔下：
1. **DEF 編號別寫成正規表示式片段**：把多個編號縮寫成
   「共同前綴 ＋ 方括號列出尾碼」的正規表示式（例如把 242／243／244 縮寫成
   前綴加中括號），會被 `test_defect_id_reference_integrity.py` 從方括號前
   截斷、讀成一個帳本裡不存在的殘缺編號而判紅。要列多個 ID，要嘛用
   `` `DEF-200-(242|243|244)` `` 這種圓括號＋直線分隔的正規表示式，要嘛
   各自完整反引號分開列（如 `DEF-200-242`／`DEF-200-243`／`DEF-200-244`）。
2. **反引號別繼續引用本輪剛改名／刪除的舊符號**：`TestR78GhostSymbolClaims`
   （幽靈符號掃描器）會判紅。舊名稱改用純文字敘述，不要包反引號。
3. **否定宣稱要有機讀證偽錨**：出現「尚未落地／未落地／尚未執行／尚未建立／
   零交付／零實作／零覆蓋／零消費者／零載體／沒有任何一行／一行都沒有／
   一次都沒跑」這些字眼，光附一句「現查指令」**不算數**——要加
   `<!-- absent-if: <目前 repo 搜不到、一旦出現就代表宣稱失效的字面> -->`。
   🔴 先跑 `python tools/tests/test_negative_existence_claims_r82.py --print-baseline`
   看逃生口 `handoff-claim-verified:` 天花板還有沒有餘裕——沒有餘裕就必須
   用真正的 `absent-if` 錨，不能靠逃生口過關。
   修好上述 1~3 通常會連帶清掉旁支平台模擬鎖的紅（同源問題）。

## 4. 品質與驗證（不可省）
- 每項實作：突變驗紅＋針對測試綠＋全套 `python tools/run_root_unittests.py`
  rc=0（親自讀 log **尾端** `rc=` 值，不要相信 harness 通知摘要字面；
  >10 分鐘用 `run_in_background: true`）。
- 實作項過四方定點複審（一審全查、二審驗修復；`model: sonnet` 可）；
  收斂標準＝四方無新 blocking。
- **push 必背景執行**（pre-push 會重跑全套閘門，常態 15~30 分鐘，前景等待
  幾乎必逾時）：
  ```powershell
  git push *> <log路徑>
  "push_rc=$LASTEXITCODE" | Out-File -Append <log路徑>
  ```
  完成後讀 log **尾端**確認 `push_rc=`；若逾時被工具砍掉（rc=143 等），用
  `git fetch` + `git log origin/main..HEAD` 判斷是否真的送達，不要盲目重推。
- push 後用**背景阻塞迴圈**（`gh run list --branch main --json
  headSha,status,conclusion` 比對本次 sha）等到全部 completed，逐支查
  `conclusion=success`，不要裸睡也不要人工反覆檢查。紅了先查是否本輪造成
  （不得套「長期紅」豁免；paths 沒觸發的 workflow 用 `workflow_dispatch` 補驗）。

## 5. 常踩陷阱（機械遵守；只增不減，過時的數字快照隨版本移除）
- 讀 rc 不接管線（pwsh 7.x 中斷管線不更新 `$LASTEXITCODE`）；`.sh` 執行禁帶
  `-n`（noexec 假綠）；逃生口環境變數只掛單一指令。
- 🔴 `context_budget_guard.py` 的水位百分比用**假設的 200k window** 算，
  Sonnet/Opus 5 等模型實際多為 1M——收到 94% 警報**先現查真實水位**
  （使用者的 `/context` 面板，或 `python tools/session_resume_planner.py --check`）
  才決定要不要真的觸發收斂 SOP。已在多個 session 誤觸發、提前砍掉進行中
  的工作，這不是「保守總沒錯」——半套收斂本身就是代價。
- 新增平台專屬 skip 是四層登記義務（`skip_group_policy` 主表／MAX 表／
  凍結快照／`skip_id_ledger` M6 id）——現查 `skip_*` 六模組族收斂
  （相關列：`DEF-200-251`／`DEF-101-951`）是否已解決，未解決前仍要走四層。
- 帳本「發現情境」欄零輪號（時鐘刻意凍結，現查 `current_round` 用
  `check_defect_log_crossref.py`）；狀態欄 ≤700 bytes＝索引，長文搬進
  `docs/06_quality/CrossPlatform_R*.md` 具名證據檔；程式碼註解提輪號需帶
  `round-label-ok` 標籤。
- 交棒書「還沒做」節每筆帶現查指令 code span；否定宣稱帶 `absent-if` 錨
  （見上方〈交棒書自查清單〉）。
- 帳本主檔編修後、最後一次全套之前，不再寫任何文件。
- 淨額棘輪比對用「工作樹 vs HEAD」：先 commit 再跑全套會自然轉綠，不必慌。

## 6. 每輪結尾必須輸出
1. 這輪是落地輪還是結案輪，做了哪些項目；
2. 帳本起訖未結列數與淨額（＋外部阻塞軌／結構性長債軌現況一句話，含最近
   複查日——帳本本身會警告複查日 >14 天的側軌列，別放著變垃圾桶）；
3. commit＋push＋雲端 CI 逐支結論；
4. 呈報單（僅需要掌舵者拍板的新裁決件，附現查依據）；
5. 若這輪順手發現需要落地輪處理的候選，列出 ID＋一句話理由，交給下一輪，
   不要當場展開；
6. 交棒書寫入 `docs/04_planning/R<N>_HANDOFF.md`（N＝現查最新號 +1），並過
   一次上方〈交棒書自查清單〉；
7. 給我下輪可以大力降帳本的策略建議。

## 7. 終止條件
主帳本未結列數（`--unresolved-count`）降到 **0**，且外部阻塞軌／結構性長債
軌兩條側軌（不計入前述分母）在交棒書中逐筆列出現況與最近複查日。屆時輸出
總結帳：起點 49（v2 生效時，R125）→ 終點 0，逐輪淨減歸因。


## 8. Token 資訊
（每次投放時貼上當時 `/usage` 快照）
