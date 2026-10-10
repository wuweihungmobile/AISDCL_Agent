# AutoSDD Structural Debt Log — 結構性長債軌

> **裁決存證**：掌舵者 2026-08-30 核准分軌（存證＝[`AutoSDD_TechDebt_Paydown_Playbook.md`](../04_planning/AutoSDD_TechDebt_Paydown_Playbook.md) §6 第 3 條）。
> 本表登記**跨輪工程或內部授權**型長債——修復本身需要多輪撥額度、或落地前需要掌舵者
> 具名裁決／不在單一修復包授權面內的缺陷。它們不是「卡在外部世界」（那走姊妹表
> [`AutoSDD_External_Blocked_Log.md`](AutoSDD_External_Blocked_Log.md)），也不是「單輪
> 可修的債」（那留在主帳本 [`AutoSDD_Defect_Log.md`](AutoSDD_Defect_Log.md) 未結列），
> 分軌讓主帳本的未結列數（`--unresolved-count` 的 warn/fail 分母）量到的是修復速度
> 真正能影響的量。
>
> 🔴 **本表不是規避未結列警戒線的後門**：判準與稽核共用
> `tools/lib/ledger_closing_guards.py`（`external_blocked_log_problems()` 注入
> `STRUCTURAL_DEBT_SOURCE_RE`）——三條件缺一不可：
> - **具名阻塞源限枚舉**：合法值只有 `結構性長債-<具名理由>` 一種形態
>   （fullmatch `結構性長債-\S+`，token 內不得有任何空白；裸「結構性長債」不是萬用桶），
>   且**與外部軌枚舉互斥**——外部軌四值寫進本表、或本表 token 寫進外部軌，皆當場 fail，
>   兩軌互為後門是要防的形態。
> - **解鎖條件可機械查**：每列必須寫出可觀測、可重跑的解鎖判準（指令＋預期輸出，
>   或磁碟上查得到的檔案／欄位形態），不得寫成散文式「擇機再看」。
> - **同 ID 不得雙帳並存**：同一 DEF-ID 不得同時出現在本表與主帳本未結列
>   （交叉鎖，出現即 fail）；列入本表前，主帳本該列必須先收斂為指向本表的
>   `closed-by-decision` 索引。
> - **「最近複查日」欄保留為資料**（格式不合仍 fail）；逾期提醒已於 2026-10-10 退役
>   （掌舵者 T1 立案；事件驅動：列由各自解鎖事件喚醒、新立 DEF／寫證據檔時對照）。
> - **成長棘輪**：本表筆數上限＝`ledger_closing_guards._STRUCTURAL_DEBT_MAX_ROWS`
>   （現值 7）。新增一列必須先取得掌舵者**具名裁決**（存證比照 playbook §6 落款體例），
>   裁決落款後才准把該常數重釘為新值——重釘與新列須在同一次變更內。
> - `python tools/check_defect_log_crossref.py --unresolved-count` 會印出本表筆數
>   （不計入主帳本 warn/fail 分母，但**永遠可見**，不得悄悄消失）。
>
> 首批 7 列＝R113 結案輪依裁決自主帳本遷入（起始日與複查日皆 2026-08-30）。

## 格式定義

| 欄位 | 說明 |
|---|---|
| `DEF-ID` | 對應主帳本原本的缺陷編號 |
| `具名阻塞源` | 合法值：`結構性長債-<具名理由>`（fullmatch `結構性長債-\S+`，token 內不得有空白；不得使用外部軌的四種枚舉值） |
| `阻塞起始日` | ISO 日期（`YYYY-MM-DD`），本缺陷轉入結構性長債軌的日期 |
| `解鎖條件（可機械查）` | 可觀測、可重跑的解鎖判準（指令＋預期輸出，或磁碟上查得到的形態），成立後應把該列遷回主帳本或直接結案 |
| `最近複查日` | ISO 日期，最近一次確認長債仍成立的日期（純資料欄；逾期 warn 已於 2026-10-10 退役） |

## 缺陷總表

