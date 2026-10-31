# SCG-4 PR Review 報告 — SelfImproving 決定重送去重與對帳取代標示（dedupe 增量；PRD FR-SI-33／35 的 Console 半；鍵 `agentconsole-si-decide-dedupe`）

**審查日期**: 一審 2026-11-01 00:05～00:51（QA 鏡重派；前一棒 2026-10-31 22:4x 因掌舵者切換帳號被主控中止、未交卷、中間產物不採信）　**審查者**: SCG-4 獨立 QA（Sonnet，唯讀；未參與規格撰寫與實作——規格作者＝SA 棒（QA 預審二審 PASS 後凍結）、實作者＝Sonnet Developer 棒，三方不同）　**主控親驗**: 2026-10-31 22:4x（Fable 5.1；backend gradle `*Si*`＋`*OpenApiIT*`、frontend vitest 全套／tsc／lint、help 測試、`git diff --name-only` 對 TCS §5.7）
**審查範圍**: 規格 commit `712ee3a9`（新 TCS＋契約 `API_Contract_SelfImproving_P2b.md` §8 增補）＋實作 commit `338a85f9`（35 檔：backend 主程式 13／測試 5、frontend 主程式 5／測試 5、主控代做 7——`Architecture.md` §11.1 新列與 OBS-SI-321 兩處漂移訂正、P2b TCS 勘誤 18～24、P1b TCS 勘誤 24～25、本鍵 TCS 勘誤 1～4、RTM 子表 `RTM-SelfImprovingDecideDedupe-20261031.md`＋`RTM.md` §2.7 存根、頁面說明 `lib/help/self-improving.ts`）。零 Bridge、零根層碼、零 Flyway、零 `.github`／`.claude` 改動。受審樹＝repo 外拋棄式 worktree（主控 handback 目錄下，detached @338a85f9），突變在 `git archive` 副本做。
**基準規格**: `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingDecideDedupe-20261031.md`（Stage-2 凍結 `sha256:fa73d3bf…8a86`；實作 commit `338a85f9` 當時值（勘誤 1～4）`sha256:99f5d306…dbea`，一審開工與交卷兩次相同；RELEASE_READY refreeze 後現值 `sha256:29a4db6b…5b0e`（勘誤 1～9）；AC 6／AT 25＝正 11＋負 14；W-D1～W-D6；D1～D6）　**上位**: 契約 §8（Stage-1 凍結 `sha256:32e60de7…2841`，兩次相同）；PRD v0.12 FR-SI-33／35；Architecture §10.3、§11.1；ADR-001；P2b TCS（含勘誤 18～24）。
**判決檔（逐字）**: 一審交卷全文在本 session 子代理逐字稿（主控 scratchpad `tasks\aed6c825ce1f2efa0.output`；原始日誌與腳本在 `scratchpad\qa\dedupe\r2\`：`wt_be`、`wt_fe`、`wt_zone`、`wt_fe_zone`、`mut_be`、`mut_fe`、`mut_fe_full`、`v3`）；本檔為其入庫摘要，數字皆為審查者或主控當回合親跑。

### A. FRD 功能規格一致性（AC 6／6；AT 25／25 單跑綠）

25 個 AT 在 worktree 逐一單跑（backend `gradlew cleanTest test --tests "<FQCN>.<AT>*"` 15 個皆 rc 0、XML 逐字每個 1 測試 0 失敗 0 錯誤 0 略過；frontend `npx vitest run <檔> -t <AT>` 10 個皆 rc 0、0 失敗）。

| AC-ID | 驗收標準（摘要） | 實作座標 | 測試（AT 正／負） | 一審結論 |
|-------|------------------|----------|------------------|----------|
| AC-951-1 | 決定重送閘：同一張卡的同一決定只能送出一次；只管帶 digest 的六個動詞；零副作用；閘門序在授權、停用、輸入閘之後、取 ref 之前 | `SiConsoleWriteService.rejectResend`、`SiConsoleWriteRepository.findDecideAuditRefs`、`SiConsoleWriteAdapter`（`DKIND` 表達式）、`ErrorReasons.SI_DECISION_DUPLICATE` | 2／4 | Pass（F-01：線上 reason 字面無斷言；F-02：`existingAuditRef`＝最早者無 AT） |
| AC-951-2 | dkind 的來源與兩個埠 | `SiConsoleWriteAdapter.DKIND`／`SUMMARY_COLUMNS`、`findDecideRows`、`SiConsoleWriteSummary.dkind` | 1／2 | Pass |
| AC-951-3 | 對帳的取代判定：整張表、最早已入帳者、同刻 audit_ref 字串序、`ingested` 仍為 false、量不到整欄 null | `SiReconcileService.supersededBy`（`DecisionKey`）、`SiReconcileUseCase.Item`、`SiConsoleWritesResponse` | 1／3 | Pass |
| AC-951-4 | 對帳面板：待入帳排除被取代列、預設收合的「已被取代」群組、dkind 標示、量不到不渲染 | `SiWritesPanel.tsx`（`si-superseded-list`／`-toggle`／`-items`、`Dkind`）、`lib/domain/si.ts`（`pendingWrites`、`supersededWrites`、`decideKindLabel`） | 2／2 | Pass（F-04：N=0 不渲染群組無斷言） |
| AC-951-5 | 決定對話框：只讀對帳快取、已送出待入帳的動詞停用、409 說明 | `SiDecideDialog.tsx`（`pendingByVerb`、`si-decide-dup`）、`useSiConsoleWritesCache`（`useSyncExternalStore` 讀 QueryCache、不建 observer）、`pendingDecision`、`siWriteErrorText` | 3／2 | Pass（F-03：多動詞同時命中無斷言；F-05：NOT-EVALUABLE 不停用只在契約外輸入下可觀察） |
| AC-951-6 | 契約面與既有釘選同步：十一鍵、409 說明、`schema.d.ts` 重產、§4 十二項只增不減 | `OpenApiIT.AT_951_6_1`、`si.endpoints.test.ts`、`SiReadOnlyArchTest`、`ErrorResponseDocumentation` | 2／1 | Pass（F-01：常數值＝字面由 AT-951-6-1 補釘） |

重點條文逐項核對（程式與測試皆讀過）：W-D1 閘排在授權→停用→輸入閘之後、取 ref 之前（m16 閘排到授權前→AT-951-1-E-3、AT-935-4-1 紅；m36 先取 ref→六個 AT 紅；m37 閘偷打 Bridge GET→紅）、不比 dkind／digest／subject 各自有 AT 紅（m38 族）、無 digest 動詞不受閘（m2 紅）；W-D2 `kind='decide'` 的 `case` 保護（m32 紅）、null digest 不比對（m4 紅）、升冪與同刻 audit_ref 字串序（m5a～m5e 紅）、dkind 區分大小寫（m6 紅）；W-D3 最早者（m7 紅）、整張表不看 limit（m8 紅）、`ingested` 不冒充（m9 紅）、取代判定忽略 subject／dkind／digest、null dkind、無 digest 動詞、已入帳列、兩列皆未入帳（m39～m45 全紅）；W-D4 待入帳排除被取代（m10 五個 AT 紅）、量不到不渲染（m18／m20 紅）、預設收合（m19 紅）、群組無入帳鈕（m26 紅）、排序與標籤（m28／m29 紅）；W-D5 不停用／多發 GET／toast 去編號／少第六鍵（m11～m14 紅）、比對規則（m21～m24 紅）；W-D6 十一鍵缺一（m15 七個 AT 紅）、`schema.d.ts` 少鍵或改必填（m31／m32s 紅）、409 說明覆寫鍵打錯或套到所有端點（m49／m51 紅）。`AT_940_5_1` 在 HEAD 綠，改 Architecture §11.1 新列的 reason 欄（md1／md2）使它與 `AT_951_5_3` 轉紅，證明仍解析該表。

### B. Contract 一致性（契約 §8；上位 P2b 契約 §0～§7 一字未改）
§8.3 十一鍵（`AT_951_3_1`、`AT_951_6_1`；m15 紅）；§8.2 409 details 四鍵與 `message` 含「請以對帳面板為準」（`AT_951_1_1`；`digest8` 缺席規則無可達路徑＝本鍵勘誤 3 已記）；§8.5 判定（m7～m9、m39～m45 全紅）；§8.6 文案逐字——toast 起首句「同一張卡的同一決定已送出（稽核編號 …），待主機入帳，不需重送」與對話框「已送出待入帳（稽核編號 …）」（m13、m34 紅）；§8.7 reason 常數落點（`SI_REASONS` 六鍵、不進 `REASONS`）。V3：審查者以拋棄式 IT 傾印 `/v3/api-docs`（282,467 bytes）→ `node scripts/gen-api.mjs` 重產 `schema.d.ts`，與入庫檔位元組相同（兩邊 sha256 `2d2f37bc…2360`）；decide 的 409 說明載明新 reason、observations 兩個 POST 不含（m49、m51 紅）。`git diff 712ee3a9^..712ee3a9 -- 契約`＝+84／-0 只追加。

### C. Business Invariants（零副作用、不刪列、不冒充、範圍）
閘零副作用：重送後列快照逐位元組不變、`MINI.si.writes` 與 `MINI.requests()` 筆數不變、ref 取用次數不變（m36、m37 紅）；被取代列不刪（DML 仍三條，`AT_951_6_E_1` 綠；`SiReadOnlyArchTest` 方法集合只加 `findDecideAuditRefs`／`findDecideRows`）；`ingested` 不冒充（m9 紅）；量不到整欄 null（`AT_951_3_E_2`）。範圍（G-C1）：`git diff --name-only 9f94e68a..338a85f9` 35 檔逐檔對 TCS §5.7，範圍外 0、非 `AgentConsole/` 前綴 0；`git diff --check` rc 0。§4 十二項逐 hunk只增不減（`AT_935_4_1` 改送不同動詞並新增 ops_admin 重送 approve＝409；`AT_950_5_E_2` 四次改四個動詞、writes 恰 4 與權杖斷言保留；`AT_935_3_2` 封閉集合加 `si-superseded-toggle`、`FORBIDDEN_NAME` 未放寬）。人讀：Architecture §11.1 新列與 `ErrorReasons` Javadoc 一致；P2b 勘誤 18～24 與 P1b 勘誤 24～25 的訂正方向與實際測試改法一致（僅 F-06 引句）；help 四個新欄名逐字出現在 UI 原始碼，`npx vitest run lib/help components/domain/help` rc 0（7 檔、109 個測試全綠）；RTM 子表 33 列（F1／US1／AC6／AT25），25 個 AT 列的實作檔缺 0、測試檔含該 AT 底線形缺 0；`AgentConsole/docs` 新增行「測試摘要字樣＋4 位數字同行」0 筆；新增測試行掃描：非真帳本編號 0（OBS-SI-348 只在註解）、`sk-` 0、skip／`.only`／`assumeTrue` 0、跨 AT 引用 0。全區（worktree）：gradle `*Si*`＋`*OpenApiIT*` rc 0、57 個 XML 逐字相加 249 個測試／0 失敗／0 錯誤／0 略過；vitest 全套 rc 0（101 個測試檔全綠）；tsc 0；lint 0；`ruff check AgentConsole/engine-bridge` 0。

### D. 一審發現表（P1 0／P2 4／P3 2／P4 2 ⇒ 判定 FAIL；P2 全為斷言不足，修法只補測試、不改實作、不改 AT 數）

| # | 嚴重度 | 座標 | 事實（審查者親跑） | 修法 | AC／AT |
|---|--------|------|--------------------|------|--------|
| F-01 | P2 | `ErrorReasons.java:146`；`SiConsoleWriteApiIT.java:324,693,728,794` | 線上字面 `si_decision_duplicate` 在後端無任何斷言：四處 `$.reason` 都比 `ErrorReasons.SI_DECISION_DUPLICATE`（常數比自己）。突變 m48（常數值改 `si_decision_duplicates`）：AT 集合 12 個綠、全區 249 個綠、architecture 套件 33 個綠，全存活；前端 `SI_REASONS` 只對 Architecture 表，後端打錯字時閘照擋、前端認不得 reason、toast 退回泛用文案 | 四處改比字面（常數斷言可留）；`AT_951_6_1` 加「常數值＝字面＝Architecture §11.1 表列」 | AC-951-1、951-6／AT-951-1-1、1-2、1-E-2、6-1 |
| F-02 | P2 | `SiConsoleWriteService.java:148` | W-D1「`existingAuditRef`＝回傳清單第一個＝time 最早、同刻字串序最小」無 AT：AT-951-1-1／1-2／1-E-2 的既有列都只有一列；AT-951-2-E-1 只鎖埠的排序。突變 m17（`existing.get(0)` 改末項）：AT 集合 11 個綠、全區 249 個綠，存活 | AT-951-1-2 以 `insertDecide` 預置同決定 ≥2 列（含同刻 UT1／UT2）再 POST，斷言最早者、同刻字串序較小者 | AC-951-1／AT-951-1-2 |
| F-03 | P2 | `SiDecideDialog.tsx:75-76`、`:201` | W-D5「命中者的 option 為 disabled、多個動詞命中則各一則 `si-decide-dup`」：所有 AT 最多一個動詞命中。突變 m46（只顯示第一則）、m47（只停用第一個命中）：三路徑 265 個綠，存活 | AT-951-5-1 情境一加第二列待入帳 reject，斷言兩動詞皆 disabled、兩則提示 | AC-951-5／AT-951-5-1 |
| F-04 | P2 | `SiWritesPanel.tsx:121` | W-D4「群組僅當對帳 ok 且被取代列數 ≥1 才渲染」的 N=0 半邊無斷言（AT-951-4-E-1 只鎖 NOT-EVALUABLE 半邊）。突變 m18b（條件改只看 `evaluable`）：三路徑 265 個綠，存活；退化後每位 ADMIN 都會看到「另有 0 筆已被取代…」鈕 | AT-951-4-E-2 加 (d)：ok、僅一般待入帳列、orphans 空 → 無群組、整頁不含「已被取代」 | AC-951-4／AT-951-4-E-2 |
| F-05 | P3 | `SiDecideDialog.tsx:73`；`SiWritesPanel.tsx:128` | 兩條條文只在契約外輸入下才可觀察：(1) W-D5 NOT-EVALUABLE 不停用——AT-951-5-E-1 (c) 樣本列 `ingested` 為 null，拿掉 `status !== ok` 防護（m35）仍綠；(2) 展開鈕 `aria-controls`（m50a 拿掉）仍綠 | (1) 樣本列改 `ingested:false`；(2) AT-951-4-1 加 `aria-controls` 斷言 | AT-951-5-E-1、4-1 |
| F-06 | P3 | `TCS-SelfImprovingMirror-P1b-20261021.md`（勘誤 25） | 勘誤引句「Bridge 或 backend 產生」不逐字存在；Architecture.md 實句為「多由 Bridge 產生、backend 逐字轉出，`si_decision_duplicate` 由 backend 自產」 | 勘誤改引實句（主控已改） | — |
| F-07 | P4 | `lib/help/self-improving.ts:166` | 「主機會拒絕第二次」：拒絕的是 Console 後端（409）；同檔「主機」指入帳的主機 CLI，語意混用 | 改「系統會拒絕第二次」（主控已改） | — |
| F-08 | P4 | 備註 | (i) Architecture.md 本 commit 另含 OBS-SI-321 兩處訂正（:334 目錄樹、:362 Tools 列），TCS 增量追溯表已揭露、檔案在允許集合內；(ii) `SiReconcileService` 每次 GET 全表掃 `findDecideRows`（⚖4 設計，表小）；(iii) `aria-controls` 收合時指向尚未渲染的 id（常見手法）；(iv) 群組節點排在「無待入帳」句之前（規格只定「待入帳清單之後」） | 事實記錄，不處置 | — |

### E. 突變摘要（副本 `git archive 338a85f9`；67 個、殺死 60、存活 7；任務書最低清單 m1～m15 全部殺死；每個突變後逐檔雜湊還原，最後 1,452 檔與 worktree 差異 0）
存活 7 個歸成 F-01（m48）、F-02（m17）、F-03（m46、m47）、F-04（m18b）、F-05（m35、m50a）；其餘見 A 節逐條。無 P1 的依據：閘零副作用（m36、m37 紅）、被取代列不刪（`AT_951_6_E_1`）、`ingested` 不冒充（m9 紅）、量不到整欄 null（`AT_951_3_E_2`）。

### F. 處置與二審（主控）
- FSM：`transition --to PR_REVIEW` → `gate PR_REVIEW FAIL`（retry 1，回 IMPLEMENTATION；2026-11-01 00:5x）。
- 修復棒 r1（Sonnet；准改集合＝`SiConsoleWriteApiIT`、`OpenApiIT`、`SiDecideDialog.test.tsx`、`SiView.test.tsx`、`tests/helpers/si.tsx`，實際只動前四檔；每項附突變自證）；主控同時改 F-06（P1b 勘誤 25 引句）與 F-07（help 文案）。AT 的 Given／Then 字面變動由主控寫本鍵 TCS〈勘誤〉5～9，RELEASE_READY 時 refreeze。
- **二審（2026-11-01 01:1x～01:3x；QA 鏡 Sonnet，worktree @546c8187，開工與交卷 porcelain 皆空）：PASS**——P1／P2／P3 皆 0，P4 2 條。一審七個存活突變重打（副本 `git archive 546c8187`，每個突變後以 worktree 同檔覆回、雜湊相等，最後 1,453 個 tracked 檔差異 0）全部轉紅、0 存活：m48 → gradle 249 個測試 5 失敗（`AT_951_1_1`、`1_2`、`1_E_2`、`AT_935_4_1`、`OpenApiIT.AT_951_6_1`，恰為本鍵勘誤 5 所稱五個，失敗點皆在新增的字面斷言行）；m17 → `AT_951_1_2`（新增 helper 的 `existingAuditRef` 斷言）；加碼 m17b（改取 `UUID.compareTo` 最小者）→ `AT_951_1_2` 紅；m46／m47 → `AT_951_5_1` 情境三；m18b → `AT_951_4_E_2` (d)；m35 → `AT_951_5_E_1` (d)；m50a → `AT_951_4_1`；frontend 每個突變皆恰 1 個 it 紅、還原後 73 個全綠。8 個受影響 AT 單跑 rc 0（backend 四個各 1 測試 0 失敗；frontend 四個 0 失敗，verbose 確認新增三個 it 確實有跑；四 AT 合跑重複 5 次皆綠，無 flaky）。修復 commit 對其父 `23cb8f3c`：`SiConsoleWriteApiIT` +42／−4（被刪 4 行是 `$.reason` 常數斷言，各改寫成字面＋常數並列）、`OpenApiIT` +4／−0、`SiDecideDialog.test` +48／−0、`SiView.test` +24／−0；斷言數只增（assertThat 272→279／222→223、expect 97→106／340→347）、`it(` 恰 +3、`@Test` 不變、skip／only／`@Disabled` 0；AT id 集合 25 個與 TCS 逐一相同；主程式零改動（唯一例外 `lib/help/self-improving.ts` 一行文案）。全區（worktree）：gradle `*Si*`＋`*OpenApiIT*` rc 0、249 個測試／0 失敗／0 錯誤／0 略過；vitest 全套 rc 0（101 個測試檔全綠，it 數較一審 +3）；tsc 0；lint 0；help 7 檔 109 個綠；checkstyle 0；architecture 套件 33 個綠。文件：本鍵 TCS 勘誤 5～9 與測試改法逐條一致；P1b 勘誤 25 引句在 `Architecture.md` 第 986 行逐字恰 1 次；凍結面 TCS `29a4db6b…` 與契約 `32e60de7…` 開工、交卷相同。
- 二審 P4：F-09 範圍檢查字面——`git diff --name-only 338a85f9..546c8187` 會多出 nightly 重鎖 commit `23cb8f3c` 的 `AutoClaude/.perf_baseline.toml`，不是修復 commit 所改（`git show --name-only 546c8187` 恰 8 檔皆在允許集合）；本報告範圍以各 commit 自身名單為準。F-10 `si-decide-dup` 文字的動詞標籤無斷言（加碼突變「標籤取下一個動詞」存活）；TCS／契約只規定含「已送出待入帳（稽核編號 X）」，標籤不在規格內，不處置。另註：F-01 修法落地只釘「常數＝字面」（`OpenApiIT` +4、本鍵勘誤 5），未另釘「＝Architecture §11.1 表列」——該對拍由前端 `AT_940_5_1`／`AT_951_5_3` 解析 §11.1 表承擔。
- 二審勘誤候選（只記錄）：RELEASE_READY refreeze 時可把勘誤 5～9 折回 TCS 本文；現行慣例只留勘誤表，本輪不折回。
- 判決檔：二審交卷全文在子代理逐字稿（主控 scratchpad `tasks\a7f990dd1e953467b.output`）；原始日誌 45 檔在 `scratchpad\qa\dedupe\r3\`（`summary.txt` 彙整每次 rc 與統計）。
- FSM 收尾（2026-11-01 01:3x）：`transition --to PR_REVIEW` → `gate PR_REVIEW PASS`（retry 1 後）→ `gate RTM_VERIFY PASS`（RTM 子表 33 列四格回填）→ RELEASE_READY `spec-refreeze`（PRD 4dd95528／Architecture c156549f／ADR-001 ff0bcd00／契約 32e60de7／P2b TCS 638def94／本鍵 TCS 29a4db6b）→ `transition --to RELEASE`。觀察帳本同 commit 追加 OBS-SI-359（CI vitest 逾時根因）、OBS-SI-360（OBS-SI-348 再開症狀由本增量處理）、OBS-SI-361（nightly 10-31 負載敏感假紅）。

### G. 真機驗證結果（V 系列；TCS §6.2）
| V | 項目 | 結果 |
|---|------|------|
| V1 | 掌舵者真機：對帳頁三份多送的稽核檔不再是待入帳 | 主控以 API 代驗（2026-10-31 22:44，Docker 全棧重建後；開發預設 admin 登入）：`reconcile.status=ok`、items 十一鍵；PROP-SI-006 四份 promote 稽核檔——`e550a510` `ingested=true`、`a2c9903f`／`ea60faf6`／`f5e78bb3` `ingested=false` 且 `supersededBy=e550a510`。畫面側由 Playwright 真機探針（Sonnet，2026-11-01 01:0x～01:1x，UI 登入 admin → `/self-improving`；兩次執行皆 rc 0）代驗：`si-superseded-toggle` 文字「另有 3 筆已被取代（同一張卡的同一決定已由其他稽核檔入帳）」、預設收合（`aria-expanded=false`）、展開後 `#si-superseded-items` 恰三列（上述三個 auditRef）且每列 `取代者：e550a510-…`、`si-dkind-*` 皆「晉升 promote」；群組外只剩 `si-writes-empty`「無待入帳」，沒有該三筆的列或入帳指令鈕；開對話框期間 `console-writes` GET 增量 0；瀏覽器端非 GET 請求只有登入一次。截圖與 `probe-results.json` 在主控 scratchpad `dedupe\probe\`。掌舵者本人目視待補 |
| V2 | 掌舵者真機：對話框對已送出待入帳的動詞停用 | 待掌舵者本人（目前真實資料沒有待入帳且未被取代的列，無法在真機觸發；AT-951-5-1 以替身釘住） |
| V3 | `schema.d.ts` 重產可重現 | 審查者重產與入庫檔位元組相同（B 節） |
| V4 | 開發 agent 交卷前閘門 | Developer 交卷：gradle 249 個測試 0 失敗、vitest 全套 0 失敗、tsc 0、lint 0；主控親驗同 |
| V5 | 範圍守衛 | `git diff --name-only` 35 檔全在 §5.7 集合（C 節） |
| V6 | 平台與雲端 CI | Windows 實跑全綠；push 後 `agentconsole-ci` 待查；macOS 未驗 |
