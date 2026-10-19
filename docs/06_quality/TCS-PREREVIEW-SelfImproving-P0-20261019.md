# TCS 預審報告 — SelfImproving P0（SCG-0～3 規格閘預審；FSM 功能鍵 `monorepo-si-p0-ledger`）

| 項目 | 內容 |
|---|---|
| 受審物 | `docs/03_testing/contracts/TCS-SelfImproving-P0-20261019.md`（一審版：1377 行／162,566 bytes，untracked 工作樹版；FRD-lite 與 TCS 同檔，SA 棒撰寫；二審版：HEAD `407c945b` 的同檔，1468 行／178,931 bytes，見 §6.1） |
| 輸入快照 | 一審：HEAD＝`64f2fc0f`（`git rev-parse` rc＝0）；工作樹 ` M`：PRD（僅 PRD:975 一行）、QA 報告、觀察帳本；`??` 本 TCS。PRD 的 HEAD blob＝`8d2d5ef0` blob＝`a27bba61…`（即 TCS 所引凍結摘要）；SOP 同為 `deb9716b…`。二審快照見 §6.1 |
| 審查者 | QA 棒（Sonnet 5.5；未參與 TCS 撰寫；唯讀：未改受審物、無 git 寫入、未派子代理、未跑 FSM CLI、未用 Bash）；AutoClaude 編譯器只在記憶體內乾跑、未寫檔 |
| 判定 | 一審 **FAIL**（P1＝0、P2＝1、P3＝9、P4＝5）→ 二審 **PASS**（P1＝0、P2＝0；F-01～F-10 全消除、F-11～F-15 已登記；二審新增 P3×4＝N-01～N-04，見 §6；口徑＝無 P≤2 才 PASS）。一審唯一 P2＝F-01（草稿列分類與凍結 PRD 三處衝突）已消 |

## 1. 判準逐項結果

| # | 判準 | 結果 | 證據 |
|---|---|---|---|
| 1 | 範圍對齊凍結 PRD | **FAIL**（F-01；其餘符合） | TCS 只做 §9.6 P0（PRD:718）——C1 遷移、C5、C4 的 `check`、C6 草稿；13 個 PRD AC（AC-SI-01-1～01-3、02-1～02-2、03-1～03-3、04-1～04-3、29-1～29-2）與 PRD:243～259、:390～391 逐條同集合（FR-SI-01～04、29 在 PRD 恰此 13 條）；`status`／`prop-new` 一律 rc 3、事件帳本不重放，無 P1 以後內容；自增 AC-030-1／2／3、031-1／2、032-1 的來源可追到 PRD §9.3 `check` 列（PRD:635）、§9.4 草稿列（:676）、C5（:566）、C6（:567）、NFR-SI-08-1（:447）、NFR-SI-09-1／3（:450、:452）；與 PRD 衝突＝F-01，超出 PRD 明文的類推＝F-09；PRD 的 UPPER_SNAKE 初值參數 16 個全在 R21、初值逐項與 PRD 相符（§3 Q4） |
| 2 | AT 文法與編譯相容 | **PASS**（附 F-03） | 用 AutoClaude 既有 `SddToPlaybookAdapter`（`sdd_compile` 的解析核心）在記憶體內乾跑（CLI 需 `--out` 寫檔、`load_spec` 需凍結狀態檔，故略過；凍結閘與摘要綁定「未驗」）：規格格式版 1.0、場景 brownfield、編成 39 個 AT、`unmapped_at_ids` 為空；§1 的 AT 集合＝gherkin 標頭集合（39／39）；每個 gherkin 圍欄首行恰為 `# AT-…`；AC 與 AT 前兩段 0 不一致；E 類 19 個全合 `AT-NNN-Y-E-n`；`compile_tasks` 出 39 步、`Playbook.model_validate` 通過、step_id 唯一；副作用：8 個 AT 的 expected_output_regex 多出必含字面（F-03） |
| 3 | 可測性、hermetic、跨平台、流程型代位 | **PASS**（附 F-02、F-08、F-10） | 39 個 AT 皆為 Given／When／Then 的可觀測集合斷言（`F(項目)` 集合相等、rc、位元組、detail 字樣）；16 個用 tmp 內真 git、23 個為解析層或文件層；全用 tmp 合成 repo 與 §5.5 淨化環境（移除 `GIT_*`、`GIT_CONFIG_GLOBAL` 指空檔、gpgsign／autocrlf 關閉、git 缺席直接失敗不 skip）；真檔只唯讀；無網路；路徑一律 `Path`、CRLF 情境以位元組寫；流程型 AC（AC-002-1 後半、003-1／-3、004-2、029-1／-2）的代位逐條標「流程型／SOP 條文代位／V8 文件檢核」並以「刪去副本須判不合格」自證，標示誠實；缺口：F-02（R9 歧義使一個期望集合不可得）、F-08（7 項規則無 AT）、F-10（單一 AT 含最多 26 個子情境） |
| 4 | 覆蓋 | **PASS** | 19 個 AC 各 ≥1 AT（§1 覆蓋 100%，AT 數 39＝§1＝§3 的 23＋16）；12 項邊界皆有 AT：缺 tz（AT-001-1-E-1）、非法枚舉（E-3）、控制字元與超 700 bytes（E-5）、`fixed@` 壞 sha（E-6）、懸空 OBS（AT-004-1-E-1）、`migration_base_sha` 非祖先（AT-001-3-E-3 (e)）、params 缺鍵（AT-031-1-E-1）、glob 與 PRD 不一致（AT-031-1-E-2）、`w_opp<w_min`（AT-031-1-E-3）、遷移後原地改寫（AT-004-3-E-1）、open→終值一次放行（AT-004-3-1） |
| 5 | Q1～Q5 預設 | **PASS**（附 F-06） | 見 §3；無隱藏 P2 |
| 6 | 實作可行性 | **PASS**（附 F-04） | ROW-MUTATED：真 repo 上 `git log --first-parent --reverse -- <帳本>` 8 個 commit（0.05 秒），逐版 `git show` 後依 R20 逐對比較可算（真歷史上 16 個 OBS ID 曾被原地改寫，故必須以 `migration_base_sha` 為界，設計正確）；`git grep --untracked` 兩次各約 0.6 秒（NFR-P0-2 的 30 秒預算寬裕）；R22 依規則逐字實作對真 PRD:415 與根 CLAUDE.md:81 重算 **18＋7＝25、去重 25**（誘餌 7 個皆被排除，與 SA 相符）；R24 的 PRD 指標列 PRD:61～65、判定細則區段 PRD:69～78（9 個非空行）穩定；真帳本預演（§4）：P0 退出 (b) 依規則可達（前提：M、N 正確且 F-04 處理） |