| DEF-ID | 具名阻塞源 | 阻塞起始日 | 解鎖條件（可機械查） | 最近複查日 |
|---|---|---|---|---|
| DEF-101-018 | 結構性長債-ruff存量分批清 | 2026-08-30 | `.venv/bin/ruff check . 2>&1 \| tail -1` 回「Found 0 errors.」或殘量 shrink-only 棘輪進閘（掌舵者 2026-08-29 裁維持逐筆清，未來輪照撥額度批量清）（2026-10-09 複查：ruff 0.15.21 `check .` 根目錄＝Found 3566 errors（R76 同口徑 3,711）、cwd=AutoClaude＝681（R76 824）；縮小但非 0，且僅 tools/ruff.toml 的 E501 有棘輪、無全量 shrink-only 棘輪→仍成立） | 2026-10-09 |
| DEF-101-398 | 結構性長債-dev_start拆分 | 2026-08-30 | `tools/lib/bootstrap_lock.py` 與 `tools/lib/nightly_heartbeat.py` 存在，且 `python AutoClaude/tools/check_loc_budget.py --json` 之 dev_start.py loc 低於拆分前現值 1951（2026-10-09 複查：兩支模組仍不存在；loc=1951／棘輪 1952 僅差 1 行、非拆分成果；原條件前半「loc<1952」字面成立卻無實質，故改寫為「低於 1951」→仍成立） | 2026-10-09 |
| DEF-101-701 | 結構性長債-run_root_unittests行數死結 | 2026-08-30 | 同上指令之 run_root_unittests.py headroom>0 且 MIN_TESTS 重釘路徑存在指紋一致性斷言（後半 2026-09-01 複查已達成：`run_root_unittests.py` 之 `min_tests_note_stale_tokens()` 接 fail-fast；前半 headroom 現值 0 未達成，AND 整體未解鎖）（2026-10-09 複查：run_root_unittests.py loc=777／棘輪 777＝headroom 0，前半仍未達成；`min_tests_note_stale_tokens()` 仍在且 main() fail-fast 接線→仍未解鎖） | 2026-10-09 |
| DEF-101-702 | 結構性長債-R68稽核波 | 2026-08-30 | CrossPlatform_R68_Scan_Findings.md「狀態@R69」欄 open/partial 計數＝0（2026-08-30 現值 28；2026-09-01 複查仍 28）（2026-10-09 複查：「狀態@R69」欄 open 23＋partial 5＝28，與 08-30／09-01 同口徑（另 1 筆 partial@R69）→仍成立） | 2026-10-09 |
| DEF-101-960 | 結構性長債-skip剖面需Windows實機 | 2026-08-30 | `tools/lib/skip_group_policy.py` 的 `_UNMEASURED_RUNNER_PROFILES` 不再含標 DEF-101-960 的鍵（2026-10-09 現查 2 鍵：AutoClaude/tests@linux+nopg+solo+nopgext、AISDLC_SDD/fsm_runtime@win32）（2026-10-09 複查：原條件指向 skip_id_ledger.json 的 tools/tests 鍵，而該樹鍵文法零軸、結構上不可能長出 solo／ubuntu 剖面鍵，故改指真載體；仍成立） | 2026-10-09 |
| DEF-101-980 | 結構性長債-ADR-XPLAT-005待裁決 | 2026-08-30 | docs/04_planning/ADR/ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md 檔頭狀態行不再是 Proposed（2026-09-01 複查：仍 Proposed（R81））（2026-10-09 複查：ADR-XPLAT-005 檔頭仍為 `Proposed（R81）`，檔自 2026-08-16 未動→仍成立） | 2026-10-09 |

## 登記備注

> 遷入時主帳本各列的狀態欄已改寫為 `closed-by-decision｜移入結構性長債軌（<token>）…`
> 索引句；改寫前的狀態欄原文由主帳本 git 史保全（本批遷軌**只改狀態欄與分流去向欄的
> 殘留待辦用語**，發現情境／現象與證據欄一字未動）。
>
> - **DEF-101-701 自 R89 起吸收 DEF-101-746**（兩列自 R81 起載明「合併承接」，701 為
>   單一載體；746 原文逐字保全於 `CrossPlatform_R89_Closure_Evidence.md` §DEF-101-746）。
>   本表 701 列解鎖條件中的「MIN_TESTS 重釘路徑存在指紋一致性斷言」即同時承接 746 併入
>   的「重釘判準寫成可注入紅綠」條件。
> - （史料）**DEF-101-886 自 R82 起吸收 DEF-101-214／217**（併發污染方法論，同一根因）；其
>   解鎖條件②（共用樹序列化規則機械化）即本表該列的解鎖條件。

## 複查記錄

> 「最近複查日」欄僅存放純 ISO 日期；解鎖條件達成而移出本表的列，其複查敘事逐字搬遷至本節（體例同外部阻塞軌）。

### DEF-101-886（複查 2026-10-09＝解鎖條件達成，列已移出本表）

複查：條件於 2026-09-01 掌舵者循環令 D3 具名裁決（檢查表形態）成立並落地——根 CLAUDE.md〈並行派工防互踩檢查表〉
四格條款＋`tools/tests/test_doc_loc_baseline_freshness_r60.py` 的 `dispatch_checklist_problems()` 節內判準規則鎖；
2026-10-09 現查兩者皆在（CLAUDE.md 檢查表節；該測試檔 `TestParallelDispatchChecklistIsPinnedInClaudeMd`）。主列
（`AutoSDD_Defect_Log_archive_68.md`）狀態「closed-by-decision｜移入結構性長債軌」為歷史事實不改。本表筆數 7→6；
成長棘輪 `_STRUCTURAL_DEBT_MAX_ROWS` 為上限、不隨之下修。
