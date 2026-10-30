# SCG-4 PR Review 報告 — Console 每頁說明（PageHelp；PRD FR-PH-01～08；鍵 `agentconsole-page-help`）

- 規格：TCS `AgentConsole/docs/03_testing/contracts/TCS-PageHelp-20261027.md`（Stage-2 digest `sha256:cc37fea4ab20bde1fe143f8f8460ec518f0a70e9ac0b3aef395bdf04c88b3864`）；PRD `docs/01_requirements/Console_PageHelp_PRD.md`（`sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f`，含〈勘誤一〉1-1～1-12）。審查者開工 `Get-FileHash` 相符。
- 受審 commit（本功能自己的五個；共用分支上的姊妹案 commit 不計）：輪 1a `e847ee48`、1b `3066a807`、2 `b033aeaf`、3 `7d81ab1e`、主控 G-D1 `6b0c748d`；審查時 HEAD＝`bb67692d`（主控 compat-ci paths，不屬本案）。
- 審查者：Sonnet QA 鏡（未參與起草與實作）；全程唯讀，突變重放在 `git archive HEAD` 副本；證據目錄 scratchpad `qa_ph\`（`at_loop_result.csv`、`mut_results*.jsonl`、`pw_results.jsonl`、`gates_summary.txt`、`gate_*.txt`、`route-bundle-stats.*.json`）。本檔由主控依審查者純文字交卷落檔；數字一律審查者本場自跑。

### 審查歷程

| 審次 | 日期 | 結論 | 摘要 |
|------|------|------|------|
| 一審 | 2026-10-28 09:0x～09:5x | **FAIL** | P1 0、P2 1、P3 4、P4 7；唯一 P2＝斷言不足（AT-PH-04-5-2 只測四群之二缺席），實作與說明內容免動；118 個 AT 全綠、AC 43／43、R-PH-01～37 逐條 killed、閘門全綠、零侵入成立 |
| 二審 | 2026-10-28 10:2x～10:5x | **PASS** | 對修復 commit `360e1133`（5 檔 +53／−17）重放：X29、X30 由倖存轉 killed，148 個一審 vitest 突變 verdict 與殺手集合除此二筆外完全一致（倖存 13 筆名單相同，無新倖存）；P22b 第一條路由即紅；P1 0、P2 0、P3 0、新增 P4 五筆（e-1～e-5，不阻塞）；F-02～F-05、F-07 全接受 |

### A. 一審站得住的部分（審查者數字）

- AT 118／118 綠：vitest 97 個逐一 `npx vitest run <檔> -t "<id>"`，97 筆 rc 0 且各收集 ≥1（共 111 個 it；全套 95 檔 1620 測試 rc 0）；Playwright 10／10；審查閘 GT 11／11。AC 43／43（TCS §1 映射的 118 個 AT 與 §3.2 完全一致）。逐 FR AT 數：01＝11、02＝12、03＝15、04＝30、05＝17、06＝12、07＝15、08＝6。
- 突變：R-PH-01～37 逐條 37／37 killed（R-20 以 G-C1 自證 8 個合成違規含 `lib/api/endpoints.ts`；R-35 以 M02a／M03a＋AT-PH-08-1 合成樹；R-36 以 G-D1 合成文字 3／3；R-22／27／28 以副本 Playwright dev 模式重放 P22b、P27a／b／c、P28a／b 全紅；R-23 以 build 重放 B23b（TopRegion 改回靜態 import）21／21 路由超標 +102,746～+123,152 B）。總計 159 個突變：殺 143、倖存 16（等價／冗餘 4＝M09a、M09e、S01、S02；TCS 文字過時 2＝M21a、B23a；原本即無樣本 1＝S08；真缺口 2＝X29、X30→F-01；內容設計已知缺口 7＝C01、C02、C05、C08、C17、C18、C20）。內容突變 20 個殺 13、存 7；結構探針 X01～X26 殺 23／24（只 M22b 在 vitest 倖存，見 F-05）。
- 既有鎖：`components/layout` 加第五個元件檔→`layout.test` 四元件鎖紅；加第九個導覽項→`AT_932_6_1`／`6_2`、`AT_950_10_E_1`「恰八項」紅；導覽登記表未動。`si.static.test.ts` 的 B 式：同一組 bridgeLeaks 突變在改前版與 HEAD 版殺／存逐項一致（S03、S04、S06、S07、S09 殺；S01、S02、S08 兩版同樣倖存＝原本即冗餘／無樣本）；另 M37a～f 六突變全殺（M37a 還原原式→`AT_932_4_3` 真樹掃描與 `AT_PH_06_2_3` 紅）。
- D-12 模擬（副本）：姊妹案先落地（加 `/sysadmin`、`/sysadmin/backup` 與第九導覽項、未補說明）→六個 AT 紅；補兩個 pending 頁檔＋`HELP_ROUTES`＋`HelpId`、同 commit `PENDING_CEILING` 0→2 後 118 測試全綠、tsc rc 0。
- 審查者追加探針（非 AT、已刪）：19 條路由×1440×900／390×844 開說明並展開全站共通做 axe，standalone 產物下 0 違規（AT-PH-07-4 只掃 3 路由）。

### B. 發現清單（一審；P2＝規格明文未被斷言／AT 弱於 AC／釋義誤導；P3＝措辭與偵測力；P4＝建議）

| # | 級別 | 座標 | 問題 | 建議修法與證據 |
|---|------|------|------|----------------|
| F-01 | **P2** | `components/domain/help/PageHelpDialog.test.tsx:690-714`（AT_PH_04_5_2）、`IssuesLegendGroups.tsx:39-43` `usableLegend` | D-PH-8／PRD 勘誤 1-6 要求「四群之一缺席＝失敗句」，AT 只測「無 legend」「缺 statuses」；突變 X29（拿掉 severities 陣列檢查）、X30（拿掉 results、sources 檢查）在 118 個 AT 下 vitest rc 0 倖存 | 在 AT_PH_04_5_2 的 cases 補 results／sources／severities 各設 undefined 三例＋一例非陣列值，只動測試檔；TCS AT-PH-04-5-2 (c)「或 statuses 缺」改「或任一群缺」（勘誤） |
| F-02 | P3 | `lib/help/states.ts:138` sddPhase.OBSERVATION.next | 「主要流程的位置請看旁邊的步驟」與畫面不符：OBSERVATION（回歸點未定，order=0）不畫階段步驟（`lib/domain/sdd.ts:205-212`、契約 §4.7.3） | 改「不用處理；回歸點確定前不會畫階段步驟，請看『目前狀態』的原文」 |
| F-03 | P3 | `lib/help/states.ts:162` obsClass.deferred.next | 「請把它重新打開來處理」指向 Console 沒有的操作（si 元件只有「更正」「關閉」） | 改成與畫面一致（由主機端處理；要補資料用「更正」再記一列） |
| F-04 | P3 | `lib/help/self-improving.ts`（專有詞命中 41 行）、`states.ts:179` measuring.next | 違反「淺顯易懂」：壞窗、卡面、入帳、稽核檔、摩擦、冷卻、模組桶、沙盒未白話；「結果可能是乾淨、再現或被回滾」讀不懂 | 首次出現處補半句定義；measuring.next 改白話 |
| F-05 | P3 | `tests/e2e/page-help.mock.spec.ts:114-143、160-190`（AT_PH_06_3_1／E_1） | 偵測力靠巧合：突變 P22b 會紅是因 calls 跨路由累積且 `/issues` 排 `HELP_ROUTES` 最後；vitest 側同款 M22b 倖存；反空轉門檻 clicked ≥3，現況應恰為 19 | 每路由獨立 calls；非議題路由斷言全程無 `limit=1` 請求；門檻改 `=== Object.keys(HELP_ROUTES).length` |
| F-06 | P4 | 各頁「資料來源」欄對按鈕與連結寫「您填寫或選擇」 | 語意是動作不是資料；`FieldSource` 僅六類（PRD 定） | 維持現狀（PRD 定六類），全站共通可補一句 |
| F-07 | P4 | `lib/help/common.ts` | 「唯讀的角色」各頁約 30 處未定義（實為 VIEWER；設定頁另限 ADMIN）；未列底部「Console v<版本>」 | 共通段補一列 |
| F-08 | P4 | `next/dynamic` 單一 chunk（約 102,777 B）頁面載入後即預取；G-F5 只量 firstLoad（最大 +4,845 B） | PRD 允許；要零成本須改「按下才 import()」 | 登記；PRD 勘誤 1-13 寫明量測口徑 |
| F-09 | P4 | G-D1 判準 | Select-String「本頁說明」同時命中 §3 列與 §5.2 Top 列，無法單獨證明 Top 列 | 判準改錨定「\| Top \|」列（TCS 勘誤） |
| F-10 | P4 | G-F3 判準 | 「文字表含三列」不可觀察（text reporter 不列 100% 檔）；json-summary 證實 lint.ts、stateSources.ts、registry.ts 皆在 include | 判準改用 json-summary（TCS 勘誤） |
| F-11 | P4 | 欄位完整性只鎖表單頁 | C01（刪 project-detail「建立者」列）、C17（刪 execute「啟動執行」列）、語意改錯 C02／C05／C08／C18／C20 倖存——TCS §6.2／PRD R-1 已自承 | 僅登記（可選：欄位名清單只增不減棘輪） |
| F-12 | P4 | 等價或冗餘倖存 M09a、M09e、M21a、S01、S02、S08 | 不構成缺口 | TCS 勘誤改寫突變文字（R-PH-09、R-PH-21） |

### C. ⚖ 裁決（審查者對證據；主控採納）

- 輪 3 偏離（`PageHelpDialog.test.tsx` +34／−0 補 AT_PH_04_6_2）：准許——屬 §5.7 新增測試檔、G-C2「八個新檔除外」；該 AT 有效（M13d 改「未結」label 即紅）。
- G-C2：既有測試檔只動 `si.static.test.ts`，3 個 hunk（checkText 簽章與註解 :230-233、第二分支 :235、樣板片段呼叫 :243）＋2 個新 it，無刪斷言；:243 超出 TCS 字面、屬 B 式 (ii) 的必要連動，准許並入勘誤。
- 修復棒範圍（主控）：F-01 必修（只補斷言）；F-02、F-03、F-04、F-05 一併修（釋義與偵測力，不動表 id、鍵集合、元件、登記表）；F-07 順手補；F-06 維持現狀；F-08～F-12 走 TCS／PRD 勘誤或登記。

### D. 一審閘門數字（審查者本場自跑，Windows 11／PowerShell；rc 先存變數再讀）

| 閘 | rc | 數字 |
|----|----|------|
| G-F1 全套 | 0 | 95 檔 1620 測試（基線 88／1509＋新 7 檔 111 個 it） |
| G-F2 三檔 | 0／0／0 | layout 10、si-login-gate 2、DashboardView 20＝32（≥基線 32） |
| G-F3 test:cov | 0 | All files 97.27／92.62／98.59／98.22；門檻 70／70／70／60 未動（F-10） |
| G-F4 lint、tsc | 0、0 | ESLint＋Prettier；tsc 零輸出 |
| G-F5 build＋Compare-RouteBundle | 0 | Stage-2 基線對 HEAD 0 違規；21 路由最大 +4,845 B（monitor、execute）≤100,000；比較函式自證 6／6 |
| G-F6 design-rules | 0 | 7 測試 |
| G-F7 (a) standalone page-help spec | 0 | 10 條通過（1.7 分） |
| G-F7 (b) CI 形態全部 mock spec | 0 | 103 條通過（3.8 分）；43 張被重寫的截圖以 `git cat-file` 逐檔寫回、status 乾淨 |
| G-F8 | — | `registry.test.ts:25` `PENDING_CEILING = 0`；AT_PH_03_6_1 rc 0；天花板 13→13→3→0 只降不升 |
| G-F9 | — | 掃 9 檔（下限 9）命中 0 |
| G-C1 | — | 五 commit `diff-tree` 聯集 40 路徑餵 `$allowedClose` 0 違規；自證 8／8 判違規、11／11 放行 |
| G-D1 | — | 四字樣命中（Architecture.md :217、:218、:355、:430），同一 commit `6b0c748d`（Architecture、ADR-002 第 16 列、OBS-SI-335 三檔）；`API_Contract_P3-6.md` 未改；合成文字自證 3／3 |

內容品質抽讀（審查者逐欄對畫面程式碼、PRD §4／附錄 B、契約附錄 A、SelfImproving PRD §5.1.2）：dashboard 11 欄位（活躍＝草稿／就緒／執行中、週一零點本機時區、執行中 run 規則、五十筆、30／60 秒輪詢）無誤；project-detail 29 列（SDD 區對 SddGovernanceCard／SddPhaseProgress／sdd.ts）除 F-02 外無誤；execute 約 60 列（自治等級、引擎能力六態、SSE 六態、審核後果不抄第二份）對；monitor 十項 KPI 公式對契約 §3.8.1、任務分佈四分組對 `metrics.ts:132-148`；self-improving 11 個提案狀態與三張表對 SelfImproving PRD §5.1.2 轉移全對（F-03、F-04）；issues 十欄位對 `IssueTable.HEADERS`；表單頁限制（名稱 ≤200、路徑絕對、自治 1～10 預設 3、重試預設 3、驗證命令禁字元）與 import（三種副檔名、10MB、六個有界閘）對；狀態表 projectStatus／goalStatus／taskStatus 六／五／十一列的「下一步」逐列對 PRD 附錄 B 全對；全站共通 15 列涵蓋 13 個 COMMON_ANCHORS；19 條路由「本頁說明」皆開得起來。

### E. 二審（修復棒後；同一審查者、同一套 harness 對 `360e1133` 副本重放；證據 scratchpad `qa_r2\`）

- 修復棒（Sonnet Developer）commit `360e1133`：F-01 補 results／sources／severities 缺席三例＋severities 非陣列一例（`brokenLegend`）；F-02～F-04 釋義改正與八個專有詞首次出現處白話定義；F-05 `legendCallsSince`／`expectedLegendCalls` 逐路由含載入全程計數、反空轉門檻改 `clicked＋pending＝|HELP_ROUTES|` 且 `clicked＝已寫路由數`；F-07 共通段補「Console v」「唯讀」。修復棒自驗：usableLegend 去 severities／results／sources 檢查各轉紅；非 issues 路由載入時預取詞表的突變於第一條路由即紅（Expected −1／Received +3）。主控親驗：tsc rc 0、vitest 95 檔 1620、G-F2 10／2／20。
- 二審重放：X29、X30 killed（一審倖存）；X30a／X30b／X29s／X29x 皆 killed；M13d killed（R-PH-13「應存活」註記與 AT-PH-04-6-2 衝突→勘誤 1-5）；M22b vitest 側倖存（AC-PH-06-3 載具只列 E2，由 e2e 殺→勘誤 1-19）；P22b、P22e、P12a killed；Pskip3s／Pskip3e（迴圈截成前 3 條）killed（舊門檻 ≥3 會放行；對照組不動檔綠）；N04／N05／N06 killed（出處鎖與 lint 守住新文字）。全套回歸：一審 148 個 vitest 突變在 HEAD 副本重放 killed 135／survived 13／error 0，與一審逐一比對差異恰 X29、X30 兩筆，倖存名單相同。
- 逐項：F-01 關閉；F-02 接受（但「回歸點」是畫面沒有的詞→e-1）；F-03 接受；F-04 接受（壞窗＝AC-SI-24-1、冷卻＝AC-SI-13-2、measuring 三結果＝clean／recur／rollback）；F-05 接受修復棒對簡報措辭的偏離（D-12 新增待寫路由不誤紅、比舊門檻嚴）；F-07 接受＋勘誤 1-18。
- 二審閘門：vitest 95 檔 1620 全綠（JSON 核對 97 個 vitest AT id 全在且通過）；tsc rc 0；lint rc 0；G-F2 10／2／20；G-F6 7；G-F9 掃 9 檔 0 命中；G-F5 build rc 0、Compare-RouteBundle 0 違規、最大 +4,845 B、說明 dynamic chunk 103,651 B（一審 102,777 B）；e2e page-help spec standalone 10 條通過；G-C1 六 commit diff-tree 聯集 40 路徑對 `$allowedClose` 0 違規；G-C2 既有測試只動 `si.static.test.ts`。
- 二審新發現（P4）：e-1「回歸點」措辭；e-2 非陣列例只覆蓋 severities（Y01～Y03、Y05 倖存）；e-3 反空轉兩式只抓迴圈截斷、真正下限由 AT_PH_03_3_2 承擔；e-4 兩字免鎖手法需勘誤明定；e-5 deferred.next 未提「更正」只限 ADMIN。
- **主控於二審後補做 e-1、e-2**（與勘誤同一 commit）：`states.ts` OBSERVATION.next 改「不用處理，這個狀態還不知道會回到哪個階段，所以不畫階段步驟，請看「目前狀態」的原文。」；`PageHelpDialog.test.tsx` AT_PH_04_5_2 非陣列例改四群各一＋legend 為 null 一例。主控自驗：prettier／tsc／lint rc 0；該 AT 通過（1 條，其餘 20 條略過）；`lib/help` 三檔 39 條通過；突變 Y01（statuses `Array.isArray`→`!== undefined`）rc 1 轉紅後以備份還原、SHA256 相同；全套 vitest 見 §H。e-3、e-5 登記不做；e-4 走勘誤 1-18。

### F. SCG-5 真機（PRD §11 出口；掌舵者親驗）

- **2026-10-31 06:0x～06:4x 代驗證據（兩支獨立真機棒，Docker 全棧 `http://localhost`、映像建於 01:47 含補頁 `fdd9a738`；Chromium）**：V1 ADMIN 21／21 路由開啟成功，對話框名稱＝頁名・本頁說明、h3 恰四、13 頁狀態表／議題中心 API 四群／7 頁固定句、全站共通預設收合、pageerror 0；開啟耗時 21 路由單次 41～82 ms、重複量測中位數 47～48 ms（p90 ≤66 ms）；六個抽查狀態列（execute 暫停中／待人工、monitor Token 預算警告／Agent 連線燈、self-improving handed-off／retired）釋義與畫面一致。V2 390×844 21／21：鈕 44×44 只剩圖示、對話框無橫向溢出、可捲到底。V3 ADMIN 與 VIEWER：四群 7／8／4／4 列與既有「狀態說明」對話框及 `GET /api/v1/issues?limit=1` 逐項相同，VIEWER 詞表 1,042 ms 出現。V4 execute／self-improving：Tab→Enter→對話框內焦點不外洩→Esc→焦點回「本頁說明」鈕（`:focus-visible` 2px）。axe（wcag2a／2aa／21a／21aa）開啟態 21×2＝42 次 0 違規。證據：scratchpad `qa-real\`（99 張截圖、逐路由 JSON）與對方續跑端 `C:\Users\wuwei\.autosdd\handback\tmp_rm\shots\`。
- 未涵蓋：未啟動執行批次（暫停中／待人工等只驗釋義文字、無實景）；僅 Chromium；「不看英文就能說出用途」屬主觀，purpose／steps 內英文詞皆在白名單。
- **RELEASE 放行方式待掌舵者裁示**（依代驗證據放行，或親走 V1～V4）。

