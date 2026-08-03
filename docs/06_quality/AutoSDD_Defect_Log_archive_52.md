# AutoSDD Defect Log — Archive 52

> **歸檔來源**：`AutoSDD_Defect_Log.md` 缺陷總表中 **3 筆已結列**。
>
> **搬遷判準的權威來源是 `tools/archive_defect_log.py`**（程式即判準，本標頭不重述細則）。
> 該工具落實 6 項搬遷判準（①狀態欄分類已結（fixed／wontfix／closed-by-decision）／②狀態欄無活躍字樣（open／routed／deferred／watch／workaround，ASCII 邊界非子字串；程式碼片段與角引號引述內的字樣不算，R68 收窄）／③被 crossref 掃描目標宣稱過狀態者可搬，但搬後該宣稱必須仍解析得到（帳本家族＝主檔 ∪ archive；由 --check 判準(8) 實跑驗證，R68 改寫）／④散文帶交棒字樣者需 `--ack-handoff` 具名承認／⑤該列切出的欄數等於表頭欄數（欄位定位失效者一律不判讀狀態、一律不可搬）／⑥無外部居所指針宣稱本列現居主檔（指針反向依賴，DEF-101-612；有則硬擋，須先訂正該指針，不接受 --ack 繞過）），
> 並在落地後以 `--check` 稽核 8 項保全判準：(1)行尾：帳本家族每一份檔在磁碟上不得含 CR（`.gitattributes` 宣告 eol=lf）、(2)重複列：同一 ID 在同一份檔內不得出現兩列、(3)跨檔矛盾：同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話、(4)立帳指針：稽核面每一處「立帳見」都要跟得上可解析 DEF-ID，且居所宣稱與實況一致、(5)歸檔索引涵蓋性：磁碟上每支 archive 都要在歸檔索引檔有一條以它為主體的 bullet（雙向）、(6)非「立帳見」方言的居所宣稱：`見主檔 DEF-x`／`見 DEF-x（現居 archive_NN）` 同樣驗居所；裸「現居 archive_NN」（無「見」動詞）另受對等硬要求，須跟得上可解析 DEF-ID、(7)表格列欄數：每列切出的欄數等於該檔表頭欄數；archive 側既有列具名基線、主檔零豁免、(8)跨檔宣稱可解析：掃描目標的每一句狀態宣稱都要能在帳本家族（主檔 ∪ archive）解析到，且狀態一致（判準③ 改寫後的事後條件，R68）
> （本段由該檔的 `MOVE_CRITERIA`／`CHECK_CRITERIA` 常數機械生成，逐項定義見
> `check()` docstring；**勿手改**——手寫版曾與實作脫節而被複製成永久史料）。
> **歷輪標頭曾宣稱有這樣一支腳本但 repo 內無載具**，
> 且散文所載判準與實際執行的判準不一致——R60 起改為引用可重跑的工具，見該檔 docstring。
>
> **搬遷清單**：`DEF-101-771`、`DEF-101-772`、`DEF-101-774`
>
> **本次操作備註**：R73 開場歸檔：搬 R72 已結三列，回到 warn 線下
>
> 餘裕一律以 `python tools/check_defect_log_crossref.py` 的實跑訊號為權威，
> 本標頭**不對餘裕做定性宣稱**（R59 SA-R59-P2-1 訂正：定性宣稱會在同輪後續編輯中被推翻）。
>
> **原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。查詢缺陷現況一律先看主檔缺陷總表。

## 缺陷總表（已結列，逐字保全）

| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |
|---|---|---|---|---|---|---|
| DEF-101-771 | 2026-08-03 | R72 開輪核對 CI 現況（R71 收官 commit `1e5214b` push 後首次比對 GitHub Actions 結果） | **R71 收官 commit 讓 `macos-compat-ci` 與 `root-infra-ci` 由綠轉紅**（前一 commit `fd860ab` 兩支皆 success）。兩個**獨立**根因，共同形態＝**Windows 側閘門對「只在非 Windows 成立的問題」結構性失明**。**根因 A（標籤不一致）**：6 支 skip 的標籤中 5 支寫 `[WINDOWS-ONLY]`（`tools/tests/test_dev_start.py:6301`）、1 支完全沒標籤（`tools/tests/test_ps51_compat.py:670-674`），而守衛 `tools/run_root_unittests.py:115` 只認 `[WINDOWS-NATIVE-ONLY]`；**該守衛 `:596-599` 有 `if on_windows: return []`，在 Windows 上整組閉嘴** ⇒ 本機 pytest／pre-push／windows-compat-ci **三個 Windows 側閘門是同一個瞎點的三份複本**。**根因 B（單側對稱鎖）**：`test_dev_start.TestMacNightlyPlistCapabilityTable::test_capability_row_count_reaches_windows_side_parity` 斷言 `5 not greater than or equal to 6`——R71 給 Windows `-Status` 增列使 win_rows 4→6、mac 側未動；**該類別層帶 `@unittest.skipUnless(sys.platform == "darwin")`（`test_dev_start.py:3777-3783`），在 Windows 上 SKIPPED** ⇒ **守「兩側對稱」的鎖只有一側跑得到**。**量化失明面**：本機 Windows skip 44 支 vs mac/ubuntu skip 33 支、兩集合近乎互斥，28 支 darwin-only 測試在 Windows 上結構性不可見；`MIN_TESTS=1663` 用 `countTestCases()`（收集數）、skip 與否不影響 ⇒「1663 OK」與「1663 FAILED」**可同時為真** | P0 | `tools/tests/test_dev_start.py`／`tools/tests/test_ps51_compat.py`／`tools/install_mac_nightly.sh` | fixed@R72：**根因 A**＝兩處都補上正確標籤，驗證以 AST 靜態模擬非 Windows 判定，**真正漏標 0 處**。**根因 B**＝`tools/install_mac_nightly.sh` 補 `StandardErrorPath` 的真實 `_cap_line`（該鍵 plist `:119` 有寫卻**從未被檢查＝真覆蓋缺口，非湊數**），mac_rows 5→6；同時清掉 3 處寫死的「四項」過期字面。驗證＝靜態計數 `5 + 3 − 2 = 6` ≥ win 6、`bash -n` rc=0、`pytest test_ps51_compat.py test_schedule_capability_parity.py` **19 passed rc=0**。⚠️ **誠實劃界**：本列修的是兩個**症狀**；兩個閘門盲點**本身**（守衛在 Windows 上整組閉嘴、對稱鎖單側跑）本輪**未改** |
| DEF-101-772 | 2026-08-03 | R72 收斂包複核前一包（因額度中斷未收尾）寫入的歸檔裁決文件與機械鎖 | **治理文件自己犯了它正在治的病：寫死的量測值當輪即 stale**。`docs/04_planning/Archive/README.md` 開頭才明訂「不快照數字、一律 `ls` 實查」，但同一份檔的裁決段、本帳本 `DEF-101-770` 列、`tools/tests/test_ntfs_trailing_space_device_name.py:609-616` 註解，三處都寫死了斷鏈規模「78 處／54 檔／15／19」。本輪以 `git ls-files` 逐檔套鎖內同一條 `_ARCHIVABLE_DOC_RE` 複查：實際 **298 處／176 份檔**，其中逐字保全帳本 **16 處**、`AISDLC_SDD/AISDLC_SDD_v0.XX/` 凍結版 **176 處／92 檔**、AutoClaude **8 處**——**四個數字全部對不上**，凍結版一項差近 9 倍（92 份凍結版各存一份 `SDD_AUTOCLAUDE_BRIDGE.md` 引用，即「同一句話在 30 個版本各留一份」的既有形態，估算最易漏算者） | P2 | `docs/04_planning/Archive/README.md`／`tools/tests/test_ntfs_trailing_space_device_name.py`／本帳本 `DEF-101-770` 列 | fixed@R72：三處全部改寫為「決定性事實＝**兩類禁改持有者非空**（規模只是佐證）」＋ dated snapshot ＋**複查方法**（`git ls-files` 套鎖內同一條 regex；鎖自身掃的是其中 root `docs/**.md` 子集，同日實測 110 處／75 檔）。**教訓**：`DEF-101-770` 拒用映射表的理由「表要人維護、漏補即 stale」正確，卻把同樣會 stale 的**散文數字**原地留下——**「不列映射表」與「不寫死數字」是同一條紀律的兩半，只做前半等於沒做** |
| DEF-101-774 | 2026-08-03 | R72 掌舵者提問「Windows smoke 排程是否得等每日 02:00 才知道結果」，以隨選觸發實測作答 | **答案＝不必等；且這是 R71 那筆 CP950 修復第一次在真排程環境被驗證**。`Start-ScheduledTask -TaskName AutoClaude_WindowsSmoke` 隨選觸發，約 **80 秒**完成、`LastTaskResult=0`；log 逐字 `[smoke-env] codepage=950`、`cwd=C:\WINDOWS\system32`、`===== 彙總：PASS=12 FAIL=0 =====`。**為何值得立帳**：該修復先前只有互動式 shell 的證據，而排程環境的 codepage 與 cwd **兩者都與互動式不同**（cwd 落在 `system32`＝相對路徑必炸），正是它要防的情境 | P3 | `AutoClaude_WindowsSmoke` 排程工作／`tools/windows_smoke_local.ps1` | no_action_needed（正面驗證結果，無待修項）——併記可複用手法：驗排程行為用 `Start-ScheduledTask` 隨選觸發 ＋ `Get-ScheduledTaskInfo` 讀 `LastTaskResult`，屬根 `CLAUDE.md`〈反「事後諸葛」取證規則〉的執行面動作 |
