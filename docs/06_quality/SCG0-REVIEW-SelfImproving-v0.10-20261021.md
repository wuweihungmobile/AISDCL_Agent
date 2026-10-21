# SCG-0 複審報告（差分）— SelfImproving PRD v0.10（T1 2026-10-20 修訂）

**審查者**：QA（Sonnet 子代理；未參與本輪 SA／Architect 撰寫；文字交卷由主控謄寫，數字皆 `[他包回報]`）。
**T1**：sid `d6dfce97-92bd-4d34-b7d3-73cf5feaa23d` line 13。**一審時刻**：2026-10-21 02:3x～03:0x +08:00；HEAD `ecf4d2ba`，審查對象＝工作樹相對 HEAD 的差分（PRD、Operations SOP、AgentConsole Architecture.md、`research_sources.json`、`params.json`、根 `CLAUDE.md`、`.claude/settings.json`、BRIDGE §8.6）；任務書 scratchpad `si_p2\qa_scg0_brief.md`（13 個審查重點）。
**FSM**：PRD 鍵 `monorepo-selfimproving` `gate --gate SCG_VALIDATION --result FAIL`（retry 1/3，回 SPEC_DRAFTING）；修復棒＝SA 同代理（主控例外授權 §9.2／§9.3／§9.4 指定位置）；二審只驗修復。

## 0. 判定

**FAIL**（P1＝0、P2＝2、P3＝10、P4＝15）。
- P2 兩筆都是「文件自相矛盾，落在晉升與驗證判定這條閘門關鍵路徑」：F-01 主控 2026-10-21 續裁的 `touched_ok=true` 晉升前提只同步到一部分位置；F-02 `rollback_ok=false` 的 verdict 語意，§5.1.2／AC-SI-15-4 與 §9.3／§9.4 對不上。
- 其餘 13 個重點中，T1 對映、憲法對照、連動面、訂正協議、§12.2 回寫、SOP 凍結者節都通過（附 P3／P4）。

## 1. 輸入快照與審查範圍

- HEAD＝`ecf4d2ba`。`git status --porcelain` 與審查起點完全相同（26 個 M、1 個 `??`），審查期間未變。
- 審查基準 blob（`git hash-object` 前 12 碼）：PRD `bed525eaf5ed`、SOP `31064475f5c1`、Architecture `72919bda6705`、`research_sources.json` `4e2f2e04cb82`、`params.json` `5dcf45168ec0`、根 `CLAUDE.md` `1e4a0a52e596`、`.claude/settings.json` `ff8906bc83cd`、BRIDGE `a1f872983969`。
- PRD 差分共 102 個 hunk，Architecture 128 行；`python tools/selfimproving.py check` rc=0、overall=PASS、rows=234、items=28。
- 腳本普查（記憶體內解析、無寫入）：AC 定義 106（HEAD 99；新增 `AC-SI-15-4`、`AC-SI-32-6`、`AC-SI-35-1～35-5`）、重複 0、引用未定義 0；FR 35（HEAD 34）；元件 C1～C21、ADR-SI-01～13 引用皆有定義；§9.7 #41～#81 連號無缺；PRD 與 SOP 皆 UTF-8 無 BOM、LF。

## 2. 13 個審查重點逐項判定

