輸入快照：HEAD＝01d9be6e；主控裁決 D-01～D-66

# API 契約 — ResearchToPRD（研究到規格：研究、PRD 工作室、Gate 0、分流、SCR、交付）〔定稿候選 v1.0.0-rc3〕

**版本**：v1.0.0-rc3 定稿候選｜**日期**：2026-11-02｜**作者角色**：Architect 草擬 v0.1、SD 依主控裁決 D-12～D-66 定稿
**讀者**：後端開發者（Spring Boot 4.1／Java 21）、前端開發者（Next.js 16）、Bridge 維護者（Python）、QA
**形狀沿用**：[API_Contract_SelfImproving_P2b.md](API_Contract_SelfImproving_P2b.md) 的章節骨架（共通約定→console-api→Bridge→SSE→DB→驗收）與 [API_Contract_P3-6.md](API_Contract_P3-6.md) 的封包。
**機器可讀版**：不另附 OpenAPI；真相源是 backend 執行期 `/v3/api-docs`（springdoc），入庫快照 `frontend/lib/api/schema.d.ts`；與本文衝突時以本文為準並回報修正。
**對應**：PRD `docs/01_requirements/ResearchToPRD_PRD.md`（每個端點附對應 FR／AC）、[ADR-003](ADR-003-ResearchToPRD.md)、`docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md`、Architecture §10／§11（本輪增補）。

| 版本 | 日期 | 範圍 |
|---|---|---|
| v0.1 | 2026-11-02 | Architect 初稿：P0 外環＋P1／P2 端點的形狀預留 |
| v1.0 | 2026-11-02 | SD 定稿：ADMIN 專屬動作（D-12）、`return`／`reinit`／`route/preview`／`gates`／`delivery/pr`／`records/audit`／`allowlist`／`restore` 新增端點、欄位值域與 PRD 對齊、DDL 修正（`rp_no`、`console_project_id`、地板）、SSE 事件與錯誤碼彙整；期標註〔P0〕〔P1〕〔P2〕 |
| v1.0.0-rc2 | 2026-11-02 | 依主控裁決 D-42～D-50 修訂：審查輪與分數 DTO 向框架審查卡模板對齊（`precheck.checks[]`、`conditions`、`prdVersion`＋`prdVersionNo`、`weightedScore` 兩位小數與整數式比較、`assistAgentId`、缺陷 `waiver`／`resolvedIn`）；證據 DTO 補 `candidate`、`unanchored`、`fetchNo` 與 `EvidenceMatrixDto`（`counterEvidence`、`honestBounds`、`searchLog`）；§0.2 能力探針為無 DSN 503 的唯一例外；§3 新增 SSE `research.replay_gap`；`return` 端點與 HUMAN_PENDING 守則（D-50）；D-51～D-53：`EvidenceItemDto.unanchored`、allowlist 稽核走 `AuditTrail`、審查輪 DTO 含 `finishedAt` 與 `fsmGateResult`；D-54～D-56：`ReviewRoundDto.verdict` 移除 `REVIEW_INVALID`、§3 新增 `research.review_invalid`；D-57：審查輪列只在輪有結果時一次寫入（`ReviewRoundDto` 刪 `status`、`finishedAt` 必填、結果欄（含 `verdict`）非 null；`research.review` 只在輪完成時送；`research.run` 加 `attempt`；API-RP-10 說明）；D-59：`ResearchFsmViewDto`（`retryHistory.gates`、`humanReturnCount`）、`ReviewRoundDto.fsmGeneration`、API-RP-04 補 `flowStatus` 由 Bridge 衍生並落 DB、API-RP-13 說明 |
| v1.0.0-rc3 | 2026-11-02 | 依 SCG-0 一審 FAIL 與主控裁決 D-60～D-64 修訂：D-60——ESCALATION 人工恢復後預算不歸零（API-RP-11 `iterate` 說明、§4 控件表剩餘預算改 `max(0, 3 − currentCount)`）與「換世代」＝API-RP-20 的 `generation:"next"` 模式（僅 ADMIN，D-64；VIEWER 由既有授權鏈擋〔403 `ACCESS_DENIED`〕、OPERATOR 由服務層擋〔403 `research_write_forbidden`〕，兩者 Bridge 請求數 0；§0.1、§0.2 第 2a 列、§0.3、§1.1、§1.2、§4、§5 Bridge 端點表）；D-62(1)——API-RP-22 稽核落 V6 `audit_log` 的 `entity_type`／`entity_id`（無 `note` 欄）；F-20——`minIntervalSeconds` 建立後不可 PATCH（§1.2、API-RP-22）；D-61——`ReviewRoundDto.fsmRetryCount` 註記（`gate PASS` 輪為 0、POST_HUMAN 通過輪為 null）；QA 二審 D-65——API-RP-20 不帶 `generation` 的重試初始化只在 `flowStatus=FAILED` 且 `flowDetail` 以 `init_failed:` 起頭時可呼叫，其餘 409 `stage_conflict`（`details.flowStatus`／`flowDetail`）、零寫入（§1.4、§2.2 Bridge 端點表） |

---

## 0　共通約定

### 0.1　封包、認證、角色

- 認證：Bearer JWT。成功 `{code, message, data, timestamp, traceId}`；錯誤 `{code, message, errors[], reason?, details?, traceId}`（P2b §0.2:40）。
- 角色（Architecture §8.2 增列）：**`GET`＝VIEWER 以上；`POST／PUT／PATCH` 預設＝OPERATOR 以上（`SecurityConfig` 通用規則，`SecurityConfig.java:97`）；下列動作僅 ADMIN（D-12）**：`POST …/approve`、`POST …/return`、`POST …/route`、`POST …/gates`、`POST …/delivery/tag`、`POST …/delivery/pr`、`POST /research/allowlist`、`PATCH /research/allowlist/{id}`。ADMIN 規則在 `SecurityConfig` 以 `requestMatchers(HttpMethod.POST／PATCH, …).hasRole("ADMIN")` 逐條置於通用 `/api/v1/**` 規則**之前**（先中者定案；先例 `POST /api/v1/si/**`＝`SecurityConfig.java:88`、`PUT／DELETE /api/v1/issues/**`＝`:91-92`、`POST /api/v1/sysadmin/**`＝`:95`）：`/api/v1/research/projects/*/approve`、`…/*/return`、`…/*/route`（精確路徑；`…/route/preview` 不在此列＝OPERATOR）、`…/*/gates`、`…/*/delivery/tag`、`…/*/delivery/pr`、`/api/v1/research/allowlist`（POST）、`/api/v1/research/allowlist/*`（PATCH）。VIEWER／OPERATOR 呼叫＝403 `ACCESS_DENIED`。**例外（D-64）**：`POST …/reinit` 帶 `generation:"next"`（換世代）亦僅 ADMIN，但同一路徑的重試初始化模式為 OPERATOR 以上，`SecurityConfig` 的 matcher 無法依請求本文分流，所以角色檢查分兩段：**VIEWER**＝既有授權鏈就擋（通用 POST 規則要求 OPERATOR 以上，`SecurityConfig.java:97`）⇒ 403 `ACCESS_DENIED`（與 `RbacIT` 現行 VIEWER 寫入斷言同一條：`$.code`＝403、`$.reason`＝`ACCESS_DENIED`，`RbacIT.java:99-102`）；**OPERATOR**＝通過授權鏈後由 console-api 的 `ResearchCommandService` 在服務層檢查 ⇒ 403 `research_write_forbidden`（不是 matcher 層的 `ACCESS_DENIED`）；兩者的 Bridge 請求數皆為 0（角色檢查先於任何 Bridge 呼叫），`RbacIT` 對兩者各釘一個斷言。**`approver` 一律取 JWT subject，請求本文不收 approver**（先例 `SddFreezeRequest.java:11`）。
- 時間：ISO-8601 含 offset，UTC 輸出 `+00:00`，不得 naive。
- 識別碼：`id`（研究專案）＝UUID，由 console-api 在建立時配號並同時是 Bridge 的 `research_id`；`rpNo`＝顯示編號 `RP-NNNN`（DB 序列配號）；`stageRunId`＝引擎 `run_id`；證據 `E-NNN`、來源 `S-NNN`、缺陷 `D-<輪>-<序>`。
- 機密：GitHub token、權杖、金鑰不出現在任何回應、`details`、日誌、DTO `toString`。

### 0.2　共通失敗表（先中者定案）

