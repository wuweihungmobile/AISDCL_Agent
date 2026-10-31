# SCG-4 PR Review 報告 — 議題中心（Issue Center）階段一＋二（PRD v1.0 FR-IC-01～12；鍵 `monorepo-issue-center`／`agentconsole-issue-center`）

**審查日期**: 2026-10-27（一審 09:39～11:30；二審見〈審查歷程〉）　**審查者**: SCG-4 獨立 QA（Sonnet 5.5，唯讀；未參與規格撰寫與實作——規格作者＝SA 棒、實作者＝根層與 Console 兩支 Developer 棒＋修復棒，皆不同代理）　**主控親驗**: 2026-10-27 11:4x（根層三檔 unittest、`si check`、`si issues --status 待處理`、五個突變在副本重放）；修復棒後與真機段見 §E、§F
**審查範圍**: 實作 commit `488d8e66`（`7928b962..488d8e66`，96 檔）。根層半：`tools/lib/selfimproving/{issuemap,issues,issues_items}.py`、`tools/selfimproving.py` 的 `issues` 動詞與 `export --kind issues`、`tools/tests/test_selfimproving_issues.py`／`test_selfimproving_issuemap.py`、§5.7 同步鎖。Console 半：Bridge `GET /si/issues`（`app/si_cli.py`、`routers/si.py`、`tests/test_si_issues.py`）、backend 四端點＋Flyway `V14__issue_priority.sql`（`Issue*`、`IssuePriorityAdapter`、安全規則、OpenAPI 計數）、frontend 「議題中心」四分頁（`components/domain/issues/**`、`lib/domain/issues.ts`、導覽登記表）、`docs/02_architecture/API_Contract_IssueCenter.md`。
**基準規格**: `docs/01_requirements/Issue_Center_PRD.md` v1.0（Stage-1 `sha256:a162a104…`；AC 90）；`docs/03_testing/contracts/TCS-IssueCenter-20261027.md`（Stage-2 `sha256:bc6a9493…6fba`；R-IC-01～75、AT 223＝正向 121／反向 102、載具 §3.1、閘門 G-R／G-B／G-K／G-F／G-C）。
**判決檔（逐字）**: 一審交卷全文＝主控 scratchpad `qa_scg4_report_r1.md`（本 session `c61e3847`）；突變規格檔 `spec_*.py`、執行器 `mutate.py`／`mutate_seq.py`、逐 R 核對 `r_vs_listed.py`、閘門 log `gates\` 同目錄；本檔為入庫摘要，數字皆為審查者、修復棒或主控當回合親跑。

### 審查歷程

| 輪 | 判決 | P1／P2／P3／P4 | 處置 |
|----|------|----------------|------|
| 一審 | FAIL（通過條件 7「無 P1、P2 未結」不成立） | 0／9／3／1 組 | P2 全屬「PRD／TCS 明文的邊界或值沒被斷言（突變倖存）」「TCS 所列 AT 殺不到該條突變」「規格漏項」「越出 §5.7 的檔」；實作邏輯一處都不用改。主控親驗後派兩支修復棒（根層＝Q-01～04、07、08、10；Console＝Q-05、06、11、12；皆只補斷言）＋ TCS 勘誤一（1-1～1-5 對應 ⚖(a)～(d) 與 Q-09）＋ PRD 勘誤一（§9 落點表補 `issues_items.py`） |
| 二審 | PASS（12:40～12:58；同一位 QA 唯讀） | 0／0／1／4 | 一審 Q-01～Q-12 全數閉合：被改 AT 整檔重跑全綠（根層 issues 104 OK、export_status 15 OK；frontend 19 檔 382 個全綠；backend `cleanTest test --tests *Issue*` 53 成功；Bridge `test_si_issues` 12 通過）；一審倖存突變在副本重放 38 次＝37 KILLED＋1 對照（C11 只跑 RX 04-6 仍倖存、不要求），restored 38／FAIL 0；G-C5 被刪 assert 0；G-C1 相減快照後 10 筆皆 §5.7 或主控文件；Architecture.md 唯一 hunk＝§7.2 一列；勘誤一 1-1～1-12、PRD P-1～P-3 逐條對 Q／⚖ 與實測相符、PRD digest 與 `Get-FileHash` 逐字同。P3＝Q2-1（勘誤 1-6 位置欄漏 D-C11 :142、§5.7 :1166 與 Console 表、PRD §9 :404）；P4＝Q2-2（Console 棒自述「未加函式」實加 1 個 `it`）、Q2-3（1-1／P-2 漏 `capability:4`、`:647-648`）、Q2-4（勘誤標題引的新 digest 待 refreeze 後補）、Q2-5（P-1 WHY 引了 PRD 沒有的字句）。主控於放行前補齊 Q2-1／Q2-3／Q2-5（勘誤 1-1、1-6、P-1～P-3 修字），Q2-4 於 refreeze 後補 digest |

### A. 一審站得住的部分（審查者數字）
- PRD 90 AC 與 TCS §1 的 90 列一一對上；每條 AC 正向與反向各 ≥1 個 AT；§1 引用的 223 個 AT＝§3.2 的 223 列。
- 215 個非審查閘 AT 各有對應測試函式，載具分佈與 §3.1 逐格相同（RI 104、RM 7、RX 4、BR 8、BU 1、BI 26、BM 2、BA 2、BB 2、BC 1、BS 3、FL 7、FV 28、FD 3、FP 3、FG 2、FS 6、FN 3、E2 1、ES 2）；無錯載具、無多餘測試、無 skip／xfail／空斷言；8 個審查閘 AT（GT）以 G 指令輸出為證。
- R-IC-01～75 每條至少一個突變轉紅（223 次副本執行全部位元組還原 OK）。
- 四道差分（Bridge↔CLI、console-api↔黃金檔、`issues --json`↔`export`、`rollback_pending`↔議題）皆綠；G-C1～G-C6 除 Q-09 外全過。
- 真帳本可讀性（PRD §11 階段一 (a) 的機械面）：`issues` rc 0、376 ms、全繁中；`--status 待處理` 2 件（PROP-SI-004、PROP-SI-005 皆「觀察中」）；`--status 待您決定` 0 件，與 `si status` 一致；三問（等我決定／進行中／已結案）不看英文可答。

### B. 發現清單（一審；級別＝P2 規格明文未被斷言或所列 AT 殺不到／P3 次要守衛或過期註解／P4 建議）

| Q | 級 | 座標 | 問題 | 處置 |
|---|---|---|---|---|
| Q-01 | P2 | `test_selfimproving_issues.py:1471-1495`（AT-IC-05-3-E-1）←→ `issues.py:134`、`issues_items.py:234` | TCS 明列「孤列＝3S 或 4S＋行號」，只釘 3S；結構缺陷孤列 4S 無斷言（突變 X1 倖存）；提案號＝S 邊界亦倖存（U1） | 根層修復棒補 since＝4S＋行號±0 兩向與 PROP 號＝S 例 |
| Q-02 | P2 | 同檔 :1421-1441（AT-IC-05-2-1）←→ `issues.py:248` | 「truncated＝符合者多於上限」：30 件／limit 7 不整除，`>`→`>=` 倖存（Y8） | 補整除夾具 28 件／limit 7（末頁 truncated＝false、next_since＝null） |
| Q-03 | P2 | 同檔 :1058-1073（AT-IC-04-3-1）←→ `issues_items.py:87` | R-IC-23 恰 80 code point 不加「…」無斷言（Z2 倖存） | 補恰 80／81 兩例 |
| Q-04 | P2 | `issues_items.py:171`；PRD §5.2 :194；TCS R-IC-31 | PRD 明寫「姊妹軌解鎖條件截 40 字」，TCS R-IC-31 漏載、無 AT（U2 倖存） | 修復棒於 AT-IC-04-1-1 補 ≥41 code point 夾具；TCS 勘誤一補 R-IC-31／AT-IC-04-1-1 字句 |
| Q-05 | P2 | `lib/domain/issues.ts:95-98`；`IssuesView.test.tsx:170-185`（AT-IC-05-7-1） | 「置頂列其內依第一條」未被斷言：置頂群改用第二條（D1）90 個前端測試全綠 | Console 修復棒重設夾具使兩條規則次序相反並斷言 |
| Q-06 | P2 | `IssuePriorityAdapter.java:47-49`；`IssueApiIT.java:760-773`（AT-IC-09-7-1） | 「setBy、setAt 為後者」：UPSERT 少更新 `set_at`（J1）仍全綠——測試只比回應本文（service 時鐘） | 修復棒以 `priorityRows()` 讀資料庫列 `set_at` 斷言 |
| Q-07 | P2 | `issues.py:300`、`tools/selfimproving.py:283`（R-IC-34） | 文字表選規則 `all`→`any`（U6）全倖存；`--json` 也套顯示序（D5）只被 06-2-1 殺、所列 05-1／05-6 殺不到 | 修復棒於 AT-IC-05-6-1 補混合 `--status` 文字表序＋`--json` 游標序斷言 |
| Q-08 | P2 | TCS R-IC-20／29／42 的 AT 欄；`test_selfimproving_export_status.py:828-838`（AT-IC-06-2-1） | 所列 AT 殺不到該條突變：R-IC-20「approved 歸待您決定」（實際殺手 03-6-E-1）；R-IC-29「raw 截斷」（實際殺手 04-3-1）；R-IC-42「items 依雜湊序」（06-2-1 兩次執行同行程、雜湊種子相同；實際殺手 05-2／05-3／05-4／05-6／12-1-E-1） | 修復棒在所列 AT 補斷言（R-IC-42 仿 `test_AT_140_2_E_1` 以不同 `PYTHONHASHSEED` 子行程差分）；載具結構上不可能者勘誤 AT 欄 |
| Q-09 | P2（範圍） | `tools/lib/selfimproving/issues_items.py`（新檔 330 行）不在 TCS §5.7 | G-C1 唯一殘餘 | ⚖(a)：規格勘誤（TCS 1-1／1-2、PRD P-1／P-2），實作不改 |
| Q-10 | P3 | 根層 `issues` 匯出形狀無絕對釘 | schema_rev／kind／頂層鍵序／議題鍵序／generated_at 去 offset 在根層 126 個測試全倖存（Bridge 殺到 schema_rev 與 kind） | 修復棒加一個仿 `test_AT_132_5_1` 的形狀測試 |
| Q-11 | P3 | backend `IssueQueryService`（since／limit）、Bridge `routers/si.py`（ge=0／ge=1） | 接受側邊界無 AT：`since=0`、`limit=1` 應 200 | 修復棒於 AT-IC-07-4-E-1（backend、Bridge）補；TCS 勘誤補句 |
| Q-12 | P3 | `IssuesView.tsx:208` | 註解寫「決定鈕停用」，實作是 aria-busy＋改字（⚖(e) 實作對） | 修復棒改註解 |
| Q-13 | P4 | 一組建議（提示條對象上限 5、篩選殘值跨分頁、自連結、多筆 close 取最後、`_LEAD_SEP` 跨模組私有名、legend 釋義少一句等） | 皆實務等價或 PRD 未規定 | 登記不改；候選入下一輪 T1 |

### C. ⚖ 裁決（審查者對證據；主控採納）
- (a) 第三支檔 `issues_items.py` 與 `CAPABILITY` 50→51：規格勘誤、實作不改（LOC 分級：311＋330 行併一支必越 400；注入縫全在 `issues.py`；靜態詞表鎖已掃兩支）。
- (b) AT-IC-07-2-2「含空白 source→200」vs B-05 503：規格勘誤（含空白不是合法來源名，全鏈正確行為 503；`issues-docker.stack.ts` 已依此）。
- (c) cause `output_too_large`→`stdout_too_large`：規格筆誤（Bridge 既有字面、RTM AT-932-3-E-3 已凍結）。
- (d) AT-IC-04-2-E-2 整檔 assertNotIn：規格文字勘誤（根層鎖禁整檔 haystack 缺席斷言；實作逐行字面＋AST）。
- (e) 「決定」鈕取快照期間不停用、只標 aria-busy：實作對、TCS 不改（R-IC-74／AT-IC-12-5-1 要求焦點歸還，停用會讓焦點掉出）。
- 勘誤路由：(a)(d)＋Q-04／Q-08 根層半、(b)(c)＋Q-11 Console 半 ⇒ 跨兩半，依 TCS〈凍結後修訂路由〉3：`monorepo-issue-center` 先 refreeze、`agentconsole-issue-center` 引同條號 refreeze，兩鍵 digest 必須相同；PRD §9 走第 4 點。

### D. 一審閘門數字（審查者本場自跑，PowerShell 序列、根 .venv；rc 先存檔再讀）
| 閘 | 結果 |
|---|---|
| G-R1～G-R4 | issues 104 OK（26.8 s）、issuemap 7 OK、p3_meta 10 OK、export_status 15 OK |
| G-R5 | `test_selfimproving_*.py` 540 OK（1269 s） |
| G-R6／G-R7／G-R8 | ruff All checks passed（rc 0）兩次；`si check` overall=PASS rc 0（33 項） |
| G-R9／G-R10 | `issues`／`--json` rc 0、376～394 ms（真帳本 597 筆，首頁 500）；獨立算法對帳 EQUAL：總數 597＝已完成 544＋延後 51＋觀察中 2＋待您決定 0；problems 0、ne 0 |
| G-R11～G-R14 | LOC 無違規（issuemap 321／issues 311／issues_items 330）；ci_paths 49 通過；module_layout 9 OK；params.json 無差異 |
| G-B1～G-B3 | ruff 兩視角 rc 0；pytest 序列 rc 0（通過 1249、略過 24，586 s；`-n auto` 在本機 20 核紅的 9～13 個全是既有 E2E 引擎 run、無 `test_si_*`，序列重跑綠）；黃金檔重產兩次 10 檔 same、副本位元組相同 |
| G-K1／G-K2 | `gradlew clean build` BUILD SUCCESSFUL（2m 21s；XML 彙總 2076 個測試、0 失敗）；`--tests *Issue*` 53 成功 0 失敗 0 略過 |
| G-F1～G-F4 | lint＋prettier OK；tsc rc 0；`test:cov` 88 檔 1508 個全綠，`lib/domain/issues.ts` 100／99.25／100／100；build rc 0 |
| G-F5／G-F6 | `issues.mock.spec.ts` 1 通過；`shells-and-layout.spec.ts` 需真後端（ECONNREFUSED）歸 SCG-5；G-F6 需全棧（§F） |
| G-C1～G-C6 | 變更檔 ⊆ §5.7（唯一例外 Q-09）；docs/06_quality 與七本帳零差異；`reasons.ts`／`API_Contract_P3-6.md`／`Architecture.md` 零輸出（負控非空）；既有測試 hunk 無被刪 assert；守衛面零差異 |

**主控親驗（2026-10-27 11:4x，根 .venv）**：`test_selfimproving_issues.py` Ran 104 OK、`issuemap` 7 OK、`export_status` 15 OK（rc 皆 0）；`si check` overall=PASS rc 0；`issues --status 待處理` rc 0 共 2 件問題 0 筆；副本重放 `Y8` SURVIVED(ran 12)、`C2` KILLED(ran 1)、`Z2`／`U2`／`U6` 整檔跑唯一紅＝副本缺 `.git` 的 `test_AT_IC_06_4_1`（即倖存），五次 restored=OK，副本三支生產檔 sha256 與工作樹相同。

### E. 二審（修復棒後；審查者以同一套 spec 檔對副本重放；判決檔逐字＝同一子代理逐字稿、log 在 scratchpad `r2_logs\`）
- **修復棒成品**（主控親驗：`git diff --stat` 與 `-U0` 刪除行、整檔重跑、副本重放）：根層 `test_selfimproving_issues.py` +111、`test_selfimproving_export_status.py` +71（0 刪除；Ran 104 OK、Ran 15 OK；E501 ≤100 無輸出；主控重放 Y8 KILLED(ran 12)、D5 KILLED(ran 12)、V42b@own KILLED(ran 1)、X1 KILLED(ran 104；FAIL＝`test_AT_IC_05_3_E_1` 加基線紅 06-4-1）；生產碼 `tools/lib`、`tools/selfimproving.py` diff 空）；Console `IssuesView.test.tsx` +31（AT_IC_05_7_1 加一個 `it`，夾具讓兩條規則對置頂列次序相反）、`IssueApiIT.java` +39（`priorityRows()` 多讀 `set_at`、`awaitClockPast` 有界輪詢、AT_IC_09_7_1 斷言資料庫列 `set_at`）、`test_si_issues.py` +4（`--since 0`、`--limit 1` 兩案）、`IssuesView.tsx:208` 一行註解（主控 `-U0` 核對只此一行；vitest 19 檔 382 個全綠；`cleanTest test --tests *Issue*` 53 成功；pytest 12 通過；主控重放 D1 KILLED，失敗者＝新增的 AT_IC_05_7_1）。
- **審查者重放（副本；逐一套用→判定→逐位元還原；基線紅 06-4-1 剔除）**：X1、U1（05-3-E-1）；Y8（05-2-1）；Z2（04-3-1）；U2（04-1-1）；U6、D5（05-6-1；D5 整檔另被 06-2-1 殺）；B6 所列 01-2／03-4／04-10（04-10-1）；C11 所列 04-7（04-7-1、04-7-E-1）；V42a、V42b 外層 `PYTHONHASHSEED` 0～3 共 8／8（06-2-1 子行程差分）；S1 兩版、S3～S6 兩族、U9 兩族（05-4-1；04-6-1、04-6-E-1）；D1（05-7-1 新 `it`）；J1（09-7-1）；B4a（07-1-1、06-1-2）、B4b（07-1-1）；J5、J6（07-4-E-1）。副本 597 個生產檔與 HEAD 逐檔 sha256 相同。
- **同步鎖與加跑**：G-R3 p3_meta 10 OK；G-R13 module_layout 9 OK；G-R8 `si check` PASS（fingerprint 與一審同值）；ruff／E501／prettier／eslint／tsc rc 0；`tools/check_pytest_baseline_sites.py` rc 0（Architecture.md 新列不觸發）。
- **二審未涵蓋（誠實）**：全量回歸（G-R5、G-B2、G-K1、G-F3、G-R12）只跑被改檔所在 suite；G-R15（`run_root_unittests.py`）留收尾單人窗口（重釘後主控跑）；兩把 issue-center 鍵的 refreeze 由主控做（§H）；AT-IC-12-2-1 的 macOS／Linux 側由 CI（macos-compat-ci）承接。

### F. SCG-5 真機（Docker 全棧；PRD §11 出口 (a) 由掌舵者親驗）
- 全棧以本輪實作重建（2026-10-27 11:5x，`docker compose --profile db --profile app --profile full up -d --build` rc 0；`aisdlc-frontend`／`aisdlc-backend`／`aisdlc-engine-bridge` 三個映像為新建、全部 healthy；Bridge 以唯讀 bind 掛工作樹 `tools/`、`docs/06_quality/`，帳本改動不需重建）。
- **AT-IC-07-2-2**（主控親跑，`npx playwright test -c tests/e2e/docker.config.ts -g "AT_IC_07_2_2"`，`E2E_API_URL=http://localhost`）：rc 0、`1 passed (3.7s)`；輸出「全部 597 件；篩選（待處理、待您決定／使用者提案、系統缺陷）1 件；含空白的 source＝503 si_unavailable」（勘誤一 1-3 語意）。
- **AT-IC-09-6-2**（同法 `-g "AT_IC_09_6_2"`）：**前置未成立**——rc 1，判定式於 `issues-docker.stack.ts:90` 大聲失敗：「全棧的帳本沒有任何可排的議題（待您決定、待解、進行中）：無法驗證順位的持久性——請先讓帳本有一筆可排的議題」。真帳本此刻 604 件＝候選 1（OBS-SI-329 open）、觀察中 2（PROP-SI-004／005，不可排）、延後 51、已完成 550；候選不可排（PRD §4／R-IC-28）、缺陷帳本零未結列、無 proposed／verified／approved 提案。主控刻意**不**為了過 AT 而開假缺陷或假提案（缺陷帳本另有淨額棘輪：本輪新增未結不得多於結案，逃生口只准掌舵者決定）。處置＝待真帳本出現可排議題時重跑此 AT（OBS-SI-333）；PRD §11 階段二 (d) 本輪只有 backend `IssueApiIT`（Testcontainers 真 PG，順位 UPSERT 與資料庫列 `set_at`）與 Flyway V14 的證據，容器重啟後持久性尚未真機驗。
- **掌舵者真機走查（PRD §11 階段一 (a)、階段二 (a)～(c)）**：待掌舵者開 `http://localhost` 左列「議題中心」四分頁、狀態說明、篩選；設一次順位同樣受上項限制（無可排議題時「排序」鈕不會出現）。完成後由主控把 sid＋line 補進本節並 `transition --to RELEASE`。