## 2. 發現清單（編號獨立於 SCG-0 報告）

| 編號 | 嚴重度 | 位置 | 症狀（附證據） | 修法 | 誰修 |
|---|---|---|---|---|---|
| F-01 | **P2** | TCS:67（R6）、:1005（AT-030-3-2）；PRD:452、:868、:309、:676 | OBS 草稿列的分類固定為 `tooling`，但凍結 PRD 明文「迴圈任一階段失敗都留一筆 OBS（分類 `bug`）」（NFR-SI-09-3，PRD:452；§12.2 錯誤處理，PRD:868「階段失敗留一筆 OBS（分類 `bug`）」；AC-SI-13-3，PRD:309 同為 `bug`），且 §9.4（PRD:676）把「CLI 非零 rc 並印可貼入的 OBS 草稿列」綁在 NFR-SI-09-3 上；R6 自己引 §9.4 卻改值，§7 開放問題未列。PRD 已凍結，TCS 不得單方改值（任務書準則：與 PRD 衝突處＝P2） | R6 與 AT-030-3-2 的固定值改 `bug`；若認為 `tooling` 較合適，須入 §7 開放問題、由掌舵者以 T1 裁決 | SA |
| F-02 | P3 | TCS:73（R9）、:446／:451（AT-001-1-E-4 情境三） | R9 沒寫「格式不合的 ID 是否參與 DUP／ORDER 追蹤」。情境三（列 005 改成兩位數字的 ID、列 007 改成第三位為字母的 ID；此處刻意不寫字面 ID，緣由見 §6 的 N-04）期望 `ledger.structure` 恰三筆 `ROW-ID-FORMAT`，只在「不參與」時成立：若參與，兩位數那列把最大值抬到 12，列 006、008、009、010 各多一筆 `ROW-ID-ORDER`（共多 4 筆），含字母的 ID 做 `int()` 還會拋例外 | R9 明寫「格式不合者不入 DUP／ORDER 追蹤」 | SA |
| F-03 | P3 | TCS:640、:660、:734、:809、:887、:946、:1074、:1130～1131 | §2 自訂規則「Then、And 行只有驗收字樣一組引號」被 8 個 AT 違反（含 `「…」`）。`sdd_compile` 對每行取第一個引號字面值當驗收條件，故 AT-031-1-E-2 要求最後回覆含「根 」（含空白）、AT-030-1-E-1 含「無 FAIL 但有 blocking NE」、AT-032-1-1 含「擷取者」「P1 定稿」、AT-004-1-1 含「列首格」等（共 8 條，§4 節錄）。文法層無 unmapped；只影響 autoclaude 編譯路徑（本 Feature 宣告 session-only，故不擋閘） | 這些 Then／And 行的 `「…」` 改反引號或移到 Given／When | SA |
| F-04 | P3 | TCS:157（R25）、:1367（V2）、:1374（V9）；帳本 LED:20 | 與 P0 退出 (b) 相衝的現行慣例：今日工作樹又原地改了 OBS-SI-011（累計 ×8→×9）；真歷史上帳本 8 個 commit 的後 7 個中有 5 個含既有列原地改寫。M 之後同類動作＝`ROW-MUTATED`，V2 即紅；SOP 骨架與 V9 都沒有「累計與更新走追加更正列」的條文與驗收 | M 之前把 011 的累計改成追加或「現查」形態；R25 加 SOP 條文（累計與更新走 `rel=corrects:` 追加列）並加 AT 代位；V9 加「N 之後至 SCG-4 前既有列零原地改寫」 | 主控、SA |
| F-05 | P3 | TCS:96～108（R16）；PRD:208 | R16 的九種「可定位」形態比 PRD:208 的四形態（檔案:行、指令＋rc、sid＋seq、帳本列 ID）寬：裸 sid、裸檔名、裸目錄、裸 sha、`§` 文件別名皆過（真帳本命中 `dir` 形態 19 列、`docref` 12 列，可與他形態並存）；放寬未列入 §7，與一審 F-15「座標須可重查」的標準有張力 | 把放寬列為開放問題並寫理由；或讓 `sid` 形態要求同列有 `line` 或 `seq` | SA |
| F-06 | P3 | TCS:1344（Q2）、:45（D1）；PRD:415 (iv) | 附註檔 `…_notes.md` 不在任何 `non_evolvable_globs` 內，且 `check` 不比對其內容不變（`orig` 保全只靠 V3 一次性稽核）。SA 只列「放協定目錄」一案並視「進 manifest」為缺點；現成解：改放 `docs/05_development/SelfImproving_Observation_Ledger_notes.md`，被既有 glob `docs/05_development/SelfImproving_*.md` 涵蓋，不必改 PRD | 改路徑；或把缺口升 T1 | SA、主控 |
| F-07 | P3 | TCS:254～275（18 處）、:277 | TCS 引的 PRD digest `a27bba61…` 是 HEAD 與 8d2d5ef0 的 blob（我今日重算一致）；工作樹 PRD 因 C.2 座標訂正已變（`9c571827…`），PRD 重凍後 18 處需回填；TCS:277 已寫「以 `show` 為準」，但交棒清單沒有這一步，且 `monorepo-si-p0-ledger` 的 Stage-1 須採納**重凍後**的兩份 | 列為 SA 與主控的前置動作，以 `show` 輸出回填 | SA、主控 |
| F-08 | P3 | TCS:63（R2）、:65（R4）、:69（R8）、:73（R9）、:114（R18）、:119（R20） | 7 項規則沒有任何 AT 釘住（我對 TCS 搜尋：BOM、no-history、鍵序、timeout 只出現在規則文字）：R2 相對路徑相對於 `--repo` 而非 cwd（AT 只用不存在的 `no/such.md`，換成 cwd 解析也同樣 rc 3）；R4 鍵序；R8(c) 每個 git 呼叫帶 timeout、`-C`、`encoding`（AT-030-2-1 只記 `args[0]`、`env`、`shell`）；R9 帳本 BOM 容許；R18(a) 的 `…+<k>` 截斷；R20 的 `no-history` 與「帳本不在 repo 內 ⇒ SOURCE-UNAVAILABLE」 | 各補一個 tmp 內可做的子情境 | SA |
| F-09 | P3 | TCS:39、:224～226、:123、:1154／:715 | 自增 AC 的來源標示不精確且有輕微超出：(a) 「判準指紋」在 PRD 只掛量測腳本（PRD:355、:356、:646）與 audit_session 先例，`check` 列（PRD:635）沒有，AC-030-3 的指紋與 `check_rules_rev` 是 SA 類推新增；(b) R21 的 `PARAM-UNKNOWN`（多出的鍵＝紅）超出 PRD:635 的「PRD 引用的參數名須存在」，且擋住 P1／P2 加鍵（須先改 TCS）；(c) §3.1 的 AT-003-3-1 寫「旗標恰四個」，AT 內文是五個（含 `--help`） | FRD-lite 標明「類推、非 PRD 明文」並請掌舵者知悉，或移到 P3 的 TCS；(c) 改字 | SA |
| F-10 | P3 | 全檔 | 多個 AT 各含 8～26 個子情境（AT-031-1-E-1 最多），一個紅燈難定位哪個情境壞 | 用 `subTest` 或參數化，保留 AT ID 對映 | SA、Developer |
| F-11 | P4 | TCS:157（R25） | SOP 骨架以大量字面中文片段做存在判準（含真 ID `OBS-SI-033`／`038`），措辭一改即紅；已用「刪去副本須判不合格」證明判準非恆真，登記 | — | — |
| F-12 | P4 | TCS:84（R13）、§4 | `deferred`、`decided` 只驗附加文字非空，PRD:218 要求「一句可觀測再開症狀」「裁決者與一句裁決」，代位未標；「新列的復發候選提示」（PRD:635、AC-SI-06-2，屬 P1）未列入 §4「刻意不做」 | §4 補兩列 | SA |
| F-13 | P4 | TCS:67（R6） | 草稿列 ID＝帳本現有最大 ID＋1、不看封存檔：封存若搬走高號列且暫無新列，可能撞號（現無封存檔） | 登記 | — |
| F-14 | P4 | TCS:1314（§5.5） | hermetic 環境未設 `GIT_CEILING_DIRECTORIES`；tmp 若落在某 repo 之下，AT-001-1-E-6 情境四的「無 git 目錄」會找到祖先 repo（一般機器與 CI 不成立） | 設 ceiling 為 tmp 父目錄 | SA |
| F-15 | P4 | TCS:1138～1198（§3） | §3 與 §1 重複維護兩份 AT 清單；TCS 體量 162KB（已登記 OBS-SI-045） | 登記 | — |