| # | 重點 | 判定 | 要點 |
|---|---|---|---|
| 1 | T1 五點對映 | PASS（P4-14） | §14 逐字引文對 transcript line 13 逐字相符（`type=user`、`origin.kind=human`、2026-10-20T15:55:41.397Z）；C.1 新表含前言、1a、1b1、1b2、1b3～1b5、1c、問題 3 |
| 2 | 需求面↔§9 | **FAIL** | F-01、F-02；F-08、F-12。兩參數 524288／10 與 `event_max_bytes` 4096 三處一致；來源表 14 筆逐筆 0 不符、id 位元組序、host 全 ASCII |
| 3 | 可測性 | PASS（附 P3／P4） | 7 條新 AC 皆可寫 AT；動詞旗標具體；P 型未寫成「被擋」（F-07、F-09） |
| 4 | 憲法對照 | PASS | FR-SI-35 對照列涵蓋禁令 11／12、鐵律四、C-15；載體≠寫入者、無 DELETE、處置 open→終值一次沿 AC-SI-04-3 |
| 5 | 連動面 | PASS（附 P3） | Architecture 新節與 PRD C18／C20／C21 逐檔一致；§5.2 硬規則 5 的機械檢查可執行（`const NAV` 現回 1 筆，落地前應有輸出）；SOP rc 表與 §9.3 一致；P2 配方「待補」見 F-08 |
| 6 | 訂正協議 | PASS（附 P4-4） | 102 hunk 普查：被取代的規範句皆有〔訂正〕或為純插入 |
| 7 | §5.1.2／§9.2／§9.3／§9.4 一致 | **FAIL** | F-02、F-01；`unverified_ack` 三處一致；複驗邊與 `verify_runs_max` 六處一致 |
| 8 | `exec` 類判準 | 條件通過 | 四項可測；缺「import `runner` 者必登記 exec」（F-06） |
| 9 | §5.4↔AC-SI-32-6 | 條件通過 | (a)(d) 有對應；(b)(c) 無消費端測試、欄位清單不一致（F-07） |
| 10 | §12.2 回寫 | PASS（附 P3） | 約 25 個座標零失真；未驗者皆有再開症狀；殘留 F-10 |
| 11 | 狀態機補強三處一致 | **FAIL** | 沙盒失敗出口＝F-02＋F-11；`returned` 限兩碼五處一致；晉升前提＝F-01 |
| 12 | C.2 #20 vs §5／§9 | **FAIL（部分）** | (a)～(h)(j)(k) 對得上；(i) 與 AC-SI-15-4、§9.2、§9.3 `promote`、§5.1.2 正文不符，同列〈誠實劃界〉自相矛盾 |
| 13 | SOP 凍結者節 | PASS | 與 AC-SI-20-1 一致，〔訂正〕保留原文 |

## 3. 發現表

### P2（阻塞）

| 編號 | 座標 | 缺陷 | 建議修法 |
|---|---|---|---|
| F-01 | 已含 `touched_ok`：§7.2「晉升」列、AC-SI-16-2、§9.3 `decide` 列、§5.1.2 訂正註、C.2 #20 (i)；未含或相反：AC-SI-15-4 末句、C.2 #20 同列〈誠實劃界〉、§5.1.2 正文、§9.2 轉移註記（`promote` 只需 `p.rollback_ok is True`）、§9.3 `promote` 列 | 同一晉升前提兩種版本；依 §9.2 實作 `fold._dec` 時重放會放行 `touched_ok=false` 的手動 DEC 而寫入端擋（寫入與重放判準分叉）；§5.1.2 訂正註宣稱「同步」不實；§13.3 無此續裁列 | 五處同步 `touched_ok=true`（AC-SI-15-4、C.2 #20、§5.1.2 正文、§9.2 `Prop`＋`fold._dec`、§9.3 `promote`）；§13.3 補列；grep `touched_ok\|rollback_ok` 逐處複核 |
| F-02 | 敘述「沙盒失敗者不跑探針、直接收 NE 或 FAIL」：§5.1.2、AC-SI-15-4、NFR-SI-01、§9.7 #76(i)、AC-SI-16-2；機制：§9.3 `verify` 列只有 `applied=false`、`touched_ok=false` 直接 NE，`rollback_ok=false` 落入「其餘」＝跑探針；§9.4 三態判定表順序 ①②（NE）先於 ③`rollback_ok≠true`⇒FAIL | 不跑探針時 `carrier_proof`／`baseline_red` 為 null，先命中 ①②⇒NE，永遠到不了 FAIL；`events.verdict` 重算 NE 與 `verify` 記的 FAIL 不符⇒`VERDICT-MISMATCH`；若收 NE 又非兩碼⇒不可退回不可晉升只剩否決，續棒補的出口落空 | 判定表最前加 ⓪（`probes_n=0`）：`applied≠true`⇒NE[SANDBOX-NOT-APPLIED]、`touched_ok=false`⇒NE[TOUCHED-SUPERSET]、`rollback_ok≠true`⇒FAIL[ROLLBACK-DRYRUN-FAILED]；§9.3 `verify` 直接收 verdict 條件擴為三者之一；TCS 補三值全組合 × `probes_n` 真值表 AT 並驗 `events.verdict` 一致 |

### P3（登記）

