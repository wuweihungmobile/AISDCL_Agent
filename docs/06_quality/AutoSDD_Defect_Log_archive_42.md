# AutoSDD Defect Log — Archive 42

> **歸檔來源**：`AutoSDD_Defect_Log.md` 缺陷總表中 **3 筆已結列**。
>
> **搬遷判準的權威來源是 `tools/archive_defect_log.py`**（程式即判準，本標頭不重述細則）。
> 該工具落實 6 項搬遷判準（①狀態欄分類已結（fixed／wontfix／closed-by-decision）／②狀態欄無活躍字樣（open／routed／deferred／watch／workaround，ASCII 邊界非子字串）／③未被 crossref 掃描目標做過可辨識狀態宣稱／④散文帶交棒字樣者需 `--ack-handoff` 具名承認／⑤該列切出的欄數等於表頭欄數（欄位定位失效者一律不判讀狀態、一律不可搬）／⑥無外部居所指針宣稱本列現居主檔（指針反向依賴，DEF-101-612；有則硬擋，須先訂正該指針，不接受 --ack 繞過）），
> 並在落地後以 `--check` 稽核 7 項保全判準：(1)行尾：帳本家族每一份檔在磁碟上不得含 CR（`.gitattributes` 宣告 eol=lf）、(2)重複列：同一 ID 在同一份檔內不得出現兩列、(3)跨檔矛盾：同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話、(4)立帳指針：稽核面每一處「立帳見」都要跟得上可解析 DEF-ID，且居所宣稱與實況一致、(5)歸檔索引涵蓋性：磁碟上每支 archive 都要在主檔索引段有一條以它為主體的 bullet（雙向）、(6)非「立帳見」方言的居所宣稱：`見主檔 DEF-x`／`見 DEF-x（現居 archive_NN）` 同樣驗居所；裸「現居 archive_NN」（無「見」動詞）另受對等硬要求，須跟得上可解析 DEF-ID、(7)表格列欄數：每列切出的欄數等於該檔表頭欄數；archive 側既有列具名基線、主檔零豁免
> （本段由該檔的 `MOVE_CRITERIA`／`CHECK_CRITERIA` 常數機械生成，逐項定義見
> `check()` docstring；**勿手改**——手寫版曾與實作脫節而被複製成永久史料）。
> **歷輪標頭曾宣稱有這樣一支腳本但 repo 內無載具**，
> 且散文所載判準與實際執行的判準不一致——R60 起改為引用可重跑的工具，見該檔 docstring。
>
> **搬遷清單**：`DEF-101-664`、`DEF-101-684`、`DEF-101-698`
>
> **本次操作備註**：R67 round 3 收尾包（最終收尾）：本輪 SC 鎖落地＋散文閉環＋MIN_TESTS 第三次重釘三列入帳前的容量輪替；主檔 257283 bytes、三列合計 6419 bytes 會撞 262144 硬閘（實算 263702）。判準④ 具名承認 2 筆 false positive：DEF-101-664（fixed@R67R2，marker 改派 出現在**逐字保全的 partial@R67 原文**內，其後的〔LOCK 包補完〕段已逐項交付 (a)(b)(c)，列內無待接工作）、DEF-101-684（fixed@R67R2，marker 承接者 出現在缺陷描述「零機械承接者」與修復描述「(1c) 機械承接者現況誠實登記」內，ADR 側與 tools 側皆已交付）——與 archive_39 已 ack 的 DEF-101-626／629／662 同一類（marker 落在引述既有敘述的散文裡）。**刻意不 ack** DEF-101-652（run_local_nightly.ps1 對等缺口未修）、DEF-101-663（596／610 改派的具名載體）、DEF-101-689（分流去向明載「下一輪加一道機械對帳」），三者有真實待辦，一律留主檔
>
> 餘裕一律以 `python tools/check_defect_log_crossref.py` 的實跑訊號為權威，
> 本標頭**不對餘裕做定性宣稱**（R59 SA-R59-P2-1 訂正：定性宣稱會在同輪後續編輯中被推翻）。
>
> **原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。查詢缺陷現況一律先看主檔缺陷總表。

## 缺陷總表（已結列，逐字保全）

| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |
|---|---|---|---|---|---|---|
| DEF-101-664 | 2026-08-01 | R67 Scan-H（RATCHET 包；沙箱同 session A/B commit 後對照實測） | **HEAD 比對式棘輪在所有真正消費其 rc 的閘門裡結構性恆真**：`tools/check_script_parity.py:1039-1045::_read_previous_self_source()` 取 `git show HEAD:<本檔>`，而 pre-push（`tools/git-hooks/pre-push:223`）與三支 CI workflow 皆跑在 commit 之後（CI 為乾淨 checkout）⇒ HEAD 逐字等於工作樹 ⇒ previous_map==current_map ⇒ 永遠零違規。沙箱實測：同一筆 tier4→unpinned 降級 commit 後，舊實作 rc=0 印「✅ 零降級」、新實作 rc=1 印「❌ tier 棘輪違反」。另一 fail-open 面：`previous is None` 走綠燈空轉。同形狀另存在於 `tools/tests/test_adr_xplat001_c1c2_lock.py:1558`（`TestShrinkOnlyRatchet`）與同檔的護欄檔數棘輪 | P2（原 P1，四方複審降級） | 根層護欄 `tools/check_script_parity.py`（本輪）＋ `tools/tests/test_adr_xplat001_c1c2_lock.py`（未修） | fixed@R67R2（原 `partial@R67`，逐字保全於後）：〔R67 原文〕`check_script_parity.py` 基準改為簽入本檔的凍結常數 `_TIER_BASELINE`（23 筆），刪除唯一 git 依賴；新增涵蓋規則（活體 key 未登記於基準即紅，封堵「刪基準條目迴避棘輪」）；回歸鎖 `tools/tests/test_check_script_parity.py::TestR67BaselineRatchet` 9 支，含結構鎖 `test_ratchet_is_independent_of_git_state`（禁用 subprocess 仍須運作，舊實作在此鎖下必紅）。🔴 **未修**：`test_adr_xplat001_c1c2_lock.py` 內兩支同病棘輪不在該包授權面，改派為：未指派（解鎖條件＝比照本輪已驗證修法換成該檔內的凍結常數＋照抄結構鎖）。〔R67 round 2 LOCK 包補完，本列轉 fixed〕上述兩支同病棘輪已修：(a) `TestShrinkOnlyRatchet` 的 `_MAX_BASELINE_ENTRIES`／`_BASELINE_ID_CEILING` 基準由 `git show HEAD:<本檔>` 改為簽入本檔的 `_FROZEN_MAX_BASELINE_ENTRIES`／`_FROZEN_BASELINE_ID_CEILING`；(b) `TestGuardFileCountShrinkOnlyRatchet` 由 `git ls-tree -r HEAD` 改為 `_FROZEN_GUARD_FILE_COUNT`；(c) 新增結構鎖 `test_ratchet_is_independent_of_git_state`（禁用 subprocess）。取證：沙箱 commit 前後皆 rc=1（修前 commit 後 rc=0 ⇒ 恆真已複現）。**本列的 partial→fixed 訂正靠人工比對才發現**，流程建議見 `DEF-101-689` |
| DEF-101-684 | 2026-08-01 | R67 round 2 四方複審（ARCH-R67-01＋SD-R67-03，兩方交叉；ADRDOC 包＋LOCK 包） | **§8 表頭新規則 1（禁 `R<N>+` 開放下界輪次）零機械承接者，且同輪在唯一有機械承接者的欄位自違**——`tools/check_script_parity.py:608` 寫入 `退場：R68+`，而該檔 `_UNPINNED_EXIT_RE`（當時樣式＝「未指派」**或**「R 加十進位數字」二選一）明確放行它（實測 `re.compile(...).search('退場：R68+（…）')` → True）。Rule 7 反例：同概念兩載體採矛盾文法，被強制的那個放行被禁形態 | P2 | 根層 `docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md` ＋ 根層 `tools/check_script_parity.py` | fixed@R67R2：ADR 側規則 1 精確化為 (1a) 合法文法逐字定義（含可機械查的具名角色例外）／(1b) 射程擴及程式碼側登記表／(1c) 機械承接者現況誠實登記；tools 側正則在「R 加數字」分支後補上負向前瞻 `(?![\d+＋])`（半形與全形加號一併擋）＋該筆改列 `退場：未指派`（親讀 §8 item 11 確認承接者欄為「封存中／前置＝Phase 2-B signoff」，無具名輪次）。注入 rc=1／還原 rc=0 |
| DEF-101-698 | 2026-08-01 | R67 round 2 收尾回填後自查（EVIDENCE 包；`SA-R67-07` 同類，由本包回填動作**自己製造**後當場抓到） | **`ONBOARDING.md` §7 表② `ci-gate` v0.01 列的歸因散文寫死了「Windows 欄量測時 daemon 執行中／macOS 欄量測時 daemon 停用＝ −3」這個當時的組合**，而 round 2 以乾淨 venv 回填時本機 daemon 為 `up`（`snapshot-fingerprints-darwin` 錨的 `docker=up`）⇒ 兩欄現為同值、差額 0，該句在回填完成的當下即失實。同列的 v0.30／scripts 兩列早已依 Cluster B 教訓寫明「當輪值刻意不寫進歸因散文」而未受影響 ⇒ 缺口只在**環境狀態**這一維，尚未被那條紀律涵蓋 | P3 | 根層 `ONBOARDING.md` §7 表② | fixed@R67R2：改為不寫死任何一欄的 daemon 狀態與差額方向，只留「daemon 停用時該 3 支跳過＝ −3」這條與環境無關的因果，並附現查指令 `grep -n 'snapshot-fingerprints-' ONBOARDING.md`（macOS zsh 實跑 rc=0，兩條錨各印一行含 `docker=`）。**通則**：Cluster B 的「當輪值不寫進散文」應擴及**當輪環境狀態**（docker／pgextras／host），兩者同為每輪必變的量 |
