> 入庫說明（2026-11-07 主控）：本報告自 session 暫存區落檔；文中引用的截圖（.png）、axe 結果與 SSE log 留在主控暫存區未入庫，入庫版以文字判定為準。

# INT P0：Docker 全棧 mock E2E 代驗報告（ResearchToPRD P0；PKG-INT）

- 驗證對象：主控以 origin/main `0b678757` 重建的 Docker 全棧（nginx :80 → frontend／backend／engine-bridge／PG18；`capabilities.mode=mock-only`、研究劇本＝`mock_claude_script_pass.json`）。
- 執行：整合代驗棒（Sonnet，唯讀：未改 repo、未碰 git 寫入動詞、未重建／重啟容器、未派子代理、Web 工具未用）。起訖約 2026-11-03 05:01～05:40（UTC+8）。收尾時 `git status --short` 為空、HEAD＝`04884296`（主控於我執行期間提交的 compose 研究劇本接線 commit；我未改任何 repo 檔）。
- 帳密與權杖只在指令內使用（執行期自 `backend/README.md` 解析），未寫入任何輸出檔；nginx／backend 日誌核對無 `access_token` 值外洩（nginx 以 `?***` 遮罩）。
- 證據根目錄（全部絕對路徑）：`C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\245e80aa-71c4-443b-b8fe-d59f87a9f0e8\scratchpad\r2p\qa\int\`（下稱 `INT\`）；截圖與 axe 在 `INT\ui\`、SSE 逐行日誌在 `INT\sse-*.log`、進度在 `INT\progress.md`。

## 0. 先說結論

1. **路徑 B（通過劇本）端到端全綠**：建立 → research → draft → review（第 1 輪 79.90 REVISE）→ iterate → 第 2 輪 90.30 PASS → ADMIN 核准（API 與 UI 各一次）→ `SPEC_FROZEN`／flow `route/FROZEN`；`specDocDigests` ＝ FSM CLI `show` 的 `frozen_stages[-1].spec_doc_digests` ＝ DB `research_gate_decisions.frozen_digests`（四鍵逐位相同）；二次核准 409。
2. **RBAC 真機全數符合**（VIEWER 13/13 寫入 403 `ACCESS_DENIED`；OPERATOR 對 approve／return／allowlist 403；換世代 OPERATOR 403 `research_write_forbidden` 且 0 決定列）。
3. **UI 真機**：23 次 axe 掃描（WCAG 2.0／2.1 A／AA）**零違規**；1440／1000／600／390 無水平溢出；對話框焦點陷阱與歸還成立；ESCALATION 區塊、核准、換世代、送審、一鍵迭代、新建、封存復原皆可走通。
4. **發現 14 項缺陷（P1×0、P2×6、P3×5、P4×3）**，其中四項是「單元／Mock 測試看不出、只有真棧才現形」的跨服務契約錯位（對帳欄位名、範圍欄位大小寫、失敗游標語意、取消後死路）；另有兩項非 hermetic（Docker E2E 實際連真外網、失敗路徑呼叫外部 MiniMax）。細節見 §5。
5. **未能驗的**：路徑 A（fail3，三輪 FAIL）——容器環境固定為 pass 劇本、且禁止重建容器；真 `claude` 相關 V 項；Bridge／DB 斷線類（503／outbox 重放／replay_gap）。見 §7。

## 1. API 走查（admin；HTTP 狀態／reason／耗時）

專案代號：A=RP-0001（兩軸、故意）、B=RP-0002（零命中議題）、C=RP-0003（主線，核准）、D=RP-0004（人工退回／換世代）、E=RP-0005（UI ESCALATION）、F=RP-0006（UI 核准）、G=RP-0007（UI 新建）。耗時為單次請求回應時間；stage 另列牆鐘（POST 後至終態事件）。

| # | 步驟 | 結果 | 備註 |
|---|------|------|------|
| 1 | `GET /research/capabilities`（admin） | 200 · 52 ms | `mode=mock-only, db=true, claudeCli.ok=false, webLayerEnabled=false`；`fetchHosts:[]`（見 INT-08） |
| 2 | `GET /research/allowlist` | 200 · 22 ms | 5 個 ENV 基底（arxiv 3 s、S2 3 s、GitHub 60 s、SE 3 s） |
| 3 | 建專案（議題軸用中文簡稱 `效能`／`授權`） | 422 `invalid_request` · 35 ms | Bridge：`軸標籤須取自登錄表 [技術可行、授權相容、維護風險、效能邊界、資安、成本]` |
| 4 | 建專案 A（兩軸） | **201** · 675 ms | `rpNo=RP-0001`、`flowStep=topic/INGESTED/IDLE`、`fsmProject=research-<slug>`、`research.step seq=1` |
| 5 | A：詳情／fsm／events／list | 200 · 9／26／12／7 ms | fsm 含 `retryHistory.gates{SCG_VALIDATION,PR_REVIEW,RTM_VERIFY}` 與 `humanReturnCount:0`；現態 `AGENT_LOAD` |
| 6 | A：`POST stages/research` | **202** · 93 ms | SSE ids 2..6；30.6 s 後 `FAILED`／`evaluator_failed`（R8 軸集合不符；見 INT-11），flow 回 `INGESTED/IDLE` |
| 7 | 建專案 B（六軸，議題 `INT docker mock claude gate`） | 201 · 617 ms | |
| 8 | B：`POST stages/research` | 202 · 109 ms | 13.2 s 後 `FAILED`／`no_evidence`（arXiv 803 B 空、GitHub 55 B 零筆、S2 429；見 INT-06） |
| 9 | 建專案 C（六軸，議題 `整合代驗 mock claude Gate 0`） | 201 · 610 ms | |
| 10 | C：`POST stages/research` | **202** · 93 ms | SSE ids 2..17 連續無缺漏；約 17 s 後 `EVIDENCE_READY`（含 6 `research.source`＋4 `research.evidence`）；run `SUCCEEDED` |
| 11 | C：`GET sources`／`evidence` | 200 · 11／22 ms | 6 來源；矩陣 v1、4 列、`counterEvidence` 4、`searchLog` 8；矩陣 sha256 ＝ 容器內 `evidence_matrix.md` 的 sha256sum |
| 12 | C：`GET events` 分頁 | 200 · 12 ms | `afterSeq=0&limit=5` → 5 筆、`truncated:true`、`nextSeq=5`；續抓 12 筆、`nextSeq=17`；`limit=501` 被夾成 500 仍 200 |
| 13 | C：`POST stages/draft` | **202** · 109 ms | SSE ids 18..24（`Last-Event-ID:17`）；3.4 s；`prd/versions` v1 `v0.1.0-draft`（AGENT，15,344 B，refs E-001..E-004）；flow `studio/DRAFTING/IDLE`、FSM `SPEC_DRAFTING` |
| 14 | C：`GET review-rounds`／`{1}`（未審前） | 200 空陣列／404 `research_not_found` | 無進行中輪列（D-57） |
| 15 | C：`POST stages/review` | **202** · 170 ms | SSE ids 25..36；11.6 s；第 1 輪 `weightedScore` 原文 **`79.90`**、`minDimensionScore 70`、`REVISE`、`fsmGateResult FAIL`、`fsmRetryCount 1`、5 缺陷、`triggerKind MANUAL`；FSM `SPEC_DRAFTING`、`currentCount 1` |
| 16 | C：`POST stages/iterate` | **202** · 93 ms | SSE ids 37..56；15.2 s；REVISE→`v0.2.0-draft`；第 2 輪 **`90.30`** PASS、min 88、`fsmGateResult PASS`、`fsmRetryCount 0`、`triggerKind AUTO`；第 1 輪 4 缺陷轉 FIXED（`fixedIn v0.2.0-draft`）、D-1-002（P3）維持 OPEN；FSM `HUMAN_PENDING`、flow `GATE0_PENDING/WAITING_HUMAN`、`humanPending.count 1` |
| 17 | C：approve 負向 | VIEWER 403／OPERATOR 403 `ACCESS_DENIED`、匿名 401 `UNAUTHENTICATED`；摘要不符 422 `digest_mismatch`（48 ms，`details.files[]` 列鍵與現值）；零鍵 422 `invalid_request`；`prdVersion=1`（非 head）409 `review_not_passed`（`details.headVersion 2`）；摘要格式錯／空本文 422 | 見 INT-13 |
| 18 | C：approve（ADMIN，成功） | **200** · 497 ms | `stage=Gate-0`、`specDocDigests` 四鍵、`fsmState=SPEC_FROZEN` |
| 19 | C：二次 approve | 409 `fsm_state_conflict` · 39 ms | `details.current_state=SPEC_FROZEN, expected_state=HUMAN_PENDING` |
| 20 | C：核准後狀態 | — | flow `route/FROZEN/IDLE`；`prd/versions` v3 `v1.0.0` BASELINE（HUMAN／admin，sha256＝v2）；容器 `PRD-v1.0.0.md` 與 `PRD_draft.md` 位元組相同；DB `research_gate_decisions` 1 列 GATE0 APPROVED／decided_by `admin`；events 1..67 連號 |
| 21 | C：`GET records/audit` | 200 · 10 ms | R1=1 R2=12 R3=2 R4=3 R5=2 R6=1 R7=0 R8=0 R9=5 R10=0 R11=0 R12=0 R13=15 R14=10；`missing=[R7,R8,R11]`（符合 ⚖3） |
| 22 | C：`POST reconcile`（operator／admin） | 200 · 51 ms | `consistent:true`、六項 `ok`；但 `checks[].name` 全為 `""`（INT-01） |
| 23 | C：凍結後寫入 | `PUT prd`／`stages/review`／`return` 皆 409 `spec_frozen` | `details.flowStep=route, flowPhase=FROZEN` |
| 24 | B：archive／restore | 200／200 · 48／38 ms | archive 後 list 不含；restore 後回列；A、C 同（61／41、40／34 ms） |
| 25 | 重複 slug | 409 `slug_in_use` · 26 ms | `details.slug` |
| 26 | 輸入閘 9 變體（缺 topic／501 字／depth FAST／四層全關／industry 開／bad slug／recency 4／axes 7 項／hint 列舉外） | 皆 **400**（`industry` 為 `layer_unavailable`）· 9～15 ms | 前後 DB `research_projects` 列數不變（3＝3） |
| 27 | D：`PUT prd` 驗證 | 過期 `baseVersion` 409 `prd_version_conflict`（36 ms）；空／含 NUL 422；合法 **201**（operator，53 ms；v3 `v0.3.0-draft` HUMAN） | |
| 28 | D：兩個併發 `PUT`（同 `baseVersion=3`） | 一個 201（v4）、一個 409 `prd_version_conflict` | DB 版本號唯一 |
| 29 | D：`return`（缺理由／空白） | 422 `invalid_request` | |
| 30 | D：`return` ×3（ADMIN） | 200 · 325／360／344 ms | `fsmRetryCount 1／2／3`；第 3 次 `escalated:true`；FSM 前兩次維持 `HUMAN_PENDING`（`currentCount` 1／2）、第 3 次現態 **`ESCALATION`**（`rule_id R-9.1`；非 `AUTO_RECOVERY_ATTEMPT`）；`humanReturnCount 3`；flow `studio/REVISING/ESCALATED` |
| 31 | D：ESCALATION 下 | `review`／`iterate`／`return` 409 `escalated`（`details.recovery{target,powershell,posix}`）；`revise afterEscalation:true` 409 `fsm_state_conflict`（`current_state ESCALATION`）；`draft` 409 `stage_conflict`；`approve` 409 `review_not_passed`；`tcs-draft` 502 `not_implemented` | 見 INT-14 |
| 32 | D：`reinit generation:next` | OPERATOR 403 `research_write_forbidden`（11 ms、決定列數不變）；ADMIN 缺理由 422；ADMIN 200 · 695 ms | `fsmProject=research-int-p0-pass-d-g2`、`fsmGeneration 2`、`gateDecisionId`；新鍵現態 `AGENT_LOAD`、`humanReturnCount 0`、`retryHistory.gates` 歸零；DB 加 `ABANDON_KEY／ABANDONED`（`fsm_project`＝舊鍵、`fsm_state_after ESCALATION`）；舊世代輪列仍 `fsmGeneration 1` |
| 33 | 併發 stage | 另一專案啟動 409 `stage_conflict`（`details.cause=max_concurrent_runs, limit 1, active 1`）；同專案再啟動 409 `stage_conflict`（`activeStage/activeStageRunId`） | D-67 |
| 34 | `POST cancel`（operator） | 200 · 78 ms | `stoppedRunId`、flow `topic/RESEARCHING/CANCELLED`；之後陷入死路（INT-02）；無進行中時 cancel 冪等（`stoppedRunId:null`） |
| 35 | allowlist | POST 201（35 ms）；Reddit 無條款確認 422 `terms_ack_required`；PATCH `enabled:false`→`true` 皆 200（34／37 ms）；PATCH 帶 `minIntervalSeconds` 422 `invalid_request`（immutable）；host 帶 scheme 422；interval 0 422；未知 id 404 | `audit_log`：4 筆被拒＋8 筆 ADMIN ＝ 12 列，**每個請求恆一列**；成功列 `entity_type=research_allowlist, entity_id=<條目 uuid>`，失敗列 `entity_type=research`；下一個 stage run 的 `allowlist_snapshot` 含 `docs.python.org`（ADMIN）；`research_events` 無 allowlist 事件 |
| 36 | SSE 驗證面 | 無 token 401 `UNAUTHENTICATED`；壞 `access_token` 401 `TOKEN_INVALID`；未知專案 404；VIEWER 200 | `?access_token=` 與 `Authorization` 兩種皆可 |
| 37 | 清場 | 7 專案全 archive（`archived_at` 皆已寫、列保留）；allowlist 探針條目 `enabled=false` | list 非封存＝0 |

### 1.1 SSE 真串流與 `Last-Event-ID`（真標頭）

- 研究／草擬／審查／迭代四種 stage 的事件皆經真 SSE 收到，ids 全程連續、無重複（C：2..17、18..24、25..36、37..56；D／E／F 同）；每 15 s 一個 `heartbeat`（無 `id:`）。
- 重連補送：`Last-Event-ID: 20` → 重播 21..63（44 筆，連續、0 重複、0 缺口）；`Last-Event-ID: 57`（以 `Authorization` 標頭認證）→ 58..63；不帶 → 不重播、只送後續事件。
- `research.replay_gap` 未驗（需緩衝逾期情境）。

### 1.2 RBAC 矩陣（真機；有 token 的三角色＋匿名）

| 端點群 | VIEWER | OPERATOR | ADMIN |
|--------|--------|----------|-------|
| 13 個 GET（capabilities、list、detail、events、sources、evidence、prd versions／單版、review-rounds／單輪、fsm、records/audit、allowlist） | 200 ×13 | — | 200 |
| POST projects／stages／cancel／reconcile／archive／restore／reinit（重試）、PUT prd | 403 `ACCESS_DENIED` | 200／201／409（依狀態） | 同 |
| POST approve／return、POST／PATCH allowlist | 403 `ACCESS_DENIED` | **403 `ACCESS_DENIED`** | 200／201 |
| POST reinit `generation:next` | 403 `ACCESS_DENIED` | **403 `research_write_forbidden`**（服務層；Bridge 請求 0、決定列不增） | 200 |
| 匿名 | 401 `UNAUTHENTICATED` | | |

## 2. UI 真機（Playwright library API，chromium，1440；真棧 `http://localhost`；未改 repo、未寫 spec 檔）

