# SCG-0～3 規格階段獨立審查報告：根層鍵 `monorepo-si-p7-flow-visibility`（SelfImproving P7 第一波主機端）

- **審查日期**：2026-11-11
- **審查者**：獨立審查棒（未參與撰寫；只讀，未改任何規格、程式、測試）
- **輸入快照**：HEAD `e1ad0ac0`＋工作樹未提交的規格改動（`git diff --stat`：PRD +82、SOP +52、Root_Layout ±1、TCS-P4 ±15、TCS-P5 +1、TCS-P6 ±5，新增 `TCS-SelfImproving-P7-20261111.md` 557 行）
- **判準來源**：主控共同背景（裁決 1～11、治理不變量、嚴重度定義）、根層 SA 交卷、Console SA 交卷

## 1. 審查範圍

| 檔 | 審查面 |
|---|---|
| `docs/01_requirements/SelfImproving_PRD.md`（v0.16 增量：FG-P、FR-SI-47～49、C28／C29、§9.3 `push-run`、§9.4〈P7 增補〉、ADR-SI-19、§9.7 #88 訂正與 #91～#96、§9.9、§10.1、§13.3、§14、附錄 C.2 #26） | 全部增量 |
| `docs/03_testing/contracts/TCS-SelfImproving-P7-20261111.md` | 全檔 |
| `docs/05_development/SelfImproving_Operations_SOP.md` | P7 增量與三處勘誤 |
| `docs/02_architecture/Root_Layout_and_Module_Placement.md` | §3 SelfImproving 列 P7 句 |
| `TCS-SelfImproving-P4／P5／P6` | 勘誤二、勘誤十三、E-10 與就地〔訂正〕 |
| 對照：`AgentConsole/docs/03_testing/contracts/TCS-SiFlowVisibility-20261111.md` §0.2、§5.1、§6.2、§7 | 介面一致性 |
| 對照：`tools/tests/test_selfimproving_schedule_patrol.py`、`test_selfimproving_schedule_gate.py`、`_selfimproving_p4_fixtures.py`、`tools/lib/selfimproving/{runner,git,sched,evspec,schedarm}.py` | 勘誤衝突實查 |

## 2. 逐項結論

### 2.1 可測性、AT 覆蓋、映射與數量

- 機械核對（PowerShell 逐列解析 TCS-P7 §1 表格）：AT 定義 **96**、檔別 RD 48／MM 11／PU 37、負控 28、零重複編號；§5 映射表抽出 96 個 AT、與定義集合差集為空。與 SA 交卷、TCS §5、TCS 檔頭宣稱一致。
- AC 36 條（PRD 32＋自增 4）皆至少一個 AT；PRD 的 AC-SI-49-3／49-4 合併為一條敘述但 TCS 分列，計數仍為 13。
- Given／When／Then 大多可機械判定；負向（`-E-`）、邊界（截斷位元組、n＝min、嚴格大於的新鮮度界）、併發（`push.lock` 雙行程、崩潰窗口、守門後再提交）、半途失敗（原子寫失敗、結果檔寫失敗、牆鐘逾時）皆有覆蓋。
- **缺口**：`push.state` 的判定規則彼此矛盾且無優先序（R-05），使 AT-749-10-2 不可唯一判定；R156 型卡點（運轉未關使 (f) 一律跳過、Console `run-request` 被消耗成 `sched.skip`）沒有任何 AT 或欄位（R-04）。

### 2.2 主控裁決 1～11 逐條

| 裁決 | 結論 | 依據 |
|---|---|---|
| 1 唯讀 bind、原子覆寫、不簽章、Bridge 只讀 | 符合 | TCS-P7 §2.2、AT-747-8-1／8-2；PRD §9.4〈P7 增補〉 |
| 2 預設 true、三條件、工作樹乾淨、明寫 sha、不 HEAD／force／`--no-verify` | 大致符合；「工作樹乾淨」實作為「除 SI 自有路徑外乾淨」未附 WHY（R-14）；守門未綁 APP 種類與內容（R-06） | AT-749-3-1、4-1、5-1、6-1；PRD L659 |
| 3 S4U 不推、互動登入任務、不存權杖、鎖、牆鐘、失敗碼、同 sha 不無限重試、macOS 對等 | 符合；`pythonw` 下未處理例外不可見（R-15） | AT-749-6-E-1、8-*、9-*、12-*、13-*；ADR-SI-19 |
| 4 第二波項目只需白話顯示原因 | **不符**：R156 型卡點與 (f) 跳過原因無碼無白話（R-04） | 附錄 A 無 `blackout`／`quota-band`／`other-driver`／`run-open`／`spawn-failed` |
| 5 新鮮度 2×心跳＋5 分；缺檔有畫面 | 符合（缺檔畫面屬 Console） | AT-747-8-4 |
| 6 M 類不加安靜前置、前／後像、`MEMORY-DIR-UNRESOLVED` | 符合 | AT-748-2-1、3-1、4-1、4-2 |
| 7 `heldout-freeze` 低於下限只 stderr 警告、不改卡面 | 符合 | AT-747-13-1、13-E-1 |
| 8 原因碼→白話單一家，凡帶碼處皆帶白話（含沙盒碼、verify reasons、推送句） | **部分不符**：`sandbox.failCode` 無白話欄（R-02）；`ne[].reason` 新碼與 (f) 跳過碼不在附錄 A（R-03、R-04）；Console 自造評估集白話（R-08） | TCS-P7 L296、§附錄 A |
| 9 console-writes 十一鍵不動、前端以稽核編號對照；VIEWER 可看 | 根層文字矛盾：TCS L9、PRD C28（L910）仍寫「backend 對映與 `hostRejection` 併入」（R-11） | Console TCS §7.1 第 3 點已依裁決 |
| 10 OFF 仍寫 `off:true` 快照，衝突須勘誤 | 未與既有測試衝突（見 2.4），但 PRD AC-SI-36-5 與 SOP 步 0 字面「整次 no-op」未加〔訂正〕，且未寫明「不取鎖、成功不加日誌行」（R-09） | PRD L521、SOP L516 |
| 11 黃金樣本由根層 TCS 定義路徑 | **不符**：TCS-P7 全文無黃金樣本路徑（Grep `golden|黃金` 只命中卡面與 P6 匯出夾具），Console TCS L1014 依賴 `patrol.golden.json`／`detail.golden.json`（R-01） | — |

### 2.3 治理不變量