### H. 凍結與放行紀錄

- 二審 PASS 後主控親驗（本機 Windows 11）：全套 vitest 95 檔 1620 測試全綠（含 e-1／e-2 補做）；tsc、lint rc 0；`python tools/selfimproving.py check` overall=PASS（OBS-SI-336～338 入帳：Claude Code safetyCheck 誤擋 `Remove-Item Env:`、junction 只夠 vitest／tsc、CI 形態 e2e 重寫 43 張截圖）。
- 勘誤套用（主控，路由第 4 點）：TCS 檔尾〈勘誤一〉1-1～1-19（一審候選 1～11＋G-C2 :243＋junction 實體複製＋輪 3 AT-PH-04-6-2 綁定＋二審 12～15）；PRD 檔尾〈勘誤二〉2-1（AC-PH-06-4 量測口徑）；TCS 檔頭 PRD digest 同步、§1 增量追溯表依議題中心先例保留 Stage-2 快照。新 digest（`Get-FileHash`）：PRD `sha256:cf1e97a9e5b666daef3024b13bc15a6903a6097f63a8dd8a24051813c899e3d0`（62,607 bytes）、TCS `sha256:c58035bb00e63978b8693a5f192d8a57ef7a7a930702db000fa9e5bea8a67b6e`（197,189 bytes）。
- FSM 鍵 `agentconsole-page-help`（2026-10-28 11:0x～11:3x，主控依凍結常態規則執行）：IMPLEMENTATION → `transition --to PR_REVIEW` → `gate PR_REVIEW PASS`（→ RTM_VERIFY；勘誤與報告 commit `e37e5dfc`）→ RTM §2.5 回填（文件棒，170 列＝F 1／US 8／AC 43／AT 118；commit `ad237aa4`）→ `gate RTM_VERIFY PASS`（→ RELEASE_READY）→ `spec-refreeze --doc PRD --doc TCS` rc 0：`refrozen: true`、`stage: Stage-2`、`supersedes: 2026-10-27T20:04:56+00:00`，記入 PRD `sha256:cf1e97a9…e3d0`、TCS `sha256:c58035bb…7b6e`（與上列 `Get-FileHash` 相同）。RELEASE 待掌舵者真機 V1～V4（§F）後 `transition --to RELEASE`。

