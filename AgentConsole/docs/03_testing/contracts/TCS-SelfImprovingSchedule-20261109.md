# Test Contract Specification — SelfImproving 排程控制載體（Console 半：橫幅排程欄位組、啟停與週期對話框、立即啟動對話框、backend 兩個 POST 與 Flyway CHECK 改版、Bridge 兩個 POST、稽核 JSON 兩種新 kind 的跨語言向量與對帳）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭；根層半另有 `TCS-SelfImproving-P4-20261109.md`）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole；上位文件含 P2b、P1b 的 TCS 與後繼契約）的單一 Feature（SelfImproving P4 的 Console 半）；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingSchedule-20261109.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因上位文件含根層 PRD）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-910 |
| **Feature 名稱** | SelfImproving 排程控制載體（Console 半）——橫幅「自動演化排程」欄位組與 `schedule` 量不到規則、ADMIN 的啟停開關／週期輸入／「立即啟動一次演化」三個控件與兩個確認對話框、`overdue` 警示與略過原因、backend `POST /api/v1/si/schedule/set` 與 `POST /api/v1/si/runs/request`（含序 5′ 界取得、不走重送閘）、Bridge `POST /si/schedule:set` 與 `POST /si/runs:request`、稽核 JSON `sched-set`／`run-request` 兩種 kind 的跨語言向量與黃金檔 G6～G9、對帳 `kind` 新值與 `orphans`、Flyway CHECK 改版、每頁說明 |
| **User Story** | US-930 |
| **建立日期** | 2026-11-09 |
| **輸入快照** | HEAD 於撰寫時為 `5199e5600a01b5627c2ae8b1d0aa80e6debdf6a4`（`git rev-parse HEAD` 現查；Console PRD §0.11 已於其後的 commit 落檔，凍結前由主控重查）；上位檔 digest 見〈增量追溯表〉，**由主控於凍結前以 `Get-FileHash -Algorithm SHA256` 現算**（SD 棒不代算，避免上位檔仍在編修時漂移） |
| **QA 負責人** | 本鍵 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SD 棒，實作者＝鍵 `agentconsole-si-schedule` 的三個開發 agent〔PKG-BE、PKG-BR、PKG-FE〕，三方不同） |
| **FSM 功能鍵** | `agentconsole-si-schedule`（**依賴根層鍵 `monorepo-si-p4-schedule` RELEASE**；一律從 monorepo 根啟動：`python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug si-schedule`） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統的單一 Feature（上位文件見〈增量追溯表〉）。**凍結檔不得再改**：發現需修訂處一律寫在 §7 的清單，走掌舵者 T1／SPEC_REGRESSION_CHECK。**與根層 TCS 的接縫**（`docs/03_testing/contracts/TCS-SelfImproving-P4-20261109.md`，下稱「根層 TCS」）：事件欄位（根層 R139）、稽核 body 規則與位元組權威（根層 R141）、`status.schedule` 形狀（根層 R158）、Console 載體入帳（根層 R146）、黃金檔收下 AT（根層 AT-437-1-3）**一律引根層 TCS 的 R 條文編號、不在本檔複寫判準**；本檔只釘 Console 側（HTTP 形狀、閘門序、前端呈現、Bridge 落檔、Flyway）。契約文件＝`AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P2c.md`（v0.1；實作輪後依實作如實校對升 v1.0），Architecture §5.6、§10.3、§12.1 L-SI-1／L-SI-2。

### FRD-lite

**現況與變更（Before／After；brownfield；現況於撰寫時現查）**

- Before：(1) `/self-improving` 的 `SiStatusBanner` 把 `status.items[0]` 的未知鍵一律列在「其他欄位」，`SI_STATUS_KNOWN_KEYS` 不含 `schedule`；沒有任何排程或啟動控件；(2) backend 的 `POST /api/v1/si/**` 只有四個（`decide`、`observations`、`observations/{id}/close`、`observations/validate`），`SiWriteKind` 為三值（`decide`、`obs-add`、`obs-close`）；(3) Bridge 的寫入路由為三個稽核落檔 POST 與一個唯讀 `validate`；(4) `console.si_console_writes.kind` 的 CHECK 為三值（`V13__si_console_writes.sql` 的欄位內聯匿名 CHECK）；(5) 對帳 `items[].kind` 值域三值；`status.consolePending` 的種類三值；(6) `lib/domain/si.ts` 的 `SiWriteKind` 與 `SI_WRITE_KIND_LABELS`、`ingestCommands` 只認三種。
- After：(1) 橫幅加「自動演化排程」欄位組（具名欄位，`schedule` 進 `SI_STATUS_KNOWN_KEYS`；量不到規則 W-S1），ADMIN 另有排程面板與三控件（W-S2～W-S6）；(2) backend 加兩個 POST（API-SI-12、API-SI-13；閘門序含序 5′、不走重送閘；W-S7）；(3) Bridge 加兩個落檔 POST（W-S8）；(4) Flyway 新版本把 CHECK 擴為五值（W-S7，版本號**現查最大版本＋1**）；(5) 稽核 JSON 兩種新 kind 的跨語言向量 V5～V8 與黃金檔 G6～G9、對帳與 `orphans` 的新 kind 判準（W-S9）；(6) 每頁說明與既有鎖的預期值同步（W-S10）。
- **非目標**：不改根層 `tools/`（含巡邏器與兩個入帳動詞）、不改 `si_console_writes` 的欄位與「列不可改」trigger、不新增資料表、不改決定重送閘（`si_decision_duplicate` 只管 `decide`）、不改導覽登記表與 `ToolsRegion.tsx`、不做任何刪除 UI、不在 Console 查詢主機 OS 任務（L-SI-1）、不新增 reason（`SI_REASONS` 不新增鍵）。

**AC 編號規則**

1. **編譯文法**：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。
2. **對映**：AC 取 Console PRD §0.11 的 `AC-964-1`～`AC-964-10`（其與根層 PRD 的對應：`AC-SI-37-1` ↔ `AC-964-7`、`AC-964-8`、`AC-964-9`；`AC-SI-37-3`、`AC-SI-37-4` ↔ `AC-964-1`～`AC-964-6`；`AC-SI-37-5` ↔ `AC-964-9`）；本檔不自增 AC。
3. **AT 命名**：`AT-<AC 數字 id>-<序>`；負控與邊界 `AT-<AC 數字 id>-E-<序>`；測試名含其底線形（`AT-964-7-1`→`AT_964_7_1`；Java 方法名以底線形開頭加駝峰敘述）。每個 AC 內數字序與 E 序各不超過 9，使 `-t`、`--tests`、`-k`、`-g` 的子字串比對不會誤收其他 AT。
4. **計數**：AC 10 個、AT 69 個（正控 44、負控 25；分佈見 §1 末與 §6）。

**本增量交付物**（D1～D9；路徑相對 monorepo 根；三個開發包的持有面見〈提交順序與責任〉）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | backend：兩個 POST、請求 DTO、收據、`SiWriteKind` 兩新值、稽核簽章的兩新 kind 與 body 序列化、`BridgeHttpAdapter` 兩個新呼叫、序 5′ 的界取得（`SiMirrorUseCase`）、`SiKeyNames` 深層對映、`ErrorResponseDocumentation` 兩端點說明 | `AgentConsole/backend/src/main/java/com/aisdlc/console/` 下 `adapter/in/web/SiController.java` 與 `dto/`、`application/service/`（`SiConsoleWriteService`、`SiAuditSigner`、`SiWriteGates`）、`application/port/**`、`adapter/out/bridge/BridgeHttpAdapter.java`、`domain/model/si/SiWriteKind.java`、`adapter/in/web/ErrorResponseDocumentation.java` 與 `SiKeyNames`（實作輪現查檔名） | PKG-BE | AC-964-7、964-9 |
| D2 | backend：Flyway 新版本（版本號＝`db/migration/` 現查最大號＋1；CHECK 實名以 `pg_constraint` 現查） | `AgentConsole/backend/src/main/resources/db/migration/V<現查＋1>__*.sql` | PKG-BE | AC-964-7 |
| D3 | backend 對帳讀面：`ingested` 判準與 `orphans` 的新 kind、`items[].kind` 值域 | `application/service/SiReconcileService.java` 等（現查） | PKG-BE | AC-964-9 |
| D4 | 黃金檔與向量：backend 的 G6～G9 與 V5～V8（Java 端） | `AgentConsole/backend/src/test/resources/si/audit/` 與 `SiAuditSignerTest` | PKG-BE（產出者） | AC-964-9 |
| D5 | Bridge：兩個落檔路由與測試；黃金檔副本與 Python 端向量 | `AgentConsole/engine-bridge/app/routers/si.py`（改）、`tests/test_si_write_routes.py`、`test_si_audit_filename_safety.py`、`test_si_console_ingest.py`、`test_si_readonly_lock.py`、`tests/fixtures/si_audit/`（G6～G9 副本，逐位元組同 backend） | PKG-BR（消費 PKG-BE 的黃金檔） | AC-964-8、964-9 |
| D6 | frontend 純函式、型別、端點：`SI_STATUS_KNOWN_KEYS`、表 M-S／M-R、`scheduleFields`、`periodHint`、`validateScheduleForm`／`buildScheduleRequest`／`validateRunRequestForm`／`buildRunRequest`、`SiWriteKind` 與標籤與 `ingestCommands`、`postSiScheduleSet`／`postSiRunRequest`、`schema.d.ts` 重產 | `AgentConsole/frontend/lib/domain/si.ts`、`lib/api/{endpoints,queries,types}.ts`、`lib/api/schema.d.ts` | PKG-FE | AC-964-1～6、964-10 |
| D7 | frontend 元件：排程面板與兩個對話框、橫幅欄位組、對帳面板標籤、說明檔 | `AgentConsole/frontend/components/domain/si/{SiSchedulePanel,SiScheduleDialog,SiRunRequestDialog}.tsx`（新）、`SiStatusBanner.tsx`、`SiWritesPanel.tsx`、`SiView.tsx`、`siParts.tsx`（改；兩個對話框合一為單一元件亦可，實作輪依 LOC 與可讀性二擇一並回寫 Architecture §5.6） | PKG-FE | AC-964-1～6 |
| D8 | 既有釘選測試同步與新測試（只改預期值；逐項見 §4） | §4〈需同步的既有測試〉 | 三包各自持有面 | AC-964-10；NFR-SC-5 |
| D9 | 出口實查（V 系列，非 AT） | §6.2 的 V1～V8 | QA、主控、掌舵者 | 根層 PRD §8.1 P4 出口 (b) |

**提交順序與責任**

- 依賴序：**根層 SCHED 棒 commit（`consoleaudit` 兩新 kind 可驗簽；D-CS-13）→ PKG-BE（黃金檔與向量先產出，主控以根層 CLI 驗簽後定稿）→ PKG-BR（消費黃金檔）；根層鍵 RELEASE 只為本鍵 RELEASE 的前置；PKG-FE 可與 PKG-BE 並行開工純函式與元件，但 `schema.d.ts` 須待 PKG-BE 完成後以拋棄式 IT 倒 `/v3/api-docs` 餵 `scripts/gen-api.mjs` 重產入庫**（沿 P2b 勘誤 9 作法）。每支程式完成即編譯並跑該區 AT，不累積（`AgentConsole/CLAUDE.md` 鐵律 11）。
- **三包持有面互不重疊、可並行**（鐵律七）：PKG-BE＝`AgentConsole/backend/**`（含 Flyway 新檔與黃金檔產出）；PKG-BR＝`AgentConsole/engine-bridge/**`；PKG-FE＝`AgentConsole/frontend/**`。唯一共用物是**黃金檔 G6～G9 與向量 V5～V8**：由 PKG-BE 產出（Java 序列化器、`Clock.fixed`、金鑰 K0、帳號 admin）並經根層 `consoleaudit.py` 驗簽收下後定稿，**主控**把同一份位元組複製到 PKG-BR 的 `tests/fixtures/si_audit/`（逐位元組相同；PKG-BR 不得自行重造），故 PKG-BR 的 AT-964-9-3、AT-964-9-E-1 須待此交接後才能全綠；三包之間不得互相修改對方的目錄。
- 開發 agent **不 commit／push**、不動根層 `tools/`、`.github/`、`.claude/`、凍結檔與既有 TCS（鐵律 7；本鍵的 Flyway 新檔屬 PKG-BE 的允許集合，這與前一個增量「零 Flyway」不同）。`Architecture.md` §5.6／§10.3 去「規劃」註、契約升 v1.0、RTM 本地子表（預定 §2.14）、SCG-4 報告、`lib/help/self-improving.ts` 的頁面說明（與 UI 實作同 commit，出處鎖到 `sourceFiles`）由主控代做。
- 真帳本、真事件帳本、真 `~/.autosdd/` 一律唯讀：AT 只用 Testcontainers PG、迷你 Bridge、jsdom、fetch 替身與 Playwright 的路由替身；Docker 全棧 V 系列由主控跑、不由 AT 充當。

**〈增量行為規則〉**（W-S1～W-S10；各 AT 以 W-S 編號引用。實查依據：契約 `API_Contract_SelfImproving_P2c.md` §0～§7、Architecture §5.6／§10.3／§12.1 L-SI-1／L-SI-2、Console PRD §0.11；現行測試 `SiConsoleWriteApiIT`、`SiConsoleWritesReadApiIT`、`SiConsoleWritesMigrationIT`、`SiAuditSignerTest`、`SiWriteGatesTest`、`SiKeyNamesTest`、`SiMirrorApiIT`、`SiReadOnlyArchTest`、`BridgeHttpAdapterSiWriteTest`、`OpenApiIT`、`AbstractSiWriteIT`；Bridge `tests/test_si_{write_routes,audit_filename_safety,console_ingest,readonly_lock,routes}.py`；frontend `SiView.test.tsx`、`SiDecideDialog.test.tsx`、`si.static.test.ts`、`lib/domain/si.test.ts`、`lib/api/si.endpoints.test.ts`、`tests/helpers/si.tsx`）