## 3. 開放問題 Q1～Q5 判讀

- **Q1（rc 語意）同意預設。** 真 repo 上 `PROP-SI` 提及 23 處 ⇒ `ref.carrier_families` 必為 NE；若「任何 NE 都非綠」，P0 退出 (b) 依文字不可達，SA 的判斷成立。項級 NE＋總評 PASS 與 PRD AC-SI-04-1「不得判通過」不衝突（該項印未判）。rc 3 與 argparse 的 2 分開合理。
- **Q2（附註檔）預設可接受，但有更簡單的現成解（F-06）。** PRD:415 (iv) 散文寫「SI 全部文件」而實體 glob 沒列附註檔，是 PRD 自身的小缺口，只能走 T1，不是 TCS 缺陷。
- **Q3（回填規則）合理。** 真帳本現況：45 列、僅 2 列處置已合 DISP_TOKEN（43 列需改寫）、3 列座標不合 R16（019、029、034，與 SA 相符）、P1／P2 列 0 筆（R15 不會逼 M 改嚴重度）、時間格 0 筆不合文法（M 不必動時間格，與 V3「時間逐格相同」相容）。SA 的「8 列超 700」估算對假設敏感：我以「新處置 40B＋標記 60B＋`orig` 內嵌舊處置」只估得 1 列（OBS-SI-043，649→約 759 bytes）超線；Q3 本就寫「以 M 前現查為準」，不影響規格。
- **Q4（未命名參數）合理。** PRD C5 說「UPPER_SNAKE 與 lower_snake 一對一」：PRD 的 UPPER_SNAKE 初值參數 16 個（含 `W_` 四個、`EVENT_MAX_BYTES`）全在 R21；PRD 未取名的三項由 TCS 命名並列 Q4；初值逐項與 PRD 相符（`W_N` 20、`W_MIN` 5、`W_EVT` 2、`W_OPP` 5、`MAX_PROPOSALS_PER_RUN` 3、`MAX_REVISIONS` 2、`CHURN_MAX` 2、`MIN_HELDOUT` 5、`MAX_TOUCH_RATIO` 0.2、`MAX_NEW_ENTRIES` 3、`STOP_AFTER_BAD` 2、`CAP_FRAC` 0.9、`MAX_ARCHIVE_ENTRIES_PER_CARD` 50、`CARD_LINE_MAX` 100、`EVENT_MAX_BYTES` 2000、`ROW_MAX_BYTES` 700）。
- **Q5（glob 一致性機器判準）同意。** 位置式抽取對真 PRD 與根 CLAUDE.md 穩定（18＋7＝25 重算相符）；脆弱點＝PRD:415 行內標點與 CLAUDE.md:81 單行，再開症狀合理。