| 序 | HTTP | reason | 條件 |
|---|---|---|---|
| 1 | 401 | — | 無有效 JWT |
| 2 | 403 | `ACCESS_DENIED` | 角色不足（VIEWER 打寫入端點；OPERATOR 打 ADMIN 專屬端點；**例外**：OPERATOR 打換世代改走第 2a 列） |
| 2a | 403 | `research_write_forbidden` | 服務層角色檢查（D-64）：OPERATOR 打換世代（`POST …/reinit` 帶 `generation:"next"`）——matcher 無法依請求本文分流，所以在 `ResearchCommandService` 入口檢查，先於任何 Bridge 呼叫（Bridge 請求數 0）；VIEWER 打同一端點仍在第 2 列就被擋（`ACCESS_DENIED`）。同名 reason 在 Bridge 傳輸層另指寫入權杖缺或錯（§2.1），兩者是不同的擋下層 |
| 3 | 503 | `research_write_disabled` | backend 或 Bridge 未設 `BRIDGE_RESEARCH_WRITE_TOKEN` |
| 4 | 503 | `research_requires_db` | Bridge 無 `BRIDGE_DB_DSN`（研究端點不降級成純檔案；D-36）。**唯一例外**：`GET /api/v1/research/capabilities`（API-RP-01）仍回 200 並以 `db:false` 說明（D-49；UI 才能顯示停用原因而不是空白或錯誤頁） |
| 5 | 400／422 | `invalid_request` | 輸入閘（§1.2）；console-api 欄位級 `errors[]`（400）、Bridge `violations[]`（422） |
| 6 | 404 | `research_not_found` | `{id}` 不存在或已封存且端點不收封存 |
| 7 | 409 | 端點專屬（§1.4） | 狀態衝突 |
| 8 | 502／504 | `bridge_unreachable`／`bridge_timeout` | 沿 `BridgeHttpAdapter` 語意：連線 3 s、一般 30 s、**POST 不重試**（Architecture §4.3:299） |

### 0.3　角色矩陣

| 動作 | VIEWER | OPERATOR | ADMIN | 端點 |
|---|---|---|---|---|
| 檢視全部頁面、產物、版本、審查、決定、對帳 | ✓ | ✓ | ✓ | 所有 `GET` |
| 新建／封存／復原／重試初始化研究專案、取消 stage、對帳 | — | ✓ | ✓ | API-RP-03、18、20 |
| **換世代**（ESCALATION 時放棄舊鍵；D-64） | — | — | ✓ | API-RP-20（`generation:"next"`；VIEWER 由既有授權鏈擋〔403 `ACCESS_DENIED`〕、OPERATOR 由 `ResearchCommandService` 在服務層擋〔403 `research_write_forbidden`〕；見 §0.1、§0.2 第 2a 列） |
| 啟動研究、草擬、審查、修訂、迭代、TCS 草擬；存 PRD 新版 | — | ✓ | ✓ | API-RP-09、11 |
| 分流預演、發起 SCR | — | ✓ | ✓ | API-RP-14（preview）、15 |
| **Gate 0 核准、退回修改** | — | — | ✓ | API-RP-12、21 |
| **分流確認、SCG 登錄、建立 Release Tag、建立 PR** | — | — | ✓ | API-RP-14（route）、23、17 |
| **管理研究來源 allowlist（新增／停用）** | — | — | ✓ | API-RP-22 |

---

## 1　console-api 端點（`/api/v1/research/**`）

### 1.1　總表

| 編號 | 方法與路徑 | 角色 | 成功 | 期 | operationId | 對應 FR／AC |
|---|---|---|---|---|---|---|
| API-RP-01 | `GET /research/capabilities` | V+ | 200 | P0 | `getResearchCapabilities` | FR-R2P-04／AC-04-11；FR-13／AC-13-7 |
| API-RP-02 | `GET /research/projects` | V+ | 200 | P0 | `listResearchProjects` | FR-01／AC-01-10；FR-21 |
| API-RP-03 | `POST /research/projects` | O+ | 201 | P0 | `createResearchProject` | FR-03／AC-03-1～03-5、03-7 |
| API-RP-04 | `GET /research/projects/{id}` | V+ | 200 | P0 | `getResearchProject` | FR-01／AC-01-1、01-9 |
| API-RP-05 | `GET /research/projects/{id}/events` | V+ | 200 | P0 | `listResearchEvents` | FR-06／AC-06-2、06-4 |
| API-RP-06 | `GET /stream/research/{id}`（SSE） | V+ | 200 | P0 | — | FR-06／AC-06-1、06-2 |
| API-RP-07 | `GET /research/projects/{id}/sources`、`/evidence` | V+ | 200 | P0 | `listResearchSources`、`listResearchEvidence` | FR-05；FR-02／AC-02-3 |
| API-RP-08 | `GET /research/projects/{id}/prd/versions`、`/prd/versions/{n}` | V+ | 200 | P0 | `listPrdVersions`、`getPrdVersion` | FR-02／AC-02-2；FR-09／AC-09-2 |
| API-RP-09 | `PUT /research/projects/{id}/prd` | O+ | 201 | P0 | `savePrdVersion` | FR-09／AC-09-6；FR-02／AC-02-2 |
| API-RP-10 | `GET /research/projects/{id}/review-rounds`、`/review-rounds/{n}` | V+ | 200 | P0 | `listReviewRounds`、`getReviewRound` | FR-08／AC-08-1；FR-09／AC-09-4 |
| API-RP-11 | `POST /research/projects/{id}/stages/{stage}` | O+ | 202 | P0（`tcs-draft` P1） | `startResearchStage` | FR-04、07、08、14／AC-14-7；FR-18／AC-18-6 |
| API-RP-12 | `POST /research/projects/{id}/approve` | **ADMIN** | 200 | P0 | `approveResearchBaseline` | FR-10／AC-10-1～10-9 |
| API-RP-13 | `GET /research/projects/{id}/fsm` | V+ | 200 | P0 | `getResearchFsm` | FR-08／AC-08-3；FR-18／AC-18-1 |
| API-RP-14 | `POST …/route/preview`（O+，200）、`POST …/route`（**ADMIN**，202）、`GET …/route`（V+，200） | 見左 | 見左 | P1 | `previewResearchRoute`、`routeResearchProject`、`getResearchRoute` | FR-11、12、13 |
| API-RP-15 | `POST …/scr`（O+，202）、`GET …/scr`（V+，200） | 見左 | 見左 | P1 | `openResearchScr`、`listResearchScr` | FR-19 |
| API-RP-16 | `GET /research/projects/{id}/decomposition` | V+ | 200 | P1 | `getResearchDecomposition` | FR-14／AC-14-1、14-6 |
| API-RP-17 | `GET …/delivery`（V+，200）、`POST …/delivery/tag`（**ADMIN**，201）、`POST …/delivery/pr`（**ADMIN**，201） | 見左 | 見左 | P2 | `getResearchDelivery`、`createResearchTag`、`createResearchPr` | FR-20／AC-20-1～20-5 |
| API-RP-18 | `POST …/cancel`、`/reconcile`、`/archive`、`/restore` | O+ | 200 | P0 | `cancelResearchStage`、`reconcileResearch`、`archiveResearchProject`、`restoreResearchProject` | FR-01；FR-23／AC-23-1 |
| API-RP-19 | `GET /research/projects/{id}/records/audit` | V+ | 200 | P0 | `getResearchRecordsAudit` | FR-02／AC-02-4；§1.3 M3 |
| API-RP-20 | `POST /research/projects/{id}/reinit` | O+；`generation:"next"` 僅 **ADMIN** | 200 | P0 | `reinitResearchProject` | FR-03／AC-03-5；FR-18／AC-18-6 |
| API-RP-21 | `POST /research/projects/{id}/return` | **ADMIN** | 200 | P0 | `returnResearchPrd` | FR-10／AC-10-5；FR-08／AC-08-9 |
| API-RP-22 | `GET /research/allowlist`（V+，200）、`POST /research/allowlist`（**ADMIN**，201）、`PATCH /research/allowlist/{id}`（**ADMIN**，200） | 見左 | 見左 | P0 | `listResearchAllowlist`、`addResearchAllowlistEntry`、`updateResearchAllowlistEntry` | FR-04／AC-04-7 |
| API-RP-23 | `POST /research/projects/{id}/gates` | **ADMIN** | 200 | P2 | `registerResearchGate` | FR-15／AC-15-6 |