| 編號 | 座標 | 缺陷 | 建議修法 |
|---|---|---|---|
| F-03 | §9.3 `sandbox` 列（前置只有 approved＋`dec(approve)`）；§9.2 `heldout.freeze`、AC-SI-20-1（凍結 `seq` 須早於第一筆 `app.sandbox`） | 先 `sandbox` 後凍結不被寫入端擋，`events.transitions` 事後永久紅 | `sandbox` 前置加同 PROP 已有 `heldout.freeze`（缺＝rc 1）並補 AT |
| F-04 | NFR-SI-02-3（無人值守僅可執行到提案止） vs §9.3 rc 通則（`sandbox`／`verify`／`heldout-freeze`／`card --issue` 照常） | 「前置是人的 approve、本就到不了」不成立：approve 可先記、無人窗口續跑即可到 `sandbox` | 二擇一：UNATTENDED 拒 `sandbox`／`verify`，或 NFR-SI-02-3 明定「套用」＝promote 並刪不實理由 |
| F-05 | §9.4 `apply_lock` 段 (3)「釋放…用盡後拋原始例外」；`evwrite.py`:129–130；`writeverbs.py`:105–106 | 事件已追加、釋放才拋 ⇒ rc 3 並印「帳本未變動」（失實），重送會重複寫入；(a)～(e) 無「用盡」分支 | 釋放失敗不改 rc、只印警告並交陳舊鎖回收；補「用盡」分支 AT |
| F-06 | §9.4 `exec` 判準 | 「import runner 者歸 exec」只是慣例，`rw` 檔 import `runner` 不會紅 | 明寫「任何相對 import `runner` 的檔須登記 exec」並與計數釘住 |
| F-07 | FR-SI-32 補述、§13.1（欄位 7）vs C20、Architecture §5.4（欄位 9）；AC-SI-32-6 | 欄位清單缺 `match`、`mobile`；<768 只渲染 `mobile:true`、未知路徑不 fallback 兩項無 AC；(b)(c) 無消費端測試；篩選五維度與游標分頁並存未定；(d) 與函式型 `href` 說法不一 | 補欄位；AC-SI-32-6 增 (e)(f)；測試清單補 (b)(c)；篩選與詳情補 AC 或標明非 AC |
| F-08 | §8.1 P2（出口 (a)～(f)）、P2b；§9.6 P2（根層半歸 P2 鍵，閘欄仍寫 §8.1 P2 出口）；FG-L、FR-SI-35 標題 | 根層半（`obs-add`／`obs-close`／`decide --carrier console`、`check obs.console_audit`、`status console_pending[]`、`export buckets[]`）在 P2 鍵交付但 P2 出口無驗收；SOP「P2 動詞（待補）」無承接 | P2 出口加 (g)；FG-L 與 FR 標題註根層半＝P2 |
| F-09 | AC-SI-35-1 ②、AC-SI-33-1、Architecture §10.2、§9.4 Console 面、C21 | 「不呼叫寫入型 CLI 動詞」無機械鎖（AST 鎖不管 argv 動詞），AC 句卻像 M | 標 P，或 `test_si_readonly_lock.py` 加判準（argv 動詞只准 `export`、`obs-add --dry-run`） |
| F-10 | Architecture L553「Token Guard halt 同理」 vs §12.2 V-3 結論（`RunEventProcessor.java`:314 只認 ESCALATION 前綴） | 失真句留在正文 | L553 加〔訂正〕一句 |
| F-11 | §5.1.2、AC-SI-15-4、§7.2（`否決` 只收 proposed／verified；`退回` 不收 approved） | 匯出失敗不寫事件、PROP 維持 approved；確定性失敗時卡死且 `DUPLICATE-TYPE` 擋同型再提 | 允許對 approved 下 `否決`，或匯出失敗也寫 `app.sandbox`（`applied=false`、`SANDBOX-EXPORT-FAILED`）走 NE 出口 |
| F-12 | §9.2 稽核 JSON 外層鍵清單；§9.3 Bridge 段（驗 `audit_ref` 為 UUID 又稱不解 `body`、`{id}` 須等於 `body.obs_id`）；Architecture §10.2／§10.3 | 外層鍵漏 `audit_ref`；不解 `body` 就無法比對 `obs_id` | 外層加 `audit_ref`（與 `subject`），`{id}` 一致性改由 backend 與 CLI 驗或明寫 Bridge 只解該欄位 |

### P4（理論洞／細節）