## 4. 我今日重跑的輸出（節錄並合併同類行、省略處以「…」；數值皆為本回合工具輸出）

```
[compile 乾跑：記憶體內、cwd＝scratchpad、python -B；跑後 git status 無新增]
spec_format_version=1.0 scenario=brownfield contracts compiled=39 unmapped_at_ids={}
_AT_ROW rows=39 unique=39; gherkin blocks=39 with-AT-header=39 unique=39
set(§1 AT)==set(gherkin AT): True
gherkin fences whose first line is not exactly `# <AT id>`: (none)
AC/AT prefix mismatches: (none)
E-class AT ids matching AT-NNN-Y-E-n: 19; non-E: 20
contracts=39 weak_regex=(none) non-ideal-regex=8
   AT-031-1-E-2 -> (?s)(?=.*根\ )(?=.*\[AT_OK_031_1_E_2\])
   AT-030-1-E-1 -> (?s)(?=.*無\ FAIL\ 但有\ blocking\ NE)(?=.*\[AT_OK_030_1_E_1\])
   AT-032-1-1 -> (?s)(?=.*擷取者)(?=.*P1\ 定稿)(?=.*\[AT_OK_032_1_1\])
   …（另 AT-002-1-1、002-2-1、004-1-1、004-2-1、029-1-1 同型）