### 1.2　輸入閘（Architecture §8.3 增列第 1 層）

| 欄位 | 規則 | 違規 |
|---|---|---|
| `slug` | `^[a-z0-9][a-z0-9-]{0,29}$`；與未封存專案不重複 | 400／409 `slug_in_use` |
| `title` | 1～200 字 | 400 |
| `topic` | 1～500 字、無 NUL（PRD §5.1.2 為準） | 400 |
| `depthLevel` | `QUICK｜STANDARD｜DEEP` | 400 |
| `scope.layers` | 四布林 `academic／industry／oss／community`，至少一個為真；`industry` 為真但 `capabilities.webLayerEnabled=false` ⇒ 400 `layer_unavailable` | 400 |
| `scope.techStack`、`inScope[]`、`outOfScope[]`、`recencyYears`、`applicabilityAxes[]`、`targetScopeHint` | `techStack` ≤200 字自由文字（不入任何指令）；`inScope`／`outOfScope` 各 ≤20 項、每項 ≤200 字；`recencyYears`∈{1,2,3}；`applicabilityAxes` 1～6 項、每項 ≤40 字；`targetScopeHint`∈`AISDLC_MODULE｜STANDALONE_PROJECT｜UNDECIDED` | 400 |
| `baseVersion`（PRD） | ＝目前 head 版號 | 409 `prd_version_conflict`（`details.headVersion`） |
| `content`（PRD） | ≤ 1 MiB、UTF-8、無 NUL | 422 |
| `expectedDigests` | 鍵＝相對 POSIX 路徑、值＝`sha256:<64hex>`；必須涵蓋核准當時的 `01_specs/PRD-v1.0.0.md`（或 head PRD）、`00_research/evidence_matrix.md`、`00_research/issue_scope.json`、`01_specs/adr_draft.md` | 422 |
| `reason`（approve／return／scr／gates／reinit） | 1～500 字；`return` 與 `reinit`（`generation:"next"`）必填 | 422 |
| `route.targetModule`〔P1〕 | 取自 ADMIN 維護的落點目標清單（預設 autoclaude／agentconsole／sdd／monorepo） | 422 |
| `route.targetPath`〔P1〕 | 絕對；過 allowed roots | 422 `sanitization_failed` |
| `route.branchName`〔P1〕 | `^feature/[a-z0-9-]{1,40}$` | 400 |
| `route.repoName`〔P1〕 | `^[a-z][a-z0-9-]{1,38}$` | 400 |
| `route.visibility`〔P1〕 | `PUBLIC｜PRIVATE`，預設 `PRIVATE`；`PUBLIC` 須 `confirmRepoName`＝`repoName`（D-15） | 422 `public_confirmation_required` |
| `route.stackTemplate`〔P1〕 | 須在 `capabilities.scaffoldTemplates[]`（登記制，D-32） | 422 |
| `route.scopeDiffersReason`〔P1〕 | 分流軌道與 PRD `target_scope` 不同時必填 1～200 字 | 422 |
| `scr.kind／sourceKind`〔P1〕 | `MINOR｜MAJOR`／`HUMAN｜REVIEW_FINDING｜SCG4｜HEALING_FAILED` | 400 |
| `gates.gate／result`〔P2〕 | `gate`∈`PR_REVIEW｜RTM_VERIFY｜RELEASE_READY`；`result`∈`PASS｜FAIL`（本功能對 `RELEASE_READY` 只送 `FAIL`）；`reviewReportRef` ≤300 字 | 400 |
| `tagName`〔P2〕 | `^v[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.]+)?$` | 400 |
| `allowlist.host` | 小寫 host、無 scheme／port／path／userinfo、`^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$`；`listKind`∈`FETCH｜WEB`；`minIntervalSeconds` 1～3600，建立時決定、**建立後不可 PATCH**（要調整＝停用後重建；實際間隔＝max(Bridge 內建下限, 條目值)，PRD NFR-R2P-03-6；低於內建下限者仍以內建下限執行）；Reddit 網域（`reddit.com`、`*.reddit.com`、`redd.it`）須 `tosAcknowledged=true` | 400／422 `terms_ack_required` |

### 1.3　DTO（camelCase；console-api 對 Bridge 的 snake_case 轉換同 Arch §4.3:299）