P4-1 PRD 內 compat-ci 與 `test_adr_xplat001_c1c2_lock.py` 的行號引用已漂移；P4-2 §9.0 Q15「九種 kind」應為八；P4-3 「主控探針 00:1x」非精確時刻；P4-4 AC-SI-10-3 語意補定無〔訂正〕；P4-5 判定表 reasons：`applied=false` 時 `touched_ok` 為 null 亦列 TOUCHED-SUPERSET、無探針 M／D 被標 CARRIER-PROOF-FAILED（建議「無探針」碼）；P4-6 `git apply` 逾時與 Bridge 稽核落檔 I/O 失敗的狀態未定；P4-7 「IDNA 形態」未定義；P4-8 `buckets[]` 次序與「未分類」；P4-9 根 CLAUDE.md 與 BRIDGE §8.6 把 T1 問題 3 推廣為整個 SDD 流程的常態規則（建議向掌舵者確認範圍）；P4-10 NFR-SI-01「宣告值」無消費者；P4-11 `marks_extra` 准 `src` 與 §5.1.1 衝突；P4-12 表單欄位含 `|` 未規定；P4-13 「最後審查日期」引本報告檔須同 commit 落檔；P4-14 C.1 對映表無「1b 總問」單列；P4-15 `HELDOUT-TOO-SMALL` 的出口列「複驗」不成立；Console DB 稽核表宜明定不可改。

## 4. 抽驗座標與 URL（30 組；零失真者摘要）

`tools/lib/apply_lock.py`:57–68／:71–82／:102–108；`tools/lib/selfimproving/{rows,scan,fold,events,git,writeverbs}.py` 各引用行；`tools/tests/test_selfimproving_capability.py` 登記表 24 鍵 19／3／2；`docs/06_quality/AutoSDD_Defect_Log.md`:332；觀察帳本 OBS-SI-191～222 列；transcript line 13（human）與 line 841（peer，體檢交卷）；`ToolsRegion.tsx`:21–39／:54–69／:87–106、`layout.test.tsx`、`lib/nav/` 三檔存在；backend `SecurityConfig.java`:80–84、`StepPrompt.java`:26、`RunEventProcessor.java`:314 等；`docker-compose.yml`、`engine-bridge/Dockerfile`；`git ls-files -s` 29,302 筆（mode 120000＝0、160000＝0）；venv Python 3.11.9、`tarfile.data_filter` 存在；11 支 workflow 皆 3.11；`research.scan` 最壞行 1,696／1,989 手算吻合。漂移者已列 P4-1～P4-3。URL：14 筆與 JSON 逐字相同、全 https、host 全 ASCII；本審不連網，體積交叉驗 3 筆、其餘沿主控探針值 [未重測]。

## 5. QA 自檢

零寫入（未建、改、刪任何檔）、未派子代理、未連網、未跑測試套件、未用 Bash；審查起訖 `git diff` index 行逐檔相同。超出白名單但唯讀的兩項已揭露（`python -c` 查 `tarfile.data_filter`；讀 transcript 兩行）。token 約 0.7M（單一 Sonnet 代理）。

## 6. 主控處置（逐段追加）

- 2026-10-21 03:07：`gate --gate SCG_VALIDATION --result FAIL`（retry 1/3→SPEC_DRAFTING）。修復棒派回 SA 同代理，裁決：F-01 五處同步 `touched_ok=true`；F-02 採「不跑探針」＋判定表 ⓪；F-03 `sandbox` 前置加 `heldout.freeze`；F-04 採「UNATTENDED 下 `sandbox`／`verify`／`heldout-freeze`／`card --issue` 亦非零 rc」；F-05 釋放失敗不改 rc；F-06 import `runner` 者必登記 exec；F-07 補欄位與 AC (e)(f)、篩選在前端對已取得頁做；F-08 P2 出口加 (g)；F-09 改 M（argv 動詞白名單判準）；F-10 L553〔訂正〕；F-11 匯出失敗也寫 `app.sandbox`（`SANDBOX-EXPORT-FAILED`）；F-12 外層鍵加 `audit_ref`／`subject`、Bridge 只解外層；P4-1～8、10～12、15 一併修；P4-9 留掌舵者確認（最終報告明列）；P4-13 本報告與 PRD 同 commit；P4-14 不動。
- 2026-10-21 03:3x：SA 修復棒交卷（需求面 20 餘處＋§9 授權 27 行；其餘 387 行 SHA256 `d810b437…`；新欄 `app.sandbox.fail_code`、碼 `SANDBOX-EXPORT-FAILED`／`SANDBOX-APPLY-TIMEOUT`／`NO-PROBES`、判定表 ⓪）；主控補裁可退回碼加第四碼 `SANDBOX-APPLY-TIMEOUT`（六處）、Architecture L976／L941 兩句；`check` rc=0；PRD 鍵 `transition --to SCG_VALIDATION`；QA 二審以 SendMessage 續派同一代理。