- **`push-run` 守門可繞過性**
  - 偽造／誤帶 trailer：守門只要求 APP「在帳本且 prop 相符」，未限定 APP 必為 `app.promote`／`app.rollback`、未限定一個 APP 只對應一個提交、也未把提交內容綁到該 APP 的 `post_sha256`。同一 PROP 的 `app.sandbox`／`app.verify` 的 APP 也在帳本（例：本 repo 的 APP-SI-014 為驗證證據），任何人或互動代理照抄巡邏提交格式（含 trailer）並只改該 PROP 觸及檔或 SI 帳本，就會被自動推上 `main`——正是 US-P7-05「不會推出別人的半成品」要防的情境（R-06，P2）。
  - 領先提交混入非巡邏提交：AT-749-4-1 ①⑥⑦、4-E-1 已涵蓋，判第一個不符者。
  - 互動視窗同時 commit：AT-749-6-2「推明確 sha」涵蓋推送內容；但 pre-push 閘門測的是工作樹，守門只在評估當下檢查乾淨，推送牆鐘最長 120 分內人的改動會影響閘門結果（R-14）。
  - 推到一半失敗：遠端已接受而本機行程被殺時，本機 `origin/main` 不前進，下次重試得到 up-to-date／rc 0 而轉 `PUSH-OK`，結果正確但最長 `sched_push_retry_minutes`（360 分）內快照顯示 `failed`（R-19，P4）。
  - 遠端已前進：`PUSH-REJECTED`、不可重試、新 sha 才再試，有界（AT-749-8-1）。
- **M 類 pre／post-image**：前像沿既有 `PREIMAGE-MISMATCH`；後像以 `manifest.paths_manifest` 重算比對 `post_sha256`、不自動回滾、P 類不驗（AT-748-4-*），完備。
- **評估集與機密外露**：`propdetail` 不讀家目錄、AST 禁 `heldout` 字串（AT-747-4-E-2）；`heldout` 只出 `digest8`；`verify` 只出布林與計數（`carrier_proof` 依 `evspec.py:226` 為 `bool|null`，但 TCS 未寫型別，R-03）；推送結果遮罩與植入字串零命中（AT-749-7-2、13-1）。未見外露路徑。
- **巡邏器代下決定**：無。巡邏器只入帳、推進已有 DEC 的 PROP；`pushguard` 只判讀；`push-run` 為 C 類，無人視窗拒收（AT-749-11-1）。

### 2.4 勘誤正確性與 `AUTOSDD_SI_PATROL_OFF` 衝突實查

- TCS-P4 勘誤二：R154／R155 就地〔訂正〕保留原文、AT-440-2-1／2-E-1 改期望值合理；D-IMP-6 (7) 收回理由充分。**但** PRD §9.7 #96（L1387）宣稱 P4 勘誤含「R157 日誌」與「AT-438-7-1 `ALLOWED_GIT`」，勘誤二實際寫兩者「不變」（R-12）。
- TCS-P5 勘誤十三、TCS-P6 E-10：只放寬範圍守衛與 `params.json` 釘選，不使既有 AT 語意失效；E-10 把 AT-690-2-1 的位元組釘轉交 AT-749-1-1＋基準檔活值，承接完整。
- **OFF 快照衝突實查**（Grep `PATROL_OFF` 於 `docs/03_testing/contracts`、`tools/tests`、`tools/lib/selfimproving`）：
  - `test_selfimproving_schedule_patrol.py:169-187`（AT-436-5-E-1）：斷言 `fx.snap(R)`（只有 repo）不變、`locks/patrol.lock` 不存在、`patrol.log` 恰增一行。寫家目錄快照**不違反**現行斷言，前提是 OFF 路徑**不取 patrol.lock** 且**寫入成功時不加日誌行**——規格未寫明（R-09）。
  - TCS-P4 L155、L273、L883-893（AC-SI-36-5／AT-436-5-E-1「整次 no-op」）；PRD L521 AC-SI-36-5「整次 no-op（rc 0、日誌一行）」；SOP L516 步 0「整次 no-op」：字面與 P7 行為矛盾，只有 PRD AC-SI-47-8 單方面宣稱「取代」，被取代的條文本身沒有〔訂正〕（R-09）。
  - `test_selfimproving_schedule_patrol.py:129-151`（AT-436-3-E-2）：鎖被占／無人值守時斷言 `snapshot()`（含家目錄樹，排除 `locks`）不變——與 AT-747-8-E-1「不寫快照」一致，無衝突。
  - `test_selfimproving_schedule_patrol.py:96-109`（AT-436-3-2 dry-run 家目錄零寫入）：與 AT-747-8-E-1 一致，無衝突。
  - **相鄰衝突**：`test_selfimproving_schedule_patrol.py:77-90`（AT-436-3-1）釘 stdout 恰五行 `step=`（巡視、入帳、到期、運轉、推進）與 `--json` 的 `steps` 長度 5；SOP L522 把寫快照稱為「步 5」。若實作把寫快照輸出成第六個 step 行即紅，規格未禁止（R-10）。

### 2.5 與 Console 規格的介面一致性（逐欄）

| 欄 | 根層（TCS-P7 §2） | Console（TCS-SiFlowVisibility §0.2／§5.1） | 結論與 target |
|---|---|---|---|
| `push.state` 值域 | `off｜idle｜pending｜waiting-login｜running｜ok｜failed｜blocked` | C-5 標籤表 `idle／running／ok／failed／skipped`；AT L515-517 以 `skipped` 與「`idle`＋`ahead>0`」推導 | **不一致**，`off／pending／waiting-login／blocked` 會顯示「未知的推送狀態」→ console（R-07） |
| `push.tick_at` | 有 | 未讀（其他鍵透傳） | 可接受 |
| `runs.live[].purpose` | W1＝`scheduled｜console｜manual` | 標籤缺 `manual` | console（R-07） |
| `runs.queued[]` | 恆 `[]`，元素結構未定 | `{purpose,target,why}` | root 宜寫明 W2 預留元素結構（R-07 附註） |
| `heldout` | 八鍵含 `digest8`、`neNote` | C-3 只列六鍵；自造「案例數低於下限，驗證必判『無法評估』」 | console 應改顯示根層 `neNote`（裁決 8）→ console（R-08） |
| `detail` 欄數 | 八欄（含 `sourceObs`、`timeline`） | L133 寫「六欄」；時間線改打既有議題端點 | 文字 console；功能可接受（R-08） |
| `sandbox` 白話 | 只有 `failCode` | 保底句 | root 須補白話（裁決 8）→ root（R-02） |
| `verify.carrierProof` 型別 | 未寫 | 字串原樣、夾具 `"ok"` | root 寫 `bool|null`；console 夾具改布林（R-03／R-08） |
| `ingest[]`、`props[]`、`next`、`who` 五值、`steps[]` | 相同 | 相同 | 一致 |
| 黃金樣本路徑 | **無** | 依賴 `patrol.golden.json`、`detail.golden.json` | root（R-01） |
| `readAt` | 不屬根層 | Bridge 自定 | 一致 |

### 2.6 跨平台

