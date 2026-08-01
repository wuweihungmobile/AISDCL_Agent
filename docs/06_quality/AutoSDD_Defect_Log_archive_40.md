# AutoSDD Defect Log — Archive 40

> **歸檔來源**：`AutoSDD_Defect_Log.md` 缺陷總表中 **1 筆已結列**。
>
> **搬遷判準的權威來源是 `tools/archive_defect_log.py`**（程式即判準，本標頭不重述細則）。
> 該工具落實 6 項搬遷判準（①狀態欄分類已結（fixed／wontfix／closed-by-decision）／②狀態欄無活躍字樣（open／routed／deferred／watch／workaround，ASCII 邊界非子字串）／③未被 crossref 掃描目標做過可辨識狀態宣稱／④散文帶交棒字樣者需 `--ack-handoff` 具名承認／⑤該列切出的欄數等於表頭欄數（欄位定位失效者一律不判讀狀態、一律不可搬）／⑥無外部居所指針宣稱本列現居主檔（指針反向依賴，DEF-101-612；有則硬擋，須先訂正該指針，不接受 --ack 繞過）），
> 並在落地後以 `--check` 稽核 7 項保全判準：(1)行尾：帳本家族每一份檔在磁碟上不得含 CR（`.gitattributes` 宣告 eol=lf）、(2)重複列：同一 ID 在同一份檔內不得出現兩列、(3)跨檔矛盾：同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話、(4)立帳指針：稽核面每一處「立帳見」都要跟得上可解析 DEF-ID，且居所宣稱與實況一致、(5)歸檔索引涵蓋性：磁碟上每支 archive 都要在主檔索引段有一條以它為主體的 bullet（雙向）、(6)非「立帳見」方言的居所宣稱：`見主檔 DEF-x`／`見 DEF-x（現居 archive_NN）` 同樣驗居所；裸「現居 archive_NN」（無「見」動詞）另受對等硬要求，須跟得上可解析 DEF-ID、(7)表格列欄數：每列切出的欄數等於該檔表頭欄數；archive 側既有列具名基線、主檔零豁免
> （本段由該檔的 `MOVE_CRITERIA`／`CHECK_CRITERIA` 常數機械生成，逐項定義見
> `check()` docstring；**勿手改**——手寫版曾與實作脫節而被複製成永久史料）。
> **歷輪標頭曾宣稱有這樣一支腳本但 repo 內無載具**，
> 且散文所載判準與實際執行的判準不一致——R60 起改為引用可重跑的工具，見該檔 docstring。
>
> **搬遷清單**：`DEF-101-677`
>
> **本次操作備註**：R67 round 2 收尾（EVIDENCE 包）：四方複審 round 2 修復入帳前的容量輪替；主檔 95.9% 逼近 262144 硬上限（ARCH-R67-05(c)）
>
> 餘裕一律以 `python tools/check_defect_log_crossref.py` 的實跑訊號為權威，
> 本標頭**不對餘裕做定性宣稱**（R59 SA-R59-P2-1 訂正：定性宣稱會在同輪後續編輯中被推翻）。
>
> **原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。查詢缺陷現況一律先看主檔缺陷總表。

## 缺陷總表（已結列，逐字保全）

| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |
|---|---|---|---|---|---|---|
| DEF-101-677 | 2026-08-01 | R67 收尾 Scan-H | **`tools/sync_onboarding_baselines.py` 的 `--write --with-slow` 在慢量測跑完之後才取測試樹指紋**（`measure_slow()` → `measure_fingerprints()`，舊 L1196-1197）⇒ 測試樹若在那段分鐘級窗口內被改動（並行修復包寫測試檔／另一 agent 同時作業），`snapshot-fingerprints-<平台>` 錨會記下**改動後**那棵樹的指紋，而表② 四格計數留在**改動前**的樹上；事後 `--check-snapshot` 量到相符指紋判 ✅ rc=0，**計數其實已 stale**。錨的字面語意是「該欄的數字是在哪一棵測試樹上量的」，實際記下的卻是一棵**從未被量測過**的樹。這不屬於檔頭已揭露的「會漏」邊界——樹確實變動了（觸發器唯一認得的事件），是**回填路徑親手把觸發器拆掉**；反向亦會咬（改動事後還原則錨誤紅）。取證：沙箱複現腳本印出「文件計數 3／文件指紋 064594d853a2／量測前真實指紋 a39cb8e812af／現查 live 064594d853a2／現在重測會得 4／`--check-snapshot` rc=0」＝假綠組合成立。活體徵候：BASELINE 包寫入 macOS `scripts/tests`=253、收尾包同樹量到 259 而 `scripts=66deed1f4057` 前後未變。同型窗口另二處：`--check-snapshot` 判決後重量指紋才印證據（判決依據≠取證載具）、`--json` 單次呼叫內量 live 指紋 3 次／算 `check()` 2 次（可印 `snapshot_problems: []` 卻回 rc=1） | P2 | 就地修復（R67 收尾）：新增 `measure_slow_on_stable_tree()` 前後各取一次指紋夾住窗口，不同即 fail-loud 且**一個 byte 都不寫**（訊息含變動樹清單＋重跑指令）；`snapshot_report`／`check_snapshot` 加可選 `live` 注入使唯讀路徑一次量、到處用。契約方向維持「會漏、不會冤」——這是**取消回填路徑的自我豁免**，非提高嚴格度。回歸鎖 5 支落 `tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR67SlowMeasurementWindowIsFingerprintBracketed`（含假綠產物構造反證、代價劃界、唯讀路徑量測次數）。殘留缺口：窗口內「改動又還原」偵測不到（淨變動判準）；`measure_all()`（表①）同型窗口刻意不修（表① 有 live 鎖自我修正） | fixed@R67 收尾（注入雙向實測：A/B/C 三組注入皆 rc=1、逐字還原後皆 rc=0；`run_root_unittests` 1323 tests OK；`--check`／`--check-snapshot` 於乾淨 venv 皆 rc=0） |