```ts
type FlowStepId = "topic" | "studio" | "route" | "build" | "deliver";
// DB 游標只含前八值；PAUSED 只出現在 ResearchFlowPolicy 衍生的 effective（D-20 SA-06）
type FlowStatus = "IDLE"|"RUNNING"|"WAITING_HUMAN"|"BLOCKED"|"ESCALATED"|"FAILED"|"CANCELLED"|"COMPLETED"|"PAUSED";
interface FlowStep { id: FlowStepId; label: string; state: "DONE"|"CURRENT"|"BLOCKED"|"TODO"; phase?: string; blockedReason?: string }
interface Flow {
  currentStep: FlowStepId; furthestStep: FlowStepId;
  steps: FlowStep[];                                   // 固定 5 項，順序＝topic→deliver
  effective: { step: FlowStepId; phase: string; status: FlowStatus; detail: string };  // 步驟 3 之後由 ResearchFlowPolicy 衍生
  resumeHref: string;                                  // 例 /research/<id>?step=studio；build 階段可為 /projects/<pid>/execute?from=research:<id>
}
interface ResearchProjectSummary { id: string; rpNo: string; slug: string; title: string; depthLevel: string; targetScope: string;
  flowStep: FlowStepId; flowPhase: string; flowStatus: FlowStatus; flowDetail: string; consoleProjectId: string|null;
  createdBy: string; createdAt: string; updatedAt: string; archivedAt: string|null }
interface ResearchProjectDetail extends ResearchProjectSummary {
  topic: string; scope: Record<string, unknown>; scopeRev: number; fsmProject: string; fsmGeneration: number;
  flow: Flow;
  counts: { sources: number; evidenceItems: number; prdVersions: number; reviewRounds: number; openDefects: number };
  headPrdVersion: number | null;
  lastReview: { round: number; weightedScore: number|null; minDimensionScore: number|null; passed: boolean; escalated: boolean } | null;   // 最新一個已完成的輪（D-57）
  parentResearchId: string | null;
}
interface ResearchEvent { seq: number; eventType: string; step: FlowStepId; actor: string; refKind: string|null; refId: string|null;
  payload: Record<string, unknown>; occurredAt: string }
interface SourceDto { sourceNo: string; layer: "ACADEMIC"|"INDUSTRY"|"OSS"|"COMMUNITY"; tier: "T1"|"T2"|"T3"; verification: "V1"|"V2"|"V3";
  anchorKind: "URL"|"DOI"|"COMMIT"; url: string; doi: string|null; gitCommit: string|null; title: string; authorsOrg: string;
  publishedAt: string|null; sourceType: string; licenseSpdx: string|null; licenseNote: string; clueOnly: boolean;
  fetches: Array<{ fetchNo: string; method: string; observedBy: "BRIDGE"|"AGENT_DECLARED"; host: string; httpStatus: number|null; outcome: string;
                   rawSha256: string|null; rawBytes: number|null; fetchedAt: string }> }
interface EvidenceItemDto { evidenceNo: string; sourceNo: string; candidate: string|null; claim: string; f1Mechanism: string; f2Evidence: string; f3Critique: string;
  f4RiskTags: string[]; f5Applicability: Record<string, { grade: "A"|"M"|"N"; reason: string }>; f6Limits: string;
  f7Verification: "V1"|"V2"|"V3"; strength: "STRONG"|"MEDIUM"|"WEAK"|"CANDIDATE"; unanchored: boolean /* Bridge 入庫時計算，PRD 不得引用 */; matrixVersion: number; scopeRev: number }
interface CounterEvidenceDto { evidenceNo: string; searchId: string|null; conclusion: "WEAKEN"|"LIMIT"|"IRRELEVANT"|"NOT_FOUND"|"NOT_SEARCHED"; sourceNo: string|null; note: string }
interface HonestBoundsDto { notFound: Array<{ query: string; date: string; result: string }>; summaryOnly: string[]; notReadFully: string[] }
interface SearchLogDto { searchNo: string /* "Q-NNN"（DB 為整數，顯示時補零） */; layer: "ACADEMIC"|"INDUSTRY"|"OSS"|"COMMUNITY"; tool: "WebSearch"|"WebFetch"; query: string; at: string; resultUrls: string[] }
interface EvidenceMatrixDto { matrixVersion: number; scopeRev: number; sha256: string; items: EvidenceItemDto[];
  counterEvidence: CounterEvidenceDto[]; honestBounds: HonestBoundsDto; searchLog: SearchLogDto[] }   // 後三者取自 research_artifacts(EVIDENCE_ITEMS).content 全文（D-43；P0 不另立表）
interface PrdVersionDto { versionNo: number; semver: string; kind: "DRAFT"|"BASELINE"; authorKind: "AGENT"|"HUMAN"; author: string;
  parentVersionNo: number|null; sha256: string; bytes: number; evidenceRefs: string[]; changeSummary: string; createdAt: string; content?: string /* 僅單筆端點回 */ }
interface ReviewScoreDto { dimension: "ARCHITECTURE"|"PRODUCT"|"QA"|"SECURITY"; weight: number; score: number /* 整數 0～100 */;
  agentId: string;                                     // PRODUCT＝"pm-po"（D-44）
  assistAgentId: string|null; assistAgentYamlSha256: string|null;   // 只有 SECURITY：compliance-officer，其餘 null
  agentYamlSha256: string; personaSha256: string; summary: string }
interface DefectDto { defectNo: string; dimension: string; severity: "P1"|"P2"|"P3"|"P4"; code: string; prdAnchor: string;
  description: string; suggestion: string; evidenceRefs: string[]; status: "OPEN"|"FIXED"|"WAIVED"|"SUPERSEDED"|"REGRESSED";
  fixedInVersionNo: number|null; resolvedIn: string|null;      // resolvedIn＝該版本的 semver（審查卡的 resolved_in）
  waiver: { by: string; reason: string; at: string } | null }  // 審查卡的 waiver；at 對映 DB resolved_at；WAIVED 時三者必填
// 輪列只在輪有結果時一次寫入（D-57）：沒有進行中的輪列，所以沒有 `status`，也沒有「結果未定」的 null；進行中的審查看 `research.run`（stage＝REVIEW）
interface ReviewRoundDto { roundNo: number; fsmGeneration: number; prdVersionNo: number; prdVersion: string;   // prdVersion＝semver 字串、prdVersionNo＝整數，並存（D-43）；fsmGeneration＝輪列的 fsm_generation，供 UI 只比對目前世代（D-59(4)）
  triggerKind: "AUTO"|"MANUAL"|"POST_HUMAN";
  precheck: { passed: boolean; checks: Array<{ id: "SLV-001"|"SLV-002"|"SLV-003"|"AMBIGUITY"; passed: boolean; detail: string }> };
  weightedScore: number|null;   // W100/100，兩位小數（DB NUMERIC(5,2) 原樣序列化）；前置否決不過時 null。顯示用 toFixed(2)；比較一律用整數 Math.round(weightedScore*100) 對 8500，不得先四捨五入到一位（D-42）
  threshold: number; floorScore: number; minDimensionScore: number|null;
  conditions: { precheckPassed: boolean; weightedGeThreshold: boolean|null; allDimensionsGeFloor: boolean|null; noOpenP1: boolean };   // 由 console-api 自欄位導出，供 UI 說明不成立的條件；前置否決不過（未計分）時 weightedGeThreshold、allDimensionsGeFloor 為 null
  openP1Count: number; passed: boolean; verdict: "PASS"|"REVISE"|"ESCALATE";   // REVIEW_INVALID 不是輪的 verdict：無效輸出不寫輪列（D-55）
  fsmGateResult: "PASS"|"FAIL"|null;   // triggerKind=POST_HUMAN 且 passed 時為 null（HUMAN_PENDING 下不呼叫 gate PASS，D-50）
  fsmRetryCount: number|null; escalated: boolean; scores: ReviewScoreDto[]; defects: DefectDto[];   // fsmRetryCount：gate FAIL 輪＝其回傳的 retry_count；gate PASS 輪＝0（引擎於 PASS 時歸零、回傳不帶 retry_count）；POST_HUMAN 通過輪（未呼叫 gate）＝null，與 fsmGateResult 同為 null（D-61）
  startedAt: string; finishedAt: string }   // 起訖取自產生本輪的 REVIEW stage run，皆必填（D-57）
// API-RP-13：研究面 FSM 視圖＝既有 SddFsmState（形狀沿 SddFsmStateDto）原樣、只增不減，再加兩個欄位（D-59(4)）
interface ResearchFsmViewDto extends SddFsmState {
  retryHistory: SddRetryHistory & {                    // 既有 { count, last } 原樣
    gates: Record<string /* SCG_VALIDATION｜PR_REVIEW｜RTM_VERIFY */, { currentCount: number; entries: number }> };   // currentCount＝該閘 current_count；entries＝該閘 history 筆數
  humanReturnCount: number }                           // 目前 fsm_generation 內 research_gate_decisions 中 gate=GATE0、decision=CHANGES 的筆數
interface ApproveResult { gateDecisionId: string; stage: string; specDocDigests: Record<string,string>; fsmState: string }
interface AllowlistEntryDto { id: string; listKind: "FETCH"|"WEB"; host: string; layer: string; purpose: string; tosNote: string;
  minIntervalSeconds: number; enabled: boolean; tosAcknowledged: boolean; source: "ENV"|"ADMIN"; addedBy: string|null; addedAt: string|null }
interface CapabilitiesDto { mode: "local"|"mock-only"; db: boolean; claudeCli: { ok: boolean; version?: string }; ghCli: { ok: boolean; authenticated: boolean };
  git: { ok: boolean; version?: string }; researchRoot: string; scaffoldRoot: string|null; scaffoldTemplates: string[];
  repoWritable: boolean; webLayerEnabled: boolean; fetchHosts: string[] }
interface RecordsAuditDto { classes: Array<{ id: string; name: string; count: number }>; missing: string[] }   // R1～R14；missing＝count 為 0 且該類不屬「允許為 0」（R10、R12）者
interface ReconcileResult { consistent: boolean; checks: Array<{ name: string; status: "ok"|"drift"|"NOT_EVALUABLE";
  drift?: Array<{ kind: string; path: string; expectedSha256?: string; actualSha256?: string }> }> }
// P1／P2：
interface RouteStepDto { stepNo: number; step: string; status: "RUNNING"|"OK"|"FAILED"|"SKIPPED"|"COMPENSATED"; argvRedacted: string;
  exitCode: number|null; stdoutTail: string; stderrTail: string; startedAt: string; finishedAt: string|null }
interface RouteDecisionDto { routeId: string; track: "A"|"B"; targetKind: "MODULE"|"STANDALONE"; targetModule: string|null; targetPath: string;
  gitBranch: string|null; baseRef: string|null; repoUrl: string|null; repoVisibility: "PUBLIC"|"PRIVATE"|null; stackTemplate: string|null;
  consoleProjectId: string|null; implFsmProject: string|null; status: "PENDING"|"RUNNING"|"SUCCEEDED"|"FAILED"|"COMPENSATED";
  failureStep: string|null; steps: RouteStepDto[] }
interface ScrDto { scrNo: number; kind: "MINOR"|"MAJOR"; sourceKind: string; reason: string; affectedSections: string[];
  status: "OPEN"|"APPROVED"|"REJECTED"|"APPLIED"|"SUPERSEDED"; prdFromVersionNo: number|null; prdToVersionNo: number|null;
  successorResearchId: string|null; requestedBy: string; requestedAt: string }
interface DeliveryDto { kind: "RELEASE_TAG"|"PULL_REQUEST"|"RELEASE_NOTE"; ref: string; commitSha: string|null; url: string|null;
  rtmReportRef: string|null; fsmStateAfter: string|null; status: "CREATED"|"FAILED"; createdBy: string; createdAt: string }
```

### 1.4　各端點要點

**API-RP-01 能力探針**：轉 Bridge `GET /research/capabilities`，快取 30 s；`mode=mock-only` 時 UI 停用「啟動深研」（D-29）。**無 `BRIDGE_DB_DSN` 時仍回 200 並以 `db:false` 說明**——這是 §0.2 第 4 列 503 規則的唯一例外（D-49），其餘 `/research/**` 端點一律 503。