- **W-S1 橫幅排程欄位組與量不到規則**（`lib/domain/si.ts` 的純函式 `scheduleFields(schedule)`，橫幅與面板共用同一個函式、不各自解讀）：(a) 取 `status.items[0].schedule`（camelCase；不新增 GET），具名欄位＝啟用、週期（分鐘）並列 `periodHint` 換算、最近一次設定（`lastSet` 的 `at`、`by`、`carrier`）、本格起訖（`cellStart`、`cellEnd`）、本格是否已執行（`ranThisCell`）、本格最近一次略過（`lastSkip` 的 `at`、`reason`、`detail`）、是否逾期（`overdue`）、OS 任務是否武裝（`armed`）；(b) `armed` 為字串 `NOT-EVALUABLE：export-reads-no-home`（根層 R158）時固定顯示 `量不到：Console 看不到主機上的排程任務`，**不得**顯示成已武裝或未武裝，`armed` 為物件時亦不使用其內容宣稱武裝（Console 只看事件折出的欄位，L-SI-1）；(c) **任何欄位缺席、為 null（`lastSet`、`lastSkip` 除外，那兩者為 null 時顯示「尚無」）或型別不符一律顯示量不到**，不顯示成「無」或 `false`；(d) `schedule` 整鍵缺席（根層尚未升版）＝整組顯示量不到，橫幅其餘欄位不受影響；(e) `SI_STATUS_KNOWN_KEYS` 加入 `schedule`，使它不再落入「其他欄位」；`SiKeyNames` 深層對映（backend 轉出）見 W-S7 (k)；(f) 全部欄位純文字渲染（不使用 `dangerouslySetInnerHTML`，AC-SI-32-1）。
- **W-S2 控件與輸入閘**（表 M-S、表 M-R；`lib/domain/si.ts`，前端先擋、backend 為權威）：(a) 三個控件只對 ADMIN 顯示（啟用／停用開關、週期輸入、「立即啟動一次演化」鈕），非 ADMIN 只渲染唯讀欄位組；(b) 週期輸入的合法界**取自橫幅的 `schedule.periodMin`～`schedule.periodMax`（含端點）**，`lib/domain/si.ts` 與元件內**無任何界值常數**（靜態掃描判）；界由呼叫端傳入 `validateScheduleForm(form, {periodMin, periodMax})`；(c) 輸入旁即時顯示 `periodHint(minutes)`：`minutes % 1440 === 0`→`≈N 天`、否則 `minutes % 60 === 0`→`≈N 小時`、其餘→`約 X.X 小時`（X.X 為一位小數、四捨五入）；純文字；(d) 週期輸入預填目前 `periodMinutes`；界外值、非整數、小數、空白、負數、0 即時標紅並停用送出；**停用方向仍須帶界內週期**（D-CS-6：`enabled` 與 `periodMinutes` 兩鍵皆必備、不開例外；現值落在界外時預填值標紅並提示「請先改成界內週期」，不放行）；(e) 橫幅界取不到（`periodMin`／`periodMax` 缺席、非整數、`periodMin>periodMax`）＝送出停用並說明 `量不到界值`（不放行、以 backend 為準）；(f) `reason`（排程設定）與 `note`（立即啟動）規則同一組（D-CS-4，與根層 R141 (c) 逐項一致）：選填、單行、≤120 code point（補充平面字元算一個）、拒 U+0000～U+001F 與 U+007F、有值不得全空白、允許 `|`；(g) `buildScheduleRequest` 產 `{enabled, periodMinutes, reason?}`（`reason` 空則省略該鍵）；`buildRunRequest` 產 `{note?}`（空則為 `{}`）。
- **W-S3 寫入 UI 流程（排程設定）與入帳指令**：(a) 每個動作先開確認對話框（標題、摘要〔本次會把排程改成什麼：啟用或停用、週期〕、可選理由一行、送出鈕）；(b) 送出呼叫 `usePostSiScheduleSet`（`useWrite` 包裝），成功＝201 收據：顯示 `auditRef`、`kind`、`time`、說明「稽核檔已落地，待入帳」（**不是已生效**）、入帳指令與一句「若主機上的巡邏任務已武裝，下一次心跳（約 N 分鐘內）會自動入帳；Console 看不到該任務是否武裝，所以仍列出手動入帳指令」（N 取自橫幅 `heartbeatMinutes`；缺席時省略「約 N 分鐘內」）；(c) 成功使 `status` 與 `console-writes` 查詢失效重取；(d) 失敗（4xx、5xx、網路）不關窗、表單不收起、`reason` 與 `message` 逐字顯示；(e) 連點只送一次（送出中停用）；(f) `ingestCommands(kind, auditRef)` 對兩新 kind 各產指令，PowerShell 與 bash 形態字串**相同**：`sched-set`→`python tools/selfimproving.py sched set --carrier console --audit-ref <auditRef>`；`run-request`→`python tools/selfimproving.py run-open --trigger a --carrier console --audit-ref <auditRef> --coord console_audit/<auditRef>.json --by console`（與契約 §0 逐字相同；根層 R146 的入帳動詞旗標為其唯一真相）；既有三 kind 的指令不變；(g) `SiWriteKind` 加 `sched-set`、`run-request`，`SI_WRITE_KIND_LABELS` 加「排程設定」「立即啟動」。
- **W-S4 立即啟動對話框與軟停用（D-CS-5）**：(a) 備註一行、確認摘要（摘要須含黑窗說明：主機 `sched_blackout_local` 黑窗內送出的請求，會在黑窗結束後的下一心跳才執行——與 Console PRD §0.11 校正 3、根層 AC-SI-38-8 同義，D-QA-15；文案由 AT-964-4-1 的 NFR-SC-1 判準一併約束「不含已生效字樣」，不另立 AT）、送出呼叫 `usePostSiRunRequest`，收據與錯誤呈現同 W-S3；(b) **backend 不設重送閘**（兩次相同請求各得 201 與不同 `auditRef`），防連點與誤重送只靠前端軟停用：對帳查詢快取（`console-writes` 既有查詢鍵，**只讀、不發新請求**）已有 `kind=run-request` 且 `ingested=false` 的列時，主鈕停用並顯示 `已送出待入帳（稽核編號 <auditRef>）`；(c) 快取缺席（無面板的頁面、查詢載入中或失敗）、對帳 NOT-EVALUABLE、該列 `ingested` 為 true、或待入帳的只有 `sched-set` 時**不停用**（以 backend 為準）；(d) 主機端以「已有未關運轉改記 `sched.skip`」消化多餘請求（根層 R146 (b)）；(d′) 入帳得到的 (a) 運轉由巡邏器於同一心跳執行（根層 AC-SI-38-8、R166；被擋時只寫巡邏日誌、不寫 `sched.skip`，運轉保持開啟、下一心跳再試），Console 不負責執行；(e) 對話框與面板新增的唯讀快取 hook 名稱不得以 `useCreate`、`useUpdate`、`useDelete`、`usePost`、`usePut`、`usePatch`、`useRetry`、`useApprove`、`useSignoff`、`useExecute`、`useSi` 加寫入動詞字樣起頭（例：`useSiConsoleWritesCache`；`si.static.test.ts` 的 `WRITE_HOOK` 判準）。
- **W-S5 `overdue` 警示與略過原因**：(a) `schedule.overdue === true`⇒橫幅與面板顯示醒目警示 `逾期未巡邏：請在主機執行 python tools/selfimproving.py sched show`；(b) `overdue === false`⇒不顯示警示；`overdue` 為 null 或缺席⇒顯示 `量不到` 並註明原因（無事件帳本），**不得**顯示成「沒有逾期」；(c) `overdue` 是推算值（L-SI-2）：文案只說「逾期未巡邏」、**不得**含「任務已停用」「任務已壞」字樣；(d) `lastSkip` 非 null 時顯示略過時間、原因（七值之一，原樣顯示、未知值原樣顯示）與細節；**有略過事件＝巡邏活著只是被擋，畫面顯示略過原因而不是逾期**（此時根層保證 `overdue` 為 false，前端仍以收到的值為準、不自行推翻）。
- **W-S6 ADMIN 邊界與錯誤逐字呈現**：(a) 非 ADMIN（Viewer、Operator）零控件、零 POST；(b) ADMIN 但帳號名不在 `console.si.deciders`⇒backend 403 `si_write_forbidden`，畫面逐字顯示 `reason` 與 `message`、不關窗；(c) 503 `si_write_disabled`（含 `details.cause`）、503 `si_unavailable`（含 `details.cause=schedule_bounds_unavailable` 與 `detail`）、422 `invalid_request`（`details.violations[{field,message}]` 逐項顯示）一律逐字呈現（沿 `siWriteErrorText` 與 `describeError`）；(d) 全樹靜態：新元件不直接 `fetch(`、不含 PUT／PATCH／DELETE 字樣、寫入 hook 僅限 `usePostSiScheduleSet`、`usePostSiRunRequest`（對話框各自恰一個）、不使用 `dangerouslySetInnerHTML`、不以 `localStorage` 或 `sessionStorage` 另存界值或草稿（不存第二份界值）。
- **W-S7 backend 兩個 POST**（API-SI-12、API-SI-13；契約 §0、§1）：(a) **閘門序**（先中者定案）：401→403 `ACCESS_DENIED`（非 ADMIN）→403 `si_write_forbidden`（不在名單）→503 `si_write_disabled`（`details.cause`＝`audit_key_unset`｜`bridge_token_unset`）→422 `invalid_request`（序 5 靜態輸入閘）→（僅 `sched-set`）序 5′ 界檢查→執行；(b) **序 5 輸入閘**（與 W-S2 同一張表；一次回報全部違規，`details.violations[{field,message}]`，欄名 camelCase，帳號 `user`）：`enabled` 布林必填（字串 `true` 拒）、`periodMinutes` JSON 整數必填（小數、字串、負、0 拒；布林拒）、`reason`／`note` 單行 ≤120 code point、控制字元（含 DEL、孤立代理字元）拒、有值不得全空白、先判原值再去前後空白；帳號名 `^[A-Za-z0-9_.-]{1,64}$`；(c) **序 5′**：自 `GET status`（沿 `SiMirrorUseCase`，連線 2 秒、讀取 20 秒、不重試）取 `schedule.periodMin／periodMax` 驗界，界外＝422 `invalid_request`、`violations[{field:periodMinutes,message:須在 <min>～<max> 分鐘之間}]`（數字取自當下 `status`）；**停用方向同樣經過序 5′**；`run-request` 無序 5′；(d) **界取得失敗（D-CS-2）**：`schedule` 鍵缺席、兩界鍵缺席或非整數、`periodMin>periodMax`＝503 `si_unavailable`、`details.cause=schedule_bounds_unavailable`、`details.detail` 指出缺哪個鍵（**不新增 reason**）；`GET status` 本身失敗沿其既有對映（502／504／503 `si_unavailable` 原因逐字轉出）；**不放行、不用快取值、不退回預設界**（連續兩個請求：第一個取得界 A，第二個 `status` 失敗＝503，不沿用 A）；(e) **執行**（寫入模型不變）：先 INSERT `si_console_writes` 列（`kind` 為 `sched-set`｜`run-request`、`subject_id` 與 `digest` 為 NULL）→單次 Bridge 呼叫（`POST /si/schedule:set`｜`/si/runs:request`）→補償與結果不明語意逐字沿 P2b（Bridge 非 2xx⇒補償刪列並逐字轉出原因；逾時結果不明⇒保留列）；稽核 body 鍵序＝共通鍵（`schema_rev`、`audit_ref`、`kind`、`user`、`role`、`time`）之後依書寫序接專屬鍵（`enabled`、`period_minutes`、`reason`｜`note`；選用鍵缺席則略過），外層 `subject` 恆 null，位元組權威＝根層 `consoleaudit.py`（根層 R141 (e)）；(f) **收據**（201）＝`{auditRef, kind, subject:null, time, keyId}`，不含 `body`、`mac`；`time` 秒精度、`±HH:MM`、不輸出 `Z`；(g) **不走 dedupe**：同一請求連送兩次各得 201 與不同 `auditRef`，409 `si_decision_duplicate` 永不出現；(h) **其他方法**：PUT／PATCH／DELETE 對兩新路徑，VIEWER 403、OPERATOR 與 ADMIN 405；GET 對兩新路徑，ADMIN 405、其餘沿既有；(i) **Flyway**：新版本號＝`db/migration/` 現查最大號＋1（**本檔與 AT 不寫死版本號**，D-CS-1）；內容＝DROP 舊 CHECK（**實名以 `pg_constraint` 現查**）後 ADD 五值 CHECK（`decide`、`obs-add`、`obs-close`、`sched-set`、`run-request`）；`kind VARCHAR(12)` 足夠（`run-request` 11 字元，再加 kind 須先放寬欄寬並記於遷移註解）；`si_console_writes_guard()` trigger 不變；(j) **OpenAPI 與 ArchUnit**：兩 operationId `postSiScheduleSet`、`postSiRunRequest`；路徑集合與操作總數同步；`SiReadOnlyArchTest` 擴充覆蓋（兩新 mapping 不帶 `method`、唯一存取該表的類別不變、DML 鎖不變）；(k) **`status.schedule` 透傳**：`SiKeyNames` 深層對映 `period_minutes→periodMinutes`、`period_min→periodMin`、`period_max→periodMax`、`heartbeat_minutes→heartbeatMinutes`、`last_set→lastSet`、`cell_start→cellStart`、`cell_end→cellEnd`、`ran_this_cell→ranThisCell`、`last_skip→lastSkip`；`last_set.at／by／carrier` 與 `last_skip.at／reason／detail` 內層鍵不變；缺鍵≠null、未知鍵透傳的既有規則不變。
- **W-S8 Bridge 兩個 POST**（契約 §2）：驗證順序、`O_CREAT|O_EXCL` 原樣落檔、`fsync`、201 `{"audit_ref","stored":true}`、其餘方法 405 **逐字沿 P2b §2.1**（寫入面停用 503 `si_write_disabled`→`X-Bridge-Token` 403 `si_write_forbidden`→本文單一 UTF-8 JSON 物件且 ≤65536 位元組→外層七鍵形態驗證→落檔；同名 409 `si_audit_exists`；其他 `OSError` 503 `si_unavailable`〔`cause=audit_write_failed`〕）；差異：無路徑參數；外層 `kind` 須分別等於 `sched-set`／`run-request`（與端點相符，否則 422 `invalid_request`）；外層 `subject` **須為 null**（非 null＝422 `invalid_request`、`violations[{field:subject, rule, message}]`）；Bridge 只驗形態、不解 `body`、不驗簽；路由經既有 `_store_signed_audit`，**不新增任何檔案寫入點**；靜態鎖（`test_si_readonly_lock.py` 判準 1′～5′）不變：組 argv 的函式仍恰兩個（`export`、`obs-add --dry-run`）、`si_cli.py` 的 argv 動詞白名單不變、寫入形態只在 `app/si_audit.py` 且路徑引數源自 `audit_dir` 參數；兩新路由不呼叫任何 CLI 動詞。
- **W-S9 稽核 JSON 兩種新 kind、跨語言向量、黃金檔與對帳**：(a) **向量 V5～V8**（固定 body、金鑰、預期 mac；Java 與 Python 兩端各一份、值逐字相同；**本檔不預填數值**，由實作輪以 Java 序列化器產出、經根層 `consoleaudit.py` 驗簽收下後入表，D-CS-3）：V5＝`sched-set` 啟用含 `reason`、V6＝`sched-set` 停用不含 `reason`、V7＝`run-request` 含 `note`、V8＝`run-request` 不含 `note`；(b) **黃金檔 G6～G9**（對映 V5～V8；`Clock.fixed`、金鑰 K0、帳號 admin）住 `backend/src/test/resources/si/audit/` 與 `engine-bridge/tests/fixtures/si_audit/`，兩處**逐位元組相同**；backend 的序列化器重現黃金檔位元組；(c) **真 CLI 收下**（前置＝根層鍵 RELEASE；**釘「收下 rc 0」、不釘數值**）：`test_si_console_ingest.py` 增案例——G6～G9 被根層 `sched set --carrier console`（G6、G7）與 `run-open --trigger a --carrier console`（G8、G9）收下，rc 皆 0；此為「Console 簽出的檔能入帳」的唯一自動化證據，與根層 TCS 的 AT-437-1-3 是同一組黃金檔的兩側驗證（一側 Console 產出且 Python 驗，一側根層 CLI 驗）；(d) **位元組與規則的權威**＝根層 `consoleaudit.py`（鍵序＝共通鍵之後依書寫序接專屬鍵；`reason`／`note` 規則＝根層 R141 (c)：選填、單行、≤120 code point、拒 U+0000～U+001F 與 U+007F、有值不得全空白、允許 `|`；`sched-set` 的 `enabled` 與 `period_minutes` 兩鍵皆必備）；Console 端 422 的向量表與根層 R141 (c) 同表同結果（表驅動）；body 鍵序對調者 CLI 驗簽必拒（`AUDIT-MAC-MISMATCH`）；(e) **對帳**（契約 §4.2）：`items[].kind` 值域加 `sched-set`、`run-request`；這兩種列的 `subjectId`、`digest`、`dkind`、`supersededBy` 恆 null；`ingested`＝事件帳本含任一筆帶相同 `audit_ref` 的 `sched.set`、`run.open` 或 `sched.skip`（`run-request` 於已有未關運轉時入帳結果為 `sched.skip`，亦算已入帳）；`reconcile.status` 為 NOT-EVALUABLE 時整欄 null；`orphans[]` 加映射：`carrier=console` 且帶 `audit_ref` 的 `sched.set`→kind `sched-set`、`run.open`／`sched.skip`→kind `run-request`，而表內無對應 `audit_ref` 者以 `{auditRef, kind, subject:null}` 入列（排序、去重沿 P2b §4）；`status.consolePending` 的種類值域加兩值，橫幅沿既有規則原樣列出；掃描上限與 `scan_cap_exceeded` 不變。
- **W-S10 文件與既有鎖連動**：(a) 每頁說明 `lib/help/self-improving.ts` 補步驟與欄位（怎麼啟用排程、怎麼改週期、怎麼立即啟動一次、「待入帳」與「逾期」各代表什麼；國高中程度，沿 §0.10 D-UX-2；欄位名逐字取自畫面字樣、出處鎖到 `sourceFiles`），走既有三道雙向鎖與可讀性鎖；(b) 既有釘選只改預期值（§4 同步表）：`SI_STATUS_KNOWN_KEYS`、`SiWriteKind` 值域、`SI_WRITE_KIND_LABELS`、`ingestCommands`、端點數（現查；Architecture 預估 79→81）、`SI_REASONS` **不新增鍵**、OpenAPI 路徑與操作總數、Flyway 版本數、ArchUnit 方法集合、Bridge 路由數；(c) 文件：契約 v0.1 依實作如實校對升 v1.0、Architecture §5.6／§10.3 去「規劃」註、`Architecture.md` §12.1 L-SI-1／L-SI-2 保留；RTM 本地子表（預定 §2.14）；(d) `nav` 登記表與 `ToolsRegion.tsx` 不改（`registry.test.ts` 零改動）。

**主控先行裁決（D-CS-1～D-CS-6；已裁，掌舵者可推翻）**：D-CS-1 Flyway 版本一律「現查＋1」，TCS 與 AT 不寫死版本號，CHECK 約束實名以 `pg_constraint` 現查（AT 以查詢結果為準）；D-CS-2 界取得失敗＝503 `si_unavailable`＋`details.cause=schedule_bounds_unavailable`（不新增 reason），`GET status` 本身失敗沿 GET 既有對映、不放行、不用快取值；D-CS-3 稽核 body 鍵序＝共通鍵之後依書寫序接專屬鍵、位元組權威＝根層 `consoleaudit.py` 簽章對象、黃金檔 G6～G9 由實作輪以真 CLI 收下（AT 釘「收下 rc 0」而不是釘數值）；D-CS-4 `reason`／`note` 規則與根層入帳驗證同一組（W-S2 (f)、W-S9 (d)）；D-CS-5 `run-request` 不設 backend 重送閘、前端在對帳快取有待入帳 `run-request` 時停用鈕（快取缺席不停用）、主機端以「已有未關運轉改記 `sched.skip`」消化；D-CS-6 `sched-set` 停用時 `periodMinutes` 仍必填且須在界內（兩鍵皆必備、不開例外）。

**User Story 與 AC 對映**

| US ID | User Story | AC ID | 摘要（PRD 座標；規則） |
|-------|------------|-------|-------------------------|
| US-930 | 作為掌舵者，我要在 Console 看得出自動演化排程有沒有啟用、下一格何時、有沒有逾期，並能啟停、改週期、立即啟動一次，且知道這些請求要等主機入帳才生效 | AC-964-1～AC-964-10 | Console PRD §0.11；根層 AC-SI-37-1、37-3、37-4、37-5；W-S1～W-S10 |

> 編譯相容提醒：本表第一欄用 US ID，不把 AC ID 放第一欄（`sdd_compile` 會把第一欄形如 AC 的表格列當成 AC→AT 映射列掃描）；除 §1 外沒有任何第一欄以 AC 起頭的表格。**§1 表格列的描述格不含豎線字元**（編譯器以豎線切欄）。本檔任何一行不寫測試摘要字樣與 4 位數字同行（`AgentConsole/CLAUDE.md` 文件閘）；範例識別碼不寫字面的 `OBS-SI-`、`PROP-SI-` 接數字。

**INVEST 自檢**：獨立（依賴根層鍵 RELEASE 與 P2b 已落地的稽核管線，兩者皆為前置而非並行依賴）、可協商（§7 列出可裁決的預設）、有價值（掌舵者「UI 可以啟動控制」與「參數化設定週期」的直接落地）、可估計（backend 約 10 個類別小幅修改加 1 個 Flyway 檔與 2 個測試類別、Bridge 1 個路由檔、frontend 3 個新元件與 1 個純函式模組）、小（零新資料表、零新環境變數、零新 compose 掛載）、可測（全部 AT 只用 Testcontainers PG、迷你 Bridge、jsdom、fetch 替身與 Playwright 路由替身，不連外網）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-SC-1 | **寫入不生效即不宣稱生效**：201 收據文案一律為「稽核檔已落地，待入帳」，不得出現「已生效」「已啟用」「已啟動」字樣 | AT-964-3-1、AT-964-4-1 |
| NFR-SC-2 | **量不到不顯示成零或綠**（NFR-SI-09 對稱）：`overdue`、`armed`、任一 `schedule` 欄位量不到時顯示量不到，不顯示「沒有逾期」「未武裝」「無」「false」 | AT-964-1-E-1、AT-964-1-E-2、AT-964-5-2 |
| NFR-SC-3 | **零副作用的拒絕**：序 1～5′ 任一拒絕前後，表內列數、迷你 Bridge 收到的請求數（序 5′ 的 `GET status` 除外，須逐項斷言）、ref 來源取用次數的變動量皆為 0 | AT-964-7-E-1、AT-964-7-E-2、AT-964-7-E-3 |
| NFR-SC-4 | **界不另存第二份**：前後端皆不寫死界值，界只來自 `status.schedule`；根層 CLI 為權威 | AT-964-2-2、AT-964-6-E-1、AT-964-7-E-3 |
| NFR-SC-5 | **零退化與範圍**：既有 AT 在其角色下仍綠，釘選數字只改預期值（§4）；只動 §5.7 允許集合 | V5、V6、AT-964-10-E-1 |
| NFR-SC-6 | **開發 agent 交卷前閘門**（輸出逐字貼入）：(1) 本檔各 AT 逐一單跑；(2) `gradlew clean build`；(3) 前端 lint、`tsc --noEmit`、build、vitest；(4) Bridge `pytest`、`ruff check`（本目錄與 monorepo 根視角各一次）；(5) 讀 rc 先存變數再讀；(6) 不 commit、不碰根層 `tools/`、`.claude/`、凍結檔；(7) 夾具與測試中不得出現不存在於真帳本的字面 `PROP-SI-`、`OBS-SI-`、`RUN-SI-` 接數字；(8) 不得有 `sk-` 形態字串與真機密；(9) 契約 v0.1 與實作不符處以純文字回報；(10) 交卷含流程摩擦節 | SCG-4 實跑檢核 V5、V6 |
| NFR-SC-7 | **跨平台**（根鐵律三）：新程式與測試不引入平台專屬假設；Windows 與 Linux（CI）皆須全綠；macOS 未驗 | V8 |
| NFR-SC-8 | **純文字與不洩漏**：所有來自 `schedule`（含 `lastSkip.detail`）的文字以純文字渲染；金鑰與權杖值不出現在回應、日誌、畫面與測試輸出 | AT-964-1-E-3、AT-964-6-E-2、AT-964-7-1 |