compile_tasks → 39 tasks; Playbook.model_validate OK; first step_id=sdd-brownfield-at-001-1-1; evaluator=pytest tools/tests/test_selfimproving_check.py -k "AT_001_1_1" -q
[R22] 必備集合：PRD 18 ＋ CLAUDE.md 7 ＝ 25 項；去重後 25 項（SA 預演 18＋7＝25）
[R24] PRD 指標列（M1～M5）：[(61, 1), (62, 2), (63, 3), (64, 4), (65, 5)]（各恰一列＝True）
[R24] 判定細則區段：PRD:69～78（下一個 `#### ` 在 PRD:79）；非空行 9 行；最長 772 bytes
[LEDGER] 真帳本資料列 45；欄數分佈 {8: 45}；列位元組 min=215 max=649；含控制字元的列：(none)
[R10] 真帳本時間格不合文法（TIME-FORMAT）：(none)
[R16] 真帳本證據座標不命中九形態（COORD-NONE）：3 列：OBS-SI-019、OBS-SI-029、OBS-SI-034
[R13] 現行處置已合 DISP_TOKEN 的列：2／45；需改寫（非枚舉首詞）43 列
[R18a] 提及（不含定義）的相異 OBS ID 36 個；不在主鍵集合者（OBS-REF-DANGLING）0 個
[R18d] 載體未建立家族提及：{'PROP-SI': 23}（NE nonblocking 預期成立：True）
[R26] 根 .claude/settings.json 含 selfimproving（不分大小寫）：False
[R20] 帳本相關 commit（--first-parent --reverse）：8 個；版本序列 9 個、相鄰比較 8 對；真歷史上「格內容有差異或刪列」事件 21 筆
[R20] 曾被原地改寫的 OBS ID：16 個（含 OBS-SI-011）；工作樹與 HEAD 帳本內容：不同（OBS-SI-011 累計 ×8→×9）
git grep OBS-SI: rc=0 lines=155 seconds=0.64 ／ git grep carriers: rc=0 lines=18 seconds=0.61 ／ git log first-parent: commits=8 seconds=0.05
PRD: HEAD blob sha256=a27bba619c493b2e…  8d2d5ef0 blob=a27bba619c493b2e…  worktree=9c5718274eb511cc…  TCS 引用：HEAD→True worktree→False
```

## 5. 附：任務 A 結論、未涵蓋、流程摩擦

- **任務 A（PRD C.2 座標訂正）：訂正成立。** 逐字稿 `f3ead132-…jsonl`（13,047,340 bytes、以 LF 切得 3,109 段，末段為空）以 JSON 結構解析：line 2476、2525、2581 皆 `type=user`、`message.role=user`、頂層 `origin.kind=human`（`turnOrigin=human`）、內容為字串，且與 PRD:975 的引文逐字相符（整則訊息等於引文，75／75、37／37、15／15 字）；line 2493、2536 為 `type=assistant`、無 `origin`、僅含 `tool_use` 區塊、文字 0 字（即「assistant 空記錄」）。`git diff HEAD --numstat` 該檔為 `1 1`，只動 PRD:975 一個物理行（三處座標都在其內）；`git diff --stat 8d2d5ef0 HEAD` 該檔為空，即其餘內容與凍結版相同。
- **未涵蓋**：編譯器的凍結閘、摘要綁定、FSM 狀態檔路徑與 `--spec-file` 路徑（乾跑未走 `load_spec`，「未驗」）；`check` 本身尚未實作，我的 R9～R22 預演是對真資料的規則演練、不是對實作的驗證；AT 未執行；macOS 未驗；`-k` 子字串選測未實跑；AT 文字未逐條重推（只推演了 AT-001-1-E-1、E-2、E-3、E-4、004-3-E-1 等指名情境的期望集合）。
- **流程摩擦**：(1) auto mode 系統提示再度要求優先用 Bash，與鐵律一及任務書衝突，全程 PowerShell／Read／Grep／Edit（OBS-SI-011 再復發）；(2) `Grep` 對 PRD:566、:635 回「Omitted long matching line」，改 Read 單行；TCS 162KB 分 8 段讀（OBS-SI-045 同型）；(3) `Glob` 的大括號選項內含路徑分隔符時匹配不到（`{_stdio_utf8.py,lib/…}` 回「No files found」，改單檔查詢才找到 `tools/_stdio_utf8.py`），是假陰性風險；(4) 編譯 CLI 無法唯讀使用，改呼叫 adapter 的私有解析方法（與 `load_spec` 同一批函式，但屬私有 API，日後可能漂移）；(5) 我的兩個腳本小失誤（引文索引錯位、f-string 反斜線語法），已更正且未影響結論。

一審完成：2026-10-19 12:27（+08:00）；QA（Sonnet 5.5，未參與撰寫）；一審判定 **FAIL**（P1＝0、P2＝1、P3＝9、P4＝5）；二審見 §6。

## 6. 二審（驗修復；2026-10-19 13:17 起，+08:00）

> 本節的 TCS 行號一律指 HEAD `407c945b` 的版本（1468 行）；§1～§5 的行號指一審版本（1377 行），保留原樣。口徑不變：只有 P1／P2 擋 PASS。

### 6.1 輸入快照與重跑（皆為本回合工具輸出）

- **HEAD**＝`407c945b07aceeddcd85d4d073a2d59a87c79175`（`git rev-parse` rc＝0）。`git status --short` 一行 ` M docs/06_quality/SelfImproving_Observation_Ledger.md`——**工作樹並不乾淨**（與任務書「乾淨」不符；是主控的觀察帳本〔工作樹 50 列、HEAD 49 列〕，不是受審物）。TCS 與工作樹相同（`git diff --quiet HEAD -- <TCS>` rc＝0）：blob `3b872b86…`、sha256 `30041a19…`、1468 行／178,931 bytes、CR 0、TAB 0；19 個表格欄數全一致、47 個圍欄全閉合；`git diff 7b9c6ba6 HEAD` 對該檔的 75 個 hunk 我全部讀過。
- **adapter 乾跑重跑**（記憶體內、`python -B`、cwd＝scratchpad；不呼叫 CLI、不寫檔）：`spec_format_version=1.0 scenario=brownfield contracts compiled=42 unmapped_at_ids={}`；§1 的 AT 集合＝gherkin 標頭集合（42／42）；AC 與 AT 前兩段不一致 0；E 類 22、非 E 20；`weak_regex` 無、`non-ideal-regex=0`、Then／And 行非驗收字樣的引號字面 0；`compile_tasks` 出 42 步、`Playbook.model_validate` 通過、step_id 唯一。
- **PRD／SOP digest（任務項 2：通過）**：`Get-FileHash` 與 hashlib 對工作樹現算相同——PRD `9c5718274eb511cc071deb1193ae7eadaaffc3b636826acf8e7935a50754460e`、SOP `deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2`，皆等於各自的 HEAD blob。TCS 內 PRD digest **18 處**（:255～259、:261～270、:272、:273、:275）、SOP digest **3 處**（:271、:274、:276）、舊 `a27bba61…` **0 處**；路徑與摘要逐列配對正確，:278 的說明已改為重凍後版本。

### 6.2 一審發現逐筆核

| 編號 | 結果 | 座標（TCS@HEAD） | 本回合驗證 |
|---|---|---|---|
| F-01（P2） | **消除** | R6 :68；AT-030-3-2 :1038 | 兩處固定值皆改 `bug` 並引 PRD:452、:868、:309、:676；Grep `tooling` 全檔只剩 R13 枚舉（:85）與基線資料列（:1351、:1358、:1359） |
| F-02 | **消除** | R9 :74；AT-001-1-E-4 :455、:458、:461 | R9 明寫格式不合的 ID（含 (2) 類空 ID 欄）不入已見集合、不更新最大值、不做整數轉換，情境三的期望（恰三筆 `ROW-ID-FORMAT`）現可得；新增情境六（BOM、表頭在第 1 行、tz 宣告在表後）釘住 BOM 容許 |
| F-03 | **消除** | AT-002-1-1 :648；AT-002-2-1 :668；AT-004-1-1 :742；AT-004-2-1 :819；AT-029-1-1 :917；AT-030-1-E-1 :979；AT-031-1-E-2 :1095、:1102；AT-032-1-1 :1194～1195 | 八個 AT 的 `「…」` 改為反引號或平述；6.1 乾跑 `non-ideal-regex=0`、非驗收字樣的引號字面 0（一審為 8） |
| F-04 | **消除**（規格面；措辭過寬見 N-03） | 慣例 :57；R25 (9) :158；AT-004-3-1 :839；V9 :1466 | 新增「M 之後只追加」慣例、SOP 條文 (9)、AT 內「刪去該行的副本須判不合格」自證、V9 的零原地改寫與機械憑證；並要求主控在 M 之前把累計欄改成追加或現查形態（:57） |
| F-05 | **消除**（Q6；`sid` 收斂的實效見 N-01） | R16 :97、:105；Q6 :1429 | 放寬已列為 Q6 並附真帳本實測、替代與再開症狀（我一審的修法二選一，已滿足）；`sid` 形態改為須同格帶 `line` 或 `seq`（真帳本 10 列含 sid 者全帶 ` line N`，零列只靠裸 sid，我重算相符） |
| F-06 | **消除** | D1 :45；:617；:758；M :1366；§5.6 :1397；Q2 :1425；§4 :1320 | 附註檔路徑一律 `docs/05_development/SelfImproving_Observation_Ledger_notes.md`（Grep 全檔 7 筆同形、`docs/06_quality/` 版殘留 0）；PRD:415 (iv) 實有 `docs/05_development/SelfImproving_*.md`；剩餘缺口（`check` 不比對附註檔內容）已入 Q2 與 §4 |
| F-07 | **消除** | 見 6.1 | 18／3／0 與現算 digest 全符 |
| F-08 | **消除**（七項逐項） | R2→AT-030-1-1 :952、:957；R4→:958；R8 (c)→R8 :70＋AT-030-2-1 :994、:998；R9 BOM→AT-001-1-E-4 :455、:461；R18 (a)→AT-004-1-E-1 :760、:763；R20→新 AT-004-3-E-3 :885～902 | 逐條讀過，期望值與規則文字一致：相對路徑以誘餌 cwd 判別；鍵序用 `object_pairs_hook=list`；`run` 與 `Popen` 次數相等；七處提及＝5 處加 `…+2`；(A) 未提交帳本＝`no-history`、(B) 帳本在 repo 外＝blocking NE、rc 2 |
| F-09 | **消除** | :39；R7 :69；R21 :124；碼表 :197；AT-003-3-1 :723、:1218 | 自增 AC 來源逐條標「PRD 明文」或「本檔類推」；`PARAM-UNKNOWN` 全檔 0 處、改為多出的鍵不判紅（V6 :1463 核恰 23 鍵）；旗標改述為四個功能旗標加 `--help`，AT 列五個旗標，一致 |
| F-10 | **消除** | 規則 :350；AT-031-1-E-1 :1067～1083；E-4 :1128～1144；E-5 :1146～1162 | 「子情境一律 `subTest`／參數化、失敗訊息指出情境」成為 §2 規則；原 26 子情境的 AT 拆成三個；E-5 的邊界對照與 R21 表（比例鍵 (0,1]、整數鍵 ≥1、陣列非空）逐值相符 |
| F-11～F-15（P4） | **已登記** | §7.2 :1435～1439 | 五列各有處置與再開症狀；F-14（`GIT_CEILING_DIRECTORIES`）僅登記、規格未改，我同意 |

### 6.3 二審新發現（皆 P3；P1＝0、P2＝0、P4＝0）

| 編號 | 嚴重度 | 位置（TCS@HEAD） | 症狀（附證據） | 修法 | 誰修 |
|---|---|---|---|---|---|
| N-01 | P3 | R16 :97、:105（`sha`／`sid`）；AT-001-1-E-2 :406、:409 | R16 標頭宣稱「裸 sid 不算」，但 `sha` 形態（7～40 位 hex、含 a～f、以非英數字為界）會把 UUID 的第一段當 sha 吃掉。我用 TCS 自己的九個正規式實測：真實形 sid（如本場 `f3ead132-29b1-418c-97d9-35868ab11c70`）裸寫，或加 `line=2476`、`line:2476`、`L2476`、`第 2476 行`，或短碼 `f3ead132 line 2476`，都只靠 `sha` 過關；只有全數字 UUID（基線 `00000000-0000-4000-8000-000000000006` 形）才判 COORD-NONE。故 AT 的列 008 只在 UUID 不含 a～f 時成立，而 AT 沒釘 UUID。另 R19 (d) 的 `line\s*[:=]?\s*\d+` 收 `line=2581`，R16 的 `sid` 形態不收，兩處語法不一 | `sha` 的邊界納入連字號（前後斷言都排除 `-`）後對真帳本重跑 R16 預演；或承認裸 sid 經 `sha` 放行並刪去「裸 sid 不算」與列 008；AT 的列 008 釘一個含 a～f 的 UUID；`sid` 與 R19 (d) 的 line／seq 語法對齊 | SA |
| N-02 | P3 | Q6 :1429；V3 :1460；主控裁決列 OBS-SI-049 | Q6 與主控裁決都把「形態合規卻不可重查」的防線交給 V3 抽查，但 V3 八項沒有一項抽查座標可重查：(3) 只比座標逐格相同，(8) 只抽回填語意。我對 HEAD 現算：12 列只靠單一放寬形態過關——`docref` 7（006、008、020、041、043、048、049）、無行號 `file` 3（011、012、030）、無行號 `path` 2（007、016）；Q6 的再開症狀（V3 抽查到不可重查的座標）因此無人會觸發 | V3 (8) 補一句：另自「證據座標」欄抽 ≥5 列（優先取僅靠 `docref`、`dir`、無行號 `file` 或 `path` 過關者）逐一重查；或改寫 Q6 的承擔句 | SA |
| N-03 | P3 | :57、R25 (9) :158、V9 :1466；對照 R20 :120、AT-004-3-1 :834／:839、PRD:211、PRD:259（AC-SI-04-3） | 一審 F-04 的修復措辭過寬（源自我一審修法的用字）：三處寫「M 之後狀態更新一律追加列、原地改寫即 `ROW-MUTATED`、既有列零原地改寫」，但 R20、AT-004-3-1（K1 把列 001 的處置由 `open` 改成 `deferred；…`，判 PASS）與 PRD:211／AC-SI-04-3 都明許「處置欄 `open`→終值一次」的原地改寫，TCS:217 也這樣寫。V9 以 `history.row_mutated` PASS 當「零原地改寫」的機械憑證，但該憑證對 open→終值一次也綠，字面與憑證不等價；照字面做的人會把 `open` 列永遠留著、另追加列結案 | 三處加「處置欄 `open`→終值一次除外（PRD:211）」；V9 改「零原地改寫（處置欄 open→終值一次除外）」 | SA |
| N-04 | P3 | V2 :1459；R18 (a) :115 | V2 括註只說「本檔與測試原始碼不含不存在的字面 OBS 編號」，但 R18 (a) 掃整個 repo（含未追蹤）。我用 R18 規則對現況重演，真 repo 當時有 2 筆 `OBS-REF-DANGLING`，皆在我一審報告 F-02 列（字面反例 ID），N 之後 V2 的 `ref.obs` 會因此轉紅；已自行改成文字描述，改字後重跑為 0 筆。SCG-4 前所有 QA／SA／SD 文件（含本報告）都不得出現字面不存在的 OBS 編號 | V2 括註改「整個 repo 的非忽略檔」；N 之前先跑一次 `check`、清零 `OBS-REF-DANGLING`；寫反例請用文字或 `OBS-SI-NN` 佔位 | SA、主控 |

### 6.4 判讀、預算、建議、未涵蓋與摩擦

- **Q6 判讀（任務項 1）：不構成與凍結 PRD 的衝突（非 P2）；屬可接受的規格細化，不扣分，殘差登 P3（N-02）。** 理由：(a) PRD:208 的「檔案:行／指令＋rc／sid＋seq／帳本列 ID」是欄位說明，沒有「僅」「限」之類窮盡語，規範句 AC-SI-01-1（PRD:243）寫的是「≥1 個可定位」；(b) PRD 他處把檔案路徑、檔名、sha 當座標用——AC-SI-06-2（PRD:269）比對「同證據座標檔案路徑」、AC-SI-23-1（PRD:361）以證據座標「引用該記憶條目（檔名或條目標題）」、AC-SI-16-3（PRD:326）把「合入 sha」當座標——四形態若讀成窮盡，反與這些條文自相矛盾；(c) 放寬方向是「收得更寬」，SA 已在 R16 標頭與 Q6 明示並附實測，我獨立重算相符：HEAD 7b9c6ba6 的 47 列，九形態 3 列不合（019、029、034），以「路徑或檔名帶 :行／反引號指令同格有 rc／sid 加 line 或 seq／帳本列 ID」粗判 24 列不合（與 SA 的 24 一致；HEAD 407c945b 的 49 列為 26 與 3），而遷移只准追加座標；(d) 唯一收得過鬆的 `sid` 已改（實效見 N-01）。保留的張力：PRD 文字未改，掌舵者若把 PRD:208 讀成窮盡，走 T1；主控裁決（OBS-SI-049）已記「下次 PRD 重凍時明文化」，建議凍結前把 Q6 回報掌舵者（§7 標題已要求）。
- **AT 預算（任務項 3）**：42 已達上限，**我不要求再補 AT，也不建議放寬上限**：N-01 只需把 AT-001-1-E-2 的列 008 釘一個含 a～f 的 UUID，N-03 在既有 AT-004-3-1 加一句期望，N-02、N-04 是 V3、V2 的文字。
- **FSM 建議（`monorepo-si-p0-ledger`）**：二審判定 PASS ⇒ 建議主控對 SCG_VALIDATION 記 gate PASS，再走 HUMAN_PENDING 與 Stage-2 `spec-frozen`（我未跑 FSM CLI，指令形態以 SOP、BRIDGE 為準）。N-01～N-04 皆純文字、SA 一棒可清；Stage-2 凍結後再改須重凍，**建議凍結前先清**（改後只需重跑 6.1 的乾跑與 N-01 的探針，不必整份重審）；若現在就凍結，請把四項登進 §7.2 同型表（附再開症狀）。凍結後的實際 digest 以 `show` 為準（:278）。
- **給主控的提醒（非 TCS 缺陷）**：(1) 工作樹帳本最後一列為 686 bytes，按 Q3 同法估算 M 加欄後約 796 bytes（> 700），與 OBS-SI-043 一樣須處理，Q3 已寫「以 M 提交前現查為準」；(2) 重演 R22 仍 18＋7＝25、R24 仍為 M1～M5 各一列加判定細則 PRD:69～78 的 9 個非空行、`PROP-SI` 家族提及 23 處（`ref.carrier_families` 仍必為 nonblocking NE），P0 退出 (b) 依規則仍可達（前提：M 與 N 正確、N-04 清零）。
- **未涵蓋**：`check` 尚未實作，R9～R22 的預演是對真資料的規則演練、非對實作的驗證；AT 未執行；凍結閘與摘要綁定（`load_spec`）未走；未改動的 AT 未逐條重推；FSM 狀態未查；macOS 未驗。
- **流程摩擦**：(1) auto mode 系統提示再度要求優先用 Bash，與鐵律一及任務書衝突，全程 PowerShell／Read／Grep／Edit（OBS-SI-011 再復發）；(2) 本回合中途 context 壓縮一次，靠 scratchpad 內的 diff 傾印檔才無損續查——建議二審任務書預先要求「先把 `git diff -U0` 導到 scratchpad 再讀」；(3) 任務書稱「工作樹乾淨」，實際 ` M` 一個帳本檔（主控持續入帳所致），審前快照須現查；(4) PowerShell 把原生輸出導檔會經 console 編碼轉碼，改用 `Start-Process -RedirectStandardOutput` 取原始 UTF-8 位元組再用 Read 讀；(5) **自我更正**：一審 F-02 列寫了字面反例 ID，使真 repo 的 R18 (a) 重演出 2 筆 dangling（N-04），已改成文字描述。

二審完成：2026-10-19 13:21（+08:00）；QA（Sonnet 5.5，未參與撰寫）；二審判定 **PASS**（P1＝0、P2＝0；一審 F-01～F-10 全消除、F-11～F-15 已登記；二審新增 P3×4＝N-01～N-04）。