- Windows：`Register-ScheduledTask -LogonType Interactive -RunLevel Limited`、`pythonw.exe` 直呼、`NextRunTime` 值為憑證、回讀 `Principal.UserId`；`runner.run_argv` 已帶 `CREATE_NO_WINDOW`（`runner.py:94-95`），不會閃窗。未定義 `sched arm` 在非提權時巡邏段失敗後是否仍嘗試推送段（V-P7-1 的程序依賴此點，R-17）。
- macOS：launchd 使用者層 agent、`launchctl list` rc 為憑證、Windows 字面只住 `sys.platform` 分支（AT-749-12-4），標「未驗」誠實。
- 路徑正斜線（AT-747-2-1）、`-z`＋`core.quotepath=false`（AT-749-4-E-1）、LF／無 BOM（AT-747-8-1、AT-749-1-1）、時間帶 offset（§3 時鐘縫），完備。
- `pythonw` 無 stdout／stderr：`push-run` 未處理例外只剩 `LastTaskResult`，快照恆 `pending`（R-15）。

### 2.7 落點與機械鎖

- 6 新模組住既有套件 `tools/lib/selfimproving/`、入口不變、測試 3 檔＋夾具 1，符合 Root_Layout §2；Root_Layout §3 只加文字不先寫反引號路徑，與 P6 先例一致。
- LOC：`patrol.py`／`patrolrun.py` 淨增 ≤30 行且 ≤400（AT-790-2-1）；新檔估 ≤230。
- 範圍守衛四處一致（AT-790-4-2、`P7_ALLOWED` 單一來源）；參數鍵驗證（AT-749-1-*）；`C_CLASS`、動詞數、`CAPABILITY` 同步站點列明。
- 重釘面只以「`test_adr_xplat001_c1c2_lock.py` 與其他重釘儀式檔」概稱，未點名新測試檔的 `_TREE_FILE_FLOORS`、ONBOARDING 基線同步等已知連動站點（R-22，P4）。
- `scheduled_task_expectations.json` 與 `test_install_windows_nightly.py:943` 以固定任務名對表，新任務不入表不會誤紅；排除理由寫入 ADR-SI-19，可接受。

### 2.8 真機 V 項是否足以證明「不開 CLI 走完第一波」

V-P7-1～8 各自驗一段（註冊、快照、推送、未登入、分類、M 類），但 V-P7-3 的推送標的是「造一個巡邏式提交」（構造），V-P7-7 不含推送，Console 鍵 V1～V8 也只看顯示。**沒有一條真機項把「Console 核准 → 巡邏 sandbox／verify／發卡 → Console 決定晉升 → 巡邏 promote／commit → `AutoSDD_SI_Push` 推送 → Console 顯示已推送」串成一次**，因此不足以證明第一波範圍內不開 CLI 可走完（凍結評估集屬人工前置，可在 V 項明列為例外）（R-18）。

## 3. 發現表