**追溯矩陣**：F-910 ← Console PRD §0.11（校正 1～8）、根層 SelfImproving PRD v0.13 的 FR-SI-37（AC-SI-37-1～37-5）、§9.1 C24、§9.2〈P4 增補〉、§9.3〈P4 寫入端點〉、§9.6 P4 列；Architecture §5.6、§10.3、§12.1 L-SI-1／L-SI-2；契約 `API_Contract_SelfImproving_P2c.md`；P2b 的稽核管線（W10、W11、W14、W15）；US-930 → AC-964-1～10（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3；「已凍結上位文件」相對 `spec-frozen --root`＝monorepo 根；**凍結摘要一律由主控於凍結前以 `Get-FileHash -Algorithm SHA256` 現算並填入，再與該鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 對照，不符以 `show` 為準**）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定、FRD 覆蓋、利害關係人已簽核 | Console PRD §0.11（F-910、US-930、AC-964-1～10）；授權＝sid f1522ddb-bdcf-4104-bb81-614c1118fa9d line 14；凍結常態規則（根 CLAUDE.md） | docs/01_requirements/Agent_ConsoleUI_PRD.md | sha256:a8fae6931f22c4b3680137d075e62a2aa4166cf773811148fc2a9e2aa89ed547（主控現算 2026-11-09 13:43 +08:00） |
| SCG-0／根層 PRD（契約的唯一定稿處） | v0.13 FR-SI-37、§9.2〈P4 增補〉、§9.3〈P4 寫入端點〉 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00；與根層 TCS 追溯表同值） |
| SCG-0／NFR 已量化、User Story INVEST、RTM 初版 | NFR-SC-1～8；US-930；本檔 §1 與 §6（RTM 本地子表於 SCG-5 回填） | （本檔；隨 Stage 凍結，非上位文件） | n/a（自引） |
| SCG-1／整合架構、NFR 對應 | Architecture §5.6、§10.3、§12.1 L-SI-1／L-SI-2 | AgentConsole/docs/02_architecture/Architecture.md | sha256:e61039ade8453f8ba78a92dcc0276b8dd949260b3de140a2c086a228d0b48978（主控現算 2026-11-09 13:43 +08:00） |
| SCG-1／技術選型與偏離清單 | ADR-001（Spring Boot 4.1、JDBC adapter 體例、PG18、Flyway） | AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md | sha256:ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38（主控現算 2026-11-09 13:43 +08:00） |
| SCG-3／API Spec、錯誤碼、Consumer Contract | 契約 v0.1（API-SI-12、API-SI-13、Bridge 兩路由、§1.4 的 `schedule_bounds_unavailable`、§3 稽核 body、§4 `status.schedule` 與對帳、§5 Flyway、§6 前端閘） | AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P2c.md | sha256:ec93e6199dfd356bad589ff4f16ef467a3d59536441cbec18320a71c7a5366ef（主控現算 2026-11-09 13:43 +08:00） |
| SCG-3／前代契約（P2b 的稽核管線與補償語意） | `API_Contract_SelfImproving_P2b.md` §0.1～§0.4、§1.2、§1.4、§2.1、§3.2～§3.4、§4 | AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P2b.md | sha256:32e60de75fda6171a452d28449567aa19e5ade8825e3fcc27e35edd795b92841（主控現算 2026-11-09 13:43 +08:00） |
| SCG-3／上位 TCS | `TCS-SelfImprovingDecide-P2b-20261024.md`（W10、W11、W14、W15 與其 AT）；`TCS-SelfImprovingDecideDedupe-20261031.md`（對帳面板與取代群組；本檔不改其行為） | AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingDecide-P2b-20261024.md | sha256:638def94d922c50801b8b64cb5eb75228111226ba36f8c8801f4b3d9e23f649a（主控現算 2026-11-09 13:43 +08:00） |
| SCG-3／根層 TCS（接縫） | 根層 TCS 的 R139、R141、R146、R158、AT-437-1-3（本檔引用不複寫） | docs/03_testing/contracts/TCS-SelfImproving-P4-20261109.md | sha256:a8671d0f3d6e50f191ff04e53d3c684468fc603a4689754f4cbcbeb890f64b30（主控現算 2026-11-09 13:43 +08:00） |

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC；負控與邊界以 `AT-<NNN>-<Y>-E-<n>` 命名。分層縮寫：**BE**＝backend JUnit（`gradlew test --tests`）、**BR**＝Bridge pytest、**FE**＝frontend vitest、**PW**＝Playwright mock（`E2E_MODE=standalone`，頁面對後端的呼叫以路由替身回應）。測試檔與判定指令見 §2 各 AT 標頭。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-964-1 | 橫幅排程欄位組與量不到規則 | AT-964-1-1 | （FE）完整 `schedule` 的具名欄位組：啟用、週期與換算、最近設定、本格起訖、已執行、最近略過、逾期、武裝 | ✅ | Integration | □ |
| AC-964-1 | 橫幅排程欄位組與量不到規則 | AT-964-1-2 | （FE）`armed` 為量不到字串時固定顯示量不到文案，不顯示已武裝或未武裝 | ✅ | Integration | □ |
| AC-964-1 | 橫幅排程欄位組與量不到規則 | AT-964-1-3 | （FE）`SI_STATUS_KNOWN_KEYS` 含 `schedule`：不再列入其他欄位，其餘未知鍵仍列入 | ✅ | Integration | □ |
| AC-964-1 | 橫幅排程欄位組與量不到規則 | AT-964-1-E-1 | （FE）`scheduleFields` 對缺席、null、型別不符逐欄回量不到，不回無或 false | ✅ | Unit | □ |
| AC-964-1 | 橫幅排程欄位組與量不到規則 | AT-964-1-E-2 | （FE）`schedule` 整鍵缺席：整組量不到，橫幅其餘欄位不受影響 | ✅ | Integration | □ |
| AC-964-1 | 橫幅排程欄位組與量不到規則 | AT-964-1-E-3 | （FE）`lastSkip.detail` 含標記字樣時以純文字呈現，不產生元素 | ✅ | Integration | □ |
| AC-964-2 | 啟停開關與週期輸入 | AT-964-2-1 | （FE）`periodHint` 換算：整天、整小時、其餘一位小數 | ✅ | Unit | □ |
| AC-964-2 | 啟停開關與週期輸入 | AT-964-2-2 | （FE）界取自橫幅的 `periodMin`／`periodMax`，改界後行為隨之改變 | ✅ | Integration | □ |
| AC-964-2 | 啟停開關與週期輸入 | AT-964-2-3 | （FE）預填目前週期；停用時週期仍必填並可送出 | ✅ | Integration | □ |
| AC-964-2 | 啟停開關與週期輸入 | AT-964-2-4 | （PW）ADMIN 啟用開關流程：開對話框、送出、顯示待入帳收據 | ✅ | E2E | □ |
| AC-964-2 | 啟停開關與週期輸入 | AT-964-2-E-1 | （FE）週期的界外、端點、非整數、小數、空白、負數、零：標紅並停用送出，端點通過 | ✅ | Integration | □ |
| AC-964-2 | 啟停開關與週期輸入 | AT-964-2-E-2 | （FE）界取不到：送出停用並說明量不到界值；現值落界外時預填標紅 | ✅ | Integration | □ |
| AC-964-3 | 排程設定確認對話框與收據 | AT-964-3-1 | （FE）送出的請求本文與 201 收據、待入帳文案、入帳指令、查詢失效重取 | ✅ | Integration | □ |
| AC-964-3 | 排程設定確認對話框與收據 | AT-964-3-2 | （FE）`ingestCommands` 對兩新 kind 的指令字串逐字相同，既有三 kind 不變 | ✅ | Unit | □ |
| AC-964-3 | 排程設定確認對話框與收據 | AT-964-3-3 | （FE）確認摘要文字與理由選填：空理由時本文不含 `reason` | ✅ | Integration | □ |
| AC-964-3 | 排程設定確認對話框與收據 | AT-964-3-4 | （PW）ADMIN 改週期流程：換算提示、送出、收據 | ✅ | E2E | □ |
| AC-964-3 | 排程設定確認對話框與收據 | AT-964-3-E-1 | （FE）失敗不關窗：409、502、504 與網路錯誤逐字顯示 reason 與 message | ✅ | Integration | □ |
| AC-964-3 | 排程設定確認對話框與收據 | AT-964-3-E-2 | （FE）連點只送一次；缺必填停用送出 | ✅ | Integration | □ |
| AC-964-3 | 排程設定確認對話框與收據 | AT-964-3-E-3 | （FE）`reason` 規則負控表：超長、換行、控制字元、全空白拒，豎線與補充平面字元放行 | ✅ | Unit | □ |
| AC-964-4 | 立即啟動對話框與待入帳停用 | AT-964-4-1 | （FE）送出的請求本文與收據、入帳指令、待入帳文案 | ✅ | Integration | □ |
| AC-964-4 | 立即啟動對話框與待入帳停用 | AT-964-4-2 | （FE）對帳快取有待入帳的 `run-request`：主鈕停用並顯示稽核編號 | ✅ | Integration | □ |
| AC-964-4 | 立即啟動對話框與待入帳停用 | AT-964-4-3 | （FE）快取缺席、對帳量不到、已入帳、只有 `sched-set` 待入帳：皆不停用 | ✅ | Integration | □ |
| AC-964-4 | 立即啟動對話框與待入帳停用 | AT-964-4-4 | （PW）ADMIN 立即啟動流程：送出、收據、待入帳後鈕停用 | ✅ | E2E | □ |
| AC-964-4 | 立即啟動對話框與待入帳停用 | AT-964-4-E-1 | （FE）軟停用只讀快取：開啟對話框前後 `console-writes` 的 GET 次數不變 | ✅ | Integration | □ |
| AC-964-4 | 立即啟動對話框與待入帳停用 | AT-964-4-E-2 | （FE）`note` 規則負控表與空備註時本文為空物件 | ✅ | Unit | □ |
| AC-964-5 | 逾期警示與略過原因 | AT-964-5-1 | （FE）`overdue` 為真：警示文案逐字含主機現查指令 | ✅ | Integration | □ |
| AC-964-5 | 逾期警示與略過原因 | AT-964-5-2 | （FE）`overdue` 為 null 或缺席顯示量不到與原因；為 false 不顯示警示 | ✅ | Integration | □ |
| AC-964-5 | 逾期警示與略過原因 | AT-964-5-3 | （FE）`lastSkip` 非 null：顯示時間、原因、細節；顯示略過而非逾期 | ✅ | Integration | □ |
| AC-964-5 | 逾期警示與略過原因 | AT-964-5-E-1 | （FE）逾期三態乘略過兩態的矩陣：無誤報，文案不含任務已停用字樣 | ✅ | Unit | □ |
| AC-964-6 | 非 ADMIN 唯讀與錯誤逐字呈現 | AT-964-6-1 | （FE）Viewer 與 Operator：零控件、零 POST、唯讀欄位組仍顯示 | ✅ | Integration | □ |
| AC-964-6 | 非 ADMIN 唯讀與錯誤逐字呈現 | AT-964-6-2 | （FE）名單外 ADMIN 的 403 `si_write_forbidden` 逐字顯示且不關窗 | ✅ | Integration | □ |
| AC-964-6 | 非 ADMIN 唯讀與錯誤逐字呈現 | AT-964-6-3 | （FE）503 `si_write_disabled` 與 503 `si_unavailable` 的 cause 與 detail 逐字顯示 | ✅ | Integration | □ |
| AC-964-6 | 非 ADMIN 唯讀與錯誤逐字呈現 | AT-964-6-4 | （FE）422 `invalid_request` 的 violations 逐項顯示 | ✅ | Integration | □ |
| AC-964-6 | 非 ADMIN 唯讀與錯誤逐字呈現 | AT-964-6-E-1 | （FE）靜態：新元件不直接 fetch、不含 PUT 等字樣、寫入 hook 恰為各自一個、界值零常數 | ✅ | Unit | □ |
| AC-964-6 | 非 ADMIN 唯讀與錯誤逐字呈現 | AT-964-6-E-2 | （FE）靜態：不使用危險 HTML 注入、不以瀏覽器儲存另存界值或草稿 | ✅ | Unit | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-1 | （BE）`sched-set` 的 201、收據鍵集合、表內新列、迷你 Bridge 收到的外層與 body 鍵序與簽章 | ✅ | Integration | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-2 | （BE）`run-request` 的 201：空物件與含備註兩種本文 | ✅ | Integration | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-3 | （BE）停用方向帶界內週期仍 201，body 的 `enabled` 為 false | ✅ | Integration | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-4 | （BE）序 5′ 界檢查：端點 201、端點外 422 且訊息取自當下界、界改變後隨之改變 | ✅ | Integration | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-5 | （BE）不走重送閘：同一請求連送各得 201 與不同 `auditRef`，無 409 重送 reason | ✅ | Integration | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-6 | （BE）Flyway 新版本：版本現查加一、CHECK 實名現查、五值可寫、第六值被拒、舊列不受影響 | ✅ | Integration | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-7 | （BE）OpenAPI：兩 operationId、路徑集合與操作總數、兩端點的狀態碼集合與說明 | ✅ | Contract | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-8 | （BE）`status.schedule` 經 `SiKeyNames` 的深層欄名對映與透傳規則 | ✅ | Unit | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-9 | （BE）ArchUnit：兩新 mapping 不帶 method、唯一存取該表的類別與 DML 鎖不變 | ✅ | Unit | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-E-1 | （BE）閘門序逐級：401、403 兩種、503 兩種 cause，每級零副作用 | ✅ | Integration | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-E-2 | （BE）序 5 輸入閘：全部違規一次回報，欄位表驅動並與根層字串規則同表 | ✅ | Integration | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-E-3 | （BE）界取得失敗 503 `schedule_bounds_unavailable`、status 失敗沿 GET 對映、不用快取值 | ✅ | Integration | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-E-4 | （BE）補償與結果不明：Bridge 非 2xx 補償刪列、逾時保留列、原因逐字轉出 | ✅ | Integration | □ |
| AC-964-7 | backend 兩個 POST | AT-964-7-E-5 | （BE）其餘方法：PUT、PATCH、DELETE 的 403 與 405，GET 的 405 | ✅ | Integration | □ |
| AC-964-8 | Bridge 兩個 POST | AT-964-8-1 | （BR）`POST /si/schedule:set`：201、原樣位元組落檔、獨佔建立 | ✅ | Integration | □ |
| AC-964-8 | Bridge 兩個 POST | AT-964-8-2 | （BR）`POST /si/runs:request`：201、原樣位元組落檔 | ✅ | Integration | □ |
| AC-964-8 | Bridge 兩個 POST | AT-964-8-3 | （BR）外層七鍵與 kind 相符、subject 為 null 時接受 | ✅ | Integration | □ |
| AC-964-8 | Bridge 兩個 POST | AT-964-8-4 | （BR）靜態鎖不變：組 argv 函式恰兩個、動詞白名單不變、寫入形態僅在稽核模組、兩新路由不呼叫 CLI | ✅ | Unit | □ |
| AC-964-8 | Bridge 兩個 POST | AT-964-8-5 | （BR）檔名安全：非 UUID 與路徑穿越字樣的 audit_ref 不落檔 | ✅ | Integration | □ |
| AC-964-8 | Bridge 兩個 POST | AT-964-8-E-1 | （BR）subject 非 null 與 kind 不符：422 與 violations，不落檔 | ✅ | Integration | □ |
| AC-964-8 | Bridge 兩個 POST | AT-964-8-E-2 | （BR）權杖、大小、非 JSON、同名 409、落檔 I/O 失敗的逐級對映 | ✅ | Integration | □ |
| AC-964-8 | Bridge 兩個 POST | AT-964-8-E-3 | （BR）其餘方法 405 | ✅ | Integration | □ |
| AC-964-9 | 稽核 JSON 向量、黃金檔與對帳 | AT-964-9-1 | （BE）向量 V5～V8 的 Java 端：body 鍵序與簽章，值由實作輪產出並入表 | ✅ | Unit | □ |
| AC-964-9 | 稽核 JSON 向量、黃金檔與對帳 | AT-964-9-2 | （BE）序列化器在固定時鐘與金鑰下逐位元組重現黃金檔 G6～G9 | ✅ | Unit | □ |
| AC-964-9 | 稽核 JSON 向量、黃金檔與對帳 | AT-964-9-3 | （BR）黃金檔副本與 backend 產出逐位元組相同，且真 CLI 收下 G6～G9 rc 為 0 | ✅ | Integration | □ |
| AC-964-9 | 稽核 JSON 向量、黃金檔與對帳 | AT-964-9-4 | （BE）`console-writes`：兩新 kind 的列、其餘欄位恆 null、`ingested` 判準 | ✅ | Integration | □ |
| AC-964-9 | 稽核 JSON 向量、黃金檔與對帳 | AT-964-9-5 | （BE）`orphans[]` 的新 kind 映射、排序與去重 | ✅ | Integration | □ |
| AC-964-9 | 稽核 JSON 向量、黃金檔與對帳 | AT-964-9-E-1 | （BR）Python 端向量驗簽；body 鍵序對調的檔被真 CLI 以 MAC 不符拒收 | ✅ | Integration | □ |
| AC-964-9 | 稽核 JSON 向量、黃金檔與對帳 | AT-964-9-E-2 | （BE）對帳量不到時兩新 kind 的 `ingested` 為 null | ✅ | Integration | □ |
| AC-964-9 | 稽核 JSON 向量、黃金檔與對帳 | AT-964-9-E-3 | （BE）`run-request` 以 `sched.skip` 入帳亦為已入帳 | ✅ | Integration | □ |
| AC-964-10 | 文件與說明連動 | AT-964-10-1 | （FE）每頁說明含排程步驟與欄位字樣，三道雙向鎖與可讀性鎖綠 | ✅ | Unit | □ |
| AC-964-10 | 文件與說明連動 | AT-964-10-2 | （FE）既有釘選的新預期值：端點數、已知鍵、寫入 kind 值域與標籤、`SI_REASONS` 鍵集合不變 | ✅ | Contract | □ |
| AC-964-10 | 文件與說明連動 | AT-964-10-3 | （FE）文件掃描：Architecture 去規劃註、契約升 v1.0、兩條已知限制仍在 | ✅ | Unit | □ |
| AC-964-10 | 文件與說明連動 | AT-964-10-E-1 | （FE）既有純函式的行為回歸表：三種舊 kind 的指令字串、對帳面板函式、`SI_REASONS` 順序不變 | ✅ | Unit | □ |

## 2. 可自動化 AT 格式規範

> **驗收字樣與判定指令**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（形態：方括號內為 `AT_OK_` 接 AT 底線形去掉 `AT_` 前綴的部分；E 類的 `E` 保留）；Then、And 行**只有驗收字樣一組引號**，其餘程式碼字面值一律用反引號，引號、撇號與全形引號一律不得出現在 Then、And 行（編譯器的引號字面抽取會把被框住的字誤收為期望輸出片段）；本檔的 Given、When 行同樣不用雙引號（JSON 以不帶引號的簡寫表示）。本 Feature 走 SDD session-only 路徑：實作者在 session 內自跑判定指令，**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。
>
> **AT 底線形**＝把 AT ID 的連字號換成底線（`AT-964-7-E-3` 的底線形是 `AT_964_7_E_3`）；每個 AT 的測試函式（Java 為方法、pytest 為函式、vitest 為 `it` 名稱、Playwright 為 `test` 名稱）須含其底線形；每個 AC 內數字序與 E 序各不超過 9。**同一 AT 的子情境**一律以參數化或 `subTest`／`it.each`／`@ParameterizedTest` 實作並保留底線形，任一子情境失敗時，失敗訊息須指出是哪一個。**AT 內不引用其他 AT 的 ID**。**不得新增 skip 或 `it.skip`／`describe.skip`／`test.skip`／`@Disabled`**：Docker 缺席視為環境壞、直接失敗。
>
> **每個 AT 區塊 8 行**：三行 `#` 標頭（AT ID；對應 AC、W-S 規則與 PRD 座標；測試類型、自動化工具、判定指令）、`Scenario:`（＝§1 的 AT 描述）、`Given`、`When`、`Then`、帶驗收字樣的 `And`。
>
> **判定指令的四種形態**（標頭只列引數部分；PowerShell 不用裸 `cd`，用 `Push-Location … Pop-Location` 同行成對，讀 rc 先存變數再讀）：backend `gradlew test --tests "<類別全名>.<AT 底線形>*"`（cwd＝`AgentConsole/backend`；整合測試需 Docker）；Bridge `python -m pytest <檔> -k <AT 底線形> -q`（cwd＝`AgentConsole/engine-bridge`，根層 `.venv`）；frontend `npx vitest run <檔> -t <AT 底線形>`（cwd＝`AgentConsole/frontend`）；Playwright `npx playwright test <檔> -g <AT 底線形>`（cwd＝`AgentConsole/frontend`，`E2E_MODE=standalone`）。
>
> **斷言簡寫**（資料與設施細節見 §5）：**backend**：`ADMIN`（帳號 admin，在 `console.si.deciders`、金鑰與權杖已設）、`SEAM`（`SiWriteSeam` 排入 ref）、`MINI`（迷你 Bridge；本鍵加 `MINI.status(schedule)` 設定其 `GET /si/status` 回應的 `items[0].schedule`、`MINI.si.writes` 記錄兩個新落檔路徑收到的位元組）、`BOUNDS`＝`periodMin` 60、`periodMax` 10080（夾具值；測試**不**自行硬編成預期界，一律取 `MINI.status` 設定的值比對）、`writeRows()`（表內逐列內容含 body 位元組）、`refs`（`SiAuditRefSource` 取用次數）；**frontend**：`renderSi`、fetch 替身、`overrides` 沿 P2b；`statusItem({ schedule })` 與 `sched(over)`（見 §5.6：camelCase 的完整 `schedule` 物件，`over` 逐鍵覆寫，`DROP` 表示刪鍵）；`ADMIN_UI`、`VIEWER_UI`、`OPERATOR_UI` 為三種角色的渲染設定；`writeItem` 沿 P2b。

**A. frontend（FE）：橫幅、輸入閘、對話框、說明**