腳本在 `INT\ui\*.mjs`（共用 `common.mjs`）；`E2E` README 要求的 `--output` 不適用（未用 test runner，截圖只落 `INT\ui\`）。

| 場景 | 結果 |
|------|------|
| 登入（UI）、側欄「研發工作流」`aria-current=page`、`/research` 清單 | PASS；清單列出新專案與徽章（C「Gate 0 已核准」，其餘「進行中」）；空狀態顯示「還沒有任何研究專案」＋新建入口、不自動跳轉；「查看已封存」可復原（UI 復原 RP-0003 成功） |
| 390 px | PASS：底部 Tab 為 儀表板／專案管理／執行中心／監控中心／系統設定，**不含**研發工作流（`mobile:false`；截圖 `list-390.png`） |
| 工作區（C）步驟列、議題面板、動態欄 | 步驟列 5 步（`已完成／已完成／進行中／待做／待做`）；動態欄 `data-connection=open`「即時連線中」、66 筆事件 `data-seq` 連續；證據矩陣表 4 列（摘要「矩陣 v1 · 共 4 列 合格 4 列 UNANCHORED：0 筆 授權待查：3 列」）；技術優缺點矩陣可切；**議題範圍欄位恆「—」（INT-03）** |
| PRD 工作室（C，凍結） | 目錄 58 項；編輯／預覽／Diff 三模式；Diff v1→v2「新增 14 行、刪除 5 行（相同 342 行）」且前綴為文字（`+ 新增`／`- 刪除`，非僅色彩）；預覽的 Mermaid **渲染為 SVG**（無 error／timeout）、預覽無 script／iframe／object／embed；Gatekeeper：`90.30 ／ 門檻 85.00`、最低維度 `88 ／ 地板 60`、雷達圖＋等效文字表（架構 92 商業 90 QA 88 資安 91）、4 缺陷卡；凍結橫幅與「前往分流」 |
| Gatekeeper 剩餘預算與送審／迭代（G） | UI「送審」→ 四審查者進度面板 → 第 1 輪 `79.90`、「剩餘預算 2 次」→ UI「一鍵自動迭代修正」→ 第 2 輪 `90.30` → `GATE0_PENDING`，核准鈕 ADMIN 可用 |
| 角色（F，GATE0_PENDING） | VIEWER：新建／封存／核准／退回／對帳全停用、`title=權限不足（唯讀角色）`，編輯器唯讀，無「研究來源設定」；OPERATOR：核准／退回停用 `title=權限不足：這個動作僅 ADMIN 可用`、對帳可用、無「研究來源設定」；ADMIN：核准鈕可用 |
| Gate 0 核准（UI，F） | 對話框摘要 `v0.2.0-draft（第 2 版）／sha256 前 8 碼 835f732a／90.30／最低 88／未結缺陷 4`、四個凍結檔；按「核准並凍結」→ 911 ms 成功 toast；DB 1 列 GATE0 APPROVED（`admin`）；UI 轉凍結；核准後 Gatekeeper 出現「已過期」徽章（INT-09） |
| ESCALATION（E） | 第 3 次退回（API）於頁面開啟時到達 → 341 ms 彈出「審查已升級，需要人工處理」；區塊含狀態機現態 `ESCALATION`、各輪分數（第 1 輪 79.90、第 2 輪 90.30）、未結缺陷 4、PowerShell／POSIX 兩段可複製恢復指令（`複製`×2）；按鈕只有「我已恢復，繼續（僅一次機會）」與「換世代」，**沒有恢復動詞按鈕**；「我已恢復」在仍 ESCALATION 時顯示說明（API 409 `fsm_state_conflict`，不寫 FSM）；OPERATOR「換世代」停用（title）；ADMIN「換世代」→ 對話框（理由未填時確認鈕停用＝二次確認）→ 成功，UI「狀態機世代 2」 |
| 編輯儲存（E） | 在編輯器加一行→「有尚未儲存的修改」→儲存 → v3 `v0.3.0-draft`（人工）→ 舊審查標「已過期」，核准註記「審查已過期：PRD 已有新版本（第 3 版），審查的是第 2 版，請重新審查」 |
| 新建（UI，G） | 「新建研究專案」對話框：slug 自動 `mock-claude-gate-0`；空議題擋下「必填，最多 500 字」；建立後導向工作區；`scope`＝`inScope:[議題]`、六軸、`recency 3`；「啟動深研」停用並顯示「容器模式只跑 mock claude 的驗收；真研究限本機模式」；`?step=deliver`／`?step=route`（超前）導回 `?step=topic`；步驟 3 為占位面板（C `?step=route`：「第 3 步：分流 本步驟於後續階段提供」） |
| 研究來源設定（ADMIN） | 對話框列 6 列（5 ENV「不可變更」＋1 ADMIN「停用」）；OPERATOR／VIEWER 無入口 |
| 焦點 | 兩個對話框（研究來源設定、新建）：開啟時焦點進入、Tab×12 不外洩、Esc 後焦點回觸發鈕（PASS） |
| 對帳（UI） | **D（FSM 對映 drift）**：橫幅「檔案與資料庫不一致」但只列「`flow（）`」，沒有「狀態機的現態與流程游標的對映不合」警示；**C（注入檔案漂移）**：列出 `01_specs/PRD-v1.0.0.md（）`、`00_research/evidence_matrix.md（）`×2，標籤為空、無資料庫／檔案摘要（INT-01、INT-10）；還原檔案後 `consistent=true` |
| 失敗／取消狀態（B、A） | UI 無失敗橫幅，B 只顯示「目前：議題已受理（閒置）」、A 顯示「研究中（已取消）」（INT-04、INT-02） |

### 2.1 axe 掃描（WCAG 2.0／2.1 A／AA；viewport 暫拉到 2400 高；reduced-motion）

23 份結果檔皆 **0 違規**（`INT\ui\axe-*.json`）：清單 1440／1000／600／390／空狀態；議題步（C）1440／1000／600；PRD 工作室（C）1440／1000／600、Diff 有差異列；工作室 F（GATE0_PENDING）、E（ESCALATION）、E（儲存後）、G（失敗輪）；失敗態 A、B 議題步；對話框：研究來源設定、新建、Gate 0、換世代、ESCALATION 彈窗。水平溢出：清單／議題／工作室在 1440、1000、600 與清單在 390 皆 `scrollWidth ≤ clientWidth`。Studio 在 600 為分頁籤（`目錄／編輯器／審批`）。
註：早期截圖（`topic-C-*`、`studio-C-edit／preview`、`*-1000`、`*-600`）為單一視窗高；其後截圖已改暫拉高視窗取全頁。

### 2.2 SSE 於 UI 的行為

- 動態欄重新載入：17 筆（G）重載前後 `data-seq` 序列完全相同（由 DB 重建）。
- Playwright `context.setOffline(true)` **不會切斷已建立的 EventSource**（16 s 離線期間 `data-connection` 全程 `open`，UI＝DB＝17 筆）——TCS AT-960-22-4 規定的「離線再上線」手法因此不會真的測到重連（INT-12）。
- 改以「載入前 `route.abort` 串流」：狀態顯示「重新連線中…」、期間 draft 的 7 筆事件 UI 未顯示；解除封鎖後自動重連（無須按「重新連線」；狀態於頁面載入後 24.3 s 由 `reconnecting` 轉 `open`），事件補齊，最終 UI 25 筆＝DB 25 筆、連續；重連後即時事件（reconcile）269 ms 內到畫面。

## 3. DB 核對（`docker exec aisdlc-pg-primary psql …`；帳密只在指令內）

- 起始：13 張 research 表皆 0 列、Flyway 至 v18 成功。終了（取樣於 UI 場景 s10 之後；其後 UI 復原／再封存另增數筆事件）：projects 7、events 308、artifacts 48、stage_runs 25、sources 30、fetches 73、evidence_items 20、prd_versions 14、review_rounds 8、review_scores 32、review_defects 36、gate_decisions 10、allowlist_entries 1。
- 每專案 `research_events.seq` 連號（`max-min+1=count`）且 `research_projects.last_event_seq = max(seq)`（7／7）。
- 25 筆 stage run 皆有 `playbook_sha256`、`config_sha256`、`prompt_manifest`（25／25）；`execution_runs` 0 列（研究 run 不進執行表）。
- 觸發器在真庫生效（皆在 `begin…rollback` 內試，前後列數不變）：`research_events` UPDATE、`research_review_rounds` DELETE／UPDATE → `為 append-only`；缺陷 `FIXED→OPEN` 被擋；來源 `verification V2→V1` 被擋；`research_projects` 改 slug／DELETE、allowlist 改 host 被通用守衛擋。（T3 非線索來源 CHECK 的試插因我的 INSERT 缺 `first_fetched_at` 先撞 NOT NULL，**未得結論**。）
- 編譯結果（容器 `/workspace/<runId>/config.yaml`，23 份）：`--permission-mode acceptEdits --allowedTools Read,Glob,Grep,Edit(//workspace/my-project/<slug>/**)`（REVIEW 為 `…/02_governance/reviews/round-<k>/**`）；0 份含 Bash／PowerShell／Task／Agent；run 檔無 `BRIDGE_`／`SDD_`／`TOKEN` 字樣；`step_timeout_seconds 600`（D-75）；步驟 prompt 只寫「先 Read `.prompts/<role>.md`」；四審查者在同一 REVIEW run 依序。

## 4. V 系列判定（TCS §6.2；不是 AT）

| 項 | 判定 | 證據／原因 |
|----|------|-----------|
| V-R2 repo 外工作區不載入根 CLAUDE.md 與 hooks | NOT-EVALUABLE | 需本機真 `claude -p`；容器 `claudeCli.ok=false` |
| V-R1 `--allowedTools` 與 WebFetch 語法／無提示行為 | NOT-EVALUABLE（真 claude） | 真棧只能驗「編譯結果」：見 §3 編譯結果，與 D-74 追認形態一致 |
| V-R3 命令列長度與 `.prompts` 參照法 | NOT-EVALUABLE（Windows 命令列） | 真棧可見參照法：步驟 prompt 僅參照句；`.prompts/draft.md` 22,116 B、`research.md` 14,434 B |
| V-R5 無 `MINIMAX_API_KEY` 時 evaluator 失敗的重試 | NOT-EVALUABLE（本棧有金鑰環境變數，值已遮蔽）；另得觀察 | evaluator 失敗 → `RETRYING attempt 2`（`max_retries 1`）→ ESCALATION → stage `FAILED/evaluator_failed`；**ESCALATION 時引擎呼叫外部 MiniMax**（INT-07） |
| V-R4 httpx 釘 IP／SNI | NOT-EVALUABLE | 本機假伺服器項（BR-B）；真棧只見對 arXiv／GitHub 的真連線成功 |
| V-R9 官方速率數值 | PARTIAL | 真棧 allowlist 值 3／3／3／60／3 s 與 §5.1 一致；S2 未帶金鑰實測 429 `RATE_LIMITED`；SE 官方頁已由主控 `08f8cfea` 落證 |
| V-R6 新狀態目錄首次 `show` 建檔、第 3 次 FAIL 現態 | **PASS（真 CLI，容器 LATEST v0.30）** | audit `sdd_cli show ok rc 0`→`transition`×2→`AGENT_LOAD`；D、E 各一次人工退回×3 → `ESCALATION`（`R-9.1`、`retry_count 3 ≥ 3`） |
| V-R7 `spec-frozen --stage Gate-0 --digest --root` | **PASS（真 CLI）** | C、F 各一次；`spec_docs` 為相對路徑四檔；`spec_doc_digests` 與 sha256sum、API、DB 逐位相同 |
| V-H2 真實議題端到端（真 claude） | NOT-EVALUABLE | 需本機模式 |
| V-B1 bundle 增量 | NOT-EVALUABLE（非本棒） | |
| V-H1 掌舵者離開再回來（sid／line） | NOT-EVALUABLE（只掌舵者） | 構造情境佐證：深連結、重載動態欄相同（不充當 V-H1） |
| V-D1 Docker 全棧兩路徑 E2E | **PARTIAL** | 路徑 B 全綠（API＋UI）；路徑 A（fail3）未跑（容器環境固定 pass、禁止重建）；以「人工退回×3→ESCALATION」取得 ESCALATION 態（FSM 與 UI 皆驗），但 DB 的 R6 非零，與 AT-960-22-2 的 R 類期望不同 |
| V-C1 Architecture 5.4 檢查表 | NOT-EVALUABLE（SCG-4 報告 §B） | |
| 掌舵者目視項 | NOT-EVALUABLE | 1440／1000／600 截圖已附（Diff 前綴、Mermaid、ESCALATION 區塊）；Reddit 條款文案未驗（未新增 Reddit 條目） |
| macOS／Linux 主機 | 未驗 | 本棒為 Windows 主機＋Linux 容器 |

「各包交卷聲明的未對真 Bridge 驗」四項：approve 成功路徑 **PASS**（API 與 UI）、SSE 真串流 **PASS**、`Last-Event-ID` 真標頭 **PASS**（§1.1）、allowlist PATCH `false→true` **PASS**。

## 5. 缺陷清單（P1～P4）

### P2

**INT-01 對帳結果欄位名與簽章欄位在 console-api 與 Bridge 之間錯位**
- 現象：`POST …/reconcile` 回的 `checks[*].name` 恆為 `""`；漂移列的 `expectedSha256`／`actualSha256` 不見。UI 的對帳橫幅因此：檔案漂移列標籤為空「（）」且無摘要；FSM 對映漂移被當成檔案漂移（只列 `flow（）`），`fsm-mapping-warning` 永不顯示（`lib/domain/research.ts:533` 靠 `name === "fsm_flow_mapping"`）。
- 定位：`AgentConsole/backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/research/ReconcileResultDto.java:48`（讀 `name`）、`:44-45`（讀 snake_case `expected_sha256`／`actual_sha256`）；Bridge `AgentConsole/engine-bridge/app/research/gates/reconcile.py:63`（`_drift` 輸出 camelCase）、`:72-77`、`:84-92`（以 `id` 為鍵）。
- 重現：任一專案 `POST /api/v1/research/projects/{id}/reconcile` → `checks[0].name==""`；對照容器內直打 Bridge `:reconcile` 得 `{"id":"fsm_flow_mapping",…}`。後端 IT 的 MiniBridge 用 `name`，所以測不出。

**INT-02 取消 research stage 後專案卡死（無任何 API／UI 可恢復）**
- 現象：`POST cancel` 只把 stage run 標 `CANCELLED`、游標 `flow_status=CANCELLED`，`flow_phase` 留在 `RESEARCHING`；之後 `POST stages/research` 一律 409 `stage_conflict`（`details.unmet=[{rule:phase, expected:[INGESTED,EVIDENCE_READY], current:RESEARCHING}]`）；`reinit`（重試）409（`flowStatus CANCELLED`）；archive／restore 不改游標。
- 定位：`AgentConsole/engine-bridge/app/routers/research.py:827`（cancel 只寫 status）、`:555`（research 前置 phase 集合）。
- 重現：A 專案：`stages/research`（202）→ 2 s 內 `cancel`（200）→ `stages/research` → 409。（失敗的 run 則游標回 `INGESTED`，可重試。）

**INT-03 專案範圍欄位在真棧恆顯示「—」**
- 現象：API `scope` 內鍵為 snake_case（`in_scope`、`tech_stack`、`out_of_scope`、`recency_years`、`applicability_axes`），UI `readResearchScope` 讀 camelCase；議題面板「納入範圍／排除範圍／目標技術棧／文獻年限與適用性軸」全空（只有四個 `layers` 單字鍵正確）。
- 定位：`AgentConsole/frontend/lib/domain/research.ts:1217-1221`；顯示 `components/domain/research/TopicPanel.tsx:182-193`。截圖 `INT\ui\topic-C-feed-1440.png`。Vitest 夾具為 camelCase，所以測不出。

**INT-04 研究失敗在真棧不顯示**
- 現象：Bridge 把失敗的 stage run 的游標寫成 `IDLE`＋`flowDetail=<exit_reason>`（`research.step {flowStatus:"IDLE", flowDetail:"no_evidence"|"evaluator_failed"}`；`gates/reconcile.py:6-7` 文件亦載「FAILED 只用於初始化失敗」），UI 的 `researchFailureOf` 只認 `flowStatus==="FAILED"`，於是「研究未完成：原因／續跑」「研究失敗／重試」橫幅永不出現；使用者只看到「議題已受理（閒置）」（AC-R2P-04-5「不得顯示為完成」且須顯示原因）。
- 定位：`AgentConsole/frontend/lib/domain/research.ts:1,180`；Bridge 游標寫入同 `app/research/orchestrator.py` 的失敗收尾。截圖 `INT\ui\topic-B-failed-state-1440.png`、`topic-A-failed-state-1440.png`。

**INT-06 Docker E2E 非 hermetic：研究 stage 的前置抓取連真外網，結果取決於外部**
- 現象：mock-only 容器內 `_prefetch` 仍對真 arXiv／Semantic Scholar／GitHub 發請求（Bridge 日誌 `bridge.research.fetch host=export.arxiv.org outcome=OK status=200`、S2 `RATE_LIMITED 429`、GitHub `OK`）；議題 `INT docker mock claude gate` 零命中 → stage `FAILED/no_evidence`（13 s）；議題 `…mock claude Gate 0` 才有命中而成功。離線或限流環境下 Docker E2E 必紅；S2 未帶金鑰的 429 還讓每次研究多耗約 12 s。TCS §5.3「任何 AT 中都不被連線」被違反。
- 定位：`AgentConsole/engine-bridge/app/research/orchestrator.py:643-647`（`_research` 先 `_prefetch`）、`:664-706`（真抓取；`:705-706` 無來源即 `no_evidence`）。
- 建議：mock-only／劇本模式下略過或改用夾具抓取（或 compose 設空 `BRIDGE_RESEARCH_FETCH_ALLOWLIST` 並讓劇本模式容忍零來源）。

**INT-07 stage 升級（ESCALATION）時引擎對外呼叫 MiniMax**
- 現象：evaluator 失敗重試後進 ESCALATION，引擎的決策／演化器呼叫 `https://api.minimax.chat`（`autoclaude.decision: Minimax API 暫時失敗（attempt 1/3）… HTTP 301`、第 3 次後回退規則引擎），失敗路徑多耗約 11 s，且是對外的資料出口（payload 未檢視）。成功的 run 0 次呼叫。研究 stage 的編譯 config 沒有任何 brain／evolution 旗標，且 Bridge 容器環境帶 `MINIMAX_API_KEY`（值已遮蔽）。
- 定位：容器內 `/workspace/24d9aac6-b015-4b93-ab40-2859bef4b9d1/engine-1.log` 第 32／40／48 行；`AgentConsole/engine-bridge/app/research/**` 全無 `MINIMAX`／`kernel_brain` 字樣（研究 run 沿用通用 `app/runner.py` 的環境傳遞，`:980-992`）。
- 建議：研究 run 編譯時釘關 Brain，且不把 `MINIMAX_*` 放進研究引擎子行程環境（對齊 W-R8「環境隔離」）。

### P3

**INT-05 人工存 PRD／換世代後，對帳誤報 `fsm_flow_mapping` drift**
- `save_prd` 固定寫 `DRAFTING`（`app/routers/research.py:519`），但對映表 HUMAN_PENDING 只准 `GATE0_PENDING`／`REVISING`、AGENT_LOAD 只准 topic 步（`app/research/gates/reconcile.py:23-28`、`:21-22`）。重現：D 在 HUMAN_PENDING 時 `PUT /prd` → reconcile `consistent:false`（`FSM_FLOW`）；`reinit generation:next` 後（FSM `AGENT_LOAD`、flow `studio/REVISING`）同樣 drift。使用者的正常路徑（Gate 0 前改稿、換世代）因此出現「不一致」警示。與 API-RP-09（回 DRAFTING）與 PRD §5.1.1 M1／⚖26（合法相態）互相矛盾，需裁決一邊。

**INT-08 Bridge capabilities 鍵集合與契約 §2.1 不符**
- Bridge 回 `{mode, root, db, claude_cli, gh_cli, git, web_layer_enabled, scaffold_templates}`（`app/research/settings.py:55-56,190-210`，且 TCS AT-960-2-7 逐字釘這八鍵）；契約 §2.1 要 `sdd_root、research_root、scaffold_root、repo_writable、fetch_hosts`。console-api 因此回 `fetchHosts:[]`（即使已新增 ADMIN 條目）、`repoWritable:false`、`scaffoldRoot:null`。TCS 與契約互相矛盾；目前前端無 `fetchHosts` 消費者，但 `queries.ts:1459` 註解以為會重抓。

**INT-09 凍結後 Gatekeeper 把「通過」的審查標為「已過期」**
- 核准後 head 變為 v3（BASELINE，與 v2 同 sha256），`stale = latest.prdVersionNo !== headNo`（`components/domain/research/GatekeeperPanel.tsx:511`）恆真 → 「第 2 輪 通過 已過期」。截圖 `INT\ui\studio-C-preview-1440.png`、`studio-F-after-approve-1440.png`。建議以 sha256 相等判定或凍結後不顯示。

**INT-10 對帳 `prd_sha256` 項把四個凍結檔全標 kind=PRD，與 `evidence_matrix` 項重複計入**
- 核准後 `prd` 清單取 `frozen_digests` 全部（`app/research/orchestrator.py:1085-1096`）：改動 PRD＋證據矩陣兩個檔 → `driftCount=3`（證據矩陣出現在 `prd_sha256` 與 `evidence_matrix` 兩項）。

**INT-11 mock 劇本固定要求議題軸＝全六軸，少於六軸即 R8 失敗（約 30 s）**
- 夾具 `engine-bridge/tests/fixtures/research/scripts/content/evidence_items.json` 的 `f5` 為六軸；專案軸取兩個即 `[R8] f5 的鍵須恰等於議題軸集合` → `evaluator_failed`（重試一次＋INT-07 的對外呼叫共約 30 s）。UI 建立預設六軸所以不受影響；API 直呼 E2E（TCS AT-960-22-x）必須建六軸，README／TCS 未載明。

### P4

**INT-12 AT-960-22-4「離線再上線」手法對已建立的 EventSource 無效**：`setOffline` 不切斷既有串流（觀察：離線 16 s 期間連線狀態全程 `open`），該 AT 會空過。建議改為載入前 `route.abort` 串流或伺服端斷線。

**INT-13 reason 與契約／TCS 的差異（已有 D-72，需勘誤落檔）**：approve 摘要不符回 422 `digest_mismatch`（契約／TCS 為 409 `spec_digest_changed`）；零鍵回 422 `invalid_request`（D-72 寫 `missing_digests`）；`RESEARCH_REASONS`（`lib/domain/research.ts`）無這兩個 reason，UI 退回顯示伺服器訊息。

**INT-14 其他小項**：①`stages/tcs-draft` 回 502 `not_implemented`（Bridge 501 被映成 502）；②PATCH 不存在的 allowlist id 回 404 `research_not_found` 訊息「研究專案不存在或已刪除」；③Bridge 要求 `scope.in_scope` 至少 1 項（契約 §1.2 只寫 ≤20 項；UI 恆送 1 項）；④ESCALATION 恢復指令是容器內路徑（`/sdd/AISDLC_SDD_v0.30`、`/usr/local/bin/python3.11`），Docker 模式的使用者需自行 `docker exec`；⑤工作室編輯器即時預覽把 `<!-- r2p:section=N -->` 錨點當文字顯示；⑥清單徽章把失敗／取消的專案也標「進行中」。

## 6. 對 TCS／RTM「E2E 驗證」欄的建議回填

- AT-960-22-3（路徑 B）：**真棧 PASS**（API＋UI；證據 §1 步驟 9～22、§2 Gate 0 核准）。`research-docker.stack.ts` 尚未存在於 repo，本報告為手動等價執行，非該 spec 的輸出。
- AT-960-22-2（路徑 A）：**未驗**（fail3 無法在不重建容器下切換）；ESCALATION 呈現（AC-960-15 UI 側）以替代路徑驗過。
- AT-960-22-4：**部分**（Last-Event-ID 真標頭與 UI 補齊／重載重建已驗；規定手法無效，INT-12）。
- AT-960-22-5：**PASS**（側欄、390 Tab、空狀態、深連結導回、占位面板、mock-only 停用、VIEWER 唯讀、ADMIN 設定／OPERATOR 無入口）。
- AT-960-22-E-1：**PASS**（以 library 等價腳本；23 次 axe 零違規、四寬度無溢出、焦點陷阱與歸還）。
- 契約／AC 面：AC-960-4（輸入閘、重複 slug、封存復原、入庫完整率）、AC-960-5（RBAC）、AC-960-7（編譯最小授權）、AC-960-9（矩陣 sha256＝檔案）、AC-960-10（事件連號、重播）、AC-960-12（W100 兩位小數、前置、缺陷狀態）、AC-960-13／14／15（FSM 預算、核准、退回、ESCALATION、換世代）真棧通過；AC-960-21（對帳）**受 INT-01／05／10 影響，不宜標通過**。

## 7. 誠實劃界

- 路徑 A（fail3）未跑；真 `claude` 相關 V 項（R1／R2／R3／H2）未驗；`BRIDGE_DB_DSN` 缺、Bridge／PG 斷線、outbox 重放、`research_write_disabled` 503、`bridge_unreachable`／`bridge_timeout` 502／504、`research.replay_gap` 皆未驗（需停服務或環境變更，禁止）。
- Docker 內結果含**真外網**依賴（見 INT-06）：同一議題在別的時間／網路下可能得到不同的研究 stage 結果；本報告成功路徑用的議題 `整合代驗 mock claude Gate 0` 在驗證當下有命中。
- 檔案漂移注入是在容器內對我自己建立的專案工作區 append 一個位元組後立即還原（`sha256sum` 驗證還原）；DB 觸發器探針皆在 `begin…rollback` 內並以列數前後比對。
- 證據明細（`evidence-detail`）UI 點列開啟面板未驗到（點第一列後無 `evidence-detail` 節點）；Reddit 條款文案與目視項未驗；T3 非線索 CHECK 試插無結論。
- 殘留：Bridge 容器 volume `/workspace/my-project/` 下留有 7 個測試工作區（`int-p0-pass-a|b|c|d`、`int-p0-esc-e`、`int-p0-ui-f`、`mock-claude-gate-0`）與 `/workspace/<runId>/` 引擎 run 目錄；DB 的 7 個專案與 allowlist 探針條目（`docs.python.org`，已停用）依規定保留。無背景行程、無 Playwright 暫存落在 repo；容器全程 healthy。

## 8. 檔案清單（絕對路徑；根＝`C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\245e80aa-71c4-443b-b8fe-d59f87a9f0e8\scratchpad\r2p\qa\int\`）

- 報告：`INT-P0-DockerMockE2E-20261103.md`（本檔）；進度：`progress.md`。
- 工具腳本：`lib.ps1`、`sse_stage.py`、`drive_to_gate0.ps1`、`ui\common.mjs`、`ui\s1_list.mjs`、`s1b_focus.mjs`、`s2_workspace.mjs`、`s4_roles_approve.mjs`、`s5_escalation.mjs`、`s7_create_sse.mjs`、`s8_sse_blocked.mjs`、`s9_misc.mjs`、`s10_budget_iterate.mjs`、`s11_failed_states.mjs`、`s12_empty_nav.mjs`、`s13_mermaid.mjs`。
- SSE 逐行日誌：`sse-A-research.log`、`sse-B-research.log`、`sse-C-research.log`、`sse-C-draft.log`、`sse-C-review1.log`、`sse-C-iterate.log`、`sse-C-replay-lei20.log`、`sse-C-replay-lei57-hdr.log`、`sse-C-fresh.log`、`sse-viewer-sse.log`、`sse-projectD|E|F-{research,draft,review,iterate}.log`、`drive-E.log`、`drive-F.log`、`approve-C-response.json`。
- 截圖（50 張，`ui\`）：`list-admin-1440|1,000|600.png`、`list-390.png`、`list-empty-state-1440.png`、`list-archived-view-1440.png`、`list-after-create-1440.png`、`list-viewer-1440.png`、`list-operator-1440.png`、`allowlist-dialog-admin.png`、`create-dialog-1440.png`、`topic-C-feed|evidence-table|evidence-detail|proscons-1440.png`、`topic-C-1000|600.png`、`topic-A|B-failed-state-1440.png`、`topic-G-new-mock-only|sse-blocked|fallback-events|after-reconnect|after-offline|after-reload-1440.png`、`studio-C-edit|preview|diff|diff-v1-v2-1440.png`、`studio-C-1000|600.png`、`mermaid-block-C.png`、`studio-D-reconcile-ui-1440.png`、`route-C-reconcile-drift-ui-1440.png`、`studio-E-before-escalation|escalation-popup|escalation-section|recover-notice|reinit-dialog|after-reinit|edited-unsaved|saved-stale-1440.png`、`studio-F-viewer|operator|admin-before-approve|gate0-dialog|after-approve-1440.png`、`studio-G-no-review|review-running|failed-round-budget|gate0-pending-1440.png`。
- axe：`ui\axe-*.json`（23 份）；各場景 verdict 在終端輸出與 `progress.md` 摘要。