| 編號 | 嚴重度 | 位置 | 問題 | 建議修法 | target |
|---|---|---|---|---|---|
| R-01 | P2 | TCS-P7 §3（L338-344）、§2；Console TCS L85、L1014、L1102 | 裁決 11 要求根層 TCS 定義兩份黃金樣本路徑，根層全文沒有；Console 的 AT-966-1-1／4-1／4-3 第二列與 sha256 比對無所依 | 在 TCS-P7 §3 新增「黃金樣本」條：路徑（例 `tools/tests/fixtures/selfimproving_p7/patrol.golden.json`、`detail.golden.json`）、產生方式（由 RD 測試以確定性夾具產出並與檔位元組比對）、納入 §4 允許集合與一條 AT | root |
| R-02 | P2 | TCS-P7 L296（§2.1 `sandbox`）、AT-747-5-1；PRD AC-SI-47-5 | 裁決 8：沙盒失敗碼須同時帶白話，`sandbox` 只有 `failCode` | `sandbox` 增 `failText`（取 `nextstep.reason(failCode).text`，`failCode` 為 null 時 null），附錄 A.3／A.5 已含沙盒碼；AT-747-5-1 鍵集合與 AT-747-12-3 同步 | root |
| R-03 | P3 | TCS-P7 L67、L73、L79、L100（`ne` 新碼）；L297（`carrierProof`） | `PATCH-UNREADABLE`、`BODY-UNREADABLE`、`OBS-LEDGER-UNREADABLE`、`HELDOUT-MIN-UNKNOWN`、`TIMELINE-TRUNCATED` 經匯出帶出卻不在附錄 A；`carrierProof` 型別未寫（實為 `bool|null`，`evspec.py:226`） | 附錄 A 增一節「匯出 `ne` 碼」並在 `ne` 項加 `text`（或明寫 `ne` 屬既有契約、豁免裁決 8 的 WHY）；§2.1 寫 `carrierProof: bool|null` | root |
| R-04 | P2 | TCS-P7 §2.2 `steps[].result`（L308）、附錄 A；SOP L519（步 2）、L518（步 1 `run-request`→`sched.skip`） | 裁決 4／8：第二波才解的 R156 型卡點（運轉未關使 (f) 每格 `sched.skip(run-open)`、Console `run-request` 被消耗成跳過）與其他跳過原因（`blackout`、`quota-band`、`other-driver`、`dirty-tree`、`spawn-failed`）在快照中只有自由文字，沒有碼也沒有白話；使用者按了「立即運轉」卻看不到為何沒跑 | 快照增 `schedule{due_at, skip:{code,text}}` 或令 `steps[]` 帶 `{code,text}`；附錄 A 增 A.6 跳過原因碼（含「已有未關運轉 RUN-…，需等它關閉（第二波起可由 Console 處理）」）；補一條 AT | root |
| R-05 | P2 | TCS-P7 AT-749-10-2（L248）vs 附錄 A.4（L536、L539-545）；PRD AC-SI-49-10（L665） | `PUSH-RETRY-WAIT` 在 A.4 為 `failed`、在 AT-749-10-2 為 `blocked`；同 sha 不可重試失敗後同時滿足 `failed`（最近結果失敗且 ahead>0）與 `blocked`（守門回 EXHAUSTED）；`pending`／`waiting-login` 的 `code` 值未定；各態無判定優先序 ⇒ AT 不可唯一判定 | 定一張「判定序」表（例：off→running→守門碼對映→最近結果→pending／waiting-login），逐碼給唯一 `state`，`pending`／`waiting-login` 明寫 `code`（例 `PUSH-PENDING`、`PUSH-WAITING-LOGIN` 並入附錄 A.4）；AT-749-10-2 改為表驅動 | root |
| R-06 | P2 | PRD AC-SI-49-3／49-4（L659）；TCS-P7 AT-749-3-1、4-1（L201-206）；§10.1 風險列 | 守門未限定 APP 必為 `app.promote`／`app.rollback`、未限一 APP 一提交、未把提交內容綁到 APP 的 `post_sha256`；照抄巡邏提交格式（含同 PROP 的沙盒／驗證 APP）並只改該 PROP 觸及檔或 SI 帳本的人工／互動代理提交會被自動推上 `main` | (ii) 改為「APP 為該 PROP 的 `app.promote` 或 `app.rollback`」；加 (v) 同一 APP 在領先範圍至多一個提交；加 (vi) P 類提交中觸及路徑的 blob 雜湊等於該 APP 的 post 清單、M 類提交只准 SI 自有路徑；AT-749-4-1 增三個子案 | root |
| R-07 | P2 | Console TCS C-5（L147）、AT L515-517；C-1（L139） | Console 推送狀態標籤表用舊設計稿值域（含 `skipped`、以 `idle`＋`ahead>0` 推待推送），根層 `off／pending／waiting-login／blocked` 會顯示成「未知的推送狀態」，主控裁決 3 要的「等使用者登入後自動推送」只能靠 `text` 保底；`purpose` 標籤缺 `manual`；`runs.queued[]` 元素結構與根層「恆空、未定」不對齊 | Console C-5 與 AT 改用根層八值（以 TCS-P7 §2.2 為準）並補 `manual`；根層在 §2.2 註明 `queued` 元素於 W2 定義、W1 不得有元素 | console（`queued` 附註 root） |
| R-08 | P3 | Console TCS L133、L143（C-3）、L511、L1013 | 「`detail` 六欄」與根層八欄不符；Console 自造評估集白話句，違反裁決 8 單一家（應顯示 `heldout.neNote`）；夾具 `carrierProof:"ok"` 與實際 `bool|null` 不符 | 改「八欄」並註明 `sourceObs`／`timeline` 暫不使用；評估集警示改以 `neNote` 顯示、缺席才用保底；夾具改布林 | console |
| R-09 | P3 | PRD AC-SI-36-5（L521）；SOP L516、L532；TCS-P4 L155、L273、L883-893；TCS-P7 AT-747-11-2（L131） | OFF 寫快照與被取代條文「整次 no-op」並存未加〔訂正〕；未寫明 OFF 路徑不取 `patrol.lock`、寫入成功不加日誌行、不呼叫 `pushguard`（否則 AT-436-5-E-1 的「不取鎖」「日誌恰增一行」轉紅）；OFF 無鎖寫入與他行程心跳的競寫未述 | PRD AC-SI-36-5、SOP 步 0、TCS-P4 AT-436-5-E-1 Then 加〔訂正〕與勘誤列；AT-747-11-2 加斷言「鎖檔不存在、日誌恰一行、git 呼叫 0 次」 | root |
| R-10 | P3 | SOP L522（「5 寫快照」）；`test_selfimproving_schedule_patrol.py:77-90`（AT-436-3-1） | 既有 AT 釘 stdout 恰五個 `step=` 行與 `--json` `steps` 長度 5；規格未禁止把寫快照輸出成第六步 | AC-SI-47-8／AT-747-8-1 明寫「寫快照不新增 stdout step 行、`--json` 形態不變」，或走勘誤改 AT-436-3-1 | root |
| R-11 | P3 | TCS-P7 L8（「對齊裁決 1～8」）、L9；PRD C28（L910） | 仍寫「backend 對映與 `hostRejection` 併入」，與裁決 9（console-writes 十一鍵不動、前端以稽核編號對照）矛盾；裁決 9～11 未列入對齊 | 改為「前端以 `auditRef` 對照快照 `ingest[]`」；對齊句改 1～11 | root |
| R-12 | P3 | PRD §9.7 #96（L1387）vs TCS-P4 勘誤二 | #96 宣稱 P4 勘誤含「R157 日誌」「AT-438-7-1 `ALLOWED_GIT`」，勘誤二寫兩者不變 | #96 刪這兩項或改「確認不變」 | root |
| R-13 | P3 | PRD AC-SI-49-7（L651 附近）；TCS-P7 AT-749-7-1／7-E-1（L225-226） | 認證、拒絕、網路樣式先於 `[pre-push dispatcher]` 判：pre-push 閘門輸出（測試日誌）常含 `Connection refused`、`Authentication failed` 等字樣 ⇒ hook 失敗被判 `PUSH-AUTH`（誤導人去更新憑證）或 `PUSH-FAILED`（重試三次、每次重跑長閘門） | 有 dispatcher 標記時只以 git 自身尾段（`error: failed to push some refs`、`hook declined`、`! [remote rejected]` 等）判 AUTH／REJECTED，其餘歸 HOOK；或在 dispatcher 區段之外比對；補一個「hook 日誌含認證字樣」子案 | root |
| R-14 | P3 | PRD AC-SI-49-5（`PUSH-DIRTY-TREE`）；`sched.py:280-282`；SOP L182 | 裁決 2 要「工作樹乾淨」，實作判準排除 SI 自有路徑而未附 WHY；且乾淨只在評估當下查，pre-push 閘門跑在工作樹上，推送期間（至多 120 分）人的改動會影響閘門結果 | PRD 寫明偏離與理由；推送結束後再查一次 `dirty_paths`，期間變髒則結果附註「閘門期間工作樹有變動」（或改在 sha 的拋棄式 worktree 執行閘門並說明代價） | root |
| R-15 | P3 | PRD AC-SI-49-12（`pythonw.exe`）；TCS-P7 AT-749-13-1（提到 `tick.log`）、§2.3 | `pythonw` 無 stdout／stderr，`push-run` 未處理例外只剩 `LastTaskResult`，快照恆 `pending`、`tick.log` 並不屬推送任務 | `push-run` 頂層捕捉例外寫 `push/last_error.json`（碼 `PUSH-INTERNAL-ERROR`＋白話，遮罩後）並反映到快照 `push`；補 AT；更正 AT-749-13-1 的 `tick.log` | root |
| R-16 | P3 | TCS-P7 附錄 A.1（L482）、AT-747-9-3（L118） | `AUDIT-REF-REUSED` 標 `permanent:false`、「下一心跳自動重試」，語意上是永久衝突（TCS-P4 D-IMP-6 (4)：已入帳的 ref 不再重試） | 改 `permanent:true`、`who` 主機管理者，或附 WHY | root |
| R-17 | P3 | PRD AC-SI-49-12；TCS-P7 AT-749-12-1／12-3、V-P7-1（L423） | 巡邏任務註冊需提權；未定義非提權執行 `sched arm` 時巡邏段失敗後是否仍嘗試推送段、rc 與輸出為何；V-P7-1 的「巡邏任務已安裝後單跑」沒有對應的旗標或模式 | 明定順序與續行規則（例：巡邏段已存在且設定相符即略過再註冊推送段），或提供 `sched arm --push-only`；AT 補子案 | root |
| R-18 | P3 | TCS-P7 §6（L419-430）；Console TCS §6.2 | 無一條真機項串起「Console 核准→巡邏推進→Console 晉升→巡邏 commit→自動推送→Console 顯示已推送」；V-P7-3 的推送標的為構造提交 | 新增 V-P7-9 端到端（凍結評估集列為唯一允許的人工 CLI 前置），兩鍵 RTM 互引 | root |
| R-19 | P4 | PRD FR-SI-49 誠實劃界；AT-749-9-2 | 遠端已接受而本機被牆鐘殺時，快照最長 360 分顯示 `failed` | 誠實劃界補一句，或 `PUSH-WALL-EXCEEDED` 後下一心跳即允許重試一次 | root |
| R-20 | P4 | SOP L521（步 4「不 push」）、L533（3b） | 步 4 原句「不 push」與 commit 本文刪「不 push」語意易混；3b 建議以留髒改動暫停推送，會同時擋 promote | 步 4 改「巡邏器本體不 push」；3b 刪留髒改動的建議 | root |
| R-21 | P4 | PRD §14 T1 2026-11-11、附錄 C.2 #26；TCS-P7 追溯表 `P7-PENDING` | 座標與摘要待主控補，屬凍結前程序性空欄 | 凍結前補齊並由 `spec-frozen` 前檢核 | root |
| R-22 | P4 | TCS-P7 §4「重釘」列（L355）；PRD §9.9.1 | 重釘面只概稱，未點名新測試檔的 `_TREE_FILE_FLOORS`、ONBOARDING 測試基線同步等已知連動站點 | 列明重釘清單 | root |