- **放行紀錄（2026-10-31）**：掌舵者於互動視窗裁示「放行」（sid `655d9777-cfd0-4478-b2b3-b8245313b24c` line 4067），上項真機走查免做；兩鍵轉 RELEASE，見 §H。

### H. 凍結與放行紀錄
- 兩鍵 `monorepo-issue-center`／`agentconsole-issue-center`：2026-10-27 13:1x `transition --to PR_REVIEW` → `gate PR_REVIEW PASS` → `gate RTM_VERIFY PASS`（RTM `docs/06_quality/RTM-IssueCenter-20261027.md` 根層 116 AT、`AgentConsole/docs/06_quality/RTM.md` §2.4 Console 107 AT）→ RELEASE_READY → `spec-refreeze`（TCS 勘誤一 1-1～1-12、PRD 勘誤一 P-1～P-3）。兩鍵 digest 相同：TCS `sha256:9cd3286051ecda44c12187334954e944024135a275bb9393fdbd44d74850412d`、PRD `sha256:9765a825973f75722b79268dd827047a712a6db6a694f62f31e9fb90655a9eba`（Stage-2 原值 TCS `bc6a9493…`、Stage-1 PRD `a162a104…`）。
- 兩把 SI 鍵 `agentconsole-si-mirror`／`agentconsole-si-decide` 同日 refreeze（Architecture §7.2 加 `issue_priority` 列；Architecture 新 digest `sha256:dbdbd5f97d4bbfea91b5877ae121c36471455e4a0154d046e84b3261781c3ac5`，兩鍵相同）。
- `transition --to RELEASE`：2026-10-31 掌舵者互動放行（sid `655d9777-cfd0-4478-b2b3-b8245313b24c` line 4067，原文「放行」；§F 的真機走查由掌舵者裁示免做）；主控對兩鍵 `agentconsole-issue-center`／`monorepo-issue-center` 執行 `transition --to RELEASE` 皆 rc 0，`show` 現為 RELEASE。