## 7. 二審（QA 同一代理續審；文字交卷由主控謄寫；數字皆 `[他包回報]`）

**判定：PASS**（P1＝0、P2＝0）。一審 F-01～F-12 全部修復；P4-1～8、10～12、15 已修；P4-9／13／14 依處置刻意不動。一審 13 個重點：#2、#7、#8、#11 轉 PASS；#9 轉 PASS（附 N-5）；#12 轉 PASS（附 N-3）；其餘維持 PASS。

- 輸入：HEAD `ecf4d2ba`；PRD blob `98e9c28aa90d`（582,678 bytes、1416 行、LF、無 BOM）、Architecture `89ff3eeddb20`；SOP／JSON／根 CLAUDE.md／settings／BRIDGE 六檔與一審相同。`si check` rc=0（rows=240）。普查：AC 106、FR 35、ADR-SI 13、元件 21、§9.7 #41～#81 連號。
- 逐項：F-01 晉升前提九處皆「`rollback_ok=true` 且 `touched_ok=true`」；F-02 判定表 ⓪（applied→touched→rollback，先中者定）、`verify` 列三者之一直接收 verdict、`NO-PROBES`、真值表句在場；F-03～F-12 各處通過（含 F-07 九欄與 AC-SI-32-6 (e)(f)、F-09 argv 白名單判 M、F-11 `fail_code`、F-12 外層 `audit_ref`／`subject`）；主控補裁四碼六處一致、Architecture 三處在場；P4 各項通過。
- §9 不變證據（本場重算）：§9＝L643～L1056 共 414 行；排除 SA 列的 27 行（26 行帶「SA 修復棒」標記＋L826）後 387 行 SHA256 `d810b4374d2ea4d6e363a1babc73c0a18fda4d8bbaa4849d8b152768000a42c6`，與 SA 回報值一致。界線：修復前原檔不在 git，無法獨立重算修復前雜湊。
- 新登記（皆非阻塞）：**N-1（P3）** PRD L424／L1381 探針時刻「00:10～00:12」與逐字稿不符——`probe_sources.py` 執行 line 380＝2026-10-20T16:04:37Z（00:04 +08:00）、`probe_sources2.py` line 419＝16:06:38Z、`research_sources.json` 寫入 line 484＝16:09:15Z，實測區間 00:04～00:07 且早於表檔寫入；N-2（P4）L334「上列三碼」應為四碼；N-3（P4）C.2 #20 (j) 與右欄仍寫宣告值；N-4（P4）Architecture §10.3 寫入端點失敗欄缺 503 `si_unavailable`；N-5（P4）Architecture §5.4 檢查表缺消費端測試項、`roles`／`enabled` 斷言歸屬與 PRD C20 不一致；N-6（P4）§9.3 `verify` 列文序（預檢在前、⓪ 在後）與判定表序不同，兩者同時成立時何者為準未明寫；N-7（P4，設計取捨）暫態匯出失敗記 NE 後只能退回、耗一次 `MAX_REVISIONS`，成本未寫進正文。
- QA 自檢：repo 內零寫入、未派子代理、未連網、未跑測試套件、未用 Bash；超白名單一項（掃逐字稿 line 380～500 的時戳，唯讀）已揭露；流程摩擦：一次唯讀 PowerShell 被工具層誤擋「Remove-Item on system path '/' is blocked」（指令無刪除動作），拆成三個小呼叫後正常；額度守衛於 five_hour 98% 自動寫續航任務書並武裝哨兵（主控現查：`AutoSDD_Sentinel_d6dfce97…` NextRunTime 2026-10-21 04:06:38，LastTaskResult 0）。token 累計約 1.05M（含一審）。
- **主控處置（2026-10-21 03:5x～04:0x）**：N-1～N-7 全部由主控親改（N-1 時刻改 00:04～00:07 並註明誤寫源自主控任務書估值「00:1x」，另入帳 OBS；N-2 四碼；N-3 (j) 訂正與右欄；N-4 L950 失敗欄；N-5 §5.4 消費端測試項與歸屬；N-6 `verify` 列加「⓪ 先於預檢」；N-7 AC-SI-15-4 加代價句）；`check` rc=0；PRD 鍵 `gate --gate SCG_VALIDATION --result PASS` → HUMAN_PENDING → `spec-frozen --stage Stage-1`（常態規則，approver 引 sid d6dfce97 line 13）。