```gherkin
# AT-964-1-1
# 對應 AC: AC-964-1（W-S1；根層 AC-SI-37-3、37-4）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiSchedulePanel.test.tsx -t AT_964_1_1
Scenario: （FE）完整 `schedule` 的具名欄位組：啟用、週期與換算、最近設定、本格起訖、已執行、最近略過、逾期、武裝
  Given `renderSi` 以 `ADMIN_UI` 與 `statusItem({ schedule: sched() })` 渲染；`sched()` 的 `enabled` 為 true、`periodMinutes` 為 1440、`lastSet` 為 `{at, by, carrier}` 三鍵齊全、`cellStart` 與 `cellEnd` 為帶 offset 的 ISO、`ranThisCell` 為 true、`lastSkip` 為 `{at, reason, detail}`、`overdue` 為 false
  When 檢視橫幅的自動演化排程欄位組
  Then 逐欄各有一個具名標籤與值：啟用顯示是、週期顯示 `1440` 並列 `≈1 天`、最近設定顯示 at 與 by 與 carrier、本格起訖顯示兩個時間、本格已執行顯示是、最近略過顯示 at 與 reason 與 detail、逾期顯示否、武裝顯示量不到文案；欄位組出現在 `SiStatusBanner` 與 `SiSchedulePanel` 時內容逐字相同（同一個 `scheduleFields`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_1_1]"
```
```gherkin
# AT-964-1-2
# 對應 AC: AC-964-1（W-S1 (b)；Architecture §12.1 L-SI-1）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiSchedulePanel.test.tsx -t AT_964_1_2
Scenario: （FE）`armed` 為量不到字串時固定顯示量不到文案，不顯示已武裝或未武裝
  Given `sched()` 的 `armed` 依序為字串 `NOT-EVALUABLE：export-reads-no-home`、物件 `{task, present: true, credential: x}`、物件 `{task, present: false, credential: y}`、布林 true
  When 各渲染一次並取 armed 欄的文字
  Then 四次的 armed 欄文字皆為 `量不到：Console 看不到主機上的排程任務`；畫面任一處都不含已武裝與未武裝字樣
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_1_2]"
```
```gherkin
# AT-964-1-3
# 對應 AC: AC-964-1（W-S1 (e)；PRD §0.11 校正 1）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_964_1_3
Scenario: （FE）`SI_STATUS_KNOWN_KEYS` 含 `schedule`：不再列入其他欄位，其餘未知鍵仍列入
  Given `statusItem` 帶 `schedule` 與一個虛構未知鍵 `futureKey`
  When 渲染 `SiView` 並檢視橫幅的其他欄位區
  Then 其他欄位區含 `futureKey`、不含 `schedule`；`SI_STATUS_KNOWN_KEYS` 含 `schedule` 且既有鍵一個不少
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_1_3]"
```
```gherkin
# AT-964-1-E-1
# 對應 AC: AC-964-1（W-S1 (c)；NFR-SC-2）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_964_1_E_1
Scenario: （FE）`scheduleFields` 對缺席、null、型別不符逐欄回量不到，不回無或 false
  Given 對 `sched()` 逐鍵（`enabled`、`periodMinutes`、`cellStart`、`cellEnd`、`ranThisCell`、`overdue`、`armed`）各做三種變形：刪鍵、設為 null、設為錯型別（字串／數字／物件互換）；`lastSet`、`lastSkip` 設為 null 為另一組
  When 呼叫 `scheduleFields`
  Then 每個變形的對應欄位值為量不到標記（不是空字串、不是 false、不是 0）；其餘欄位不受影響；`lastSet`、`lastSkip` 為 null 時為尚無
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_1_E_1]"
```
```gherkin
# AT-964-1-E-2
# 對應 AC: AC-964-1（W-S1 (d)）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_964_1_E_2
Scenario: （FE）`schedule` 整鍵缺席：整組量不到，橫幅其餘欄位不受影響
  Given `statusItem` 不含 `schedule` 鍵（其他鍵與既有測試夾具相同）
  When 渲染 `SiView`
  Then 排程欄位組每個欄位皆顯示量不到；橫幅的其餘具名欄位（事件偵測、待決提案等）與缺席前逐字相同；頁面不丟例外、不空白
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_1_E_2]"
```
```gherkin
# AT-964-1-E-3
# 對應 AC: AC-964-1（W-S1 (f)；NFR-SC-8；PRD AC-SI-32-1）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiSchedulePanel.test.tsx -t AT_964_1_E_3
Scenario: （FE）`lastSkip.detail` 含標記字樣時以純文字呈現，不產生元素
  Given `sched()` 的 `lastSkip.detail` 為含 `<img src=x onerror=alert(1)>` 與 `<script>` 字樣的字串，`lastSkip.reason` 為未知值 `weird-reason`
  When 渲染
  Then 畫面以文字顯示該字串原文（`textContent` 含尖括號字樣）；容器內查無 `img`、`script` 元素；未知 reason 原樣顯示
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_1_E_3]"
```
```gherkin
# AT-964-2-1
# 對應 AC: AC-964-2（W-S2 (c)）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_964_2_1
Scenario: （FE）`periodHint` 換算：整天、整小時、其餘一位小數
  Given `periodHint` 的輸入 1440、2880、60、120、90、100、75、61、10080
  When 逐一呼叫
  Then 依序回 `≈1 天`、`≈2 天`、`≈1 小時`、`≈2 小時`、`約 1.5 小時`、`約 1.7 小時`、`約 1.3 小時`、`約 1.0 小時`、`≈7 天`；回傳皆為純文字字串
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_2_1]"
```
```gherkin
# AT-964-2-2
# 對應 AC: AC-964-2（W-S2 (b)；NFR-SC-4）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_2_2
Scenario: （FE）界取自橫幅的 `periodMin`／`periodMax`，改界後行為隨之改變
  Given 兩份 `sched()`：甲的 `periodMin` 為 60、`periodMax` 為 10080；乙的 `periodMin` 為 30、`periodMax` 為 120；對話框各以其渲染
  When 於週期輸入各填 45
  Then 甲的送出鈕停用且錯誤文字指出甲的界（`60` 與 `10080` 來自夾具，不是常數）；乙的送出鈕可用；`validateScheduleForm` 的簽章要求呼叫端傳入界（缺界參數時回量不到界值）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_2_2]"
```
```gherkin
# AT-964-2-3
# 對應 AC: AC-964-2（W-S2 (d)；D-CS-6）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_2_3
Scenario: （FE）預填目前週期；停用時週期仍必填並可送出
  Given `sched()` 的 `periodMinutes` 為 720、`enabled` 為 true；對話框開啟
  When 把開關切為停用並送出；另一次清空週期欄再送出
  Then 週期欄預填 `720`；停用送出的請求本文為 `{enabled: false, periodMinutes: 720}`；清空週期時送出停用且標紅（停用方向不開例外）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_2_3]"
```
```gherkin
# AT-964-2-E-1
# 對應 AC: AC-964-2（W-S2 (d)）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_2_E_1
Scenario: （FE）週期的界外、端點、非整數、小數、空白、負數、零：標紅並停用送出，端點通過
  Given 界為 `periodMin` 60、`periodMax` 10080（取自夾具）；輸入值清單 60、10080、59、10081、90.5、abc、空字串、全空白、-60、0、1e3
  When 逐值填入週期欄
  Then 60 與 10080 可送出且不標紅；其餘皆標紅並停用送出（`1e3` 不當作整數 1000 收下）；每個值的判定在子情境名稱中可辨識
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_2_E_1]"
```
```gherkin
# AT-964-2-E-2
# 對應 AC: AC-964-2（W-S2 (d)(e)；契約 §1.4 已知邊界）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_2_E_2
Scenario: （FE）界取不到：送出停用並說明量不到界值；現值落界外時預填標紅
  Given 四種 `sched()` 變形：`periodMin` 缺席、`periodMax` 為字串、`periodMin` 大於 `periodMax`、`schedule` 整鍵缺席；另一份現值 `periodMinutes` 為 30 而界為 60 至 10080
  When 開啟對話框
  Then 前四者送出鈕停用且顯示 `量不到界值`；第五份預填 `30` 標紅並提示請先改成界內週期、送出停用
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_2_E_2]"
```
```gherkin
# AT-964-3-1
# 對應 AC: AC-964-3（W-S3 (a)～(c)；NFR-SC-1）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_3_1
Scenario: （FE）送出的請求本文與 201 收據、待入帳文案、入帳指令、查詢失效重取
  Given `ADMIN_UI`；fetch 替身對 `POST /api/v1/si/schedule/set` 回 201 收據（`auditRef` 為 UUID、`kind` 為 sched-set、`subject` 為 null、`time`、`keyId`）；`heartbeatMinutes` 為 15；對話框填啟用、週期 120、理由為一行
  When 送出
  Then 請求本文恰為 `{enabled: true, periodMinutes: 120, reason}`；收據區顯示 `auditRef`、`sched-set`、`time` 與 `稽核檔已落地，待入帳`，**不含**已生效字樣；顯示 `python tools/selfimproving.py sched set --carrier console --audit-ref <auditRef>`（PowerShell 與 bash 兩處字串相同）與含 `15` 的巡邏心跳說明；`status` 與 `console-writes` 兩個查詢各被失效並重取一次
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_3_1]"
```
```gherkin
# AT-964-3-2
# 對應 AC: AC-964-3（W-S3 (f)(g)）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_964_3_2
Scenario: （FE）`ingestCommands` 對兩新 kind 的指令字串逐字相同，既有三 kind 不變
  Given 一個固定的 auditRef 與五種 kind（decide、obs-add、obs-close、sched-set、run-request；decide 帶既有所需參數）
  When 呼叫 `ingestCommands`，並讀 `SI_WRITE_KIND_LABELS`
  Then `sched-set` 的 PowerShell 與 bash 兩形態皆為 `python tools/selfimproving.py sched set --carrier console --audit-ref <ref>`；`run-request` 皆為 `python tools/selfimproving.py run-open --trigger a --carrier console --audit-ref <ref> --coord console_audit/<ref>.json --by console`；既有三 kind 的輸出與修改前逐字相同；標籤含 `排程設定` 與 `立即啟動`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_3_2]"
```
```gherkin
# AT-964-3-3
# 對應 AC: AC-964-3（W-S3 (a)；W-S2 (g)）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_3_3
Scenario: （FE）確認摘要文字與理由選填：空理由時本文不含 `reason`
  Given 對話框填停用、週期 1440、理由留空
  When 檢視確認摘要並送出
  Then 摘要文字說明本次會把排程改成停用並列出週期（含 `≈1 天`）；請求本文恰為 `{enabled: false, periodMinutes: 1440}`（無 `reason` 鍵）；理由填入一行後本文才含 `reason`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_3_3]"
```
```gherkin
# AT-964-3-4
# 對應 AC: AC-964-3（W-S3；Playwright mock）
# 測試類型: E2E；自動化工具: Playwright（mock 模式，路由替身）；判定指令: npx playwright test tests/e2e/self-improving-schedule.mock.spec.ts -g AT_964_3_4
Scenario: （PW）ADMIN 改週期流程：換算提示、送出、收據
  Given `E2E_MODE=standalone`；路由替身回 ADMIN 登入、`GET /api/v1/si/status`（含 `schedule`，界 60 至 10080）與 `POST /api/v1/si/schedule/set` 的 201；瀏覽器開 `/self-improving`
  When 於排程面板開設定對話框，週期輸入 180 並確認送出
  Then 週期旁即時出現 `≈3 小時`；替身收到的本文為 `{enabled, periodMinutes: 180}`；畫面出現 `稽核檔已落地，待入帳` 與入帳指令；整個流程無主控台錯誤
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_3_4]"
```
```gherkin
# AT-964-3-E-1
# 對應 AC: AC-964-3（W-S3 (d)）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_3_E_1
Scenario: （FE）失敗不關窗：409、502、504 與網路錯誤逐字顯示 reason 與 message
  Given fetch 替身依序回 409 `si_audit_exists`、502、504、網路例外，各帶 `reason` 與 `message`
  When 各送出一次
  Then 每次對話框仍開著、表單內容保留、送出鈕恢復可用、畫面逐字顯示該次的 reason 與 message；無收據區出現
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_3_E_1]"
```
```gherkin
# AT-964-3-E-2
# 對應 AC: AC-964-3（W-S3 (e)）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_3_E_2
Scenario: （FE）連點只送一次；缺必填停用送出
  Given fetch 替身對 POST 延遲回應；對話框填合法值
  When 連續點送出鈕三次；另一次把週期清空後點送出
  Then 替身收到的 POST 恰一次；回應前送出鈕為停用；清空週期時送出鈕停用、POST 為零次
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_3_E_2]"
```
```gherkin
# AT-964-3-E-3
# 對應 AC: AC-964-3（W-S2 (f)；D-CS-4）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_964_3_E_3
Scenario: （FE）`reason` 規則負控表：超長、換行、控制字元、全空白拒，豎線與補充平面字元放行
  Given 輸入：120 個 U+4E2D、121 個 U+4E2D、120 個 U+1F600、121 個 U+1F600、`a|b`、`x\ny`、`x\ry`、U+0000、U+001F、U+007F、空字串、三個空格、一個 TAB、前後有空白的 `  ok  `
  When 呼叫 `validateScheduleForm` 的 reason 判定
  Then 放行：120 個 U+4E2D、120 個 U+1F600、`a|b`、`  ok  `（建請求時去前後空白）、空字串（視為未填：本文省略 `reason`，不算違規）；拒：121 個 U+4E2D、121 個 U+1F600、含換行、CR、U+0000、U+001F、U+007F、三個空格、TAB（全空白為違規）；結果與根層 TCS 的 R141 (c) 逐項一致（空字串的前後端差異見 §7.1 ⚖ 4）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_3_E_3]"
```
```gherkin
# AT-964-4-1
# 對應 AC: AC-964-4（W-S4 (a)；NFR-SC-1）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiRunRequestDialog.test.tsx -t AT_964_4_1
Scenario: （FE）送出的請求本文與收據、入帳指令、待入帳文案
  Given `ADMIN_UI`；對帳快取無待入帳；fetch 替身對 `POST /api/v1/si/runs/request` 回 201 收據（`kind` 為 run-request、`subject` 為 null）；對話框填備註一行
  When 送出
  Then 請求本文為 `{note}`；收據區顯示 `稽核檔已落地，待入帳`（不含已啟動字樣）與 `python tools/selfimproving.py run-open --trigger a --carrier console --audit-ref <auditRef> --coord console_audit/<auditRef>.json --by console`；備註留空時本文為 `{}`（註：入帳後的 (a) 運轉由巡邏器同心跳執行，見根層 AC-SI-38-8；本 AT 只判 Console 側呈現）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_4_1]"
```
```gherkin
# AT-964-4-2
# 對應 AC: AC-964-4（W-S4 (b)；D-CS-5）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiRunRequestDialog.test.tsx -t AT_964_4_2
Scenario: （FE）對帳快取有待入帳的 `run-request`：主鈕停用並顯示稽核編號
  Given 對帳查詢快取已有 `writeItem({ auditRef: U1, kind: run-request, ingested: false })`，`reconcile.status` 為 ok
  When 開啟立即啟動對話框
  Then 主鈕為 disabled；畫面顯示 `已送出待入帳（稽核編號 <U1>）`；備註欄仍可編輯、取消鈕可用
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_4_2]"
```
```gherkin
# AT-964-4-3
# 對應 AC: AC-964-4（W-S4 (c)）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiRunRequestDialog.test.tsx -t AT_964_4_3
Scenario: （FE）快取缺席、對帳量不到、已入帳、只有 `sched-set` 待入帳：皆不停用
  Given 四種快取狀態：無該查詢快取；`reconcile.status` 為 NOT-EVALUABLE；一筆 run-request 且 `ingested` 為 true；一筆 sched-set 且 `ingested` 為 false
  When 各開啟對話框
  Then 四次主鈕皆可用；皆不顯示 `已送出待入帳`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_4_3]"
```
```gherkin
# AT-964-4-4
# 對應 AC: AC-964-4（W-S4；Playwright mock）
# 測試類型: E2E；自動化工具: Playwright（mock 模式，路由替身）；判定指令: npx playwright test tests/e2e/self-improving-schedule.mock.spec.ts -g AT_964_4_4
Scenario: （PW）ADMIN 立即啟動流程：送出、收據、待入帳後鈕停用
  Given `E2E_MODE=standalone`；路由替身回 ADMIN、`status`、`POST /api/v1/si/runs/request` 的 201，以及 `GET /api/v1/si/console-writes`（第一次無待入帳、送出後重取含一筆 run-request 且 ingested 為 false）
  When 開 `/self-improving`，點立即啟動一次演化並確認送出
  Then 替身收到的本文為 `{}` 或含備註的物件；畫面出現待入帳收據；送出後重開對話框主鈕停用並顯示 `已送出待入帳（稽核編號 …）`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_4_4]"
```
```gherkin
# AT-964-4-E-1
# 對應 AC: AC-964-4（W-S4 (b)(e)；P2b 的快取只讀體例）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiRunRequestDialog.test.tsx -t AT_964_4_E_1
Scenario: （FE）軟停用只讀快取：開啟對話框前後 `console-writes` 的 GET 次數不變
  Given 對帳面板已載入一次（替身記錄 `console-writes` 的 GET 為一次）
  When 開啟、關閉、再開啟立即啟動對話框兩次
  Then `console-writes` 的 GET 次數仍為一次；對話框使用的快取 hook 名稱不以寫入動詞前綴起頭
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_4_E_1]"
```
```gherkin
# AT-964-4-E-2
# 對應 AC: AC-964-4（W-S2 (f)(g)；D-CS-4）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_964_4_E_2
Scenario: （FE）`note` 規則負控表與空備註時本文為空物件
  Given 與 AT-964-3-E-3 同一張輸入表（改套用於 note）
  When 呼叫 `validateRunRequestForm` 與 `buildRunRequest`
  Then 放行與拒收的集合與 reason 的結果逐項相同；備註空字串或未填時 `buildRunRequest` 回 `{}`；備註有值時回 `{note}` 且已去前後空白
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_4_E_2]"
```
```gherkin
# AT-964-5-1
# 對應 AC: AC-964-5（W-S5 (a)）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiSchedulePanel.test.tsx -t AT_964_5_1
Scenario: （FE）`overdue` 為真：警示文案逐字含主機現查指令
  Given `sched()` 的 `overdue` 為 true、`lastSkip` 為 null
  When 渲染橫幅與面板
  Then 兩處各有一個醒目警示，文字含 `逾期未巡邏：請在主機執行 python tools/selfimproving.py sched show`；警示元素帶警示角色（role alert 或等價）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_5_1]"
```
```gherkin
# AT-964-5-2
# 對應 AC: AC-964-5（W-S5 (b)；NFR-SC-2）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiSchedulePanel.test.tsx -t AT_964_5_2
Scenario: （FE）`overdue` 為 null 或缺席顯示量不到與原因；為 false 不顯示警示
  Given 三份 `sched()`：`overdue` 為 null、`overdue` 缺席、`overdue` 為 false
  When 各渲染
  Then 前兩者逾期欄顯示 `量不到` 並註明事件帳本不在場之類的原因、不含沒有逾期字樣；第三者逾期欄顯示否且無警示元素
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_5_2]"
```
```gherkin
# AT-964-5-3
# 對應 AC: AC-964-5（W-S5 (d)）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiSchedulePanel.test.tsx -t AT_964_5_3
Scenario: （FE）`lastSkip` 非 null：顯示時間、原因、細節；顯示略過而非逾期
  Given `sched()` 的 `lastSkip` 為 `{at, reason: blackout, detail: d}`、`overdue` 為 false
  When 渲染
  Then 略過區顯示 at、`blackout` 與 `d`；無逾期警示；七個合法 reason 值（disabled、blackout、quota-band、other-driver、dirty-tree、run-open、spawn-failed）逐一代入皆原樣顯示
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_5_3]"
```
```gherkin
# AT-964-5-E-1
# 對應 AC: AC-964-5（W-S5 (c)；Architecture §12.1 L-SI-2）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_964_5_E_1
Scenario: （FE）逾期三態乘略過兩態的矩陣：無誤報，文案不含任務已停用字樣
  Given `overdue` 取 true、false、null、缺席四值，`lastSkip` 取 null 與非 null 兩值，共八格
  When 呼叫 `scheduleFields` 並取警示與狀態文字
  Then 只有 `overdue` 為 true 的兩格有逾期警示（不因 lastSkip 而抑制或新增）；null 與缺席的兩格為量不到；任一格的任何文案都不含 `任務已停用` 與 `任務已壞`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_5_E_1]"
```
```gherkin
# AT-964-6-1
# 對應 AC: AC-964-6（W-S6 (a)；根層 AC-SI-37-4）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiSchedulePanel.test.tsx -t AT_964_6_1
Scenario: （FE）Viewer 與 Operator：零控件、零 POST、唯讀欄位組仍顯示
  Given 以 `VIEWER_UI` 與 `OPERATOR_UI` 各渲染含 `schedule` 的頁面；fetch 替身記錄所有請求
  When 檢視面板
  Then 兩種角色皆查無啟用開關、週期輸入、立即啟動鈕；排程欄位組仍顯示；任何互動後 POST 請求數為 0
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_6_1]"
```
```gherkin
# AT-964-6-2
# 對應 AC: AC-964-6（W-S6 (b)）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_6_2
Scenario: （FE）名單外 ADMIN 的 403 `si_write_forbidden` 逐字顯示且不關窗
  Given fetch 替身對兩個新 POST 回 403 `si_write_forbidden`，`message` 為夾具字串
  When 在設定對話框與立即啟動對話框各送出一次
  Then 兩者皆逐字顯示 reason 與 message、對話框不關、送出鈕恢復
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_6_2]"
```
```gherkin
# AT-964-6-3
# 對應 AC: AC-964-6（W-S6 (c)；D-CS-2）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_6_3
Scenario: （FE）503 `si_write_disabled` 與 503 `si_unavailable` 的 cause 與 detail 逐字顯示
  Given fetch 替身回 503 `si_write_disabled`（`details.cause` 為 audit_key_unset）與 503 `si_unavailable`（`details.cause` 為 schedule_bounds_unavailable、`details.detail` 為夾具字串）
  When 各送出一次
  Then 畫面逐字顯示 reason、cause 與 detail；不把 `schedule_bounds_unavailable` 改寫成其他文字或隱藏；對話框不關
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_6_3]"
```
```gherkin
# AT-964-6-4
# 對應 AC: AC-964-6（W-S6 (c)）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiScheduleDialog.test.tsx -t AT_964_6_4
Scenario: （FE）422 `invalid_request` 的 violations 逐項顯示
  Given fetch 替身回 422 `invalid_request`，`details.violations` 為兩項 `{field: periodMinutes, message: m1}`、`{field: reason, message: m2}`
  When 送出
  Then 畫面逐項顯示欄名與訊息（m1、m2 逐字）；對話框不關；表單內容保留
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_6_4]"
```
```gherkin
# AT-964-6-E-1
# 對應 AC: AC-964-6（W-S6 (d)；W-S2 (b)；NFR-SC-4）
# 測試類型: Unit；自動化工具: vitest 檔案掃描（jsdom；hermetic）；判定指令: npx vitest run components/domain/si/si.static.test.ts -t AT_964_6_E_1
Scenario: （FE）靜態：新元件不直接 fetch、不含 PUT 等字樣、寫入 hook 恰為各自一個、界值零常數
  Given 新增與修改的元件原始碼（`SiSchedulePanel.tsx`、`SiScheduleDialog.tsx`、`SiRunRequestDialog.tsx` 或其合一形）與 `lib/domain/si.ts`
  When 以掃描判準檢查，並對注入副本（加 fetch、加 PUT 字樣、加第二個寫入 hook、加字面 10080 常數）自證
  Then 真檔：無直接 `fetch(`、無 PUT／PATCH／DELETE 字樣；設定對話框 import 的寫入 hook 恰為 `usePostSiScheduleSet`、立即啟動對話框恰為 `usePostSiRunRequest`；`lib/domain/si.ts` 與元件內無出現 60 與 10080 與 1440 作為界或預設週期的數值常數（出現於換算函式的 60 與 1440 為換算因子，由白名單具名放行）；四個注入副本各被判出
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_6_E_1]"
```
```gherkin
# AT-964-6-E-2
# 對應 AC: AC-964-6（W-S6 (d)；NFR-SC-8）
# 測試類型: Unit；自動化工具: vitest 檔案掃描（jsdom；hermetic）；判定指令: npx vitest run components/domain/si/si.static.test.ts -t AT_964_6_E_2
Scenario: （FE）靜態：不使用危險 HTML 注入、不以瀏覽器儲存另存界值或草稿
  Given 同 AT-964-6-E-1 的原始碼集合
  When 掃描並對注入副本自證
  Then 真檔無 `dangerouslySetInnerHTML`、無 `localStorage`、`sessionStorage`、`indexedDB` 字樣；兩個注入副本（加危險 HTML、加 localStorage 寫入界值）各被判出
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_6_E_2]"
```
```gherkin
# AT-964-10-1
# 對應 AC: AC-964-10（W-S10 (a)；Console PRD §0.10 D-UX-2）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/help/content.test.ts -t AT_964_10_1
Scenario: （FE）每頁說明含排程步驟與欄位字樣，三道雙向鎖與可讀性鎖綠
  Given `lib/help/self-improving.ts` 的 self-improving 頁說明與畫面字樣來源（`sourceFiles`）
  When 以既有的三道雙向鎖與可讀性鎖（`content.test.ts`、`pageFacts.test.ts`、`readability.test.ts`、`lint.test.ts`）檢查，並檢查新增字樣
  Then 說明含啟用排程、改週期、立即啟動一次、待入帳、逾期各一個步驟或名詞解釋；欄位名逐字取自畫面字樣（`自動演化排程`、`立即啟動一次演化`、`待入帳`、`逾期未巡邏` 等）；可讀性分數在國高中程度門檻內；四個既有檢查檔皆綠
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_10_1]"
```
```gherkin
# AT-964-10-2
# 對應 AC: AC-964-10（W-S10 (b)；契約 §6）
# 測試類型: Contract；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/api/si.endpoints.test.ts -t AT_964_10_2
Scenario: （FE）既有釘選的新預期值：端點數、已知鍵、寫入 kind 值域與標籤、`SI_REASONS` 鍵集合不變
  Given `lib/api/endpoints.ts`、`lib/domain/si.ts` 的匯出
  When 讀端點清單、`SI_STATUS_KNOWN_KEYS`、`SiWriteKind` 值域、`SI_WRITE_KIND_LABELS`、`SI_REASONS`
  Then 端點清單含 `postSiScheduleSet`（路徑 `/api/v1/si/schedule/set`）與 `postSiRunRequest`（路徑 `/api/v1/si/runs/request`），總數等於修改前現值加 2（修改前現值於實作輪現查並寫入斷言，不寫死於本檔）；已知鍵含 `schedule`；`SiWriteKind` 為五值；標籤五個皆有；`SI_REASONS` 鍵集合與順序與修改前逐位相同（本鍵無新 reason）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_10_2]"
```
```gherkin
# AT-964-10-3
# 對應 AC: AC-964-10（W-S10 (c)；Architecture §12.1）
# 測試類型: Unit；自動化工具: vitest 檔案掃描（jsdom；hermetic）；判定指令: npx vitest run components/domain/si/si.static.test.ts -t AT_964_10_3
Scenario: （FE）文件掃描：Architecture 去規劃註、契約升 v1.0、兩條已知限制仍在
  Given `AgentConsole/docs/02_architecture/Architecture.md` 的 §5.6、§10.3、§12.1 與 `API_Contract_SelfImproving_P2c.md` 的版本沿革（相對 monorepo 根讀檔）
  When 掃描
  Then §5.6 與 §10.3 的排程相關小節不再含 `P4 規劃` 與 `規劃，實作輪落地後去註` 字樣；契約版本沿革含 v1.0 一列且首行版本非 v0.1；§12.1 的 L-SI-1 與 L-SI-2 兩列仍在且字面未被刪；缺任一項即紅
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_10_3]"
```
```gherkin
# AT-964-10-E-1
# 對應 AC: AC-964-10（W-S10 (b)；NFR-SC-5）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_964_10_E_1
Scenario: （FE）既有純函式的行為回歸表：三種舊 kind 的指令字串、對帳面板函式、`SI_REASONS` 順序不變
  Given 修改前以同一組輸入錄下的期望表（內嵌於測試）：三個舊 kind 的 `ingestCommands`、`pendingWrites`、`supersededWrites`、`decideKindLabel`、`pendingDecision`、`SI_REASONS` 的鍵與順序
  When 逐項呼叫
  Then 全部與期望表逐位相同；`writeItem` 對既有呼叫的結果逐位元組相同（新增 kind 值不影響舊呼叫的預設）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_10_E_1]"
```

**B. backend（BE）：兩個 POST、Flyway、OpenAPI、ArchUnit、對帳**

```gherkin
# AT-964-7-1
# 對應 AC: AC-964-7（W-S7 (e)(f)；NFR-SC-8）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiScheduleWriteApiIT.AT_964_7_1*"（cwd＝AgentConsole/backend）
Scenario: （BE）`sched-set` 的 201、收據鍵集合、表內新列、迷你 Bridge 收到的外層與 body 鍵序與簽章
  Given `ADMIN`；`MINI.status` 設 `periodMin` 60、`periodMax` 10080；`SEAM` 排入一個 ref；請求本文 `{enabled: true, periodMinutes: 120, reason: 一行}`
  When `POST /api/v1/si/schedule/set`
  Then 201；`data` 鍵集合恰為 `auditRef`、`kind`、`subject`、`time`、`keyId`（`kind` 為 sched-set、`subject` 為 null、`time` 為秒精度 `±HH:MM` 且不含 Z）；無 `body`、`mac`；表內恰新增一列：`kind` 為 sched-set、`subject_id` 與 `digest` 為 NULL、`user` 為 admin、`role` 為 ADMIN；`MINI.si.writes` 收到一筆落檔本文：外層恰七鍵且 `subject` 為 null，body 鍵序依次為 `schema_rev`、`audit_ref`、`kind`、`user`、`role`、`time`、`enabled`、`period_minutes`、`reason`；以測試金鑰重算 HMAC 等於外層 `mac`；回應、日誌捕捉與 `MINI` 記錄皆不含金鑰與權杖值
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_1]"
```
```gherkin
# AT-964-7-2
# 對應 AC: AC-964-7（W-S7 (e)）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiScheduleWriteApiIT.AT_964_7_2*"（cwd＝AgentConsole/backend）
Scenario: （BE）`run-request` 的 201：空物件與含備註兩種本文
  Given `ADMIN`；`SEAM` 排入兩個 ref；兩份請求：`{}` 與 `{note: 一行}`
  When 各 `POST /api/v1/si/runs/request`
  Then 兩者皆 201、`kind` 為 run-request、`subject` 為 null；表內各新增一列（`subject_id`、`digest` 為 NULL）；`MINI` 收到的 body 鍵序為共通鍵之後接 `note`（第一份無 `note` 鍵）；本路徑**不呼叫** `GET /si/status`（`MINI` 的 status 請求數為 0，無序 5′）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_2]"
```
```gherkin
# AT-964-7-3
# 對應 AC: AC-964-7（W-S7 (c)；D-CS-6）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiScheduleWriteApiIT.AT_964_7_3*"（cwd＝AgentConsole/backend）
Scenario: （BE）停用方向帶界內週期仍 201，body 的 `enabled` 為 false
  Given `ADMIN`；`MINI.status` 設界；請求 `{enabled: false, periodMinutes: 1440}`
  When `POST /api/v1/si/schedule/set`
  Then 201；落檔 body 含 `enabled` 為 false 與 `period_minutes` 為 1440；`MINI` 的 status 請求數為 1（停用方向同樣經序 5′）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_3]"
```
```gherkin
# AT-964-7-4
# 對應 AC: AC-964-7（W-S7 (c)；NFR-SC-4）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiScheduleWriteApiIT.AT_964_7_4*"（cwd＝AgentConsole/backend）
Scenario: （BE）序 5′ 界檢查：端點 201、端點外 422 且訊息取自當下界、界改變後隨之改變
  Given `ADMIN`；`MINI.status` 先設界 `[lo, hi]`（取 60 與 10080），之後改設 `[lo2, hi2]`（取 30 與 120）
  When 依序以 `periodMinutes` 為 `lo`、`hi`、`lo-1`、`hi+1` 送出；改界後再以 100 與 121 送出
  Then `lo` 與 `hi` 為 201；`lo-1` 與 `hi+1` 為 422、`reason` 為 `invalid_request`、`details.violations` 含 `{field: periodMinutes, message}` 且 message 含當下界的兩個數字；改界後 100 為 201、121 為 422 且 message 含新界；422 的請求零副作用（表內列數、`MINI.si.writes`、`refs` 不變）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_4]"
```
```gherkin
# AT-964-7-5
# 對應 AC: AC-964-7（W-S7 (g)；D-CS-5）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiScheduleWriteApiIT.AT_964_7_5*"（cwd＝AgentConsole/backend）
Scenario: （BE）不走重送閘：同一請求連送各得 201 與不同 `auditRef`，無 409 重送 reason
  Given `ADMIN`；`SEAM` 排入四個不同 ref；同一份 `sched-set` 請求與同一份 `run-request` 請求
  When 各連送兩次
  Then 四次皆 201；每個端點兩次的 `auditRef` 互異；表內共新增四列；沒有任何回應的 `reason` 為 `si_decision_duplicate`；兩端點的 OpenAPI 說明與回應碼表不含該 reason（`ErrorReasons` 全域表仍含它——`decide` 在用；D-CS-16）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_5]"
```
```gherkin
# AT-964-7-6
# 對應 AC: AC-964-7（W-S7 (i)；D-CS-1）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.infrastructure.persistence.SiConsoleWritesMigrationIT.AT_964_7_6*"（cwd＝AgentConsole/backend）
Scenario: （BE）Flyway 新版本：版本現查加一、CHECK 實名現查、五值可寫、第六值被拒、舊列不受影響
  Given 測試啟動後的 PG（Flyway 已套用全部遷移）；斷言所需的版本資訊一律現查：讀 `db/migration/` 目錄的最大版本與 `flyway_schema_history` 的已套用版本；以 `pg_constraint` 查 `console.si_console_writes` 上 `kind` 的 CHECK 約束實名與定義
  When 檢查遷移與約束，並對表以各 kind 值做 INSERT
  Then 目錄的遷移版本序列嚴格遞增且無缺號，新增檔的版本恰為新增前最大版本加 1（以 `flyway_schema_history` 中該檔之前的最大版本現查，不寫死數字）；已套用版本集合等於目錄版本集合；`kind` 的 CHECK 只有一個、定義含五值 `decide`、`obs-add`、`obs-close`、`sched-set`、`run-request`；五值皆可 INSERT（`subject_id`、`digest` 為 NULL 亦可）、第六個值（例 `bogus`）被 CHECK 拒絕；遷移前就存在的三種列內容不變；對既有列改 `kind` 仍被 trigger 拒絕
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_6]"
```
```gherkin
# AT-964-7-7
# 對應 AC: AC-964-7（W-S7 (j)；契約 §1.1）
# 測試類型: Contract；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.infrastructure.config.OpenApiIT.AT_964_7_7*"（cwd＝AgentConsole/backend）
Scenario: （BE）OpenAPI：兩 operationId、路徑集合與操作總數、兩端點的狀態碼集合與說明
  Given 啟動後的 `/v3/api-docs`
  When 讀路徑與操作
  Then 含 `POST /api/v1/si/schedule/set`（operationId `postSiScheduleSet`）與 `POST /api/v1/si/runs/request`（operationId `postSiRunRequest`）；兩者的回應碼集合含 201、401、403、422、502、503、504、409（`si_audit_exists`）；路徑與操作總數等於修改前現值加 2（修改前現值於實作輪現查並寫入斷言）；既有 SI 路徑的方法與狀態碼集合不變；兩端點的 503 說明提及 `schedule_bounds_unavailable`；`SiWriteKind` 全等斷言為五值
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_7]"
```
```gherkin
# AT-964-7-8
# 對應 AC: AC-964-7（W-S7 (k)；契約 §4.1）
# 測試類型: Unit；自動化工具: JUnit 5（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.dto.SiKeyNamesTest.AT_964_7_8*"（cwd＝AgentConsole/backend）
Scenario: （BE）`status.schedule` 經 `SiKeyNames` 的深層欄名對映與透傳規則
  Given 一份 snake_case 的 `status` 物件，其 `schedule` 含根層 R158 的 12 鍵（`last_set` 與 `last_skip` 為物件）及一個未知鍵 `future_key`
  When 以 `SiKeyNames` 轉出
  Then 鍵依序為 `enabled`、`periodMinutes`、`periodMin`、`periodMax`、`heartbeatMinutes`、`lastSet`、`cellStart`、`cellEnd`、`ranThisCell`、`lastSkip`、`overdue`、`armed`；`lastSet` 內為 `at`、`by`、`carrier`、`lastSkip` 內為 `at`、`reason`、`detail`（內層鍵不變）；未知鍵 `future_key` 以既有規則轉為 camelCase 並透傳；缺鍵不補成 null、null 值不丟失
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_8]"
```
```gherkin
# AT-964-7-9
# 對應 AC: AC-964-7（W-S7 (j)）
# 測試類型: Unit；自動化工具: JUnit 5 + ArchUnit 與原始碼掃描（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.architecture.SiReadOnlyArchTest.AT_964_7_9*"（cwd＝AgentConsole/backend）
Scenario: （BE）ArchUnit：兩新 mapping 不帶 method、唯一存取該表的類別與 DML 鎖不變
  Given `SiController` 與寫入埠、對帳埠的現行釘選
  When 執行擴充後的鎖
  Then 兩個新 handler 以不帶 `method` 的 mapping 宣告（沿既有 `@RequestMapping` 體例）；唯一存取 `si_console_writes` 的類別集合不變；DML 的三條鎖不變（無 UPDATE、DELETE 之外的新寫入形態；刪列只在補償路徑）；方法集合釘選同步為新增兩個 handler 與其用例方法
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_9]"
```
```gherkin
# AT-964-7-E-1
# 對應 AC: AC-964-7（W-S7 (a)；NFR-SC-3）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiScheduleWriteApiIT.AT_964_7_E_1*"（cwd＝AgentConsole/backend）
Scenario: （BE）閘門序逐級：401、403 兩種、503 兩種 cause，每級零副作用
  Given 兩端點各一份合法請求；依序構造：無 JWT；Viewer；Operator；名單外 ADMIN；金鑰環未設；Bridge 權杖未設；以及同時多重違規的組合（Viewer 且輸入違規、名單外 ADMIN 且金鑰未設、金鑰未設且輸入違規）
  When 對兩端點各送出
  Then 依序 401、403 `ACCESS_DENIED`、403 `ACCESS_DENIED`、403 `si_write_forbidden`、503 `si_write_disabled` 且 `details.cause` 為 `audit_key_unset`、503 `si_write_disabled` 且 `details.cause` 為 `bridge_token_unset`；組合情境取序較前者；每級之前後表內列數、`MINI.si.writes`、`refs` 取用次數、`MINI` 的 status 請求數皆不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_E_1]"
```
```gherkin
# AT-964-7-E-2
# 對應 AC: AC-964-7（W-S7 (b)；D-CS-4；根層 R141 (c)）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiScheduleWriteApiIT.AT_964_7_E_2*"（cwd＝AgentConsole/backend）
Scenario: （BE）序 5 輸入閘：全部違規一次回報，欄位表驅動並與根層字串規則同表
  Given 表驅動的違規清單：`enabled` 缺、為字串 true、為數字 1；`periodMinutes` 缺、小數 90.5、字串 120、負數、0、布林 true；`reason` 與 `note` 各取 121 個 U+4E2D、換行、CR、U+0000、U+001F、U+007F、孤立代理字元、空字串、全空白；放行對照 120 個 U+1F600、`a|b`；並含一份同時違規四處的請求
  When 逐項送出（`sched-set` 與 `run-request` 各自適用的欄位）
  Then 每個違規請求 422、`reason` 為 `invalid_request`、`details.violations` 含對應 `{field, message}`（欄名 camelCase）；同時違規四處的請求一次回報四項；放行對照 201；`reason` 與 `note` 的放行與拒收集合與根層 TCS 的 R141 (c) 逐項一致（本表即該表的 Java 端表驅動副本，補充平面字元以 code point 計）；422 前後零副作用
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_E_2]"
```
```gherkin
# AT-964-7-E-3
# 對應 AC: AC-964-7（W-S7 (d)；D-CS-2；NFR-SC-3、NFR-SC-4）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiScheduleWriteApiIT.AT_964_7_E_3*"（cwd＝AgentConsole/backend）
Scenario: （BE）界取得失敗 503 `schedule_bounds_unavailable`、status 失敗沿 GET 對映、不用快取值
  Given `MINI.status` 依序設為：`schedule` 鍵缺席、`period_min` 缺席、`period_max` 缺席、`period_min` 為字串、`period_min` 大於 `period_max`；另設 `GET status` 本身失敗三種：Bridge 不可達、逾時、回 503 `si_unavailable`（原因 `schema_rev_mismatch` 類夾具）；另一組連續兩請求：第一個 status 正常回界、第二個 status 失敗
  When 對 `sched-set` 送出合法請求（`run-request` 不經序 5′，另送一次作對照）
  Then 前五者 503、`reason` 為 `si_unavailable`、`details.cause` 為 `schedule_bounds_unavailable`、`details.detail` 指出缺哪個鍵或何種不合；status 失敗三者的狀態碼與 reason 與 `GET /api/v1/si/status` 在同樣失敗下的回應逐項相同（502、504、503 原因逐字轉出）；連續兩請求的第二個為 503（不沿用第一個取得的界）；全部零副作用（無列、無 Bridge 落檔、`refs` 不變）；`run-request` 對照仍 201
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_E_3]"
```
```gherkin
# AT-964-7-E-4
# 對應 AC: AC-964-7（W-S7 (e)；P2b W11）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiScheduleWriteApiIT.AT_964_7_E_4*"（cwd＝AgentConsole/backend）
Scenario: （BE）補償與結果不明：Bridge 非 2xx 補償刪列、逾時保留列、原因逐字轉出
  Given `ADMIN`；`MINI` 依序被設為回 422 `invalid_request`、409 `si_audit_exists`、503 `si_unavailable`、503 `si_write_disabled`、403 `si_write_forbidden`，以及連線逾時（結果不明）
  When 對兩端點各送出合法請求
  Then 前五者的回應狀態碼與 reason 逐字轉出 Bridge 的原因（`BRIDGE_REJECTED` 的 422 沿 P2b 對映），表內該次新增的列被補償刪除（列數回到送出前）；逾時情境回 504，且該列**保留**（結果不明）；`refs` 每次恰取用一次
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_E_4]"
```
```gherkin
# AT-964-7-E-5
# 對應 AC: AC-964-7（W-S7 (h)）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiScheduleWriteApiIT.AT_964_7_E_5*"（cwd＝AgentConsole/backend）
Scenario: （BE）其餘方法：PUT、PATCH、DELETE 的 403 與 405，GET 的 405
  Given 兩個新路徑；三種角色 Viewer、Operator、ADMIN
  When 各以 PUT、PATCH、DELETE、GET 呼叫
  Then PUT、PATCH、DELETE：Viewer 為 403、Operator 與 ADMIN 為 405；GET：無 token 為 401、已登入角色（Viewer、Operator、ADMIN）一律 405（D-CS-14：`SecurityConfig` 對 `GET /api/v1/**` 放行 VIEWER 以上且兩路徑無 GET 對映，原寫 Viewer／Operator 403 為規格稿推定）；所有情境零副作用
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_7_E_5]"
```
```gherkin
# AT-964-9-1
# 對應 AC: AC-964-9（W-S9 (a)(d)；D-CS-3；根層 R141 (e)）
# 測試類型: Unit；自動化工具: JUnit 5（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiAuditSignerTest.AT_964_9_1*"（cwd＝AgentConsole/backend）
Scenario: （BE）向量 V5～V8 的 Java 端：body 鍵序與簽章，值由實作輪產出並入表
  Given 四個固定輸入（V5 sched-set 啟用含 reason、V6 sched-set 停用不含 reason、V7 run-request 含 note、V8 run-request 不含 note；固定時鐘、金鑰 K0、帳號 admin、固定 auditRef）
  When 以 `SiAuditSigner` 產 body 字串並簽章
  Then body 字串的鍵序為共通鍵之後依書寫序接專屬鍵（選用鍵缺席則略過）；簽章等於向量表內該列的預期 mac（預期值由實作輪以 Java 序列化器產出，經根層 `consoleaudit.py` 驗簽收下後入表，**本檔不預填數值**）；Python 端向量表的四列與 Java 端逐字相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_9_1]"
```
```gherkin
# AT-964-9-2
# 對應 AC: AC-964-9（W-S9 (b)）
# 測試類型: Unit；自動化工具: JUnit 5（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.application.service.SiAuditSignerTest.AT_964_9_2*"（cwd＝AgentConsole/backend）
Scenario: （BE）序列化器在固定時鐘與金鑰下逐位元組重現黃金檔 G6～G9
  Given 位於 `backend/src/test/resources/si/audit/` 的 G6、G7、G8、G9（對映 V5、V6、V7、V8）
  When 以相同輸入重新產生整個稽核檔位元組
  Then 四檔逐位元組相同；位元組為 UTF-8 無 BOM、緊湊 JSON、外層恰七鍵且 `subject` 為 null；檔案的 SHA-256 等於外層與入帳端使用的 `audit_sha256` 對象
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_9_2]"
```
```gherkin
# AT-964-9-4
# 對應 AC: AC-964-9（W-S9 (e)；契約 §4.2）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_964_9_4*"（cwd＝AgentConsole/backend）
Scenario: （BE）`console-writes`：兩新 kind 的列、其餘欄位恆 null、`ingested` 判準
  Given 表內植入四列：sched-set（甲）、sched-set（乙）、run-request（丙）、run-request（丁）；事件帳本夾具含：帶甲 `audit_ref` 的 `sched.set`、帶丙 `audit_ref` 的 `run.open`、帶丁 `audit_ref` 的 `sched.skip`，乙無對應事件
  When `GET /api/v1/si/console-writes`
  Then 四列的 `kind` 值域為 sched-set 與 run-request；四列的 `subjectId`、`digest`、`dkind`、`supersededBy` 皆為 null；`ingested` 甲為 true、乙為 false、丙為 true、丁為 true；`items[]` 鍵集合仍為十一鍵；既有三 kind 的列的判準與值不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_9_4]"
```
```gherkin
# AT-964-9-5
# 對應 AC: AC-964-9（W-S9 (e)）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_964_9_5*"（cwd＝AgentConsole/backend）
Scenario: （BE）`orphans[]` 的新 kind 映射、排序與去重
  Given 事件帳本夾具含 `carrier` 為 console 且帶 `audit_ref` 的 `sched.set`（兩筆同 `audit_ref`）、`run.open`、`sched.skip`，及一筆 `carrier` 非 console 的 `sched.set`；表內皆無對應 `audit_ref`
  When `GET /api/v1/si/console-writes`
  Then `orphans[]` 含 `{auditRef, kind: sched-set, subject: null}`（去重為一筆）、`{auditRef, kind: run-request, subject: null}` 兩筆（來自 `run.open` 與 `sched.skip`）；`carrier` 非 console 者不入列；排序與去重規則同 P2b §4（既有三 kind 的 orphan 判準不變）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_9_5]"
```
```gherkin
# AT-964-9-E-2
# 對應 AC: AC-964-9（W-S9 (e)；NFR-SC-2）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_964_9_E_2*"（cwd＝AgentConsole/backend）
Scenario: （BE）對帳量不到時兩新 kind 的 `ingested` 為 null
  Given 表內有 sched-set 與 run-request 各一列；對帳來源 NOT-EVALUABLE（事件帳本不可讀）與 `scan_cap_exceeded` 兩種情境
  When `GET /api/v1/si/console-writes`
  Then 兩情境下兩列的 `ingested` 皆為 null、`reconcile.status` 為 NOT-EVALUABLE（`scan_cap_exceeded` 時帶其 reason）；不把任何一列判成已入帳或待入帳
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_9_E_2]"
```
```gherkin
# AT-964-9-E-3
# 對應 AC: AC-964-9（W-S9 (e)；根層 R146 (b)）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_964_9_E_3*"（cwd＝AgentConsole/backend）
Scenario: （BE）`run-request` 以 `sched.skip` 入帳亦為已入帳
  Given 表內一列 run-request；事件帳本只有帶該 `audit_ref` 的 `sched.skip`（`reason` 為 run-open、`carrier` 為 console），無 `run.open`
  When `GET /api/v1/si/console-writes`
  Then 該列 `ingested` 為 true、不出現在待入帳；`orphans[]` 不含它
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_9_E_3]"
```

**C. Bridge（BR）：兩個落檔 POST、靜態鎖、黃金檔與真 CLI**

```gherkin
# AT-964-8-1
# 對應 AC: AC-964-8（W-S8；P2b §2.1）
# 測試類型: Integration；自動化工具: pytest + FastAPI TestClient + tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_964_8_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （BR）`POST /si/schedule:set`：201、原樣位元組落檔、獨佔建立
  Given 權杖與稽核目錄已設；一份合法外層七鍵（`kind` 為 sched-set、`subject` 為 null）的請求位元組 B
  When 以正確 `X-Bridge-Token` POST
  Then 201，本文為 `audit_ref` 等於外層值、`stored` 為 true 的兩鍵物件；稽核目錄內恰多一個檔 `<audit_ref>.json`，位元組逐位等於 B；以獨佔建立（同名再 POST 得 409，檔內容不變）；回應不含絕對路徑
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_8_1]"
```
```gherkin
# AT-964-8-2
# 對應 AC: AC-964-8（W-S8）
# 測試類型: Integration；自動化工具: pytest + FastAPI TestClient + tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_964_8_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （BR）`POST /si/runs:request`：201、原樣位元組落檔
  Given 同 AT-964-8-1，`kind` 為 run-request
  When 以正確權杖 POST
  Then 201 與原樣落檔同 AT-964-8-1；外層中的 `body` 字串不被解析、不被改寫（含不重排、不補鍵）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_8_2]"
```
```gherkin
# AT-964-8-3
# 對應 AC: AC-964-8（W-S8）
# 測試類型: Integration；自動化工具: pytest + FastAPI TestClient + tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_964_8_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （BR）外層七鍵與 kind 相符、subject 為 null 時接受
  Given 外層恰七鍵 `schema_rev`、`audit_ref`、`kind`、`subject`、`body`、`key_id`、`mac`
  When 兩個端點各以相符 kind 與 `subject` 為 null 送出
  Then 皆 201；外層缺任一鍵或多一鍵皆 422 `invalid_request`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_8_3]"
```
```gherkin
# AT-964-8-4
# 對應 AC: AC-964-8（W-S8；P2b §2.3 判準 1′～5′）
# 測試類型: Unit；自動化工具: pytest + AST 掃描（hermetic）；判定指令: python -m pytest tests/test_si_readonly_lock.py -k AT_964_8_4 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （BR）靜態鎖不變：組 argv 函式恰兩個、動詞白名單不變、寫入形態僅在稽核模組、兩新路由不呼叫 CLI
  Given `app/routers/si.py`、`app/si_audit.py`、`app/si_cli.py` 的原始碼與修改前的鎖
  When 執行擴充後的鎖並對注入副本自證
  Then 組 argv 的函式仍恰為 `export` 與 `obs-add --dry-run` 兩個；`si_cli.py` 的動詞白名單不變；寫入形態只出現在 `app/si_audit.py` 且路徑引數源自 `audit_dir` 參數；兩新路由只經 `_store_signed_audit`、無 `si_cli` 呼叫；路由總數等於修改前現值加 2（現查）；注入副本（在新路由加 argv 組裝、加寫檔呼叫）各被判出
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_8_4]"
```
```gherkin
# AT-964-8-5
# 對應 AC: AC-964-8（W-S8；檔名安全）
# 測試類型: Integration；自動化工具: pytest + tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_audit_filename_safety.py -k AT_964_8_5 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （BR）檔名安全：非 UUID 與路徑穿越字樣的 audit_ref 不落檔
  Given 兩個端點與外層 `audit_ref` 的變形：非 UUID 字串、含 `../`、含反斜線、含 NUL、大寫 UUID、空字串
  When 各 POST
  Then 非法者 422 `invalid_request` 且稽核目錄不新增任何檔、目錄外無任何新檔；合法小寫 UUID 對照組 201；兩個端點結果一致
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_8_5]"
```
```gherkin
# AT-964-8-E-1
# 對應 AC: AC-964-8（W-S8 (subject、kind)）
# 測試類型: Integration；自動化工具: pytest + FastAPI TestClient + tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_964_8_E_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （BR）subject 非 null 與 kind 不符：422 與 violations，不落檔
  Given 外層 `subject` 為字串、為空字串；外層 `kind` 為 decide、obs-add、另一端點的 kind
  When 兩端點各 POST
  Then 皆 422 `invalid_request`；`subject` 違規的 `details.violations` 含 `{field: subject, rule, message}`；kind 不符的 violations 指出 `kind`；稽核目錄不新增檔
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_8_E_1]"
```
```gherkin
# AT-964-8-E-2
# 對應 AC: AC-964-8（W-S8；P2b §2.1）
# 測試類型: Integration；自動化工具: pytest + FastAPI TestClient + tmp 稽核目錄（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_964_8_E_2 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （BR）權杖、大小、非 JSON、同名 409、落檔 I/O 失敗的逐級對映
  Given 兩端點；情境：權杖或稽核目錄未設；缺權杖與錯權杖；本文 65537 位元組；本文非單一 JSON 物件（陣列、字串、多物件）；同名檔已存在；稽核目錄唯讀（模擬 OSError）
  When 各 POST
  Then 依序 503 `si_write_disabled`、403 `si_write_forbidden`、422 `invalid_request`（`violations[0].rule` 為 `too_large`；P2b `_read_limited_body` 現行對映，主控現查 `engine-bridge/app/routers/si.py`：宣告或累計超過 `SI_WRITE_BODY_MAX_BYTES` 即 422 且不讀完）、422 `invalid_request`、409 `si_audit_exists`、503 `si_unavailable` 且 `cause` 為 audit_write_failed；先中者定案；除 409 外稽核目錄無新增檔
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_8_E_2]"
```
```gherkin
# AT-964-8-E-3
# 對應 AC: AC-964-8（W-S8）
# 測試類型: Integration；自動化工具: pytest + FastAPI TestClient（hermetic）；判定指令: python -m pytest tests/test_si_write_routes.py -k AT_964_8_E_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （BR）其餘方法 405
  Given 兩個新路徑
  When 以 GET、PUT、PATCH、DELETE 呼叫
  Then 皆 405；稽核目錄無任何變動
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_8_E_3]"
```
```gherkin
# AT-964-9-3
# 對應 AC: AC-964-9（W-S9 (b)(c)；D-CS-3；根層 AT-437-1-3 的另一側）
# 測試類型: Integration；自動化工具: pytest + 黃金檔 + 真根層 CLI 子行程（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_964_9_3 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （BR）黃金檔副本與 backend 產出逐位元組相同，且真 CLI 收下 G6～G9 rc 為 0
  Given `engine-bridge/tests/fixtures/si_audit/` 的 G6～G9（由 PKG-BE 產出、主控複製）；唯讀讀取 `backend/src/test/resources/si/audit/` 的同名檔；tmp 家目錄與 tmp 合成 repo；測試金鑰 K0 以環境變數餵入；**前置＝根層鍵已 RELEASE**
  When 比對兩處位元組；把 G6、G7 放入 `console_audit/` 後呼叫根層 `sched set --carrier console --audit-ref <ref>`；把 G8、G9 放入後呼叫 `run-open --trigger a --carrier console --audit-ref <ref> --coord console_audit/<ref>.json --by console`
  Then 兩處四檔逐位元組相同；四次 CLI 的 rc 皆為 0（釘收下、不釘任何數值）；事件帳本新增對應的 `sched.set`（兩筆）與 `run.open` 或 `sched.skip`（依當下是否有未關運轉）且帶各自的 `audit_ref` 與 `audit_sha256`；黃金檔缺失或 CLI 缺席時本 AT 為紅（不 skip）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_9_3]"
```
```gherkin
# AT-964-9-E-1
# 對應 AC: AC-964-9（W-S9 (a)(d)）
# 測試類型: Integration；自動化工具: pytest + 黃金檔 + 真根層 CLI 子行程（hermetic）；判定指令: python -m pytest tests/test_si_console_ingest.py -k AT_964_9_E_1 -q（cwd＝AgentConsole/engine-bridge）
Scenario: （BR）Python 端向量驗簽；body 鍵序對調的檔被真 CLI 以 MAC 不符拒收
  Given Python 端向量表（V5～V8，與 Java 端逐字相同）；一份把 G6 的 body 鍵序對調（不改簽章與外層）的變形檔
  When 以 Python 的 HMAC 驗向量；對變形檔呼叫 `sched set --carrier console`
  Then 四個向量的 HMAC 重算皆等於表內 mac；變形檔 rc 為 1、碼 `AUDIT-MAC-MISMATCH`、事件帳本不變、稽核檔仍在
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_9_E_1]"
```

**D. Playwright（PW）：ADMIN 三個動作各一**

```gherkin
# AT-964-2-4
# 對應 AC: AC-964-2（W-S2、W-S3；Playwright mock）
# 測試類型: E2E；自動化工具: Playwright（mock 模式，路由替身）；判定指令: npx playwright test tests/e2e/self-improving-schedule.mock.spec.ts -g AT_964_2_4
Scenario: （PW）ADMIN 啟用開關流程：開對話框、送出、顯示待入帳收據
  Given `E2E_MODE=standalone`；路由替身回 ADMIN 登入、`status`（`schedule.enabled` 為 false、界 60 至 10080、週期 1440）與 `POST /api/v1/si/schedule/set` 的 201
  When 開 `/self-improving`，於排程面板把開關切為啟用並確認送出
  Then 替身收到的本文為 `{enabled: true, periodMinutes: 1440}`；畫面出現 `稽核檔已落地，待入帳` 與 `python tools/selfimproving.py sched set --carrier console --audit-ref` 開頭的入帳指令；橫幅在重取 `status` 後仍以替身回應為準（不樂觀顯示已啟用）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_964_2_4]"
```

## 3. AT 完整清單

> 依測試類型與測試檔的閱讀索引（權威清單是 §1）。本節表格第一欄是測試檔、不是 AC ID。

### 3.1 backend（BE；20 個）

| 測試檔（`AgentConsole/backend/src/test/java/com/aisdlc/console/` 下） | AT ID |
|------------------------------------------------------------------------|-------|
| adapter/in/web/SiScheduleWriteApiIT.java（新；10 個） | AT-964-7-1～AT-964-7-5、AT-964-7-E-1～AT-964-7-E-5 |
| infrastructure/persistence/SiConsoleWritesMigrationIT.java（既有，新增方法） | AT-964-7-6 |
| infrastructure/config/OpenApiIT.java（既有，新增方法） | AT-964-7-7 |
| adapter/in/web/dto/SiKeyNamesTest.java（既有，新增方法） | AT-964-7-8 |
| architecture/SiReadOnlyArchTest.java（既有，新增方法） | AT-964-7-9 |
| application/service/SiAuditSignerTest.java（既有，新增方法） | AT-964-9-1、AT-964-9-2 |
| adapter/in/web/SiConsoleWritesReadApiIT.java（既有，新增方法） | AT-964-9-4、AT-964-9-5、AT-964-9-E-2、AT-964-9-E-3 |

### 3.2 Bridge（BR；10 個）

| 測試檔（`AgentConsole/engine-bridge/tests/` 下） | AT ID |
|---------------------------------------------------|-------|
| test_si_write_routes.py（既有，新增函式） | AT-964-8-1、AT-964-8-2、AT-964-8-3、AT-964-8-E-1、AT-964-8-E-2、AT-964-8-E-3 |
| test_si_readonly_lock.py（既有，新增函式） | AT-964-8-4 |
| test_si_audit_filename_safety.py（既有，新增函式） | AT-964-8-5 |
| test_si_console_ingest.py（既有，新增函式） | AT-964-9-3、AT-964-9-E-1 |

### 3.3 frontend（FE；36 個）與 Playwright（PW；3 個）

| 測試檔（`AgentConsole/frontend/` 下） | AT ID |
|----------------------------------------|-------|
| components/domain/si/SiSchedulePanel.test.tsx（新；7 個） | AT-964-1-1、AT-964-1-2、AT-964-1-E-3、AT-964-5-1、AT-964-5-2、AT-964-5-3、AT-964-6-1 |
| components/domain/si/SiScheduleDialog.test.tsx（新；11 個） | AT-964-2-2、AT-964-2-3、AT-964-2-E-1、AT-964-2-E-2、AT-964-3-1、AT-964-3-3、AT-964-3-E-1、AT-964-3-E-2、AT-964-6-2、AT-964-6-3、AT-964-6-4 |
| components/domain/si/SiRunRequestDialog.test.tsx（新；4 個） | AT-964-4-1、AT-964-4-2、AT-964-4-3、AT-964-4-E-1 |
| components/domain/si/SiView.test.tsx（既有，新增 it） | AT-964-1-3、AT-964-1-E-2 |
| components/domain/si/si.static.test.ts（既有，新增 it） | AT-964-6-E-1、AT-964-6-E-2、AT-964-10-3 |
| lib/domain/si.test.ts（既有，新增 it） | AT-964-1-E-1、AT-964-2-1、AT-964-3-2、AT-964-3-E-3、AT-964-4-E-2、AT-964-5-E-1、AT-964-10-E-1 |
| lib/help/content.test.ts（既有，新增 it） | AT-964-10-1 |
| lib/api/si.endpoints.test.ts（既有，新增 it） | AT-964-10-2 |
| tests/e2e/self-improving-schedule.mock.spec.ts（新；PW 3 個） | AT-964-2-4、AT-964-3-4、AT-964-4-4 |

**Contract 與 E2E 的歸類**：AT-964-7-7、AT-964-10-2 為 Contract 類；三個 PW 為 E2E 類；Docker 全棧為 V 系列、不入 AT（§6.2）。

## 4. 邊界與錯誤測試規格，與需同步的既有測試

邊界與錯誤情境以 `AT-<NNN>-<Y>-E-<n>` 命名並已列入 §1；下表是依場景類型的索引（第一欄為場景類型、不是 AC ID）。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|----------|
| 量不到（不顯示成零或綠） | AT-964-1-E-1、AT-964-1-E-2、AT-964-5-2、AT-964-2-E-2、AT-964-9-E-2 | 欄位缺席、null、型別不符、`schedule` 整鍵缺席、`overdue` 為 null、界取不到、對帳量不到 | `sched()` 變形、替身回應 | 量不到文案或 null，不是無、false、零 |
| 週期與字串邊界 | AT-964-2-E-1、AT-964-3-E-3、AT-964-4-E-2、AT-964-7-E-2、AT-964-7-4 | 端點值與端點外、小數、字串、布林、120 與 121 code point、補充平面字元、控制字元、全空白、豎線 | 表驅動輸入 | 前端先擋、backend 為權威、兩端與根層 R141 (c) 同表 |
| 閘門序與零副作用 | AT-964-7-E-1、AT-964-7-E-3、AT-964-7-E-4、AT-964-7-E-5 | 401、403 兩種、503 兩種、界取得失敗、補償與結果不明、其餘方法 | 角色、環境、替身 | 先中者定案；零副作用（逐項斷言列數、Bridge 落檔、ref 取用） |
| 錯誤逐字呈現 | AT-964-3-E-1、AT-964-6-2、AT-964-6-3、AT-964-6-4 | 409、502、504、網路錯誤、403、503、422 | fetch 替身 | 逐字顯示 reason、message、cause、detail、violations；不關窗 |
| 非 ADMIN 與靜態鎖 | AT-964-6-1、AT-964-6-E-1、AT-964-6-E-2、AT-964-8-4、AT-964-7-9 | 零控件零 POST、不直接 fetch、不另存界值、Bridge 不組 argv、ArchUnit | 角色渲染、原始碼掃描、注入副本 | 注入副本各被判出 |
| 防連點與軟停用 | AT-964-3-E-2、AT-964-4-2、AT-964-4-3、AT-964-4-E-1 | 連點只送一次、對帳快取有待入帳時停用、快取缺席與量不到不停用、不發新請求 | 快取與 fetch 計數 | 只讀快取；backend 無重送閘（AT-964-7-5） |
| 位元組權威與跨語言 | AT-964-9-1、AT-964-9-2、AT-964-9-3、AT-964-9-E-1、AT-964-8-1、AT-964-8-2 | 向量、黃金檔、真 CLI 收下、鍵序對調、Bridge 原樣落檔 | 黃金檔與固定時鐘 | 位元組逐位相同；MAC 不符被拒；**不預填數值** |
| 對帳新 kind | AT-964-9-4、AT-964-9-5、AT-964-9-E-3 | `ingested` 判準、`orphans` 映射、`sched.skip` 入帳 | 事件帳本夾具 | 與契約 §4.2 一致 |
| Flyway | AT-964-7-6 | 版本現查加一、CHECK 實名現查、五值與第六值 | `pg_constraint`、`flyway_schema_history` | 不寫死版本號與約束名 |
| 刻意不做 | （無 AT） | 真容器全棧、真機入帳、真 OS 任務、macOS、根層 CLI 內部（根層 TCS） | — | V 系列或 §7.2 登記，不以構造資料充當 |

### 4.1 需同步的既有測試（只改預期值；不弱化斷言；本表外既有函式因本鍵而紅者，開發 agent 以純文字回報、由主控裁決後補入本表）

| 包 | 既有測試（檔與函式或斷言） | 變更 |
|----|------------------------------|------|
| PKG-FE | `components/domain/si/SiView.test.tsx`：橫幅其他欄位區的斷言（`schedule` 不再列入其他欄位，AT-964-1-3 為其新案例）；寫入入口白名單斷言（新增排程面板的三個控件與兩個對話框入口，僅 ADMIN） | 預期值增列；既有案例不刪 |
| PKG-FE | 橫幅斷言：現無獨立 `SiStatusBanner.test.tsx`（SD 撰寫時現查；橫幅測試住 `SiView.test.tsx`），若實作輪新增獨立檔須同步並回報 | 現查 |
| PKG-FE | `lib/domain/si.test.ts`：`SI_STATUS_KNOWN_KEYS` 的釘選（加 `schedule`）、`SiWriteKind` 與 `SI_WRITE_KIND_LABELS` 的釘選（三值改五值）、`ingestCommands` 的列舉斷言（加兩 kind）；`SI_REASONS` 的鍵集合與順序釘選**不改** | 預期值增列 |
| PKG-FE | 對帳面板種類標籤的既有測試（`SiView.test.tsx` 內 `SiWritesPanel` 區）：種類標籤對照表加 `排程設定`、`立即啟動`；`writeItem` 夾具（`tests/helpers/si.tsx`）的 `kind` 型別放寬為五值，既有呼叫的結果逐位元組不變 | 預期值增列 |
| PKG-FE | `components/domain/si/si.static.test.ts`：`WRITE_HOOK` 名稱前綴判準與「對話框 import 的寫入 hook 恰為」的斷言對新增的兩個對話框擴充（`SiDecideDialog` 的既有斷言不變）；全樹掃描禁 `fetch(` 與 PUT、PATCH、DELETE 字樣對新元件同樣適用 | 擴充涵蓋 |
| PKG-FE | `lib/api/si.endpoints.test.ts`（與端點總數釘選）：新增 `postSiScheduleSet`、`postSiRunRequest` 兩條，總數釘選等於修改前現值加 2 | 預期值加 2（實作輪現查原值） |
| PKG-FE | `lib/help/content.test.ts`、`pageFacts.test.ts`、`readability.test.ts`、`lint.test.ts`（既有三道雙向鎖與可讀性鎖）：`self-improving` 頁說明增修後須仍綠；`lib/nav/registry.test.ts` 不改 | 說明由主控與 UI 同 commit 補 |
| PKG-BE | `SiConsoleWriteApiIT`（既有）：任何斷言 `SiWriteKind` 值域或列舉 kind 為三值的站點；既有四個 POST 的行為與 AT 不改 | 預期值增列 |
| PKG-BE | `SiWriteGatesTest`、`SiAuditSignerTest`（既有）：kind 列舉斷言與向量表（加 V5～V8）；既有向量 V1～V4 與黃金檔 G1～G5 的值不改 | 增列 |
| PKG-BE | `SiConsoleWritesMigrationIT`（既有）：CHECK 約束的斷言由三值改五值（AT-964-7-6 為新案例）；`SchemaMigrationIT`、`V5UpgradeMigrationIT`（既有）的遷移版本數斷言隨新版本更新（**只改預期值，且數字於實作輪現查、不寫死於本檔**） | 預期值更新 |
| PKG-BE | `OpenApiIT`（既有）：路徑與操作總數、各 SI 路徑方法與狀態碼集合的釘選加兩個新路徑；`SiReadOnlyArchTest`（既有）：寫入埠與用例的方法集合釘選、`@RequestMapping` 不帶 method 的掃描涵蓋兩新 handler | 預期值增列 |
| PKG-BE | `SiMirrorApiIT`（既有）：`AT_940_5_2` 會讀 `ErrorResponseDocumentation.java`、`ErrorReasons.java` 的原始碼——新增的兩端點說明文字不得含「唯一帶 reason」「唯一例外」字樣，`si_not_found`、`si_unavailable` 的常數字面格式不得改動；`status` 透傳的既有案例加 `schedule` 鍵 | 守住既有字樣鎖 |
| PKG-BE | `SiKeyNamesTest`、`BridgeHttpAdapterSiWriteTest`（既有）：深層對映表與兩個新 Bridge 呼叫（路徑 `/si/schedule:set`、`/si/runs:request`）的釘選 | 增列 |
| PKG-BE | `SiConsoleWritesReadApiIT`（既有）：`items[].kind` 值域與 `orphans` 判準的既有斷言（既有三 kind 不變） | 預期值增列 |
| PKG-BE（D-CS-19 追認；實作輪表外站點） | `IssueBridgeArchTest.AT_IC_07_6_1`（`AgentBridge` 的 `si` 方法 5→7、`SiController` POST 4→6；TCS-IssueCenter 勘誤四 4-2）；`BackupJobMigrationIT.snapshotOfExistingTables`（約束快照排除 `si_console_writes_kind_check`——V23 為宣告過的有意變動，其餘約束仍逐項比對）；`BackupJobMigrationIT`（3 處）、`IssuePriorityMigrationIT`、`ResearchSchemaMigrationIT`（3 處）的 Flyway 版本清單加 `"23"`；測試替身 `com/aisdlc/minibridge/MiniBridge.java`（`Si.status(Object)`、`Si.DROP`、`Si.scheduleWithBounds`、`Si.statusRequests()`）與 `MiniBridgeController.java`（`/si/schedule:set`、`/si/runs:request`）——§5.5 `MINI.status` 與計數所需 | 預期值更新／替身增列 |
| PKG-BR | `tests/test_si_readonly_lock.py`：路由總數與寫入路由清單釘選加兩個新路由；判準 1′～5′ 不改；`tests/test_si_write_routes.py`、`test_si_audit_filename_safety.py`：路由清單與檔名安全參數化表加兩個新路由；`tests/test_si_routes.py`、`test_si_cli.py`（唯讀 GET 與 CLI 白名單）預期零改 | 預期值增列；零改者以現查確認 |

## 5. 測試資料規格

### 5.1 常數與資料

- 測試資料不使用真帳本識別碼；稽核 `audit_ref` 於執行期組出小寫 UUID；`user` 一律 `admin`、`role` 為 `ADMIN`、`key_id` 為 8 碼 hex 夾具。
- **界夾具**：`BOUNDS`＝`periodMin` 60、`periodMax` 10080、`heartbeatMinutes` 15、預設 `periodMinutes` 1440；另一組 `BOUNDS2`＝30 至 120（AT-964-7-4、AT-964-2-2 用）。**測試的預期值一律由夾具設定值導出，不在斷言中另寫一份常數**（NFR-SC-4）。
- **字串規則向量表 M-X**（reason 與 note 共用；前端與 backend 各一份表驅動副本，與根層 TCS 的 R141 (c) 同表）：放行＝120 個 U+4E2D、120 個 U+1F600、`a|b`、前後有空白的 `  ok  `（前後空白去除後放行）；拒收＝121 個 U+4E2D、121 個 U+1F600、含 LF、含 CR、含 U+0000、含 U+001F、含 U+007F、孤立代理字元（backend）、全空白、TAB。**空值語意**：前端把未填或空字串視為未填、省略該鍵；backend 收到字串型的空字串或全空白＝422（有值不得全空白）。
- **黃金檔與向量**：G6～G9 對映 V5～V8（V5 sched-set 啟用含 reason、V6 sched-set 停用不含 reason、V7 run-request 含 note、V8 run-request 不含 note）；`Clock.fixed`、金鑰 K0、帳號 admin；位元組與 mac 值由實作輪產出，**本檔不預填**。**實作輪入表（D-CS-18；PKG-BE 產出、主控以根層 CLI 收下、2026-11-09）**：檔案住 `backend/src/test/resources/si/audit/`，副本住 `engine-bridge/tests/fixtures/si_audit/`（主控複製，逐位元組同）——G6 `sched-set-enable.json`（`audit_ref` a1000000-0000-4000-8000-000000000006、enabled true、period_minutes 120、reason「夾具啟用」；445 位元組，sha256 55cf567a…）、G7 `sched-set-disable.json`（…0007、false、1440、無 reason；419 位元組，7210a524…）、G8 `run-request-note.json`（…0008、note「夾具立即啟動」；413 位元組，59256ad4…）、G9 `run-request.json`（…0009、無 note；381 位元組，9977906f…）；`time` 皆 `2026-10-24T22:30:15+08:00`、`key_id` f076edf0。PKG-BR／PKG-FE 對同一組輸入一律引用這四檔。

### 5.5 backend 測試設施（沿 P2b TCS §5.4 與 DecideDedupe TCS §5.5；只增不改）

- `AbstractSiWriteIT` 沿用（`SEAM`、`MINI`、`ADMIN`、`writeRows()`）；新增 `MINI.status(scheduleJson)`：設定迷你 Bridge 的 `GET /si/status` 回應中 `items[0].schedule`（含「鍵缺席」「型別錯」的變形），並可設定該 GET 的失敗模式（不可達、逾時、503 與原因）；`MINI` 記錄 status 請求次數，供「零副作用」與「`run-request` 不取界」斷言。
- 事件帳本夾具（對帳）：`event(...)` 加 `sched.set`、`run.open`、`sched.skip` 三種帶 `audit_ref` 與 `carrier` 的建構（`carrier` 可設 console 或其他）。
- 每個測試前清表與重設夾具的既有 `@BeforeEach` 不變。

### 5.6 frontend 與 Playwright 測試設施（沿 P2b TCS §5.5；只增不改）

- `tests/helpers/si.tsx`：`statusItem({ schedule })`（`schedule` 缺省為不含該鍵，既有呼叫不變）、`sched(over)`（camelCase 的完整 `schedule`：`enabled` true、`periodMinutes` 1440、`periodMin` 60、`periodMax` 10080、`heartbeatMinutes` 15、`lastSet` `{at, by, carrier}`、`cellStart`、`cellEnd`、`ranThisCell` false、`lastSkip` null、`overdue` false、`armed` 為量不到字串；`over` 逐鍵覆寫，`DROP` 表示刪鍵）、`writeItem` 的 `kind` 放寬為五值（其餘預設值不變，既有呼叫的結果逐位元組相同）；`ADMIN_UI`、`VIEWER_UI`、`OPERATOR_UI` 沿既有角色渲染輔助。
- Playwright：`tests/e2e/self-improving-schedule.mock.spec.ts` 新檔，走既有 mock 體例（`tests/e2e/mockApi.ts` 與 `E2E_MODE=standalone`），登入、`status`、兩個 POST、`console-writes` 皆以路由替身回應；不連真後端。

### 5.7 hermetic 環境與允許變更的檔案集合

全部 AT 只用 Testcontainers 的 PG18、迷你 Bridge、FastAPI TestClient、jsdom、fetch 替身、Playwright 路由替身、tmp 目錄與（AT-964-9-3、AT-964-9-E-1）真根層 CLI 子行程（hermetic：tmp 家目錄、tmp 合成 repo、測試金鑰環境變數）；不連外網、不寫真帳本、不碰真 `~/.autosdd/`。測試結束必關迷你 Bridge 與回收資源。

| 區 | 允許新增或修改的路徑（相對 monorepo 根） |
|----|--------------------------------------------|
| PKG-BE 主程式 | `AgentConsole/backend/src/main/java/com/aisdlc/console/` 下與兩個 POST、`SiWriteKind`、稽核簽章、Bridge 呼叫、`SiKeyNames`、對帳讀面、`ErrorResponseDocumentation` 相關的類別（D1、D3；實作輪現查檔名）；`AgentConsole/backend/src/main/resources/db/migration/V<現查＋1>__*.sql`（新檔，D2） |
| PKG-BE 測試與黃金檔 | `AgentConsole/backend/src/test/java/com/aisdlc/console/` 下 §3.1 所列測試檔與 `support/AbstractSiWriteIT.java`；`AgentConsole/backend/src/test/resources/si/audit/`（G6～G9 與向量檔，D4）；測試替身 `AgentConsole/backend/src/test/java/com/aisdlc/minibridge/**`（§5.5 `MINI.status` 與兩新路由；D-CS-19） |
| PKG-BR | `AgentConsole/engine-bridge/app/routers/si.py`（改）；`AgentConsole/engine-bridge/tests/` 下 §3.2 所列測試檔與 `tests/fixtures/si_audit/`（G6～G9 副本，由主控自 PKG-BE 複製） |
| PKG-FE | `AgentConsole/frontend/components/domain/si/` 下 `SiSchedulePanel.tsx`、`SiScheduleDialog.tsx`、`SiRunRequestDialog.tsx`（或合一形）、`SiStatusBanner.tsx`、`SiWritesPanel.tsx`、`SiView.tsx`、`siParts.tsx` 與 §3.3 所列測試檔；`lib/domain/si.ts`、`lib/api/{endpoints,queries,types}.ts`、`lib/api/schema.d.ts`（重產）、`lib/api/si.endpoints.test.ts`、`lib/domain/si.test.ts`、`lib/help/content.test.ts`、`tests/helpers/si.tsx`、`tests/e2e/self-improving-schedule.mock.spec.ts` |
| 不屬開發 agent（主控代做） | `AgentConsole/docs/02_architecture/Architecture.md` §5.6、§10.3 去規劃註；契約 `API_Contract_SelfImproving_P2c.md` 升 v1.0；RTM 本地子表（預定 §2.14；DEF-200-576 體例）；SCG-4 報告；`AgentConsole/frontend/lib/help/self-improving.ts`（與 UI 同 commit）；黃金檔自 PKG-BE 複製到 PKG-BR；凍結上位的勘誤與 refreeze；黃金檔與向量的經根層 CLI 驗簽定稿 |
| 不得變更 | 根層 `tools/`、`.claude/`、`.github/`、`AgentConsole/docker-compose*.yml`（無新掛載）、既有 Flyway 檔（只准新增一個）、凍結檔與既有 TCS（上列勘誤除外）、`engine-bridge` 的 `si_cli.py`（argv 白名單不變）與 `app/si_audit.py` 的寫入形態 |

---

## 6. RTM 連結確認

### 6.1 追溯

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| Console PRD §0.11（F-910）→ US-930 | ☑ 已映射 |
| US-930 → 本檔 10 個 AC（AC-964-1～10） | ☑ 已映射（FRD-lite） |
| 10 個 AC → 本檔全部 69 個 AT（正控 44、負控 25；backend 20、Bridge 10、frontend 36、Playwright 3） | ☑ 已映射（本文件 §1、§3） |
| 根層 AC-SI-37-1、37-3、37-4、37-5 → AC-964-1～9 | ☑ 已映射（FRD-lite AC 編號規則 2；接縫引根層 TCS R139、R141、R146、R158、AT-437-1-3） |
| 契約 v0.1 → v1.0（實作輪回寫）、Architecture §5.6／§10.3 去規劃註 | □ 主控於 SCG-5 收齊（AT-964-10-3 守） |
| 每頁說明（self-improving） | □ 主控代做，與 UI 同 commit（AT-964-10-1 守） |
| RTM 本地子表（預定 §2.14；F-910、US-930、AC-964-1～10 與各 AT 列） | □ 主控於 SCG-5 回填 |
| AT → CI Pipeline | □ 未整合（測試檔入庫後由雲端 `agentconsole-ci` 的 backend、frontend、engine-bridge job 一併執行；`paths` 預期已含 SI 路徑，實作輪現查） |

**行為規則 → AT 對映**（W-S1～W-S10 各至少被一個 AT 釘住；有負控者並列）

| 規則 | 內容 | 釘住它的 AT |
|------|------|-------------|
| W-S1 | 橫幅欄位組與量不到 | AT-964-1-1、AT-964-1-2、AT-964-1-3、AT-964-1-E-1、AT-964-1-E-2、AT-964-1-E-3 |
| W-S2 | 控件與輸入閘 | AT-964-2-1、AT-964-2-2、AT-964-2-3、AT-964-2-E-1、AT-964-2-E-2、AT-964-3-E-3、AT-964-4-E-2 |
| W-S3 | 設定對話框與收據、入帳指令 | AT-964-2-4、AT-964-3-1、AT-964-3-2、AT-964-3-3、AT-964-3-4、AT-964-3-E-1、AT-964-3-E-2 |
| W-S4 | 立即啟動與軟停用 | AT-964-4-1、AT-964-4-2、AT-964-4-3、AT-964-4-4、AT-964-4-E-1 |
| W-S5 | 逾期與略過 | AT-964-5-1、AT-964-5-2、AT-964-5-3、AT-964-5-E-1 |
| W-S6 | ADMIN 邊界與錯誤呈現 | AT-964-6-1、AT-964-6-2、AT-964-6-3、AT-964-6-4、AT-964-6-E-1、AT-964-6-E-2 |
| W-S7 | backend 兩個 POST | AT-964-7-1～AT-964-7-9、AT-964-7-E-1～AT-964-7-E-5 |
| W-S8 | Bridge 兩個 POST | AT-964-8-1～AT-964-8-5、AT-964-8-E-1～AT-964-8-E-3 |
| W-S9 | 向量、黃金檔、對帳 | AT-964-9-1～AT-964-9-5、AT-964-9-E-1～AT-964-9-E-3 |
| W-S10 | 文件與既有鎖 | AT-964-10-1、AT-964-10-2、AT-964-10-3、AT-964-10-E-1 |

### 6.2 V 系列：實查檢核（QA、主控、掌舵者；**不是 AT**，結果寫進 SCG-4 報告與 RTM 備註；未驗者如實標「未驗」，構造情境不得充當）

| 編號 | 實查項 | 步驟與指令要點 | 通過判準與證據 | 再開症狀 |
|------|--------|----------------|----------------|----------|
| V1 | Docker 全棧：真容器 POST→稽核檔落地→主機 `si patrol --dry-run` 讀到待入帳（主控跑） | `docker compose --profile db --profile app --profile full up -d --build`；以 admin token 對 `POST /api/v1/si/schedule/set` 與 `POST /api/v1/si/runs/request` 各送一次；列稽核目錄；於主機以 `python tools/selfimproving.py patrol --dry-run`（零寫入）與 `status --json` 讀 `console_pending` | 兩次皆 201；稽核目錄各多一檔且位元組等於送出的本文；`patrol --dry-run` 的輸出列出兩份將入帳的 `audit_ref`；`console_pending` 含兩筆（kind 為 sched-set 與 run-request）；輸出逐字貼入 | 稽核檔缺、位元組不符、待入帳未被讀到 |
| V2 | 真機：Console 排程設定走完入帳（掌舵者；根層 PRD §8.1 P4 出口 (b)） | 掌舵者於 `/self-improving` 改週期並送出；主機巡邏器下一心跳（或手動入帳指令）入帳；重取橫幅 | 橫幅 `lastSet.carrier` 為 console、週期為新值；對帳面板該筆為已入帳；附 sid 與 line 或截圖 | 入帳後橫幅仍為舊值、或待入帳不消失 |
| V3 | 真機：立即啟動走完入帳（掌舵者） | 送出立即啟動；觀察事件帳本 | 出現一筆 trigger 為 a、carrier 為 console 的 `run.open`（或已有未關運轉時的 `sched.skip`）；按鈕在待入帳期間停用 | 按鈕仍可連點造成多筆、或請求卡在待入帳 |
| V4 | `schema.d.ts` 重產可重現與 OpenAPI | PKG-BE 完成後依 P2b 勘誤 9 作法重產；`OpenApiIT` 親跑 | 重產結果與入庫檔逐位元組相同；`OpenApiIT` rc 為 0（讀 rc 先存變數再讀） | 重產後有差異 |
| V5 | 閘門全綠 | backend `gradlew clean build`（Checkstyle、JaCoCo 80%、ArchUnit）；frontend `npm run lint`、`npx tsc --noEmit`、`npm run build`、`npx vitest run`（覆蓋率 70%）含 `design-rules.test.ts`；Bridge `python -m pytest -q`、`ruff check`（本目錄與根視角各一次） | 各指令 rc 為 0；輸出逐字貼入 SCG-4 報告 | 任一閘門紅 |
| V6 | 範圍守衛與文件連動 | `git diff --name-only` 與 `git status --porcelain`（含未追蹤檔）對照 §5.7；Flyway 目錄只多一個新檔；契約 v1.0、Architecture、RTM、說明檔的主控項 | 只出現允許集合；零根層 `tools/`、零 `.claude/`；缺項即紅 | 出現允許集合外的檔；既有 Flyway 檔被改 |
| V7 | Flyway 升級實查（真 PG） | 對已有三種舊列的資料庫套用新遷移 | 遷移成功；舊列不變；五值可寫；`pg_constraint` 實名與遷移檔一致 | 遷移失敗或舊列被改 |
| V8 | 平台與雲端 CI | Windows 實跑全部 AT 與 V1、V4；push 後 `agentconsole-ci`；macOS 標「未驗」 | `gh run list` 現查的 run 與結論；報告載明各平台狀態 | 雲端紅而本機綠 |

---

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 裁決與預設

| 編號 | 問題 | 本檔採用 | 替代與再開症狀 |
|------|------|----------|----------------|
| D-CS-1 | Flyway 版本號與 CHECK 實名 | **主控裁決**：一律現查最大版本＋1，TCS 與 AT 不寫死；實名以 `pg_constraint` 現查（AT-964-7-6、V7） | 再開：版本號撞號（兩鍵同時開發） |
| D-CS-2 | `sched-set` 界取得失敗的 reason | **主控裁決**：503 `si_unavailable`＋`details.cause=schedule_bounds_unavailable`，不新增 reason；`GET status` 失敗沿 GET 既有對映、不放行、不用快取值（AT-964-7-E-3） | 再開：畫面無法區分界取不到與 status 不可用 |
| D-CS-3 | 稽核 body 鍵序與位元組權威 | **主控裁決**：共通鍵之後依書寫序接專屬鍵；位元組權威＝根層 `consoleaudit.py`；黃金檔 G6～G9 由真 CLI 收下，AT 釘 rc 0 不釘數值（AT-964-9-1、9-2、9-3、9-E-1） | 再開：根層與 Console 對鍵序不一致導致 MAC 不符 |
| D-CS-4 | `reason`／`note` 規則 | **主控裁決**：選填、單行、≤120 code point、拒 U+0000～U+001F 與 U+007F、有值不得全空白、允許 `|`；與根層入帳驗證同一組（AT-964-3-E-3、4-E-2、7-E-2） | 再開：Console 放行而 CLI 拒收（或反之） |
| D-CS-5 | `run-request` 的重送防線 | **主控裁決**：backend 不設重送閘；前端在對帳快取有待入帳 `run-request` 時停用鈕（快取缺席不停用）；主機端以已有未關運轉改記 `sched.skip` 消化（AT-964-7-5、4-2、4-3、9-E-3） | 再開：連點造成大量待入帳而主機消化延遲 |
| D-CS-6 | 停用時 `periodMinutes` | **主控裁決**：仍必填且須在界內，不開例外（AT-964-2-3、2-E-2、7-3） | 再開：根層調界後現值落界外使掌舵者無法停用（畫面提示先改界內週期；若成真回根層修訂） |
| D-CS-7 | 兩個對話框分立或合一 | **主控裁決**：分立（`SiScheduleDialog`、`SiRunRequestDialog`，共用 `siParts.tsx`）；Developer 若合一，於勘誤登記檔名對照 | — |
| D-CS-8 | 請求本文未知欄位的行為 | **主控裁決**：本檔 AT 不釘；實作輪現查 P2b 兩個 POST 的現行行為後補差分 AT，並回寫契約 §1.2（v1.0） | 再開：兩端對未知欄位行為不一致（422 vs 忽略） |
| D-CS-9 | Playwright mock 替身形態 | **主控裁決**：沿 `tests/e2e/mockApi.ts` 與 `*.mock.spec.ts` 體例、`E2E_MODE=standalone` 先 `npm run build`；跑完以 `git show HEAD:<png>` 還原被覆寫截圖 | — |
| D-CS-10 | 空字串語意 | **主控裁決**：前端把空字串視為未填並省略該鍵；backend 對字串型空字串與全空白一律 422（與根層 R141 (c) 一致；表 M-X） | — |
| D-CS-11 | Bridge 本文超過 64 KB 的狀態碼 | **主控裁決**：422 `invalid_request`、`rule=too_large`（主控現查 `engine-bridge/app/routers/si.py` `_read_limited_body`：宣告或累計超過 `SI_WRITE_BODY_MAX_BYTES` 即 422 且不讀完）；AT-964-8-E-2 已釘 | — |
| D-CS-12 | 現值落界外時的畫面 | **主控裁決**：預填現值並標紅、提示先改成界內週期再送出停用（D-CS-6 不開例外） | 再開：掌舵者回報無法停用 |
| D-CS-13（實作輪 2026-11-09） | 開工前置「根層鍵 RELEASE」與根層 AT-437-1-3（真 CLI 收下黃金檔 G6～G9）互為前置（循環；根層 TCS D-IMP-1） | **主控裁決（依授權代決）**：PKG-BE 的前置降為「根層 SCHED 棒 commit」（黃金檔只依賴凍結契約與根層 `consoleaudit` 驗簽實作），根層鍵 RELEASE 改為本鍵 RELEASE 的前置；黃金檔仍由 BE 產出、主控以根層 CLI 驗簽後複製到 Bridge fixtures（§依賴序同步改寫） | 再開：黃金檔被根層 CLI 拒收 ⇒ 回 SD 對齊契約 §3 |
| D-CS-14（PKG-BE 交卷） | GET 打兩個新路徑：契約 §1.1 與 AT-964-7-E-5 寫「VIEWER、OPERATOR 403、ADMIN 405」，實測 `SecurityConfig` 對 `GET /api/v1/**` 放行 VIEWER 以上且無 GET 對映 ⇒ 已登入角色一律 405 | **主控裁決**：以實測為準——無 token 401、已登入角色（VIEWER／OPERATOR／ADMIN）一律 405；AT-964-7-E-5 的 Then 與契約 v1.0 §1.1 同步改字面；不動 `SecurityConfig`（P2b 既有通則） | 再開：資安審查要求未授權角色對寫入路徑必回 403 |
| D-CS-15（PKG-BE 交卷） | `SiKeyNames` 深層欄名對映：既有 `camel()` 通則已涵蓋 W-S7 (k) 九個鍵，主程式零改動 | **主控裁決**：接受；AT-964-7-8 釘住通則涵蓋；契約 v1.0 §4.1 註明「通則涵蓋、無特例表」 | — |
| D-CS-16（PKG-BE 交卷） | AT-964-7-5 字面「`ErrorReasons` 與兩端點的 OpenAPI 說明不含 `si_decision_duplicate`」，但 `ErrorReasons` 全域表必含該 reason（`decide` 在用） | **主控裁決**：Then 改為只判兩端點的 OpenAPI 說明與回應碼表（AT-964-7-7、7-5 皆斷言）；`ErrorReasons` 不在判準內 | — |
| D-CS-17（PKG-BE 交卷；承 D-CS-8） | 未知欄位處置：Spring Boot 預設忽略，稽核 body 只由已驗欄位組成、不會簽進未知欄位 | **主控裁決**：接受現狀、不補差分 AT；契約 v1.0 §1.2 回寫「未知欄位忽略、不入 body」 | 再開：契約改為拒收未知欄位 |
| D-CS-18（PKG-BE 交卷） | 黃金檔輸入值（reason「夾具啟用」、period 120／1440、note「夾具立即啟動」、`audit_ref` a1…06～09）由 BE 自定，TCS §5.1 未預填 | **主控裁決**：以 BE 產出為定稿並入表 §5.1（根層 AT-437-1-3 已以真 CLI 收下四檔並以位元組 tamper 驗 MAC 負控）；PKG-BR／PKG-FE 一律引用這四檔 | 再開：契約 §3 鍵序變更 ⇒ 重產 |
| D-CS-19（PKG-BE 交卷） | §4.1 表外因本鍵轉紅而補改的既有測試與替身：`IssueBridgeArchTest.AT_IC_07_6_1`（5→7、4→6）、`BackupJobMigrationIT.snapshotOfExistingTables`（排除 `si_console_writes_kind_check`）、三支 MigrationIT 的版本清單、`com/aisdlc/minibridge/**` 替身 | **主控裁決**：追認並補進 §4.1 與 §5.7（PKG-BE 列加 `com/aisdlc/minibridge/**`）；TCS-IssueCenter 勘誤四 4-2 同步、兩把 issue-center 鍵 refreeze | — |
| D-CS-21（PKG-BR 交卷） | 兩新路由 `subject` 非 null 的 422 違規 rule 名：契約未指名 | **主控裁決**：沿既有 `must_be_null`（與 obs-add 同值；訊息字面「此端點的 subject 須為 null」）；契約 v1.0 §2.2 註明 | — |
| D-CS-22（PKG-BR 交卷） | AT-964-8-4 的 AST 鎖新增「判準 6」（兩個新路由函式本體只呼叫 `_store_signed_audit`、不碰 `si_cli`，路由檔不得含組 argv 的函式），不屬 P2b 判準 1′～5′ | **主控裁決**：接受為 P4 增量判準；1′～5′ 常數與判準一字未改（AT-964-8-4 已斷言）；契約 v1.0 §2.2 補一句 | — |
| D-CS-23（PKG-BR 交卷；連動面） | 根層 commit 9baf53e9 的 `sched.py` 頂層 `from lib import transcript_activity` 使真 CLI 的 import 閉包變大，Bridge 真 CLI 測試夾具 `tests/si_repo_support.py::CLI_CLOSURE` 失效（開工即 `cannot import name 'transcript_activity' from 'lib'`） | **主控裁決**：BR 棒補 10 檔（`transcript_activity`、`quota_limits`、`quota_messages`、`model_roles`、`quota_policy`、`quota_policy_env`、`quota_pace`、`quota_burndown`、`endurance_env`、`unattended_authz`）進 `CLI_CLOSURE`，主控同 commit 把同 10 檔補進 `.github/workflows/agentconsole-ci.yml` 的 `push`／`pull_request` 兩段 `paths`，並把 `tests/test_si_deploy_config.py::FULL_PATHS`（合成 workflow 的期望表）同步 +10（AT-940-4-1／940-4-E-1／950-11-2 轉綠；§4.1 站點）；閉包以手列檔名維護、根層再加 lazy import 時會再失效 ⇒ 立為結構性債（OBS 列）：候選修法＝閉包改為靜態 import 分析或整個 `tools/lib` 頂層 `*.py` 複製，由 Console 側下一個增量處理 | 再開：根層 `tools/lib/selfimproving/**` 新增 import 其他 `tools/lib` 檔 ⇒ Bridge 真 CLI 測試紅 |
| D-CS-20（PKG-BE 交卷；實作備註） | (a) 請求 DTO 的 `enabled`／`periodMinutes`／`reason`／`note` 以 `Object` 接收，型別錯走輸入閘 422 一次全列（OpenAPI 以 `@Schema(type=…)` 標型）；(b) 「全空白」判準對齊 Python `str.strip()`（含 U+00A0、U+0085），避免 Console 放行而 CLI 以 `FIELD-BLANK` 拒收；(c) `SiConsoleWriteService` 新增依賴 `SiMirrorUseCase`、序 5′ 每次現取 `status()` 不快取（AT-964-7-9 釘 ArchUnit） | **主控裁決**：三項接受為實作決策並記錄於此（契約 v1.0 §1.2 註 (a)(b)） | — |
| ⚖ 1 | 兩個對話框分立或合一 | 預設分立（`SiScheduleDialog`、`SiRunRequestDialog`，共用 `siParts.tsx` 的收據與錯誤元件）；AT 的檔名依此；合一時 Developer 於勘誤登記對照 | 再開：LOC 或可讀性壓力 |
| ⚖ 2 | 請求本文的未知欄位處置（契約 §1.2 只說「沿 P2b 兩個 POST 現行行為」） | 本檔 AT 不釘未知欄位；實作輪現查 DTO 行為並於契約 v1.0 回寫，必要時補一個與既有 `POST /observations` 的差分 AT 經勘誤登記 | 再開：未知欄位被靜默收下卻簽進 body |
| ⚖ 3 | Playwright mock 的替身形態 | 沿既有 `tests/e2e/mockApi.ts` 與 `*.mock.spec.ts` 體例（`E2E_MODE=standalone`）；三個 PW AT 各一個動作 | 再開：既有體例無法替身 POST |
| ⚖ 4 | 空字串語意（前端視為未填、backend 視為違規） | 前端省略該鍵；backend 對字串型空字串與全空白一律 422（與根層 R141 (c) 一致）；表 M-X 明記 | 再開：掌舵者清空欄位後仍送出空字串 |
| ⚖ 5 | Bridge 本文過大（65537 位元組）的狀態碼 | 沿 P2b 現行對映（AT-964-8-E-2 以實作輪現查值寫入斷言，不在本檔假定 413 或 422） | 再開：與 P2b 對映不一致 |
| ⚖ 6 | 現值落界外時的畫面行為 | 預填現值標紅並提示先改界內週期，送出停用（AT-964-2-E-2） | 再開：掌舵者需要不改週期就停用 |

### 7.2 SD 對上位文件與現況的發現（供主控處理；本檔未改任何凍結檔）

1. 根層 PRD §9.1 C24 檔名表寫 Flyway V19、任務前置寫 V19／V20，契約 §5 現查最大為 V22（故新版本為 V23）；本檔一律「現查＋1」（D-CS-1），建議主控於 PRD 修訂時改寫。
2. 任務前置提到的 `SiStatusBanner.test.tsx` 於撰寫時不存在（橫幅斷言在 `SiView.test.tsx`），已於 §4.1 標「現查」。
3. 契約 §1.4 表欄名為 `details`，內列 `cause`；本檔依主控 D-CS-2 寫成 `details.cause`，實作輪於契約 v1.0 校對欄位位置。
4. 根層無人值守授權的現況句以根層 PRD AC-SI-38-3 的清單為準（`card`、`obs-add`、`obs-close`、`promote`、`rollback`、`sandbox`、`heldout-freeze`、`verify`、`decide`、`measure` 在無人值守下已拒；D-QA-9），本檔不引用「現碼只有 decide 與 measure 拒」的舊句；Console 側不依賴該清單。
5. AC-964-3 與 AC-964-4 的「收據」文案於 Console PRD 以「稽核檔已落地，待入帳」為準，本檔以 NFR-SC-1 釘「不含已生效字樣」。

---

## 📋 SCG-4 通過標準

- [ ] 本檔 69 個 AT 全綠（backend 20、Bridge 10、frontend 36、Playwright 3），且既有 AT 全綠（斷言值只在 §4.1 站點改）；AT-964-9-3 與 AT-964-9-E-1 須在根層鍵 RELEASE 且黃金檔已交接後為綠。
- [ ] V4、V5、V6、V7 由 QA 或主控實跑並貼輸出；V1 由主控跑；V2、V3 由掌舵者真機（未達成者標「未達成（前置未成立）」，不以構造資料充當）；V8 載明平台狀態。
- [ ] QA 獨立審查：突變驗證（對序 5′ 界比較、鍵序、`ingested` 判準、軟停用條件、量不到規則各做至少一個突變並確認對應 AT 轉紅）；斷言強度審查。
- [ ] 範圍守衛：§5.7 之外零變更；根層 `tools/`、`.claude/`、既有 Flyway 檔零差異；Flyway 目錄恰多一個新檔。
- [ ] 契約 v1.0、Architecture 去規劃註、RTM 本地子表、每頁說明由主控收齊並與實作同 commit。

## 勘誤（本檔凍結之後的訂正；凍結前留空）

（留空）