## 4. 結論

**CONDITIONAL**（不得判 PASS：P2 共 7 筆——R-01、R-02、R-04、R-05、R-06 為 root，R-07 為 console；無 P1）。

- 規格骨幹完整：AT 96 條數量與映射機械核對一致、治理不變量（巡邏器不代決、無人視窗不推送、評估集零外露、不 force／不 `--no-verify`、推明確 sha）皆有機械 AT；P4／P5／P6 勘誤未使既有 AT 語意失效，OFF 快照與既有測試實查無直接衝突。
- 放行條件：修畢全部 P2（R-01、R-02、R-04、R-05、R-06 於根層；R-07 於 Console），並至少處理 R-09、R-10、R-11（字面矛盾與既有 AT 的保護條款）後，由同一審查面只重驗受影響條目即可。

---

## 二審（2026-11-11；同一審查者，只讀現行工作樹，不採信修訂者回報）

**做法**：重讀 TCS-P7（現 630 行）、PRD 受影響條（AC-SI-36-5、47-8～47-15、49-3～49-13、§9.7 #95／#96、§9.9）、SOP（L225、L483、L516、L521、L532-533、L557-566）、TCS-P4 勘誤三（L883）；以 PowerShell 逐列解析 AT 表與 §5 映射；對照 `tools/lib/selfimproving/patrolrun.py:308-333`（`_commit`）與 `sched.py:32-33`（`_OWN_PREFIXES`）。

### 二審 1. 一審發現逐條結論

| 編號 | 結論 | 依據 |
|---|---|---|
| R-01 | 已修 | TCS-P7 §3（L373）定義 `tools/tests/fixtures/selfimproving/p7/{patrol,detail}.golden.json`、產生規則與涵蓋情境；AT-790-5-1／5-E-1；§4 允許集合已列；PRD L1401 引用 |
| R-02 | 已修 | §2.1 `sandbox.failText`（L318） |
| R-03 | 已修 | `ne` 新碼帶 `text`（L326）、附錄 A.7；`carrierProof: bool｜null`（L319） |
| R-04 | 已修 | 快照 `schedule{enabled,current,last_skip}`、`runs.waiting[]`、附錄 A.6、AC-SI-47-15 與 AT-747-15-1～E-1；AT-747-15-2 專測「立即啟動被消耗成跳過」且不改 R156 行為 |
| R-05 | 已修（但見新 R-24） | 附錄 A.4b 判定序七步互斥、`push.code`／`text` 恆非空、`retry` 欄；AT-749-10-2 改表驅動並要求窮舉互斥；RETRY-WAIT／EXHAUSTED 改以 `failed`＋`retry` 表達（A.4 L581） |
| R-06 | 已修（P2 結案；殘留降為新 R-26，另有連動缺口新 R-25） | 見下方〈R-06 再攻〉 |
| R-07 | **未修**（target console） | Console TCS 現檔仍是 C-5 `skipped`（L147）、AT L515／L517 `skipped`；無 `waiting-login`／`pending`／`blocked`／`off` 標籤、無 `manual`；且未對齊新增的 `schedule`、`runs.waiting`、`push.retry`、`push.code` 恆非空 |
| R-08 | **未修**（target console） | Console TCS 仍寫「六欄」（L23、L133、L383）；`carrierProof` 夾具仍為字串（L668、L1013）；黃金樣本仍只寫檔名、未引用根層路徑 `tools/tests/fixtures/selfimproving/p7/`（L1014、L1102） |
| R-09 | 已修 | PRD AC-SI-36-5 加〔訂正〕（L521）；SOP 步 0 加〔訂正〕（L516）；TCS-P4 勘誤三（L883：AT-436-5-E-1 斷言一字不變且維持成立）；AT-747-11-2 加副作用邊界（不取鎖、git 0 次、日誌恰一行） |
| R-10 | 已修 | AT-747-8-1 明寫不新增 step 行、`--json` steps 仍 5 |
| R-11 | 已修 | TCS L8 對齊 1～11、L9 改前端以 `auditRef` 對照；全 `docs/` 已無 `hostRejection`（僅本報告引用） |
| R-12 | 已修 | PRD #96（L1388）改為「R157 與 `ALLOWED_GIT` 確認不變」 |
| R-13 | 已修 | AT-749-7-1 判序改「先 hook 標記、只看最後標記行之後的尾段」；AT-749-7-E-1 專測 hook 日誌含認證／網路字樣 |
| R-14 | 已修（措辭小瑕疵併入新 R-27） | PRD AC-SI-49-5 偏離 WHY；AC-SI-49-6／AT-749-6-3 推送後復查 `tree_changed` |
| R-15 | 已修（rc 表漏列併入新 R-27） | `push/last_error.json`、AT-749-9-4、A.4b 第 6 步 |
| R-16 | 已修 | 附錄 A.1 L514、AT-747-9-3 |
| R-17 | 已修 | `sched arm --push-only`／`sched disarm --push-only`、兩段獨立；AT-749-12-3、12-6；V-P7-1 改用 `--push-only` |
| R-18 | 已修 | V-P7-9 端到端（L461），人工前置限凍結評估集 |
| R-19 | 已修 | PRD L670 誠實劃界 |
| R-20 | 已修 | SOP L521「巡邏器本體不 push」；3b 改 `sched disarm --push-only`、明示勿留髒改動（L533） |
| R-21 | 已修 | §4A `spec-frozen` 前檢核清單四項 |
| R-22 | 已修 | §4「重釘」列點名 `_TREE_FILE_FLOORS`、onboarding 基線、落點鎖等 |

### 二審 2. R-06 再攻（推送守門）