**API-RP-03 建立**：請求 `{slug,title,topic,scope,depthLevel,targetScopeHint?}`；console-api 驗輸入→配 `id`→`AuditTrail.note("research.create","research",id)`→Bridge `POST /research/projects`。Bridge 先在單一交易寫 `research_projects`（DB 序列配 `rp_no`）、`research_events(seq=1)`、`research_artifacts(ISSUE_SCOPE)`，再建工作區與 `issue_scope.json`、外環 FSM 鍵（INIT→AGENT_LOAD）。201 回 `ResearchProjectDetail`（`flowStep=topic`、`flowPhase=INGESTED`）。失敗：409 `slug_in_use`、503 `research_write_disabled`／`research_requires_db`、422（Bridge 路徑／環境不合）；檔案或建鍵失敗＝`flowStatus=FAILED`＋`flowDetail="init_failed:<步驟>"`（見 API-RP-20）。

**API-RP-04 詳情與流程脊**：`flow` 由 `ResearchFlowPolicy.effective(research, project, latestRun, fsmView)` 計算（純函式、單測釘住）：

| 條件 | `effective` |
|---|---|
| `flowStep∈{topic,studio,route}` 或 `flowPhase∈{TCS_DRAFTING,TCS_PENDING}` | 直接用 DB 游標（`flowStatus` 也是 DB 值：Bridge 於寫游標時依優先序 `ESCALATED` > `RUNNING` > `WAITING_HUMAN` > `IDLE` 衍生並落 DB，`ResearchFlowPolicy` 原樣取用、不自行衍生；`REVIEWING` 以 REVIEW stage run 為憑、不以輪列推導；D-59(3)） |
| `consoleProjectId` 非空、無 run、FSM 在 SPEC_FROZEN／IMPLEMENTATION 且已 negotiate | `build／BUILD_READY` |
| 最新 run `RUNNING` | `build／BUILDING`；其中存在 RETRYING 步驟＝`build／HEALING` |
| 最新 run `PAUSED`＋有 `review_requests PENDING` | `build／AWAITING_HUMAN`（`status=WAITING_HUMAN`）；其餘 PAUSED＝`build／PAUSED`（`status=PAUSED`） |
| FSM `ESCALATION*` | `build／ESCALATED`（`status=ESCALATED`） |
| FSM `RELEASE_READY`／`RELEASE` | `deliver／RELEASE_PENDING`／`DELIVERED` |

`furthestStep`＝DB 游標與 effective 中較後者（供前端判斷 `?step=` 是否可達；超前即導回 `currentStep`）。

**API-RP-05／06 事件與 SSE**：`GET …/events?afterSeq=&limit=(≤500)` 回 `{items:ResearchEvent[], nextSeq, truncated}`（讀 `research_events`）。SSE 事件 `id: <seq>`、`event: <eventType>`、`data: <ResearchEvent JSON>`；認 `Last-Event-ID`；每 15 s `event: heartbeat`；斷線後客戶端先 REST 回補再接串流（Arch §5.3:399）；**伺服器重播不完整**（緩衝已逾期，或可重播範圍與 `Last-Event-ID` 之間有序號缺口）時，重連後先送 `research.replay_gap`（`fromSeq`、`toSeq`；不帶 `id:`），客戶端收到該事件，或自行偵測到 `id` 不連續，即全量重抓（專案詳情、列表、`…/events?afterSeq=` 自己最後處理的序號之後，至少到 `toSeq`）再重新訂閱（D-49）。事件型別見 §3。

**API-RP-07 來源與證據**：`GET …/sources` 回 `SourceDto[]`；`GET …/evidence?matrixVersion=`（預設最新版）回 `EvidenceMatrixDto`：`items` 取自 `research_evidence_items`（含 `candidate`、`strength`、`unanchored`），`counterEvidence`／`honestBounds`／`searchLog` 取自 `research_artifacts`（`kind=EVIDENCE_ITEMS`）的 `content` 全文（D-43；P0 不另立表）；「授權待查」計數由 console-api 純函式自 `items` 與來源導出、不落 DB。

**API-RP-09 存新版**：`{baseVersion, content, changeSummary?}`；成功 201 `PrdVersionDto`（`authorKind=HUMAN`、`author`＝JWT subject）；Bridge 先寫檔後寫列（原子 replace，重用 `fsutil.write_text_atomic`）；`flowPhase` 回 `DRAFTING`（人改過需重審；Gate 0 的前置為「head 版本有一輪通過的審查」）；凍結後（Gate 0 之後）409 `spec_frozen`。

**API-RP-10 審查輪（D-57）**：`GET …/review-rounds` 回 `ReviewRoundDto[]`（依 `roundNo` 遞增）、`GET …/review-rounds/{n}` 回單筆（`n`＝`roundNo`）。**只有已完成評估的輪才有列**：進行中、被取消、中斷或輸出無效的審查沒有輪列，`{n}` 指向它們時回 404 `research_not_found`（§0.2 第 6 列），進行中的狀態由 stage run 與 `research.run` 事件表達；`counts.reviewRounds` 與 `lastReview` 因此恆指已完成的輪。

**API-RP-11 啟動階段**：`stage∈research｜draft｜review｜revise｜iterate｜tcs-draft`；body 選填 `{auto?, note?, afterEscalation?}`。前置（Bridge 驗，409）：`research` 需 `INGESTED／EVIDENCE_READY`；`draft` 需 `EVIDENCE_READY` 且證據閘過；`review` 需有 head 版本；`revise` 需最近一輪 FAIL 且未 `ESCALATED`；`iterate`＝`revise`→`review` 重複至通過或耗盡（上限由 FSM `SCG_VALIDATION`＝3 次 FAIL，含人工退回；D-24；迴圈是否續跑一律以每輪 `gate` 回傳的 `next_state`／`escalated` 為準，Bridge 不自以 `3 − currentCount` 判斷）；**ESCALATION 人工恢復後（D-60）**：引擎的 `resume-from-escalation` 不動 retry 計數（只有 `gate PASS` 與 `spec-frozen` 歸零），`currentCount` 仍為 3——`iterate`（與 `revise` 帶 `afterEscalation=true`）只跑一輪 `revise`→`review`：該輪 `gate PASS` ⇒ 歸零並轉 HUMAN_PENDING，`gate FAIL` ⇒ 立即再 ESCALATION、迴圈停止（歷史列依引擎既有行為帶 tamper 字樣，Architecture §12.1 L-R12）；`review` 在 FSM 現態為 HUMAN_PENDING 時（人工退回後的再審）`triggerKind=POST_HUMAN`：通過只記 DB（不呼叫 `gate … PASS`）、未通過呼叫 `gate SCG_VALIDATION FAIL`（D-50）；`tcs-draft`〔P1〕需內環鍵已 Stage-1 採納；現有 `RUNNING` 的 stage ⇒ 409 `stage_conflict`；FSM 在 `ESCALATION*` ⇒ 409 `escalated`（`details.recovery` 帶恢復指令）；**「我已恢復，繼續」＝`revise` 帶 `afterEscalation=true`**：Bridge 唯讀驗 FSM 現態已離開 ESCALATION*，否則 409 `fsm_state_conflict`（`details.current_state`），不呼叫任何 FSM 寫入動詞（D-30）；恢復後預算不歸零、至多再得一次審查（見上；D-60）；DB 阻塞 ⇒ 503 `db_blocked`；Web 層關閉而請求含 `industry` ⇒ 400 `layer_unavailable`；`mock-only` 模式只停用 UI 的「啟動深研」，伺服器端不拒絕（mock claude 是合法執行器，Docker E2E 以 API 直呼 `stages/research` 驗證）。回 202 `{stageRunId, flowPhase, flowStatus}`。

**API-RP-12 Gate 0（僅 ADMIN；D-12、D-19、D-23）**：請求 `{prdVersion, expectedDigests, reason?}`；`approver`＝JWT subject（console-api 轉傳，Bridge 驗非空、非保留字、格式）。Bridge 檢查序：①權杖 ②`prdVersion` 為 head 且有 `passed=true` 的審查輪（否則 409 `review_not_passed`）③`expectedDigests` 與現檔逐一比對（不符 409 `spec_digest_changed`，`details.pair=expected_vs_file`）④FSM 現態＝HUMAN_PENDING 且無 ESCALATION（否則 409 `fsm_state_conflict`，帶 `expected_state`；ESCALATION 時 409 `escalated`）⑤〈外環鍵有重試史〉`transition→SPEC_REGRESSION_CHECK`（D-25）⑥`spec-frozen --stage Gate-0 …`（開啟中的 SCR 時 Stage 為 `Gate-0-SCR<n>`）。成功 200 `ApproveResult`；`research_gate_decisions` 與 `research_events` 已寫入；`flowStep=route`、`flowPhase=FROZEN`。**非冪等**：第二次呼叫 409 `fsm_state_conflict`。任何 agent、Bridge 排程或 CLI 都不得呼叫本端點（AST 鎖）。

