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
| DEF-101-960 | 結構性長債-SDD樹win32-skip剖面未接census | 2026-08-30 | ①（任何平台可做）`AISDLC_SDD/scripts/ci-gate.sh`／`.ps1` 把 SDD fsm_runtime 的 pytest `-rs` 輸出接進 census（現況：全 repo 只有 `AutoClaude/tools/local_ci_gate.py` 與 `tools/run_root_unittests.py` 會印 `[skip census]`，`ci-gate.sh:215-220` tee 後只取通過數；DEV-K 2026-10-13 現查三份 Windows CI log 零命中）；②Windows 執行者（實體機或 `windows-compat-ci`）跑出 `[skip census] AISDLC_SDD/fsm_runtime@win32` 六格；③同 commit 逐格照抄進 `_RUNTIME_SKIP_CEILING`／`_RUNTIME_SKIP_CEILING_MAX` 並自 `_UNMEASURED_RUNNER_PROFILES` 刪該鍵（`python tools/lib/skip_group_policy.py` 現查）。linux 半邊（`AutoClaude/tests@linux+nopg+solo+nopgext`）已於 2026-10-13 以 Docker 容器量到並登記（R213 證據檔〈十-3〉DEV-H）。 | 2026-10-13 |
| DEF-200-075 | 結構性長債-mac-nightly無PG剖面 | 2026-10-13 | mac nightly（`tools/run_local_nightly.sh`）以 docker compose（`docker-compose.ci.yml`）起 PG17 並 `alembic upgrade head` 後，`[skip census] AutoClaude/tests@darwin+pg+…` 剖面登記且欠債型 ≤ 10（對照 win32+pg 剖面 5）；或掌舵者裁決 mac 側不接 PG 並把該 103 支的 PG 契約測試改掛 `[ENV-DISABLED]` 標籤納入天花板（原外部軌列文見 AutoSDD_External_Blocked_Log.md〈複查記錄〉DEF-200-075 節） | 2026-10-13 |

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

### DEF-101-702（複查 2026-10-13＝解鎖條件達成，列已移出本表）

複查：`docs/06_quality/CrossPlatform_R68_Scan_Findings.md`「狀態@R69」欄 open／partial 計數＝0（2026-10-13 主控以列首詞普查：
原 open 23＋partial 5＋partial@R69 1＝29 列，逐列現判 fixed@HEAD 10／fixed@R213 8（DEV-C 2、DEV-D 1、DEV-F 3、主控 2）／
closed-by-decision@R213 11；逐列座標與理由＝R213 證據檔附錄 D（DEV-C 提案表逐字）＋〈十-3〉；R68-04 的 Windows 側 smoke step
已補但未在 Windows 實跑、R68-37 餘 3 處 AutoClaude 樹行內複本由 per-tree 棘輪凍結（3，只准往下）、另 13 支帶 `__main__` 的 CLI 由 `_UNPROTECTED_CLIS` shrink-only 凍結，皆如實登記）。本表筆數 2→1。

### DEF-101-018（複查 2026-10-13＝解鎖條件達成，列已移出本表）

複查：repo 根 `.venv/bin/ruff check . 2>&1 | tail -1` 於 2026-10-13 印 `All checks passed!`（ruff 0.15.21；解鎖條件字面
「Found 0 errors.」是舊版輸出字樣，以實際輸出為準）——AutoClaude 657→0、`AISDLC_SDD_v0.30` 96→0、根 `tools/` 維持 0；
凍結版 v0.01～v0.29 由新增 repo 根 `ruff.toml`（只做 `extend-exclude`、不選規則）排除——掌舵者裁決凍結版不可編輯，排除面
只含凍結版由 `AISDLC_SDD/scripts/tests/test_ruff_root_config_excludes_only_frozen.py` 守（LATEST 前進未補清單即紅）；
`ruff check AutoClaude／tools／AISDLC_SDD_v0.30 --statistics` 加根檔前後逐字相同；AutoClaude 全套 5451 通過／156 略過
rc=0、lint-imports 9 kept、v0.30 pytest 1979 通過 rc=0、`ci-gate.sh` rc=0〔他包回報：R213 DEV-D，證據檔〈十〉〕。本表筆數 4→3。

### DEF-101-398（複查 2026-10-13＝解鎖條件達成，列已移出本表）

複查：2026-10-13 `tools/lib/bootstrap_lock.py`（370 行）與 `tools/lib/nightly_heartbeat.py`（308 行）已存在，
`tools/dev_start.py` 1951→1411 行（`check_loc_budget.py --json` 現查），`SPECIAL_FILES` 門檻 1952→1411（只准往下）；
`test_dev_start` 拆分前後皆 286 項 OK、HEAD 對現行差分比對 367 項 0 不一致、三種突變皆被抓到〔他包回報：R213 DEV-C，
證據檔〈十〉〕；Windows bootstrap 路徑未在 Windows 實跑（本輪 mac）。本表筆數 3→2。

### DEF-101-701（複查 2026-10-13＝解鎖條件達成，列已移出本表）

複查：前半「headroom>0」於 2026-10-13 達成——`tools/run_root_unittests.py` 檔頭 15 行史料搬至
`CrossPlatform_R213_DebtZero_FourParty_Evidence.md`〈附錄 A-1〉，loc 777→763；`AutoClaude/tools/check_loc_budget.py`
`SPECIAL_FILES` 門檻 777→765（只准往下）⇒ `check_loc_budget` 現查 `[special<=765] ../tools/run_root_unittests.py: 763
（餘裕 2 行）`、rc=0；後半（`min_tests_note_stale_tokens()` fail-fast）2026-09-01 已達成。AND 整體解鎖。本表筆數 6→5。

### DEF-101-980（複查 2026-10-13＝解鎖條件達成，列已移出本表）

複查：`docs/04_planning/ADR/ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md` 檔頭狀態行 2026-10-13 由
`Proposed（R81）` 改為 `Accepted（2026-10-13；…）`，依據＝§5 機械物 M1～M14 於 HEAD 逐列現查（M8 `relay_machine.py::
SOURCE_AUTHORITATIVE`、M10 `config.py` `quota_throttle_pct`／`quota_halt_pct`、M11 `.importlinter` `root_packages` 含 `tools`
＋Rule 9；其餘指名測試類各命中），見 R213 證據檔〈三-3〉。本表筆數 5→4。

### DEF-101-886（複查 2026-10-09＝解鎖條件達成，列已移出本表）

複查：條件於 2026-09-01 掌舵者循環令 D3 具名裁決（檢查表形態）成立並落地——根 CLAUDE.md〈並行派工防互踩檢查表〉
四格條款＋`tools/tests/test_doc_loc_baseline_freshness_r60.py` 的 `dispatch_checklist_problems()` 節內判準規則鎖；
2026-10-09 現查兩者皆在（CLAUDE.md 檢查表節；該測試檔 `TestParallelDispatchChecklistIsPinnedInClaudeMd`）。主列
（`AutoSDD_Defect_Log_archive_68.md`）狀態「closed-by-decision｜移入結構性長債軌」為歷史事實不改。本表筆數 7→6；
成長棘輪 `_STRUCTURAL_DEBT_MAX_ROWS` 為上限、不隨之下修。