| 手法 | 結果 | 擋住的條件 |
|---|---|---|
| 照抄格式、trailer 指向真實 `app.sandbox`／`app.verify` | 擋 | (ii) `PUSH-APP-KIND-INVALID`（AT-749-4-E-1） |
| 照抄格式、trailer 指向真實 `app.promote`（另起一個提交） | 擋 | (iii) 同 APP 已有巡邏提交＝`PUSH-APP-REUSED`；若巡邏提交不存在，(vi) 要求本提交新增該 APP 事件行且 P 類觸及檔雜湊等於 `post_sha256`＝內容就是巡邏器產生的那份（等同合法提交） |
| 修改（amend）巡邏提交，夾帶 repo 內一般檔 | 擋 | (v) `PUSH-PATH-OUTSIDE`（AT-749-4-E-4、E-5、E-6） |
| 修改巡邏提交，多改觸及檔內容 | 擋 | (vi) `PUSH-CONTENT-MISMATCH`（AT-749-4-E-7） |
| 修改巡邏提交，夾帶 OBS 帳本任意改寫、或在本 PROP 提案目錄加任意檔 | **放行** | OBS 帳本與提案目錄只檢路徑、不檢內容（事件帳本才有追加式判準）→ 新 R-26（P3） |
| 遠端已前進 | 有界 | `origin/main` 為本機追蹤參照（未 fetch），重複判準可能看不到遠端新提交，但推送會被 non-fast-forward 拒絕（`PUSH-REJECTED`、`retry:never`），不會推錯 |
| 兩個 APP 交錯（A 的提交在 B 之後） | 正常 | 逐提交各自判；帳本追加式以各自父 blob 為前綴，順序無關 |
| rollback 提交 | 正常 | (ii) 接受 `app.rollback`、(vi) 以其 `post_sha256` 綁定（AT-749-3-1） |
| M 類「只含帳本」的提交被冒用 | 擋 | 冒用者須正好是新增該 APP 事件行的那一個提交且一對一；另起提交＝`PUSH-APP-REUSED` 或 `PUSH-CONTENT-MISMATCH`（E-8） |
| **巡邏器自己的提交被誤擋** | **會發生** | `_commit` 實際 `git add` 整個 `PROPOSALS_REL`（`patrolrun.py:315`），而 (v) 只准本 PROP 的提案目錄 → 新 R-25（P2） |

結論：R-06 原指的「照抄格式即放行」已封住，P2 結案；殘留與連動缺口另立 R-25、R-26。

### 二審 3. 新發現（受影響範圍內）

| 編號 | 嚴重度 | 位置 | 問題 | 建議修法 | target |
|---|---|---|---|---|---|
| R-23 | P2 | TCS-P7 L304（AT-790-5-E-1 列尾 `\|\|` 黏上 AT-790-4-2）、§5 映射（L436）、L45／L397 計數 | 表格斷列：AT-790-4-2 不在列首而黏在上一列尾端，渲染後成為 AT-790-5-E-1 的多餘欄；§5 映射表把 AT-790-4-2 漏掉（一審版有）。實際 AT 為 **115**（正控 75、負控 40；RD 54），宣稱 114（RD 53）；映射缺 1 | 把 AT-790-4-2 拆回獨立一列；§5 映射補回；L45、L397 與 SA 交卷改 115／75／RD 54 | root |
| R-24 | P2 | TCS-P7 AT-747-11-3（L132）vs §2.2（L344-348） | AT 釘 `push` 鍵集合恰九鍵（無 `retry`）且「其餘 str 或 null」；§2.2 定為十鍵（含 `retry`）、`state`／`code`／`text` 恆非空 str。照任一方實作，另一方必紅 | AT-747-11-3 鍵集合加 `retry`、型別改依 §2.2（`code`／`text` 非空、`retry` 僅 `failed` 時非 null），並寫明鍵序 | root |
| R-25 | P2 | 守門 (v)（TCS L206、PRD L660）vs `_commit`（`patrolrun.py:315` 把整個 `PROPOSALS_REL` 加入候選）；AT-749-2-E-1 只要求「白名單」 | 無人運轉依任務書不 commit（SOP L654），會留下他 PROP 的未提交提案檔（`dirty_paths` 視為 SI 自有、不擋 promote）；下一次巡邏 promote 提交會把它們一併收進去，守門判 `PUSH-PATH-OUTSIDE`，該提交與其後所有巡邏提交都推不出去，直到人工處理——自動推送在常態下失效 | 規格明定 `_commit` 的 `git add` 範圍＝該 PROP 的 `touched`（repo 內）∪ `SI_OWN_ALLOW(PROP)`（與守門同一常數，單一來源）；AT-749-2-E-1 加子案「他 PROP 提案目錄有未提交檔 ⇒ 不被收進巡邏提交，且該提交通過守門」；§4 允許集合確認 `patrolrun.py` 已在列 | root |
| R-26 | P3 | 守門 (v)／(vi)（TCS L206）；PRD L660 誠實劃界 | `SI_OWN_ALLOW` 中 OBS 帳本與本 PROP 提案目錄只檢路徑、不檢內容：修改巡邏提交時可改寫或刪除 OBS 既有列、在提案目錄加任意檔，仍會被推上 `main`；`_commit` 也會把無人運轉手寫、未經人看過的 OBS 列一併推出。PRD 劃界只提事件帳本 | OBS 帳本比照事件帳本加「父 blob 為本 blob 前綴」（追加式）判準；提案目錄只准新增或修改 `r<rev>.*`、`verify*.json` 等已知檔名；或在 PRD 劃界明寫此面不擋及其偵測方式 | root |
| R-27 | P4 | AT-749-6-3（L238）；SOP L225、TCS §2.4（L363）、AT-749-11-2（L276）；AT-790-5-1（L303）；L160／L161、L373 | ①AT-749-6-3 寫「除 `SI_OWN_ALLOW` 與提案目錄外乾淨」，實際判準 `sched.dirty_paths` 排除的是 `_OWN_PREFIXES`（另含 `research_registry.json` 與回測目錄，`sched.py:32-33`）；②`PUSH-INTERNAL-ERROR`（rc 1）未列入三處 rc 契約；③AT-790-5-1 引用不存在的「PRD AC-P7-090-5」（自增 AC 只住 TCS）；④L373 兩個條列黏成一行（「不得單側改。- 時鐘縫」）、L160 後缺空行 | 措辭改成與 `sched.dirty_paths` 一致；rc 表補列；改為「本檔自增 AC-P7-090-5」；修排版 | root |

### 二審 4. 已發布規格〔訂正〕對既有 AT 的影響

- TCS-P4 勘誤三（L883）：AT-436-5-E-1 的三個斷言保留不變，且由 AT-747-11-2 反向釘住 OFF 路徑不取鎖、不多寫日誌，不會使該 AT 失效。
- AT-436-3-1（`test_selfimproving_schedule_patrol.py:77-90`）由 AT-747-8-1 保護，不會失效。
- 勘誤二（P4）、勘誤十三（P5）、E-10（P6）在一審後沒有改動，結論不變。

### 二審 5. 最終結論

**CONDITIONAL**（無 P1）。仍未結的 P2 有四筆：根層 R-23、R-24、R-25，Console 端 R-07。另有 P3 兩筆：R-26（root）、R-08（console）；P4 一筆：R-27。一審其餘 20 筆根層發現已確認修正。放行前須修畢 R-23、R-24、R-25，並由 Console 鍵處理 R-07；之後只需重驗受影響條目。

---