**API-RP-13 FSM 視圖**：轉 Bridge `GET /sdd/fsm/{fsmProject}?root=<workspace>`，回 `ResearchFsmViewDto`＝`SddFsmState`（含 `phase`、`retryHistory`、`frozenStages`、`escalationHistory`、`recovery{target,powershell,posix}`；形狀沿既有 `SddFsmStateDto`）原樣、只增不減，再加兩個欄位（D-59(4)）：`retryHistory.gates`（各閘 `currentCount`＝FSM 檔該閘 `current_count`、`entries`＝該閘 `history` 筆數；既有 `retryHistory.count`／`last` 不動）與 `humanReturnCount`（整數：目前 `fsm_generation` 內 `research_gate_decisions` 中 `gate=GATE0`、`decision=CHANGES` 的筆數，由 console-api 讀 DB 計得）。各閘分項需 Bridge 在 `GET /sdd/fsm/{key}` 的投影新增同級鍵 `retry_gates`（`{<gate>: {current_count, entries}}`；additive，既有 `retry_history`＝`{count,last}` 與其測試不動）。前端直接餵 `SddPhaseProgress`／`SddEscalationBlock`，並以這兩個欄位與審查輪列表做 PRD FR-R2P-08 邊界條件的「第 n 輪 vs retry_history」對照。

**API-RP-14〔P1〕 分流**：請求 `{track:"A"|"B", targetModule?, targetPath?, branchName?, baseRef?, repoName?, visibility?, confirmRepoName?, stackTemplate?, createGithub?:boolean, scopeDiffersReason?}`。**`route/preview`（OPERATOR）**：驗輸入→Bridge `:route-preview`，回「動作清單」（每項：動作、目標路徑／分支／遠端、是否觸及外部系統），**零副作用**（前後 `git status --porcelain`、目標目錄、DB 皆相同）；部署模式不支援（容器無 `gh`、無寫入掛載）回 422 `route_unsupported_in_deployment`（`details` 指出缺項）。**`route`（僅 ADMIN）**：驗角色與輸入→（A）驗 `targetModule` 屬落點目標清單；（B）驗 `BRIDGE_SCAFFOLD_ROOT` 已設與 `stackTemplate` 在登記清單→**先**建 `projects` 列（`executionPath`、`sddProject`＝內環鍵，沿 V12 索引防重綁）→Bridge `:route`（B 的 `createGithub` 時 console-api 於單次請求本文傳 `github_token`，取自 `system_configs` 加密欄；Bridge 不落地）→任一步失敗補償到安全態（專案列標 `ARCHIVED` 並留稽核；**不**自動 `git clean`／`stash`／刪目錄）。202；進度由 SSE `research.route` 與 `GET …/route`（`steps[]`）取得。錯誤：409 `route_conflict`（已有 `PENDING／RUNNING／SUCCEEDED` 的分流）、409 `branch_exists`、422 `target_not_empty`／`public_confirmation_required`／`sanitization_failed`、502 `route_step_failed`（帶 `failureStep`）。

**API-RP-15〔P1〕 SCR**：`{kind:"MINOR"|"MAJOR", sourceKind, reason, affectedSections[]}`；MINOR 受「同 Stage ≤2 次」限制（超過 409 `scr_limit`，要求改 MAJOR）；MAJOR 回新 `researchId`（`successorResearchId`）；`sourceKind=HEALING_FAILED` 只產生恢復指令與記錄、不呼叫 FSM 寫入動詞。FSM 動作序列見 ADR-XPLAT-017 附錄 A。

**API-RP-17〔P2〕 交付**：`GET …/delivery` 回 `DeliveryDto[]`＋追溯快照參照；`POST …/delivery/tag`（僅 ADMIN）`{tagName, message?, createGithubRelease?}`：前置 FSM `RELEASE_READY` 且 RTM 100%（合併與雲端 CI 綠由人確認——Bridge 不查 CI）；已存在 409 `tag_exists`；成功後內環鍵 `transition→RELEASE`；`POST …/delivery/pr`（僅 ADMIN）`{branch?, title?, bodyPreviewAck:true}`：Bridge `git push -u origin <branch>`＋`gh pr create`（標題與內文由 PRD 與追溯表摘要確定性產生；ADMIN 已在確認框預覽），失敗不補償、回結構化錯誤。

**API-RP-18 取消／對帳／封存／復原**：`cancel` 停止進行中的 stage run（既有 `:stop` 路徑；被取消的審查 run 不寫審查輪列、不佔 `round_no`，D-57）；`reconcile` 回 `ReconcileResult`（只報告不修復，結果追加 `research_events`〔`research.reconcile`〕）；`archive`＝軟刪除，30 天內 `restore`（沿 Console PRD §9.3）。

**API-RP-19 入庫完整率**：JDBC 讀取，回 R1～R14 各類筆數與 `missing[]`（R10 自癒嘗試、R12 SCR 允許為 0）。

**API-RP-20 重試初始化／換世代**：請求本文選填 `{generation?: "next", reason?: string}`。**無 `generation`＝重試初始化**：冪等——不覆寫已存在檔案、不重複配 `rpNo`、不重複建 FSM 鍵；只在 `flowStatus=FAILED` 且 `flowDetail` 以 `init_failed:` 起頭時可呼叫，其餘狀態一律 409 `stage_conflict`（`details.flowStatus`／`flowDetail`）、零寫入（無檔案寫入、無 FSM 動作、無 DB 變更；D-65：回應碼要寫定，不留給實作期各寫各的）。**`generation:"next"`＝換世代（D-60）**：放棄這一把外環鍵、另開新世代鍵取得全新 3 次預算（框架工作流第 2.5 節既有路徑；這不是恢復，是放棄——舊鍵永遠停在 ESCALATION、不呼叫 `resume-from-escalation`，R-9.5／禁令 6 不受影響）；**僅 ADMIN**（D-64）：同一路徑的重試初始化模式為 OPERATOR 以上，`SecurityConfig` 的 matcher 無法依請求本文分流，所以角色檢查分兩段：**VIEWER**＝既有授權鏈就擋（通用 POST 規則要求 OPERATOR 以上）⇒ 403 `ACCESS_DENIED`（以 `RbacIT` 現行 VIEWER 寫入斷言為準：`$.code`＝403、`$.reason`＝`ACCESS_DENIED`）；**OPERATOR**＝通過授權鏈後由 console-api 的 `ResearchCommandService` 在服務層檢查 ⇒ 403 `research_write_forbidden`（不是 matcher 層的 `ACCESS_DENIED`）；兩者的 Bridge 請求數皆為 0（角色檢查先於任何 Bridge 呼叫；無決定列、無事件、`fsm_generation` 不變），`RbacIT` 對兩者各釘一個斷言；`reason` 必填（1～500 字）；前置（Bridge 驗）：FSM 現態為 ESCALATION*，否則 409 `fsm_state_conflict`（`details.current_state`）；缺理由 422 `invalid_request`。Bridge 動作沿首世代建立的順序（DB 先於檔案與 FSM）：單一交易寫決定列 `research_gate_decisions(gate=ABANDON_KEY, decision=ABANDONED, decided_by=JWT subject, fsm_project＝被放棄的舊鍵, fsm_state_after=ESCALATION, reason)`、`fsm_generation`＋1、`fsm_project` 改指新鍵 `research-<slug>-g<N+1>`（N＝原 `fsm_generation`）、游標 `flow_phase=REVISING`／`flow_status=IDLE`（PRD head 版本保留）與 `research.gate` 事件；再以 `show` 建新鍵（唯一建檔點的第三個呼叫點，ADR-XPLAT-017 D2）並走到 AGENT_LOAD（環境 `SDD_ENABLE_AUTO_RECOVERY=0`）；建鍵失敗＝`flowStatus=FAILED`、`flowDetail='init_failed:fsm'`，以本端點的重試初始化補建（冪等）。之後的審查輪列帶新的 `fsmGeneration`，`humanReturnCount` 與 `retryHistory.gates` 以新鍵計（舊世代輪列保留可查）。回 200 `{flow, fsmProject, fsmGeneration, gateDecisionId}`。

