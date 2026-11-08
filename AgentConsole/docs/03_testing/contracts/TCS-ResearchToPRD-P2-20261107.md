# Test Contract Specification — ResearchToPRD P2（內環看板與自癒監視器、終端窗格、人機協同彈窗、SCR 前端、SCG 登錄、交付驗收與歸檔；DB V21、Bridge 登錄與交付與自癒同步、console-api 七個端點、frontend 步驟 4 其餘與步驟 5）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole 前端導覽登記表與說明登記表、console-api、Engine Bridge；上位文件含 Console PRD §0.9、Architecture、ADR-001、ADR-002、ADR-003、ADR-XPLAT-017、API 契約兩份、ResearchToPRD PRD）的單一 Feature 的 P2 期（P0、P1 已 RELEASE）；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-ResearchToPRD-P2-20261107.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因上位文件含根層 PRD 與根層 ADR）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-908 |
| **Feature 名稱** | ResearchToPRD P2：內環可視與交付——執行看板五階段（唯讀投影、SSE 與 REST 回補、Bridge 不可達快照）、自癒監視器（視圖、`healing_history.log`、遮蔽、規格漂移偵測）、即時終端窗格、人機協同彈窗類型 (b)～(d)、SCR 前端（發起鈕、表單、橫幅、停用）、SCG-4／SCG-5／RELEASE_READY 登錄、追溯表與 Release Tag 與 PR 與開啟本地專案、`ResearchBackLink`、交付時點對帳；Flyway V21；步驟 4 其餘與步驟 5 取代占位 |
| **User Story** | US-926（執行看板與自癒觀察，對應 PRD 的 US-R2P-15、16、17）、US-927（人機協同、SCG 登錄、SCR 前端與回連，對應 US-R2P-18 與 15-6、19 的 UI 半、01-5）、US-928（交付驗收與橫切增量，對應 US-R2P-20 與 21、22、23 的 P2 增量）；SD 已以 Grep 對 `AgentConsole/docs`、`docs`、`AgentConsole`（排除 node_modules）確認 F-908、US-926、US-927、US-928、AC-962、AT-962 皆未被使用，不撞號（指令與結果見自查檔 `_aux/SELF_CHECK.md`） |
| **建立日期** | 2026-11-07 |
| **輸入快照** | HEAD＝`8380142a`（含工作樹未提交變更，`git status` 見 research 相關檔修改中）；上位檔 digest 見〈增量追溯表〉（主控落檔時以 `Get-FileHash -Algorithm SHA256` 對工作樹逐檔現算；Stage-1 凍結由 CLI 重算為準） |
| **QA 負責人** | 本鍵 SCG-4 QA 棒（獨立審查者；規格作者＝SD 棒，實作者＝鍵 `agentconsole-research-to-prd-p2` 的各包開發 agent，三方不同） |
| **FSM 功能鍵** | `agentconsole-research-to-prd-p2`（一律從 monorepo 根啟動；`python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug research-to-prd-p2`） |
| **SCG Gate** | SCG-4 □ 待審 |

---
## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統的單一 Feature 的 P2 期。**凍結檔不得再改**：上位 TCS（含 TCS-P0、TCS-P1）的訂正只寫在各自〈勘誤〉表（本檔 §4.4 列出需勘誤者及座標），走 refreeze；本檔為使其可測而補定義者標「本檔類推」並列入 §7。**本檔只管 P2**：PRD 內屬 P0、P1 的 AC 已由 TCS-P0、TCS-P1 承接，不重做；P2 內明確延後或劃界者列於 §1.3 並附 WHY。**框架側（`AISDLC_SDD`）本鍵零改動**。本檔依主控裁決 D-87～D-141（`S\HELM_DECISIONS_P1.md`；與規格字面衝突時以裁決為準並標「依 D-NN」）與 Architect＋SA 棒的 P2 接口定稿（IFACE-P2、PACKAGES-P2、RISKS_DECISIONS-P2）撰寫；**D-139 的 V21 取代 IFACE-P2 §0 的『V19 已足夠』**，凡 IFACE-P2 與 D-138～D-141 衝突處，本檔逐條在 §7 標『取代』。

### FRD-lite

**背景（掌舵者 2026-11-07 指令「確認 ResearchToPRD_PRD.md 與來源規格功能都已經完成實作與 E to E 測試機制」）**：P0（外環）、P1（分流、SDD 內環鍵、TCS 草擬、拆解、SCR 後端、步驟 3 與步驟 4 前半）已落地；P2 補上內環可視與交付。PRD 全文 `docs/01_requirements/ResearchToPRD_PRD.md`（FR-R2P-15～20 於 :722-829、§8.1 P2 列於 :1082）；決策 ADR-003、ADR-XPLAT-017；契約 `API_Contract_ResearchToPRD.md` v1.0（含勘誤）；計畫書 `ResearchToPRD_Plan.md`；主控裁決 D-87～D-141。

**現況與變更（Before／After；brownfield）**

- Before：(1) Flyway 最大號 V20；`research_gate_decisions.gate` CHECK 只有七值（無 `SCG6`）、無 `details`；`research_deliveries` 無 `snapshot_sha256`；`research_scr` 無 `evidence_url`；(2) Bridge 沒有 `:gates`、`:tag`、`:pr`、`:traceability-preview`、`:healing-sync`；`gitops.py` 的白名單不含 `tag`、`pr`、`push origin <tag>`、`ls-remote`、`remote get-url`（`test_research_gitops.py:113` 釘為拒）；`reconcile.py` 的 `CHECK_IDS` 為六項；`db.py` 無 `delivery.record`；(3) console-api 沒有看板、gates、自癒、交付端點，`OpenApiIT` 為 107 條路徑與 124 個操作，`ResearchReasonsTest` 鎖 35 個 reason，`SecurityConfig.java:107-109` 已預登 `gates`、`delivery/tag`、`delivery/pr` 三條 ADMIN 規則但無對應端點；(4) frontend 步驟 4 只有拆解、TCS 與連結，步驟 5 為占位面板，沒有 `ResearchBackLink`，`endpoints.test.ts` 釘 118 個端點函式。
- After：(1) 新增 `V21__research_gate_details_delivery_snapshot.sql`（DDL 取 Architecture K.6，不得自改；D-139）：gate CHECK 加 `SCG6`、`details JSONB`、`snapshot_sha256 CHAR(64)`、`evidence_url`；(2) Bridge 新增 `app/research/{inner_gates,delivery,healing}.py` 與 `app/routers/research_deliver.py`（五個端點）、`gitops.py` 新增 P2 形態、`db.py` 新增 `P2_OPS` 與 `list_healing_attempts`、`CHECK_IDS` 第七項 `delivery`；(3) console-api 新增七個端點（`OpenApiIT` 114／131）、`HealingExcerptMasker`、`ResearchHealingNotifier`（`RunConsumers` post-commit）、兩個新 reason（37）；(4) frontend 新增看板、自癒監視器、終端窗格、決策彈窗、SCR 對話框與橫幅、SCG 登錄對話框、`DeliverPanel` 與追溯表與確認框、`ResearchBackLink`，步驟 5 取代占位（占位為零），說明登記表步驟 4 其餘與步驟 5 寫實。
- **非目標**：P0、P1 已落地者不重做（含 FR-R2P-18 類型 (a) 與 AC-R2P-18-1、18-4、18-5、18-6，及 FR-R2P-19 後端）；框架側零改動（`AISDLC_SDD`、`AutoClaude` 不改，ADR-XPLAT-016 §11 白名單不擴大）；不改 `sdd_cli.py` 動詞集合與旗標白名單、不改 `SecurityConfig`、`ExecutionController`、`ResearchFlowPolicy.java`、`LiveLogCard`、`useRunStream`；不新增 hook、守衛碼、根層 `tools/` 模組；不新增 `os.replace`、`rename`、`move` 站點；不新增前端相依；不實作 GitHub Release（Q-8）；不新增導覽列與說明頁；全站狀態燈列與研究範圍修訂端點仍延後（D-31、D-115）。

**AC 編號規則**

1. **編譯文法**：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。PRD 的 `AC-R2P-NN-Y` 含字母，故本檔沿 P0、P1 採**雙名**：機器可讀位置（§1.5、§3）一律用 `AC-962-n`；人讀處一律同時寫出 PRD 全名。
2. **對映**：本檔 AC 家族號 962（現有最大號為 961，不撞號；D-90），共 30 個 AC。AC-962-n 是**契約級**條款，比 AC-R2P 粗；PRD 內屬 P2 的 23 條 AC-R2P（FR-R2P-15、16、17、18 類型 (b)～(d) 的 18-2 與 18-3、20）加 15 條增量半條，全數映到至少一個 AC-962 與其 AT（對照全表在 §1.2）。
3. **AT 命名**：`AT-962-<AC 序>-<序>`；負控與邊界 `AT-962-<AC 序>-E-<序>`；測試名含其底線形（`AT-962-3-2`→`AT_962_3_2`；Java 方法名以底線形開頭、後接駝峰敘述；pytest 函式名為 `test_AT_962_3_2_…`；vitest 的 `it` 標題以底線形開頭）。每個 AC 內數字序與 E 序各不超過 9。
4. **計數**：AC 30 個、AT 313 個（正控 206、負控與邊界 107；〔勘誤 2026-11-08〕新增 AT-962-1b-1～1b-4 四列，見勘誤表 E-5）；另有 V 系列（§6.2，不是 AT）。RTM 子表列數＝F 1＋US 3＋AC 30＋AT 313（RTM-P2 回填後實為三百四十七列）。

**User Story**

| US | 對應 PRD | 敘述 | 涵蓋 AC |
|----|----------|------|---------|
| US-926 | US-R2P-15、16、17 | 作為 OPERATOR，我要在步驟 4 一頁看到從拆解到回歸驗收五階段各卡在哪、自癒嘗試與規格漂移、背景命令的即時輸出，並能一鍵進入既有執行中心；Bridge 不可達時我要看到有時間標示的快照而不是空畫面 | AC-962-6、AC-962-7、AC-962-8、AC-962-9、AC-962-10、AC-962-11、AC-962-12、AC-962-13 |
| US-927 | US-R2P-18（類型 b、c、d）、15-6、19 的 UI 半、01-5 | 作為掌舵者，我要在系統需要我決定時被明確告知、能登錄 SCG-4 與 SCG-5 的審查結果（含審查者獨立聲明）、能從看板發起 SCR 並看到橫幅與停用，且能從執行中心回到研發工作流 | AC-962-3、AC-962-4、AC-962-14、AC-962-15、AC-962-16 |
| US-928 | US-R2P-20、21、22、23 的 P2 增量 | 作為掌舵者，我要在交付前看見每條驗收準則是否都有通過的測試，並一鍵建立 Release Tag 與（可選）PR；作為維運，我要資料表、閘、對帳、稽核與契約鎖在 P2 一併到位且守衛不鬆動 | AC-962-1、AC-962-2、AC-962-5、AC-962-17、AC-962-18、AC-962-19、AC-962-20、AC-962-21、AC-962-22、AC-962-23、AC-962-24、AC-962-25、AC-962-26、AC-962-27、AC-962-28、AC-962-29、AC-962-30 |

**本增量交付物**（D1～D10；路徑相對 monorepo 根；每包一個 Sonnet 開發棒，派工明寫 `model: sonnet`；各包的「允許變更檔案集合」見 §5.7；依 D-141 波 0～3）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | V21 與 IT | `AgentConsole/backend/src/main/resources/db/migration/V21__research_gate_details_delivery_snapshot.sql`（DDL 取 K.6）；`ResearchSchemaMigrationIT` 與五個 Flyway IT 的版本清單；`engine-bridge/tests/research_pg_support.py` | PKG-DB-P2 | AC-962-1 |
| D2 | Bridge 登錄、交付、自癒同步 | `app/research/{inner_gates,delivery,healing}.py`、`app/routers/research_deliver.py`、`gitops.py`、`db.py`（`P2_OPS`、`list_healing_attempts`、兩個 INSERT）、`gates/reconcile.py`、`scr.py` 與 `research_scr.py`（僅 `evidence_url`）、假 gh 補模式、能力登記與 AST 鎖測試 | PKG-BR-P2 | AC-962-2、3、5、6、7（Bridge 半）、8、17（Bridge 半）、18、20（Bridge 半）、23、26 |
| D3 | console-api | 七個端點、DTO、讀配接器、服務、`HealingExcerptMasker`、`ResearchHealingNotifier`、`RunConsumers`、`ErrorReasons`、`OpenApiIT`、`RbacIT`、`ResearchReasonsTest`、迷你 Bridge | PKG-API-P2 | AC-962-4、7（Java 半）、9、10、14（pendingReviews）、15（evidenceUrl）、17、19、20、21（概覽）、22、24、26 |
| D4 | frontend 步驟 4 其餘 | 看板、自癒監視器、終端窗格、決策彈窗、SCG 登錄對話框、SCR 對話框與橫幅；全部 P2 共享單點；漂移橫幅整併 | PKG-FE-P2A | AC-962-4（GateRegisterDialog）、11、12、13、14、15、24、25 |
| D5 | frontend 步驟 5 與回連 | `DeliverPanel`、`TraceabilityTable`、`ReleaseActions`、Tag 與 PR 確認框、`ResearchBackLink` 與兩頁掛點 | PKG-FE-P2B | AC-962-16、17（UI）、21、25 |
| D6 | 型別層收口 | `schema.d.ts` 重產、生成型替換手寫型、夾具補必填欄 | PKG-FE-W3 | AC-962-27 |
| D7 | 整合 P2 | `engine-bridge/tests/test_research_int_p2.py`、`tests/e2e/research-deliver.stack.spec.ts`、Docker 與本機模式實跑、V 系列證據 | INT-P2 | AC-962-28 |
| D8 | 遮蔽夾具 | `engine-bridge/tests/fixtures/research/healing_redaction_cases.json`（BR-P2 建、API-P2 讀） | PKG-BR-P2 | AC-962-7 |
| D9 | 文件連動（主控） | Architecture K.6 與契約與 ADR-003 與 PRD 勘誤批次、RTM 回填、Implementation_Plan 進度帳一列、SCG-4 報告 | 主控 | AC-962-29、30 |
| D10 | `V21_DDL.md` 草案 | scratchpad `S\sd\p2\V21_DDL.md`（K.4 體例：DDL 全文與驗收段），主控落 Architecture K.6；DB AT 逐字取 K.6 | SD 棒→主控 | AC-962-1、30 |

**提交順序與責任**

- 依 D-141：波 0＝PKG-DB-P2；波 1＝PKG-BR-P2 ∥ PKG-FE-P2A；波 2＝PKG-API-P2（BR-P2 收卷後，因 `CHECK_IDS` 由 Bridge 原始碼抽取、遮蔽夾具由 BR-P2 先建）∥ PKG-FE-P2B（FE-P2A 收卷後）；波 3＝PKG-FE-W3（API-P2 與 P1 修復棒收卷後，重產 `schema.d.ts`）；之後整合 P2、SCG-4 QA 鏡、修復棒、RTM 回填。每支程式完成立即編譯並跑該區 AT（`AgentConsole/CLAUDE.md` 鐵律 11），不累積。
- 開發 agent **不准 commit／push**（鐵律 3）；不動 §5.7 各包集合以外的檔（鐵律 7）；根層檔與框架樹需要變動時回報主控；真帳本、真 `~/.autosdd/`、真 `AgentConsole/build/reports/fsm`、真 repo 一律唯讀（FSM 實跑只在暫存狀態目錄；真 git 只在 `$env:TEMP` 拋棄式 clone 與 `file://` bare repo；`gh` 一律假可執行檔夾具）。
- DB 型 Bridge AT 需要 `BRIDGE_TEST_DSN` 指向可建庫的 PostgreSQL；框架對拍與真 CLI 型 AT 需要 `SDD_ROOT`。**SCG-4 與 RTM 證據一律在兩者皆在場下跑到 0 skipped**；缺任一者造成的 skip 不得當作通過（§2 的 TOOL-ABSENCE 規則）。
- **FIX 包允許集合**：修復棒的允許集合＝原包集合∪該審查報告指名的檔；報告未指名的檔一律回報主控，不得自行擴張。
- **交卷前自跑根層鎖（D-141）**：`test_windowsapps_guard_bash_parity`、`test_doc_loc_baseline_freshness_r60` 的 E501 棘輪、`_TREE_FILE_FLOORS` 與名冊（P1 兩次 pre-push 被擋的教訓；AT-962-29-4）。

**〈增量行為規則〉**（W-R2P1～W-R2P26；各 AT 與 §1 以 W-R2P 編號引用。實查依據：PRD §5、§8.1；ADR-003；ADR-XPLAT-017；契約 §0～§5；Architecture K.4；IFACE-P2、PACKAGES-P2、RISKS_DECISIONS-P2；D-138～D-141；`engine-bridge/app/{sdd_cli,fsutil,mock_claude,procutil}.py`、`routers/{research,research_scr,research_route}.py`、`research/{gitops,db,scr}.py`、`research/gates/reconcile.py`；backend 的 `SecurityConfig`、`OpenApiIT`、`RbacIT`、`ResearchReasonsTest`、`V18`～`V20`；frontend 的 `lib/domain/research.ts`、`ResearchWorkspaceView`）

- **W-R2P1 Bridge 仍是研究表唯一寫入者**：console-api 對 `research_*` 零寫入（含 V21 新欄）；console-api 只寫自己的 `projects` 列、`review_requests` 決定與 `audit_log`；`delivery.record`、`gate.decision` 皆由 Bridge 寫（AC-R2P-02-10 字串掃描）。
- **W-R2P2 gitops 仍是 git 與 gh 子行程唯一出口**：P2 新增形態（tag、push origin tag、ls-remote、remote get-url、pr create、pr list）只加進 `research/gitops.py`；argv 陣列、`shell=False`、`EXEC_MODULES` 不變；仍禁 `--force`、`push --tags`、`tag -d`、`gh release create`、`gh pr merge`。
- **W-R2P3 FSM 單一寫入面與動詞表不破壞**：`RESEARCH_VERBS` 五個不變；`gate=` 一律字面常數；`:gates` 與 RELEASE 轉換住 `inner_gates.py`；`delivery.py`、`healing.py` 零 FSM 寫入（⚖P2-1）；`sdd_cli.py` 零改動。
- **W-R2P4 SCG 登錄映射（D-138、D-139）**：PR_REVIEW→`SCG4`、RTM_VERIFY→`SCG5`、RELEASE_READY FAIL→`SCG6`；PASS→`APPROVED`、FAIL→`REJECTED`；`details` JSONB 承載 `reviewer_independent`、`review_report_ref`、`ci_red`；`reason` 欄只放人填理由、不加前綴；`(RELEASE_READY, PASS)` 一律 422（由 `:tag` 走）。
- **W-R2P5 內環現態矩陣與預算**：PR_REVIEW 允許現態 IMPLEMENTATION、EXECUTION_EVALUATION、ADVERSARIAL_EVALUATION、PR_REVIEW；RTM_VERIFY 與 RELEASE_READY 限同名現態；矩陣外 409 且零寫入；預算（RETRY_LIMITS）與超限 ESCALATION 以引擎回傳 `next_state` 為準，Bridge 不自算。
- **W-R2P6 新 op 與游標**：`P2_OPS={delivery.record}`；`OPS`、`METHOD_KINDS`、`WRITE_METHODS` 不動；含游標 UPDATE 的函式同時 `append_event`；FSM 在前、DB 在後，DB 阻塞走 outbox 補寫。
- **W-R2P7 自癒資料流**：DB 真相＝`execution_steps`；視圖 `v_research_healing_attempts` 唯讀；`healing_history.log` 是衍生檔、不是輸入；attempt 讀端以視窗函式導出；歸因與補丁結果恆 null（引擎未提供）。
- **W-R2P8 遮蔽恆開且兩端對拍**：Bridge 疊用 `redact_secrets` 與 `gitops.redact`、不讀 `REDACT_SECRETS_IN_LOGS`；console-api 另寫 `HealingExcerptMasker`；兩端讀同一份 `healing_redaction_cases.json`；先遮蔽再截尾 300 字元。
- **W-R2P9 規格漂移：`:tag` 與 `:gates` 阻擋、`:healing-sync` 只記錄（D-142）**：漂移＝凍結 digest（FSM `frozen_stages[*].spec_doc_digests` 的聯集）與目標檔重算 sha256 不符。`:tag` 與 `:gates` 前置遇漂移＝**阻擋**：422 `digest_mismatch`（既有 P0 reason，不增 reason、四方鎖仍 37）加 `details.drift[{path, expected_sha256, actual_sha256}]`，零 DB 寫入、零 FSM 呼叫、零 gitops 呼叫，畫面引導發起 SCR；`:healing-sync` 是事後偵測、無可阻擋的動作，只記錄加告警（`SPEC_CHANGE_FORBIDDEN`）。Bridge 寫入端點檢查序為：權杖→資料庫→專案存在→請求本文→**凍結 digest 比對**（僅 `:gates`、`:tag`）→FSM 與業務前置→副作用（D-144 F-01）。不還原檔（還原為毀滅性動作）；補丁寫檔當下的『被拒』由框架 hooks 承擔（V-S1）。
- **W-R2P10 看板為唯讀投影**：`GET …/kanban`（API-RP-26）無副作用；資料來自既有 Console 資料；Bridge 不可達回 DB 快照並標快照時間；內環 FSM 無推播，≤500ms 只對『SSE 幀到達之後』成立。
- **W-R2P11 角色**：`gates`、`delivery/tag`、`delivery/pr` 僅 ADMIN（`SecurityConfig.java:107-109` 已預登，不改）；kanban、healing、delivery、traceability 四個 GET 為 VIEWER 以上；OPERATOR 與 VIEWER 對 ADMIN 端點同為授權鏈 403、Bridge 請求為零。
- **W-R2P12 DDL 事實（D-139）**：新增 `V21__research_gate_details_delivery_snapshot.sql`：gate CHECK 加 SCG6、details JSONB、`snapshot_sha256 CHAR(64)`、`evidence_url`；Flyway V1～V20 不改；DDL 以 Architecture K.6 為準（`V21_DDL.md` 為草案）。
- **W-R2P13 前端呈現**：外部與 LLM 文字一律純文字；VIEWER 寫入控件停用且 `title` 為『權限不足』；游標與狀態取自 API；SSE 加 REST 回補；共享單點歸 FE-P2A 一棒。
- **W-R2P14 SCR 表單與證據連結**：證據連結入 `research_scr.evidence_url`（https、至多 500），不附在 reason 末行（D-138 Q-12）；`HEALING_FAILED` 來源只顯示可複製指令。
- **W-R2P15 ResearchBackLink**：看板連結帶 `?researchId=<uuid>`；兩頁以 `useSearchParams` 讀、UUID 驗證、無參數不顯示；不存 storage、不呼叫 API；頁面殼不改。
- **W-R2P16 追溯表導出**：單元欄＝R8 `covers_ac`→覆蓋任務終態；無覆蓋任務＝NONE（標紅）；E2E 欄＝SCG5 APPROVED 才 PASS；RTM 彙總作全域閘（諮詢）；Bridge `:tag` 內重算、不信 console-api。
- **W-R2P17 Tag 序列與交易邊界（D-138 Q-4）**：驗證→冪等探測→取 commit→`tag -a`→（`push:true` 且有 origin）push→寫快照檔→單交易入庫→`transition --to RELEASE`→對帳；失敗不補償（補償皆毀滅形態）、重送冪等續跑；`fsm_state_after` 寫當時事實 `RELEASE_READY`；快照 sha256 入 `snapshot_sha256`、`rtm_report_ref` 只存路徑。
- **W-R2P18 PR 模板與失敗**：標題與內文由資料欄位確定性拼裝（不帶使用者自由文字、不超過 4000 字）；`title` 欄只作預覽；失敗只發 `research.delivery{status:FAILED}` 事件、不寫 FAILED 列；token 只進 gh 子行程環境。
- **W-R2P19 步驟 5 誠實呈現**：『開啟本地專案』只顯示與複製、不假裝可開啟；容器模式標『此為容器內路徑』；外部連結 `rel="noopener noreferrer"`；零測試不是通過。
- **W-R2P20 對帳新增 delivery**：`CHECK_IDS` 第七項；重算快照檔 sha256 對 `snapshot_sha256`；未交付為 `absent_check`；交付時點自動對帳一次；只報告不修復；數量以 `CHECK_IDS` 原始碼為準、不寫死。
- **W-R2P21 reason 與契約鎖**：新增恰兩個 reason（`tag_exists` 409、`delivery_step_failed` 502）；`RESEARCH_` 前綴；四方鎖 35→37；未登記字面不得流出（D-136）。
- **W-R2P22 導覽不動**：P2 不新增導覽列、不新增說明頁；`HELP_PAGES`、詞彙計數不變；欄位釋義過 lint。
- **W-R2P23 型別層**：`schema.d.ts` 只由 FE-W3 重產；夾具補必填欄、不放寬為選填（D-135）。
- **W-R2P24 hermetic**：AT 不連外部網路；真 git 只在 `$env:TEMP` 拋棄式 clone 與 `file://` bare repo；`gh` 一律假；FSM 只在暫存狀態目錄；DB 拋棄式；時間假時鐘；`sleep` 不超過 2 秒。
- **W-R2P25 不新增守衛與目錄項原語**：不新增 hook、守衛碼、根層 `tools/` 模組；不新增 `os.replace`、`rename`、`move` 站點；新 Python 檔 `open`／`read_text`／`write_text` 帶 `encoding="utf-8"`、時間戳帶時區。
- **W-R2P26 文件連動**：上位文件訂正只走勘誤並於 RELEASE_READY 一併 refreeze；入庫文件不得有『passed 或 skipped 字樣加四位數字』同行。

### 增量追溯表（上位凍結檔；digest＝主控落檔時以 `Get-FileHash -Algorithm SHA256` 對工作樹逐檔現算，Stage-1 凍結由 CLI 重算為準；本檔不填任何 sha256；D-89：與 P0、P1 鍵同一組十檔，取工作樹現行版本含勘誤——P2 鍵於 P1 RELEASE 之後才凍結，屆時含 K.6 與 D-140 十四處勘誤）

| 上位檔 | 路徑（相對 monorepo 根） | sha256 |
|--------|--------------------------|--------|
| Console PRD（§0.9 研究指標、§8.1 導覽註） | `docs/01_requirements/Agent_ConsoleUI_PRD.md` | `87dd6c9ba917ed0296eb923e7e6122cb4d5f6afb9c5bc06ab39143a0a9924660` |
| Architecture（K.4／K.6 DDL、§5.4、§10、§11.1） | `AgentConsole/docs/02_architecture/Architecture.md` | `99b635437e142c3267a1544c3dcff392a9e50cce379116c8893e14d427b6b5ce` |
| ADR-001（技術棧鎖定） | `AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md` | `ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38` |
| ADR-002（前端設計系統） | `AgentConsole/docs/02_architecture/ADR-002-Frontend-Design-System.md` | `b0897c536bdbce19efc21bf0762240f22e054fc4ff03882276fa0ed59da6066d` |
| API 契約 P3-6（附錄 B reason 表；`reasons.test.ts` 的雙向鎖對象） | `AgentConsole/docs/02_architecture/API_Contract_P3-6.md` | `0ada38cf4fe438c4fd572a89cc3af089711361339c62e01653ef2438cefe2300` |
| OpenAPI 快照 P3-6 | `AgentConsole/docs/02_architecture/openapi-p3-6.yaml` | `956539977c70fe6527c7d41162cc49a6d6138c5a49d35d7a43c4852a6bf87823` |
| ResearchToPRD PRD（含勘誤） | `docs/01_requirements/ResearchToPRD_PRD.md` | `4e844433f3031e1041706c6a6cf41f8e306ca9cf9848d865a5e65c577a655bbc` |
| ADR-003（載體、持久化、流程脊、D8、D14～D16） | `AgentConsole/docs/02_architecture/ADR-003-ResearchToPRD.md` | `8507064f6b78abffac57e2a7d5ca516853744499a97308555d927749c61e1e0f` |
| ADR-XPLAT-017（Bridge 研究寫入面；D2、D5、附錄 A） | `docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md` | `b3cc74fd889514a2f8b88b4b17bbb3d8d7decf93fc831dbe500d7dade269c523` |
| API 契約 ResearchToPRD v1.0（含勘誤） | `AgentConsole/docs/02_architecture/API_Contract_ResearchToPRD.md` | `55aa8709953945afd0f950d248440ce7680c2ff15cb9ff937ea4d0f0c25484ac` |

---
## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC；邊界、錯誤與負控 AT 以 `AT-962-<n>-E-<m>` 命名並列於本節。測試類型為 Unit／Integration／Contract／E2E／Gate。各 AT 的判定指令與測試檔見 §3 各 AT 末行。本鍵 Java 與 TS 的 AT 走徑②（SDD session-only）、**不入 evaluator**；Bridge 的 AT 可走徑①或徑②（見 §2）。
### 1.1 AC-962-n 的 Given／When／Then（契約級）
- **AC-962-1** 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url
  - 主責包與規則：PKG-DB-P2；W-R2P1、W-R2P12
  - 對應 PRD：AC-R2P-02-7、AC-R2P-02-8、AC-R2P-19-1
  - Given 套用 V1～V21 的 PostgreSQL 18 When 對三張表的新欄與新 CHECK 做合法與越界寫入、對既有資料升級 Then CHECK 依 Architecture K.6 逐條拒絕，既有列不變，守衛與版本清單不退步。
- **AC-962-2** gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list
  - 主責包與規則：PKG-BR-P2；W-R2P2、W-R2P3
  - 對應 PRD：AC-R2P-20-3、AC-R2P-20-4
  - Given gitops 允許表 When 餵入新增與仍禁的 git／gh 形態 Then 新增形態通過並回 argv 陣列，仍禁形態（強推、刪除、release、merge）在 spawn 前拒絕，環境與 token 隔離不變。
- **AC-962-3** Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫
  - 主責包與規則：PKG-BR-P2；W-R2P4、W-R2P5
  - 對應 PRD：AC-R2P-02-5、AC-R2P-15-6、AC-R2P-16-5
  - Given 內環鍵現態與 SUCCEEDED 分流 When 登錄 gate 結果 Then 依現態矩陣執行 transition 與 gate、以回傳 next_state 為準、決定列依映射入庫（SCG4／SCG5／SCG6，details 承載獨立性），現態不合 409 且零寫入。
- **AC-962-4** console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核
  - 主責包與規則：PKG-API-P2、PKG-FE-P2A；W-R2P4、W-R2P9、W-R2P11
  - 對應 PRD：AC-R2P-15-6、AC-R2P-16-5
  - Given 已綁 console 專案的研究專案 When ADMIN 登錄 SCG 結果 Then 前置（任務、RTM、SCR）先於 Bridge 檢查，漂移由 Bridge 判定、console-api 只透傳 422，PR_REVIEW 必須聲明審查者獨立，OPERATOR 與 VIEWER 回 403，Bridge 請求為零；登錄對話框（GateRegisterDialog）未勾聲明不可送、FAIL 必填理由、RELEASE_READY 只有 FAIL、非 ADMIN 停用、錯誤文案取登記處。
- **AC-962-5** 鎖：AST、能力登記、動詞表與 P2_OPS
  - 主責包與規則：PKG-BR-P2；W-R2P3、W-R2P6
  - 對應 PRD：AC-R2P-15-6、AC-R2P-20-3
  - Given 新增四個 Bridge 模組與一個 db op When 跑整樹 AST 與能力登記鎖 Then gate 呼叫皆字面常數、新模組不自起子行程與不直接寫 FSM（RELEASE 轉換住 inner_gates）、動詞表與 OPS 一一對應不變。
- **AC-962-6** 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限
  - 主責包與規則：PKG-BR-P2；W-R2P7
  - 對應 PRD：AC-R2P-16-1、AC-R2P-16-4
  - Given execution_steps 的 RETRYING 與 FAILED 列 When Bridge 同步 Then healing_history.log 追加對應行（逐筆一致、冪等、遮蔽後尾 300 字元、超上限寫一次 truncated），Bridge 只新增唯讀 DB 方法。
- **AC-962-7** 自癒遮蔽：Bridge 與 console-api 兩端共用夾具對拍
  - 主責包與規則：PKG-BR-P2、PKG-API-P2；W-R2P8
  - 對應 PRD：AC-R2P-16-4
  - Given 含假機密的失敗日誌 When 入 log 與 API 回應 Then 兩端皆已遮蔽、先遮蔽後截尾、不誤殺非機密字串，兩端測試讀同一份 JSON 夾具。
- **AC-962-8** SPEC_CHANGE_FORBIDDEN：凍結規格漂移的偵測、標記與告警（不還原）
  - 主責包與規則：PKG-BR-P2、PKG-API-P2；W-R2P9
  - 對應 PRD：AC-R2P-16-5
  - Given 補丁改動已凍結規格檔 When 同步、登錄 SCG 或建 Tag Then `:healing-sync` 記錄加告警；`:gates` 與 `:tag` 前置 422 `digest_mismatch`（零寫入、零 FSM 呼叫、`details.drift[]`）；sha 不被 Bridge 改動、API 標 specChangeForbidden；『被拒』屬框架 hooks（V-S1）。
- **AC-962-9** console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知
  - 主責包與規則：PKG-API-P2；W-R2P7、W-R2P10
  - 對應 PRD：AC-R2P-16-1、AC-R2P-16-2、AC-R2P-16-3
  - Given 研究專案的執行步驟 When 讀自癒端點與處理 run 事件 Then 數值與 DB 逐值相等、歸因與補丁結果為 null、通知只在相關事件的提交之後 best-effort 發出。
- **AC-962-10** 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制
  - 主責包與規則：PKG-API-P2；W-R2P10
  - 對應 PRD：AC-R2P-15-1、AC-R2P-15-2、AC-R2P-15-4、AC-R2P-15-6、AC-R2P-18-3
  - Given 已綁 console 專案的研究專案 When 讀看板 Then 每欄計數與狀態逐值等於來源端點，Bridge 不可達時回 DB 快照加快照時間且 FSM 欄為未知，路由清單不含執行控制動詞。
- **AC-962-11** 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結
  - 主責包與規則：PKG-FE-P2A；W-R2P13
  - 對應 PRD：AC-R2P-01-5、AC-R2P-15-1、AC-R2P-15-2、AC-R2P-15-3、AC-R2P-15-4、AC-R2P-15-5
  - Given kanban 資料與 SSE 幀 When 渲染與更新 Then 欄序與數值正確、幀到達至 DOM 不超過 500ms、斷線回補、Bridge 不可達顯示快照橫幅而不是空看板。
- **AC-962-12** 自癒監視器前端：嘗試次數對上限、純文字、耗盡升級、規格漂移引導 SCR
  - 主責包與規則：PKG-FE-P2A；W-R2P13
  - 對應 PRD：AC-R2P-16-1、AC-R2P-16-2、AC-R2P-16-3、AC-R2P-16-5、AC-R2P-19-1
  - Given healing 資料 When 渲染 Then 顯示嘗試次數對上限與摘錄（純文字）、歸因與補丁結果缺值標引擎未提供、耗盡連到決策彈窗、漂移列引導發起 SCR。
- **AC-962-13** 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流
  - 主責包與規則：PKG-FE-P2A；W-R2P13
  - 對應 PRD：AC-R2P-17-1、AC-R2P-17-2、AC-R2P-17-3、AC-R2P-17-4
  - Given 執行中或已結束的 run When 展開窗格 Then 以既有 useRunStream 與 LiveLogCard 顯示（無第二份實作）、純文字、結束後以 steps 回補，開合僅存瀏覽器。
- **AC-962-14** 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點
  - 主責包與規則：PKG-FE-P2A、PKG-API-P2；W-R2P13
  - 對應 PRD：AC-R2P-18-2、AC-R2P-18-3
  - Given 待審項（自癒耗盡、Agent 請求、重大選擇） When 彈窗 Then 同一殼、按鈕由 allowedDecisions 驅動、重複幀只開一個、稍後處理只關窗，決定走既有 review 端點並入庫。
- **AC-962-15** SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫
  - 主責包與規則：PKG-FE-P2A、PKG-API-P2、PKG-BR-P2；W-R2P14
  - 對應 PRD：AC-R2P-19-1、AC-R2P-19-4、AC-R2P-19-5、AC-R2P-19-6、AC-R2P-19-7
  - Given 內環進行中 When OPERATOR 以上發起 SCR Then 表單驗證與錯誤回顯正確、證據連結（https）入 evidence_url、SCR_OPEN 時橫幅出現且所有啟動類動作停用。
- **AC-962-16** ResearchBackLink：深連結 ?researchId=、兩頁掛點、反向釘改寫
  - 主責包與規則：PKG-FE-P2B；W-R2P15
  - 對應 PRD：AC-R2P-01-5、AC-R2P-15-5
  - Given 自看板進入執行中心或監控中心 When 頁面載入 Then 有合法 researchId 時顯示回到研發工作流，無或非 UUID 一律不顯示，零後端零儲存。
- **AC-962-17** 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現
  - 主責包與規則：PKG-BR-P2、PKG-API-P2、PKG-FE-P2B；W-R2P16
  - 對應 PRD：AC-R2P-20-1、AC-R2P-20-2、AC-R2P-20-3
  - Given 凍結 PRD 與拆解與任務終態 When 產生追溯表 Then 一個 AC 一列（集合相等）、單元欄由 covers_ac 加任務終態導出、零測試標紅、預演零副作用、Tag 前置於 Bridge 內重算。
- **AC-962-18** Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑
  - 主責包與規則：PKG-BR-P2；W-R2P17
  - 對應 PRD：AC-R2P-02-5、AC-R2P-16-5、AC-R2P-20-2、AC-R2P-20-3
  - Given FSM 現態 RELEASE_READY 且追溯全 PASS When 建立 Release Tag Then 依序驗證、本地 tag、（確認後）push、快照檔、單交易入庫、transition RELEASE、對帳；失敗不補償且可重送續跑。
- **AC-962-19** console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核
  - 主責包與規則：PKG-API-P2；W-R2P17、W-R2P11
  - 對應 PRD：AC-R2P-02-5、AC-R2P-16-5、AC-R2P-20-2、AC-R2P-20-3
  - Given ADMIN 與前置成立 When POST delivery/tag Then 先驗 FSM、RTM 閘與 SCR 再轉送 Bridge，tagName 與 message 邊界精準，Bridge 錯誤 reason 原樣透傳，OPERATOR 與 VIEWER 403。
- **AC-962-20** PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償
  - 主責包與規則：PKG-BR-P2、PKG-API-P2；W-R2P18
  - 對應 PRD：AC-R2P-20-4
  - Given ADMIN 且 gh 可用 When 建立 PR Then 先 push -u 再 gh pr create（argv 陣列）、標題內文由資料欄位拼裝、已有 PR 冪等回既有、缺項 422、token 只進 gh 環境。
- **AC-962-21** 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案
  - 主責包與規則：PKG-FE-P2B、PKG-API-P2；W-R2P19
  - 對應 PRD：AC-R2P-20-1、AC-R2P-20-2、AC-R2P-20-3、AC-R2P-20-4、AC-R2P-20-5、AC-R2P-21-5
  - Given 交付資料 When 渲染步驟 5 Then 取代占位、Tag 鈕依未覆蓋與 FSM 與 SCR 與角色停用、PR 與本地專案如實呈現（不假裝可開啟）、外部連結帶 noopener noreferrer。
- **AC-962-22** 交付稽核與完整率：records/audit、audit_log 與事件 trace_id、append-only
  - 主責包與規則：PKG-API-P2；W-R2P12
  - 對應 PRD：AC-R2P-02-4、AC-R2P-02-5、AC-R2P-20-3、AC-R2P-20-6
  - Given 交付與 gates 動作 When 查稽核 Then 已交付專案 missing 為空、audit_log 與事件同 trace_id、交付列不可變且 (research_id, kind, ref) 唯一。
- **AC-962-23** 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳
  - 主責包與規則：PKG-BR-P2、PKG-API-P2、PKG-FE-P2A；W-R2P20
  - 對應 PRD：AC-R2P-16-1、AC-R2P-23-1、AC-R2P-23-4
  - Given 已建立 Release Tag 的專案 When 對帳 Then delivery 項重算快照檔 sha256 對 snapshot_sha256（不符為 drift）、未交付不算漂移、:tag 成功後自動對帳一次、只報告不修復。
- **AC-962-24** 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125
  - 主責包與規則：PKG-API-P2、PKG-FE-P2A；W-R2P21
  - 對應 PRD：AC-R2P-15-1、AC-R2P-15-6、AC-R2P-20-3、AC-R2P-20-4
  - Given 七個新端點與兩個新 reason When 跑共享單點測試 Then 四方 reason 集合相等、OpenAPI 計數與狀態碼表逐項登記、gates／tag／pr 僅 ADMIN、前端端點函式與 operationId 一一對應。
- **AC-962-25** 說明登記表、五步接線與兩處漂移橫幅整併、導覽不動
  - 主責包與規則：PKG-FE-P2A、PKG-FE-P2B；W-R2P22
  - 對應 PRD：AC-R2P-21-2、AC-R2P-21-5、AC-R2P-23-4
  - Given 步驟 4 其餘與步驟 5 交付 When 跑說明三道鎖與導覽鎖 Then 欄位釋義過 lint、頁數與詞彙計數不變、單一漂移橫幅、四區塊零差異。
- **AC-962-26** 寫入擁有權與 db op：Bridge 唯一寫入者、delivery.record、outbox、檢查序
  - 主責包與規則：PKG-BR-P2、PKG-API-P2；W-R2P1、W-R2P6
  - 對應 PRD：AC-R2P-02-10、AC-R2P-02-5、AC-R2P-20-3、AC-R2P-20-4
  - Given 新增端點與 op When 檢查寫入面 Then console-api 對 research_* 零寫入、delivery.record 同交易寫列與事件、DB 阻塞走 outbox、五個 Bridge 端點檢查序一致。
- **AC-962-27** FE-W3 型別層：schema.d.ts 重產、生成型替換手寫型、夾具補必填欄
  - 主責包與規則：PKG-FE-W3；W-R2P23
  - 對應 PRD：AC-R2P-21-2
  - Given backend OpenAPI 含七條新路徑 When 重產 schema.d.ts Then 手寫型改引生成型、夾具補必填欄而不放寬為選填、tsc 與 lint 與 build 皆過。
- **AC-962-28** 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理
  - 主責包與規則：INT-P2；W-R2P24
  - 對應 PRD：AC-R2P-15-1、AC-R2P-15-6、AC-R2P-16-1、AC-R2P-16-3、AC-R2P-16-5、AC-R2P-17-1、AC-R2P-18-2、AC-R2P-19-1、AC-R2P-19-4、AC-R2P-20-1、AC-R2P-20-3、AC-R2P-20-4、AC-R2P-23-4
  - Given 暫存專案與 file:// bare origin 與假 gh 與 Docker 全棧 When 跑整合 Then PRD §8.1 P2 出口 (a)～(g) 取得逐字證據，容器模式的 :tag 回 422 且零變化，並清掃殘留。
- **AC-962-29** 邊界、跨平台與衛生閘：允許集合、禁區、無新守衛、無新目錄項原語
  - 主責包與規則：主控與各包；W-R2P25
  - 對應 PRD：AC-R2P-02-10
  - Given 開工基準與 HEAD When 核對差異 Then 變更檔皆屬包集合、禁區零差異、目錄項原語站點淨增 0、根層鎖與 ruff 皆過。
- **AC-962-30** 文件連動與 V 系列：K.6、十四處勘誤、RTM 回填、出口逐項
  - 主責包與規則：主控；W-R2P26
  - 對應 PRD：AC-R2P-02-4、AC-R2P-20-3
  - Given RELEASE_READY When 落檔勘誤與回填 Then V21 與 K.6 逐字一致、勘誤批次寫入並 refreeze、RTM 列數與宣告一致、V 系列與出口 (a)～(i) 逐項有證據。

### 1.2 PRD 屬 P2 的 AC-R2P → AC-962-n → AT 全表（23 條核心加 15 條增量，共 38 條，逐條不漏）

| AC-R2P | AC-962 | AT | 備註 |
|--------|--------|----|------|
| AC-R2P-15-1 | AC-962-10、AC-962-11、AC-962-24、AC-962-28 | AT-962-10-1、AT-962-10-2、AT-962-10-3、AT-962-10-4、AT-962-10-5、AT-962-10-6、AT-962-10-9、AT-962-10-E-4、AT-962-10-E-5、AT-962-11-1、AT-962-11-2、AT-962-11-E-1、AT-962-11-E-4、AT-962-24-2、AT-962-24-5、AT-962-28-7 | — |
| AC-R2P-15-2 | AC-962-10、AC-962-11 | AT-962-10-E-1、AT-962-10-E-2、AT-962-10-E-3、AT-962-11-8 | — |
| AC-R2P-15-3 | AC-962-11 | AT-962-11-3、AT-962-11-4、AT-962-11-5、AT-962-11-9、AT-962-11-E-3 | ≤500ms 定義＝SSE 幀到達瀏覽器至 DOM commit；不含 FSM 檔改變到幀發出之間（Q-9；V-D5 量測） |
| AC-R2P-15-4 | AC-962-10、AC-962-11 | AT-962-10-8、AT-962-11-7、AT-962-11-9、AT-962-11-E-2 | Bridge 不可達：FSM 衍生欄 null 加未知徽章，不猜 |
| AC-R2P-15-5 | AC-962-11、AC-962-16 | AT-962-11-6、AT-962-16-2、AT-962-16-3、AT-962-16-4 | — |
| AC-R2P-15-6 | AC-962-3、AC-962-4、AC-962-5、AC-962-10、AC-962-24、AC-962-28 | AT-962-3-1、AT-962-3-2、AT-962-3-3、AT-962-3-4、AT-962-3-5、AT-962-3-6、AT-962-3-7、AT-962-3-8、AT-962-3-9、AT-962-3-E-1、AT-962-3-E-2、AT-962-3-E-3、AT-962-3-E-4、AT-962-3-E-5、AT-962-3-E-6、AT-962-4-1、AT-962-4-2、AT-962-4-3、AT-962-4-4、AT-962-4-5、AT-962-4-6、AT-962-4-7、AT-962-4-8、AT-962-4-E-1、AT-962-4-E-2、AT-962-4-E-3、AT-962-4-E-4、AT-962-4-E-5、AT-962-4-E-6、AT-962-4-E-7、AT-962-4-E-8、AT-962-4-E-9、AT-962-5-1、AT-962-5-2、AT-962-5-6、AT-962-5-E-1、AT-962-5-E-2、AT-962-10-7、AT-962-24-4、AT-962-28-1 | RELEASE_READY FAIL 入 `gate=SCG6`（D-139）；獨立性聲明入 `details`（D-138） |
| AC-R2P-16-1 | AC-962-6、AC-962-9、AC-962-12、AC-962-23、AC-962-28 | AT-962-6-1、AT-962-6-2、AT-962-6-3、AT-962-6-4、AT-962-6-5、AT-962-6-6、AT-962-6-7、AT-962-6-8、AT-962-6-E-1、AT-962-6-E-2、AT-962-6-E-3、AT-962-9-1、AT-962-9-5、AT-962-9-6、AT-962-9-E-1、AT-962-9-E-2、AT-962-12-5、AT-962-23-5、AT-962-28-3 | attempt 讀端導出；視圖欄位不含歸因與補丁結果（D-140 #5） |
| AC-R2P-16-2 | AC-962-9、AC-962-12 | AT-962-9-1、AT-962-9-2、AT-962-9-3、AT-962-9-4、AT-962-9-7、AT-962-9-E-3、AT-962-12-1、AT-962-12-2、AT-962-12-E-1、AT-962-12-E-3 | — |
| AC-R2P-16-3 | AC-962-9、AC-962-12、AC-962-28 | AT-962-9-3、AT-962-12-3、AT-962-28-3、AT-962-28-4 | — |
| AC-R2P-16-4 | AC-962-6、AC-962-7 | AT-962-6-4、AT-962-7-1、AT-962-7-2、AT-962-7-3、AT-962-7-4、AT-962-7-5、AT-962-7-E-1、AT-962-7-E-2、AT-962-7-E-3 | — |
| AC-R2P-16-5 | AC-962-3、AC-962-4、AC-962-8、AC-962-12、AC-962-18、AC-962-19、AC-962-28 | AT-962-3-E-6、AT-962-4-E-5、AT-962-8-1、AT-962-8-2、AT-962-8-3、AT-962-8-4、AT-962-8-5、AT-962-8-E-1、AT-962-8-E-2、AT-962-8-E-3、AT-962-12-4、AT-962-12-E-2、AT-962-18-E-5、AT-962-19-E-5、AT-962-28-E-1 | AC 拆兩半：Bridge 偵測、標記、告警（AT）；框架 hook『被拒』（V-S1，D-140 #8） |
| AC-R2P-17-1 | AC-962-13、AC-962-28 | AT-962-13-1、AT-962-13-5、AT-962-13-6、AT-962-13-7、AT-962-13-E-2、AT-962-28-7 | — |
| AC-R2P-17-2 | AC-962-13 | AT-962-13-2、AT-962-13-E-1 | PRD 路徑 `lib/sse/` 實為 `lib/api/sse.ts` 與 `hooks/useRunStream.ts`（D-140 #3） |
| AC-R2P-17-3 | AC-962-13 | AT-962-13-3、AT-962-13-E-3 | — |
| AC-R2P-17-4 | AC-962-13 | AT-962-13-4 | — |
| AC-R2P-18-2 | AC-962-14、AC-962-28 | AT-962-14-1、AT-962-14-2、AT-962-14-3、AT-962-14-4、AT-962-14-7、AT-962-14-8、AT-962-14-E-1、AT-962-14-E-2、AT-962-14-E-3、AT-962-14-E-4、AT-962-28-4 | — |
| AC-R2P-18-3 | AC-962-10、AC-962-14 | AT-962-10-6、AT-962-14-5、AT-962-14-6 | 待辦取 `kanban.pendingReviews`，不用 `GET /signoffs/pending`（D-140 #4） |
| AC-R2P-20-1 | AC-962-17、AC-962-21、AC-962-28 | AT-962-17-1、AT-962-17-2、AT-962-17-3、AT-962-17-4、AT-962-17-6、AT-962-17-7、AT-962-17-8、AT-962-17-E-1、AT-962-17-E-3、AT-962-21-1、AT-962-21-2、AT-962-21-8、AT-962-21-E-2、AT-962-28-7 | 單元欄＝R8 `covers_ac` 加任務終態；E2E 欄＝SCG5 APPROVED 才 PASS（D-140 #7） |
| AC-R2P-20-2 | AC-962-17、AC-962-18、AC-962-19、AC-962-21 | AT-962-17-3、AT-962-17-5、AT-962-17-7、AT-962-17-8、AT-962-17-E-2、AT-962-18-E-2、AT-962-19-2、AT-962-21-3、AT-962-21-8、AT-962-21-E-1 | — |
| AC-R2P-20-3 | AC-962-2、AC-962-5、AC-962-17、AC-962-18、AC-962-19、AC-962-21、AC-962-22、AC-962-24、AC-962-26、AC-962-28、AC-962-30 | AT-962-2-1、AT-962-2-3、AT-962-2-4、AT-962-2-5、AT-962-2-6、AT-962-2-E-1、AT-962-2-E-2、AT-962-2-E-3、AT-962-5-3、AT-962-5-4、AT-962-5-5、AT-962-5-7、AT-962-17-E-4、AT-962-18-1、AT-962-18-2、AT-962-18-3、AT-962-18-4、AT-962-18-5、AT-962-18-6、AT-962-18-7、AT-962-18-8、AT-962-18-9、AT-962-18-E-1、AT-962-18-E-2、AT-962-18-E-3、AT-962-18-E-4、AT-962-18-E-5、AT-962-18-E-6、AT-962-19-1、AT-962-19-2、AT-962-19-3、AT-962-19-4、AT-962-19-5、AT-962-19-E-1、AT-962-19-E-2、AT-962-19-E-3、AT-962-19-E-4、AT-962-19-E-5、AT-962-19-E-6、AT-962-21-4、AT-962-21-E-4、AT-962-22-5、AT-962-24-1、AT-962-24-2、AT-962-24-3、AT-962-24-4、AT-962-24-6、AT-962-24-E-1、AT-962-24-E-2、AT-962-24-E-3、AT-962-26-2、AT-962-26-3、AT-962-26-E-1、AT-962-28-1、AT-962-28-8、AT-962-28-E-2、AT-962-28-E-3、AT-962-30-1、AT-962-30-2、AT-962-30-5 | R11 快照 sha 入 `snapshot_sha256`（D-139）；`push` 欄由確認框勾選（D-140 #1） |
| AC-R2P-20-4 | AC-962-2、AC-962-20、AC-962-21、AC-962-24、AC-962-26、AC-962-28 | AT-962-2-2、AT-962-2-6、AT-962-2-E-1、AT-962-20-1、AT-962-20-2、AT-962-20-3、AT-962-20-4、AT-962-20-5、AT-962-20-6、AT-962-20-7、AT-962-20-8、AT-962-20-E-1、AT-962-20-E-2、AT-962-20-E-3、AT-962-20-E-4、AT-962-21-5、AT-962-21-7、AT-962-21-E-3、AT-962-24-4、AT-962-26-5、AT-962-28-2 | — |
| AC-R2P-20-5 | AC-962-21 | AT-962-21-6、AT-962-21-7 | — |
| AC-R2P-20-6 | AC-962-22 | AT-962-22-1 | — |
| AC-R2P-01-5 | AC-962-11、AC-962-16 | AT-962-11-6、AT-962-16-1、AT-962-16-2、AT-962-16-3、AT-962-16-5、AT-962-16-E-1、AT-962-16-E-2、AT-962-16-E-3 | P2 半條：連結與 `ResearchBackLink`（TCS-P0 ⚖2；P1 已有連結半） |
| AC-R2P-02-4 | AC-962-22、AC-962-30 | AT-962-22-1、AT-962-22-2、AT-962-22-E-3、AT-962-30-3、AT-962-30-4、AT-962-30-E-1、AT-962-30-E-2 | P2 半條：已交付專案 `records/audit.missing` 為空 |
| AC-R2P-02-5 | AC-962-3、AC-962-18、AC-962-19、AC-962-22、AC-962-26 | AT-962-3-6、AT-962-18-3、AT-962-19-6、AT-962-22-3、AT-962-22-4、AT-962-22-5、AT-962-22-E-1、AT-962-22-E-2、AT-962-26-5 | P2 半條：Release Tag、PR、gates 的稽核列與事件 trace_id |
| AC-R2P-02-7 | AC-962-1 | AT-962-1-1、AT-962-1-2、AT-962-1-3、AT-962-1-4、AT-962-1-5、AT-962-1-6、AT-962-1-7、AT-962-1-8、AT-962-1-E-1、AT-962-1-E-3、AT-962-1b-1、AT-962-1b-2、AT-962-1b-3、AT-962-1b-4 | P2 增量：V21 的 CHECK、守衛與版本清單不退步（受控與 append-only 不變） |
| AC-R2P-02-8 | AC-962-1 | AT-962-1-1、AT-962-1-E-2 | P2 增量：V21 新欄型別與既有時間欄皆帶時區 |
| AC-R2P-02-10 | AC-962-26、AC-962-29 | AT-962-26-1、AT-962-26-2、AT-962-26-4、AT-962-26-E-2、AT-962-29-1、AT-962-29-2、AT-962-29-3、AT-962-29-4、AT-962-29-5、AT-962-29-E-1、AT-962-29-E-2、AT-962-29-E-3 | P2 增量：console-api 對 `research_*` 零寫入（新增七個端點與新類） |
| AC-R2P-19-1 | AC-962-1、AC-962-12、AC-962-15、AC-962-28 | AT-962-1-5、AT-962-12-4、AT-962-15-1、AT-962-15-2、AT-962-15-3、AT-962-15-5、AT-962-15-6、AT-962-15-7、AT-962-15-8、AT-962-15-E-2、AT-962-28-5 | FR-R2P-19 UI 半：發起鈕、表單；後端 P1 已落地 |
| AC-R2P-19-4 | AC-962-15、AC-962-28 | AT-962-15-3、AT-962-15-5、AT-962-28-5 | FR-R2P-19 UI 半：橫幅與 MAJOR 導向後繼專案 |
| AC-R2P-19-5 | AC-962-15 | AT-962-15-2、AT-962-15-4、AT-962-15-6、AT-962-15-7、AT-962-15-E-1、AT-962-15-E-3、AT-962-15-E-4 | FR-R2P-19 UI 半：欄位驗證回顯；另含 evidence_url（D-139） |
| AC-R2P-19-6 | AC-962-15 | AT-962-15-4 | FR-R2P-19 UI 半：scr_limit 文案提示改 MAJOR |
| AC-R2P-19-7 | AC-962-15 | AT-962-15-3 | FR-R2P-19 UI 半：HEALING_FAILED 來源只顯示可複製指令、不顯示已發起（後端 P1 已落地） |
| AC-R2P-21-2 | AC-962-25、AC-962-27 | AT-962-25-1、AT-962-25-5、AT-962-25-E-1、AT-962-25-E-2、AT-962-27-1、AT-962-27-2、AT-962-27-3、AT-962-27-E-1、AT-962-27-E-2 | FR-R2P-21 增量：步驟 4 其餘與步驟 5 的說明登記表欄位釋義 |
| AC-R2P-21-5 | AC-962-21、AC-962-25 | AT-962-21-1、AT-962-25-2、AT-962-25-4 | FR-R2P-21 增量（P2 版）：五步皆真面板，占位為零 |
| AC-R2P-23-1 | AC-962-23 | AT-962-23-1、AT-962-23-6、AT-962-23-E-1 | FR-R2P-23 增量：checks[] 加第七項 `delivery` |
| AC-R2P-23-4 | AC-962-23、AC-962-25、AC-962-28 | AT-962-23-2、AT-962-23-3、AT-962-23-4、AT-962-23-7、AT-962-23-E-2、AT-962-25-3、AT-962-28-6 | FR-R2P-23 增量：交付時點自動對帳 |

### 1.3 本檔範圍外與劃界（P0、P1 已落地者不重做；P2 內明確延後或不聲稱者逐項附 WHY）

> PRD 其餘 AC-R2P（P0 的 111 條與 P1 的 47 條）已由 TCS-P0、TCS-P1 承接，本檔不重做，P2 RELEASE 時不重算。P2 範圍內下列四項**不由本檔聲稱已覆蓋**：

| 項 | 處置 | WHY |
|----|------|-----|
| AC-R2P-16-5 的『該嘗試被拒』半 | 不在 AT；V-S1 | 補丁由 Claude Code 在目標 repo 寫檔，Bridge 無事前攔截面；防止面是框架 hooks（禁令 3），本鍵不得改框架樹（D-140 #8） |
| 內環 FSM 檔改變到看板更新的端到端上界 | 不在 AT；V-D5 量測 | 內環 FSM 由引擎檔推進、Bridge 無推播；AC-R2P-15-3 的 ≤500ms 只對『SSE 幀到達之後』成立（Q-9） |
| 逐 AC 的 E2E 機器來源 | 追溯表 E2E 欄如實標 `NOT_RUN`，僅 SCG5 APPROVED 後才 `PASS` | 現有 RTM 只有彙總、逐 AC 列被 Bridge 丟棄且編號不同（D-90、D-140 #7） |
| 真 GitHub 的 Tag 推送與 PR | 不在 AT；V-H6 | 對外副作用與 token，必須真人決定（沿 D-92）；代驗面以 `file://` bare origin 與假 gh 涵蓋 |

### 1.4 機械鎖與出口判準的對照

**PRD §9.4 機械鎖與 ADR-XPLAT-017 §5 測試鎖（P2 部分）→ AT**（每項至少一個 AT；本表由自查腳本逐一核對 AT 存在）

| 鎖 | 來源 | 對應 AT |
|----|------|---------|
| ① ArchUnit 字串掃描：console-api 對 `research_*` 零寫入 | PRD §9.4 ① | AT-962-26-1、26-4 |
| ② Bridge AST：FSM 單一寫入面、`gate` 字面常數、新模組不自起子行程、`inner_gates` 專屬規則 | PRD §9.4 ②；ADR-XPLAT-017 §5 | AT-962-5-1、5-2、5-3、5-4、5-E-1 |
| ④ 能力登記：git 與 gh 子行程只住 `gitops.py`；新模組先登記 | PRD §9.4 ④ | AT-962-5-5、2-E-3 |
| ⑤ token 脫敏夾具（含假 token） | PRD §9.4 ⑤ | AT-962-2-6、20-6、20-E-4、7-4 |
| ⑦ Schema IT 的 CHECK、觸發器與版本清單（V21） | PRD §9.4 ⑦ | AT-962-1-1～1-8、1-E-1、1-E-2、1-E-3 |
| 動詞表不變與 `sdd_cli.py` 零 diff | ADR-XPLAT-017 §5 | AT-962-5-6、29-2 |
| 暫存狀態目錄實跑：`:gates` 現態矩陣與 `:tag` 的 RELEASE 序列的 `decision_trace` | ADR-XPLAT-017 附錄 A | AT-962-3-1、3-2、3-3、3-4、3-5、18-5、28-1 |
| reason 四方鎖 37 與 OpenAPI 計數與 RBAC | D-136；PRD §9.4 | AT-962-24-1、24-2、24-3、24-4、24-E-1、24-E-2 |
| 遮蔽兩端對拍（共用 JSON 夾具） | IFACE-P2 §3.3 | AT-962-7-1、7-3、7-E-3 |
| 終端窗格靜態判準（無 WebSocket、無第二份串流） | PRD AC-R2P-17-2 | AT-962-13-2、13-E-1 |
| 路由清單比對：看板不新增執行控制端點 | PRD AC-R2P-15-2 | AT-962-10-E-1、11-8 |
| 既有重用元件零改動（LiveLogCard、useRunStream、LogPanel） | PRD AC-R2P-17-3 | AT-962-13-E-3 |

**P0、P1 殘留分流（RISKS (c)）**

| 項 | 分流 | 本檔承接 |
|----|------|----------|
| D-131(6) 兩處漂移橫幅並存 | 歸 FE-P2A | AT-962-25-3 |
| P0 R-3：AT-960-20-4 字面掃描自我命中 | 歸 FE-P2A | AT-962-25-4 |
| D-135 `DecompositionDto.prdSha256` 後端標必填 | 不歸 P2（P1 修復棒或 RELEASE_READY 批次）；W3 重產時以當下 OpenAPI 為準 | AT-962-27-1 |
| `BackupJobMigrationIT` 視圖排除條件 | P1 已落地；API-P2 開工前以 Grep 確認 `snapshotOfExistingTables` 排除條件在 | AT-962-1-7 |
| D-75、D-86、BLOCKED_DB 校正 | 不收（無 P2 AC 驅動） | 不在本檔 |

### 1.5 AC → AT 映射（機器可讀；每列一個 AT）

| AC | AC 描述 | AT | AT 描述 | 自動化 | 測試類型 | 狀態 |
|----|---------|----|---------|-------|---------|------|
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-1 | Flyway 歷史 1～21 全成功；V21 檔名與描述固定；V1～V20 的 checksum 不變；ddl-auto validate 不報錯。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-2 | research_gate_decisions.gate 的 CHECK 加 SCG6：列舉恰八值，SCG7 與小寫被拒，VARCHAR(11) 容得下全部值。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-3 | research_gate_decisions.details：JSONB NOT NULL 預設空物件，CHECK 限物件型別；三個約定鍵可寫入。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-4 | research_deliveries.snapshot_sha256：CHAR(64) 可空，64 位小寫十六進位才合法。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-5 | research_scr.evidence_url：可空，限 https 開頭且長度不超過 500；不在受控更新清單內。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-6 | P0／P1 的守衛不退步：十八張 research_ 表逐表 DELETE 仍被擋、受控表清單與 append-only 清單不變。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-7 | 六處 Flyway 版本清單加 21，且既有表零變動快照不受 V21 影響。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-8 | Bridge 的拋棄式資料庫夾具套到 V21，且 Bridge 兩個 INSERT 帶新欄位。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-E-1 | 升級不改既有資料：在已有 V20 資料（含各 gate 值的決定列、SCR 列、交付列）的庫上套 V21，既有列逐欄不變。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-E-2 | V21 的時間欄與欄位型別：新增欄型別固定，既有時間欄仍皆為帶時區型別。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1-E-3 | V21 約束名可預期且可被 pg_constraint 逐條查到（不是匿名約束）。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1b-1 | V22 升級不改既有資料：在 V21 資料庫上套 V22，各表既有列逐欄不變，V1～V21 的 checksum 不變、V22 不新增表。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1b-2 | V22 放寬 research_projects.flow_phase：deliver／DELIVERED／COMPLETED 組合可寫，列舉恰十四值。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1b-3 | V22 的 flow_phase CHECK 仍擋非法值：小寫、空字串、尾空白與其他字串皆 23514。 | ✅ | Integration | □ |
| AC-962-1 | 資料庫 V21：gate 加 SCG6、決定列 details、交付列 snapshot_sha256、SCR 列 evidence_url | AT-962-1b-4 | V22 約束名可預期：pg_constraint 以 research_projects_flow_phase_check 查恰一條且定義含 DELIVERED，V21 的 gate 守衛不退步。 | ✅ | Integration | □ |
| AC-962-2 | gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list | AT-962-2-1 | gitops 白名單新增 git 形態：tag --list、tag -a、push origin <tag>、ls-remote --tags origin、remote get-url origin、rev-parse --verify refs/tags。 | ✅ | Unit | □ |
| AC-962-2 | gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list | AT-962-2-2 | gitops 白名單新增 gh 形態：pr create 與 pr list；其餘 gh 子命令仍拒。 | ✅ | Unit | □ |
| AC-962-2 | gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list | AT-962-2-3 | tag 訊息模板正規式：`release: <semver>（RP-NNNN，追溯快照 sha256 <12 碼小寫十六進位>）`；既有 commit 模板不退步。 | ✅ | Unit | □ |
| AC-962-2 | gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list | AT-962-2-4 | valid_semver 常數邊界：官方 semver 2.0 的保守子集，長度上限 64。 | ✅ | Unit | □ |
| AC-962-2 | gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list | AT-962-2-5 | push origin <tag> 與既有 push -u origin <ref> 分開比對，不放寬 -u 形態。 | ✅ | Unit | □ |
| AC-962-2 | gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list | AT-962-2-6 | gh 與 git 呼叫的環境與 token 隔離沿 P1 不變：GH_TOKEN 只進 gh，不進 argv 與 git。 | ✅ | Unit | □ |
| AC-962-2 | gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list | AT-962-2-E-1 | 仍禁形態負控：--force、push --tags、tag -d、tag -f、gh release create、gh pr merge、任何刪除形態，在 spawn 之前拒絕。 | ✅ | Unit | □ |
| AC-962-2 | gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list | AT-962-2-E-2 | 選項注入負控：tag 名與 branch 名以 `-` 起頭、含空白、含控制字元一律在 spawn 前被拒。 | ✅ | Unit | □ |
| AC-962-2 | gitops 白名單 P2 形態：tag、push origin tag、ls-remote、remote get-url、pr create、pr list | AT-962-2-E-3 | EXEC_MODULES 不變：git 與 gh 的 argv 字面只住 gitops.py；新模組不含 git／gh 字面。 | ✅ | Unit | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-1 | SCG-4 登錄：現態 IMPLEMENTATION 先 transition 再 gate PASS，序列與 decision_trace 和人工等價序列相同。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-2 | PR_REVIEW 現態矩陣：EXECUTION_EVALUATION、ADVERSARIAL_EVALUATION 先 transition；現態已是 PR_REVIEW 略過 transition。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-3 | PR_REVIEW FAIL 回 IMPLEMENTATION 並耗預算；連續 FAIL 到限額時 next_state 以引擎回傳為準（含 ESCALATION），Bridge 不自算。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-4 | SCG-5 登錄：RTM_VERIFY PASS 到 RELEASE_READY、FAIL 回 IMPLEMENTATION（預算 2）；現態必須是 RTM_VERIFY。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-5 | RELEASE_READY FAIL（雲端 CI 紅）：理由必填，回 IMPLEMENTATION，登錄為 gate 值 SCG6 並記 details.ci_red。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-6 | 決定入庫映射：PR_REVIEW→SCG4、RTM_VERIFY→SCG5、RELEASE_READY→SCG6；PASS→APPROVED、FAIL→REJECTED；details 承載獨立性聲明與報告參照。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-7 | 零信任 RTM 重驗：PR_REVIEW 要求報告 fully_covered、RTM_VERIFY 要求 ac.pct 為 100，不信 console-api 傳入的判斷。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-8 | 冪等：同一 decision_id 重送不重複 FSM 寫入與 DB 列。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-9 | 與 SCR 共存：SCR MINOR 序列內部的 gate PR_REVIEW FAIL 不寫 SCG4 列；OPEN SCR 期間 `:gates` 回 scr_open。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-E-1 | 現態不合負控：矩陣外的每個 FSM 狀態一律 409 且零 FSM 寫入、零 DB 列。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-E-2 | 無 SUCCEEDED 分流時一律 409，details.cause 為 route_not_succeeded。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-E-3 | 組合與欄位邊界：(RELEASE_READY, PASS) 一律 422；FAIL 理由必填；reason 500／501；review_report_ref 300／301。 | ✅ | Unit | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-E-4 | approver 不合（空、含控制字元、超長）時 422，且不呼叫任何 FSM 動詞。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-E-5 | FSM 在前、DB 在後：DB 阻塞時 `:gates` 回 503 db_blocked，決定列留在 outbox，恢復後重放補寫且游標重衍生。 | ✅ | Integration | □ |
| AC-962-3 | Bridge :gates：內環 SCG-4／SCG-5／RELEASE_READY FAIL 登錄的 FSM 序列與決定入庫 | AT-962-3-E-6 | `:gates` 前置漂移負控：三種 gate 遇凍結 digest 不符一律 422 digest_mismatch，零寫入、零 FSM 呼叫。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-1 | ADMIN 登錄 SCG-4：console-api 產 decisionId、帶最新 runId、approver 取 JWT subject，回應形狀固定。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-2 | PR_REVIEW 服務層前置：任務未完成或 RTM 未全覆蓋或無 RTM 時 409，details.unmet 逐項列出，Bridge 請求數為 0。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-3 | RTM_VERIFY 前置：acPct 為 100 才轉送；99.99 拒。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-4 | 審查者獨立性：PR_REVIEW 必須 reviewerIndependent 為 true；其餘 gate 不要求；Console 不判斷獨立性。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-5 | 欄位邊界：FAIL 必填 reason（1～500）、reviewReportRef 不超過 300、組合限制。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-6 | OPEN SCR 期間 409 scr_open；escalated 由 nextState 前綴 ESCALATION 判定並如實回傳。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-7 | GateRegisterDialog 正控：三個 gate 選項、PR_REVIEW 顯示審查者獨立聲明與報告參照、勾選後送出的請求本文、成功與升級呈現。 | ✅ | Unit | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-8 | GateRegisterDialog：RELEASE_READY 只有 FAIL 選項、FAIL 必填理由計數器、SCR_OPEN 時停用。 | ✅ | Unit | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-E-1 | OPERATOR 呼叫 gates 回 403，Bridge 請求數為 0，無任何研究表變化。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-E-2 | VIEWER 呼叫 gates 回 403，且與 OPERATOR 同為授權鏈拒絕。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-E-3 | 專案狀態負控：研究專案不存在回 404；尚未綁 console 專案回 409。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-E-4 | Bridge 不可達或逾時：502 或 504，且 console-api 不留部分狀態。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-E-5 | console-api 透傳 gates 的 422 digest_mismatch：reason、狀態碼與 details.drift 原樣，不重寫。 | ✅ | Integration | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-E-6 | 未勾審查者獨立聲明不可送：PR_REVIEW 送出鈕停用、請求數為 0；其餘 gate 不要求。 | ✅ | Unit | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-E-7 | FAIL 無理由不可送；理由 500／501 與報告參照 300／301 邊界。 | ✅ | Unit | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-E-8 | 非 ADMIN（OPERATOR、VIEWER）：登錄鈕停用且 title 為權限不足，請求數為 0。 | ✅ | Unit | □ |
| AC-962-4 | console-api POST …/gates：角色、服務層前置、獨立性聲明與稽核 | AT-962-4-E-9 | 錯誤文案：409 fsm_state_conflict（unmet 逐項中文）、409 scr_open、422 digest_mismatch（列出漂移路徑並引導發起 SCR）、502 取 RESEARCH_REASON_TEXT；403 `ACCESS_DENIED` 取通用權限不足文案（非研究 reason）。 | ✅ | Unit | □ |
| AC-962-5 | 鎖：AST、能力登記、動詞表與 P2_OPS | AT-962-5-1 | inner_gates.py 的三個 gate 呼叫皆為字面常數，各在一個 if 分支；gate_needs_guard 對它們為假。 | ✅ | Unit | □ |
| AC-962-5 | 鎖：AST、能力登記、動詞表與 P2_OPS | AT-962-5-2 | inner_gates 專屬規則：只呼叫 fsm_ops.gate 與 fsm_ops.transition，不呼叫 spec_frozen、approve_baseline、spec_refreeze、create_key。 | ✅ | Unit | □ |
| AC-962-5 | 鎖：AST、能力登記、動詞表與 P2_OPS | AT-962-5-3 | delivery.py 與 healing.py 列入 _NO_FSM_WRITE_MODULES：兩檔零 FSM 寫入；RELEASE 的 transition 住 inner_gates。 | ✅ | Unit | □ |
| AC-962-5 | 鎖：AST、能力登記、動詞表與 P2_OPS | AT-962-5-4 | EXEC_MODULES 不變且新模組不自起子行程：spawners 為 EXEC_MODULES 的子集。 | ✅ | Unit | □ |
| AC-962-5 | 鎖：AST、能力登記、動詞表與 P2_OPS | AT-962-5-5 | 能力登記：四個新模組先登記再掃描，實樹與登記表一對一。 | ✅ | Unit | □ |
| AC-962-5 | 鎖：AST、能力登記、動詞表與 P2_OPS | AT-962-5-6 | 動詞表不變：RESEARCH_VERBS 五個、resume-from-escalation 不入；transition 目標含 PR_REVIEW 與 RELEASE。 | ✅ | Unit | □ |
| AC-962-5 | 鎖：AST、能力登記、動詞表與 P2_OPS | AT-962-5-7 | P2_OPS 登記 delivery.record；OPS、METHOD_KINDS、WRITE_METHODS 不動，一一對應鎖仍綠。 | ✅ | Unit | □ |
| AC-962-5 | 鎖：AST、能力登記、動詞表與 P2_OPS | AT-962-5-E-1 | 紅綠自證負控：變數 gate、delivery 內 spec_frozen、healing 內 subprocess 的夾具原始碼各被判違規。 | ✅ | Unit | □ |
| AC-962-5 | 鎖：AST、能力登記、動詞表與 P2_OPS | AT-962-5-E-2 | 游標更新函式同時 append_event：delivery.record 與 gate.decision 內的游標 UPDATE 同函式含 append_event。 | ✅ | Unit | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-1 | 視圖列與日誌行逐筆一致：key 為 (run_id, step_number)，欄位集合固定，view_rows 的 key 集合等於 log 的 key 集合。 | ✅ | Integration | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-2 | 冪等：重送不重複，只追加缺的行。 | ✅ | Integration | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-3 | attempt 導出：同 (run_id, task_id) 內依 step_number 升冪的第 n 筆。 | ✅ | Unit | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-4 | excerpt 取遮蔽後的尾端 300 字元；以字元計不以位元組計；邊界 299、300、301。 | ✅ | Unit | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-5 | 日誌上限 HEALING_LOG_MAX_BYTES＝2097152：到達上限前正常追加，超過後不再追加、寫一次 truncated 行並發 HEALING_LOG_TRUNCATED。 | ✅ | Integration | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-6 | 寫檔經 fsutil.write_text_atomic，LF、UTF-8、ensure_ascii 為假，且不新增目錄項原語站點。 | ✅ | Unit | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-7 | ResearchDb 唯一新增的方法是唯讀的 list_healing_attempts；沒有新寫入面。 | ✅ | Integration | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-8 | `:healing-sync` 為內部端點：檢查序、回應形狀與角色。 | ✅ | Integration | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-E-1 | 無視圖列或專案未綁 console 專案：200 無操作，不建空檔。 | ✅ | Integration | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-E-2 | 並行 sync 持專案鎖序列化，不產生重複行。 | ✅ | Integration | □ |
| AC-962-6 | 自癒同步 :healing-sync：視圖列對日誌行、冪等、尾 300 字元、2 MiB 上限 | AT-962-6-E-3 | 資料庫阻塞時 503 db_blocked，且不寫檔。 | ✅ | Integration | □ |
| AC-962-7 | 自癒遮蔽：Bridge 與 console-api 兩端共用夾具對拍 | AT-962-7-1 | Bridge 遮蔽對拍夾具逐筆：疊用 redact_secrets 與 gitops.redact。 | ✅ | Unit | □ |
| AC-962-7 | 自癒遮蔽：Bridge 與 console-api 兩端共用夾具對拍 | AT-962-7-2 | 研究面恆遮：不讀 REDACT_SECRETS_IN_LOGS，環境關掉開關仍遮。 | ✅ | Unit | □ |
| AC-962-7 | 自癒遮蔽：Bridge 與 console-api 兩端共用夾具對拍 | AT-962-7-3 | Java 遮蔽器與 Python 同夾具逐筆相同（兩端對拍）。 | ✅ | Unit | □ |
| AC-962-7 | 自癒遮蔽：Bridge 與 console-api 兩端共用夾具對拍 | AT-962-7-4 | log 檔逐字掃描：假 token 零明文。 | ✅ | Integration | □ |
| AC-962-7 | 自癒遮蔽：Bridge 與 console-api 兩端共用夾具對拍 | AT-962-7-5 | API 回應逐字掃描：GET healing 的 excerpt 已遮蔽。 | ✅ | Integration | □ |
| AC-962-7 | 自癒遮蔽：Bridge 與 console-api 兩端共用夾具對拍 | AT-962-7-E-1 | 先遮蔽再截尾：token 跨 300 字元邊界時不留半截 token。 | ✅ | Unit | □ |
| AC-962-7 | 自癒遮蔽：Bridge 與 console-api 兩端共用夾具對拍 | AT-962-7-E-2 | 誤殺負控：非機密長字串與雜湊不被遮蔽。 | ✅ | Unit | □ |
| AC-962-7 | 自癒遮蔽：Bridge 與 console-api 兩端共用夾具對拍 | AT-962-7-E-3 | 夾具鎖：兩端測試各自讀同一份 JSON，不各抄一份。 | ✅ | Unit | □ |
| AC-962-8 | SPEC_CHANGE_FORBIDDEN：凍結規格漂移的偵測、標記與告警（不還原） | AT-962-8-1 | 偵測：改動一個已凍結檔，healing.detect_spec_change 回出漂移，且 Bridge 不改該檔。 | ✅ | Integration | □ |
| AC-962-8 | SPEC_CHANGE_FORBIDDEN：凍結規格漂移的偵測、標記與告警（不還原） | AT-962-8-2 | 未改動不誤報；凍結階段取聯集；digest 逐檔重算。 | ✅ | Unit | □ |
| AC-962-8 | SPEC_CHANGE_FORBIDDEN：凍結規格漂移的偵測、標記與告警（不還原） | AT-962-8-3 | 告警：追加 log 一行 spec_change、發 research.alert kind SPEC_CHANGE_FORBIDDEN，同一漂移不重複告警。 | ✅ | Integration | □ |
| AC-962-8 | SPEC_CHANGE_FORBIDDEN：凍結規格漂移的偵測、標記與告警（不還原） | AT-962-8-4 | 偵測點三處：`:healing-sync` 只記錄與告警；`:gates` 與 `:tag` 前置比對不符即 422 digest_mismatch（阻擋，D-142）。 | ✅ | Integration | □ |
| AC-962-8 | SPEC_CHANGE_FORBIDDEN：凍結規格漂移的偵測、標記與告警（不還原） | AT-962-8-5 | API 於漂移列補 specChangeForbidden。 | ✅ | Integration | □ |
| AC-962-8 | SPEC_CHANGE_FORBIDDEN：凍結規格漂移的偵測、標記與告警（不還原） | AT-962-8-E-1 | 不還原負控：偵測後 Bridge 不呼叫任何破壞性 git 形態。 | ✅ | Integration | □ |
| AC-962-8 | SPEC_CHANGE_FORBIDDEN：凍結規格漂移的偵測、標記與告警（不還原） | AT-962-8-E-2 | 凍結檔被刪除亦為漂移，且不拋例外。 | ✅ | Unit | □ |
| AC-962-8 | SPEC_CHANGE_FORBIDDEN：凍結規格漂移的偵測、標記與告警（不還原） | AT-962-8-E-3 | 劃界負控：回應與事件不聲稱『已拒絕補丁』。「被拒」屬框架 hooks，由 V-S1 承擔。 | ✅ | Integration | □ |
| AC-962-9 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | AT-962-9-1 | GET healing 逐值對 DB：列數、run、task、attempt、status、excerpt、occurredAt；VIEWER 可讀。 | ✅ | Integration | □ |
| AC-962-9 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | AT-962-9-2 | maxRetries 取系統參數 agent.maxRetries：預設 3，改 5 後回 5。 | ✅ | Integration | □ |
| AC-962-9 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | AT-962-9-3 | resolved 與 escalated 導出：任務其後 COMPLETED 補 resolved；任務 ESCALATED 的最後一列補 escalated。 | ✅ | Integration | □ |
| AC-962-9 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | AT-962-9-4 | attribution 與 patchResult 恆為 null，不假造（PRD R10 與資料現況不一致，D-140 #5）。 | ✅ | Integration | □ |
| AC-962-9 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | AT-962-9-5 | 日誌落後筆數：logSyncedThrough 與差額推得。 | ✅ | Integration | □ |
| AC-962-9 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | AT-962-9-6 | 通知時點與條件：RunConsumers.handle 在 tx 提交之後、hub.publish 之前，僅當事件使任務進入 RETRYING／FAILED／ESCALATED 時呼叫 notify。 | ✅ | Unit | □ |
| AC-962-9 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | AT-962-9-7 | retryingSteps 計算：最新 run 內 RETRYING 且其後無同 task 非 RETRYING 列者。 | ✅ | Integration | □ |
| AC-962-9 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | AT-962-9-E-1 | 通知 best-effort：Bridge 不可達或逾時只記 log，事件處理與 SSE 發佈不受影響。 | ✅ | Unit | □ |
| AC-962-9 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | AT-962-9-E-2 | 非研究專案的 run：notify 為無操作，Bridge 請求數為 0。 | ✅ | Unit | □ |
| AC-962-9 | console-api 自癒讀端與通知：GET healing、maxRetries、導出欄、RunConsumers post-commit 通知 | AT-962-9-E-3 | 不存在的研究專案 404；專案無 console 專案時回空列 200。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-1 | 差分：Task 拆解欄與 GET decomposition 逐值相等（完成判定＝已簽核且非 stale）。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-2 | 差分：測試規格產生欄與 GET fsm 的 frozenStages、negotiated 逐值相等。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-3 | 差分：程式碼實作欄與專案任務計數、FSM 現態逐值相等；完成判定在邊界上精確。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-4 | 差分：自癒修復欄與 GET healing 的 retryingSteps、escalatedTasks、maxRetries 逐值相等。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-5 | 差分：回歸驗收欄與 executions/{runId}/rtm、FSM 現態逐值相等；完成判定邊界。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-6 | pendingReviews：review_requests 的 PENDING 與該專案所有 run 相連；kind 區分 ESCALATED；已決定者不列。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-7 | gates 清單：SCG4、SCG5、SCG6 各取最近 5 筆；6 筆時只回 5。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-8 | Bridge 不可達：200、bridgeReachable 為 false、stale 為 true、FSM 衍生欄 null 加 unknown、DB 欄取即時值、snapshotAt 取三個來源時間的最大值。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-9 | latestRunId 取專案最新 execution_run；無 run 時為 null 且 rtmAvailable 為 false。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-E-1 | 路由清單比對：/api/v1/research/** 無執行控制動詞路徑；P2 新增路徑集合恰七條；負控夾具被判違規。 | ✅ | Unit | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-E-2 | 看板 GET 無副作用：前後研究表列數與 Bridge 寫入請求數不變，Bridge 只收讀請求。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-E-3 | 未簽核與 SCR 開啟時既有 execute 仍回 409（看板不重造守衛）。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-E-4 | 存取與不存在：VIEWER 200、未登入 401、不存在專案 404。 | ✅ | Integration | □ |
| AC-962-10 | 看板聚合端點 GET …/kanban：五欄差分、待審、gates、Bridge 不可達快照、無第二套執行控制 | AT-962-10-E-5 | 完成判定不被假資料抬高：RTM 諮詢性質不被當成獨立通過證據。 | ✅ | Integration | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-1 | kanbanColumns 純函式窮舉表：五欄完成判定的每個邊界。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-2 | 渲染五欄、順序固定、計數等於資料。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-3 | SSE 到客戶端至 DOM 更新不超過 500ms（假計時器、假 EventSource，不用牆鐘）。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-4 | 三條串流任一幀都觸發 kanban 失效重抓；同一去抖窗內多幀合併為一次。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-5 | 斷線回補：replay_gap 幀或重連後以 REST 全量重抓，並帶 Last-Event-ID。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-6 | 每欄深連結：開啟執行中心與監控中心，帶 researchId；停用規則與文案取登記處。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-7 | Bridge 不可達態：橫幅加快照時間加未知徽章，不渲染空看板，不把快照當即時。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-8 | 靜態判準：KanbanBoard 只用 Link 或既有 endpoints 函式，不 import 新的執行控制端點函式，不直呼 fetch。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-9 | Playwright mock：頁面內 performance.mark 再驗 500ms、斷線回補、Bridge 不可達態。 | ✅ | E2E | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-E-1 | VIEWER：看板可讀，寫入類動作停用，title 為權限不足。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-E-2 | 缺值不猜：FSM 欄為 null 時顯示未知，不顯示 0 或完成。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-E-3 | 去抖邊界：99ms 內合併、101ms 後各自觸發。 | ✅ | Unit | □ |
| AC-962-11 | 看板前端：五欄、SSE 500ms、斷線回補、不可達態、深連結 | AT-962-11-E-4 | a11y 與版面：看板在大、中、小三種寬度（寬度值沿 P1 的 a11y 規格）無水平溢出，axe 無 serious 與 critical。 | ✅ | E2E | □ |
| AC-962-12 | 自癒監視器前端：嘗試次數對上限、純文字、耗盡升級、規格漂移引導 SCR | AT-962-12-1 | 每任務顯示嘗試次數對上限、最近失敗摘錄、歸因與補丁結果；數值等於資料。 | ✅ | Unit | □ |
| AC-962-12 | 自癒監視器前端：嘗試次數對上限、純文字、耗盡升級、規格漂移引導 SCR | AT-962-12-2 | 純文字：摘錄含 HTML 與 on* 屬性時 DOM 無元素節點。 | ✅ | Unit | □ |
| AC-962-12 | 自癒監視器前端：嘗試次數對上限、純文字、耗盡升級、規格漂移引導 SCR | AT-962-12-3 | 耗盡升級：escalated 列顯示已升級徽章並連到決策彈窗，不再提供自動重試。 | ✅ | Unit | □ |
| AC-962-12 | 自癒監視器前端：嘗試次數對上限、純文字、耗盡升級、規格漂移引導 SCR | AT-962-12-4 | 規格漂移列：顯示引導並預填 SCR 發起。 | ✅ | Unit | □ |
| AC-962-12 | 自癒監視器前端：嘗試次數對上限、純文字、耗盡升級、規格漂移引導 SCR | AT-962-12-5 | 日誌落後提示。 | ✅ | Unit | □ |
| AC-962-12 | 自癒監視器前端：嘗試次數對上限、純文字、耗盡升級、規格漂移引導 SCR | AT-962-12-E-1 | 空狀態不顯示假進度。 | ✅ | Unit | □ |
| AC-962-12 | 自癒監視器前端：嘗試次數對上限、純文字、耗盡升級、規格漂移引導 SCR | AT-962-12-E-2 | VIEWER：發起 SCR 鈕停用。 | ✅ | Unit | □ |
| AC-962-12 | 自癒監視器前端：嘗試次數對上限、純文字、耗盡升級、規格漂移引導 SCR | AT-962-12-E-3 | 摘錄長度與版面：300 字元摘錄不撐破容器。 | ✅ | Unit | □ |
| AC-962-13 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | AT-962-13-1 | 展開時以 useRunStream 餵 LiveLogCard；收合時仍訂閱，開合不重連。 | ✅ | Unit | □ |
| AC-962-13 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | AT-962-13-2 | 靜態判準：與執行中心共用同一日誌元件與串流客戶端，無第二份實作。 | ✅ | Unit | □ |
| AC-962-13 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | AT-962-13-3 | 純文字哨兵：script、img、on* 屬性與哨兵呼叫皆為 0，ANSI 序列不殘留。 | ✅ | Unit | □ |
| AC-962-13 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | AT-962-13-4 | run 結束後以 REST 回補：steps?afterSeq 分頁補齊，與結束前一致。 | ✅ | Unit | □ |
| AC-962-13 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | AT-962-13-5 | 開合狀態僅存瀏覽器：鍵 research.terminal.open，預設收合，localStorage 例外時仍可用。 | ✅ | Unit | □ |
| AC-962-13 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | AT-962-13-6 | log 幀到達至顯示不超過 500ms（假計時器）。 | ✅ | Unit | □ |
| AC-962-13 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | AT-962-13-7 | 斷線以 Last-Event-ID 回補。 | ✅ | Unit | □ |
| AC-962-13 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | AT-962-13-E-1 | 靜態掃描負控：夾具原始碼含 WebSocket、new EventSource、dangerouslySetInnerHTML 皆被判違規。 | ✅ | Unit | □ |
| AC-962-13 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | AT-962-13-E-2 | runId 為 null：顯示尚無執行批次，不訂閱。 | ✅ | Unit | □ |
| AC-962-13 | 終端窗格：共用日誌元件與串流客戶端、純文字、REST 回補、開合不影響串流 | AT-962-13-E-3 | 重用元件零改動：LiveLogCard.tsx、useRunStream.ts、LogPanel.tsx 零 diff。 | ✅ | Gate | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-1 | 類型 (b) 自癒耗盡：ESCALATED 待審開彈窗，四個決定按鈕由 allowedDecisions 驅動。 | ✅ | Unit | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-2 | 類型 (c) Agent 請求審核：kind 非 ESCALATED 的待審與 review-request 幀同殼處理。 | ✅ | Unit | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-3 | 類型 (d) 重大架構選擇：alert ESCALATION 幀與 review-request 皆可觸發；去重鍵 reviewId，無則用 alert 幀 seq；Console 不判斷何謂重大。 | ✅ | Unit | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-4 | 決定送出走既有端點，不寫 research gates。 | ✅ | Unit | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-5 | 稍後處理：只關窗並以 sessionStorage 記 key，待辦仍在列表與頂列徽章，重新整理後仍在。 | ✅ | Unit | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-6 | 去重：SSE 重播的重複幀同 key 只出現一個彈窗；重新整理後由 pendingReviews 重建。 | ✅ | Unit | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-7 | 單一彈窗殼：research 目錄不得出現第二個彈窗殼，並重用 SddEscalationBlock。 | ✅ | Unit | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-8 | 決定入庫：review_requests 的 decided_by、decided_at、comment 與 audit_log 一列；不寫 research_gate_decisions。 | ✅ | Integration | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-E-1 | VIEWER：可讀內容，決定鈕全停用，title 為權限不足。 | ✅ | Unit | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-E-2 | allowedDecisions 以外的按鈕不渲染。 | ✅ | Unit | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-E-3 | 他人已決定：決定端點回 409 或 404 時顯示錯誤並重抓 pendingReviews，不重複送出。 | ✅ | Unit | □ |
| AC-962-14 | 人機協同決策彈窗 (b)～(d)：單一殼、去重、稍後處理、決定走既有端點 | AT-962-14-E-4 | 無逾時自動處理：時間前進 72 小時仍無自動決定請求。 | ✅ | Unit | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-1 | 發起入口：看板與步驟 4 頁頂的『發起規格變更（SCR）』，OPERATOR 以上可用。 | ✅ | Unit | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-2 | 表單欄位齊備與預填：kind、sourceKind、reason 計數器、reasonClass 中文五值、affectedSections 多選、證據連結。 | ✅ | Unit | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-3 | 送出與結果：202 顯示已發起；MAJOR 導向後繼專案；HEALING_FAILED 只顯示可複製指令。 | ✅ | Unit | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-4 | 錯誤回顯：422 violations 逐筆回到欄位；scr_open、scr_limit、fsm_state_conflict 顯示登記文案。 | ✅ | Unit | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-5 | SCR_OPEN 時橫幅與停用規則：看板、InnerLoopLinks、GateRegisterDialog、ReleaseActions 的啟動類動作一律停用並顯示同一文案。 | ✅ | Unit | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-6 | console-api 的 evidenceUrl：ScrOpenRequest 選填，轉送 Bridge 的 evidence_url，ScrDto 回傳。 | ✅ | Integration | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-7 | Bridge `:scr` 接受 evidence_url 並寫入 research_scr.evidence_url。 | ✅ | Integration | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-8 | scr.open op 的 INSERT 帶 evidence_url，欄位順序與參數一一對應。 | ✅ | Unit | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-E-1 | 常數邊界：reason 500／501、affectedSections 20／21、單項 200／201、證據連結 500／501。 | ✅ | Unit | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-E-2 | 無權不送請求：VIEWER 的對話框不能開啟、送出請求數為 0。 | ✅ | Unit | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-E-3 | reasonClass 兩種拼法：前端送中文，後端兩種拼法皆收。 | ✅ | Unit | □ |
| AC-962-15 | SCR 前端與 evidence_url：發起入口、表單、橫幅、停用規則、證據連結入庫 | AT-962-15-E-4 | 證據連結以外部連結安全規則顯示：只接受 https，顯示為純文字。 | ✅ | Unit | □ |
| AC-962-16 | ResearchBackLink：深連結 ?researchId=、兩頁掛點、反向釘改寫 | AT-962-16-1 | ResearchBackLink：UUID 顯示回到研發工作流，href 固定；null 不渲染。 | ✅ | Unit | □ |
| AC-962-16 | ResearchBackLink：深連結 ?researchId=、兩頁掛點、反向釘改寫 | AT-962-16-2 | ExecuteView 在 ?researchId=<uuid> 時頁頂顯示 BackLink。 | ✅ | Unit | □ |
| AC-962-16 | ResearchBackLink：深連結 ?researchId=、兩頁掛點、反向釘改寫 | AT-962-16-3 | MonitorView 在 ?researchId=<uuid> 時頁頂顯示 BackLink。 | ✅ | Unit | □ |
| AC-962-16 | ResearchBackLink：深連結 ?researchId=、兩頁掛點、反向釘改寫 | AT-962-16-4 | 看板與 InnerLoopLinks 的連結帶 researchId 查詢參數。 | ✅ | Unit | □ |
| AC-962-16 | ResearchBackLink：深連結 ?researchId=、兩頁掛點、反向釘改寫 | AT-962-16-5 | P1 反向釘改寫：工作區只在已有 consoleProjectId 的步驟 4 面板出現連結字樣，其他步驟仍沒有。 | ✅ | Unit | □ |
| AC-962-16 | ResearchBackLink：深連結 ?researchId=、兩頁掛點、反向釘改寫 | AT-962-16-E-1 | 無參數（深連結直接開執行中心）不顯示返回連結，不猜。 | ✅ | Unit | □ |
| AC-962-16 | ResearchBackLink：深連結 ?researchId=、兩頁掛點、反向釘改寫 | AT-962-16-E-2 | 非 UUID 一律忽略：路徑穿越、腳本、長度不符、非十六進位。 | ✅ | Unit | □ |
| AC-962-16 | ResearchBackLink：深連結 ?researchId=、兩頁掛點、反向釘改寫 | AT-962-16-E-3 | 零後端、零儲存：不呼叫 API、不讀寫 storage；頁面殼零差異。 | ✅ | Unit | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-1 | build_traceability：列數等於凍結 PRD 的 AC 總數，一個 AC 一列，集合相等、無遺漏無多餘。 | ✅ | Integration | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-2 | gherkinSummary 每段不超過 120 字；邊界 120／121。 | ✅ | Unit | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-3 | unitStatus 導出：覆蓋任務全 COMPLETED 為 PASS；任一 FAILED 或 ESCALATED 為 FAIL；其餘 NOT_RUN；無覆蓋任務為 NONE。 | ✅ | Unit | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-4 | e2eStatus：僅當存在 SCG5 的 APPROVED 決定且其後無 REJECTED 時為 PASS，否則 NOT_RUN（無逐 AC 的 E2E 機器來源，如實標示）。 | ✅ | Unit | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-5 | totals：未覆蓋＝unitStatus 不為 PASS 的列數；e2e 欄不計入；零測試不是通過。 | ✅ | Unit | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-6 | `:traceability-preview` 零副作用：DB 與檔案前後相同。 | ✅ | Integration | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-7 | GET delivery/traceability 逐值對 Bridge 回放；VIEWER 可讀；rtm 欄形狀固定。 | ✅ | Integration | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-8 | 表格呈現：一 AC 一列、紅標、未覆蓋計數、摘要純文字。 | ✅ | Unit | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-E-1 | 凍結 PRD 讀不到：409 fsm_state_conflict，unmet 含 prd_not_frozen，零寫入。 | ✅ | Integration | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-E-2 | 拆解缺席或 stale：全部 AC 的 unitStatus 為 NONE，不假設通過。 | ✅ | Integration | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-E-3 | AC 數邊界：N 為 1 與 250 時列數仍等於 N。 | ✅ | Unit | □ |
| AC-962-17 | 追溯表：build_traceability、unitStatus 導出、totals、GET traceability 與表格呈現 | AT-962-17-E-4 | 零信任：`:tag` 內重算追溯表，不信任請求帶入的列。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-1 | Tag 正控序列：驗證、冪等探測、取 commit、tag -a、（push:true 且有 origin）push、寫快照檔、單交易入庫、transition RELEASE、對帳。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-2 | tag 訊息只取模板：release: <tag>（RP-NNNN，追溯快照 sha256 <前 12 碼>），使用者 message 不進 argv，只入 detail 並先遮蔽。 | ✅ | Unit | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-3 | 快照檔與 R11：traceability_matrix.json 鍵序固定、LF、不跳脫中文；其 sha256 等於 snapshot_sha256 欄；rtm_report_ref 為檔案相對路徑。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-4 | 單一 DB 交易：RELEASE_TAG 列與 research.delivery 事件同交易，欄位值固定。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-5 | FSM 與游標：transition --to RELEASE 序列與游標落點。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-6 | 冪等續跑：同 tag 已有 CREATED 列時跳過 tag、push、入庫，只補 transition。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-7 | push 失敗：502 delivery_step_failed、failure_step 為 push，本地 tag 保留，可重送續跑，絕不強推。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-8 | FSM 步驟失敗：502 failure_step 為 fsm_release，DB 列已存，重送只重做 transition。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-9 | push 確認規則：push 為假或無 origin 不推送；遠端已有同 sha 視為成功；不同 sha 拒。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-E-1 | tag 已存在且非本專案 CREATED 列：409 tag_exists，零 DB、零 FSM。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-E-2 | 前置不成立：現態非 RELEASE_READY、追溯未全覆蓋、SCR 開啟，各 409 且零 git 副作用。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-E-3 | createGithubRelease 為 true：422 release_not_supported，零副作用。 | ✅ | Unit | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-E-4 | argv 注入：message 含 --exec、換行、$(...) 時 argv 仍恰為模板。 | ✅ | Unit | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-E-5 | 規格漂移與 Tag：前置比對凍結 digest 不符即 422 digest_mismatch，零副作用（D-142 ⚖P2-9）。 | ✅ | Integration | □ |
| AC-962-18 | Bridge :tag：冪等序列、快照檔、單交易入庫、FSM RELEASE 與失敗續跑 | AT-962-18-E-6 | 容器模式前置：目標專案不可寫（repo_writable 缺）時 `:tag` 回 422 route_unsupported_in_deployment，零副作用。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-1 | ADMIN 建立 tag：轉送 Bridge 一次，請求欄位固定。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-2 | 服務層前置先於 Bridge：FSM 現態、RTM 閘、無 OPEN SCR，不合 409 且 Bridge 請求 0。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-3 | tagName 正規式與長度邊界：與 Bridge 同一份常數字面。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-4 | message 長度：200 通過、201 為 422。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-5 | Bridge 錯誤透傳：tag_exists、delivery_step_failed 保持 reason、HTTP 狀態與 details。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-6 | 稽核：每個 tag 寫入請求入 audit_log，且與 Bridge 事件同 trace_id。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-E-1 | OPERATOR 呼叫 tag 回 403，Bridge 請求 0，無研究表變化。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-E-2 | VIEWER 呼叫 tag 回 403。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-E-3 | createGithubRelease 為 true：422 release_not_supported，Bridge 請求 0；push 缺省為 false。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-E-4 | Bridge 不可達：502，無部分狀態。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-E-5 | console-api 透傳 tag 的 422 digest_mismatch。 | ✅ | Integration | □ |
| AC-962-19 | console-api Tag 端點：服務層前置、semver 與長度邊界、錯誤透傳與稽核 | AT-962-19-E-6 | console-api 直呼 `:tag` 於容器模式：透傳 422 route_unsupported_in_deployment（沿 P1 AT-961-22-5 體例），不自行猜測部署能力。 | ✅ | Integration | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-1 | PR 正控序列：push -u origin、gh pr create（argv 陣列、token 只進環境）、入庫、事件。 | ✅ | Integration | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-2 | 標題與內文模板：標題截斷 60 字、內文四段固定序、不超過 4000 字、不帶使用者自由文字。 | ✅ | Unit | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-3 | title 欄只作預覽：不等於模板輸出時 422 title_not_template；bodyPreviewAck 必須為 true。 | ✅ | Unit | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-4 | 已有 PR 冪等：回既有、created 為 false，不再 gh pr create。 | ✅ | Integration | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-5 | 前置缺項：gh、gh_auth、origin、repo_writable 缺任一，422 route_unsupported_in_deployment，零副作用。 | ✅ | Integration | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-6 | token 零外洩：只進 gh 子行程環境，不入 argv、log、DB、回應。 | ✅ | Integration | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-7 | 失敗不補償：502 delivery_step_failed、failure_step 為 push 或 pr_create，不寫 FAILED 列，只發 FAILED 事件。 | ✅ | Integration | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-8 | console-api：ADMIN 建 PR，只在此端點讀 research.github_token 放進本文 github_token。 | ✅ | Integration | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-E-1 | OPERATOR 與 VIEWER 呼叫 pr 回 403，Bridge 請求 0。 | ✅ | Integration | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-E-2 | bodyPreviewAck 為 false 或缺：422，Bridge 請求 0。 | ✅ | Integration | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-E-3 | branch 驗證：預設取 route_decisions.git_branch；不合 ref 規則 422。 | ✅ | Integration | □ |
| AC-962-20 | PR：標題與內文確定性模板、預覽確認、冪等、前置缺項、token 零外洩、失敗不補償 | AT-962-20-E-4 | PR 內文不含 GH_TOKEN：leak 模式下以 token 值掃描 PR 標題與內文。 | ✅ | Integration | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-1 | 步驟 5 取代占位：deliver 為 DeliverPanel，研究面占位面板為零個。 | ✅ | Unit | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-2 | DeliverPanel 整體呈現：追溯表、發布動作列、交付紀錄、對帳狀態。 | ✅ | Unit | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-3 | 建立 Tag 鈕停用規則：未覆蓋大於 0、非 RELEASE_READY、SCR_OPEN、非 ADMIN 任一成立即停用並顯示原因與未覆蓋清單。 | ✅ | Unit | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-4 | Tag 確認框：semver 即時驗證、push 勾選預設未勾並附說明、成功顯示交付與快照 sha256、錯誤 reason 文案。 | ✅ | Unit | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-5 | PR：已記錄顯示 URL（新分頁、noopener noreferrer）；無 PR 時 ADMIN 見建立 PR 並預覽標題、內文與推送目標；其餘顯示尚未建立與原因。 | ✅ | Unit | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-6 | 開啟本地專案：顯示專案根路徑與複製鈕；容器模式標示容器內路徑；不假裝可開啟。 | ✅ | Unit | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-7 | GET delivery 概覽逐欄：deliveries、snapshot、projectRoot、containerMode、preconditions。 | ✅ | Integration | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-8 | 步驟 5 的 mock E2E：版面無溢出、axe 無 serious 與 critical、兩個確認框焦點陷阱與歸還。 | ✅ | E2E | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-E-1 | RTM 100% 但非 RELEASE_READY：仍停用。 | ✅ | Unit | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-E-2 | 純文字渲染：摘要含 HTML 不執行。 | ✅ | Unit | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-E-3 | 外部連結安全：所有外部連結帶 noopener noreferrer。 | ✅ | Unit | □ |
| AC-962-21 | 步驟 5 前端：DeliverPanel、追溯表、發布動作列、Tag 與 PR 確認框、開啟本地專案 | AT-962-21-E-4 | 已交付（FSM 為 RELEASE）：Tag 鈕顯示已建立並停用，不可重複送出。 | ✅ | Unit | □ |
| AC-962-22 | 交付稽核與完整率：records/audit、audit_log 與事件 trace_id、append-only | AT-962-22-1 | 已交付專案 records/audit：missing 為空（R11 筆數至少 1；R10 與 R12 允許 0）。 | ✅ | Integration | □ |
| AC-962-22 | 交付稽核與完整率：records/audit、audit_log 與事件 trace_id、append-only | AT-962-22-2 | 未交付專案口徑不變：missing 仍含 R11。 | ✅ | Integration | □ |
| AC-962-22 | 交付稽核與完整率：records/audit、audit_log 與事件 trace_id、append-only | AT-962-22-3 | Release Tag 稽核：audit_log 一列與 research.delivery 事件同 trace_id，事件含 digest 與理由。 | ✅ | Integration | □ |
| AC-962-22 | 交付稽核與完整率：records/audit、audit_log 與事件 trace_id、append-only | AT-962-22-4 | SCG 登錄稽核：gates 請求入 audit_log，決定列的 audit_trace_id 與之對應。 | ✅ | Integration | □ |
| AC-962-22 | 交付稽核與完整率：records/audit、audit_log 與事件 trace_id、append-only | AT-962-22-5 | 交付列不可變與唯一：append-only 守衛、UNIQUE(research_id, kind, ref)。 | ✅ | Integration | □ |
| AC-962-22 | 交付稽核與完整率：records/audit、audit_log 與事件 trace_id、append-only | AT-962-22-E-1 | 失敗的 tag（502）不產生 research_deliveries 列，但 audit_log 仍有一列。 | ✅ | Integration | □ |
| AC-962-22 | 交付稽核與完整率：records/audit、audit_log 與事件 trace_id、append-only | AT-962-22-E-2 | 重送冪等：同 (kind, ref) 不增列。 | ✅ | Integration | □ |
| AC-962-22 | 交付稽核與完整率：records/audit、audit_log 與事件 trace_id、append-only | AT-962-22-E-3 | R10 為 0 筆的已交付專案仍通過完整率。 | ✅ | Integration | □ |
| AC-962-23 | 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳 | AT-962-23-1 | CHECK_IDS 加第七項 delivery，順序固定；以原始碼為準，不寫死數字。 | ✅ | Unit | □ |
| AC-962-23 | 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳 | AT-962-23-2 | delivery 檢查：重算 traceability_matrix.json 的 sha256 對 snapshot_sha256；一致 ok，不符 drift。 | ✅ | Integration | □ |
| AC-962-23 | 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳 | AT-962-23-3 | 無交付列：absent_check，ok 且 present 為假；有列但檔缺失為 drift。 | ✅ | Integration | □ |
| AC-962-23 | 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳 | AT-962-23-4 | 交付時點自動對帳：reconcile_at_delivery 在 :tag 成功後恰一次，結果 consistent 為 true（出口 g）。 | ✅ | Integration | □ |
| AC-962-23 | 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳 | AT-962-23-5 | `:reconcile` 尾端順帶 healing.sync，失敗不影響對帳結果。 | ✅ | Integration | □ |
| AC-962-23 | 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳 | AT-962-23-6 | console-api 轉送七項：名稱取自 Bridge 的 CHECK_IDS，迷你 Bridge 回 7 項。 | ✅ | Integration | □ |
| AC-962-23 | 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳 | AT-962-23-7 | 前端 `RECONCILE_CHECK_LABEL` 新增 delivery＝『交付』，`reconcileDriftView` 對 delivery drift 回檔案漂移列，單一橫幅顯示 delivery 漂移。 | ✅ | Unit | □ |
| AC-962-23 | 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳 | AT-962-23-E-1 | P1 的 pending_correction 第三態不受影響。 | ✅ | Integration | □ |
| AC-962-23 | 對帳第七項 delivery：快照 sha256 對 snapshot_sha256、交付時點自動對帳 | AT-962-23-E-2 | 只報告不修復：對帳後快照檔與 DB 列位元組不變。 | ✅ | Integration | □ |
| AC-962-24 | 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125 | AT-962-24-1 | reason 由 35 增為 37：新增 tag_exists（409）、delivery_step_failed（502），四方集合相等。 | ✅ | Unit | □ |
| AC-962-24 | 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125 | AT-962-24-2 | OpenApiIT 計數：路徑 107 變 114、操作 124 變 131；研究路徑 30 變 37、操作 35 變 42、operationId 34 變 41、狀態碼表 35 變 42。 | ✅ | Integration | □ |
| AC-962-24 | 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125 | AT-962-24-3 | 七個新操作的狀態碼表逐一登記：gates、tag、pr 含 403、404、409、422、502，讀端含 401、403、404。 | ✅ | Integration | □ |
| AC-962-24 | 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125 | AT-962-24-4 | RBAC 矩陣：gates、tag、pr 為 ADMIN 專屬（OPERATOR 與 VIEWER 皆 403）；kanban、healing、delivery、traceability 的 GET 為 VIEWER 以上。 | ✅ | Integration | □ |
| AC-962-24 | 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125 | AT-962-24-5 | 端點函式總數與 operationId 一一對應：118 增為 125。 | ✅ | Unit | □ |
| AC-962-24 | 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125 | AT-962-24-6 | 前端兩個新 reason 有中文文案且 research.ts 常數與後端逐字一致。 | ✅ | Unit | □ |
| AC-962-24 | 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125 | AT-962-24-E-1 | RESEARCH_ 前綴：新常數不污染 REASONS 集合鎖。 | ✅ | Unit | □ |
| AC-962-24 | 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125 | AT-962-24-E-2 | 未登記四方鎖的字面不得流出：Bridge 新模組的 reason 字面皆屬 37 個。 | ✅ | Unit | □ |
| AC-962-24 | 契約鎖：reason 37、OpenAPI 114／131、RBAC、端點函式 125 | AT-962-24-E-3 | 契約與 Architecture 的 reason 表缺列由具名名單鎖住，勘誤批次後清空。 | ✅ | Gate | □ |
| AC-962-25 | 說明登記表、五步接線與兩處漂移橫幅整併、導覽不動 | AT-962-25-1 | 說明登記表：步驟 4 其餘與步驟 5 的欄位釋義一次寫完，過三道鎖與 lint，HELP_PAGES 計數不變。 | ✅ | Unit | □ |
| AC-962-25 | 說明登記表、五步接線與兩處漂移橫幅整併、導覽不動 | AT-962-25-2 | P2 版步驟接入：五步皆真面板；Gate 0 未完成時超前導回規則不變。 | ✅ | Unit | □ |
| AC-962-25 | 說明登記表、五步接線與兩處漂移橫幅整併、導覽不動 | AT-962-25-3 | 兩處漂移橫幅整併為工作區單一橫幅（D-131(6)）。 | ✅ | Unit | □ |
| AC-962-25 | 說明登記表、五步接線與兩處漂移橫幅整併、導覽不動 | AT-962-25-4 | P0 殘留 R-3：反向斷言正則改字串拼接，AT_960_20_4 的字面掃描不再自我命中。 | ✅ | Unit | □ |
| AC-962-25 | 說明登記表、五步接線與兩處漂移橫幅整併、導覽不動 | AT-962-25-5 | 導覽與詞彙不動：registry.ts 零 diff，mobile 不超過 6，詞彙與衍生標籤計數與 P1 相同。 | ✅ | Unit | □ |
| AC-962-25 | 說明登記表、五步接線與兩處漂移橫幅整併、導覽不動 | AT-962-25-E-1 | 四區塊零差異：layout.tsx 與 components/layout/** 零 diff。 | ✅ | Gate | □ |
| AC-962-25 | 說明登記表、五步接線與兩處漂移橫幅整併、導覽不動 | AT-962-25-E-2 | 狀態表不增：StateTableId 成員數不變。 | ✅ | Unit | □ |
| AC-962-26 | 寫入擁有權與 db op：Bridge 唯一寫入者、delivery.record、outbox、檢查序 | AT-962-26-1 | 字串掃描：console-api 新類對 research_* 零 INSERT、UPDATE、DELETE。 | ✅ | Unit | □ |
| AC-962-26 | 寫入擁有權與 db op：Bridge 唯一寫入者、delivery.record、outbox、檢查序 | AT-962-26-2 | delivery.record op：研究表唯一寫入者為 Bridge，DB 列與事件同一交易，fail-loud。 | ✅ | Integration | □ |
| AC-962-26 | 寫入擁有權與 db op：Bridge 唯一寫入者、delivery.record、outbox、檢查序 | AT-962-26-3 | outbox：DB 阻塞時 delivery.record 與 gate.decision 入 outbox，恢復後補寫，游標重衍生。 | ✅ | Integration | □ |
| AC-962-26 | 寫入擁有權與 db op：Bridge 唯一寫入者、delivery.record、outbox、檢查序 | AT-962-26-4 | 新 Java 類符合 ArchUnit 層次與命名；masker 在 persistence 層。 | ✅ | Unit | □ |
| AC-962-26 | 寫入擁有權與 db op：Bridge 唯一寫入者、delivery.record、outbox、檢查序 | AT-962-26-5 | research.delivery 事件登記：成功與失敗兩種 payload 的鍵集合定案並進 EVENT_PAYLOAD_KEYS，append_event 對登記外鍵 fail-loud。 | ✅ | Unit | □ |
| AC-962-26 | 寫入擁有權與 db op：Bridge 唯一寫入者、delivery.record、outbox、檢查序 | AT-962-26-E-1 | Bridge 五個新端點的檢查序：權杖、資料庫、專案存在、本文、前置。 | ✅ | Integration | □ |
| AC-962-26 | 寫入擁有權與 db op：Bridge 唯一寫入者、delivery.record、outbox、檢查序 | AT-962-26-E-2 | healing-sync 為內部端點：不在 console-api 路由與 OpenAPI。 | ✅ | Integration | □ |
| AC-962-27 | FE-W3 型別層：schema.d.ts 重產、生成型替換手寫型、夾具補必填欄 | AT-962-27-1 | schema.d.ts 由 backend OpenAPI 重產：七條新路徑與新 DTO 存在，重產後 diff 為空。 | ✅ | Gate | □ |
| AC-962-27 | FE-W3 型別層：schema.d.ts 重產、生成型替換手寫型、夾具補必填欄 | AT-962-27-2 | 手寫型別改引生成型：P2 型別皆為生成型別名的別名或引用。 | ✅ | Unit | □ |
| AC-962-27 | FE-W3 型別層：schema.d.ts 重產、生成型替換手寫型、夾具補必填欄 | AT-962-27-3 | 夾具補必填欄、不放寬為選填（D-135）：生成型必填欄在夾具皆有值。 | ✅ | Unit | □ |
| AC-962-27 | FE-W3 型別層：schema.d.ts 重產、生成型替換手寫型、夾具補必填欄 | AT-962-27-E-1 | tsc、lint、build 皆 rc 0。 | ✅ | Gate | □ |
| AC-962-27 | FE-W3 型別層：schema.d.ts 重產、生成型替換手寫型、夾具補必填欄 | AT-962-27-E-2 | 單一歸屬：schema.d.ts 只由 FE-W3 修改。 | ✅ | Gate | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-1 | 出口 (a)：內環走完到交付。gates（PR_REVIEW PASS、RTM_VERIFY PASS）→ FSM RELEASE_READY → tag（file:// bare origin）→ FSM RELEASE，逐字證據。 | ✅ | Integration | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-2 | 出口 (a) 的 PR URL：假 gh 走 pr create 與 pr list。 | ✅ | Integration | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-3 | 出口 (b)(f)：引擎重試耗盡自然觸發 ESCALATED（claude 為 mock 可執行檔，須標明），視圖對真失敗步驟有列。 | ✅ | Integration | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-4 | 出口 (b)：ESCALATED 後彈窗出現（mock 一次、真棧一次），決定走既有 review 端點。 | ✅ | E2E | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-5 | 出口 (c)：本機模式從看板 UI 發起 MINOR SCR，Gate 0 經 approveViaApi 代驗，舊凍結版保留、新 digest 入庫。 | ✅ | E2E | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-6 | 出口 (g)：`:tag` 後對帳 consistent 為 true。 | ✅ | Integration | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-7 | Docker mock-only：看板、自癒視圖、終端窗格、追溯表可驗；`:gates` 用暫存 FSM 鍵。 | ✅ | E2E | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-8 | Docker 容器模式負控：API 直呼 :tag 回 422 route_unsupported_in_deployment，DB 零變化。 | ✅ | E2E | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-E-1 | SPEC_CHANGE_FORBIDDEN 取證：暫存專案手改凍結檔，偵測加告警，sha 不被 Bridge 改動；『被拒』列 V-S1。 | ✅ | Integration | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-E-2 | 清理義務：subst、worktree、bare repo、拋棄式 DB、假 gh 目錄、Docker 測試標籤與懸空卷無殘留。 | ✅ | Gate | □ |
| AC-962-28 | 整合 P2：內環走完到交付、真失敗步驟、Docker mock-only 負控與清理 | AT-962-28-E-3 | hermetic：任何 P2 pytest AT 不連外網，真 GitHub 不被連線（沿 AT-961-23-E-1 的替身體例）。 | ✅ | Integration | □ |
| AC-962-29 | 邊界、跨平台與衛生閘：允許集合、禁區、無新守衛、無新目錄項原語 | AT-962-29-1 | 允許變更檔案集合：只動各包 §5.7 的集合，其餘零差異。 | ✅ | Gate | □ |
| AC-962-29 | 邊界、跨平台與衛生閘：允許集合、禁區、無新守衛、無新目錄項原語 | AT-962-29-2 | 禁區零差異：根 CLAUDE.md、.claude、tools、.github、AutoClaude、AISDLC_SDD、Flyway V1～V20、package.json、sdd_cli.py、rtm.py、SecurityConfig、ExecutionController、ResearchFlowPolicy.java、nav registry。 | ✅ | Gate | □ |
| AC-962-29 | 邊界、跨平台與衛生閘：允許集合、禁區、無新守衛、無新目錄項原語 | AT-962-29-3 | 不新增 os.replace、rename、move 站點，根層 dirent 鎖綠。 | ✅ | Gate | □ |
| AC-962-29 | 邊界、跨平台與衛生閘：允許集合、禁區、無新守衛、無新目錄項原語 | AT-962-29-4 | 根層 tools/tests 相關鎖自跑（D-141）：windowsapps guard 平價、E501 棘輪、_TREE_FILE_FLOORS、名冊。 | ✅ | Gate | □ |
| AC-962-29 | 邊界、跨平台與衛生閘：允許集合、禁區、無新守衛、無新目錄項原語 | AT-962-29-5 | Python 衛生：ruff 0 錯，新檔 open 與 read_text 與 write_text 帶 encoding，時間戳帶 tz。 | ✅ | Gate | □ |
| AC-962-29 | 邊界、跨平台與衛生閘：允許集合、禁區、無新守衛、無新目錄項原語 | AT-962-29-E-1 | 子行程使用者不增：除 gitops、sdd_cli 既有六檔外無新增。 | ✅ | Gate | □ |
| AC-962-29 | 邊界、跨平台與衛生閘：允許集合、禁區、無新守衛、無新目錄項原語 | AT-962-29-E-2 | 新增夾具目錄不含 shell 腳本，名冊不變。 | ✅ | Gate | □ |
| AC-962-29 | 邊界、跨平台與衛生閘：允許集合、禁區、無新守衛、無新目錄項原語 | AT-962-29-E-3 | 入庫文件守門：無測試摘要字樣加四位數字同行。 | ✅ | Gate | □ |
| AC-962-30 | 文件連動與 V 系列：K.6、十四處勘誤、RTM 回填、出口逐項 | AT-962-30-1 | V21 DDL 與 Architecture K.6 逐字一致，且與 `V21_DDL.md` 草案對拍。 | ✅ | Gate | □ |
| AC-962-30 | 文件連動與 V 系列：K.6、十四處勘誤、RTM 回填、出口逐項 | AT-962-30-2 | RELEASE_READY 勘誤批次：D-140 十四處與 D-139 連動寫入契約、ADR-003 D16、Architecture、PRD，並一併 refreeze。 | ✅ | Gate | □ |
| AC-962-30 | 文件連動與 V 系列：K.6、十四處勘誤、RTM 回填、出口逐項 | AT-962-30-3 | RTM-P2 子表回填：列數等於 F 1 加 US 3 加 AC 30 加 AT 總數，四格回填，不刪列不改號。 | ✅ | Gate | □ |
| AC-962-30 | 文件連動與 V 系列：K.6、十四處勘誤、RTM 回填、出口逐項 | AT-962-30-4 | V 系列（§6）皆有文字證據或如實標未驗。 | ✅ | Gate | □ |
| AC-962-30 | 文件連動與 V 系列：K.6、十四處勘誤、RTM 回填、出口逐項 | AT-962-30-5 | PRD §8.1 P2 出口 (a)～(i) 逐項有證據。 | ✅ | Gate | □ |
| AC-962-30 | 文件連動與 V 系列：K.6、十四處勘誤、RTM 回填、出口逐項 | AT-962-30-E-1 | 計數宣告一致：TCS 檔頭 AT 數、RTM 列數、§1.5 列數相等。 | ✅ | Gate | □ |
| AC-962-30 | 文件連動與 V 系列：K.6、十四處勘誤、RTM 回填、出口逐項 | AT-962-30-E-2 | 專案文件上限：AgentConsole/CLAUDE.md 不超過 200 行、README.md 不超過 80 行。 | ✅ | Gate | □ |

---
## 2. 可自動化 AT 格式規範

> **徑判定（計畫書 §1 末段）**：Bridge（Python）可走徑①委派迴圈；backend（Java）與 frontend（TS）走徑②「SDD session-only」——**Java 與 TS 的 AT 不入 evaluator**，由 session 內自跑判定指令並**把輸出逐字貼進證據檔與 RTM**（沒貼＝未驗證），並在最終回覆逐 AT 列出 AT 底線形與其測試輸出。指令核對型（Gate）AT 由主控或收尾單人窗口跑。Bridge 的 AT 若改走徑①，由主控把 §3 的 Given／When／Then 轉成 Gherkin 區塊並加驗收字樣，不改 AT 內容；本檔以 §3 的 Given／When／Then 為規範性文字。
>
> **AT 底線形**＝把 AT ID 的連字號換成底線（`AT-962-3-2` 的底線形是 `AT_962_3_2`；`AT-962-13-E-3` 是 `AT_962_13_E_3`）；每個 AT 的測試函式（Java 為方法）名稱須含其底線形（`test_AT_962_3_2_…`、`AT_962_24_1_reasonSet…`、vitest 的 `it("AT_962_11_3 …")`）。每個 AC 內數字序與 E 序各不超過 9。**同一 AT 的子情境**以參數化或 `subTest` 實作並保留 AT 底線形，任一子情境失敗時訊息須指出是哪個情境。**AT 內不引用其他 AT 的 ID 作為執行條件**（本檔 AT 文字中的「同 AT-962-x」「見 AT-962-x」僅為讀者導引，不是測試相依；只有 §1、§6 的表格以 AT ID 作為映射）。
>
> **不得新增 skip、xfail、`it.skip`、`describe.skip`**，唯一例外是下列兩類**有名稱的環境缺件**，且必須以固定字首標示：(a) 框架對拍、真 CLI 與暫存 FSM 實跑缺 `SDD_ROOT`：`pytest.skip("TOOL-ABSENCE: SDD_ROOT 不存在")`；(b) 需要真 PostgreSQL 的 Bridge AT 缺 `BRIDGE_TEST_DSN`：沿 `tests/test_db_integration.py` 體例 `@pytest.mark.db` 加 `skipif`，reason 以 `TOOL-ABSENCE: BRIDGE_TEST_DSN` 起頭；另允許 (c) 平台缺件（無權建立符號連結或 junction）以 `TOOL-ABSENCE: symlink` 標示該子情境。三類在一般開發跑可以存在，但**SCG-4 與 RTM 證據必須在 `SDD_ROOT` 與 `BRIDGE_TEST_DSN` 皆在場下跑到 0 skipped**；以 skip 充當通過一律不接受。git 或 loopback 埠缺席視為環境壞、直接失敗。
>
> **判定指令的形態**（各 AT 末行列「引數部分」；cwd 如下，PowerShell 不用裸 cd、讀 rc 先存變數再讀）：Bridge（pytest；根 `.venv` 已啟用）`python -m pytest tests/<檔> -k <AT 底線形> -q`，DB 型加 `BRIDGE_TEST_DSN`；backend（Gradle；整合測試需 Docker）`gradlew test --tests "<類別全名>.<AT 底線形>*"`；frontend `npx vitest run <檔> -t <AT 底線形>`，E2E 為 `npx playwright test <檔> -g <AT 底線形>`（Docker 全棧用 `tests/e2e/docker.config.ts`）。

```powershell
Push-Location AgentConsole\engine-bridge; $env:BRIDGE_TEST_DSN='<YOUR_TEST_DSN>'; python -m pytest tests/test_research_inner_gates.py -k AT_962_3_1 -q; $rc_py = $LASTEXITCODE; Pop-Location
Push-Location AgentConsole\backend; .\gradlew.bat test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_2*"; $rc_jv = $LASTEXITCODE; Pop-Location
Push-Location AgentConsole\frontend; npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_3; $rc_ts = $LASTEXITCODE; Pop-Location
"pytest rc=$rc_py gradle rc=$rc_jv vitest rc=$rc_ts"
```

```bash
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && BRIDGE_TEST_DSN='<YOUR_TEST_DSN>' python -m pytest tests/test_research_inner_gates.py -k AT_962_3_1 -q; echo "pytest rc=$?")
(cd AgentConsole/backend && ./gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_2*"; echo "gradle rc=$?")
(cd AgentConsole/frontend && npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_3; echo "vitest rc=$?")
```

> **斷言簡寫與夾具名**（本檔各 AT 共用；實作與設施細節見 §5）：**Bridge 側**——`RDB`＝`make_research_db()`（套 `V1`～`V21` 真檔，測後 DROP）；`LB`＝活 Bridge（沿 `tests/conftest.py::make_bridge`）；`H`＝標頭 `X-Bridge-Token`；`TMPFSM`＝暫存 FSM 狀態目錄；假 gh 與拋棄式 git 見 §5.2。**backend 側**——`AbstractIntegrationTest`、`AbstractApiIT`（Testcontainers PG18）；迷你 Bridge＝`MiniResearch`／`MiniResearchController`；`viewer()`、`operator()`、`admin()` 憑證沿既有 `ApiClient`。**frontend 側**——`Providers` 與 `stubApi`；假 `EventSource` 與假計時器；測試 id 以 `data-testid` 取元素。**E2E**——Docker 全棧只跑 mock claude（nginx 80 埠、`E2E_ROOT` 短路徑、並行各自 `--output`）；mock spec 以 `mockApi.ts` 體例。

---
## 3. AT 完整清單與 Given／When／Then

> 每個 AT 一條：`AT 編號（測試框架｜測試檔｜類型｜對應 PRD AC）描述`，其下為 Given、When、Then 與判定指令。AC 層級的 Given／When／Then 見 §1.1。**Then 欄中的程式碼字面值一律用反引號；本檔所有數值（上限、字元數、逾時）取自 PRD、ADR、契約與主控裁決，為「初值（未校準）」者實作時亦以常數登記並以測試釘住。**

### 3.1 Bridge（pytest；可走徑①委派迴圈，亦可徑②自跑）

- **AT-962-1-8**（pytest｜`test_research_deliver_router.py`｜Integration｜AC-R2P-02-7）Bridge 的拋棄式資料庫夾具套到 V21，且 Bridge 兩個 INSERT 帶新欄位。
  - Given `research_pg_support.py` 的 `LAST_VERSION` 改 21；`BRIDGE_TEST_DSN`
  - When `make_research_db()`；經 `gate.decision` op 寫 SCG6 決定並帶 details；經 `scr.open` op 帶 evidence_url；省略兩者再寫一次
  - Then `migration_files()` 依數值序讀到 21 個真檔、不另抄 DDL；SCG6 列的 details 為傳入物件；省略時 details 為空物件、evidence_url 為 NULL；P1 既有 AT 不需改
  - 判定：python -m pytest tests/test_research_deliver_router.py -k AT_962_1_8 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-2-1**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-20-3）gitops 白名單新增 git 形態：tag --list、tag -a、push origin <tag>、ls-remote --tags origin、remote get-url origin、rev-parse --verify refs/tags。
  - Given `research/gitops.py` 的 `parse_git` 與固定 cwd 夾具
  - When 餵入 `[tag, --list, v1.2.3]`、`[tag, -a, v1.2.3, -m, <模板訊息>]`、`[push, origin, v1.2.3]`、`[ls-remote, --tags, origin, v1.2.3]`、`[remote, get-url, origin]`、`[rev-parse, --verify, refs/tags/v1.2.3]`
  - Then 六者皆通過驗證並回 argv 陣列；`test_research_gitops.py:113` 的『`tag -a` 為拒』改為正控、`pr create` 與 `release create` 兩項保留為拒（§4 第 14 列）
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_962_2_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-2-2**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-20-4）gitops 白名單新增 gh 形態：pr create 與 pr list；其餘 gh 子命令仍拒。
  - Given `parse_gh`
  - When 餵入 `[pr, create, --title, T, --body, B, --base, main, --head, feature/x]`、`[pr, list, --head, feature/x, --json, url]`，以及 `[pr, merge]`、`[pr, close]`、`[release, create, v1]`、`[repo, delete]`、`[pr, create]`（缺旗標）、旗標順序顛倒
  - Then 前兩者通過；其餘一律 `GitopsDenied` 且在 spawn 之前；缺旗標與順序變體被拒（只認固定旗標序）
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_962_2_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-2-3**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-20-3）tag 訊息模板正規式：`release: <semver>（RP-NNNN，追溯快照 sha256 <12 碼小寫十六進位>）`；既有 commit 模板不退步。
  - Given `_MESSAGE_RES` 新增一條
  - When 餵入合法訊息；缺 RP 號、RP 號 3 位、sha 11 碼、sha 13 碼、sha 含大寫、訊息含換行、尾隨空白、全形括號換半形、semver 不合；再餵既有 commit 模板
  - Then 合法者通過（RP 號 4 位以上）；其餘皆被拒；既有 commit 與 tag 以外模板仍通過；正規式以 `fullmatch` 判定
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_962_2_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-2-4**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-20-3）valid_semver 常數邊界：官方 semver 2.0 的保守子集，長度上限 64。
  - Given `valid_semver(name)` 純函式
  - When 餵 `1.2.3`、`v1.2.3`、`1.2.3-rc.1`、`1.2.3+b.5`、`1.2.3-rc.1+b.5`、`0.0.0`、64 字元合法 tag、65 字元；`1.2`、`01.2.3`、`1.2.3.4`、`v`、空字串、`-x`、`1.2.3 `、`1.2.3;x`、`../1.2.3`、`1.2.3\n`
  - Then 合法者與 64 字元通過；65 字元與其餘皆被拒；結果與 console-api 的 semver 正規式（AT-962-19-3）同一份常數字面（兩端正規式字串逐字相等，由本 AT 讀契約常數檔比對）
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_962_2_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-2-5**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-20-3）push origin <tag> 與既有 push -u origin <ref> 分開比對，不放寬 -u 形態。
  - Given `parse_git`
  - When 餵 `[push, -u, origin, feature/x]`（既有）、`[push, origin, v1.2.3]`（新）、`[push, origin, feature/x]`、`[push, origin, refs/heads/x]`、`[push, --tags]`、`[push, origin, +v1.2.3]`、`[push, origin, :v1.2.3]`、`[push, -f, origin, v1.2.3]`
  - Then 只有前兩者通過；`push origin <非 semver>` 被拒；其餘（含強推、刪除形態、`--tags`）一律被拒
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_962_2_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-2-6**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-20-3、AC-R2P-20-4）gh 與 git 呼叫的環境與 token 隔離沿 P1 不變：GH_TOKEN 只進 gh，不進 argv 與 git。
  - Given `child_env` 與假 gh 夾具（`FAKE_GH_MODE=leak`）；假 token `ghp_FAKE_R2P2_TOKEN_000000000000000000`
  - When 以 token 呼叫 `pr create`；另以 git 子行程呼叫 `tag -a`
  - Then argv 與回傳摘要不含 token 值；git 子行程環境無 GH_TOKEN；`leak` 模式下 gh 把 token 印到 stdout 與 stderr，回傳的 tail 已被 `redact` 遮蔽；環境白名單鍵集合與 P1 相同
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_962_2_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-2-E-1**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-20-3、AC-R2P-20-4）仍禁形態負控：--force、push --tags、tag -d、tag -f、gh release create、gh pr merge、任何刪除形態，在 spawn 之前拒絕。
  - Given `parse_git`／`parse_gh` 與 spawn 計數器（假 `Popen`）
  - When 逐一餵 `[push, --force, origin, v1]`、`[push, origin, v1, --force]`、`[push, --tags]`、`[tag, -d, v1]`、`[tag, -f, v1]`、`[tag, -a, v1]`（缺 -m）、`[branch, -D, x]`、`[release, create, v1]`、`[pr, merge, 1]`、`[pr, close, 1]`
  - Then 全數 `GitopsDenied`；spawn 計數為 0；`GitopsDenied` 訊息不回顯整條 argv 中的機密
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_962_2_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-2-E-2**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-20-3）選項注入負控：tag 名與 branch 名以 `-` 起頭、含空白、含控制字元一律在 spawn 前被拒。
  - Given `parse_git`／`parse_gh`
  - When tag 名為 `-v1.2.3`、`--exec=x`、`v1 2`、`v1\t2`、`v1\n2`；`pr create --head` 為 `-x`、`a b`、`a..b`
  - Then 皆被拒；argv 為陣列且 `shell=False`（沿 P1 AST 鎖）
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_962_2_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-2-E-3**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-20-3）EXEC_MODULES 不變：git 與 gh 的 argv 字面只住 gitops.py；新模組不含 git／gh 字面。
  - Given `tests/test_research_capability.py` 的實樹掃描
  - When 掃描 `delivery.py`、`healing.py`、`inner_gates.py`、`routers/research_deliver.py` 的字串常數
  - Then 四檔零個 git 或 gh argv 字面；`EXEC_MODULES` 集合與 P1 逐字相同
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_962_2_E_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-1**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）SCG-4 登錄：現態 IMPLEMENTATION 先 transition 再 gate PASS，序列與 decision_trace 和人工等價序列相同。
  - Given 暫存狀態目錄（`TMPFSM`）的內環鍵現態 IMPLEMENTATION；SUCCEEDED 分流；RTM 夾具 fully_covered；`LB`
  - When POST `:gates`，`gate=PR_REVIEW`、`result=PASS`、`reviewer_independent=true`
  - Then FSM 呼叫序列為 `transition --to PR_REVIEW`（`--trigger research_bridge`、reason 含 `SCG-4 registration; research=<rp_no>`）→ `gate --gate PR_REVIEW --result PASS`；`next_state` 為 RTM_VERIFY；decision_trace 與人工指令序列逐項相同；回應 200 帶 `gate_decision_id`、`fsm_state_before`、`next_state`、`escalated=false`、`flow`
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-2**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）PR_REVIEW 現態矩陣：EXECUTION_EVALUATION、ADVERSARIAL_EVALUATION 先 transition；現態已是 PR_REVIEW 略過 transition。
  - Given `TMPFSM` 逐一置於四個現態（子情境）
  - When 各 POST 一次 `gate=PR_REVIEW`、`result=PASS`
  - Then 三個現態各有一個 transition 加一個 gate；現態 PR_REVIEW 只有一個 gate、零 transition；每個子情境的失敗訊息指出是哪個現態
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-3**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）PR_REVIEW FAIL 回 IMPLEMENTATION 並耗預算；連續 FAIL 到限額時 next_state 以引擎回傳為準（含 ESCALATION），Bridge 不自算。
  - Given `TMPFSM`；RETRY_LIMITS 常數取自 `transition_rules.py:267-274`（PR_REVIEW 為 5）
  - When 連續登錄 PR_REVIEW FAIL（理由各異）至限額邊界：第 限額−1 次、第 限額 次、第 限額+1 次
  - Then 未達限額每次 next_state 為 IMPLEMENTATION；到達限額的那一次 next_state 以引擎回傳字面為準（若為 ESCALATION 開頭則 `escalated=true`、游標 `flow_status=ESCALATED`、發 `research.alert{kind:ESCALATED}`）；測試以回傳值斷言、不內嵌第二份數字
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-4**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）SCG-5 登錄：RTM_VERIFY PASS 到 RELEASE_READY、FAIL 回 IMPLEMENTATION（預算 2）；現態必須是 RTM_VERIFY。
  - Given `TMPFSM` 現態 RTM_VERIFY；RTM 夾具 ac.pct 為 100
  - When POST `gate=RTM_VERIFY`、PASS；再重置後連續 FAIL 至限額邊界
  - Then PASS 後 `next_state` 為 RELEASE_READY，序列只有一個 `gate`、零 transition；FAIL 序列與預算邊界同 AT-962-3-3 的斷言法；`gate` 呼叫的 `--gate` 為字面 `RTM_VERIFY`
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-5**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）RELEASE_READY FAIL（雲端 CI 紅）：理由必填，回 IMPLEMENTATION，登錄為 gate 值 SCG6 並記 details.ci_red。
  - Given `TMPFSM` 現態 RELEASE_READY（依 D-138 取代 IFACE §0 對照第 2 項：不用 SCG5 加理由前綴）
  - When POST `gate=RELEASE_READY`、`result=FAIL`、reason 為一句；再連續 FAIL 至限額邊界
  - Then FSM 序列為單一 `gate --gate RELEASE_READY --result FAIL --reason <理由>`；`next_state` 為 IMPLEMENTATION；`research_gate_decisions` 新增一列 gate 為 `SCG6`、decision 為 `REJECTED`、details 的 `ci_red` 為 true；reason 欄不含任何方括號前綴
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-6**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6、AC-R2P-02-5）決定入庫映射：PR_REVIEW→SCG4、RTM_VERIFY→SCG5、RELEASE_READY→SCG6；PASS→APPROVED、FAIL→REJECTED；details 承載獨立性聲明與報告參照。
  - Given `RDB`（V21）；三種 gate 各登錄 PASS 與 FAIL（RELEASE_READY 只 FAIL）
  - When 逐一登錄後查 `research_gate_decisions` 與 `research_events`
  - Then gate 值與 decision 值如映射；PR_REVIEW 列 details 為 `{reviewer_independent:true, review_report_ref:<值或 null>}`；`fsm_project` 為內環鍵、`fsm_state_after` 為回傳 `next_state`、`decided_by` 為 approver、`audit_trace_id` 為 `trace_id_var`；reason 欄只含人填理由（依 D-138 取代 IFACE §0 第 3 項）；`research.gate` 事件 payload 鍵集合與 P0 相同
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-7**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）零信任 RTM 重驗：PR_REVIEW 要求報告 fully_covered、RTM_VERIFY 要求 ac.pct 為 100，不信 console-api 傳入的判斷。
  - Given RTM 夾具：fully_covered 為假；ac.pct 為 99.99、100；報告不存在（`rtm_not_found`）
  - When 各 POST 一次對應 gate
  - Then 不足者 409 `fsm_state_conflict`、`details.unmet` 含 `rtm_below_100`；報告不存在同；零 FSM 寫入、零 DB 列；100 與 fully_covered 為真時通過（99.99 不得四捨五入通過）
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-8**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）冪等：同一 decision_id 重送不重複 FSM 寫入與 DB 列。
  - Given `LB`；一次成功的 `:gates`
  - When 以同一 decision_id 與同一本文再 POST 一次
  - Then 第二次 200 並回與第一次相同的 `gate_decision_id`；FSM 呼叫計數與 `research_gate_decisions` 列數不增
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_8 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-9**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）與 SCR 共存：SCR MINOR 序列內部的 gate PR_REVIEW FAIL 不寫 SCG4 列；OPEN SCR 期間 `:gates` 回 scr_open。
  - Given 一個 OPEN 的 MINOR SCR；另一個走完 `apply_minor` 的專案
  - When 對前者 POST `:gates`；對後者查 `research_gate_decisions`
  - Then 前者 409 `scr_open`、零 FSM 寫入；後者的 SCR 序列雖呼叫 `gate PR_REVIEW FAIL` 但 `research_gate_decisions` 無 SCG4 列（D-138 Q-16）
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_9 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-E-1**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）現態不合負控：矩陣外的每個 FSM 狀態一律 409 且零 FSM 寫入、零 DB 列。
  - Given `TMPFSM` 遍歷矩陣外全部狀態（含 INIT、SPEC_DRAFTING、SPEC_FROZEN、RELEASE、各 ESCALATION*）；另 gate=RTM_VERIFY 而現態為 IMPLEMENTATION、gate=PR_REVIEW 而現態為 RTM_VERIFY
  - When 各 POST 一次
  - Then 全數 409 `fsm_state_conflict`、`details.current_state` 為現態字面；FSM 呼叫計數為 0；決定列與事件為 0
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-E-2**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）無 SUCCEEDED 分流時一律 409，details.cause 為 route_not_succeeded。
  - Given 研究專案無 SUCCEEDED 的路由列（PENDING、FAILED、COMPENSATED 各一種）
  - When POST `:gates`
  - Then 409 `fsm_state_conflict`、`details.cause` 為 `route_not_succeeded`；零寫入
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-E-3**（pytest｜`test_research_inner_gates.py`｜Unit｜AC-R2P-15-6）組合與欄位邊界：(RELEASE_READY, PASS) 一律 422；FAIL 理由必填；reason 500／501；review_report_ref 300／301。
  - Given `inner_gates.validate_request` 純函式
  - When 餵 `(RELEASE_READY, PASS)`；FAIL 配空理由與 500、501 字元理由；PASS 配空理由；review_report_ref 為 300、301 字元；未知 gate、未知 result
  - Then `(RELEASE_READY, PASS)` 為 422 `invalid_request`（`violations[{field:result, rule:release_pass_via_tag}]`）；FAIL 空理由與 501 字元、報告參照 301 字元、未知值皆 422 並逐欄列出；500 與 300 字元通過；PASS 空理由通過
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_E_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-E-4**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）approver 不合（空、含控制字元、超長）時 422，且不呼叫任何 FSM 動詞。
  - Given `sdd_cli.validate_research_approver`
  - When approver 為空、`a\nb`、101 字元、合法 JWT subject
  - Then 前三者 422 且 FSM 呼叫計數為 0；合法者通過
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_E_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-E-5**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6）FSM 在前、DB 在後：DB 阻塞時 `:gates` 回 503 db_blocked，決定列留在 outbox，恢復後重放補寫且游標重衍生。
  - Given `RDB` 注入 DB 阻塞；`LB`
  - When POST `:gates` 成功路徑，DB 於寫決定列時阻塞，之後恢復
  - Then 回應單一值：503 `db_blocked`（P0 `DbBlocked`，`outbox.py:263,:285`；不回 200）；FSM 呼叫計數為 1；阻塞期間 DB 無決定列、outbox 有恰 1 筆 pending 的 `gate.decision`；恢復並重放後 `research_gate_decisions` 恰 1 列；游標由 `orchestrator.project_state` 重衍生；不重複呼叫 FSM（⚖P2-19）
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_E_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-3-E-6**（pytest｜`test_research_inner_gates.py`｜Integration｜AC-R2P-15-6、AC-R2P-16-5）`:gates` 前置漂移負控：三種 gate 遇凍結 digest 不符一律 422 digest_mismatch，零寫入、零 FSM 呼叫。
  - Given `TMPFSM` 現態合法（IMPLEMENTATION、RTM_VERIFY、RELEASE_READY 各一）；凍結檔被改；RTM 夾具滿足；另備現態不合且漂移的夾具
  - When 各 POST `gate=PR_REVIEW`、`RTM_VERIFY`、`RELEASE_READY`（FAIL）
  - Then 皆 422 `digest_mismatch`、`details.drift[]` 逐項含 `path`、`expected_sha256`、`actual_sha256`；FSM 呼叫 0、`research_gate_decisions` 與 `research_events` 零新增；現態不合且漂移者回 422（漂移比對先於現態矩陣）；凍結檔位元組不被改動
  - 判定：python -m pytest tests/test_research_inner_gates.py -k AT_962_3_E_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-5-1**（pytest｜`test_research_ast_locks.py`｜Unit｜AC-R2P-15-6）inner_gates.py 的三個 gate 呼叫皆為字面常數，各在一個 if 分支；gate_needs_guard 對它們為假。
  - Given `check_source` 整樹掃描（C1～C7）；`inner_gates.py` 實檔
  - When 取所有 `fsm_ops.gate(...)` 呼叫節點
  - Then 恰三個呼叫、`gate=` 分別為字面 `"PR_REVIEW"`、`"RTM_VERIFY"`、`"RELEASE_READY"`；不含變數分派；整樹掃描零違規
  - 判定：python -m pytest tests/test_research_ast_locks.py -k AT_962_5_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-5-2**（pytest｜`test_research_ast_locks.py`｜Unit｜AC-R2P-15-6）inner_gates 專屬規則：只呼叫 fsm_ops.gate 與 fsm_ops.transition，不呼叫 spec_frozen、approve_baseline、spec_refreeze、create_key。
  - Given 新增專屬 AST 規則與紅綠自證夾具
  - When 掃 `inner_gates.py`；對夾具原始碼（含 `fsm_ops.spec_frozen(...)`、變數 gate）掃描
  - Then 實檔零違規；夾具被判違規（紅）；合法夾具通過（綠）；本規則在 `test_research_ast_locks.py`（共享單點，歸 BR-P2）
  - 判定：python -m pytest tests/test_research_ast_locks.py -k AT_962_5_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-5-3**（pytest｜`test_research_ast_locks.py`｜Unit｜AC-R2P-20-3）delivery.py 與 healing.py 列入 _NO_FSM_WRITE_MODULES：兩檔零 FSM 寫入；RELEASE 的 transition 住 inner_gates。
  - Given `_NO_FSM_WRITE_MODULES` 加兩檔（§4 第 13 列；依 ⚖P2-1 取代 IFACE §6.2 步驟 8 的『delivery 直接呼叫 transition』）
  - When 掃兩檔的 FSM 動詞與 `fsm_ops` 匯入
  - Then 兩檔零 `transition`、`gate`、`spec_frozen` 呼叫與零 `tools.fsm_runtime` 匯入；`inner_gates.release_transition` 內的 `transition` 的 `--to` 為字面 `RELEASE`
  - 判定：python -m pytest tests/test_research_ast_locks.py -k AT_962_5_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-5-4**（pytest｜`test_research_ast_locks.py`｜Unit｜AC-R2P-20-3）EXEC_MODULES 不變且新模組不自起子行程：spawners 為 EXEC_MODULES 的子集。
  - Given 整樹 AST 掃描
  - When 找出所有 `subprocess`／`Popen`／`os.system` 使用者
  - Then 集合 ⊆ `EXEC_MODULES`（六檔，與 P1 相同）；`delivery.py`、`healing.py`、`inner_gates.py`、`routers/research_deliver.py` 皆不在 spawners（`:340` 不紅）
  - 判定：python -m pytest tests/test_research_ast_locks.py -k AT_962_5_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-5-5**（pytest｜`test_research_capability.py`｜Unit｜AC-R2P-20-3）能力登記：四個新模組先登記再掃描，實樹與登記表一對一。
  - Given `CAPABILITY` 加 `research/inner_gates.py`、`research/delivery.py`、`research/healing.py`、`routers/research_deliver.py`（類別以門判定：經 `fsm_ops` 或 `gitops` 者為 exec，只讀 DB 與檔者為 ro／rw；登記值本 AT 不預設，取檔頭自述規則）
  - When 跑 `:267` 的實樹對登記表檢查
  - Then 實樹檔與登記表一對一；`vcs` 類別仍只有 `gitops.py`；`EXEC_DOORS` 集合不變
  - 判定：python -m pytest tests/test_research_capability.py -k AT_962_5_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-5-6**（pytest｜`test_sdd_cli.py`｜Unit｜AC-R2P-15-6）動詞表不變：RESEARCH_VERBS 五個、resume-from-escalation 不入；transition 目標含 PR_REVIEW 與 RELEASE。
  - Given `sdd_cli.RESEARCH_VERBS`、`INNER_TRANSITION_TARGETS`、`INNER_GATES`
  - When 斷言集合與 `git diff` 對 `app/sdd_cli.py`
  - Then 動詞集合與 P1 相同；`INNER_TRANSITION_TARGETS` 含 PR_REVIEW 與 RELEASE；`INNER_GATES` 含三個內環閘；`sdd_cli.py` 零 diff（`test_sdd_cli.py:390` 不紅）
  - 判定：python -m pytest tests/test_sdd_cli.py -k AT_962_5_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-5-7**（pytest｜`test_research_db.py`｜Unit｜AC-R2P-20-3）P2_OPS 登記 delivery.record；OPS、METHOD_KINDS、WRITE_METHODS 不動，一一對應鎖仍綠。
  - Given `db.py` 新增 `P2_OPS`；`db.apply` 查找鏈 `OPS or ROUTE_OPS or P1_OPS or P2_OPS`
  - When 斷言三個既有表與新表
  - Then `P2_OPS` 恰一個鍵 `delivery.record`；`set(METHOD_KINDS.values()) == set(OPS)` 仍成立（`test_research_db.py:158`）；`WRITE_METHODS` 與 P1 逐字相同；`gate.decision` 仍由 `OPS` 提供
  - 判定：python -m pytest tests/test_research_db.py -k AT_962_5_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-5-E-1**（pytest｜`test_research_ast_locks.py`｜Unit｜AC-R2P-15-6）紅綠自證負控：變數 gate、delivery 內 spec_frozen、healing 內 subprocess 的夾具原始碼各被判違規。
  - Given 三份夾具原始碼字串
  - When 各餵 `check_source`
  - Then 三者各產生至少一個違規；去掉違規後的對照夾具零違規（鎖能咬人）
  - 判定：python -m pytest tests/test_research_ast_locks.py -k AT_962_5_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-5-E-2**（pytest｜`test_research_ast_locks.py`｜Unit｜AC-R2P-15-6）游標更新函式同時 append_event：delivery.record 與 gate.decision 內的游標 UPDATE 同函式含 append_event。
  - Given `test_research_ast_locks.py:416` 規則
  - When 掃 `db.py` 的 `_op_delivery_record` 與既有函式
  - Then 每個含游標 UPDATE 的函式同時呼叫 `append_event`；新函式未違反
  - 判定：python -m pytest tests/test_research_ast_locks.py -k AT_962_5_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-1**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-1）視圖列與日誌行逐筆一致：key 為 (run_id, step_number)，欄位集合固定，view_rows 的 key 集合等於 log 的 key 集合。
  - Given `RDB`（V21）；一個研究專案綁 console 專案，三個 run 的 execution_steps 含 RETRYING 與 FAILED 共 N 列；`LB`
  - When POST `:healing-sync`；讀 `03_execution/healing_history.log`
  - Then log 為 JSON Lines、每行鍵為 `run_id`、`task_id`、`step_number`、`attempt`、`status`、`excerpt`、`occurred_at`；key 集合與視圖列 key 集合相等；回應 `view_rows` 與 `log_lines` 為 N；`appended` 為 N
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_6_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-2**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-1）冪等：重送不重複，只追加缺的行。
  - Given 已同步過一次；再新增 2 列視圖資料
  - When 再 POST 兩次
  - Then 第一次 `appended` 為 2、第二次為 0；log 檔位元組在第二次前後相同；既有行不被改寫
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_6_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-3**（pytest｜`test_research_healing.py`｜Unit｜AC-R2P-16-1）attempt 導出：同 (run_id, task_id) 內依 step_number 升冪的第 n 筆。
  - Given 夾具：同 task 的 step 3、5、9 與另一 task 的 step 4
  - When 呼叫導出函式
  - Then 第一個 task 的 attempt 依序為 1、2、3；另一 task 為 1；跨 run 不累加
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_6_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-4**（pytest｜`test_research_healing.py`｜Unit｜AC-R2P-16-1、AC-R2P-16-4）excerpt 取遮蔽後的尾端 300 字元；以字元計不以位元組計；邊界 299、300、301。
  - Given error_message 長度 299、300、301 的純文字與含多位元組字元的版本
  - When 呼叫 `excerpt()`
  - Then 299 與 300 原樣；301 取最後 300 字元；多位元組字元不被切半；先遮蔽再截尾（見 AT-962-7-E-1）
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_6_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-5**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-1）日誌上限 HEALING_LOG_MAX_BYTES＝2097152：到達上限前正常追加，超過後不再追加、寫一次 truncated 行並發 HEALING_LOG_TRUNCATED。
  - Given 把常數以環境夾具調小為可測值（測試另一個斷言釘正式值 2097152）；檔大小邊界：差 1 位元組到上限、恰到上限、超過 1 位元組
  - When 連續 sync 至越界，再 sync 一次
  - Then 正式常數字面為 2097152；越界時檔尾恰有一行 `{"truncated":true}`、發一筆 `research.alert{kind:"HEALING_LOG_TRUNCATED"}`；再次 sync 不重複寫 truncated、不再追加；檔大小不超過上限加一行 truncated 的長度
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_6_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-6**（pytest｜`test_research_healing.py`｜Unit｜AC-R2P-16-1）寫檔經 fsutil.write_text_atomic，LF、UTF-8、ensure_ascii 為假，且不新增目錄項原語站點。
  - Given `healing.py` 原始碼與寫出的檔案位元組
  - When 掃 `os.replace`／`rename`／`move` 站點；檢查位元組
  - Then 站點淨增 0；檔案無 CR、為 UTF-8、中文不被轉成跳脫序列；`open`／`write_text` 皆帶 `encoding="utf-8"`
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_6_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-7**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-1）ResearchDb 唯一新增的方法是唯讀的 list_healing_attempts；沒有新寫入面。
  - Given `db.py`
  - When 比對 `WRITE_METHODS` 與公開方法；對 `list_healing_attempts` 在唯讀交易下執行
  - Then 公開寫入方法集合不變；該方法只執行 SELECT（SQL 字串掃描）；對視圖的 INSERT 被拒
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_6_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-8**（pytest｜`test_research_deliver_router.py`｜Integration｜AC-R2P-16-1）`:healing-sync` 為內部端點：檢查序、回應形狀與角色。
  - Given `LB`；寫入權杖 `H`
  - When POST 帶與不帶權杖；不存在專案；本文帶多餘欄位
  - Then 無權杖 401 或 403（沿 P0 行為字面）；不存在專案 404；回應鍵為 `view_rows`、`log_lines`、`appended`、`spec_change`；`requested_by` 以 `system` 記入事件；檢查序為權杖→資料庫→專案存在→本文→前置
  - 判定：python -m pytest tests/test_research_deliver_router.py -k AT_962_6_8 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-E-1**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-1）無視圖列或專案未綁 console 專案：200 無操作，不建空檔。
  - Given 兩種專案
  - When POST `:healing-sync`
  - Then `appended` 為 0、`view_rows` 為 0；`healing_history.log` 不存在；不發事件
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_6_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-E-2**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-1）並行 sync 持專案鎖序列化，不產生重複行。
  - Given 兩個執行緒同時送 `:healing-sync`（假時鐘）
  - When 並行呼叫
  - Then log 的 key 無重複；兩個回應的 `appended` 加總等於缺的行數
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_6_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-6-E-3**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-1）資料庫阻塞時 503 db_blocked，且不寫檔。
  - Given `RDB` 注入阻塞
  - When POST `:healing-sync`
  - Then 503 `db_blocked`；log 檔位元組不變
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_6_E_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-7-1**（pytest｜`test_research_healing.py`｜Unit｜AC-R2P-16-4）Bridge 遮蔽對拍夾具逐筆：疊用 redact_secrets 與 gitops.redact。
  - Given `tests/fixtures/research/healing_redaction_cases.json`（`[{input, expected}]`，BR-P2 建、API-P2 只讀）
  - When 逐筆餵 `healing.mask()`
  - Then 每筆輸出等於 expected；夾具至少涵蓋 GitHub token（`ghp_`、`github_pat_`）、`sk-` 金鑰、Bearer、AWS key、`password=`；每類別至少一筆
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_7_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-7-2**（pytest｜`test_research_healing.py`｜Unit｜AC-R2P-16-4）研究面恆遮：不讀 REDACT_SECRETS_IN_LOGS，環境關掉開關仍遮。
  - Given 環境變數 `REDACT_SECRETS_IN_LOGS` 設 `false`、`0`、空
  - When 呼叫 `healing.mask()`
  - Then 輸出仍遮蔽；`healing.py` 原始碼不含該環境變數名
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_7_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-7-4**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-4）log 檔逐字掃描：假 token 零明文。
  - Given execution_steps.error_message 含夾具假 token；`ghp_FAKE_R2P2_TOKEN_000000000000000000`
  - When sync 後讀 log 檔位元組
  - Then 全檔無任何假 token 字面；視圖與 `execution_steps` 內容未被改動（逐位比對）
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_7_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-7-E-1**（pytest｜`test_research_healing.py`｜Unit｜AC-R2P-16-4）先遮蔽再截尾：token 跨 300 字元邊界時不留半截 token。
  - Given error_message 把 token 起點放在第 290 字元與第 301 字元之前
  - When 呼叫 `excerpt()`
  - Then 輸出無 token 片段（遮蔽標記完整或整段略去）；Java 端 `HealingExcerptMasker` 同夾具同結果
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_7_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-7-E-2**（pytest｜`test_research_healing.py`｜Unit｜AC-R2P-16-4）誤殺負控：非機密長字串與雜湊不被遮蔽。
  - Given 夾具中標記為 `keep` 的筆（40 位 commit sha、UUID、長 base64 無前綴字串、`password` 一詞單獨出現）
  - When 餵遮蔽函式
  - Then 輸出等於輸入；兩端相同
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_7_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-8-1**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-5）偵測：改動一個已凍結檔，healing.detect_spec_change 回出漂移，且 Bridge 不改該檔。
  - Given 暫存目標專案；內環 FSM `frozen_stages` 含 Stage-1 與 Stage-2 的 spec_doc_digests；手動改一個凍結檔
  - When POST `:healing-sync`
  - Then 回應 `spec_change` 含該路徑、`expected`、`actual`；凍結檔位元組在呼叫前後與『手動改後』相同（Bridge 不還原、不改寫）
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_8_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-8-2**（pytest｜`test_research_healing.py`｜Unit｜AC-R2P-16-5）未改動不誤報；凍結階段取聯集；digest 逐檔重算。
  - Given 未改動樹；Stage-1 與 Stage-2 digests 有重疊與不重疊路徑
  - When 呼叫 `detect_spec_change`
  - Then 空清單；聯集覆蓋所有階段路徑；重疊路徑只比一次
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_8_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-8-3**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-5）告警：追加 log 一行 spec_change、發 research.alert kind SPEC_CHANGE_FORBIDDEN，同一漂移不重複告警。
  - Given 同 AT-962-8-1 的漂移；`LB`
  - When 連續 sync 兩次
  - Then log 有恰一行 `{"spec_change":true,"paths":[…],"expected":…,"actual":…}`；事件恰一筆且 detail 為 JSON；第二次無新增
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_8_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-8-4**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-5）偵測點三處：`:healing-sync` 只記錄與告警；`:gates` 與 `:tag` 前置比對不符即 422 digest_mismatch（阻擋，D-142）。
  - Given 以 spy 包 `detect_spec_change`；凍結檔被改（同 AT-962-8-1）；其餘前置皆成立；另備未漂移對照
  - When 各呼叫 `:healing-sync`、`:gates`（三種 gate 各一）、`:tag` 一次
  - Then 三處各呼叫偵測一次；`:healing-sync` 為 200 並含 `spec_change`；`:gates` 與 `:tag` 為 422 `digest_mismatch`、`details.drift[]` 每項含 `path`、`expected_sha256`、`actual_sha256`；零 DB 列、零 FSM 呼叫、零 gitops 呼叫；未漂移對照照常成功
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_8_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-8-E-1**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-5）不還原負控：偵測後 Bridge 不呼叫任何破壞性 git 形態。
  - Given gitops 呼叫記錄
  - When sync 一次
  - Then gitops 記錄無 `checkout --`、`restore`、`reset`、`clean`、`stash`；凍結檔仍為被改後內容
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_8_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-8-E-2**（pytest｜`test_research_healing.py`｜Unit｜AC-R2P-16-5）凍結檔被刪除亦為漂移，且不拋例外。
  - Given 刪除一個凍結檔
  - When 呼叫 `detect_spec_change`
  - Then 回出該路徑、`actual` 為 `missing`；無例外
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_8_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-8-E-3**（pytest｜`test_research_healing.py`｜Integration｜AC-R2P-16-5）劃界負控：回應與事件不聲稱『已拒絕補丁』。「被拒」屬框架 hooks，由 V-S1 承擔。
  - Given 同 AT-962-8-1
  - When 檢查回應鍵與事件 payload 鍵
  - Then 沒有 `rejected`、`blocked`、`denied` 類鍵；事件 kind 僅為 `SPEC_CHANGE_FORBIDDEN`（偵測語意）
  - 判定：python -m pytest tests/test_research_healing.py -k AT_962_8_E_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-15-7**（pytest｜`test_research_scr.py`｜Integration｜AC-R2P-19-1、AC-R2P-19-5）Bridge `:scr` 接受 evidence_url 並寫入 research_scr.evidence_url。
  - Given `RDB`（V21）；`LB`
  - When POST `:scr` 帶合法、缺、非 https、501 字元的 evidence_url
  - Then 合法者列的 evidence_url 等於輸入；缺者為 NULL；後二者 422 `violations` 規則為 `evidence_not_https`、`evidence_too_long`（本檔類推 ⚖P2-11）；`reason` 欄與輸入逐字相同；P1 的 SCR AT 零改動
  - 判定：python -m pytest tests/test_research_scr.py -k AT_962_15_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-15-8**（pytest｜`test_research_scr.py`｜Unit｜AC-R2P-19-1）scr.open op 的 INSERT 帶 evidence_url，欄位順序與參數一一對應。
  - Given `db.py` 的 `_op_scr_open` 與 SQL 常數（`db.py:1122`）
  - When 靜態檢查欄位清單與參數個數；實跑一次寫入
  - Then 欄位清單含 `evidence_url`；參數個數相符；寫入後讀回一致
  - 判定：python -m pytest tests/test_research_scr.py -k AT_962_15_8 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-17-1**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-1）build_traceability：列數等於凍結 PRD 的 AC 總數，一個 AC 一列，集合相等、無遺漏無多餘。
  - Given 凍結 PRD 夾具（N 個 AC）；`scr.parse_frozen_prd`；拆解與任務夾具
  - When 呼叫 `delivery.build_traceability`
  - Then rows 的 `ac` 集合等於 PRD 的 AC 集合（以集合相等斷言）；欄位為 `ac`、`userStory`、`gherkinSummary`、`unitStatus`、`e2eStatus`、`lastRunAt`、`source`；`totals.acTotal` 為 N
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_17_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-17-2**（pytest｜`test_research_delivery.py`｜Unit｜AC-R2P-20-1）gherkinSummary 每段不超過 120 字；邊界 120／121。
  - Given Given、When、Then 各段長度為 119、120、121 的 PRD 夾具
  - When 產生摘要
  - Then 每段至多 120 字（超過者截斷並以省略號結尾且總長仍不超過 120）；純文字、不含 Markdown 標記以外的 HTML
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_17_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-17-3**（pytest｜`test_research_delivery.py`｜Unit｜AC-R2P-20-1、AC-R2P-20-2）unitStatus 導出：覆蓋任務全 COMPLETED 為 PASS；任一 FAILED 或 ESCALATED 為 FAIL；其餘 NOT_RUN；無覆蓋任務為 NONE。
  - Given R8 covers_ac 與任務終態夾具各組合；僅有豁免的 AC
  - When 導出狀態與 lastRunAt、source
  - Then 如列；`lastRunAt` 為覆蓋任務 finished_at 最大值；`source` 含 `task:<taskId>` 與 `RTM-COVERAGE-<project>.yaml`；NONE 者標紅（依 D-138 Q-5 與 D-140 #7）
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_17_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-17-4**（pytest｜`test_research_delivery.py`｜Unit｜AC-R2P-20-1）e2eStatus：僅當存在 SCG5 的 APPROVED 決定且其後無 REJECTED 時為 PASS，否則 NOT_RUN（無逐 AC 的 E2E 機器來源，如實標示）。
  - Given 決定序列夾具：無、SCG5 APPROVED、APPROVED 後 REJECTED、只有 SCG4 APPROVED
  - When 導出 e2eStatus
  - Then 僅第二種為 PASS；其餘 NOT_RUN；不假裝逐 AC
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_17_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-17-5**（pytest｜`test_research_delivery.py`｜Unit｜AC-R2P-20-2）totals：未覆蓋＝unitStatus 不為 PASS 的列數；e2e 欄不計入；零測試不是通過。
  - Given 混合夾具
  - When 計算 totals
  - Then `uncovered` 等於 unitStatus 非 PASS 的列數；e2eStatus 為 NOT_RUN 不增加 uncovered；`covered 加 uncovered 等於 acTotal`
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_17_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-17-6**（pytest｜`test_research_deliver_router.py`｜Integration｜AC-R2P-20-1）`:traceability-preview` 零副作用：DB 與檔案前後相同。
  - Given `RDB`；工作區檔案雜湊
  - When POST `:traceability-preview` 三次
  - Then `research_*` 列數、事件數、檔案樹雜湊皆不變；回應含 `rows`、`totals`、`rtm`、`generatedAt`
  - 判定：python -m pytest tests/test_research_deliver_router.py -k AT_962_17_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-17-E-1**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-1）凍結 PRD 讀不到：409 fsm_state_conflict，unmet 含 prd_not_frozen，零寫入。
  - Given 尚未 Gate 0 凍結的專案
  - When POST `:traceability-preview`
  - Then 409；`details.unmet` 含 `prd_not_frozen`（本檔類推 ⚖P2-12）；零寫入
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_17_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-17-E-2**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-2）拆解缺席或 stale：全部 AC 的 unitStatus 為 NONE，不假設通過。
  - Given 無拆解；拆解標 STALE
  - When build_traceability
  - Then 所有列 NONE、`uncovered` 等於 acTotal
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_17_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-17-E-3**（pytest｜`test_research_delivery.py`｜Unit｜AC-R2P-20-1）AC 數邊界：N 為 1 與 250 時列數仍等於 N。
  - Given PRD 夾具 N＝1、250
  - When build_traceability
  - Then 列數等於 N；無分頁截斷
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_17_E_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-17-E-4**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3）零信任：`:tag` 內重算追溯表，不信任請求帶入的列。
  - Given 請求本文偽造一份全 PASS 的 rows；實際有 NONE 列
  - When POST `:tag`
  - Then 409（unmet 含 `rtm_below_100` 或未覆蓋）；零 git 副作用；回應未回顯偽造列
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_17_E_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-1**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3）Tag 正控序列：驗證、冪等探測、取 commit、tag -a、（push:true 且有 origin）push、寫快照檔、單交易入庫、transition RELEASE、對帳。
  - Given 暫存 git 專案（真 git，`$env:TEMP`）；`file://` 的 bare repo 當 origin；內環 FSM 現態 RELEASE_READY；追溯全 PASS；`LB`
  - When POST `:tag`：`tag_name=v1.2.3`、`push=true`
  - Then gitops 呼叫序列為 `tag --list`、`rev-parse --verify HEAD`、`tag -a`、`remote get-url origin`、`ls-remote --tags origin`、`push origin v1.2.3`；其後寫 `03_execution/traceability_matrix.json`；一個 DB 交易；FSM `transition --to RELEASE`；`reconcile_at_delivery` 一次；回應 201
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-2**（pytest｜`test_research_delivery.py`｜Unit｜AC-R2P-20-3）tag 訊息只取模板：release: <tag>（RP-NNNN，追溯快照 sha256 <前 12 碼>），使用者 message 不進 argv，只入 detail 並先遮蔽。
  - Given message 為一般文字與含假 token 文字
  - When 呼叫 `create_tag`，攔截 gitops argv
  - Then `-m` 後的參數恰為模板輸出；`research_deliveries.detail` 含遮蔽後使用者文字（至多 2000 字）；argv 中無使用者原文；`detail` 邊界 2000、2001 字元：2000 原樣、2001 於遮蔽後截為 2000
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-3**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3、AC-R2P-02-5）快照檔與 R11：traceability_matrix.json 鍵序固定、LF、不跳脫中文；其 sha256 等於 snapshot_sha256 欄；rtm_report_ref 為檔案相對路徑。
  - Given 成功建立 tag 後
  - When 讀檔與資料列
  - Then 檔含 `research_id`、`rp_no`、`prd_sha256`、`frozen_digests`、`generated_at` 與追溯輸出；sha256 與 `snapshot_sha256` 逐字相等；`rtm_report_ref` 為 `03_execution/traceability_matrix.json`（依 D-139 取代 IFACE §0 第 4 項的 `@sha256` 承載）
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-4**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3）單一 DB 交易：RELEASE_TAG 列與 research.delivery 事件同交易，欄位值固定。
  - Given 同 AT-962-18-1
  - When 查 `research_deliveries` 與 `research_events`
  - Then 列：`kind=RELEASE_TAG`、`ref` 為 tag 名、`commit_sha` 為 40 位小寫十六進位、`url` 為 NULL、`rtm_run_id` 為最新 run、`snapshot_sha256` 為 64 位小寫十六進位、`fsm_state_after` 為 `RELEASE_READY`（當時事實；表 append-only）、`status=CREATED`、`created_by` 為 approver；`research.delivery` 成功事件 payload 鍵集合恰為 `{kind, ref, status, digest, reason, failure_step}`（`digest` 為快照 sha256、`failure_step` 為 null）；兩者同一交易提交（D-144 F-10）
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-5**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3）FSM 與游標：transition --to RELEASE 序列與游標落點。
  - Given 暫存狀態目錄
  - When 成功路徑
  - Then FSM 呼叫為 `transition --to RELEASE --reason "release tag v1.2.3; research=<rp_no>" --trigger research_bridge`；成功後游標為 `deliver／DELIVERED／COMPLETED`；回應 `fsmState` 為 `RELEASE`；decision_trace 與人工序列相同；此 transition 由 `inner_gates.release_transition` 發出（⚖P2-1）
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-6**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3）冪等續跑：同 tag 已有 CREATED 列時跳過 tag、push、入庫，只補 transition。
  - Given 步驟 8 失敗後的狀態（列已存、FSM 仍 RELEASE_READY）；以及 FSM 已 RELEASE 的狀態
  - When 重送 `:tag`
  - Then 前者只執行 transition 並成功；後者零 FSM 寫入；兩者 `research_deliveries` 列數不增、gitops 無 `tag -a`
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-7**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3）push 失敗：502 delivery_step_failed、failure_step 為 push，本地 tag 保留，可重送續跑，絕不強推。
  - Given origin 設為不可寫的 bare repo
  - When POST `:tag`（push=true）；修復 origin 後再送
  - Then 第一次 502 且 `details.failure_step=push`、本地 tag 存在、無 DB 列、FSM 仍 RELEASE_READY；第二次成功；gitops 記錄全程無 `--force`
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-8**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3）FSM 步驟失敗：502 failure_step 為 fsm_release，DB 列已存，重送只重做 transition。
  - Given 注入 transition 失敗
  - When POST 兩次
  - Then 第一次 502 且列已存；第二次 201 且只多一個 transition
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_8 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-9**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3）push 確認規則：push 為假或無 origin 不推送；遠端已有同 sha 視為成功；不同 sha 拒。
  - Given 四種組合：push=false；push=true 無 origin；遠端 tag 同 sha；遠端 tag 異 sha
  - When POST `:tag`
  - Then 前兩者 gitops 無 `push`；第三者成功且不再 push；第四者 422 `invalid_request` 規則 `remote_tag_diverged` 且零 DB 列、FSM 不動
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_9 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-E-1**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3）tag 已存在且非本專案 CREATED 列：409 tag_exists，零 DB、零 FSM。
  - Given 手動先建同名 tag
  - When POST `:tag`
  - Then 409 `tag_exists`；零列、零 FSM 呼叫、本地 tag 不被改動
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-E-2**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-2、AC-R2P-20-3）前置不成立：現態非 RELEASE_READY、追溯未全覆蓋、SCR 開啟，各 409 且零 git 副作用。
  - Given 三種夾具
  - When POST `:tag`
  - Then 409 `fsm_state_conflict`（unmet 依序為 `not_release_ready`、`rtm_below_100`、`scr_open`；`scr_open` 另以 reason `scr_open` 回）；gitops 呼叫 0
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-E-3**（pytest｜`test_research_delivery.py`｜Unit｜AC-R2P-20-3）createGithubRelease 為 true：422 release_not_supported，零副作用。
  - Given 請求帶 `create_github_release=true`
  - When POST `:tag`
  - Then 422 `invalid_request`、規則 `release_not_supported`；gitops 呼叫 0；DB 零列
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_E_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-E-4**（pytest｜`test_research_delivery.py`｜Unit｜AC-R2P-20-3）argv 注入：message 含 --exec、換行、$(...) 時 argv 仍恰為模板。
  - Given message 為三種惡意字串
  - When 呼叫 `create_tag`
  - Then 攔截的 argv 逐字等於模板、無使用者字串；`shell=False`
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_E_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-E-5**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3、AC-R2P-16-5）規格漂移與 Tag：前置比對凍結 digest 不符即 422 digest_mismatch，零副作用（D-142 ⚖P2-9）。
  - Given 凍結檔被改（同 AT-962-8-1）；其餘前置皆成立（RELEASE_READY、追溯全覆蓋、無 OPEN SCR）；暫存 git 與 bare origin
  - When POST `:tag`
  - Then 422 `digest_mismatch`、`details.drift[{path, expected_sha256, actual_sha256}]`；gitops 呼叫 0（無 `tag -a`、無 push）、`research_deliveries` 零列、FSM 呼叫 0、快照檔不產生；凍結檔位元組不被 Bridge 改動；檢查序上漂移比對在專案存在與本文驗證之後、FSM 與 RTM 前置之前（同時有現態不合與漂移的夾具回 422 而非 409）
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_18_E_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-18-E-6**（pytest｜`test_research_deliver_router.py`｜Integration｜AC-R2P-20-3）容器模式前置：目標專案不可寫（repo_writable 缺）時 `:tag` 回 422 route_unsupported_in_deployment，零副作用。
  - Given capabilities 為 `mock-only` 或 `repo_writable=false` 的夾具；其餘前置成立
  - When POST `:tag`
  - Then 422 `route_unsupported_in_deployment`、`details.missing[{item: repo_writable}]`；gitops 呼叫 0、`research_deliveries` 零列、FSM 呼叫 0
  - 判定：python -m pytest tests/test_research_deliver_router.py -k AT_962_18_E_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-20-1**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-4）PR 正控序列：push -u origin、gh pr create（argv 陣列、token 只進環境）、入庫、事件。
  - Given 暫存 git 與 bare origin；假 gh（`FAKE_GH_MODE=ok`，需補 `pr create` 與 `pr list` 模式）；假 token
  - When POST `:pr`：`branch` 缺省、`body_preview_ack=true`
  - Then gitops 序列 `push -u origin <branch>` 然後 `gh pr create --title … --body … --base … --head …`；`research_deliveries` 一列：`kind=PULL_REQUEST`、`ref` 為 PR 編號、`url` 為 PR URL、`status=CREATED`、`snapshot_sha256` 為 NULL；`research.delivery` 事件一筆；假 gh 記錄 GH_TOKEN 只在環境
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_20_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-20-2**（pytest｜`test_research_delivery.py`｜Unit｜AC-R2P-20-4）標題與內文模板：標題截斷 60 字、內文四段固定序、不超過 4000 字、不帶使用者自由文字。
  - Given 研究專案 title 長度 59、60、61；FR 與 AC 數；內文資料欄位
  - When 呼叫模板函式
  - Then 標題為 `feat: <RP-NNNN> <title 截 60 字>（<FR 數> FR／<AC 數> AC）`；內文段落依序為摘要、追溯表摘要、規格依據、確認；總長不超過 4000（超過時截斷於段落邊界）；經 `gitops.redact`；內文長度邊界 3999、4000、4001：4000 以內原樣、4001 截斷於段落邊界且總長不超過 4000
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_20_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-20-3**（pytest｜`test_research_delivery.py`｜Unit｜AC-R2P-20-4）title 欄只作預覽：不等於模板輸出時 422 title_not_template；bodyPreviewAck 必須為 true。
  - Given 請求變體
  - When POST `:pr`
  - Then title 不吻合為 422 `invalid_request`（rule `title_not_template`）；ack 為 false 或缺為 422（rule `preview_ack_required`，本檔類推 ⚖P2-13）；零 gitops 呼叫
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_20_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-20-4**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-4）已有 PR 冪等：回既有、created 為 false，不再 gh pr create。
  - Given 假 gh 的 `pr list` 回非空；另一情境 DB 已有 PULL_REQUEST 列
  - When POST `:pr`
  - Then 200、`created=false`、回既有 URL；gitops 無 `pr create`
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_20_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-20-5**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-4）前置缺項：gh、gh_auth、origin、repo_writable 缺任一，422 route_unsupported_in_deployment，零副作用。
  - Given 四種缺項夾具
  - When POST `:pr`
  - Then 422 且 `details.missing[{item}]` 為對應項名；零 gitops 呼叫、零 DB 列
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_20_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-20-6**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-4）token 零外洩：只進 gh 子行程環境，不入 argv、log、DB、回應。
  - Given 假 gh `FAKE_GH_MODE=leak`；假 token
  - When POST `:pr`
  - Then argv、`research_deliveries`、事件、回應、Bridge log 全文掃描皆無 token 字面；leak 輸出經 `redact` 遮蔽
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_20_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-20-7**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-4）失敗不補償：502 delivery_step_failed、failure_step 為 push 或 pr_create，不寫 FAILED 列，只發 FAILED 事件。
  - Given `push` 失敗與 `FAKE_GH_MODE=fail-pr` 兩種
  - When POST `:pr`
  - Then 502、`details.failure_step` 對應、`details.stderr_tail` 已遮蔽截尾；`research_deliveries` 零列；`research.delivery{status:FAILED}` 一筆；無任何刪除形態 git 呼叫
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_20_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-20-E-3**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-4）branch 驗證：預設取 route_decisions.git_branch；不合 ref 規則 422。
  - Given branch 缺省、`feature/x`、`-x`、`a..b`
  - When POST `:pr`
  - Then 缺省採既有分支名；後二者 422 且零 gitops 呼叫
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_20_E_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-20-E-4**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-4）PR 內文不含 GH_TOKEN：leak 模式下以 token 值掃描 PR 標題與內文。
  - Given 假 gh 記錄的 argv
  - When POST `:pr`
  - Then 標題與內文零 token 字面
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_20_E_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-23-1**（pytest｜`test_research_reconcile.py`｜Unit｜AC-R2P-23-1）CHECK_IDS 加第七項 delivery，順序固定；以原始碼為準，不寫死數字。
  - Given `gates/reconcile.py` 的 `CHECK_IDS`
  - When 取 `reconcile()` 結果的 `checks[].id`
  - Then id 序列等於 `list(CHECK_IDS)` 且最後一項為 `delivery`（`test_research_reconcile.py:96,:490` 自動跟隨，註解由『六項』改為『以 CHECK_IDS 為準』）
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_962_23_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-23-2**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-23-4）delivery 檢查：重算 traceability_matrix.json 的 sha256 對 snapshot_sha256；一致 ok，不符 drift。
  - Given 有 RELEASE_TAG CREATED 列的專案；快照檔未改與被改兩種
  - When `:reconcile`
  - Then 未改為 ok；被改為 drift 且帶 `expectedSha256`、`actualSha256`；`consistent` 因 drift 為 false
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_962_23_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-23-3**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-23-4）無交付列：absent_check，ok 且 present 為假；有列但檔缺失為 drift。
  - Given 兩種夾具
  - When `:reconcile`
  - Then 未交付不算 drift；檔缺失為 drift 且 `actualSha256` 為 `missing`
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_962_23_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-23-4**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-23-4）交付時點自動對帳：reconcile_at_delivery 在 :tag 成功後恰一次，結果 consistent 為 true（出口 g）。
  - Given 成功建立 tag
  - When 讀 `research.reconcile` 事件與呼叫計數
  - Then 對帳恰一次（以 spy 計數；`reconcile_at_route` 在 `:route` 成功後恰一次的既有行為不變）；`consistent=true`；既有呼叫點鎖 `test_research_reconcile.py:331`（`test_AT_960_21_4_p0_has_only_the_gate_0_call_site_for_reconcile`）由 3 處更新為 4 處（呼叫點落 `routers/research.py` 的 `reconcile_at_delivery` 助手，§4.2 的 `test_research_reconcile.py:331` 列），並保留本 AT 自帶的呼叫次數斷言（D-142 ⚖P2-15 更正）
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_962_23_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-23-5**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-16-1）`:reconcile` 尾端順帶 healing.sync，失敗不影響對帳結果。
  - Given healing.sync 注入例外
  - When `:reconcile`
  - Then 對帳結果與無例外時相同；補漏成功時 log 補齊
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_962_23_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-23-E-1**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-23-1）P1 的 pending_correction 第三態不受影響。
  - Given TCS_PENDING 且 Stage-2 已凍結
  - When `:reconcile`
  - Then 該項仍為 `pending_correction`、不計 drift
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_962_23_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-23-E-2**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-23-4）只報告不修復：對帳後快照檔與 DB 列位元組不變。
  - Given 快照被改
  - When `:reconcile` 兩次
  - Then 檔案與資料列逐位不變；兩次結果相同
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_962_23_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-26-2**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3、AC-R2P-02-10）delivery.record op：研究表唯一寫入者為 Bridge，DB 列與事件同一交易，fail-loud。
  - Given `RDB`；注入 DB 錯誤
  - When 經 `db.apply('delivery.record', …)` 寫一次；再注入錯誤寫一次
  - Then 成功時列與事件同交易；錯誤不被吞（拋出）；游標更新函式同時 `append_event`
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_26_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-26-3**（pytest｜`test_research_delivery.py`｜Integration｜AC-R2P-20-3）outbox：DB 阻塞時 delivery.record 與 gate.decision 入 outbox，恢復後補寫，游標重衍生。
  - Given DB 阻塞後恢復
  - When 觸發兩種寫入
  - Then 恢復後各恰一列；游標由 `project_state` 重衍生；不重複
  - 判定：python -m pytest tests/test_research_delivery.py -k AT_962_26_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-26-5**（pytest｜`test_research_events.py`｜Unit｜AC-R2P-02-5、AC-R2P-20-4）research.delivery 事件登記：成功與失敗兩種 payload 的鍵集合定案並進 EVENT_PAYLOAD_KEYS，append_event 對登記外鍵 fail-loud。
  - Given `db.py` 的 `EVENT_PAYLOAD_KEYS`、`EVENT_OPTIONAL_KEYS`；`test_research_events.py:195,:282` 的登記表等式
  - When 餵 `append_event` 成功事件（ref 非 null、failure_step 為 null）、失敗事件（ref 為 null、failure_step 為 `push`、`pr_create`、`fsm_release`、`tag` 各一）、缺 `failure_step` 的失敗事件、多出未登記鍵的事件
  - Then 成功與四種失敗皆通過且鍵集合恰為 `{kind, ref, status, digest, reason, failure_step}`；失敗事件缺 `failure_step` 被拒；未登記鍵被拒（fail-loud）；`research_events.event_type` 無 DDL CHECK 故不需 V21
  - 判定：python -m pytest tests/test_research_events.py -k AT_962_26_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-26-E-1**（pytest｜`test_research_deliver_router.py`｜Integration｜AC-R2P-20-3）Bridge 五個新端點的檢查序：權杖、資料庫、專案存在、本文、前置。
  - Given 表驅動：`:gates`、`:tag`、`:pr`、`:traceability-preview`、`:healing-sync`；`:gates` 與 `:tag` 另備『同時漂移與現態不合』夾具
  - When 各以缺權杖、DB 阻塞、不存在專案、壞本文、漂移（僅 `:gates`、`:tag`）、前置不成立各打一次
  - Then 回應碼依序為 401 或 403、503、404、422、422 `digest_mismatch`（僅 `:gates`、`:tag`）、409；先中者定案（漂移優先於現態與 RTM 前置，D-144 F-01）
  - 判定：python -m pytest tests/test_research_deliver_router.py -k AT_962_26_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-28-1**（pytest｜`test_research_int_p2.py`｜Integration｜AC-R2P-20-3、AC-R2P-15-6）出口 (a)：內環走完到交付。gates（PR_REVIEW PASS、RTM_VERIFY PASS）→ FSM RELEASE_READY → tag（file:// bare origin）→ FSM RELEASE，逐字證據。
  - Given 暫存專案、暫存 git、`file://` bare repo、暫存狀態目錄；mock 引擎
  - When 依序呼叫 `:gates`、`:gates`、`:tag`
  - Then decision_trace 與人工等價序列 diff 為空；`show` 輸出 `current_state=RELEASE`；M2 與 M3 指標欄取值（records 完整、追溯 100%）入證據
  - 判定：python -m pytest tests/test_research_int_p2.py -k AT_962_28_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-28-2**（pytest｜`test_research_int_p2.py`｜Integration｜AC-R2P-20-4）出口 (a) 的 PR URL：假 gh 走 pr create 與 pr list。
  - Given 假 gh（需補模式）
  - When POST `:pr`
  - Then 回 PR URL；R11 有 PULL_REQUEST 列
  - 判定：python -m pytest tests/test_research_int_p2.py -k AT_962_28_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-28-3**（pytest｜`test_research_int_p2.py`｜Integration｜AC-R2P-16-3、AC-R2P-16-1）出口 (b)(f)：引擎重試耗盡自然觸發 ESCALATED（claude 為 mock 可執行檔，須標明），視圖對真失敗步驟有列。
  - Given 暫存目標專案；playbook 一步、`max_retries=1`；evaluator 以真指令失敗；claude 以既有載具驅動：`tests/conftest.py:236-244` 的 `run_body` 加 config `claude.command` 指向 `aisdlc-mock-claude`，失敗由 `MOCK_CLAUDE_FAIL_REGEX`（`mock_claude.py:19`）造成（repo 內沒有以環境變數指定 claude 路徑的機制，原稿該寫法已更正）
  - When 跑 run 至 ESCALATED；`select count(*) from console.v_research_healing_attempts where research_id=…`
  - Then review request 由引擎自然產生（非手寫列）；視圖計數至少 1；證據標『引擎真、claude 為 mock』（D-140 #13）
  - 判定：python -m pytest tests/test_research_int_p2.py -k AT_962_28_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-28-6**（pytest｜`test_research_int_p2.py`｜Integration｜AC-R2P-23-4）出口 (g)：`:tag` 後對帳 consistent 為 true。
  - Given 同 AT-962-28-1
  - When 讀對帳事件
  - Then `consistent=true`
  - 判定：python -m pytest tests/test_research_int_p2.py -k AT_962_28_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-28-E-1**（pytest｜`test_research_int_p2.py`｜Integration｜AC-R2P-16-5）SPEC_CHANGE_FORBIDDEN 取證：暫存專案手改凍結檔，偵測加告警，sha 不被 Bridge 改動；『被拒』列 V-S1。
  - Given 暫存專案
  - When 手改一個凍結檔後 sync
  - Then 偵測、告警、sha 與手改後相同
  - 判定：python -m pytest tests/test_research_int_p2.py -k AT_962_28_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-962-28-E-3**（pytest｜`test_research_int_p2.py`｜Integration｜AC-R2P-20-3）hermetic：任何 P2 pytest AT 不連外網，真 GitHub 不被連線（沿 AT-961-23-E-1 的替身體例）。
  - Given socket 層替身，攔截所有非 loopback 連線；P2 的 pytest 檔集合
  - When 跑 P2 四個 Bridge 測試檔的交付與自癒案例並掃描原始碼中的 `https://github.com`、`api.github.com` 呼叫
  - Then 零真連線；原始碼無對真 GitHub 的呼叫（假 gh 與 `file://` bare repo 取代）
  - 判定：python -m pytest tests/test_research_int_p2.py -k AT_962_28_E_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）

### 3.2 backend（JUnit；徑②）

- **AT-962-1-1**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7、AC-R2P-02-8）Flyway 歷史 1～21 全成功；V21 檔名與描述固定；V1～V20 的 checksum 不變；ddl-auto validate 不報錯。
  - Given 套用 V1～V21 的 PostgreSQL 18 容器（Testcontainers）；Architecture K.6 的 V21 DDL（逐字取 K.6，對照 `V21_DDL.md` 草案）
  - When 讀 flyway_schema_history；以 `databaseAt("20")` 與 `databaseAt("21")` 各建一庫比對 V1～V20 的 checksum；以 validate 啟動
  - Then 版本依序 1 至 21 且皆成功；V21 的 script 為 `V21__research_gate_details_delivery_snapshot.sql`、描述為 `research gate details delivery snapshot`；V1～V20 的 checksum 與 20 版庫相同；啟動不報 validate 錯；V21 不新增任何表（console schema 的表集合與 V20 相同，只多欄位）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_1*"（cwd＝AgentConsole/backend）
- **AT-962-1-2**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）research_gate_decisions.gate 的 CHECK 加 SCG6：列舉恰八值，SCG7 與小寫被拒，VARCHAR(11) 容得下全部值。
  - Given 套用 V1～V21；一個合法研究專案列
  - When 逐一插入 gate 為 `GATE0`、`SCR`、`ROUTE`、`STAGE2`、`SCG4`、`SCG5`、`SCG6`、`ABANDON_KEY`，以及 `SCG7`、`scg6`、`SCG`、空字串
  - Then 八個合法值全通過；`SCG7`、`scg6`、`SCG`、空字串為 23514；既有 `SCG4`、`SCG5` 列於升級前後值不變；`expectEnum` 的期望集合由七值改八值（§4 第 9 列）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_2*"（cwd＝AgentConsole/backend）
- **AT-962-1-3**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）research_gate_decisions.details：JSONB NOT NULL 預設空物件，CHECK 限物件型別；三個約定鍵可寫入。
  - Given 套用 V1～V21；一個研究專案；一筆升級前的既有 GATE0 決定列
  - When 省略 details 插入；插入 `{"reviewer_independent":true,"review_report_ref":"a.md","ci_red":false}`；插入 `[]`、`"x"`、`1`、`null`（JSON null）、SQL NULL；讀既有 GATE0 列的 details
  - Then 省略時值為空物件；三鍵物件通過；`[]`、`"x"`、`1`、JSON `null` 為 23514（jsonb_typeof 非 object）；SQL NULL 為 23502；既有列 details 回填為空物件；欄位型別為 jsonb；append-only 守衛仍擋 UPDATE 與 DELETE
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_3*"（cwd＝AgentConsole/backend）
- **AT-962-1-4**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）research_deliveries.snapshot_sha256：CHAR(64) 可空，64 位小寫十六進位才合法。
  - Given 套用 V1～V21；一個研究專案
  - When 插入 RELEASE_TAG 列：snapshot_sha256 為 64 位小寫十六進位、63 位、65 位、64 位含大寫、64 位含 `g`、NULL；對已存在列 UPDATE snapshot_sha256
  - Then 64 位小寫與 NULL 通過；63 位為 23514；65 位為 22001（欄寬）；含大寫或非十六進位為 23514；UPDATE 被 append-only 守衛拒（類別 23）；『TAG 列必填』由應用層守，DB 不擋（NULL 的 TAG 列可插入，由 AT-962-18 在應用層釘）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_4*"（cwd＝AgentConsole/backend）
- **AT-962-1-5**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7、AC-R2P-19-1）research_scr.evidence_url：可空，限 https 開頭且長度不超過 500；不在受控更新清單內。
  - Given 套用 V1～V21；一個研究專案
  - When 插入 SCR 列：evidence_url 為 NULL、`https://a.example/x`、`http://a.example`、`HTTPS://a.example`、`javascript:alert(1)`、`https://` 補到恰 500 字元、501 字元、空字串；對既有列 UPDATE evidence_url
  - Then NULL 與 https 開頭且 500 字元以內者通過；`http://`、大寫 `HTTPS://`、`javascript:`、空字串為 23514；500 字元通過、501 字元為 23514（CHECK 含長度上限，欄位為 TEXT 故非 22001）；UPDATE evidence_url 被 `research_controlled_update_guard` 拒（清單外欄位）；P1 既有 SCR 插入（不帶此欄）仍通過
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_5*"（cwd＝AgentConsole/backend）
- **AT-962-1-6**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）P0／P1 的守衛不退步：十八張 research_ 表逐表 DELETE 仍被擋、受控表清單與 append-only 清單不變。
  - Given 套用 V1～V21；十八張 research_ 表各一合法列
  - When 逐表 DELETE；對 research_gate_decisions、research_deliveries 做 UPDATE；對四張受控表做清單內與清單外欄位 UPDATE
  - Then DELETE 一律類別 23；兩張 append-only 表 UPDATE 被拒；受控表清單內欄位可更新、清單外被拒；V21 未改任何觸發器與函式（觸發器名單與 V20 相同）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_6*"（cwd＝AgentConsole/backend）
- **AT-962-1-7**（JUnit｜`BackupJobMigrationIT`｜Integration｜AC-R2P-02-7）六處 Flyway 版本清單加 21，且既有表零變動快照不受 V21 影響。
  - Given §4 第 1 列列出的六處版本清單（含 `BackupJobMigrationIT` 的兩處）
  - When 跑六個 Flyway IT；`BackupJobMigrationIT` 的 `snapshotOfExistingTables` 前後比對
  - Then 六處清單皆為 1 至 21；`ResearchSchemaMigrationIT` 另釘 `containsEntry("21", "research gate details delivery snapshot")`；`research_` 起頭的表被快照排除（V21 只改這些表）故比對不變；視圖排除條件（V19 的 `v\_research\_`）不動
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.BackupJobMigrationIT.AT_962_1_7*"（cwd＝AgentConsole/backend）
- **AT-962-1-E-1**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）升級不改既有資料：在已有 V20 資料（含各 gate 值的決定列、SCR 列、交付列）的庫上套 V21，既有列逐欄不變。
  - Given 先套 V1～V20 並灌入各表代表列（含 gate 為 SCG5 的決定、kind 為 PULL_REQUEST 的交付）
  - When 套 V21 後逐列比對（排除新增欄）
  - Then 既有列的原欄位值逐位相同；新欄位的預設值與 NULL 正確（details 空物件、snapshot_sha256 與 evidence_url 為 NULL）；沒有任何列因新 CHECK 被拒
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_E_1*"（cwd＝AgentConsole/backend）
- **AT-962-1-E-2**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-8）V21 的時間欄與欄位型別：新增欄型別固定，既有時間欄仍皆為帶時區型別。
  - Given 套用 V1～V21
  - When 以 information_schema.columns 查三個新欄與 V16～V19 的全部 timestamp 欄
  - Then details 為 jsonb、snapshot_sha256 為 character(64)、evidence_url 為 text；所有 research_ 表的 timestamp 欄皆為 `timestamp with time zone`（沿 AT-961-1-1）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_E_2*"（cwd＝AgentConsole/backend）
- **AT-962-1-E-3**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）V21 約束名可預期且可被 pg_constraint 逐條查到（不是匿名約束）。
  - Given 套用 V1～V21；K.6 指定的約束名
  - When 查 `pg_constraint` 中 research_gate_decisions、research_deliveries、research_scr 的 CHECK 名與定義
  - Then gate 的 CHECK 定義含 `SCG6`；details、snapshot_sha256、evidence_url 各有一條具名 CHECK；舊的 gate CHECK 已被取代而不是並存（同一欄不得有兩條互相矛盾的 gate CHECK）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1_E_3*"（cwd＝AgentConsole/backend）
- **AT-962-1b-1**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）〔勘誤 2026-11-08 新列；D-162(a)〕V22 升級不改既有資料。
  - Given 已套 V1～V21 且含各表既有列的拋棄式資料庫
  - When 套 V22
  - Then 各表既有列逐欄不變；V1～V21 的 checksum 不變；V22 不新增任何表
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1b_1*"（cwd＝AgentConsole/backend）
- **AT-962-1b-2**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）〔勘誤 2026-11-08 新列；D-162(a)〕DELIVERED 組合可寫且列舉恰十四值。
  - Given 套用 V1～V22
  - When 寫入 `flow_step=deliver`、`flow_phase=DELIVERED`、`flow_status=COMPLETED` 的研究專案列，並以 `pg_get_constraintdef` 讀 `research_projects_flow_phase_check`
  - Then 寫入成功；`flow_phase` 列舉恰為十四值（原十三值加 `DELIVERED`）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1b_2*"（cwd＝AgentConsole/backend）
- **AT-962-1b-3**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）〔勘誤 2026-11-08 新列；D-162(a)〕V22 後 CHECK 仍擋非法值。
  - Given 套用 V1～V22
  - When `flow_phase` 取小寫 `delivered`、空字串、尾空白 `DELIVERED `、其他字串
  - Then 皆 SQLSTATE 23514
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1b_3*"（cwd＝AgentConsole/backend）
- **AT-962-1b-4**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）〔勘誤 2026-11-08 新列；D-162(a)〕V22 約束名可預期且守衛不退步。
  - Given 套用 V1～V22
  - When 以 `pg_constraint` 查 `research_projects_flow_phase_check`，並重做 AT-962-1-E-3 的 gate 約束查詢
  - Then `research_projects_flow_phase_check` 恰一條、定義含 `DELIVERED`（舊約束被取代而非並存）；`research_gate_decisions_gate_check` 仍恰一條且含 `SCG6`
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_1b_4*"（cwd＝AgentConsole/backend）
- **AT-962-4-1**（JUnit｜`ResearchGateApiIT`｜Integration｜AC-R2P-15-6）ADMIN 登錄 SCG-4：console-api 產 decisionId、帶最新 runId、approver 取 JWT subject，回應形狀固定。
  - Given 迷你 Bridge（`MiniBridge` 補 `:gates`）；已綁 console 專案且有 run 的研究專案；任務皆完成、RTM fullyCovered
  - When ADMIN POST `/gates`：`gate=PR_REVIEW`、`result=PASS`、`reviewerIndependent=true`
  - Then 迷你 Bridge 收到恰一次 `:gates`：`decision_id` 為 UUID、`run_id` 為最新 run、`approver` 為 JWT subject、`requested_by` 為同值；回應 200 鍵集合為 `gateDecisionId`、`gate`、`result`、`fsmStateBefore`、`nextState`、`escalated`、`flow`；console-api 對 `research_*` 零寫入
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchGateApiIT.AT_962_4_1*"（cwd＝AgentConsole/backend）
- **AT-962-4-2**（JUnit｜`ResearchGateApiIT`｜Integration｜AC-R2P-15-6）PR_REVIEW 服務層前置：任務未完成或 RTM 未全覆蓋或無 RTM 時 409，details.unmet 逐項列出，Bridge 請求數為 0。
  - Given 三種夾具：有任務 RUNNING；RTM fullyCovered 為假；RTM 404（`rtm_not_found`）
  - When ADMIN POST PR_REVIEW
  - Then 皆 409 `fsm_state_conflict`；`details.unmet` 依序為 `tasks_incomplete`、`rtm_below_100`、`rtm_unavailable`（可同時多項）；迷你 Bridge 請求數為 0
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchGateApiIT.AT_962_4_2*"（cwd＝AgentConsole/backend）
- **AT-962-4-3**（JUnit｜`ResearchGateApiIT`｜Integration｜AC-R2P-15-6）RTM_VERIFY 前置：acPct 為 100 才轉送；99.99 拒。
  - Given RTM 夾具 acPct 為 99.99、100
  - When ADMIN POST RTM_VERIFY
  - Then 99.99 為 409 `fsm_state_conflict`（unmet 含 `rtm_below_100`）、Bridge 請求 0；100 轉送 Bridge 恰一次
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchGateApiIT.AT_962_4_3*"（cwd＝AgentConsole/backend）
- **AT-962-4-4**（JUnit｜`ResearchGateApiIT`｜Integration｜AC-R2P-15-6）審查者獨立性：PR_REVIEW 必須 reviewerIndependent 為 true；其餘 gate 不要求；Console 不判斷獨立性。
  - Given 請求變體：true、false、缺；對 RTM_VERIFY 的 false 與缺
  - When ADMIN POST
  - Then PR_REVIEW 的 false 與缺為 422 `invalid_request`（`violations[{field:reviewerIndependent, rule:reviewer_independence_required}]`）；RTM_VERIFY 與 RELEASE_READY 不受限；true 時轉送本文含 `reviewer_independent=true` 與 `review_report_ref`
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchGateApiIT.AT_962_4_4*"（cwd＝AgentConsole/backend）
- **AT-962-4-5**（JUnit｜`ResearchGateApiIT`｜Integration｜AC-R2P-15-6）欄位邊界：FAIL 必填 reason（1～500）、reviewReportRef 不超過 300、組合限制。
  - Given 請求變體
  - When FAIL 配空 reason、500、501 字元；PASS 配空 reason；reviewReportRef 300、301 字元；`(RELEASE_READY, PASS)`；未知 gate
  - Then 空與 501 字元、301 字元、`(RELEASE_READY, PASS)`（rule `release_pass_via_tag`）、未知 gate 皆 422 且 Bridge 請求 0；500 與 300 字元與 PASS 空理由通過
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchGateApiIT.AT_962_4_5*"（cwd＝AgentConsole/backend）
- **AT-962-4-6**（JUnit｜`ResearchGateApiIT`｜Integration｜AC-R2P-15-6）OPEN SCR 期間 409 scr_open；escalated 由 nextState 前綴 ESCALATION 判定並如實回傳。
  - Given 一個 OPEN SCR 的專案；迷你 Bridge 回 `next_state=ESCALATION_FINAL`
  - When ADMIN POST（前者）與 POST（後者）
  - Then 前者 409 `scr_open`、Bridge 請求 0；後者 200 且 `escalated=true`、`nextState` 為字面值
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchGateApiIT.AT_962_4_6*"（cwd＝AgentConsole/backend）
- **AT-962-4-E-1**（JUnit｜`RbacIT`｜Integration｜AC-R2P-15-6）OPERATOR 呼叫 gates 回 403，Bridge 請求數為 0，無任何研究表變化。
  - Given OPERATOR 憑證；迷你 Bridge 計數器
  - When POST `/gates`（各 gate 變體）
  - Then 403 `ACCESS_DENIED`（授權鏈）；Bridge 請求 0；`research_gate_decisions` 與 `research_events` 列數不變；`SecurityConfig.java:107` 零 diff
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.security.RbacIT.AT_962_4_E_1*"（cwd＝AgentConsole/backend）
- **AT-962-4-E-2**（JUnit｜`RbacIT`｜Integration｜AC-R2P-15-6）VIEWER 呼叫 gates 回 403，且與 OPERATOR 同為授權鏈拒絕。
  - Given VIEWER 憑證
  - When POST `/gates`
  - Then 403 `ACCESS_DENIED`；Bridge 請求 0
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.security.RbacIT.AT_962_4_E_2*"（cwd＝AgentConsole/backend）
- **AT-962-4-E-3**（JUnit｜`ResearchGateApiIT`｜Integration｜AC-R2P-15-6）專案狀態負控：研究專案不存在回 404；尚未綁 console 專案回 409。
  - Given 不存在的 id；已 Gate 0 但 `console_project_id` 為空的專案
  - When ADMIN POST
  - Then 前者 404 `research_not_found`；後者 409 `fsm_state_conflict`（unmet 含 `no_console_project`，本檔類推見 ⚖P2-6）；Bridge 請求 0
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchGateApiIT.AT_962_4_E_3*"（cwd＝AgentConsole/backend）
- **AT-962-4-E-4**（JUnit｜`ResearchGateApiIT`｜Integration｜AC-R2P-15-6）Bridge 不可達或逾時：502 或 504，且 console-api 不留部分狀態。
  - Given 迷你 Bridge 停機與延遲
  - When ADMIN POST
  - Then 502 `bridge_unreachable`、504 `bridge_timeout`；console-api 無研究表寫入；`audit_log` 仍橫切一列（AuditLoggingFilter）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchGateApiIT.AT_962_4_E_4*"（cwd＝AgentConsole/backend）
- **AT-962-4-E-5**（JUnit｜`ResearchGateApiIT`｜Integration｜AC-R2P-15-6、AC-R2P-16-5）console-api 透傳 gates 的 422 digest_mismatch：reason、狀態碼與 details.drift 原樣，不重寫。
  - Given 迷你 Bridge 回 422 `digest_mismatch` 與 `details.drift[{path, expected_sha256, actual_sha256}]`
  - When ADMIN POST `/gates`
  - Then console-api 回 422、`reason=digest_mismatch`（在 37 個四方鎖內）、`details.drift` 逐項原樣；`audit_log` 恰一列；console-api 對 `research_*` 零寫入
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchGateApiIT.AT_962_4_E_5*"（cwd＝AgentConsole/backend）
- **AT-962-7-3**（JUnit｜`HealingExcerptMaskerTest`｜Unit｜AC-R2P-16-4）Java 遮蔽器與 Python 同夾具逐筆相同（兩端對拍）。
  - Given `HealingExcerptMasker`（API-P2 新類）；讀 `engine-bridge/tests/fixtures/research/healing_redaction_cases.json`（以 `BridgeSource` 同類相對路徑機制）
  - When 逐筆餵 `mask()`
  - Then 每筆輸出等於 expected；Java 端另斷言該夾具檔在 repo 內只有一份（以檔名 glob 計數為 1）且路徑與 AT-962-7-1 所讀相同（不再以『Python 端記錄值』比對 sha）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.out.persistence.research.HealingExcerptMaskerTest.AT_962_7_3*"（cwd＝AgentConsole/backend）
- **AT-962-7-5**（JUnit｜`ResearchHealingApiIT`｜Integration｜AC-R2P-16-4）API 回應逐字掃描：GET healing 的 excerpt 已遮蔽。
  - Given 同夾具資料；VIEWER 憑證
  - When GET `/healing`；以字串掃整個回應本文
  - Then 本文不含任何假 token 字面；excerpt 為遮蔽後尾 300 字元
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchHealingApiIT.AT_962_7_5*"（cwd＝AgentConsole/backend）
- **AT-962-7-E-3**（JUnit｜`HealingExcerptMaskerTest`｜Unit｜AC-R2P-16-4）夾具鎖：兩端測試各自讀同一份 JSON，不各抄一份。
  - Given Python 與 Java 測試原始碼
  - When 掃描兩端對夾具路徑的引用與內嵌的 token 樣式字面
  - Then 兩端都引用同一路徑；測試原始碼不內嵌第二份 expected 表
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.out.persistence.research.HealingExcerptMaskerTest.AT_962_7_E_3*"（cwd＝AgentConsole/backend）
- **AT-962-8-5**（JUnit｜`ResearchHealingApiIT`｜Integration｜AC-R2P-16-5）API 於漂移列補 specChangeForbidden。
  - Given 迷你 Bridge 回 `spec_change` 非空
  - When GET `/healing`
  - Then 對應列 `specChangeForbidden` 為 true、其他列為 false；無漂移時全 false
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchHealingApiIT.AT_962_8_5*"（cwd＝AgentConsole/backend）
- **AT-962-9-1**（JUnit｜`ResearchHealingApiIT`｜Integration｜AC-R2P-16-1、AC-R2P-16-2）GET healing 逐值對 DB：列數、run、task、attempt、status、excerpt、occurredAt；VIEWER 可讀。
  - Given Testcontainers 內灌 execution_steps 的 RETRYING 與 FAILED；已綁研究專案
  - When VIEWER GET `/healing`
  - Then 200；rows 逐值等於同一交易讀視圖並以視窗函式導出的值；欄位名為 camelCase；回應含 `maxRetries`、`logSyncedThrough`
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchHealingApiIT.AT_962_9_1*"（cwd＝AgentConsole/backend）
- **AT-962-9-2**（JUnit｜`ResearchHealingApiIT`｜Integration｜AC-R2P-16-2）maxRetries 取系統參數 agent.maxRetries：預設 3，改 5 後回 5。
  - Given `system_configs` 的 `agent.maxRetries`
  - When GET 兩次（改值前後）
  - Then 前後分別回 3 與 5；attempt 與上限並列顯示所需欄位齊備；attempt 邊界：attempt 為 `maxRetries` 減 1、等於、加 1 三列，顯示『嘗試 n／上限』，等於者標『已耗盡』、超過者不顯示負的剩餘次數
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchHealingApiIT.AT_962_9_2*"（cwd＝AgentConsole/backend）
- **AT-962-9-3**（JUnit｜`ResearchHealingApiIT`｜Integration｜AC-R2P-16-2、AC-R2P-16-3）resolved 與 escalated 導出：任務其後 COMPLETED 補 resolved；任務 ESCALATED 的最後一列補 escalated。
  - Given 三個任務：重試後完成、重試耗盡轉 ESCALATED、仍在重試
  - When GET `/healing`
  - Then 第一個任務各列 `resolved` 為 true；第二個任務最後一列 `escalated` 為 true；第三個皆 false
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchHealingApiIT.AT_962_9_3*"（cwd＝AgentConsole/backend）
- **AT-962-9-4**（JUnit｜`ResearchHealingApiIT`｜Integration｜AC-R2P-16-2）attribution 與 patchResult 恆為 null，不假造（PRD R10 與資料現況不一致，D-140 #5）。
  - Given 任何資料
  - When GET `/healing`
  - Then 每列這兩個欄位為 null；OpenAPI 註明『引擎未提供』
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchHealingApiIT.AT_962_9_4*"（cwd＝AgentConsole/backend）
- **AT-962-9-5**（JUnit｜`ResearchHealingApiIT`｜Integration｜AC-R2P-16-1）日誌落後筆數：logSyncedThrough 與差額推得。
  - Given 迷你 Bridge 的 `:healing-sync` 回應 `view_rows` 大於 `log_lines`
  - When GET `/healing`
  - Then 回應含落後筆數（view_rows 減 log_lines）與 `logSyncedThrough`；無同步紀錄時為 null
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchHealingApiIT.AT_962_9_5*"（cwd＝AgentConsole/backend）
- **AT-962-9-6**（JUnit｜`ResearchHealingNotifierTest`｜Unit｜AC-R2P-16-1）通知時點與條件：RunConsumers.handle 在 tx 提交之後、hub.publish 之前，僅當事件使任務進入 RETRYING／FAILED／ESCALATED 時呼叫 notify。
  - Given `RunEventProcessor.Outcome.healingRelevant` 旗標；呼叫順序記錄器
  - When 餵相關事件（RETRYING、FAILED、ESCALATED）與無關事件（RUNNING、COMPLETED）
  - Then 相關事件各通知一次、無關事件 0 次；順序為 commit→notify→publish；`RunEventProcessor` 的處理邏輯零改動（只加唯讀旗標）
  - 判定：gradlew test --tests "com.aisdlc.console.application.service.ResearchHealingNotifierTest.AT_962_9_6*"（cwd＝AgentConsole/backend）
- **AT-962-9-7**（JUnit｜`ResearchHealingApiIT`｜Integration｜AC-R2P-16-2）retryingSteps 計算：最新 run 內 RETRYING 且其後無同 task 非 RETRYING 列者。
  - Given 三種序列的 steps
  - When GET `/healing` 與 `/kanban`
  - Then 兩端點的 retryingSteps 相同且等於定義值
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchHealingApiIT.AT_962_9_7*"（cwd＝AgentConsole/backend）
- **AT-962-9-E-1**（JUnit｜`ResearchHealingNotifierTest`｜Unit｜AC-R2P-16-1）通知 best-effort：Bridge 不可達或逾時只記 log，事件處理與 SSE 發佈不受影響。
  - Given 迷你 Bridge 停機
  - When 處理一個相關事件
  - Then 事件交易已提交、SSE 照發、無例外外洩；log 有一行警告（不含 token）
  - 判定：gradlew test --tests "com.aisdlc.console.application.service.ResearchHealingNotifierTest.AT_962_9_E_1*"（cwd＝AgentConsole/backend）
- **AT-962-9-E-2**（JUnit｜`ResearchHealingNotifierTest`｜Unit｜AC-R2P-16-1）非研究專案的 run：notify 為無操作，Bridge 請求數為 0。
  - Given run 所屬專案未綁研究專案
  - When 處理相關事件
  - Then Bridge 請求 0；無例外
  - 判定：gradlew test --tests "com.aisdlc.console.application.service.ResearchHealingNotifierTest.AT_962_9_E_2*"（cwd＝AgentConsole/backend）
- **AT-962-9-E-3**（JUnit｜`ResearchHealingApiIT`｜Integration｜AC-R2P-16-2）不存在的研究專案 404；專案無 console 專案時回空列 200。
  - Given 兩種專案
  - When GET `/healing`
  - Then 404 `research_not_found`；後者 200、rows 為空、`maxRetries` 仍回
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchHealingApiIT.AT_962_9_E_3*"（cwd＝AgentConsole/backend）
- **AT-962-10-1**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-1）差分：Task 拆解欄與 GET decomposition 逐值相等（完成判定＝已簽核且非 stale）。
  - Given Testcontainers；研究專案綁 console 專案；拆解狀態依序為 DRAFTED、SIGNED_OFF、SIGNED_OFF 且 stale、STALE
  - When 同一交易內 GET `/kanban` 與 GET `/decomposition`
  - Then `columns.decompose` 的 status、tasksCount、stale 與來源端點逐值相等；`done` 只在 SIGNED_OFF 且非 stale 時為 true
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_1*"（cwd＝AgentConsole/backend）
- **AT-962-10-2**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-1）差分：測試規格產生欄與 GET fsm 的 frozenStages、negotiated 逐值相等。
  - Given 迷你 Bridge 的 `/sdd/fsm` 回 Stage-2 未凍結、已凍結兩種
  - When GET `/kanban` 與 GET `/fsm`
  - Then `tcs.stage2Frozen`、`tcs.negotiated`、`tcs.fsmState` 與 fsm 視圖相同；`done` 等於 stage2Frozen
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_2*"（cwd＝AgentConsole/backend）
- **AT-962-10-3**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-1）差分：程式碼實作欄與專案任務計數、FSM 現態逐值相等；完成判定在邊界上精確。
  - Given 任務組合：total 為 0；completed 加 skipped 等於 total；差 1；含 failed、escalated、retrying
  - When GET `/kanban` 與專案詳情的任務計數
  - Then 七個計數（total、running、completed、skipped、failed、escalated、retrying）逐值相等；`done` 只在 total 大於 0 且 completed 加 skipped 等於 total 時為 true（total 為 0 不算完成）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_3*"（cwd＝AgentConsole/backend）
- **AT-962-10-4**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-1）差分：自癒修復欄與 GET healing 的 retryingSteps、escalatedTasks、maxRetries 逐值相等。
  - Given 含 RETRYING 序列與 ESCALATED 任務的資料
  - When GET `/kanban` 與 GET `/healing`
  - Then 三值相等；`done` 在 retryingSteps 與 escalatedTasks 皆為 0 時為 true
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_4*"（cwd＝AgentConsole/backend）
- **AT-962-10-5**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-1）差分：回歸驗收欄與 executions/{runId}/rtm、FSM 現態逐值相等；完成判定邊界。
  - Given RTM：acPct 100 且 fullyCovered、acPct 99.99、fullyCovered 為假；FSM 現態 RELEASE_READY、RELEASE、RTM_VERIFY；RTM 404
  - When GET `/kanban` 與 GET `/executions/{runId}/rtm`
  - Then `rtm.*` 與來源逐值相等且 `rtm.advisory` 恆為 true；404 時 `rtmAvailable` 為 false；`done` 僅在 acPct 為 100、fullyCovered 為真、現態屬 RELEASE_READY 或 RELEASE 時為 true（其餘組合皆 false）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_5*"（cwd＝AgentConsole/backend）
- **AT-962-10-6**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-18-3、AC-R2P-15-1）pendingReviews：review_requests 的 PENDING 與該專案所有 run 相連；kind 區分 ESCALATED；已決定者不列。
  - Given 三筆待審（一 ESCALATED、一 Agent 請求、一已 DECIDED）；另一專案的待審一筆
  - When GET `/kanban` 兩次（間隔不變資料，模擬重新整理）
  - Then 只回前兩筆且鍵為 `reviewId`、`runId`、`kind`、`taskId`、`reason`、`createdAt`、`allowedDecisions`；兩次結果相同；不含他專案資料；新增的專案級查詢不改既有 `ReviewRequestRepositoryAdapter` 方法
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_6*"（cwd＝AgentConsole/backend）
- **AT-962-10-7**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-6）gates 清單：SCG4、SCG5、SCG6 各取最近 5 筆；6 筆時只回 5。
  - Given 每種 gate 各 6 筆決定（依 D-139 納入 SCG6，見 ⚖P2-8）
  - When GET `/kanban`
  - Then 每種至多 5 筆、依 decidedAt 由新到舊；鍵為 `gate`、`decision`、`decidedBy`、`decidedAt`、`fsmStateAfter`、`reason`
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_7*"（cwd＝AgentConsole/backend）
- **AT-962-10-8**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-4）Bridge 不可達：200、bridgeReachable 為 false、stale 為 true、FSM 衍生欄 null 加 unknown、DB 欄取即時值、snapshotAt 取三個來源時間的最大值。
  - Given 迷你 Bridge 停機；專案 updated_at、最新事件、最新決定三個時間各異
  - When GET `/kanban`
  - Then `bridgeReachable=false`、`stale=true`；`tcs.stage2Frozen`、`tcs.fsmState`、`implement.fsmState`、`regression.fsmState`、`regression.releaseReady` 皆為 null 且各帶 `unknown:true`（不猜）；任務計數、拆解、pendingReviews、gates 為 DB 即時值；`snapshotAt` 為三者最大值；無任何事件時取專案 updated_at
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_8*"（cwd＝AgentConsole/backend）
- **AT-962-10-9**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-1）latestRunId 取專案最新 execution_run；無 run 時為 null 且 rtmAvailable 為 false。
  - Given 三個 run；無 run 的專案
  - When GET `/kanban`
  - Then `latestRunId` 為最新 run；無 run 時為 null、regression 欄 `rtm` 為 null
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_9*"（cwd＝AgentConsole/backend）
- **AT-962-10-E-1**（JUnit｜`ResearchKanbanRouteInventoryTest`｜Unit｜AC-R2P-15-2）路由清單比對：/api/v1/research/** 無執行控制動詞路徑；P2 新增路徑集合恰七條；負控夾具被判違規。
  - Given `RequestMappingHandlerMapping` 與 OpenAPI paths；夾具路徑 `/api/v1/research/projects/{id}/execute`
  - When 掃描全部研究路徑與夾具
  - Then 實樹零個含 `execute`、`pause`、`resume`、`cancel`、`stop`、`restore`、`review` 片段的路徑；P2 新增路徑集合等於 §3 AC-962-24 列出的七條；夾具被判違規
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanRouteInventoryTest.AT_962_10_E_1*"（cwd＝AgentConsole/backend）
- **AT-962-10-E-2**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-2）看板 GET 無副作用：前後研究表列數與 Bridge 寫入請求數不變，Bridge 只收讀請求。
  - Given 迷你 Bridge 請求記錄器
  - When GET `/kanban` 三次
  - Then `research_*` 列數不變；迷你 Bridge 只有 `GET /sdd/fsm/{project}` 讀請求、寫請求 0
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_E_2*"（cwd＝AgentConsole/backend）
- **AT-962-10-E-3**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-2）未簽核與 SCR 開啟時既有 execute 仍回 409（看板不重造守衛）。
  - Given 研究專案：拆解未簽核；另一個 SCR 為 OPEN
  - When POST 既有 `/projects/{id}/execute`
  - Then 各 409（`UNSIGNED_DRAFT` 與 `scr_open`）；本包不改 `ExecutionController`
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_E_3*"（cwd＝AgentConsole/backend）
- **AT-962-10-E-4**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-1）存取與不存在：VIEWER 200、未登入 401、不存在專案 404。
  - Given 三種呼叫者與 id
  - When GET `/kanban`
  - Then 如列；404 reason 為 `research_not_found`
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_E_4*"（cwd＝AgentConsole/backend）
- **AT-962-10-E-5**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-15-1）完成判定不被假資料抬高：RTM 諮詢性質不被當成獨立通過證據。
  - Given RTM 為 100 但 FSM 為 RTM_VERIFY
  - When GET `/kanban`
  - Then `regression.done` 為 false；`rtm.advisory` 為 true
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_10_E_5*"（cwd＝AgentConsole/backend）
- **AT-962-14-8**（JUnit｜`ResearchKanbanApiIT`｜Integration｜AC-R2P-18-2）決定入庫：review_requests 的 decided_by、decided_at、comment 與 audit_log 一列；不寫 research_gate_decisions。
  - Given 一筆 PENDING 待審；ADMIN 或 OPERATOR 憑證
  - When POST 既有 `/executions/{runId}/review/{id}`
  - Then 204；review_requests 三欄已填；`audit_log` 新增一列；`research_gate_decisions` 列數不變
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchKanbanApiIT.AT_962_14_8*"（cwd＝AgentConsole/backend）
- **AT-962-15-6**（JUnit｜`ResearchScrApiIT`｜Integration｜AC-R2P-19-1、AC-R2P-19-5）console-api 的 evidenceUrl：ScrOpenRequest 選填，轉送 Bridge 的 evidence_url，ScrDto 回傳。
  - Given 迷你 Bridge；請求 evidenceUrl 為缺、合法 https、500 字元、501 字元、`http://`、`javascript:`、空字串
  - When OPERATOR POST `/scr`
  - Then 合法者轉送 `evidence_url` 並在回應與 GET 列表出現 `evidenceUrl`；501 字元、`http://`、`javascript:` 為 422 `invalid_request`（`violations[{field:evidenceUrl, rule:not_https｜too_long}]`）且 Bridge 請求 0；空字串視同缺；`reason` 欄不被附加『證據：』行（D-138 Q-12 取代 IFACE §7 的末行法）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchScrApiIT.AT_962_15_6*"（cwd＝AgentConsole/backend）
- **AT-962-17-7**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-1、AC-R2P-20-2）GET delivery/traceability 逐值對 Bridge 回放；VIEWER 可讀；rtm 欄形狀固定。
  - Given 迷你 Bridge 回放黃金檔
  - When VIEWER GET `/delivery/traceability`
  - Then 200；rows 與 totals 逐值等於回放（snake→camel）；`rtm` 鍵為 `runId`、`fullyCovered`、`acPct`、`advisory`（恆 true）；無 run 時 `rtm` 為 null
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_17_7*"（cwd＝AgentConsole/backend）
- **AT-962-19-1**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-3）ADMIN 建立 tag：轉送 Bridge 一次，請求欄位固定。
  - Given 迷你 Bridge；前置皆成立（FSM RELEASE_READY、RTM 閘、無 OPEN SCR）
  - When ADMIN POST `/delivery/tag`：`tagName=v1.2.3`、`message`、`push=true`
  - Then Bridge 收到一次 `:tag`，本文鍵為 `tag_name`、`message`、`push`、`create_github_release`、`approver`、`requested_by`；回應 201 含 `delivery`、`snapshot{relPath,sha256}`、`flow`、`fsmState`
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_19_1*"（cwd＝AgentConsole/backend）
- **AT-962-19-2**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-2、AC-R2P-20-3）服務層前置先於 Bridge：FSM 現態、RTM 閘、無 OPEN SCR，不合 409 且 Bridge 請求 0。
  - Given 三種夾具
  - When ADMIN POST
  - Then 409；`details.unmet` 為 `not_release_ready`、`rtm_below_100`、`scr_open`（SCR 開啟時 reason 為 `scr_open`）；Bridge 請求 0
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_19_2*"（cwd＝AgentConsole/backend）
- **AT-962-19-3**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-3）tagName 正規式與長度邊界：與 Bridge 同一份常數字面。
  - Given tagName 為 `v1.2.3`、`1.2.3-rc.1+b.5`、64 字元、65 字元、`1.2`、`01.2.3`、空
  - When ADMIN POST
  - Then 合法與 64 字元通過；其餘 422 `invalid_request`（`violations[{field:tagName, rule:not_semver}]`）；正規式字串與 `gitops.valid_semver` 逐字相等（AT-962-2-4 比對）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_19_3*"（cwd＝AgentConsole/backend）
- **AT-962-19-4**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-3）message 長度：200 通過、201 為 422。
  - Given message 為 200、201 字元
  - When ADMIN POST
  - Then 200 轉送；201 為 422 且 Bridge 請求 0
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_19_4*"（cwd＝AgentConsole/backend）
- **AT-962-19-5**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-3）Bridge 錯誤透傳：tag_exists、delivery_step_failed 保持 reason、HTTP 狀態與 details。
  - Given 迷你 Bridge 分別回 409 `tag_exists`、502 `delivery_step_failed`（`failure_step=push`）
  - When ADMIN POST
  - Then console-api 回相同 reason 與狀態碼；`details.failure_step` 原樣；reason 皆在 37 個四方鎖內
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_19_5*"（cwd＝AgentConsole/backend）
- **AT-962-19-6**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-02-5）稽核：每個 tag 寫入請求入 audit_log，且與 Bridge 事件同 trace_id。
  - Given 迷你 Bridge 回放含 `research.delivery` 事件
  - When ADMIN POST
  - Then `audit_log` 新增恰一列（含 subject、角色、路徑、trace id）；事件的 trace_id 與該列相同
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_19_6*"（cwd＝AgentConsole/backend）
- **AT-962-19-E-1**（JUnit｜`RbacIT`｜Integration｜AC-R2P-20-3）OPERATOR 呼叫 tag 回 403，Bridge 請求 0，無研究表變化。
  - Given OPERATOR 憑證
  - When POST `/delivery/tag`
  - Then 403 `ACCESS_DENIED`；Bridge 請求 0；`research_deliveries` 列數不變
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.security.RbacIT.AT_962_19_E_1*"（cwd＝AgentConsole/backend）
- **AT-962-19-E-2**（JUnit｜`RbacIT`｜Integration｜AC-R2P-20-3）VIEWER 呼叫 tag 回 403。
  - Given VIEWER 憑證
  - When POST `/delivery/tag`
  - Then 403 `ACCESS_DENIED`；Bridge 請求 0
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.security.RbacIT.AT_962_19_E_2*"（cwd＝AgentConsole/backend）
- **AT-962-19-E-3**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-3）createGithubRelease 為 true：422 release_not_supported，Bridge 請求 0；push 缺省為 false。
  - Given 請求變體
  - When ADMIN POST
  - Then `true` 為 422；缺省 push 時轉送 `push=false`
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_19_E_3*"（cwd＝AgentConsole/backend）
- **AT-962-19-E-4**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-3）Bridge 不可達：502，無部分狀態。
  - Given 迷你 Bridge 停機
  - When ADMIN POST
  - Then 502 `bridge_unreachable`；console-api 無研究表寫入
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_19_E_4*"（cwd＝AgentConsole/backend）
- **AT-962-19-E-5**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-3、AC-R2P-16-5）console-api 透傳 tag 的 422 digest_mismatch。
  - Given 迷你 Bridge 回 422 `digest_mismatch` 與 `details.drift[]`
  - When ADMIN POST `/delivery/tag`
  - Then 422、reason 與 `details.drift` 原樣；`research_deliveries` 零列；Bridge 請求恰一次（console-api 不自行比對 digest，由 Bridge 零信任判定）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_19_E_5*"（cwd＝AgentConsole/backend）
- **AT-962-19-E-6**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-3）console-api 直呼 `:tag` 於容器模式：透傳 422 route_unsupported_in_deployment（沿 P1 AT-961-22-5 體例），不自行猜測部署能力。
  - Given 迷你 Bridge 回 422 `route_unsupported_in_deployment` 與 `details.missing[repo_writable]`
  - When ADMIN POST `/delivery/tag`
  - Then console-api 回 422、reason 與 `details.missing` 原樣；`research_deliveries` 零列；Bridge 請求恰一次
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_19_E_6*"（cwd＝AgentConsole/backend）
- **AT-962-20-8**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-4）console-api：ADMIN 建 PR，只在此端點讀 research.github_token 放進本文 github_token。
  - Given 設定鍵有值與空；迷你 Bridge
  - When ADMIN POST `/delivery/pr`；再對 `/delivery/tag` 呼叫確認不帶 token
  - Then PR 請求本文含 `github_token`；tag 與其他研究端點本文無此鍵；回應與稽核不含 token；錯誤透傳同 AT-962-19-5
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_20_8*"（cwd＝AgentConsole/backend）
- **AT-962-20-E-1**（JUnit｜`RbacIT`｜Integration｜AC-R2P-20-4）OPERATOR 與 VIEWER 呼叫 pr 回 403，Bridge 請求 0。
  - Given 兩種憑證
  - When POST `/delivery/pr`
  - Then 皆 403 `ACCESS_DENIED`；Bridge 請求 0
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.security.RbacIT.AT_962_20_E_1*"（cwd＝AgentConsole/backend）
- **AT-962-20-E-2**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-4）bodyPreviewAck 為 false 或缺：422，Bridge 請求 0。
  - Given 請求變體
  - When ADMIN POST
  - Then 422 `invalid_request`；Bridge 請求 0
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_20_E_2*"（cwd＝AgentConsole/backend）
- **AT-962-21-7**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-20-5、AC-R2P-20-4）GET delivery 概覽逐欄：deliveries、snapshot、projectRoot、containerMode、preconditions。
  - Given 已有 tag 與 PR 各一；`research_route_decisions.target_path`；capabilities mode 為 mock-only 與非
  - When VIEWER GET `/delivery`
  - Then 鍵集合固定；`projectRoot` 等於 target_path；`containerMode` 等於 `mode==mock-only`；`preconditions` 含 `releaseReady`、`rtmFull`、`scrOpen`、`hasOrigin`、`ghAvailable`（未知為 null）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_21_7*"（cwd＝AgentConsole/backend）
- **AT-962-22-1**（JUnit｜`ResearchApiIT`｜Integration｜AC-R2P-02-4、AC-R2P-20-6）已交付專案 records/audit：missing 為空（R11 筆數至少 1；R10 與 R12 允許 0）。
  - Given 完成分流、簽核、tag 的專案（R7、R8、R11 有列）
  - When GET `/records/audit`
  - Then `missing` 為空陣列；R10 與 R12 為 0 筆不列入 missing
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_962_22_1*"（cwd＝AgentConsole/backend）
- **AT-962-22-2**（JUnit｜`ResearchApiIT`｜Integration｜AC-R2P-02-4）未交付專案口徑不變：missing 仍含 R11。
  - Given 已簽核未交付的專案
  - When GET `/records/audit`
  - Then `missing` 恰含 `R11`（沿 P1 口徑）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_962_22_2*"（cwd＝AgentConsole/backend）
- **AT-962-22-3**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-02-5）Release Tag 稽核：audit_log 一列與 research.delivery 事件同 trace_id，事件含 digest 與理由。
  - Given 成功建立 tag
  - When 查 `audit_log` 與 `research_events`
  - Then 兩者 trace_id 相同；事件 payload 鍵集合為 `{kind, ref, status, digest, reason, failure_step}`，`digest` 為追溯快照 sha256、`ref` 為 tag 名；理由存於 `research_deliveries.detail`
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_22_3*"（cwd＝AgentConsole/backend）
- **AT-962-22-4**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-02-5）SCG 登錄稽核：gates 請求入 audit_log，決定列的 audit_trace_id 與之對應。
  - Given ADMIN 登錄一次
  - When 查兩表
  - Then `audit_log` 一列；`research_gate_decisions.audit_trace_id` 等於其 trace id
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_22_4*"（cwd＝AgentConsole/backend）
- **AT-962-22-5**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-5、AC-R2P-20-3）交付列不可變與唯一：append-only 守衛、UNIQUE(research_id, kind, ref)。
  - Given 同研究專案的兩筆相同 (kind, ref)
  - When 插入、UPDATE、DELETE
  - Then 重複為 23505；UPDATE 與 DELETE 為類別 23；同 ref 不同 kind 可並存
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_962_22_5*"（cwd＝AgentConsole/backend）
- **AT-962-22-E-1**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-02-5）失敗的 tag（502）不產生 research_deliveries 列，但 audit_log 仍有一列。
  - Given 迷你 Bridge 回 502
  - When ADMIN POST tag
  - Then `research_deliveries` 列數不變；`audit_log` 新增一列
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_22_E_1*"（cwd＝AgentConsole/backend）
- **AT-962-22-E-2**（JUnit｜`ResearchDeliveryApiIT`｜Integration｜AC-R2P-02-5）重送冪等：同 (kind, ref) 不增列。
  - Given 已有 tag 列
  - When 重送
  - Then 列數不變
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDeliveryApiIT.AT_962_22_E_2*"（cwd＝AgentConsole/backend）
- **AT-962-22-E-3**（JUnit｜`ResearchApiIT`｜Integration｜AC-R2P-02-4）R10 為 0 筆的已交付專案仍通過完整率。
  - Given 無自癒嘗試的已交付專案
  - When GET `/records/audit`
  - Then `missing` 為空
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_962_22_E_3*"（cwd＝AgentConsole/backend）
- **AT-962-23-6**（JUnit｜`ResearchBridgeShapeTest`｜Integration｜AC-R2P-23-1）console-api 轉送七項：名稱取自 Bridge 的 CHECK_IDS，迷你 Bridge 回 7 項。
  - Given `BridgeSource.constants("CHECK_IDS", …)`；`MiniResearch.consistentReconcileChecks()` 補第七項
  - When POST `/reconcile`
  - Then `ReconcileResultDto.checks` 名稱序列等於 Bridge 常數；一項不漏（`ResearchApiIT.java:54` 與 `ResearchBridgeShapeTest.java:39,:58` 自動跟隨）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchBridgeShapeTest.AT_962_23_6*"（cwd＝AgentConsole/backend）
- **AT-962-24-1**（JUnit｜`ResearchReasonsTest`｜Unit｜AC-R2P-20-3）reason 由 35 增為 37：新增 tag_exists（409）、delivery_step_failed（502），四方集合相等。
  - Given `ErrorReasons.java` 新增兩個 `RESEARCH_` 常數；`ResearchErrorDocs`；`lib/domain/research.ts` 的 `RESEARCH_REASONS`；契約 §0.2；Architecture §11.1
  - When 跑 `ResearchReasonsTest`（`ALL_REASONS` 加 `P2_REASONS` 兩項；`hasSize(35)` 改 37，`:142`）
  - Then 後端與前端集合等於 37 個的 ALL；每個 reason 有 HTTP 狀態與文案；兩份 `*_ERRATUM_PENDING` 名單（`:60`、`:63`）加入兩項並以『缺列集合恰等於名單』雙向鎖住，勘誤落地後清空（⚖P2-14：前端常數實住 `lib/domain/research.ts:749`，非 PACKAGES 所稱的 `lib/api/reasons.ts`）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchReasonsTest.AT_962_24_1*"（cwd＝AgentConsole/backend）
- **AT-962-24-2**（JUnit｜`OpenApiIT`｜Integration｜AC-R2P-15-1、AC-R2P-20-3）OpenApiIT 計數：路徑 107 變 114、操作 124 變 131；研究路徑 30 變 37、操作 35 變 42、operationId 34 變 41、狀態碼表 35 變 42。
  - Given `OpenApiIT.java:170-171,:971,:979,:980,:999` 與 `EXPECTED`、`RESEARCH_OPERATION_IDS`、`RESEARCH_STATUS_CODES` 各加七項
  - When 跑 OpenApiIT
  - Then 自算法：新增路徑七條（`/kanban`、`/gates`、`/healing`、`/delivery`、`/delivery/tag`、`/delivery/pr`、`/delivery/traceability`；同路徑 GET 與 POST 合併計一）；新增操作七個（`getResearchKanban`、`registerResearchGate`、`getResearchHealing`、`getResearchDelivery`、`createResearchTag`、`createResearchPr`、`getResearchTraceability`）；以實際新增數為準並於證據註明差異；`:healing-sync` 不入 OpenAPI
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.config.OpenApiIT.AT_962_24_2*"（cwd＝AgentConsole/backend）
- **AT-962-24-3**（JUnit｜`OpenApiIT`｜Integration｜AC-R2P-20-3）七個新操作的狀態碼表逐一登記：gates、tag、pr 含 403、404、409、422、502，讀端含 401、403、404。
  - Given `ErrorResponseDocumentation` 的逐操作條目
  - When 跑 OpenApiIT 的狀態碼斷言
  - Then 每個新操作的狀態碼集合等於登記表；缺任一操作即紅（`ErrorResponseDocumentation.java:87,:151` 體例）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.config.OpenApiIT.AT_962_24_3*"（cwd＝AgentConsole/backend）
- **AT-962-24-4**（JUnit｜`RbacIT`｜Integration｜AC-R2P-15-6、AC-R2P-20-3、AC-R2P-20-4）RBAC 矩陣：gates、tag、pr 為 ADMIN 專屬（OPERATOR 與 VIEWER 皆 403）；kanban、healing、delivery、traceability 的 GET 為 VIEWER 以上。
  - Given `RbacIT.java:459-478` 的 matcher 清單（現已含三條 ADMIN 規則）與 `:499` 的探針清單
  - When 跑 RbacIT
  - Then ADMIN 通過且迷你 Bridge 到達恰一次；GET 四端點 VIEWER 200；`SecurityConfig.java:103-111`（P2 相關三條在 :107-109）零 diff（規則已預登，若 RbacIT 揭露缺口才回報）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.security.RbacIT.AT_962_24_4*"（cwd＝AgentConsole/backend）
- **AT-962-24-E-1**（JUnit｜`ResearchReasonsTest`｜Unit｜AC-R2P-20-3）RESEARCH_ 前綴：新常數不污染 REASONS 集合鎖。
  - Given `IssueReasonsContractTest`、`BackupReasonsContractTest`
  - When 跑兩個集合鎖
  - Then 兩者仍綠；`lib/api/reasons.ts` 零 diff
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchReasonsTest.AT_962_24_E_1*"（cwd＝AgentConsole/backend）
- **AT-962-24-E-2**（JUnit｜`ResearchReasonsTest`｜Unit｜AC-R2P-20-3）未登記四方鎖的字面不得流出：Bridge 新模組的 reason 字面皆屬 37 個。
  - Given 掃描 `inner_gates.py`、`delivery.py`、`healing.py`、`routers/research_deliver.py` 的 reason 字面
  - When 與 ALL_REASONS 比對
  - Then 字面集合為 ALL_REASONS 的子集（D-136）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchReasonsTest.AT_962_24_E_2*"（cwd＝AgentConsole/backend）
- **AT-962-26-1**（JUnit｜`ResearchArchTest`｜Unit｜AC-R2P-02-10）字串掃描：console-api 新類對 research_* 零 INSERT、UPDATE、DELETE。
  - Given `backend/src/main/java/com/aisdlc/console/**`
  - When 跑 ResearchArchTest 的寫入掃描（`git grep` 同判準：H30 於 HEAD 為零命中）
  - Then 新增的 Controller、Service、ReadAdapter 皆零命中；ReadAdapter 的 SQL 只含 SELECT
  - 判定：gradlew test --tests "com.aisdlc.console.architecture.ResearchArchTest.AT_962_26_1*"（cwd＝AgentConsole/backend）
- **AT-962-26-4**（JUnit｜`ResearchArchTest`｜Unit｜AC-R2P-02-10）新 Java 類符合 ArchUnit 層次與命名；masker 在 persistence 層。
  - Given `ResearchArchTest`
  - When 跑
  - Then 全綠；Controller 不 import `JdbcClient`；`HealingExcerptMasker` 不被 domain 依賴
  - 判定：gradlew test --tests "com.aisdlc.console.architecture.ResearchArchTest.AT_962_26_4*"（cwd＝AgentConsole/backend）
- **AT-962-26-E-2**（JUnit｜`OpenApiIT`｜Integration｜AC-R2P-02-10）healing-sync 為內部端點：不在 console-api 路由與 OpenAPI。
  - Given OpenAPI paths 與 RequestMapping
  - When 掃描 `healing-sync`
  - Then 零命中
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.config.OpenApiIT.AT_962_26_E_2*"（cwd＝AgentConsole/backend）

### 3.3 frontend（vitest；徑②）

- **AT-962-4-7**（vitest｜`components/domain/research/GateRegisterDialog.test.tsx`｜Unit｜AC-R2P-15-6）GateRegisterDialog 正控：三個 gate 選項、PR_REVIEW 顯示審查者獨立聲明與報告參照、勾選後送出的請求本文、成功與升級呈現。
  - Given `Providers` 與 `stubApi`；ADMIN；kanban 夾具為回歸驗收欄；stubApi 回 `{gateDecisionId, nextState:"RTM_VERIFY", escalated:false}` 與 `{nextState:"ESCALATION_FINAL", escalated:true}`
  - When 選 PR_REVIEW、勾『我確認審查者未參與規格與實作』、填理由與報告參照、送出；再以 escalated 回應重送
  - Then POST `/gates` 本文為 `{gate, result, reason, reviewReportRef, reviewerIndependent:true}`；成功顯示 `nextState` 並使 kanban 失效重抓；escalated 為真時顯示『已升級，等待人工處理』並引導至決策彈窗（ESCALATION 的恢復指令只顯示、不提供恢復按鈕）；文字純文字渲染
  - 判定：npx vitest run components/domain/research/GateRegisterDialog.test.tsx -t AT_962_4_7（cwd＝AgentConsole/frontend）
- **AT-962-4-8**（vitest｜`components/domain/research/GateRegisterDialog.test.tsx`｜Unit｜AC-R2P-15-6）GateRegisterDialog：RELEASE_READY 只有 FAIL 選項、FAIL 必填理由計數器、SCR_OPEN 時停用。
  - Given ADMIN；gate 選 RELEASE_READY；另一情境 `scrOpen=true`
  - When 渲染並檢視結果選項與送出條件
  - Then RELEASE_READY 的結果選項只有 FAIL（PASS 不渲染，並說明『PASS 由建立 Tag 完成』）；理由欄顯示 1 至 500 計數；`scrOpen=true` 時整個對話框的送出停用並顯示 `BUILD_DISABLED_TEXT.SCR_OPEN` 文案
  - 判定：npx vitest run components/domain/research/GateRegisterDialog.test.tsx -t AT_962_4_8（cwd＝AgentConsole/frontend）
- **AT-962-4-E-6**（vitest｜`components/domain/research/GateRegisterDialog.test.tsx`｜Unit｜AC-R2P-15-6）未勾審查者獨立聲明不可送：PR_REVIEW 送出鈕停用、請求數為 0；其餘 gate 不要求。
  - Given ADMIN；gate 選 PR_REVIEW、不勾聲明；另測 RTM_VERIFY 與 RELEASE_READY
  - When 嘗試送出
  - Then PR_REVIEW 未勾時送出鈕 `disabled`、`POST /gates` 為 0 次並顯示聲明必填說明；RTM_VERIFY 與 RELEASE_READY 不要求勾選即可送
  - 判定：npx vitest run components/domain/research/GateRegisterDialog.test.tsx -t AT_962_4_E_6（cwd＝AgentConsole/frontend）
- **AT-962-4-E-7**（vitest｜`components/domain/research/GateRegisterDialog.test.tsx`｜Unit｜AC-R2P-15-6）FAIL 無理由不可送；理由 500／501 與報告參照 300／301 邊界。
  - Given ADMIN；result 選 FAIL
  - When 理由為空、500 字元、501 字元；報告參照 300、301 字元
  - Then 空與 501 字元、301 字元時送出停用並顯示錯誤；500 與 300 字元可送；PASS 時理由可空
  - 判定：npx vitest run components/domain/research/GateRegisterDialog.test.tsx -t AT_962_4_E_7（cwd＝AgentConsole/frontend）
- **AT-962-4-E-8**（vitest｜`components/domain/research/GateRegisterDialog.test.tsx`｜Unit｜AC-R2P-15-6）非 ADMIN（OPERATOR、VIEWER）：登錄鈕停用且 title 為權限不足，請求數為 0。
  - Given OPERATOR 與 VIEWER 角色
  - When 渲染並嘗試開啟、送出
  - Then 觸發鈕 `disabled`、`title="權限不足"`；`POST /gates` 為 0 次
  - 判定：npx vitest run components/domain/research/GateRegisterDialog.test.tsx -t AT_962_4_E_8（cwd＝AgentConsole/frontend）
- **AT-962-4-E-9**（vitest｜`components/domain/research/GateRegisterDialog.test.tsx`｜Unit｜AC-R2P-15-6）錯誤文案：409 fsm_state_conflict（unmet 逐項中文）、409 scr_open、422 digest_mismatch（列出漂移路徑並引導發起 SCR）、502 取 RESEARCH_REASON_TEXT；403 `ACCESS_DENIED` 取通用權限不足文案（非研究 reason）。
  - Given stubApi 依序回上述五種錯誤（409 帶 `details.unmet:[tasks_incomplete, rtm_below_100]`；422 帶 `details.drift[]`）
  - When 送出
  - Then 顯示登記表文案（不內嵌第二份）；unmet 逐項以中文列出；digest_mismatch 顯示每個漂移 `path` 並提供『發起 SCR』鈕（開 ScrRequestDialog，`sourceKind` 預填 `SCG4`）
  - 判定：npx vitest run components/domain/research/GateRegisterDialog.test.tsx -t AT_962_4_E_9（cwd＝AgentConsole/frontend）
- **AT-962-11-1**（vitest｜`lib/domain/research.test.ts`｜Unit｜AC-R2P-15-1）kanbanColumns 純函式窮舉表：五欄完成判定的每個邊界。
  - Given `lib/domain/research.ts` 新增的 `kanbanColumns(dto)`；輸入矩陣覆蓋 AT-962-10-1～10-5 的邊界
  - When 逐列餵入
  - Then 輸出的 done 與後端判定逐列相同；FSM 衍生欄 null 時 done 為 `unknown` 而不是 false（不猜）
  - 判定：npx vitest run lib/domain/research.test.ts -t AT_962_11_1（cwd＝AgentConsole/frontend）
- **AT-962-11-2**（vitest｜`components/domain/research/KanbanBoard.test.tsx`｜Unit｜AC-R2P-15-1）渲染五欄、順序固定、計數等於資料。
  - Given `Providers` 與 `stubApi`；kanban 夾具
  - When 渲染 KanbanBoard
  - Then 欄序為 Task 拆解、測試規格產生、程式碼實作、自癒修復、回歸驗收；每欄計數與狀態文字等於夾具；RTM 欄標『諮詢視圖』
  - 判定：npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_2（cwd＝AgentConsole/frontend）
- **AT-962-11-3**（vitest｜`components/domain/research/KanbanBoard.test.tsx`｜Unit｜AC-R2P-15-3）SSE 到客戶端至 DOM 更新不超過 500ms（假計時器、假 EventSource，不用牆鐘）。
  - Given `vi.useFakeTimers()`；假 `EventSource` 送 `status-change` 幀；重抓回新值
  - When 送幀後 `advanceTimersByTime(100)` 與 `(499)`，以幀時戳與 `performance.now()` 差量測
  - Then 100ms 內發出 kanban 重抓；499ms 內 DOM 已反映新值；量測差值不大於 500；常數 500 與 100 取自 `lib/domain/research.ts` 單一常數；負控子情境：把重抓與渲染人為延後 501ms 時，量測差值為 501，本 AT 的斷言函式回報違規（證明 500 上限咬人）
  - 判定：npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_3（cwd＝AgentConsole/frontend）
- **AT-962-11-4**（vitest｜`components/domain/research/KanbanBoard.test.tsx`｜Unit｜AC-R2P-15-3）三條串流任一幀都觸發 kanban 失效重抓；同一去抖窗內多幀合併為一次。
  - Given 研究專案串流（`research.step`、`research.gate`、`research.delivery`）與 run 串流（`status-change`、`review-request`、`alert`）
  - When 各送一幀；再於 99ms 內連送三幀
  - Then 每種幀都引發重抓；去抖窗內三幀只重抓一次
  - 判定：npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_4（cwd＝AgentConsole/frontend）
- **AT-962-11-5**（vitest｜`components/domain/research/KanbanBoard.test.tsx`｜Unit｜AC-R2P-15-3）斷線回補：replay_gap 幀或重連後以 REST 全量重抓，並帶 Last-Event-ID。
  - Given 假 EventSource 斷線再重連；送 `replay_gap`
  - When 觸發重連
  - Then 重連請求帶 Last-Event-ID；收到 replay_gap 即全量重抓 kanban；畫面不顯示過期值
  - 判定：npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_5（cwd＝AgentConsole/frontend）
- **AT-962-11-6**（vitest｜`components/domain/research/KanbanBoard.test.tsx`｜Unit｜AC-R2P-15-5、AC-R2P-01-5）每欄深連結：開啟執行中心與監控中心，帶 researchId；停用規則與文案取登記處。
  - Given 已綁 console 專案、未綁、SCR_OPEN 三種
  - When 渲染並讀連結
  - Then href 為 `/projects/<id>/execute?researchId=<uuid>` 與 `/projects/<id>/monitor?researchId=<uuid>`；未綁或 SCR_OPEN 時停用並顯示 `BUILD_DISABLED_TEXT` 對應文案；用 `<Link>` 導向，不呼叫新端點
  - 判定：npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_6（cwd＝AgentConsole/frontend）
- **AT-962-11-7**（vitest｜`components/domain/research/KanbanBoard.test.tsx`｜Unit｜AC-R2P-15-4）Bridge 不可達態：橫幅加快照時間加未知徽章，不渲染空看板，不把快照當即時。
  - Given kanban 夾具 `bridgeReachable=false`、`stale=true`、`snapshotAt`
  - When 渲染
  - Then 橫幅文字為『Engine Bridge 無法連線，以下為 <snapshotAt> 的 DB 快照』；FSM 衍生欄顯示『未知』徽章；仍顯示 DB 欄位；有 `data-stale=true` 標記；沒有任何欄顯示『已完成』於未知欄
  - 判定：npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_7（cwd＝AgentConsole/frontend）
- **AT-962-11-8**（vitest｜`components/domain/research/KanbanBoard.test.tsx`｜Unit｜AC-R2P-15-2）靜態判準：KanbanBoard 只用 Link 或既有 endpoints 函式，不 import 新的執行控制端點函式，不直呼 fetch。
  - Given `readFileSync` 讀 `KanbanBoard.tsx` 與 `KanbanColumn.tsx`
  - When 正規式掃描
  - Then 無 `fetch(`、無新增的 execute／pause／resume／cancel 端點函式匯入；動作鈕只連 `/projects/{id}/execute`、`/executions/{runId}/{pause,resume,cancel}`、`/executions/{runId}/review/{id}` 這些既有路徑
  - 判定：npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_8（cwd＝AgentConsole/frontend）
- **AT-962-11-E-1**（vitest｜`components/domain/research/KanbanBoard.test.tsx`｜Unit｜AC-R2P-15-1）VIEWER：看板可讀，寫入類動作停用，title 為權限不足。
  - Given VIEWER 角色
  - When 渲染
  - Then 『登錄 SCG』與『發起 SCR』鈕 `disabled` 且 `title` 為『權限不足（唯讀角色）』；導覽連結仍可點
  - 判定：npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_E_1（cwd＝AgentConsole/frontend）
- **AT-962-11-E-2**（vitest｜`components/domain/research/KanbanBoard.test.tsx`｜Unit｜AC-R2P-15-4）缺值不猜：FSM 欄為 null 時顯示未知，不顯示 0 或完成。
  - Given 夾具把 `tcs.fsmState` 等設為 null 並帶 unknown
  - When 渲染
  - Then 對應欄文字為『未知』；沒有『0』與『完成』字樣
  - 判定：npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_E_2（cwd＝AgentConsole/frontend）
- **AT-962-11-E-3**（vitest｜`components/domain/research/KanbanBoard.test.tsx`｜Unit｜AC-R2P-15-3）去抖邊界：99ms 內合併、101ms 後各自觸發。
  - Given 假計時器
  - When 兩幀相隔 99ms 與 101ms
  - Then 前者重抓一次、後者兩次
  - 判定：npx vitest run components/domain/research/KanbanBoard.test.tsx -t AT_962_11_E_3（cwd＝AgentConsole/frontend）
- **AT-962-12-1**（vitest｜`components/domain/research/HealingMonitor.test.tsx`｜Unit｜AC-R2P-16-2）每任務顯示嘗試次數對上限、最近失敗摘錄、歸因與補丁結果；數值等於資料。
  - Given healing 夾具（含 attribution 與 patchResult 為 null 的列）
  - When 渲染 HealingMonitor
  - Then 顯示『嘗試 n／上限』（上限取 `maxRetries`）；摘錄為純文字；歸因與補丁結果為 null 時顯示『引擎未提供』
  - 判定：npx vitest run components/domain/research/HealingMonitor.test.tsx -t AT_962_12_1（cwd＝AgentConsole/frontend）
- **AT-962-12-2**（vitest｜`components/domain/research/HealingMonitor.test.tsx`｜Unit｜AC-R2P-16-2）純文字：摘錄含 HTML 與 on* 屬性時 DOM 無元素節點。
  - Given 摘錄含 `<script>`、`<img src=x onerror=...>`
  - When 渲染
  - Then 容器內 script 與 img 為 0；任一元素無 on* 屬性；哨兵呼叫 0
  - 判定：npx vitest run components/domain/research/HealingMonitor.test.tsx -t AT_962_12_2（cwd＝AgentConsole/frontend）
- **AT-962-12-3**（vitest｜`components/domain/research/HealingMonitor.test.tsx`｜Unit｜AC-R2P-16-3）耗盡升級：escalated 列顯示已升級徽章並連到決策彈窗，不再提供自動重試。
  - Given 一個 escalated 任務，pendingReviews 有對應項
  - When 渲染並點徽章
  - Then 顯示『已升級，等待人工決定』；點擊開 DecisionModal（同一殼）；沒有『重試』按鈕直接呼叫引擎（重試走彈窗的既有審核動作）
  - 判定：npx vitest run components/domain/research/HealingMonitor.test.tsx -t AT_962_12_3（cwd＝AgentConsole/frontend）
- **AT-962-12-4**（vitest｜`components/domain/research/HealingMonitor.test.tsx`｜Unit｜AC-R2P-16-5、AC-R2P-19-1）規格漂移列：顯示引導並預填 SCR 發起。
  - Given healing 夾具某列 `specChangeForbidden=true`
  - When 渲染並點『發起 SCR』
  - Then 顯示『補丁觸及凍結規格，請發起 SCR』；開 ScrRequestDialog 且 `sourceKind` 預填 `HEALING_FAILED`
  - 判定：npx vitest run components/domain/research/HealingMonitor.test.tsx -t AT_962_12_4（cwd＝AgentConsole/frontend）
- **AT-962-12-5**（vitest｜`components/domain/research/HealingMonitor.test.tsx`｜Unit｜AC-R2P-16-1）日誌落後提示。
  - Given 夾具落後 3 筆與 0 筆
  - When 渲染
  - Then 落後時顯示『日誌落後 3 筆』；0 筆不顯示
  - 判定：npx vitest run components/domain/research/HealingMonitor.test.tsx -t AT_962_12_5（cwd＝AgentConsole/frontend）
- **AT-962-12-E-1**（vitest｜`components/domain/research/HealingMonitor.test.tsx`｜Unit｜AC-R2P-16-2）空狀態不顯示假進度。
  - Given rows 為空
  - When 渲染
  - Then 顯示『目前沒有自癒嘗試』；沒有『0／3』字樣
  - 判定：npx vitest run components/domain/research/HealingMonitor.test.tsx -t AT_962_12_E_1（cwd＝AgentConsole/frontend）
- **AT-962-12-E-2**（vitest｜`components/domain/research/HealingMonitor.test.tsx`｜Unit｜AC-R2P-16-5）VIEWER：發起 SCR 鈕停用。
  - Given VIEWER 角色與漂移列
  - When 渲染
  - Then 鈕 `disabled`、title 為權限不足
  - 判定：npx vitest run components/domain/research/HealingMonitor.test.tsx -t AT_962_12_E_2（cwd＝AgentConsole/frontend）
- **AT-962-12-E-3**（vitest｜`components/domain/research/HealingMonitor.test.tsx`｜Unit｜AC-R2P-16-2）摘錄長度與版面：300 字元摘錄不撐破容器。
  - Given 300 字元不含空白的摘錄
  - When 渲染（含 CSS 類名斷言）
  - Then 容器具換行與溢出處理類別；文字不被截成 299
  - 判定：npx vitest run components/domain/research/HealingMonitor.test.tsx -t AT_962_12_E_3（cwd＝AgentConsole/frontend）
- **AT-962-13-1**（vitest｜`components/domain/research/TerminalPane.test.tsx`｜Unit｜AC-R2P-17-1）展開時以 useRunStream 餵 LiveLogCard；收合時仍訂閱，開合不重連。
  - Given 假 EventSource；`TerminalPane` props `runId`
  - When 展開、收合、再展開
  - Then 整個過程 EventSource 實例數為 1、未被關閉；收合時畫面不渲染 LiveLogCard 但串流狀態保留；再展開時顯示收合期間累積的行
  - 判定：npx vitest run components/domain/research/TerminalPane.test.tsx -t AT_962_13_1（cwd＝AgentConsole/frontend）
- **AT-962-13-2**（vitest｜`components/domain/research/TerminalPane.test.tsx`｜Unit｜AC-R2P-17-2）靜態判準：與執行中心共用同一日誌元件與串流客戶端，無第二份實作。
  - Given `readFileSync` 讀 `TerminalPane.tsx` 與 `components/domain/research/**` 的**非測試原始碼**（排除 `*.test.tsx`、`*.test.ts`、`tests/`），先剝除註解（行註解與區塊註解）再掃描；正規式以字串拼接組成，使測試檔自身不命中（沿 P0 R-3 修法；或沿 `EvidenceTimeline.test.tsx` 的 `renderViolations` 掃描函式）
  - When 正規式掃描
  - Then `TerminalPane.tsx` 含 `from "@/hooks/useRunStream"` 與 `from "@/components/domain/execute/LiveLogCard"`；非測試原始碼（剝註解後）零命中 `WebSocket`、`new EventSource`、`dangerouslySetInnerHTML`、`lib/sse/`（現檔註解 `MermaidBlock.tsx:12`、`RouteActionList.tsx:5`、`StudioPanel.tsx:17` 與 `EvidenceTimeline.test.tsx` 的字面因剝註解與排除測試檔而不命中）；全 research 目錄的非測試碼內這兩個匯入只出現在 `TerminalPane.tsx`（PRD 路徑 `lib/sse/` 實為 `lib/api/sse.ts`，D-140 #3）
  - 判定：npx vitest run components/domain/research/TerminalPane.test.tsx -t AT_962_13_2（cwd＝AgentConsole/frontend）
- **AT-962-13-3**（vitest｜`components/domain/research/TerminalPane.test.tsx`｜Unit｜AC-R2P-17-3）純文字哨兵：script、img、on* 屬性與哨兵呼叫皆為 0，ANSI 序列不殘留。
  - Given log 行含 `<script>alert(1)</script>`、`\x1b[31mRED\x1b[0m`、`<img src=x onerror="__sentinel()">`
  - When 渲染
  - Then 容器內 `script, img` 為 0、含 on* 屬性元素 0、`__sentinel` 呼叫 0、可見文字不含 `\x1b[`；本包不改 LiveLogCard（若不達標以勘誤回報）
  - 判定：npx vitest run components/domain/research/TerminalPane.test.tsx -t AT_962_13_3（cwd＝AgentConsole/frontend）
- **AT-962-13-4**（vitest｜`components/domain/research/TerminalPane.test.tsx`｜Unit｜AC-R2P-17-4）run 結束後以 REST 回補：steps?afterSeq 分頁補齊，與結束前一致。
  - Given run 終態；steps 夾具分三頁
  - When 開啟窗格
  - Then 依序以 afterSeq 取頁直到空頁；顯示的行序列與結束前串流收到的行逐行相等
  - 判定：npx vitest run components/domain/research/TerminalPane.test.tsx -t AT_962_13_4（cwd＝AgentConsole/frontend）
- **AT-962-13-5**（vitest｜`components/domain/research/TerminalPane.test.tsx`｜Unit｜AC-R2P-17-1）開合狀態僅存瀏覽器：鍵 research.terminal.open，預設收合，localStorage 例外時仍可用。
  - Given localStorage 正常與拋例外兩種
  - When 開、重載
  - Then 狀態保留；拋例外時以預設收合渲染且不崩潰；開合狀態不進任何 API 請求
  - 判定：npx vitest run components/domain/research/TerminalPane.test.tsx -t AT_962_13_5（cwd＝AgentConsole/frontend）
- **AT-962-13-6**（vitest｜`components/domain/research/TerminalPane.test.tsx`｜Unit｜AC-R2P-17-1）log 幀到達至顯示不超過 500ms（假計時器）。
  - Given 假 EventSource 送 log 幀
  - When advanceTimersByTime(499)
  - Then DOM 已含新行；量測差值不大於 500；負控子情境：人為延後 501ms 時量測差值超過 500、斷言回報違規
  - 判定：npx vitest run components/domain/research/TerminalPane.test.tsx -t AT_962_13_6（cwd＝AgentConsole/frontend）
- **AT-962-13-7**（vitest｜`components/domain/research/TerminalPane.test.tsx`｜Unit｜AC-R2P-17-1）斷線以 Last-Event-ID 回補。
  - Given 假 EventSource 斷線重連
  - When 重連
  - Then 請求帶 Last-Event-ID；補回缺行、不重複顯示
  - 判定：npx vitest run components/domain/research/TerminalPane.test.tsx -t AT_962_13_7（cwd＝AgentConsole/frontend）
- **AT-962-13-E-1**（vitest｜`components/domain/research/TerminalPane.test.tsx`｜Unit｜AC-R2P-17-2）靜態掃描負控：夾具原始碼含 WebSocket、new EventSource、dangerouslySetInnerHTML 皆被判違規。
  - Given 三份違規夾具字串與一份合法夾具
  - When 餵掃描函式
  - Then 三者各被判違規；合法夾具通過（掃描能咬人）
  - 判定：npx vitest run components/domain/research/TerminalPane.test.tsx -t AT_962_13_E_1（cwd＝AgentConsole/frontend）
- **AT-962-13-E-2**（vitest｜`components/domain/research/TerminalPane.test.tsx`｜Unit｜AC-R2P-17-1）runId 為 null：顯示尚無執行批次，不訂閱。
  - Given `runId=null`
  - When 渲染
  - Then 顯示『尚無執行批次』；EventSource 實例數為 0
  - 判定：npx vitest run components/domain/research/TerminalPane.test.tsx -t AT_962_13_E_2（cwd＝AgentConsole/frontend）
- **AT-962-14-1**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-2）類型 (b) 自癒耗盡：ESCALATED 待審開彈窗，四個決定按鈕由 allowedDecisions 驅動。
  - Given kanban.pendingReviews 一筆 kind 為 ESCALATED、allowedDecisions 為 APPROVE、REJECT、RETRY、SKIP
  - When 渲染
  - Then 彈窗顯示原因與四顆按鈕（通過、拒絕、重試、跳過）；按鈕集合恰等於 allowedDecisions
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_1（cwd＝AgentConsole/frontend）
- **AT-962-14-2**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-2）類型 (c) Agent 請求審核：kind 非 ESCALATED 的待審與 review-request 幀同殼處理。
  - Given 待審 kind 為其他；SSE `review-request` 幀
  - When 渲染並送幀
  - Then 同一彈窗殼；按鈕依 allowedDecisions；不另開第二種元件
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_2（cwd＝AgentConsole/frontend）
- **AT-962-14-3**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-2）類型 (d) 重大架構選擇：alert ESCALATION 幀與 review-request 皆可觸發；去重鍵 reviewId，無則用 alert 幀 seq；Console 不判斷何謂重大。
  - Given 兩種幀各一
  - When 送幀
  - Then 皆開彈窗；去重鍵如述；沒有任何『重大性』判斷程式（靜態掃描無相關詞彙）
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_3（cwd＝AgentConsole/frontend）
- **AT-962-14-4**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-2）決定送出走既有端點，不寫 research gates。
  - Given stubApi；選 RETRY 並填理由
  - When 按確認
  - Then POST `/api/v1/executions/{runId}/review/{reviewId}`、body 為 `{decision, comment}`；204 後關窗並使 kanban 失效；不呼叫 `/gates`
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_4（cwd＝AgentConsole/frontend）
- **AT-962-14-5**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-3）稍後處理：只關窗並以 sessionStorage 記 key，待辦仍在列表與頂列徽章，重新整理後仍在。
  - Given sessionStorage 鍵 `research.decision.snoozed`（本檔類推，⚖P2-10）；kanban 兩次載入
  - When 按『稍後處理』再重載
  - Then 窗關閉且本分頁不再自動彈出同 key；`pendingReviews` 仍列該項、步驟 4 待辦列仍有；不呼叫 `GET /signoffs/pending`；不呼叫任何決定端點
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_5（cwd＝AgentConsole/frontend）
- **AT-962-14-6**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-3）去重：SSE 重播的重複幀同 key 只出現一個彈窗；重新整理後由 pendingReviews 重建。
  - Given 同 reviewId 的 review-request 幀連送三次
  - When 送幀並重載
  - Then 彈窗 DOM 只有一個；重載後以 pendingReviews 重建且仍只有一個
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_6（cwd＝AgentConsole/frontend）
- **AT-962-14-7**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-2）單一彈窗殼：research 目錄不得出現第二個彈窗殼，並重用 SddEscalationBlock。
  - Given 靜態掃描 `components/domain/research/**`
  - When 掃描 Dialog 殼定義與 `SddEscalationBlock` 匯入處
  - Then 決策彈窗殼恰一個（`DecisionModal`，或擴充既有殼並由其委派）；P0 類型 (a) 仍重用 `SddEscalationBlock`
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_7（cwd＝AgentConsole/frontend）
- **AT-962-14-E-1**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-2）VIEWER：可讀內容，決定鈕全停用，title 為權限不足。
  - Given VIEWER 角色
  - When 渲染
  - Then 所有決定鈕 `disabled`、`title="權限不足"`；內容可讀；送出請求 0
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_E_1（cwd＝AgentConsole/frontend）
- **AT-962-14-E-2**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-2）allowedDecisions 以外的按鈕不渲染。
  - Given allowedDecisions 只有 APPROVE、REJECT
  - When 渲染
  - Then 沒有重試與跳過按鈕
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_E_2（cwd＝AgentConsole/frontend）
- **AT-962-14-E-3**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-2）他人已決定：決定端點回 409 或 404 時顯示錯誤並重抓 pendingReviews，不重複送出。
  - Given stubApi 回 409
  - When 按確認兩次
  - Then 顯示錯誤文字；重抓一次；POST 次數為 1
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_E_3（cwd＝AgentConsole/frontend）
- **AT-962-14-E-4**（vitest｜`components/domain/research/DecisionModal.test.tsx`｜Unit｜AC-R2P-18-2）無逾時自動處理：時間前進 72 小時仍無自動決定請求。
  - Given 假計時器；彈窗開著
  - When advanceTimersByTime(72 小時)
  - Then 決定端點請求 0；彈窗仍在
  - 判定：npx vitest run components/domain/research/DecisionModal.test.tsx -t AT_962_14_E_4（cwd＝AgentConsole/frontend）
- **AT-962-15-1**（vitest｜`components/domain/research/ScrRequestDialog.test.tsx`｜Unit｜AC-R2P-19-1）發起入口：看板與步驟 4 頁頂的『發起規格變更（SCR）』，OPERATOR 以上可用。
  - Given OPERATOR、ADMIN、VIEWER 三角色
  - When 渲染看板與步驟 4 頁頂
  - Then OPERATOR 與 ADMIN 可點；VIEWER 停用且 title 為權限不足；兩處入口同一元件
  - 判定：npx vitest run components/domain/research/ScrRequestDialog.test.tsx -t AT_962_15_1（cwd＝AgentConsole/frontend）
- **AT-962-15-2**（vitest｜`components/domain/research/ScrRequestDialog.test.tsx`｜Unit｜AC-R2P-19-1、AC-R2P-19-5）表單欄位齊備與預填：kind、sourceKind、reason 計數器、reasonClass 中文五值、affectedSections 多選、證據連結。
  - Given 自看板 SCG-4 FAIL 開、自自癒監視器開、自頁頂開
  - When 渲染對話框
  - Then kind 有 MINOR 與 MAJOR 各自後果說明；sourceKind 依入口預填為 `SCG4`、`HEALING_FAILED`、`HUMAN`；reasonClass 五個中文選項（PRD 缺漏證據、AC 模糊、需求變更、技術不可行、其他）；affectedSections 選項取自凍結 PRD 章節與 AC；證據連結為選填欄
  - 判定：npx vitest run components/domain/research/ScrRequestDialog.test.tsx -t AT_962_15_2（cwd＝AgentConsole/frontend）
- **AT-962-15-3**（vitest｜`components/domain/research/ScrRequestDialog.test.tsx`｜Unit｜AC-R2P-19-1、AC-R2P-19-4、AC-R2P-19-7）送出與結果：202 顯示已發起；MAJOR 導向後繼專案；HEALING_FAILED 只顯示可複製指令。
  - Given stubApi：kind MINOR 回 202；MAJOR 回 `successorResearchId`；HEALING_FAILED 回 200 與 `recovery{target,powershell,posix}`
  - When 分別送出
  - Then MINOR 顯示『SCR 已發起』並使游標重抓；MAJOR 路由導向 `/research/<successorResearchId>`；HEALING_FAILED 顯示 `CopyCommand`（兩平台指令）且不顯示『已發起』成功態
  - 判定：npx vitest run components/domain/research/ScrRequestDialog.test.tsx -t AT_962_15_3（cwd＝AgentConsole/frontend）
- **AT-962-15-4**（vitest｜`components/domain/research/ScrRequestDialog.test.tsx`｜Unit｜AC-R2P-19-5、AC-R2P-19-6）錯誤回顯：422 violations 逐筆回到欄位；scr_open、scr_limit、fsm_state_conflict 顯示登記文案。
  - Given stubApi 回 422（多違規）、409 三種 reason
  - When 送出
  - Then 每筆 violation 顯示於對應欄位下；`scr_limit` 文案提示改 MAJOR；文案取 `RESEARCH_REASON_TEXT`（不內嵌第二份）
  - 判定：npx vitest run components/domain/research/ScrRequestDialog.test.tsx -t AT_962_15_4（cwd＝AgentConsole/frontend）
- **AT-962-15-5**（vitest｜`components/domain/research/ScrBanner.test.tsx`｜Unit｜AC-R2P-19-4、AC-R2P-19-1）SCR_OPEN 時橫幅與停用規則：看板、InnerLoopLinks、GateRegisterDialog、ReleaseActions 的啟動類動作一律停用並顯示同一文案。
  - Given kanban `scrOpen=true`
  - When 渲染 ScrBanner 與四個元件
  - Then 橫幅文字為『規格變更中：SCR-<n>（<kind>）』並連到工作室；四處動作停用且文案取 `BUILD_DISABLED_TEXT.SCR_OPEN`；`executionBlock()` 簽名不變
  - 判定：npx vitest run components/domain/research/ScrBanner.test.tsx -t AT_962_15_5（cwd＝AgentConsole/frontend）
- **AT-962-15-E-1**（vitest｜`components/domain/research/ScrRequestDialog.test.tsx`｜Unit｜AC-R2P-19-5）常數邊界：reason 500／501、affectedSections 20／21、單項 200／201、證據連結 500／501。
  - Given 表單輸入邊界值
  - When 逐一輸入並觀察送出鈕與訊息
  - Then 邊界內可送出；超界顯示計數與錯誤且送出鈕停用；計數器顯示剩餘字數
  - 判定：npx vitest run components/domain/research/ScrRequestDialog.test.tsx -t AT_962_15_E_1（cwd＝AgentConsole/frontend）
- **AT-962-15-E-2**（vitest｜`components/domain/research/ScrRequestDialog.test.tsx`｜Unit｜AC-R2P-19-1）無權不送請求：VIEWER 的對話框不能開啟、送出請求數為 0。
  - Given VIEWER
  - When 嘗試開啟與送出
  - Then 鈕停用；請求 0
  - 判定：npx vitest run components/domain/research/ScrRequestDialog.test.tsx -t AT_962_15_E_2（cwd＝AgentConsole/frontend）
- **AT-962-15-E-3**（vitest｜`components/domain/research/ScrRequestDialog.test.tsx`｜Unit｜AC-R2P-19-5）reasonClass 兩種拼法：前端送中文，後端兩種拼法皆收。
  - Given 請求攔截
  - When 送出任一分類
  - Then 請求本文 `reasonClass` 為中文字面；（後端兩拼法由 AT-961 系列既有鎖守，不重造）
  - 判定：npx vitest run components/domain/research/ScrRequestDialog.test.tsx -t AT_962_15_E_3（cwd＝AgentConsole/frontend）
- **AT-962-15-E-4**（vitest｜`components/domain/research/ScrRequestDialog.test.tsx`｜Unit｜AC-R2P-19-5）證據連結以外部連結安全規則顯示：只接受 https，顯示為純文字。
  - Given 連結欄輸入 `javascript:alert(1)` 與 `https://a.example`
  - When 輸入並送出
  - Then 前者在前端即被擋並顯示錯誤；後者通過；任何位置不以 `href` 渲染使用者輸入的非 https 字串
  - 判定：npx vitest run components/domain/research/ScrRequestDialog.test.tsx -t AT_962_15_E_4（cwd＝AgentConsole/frontend）
- **AT-962-16-1**（vitest｜`components/domain/research/ResearchBackLink.test.tsx`｜Unit｜AC-R2P-01-5）ResearchBackLink：UUID 顯示回到研發工作流，href 固定；null 不渲染。
  - Given props `researchId` 為 UUID 與 null
  - When 渲染
  - Then 有值時 `<a>` 文字為『回到研發工作流』、href 為 `/research/<id>?step=build`；null 時 DOM 為空
  - 判定：npx vitest run components/domain/research/ResearchBackLink.test.tsx -t AT_962_16_1（cwd＝AgentConsole/frontend）
- **AT-962-16-2**（vitest｜`components/domain/execute/ExecuteView.test.tsx`｜Unit｜AC-R2P-01-5、AC-R2P-15-5）ExecuteView 在 ?researchId=<uuid> 時頁頂顯示 BackLink。
  - Given `useSearchParams` 注入 `researchId`
  - When 渲染 ExecuteView
  - Then 顯示回連且 href 正確；`ExecuteView.sdd.test.tsx` 不受影響（同檔集合跑綠）
  - 判定：npx vitest run components/domain/execute/ExecuteView.test.tsx -t AT_962_16_2（cwd＝AgentConsole/frontend）
- **AT-962-16-3**（vitest｜`components/domain/monitor/MonitorView.test.tsx`｜Unit｜AC-R2P-01-5、AC-R2P-15-5）MonitorView 在 ?researchId=<uuid> 時頁頂顯示 BackLink。
  - Given 同上
  - When 渲染 MonitorView
  - Then 顯示回連且 href 正確
  - 判定：npx vitest run components/domain/monitor/MonitorView.test.tsx -t AT_962_16_3（cwd＝AgentConsole/frontend）
- **AT-962-16-4**（vitest｜`components/domain/research/InnerLoopLinks.test.tsx`｜Unit｜AC-R2P-15-5）看板與 InnerLoopLinks 的連結帶 researchId 查詢參數。
  - Given 已綁 console 專案的研究專案
  - When 渲染兩元件
  - Then 所有開啟執行中心與監控中心的 href 皆含 `?researchId=<uuid>`；UUID 格式驗證通過
  - 判定：npx vitest run components/domain/research/InnerLoopLinks.test.tsx -t AT_962_16_4（cwd＝AgentConsole/frontend）
- **AT-962-16-5**（vitest｜`components/domain/research/ResearchWorkspaceView.test.tsx`｜Unit｜AC-R2P-01-5）P1 反向釘改寫：工作區只在已有 consoleProjectId 的步驟 4 面板出現連結字樣，其他步驟仍沒有。
  - Given `ResearchWorkspaceView.test.tsx:228-233` 的斷言（§4 第 16 列）
  - When 各步驟渲染
  - Then 步驟 4 面板有連結字樣；步驟 1、2、3、5 的文字不匹配 `/開啟執行中心|開啟監控中心/`（DeliverPanel 不放這兩個連結）；其餘斷言零改動
  - 判定：npx vitest run components/domain/research/ResearchWorkspaceView.test.tsx -t AT_962_16_5（cwd＝AgentConsole/frontend）
- **AT-962-16-E-1**（vitest｜`components/domain/execute/ExecuteView.test.tsx`｜Unit｜AC-R2P-01-5）無參數（深連結直接開執行中心）不顯示返回連結，不猜。
  - Given 無查詢參數
  - When 渲染 ExecuteView 與 MonitorView
  - Then 兩者皆無回連
  - 判定：npx vitest run components/domain/execute/ExecuteView.test.tsx -t AT_962_16_E_1（cwd＝AgentConsole/frontend）
- **AT-962-16-E-2**（vitest｜`components/domain/research/ResearchBackLink.test.tsx`｜Unit｜AC-R2P-01-5）非 UUID 一律忽略：路徑穿越、腳本、長度不符、非十六進位。
  - Given researchId 為 `../x`、`<script>`、35 字元、含 `g` 的 36 字元、空字串
  - When 渲染
  - Then 皆不渲染；合法大小寫混合 UUID 渲染（比對不分大小寫）
  - 判定：npx vitest run components/domain/research/ResearchBackLink.test.tsx -t AT_962_16_E_2（cwd＝AgentConsole/frontend）
- **AT-962-16-E-3**（vitest｜`components/domain/research/ResearchBackLink.test.tsx`｜Unit｜AC-R2P-01-5）零後端、零儲存：不呼叫 API、不讀寫 storage；頁面殼零差異。
  - Given spy `fetch`、`localStorage`、`sessionStorage`；`git diff` 對兩個 page.tsx
  - When 渲染 ExecuteView
  - Then 三者呼叫 0；`app/projects/[projectId]/execute/page.tsx` 與 `monitor/page.tsx` 零 diff
  - 判定：npx vitest run components/domain/research/ResearchBackLink.test.tsx -t AT_962_16_E_3（cwd＝AgentConsole/frontend）
- **AT-962-17-8**（vitest｜`components/domain/research/TraceabilityTable.test.tsx`｜Unit｜AC-R2P-20-1、AC-R2P-20-2）表格呈現：一 AC 一列、紅標、未覆蓋計數、摘要純文字。
  - Given 夾具含 PASS、FAIL、NOT_RUN、NONE 與含 `<script>` 的摘要
  - When 渲染
  - Then 列數等於 acTotal；非 PASS 列標紅（有文字標記，不只靠顏色）；『未覆蓋 n』等於 totals.uncovered；摘要為純文字；表格有可及的列與欄名稱
  - 判定：npx vitest run components/domain/research/TraceabilityTable.test.tsx -t AT_962_17_8（cwd＝AgentConsole/frontend）
- **AT-962-21-1**（vitest｜`components/domain/research/ResearchWorkspaceView.test.tsx`｜Unit｜AC-R2P-21-5、AC-R2P-20-1）步驟 5 取代占位：deliver 為 DeliverPanel，研究面占位面板為零個。
  - Given `ResearchWorkspaceView.test.tsx:264-326`（AT_961_19_1）改寫（§4 第 17 列）
  - When 渲染五個步驟
  - Then `?step=deliver` 顯示 DeliverPanel；任一步驟皆無 `research-placeholder`；`PlaceholderPanel`（`ResearchWorkspaceView.tsx:66`）刪除或僅防呆；超前導回規則沿 P1
  - 判定：npx vitest run components/domain/research/ResearchWorkspaceView.test.tsx -t AT_962_21_1（cwd＝AgentConsole/frontend）
- **AT-962-21-2**（vitest｜`components/domain/research/DeliverPanel.test.tsx`｜Unit｜AC-R2P-20-1）DeliverPanel 整體呈現：追溯表、發布動作列、交付紀錄、對帳狀態。
  - Given delivery 與 traceability 夾具
  - When 渲染
  - Then 含 TraceabilityTable、ReleaseActions、已建立交付清單（tag、PR 各一列）、最近對帳 delivery 項；無寫入控件於未授權角色
  - 判定：npx vitest run components/domain/research/DeliverPanel.test.tsx -t AT_962_21_2（cwd＝AgentConsole/frontend）
- **AT-962-21-3**（vitest｜`components/domain/research/ReleaseActions.test.tsx`｜Unit｜AC-R2P-20-2）建立 Tag 鈕停用規則：未覆蓋大於 0、非 RELEASE_READY、SCR_OPEN、非 ADMIN 任一成立即停用並顯示原因與未覆蓋清單。
  - Given 六種組合夾具
  - When 渲染
  - Then 只有全部條件成立才啟用；停用時顯示原因文字（未覆蓋清單逐 AC 列出）；SCR_OPEN 文案取登記處；非 ADMIN title 為權限不足
  - 判定：npx vitest run components/domain/research/ReleaseActions.test.tsx -t AT_962_21_3（cwd＝AgentConsole/frontend）
- **AT-962-21-4**（vitest｜`components/domain/research/TagConfirmDialog.test.tsx`｜Unit｜AC-R2P-20-3）Tag 確認框：semver 即時驗證、push 勾選預設未勾並附說明、成功顯示交付與快照 sha256、錯誤 reason 文案。
  - Given stubApi 回 201、409 `tag_exists`、502 `delivery_step_failed`（`failure_step=push`）、409 `scr_open`
  - When 輸入 tag、勾與不勾 push、送出
  - Then 不合 semver 時送出鈕停用並顯示規則；預設未勾 push；請求本文 `push` 對應勾選；成功顯示 tag、commit sha 前 12 碼、snapshot sha256；錯誤顯示 `RESEARCH_REASON_TEXT` 文案與失敗步驟
  - 判定：npx vitest run components/domain/research/TagConfirmDialog.test.tsx -t AT_962_21_4（cwd＝AgentConsole/frontend）
- **AT-962-21-5**（vitest｜`components/domain/research/PrConfirmDialog.test.tsx`｜Unit｜AC-R2P-20-4）PR：已記錄顯示 URL（新分頁、noopener noreferrer）；無 PR 時 ADMIN 見建立 PR 並預覽標題、內文與推送目標；其餘顯示尚未建立與原因。
  - Given 夾具：已有 PR；無 PR 且 gh 可用；OPERATOR；gh 缺失（missing 含 gh）
  - When 渲染與開確認框
  - Then 連結 `target="_blank"` 且 `rel` 含 `noopener` 與 `noreferrer`；預覽內容與模板一致且為純文字；確認需勾 ack 才可送；OPERATOR 無建立鈕；缺項時顯示『尚未建立』與缺項原因
  - 判定：npx vitest run components/domain/research/PrConfirmDialog.test.tsx -t AT_962_21_5（cwd＝AgentConsole/frontend）
- **AT-962-21-6**（vitest｜`components/domain/research/ReleaseActions.test.tsx`｜Unit｜AC-R2P-20-5）開啟本地專案：顯示專案根路徑與複製鈕；容器模式標示容器內路徑；不假裝可開啟。
  - Given overview 夾具 `containerMode` 為 false 與 true
  - When 渲染並點複製
  - Then 顯示 `projectRoot` 與複製鈕（`CopyCommand`）；容器模式加註『此為容器內路徑』；DOM 無 `file://` 連結、不呼叫 `window.open`
  - 判定：npx vitest run components/domain/research/ReleaseActions.test.tsx -t AT_962_21_6（cwd＝AgentConsole/frontend）
- **AT-962-21-E-1**（vitest｜`components/domain/research/ReleaseActions.test.tsx`｜Unit｜AC-R2P-20-2）RTM 100% 但非 RELEASE_READY：仍停用。
  - Given 夾具
  - When 渲染
  - Then Tag 鈕停用，原因含『尚未達 RELEASE_READY』
  - 判定：npx vitest run components/domain/research/ReleaseActions.test.tsx -t AT_962_21_E_1（cwd＝AgentConsole/frontend）
- **AT-962-21-E-2**（vitest｜`components/domain/research/TraceabilityTable.test.tsx`｜Unit｜AC-R2P-20-1）純文字渲染：摘要含 HTML 不執行。
  - Given 摘要含 `<img src=x onerror=...>`
  - When 渲染
  - Then 無 img 元素與 on* 屬性
  - 判定：npx vitest run components/domain/research/TraceabilityTable.test.tsx -t AT_962_21_E_2（cwd＝AgentConsole/frontend）
- **AT-962-21-E-3**（vitest｜`components/domain/research/PrConfirmDialog.test.tsx`｜Unit｜AC-R2P-20-4）外部連結安全：所有外部連結帶 noopener noreferrer。
  - Given 全 DeliverPanel 的 `<a>`
  - When 渲染並掃描
  - Then 每個 `target=_blank` 的連結 `rel` 皆含兩者
  - 判定：npx vitest run components/domain/research/PrConfirmDialog.test.tsx -t AT_962_21_E_3（cwd＝AgentConsole/frontend）
- **AT-962-21-E-4**（vitest｜`components/domain/research/ReleaseActions.test.tsx`｜Unit｜AC-R2P-20-3）已交付（FSM 為 RELEASE）：Tag 鈕顯示已建立並停用，不可重複送出。
  - Given fsmState 為 RELEASE 且有 RELEASE_TAG 列
  - When 渲染
  - Then 顯示『已建立 <tag>』；鈕停用；送出請求 0
  - 判定：npx vitest run components/domain/research/ReleaseActions.test.tsx -t AT_962_21_E_4（cwd＝AgentConsole/frontend）
- **AT-962-23-7**（vitest｜`components/domain/research/ResearchWorkspaceView.test.tsx`｜Unit｜AC-R2P-23-4）前端 `RECONCILE_CHECK_LABEL` 新增 delivery＝『交付』，`reconcileDriftView` 對 delivery drift 回檔案漂移列，單一橫幅顯示 delivery 漂移。
  - Given `lib/domain/research.ts:518-525` 的 `RECONCILE_CHECK_LABEL`；對帳結果夾具 delivery 為 drift
  - When 渲染工作區
  - Then 標籤表鍵集合為七個且 `delivery` 標籤為『交付』（`research.test.ts:710-714` 的名單與 `Set size` 改七）；單一橫幅（依 AT-962-25-3）列出『交付』漂移；`RECONCILE_CHECK_LABEL` 含 `delivery`＝『交付』，且 `reconcileDriftView` 對 delivery drift 回檔案漂移列（`types.ts:840-845` 的 `name` 為 `string`，不需型別聯集）
  - 判定：npx vitest run components/domain/research/ResearchWorkspaceView.test.tsx -t AT_962_23_7（cwd＝AgentConsole/frontend）
- **AT-962-24-5**（vitest｜`lib/api/endpoints.test.ts`｜Unit｜AC-R2P-15-1）端點函式總數與 operationId 一一對應：118 增為 125。
  - Given `endpoints.test.ts:322`（`toHaveLength(118)`）
  - When 跑 endpoints.test.ts
  - Then 總數為 125（以實際新增七個函式為準）；七個函式名與 operationId 一一對應；URL 與方法與契約一致
  - 判定：npx vitest run lib/api/endpoints.test.ts -t AT_962_24_5（cwd＝AgentConsole/frontend）
- **AT-962-24-6**（vitest｜`lib/domain/research.test.ts`｜Unit｜AC-R2P-20-3）前端兩個新 reason 有中文文案且 research.ts 常數與後端逐字一致。
  - Given `RESEARCH_REASONS`、`RESEARCH_REASON_TEXT`
  - When 跑 research.test.ts
  - Then 含 `TAG_EXISTS`、`DELIVERY_STEP_FAILED`；文案非空；常數字面等於 `tag_exists`、`delivery_step_failed`；`RESEARCH_REASONS` 值集合長度為 37（`research.test.ts:958-959` 的 `toHaveLength(35)` 改 37）
  - 判定：npx vitest run lib/domain/research.test.ts -t AT_962_24_6（cwd＝AgentConsole/frontend）
- **AT-962-25-1**（vitest｜`lib/help/research-workspace.test.ts`｜Unit｜AC-R2P-21-2）說明登記表：步驟 4 其餘與步驟 5 的欄位釋義一次寫完，過三道鎖與 lint，HELP_PAGES 計數不變。
  - Given `lib/help/research-workspace.ts`；`registry.test.ts`、`content.test.ts`、`lint.test.ts`
  - When 跑四個說明測試
  - Then 每條釋義不超過 60 字、英文白名單通過；`HELP_PAGES` 與 `HELP_ROUTES` 計數與 P1 相同（P2 不新增頁）；`PENDING_HELP_PAGES` 為空
  - 判定：npx vitest run lib/help/research-workspace.test.ts -t AT_962_25_1（cwd＝AgentConsole/frontend）
- **AT-962-25-2**（vitest｜`components/domain/research/ResearchWorkspaceView.test.tsx`｜Unit｜AC-R2P-21-5）P2 版步驟接入：五步皆真面板；Gate 0 未完成時超前導回規則不變。
  - Given 游標在 studio 與 build、deliver 的組合
  - When 渲染 `?step=route|build|deliver`
  - Then 皆為真面板；超前導回沿 P1
  - 判定：npx vitest run components/domain/research/ResearchWorkspaceView.test.tsx -t AT_962_25_2（cwd＝AgentConsole/frontend）
- **AT-962-25-3**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-23-4）兩處漂移橫幅整併為工作區單一橫幅（D-131(6)）。
  - Given `ResearchWorkspaceView.tsx:92` 的 `drift-banner` 與 `BuildFrontPanel.tsx:43` 的 `build-drift-banner`；兩檔測試（`BuildFrontPanel.test.tsx:527-538`、`ResearchWorkspaceView.test.tsx:417-524`）
  - When 渲染步驟 4 在對帳 drift 與一致兩情境
  - Then 畫面只有一個 `drift-banner`；`build-drift-banner` 不存在；兩處測試同改且語意不減
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_962_25_3（cwd＝AgentConsole/frontend）
- **AT-962-25-4**（vitest｜`components/domain/research/ResearchFlowHeader.test.tsx`｜Unit｜AC-R2P-21-5）P0 殘留 R-3：反向斷言正則改字串拼接，AT_960_20_4 的字面掃描不再自我命中。
  - Given `ResearchFlowHeader.test.tsx:123` 附近的正則
  - When 跑 AT_960_20_4 與本檔
  - Then 兩者皆綠；斷言語意不變（仍禁止 flow header 引用四區塊元件）
  - 判定：npx vitest run components/domain/research/ResearchFlowHeader.test.tsx -t AT_962_25_4（cwd＝AgentConsole/frontend）
- **AT-962-25-5**（vitest｜`lib/nav/research-nav.test.ts`｜Unit｜AC-R2P-21-2）導覽與詞彙不動：registry.ts 零 diff，mobile 不超過 6，詞彙與衍生標籤計數與 P1 相同。
  - Given `research-nav.test.ts`、`registry.test.ts`
  - When 跑兩檔與 `git diff`
  - Then 全綠；`lib/nav/registry.ts` 零 diff；事件層新 kind（`HEALING_LOG_TRUNCATED` 等）不入詞彙
  - 判定：npx vitest run lib/nav/research-nav.test.ts -t AT_962_25_5（cwd＝AgentConsole/frontend）
- **AT-962-25-E-2**（vitest｜`lib/help/research-workspace.test.ts`｜Unit｜AC-R2P-21-2）狀態表不增：StateTableId 成員數不變。
  - Given `lib/help/types.ts` 與 `states.ts`
  - When 跑 content 與 registry 測試
  - Then `StateTableId` 計數與 P1 相同
  - 判定：npx vitest run lib/help/research-workspace.test.ts -t AT_962_25_E_2（cwd＝AgentConsole/frontend）
- **AT-962-27-2**（vitest｜`lib/api/types.test.ts`｜Unit｜AC-R2P-21-2）手寫型別改引生成型：P2 型別皆為生成型別名的別名或引用。
  - Given `lib/api/types.ts`
  - When 型別層測試（`expectTypeOf`）
  - Then 新 DTO 型別與生成型相等；開放物件回應維持手寫型並註解
  - 判定：npx vitest run lib/api/types.test.ts -t AT_962_27_2（cwd＝AgentConsole/frontend）
- **AT-962-27-3**（vitest｜`lib/api/types.test.ts`｜Unit｜AC-R2P-21-2）夾具補必填欄、不放寬為選填（D-135）：生成型必填欄在夾具皆有值。
  - Given `tests/fixtures/research/*.ts`
  - When tsc 與型別測試
  - Then tsc 0 錯；靜態掃描無新增的 `?:` 放寬於生成型必填欄
  - 判定：npx vitest run lib/api/types.test.ts -t AT_962_27_3（cwd＝AgentConsole/frontend）

### 3.4 E2E 與指令核對（Docker 全棧、Playwright、git 與靜態工具；主控或整合棒跑）

- **AT-962-11-9**（Playwright｜`tests/e2e/research-kanban.mock.spec.ts`｜E2E｜AC-R2P-15-3、AC-R2P-15-4）Playwright mock：頁面內 performance.mark 再驗 500ms、斷線回補、Bridge 不可達態。
  - Given `mockApi.ts` 體例；SSE 以頁面內假事件源
  - When 三個情境各一
  - Then mark 差值不大於 500ms；斷線後回補到最新；不可達態有橫幅且無空看板
  - 判定：npx playwright test tests/e2e/research-kanban.mock.spec.ts -g AT_962_11_9 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-962-11-E-4**（Playwright｜`tests/e2e/a11y.mock.spec.ts`｜E2E｜AC-R2P-15-1）a11y 與版面：看板在大、中、小三種寬度（寬度值沿 P1 的 a11y 規格）無水平溢出，axe 無 serious 與 critical。
  - Given mock spec；步驟 4 看板情境（含不可達態）
  - When 三種寬度各掃描
  - Then `scrollWidth` 不大於 `clientWidth`；axe 無 serious、critical（以 `--output` 各自目錄）
  - 判定：npx playwright test tests/e2e/a11y.mock.spec.ts -g AT_962_11_E_4 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-962-13-E-3**（指令核對｜指令｜Gate｜AC-R2P-17-3）重用元件零改動：LiveLogCard.tsx、useRunStream.ts、LogPanel.tsx 零 diff。
  - Given 開工基準 commit 與 HEAD
  - When `git diff --name-only <基準>..HEAD -- AgentConsole/frontend/components/domain/execute/LiveLogCard.tsx AgentConsole/frontend/hooks/useRunStream.ts AgentConsole/frontend/components/domain/monitor/LogPanel.tsx`
  - Then 輸出為空
  - 判定：git diff --name-only <基準>..HEAD -- <三檔>（cwd＝monorepo 根；PowerShell 與 bash 皆可）
- **AT-962-21-8**（Playwright｜`tests/e2e/research-deliver.mock.spec.ts`｜E2E｜AC-R2P-20-1、AC-R2P-20-2）步驟 5 的 mock E2E：版面無溢出、axe 無 serious 與 critical、兩個確認框焦點陷阱與歸還。
  - Given mock spec；三種寬度
  - When 開啟步驟 5、開關兩個確認框
  - Then `scrollWidth` 不大於 `clientWidth`；axe 通過；焦點循環與歸還正確
  - 判定：npx playwright test tests/e2e/research-deliver.mock.spec.ts -g AT_962_21_8 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-962-24-E-3**（指令核對｜指令｜Gate｜AC-R2P-20-3）契約與 Architecture 的 reason 表缺列由具名名單鎖住，勘誤批次後清空。
  - Given 契約 §0.2 與 Architecture §11.1
  - When `Select-String` 兩檔的 `tag_exists` 與 `delivery_step_failed`
  - Then RELEASE_READY 勘誤批次後各檔各命中至少一次，且 `ResearchReasonsTest` 兩份 PENDING 名單為空
  - 判定：Select-String -Path AgentConsole/docs/02_architecture/API_Contract_ResearchToPRD.md,AgentConsole/docs/02_architecture/Architecture.md -Pattern 'tag_exists','delivery_step_failed'（cwd＝monorepo 根；bash 版 grep -c）
- **AT-962-25-E-1**（指令核對｜指令｜Gate｜AC-R2P-21-2）四區塊零差異：layout.tsx 與 components/layout/** 零 diff。
  - Given 基準與 HEAD
  - When `git diff --name-only <基準>..HEAD -- AgentConsole/frontend/app/layout.tsx AgentConsole/frontend/components/layout`
  - Then 輸出為空
  - 判定：git diff --name-only <基準>..HEAD -- AgentConsole/frontend/app/layout.tsx AgentConsole/frontend/components/layout（cwd＝monorepo 根）
- **AT-962-27-1**（指令核對｜指令｜Gate｜AC-R2P-21-2）schema.d.ts 由 backend OpenAPI 重產：七條新路徑與新 DTO 存在，重產後 diff 為空。
  - Given backend 啟動後的 `/v3/api-docs`；`openapi-typescript` 既有腳本
  - When 重產並 `git diff --exit-code -- AgentConsole/frontend/lib/api/schema.d.ts`；Grep 七個路徑與 `KanbanDto`、`GateRegisterRequest`、`HealingDto`、`DeliveryOverviewDto`、`TagRequest`、`PrRequest`、`TraceabilityDto`、`ScrDto.evidenceUrl`
  - Then 全部命中；重產後無差異
  - 判定：npm run gen:api（或既有重產指令，現查 package.json）後 git diff --exit-code -- AgentConsole/frontend/lib/api/schema.d.ts（cwd＝monorepo 根）
- **AT-962-27-E-1**（指令核對｜指令｜Gate｜AC-R2P-21-2）tsc、lint、build 皆 rc 0。
  - Given frontend
  - When `npx tsc --noEmit`、`npm run lint`、`npm run build`
  - Then 三者 rc 皆 0（rc 先存變數再讀）
  - 判定：Push-Location AgentConsole\frontend; npx tsc --noEmit; $a=$LASTEXITCODE; npm run lint; $b=$LASTEXITCODE; npm run build; $c=$LASTEXITCODE; Pop-Location; "tsc=$a lint=$b build=$c"
- **AT-962-27-E-2**（指令核對｜指令｜Gate｜AC-R2P-21-2）單一歸屬：schema.d.ts 只由 FE-W3 修改。
  - Given 各包提交
  - When 逐包 `git diff --name-only`
  - Then 僅 FE-W3 的提交含該檔
  - 判定：git log --format=%h -- AgentConsole/frontend/lib/api/schema.d.ts（cwd＝monorepo 根；對照各包提交）
- **AT-962-28-4**（Playwright｜`tests/e2e/research-deliver.stack.spec.ts`｜E2E｜AC-R2P-18-2、AC-R2P-16-3）出口 (b)：ESCALATED 後彈窗出現（mock 一次、真棧一次），決定走既有 review 端點。
  - Given Docker 全棧；mock 劇本
  - When 開步驟 4、處理一次
  - Then 彈窗出現且決定入庫；`audit_log` 一列
  - 判定：npx playwright test tests/e2e/research-deliver.stack.spec.ts -g AT_962_28_4 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-962-28-5**（Playwright｜`tests/e2e/research-deliver.stack.spec.ts`｜E2E｜AC-R2P-19-1、AC-R2P-19-4）出口 (c)：本機模式從看板 UI 發起 MINOR SCR，Gate 0 經 approveViaApi 代驗，舊凍結版保留、新 digest 入庫。
  - Given 載具甲（本機模式：backend 與 Bridge 同機、真 PG、拋棄式 clone、研究劇本 `pass` 與內環 mock）；Gate 0 一律經 P0 helper `approveViaApi` 走 API 核准（不靠真人點擊；構造情境，證據標明）
  - When 自看板 UI 發起 MINOR SCR，起草與審查走研究劇本，Gate 0 以 `approveViaApi` 核准，再套用 SCR
  - Then 舊凍結 PRD 檔位元組不變；新 `spec_doc_digests` 入庫；SCR 轉 APPLIED；證據註明『Gate 0 為 API 代驗』
  - 判定：npx playwright test tests/e2e/research-deliver.stack.spec.ts -g AT_962_28_5 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-962-28-7**（Playwright｜`tests/e2e/research-deliver.stack.spec.ts`｜E2E｜AC-R2P-15-1、AC-R2P-17-1、AC-R2P-20-1）Docker mock-only：看板、自癒視圖、終端窗格、追溯表可驗；`:gates` 用暫存 FSM 鍵。
  - Given Docker 全棧（容器無 repo 寫入掛載與 gh）
  - When 走看板、自癒、終端、追溯表
  - Then 各面板正確呈現；沒有任何寫入 repo 的動作
  - 判定：npx playwright test tests/e2e/research-deliver.stack.spec.ts -g AT_962_28_7 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-962-28-8**（Playwright｜`tests/e2e/research-deliver.stack.spec.ts`｜E2E｜AC-R2P-20-3）Docker 容器模式負控：API 直呼 :tag 回 422 route_unsupported_in_deployment，DB 零變化。
  - Given Docker 全棧
  - When POST `…/delivery/tag`
  - Then 422、`details.missing` 含 `repo_writable`；`research_deliveries` 與 FSM 不變
  - 判定：npx playwright test tests/e2e/research-deliver.stack.spec.ts -g AT_962_28_8 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-962-28-E-2**（指令核對｜指令｜Gate｜AC-R2P-20-3）清理義務：subst、worktree、bare repo、拋棄式 DB、假 gh 目錄、Docker 測試標籤與懸空卷無殘留。
  - Given INT 收尾
  - When 逐項現查
  - Then 證據檔『殘留清單』為無殘留
  - 判定：Get-PSDrive -PSProvider FileSystem；git worktree list；docker image ls；psql -l（cwd＝monorepo 根；逐項人讀對照）
- **AT-962-29-1**（指令核對｜指令｜Gate｜AC-R2P-02-10）允許變更檔案集合：只動各包 §5.7 的集合，其餘零差異。
  - Given 開工基準 commit（RTM-P2 檔頭記錄）與 HEAD；§5.7 各包集合
  - When `git diff --name-only <基準>..HEAD` 與 `git status --porcelain` 逐檔歸屬
  - Then 每個變更檔屬於某包集合或主控收尾連動清單；§4 各列只改預期值、零刪斷言（掃刪除行的 `expect(`、`assert`、`it(`、`@Test`）
  - 判定：git diff --name-only <基準>..HEAD；git diff -U0 <基準>..HEAD -- <§4 測試檔> 掃刪除行（cwd＝monorepo 根）
- **AT-962-29-2**（指令核對｜指令｜Gate｜AC-R2P-02-10）禁區零差異：根 CLAUDE.md、.claude、tools、.github、AutoClaude、AISDLC_SDD、Flyway V1～V20、package.json、sdd_cli.py、rtm.py、SecurityConfig、ExecutionController、ResearchFlowPolicy.java、nav registry。
  - Given 基準與 HEAD
  - When `git diff --name-only <基準>..HEAD -- <禁區清單>`
  - Then 輸出為空（`agentconsole-ci.yml` 的 paths 由主控收尾單窗另列）
  - 判定：git diff --name-only <基準>..HEAD -- .claude tools .github AutoClaude AISDLC_SDD CLAUDE.md AgentConsole/backend/src/main/resources/db/migration/V1* AgentConsole/engine-bridge/app/sdd_cli.py（cwd＝monorepo 根）
- **AT-962-29-3**（指令核對｜指令｜Gate｜AC-R2P-02-10）不新增 os.replace、rename、move 站點，根層 dirent 鎖綠。
  - Given 基準與 HEAD 的 `app/research/**`
  - When `git grep` 目錄項原語；跑 `TestDirEntryPrimitivesAreAccountedFor`
  - Then 站點淨增 0；測試 rc 0
  - 判定：git grep -nE "os\.(replace|rename)|shutil\.move" -- AgentConsole/engine-bridge/app；python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v（cwd＝tools/tests；rc 先存變數）
- **AT-962-29-4**（指令核對｜指令｜Gate｜AC-R2P-02-10）根層 tools/tests 相關鎖自跑（D-141）：windowsapps guard 平價、E501 棘輪、_TREE_FILE_FLOORS、名冊。
  - Given 各包交卷前
  - When 跑兩個測試檔
  - Then rc 0
  - 判定：python -m unittest test_windowsapps_guard_bash_parity test_doc_loc_baseline_freshness_r60（cwd＝tools/tests；rc 先存變數）
- **AT-962-29-5**（指令核對｜指令｜Gate｜AC-R2P-02-10）Python 衛生：ruff 0 錯，新檔 open 與 read_text 與 write_text 帶 encoding，時間戳帶 tz。
  - Given 新 Python 檔
  - When `ruff check AgentConsole/engine-bridge`（本目錄與根視角各一次）
  - Then 0 錯
  - 判定：ruff check AgentConsole/engine-bridge（cwd＝monorepo 根）；Push-Location AgentConsole\engine-bridge; ruff check .; Pop-Location
- **AT-962-29-E-1**（指令核對｜指令｜Gate｜AC-R2P-02-10）子行程使用者不增：除 gitops、sdd_cli 既有六檔外無新增。
  - Given 基準與 HEAD
  - When `git grep -nE "subprocess|Popen" -- AgentConsole/engine-bridge/app`
  - Then 命中檔集合等於 EXEC_MODULES 與 procutil
  - 判定：git grep -lE "subprocess|Popen" -- AgentConsole/engine-bridge/app（cwd＝monorepo 根；與基準比對）
- **AT-962-29-E-2**（指令核對｜指令｜Gate｜AC-R2P-02-10）新增夾具目錄不含 shell 腳本，名冊不變。
  - Given `tests/fixtures/research/`
  - When `git status --porcelain` 看新目錄
  - Then 無新目錄含 .sh；假 gh 只改既有 `gh_fake.py`
  - 判定：git status --porcelain -- AgentConsole/engine-bridge/tests/fixtures（cwd＝monorepo 根）
- **AT-962-29-E-3**（指令核對｜指令｜Gate｜AC-R2P-02-10）入庫文件守門：無測試摘要字樣加四位數字同行。
  - Given 本鍵新增或修改的文件
  - When pre-commit 的 `tools/check_pytest_baseline_sites.py` 判準
  - Then 零違規
  - 判定：python tools/check_pytest_baseline_sites.py（cwd＝monorepo 根）
- **AT-962-30-1**（指令核對｜指令｜Gate｜AC-R2P-20-3）V21 DDL 與 Architecture K.6 逐字一致，且與 `V21_DDL.md` 草案對拍。
  - Given Architecture K.6 區塊與 `V21__research_gate_details_delivery_snapshot.sql`
  - When 抽出兩者 DDL 文字比對
  - Then 逐字相同（空白正規化後 sha256 相等）
  - 判定：取 Architecture K.6 的 sql 區塊與 V21 檔各算 SHA256 比對（cwd＝monorepo 根；PowerShell Get-FileHash）
- **AT-962-30-2**（指令核對｜指令｜Gate｜AC-R2P-20-3）RELEASE_READY 勘誤批次：D-140 十四處與 D-139 連動寫入契約、ADR-003 D16、Architecture、PRD，並一併 refreeze。
  - Given RELEASE_READY 態
  - When 逐檔 Select-String 勘誤字樣
  - Then 每處至少一個命中；勘誤表非空
  - 判定：Select-String -Path docs/01_requirements/ResearchToPRD_PRD.md,AgentConsole/docs/02_architecture/*.md -Pattern 'SCG6','snapshot_sha256','evidence_url'（cwd＝monorepo 根）
- **AT-962-30-3**（指令核對｜指令｜Gate｜AC-R2P-02-4）RTM-P2 子表回填：列數等於 F 1 加 US 3 加 AC 30 加 AT 總數，四格回填，不刪列不改號。
  - Given RTM-P2 檔
  - When 數定義列
  - Then 列數與 TCS 檔頭宣告相同
  - 判定：(Select-String -Path AgentConsole/docs/06_quality/RTM-ResearchToPRD-P2-*.md -Pattern '^\| `(F|US|AC|AT)-').Count（期望值寫於 TCS 檔頭計數；bash 版 grep -cE）
- **AT-962-30-4**（指令核對｜指令｜Gate｜AC-R2P-02-4）V 系列（§6）皆有文字證據或如實標未驗。
  - Given 證據檔
  - When 逐項核對
  - Then V-S1、V-D5、V-H5、V-H6 與掌舵者真機五步（V-H）各有證據或『未驗』
  - 判定：人讀對照 SCG-4 報告 §B 與 §6 V 系列表（無自動指令；結果記為文字）
- **AT-962-30-5**（指令核對｜指令｜Gate｜AC-R2P-20-3）PRD §8.1 P2 出口 (a)～(i) 逐項有證據。
  - Given §6.1 對照表
  - When 逐項核對
  - Then 九項各有 AT 綠與證據或 V 證據
  - 判定：人讀對照 §6.1 表；各項證據逐字貼入 SCG-4 報告
- **AT-962-30-E-1**（指令核對｜指令｜Gate｜AC-R2P-02-4）計數宣告一致：TCS 檔頭 AT 數、RTM 列數、§1.5 列數相等。
  - Given TCS 與 RTM
  - When 數 §1.5 與 §3 與 RTM 的 AT 定義列
  - Then 三者相等
  - 判定：Select-String 數 TCS 的 '^- \*\*AT-962-' 與 RTM 的 '^\| `AT-962-'（cwd＝monorepo 根；期望值寫死於檔頭）
- **AT-962-30-E-2**（指令核對｜指令｜Gate｜AC-R2P-02-4）專案文件上限：AgentConsole/CLAUDE.md 不超過 200 行、README.md 不超過 80 行。
  - Given 兩檔
  - When 數行
  - Then 不超過上限
  - 判定：(Get-Content AgentConsole/CLAUDE.md).Count；(Get-Content AgentConsole/README.md).Count（cwd＝monorepo 根）

---
## 4. 需同步的既有測試與凍結文件勘誤（只改預期值，不刪斷言，例外見共同規則；每筆寫明「為何現值變了」）

> 座標為 SD 寫稿時（HEAD 為 `8380142a`，工作樹含 research 相關未提交修改）以 Grep 與 `git grep` 現查的快照（逐字結果見自查檔 `_aux/HARDPIN_SCAN.txt`，由 `_aux/scan_hardpins.py` 重跑），重跑法＝照座標讀檔；開發棒動手前先對該檔現查行號。標「現查」者為 SD 只確認檔存在、行號待開發棒定。**共同規則（AT-962-29-1 的 GATE 核對）**：下列每個 hunk 只動預期值、清單、探針列、快照列或註解；被刪的 `expect`、`it`、`assert`、`@Test` 行為 0；AT 標題與 id 不變。**例外（改斷言範圍或改規則歸屬；各列自寫範圍與理由，GATE 核對時逐列放行）**：標『例外』的列。product 檔（非測試）隨所屬包交付，列在此處是因為它們與測試同步。

### 4.1 backend 既有測試與 product 連動（PKG-DB-P2、PKG-API-P2）

| # | 檔:行 | 現值 | 改後值 | 為何現值變了 | 持有包 |
|---|-------|------|--------|--------------|--------|
| 1 | 六處 Flyway 版本清單：`AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/SchemaMigrationIT.java:69`、`V5UpgradeMigrationIT.java:136`、`IssuePriorityMigrationIT.java:131`、`BackupJobMigrationIT.java:171`（另 `:191`）、`SiConsoleWritesMigrationIT.java:129`、`ResearchSchemaMigrationIT.java:502`（另 `:1739`） | 皆 `…, "19", "20"` 結尾的 `containsExactly` | 各加 `"21"` | V21 落地（AT-962-1-7）；P1 的 V20 先例同型 | PKG-DB-P2 |
| 2 | `ResearchSchemaMigrationIT.java:505`（`containsEntry("20", "research github token config")` 一行） | 最高版 20 | 再加 `.containsEntry("21", "research gate details delivery snapshot")` | AT-962-1-1、1-7 | PKG-DB-P2 |
| 3 | `ResearchSchemaMigrationIT.java:1032-1033`（`expectEnum(soft, db.jdbc, "research_gate_decisions", "gate", …)`） | 七個列舉值（含 `ABANDON_KEY`） | 八值：`SCG5` 後加 `SCG6` | D-139 擴 gate CHECK（AT-962-1-2） | PKG-DB-P2 |
| 4 | `ResearchSchemaMigrationIT.java:473-474`（`databaseAt("18")`、`databaseAt("15")` 對 P0 表集合）與 `:1718`（`at18`） | 以特定版號查表集合 | **不變**（V21 不新增表；逐字確認 `baseTables` 結果不因 V21 改變） | 確認不紅；AT-962-1-1 另釘 V21 不新增表 | PKG-DB-P2 |
| 5 | `BackupJobMigrationIT.java:82-106,:154`（`snapshotOfExistingTables` 排除 `research_` 起頭之表） | 既有表零變動快照排除 `research_%` | **不變**（V21 只改 `research_` 表，已被排除） | 確認不紅（AT-962-1-7）；視圖排除條件 `v\_research\_` 為 P1 已加 | PKG-DB-P2 |
| 6 | `OpenApiIT.java:170`（`EXPECTED_PATH_COUNT = 107`） | 107 | 114 | 新增七條路徑（AT-962-24-2） | PKG-API-P2 |
| 7 | `OpenApiIT.java:171`（`EXPECTED_OPERATION_COUNT = 124`） | 124 | 131 | 新增七個操作 | PKG-API-P2 |
| 8 | `OpenApiIT.java:971`（研究路徑 `hasSize(30)`） | 30 | 37 | 同上 | PKG-API-P2 |
| 9 | `OpenApiIT.java:979-980`（研究操作 `isEqualTo(35)`、有 operationId `hasSize(34)`） | 35／34 | 42／41 | 同上 | PKG-API-P2 |
| 10 | `OpenApiIT.java:877`（`RESEARCH_OPERATION_IDS`）、`:923`（`RESEARCH_STATUS_CODES`）、`:999`（`hasSize(35)`）、`:45`（`EXPECTED` 路徑表） | 各 34／35／35 項 | 各加七項；`:999` 改 42；`EXPECTED` 加七條路徑 | AT-962-24-2、24-3 | PKG-API-P2 |
| 11 | `ResearchReasonsTest.java:142`（`ALL_REASONS hasSize(35)`）與 `:53-58`（`P0_REASONS`、`P0_TAIL_REASONS`、`P1_REASONS`、`ALL_REASONS = union(...)`） | 35 | 新增 `P2_REASONS`（`tag_exists`、`delivery_step_failed`）併入 union，`hasSize(37)` | AT-962-24-1 | PKG-API-P2 |
| 12 | `ResearchReasonsTest.java:60`（`CONTRACT_ERRATUM_PENDING`）、`:63`（`ARCHITECTURE_ERRATUM_PENDING`） | P1 缺列名單 | 各加兩項（契約 §0.2 與 Architecture §11.1 尚未補列） | 雙向鎖：缺列集合恰等於名單，勘誤落地後清空 | PKG-API-P2 |
| 13 | `ErrorReasons.java` 的 `RESEARCH_` 常數（product）與 `ResearchErrorDocs.java` | 35 個 | 加 `RESEARCH_TAG_EXISTS`、`RESEARCH_DELIVERY_STEP_FAILED` | 前綴須 `RESEARCH_`，否則 `IssueReasonsContractTest`、`BackupReasonsContractTest` 集合鎖紅 | PKG-API-P2 |
| 14 | `RbacIT.java:459-478`（matcher 清單，已含 `gates`、`delivery/tag`、`delivery/pr` 三條 ADMIN 規則）、`:499`（探針迴圈已含 `gates`、`delivery/tag`、`delivery/pr`） | 三端點已入清單 | **不改清單**；新增 `kanban`、`healing`、`delivery`、`delivery/traceability` 四個 GET 的 VIEWER 200 探針與 OPERATOR 對三端點的 403 負控行為斷言 | AT-962-24-4；`SecurityConfig.java:103-111`（P2 相關三條在 :107-109） 已預登 | PKG-API-P2 |
| 15 | `ResearchApiIT.java:54`（`RECONCILE_CHECK_IDS`）、`ResearchBridgeShapeTest.java:39-40,:58`（`BridgeSource.constants("CHECK_IDS", …)`）與迷你 Bridge `AgentConsole/backend/src/test/java/com/aisdlc/minibridge/MiniResearch.java:240`（`consistentReconcileChecks()`） | 對帳項由 Bridge 原始碼抽取；迷你 Bridge 回六項 | 抽取自動跟隨；`consistentReconcileChecks()` 補第七項 `delivery` | `CHECK_IDS` 加 `delivery`（AT-962-23-6） | PKG-API-P2 |
| 16 | `ScrDto.java:17,:30`、`ScrOpenRequest.java:16,:20`（`new ScrInput(…)`）與 SCR 讀取模型／配接器（現查 `ScrReadAdapter`）；`ResearchScrApiIT.java`（`reasonClass` 出現處） | 無 `evidenceUrl` | 三個 DTO／輸入／讀取模型各加可空 `evidenceUrl`；既有 AT 不傳該欄仍須綠 | D-139：`research_scr.evidence_url`（AT-962-15-6） | PKG-API-P2 |
| 17 | `RunConsumers.java:204-219`（`handle` 的 `tx.execute` 之後）與 `RunEventProcessor.java`（`Outcome`） | 無通知 | post-commit 通知＋唯讀旗標 `healingRelevant`；處理邏輯零改動 | AT-962-9-6；集合外追認（PACKAGES §6） | PKG-API-P2 |
| 18 | `ErrorResponseDocumentation.java:87,:151` 體例（新七個操作的逐操作狀態碼條目；檔名與完整性檢查現查） | 無新操作條目 | 加七項 | AT-962-24-3 | PKG-API-P2 |

### 4.2 Bridge 既有測試與 product 連動（PKG-DB-P2、PKG-BR-P2）

| # | 檔:行 | 現值 | 改後值 | 為何現值變了 | 持有包 |
|---|-------|------|--------|--------------|--------|
| 19 | `engine-bridge/tests/research_pg_support.py:30`（`LAST_VERSION = 20`）與檔頭敘述 | 20 | 21 | `migration_files()` 依數值序讀 21 個真檔（AT-962-1-8） | PKG-DB-P2 |
| 20 | `engine-bridge/tests/test_research_reconcile.py:92,:96,:490`（`[c["id"] …] == list(CHECK_IDS)`、註解『六項檢查名與順序不變』） | 六項 | 斷言自動跟隨七項；註解改『以 `CHECK_IDS` 為準』 | AT-962-23-1；`reconcile.py:53-54` 加 `delivery` | PKG-BR-P2 |
| 21 | `engine-bridge/tests/test_research_ast_locks.py:424-425`（`_NO_FSM_WRITE_MODULES`） | 五檔 | 加 `research/delivery.py`、`research/healing.py`（`inner_gates.py` 不加，另寫專屬規則） | AT-962-5-2、5-3（共享單點，歸 BR-P2） | PKG-BR-P2 |
| 22 | 同檔 `:31`（`EXEC_MODULES`）、`:340`（spawners 子集鎖）、`:443-448`（`create_key` 呼叫者）、`:104-166`（`gate_needs_guard` 與 C7） | 六檔；呼叫者 2／終點 4 | **皆不變**；新模組須滿足（`inner_gates.py` 三個字面 gate；不自起子行程） | AT-962-5-1、5-4；確認不紅 | PKG-BR-P2 |
| 23 | `engine-bridge/tests/test_research_gitops.py:113`（`[tag, -a, v1, -m, x]`、`[pr, create]`、`[release, create]` 皆拒）與 `:116`（`[pr, create]`、`[release, create, v1]` 的 `GitopsDenied`） | 三項皆拒 | `tag -a`（模板訊息）與 `pr create`（完整旗標）轉為允許；`release create`、缺旗標、`--force` 仍拒 | AT-962-2-1、2-2、2-E-1（**例外：不只改預期值，改正控／負控歸屬**） | PKG-BR-P2 |
| 24 | `engine-bridge/app/research/gitops.py:165`（`_MESSAGE_RES`）、`:174`（`parse_git`）、`:286`（`parse_gh`） | 無 tag／pr 形態 | 新增模板、形態與 `valid_semver` | product；AT-962-2-3、2-4 | PKG-BR-P2 |
| 25 | `engine-bridge/tests/test_research_capability.py:47-117`（`CAPABILITY`；`EXEC_DOORS` `:117`；實樹一對一） | 無四個新模組 | 加 `research/inner_gates.py`、`research/delivery.py`、`research/healing.py`、`routers/research_deliver.py`（類別依檔頭自述規則） | AT-962-5-5；新模組先登記 | PKG-BR-P2 |
| 26 | `engine-bridge/app/research/db.py:272`（`INSERT INTO {s}.research_gate_decisions (…)`）與 `:1122`（`INSERT INTO {s}.research_scr (…)`）、`:1355-1383`（`P1_OPS`、`ROUTE_OPS`、`OPS`）、`:1451`（查找鏈） | INSERT 無 `details`、`evidence_url`；查找鏈三表 | 兩個 INSERT 各加新欄（省略時預設值）；新增 `P2_OPS`、查找鏈第四表；`OPS`／`METHOD_KINDS`／`WRITE_METHODS` 不動 | product；AT-962-1-8、5-7、15-8（`test_research_db.py:156-158` 的一一對應鎖須仍綠） | PKG-BR-P2 |
| 27 | `engine-bridge/tests/fixtures/research/fake_gh/gh_fake.py:30-43`（只認 `auth status`、`repo create`；其餘走 `:43` unsupported） | 無 `pr` | 補 `pr create`、`pr list` 與 `FAKE_GH_MODE=fail-pr`、既有 `leak`；仍單檔、不加 shell 腳本 | AT-962-20-1、20-7 | PKG-BR-P2 |
| 28 | `engine-bridge/tests/test_sdd_cli.py:274,:390`（`ALLOWED_VERBS`、`RESEARCH_VERBS` 釘選） | 五個動詞 | **不變** | 確認不紅（AT-962-5-6） | PKG-BR-P2 |
| 29 | `engine-bridge/tests/test_research_scr.py`（P1 的 SCR AT，`reason_class` 出現於 `:112,:158-182,:291-331`） | 不帶 `evidence_url` | 只增新案例（AT-962-15-7、15-8）；既有 AT 零改動 | evidence_url 缺省 NULL | PKG-BR-P2 |
| 30 | `engine-bridge/app/research/scr.py:84-109,:239`、`routers/research_scr.py`（接受並驗證 `evidence_url`） | 無該欄 | 加欄與兩條驗證規則（⚖P2-11） | D-139；**PACKAGES 禁區補列**（⚖P2-17） | PKG-BR-P2 |
| 31 | `engine-bridge/tests/test_research_reconcile.py:331-339`（`test_AT_960_21_4_p0_has_only_the_gate_0_call_site_for_reconcile`：掃 `app/**` 的 `orchestrator.reconcile(` 呼叫點；`:339` 斷言 `sorted(檔名)==["app/routers/research.py"]*3`） | 3 個呼叫點、檔名集合恰為 `routers/research.py` | 4：新增 `reconcile_at_delivery` 助手的呼叫點，落 `routers/research.py`（與 `reconcile_at_route` 同款）；若實作改落 `research_deliver.py`，檔名集合同改 | AT-962-23-4；D-142 ⚖P2-15 更正、D-144 F-02（SD 首版 H19 掃錯檔，已更正） | PKG-BR-P2 |
| 32 | `engine-bridge/tests/test_research_reconcile.py:99-101`（`{id: present}` 六鍵整張字典 `==`） | 六鍵 | 七鍵：加 `delivery`（未交付時 present 為假） | `CHECK_IDS` 第七項（AT-962-23-1、23-3；D-144 F-03） | PKG-BR-P2 |
| 33 | `engine-bridge/app/research/db.py:67-87`（`EVENT_PAYLOAD_KEYS`）、`:89`（`EVENT_OPTIONAL_KEYS`）、`:349-357`（`append_event` 對未登記型別與鍵集合 fail-loud）；`engine-bridge/tests/test_research_events.py:195,:282`（以登記表做等式） | `research.delivery` 未登記 | 登記 `research.delivery`＝`{kind, ref, status, digest, reason, failure_step}`，可選鍵依 D-144 F-10；`test_research_events.py` 的等式與普查只改預期值 | AT-962-26-5、18-4、20-7（product 與測試同步） | PKG-BR-P2 |

### 4.3 frontend 既有測試與 product 連動（PKG-FE-P2A、PKG-FE-P2B、PKG-FE-W3、INT-P2）

| # | 檔:行 | 現值 | 改後值 | 為何現值變了 | 持有包 |
|---|-------|------|--------|--------------|--------|
| 34 | `frontend/lib/api/endpoints.test.ts:322`（`toHaveLength(118)`） | 118 | 125（七個新端點函式） | AT-962-24-5 | PKG-FE-P2A |
| 35 | `frontend/lib/domain/research.ts:749`（`RESEARCH_REASONS`）與 `:793` 起的 `RESEARCH_REASON_TEXT`；`frontend/lib/domain/research.test.ts:958-959`（`expect(values).toHaveLength(35)`） | 35 個；`toHaveLength(35)` | 加 `TAG_EXISTS`、`DELIVERY_STEP_FAILED` 與文案；`toHaveLength(37)` | AT-962-24-6；集合由 Java `ResearchReasonsTest.java:148` 讀此檔（⚖P2-14：PACKAGES 所稱 `lib/api/reasons.ts` 不是常數所在，該檔零 diff） | PKG-FE-P2A |
| 36 | `frontend/components/domain/research/ResearchWorkspaceView.test.tsx:228-233`（反向釘：整個工作區不得匹配 `/ResearchBackLink|開啟執行中心|開啟監控中心/`） | 整區禁 | 僅步驟 4 面板（已綁 consoleProjectId）允許連結字樣，其餘步驟仍禁 | AT-962-16-5；**例外：改斷言範圍** | PKG-FE-P2B |
| 37 | 同檔 `:188,:218,:243,:249,:264-326`（`research-placeholder` 與 `AT_961_19_1` 的 deliver 占位斷言） | deliver 仍是占位 | deliver 為 `DeliverPanel`；占位面板零個 | AT-962-21-1、25-2；**例外：改斷言範圍** | PKG-FE-P2B |
| 38 | `frontend/components/domain/research/ResearchWorkspaceView.tsx:66,:92,:248` 與 `BuildFrontPanel.tsx:43`；測試 `BuildFrontPanel.test.tsx:527-538`、`ResearchWorkspaceView.test.tsx:417-524` | 兩處漂移橫幅（`drift-banner`、`build-drift-banner`） | 只留工作區 `drift-banner`；面板內橫幅移除，兩處測試同改 | D-131(6)；AT-962-25-3；**例外：刪一個橫幅斷言組並改歸工作區** | PKG-FE-P2A（`ResearchWorkspaceView.tsx` 的 deliver 分支歸 P2B，橫幅整併歸 P2A，序列：A 先、B 後） |
| 39 | `frontend/components/domain/research/ResearchFlowHeader.test.tsx:123` 附近（反向斷言正則字面含四區塊名） | 字面掃描自我命中（P0 R-3） | 以字串拼接組正則，語意不變 | AT-962-25-4 | PKG-FE-P2A |
| 40 | `frontend/components/domain/research/InnerLoopLinks.tsx:6,:36,:51`（P1 註解『看板、自癒與終端屬 P2』與連結 href）與其測試 | href 無 researchId | href 加 `?researchId=<uuid>`、註解訂正 | AT-962-16-4 | PKG-FE-P2A |
| 41 | `frontend/lib/domain/research.ts:1850-1870`（`BUILD_DISABLED_TEXT.SCR_OPEN`、`executionBlock()`） | 已含 `scrOpen` 參數 | **簽名不變**（AT-962-15-5） | 確認不紅 | PKG-FE-P2A |
| 42 | `frontend/lib/nav/research-nav.test.ts:119,:125`、`registry.test.ts:140-145`（導覽列數、`mobile` 為 true 恰 6、`DELIVERED_NAV_ROWS` 前綴）與 `lib/help/{registry,content,lint,research-workspace}.test.ts` 的計數鎖 | P1 釘值 | **不變**（P2 不新增導覽列與說明頁） | 確認不紅（AT-962-25-1、25-5） | PKG-FE-P2A |
| 43 | `frontend/lib/api/schema.d.ts`（共享單點）、`lib/api/types.ts`、`tests/fixtures/research/*.ts` | P1 重產版 | 重產（七條新路徑、新 DTO、`ScrDto.evidenceUrl`）；手寫型改引生成型 | AT-962-27-1～27-3 | PKG-FE-W3 |
| 44 | `frontend/tests/e2e/research-docker.stack.spec.ts:339-346`（`checks.map(name).sort()` 的 `toEqual` 六名）與 `tests/e2e/README.md` | 六個對帳項名 | **例外**：只改 `:339-346` 的期望名單為七名（加 `delivery`）；其餘 P1 真棧 spec 不改；P2 另增 `research-deliver.stack.spec.ts` | `CHECK_IDS` 第七項；Docker 真棧 spec 只在 INT 跑、不在 CI（AT-962-23-7、28-4；D-144 F-03） | PKG-FE-W3（該檔列入其允許集合） |
| 45 | `frontend/components/domain/execute/ExecuteView.tsx`、`monitor/MonitorView.tsx` 與 `ExecuteView.test.tsx`、`ExecuteView.sdd.test.tsx`、`MonitorView.test.tsx` | 無回連 | 頂部掛 `ResearchBackLink`；各測試只增案例；`ExecuteView.sdd.test.tsx` 現查不受影響 | AT-962-16-2、16-3；集合外追認 | PKG-FE-P2B |
| 46 | `frontend/lib/domain/research.test.ts:710-714`（`Object.keys(RECONCILE_CHECK_LABEL)` `toEqual(SIX_CHECKS)`、`Set size 6`）與 `frontend/lib/domain/research.ts:518-525`（`RECONCILE_CHECK_LABEL` 標籤表） | 六個標籤 | 標籤表加 `delivery`＝『交付』；測試的名單與 `Set size` 改七（只改預期值） | `CHECK_IDS` 第七項（AT-962-23-7；D-144 F-03；共享單點歸 FE-P2A） | PKG-FE-P2A |

### 4.4 凍結文件的勘誤（不得改凍結檔；主控於 RELEASE_READY 的 refreeze 批次各補一列勘誤；方向依 D-138～D-140）

| # | 凍結檔:位置 | 現有陳述 | 勘誤內容 |
|---|-------------|----------|----------|
| E1 | `AgentConsole/docs/02_architecture/API_Contract_ResearchToPRD.md` §1.1、§1.3、§1.4、§2.2、§3、§0.2 | 缺 API-RP-26、27、28 與五個 Bridge 端點；API-RP-17 缺 `push?`；API-RP-23 缺 `reviewerIndependent`；`research.delivery` payload 為 `{kind, ref, status}`；`research.alert.kind` 缺兩值；缺 2 個 reason；對帳 checks 為六項 | D-140 #1、#9、#11、#14、D-138 Q-1、D-139：補列；`push?`；`createGithubRelease` 註 P2 不實作；payload 定為固定六鍵 `{kind, ref, status, digest, reason, failure_step}`（D-145；`commitSha` 只在 `research_deliveries` 列、不進事件）；alert kind 加 `SPEC_CHANGE_FORBIDDEN`、`HEALING_LOG_TRUNCATED`；reason 加 2；checks id 列以 `CHECK_IDS` 為準 |
| E2 | `AgentConsole/docs/02_architecture/Architecture.md` §11.3′（新增 K.6）、§11.1、§5 | K.4 止於 V19／V20；reason 表 35；無 V21 | D-139：落檔 K.6（V21 DDL 全文，取 `V21_DDL.md`）；reason 表補 2；`research_deliveries` 補 `snapshot_sha256` 說明 |
| E3 | `AgentConsole/docs/02_architecture/ADR-003-ResearchToPRD.md` D16 與 §4 | 白名單無 tag／pr 形態 | IFACE §6.3：補列六個 git 形態與兩個 gh 形態、仍禁清單、`valid_semver` 與 tag 訊息模板 |
| E4 | `docs/01_requirements/ResearchToPRD_PRD.md` :774、:781、:393、:816、AC-R2P-16-5、:747、:746、:795 | `lib/sse/`；`GET /signoffs/pending`；R10 欄位；追溯來源 RTM；AC-16-5『被拒』；`views/` 路徑；RELEASE_READY 登錄；證據連結 | D-140 #2、#3、#4、#5、#6、#7、#8、#12：路徑勘誤；待辦取 `kanban.pendingReviews`；attempt 讀端導出、歸因與補丁結果引擎未提供；追溯來源改 R8 加任務終態；AC-16-5 拆兩半；RELEASE_READY FAIL 為 `gate=SCG6`；證據連結入 `evidence_url`；出口 (b)『真實』註明引擎真、claude 為 mock（#13） |
| E5 | `AgentConsole/docs/03_testing/contracts/TCS-ResearchToPRD-P1-20261107.md` §1.3、AT-961-8-x、AT-961-20-x、AT-961-19-1 | 『P2 的 tag、pr、release 為拒』『對帳六項』『deliver 仍占位』 | 只改歸屬註記：P2 起 tag 與 pr 形態轉允許（本檔 §4）、對帳加第七項、占位為零；P1 的 AT 編號與數不變 |
| E6 | `docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md` D2 與 `HELM_DECISIONS` 的 D-45 | 『P0／P1 不呼叫內環 gate』 | P2 起 `POST …/gates` 實作，D-45 不再約束 P2（P1 ⚖P1-27 已預告）；動詞集合不變 |

### 4.5 硬釘掃描（掃描指令與逐字結果見自查檔 `_aux/HARDPIN_SCAN.txt`，三十二項；對 `backend/src/{main,test}`、`frontend/{lib,components,tests}`、`engine-bridge/{app,tests}` 重掃）

> 判準：既有測試以「精確集合、個數、原始碼字串、全樹 AST 或文字掃描」釘住某個會因本期而變的事實。本輪掃過：Flyway 版本清單與 gate 列舉、既有表快照、`OpenApiIT` 計數與三張表、reason 集合與兩份勘誤待辦名單、RBAC 清單與 `SecurityConfig` 規則、`CHECK_IDS` 與迷你 Bridge、AST 鎖與能力登記與動詞表、gitops 允許表測試、`db.py` 操作登記與兩個 INSERT、假 gh 模式表、端點函式總數、占位面板與反向釘、兩處漂移橫幅、`RESEARCH_REASONS`、導覽與說明計數鎖、SCR DTO、真棧 spec、console-api 研究表寫入掃描（H30 為零命中＝預期）。逐筆判讀：上列 §4.1 至 §4.4；其餘命中與本期無關（見自查檔）。SD 另現查並如實登記與 ARCH 文件不符的事實：⚖P2-14（`RESEARCH_REASONS` 住 `research.ts`）；對帳呼叫點鎖**存在**於 `test_research_reconcile.py:331`（SD 首版 H19 曾掃錯檔，D-142 更正，已列入本節 §4.2；⚖P2-15）。QA 一審（D-144）補列：第七項 `delivery` 的連動三處（`test_research_reconcile.py:99-101`、`research.test.ts:710-714` 與標籤表、`research-docker.stack.spec.ts:339-346`）、`research.test.ts:958-959`、`EVENT_PAYLOAD_KEYS`。


### 4.6 RELEASE_READY 勘誤補列（〔勘誤 2026-11-08〕D-148～D-167；實作期揭露的硬釘與座標，列號 47 起接 §4.3；只登記、不改上列既有列的原文）

| # | 檔:行 | 現值 | 改後值 | 為何現值變了 | 持有包 |
|---|-------|------|--------|--------------|--------|
| 47 | `frontend/lib/api/si.endpoints.test.ts:44-46`（`toHaveLength(118)`） | 118 | 125 | 七個新端點函式使 SelfImproving 端點測試所數的全站函式總數上升（D-148 FE-2；§4.3#34 只列了 `endpoints.test.ts:322`） | PKG-FE-P2A |
| 48 | P1 既有測試 `AT_961_18_5`、`AT_961_18_6`、`AT_961_20_E_4` 三處斷言（P1 工作區測試） | 18-5「面板不含看板…」；18-6「沒有發起 SCR 的鈕」；20-E-4 面板內 `build-drift-banner` | 18-5「內環鍵未採納時不渲染」並加 25-3a；18-6「有、規格變更中停用並顯示登記文案」；20-E-4 的 `build-drift-banner` 依 D-131(6) 刪除、歸工作區單一橫幅（SCR 橫幅整併為單一 `scr-banner`，文案為 P1 斷言與 AC-962-15-5 的超集） | P2 把看板、SCR 鈕與橫幅接進同一面板（D-155）；**同時登記到 TCS-P1 勘誤表** | PKG-FE-P2A |
| 49 | §4.3#37 座標（`ResearchWorkspaceView.test.tsx`） | `:188,:218,:243,:249,:264-326` | 擴充為 `:188`、`:228-233`、`:246-252`、`:264-326`、`:305-328`、`:678` | FE-P2B 實際改動的 hunk 座標（D-150#8） | PKG-FE-P2B |
| 50 | §4.1#12（`ResearchReasonsTest.java` 兩份 `*_ERRATUM_PENDING`） | 「各加兩項」 | 名單只加 `delivery_step_failed`（契約 §0.2 與 Architecture §11.1 已含 `tag_exists`）；本批勘誤落地後兩份名單清空 | D-149#10 | PKG-API-P2；清空由 PKG-ERRATA-P2 |
| 51 | §4.1#17（`RunEventProcessor.Outcome`） | 「post-commit 通知＋唯讀旗標」 | `Outcome` 保留三參數次要建構子（`healingRelevant=false`）；record 加欄時呼叫點在允許集合內者改呼叫點、集合外才保留舊元數次要建構子 | D-149#2、#6 | PKG-API-P2 |
| 52 | §4.1#18（`ErrorResponseDocumentation.java`） | 「加七項」 | 預期零改動：落點為 `ResearchErrorDocs`（逐操作狀態碼由它驅動） | D-149#11 | PKG-API-P2 |
| 53 | AC-962-1 全部「21」（AT-962-1-1 的「歷史 1 至 21」、六處 Flyway 版本清單 IT、`research_pg_support.LAST_VERSION`、§4.1#1／#2／#19） | 21 | 22；AT-962-1-1 改「歷史 1 至 22」；AT-962-1-8 判準改「`LAST_VERSION`≥21 且遷移檔數等於 `LAST_VERSION`」 | V22 放寬 `flow_phase` CHECK（PKG-DB-P2b，commit ee5bd46d） | PKG-DB-P2b |

---
## 5. 測試資料規格

### 5.1 值域常數（測試與產品碼共用同一份常數，不各寫一份；初值標「未校準」者以常數登記並以測試釘住）

| 常數 | 值 | 來源 |
|------|-----|------|
| 內環 gate 值（console-api 請求） | `PR_REVIEW`、`RTM_VERIFY`、`RELEASE_READY`；`result`：`PASS`、`FAIL`；`(RELEASE_READY, PASS)` 一律 422 | IFACE §2.1；W-R2P4 |
| 決定列 gate 映射 | PR_REVIEW→`SCG4`；RTM_VERIFY→`SCG5`；RELEASE_READY→`SCG6`；PASS→`APPROVED`、FAIL→`REJECTED` | D-138、D-139；V21 |
| `details` 鍵 | `reviewer_independent`（布林）、`review_report_ref`（字串或 null）、`ci_red`（布林） | D-139 |
| gates 欄位邊界 | `reason` 1 至 500 字（FAIL 必填）；`reviewReportRef` 至多 300 字；`reviewerIndependent` 於 PR_REVIEW 必為 true | IFACE §2.1 |
| RETRY_LIMITS | PR_REVIEW 5、RTM_VERIFY 2、RELEASE_READY 2（常數取 `transition_rules.py:267-274`，測試不內嵌第二份；超限 ESCALATION 以引擎回傳為準） | IFACE §2.2 |
| `excerpt` 長度 | 遮蔽後尾端 300 字元（以字元計） | IFACE §3.2；AT-962-6-4 |
| `HEALING_LOG_MAX_BYTES` | `2097152`（2 MiB）；越界寫一次 `{"truncated":true}` 並發 `research.alert{kind:HEALING_LOG_TRUNCATED}` | IFACE §3.3；AT-962-6-5 |
| `maxRetries` | 系統參數 `agent.maxRetries`，初值 3 | V2:27；AT-962-9-2 |
| 看板去抖與預算 | 去抖 100 ms；SSE 幀到 DOM 至多 500 ms（單一常數住 `lib/domain/research.ts`） | IFACE §1.5；AT-962-11-3 |
| gates 清單筆數 | SCG4、SCG5、SCG6 各最近 5 筆 | IFACE §1.2；⚖P2-8 |
| 終端開合鍵 | `localStorage` 鍵 `research.terminal.open`，預設收合 | IFACE §4.1 |
| 稍後處理鍵 | `sessionStorage` 鍵 `research.decision.snoozed`（本檔類推） | ⚖P2-10 |
| `tagName` 正規式 | `^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$`，長度至多 64；Bridge 與 console-api 逐字相同 | IFACE §6.2；AT-962-2-4、19-3 |
| tag 訊息模板 | `release: <tagName>（RP-<NNNN>，追溯快照 sha256 <前 12 碼小寫十六進位>）`；使用者 `message` 至多 200 字，只入 `detail`（至多 2000 字、已遮蔽） | IFACE §6.2、§6.3 |
| PR 模板 | 標題 `feat: <RP-NNNN> <研究專案 title 截 60 字>（<FR 數> FR／<AC 數> AC）`；內文四段（摘要、追溯表摘要、規格依據、確認）至多 4000 字 | IFACE §6.4 |
| 追溯表欄位 | `ac`、`userStory`、`gherkinSummary`（每段至多 120 字）、`unitStatus`（`PASS`、`FAIL`、`NOT_RUN`、`NONE`）、`e2eStatus`（`PASS`、`NOT_RUN`）、`lastRunAt`、`source` | IFACE §6.1 |
| 快照檔 | `03_execution/traceability_matrix.json`；鍵序固定、`ensure_ascii=False`、LF；sha256 入 `research_deliveries.snapshot_sha256` | IFACE §6.2；D-139 |
| `evidence_url` | NULL 或 `^https://` 開頭、至多 500 字元；不在受控更新清單 | D-139 |
| 新 reason | `tag_exists`（409）、`delivery_step_failed`（502，`details.failure_step`∈`push`｜`pr_create`｜`fsm_release`｜`tag`）；四方鎖 37 | IFACE §9.3；D-138 Q-14 |
| 新 SSE 內容 | `research.delivery` payload 鍵集合＝`{kind, ref, status, digest, reason, failure_step}`（成功：`ref` 非 null、`failure_step` 為 null；失敗：`ref` 為 null、`failure_step` 必填，值∈`push`｜`pr_create`｜`fsm_release`｜`tag`），並登記進 `db.py` 的 `EVENT_PAYLOAD_KEYS`；`research.alert.kind` 加 `SPEC_CHANGE_FORBIDDEN`、`HEALING_LOG_TRUNCATED` | D-144 F-10；IFACE §9.2 |
| `unmet[]` 項名 | `tasks_incomplete`、`rtm_below_100`、`rtm_unavailable`、`not_release_ready`、`scr_open`、`no_console_project`（⚖P2-6）、`prd_not_frozen`（⚖P2-12） | IFACE §2.1、§6.2 |
| `digest_mismatch` | 既有 P0 reason（422）：`:tag` 與 `:gates` 前置漂移；`details.drift[{path, expected_sha256, actual_sha256}]`；四方鎖不增 | D-142 ⚖P2-9 |
| 端點計數 | `OpenApiIT` 路徑 114、操作 131；`endpoints.test.ts` 125；自算法見 AT-962-24-2 | §4 |
| 新端點（console-api） | `GET …/kanban`（`getResearchKanban`）、`POST …/gates`（`registerResearchGate`）、`GET …/healing`（`getResearchHealing`）、`GET …/delivery`（`getResearchDelivery`）、`POST …/delivery/tag`（`createResearchTag`）、`POST …/delivery/pr`（`createResearchPr`）、`GET …/delivery/traceability`（`getResearchTraceability`） | IFACE §0 |
| 新端點（Bridge） | `:gates`、`:tag`、`:pr`、`:traceability-preview`、`:healing-sync`（內部） | IFACE §0 |
| 唯讀提示 | `title` 為『權限不足（唯讀角色）』（看板與按鈕）或『權限不足』（決策彈窗，沿 P0 W-R9） | P0／P1 先例 |

### 5.2 夾具倉（路徑相對 `AgentConsole/engine-bridge/tests/`，凍結複本、hermetic、無網路）

- **拋棄式 git 夾具** `research_git_support.py`（沿 P1）：真 git 只在 `$env:TEMP`；P2 加 `file://` 的 bare repo 當 origin（驗 `push` 與 `ls-remote`，測後刪除）；`HOME`、`GIT_CONFIG_GLOBAL`、`GIT_CONFIG_SYSTEM` 指向暫存空檔。
- **假 gh 夾具** `fixtures/research/fake_gh/gh_fake.py`（沿 P1，BR-P2 補 `pr create`、`pr list`、`FAKE_GH_MODE=fail-pr`；既有 `ok`、`unauth`、`fail-create`、`leak` 不改）；Windows 為 `gh.cmd` 薄殼、POSIX 為 sh 腳本，皆已存在，不新增目錄；另一平台形態標『未驗』。假 token 字面：`ghp_FAKE_R2P2_TOKEN_000000000000000000`。
- **遮蔽夾具** `engine-bridge/tests/fixtures/research/healing_redaction_cases.json`（`[{input, expected, keep?}]`；BR-P2 建、API-P2 只讀；pytest 與 JUnit 同讀＝兩端對拍的唯一機械鎖）。
- **內環失敗劇本** `fixtures/research/scripts/inner_fail.json`（BR-P2；僅當現查 `mock_claude.py` 現有機制不足時才建，列 V-D6）。
- **暫存 FSM 狀態目錄**（沿計畫書附錄 A）：對 `:gates` 現態矩陣每一列各跑一次，`decision_trace` 與人工等價序列 diff。
- **資料庫夾具** `research_pg_support.py`：`make_research_db()` 套到 V21（`LAST_VERSION=21`）；Testcontainers（backend）。
- **迷你 Bridge**（backend 測試樹 `com.aisdlc.minibridge`；`MiniResearch`、`MiniResearchController`）：補 `:gates`、`:tag`、`:pr`、`:traceability-preview`、`:healing-sync` 行為與 `/sdd/fsm` 視圖；回應形狀以 IFACE 為準先行。
- **frontend 夾具** `tests/fixtures/research/`：kanban（五欄、不可達、待審）、healing（含漂移與 null 欄）、gates、traceability、delivery 概覽、SSE 事件流；假 `EventSource` 與假計時器。
- **Docker 全棧**（INT）：mock claude；容器無 repo 寫入掛載與 gh，只驗唯讀面與負控；真 git／gh 路徑走本機模式。

### 5.3 hermetic 環境

- 一律無網路外呼：真 git 只在 `$env:TEMP` 下的拋棄式 clone 與 `file://` bare repo；`gh` 一律假夾具；headless claude 一律 `aisdlc-mock-claude`；GitHub 等真端點在任何 AT 中都不被連線（AT-962-28-E-3）。真網路只出現在 V-H6（掌舵者真機）。
- DB 型 AT 只用拋棄式資料庫（`RDB` 或 Testcontainers），絕不連真 `aisdlc` 資料庫；真 `~/.autosdd/`、真 `AgentConsole/build/reports/fsm`、真工作區根、真 repo 一律唯讀；FSM 實跑一律在暫存狀態目錄。
- 時間以假時鐘注入（去抖、逾時、心跳、SSE 緩衝、500ms 預算）；任何測試不得 `sleep` 超過 2 秒等待真時間；前端 ≤500ms 一律假計時器與假 EventSource，不用牆鐘（負載敏感測試教訓，N-02）。
- 清理義務（掌舵者 2026-11-07 指令）：每個整合與 INT AT 收尾清掉自建的 subst 磁碟機、副本目錄、worktree、bare repo、行程、拋棄式資料庫、Docker 測試標籤與懸空卷（AT-962-28-E-2）；證據檔列「殘留清單」（沒有寫「無殘留」）。

### 5.7 允許變更的檔案集合（各包開發 agent 只准動自己包的檔；路徑相對 monorepo 根；本節為 PACKAGES-P2 §2 的收斂並依 D-139、D-141 增補，兩者不一致以較窄者為準並回報主控）

> 共同禁區（任何包皆不得動）：根 `CLAUDE.md`、`.claude/`、`tools/`、`.github/`、`AutoClaude/`、`AISDLC_SDD/`（含 LATEST）、`AgentConsole/CLAUDE.md`、`docs/**`、`AgentConsole/docs/**`（文件一律由主控與 SD 寫；開發棒零文件）、`.gitignore`、`package.json` 與 `package-lock.json`（P2 零新相依）、`docker-compose*.yml`、`Dockerfile`、`AgentConsole/docker/**`、Flyway 已發佈檔 V1～V20、`app/sdd_cli.py`（動詞集合鎖）、`app/rtm.py`、`routers/{sdd,autoclaude}.py`、`ExecutionController`、`SecurityConfig`、`ResearchFlowPolicy.java`、`lib/nav/registry.ts`、`app/layout.tsx`、`components/layout/**`、`LiveLogCard.tsx`、`useRunStream.ts`、`LogPanel.tsx`。共享單點：`OpenApiIT` 計數與 `ResearchReasonsTest` 名單只給 PKG-API-P2；`lib/api/schema.d.ts` 只給 PKG-FE-W3；`lib/api/{endpoints,queries,types}.ts`、`lib/domain/research.ts`、說明登記表、`tests/helpers/research.tsx` 只給 PKG-FE-P2A；`test_research_capability.py`、`test_research_ast_locks.py`、`db.py`、`routers/research.py`、`reconcile.py` 只給 PKG-BR-P2；`research_pg_support.py` 的 `LAST_VERSION` 歸 PKG-DB-P2。

| 包 | 允許變更的檔案集合 |
|----|--------------------|
| PKG-DB-P2 | `AgentConsole/backend/src/main/resources/db/migration/V21__research_gate_details_delivery_snapshot.sql`（新；逐字取 Architecture K.6，不得自改）；`backend/src/test/java/com/aisdlc/console/infrastructure/persistence/{ResearchSchemaMigrationIT,SchemaMigrationIT,V5UpgradeMigrationIT,IssuePriorityMigrationIT,BackupJobMigrationIT,SiConsoleWritesMigrationIT}.java`（§4 第 1～5 列）；`engine-bridge/tests/research_pg_support.py`（`LAST_VERSION`） |
| PKG-DB-P2b（〔勘誤 2026-11-08 新列；D-162(a)〕） | `AgentConsole/backend/src/main/resources/db/migration/V22__research_flow_phase_delivered.sql`（新；逐字取 Architecture K.7，不得自改）；七處 Flyway 版本清單與 V22 區塊的 IT 站點（`backend/src/test/java/com/aisdlc/console/infrastructure/persistence/{ResearchSchemaMigrationIT,SchemaMigrationIT,V5UpgradeMigrationIT,IssuePriorityMigrationIT,BackupJobMigrationIT,SiConsoleWritesMigrationIT}.java`，含 `AT_962_1b_1～1b_4`）；`engine-bridge/tests/research_pg_support.py`（`LAST_VERSION` 21→22） |
| PKG-BR-P2 | `AgentConsole/engine-bridge/app/research/{inner_gates,delivery,healing}.py`（新）、`app/routers/research_deliver.py`（新；`:gates`、`:tag`、`:pr`、`:traceability-preview`、`:healing-sync`）、`app/routers/research.py`（檔尾 `include_router`、`reconcile_at_delivery`、`:reconcile` 尾端順帶 `healing.sync`；集合外追認同 D-134(1)）、`app/research/gitops.py`、`app/research/db.py`（`P2_OPS`、`_op_delivery_record`、`list_healing_attempts`、兩個 INSERT 加新欄）、`app/research/gates/reconcile.py`（`delivery`）、`app/research/scr.py` 與 `app/routers/research_scr.py`（只為 `evidence_url`；⚖P2-17 補列）；測試 `tests/test_research_{inner_gates,delivery,healing,deliver_router,int_p2}.py`（`int_p2` 由 INT 棒執行）、`tests/test_research_{gitops,reconcile,ast_locks,capability,db,scr,events}.py`（只增與只改預期值，§4）、`tests/fixtures/research/{healing_redaction_cases.json,scripts/inner_fail.json,fake_gh/gh_fake.py}`；〔勘誤 2026-11-08；D-162〕追認 `app/research/orchestrator.py`（`reconcile` 的 `checks` 清單加第七項 `_delivery_check`，非動它不可）與 `tests/research_git_support.py`（`make_route_db` 改 `make_research_db()`，套到 V21）；不得動 `sdd_cli.py`、`rtm.py`、`routers/{sdd,autoclaude}.py`、`research/{route,adopt,decompose_plan,fsm_ops}.py` |
| PKG-API-P2 | `AgentConsole/backend/src/main/java/com/aisdlc/console/**` 研究相關新檔（`ResearchDeliveryController`、`ResearchGateController`、`ResearchKanbanController`、`ResearchHealingController`、DTO `KanbanDto`、`GateRegisterRequest`、`GateRegisterResult`、`HealingDto`、`DeliveryOverviewDto`、`TagRequest`、`PrRequest`、`TraceabilityDto`、`Research{Kanban,Gate,Healing,Delivery}Service`、`ResearchHealingNotifier`、`{Kanban,Healing,Delivery}ReadAdapter`、`HealingExcerptMasker`）與既有檔（`BridgeEndpoints`、`BridgeHttpAdapter`、`RunConsumers`、`RunEventProcessor`、`ErrorReasons`、`ResearchErrorDocs`、`ErrorResponseDocumentation`、`ScrDto`、`ScrOpenRequest`、SCR 讀取與服務、records/audit 讀配接器）；`backend/src/test/**`（`ResearchKanbanApiIT`、`ResearchKanbanRouteInventoryTest`、`ResearchGateApiIT`、`ResearchHealingApiIT`、`ResearchDeliveryApiIT`、`HealingExcerptMaskerTest`、`ResearchHealingNotifierTest` 新檔；`OpenApiIT`、`ResearchReasonsTest`、`RbacIT`、`ResearchApiIT`、`ResearchBridgeShapeTest`、`ResearchArchTest`、`ResearchScrApiIT`、`MiniResearch*` 只增與只改預期值）、`src/test/resources/research/**`；〔勘誤 2026-11-08；D-149#1／#2／#3／#9、D-159 E#3〕追認新檔與既有檔：七個新埠 `application/port/in/Research{Kanban,Gate,Healing,Delivery}UseCase`、`application/port/out/Research{Kanban,Healing,Delivery}ReadPort`、`ResearchBridge.java`（加五個方法）、`ResearchScrUseCase.java`、`ResearchRouteViews.java`、`ResearchExceptionHandler.java`、`ResearchScrService.java`、測試側 `minibridge/MiniDeliveryBehaviors.java`、`support/ResearchP2Fixtures.java`，並承接 `ResearchSchemaMigrationIT` 的 AT-962-22-5（DB-P2 已 commit、無並行持有者；API-P2 計七十六個 AT）；不改 `SecurityConfig`、`ResearchFlowPolicy`、`ExecutionController`、Flyway |
| PKG-FE-P2A | `AgentConsole/frontend/components/domain/research/{KanbanBoard,KanbanColumn,HealingMonitor,TerminalPane,DecisionModal,GateRegisterDialog,ScrRequestDialog,ScrBanner,PendingReviewList}.tsx`＋測試；`BuildFrontPanel.tsx`、`InnerLoopLinks.tsx`、`ResearchFlowHeader.test.tsx`、`ResearchWorkspaceView.tsx`（僅漂移橫幅整併）與其測試的橫幅段；共享單點 `lib/api/{types,endpoints,queries}.ts`＋`endpoints.test.ts`、`lib/domain/research.ts`＋`research.test.ts`（含 `RESEARCH_REASONS`）、`lib/help/research-workspace.ts`（步驟 4 其餘與步驟 5 的欄位釋義一次寫完）、`lib/help/states.ts`（若需要）、`tests/helpers/research.tsx`、`tests/fixtures/research/*.ts`、`tests/e2e/research-kanban.mock.spec.ts`、`tests/e2e/a11y.mock.spec.ts`（追加）；〔勘誤 2026-11-08〕追認 `lib/api/si.endpoints.test.ts`（D-148 FE-2）與 `tests/e2e/research-build-front.mock.spec.ts`（一處 execute href 加 `?researchId=`，D-155）；不得動 `app/layout.tsx`、`components/layout/**`、`lib/nav/registry.ts`、`LiveLogCard.tsx`、`useRunStream.ts`、`LogPanel.tsx`、`package.json`、`schema.d.ts`、`lib/api/reasons.ts` |
| PKG-FE-P2B | `AgentConsole/frontend/components/domain/research/{DeliverPanel,TraceabilityTable,ReleaseActions,TagConfirmDialog,PrConfirmDialog,ResearchBackLink}.tsx`＋測試；`ResearchWorkspaceView.tsx`（deliver 分支）與其測試（§4 第 16、17 列）；`components/domain/execute/{ExecuteView,ExecuteView.test,ExecuteView.sdd.test}.tsx`、`components/domain/monitor/{MonitorView,MonitorView.test}.tsx`；`tests/e2e/research-deliver.mock.spec.ts`；FE-P2A 收卷後才開、對共享單點只 import 不改；〔勘誤 2026-11-08〕追認：`lib/help/research-workspace.ts`（僅 `sourceFiles` 增列自己的新元件檔，D-156）、`lib/domain/research.ts`＋`research.test.ts`（僅 semver 正規式、Tag／PR 上限、「僅 ADMIN」文案與 `DELIVER_LABEL` 常數，D-157）、`lib/api/types.ts` 的追溯列型別與 `frTotal`、`tests/fixtures/research/p2.ts` 的追溯夾具、`TraceabilityTable` 渲染三段與來源清單（D-158） |
| PKG-FE-W3 | `AgentConsole/frontend/lib/api/schema.d.ts`（重產；唯一歸屬）、`lib/api/types.ts`（手寫型改引生成型）、`tests/fixtures/research/*.ts`（補必填欄）與對應 `*.test.ts(x)`（只改預期值）、`tests/e2e/research-docker.stack.spec.ts` 的 `:339-346` 期望名單（只改預期值，D-144 F-03）；API-P2 收卷與 P1 修復棒收卷之後才開；不得動元件邏輯；〔勘誤 2026-11-08〕追認：`lib/api/types.test.ts`（新；D-152#1）、`HealingMonitor.tsx`／`HealingMonitor.test.tsx`／`tests/fixtures/research/p2.ts`／`tests/e2e/a11y.mock.spec.ts` 該行／`types.ts` 的 `ResearchHealing`（欄名 `logBehind`→`logLag` 並補四欄；D-161）、`DecisionModal.tsx`／`TagConfirmDialog.tsx` 與其測試（生成型把可空欄標為 null 後的 `?? ""` 處理，非功能變更；D-163） |
| INT-P2 | `AgentConsole/engine-bridge/tests/test_research_int_p2.py`、`tests/fixtures/research/fake_gh/**`（沿用）、`frontend/tests/e2e/research-deliver.stack.spec.ts`；Docker 與本機模式實跑；證據檔由主控落檔；〔勘誤 2026-11-08〕證據檔＝`AgentConsole/docs/06_quality/INT-ResearchToPRD-P2-20261108.md`（第二套拋棄式棧補跑 AT-962-28-3／28-4／28-5，D-153#1、D-166） |

> **FIX 包**：修復棒的允許集合＝原包集合∪審查報告指名的檔（見〈提交順序與責任〉）。

---

## 6. RTM 連結確認

### 6.1 追溯與 PRD §8.1 P2 出口 (a)～(i) 對映
RTM 子表 `AgentConsole/docs/06_quality/RTM-ResearchToPRD-P2-20261107.md`（列數見 §1 計數；F 1、US 3、AC 與 AT 逐列）；`RTM.md` 的 §2.10 存根補一行 P2 引言（不計入 §2 總列數與 US 58）。每完成一項需求即回填四格（實作檔、自動測試、E2E 驗證、狀態），不得刪列、改號、合併列（`AgentConsole/CLAUDE.md` 鐵律 12）。

| 出口判準（PRD :1082） | 對應 AT 與 V |
|----------------------|--------------|
| (a) 內環走完到交付（RELEASE_READY→RELEASE、Tag、PR URL、M2、M3） | AT-962-28-1、AT-962-28-2、AT-962-18-1、AT-962-20-1、AT-962-22-1、V-H5 |
| (b) 至少一次 ESCALATED 或待審彈窗（真實：引擎真重試耗盡、claude 為 mock，須標明） | AT-962-28-3、AT-962-28-4、AT-962-14-1、AT-962-12-3、AT-962-9-3、V-D6 |
| (c) 至少一次 SCR 演練（從看板 UI 發起 MINOR） | AT-962-28-5、AT-962-15-3、AT-962-15-5 |
| (d) 看板差分綠 | AT-962-10-1、AT-962-10-2、AT-962-10-3、AT-962-10-4、AT-962-10-5 |
| (e) 終端窗格靜態判準綠 | AT-962-13-2、AT-962-13-E-1 |
| (f) 視圖對真失敗步驟有列 | AT-962-28-3、AT-962-6-1 |
| (g) 交付時點對帳 ok | AT-962-28-6、AT-962-23-4、AT-962-23-2 |
| (h) `ResearchBackLink` 兩頁 AT 綠 | AT-962-16-1、AT-962-16-2、AT-962-16-3 |
| (i) 掌舵者真機五步（附 sid 與 line） | V-H5 |

### 6.2 V 系列：實查檢核（主控、整合棒、掌舵者；**不是 AT**；證據文字逐字貼入 P2 證據檔與 RTM 的 E2E 驗證欄，未驗者如實標「未驗」）

- **V-S1**（AC-962-8；AC-R2P-16-5『被拒』半）框架 hooks 對凍結檔補丁的實際攔截：Bridge 起的 run 是否帶 SDD 三件組使 hooks 生效（推論，未查證）；INT 以真 AutoClaude 對暫存專案凍結檔下手，量 sha 與 hook deny 記錄。結果寫入證據；若不攔，P2 不聲稱『被拒』，另案框架側（本鍵不得改框架樹）
- **V-D5**（AC-962-11；AC-R2P-15-3）『FSM 檔改變→看板更新』端到端上界量測（劃界 (d)-1：內環 FSM 無推播）：INT 量測中位數與最大值並記錄；不充當 AT
- **V-D6**（AC-962-28）`mock_claude.py` 是否能驅動內環 playbook 出 RETRYING、FAILED、ESCALATED 的現查（決定是否需 `inner_fail.json`；真路徑為引擎真重試耗盡、claude 為 mock 可執行檔，D-140 #13）
- **V-D7**（AC-962-13；AC-R2P-17-4）`useRunStream` 與 `LiveLogCard` 的 DOM 純文字行為與 `steps?afterSeq` 回補是否含完整 log 行（劃界 (d)-4）；若不含，AT-962-13-4 的『與結束前一致』以夾具態成立並如實標示
- **V-D8**（AC-962-8）Bridge 起 AutoClaude run 時 `SDD_ACTIVE_VERSION`、`SDD_STATE_DIR`、`SDD_PROJECT` 三件組是否被帶入子行程環境（與 V-S1 同一次取證）
- **V-H5**（AC-R2P-15、16、18、20；PRD §8.1 P2 出口 (i)）掌舵者真機五步（IFACE §10.6）：(1) `/research` 開啟已 Gate 0 專案並分流；(2) 步驟 4 簽核拆解、TCS 凍結、啟動執行；(3) 看板上看到自癒或彈窗（或故障注入）並處理一次；(4) 登錄 SCG-4 與 SCG-5；(5) 步驟 5 追溯表全綠→建立 Tag（本機或 Private 測試庫二擇一，標明）→（可選）建立 PR。附 sid 與 line；構造情境不能充當
- **V-H6**（AC-962-18、20）真 GitHub 的 Tag 推送與 PR（Private 測試庫）由掌舵者以互動選項決定是否執行；不阻擋 RELEASE（沿 D-92）；代驗面以 `file://` bare origin 與假 gh 涵蓋
- **V-C2**（AC-962-30）Architecture §5.4 檢查表（P2 版）逐項人讀對照（SCG-4 報告 §B）
- **掌舵者目視項**（—）看板五欄、自癒監視器、終端窗格、決策彈窗、SCR 表單、步驟 5 追溯表與確認框在大、中、小三種寬度的觀感；結果記為文字，不充當 AT
- **macOS 與 Linux 未驗項**（—）本鍵在 Windows 實作與驗證；POSIX 形態假 gh、`file://` bare repo 的路徑形態、symlink 子情境一律標『未驗』，不得以 Windows 結果代表（NFR-R2P-10-3）

---

## 7. 本檔採用的預設裁決（SD 依 PRD、ADR、契約與主控裁決 D-87～D-141、IFACE-P2 與 PACKAGES-P2 判定；凡 PRD 與契約沒定到而 AT 需要的常數與形態都在此列；狀態「採納」＝主控裁決已定、「待裁決」＝SD 預設值、主控可推翻，推翻時走勘誤；「取代」＝依 D-138～D-141 取代 IFACE-P2 的對應陳述）

| ⚖ | 狀態 | 裁決 | 來源或「本檔類推」 | WHY |
|----|------|------|-------------------|-----|
| ⚖P2-1 | 採納 D-142 | RELEASE 的 `transition --to RELEASE` 只住 `inner_gates.release_transition()`，`delivery.py` 零 FSM 寫入；IFACE §6.2 步驟 8 的落點改為此（取代；PACKAGES §5 第 13 列為真） | IFACE §6.2；PACKAGES §5#13、§2.1；`test_research_ast_locks.py:424` | FSM 寫入面集中單檔，AST 專屬規則才寫得出 |
| ⚖P2-2 | 採納 D-138、D-139 | 審查者獨立性與報告參照入 `research_gate_decisions.details`，`reason` 不加前綴（取代 IFACE §0 對照第 3 列與 §2.1 的 `[reviewer_independent=…]` 前綴法） | D-138 Q-2；D-139(2) | 查詢不必解析字串，CHECK 可約束型別 |
| ⚖P2-3 | 採納 D-138、D-139 | RELEASE_READY FAIL 登錄 `gate=SCG6`，`details.ci_red=true`（取代 IFACE §0 對照第 2 列的 `SCG5` 加前綴；與框架 `transition_rules.py:311` 對齊） | D-138 Q-3；D-139(1) | 消除成因；DDL 一次到位 |
| ⚖P2-4 | 採納 D-139 | 追溯快照 sha256 入 `research_deliveries.snapshot_sha256`；`rtm_report_ref` 只存 `03_execution/traceability_matrix.json` 路徑（取代 IFACE §0 對照第 4 列的 `@sha256:` 承載）；TAG 列必填由應用層守、PR 列為 NULL | D-139(3)；D-140 #10 | 結構化欄位勝過字串承載 |
| ⚖P2-5 | 採納 D-138、D-139 | SCR 失敗證據連結入 `research_scr.evidence_url`，不附 reason 末行（取代 IFACE §0 對照第 7 列與 §7 末句；D-138 稱『七項』，IFACE §0 表實為八列，本檔以列內容而非列序對應） | D-138 Q-12；D-139(4)；D-140 #12 | 同上 |
| ⚖P2-6 | 採納 D-142 | `POST …/gates` 於研究專案尚未綁 console 專案時回 409 `fsm_state_conflict`，`details.unmet` 項名 `no_console_project`（本檔類推；IFACE §2.1 只說 `fsm_state_conflict`） | IFACE §2.1 | 契約未定項名；AT 需要一個字面 |
| ⚖P2-7 | 採納 D-138 Q-1 | 看板投影為 console-api `GET …/kanban`（API-RP-26；契約 §1.1 補列，D-140 勘誤批次）；另 API-RP-27（healing）、API-RP-28（traceability）補列 | D-138；IFACE §0 | Bridge 不可達快照屬伺服器端邏輯 |
| ⚖P2-8 | 採納 D-142 | 看板 `gates[]` 納入 `SCG6`（D-139 後 RELEASE_READY FAIL 在 SCG6；IFACE §1.2 只寫 SCG4、SCG5） | D-139；IFACE §1.2 | CI 紅的決定若不顯示，看板失真 |
| ⚖P2-9 | 採納 D-142（改判） | 規格漂移於 `:tag` 與 `:gates` 前置＝阻擋，422 `digest_mismatch`（既有 P0 reason）加 `details.drift[{path, expected_sha256, actual_sha256}]`，零寫入、零 FSM 呼叫；`:healing-sync` 只記錄加告警；檢查序＝專案存在→本文→凍結 digest 比對→FSM 前置（D-144 F-01）；不新增 reason（四方鎖 37） | D-142 ⚖P2-9；D-144 F-01；D-138 Q-7 | 對漂移後的規格打 Tag 或登錄 SCG-4 等於替未凍結的規格背書（禁令 3）；阻擋不是還原 |
| ⚖P2-10 | 採納 D-142 | 『稍後處理』的 `sessionStorage` 鍵名取 `research.decision.snoozed`（本檔類推；IFACE §5 只說『記入 sessionStorage』） | IFACE §5 | AT 需要字面常數 |
| ⚖P2-11 | 採納 D-142 | evidence_url 驗證規則名：Bridge `evidence_not_https`、`evidence_too_long`；console-api `violations` 規則 `not_https`、`too_long`（本檔類推） | D-139(4) | 兩端規則名須單一來源，AT 需要字面 |
| ⚖P2-12 | 採納 D-142 | 追溯表在無凍結 PRD 時回 409 `fsm_state_conflict`、`unmet` 含 `prd_not_frozen`（本檔類推） | IFACE §6.1 | 契約未定 |
| ⚖P2-13 | 採納 D-142 | PR 預覽未確認的規則名 `preview_ack_required`（本檔類推；IFACE §6.4 只說 `bodyPreviewAck` 必須為 true） | IFACE §6.4 | AT 需要字面 |
| ⚖P2-14 | 採納 D-142 | `RESEARCH_REASONS` 實住 `frontend/lib/domain/research.ts:749`（`frontend/lib/domain/research.ts:11` 註解明寫研究 reason 不進 `lib/api/reasons.ts`）；IFACE §9.3 ③ 與 PACKAGES §2.3 把常數與 `reasons.test.ts` 寫在 `lib/api/reasons.ts`，本檔依現查改為 `research.ts` 與其測試，`reasons.ts` 零 diff | IFACE §9.3；PACKAGES §2.3、§5#20；SD Grep 現查 | 否則開發棒會去改一個會讓雙向鎖紅的檔 |
| ⚖P2-15 | 採納 D-142（更正） | 對帳呼叫點鎖**存在**：`tests/test_research_reconcile.py:331`（`test_AT_960_21_4_p0_has_only_the_gate_0_call_site_for_reconcile`，`:339` 斷言 3 處且檔名集合為 `routers/research.py`）；P2 新增 `reconcile_at_delivery` 呼叫點 ⇒ §4 補該鎖 3→4，不另立 AST 鎖；SD 首版 H19 掃錯檔，已更正 | D-142 ⚖P2-15；D-144 F-02 | 鎖的存在與否以 Grep 為準 |
| ⚖P2-16 | 採納 D-141 | 分包為 PKG-DB-P2（波 0）→ PKG-BR-P2 ∥ PKG-FE-P2A（波 1）→ PKG-API-P2 ∥ PKG-FE-P2B（波 2）→ PKG-FE-W3（波 3）→ INT-P2；共享單點歸屬同 PACKAGES §3，另 `research_pg_support.py` 的 `LAST_VERSION` 歸 DB-P2 | D-141；PACKAGES | 鎖持有面各只給一棒（鐵律七） |
| ⚖P2-17 | 採納 D-142 | D-139 的 `evidence_url` 使 `app/research/scr.py`、`app/routers/research_scr.py` 必須改（PACKAGES §2.1 把二者列禁區）：本檔把這兩檔補進 BR-P2 允許集合，只限加欄與驗證，P1 的 SCR 行為與 AT 零改動 | D-139；PACKAGES §2.1 禁區 | 否則 D-139(4) 無人能落地 |
| ⚖P2-18 | 採納 D-142 | 內環失敗劇本：先現查 `mock_claude.py` 是否支援步驟失敗；不足才建 `inner_fail.json`（IFACE §10.2 標推論），INT 首要現查（V-D6） | IFACE §10.2；RISKS (d)-3 | 載具能力未驗，不預先假設 |
| ⚖P2-19 | 採納 D-144 | AT-962-3-E-5 單值：DB 阻塞時回 503 `db_blocked`（P0 `DbBlocked`，`outbox.py:263,:285`：記錄留 outbox、不回 200）；D-144 F-08 引的『Bridge 不可達且 DB 有快照＝200＋snapshotAt』屬看板，已由 AT-962-10-8 承擔（`snapshotAt` 至少有專案 updated_at，故無『無快照 503』分支） | D-144 F-08；`outbox.py:250-303` | F-08 的指名 AT 與其單值內容不同題，SD 依現行契約取單值並如實註明 |
| ⚖P2-20 | 採納 D-144 | F-07、F-09～F-12 的載具與常數定案：AT-962-28-3 用 `conftest.py` 的 `run_body` 加 config `claude.command` 與 `MOCK_CLAUDE_FAIL_REGEX`；補界外對照（PR 內文四千字、`detail` 兩千字、≤500ms 的 501ms 對照、`maxRetries` 邊界）；AT-962-28-5 載具＝本機模式（載具甲）加 `approveViaApi`（P0 helper）走 Gate 0；`:tag` 容器模式補 Bridge 與 console-api 兩案（AT-962-18-E-6、19-E-6）；`research.delivery` payload 定案並登記 | D-144 | 各項皆 QA 一審指名、主控定案 |
| ⚖P2-21 | 採納 D-140 | D-140 #1：契約 API-RP-17 補 `push?`；`createGithubRelease` 註『P2 不實作』（對應 AT-962-19-1、19-E-3、18-E-3、18-9） | D-140 #1；RISKS (b)-1 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-22 | 採納 D-140 | D-140 #2：RELEASE_READY 登錄依 D-139 改 `SCG6`（對應 AT-962-3-5、1-2） | D-140 #2；RISKS (b)-2 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-23 | 採納 D-140 | D-140 #3：PRD `lib/sse/` 路徑勘誤為 `lib/api/sse.ts` 與 `hooks/useRunStream.ts`（對應 AT-962-13-2） | D-140 #3；RISKS (b)-3 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-24 | 採納 D-140 | D-140 #4：稍後處理待辦取 `kanban.pendingReviews`（對應 AT-962-14-5、10-6） | D-140 #4；RISKS (b)-4 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-25 | 採納 D-140 | D-140 #5：R10 欄位：attempt 讀端導出、歸因與補丁結果引擎未提供（對應 AT-962-9-4、6-3、12-1） | D-140 #5；RISKS (b)-5 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-26 | 採納 D-140 | D-140 #6：PRD 整合點路徑 `components/domain/views/` 勘誤為 `{execute,monitor}/`（對應 AT-962-16-2、16-3） | D-140 #6；RISKS (b)-6 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-27 | 採納 D-140 | D-140 #7：追溯表來源勘誤為 R8 `covers_ac` 加任務終態、RTM 彙總作全域閘（對應 AT-962-17-3、17-4、17-5） | D-140 #7；RISKS (b)-7 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-28 | 採納 D-140 | D-140 #8：AC-16-5 拆『Bridge 偵測、標記、告警』（AT）與『框架 hook 拒絕』（V-S1）（對應 AT-962-8-1～8-3、8-E-3） | D-140 #8；RISKS (b)-8 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-29 | 採納 D-140 | D-140 #9：契約 `research.delivery` payload 補 digest 與理由欄；`research.alert.kind` 加兩值（對應 AT-962-18-4、6-5、8-3） | D-140 #9；RISKS (b)-9 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-30 | 採納 D-140 | D-140 #10：快照 sha256 依 D-139 入 `snapshot_sha256`（對應 AT-962-18-3、1-4、23-2） | D-140 #10；RISKS (b)-10 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-31 | 採納 D-140 | D-140 #11：契約 API-RP-23 補 `reviewerIndependent`；`reviewReportRef` 入 `details`（對應 AT-962-4-4、3-6） | D-140 #11；RISKS (b)-11 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-32 | 採納 D-140 | D-140 #12：證據連結依 D-139 入 `evidence_url`（對應 AT-962-15-6、15-7、1-5） | D-140 #12；RISKS (b)-12 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-33 | 採納 D-140 | D-140 #13：出口 (b)『真實』＝引擎真重試耗盡路徑，claude 為 mock 須標明（對應 AT-962-28-3、V-D6） | D-140 #13；RISKS (b)-13 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-34 | 採納 D-140 | D-140 #14：對帳『六項』改『以 `CHECK_IDS` 為準』（對應 AT-962-23-1、23-6） | D-140 #14；RISKS (b)-14 | 十四處都在 P2 凍結前的同一份上位文件；RELEASE_READY 一次 SPEC_AUDIT 收齊 |
| ⚖P2-35 | 採納 D-138 | Q-4：Tag 序列與交易邊界（W-R2P17）（對應 AT-962-18-1～18-9） | D-138 Q-4；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-36 | 採納 D-138 | Q-5：追溯表單元欄與 E2E 欄導出（對應 AT-962-17-3、17-4） | D-138 Q-5；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-37 | 採納 D-138 | Q-6：R10 導出、歸因與補丁結果 null、遮蔽兩端對拍、研究面恆遮（對應 AT-962-6-3、7-1～7-3、9-4） | D-138 Q-6；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-38 | 採納 D-138 | Q-7：SPEC_CHANGE 只偵測不還原；『被拒』屬 V-S1（對應 AT-962-8-1～8-E-3） | D-138 Q-7；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-39 | 採納 D-138 | Q-8：不做 GitHub Release（對應 AT-962-18-E-3、19-E-3） | D-138 Q-8；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-40 | 採納 D-138 | Q-9：≤500ms 定義與驗證載具（對應 AT-962-11-3、13-6） | D-138 Q-9；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-41 | 採納 D-138 | Q-10：PR 標題與內文模板、失敗只發事件（對應 AT-962-20-2、20-7） | D-138 Q-10；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-42 | 採納 D-138 | Q-11：ResearchBackLink 以 `?researchId=` 深連結（對應 AT-962-16-1～16-E-3） | D-138 Q-11；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-43 | 採納 D-138 | Q-13：`healing_history.log` 觸發點為 console-api post-commit 通知（對應 AT-962-9-6、23-5） | D-138 Q-13；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-44 | 採納 D-138 | Q-14：新增恰兩個 reason（對應 AT-962-24-1） | D-138 Q-14；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-45 | 採納 D-138 | Q-15：對帳只加 `delivery`（對應 AT-962-23-1） | D-138 Q-15；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |
| ⚖P2-46 | 採納 D-138 | Q-16：SCR 序列的 gate 不寫 SCG4 列；OPEN SCR 期間 `:gates` 回 `scr_open`（對應 AT-962-3-9） | D-138 Q-16；RISKS (a) | ARCH 建議 A，零 DDL 最小侵入 |

---

## 📋 SCG-4 通過標準

1. §3 全部 AT 綠（Bridge pytest 在 `BRIDGE_TEST_DSN` 與 `SDD_ROOT` 皆在場下 0 skipped、backend `gradlew clean build` 為 BUILD SUCCESSFUL 且 JaCoCo 不低於 80%、frontend vitest 覆蓋率不低於 70% 且 `tsc`、`lint`、`build` rc 0；Docker E2E 對全棧綠；各 AT 的輸出逐字貼入證據）。
2. §4 各列同步只改預期值、零刪斷言（例外列依 §4 開頭明示）；§4.4 凍結文件勘誤各補一列並於 RELEASE_READY 一併 refreeze。
3. §5.7 各包集合外零差異、禁區零差異（AT-962-29-1、29-2）；不新增 `os.replace`、`rename`、`move` 站點（AT-962-29-3）；不新增 hook 與守衛。
4. §1.2 的 P2 AC-R2P 皆有 AT 或 V 的正向證據；§1.3 的劃界項不得被算作已覆蓋。
5. V 系列（§6.2）：V-S1、V-D5～V-D8、V-C2 皆有文字證據或如實標「未驗」；V-H5、V-H6 為掌舵者真機（構造情境不能充當）。
6. 文件連動全部落地（AT-962-30-1～30-3）；RTM 子表每列回填；`AgentConsole/CLAUDE.md` 不超過 200 行、`README.md` 不超過 80 行。
7. PRD §8.1 P2 出口 (a) 至 (i) 逐項有證據（§6.1 對照表）。

## 勘誤（凍結後的訂正；內文已就地訂正、被訂正的原文逐字保留於下表；走 `spec-refreeze`）

> 本表於 Stage-2 凍結時為空；凍結後的訂正於 RELEASE_READY 批次一併寫入並 refreeze（日期欄只寫月-日、不寫四位數年份，原因同 TCS-P0、TCS-P1 勘誤表：避免行內數字觸發基線站點掃描）。

| 編號 | 日期 | 位置 | 原文 | 訂正 | 原因與證據 |
|------|------|------|------|------|------------|
| E-1 | 11-08 | §5.7 允許集合（各包列） | 原文：DB-P2 列無 V22；BR-P2 列無 `orchestrator.py`、`research_git_support.py`；API-P2 列無七個新埠等；FE-P2A／P2B／W3／INT-P2 列缺下列追認檔 | 已就地訂正：①新增 PKG-DB-P2b 列（V22 檔、七處 Flyway 版本清單 IT 站點、`research_pg_support.py`）；②BR-P2 加 `app/research/orchestrator.py`、`tests/research_git_support.py`；③API-P2 加七個新埠（`application/port/in/Research{Kanban,Gate,Healing,Delivery}UseCase`、`port/out/Research{Kanban,Healing,Delivery}ReadPort`）、`ResearchBridge.java`、`ResearchScrUseCase.java`、`ResearchRouteViews.java`、`ResearchExceptionHandler.java`、`ResearchScrService.java`、`minibridge/MiniDeliveryBehaviors.java`、`support/ResearchP2Fixtures.java`、`ResearchSchemaMigrationIT`（AT-962-22-5）；④FE-P2A 加 `lib/api/si.endpoints.test.ts`、`tests/e2e/research-build-front.mock.spec.ts`；⑤FE-P2B 加 `lib/help/research-workspace.ts`（僅 `sourceFiles`）、`lib/domain/research.ts`＋`research.test.ts`（僅 D-157 常數）、`lib/api/types.ts`／`tests/fixtures/research/p2.ts`／`TraceabilityTable`（D-158）；⑥FE-W3 加 `lib/api/types.test.ts`、`HealingMonitor.tsx`／`.test.tsx`／`p2.ts`／`a11y.mock.spec.ts`、`DecisionModal.tsx`／`TagConfirmDialog.tsx`／`.test.tsx`；⑦INT-P2 加證據檔 `docs/06_quality/INT-ResearchToPRD-P2-20261108.md` | D-149#1／#2／#3／#9、D-155、D-156、D-157、D-158、D-159 E#3、D-161、D-162、D-163 |
| E-2 | 11-08 | §4 硬釘補列（新增 §4.6 第 47～53 列） | 原文：§4 無下列列 | 訂正：新增 §4.6：`si.endpoints.test.ts:44-46` 118→125（D-148 FE-2）；P1 三處斷言 AT_961_18_5／18_6／20_E_4 改動（D-155，同時登記到 TCS-P1 勘誤表）；§4.3#37 座標擴充 `:188`、`:228-233`、`:246-252`、`:264-326`、`:305-328`、`:678`（D-150#8）；§4.1#12 名單只加 `delivery_step_failed`（D-149#10）；§4.1#17 `Outcome` 三參數次要建構子（D-149#2、#6）；§4.1#18 `ErrorResponseDocumentation` 零改動、落點 `ResearchErrorDocs`（D-149#11）；AC-962-1「21」→「22」 | D-148、D-149、D-150、D-155、D-162 |
| E-3 | 11-08 | AC-962-1 全部（AT-962-1-1、1-7、1-8 與 §4.1#1／#2／#19） | 原文：「Flyway 歷史 1～21 全成功」「六處 Flyway 版本清單加 21」「Bridge 夾具套到 V21」「`LAST_VERSION = 20`→21」 | 訂正：21 一律改 22——AT-962-1-1 為歷史 1 至 22（V1～V21 checksum 不變、V22 不新增表）、六處版本清單 IT 與 `ResearchSchemaMigrationIT` 皆至 22、`research_pg_support.LAST_VERSION` 22；AT-962-1-8 判準改「`LAST_VERSION`≥21 且遷移檔數等於 `LAST_VERSION`」；V22 DDL 全文＝Architecture K.7 | D-162(a)；PKG-DB-P2b（commit ee5bd46d） |
| E-4 | 11-08 | AT-962-1-4（備註） | 原文：「`snapshot_sha256` 為 63 位、64 位含大寫、64 位含 `g`⇒23514」 | 訂正：維持既有 63 碼負控；註記「CHAR(64) 補空白使 63 碼存入後恆為 64 字元，故正規式 `{63,64}` 與 `{64}` 無輸入可區分＝等價突變」，不補測試 | SCG-4 一審 F-05（二審 SQL 驗證撤銷）、報告 D5 |
| E-5 | 11-08 | 新列 AT-962-1b-1～1b-4（§1.2、§1.5、§3.2、檔頭計數） | 原文：（無此四條）→ 訂正：新增 AT-962-1b-1（V22 升級既有列不變）、1b-2（DELIVERED 組合可寫且列舉恰十四值）、1b-3（小寫、空字串、尾空白、其他值 23514）、1b-4（`pg_constraint` 恰一條含 DELIVERED 且 gate 守衛不退步）；測試 `ResearchSchemaMigrationIT::AT_962_1b_*`；同步 §1.2、§1.5、§3.2、檔頭計數（AT 309→313、正控 202→206）與 RTM-P2 增四列（343→347，已由 RTM 回填 commit d8f68875 落地） |  | D-162(a)；PKG-DB-P2b |
| E-6 | 11-08 | AT-962-6-7（標題） | 原文：「ResearchDb 唯一新增的方法是唯讀的 list_healing_attempts；沒有新寫入面。」 | 訂正：標題改「新增讀方法皆唯讀」（允許三個唯讀 DB 讀方法：決定列、交付列、任務終態） | D-148 BR-1 |
| E-7 | 11-08 | AT-962-25-2、21-1、16-5、15-5（歸屬） | 原文：25-2／21-1／16-5 歸 FE-P2A；15-5 的 ReleaseActions 半由 A 承接 | 訂正：25-2、21-1、16-5 歸 FE-P2B；15-5 於 A 只測三處，`ReleaseActions` 的 SCR_OPEN 停用由 B 的 AT-962-21-3 承接 | D-148 FE-1、FE-3 |
| E-8 | 11-08 | AT-962-16-E-3、16-E-1、P0 `AT_960_19_5` | 原文：16-E-3「零後端、零儲存；頁面殼零差異」；16-E-1「ExecuteView 無參數不顯示」；`AT_960_19_5` 含 PLACEHOLDERS 與占位進度案 | 訂正：16-E-3 的 When 改三項（只渲染 BackLink 本身 spy 三者為零；剝註解靜態掃描 `ResearchBackLink.tsx` 無 `fetch(`／`localStorage`／`sessionStorage`／`document.cookie`；兩個 `page.tsx` 零 diff）；16-E-1 拆 `ExecuteView.test.tsx` 與 `MonitorView.test.tsx` 兩檔同掛（AT 數不變）；回連只掛兩個 View 的主分支；`AT_960_19_5` 的 PLACEHOLDERS 與占位進度案刪除、語意轉移 AT-962-25-2；`AT_960_19_6` 鎖只增不減（加 `tag-create`） | D-150#3／#4／#5、D-157 |
| E-9 | 11-08 | AT-962-21-6、21-E-3、AT-962-21-5 | 原文：21-6「開啟本地專案：顯示專案根路徑與複製鈕；容器模式標示容器內路徑；不假裝可開啟」；21-E-3「外部連結安全：所有外部連結帶 noopener noreferrer」；21-5「…無 PR 時 ADMIN 見建立 PR 並預覽標題、內文與推送目標」 | 訂正：21-6 以 OPERATOR 驗複製鈕並加負控「VIEWER 下 `project-root-copy` 不存在」（VIEWER 只顯示可選取的路徑文字；P0 `AT_960_19_6` 斷言一字不動）；21-E-3 實作於 `PrConfirmDialog.test`；21-5 預覽以 `frTotal`、`rpNo`、`title` 截 60 字、`acTotal`、`branch` 組出與 Bridge 模板逐字同形的標題預覽與內文四段大綱，並明示「實際內容由後端確定性產生」；semver 正規式、Tag／PR 上限與「僅 ADMIN」文案收進 `lib/domain/research.ts` | D-150#1、D-151、D-157 |
| E-10 | 11-08 | AT-962-17-x、21-5（totals） | 原文：17-5「totals：未覆蓋＝unitStatus 不為 PASS 的列數；e2e 欄不計入；零測試不是通過」（totals 無 `frTotal`）；17-2「gherkinSummary 每段不超過 120 字」 | 訂正：`totals` 加 `frTotal`（凍結 PRD 的 FR 條數，與 AC 計數同一解析路徑，也是 `:tag`／`:pr` 標題 `<FR 數>` 的來源）；追溯列 `gherkinSummary` 為 `{given,when,then}`（每段至多 120 字）、`source` 為字串陣列 | D-151、D-158 |
| E-11 | 11-08 | AT-962-9-5、8-5（Given） | 原文：9-5「日誌落後筆數：logSyncedThrough 與差額推得」；8-5「API 於漂移列補 specChangeForbidden」 | 訂正：Given 補「先經 Notifier 觸發一次 sync」——`GET …/healing` 零 Bridge 請求，`logLag`／`logSyncedThrough` 取自記憶體快取，快取缺時為 0 與 null | D-149#5 |
| E-12 | 11-08 | AT-962-10-E-1（禁用片段） | 原文：10-E-1「路由清單比對：無執行控制動詞路徑；P2 新增路徑集合恰七條；負控夾具被判違規」（未列具體禁用片段） | 訂正：禁用片段縮為 `execute｜pause｜resume｜stop`，並斷言七條新路徑不含 `cancel｜restore｜review` | D-159 E#5 |
| E-13 | 11-08 | AT-962-27-1（判準） | 原文：27-1「schema.d.ts 由 backend OpenAPI 重產：七條新路徑與新 DTO 存在，重產後 diff 為空」 | 訂正：判準改「連續重產兩次雜湊相等＋七路徑與 DTO 命中＋`git diff --stat` 只增不刪」；重產環境＝`gradlew bootRun`＋dev PG（工作樹原始碼），交卷附 `/v3/api-docs` sha | D-152#4、#5 |
| E-14 | 11-08 | AT-962-28-3、28-4、28-5（載具） | 原文：28-3「pytest｜`test_research_int_p2.py`｜Integration｜…引擎重試耗盡自然觸發 ESCALATED（claude 為 mock 可執行檔，須標明）」（本機模式載具，需重建共用 `aisdlc-backend` 容器指向主機 Bridge）；28-4、28-5 同載具 | 訂正：載具改全棧為載具、pytest 作 HTTP 客戶端（`E2E_STACK` 與 ADMIN 帳密環境變數門控；缺全棧 skip 標 TOOL-ABSENCE）；28-3／28-4／28-5 一律在**第二套拋棄式棧**上補跑——自有 compose 專案 `r2p2int`＋主機 Bridge local mode（埠 18081）（另一 compose project、不同埠、不 `--build`、不覆寫共用映像、卷隔離、用完 `down -v` 只清自己的）；28-5 的 Gate 0 以 API 代驗、審查卡為構造（須於證據標明，不得單獨充當真實審查）。**本表只登載具字面，不登結果**（結果見 INT 證據檔第二段與 RTM） | D-153#1、#4、D-166 |
| E-15 | 11-08 | AT-962-28-8（Then）、28-7（劃界） | 原文：28-8「Docker 容器模式負控：API 直呼 :tag 回 422 route_unsupported_in_deployment，DB 零變化」（Then：422、`details.missing` 含 `repo_writable`）；28-7「Docker mock-only：看板、自癒視圖、終端窗格、追溯表可驗」 | 訂正：28-8 Then 改「容器模式 `delivery/tag` 回 409（`no_console_project`／Bridge `route_not_succeeded`）且零變化」，422 `route_unsupported_in_deployment` 負控改掛 Bridge pytest AT-962-18-E-6；28-7 劃界：Docker mock-only 只能驗 API 唯讀面與導回 | D-164 D-1／D-5；INT 證據檔 D-1、D-5 |
| E-16 | 11-08 | AT-962-18-5、AC-962-23 mapping | 原文：18-5「FSM 與游標：transition --to RELEASE 序列與游標落點」（無 V22 前提）；對帳 mapping 於 `SPEC_FROZEN` 無 `deliver` | 訂正：18-5 補「`LAST_VERSION`≥22 前提」並斷言游標 `deliver／DELIVERED／COMPLETED`；AC-962-23 的 FLOW_FSM_MAPPING 於外環現態 `SPEC_FROZEN` 增 `deliver／DELIVERED` 新列；`:tag` 續跑判準＝快照檔先於 `tag -a` 寫入、重送時 tag 存在且快照 `tag_name`／`commit_sha` 吻合 HEAD 才續跑，否則 409 `tag_exists`；遠端同 sha 以 `ls-remote` 剝離行 `^{}` 比對 HEAD commit；`lastRunAt` 取 `tasks.completed_at`、覆蓋對映讀 `pass_criteria_spec` | D-162(a)(b)(c)(e) |
| E-17 | 11-08 | AT-962-13-3、11-E-2、7-3（字面） | 原文：13-3「純文字哨兵：…ANSI 序列不殘留」；11-E-2 Then「沒有『0』與『完成』字樣」（看板事實列曾寫「已完成」）；7-3「Java 遮蔽器與 Python 同夾具逐筆相同」（夾具無 AKIA 案） | 訂正：13-3 ANSI 由 `TerminalPane` 餵入前剝除；11-E-2 事實列字面改「成功任務」使 Then 成立；7-3 同夾具 `healing_redaction_cases.json` 加一筆 AKIA 案，兩端各加 `AKIA[0-9A-Z]{16}` 遮蔽樣式（Bridge `gitops.redact` 與 Java `HealingExcerptMasker`） | D-155⑤、D-162(g) |
| E-18 | 11-08 | AT-962-13-E-3（路徑）、18-4／24-E-3／5-6／18-E-4（命名） | 原文：13-E-3 所列 `LogPanel.tsx` 在 execute 目錄 | 訂正：路徑改 `components/domain/LogPanel.tsx`；18-4 與 24-E-3 以別名註解承接（18-4 併入 `18_3_4` 測試、24-E-3 由 `AT_961_15_4` 承擔）；5-6 與 13-E-3 已獨立命名、18-E-4 以參數化 id 命名 | SCG-4 一審 F-10；二審 H.3 |
| E-19 | 11-08 | AT-962-29-2（字面） | 原文：「P2 窗口內 `AutoClaude/` 零差異」 | 訂正：字面排除主控 chore(perf) 常態 commit（`AutoClaude/.perf_baseline.toml`、`ONBOARDING.md` 的重鎖更新）；其餘禁區仍零差異 | SCG-4 一審 F-18 |
| E-20 | 11-08 | AT-962-4-x 理由長度與規則名（註記） | 原文：未載理由長度計法與兩層規則名 | 訂正：註記——500 字上限前端與 Bridge 以 code point 計、console-api 以 UTF-16 計（已知差異）；規則名分層（console-api `invalid_gate`／`invalid_result`、Bridge `gate_invalid`／`result_invalid`），契約已補列；不改行為 | SCG-4 一審 F-14、F-15 |
| E-21 | 11-08 | V-D8（§6.2）與 AC-962-6（註記） | 原文：V-D8 預期自癒補丁觸及凍結規格「被拒」 | 訂正：Bridge 的 runner 剝除環境中的 `SDD_*` 三件組 ⇒ run 內框架 hook 不生效，P2 **不得聲稱**「被拒」，只做 Bridge 偵測＋標記＋告警；Architecture §10.4 與 RTM 備註同步 | D-164（V-D8） |
| E-22 | 11-08 | 後續 FIX 候選（P4，不改條文） | 原文：（無） | 登記：N-1＝`ResearchHealingApiIT` AT-9-5 以忙等（`Thread.onSpinWait`）等快取、高負載下有五秒上界逾時風險，宜改有界輪詢睡眠；N-2＝`gherkin_summary` 的圍欄剔除只認行首圍欄行、行內中段圍欄不處理（現行夾具型態不觸發）；F-16＝P0 `StudioPanel` 兩個測試檔在負載下逾時（沿既有負載敏感名單）；F-14＝理由長度統一以 code point 計 | SCG-4 二審 N-1、N-2；一審 F-14、F-16；D-167 |
| E-23 | 11-08 | §4 各包 commit 登記 | 原文：（無） | 登記：IDE 三筆清零 e4b123af；DB-P2 7652dc27；FE-P2A 28d36d6f；FE-P2B 10daf683；API-P2 42b23c28；FE-W3 dd98bc26 與 65f341d4；Mermaid fdac86f1；BR-P2 ed6fdfa0 與 ea978443；API-FIX c738d31a；DB-P2b ee5bd46d；INT 第一段 5f6f01df 與 57dc872a；SCG-4 FIX-P2 a3e2ec5c；SCG-4 報告 f6e5e21c；RTM 回填 d8f68875；INT 第二段（第二套拋棄式棧，D-166）a9e87542；FIX-INT（D-6 修復，D-168）adf6c9af；RELEASE_READY 勘誤批次與 refreeze＝本列所在 commit 之後各一（RTM 第二次回填登記 hash） | D-154、D-165、D-167、D-166、D-168 |
| E-24 | 11-08 | TCS-P1 連動 | 原文：（無） | 訂正：TCS-P1 勘誤表同批補列（AT_961_18_5／18_6／20_E_4 斷言改動，D-155；P0 `AT_960_19_6` 只增不減）；P1 鍵已 RELEASE，refreeze 由主控做 | D-155、D-157 |
| E-25 | 11-08 | AT-962-15-2（Then） | 原文：「…affectedSections 選項取自凍結 PRD 章節與 AC；證據連結為選填欄」 | 訂正：補「選項**值**＝章節編號（`5`、`5.2`）與 AC 編號（`AC-` 後須數字開頭，範本佔位 `AC-NNN-Y` 不算），不是標題全文；顯示文字可帶標題；與 Bridge `parse_frozen_prd`（`_AC_RE`）同一規則，兩端以共用夾具 `engine-bridge/tests/fixtures/research/scr_section_options_cases.json` 對拍」；`lib/help/research-workspace.ts` 的「受影響章節」說明由修復棒改程式側（docs 無鏡像） | D-168（INT 第二段缺陷 D-6） |
| E-26 | 11-08 | V-D5 與 AC-R2P-15-3 劃界（§1.2、§1.3、§6.2 對應處，只登記量測字樣） | 原文：「V-D5：『FSM 檔改變→看板更新』端到端上界量測；INT 量測中位數與最大值並記錄；不充當 AT」 | 登記量測結果（INT 第二段，第二套拋棄式棧）：內環 FSM 由框架 CLI 直接推進時 console-api 無 SSE 幀 ⇒ 已開著的看板在十四次動作後三十秒內零更新；REST 讀端於一百一十一至三百二十五毫秒內即反映新狀態。判讀：這是 W-R2P10、Q-9 已載明的設計邊界（Bridge 無推播；≤500ms 只對 SSE 幀到達之後成立），**不是缺陷**，不改條文、不加 AT；Architecture §10.4 已補一句「無 SSE 幀，看板靠導航或 REST 回補」 | D-7、D-138 Q-9；INT 證據檔第二段 |
| E-27 | 11-08 | 後續 FIX 候選（P4，不改條文；續 E-22） | 原文：（無） | 登記：D-8＝同一次 ESCALATED 升級在步驟 4 彈兩次（先是可決定的審核項，決定後再彈 info-only 的「引擎升級事件」、沒有決定鈕；AT-962-28-4 真棧截圖）；修復棒 PKG-FIX-INT 只做 D-6、未讀彈窗映射，候選＝`HealingMonitor`／看板的事件→彈窗映射以 taskId 去重並補單元測試 | INT 第二段 D-8；D-168 |
| E-28 | 11-09 | AT-962-21-2（`DeliverPanel.test.tsx`；§1 AC-962-21 列與 AT 清單條文） | 原文：「DeliverPanel 整體呈現：追溯表、發布動作列、交付紀錄、對帳狀態」（未提及唯讀角色的停用集合） | 加註：VIEWER 下「每個 button 都停用且 title 為權限不足」的集合不含表頭排序鈕（帶 `data-sort-key` 的 button；排序是唯讀操作）；該測試檔 expect／it 數不變。另 RP-1 現查：本檔 :403、:863 為 attempt 導出（依 step_number 升冪）、:1464 為閘門決定紀錄（依 decidedAt 由新到舊），皆非研究專案清單畫面序，條文不改 | 鍵 `agentconsole-console-ux-sort-help` 勘誤 E-6、§6 RP-1；FE-SORT 交卷候選 1，主控裁決成立 |