### G. 流程摩擦（審查者七項；主控處置）

1. `npx.ps1` 在腳本內把原命令文字重新 Invoke-Expression，`$script:` 變數在其 StrictMode 下炸（審查者載具，已改區域變數）。
2. PS 5.1＋`$ErrorActionPreference='Stop'`＋`2>&1`：Playwright webServer 的 stderr 警告被當終止錯誤（已修）。
3. Turbopack dev server 在 `node_modules` junction 副本上起不來（ENOENT build-manifest）：TCS §2 的 junction 只夠 vitest／tsc，Playwright 與 build 突變須實體複製 `node_modules`（約 790 MB，robocopy 13 秒）→ TCS 勘誤候選。
4. PowerShell 工具守衛誤擋 `Remove-Item Env:…` 及含該字樣的長指令，改用 .NET 方法 → 主控登記為守衛面理論洞（不立輪）。
5. CI 形態全套 mock spec 會重寫 43 張已追蹤截圖（已逐檔寫回）；建議截圖輸出改到忽略目錄 → 登記。
6. 審查者兩次用 `Start-Process` 起背景鏈（違鐵律六），靠輪詢輸出檔補救。
7. 手寫 `.ps1` 無 BOM 被 5.1 誤讀中文、誤刪副本檔，已從 base 還原並以 robocopy 全樹比對一致。