**API-RP-21 退回修改（僅 ADMIN；D-25、D-50）**：`{reason}`（必填）；Bridge 呼叫 `gate SCG_VALIDATION FAIL --reason "人工審查：…"`——FSM **維持 HUMAN_PENDING**（trace 記 `gate_fail_blocked`）、`retry_count`＋1，與自動 FAIL 共用 3 次預算；寫 `research_gate_decisions(decision=CHANGES)`；PRD 回可編輯；之後的重審 `trigger_kind=POST_HUMAN`：通過只在 DB 記一輪（`fsmGateResult=null`；Bridge **不在 HUMAN_PENDING 呼叫 `gate … PASS`**，因 PASS 路徑會以 rc 1 結束）、未通過呼叫 `gate SCG_VALIDATION FAIL`；累計第 3 次 FAIL＝ESCALATION。回 200 `{gateDecisionId, fsmRetryCount, escalated}`。

**API-RP-22 allowlist（D-17）**：`GET` 回 `AllowlistEntryDto[]`（含 `source=ENV` 的部署基底與 `ADMIN` 條目）；`POST` 新增條目（初始清單＝arXiv、Semantic Scholar、GitHub API、Stack Exchange API 四組主機；產業網域逐一加入；Reddit 須 `tosAcknowledged=true`）；`PATCH` 只准改 `enabled`（與停用欄），不可刪；body 含 `enabled` 以外的欄位（含 `minIntervalSeconds`）回 422 `invalid_request`、條目不變；`minIntervalSeconds` 建立時決定、**建立後不可 PATCH**（實際間隔＝max(內建下限, 條目值)，低於內建下限者仍以內建下限執行；PRD NFR-R2P-03-6、AC-R2P-04-12），要調整間隔＝停用該條目後重建；ADMIN 新增／停用成功後由 console-api 以 `AuditTrail.note("research.allowlist", "research_allowlist", <條目 id>)` 標註（Bridge 寫 `research_allowlist_entries` 並回應成功、條目 id 已知後才標）：`audit` 日誌行帶 `action=research.allowlist`、`entity=research_allowlist:<條目 id>`；V6 `audit_log` 列（每個 `/api/` 寫入請求本就恆一列，含被拒的 401／403／422／429；被拒請求的 `entity_*` 欄取過濾器預設解析，本契約不規範）的 `entity_type='research_allowlist'`、`entity_id`＝條目 id；**不新增欄位、不改 V6、不改 `AuditLoggingFilter`**（V6 沒有 `note` 欄）；**不寫 `research_events`**——該表以 `research_id` 為鍵，allowlist 是全域資源（D-52、D-62(1)）；有效清單＝環境變數基底 ∪ 啟用中條目，每個 stage run 的快照入 `research_stage_runs.allowlist_snapshot`。

**API-RP-23〔P2〕 SCG 登錄（僅 ADMIN；D-23）**：`{gate, result, reason, reviewReportRef?}`；Bridge 於現態 IMPLEMENTATION 時先 `transition→PR_REVIEW` 再 `gate`；`RTM_VERIFY` 前置＝RTM 100%（<100% 拒絕）；回傳以 FSM 的 `next_state` 為準；寫 `research_gate_decisions(gate=SCG4／SCG5)` 與事件；SCG-4 審查者須未參與規格與實作（ADMIN 於確認框聲明，Console 不判斷獨立性）。

---

## 2　Bridge 端點（`/research/*`；僅 console-api 呼叫，不對瀏覽器開放）

### 2.1　共通

寫入端點須 `X-Bridge-Token`（值＝`BRIDGE_RESEARCH_WRITE_TOKEN`）：未設 503 `research_write_disabled`；缺或錯 403 `research_write_forbidden`；佔位字串或短於 32 字元＝啟動即 `SettingsError`（同 `settings.py:148-170`）。每個請求帶 `X-Trace-Id`。成功與被拒都記 `bridge.audit`（`security.AuditLog`，`security.py:83-105`）：`research_write{verb,research_id,approver,result,trace_id}`，不含權杖與 token。無 `BRIDGE_DB_DSN`＝所有研究端點 503 `research_requires_db`，**唯一例外**是下一行的 `GET /research/capabilities`（仍 200，`db:false`；D-49）。
`GET /research/capabilities` 回 `{mode, db, claude_cli:{ok,version}, gh_cli:{ok,authenticated}, git:{ok,version}, sdd_root, research_root, scaffold_root, scaffold_templates[], repo_writable, web_layer_enabled, fetch_hosts[]}`；`GET /health/deep` 另帶資訊欄 `research`（不影響 503 判定，同 `sdd` 先例，Arch §10.1:936）。

### 2.2　端點形狀（snake_case）

| 端點 | 請求要點 | 回應要點 |
|---|---|---|
| `POST /research/projects` | `{research_id, slug, title, topic, scope, depth_level, created_by}` | 201 `{research_id, rp_no, workspace_path, fsm_project, flow:{step,phase,status}}`；409 `slug_in_use`；422 `violations[]` |
| `POST /research/projects/{id}/stages/{stage}:start` | `{auto, note, requested_by, after_escalation}` | 202 `{stage_run_id, engine_run_id, flow}`；409 `stage_conflict／fsm_state_conflict／escalated`；503 `db_blocked` |
| `PUT /research/projects/{id}/prd` | `{base_version, content, change_summary, author}` | 201 `{version_no, semver, sha256, bytes}`；409 `prd_version_conflict／spec_frozen` |
| `POST /research/projects/{id}:approve-baseline` | `{prd_version, expected_digests, approver, reason}` | 200 `{gate_decision_id, stage, spec_doc_digests, fsm_state}` |
| `POST /research/projects/{id}:return` | `{approver, reason}` | 200 `{gate_decision_id, fsm_retry_count, escalated}` |
| `POST /research/projects/{id}:route-preview`／`:route`〔P1〕 | `{track, target_module?, target_path?, branch_name?, base_ref?, repo_name?, visibility?, stack_template?, create_github, console_project_id, approver, github_token?, scope_differs_reason?}` | preview 200 `{actions[]}`；route 202 `{route_id}`；`github_token` 僅單次請求、不落地、不入 log |
| `POST /research/projects/{id}:scr`〔P1〕、`:gates`〔P2〕、`:tag`／`:pr`〔P2〕 | 見 §1.4 | 202／200／201 |
| `POST /research/projects/{id}:cancel`、`:reconcile`、`:archive`、`:restore` | `{}` | 200 `{stopped_run_id?}`／`{consistent, checks[]}`／`{flow}` |
| `POST /research/projects/{id}:reinit` | `{}`（重試初始化）｜`{generation:"next", reason, decided_by}`（換世代；D-60） | 200 `{flow}`｜200 `{flow, fsm_project, fsm_generation, gate_decision_id}`；重試初始化：409 `stage_conflict`（`flow_status` 非 FAILED，或 `flow_detail` 不以 `init_failed:` 起頭；`details.flowStatus`／`flowDetail`；零寫入，D-65）；換世代：409 `fsm_state_conflict`（現態非 ESCALATION*）、422（缺理由） |
| `GET /research/allowlist`、`POST /research/allowlist`、`PATCH /research/allowlist/{id}` | `{list_kind, host, layer, purpose, tos_note, min_interval_seconds, tos_acknowledged}`／`{enabled}` | 200／201 `AllowlistEntry`；422 `terms_ack_required` |
| `GET /research/projects/{id}/events?after=&limit=`、`/stream?after=` | — | `research_events` 重播／SSE |

寫檔與入庫的持久化協定（寫檔→outbox→DB 交易→標 done）、fail-loud 行為見 ADR-003 D2 與 Architecture §10.2′。

---

## 3　SSE 事件型別（`event:` 欄；`seq`＝`research_events.seq`）