## 三審（2026-11-11；範圍只限 R-23～R-27 與這次修訂的連動面；Console 端 R-07／R-08 由 Console 審查者驗，不計入本結論）

**做法**：讀現行 TCS-P7（647 行）、PRD AC-SI-49-2～49-4（L659-660）、SOP rc 表（L225）。用 PowerShell 逐列解析：列首 AT **124** 筆（正控 78、負控 46；RD 54、MM 11、PU 59），零重複；全表沒有「`||` 黏列」；每列 AT 的未轉義直線數（排除反引號內）都是 5，即 4 欄；§5 映射抽出的集合與定義集合差集為空；L45 與 L409 宣稱都是 124。另對照 `patrolrun.py:308-333`（`_commit`）、`sched.py:32-33`。

### 三審 1. R-23～R-27 逐條

| 編號 | 結論 | 依據 |
|---|---|---|
| R-23 | 已修 | 實數 124／78／46 與 L45、L409 一致；AT-790-4-2 已是獨立一列（L314）並列入 §5；欄數全部正確 |
| R-24 | 已修 | AT-747-11-3（L132）：十鍵、鍵序同 §2.2、`state`／`code`／`text` 恆非空 str、`retry` 值域，與 §2.2（L354-358）一致 |
| R-25 | 已修（但 AT-749-2-2 夾具自相矛盾，見新 R-28） | `pushguard.commit_allow` 為 `_commit` 與守門 (v) 的共同來源（TCS L204、L208；PRD L659-660）；`_commit` 不再含整個 `PROPOSALS_REL`、`git commit` 帶 pathspec；`COMMIT-LEFTOVER`（附錄 A.3 L565） |
| R-26 | 已修（PRD 留下一句矛盾，見新 R-29） | (vii) `commits.jsonl` 紀錄判準與 (viii) 帳本差分三規則；AT-749-2-3、3-2、4-E-12～E-17；附錄 A.4（L586-588）與 A.4b 第 4 步（L607）已收新碼；amend／rebase／照抄的 sha 改變後必定 `PUSH-NOT-RECORDED` |
| R-27 | 已修 | AT-749-6-3（L247）乾淨判準改為與 `sched.dirty_paths` 一致；§2.4（L374）與 SOP L225 已列 `PUSH-INTERNAL-ERROR`；AT-790-5-1 改「本檔自增 AC-P7-090-5」；L385 條列已拆行 |

### 三審 2. 主控指定的三個連動面

1. **提交紀錄與 `_commit` 的時序**：紀錄在 commit 成功之後才寫。寫入失敗（AT-749-2-3）或巡邏在兩步之間被殺，結果都是該 sha 沒有紀錄，守門回 `PUSH-NOT-RECORDED`，屬安全側失敗，不會推錯。代價：被殺時不會留下 `COMMIT-RECORD-FAILED` 筆記，該提交與其後所有巡邏提交都卡在 `blocked`，直到人工推送。AT-749-4-E-16 寫「補寫紀錄（人工確認後）才放行」，但規格沒有任何補寫的動詞或步驟；另外紀錄的 sha 若在 commit 之後以 `rev-parse HEAD` 取得，互動視窗恰好在中間 commit 時會記到別人的 sha（仍然會被 `RECORD-MISMATCH`／`NOT-RECORDED` 擋，安全側）→ 併入新 R-30（P4）。
2. **`COMMIT-LEFTOVER` 會不會讓下一次 promote 被 dirty-tree 永久擋住**：不會。留下的檔若是 SI 自有路徑（他 PROP 提案目錄等），`sched.dirty_paths` 本來就排除，不擋 promote、也不擋推送；若是非 SI 自有檔，promote 在提交之前就已被 `dirty-tree` 前置擋下，根本不會產生提交，所以不是新增的阻擋。但這也說明 AT-749-2-2 的夾具不可能成立（新 R-28）。
3. **守門清單與 `commit_allow` 是否同一份**：路徑是同一份（同一函式、同一個 `touched` 來源 `sandbox.prop_context`、同一個 `cls`）。但守門另有 (viii) 帳本差分規則，`_commit` 不檢查：OBS 帳本若有人改過既有列但未提交，或提案目錄裡已追蹤的檔被改過，`_commit` 會照樣收進巡邏提交，守門再判 `PUSH-LEDGER-RULE`，結果是巡邏器自己的提交推不出去。這是安全側失敗，不是繞過 → 新 R-31（P3）。

### 三審 3. 新發現

| 編號 | 嚴重度 | 位置 | 問題 | 建議修法 | target |
|---|---|---|---|---|---|
| R-28 | P2 | TCS-P7 AT-749-2-2（L204） | 夾具「工作樹另有一個已 `git add` 的無關檔」與兩條既有判準互斥：①promote 前置要求除 SI 自有路徑外乾淨（P4 R155 (d)、AT-747-10-2 `dirty-tree`），有這個檔 promote 就不會發生、也就沒有提交；②即使有提交，`pushguard.evaluate` 也會先回 `PUSH-DIRTY-TREE`（AT-749-5-1），與本 AT 的「隨後 `evaluate` 回 `ok=True`、真推送成功」矛盾。這條 AT 照寫無法同時綠 | 把「無關檔」改為 `sched.dirty_paths` 會排除、但不在 `commit_allow` 內的已暫存 SI 自有路徑（例：已 `git add` 的 `research_registry.json`，或他 PROP 提案目錄的已暫存檔），斷言它不進巡邏提交、仍留在 index；另以一個子案寫明「非 SI 自有髒檔 ⇒ promote 被 `dirty-tree` 擋、零提交」 | root |
| R-29 | P3 | PRD AC-SI-49-3／49-4（L660）；TCS §2.3 標題（L361） | PRD 同一條同時寫「(vii) `push/commits.jsonl` 紀錄」和「無狀態、不另立『自有提交清單』」，前後矛盾；TCS §2.3 標題「只由 `push-run` 寫、由巡邏器唯讀」與表內 `commits.jsonl` 由巡邏器寫入矛盾 | PRD 刪去「無狀態、不另立自有提交清單」，改寫成「紀錄只作必要條件、寫失敗即安全側不推」；§2.3 標題改成「`push-run` 與巡邏器各寫其檔（見寫入者欄）」 | root |
| R-30 | P4 | AT-749-4-E-16（L234）、AT-749-2-3（L205）、§2.3 `commits.jsonl` 列（L368） | 「補寫紀錄（人工確認後）才放行」沒有規定機制（沒有動詞，也沒寫是否只能人工推送）；紀錄的 sha 取得方式未定（應取自本次 commit 的結果，不可在之後另讀 `HEAD`）；巡邏在 commit 與寫紀錄之間被殺時沒有筆記，只剩 `PUSH-NOT-RECORDED` | 明寫恢復路徑為「人工確認後由互動主控 `git push`」，或在 SOP 碼表給出處置；規定 sha 取自 commit 當下（例如 `git commit` 後立即在同一 `_commit` 內以 `rev-parse` 比對其 trailer）；在 SOP〈自動推送〉碼表補 `PUSH-NOT-RECORDED`／`PUSH-RECORD-MISMATCH`／`PUSH-LEDGER-RULE` 的處置 | root |
| R-31 | P3 | AT-749-2-2、守門 (viii)（L208）、`_commit` | `commit_allow` 只共用路徑、不共用 (viii) 帳本差分規則：工作樹中違反規則的 SI 自有改動（改寫 OBS 既有列、改既有提案檔）會被 `_commit` 收進巡邏提交，守門回 `PUSH-LEDGER-RULE`，自動推送因此停擺（安全側） | `_commit` 在 `git add` 前以同一組 (viii) 判準篩檔：違規的路徑不收（留工作樹並記 `COMMIT-LEFTOVER`），或整次不 commit 並記專屬碼；補一條 AT（工作樹 OBS 既有列被改 ⇒ 巡邏提交不含它、守門放行） | root |