### G. 流程摩擦（審查者八項；主控處置）
1. 任務書原寫「在工作樹突變」與 TCS :678（匯出副本）衝突——主控中途更正；副本三個坑（不含 AISDLC_SDD 須單補 `scripts`、無 `.git` 使 06-4-1 恆紅、node_modules 以 junction 指回工作樹）⇒ 入觀察帳本。
2. 批次突變互相污染（Java 共用路徑誤殺；Python `-k` 子集在基線紅下整檔一律 KILLED）⇒ 逐一跑＋基線感知器；入觀察帳本。
3. 審查者自己兩次重疊（`-n auto` 與突變同跑；排隊等待條件寫錯）——受影響結果已用乾淨重跑取代。
4. Bridge `-n auto` 在本機 20 核紅既有 E2E 引擎 run；TCS 閘門用序列，與根 CLAUDE.md「CI 一律多 CPU」形態不同 ⇒ 入觀察帳本另案。
5. TCS 把只能對真後端跑的 `shells-and-layout.spec.ts` 放進 G-F5 ⇒ 勘誤移到 SCG-5 清單。
6. R 條文「突變欄／AT 欄」未被機械驗證過（Q-08）⇒ 開發棒交卷前自跑「所列 AT 是否轉紅」；入觀察帳本。
7. Windows 的 Bash 工具被 hook 擋下（預期）。