| `event` | `payload` 要點 |
|---|---|
| `research.step` | `{flowStep, flowPhase, flowStatus, flowDetail}` |
| `research.run` | `{stage, roundNo, attempt, stageRunId, engineRunId, status, tokensUsed}`（`(stage, roundNo, attempt)` 即 stage run 的自然鍵；**進行中的審查只由 `stage=REVIEW` 的本事件表達**，審查沒有進行中的輪列，D-57；前端可據 `engineRunId` 另訂引擎原生串流 `GET /autoclaude/runs/{id}/stream` 看逐行日誌） |
| `research.source` | `{sourceNo, layer, tier, verification, title, url, fetchOutcome}` |
| `research.evidence` | `{matrixVersion, evidenceNo, sourceNo, claim, strength}` |
| `research.prd` | `{versionNo, semver, authorKind, author, sha256}` |
| `research.review`（D-57） | `{roundNo, weightedScore, minDimensionScore, passed, verdict, escalated}`：**只在輪完成時送**（輪列寫入的同一交易內追加；`weightedScore`、`minDimensionScore` 於前置否決不過時為 null，其餘必有值）；進行中、取消、中斷、無效輸出都不送本事件（進行中聽 `research.run`；無效另送 `research.review_invalid`） |
| `research.review_invalid`（D-55） | `{stageRunId, roundNo, attempt, reason}`：審查者輸出重試一次後仍不合 schema；該 REVIEW stage run `status=FAILED`、`exit_reason=review_invalid`；**不寫審查輪列、`roundNo` 不佔用**（下一次審查沿用同號、`attempt`＋1）；`reason` 為驗證失敗摘要（維度與規則，不含審查者原文） |
| `research.defect` | `{defectNo, severity, dimension, status}` |
| `research.gate` | `{gate, decision, decidedBy, fsmStage, frozenDigests}` |
| `research.reconcile` | `{consistent, driftCount}` |
| `research.route`〔P1〕 | `{routeId, stepNo, step, status}` |
| `research.scr`〔P1〕 | `{scrNo, kind, status}` |
| `research.delivery`〔P2〕 | `{kind, ref, status}` |
| `research.alert` | `{kind: "BLOCKED_DB"｜"ESCALATED"｜"QUOTA"｜"DENIED_FETCH"｜"STAGE_FAILED", detail}` |
| `research.replay_gap`（D-49） | `{fromSeq, toSeq}`：伺服器重播不完整（緩衝已逾期或有序號缺口）時於重連後第一個送出；與 `heartbeat` 一樣不是 `research_events` 列、不帶 `id:`；客戶端收到即全量重抓（專案詳情、列表、`…/events?afterSeq=` 自己最後處理的序號之後，至少到 `toSeq`）再續接 |
| `heartbeat` | `{}` |

事件文字（標題、摘要、描述）一律以純文字渲染（不用 `dangerouslySetInnerHTML`；AC-R2P-06-3）。

---

## 4　前端控件資料來源與閘（逐控件）

| 控件（來源規格 §6.2） | 資料來源 | 閘 |
|---|---|---|
| 議題輸入面板 `[啟動深研]` | API-RP-03＋API-RP-11(`research`) | `capabilities.mode=local` 且 `claudeCli.ok`；層開關受 `webLayerEnabled` 限制 |
| 研究來源設定對話框（ADMIN） | API-RP-22 | 僅 ADMIN 顯示；Reddit 須勾選條款確認 |
| 證據鏈即時動態欄 | API-RP-05／06（`research.source／evidence／run`） | — |
| `[生成 PRD 初稿 →]` | API-RP-11(`draft`)；成功後 `?step=studio` | 需 `EVIDENCE_READY` |
| PRD 目錄樹／編輯器／Diff | API-RP-08（兩版本 content 於前端 `diff`）、API-RP-09 | 保存＝新版；未存稿僅 `localStorage` 便利層 |
| 四方雷達／缺陷卡 | API-RP-10（`scores[]`、`defects[]`）；雷達＝`recharts` RadarChart | — |
| `[一鍵自動迭代修正]`（未通過才顯示） | API-RP-11(`iterate`) | 未 `ESCALATED`；顯示剩餘預算＝`max(0, 3 − currentCount)`（`currentCount`＝API-RP-13 的 `retryHistory.gates.SCG_VALIDATION.currentCount`；ESCALATION 人工恢復後仍為 3 ⇒ 顯示 0 並標「恢復後僅一次機會」，按鈕仍啟用；D-60） |
| `[核准 PRD →]`（通過＝前置否決通過、`W100 ≥ 100 × threshold`、各維度 ≥60 且無未結 P1 才解鎖；不成立的條件取自 `ReviewRoundDto.conditions`） | API-RP-12 | 僅 ADMIN；需 head 版本有 `passed` 審查輪；`expectedDigests` 由前端自 API-RP-08／證據矩陣取得 |
| `[退回修改]` | API-RP-21 | 僅 ADMIN；理由必填 |
| HUMAN_PENDING 等待時長與滿 72 小時橫幅（D-48(3)） | API-RP-10（最近一輪 `fsmGateResult=PASS` 的 `finishedAt`）＋API-RP-13（FSM 現態） | 純前端計算；零寫入、不呼叫任何 FSM 動詞 |
| ESCALATION 區塊＋「我已恢復，繼續（僅一次機會）」＋「換世代」 | API-RP-13（`SddEscalationBlock`＋`CopyCommand`）；「我已恢復，繼續」＝API-RP-11(`revise`,`afterEscalation=true`)；「換世代」＝API-RP-20(`generation:"next"`) | 前者 Bridge 驗 FSM 已離開 ESCALATION*；後者僅 ADMIN（非 ADMIN 停用並以 `title` 說明權限不足；後端 403：VIEWER＝`ACCESS_DENIED`〔授權鏈〕、OPERATOR＝`research_write_forbidden`〔服務層〕，兩者 Bridge 請求數 0）、FSM 現態須為 ESCALATION*、理由必填、二次確認 |
| 分流 Drawer 卡 A／B〔P1〕 | API-RP-14；進度 SSE `research.route` | `capabilities.repoWritable`／`scaffoldRoot`／`ghCli` 決定可用性並顯示原因；確認僅 ADMIN |
| TCS 草擬／核准〔P1〕 | API-RP-11(`tcs-draft`)；凍結走既有 `POST /api/v1/projects/{id}/sdd/freeze` | TCS 在場 |
| 看板／自癒／終端／HITL〔P2〕 | 既有執行 API＋SSE（`/executions/{runId}/…`、`stream/executions/{runId}/logs`）＋`research.*`；自癒＝視圖 `v_research_healing_attempts` | 既有 signoff 硬閘不變 |
| 追溯矩陣、SCG 登錄、Release 動作列〔P2〕 | 既有 `GET /executions/{runId}/rtm`；API-RP-23；API-RP-17 | 僅 ADMIN；`RELEASE_READY` |

---

## 5　DB 對應與驗收

DDL 與所有權見 Architecture §11.3／§7；console-api 以 JDBC 讀、零寫入（ArchUnit 字串掃描測試釘住）。驗收 AT 命名沿既有：`AT-96N-…`（編號由各期 TCS 配）。**P0 必備 AT**：①建立→`research_events seq=1`、`flow=topic/INGESTED`、`rpNo` 配號；②同一 `slug` 第二次 409；③VIEWER 打 POST 403、匿名 401、OPERATOR 打 ADMIN 專屬端點 403；④Bridge 無 DSN→503 `research_requires_db`；⑤斷 DB 時 stage 進 `BLOCKED_DB`、復原後 outbox 重放、事件不重不漏；⑥SSE 斷線以 `Last-Event-ID` 重播無缺漏；⑦三輪 FAIL→`ESCALATED` 且 FSM 現態＝ESCALATION（不是 AUTO_RECOVERY_ATTEMPT）；⑧Gate 0 核准：`research_gate_decisions` 一列、`frozen_digests` 與 `show` 的 `frozen_stages[-1].spec_doc_digests` 逐位元相同、第二次核准 409；⑨核准後改檔→`expectedDigests` 比對 409；⑩`tier=T3` 且非線索被 DB 擋；⑪PRD 200 KB 預覽 ≤2 s；⑫`PUT …/prd` 兩個併發請求，一個 201 一個 409；⑬allowlist：ADMIN 新增生效且入下一個 stage 快照、OPERATOR 403、Reddit 無條款確認 422；⑭人工退回與自動 FAIL 共用 3 次預算（第 3 次＝ESCALATION）；⑮既有 `:freeze` 對無 TCS 仍 422；⑯無 DSN 時 `GET /research/capabilities` 仍 200 且 `db:false`、其餘端點 503；⑰HUMAN_PENDING 守則負控（`gate SCG_VALIDATION FAIL` 態不動且計數＋1、`gate … PASS` rc≠0；退回後再審通過 `fsmGateResult=null`）；⑱DB 觸發器：缺陷 `status` 單向、來源 `verification` 只升不降、通用守衛擋清單外欄位與任何 DELETE；⑲伺服器重播不完整時送 `research.replay_gap` 且客戶端全量重抓；⑳`weightedScore` 表驅動：85／85／84／86 → 84.95 且未通過、85／85／85／85 → 85.00 且 `weightedGeThreshold=true`。