### 三審 4. 最終結論

**CONDITIONAL**（無 P1；Console 端 R-07／R-08 不計入）。R-23～R-27 五筆都已確認修正。根層仍未結的有：R-28（P2）、R-29（P3）、R-31（P3）、R-30（P4）。修畢 R-28 即可轉 PASS；R-29～R-31 建議同批處理。

---

## 四審（2026-11-11；範圍只限 R-28～R-31 與其連動面；Console 端不計入）

**做法**：讀現行 TCS-P7（651 行）、PRD AC-SI-49-2 與 AC-SI-49-3／49-4、SOP〈自動推送（P7）〉碼表。以 PowerShell 逐列解析：AT **127** 筆（正控 80、負控 47；RD 54、MM 11、PU 62），零重複、零黏列，每列都是 4 欄；§5 映射與定義集合差集為空；L45、L412 都宣稱 127／80／47，AC 共 38（L460）。三者一致。

### 四審 1. R-28～R-31 逐條

| 編號 | 結論 | 依據 |
|---|---|---|
| R-28 | 已修 | AT-749-2-2（L204）夾具改為只放 `sched.dirty_paths` 會排除、但不在 `commit_allow` 內的 SI 自有路徑（他 PROP 提案目錄的未提交檔、已暫存的 `research_registry.json`）；先斷言 `dirty_paths` 為空且 promote 成功，再斷言提交只含本 PROP 路徑、之後真推送成功。與 promote 的 `dirty-tree` 前置、守門的 `PUSH-DIRTY-TREE` 都不再互斥 |
| R-29 | **部分修正** | TCS §2.3 標題已改為分列寫入者（`commits.jsonl` 只由巡邏器 `_commit` 寫）。但 **PRD AC-SI-49-3／49-4 仍保留「無狀態、不另立『自有提交清單』」**，與同條 (vii) 的 `commits.jsonl` 矛盾；修訂者所稱「三者缺一不可」字樣在 PRD 中查無（Grep 零命中）→ 仍未結 |
| R-30 | 已修（殘留一點見新 R-33） | AT-749-4-E-16（L237）明定沒有補寫機制、`PUSH-NOT-RECORDED` 對自動推送是終局、只能人工推送，且涵蓋「commit 與寫紀錄之間被殺」；AT-749-2-4（L206）定 sha 取自 commit 後的 `git rev-parse HEAD`；SOP L564-565 補上 `PUSH-NOT-RECORDED`／`PUSH-RECORD-MISMATCH`／`PUSH-LEDGER-RULE` 的處置 |
| R-31 | TCS 已修（PRD 未同步，見新 R-32） | `pushguard.ledger_rule_problems` 為單一函式，`_commit`（`git add` 前，HEAD 對工作樹）與守門（父提交對該提交）共用，AST 鎖第二份實作（AT-749-2-5）；違規時不提交、不寫紀錄、記 `COMMIT-LEDGER-RULE`（AT-749-2-E-2 三子案、附錄 A.3 L568） |

### 四審 2. 連動面檢查

- AT-749-2-E-2 的後果：`_commit` 拒提交後，promote 已套用的觸及檔會留在工作樹，對其後的 promote（`dirty-tree`）與推送（`PUSH-DIRTY-TREE`）都是阻擋，直到人工處理。這與該 AT「人工檢查後自行提交」一致，屬安全側，不另立發現。
- 紀錄的 sha 改為「commit 之後 `rev-parse HEAD`」：若互動視窗剛好在兩步之間 commit，會記到別人的 sha。結果是巡邏提交 `PUSH-NOT-RECORDED`、別人的提交 `PUSH-RECORD-MISMATCH`／`PUSH-FOREIGN-COMMITS`，兩者都不會推送，屬安全側；但規格沒寫這個競態。另外 AT-749-2-4 有一句語意不通（「以夾具讓 hook 之外的 post-commit 行為改 HEAD 以外值不可行」）→ 新 R-33（P4）。
- 數量、映射、欄數皆一致（見上）。

### 四審 3. 新發現

| 編號 | 嚴重度 | 位置 | 問題 | 建議修法 | target |
|---|---|---|---|---|---|
| R-32 | P3 | PRD AC-SI-49-2（只寫了 `commit_allow`）；全 PRD 無 `ledger_rule_problems`／`COMMIT-LEDGER-RULE`／紀錄 sha 來源 | TCS 新增「`_commit` 先跑帳本差分規則、違規不提交」（AT-749-2-5、2-E-2）與 sha 取得方式（AT-749-2-4），但 PRD 未同步。TCS §4A 寫明「與 PRD 不一致處以 PRD 為準」，等於把新行為放在一個上位文件沒有依據的位置 | PRD AC-SI-49-2 補一句：`_commit` 在 `git add` 前以 `pushguard.ledger_rule_problems` 檢查，違規＝不提交、不寫紀錄、記 `COMMIT-LEDGER-RULE`；紀錄的 sha 取自 commit 後的 `rev-parse HEAD` | root |
| R-33 | P4 | AT-749-2-4（L206） | 一句語意不通；commit 與 `rev-parse` 之間若有互動視窗 commit 的競態未寫明（結果為安全側） | 刪掉該句，改寫成「若兩步之間 HEAD 被他人前進，紀錄將對不上，守門以 `PUSH-NOT-RECORDED`／`PUSH-RECORD-MISMATCH` 擋下（安全側）」；可選：`_commit` 寫紀錄前核對該 sha 的 trailer 等於本次 APP／PROP，不符即記 `COMMIT-RECORD-FAILED` | root |

### 四審 4. 最終結論

**PASS**（根層；無 P1、P2；Console 端 R-07／R-08 依指示不計入）。R-28、R-30、R-31 已確認修正；仍未結的都屬非阻擋級：R-29（P3，PRD 仍留「無狀態、不另立自有提交清單」）、R-32（P3，PRD 未同步 `_commit` 的帳本差分規則與 sha 來源）、R-33（P4，AT-749-2-4 措辭與競態說明）。建議在 Stage-1 凍結前一併補進 PRD，以免凍結後還要走勘誤。
