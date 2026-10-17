# API 契約 — Phase 3～6（BRD/PRD 匯入、專案執行、專案監控、系統設定）

**版本**：v1.5（整合輪 115〔`docs/04_planning/AutoSDD_improving_115.md`〕：把 AISDLC_SDD 接成 Console × Bridge × AutoClaude × SDD 的系統迴圈，主控裁決 D-115-01～16、18，契約先行；已與 ADR-XPLAT-016 對齊（處置見 §6.8.6）；v1.4 為 W7 第二批：掌舵者授權的 D-16〔AISDLC_SDD 接入〕、D-17〔深度探針〕、D-18〔待審批清單〕、D-19〔refresh token 撤銷名單〕與 D-20〔文件登記〕；v1.3 為 W7 第一批，D-11〔引擎旋鈕查證與等級 6～10 的 `engineCapabilities`〕與 D-12〔資源使用情況〕；v1.2 為 W5 修復波，W4 獨立 QA 缺陷修復的 22 項主控裁決〔C-1～C-22〕與契約漂移一次回寫；v1.1 為 v1.0〔6df940c〕之後套用 11 項未決問題裁決並回應獨立 Architect 審查的版本）｜**日期**：2026-10-17（v1.5；v1.4 為 2026-10-16）｜**作者角色**：SA／SD
**讀者**：後端開發者（Spring Boot 4.1／Java 21）、前端開發者（Next.js 16）、QA（依本契約驗收）
**機器可讀版**：[openapi-p3-6.yaml](openapi-p3-6.yaml)（OpenAPI 3.1；schema 名稱、欄位與本文一致；兩者衝突以本文為準並回報修正）
**對應需求**：PRD §5.2～§5.5、§7.1.4～§7.1.8、附錄 B；RTM `API-IMP／SGN／EXE／MON／NTF／SSE／SET／ALR／AUT／DAG`（v1.2 增 `API-MON-08`、`API-PRJ-06`、`BR-26`；v1.4 增 `API-ENG-01`、`API-SGN-05`、`API-AUTH-03`）、`US-I／E／M／S`、`NFR-SEC-03／04／05`、`NFR-OBS-01`（v1.2 增 `NFR-9.3-04`、`NFR-9.4-04`；v1.3 不增新 ID，只為 `API-AUT-06` 與 `US-M-10` 的「資源使用情況」補可驗證的情境，見附錄 E 與 E2E-14；v1.4 以 E2E-15 補強 `NFR-OBS-01` 的 FSM 對照，並以 E2E-16 驗 D-17～D-19；v1.5 增 `API-PRJ-07`、`API-SGN-06`、`API-EXE-15`、`API-EXE-16`、`API-ENG-02`、`API-IMP-11`、`API-IMP-12`、`API-PRJ-08`、`BR-27`～`BR-33`、`UI-SDD-01`～`UI-SDD-03`，並以 E2E-17 補強 `NFR-OBS-01` 的 FSM 四源對拍；新列草案見 §6.8.4）

> **本文的使用方式**：開發者照 §1（端點）、§2（SSE）、§3（Bridge 與讀模型）施工；QA 照 §5（E2E 情境）與附錄 B（reason 常數）驗收；§4 讓前端確認「設計稿每個元素有沒有資料來源」；§6 列出本文與其他文件不一致處的裁決。
> v1.1 起沒有待裁決的規格點：v1.0 的 11 項未決問題已由主控裁決（§6.3），審查缺陷已逐條回應（§6.4），其餘章節都是可直接施工的定案。v1.2 的 22 項變動（C-1～C-22）同樣全是主控已定的裁決（§6.5），沒有待裁決的規格點。v1.3 的 D-11、D-12 是主控授權的裁決（§6.6.1）；§6.6.3 列的偏離點主控已於 2026-10-16 確認採方案 A，沒有待裁決的規格點。v1.4 的 D-16～D-20 同樣是主控授權的裁決（§6.7.1）；SA 落筆時提出的 Q1～Q8 八點，主控已於 2026-10-16 全部裁決（§6.7.3 保留決策紀錄），所以本文沒有待裁決的規格點。**v1.5**：D-115-01～16 與 D-115-18 是主控已定的裁決（§6.8.1），SA 初稿的 Q1～Q5 與 S1～S8 已結案（§6.8.3），本文已與 ADR-016 對齊（§6.8.6 A）。§6.8.6 B 列的 14 項「ADR 沒寫、契約暫定」的靜默處中，#1、#2、#3、#6、#14 已由 D-115-18 的五項裁決定案，其餘為契約暫定、待 SD 或 Dev 在落地時確認；Dev-Bridge 等已依 ADR 開工，**契約與 ADR 衝突時以 ADR 為準**，並回寫本文。

**版本沿革**

| 版本 | 日期 | 範圍 | 對應裁決／來源 |
|------|------|------|----------------|
| v1.0 | — | 初版（commit 6df940c） | — |
| v1.1 | 2026-10-15 | 套用 11 項未決問題裁決並回應獨立 Architect 審查 | §6.3、§6.4（AR-01～21、TBC-1～3） |
| v1.2 | 2026-10-15 | W5 修復波：W4 獨立 QA 缺陷修復與契約漂移回寫 | C-1～C-22（§6.5） |
| v1.3 | 2026-10-16 | W7 第一批：引擎旋鈕查證與資源使用情況 | D-11、D-12（§6.6） |
| v1.4 | 2026-10-16 | W7 第二批：AISDLC_SDD 接入、深度探針、待審批清單、refresh token 撤銷 | D-16～D-20（§6.7） |
| v1.5 | 2026-10-17 | 整合輪 115：SDD 迴圈（批次治理、人工閘寫入、FSM 同步、追溯覆蓋、專案綁定） | D-115-01～13（§6.8；`AutoSDD_improving_115.md` §6） |
| v1.5（ADR 對齊） | 2026-10-17 | v1.5 與 ADR-XPLAT-016 對齊：Console 專案為錨（凍結請求無 `binding`）、委派退出語意與回收點、AT 文法與逆向 RTM 歸屬、摘要／權杖／CLI rc／專案名規則等值落定；D-115-18：SDD run 的 `:resume`／`/restore` 也帶權杖（共四個呼叫）、含 `/` 的專案原名降級為已知邊界 | D-115-14～16、18；ADR-XPLAT-016 附錄 A、B（§6.8.6） |

> **v1.5 變更摘要**（逐條對照見 §6.8；整合輪 115，主控裁決 D-115-01～16、18，契約先行；證據表見 §6.8.2；**已與 ADR-XPLAT-016〔下稱 ADR-016，Proposed〕對齊**，逐項處置與仍待確認的靜默處見 §6.8.6；環境契約、CLI 動詞與 rc、摘要、權杖與最小侵入白名單的完整規格一律以 ADR-016 為唯一真相源，本文只引用位置，並在需要機械斷言處逐字引用其值）：
> 1. **SDD 批次（G-01、G-06、G-08；D-115-06）**：Bridge `POST /autoclaude/runs` 增選填頂層 `sdd` 區塊——Bridge 伺服端預檢（凍結、三點摘要、FSM 狀態）後注入 `workflow_type`／`workflow_path`（有 `spec_file` 時是檔案路徑）與引擎環境 `SDD_PROJECT`，外部契約仍不開 `workflow_*`；Console 對「範圍內任務全為 SDD 來源」的批次送 `sdd`，step_id 沿用規格的 `sdd-<場景>-<at id 小寫>`，混合批次不啟用並在 execute 的 201 以 `warnings[]` 出聲（§1.10.6、§3.1.6、§3.4.1）。
> 2. **人工閘寫入（G-09；D-115-01、D-115-03）**：Bridge 新增 `POST /sdd/fsm/{project}:freeze`（唯一的 FSM 寫入動詞，須帶 `X-Bridge-Token`，經 FSMRuntime CLI 子行程）；Console 新增 `POST /api/v1/projects/{id}/sdd/freeze`（approver＝JWT subject；**沒有 `binding` 欄**）。Bridge 原始碼不得直接開寫 `FSM-STATE-*.yaml`；權杖不進引擎子行程（§1.10.2、§3.1.4）。
> 3. **FSM 同步（G-04；D-115-04、D-115-10、D-115-15）**：SDD 批次 spawn 前依預檢表談判並委派進入（`TEST_CONTRACT_NEGOTIATED` 自癒、`AUTOCLAUDE_DELEGATED` 回收點）；`COMPLETED` 與 `CANCELLED` 以 `done` 交還控制權、引擎升級型 `FAILED` 以 `failed` 進 `ESCALATION`（恢復留在 SDD session）；`PAUSED`、額度停機、孤兒不動；`resume`／`restore` 重驗（§3.1.6）。
> 4. **追溯覆蓋（G-05）**：Bridge `GET /autoclaude/runs/{id}/rtm`、Console `GET /api/v1/executions/{runId}/rtm`，一律標諮詢視圖；有無法歸屬 AC 的 AT 時 `fullyCovered=false`（§1.10.3、§3.1.4）。
> 5. **Console 專案為錨（G-07、G-13；D-115-02、D-115-14）**：`projects` 增三欄與部分唯一索引（Flyway V12）；FSM 專案預設＝專案名；路徑 A 匯入帶選填 `targetProjectId` 併入既有專案；新增 `PUT /api/v1/projects/{id}/sdd-binding` 編輯綁定；`GET /sdd/fsm*` 與 `GET /engines/sdd` 依專案帶 `root`，回應加 `phase`、`escalation_history`（尾 5 筆）、`escalation_provenance`、`fsm_project`，ESCALATION 時加 `recovery`；專案名改由 Bridge 的淨化鏡像處理（S-10）（§1.10.4、§1.10.5、§1.10.7、§1.10.8、§3.1.4、§3.1.5）。
> 6. **編譯與路徑 A（S-03、S-04、S-12、G-08；D-115-16）**：`POST /sdd/compile` 增 `spec_file`、`fsm_project`，回應增 `spec_file`、`fsm_project`、`frozen_digest`、`unmapped_at_ids[]`、`warnings[]`，凍結後內容已變更＝409；AT 文法 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`、前兩段＝所屬 AC；路徑 A 補齊 `max_retries`／`maintain_context`／`spec_digest`／`weak_regex`，並收下 `spec_format_version`（§3.1.4、§3.3.2）。
> 7. **新路徑**：console-api 3 個（`POST /projects/{id}/sdd/freeze`、`GET /executions/{runId}/rtm`、`PUT /projects/{id}/sdd-binding`；`OpenApiIT` 路徑 58→61、操作 67→70）、Bridge 2 個（`POST /sdd/fsm/{project}:freeze`、`GET /autoclaude/runs/{id}/rtm`）；E2E-17 與 Bridge 對拍測試清單見 §5。

> **v1.4 變更摘要**（逐條對照見 §6.7；W7 第二批，掌舵者授權的 D-16～D-20，契約先行；證據表見 §6.7.2）：
> 1. **AISDLC_SDD 接入（D-16）**：Bridge 新增 `GET /sdd/fsm`（FSM 專案清單），`GET /sdd/fsm/{project}` 加 `human_pending`／`retry_history`／`rtm_coverage`（§3.1.3）；`GET /health/deep` 加 `sdd` 檢查（§3.1.1）；console-api 新增 `GET /api/v1/engines/sdd`（§1.7.1），監控頁新增「AISDLC_SDD 引擎」卡（§4.3 M-20）與 E2E-15。三項偏離 PRD 的決定（FSM 不走 SSE 改輪詢、分解器只用 `GoalDecomposer`、signoff 與 HUMAN_PENDING 只做語意對映且 Console 唯讀）登記於 ADR-001 D22。
> 2. **深度探針（D-17）**：`autoclaude.healthCheckPath` 預設由 `/health` 改 `/health/deep`（種子預設＋Flyway V11 只改仍等於舊預設的既有列），console-api 探測環改打它、讀取逾時 3→8 秒；探測的「失敗」從此包含「Bridge 行程可達、`git`／`autoclaude`／`workspace`／`db` 任一自檢未通過（503）」；`/health/deep` 新增的 `sdd` 檢查**只當資訊**，不影響 200／503（主控裁決 Q1、Q4；§3.1、§3.1.1、§0.5 V11、附錄 C.5）。
> 3. **待審批清單（D-18）**：新增 `GET /api/v1/signoffs/pending`（§1.8.1），與通知摘要的 `pendingSignoffs` 同一判準、同一組述詞；儀表板「待人工審批」卡改用它（§4.5 G-10）。
> 4. **refresh token 撤銷名單（D-19）**：換新輪替時撤銷舊 token，並新增 `POST /api/v1/auth/logout` 讓登出也撤銷；Redis 優先、不在線退回單實例記憶體並記 WARN（§1.9）。ADR-001 D16 改寫、D23 補記。
> 5. **文件登記（D-20）**：DAG 全螢幕由前端實作（§4.2 E-22）、公告列五項靜態標示與已實作的任務層級範圍（§4.6）；ADR-001 補登 D1 虛擬執行緒範圍、前端覆蓋率口徑與 INFRA 兩項偏離；Architecture 補與 PRD §4.1 目錄樹的差異、Redis 字樣訂正等。專案詳情「匯出」鈕與任務詳情第三張指標卡兩項屬 ADR-002 §4，不在 SA 持有面，文字交主控代填（§6.7.3）。
> 6. **新路徑 3 個**：`GET /api/v1/engines/sdd`、`GET /api/v1/signoffs/pending`、`POST /api/v1/auth/logout`（`OpenApiIT` 路徑 55→58、操作 64→67，§0.8）；其中 `logout` 是 D-19「登出時撤銷」所必需（主控給定的新路徑清單沒有它），主控已裁決視同核可（§6.7.3 Q6）。

> **v1.3 變更摘要**（逐條對照見 §6.6；掌舵者授權的 D-11、D-12，契約先行；結論的依據是現查 `AutoClaude/` 的原始碼與引擎自己的測試，不是推測，證據表見 §6.6.2）：
> 1. **引擎旋鈕查證（D-11）**：能由 Console 控制、而且在引擎生產路徑上**真的有讀者**的，只有 `minimax.enable_kernel_brain`（Brain 逐步校正）。`playbook.max_evolutions`／`require_evolution_signoff` 在生產的 Kernel 路徑沒有讀者（演化只提案、不套用，`AutoResumeService` 沒有核可閘），**Console 不送**；演化的 AI 提案只由金鑰的有無決定。`enable_kernel_brain=true` 而沒有金鑰時，引擎是**啟動即失敗**（不是忽略），所以沒有金鑰一律不送（§3.4.2）。
> 2. **新欄位 `engineCapabilities`**：`ExecutionRunResponse` 帶 `{autoMutation, selfEvolution}`，值域 `ENABLED`／`OFF`／`UNAVAILABLE_NO_API_KEY`；spawn 時決定、落庫 `execution_runs.engine_capabilities`（Flyway V10，建立時凍結）。`ENABLED` 的意思以引擎實際行為為準：`autoMutation`＝Brain 逐步校正，`selfEvolution`＝只產生演化提案、不套用（§3.4.2、§1.2.1、§1.2.3）。
> 3. **設定鍵與等級**：附錄 C 的 `agent.enableAutoMutation` 由 `UNVERIFIED` 改 `ENGINE`；`agent.enableSelfEvolution` 由 `UNVERIFIED` 改 `STORED_ONLY`（已驗證它不影響引擎）；§3.6.1 等級 6～10 列改寫；附錄 E 的 `API-AUT-06` 改為可驗證情境，新增 E2E-14。
> 4. **資源使用情況（D-12）**：Bridge `RunStateOut.resources`（psutil 取樣引擎行程樹）→ `ExecutionRunDetailResponse.bridge.resources` → §4.3 M-19 的顯示格式；取代 v1.2 的「Bridge 沒有此資料」（§3.1、§3.1.2、§4.6 G-M3）。
> 5. **其他文件**：Architecture §6(c)、§7、§10、§11、§12 與 ADR-001（D20、D21、G-18）同步。

> **v1.2 變更摘要**（逐條對照見 §6.5；W4 獨立 QA 報告 `docs/06_quality/QA_P3-6_E2E_Verification.md` 的 10 筆缺陷與 21 筆觀察由 W5 修復，契約先行）：
> 1. **新端點與新欄位**：`GET /monitor/task-totals`（C-1，§1.3.8）、`POST /projects/{id}/restore` 與 `GET /projects?deleted=true`（C-3，§1.6）、Bridge `GET /health/deep`（C-2，§3.1.1）；匯入詳情的 `warnings[]`／`parseOptions`（C-10，§1.1.9）；批次列表的 `bridgeStatus`（C-11，§1.2.2）。
> 2. **語意改動**：PDF 報表改回 200（C-4，§1.3.7；501 與 `PDF 報表尚未提供（W5）` 退役）；設定匯入「值未變」先於驗證計 `skipped`（C-6，§1.5.10）；`ENGINE_ESCALATION` 去重鍵帶 `runId`（C-7，§3.7）；執行中刪除目標／任務回 409 `project_executing`（C-8，§1.6.3）；手動重試不受 `maxRetries` 限制（C-9，§1.6.4）；`X-Trace-Id` 貫穿 console-api→Bridge（C-12，§0.4 第 6 點、§3.1.1）。
> 3. **客戶端流程**：`POST /auth/refresh` 失敗分 `renewed`／`invalid`／`unavailable` 三類，只有 `invalid` 登出，SSE 以 1→30 秒退避重連（C-5，§2.8）。
> 4. **漂移回寫**（C-21、C-22）：W4 補充節〈契約漂移裁決〉的 B1-1～B1-9、F1-3～F1-6、F2-1／F2-2／F2-5／F2-6 與 B2 交卷的六條，以實作為準寫進對應正文（逐條附程式位置，§6.5.2）；§3.7 補 `CONSECUTIVE_FAILURES` 觸發路徑說明。
> 5. **其他文件**：ADR-001 加 D19（軟刪除保留期）與 G-20（KPI「環形」→數值卡）（C-3、C-13）；§4.3 M-12 補追蹤鏈視圖裁決（C-14）；Architecture.md 的端點、資料所有權與 Bridge 契約同步。

> **v1.1 變更摘要**（逐條對照見 §6.3 主控裁決與 §6.4 審查回應表）：
> 1. **Bridge 修復相依**：PAUSED 的 run 做 restore 依賴 Bridge 修復 DB 模式的 advisory lock 自撞（AR-01；§1.2.10、§3.6.3、E2E-07）。
> 2. **SSE**：`/metrics` 收斂快照的事件 id 互異（`<S>.1`／`<S>.2`／`<S>.3`）；框架以解析後欄位斷言（冒號後空白不保證）；SseEmitter 完成時的 ASYNC dispatch 授權提醒（AR-02／03、TBC-1；§2）。
> 3. **部署**：新增〈反向代理需求〉§0.7（nginx 上傳大小、逾時、access log 遮罩；AR-04／05）；限流鍵改為 JWT subject、輪詢地板 10 秒（AR-06；§0.4）。
> 4. **儲存對齊**：`import_records.parse_path`／`last_parse_errors`（V5，AR-07）；通知摘要的 Bridge 欄位歸屬（AR-08）；`model.apiUrl` 改為完整的 chat-completions 端點（AR-09）；SSRF 改用 Apache HttpClient 5 釘 IP（AR-10）；loopback 例外改為 e2e 專用旗標（D-47）。
> 5. **規則補強**：人工判定優先於 R-goal 重算（AR-11）、補償刪除守門（AR-15）、`maxRetries` 上限 20（AR-14）、路徑 A 每 24 個合約切一個目標（AR-19）、`details` 不輸出 null（AR-17）、狀態轉移與 Bridge 事件細節的訂正（AR-20／21）。
> 6. **E2E 與既有測試**：E2E 環境補強（PATH、絕對路徑的 mock claude、額度快取隔離、關閉演化；AR-12）；新增〈須同步修改的既有程式與測試〉§0.8（AR-16）。
> 7. **§6**：§6.2 改為「契約 v1.1 對任務書（含補充節）」的差異表；新增 §6.3 主控裁決與 §6.4 審查回應表。

---

## 0. 共通約定

### 0.1 權威順位與事實來源

| 順位 | 來源 | 範圍 |
|------|------|------|
| 1 | PRD §0（校正區）、附錄 B | 需求與狀態機；與下列文件衝突時以 PRD §0 為準（§6 逐條列出實際衝突） |
| 2 | 本契約 | Phase 3～6 的 HTTP／SSE 形狀、錯誤常數、讀模型規則 |
| 3 | `AgentConsole/engine-bridge/README.md`、`app/models.py`、`app/routers/*.py`、`app/runner.py`、`tests/` | **Bridge 行為的唯一真相源**（本文引用的 Bridge 事實皆已對這些檔核對） |
| 4 | Architecture §6／§7／§8／§11、ADR-001 | 架構決策；與本契約衝突處已在 §6 裁決 |
| 5 | `agent_briefs/W3_BACKEND_P3-6.md` 與五份任務書（W3-B1／B2、W4-F1／F2、W4-QA，含檔尾〈主控裁決補充〉） | 主控已拍板的實作決策；與本契約仍有差異處列在 §6.2（衝突時以本契約為準） |

### 0.2 封包、型別與格式

| 項目 | 約定 |
|------|------|
| 前綴與編碼 | `/api/v1/**`；請求與回應皆 UTF-8 JSON（檔案端點另述） |
| 成功封包 | `{ "code":200\|201, "message":"success", "data":…, "timestamp":"…", "traceId":"…" }`（`ApiResult<T>`）；`traceId` 與回應標頭 `X-Trace-Id` 相同 |
| 無內容 | 204 沒有本文也沒有封包（`review`、`acknowledge`） |
| 不包封包 | 報表下載（CSV／PDF）、設定匯出（JSON 檔）、SSE |
| 分頁封包 | `data = { content:[…], page, size, totalElements, totalPages }`；`page` 從 0 起算；預設 `size=10`、上限 100（`steps`／`logs` 預設 50、上限 200；`settings/history` 預設 20、上限 100）；超出上限回 400 |
| 排序參數 | `sort=欄位[,asc\|desc]`；欄位白名單各端點註明，未知欄位或方向回 400（沿用 Phase 2 `ProjectController` 的訊息格式） |
| 時間 | ISO-8601 且帶 offset：`Instant` 欄位輸出 `…Z`，`ApiResult.timestamp` 為伺服器時區 offset（如 `+08:00`），Bridge 轉來的 `ts` 為 `+00:00`；三者皆為合法 RFC 3339，client 一律以 `Date.parse` 類函式解析，不比對字串 |
| 列舉 | 值全大寫底線（`IN_PROGRESS`）；例外（逐字常數）：有界閘名稱 `max_steps` 等、`bucket`／`format`／`order` 查詢參數、SSE 事件名（kebab-case） |
| 欄位命名 | camelCase；DTO 命名 `XxxRequest`／`XxxResponse`；`ConfigResponse.isEncrypted`、`CheckpointResponse.isAutomatic` 的 JSON 名稱必須帶 `is` 前綴（Java record 的 boolean 欄位注意序列化名稱，必要時 `@JsonProperty`） |
| null 與缺席 | 值為 null 的欄位可能輸出 `null` 或整個省略；client 視兩者等價（用 `?? default` 讀）。**`ApiError.details` 內不輸出 null 值**（後端 `DomainException.details` 以 `Map.copyOf` 建立，遇 null 會丟 NPE 變 500）：沒有值的鍵一律省略，所以文件與 E2E 對 `details` 的斷言都寫成「缺席或 null」 |
| ID | 路徑與欄位中的 id 皆小寫帶連字號 UUID；格式不合的路徑參數回 400（Phase 2 既有行為，訊息 `參數 <名> 的值格式不正確`），查無資料回 404 |
| 金額／計數 | Token 一律整數（`int64`）；百分比一律 0～100（不是 0～1）並四捨五入到小數 1 位 |

### 0.3 錯誤封包與 `reason` 常數

錯誤一律使用 Phase 1+2 的 `ApiError`：`{ code, message, reason?, errors:[{field,message}], details?, timestamp, traceId }`；整個後端只有 `GlobalExceptionHandler` 產生它。

1. **`reason` 是前後端共用的常數**：後端集中在 `ErrorReasons`（或等價常數類別），前端集中在 `lib/api/reasons.ts`，兩邊字串逐字相同；E2E 以 `reason` 逐字比對。全部常數見**附錄 B**；各端點小節只列該端點用到的。
2. `message` 是給人看的中文句子（可含動態值），**不得**用來做程式判斷；`details` 的鍵為 camelCase，每個鍵在各端點小節固定。
3. PRD 逐字指定的 reason 一律沿用：`未經人工審批的草案不可執行`、`halt_threshold_pct 必須大於 compact_threshold_pct`。Phase 1+2 既有的 reason（`UNAUTHENTICATED`／`TOKEN_EXPIRED`／`TOKEN_INVALID`／`ACCESS_DENIED`／`MALFORMED_REQUEST_BODY`／`已 signoff`／`目前狀態不可重試`）不變。
4. 狀態碼語意（Phase 3～6 補充）：

| 碼 | 語意 |
|----|------|
| 400 | Bean Validation／格式；`approver` 缺漏；token_guard 跨鍵違規；命令含禁用字元；時間範圍不合法（含 `task-totals` 視窗超過 92 天）；加密值要求；查詢參數型別不符（例：`reveal=abc`，B1-4） |
| 401／403 | 未認證（`UNAUTHENTICATED`／`TOKEN_EXPIRED`／`TOKEN_INVALID`）／角色不足（`ACCESS_DENIED`；`reveal=true` 非 ADMIN 另有專屬 reason） |
| 404 | 資源不存在或已軟刪除；`runId`／`checkpointId`／審核項不屬於所述父資源也是 404 |
| 409 | 草案未 signoff 即執行／resume／restore；匯入或執行狀態不允許該操作；並發互斥；審核項已處理；敏感參數未帶 `confirm=true`；Bridge 草案失效；專案有進行中批次時刪除其目標／任務（`project_executing`）；專案復原前提不符（`project_not_deleted`、`restore_window_expired`） |
| 413／415 | 上傳超過 10MB（匯入）或 1MB（設定檔）／副檔名或類型不支援 |
| 422 | 有界閘與消毒拒絕（含 Bridge 的 422 原因逐字帶出）；SSRF／allowlist 檢查未通過；上傳檔案內容無法讀取 |
| 429 | 超過每分鐘 100 次（見 §0.4） |
| 502／504 | Bridge 無法連線／逾時（建立執行已補償刪除 run 列） |

5. **W5（v1.2）新增的四個 reason 是英文識別字**（主控裁決 C-3、C-5、C-8）：`project_executing`、`project_not_deleted`、`restore_window_expired` 由後端回；`upstream_unavailable` **只由前端合成**（`POST /auth/refresh` 暫時失敗時的 `ApiError`，後端永不回它，§2.8）。它們與 Phase 1+2 既有的 `UNAUTHENTICATED` 等英文識別字同風格，與 Phase 3～6 的中文逐字常數並存；規則與其他 reason 相同（逐字、前後端各一份常數、不得用 `message` 判斷），全部列在附錄 B.2。注意 `project_executing`（刪除目標／任務被擋，§1.6.3）與 execute 的 `專案正在執行中`（啟動執行被擋，§1.2.1 第 3 項）是**不同**的 reason，不要混用。
6. **501 已退役**（C-4）：PDF 報表自 v1.2 起回 200（§1.3.7）；`PDF 報表尚未提供（W5）` 常數與後端的 `NotImplementedYetException` 一併移除，附錄 B.2 不再列它。
7. **v1.4 的回應本文欄位 `reason` 不是 `ApiError.reason`**（D-16）：`GET /engines/sdd` 的 200 回應有一個 `data.reason` 欄位（§1.7.1），值是英文識別字（`bridge_unreachable`、`sdd_unavailable`、`bridge_error`、`fsm_not_found`、`fsm_state_unreadable`），描述「引擎目前的狀態」，**不是錯誤封包**；它們不進附錄 B.2，另列附錄 B.4，也不得拿來當 HTTP 錯誤處理的判斷依據（該端點在引擎不可用時仍回 200，同 §1.2.3 的慣例）。

8. **v1.5 新增的五個 `ApiError.reason` 與一個 404 例外都是英文識別字**（整合輪 115；已與 ADR-016 對齊）：`sdd_fsm_state_conflict`、`sdd_fsm_not_found`、`sdd_spec_digest_changed`、`sdd_binding_conflict`、`sdd_write_disabled`（由後端回；SA 初稿的 `sdd_not_bound` 隨 D-115-14 移除），以及 `GET /executions/{runId}/rtm` 的 404 `rtm_not_found`——**本端點是「404 的 `reason` 省略」慣例的唯一例外**，因為「批次不存在」與「批次存在但沒有追溯報告」必須能機械區分。規則同第 5 點（逐字、前後端各一份常數、不得用 `message` 判斷）。此外 `GET /engines/sdd` 的回應欄位 `data.reason` 新增一個值 `sdd_root_rejected`（回應欄位，不是 `ApiError.reason`，同第 7 點，附錄 B.4）。全部列在附錄 B.5。其餘 SDD 相關錯誤一律沿用既有 reason（`SDD 規格檢查未通過`、`引擎拒絕此請求`、`引擎橋接服務錯誤`等，§3.2 的新列）。

### 0.4 認證、角色、CORS 與限流

**角色矩陣**（最低角色；ADMIN ⊃ OPERATOR ⊃ VIEWER）：

| 端點群 | VIEWER | OPERATOR | ADMIN |
|--------|:------:|:--------:|:-----:|
| 匯入讀取（`GET /import`、`GET /import/{id}`） | ✅ | ✅ | ✅ |
| 匯入寫入（upload／text／parse／result／signoff／confirm／reject） | — | ✅ | ✅ |
| 執行讀取（`GET` run／steps／dag／checkpoints／executions）、兩條 SSE | ✅ | ✅ | ✅ |
| 執行寫入（execute／pause／resume／cancel／restore／review） | — | ✅ | ✅ |
| 監控讀取（metrics／趨勢／`task-totals`／alerts／logs／report／notifications） | ✅ | ✅ | ✅ |
| 引擎狀態（`GET /engines/sdd`）、待審批清單（`GET /signoffs/pending`）（v1.4） | ✅ | ✅ | ✅ |
| 執行追溯覆蓋（`GET /executions/{runId}/rtm`）（v1.5） | ✅ | ✅ | ✅ |
| SDD 核准凍結（`POST /projects/{id}/sdd/freeze`；人工閘，角色與 signoff 同級）（v1.5） | — | ✅ | ✅ |
| SDD 綁定編輯（`PUT /projects/{id}/sdd-binding`；角色與 freeze 同級）（v1.5） | — | ✅ | ✅ |
| 告警確認 | — | ✅ | ✅ |
| 專案復原（`POST /projects/{id}/restore`）、檢視已刪除專案（`GET /projects?deleted=true`；VIEWER → 403 `ACCESS_DENIED`，由 controller 檢查，與 `reveal` 同型） | — | ✅ | ✅ |
| 設定讀取（`GET /settings*`、`history`；加密值遮罩） | ✅ | ✅ | ✅ |
| `reveal=true` 揭露加密明文 | — | — | ✅ |
| 設定寫入與工具（PUT／reset／import／export／test-connection） | — | — | ✅ |

**對 `SecurityConfig` 的必要改動**（現行：`GET /api/v1/**` 為 VIEWER 以上、其餘為 OPERATOR 以上）：

1. `/api/v1/settings/**` 的**非 GET** 一律要求 ADMIN（含 `POST /settings/export`、`/settings/import`、`/settings/test-connection`，它們是 POST 但屬 ADMIN 專用）；`GET …?reveal=true` 由 Controller 檢查角色，非 ADMIN 回 403（reason `僅 ADMIN 可揭露敏感參數`）。
2. **SSE 認證**（兩種都收，主控裁決）：`/api/v1/stream/**` 先看 `Authorization: Bearer`，沒有才看查詢參數 `access_token`。只收 access token；refresh token 一律 401（`TOKEN_INVALID`）；此查詢參數**僅限 `/api/v1/stream/**`**（其他路徑出現一律忽略）。補強：**後端任何存取日誌不得輸出含 `access_token` 的 query string**（`AuditLoggingFilter` 只審寫入方法且記 `getRequestURI()`，本來就不含 query；若另外啟用 Tomcat access log 或 `CommonsRequestLoggingFilter`，須遮罩）；nginx 的 `log_format` 遮罩見 §0.7；SSE 回應帶 `Cache-Control: no-store`；`SseEmitter` 完成時的 ASYNC dispatch 授權見 §2.1 的實作提醒。
3. **CORS**：`allowedHeaders` 補 `Last-Event-ID`；`exposedHeaders` 補 `X-Follow-Up-Run-Id`、`Retry-After`、`Content-Disposition`；實作另暴露 `X-Trace-Id`（`SecurityConfig.corsConfigurationSource`）。`X-RateLimit-Limit`／`X-RateLimit-Remaining` **刻意不暴露**（QA O-01 維持觀察）：瀏覽器端的 JS 只讀 `Retry-After`。
4. **限流**（NFR-9.2-06；AR-06）：每個**使用者**每 60 秒 100 次（Bucket4j 記憶體實作；Redis 為選配）。**計數方式是固定視窗**（B1-9；`infrastructure/security/RateLimiter`）：每個鍵的視窗從該鍵「視窗期滿後的第一個請求」起算、長 60 秒，視窗內計到 100 次，期滿換一個全新的桶；`Retry-After`＝距視窗結束的秒數（無條件進位、不小於 1）。不採貪婪補充的 token bucket（每 0.6 秒補 1 個）：連續 100 次請求跑超過 0.6 秒時第 101 次仍會成功，E2E-11 的「第 101 次回 429」就變成取決於機器速度。
   - **限流鍵**＝已認證請求的 JWT subject；**未認證**的請求（登入端點、帶無效 token 而回 401 的請求）才以客戶端 IP 為鍵。理由：Docker 全棧下所有使用者都經 nginx 進來，若以連線位址為鍵，整個系統會共用同一個桶。限流 filter 排在 `JwtAuthenticationFilter` 之後（取得 subject 後才算桶：現行 `JwtAuthenticationFilter` 遇到無效或過期 token 不自行回應、只記錄原因並以匿名身分往下走，所以這類請求在限流 filter 看到的就是「未認證」）、**授權判定之前**（即 `addFilterAfter(rateLimitFilter, JwtAuthenticationFilter.class)`，早於 Spring Security 最後的授權步驟）；因此超限的請求**先得 429，而不是 401／403**（E2E-11 步驟 7 驗這個順序）。
   - 對象＝`/api/**`；不計入：`/actuator/**`、`/v3/api-docs`、SSE 連線建立之後的串流本身（建立請求算 1 次）。
   - 超限回 **429**：`reason`＝`超過每分鐘 100 次請求上限`、`details={limit:100, windowSeconds:60, retryAfterSeconds:N}`，並帶標頭 `Retry-After`（秒）、`X-RateLimit-Limit: 100`、`X-RateLimit-Remaining: 0`；成功回應也帶後兩個標頭。
   - **客戶端 IP**（只有未認證請求用得到）：docker／e2e profile 設 `console.security.rate-limit.trust-forwarded-for=true`，並以 `server.forward-headers-strategy=native` 啟動（Tomcat 的 RemoteIpValve 只信任內網代理位址，預設即涵蓋 nginx 容器與本機測試 client）；限流取處理後的 `getRemoteAddr()`，**不自行解析 `X-Forwarded-For`**。production 直連（沒有代理）維持 `false`，此時偽造的 `X-Forwarded-For` 不會被採信。
   - 開關：`console.security.rate-limit.enabled`（預設 `true`；單元／整合測試 profile 預設 `false`，但必須有一支測試開著它打 101 次、驗第 101 次回 429；e2e profile 為 `true`）。
   - **輪詢地板**：同一個使用者的所有頁面共用同一個桶，所以通知摘要與任何輪詢間隔都**不得小於 10 秒**（`monitor.refreshIntervalMs` 的預設值與最小值皆為 `10000`，附錄 C）；監控頁約 8 個端點、每 10 秒各一次≈每分鐘 48 次，仍在 100 以內；頁面不可見時應停止輪詢。
5. 審計（NFR-9.2-07）：沿用 `AuditLoggingFilter` 的結構化 JSON 日誌；Phase 3～6 追加兩個欄位 `action`（例：`import.signoff`、`execution.review.APPROVE`、`settings.reveal`、`project.restore`）與 `entity`（`<type>:<id>`）。另依任務書把寫入端點（POST／PUT／PATCH／DELETE）落一列到 `console.audit_log`（V6；**內部實作**，寫入失敗不得影響主請求；契約沒有任何端點讀它，見 §6 D-13）。
6. **traceId 貫穿 console-api→Bridge（C-12；NFR-9.4-04；QA O-11）**：console-api 的 `TraceIdFilter` 對每個請求自產一個 UUID（**不採信**入站的 `X-Trace-Id`，避免日誌注入），寫進 MDC（日誌樣板的 `%X{traceId}`）、回應標頭 `X-Trace-Id` 與封包的 `traceId`。console-api 對 **Bridge 的每一個請求**（`/autoclaude/*`、`/sdd/*`、健康探測，含 SSE 事件串流）都帶標頭 `X-Trace-Id`：由使用者請求觸發的呼叫取當前請求的 traceId；沒有請求上下文的背景消費者（`RunEventConsumer`、探測環、啟動對帳）用該 run 的 traceId（啟動該 run 的 execute 請求的 traceId，只存在記憶體、不入庫），取不到就新產一個 UUID。Bridge 端（§3.1.1）：中介層讀取該標頭（缺則自產 `uuid4`）、回應回帶同名標頭、**每一行**應用日誌都帶 `trace_id`。如此同一次使用者操作的 console-api 日誌、Bridge 日誌與前端錯誤封包的 `traceId` 可用同一個值串起來。
7. **refresh token 撤銷（v1.4；D-19；§1.9）**：`POST /auth/refresh` 換新時**原子地撤銷舊 refresh token**（鍵＝token 的 `jti`），撤銷後再拿舊 token 換新 → 401 `INVALID_REFRESH_TOKEN`（客戶端分類為 `invalid`，§2.8）；新增 `POST /auth/logout` 讓登出也撤銷。撤銷名單 Redis 優先、Redis 不在線退回單實例記憶體並記 WARN；access token 無狀態，不在名單內。`SecurityConfig` 把 `POST /api/v1/auth/logout` 加入 `permitAll`（與 login、refresh 同列）。

### 0.5 資料庫增補（Flyway；契約所需）

現況：V1～V4 已套用（`V3__review_requests`、`V4__monitor_alerts` 在 Phase 1+2 已建表）。本契約涉及 **V5～V12**（V12 為 v1.5 增補，見該節）；版號依任務書分工：V5、V6 屬後端第一棒（W3-B1），V7 屬後端第二棒（W3-B2，在 B1 交卷後的同一棵樹上接續，所以版號不會撞），**V8、V9 屬 W5-BE（v1.2，在 V7 之後接續）**，**V10 屬 W7-BE（v1.3，在 V9 之後接續）**，**V11 屬 W7-BE（v1.4，在 V10 之後接續；只有一支 `UPDATE`，沒有新欄位）**；已套用的 V1～V9 **不得修改**。

**V5 `V5__seed_engine_configs.sql`**（W3-B1；Architecture §11.4 的 V5 補充鍵，加上審查回應的欄位與預設值校正）：①新增下列九個鍵；②補全部鍵的 `validation_rule`；③新增欄位 `system_configs.impact_note VARCHAR(500)`（US-S-08）；④新增 `import_records.parse_path`、`import_records.last_parse_errors`（AR-07，見下方 SQL）；⑤預設值校正（AR-06、AR-09，見下方 SQL）。

| 類別 | 鍵 | valueType | 預設 |
|------|----|-----------|------|
| autoclaude | `claudeCommand` | STRING | `claude` |
| autoclaude | `claudeExtraArgs` | STRING | （空字串） |
| autoclaude | `claudeContinueFlag` | STRING | `--continue` |
| autoclaude | `claudeEncoding` | STRING | `utf-8` |
| autoclaude | `dbDsn` | ENCRYPTED（`is_encrypted=TRUE`） | （空字串） |
| autoclaude | `dualReadResolution` | ENUM | `yaml_wins` |
| model | `enableKernelBrain` | BOOLEAN | `false` |
| execution | `autoResume` | BOOLEAN | `true` |
| execution | `maxAutoResumes` | INTEGER | `10` |

中繼資料的歸屬：`options`／`min`／`max`／`effect` 放程式內的 `ConfigCatalog`（附錄 C 是唯一真相源），不入 DB；`impactNote` 讀 `system_configs.impact_note`。V5 把附錄 C 的 `validationRule` 正規表示式寫進 `system_configs.validation_rule`、把附錄 C 的 `impactNote` 寫進 `impact_note`（任務書點名的 8 個關鍵鍵為最低要求，附錄 C 有影響提示者一併寫入）。

V5 的 SQL 節錄（④⑤；`ddl-auto=validate` 要求實體同步：`ImportRecordEntity` 加兩欄、`SystemConfigEntity` 加 `impact_note`）：

```sql
-- ④ 匯入記錄：解析路徑與「最近一次被有界閘拒絕」的原因各有專屬欄位（AR-07）
--    parsed_result 在解析成功前為 NULL（任務書的 parsed_result.error 作廢）
ALTER TABLE console.import_records
    ADD COLUMN parse_path VARCHAR(20),          -- SDD／LLM／DECOMPOSE；解析成功後才有值
    ADD COLUMN last_parse_errors JSONB;         -- GateError[]；成功解析後清為 NULL

-- ⑤ 預設值校正：只在值仍等於舊預設時才改（不覆蓋管理員改過的值）；value 與 default_value 各自判斷
UPDATE console.system_configs SET value = 'https://api.minimax.io/v1/text/chatcompletion_v2'
 WHERE category = 'model' AND key = 'apiUrl' AND value = 'https://api.anthropic.com';
UPDATE console.system_configs SET default_value = 'https://api.minimax.io/v1/text/chatcompletion_v2'
 WHERE category = 'model' AND key = 'apiUrl' AND default_value = 'https://api.anthropic.com';
-- model.name：舊預設 claude-sonnet-4-20250514 → MiniMax-M2.7（與上一列成對，同樣寫法）
-- monitor.refreshIntervalMs：舊預設 3000 → 10000（同樣寫法）
```

⑤ 的依據：`model.apiUrl` 改為「完整的 chat-completions 端點」（§1.5.7、§3.3.3），預設值取引擎自己的預設（`AutoClaude/autoclaude/utils/config.py` 的 `MinimaxConfig.base_url＝https://api.minimax.io/v1/text/chatcompletion_v2`、`MinimaxConfig.model＝MiniMax-M2.7`），否則種子預設（Anthropic 網域）在設了金鑰之後會被 Bridge 以 `outbound_not_allowed` 拒絕（AR-09）；`monitor.refreshIntervalMs` 的下限抬到 10 秒見 §0.4 第 4 點（AR-06）。

**V6 `V6__audit_log.sql`**（W3-B1；**內部實作**，不進 HTTP 契約）：`console.audit_log(id, occurred_at, subject, role, method, path, entity_type, entity_id, http_status, trace_id)`，欄位依任務書；§0.4 第 5 點說明寫入規則。

**V7 `V7__console_event_anchors_and_token_samples.sql`**（W3-B2）：

```sql
-- Console 自產 SSE 事件（review-request／alert）的重播錨點；子序號規則見 §2.2
ALTER TABLE console.review_requests
    ADD COLUMN event_seq INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN event_sub INTEGER NOT NULL DEFAULT 1;
ALTER TABLE console.alerts
    ADD COLUMN event_seq INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN event_sub INTEGER NOT NULL DEFAULT 1;      -- 0＝Bridge 告警事件的持久化鏡像（SSE 不重播它）

-- console-api 已處理到的 Bridge 事件 seq（Console 擁有此欄；Bridge 不寫）
ALTER TABLE console.execution_runs
    ADD COLUMN console_last_seq INTEGER NOT NULL DEFAULT 0;

-- Token 趨勢與任務 Token 歸因的來源（Bridge 不寫 execution_steps.tokens_used，見 §6 D-16）
CREATE TABLE console.run_token_samples (
    run_id      UUID NOT NULL REFERENCES console.execution_runs(id) ON DELETE CASCADE,
    seq         INTEGER NOT NULL,
    ts          TIMESTAMP WITH TIME ZONE NOT NULL,
    tokens_used BIGINT NOT NULL,            -- 本批次累計（Bridge token 事件的 tokens_used）
    delta       BIGINT NOT NULL,            -- 與前一則的差
    context_pct DOUBLE PRECISION,
    task_id     UUID REFERENCES console.tasks(id),   -- 增量歸因的任務（目前 RUNNING 的步驟）
    PRIMARY KEY (run_id, seq)
);
CREATE INDEX idx_run_token_samples_ts ON console.run_token_samples(ts);

-- 同一規則＋對象在被確認前不重複產生告警（PRD §5.4.4；DB 層兜底）
CREATE UNIQUE INDEX uq_alerts_open_rule_subject
    ON console.alerts(project_id, rule, subject) WHERE acknowledged = FALSE;
```

實作注意：(a) `execution_runs` 的 `status／subprocess_pid／bridge_instance／advisory_lock_key／total_tokens_used／completed_at` 由 Bridge 寫，`ExecutionRunEntity` 對它們一律唯讀（`updatable=false` 或只用目標明確的 `UPDATE … SET console_last_seq=?`），避免 JPA 整列回寫蓋掉 Bridge 的更新（PRD §0.2.2）；(b) `alerts.subject` 對規則型告警永遠非 null（否則 partial unique index 對 NULL 失效）；(c) `review_requests.kind` 的 CHECK（V3）**不擴充**，四種 kind 足夠（§3.6）。

**V8 `V8__import_record_warnings_and_options.sql`**（W5-BE；C-10；QA 的 F1-1／F1-2）：

```sql
-- 匯入記錄補兩欄：重開記錄（歷史列表、重新整理）時還原黃色解析提示與解析選項
ALTER TABLE console.import_records
    ADD COLUMN warnings JSONB NOT NULL DEFAULT '[]'::jsonb,   -- ParseWarning[]；最近一次成功的 parse／PUT result 的結果
    ADD COLUMN parse_options JSONB;                           -- ParseOptions；最近一次 parse 請求的選項；從未 parse 過為 NULL
```

寫入規則：`parse` 通過欄位驗證、進入 `PARSING` 時把請求的 `ParseOptions` 原樣寫進 `parse_options`（`autonomyLevel` 省略者存預設 3；**不論該次 parse 成敗**，保存的都是最近一次請求）；`parse` 成功時以該次的 `warnings` 覆寫 `warnings`；`PUT /import/{id}/result` 成功時以重算後的 `warnings` 覆寫；`parse` 失敗（退回 `UPLOADED`）不動 `warnings`（與「保留上一次成功的 `parsed_result`」同一原則，§1.1.3）。既有記錄升級後 `warnings=[]`、`parse_options=NULL`。`ImportRecordEntity` 同步加兩欄（`ddl-auto=validate`）。

**V9 `V9__soft_delete_timestamps.sql`**（W5-BE；C-3；NFR-9.3-04）：

```sql
-- 軟刪除時間：保留期與復原都需要知道「何時刪的」與「同一次刪除連帶軟刪了哪些」
ALTER TABLE console.projects ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE,
                             ADD COLUMN status_before_delete VARCHAR(20);   -- 軟刪除前的專案狀態（復原時還原；軟刪除會把 status 改成 ARCHIVED）
ALTER TABLE console.goals    ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE console.tasks    ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
-- 升級前已軟刪的列：真正的刪除時間已不可考，以 updated_at 近似（軟刪除當下會更新它）；status_before_delete 留 NULL
UPDATE console.projects SET deleted_at = updated_at WHERE is_deleted = TRUE AND deleted_at IS NULL;
UPDATE console.goals    SET deleted_at = updated_at WHERE is_deleted = TRUE AND deleted_at IS NULL;
UPDATE console.tasks    SET deleted_at = updated_at WHERE is_deleted = TRUE AND deleted_at IS NULL;
CREATE INDEX idx_projects_deleted_at ON console.projects(deleted_at) WHERE is_deleted = TRUE;
```

寫入規則（`ProjectService.delete`、`GoalService.delete`、`TaskService.delete` 與各自的 `softDeleteBy…` 查詢）：任何軟刪除都同時寫 `deleted_at`；**刪除專案時，專案與它當時仍未刪除的目標、任務在同一交易內寫入同一個 `deleted_at` 值**（既有程式已把同一個 `now` 傳給三者）——復原靠「目標／任務的 `deleted_at` 等於專案的 `deleted_at`」辨識「同一次刪除連帶軟刪」的列（§1.6.1）；刪除專案時把刪除前的 `status` 存進 `status_before_delete`，再轉 `ARCHIVED`。`ProjectEntity`、`GoalEntity`、`TaskEntity` 同步加欄位。

**V10 `V10__execution_run_engine_capabilities.sql`**（W7-BE；D-11；§3.4.2）：

```sql
-- 該批次 spawn 時 Console 送進引擎的能力狀態：建立批次時與 execution_runs 同一次 INSERT 寫入，之後不再更新
-- NULL＝V10 之前建立的批次（當時送了什麼已不可考，不回填、不猜測）
ALTER TABLE console.execution_runs ADD COLUMN engine_capabilities JSONB;   -- {"autoMutation":"ENABLED","selfEvolution":"ENABLED"}

-- impact_note 存在 system_configs（V5 寫入）：三個鍵的語意在 v1.3 改變，文字依附錄 C.1／C.2 校正（以 (category,key) 對位，不比對舊文字）
UPDATE console.system_configs AS c SET impact_note = v.note
  FROM (VALUES
    ('model', 'enableKernelBrain',  '<附錄 C.1 enableKernelBrain 的 impactNote 原文>'),
    ('agent', 'enableAutoMutation', '<附錄 C.2 enableAutoMutation 的 impactNote 原文>'),
    ('agent', 'enableSelfEvolution','<附錄 C.2 enableSelfEvolution 的 impactNote 原文>')
  ) AS v(category, key, note)
 WHERE c.category = v.category AND c.key = v.key;
```

寫入規則：①`engine_capabilities` 只由 console-api 在建立批次時寫一次，值就是 `ConfigMaterializer.materialize(autonomyLevel)` 回傳的 `engineCapabilities`——**同一個回傳值也用來組 Bridge 請求**（§3.4.2 的一致性規則）；Bridge 不寫它，`resume`／`restore` 不更新它（引擎設定檔 `config.yaml` 在 spawn 時就凍結）。②`ExecutionRunEntity` 同步加欄位（`ddl-auto=validate`），對它設 `updatable=false`。③JSON 鍵固定為 `autoMutation`、`selfEvolution`，值為 §3.4.2 的三種之一；讀出時缺鍵或值不認得，一律當成「該鍵缺席」，不丟例外（前向相容）。④`UPDATE` 的三段字串必須與附錄 C 的 `impactNote` 逐字相同（`SchemaMigrationIT` 比對，§0.8）；`impact_note` 欄位上限 500 字元。

**V11 `V11__health_check_path_deep.sql`**（W7-BE；D-17；§3.1）：

```sql
-- console-api 的 Bridge 探測環改打深度探針：只在值仍等於舊預設 /health 時才改（不覆蓋管理員改過的值；寫法同 V5 的 ⑤）；
-- value 與 default_value 各自判斷
UPDATE console.system_configs SET value = '/health/deep'
 WHERE category = 'autoclaude' AND key = 'healthCheckPath' AND value = '/health';
UPDATE console.system_configs SET default_value = '/health/deep'
 WHERE category = 'autoclaude' AND key = 'healthCheckPath' AND default_value = '/health';
-- impact_note（V5 寫入）：文字依附錄 C.5 校正，以 (category,key) 對位，不比對舊文字
UPDATE console.system_configs SET impact_note = '<附錄 C.5 healthCheckPath 的 impactNote 原文>'
 WHERE category = 'autoclaude' AND key = 'healthCheckPath';
```

寫入規則與限制：①沒有新欄位、沒有新表，`ddl-auto=validate` 不受影響。②預設值的真相源是 `system_configs.default_value`（V2 種子，本支遷移校正）與 `BridgeEndpoints.DEFAULT_HEALTH_PATH`（設定缺席時的程式內兜底，`/health` 改 `/health/deep`）；`ConfigCatalog` 只放中繼資料（effect 等），沒有預設值。③管理員**刻意**把值設成 `/health`（與舊預設相同）的既有部署會被一併改成 `/health/deep`——資料庫分不出「刻意」與「沒動過」（V5 ⑤ 同樣的取捨）；要保留淺探測，升級後把值改回 `/health`（附錄 C.5 的驗證規則允許）。④`SchemaMigrationIT` 驗三種情形：舊預設→被改成 `/health/deep`；管理員改成其他值（例 `/custom`）→不動；已是 `/health/deep`→不動；`impact_note` 逐字等於附錄 C.5。

**V12 `V12__project_sdd_binding.sql`**（W3-BE；v1.5；G-07、D-115-14；在 V11 之後接續；三個新欄位加一個部分唯一索引；ADR-016 §7.2）：

```sql
-- Console 專案為錨的 SDD 綁定：三欄皆可 NULL；既有專案升級後皆為 NULL，不回填、不猜測
ALTER TABLE console.projects
    ADD COLUMN sdd_project   VARCHAR(100),   -- FSM 專案鍵（第一次使用時寫回標準鍵，或由使用者編輯）；NULL＝用預設（專案名）
    ADD COLUMN sdd_spec_dir  VARCHAR(500),   -- 規格檔所在目錄（絕對路徑）＝編譯回應 spec_path 的父目錄；與 execution_path 同長度上限
    ADD COLUMN sdd_spec_file VARCHAR(500);   -- 規格檔（絕對路徑）＝編譯回應的 spec_path；NULL＝尚未用路徑 A 匯入規格

-- 一個 FSM 專案只對應一個「未軟刪除」的 Console 專案（NULL 不佔位）
CREATE UNIQUE INDEX ux_projects_sdd_binding
    ON console.projects (execution_path, sdd_project)
    WHERE sdd_project IS NOT NULL AND is_deleted IS NOT TRUE;
```

寫入規則與限制：①寫入點只有三處：(a) `POST /projects/{id}/sdd/freeze` 的第 5 項（§1.10.2）與 `POST /import/{id}/confirm`（§1.10.8）把 Bridge 回的標準鍵寫進 `sdd_project`（原為 NULL 時）；(b) `POST /import/{id}/confirm` 把 `ParsedResult.sddSpecDir／sddSpecFile`（路徑 A 才有值，§3.3.2）寫進 `sdd_spec_dir`／`sdd_spec_file`（建立新專案時一併帶入，併入既有專案時冪等更新）；(c) `PUT /projects/{id}/sdd-binding`（§1.10.7）編輯 `sdd_project`。②`POST`／`PUT /projects` 的請求不收這三欄（帶了也不採用）；沒有「解除綁定」端點——編輯 `sdd_project`（含清成 NULL）即改綁。③`ProjectEntity`、`NewProject`、`ProjectResponse`、`ProjectDetailResponse` 同步加欄（`ddl-auto=validate`）；`ProjectSummaryResponse`（列表）不帶。④**部分唯一索引**：`(execution_path, sdd_project)` 在 `sdd_project` 非空且 `is_deleted IS NOT TRUE` 的列中唯一（`is_deleted` 是可為 NULL 的布林，所以用 `IS NOT TRUE`）；Backend 在任何 Bridge 寫入呼叫之前先檢查、後寫入，衝突回 409 `sdd_binding_conflict`，索引是最後的兜底（寫入時撞索引一律轉成同一個 409）。⑤`SchemaMigrationIT` 驗：三欄存在、型別為 varchar（長度 100／500／500）、可 NULL，索引存在且為部分索引（兩個未刪專案同 `(execution_path, sdd_project)` 失敗；其中一個軟刪除後可成立；`sdd_project` 為 NULL 的多列不衝突）；既有專案列升級後三欄為 NULL。

### 0.6 名詞對照

| Bridge | Console | 說明 |
|--------|---------|------|
| `run_id` | `execution_runs.id`、路徑 `{runId}` | 同一個 UUID |
| `step_id`（playbook，字串） | `dag.nodes[].stepId`、`ExecutionStepResponse.stepId`、`LogEventData.stepId`、`CurrentStep.stepId` | 例 `G1-T2`；**同名欄位的三種意思**請以所屬型別區分：①這一列（playbook 的 step_id）；②審核端點路徑的 `{stepId}`＝`review_requests.id`（UUID，名稱沿用 PRD，**不是** playbook 的 step_id）；③`ReviewRequestResponse.stepId`＝`execution_steps.id`（UUID，佐證該審核項的步驟列） |
| 步驟序號 `stepNumber` | `LogEventData.stepNumber`、`CurrentStep.stepNumber`＝該步驟在批次 playbook 內的**位置**（1 起，等於 DAG 的 `sequence`）；`ExecutionStepResponse.stepNumber`＝該 step 事件的 **Bridge seq**（`execution_steps.step_number` 欄放 seq） | **同名三處、兩種意思**（位置 vs 事件序號）；要用位置請讀 `ExecutionStepResponse.stepId` 對 `dag` |
| `goal_task_id`（playbook 每步欄位） | `tasks.id` | Bridge 以它寫 `execution_steps.task_id` |
| `checkpoint_id` | `checkpoints.id`、路徑 `{checkpointId}` | 同值 |
| `seq`（事件序號） | SSE `id:` 的整數部分；`execution_steps.step_number` | 同一個序號空間 |
| 八態（INITIALIZING／RUNNING／PAUSING／PAUSED／CANCELLING／COMPLETED／FAILED／CANCELLED） | `RunStatus` 六態＋`bridgeStatus` | `PAUSING`／`CANCELLING` 折為 `RUNNING`；原值放 `bridgeStatus` |
| `alert.level` `info`／`warning`／`error` | `AlertSeverity` `INFO`／`WARNING`／`CRITICAL`（SSE）；持久化只用 `WARNING`／`CRITICAL` | |

### 0.7 反向代理需求（docker／nginx；AR-04、AR-05）

全棧部署經 nginx（`AgentConsole/docker/nginx/`）。下列需求不屬於 HTTP 契約本身，但缺了就會讓契約的行為在 Docker 全棧下失效（前兩項是審查實測到的缺口：nginx 預設 `client_max_body_size` 只有 1m，10MB 上傳經 nginx 必被擋成 413；現有 `log_format` 記 `"$request"`，query string 裡的 `access_token` 會原樣進 access log）。這些檔案不在 `backend/**`，所以逐項指定 owner。

| # | 需求 | 設定 | owner |
|---|------|------|-------|
| 1 | 匯入：10MB 檔案、文字最長 2,000,000 字元（UTF-8 最多約 6MB）、同步解析最長約 `model.timeout`＋15 秒 | `location /api/v1/import/ { client_max_body_size 11m; proxy_read_timeout 180s; … }` | W3-B1 |
| 2 | 設定檔匯入（≤1MB 的 JSON 加 multipart 封裝） | `location = /api/v1/settings/import { client_max_body_size 2m; … }`（任務書只列了匯入位置，這一項由本契約補列） | W3-B1 |
| 3 | SSE（含 EventSource 的 `?access_token=`） | `location /api/v1/stream/ { proxy_buffering off; proxy_http_version 1.1; proxy_read_timeout 3600s; … }`（現有 `/api/` 區塊已有 `proxy_buffering off` 與 `86400s`；獨立區塊是讓需求明文，並把串流的逾時與一般 API 分開） | W3-B2 |
| 4 | access log 不得出現 `access_token` 的值 | `nginx.conf` 的 `log_format` 不記含 query 的 `$request`，二選一：改記 `$uri`；或用 `map $request_uri $masked_uri { default $request_uri; ~^(?<tokpre>[^?]*\?(?:.*&)?access_token=)[^&]*(?<toksuf>.*)$ "${tokpre}***${toksuf}"; }` 後記 `"$request_method $masked_uri $server_protocol"` | W3-B2 |
| 5 | **`error_log` 也不得洩漏 `access_token`**（v1.2，QA 全棧實測 DEF-AC-008）：上游被切斷（例：backend 重啟）時 nginx 會把完整的原始請求行（含 `?access_token=<JWT>`）印進 `error_log`，`log_format` 管不到它 | `error_log … crit;`（降到 `crit` 以上；要除錯時暫時調回 `error` 並在事後清檔，檔頭〈誠實劃界〉須如實說明）；前端改 fetch 串流帶標頭是另一條治本路（§2.8 第 2 點的優先做法），不在 v1.2 範圍 | W5-INFRA（C-15） |
| 6 | **前端健康路由與快取標頭**（v1.2，QA O-08／O-09）：`/api/health` 是前端自己的健康路由，不得被 `/api/` 區塊反代到 backend 而回 401；靜態資源的 `Cache-Control` 只能出現一份 | `location = /api/health { proxy_pass http://frontend…; }` 放在 `/api/` 區塊之前；靜態資源 location 只留一個 `Cache-Control` 來源 | W5-INFRA（C-15） |

通則：

- nginx 的 `proxy_set_header` **不會**從別的 location 繼承：新增的 location 必須重複 `Host`、`X-Real-IP`、`X-Forwarded-For`、`X-Forwarded-Proto` 四行（或抽成 `include` 片段）；`proxy_pass` 用不含 URI 的形式（`proxy_pass http://backend;`），才會保留原始請求 URI。
- `model.timeout` 的上限（600 秒）大於上表的 180 秒：經 nginx 部署時，超過 180 秒的匯入解析（路徑 B 與 C）會被 nginx 回 504，所以部署時建議 `model.timeout` ≤ 150（附錄 C 的 `impactNote` 已註明）。
- 後端要搭配 `server.forward-headers-strategy=native`（§0.4 第 4 點），限流才看得到真正的客戶端。
- 驗證（W4-QA）：經 nginx 上傳 10MB 檔案（預期 201）、匯入設定檔、`curl.exe -N` 讀 SSE，並以 `docker compose logs nginx` 確認沒有任何 `access_token` 值（E2E-12 步驟 12）。

### 0.8 須同步修改的既有程式與測試（AR-14、AR-16）

Phase 3～6 落地時，下列 Phase 1+2 的既有內容必然受影響；任務書沒有逐項點名，這裡指定「哪一棒改、改成什麼」。**是改，不是刪**：測試的意圖不變，只把真值更新成落地後的樣子。

**既有程式**

| # | 位置 | 改動 | 棒 |
|---|------|------|----|
| 1 | `SecurityConfig` | settings 的非 GET 要求 ADMIN；`/api/v1/stream/**` 接受 `?access_token=`；限流 filter 排在 `JwtAuthenticationFilter` 之後；`dispatcherTypeMatchers(DispatcherType.ASYNC).permitAll()`（§2.1） | B1：settings、限流；B2：stream、ASYNC |
| 2 | `CreateTaskRequest`、`UpdateTaskRequest` | `maxRetries` 在 `@Min(0)` 之外加 `@Max(20)`（訊息 `最大重試次數不可超過 20`）。Bridge 的 `PlaybookIn` 上限是 20，Phase 2 目前允許任意大的值，execute 時會被 Bridge 以 422 拒絕；execute 端另有第 9f 項檢查作第二道防線（AR-14） | B1 |
| 3 | CORS 設定 | `allowedHeaders` 補 `Last-Event-ID`；`exposedHeaders` 補 `X-Follow-Up-Run-Id`、`Retry-After`、`Content-Disposition` | 先做到的那一棒補齊，後一棒核對 |
| 4 | `ErrorResponseDocumentation.CONFLICT_ENDPOINTS`（springdoc 的 409 文件清單） | 補入新的 409 端點 | 各棒補自己的端點 |
| 5 | JSON 欄位名 | `ConfigResponse.isEncrypted`、`CheckpointResponse.isAutomatic` 需 `@JsonProperty`（§0.2） | B1、B2 |
| 6 | JPA 實體 | `ImportRecordEntity` 加 `parse_path`、`last_parse_errors`；`SystemConfigEntity` 加 `impact_note`；（B2）`ExecutionRunEntity` 加 `console_last_seq`，`ReviewRequestEntity`、`AlertEntity` 加 `event_seq`、`event_sub`。`ddl-auto=validate` 要求與 Flyway 一致 | 各棒 |

**既有測試**（類別都在 `backend/src/test/java/com/aisdlc/console/` 之下）

| 測試 | 現況 | B1 交卷時的真值 | B2 交卷時的真值 |
|------|------|-----------------|-----------------|
| `infrastructure/config/OpenApiIT::theDocumentListsExactlyTheEndpointsOfPhaseOneAndTwo`（含 `EXPECTED` 路徑表與類別註解） | `paths` 恰好 13 個（Phase 1+2） | 加入 B1 的 20 個路徑（匯入 9、通知摘要 1、設定 10）；方法與路徑變數名逐字取自 `openapi-p3-6.yaml`；方法改名以免說謊 | 再加入 B2 的 20 個路徑（執行 11、監控 7、SSE 2）；最終 `paths` 共 53 個 |
| `infrastructure/persistence/SchemaMigrationIT::flywayAppliedVersionsOneToFourSuccessfully` | `containsExactly("1","2","3","4")` | 改名；`containsExactly("1","2","3","4","5","6")` | `containsExactly("1","2","3","4","5","6","7")` |
| 同檔 `::seedHasAllSixCategoriesWithTheDocumentedParameterCounts` | `model 9、agent 9、execution 8、monitor 6、autoclaude 5、sdd 4` | `model 10、agent 9、execution 10、monitor 6、autoclaude 11、sdd 4`（共 50，與附錄 C 一致） | 不變 |
| 同檔 `::onlyTheApiKeyIsEncryptedAndItsValueIsEmpty` | `hasSize(1)`，只有 `model.apiKey` | 改名；`hasSize(2)`：`model.apiKey` 與 `autoclaude.dbDsn`，兩者 `value` 皆 `""`、`value_type` 皆 `ENCRYPTED` | 不變 |
| 同檔 `::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic`（不會紅，建議更新） | `CONSOLE_TABLES` 12 張 | 加入 `audit_log` | 加入 `run_token_samples` |

不會紅、不必動的：`StateMachinesTest`、`TaskTest`、`GoalTest`、`ProjectTest`（契約的「系統重設」走專用方法，不改 `StateMachines` 的轉移表，§3.5.3）；`AuditLogIT`、`RbacIT`、`ResponseEnvelopeIT`（以 contains 與筆數斷言）。

**v1.2 追加（W5-BE 同步；同樣是改，不是刪）**

| 測試／程式 | 改動 |
|-----------|------|
| `OpenApiIT` 的 `EXPECTED` 路徑表 | 再加 2 個路徑——`GET /api/v1/monitor/task-totals`、`POST /api/v1/projects/{id}/restore`（`GET /api/v1/projects` 只多一個 `deleted` 查詢參數，不是新路徑）；路徑 53→55、操作 62→64；`DELETE /api/v1/goals/{id}`、`DELETE /api/v1/tasks/{id}` 的 409 文件化；`GET /api/v1/monitor/projects/{projectId}/report` 的 501 文件化移除 |
| `SchemaMigrationIT` | Flyway 版本改 `containsExactly("1",…,"9")`；`import_records` 多 `warnings`、`parse_options`；`projects` 多 `deleted_at`、`status_before_delete`；`goals`／`tasks` 多 `deleted_at`；`V5UpgradeMigrationIT` 的升級帶資料測試補 V8、V9 |
| `ErrorResponseDocumentation` | `CONFLICT_ENDPOINTS` 補 restore 與兩個 DELETE；`NotImplementedYetException` 與 `ErrorReasons.PDF_NOT_AVAILABLE` 一併移除（C-4） |
| `ProjectController`／`SecurityConfig` | `GET /api/v1/projects?deleted=true` 由 controller 檢查角色（VIEWER → 403 `ACCESS_DENIED`），不必動 matcher；`POST /api/v1/projects/{id}/restore` 落在既有的「GET 之外一律 OPERATOR 以上」規則 |
| `ConfigCatalog` | `execution.globalTokenBudget` 的 `max` 常數由 `1000000000000` 改 `999999999999`（與 V5 的 `validation_rule` 一致，附錄 C.3；B1-1） |

**v1.3 追加（W7-BE 同步；同樣是改，不是刪）**

| 測試／程式 | 改動 |
|-----------|------|
| `ConfigMaterializer` | `materialize()` 改為 `materialize(int autonomyLevel)`，回傳 `Materialized(configOverrides, env, engineCapabilities)`。`RunLauncher` 在**交易 1 之前**呼叫一次，結果同時用於 `execution_runs.engine_capabilities` 的 INSERT 與 Bridge 請求（現況是交易 1 之後才呼叫，兩次讀設定之間設定可能被改，§3.4.2 的一致性規則）。`resume`／`restore`／審核 `APPROVE` 只用 `.env()`（現況不變），其 `autonomyLevel` 取該 run 的 `autonomy_level` |
| `ConfigMaterializerTest` | 補決策表測試：等級 {1, 5, 6, 7, 10} × 金鑰有／無 × `agent.enableAutoMutation`／`agent.enableSelfEvolution`／`model.enableKernelBrain` 各自為真的組合（§3.4.2 決策表的 8 列每列至少一支），逐一斷言送出的鍵、`env`、`engineCapabilities`；另斷言**永不送**的鍵（`playbook.max_evolutions`、`playbook.require_evolution_signoff` 等，§3.4.2）在任何組合下都不出現在 `configOverrides` |
| `ConfigCatalog` | `agent.enableAutoMutation` 的 effect `UNVERIFIED→ENGINE`；`agent.enableSelfEvolution` `UNVERIFIED→STORED_ONLY`；三個鍵的 `impactNote` 與附錄 C.1／C.2 逐字相同 |
| `ExecutionRun`／`ExecutionRunEntity`／`ExecutionRunResponse` | 加 `engineCapabilities`（§1.2.1；V10；實體 `updatable=false`） |
| `AgentBridge.RunSnapshot`／`BridgeInfoView`／`BridgeInfoDto` | 加 `resources`（§3.1.2）；Bridge 回應缺這個鍵（舊版 Bridge）視為 null |
| `SchemaMigrationIT` | Flyway 版本改 `containsExactly("1",…,"10")`；`execution_runs` 多 `engine_capabilities`（jsonb、可 NULL）；三個鍵的 `impact_note` 等於附錄 C 的文字；`V5UpgradeMigrationIT` 的升級帶資料測試補 V10（既有批次列升級後 `engine_capabilities` 為 NULL） |
| `ExecutionLifecycleApiIT` | 補 IT：execute 201 與 `GET` 詳情的 `engineCapabilities`（有金鑰／無金鑰各一）；詳情的 `bridge.resources`（迷你 Bridge 回 `resources`、不回、回 null 三種） |
| `OpenApiIT` | 不必改：沒有新路徑，`ExecutionRunResponse`／`BridgeInfo` 只加欄位 |

**v1.4 追加（W7-BE／W7-FE 同步；同樣是改，不是刪）**

| 測試／程式 | 改動 |
|-----------|------|
| `OpenApiIT` 的 `EXPECTED` 路徑表 | 再加 3 個路徑——`GET /api/v1/engines/sdd`、`GET /api/v1/signoffs/pending`、`POST /api/v1/auth/logout`；路徑 55→58、操作 64→67（數字承接 v1.2，v1.3 沒有新路徑）；`/api/v1/auth/logout` 的 `post.security` 為空陣列（比照 `/auth/refresh`，現有斷言見 `OpenApiIT.java:132`） |
| `SecurityConfig` | `POST /api/v1/auth/logout` 加進 `permitAll` 清單（現為 login、refresh，`SecurityConfig.java:74`）；`GET /api/v1/engines/**`、`GET /api/v1/signoffs/**` 落在既有「`GET /api/v1/**` 為 VIEWER 以上」規則，不必動 matcher；`RbacIT` 補：VIEWER 對兩個新 GET 回 200、未認證回 401 |
| `TokenIssuer`／`JwtTokenService`／`AuthService`／`AuthController` | `RefreshIdentity` 加 `tokenId`（`jti`；`JwtTokenService.build` 已為每個 token 簽發 `.id(UUID)`，不必改簽發）與 `expiresAt`；`AuthService.refresh` 改為「驗證 → `tryRevoke(tokenId, expiresAt)`（回 false 即 401 `INVALID_REFRESH_TOKEN`）→ 查帳號 → 簽發新一對」；新增 `AuthUseCase.logout(refreshToken)` 與 `AuthController` 的 `POST /logout`（204，`LogoutRequest{refreshToken}`）；`AuthApiIT` 補 §1.9.2 驗收的各項行為 |
| 新增：`RefreshTokenRevocations`（port）與實作 | `application.port.out.RefreshTokenRevocations`；`infrastructure.security` 放 Redis 實作、記憶體實作與降級包裝（§1.9.2）；`build.gradle.kts` 加 `spring-boot-starter-data-redis`（附錄 D.4）；`application.yml` 設 `management.health.redis.enabled=false` 與 `console.security.refresh-revocation.store=auto`（附錄 D.2）；ArchUnit A2／A5 不得被新相依弄紅（port 在 application、實作在 infrastructure，與 `JwtTokenService` 實作 `TokenIssuer` 同一形態） |
| 新增：待審批清單 | 建議 `application.port.out.SignoffQueue`（或延伸 `NotificationCounts`）＋ `adapter.in.web.SignoffsController`；**`pendingSignoffs` 計數與清單的述詞必須由同一處產生**（§1.8.1）——`NotificationCountsAdapter.PENDING_SIGNOFFS` 的四段 `count(*)` 與新的清單查詢不得各寫一份；新增 `SignoffsPendingApiIT` 與一支不變量 IT（`counts.total` 等於 `GET /notifications/summary` 的 `pendingSignoffs`，E2E 另驗一次） |
| `AgentBridge`／`BridgeHttpAdapter`／`BridgeEndpoints` | 新增 `sddVersion()`、`sddFsmList()`、`sddFsm(project)`（基底取 `sddBase()`，讀取逾時 3 秒，不重試）；`health()` 的讀取逾時 3→8 秒（`HEALTH_READ_TIMEOUT`，§3.1）；`BridgeEndpoints.DEFAULT_HEALTH_PATH`（`BridgeEndpoints.java:15`）`/health`→`/health/deep`；`BridgeHttpAdapterTest` 補 SDD 三個呼叫（200、503 `sdd_unavailable`、404 `fsm_not_found`、422 `fsm_state_unreadable`、連線失敗、逾時）與「探測的 503 計為失敗」 |
| 新增：`EnginesController`＋`SddEngineQueryService` | §1.7.1；Bridge 失敗一律轉成 200＋`available=false`（不是 502）；`project` 以 `^[A-Za-z0-9._-]{1,128}$` 驗證，不合 400；新增 `EnginesApiIT`（以迷你 Bridge 驗映射表的每一列） |
| `BridgeHealthMonitor` 相關測試 | 預設探測路徑 `/health/deep`；503 與連線失敗皆計為失敗；測試用的迷你 Bridge（`MiniBridgeController`）補 `GET /health/deep`（預設 200，可切換 503）與 `/sdd/version`、`/sdd/fsm`、`/sdd/fsm/{project}` 三個唯讀路由 |
| `SchemaMigrationIT` | Flyway 版本改 `containsExactly("1",…,"11")`；V11 的三種情形（§0.5 V11）；`V5UpgradeMigrationIT` 的升級帶資料測試補 V11 |
| 前端 | `lib/api/endpoints.ts` 加 `getSddEngine(project?)`、`getPendingSignoffs(limit?)`、`logout(refreshToken)`；`lib/auth/AuthProvider.tsx` 的 `logout()` 先 fire-and-forget 呼叫 `logout`；`useSignoffQueue` 改以 `getPendingSignoffs` 為資料來源（§4.5 G-10）；mock fixture（`tests/e2e/settingsFixture.ts` 的 `healthCheckPath` 預設）與 e2e 的假 Bridge 補 `/health/deep`（§5.0.1） |

**v1.5 追加（W2-Bridge／W3-BE／W3-FE 同步；同樣是改，不是刪；已與 ADR-016 對齊）**

| 測試／程式 | 改動 |
|-----------|------|
| `OpenApiIT` 的 `EXPECTED` 路徑表 | 再加 3 個路徑——`POST /api/v1/projects/{id}/sdd/freeze`、`GET /api/v1/executions/{runId}/rtm`、`PUT /api/v1/projects/{id}/sdd-binding`；路徑 58→61、操作 67→70；`GET /api/v1/engines/sdd` 多一個 `projectId` 查詢參數與 404 文件化、`POST /api/v1/projects/{projectId}/execute` 的 201 schema 多 `warnings`、`POST /api/v1/import/{id}/parse` 的請求 schema 多 `targetProjectId`（皆不是新路徑） |
| `SchemaMigrationIT` | Flyway 版本改 `containsExactly("1",…,"12")`；`projects` 多三欄（varchar 100／500／500、可 NULL）與部分唯一索引 `ux_projects_sdd_binding`；`V5UpgradeMigrationIT` 的升級帶資料測試補 V12（既有專案升級後三欄為 NULL） |
| `SecurityConfig`／`RbacIT` | 不必動 matcher：freeze、sdd-binding 落在「GET 之外一律 OPERATOR 以上」、rtm 落在「`GET /api/v1/**` 為 VIEWER 以上」；`RbacIT` 補：VIEWER 對 freeze、sdd-binding 回 403、對 rtm 回 200，未認證三者皆 401 |
| `ErrorResponseDocumentation` | `CONFLICT_ENDPOINTS` 補 freeze、sdd-binding 與 confirm（併入）；rtm 的 404 `rtm_not_found` 與 freeze／execute／resume／restore 的 503 `sdd_write_disabled` 文件化 |
| `application.yml`／`BridgeProperties`／`docker-compose.yml`／`.env.example` | `console.bridge.sdd-write-token`（`${BRIDGE_SDD_WRITE_TOKEN:}`；有設但短於 32 字元或仍是 `<…>` 佔位⇒啟動失敗）；compose 對 backend 與 engine-bridge 都傳 `BRIDGE_SDD_WRITE_TOKEN: ${BRIDGE_SDD_WRITE_TOKEN:-}`；`.env.example` 只放 `<YOUR_BRIDGE_SDD_WRITE_TOKEN_MIN_32_CHARS>`（ADR-016 §9） |
| `AgentBridge`／`BridgeHttpAdapter`／`BridgeEndpoints` | `SddTask` 加 `maxRetries`、`maintainContext`、`specDigest`；`SddCompileResult` 加 `specFile`、`fsmProject`、`frozenDigest`、`specFormatVersion`、`unmappedAtIds`、`warnings`（既有的 `specPath` 供回填）；`sddCompile(specDir, specFile, fsmProject)`；`StartRunRequest` 加 `sdd`；新增 `sddFreeze(project, request)`（POST，2 秒／40 秒，不重試）、`getRunRtm(runId)`（GET，2 秒／3 秒，不重試）；`sddFsmList(root)`、`sddFsm(project, root)` 加選填 `root`；`startRun` 的讀取逾時依是否帶 `sdd` 取 30／90 秒；`resumeRun`、`restoreRun` 的讀取逾時由 15 秒改 30 秒（主控裁決；§3.1 呼叫表）；`X-Bridge-Token` 附在 `sddFreeze`、帶 `sdd` 的 `startRun`，以及 `resumeRun`、`restoreRun`（D-115-18：SDD run 的這兩個呼叫也驗權杖；console-api 不記錄批次是否為 SDD，所以一律附，由 Bridge 只對 SDD run 驗），**不得寫進日誌、錯誤封包或 `details`** |
| 新增：SDD 治理用例（建議名 `SddGovernanceService`） | freeze 用例（approver＝JWT subject、稽核、唯讀 GET 取標準鍵、綁定唯一性先檢查後寫入與寫回、錯誤對映，§1.10.2）；binding 編輯（§1.10.7）；`projectId`→`root` 與有效 FSM 專案的解析（與 `SddEngineQueryService` 共用，§1.10.4、§1.10.5）；SDD 批次資格判定與 `sdd` 區塊組裝（§1.10.6）；`ErrorReasons` 補附錄 B.5 的五個常數 |
| `ImportParser`／`ParseOptions`／`ParsedResult`／`ImportService.confirm`／`NewProject` | `ParseOptions` 加 `specFile`、`sddProject`、`targetProjectId`；`ParsedResult` 加四個伺服器擁有欄位；`sddTask()` 填 `maxRetries` 並把 `maintainContext` 放進 `passCriteriaSpec`；`confirm` 帶 `targetProjectId` 時併入目標專案（§1.10.8）、否則把綁定帶進新專案；新增 `at_unmapped`、`frozen_digest_absent`、`state_dir_not_ignored` 警告；🔴 `ImportParser.probeSpec` 對 409 `spec_digest_changed` 明確丟拒絕（不得降級成略過路徑 A；回歸測試具名，§3.3.2 第 9 點） |
| `ExecutionPlanner`／`PlaybookBuilder`／`RunLauncher` | SDD 批次的 step_id 沿用 `passCriteriaSpec.stepId`（`dag.nodes[].stepId` 同）；playbook 任務多送 `maintain_context`、`spec_digest`、`weak_regex`；`RunLauncher` 依資格送 `sdd` 區塊並把 `warnings`（含 Bridge 回的 `sdd_frozen_digest_absent`）放進 execute 的 201；補償刪除規則不變（§3.4.1）；resume／restore 對 SDD run 的 Bridge 失敗對映（§3.2） |
| `MiniBridge`（測試用迷你 Bridge） | 補 `POST /sdd/fsm/{project}:freeze`（可切換 200／403／409／503）、`GET /autoclaude/runs/{id}/rtm`（有資料／404／422 三種）、`GET /sdd/fsm?root=`、`GET /sdd/fsm/{project}`（新欄位）、`/sdd/compile` 的新請求與回應欄位（含 409）；`POST /autoclaude/runs` 收 `sdd` 區塊 |
| 前端 | `lib/api/endpoints.ts` 加 `freezeProjectSdd(id, body)`、`updateProjectSddBinding(id, body)`、`getExecutionRtm(runId)`；`getSddEngine` 加 `projectId`；`lib/domain/sdd.ts` 加階段字典與顯示規則（§4.7）；專案詳情「SDD 治理」區、執行詳情「追溯覆蓋（諮詢）」面板與 SDD 卡的階段進度為新元件；匯入頁加「併入既有專案」選擇；mock fixture 與 e2e 的假 Bridge 補上述路由 |

---
## 1. 端點總表與逐端點契約

### 1.0 總表（45 個端點；SSE 兩條詳見 §2；#41～#42 為 v1.2 新增、#43～#45 為 v1.4 新增；v1.5 另增 #46～#48，共 48 個）

「補」＝PRD 未列、為設計稿或 Architecture 所需的補充端點（§6 D-05、D-10…）。Phase 2 已實作的 `POST /projects|goals|tasks/{id}/signoff`（`API-SGN-02～04`）不重複定義。

| # | 方法 路徑 | 角色 | Request → Response（成功碼） | RTM／US |
|---|-----------|------|------------------------------|---------|
| 1 | `GET /api/v1/import` | VIEWER | 查詢參數 → `Page<ImportRecordResponse>`（200） | API-IMP-06／US-I-06 |
| 2 | `POST /api/v1/import/upload` | OPERATOR | multipart `file` → `ImportRecordResponse`（201） | API-IMP-01、07／US-I-01 |
| 3 | `POST /api/v1/import/text` | OPERATOR | `TextImportRequest` → `ImportRecordResponse`（201） | API-IMP-02／US-I-02 |
| 4 | `GET /api/v1/import/{id}`（補） | VIEWER | → `ImportRecordDetailResponse`（200） | API-IMP-06／US-I-03、06 |
| 5 | `POST /api/v1/import/{id}/parse` | OPERATOR | `ParseOptions` → `ParseResultResponse`（200） | API-IMP-03、08、09／US-I-03、05、07、08、10 |
| 6 | `PUT /api/v1/import/{id}/result` | OPERATOR | `EditParsedResultRequest` → `ParseResultResponse`（200） | API-IMP-04／US-I-04、10 |
| 7 | `POST /api/v1/import/{id}/signoff` | OPERATOR | `SignoffRequest` → `ImportRecordResponse`（200） | API-SGN-01／US-I-09 |
| 8 | `POST /api/v1/import/{id}/confirm` | OPERATOR | — → `ProjectResponse`（201） | API-IMP-05、10／US-I-09 |
| 9 | `POST /api/v1/import/{id}/reject`（補） | OPERATOR | — → `ImportRecordResponse`（200） | API-IMP-10 |
| 10 | `POST /api/v1/projects/{projectId}/execute` | OPERATOR | `StartExecutionRequest` → `ExecutionRunResponse`（201） | API-EXE-01、11、12、13／US-E-01、02、10 |
| 11 | `GET /api/v1/projects/{projectId}/executions`（補） | VIEWER | 查詢參數 → `Page<ExecutionRunSummaryResponse>`（200） | API-EXE-14／US-M-06 |
| 12 | `GET /api/v1/executions/{runId}` | VIEWER | → `ExecutionRunDetailResponse`（200） | API-EXE-05／US-E-07、M-10 |
| 13 | `POST /api/v1/executions/{runId}/pause` | OPERATOR | — → `ExecutionRunResponse`（200） | API-EXE-02／US-E-04 |
| 14 | `POST /api/v1/executions/{runId}/resume` | OPERATOR | — → `ExecutionRunResponse`（200） | API-EXE-03、11／US-E-05 |
| 15 | `POST /api/v1/executions/{runId}/cancel` | OPERATOR | — → `ExecutionRunResponse`（200） | API-EXE-04／US-E-06 |
| 16 | `GET /api/v1/executions/{runId}/steps` | VIEWER | `page,size,afterSeq` → `Page<ExecutionStepResponse>`（200） | API-EXE-06、SSE-03／US-M-03、09 |
| 17 | `GET /api/v1/executions/{runId}/dag` | VIEWER | → `DagResponse`（200） | API-EXE-07、DAG-01／US-E-09 |
| 18 | `GET /api/v1/executions/{runId}/checkpoints` | VIEWER | → `List<CheckpointResponse>`（200） | API-EXE-08／US-E-11 |
| 19 | `POST /api/v1/executions/{runId}/restore/{checkpointId}` | OPERATOR | — → `ExecutionRunResponse`（200） | API-EXE-09、11／US-E-11 |
| 20 | `POST /api/v1/executions/{runId}/review/{stepId}` | OPERATOR | `ReviewRequest` → 無內容（204） | API-EXE-10、AUT-01～06／US-E-07、08 |
| 21 | `GET /api/v1/monitor/projects/{projectId}/metrics` | VIEWER | `runId,from,to` → `ProjectMetricsResponse`（200） | API-MON-01／US-M-01、10 |
| 22 | `GET /api/v1/monitor/projects/{projectId}/token-trend` | VIEWER | `runId,from,to,bucket` → `List<TokenTrendPoint>`（200） | API-MON-02／US-M-02 |
| 23 | `GET /api/v1/monitor/projects/{projectId}/task-trend` | VIEWER | 同上 → `List<TaskTrendPoint>`（200） | API-MON-03／US-M-03 |
| 24 | `GET /api/v1/monitor/projects/{projectId}/alerts` | VIEWER | `runId,acknowledged,limit` → `List<AlertResponse>`（200） | API-MON-04、ALR-01～06／US-M-05 |
| 25 | `POST /api/v1/monitor/alerts/{alertId}/acknowledge` | OPERATOR | — → 無內容（204） | API-MON-05／US-M-05 |
| 26 | `GET /api/v1/monitor/projects/{projectId}/logs` | VIEWER | 篩選＋分頁 → `Page<LogEntryResponse>`（200） | API-MON-06／US-M-04 |
| 27 | `GET /api/v1/monitor/projects/{projectId}/report` | VIEWER | `format=csv\|pdf,…` → 檔案（200） | API-MON-07／US-M-07 |
| 28 | `GET /api/v1/notifications/summary`（補） | VIEWER | → `NotificationSummaryResponse`（200） | API-NTF-01／US-E-07 |
| 29 | `GET /api/v1/stream/executions/{runId}/logs` | VIEWER | SSE（§2） | API-SSE-01、03／US-E-03、07 |
| 30 | `GET /api/v1/stream/executions/{runId}/metrics` | VIEWER | SSE（§2） | API-SSE-02、03／US-E-03 |
| 31 | `GET /api/v1/settings` | VIEWER | `reveal` → `Map<category,List<ConfigResponse>>`（200） | API-SET-01／US-S-01、04、08 |
| 32 | `GET /api/v1/settings/{category}` | VIEWER | `reveal` → `List<ConfigResponse>`（200） | API-SET-02／US-S-01、04 |
| 33 | `PUT /api/v1/settings/{category}/{key}` | ADMIN | `UpdateConfigRequest` → `ConfigResponse`（200） | API-SET-03、10／US-S-02、08 |
| 34 | `PUT /api/v1/settings/execution/token-guard` | ADMIN | `TokenGuardRequest` → `List<ConfigResponse>`（200） | API-SET-04／NFR-SEC-05 |
| 35 | `POST /api/v1/settings/{category}/{key}/reset` | ADMIN | `confirm` → `ConfigResponse`（200） | API-SET-05／US-S-03 |
| 36 | `POST /api/v1/settings/{category}/reset`（補） | ADMIN | `confirm` → `List<ConfigResponse>`（200） | API-SET-05／US-S-03 |
| 37 | `POST /api/v1/settings/test-connection` | ADMIN | `TestConnectionRequest?` → `ConnectionTestResponse`（200） | API-SET-06／US-S-05／NFR-SEC-04 |
| 38 | `GET /api/v1/settings/history` | VIEWER | 篩選＋分頁 → `Page<ConfigHistoryResponse>`（200） | API-SET-07／US-S-07 |
| 39 | `POST /api/v1/settings/export` | ADMIN | — → `SettingsExportDocument`（200，檔案） | API-SET-08／US-S-06 |
| 40 | `POST /api/v1/settings/import` | ADMIN | multipart `file` → `ImportSettingsResponse`（200） | API-SET-09／US-S-06 |
| 41 | `GET /api/v1/monitor/task-totals`（v1.2 補，C-1） | VIEWER | `from,to` → `TaskTotalsResponse`（200） | API-MON-08／US-M-03 |
| 42 | `POST /api/v1/projects/{id}/restore`（v1.2 補，C-3；Phase 2 資源） | OPERATOR | — → `ProjectDetailResponse`（200） | API-PRJ-06／NFR-9.3-04 |
| 43 | `GET /api/v1/engines/sdd`（v1.4 補，D-16） | VIEWER | `project?` → `SddEngineStatusResponse`（200；Bridge 不可達也回 200） | API-ENG-01／NFR-OBS-01、BR-13、BR-14 |
| 44 | `GET /api/v1/signoffs/pending`（v1.4 補，D-18） | VIEWER | `limit?` → `PendingSignoffsResponse`（200） | API-SGN-05／US-E-07 |
| 45 | `POST /api/v1/auth/logout`（v1.4 補，D-19；Phase 1+2 資源，免認證） | 免認證 | `LogoutRequest` → 無內容（204） | API-AUTH-03 |
| 46 | `POST /api/v1/projects/{id}/sdd/freeze`（v1.5 補，D-115-03；Phase 2 資源） | OPERATOR | `SddFreezeRequest` → `SddFsmState`（200） | API-SGN-06、API-PRJ-07 |
| 47 | `GET /api/v1/executions/{runId}/rtm`（v1.5 補，G-05） | VIEWER | → `ExecutionRtmResponse`（200；沒有報告為 404 `rtm_not_found`） | API-EXE-16 |
| 48 | `PUT /api/v1/projects/{id}/sdd-binding`（v1.5 補，D-115-14；Phase 2 資源） | OPERATOR | `SddBindingRequest` → `ProjectDetailResponse`（200；唯一性衝突為 409 `sdd_binding_conflict`） | API-PRJ-08 |

v1.2 另有三處是改動 Phase 2 既有端點（不編號，詳見 §1.6）：`GET /api/v1/projects` 新增查詢參數 `deleted`（§1.6.2）；`DELETE /api/v1/goals/{id}`、`DELETE /api/v1/tasks/{id}` 新增 409 `project_executing`（§1.6.3）；`POST /api/v1/tasks/{id}/retry` 的「不受 `maxRetries` 限制」明文（§1.6.4）。

v1.5 另有改動既有端點與 schema 的幾處（不編號，詳見 §1.10）：`GET /api/v1/engines/sdd` 新增 `projectId` 查詢參數與回應欄位 `phase`、`escalationHistory`、`escalationProvenance`、`fsmProject`、`recovery`（§1.10.4）；`POST /api/v1/projects/{projectId}/execute` 新增 SDD 批次行為與 201 的 `warnings[]`（§1.10.6）；`ProjectResponse`／`ProjectDetailResponse` 新增綁定三欄（§1.10.5）；匯入的 `ParseOptions`（含 `targetProjectId`）／`ParsedResult`／`ParseWarning` 新增欄位與警告碼，`confirm` 可併入既有專案（§1.10.8、§3.3.2）。

---

### 1.1 BRD/PRD 匯入（Phase 3）

匯入記錄狀態機（`API-IMP-10`）：

```
UPLOADED ──parse──▶ PARSING ──成功──▶ PARSED ──PUT result──▶ REVIEWING
   ▲                   │失敗(422／502／504)│                      │
   └───────────────────┘                  └────signoff／confirm───┘ ──confirm──▶ IMPORTED
任一非終態 ──reject──▶ REJECTED        （IMPORTED、REJECTED 為終態）
```

| 目前狀態 | parse | PUT result | signoff | confirm | reject |
|----------|:-----:|:----------:|:-------:|:-------:|:------:|
| UPLOADED | ✅ | ✗ | ✗ | ✗ | ✅ |
| PARSING | ✗ | ✗ | ✗ | ✗ | ✗ |
| PARSED | ✅（未 signoff） | ✅ | ✅ | ✅（需已 signoff） | ✅ |
| REVIEWING | ✅（未 signoff） | ✅（撤銷 signoff） | ✅ | ✅（需已 signoff） | ✅ |
| IMPORTED／REJECTED | ✗ | ✗ | ✗ | ✗（IMPORTED 回 `已匯入`） | ✗ |

✗ 一律 409：reason `匯入記錄狀態不允許此操作`，`details={action, status}`（`action` ∈ `parse|editResult|signoff|confirm|reject`）。**表內唯一的例外**（AR-21）：狀態為 `PARSING` 時再 `parse`，回 409 `解析中，請稍候`（`details={status:"PARSING"}`）——其餘動作在 `PARSING` 仍是上述的「狀態不允許」。`parse` 的前置檢查順序固定為：`IMPORTED`／`REJECTED` → `匯入記錄狀態不允許此操作`；`PARSING` → `解析中，請稍候`；已 signoff → `已 signoff，不可重新解析`。

#### 1.1.1 `POST /api/v1/import/upload`　上傳檔案　〔API-IMP-01、API-IMP-07／US-I-01〕

- **角色**：OPERATOR。**Bridge**：無。
- **Request**：`multipart/form-data`，欄位 `file`（必填）。副檔名限 `.md`／`.pdf`／`.docx`（不分大小寫）；大小 ≤ 10 MB（10,485,760 bytes；Spring `max-file-size=10MB`、`max-request-size=11MB`）。
- **文字擷取**（後端，存入 `import_records.source_content`；檔名只留 basename、≤ 500 字元）：`.md` 以嚴格 UTF-8 解碼（BOM 容許）；`.pdf` 用 Apache PDFBox 逐頁抽文字；`.docx` 用 Apache POI XWPF 依序抽段落與表格儲存格文字（儲存格以 tab 分隔、段落以換行）。先驗魔術位元組（`%PDF-`／ZIP `PK\x03\x04`）再解析。
- **成功 201**：`ApiResult<ImportRecordResponse>`；`status=UPLOADED`、`signedOff=false`、`sourceType` 依副檔名為 `MARKDOWN`／`PDF`／`DOCX`。

```json
{ "code":201, "message":"success", "data":{
    "id":"7d9f3b52-1c0a-4e8e-9a43-5f6b2c1d8e01", "sourceType":"MARKDOWN", "sourceFileName":"e2e-brd.md",
    "status":"UPLOADED", "signedOff":false, "createdAt":"2026-10-15T08:30:12Z" },
  "timestamp":"2026-10-15T16:30:12+08:00", "traceId":"0f7c2a58-4e1d-4b29-9d3e-6a1b5c8d9e02" }
```

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | `未提供檔案` | — | 沒有 `file` 部件 |
| 400 | `檔案是空的` | — | 0 bytes |
| 413 | `檔案超過 10MB 上限` | `{limitBytes:10485760}` | `MaxUploadSizeExceededException` |
| 415 | `只支援 .md／.pdf／.docx 檔案` | `{extension, allowed:[".md",".pdf",".docx"]}` | 副檔名不在清單 |
| 422 | `檔案內容與副檔名不符` | `{extension}` | 魔術位元組不符 |
| 422 | `檔案不是有效的 UTF-8 文字` | — | `.md` 解碼失敗 |
| 422 | `PDF 已加密，無法擷取文字` | — | 需要密碼 |
| 422 | `檔案已損毀，無法讀取` | — | PDFBox／POI 解析例外 |
| 422 | `無法從檔案擷取文字` | — | 擷取後全為空白（例：掃描檔） |
| 401／403／429 | 通用 | | |

#### 1.1.2 `POST /api/v1/import/text`　貼上純文字　〔API-IMP-02／US-I-02〕

- **角色**：OPERATOR。**Bridge**：無。
- **Request**（`TextImportRequest`）：

| 欄位 | 型別 | 必填 | 規則 |
|------|------|:----:|------|
| `content` | string | ✅ | 1～2,000,000 字元；不可全為空白 |
| `sourceFileName` | string | — | ≤ 500；省略時存 null |
| `sourceType` | `PLAIN_TEXT`｜`MARKDOWN` | — | 預設 `PLAIN_TEXT`；其他值 400（`PDF`／`DOCX` 只能由 upload 產生） |

- **成功 201**：`ImportRecordResponse`（同 1.1.1）。
- **錯誤**：400 Bean Validation（`errors=[{field:"content",message:"內容不可為空"}]`，reason 省略）；401／403／429 通用。

#### 1.1.3 `POST /api/v1/import/{id}/parse`　觸發 AI 解析　〔API-IMP-03、08、09／US-I-03、05、07、08、10〕

- **角色**：OPERATOR。**Bridge**：路徑 A／C 會呼叫（§3.3）。**同步**呼叫（UI「解析中」），路徑 B 的逾時＝`model.timeout` 秒；反向代理須放寬 read timeout（180 秒）與上傳大小，見 §0.7。
- **Request**（`ParseOptions`）：

| 欄位 | 型別 | 必填 | 規則 |
|------|------|:----:|------|
| `executionPath` | string | ✅ | ≤ 500；絕對路徑格式（POSIX `/…`、磁碟機 `C:\…` 或 `C:/…`、UNC `\\host\share`）；不得含 NUL。Bridge 的 allowlist 在執行時才驗（ADR-001 G-15：不提供瀏覽按鈕） |
| `autonomyLevel` | int | — | 1～10，預設 3；成為落庫專案的 `autonomyLevel` |
| `additionalPrompt` | string | — | ≤ 4,000 |
| `specDir` | string | — | ≤ 500；明示的 SDD 規格目錄（絕對路徑）。省略＝以 `executionPath` 探測 |

- **處理**：狀態 `PARSING`（同時清空 `last_parse_errors`，並把本次請求的 `ParseOptions` 原樣存進 `parse_options`，V8，§0.5）→ 依 §3.3 選路徑與轉換 → 套三道有界閘與 `prompt_too_long`。
  - **成功**：存 `parsed_result`、`parse_path`、`ai_model`、`token_used`、`warnings`（V8），狀態 `PARSED`、`signedOff=false`。
  - **失敗**（有界閘 422、SDD 規格被拒 422、Bridge 不可達 502／504、模型端失敗 `brain_*`）：狀態一律退回 `UPLOADED`。僅「被有界閘拒絕」時把 `errors[]` 存進 `last_parse_errors`（V5 新增的 JSONB 欄位，AR-07）；非閘的失敗不寫（錯誤只在該次回應裡）。**失敗不寫 `parsed_result` 與 `parse_path`**：兩者在第一次成功解析前一律為 NULL（任務書的 `parsed_result.error` 作廢）；`warnings` 同樣不動（保留上一次成功的值）；`parse_options` 已在進入 `PARSING` 時寫入，失敗後仍保留（讓使用者重開記錄時選項還在）。
  - 先前成功解析過的記錄再次 parse（僅未 signoff 者可以）：失敗時狀態同樣退回 `UPLOADED`，但**保留**上一次成功的 `parsed_result`（使用者的編輯內容不因一次失敗的重解析而消失）；`GET /import/{id}` 仍可讀到它；但記錄已回到 `UPLOADED`，要繼續編輯或 signoff 須再成功解析一次。
- **成功 200**：`ParseResultResponse`（欄位逐一說明見 §3.3.6）：

```json
{ "code":200, "message":"success", "data":{
    "importId":"7d9f3b52-1c0a-4e8e-9a43-5f6b2c1d8e01", "status":"PARSED", "path":"LLM",
    "signedOff":false, "aiModel":"e2e-model", "tokenUsed":1152, "errors":[], "warnings":[],
    "parsedResult":{
      "project":{ "name":"E2E 匯入專案", "executionPath":"<E2E_ROOT>/proj-import",
                  "passCriteria":"三個目標全部完成", "description":"由 BRD 匯入", "autonomyLevel":3 },
      "goals":[
        { "key":"g1", "name":"基礎", "passCriteria":"基礎任務完成", "sortOrder":0, "dependsOn":[],
          "tasks":[ { "name":"初始化", "description":"請輸出 [T1_DONE]", "passCriteria":"輸出含 [T1_DONE]", "sortOrder":0 } ] },
        { "key":"g2", "name":"核心", "passCriteria":"核心任務完成", "sortOrder":1, "dependsOn":["g1"],
          "tasks":[ { "name":"實作", "description":"請輸出 [T3_DONE]", "passCriteria":"輸出含 [T3_DONE]", "sortOrder":0 } ] } ],
      "path":"LLM", "aiModel":"e2e-model", "tokenUsed":1152 } },
  "timestamp":"2026-10-15T16:30:14+08:00", "traceId":"…" }
```

| HTTP | reason | details／errors | 觸發 |
|------|--------|-----------------|------|
| 400 | （Bean Validation） | `errors=[{field:"executionPath",message:"必須是絕對路徑"}…]` | 欄位驗證 |
| 404 | （訊息）`匯入記錄不存在或已刪除：<id>` | — | |
| 409 | `解析中，請稍候` | `{status:"PARSING"}` | 狀態為 PARSING 時再 parse（含同一筆的並發呼叫） |
| 409 | `已 signoff，不可重新解析` | `{signedOffBy,signedOffAt}` | |
| 409 | `匯入記錄狀態不允許此操作` | `{action:"parse",status}` | IMPORTED／REJECTED |
| 422 | `解析結果未通過有界閘` | `errors[]` 每項 `{field,message,gate,detail,location?}`（**列出全部違規**）；`field`＝`location`（沒有 location 的閘退回**閘名**，例：`brain_failed`、`brain_unsupported`），`message`＝`detail`（B1-3；`ApiError.FieldError.ofGate`）；`details={path}` | §3.3.5 |
| 422 | `SDD 規格檢查未通過` | `details={bridgeReason,detail}`；`errors=[{field:"specDir",message}]` | 規格存在但被 Bridge 拒（`spec_not_frozen`／`spec_tainted`／`spec_format_version_unsupported`／`spec_ambiguous`；明示 `specDir` 時 `spec_not_found` 與路徑消毒失敗亦同） |
| 502／504 | `引擎橋接服務無法連線`／`引擎橋接服務逾時` | | 路徑 A（明示 specDir）或 C 的 Bridge 不可達 |
| 401／403／429 | 通用 | | |

- **v1.5（D-115-14）**：`ParseOptions` 另有選填欄位 `specFile`、`sddProject`、`targetProjectId`（路徑 A；規則見 §3.3.2 的 v1.5 補充與 §1.10.8）。帶 `targetProjectId` 時多出：404（訊息 `專案不存在或已刪除：<id>`，無 reason）與 409 `sdd_binding_conflict`（`details={cause, field?, …}`，附錄 B.5）；`SDD 規格檢查未通過` 的 `bridgeReason` 另可能是 `spec_digest_changed`（凍結後規格內容已變更，探測模式同樣 fail-closed）。解析結果 `warnings[]` 另有 `at_unmapped`、`frozen_digest_absent`、`state_dir_not_ignored`。

#### 1.1.4 `PUT /api/v1/import/{id}/result`　編輯解析結果　〔API-IMP-04／US-I-04、10〕

- **角色**：OPERATOR。**Bridge**：無。
- **Request**（`EditParsedResultRequest`）：`{ "parsedResult": ParsedResult }`。`project` 與 `goals` 必填；`path`／`aiModel`／`tokenUsed`／`reasoning`／`draftIds`／`specDigest` 為伺服器擁有，**請求帶了也忽略**。
- **整樹覆寫規則**：陣列順序即排序，`sortOrder` 由伺服器重編為 0 起連續整數；每個目標的 `key` 在整棵樹內唯一（前端新增目標時自行產生，例如 `g-<短 uuid>`）；`dependsOn` 引用其他目標的 `key`。
- **驗證順序**：① 400 結構（缺必填欄位或型別錯誤——含任務的 `name`／`description` 為 null 或缺欄位、長度、`goals` 為空、某目標 `tasks` 為空、目標的 `name` 空白、目標與任務的 `passCriteria` 空白）→ ② 400 消毒（`evaluatorCommand` 含禁用字元 `` !`><~$&; `` → reason `命令含禁用字元`＋`details.violations`；`expectedOutputRegex` 無法編譯；與 Phase 2 任務建立同規則）→ ③ 422 有界閘（§3.3.5，列出全部違規）。**任務的 `name` 或 `description` 為空白字串不在 ① 擋**，一律交給 ③ 的 `empty_prompt` 閘（與 parse 路徑同一套，位置 `goals[i].tasks[j].name`／`.description`；AR-21）。
- **效果**：狀態 `REVIEWING`；**撤銷既有 signoff**（`signedOff=false`、`signedOffBy／At` 清空）；記錄的 `warnings` 以重算後的值覆寫（只含仍成立者，V8，§0.5）；回 `ParseResultResponse`（`errors=[]`）。
- **錯誤**：404；409 `匯入記錄狀態不允許此操作`（`action:"editResult"`，僅 PARSED／REVIEWING 可編輯）；400；422 `解析結果未通過有界閘`；401／403／429。

#### 1.1.5 `POST /api/v1/import/{id}/signoff`　🔴 人工 signoff　〔API-SGN-01／US-I-09〕

- **角色**：OPERATOR。**Bridge**：路徑 C 對每個 `draftIds` 呼叫 `POST /autoclaude/decompose/{draft_id}:approve`。
- **Request**（`SignoffRequest`，Phase 2 同名）：`{ "approver": "<非空白>" }`。
- **處理**：驗 `approver` 非空白 → 狀態須為 PARSED／REVIEWING 且未 signoff → 逐一 `:approve`（Bridge 回 `already_signed_off` 視為成功；任一其他失敗 → 502／409 且**不改任何狀態**）→ 設 `signedOff=true`、`signedOffBy=approver.strip()`、`signedOffAt=now`。
- **成功 200**：`ImportRecordResponse`（**偏離 PRD §7.1.4.1 的回傳型別**：signoff 只批准、不落庫；`confirm` 才建立專案，ADR-001 D12）。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （Bean Validation）`approver 不可為空（人工 signoff 不可匿名）` | `errors=[{field:"approver"…}]` | 缺漏或空白 |
| 404 | （訊息） | | |
| 409 | `匯入記錄狀態不允許此操作` | `{action:"signoff",status}` | 非 PARSED／REVIEWING |
| 409 | `已 signoff` | `{signedOffBy,signedOffAt}` | 重複 signoff（Phase 2 同常數） |
| 409 | `草案已失效，請重新解析` | `{draftId}` | Bridge 對該 draft 回 404 `draft_not_found`（workspace 被清） |
| 502／504 | 同上 | | Bridge 不可達 |
| 401／403／429 | 通用 | | |

#### 1.1.6 `POST /api/v1/import/{id}/confirm`　確認匯入　〔API-IMP-05、10／US-I-09〕

- **角色**：OPERATOR。**Bridge**：無（signoff 已處理）。
- **前置**：狀態 PARSED／REVIEWING 且 `signedOff=true`。
- **處理**：**單一交易**建立 Project（`status=DRAFT`、`autonomyLevel`＝`parsedResult.project.autonomyLevel ?? 3`、`createdBy`＝JWT subject）→ Goals（`sortOrder`＝陣列序、`dependsOn` 由 key 換成 id 並再跑 Kahn）→ Tasks（`maxRetries` 預設 3）。**全部 `signedOff=true`，`signedOffBy／At` 承襲匯入記錄**。再次套用 Phase 2 的欄位消毒（`PassCriteriaSanitizer`）；回寫 `projectId`、`status=IMPORTED`。任何一步失敗整個交易回滾。
- **成功 201**：`ApiResult<ProjectResponse>`（Phase 2 同名 schema）。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （Bean Validation／`命令含禁用字元`） | `errors[].field` 為 `parsedResult.goals[i].tasks[j].…` | 落庫前複驗不過 |
| 404 | （訊息） | | |
| 409 | `草案尚未 signoff，不可確認匯入` | `{status,signedOff:false}` | 未 signoff（設計稿：須先 signoff 才能「確認匯入」） |
| 409 | `已匯入` | `{projectId}` | 狀態 IMPORTED |
| 409 | `匯入記錄狀態不允許此操作` | `{action:"confirm",status}` | UPLOADED／PARSING／REJECTED |
| 401／403／429 | 通用 | | |

- **v1.5（D-115-14）**：`parse` 帶 `targetProjectId` 的記錄，`confirm` **不建立新專案**，改為把草稿的目標與任務併入目標專案並回填 SDD 綁定（規則見 §1.10.8；成功仍回 **201**，回傳的是目標專案；匯入記錄的 `projectId`＝目標專案）；多出 409 `sdd_binding_conflict`（`cause` 為 `target_bound_differently` 或 `already_bound_elsewhere`）與 404（目標專案已被刪除）。不帶 `targetProjectId` 的 `confirm` 建立新專案時，也會回填綁定（§0.5 V12），且同一 `executionPath` 下已有未刪除專案綁定同一個標準鍵時回 409 `sdd_binding_conflict`（`cause="already_bound_elsewhere"`）。

#### 1.1.7 `POST /api/v1/import/{id}/reject`　放棄匯入（補）　〔API-IMP-10〕

- **角色**：OPERATOR。無 body。非終態且非 PARSING 的記錄 → `status=REJECTED`，回 200 `ImportRecordResponse`。IMPORTED／REJECTED／PARSING → 409 `匯入記錄狀態不允許此操作`（`action:"reject"`）。不呼叫 Bridge（Bridge 草案檔留在其 workspace，由其清理）。

#### 1.1.8 `GET /api/v1/import`　查詢匯入歷史　〔API-IMP-06／US-I-06〕

- **角色**：VIEWER。查詢參數：`page,size`、`status`（`ImportStatus`）、`q`（來源檔名模糊搜尋，不分大小寫，`%`／`_` 視為字面）、`sort`（`createdAt|status`，預設 `createdAt,desc`）。
- **成功 200**：`Page<ImportRecordResponse>`（列表不含 `sourceContent`、`parsedResult`）。錯誤：400（未知 status／sort）、401／429。

#### 1.1.9 `GET /api/v1/import/{id}`　查詢詳情（補）　〔API-IMP-06／US-I-03〕

- **角色**：VIEWER。**成功 200**：`ImportRecordDetailResponse`＝`ImportRecordResponse`（含 `parsePath`、`lastParseErrors`，儲存位置見 §0.5 V5）＋ `sourceContent` ＋ `parsedResult`（第一次成功解析前為 null）＋ **`warnings[]`**（`ParseWarning[]`，與 `ParseResultResponse.warnings` 同形；最近一次成功的 parse 或 `PUT result` 的結果，沒有就是 `[]`，**永遠出現**）＋ **`parseOptions`**（`ParseOptions`，最近一次 parse 請求的選項；從未 parse 過為 null）。後兩者為 v1.2（C-10；儲存位置見 §0.5 V8）：前端重開記錄時據此還原黃色解析提示與解析選項（§4.1 I-12、I-18；取代 v1.1 的已知限制 F1-1／F1-2）。列表 `GET /import` 的項目不含這兩者。錯誤：400（id 格式）、404、401／429。

---
### 1.2 專案執行（Phase 4）

本節的 Bridge 行為皆依 `AgentConsole/engine-bridge/README.md` 與 `app/runner.py`：pause 只收 RUNNING、resume 只收 PAUSED、stop 收 RUNNING／PAUSING／PAUSED、restore 收 PAUSED 與三個終態（PAUSED 的 restore 在 DB 模式依賴一項 Bridge 修復，見 §1.2.10 與 AR-01）；其餘一律 409 `invalid_state`。**同一個 run 的「控制操作」與「事件消費／讀模型更新」在 console-api 內以 per-run 互斥鎖序列化**，避免還原或取消與事件處理互相踩踏。

控制類端點（pause／resume／cancel／restore）的回應都是 `ExecutionRunResponse` **快照**：呼叫 Bridge 動作成功後，立刻再讀一次 Bridge `GET /autoclaude/runs/{id}`，`status`＝六態折疊值、`bridgeStatus`＝Bridge 原值（例：pause 後為 `RUNNING`＋`PAUSING`；暫停中的 run 被 cancel 則 Bridge 已同步到 `CANCELLED`，回應即為 `CANCELLED`）。快照裡的 `engineCapabilities` 讀自 DB（建立時凍結，§1.2.1），不隨 resume／restore 重算。

#### 1.2.1 `POST /api/v1/projects/{projectId}/execute`　啟動執行　〔API-EXE-01、11、12、13、DAG-01、AUT／US-E-01、02、10〕

- **角色**：OPERATOR。**Bridge**：`POST /autoclaude/runs`。
- **Request**（`StartExecutionRequest`；body 可為 `{}`）：

| 欄位 | 型別 | 必填 | 預設 | 規則 |
|------|------|:----:|------|------|
| `autonomyLevel` | int | — | 專案的 `autonomyLevel` | 1～10 |
| `tokenBudget` | int64 | — | 系統參數 `execution.globalTokenBudget` | ≥ 1 |
| `scope.mode` | `ALL`｜`SELECTED` | — | `ALL` | `ALL` 時不可帶 `goalIds`／`taskIds`；`SELECTED` 時兩者至少一個非空 |
| `scope.goalIds` | uuid[] | — | `[]` | 該專案內未刪除的目標 |
| `scope.taskIds` | uuid[] | — | `[]` | 該專案內未刪除的任務 |
| `scope.limits.taskTokens`／`goalTokens` | int64 | — | 無 | ≥ 1；US-E-10 的單一任務／目標上限 |

- **範圍解析**：`ALL`＝專案內全部「可執行」任務（狀態不是 `COMPLETED`／`SKIPPED`）；`SELECTED`＝所選目標的全部可執行任務 ∪ 所選任務。目標順序＝依 `goal_dependencies` 做 Kahn 拓撲排序，同層依 `execution.dagSchedulerStrategy` 擇一（`TOPOLOGICAL`／`PRIORITY`＝`sortOrder` 升冪；`SHORTEST_FIRST`＝所屬目標內預估 Token 總和升冪，null 視為 0，平手取 `sortOrder`）；目標內任務依 `sortOrder`（平手取 `createdAt`、`id`）。展平後為 playbook 的步驟序列。
- **驗證順序（固定，QA 依序斷言）**：

| # | 檢查 | HTTP | reason | details |
|---|------|------|--------|---------|
| 1 | 專案存在且未軟刪除 | 404 | （訊息）`專案不存在或已刪除：<id>` | — |
| 2 | Bean Validation（等級／預算／mode／ids 格式） | 400 | （無） | `errors[]` |
| 3 | 專案狀態為 `EXECUTING` | 409 | `專案正在執行中` | `{projectId, runId}` |
| 4 | 專案狀態為 `ARCHIVED`（`DRAFT`／`READY`／`FAILED`／`COMPLETED` 皆可進入後續檢查） | 409 | `專案狀態不允許執行` | `{status}` |
| 5 | 專案、**全部**未刪目標、**全部**未刪任務皆 `signedOff=true`（**整案**檢查，不是只看所選範圍：`SELECTED` 時範圍外的未簽任務也會擋；這樣才能同時滿足 E2E-02 步驟 5「無效範圍＋仍有未簽 → 409 先於範圍檢查」；B2-1，`ExecuteProjectService.requireSignedOff`） | 409 | `未經人工審批的草案不可執行`（message：`草案未經人工審批，禁止執行`） | `{unsignedProjectId?, unsignedGoalIds[], unsignedTaskIds[]}`（專案本身已 signoff 時省略 `unsignedProjectId`，`details` 不輸出 null，§0.2） |
| 6 | `goalIds`／`taskIds` 皆屬於該專案 | 400 | `所選範圍不合法` | `{invalidGoalIds[], invalidTaskIds[]}` |
| 7a | `SELECTED` 內有已 `COMPLETED`／`SKIPPED` 的目標或任務 | 409 | `所選任務或目標已完成` | `{goalIds[], taskIds[]}` |
| 7b | 所選目標依賴了「未選且未完成」的目標（**`COMPLETED` 與 `SKIPPED` 的前置目標都算已滿足**；審核 `SKIP`／`RETRY` 開的後續批次不做 7b；B2-2，`ExecutionPlanner.requireDependenciesAreSelectedOrDone`） | 409 | `所選目標依賴未完成的前置目標` | `{missingGoalIds[]}` |
| 7c | 解析後沒有任何可執行任務 | 409 | `沒有可執行的任務` | — |
| 8 | 目標依賴成環（防禦；Phase 2 已擋） | 409 | `依賴成環` | `{cycle[]}` |
| 9a | 任一步驟 prompt（§3.4.3 樣板組好後）超過 20,000 字元 | 422 | `步驟 prompt 超過 20000 字元上限` | `{taskId, stepId, length, limit:20000}` |
| 9b | 評估指令含禁用字元（第 2 層複驗，NFR-SEC-03） | 422 | `評估指令含禁用字元` | `{taskId, chars[]}` |
| 9c | 評估指令首個 token 不在可執行檔白名單（附錄 D.3） | 422 | `評估指令不在可執行檔白名單` | `{taskId, executable}` |
| 9d | `expectedOutputRegex` 無法編譯 | 422 | `expectedOutputRegex 無法編譯` | `{taskId}` |
| 9e | 範圍任務數超過 Bridge 單一 playbook 上限（`PlaybookIn.tasks` ≤ 500） | 422 | `範圍任務數超過單一批次上限 500` | `{count, limit:500}` |
| 9f | 範圍內任一任務的 `maxRetries` > 20（Bridge `PlaybookIn` 上限；Phase 2 建立／更新任務的 DTO 也加 `@Max(20)`，這一項是第二道防線，AR-14） | 422 | `任務最大重試次數超過上限 20` | `{taskId, maxRetries, limit:20}` |
| 10 | Bridge 409 `advisory_lock_held` | 409 | `同專案同路徑已有執行中的批次` | `{holderRunId}` |
| 10 | Bridge 422（消毒／格式） | 422 | `引擎拒絕此請求` | `{bridgeReason, violations[]}`（`violations` 逐項原樣帶出） |
| 10 | Bridge 不可達／逾時／其他 5xx | 502／504／502 | `引擎橋接服務無法連線`／`…逾時`／`引擎橋接服務錯誤` | `{bridgeStatus?, bridgeReason?}` |

第 3～9f 項**不呼叫 Bridge**；第 10 項失敗時，剛建立的 `execution_runs` 列**補償刪除**，專案與任務狀態不動。補償刪除的守門只有一條：「該 run 尚無任何 `execution_steps`」，**不看列的狀態**——Bridge 在 `spawn_failed` 時已把列標成 `FAILED` 並鏡射進 DB，仍要刪，否則會留下一個佔用 `run_number` 的 FAILED 空批次（AR-15；流程見 §3.4.5）。檢查 5 的順序在 6 之前，所以未 signoff 時即使 ids 有誤也先回 409（與 PRD「不靜默放行」一致）。

- **成功處理**：持專案列鎖取下一個 `run_number` → 寫 `execution_runs`（僅 console 欄位：`id, project_id, run_number, autonomy_level, scope, token_budget, dag, started_at`）並提交 → Bridge `POST /autoclaude/runs` → 201 後：專案轉 `EXECUTING`（`DRAFT`／`FAILED` 先內部轉 `READY` 再轉 `EXECUTING`，同一交易；`COMPLETED` 的專案補了新任務後可再跑，屬系統重設直接 `→EXECUTING`，§3.5.3、§6 D-31；若範圍內已無可執行任務則由第 7c 項擋下）、範圍內任務 `→QUEUED`（狀態重設規則見 §3.5.3）、啟動事件消費者（§3.5.4）。
- **成功 201**：`ApiResult<ExecutionRunResponse>`，`status=RUNNING`、`bridgeStatus=RUNNING`（以 Bridge 201 回的 `status` 為準，不依賴 DB 回讀時機）、`totalTokensUsed=0`。

```json
{ "code":201, "message":"success", "data":{
    "id":"e5a7c3b9-2f1d-4b6a-8c0e-1d2f3a4b5c31", "projectId":"0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02",
    "runNumber":1, "status":"RUNNING", "bridgeStatus":"RUNNING", "autonomyLevel":1,
    "scope":{ "mode":"ALL", "goalIds":[], "taskIds":[] },
    "totalTokensUsed":0, "tokenBudget":100000, "startedAt":"2026-10-15T08:30:12Z",
    "engineCapabilities":{ "autoMutation":"OFF", "selfEvolution":"OFF" } },
  "timestamp":"2026-10-15T16:30:12+08:00", "traceId":"…" }
```

- **`engineCapabilities`（v1.3；D-11）**：`ExecutionRunResponse` 的欄位，所以 execute 的 201、`GET /executions/{runId}`、pause／resume／cancel／restore 的快照回應都帶同一份值。形狀 `{ "autoMutation": <狀態>, "selfEvolution": <狀態> }`，`<狀態>`∈`ENABLED`／`OFF`／`UNAVAILABLE_NO_API_KEY`。它回答的是「這個批次 spawn 時，Console **實際送進引擎**什麼」，不是「使用者設了什麼」——兩者在 `selfEvolution` 上會不同，原因與各值的精確意思見 §3.4.2。上面的範例是沒有金鑰、等級 1 的批次（`OFF`／`OFF`）。
  - **何時決定、存在哪**：spawn 時決定（等級 6～10 沒有額外的驗證項；沒有金鑰也不報錯，如實回 `UNAVAILABLE_NO_API_KEY`），落庫於 `execution_runs.engine_capabilities`（V10，§0.5），建立後不再更新。
  - **缺席**：V10 之前建立的批次沒有這個欄位（null 與缺席等價，§0.2）；前端不顯示晶片、不得猜測。
  - **不在列表**：`ExecutionRunSummaryResponse`（批次列表）不帶它。
- **v1.5（D-115-06）SDD 批次**：上表第 10 項的 Bridge 呼叫，在「範圍內任務全為 SDD 來源」時改帶頂層 `sdd` 區塊（資格判定與組裝見 §1.10.5～§1.10.6；Bridge 預檢與 FSM 同步見 §3.1.6）。第 10 項因此多出下列失敗：Bridge 422 `spec_not_frozen` 等 → 422 `SDD 規格檢查未通過`；Bridge 409 `spec_digest_changed` → 409 `sdd_spec_digest_changed`；Bridge 409 `fsm_state_conflict` → 409 `sdd_fsm_state_conflict`；Bridge 404 `fsm_not_found` → 409 `sdd_fsm_not_found`；Bridge 422 `sdd_invalid_argument`／`sdd_block_invalid` → 422 `引擎拒絕此請求`；Bridge 503 `sdd_write_disabled` → 503 `sdd_write_disabled`；Bridge 的 `sdd_cli_*`（500／502／504）→ 502 `引擎橋接服務錯誤`（對映總表見 §3.2 的 v1.5 列）。它們與其他第 10 項失敗一樣**補償刪除**剛建的 `execution_runs` 列（此時尚無任何 `execution_steps`）。201 回應新增選填欄位 `warnings[]`（`{code, cause?, detail}`；`sdd_governance_inactive`、`sdd_frozen_digest_absent`，§1.10.6），**只有 execute 的 201 帶它**，pause／resume／cancel／restore 與 `GET` 不帶。

#### 1.2.2 `GET /api/v1/projects/{projectId}/executions`　列出執行批次（補）　〔API-EXE-14／US-M-06〕

- **角色**：VIEWER。查詢參數：`page,size`、`status`（`RunStatus`）、`sort`（`startedAt|runNumber`，預設 `startedAt,desc`）。
- **成功 200**：`Page<ExecutionRunSummaryResponse>`。`tasksTotal`＝該批次 `dag` 的 TASK 節點數；`tasksCompleted`／`tasksFailed`＝該批次 `execution_steps` 中有 `COMPLETED`／`FAILED` 列的**相異任務數**；`successRate`＝`tasksCompleted ÷ (tasksCompleted+tasksFailed) × 100`（兩者皆 0 為 null）；`durationSec` 見 schema。**`bridgeStatus`**（`BridgeRunStatus`，可 null；v1.2，C-11，QA F2-4；與 `ExecutionRunDetailResponse.bridgeStatus` 同義）：列表**不為此欄位逐批呼叫 Bridge**——取 console-api 記憶體中該批次最近一則 `status` 事件的 Bridge 狀態（`RunRegistry.Runtime.bridgeStatus`，所以 `PAUSING`／`CANCELLING` 只在 console-api 仍消費該批次時可見，正是前端要顯示處理中晶片的情境）；記憶體沒有（批次已終態、console-api 重啟後尚未收到事件）時以 DB `status` 同名值補（六態都在 Bridge 八態之內）；僅 `status=RUNNING` 且記憶體也沒有時為 null（缺席）。前端的批次下拉與批次比較據此顯示 `PAUSING`／`CANCELLING` 晶片（取代 v1.1 只有詳情看得到的限制）。
- **錯誤**：400（未知 status／sort）、404 專案、401／429。

#### 1.2.3 `GET /api/v1/executions/{runId}`　查詢執行狀態　〔API-EXE-05／US-E-07、M-10〕

- **角色**：VIEWER。**Bridge**：`GET /autoclaude/runs/{id}`（逾時 3 秒）。
- **成功 200**：`ExecutionRunDetailResponse`＝`ExecutionRunResponse` ＋：

| 欄位 | 來源 | Bridge 不可達時 |
|------|------|-----------------|
| `currentStep{stepId,stepNumber,taskId,taskName,goalId,attempt}` | Bridge `current_step`、`current_step_number`、`attempt` ＋ dag 對映 | `null` |
| `completedSteps`／`totalSteps` | Bridge `completed_steps`／`total_steps` | 由 DB 衍生：`completedSteps`＝該批次有 `COMPLETED` 列的相異任務數；`totalSteps`＝dag 的 TASK 節點數 |
| `lastEventSeq` | Bridge `last_event_seq` | DB 內最大 `step_number` 或 null |
| `reason` | Bridge `reason` | null |
| `elapsedSec` | 進行中＝現在−`startedAt`；終態＝`completedAt`−`startedAt` | 同左 |
| `pendingReviews[]` | `review_requests` 中 `status=PENDING`（依 `requestedAt` 升冪） | 同左（DB） |
| `bridge{connected,instance,status,runKnown,checkedAt,resources}` | 見下 | `connected=false`，`status`、`resources` 為 null |

- **Bridge 不可達（連線失敗或逾時）時仍回 200**，`bridge.connected=false`，**不回 5xx**（主控裁決）。Bridge 可達但回 404 `run_not_found`（workspace 被清）→ `connected=true`、`runKnown=false`、進度同 DB 衍生。`bridge.instance` 取 Bridge 的 `bridge_instance`；**不外露 pid 與 lock key**。
- **`bridge.resources`（v1.3；D-12；US-M-10）**：`{ cpuPercent, memoryBytes, processCount, sampledAt }` 或 null，來自同一次 `GET /autoclaude/runs/{id}` 回應裡的引擎行程樹資源取樣（Bridge 規格與取樣規則見 §3.1.2）：`cpuPercent`＝整機正規化的 CPU 百分比（0～100，小數 1 位）、`memoryBytes`＝行程樹 RSS 總和（int64）、`processCount`＝行程數（int32）、`sampledAt`＝取樣時間（ISO-8601 含 offset）。**以下任一情形為 null（或缺席）**：引擎行程不存活（尚未啟動、暫停中、終態）、還沒有第一筆樣本、最近一筆樣本已過期、`bridge.connected=false`、`bridge.runKnown=false`；Bridge 回應沒有 `resources` 鍵（舊版 Bridge）亦同。**只有本端點帶 `bridge` 物件**（pause／resume／cancel／restore 的快照沒有）。顯示格式見 §4.3 M-19。
- **錯誤**：400（id 格式）、404、401／429。

#### 1.2.4～1.2.6 `POST /api/v1/executions/{runId}/pause｜resume｜cancel`　〔API-EXE-02、03、04、11／US-E-04、05、06〕

- **角色**：OPERATOR。無 body。成功 200 `ApiResult<ExecutionRunResponse>`（快照，見本節開頭）。

| 端點 | DB 預檢（失敗 409） | Bridge 呼叫 | 成功後典型回應 | 副作用 |
|------|---------------------|-------------|----------------|--------|
| `pause` | `status=RUNNING`（終態或 PAUSED 直接 409，不呼叫 Bridge） | `:pause` → 202 `PAUSING`（PAUSING 時冪等） | `RUNNING`＋`PAUSING` | 無；`PAUSED` 由 SSE `status-change` 通知。已在最後一步時暫停來不及，run 照常 `COMPLETED` |
| `resume` | `status=PAUSED`；**重驗範圍內專案／目標／任務 `signedOff`**（`未經人工審批的草案不可執行`，details 同 execute 第 5 項） | `:resume` → 202 `RUNNING` | `RUNNING`＋`RUNNING` | 專案回 `EXECUTING` |
| `cancel` | `status∈{RUNNING,PAUSED}` | `:stop` → 202 `CANCELLING` | `RUNNING`＋`CANCELLING`（PAUSED 者即時 `CANCELLED`） | 終態 `CANCELLED` 後：範圍內 `RUNNING`／`QUEUED` 任務→`CANCELLED`、其餘不動；專案→`READY`；`IN_PROGRESS` 目標→`PENDING`（§3.5.3） |

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （訊息）`參數 runId 的值格式不正確` | | 路徑參數不是 UUID（Phase 2 既有行為，§0.2） |
| 404 | （訊息）`執行批次不存在或已刪除：<id>` | | |
| 409 | `目前執行狀態不允許此操作` | `{action:"pause\|resume\|cancel", runStatus, bridgeStatus}` | DB 預檢不符，或 Bridge 409 `invalid_state` |
| 409 | `未經人工審批的草案不可執行` | `{unsignedProjectId,unsignedGoalIds[],unsignedTaskIds[]}` | 僅 resume |
| 409 | `引擎端已無此執行（工作區可能已清除）` | `{runId}` | Bridge 404 `run_not_found` |
| 502／504 | `引擎橋接服務無法連線`／`…逾時`／`引擎橋接服務錯誤` | | DB 狀態不變 |
| 401／403／429 | 通用 | | |

- **v1.5（D-115-15）SDD 批次的 `resume`**：Bridge 對 SDD run 先**重跑預檢**（凍結＝現檔、匯入摘要＝現檔、FSM 前置；§3.1.6 第 7 點），額外失敗：409 `sdd_spec_digest_changed`（規格在暫停期間被改動）、409 `sdd_fsm_state_conflict`（FSM 不在 `AUTOCLAUDE_DELEGATED` 且不是可重進的 `IMPLEMENTATION`，或委派屬於別的 run／外來）、422 `SDD 規格檢查未通過`；失敗時 run 維持 `PAUSED`、不 spawn。`pause` 不碰 FSM；`cancel` 的終態同步由 Bridge 在終態後做（`CANCELLED`⇒`delegate-exit done`，§3.1.6 第 5 點）。
- **v1.5（D-115-18）SDD run 的權杖**：對 SDD run，console-api 呼叫 Bridge `:resume` 須附 `X-Bridge-Token`（§3.1.4 共通規則 2；ADR-016 §9 的兩個呼叫擴大為四個，`restore` 同，見 §1.2.10）。Bridge 沒設權杖 → 503 `sdd_write_disabled`、標頭缺漏或不符 → 403 `sdd_write_forbidden`，Console 轉譯同 execute（§3.2）：503 → **503** `sdd_write_disabled`、403 → **502** `引擎橋接服務錯誤`（`details={bridgeStatus:403, bridgeReason:"sdd_write_forbidden"}`，另記 ERROR 日誌）；權杖檢查在預檢之前，所以 run 維持 `PAUSED`、DB 與 FSM 都不變。console-api 不記錄批次是否為 SDD，`:resume` 一律附標頭（backend 有設權杖時）；不含 `sdd` 的 run 不受影響。Bridge 呼叫的讀取逾時為 30 秒（§3.1 呼叫表；原 15 秒，SDD run 可能多一次 `delegate-enter`），逾時回 504 `引擎橋接服務逾時`、DB 狀態不變。

#### 1.2.7 `GET /api/v1/executions/{runId}/steps`　分頁查詢步驟　〔API-EXE-06、SSE-03／US-M-03、09〕

- **角色**：VIEWER。查詢參數：`page`（0 起）、`size`（預設 50、上限 200）、`afterSeq`（≥0，**嚴格大於**）。依 `stepNumber` 升冪。
- **資料來源**：`console.execution_steps`（Bridge 寫；每個 `step` 事件一列，狀態 `STARTED／RETRYING／COMPLETED／FAILED`）。**`stepNumber`＝該 step 事件的 Bridge `seq`**（Bridge 把位置放進 `input`，`step_number` 欄放 seq），所以 `afterSeq` 可直接對 SSE `Last-Event-ID` 的整數部分（Console 自產事件的子序號不影響）。
- **`ExecutionStepResponse` 欄位**：`id, runId, taskId, taskName, goalId, stepNumber, stepId(=input.step_id), attempt(=input.attempt), action("<step_id>: <任務名稱>"), status, tokensUsed, errorMessage, output, timestamp`。`tokensUsed`：**Bridge 不寫 `execution_steps.tokens_used`**，`COMPLETED`／`FAILED` 列由 console-api 以該任務在本批次的 token 歸因（`run_token_samples` 依 `task_id` 加總）回傳，其餘列為 null；`output` 目前恆為 null。
- **REST 回補用法**：SSE 斷線且 `Last-Event-ID` 已過期時，以 `afterSeq=<id 的整數部分>` 迴圈取頁補齊步驟，再重新連 SSE。注意 `steps` 只含步驟事件；引擎原始 `log` 行與告警／審核項需另以 SSE 重播或 `alerts`／`pendingReviews` 取得。
- **錯誤**：400（`afterSeq<0`、`size>200`、runId 格式）、404、401／429。
- **欄位意思**：`stepNumber` 是事件 seq（不是步驟位置），`stepId` 是 playbook 的 step_id（字串）；同名欄位在別的型別有不同意思，見 §0.6。

#### 1.2.8 `GET /api/v1/executions/{runId}/dag`　DAG 圖　〔API-EXE-07、DAG-01／US-E-09〕

- **角色**：VIEWER。成功 200：`DagResponse{runId, nodes[], edges[], statusAsOf}`。
- 節點：`GOAL`（`id`＝目標 id，`sequence`＝目標序）與 `TASK`（`id`＝任務 id，`goalId`，`stepId`，`sequence`＝展平後位置，1 起算，等於 Bridge 的 `step_number`／`current_step_number`）。邊：`DEPENDENCY`（前置目標→依賴者，只含範圍內的目標）與 `CONTAINS`（目標→其任務）。節點／邊在建立批次時凍結於 `execution_runs.dag`；`status` 於讀取時疊加目標與任務的**現況**（歷史批次亦為現況，見 `statusAsOf`；§6 D-38）。
- 錯誤：400（runId 格式）、404、401／429。

#### 1.2.9 `GET /api/v1/executions/{runId}/checkpoints`　斷點列表　〔API-EXE-08／US-E-11〕

- **角色**：VIEWER。成功 200：`List<CheckpointResponse>`（舊→新）。資料來自 `console.checkpoints`（Bridge 於每個步驟完成時自行記錄歷史快照，append-only，命名 `after-<step_id>`）。`stepIdx`／`stepId` 取自 `state_snapshot` 的 `step_idx`／`step_id`（＝**還原後下一個要跑的步驟**；最後一步之後 `stepIdx=總步數`、`stepId=""`）；`completedSteps`＝快照的 `completed_step_ids` 長度。不含 `stateSnapshot` 本體。（Bridge 另有等價的 REST 來源 `GET /autoclaude/runs/{id}/checkpoints`，欄位較少、沒有 `completedSteps`，§3.1；本端點以 DB 為準。）
- 錯誤：400（runId 格式）、404、401／429。

#### 1.2.10 `POST /api/v1/executions/{runId}/restore/{checkpointId}`　從歷史斷點還原　〔API-EXE-09、11／US-E-11〕

- **角色**：OPERATOR。**Bridge**：`POST /autoclaude/runs/{id}/restore {checkpoint_id}`（202）。語意不同於 resume：restore **必帶** `checkpointId`、時間回退到該還原點。
- **前置**：`checkpointId` 屬於該 run（否則 404）；該 run 是專案**最新**的批次；DB `status∈{PAUSED,COMPLETED,FAILED,CANCELLED}`（`RUNNING`／`INITIALIZING` → 409）；重驗範圍內 `signedOff`；Bridge 還會重取已釋放的鎖（可能 409）並重驗 `execution_path`（TOCTOU，可能 422）。
- 🔴 **PAUSED 的 restore 依賴 Bridge 修復（AR-01）**：Bridge 的 `restore()` 對 PAUSED 與終態都允許，但無條件呼叫 `reacquire_lock`（`runner.py`）。在 DB 模式下，PAUSED 的 run 仍持有舊的專用連線與 session 級 advisory lock，`locks.py` 的 `acquire` 每次開新連線做 `pg_try_advisory_lock`，必然失敗；失敗路徑還會先把登記拔掉，之後終態的 `release` 早退，舊連線永不關閉、鎖外洩，同專案同路徑之後的所有 execute 都會 409。後果：未修復時 PAUSED 的 restore 回 409 `同專案同路徑已有執行中的批次`（`holderRunId` 就是這個 run 自己）。主控已另派修復者修 Bridge 本體（`reacquire_lock` 對仍持鎖的 run 略過、`acquire` 對同一個 holder 冪等、失敗不拔登記、補 DB 模式測試）。**契約維持「PAUSED 可 restore」**；Bridge 修復落地前此行為不可用：開發與 QA 遇到就登記為 Bridge 缺陷（不要改契約），冒煙可暫以終態 run 的 restore 代替（W3-B2 任務書）。受影響的流程：E2E-07 步驟 6、審核 `GOAL_COMPLETED` 的 `RETRY`（此時 run 為 PAUSED，§3.6.3）。
- **成功 200**：`ExecutionRunResponse` 快照（典型 `RUNNING`＋`RUNNING`）。Bridge 隨後發 `alert`（`code=RESTORE`、level `info`）與 `status RUNNING`。
- **副作用（Bridge 接受後，同一交易）**：依快照的 `completed_step_ids` 把**其餘**範圍內任務重設為 `QUEUED`、受影響目標重設、專案回 `EXECUTING`（§3.5.3）。**restore 沿用該 run 建立時的 playbook**：還原後之前修改的任務內容不會生效；要用新內容請另開批次（`execute`）。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （訊息）`參數 <名> 的值格式不正確` | | `runId`／`checkpointId` 不是 UUID |
| 404 | （訊息）`checkpoint 不存在或不屬於此執行：<id>` | | |
| 409 | `目前執行狀態不允許此操作` | `{action:"restore",runStatus,bridgeStatus}` | |
| 409 | `只能還原專案最新的執行批次` | `{latestRunId,latestRunNumber}` | 該 run 不是專案 `run_number` 最大者（避免以過期的 playbook 範圍重跑已被跳過或已完成的任務） |
| 409 | `未經人工審批的草案不可執行` | 同 execute | |
| 409 | `同專案同路徑已有執行中的批次` | `{holderRunId}` | 終態還原時鎖被別的 run 取走 |
| 409 | `引擎端已無此執行（工作區可能已清除）` | | Bridge 404 `run_not_found` |
| 422 | `引擎拒絕此請求` | `{bridgeReason,violations[]}` | `execution_path` 重驗失敗 |
| 502／504 | 通用 | | |

- **v1.5（D-115-15）SDD 批次的 `restore`**：同 `resume`，Bridge 重跑預檢；FSM 為 `IMPLEMENTATION` 時重新 `delegate-enter`，為 `ESCALATION` 或被別的 run／外來委派佔用時 409 `sdd_fsm_state_conflict` 並不 spawn；額外失敗另有 409 `sdd_spec_digest_changed`、422 `SDD 規格檢查未通過`（§3.2、§3.1.6 第 7 點）。
- **v1.5（D-115-18）SDD run 的權杖**：同 `resume`（§1.2.4～§1.2.6）：Bridge `restore` 須附 `X-Bridge-Token`；缺／錯 → Bridge 503 `sdd_write_disabled`／403 `sdd_write_forbidden` → Console **503** `sdd_write_disabled`／**502** `引擎橋接服務錯誤`（`details.bridgeStatus=403`）；檢查在預檢之前，run、專案與 FSM 狀態都不變。Bridge 呼叫的讀取逾時同為 30 秒（§3.1 呼叫表）。

#### 1.2.11 `POST /api/v1/executions/{runId}/review/{stepId}`　審核　〔API-EXE-10、AUT-01～06／US-E-07、08〕

- **角色**：OPERATOR。**路徑的 `{stepId}` 是 `review_requests.id`（UUID），不是 playbook 的 step_id**（主控裁決）。審核人＝JWT subject（`decided_by`）。
- **Request**（`ReviewRequest`）：`{ "decision": "APPROVE|REJECT|RETRY|SKIP", "comment": "≤2000 字元（選填）" }`。
- **成功 204**（無本文）。`SKIP`，以及找不到還原點而改開後續批次的 `RETRY`，會另建後續批次（follow-up run），其 id 放在回應標頭 **`X-Follow-Up-Run-Id`**；其餘決定不出現該標頭。審核項狀態對映：`APPROVE→APPROVED`、`REJECT→REJECTED`、`RETRY→RETRIED`、`SKIP→SKIPPED`，寫入 `decided_by／decided_at／comment`。
- **每個 `kind` 允許的決定與動作**見 §3.6.3（`ReviewRequestResponse.allowedDecisions` 即該表的資料化）。
- 審核 `RETRY` 讓失敗任務 `retry_count+1`，與手動重試（§1.6.4）一樣**不受 `maxRetries` 限制**：`maxRetries` 是引擎自動重試的上限，人工介入不算。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （Bean Validation）；路徑 id 格式為（訊息）`參數 <名> 的值格式不正確` | `errors=[{field:"decision"…}]` | decision 缺漏或不在列舉、comment 過長；`runId`／`stepId` 不是 UUID |
| 404 | （訊息）`審核項不存在或不屬於此執行：<id>` | | `{stepId}` 查無或其 `run_id` 不符 |
| 409 | `審核項已處理` | `{status,decidedBy,decidedAt}` | 狀態非 `PENDING`（含並發雙擊的後者） |
| 409 | `此審核項不允許該決定` | `{kind,decision,allowedDecisions[]}` | decision 不在 `allowedDecisions` |
| 409 | `目前執行狀態不允許此操作` | `{action:"review",runStatus,bridgeStatus}` | 例：gate 審核項的 `APPROVE` 但 run 已不在 `PAUSED` |
| 409／422／502／504 | 同 execute 第 10 項 | | `SKIP`／`RETRY` 開後續批次或 restore 時 Bridge 回應 |
| 401／403／429 | 通用 | | |

**原子性**：`SKIP`／後續批次先完成「建 run 列＋Bridge 接受」，成功後才提交審核項與任務的狀態變更；任何一步失敗全部回滾，審核項維持 `PENDING`。

**`SKIP` 與「新批次自動關閉舊審核項」的先後**（AR-21）：①鎖定該審核項（仍須是 `PENDING`）；②建後續批次（run 列＋Bridge 接受）；③同一交易內，**先**把這個審核項標 `SKIPPED`、任務標 `SKIPPED`，**再**執行 §3.5.3「新批次建立時，前批仍 `PENDING` 的審核項自動 `REJECTED`」。該規則只作用於仍為 `PENDING` 的項目，所以已被標 `SKIPPED` 的這一筆不受影響（E2E-05 步驟 7 預期 `SKIPPED`），只有同一專案其他仍待決的項目才被自動關閉。`RETRY` 改開後續批次（找不到還原點時）同理，該審核項標 `RETRIED`。

---
### 1.3 專案監控（Phase 5）

**共通查詢參數**（`metrics`／`token-trend`／`task-trend`／`logs`／`report`；`alerts` 只用 `runId`）：

| 參數 | 型別 | 預設 | 規則 |
|------|------|------|------|
| `runId` | uuid | 省略＝專案全部批次 | 必須屬於該專案，否則 404（訊息 `執行批次不存在或不屬於此專案：<id>`） |
| `from` | date-time（帶 offset） | `to` 之前 24 小時 | 必須早於 `to`，否則 400 `時間範圍不合法`（`details={from,to}`） |
| `to` | date-time（帶 offset） | 現在 | 視窗上限 366 天，超過同為 400 `時間範圍不合法` |
| `bucket`（僅趨勢） | `HOUR`｜`DAY` | 視窗 ≤ 48 小時用 `HOUR`，否則 `DAY` | 桶以 UTC 為界；視窗內桶數超過 1,000 回 400 `時間範圍不合法`（請改用 `DAY`）。**前端圖表以瀏覽器本機時區顯示桶標籤**（桶起點仍是 UTC，跨日界附近的 `DAY` 標籤可能與伺服器的日界差一天；F2-1，`lib/domain/metrics.ts` 的 `formatBucketLabel`；不登缺陷） |

**Bridge**：監控端點不呼叫 Bridge（資料全來自 DB），唯一例外是 `agentAvailability`（取自 console-api 對 Bridge 的健康探測環，§3.1）。

**時間參數的容錯（B2-6）**：查詢字串裡**未編碼**的 `+`（例：`from=2026-10-15T16:40:00+08:00`）會被解碼成空白；後端把結尾的「空白＋`HH:mm`」還原成 `+HH:mm`（`adapter/in/web/TimeParams.parse`），而不是回令人困惑的 400。正式呼叫端仍應把 `+` 編成 `%2B`；`task-totals`（§1.3.8）的 `from`／`to` 套用同一規則。

所有監控端點共通錯誤：404 專案不存在、404 `runId` 不屬於該專案、400（參數格式）、401／429。聚合公式、前一視窗比較與日誌衍生規則統一見 **§3.8**。

**輪詢**：監控頁各端點的輪詢間隔同樣不得小於 `monitor.refreshIntervalMs`（預設與最小值皆 10 秒），頁面不可見時應暫停；監控頁約 8 個端點，每 10 秒各一次約為每分鐘 48 次，在限流（每使用者每分鐘 100 次，§0.4 第 4 點）之內（AR-06）。

#### 1.3.1 `GET /api/v1/monitor/projects/{projectId}/metrics`　〔API-MON-01／US-M-01、M-10〕

- **角色**：VIEWER。成功 200：`ProjectMetricsResponse`。
- **欄位**：十個 `MetricValue{value,previousValue,delta}`——PRD §5.4.2 八項：`projectCompletionRate`（專案完成率，**全域**，不隨 `projectId` 變）、`goalAchievementRate`、`taskSuccessRate`、`averageRetryCount`、`totalTokens`（Token 總消耗）、`tokenBudgetUsageRate`、`averageTaskDurationSec`、`agentAvailability`；加設計稿卡片用的 `taskCompletionRate`（「完成率」＝專案內任務完成進度）與 `retryRate`（「重試率」）。另有 `tokenBudget`、`taskStatusDistribution`（任務十一態現況計數，缺的態為 0 且一律出現）、`taskDurations[]`（視窗內完成的任務，耗時由長到短至多 10 筆）、`retryDistribution[]`（重試 0、1、2、3、4、≥5 次的任務數）。`generatedAt`＝伺服器產生時間。
- 數值無法計算（分母為 0、沒有探測樣本、無預算）時 `value=null`；`previousValue`／`delta` 的 null 規則見 §3.8.1。

```json
{ "code":200, "message":"success", "data":{
    "projectId":"0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02", "runId":"e5a7c3b9-2f1d-4b6a-8c0e-1d2f3a4b5c31",
    "from":"2026-10-14T08:40:00Z", "to":"2026-10-15T08:40:00Z", "generatedAt":"2026-10-15T08:40:00Z",
    "taskCompletionRate":{ "value":100.0, "previousValue":0.0, "delta":100.0 },
    "taskSuccessRate":{ "value":100.0, "previousValue":null, "delta":null },
    "retryRate":{ "value":0.0, "previousValue":null, "delta":null },
    "totalTokens":{ "value":3720, "previousValue":0, "delta":3720 },
    "tokenBudgetUsageRate":{ "value":3.7, "previousValue":null, "delta":null },
    "averageRetryCount":{ "value":0.0, "previousValue":null, "delta":null },
    "projectCompletionRate":{ "value":100.0, "previousValue":null, "delta":null },
    "goalAchievementRate":{ "value":100.0, "previousValue":null, "delta":null },
    "averageTaskDurationSec":{ "value":1.8, "previousValue":null, "delta":null },
    "agentAvailability":{ "value":100.0, "previousValue":null, "delta":null },
    "tokenBudget":100000,
    "taskStatusDistribution":{ "PENDING":0,"QUEUED":0,"BLOCKED":0,"RUNNING":0,"VALIDATING":0,"COMPLETED":3,"FAILED":0,"ESCALATED":0,"PAUSED":0,"SKIPPED":0,"CANCELLED":0 },
    "taskDurations":[ { "taskId":"c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21", "taskName":"初始化", "goalName":"基礎", "durationSec":1.9 } ],
    "retryDistribution":[ { "retries":0, "tasks":3 } ] },
  "timestamp":"2026-10-15T16:40:00+08:00", "traceId":"…" }
```

#### 1.3.2 `GET …/token-trend`　〔API-MON-02／US-M-02〕

- **角色**：VIEWER。成功 200：`List<TokenTrendPoint>{bucketStart,tokens,cumulativeTokens,budget}`（依 `bucketStart` 升冪）。來源 `console.run_token_samples`（§0.5）：`tokens`＝桶內 `delta` 之和、`cumulativeTokens`＝自視窗起點累計；沒有資料的桶不補零；`budget`＝所屬批次的 `tokenBudget`（多批次取視窗內最新批次；無預算為 null）。

#### 1.3.3 `GET …/task-trend`　〔API-MON-03／US-M-03〕

- **角色**：VIEWER。成功 200：`List<TaskTrendPoint>{bucketStart,started,completed,failed,retried}`。來源 `execution_steps`：桶內 `STARTED`／`COMPLETED`／`FAILED`／`RETRYING` 列的筆數。成功／失敗比率由前端以 `completed`、`failed` 計算。

#### 1.3.4 `GET …/alerts`　〔API-MON-04、ALR-01～06／US-M-05〕

- **角色**：VIEWER。查詢參數：`runId`、`acknowledged`（`true`／`false`／省略）、`limit`（1～200，預設 50）。成功 200：`List<AlertResponse>`（`createdAt` 由新到舊）。
- `rule` 值域＝PRD 六條規則＋`ENGINE_ESCALATION`／`ENGINE_TOKEN_HALT`；各規則的判定與訊息樣板見 §3.7。

#### 1.3.5 `POST /api/v1/monitor/alerts/{alertId}/acknowledge`　〔API-MON-05／US-M-05〕

- **角色**：OPERATOR。無 body。成功 **204**。**冪等**：已確認者再次呼叫仍 204，且不改寫第一次的 `acknowledgedBy／At`。404（訊息 `告警不存在：<id>`）、400（id 格式）、401／403／429。確認後同一規則＋對象可再產生新告警。

#### 1.3.6 `GET …/logs`　〔API-MON-06／US-M-04〕

- **角色**：VIEWER。額外查詢參數：`level`（`ALL|INFO|WARN|ERROR`，預設 `ALL`）、`taskId`（uuid）、`q`（訊息關鍵字，不分大小寫，`%`／`_` 視為字面，≤200）、`order`（`asc|desc`，預設 `desc`）、`page`、`size`（預設 50、上限 200）。
- 成功 200：`Page<LogEntryResponse{id,timestamp,level,source,message,runId,taskId,stepId}>`。日誌**由既有資料衍生，不新增日誌表**，且**不含引擎原始 stdout**（原始行只在 SSE `log` 事件，`source=ENGINE`）；衍生規則見 §3.8.3。
- 錯誤：400（level／order／size 不合法、時間範圍）、404、401／429。

#### 1.3.7 `GET …/report?format=csv|pdf`　〔API-MON-07／US-M-07〕

- **角色**：VIEWER。查詢參數：`format`（`csv|pdf`，預設 `csv`）、`runId`、`from`、`to`。**不包 ApiResult 封包**。呼叫端 CSV 送 `Accept: text/csv`（或 `*/*`）；PDF 的 `Accept` 見下方 PDF 條。
- **CSV（必做）**：`Content-Type: text/csv; charset=UTF-8`；`Content-Disposition: attachment; filename="monitor-report-<projectId 前 8 碼>-<yyyyMMdd-HHmm>.csv"`（時間為 UTC）；UTF-8 含 BOM、行尾 CRLF、欄位依 RFC 4180 引號跳脫；**CSV 注入防護**：任何以 `=`、`+`、`-`、`@` 開頭的文字欄位在前面補一個單引號 `'`。內容為連續的區段，每段以 `#section,<名稱>` 行起頭、下一行是欄名、之後是資料列、段與段之間空一行：

```
#report,<專案名稱>,<from>,<to>,<runId 或 ALL>
#section,summary
metric,value,previousValue,delta,unit
taskCompletionRate,100.0,0.0,100.0,PERCENT
…（十個 KPI，順序同 §1.3.1；null 輸出空字串；unit ∈ PERCENT|COUNT|SECONDS|TOKENS）

#section,runs
runNumber,runId,status,autonomyLevel,startedAt,completedAt,durationSec,totalTokensUsed,tokenBudget,tasksTotal,tasksCompleted,tasksFailed

#section,tasks
goalName,taskName,status,retryCount,maxRetries,actualTokens,startedAt,completedAt,durationSec

#section,alerts
createdAt,severity,rule,subject,message,acknowledged,acknowledgedBy,acknowledgedAt
```

- **區段取數規則（B2-6；`MonitorService.report`）**：`runs` 含**所有 `started_at < to` 的批次**（不論是否在視窗內結束；有帶 `runId` 時只有該批次）；`tasks` 是範圍內未軟刪任務的現況；`alerts` 只含**視窗內**（`created_at ∈ [from,to)`）的告警。
- **PDF（v1.2，C-4；US-M-07／API-MON-07）**：`Content-Type: application/pdf`；`Content-Disposition: attachment; filename="monitor-report-<projectId 前 8 碼>-<yyyyMMdd-HHmm>.pdf"`（規則同 CSV，時間為 UTC）。內容是**與 CSV 相同的四個區段**（`summary`／`runs`／`tasks`／`alerts`，欄位與順序同上方 CSV，null 顯示 `—`；取數規則同上），另加標題（專案名稱＋「監控報表」）、時間範圍（`from`～`to`）、範圍（`runId` 或「全部批次」）與產生時間（UTC）；PDF 是純文字呈現，不做 CSV 的注入防護引號。以既有相依 **Apache PDFBox 3** 產生（附錄 D.4；**不新增相依**，v1.1 寫的 openhtmltopdf 作廢）。中文需內嵌 OFL 授權的 CJK 字型（建議 Noto Sans TC 靜態 Regular，字型檔與授權文字放 `backend/src/main/resources/fonts/`，以 `PDType0Font.load` 載入）；字型沒有的字元一律以 `?` 取代，**不得讓整份報表失敗**；實作環境確實取不到 CJK 字型時，允許退回英文欄位標籤（須在交卷〈沒做／偏離〉註明）。呼叫端 CSV 送 `Accept: text/csv`、PDF 送 `application/pdf`（皆可用 `*/*`），後端以 `format` 為準、**不因 Accept 不符回 406**。原 `501`／`PDF 報表尚未提供（W5）` 退役（§0.3 第 6 點）。
- 錯誤：400 `不支援的報表格式`（`details={format,supported:["csv","pdf"]}`）、400 `時間範圍不合法`、404、401／429。

#### 1.3.8 `GET /api/v1/monitor/task-totals`　全域任務總計（v1.2，C-1）　〔API-MON-08／US-M-03；QA DEF-AC-009〕

- **角色**：VIEWER 以上。**Bridge**：無（資料全來自 DB）。取代 v1.1 §4.6 G-G3 的做法（前端對每個專案各打一次 `task-trend` 再加總：單一總覽分頁穩態每分鐘約 31 次請求，用掉三成限流額度，專案數 ≥ 30 後一次快速導覽就會撞 429）：儀表板「本週完成」改打這一支，每 60 秒 1 次。
- **查詢參數**：

| 參數 | 型別 | 必填 | 規則 |
|------|------|:----:|------|
| `from` | date-time（帶 offset） | ✅ | 視窗起點（含）。缺漏或格式不合 → 400（`errors[].field=from`）；未編碼 `+` 的容錯同 §1.3 |
| `to` | date-time（帶 offset） | — | 視窗終點（不含）；預設現在 |

- **視窗規則**：`from` 必須早於 `to`，且 `to − from` **不可超過 92 天**；違反 → **400**，`errors=[{field:"to", message:…}]`，`reason=時間範圍不合法`（沿用 §1.3 既有的時間範圍 reason，不另立常數；主控裁決 C-1 的「400 `validation_error`（`errors[].field=to`）」即此形態，見 §6.5.1），`details={from,to,maxDays:92}`。
- **成功 200**：`ApiResult<TaskTotalsResponse>`，`data`＝`{ from, to, started, completed, failed, retried, projectsCounted }`：
  - `from`／`to`：實際採用的視窗（`to` 省略時為伺服器處理當下的時間）。
  - `started`／`completed`／`failed`／`retried`：`console.execution_steps` 中 `timestamp ∈ [from, to)` 且 `status` 為 `STARTED`／`COMPLETED`／`FAILED`／`RETRYING` 的**列數**——與 §1.3.3 `task-trend` **同一張表、同一判準**（只計所屬任務未軟刪的列），只是不分桶、跨全部**未封存且未軟刪除**的專案（`projects.status<>'ARCHIVED'` 且未軟刪，與 `projectCompletionRate` 的分母同一判準，§3.8.1）。
  - `projectsCounted`：上述專案中，在視窗內至少有一列被計入四個計數之一的專案數。
- **不變量（BE 以整合測試釘住）**：同一個視窗，對每個「未封存且未軟刪除」的專案各呼叫一次 `task-trend`（不帶 `runId`；`bucket=DAY`，免得 92 天視窗的 `HOUR` 桶數超過 1,000 而被 400）、把所有桶的 `started`／`completed`／`failed`／`retried` 各自加總，**逐欄等於**本端點的同名欄位。
- **說明**：`completed` 是步驟事件的列數，同一任務被還原重跑會重複計（與 `task-trend` 同）。儀表板「本週完成」顯示 `completed`：`from`＝本週一 00:00（瀏覽器本機時區）轉成 ISO-8601、`to` 省略。

```json
{ "code":200, "message":"success", "data":{
    "from":"2026-10-12T00:00:00Z", "to":"2026-10-15T08:40:00Z",
    "started":42, "completed":40, "failed":2, "retried":3, "projectsCounted":5 },
  "timestamp":"2026-10-15T16:40:00+08:00", "traceId":"…" }
```

| HTTP | reason | details／errors | 觸發 |
|------|--------|-----------------|------|
| 400 | （Bean Validation，reason 省略） | `errors=[{field:"from",message}]` | `from` 缺漏或格式不合；`to` 格式不合時 `field=to` |
| 400 | `時間範圍不合法` | `errors=[{field:"to",message}]`；`details={from,to,maxDays:92}` | `from` 不早於 `to`，或視窗超過 92 天 |
| 401／429 | 通用 | | |

### 1.4 通知

#### 1.4.1 `GET /api/v1/notifications/summary`（補）　〔API-NTF-01／US-E-07〕

- **角色**：VIEWER。成功 200：`NotificationSummaryResponse{pendingSignoffs, pendingReviews, unacknowledgedAlerts, bridgeConnected, bridgeCheckedAt}`，前三者為跨專案的整數：
  - `pendingSignoffs`＝`projects`、`goals`、`tasks` 三表中 `signed_off=false` 且未軟刪者（目標與任務所屬的專案、目標也須未軟刪）＋ `import_records` 中 `status∈{PARSED,REVIEWING}` 且 `signed_off=false` 者。每個待簽核的列算一次（執行閘要求三層全簽，每一列都是一次待做的 signoff）；`UPLOADED`／`PARSING` 的匯入記錄尚無可簽核內容，不計（§6 D-46）。**v1.4（D-18）：同一判準的清單端點是 `GET /signoffs/pending`（§1.8.1），它的 `counts.total` 恆等於本欄位**；
  - `pendingReviews`＝`review_requests.status='PENDING'` 總數；
  - `unacknowledgedAlerts`＝`alerts.acknowledged=false` 總數；
  - `bridgeConnected`／`bridgeCheckedAt`＝最近一次 Bridge 健康探測（每 30 秒，`GET {autoclaude.healthCheckPath}`，**v1.4 起預設 `/health/deep`、讀取逾時 8 秒**〔v1.3 以前為 `/health`、3 秒〕，§3.1）的結果與時間；從未探測為 null。**v1.4 的語意變化**：探測成功＝回 2xx；Bridge 行程可達但深度自檢未通過（503 `degraded`：`git`／`autoclaude`／`workspace`／`db` 四項任一失敗，§3.1.1；`sdd` 只當資訊、不影響）也是 `false`——所以 `false` 涵蓋「連不上」與「連得上但引擎不可用」兩種，摘要不區分（要區分需另增欄位，列為後續候選）。供頂列「Engine Bridge · 已連線」綠點（設計稿全域元素；`/actuator/health` 只代表 console-api 自己）。**歸屬（AR-08）**：這支端點由 W3-B1 實作，B1 階段兩欄一律回 null（探測環還不存在）；W3-B2 建好探測環後，在**同一支 controller** 補上實值，不新增端點。前端在 B1 階段看到 null 顯示「未知」灰點。
- 供頂列通知鈴與 signoff 佇列徽章輪詢：間隔＝`monitor.refreshIntervalMs`，**預設與最小值皆為 10 秒**（AR-06）；限流鍵是 JWT subject，同一使用者所有頁面共用每分鐘 100 次（§0.4 第 4 點）。401／429。

### 1.5 系統參數（Phase 6）

**Bridge**：設定端點不呼叫 Bridge（`test-connection` 是 console-api 直連模型端點，不經 Bridge）；參數經 `ConfigMaterializer` 在**執行時**才物化給 Bridge（§3.4.2）。**每個鍵的型別、預設、驗證、範圍、選項、影響提示與引擎效果＝附錄 C（唯一真相源）**。以下通則：

- `value` 一律是字串：`INTEGER`／`LONG`＝`^(0|-?[1-9][0-9]*)$`；`FLOAT`＝`^-?[0-9]+(\.[0-9]+)?$`；`BOOLEAN`＝小寫 `true`／`false`；`ENUM`＝選項之一（區分大小寫）；`STRING`＝不含 NUL、≤ 4,000 字元；`ENCRYPTED`＝非空 ≤ 512 字元，或空字串表示清除。
- 加密參數（`is_encrypted=true`：`model.apiKey`、`autoclaude.dbDsn`）以 AES-256-GCM 儲存（金鑰 `CONSOLE_ENCRYPTION_KEY`，base64 的 32 bytes；缺少或長度不對＝**啟動失敗**）；GET 一律回遮罩字串 `••••••••`（U+2022 共八個）＋`hasValue`；歷史與匯出同樣遮罩；明文只在 `reveal=true`（ADMIN）時回傳，且每次揭露寫審計日誌（只記分類與次數，不記值）。
- 每次成功寫入都寫一筆 `system_config_history`（加密參數的新舊值一律存遮罩標記，不存明文或密文）。

#### 1.5.1 `GET /api/v1/settings`　〔API-SET-01／US-S-01、04、08〕

- **角色**：VIEWER；`reveal=true` 需 ADMIN（其他角色 403，reason `僅 ADMIN 可揭露敏感參數`）。成功 200：`Map<category, List<ConfigResponse>>`，分類順序 `model,agent,execution,monitor,autoclaude,sdd`，分類內依附錄 C 順序。`reveal` 不是布林值（例：`reveal=abc`）→ **400**：`message=參數 reveal 的值格式不正確`、`errors=[{field:"reveal",…}]`、reason 省略（B1-4；Spring 的型別不符統一走 `GlobalExceptionHandler.handleTypeMismatch`，與其他端點的路徑／查詢參數格式錯誤同一格式）。`reveal=true` 以**分類**為單位（沒有單鍵揭露端點），每次揭露寫一筆審計（F1-5，§4.4 S-05）。
- `ConfigResponse`：`id, category, key, value, valueType, defaultValue, description, isEncrypted, hasValue, validationRule, options, min, max, impactNote, effect, updatedAt, updatedBy`（`options`／`min`／`max`／`effect` 來自附錄 C 的 `ConfigCatalog`，`impactNote` 讀 `system_configs.impact_note`（V5 依附錄 C 寫入，§0.5）；`effect∈ENGINE|CONSOLE|STORED_ONLY|UNVERIFIED`，誠實標示該參數是否真的影響引擎）。

#### 1.5.2 `GET /api/v1/settings/{category}`　〔API-SET-02〕

- 同 1.5.1，只回一個分類（`List<ConfigResponse>`）；分類不在六個之內 → 404（訊息 `設定分類不存在：<category>`）；`reveal` 非布林同樣 **400**（B1-4）。

#### 1.5.3 `PUT /api/v1/settings/{category}/{key}`　〔API-SET-03、10／US-S-02、08〕

- **角色**：ADMIN。**Request**（`UpdateConfigRequest`）：`{ "value": "<字串>", "confirm": true|false(選填) }`。
- **驗證順序**：

| # | 檢查 | HTTP | reason | details |
|---|------|------|--------|---------|
| 1 | 鍵存在 | 404 | （訊息）`設定鍵不存在：<category>.<key>` | — |
| 2 | 型別、`validationRule`、`min`／`max`、`options` | 400 | `參數值不符合型別或驗證規則` | `errors=[{field:"value",message:"需為整數（1～10）"}]`；`details={valueType,validationRule,min,max,options}` |
| 3 | `model.apiUrl`：SEC-04 規則 1～5（§1.5.7：格式、scheme、userinfo、IP 字面類別、allowlist；**不做 DNS**；loopback 字面只有 `allow-loopback=true` 且在 allowlist 內才放行）。值必須是「完整的 chat-completions 端點 URL」，後端不替它補路徑 | 400 | `目標位址未通過 SSRF／allowlist 檢查` | `{host,violation}` |
| 4 | token_guard 單鍵：讀對端鍵現值，`halt > compact` 且各自在範圍內 | 400 | `halt_threshold_pct 必須大於 compact_threshold_pct` | `{compactThresholdPct,haltThresholdPct}`（以更新後的值為準）；`errors=[{field:"value",message:"必須大於 compactThresholdPct"}]`——**單鍵端點一律 `field=value`**（B1-6；`SettingsService.update` 的 `requireTokenGuardOrder(…, "value")`；單鍵重置與分類重置同），群組端點 §1.5.4 才是 `haltThresholdPct` |
| 5 | 加密鍵未帶 `confirm=true` | 409 | `敏感參數更新需二次確認（confirm=true）` | `{category,key}` |

- **成功 200**：`ConfigResponse`（加密值遮罩）。值未變更（與現值相同）仍回 200，但**不寫歷史**。
- 錯誤另有 401／403（非 ADMIN）／429。

#### 1.5.4 `PUT /api/v1/settings/execution/token-guard`　〔API-SET-04／NFR-SEC-05〕

- **角色**：ADMIN。**Request**（`TokenGuardRequest`）：`{ "compactThresholdPct": 70, "haltThresholdPct": 95 }`（皆整數；`compact` 1～99、`halt` 2～100）。同一交易內校驗並寫兩個鍵。
- **成功 200**：`List<ConfigResponse>`（`compactThresholdPct`、`haltThresholdPct` 兩筆）；各寫一筆歷史（值未變者不寫）。
- **錯誤**：400 `halt_threshold_pct 必須大於 compact_threshold_pct`（`halt <= compact`，含相等；`errors=[{field:"haltThresholdPct",message:"必須大於 compactThresholdPct"}]`、`details={compactThresholdPct,haltThresholdPct}`）；400 Bean Validation（缺欄位、非整數、超出範圍；`errors[]`，reason 省略）；401／403／429。**任何失敗都不改任何一個鍵**。

#### 1.5.5 `POST /api/v1/settings/{category}/{key}/reset`　〔API-SET-05／US-S-03〕

- **角色**：ADMIN。查詢參數 `confirm`（布林，預設 false）。把 `value` 設回 `default_value` 並寫歷史。
- **錯誤**：404；409 `敏感參數重置需二次確認（confirm=true）`（加密鍵未帶 `confirm=true`）；400 `halt_threshold_pct 必須大於 compact_threshold_pct`（重置單一 token_guard 鍵後違反跨鍵約束，例如 halt 目前 75 時重置 compact→80）；401／403／429。
- **成功 200**：`ConfigResponse`。

#### 1.5.6 `POST /api/v1/settings/{category}/reset`（補）　〔API-SET-05／US-S-03〕

- **角色**：ADMIN。設計稿底部「全部重置為預設值」。查詢參數 `confirm`。同一交易內逐鍵重置並各寫歷史；**加密鍵預設略過**（要連同重置須 `confirm=true`）；token_guard 以重置後的最終值做跨鍵校驗，不滿足 → 400（同上 reason，且整批不套用）。
- **成功 200**：`List<ConfigResponse>`（該分類全部鍵的最新狀態）；404 分類不存在。

#### 1.5.7 `POST /api/v1/settings/test-connection`　〔API-SET-06／US-S-05／NFR-SEC-04〕

- **角色**：ADMIN。**Request**（選填；`TestConnectionRequest`）：`{ "apiUrl"?, "apiKey"?(僅寫入、不回顯), "model"? }`；省略的欄位取已儲存的 `model.apiUrl`／`model.apiKey`／`model.name`。金鑰**不寫日誌、不回顯**。
- **`apiUrl` 的語意（AR-09）**：**完整的 chat-completions 端點 URL**（例：`https://api.minimax.io/v1/text/chatcompletion_v2`），與系統參數 `model.apiUrl` 相同；不是 base URL，後端**不會**替它補路徑。
- **檢查順序（SEC-04；任一不過 → 422，且未發出任何連線）**：

| # | 規則 | `details.violation` |
|---|------|---------------------|
| 1 | URL 可解析；無空白／控制字元／反斜線；連接埠合法；host 只能是 ASCII（含非 ASCII 的 IDN 一律拒絕）；**IP 字面必須是標準寫法**（IPv4 點分十進位四段、IPv6 標準寫法）——十進位整數、十六進位、八進位、縮寫（如 `127.1`）一律拒絕；**host 不可為空**（`file:///x`、`http:///x` 這類空 host 一律 `malformed_url`——規則 1 先於規則 2，所以不會得到 `scheme`；B1-2，`OutboundUrlPolicy.checkStatic`） | `malformed_url` |
| 2 | scheme 只能 `http`／`https` | `scheme` |
| 3 | 不得含 userinfo（`user:your_password_here@host` 這種寫法一律拒絕） | `userinfo` |
| 4 | host 先小寫、去尾端 `.`（IP 字面 `127.0.0.1.` 視同 `127.0.0.1`，**仍套分類與 allowlist**；B1-2）；host 為 **IP 字面**（已過 1 的標準寫法）時分類：`127.0.0.0/8`、`::1`→`loopback`；`169.254.0.0/16`（含 `169.254.169.254`）、`fe80::/10`→`link_local`；`10/8`、`172.16/12`、`192.168/16`、`fc00::/7`、`100.64/10`、`0.0.0.0/8` 等→`private_ip`。`link_local`、`private_ip` **任何 profile 都拒絕，即使該字面列在 allowlist**；`loopback` 預設拒絕，只有「`console.security.allow-loopback=true`（僅 e2e／test／本機 profile）**且**該字面完全等於 allowlist 某項」才放行 | `loopback`／`link_local`／`private_ip` |
| 5 | host（小寫、去尾端 `.`）必須與 `console.security.outbound-allowlist` 的某項**完全相等** | `not_in_allowlist` |
| 6 | 僅限名稱 host：DNS 解析所有 A／AAAA，**任一**位址落在 `link_local`／`private_ip` 類 → 拒絕（名稱解析到內網＝DNS rebinding 型態，**即使該名稱在 allowlist 內**）；落在 `loopback` 類同樣拒絕，除非 `console.security.allow-loopback=true`（已過 5，即該名稱在 allowlist 內）。測試環境以 `console.security.test-dns-overrides` 讓解析結果可決定地重現 | `dns_rebinding` |

**放行規則一覽**（以 host 在 allowlist 內為前提；不在 allowlist 者一律停在規則 4 或 5）：

| 位址類別 | production／docker | e2e／test／本機（`allow-loopback=true`） |
|----------|--------------------|-------------------------------------------|
| 公開位址 | 放行 | 放行 |
| loopback（`127.0.0.0/8`、`::1`；字面或解析結果） | 拒絕（`loopback`／`dns_rebinding`） | 放行 |
| link-local | 拒絕 | 拒絕 |
| 私網（含 `100.64/10`） | 拒絕 | 拒絕 |

  本契約**沒有**「允許私網」的旗標：e2e 的假伺服器一律綁在 `127.0.0.1`（loopback），所以只需要 `allow-loopback`；`rebind.e2e.test` 在 allowlist 內但被 `test-dns-overrides` 解析到私網位址 `10.0.0.5`，用來驗 `dns_rebinding`，兩者互不衝突（E2E-10）。預設 allowlist 與 Bridge 對齊：`api.minimax.io,api.minimax.chat`（AR-09）；e2e／本機 profile 另加 `127.0.0.1,localhost`（§6 D-47）。
- **連線實作（AR-10）**：通過 1～6 後必須**把連線釘死在已驗證的 IP**，並以原 host 作 `Host` 標頭與 TLS SNI／主機名驗證，**不自動跟隨 redirect**。JDK 內建的 `HttpClient` 做不到（沒有 DNS resolver 注入點；`Host` 是受限標頭；改用 IP 字面 URL 會讓 TLS 驗證對到 IP 而不是原 host），所以契約核可新增 **Apache HttpClient 5**（`org.apache.httpcomponents.client5:httpclient5`，版本由 Spring Boot BOM 管理，附錄 D.4）：以自訂 `DnsResolver` 回傳已驗證的 IP（`test-dns-overrides` 由同一個 resolver 先查）、請求 URI 保留原 host、`RequestConfig` 關閉 redirect。`test-connection` 與匯入路徑 B 的 LLM client（§3.3.3）都走同一個封裝（建議 `OutboundHttpClient`），`RestClient` 以 `HttpComponentsClientHttpRequestFactory` 包它，`MockRestServiceServer` 仍可用於測試。
- **探測請求**（AR-09）：`POST <apiUrl>`（完整端點，原樣，不改路徑），標頭 `Authorization: Bearer <apiKey>`（無金鑰則不帶）、`Content-Type: application/json`、`Accept: application/json`、`User-Agent: aisdlc-console`；本文 `{"model":"<model>","messages":[{"role":"user","content":"ping"}],"max_tokens":1,"stream":false}`；總逾時 `min(model.timeout, 10)` 秒、連線逾時 5 秒。這會消耗供應商端約一個 token 的用量；v1.0 的 `GET /v1/models` 探測對「完整端點」形式的 URL 沒有意義（MiniMax 的預設端點沒有模型列表）。
- **成功 200**（只要實際嘗試過連線，成功或失敗都是 200）：`ConnectionTestResponse{success,latencyMs,message,resolvedHost,httpStatus}`：

| 結果 | `success` | `message` |
|------|-----------|-----------|
| HTTP 2xx | true | `連線成功` |
| HTTP 401／403 | false | `認證失敗（HTTP 401）` |
| HTTP 404／405 | false | `端點路徑不存在或不接受 POST（HTTP 404）` |
| 3xx | false | `目標回應重新導向，已拒絕跟隨（HTTP 302）` |
| 其他 4xx／5xx | false | `服務回應錯誤（HTTP 503）` |
| 逾時 | false | `連線逾時（<N> 秒）` |
| 拒絕連線／其他 I/O | false | `無法連線：<簡短原因>` |

  `latencyMs`＝送出請求到收到回應標頭的毫秒數（無回應為 null）；`resolvedHost`＝URL 的 host（小寫）。
- **422**：`目標位址未通過 SSRF／allowlist 檢查`，`details={host,violation}`（無連線）。每次呼叫（含被拒）寫審計：`settings.testConnection`＋host＋結果，絕不記金鑰與 userinfo。
- 另：400（body 格式）、401／403／429。

#### 1.5.8 `GET /api/v1/settings/history`　〔API-SET-07／US-S-07〕

- **角色**：VIEWER。查詢參數：`category`、`key`（需與 `category` 併用，單獨給 `key` → 400）、`page`、`size`（預設 20、上限 100）。成功 200：`Page<ConfigHistoryResponse{id,configId,category,key,oldValue,newValue,changedAt,changedBy}>`（`changedAt` 由新到舊；加密參數兩個值一律 `••••••••`）。

#### 1.5.9 `POST /api/v1/settings/export`　〔API-SET-08／US-S-06〕

- **角色**：ADMIN。**不包 ApiResult**，直接回 `application/json` 檔：`Content-Disposition: attachment; filename="aisdlc-settings-<yyyyMMdd>.json"`。

```json
{ "version":1, "exportedAt":"2026-10-15T08:45:00Z",
  "configs":[ { "category":"model","key":"apiUrl","value":"https://api.minimax.io/v1/text/chatcompletion_v2" },
              { "category":"model","key":"apiKey","value":"<encrypted>" } ] }
```

- 全部 50 個鍵都輸出；加密參數的 `value` 固定為字串 `<encrypted>`（W3 任務書的作法；偏離 Architecture「不含敏感值」只是形式，§6 D-24）。

#### 1.5.10 `POST /api/v1/settings/import`　〔API-SET-09／US-S-06／NFR-SEC-05〕

- **角色**：ADMIN。`multipart/form-data`，欄位 `file`（≤ 1 MB；內容為 `version=1` 的 `SettingsExportDocument`）。
- **處理**（v1.2，C-6；QA DEF-AC-002、B1-7；實作＝`SettingsService.importSettings`）：同一個鍵在檔內出現多次以最後一筆為準；對每一項**依下列固定順序**判定，先成立者勝：
  1. 未知的 `category.key` → `errors`（`reason:"設定鍵不存在"`）；
  2. 值為 `<encrypted>` 佔位 → **略過**（計 `skipped`）；
  3. 該鍵是加密鍵、但給的是非佔位值（明文）→ 列入 `errors`、**不套用**（`reason` 同 1.5.3 第 5 項：`敏感參數更新需二次確認（confirm=true）`；匯入不能繞過二次確認）；
  4. **值與現值相同 → 計 `skipped`，不做任何值規則與 allowlist 驗證**。匯出後原樣匯入因此一定 `errors=[]`，即使現值的 `model.apiUrl` 主機不在 allowlist（v1.1 的實作先驗證、後比值，是 DEF-AC-002 的根因：e2e 的 allowlist 不含預設的 `api.minimax.io`，匯出再匯入就出現 `model.apiUrl` 的 errors）；
  5. 驗證（型別／規則／範圍／選項／SEC-04 allowlist，同 1.5.3 的 2、3）不過 → `errors`；
  6. 通過者成為候選。
  token_guard 兩鍵以**「候選＋現值」合併後的最終值**做 `halt > compact` 跨鍵校驗，不滿足則兩鍵皆列入 `errors`（`reason:"halt_threshold_pct 必須大於 compact_threshold_pct"`）且都不套用。候選在**同一交易**套用並各寫歷史（計 `applied`）。
- **成功 200**：`ImportSettingsResponse{applied,skipped,errors:[{category,key,reason}]}`（部分失敗仍是 200）。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | `設定檔格式錯誤` | `{problem:"invalid_json\|missing_configs\|unsupported_version"}` | 不是 JSON（`invalid_json`）／`version≠1`（`unsupported_version`）／缺 `configs` 陣列，**或其中某一項的結構不合法**（不是 `{category,key,value}`、`value` 缺漏或為物件／陣列；一律 `missing_configs`；B1-7，`SettingsFileReader.read`） |
| 413 | `設定檔超過 1MB 上限` | `{limitBytes:1048576}` | |
| 415 | `只接受 JSON 設定檔` | | 副檔名不是 `.json`，**或**內容型別不含 `json`／`octet-stream`（內容型別為空放行；B1-7，同一支 `SettingsFileReader.read`） |
| 401／403／429 | 通用 | | |

### 1.6 專案復原與 Phase 2 補充（v1.2）

本節的端點都屬 Phase 1+2 的資源（專案／目標／任務），其基本契約在 PRD §7.1.1～§7.1.3 與 Phase 2 實作；v1.2 只列**新增或改變**的部分。

#### 1.6.1 `POST /api/v1/projects/{id}/restore`　復原軟刪除的專案（v1.2，C-3）　〔API-PRJ-06／NFR-9.3-04〕

- **角色**：OPERATOR 以上（VIEWER → 403 `ACCESS_DENIED`）。無 body。**Bridge**：無。
- **前置**：專案存在、`is_deleted=true`，且 `deleted_at` 在保留期內（`deleted_at ≥ 現在 − console.retention.soft-delete-days`，預設 30 天，§1.6.5、附錄 D.2）。保留期**與清除排程是否開啟無關**：期外的專案即使還留在資料庫，也不可經 API 復原。
- **處理**（單一交易）：
  1. 專案：`is_deleted=false`、`deleted_at=NULL`、`status` 還原為 `status_before_delete`（升級前就已軟刪、該欄為 NULL 者：未 signoff → `DRAFT`，已 signoff → `READY`）、`status_before_delete=NULL`、`updated_at=now`；`signedOff` 等其餘欄位原樣保留。
  2. **同一次刪除連帶軟刪的目標與任務**：`is_deleted=false`、`deleted_at=NULL`——辨識方式＝其 `deleted_at` **等於**專案的 `deleted_at`（§0.5 V9：刪除專案時三者寫同一個時間值）。**單獨先刪除的目標／任務**（`deleted_at` 與專案的不同）維持已刪除，不隨專案回來。
  3. `goal_dependencies`、`execution_runs` 與其步驟／檢查點／審核項／告警等不曾被刪除，原樣可見；目標／任務的 `status`、`retry_count` 等欄位在刪除時就沒動過，原樣保留。
  4. 審計：`audit_log`（`action=project.restore`、`entity=project:<id>`）。
- **成功 200**：`ApiResult<ProjectDetailResponse>`（Phase 2 同名 schema：專案全部欄位＋目標摘要清單，只含復原後未刪的目標）。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （訊息）`參數 id 的值格式不正確` | | 路徑參數不是 UUID |
| 403 | `ACCESS_DENIED` | | VIEWER |
| 404 | （訊息）`專案不存在或已清除：<id>` | | 沒有這個 id，或已被清除排程實體刪除 |
| 409 | `project_not_deleted` | `{projectId, status}` | 專案目前沒有被軟刪除 |
| 409 | `restore_window_expired` | `{projectId, deletedAt, retentionDays}` | `deleted_at` 早於「現在 − 保留期」 |
| 401／429 | 通用 | | |

#### 1.6.2 `GET /api/v1/projects?deleted=true`　列出已軟刪除的專案（v1.2，C-3）

- Phase 2 既有的 `GET /api/v1/projects` 新增查詢參數 `deleted`（布林，預設 `false`）：`true`＝**只列軟刪除的專案**（`is_deleted=true`）；`false`／省略＝只列未軟刪除者（原行為不變）。其餘參數（`page,size,q,status,sort`）照常；`sort` 白名單不變、預設 `updatedAt,desc`——軟刪除當下會更新 `updated_at`，所以「已刪除」清單預設即「最近刪除的在前」。
- **角色**：`deleted=true` 需 OPERATOR 以上，VIEWER → **403** `ACCESS_DENIED`（由 controller 檢查；`deleted=false` 仍是 VIEWER 以上）。`deleted` 不是布林值 → 400（格式同 B1-4）。
- 列表項 `ProjectSummaryResponse` 新增 **`deletedAt`**（date-time；只有 `deleted=true` 的列表帶值，其餘缺席）。保留期已過（`restore_window_expired`）的專案**仍會列出**（資料還在，清除排程預設又是關的）；前端可在按「復原」得到 409 後提示，是否過期也可由 `deletedAt` 與保留期推算，列表不另帶欄位。

#### 1.6.3 `DELETE /api/v1/goals/{id}`、`DELETE /api/v1/tasks/{id}`　執行中刪除（v1.2，C-8；QA O-05）

- Phase 2 既有端點（204；目標含 `RUNNING` 任務、任務本身 `RUNNING` 時 409 `RUNNING 狀態的任務不可刪除`，不變）。v1.2 新增：**所屬專案有進行中批次時，刪除目標或任務一律 409**，`reason=project_executing`，`details={projectId, runId}`（任一進行中批次的 id）。
- 「進行中批次」＝該專案存在 `execution_runs.status ∈ {INITIALIZING, RUNNING, PAUSED}` 的批次——即 Bridge 的 `RUNNING`／`PAUSING`／`PAUSED`／`CANCELLING`（`PAUSING`／`CANCELLING` 折為 `RUNNING`，§0.6）。理由：批次進行中刪除「尚未開始」的目標／任務，批次仍照原 playbook 跑完，結果與畫面對不上（O-05）。
- 檢查順序：404 → **`project_executing`** → 既有的 `RUNNING 狀態的任務不可刪除`（兩者並存時先回前者，因為它涵蓋更廣）。
- 專案本身的刪除（`DELETE /api/v1/projects/{id}`）維持 Phase 2 規則（`EXECUTING` → 409 `EXECUTING 狀態的專案不可刪除`），不變。
- 前端：顯示原因（附錄 B 的 `project_executing`）；批次結束後即可再刪。

#### 1.6.4 `POST /api/v1/tasks/{id}/retry`　手動重試明文（v1.2，C-9；QA O-04）

- Phase 2 既有端點（OPERATOR；D-34）。行為不變：只允許 `FAILED`／`ESCALATED`（否則 409 `目前狀態不可重試`）；`retryCount+1`、狀態轉 `QUEUED`；**不啟動 run**。
- **v1.2 明文：手動重試不受 `maxRetries` 限制。** `maxRetries` 是引擎對「自動重試」的上限；人工介入的重試不算自動重試，所以 `retryCount` 可大於 `maxRetries`（例：ESCALATED 任務按「重試」後 `retryCount=3`、`maxRetries=1`）。審核 `RETRY` 同理（§1.2.11）。
- 前端文案（主控裁決）：toast 由「重試 N / M」改為 **「手動重試第 N 次（不計入自動重試上限 M）」**，`N`＝回應的 `retryCount`、`M`＝`maxRetries`。

#### 1.6.5 軟刪除保留期與清除排程（v1.2，C-3；ADR-001 D19）

| 屬性 | 預設 | 說明 |
|------|------|------|
| `console.retention.soft-delete-days` | `30` | 軟刪除專案可復原的天數（≥ 1）；PRD NFR-9.3-04「所有刪除操作皆為軟刪除，支援 30 天內復原」 |
| `console.retention.purge-enabled` | **`false`** | 是否註冊每日清除排程。**預設關閉**：實體刪除不可逆，部署者必須明確開啟；未開啟時軟刪除資料只會累積、不會消失 |

- **清除排程**（`purge-enabled=true` 時才註冊；每日一次，時間由實作決定）：實體刪除 `deleted_at < 現在 − soft-delete-days` 的**專案及其整棵子資料**（目標、任務、目標依賴、執行批次與其步驟／檢查點／審核項／告警／token 樣本；`import_records.project_id` 置 NULL），每個專案一個交易，單一專案失敗只記 WARN、不影響其他專案；audit 記 `project.purge`（subject `system`）。**範圍只有專案層級**：在存活專案內單獨軟刪除的目標／任務不被清除（它們隨其專案被清除時才一併實體刪除）。
- 有單元測試（排程邏輯可注入時鐘；`purge-enabled=false` 時不註冊排程）。

### 1.7 引擎狀態（v1.4；D-16）

#### 1.7.1 `GET /api/v1/engines/sdd`　AISDLC_SDD 引擎狀態（只讀）（v1.4，D-16）　〔API-ENG-01／NFR-OBS-01、BR-13、BR-14〕

- **角色**：VIEWER 以上。**Bridge**：依序呼叫 `GET /sdd/version`、`GET /sdd/fsm`，帶了 `project` 時再呼叫 `GET /sdd/fsm/{project}`（§3.1.3）；三者全是唯讀，console-api 不寫 SDD 目錄、不寫任何 FSM-STATE 檔（ADR-001 D22 第 3 點）。每個呼叫連線／讀取逾時 2 秒／3 秒、不重試，失敗即短路（後面的呼叫不再發）；這支端點不快取，每次請求都打 Bridge。
- **v1.5 加註（D-115-01、D-115-02、D-115-14；S-10）**：①本端點新增選填查詢參數 `projectId`，依專案帶 `root`，讀「該專案根目錄下」的 FSM 狀態（§1.10.4）；②`SddFsmState` 新增 `phase`、`escalationHistory`、`escalationProvenance`、`fsmProject`、`recovery`（§1.10.4）；③`project` 的驗證由 `^[A-Za-z0-9._-]{1,128}$` 改為「1～200 字元、不含控制字元」，值原樣交給 Bridge 的淨化鏡像處理（§3.1.4 (b)；ADR-016 §7.4）——下表「`project`」列、`errors[0].field=project` 的判準與附錄 D.1 的舊 regex 一律以本條與 §1.10.4 為準；④本端點本身仍只讀、console-api 仍不直接寫任何 FSM-STATE 檔——v1.5 唯一的 FSM 寫入動詞是 Bridge 的 `:freeze`，經 FSMRuntime CLI 子行程完成（§3.1.4；ADR-001 D22 第 3 點的「Console 只讀」由 ADR-016 修訂為「只經 CLI 窄寫」）。
- **為什麼有它**：PRD §0.2、§0.3 把 FSM-STATE 列為 Console 對 SDD 的遙測來源，但 v1.3 以前 Bridge 的 `/sdd/version`、`/sdd/fsm/{project}` 在 Console 後端與前端沒有任何消費者（完整性審查 I-01、I-02、V-06），Console 只用過規格編譯（`/sdd/compile`）。本端點是 Console 對 FSM 狀態的唯一消費點，供監控頁「AISDLC_SDD 引擎」卡（§4.3 M-20）與 NFR-OBS-01 的「FSM 檔 ↔ Console 渲染」對照（E2E-15）使用。
- **查詢參數**：

| 參數 | 型別 | 必填 | 規則 |
|------|------|:----:|------|
| `project` | string | — | FSM 專案名，須符合 `^[A-Za-z0-9._-]{1,128}$`（與 Bridge 同一個白名單）；不合 → **400**（`errors[0].field=project`）。省略 → `fsm` 為 null（**不帶** `reason`），由前端依 `projects` 選一個再帶 `project` 重取 |

- **成功 200**：`ApiResult<SddEngineStatusResponse>`。**引擎不可用也回 200**（沿用 §1.2.3「Bridge 不可達回 200」的慣例）：這支端點回報的是「引擎現在的狀態」，不是「這次呼叫成不成功」，前端據此畫「不可用」而不是錯誤頁。`data`：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `available` | boolean | `GET /sdd/version` 與 `GET /sdd/fsm` 都成功為 true；任一失敗為 false |
| `reason` | string \| null | 見下方映射表；`available=true` 且沒有問題時為 null |
| `version` | `{latest, root}` \| null | `latest`＝SDD 版本目錄名（例 `AISDLC_SDD_v0.30`）；`root`＝**Bridge 看到的**目錄路徑（Docker 下是容器內路徑；僅供顯示，前端預設只秀 `latest`）；`GET /sdd/version` 失敗為 null |
| `projects` | `SddProjectEntry[]` | `{project, source, currentState, updatedAt}`：`project`＝FSM-STATE 檔名中的專案名、`source`＝檔名、`currentState`／`updatedAt` 取檔內 `fsm_state` 同名鍵（缺則 null）；順序＝Bridge 清單順序（專案名不分大小寫升冪，§3.1.3；console-api 不重排）；`available=false` 時為 `[]` |
| `fsm` | `SddFsmState` \| null | 帶了 `project` 且取得時有值；其餘為 null |
| `checkedAt` | date-time | console-api 處理這次請求的時間（UTC，`…Z`） |

`SddFsmState`（對映 Bridge `GET /sdd/fsm/{project}`；**最外層鍵轉 camelCase，巢狀內容原樣**＝FSM 檔寫什麼就是什麼，保留 snake_case 鍵，使「檔案 ↔ API ↔ 畫面」可逐值比對）：

| 欄位 | 型別 | 來源（Bridge 欄位＝`fsm_state` 內同名的鍵） |
|------|------|------|
| `project` | string | `project`（缺則以檔名中的專案名補） |
| `currentState` | string \| null | `current_state`（例 `INIT`、`HUMAN_PENDING`、`ESCALATION`） |
| `currentSprint` | integer \| null | `current_sprint` |
| `sessionId` | string \| null | `session_id` |
| `updatedAt` | string \| null | `updated_at`（ISO-8601 字串，原樣） |
| `frozenStages` | object[] | `frozen_stages`（原樣；缺則 `[]`） |
| `decisionTrace` | object[] | `decision_trace` 的**尾 5 筆**（舊→新，原樣；每筆 `{ts, from, to, reason, spec_refs, agents_consulted, trigger}`；缺則 `[]`） |
| `source` | string | 檔名（`FSM-STATE-<project>.yaml`） |
| `humanPending` | `{count, items}` | 待人工確認的數量與項目，語意見 §3.1.3 |
| `retryHistory` | `{count, last}` | 重試歷史的總筆數與最近一筆（`last` 是原筆再加一個 `gate` 欄＝所屬的重試閘名），語意見 §3.1.3 |
| `rtmCoverage` | object \| null | 見 §3.1.3；現行 FSM-STATE 沒有這個鍵，**現況恆為 null**，畫面不顯示 |

**`reason` 映射**（`SddEngineStatusResponse.reason` 是回應欄位，不是 `ApiError.reason`；§0.3 第 7 點、附錄 B.4）：

| `reason` | `available` | 觸發（Bridge 的回應 → 本端點） |
|----------|:-----------:|------------------------------|
| `bridge_unreachable` | false | 任一 Bridge 呼叫連線失敗或逾時 |
| `sdd_unavailable` | false | `GET /sdd/version` 或 `GET /sdd/fsm` 回 503 `sdd_unavailable`（`SDD_ROOT` 無效、找不到 SDD 版本目錄） |
| `bridge_error` | false | 其餘非 2xx（第一、二個呼叫的 5xx、422 等；第三個呼叫 404／422 以外的錯誤），或 2xx 但本文不是預期的 JSON 形狀 |
| `fsm_not_found` | true | 帶了 `project`，`GET /sdd/fsm/{project}` 回 404（`fsm_not_found`）：`fsm=null`，`projects` 與 `version` 照常 |
| `fsm_state_unreadable` | true | 帶了 `project`，Bridge 回 422（`fsm_state_unreadable`：YAML 壞掉、不是 UTF-8、缺 `fsm_state` 根節點、或巢狀過深）：`fsm=null` |
| （null） | true | 其餘；`projects=[]` 也是正常狀態（SDD 目錄存在、但還沒有任何 FSM 狀態檔——SDD runtime 沒跑過，前端顯示「尚無 FSM 狀態檔」） |

第三個呼叫（`GET /sdd/fsm/{project}`）若連線失敗、逾時或回 404／422 以外的錯誤：`available=false`，`reason` 依上表前三列，`fsm=null`；`version` 與 `projects` 保留前兩個呼叫已取得的值。Bridge `GET /sdd/fsm` 回應裡的 `errors[]`（讀不動的檔名）console-api 只記 WARN 日誌，不轉發。

```json
{ "code":200, "message":"success", "data":{
    "available":true, "reason":null,
    "version":{ "latest":"AISDLC_SDD_v0.30", "root":"/sdd/AISDLC_SDD_v0.30" },
    "projects":[
      { "project":"AISDLC_SDD", "source":"FSM-STATE-AISDLC_SDD.yaml", "currentState":"INIT", "updatedAt":"2026-07-15T17:36:40+00:00" } ],
    "fsm":{
      "project":"AISDLC_SDD", "currentState":"INIT", "currentSprint":1,
      "sessionId":"48cdae05-31cf-4b09-95c1-bb55929fb1c8", "updatedAt":"2026-07-15T17:36:40+00:00",
      "frozenStages":[], "decisionTrace":[], "source":"FSM-STATE-AISDLC_SDD.yaml",
      "humanPending":{ "count":0, "items":[] }, "retryHistory":{ "count":0, "last":null }, "rtmCoverage":null },
    "checkedAt":"2026-10-16T03:21:45Z" },
  "timestamp":"2026-10-16T11:21:45+08:00", "traceId":"…" }
```

- **輪詢**：前端 30 秒一次（只在「AISDLC_SDD 引擎」卡掛載且分頁可見時；§4.3 M-20）。理由：FSM 檔只在 SDD runtime 執行時才變動，不需要 SSE（ADR-001 D22 第 1 點）；30 秒大於輪詢地板 10 秒（§0.4 第 4 點），一個開著的卡片約每分鐘 2 次請求，監控頁其他輪詢合計仍在每分鐘 100 次內。
- **驗收**：`EnginesApiIT`（以迷你 Bridge 逐列驗映射表：有專案、帶 `project`、`project` 不存在、422、503 `sdd_unavailable`、連線失敗、逾時、未帶 `project`、非法 `project` 的 400、VIEWER 200／未認證 401）；E2E-15。

| HTTP | reason | details／errors | 觸發 |
|------|--------|-----------------|------|
| 400 | （Bean Validation，reason 省略） | `errors=[{field:"project",message}]` | `project` 不符 `^[A-Za-z0-9._-]{1,128}$` |
| 401／429 | 通用 | | |

### 1.8 待審批清單（v1.4；D-18）

#### 1.8.1 `GET /api/v1/signoffs/pending`　列出待簽核的草案（跨專案）（v1.4，D-18）　〔API-SGN-05／US-E-07〕

- **角色**：VIEWER 以上。**Bridge**：無（資料全來自 DB）。
- **為什麼有它**（完整性審查 I-05）：頂列徽章與儀表板 KPI「待審批草案數」取通知摘要的 `pendingSignoffs`（專案、目標、任務與待審批匯入記錄四種草案的總數，§1.4.1），但儀表板「待人工審批」卡的清單是前端用專案與目標 API 另外組的（`useSignoffQueue`：只有未簽專案與其底下未簽目標）——沒有任務、沒有匯入記錄、也沒有「已簽專案底下的草案」，數字大於點得到的項目。本端點以**同一組述詞**列出全部項目，卡片清單與計數從此同源。
- **查詢參數**：

| 參數 | 型別 | 必填 | 規則 |
|------|------|:----:|------|
| `limit` | integer | — | 清單最多回幾筆；預設 **50**、範圍 1～**200**；非整數或超出範圍 → **400**（`errors[0].field=limit`）。只截斷 `items`，**不影響 `counts`** |

- **判準**（與 §1.4.1 `pendingSignoffs` **完全相同**；四種各一段述詞）：
  1. `PROJECT`：`projects.signed_off=false` 且未軟刪；
  2. `GOAL`：`goals.signed_off=false` 且未軟刪，且所屬專案未軟刪；
  3. `TASK`：`tasks.signed_off=false` 且未軟刪，且所屬目標與專案都未軟刪；
  4. `IMPORT`：`import_records.status∈{PARSED, REVIEWING}` 且 `signed_off=false`（`UPLOADED`、`PARSING` 尚無可簽核內容；`IMPORTED`、`REJECTED` 是終態，皆不計，§6 D-46）。

  **實作約束**：計數與清單的述詞由同一處產生（同一組 SQL 片段），不得計數一份、清單一份；現行 `NotificationCountsAdapter.PENDING_SIGNOFFS` 就是計數那一份，BE 應把它與清單查詢收斂成單一來源。
- **排序**：`created_at` 升冪（最早的先處理），同值以 `id` 升冪（決定性）；`created_at` 為 NULL 者排最後。
- **成功 200**：`ApiResult<PendingSignoffsResponse>`，`data`＝`{ counts, items }`：`counts`＝`{projects, goals, tasks, imports, total}`（int；`total` 是四者之和）；`items[]`＝`PendingSignoffItem`：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `kind` | `PROJECT`／`GOAL`／`TASK`／`IMPORT` | 草案種類 |
| `id` | uuid | 該列的 id（也是 signoff 端點的路徑參數：`/projects｜goals｜tasks/{id}/signoff`、`/import/{id}/signoff`） |
| `projectId` | uuid \| null | 所屬專案；`PROJECT` 項＝自己的 id；**`IMPORT` 項為 null**（匯入記錄在 `confirm` 之前還沒有專案） |
| `projectName` | string \| null | 所屬專案名稱；`IMPORT` 項為 null |
| `parentId` | uuid \| null | `PROJECT`＝null；`GOAL`＝專案 id；`TASK`＝目標 id；`IMPORT`＝null |
| `title` | string | `PROJECT`／`GOAL`／`TASK`＝`name`；`IMPORT`＝`source_file_name`，沒有檔名（貼上文字）時為 `貼上文字` |
| `createdAt` | date-time | 該列的 `created_at`（UTC，`…Z`） |

- **不變量（BE 以整合測試釘住）**：①同一時刻，`counts.total` 等於 `GET /notifications/summary` 的 `pendingSignoffs`；②`counts.projects／goals／tasks／imports` 各自等於四段述詞單獨的計數；③`limit` 小於 `total` 時 `items.length＝limit`，且是排序後最前面的 `limit` 筆；④簽核一筆（任一種）後，`counts.total` 減 1、該筆從 `items` 消失；⑤已簽、已軟刪（含「專案已軟刪、其目標與任務未軟刪」）、狀態為 `UPLOADED`／`PARSING`／`IMPORTED`／`REJECTED` 的匯入記錄，都不出現。
- **前端用法**：儀表板「待人工審批」卡（§4.5 G-10）。

```json
{ "code":200, "message":"success", "data":{
    "counts":{ "projects":1, "goals":1, "tasks":0, "imports":1, "total":3 },
    "items":[
      { "kind":"IMPORT", "id":"…", "projectId":null, "projectName":null, "parentId":null, "title":"需求文件.md", "createdAt":"2026-10-15T01:02:03Z" },
      { "kind":"PROJECT", "id":"…", "projectId":"…", "projectName":"新專案", "parentId":null, "title":"新專案", "createdAt":"2026-10-15T08:30:12Z" },
      { "kind":"GOAL", "id":"…", "projectId":"…", "projectName":"新專案", "parentId":"<projectId>", "title":"基礎", "createdAt":"2026-10-15T08:30:13Z" } ] },
  "timestamp":"2026-10-16T11:21:45+08:00", "traceId":"…" }
```

| HTTP | reason | details／errors | 觸發 |
|------|--------|-----------------|------|
| 400 | （Bean Validation，reason 省略） | `errors=[{field:"limit",message}]` | `limit` 非整數或不在 1～200 |
| 401／429 | 通用 | | |

### 1.9 認證補充（v1.4；D-19；ADR-001 D16、D23）

本節屬 Phase 1+2 的認證資源（`/api/v1/auth/*`，免認證）：v1.4 新增登出端點，並把「refresh token 輪替與撤銷名單」做完——ADR-001 D16 原本承諾、但後端零實作（完整性審查 I-06）。

#### 1.9.1 `POST /api/v1/auth/logout`　登出並撤銷 refresh token（v1.4，D-19）　〔API-AUTH-03；主控裁決 Q6：視同核可〕

- **角色**：免認證（與 `login`、`refresh` 同：登出時 access token 可能已過期，仍必須能撤銷 refresh token）。**Bridge**：無。
- **請求**：`LogoutRequest{ refreshToken }`（`@NotBlank`；缺漏或空白 → 400，`errors[0].field=refreshToken`）。
- **成功 204**（無內容、無封包，同 `review`、`acknowledge`）。**只要請求格式合法就一律 204**：refresh token 有效 → 撤銷它的 `jti`；無效、過期、已被撤銷、或是 access token → 同樣 204，不撤銷任何東西。理由：不讓這支端點變成「探測某個 token 是否有效」的管道，也讓客戶端的登出流程不必處理失敗分支。
- **不撤銷 access token**：access token 無狀態，最長 30 分鐘後自然失效；撤銷名單只擋 refresh（D-19 的範圍）。要在登出當下就讓 access token 失效，必須每個請求都查名單，列為後續候選。
- **前端**：`logout()` 先以 fire-and-forget 呼叫本端點（帶目前 session 的 `refreshToken`；沒有 session 就不呼叫），**不等結果，網路失敗或非 2xx 也不阻擋本機登出**（清 session、清 TanStack Query 快取、導向 `/login` 照舊，§2.8 第 10 點）。
- **審計**：落 `audit_log`（§0.4 第 5 點對寫入方法一視同仁），`action=auth.logout`；匿名請求的 `subject` 為 NULL（與 `auth.login` 的匿名列一致，V6 欄位註解「未認證為 NULL」；W7-BE 實作定稿，`AuthApiIT::aLogoutIsAuditedWithAnEmptyAnonymousSubject` 釘住）。

| HTTP | reason | details／errors | 觸發 |
|------|--------|-----------------|------|
| 400 | （Bean Validation，reason 省略） | `errors=[{field:"refreshToken",message}]` | 缺漏或空白 |
| 429 | 通用 | | 未認證請求以客戶端 IP 計限流（§0.4 第 4 點） |

#### 1.9.2 refresh token 撤銷名單（v1.4，D-19）

| 項目 | 契約 |
|------|------|
| 鍵 | refresh token 的 **`jti`**（`JwtTokenService.build` 已為每個 token 簽發 `.id(UUID)`；`TokenIssuer.RefreshIdentity` 加 `tokenId`、`expiresAt` 兩欄）。名單只存「已撤銷的 `jti`」，不存 token 本身。沒有 `jti` 的 refresh token（理論上只可能來自更早的程式版本）視為無效，401 `INVALID_REFRESH_TOKEN`，使用者重新登入即可 |
| 存活時間 | 到該 token 的 `exp` 為止（`max(exp − 現在, 1 秒)`）：過了 `exp` 的 token 本來就被拒（`EXPIRED`），不必再記 |
| 何時撤銷 | ①**換新**：`POST /auth/refresh` 驗證簽章、用途與期限通過後，先 `tryRevoke(tokenId)`——原子操作，回 false＝已被撤銷（登出過，或另一個併發換新搶先）→ 401 `INVALID_REFRESH_TOKEN`；回 true 才查帳號並簽發新的一對。②**登出**：`POST /auth/logout`（§1.9.1） |
| 撤銷後的行為 | 以被撤銷的 refresh token 呼叫 `POST /auth/refresh` → **401**，`reason=INVALID_REFRESH_TOKEN`（與其他無效 refresh token 同一個 reason，不另立常數）；客戶端分類為 `invalid` → 清 session、導向登入（§2.8）。被撤銷的 refresh token 若被當 Bearer 用，依舊是 401 `TOKEN_INVALID`（refresh token 本來就不能當 access 用，與撤銷無關） |
| 併發換新 | 同一個 refresh token 的兩個併發 `refresh`，**只有一個成功**（`tryRevoke` 原子：Redis `SET key 1 NX EX ttl`；記憶體 `putIfAbsent`）。前端的換新是單飛行（`doRefresh` 共用同一個進行中的換新，§2.8），正常使用不會觸發；多個分頁各有自己的 session（`sessionStorage`），不共用 token |
| 儲存 | **Redis 優先**：鍵 `console:revoked-refresh:<jti>`、值 `1`、TTL 如上。**Redis 不在線**（連線失敗、逾時、任何 `DataAccessException`）時**降級為單實例記憶體名單**（`ConcurrentHashMap<jti, 到期時間>`；讀取時惰性清除、每 10 分鐘掃描一次），並記 **WARN**——只在狀態轉換時記（進入降級一次、恢復一次〔INFO〕），不在每次呼叫都記，免得 Redis 掛掉時日誌被灌爆。降級期間在記憶體撤銷的 `jti` 只對該實例有效，Redis 恢復後**不回補到 Redis**（記憶體名單繼續查到自己的 `exp`）。Console 目前是單實例部署（Architecture §2），這個限制可接受；多實例前須改成只認 Redis |
| 選用方式 | `console.security.refresh-revocation.store`：`auto`（預設；`spring.data.redis.host` 有值才用 Redis，否則純記憶體，本機開發不必起 Redis）、`redis`、`memory`（附錄 D.2）。`SPRING_DATA_REDIS_HOST`／`_PORT` 因此是**選填**環境變數（附錄 D.2、Architecture §9.4） |
| 健康檢查 | **必須**設 `management.health.redis.enabled=false`：Spring Boot 在 classpath 有 Redis 時會自動註冊 Redis 健康指標，Redis 不在線會讓 `/actuator/health` 變 DOWN，進而讓 backend 容器 unhealthy——正好違背「Redis 不在線仍可用」的降級承諾（ADR-001 D16） |
| 不在名單內的 | **限流計數**（Bucket4j 記憶體實作，§0.4 第 4 點）與 **SSE 位移**（存 DB 的 `console_last_seq`，§0.5 V7）維持現狀，**不使用 Redis**（ADR-001 D16 如實登記）；Bridge 探測環形緩衝也在記憶體（`BridgeHealthMonitor`） |
| 已知限制 | ①換新回應在網路上遺失時，客戶端以舊 token 重試會得到 401 而被登出（舊 token 已撤銷）；access token 約 30 分鐘才換新一次，機率很低，且「重放寬限窗」會讓被竊的 token 在窗內可重放、也要多一份狀態，所以不做寬限。②記憶體名單隨行程重啟清空：重啟前已登出、尚未過期的 refresh token 在重啟後復活（Redis 在線時不會）——這是降級的代價，登記於 ADR-001 D23 |

**驗收**：`AuthApiIT`（降級以丟 `RedisConnectionFailureException` 的替身驗，不需真 Redis）：①換新一次後，用舊 refresh token 再換新 → 401 `INVALID_REFRESH_TOKEN`，新 token 可用；②登出後，被登出的 refresh token 換新 → 401；③登出垃圾字串、過期 token、access token → 皆 204；④同一個 refresh token 兩個併發換新 → 一個 200、一個 401；⑤Redis 替身拋例外 → 撤銷與查詢退到記憶體、仍得到正確結果、只記一次 WARN，恢復後記一次 INFO；⑥`/actuator/health` 在 Redis 替身不可用時仍為 UP；E2E-16 第 5～6 列。

### 1.10 SDD 整合迴圈（v1.5；整合輪 115；已與 ADR-XPLAT-016 對齊）

本節是 v1.5 的 console-api 契約：一條從「在 SDD 下凍結規格」到「批次執行、FSM 同步、追溯覆蓋」的迴圈，Console 負責其中的人工閘（核准凍結）、路徑 A 匯入（既有，補欄位並可併入既有專案）、SDD 批次、追溯與觀測。Bridge 與 SDD 側的行為見 §3.1.4～§3.1.7。環境契約、CLI 動詞與 rc、摘要、權杖、預檢、委派同步與最小侵入白名單的**完整規格**以 ADR-XPLAT-016（下稱 ADR-016，Proposed）為唯一真相源；本節只寫 HTTP 面的欄位、錯誤與對映，並在需要機械斷言處逐字引用 ADR 的值（引用處標 ADR 節次）。判準對照：整合輪 115 §2 的 C1～C6。

#### 1.10.1 迴圈總覽（誰在哪一步做什麼）

| 段 | 動作 | 執行者 | 端點／動詞 | FSM `current_state` 的變化 |
|----|------|--------|------------|----------------------------|
| S1 | 建立 Console 專案：`executionPath`＝SDD 專案根；FSM 專案預設＝專案名（§1.10.5） | Console | Phase 2 `POST /projects` | 無 |
| S2 | 在專案根的 SDD session 建 FSM 專案、跑 SCG-0～3 到人工確認點（`SDD_STATE_DIR=<executionPath>/build/reports/fsm`、`SDD_PROJECT`＝專案名或其淨化鍵；Console 不提供，§6.8.6 登記延後） | SDD session（人或 AI） | SDD CLI | `INIT`→…→`HUMAN_PENDING` |
| S3 | **人工核准凍結** | Console（OPERATOR 以上） | `POST /projects/{id}/sdd/freeze`（§1.10.2）→ Bridge `:freeze` | `HUMAN_PENDING`→`SPEC_FROZEN` |
| S4 | 路徑 A 匯入並**併入同一個專案**：編譯凍結規格→草稿→signoff→confirm | Console | `parse`（帶 `targetProjectId`）→…→`confirm`（§1.10.8、§3.3.2） | 無（只唯讀檢查凍結與摘要） |
| S5 | 執行 SDD 批次 | Console → Bridge | `POST /projects/{id}/execute`（§1.10.6）→ `POST /autoclaude/runs`＋`sdd`（§3.1.6） | `SPEC_FROZEN`→（談判）→`IMPLEMENTATION`→`AUTOCLAUDE_DELEGATED`（`TEST_CONTRACT_NEGOTIATED` 自癒與 `AUTOCLAUDE_DELEGATED` 回收點見 §3.1.6） |
| S6 | 批次結束 | Bridge（自動） | — | `COMPLETED`／`CANCELLED`→`IMPLEMENTATION`；引擎升級型 `FAILED`→`ESCALATION`；其餘終態與 `PAUSED` 不動 |
| S7 | 追溯覆蓋 | Console | `GET /executions/{runId}/rtm`（§1.10.3） | 無 |
| S8 | 觀測 | Console | `GET /engines/sdd?projectId=`（§1.10.4） | 無 |
| S9 | 失敗後恢復 | **人，在 SDD session**（Console 只顯示 `ESCALATION`、`escalationProvenance` 與可複製的恢復指令；沒有恢復動詞） | `resume-from-escalation` | `ESCALATION`→`IMPLEMENTATION` |

**Console 專案是錨（D-115-14；ADR-016 §7.2）**：綁定＝專案的 `executionPath`（狀態目錄根＝`<executionPath>/build/reports/fsm`；**只有 Bridge 對 CLI 子行程設定 `SDD_STATE_DIR`**）加 `sddProject`（FSM 專案鍵，預設＝專案名）。因此**不存在「未綁定」狀態**：核准凍結的請求沒有 `binding` 欄、也沒有 `sdd_not_bound`；「先凍結才能匯入、先有專案才能凍結」的循環依賴由「專案先建、匯入併入它」解開，不再需要佔位專案。一個 FSM 專案只對應一個未刪除的 Console 專案（部分唯一索引，§0.5 V12）。

#### 1.10.2 `POST /api/v1/projects/{id}/sdd/freeze`　核准凍結（人工閘；v1.5，D-115-03）　〔API-SGN-06、API-PRJ-07／PRD §0.4〕

- **角色**：OPERATOR 以上（與 `POST /projects/{id}/signoff` 同級；VIEWER → 403 `ACCESS_DENIED`）。**Bridge**：唯讀 `GET /sdd/fsm/{project}?root=`（取標準鍵）與 `POST /sdd/fsm/{project}:freeze`（§3.1.4；後者帶 `X-Bridge-Token`，逾時 2 秒／40 秒、不重試）。
- **為什麼有它**：PRD §0.4 把 Console 的 signoff 對映 FSM 的 `HUMAN_PENDING`。v1.4 以前 Console 對 FSM 只讀（ADR-001 D22）；v1.5（D-115-01、D-115-03）只新開這一個人工閘寫入動詞：`HUMAN_PENDING`→`SPEC_FROZEN`，帶 approver、理由與文件摘要。退回修改、init、gate、恢復一律留在 SDD session（§6.8.6 延後格）。
- **Request**（`SddFreezeRequest`；**沒有 `binding` 欄**，D-115-14）：

| 欄位 | 型別 | 必填 | 規則 |
|------|------|:----:|------|
| `reason` | string | ✅ | 去前後空白後 1～500 字元，不含控制字元（含換行）；**不靜默截斷、不替換**，違反即 400（Bridge 同規則，違反回 422 `sdd_invalid_argument`；ADR-016 §4.4） |
| `stage` | string | — | `^[A-Za-z0-9._-]{1,64}$`；省略 → Bridge 以 `Stage-<n>`（`n`＝`frozen_stages` 筆數＋1）。階段名不要求唯一（ADR-016 §4.4） |
| `docs` | string[] | 條件 | 1～20 項；每項是**相對專案 `executionPath`** 的 POSIX 路徑（不得為絕對路徑、不得含 `..`）。省略＝`[sddSpecFile 換算成相對 executionPath 的路徑]`（專案已有 `sddSpecFile` 時）；省略而專案沒有 `sddSpecFile`、或規格檔不在 `executionPath` 之下 → 400（`errors[0].field=docs`）；專案已有 `sddSpecFile` 而 `docs` 不含它 → 400（同欄位）。**須含至少一份 TCS**（檔名符合 `TEST-CONTRACT-SPEC-*` 或 `TCS-*`），由 Bridge 判定（ADR-016 §6.3 ①） |
| `expectedDigests` | object | — | `{<docs 內的相對路徑>: "sha256:<64 位小寫 hex>"}`：核准人當時看到的摘要。有帶＝Bridge 逐一與現檔比對，不符 → 409 `sdd_spec_digest_changed`（`details.pair=expected_vs_file`；防「核准人看的版本不是現在要凍結的版本」，ADR-016 §6.3 ①）。鍵必須都在 `docs` 內，否則 400（`errors[0].field=expectedDigests`）。**v1.5 的畫面不送這欄**（沒有顯示規格摘要的元件）；保留給 API 消費者（§6.8.6 靜默處 #2） |

  approver **不在請求內**：一律取 JWT subject（人工 signoff 不可匿名，也不可由 client 指定）；Bridge 要求 1～100 字元、無控制字元、不含 `;`（違反回 422 `sdd_invalid_argument`，Console 轉成 422 `引擎拒絕此請求`）。

- **驗證順序**（固定，QA 依序斷言）：

| # | 檢查 | HTTP | reason | details |
|---|------|------|--------|---------|
| 1 | 專案存在且未軟刪除 | 404 | （訊息）`專案不存在或已刪除：<id>` | — |
| 2 | Bean Validation（`reason`／`stage`／`docs`／`expectedDigests` 的格式；缺 `docs` 又無規格檔；`docs` 不含已綁定的規格檔） | 400 | （無） | `errors[]` |
| 3 | backend 沒有設定寫入權杖 | 503 | `sdd_write_disabled` | — |
| 4 | **唯讀** `GET /sdd/fsm/{有效 FSM 專案}?root=<executionPath>` 取回標準鍵 `fsm_project`（有效值見 §1.10.5）；失敗依下表對映 | — | — | — |
| 5 | **綁定唯一性與寫回**：以標準鍵查 `(executionPath, sddProject)` 在未軟刪除的其他專案是否已被綁定；通過後，專案的 `sddProject` 為 NULL 時**寫入標準鍵**（獨立短交易，**先於** Bridge 的寫入呼叫） | 409 | `sdd_binding_conflict` | `{cause:"already_bound_elsewhere", sddProject, holderProjectId}` |
| 6 | 呼叫 Bridge `:freeze`；失敗依下表對映 | — | — | — |

  第 5 項的次序是 ADR-016 §7.2 的設計：衝突要在**任何 Bridge 寫入呼叫之前**發現，以免 FSM 已被寫入才發現兩個 Console 專案認領同一個 FSM 專案；寫回發生在「這個鍵真的有狀態檔」（第 4 項）被確認之後，所以填錯的名字不會留下綁定。第 6 項之後失敗**不回滾**第 5 項的寫回（鍵確實有狀態檔，綁定本身是對的）。

- **Bridge 失敗對映**（第 4、6 項）：

| Bridge 回應 | Console 回應 |
|-------------|--------------|
| 409 `fsm_state_conflict`（`detail.current_state` 不是 `HUMAN_PENDING`，含已凍結） | **409** `sdd_fsm_state_conflict`，`details={currentState, expectedState:"HUMAN_PENDING"}` |
| 404 `fsm_not_found`（第 4 項的 GET，或 CLI rc 5 `state_not_found`） | **409** `sdd_fsm_not_found`，`details={sddProject}`（送出的有效 FSM 專案名）——狀態檔要先在 `executionPath` 的 SDD session 建立（CLI 恆帶 `--must-exist`，ADR-016 §3.5） |
| 409 `spec_digest_changed`（`detail.pair=expected_vs_file`） | **409** `sdd_spec_digest_changed`，`details={pair, doc, expectedDigest, currentDigest}` |
| 422 `fsm_state_unreadable`／`sanitization_failed`／`sdd_invalid_argument`（`root`、`docs[i]` 不合法或缺檔或跑出根目錄、`docs` 不含 TCS、`approver`／`reason` 不合） | **422** `引擎拒絕此請求`，`details={bridgeReason, violations[]}`（Bridge 沒給 `violations` 時為 `[]`，並加 `details.detail`＝Bridge 的 `detail` 文字） |
| 503 `sdd_write_disabled`（Bridge 沒設權杖） | **503** `sdd_write_disabled` |
| 403 `sdd_write_forbidden`（權杖不符＝兩端設定不一致） | **502** `引擎橋接服務錯誤`，`details={bridgeStatus:403, bridgeReason:"sdd_write_forbidden"}`；另記 ERROR 日誌（設定缺陷，不是使用者錯誤） |
| 500 `sdd_cli_usage`、502 `sdd_cli_failed`、504 `sdd_cli_timeout`、其餘 5xx | **502** `引擎橋接服務錯誤`，`details={bridgeStatus, bridgeReason}` |
| 連線失敗／讀取逾時 | **502**／**504**（§3.2） |

- **成功 200**：`ApiResult<SddFsmState>`——與 `GET /engines/sdd` 的 `fsm` 同形（凍結後的狀態：`currentState="SPEC_FROZEN"`、`frozenStages` 多一筆，含 `spec_doc_digests`、`approved_by`）。
- **稽核與 FSM 側對上**（C2）：沿用 §0.4 第 5 點，每個請求一列 `audit_log`，`action=project.sdd.freeze`、`entity=project:<id>`、`http_status` 記結果，`subject`＝approver。FSM 檔 `decision_trace` 末筆（`trigger=spec_frozen`、`to=SPEC_FROZEN`）的 `reason` 固定為 `console-freeze approver=<approver>; reason=<使用者理由>`，`spec_refs`＝正規化後的 `docs`；`frozen_stages[-1].approved_by`＝approver（ADR-016 §4.3、§4.4）。Bridge 稽核事件 `sdd_write`（`verb=spec-frozen`、`project`、`approver`、`result`、`trace_id`〔取自 `X-Trace-Id`，沒有則省略〕；不含權杖，ADR-016 §9）。三處以「approver＋traceId＋時間」互相對上。
- **非冪等**：第二次呼叫（FSM 已不在 `HUMAN_PENDING`）→ 409 `sdd_fsm_state_conflict`。
- **文件摘要**：`frozen_stages[-1].spec_doc_digests` 是映射 `{<相對 root 的 POSIX 路徑>: "sha256:<64 位小寫 hex>"}`；演算法＝**換行正規化後的 UTF-8 文字**（`\r\n`、`\r`→`\n`，BOM 不剝）的 sha256，與 adapter 的 `SddSpec.digest` 逐位元相同，**不是**原始 bytes（CRLF 檔會假性不符）；非 UTF-8 的檔不能凍結，單檔上限 16 MiB（ADR-016 §4.3）。Console 不解讀，原樣出現在 `GET /engines/sdd` 的 `frozenStages`。
- 前端：§4.7.1。

#### 1.10.3 `GET /api/v1/executions/{runId}/rtm`　執行追溯覆蓋（諮詢視圖；v1.5，G-05）　〔API-EXE-16〕

- **角色**：VIEWER 以上。**Bridge**：`GET /autoclaude/runs/{id}/rtm`（§3.1.4；逾時 2 秒／3 秒、不重試）。
- **為什麼有它**：A 軌逆向回寫（`RtmWritebackPlugin`）把每個 SDD 批次的 AT／AC 覆蓋寫成 `RTM-COVERAGE-*.yaml`，v1.4 以前沒有任何讀者（`rtm_coverage` 欄恆 null）。本端點是 Console 對它的唯一消費點。**諮詢視圖**：「AT 通過」只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘，所以回應恆帶 `advisory:true`，前端必須標示（§4.7.2）。
- **成功 200**：`ApiResult<ExecutionRtmResponse>`（來源＝Bridge 同名欄位，鍵轉 camelCase，值原樣）：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `scenario` | string | 場景（缺則 `""`） |
| `specDigest` | string | 編譯規格的摘要（`sha256:<hex>`；缺則 `""`） |
| `at` | `{passed, total, unmapped, pct}` | AT 通過數／總數／**無法歸屬 AC 的個數**／百分比（0～100，1 位小數）。`total`、`passed` **含**無法歸屬者（ADR-016 §8.5：AT 級指標不假裝它不存在）；`unmapped`＝YAML `summary.unmapped_at`，舊報告缺欄為 0 |
| `ac` | `{covered, total, pct}` | AC 覆蓋數／總數／百分比（同上）；無法歸屬的 AT **不進**任何 AC 桶 |
| `failedAtIds` | string[] | 未通過的 AT（Bridge 已排序；沒有為 `[]`；含無法歸屬者） |
| `weakRegexAtIds` | string[] | 驗收 regex 偏弱（轉譯保真度警訊）的 AT（同上） |
| `unmappedAtIds` | string[] | **逆向還原後無法歸屬 AC 的 AT**（YAML 頂層 `unmapped_at_ids`，已排序；舊報告缺欄為 `[]`）。注意：這與 `POST /sdd/compile` 回應的同名 `unmapped_at_ids`（規格出現卻沒編成步驟）是**兩個不同層的欄位**，不得混用（ADR-016 §8.2） |
| `fullyCovered` | boolean | `ac.total>0` 且 AC 全數覆蓋，**且 `unmappedAtIds` 為空**——有無法歸屬的 AT 時恆為 `false`（ADR-016 §8.5；SCG-5 的機器判斷，仍是諮詢） |
| `advisory` | boolean | **恆為 `true`** |

- **錯誤**：

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （訊息）`參數 runId 的值格式不正確` | | runId 不是 UUID |
| 404 | （訊息）`執行批次不存在或已刪除：<id>`；**無 reason** | | 資料庫沒有這個批次 |
| 404 | `rtm_not_found` | `{runId}` | 批次存在但沒有報告：沒有啟用 SDD 治理的批次、批次尚未結束、批次不是正常走完（引擎只在 run 正常走完時才寫報告，`FAILED`／`CANCELLED`／額度停機都沒有）、工作區已清除（Bridge 404 `run_not_found`）、或 Bridge 404 `rtm_not_found`（D-115-16：維持 404，不改 200 加旗標） |
| 422 | `引擎拒絕此請求` | `{bridgeReason:"rtm_unreadable", violations:[]}` | 報告檔存在但 YAML 壞掉或缺 `summary` |
| 502／504 | 通用 | | Bridge 失敗 |
| 401／429 | 通用 | | |

- **邊界**：①有無法歸屬的 AT 時，`at.total` 與 `ac` 的分母口徑不同（前者含、後者不含），前端不得拿 `at.total` 去除 `ac.total` 之類互推；②不輪詢、不快取：前端在批次進入終態後取一次（§4.7.2）。

#### 1.10.4 `GET /api/v1/engines/sdd` 的 v1.5 變更（D-115-02；G-07、G-13）　〔API-ENG-02〕

- **新增選填查詢參數**：

| 參數 | 型別 | 規則 |
|------|------|------|
| `projectId` | uuid | 帶了＝讀「該專案」的 FSM：`root`＝該專案的 `executionPath`。專案不存在或已軟刪除 → **404**（訊息 `專案不存在或已刪除：<id>`，無 reason）；格式不合 → 400（`errors[0].field=projectId`）。省略＝v1.4 行為（讀 Bridge 預設的狀態目錄），完全不變 |
| `project` | string | 取代 v1.4 的 `^[A-Za-z0-9._-]{1,128}$`：1～200 字元（專案名上限）、不含控制字元（U+0000～U+001F、U+007F），不合 → 400（`errors[0].field=project`）。**Console 不淨化、不檢查 Windows 禁用字元**：值原樣交給 Bridge，由 Bridge 的淨化鏡像處理（§3.1.4 (b)；ADR-016 §7.2、§7.4）。帶了 `projectId` 而省略 `project` 時，預設取**有效 FSM 專案**（§1.10.5：`sddProject` 有值取它，否則專案名） |

- **呼叫 Bridge**：同 v1.4 的依序短路規則，但 `GET /sdd/fsm` 與 `GET /sdd/fsm/{project}` 帶 `root=<executionPath>`（§3.1.4）；`GET /sdd/version` 不帶。
- **回應新增**（皆選填；舊 Bridge 缺欄時一律補預設，不得失敗）：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `fsm.phase` | `SddFsmPhase`｜null | 階段資訊（定義與對映表見 §3.1.5） |
| `fsm.escalationHistory` | object[] | **尾 5 筆**、舊→新、原樣——保留 FSM 檔的 snake_case 鍵，例 `triggered_at`、`trigger_reason`、`resolved_at`、`resolution`、`source`；缺則 `[]` |
| `fsm.escalationProvenance` | object｜null | FSM 檔的 `escalation_provenance` 原樣（例 `{rule_id, source, reason, …}`；`source="autoclaude_delegated_failed"` 即「委派失敗進入 ESCALATION」）；缺則 null。🔴 恢復後它**不會被清除**，所以「現在有沒有未解的委派失敗」只能由 `currentState` 與 `escalationHistory` 末筆判斷（§4.7.3；ADR-016 §5.3） |
| `fsm.fsmProject` | string｜null | 狀態檔名裡**淨化後的標準鍵**（`FSM-STATE-<鍵>.yaml` 的 `<鍵>`）；現有的 `fsm.project` 是檔內的原名，兩者可能不同，**不能拿 `project` 當鍵**（ADR-016 §7.2）；缺則 null |
| `fsm.recovery` | `{target, powershell, posix}`｜null | **僅 `currentState` 為 `ESCALATION`／`ESCALATION_FINAL` 時由 Bridge 回**（其餘狀態缺席或 null）：`target`＝建議的 `--to`（委派失敗＝`IMPLEMENTATION`）、`powershell`／`posix`＝可複製的 `resume-from-escalation` 指令（ADR-016 §5.3 模板；只含路徑與指令，理由欄位留 `<人工原因>` 佔位，**不含任何機密**）。Console 原樣顯示，不得自行組字或猜測目標；Bridge 無法判定目標時整個省略（§6.8.6 靜默處 #5） |

  `frozenStages[]` 的項目自 v1.5 起可含 `spec_doc_digests`、`approved_by`（形狀見 §1.10.2；Console 原樣帶出、不解讀）。`rtmCoverage` 維持保留位（現況恆 null）；單一批次的覆蓋改看 §1.10.3。
- **`reason` 新值 `sdd_root_rejected`**（回應欄位，附錄 B.4）：帶了 `projectId`，而 Bridge 對 `root` 回 422 `sanitization_failed`（專案路徑不在 `BRIDGE_ALLOWED_PATH_ROOTS` 內、或已不存在）→ 200、`available=true`、`projects=[]`、`fsm=null`、`reason="sdd_root_rejected"`（`version` 保留）。專案根目錄存在但還沒有 `build/reports/fsm` **不是錯誤**：`projects=[]`、`reason=null`（卡片顯示「尚無 FSM 狀態檔」）。
- **舊 Bridge 相容**：Bridge 回應缺 `phase`／`escalation_history`／`escalation_provenance`／`fsm_project`／`recovery` 時，Backend 補 `phase=null`、`escalationHistory=[]`、其餘 null，不得因此失敗。

#### 1.10.5 專案的 SDD 綁定欄位、有效值與批次資格（v1.5，G-07、D-115-14）　〔API-PRJ-07〕

- **欄位**：`ProjectResponse`（confirm 的回傳）與 `ProjectDetailResponse`（詳情與 restore 的回傳）新增 `sddProject`、`sddSpecDir`、`sddSpecFile`（皆 string｜null，null 與缺席等價，§0.2；`ProjectSummaryResponse` 不帶）。語意：

| 欄位 | 語意 | 寫入點 |
|------|------|--------|
| `sddProject` | FSM 專案鍵（≤ 100 字元）；**NULL＝「用預設」**（專案名）。存的是標準鍵（第一次使用時寫回）或使用者在 §1.10.7 輸入的值 | 核准凍結第 5 項、路徑 A confirm、`PUT /projects/{id}/sdd-binding` |
| `sddSpecDir` | 規格檔所在目錄（絕對路徑）＝編譯回應 `spec_path` 的父目錄 | 只有路徑 A 的 confirm |
| `sddSpecFile` | 規格檔（絕對路徑）＝編譯回應的 `spec_path`（ADR-016 §7.2）；後續批次據此**精確指到那份 TCS**，之後多一份 TCS 也不會變歧義 | 只有路徑 A 的 confirm |

- **有效 FSM 專案**：`sddProject` 有值時取它，否則取**專案名**。**Backend 不自行淨化**（淨化鏡像只有 Bridge 有）：一律把「有效值（可以是原名）」交給 Bridge，Bridge 回應帶淨化後的標準鍵 `fsm_project`。
- **寫回（固定專案鍵）**：在**第一次使用**時——核准凍結（§1.10.2 第 5 項）、路徑 A 的 confirm 落庫時——Backend 把 Bridge 回的標準鍵寫進 `sddProject`（原為 NULL 時）。此後專案改名不會讓綁定悄悄移到另一個 FSM 專案。
- **唯一性**：`(executionPath, sddProject)` 在**未軟刪除且 `sddProject` 非空**的列中唯一（部分唯一索引，§0.5 V12）；衝突 → 409 `sdd_binding_conflict`。Backend 一律「先檢查、後寫入」（核准凍結第 5 項在任何 Bridge 寫入之前；confirm 在落庫交易內）；索引是最後的兜底。
- **SDD 批次資格**（execute 判定；以本批次「範圍內」任務為準，**全部成立**才送 `sdd` 區塊，任一不成立＝不送、走既有的 `G<g>-T<t>` 路徑並依 §1.10.6 出聲）：

| # | 條件 | 不成立的 `cause` |
|---|------|------------------|
| 1 | 專案已有規格綁定（`sddSpecDir` 非空，亦即已用路徑 A 匯入過規格；ADR-016 §7.2） | `not_bound` |
| 2 | backend 已設定寫入權杖 | `token_not_configured` |
| 3 | 範圍內每個任務的 `passCriteriaSpec.source` 都是 `sdd`，且 `stepId`、`specDigest` 皆為非空字串 | `mixed_scope` |
| 4 | 範圍內所有任務的 `specDigest` 相等（同一份規格） | `spec_mismatch` |
| 5 | 範圍內各任務的 `stepId` 互不相同 | `duplicate_step_id` |

#### 1.10.6 `POST /api/v1/projects/{projectId}/execute` 的 SDD 批次（v1.5；D-115-06）　〔API-EXE-15〕

- **請求不變**（`StartExecutionRequest` 沒有任何新欄位；SDD 治理是否啟用由資格判定決定，不由 client 指定）。
- **資格成立時**，Bridge 請求（§3.4.1 的 v1.5 補充）多一個頂層 `sdd`：`{ "spec_dir": <sddSpecDir>, "spec_file": <sddSpecFile，沒有則省略>, "fsm_project": <有效 FSM 專案>, "root": <專案 executionPath>, "approver": <簽核人> }`。`approver`＝範圍內 SDD 來源任務的 `signedOffBy`（承襲匯入記錄的核准人；多個值時取排序最前任務的值）；為空時取觸發 execute 的 JWT subject，所以 **Backend 永遠送具名人**（ADR-016 §5.2 C-1；Bridge 端此欄選填、省略時記 `console`）。
- **201 的 `warnings[]`**（`ExecutionWarning{code, cause?, detail}`；選填，缺席＝沒有警告）：

| `code` | `cause` | 意思 |
|--------|---------|------|
| `sdd_governance_inactive` | `not_bound`／`token_not_configured`／`mixed_scope`／`spec_mismatch`／`duplicate_step_id`（§1.10.5） | 本批次**沒有**啟用 SDD 治理：沒有預檢、沒有 FSM 同步、step_id 維持 `G<g>-T<t>`、事後也不會有追溯報告；`detail` 是給人看的中文說明。只有「範圍內至少有一個 SDD 來源任務（`passCriteriaSpec.source=sdd`）」才出聲；沒有任何 SDD 來源任務的批次不帶 |
| `sdd_frozen_digest_absent` | （無） | 本批次已啟用 SDD 治理，但凍結時沒有記錄內容摘要（舊狀態檔，或以舊版 CLI 凍結）：放行但**無法偵測凍結後改檔**，`detail` 說明（Bridge 回的 201 `warnings` 原樣轉入；ADR-016 §6.3 ③） |

  **只有 execute 的 201 帶 `warnings`**。沒有警告時維持 v1.4 的回應形狀。
- **失敗**：見 §1.2.1 的 v1.5 加註與 §3.2；補償刪除規則不變。
- **後續批次**（審核 `SKIP`／`RETRY` 開的後續批次）走同一條建立路徑：同樣依資格送 `sdd`、同樣預檢。這些端點回 204（無本文），`warnings` 只寫 console-api 日誌（WARN），不回前端。FSM 若停在 `ESCALATION`（引擎升級型失敗後的常態）或被外來委派佔用，後續批次會被 409 `sdd_fsm_state_conflict` 擋下，審核決定隨之失敗（原子性規則見 §1.2.11），須先在 SDD session 恢復 FSM（§3.1.7 第 1 點）。
- **`resume`／`restore`**：SDD 批次的 `resume`／`restore` 由 Bridge **重跑預檢**（§3.1.6 第 7 點）：內容摘要重驗與 FSM 前置檢查。額外的失敗回應見 §1.2.4～§1.2.6 與 §1.2.10 的 v1.5 加註；Console 的 DB 預檢不變。

#### 1.10.7 `PUT /api/v1/projects/{id}/sdd-binding`　編輯專案的 FSM 專案（v1.5；ADR-016 §7.2「可編輯」「改綁」）　〔API-PRJ-08〕

- **角色**：OPERATOR 以上。**Bridge**：無。**為什麼有它**：ADR-016 §7.2 規定 `sdd_project` 可由使用者編輯（自由輸入、Bridge 淨化後生效），且沒有「解除綁定」端點——編輯它即改綁；而 Phase 1+2 的專案更新端點不在本契約範圍，所以另開這個窄端點（§6.8.6 靜默處 #1，需主控確認）。
- **Request**（`SddBindingRequest`）：`{ "sddProject": "<名稱>" | null }`。非 null 時：去前後空白後 1～100 字元、無控制字元；`null`＝清除，回到「用預設」（專案名）。
- **處理**：存入去空白後的值，**不檢查狀態檔是否存在**、**不呼叫 Bridge**（填錯的名字只會讓 `GET /engines/sdd` 回 `fsm_not_found`，不留下寫入）；先檢查唯一性（同 §1.10.5），衝突 → 409。相同值再送＝冪等（200，不寫稽核）。改綁**不搬移** FSM 狀態檔，也不影響進行中的批次（終態同步用 run 建立時存下的專案鍵，§3.1.6）。
- **成功 200**：`ApiResult<ProjectDetailResponse>`。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （Bean Validation） | `errors[0].field=sddProject` | 空白、過長或含控制字元 |
| 404 | （訊息）`專案不存在或已刪除：<id>` | | |
| 409 | `sdd_binding_conflict` | `{cause:"already_bound_elsewhere", sddProject, holderProjectId}` | 同 `executionPath` 已有未刪除的專案以同一個 `sddProject` 綁定 |
| 401／403／429 | 通用 | | VIEWER → 403 `ACCESS_DENIED` |

- 稽核：沿用 §0.4 第 5 點，`action=project.sdd.bind`、`entity=project:<id>`。前端：§4.7.1。

#### 1.10.8 路徑 A 匯入併入既有專案（`targetProjectId`；v1.5，D-115-14）　〔API-IMP-12〕

- **為什麼有它**：解開「先凍結、後匯入」的循環依賴（§1.10.1）。`ParseOptions` 新增選填 `targetProjectId`（uuid；見 §3.3.2 的 v1.5 補充）。
- **帶 `targetProjectId`**：
  - **parse**：目標專案須存在且未軟刪除，否則 404（訊息 `專案不存在或已刪除：<id>`）。`executionPath`、`sddProject`（有效值）、`specFile` **一律取自目標專案**；請求另帶不同值 → 409 `sdd_binding_conflict`（`details={cause:"request_differs_from_target", field}`）。`executionPath` 在 `ParseOptions` 仍是必填欄位：帶目標專案的值即可。目標專案某欄位為 NULL（尚未綁定規格檔）時，該欄位不受限，以請求值為準。
  - **confirm**：**不建立新專案**，把草稿的目標與任務**併入目標專案**，並回填 SDD 綁定：`sddSpecDir`／`sddSpecFile`（取自 `ParsedResult`，冪等更新）、`sddProject`（為 NULL 時寫入編譯回應的標準鍵）。專案已有不同的綁定——編譯回應的標準鍵與目標專案的 `sddProject`（或其預設淨化鍵）不同，或規格根不在目標專案的 `executionPath` 之下——→ 409 `sdd_binding_conflict`（`details={cause:"target_bound_differently", sddProject}`）。confirm 與 parse 各驗一次（兩次之間綁定可能被 §1.10.7 改掉）。成功仍回 **201** `ApiResult<ProjectResponse>`（目標專案；新建的是目標與任務，不是專案），匯入記錄的 `projectId`＝目標專案、`status=IMPORTED`。
  - **併入規則**（ADR-016 §7.2 把排序與編號交給本契約）：新目標加在目標專案**既有未刪目標之後**——新目標的 `sortOrder`＝既有未刪目標的最大 `sortOrder`＋1＋草稿內的序（從 0 起；沒有既有目標時從 0 起）；草稿內的 `dependsOn` 依 key 換成新建的目標 id，**不會產生指向既有目標的依賴**；專案本身的欄位（名稱、說明、`passCriteria`、自治等級、`executionPath`、簽核欄位）一律不動，草稿的 `project.*` 不採用；新建的目標與任務 `signedOff=true`，`signedOffBy／At` 承襲匯入記錄（同 confirm 既有規則）。**專案層的 `signedOff` 不動**：目標專案若尚未簽核，execute 的第 5 項（整案 signedOff 檢查）會擋下，須另以 Phase 2 的專案 signoff 簽核（匯入記錄的 signoff 只涵蓋它建立的目標與任務；§6.8.6 靜默處 #3）。
- **不帶 `targetProjectId`**：維持現行「建立新專案」，以 `ParseOptions.executionPath` 當專案的 `executionPath`，以編譯回應回填綁定；同一 `executionPath` 下已有未刪除專案綁定同一個標準鍵 → 409 `sdd_binding_conflict`（`details={cause:"already_bound_elsewhere", sddProject, holderProjectId}`；confirm 先檢查、唯一索引兜底）。
- **回填只在 confirm 成功落庫時做**，parse／預覽不回填——放棄的草稿不該產生綁定。

---
## 2. SSE 契約（`API-SSE-01～03`／`US-E-03、07`）

兩個端點：`GET /api/v1/stream/executions/{runId}/logs`（事件 `log`、`status-change`、`review-request`、`alert`）與 `GET /api/v1/stream/executions/{runId}/metrics`（事件 `metric-update`、`token-update`、`progress-update`）。console-api 的 `RunEventConsumer`（每個活躍 run 一條虛擬執行緒）讀 Bridge `GET /autoclaude/runs/{id}/stream?after=<seq>`，更新讀模型並扇出給前端訂閱者；Bridge 的 `seq` 是整個鏈路的序號基礎（Bridge 事件單調連續、重啟後延續，已由其測試鎖定）。

### 2.1 連線、認證與框架

| 項目 | 契約 |
|------|------|
| 角色 | VIEWER 以上 |
| 認證 | `Authorization: Bearer <access token>` 與 `?access_token=<access token>` **兩者皆收**（EventSource 不能帶標頭）；標頭優先；只收 access token（refresh token 一律 401）。無效／過期 → **401 JSON**（`UNAUTHENTICATED`／`TOKEN_EXPIRED`／`TOKEN_INVALID`，在串流開始前回；已開始的串流若 token 在中途過期**不中斷**，下次重連才驗） |
| 查無 run | 404 JSON（訊息 `執行批次不存在或已刪除：<id>`） |
| 回應標頭 | `Content-Type: text/event-stream;charset=UTF-8`、`Cache-Control: no-cache, no-store`、`X-Accel-Buffering: no` |
| 框架 | 第一個框架是 `retry`（3000）加空行；之後每個事件由 `id`、`event`、`data` 三個欄位加空行組成；`data` 為 UTF-8、不含換行的單行 JSON（`ensure_ascii=false` 的緊湊 JSON）。**欄位名後面的冒號之後是否跟一個空白不拘**（SSE 規格允許；Spring `SseEmitter` 實際輸出不帶空白：`retry:3000`、`id:41`、`event:log`、`data:{…}`、`:keep-alive`）。本文範例為了易讀寫成帶空白的形式；**QA 與前端一律以解析後的欄位（事件名、id、data JSON）斷言，不比對位元組字面**（AR-03）。後端用 `SseEmitter` 即可，不必為了湊字面去繞過它改寫原始框架 |
| keep-alive | 連續 **15 秒**沒有任何事件就送一行註解（內容為 `keep-alive`）加空行（任何事件都重置計時）；註解行的冒號後空白同樣不拘。**註解行對瀏覽器原生 `EventSource` 不可見**（它不觸發任何 JS 事件；F2-6），前端因此不能用它判斷「連線還活著」，改以批次詳情（`GET /executions/{runId}`）每 15 秒的保險輪詢兜底（`lib/api/queries.ts` 的 `EXECUTION_POLL_MS`；終態不輪詢）；keep-alive 的用途只是避免代理與瀏覽器因閒置切線 |
| 順序 | 依 `(seq, sub)` 升冪送出；Bridge 事件的 `sub` 視為 0 |
| 慢速訂閱者 | 每個連線有 1,000 個框架的送出佇列；佇列滿＝伺服器主動關閉該連線，客戶端以 `Last-Event-ID` 重連即補齊（不丟事件） |
| 代理 | nginx 的設定見 §0.7：`/api/v1/stream/` 須 `proxy_buffering off`、`proxy_http_version 1.1`、`proxy_read_timeout 3600s`，且 access log 要遮罩 `access_token`（owner＝W3-B2） |

**實作提醒：`SseEmitter` 完成時的 ASYNC dispatch（TBC-1，審查提出的待確認項，尚未實證）**：`SseEmitter` 完成（`complete()`）時，Servlet 容器會以 ASYNC dispatch 再走一次過濾鏈與授權；`JwtAuthenticationFilter` 是 `OncePerRequestFilter`（預設不處理 ASYNC dispatch），而 API 沒有 session，授權鏈在這次 dispatch 可能判成未認證，日誌出現 `AccessDeniedException`，進而違反 §5.0.4 的 A3（沒有未預期例外）。處置二選一：`SecurityConfig` 設 `dispatcherTypeMatchers(DispatcherType.ASYNC).permitAll()`；或讓 filter 覆寫 `shouldNotFilterAsyncDispatch()` 為 `false` 並在 ASYNC dispatch 沿用原請求的認證。W3-B2 交卷須貼「串流正常結束後，日誌沒有 AccessDenied 錯誤」的證據（§0.8 第 1 項）。

### 2.2 `id:` 規則

- **Bridge 事件**：`id` ＝ Bridge `seq`（正整數，例 `41`）。
- **console-api 自產的 `/logs` 事件**（`review-request`、Console 規則產生的 `alert`）：`id` ＝ `<seq>.<n>`，其中 `<seq>` ＝建立當下**已處理到的最後一則 Bridge 事件 seq**（錨點；尚未處理任何事件時為 `0`），`<n>` ≥ 1。同一個錨點下 `n` 依建立順序遞增。`/metrics` 的 id 規則（即時事件與收斂快照）另見 §2.6。
- **比較**：把 id 解析成數對 `(seq, n)`（無小數點者 `n=0`）做字典序比較。因此 `41` < `41.1` < `41.2` < `42`。
- **子序號配置**：`/logs` 串流的 `n` ＝「同 run 同錨點下，`review_requests` 與 `alerts` 兩表中 `event_sub` 的最大值＋1」（交易內計算，錨點與子序號寫入該列的 `event_seq`／`event_sub`，§0.5）。`/metrics` 的 id 是固定規則，不入庫，見 §2.6。
- **連線層的暫態告警**（`BRIDGE_UNREACHABLE`、`BRIDGE_RUN_UNKNOWN`，不持久化）**不帶 `id:` 行**（SSE 允許省略；瀏覽器的 last event id 不變），避免它與日後才配置的子序號撞號而被客戶端去重誤丟。
- **Bridge 告警事件的持久化鏡像**（ESCALATION／TOKEN_HALT 寫入 `alerts`）`event_sub=0`，**SSE 重播時不從 DB 再送一次**（Bridge 事件本身就會重播）。

### 2.3 `Last-Event-ID` 重播語意（at-least-once）

1. 連線時帶 `Last-Event-ID: <id>`（瀏覽器 EventSource 重連時自動帶；fetch 串流自行帶）→ 伺服器重播所有 `(seq, n)` **嚴格大於**該值的事件，再接即時事件。格式不合（不符 `^[0-9]+(\.[0-9]+)?$`）視為沒有帶，不回 400。
2. **`/logs` 重播來源**：Bridge 事件取自 Bridge `GET /autoclaude/runs/{id}/events?after=<seq>&limit=500`（逐頁；Bridge 記憶體環 5,000 則，更舊的自動掃 `events.jsonl`，所以任何歷史位置都可重播，Bridge 重啟後亦然）再套用 §2.7 的對映；Console 自產事件取自 `review_requests`／`alerts`（依 `event_seq`／`event_sub`，且 `event_sub ≥ 1`）。兩者合併後依 `(seq, n)` 排序。
3. **沒有 `Last-Event-ID` 時**（新開頁面）：`/logs` 先重播最後 `tail` 則事件（查詢參數，預設 200，0＝只收之後的新事件，上限 5,000）再接即時；`/metrics` 見 2.5。
4. **客戶端必須去重**：at-least-once 表示可能重複；客戶端記住已處理的最大 `(seq, n)`，小於等於者忽略。這條規則對 `/logs` 與 `/metrics` 一體適用，因為同一條串流的 id 保證**互異且嚴格遞增**（`/metrics` 的收斂快照三則 id 各不相同，§2.6）；`/logs` 與 `/metrics` 是兩條獨立的串流，客戶端各自記自己的最大 id。
5. **Bridge 暫時不可達**：串流**不關閉**，持續送 keep-alive，並送一則 `alert`（`origin=CONSOLE`、`code=BRIDGE_UNREACHABLE`、`severity=WARNING`、不持久化、同一次中斷只送一次）；每 5 秒重試，恢復後自動補齊。Bridge 回 404 `run_not_found` 則送一則 `alert`（`code=BRIDGE_RUN_UNKNOWN`、`WARNING`）後關閉。
6. **REST 回補**（不能或不想重播時）：`GET /executions/{runId}/steps?afterSeq=<id 整數部分>` 補步驟；`GET /executions/{runId}`（`pendingReviews`）補審核項；`GET …/alerts` 補告警。引擎原始 `log` 行無 REST 回補（只在 SSE 與 Bridge 的 events）。

### 2.4 終態、暫停與關閉

- `PAUSED` **不結束**串流（run 仍持鎖、可 resume）；`PAUSING`／`CANCELLING` 同。
- run 進入終態（`COMPLETED`／`FAILED`／`CANCELLED`）：先送該 `status-change`，再送完它之後衍生的事件（例如終態時才建立的 `review-request`），然後**關閉連線**。
- **重連一個已終態的 run**：`/logs` 若重播集合為空 → **HTTP 204**（EventSource 收到 204 不再重連；fetch 客戶端視為串流結束）；不為空 → 送完重播後關閉。`/metrics` 若帶的 `Last-Event-ID` 已 ≥ `<S>.3`（`S`＝終態 `status` 事件的 seq，`<S>.3` 是終態快照的最後一個 id，§2.6）→ 204，否則送終態快照（`<S>.1`、`<S>.2`、`<S>.3`）後關閉；沒有帶 `Last-Event-ID` 時同樣送終態快照後關閉。
- **restore 會讓終態 run 重新變回 `RUNNING`**：呼叫 restore 的客戶端須在 restore 回應之後**重新連線**（原連線早已因終態關閉）。

### 2.5 `/logs` 的事件

所有事件的 `data` 都含 `seq`（錨點或 Bridge seq，整數）與 `ts`（ISO-8601 帶 offset）。

#### `log`

`LogEventData`：`{ seq, ts, source, level, message, stepId?, stepNumber?, taskId?, taskName?, goalId?, attempt?, stepStatus?, tokensUsed? }`

| 欄位 | 說明 |
|------|------|
| `source` | `ENGINE`＝Bridge `log` 事件（引擎 stdout 一行，`message` 為原行，單則上限 8,000 字元由 Bridge 截斷並附註）；`STEP`＝由 Bridge `step` 事件衍生的摘要行 |
| `level` | `DEBUG`｜`INFO`｜`WARN`｜`ERROR`｜`CRITICAL`；ENGINE 取 Bridge `level`（`WARNING`→`WARN`）；STEP：`STARTED`／`COMPLETED`→`INFO`、`RETRYING`→`WARN`、`FAILED`→`ERROR` |
| `message`（STEP） | `STARTED` `開始：<任務名>（<stepId>，第 <attempt> 次）`；`RETRYING` `重試：<任務名>（<stepId>，第 <attempt> 次）`；`COMPLETED` `完成：<任務名>（<stepId>）`＋（有值時）` Token: <n>`；`FAILED` `失敗：<任務名>（<stepId>，第 <attempt> 次）：<errorMessage>` |
| `stepId`／`stepNumber`／`taskId`／`taskName`／`goalId`／`attempt`／`stepStatus` | STEP 一律帶（`stepNumber`＝步驟位置，1 起）；ENGINE 行若消費者已知目前步驟則帶 `stepId`／`taskId`，否則省略 |
| `tokensUsed` | 只有 STEP 的 `COMPLETED` 帶：該任務在本批次累計的 Token（歸因規則 §3.5.2） |

`FAILED` 的 `<errorMessage>` 取自 DB `execution_steps` 的 `FAILED` 列（由 Bridge 寫）：若該列比 `step` 事件晚到，**即時**框架可能暫缺錯誤文字（真 Bridge 實測未發生）；`/logs` 的重播與 `GET …/logs` 一定補得上（B2-5；`RunEventProcessor` 以 `steps.findLatest(runId, stepId, "FAILED")` 取值、`StreamService` 重播同一路徑）。

```
id: 17
event: log
data: {"seq":17,"ts":"2026-10-15T08:30:13.482+00:00","source":"STEP","level":"INFO","message":"開始：初始化（G1-T1，第 1 次）","stepId":"G1-T1","stepNumber":1,"taskId":"c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21","taskName":"初始化","goalId":"a1f4c2d3-5b6e-4c7d-8e9f-0a1b2c3d4e11","attempt":1,"stepStatus":"STARTED"}
```

#### `status-change`

`StatusChangeEventData`：`{ seq, ts, runStatus, bridgeStatus, reason }`。`runStatus` 為六態折疊值，`bridgeStatus` 為 Bridge 原值（`PAUSING`／`CANCELLING` 在此可見），`reason` 為 Bridge `reason` 原文（例 `在步驟邊界暫停（已完成 1 步，續跑點：G1-T2）`、`引擎升級（ESCALATION）：…`）。每次 Bridge `status` 事件都送一則（含 `INITIALIZING`）。

```
id: 41
event: status-change
data: {"seq":41,"ts":"2026-10-15T08:30:20.101+00:00","runStatus":"PAUSED","bridgeStatus":"PAUSED","reason":"在步驟邊界暫停（已完成 1 步，續跑點：G1-T2）"}
```

#### `review-request`

`ReviewRequestEventData`：`{ seq, sub, ts, review }`，`review` 為完整 `ReviewRequestResponse`（含 `allowedDecisions`）。`id` ＝ `<seq>.<sub>`（`sub ≥ 1`）。審核項建立時機見 §3.6；導覽列 Badge 以 `GET /notifications/summary` 為準，這個事件只用來即時刷新。

```
id: 41.1
event: review-request
data: {"seq":41,"sub":1,"ts":"2026-10-15T08:30:20.140+00:00","review":{"id":"f0b1c2d3-e4f5-4a6b-8c7d-9e0f1a2b3c41","runId":"e5a7c3b9-2f1d-4b6a-8c0e-1d2f3a4b5c31","kind":"TASK_CONFIRM","status":"PENDING","taskId":"c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c22","goalId":"a1f4c2d3-5b6e-4c7d-8e9f-0a1b2c3d4e11","taskName":"設定","goalName":"基礎","reason":"Level 1：請確認是否繼續執行任務「設定」","requestedAt":"2026-10-15T08:30:20Z","allowedDecisions":["APPROVE","REJECT"]}}
```

#### `alert`

`AlertEventData`：`{ seq, sub?, ts, origin, alertId?, rule?, code?, severity, subject?, message, stepId? }`。

| `origin` | id | 內容 |
|----------|----|------|
| `ENGINE` | `<seq>`（Bridge `alert` 事件） | `code`＝Bridge 的 `code`（`ESCALATION`、`TOKEN_HALT`、`LIMIT_RETRY`、`RESTORE`、`FORCE_KILL`、`CONFIG_OVERRIDE_IGNORED`、`STEP_TRACKING_GAP`、`ENV_LOST`、`BRIDGE_INTERNAL`…）；`severity`：`info→INFO`、`warning→WARNING`、`error→CRITICAL`；只有 `ESCALATION`、`TOKEN_HALT` 會持久化（規則 `ENGINE_ESCALATION`／`ENGINE_TOKEN_HALT`）；該事件**新增了一列**才帶 `alertId`／`rule`，被 §3.7 的「未確認前不重複產生」擋下者不帶（SSE 照常轉發） |
| `CONSOLE` | `<seq>.<sub>` | 六條 PRD 規則（§3.7）產生並持久化的告警，帶 `alertId`、`rule`、`subject`；或不持久化、**不帶 `id:` 行**的連線告警（`code=BRIDGE_UNREACHABLE`／`BRIDGE_RUN_UNKNOWN`；其 `seq` 為目前錨點、無 `sub`） |

### 2.6 `/metrics` 的事件（三者皆為狀態快照，latest-wins）

- **收斂快照**（AR-02）：不重播歷史；每次連線（不論有無 `Last-Event-ID`）伺服器**先依序各送一則最新快照**，三則的 id 互異且嚴格遞增：`progress-update`＝`<S>.1`、`token-update`＝`<S>.2`、`metric-update`＝`<S>.3`，其中 `S` ＝目前最後處理的 Bridge seq（尚未處理任何事件時 `S=0`），再接即時事件。這與「從 `Last-Event-ID` 之後重播」在語意上等價，因為客戶端只需要最新狀態（§6 D-32）。v1.0 把 `progress-update` 與 `token-update` 都標成 `<S>`，會讓客戶端「小於等於已見最大 id 者忽略」的去重丟掉第二則快照，也違反 §5.0.4 的 A4。
- **即時事件的 id**：同一個 Bridge 事件最多扇出兩則（第一則 `<seq>`，第二則 `metric-update` 為 `<seq>.1`，見下表）。快照之後才發生的 Bridge 事件 seq 必然大於 `S`，所以即時事件的 id（`<S+1>` 起）一定大於快照的 `<S>.3`，整條串流嚴格遞增、無重複。實作要「先註冊訂閱者、再取快照」，快照之後只送 seq > `S` 的即時事件，避免與快照重複或亂序。
- 事件與觸發：

| Bridge 事件 | 送出 | id |
|-------------|------|----|
| `status`（任何值） | `progress-update` | `<seq>` |
| 終態 `status` | `progress-update`，再一則最終 `metric-update` | `<seq>`、`<seq>.1` |
| `step` `STARTED`／`RETRYING` | `progress-update` | `<seq>` |
| `step` `COMPLETED`／`FAILED` | `progress-update`，再 `metric-update` | `<seq>`、`<seq>.1` |
| `token` | `token-update`，再 `metric-update` | `<seq>`、`<seq>.1` |
| `log`、`alert` | —（這個串流不送） | |

| 事件 | `data` 欄位 |
|------|-------------|
| `progress-update`（`ProgressUpdateEventData`） | `seq, ts, runStatus, bridgeStatus, completedSteps, totalSteps, progressPct(=completedSteps÷totalSteps×100，小數 1 位), currentStep?{stepId,stepNumber,taskId,taskName,goalId,attempt}` |
| `token-update`（`TokenUpdateEventData`） | `seq, ts, tokensUsed(本批次累計，＝Bridge token 事件的 tokens_used), delta(與前一則的差；第一則＝tokensUsed), contextPct(引擎回報的 context 視窗使用%，不是預算%), tokenBudget?, budgetUsageRate?(=tokensUsed÷tokenBudget×100，小數 1 位), taskId?(增量歸因的任務)` |
| `metric-update`（`MetricUpdateEventData`） | `seq, sub, ts, completedTasks, failedTasks, totalTasks, retriedTasks, averageRetryCount, totalTokensUsed, tokenBudgetUsageRate?, elapsedSec`（範圍＝本批次；公式同 §3.8.1 的批次層級） |

```
id: 36
event: token-update
data: {"seq":36,"ts":"2026-10-15T08:30:14.020+00:00","tokensUsed":1240,"delta":1240,"contextPct":0.6,"tokenBudget":100000,"budgetUsageRate":1.2,"taskId":"c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21"}

id: 36.1
event: metric-update
data: {"seq":36,"sub":1,"ts":"2026-10-15T08:30:14.020+00:00","completedTasks":0,"failedTasks":0,"totalTasks":3,"retriedTasks":0,"averageRetryCount":0.0,"totalTokensUsed":1240,"tokenBudgetUsageRate":1.2,"elapsedSec":2}
```

同一條串流上，一個**新連線**在 `S=36` 時先收到的收斂快照（三則 id 互異，之後才是 seq ≥ 37 的即時事件）：

```
id: 36.1
event: progress-update
data: {"seq":36,"ts":"2026-10-15T08:30:14.030+00:00","runStatus":"RUNNING","bridgeStatus":"RUNNING","completedSteps":0,"totalSteps":3,"progressPct":0.0,"currentStep":{"stepId":"G1-T1","stepNumber":1,"taskId":"c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21","taskName":"初始化","goalId":"a1f4c2d3-5b6e-4c7d-8e9f-0a1b2c3d4e11","attempt":1}}

id: 36.2
event: token-update
data: {"seq":36,"ts":"2026-10-15T08:30:14.030+00:00","tokensUsed":1240,"delta":1240,"contextPct":0.6,"tokenBudget":100000,"budgetUsageRate":1.2}

id: 36.3
event: metric-update
data: {"seq":36,"sub":3,"ts":"2026-10-15T08:30:14.030+00:00","completedTasks":0,"failedTasks":0,"totalTasks":3,"retriedTasks":0,"averageRetryCount":0.0,"totalTokensUsed":1240,"tokenBudgetUsageRate":1.2,"elapsedSec":2}
```

### 2.7 Bridge 事件 → Console SSE 對映（逐事件）

Bridge 的 SSE `data` 是扁平封包 `{seq, ts, …}`（事件名在 `event:` 行；`review-request` 事件 Bridge **從不發送**）。**REST 重播的形狀不同**（AR-20）：Bridge 的 `GET /autoclaude/runs/{id}/events` 回的是**含 `event` 鍵的封包陣列**（`{seq, ts, event, …欄位}`，與 `events.jsonl` 同形），SSE 的 `data` 則已去掉 `event` 鍵（`to_sse_data`）。後端用 REST 重播時，要自己取出 `event` 鍵當事件名、並從 `data` 內移除它，再套用下表的對映。

| Bridge `event:` 與 `data` 欄位 | `/logs` | `/metrics` |
|-------------------------------|---------|------------|
| `log` `{level,line}` | `log`（`source=ENGINE`），id `<seq>` | — |
| `status` `{status,reason}`（8 態） | `status-change`，id `<seq>` | `progress-update`（＋終態時 `metric-update`） |
| `step` `{step_id,step_number,status,attempt,name,total_steps}`（`status`∈`STARTED／RETRYING／COMPLETED／FAILED`） | `log`（`source=STEP`），id `<seq>` | `progress-update`（`COMPLETED`／`FAILED` 另加 `metric-update`） |
| `token` `{pct,tokens_used}` | — | `token-update`＋`metric-update` |
| `alert` `{level,code,message,step_id?}` | `alert`（`origin=ENGINE`），id `<seq>` | — |
| （Console 自產）`review_requests` 新列 | `review-request`，id `<seq>.<sub>` | — |
| （Console 自產）規則告警 | `alert`（`origin=CONSOLE`），id `<seq>.<sub>` | — |

### 2.8 客戶端建議流程

1. 頁面載入：`GET /executions/{runId}`（狀態、進度、`pendingReviews`）＋`GET …/dag`＋（可選）`GET …/steps` 取步驟歷史；再開 SSE。
2. 開 SSE：優先用 fetch 串流並帶 `Authorization: Bearer`（可控制 `Last-Event-ID`、避免 token 進 URL）；使用瀏覽器 `EventSource` 時改用 `?access_token=`。
3. 收到事件：依 `event` 更新 UI，並記錄最大 `(seq, n)` 去重。
4. 斷線：自動重連並帶 `Last-Event-ID`；連續失敗兩次以上，退回 REST 回補（2.3 第 6 點）後再連。
5. 收到 `status-change` 且 `runStatus` 為終態：不再重連；若收到 204 同樣停止。restore 後主動重新連線。
6. 前端「SSE 串流」狀態點＝客戶端連線狀態（不是伺服器欄位）。
7. **換新（`POST /auth/refresh`）的失敗分三類**（v1.2；C-5，QA DEF-AC-007）：REST 的 401 換新（`sendWithRenewal`）與 SSE 取 token（`getFreshAccessToken`）共用同一個判斷（`lib/api/client.ts` 的 `doRefresh`／`renewSession`）：

   | 類別 | 判準 | 客戶端動作 |
   |------|------|-----------|
   | `renewed` | 2xx 且帶新 token | 存新 token，重送原請求／重建連線 |
   | `invalid` | HTTP **400／401／403**（refresh token 無效、過期或被撤銷） | **清 session、導向登入**——這是唯一會登出的情形 |
   | `unavailable` | 網路錯誤（`fetch` 丟例外）、HTTP **5xx**（含 nginx 在 backend 重啟時立即回的 502／503／504）、HTTP **429**；其餘未列狀態碼同樣保守視為 `unavailable`（寧可保留 session，也不誤登出） | **保留 session、不登出、不導向登入**；REST 路徑丟 `ApiError{ status:503, reason:"upstream_unavailable", message:"伺服器暫時無法連線，請稍後再試" }`（客戶端合成，附錄 B）；SSE 路徑見第 8 點 |

   為什麼要分：經 nginx 部署時，backend 重啟的那幾秒 `POST /auth/refresh` 會立即得到 502；v1.1 的客戶端把任何失敗都當成登入失效而登出，backend 恢復後仍停在登入頁（QA 全棧實測；mock 伺服器永遠不回 502、本機直連時 EventSource 的重連先成功，所以都看不到）。
8. **SSE 取 token 與退避**（v1.2）：`getFreshAccessToken({force})` 在換新為 `unavailable` 時，**現有 access token 尚未過期就沿用它**繼續連線；已過期則回 `null` 且**不登出**。串流層遇到 `null` 或連線失敗，以 **1→2→4→…→30 秒**（上限 30 秒）指數退避重連，狀態點維持「重新連線中」（不是「已斷線」），並沿用第 4 點的 `Last-Event-ID` 重播與「連續失敗兩次以上才退回 REST 回補」。只有 `invalid` 才清 session。
9. REST 呼叫端收到 `ApiError{status:503, reason:"upstream_unavailable"}` 時：顯示其 `message`、保留畫面狀態，由使用者或下一次輪詢重試；不要導向登入頁。
10. **登出與撤銷（v1.4；D-19；§1.9）**：使用者按登出時，客戶端先 fire-and-forget 呼叫 `POST /auth/logout`（帶目前 session 的 refresh token；不等結果、失敗也不阻擋），再清 session、清快取、導向 `/login`。換新時舊 refresh token 已被撤銷（上一次換新或登出已撤銷它）得到 **401 `INVALID_REFRESH_TOKEN`**，屬第 7 點的 `invalid`：同樣清 session、導向登入——**與「refresh token 過期」在客戶端動作上沒有差別**，所以前端不需要新的分支；差別只在伺服器端（撤銷名單，§1.9.2）。

---
## 3. Bridge 對映、匯入路徑與讀模型

本章是 §1、§2 的實作規則：console-api 如何呼叫 Engine Bridge、如何把外部結果轉成 Console 的資料。所有 Bridge 事實已對 `AgentConsole/engine-bridge/`（README、`app/*.py`、`tests/`）核對；Bridge 只有 console-api 以服務身分呼叫（內網，無認證，Architecture §12 L-6）。

🔴 **本契約依賴一項 Bridge 修復（AR-01）**：Bridge 在 DB 模式對 PAUSED 的 run 做 restore 會自撞 advisory lock 並洩漏鎖（細節見 §1.2.10）。主控已另派修復者修 Bridge 本體；契約維持「PAUSED 可 restore」，受影響的是 §1.2.10、§3.6.3（`GOAL_COMPLETED` 的 `RETRY`）與 E2E-07 步驟 6。Bridge 修復落地前遇到 409 `同專案同路徑已有執行中的批次`（`holderRunId` 是自己），登記為 Bridge 缺陷，不要改契約。

### 3.1 呼叫總表

Bridge 基底位址：**管理員在設定頁改過的** `autoclaude.engineUrl`（`/autoclaude/*`）／`sdd.engineUrl`（`/sdd/*`）優先；沒改過（仍是種子預設 `http://engine-bridge:8081`）就取環境變數 `ENGINE_BRIDGE_URL`（程式預設 `http://localhost:8081`；docker compose 設 `http://engine-bridge:8081`）。每次呼叫都重新解析，設定改了下一個呼叫就走新位址（B1-5；`adapter/out/bridge/BridgeEndpoints.base`、`infrastructure/config/BridgeProperties`）。健康探測路徑＝`autoclaude.healthCheckPath`（**v1.4 起預設 `/health/deep`**，D-17；v1.3 以前為 `/health`）；console-api 的探測環與容器編排的 healthcheck 現在打**同一個深度探針**（§3.1.1）。**為什麼改**（完整性審查 I-03）：Bridge 的淺層 `/health` 不論引擎是否可用都回 `status:"ok"`（`engine-bridge/app/main.py:118-139` 的 `build_health`：`engines.autoclaude.ok`、`engines.sdd.ok` 可為 false 但 `status` 恆為 `"ok"`、整體仍 200；Console 的 `BridgeHttpAdapter.health()` 只看 HTTP 2xx，`BridgeHttpAdapter.java:150-158`），所以引擎匯入失敗、`git` 不見、工作區不可寫時，頂列仍顯示「已連線」、`agentAvailability` 不降；只有 `/health/deep` 會在這些情形回 503。

`AgentBridge`（application 層的 out port）建議的方法名列在最後一欄：後端第一棒先放 `sddCompile`、`decompose`、`approveDraft`、`health`，第二棒在同一介面補其餘（runs 系列）。健康探測的排程與記憶體環由第二棒建立（第一棒的 `notifications/summary` 在此之前把 `bridgeConnected`／`bridgeCheckedAt` 回 null，AR-08，§1.4.1）。

| Console 操作 | Bridge 呼叫 | 成功碼 | 逾時（連線／讀取） | 重試 | 方法名 |
|--------------|-------------|--------|--------------------|------|--------|
| execute | `POST /autoclaude/runs` | 201 | 2s／30s | 無（非冪等；失敗即補償） | `startRun` |
| pause | `POST /autoclaude/runs/{id}:pause` | 202 | 2s／5s | 無 | `pauseRun` |
| resume | `POST /autoclaude/runs/{id}:resume`（可帶 `env`；SDD run 另帶 `X-Bridge-Token`，v1.5） | 202 | 2s／**30s**（v1.5：原 15s；SDD run 可能多一次 `delegate-enter`，CLI 單次 ≤ 20 秒） | 無 | `resumeRun` |
| cancel | `POST /autoclaude/runs/{id}:stop` | 202 | 2s／10s | 無 | `stopRun` |
| restore | `POST /autoclaude/runs/{id}/restore`（SDD run 另帶 `X-Bridge-Token`，v1.5） | 202 | 2s／**30s**（v1.5：原 15s；理由同 resume） | 無 | `restoreRun` |
| 取快照（v1.3 起回應含 `resources`，§3.1.2） | `GET /autoclaude/runs/{id}` | 200 | 2s／3s | 2 次（200ms 退避） | `getRun` |
| 事件重播 | `GET /autoclaude/runs/{id}/events?after=&limit=` | 200（裸陣列） | 2s／10s | 2 次 | `listEvents` |
| 事件串流 | `GET /autoclaude/runs/{id}/stream?after=<last_seq>` | 200 SSE | 3s／45s（閒置逾 45 秒視為斷線，以 `after=<last_seq>` 重連；Bridge 每 15 秒送 keep-alive） | 指數退避 1→30s | `streamEvents` |
| 匯入規格 | `POST /sdd/compile {spec_dir}` | 200 | 2s／15s | 無 | `sddCompile` |
| 匯入拆解 | `POST /autoclaude/decompose` | 200 | 2s／`model.timeout`＋15s | 無 | `decompose` |
| signoff | `POST /autoclaude/decompose/{draft_id}:approve` | 200 | 2s／10s | 無（對已簽署者 409 視為成功） | `approveDraft` |
| 健康探測（v1.4：預設路徑 `/health/deep`；**2xx 為成功，503 `degraded`、其他非 2xx、連線失敗、逾時一律為失敗**） | `GET {healthCheckPath}` | 200 | 2s／**8s**（v1.4；v1.3 以前 3s） | 無；每 30 秒一次，**console-api 啟動時與每個 run 開始時各立即探測一次**，結果存記憶體環（2,880 筆＝24 小時） | `health` |
| 引擎狀態：版本（v1.4） | `GET /sdd/version` | 200 | 2s／3s | 無 | `sddVersion` |
| 引擎狀態：FSM 專案清單（v1.4） | `GET /sdd/fsm` | 200 | 2s／3s | 無 | `sddFsmList` |
| 引擎狀態：單一專案的 FSM（v1.4） | `GET /sdd/fsm/{project}` | 200 | 2s／3s | 無 | `sddFsm` |
| 核准凍結（v1.5；人工閘，§3.1.4） | `POST /sdd/fsm/{project}:freeze`（帶 `X-Bridge-Token`；`{project}` 須 percent-encode） | 200 | 2s／40s | 無（非冪等：第二次回 409） | `sddFreeze` |
| 執行 SDD 批次（v1.5；§3.1.6） | `POST /autoclaude/runs`（帶頂層 `sdd` 與 `X-Bridge-Token`） | 201 | 2s／**90s**（含最多三次 FSM CLI 子行程，每次 ≤ 20 秒；一般批次維持 30s） | 無（非冪等；失敗即補償） | `startRun` |
| 追溯覆蓋（v1.5；§3.1.4） | `GET /autoclaude/runs/{id}/rtm` | 200 | 2s／3s | 無 | `getRunRtm` |
| 引擎狀態：FSM 清單與單一專案（v1.5 加選填 `root`） | `GET /sdd/fsm?root=`、`GET /sdd/fsm/{project}?root=` | 200 | 2s／3s | 無 | `sddFsmList(root)`、`sddFsm(project, root)` |
| 匯入規格（v1.5 加 `spec_file`、`fsm_project`） | `POST /sdd/compile {spec_dir, spec_file?, fsm_project?}` | 200 | 2s／15s | 無 | `sddCompile(specDir, specFile, fsmProject)` |
| 斷點列表 | `GET /autoclaude/runs/{id}/checkpoints`（Bridge 端點仍存在；**Console 不再呼叫**——斷點清單與審核 `RETRY` 的 `step_idx` 一律讀 DB 的 `console.checkpoints`（Bridge DB 模式寫入），W7 依完整性審查 I-07 刪除後端死碼 `listCheckpoints`） | — | — | — | （已移除） |

`:resume` 與 `restore` 的 body 可帶 `env`（Bridge 重啟後請求層 env 會遺失，見其 `ENV_LOST` 告警）：console-api 一律重新物化並帶上 §3.4.2 的 `env`。**機密只能走 `env`**（Bridge 的 `config_overrides` 拒絕 `api_key`／`db_dsn`，且 `run.json` 只記 env 的名稱）。console-api 對上表**每個請求**（含事件串流與健康探測）都帶標頭 `X-Trace-Id`（v1.2，C-12；取值規則 §0.4 第 6 點，Bridge 端見 §3.1.1）。

**v1.5（D-115-18）**：SDD run 的 `:resume` 與 `restore` 另帶標頭 `X-Bridge-Token`（§3.1.4 共通規則 2；與 `sddFreeze`、帶 `sdd` 的 `startRun` 合計四個呼叫）；console-api 不記錄批次是否為 SDD，這兩個呼叫一律附（backend 有設權杖時）。**讀取逾時由 15 秒放寬為 30 秒**（只這兩個呼叫；主控裁決）：SDD run 可能多一次 `delegate-enter`（FSMRuntime CLI 單次逾時 20 秒，§3.1.4 共通規則 1），15 秒會在 Bridge 還在工作時先讀取逾時而得到 504；因為 console-api 分不出 SDD 與非 SDD run，兩者共用同一個逾時值。其餘欄位不變。

#### 3.1.1 Bridge 深度探針 `GET /health/deep` 與 `X-Trace-Id`（v1.2；C-2、C-12）

> 本小節是 **Bridge 自己的端點與標頭**，不是 console-api 的：`openapi-p3-6.yaml` 為了紀錄也列出 `GET /health/deep`（tag「Engine Bridge（內部端點）」，路徑層級的 `servers` 覆寫為 Bridge；schema `BridgeDeepHealthResponse`），但 Bridge 的完整契約以它自己的 `/openapi.json` 與 `engine-bridge/README.md` 為準。原 `GET /health` 條目**不動**。

**為什麼要有深度探針（QA DEF-AC-003，P1）**：`/health` 只證明「Bridge 行程活著、引擎可匯入」；Docker 全棧下 Bridge 映像沒有 `git`（引擎內共 11 處 subprocess 呼叫 git，開機自檢 `boot_self_check` 是其中之一），容器永遠 healthy、任何批次卻一律 FAILED（`FileNotFoundError: 'git'`）——本機、mock、Bridge 的 pytest 全綠，只有全棧真跑才現形。對策兩條：映像安裝 `git` 與 `ca-certificates`（`apt-get install -y --no-install-recommends git ca-certificates`，build 後 `RUN git --version` 冒煙）；healthcheck 改打深度探針。

| 項目 | 契約 |
|------|------|
| 路徑／認證 | `GET /health/deep`；**免認證**（與 `/health` 同；Bridge 本來就只在內網） |
| 檢查（**前四項任一失敗＝整體 degraded**；第五項 `sdd` 只當資訊） | ① `git`：以 subprocess 執行 `git --version`，**逾時 5 秒**；② `autoclaude`：`import autoclaude`；③ `workspace`：在 `ENGINE_WORKSPACE` 內建立並刪除一個暫存檔（可寫）；④ `db`：只有設了 `BRIDGE_DB_DSN` 才做，ping 一次；沒設 DSN 時 `ok` 為 `null`（不算失敗）；⑤ **`sdd`（v1.4，D-17；主控裁決 Q4：只當資訊）**：AISDLC_SDD 樹是否可用，三態；**照常出現在 `checks` 裡，但 `ok:false` 不翻轉整體判定、不進頂層 `reason`、不觸發 503**，見下方「`sdd` 檢查」 |
| 全部通過 | **200**：`{"status":"ok","checks":{"git":{"ok":true,"version":"git version 2.39.5"},"autoclaude":{"ok":true,"version":"…"},"workspace":{"ok":true},"db":{"ok":true},"sdd":{"ok":true,"latest":"AISDLC_SDD_v0.30"}}}`（無 DSN 時 `"db":{"ok":null}`；`sdd` 可為 `true`／`null`／`false`，三種都是 200，見下方） |
| 前四項任一失敗 | **503**：`{"status":"degraded","reason":"<各失敗項的「名稱: 原因」，多項以「；」連接>","checks":{…}}`（頂層 `reason` **只列前四項的失敗，不含 `sdd`**）；失敗的項目 `ok:false` 並各附 `reason`（例：`"git":{"ok":false,"reason":"找不到 git 執行檔"}`），其餘項目（含 `sdd`）照常回報 |
| 使用者 | docker compose 的 bridge healthcheck 與 **console-api 的探測環（v1.4 起，預設 `autoclaude.healthCheckPath=/health/deep`，D-17）** 都打這一支。探測環的讀取逾時因此由 3 秒抬到 **8 秒**（主控已接受）：`git --version` 自己最多等 5 秒，再加其餘各項，3 秒的讀取逾時會在 Bridge 只是慢、並沒有壞時把它判成不可達。**成本**：每次探測 spawn 一次 `git`、建立並刪除一個暫存檔、（有 DSN 時）ping 一次 DB，每 30 秒一次，對單一 Bridge 可以忽略（v1.2 曾因此讓探測環留在淺探測，D-17 改變這個取捨）。**探測的敏感面**：`agentAvailability`、`bridgeConnected`、`AGENT_UNRESPONSIVE` 只對 `git`／`autoclaude`／`workspace`／`db` 四項敏感；`sdd` 無效只會出現在 `checks.sdd` 與 Console 的 SDD 卡（`GET /engines/sdd` 的 `available=false`），**不會**拉低 Agent 可用率、讓頂列轉灰或誤報告警——SDD 是選用引擎，它壞了不該被當成 Bridge 不可用（主控裁決 Q4；§3.7、§3.8.1） |

**`sdd` 檢查**（v1.4，D-17；實作 `engine-bridge/app/health.py` 的 `check_sdd`；回 `{"ok", "latest", "reason"?}`；**只當資訊：不論回什麼，整體判定都不看它**）：

| `ok` | 條件 | 本文 |
|:----:|------|------|
| `null`（不算失敗） | `Settings.sdd_root` 為 None：`SDD_ROOT` 沒設，且預設位置 `<monorepo>/AISDLC_SDD` 下找不到版本目錄（映像內沒掛載 SDD 時即此情形）。Bridge 照樣能跑 AutoClaude 的批次，只有 `/sdd/version`、`/sdd/fsm*` 回 503 | `{"ok":null,"latest":null,"reason":"未設定 SDD_ROOT，也找不到預設位置的 AISDLC_SDD 目錄"}`（`reason` 在這裡只是說明，不算失敗） |
| `true` | `sdd_root` 是目錄，**且**（有 `build/reports/fsm` **或**有版本入口文件 `AISDLC_SDD_INIT.md`） | `{"ok":true,"latest":"<目錄名>"}` |
| `false` | `sdd_root` 不存在或不是目錄；或是目錄但兩者都沒有（空的或掛錯的唯讀掛載，例如掛載來源路徑不存在、被建成空目錄） | `{"ok":false,"latest":<目錄名或 null>,"reason":"…"}`；**整體仍 200**（只當資訊），頂層 `reason` 不列它 |

**判準與「只當資訊」（主控裁決 Q1、Q4；INFRA 已實作並以 `tests/test_health_deep.py` 實測）**：①**為什麼入口文件也算數**——主控任務書原寫「`build/reports/fsm` 不存在 → false」，但 `AISDLC_SDD/AISDLC_SDD_v0.30/build/reports/` 被 git 忽略（`AISDLC_SDD/.gitignore:313`，`git ls-files` 在該目錄為 0 筆），**全新 clone 沒有這個目錄**。FSM 狀態檔是跑過 SDD runtime 才有的執行期產物，不是「SDD 樹有沒有掛上」的證據；每個版本目錄都有、而且入庫的入口文件 `AISDLC_SDD_INIT.md` 才是（`git ls-files` 30 筆，對應 30 個版本目錄）。②**為什麼不算進 503**——SDD 是選用引擎：compose 的 healthcheck 與 Console 的探測環都打這一支，503 會被當成「Bridge 不可用」（容器 unhealthy、頂列轉灰、Agent 可用率下降、誤報 `AGENT_UNRESPONSIVE`），而 `SDD_ROOT` 設定錯誤其實只影響 `/sdd/version`、`/sdd/fsm*` 兩類查詢（規格編譯 `/sdd/compile` 不讀 `SDD_ROOT`），AutoClaude 批次照常可跑；所以 `sdd.ok=false` 只顯示在 `checks.sdd` 與 Console 的 AISDLC_SDD 卡（`GET /engines/sdd` 的 `available=false`、`reason=sdd_unavailable`）。兩點合起來，乾淨 clone 的全棧起得來，Bridge 的快樂路徑 pytest 在 CI 的乾淨 checkout 也不會紅。

**`X-Trace-Id`（NFR-9.4-04；C-12；QA O-11）**：console-api 對 Bridge 的**每個請求**都帶標頭 `X-Trace-Id`（取值規則見 §0.4 第 6 點）。Bridge 的 HTTP 中介層：① 讀取該標頭（缺漏或格式不合時自產 `uuid4`）；② **回應回帶同名標頭**（SSE 事件串流的回應同樣帶）；③ 把它放進 `contextvars`，使 Bridge 的**每一行**應用日誌都帶 `trace_id` 欄位——沒有請求上下文的行（啟動、關閉、與請求無關的背景執行緒）`trace_id` 為 `-`；Bridge 為某個請求啟動的背景工作（run 監督執行緒）是否沿用該請求的 trace id 由實作決定（建議沿用，例如 `contextvars.copy_context()`）。Bridge 另可設 `BRIDGE_LOG_DIR` 把日誌寫成滾動檔案（compose 掛 `app_logs` 卷，C-16；與 console-api 的 `LOG_DIR` 同義）。驗收見 E2E-13。

#### 3.1.2 引擎行程樹的資源取樣 `RunStateOut.resources`（v1.3；D-12；US-M-10）

> 本小節是 **Bridge 的回應欄位與背景取樣器**，實作者是 W7-INFRA（`engine-bridge/app/models.py` 的 `RunStateOut`、`runner.py` 的 `RunHandle.snapshot()`、新增的取樣器）；console-api 只消費它（§1.2.3 的 `bridge.resources`）。Bridge 的完整契約仍以其 `/openapi.json` 與 `engine-bridge/README.md` 為準，INFRA 須同步更新 README。

`GET /autoclaude/runs/{id}` 的回應（`RunStateOut`）新增欄位 **`resources: ResourcesOut | null`**（只增不減；其他欄位一律不動）。

| 項目 | 契約 |
|------|------|
| `ResourcesOut` | `{ "cpu_percent": 12.3, "rss_bytes": 361758720, "process_count": 3, "sampled_at": "2026-10-16T03:21:45.123456+00:00" }`；`cpu_percent`＝float，0.0～100.0，**小數 1 位**；`rss_bytes`＝int，≥ 0；`process_count`＝int，≥ 1；`sampled_at`＝ISO-8601 含 offset（Bridge 一律 UTC `+00:00`，與其他時間戳一致） |
| 取樣對象 | 該 run 的**引擎行程樹**：`RunRecord.pid`（`python -m autoclaude` 那個行程）加上它的全部子孫（`psutil.Process(pid).children(recursive=True)`，含 `claude` 或 mock claude 子行程）。**不含 Bridge 自己**，也不含別的 run |
| `cpu_percent` | 行程樹各行程 `Process.cpu_percent(interval=None)` 的**總和 ÷ 邏輯核心數**（`psutil.cpu_count(logical=True)`，取不到時視為 1），夾在 0～100、四捨五入到小數 1 位＝**整機正規化**（100 ＝ 整台機器所有邏輯核心被占滿；與 `top` 那種單核 100% 的算法不同，前端文案就叫「CPU」不加「核」）。**所以多核機器上的數字會偏小是正常的**：W7-SA 實測 20 個邏輯核心的機器上，一個單執行緒滿載的行程樹是 4.9%（同一個 `Process` 物件上的原始值 97.9 ÷ 20） |
| `rss_bytes` | 行程樹各行程 `memory_info().rss` 的總和。各行程的共用頁（解譯器、共用函式庫）會被重複計入，所以這是**上界估計**，不是精確的實體記憶體占用；畫面文案寫「記憶體」即可，不要標示成精確值 |
| `process_count` | 取樣當下仍存活的行程數（含根），照實回報、不扣除。**Windows 實測（W7-SA 以 psutil 對一個含孫行程的 venv 行程樹取樣）：用 venv 的 `python.exe` 啟動的行程會多一層啟動器殼，兩個直譯器對應 4 個行程**；所以引擎樹的行程數比直覺大，任何測試只能斷言 ≥ 1，不得斷言精確值 |
| 取樣節奏 | Bridge 背景執行緒**每 5 秒**對每個「引擎行程樹存活」的 run 取一次樣本，記憶體只留**最近一筆**；**請求路徑不取樣、不阻塞**，只回最近一筆。建議 spawn 後立刻補一筆（CPU 為 0.0），讓第一次輪詢就有值 |
| 🔴 取樣器的陷阱 | `cpu_percent(interval=None)` 是「與**同一個 `psutil.Process` 物件**上一次呼叫之間」的差值。取樣器必須**跨 tick 持有每個 pid 的 `Process` 物件**（以 pid＋`create_time` 為鍵，行程消失就丟）；每次都重建物件＝每次都是第一筆＝永遠 0.0。新出現行程的第一筆 CPU 為 0.0 屬預期，可接受 |
| 何時為 `null` | ①引擎行程樹不存活：尚未 spawn、**PAUSED（pause 會終止整棵行程樹，ADR-001 D8，所以暫停中沒有資源可言）**、終態；②還沒有第一筆樣本；③**最近一筆樣本已超過 15 秒**（取樣器卡住或掛掉：寧可回 null，也不回過期的數字）。單一行程取樣失敗（`NoSuchProcess`／`AccessDenied`／`ZombieProcess`）只略過該行程，不讓整筆失敗；行程樹內全部都取不到＝①。取樣器自己的任何例外只記 log，不得拖垮 Bridge 或改變 run 狀態 |
| 不外露 | `resources` 不含 pid、命令列、環境變數；console-api 的回應同樣不含 |
| 平台 | Windows 與 POSIX 都只走 `psutil`（不用 `os.kill`／`/proc` 直讀）；Windows 行為＝`cpu_percent` 同樣以邏輯核心數正規化；平台相依處留註解 |

**console-api 的對映**（`ExecutionRunDetailResponse.bridge.resources`）：`cpu_percent→cpuPercent`、`rss_bytes→memoryBytes`、`process_count→processCount`、`sampled_at→sampledAt`（值原樣帶出，不在 console-api 重算或四捨五入）。Bridge 不可達（`bridge.connected=false`）、`run_not_found`（`runKnown=false`）、回應缺 `resources` 鍵或值為 null 時，`bridge.resources` 為 null。資源不進 SSE、不寫 DB：前端跟著 `GET /executions/{runId}` 的輪詢（現為 15 秒，`EXECUTION_POLL_MS`）更新，所以畫面上的數字最舊約 20 秒，這是設計取捨，不是缺陷。

驗收：Bridge pytest（有行程時 `resources` 欄位齊全且型別正確、終態與 PAUSED 後為 null、取樣器對已消失的 pid 不炸、跨 tick 持有 `Process` 物件而非每次重建）；E2E-14 第 8～9 列。

#### 3.1.3 Bridge 的 AISDLC_SDD 唯讀查詢：`GET /sdd/fsm`（清單）與 `GET /sdd/fsm/{project}` 的新欄位（v1.4；D-16）

> 本小節是 **Bridge 的端點**，實作者是 W7-INFRA（`engine-bridge/app/routers/sdd.py`）；console-api 只消費它們（§1.7.1）。形狀由主控 D-16 定死；下表補的是**對現行 FSM 狀態檔真實結構的語意定義**——W7-SA 現讀 `AISDLC_SDD_v0.30/tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml`、`state_loader.py` 與 `build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml`（證據見 §6.7.2）；INFRA 的實作與其測試（`engine-bridge/tests/test_sdd_fsm.py`）與下表一致，契約從其實作。Bridge 的完整契約仍以其 `/openapi.json` 與 `engine-bridge/README.md` 為準，INFRA 須同步更新 README。三個端點全是**唯讀**：不寫、不建立、不改動 SDD 目錄下的任何東西（ADR-001 D22 第 3 點；AISDLC_SDD Rule 9「繞過 `FSMRuntime` 直接讀寫 FSM-STATE」是違反即停機的禁令，Console 只讀）。

> **v1.5 加註（D-115-01、D-115-02、D-115-14；S-10）**：本小節描述 v1.4 的三個**唯讀**端點；v1.5 對它們的改動（選填 `root`、回應增 `phase`／`escalation_history`／`escalation_provenance`／`fsm_project`／`recovery`、專案名改由淨化鏡像處理）與新增的唯一寫入動詞 `:freeze` 一律寫在 §3.1.4，本小節的「名稱白名單」「只讀不寫」等字句在與 §3.1.4 衝突處以 §3.1.4 為準。

**`GET /sdd/version`**：不變（`{"latest":"<版本目錄名>","root":"<路徑>"}`；`SDD_ROOT` 無效 → 503 `sdd_unavailable`）。

**`GET /sdd/fsm`**（新）：

| 項目 | 契約 |
|------|------|
| 掃描 | `<SDD_ROOT>/build/reports/fsm/` 底下（第一層，不遞迴）檔名符合 `FSM-STATE-<name>.yaml` 的項目。`.yml`、`.bak` 與其他檔名一律忽略（不進清單也不進 `errors`） |
| 回應 200 | `{"root":"<SDD 版本目錄名>","projects":[{"project","source","current_state","updated_at"}],"errors":["<檔名>",…]}` |
| `projects[]` | `project`＝檔名去掉前綴 `FSM-STATE-` 與副檔名 `.yaml`（**就是 `GET /sdd/fsm/{project}` 吃的鍵**，每一筆都點得進去）；`source`＝檔名；`current_state`、`updated_at`＝檔內 `fsm_state` 同名鍵（缺則 null；`updated_at` 原樣，不轉型） |
| 名稱白名單 | `<name>` 必須符合 `^[A-Za-z0-9._-]{1,128}$`（與 `{project}` 路徑參數同一條規則）；不合者（空白、非 ASCII、過長…）放進 `errors`，不進 `projects` |
| `errors[]` | 讀不動的**檔名**（不含路徑與內容）：名稱不合白名單、YAML 語法錯誤、YAML 巢狀過深（PyYAML 遞迴超限，`RecursionError`）、不是 UTF-8、檔案讀取失敗（`OSError`）、缺 `fsm_state` 根節點或它不是映射、同名但是目錄、resolve 後跑出 fsm 目錄的 symlink（逃逸）。一個壞檔不影響其餘檔的列出；`errors` 永遠出現（可為空陣列） |
| 排序 | 依**檔名**不分大小寫升冪（`casefold`；`Zulu` 排在 `beta` 之後）。檔名前綴固定，所以一般情形等同依專案名；邊緣差別：一個名稱是另一個名稱的前綴時（例：`a` 與 `a-b`），排序鍵多了 `.yaml` 副檔名，`a-b` 會排在 `a` 之前（INFRA 的實作如此，契約從之）。console-api 不重排 |
| 目錄不存在 | `build/reports/fsm` 不存在（全新 clone：`build/reports/` 被 git 忽略）→ **200** `{"root":…,"projects":[],"errors":[]}`，不是錯誤。此時 `GET /sdd/fsm/{任何名稱}` 是 404 `fsm_not_found` |
| `SDD_ROOT` 無效 | 503 `{"code":503,"reason":"sdd_unavailable","detail":"…"}`（同 `GET /sdd/version`） |
| 開發機上的實際內容 | 同一個目錄除了 `FSM-STATE-AISDLC_SDD.yaml`（真專案）之外，還有 SDD 測試套件留下的 `FSM-STATE-test-<數字>.yaml` 殘留檔（W7-SA 實見 7 個），**照列**，Bridge 不過濾；所以任何斷言一律寫「清單**包含**某專案」，不寫「清單等於…」（E2E-15） |

**`GET /sdd/fsm/{project}`**：既有欄位**一個都不動**（`project`、`current_state`、`current_sprint`、`session_id`、`updated_at`、`frozen_stages`、`decision_trace`〔尾 5 筆〕、`source`），**只增不減**，新增三個：

| 新欄位 | 型別 | 語意（以現行 FSM-STATE 的真實結構為準） |
|--------|------|------------------------------------------|
| `human_pending` | `{"count": int, "items": object[]}` | 讀 `fsm_state.human_pending_tracking`。**現行寫法是單一映射**（`entered_at`、`reminder_sent_at`、`reminder_hours`、`escalation_hours`；`entered_at` 在進入 `HUMAN_PENDING` 時蓋時戳、離開時清成 null）：`entered_at` 有值＝FSM 正停在人工確認點 → `{"count":1,"items":[<該映射原樣>]}`；`entered_at` 為 null／缺席 → `{"count":0,"items":[]}`。若它是 list（日後 schema 改成多筆）→ `count`＝筆數、`items`＝尾 5 筆原樣；其他型別 → `{"count":0,"items":[]}`。**所以 `count` 實務上只會是 0 或 1** |
| `retry_history` | `{"count": int, "last": object \| null}` | 讀 `fsm_state.retry_history`。**現行寫法是「以重試閘為鍵的映射」**（`SCG_VALIDATION`、`PR_REVIEW`、`RTM_VERIFY`，各有 `current_count`、`max_limit`、`history[]`；`history` 每筆 `{attempt, date, failure_reason, scg_gate}`）：`count`＝各閘 `history` 筆數的總和（`patterns` 等其他列表不算）；`last`＝全部筆中 `date` 最晚者（`date` 以字串比較〔ISO 8601 時戳〕，缺 `date` 視為空字串而最早；同時刻取後出現者）**原樣再加一個 `gate` 欄**（所屬的閘名；合併後無法從原筆看出；某筆若不是映射，則以 `{"gate":…,"value":<該筆>}` 帶出）；某閘的 `history` 不是 list 就略過該閘；沒有任何一筆 → `{"count":0,"last":null}`。若它是 list → `count`＝筆數、`last`＝尾 1 筆；其他型別 → `{"count":0,"last":null}` |
| `rtm_coverage` | object \| number \| null | 讀 `fsm_state.rtm_coverage`，**有就原樣帶出，沒有就 null**。現行 FSM-STATE schema（`FSM-STATE-TEMPLATE.yaml`、`state_loader.py`）**沒有任何 RTM 覆蓋數值的鍵**（`retry_history.RTM_VERIFY` 是重試計數，不是覆蓋率；RTM 覆蓋率在 `docs/03_testing/` 的 RTM 與 SCG-5 閘門結果），所以**現況恆為 null**；這個欄位是保留位，Console 卡片不顯示它 |

**錯誤**（`GET /sdd/fsm/{project}`；沿用 Bridge 的錯誤封包 `{"code","reason",…}`）：`project` 不合白名單、檔不存在、或 symlink 逃逸 → 404 `{"code":404,"reason":"fsm_not_found","project":"<名稱>"}`；YAML 壞掉、YAML 巢狀過深（`RecursionError`）、不是 UTF-8、檔案讀取失敗（`OSError`）、缺 `fsm_state` 根節點 → 422 `{"code":422,"reason":"fsm_state_unreadable","detail":"…"}`（清單端點對同樣的檔放進 `errors[]`，不是 500）；`SDD_ROOT` 無效 → 503 `sdd_unavailable`。

驗收：Bridge pytest（`tests/test_sdd_fsm.py`：清單的排序、`errors`、symlink 逃逸、目錄不存在、503；三個新欄位對真實結構與假設的 list 結構；只讀不寫的 mtime 快照；對真實 FSM 檔逐值比對〔檔不存在時 skip〕）；E2E-15。

#### 3.1.4 Bridge 的 SDD 讀取擴充與寫入面（v1.5；D-115-01、D-115-02、D-115-03；已與 ADR-016 對齊）

> 本小節是 **Bridge 的端點與行為**（實作者是 W2 Dev-Bridge：`engine-bridge/app/routers/sdd.py`、`routers/autoclaude.py`、`models.py`、`runner.py`、`settings.py` 與新模組）；console-api 只消費它們（§1.10）。Bridge 的完整契約仍以其 `/openapi.json` 與 `engine-bridge/README.md` 為準，Dev-Bridge 須同步更新 README。環境契約、CLI 動詞與 rc、權杖的**完整規格**以 ADR-016 §3.5、§4、§9 為唯一真相源；本節寫 HTTP 面，並逐字引用需要機械斷言的值。

**共通規則（v1.5 起適用於所有 SDD 寫入）**：

1. **只經 CLI 子行程**（ADR-016 §3.5）：Bridge 對 FSM 的一切寫入都是 FSMRuntime CLI 子行程——argv＝`[sys.executable, "-W", "ignore::RuntimeWarning", "-m", "tools.fsm_runtime.fsm_runtime", <動詞>, "--project", <專案鍵>, "--must-exist", …]`，cwd＝SDD 版本目錄；環境以 `os.environ` 為底**移除所有 `BRIDGE_*`、`SDD_*`、`PYTHONPATH`**，再設 `PYTHONPATH=<版本目錄>`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUTF8=1`、兩個規則遙測旗標＝`0`、`SDD_STATE_DIR=<root>/build/reports/fsm`、`SDD_PROJECT=<專案鍵>`；stdin＝DEVNULL，行程旗標沿用 `procutil.popen_platform_kwargs()`；stdout 取最後一個非空行解析為 JSON，stderr 只作診斷（截 2 KB 入稽核、不入回應）；單次逾時 **20 秒**（逾時以行程樹終止後回 504）。動詞白名單：`spec-frozen`（僅經 `:freeze`）、`negotiate-enter`、`negotiate-exit --outcome agreed`、`delegate-enter`、`delegate-exit --decision done｜failed`；其餘動詞 Bridge 一律不呼叫。**Bridge 原始碼不得出現對 `FSM-STATE-*.yaml` 的寫入開檔**（Rule 9 絕對禁令第 1 條；對拍測試 F-4 以原始碼掃描釘住）。
2. **權杖**（ADR-016 §9）：寫入動詞須帶標頭 `X-Bridge-Token`，**共四個呼叫**：`POST /sdd/fsm/{project}:freeze`、帶 `sdd` 的 `POST /autoclaude/runs`，以及 SDD run（`RunRecord.sdd` 存在）的 `POST /autoclaude/runs/{id}:resume` 與 `POST /autoclaude/runs/{id}/restore`（D-115-18 把 ADR-016 §9 的兩個呼叫擴大為四個：這兩個動作同樣會寫 FSM〔`delegate-enter` 重進〕）；權杖的環境變數名為 **`BRIDGE_SDD_WRITE_TOKEN`**（Bridge 與 backend 同名；backend 的 Spring 屬性 `console.bridge.sdd-write-token`，附錄 D.2）。Bridge 沒有設定權杖＝這些動詞整個停用：**503** `{"code":503,"reason":"sdd_write_disabled","detail":"…"}`（不含 `sdd` 的 run——含它的 `:resume`／`/restore`——照舊，不需要權杖）；設了而標頭缺漏或不符＝**403** `{"code":403,"reason":"sdd_write_forbidden"}`（缺與錯同一個 reason，`hmac.compare_digest` 比對）。設定值**短於 32 字元或仍是 `<…>` 佔位**＝Bridge **啟動即失敗**（`SettingsError`，不靜默退回停用）。權杖**只有 backend 與 Bridge 持有**：`RunHandle._child_env` 必須在合併請求層 `env` 之前先移除繼承來的 `BRIDGE_SDD_WRITE_TOKEN`、`SDD_STATE_DIR`、`SDD_PROJECT`，之後**只有**含 `sdd` 區塊的 run 才設 `SDD_PROJECT=<專案鍵>`（**不注入 `SDD_STATE_DIR`**：引擎沒有讀者，給了只會讓子行程內的 AI 步驟拿到呼叫 FSM CLI 的現成指向）；`security.validate_env` 的拒絕清單加入這三個名稱（請求層 `env` 設定它們 → 422 `forbidden_name`）；任何回應、日誌、稽核事件都不得出現權杖值（對拍測試 F-7）。權杖檢查先於一切會碰檔案系統的檢查（`:resume`／`/restore` 例外：須先查到 run 才知道它帶不帶 `sdd`，順序是 run 查找〔404 `run_not_found`〕→ 權杖 → 其餘預檢、取鎖與 FSM 動作；缺／錯同樣回 503／403，run 狀態不變、不 spawn）。console-api 不記錄批次是否為 SDD，對 `:resume`／`/restore` 一律附標頭（backend 有設權杖時；Bridge 對非 SDD run 不看它）。
3. **序列化與稽核**（ADR-016 §3.5、§9）：行程內以 `(狀態目錄, 專案鍵)` 為鍵的互斥鎖，**同時罩住**「CLI 呼叫」與「`GET /sdd/fsm/{project}` 的檔案讀取」（消除 Bridge 自己「讀的當下被 `os.replace` 換檔」的 Windows 共享違規）。跨行程競態（例如 SDD session 同時在寫）**沒有跨行程鎖**，是已知邊界（§3.1.7 第 9 點）。每個成功或被拒的寫入動詞都記一筆 Bridge 稽核事件 `sdd_write`（`security.AuditLog`：`verb`、`project`、`approver`、`result`，另帶 `trace_id`；不記權杖與環境）。
4. **CLI 失敗的共同對映**（rc 表見 ADR-016 §4.1；CLI stdout 恰好一行 JSON，失敗為 `{"ok":false,"error":<代碼>,"detail":<ASCII，≤200 字>}`；`--reason` 內的中文只進 YAML、不回印）：

| CLI rc | stdout `error` | Bridge 回應 |
|:------:|----------------|-------------|
| 0 | —（含 `"noop":true`） | 繼續 |
| 1 | —（非預期例外） | **502** `sdd_cli_failed`（`detail` 為 ASCII，不含環境變數與權杖） |
| 2 | —（argparse 用法錯誤；stdout 無 JSON） | **500** `sdd_cli_usage`（Bridge 自己的 bug，測試必須零次出現） |
| 3 | `transition_not_allowed` | **409** `fsm_state_conflict`（`detail.current_state`） |
| 4 | `invalid_argument`／`doc_not_found`／`doc_outside_root`／`doc_too_large`／`doc_not_utf8` | **422** `sdd_invalid_argument`（Bridge 先驗過，出現＝Bridge bug 或競態） |
| 5 | `state_not_found`／`state_unreadable` | **404** `fsm_not_found`／**422** `fsm_state_unreadable` |
| —（逾時 20 秒） | — | **504** `sdd_cli_timeout` |
| —（無法啟動） | — | **502** `sdd_cli_failed` |

**(a) 選填查詢參數 `root`（`GET /sdd/fsm`、`GET /sdd/fsm/{project}`）**

| 項目 | 契約 |
|------|------|
| 語意 | 專案根目錄（絕對路徑）；狀態目錄＝`<root>/build/reports/fsm`（取代預設的 `<SDD_ROOT>/build/reports/fsm`）。省略＝v1.4 行為，完全不變 |
| 驗證 | 經 `security.check_path`（`BRIDGE_ALLOWED_PATH_ROOTS`；絕對路徑、無 `..`、存在、是目錄）；不合 → **422** `{"code":422,"reason":"sanitization_failed","violations":[{"field":"root","rule":…}]}`（沿用既有形狀） |
| 其餘 | `<root>/build/reports/fsm` 不存在＝與 v1.4 相同（清單回 200 空清單、`GET /sdd/fsm/{任何名稱}` 回 404 `fsm_not_found`）；symlink 逃逸檢查維持；`SDD_ROOT` 無效仍是 503 `sdd_unavailable`（CLI 與版本資訊仍需要它）；清單回應的 `root` 欄位語意不變（SDD 版本目錄名） |

**(b) 專案名規則（S-10；ADR-016 §7.4；取代 `^[A-Za-z0-9._-]{1,128}$`）**

- **淨化鏡像**：Bridge 持有**一份**逐字鏡像 `fsm_component(name)`（Bridge 與 SDD 同屬 monorepo 但不同子專案，不 import；建議檔 `fsm_names.py`），規則來源 `AISDLC_SDD/scripts/component_sanitizer.py` 的 `sanitize_component`：NFC → strip → 把 `<`、`>`、`:`、`"`、`?`、`*`、`\`、`/`、ASCII 豎線與 ord<0x20／0x7F 換成 `_` → 截 80 → `rstrip(" .")`（空則 `untitled`）→ stem 若是 Windows 保留裝置名則加 `_` 前綴並重截。**進入 Bridge 的專案名（`:freeze` 的路徑參數、`GET /sdd/fsm/{project}` 的路徑參數、`sdd.fsm_project`、`/sdd/compile` 的 `fsm_project`）一律先過它**；淨化是冪等的，所以傳原名與傳標準鍵等價。
- **讀取白名單＝淨化輸出域**：非空；已是 NFC；長度 ≤ 80；不是 `.`／`..`；不含 `<`、`>`、`:`、`"`、`?`、`*`、`\`、`/`、ASCII 豎線、控制字元、DEL；無前後空白；不以 `.` 結尾。`GET /sdd/fsm`（清單）的 `errors` 語意不變：檔名不合此判準者進 `errors`，不進 `projects`。`..` 只有整段等於 `.`／`..` 或帶分隔符才有穿越意義；`_readable_state_file` 的 symlink 逃逸檢查維持。
- **原名反查**（🔴 D-115-19 覆寫：本條**不實作**、原文保留）：~~`GET /sdd/fsm/{project}` 先以淨化後的鍵找 `FSM-STATE-<鍵>.yaml`；無該檔但**恰有一個**檔的 YAML `fsm_state.project` 等於輸入原名時採用它~~——ADR-XPLAT-016 §7.4 無此條；SDD 的 `state_loader` 與 Bridge 同用 `sanitize_component`，CLI 產生的檔名必等於標準鍵，反查只對手動改名的檔有意義；原名反查仍存在於 **adapter 內部**（ADR §7.1、F-2 的 `a:b` 對拍）。路徑參數須 percent-encode（`%`、`#`、`+`、`;`、空白與非 ASCII）；含 `/` 的原名不可由 URL 定址（§3.1.7 第 11 點，已知邊界），請改用回應的 `fsm_project`。
- **Console 側**：Backend 不淨化、不檢查 Windows 禁用字元，只做長度與控制字元的檢查（§1.10.4），把有效值原樣交給 Bridge。對拍測試 F-8：`fsm_component` 對一批樣本（含 CJK、空白、括號、`+`、`@`、`a:b`、`x/y`、`CON`、80 字以上、NFD 輸入、尾端空白與句點）與 SDD 原函式逐一相等且冪等，其輸出皆被讀取白名單接受。

**(c) 回應新欄位（只增不減；僅 `GET /sdd/fsm/{project}` 與 `:freeze` 的成功回應）**

| 新欄位 | 型別 | 語意 |
|--------|------|------|
| `phase` | `{"name":str,"order":int,"blocking":bool,"observation":bool}` 或 null | 由 `current_state` 純函式投影出的階段資訊（定義與對映表見 §3.1.5）。**欄位永遠出現**；尚未接線該函式的 Bridge 回 null（W4 dogfood 產物搬入後恆有值，未知狀態回 `UNKNOWN` 物件而不是 null）；Backend／Frontend 一律當選填，缺值顯示「—」 |
| `escalation_history` | object[] | 讀 `fsm_state.escalation_history`（list）的**尾 5 筆**，舊→新、原樣；缺或不是 list → `[]` |
| `escalation_provenance` | object 或 null | 讀 `fsm_state.escalation_provenance` 原樣；缺或不是映射 → null。🔴 它與 `autoclaude_delegated_tracking` 在人工恢復後都**不會被清除**，是歷史殘留欄、不是現況旗標，消費者必須先看 `current_state`（ADR-016 §5.3） |
| `fsm_project` | string | 狀態檔名裡**淨化後的標準鍵**（`FSM-STATE-<鍵>.yaml` 的 `<鍵>`）。現有的 `project` 欄是檔內原名，兩者可能不同，不能拿 `project` 當鍵（ADR-016 §7.2） |
| `recovery` | `{"target":str,"powershell":str,"posix":str}`，或鍵缺席 | **僅 `current_state` 為 `ESCALATION`／`ESCALATION_FINAL` 時出現**：`target`＝建議的 `resume-from-escalation --to`（委派失敗＝`IMPLEMENTATION`，與 `autoclaude_delegated_tracking.resume_state` 一致；Bridge 無法判定目標時整個鍵省略，§6.8.6 靜默處 #5）；`powershell`／`posix`＝ADR-016 §5.3 的恢復指令模板（PowerShell 形態用 `Push-Location`／`Pop-Location` 同一句內成對、不裸 `cd`；POSIX 的 `VAR=值 指令` 前綴只作用於該指令；嵌入的路徑與專案鍵須依各殼層規則跳脫），`--reason` 留 `<人工原因>` 佔位。Bridge 與 Console **都不提供恢復動詞**（`resume-from-escalation` 不在 CLI 白名單；恢復只有人、留在 SDD session，R-9.5） |

`frozen_stages[]` 的項目自 v1.5 起可含兩個只在有值時才出現的新鍵：`spec_doc_digests`、`approved_by`（見 (d)）。`GET /sdd/fsm`（清單）的項目**不帶**以上任何新欄位。

**(d) `POST /sdd/fsm/{project}:freeze`　核准凍結（唯一的 FSM 寫入動詞）**

- **請求**：標頭 `X-Bridge-Token`（必填）、`X-Trace-Id`（選填，既有規則）；body（`extra=forbid`）：

| 欄位 | 型別 | 規則 |
|------|------|------|
| `root` | string | 專案根目錄（絕對路徑；同 (a) 的 `check_path`） |
| `stage` | string | 選填；`^[A-Za-z0-9._-]{1,64}$`；省略 → `Stage-<n>`（`n`＝`frozen_stages` 筆數＋1，Bridge 持互斥鎖時讀狀態檔計得）。階段名不要求唯一（摘要鍵遇重複以後者為準） |
| `docs` | string[] | 1～20 項；每項是相對 `root` 的 POSIX 路徑，不得為絕對路徑、不得含 `..`，須是 `root` 之下的既有檔案（resolve 後不得跑出 `root`，含 symlink）；**至少一份檔名符合官方 TCS 命名**（`TEST-CONTRACT-SPEC-*` 或 `TCS-*`，與 adapter 的官方命名判準同形） |
| `approver` | string | 1～100 字元，無控制字元，**不含 `;`**（否則 422 `sdd_invalid_argument`，讓 `--reason` 的 `key=value; …` 組字可無歧義解析） |
| `reason` | string | 去前後空白後 1～500 字元，無控制字元（含換行）；**不靜默截斷、不替換**，違反即 422 `sdd_invalid_argument` |
| `expected_digests` | object | 選填；`{<docs 內的相對路徑>: "sha256:<64 位小寫 hex>"}`＝核准人當時看到的摘要；鍵須都在 `docs` 內 |

- **檢查順序（固定；與 Dev-Bridge 實作一致）**：①本文格式（422 `invalid_request`，既有）②權杖（503／403，共通規則 2）③`approver`／`reason` 清理（不合 → 422 `sdd_invalid_argument`）④`root`（422 `sanitization_failed`）⑤`{project}` 經淨化鏡像後找狀態檔（不存在 → 404 `fsm_not_found`；YAML 壞掉 → 422 `fsm_state_unreadable`）⑥`docs` 逐項檢查（422 `sanitization_failed`，`violations[].field` 為 `docs[i]`，`rule` 為 `absolute`、`contains_dotdot`、`not_found`、`outside_root`、`duplicate`、`invalid`；Console 把 `rule` 當不透明字串顯示，不依賴碼表；整份 `docs` 不含 TCS → 同為 422 `sanitization_failed`，`violations=[{"field":"docs","rule":"missing_tcs"}]`，規則碼與 Dev-Bridge 實作一致；§6.8.6 靜默處 #4）⑦前置：`current_state==HUMAN_PENDING`，否則 **409** `fsm_state_conflict`（`detail={"current_state":"<實際>","expected_state":"HUMAN_PENDING"}`）⑧`expected_digests` 逐一與現檔摘要比對，不符 → **409** `spec_digest_changed`（`detail={"pair":"expected_vs_file","doc":…,"expected_digest":…,"current_digest":…}`；鍵不在 `docs` 內 → 422 `sanitization_failed`，`rule=not_in_docs`）⑨以 CLI `spec-frozen --digest --root --stage --doc… --approver --reason --json` 記錄凍結（CLI 先驗前置、再算摘要、最後才改狀態；缺檔、非 UTF-8、超過 16 MiB 時 CLI 自己也會失敗＝縱深防禦，rc 4）。
- **成功 200**：與 `GET /sdd/fsm/{project}` 同形（凍結後重讀；含 `phase`、`escalation_history`、`escalation_provenance`、`fsm_project`），**另加** `stage`（實際採用的階段名）與 `spec_doc_digests`（映射，同 `frozen_stages[-1]`）。
- **摘要（S4 定案，ADR-016 §4.3）**：`spec_doc_digests`＝`{<相對 root 的 POSIX 路徑>: "sha256:<64 位小寫 hex>"}`；演算法＝**換行正規化後的 UTF-8 文字**（先 `\r\n`→`\n`、再 `\r`→`\n`；BOM 不剝）的 sha256，與 adapter 的 `SddSpec.digest`（＝`sha256(read_text(encoding="utf-8").encode("utf-8"))`）**逐位元相同**；不是原始 bytes（Windows 編輯器存成 CRLF 是常態，用原始 bytes 會讓每次比對假紅）。檔案必須是合法 UTF-8、單檔 ≤ 16 MiB。CLI、adapter、Bridge 三處各持一份等價的兩行實作，由對拍測試 F-6 守，不得跨子專案 import。
- **FSM 側的效果**：`current_state` 轉為 `SPEC_FROZEN`、`frozen_stages` 加一筆（`stage`、`frozen_at`、`spec_docs`、`spec_doc_digests`、`approved_by`）、`decision_trace` 加一筆（`trigger=spec_frozen`，`reason`＝`console-freeze approver=<approver>; reason=<使用者理由>`，`spec_refs`＝正規化後的 `spec_docs`）；其餘由 SDD runtime 既有行為決定（例如重試計數歸零）。
- **不做的事**：不跑 `/stage-compaction`（R-9.4 的凍結後壓縮是 SDD session 的責任）、不退回修改、不 init、不 gate、不恢復。

**(e) `POST /sdd/compile` 的 v1.5 變更（S-03、S-04、S-11、S-12、G-02、G-06；ADR-016 §6、§7.1、§8）**

| 方向 | 欄位 | 契約 |
|------|------|------|
| 請求（新，選填） | `spec_file` | 相對 `spec_dir` 的 POSIX 路徑（或 `spec_dir` 之下的絕對路徑），指定要編譯的規格檔（同一目錄有多份 TCS 時用，S-04）。`resolve()` 後須是 `spec_dir` 之下、副檔名 `.md`（不分大小寫）的**既有檔案**；**不掃描、不套官方命名規則**（呼叫端已具名）。不合 → 422 `sanitization_failed`（`violations[].field="spec_file"`）；檔不存在 → 422 `spec_not_found` |
| 請求（新，選填） | `fsm_project` | FSM 專案名（原名或標準鍵皆可，先過 (b) 的淨化鏡像）。**Bridge 行程內呼叫 adapter 一律顯式傳值**（省略時傳空字串＝明確不指定，不讀 Bridge 自己的環境）。有給＝凍結閘只認 `FSM-STATE-<鍵>.yaml`（無該檔但恰有一個檔的 `fsm_state.project` 等於輸入原名時採用它）；其餘情況 → 422 `spec_not_frozen`（`detail` 列出該目錄現有的專案鍵，**不再往上層目錄找**）。省略＝狀態目錄內恰一個狀態檔時採用它；有兩個以上而無法指認 → fail-closed 422 `spec_not_frozen`（`detail`：狀態檔不唯一，請指定專案）（G-02／S-05；ADR-016 §7.1） |
| 行為（既有） | 狀態目錄 | adapter 自 `spec_dir` 向上搜尋第一個含 `FSM-STATE-*.yaml` 的 `build/reports/fsm`；`root` 不是 compile 的參數 |
| 回應（新） | `spec_file` | 實際採用的規格檔，相對 `spec_dir` 的 POSIX 路徑 |
| 回應（既有，補述） | `spec_path` | 實際採用的規格檔的絕對路徑；Console 用它填 `sddSpecFile`、用它的父目錄填 `sddSpecDir`（ADR-016 §7.2；§6.8.6 靜默處 #7） |
| 回應（新） | `fsm_project` | 通過凍結閘的狀態檔的**標準鍵**（檔名 `FSM-STATE-<鍵>.yaml` 的 `<鍵>`；Console 用它寫回 `sddProject`） |
| 回應（新） | `frozen_digest` | `"verified"`（狀態檔有摘要且與現檔吻合）或 `"absent"`（沒有任何階段帶摘要：舊狀態檔，或凍結時沒帶 `--digest`；放行並出聲一次，Console 轉成匯入警告 `frozen_digest_absent`） |
| 回應（新） | `unmapped_at_ids` | string[]：規格**宣告位置**出現、卻**沒有被編成 step** 的 AT 字樣，依首次出現順序去重；全部對得上＝`[]`。**欄位永遠出現**。宣告位置只有兩處：①AC 映射列（以豎線開頭、第一欄形如 `AC-…` 的表格列）的第三欄第一個寬鬆 AT 字樣；②每個 `gherkin` 圍欄區塊的第一個 `# AT-…` 標頭。§3 清單表、§4 邊界表（第一欄是場景類型）與散文都不是宣告位置，所以照模板填不會讓編譯失敗；AC 映射列的 AC 與 AT 前兩段推得的 `AC-<第一段>-<第二段>` 不一致者視為未編成。有值時仍回 **200**（D-115-16：是否阻擋由消費者決定，Console 轉成匯入警告，§3.3.2；`sdd_compile` CLI 則 rc 6 且不寫輸出檔，D-115-09） |
| 回應（新） | `warnings` | `[{code, detail}]`，選填。專案根是 git 工作樹而 `build/reports/fsm/` **未被忽略**時帶 `state_dir_not_ignored`（以 `git -C <根> check-ignore -q -- build/reports/fsm/FSM-STATE-x.yaml` 判定：rc 0 已忽略、1 未忽略、128 非 git 樹則略過）；只警告不擋 |
| 回應（補述） | `spec_format_version` | 既有欄位。宣告＝**行首**（容許 `>`、`*`、`_`、反引號、`-`、空白的裝飾）的 `spec-format-version`，值＝同行第一個 `\d+\.\d+`；行內散文提及不算宣告；缺欄＝預設 `1.0`；宣告卻解析不出值（例 `tbd`）→ 拒絕；不在支援集（現為 `1.0`）→ 422 `spec_format_version_unsupported`（S-11）。自 v1.5 起 Console 讀它（§3.3.2） |
| 回應（補述） | `scenario` | 既有欄位：行首的 `**scenario**:`（或 `場景:`，半／全形冒號）宣告優先，值須屬 10 個場景之一，否則 422 `spec_ambiguous`；沒有宣告才退回既有的內文啟發式（沿用既有 step_id，另出聲 `sdd.scenario_inferred`）（S-12） |
| AT 文法 | — | `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`（整串全比對、區分大小寫；D-115-16）：**前兩段數字＝所屬 AC**（`AT-001-12-3-a` 屬 `AC-001-12`），第三段起的英數尾綴不影響歸屬；`step_id`＝`sdd-<scenario>-<at id 小寫>`。模板 §4 的 `AT-{NNN}-E-n` 因第二段不是數字而**不可編譯**；要由 AutoClaude 執行的邊界／錯誤 AT 須命名為 `AT-{NNN}-{Y}-E-{n}` 並列入 §1（ADR-016 §8.1；模板不改，D-115-09） |
| 行為（新） | 凍結內容綁定 | 狀態檔的 `frozen_stages[*].spec_doc_digests` 有該規格檔的摘要時，與現檔摘要比對，**不符 → 409 `spec_digest_changed`**（`detail={"pair":"frozen_vs_file","doc":…,"frozen_digest":…,"current_digest":…}`；D-115-16 後「內容與凍結時不同」在三個預檢點一律 409，不是 422）；規格檔不在任何階段的清單內 → 422 `spec_not_frozen`；舊狀態檔沒有摘要＝維持 v1.4 行為（只驗「有凍結」）並出聲一次（`frozen_digest="absent"`，G-06）。摘要的取用：全部階段的 `spec_doc_digests` 取**聯集**（同一鍵在多個階段出現時，後一階段勝出）；以「規格檔絕對路徑的尾段等於某個鍵」比對，**不依賴專案根的絕對路徑**（Docker 與主機路徑不同也成立） |

**(f) `GET /autoclaude/runs/{id}/rtm`　追溯覆蓋（唯讀；G-05）**

- **來源**：該 run 工作區 `engine/checkpoints/rtm/` 下的 `RTM-COVERAGE-<project>.yaml`（引擎 `RtmWritebackPlugin` 在 run **正常走完**時寫入；glob `RTM-COVERAGE-*.yaml`，多份取修改時間最新者；`.jsonl` 歷史檔不讀）。**不需權杖**（唯讀）。
- **成功 200**：

```json
{ "scenario":"greenfield", "spec_digest":"sha256:…",
  "at":{ "passed":4, "total":4, "unmapped":0, "pct":100.0 },
  "ac":{ "covered":2, "total":2, "pct":100.0 },
  "failed_at_ids":[], "weak_regex_at_ids":[], "unmapped_at_ids":[], "fully_covered":true, "advisory":true }
```

  欄位取自 YAML：`scenario`、`spec_digest`、`summary.passed_at`／`total_at`／`unmapped_at`／`at_coverage_pct`、`summary.covered_ac`／`total_ac`／`ac_coverage_pct`、`failed_at_ids`、`weak_regex_at_ids`、頂層 `unmapped_at_ids`、`summary.fully_covered`；舊報告缺 `unmapped_at`／`unmapped_at_ids` 時視為 0／`[]`；`advisory` **恆為 `true`**（Bridge 自己加，不來自檔案）。逆向歸屬規則（ADR-016 §8.5）：還原不出 AC 的 AT（字串以 `AT-` 開頭卻不過文法）**仍計入** `total_at`、依完成與否計入 `passed_at`／`failed_at_ids`，但**不進任何 AC 桶**，並列入 `unmapped_at_ids`；`fully_covered` 在 `unmapped_at_ids` 非空時為 `false`。
- **錯誤**：run 不存在 → 404 `run_not_found`（既有）；沒有報告檔（沒有啟用 SDD 治理、run 尚未結束、run 不是正常走完——引擎只在正常走完時寫報告）→ **404** `{"code":404,"reason":"rtm_not_found","run_id":"…"}`；YAML 壞掉、不是映射、缺 `summary` → **422** `{"code":422,"reason":"rtm_unreadable","detail":"…"}`。

**(g) 部署備註**：①`root` 底下的 `build/reports/fsm` 必須對 Bridge 行程可寫（Docker 下專案目錄須是可寫掛載；專案根唯讀掛載時 `:freeze` 與批次同步因 CLI 寫狀態檔失敗而回 502 `sdd_cli_failed`）；SDD 本身仍可唯讀掛載，由 CLI 的固定環境（遙測旗標＝0、不寫 `__pycache__`）避免寫入版本目錄（〔未驗〕容器級，ADR-016 §14.1）。②使用者專案根須把 `build/reports/` 加進 `.gitignore`（FSM 狀態檔是執行期產物，不入庫）：`/sdd/compile` 偵測到未忽略時回 `warnings[state_dir_not_ignored]`；Console 另在專案詳情的「SDD 治理」區以靜態提示提醒（§4.7.1）。③寫入權杖是 backend 與 Bridge 共用的祕密：compose 對 backend 與 engine-bridge 兩個服務都傳 `BRIDGE_SDD_WRITE_TOKEN: ${BRIDGE_SDD_WRITE_TOKEN:-}`（預設空＝停用；SDD 是選用引擎，不像 `JWT_SECRET` 設成必填），`.env.example` 只放 `<YOUR_BRIDGE_SDD_WRITE_TOKEN_MIN_32_CHARS>` 佔位，**repo 內不放任何真值**。

#### 3.1.5 `phase` 對映表（v1.5；G-13；W4 dogfood 標的 T-G 的規格輪廓）

> 本小節是 W4 dogfood（D-115-08）的標的規格：Bridge 純函式「FSM `current_state` → 階段／阻塞／觀測旗標」。階段分組由本契約依 SDD LATEST 的 `transition_rules.py`（`_HAPPY_PATH` 主路徑、`OBSERVATION_STATES`）與 `FSMRuntime._BLOCKING_STATES` 定義；QA 據此寫 TCS（Gherkin 的 Then 須含引號字面值，使驗收 regex 可推導、避免 `weak_regex`）。函式輸入只有 `current_state`（任何型別），輸出恆為下列形狀之一，**不拋例外**。

輸出 `SddFsmPhase{name, order, blocking, observation}`；判定順序（先命中者勝）：

1. `current_state` 不是字串、為空白、或不在本表任何一格 → `{name:"UNKNOWN", order:0, blocking:false, observation:false}`。
2. 阻塞狀態（`ESCALATION`、`ESCALATION_FINAL`、`TERMINATED`、`TOKEN_BUDGET_CRITICAL`；＝SDD `_BLOCKING_STATES`）→ `{name:"BLOCKED", order:0, blocking:true, observation:false}`。
3. 觀測狀態（＝SDD `OBSERVATION_STATES`，現況 15 個）→ `observation:true`、`blocking:false`；`name`／`order` 取「回歸階段」（下表第二張）；回歸點只能由執行期的 `resume_state` 決定者 → `name:"OBSERVATION"`、`order:0`。
4. 過渡狀態（`AUTO_COMPACT_PENDING`、`AUTO_RECOVERY_ATTEMPT`、`RESUME_VERIFICATION`）→ `{name:"TRANSIENT", order:0, blocking:false, observation:false}`。
5. 其餘（主路徑）→ 下表第一張的階段，`blocking:false`、`observation:false`。

主路徑階段（`order` 沿主路徑單調不減；相鄰兩個階段差 1）：

| `order` | `name` | 中文標籤 | 包含的 `current_state` |
|:---:|--------|----------|------------------------|
| 1 | `INTAKE` | 立案 | `INIT`、`SCENARIO_DETECT`、`AGENT_LOAD`、`INTENT_DECOMPOSITION`、`BACKLOG_PRIORITIZED` |
| 2 | `SPECIFICATION` | 規格撰寫 | `SPEC_DRAFTING`、`SCG_VALIDATION` |
| 3 | `HUMAN_GATE` | 人工確認 | `HUMAN_PENDING`、`REMINDER`、`SPEC_REGRESSION_CHECK` |
| 4 | `FROZEN` | 規格凍結 | `SPEC_FROZEN`、`TEST_CONTRACT_NEGOTIATED` |
| 5 | `IMPLEMENTATION` | 實作 | `IMPLEMENTATION`、`SANDBOX_HARDENING_GATE`、`EXECUTION_EVALUATION`、`ADVERSARIAL_EVALUATION` |
| 6 | `REVIEW` | 審查 | `PR_REVIEW`、`SPEC_AUDIT` |
| 7 | `VERIFICATION` | 追溯驗證 | `RTM_VERIFY` |
| 8 | `RELEASE` | 發布 | `RELEASE_READY`、`RELEASE` |

非主路徑的 `name`（`order` 一律 0）：`BLOCKED`（阻塞）、`TRANSIENT`（過渡中）、`OBSERVATION`（觀測中，回歸點未定）、`UNKNOWN`（未知）；前端的中文標籤字典見 §4.7.3。

觀測狀態的回歸階段：

| 觀測狀態 | 回歸階段（`name`／`order`） |
|----------|----------------------------|
| `AUTOCLAUDE_DELEGATED`、`EVALUATOR_AUDIT` | `IMPLEMENTATION`／5 |
| `SPEC_DEBATE` | `SPECIFICATION`／2 |
| `SPEC_PATCH_PROPOSAL`、`EXPERIMENT_REPLAY` | `REVIEW`／6 |
| `PRODUCTION_SIGNAL`、`LEARNING_COMMIT`、`SCAFFOLD_GC`、`MEMORY_CONSOLIDATION`、`PRODUCTION_BEHAVIORAL_SIGNAL`、`CAPABILITY_BENCHMARK` | `RELEASE`／8 |
| `HUB_SYNC`、`TRAJECTORY_PREDICTED`、`DRIFT_OBSERVATION`、`MONITOR_VIOLATION` | `OBSERVATION`／0（回歸點不可由狀態字串靜態判定） |

涵蓋範圍：`_HAPPY_PATH` 的全部鍵（W115-SA 現查共 43 個：主路徑 21、觀測 15、阻塞 4、過渡 3；§6.8.2 E6）都有對映；SDD 日後新增狀態而本表沒有對映時，對拍測試 F-5 變紅（而不是靜默落到 `UNKNOWN`）。

T-G 的 AC 輪廓（給 QA 寫 TCS；全部 Unit）：AC-001-1 主路徑各狀態回上表階段、`order` 沿主路徑單調不減（2 個 AT：`INIT`～`HUMAN_PENDING`、`SPEC_FROZEN`～`RELEASE`）；AC-001-2 觀測態 `observation=true`、`blocking=false`，`name`／`order` 為回歸階段（例：`AUTOCLAUDE_DELEGATED`→`IMPLEMENTATION`／5；`HUB_SYNC`→`OBSERVATION`／0）；AC-001-3 阻塞態 `blocking=true`、`observation=false`、`name=BLOCKED`、`order=0`；AC-001-4 容錯：未知字串、`None`、整數、列表、字典、空字串、前後有空白的合法狀態名一律 `UNKNOWN`／0 且不拋例外（2 個 AT）；AC-001-5 過渡態回 `TRANSIENT`／0。約 7 個 AT。

#### 3.1.6 SDD 批次：`sdd` 區塊、預檢與 FSM 同步（D-115-04、D-115-06、D-115-10、D-115-15；已與 ADR-016 §6.3、§7.3、§10 對齊）

**`sdd` 區塊**（`POST /autoclaude/runs` 的頂層選填欄位，`RunCreateIn.sdd`；與 `playbook` 同層，不在 `playbook` 內；欄位語意取 ADR-016 §7.3）：

| 欄位 | 型別 | 必填 | 規則 |
|------|------|:----:|------|
| `spec_dir` | string | ✅ | 絕對路徑，`check_path`（`BRIDGE_ALLOWED_PATH_ROOTS`）；須在 `root` 之下（否則 422 `sdd_block_invalid`） |
| `spec_file` | string | — | 相對 `spec_dir`，或絕對路徑但須在 `spec_dir` 之下；`spec_dir` 內有多份 TCS 時必填；其餘規則同 §3.1.4 (e) |
| `fsm_project` | string | ✅ | 原名或標準鍵皆可，Bridge 一律先過淨化鏡像（§3.1.4 (b)） |
| `root` | string | — | 專案根，預設＝請求的 `execution_path`；`check_path`；`spec_dir` 必須在其內；FSM 狀態目錄＝`<root>/build/reports/fsm` |
| `approver` | string | — | 簽核人：1～100 字元、無控制字元、不含 `;`（否則 422 `sdd_invalid_argument`）；省略＝`console`（服務身分，稽核上一眼可辨不是具名人，不假裝有人簽）；Backend 永遠送具名人（§1.10.6） |

- `PlaybookIn.workflow_type` 仍只收 `auto`、`PlaybookIn` 仍 `extra=forbid`：**外部契約不開 `workflow_*`**。有 `sdd` 時由 Bridge **伺服端**在寫 `playbook.yaml` 時覆寫 `workflow_type=aisdlc_sdd`、`workflow_path`＝**已驗證的 realpath**（有 `spec_file` 用該檔案路徑、否則用 `spec_dir`；引擎 PRE_RUN 的 `load_spec(workflow_path)` 把檔案路徑視為 `spec_file`，port 簽名不改，ADR-016 §8.3）；引擎子行程環境**只有** `SDD_PROJECT=<專案鍵>`（先剝除繼承自 Bridge 的 `SDD_*`，§3.1.4 共通規則 2）。沒有 `sdd` 的請求行為與 v1.4 完全相同（不需要權杖）。
- `RunRecord` 增選填 `sdd`（`spec_dir`、`spec_file`、`fsm_project`、`root`、`state_dir`、`approver`、同步結果）；`resume`／`restore` 的重驗與回收判定都從它取值，舊 `run.json` 缺欄走預設、`schema_version` 不變；除 `approver` 與 `fsm_project` 之外不含任何機密。

**預檢順序**（固定，QA 依序斷言；全部通過前不取鎖、不寫 FSM、不 spawn；ADR-016 §6.3、§10.2）：

| # | 檢查 | HTTP | reason | 附加欄位 |
|---|------|------|--------|----------|
| 0 | 本文格式（既有） | 422 | `invalid_request` | `violations[]` |
| 1 | 權杖（Bridge 沒設／標頭缺漏或不符） | 503／403 | `sdd_write_disabled`／`sdd_write_forbidden` | — |
| 2 | 區塊與路徑閘：`root`、`spec_dir`、`spec_file` 過 `check_path`；`fsm_project` 先淨化；`approver` 值域 | 422 | 路徑不合 `sanitization_failed`（`violations[].field` 為 `sdd.root`、`sdd.spec_dir`、`sdd.spec_file`）；`spec_dir` 不在 `root` 之下 `sdd_block_invalid`；`approver` 不合 `sdd_invalid_argument` | `violations[]`／`detail` |
| 3 | 凍結與規格檢查（同 `/sdd/compile` 的 adapter、`fsm_project`、`spec_file`；「執行前」那一點的凍結＝現檔） | 422／409 | `spec_not_frozen`、`spec_tainted`、`spec_format_version_unsupported`、`spec_not_found`、`spec_ambiguous`；內容不符＝**409** `spec_digest_changed` | `detail`；409 的 `detail={pair:"frozen_vs_file", doc, frozen_digest, current_digest}` |
| 4 | **匯入摘要**：playbook 各任務的 `spec_digest`（匯入時存下的值）必須恰為現檔摘要這一個值 | 409／422 | `spec_digest_changed`；任務完全沒有 `spec_digest`＝`sdd_block_invalid`（Backend bug） | 409 的 `detail={pair:"import_vs_file", doc, import_digest, current_digest}` |
| 5 | FSM 狀態（**唯讀**讀取）依下方預檢表處置 | 409／404 | `fsm_state_conflict`／`fsm_not_found` | `detail`（見預檢表與回收點） |
| — | 之後才是既有的取鎖（409 `advisory_lock_held`）→ **FSM 寫入** → `_materialize` → spawn | | | |

- 第 3 項「凍結摘要缺」（舊狀態檔，或凍結時沒帶 `--digest`；`frozen_digest="absent"`）→ 放行，並在 Bridge 回的 201 帶 `warnings:[{code:"sdd_frozen_digest_absent", detail}]`（不靜默；Backend 原樣轉入 Console 的 201 `warnings[]`，§1.10.6）。摘要的演算法與值格式見 §3.1.4 (d)：CLI、adapter、現檔重算三處必須是同一個演算法，否則 CRLF 檔會假性不符（對拍測試 F-6）。
- 三個預檢點的錯誤對映一致（ADR-016 §6.3）：①`:freeze` 的 `expected_digests`、②`/sdd/compile`、③執行前——「內容與凍結（或核准人看過的版本）不同」一律 **409 `spec_digest_changed`**，「未凍結、狀態檔缺、規格檔不在凍結清單」一律 **422 `spec_not_frozen`**。

**FSM 同步**（寫入全部經 CLI，動詞與 `--reason` 見下表；順序與條件如下）：

1. **FSM 寫入在 `_materialize` 之前、取鎖之後**（失敗時才不會留下半成品 run 目錄——否則 `reconcile` 下次啟動會把它當「活躍而無行程」的孤兒標成 FAILED）。依預檢表：

| FSM 現況 | 處置 | 備註 |
|----------|------|------|
| `IMPLEMENTATION` | `delegate-enter` | 常態 |
| `AUTOCLAUDE_DELEGATED` | 回收點（第 3 點）：所引用的 run 已終態或不存在 ⇒ `delegate-exit done`（RECLAIMED）→ `delegate-enter`；仍活著或外來委派 ⇒ 409 `fsm_state_conflict` | 回收也是 FSM 寫入，在鎖內做 |
| `TEST_CONTRACT_NEGOTIATED` | `negotiate-exit agreed` → `delegate-enter` | 上次 enter 後 exit 前中斷的自癒（C-4） |
| `SPEC_FROZEN` | `negotiate-enter` → `negotiate-exit agreed` → `delegate-enter` | 首次批次 |
| 其他（含 `HUMAN_PENDING`、`ESCALATION`、`ESCALATION_FINAL`） | 409 `fsm_state_conflict`，`detail.current_state` 帶回 | `ESCALATION` 的出路見 §3.1.7 第 1 點 |
| 狀態檔不存在 | 404 `fsm_not_found` | Bridge 不 init |

   `--reason` 的固定組字（ADR-016 §4.4；稽核三處的對上靠它；格式為 `console-` 開頭、`key=value` 以 `; ` 分隔）：

| 動詞 | `--reason`（與其他旗標） |
|------|--------------------------|
| `negotiate-enter` | `console-signoff approver=<approver>; run=<run_id>`；`--contract-ref`＝TCS 相對路徑 |
| `negotiate-exit --outcome agreed` | `console-signoff approver=<approver>; oracle=<TCS 相對路徑>@<sha256:…>; basis=import-draft-signoff; r9.20.3=not-satisfied` |
| `delegate-enter` | `console-run run=<run_id> START`；`--playbook-ref run:<run_id>`（`run:` 前綴讓回收規則只認 Bridge 簽發的值） |
| `delegate-exit --decision done` | `console-run run=<id> COMPLETED`／`console-run run=<id> CANCELLED`／`console-run run=<舊 id> RECLAIMED old_status=<舊終態或 missing> by=<新 id>`／`console-run run=<id> SPAWN-FAILED delegation not started` |
| `delegate-exit --decision failed` | `console-run run=<id> ENGINE-ESCALATION step=<step_id>: <detail>`（`detail` 取前 200 字、換行與控制字元換成空格） |

2. **談判閘對映（D-115-10；ADR-016 §5.2 裁決：接受「Console 簽核匯入草稿＝談判 `agreed`」，附四條件）**：C-1 只在 Bridge 收到**帶有效權杖**且含 `sdd` 區塊的請求時執行，簽署人＝`sdd.approver`；C-2 憑證的誠實條款寫進 `negotiate-exit` 的 reason（`r9.20.3=not-satisfied`：稽核者讀到的是「人簽了這份 oracle、獨立性條款未滿足」，不是假裝完整談判）；C-3 真正的閘仍是 SCG-4 的獨立審查，RTM 面板一律標「諮詢視圖」，本契約**不宣稱** R-9.20.3 已滿足；C-4 enter 與 exit 在同一個 Bridge 請求內背靠背，中間失敗留在 `TEST_CONTRACT_NEGOTIATED`，由預檢表自癒。Bridge **不**呼叫 `negotiate-exit underspecified`（Console 沒有「退回修改」）。
3. **回收點（D-115-15；ADR-016 §10.3）**：FSM 可能留在 `AUTOCLAUDE_DELEGATED` 而沒有任何行程（引擎異常結束、額度停機、孤兒、Bridge 關閉都「不動」）；回收點讓**新批次**自己解開陳舊委派，且只在確認「舊 run 已不在跑」時才動手。🔴 判斷只在 `current_state=AUTOCLAUDE_DELEGATED` 時才讀 `autoclaude_delegated_tracking.playbook_ref`（tracking 在 exit 後**不清除**，在 `IMPLEMENTATION` 上是歷史殘留欄）。判定依序：

| # | 條件 | 處置 |
|---|------|------|
| 1 | `playbook_ref` 缺，或不以 `run:` 開頭（外來委派：人在 SDD session 進入的） | 409 `fsm_state_conflict`，`detail={current_state, reason:"foreign_delegation"}`；Bridge **不碰**——解卡由人在 SDD session `delegate-exit` |
| 2 | 解出 `run_id` 後，Bridge 的 run 登錄（含重啟後由 `run.json` 還原的）**查無此 run** | 視為不存在 ⇒ 回收 |
| 3 | 該 run 存在，但其 `sdd.state_dir` 或 `sdd.fsm_project` 與本次不同 | 視為外來，同第 1 項 409 |
| 4 | 該 run 為**活躍**（`INITIALIZING`／`RUNNING`／`PAUSING`／`PAUSED`／`CANCELLING`） | 409 `fsm_state_conflict`，`detail={current_state, run_id, run_status}`（同一個 Console 專案與路徑另由 advisory lock 先回 409；**不同** Console 專案指向同一個 `(狀態目錄, fsm_project)` 由這一條回 409，Backend 的部分唯一索引是第一道） |
| 5 | 該 run 為**終態**（`COMPLETED`／`FAILED`／`CANCELLED`） | 回收 |

   **回收**＝鎖內依序 `delegate-exit --decision done`（reason `…RECLAIMED…`）→ `delegate-enter`（`--playbook-ref run:<新 id>`）；兩步之間 `delegate-enter` 失敗 ⇒ FSM 停在 `IMPLEMENTATION`（無委派）、本次建立回 409／5xx 並不 spawn，下次建立從 `IMPLEMENTATION` 常態進入，不需人工。回收在 Bridge 稽核記一筆（含舊 run id 與舊終態）。回收只對 `AUTOCLAUDE_DELEGATED` 成立：`ESCALATION` 只有人能解（`delegate-exit` 在 `ESCALATION` 回 rc 3）。
4. **補償**：從 FSM 寫入成功起，到引擎行程確認啟動之前的任何失敗（`_materialize` 例外、`spawn_failed`…），Bridge 必須補償——以 `done` 離開委派（`AUTOCLAUDE_DELEGATED`→`IMPLEMENTATION`，reason 見上表 `SPAWN-FAILED`）；**不得**用 `failed` 離開，那會進阻塞態 `ESCALATION`，不可把基礎設施故障映成它。補償本身失敗只記 ERROR 與 alert `SDD_FSM_SYNC_FAILED`，不改變對呼叫端的錯誤回應。談判已完成而進入委派失敗＝FSM 停在 `IMPLEMENTATION`（已談判），重試安全。
5. **終態同步**（run 監督執行緒在 `_finalize` 寫完終態之後，狀態事件先發布，**在 `handle.lock` 之外**才呼叫 CLI；只對帶 `sdd` 建立的 run；ADR-016 §10.1）。🔴 `delegate-exit --decision done` 的語意是「**委派交還控制權、未升級**」，不是「成功」：run 是否成功由後續閘門判（SCG-4 審查、RTM 面板），FSM 不替它背書；所以完成與使用者取消都是 `done`，只有引擎升級型失敗是 `failed`：

| 事件 | 判定（`runner.py` 實際分支） | FSM 動作 | FSM 結果 |
|------|------------------------------|----------|----------|
| `COMPLETED` | 最終狀態 `COMPLETED` | `delegate-exit done`（`… COMPLETED`） | `IMPLEMENTATION` |
| `CANCELLED`（使用者取消，非孤兒；含 `PAUSED` 時直接收尾） | 最終狀態 `CANCELLED` | `delegate-exit done`（`… CANCELLED`；D-115-15 修訂 D-115-10 的「不動」） | `IMPLEMENTATION`（之後可再委派） |
| `FAILED`·引擎升級型 | `reason` 以 `引擎升級（ESCALATION）` 開頭，亦即 `runner.py` 的 `_escalation` 非空 | `delegate-exit failed`（`… ENGINE-ESCALATION step=…`） | `ESCALATION`（FSM 自己寫 `escalation_history`，`source=autoclaude_delegated_failed`；`autoclaude_delegated_tracking.playbook_ref` 仍指出是哪個 run） |
| `FAILED`·額度或 token 停機 | `_failure_reason` 的 halted 分支、無 `_escalation` | **不動**（基礎設施故障不得映成阻塞態） | 維持 `AUTOCLAUDE_DELEGATED`（留給回收點） |
| `FAILED`·引擎異常結束、被訊號終止、Bridge 關閉 | 同上，無 `_escalation` | **不動** | 維持 `AUTOCLAUDE_DELEGATED`（留給回收點） |
| `FAILED`／`CANCELLED`·孤兒（Bridge 重啟後 `reconcile`） | 不論被標成 `FAILED` 或 `CANCELLED` | **不動** | 維持 `AUTOCLAUDE_DELEGATED`（留給回收點） |
| `FAILED`·spawn 失敗 | `_spawn` 的 `OSError` | 補償 `delegate-exit done`（`… SPAWN-FAILED delegation not started`） | `IMPLEMENTATION` |
| `PAUSED`（非終態） | — | **不動** | 維持 `AUTOCLAUDE_DELEGATED`；`resume` 沿用同一個委派 |

   終態事件到「FSM 回到 `IMPLEMENTATION`」之間有約 0.1 秒（暖機）視窗：**四源對拍必須輪詢到 FSM 離開 `AUTOCLAUDE_DELEGATED`（上限 30 秒）再比，不得單次讀取**（E2E-17 第 15 列）。
6. **exit 的容錯與 alert**：`delegate-exit` 回 rc 3（FSM 已不在 `AUTOCLAUDE_DELEGATED`，例如人工已處理）⇒ 視為「已就位」，記 alert `{level:"warning", code:"SDD_SYNC_STATE_DRIFT"}`、不失敗；其他非零 ⇒ 記 alert `{level:"error", code:"SDD_FSM_SYNC_FAILED"}` 與稽核，並把 `{exit, ok:false, error}` 寫進 run 紀錄，FSM 留在原態（由回收點或人工處理）；同步動作失敗**不改 run 狀態、不重試**。這幾個 alert 與其他 Bridge 告警一樣經 SSE 轉發，不另存成 Console 告警（§3.7、D-17 的「其餘 Bridge 告警只轉發」）。
7. **`resume`／`restore`（SDD run）**：先重跑預檢第 3、4 項（凍結＝現檔、匯入摘要＝現檔；任務摘要取自該 run 工作區已存的 `playbook.yaml`）；FSM 為 `AUTOCLAUDE_DELEGATED` 且 `playbook_ref` 就是本 run（`run:<本 id>`）⇒ 直接續；引用別的 run 或外來委派 ⇒ 409（回收點第 1、3、4 項）；為 `IMPLEMENTATION` ⇒ `delegate-enter` 重進（`playbook_ref` 仍用本 run 的 id）；其他（含 `ESCALATION`）⇒ **409 `fsm_state_conflict` 並不 spawn**。審核決定（`SKIP`／`RETRY`）開的後續批次走建立流程，與 execute 相同。被回收的舊 run 若是可 `restore` 的終態（額度停機的 `FAILED`、取消後的 `CANCELLED`），之後 `:restore` 走本點的 `IMPLEMENTATION`⇒`delegate-enter` 一列，與新批次不衝突（新批次仍在跑時 `restore` 會因回收點第 4 項得 409）。**權杖**：SDD run 的 `:resume`／`/restore` 也須帶 `X-Bridge-Token`（D-115-18；§3.1.4 共通規則 2），檢查在上述預檢之前；缺／錯回 503／403，不 spawn、FSM 不動。

**建立流程順序**（ADR-016 §10.2）：

```
create(req 含 sdd):
 1  既有驗證＋sdd 唯讀預檢（上表 0～5）                      → 4xx，零副作用
 2  取得 advisory lock（既有）
 3  FSM 寫入（依預檢表）                                    → rc≠0：釋放鎖、回 409／5xx，尚無任何工作區產物
 4  _materialize（既有）                                    → 例外：補償 delegate-exit done ＋釋放鎖
 5  start／_spawn（既有）                                   → spawn 失敗：補償 delegate-exit done
 6  終態：狀態事件先發布，之後（handle.lock 之外）才呼叫 delegate-exit
```

#### 3.1.7 已知邊界（誠實劃界；不是待修缺陷）

1. **`ESCALATION` 只有人能解，Console 沒有恢復動詞**（D-115-15；ADR-016 §5.3）：引擎升級型失敗會讓 FSM 進 `ESCALATION`（阻塞態；R-9.5、絕對禁令第 6 條：必須等人工）。恢復**留在 SDD session**：`resume-from-escalation --to IMPLEMENTATION --project <鍵> --reason "<人工原因>"`（`GET /sdd/fsm/{project}` 在 `ESCALATION`／`ESCALATION_FINAL` 時多回 `recovery`，Console 顯示可複製的指令）；恢復後 FSM 回 `IMPLEMENTATION`、歷史回填 `resolved_at`，**下一個 Console 批次可直接啟動**。恢復前新的 SDD 批次一律 409 `sdd_fsm_state_conflict`（`details.currentState="ESCALATION"`）。判斷「有未解的委派失敗」只能用「`currentState` 屬 `ESCALATION`／`ESCALATION_FINAL`，且 `escalationHistory` 末筆 `resolved_at` 為空」——`escalation_provenance` 與 `autoclaude_delegated_tracking` 在恢復後**不會被清除**，只看它們在不在，會在 `IMPLEMENTATION` 上顯示過期的失敗。**停在委派態的其餘情形**（取消除外：取消走 `done`；額度停機、異常結束、孤兒、Bridge 關閉）由**新批次的回收點**自動解開（§3.1.6 第 3 點）；外來委派（人在 SDD session 進入的）與仍活躍的 run 則 409，解卡由人處理。
2. **`restore`／`resume` 會重驗，但沒有 Console 解卡動詞**（§3.1.6 第 7 點）：已 `COMPLETED` 的批次 `restore` 時，FSM 是 `IMPLEMENTATION`，Bridge 會重新 `delegate-enter`；若 FSM 在 `ESCALATION` 或被別的 run／外來委派佔用則 409 並不 spawn。要讓 FSM 軌跡乾淨地反映新一輪，建議另開新批次而不是 restore。
3. **一個 FSM 專案只對應一個未刪除的 Console 專案**（D-115-14；部分唯一索引，§0.5 V12）：同一個 `(executionPath, sddProject)` 不能被兩個專案認領；Bridge 側的縱深是回收點第 4 項（不同 Console 專案指向同一個 `(狀態目錄, fsm_project)` 且對方的 run 仍活躍 ⇒ 409）。Bridge 的 advisory lock 以「專案名＋路徑」為鍵，兩個專案名不同不會互擋，所以不能靠它。
4. **談判閘的語意落差**（D-115-10；ADR-016 §5.2）：R-9.20.3 要求 oracle 對 Generator 不可見，AutoClaude 路徑上測試與實作由同一個 AI 寫，此條件**結構上不成立**；本契約把「Console 簽核＝談判同意」當作人工背書，並把 `r9.20.3=not-satisfied` 寫進 `negotiate-exit` 的 reason，不當作 oracle 獨立性的證明。
5. **RTM 與 AT 文法**：正向 `unmapped_at_ids`（規格宣告位置出現卻沒編成步驟；Bridge `/sdd/compile` 回應、Console 轉警告）與逆向 `unmappedAtIds`（已編成的 AT 還原後無法歸屬 AC；RTM 回應）是**兩個不同層的欄位**；文法與歸屬規則見 §3.1.4 (e)、(f)（ADR-016 §8）。舊規格若用兩位首段（`AT-14-…`）或字母第二段（`AT-001-E-1`），其 AT 會列入 `unmapped_at_ids`（可執行的邊界／錯誤 AT 須命名為 `AT-{NNN}-{Y}-E-{n}`）。
6. **`spec_doc_digests` 只有凍結當下的文件清單**：凍結後新增的規格檔不在其內；預檢只比對 `spec_file`（或 adapter 選定的檔）。
7. **評估指令的鑑別力**（整合輪 115 §5.1-2）：`pytest -k AT_x` 只證「有測試且綠」；RTM 一律標諮詢，SCG-4 的人工審查才是真閘。
8. **權杖只封住 Bridge 的 HTTP 寫入面**（ADR-016 §9 劃界）：引擎子行程內的 AI 步驟仍可自己執行框架的 FSM CLI（框架程式碼對它可讀）。縱深在於：不注入 `SDD_STATE_DIR`；批次期間 FSM 在 `IMPLEMENTATION`／`AUTOCLAUDE_DELEGATED`，`spec-frozen` 轉態不合法；凍結綁內容，竄改規格可偵測。**不防禦主動對抗的 AI**，與 Bridge 無認證的既有限制（Architecture §12 L-6）同級。
9. **跨行程競態**（ADR-016 §3.5）：FSM 狀態檔 load-modify-save 沒有跨行程鎖（只有 `os.replace` 原子）；Bridge 只在 spawn 與終態各呼叫一次、且行程內序列化，預期近零，但 SDD session 與 Bridge 同時寫＝競態（再開症狀：觀測到 `escalation_history`／`decision_trace` 遺失）。
10. **`done` 不是「成功」**：FSM 軌跡不再區分「完成」與「取消」，靠 `decision_trace` 的 reason 字串（`COMPLETED`／`CANCELLED`）區分；成敗由後續閘門與 RTM 判（ADR-016 §14.1）。
11. **Bridge 的專案路徑只收不含 `/` 的名稱**（D-115-18 ③；ADR-016 §7.4「原名與標準鍵等價」的邊界）：`GET /sdd/fsm/{project}` 與 `POST /sdd/fsm/{project}:freeze` 的 `{project}` 是**單一路徑段**，只收淨化後的 FSM 鍵（或本來就不含 `/` 的原名，經淨化鏡像後與標準鍵等價）；含 `/` 的原名經 URL 解碼後路由不匹配，Bridge 回**沒有 `reason`** 的 404（框架預設的 `Not Found`，不是 Bridge 錯誤封包；以 Starlette TestClient 實測：`{project}` 對 `a%2Fb` 回 404，`\` 與空白不受影響）。契約**不要求** Bridge 為此改用 `{project:path}`。影響：專案名含 `/` 且 `sddProject` 仍為 NULL 時，第一次使用（核准凍結第 4 項的唯讀 GET、`GET /engines/sdd?project=`）無法由 URL 定址；Console 暫把這個 404 當「找不到狀態檔」轉譯（`GET /engines/sdd` 為 `reason="fsm_not_found"`，核准凍結為 409 `sdd_fsm_not_found`、`details.sddProject` 帶出送出的名稱），不另設錯誤碼。避開：用 `PUT /projects/{id}/sdd-binding`（§1.10.7）把 `sddProject` 設成不含 `/` 的名稱（例如淨化後的鍵），有效 FSM 專案改取它，就不會再用到含 `/` 的專案名。請求本文裡的 `fsm_project`（`/sdd/compile`、`POST /autoclaude/runs` 的 `sdd`）不受此限，Bridge 一律先淨化。

### 3.2 錯誤轉譯（Bridge → Console）

Bridge 錯誤封包一律 `{"code":<狀態>,"reason":"…",…}`；422 另帶 `violations[]`（`{field,rule,message,…}`）。

| Bridge 回應 | 發生於 | Console 回應 |
|-------------|--------|--------------|
| 409 `advisory_lock_held`＋`holder_run_id` | execute、restore | **409** `同專案同路徑已有執行中的批次`，`details={holderRunId}`（execute 另補償刪除剛建的列） |
| 409 `invalid_state`＋`{run_id,status,detail}` | pause／resume／stop／restore | **409** `目前執行狀態不允許此操作`，`details={action,runStatus,bridgeStatus}`（`bridgeStatus`＝Bridge 的 `status`） |
| 409 `no_checkpoint` | resume | **409** `找不到可續跑的 checkpoint` |
| 404 `run_not_found` | 控制類呼叫 | **409** `引擎端已無此執行（工作區可能已清除）`；`GET` 詳情改以 `bridge.runKnown=false` 表達，不報錯 |
| 404 `checkpoint_not_found` | restore | **404**（訊息 `checkpoint 不存在或不屬於此執行：<id>`） |
| 404 `draft_not_found` | approve | **409** `草案已失效，請重新解析`，`details={draftId}` |
| 409 `already_signed_off` | approve | 視為成功（冪等） |
| 422 `sanitization_failed`＋`violations[]` | execute、resume、restore | **422** `引擎拒絕此請求`，`details={bridgeReason:"sanitization_failed",violations}`（逐項原樣帶出，不改寫） |
| 422 `invalid_request`＋`violations[]` | 任何 | **422** `引擎拒絕此請求`（`bridgeReason:"invalid_request"`）；代表 console-api 組出的請求不符契約＝缺陷，另記 ERROR 日誌 |
| 422 帶 `gate`／`detail`（`max_steps`／`cycle`／`empty_prompt`／`brain_unsupported`／`brain_failed`；Bridge 還會把 `duplicate_step_id`、`dangling_dependency` 歸入 `cycle`，`empty_goal` 歸入 `empty_prompt`，`no_steps`、`brain_returned_none` 歸入 `brain_failed`） | decompose | 轉成 **422** `解析結果未通過有界閘`，`errors[]` 項目 `gate`／`detail` 取 Bridge 值（`location` 省略） |
| 422 `spec_not_frozen`／`spec_tainted`／`spec_format_version_unsupported`／`spec_not_found`／`spec_ambiguous`＋`detail` | sdd compile | **422** `SDD 規格檢查未通過`，`details={bridgeReason,detail}`（匯入探測模式下的 `spec_not_found` 例外，見 §3.3.1） |
| 500 `spawn_failed`、503 `lock_backend_unavailable`、`run_exists`（console 的 id 是新 UUID，不應發生）、其餘 5xx | execute 等 | **502** `引擎橋接服務錯誤`，`details={bridgeStatus,bridgeReason}`；execute 補償刪除 run 列（守門＝該 run 尚無 `execution_steps`，不看狀態，`spawn_failed` 時列已被 Bridge 標成 `FAILED` 仍要刪；§3.4.5，AR-15）。`/sdd/compile` 遇其餘 5xx：探測模式略過路徑 A、明示 `specDir` 時同樣 502 |
| 連線失敗（拒絕連線、DNS、連線逾時） | 任何 | **502** `引擎橋接服務無法連線` |
| 讀取逾時 | 任何 | **504** `引擎橋接服務逾時` |
| 409 `fsm_state_conflict`＋`detail{current_state, expected_state?, run_id?, run_status?, reason?}`（v1.5） | 核准凍結、帶 `sdd` 的 execute、SDD run 的 resume／restore | **409** `sdd_fsm_state_conflict`，`details={currentState, expectedState?, runId?, runStatus?, cause?}`（`expected_state` 是字串或陣列，原樣帶出；`detail.reason="foreign_delegation"`→`details.cause`；`run_id`／`run_status`→`runId`／`runStatus`）；execute 補償刪除剛建的 run 列 |
| 409 `spec_digest_changed`＋`detail{pair, doc, expected_digest?, frozen_digest?, import_digest?, current_digest}`（v1.5） | 核准凍結（`pair=expected_vs_file`）、帶 `sdd` 的 execute（預檢第 3、4 項：`frozen_vs_file`／`import_vs_file`）、SDD run 的 resume／restore | **409** `sdd_spec_digest_changed`，`details={pair, doc, expectedDigest, frozenDigest, importDigest, currentDigest}`（沒有的鍵省略）；execute 補償刪除剛建的 run 列 |
| 409 `spec_digest_changed`（v1.5；`POST /sdd/compile`） | 匯入 `parse` | **422** `SDD 規格檢查未通過`，`details={bridgeReason:"spec_digest_changed", detail:"<Bridge detail 物件的一行文字>"}`；**不得**降級成「沒有規格」而退回 LLM 路徑——探測模式同樣 fail-closed（§3.3.1、§3.3.2 第 9 點；ADR-016 §6.3 要求 `ImportParser.probeSpec` 對 409 明確丟拒絕） |
| 404 `fsm_not_found`（v1.5） | 核准凍結（第 4 項的唯讀 GET 或 CLI rc 5）、帶 `sdd` 的 execute | **409** `sdd_fsm_not_found`，`details={sddProject}`（專案存在，但那個 FSM 專案沒有狀態檔：要先在專案根的 SDD session 建立）；execute 補償刪除 |
| 422 `spec_not_frozen`／`spec_tainted`／`spec_format_version_unsupported`／`spec_not_found`／`spec_ambiguous`（v1.5） | 帶 `sdd` 的 execute（預檢第 3 項）、SDD run 的 resume／restore | **422** `SDD 規格檢查未通過`，`details={bridgeReason, detail}`（與路徑 A 同一個轉譯；§3.3.1 的「探測模式例外」只適用 `parse`）；execute 補償刪除剛建的 run 列 |
| 422 `fsm_state_unreadable`／`sanitization_failed`／`sdd_invalid_argument`／`sdd_block_invalid`（`:freeze` 的 `root`、`docs[i]`、`approver`、`reason`；帶 `sdd` 的 execute 的 `sdd.*`）（v1.5） | 核准凍結、execute | **422** `引擎拒絕此請求`，`details={bridgeReason, violations[]}`（逐項原樣帶出；Bridge 沒給 `violations` 時為 `[]`，並加 `details.detail`＝Bridge 的 `detail` 文字） |
| 503 `sdd_write_disabled`（v1.5） | 核准凍結、帶 `sdd` 的 execute、SDD run 的 resume／restore（D-115-18） | **503** `sdd_write_disabled`（無 `details`）；execute 並補償刪除剛建的 run 列；resume／restore 不改 run 與 DB 狀態 |
| 403 `sdd_write_forbidden`（v1.5） | 核准凍結、帶 `sdd` 的 execute、SDD run 的 resume／restore（D-115-18） | **502** `引擎橋接服務錯誤`，`details={bridgeStatus:403, bridgeReason:"sdd_write_forbidden"}`；另記 ERROR 日誌（兩端的權杖設定不一致，是設定缺陷不是使用者錯誤） |
| 500 `sdd_cli_usage`、502 `sdd_cli_failed`、504 `sdd_cli_timeout`（v1.5） | 核准凍結、帶 `sdd` 的 execute、SDD run 的 resume／restore | 落在上方「其餘 5xx → 502 `引擎橋接服務錯誤`」那一列（`details.bridgeStatus`、`details.bridgeReason`）；execute 補償刪除。（Bridge 回的 504 是 HTTP 回應，不是連線讀取逾時，所以不走「讀取逾時 → 504」那一列） |
| 404 `rtm_not_found`、404 `run_not_found`（v1.5；rtm 端點） | `GET /executions/{runId}/rtm` | **404** `rtm_not_found`，`details={runId}`（本端點的 `run_not_found` 不走上方控制類呼叫的 409 對映：批次是否存在以資料庫為準，Bridge 端沒有就是沒有報告） |
| 422 `rtm_unreadable`（v1.5） | `GET /executions/{runId}/rtm` | **422** `引擎拒絕此請求`，`details={bridgeReason:"rtm_unreadable", violations:[]}` |
| 422 `sanitization_failed`（`GET /sdd/fsm*` 的 `root`；v1.5） | `GET /engines/sdd?projectId=` | **200**＋`available=true`、`reason="sdd_root_rejected"`（回應欄位，不是錯誤；§1.10.4） |

### 3.3 匯入：三條解析路徑

#### 3.3.1 路徑選擇（`POST /import/{id}/parse`；依序，先符合者勝）

1. **明示 `specDir`**（非空白）→ **路徑 A**。任何 Bridge 失敗都報錯（含 `spec_not_found`）。
2. **探測 `executionPath`**：`POST /sdd/compile {spec_dir: executionPath}`（`sdd.engineUrl`）。
   - 200 → **路徑 A**。
   - 422 `spec_not_found`，或 422 `sanitization_failed`（路徑不存在／不在 allowlist 內；匯入階段的探測不因此擋下，執行階段才由 Bridge 把關）→ 視為「沒有規格」，繼續第 3 步。
   - 422 `spec_not_frozen`／`spec_tainted`／`spec_format_version_unsupported`／`spec_ambiguous` → **規格存在但被拒＝fail-closed**：回 422 `SDD 規格檢查未通過`，**不**退回 LLM 路徑瞎猜（PRD §0.4 的凍結硬閘）。
   - Bridge 不可達／逾時／5xx → 略過路徑 A（記日誌），繼續第 3 步。（Bridge 的 `/sdd/compile` 不會回 503 `sdd_unavailable`：該路由不經過 `_sdd_root`，v1.0 列的這個分支是死碼，已移除；AR-21。）
3. **路徑 C**：`sourceType=PLAIN_TEXT` 且 `content.strip()` 長度 **< 2,000 字元** 且**沒有 Markdown 標題行**（無符合 `^[ ]{0,3}#{1,6}[ \t]` 的行）→ 視為高階目標。
4. **路徑 B**：其餘全部。

`sourceType=MARKDOWN／PDF／DOCX` 一律不會走 C（它們是文件）。

**所有路徑共通**：`parsedResult.project.executionPath` 與 `project.autonomyLevel` 一律取自 `ParseOptions`（不採模型或規格建議的值）；`ImportRecordResponse.parsePath` 記錄採用的路徑；任務數、目標數的上限與 `prompt_too_long` 對每條路徑都適用（§3.3.5）。

#### 3.3.2 路徑 A：規格驅動（`path=SDD`）

- **請求**：`POST /sdd/compile {"spec_dir": "<specDir 或 executionPath>"}`。
- **Bridge 回應**：`{tasks[], scenario, contracts[], spec_path, digest, spec_format_version}`；`tasks[]` 是 `SddToPlaybookAdapter.compile_tasks` 的 PlaybookTask（`step_id,name,prompt,expected_output_regex?,evaluator_command?,spec_digest,weak_regex,…`）。
- **轉換**（AR-19：ADR-001 D18 的「1 個 Goal 容納全部合約」改為**依編譯順序每 24 個合約切成一個 Goal**——凍結規格的合約數常超過 24，全塞進一個目標會被 `max_steps` 閘永遠擋成 422，該專案就無法匯入）：

| Console 欄位 | 來源 |
|--------------|------|
| `project.name` | `scenario`（空則 `executionPath` 的最後一段目錄名） |
| `project.passCriteria` | `規格「<scenario>」的全部合約驗收通過` |
| `project.description` | `由凍結 SDD 規格匯入（<spec_path>；digest <digest 前 12 碼>）` |
| `goals[k]`（k＝1、2、…；`tasks[]` 依 Bridge 回傳的編譯順序，每 24 個一組） | `key=g<k>`、`sortOrder=k−1`；`name`＝只有一組時 `<scenario>`，多組時 `<scenario>（第 k 批）`；`passCriteria=全部 <n_k> 個合約的驗收標準通過`（`n_k` 為該組任務數）；`description=` 同專案 description；`dependsOn`＝k>1 時 `["g<k−1>"]`（保住編譯順序，不受 `execution.dagSchedulerStrategy` 影響） |
| `tasks[i].name` | `task.name` |
| `tasks[i].description` | `task.prompt`（完整，不截斷） |
| `tasks[i].passCriteria` | `輸出符合 <expected_output_regex>`；無 regex 則 `規格合約 <step_id> 的驗收標準` |
| `tasks[i].expectedOutputRegex` | `task.expected_output_regex`（無法編譯 → 清空＋warning `regex_dropped`） |
| `tasks[i].evaluatorCommand` | `task.evaluator_command`（過 Phase 2 消毒；含禁用字元 → 清空＋warning `evaluator_command_dropped`） |
| `tasks[i].passCriteriaSpec` | `{"source":"sdd","specDigest":"<digest>","stepId":"<step_id>","weakRegex":<bool>}` |
| `specDigest` | `digest`；`aiModel`／`tokenUsed` 皆 null；不呼叫任何 Brain |

每組 ≤ 24 個任務，所以每個目標仍套 `max_steps` 閘；其餘閘（`cycle`、`empty_prompt`、`prompt_too_long`）不變。只有合約數超過 24×24 時，目標數才會 > 24 而被 `max_steps`（`location=goals`）擋下。

**v1.5 補充（G-08、S-03、S-04、G-06；D-115-09、D-115-14、D-115-16；已與 ADR-016 §6～§8 對齊）**——以下條文只加不改，與上表衝突處以本段為準：

1. **請求**：`POST /sdd/compile {"spec_dir": …, "spec_file"?: …, "fsm_project"?: …}`。`spec_file` 取自 `ParseOptions.specFile`；`fsm_project` 取自 `ParseOptions.sddProject`（有 `targetProjectId` 時取目標專案的**有效 FSM 專案**，§1.10.5）——Backend 不淨化，值原樣送出，Bridge 淨化後在回應帶標準鍵。匯入探測模式（§3.3.1 第 2 步）只送 `spec_dir`（與已知時的 `fsm_project`），不送 `spec_file`。
2. **`ParseOptions` 新增選填欄位**：
   - `specFile`：要編譯的規格檔——相對 `specDir` 的 POSIX 路徑，或 `specDir` 之下的絕對路徑；須與明示的 `specDir` 並用（目標專案已有 `sddSpecDir` 時以它為 `specDir`）；單獨帶 → 400（`errors[0].field=specFile`）。
   - `sddProject`：FSM 專案名的**有效值**（可以是原名；1～200 字元、無控制字元；§1.10.5）；同一個狀態目錄有多個 FSM 專案時用來指認凍結閘要認哪一個，缺漏時由 adapter 在「只有一份」時自動採用（§3.1.4 (e)）。
   - `targetProjectId`（uuid）：**併入既有專案**（D-115-14；§1.10.8）。帶了之後 `executionPath`、`sddProject`、`specFile` 取自目標專案（目標專案某欄位為 NULL 時以請求值為準），請求另帶不同值 → 409 `sdd_binding_conflict`；目標專案不存在或已軟刪除 → 404。
3. **Bridge 回應的新欄位**（§3.1.4 (e)）：`SddCompileResult` 收下 `spec_file`、`fsm_project`、`frozen_digest`、`spec_format_version`、`unmapped_at_ids`、`warnings`。
4. **欄位保真**（G-08；與 `sdd_compile` CLI 逐任務對拍，F-1）：

| Console 欄位 | v1.5 的來源 |
|--------------|-------------|
| `tasks[i].maxRetries` | `task.max_retries`（SCG-4 型 5、SCG-5 型 2）；Bridge 沒給則 null（落庫取預設 3）。v1.4 是一律 null |
| `tasks[i].passCriteriaSpec` | v1.4 的 `{source, specDigest, stepId, weakRegex}` **加** `maintainContext`（布林，＝`task.maintain_context`；Bridge 沒給則不放這個鍵）。`specDigest` 仍取回應的規格層級 `digest`（與各任務的 `spec_digest` 相同） |

5. **`ParsedResult` 新增四個伺服器擁有欄位**（`PUT /import/{id}/result` 的請求帶了也忽略，同 `specDigest`）：`specFormatVersion`（＝`spec_format_version`；只供顯示與稽核，不做任何閘控）、`sddProject`（＝回應的 `fsm_project`，標準鍵）、`sddSpecDir`（＝回應 `spec_path` 的**父目錄**，絕對路徑）、`sddSpecFile`（＝回應的 `spec_path`，絕對路徑；ADR-016 §7.2）。只有路徑 A 才有值，路徑 B／C 缺席。**`confirm` 才回填**（parse／預覽不回填）：不帶 `targetProjectId` 時帶進新專案的 `sdd_project`／`sdd_spec_dir`／`sdd_spec_file`（§0.5 V12）；帶 `targetProjectId` 時併入目標專案並冪等更新 `sdd_spec_dir`／`sdd_spec_file`、為 NULL 時寫入 `sdd_project`（§1.10.8）。
6. **解析結果 `warnings[]` 的三個新警告碼**（黃色提示，不阻擋；匯入頁照既有的警告區顯示，signoff 前由人決定）：
   - `at_unmapped`：`unmapped_at_ids` 非空 → `{code:"at_unmapped", detail:"規格出現但未編成步驟的 AT：<id、id…>", location:"specDir"}`；空則不加。已編成的 AT 照常產出任務。
   - `frozen_digest_absent`：回應 `frozen_digest="absent"` → `{code:"frozen_digest_absent", detail:"規格凍結時沒有記錄內容摘要（舊狀態檔），無法偵測凍結後改檔", location:"specDir"}`（SA 補：ADR-016 §6.2 只要求 adapter 出聲，Console 轉成警告，§6.8.6 靜默處 #9）。
   - `state_dir_not_ignored`：Bridge 回應的 `warnings` 帶它 → 原樣轉入（`location:"executionPath"`）；提醒使用者把 `build/reports/` 加進該專案的 `.gitignore`。
7. **`spec_ambiguous`（S-04）**：同目錄有多份 TCS 而沒給 `specFile`，仍是 422 `SDD 規格檢查未通過`（`details.bridgeReason=spec_ambiguous`），`detail` 列出符合條件的檔名，使用者據此帶 `specFile` 重試。
8. **凍結與內容綁定（G-06；D-115-16 後的對映）**：規格未凍結、狀態檔缺、規格檔不在凍結清單 → 422 `SDD 規格檢查未通過`（`details.bridgeReason=spec_not_frozen`）；**凍結之後又改了 TCS**（Bridge 409 `spec_digest_changed`）→ 同樣回 422 `SDD 規格檢查未通過`，`details.bridgeReason=spec_digest_changed`，`detail` 說明凍結後內容已變更。**一律不是 200，也不退回 LLM 路徑。**
9. **探測模式的 fail-closed（ADR-016 §6.3）**：`ImportParser.probeSpec` 現行把「非 422」的 4xx 當成「略過路徑 A」——Bridge 的 409 `spec_digest_changed` 若走這條會被**靜默降級成 LLM 草稿（fail-open）**。契約要求 Backend 對 `spec_digest_changed`（409）與 `spec_not_frozen`（422）一律當**拒絕**處理：探測模式下同樣視為「規格存在但被拒」，回 422 `SDD 規格檢查未通過`，不得繼續第 3 步（回歸測試須具名釘住 409 的案例）。
10. **AT 文法與 `step_id`**（D-115-16；ADR-016 §8.1）：編譯接受的 AT id 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC，尾綴不影響歸屬；`step_id`＝`sdd-<scenario>-<at id 小寫>`（`passCriteriaSpec.stepId` 同值）。**照模板填 §4 的 `AT-{NNN}-E-n` 不會讓編譯失敗，但這些 AT 也不會被編成任務**；要執行邊界／錯誤 AT 須命名為 `AT-{NNN}-{Y}-E-{n}` 並列入 §1。

#### 3.3.3 路徑 B：自由文件 → OpenAI 相容 chat completions（`path=LLM`）

- **設定來源**：`model.apiUrl`、`model.apiKey`（解密）、`model.name`、`model.timeout`、`model.temperature`、`model.topP`、`model.maxTokensPerRequest`（皆取呼叫當下的值）。
- **呼叫前的檢查**（不過 → `brain_unsupported`，`detail` 說明原因）：`model.apiKey` 非空；`model.apiUrl` 通過 SEC-04（§1.5.7 的規則 1～6）。連線走 §1.5.7 的 `OutboundHttpClient`（Apache HttpClient 5，把連線釘死在已驗證的 IP、Host／SNI 用原 host、不跟隨 redirect；AR-10）。
- **URL（AR-09）**：`model.apiUrl` **就是完整的 chat-completions 端點 URL**（預設 `https://api.minimax.io/v1/text/chatcompletion_v2`），後端**原樣 POST，不補任何路徑**。v1.0 的「自動補 `/v1/chat/completions`」已取消：同一個設定值還要原樣物化給引擎當 `minimax.base_url`（§3.4.2；引擎的 `MinimaxClient` 直接 `POST` 這個 URL），兩處必須是同一種意思，否則設了金鑰之後預設值必被 Bridge 拒絕（`outbound_not_allowed`，§6 D-48）。E2E 的假伺服器因此要把 `model.apiUrl` 設成含路徑的完整 URL（§5.0.2）。
- **請求**：`POST <model.apiUrl>`，標頭 `Authorization: Bearer <apiKey>`、`Content-Type: application/json`；body：

```json
{ "model": "<model.name>",
  "messages": [
    { "role": "system", "content": "<系統訊息，見下>" },
    { "role": "user",   "content": "<PRD §5.2.4 樣板代入後的全文，見下>" } ],
  "temperature": <model.temperature>, "top_p": <model.topP>, "max_tokens": <model.maxTokensPerRequest>,
  "response_format": { "type": "json_object" }, "stream": false }
```

- **系統訊息**（逐字）：

```
你是一位資深的軟體架構師。只輸出一個 JSON 物件，不要輸出任何其他文字，也不要使用 Markdown 程式碼框。
JSON 結構：
{
  "project": { "name": "string", "executionPath": "string（建議）", "passCriteria": "string（Markdown）", "description": "string（Markdown）" },
  "goals": [
    { "key": "g1", "name": "string", "description": "string（Markdown）", "passCriteria": "string（Markdown）",
      "sortOrder": 0, "dependsOn": ["其他目標的 key；沒有則為空陣列"],
      "tasks": [ { "name": "string", "description": "string（Markdown，不可為空）", "passCriteria": "string（Markdown）", "sortOrder": 0, "estimatedTokens": 0 } ] }
  ]
}
限制：最多 24 個目標、每個目標最多 24 個任務；key 在整份輸出內唯一；dependsOn 只能引用其他目標的 key 且不得成環；每個任務的 description 都必須有實質內容。
```

- **使用者訊息**＝PRD §5.2.4 的輸入 Prompt 樣板逐字，代入 `{autonomyLevel}`（`ParseOptions.autonomyLevel`，影響任務粒度，US-I-07）、`{additionalPrompt}`（空則 `（無）`）、`{documentContent}`（`sourceContent`）：

```
你是一位資深的軟體架構師。請分析以下需求文件，並將其拆解為三層結構：

1. **專案 (Project)**：整體專案名稱、執行路徑建議、通過標準、說明描述
2. **目標 (Goal)**：專案下的主要里程碑或功能模組，含說明描述與通過標準
3. **任務 (Task)**：目標下的具體可執行開發任務，含說明描述與通過標準

自治等級: {autonomyLevel}
補充說明: {additionalPrompt}

---
需求文件內容:
{documentContent}
---

請以 JSON 格式輸出結果。
```

- **長度上限**：系統訊息＋使用者訊息總字元數 > `console.import.max-prompt-chars`（預設 120,000）→ 不呼叫模型，直接 `prompt_too_long`（`location=sourceContent`）。
- **回應處理**：取 `choices[0].message.content`；`finish_reason=length` → `brain_failed`（`detail`：輸出被截斷，請縮短文件或調高 `model.maxTokensPerRequest`）；內容空白／非 JSON（容許外層 ``` 程式碼框，先剝除）／缺 `project` 或 `goals`／`goals` 為空／某目標 `tasks` 為空 → `brain_failed`（`detail` 指出缺什麼）；HTTP 非 2xx、逾時（`model.timeout`）、連線失敗 → `brain_failed`（`detail` 含 HTTP 狀態或例外類別，**不含金鑰與完整 URL**）。成功時 `tokenUsed`＝`usage.total_tokens`（缺則 `prompt_tokens+completion_tokens`，再缺為 null）、`aiModel`＝回應的 `model`（缺則 `model.name`）。
- **轉成 `ParsedResult`**：目標缺 `key` 則依序補 `g1、g2…`；`project.executionPath` 一律以 `ParseOptions.executionPath` 為準（LLM 的建議丟棄）；任務／目標的 `passCriteria` 空白 → 填佔位字串 `（AI 解析未提供通過標準，請於 signoff 前補齊）` 並加 warning `passcriteria_placeholder`；`sortOrder` 一律依陣列順序重編；LLM 帶的未知欄位忽略。

#### 3.3.4 路徑 C：高階目標 → Bridge decompose（`path=DECOMPOSE`）

- **請求**：`POST /autoclaude/decompose`，body `{"goal": <content.strip()>, "context": <additionalPrompt 或 "">, "project": <內容第一行（≤ 60 字元）或 "decomposed-goal">, "max_steps": 24, "config_overrides": {"minimax": {"base_url","model","timeout_seconds"}}}`；`minimax` 區段只在 `model.apiKey` 有值時帶（`base_url`＝`model.apiUrl` 原樣、`model`＝`model.name`、`timeout_seconds`＝`model.timeout`，同 §3.4.2）。**注意**：Bridge 的 decompose **只從它自己的行程環境讀 `MINIMAX_API_KEY`**，請求無法帶金鑰（`config_overrides` 禁放機密）；Bridge 環境沒有金鑰 → 422 `brain_unsupported`（`detail`＝「無法建立 Brain：…」），這是部署設定問題，訊息逐字顯示給使用者。
- **Bridge 回應**：`{draft_id, goal_hash, reasoning, playbook:{project, global_goal, tasks[{step_id,name,prompt,evaluator_command?,…}]}, signed_off:false}`；`tasks[]` 已是拓撲序，**不含依賴資訊**（引擎只在驗證時用 `depends_on`，草稿不保留）。
- **轉換**（1 個 Goal ＋ N 個 Task）：

| Console 欄位 | 來源 |
|--------------|------|
| `project.name` | 請求的 `project` |
| `project.passCriteria` | `goal`（原文） |
| `project.description` | `reasoning`（空則 `由高階目標自動拆解`） |
| `goals[0]` | `key=g1`、`name=<project.name>`、`description=reasoning`、`passCriteria=拆解出的全部步驟依序完成` |
| `tasks[i].name` | `step.name`（空則 `step_id`） |
| `tasks[i].description` | `step.prompt` |
| `tasks[i].passCriteria` | 有 `evaluator_command` 則 `評估指令通過`，否則佔位字串（同 3.3.3）＋warning `passcriteria_placeholder` |
| `tasks[i].evaluatorCommand` | `step.evaluator_command`（消毒不過 → 清空＋warning `evaluator_command_dropped`） |
| `tasks[i].passCriteriaSpec` | `{"source":"decompose","stepId":"<step_id>","draftId":"<draft_id>"}` |
| `draftIds`／`reasoning` | `[draft_id]`／`reasoning`；`aiModel`／`tokenUsed` 為 null（Bridge 不回報） |

- Bridge 草稿存於其 workspace 的 `_drafts/<draft_id>.json`；signoff 時對每個 `draftIds` 呼叫 `:approve`（審計）。

#### 3.3.5 三道有界閘與相關檢查

三條路徑與 `PUT /import/{id}/result` 共用同一個後端實作（`ParsedResultValidator`），在樹層級**一次列出全部違規**（US-I-10：完整顯示、不截斷、不修剪；`errors[]` 依下表順序，同閘內依樹的位置）。路徑 C 的 Bridge 閘（對映見 §3.2）先於本表；路徑 B 的 `brain_*` 發生在還沒有樹的時候，所以只會單獨出現。

| 順序 | `gate` | 定義 | `location` 格式 | `detail` 範例 |
|------|--------|------|-----------------|---------------|
| 1 | `empty_prompt` | 任務 `name` 或 `description` 去空白後為空 | `goals[i].tasks[j].name`／`.description` | `任務「（未命名）」的描述為空（goals[0].tasks[2]）` |
| 2 | `max_steps` | 目標數 > 24；或任一目標的任務數 > 24（硬上限，config 可下調不可上調；**不截斷、不修剪**） | `goals`／`goals[i].tasks` | `目標「建立基礎架構」的任務數 25 超過上限 24（不截斷、不修剪）` |
| 3 | `cycle` | 目標依賴圖不是 DAG：Kahn 排序失敗（成環）、自依賴、`dependsOn` 引用不存在的 `key`、目標 `key` 重複（Bridge 同樣把這些 DAG 結構問題歸入 `cycle`） | `goals[i].dependsOn`／`goals[i].key` | `目標依賴成環：基礎 -> 核心 -> 基礎` |
| 4 | `prompt_too_long` | 任務依 §3.4.3 樣板組出的 prompt 超過 20,000 字元（Windows 命令列上限，Architecture §12 L-9） | `goals[i].tasks[j]` | `任務「實作」的 prompt 長度 23412 超過上限 20000` |
| — | `brain_unsupported` | 路徑 B：`model.apiKey` 為空，或 `model.apiUrl` 未通過 SEC-04；路徑 C：Bridge 無法建立 Brain | 省略 | `模型位址未通過 SSRF／allowlist 檢查（not_in_allowlist）` |
| — | `brain_failed` | 模型呼叫失敗、輸出非 JSON／缺必要欄位／結果為空／被截斷（路徑 B）；Bridge 回報無步驟或 Brain 回 None（路徑 C） | 省略 | `模型輸出不是合法 JSON：…` |
| — | `prompt_too_long`（文件層） | 路徑 B 的 LLM 輸入總長超過 `console.import.max-prompt-chars` | `sourceContent` | `文件過長：<n> 字元，上限 120000` |

結構性問題（缺必填欄位、型別錯誤、空陣列）與消毒問題（禁用字元、regex 無法編譯）**不是**閘，回 400（見 1.1.4）。**任務的 `name`／`description` 是「空白字串」則是閘 `empty_prompt`**，與「欄位缺漏（null）」的 400 區分；不論來自 parse 或 `PUT /import/{id}/result` 都是同一套（AR-21）。路徑 A 的每個目標至多 24 個任務（§3.3.2），所以合約數多不會讓整案被 `max_steps` 擋下。

#### 3.3.6 `ParseResultResponse` 各欄位

| 欄位 | parse 成功 | PUT result 成功 |
|------|-----------|-----------------|
| `importId` | 記錄 id | 同左 |
| `status` | `PARSED` | `REVIEWING` |
| `path` | `SDD`／`LLM`／`DECOMPOSE` | 沿用庫內值 |
| `parsedResult` | 三層樹＋`path`／`aiModel`／`tokenUsed`／`reasoning?`／`draftIds?`／`specDigest?` | 以請求的 `project`＋`goals` 覆寫後的樹（伺服器欄位沿用庫內值） |
| `signedOff` | `false` | `false`（編輯撤銷 signoff） |
| `aiModel`／`tokenUsed`／`reasoning` | 路徑 B：模型回報；路徑 C：只有 `reasoning`；路徑 A：皆 null | 沿用庫內值 |
| `errors` | `[]`（閘違規走 422，不走這裡） | `[]` |
| `warnings` | `evaluator_command_dropped`／`regex_dropped`／`passcriteria_placeholder`，每項 `{code,detail,location}` | 重新計算（只含仍成立者） |

---
### 3.4 執行：Playbook 組裝與 Bridge 請求

#### 3.4.1 Playbook 欄位表（`PlaybookBuilder`；Bridge `PlaybookIn` 為 `extra=forbid`，多送欄位即 422）

| Playbook 欄位 | 來源 | 備註 |
|---------------|------|------|
| `version` | 固定 `"1.0"` | |
| `project` | 專案名稱淨化後（見下） | 1～200 字元；同名同路徑會共用 Bridge 的 advisory lock 鍵 |
| `global_goal` | `project.passCriteria` | 主控裁決（W3 任務書；Architecture 寫「說明、缺則通過標準」，§6 D-07） |
| `workflow_type` | 不送（預設 `auto`） | |
| `global_invariants.max_retries_per_step` | 系統參數 `agent.maxRetries` | 0～20（設定驗證已保證） |
| `global_invariants.auto_compact_interval` | 不送（引擎預設 5） | **E2E 專案任務數須 ≤ 5**，避免觸發引擎的 `/compact` 額外呼叫而改變 Token 帳（§5.0） |
| `tasks[].step_id` | `G<g>-T<t>`（§3.4.4） | 1～128 字元、無控制字元；整份 playbook 內唯一 |
| `tasks[].name` | `task.name` | 1～500 字元 |
| `tasks[].prompt` | §3.4.3 樣板 | 1～20,000 字元 |
| `tasks[].expected_output_regex` | `task.expectedOutputRegex` | 無則不送 |
| `tasks[].evaluator_command` | `task.evaluatorCommand` | 先過第 2 層複驗（§1.2.1 第 9b、9c）；無則不送 |
| `tasks[].max_retries` | `task.maxRetries` | 0～20（Phase 2 DTO 的 `@Max(20)` 與 execute 第 9f 項雙重保證；超過會被 Bridge 以 422 `invalid_request` 拒絕，AR-14） |
| `tasks[].goal_task_id` | `task.id`（UUID 字串） | **必送**：Bridge 只有帶 UUID 的步驟才寫 `execution_steps` |
| `tasks[].command` | **永不送** | 引擎 Kernel 路徑對它零消費（ADR-001 D17）；E2E 的替身走 `claude.command` |
| `tasks[].maintain_context`／`evaluator_timeout_seconds`／其他 | 不送 | 用 Bridge／引擎預設 |

**專案名稱淨化**：把不在 `[A-Za-z0-9._\-一-鿿]` 內的字元換成 `_`，截到 200 字元；結果為空則用 `project-<專案 id 前 8 碼>`。

Bridge 請求：`{ "run_id": "<execution_runs.id>", "project": "<淨化名>", "execution_path": "<project.executionPath>", "playbook": {…}, "config_overrides": {…}, "env": {…}, "fresh": false }`。

**v1.5 補充：SDD 批次的 playbook 與 Bridge 請求（D-115-06；G-01、G-06、G-08；已與 ADR-016 對齊）**——只有 §1.10.5 的資格全部成立時適用；不成立時上表與 v1.4 完全相同。

| 欄位 | SDD 批次的做法 |
|------|----------------|
| `workflow_type`／`workflow_path` | Console **仍不送**；由 Bridge 伺服端覆寫（§3.1.6；有 `spec_file` 時 `workflow_path` 是規格檔的 realpath，否則是規格目錄） |
| `tasks[].step_id` | 沿用 `passCriteriaSpec.stepId`（`sdd-<場景>-<at id 小寫>`；整份 playbook 唯一，由資格第 5 項保證）；`dag.nodes[].stepId`、`ExecutionStepResponse.stepId`、SSE 與日誌的 `stepId` 同值（`G<g>-T<t>` 只用於非 SDD 批次，§3.4.4）。引擎的 `RtmWritebackPlugin` 只認 `sdd-` 前綴，這是追溯報告的前提 |
| `tasks[].max_retries` | `task.maxRetries`（路徑 A 現在填 5 或 2）；其餘規則不變 |
| `tasks[].maintain_context` | `passCriteriaSpec.maintainContext`（布林；缺則不送） |
| `tasks[].spec_digest` | `passCriteriaSpec.specDigest`（Bridge 預檢第 4 項的「匯入時」摘要；`sha256:<64 位小寫 hex>`，§3.1.4 (d)） |
| `tasks[].weak_regex` | `passCriteriaSpec.weakRegex`（布林；缺則不送） |
| 頂層 `sdd` | `{spec_dir, spec_file?, fsm_project, root, approver}`（§1.10.6），與 `playbook` 同層；同時附標頭 `X-Bridge-Token` |
| 請求層 `env` | `ConfigMaterializer` **不會**送 `BRIDGE_SDD_WRITE_TOKEN`、`SDD_PROJECT`、`SDD_STATE_DIR`；Bridge 的 `validate_env` 拒絕它們（422 `forbidden_name`，§3.1.4 共通規則 2） |
| 201 回應 | Bridge 的 201 可帶選填 `warnings:[{code, detail}]`（目前只有 `sdd_frozen_digest_absent`）；Backend 原樣轉入 Console 201 的 `warnings[]`（§1.10.6） |
| 讀取逾時 | 90 秒（含最多三次 FSM CLI 子行程，每次 ≤ 20 秒；一般批次維持 30 秒；§3.1） |

prompt 樣板（§3.4.3）不變：SDD 任務的 `description` 就是編譯出的 prompt（已含契約、驗收閘與規格出處）。`PlaybookIn` 仍是 `extra=forbid`：Bridge 已接受 `maintain_context`／`spec_digest`／`weak_regex`（引擎 `PlaybookTask` 的既有欄位），所以不需要放寬 `PlaybookIn`；補償與 `execution_runs` 的建立流程（§3.4.5）不變。

#### 3.4.2 `config_overrides` 與 `env` 物化（`ConfigMaterializer`；`API-SET-10`）

Bridge 對 `config_overrides` 的規則：頂層鍵限 `claude, minimax, embedder, loop, playbook, token_guard, alert_ladder, notification, tool_invocation, executor, preferences`；未知鍵 → 422（引擎會靜默丟棄打錯字的欄位，所以 Bridge 擋）；機密鍵（`minimax.api_key`、`storage.db_dsn` 等）→ 422；`storage`／`checkpoint_dir`／`log_dir` 等管控鍵**合法但被忽略並發 `CONFIG_OVERRIDE_IGNORED` 告警**（所以 Console **不送**，避免每個 run 都帶噪音告警）。

| 送到 Bridge 的位置 | 來源（系統參數） | 條件 |
|--------------------|------------------|------|
| `config_overrides.claude.command` | `autoclaude.claudeCommand`（預設 `claude`；E2E 為 mock claude 的**絕對路徑**，§5.0.2） | 永遠 |
| `config_overrides.claude.extra_args` | `autoclaude.claudeExtraArgs` 以空白切成陣列 | 非空才送；每個 token 須符合 `^[A-Za-z0-9_.=:,/@\-]+$` |
| `config_overrides.claude.continue_flag`／`encoding` | `autoclaude.claudeContinueFlag`／`claudeEncoding` | 永遠 |
| `config_overrides.playbook.step_timeout_seconds` | `agent.taskTimeout` | 永遠 |
| `config_overrides.token_guard.compact_threshold_pct`／`halt_threshold_pct` | `execution.compactThresholdPct`／`haltThresholdPct`（整數轉數字） | 永遠；**不送 `token_guard.enabled`**（不得經 Console 繞過安全收斂，NFR-SEC-05） |
| `config_overrides.token_guard.auto_resume`／`max_auto_resumes` | `execution.autoResume`／`maxAutoResumes` | 永遠 |
| `config_overrides.minimax.base_url`／`model`／`timeout_seconds` | `model.apiUrl`（**原樣**，完整的 chat-completions 端點，AR-09）／`model.name`／`model.timeout` | **只在 `model.apiKey` 有值時**送（沒有金鑰引擎本來就用不到 Brain）。Bridge 會依它自己的 `BRIDGE_OUTBOUND_ALLOWLIST` 驗 `minimax.base_url` 的 host：Console 的預設 allowlist 因此與 Bridge 對齊（`api.minimax.io,api.minimax.chat`，附錄 D.2），種子預設值也已改成引擎預設端點（§0.5 V5）；否則 Console 放行、Bridge 拒絕，每次 execute 都回 422 `引擎拒絕此請求` |
| `config_overrides.minimax.enable_kernel_brain`（v1.3，D-11） | `brainRequested`＝`model.enableKernelBrain` ∨ `agent.enableAutoMutation` ∨ 自治等級 ≥ 6（決策表見下） | **只在 `model.apiKey` 有值時送，而且顯式送 `true` 或 `false`**（磁碟上的引擎設定檔因此永遠看得到有效值）。**沒有金鑰一律不送**：引擎對「`enable_kernel_brain=true` 但沒有金鑰」不是忽略，而是**啟動即失敗**（`main.py` 記 `初始化失敗: enable_kernel_brain=True 但未設定 MINIMAX_API_KEY／config.minimax.api_key` 後 `return 1`，證據見 §6.6.2 Q1），Bridge 會把這個批次判 `FAILED`（`reason` 為「引擎異常結束（exit=1）…」） |
| `env.MINIMAX_API_KEY` | `model.apiKey` 解密後 | 只在有值時送；絕不進 `config_overrides`、日誌或回應 |
| `env.MOCK_CLAUDE_*` | profile `e2e`／`test` 的 `console.execution.mock-env` 映射（例 `MOCK_CLAUDE_DELAY`、`MOCK_CLAUDE_FAIL_REGEX`、`MOCK_CLAUDE_TRACE`） | **只在測試 profile**；production 永不送 |

不送／只儲存：`autoclaude.dalBackend`／`dbDsn`／`dualReadResolution`（Bridge 固定 `yaml_only`，`effect=STORED_ONLY`，§6 D-27）、`agent.maxConcurrentTasks`／`execution.maxParallelGoals`（引擎序列執行）、`agent.enableSelfEvolution`（v1.3 已驗證：引擎沒有對應的有效旗標，`effect=STORED_ONLY`，見下方〈引擎旋鈕查證〉）。`agent.enableAutoMutation` 與 Level 6～10 **不再是「不送」**（v1.3）：它們透過上表的 `minimax.enable_kernel_brain` 送進引擎。**永不送**（任何等級、任何旗標組合都不得出現在 `config_overrides`，單元測試逐一斷言）：`playbook.max_evolutions`、`playbook.require_evolution_signoff`（引擎執行路徑上沒有讀者，送了只會讓人誤以為有演化上限與核可閘）、`playbook.enable_rtm_feedback`、`playbook.goal_synthesis_enabled`、`playbook.enable_translation_auto_propose`（對 Console 產生的 playbook 沒有可觀測的效果，或會關掉既有的檢查）；理由與證據見 §6.6.2。

**引擎旋鈕查證（v1.3；D-11；AR-12、TBC-2 的後續。現查 `AutoClaude/`，逐條證據含檔案與行號見 §6.6.2）**——結論先講：

1. **只有 `minimax.enable_kernel_brain` 是「Console 能控制、而且引擎生產路徑上真的有讀者」的旗標。** 為真且有金鑰時，引擎在**步驟失敗且還有重試次數**時，先請 Brain 改寫該步驟的 prompt 再重試；**Brain 呼叫失敗時該步驟直接升級（ESCALATION），不再重試**。Kernel 呼叫 Brain 時沒有要求「步驟變異」（`allow_step_mutation` 預設 false，Brain 不被告知變異格式），所以實務上只有 prompt 改寫：PRD 的「自動突變」在引擎裡的實際內容是 **Brain 逐步校正**。沒有金鑰時：旗標為真＝啟動失敗（見上表）；旗標為假＝引擎只記一行警告「Brain 相關能力（步驟 correction／goal synthesis／自演化提案）本次停用」，playbook 照跑。
2. **`playbook.max_evolutions`、`playbook.require_evolution_signoff` 在生產路徑上沒有讀者。** Bridge 啟動引擎的 `argv` 是 `python -m autoclaude <playbook> --config <config.yaml>`，走 Kernel；Kernel 在**失敗型** ESCALATION（重試耗盡、收斂判升級；Brain 故障與 veto 型升級不走這段善後）後只**發布演化提案、寫一行 `=== EVOLUTION PROPOSAL ===` 日誌**，不套用、不重載、不產生 `evolved_*.yaml`。Kernel 回傳的 `KernelResult.evolved_playbook_path` 永遠是 `None`，所以 `AutoResumeService` 裡讀 `max_evolutions` 的重載迴圈進不去，而且那個迴圈**沒有**核可閘；`require_evolution_signoff` 只被舊的 `PlaybookRunner` 讀（該類別在套件內沒有任何建構點）。引擎自己的測試鎖住了「只提案不套用」（`test_proposal_is_logged_but_never_applied`），理由正是「否則繞過 `AutoResumeService` 缺的核可閘」。舊路徑上 `require_evolution_signoff=true` 而沒有 approver 時的 fail-closed 結果是「拒絕這次演化重載，run 以原本已升級的結果結束」：它發生在 run 本來就已經 ESCALATION 之後，所以既不是「批次繼續跑」，也不是額外多一個「整批停機」的動作。
3. **演化的 AI 提案只由金鑰的有無決定，沒有開關。** 有金鑰引擎才建 `MinimaxClient`，失敗型 ESCALATION 時 `EvolutionPlugin` 先請外部模型提案（失敗退回規則引擎），最壞約 96 秒（`_call_with_retry` 逾時 30 秒、最多 3 次加退避，只會拉長 `status FAILED` 的出現時間，失敗仍 fail-soft）；沒有金鑰就只剩規則引擎。兩種提案都只寫日誌。有金鑰的批次另外會在**最後一步之後**（run 走完全部步驟時才有；ESCALATION 或 halt 的 run 沒有）多打一次目標驗證請求（`GoalSynthesisPlugin`，POST_RUN；失敗 fail-open，結果在 Kernel 路徑上不套用）。這兩個外呼與 `enable_kernel_brain`、等級、旗標都無關。Bridge 把自己的行程環境傳給引擎子行程，所以 **E2E「關閉演化」＝執行類情境的 `model.apiKey` 必須為空（Console 就不送 `MINIMAX_API_KEY` 與 `minimax.*`），並在啟動 Bridge 前清掉它行程環境裡的 `MINIMAX_*`**（§5.0.2；D-58 的結論不變）。
4. 其餘三個 `playbook` 旗標（`enable_rtm_feedback`、`goal_synthesis_enabled`、`enable_translation_auto_propose`）對 Console 產生的 playbook 沒有可觀測的效果（第一個只對 `sdd-` 開頭的步驟生效，Console 的 step_id 是 `G<g>-T<t>`；後兩者出廠就是開），不送。

**物化決策**（`materialize(autonomyLevel)`；`level`＝本批次的 `autonomyLevel`）：

```
effAutoMutation  = agent.enableAutoMutation  ∨ level ≥ 6
effSelfEvolution = agent.enableSelfEvolution ∨ level ≥ 7
brainRequested   = model.enableKernelBrain   ∨ effAutoMutation
hasKey           = model.apiKey 解密後非空
```

| # | `hasKey` | `brainRequested` | `effSelfEvolution` | 送出的 `minimax.*` | `env.MINIMAX_API_KEY` | `autoMutation` | `selfEvolution` |
|---|:--------:|:----------------:|:------------------:|---------------------|:---------------------:|----------------|-----------------|
| 1 | 有 | 真 | 真 | `base_url`／`model`／`timeout_seconds`＋`enable_kernel_brain: true` | 送 | `ENABLED` | `ENABLED` |
| 2 | 有 | 真 | 假 | 同上（`enable_kernel_brain: true`） | 送 | `ENABLED` | `ENABLED` |
| 3 | 有 | 假 | 真 | 同上，但 `enable_kernel_brain: false` | 送 | `OFF` | `ENABLED` |
| 4 | 有 | 假 | 假 | 同上，但 `enable_kernel_brain: false` | 送 | `OFF` | `ENABLED` |
| 5 | 無 | 真 | 真 | 不送 | 不送 | `UNAVAILABLE_NO_API_KEY` | `UNAVAILABLE_NO_API_KEY` |
| 6 | 無 | 真 | 假 | 不送 | 不送 | `UNAVAILABLE_NO_API_KEY` | `OFF` |
| 7 | 無 | 假 | 真 | 不送 | 不送 | `OFF` | `UNAVAILABLE_NO_API_KEY` |
| 8 | 無 | 假 | 假 | 不送 | 不送 | `OFF` | `OFF` |

**等級 × 兩個旗標 × 金鑰的完整矩陣**（由上面的決策函式機械產生；`model.enableKernelBrain=false`——它為真時，對 `enable_kernel_brain` 與 `autoMutation` 的影響等同 `agent.enableAutoMutation=true`，對 `selfEvolution` 沒有影響；同一類別內每個等級的結果相同，單元測試取等級 {1, 5, 6, 7, 10} 驗邊界）：

| 自治等級 | `enableAutoMutation` | `enableSelfEvolution` | 有金鑰：送出的 `enable_kernel_brain`／`{autoMutation, selfEvolution}` | 沒有金鑰（不送 `minimax.*`）：`{autoMutation, selfEvolution}` |
|----------|:---:|:---:|-----|-----|
| 1～5 | 假 | 假 | `false`／`{OFF, ENABLED}` | `{OFF, OFF}` |
| 1～5 | 假 | 真 | `false`／`{OFF, ENABLED}` | `{OFF, UNAVAILABLE_NO_API_KEY}` |
| 1～5 | 真 | 假 | `true`／`{ENABLED, ENABLED}` | `{UNAVAILABLE_NO_API_KEY, OFF}` |
| 1～5 | 真 | 真 | `true`／`{ENABLED, ENABLED}` | `{UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY}` |
| 6 | 假 | 假 | `true`／`{ENABLED, ENABLED}` | `{UNAVAILABLE_NO_API_KEY, OFF}` |
| 6 | 假 | 真 | `true`／`{ENABLED, ENABLED}` | `{UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY}` |
| 6 | 真 | 假 | `true`／`{ENABLED, ENABLED}` | `{UNAVAILABLE_NO_API_KEY, OFF}` |
| 6 | 真 | 真 | `true`／`{ENABLED, ENABLED}` | `{UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY}` |
| 7～10 | 假 | 假 | `true`／`{ENABLED, ENABLED}` | `{UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY}` |
| 7～10 | 假 | 真 | `true`／`{ENABLED, ENABLED}` | `{UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY}` |
| 7～10 | 真 | 假 | `true`／`{ENABLED, ENABLED}` | `{UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY}` |
| 7～10 | 真 | 真 | `true`／`{ENABLED, ENABLED}` | `{UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY}` |

**`engineCapabilities` 各值的精確意思**（它描述「Console 送進引擎的」與「引擎因此會做的」，不是使用者的設定）：

| 欄位 | `ENABLED` | `OFF` | `UNAVAILABLE_NO_API_KEY` |
|------|-----------|-------|--------------------------|
| `autoMutation` | 已送 `enable_kernel_brain: true`（且送了金鑰）：步驟失敗且尚有重試次數時，Brain 先改寫 prompt 再重試；**Brain 呼叫失敗則該步驟直接升級**（錯的金鑰或網址會讓「重試」變成「升級」）。實務上只有 prompt 改寫，不含步驟變異 | 已送 `enable_kernel_brain: false`（有金鑰），或沒有金鑰且沒人要求；失敗步驟照舊自動重試 | 有人要求（`model.enableKernelBrain`、`agent.enableAutoMutation` 或等級 ≥ 6）但 Console 沒有金鑰可送；Console 不送 `minimax.*`，批次照常執行，只是沒有 Brain |
| `selfEvolution` | **有金鑰就是 `ENABLED`，與旗標和等級都無關**（引擎沒有開關）：失敗型 ESCALATION 時由 Brain 產生演化**提案**，只寫引擎日誌，**不套用、不重載、不產生 `evolved_*.yaml`** | 沒有金鑰且沒人要求（沒有 Brain 的演化提案；引擎的規則引擎提案仍會寫日誌，但那不是這個欄位談的） | 有人要求（`agent.enableSelfEvolution` 或等級 ≥ 7）但沒有金鑰：AI 演化提案不會發生 |

**一致性規則**：①`materialize(level)` 在每次建立批次時**只呼叫一次**，回傳值同時用於 `execution_runs.engine_capabilities` 的 INSERT 與 Bridge 請求（兩次分開讀設定，設定可能在中間被改，落庫的值就會與實際送出的不符）；②審核 `SKIP`／`RETRY` 開的後續批次也走同一條路（等級繼承自原批次），各自依當下的設定重新決定；③`resume`／`restore` 不重算 `engineCapabilities`：引擎設定檔 `config.yaml` 在 spawn 時凍結（路徑 `<ENGINE_WORKSPACE>/<runId>/config.yaml`，Bridge `runner.py` 的 `_materialize` 寫入），只有 `env` 會依當下的設定重新帶上。

**誠實劃界與已知限制**（不是待修缺陷）：
1. **`UNAVAILABLE_NO_API_KEY` 只認 Console 的 `model.apiKey`。** Docker 全棧下 compose 的 `engine-bridge` 服務本身就必填 `MINIMAX_API_KEY`（`docker-compose.yml`），Bridge 會把它傳給每個引擎子行程，所以那種部署裡引擎**實際上有金鑰**（AI 演化提案與目標驗證照跑），但 Console 看不到它：不會送 `enable_kernel_brain: true`，報 `UNAVAILABLE_NO_API_KEY`。方向是低估（不會把引擎沒做的事報成已啟用）；要精準回報，需要 Bridge 在 `/health` 回報環境金鑰的有無，列為後續候選，不在 v1.3。
2. **旗標設為 `false` 關不掉等級的強制開啟**：公式用 ∨，等級 ≥ 6 一律視為要求自動突變、≥ 7 一律視為要求自演化。要關 Brain 校正請降等級，或清掉金鑰。
3. **金鑰在批次中途被改或被清掉**：`resume`／`restore` 的 `env` 依當下設定重帶，但 `config.yaml` 是凍結的。凍結的設定為 `enable_kernel_brain: true` 而此時金鑰已被清掉（Bridge 環境也沒有）→ 引擎重新啟動即失敗，批次判 `FAILED`；反過來，批次中途才補了金鑰 → Brain 校正仍關（凍結為 false，或根本沒有 `minimax` 區段），但演化提案與目標驗證開始外呼。`engineCapabilities` 維持建立時的值。要換設定請另開批次。
4. **有金鑰時的外呼量**：每個失敗且尚有重試次數的 attempt 一次校正請求（Brain 開啟時才有）；每次失敗型 ESCALATION 一次演化提案請求（有金鑰就有，與 Brain 開關無關）；最後一步之後一次目標驗證請求（同上；只有 run 走完全部步驟時才有）。5xx 時每個請求被引擎重試 3 次（退避 2 秒＋4 秒），逾時最長 `model.timeout`×3＋6 秒。

#### 3.4.3 prompt 樣板與長度上限

`tasks[].prompt` ＝ 下列文字（行以 `\n` 連接）；`task.description` 去空白後為空時，描述那一段（連同它前後的空行）整段省略：

```
## 任務 <stepId>：<task.name>
所屬目標：<goal.name>

<task.description>

## 通過標準
<task.passCriteria>
```

- 加入 `<stepId>` 與任務名稱是為了讓每步 prompt **互不為子字串**——Bridge 以「步驟 prompt 是否出現在引擎啟動行」辨識步驟邊界，prompt 相同或互為子字串會讓邊界判定退化。
- **長度**以 Java `String.length()`（UTF-16 code unit）計，≤ **20,000**；超過 → execute 第 9a 項 422（匯入階段為 `prompt_too_long` 閘）。依據：引擎把 prompt 當命令列參數傳給 claude，Linux 單一參數上限 128 KiB、**Windows 整條命令列 32,767 字元**（Architecture §12 L-9；CI run 以 50,000 個中文字實證 spawn 失敗）。
- `task.description`／`passCriteria` 的 Markdown 原文原樣帶入，不另轉義（它們不是命令；命令欄位只有 `evaluatorCommand`，已走三層消毒）。

#### 3.4.4 DAG 與 `step_id`

- **目標位置 `g`**＝該批次範圍內的目標依拓撲＋策略排序後的序號（1 起）；**任務位置 `t`**＝該目標在**本批次範圍內**的任務序（1 起，依 `sortOrder`、`createdAt`、`id`）。`step_id` ＝ `G<g>-T<t>`（例 `G1-T1`、`G1-T2`、`G2-T1`）。整份 playbook 內唯一，且每個批次獨立編號（後續批次重新從 `G1-T1` 起；`dag.nodes[].stepId` 是權威對映）。這取代 Architecture 的全域 `T001…` 與 W3 任務書的 `G<sortOrder>-T<sortOrder>`（後者在 `sortOrder` 重複時會撞 id，§6 D-06）。
- **v1.5 例外（SDD 批次，§1.10.5 資格成立時）**：`step_id` 不用 `G<g>-T<t>`，而是沿用任務 `passCriteriaSpec.stepId`（`sdd-<場景>-at-…`），`dag.nodes[].stepId` 同值；`sequence`（展平後位置）與目標位置 `g` 的規則不變。非 SDD 批次與混合批次維持本節原規則。
- **展平順序**＝DAG 節點的 `sequence`：`TASK` 節點的 `sequence` 等於 Bridge 的 `step_number`（1 起）。
- `execution_runs.dag`（建立時凍結，只含結構，不含狀態）：

```json
{ "nodes":[
    { "id":"a1f4c2d3-…-4e11", "kind":"GOAL", "label":"基礎", "sequence":1 },
    { "id":"c7e2b1a0-…-1c21", "kind":"TASK", "label":"初始化", "goalId":"a1f4c2d3-…-4e11", "stepId":"G1-T1", "sequence":1 },
    { "id":"c7e2b1a0-…-1c22", "kind":"TASK", "label":"設定",   "goalId":"a1f4c2d3-…-4e11", "stepId":"G1-T2", "sequence":2 },
    { "id":"a1f4c2d3-…-4e12", "kind":"GOAL", "label":"核心", "sequence":2 },
    { "id":"c7e2b1a0-…-1c23", "kind":"TASK", "label":"實作", "goalId":"a1f4c2d3-…-4e12", "stepId":"G2-T1", "sequence":3 } ],
  "edges":[
    { "from":"a1f4c2d3-…-4e11", "to":"a1f4c2d3-…-4e12", "kind":"DEPENDENCY" },
    { "from":"a1f4c2d3-…-4e11", "to":"c7e2b1a0-…-1c21", "kind":"CONTAINS" },
    { "from":"a1f4c2d3-…-4e11", "to":"c7e2b1a0-…-1c22", "kind":"CONTAINS" },
    { "from":"a1f4c2d3-…-4e12", "to":"c7e2b1a0-…-1c23", "kind":"CONTAINS" } ] }
```

#### 3.4.5 建立流程與補償

1. 驗證（§1.2.1 表的 1～9f）。
2. **交易 1**：鎖專案列 → 取 `run_number = max+1` → 插入 `execution_runs`（`id` 新 UUID、`autonomy_level`、`scope`、`token_budget`、`dag`；Bridge 欄位留 DDL 預設）→ 提交。（Bridge 的 `UPDATE … WHERE id=run_id` 需要列已存在。）
3. 呼叫 Bridge `POST /autoclaude/runs`。
4. 成功（201）→ **交易 2**：專案與任務狀態（§3.5.3）→ 啟動 `RunEventConsumer`（`after=0`）→ 回應。
5. 失敗 → **交易 3**：刪除剛建的 `execution_runs` 列。**守門只有一條：該 run 尚無任何 `execution_steps`，不看列的狀態**（AR-15）——Bridge 在 `spawn_failed`（`Popen` 失敗）時會 `set_status(FAILED, …)` 並把 `status=FAILED`、`completed_at` 鏡射進 DB，列已經不是 `INITIALIZING`；v1.0 的「僅在仍是 `INITIALIZING` 時才刪」會讓這種列留下來，成為佔用 `run_number` 的 FAILED 空批次。→ 依 §3.2 轉譯回應；專案與任務狀態不動。
6. 崩潰保護：console-api 啟動時，對「`INITIALIZING` 且建立逾 60 秒」的列問 Bridge `GET run`；Bridge 回 404 → 視同第 5 步補償刪除。

### 3.5 事件 → 讀模型（`RunEventConsumer`）

#### 3.5.1 Bridge 事實（實作消費者前必讀；已對 `runner.py` 與 Bridge 測試逐條核對，有無測試鎖定在條目內標明）

1. 事件序號從 1 起連續單調；第一則 `status` 是 `INITIALIZING`，接著 `RUNNING`。
2. **`step COMPLETED(k)` 在「步驟 k+1 的啟動行出現」或「引擎結束」時才發**，所以 `COMPLETED(k)` 與 `STARTED(k+1)` 幾乎同時、前者在前；最後一步的 `COMPLETED` 緊接 `status COMPLETED`。
3. **pause 邊界**：被要求暫停時，步驟 k 完成、k+1 剛 spawn 就被終止；k+1 的 `STARTED` **不發**（除非引擎已推進），`status PAUSED` 之前最後一則 `step` 是 `COMPLETED(k)`。一次續跑至少前進一步才允許再暫停。
4. **`STARTED` 可能重複發出**——消費者必須冪等：任務已是 `RUNNING` 時忽略重複的 `STARTED`（`execution_steps` 因此可能有兩列同一任務的 `STARTED`，屬正常）。何時會重複要分情形（AR-21，v1.0 把 resume 也算進去是講過頭了）：
   - **restore 之後**：引擎從快照重做被打斷或失敗的那一步，同一步會再發一次 `STARTED`（`attempt=1`）。例：ESCALATED 的 `RETRY` restore 到 `after-G1-T1` 後，`G1-T2` 的 `STARTED` 會出現第二次（E2E-05 步驟 5）。
   - **gate-pause 之後的 resume**：審核閘「提前一步」在步驟 k 進行中呼叫 `:pause`，邊界落在 `COMPLETED(k)` 之後、`STARTED(k+1)` 之前（第 3 點的 deferral：`runner.py` 在 k+1 的啟動行出現、`_spawn_completed ≥ 1` 且已要求暫停時，只發 `COMPLETED(k)`，把 `STARTED(k+1)` 暫存並終止引擎）；resume 後引擎重新啟動 k+1，`STARTED(k+1)` 是**第一次**發出，不是重複（E2E-04 步驟 9 預期「恰一次」）。只有暫存的 `STARTED` 已因「終止訊號到達前引擎又往前跑了一點」而補發時，resume 後才會再發第二次（毫秒級競速視窗，罕見但合法）。
   - **有無 Bridge 測試鎖定**：`test_pause_stops_at_the_step_boundary_and_resume_continues_from_the_checkpoint` 鎖定了邊界位置、`T01` 不重做與從 checkpoint 接續；**沒有任何測試鎖定「gate-pause 後 `STARTED(k+1)` 只發一次」或「重發」本身**——這兩個行為以 `runner.py` 的實作為準，W3-B2 的迷你 Bridge 測試與真 Bridge 冒煙應各驗一次。
5. `RETRYING`＝同一步驟的啟動行再次出現，`attempt` 從 2 起；重試耗盡 → `step FAILED`（`attempt`＝最後一次）→ `alert`（`code=ESCALATION`、level `error`）→ run `FAILED`，`reason` 以「引擎升級（ESCALATION）」開頭。Token Guard halt 判 `FAILED`（`reason`＝`引擎因 token／額度門檻停機（halted），未自動續跑`）並發 `alert`（`TOKEN_HALT`、`warning`）；其他異常 `reason` 為 `引擎異常結束（exit=N）：…`；Bridge 重啟回收的孤兒 `reason` 含 `orphaned`。
6. `token` 事件每個 **attempt** 一則（引擎印出 `STEP_TOKEN_PEAK` 時才有，僅 context% > 0），`tokens_used` 是**本 run 累計**（每個 attempt 加最後一筆 usage 的 input＋cache_read＋cache_creation＋output），**不帶 `step_id`**；mock claude 每次呼叫固定 1,240（1,200＋40）。消費者以「目前尚未結束的步驟」歸因。
7. Bridge 只為帶 UUID `goal_task_id` 的步驟寫 `execution_steps`；`review-request` 事件 Bridge 從不發送；`alert.level` 為 `info`／`warning`／`error`（`RESTORE` 為 `info`）。
8. 終態釋放鎖；`PAUSED` 持鎖；Bridge 重啟會把「RUNNING 但行程已不存在」的 run 標 `FAILED`（reason 含 `orphaned`）。
9. 單則 `log` 的 `line` 由 Bridge 截到 8,000 字元；事件 `ts` 為 UTC（`+00:00`）。

#### 3.5.2 事件對讀模型的更新

本表以 Architecture §7.3 為底，補上 §3.5.1 的 Bridge 事實（重複的 `STARTED`、`COMPLETED` 的發出時機、Token 歸因、失敗分類）與審核、告警、系統重設的連動。

「重算目標」＝套用 §3.5.3 的 R-goal 規則重新計算受影響目標的狀態。每處理完一則事件，**同一交易**更新 `execution_runs.console_last_seq`（冪等：重複處理同一 seq 不得產生第二筆審核項／告警／Token 樣本）。

| Bridge 事件 | 任務 | 目標／專案 | 其他副作用 |
|-------------|------|------------|-----------|
| `step STARTED`（第一次） | `→RUNNING`（`QUEUED→RUNNING`；來源不是 `QUEUED` 者先系統重設為 `QUEUED`）；`started_at` 為 null 才寫；`assigned_agent="AutoClaude"` | 重算目標（首個任務開始時 `PENDING→IN_PROGRESS`） | 套 §3.6.1 的 pause 決策；記錄「目前步驟」 |
| `step STARTED`（任務已 `RUNNING`） | 忽略（重做被打斷的步驟） | — | — |
| `step RETRYING` | `retry_count += 1`；維持 `RUNNING`（引擎內的 `FAILED→QUEUED→RUNNING` 折疊） | — | 評估 `HIGH_RETRY_RATE` |
| `step COMPLETED` | `RUNNING→VALIDATING→COMPLETED`；`completed_at`；`actual_tokens`（見下） | 重算目標 | 評估 `TASK_DURATION_EXCEEDED` |
| `step FAILED` | `RUNNING→FAILED`；`execution_log` 附錯誤訊息 | 重算目標 | 等 `status FAILED` 才分類（見下） |
| `token` | 依歸因加到該任務 `actual_tokens` | — | 寫 `run_token_samples`；評估 `TOKEN_BUDGET_*` 與 `scope.limits` |
| `alert` `ESCALATION`／`TOKEN_HALT` | — | — | 持久化 `ENGINE_ESCALATION`／`ENGINE_TOKEN_HALT`（`event_sub=0`）；一律轉發 SSE |
| `status PAUSED` | 無任務在跑 | 專案 `EXECUTING→READY`；重算目標 | 若有待決的閘 → 建審核項（§3.6.2） |
| `status RUNNING`（resume／restore 之後） | — | 專案 `→EXECUTING` | — |
| `status COMPLETED` | 殘留的 `RUNNING／VALIDATING`→`COMPLETED`（補正） | 重算目標；專案：全部未刪任務皆 `COMPLETED／SKIPPED`→`COMPLETED`，否則→`READY`（部分範圍的批次） | 最終 `metric-update`；關閉串流 |
| `status FAILED` | 依 `reason` 分類：以「引擎升級（ESCALATION）」開頭 → 最後一個 `FAILED` 任務 `FAILED→ESCALATED`；其餘（halt／異常／orphaned）維持 `FAILED`；範圍內仍 `QUEUED` 者→`PENDING`（系統重設） | 重算目標；專案→`FAILED` | 依自治等級建審核項（§3.6.2）；評估 `CONSECUTIVE_FAILURES` |
| `status CANCELLED` | 範圍內 `RUNNING`／`QUEUED`→`CANCELLED`（系統重設，US-E-06） | 重算目標；專案→`READY` | — |

**Token 歸因與 `actual_tokens`**：`delta = tokens_used − 上一則樣本的 tokens_used`（沒有上一則為 0）；歸因給「目前尚未 `COMPLETED`／`FAILED` 的步驟」所屬任務（`token` 事件先於同一步的 `COMPLETED`，所以對得上；沒有目前步驟則 `task_id` 為 null）。`tasks.actual_tokens` ＝跨所有批次的累計（每次加 `delta`）；`ExecutionStepResponse.tokensUsed` 取該任務**在本批次**的 `run_token_samples` 加總。

**`tasks.execution_log`**（US-T-05「最近一次執行日誌」）：寫入該任務最近一次執行的 STEP 摘要行與引擎 `WARN`／`ERROR`／`CRITICAL` 行，單任務上限 20,000 字元（超出保留尾端）；新一次 `STARTED`（第一次）時清空重寫。

#### 3.5.3 系統重設規則（PRD 附錄 B 沒有涵蓋 cancel／restore／後續批次）

附錄 B.3 不含 `QUEUED→CANCELLED`、`QUEUED→PENDING`、`CANCELLED／COMPLETED／RUNNING／VALIDATING→QUEUED`（B.3 允許進入 `QUEUED` 的只有 `PENDING／BLOCKED／FAILED／ESCALATED／PAUSED`），附錄 B.2 不含 `FAILED→IN_PROGRESS`、`COMPLETED→任何`；B.1 不含 `COMPLETED→EXECUTING`；但 US-E-06（取消）、US-E-11（還原）與「失敗後可重新執行」必須有這些結果。**裁決（§6 D-19）**：這些屬 **console-api 的系統重設操作**（由執行事件或審核決定觸發，領域層以專用方法直接設定狀態，不經 `StateMachines.requireTransition`），**手動 API（`PUT` 專案／`POST /tasks/{id}/retry` 等）仍完全遵守附錄 B**，`StateMachinesTest` 不受影響。

**R-goal（目標狀態推導；每個重算點都套用）**：令目標下未軟刪的任務集合為 T。
1. T 非空且全為 `COMPLETED`／`SKIPPED`：全為 `SKIPPED`→`SKIPPED`，否則→`COMPLETED`；
2. 否則若有任一 `FAILED`／`ESCALATED`→`FAILED`；
3. 否則若有任一 `RUNNING`／`VALIDATING`／`COMPLETED`→`IN_PROGRESS`；
4. 否則→`PENDING`。

**人工判定優先於 R-goal（AR-11）**：`GOAL_COMPLETED` 審核項被 `REJECT` 時，被審目標（剛完成的那個）設為 `FAILED`（人類判定；`TASK_CONFIRM`／`GOAL_CONFIRM` 的 `REJECT` 只取消 run，不標任何目標）。該目標的任務此時全是 `COMPLETED`，而 `:stop` 之後 Bridge 會發 `status CANCELLED`，消費者在該事件上對受影響的目標重算 R-goal——若不處理，R-goal 第 1 條會把目標算回 `COMPLETED`，蓋掉人類的判定。規則：**每個重算點的順序＝先對所有受影響目標套 R-goal，再對「本批次有 `kind=GOAL_COMPLETED`、`status=REJECTED` 且 `decided_by≠system` 的審核項」所指的目標套人工判定 `FAILED`**。因此人工否決的目標不會被同一批次後續的事件蓋回；直到新的批次（`execute`／`restore`／後續批次）把它納入範圍並開始任何一個任務，它才重新由 R-goal 推導。`SKIP` 的人工判定已體現在任務層（任務 `SKIPPED`，R-goal 第 1 條把 `COMPLETED`／`SKIPPED` 都算完成），不需要額外處理（E2E-05 步驟 7：G1 為 `COMPLETED`）；`ESCALATED` 類的 `REJECT` 不改變 run 與目標（目標本來就是 `FAILED`）。

| 觸發 | 專案 | 目標 | 任務 |
|------|------|------|------|
| execute 成功 | `→EXECUTING`（`DRAFT`／`FAILED` 先 `→READY`；`COMPLETED` 為系統重設，直接 `→EXECUTING`） | 不動（首個任務開始時才 `IN_PROGRESS`） | 範圍內非 `COMPLETED`／`SKIPPED` 者→`QUEUED`（`PENDING／BLOCKED／FAILED／ESCALATED／PAUSED→QUEUED` 屬 B.3；`CANCELLED／RUNNING／VALIDATING→QUEUED` 屬系統重設） |
| run `FAILED` | `→FAILED` | R-goal | 範圍內 `QUEUED→PENDING`；失敗任務依 §3.5.2 |
| run `CANCELLED` | `→READY` | R-goal | 範圍內 `RUNNING／QUEUED→CANCELLED` |
| run `COMPLETED` | 全完成→`COMPLETED`，否則→`READY` | R-goal | — |
| restore 被 Bridge 接受 | `→EXECUTING` | R-goal | 範圍內**不在**快照 `completed_step_ids` 內的任務→`QUEUED`（來源可為 `COMPLETED／FAILED／ESCALATED／CANCELLED／PENDING`；`SKIPPED` 不重設，restore 只允許最新批次故不會與之衝突）；被重設任務的 `actual_tokens` 保留（Token 已實際花費） |
| 審核 `SKIP`（後續批次） | 同 execute（後續批次） | R-goal | 該任務→`SKIPPED`（`ESCALATED→SKIPPED` 屬 B.3）；後續批次範圍＝專案內其餘非 `COMPLETED`／`SKIPPED` 任務；先標審核項 `SKIPPED` 再自動關閉其他 `PENDING` 項（§1.2.11） |
| 審核 `REJECT`（`GOAL_COMPLETED`） | 隨 `CANCELLED` | 被審目標設為 `FAILED`（人類判定，**優先於 R-goal**，見上） | 同 `CANCELLED` |
| 審核 `REJECT`（`TASK_CONFIRM`／`GOAL_CONFIRM`） | 隨 `CANCELLED` | 不另標，由 R-goal 推導 | 同 `CANCELLED` |
| 新批次建立時 | — | — | **前一批次尚 `PENDING` 的審核項自動關閉**：`status=REJECTED`、`decided_by=system`、`comment=已由第 <N> 批次取代`（避免對過期批次下決定） |
| run 進入 `COMPLETED`／`CANCELLED` | — | — | 該批次仍 `PENDING` 的 **gate 類**審核項（`TASK_CONFIRM`／`GOAL_CONFIRM`／`GOAL_COMPLETED`）自動 `REJECTED`（`decided_by=system`、`comment=執行已取消` 或 `執行已結束`）；`FAILED` 批次的 `ESCALATED` 審核項不在此列（它們正是待處置的對象） |
| 手動 `resume`／`restore`（不經審核） | — | — | 該批次 `PENDING` 的 gate 類審核項自動關閉：`resume`→`APPROVED`（`decided_by`＝呼叫者、`comment=以手動恢復處理`）；`restore`→`REJECTED`（`decided_by=system`、`comment=執行已還原`） |

#### 3.5.4 消費者生命週期（`RunEventConsumer`）

- **啟動時機**：① execute 成功（`after=0`）；② restore 被 Bridge 接受（終態 run 被 restore 後，原消費者已結束，須重啟；`PAUSED` 的 resume 沿用現有消費者）；③ **console-api 啟動時**，對每個 DB 狀態非終態的批次（`RUNNING`、`PAUSED`；`INITIALIZING` 見 §3.4.5 第 6 點）各啟一條，`after=console_last_seq`。
- **啟動掃描的對帳**：③ 先問 Bridge `GET /autoclaude/runs/{id}`：回 404 `run_not_found` → 不啟動消費者、DB 不動（狀態欄由 Bridge 擁有）、寫 WARN 日誌；`GET /executions/{runId}` 以 `bridge.runKnown=false` 表達，SSE 依 §2.3 第 5 點處理。Bridge 不可達 → 仍啟動消費者（由連線層重試，§3.1）。**另補一種情形（B2-3；`MonitorTicker.reconcile`）**：批次在 DB 已是終態（Bridge 已把 `execution_runs.status` 寫成 `COMPLETED`／`FAILED`／`CANCELLED`），但**專案仍是 `EXECUTING`**——console-api 停機期間漏掉了終態事件。此時同樣啟一條消費者，依 `console_last_seq` 從其後補處理（終態 `status` 事件連帶的專案／任務／審核項更新照常發生），處理完即結束。
- **重連**：連線失敗或閒置逾 45 秒視為斷線，指數退避 1→30 秒，以最後已處理的 Bridge seq 作 `after`（Bridge 的 stream 會先重播 `after` 之後的事件再接即時，毋須另外回補；缺口很大時可改以 `GET …/events?after=&limit=` 分頁取回）。
- **冪等與順序**：每則事件依 `seq` 處理，`seq ≤ console_last_seq` 一律略過（§3.5.2）；同一 run 的事件處理與控制操作以 per-run 互斥鎖序列化（§1.2）。
- **結束**：處理完終態 `status` 事件（含其衍生的審核項、告警、專案與任務狀態）後結束消費者，並依 §2.4 關閉該 run 的 SSE 訂閱連線；之後若 restore，由第 ② 點重啟。
- **位移持久化**：`console_last_seq` 存在 DB（V7），console-api 重啟不丟事件、不靠記憶體位移。

---

### 3.6 審核閘（自治等級 1～10）

AutoClaude 沒有審核鉤子，也不改它：閘點由 `ReviewGatePolicy` 依自治等級計算，以 Bridge 的 `:pause` 實現。**`:pause` 在「呼叫之後的下一個步驟邊界」生效**（Bridge `README`、`runner.py`、`test_e2e_lifecycle.py::test_pause_stops_at_the_step_boundary…` 已實證），所以閘點一律「**提前一步**」：在要停的那一步 `STARTED` 時就呼叫，等它的 `COMPLETED` 才呼叫就晚了一步（W3 任務書「每個 `step COMPLETED` 後立即 `:pause`」會多跑一個任務，§6 D-09）。

#### 3.6.1 pause 決策表（`step STARTED` 第一次出現時評估；每個 `(run, 步驟)` 只呼叫一次；Bridge 狀態不是 `RUNNING` 時不呼叫）

記號：`N`＝總步驟數；`i`＝剛開始的步驟位置（1 起）。

| 自治等級 | 呼叫 `:pause` 的條件 | 效果（邊界落點） | 之後建的審核項 `kind` |
|----------|----------------------|------------------|-----------------------|
| 1 Manual Confirm | `i < N` | 第 `i` 步完成後、第 `i+1` 步開始前停下 | `TASK_CONFIRM`（確認下一個任務）。第 1 個任務的確認＝使用者按「啟動執行」本身 |
| 2 Goal Confirm | `i` 是所屬目標的最後一步且 `i < N` | 該目標完成後、下一個目標開始前停下 | `GOAL_CONFIRM`（確認下一個目標） |
| 3 Review & Approve（預設） | 同等級 2 | 同等級 2 | `GOAL_COMPLETED`（審核剛完成的目標）；任務失敗另見 3.6.2 |
| 4 Exception Only | 不 pause | — | 只有失敗時（3.6.2） |
| 5 Full Autonomy | 不 pause | — | 只有致命失敗（3.6.2） |
| 6～10 Advanced | 不 pause；Console 的審核閘行為**同等級 5**（只有失敗才建審核項，§3.6.2）。差異只在引擎能力旗標（v1.3；v1.2 是「不另送引擎設定」）：等級 ≥ 6 使 `effAutoMutation` 為真、≥ 7 使 `effSelfEvolution` 為真，依 §3.4.2 物化 `minimax.enable_kernel_brain`，並在批次回應的 `engineCapabilities` 如實標示；等級照常記錄在 `execution_runs.autonomy_level` | — | 同等級 5 |

- 最後一個步驟（`i = N`）完成時 run 直接 `COMPLETED`，不暫停、不建審核項。
- **精度（Architecture §12 L-7）**：極短的步驟可能在 `:pause` 抵達前就越過邊界，暫停會晚一步生效。此時 `status PAUSED` 的位置不在預期的目標邊界；建審核項時以**實際位置**為準（`completedSteps=k`）：等級 1 照常 `TASK_CONFIRM`；等級 2／3 若 `k` 不是目標邊界則降級為 `TASK_CONFIRM`，`reason` 加註「（暫停點比預期晚一步）」。
- 使用者手動 `pause`、`TOKEN_BUDGET_EXCEEDED` 自動暫停造成的 `PAUSED` **不建審核項**（沒有待決的閘）。
- **閘點暫停旗標存記憶體（B2-4；`RunRegistry.Runtime.gatePauseRequested`／`gatePausedPositions`）**：「這次暫停是由審核閘造成」只記在 console-api 的記憶體，不入庫（它是由事件即可重建、遺失只會退回保守值的狀態）。若 console-api 在「已對 Bridge 呼叫 `:pause`」與「收到 `status PAUSED`」之間重啟，旗標遺失：該次 `PAUSED` **不建審核項**，須由使用者手動 `resume`（run 不會卡死，只是沒有待決項）。此視窗只有秒級，不另設持久化。

#### 3.6.2 審核項建立（`review_requests`；`kind` 的 CHECK 沿用 V3 的四種）

| 觸發 | `kind` | `goalId` | `taskId` | 佐證 `stepId`（`execution_steps.id`） | `reason` 樣板 | `allowedDecisions` |
|------|--------|----------|----------|--------------------------------------|---------------|--------------------|
| 等級 1 的閘點 `status PAUSED` | `TASK_CONFIRM` | 下一個任務的目標 | 下一個任務 | 剛完成步驟的 `COMPLETED` 列 | `Level 1：請確認是否繼續執行任務「<任務名>」` | `APPROVE`、`REJECT` |
| 等級 2 的閘點 | `GOAL_CONFIRM` | 下一個目標 | 該目標第一個任務 | 剛完成目標最後一步的 `COMPLETED` 列 | `Level 2：請確認是否開始目標「<目標名>」` | `APPROVE`、`REJECT` |
| 等級 3 的閘點 | `GOAL_COMPLETED` | 剛完成的目標 | 其最後一個任務 | 該步 `COMPLETED` 列 | `目標「<目標名>」已完成，等待人類審核` | `APPROVE`、`REJECT`、`RETRY` |
| `status FAILED` 且 `reason` 以「引擎升級（ESCALATION）」開頭（**等級 1～4**） | `ESCALATED` | 失敗任務的目標 | 失敗任務 | 該任務的 `FAILED` 列 | `任務「<任務名>」重試 <n> 次仍失敗，需要人類介入：<引擎 reason>`（`<n>`＝`FAILED` 列的 `attempt`−1）；若同時觸發 `CONSECUTIVE_FAILURES` 另附 `（連續 <n> 個任務失敗，已觸發 CONSECUTIVE_FAILURES 告警）` | `RETRY`、`SKIP`、`REJECT` |
| `status FAILED`（**等級 ≥ 5**，任何原因） | `ESCALATED` | 同上（找不到失敗任務則 null） | 同上（找不到則 null） | 同上 | 引擎升級時同上；否則 `執行失敗：<引擎 reason>` | 有 `taskId`：`RETRY`、`SKIP`、`REJECT`；無：`RETRY`、`REJECT` |

等級 1～4 遇到**非升級**的失敗（halt、異常、orphaned）不建審核項（只有 `status-change`、`alert` 與 FAILED 狀態可見）——這是 W3 任務書的字面規則；等級 5 與以上因引擎沒有「替代方案」能力，Console 行為與等級 4 相同，只是任何失敗都會建審核項（§6 D-18）。建立審核項時寫入 `event_seq`／`event_sub`（§2.2）並發 SSE `review-request`；`status` 初值 `PENDING`。

#### 3.6.3 審核決定的動作（`POST /executions/{runId}/review/{stepId}`）

| `kind` | `APPROVE` | `REJECT` | `RETRY` | `SKIP` |
|--------|-----------|----------|---------|--------|
| `TASK_CONFIRM` | Bridge `:resume`（run 須 `PAUSED`）→ 審核項 `APPROVED` | `:stop`→run `CANCELLED`（系統重設同 cancel）→ `REJECTED` | ✗ | ✗ |
| `GOAL_CONFIRM` | `:resume` | `:stop`→`CANCELLED` | ✗ | ✗ |
| `GOAL_COMPLETED` | `:resume` | `:stop`→`CANCELLED`，該目標設為 `FAILED`（人工判定優先於 R-goal，§3.5.3） | **restore** 到 `stepIdx` ＝「該目標第一個步驟的位置−1」的 checkpoint（＝該目標第一步之前的快照）；任務重設為 `QUEUED`、`retry_count+1`；`RETRIED` | ✗ |
| `ESCALATED` | ✗ | 關閉審核項（`REJECTED`）；run 維持 `FAILED`、任務維持 `ESCALATED`／`FAILED`、目標維持 `FAILED`；**不呼叫 Bridge** | **restore** 到 `stepIdx` ＝「失敗步驟位置−1」的 checkpoint（Bridge `restore` 接受終態 run，需重取鎖，可能 409）；失敗任務 `ESCALATED→QUEUED`、`retry_count+1`；`RETRIED`。沿用原 playbook（見 1.2.10 的注意） | 失敗任務設為 `SKIPPED`，並**以剔除它的新 playbook 開後續批次**（原因：Bridge `resume` 只收 `PAUSED`、`restore` 無法跳過步驟）；後續批次範圍＝專案內其餘非 `COMPLETED`／`SKIPPED` 任務，繼承原批次的自治等級與 `tokenBudget`／`limits`；回應標頭 `X-Follow-Up-Run-Id`；`SKIPPED` |

- 「步驟位置」指該批次 playbook 內的 1 起位置；checkpoint 以快照的 `step_idx`（0 起、＝還原後下一步）比對：要還原到位置 `p` 的步驟「之前」，取 `step_idx = p−1` 的快照。**找不到該快照（目標／失敗步驟是第一步，沒有更早的快照）**時，`RETRY` 改為：先 `:stop`（run 非終態時）、再開後續批次（範圍＝該目標／失敗任務及其後所有非完成任務），回應標頭 `X-Follow-Up-Run-Id`。
- 前置：gate 類的 `APPROVE`／`REJECT` 需 run 為 `PAUSED`；`ESCALATED` 類的 `RETRY`／`SKIP` 需 run 為終態（`FAILED`）。不符 → 409 `目前執行狀態不允許此操作`。
- 所有決定都寫 `decided_by`（JWT subject）、`decided_at`、`comment`；`REJECT` 於 ESCALATED 類不改變 run 狀態。審計日誌 `action=execution.review.<DECISION>`。
- 審核以外的操作（手動 resume／restore、cancel、run 進入終態、新批次建立）如何自動關閉待決審核項，見 §3.5.3 表的最後三列。
- **審核 `RETRY` 內部的 restore 也發 `RESTORE` 告警（F2-2）**：`GOAL_COMPLETED`／`ESCALATED` 的 `RETRY` 在 Bridge 端以 `restore` 實現，Bridge 與手動 restore 一樣會發 `alert`（`origin=ENGINE`、`code=RESTORE`、`severity=INFO`，id 為 Bridge seq，無 `alertId`、不持久化）；Console 一律轉發（SSE `alert`）。前端靠它清掉即時 DAG 疊加的舊狀態（`lib/domain/runLive.ts` 的 `isRestoreAlert`）；後端以 `ExecutionGateApiIT` 斷言該告警**恰 1 次**（真 Bridge 實測 seq=23 `alert RESTORE`）。找不到還原點而改開後續批次的那條路沒有 restore，也就沒有這則告警。
- 🔴 `GOAL_COMPLETED` 的 `RETRY` 在 run 為 `PAUSED`（gate 類審核項建立時 run 就是 `PAUSED`）時以 Bridge `restore` 實現，**依賴 AR-01 的 Bridge 修復**（§1.2.10）：修復前在 DB 模式會回 409 `同專案同路徑已有執行中的批次`（`holderRunId` 是自己）。找不到 `step_idx=p−1` 快照而改開後續批次的那條路（首個目標）不受影響，所以 E2E-04 的 RETRY 變體恰好不碰到這個缺陷。

---

### 3.7 告警規則（`API-ALR-01～06`；由消費者在每則事件後與 30 秒排程 tick 評估）

閾值**每次評估時**讀系統參數（快取不超過 5 秒）。去重：同一 `(project, rule, subject)` 在**未確認**前不重複產生（DB partial unique index 兜底；`INSERT … ON CONFLICT DO NOTHING`，Console 規則告警只有真的新增才發 SSE）。`ENGINE_ESCALATION`／`ENGINE_TOKEN_HALT` 同受此去重，但 Bridge 的 `alert` 事件本身一律照常轉發 SSE。**`ENGINE_ESCALATION` 的去重對象是 `step:<runId>:<stepId>`**（v1.2，C-7，QA O-14；`domain/service/AlertRules`）：`stepId` 每批次重新編號（§3.4.4），v1.1 的 `step:<stepId>` 會讓**不同批次**（也可能是不同任務）的升級被先前未確認的舊告警吞掉——逐批失敗的情境第 2、3 批沒有新告警列、只剩 SSE 轉發，使用者漏看；現在只有**同一批次的同一步驟**在未確認前再次升級才被去重（E2E-05 步驟 5），不同批次各自產生告警列。`ENGINE_TOKEN_HALT` 的 subject 維持 `step:<stepId>`（無則 `run:<runId>`）：同型缺口本版**未改**（主控裁決只列 `ENGINE_ESCALATION`），列為後續候選。持久化欄位：`project_id`、`run_id`、`rule`、`severity`、`subject`、`message`、`event_seq`／`event_sub`。

| 規則（`rule`） | 嚴重度 | 輸入 | 閾值來源 | 判定 | `subject` | 動作 | 訊息樣板 |
|----------------|--------|------|----------|------|-----------|------|----------|
| `TOKEN_BUDGET_WARNING` | WARNING | `token` 事件的累計 `tokens_used`、批次 `tokenBudget` | `execution.tokenBudgetWarningThreshold`（0.8） | `tokenBudget` 非 null 且 `used ≥ budget × 閾值` | `run:<runId>` | 持久化＋SSE | `Token 使用量已達預算的 <pct>%（<used> / <budget>）` |
| `TOKEN_BUDGET_EXCEEDED` | CRITICAL | 同上；另含 `scope.limits.taskTokens`／`goalTokens` 對該任務／目標的歸因累計 | — | `used > budget`；或任務累計 > `taskTokens`；或目標累計 > `goalTokens` | `run:<runId>`／`task:<taskId>`／`goal:<goalId>` | 持久化＋SSE＋**`:pause`**：只在**這則告警真的新增了一列**（`INSERT` 成功，沒被未確認的同規則同對象擋下）**且** Bridge 狀態為 `RUNNING` 時才呼叫（AR-21）；被去重擋下的重複判定不再呼叫，所以使用者 resume 後，同一個仍未確認的告警不會再把 run 暫停（E2E-08 步驟 6）；不建審核項，使用者以 resume 或 cancel 處置 | `Token 使用量已超出預算（<used> / <budget>），已要求暫停執行`；限額版：`任務「<名>」Token 用量 <n> 超過上限 <limit>，已要求暫停執行` |
| `CONSECUTIVE_FAILURES` | CRITICAL | 該目標下任務的終局結果序列（依其終局步驟時間；`COMPLETED` 為成功、`FAILED`／`ESCALATED` 為失敗、`SKIPPED` 略過） | `monitor.alertConsecutiveFailures`（3） | 最近 N 個終局結果全是失敗（在 `status FAILED` 與 `step FAILED` 處理後評估） | `goal:<goalId>` | 持久化＋SSE；Bridge 狀態仍為 `RUNNING` 才 `:pause`（Bridge 只能暫停整個 run；實務上首個 ESCALATION 已讓 run 結束，此規則在跨後續批次累計時才會觸發）；在該次 ESCALATED 審核項的 `reason` 註明 | `目標「<名>」連續 <n> 個任務失敗` |
| `AGENT_UNRESPONSIVE` | CRITICAL | 最後一則 Bridge 事件時間、探測環（`autoclaude.healthCheckPath`，v1.4 預設 `/health/deep`） | `monitor.alertAgentTimeoutSec`（300） | run 為 `RUNNING／PAUSING／CANCELLING`，且 `現在−最後事件時間 > 閾值`，**且**最近一次探測失敗（或 Bridge 不可達）；單純長步驟（探測正常）不告警。**v1.4（D-17）**：探測失敗包含深度探針的 503（`git`／`autoclaude`／`workspace`／`db` 任一失敗）；`sdd` 檢查只當資訊、不影響 503，所以 SDD 設定錯誤**不會**觸發本告警（主控裁決 Q4） | `run:<runId>` | 持久化＋SSE（不自動動作） | `Agent 已超過 <sec> 秒無回應` |
| `TASK_DURATION_EXCEEDED` | WARNING | `RUNNING` 任務的已執行時間（現在−`started_at`）；亦在 `COMPLETED` 時以實際耗時再評估一次 | `agent.taskTimeout` × `monitor.alertTaskDurationMultiplier`（600 × 2.0＝1,200 秒） | `耗時 > 閾值` | `task:<taskId>` | 持久化＋SSE | `任務「<名>」已執行 <sec> 秒，超過門檻 <threshold> 秒（<倍數> 倍）` |
| `HIGH_RETRY_RATE` | WARNING | 該目標在本批次已開始的任務與其中發生過 `RETRYING` 的任務 | 固定 50%（PRD；最小樣本 2 個已開始的任務） | `有重試的任務數 ÷ 已開始的任務數 > 0.5` | `goal:<goalId>` | 持久化＋SSE | `目標「<名>」重試率 <pct>%，超過 50%` |
| `ENGINE_ESCALATION` | CRITICAL | Bridge `alert`（`code=ESCALATION`） | — | 每則 | `step:<runId>:<stepId>`（v1.2；原 `step:<stepId>`） | 持久化（`event_sub=0`）＋轉發 | `引擎升級（ESCALATION）：<detail>` |
| `ENGINE_TOKEN_HALT` | WARNING | Bridge `alert`（`code=TOKEN_HALT`） | — | 每則 | `step:<stepId>`（無則 `run:<runId>`） | 持久化＋轉發 | `引擎因 Token／額度門檻停機：<detail>` |

其餘 Bridge `alert`（`LIMIT_RETRY`、`RESTORE`、`FORCE_KILL`、`CONFIG_OVERRIDE_IGNORED`、`STEP_TRACKING_GAP`、`ENV_LOST`、`BRIDGE_INTERNAL`）只轉發 SSE、**不持久化**。百分比一律四捨五入到整數。

**`CONSECUTIVE_FAILURES` 的觸發路徑說明（v1.2，C-22；QA O-15；只補說明，不改規則）**：規則本身照上表（同一目標最近 N 個終局結果全是失敗）。但在 UI 操作路徑下它**幾乎不可達**，原因都在 Bridge／引擎的行為與審核動作：① 引擎遇到第一個升級（ESCALATION）就結束整個批次，一個批次最多只貢獻一個失敗終局；② 審核 `SKIP` 把失敗任務標成 `SKIPPED`，而 `SKIPPED` 不計入終局序列（「略過」），原本會連續的失敗序列因此被切斷；③ 審核 `REJECT` 之後重跑 `ALL`，會在**同一個**任務再次失敗，序列不會累積到不同的任務；④ 只有用 `scope.mode=SELECTED` 加 `taskIds`，逐批各選一個（不同的）任務、且每批都失敗，才會在同一目標下累計出連續 N 個失敗終局。所以 QA 驗證此規則請用單元測試（`AlertRulesTest` 的假事件序列）或上述 `SELECTED` 逐批腳本，不要期待在一般的 ESCALATED→審核流程裡看到它。

---

### 3.8 監控聚合公式

#### 3.8.1 KPI（`GET …/metrics`）

記號：視窗 `W=[from,to)`；前一視窗 `W'=[from−(to−from), from)`；範圍任務集合 `S`＝有 `runId` 時為該批次 `dag` 內的任務，否則為專案內全部未軟刪任務；「步驟列」＝`execution_steps` 中屬於 `S` 的列（`timestamp` 為 Bridge 寫入時間）。

| KPI | 公式 | `previousValue` |
|-----|------|-----------------|
| `taskCompletionRate` | `S` 中「在時點 `T` 之前已有 `COMPLETED` 步驟列」的相異任務數 ÷ `\|S\|` × 100；`value` 取 `T=to` | 取 `T=from` |
| `taskSuccessRate` | `C ÷ (C+F) × 100`，`C`＝`W` 內有 `COMPLETED` 列的相異任務數、`F`＝`W` 內有 `FAILED` 列的相異任務數；`C+F=0`→null | 同公式套 `W'` |
| `retryRate` | `W` 內有 `RETRYING` 列的相異任務數 ÷ `W` 內有 `STARTED` 列的相異任務數 × 100；分母 0→null | 同公式套 `W'` |
| `averageRetryCount` | `W` 內 `RETRYING` 列數 ÷ `W` 內有 `STARTED` 列的相異任務數（小數 2 位）；分母 0→null | 同公式套 `W'` |
| `totalTokens` | `run_token_samples.delta` 在 `W` 內之和（限範圍批次） | 套 `W'` |
| `averageTaskDurationSec` | `S` 中 `completed_at ∈ W` 且 `started_at` 非 null 的任務之 `completed_at−started_at` 平均（秒，小數 2 位）；無樣本→null | 套 `W'` |
| `tokenBudgetUsageRate` | 範圍批次中 `started_at < to` 者：`Σ total_tokens_used ÷ Σ token_budget × 100`（只算有預算的批次）；無預算→null | null |
| `projectCompletionRate` | 全域：`status=COMPLETED` 的專案數 ÷ 非 `ARCHIVED` 且未軟刪的專案數 × 100（現況，不隨視窗） | null |
| `goalAchievementRate` | 專案內 `COMPLETED` 目標數 ÷ 未軟刪目標數 × 100（有 `runId` 時限該批次範圍的目標；現況） | null |
| `agentAvailability` | `W` 內成功的健康探測數 ÷ 探測總數 × 100（探測環在記憶體，重啟即清空；視窗超出保留範圍就用現有樣本；沒有樣本→null）。**v1.4（D-17）**：探測預設打 `/health/deep`，「成功」＝回 2xx；503（`git`／`autoclaude`／`workspace`／`db` 任一自檢未通過；`sdd` 只當資訊）、其他非 2xx、連線失敗、逾時都是失敗樣本——v1.3 以前打淺層 `/health`，Bridge 行程活著就恆成功，引擎壞了也不降（完整性審查 I-03）。環形緩衝在記憶體、重啟即清空，所以升級後不會混到舊語意的樣本 | null |

`delta`＝`value − previousValue`（兩者皆非 null 才有）。分布類欄位：`taskStatusDistribution`＝`S` 的 `tasks.status` 現況計數（十一態一律出現）；`taskDurations`＝`S` 中 `completed_at ∈ W` 的任務依耗時由長到短取 10 筆；`retryDistribution`＝`S` 中任務依 `retry_count`（現值，≥5 併入 5）分桶，桶 0～5 一律出現。

#### 3.8.2 趨勢

- **token-trend**：視窗內的 `run_token_samples` 依 `bucket`（UTC 整點或整日）分桶，`tokens`＝桶內 `delta` 之和，`cumulativeTokens`＝自 `from` 起累計；有資料的桶才輸出；`budget`＝樣本所屬批次的 `token_budget`（多批次取桶內最新批次）。
- **task-trend**：視窗內步驟列依 `bucket` 分桶，`started`／`completed`／`failed`／`retried`＝桶內 `STARTED`／`COMPLETED`／`FAILED`／`RETRYING` 列數；有資料的桶才輸出。

#### 3.8.3 日誌衍生（`GET …/logs`）

| 來源 | `id` | `source` | `level` | `message` | 時間 |
|------|------|----------|---------|-----------|------|
| `execution_steps` 列 | `step:<列 id>` | `STEP` | `STARTED`／`COMPLETED`→`INFO`；`RETRYING`→`WARN`；`FAILED`→`ERROR` | 同 §2.5 的 STEP 訊息（`COMPLETED` 不含 Token） | `timestamp` |
| `execution_runs` 開始 | `run:<runId>:started` | `RUN` | `INFO` | `Run #<n> 開始執行（自治等級 <L>）` | `started_at` |
| `execution_runs` 終態 | `run:<runId>:<status>` | `RUN` | `COMPLETED`→`INFO`、`CANCELLED`→`WARN`、`FAILED`→`ERROR` | `Run #<n> 已完成`／`已取消`／`失敗` | `completed_at` |
| `alerts` 列 | `alert:<id>` | `ALERT` | `WARNING`→`WARN`、`CRITICAL`→`ERROR` | 告警 `message` | `created_at` |
| `review_requests` 建立／決定 | `review:<id>:requested`／`review:<id>:decided` | `REVIEW` | `INFO` | `待審核：<reason>`／`審核 <決定>：<decided_by>` | `requested_at`／`decided_at` |

篩選：`level`（衍生等級，`ALL` 不篩）、`taskId`（只留帶該 `task_id` 的 STEP 列；RUN／ALERT／REVIEW 列在有 `taskId` 篩選時排除）、`q`（`message` 含關鍵字）、`runId`、`from`／`to`；穩定排序鍵＝`(timestamp, id)`（`order` 決定升降冪）。

---
## 4. 前端頁面 ↔ 端點矩陣

依據：設計稿 `Design_ConsoleUI/README.md` 畫面 6～9 與 `screenshots/06-import.png`～`09-settings.png`，並補上 PRD §5.2.5、§5.3.6、§5.4.5、§5.5.4 有、而設計稿沒畫的元素。表中「→」前是端點，「→」後是欄位。**Phase 1+2 已有的資料（專案名稱、目標清單、`signedOff` 旗標等）用 `Phase 2` 標示，不重列端點。**

### 4.1 匯入頁 `/import`（畫面 6）

| # | UI 元素 | 資料來源 | 備註 |
|---|---------|----------|------|
| I-01 | 來源頁籤：上傳檔案／貼上文字／歷史記錄 | 純前端狀態 | 設計稿 README 文字提到「URL 之類」，**截圖只有這三個頁籤**；契約不提供 URL 匯入（§4.6 G-I1） |
| I-02 | 拖放區（.md／.pdf／.docx，10MB） | `POST /import/upload`（multipart `file`）→ `ImportRecordResponse.id/status` | 413／415／422 的 `reason` 顯示在拖放區下方（附錄 B） |
| I-03 | 貼上文字的文字區 | `POST /import/text`（`content`、`sourceType`）→ `ImportRecordResponse` | |
| I-04 | 自治等級下拉（Level 1～10） | `ParseOptions.autonomyLevel`；預設值 ← `GET /settings/agent`→`defaultAutonomyLevel` | |
| I-05 | 執行路徑輸入 | `ParseOptions.executionPath` | 無瀏覽按鈕（ADR-001 G-15）；絕對路徑格式驗證錯誤見 `errors[]`。`ParseOptions.specDir` **沒有 UI 欄位**（F1-3；設計稿與任務書都沒畫，契約 D-03：路徑 A 以 `executionPath` 探測即可，明示 `specDir` 只留給 API 呼叫端；前端 `components/domain/import/SourceCard.tsx` 無此欄位） |
| I-06 | 補充說明文字區 | `ParseOptions.additionalPrompt`（≤4,000） | |
| I-07 | 「開始解析」按鈕與「解析中」畫面 | `POST /import/{id}/parse`（同步，最長約 `model.timeout` 秒；經 nginx 時上限 180 秒，§0.7） | 設計稿說明文字「套用有界閘：步驟 ≤24／Kahn 無環／prompt 非空」為靜態字串 |
| I-08 | 有界閘違規顯示（US-I-10） | parse／result 的 **422** → `errors[].gate／detail／location`（全部列出，不截斷）；重新整理或從歷史重開後以 `GET /import/{id}` → `lastParseErrors` 還原同一份清單 | 設計稿沒有這個錯誤區塊；須補一個清單元件（§4.6 G-I3） |
| I-09 | 規格被拒顯示 | 422 `SDD 規格檢查未通過` → `details.bridgeReason／detail` | 同上 |
| I-10 | 步驟 2 樹狀預覽（專案→目標→任務） | `ParseResultResponse.parsedResult`；重新整理後以 `GET /import/{id}` → `parsedResult` 還原 | `parsedResult` 在第一次成功解析前為 null，`parsePath` 同（V5，AR-07）；歷史列表重開 `UPLOADED` 的記錄時據此判斷「還沒有樹」 |
| I-11 | 節點編輯（✏️）／刪除（🗑️）／新增目標／新增任務／拖曳排序 | 前端先改本地樹，儲存時 `PUT /import/{id}/result`（整樹覆寫） | 新增目標須自行產生 `key`；拖曳後 `dependsOn` 仍用 `key` 引用，不受順序影響；**編輯會撤銷 signoff**，UI 應提示 |
| I-12 | 解析提示（evaluator 被清空、通過標準為佔位） | `ParseResultResponse.warnings[]`；重新整理或從歷史重開後以 `GET /import/{id}` → `warnings[]` 還原（v1.2，C-10） | 設計稿沒有；建議用黃色提示列 |
| I-13 | 「signed_off=false」警示橫幅與「signoff 審批」按鈕 | `ParseResultResponse.signedOff`；按鈕 → `POST /import/{id}/signoff {approver}` | **approver 由前端以目前登入者帶入**（登入回應 `TokenResponse` 無 username：從 access token 的 `sub` 取，Phase 1+2 已如此） |
| I-14 | 已 signoff 綠勾 | `ImportRecordResponse.signedOff／signedOffBy／signedOffAt` | |
| I-15 | 「放棄」 | `POST /import/{id}/reject`（補充端點） | |
| I-16 | 「確認匯入」（未 signoff 時禁用） | `POST /import/{id}/confirm` → 201 `ProjectResponse`；成功後導向 `/projects/{id}` | 後端對未 signoff 回 409 `草案尚未 signoff，不可確認匯入`（前端禁用只是體驗） |
| I-17 | 歷史記錄列表：匯入時間、來源檔名、狀態、專案連結 | `GET /import?page&size&status&q` → `createdAt／sourceFileName／status／projectId` | 點一筆 → `GET /import/{id}` 重新開啟審核 |
| I-18 | 解析選項還原（自治等級、執行路徑、補充說明、`specDir`） | `GET /import/{id}` → `parseOptions`（v1.2，C-10；從未 parse 過為 null） | 重開 `UPLOADED`／`PARSED`／`REVIEWING` 記錄時把選項填回表單（取代 v1.1 的「要重填」限制，F1-2）；解析失敗後重開也保有該次的選項 |

### 4.2 執行頁 `/projects/[projectId]/execute`（畫面 7）

| # | UI 元素 | 資料來源 | 備註 |
|---|---------|----------|------|
| E-01 | 標題「專案執行：{名稱}」 | Phase 2 `GET /projects/{id}` | |
| E-02 | 「執行已鎖定 — 草案未 signoff」橫幅＋「前往審批」 | Phase 2 `projectDetail.signedOff`；觸發 409 時另以 `details.unsignedGoalIds／unsignedTaskIds` 標示哪些未審批（`unsignedProjectId` 缺席＝專案本身已簽，`details` 不輸出 null） | 啟動按鈕禁用邏輯＝專案、所選目標、所選任務皆 signedOff |
| E-03 | 自治等級下拉 | `StartExecutionRequest.autonomyLevel`（預設專案的 `autonomyLevel`） | |
| E-04 | Token 預算輸入（設計稿示例 100,000） | `StartExecutionRequest.tokenBudget`；預設值 ← `GET /settings/execution`→`globalTokenBudget`（種子 1,000,000） | 設計稿的 100,000 只是示例 |
| E-05 | 執行範圍 checkbox（目標＋「(N tasks)」） | Phase 2 `projectDetail.goals[]`（`name`、`taskCount`、`signedOff`）→ 勾選結果組成 `scope.mode=SELECTED, goalIds[]` | 全勾＝`mode=ALL`。任務層級選取（US-E-02「特定任務」）設計稿沒畫；契約支援 `scope.taskIds`，**前端已實作**（W4-F2 起：`ScopeTree.tsx`、`ExecuteView.tsx`；v1.4 回寫，§4.6 G-E1） |
| E-06 | 「啟動執行」 | `POST /projects/{id}/execute` → 201 `ExecutionRunResponse` | 409／422 的 `reason`＋`details` 顯示（附錄 B） |
| E-07 | 「暫停」「恢復」「取消」 | `POST /executions/{runId}/pause｜resume｜cancel`；按鈕啟用規則看 `ExecutionRunDetailResponse.status` 與 `bridge.status`（`PAUSING`／`CANCELLING` 時顯示處理中、禁用） | |
| E-08 | 「從斷點恢復」 | `GET /executions/{runId}/checkpoints`（列表）→ 選一筆 → `POST /executions/{runId}/restore/{checkpointId}` | **設計稿沒有選擇斷點的對話框**（§4.6 G-E2）；列表欄位：`name`、`createdAt`、`completedSteps` |
| E-09 | 「Run #N」與狀態點（閃爍） | `ExecutionRunDetailResponse.runNumber／status`（`RUNNING` 閃爍）；即時更新 ← SSE `status-change` | |
| E-10 | 「x / y 任務完成」與進度條 | `completedSteps／totalSteps`；即時 ← SSE `progress-update.completedSteps／totalSteps／progressPct` | |
| E-11 | 「Token: 45,230 / 100,000」與進度條（超閾值變色） | `totalTokensUsed／tokenBudget`；即時 ← SSE `token-update.tokensUsed／budgetUsageRate`；變色閾值 ← `GET /settings/execution`→`tokenBudgetWarningThreshold`（預設 0.8）與 100% | |
| E-12 | 耗時（PRD 有、截圖未見） | `elapsedSec`；即時 ← SSE `metric-update.elapsedSec` | |
| E-13 | DAG 視覺化（G1→G2→G3、任務節點、展開／收合／全螢幕） | `GET /executions/{runId}/dag` → `nodes[].kind／label／status／goalId／sequence`、`edges[]`；即時更新節點狀態 ← SSE `log`（STEP）的 `taskId`＋`stepStatus` | 節點色票由前端依狀態表（`lib/domain/status.ts`）；展開／收合為前端狀態；**全螢幕＝v1.4 補實作（E-22；v1.3 以前 `DagCard` 沒有這顆鈕也沒有登記，完整性審查 D-01）** |
| E-14 | 即時日誌（深色終端機）與「SSE 串流」狀態點 | SSE `/stream/executions/{runId}/logs` 的 `log`（`ts`、`level`、`message`）；狀態點＝客戶端連線狀態 | 預設顯示 `source=STEP`，另設「顯示引擎原始輸出」開關（`source=ENGINE` 量大）。重新載入頁面：`tail=200` 重播 |
| E-15 | 自動捲動、日誌搜尋 | 純前端（對已收到的行過濾） | |
| E-16 | 待審核項目卡：計數 badge、列標題 | `ExecutionRunDetailResponse.pendingReviews[]`（`reason`、`goalName`、`taskName`）；badge 計數與即時新增 ← SSE `review-request` | |
| E-17 | 每列按鈕：通過／重試／跳過／拒絕 | `POST /executions/{runId}/review/{review.id}`，`decision` ← 按鈕；**按鈕是否可按＝`review.allowedDecisions`** | 設計稿四顆按鈕對所有項目顯示；`ESCALATED` 無「通過」、gate 類無「跳過」→ 以 `allowedDecisions` 禁用 |
| E-18 | 「查看結果／查看日誌」「修改任務」（PRD） | 導向：任務詳情 `/projects/…/tasks/{taskId}`（Phase 2）＝`review.taskId` | **F2-5**：前端只做「查看任務」連結（`components/domain/execute/ReviewCard.tsx`）——沒有獨立的「查看結果」「查看日誌」目的地：日誌以監控頁的日誌查詢涵蓋（§4.3 M-13），結果在任務詳情 |
| E-19 | 空狀態文字（無待審核項目） | `pendingReviews=[]` | |
| E-20 | 後續批次切換 | 審核 `SKIP`／`RETRY` 回 `X-Follow-Up-Run-Id`；或 `GET /projects/{id}/executions` 取最新一筆 | 前端收到標頭後改看該 run 並重連 SSE |
| E-21 | 引擎能力晶片「自動突變」「自演化」（v1.3，D-11；設計稿沒畫，建議放在批次資訊列旁） | `ExecutionRunResponse.engineCapabilities`：`POST execute` 的 201、`GET /executions/{runId}`；切換批次後取該批次的值 | 每枚晶片三態：`ENABLED`＝已啟用、`OFF`＝關閉、`UNAVAILABLE_NO_API_KEY`＝無金鑰不可用。**`selfEvolution` 的 `ENABLED` 必須讓人看得出「只提案、不自動套用」**（晶片文字或 tooltip，例：「自演化（僅提案）：已啟用」）——引擎只產生演化提案、不套用（§3.4.2）；`autoMutation` 的 `ENABLED` tooltip 建議寫「Brain 逐步校正：失敗步驟先由 Brain 改寫再重試」。欄位缺席（V10 之前的批次）不顯示晶片。文字與顏色由前端字典決定，契約只定義值域與語意 |
| E-22 | DAG 卡「全螢幕」切換（v1.4，D-20；PRD §5.3.6 wireframe 的 `[展開/收合] [全螢幕]`，完整性審查 D-01） | 純前端狀態，沒有端點 | 在 `DagCard` 標題列「展開任務／收合任務」旁加一顆「全螢幕」鈕：把 DAG 卡放大到整個視窗，建議以**頁面內覆蓋層**呈現（`position: fixed` 鋪滿視窗），**不使用瀏覽器 Fullscreen API**——它需要使用者手勢、無頭測試不可用，驗收不依賴它。覆蓋層內按鈕文字變「結束全螢幕」（`aria-pressed` 同步），`Esc` 同樣結束；結束後焦點回到「全螢幕」鈕（同 DEF-AC-011 的焦點歸還規則）。全螢幕期間 SSE 驅動的節點狀態更新照常；展開／收合狀態在進出全螢幕時保留。驗收由前端單元測試（開／關／Esc／焦點歸還）與一支 e2e 斷言（點「全螢幕」→DAG 容器尺寸等於視窗）涵蓋 |

### 4.3 監控頁 `/projects/[projectId]/monitor`（畫面 8）

| # | UI 元素 | 資料來源 | 備註 |
|---|---------|----------|------|
| M-01 | 時間範圍下拉（預設 24 小時） | 前端換算成 `from`／`to` 帶給每個監控端點 | |
| M-02 | 執行批次下拉（PRD §5.4.5 有、設計稿未畫） | `GET /projects/{id}/executions` → `runNumber／status／bridgeStatus` → `runId` 參數 | §4.6 G-M1。`bridgeStatus` 為 v1.2 新增（C-11）：`PAUSING`／`CANCELLING` 顯示處理中晶片（§1.2.2） |
| M-03 | 指標卡「完成率」 | `GET …/metrics` → `taskCompletionRate.value／delta` | 設計稿「完成率 34.8%」＝專案內任務完成進度，**不是** PRD 的「專案完成率」（全域，`projectCompletionRate`） |
| M-04 | 指標卡「任務成功率」 | `taskSuccessRate.value／delta` | ↑／↓ 與顏色由前端依語意決定（成功率升＝好） |
| M-05 | 指標卡「重試率」 | `retryRate.value／delta` | 升＝壞；顏色由前端決定 |
| M-06 | 指標卡「Token 消耗」 | `totalTokens.value／delta` | |
| M-07 | PRD 另外六項 KPI（專案完成率、目標達成率、平均重試次數、Token 預算使用率、平均任務執行時間、Agent 可用率） | 同一個 `metrics` 回應的其餘 `MetricValue` | 設計稿只畫四張卡；其餘供 Dashboard 或日後版面（ADR-001 G-13）。PRD §5.4.2 對「專案完成率」「目標達成率」寫的「環形」，**以設計稿畫面 8 的數值卡為準**（主控裁決 C-13；ADR-001 D11 已定視覺以設計稿為準，G-20 登記） |
| M-08 | Token 使用趨勢（折線＋虛線預算線＋面積） | `GET …/token-trend` → `bucketStart／tokens／cumulativeTokens／budget`（折線畫 `cumulativeTokens`；預算線畫 `budget`） | 圖例「預算線／Token 使用」靜態。`DAY` 桶的 X 軸標籤用瀏覽器本機時區（桶起點仍是 UTC；F2-1，§1.3 的 `bucket` 說明） |
| M-09 | 任務狀態分佈（完成／執行中／失敗／待處理 四條） | `metrics.taskStatusDistribution`（前端分組：完成＝`COMPLETED`；執行中＝`RUNNING＋VALIDATING＋QUEUED`；失敗＝`FAILED＋ESCALATED`；待處理＝其餘） | |
| M-10 | 執行時間分佈（垂直柱） | `metrics.taskDurations[]` → `taskName／durationSec` | |
| M-11 | 任務執行趨勢、成功／失敗比率、重試次數分佈（PRD §5.4.2 趨勢圖表，設計稿未畫） | `GET …/task-trend`、`metrics.retryDistribution` | §4.6 G-M2 |
| M-12 | 事件時間軸（PRD，設計稿未畫） | `GET /executions/{runId}/steps`（`timestamp／status／taskName`；一個批次的步驟事件，`size` 最大 200，以 `afterSeq` 續頁） | §4.6 G-M2。`task-trend` 依 PRD §7.1.6 只回 `List<TaskTrendPoint>`（不含事件清單）；M-02 選「全部批次」時，時間軸取最新一筆批次（`executions` 列表第一筆）當來源。**追蹤鏈視圖（US-M-09）以「批次下拉＋事件時間軸＋日誌查詢」涵蓋，不另做獨立視圖**（主控裁決 2026-10-15，C-14；設計稿與契約皆無獨立的追蹤鏈視圖） |
| M-13 | 執行日誌查詢卡：等級下拉（全部／INFO／WARN／ERROR）、日誌列 | `GET …/logs?level&q&page&size` → `timestamp／level／message` | PRD 另有關鍵字搜尋（`q`）、任務 id 篩選（`taskId`）；設計稿只畫等級下拉 |
| M-14 | 告警卡：列、「已確認」或「確認」 | `GET …/alerts` → `createdAt／message／severity／acknowledged`；確認 → `POST /monitor/alerts/{id}/acknowledge`（204） | 即時新增 ← SSE `alert`（執行頁／監控頁皆可訂閱同一 run） |
| M-15 | 「查看詳情」（PRD） | 無專用端點：展開該列顯示 `rule／subject／runId／message` | |
| M-16 | 「匯出報表」 | `GET …/report?format=csv｜pdf`（檔案下載；CSV 送 `Accept: text/csv`、PDF 送 `Accept: application/pdf`） | v1.2：PDF 已提供（§1.3.7，C-4；取代 v1.1 的 501）；檔名取 `Content-Disposition`（CORS 已暴露） |
| M-17 | 「設定告警」 | 導向 `/settings` 的「監控」分頁（`monitor.*`） | 無專用端點 |
| M-18 | 「自訂儀表板」（US-M-08） | 純前端（版面存 `localStorage`，ADR-001 G-18） | 無後端欄位 |
| M-19 | Agent 狀態指示燈與資源使用（US-M-10；設計稿未畫） | `metrics.agentAvailability`；即時連線 ← `GET /executions/{runId}`→`bridge.connected／status`、`currentStep`；**資源使用（v1.3，D-12）← 同一個回應的 `bridge.resources`** | **「資源使用」欄的顯示格式**：`CPU 12.3%・記憶體 345 MB・3 行程`——`cpuPercent` 小數 1 位加 `%`；`memoryBytes ÷ 1,048,576` 四捨五入到整數加 ` MB`（≥ 1,024 MB 改以 GB：÷ 1,073,741,824、小數 1 位；< 1 MB 顯示 `<1 MB`）；`processCount` 加 ` 行程`；三段以全形中點「・」相連。**沒有資料一律顯示單一的 `—`**：`resources` 為 null 或缺席、`bridge.connected=false`、或批次已是終態（詳情輪詢在終態後會停止，最後一次抓到的數字不得繼續顯示）。v1.2 的說明句「資源使用情況（CPU／記憶體）：Engine Bridge 目前沒有提供這項資料…」**移除**（`agent-note` 只留 Bridge 實例資訊）。`sampledAt` 建議放 tooltip（非驗收項）。數字的新鮮度＝詳情輪詢（15 秒）加取樣週期（5 秒），最舊約 20 秒（§3.1.2） |
| M-20 | 「AISDLC_SDD 引擎」卡（v1.4，D-16；設計稿未畫，建議放在 Agent 狀態卡旁） | `GET /api/v1/engines/sdd?project=<選定>`（§1.7.1）；輪詢 **30 秒**，分頁不可見時暫停；**不隨 Console 專案或執行批次的下拉變動**——SDD 引擎是全域的，FSM 專案與 Console 專案是兩個不同的東西 | 顯示：引擎狀態點與版本（`version.latest`）；FSM 專案下拉（`projects[].project`；預設＝上次選的且仍在清單內者〔`localStorage` 記住，只是方便〕，否則清單第一個，所以首次載入是兩段請求：先不帶 `project` 取清單、選定後帶 `project` 取內容）；選定專案的 `currentState`、`currentSprint`（「Sprint N」）、`updatedAt`（本機時區）、**待人工**＝`humanPending.count`（0 顯示「無」，1 顯示「等待人工確認」並可展開 `items[0].entered_at`）、**最近決策**＝`decisionTrace` 倒序最多 5 筆（`ts`、`from → to`、`reason`）。不可用文案依 `reason`：`bridge_unreachable`「Engine Bridge 無法連線」、`sdd_unavailable`「找不到 AISDLC_SDD 目錄（請檢查 Bridge 的 SDD_ROOT）」、`bridge_error`「Engine Bridge 回應異常」、`fsm_not_found`「找不到所選專案的 FSM 狀態檔」、`fsm_state_unreadable`「FSM 狀態檔無法讀取」；`available=true` 且 `projects=[]`：「尚無 FSM 狀態檔（SDD runtime 執行後才會產生）」。**唯讀**：卡片沒有任何寫入動作（ADR-001 D22 第 3 點）；`retryHistory`、`rtmCoverage`、`frozenStages` 不顯示，資料留在 API 供 NFR-OBS-01 對照與日後使用。FSM 專案清單在開發機上會含 SDD 測試留下的 `test-<數字>` 專案（§3.1.3），照列 |
| M-21 | 「AISDLC_SDD 引擎」卡的 v1.5 改動（D-115-02；**覆蓋 M-20 中「不隨 Console 專案或執行批次的下拉變動」與「唯讀、沒有任何寫入動作」兩句的適用範圍**） | `GET /api/v1/engines/sdd?projectId=<目前專案>`（§1.10.4）；專案沒有綁定時行為同 M-20（不帶 `projectId`、全域清單） | ①**專案帶入**：監控頁所屬的 Console 專案有綁定（`sddProject` 非空）時，卡片改帶 `projectId`，FSM 專案預設為 `sddProject`（下拉仍可改選同一個狀態目錄內的其他專案）；沒有綁定時維持 M-20。②**階段進度與 ESCALATION 標示**：見 §4.7.3。③**卡片仍然唯讀**——核准凍結只出現在專案詳情的「SDD 治理」區（§4.7.1），不在監控卡。④新增 `reason` 文案：`sdd_root_rejected`「專案路徑不在 Bridge 允許的根目錄內（或已不存在）」 |

### 4.4 設定頁 `/settings`（畫面 9）

| # | UI 元素 | 資料來源 | 備註 |
|---|---------|----------|------|
| S-01 | 分類頁籤（模型／Agent／執行／監控／AutoClaude／SDD） | `GET /settings` 的六個 key | 頁籤文字與圖示由前端字典提供 |
| S-02 | 每個參數列：label、說明 | **label**：前端字典（鍵 `category.key`；契約不含）；**說明**：`ConfigResponse.description` | §4.6 G-S1。`model.apiUrl` 的表單提示寫「完整的 chat-completions 端點 URL」（AR-09）；`monitor.refreshIntervalMs` 最小 10000（AR-06） |
| S-03 | 控制項型別（text／number／password／enum／bool） | `valueType`：`STRING`→text、`INTEGER／LONG／FLOAT`→number、`ENCRYPTED`→password、`ENUM`→enum（選項＝`options`）、`BOOLEAN`→bool；數字範圍＝`min`／`max` | 加密鍵（`ENCRYPTED`）的 `value` 恆為遮罩字串，前端以 **`hasValue`** 判斷「尚未設定」（F1-6；`components/domain/settings/SettingsView.tsx`、`SettingControl.tsx`） |
| S-04 | 值與預設值 | `value／defaultValue`；重置圖示 → `POST /settings/{category}/{key}/reset` | 加密鍵重置需 `?confirm=true` |
| S-05 | 密碼欄遮罩與顯示切換 | 預設 `value=••••••••`＋`hasValue`；顯示 → `GET /settings/{category}?reveal=true`（**僅 ADMIN**） | 非 ADMIN 時切換按鈕應禁用（設計稿未畫角色差異，§4.6 G-S2）。`reveal=true` 以**分類**為單位（沒有單鍵揭露端點）：前端每按一次「顯示」＝一次 `GET /settings/{category}?reveal=true`＝一筆審計（`settings.reveal`，只記分類與次數），只取要的那一鍵（F1-5） |
| S-06 | 驗證錯誤紅字 | 400 `errors[].field／message`；token_guard 違規見 reason `halt_threshold_pct 必須大於 compact_threshold_pct` | 前端以 zod 鏡射同規則（NFR-SEC-05 第 ③ 道） |
| S-07 | 「測試連線」與結果（連線成功（延遲 230ms）） | `POST /settings/test-connection`（可帶表單內尚未儲存的 `apiUrl`／`apiKey`）→ `success／latencyMs／message` | 422（SSRF／allowlist）顯示 reason 與 `details.violation`。`apiUrl` 是完整端點，測試會對它送一則 1-token 的 ping（供應商端約消耗一個 token），不再是 `GET /v1/models`（§1.5.7） |
| S-08 | 修改歷史卡（時間／參數／舊值→新值／@使用者） | `GET /settings/history?category&page&size` → `changedAt／category.key／oldValue／newValue／changedBy` | 加密值顯示 `••••••••` |
| S-09 | 「儲存變更」 | **逐鍵** `PUT /settings/{category}/{key}`（僅送有修改的鍵）；token_guard **任一**鍵有改就改用 `PUT /settings/execution/token-guard`（原子；對端沒改就帶畫面目前值，PRD §7.1.8；F1-4——契約 §1.5.3 的單鍵端點加跨鍵校驗仍然可用，但前端一律走群組端點）。值未變的鍵不寫歷史（§1.5.4），所以帶對端現值不會多一筆歷史 | 沒有單一的批次儲存端點；PRD 的「修改後立即儲存」也可逐欄儲存。取捨：他人恰在同時改了對端鍵時，會被畫面上的舊值覆寫（單人使用機率極低；`SettingsView.tsx` 的 `useUpdateTokenGuard`） |
| S-10 | 「全部重置為預設值」 | `POST /settings/{category}/reset`（補充端點；整個分類） | |
| S-11 | 「匯出設定」「匯入設定」 | `POST /settings/export`（下載 JSON）；`POST /settings/import`（multipart）→ `applied／skipped／errors[]` | |
| S-12 | 影響範圍提示（US-S-08） | `ConfigResponse.impactNote`：寫入前的確認對話框顯示 | |
| S-13 | 「僅儲存、不影響引擎」標示（設計稿未畫） | `ConfigResponse.effect=STORED_ONLY／UNVERIFIED` | 建議在 label 旁加小標籤（誠實呈現，Architecture §11.4）。v1.3：`agent.enableAutoMutation` 現為 `ENGINE`（`apiKey` 有值時）、`agent.enableSelfEvolution` 現為 `STORED_ONLY`，`UNVERIFIED` 只剩 `sdd.specFormat`／`workflowEngine`／`validationLevel`；`ENGINE` 與 `CONSOLE` 的鍵不加小標籤 |
| S-14 | 敏感參數二次確認（US-S-02） | 第一次 `PUT` 不帶 `confirm` → 409 `敏感參數更新需二次確認（confirm=true）`；使用者確認後帶 `confirm=true` 重送 | 或前端先彈窗再直接帶 `confirm=true` |

### 4.5 全域元素（Phase 3～6 相關）

| # | UI 元素 | 資料來源 | 備註 |
|---|---------|----------|------|
| G-01 | 頂列通知鈴紅點數字 | `GET /notifications/summary` → `pendingReviews＋unacknowledgedAlerts`（前端加總） | 輪詢間隔＝`monitor.refreshIntervalMs`（預設與最小值皆 10 秒；限流鍵是 JWT subject，同一使用者所有頁面共用每分鐘 100 次，§0.4 第 4 點，AR-06） |
| G-02 | signoff 佇列徽章 | `summary.pendingSignoffs` | |
| G-03 | 頂列「Engine Bridge · 已連線」綠點 | `summary.bridgeConnected／bridgeCheckedAt`（最近一次健康探測結果；從未探測為 null） | 契約補此二欄是因為沒有其他全域來源；`/actuator/health` 只代表 console-api 自己。W3-B1 階段兩欄為 null（探測環由 B2 建，AR-08）→ 顯示「未知」灰點。**v1.4（D-17）**：探測預設打 `/health/deep`，Bridge 行程可達但引擎自檢未通過（503）時同樣是 `false`（灰點「未連線」）；摘要不區分兩種原因（§1.4.1），滑鼠提示可寫「（或引擎自檢未通過）」 |
| G-04 | 頂列使用者徽章 | 登入者名稱 ← access token 的 `sub`（Phase 1+2） | |
| G-05 | 搜尋列「搜尋專案、目標、任務…」 | Phase 2 `GET /projects?q=`（只搜專案名稱） | PRD §7 沒有跨目標／任務的搜尋端點（§4.6 G-G1） |
| G-06 | Dashboard「待審批草案數」 | `summary.pendingSignoffs`（跨專案、含目標與任務層級，§1.4.1） | 取代 Phase 2 前端只算專案與草案目標的近似值（ADR-002 已知限制）。**v1.4（D-18）**：同一張儀表板上「待人工審批」卡的清單與徽章改由 `GET /signoffs/pending` 提供（G-10），與本 KPI 同判準、同數字 |
| G-07 | Dashboard「執行中 run 數」「進行中的執行」卡 | Phase 2 `GET /projects?status=EXECUTING` 的 `totalElements`；每個執行中專案再 `GET /projects/{id}/executions?size=1` 取最新批次的 `tasksCompleted／tasksTotal` 畫進度條 | 沒有全域 run 端點；一個專案同時只會有一個 `EXECUTING` 批次。已暫停的批次其專案為 `READY`，不計入「執行中」 |
| G-08 | Dashboard「本週完成任務數」 | `GET /monitor/task-totals`（§1.3.8；v1.2，C-1）→ `completed` | `from`＝本週一 00:00（瀏覽器本機時區）轉 ISO-8601、`to` 省略；輪詢每 60 秒 1 次（分頁隱藏不輪詢）。取代 v1.1 對各專案扇出 `task-trend` 的近似做法（§4.6 G-G3） |
| G-09 | 專案列表「已刪除」篩選與「復原」按鈕（v1.2，C-3） | `GET /projects?deleted=true`（§1.6.2）→ `deletedAt`；`POST /projects/{id}/restore`（§1.6.1） | OPERATOR 以上才看得到篩選與按鈕（VIEWER 打 `deleted=true` 是 403）；復原成功 toast 並刷新列表；409 `project_not_deleted`／`restore_window_expired` 與 404 顯示對應原因 |
| G-10 | Dashboard「待人工審批」卡的清單與徽章（v1.4，D-18；完整性審查 I-05） | `GET /signoffs/pending?limit=50`（§1.8.1）→ `items[]`、`counts.total` | 徽章＝`counts.total`（與 KPI「待審批草案數」＝`summary.pendingSignoffs` 同判準、同數字）。每列：標題＝`title`；副標依 `kind` 由前端組字（專案草案／目標草案・{projectName}／任務草案・{projectName}／匯入草案）；連結：`PROJECT`→`/projects/{id}`、`GOAL`→`/projects/{projectId}/goals/{id}`、`TASK`→`/projects/{projectId}/goals/{parentId}/tasks/{id}`、`IMPORT`→`/import`（匯入頁目前沒有以 id 深連結某筆記錄的路由）；「審批」鈕依 `kind` 開 `SignoffDialog`（它已支援 project／goal／task／import 四種）。`counts.total > items.length` 時卡片底部顯示「僅列出最早的 N 筆，共 M 筆」。輪詢間隔同 `GET /notifications/summary`，任何 signoff 成功後立即重取。取代 `useSignoffQueue` 的「專案＋目標 API 組合」做法 |

### 4.6 設計稿元素在契約裡沒有資料來源（或需補設計）

| 編號 | 元素 | 狀態 | 建議處置 |
|------|------|------|----------|
| G-I1 | 匯入「URL」來源頁籤（README 文字） | 契約無 URL 匯入 | 不做；以截圖（上傳／貼上／歷史）為準 |
| G-I2 | 路徑「瀏覽按鈕」（PRD US-I-05） | 無（ADR-001 G-15） | 以路徑輸入＋Bridge allowlist 取代；RTM 判定 ⛔ 範圍外（Web 不瀏覽伺服器檔案系統，主控裁決，附錄 E） |
| G-I3 | 有界閘違規清單、解析警告列 | 設計稿沒畫，但資料齊備（§4.1 I-08、I-12） | 前端補元件（錯誤清單：閘別徽章＋位置＋原因） |
| G-E1 | 任務層級的執行範圍選取 | 契約支援，設計稿只有目標層級 | **已實作**（W4-F2 起：`ScopeTree.tsx`、`ExecuteView.tsx`；v1.4 回寫，完整性審查 V-11③；原寫「先做目標層級；任務層級列入 W4 增強」） |
| G-E2 | 「從斷點恢復」的斷點選擇對話框 | 資料齊備，設計稿沒畫 | 前端補對話框（列表＋確認） |
| G-E3 | 後續批次（follow-up run）切換 | 契約以 `X-Follow-Up-Run-Id` 與 `executions` 列表表達 | 前端處理標頭並重連 SSE |
| G-M1 | 監控頁「執行批次」下拉 | PRD §5.4.5 有、設計稿沒畫；資料齊備（`executions`＋`runId`） | 建議補（US-M-06 需要） |
| G-M2 | 事件時間軸、任務趨勢／成功失敗比率／重試分佈圖 | 資料齊備（`steps`、`task-trend`、`retryDistribution`），設計稿沒畫 | 依 PRD §5.4.2 補圖或列為後續 |
| G-M3 | 「資源使用情況」（CPU／記憶體） | **v1.3 已補（D-12）**：Bridge `RunStateOut.resources`（§3.1.2）→ `bridge.resources`（§1.2.3）→ §4.3 M-19（v1.2 為「Bridge 無此資料」，ADR-001 G-18） | 前端在 Agent 即時狀態卡顯示（格式見 M-19）；RTM 狀態由 QA 依 E2E-14 第 8～9 列當回合證據升級 |
| G-S1 | 參數 label 的中文名稱 | 契約只給 `description` | 前端字典（50 鍵；附錄 C 的鍵名即索引） |
| G-S2 | 非 ADMIN 角色的唯讀呈現（輸入框、儲存、顯示切換、測試連線） | 設計稿未畫角色差異；契約 403 | 前端依角色禁用控制項（角色取自登入回應 `role`） |
| G-G1 | 全域搜尋跨目標／任務 | PRD §7 沒有端點 | 超出 Phase 3～6；目前只搜專案 |
| G-G2 | 頂列「通知總覽」連結頁 | 無對應頁面與端點 | 暫以通知鈴的計數取代，不做列表頁。**v1.4（D-18）**：待簽核草案的跨專案清單已有端點與卡片（`GET /signoffs/pending`，§4.5 G-10）；待審核項目與未確認告警仍沒有跨專案清單端點，鈴的連結落點見 G-G4 |
| G-G3 | Dashboard「本週完成任務數」（跨專案） | **v1.2 已補**：全域端點 `GET /monitor/task-totals`（§1.3.8；C-1） | 前端改打該端點（每 60 秒 1 次），取代 v1.1 的近似做法（前 30 個專案各打一次 `task-trend` 再加總：單一分頁穩態每分鐘約 31 次請求，QA DEF-AC-009）；同一任務被還原重跑會重複計的語意不變（`completed` 是步驟事件列數） |
| G-G4 | 通知鈴「待審核項目」「未確認告警」兩個連結的落點（完整性審查 I-05） | 通知摘要只有三個計數，**沒有 projectId**（`NotificationSummaryResponse` 不變）；`GET /signoffs/pending` 只涵蓋待簽核草案，不含待審核項目與告警 | **已知限制（v1.4 維持 v1.3 的行為）**：有「目前專案」（路由上的 `projectId`）時導向該專案的執行頁／監控頁，沒有時導向專案列表（`/projects`）；所以人在 Dashboard 等非專案頁面時，點進去只是專案列表，不是有待辦的那個專案；目標專案不是目前專案時點進去也可能是空的。「待簽核草案」列不受影響（導向 Dashboard 的待人工審批卡，§4.5 G-10；清單項各自帶專案連結）。要精準導向，需要摘要增兩個欄位（最早一筆待審核項目與未確認告警各自的 `projectId`）或新增待審核／告警清單端點（主控裁決 Q5：先接受此限制，要精準導向再另案） |
| G-G5 | 公告列的靜態字樣（設計稿 README:57；完整性審查 D-04） | 設計稿只描述文字，沒說連到哪 | 「說明文件」「下載 CLI」「GitHub」「幫助中心」「繁體中文」五項是**靜態標示**（不可點、無行為；`TopRegion` 以 `<span>` 呈現）；「通知總覽」見 G-G2；「Engine Bridge」是功能性狀態點（§4.5 G-03）。日後要連到實際文件或做語言切換，另開需求 |
| G-E4 | DAG 卡「全螢幕」 | PRD wireframe 有、設計稿無，v1.3 以前沒做也沒登記（完整性審查 D-01） | v1.4 由前端補實作，見 §4.2 E-22 |

### 4.7 SDD 治理介面（v1.5；D-115-02、D-115-03、D-115-14；G-05、G-07、G-13；已與 ADR-016 對齊）

欄位來源一律是 §1.10 的 API。**缺值（null、缺席、空字串、無法解析）一律顯示單一的「—」**（同 M-19 與 `lib/domain/sdd.ts` 的 `sddText`），不顯示 `undefined`、`null` 或「目前沒有提供這項資料」之類字樣；**空陣列與缺席要分開**：空陣列表示「確定沒有」（顯示「無」），缺席才是「—」。

#### 4.7.1 專案詳情「SDD 治理」區（UI-SDD-01）

位置：專案詳情頁（`/projects/{projectId}`）的目標清單之下、「刪除」之上。**沒有「未綁定」狀態**（D-115-14：Console 專案是錨，FSM 專案預設＝專案名）：專案從未使用 SDD（`sddProject`、`sddSpecDir`、`sddSpecFile` 皆空）時預設**收合**，標題「SDD 治理（尚未使用）」；展開後內容與已使用者相同，只是 `fsm` 通常為 null。已使用時預設展開。

資料來源：`GET /projects/{id}`（綁定三欄）＋`GET /engines/sdd?projectId={id}`（FSM 狀態；輪詢 30 秒，分頁不可見時暫停，與 M-20 同節奏；收合時不輪詢）。

| 顯示項 | 來源欄位 | 規則 |
|--------|----------|------|
| SDD 專案 | `sddProject` | 等寬字；缺值顯示「（預設：<專案名>）」而非「—」，並附「編輯」鈕（OPERATOR 以上，見下） |
| 標準鍵 | `fsm.fsmProject` | 等寬字；缺值「—」；與 `fsm.project`（檔內原名）不同時，兩者並列（原名加註「檔內原名」） |
| 規格目錄、規格檔 | `sddSpecDir`、`sddSpecFile` | 等寬字，長路徑可換行；各自缺值「—」（尚未用路徑 A 匯入規格） |
| 目前狀態 | `fsm.currentState` | 等寬字；`fsm` 為 null 時依 `reason` 顯示 M-20 的文案（`fsm_not_found`「找不到所選專案的 FSM 狀態檔」並加註「請在專案根的 SDD session 建立：<executionPath>/build/reports/fsm」等），本表其餘欄位全部「—」 |
| 階段 | `fsm.phase` | 標籤與旗標規則見 §4.7.3；`phase` 缺席或 null：階段欄「—」，仍顯示 `currentState` |
| 凍結狀態 | `fsm.frozenStages` | 空陣列＝「尚未凍結」；≥ 1 筆＝「已凍結：<最後一筆的 `stage`>（<`frozen_at` 轉本機時區>）」，單筆內缺值各自「—」；不解讀 `spec_doc_digests` |
| 待人工 | `fsm.humanPending.count` | 同 M-20：0「無」、1「等待人工確認」 |
| 最近一次升級 | `fsm.escalationHistory` 末筆 | 只有 `currentState` 為 `ESCALATION`／`ESCALATION_FINAL`（或 `phase.blocking=true`）時顯示（完整區塊見 §4.7.3）：`triggered_at`（本機時區）與 `trigger_reason`；缺值「—」 |

「編輯 SDD 專案」（OPERATOR 以上；VIEWER 不顯示）：對話框一個輸入欄（自由輸入，1～100 字元、無控制字元；留空並儲存＝清除，回到「用預設」）；說明文字「值會交給引擎橋接淨化後生效；改綁不搬移 FSM 狀態檔，也不影響進行中的批次」；送出 `PUT /projects/{id}/sdd-binding`（§1.10.7）；成功 → toast「已更新 SDD 專案」並重取專案詳情與 `engines/sdd`；失敗：400 在欄位下顯示 `errors[0].message`，`sdd_binding_conflict`「同一個專案根下已有另一個專案（<`details.holderProjectId` 前 8 碼>）綁定了這個 FSM 專案」，其餘照一般錯誤顯示 `message` 與 `traceId`。

「核准凍結」鈕（人工閘）：

- **顯示條件**：登入者角色為 OPERATOR 以上（VIEWER 不顯示，與其他寫入鈕同）。
- **啟用條件**：`fsm.currentState == "HUMAN_PENDING"`。其他狀態停用，tooltip「FSM 目前不在 HUMAN_PENDING（目前：<currentState，缺值「—」>）」；`fsm` 為 null 時一律停用。
- **對話框**（沿用 `ConfirmDialog`）：說明文字「核准後 FSM 進入 SPEC_FROZEN，規格內容將被摘要綁定；此動作無法由 Console 退回」；**「要凍結的規格文件」**多行輸入（每行一個相對專案根的路徑，1～20 行；已有 `sddSpecFile` 時預填其相對路徑；前端只做格式檢查：相對路徑、不含 `..`、不重複；是否含 TCS 與檔案是否存在由 Bridge 判定，錯誤原樣顯示）；**理由欄必填**（去前後空白後 1～500 字元，不得含換行，不合不得送出，即時顯示字數）；顯示「核准人：<目前登入者>」（唯讀；approver 取自 JWT，不由畫面指定）。
- **送出**：`POST /projects/{id}/sdd/freeze`（§1.10.2；body 為 `reason` 與 `docs`，不送 `stage`、`expectedDigests`）；成功 → toast「已核准凍結」並重取專案詳情與 `engines/sdd`；失敗依 `reason` 顯示：`sdd_fsm_state_conflict`「FSM 目前不在 HUMAN_PENDING（目前：<details.currentState>）」、`sdd_fsm_not_found`「找不到 FSM 專案狀態檔（<details.sddProject>）；請先在專案根的 SDD session 建立」、`sdd_binding_conflict`「同一個專案根下已有另一個專案綁定了這個 FSM 專案」、`sdd_spec_digest_changed`「規格檔在凍結前已被改動，請重新確認內容」、`sdd_write_disabled`「SDD 寫入功能未啟用（需管理員設定寫入權杖）」，422 `引擎拒絕此請求`顯示 `details.violations[]` 的 `field` 與 `rule`（例如 `docs`／`missing_tcs`「規格文件須含至少一份 TCS」），其餘照一般錯誤顯示 `message` 與 `traceId`。
- **靜態提示**（區塊底部）：「FSM 狀態檔位於專案根的 build/reports/fsm，請把 build/reports/ 加入該專案的 .gitignore。」（匯入時 Bridge 偵測到未忽略會另有黃色警告 `state_dir_not_ignored`。）

#### 4.7.2 執行詳情「追溯覆蓋（諮詢）」面板（UI-SDD-02）

位置：執行頁（`/projects/[projectId]/execute`）的批次詳情區；專案**沒有 SDD 規格綁定**（`sddSpecDir` 為空）時整個面板不顯示；批次**非終態**時只顯示一行說明「批次結束後才會有追溯覆蓋報告」，不呼叫端點。

資料來源：`GET /executions/{runId}/rtm`（§1.10.3）；批次進入終態（`COMPLETED`／`FAILED`／`CANCELLED`）後取**一次**，不輪詢。

標示：標題「追溯覆蓋」＋徽章「諮詢視圖」（`advisory=true` 時必顯示）；面板內固定一行說明：「AT 通過只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘。」

| 顯示項 | 來源欄位 | 規則 |
|--------|----------|------|
| AT 通過 | `at.passed`／`at.total`／`at.pct` | 「4／4（100.0%）」；`at.unmapped` > 0 時加註「其中 <n> 個無法歸屬到 AC」；`at` 缺席「—」 |
| AC 覆蓋 | `ac.covered`／`ac.total`／`ac.pct` | 「2／2（100.0%）」；缺席「—」 |
| SCG-5 覆蓋 | `fullyCovered`＋`unmappedAtIds` | `true`「AC 已達 100% 覆蓋」；`false` 且 `unmappedAtIds` 非空而 AC 已全覆蓋「AC 已達 100%，但有無法歸屬的 AT，不視為全覆蓋」；其餘 `false`「AC 未達 100% 覆蓋」；缺席「—」 |
| 規格摘要 | `specDigest` | 前 19 碼（`sha256:` 加 12 碼十六進位）加「…」，tooltip 顯示全值；空字串「—」 |
| 場景 | `scenario` | 空字串「—」 |
| 未通過的 AT | `failedAtIds` | 逗號分隔；空陣列「無」；缺席「—」 |
| 驗收 regex 偏弱的 AT | `weakRegexAtIds` | 同上；非空時加註「規格的 Then 沒有可推導的引號字面值，驗收可能偏鬆」 |
| 無法歸屬 AC 的 AT | `unmappedAtIds` | 同上；非空時加註「這些 AT 的編號不符 AT-NNN-Y-… 文法或 AC 對不上，已計入 AT 總數但不計入任何 AC」 |

狀態：404 `rtm_not_found` → 顯示中性文字「此批次沒有追溯覆蓋報告」（不是錯誤樣式；常見原因：批次沒有啟用 SDD 治理、批次不是正常走完）；422、502、504 → 一般錯誤區塊（`message` 與 `traceId`）加「重試」鈕。

#### 4.7.3 SDD 卡的階段進度與 ESCALATION 標示（UI-SDD-03；M-21）

階段字典（`lib/domain/sdd.ts`）：`phase.name` → 中文標籤——`INTAKE`「立案」、`SPECIFICATION`「規格撰寫」、`HUMAN_GATE`「人工確認」、`FROZEN`「規格凍結」、`IMPLEMENTATION`「實作」、`REVIEW`「審查」、`VERIFICATION`「追溯驗證」、`RELEASE`「發布」；非主路徑：`BLOCKED`「阻塞（需人工）」、`TRANSIENT`「過渡中」、`OBSERVATION`「觀測中」、`UNKNOWN`「未知」。字典沒有的新值（日後 Bridge 加階段）→ 顯示原字串，不崩潰。

進度條（放在「目前狀態」欄下方）：八個步驟（`order` 1～8，標籤取自字典）依序排列——

- `phase.order` 為 1～8：該步驟標為「目前」，之前的標為「已過」，之後的標為「未到」。
- `observation=true`：額外顯示小標籤「觀測中」，「目前」步驟改用虛線外框（表示回歸階段）；`currentState` 為 `AUTOCLAUDE_DELEGATED` 時另顯示標籤「委派 AutoClaude 執行中」。
- `blocking=true`：所有步驟都標為「未到」的灰階，進度條上方顯示紅色橫幅「阻塞：<currentState>（需人工恢復）」，橫幅內說明「請在 SDD session 依恢復指令處理，Console 不提供恢復動作」，並顯示下方的 ESCALATION 區塊。
- `order` 為 0（`OBSERVATION`／`TRANSIENT`／`UNKNOWN`，或 `phase` 缺席）：不標任何步驟，只顯示 `currentState` 與對應標籤（`phase` 缺席則標籤欄「—」）。

ESCALATION 區塊：`phase.blocking=true`，或 `currentState` 為 `ESCALATION`／`ESCALATION_FINAL` 時，顯示 `escalationHistory` 末筆——「ESCALATION・<`triggered_at` 本機時區>・<`trigger_reason`>」，有 `resolved_at` 時加「已解決：<`resolved_at`>／<`resolution`>」；`escalationHistory` 為空而狀態卻是阻塞態 → 區塊內寫「（沒有升級紀錄）」，橫幅照顯示。各欄位缺值「—」。🔴 **「有沒有未解的升級」的判斷式只能是「`currentState` 屬 `ESCALATION`／`ESCALATION_FINAL`，且 `escalationHistory` 末筆的 `resolved_at` 為空」**，不得只看 `escalationProvenance` 在不在（恢復後它不會被清除，在 `IMPLEMENTATION` 上會顯示過期的失敗；ADR-016 §5.3）。

- **來源行**：`escalationProvenance` 有值時加一行「來源：<`source`>」，`source=autoclaude_delegated_failed` 時註明「AutoClaude 委派失敗（引擎升級）」；缺值不顯示這一行（不寫「—」）。
- **恢復指令**：`fsm.recovery` 有值時顯示「恢復（在 SDD session 執行；Console 不提供恢復動作）」，PowerShell 與 POSIX 兩個分頁各一段等寬字指令與「複製」鈕；指令內的 `<人工原因>` 由使用者自行替換，Console 不替換、不提供執行鈕；`fsm.recovery` 缺席時只顯示橫幅的文字說明，不得由前端自行組指令（目標與路徑由 Bridge 決定，ADR-016 §5.3）。

建議的測試屬性（e2e 用）：進度條 `data-testid="sdd-phase"`，並帶 `data-phase`（`phase.name`）、`data-order`（`phase.order`）、`data-blocking`、`data-observation`（布林字串）；ESCALATION 區塊 `data-testid="sdd-escalation"`；恢復指令 `data-testid="sdd-recovery"`（內含 `data-shell="powershell"｜"posix"` 的兩段）；追溯面板 `data-testid="rtm-panel"`。

---
## 5. E2E 情境（QA 與兩位開發者共用；全部以 `aisdlc-mock-claude` 為 Claude 替身，結果可決定）

### 5.0 共用夾具與斷言慣例

#### 5.0.1 環境

| 元件 | 設定 |
|------|------|
| PostgreSQL | `pgvector/pgvector:pg18`（Testcontainers 或 compose）；Flyway 套用 V1～V11（v1.4：V8～V11 是 v1.2～v1.4 增補，§0.5） |
| Engine Bridge（真行程） | `uvicorn app.main:app --port 18081`（Windows 用 `<REPO_ROOT>\.venv\Scripts\uvicorn.exe`）；環境變數：`BRIDGE_DB_DSN`（同一個 DB）、`BRIDGE_DB_SCHEMA=console`、`ENGINE_WORKSPACE=<E2E_ROOT>/workspace`、`BRIDGE_ALLOWED_PATH_ROOTS=<E2E_ROOT>`（多個以 `os.pathsep` 分隔）、`BRIDGE_OUTBOUND_ALLOWLIST=127.0.0.1,localhost`、`BRIDGE_STOP_GRACE_SECONDS=5`、`BRIDGE_INSTANCE=e2e-bridge`；**單一 worker**。**啟動前的行程環境（AR-12）**見下方「Bridge 啟動環境」 |
| 假 OpenAI 相容伺服器（WireMock） | `<WM_PORT>`：`POST /v1/chat/completions`（匯入路徑 B 與 test-connection 的探測都打這一條；可由任何能依路徑與請求本文標記回應的假伺服器取代，例如 Python `http.server`）。綁在 `127.0.0.1`（loopback） |
| console-api（profile `e2e`） | `ENGINE_BRIDGE_URL=http://127.0.0.1:18081`；`console.security.outbound-allowlist=127.0.0.1,localhost,rebind.e2e.test`；`console.security.allow-loopback=true`；`console.security.test-dns-overrides={rebind.e2e.test: 10.0.0.5}`；`console.security.rate-limit.enabled=true`；`console.security.rate-limit.trust-forwarded-for=true`＋`server.forward-headers-strategy=native`；`console.sse.keep-alive-seconds=2`；`console.execution.mock-env={MOCK_CLAUDE_DELAY: "0.6", MOCK_CLAUDE_FAIL_REGEX: "\\[FAIL_ME\\]", MOCK_CLAUDE_TRACE: "<E2E_ROOT>/mock-trace.jsonl"}`；`CONSOLE_ENCRYPTION_KEY`、`JWT_SECRET` 為測試值 |
| 帳號 | `admin`／`operator`／`viewer`（backend README 的三組內建帳號）；限流鍵是 JWT subject（§0.4 第 4 點） |

`<E2E_ROOT>` 是測試建立的暫存根目錄、`<REPO_ROOT>` 是 monorepo 根目錄（都不寫死磁碟路徑）；每個專案的 `executionPath` 是 `<E2E_ROOT>` 之下已存在的空目錄。

**Bridge 啟動環境（AR-12；Bridge 自己的 `tests/conftest.py` 做的就是這三件事）**：

1. **PATH**：把 `<REPO_ROOT>\.venv\Scripts`（POSIX：`<REPO_ROOT>/.venv/bin`）前置到 Bridge 行程的 `PATH`。引擎以 `shutil.which(claude.command)` 解析替身；用 `.venv\Scripts\uvicorn.exe` 絕對路徑啟動 Bridge 並不會啟用 venv，`PATH` 通常不含該目錄，沒有這一步每個步驟都會在第一秒失敗。`autoclaude.claudeCommand` 另外用絕對路徑（§5.0.2），兩者並用。
2. **額度快取隔離**：設 `AUTOSDD_QUOTA_CACHE_DIR=<E2E_ROOT>/quota-cache`（一個**空目錄**）。引擎會讀帳號額度快取（`TokenGuardConfig.quota_halt_pct` 預設 95）；不隔離的話，在每天用 Claude Code 的開發機上，真實用量可能讓 E2E 的引擎 halt。
3. **清環境**：清掉 Bridge 行程環境裡所有 `AUTOSDD_*`（第 2 點那個除外）、`AUTOCLAUDE_*`、`MINIMAX_*`、`MOCK_CLAUDE_*`。Bridge 把自己的環境傳給引擎子行程，殘留的 `MINIMAX_API_KEY` 會讓引擎建 Brain，ESCALATION 時外呼模型（§3.4.2）；`MOCK_CLAUDE_*` 只應由 Console 的請求 `env` 提供。

**e2e 專用屬性與假伺服器的放行（SSRF）**：假伺服器綁在 `127.0.0.1`（loopback），所以放行機制只有一個：allowlist 含 `127.0.0.1` **且** `console.security.allow-loopback=true`（§1.5.7 規則 4）。**沒有「允許私網」的旗標**：`rebind.e2e.test` 在 allowlist 內，但被 `test-dns-overrides` 解析到私網位址 `10.0.0.5`，正好用來驗 `dns_rebinding`（E2E-10），兩者互不衝突。`allow-loopback`、`test-dns-overrides`、`console.execution.mock-env`、`console.sse.keep-alive-seconds`（2 秒）這幾個屬性**只在 e2e／test profile 載入**（主控裁決 §6.3 第 11 項），production 與 docker profile 不得出現。

**健康探測路徑與假 Bridge（v1.4，D-17）**：console-api 的探測環預設打 `GET /health/deep`（§3.1）。因此任何以 `autoclaude.engineUrl`／`ENGINE_BRIDGE_URL` 指向的**替身 Bridge**——後端整合測試的 `MiniBridgeController`、前端 mock 伺服器、e2e 腳本自己起的假伺服器——**必須提供 `GET /health/deep`**（200 `{"status":"ok","checks":{…}}`；要驗失敗路徑時回 503 `{"status":"degraded","reason":"…","checks":{…}}`）。缺這個路徑的替身會回 404，探測環一律判失敗：`bridgeConnected` 恆 `false`、`agentAvailability` 恆 0、`AGENT_UNRESPONSIVE` 可能誤報。若某個替身只實作 `/health`，須在 e2e 前置把 `autoclaude.healthCheckPath` 設為 `/health`（附錄 C.5 的驗證規則允許），並在該情境註明。真 Bridge 在 e2e 環境的 `/health/deep` 應為 200：`git` 在 PATH 上、工作區可寫、有 DSN 時 DB 可 ping、`sdd` 只當資訊、任何值都不影響 200（§3.1.1）。

**Docker 全棧版本**（W4-QA 驗證矩陣 D）不載入 e2e profile：容器內的 console-api 沒有 `allow-loopback`，假伺服器放在主機或另一個容器都會因私網位址被 SSRF 規則拒絕；compose 預設設定下路徑 B／C 也沒有模型金鑰與 Brain 可用。該矩陣的匯入步驟請改走路徑 A（把凍結規格放進容器內的專案目錄）或直接用 Phase 2 REST 建專案；路徑 B 留給本機 E2E 驗證。

#### 5.0.2 系統參數前置（admin 以 `PUT /settings/{category}/{key}` 設定；情境前執行一次）

| 鍵 | 值 | 目的 |
|----|----|------|
| `autoclaude.claudeCommand` | `<REPO_ROOT>\.venv\Scripts\aisdlc-mock-claude.exe`（POSIX：`<REPO_ROOT>/.venv/bin/aisdlc-mock-claude`）——**絕對路徑**，路徑不得含空白 | 引擎用替身（非真 Claude）；不依賴 Bridge 行程的 `PATH`（AR-12）。V5 的 `validation_rule` 允許反斜線、冒號、點與 `.exe`（附錄 C） |
| `execution.autoResume` | `false` | 避免 Token halt 時引擎自己長時間等待 |
| `agent.maxRetries` | `1` | 失敗步驟只重試一次（STARTED→RETRYING→FAILED） |
| `model.apiUrl` | `http://127.0.0.1:<WM_PORT>/v1/chat/completions`——**完整端點**（AR-09） | 假模型；只有 E2E-01、E2E-09、E2E-10 用到（`127.0.0.1` 在 e2e allowlist，且 `allow-loopback=true` 放行） |
| `model.apiKey` | **預設為空**。E2E-01 開始時設 `sk-e2e-dummy`（`confirm=true`），**E2E-01 結束時 `POST /settings/model/apiKey/reset?confirm=true` 清空**；E2E-02～E2E-08 開始前必須是空（`hasValue=false`） | 這就是「E2E 關閉演化」（AR-12、TBC-2）：引擎沒有演化開關鍵，AI 演化提案只由 `MINIMAX_API_KEY` 的有無決定（§3.4.2）。apiKey 有值時 Console 會送 `minimax.*` 與 `MINIMAX_API_KEY`，ESCALATION 時引擎對 `minimax.base_url` 發演化提案，`_call_with_retry` 的退避最壞約 96 秒，會拖垮 E2E-05 的 60 秒輪詢預算。v1.3 的 E2E-14 例外：它**專門驗**有金鑰的行為，會暫時設一個假金鑰（**不得以 `sk-` 開頭**，commit 的機密掃描會擋；`MinimaxClient` 建構時不檢查金鑰格式）並在結束時同樣 `reset` 清空 |
| `model.name`／`model.timeout` | `e2e-model`／`30` | |

#### 5.0.3 固定夾具與替身常數

- **夾具專案**（每個情境各建一份獨立的，名稱含情境編號，路徑各自一個子目錄）以 Phase 2 REST 手動建立（手動建立即 `signedOff=true`；E2E-02 例外用 `draft:true`）：
  - **PRJ-A**（3 任務）：`G1「基礎」`（sortOrder 0）含 `T1「初始化」`、`T2「設定」`；`G2「核心」`（sortOrder 1，`dependsOn=[G1]`）含 `T3「實作」`。每個任務 `description`＝`請輸出 [T<n>_DONE]`、`passCriteria`＝`輸出含 [T<n>_DONE]`、`expectedOutputRegex`＝`\[T<n>_DONE\]`、`maxRetries=1`。專案 `autonomyLevel=4`。
  - **PRJ-B**（5 任務）：`G1` 含 `T1、T2、T3`；`G2`（依賴 G1）含 `T4、T5`；其餘同 PRJ-A。
  - **任務數須 ≤ 5**：引擎預設 `auto_compact_interval=5`，超過會多一次 `/compact` 呼叫而改變 Token 帳。
- **mock claude 的行為（已對 `app/mock_claude.py` 核對）**：每次呼叫回放 prompt 內所有 `[KEYWORD]`；用量固定 `input=1200`、`output=40`（**每個 attempt 1,240 Token**；context% ＝ 0.6）；延遲 0.6 秒；prompt 命中 `\[FAIL_ME\]` 時不輸出任何關鍵字（evaluator 判失敗）。因此**任務 `description` 含 `[FAIL_ME]` 就會失敗**，不含就成功。
- **Token 帳**：一個成功的步驟 ＝ 1 個 attempt ＝ 1,240；失敗步驟（`maxRetries=1`）＝ 2 個 attempt ＝ 2,480。被 pause 中止、從未回傳的 spawn 不產生 token 事件。
- **step_id**：依 §3.4.4，PRJ-A 全範圍為 `G1-T1`、`G1-T2`、`G2-T1`（T1、T2、T3）。

#### 5.0.4 斷言慣例與共通後置斷言

- 等待狀態轉換一律輪詢（逾時 60 秒），不用固定 sleep；SSE 斷言比對**事件子序列與欄位**，不比對引擎原始 `log` 行數；Token、步驟數、狀態、reason 字串一律精確比對。
- **SSE 一律以解析後的欄位斷言**（事件名、id、data JSON），不比對框架位元組：冒號後空白不保證（`SseEmitter` 輸出 `id:41` 而非 `id: 41`，§2.1，AR-03）；keep-alive 以「解析器收到註解行、內容為 `keep-alive`」斷言。
- **限流與使用者**：限流鍵是 JWT subject（§0.4 第 4 點），每個使用者每分鐘 100 次。E2E 測試的狀態輪詢間隔不得小於 2 秒（每分鐘至多約 30 次，留一半額度給其他請求；這與產品畫面的輪詢地板 10 秒是兩回事）；**輪詢用 `viewer` 帳號（只讀），寫入動作用 `operator`／`admin`**；不同情境用不同使用者，或情境之間等 60 秒讓桶回滿；E2E-11 最後執行。沒有 JWT 的請求（登入、無效 token）才以 IP 為鍵，e2e profile 以 `trust-forwarded-for=true` 讓測試可用 `X-Forwarded-For` 區分。
- **每個涉及 run 的情境結束時都驗**：(A1) DB `execution_runs.status` ＝ Bridge `GET /autoclaude/runs/{id}` 的狀態折疊值，`total_tokens_used` 相等（NFR-OBS-01）；(A2) 每個非 2xx 回應都是 `ApiError` 封包且 `traceId` 等於 `X-Trace-Id`；(A3) 整段測試的 console-api 日誌沒有「未預期的例外」（500），也沒有串流正常結束時的 `AccessDeniedException`（§2.1，TBC-1）；(A4) 任一 SSE 連線的 id 依 `(seq,n)` 嚴格遞增、無重複；(A5) 任何回應與日誌都不含 API 金鑰明文（除 `reveal=true` 回應）。
- **`details` 的斷言一律寫「缺席或 null」**（§0.2，AR-17）：後端不輸出 null 值，所以 `details.unsignedProjectId` 之類的欄位在「沒有值」時是缺席。
- 下列 HTTP 簡寫：`POST execute` ＝ `POST /api/v1/projects/{projectId}/execute`；`GET run` ＝ `GET /api/v1/executions/{runId}`。

---

### E2E-01　匯入貼文字（路徑 B）→ 編輯 → signoff → confirm → 專案全部 signedOff　〔API-IMP-01～10、SGN-01／US-I-01～05、07～10／NFR-SEC-04〕

**前置**：operator；§5.0.2 的模型參數已設（本情境開始時由 admin 設 `model.apiUrl`＝`http://127.0.0.1:<WM_PORT>/v1/chat/completions`、`model.apiKey`＝`sk-e2e-dummy`〔`confirm=true`〕；**本情境結束時必須清掉 apiKey**，見「結束動作」）；假伺服器 stub **S-OK**（請求本文含 `需求文件內容`、無其他標記時）回 200：

```json
{ "id":"chatcmpl-e2e", "object":"chat.completion", "model":"e2e-model",
  "choices":[{ "index":0, "finish_reason":"stop", "message":{ "role":"assistant", "content":
    "{\"project\":{\"name\":\"E2E 匯入專案\",\"executionPath\":\"/ignored\",\"passCriteria\":\"三個目標全部完成\",\"description\":\"由 BRD 匯入\"},\"goals\":[{\"key\":\"g1\",\"name\":\"基礎\",\"description\":\"\",\"passCriteria\":\"基礎任務完成\",\"sortOrder\":0,\"dependsOn\":[],\"tasks\":[{\"name\":\"初始化\",\"description\":\"請輸出 [T1_DONE]\",\"passCriteria\":\"輸出含 [T1_DONE]\",\"sortOrder\":0},{\"name\":\"設定\",\"description\":\"請輸出 [T2_DONE]\",\"passCriteria\":\"輸出含 [T2_DONE]\",\"sortOrder\":1}]},{\"key\":\"g2\",\"name\":\"核心\",\"description\":\"\",\"passCriteria\":\"核心任務完成\",\"sortOrder\":1,\"dependsOn\":[\"g1\"],\"tasks\":[{\"name\":\"實作\",\"description\":\"請輸出 [T3_DONE]\",\"passCriteria\":\"輸出含 [T3_DONE]\",\"sortOrder\":0}]}]}" } }],
  "usage":{ "prompt_tokens":812, "completion_tokens":340, "total_tokens":1152 } }
```

**主流程**（文件內容：以 `# BRD` 與兩個 `##` 標題開頭、≥ 200 字元的 Markdown，確保走路徑 B 而非 C）：

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST /import/text` `{content, sourceFileName:"e2e-brd.md", sourceType:"MARKDOWN"}` | **201**；`status=UPLOADED`、`signedOff=false`、`sourceType=MARKDOWN` |
| 2 | `POST /import/{id}/parse` `{autonomyLevel:3, executionPath:"<E2E_ROOT>/proj-import", additionalPrompt:"盡量少於 5 個任務"}` | **200**；`status=PARSED`、`path=LLM`、`aiModel=e2e-model`、`tokenUsed=1152`、`signedOff=false`、`errors=[]`、`warnings=[]`；`parsedResult.goals` 2 個（g1 任務 2、g2 任務 1）、`goals[1].dependsOn=["g1"]`；`project.executionPath` ＝請求值（LLM 的 `/ignored` 被丟棄）。**WireMock 驗證**：收到 1 次 `POST /v1/chat/completions`（路徑就是 `model.apiUrl` 的路徑，後端沒有補任何路徑，AR-09），標頭 `Authorization: Bearer sk-e2e-dummy`；本文 `model=e2e-model`、`stream=false`、`response_format.type=json_object`；`messages[0].role=system`；`messages[1].content` 含 `自治等級: 3`、`補充說明: 盡量少於 5 個任務` 與文件原文 |
| 3 | `GET /import/{id}` | **200**；含 `sourceContent`、與步驟 2 相同的 `parsedResult`、`parsePath=LLM`，`lastParseErrors` 缺席或 null；**`warnings=[]`、`parseOptions` 等於步驟 2 的請求**（`autonomyLevel=3`、`executionPath`、`additionalPrompt`；v1.2，C-10） |
| 4 | `PUT /import/{id}/result`：把 g1 改名「基礎建設」、在 g2 新增任務 T4（`請輸出 [T4_DONE]`） | **200**；`status=REVIEWING`、`signedOff=false`；goals／tasks 順序與 `sortOrder`（0 起連續）依陣列重編 |
| 5 | `POST /import/{id}/confirm`（尚未 signoff） | **409**；`reason=草案尚未 signoff，不可確認匯入`；`GET /projects?q=E2E 匯入專案` 的 `totalElements=0` |
| 6 | `POST /import/{id}/signoff` `{approver:"  "}` | **400**；`errors[0].field=approver` |
| 7 | `POST /import/{id}/signoff` `{approver:"e2e-approver"}` | **200**；`signedOff=true`、`signedOffBy=e2e-approver`、`signedOffAt` 非 null |
| 8 | 再次 `signoff` | **409**；`reason=已 signoff`；`details.signedOffBy=e2e-approver` |
| 9 | `PUT result`（同一棵樹、改一個任務描述） | **200**；`signedOff=false`（**編輯撤銷 signoff**）；`GET /import/{id}` 的 `signedOffBy=null` |
| 10 | 重新 `signoff` `{approver:"e2e-approver"}` | **200** |
| 11 | `POST /import/{id}/confirm` | **201**：`signedOff=true`、`signedOffBy=e2e-approver`、`status=DRAFT`、`goalsCount=2`、`tasksCount=4`、`autonomyLevel=3`、`executionPath=<E2E_ROOT>/proj-import`、`name=E2E 匯入專案`、`createdBy=operator` |
| 12 | Phase 2 讀取：`GET /projects/{pid}/goals`、`GET /goals/{g2}`、`GET /goals/{g}/tasks` | 兩個目標皆 `signedOff=true`；`signedOffBy=e2e-approver` 只在**詳情端點**（`GET /goals/{id}`、`GET /tasks/{id}`、`GET /projects/{pid}`）斷言——**清單端點只帶 `signedOff`**，不帶 `signedOffBy`／`signedOffAt`（QA O-03：v1.1 的措辭過寬；`GoalSummaryResponse`／`TaskSummaryResponse`）；g2 的 `dependsOn=[g1 的 id]`；四個任務皆 `signedOff=true`；DB：專案／目標／任務的 `signed_off_at` 與匯入記錄的 `signed_off_at` 相同 |
| 13 | `GET /import/{id}` | `status=IMPORTED`、`projectId=pid`；再次 `confirm` → **409** `已匯入`（`details.projectId`）；`reject` → **409** `匯入記錄狀態不允許此操作`（`details.action=reject`） |
| 14 | `GET /import?status=IMPORTED&sort=createdAt,desc` | 含此筆，`projectId` 已回填 |
| 15 | 角色：viewer `POST /import/text` → **403**（`ACCESS_DENIED`）；viewer `GET /import` → **200**；operator `PUT /settings/…` 不在此情境 | |

**有界閘變體**（各用一筆新記錄與下列文件標記，WireMock 依請求本文含的標記回不同 stub；每筆 parse 都預期 **422**、`reason=解析結果未通過有界閘`、記錄 `status=UPLOADED`、`GET /import/{id}` 的 `lastParseErrors` 非空；之後改用正常文件重新 parse → 200 且 `lastParseErrors` 清空）：

| 文件標記 | stub 回應的樹 | `errors` 預期（`gate`＋`location`） |
|----------|---------------|-------------------------------------|
| `GATE_MAX` | 一個目標含 25 個任務 | `max_steps`＋`goals[0].tasks`；`detail` 含 `25` 與 `24` |
| `GATE_CYCLE` | g1 依賴 g2、g2 依賴 g1 | `cycle`＋`goals[0].dependsOn`；`detail` 含 `->` |
| `GATE_EMPTY` | 第二個任務 `description` 為 `"  "` | `empty_prompt`＋`goals[0].tasks[1].description` |
| `GATE_EMPTY_NAME` | 第一個任務 `name` 為 `"  "` | `empty_prompt`＋`goals[0].tasks[0].name`（任務 `name` 空白與 `description` 空白同為這一閘，§3.3.5，AR-21） |
| `GATE_LONG` | 一個任務 `description` 長 20,500 字元 | `prompt_too_long`＋`goals[0].tasks[0]` |
| `GATE_MULTI` | 25 個任務且其中一個描述為空 | **兩項**，順序 `empty_prompt`、`max_steps`（§3.3.5 的固定順序） |
| `GATE_BADJSON` | `content` 為 `not json` | `brain_failed`（無 `location`） |
| `GATE_HTTP500` | stub 回 HTTP 500 | `brain_failed`；`detail` 含 `500`，不含金鑰 |
| （先清空 `model.apiKey`） | — | `brain_unsupported`；`detail` 含 `model.apiKey` |

**消毒變體（NFR-SEC-03）**：對 REVIEWING 狀態的記錄 `PUT result`，把某任務 `evaluatorCommand` 設為 `pytest -q; echo done`（含 `;`）→ **400**，`reason=命令含禁用字元`，`details.violations` 列出 `;`；`expectedOutputRegex` 設為 `([` → **400**（無法編譯）；改為合法值 `pytest -q` 與 `\[T1_DONE\]` → **200**。

**空白與缺漏的區別（AR-21）**：`PUT result` 中某任務的 `name` 為空白字串 `"  "` → **422**（閘 `empty_prompt`，`location=goals[0].tasks[0].name`）；`name` 為 `null` 或整個缺欄位 → **400**（Bean Validation，`errors[0].field` 指到該欄位）。

**結束動作（必做）**：admin `POST /settings/model/apiKey/reset?confirm=true`，並確認 `GET /settings/model` 的 `apiKey.hasValue=false`——後續的執行類情境（E2E-02～E2E-08）要求 `model.apiKey` 為空（§5.0.2，「關閉演化」）。

**上傳變體**：小的 `.md` 檔 → **201**（`sourceType=MARKDOWN`）；`.txt` → **415**（`只支援 .md／.pdf／.docx 檔案`）；11MB 檔 → **413**（`檔案超過 10MB 上限`）；內容為 `hello` 但副檔名 `.pdf` → **422**（`檔案內容與副檔名不符`）；空檔 → **400**（`檔案是空的`）；viewer 上傳 → **403**。

**不在本 E2E 的範圍**：路徑 A（SDD）與 C（decompose）以「WireMock 假 Bridge」的後端整合測試覆蓋——Bridge 的 decompose 需要 `MINIMAX_API_KEY` 與真 Brain，而 `mock_brain_server.py` 不支援拆解（ADR-001 D9）。路徑 A 的整合測試要含「30 個合約」案例：預期切成兩個目標（24＋6），名稱 `<scenario>（第 1 批）`、`<scenario>（第 2 批）`，`g2.dependsOn=["g1"]`，不得因合約數多而 422（§3.3.2，AR-19）。

---

### E2E-02　execute 未 signoff → 409　〔API-EXE-11／US-E-01〕

**前置**：operator；以 `draft:true` 建立 PRJ-U（3 任務，專案、目標、任務皆 `signedOff=false`）。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute` `{}` | **409**；`reason=未經人工審批的草案不可執行`；`message=草案未經人工審批，禁止執行`；`details.unsignedProjectId`＝專案 id，`unsignedGoalIds`＝兩個目標 id，`unsignedTaskIds`＝三個任務 id |
| 2 | 檢查沒有副作用 | `GET /projects/{id}/executions` 的 `totalElements=0`；專案 `status=DRAFT`；DB `execution_runs` 無此專案的列；Bridge workspace 沒有新的 run 目錄 |
| 3 | 只 signoff 專案後 `POST execute` | **409**；`details.unsignedProjectId` **缺席或 null**（專案已簽；`details` 不輸出 null，§0.2）；目標、任務清單仍在 |
| 4 | 再 signoff 兩個目標與其中兩個任務後 `POST execute` | **409**；`unsignedGoalIds=[]`、`unsignedTaskIds` 只含第三個任務 |
| 5 | `POST execute` `{scope:{mode:"SELECTED", goalIds:[<他專案的目標 id>]}}`（仍有未 signoff） | **409**（檢查順序：未 signoff 先於範圍檢查）；全部 signoff 後同一請求 → **400** `所選範圍不合法`（`details.invalidGoalIds`） |
| 6 | signoff 第三個任務後 `POST execute` `{autonomyLevel:4}` | **201**；專案 `status=EXECUTING`（`DRAFT` 經內部 `READY`）；隨即 `POST cancel` → **200** 收尾 |
| 7 | 在 EXECUTING 期間再 `POST execute` | **409**；`reason=專案正在執行中`；`details.runId`＝步驟 6 的 run |
| 8 | 角色與參數：viewer `POST execute` → **403**；不存在的專案 → **404**；`autonomyLevel:11` → **400**；`scope:{mode:"ALL", goalIds:[…]}` → **400**；Phase 2 `PUT /tasks/{id}` `{maxRetries:25}` → **400**（`errors[0].field=maxRetries`，DTO 的 `@Max(20)`，AR-14；execute 的第 9f 項由後端整合測試以直接改 DB 的方式驗） | |

---

### E2E-03　execute 成功 → SSE 收到 step 事件 → Task／run COMPLETED → metrics 對得上　〔API-EXE-01、05～08、MON-01～06、SSE-01／US-E-01、03、09、11、M-01～04〕

**前置**：PRJ-A（新）；operator；SSE 用 `?access_token=`（operator 的 access token）。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute` `{autonomyLevel:4, tokenBudget:100000, scope:{mode:"ALL"}}` | **201**；`runNumber=1`、`status=RUNNING`、`bridgeStatus=RUNNING`、`tokenBudget=100000`、`totalTokensUsed=0`、`scope.mode=ALL` |
| 2 | Phase 2 讀取（可能與引擎啟動競速） | 專案 `status=EXECUTING`；T2、T3 為 `QUEUED`；T1 為 `QUEUED` 或 `RUNNING` |
| 3 | 立即開 `GET /stream/executions/{runId}/logs?access_token=…`，收到串流結束為止（≤ 60 秒） | 第一個框架解析為 `retry`＝3000（冒號後空白不拘，§2.1）；id 依 `(seq,n)` 嚴格遞增且不重複；`status-change` 序列含 `RUNNING`…最後一則 `COMPLETED`（`bridgeStatus=COMPLETED`）且其後連線關閉；`source=STEP` 的 `log` 依序為 `STARTED G1-T1`、`COMPLETED G1-T1`、`STARTED G1-T2`、`COMPLETED G1-T2`、`STARTED G2-T1`、`COMPLETED G2-T1`，且 `taskId` 為夾具任務 id、`COMPLETED` 的 `message` 結尾為 `Token: 1240`；至少 1 則 `source=ENGINE`；0 則 `review-request`、0 則 `alert` |
| 4 | `GET run` | `status=COMPLETED`、`bridgeStatus=COMPLETED`、`completedSteps=3`、`totalSteps=3`、`totalTokensUsed=3720`、`tokenBudget=100000`、`completedAt` 非 null、`pendingReviews=[]`、`bridge.connected=true`、`bridge.instance=e2e-bridge`、`lastEventSeq` ＝ SSE 最後一則的 `seq` |
| 5 | `GET /executions/{runId}/steps?size=200` | 6 列（三個任務各 `STARTED`＋`COMPLETED`），依 `stepNumber` 嚴格遞增；`stepId` 依序 `G1-T1`…；`COMPLETED` 列 `tokensUsed=1240`、`STARTED` 列為 null；`action` 形如 `G1-T1: 初始化`。再以 `afterSeq=<第 3 列的 stepNumber>` 查 → 剩 3 列 |
| 6 | `GET …/dag` | 5 個節點（2 `GOAL`＋3 `TASK`）、邊 1 條 `DEPENDENCY`＋3 條 `CONTAINS`；全部 `status=COMPLETED`；`TASK` 節點 `sequence` 為 1、2、3 |
| 7 | `GET …/checkpoints` | 3 筆：`after-G1-T1`、`after-G1-T2`、`after-G2-T1`；`stepIdx` 為 1、2、3；`stepId` 為 `G1-T2`、`G2-T1`、`""`；`isAutomatic=true` |
| 8 | Phase 2 讀取 | 專案、兩個目標、三個任務皆 `COMPLETED`；每個任務 `actualTokens=1240`、`retryCount=0`、`startedAt`／`completedAt` 非 null；`GET /tasks/{id}` 的 `executionHistory` 有 2 筆（`STARTED`、`COMPLETED`） |
| 9 | `GET /monitor/projects/{pid}/metrics?runId={runId}` | `totalTokens.value=3720`；`taskCompletionRate.value=100.0`（`previousValue=0.0`、`delta=100.0`）；`taskSuccessRate.value=100.0`；`retryRate.value=0.0`；`averageRetryCount.value=0.0`；`tokenBudgetUsageRate.value=3.7`；`taskStatusDistribution.COMPLETED=3`（其餘 0）；`averageTaskDurationSec.value` 介於 0.5 與 30；`taskDurations` 3 筆；`agentAvailability.value=100.0`（run 開始時立即探測一次） |
| 10 | `GET …/token-trend?runId={runId}&bucket=HOUR` | 各點 `tokens` 加總 3720；最後一點 `cumulativeTokens=3720`；各點 `budget=100000` |
| 11 | `GET …/task-trend?runId={runId}` | `started` 加總 3、`completed` 加總 3、`failed` 與 `retried` 皆 0 |
| 12 | `GET …/logs?runId={runId}&order=asc&size=200` | 含 `Run #1 開始執行（自治等級 4）`（`source=RUN`）、六筆 `source=STEP` 與 `Run #1 已完成`；`level=ERROR` 篩選 → 0 筆 |
| 13 | `GET …/alerts?runId={runId}`；`GET /projects/{pid}/executions` | `[]`；一筆批次：`runNumber=1`、`status=COMPLETED`、`tasksTotal=3`、`tasksCompleted=3`、`tasksFailed=0`、`successRate=100.0`、`durationSec≥1` |
| 14 | 一致性（A1） | Bridge 直接 `GET /autoclaude/runs/{runId}`：`status=COMPLETED`、`completed_steps=3`、`tokens_used=3720`，與 Console 回應、DB 列一致 |
| 15 | 報表：`GET /monitor/projects/{pid}/report?format=csv&runId={runId}`（`Accept: text/csv`） | **200**；`Content-Type` 為 `text/csv`；`Content-Disposition` 含 `monitor-report-`；本文以 BOM 開頭，第一行 `#report,`，依序含 `#section,summary`、`#section,runs`、`#section,tasks`、`#section,alerts` 四段；`summary` 段有 `totalTokens,3720,0,3720,TOKENS`；`runs` 段 1 列、`tasks` 段 3 列、`alerts` 段 0 列；`format=pdf` → **200**、`Content-Type: application/pdf`、本文以 `%PDF-` 開頭、`Content-Disposition` 檔名以 `.pdf` 結尾（v1.2，C-4；內容驗收見 E2E-13 第 4 列）；`format=xls` → **400**（`不支援的報表格式`）；viewer 亦可下載 |

---

### E2E-04　自治閘：Level 1 在第一步之後 PAUSED＋review-request，APPROVE 後 resume 跑完（含 Level 2／3 對照與 SSE 重播）　〔API-AUT-01～03、EXE-10、SSE-03／US-E-04、05、07、08〕

**前置**：PRJ-A（新）；operator。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute` `{autonomyLevel:1, tokenBudget:100000}` | **201** |
| 2 | 開 `/logs` SSE，觀察到 `status-change` 為 `PAUSED` 為止 | 事件順序：`STARTED G1-T1` → `COMPLETED G1-T1` → `status-change PAUSED`（`reason` 含 `在步驟邊界暫停`、`已完成 1 步`）→ `review-request`：`kind=TASK_CONFIRM`、`status=PENDING`、`taskId`＝T2、`goalId`＝G1、`allowedDecisions=[APPROVE,REJECT]`、`reason=Level 1：請確認是否繼續執行任務「設定」`，其 `id`＝`<PAUSED 事件的 seq>.1`。**PAUSED 之前不得出現 `G1-T2` 的 `STARTED`**（被中止的 spawn 不發 STARTED） |
| 3 | `GET run`、`GET /notifications/summary`、Phase 2 專案 | `status=PAUSED`、`bridgeStatus=PAUSED`、`completedSteps=1`、`currentStep=null`、`pendingReviews` 恰 1 筆且 id 同 SSE；`summary.pendingReviews=1`；專案 `status=READY` |
| 4 | **重播**：另開 `/logs`，`Last-Event-ID` ＝步驟 2 收到的第一則 `log` 的 id | 依序重播其後所有事件（含該 `review-request`，`review.id` 相同），每則恰一次、無 id ≤ 該值者；連線保持開啟（PAUSED 不結束）；閒置 ≥ 2 秒（e2e 的 keep-alive 設定）後收到 keep-alive 註解（解析後內容為 `keep-alive`） |
| 5 | 以 `Last-Event-ID` ＝ `review-request` 的 id 重連 | 不再重播任何事件，只有 keep-alive |
| 6 | `POST review/{reviewId}` `{decision:"SKIP"}` | **409**；`reason=此審核項不允許該決定`；`details.allowedDecisions=[APPROVE,REJECT]` |
| 7 | `POST review/{隨機 uuid}`；以另一個 run 的審核項 id | 皆 **404** |
| 8 | `POST review/{reviewId}` `{decision:"APPROVE", comment:"ok"}` | **204**；**無** `X-Follow-Up-Run-Id` 標頭。隨即再送一次 → **409** `審核項已處理`（`details.status=APPROVED`、`decidedBy=operator`） |
| 9 | SSE 續看 | `status-change RUNNING` → `STARTED G1-T2`（**恰一次**）→ `COMPLETED G1-T2` → `status-change PAUSED`（`已完成 2 步`）→ 第二個 `review-request`：`kind=TASK_CONFIRM`、`taskId`＝T3、`goalId`＝G2 |
| 10 | `POST review/{#2}` `APPROVE` | **204**；`STARTED G2-T1`（最後一步，**不再 pause**）→ `COMPLETED G2-T1` → `status-change COMPLETED`；串流關閉 |
| 11 | 終態檢查 | `GET run`：`COMPLETED`、`completedSteps=3`、`totalTokensUsed=3720`（被中止的 spawn 不產生 token 事件）；DB `review_requests` 2 列 `status=APPROVED`、`decided_by=operator`（第一列 `comment=ok`）、`event_sub=1`；`execution_steps` 中 T1、T2 的 `STARTED` 各恰 1 列 |
| 12 | 手動 resume 處理待決審核項 | 另開一個 Level 1 批次（**用一個新的 PRJ-A**：原專案已 `COMPLETED`，再 execute 會在第 7c 項回 409 `沒有可執行的任務`），PAUSED 後改用 `POST /executions/{runId}/resume`（不走審核）→ **200**；該審核項自動關閉為 `APPROVED`（`decidedBy`＝呼叫者、`comment=以手動恢復處理`）；run 續跑（§3.6.3 備註） |

**自治等級對照**（各用新的 PRJ-A；`tokenBudget` 皆 100000）：

| 等級 | `:pause` 呼叫時機 | PAUSED 位置 | review `kind`／`goalId`／`taskId` | `allowedDecisions` | 之後 |
|------|-------------------|-------------|-----------------------------------|--------------------|------|
| 1 | `STARTED G1-T1`、`STARTED G1-T2` | 第 1、2 步之後（各一次） | `TASK_CONFIRM`／T2 的目標／T2；再來 `TASK_CONFIRM`／T3 的目標／T3 | `APPROVE,REJECT` | 兩次 APPROVE 後 COMPLETED |
| 2 | 只有 `STARTED G1-T2`（G1 的最後一步） | 第 2 步之後（G1 與 G2 之間） | `GOAL_CONFIRM`／G2／T3 | `APPROVE,REJECT` | 一次 APPROVE 後 COMPLETED |
| 3 | 同等級 2 | 同等級 2 | `GOAL_COMPLETED`／G1／T2 | `APPROVE,REJECT,RETRY` | 一次 APPROVE 後 COMPLETED |
| 4 | 無 | 無 | 無審核項 | — | 直接 COMPLETED |

**REJECT 變體**（等級 3，G1 完成後 PAUSED，對 `GOAL_COMPLETED` 審核項 `REJECT`）：**204**；run `CANCELLED`；專案 `READY`；審核項 `REJECTED`（`decided_by=operator`）；T3 `CANCELLED`、G2 `PENDING`。**G1 `FAILED`（人類判定）**——斷言要在 run 進入 `CANCELLED` **之後**才讀：消費者處理 `status CANCELLED` 時會先把 G1 依 R-goal 重算為 `COMPLETED`（T1、T2 都完成），再套人工判定改回 `FAILED`；沒有這個順序，G1 會被蓋回 `COMPLETED`（§3.5.3 的人工判定優先，AR-11）。等級 1 的 `TASK_CONFIRM` `REJECT` 同樣 → run `CANCELLED`，但不標任何目標 `FAILED`（只有 `GOAL_COMPLETED` 的 `REJECT` 會）。

**等級 3 的 RETRY 變體**：PAUSED 在 G1 之後，`RETRY` → 目標 G1 是第一個目標、沒有 `step_idx=0` 的快照 → 走後續批次：**204** 且帶 `X-Follow-Up-Run-Id`；原 run 被 `:stop` 為 `CANCELLED`；新批次（`runNumber=2`，`scope.followUpOfRunId` ＝原 run）自 G1 起重跑。這條路徑沒有 PAUSED 的 restore，所以不碰到 AR-01 的 Bridge 缺陷；要驗「非第一個目標的 `GOAL_COMPLETED`→`RETRY`」（＝PAUSED 的 restore）需要三個目標的專案，並依賴 AR-01 的 Bridge 修復（同 E2E-07 步驟 6）。

---
### E2E-05　ESCALATED（`MOCK_CLAUDE_FAIL_REGEX` 製造失敗）→ 審核 RETRY → 再失敗 → SKIP　〔API-EXE-10、AUT-03、04、ALR-03／US-E-06～08、T-06〕

**前置**：PRJ-A（新）但 **T2 的 `description`＝`請輸出 [T2_DONE] [FAIL_ME]`**（T2 在 mock 下必失敗）；`maxRetries=1`；operator；**`model.apiKey` 為空**（§5.0.2：引擎沒有金鑰就不會在 ESCALATION 時外呼模型做演化提案，否則 `status FAILED` 會被退避拖到數十秒，TBC-2）。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute` `{autonomyLevel:4}` 並開 `/logs` SSE 到串流關閉 | `COMPLETED G1-T1` → `STARTED G1-T2`(attempt 1) → `RETRYING G1-T2`(attempt 2) → `FAILED G1-T2`(attempt 2) → `alert`（`origin=ENGINE`、`code=ESCALATION`、`severity=CRITICAL`，id 為 Bridge seq）→ `status-change FAILED`（`reason` 以 `引擎升級（ESCALATION）` 開頭）→ `review-request`（`kind=ESCALATED`，id `<FAILED 事件的 seq>.1`）→ 串流關閉（終態） |
| 2 | `GET run` | `status=FAILED`、`completedSteps=1`；`reason` 以 `引擎升級（ESCALATION）` 開頭；`pendingReviews[0]`：`kind=ESCALATED`、`taskId`＝T2、`goalId`＝G1、`allowedDecisions=[RETRY,SKIP,REJECT]`、`reason` 含 `重試 1 次仍失敗` |
| 3 | Phase 2 與告警 | 專案 `FAILED`；G1 `FAILED`；G2 `PENDING`；T1 `COMPLETED`；T2 `ESCALATED`（`retryCount≥1`）；T3 `PENDING`（`QUEUED` 被系統重設）。`GET …/alerts`：一筆 `rule=ENGINE_ESCALATION`、`severity=CRITICAL`、`subject=step:G1-T2`、未確認；`summary`：`pendingReviews=1`、`unacknowledgedAlerts=1` |
| 4 | `POST review/{id}` `{decision:"APPROVE"}` | **409** `此審核項不允許該決定`（`allowedDecisions=[RETRY,SKIP,REJECT]`） |
| 5 | **RETRY**：`{decision:"RETRY", comment:"再試一次"}` | **204**，**無** `X-Follow-Up-Run-Id`（找得到還原點 `after-G1-T1`，`stepIdx=1`，走 Bridge restore）；5 秒內 `GET run` 為 `RUNNING`；SSE（新連線，`Last-Event-ID`＝步驟 1 的最後 id）：`alert`（`origin=ENGINE`、`code=RESTORE`、`severity=INFO`、**無 `alertId`**）→ `status-change RUNNING` → `STARTED G1-T2`(attempt 1，**第二次出現**：restore 後引擎重做該步，§3.5.1 第 4 點) → `RETRYING`(2) → `FAILED`(2) → `alert ESCALATION`（同一步驟、未確認的 `ENGINE_ESCALATION` 已存在 → 被去重，**無 `alertId`**，仍轉發 SSE）→ `status-change FAILED` → 第二個 `review-request`（`ESCALATED`，PENDING）。第一個審核項 `status=RETRIED`、`decidedBy=operator`、`comment=再試一次`；`runNumber` 仍為 1；mock trace 中 `[T1_DONE]` 恰 1 次（T1 未重跑）。**注意**：restore 沿用原 playbook，T2 的 prompt 未變，所以再次失敗是預期行為 |
| 6 | **SKIP**（對第二個審核項）：`{decision:"SKIP"}` | **204**，**帶 `X-Follow-Up-Run-Id`**＝R2。`GET /executions/{R2}`：`runNumber=2`、`scope.mode=SELECTED`、`scope.taskIds=[T3]`、`scope.followUpOfRunId`＝R1、`autonomyLevel=4`、`tokenBudget` 同 R1；R2 的 DAG 只有 G2、T3（**step_id 為 `G1-T1`**：每個批次獨立編號，§3.4.4）；R2 跑到 `COMPLETED`（`totalTokensUsed=1240`） |
| 7 | 終態檢查 | T2 `SKIPPED`；T3 `COMPLETED`；G1 `COMPLETED`（T1 完成＋T2 跳過）；G2 `COMPLETED`；專案 `COMPLETED`；第二個審核項 `status=SKIPPED`；R1 仍為 `FAILED`；`GET /projects/{pid}/executions` 兩筆（R2 在前）；`unacknowledgedAlerts` 仍為 1（第一次升級的 `ENGINE_ESCALATION`：告警不因處置自動確認；步驟 5 的第二次同一步驟升級在未確認前不重複產生，故沒有第二列，只有 SSE 轉發） |

**變體 V1：第一步失敗的 RETRY**（T1 帶 `[FAIL_ME]`）：run `FAILED` 後 `RETRY` → 沒有 `step_idx=0` 的快照 → **204＋`X-Follow-Up-Run-Id`**；新批次（範圍＝專案內全部非完成任務）重跑並再度失敗，產生新的 `ESCALATED` 審核項；舊審核項 `RETRIED`。
**變體 V2：REJECT**：對 `ESCALATED` 審核項 `REJECT` → **204**，審核項 `REJECTED`；run 維持 `FAILED`、任務維持 `ESCALATED`、**不呼叫 Bridge**（Bridge 的 run 狀態不變）。
**變體 V3：新批次取代舊審核項**：run `FAILED` 且審核項 `PENDING` 時，直接 `POST execute` 開新批次 → 舊審核項自動 `status=REJECTED`、`decided_by=system`、`comment` 含 `已由第 2 批次取代`。
**變體 V4：Level 5**：`autonomyLevel:5` 執行同一專案 → 行為與等級 4 相同（失敗時建 `ESCALATED` 審核項）；其他失敗型態（halt、異常結束、orphaned）的「等級 1～4 不建審核項、等級 ≥5 建審核項」由後端單元測試的決策表覆蓋（難以在 mock 下決定性製造）。

---

### E2E-06　cancel → CANCELLED（並可重新執行）　〔API-EXE-04／US-E-06〕

**前置**：PRJ-A（新）；operator；`autonomyLevel:4`。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute`，開 `/logs` SSE，等到 `STARTED G1-T1` | **201** |
| 2 | `POST cancel` | **200**；`bridgeStatus∈{CANCELLING,CANCELLED}`（`status` 為 `RUNNING` 或 `CANCELLED`） |
| 3 | SSE | `status-change`（`runStatus=RUNNING`、`bridgeStatus=CANCELLING`）→ `status-change CANCELLED`；15 秒內串流關閉 |
| 4 | `GET run` 與 Bridge 快照 | `status=CANCELLED`、`completedAt` 非 null、`completedSteps=0`、`pendingReviews=[]`；Bridge `pid=null`（無殘留行程） |
| 5 | Phase 2 | 專案 `READY`；T1 `CANCELLED`（原 `RUNNING`）、T2／T3 `CANCELLED`（原 `QUEUED`，US-E-06）；G1／G2 `PENDING`（R-goal：沒有進度） |
| 6 | 再 `cancel`、`pause`、`resume` | 皆 **409** `目前執行狀態不允許此操作`（`details.runStatus=CANCELLED`、`details.action` 為各自動作） |
| 7 | **可重新執行**：`POST execute` `{}` | **201**；`runNumber=2`；三個任務由 `CANCELLED` 系統重設為 `QUEUED` 後跑到 `COMPLETED`；專案 `COMPLETED` |
| 8 | **PAUSED 時取消**（新專案，等級 1）：待決審核項存在時 `POST cancel` | **200**，狀態直接 `CANCELLED`（`:stop` 對 PAUSED 即時收尾）；該批次的待決 gate 審核項自動 `REJECTED`（`decided_by=system`、`comment=執行已取消`） |

---

### E2E-07　restore：從歷史 checkpoint 續跑　〔API-EXE-08、09／US-E-11〕

**前置**：PRJ-A（新）以等級 4 跑到 `COMPLETED`（`totalTokensUsed=3720`）；operator。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `GET …/checkpoints` | 3 筆（見 E2E-03 步驟 7）；記下 `after-G1-T1` 的 id（`stepIdx=1`） |
| 2 | `POST restore/{after-G1-T1}` | **200**；`status=RUNNING`、`bridgeStatus=RUNNING`；專案回 `EXECUTING`；T2、T3 重設為 `QUEUED`（T1 維持 `COMPLETED`） |
| 3 | SSE（`Last-Event-ID`＝還原前最後一則的 id） | `alert`（`ENGINE`、`RESTORE`、`INFO`）→ `status-change RUNNING` → `STARTED G1-T2` → `COMPLETED G1-T2` → `STARTED G2-T1` → `COMPLETED G2-T1` → `status-change COMPLETED`；**沒有** `G1-T1` 的 `STARTED` |
| 4 | 終態檢查 | `COMPLETED`、`completedSteps=3`、`totalTokensUsed=6200`（3,720＋2×1,240，Bridge 的累計跨 restore 持續）；`GET …/checkpoints` 數量大於 3（append-only）；`GET steps` 共 10 列（原 6＋T2、T3 各 `STARTED`＋`COMPLETED`）；mock trace 中 `[T1_DONE]` 1 次、`[T2_DONE]` 2 次、`[T3_DONE]` 2 次；T2、T3 `actualTokens=2480`（兩次執行累計）、T1 `1240`；專案回到 `COMPLETED` |
| 5 | 負向 | 對 `RUNNING` 的 run restore → **409** `目前執行狀態不允許此操作`；他人 run 的 `checkpointId` → **404**；專案已有較新批次（`runNumber` 更大）時對舊批次 restore → **409** `只能還原專案最新的執行批次`（`details.latestRunNumber`）；viewer → **403** |
| 6 | **PAUSED 時 restore**（等級 1）：第一次 PAUSED 後 `restore` 到 `after-G1-T1` | **200**；run 繼續；待決 gate 審核項自動 `REJECTED`（`decided_by=system`、`comment=執行已還原`）。🔴 **依賴 Bridge 修復（AR-01）**：未修復的 Bridge 在 DB 模式對 PAUSED 的 run 做 restore 會自撞 advisory lock，此步驟回 409 `同專案同路徑已有執行中的批次`（`details.holderRunId`＝這個 run 自己）且鎖外洩——登記為 Bridge 缺陷，不是契約缺陷；Bridge 修復尚未落地時，冒煙以步驟 2 的終態 restore 代替，本步驟標「待 AR-01」 |

---

### E2E-08　Token 預算告警（小預算）　〔API-ALR-01、02／US-M-05、E-10〕

**前置**：PRJ-B（5 任務，新）；operator；`tokenBudget:1500`；同時開 `/logs` 與 `/metrics` 兩條 SSE。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute` `{autonomyLevel:4, tokenBudget:1500}` | **201** |
| 2 | T1 的 token 事件（1,240）後 | `/metrics`：`token-update` `tokensUsed=1240`、`budgetUsageRate=82.7`；`/logs`：`alert`（`origin=CONSOLE`、`rule=TOKEN_BUDGET_WARNING`、`severity=WARNING`、`subject=run:<runId>`、`message=Token 使用量已達預算的 83%（1240 / 1500）`，id 為 `<seq>.<n>`、`n≥1`） |
| 3 | T2 的 token 事件（累計 2,480）後 | `token-update` `tokensUsed=2480`、`budgetUsageRate=165.3`；`alert`（`rule=TOKEN_BUDGET_EXCEEDED`、`severity=CRITICAL`、`message=Token 使用量已超出預算（2480 / 1500），已要求暫停執行`）；Console 對 Bridge 呼叫 `:pause` |
| 4 | 等 `status-change PAUSED` | `completedSteps` 介於 **2 與 4**（含）——`:pause` 的送達只要在最後一步之前就必然暫停；因每步 ≥0.6 秒遠大於消費者延遲，實務上為 3。**不得**直接 `COMPLETED`。`pendingReviews=[]`（預算暫停不建審核項） |
| 5 | `GET …/alerts?runId={runId}` | 恰 2 筆：`TOKEN_BUDGET_WARNING`、`TOKEN_BUDGET_EXCEEDED`，皆 `acknowledged=false`；`summary.unacknowledgedAlerts=2` |
| 6 | `POST resume` → 跑完 | **200**；run `COMPLETED`、`totalTokensUsed=6200`；告警仍恰 2 筆（**去重**：未確認前不重複產生）；**resume 後不再被暫停**——`:pause` 綁「這則告警真的新增了一列」（§3.7），resume 後 `used > budget` 的判定被未確認的同一告警擋下（沒有新增列），所以不再呼叫 `:pause`；專案 `COMPLETED` |
| 7 | 確認告警 | operator `POST /monitor/alerts/{warningId}/acknowledge` → **204**；再次確認 → **204**（冪等，`acknowledgedBy／At` 不變）；`GET …/alerts?acknowledged=false` 只剩 CRITICAL 一筆；viewer 確認 → **403**；不存在的 id → **404** |
| 8 | 指標 | `GET …/metrics?runId=…`：`tokenBudgetUsageRate.value=413.3`；`totalTokens.value=6200` |

**變體 V1：單一任務上限**：`scope.limits.taskTokens=1000`、`tokenBudget=1000000` → T1 的 token 事件（1,240 > 1,000）後出現 `TOKEN_BUDGET_EXCEEDED`、`subject=task:<T1 id>`、`message` 含 `任務「初始化」` 與 `1000`，並 `:pause`。

---

### E2E-09　系統參數：token_guard 跨鍵校驗、敏感值、reveal、重置、匯出匯入、歷史　〔API-SET-01～09、NFR-SEC-05／US-S-01～08〕

**前置**：admin；其他角色見各步。每步的「DB 不變」指 `system_configs` 該鍵的 `value` 與 `system_config_history` 筆數不變。

| # | 動作 | 預期 |
|---|------|------|
| 1 | viewer `GET /settings` | **200**；六個分類鍵數 `model=10、agent=9、execution=10、monitor=6、autoclaude=11、sdd=4`（共 50）；每筆都有 `effect`；`model.apiKey`：`value=••••••••`、`isEncrypted=true`；`execution.compactThresholdPct`：`value=80`、`min=1`、`max=99`、`effect=ENGINE`；`model.apiUrl`：`defaultValue=https://api.minimax.io/v1/text/chatcompletion_v2`（V5 校正後的預設，AR-09；`value` 視先前情境 E2E-01 是否改過而定，不斷言）；`monitor.refreshIntervalMs`：`value=defaultValue=10000`、`min=10000`（AR-06） |
| 2 | `PUT /settings/execution/token-guard` `{compactThresholdPct:90, haltThresholdPct:80}` | **400**；`reason=halt_threshold_pct 必須大於 compact_threshold_pct`（PRD 逐字）；兩鍵 DB 不變（80／90） |
| 3 | 同上 `{80, 80}`；`{100, 100}`；`{0, 50}` | 相等 → **400** 同 reason；`100`（超過 compact 上限 99）與 `0` → **400**（Bean Validation，`errors[0].field` 為對應欄位，無該 reason） |
| 4 | `{compactThresholdPct:70, haltThresholdPct:95}` | **200**；回兩筆 `ConfigResponse`；歷史新增 2 筆（`80→70`、`90→95`，`changedBy=admin`） |
| 5 | **單鍵跨鍵校驗**：`PUT /settings/execution/haltThresholdPct` `{value:"60"}`；`PUT …/compactThresholdPct` `{value:"96"}` | 皆 **400**，reason 同步驟 2（讀對端現值 70／95）；DB 不變 |
| 6 | `PUT …/compactThresholdPct` `{value:"abc"}` | **400**；`reason=參數值不符合型別或驗證規則`；`errors[0].field=value` |
| 7 | **敏感值**：`PUT /settings/model/apiKey` `{value:"sk-new"}`（不帶 confirm） | **409**；`reason=敏感參數更新需二次確認（confirm=true）`；DB 不變。改帶 `confirm:true` → **200**，`value=••••••••`、`hasValue=true`；歷史該筆 `oldValue`／`newValue` 皆 `••••••••` |
| 8 | **reveal**：operator `GET /settings/model?reveal=true`；viewer 同；admin 同 | operator／viewer **403**（`reason=僅 ADMIN 可揭露敏感參數`）；admin **200**，`apiKey.value=sk-new`（明文）；審計日誌有 `settings.reveal`（不含值）。未帶 `reveal` 的 operator `GET` → 仍是 `••••••••` |
| 9 | **角色**：operator `PUT` 任一參數／`POST reset`／`POST export`／`POST import`／`POST test-connection` | 皆 **403** `ACCESS_DENIED`；viewer 與 operator 的 `GET` 皆 **200** |
| 10 | **重置與跨鍵**（此時 compact=70、halt=95）：① `PUT /settings/execution/token-guard` `{70, 75}`；② `POST /settings/execution/compactThresholdPct/reset`；③ `POST …/haltThresholdPct/reset`；④ 再 `POST …/compactThresholdPct/reset` | ① **200**；② **400**（compact 預設 80 ≥ 目前 halt 75；reason 同步驟 2；compact 仍為 70）；③ **200**（halt→`90`）；④ **200**（compact→`80`，80 < 90）。每個成功的重置各寫一筆歷史 |
| 11 | 加密鍵重置 | `POST /settings/model/apiKey/reset`（無 confirm）→ **409** `敏感參數重置需二次確認（confirm=true）`；`?confirm=true` → **200**，`hasValue=false`。`POST /settings/execution/reset` → **200**，回該分類 10 筆且值皆為預設 |
| 12 | **匯出匯入**：`POST /settings/export` | **200** JSON：`version=1`、`configs` 50 筆；`model.apiKey`／`autoclaude.dbDsn` 的 `value="<encrypted>"`；標頭 `Content-Disposition` 含 `aisdlc-settings-` |
| 13 | 改檔案中 `monitor.refreshIntervalMs` 為較大的合法值（取值見表後註記）後 `POST /settings/import` | **200**；`applied=1`、`skipped=49`（含 2 筆 `<encrypted>` 佔位＋47 筆值未變）、`errors=[]`；歷史新增 1 筆。再匯入 `monitor.refreshIntervalMs="900"` 的檔 → **200**，`errors` 含該鍵（低於最小值，`reason=參數值不符合型別或驗證規則`，AR-06），`applied=0`。再匯入 compact=90／halt=80 的檔 → **200**，`errors` 含兩筆（`compactThresholdPct`、`haltThresholdPct`），`reason=halt_threshold_pct 必須大於 compact_threshold_pct`，兩鍵皆未套用 |
| 14 | 匯入異常檔 | `version:2` → **400** `設定檔格式錯誤`（`details.problem=unsupported_version`）；不是 JSON → **400**（`invalid_json`）；2MB 檔 → **413** `設定檔超過 1MB 上限`；`.txt` → **415** |
| 15 | **SEC-04（儲存時）**：`PUT /settings/model/apiUrl` `{value:"http://10.0.0.5"}`；`{value:"https://example.com"}`；`{value:"http://127.0.0.1:<WM_PORT>/v1/chat/completions"}` | **400**（`目標位址未通過 SSRF／allowlist 檢查`，`details.violation=private_ip`）；**400**（`not_in_allowlist`）；**200**（`127.0.0.1` 在 e2e allowlist，且 `allow-loopback=true` 放行 loopback 字面；完整端點 URL，後端不補路徑） |
| 16 | **歷史**：`GET /settings/history?category=execution&key=haltThresholdPct&page=0&size=2` | **200**；`totalElements≥3`；`changedAt` 由新到舊；單獨給 `key`（無 `category`）→ **400** |
| 17 | **`autoclaude.claudeCommand` 驗證（AR-12）**：`PUT /settings/autoclaude/claudeCommand` `{value:"<REPO_ROOT>\\.venv\\Scripts\\aisdlc-mock-claude.exe"}`（Windows 絕對路徑）；再試一個路徑中含空白的值（例：`<含空白的目錄>\\x.exe`） | **200**（允許反斜線、冒號、點與 `.exe`）；**400**（含空白，`參數值不符合型別或驗證規則`——引擎不對 `claude.command` 做 shlex 切分）。驗完把值設回測試所需的絕對路徑 |

註（步驟 13）：`monitor.refreshIntervalMs` 的較大合法值取字串 `"15000"`；新預設與最小值皆為 `10000`（附錄 C.4），低於它的值（例：`"900"`）會被驗證規則擋下。

---

### E2E-10　test-connection：私網 URL 被 SSRF 拒絕　〔API-SET-06／US-S-05／NFR-SEC-04〕

**前置**：admin；假伺服器的 `POST /v1/chat/completions` 預設 stub 回 200（不論本文）；`model.timeout=3`；e2e profile 已設 `allow-loopback=true`（§5.0.1）。`apiUrl` 一律是**完整的端點 URL**（§1.5.7，後端不補路徑）。

| 請求（`POST /settings/test-connection` body） | 預期 |
|-----------------------------------------------|------|
| `{apiUrl:"http://10.0.0.5:8080"}` | **422**；`reason=目標位址未通過 SSRF／allowlist 檢查`；`details={host:"10.0.0.5", violation:"private_ip"}`；**沒有任何連線**（WireMock 與網路皆無請求） |
| `{apiUrl:"http://192.168.1.1"}`、`http://172.16.0.9`、`http://100.64.0.1` | **422** `private_ip` |
| `{apiUrl:"http://169.254.169.254/latest/meta-data"}` | **422** `link_local` |
| `{apiUrl:"http://[::1]:8080"}` | **422** `loopback`（`::1` 不在 allowlist） |
| `{apiUrl:"http://0x7f.0.0.1"}`、`http://2130706433` | **422** `malformed_url`（非標準 IP 寫法一律拒絕） |
| `{apiUrl:"ftp://api.minimax.io/v1/text/chatcompletion_v2"}` | **422** `scheme` |
| `{apiUrl:"file:///etc/passwd"}`（空 host；規則 1 先於規則 2） | **422** `malformed_url`（不是 `scheme`；B1-2） |
| `{apiUrl:"http://exämple.com/v1"}`（host 含非 ASCII 字元） | **422** `malformed_url`（IDN 一律拒絕） |
| `{apiUrl:"http://user:your_password_here@api.minimax.io/v1/text/chatcompletion_v2"}`（userinfo 一律拒絕；此為測試夾具，不是真值） | **422** `userinfo` |
| `{apiUrl:"https://example.com"}`、`http://localhost.evil.example` | **422** `not_in_allowlist` |
| `{apiUrl:"http://rebind.e2e.test/v1/chat/completions"}`（e2e 把此名稱加入 allowlist，DNS 覆寫為私網位址 `10.0.0.5`） | **422** `dns_rebinding`（allowlist 內的名稱解析到私網位址仍拒；沒有任何連線） |
| `{apiUrl:"http://127.0.0.1:<WM_PORT>/v1/chat/completions", apiKey:"sk-secret-xyz"}` | **200**；`success=true`、`message=連線成功`、`httpStatus=200`、`resolvedHost=127.0.0.1`、`latencyMs≥0`；**假伺服器驗證**：收到 `POST /v1/chat/completions` 一次，`Authorization: Bearer sk-secret-xyz`，本文 `max_tokens=1`、`stream=false`、`messages[0].content=ping`（§1.5.7 的探測請求，原樣 POST 該 URL）；回應本文與日誌**都不含** `sk-secret-xyz` |
| `{apiUrl:"http://127.0.0.1:<WM_PORT>"}`（沒有路徑；假伺服器對 `POST /` 回 404） | **200**；`success=false`、`message=端點路徑不存在或不接受 POST（HTTP 404）`——證明後端**沒有**替 URL 補路徑（AR-09） |
| 假伺服器的 `POST /v1/chat/completions` 回 401 | **200**；`success=false`、`message=認證失敗（HTTP 401）` |
| 假伺服器回 302 `Location: http://127.0.0.1:<WM_PORT>/redirected` | **200**；`success=false`、`message` 含 `已拒絕跟隨`；假伺服器的 `/redirected` **請求數為 0** |
| 假伺服器延遲 8 秒（`model.timeout=3`） | **200**；`success=false`、`message` 含 `連線逾時`（約 3 秒內返回） |
| 空 body，且已儲存的 `model.apiUrl` 被（以 DB 直接改成）`http://10.0.0.5` | **422** `private_ip`（已儲存值同樣被檢查） |
| operator／viewer 呼叫 | **403** |

稽核：每次呼叫（含被拒）都有一行 `settings.testConnection` 審計日誌（host＋結果），整份日誌不含任何 API 金鑰與 userinfo。

**後端整合測試另補（不在 e2e 環境，`allow-loopback=false`，即 production／docker 的設定）**：allowlist 內有 `127.0.0.1` 時，`{apiUrl:"http://127.0.0.1:<port>/…"}` 仍 **422** `loopback`；allowlist 內的名稱（含 `localhost`）解析到 loopback 位址 → **422** `dns_rebinding`；私網與 link-local 在任何設定下都拒（§1.5.7 的放行規則一覽）。

---

### E2E-11　限流：第 101 次請求 → 429　〔NFR-9.2-06〕

**前置**：限流鍵是 JWT subject（§0.4 第 4 點，AR-06）；**最後執行**，開始前等 60 秒讓桶回滿；viewer 與 operator 各備一組 token（未認證的情形另用唯一的 `X-Forwarded-For` 區分 IP 桶，e2e profile 信任它）。

| # | 動作 | 預期 |
|---|------|------|
| 1 | viewer 連續 100 次 `GET /api/v1/projects` | 全部 **200**；每個回應 `X-RateLimit-Limit: 100`，`X-RateLimit-Remaining` 由 99 遞減到 0 |
| 2 | viewer 第 101 次 | **429**；`code=429`、`reason=超過每分鐘 100 次請求上限`、`details={limit:100, windowSeconds:60, retryAfterSeconds:N}`（1≤N≤60）；標頭 `Retry-After`＝N、`X-RateLimit-Remaining: 0`；封包含 `traceId` |
| 3 | 同一時間 operator（另一個使用者）請求 | **200**（桶以使用者隔離；同一個連線位址不影響） |
| 4 | 被限流的 viewer 打 `GET /actuator/health` | **200**（不計入） |
| 5 | 等 `Retry-After` 秒後 viewer 再請求 | **200** |
| 6 | viewer 開 SSE 連線並維持 | 建立算 1 次；串流期間的事件不消耗額度 |
| 7 | **未認證**請求依 IP 計：用唯一的 `X-Forwarded-For: 203.0.113.<n>` 連續 101 次 `GET /api/v1/projects`（不帶 token） | 前 100 次 **401**、第 101 次 **429**（限流 filter 在授權判定之前，超限者先得 429）；換一個 `X-Forwarded-For` → **401**（IP 桶隔離）；這些請求不吃 viewer／operator 的額度 |
| 8 | `trust-forwarded-for=false`（production 預設）時帶 `X-Forwarded-For` | 標頭被忽略，以連線位址計（後端單元／整合測試，不在 E2E 環境） |

---

### E2E-12　SSE 認證、重播與終態語意　〔API-SSE-01～03／US-E-03〕

**前置**：E2E-03 產生的已完成 run（R，`lastEventSeq=S`）；E2E-04 的 PAUSED run 用於步驟 10。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `/logs` 無 token；`?access_token=garbage`；已過期的 access token；以 **refresh token** 放進 `?access_token=` | 皆 **401 JSON**（`UNAUTHENTICATED`／`TOKEN_INVALID`／`TOKEN_EXPIRED`／`TOKEN_INVALID`），在串流開始前回 |
| 2 | viewer 的 token（標頭） | **200** 串流（VIEWER 可看） |
| 3 | 標頭帶有效 token、查詢參數帶無效 token | **200**（標頭優先） |
| 4 | 不存在的 `runId` | **404 JSON** |
| 5 | 已完成的 R：`/logs` 無 `Last-Event-ID` | **200**；重播最後 `tail`（預設 200）則事件後關閉；最後一則 `status-change` 為 `COMPLETED` |
| 6 | `/logs` 帶 `Last-Event-ID: <S>` | **204**（無內容、EventSource 不再重連） |
| 7 | `Last-Event-ID: garbage`；`?tail=0`（無 `Last-Event-ID`） | 前者視為未帶 → 同步驟 5；後者重播集合為空 → **204** |
| 8 | 已完成的 R：`/metrics` | **200**，恰 3 則：`progress-update`（`completedSteps=3`、`totalSteps=3`、`progressPct=100.0`）、`token-update`（`tokensUsed=3720`）、`metric-update`（`completedTasks=3`、`totalTasks=3`、`totalTokensUsed=3720`），id 依序 `<S>.1`、`<S>.2`、`<S>.3`（**三者互異、嚴格遞增**，A4；v1.0 的 `<S>`、`<S>`、`<S>.1` 會被客戶端去重丟掉第二則，AR-02）；之後關閉。`Last-Event-ID: <S>.3` → **204**；`Last-Event-ID: <S>.1` → 仍送終態快照後關閉（尚未收到 `.2`／`.3`） |
| 9 | 進行中的 run 開 `/metrics` | 連線後先收到 3 則最新快照（id `<S>.1`／`<S>.2`／`<S>.3`），再隨即時事件更新（id `<S+1>` 起，嚴格大於 `<S>.3`）；`Last-Event-ID` 的值不影響（收斂快照） |
| 10 | PAUSED 的 run（E2E-04）閒置 | 連線保持；每 ≤ `console.sse.keep-alive-seconds`（e2e 為 2 秒）收到一則 keep-alive 註解（解析後內容為 `keep-alive`） |
| 11 | 瀏覽器預檢：自允許的 origin 對 `/api/v1/stream/…` 送 `OPTIONS`，`Access-Control-Request-Headers: last-event-id,authorization` | 回應的 `Access-Control-Allow-Headers` 含 `Last-Event-ID` |
| 12 | 日誌稽核（AR-05） | 整份**後端日誌**（存取與審計）**不含**任何 `access_token` 的值（後端整合測試以收集到的日誌斷言；`AuditLoggingFilter` 只審寫入方法、記不含 query 的 `getRequestURI()`，本來就不會記）；Docker 全棧另以 `docker compose logs nginx` 確認沒有 `access_token` 的值（nginx 的 `log_format` 遮罩，§0.7 第 4 項；**v1.2 另含 `error_log`**：重啟 backend 讓上游被切斷後，`error_log` 同樣不得出現 token——`error_log … crit`，§0.7 第 5 項） |
| 13 | Bridge 暫時不可達（後端整合測試：假 Bridge 回連線重設） | 串流不關閉；送一則**不帶 `id:` 行**的 `alert`（`origin=CONSOLE`、`code=BRIDGE_UNREACHABLE`、`severity=WARNING`）；Bridge 恢復後自動補齊事件、無缺漏 |
| 14 | 串流正常結束時的授權（TBC-1） | 步驟 5～8 的串流（含終態關閉）結束後，console-api 日誌**沒有** `AccessDeniedException`（`SseEmitter` 完成的 ASYNC dispatch 已被放行，§2.1 的實作提醒） |

---

### E2E-13　v1.2 追加情境（W5；C-1～C-12）　〔API-MON-08、API-PRJ-06、BR-26、NFR-9.3-04、NFR-9.4-04、US-S-06、US-M-07〕

**前置**：照 §5.0；各列各用新專案（名稱含情境編號）；operator 寫、viewer 讀；列 5 在 Docker 全棧（經 nginx）、列 13 需能直連 Bridge，其餘用本機 e2e 環境。以下是 W5 的**最低驗證矩陣**（QA 可再加）。

| # | 情境（裁決） | 動作 | 預期 |
|---|--------------|------|------|
| 1 | task-totals 與 task-trend 加總一致（C-1） | 兩個專案各以等級 4 跑一批 PRJ-A 到 `COMPLETED`；`GET /monitor/task-totals?from=<批次開始前>`；再對這兩個專案各 `GET …/task-trend?from=<同>&bucket=DAY` | `started`／`completed`／`failed`／`retried` **逐欄等於**兩專案各桶加總；`projectsCounted` 等於有步驟列的專案數；封存或軟刪的專案不計；viewer **200**；`to−from` 超過 92 天 → **400** `時間範圍不合法`（`errors[0].field=to`）；缺 `from` → **400**（`errors[0].field=from`） |
| 2 | 專案復原（C-3） | operator `DELETE /projects/{id}` → **204**；`GET /projects?deleted=true`；`POST /projects/{id}/restore`；`GET /projects/{id}` 與其目標、任務 | 已刪除清單含該專案（`deletedAt` 非 null）；restore **200**（`ProjectDetailResponse`）：`status` 與刪除前相同、連帶軟刪的目標與任務一併回來，**刪除專案前就單獨刪除的目標不回來**；`GET /projects` 又列得到它；`audit_log` 有 `project.restore` |
| 3 | restore 的錯誤路徑（C-3） | ① 對沒被刪的專案 restore；② 以 DB 把 `deleted_at` 改到 31 天前再 restore；③ 隨機 uuid；④ viewer 呼叫 restore 與 `GET /projects?deleted=true` | ① **409** `project_not_deleted`；② **409** `restore_window_expired`（`details.retentionDays=30`）；③ **404**；④ **403**（`ACCESS_DENIED`） |
| 4 | PDF 報表（C-4） | `GET …/report?format=pdf&runId=…`（`Accept: application/pdf`） | **200**；`Content-Type: application/pdf`；本文以 `%PDF-` 開頭；`Content-Disposition` 檔名 `monitor-report-<8 碼>-<yyyyMMdd-HHmm>.pdf`；以 PDF 文字抽取可找到專案名稱、四個區段標題與 `totalTokens`；不再有 **501** |
| 5 | refresh 暫時失敗不登出（C-5） | Docker 全棧（經 nginx）：開著執行頁，重啟 backend 容器 | `POST /auth/refresh` 得到 **502** 時 session 不被清除、不導向 `/login`；串流狀態點為「重新連線中」；backend 恢復後自動重連、事件不重複；refresh token 真的失效（401）才登出 |
| 6 | 設定原樣匯入（C-6） | admin `POST /settings/export`，把得到的檔原樣 `POST /settings/import`（e2e profile，`model.apiUrl` 現值的主機不在 allowlist）；另匯入一個把 `model.apiUrl` 改成不在 allowlist 主機的檔 | 原樣匯入 **200**：`errors=[]`、`applied=0`、`skipped=50`（2 筆 `<encrypted>`＋48 筆值未變）；改值的那一檔該鍵進 `errors`（`目標位址未通過 SSRF／allowlist 檢查`），其餘 `skipped` |
| 7 | escalation 跨批次不被吞（C-7） | 同一專案連續兩批都在 `G1-T1` 失敗（任務帶 `[FAIL_ME]`），**不確認**第一批的 `ENGINE_ESCALATION` 告警 | 第二批同樣產生新的 `ENGINE_ESCALATION` 告警列：`GET …/alerts` 共 2 列，`subject` 分別為 `step:<runId1>:G1-T1`、`step:<runId2>:G1-T1`；同一批次內同一步驟再次升級仍被去重（E2E-05 步驟 5） |
| 8 | 執行中刪除（C-8） | 專案有 `RUNNING` 或 `PAUSED` 批次時，`DELETE /goals/{尚未開始的目標}`、`DELETE /tasks/{尚未開始的任務}` | 皆 **409** `project_executing`（`details.projectId`、`runId`）；批次進入終態後同一請求 **204** |
| 9 | 手動重試（C-9） | 對 `maxRetries=1` 的 ESCALATED 任務 `POST /tasks/{id}/retry`；再把它設回 FAILED（或讓它再失敗）後第二次 retry | 兩次皆 **200**；`retryCount` 每次 +1 且**大於 `maxRetries`**（ESCALATED 任務本來就已有 `retryCount≥1`，所以第一次手動重試後 ≥2、第二次後 ≥3）；不報 409（`maxRetries` 不限制手動重試） |
| 10 | 匯入記錄重開（C-10） | parse 出含警告的記錄（例：路徑 C 的任務沒有通過標準 → `passcriteria_placeholder`）後重新 `GET /import/{id}`；再 `PUT result`；另做一次被有界閘拒絕的 parse | `warnings[]` 與 parse 回應相同、`parseOptions` 等於 parse 請求；`PUT result` 後 `warnings` 以重算值覆寫；被拒的 parse 後 `parseOptions` 為該次請求、`warnings` 不變 |
| 11 | 批次列表 `bridgeStatus`（C-11） | Level 4 的批次進行中 `POST pause`；另一個專案的批次進行中 `POST cancel`；各自立即 `GET /projects/{id}/executions` | 該批 `bridgeStatus=PAUSING`／`CANCELLING`（`status` 仍為 `RUNNING`）；終態批次的 `bridgeStatus` 等於 `status` |
| 12 | traceId 貫穿（C-12） | 對 backend 發 `POST execute`，記下回應的 `X-Trace-Id`；Bridge 以 `BRIDGE_LOG_DIR`（或 stdout）留日誌；另直連 Bridge `GET /health` 不帶標頭 | Bridge 日誌至少有一行帶 `trace_id=<該值>`（`POST /autoclaude/runs` 那一行）；Bridge 日誌**每一行**都有 `trace_id` 欄位；直連時回應仍帶自產的 `X-Trace-Id` |
| 13 | Bridge 深度探針（C-2） | `GET {bridge}/health/deep`；再把 workspace 設成唯讀（或讓 `PATH` 不含 git）重打一次；Docker 全棧看 healthcheck 與 `docker run --rm <bridge 映像> git --version` | 正常 **200**、`checks.git.version` 非空；異常 **503**、`status=degraded`、對應項 `ok:false` 帶 `reason`；全棧 healthcheck 走這一支，映像內 `git --version` 可執行；全棧跑一個批次到 `COMPLETED`（DEF-AC-003 的證明） |

---

### E2E-14　v1.3 追加情境（W7；D-11、D-12）　〔API-AUT-06、US-M-10、API-SET-10〕

**前置**：照 §5.0；本機 e2e 環境（Docker 全棧不載入 e2e profile，假伺服器不可達，§5.0.1，所以第 1～7 列不在全棧跑；第 8～9 列兩種環境都可）；各列各用新專案（名稱含 E2E-14 與列號），夾具 PRJ-A（3 任務）；operator 寫、viewer 讀、admin 設參數。

**參數與假伺服器**：

- `model.apiUrl`＝`http://127.0.0.1:<WM_PORT>/v1/chat/completions`；`model.apiKey`＝`e2e-fake-key`（`confirm=true`；**不得以 `sk-` 開頭**）。情境結束時 `POST /settings/model/apiKey/reset?confirm=true` 清空，並把本情境改過的 `agent.enableAutoMutation`、`agent.enableSelfEvolution`、`model.enableKernelBrain` 還原為 `false`（E2E-02～E2E-08 的前提，§5.0.2）。
- 假伺服器**必須立即回應**（2xx 或 5xx 皆可，不得掛住或延遲）：有金鑰時，引擎會在**最後一步之後**（run 走完全部步驟時）打一次目標驗證請求、**每次失敗型 ESCALATION** 打一次演化提案請求；Brain 開啟時，**每個失敗且尚有重試次數的 attempt** 另打一次校正請求。5xx 時每個請求被引擎重試 3 次（退避 2 秒＋4 秒），所以有金鑰的批次最多多出約 6 秒的外呼時間，§5.0.4 的 60 秒輪詢逾時足夠。
- 假伺服器收到的請求用請求 JSON 的 `messages[0].content`（system 訊息）分類：含 `"correction_prompt"`＝Brain 校正；含 `"evolution_type"`＝演化提案；含 `"is_achieved"`＝目標驗證。
- 磁碟斷言讀 `<ENGINE_WORKSPACE>/<runId>/config.yaml`（`ENGINE_WORKSPACE` 見 §5.0.1；Bridge 為每個 run 寫的引擎設定檔），**用 YAML 解析器讀，不比對文字**。
- 第 2、3 列的步驟事件序列與 Token 數，是依引擎原始碼（`kernel.py` 的 attempt 迴圈）推導的預期值；QA 實測不符時**以實測為準**，登缺陷並回報 SA，不要自行改斷言。

| # | 情境 | 動作 | 預期 |
|---|------|------|------|
| 1 | 等級 7＋金鑰（旗標全 `false`），全部步驟成功（D-11） | admin 設金鑰；operator 以 `autonomyLevel=7` `POST execute`（PRJ-A），等到 `COMPLETED`；`GET /executions/{runId}` | 201 的 `engineCapabilities`＝`{autoMutation:ENABLED, selfEvolution:ENABLED}`，詳情同值；磁碟 config：`minimax.enable_kernel_brain` 是布林 `true`、`minimax.base_url` 等於 `model.apiUrl`、`minimax.model`／`timeout_seconds` 存在、`playbook.step_timeout_seconds` 存在；**否定斷言：`playbook` 區段沒有 `max_evolutions`、`require_evolution_signoff`**（Console 不送惰性鍵）、`minimax` 區段沒有 `api_key`；`run.json` 的 `env_keys` 含 `MINIMAX_API_KEY` 這個**名稱**，而整個 run 目錄（`config.yaml`、`playbook.yaml`、`events.jsonl`、引擎日誌）都搜不到金鑰的值（A5）；run `COMPLETED`；假伺服器的「校正」請求數為 0（沒有失敗步驟，Brain 沒被諮詢） |
| 2 | 等級 7＋金鑰＋失敗步驟：Brain 真的被呼叫（D-11） | PRJ-A 的 T1 描述含 `[FAIL_ME]`（`maxRetries=1`）；假伺服器對所有請求回 **500**；`autonomyLevel=7` execute，等到終態 | run `FAILED`，`reason` 以「引擎升級（ESCALATION）」開頭；假伺服器收到 ≥ 1 個「校正」請求（Brain 在第一次失敗後立刻被諮詢）；T1 **只有 1 個 attempt**（沒有 `RETRYING` 事件，`totalTokensUsed`＝1,240）——Brain 呼叫失敗讓該步驟直接升級；run 工作區與專案目錄都沒有 `evolved_*.yaml`；T2、T3 未執行 |
| 3 | 對照：等級 3＋金鑰（Brain 關），同一個失敗夾具（D-11） | 同第 2 列夾具，`autonomyLevel=3`（旗標全 `false`） | `engineCapabilities`＝`{autoMutation:OFF, selfEvolution:ENABLED}`；磁碟 config 的 `minimax.enable_kernel_brain` 是布林 `false`；T1 有 **2 個 attempt**（`STARTED→RETRYING→FAILED`，`totalTokensUsed`＝2,480）；整個批次期間「校正」請求恆為 0，「演化提案」請求在失敗型 ESCALATION 之後出現 ≥ 1（因為有金鑰，這正是 `selfEvolution=ENABLED` 的意思）；同樣沒有 `evolved_*.yaml` |
| 4 | 沒有金鑰（D-11） | `reset` 清掉金鑰；PRJ-A 以 `autonomyLevel=7` execute，三步成功（前提：Bridge 環境沒有 `MINIMAX_*`，§5.0.1） | `engineCapabilities`＝`{UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY}`；磁碟 config **沒有 `minimax` 區段**；run `COMPLETED`（沒有因為 `enable_kernel_brain` 缺金鑰而以離開碼 1 結束）；假伺服器零請求 |
| 5 | 等級 3、沒有金鑰、旗標全 `false`（D-11） | PRJ-A 以 `autonomyLevel=3` execute | `{OFF, OFF}`；磁碟 config 沒有 `minimax` 區段；`COMPLETED` |
| 6 | 旗標單獨生效（等級 3，D-11） | ①有金鑰、只設 `agent.enableAutoMutation=true`；②有金鑰、只設 `model.enableKernelBrain=true`；③沒有金鑰、只設 `agent.enableSelfEvolution=true`；④有金鑰、只設 `agent.enableSelfEvolution=true`（每次只改一個旗標，跑完還原） | ①②皆 `{ENABLED, ENABLED}` 且 `enable_kernel_brain: true`（兩個旗標共用同一個引擎鍵）；③`{OFF, UNAVAILABLE_NO_API_KEY}`；④`{OFF, ENABLED}` 且 `enable_kernel_brain: false`（有金鑰時 `agent.enableSelfEvolution` 不改變任何東西） |
| 7 | 凍結與缺席（D-11） | 對第 1 列的批次：先清掉 `model.apiKey`，再 `GET /executions/{runId}` 與 `GET /projects/{id}/executions`；以 DB 把該批次的 `engine_capabilities` 設為 NULL 後再 `GET /executions/{runId}` | 詳情的 `engineCapabilities` 仍是第 1 列的值（建立時凍結，不隨設定變）；批次列表項**沒有**該欄位；欄位設為 NULL 後，詳情缺席或為 null（V10 之前的批次）。控制端點（pause／resume 等）快照回應帶同值，由 `ExecutionLifecycleApiIT` 驗 |
| 8 | 資源使用：執行中（D-12） | 長批次（5 個任務，`MOCK_CLAUDE_DELAY` 調到 ≥ 3 秒，`autonomyLevel=4`）；viewer 每 ≥ 2 秒輪詢 `GET /executions/{runId}`，最長 20 秒直到 `bridge.resources` 出現；再等 ≥ 6 秒輪詢一次；同時觀察前端 Agent 即時狀態卡 | `bridge.resources` 非 null：`cpuPercent`∈[0, 100]（小數 1 位）、`memoryBytes` > 0、`processCount` ≥ 1（引擎加替身子行程；Windows 的 venv 啟動器會多一層殼，不得斷言精確值）、`sampledAt` 是含 offset 的 ISO-8601 且距現在 ≤ 15 秒；兩次輪詢的 `sampledAt` 前進；回應與日誌沒有 pid；卡片「資源使用」顯示 `CPU x.x%・記憶體 N MB・M 行程`（§4.3 M-19） |
| 9 | 資源使用：沒有資料時（D-12） | 同一個批次到終態後 `GET`；另對 `PAUSED` 的批次（等級 1 夾具，E2E-04）`GET`；Bridge 停掉後 `GET`（`bridge.connected=false`） | `bridge.resources` 皆為 null 或缺席；卡片「資源使用」顯示 `—`，畫面上沒有「目前沒有提供這項資料」字樣 |

---

### E2E-15　v1.4 追加情境（W7；D-16：AISDLC_SDD 接入）　〔API-ENG-01、NFR-OBS-01、BR-13、BR-14〕

**前置**：照 §5.0；本機 e2e 環境（Docker 全棧另見第 9 列）；operator 寫、viewer 讀、admin 設參數。**本情境不使用 repo 內真實的 `build/reports/fsm`**：它被 git 忽略（`AISDLC_SDD/.gitignore:313`，§3.1.3），乾淨 clone 與 CI 沒有它，只有跑過 SDD runtime 的開發機才有；所以主體改用**夾具**，真實檔只在第 12 列選跑（主控裁決 Q7）。

**SDD 夾具**（QA 於情境前以 YAML 序列化器產生，路徑 `<E2E_ROOT>/sdd-fixture/AISDLC_SDD_v9.99/`）：

- `AISDLC_SDD_INIT.md`（一行文字即可；`/health/deep` 的 `sdd` 檢查靠它判定這是一棵 SDD 樹，§3.1.1）。
- `build/reports/fsm/FSM-STATE-e2e-alpha.yaml`：`fsm_state` 含 `project: e2e-alpha`、`session_id: sid-alpha`、`current_state: IMPLEMENTATION`、`current_sprint: 2`、`updated_at: '2026-10-16T01:02:03+00:00'`；`decision_trace` **7 筆**（`ts`、`from`、`to`、`reason`〔`r1`～`r7`，各不相同〕、`spec_refs`、`agents_consulted`、`trigger`）；`frozen_stages: [{stage: SCG-0}]`；`retry_history`：`SCG_VALIDATION.history` 2 筆、`PR_REVIEW.history` 1 筆、`RTM_VERIFY.history` 空（每筆 `{attempt, date, failure_reason, scg_gate}`，三閘各帶 `current_count`、`max_limit`）；`human_pending_tracking: {entered_at: null, reminder_sent_at: null, reminder_hours: 72, escalation_hours: 168}`。
- `FSM-STATE-e2e-bravo.yaml`：`current_state: HUMAN_PENDING`、`current_sprint: 1`、`human_pending_tracking.entered_at: '2026-10-15T08:00:00+00:00'`，其餘同 alpha 的形狀、`decision_trace` 與各閘 `history` 為空。
- 三個壞／不相干的檔：`FSM-STATE-e2e-broken.yaml`（YAML 語法錯誤）、`FSM-STATE-bad name.yaml`（檔名含空白）、`FSM-STATE-e2e-ignored.yml`（副檔名不符，被忽略）。

**第二個 Bridge**（只用它的 `/sdd/*`，不跑批次）：`uvicorn app.main:app --port 18082`，環境同 §5.0.1 的 Bridge，但 `SDD_ROOT=<E2E_ROOT>/sdd-fixture`、`BRIDGE_INSTANCE=e2e-sdd`；admin `PUT /settings/sdd/engineUrl`＝`http://127.0.0.1:18082`（`sdd.engineUrl` 優先於 `ENGINE_BRIDGE_URL`，§3.1；`autoclaude.engineUrl` 不動，批次照打 18081）。**結束動作**：`POST /settings/sdd/engineUrl/reset` 還原（非加密鍵，不需 `confirm`）、停掉 18082～18084 的 Bridge、刪夾具目錄。

| # | 情境 | 動作 | 預期 |
|---|------|------|------|
| 1 | 清單 | viewer `GET /engines/sdd`（不帶 `project`） | 200；`available=true`、`reason=null`；`version.latest="AISDLC_SDD_v9.99"`；`projects` **恰兩筆**，順序 `e2e-alpha`、`e2e-bravo`（`broken`、`bad name`、`.yml` 都不在其中）；每筆 `source` 等於檔名、`currentState`／`updatedAt` 與檔內一致；`fsm=null` 且沒有 `reason`；`checkedAt` 為 `…Z`。**v1.5 覆寫**（§1.7.1、§1.10.4、§3.1.4 (b)；ADR-016 §7.4；上列原文保留，與本註記不同處以本註記為準）：Bridge 改以淨化輸出域判斷檔名，**內部空白合法**，`FSM-STATE-bad name.yaml` 不再因檔名被擋；夾具內容可讀（現為 `fsm_state: {project: bad}`）時它**會**列入——`projects` 為**三筆**，順序（檔名 casefold 排序）`bad name`、`e2e-alpha`、`e2e-bravo`，`bad name` 那筆 `source="FSM-STATE-bad name.yaml"`、`currentState`／`updatedAt` 為 null（檔內沒有）；夾具若改成讀不動的內容，則進 `errors`、`projects` 仍兩筆。`broken`（讀不動，進 `errors`）與 `.yml`（副檔名不符）照舊不在 `projects` 內。Bridge 側的名稱規則由 E2E-17 第 13 列與 Bridge pytest 驗 |
| 2 | 單一專案：欄位與「原樣」 | `GET /engines/sdd?project=e2e-alpha` | `fsm.currentState="IMPLEMENTATION"`、`currentSprint=2`、`sessionId`、`updatedAt` 與檔相同；`decisionTrace` 長度 5，等於檔內 7 筆的**最後 5 筆**（舊→新），每筆與檔**逐值相等**（含 snake_case 鍵 `spec_refs`、`agents_consulted`）；`frozenStages` 等於檔；`humanPending={count:0,items:[]}`；`retryHistory.count=3`，`retryHistory.last` 等於 `date` 最晚那筆加上 `gate`；`rtmCoverage=null`；`source="FSM-STATE-e2e-alpha.yaml"` |
| 3 | 待人工 | `GET /engines/sdd?project=e2e-bravo` | `fsm.currentState="HUMAN_PENDING"`、`humanPending.count=1`、`items[0].entered_at="2026-10-15T08:00:00+00:00"`（原樣）；`retryHistory={count:0,last:null}` |
| 4 | 找不到、壞檔、非法名 | ①`?project=nope`；②`?project=e2e-broken`；③`?project=a%20b`；④`?project=..%2Fx` | ① 200、`available=true`、`fsm=null`、`reason="fsm_not_found"`、`projects` 照常；② 200、`fsm=null`、`reason="fsm_state_unreadable"`（檔名合法、取得到檔、內容讀不動→Bridge 422）；③④ **400**（`errors[0].field=project`）。**v1.5 覆寫**（§1.7.1、§1.10.4、§3.1.7 第 11 點；上列原文保留，與本註記不同處以本註記為準）：Console 不再以 regex 擋 `project`（規則改為 1～200 字元、不含控制字元；名稱交 Bridge 的淨化鏡像處理），所以 ③④ 不再是 400——③ `a%20b`（名稱 `a b` 合法、無此狀態檔）→ 200、`available=true`、`fsm=null`、`reason="fsm_not_found"`；④ `..%2Fx`（含 `/` 的名稱不可由 URL 定址，Bridge 回無 `reason` 的 404，Console 暫轉「找不到狀態檔」）→ 同為 200、`reason="fsm_not_found"`；① 的 `projects` 照第 1 列覆寫（三筆）；`errors[0].field=project` 的 400 只剩「超過 200 字元或含控制字元」（E2E-17 第 13 列⑤） |
| 5 | FSM 檔 ↔ API ↔ 畫面（NFR-OBS-01 補強） | 測試以自己的 YAML 解析器讀夾具檔（不經 Bridge）；登入前端、開任一專案的監控頁，在「AISDLC_SDD 引擎」卡選 `e2e-alpha` | 卡片顯示的狀態、Sprint、更新時間（本機時區）、待人工「無」、最近決策 5 筆（倒序；`from → to` 與 `reason`）與**檔案內容逐值一致**，也與第 2 列的 API 一致（檔、API、DOM 三者相等）；改選 `e2e-bravo` → 待人工顯示「等待人工確認」 |
| 6 | 檔案變動後下一輪輪詢跟上 | 頁面開著時改寫 `FSM-STATE-e2e-alpha.yaml`：`current_state` 換值、`updated_at` 更新、`decision_trace` 加一筆；等一個輪詢週期（≤ 35 秒，或以 Playwright 假時鐘快轉 30 秒） | 卡片更新為新狀態與新決策；沒有整頁重載；若恰好讀到寫一半的檔，卡片顯示「FSM 狀態檔無法讀取」、下一輪恢復，不得崩潰 |
| 7 | 引擎不可用：Bridge 不可達 | 停掉 18082；`GET /engines/sdd`；看卡片 | **200**（不是 502）；`available=false`、`reason="bridge_unreachable"`、`version=null`、`projects=[]`、`fsm=null`；卡片顯示「Engine Bridge 無法連線」；重啟 Bridge 後下一輪輪詢復原 |
| 8 | 引擎不可用：SDD 目錄無效（`sdd` 只當資訊，主控裁決 Q4） | 另起 Bridge 18083（`SDD_ROOT=<E2E_ROOT>/no-such-dir`，不存在），`sdd.engineUrl` 指向它；`GET /engines/sdd`；再直接 `GET http://127.0.0.1:18083/health/deep` 與 `/health` | `/engines/sdd`：200、`available=false`、`reason="sdd_unavailable"`、`version=null`、`projects=[]`、`fsm=null`，卡片顯示「找不到 AISDLC_SDD 目錄（請檢查 Bridge 的 SDD_ROOT）」；`/health/deep` 仍 **200**（`status=ok`），`checks.sdd={ok:false, latest:null, reason:"SDD_ROOT 不是目錄：no-such-dir"}`，頂層沒有 `reason`；`/health` 同為 200。**這個 Bridge 對探測環是健康的**（E2E-16 第 2 列用它驗「`sdd` 無效不拖累探測」） |
| 9 | 乾淨 clone 等價：有入口文件、沒有 `build/reports/fsm`（主控裁決 Q1） | 另起 Bridge 18084（`SDD_ROOT=<E2E_ROOT>/sdd-fresh`，只含 `AISDLC_SDD_v9.98/AISDLC_SDD_INIT.md`），`sdd.engineUrl` 指向它；`GET /engines/sdd`；直接 `GET :18084/health/deep`。Docker 全棧另跑：`AISDLC_SDD/<LATEST>/build/reports` 不存在的主機上 `docker compose --profile app up --wait` | `/engines/sdd`：`available=true`、`projects=[]`、`fsm=null`、`reason=null`（卡片「尚無 FSM 狀態檔」）；`/health/deep` **200**、`checks.sdd={ok:true, latest:"AISDLC_SDD_v9.98"}`；Docker 全棧 `engine-bridge` 與 `backend` 皆 healthy（這是 Q1 裁決的證明：入口文件判準讓乾淨 clone 的全棧起得來） |
| 10 | 權限 | 未認證、viewer、operator、admin 各 `GET /engines/sdd` | 未認證 401；其餘 200（VIEWER 以上） |
| 11 | 只讀 | 第 1～9 列前後對夾具目錄（遞迴）做 mtime 快照 | 完全相同：Bridge 與 console-api 都不新增、不改動任何檔案（第 6 列由測試自己改檔，快照在改檔之後取） |
| 12 | 真實 repo 根（**選跑**：只在 `AISDLC_SDD/<LATEST>/build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml` 存在的開發機） | `sdd.engineUrl` 還原為預設（Bridge 預設指向 repo 的 `AISDLC_SDD`），`GET /engines/sdd` | `projects` **包含** `AISDLC_SDD`（不得斷言清單等於：同目錄可能有 `test-<數字>` 殘留檔）；`?project=AISDLC_SDD` 的 `fsm` 與該 YAML 檔逐欄一致（`currentState`、`currentSprint`、`updatedAt`、`humanPending.count`、`retryHistory.count`）。**該檔被 git 忽略，CI 與乾淨 clone 沒有，本列不得列為必過**：有檔就跑，沒有就在報告明寫「未跑：檔不存在」，不得靜默略過 |

---

### E2E-16　v1.4 追加情境（W7；D-17、D-18、D-19）　〔API-SGN-05、API-AUTH-03、API-NTF-01、US-M-10、UI-KPI-08〕

**前置**：照 §5.0；各列各用新專案（名稱含 E2E-16 與列號）；第 2 列另起 Bridge 18085（環境同 §5.0.1，但 `PATH` 只剩一個空目錄 `<E2E_ROOT>/empty-bin`，使 `git` 解析不到）製造 503，並另起 18083 作對照（設定同 E2E-15 第 8 列：`SDD_ROOT` 指向不存在目錄，`/health/deep` 仍 200；E2E-15 的結束動作已停掉它，所以本情境要重起）；第 10 列只在 Docker 全棧跑。

| # | 情境 | 動作 | 預期 |
|---|------|------|------|
| 1 | 探測預設值（D-17） | 全新資料庫：admin `GET /settings/autoclaude` | `healthCheckPath.value` 與 `defaultValue` 都是 `/health/deep`；`impactNote` 逐字等於附錄 C.5。V11 對既有列的三種情形由 `SchemaMigrationIT` 驗（§0.8） |
| 2 | 探測打深度探針：503 計為失敗，`sdd` 無效不算（D-17；主控裁決 Q4） | ①另起 Bridge 18085（`BRIDGE_INSTANCE=e2e-nogit`，`PATH` 只剩空目錄，`git --version` 解析不到），`autoclaude.engineUrl` 指向它；等一個探測週期（≤ 35 秒；console-api 啟動時與 run 開始時會立即探測一次）；`GET /notifications/summary`、`GET …/metrics`；直接 `GET :18085/health` 與 `/health/deep`。②**對照**：把 `autoclaude.healthCheckPath` 暫設 `/health`，再等一個週期。③**`sdd` 無效不拖累探測**：`autoclaude.engineUrl` 改指 18083（設定同 E2E-15 第 8 列），把 `healthCheckPath` 還原成 `/health/deep`，等一個週期，`GET /notifications/summary`、`GET …/metrics`、`GET /engines/sdd` | ①18085 的 `/health` 回 **200**、`/health/deep` 回 **503**（`checks.git.ok=false`，頂層 `reason` 以 `git:` 開頭）；`bridgeConnected=false`；`metrics.agentAvailability.value` < 100（失敗樣本計入）。②改打 `/health` 後同一個 Bridge 被判成功，`bridgeConnected=true`——證明差別來自探測路徑。③18083 被判成功：`bridgeConnected=true`、`agentAvailability` 不因它下降，同時 `GET /engines/sdd` 為 `available=false`（SDD 卡顯示不可用）——證明 `sdd` 失敗只影響 SDD 卡。結束把 `healthCheckPath`、`autoclaude.engineUrl`、`sdd.engineUrl` 還原，停掉 18083～18085 |
| 3 | 待審批清單與計數同源（D-18） | 造出四種待簽草案各 ≥ 1：專案、目標、任務（`draft:true` 建立、不簽）、一筆匯入記錄停在 `PARSED`（路徑 B 解析後不簽）；再造不該計入的干擾：已簽專案、軟刪專案（其目標任務未軟刪）、`UPLOADED` 與 `REJECTED` 的匯入記錄；viewer 依序 `GET /signoffs/pending`、`GET /notifications/summary` | `counts` 各值等於人工數出的數量；`counts.total == summary.pendingSignoffs`；`items` 長度＝`min(total, 50)`、`createdAt` 升冪；欄位逐一正確：`PROJECT.parentId=null`、`GOAL.parentId＝專案 id`、`TASK.parentId＝目標 id`、**`IMPORT` 的 `projectId`／`projectName`／`parentId` 為 null** 且 `title`＝檔名（貼上文字為 `貼上文字`）；干擾列都不出現 |
| 4 | `limit` 與權限（D-18） | `?limit=2`、`?limit=0`、`?limit=201`、`?limit=abc`；未認證；viewer | `limit=2`：`items` 兩筆（最早的兩筆）、`counts.total` 不變；`0`、`201`、`abc` → 400（`errors[0].field=limit`）；未認證 401；viewer 200 |
| 5 | 儀表板卡與簽核後同步（D-18） | operator 開 Dashboard：看「待人工審批」卡的徽章與項目數、KPI「待審批草案數」；依序對卡片上 PROJECT、GOAL、TASK、IMPORT 各一筆按「審批」並確認 | 徽章＝KPI 數字＝`counts.total`；項目數＝`min(total, 50)`；簽完一筆後卡片、徽章、KPI 同步減 1（重取後，不必整頁重載）；各 kind 的連結導向 §4.5 G-10 列的路徑 |
| 6 | 通知鈴連結（D-18） | 在專案頁與 Dashboard 各開鈴面板 | 「待簽核草案」連結恆為 `/#pending-signoff`；「待審核項目」「未確認告警」在專案頁→該專案的 `/execute`、`/monitor`，在 Dashboard→`/projects`（已知限制，§4.6 G-G4） |
| 7 | refresh 輪替撤銷（D-19） | `POST /auth/login` 得 `RT1`；`POST /auth/refresh {RT1}` 得 `RT2`；再 `POST /auth/refresh {RT1}`；再 `POST /auth/refresh {RT2}` | 第 2 步 200（新的一對）；第 3 步 **401 `INVALID_REFRESH_TOKEN`**；第 4 步 200（`RT2` 有效，換出 `RT3`）；`RT1` 被當 Bearer 用仍是 401 `TOKEN_INVALID` |
| 8 | 登出撤銷（D-19） | login 得 `RT`；`POST /auth/logout {RT}`；再 `POST /auth/refresh {RT}`；`POST /auth/logout`：垃圾字串、已撤銷的 `RT`、一個 access token、缺 `refreshToken`；全程不帶 Authorization | logout **204**；之後 refresh → 401 `INVALID_REFRESH_TOKEN`；垃圾字串、已撤銷的 `RT`、access token 皆 **204**（不洩漏有效性）；缺 `refreshToken` → 400（`errors[0].field=refreshToken`）；不帶 Authorization 也能呼叫（免認證）；限流照常計（未認證以 IP 計） |
| 9 | 前端登出流程（D-19） | 瀏覽器登入後按「登出」，觀察網路請求；再用登出前記下的 refresh token 打 `POST /auth/refresh`；另把 logout 請求以網路攔截弄成失敗再登出一次 | 登出時瀏覽器送出一個 `POST /api/v1/auth/logout`（body 帶 `refreshToken`）；頁面導向 `/login`、session 清空，不論 logout 請求成敗；之後以該 refresh token 換新 → 401 |
| 10 | Redis 降級（D-19；Docker 全棧才跑） | 全棧起好後 `docker compose stop redis`；login → refresh（舊 token 再換→401）→ logout；`GET /actuator/health`；看 backend 日誌；`docker compose start redis` 後再做一輪 | Redis 停掉期間撤銷仍有效（第 7、8 列的行為不變）；`/actuator/health` 仍 `UP`、backend 容器維持 healthy；日誌有**一筆** WARN（進入降級）、恢復後**一筆** INFO；Redis 回來後新的撤銷寫進 Redis（`redis-cli --scan --pattern 'console:revoked-refresh:*'` 可見）。本機 e2e（`store=memory`）略過本列 |

---

### E2E-17　v1.5 追加情境（整合輪 115；D-115-01～16：SDD 迴圈；已與 ADR-016 對齊）　〔API-SGN-06、API-PRJ-07、API-PRJ-08、API-EXE-15、API-EXE-16、API-ENG-02、API-IMP-11、API-IMP-12、BR-27～BR-33、UI-SDD-01～03、NFR-OBS-01〕

**前置**：照 §5.0；本機 e2e 環境（Docker 全棧不載入 e2e profile，假伺服器不可達，所以只有第 26 列在全棧跑）；operator 寫、viewer 讀、admin 設參數。**本情境用真的 SDD CLI 與真的 FSM 狀態檔**（不是 E2E-15 那種手寫夾具）：測試自己扮演「SDD session」，以 SDD CLI 把 FSM 專案推進到 `HUMAN_PENDING`（動詞見 ADR-016 §4.2 與 SDD `tools/fsm_runtime/README.md`；環境 `SDD_STATE_DIR=<夾具根>/build/reports/fsm`、`SDD_PROJECT=<FSM 專案名>`；**不得手寫 YAML**，Rule 9 絕對禁令第 1 條）。共通後置斷言 A1～A5（§5.0.4）照樣適用。夾具的評估指令用裸 `pytest`，必須靠 §5.0.1「Bridge 啟動環境」第 1 點的 `PATH` 前置，才會解析到專案 `.venv`（此機的 `Get-Command pytest` 可能先命中 pyenv 的 shim；見 `docs/04_planning/AutoSDD_improving_115.md` §5.1 第 1 點）。

**Console 專案與 FSM 專案的命名**（D-115-14）：每個夾具對應一個 Console 專案，**專案名＝FSM 專案名**（有效 FSM 專案預設＝專案名，§1.10.5），所以夾具用 `--project <專案名>` 建 FSM 專案、Console 專案的 `executionPath`＝夾具根；名稱用 ASCII 安全字元（例 `e2e17-alpha`），只有 `names/` 夾具刻意用特殊字元。專案層的簽核（Phase 2 `POST /projects/{id}/signoff`）要在 execute 之前由測試補做（匯入記錄的 signoff 只涵蓋它建立的目標與任務，§1.10.8）。

**環境**（在 §5.0.1 之上追加）：

- Bridge（18081）設寫入權杖：環境變數 **`BRIDGE_SDD_WRITE_TOKEN`**＝`<E2E_SDD_TOKEN>`（佔位，測試自產 `secrets.token_hex(32)`，**≥ 32 字元**；少於 32 字元 Bridge 與 backend 啟動即失敗，那一項由 Bridge／backend 的單元測試守，不在 E2E）；console-api 以同一個環境變數名帶入（Spring 屬性 `console.bridge.sdd-write-token`，附錄 D.2）；`BRIDGE_ALLOWED_PATH_ROOTS` 含 `<E2E_ROOT>`；SDD 用 repo 的 LATEST（`SDD_ROOT` 預設）。**第二個 Bridge**（18086）同設定但**不設**權杖（第 1 列用；console-api 以 `autoclaude.engineUrl` 切換指向，結束動作還原）。
- 替身（§5.0.3）：`MOCK_CLAUDE_DELAY` 設 ≥ 3 秒，讓測試能觀察到 `AUTOCLAUDE_DELEGATED`（第 15、20、21、25 列）；`model.apiKey` 必須是空（§5.0.2）。
- 稽核與 FSM 讀取：測試用獨立的 YAML 讀取（不經被測 API）讀 `FSM-STATE-*.yaml`；所有「等 FSM 回到某狀態」的斷言一律**輪詢**（每 ≥ 1 秒、上限 30 秒），因為終態事件到 FSM 回 `IMPLEMENTATION` 之間約有 0.1 秒視窗（§3.1.6 第 5 點）。

**SDD 夾具**（QA 於情境前建立，全部在 `<E2E_ROOT>/sdd-e2e/` 之下；FSM 狀態只經 CLI 產生）：

- `alpha/`：Console 專案 P1（名稱 `e2e17-alpha`，`executionPath`＝夾具根）；FSM 專案 `e2e17-alpha`。`docs/03_testing/contracts/TCS-Alpha-<日期>.md` 是**成功夾具**：檔頭 `**scenario**: greenfield`（S-12；測試類型欄會出現 `Integration` 字樣，沒有這個欄位時啟發式會誤判成 integration）與 `**spec-format-version**: 1.0`；2 個 AC、4 個 AT（`AT-001-1-1`、`AT-001-1-2` 屬 `AC-001-1`；`AT-001-2-1`、`AT-001-2-E-1` 屬 `AC-001-2`——後者是 ADR-016 §8.1 規定的邊界／錯誤 AT 命名；測試類型欄 `Unit` 與 `Integration` 各兩個 ⇒ 重試上限 5）；每個 AT 的 Gherkin `Then` 引號字面值取替身必然回放的 `[AT_OK_<序號>]`（替身只回放 prompt 內的 `[KEYWORD]`，§5.0.3）；`tests/` 預置會通過的測試檔，測試函式名含 AT 的底線化 token（例 `test_AT_001_1_1_basic`、`test_AT_001_2_E_1_basic`），使評估指令 `pytest tests -k "AT_001_1_1" -q` 不依賴 AI；`.gitignore` 含 `build/reports/`。
- `alpha-fail/`：同形的**失敗夾具**，Console 專案 P3、FSM 專案 `e2e17-alpha-fail`——AT 的測試類型欄寫 `E2E`（⇒ 重試上限 2，三個 attempt 即升級），Gherkin `Then` 引號字面值取替身**必不輸出**的詞 `NEVER_PRINTED_<序號>`（沒有方括號，替身不會回放），預置測試檔仍會通過（失敗只來自驗收 regex）。
- `multi/`：同一個 `build/reports/fsm/` 下兩個 FSM 專案——`m-alpha`（停在 `INIT`，未凍結）、`m-zeta`（已凍結：推進到 `HUMAN_PENDING` 後以 CLI 凍結）；規格目錄放兩份 TCS（`TCS-MAlpha-….md`、`TCS-MZeta-….md`，各 1 個 AT）。
- `two-tcs/`：同一個規格目錄放兩份官方命名的 TCS（`TCS-One-….md`、`TCS-Two-….md`，各 1～2 個 AT；FSM 專案 `e2e17-two` 已凍結）。
- `unmapped/`：TCS 的 Gherkin 區塊有一個標頭 `# AT-009-1-1`，但 §1 的 AC→AT 映射表**沒有**這一列；另有一列 §1 映射寫成舊編號 `AT-14-2-1`（首段非三位）；兩者都沒被編成 step（FSM 專案 `e2e17-unmapped` 已凍結）。
- `edit/`：已凍結的單一 TCS（1 個 AT；FSM 專案 `e2e17-edit`），供第 12 列改檔用。
- `names/`：兩個 FSM 專案——`訂單系統 v2`（含 CJK 與空白；檔名不變）與 `a:b`（`sanitize_component` 把 `:` 換成 `_`，所以檔案是 `FSM-STATE-a_b.yaml`，檔內 `fsm_state.project="a:b"`），各有同名的 Console 專案；皆已推進並凍結。
- `notcs/`、`expect/`：各一個停在 `HUMAN_PENDING` 的 FSM 專案（`e2e17-notcs`、`e2e17-expect`），規格目錄分別只有一份非 TCS 命名的 `README.md`、一份 TCS，供第 6 列用。
- `cancel/`、`reclaim/`、`foreign/`、`mixed/`：結構同 `alpha/`（FSM 專案 `e2e17-cancel`、`e2e17-reclaim`、`e2e17-foreign`、`e2e17-mixed`；`foreign/` 只推進到 `IMPLEMENTATION`，其餘已凍結並匯入簽核），供第 20～22、25 列用。
- **摘要比對**：測試以獨立實作的雜湊（**換行正規化後的 UTF-8 文字**的 sha256，演算法見 §3.1.4 (d)）計算規格檔摘要，與 FSM 檔內值逐值比對；另備一份**同內容、CRLF 換行**的規格檔變體（F-6 的 E2E 面：不得因換行不同而假性不符）。

| # | 情境 | 動作 | 預期 |
|---|------|------|------|
| 1 | 寫入面停用：Bridge 沒設權杖（BR-33） | 對 18086 直接 `POST /sdd/fsm/e2e17-alpha:freeze`（合法 body，帶任意 `X-Bridge-Token`）；對 18086 `POST /autoclaude/runs` 帶 `sdd`；對照 `GET /sdd/fsm/e2e17-alpha?root=…`；再對 18086 送一個**不含** `sdd` 的 `POST /autoclaude/runs`；前後對 `alpha/build/reports/fsm` 做 mtime 快照 | 兩個寫入皆 **503** `sdd_write_disabled`；`GET` 照常 200（唯讀不需權杖）；不含 `sdd` 的 run 照舊 201（不需要權杖）；FSM 檔 mtime 不變；帶 `sdd` 的請求沒有建立任何 run 目錄 |
| 2 | 權杖缺或錯（BR-33） | 對 18081 同上兩個寫入：①不帶 `X-Bridge-Token`②帶錯值（`e2e17-alpha` 此時已在 `HUMAN_PENDING`） | 皆 **403** `sdd_write_forbidden`（缺與錯同一個 reason）；回應與 Bridge 日誌**不含**權杖值；FSM 檔不變；Bridge 稽核檔有拒絕事件（`event=sdd_write`，`result` 為拒絕，事件內沒有權杖） |
| 3 | 前置狀態不符（BR-27） | 另建 FSM 專案 `e2e17-init` 停在 `INIT`；帶正確權杖 `:freeze`（`docs` 合法） | **409** `fsm_state_conflict`，`detail.current_state="INIT"`、`detail.expected_state="HUMAN_PENDING"`；FSM 檔不變 |
| 4 | 多專案狀態共處只認指定者（G-02；F-2 的 E2E 面） | `multi/`，Bridge `POST /sdd/compile`：①`{spec_dir, spec_file:"TCS-MAlpha-….md", fsm_project:"m-alpha"}`②`{spec_dir, spec_file:"TCS-MZeta-….md", fsm_project:"m-zeta"}`③`{spec_dir, spec_file:"TCS-MAlpha-….md"}`（不帶 `fsm_project`）④`fsm_project:"nope"` | ① **422** `spec_not_frozen`（**不得**因 `m-zeta` 已凍結而放行）；② 200，`fsm_project="m-zeta"`、`frozen_digest="verified"`；③ 422 `spec_not_frozen`，`detail` 說明狀態檔不唯一；④ 422 `spec_not_frozen`，`detail` 列出現有專案鍵（`m-alpha`、`m-zeta`） |
| 5 | 核准凍結：人工閘（C2；BR-27、API-SGN-06、API-PRJ-07） | P1（`e2e17-alpha`；`sddProject` 為 NULL）；`e2e17-alpha` 已推進到 `HUMAN_PENDING`；operator `POST /projects/{P1}/sdd/freeze` `{reason:"E2E 核准", docs:["docs/03_testing/contracts/TCS-Alpha-….md"]}`（不帶 `binding`，沒有這個欄位） | **200**，`fsm.currentState="SPEC_FROZEN"`、`fsm.fsmProject="e2e17-alpha"`；`fsm.frozenStages` 末筆：`stage="Stage-1"`、`spec_docs` 含該檔、`spec_doc_digests[<相對路徑>]`＝測試獨立計算者（`sha256:<64 位小寫 hex>`）、`approved_by="operator"`；FSM 檔 `decision_trace` 末筆 `trigger=spec_frozen`、`to=SPEC_FROZEN`、`reason="console-freeze approver=operator; reason=E2E 核准"`、`spec_refs` 為該檔；Bridge 稽核檔 `event=sdd_write`（`verb=spec-frozen`、`approver=operator`、`result` 成功、與請求同一個 `trace_id`、無權杖）；`audit_log` 一列 `action=project.sdd.freeze`、`entity=project:<P1>`、`subject=operator`；`GET /projects/{P1}`：`sddProject="e2e17-alpha"`（第 5 項寫回標準鍵）、`sddSpecDir`／`sddSpecFile` 仍為 null；PG `projects.sdd_project` 相等 |
| 6 | 凍結的不可重做、權限與驗證（API-SGN-06） | ①P1 再 `POST …/sdd/freeze`；②viewer；③未認證；④另建專案 P1x（無 `sddSpecFile`）不帶 `docs`；⑤`reason` 全空白；⑥`notcs/` 專案（`HUMAN_PENDING`）`docs:["README.md"]`；⑦`expect/` 專案（`HUMAN_PENDING`）帶 `expectedDigests`（鍵＝該 TCS，值為錯的摘要）；⑧`docs:["../x.md"]`；⑨`reason` 含換行 | ① **409** `sdd_fsm_state_conflict`，`details.currentState="SPEC_FROZEN"`、`expectedState="HUMAN_PENDING"`；② **403** `ACCESS_DENIED`；③ **401**；④ **400**（`errors[0].field=docs`）；⑤ **400**（`errors[0].field=reason`）；⑥ **422** `引擎拒絕此請求`，`details.violations[0]` 為 `{field:"docs", rule:"missing_tcs"}`；⑦ **409** `sdd_spec_digest_changed`，`details.pair="expected_vs_file"`；⑧ **400**（`errors[0].field=docs`）；⑨ **400**（`errors[0].field=reason`）；⑥⑦ 之後各自的 FSM 檔不變（仍 `HUMAN_PENDING`）；①～⑨ 之後 P1 的 FSM 檔不再變動 |
| 7 | 綁定唯一性與編輯（D-115-14；API-PRJ-08） | ①另建專案 P1b（名稱 `e2e17-alpha`、`executionPath` 同 `alpha/`；`sddProject` 為 NULL），operator 對它 `POST …/sdd/freeze`（合法 body）；②`PUT /projects/{P1b}/sdd-binding {sddProject:"e2e17-alpha"}`；③同一個 PUT 改 `{sddProject:"other"}`；④`{sddProject:null}`；⑤viewer 做②；⑥`{sddProject:"<101 字元>"}`；⑦`{sddProject:"  "}` | ① **409** `sdd_binding_conflict`，`details={cause:"already_bound_elsewhere", sddProject:"e2e17-alpha", holderProjectId:<P1>}`，且 **Bridge 沒收到任何寫入呼叫**（稽核檔 `sdd_write` 筆數不變、FSM 檔不變）；② 409 同 ①；③ 200，`sddProject="other"`；④ 200，`sddProject=null`；⑤ **403**；⑥⑦ **400**（`errors[0].field=sddProject`）；`audit_log` 有 `action=project.sdd.bind` 的列（③④各一） |
| 8 | 路徑 A 匯入並併入既有專案（G-08、G-07；F-1 的 E2E 面；API-IMP-12） | operator `POST /import/text`（任意文字）→ `parse` `{executionPath:"<alpha 根>", specDir:"<alpha 根>/docs/03_testing/contracts", specFile:"TCS-Alpha-….md", targetProjectId:<P1>}`；`GET` 詳情；`signoff`；`confirm`；再以 Phase 2 `POST /projects/{P1}/signoff` 簽核專案 | `parse` 200：`path=SDD`；`parsedResult` 恰 4 個任務；`specFormatVersion="1.0"`、`sddProject="e2e17-alpha"`、`sddSpecDir`＝規格目錄、`sddSpecFile`＝TCS 的**絕對路徑**（＝Bridge 回應的 `spec_path`）；`warnings=[]`；任務的 `passCriteriaSpec.stepId` 依序為 `sdd-greenfield-at-001-1-1`、`…-001-1-2`、`…-001-2-1`、`…-001-2-e-1`；`maxRetries=5`；`passCriteriaSpec.maintainContext` 依序為 `false`、`true`、`false`、`true`（每個 AC 的第一個任務 `false`）；各任務 `passCriteriaSpec.specDigest` 全部相等且＝第 5 列的凍結摘要。`confirm` → **201**，回傳的專案 `id=<P1>`（**沒有建立新專案**）、`sddSpecDir`／`sddSpecFile` 與 PG `projects.sdd_*` 相等、`sddProject` 不變；匯入記錄 `projectId=<P1>`、`status=IMPORTED`；P1 的名稱與 `executionPath` 不變；新目標的 `sortOrder` 接在既有目標之後 |
| 9 | 併入與匯入的錯誤（D-115-14） | ①`parse` 帶不存在（或已軟刪除）的 `targetProjectId`；②`parse` 帶 `targetProjectId=<P1>` 但 `executionPath` 填 `<別的根>`；③不帶 `targetProjectId`、規格根＝`<alpha 根>`：parse 後 signoff、confirm；④帶 `targetProjectId=<P1>` parse 並 signoff 後，先 `PUT /projects/{P1}/sdd-binding {sddProject:"other"}`，再 confirm（之後把 P1 改回 `e2e17-alpha`） | ① **404**（訊息 `專案不存在或已刪除：<id>`，無 reason）；② **409** `sdd_binding_conflict`，`details={cause:"request_differs_from_target", field:"executionPath"}`；③ parse 200，但 confirm → **409** `sdd_binding_conflict`（`cause="already_bound_elsewhere"`，同 `(executionPath, e2e17-alpha)` 已被 P1 綁定），**沒有建立新專案**；④ confirm → **409** `sdd_binding_conflict`（`cause="target_bound_differently"`），P1 的目標與任務數不變 |
| 10 | `spec_file` 選檔（S-04） | `two-tcs/`，`parse`：①只給 `specDir`②加 `specFile:"TCS-One-….md"`③加 `specFile:"../escape.md"`④加 `specFile:"nope.md"`⑤只給 `specFile`、不給 `specDir`（且無 `targetProjectId`） | ① **422** `SDD 規格檢查未通過`，`details.bridgeReason="spec_ambiguous"`，`detail` 列出兩個符合條件的檔名；② 200，任務只含 `TCS-One` 的 AT，`sddSpecFile` 是 `TCS-One-….md` 的絕對路徑；③ **422** `SDD 規格檢查未通過`，`details.bridgeReason="sanitization_failed"`；④ **422** `SDD 規格檢查未通過`，`details.bridgeReason="spec_not_found"`；⑤ **400**（`errors[0].field=specFile`） |
| 11 | 未映射 AT 出聲（S-03；D-115-16） | `unmapped/`，`parse`；另直接打 Bridge `POST /sdd/compile`，並對同一規格跑 `sdd_compile` CLI；再對照「照模板填 §4 的 `AT-{NNN}-E-n` 邊界表」的規格 | `parse` 200，`warnings` 含一筆 `code="at_unmapped"`、`detail` 含 `AT-009-1-1` 與 `AT-14-2-1`、`location="specDir"`，`parsedResult` 的任務不含它們；Bridge 回應 `unmapped_at_ids=["AT-14-2-1","AT-009-1-1"]`（依首次出現順序：§1 映射列在前、Gherkin 標頭在後；仍 200）；`sdd_compile` CLI **rc 6** 且**不寫輸出檔**；§4 邊界表照模板填的規格＝`unmapped_at_ids=[]`、不出聲 |
| 12 | 凍結後改檔 → 編譯 fail-closed（G-06；F-3 的 E2E 面） | `edit/`：改動 TCS 的一個字元後 ①Bridge `POST /sdd/compile`②Console `parse`（明示 `specDir`）③Console `parse`（不帶 `specDir`，以 `executionPath` 探測）；再還原內容重打 ② | ① **409** `spec_digest_changed`，`detail.pair="frozen_vs_file"`；② **422** `SDD 規格檢查未通過`，`details.bridgeReason="spec_digest_changed"`；③ 同 ②，**且不退回 LLM 路徑**（探測模式 fail-closed：`parsePath` 不是 `LLM`、沒有任何模型呼叫；ADR-016 §6.3）；還原後 ② 回 200 |
| 13 | 專案名規則與原名等價（S-10；F-8 的 E2E 面） | `names/`：①Bridge `GET /sdd/fsm?root=<names 根>`②`GET /sdd/fsm/%E8%A8%82%E5%96%AE%E7%B3%BB%E7%B5%B1%20v2?root=…`③`GET /sdd/fsm/a%3Ab?root=…` 與 `GET /sdd/fsm/a_b?root=…`④Console 專案 `訂單系統 v2`：`GET /engines/sdd?projectId=<該專案>`⑤`GET /engines/sdd?project=<201 字元>`、`?project=a%00b` | ① `projects` 含兩個專案（`訂單系統 v2` 與 `a_b`，皆不在 `errors`）；② 200，`fsm_project="訂單系統 v2"`；③ 兩者都 200 且指向同一個檔：`project="a:b"`（檔內原名）、`fsm_project="a_b"`（原名與標準鍵等價）；④ 200，`fsm.fsmProject="訂單系統 v2"`；⑤ 兩者皆 **400**（`errors[0].field=project`） |
| 14 | 專案根與 `projectId`（API-ENG-02；BR-28） | ①`GET /engines/sdd?projectId=<P1>`②`?projectId=<不存在的 uuid>`③`?projectId=abc`④viewer 讀①⑤另建一個 `executionPath` 指向 allowlist 之外目錄的專案，`?projectId=` | ① 200，`projects` 只含**該專案根**下的 FSM 專案（含 `e2e17-alpha`），`fsm.fsmProject="e2e17-alpha"`（預設取有效值），`fsm.escalationHistory=[]`、`fsm.escalationProvenance=null`、`fsm.recovery` 缺席，`fsm.phase={name:"FROZEN",order:4,blocking:false,observation:false}`（W4 dogfood 接線後；之前為 null）；② **404**（無 reason）；③ **400**；④ 200；⑤ 200，`available=true`、`reason="sdd_root_rejected"`、`projects=[]`、`fsm=null` |
| 15 | SDD 批次成功路徑（C3、C4；BR-30、BR-31；API-EXE-15） | P1 全範圍 `POST execute`；viewer 每 ≥ 2 秒輪詢 `GET run`，並同時讀 FSM 檔（`GET /sdd/fsm/e2e17-alpha?root=…` 與測試自己的 YAML 解析），直到 run 終態，再輪詢到 FSM 離開 `AUTOCLAUDE_DELEGATED`（≤ 30 秒），記下 FSM 狀態序列 | 201，**沒有 `warnings`**；`dag.nodes[].stepId` 與 playbook 的 `step_id` 都是 `sdd-greenfield-at-…`（不是 `G1-T1`）；執行中 FSM `current_state="AUTOCLAUDE_DELEGATED"`（至少被觀測到一次）且 `autoclaude_delegated_tracking.playbook_ref="run:<runId>"`；run `COMPLETED` 後 FSM `current_state="IMPLEMENTATION"`；FSM `decision_trace` 依序含 ①`SPEC_FROZEN→TEST_CONTRACT_NEGOTIATED`（reason `console-signoff approver=<匯入記錄的 signedOffBy>; run=<runId>`）②`TEST_CONTRACT_NEGOTIATED→IMPLEMENTATION`（reason `console-signoff approver=<…>; oracle=<TCS 相對路徑>@sha256:<凍結摘要>; basis=import-draft-signoff; r9.20.3=not-satisfied`）③`IMPLEMENTATION→AUTOCLAUDE_DELEGATED`（reason `console-run run=<runId> START`）④`AUTOCLAUDE_DELEGATED→IMPLEMENTATION`（reason `console-run run=<runId> COMPLETED`）；run 工作區 `playbook.yaml` 的 `workflow_type="aisdlc_sdd"`、`workflow_path`＝**TCS 檔案的 realpath**；引擎子行程環境**只有** `SDD_PROJECT=e2e17-alpha`（沒有 `SDD_STATE_DIR`、沒有任何 `BRIDGE_*`）；`run.json` 的 `env_keys` 不含權杖名；run 目錄內任何檔案與引擎日誌**搜不到權杖值**（BR-33） |
| 16 | 追溯覆蓋（C5；BR-32；API-EXE-16） | 第 15 列的 run：`GET /executions/{runId}/rtm`；對照 Bridge `GET /autoclaude/runs/{id}/rtm` 與引擎寫的 `RTM-COVERAGE-*.yaml`；另對一個進行中（`RUNNING` 或 `PAUSED`）的批次再取一次 | 200；`scenario="greenfield"`、`at={passed:4,total:4,unmapped:0,pct:100.0}`、`ac={covered:2,total:2,pct:100.0}`（`AT-001-2-E-1` 歸 `AC-001-2`）、`failedAtIds=[]`、`weakRegexAtIds=[]`、`unmappedAtIds=[]`、`fullyCovered=true`、`advisory=true`；`specDigest`＝第 5 列的凍結摘要；三處（YAML、Bridge、Console）逐值相等；進行中批次 → **404** `rtm_not_found` |
| 17 | 四源對拍（NFR-OBS-01 補強；C4） | 第 15、16 列結束後，依下方〈四源對拍表〉逐列比對（測試用獨立的 YAML／SQL 讀取，不經任何被測 API；FSM 側先輪詢到離開委派態） | 每列四源逐值相等；任一列不等即缺陷 |
| 18 | 凍結後改檔 → 執行 409（G-06；BR-30） | 第 15 列之後，在 `alpha/` 規格檔末尾加一行文字（不碰 FSM）；P1 再 `POST execute`；之後把檔案還原 | **409** `sdd_spec_digest_changed`，`details.pair="frozen_vs_file"`，含 `doc`、`frozenDigest`、`currentDigest`，且 `currentDigest≠frozenDigest`；**沒有新的 `execution_runs` 列**（已補償刪除）；FSM `current_state` 仍為 `IMPLEMENTATION`；還原後再 execute 回 201 |
| 19 | 失敗路徑與人工恢復（C4；BR-31；D-115-15；替身） | `alpha-fail/`：依第 5、8 列的步驟建立、凍結、匯入（併入 P3）並簽核專案；`POST execute`；等終態（60 秒）；再 execute；之後測試扮演 SDD session 執行真 CLI `resume-from-escalation --to IMPLEMENTATION --project e2e17-alpha-fail --reason "E2E 人工恢復"`，再 `GET /engines/sdd?projectId=<P3>`，再 execute | run `FAILED`，`reason` 以 `引擎升級（ESCALATION）` 開頭；FSM `current_state="ESCALATION"`、`escalation_provenance.source="autoclaude_delegated_failed"`、`escalation_history[-1].resolved_at` 為空；`GET /engines/sdd?projectId=<P3>`：`fsm.escalationHistory` 末筆與 FSM 檔逐值相同、`fsm.escalationProvenance.source` 同、`fsm.phase={name:"BLOCKED",order:0,blocking:true,observation:false}`（W4 接線後）、`fsm.recovery.target="IMPLEMENTATION"` 且 `powershell`／`posix` 兩段都含 `resume-from-escalation`、`--to IMPLEMENTATION` 與 `<夾具根>` 下的 `build/reports/fsm`；專案詳情「SDD 治理」區顯示紅色阻塞橫幅、ESCALATION 區塊與可複製的恢復指令（§4.7.3）；`GET /executions/{runId}/rtm` → **404** `rtm_not_found`；恢復前再 execute → **409** `sdd_fsm_state_conflict`（`details.currentState="ESCALATION"`）；CLI rc 0 後：FSM `IMPLEMENTATION`、`escalation_history[-1].resolved_at` 有值、**`escalationProvenance` 仍在**（恢復後不清除），畫面**不再**顯示未解的升級區塊（判斷式用 `currentState`，§4.7.3），再 execute → **201**（下一個批次可直接啟動） |
| 20 | 取消交還控制權（D-115-15；BR-31） | `cancel/`：P 全範圍 `POST execute`（`MOCK_CLAUDE_DELAY` ≥ 3 秒）；進行中 `POST cancel`；等 `CANCELLED`，輪詢到 FSM 離開委派態；再對 P `POST execute` | run `CANCELLED`；FSM `current_state="IMPLEMENTATION"`，`decision_trace` 末筆 `AUTOCLAUDE_DELEGATED→IMPLEMENTATION`、reason `console-run run=<runId> CANCELLED`；第二次 execute → **201**（Bridge 重新 `delegate-enter`，`playbook_ref="run:<新 runId>"`） |
| 21 | 回收點與外來委派（D-115-15；§3.1.6 第 3 點） | ①`reclaim/`：P `POST execute`（`MOCK_CLAUDE_DELAY` ≥ 3 秒）後，由測試在外部殺掉引擎行程 → run `FAILED`（引擎異常結束；FSM 不動，仍 `AUTOCLAUDE_DELEGATED`）；再對 P `POST execute`②`foreign/`：測試以真 CLI 在 `IMPLEMENTATION` 執行 `delegate-enter`（不帶 `--playbook-ref`），再對 P `POST execute` | ① 第二次 execute → **201**；FSM `decision_trace` 依序含 `AUTOCLAUDE_DELEGATED→IMPLEMENTATION`（reason `console-run run=<舊 id> RECLAIMED old_status=FAILED by=<新 id>`）與 `IMPLEMENTATION→AUTOCLAUDE_DELEGATED`（reason `console-run run=<新 id> START`）；Bridge 稽核記一筆回收（含舊 run id 與舊終態）；② **409** `sdd_fsm_state_conflict`，`details.currentState="AUTOCLAUDE_DELEGATED"`、`details.cause="foreign_delegation"`；FSM 檔不變（Bridge 不碰外來委派） |
| 22 | 混合批次與資格（G-01；API-EXE-15） | `mixed/`：專案 P5 依第 5、8 列建立、凍結、匯入並簽核專案，再手動新增一個一般任務（Phase 2）；`POST execute`（`scope.mode=ALL`）。另對只有手動任務、但已被第 5 列寫回 `sddProject` 的專案 P6 `POST execute` | P5：201，`warnings[0]={code:"sdd_governance_inactive", cause:"mixed_scope", detail:…}`；`dag` 的 `stepId` 是 `G<g>-T<t>`；FSM 檔不變；批次照常跑完、沒有追溯報告。P6：201 且**沒有** `warnings`（沒有 SDD 來源任務），步驟 id 為 `G1-T1`…。（`token_not_configured`、`spec_mismatch`、`duplicate_step_id` 與 `sdd_frozen_digest_absent` 由 `RunLauncher` 的整合測試涵蓋，E2E 不必另起實例） |
| 23 | 權限與錯誤形狀（API-EXE-16、API-ENG-02、API-SGN-06、API-PRJ-08） | rtm、engines、freeze、sdd-binding 端點：未認證、viewer、operator；freeze 的失敗回應 | 未認證 401；viewer 對 rtm、engines 為 200，對 freeze、sdd-binding 為 403；每個非 2xx 都是 `ApiError` 封包且 `traceId` 等於 `X-Trace-Id`（A2）；任何回應與日誌都不含權杖值（A5 的延伸） |
| 24 | 唯讀不變與 CLI 窄寫（A1；BR-33；F-4） | 對 `GET` 類端點（`/sdd/fsm*`、`/engines/sdd`、`/autoclaude/runs/{id}/rtm`）前後對所有 FSM 狀態目錄做 mtime 快照；另跑 Bridge 原始碼掃描 | `GET` 前後 FSM 檔的 mtime 與大小完全相同；`engine-bridge/app/**/*.py` 沒有任何以寫入模式開啟 `FSM-STATE` 檔的呼叫（F-4）；CLI 呼叫處只使用白名單動詞 |
| 25 | SDD run 的 `resume` 重驗與權杖（ADR-016 §10.1 最後一列；D-115-18） | `cancel/` 以外另一個已匯入簽核的專案：`POST execute`（`MOCK_CLAUDE_DELAY` ≥ 3 秒）→ `POST pause` 等 `PAUSED`；**直接對 Bridge** 打該 run 的 `POST /autoclaude/runs/{id}:resume` 與 `…/restore`，各做①不帶 `X-Bridge-Token`②帶錯值；在規格檔末尾加一行；`POST resume`；還原檔案再 `POST resume` | PAUSED 期間 FSM 仍 `AUTOCLAUDE_DELEGATED`（`playbook_ref` 指本 run）；直打 Bridge 的①②共四次皆 **403** `sdd_write_forbidden`，run 仍 `PAUSED`、沒有 spawn、FSM 檔不變（Bridge 沒設權杖的 503 由 Bridge pytest 守）；第一次 resume → **409** `sdd_spec_digest_changed`（`details.pair="frozen_vs_file"`），run 維持 `PAUSED`、沒有 spawn；還原後 resume → 200（`RUNNING`），FSM 不變、沿用同一個委派（console-api 有附權杖，所以這一步成功本身就是權杖附上的證據） |
| 26 | Docker 全棧（只在 Docker 全棧跑） | 全棧起好後（專案根在可寫掛載、SDD 唯讀掛載、權杖兩端同值且 ≥ 32 字元）：第 5、15、19 列各做一次簡化版；再把專案根換成唯讀掛載重打第 5 列 | `:freeze` 與批次同步成功，FSM 檔寫在專案根，`/sdd` 之下沒有新增 `__pycache__` 或遙測檔（SDD 版本目錄內 `governance/rules/*.yaml` 的內容雜湊前後相同）；權杖只存在 backend 與 Bridge 的環境，不在引擎子行程環境；專案根唯讀時 `:freeze` 回 **502**（Bridge 502 `sdd_cli_failed`）且 FSM 不變 |

**四源對拍表**（第 17 列；每列四源逐值相等；①②③④ 的順序即 NFR-OBS-01 的四源）：

| 比對項 | ① FSM 狀態檔（YAML） | ② Bridge | ③ Console API | ④ PG |
|--------|----------------------|----------|---------------|------|
| 目前狀態（跨狀態機語意對照） | `fsm_state.current_state` | `GET /sdd/fsm/{p}?root=` 的 `current_state` | `GET /engines/sdd?projectId=` 的 `fsm.currentState` | `execution_runs.status` 依對照：`COMPLETED`、`CANCELLED`⇄`IMPLEMENTATION`（FSM 已輪詢離開委派態）；引擎升級型 `FAILED`⇄`ESCALATION`；進行中、以及額度停機／異常結束／孤兒的 `FAILED`⇄`AUTOCLAUDE_DELEGATED`（不動） |
| 凍結階段與文件 | `frozen_stages[-1].stage`、`spec_docs` | 同鍵 | `fsm.frozenStages[-1].stage`、`spec_docs` | `projects.sdd_spec_dir`／`sdd_spec_file`（絕對路徑）換算出的相對 `executionPath` 路徑＝`spec_docs` 的一項 |
| 凍結摘要 | `frozen_stages[-1].spec_doc_digests`（`{<相對路徑>: "sha256:…"}`） | 同 | `fsm.frozenStages[-1]` 原樣 | `tasks.pass_criteria_spec->>'specDigest'`（匯入後的全部任務）＝規格檔現摘要（凍結後未改檔時） |
| 凍結稽核 | `decision_trace` 凍結那一筆的 `reason`（`console-freeze approver=…; reason=…`）與 `ts`、`frozen_stages[-1].approved_by` | 同 | `fsm.decisionTrace`（尾 5 筆內）、`fsm.frozenStages[-1].approved_by` | `audit_log` 的 `action=project.sdd.freeze` 一列：`subject`＝approver、`occurred_at` 與 `ts` 相差數秒內 |
| 綁定 | — | — | `ProjectDetailResponse` 的 `sddProject`／`sddSpecDir`／`sddSpecFile` | `projects.sdd_project`／`sdd_spec_dir`／`sdd_spec_file` |
| 委派追蹤 | `autoclaude_delegated_tracking.playbook_ref`（執行中＝`run:<runId>`） | — | `GET /executions/{runId}` 的 `id` | `execution_runs.id` |

### 跨專案一致性對拍測試清單（v1.5；§4.3-F；放 Bridge tests，不碰根層 `tools/tests`）

ADR-XPLAT-010 §2.1 要求跨專案一致性斷言放在整合層；本輪放 `AgentConsole/engine-bridge/tests/`（建議檔 `test_sdd_integration_parity.py`）——Bridge 是唯一同時看得到兩個引擎的元件，也避開根層守衛線的重釘稅。一律用**真的 SDD CLI（子行程）與真的 adapter（行程內）**，狀態目錄在暫存目錄，不碰 repo 真實的 `build/reports`。

| # | 名稱 | 斷言 |
|---|------|------|
| F-1 | 欄位對拍（G-08） | 同一份 TCS：Bridge `POST /sdd/compile` 的 `tasks[]` 與 `sdd_compile` CLI 的輸出，逐任務 `step_id`、`name`、`expected_output_regex`、`evaluator_command`、`max_retries`、`maintain_context`、`spec_digest`、`weak_regex` 相等（`prompt` 不比）。backend 的欄位映射（§3.3.2）另由 `ImportParserTest` 對本契約的表釘住，兩段合起來構成 G-08 的對拍 |
| F-2 | 只認指定者（G-02） | 同一狀態目錄 `m-alpha`（`INIT`）與 `m-zeta`（`SPEC_FROZEN`）：`fsm_project=m-alpha` → `spec_not_frozen`；`m-zeta` → 通過；未指認 → `spec_not_frozen`（狀態檔不唯一）；只有單一狀態檔的目錄不需指認；原名反查（`fsm_project="a:b"` 找到 `FSM-STATE-a_b.yaml`）；找不到時**不再往上層目錄找** |
| F-3 | 凍結後改檔（G-06） | 真 CLI 凍結（含 `spec_doc_digests`）→ 改 TCS → `/sdd/compile` 得 **409** `spec_digest_changed`（`pair=frozen_vs_file`）、`POST /autoclaude/runs` 預檢得 409 `spec_digest_changed`；規格檔不在凍結清單 → 422 `spec_not_frozen`；舊狀態檔（無摘要）→ 放行、`frozen_digest="absent"` 並出聲一次（行為同 v1.4） |
| F-4 | 只經 CLI（A1；D-115-01） | 掃描 `engine-bridge/app/**/*.py`：出現字串 `FSM-STATE` 的模組不得含寫入形態呼叫（`open(…, "w"／"a"／"x")`、`write_text`／`write_bytes`、`os.replace`／`rename`、`shutil` 複製移動、`unlink`）；唯一提到 `tools.fsm_runtime.fsm_runtime` 的子行程呼叫處受 `ALLOWED_VERBS` 限制；掃描器自帶一個故意違規的樣本，證明它會紅 |
| F-5 | `phase` 表對拍（G-13） | T-G 純函式的表與 SDD LATEST 的集合一致：`OBSERVATION_STATES`＝表中 `observation=true` 的狀態集；`FSMRuntime._BLOCKING_STATES`＝`blocking=true` 的集合；`_HAPPY_PATH` 的每個鍵都有對映（日後新增狀態未對映 ⇒ 紅）；主路徑 `order` 沿 `_HAPPY_PATH` 單調不減（讀 SDD 檔以 `importlib` 依路徑載入，只在測試內，不進 `app/`） |
| F-6 | 摘要演算法對拍（G-06） | 對同一個內容的 LF、CRLF、CR、BOM＋LF、BOM＋CRLF 五種檔（含非 ASCII）：CLI 凍結寫入的摘要＝adapter 的 `SddSpec.digest`＝Bridge 預檢重算的現檔摘要，**五種全部相等**；並以「原始 bytes 的 sha256」為反向對照——CRLF 與 CR 兩種必須**不等**（證明實作沒有退回原始 bytes）；非 UTF-8 檔 CLI rc 4 `doc_not_utf8`；> 16 MiB rc 4 `doc_too_large` |
| F-7 | 權杖與環境不外洩（G-09） | Bridge 環境有權杖時，`RunHandle._child_env()` 的輸出不含它；Bridge 自己的環境帶 `SDD_STATE_DIR`／`SDD_PROJECT` 時，**不含** `sdd` 區塊的 run 的子行程環境兩者皆無、含 `sdd` 區塊的只有 `SDD_PROJECT`；`validate_env` 對 `BRIDGE_SDD_WRITE_TOKEN`、`SDD_PROJECT`、`SDD_STATE_DIR` 回 422 `forbidden_name`；`run.json`、`playbook.yaml`、`config.yaml`、`events.jsonl`、引擎日誌、稽核檔與任何錯誤回應都搜不到權杖值；權杖短於 32 字元或佔位 → `SettingsError`（啟動失敗） |
| F-8 | 名稱規則對拍（S-10） | `fsm_component()` 對 ADR-016 §7.4 的 21 個樣本（含 CJK、空白、括號、`+`、`@`、`a:b`、`x/y`、`CON`、80 字以上、NFD 輸入、尾端空白與句點）與模糊集，輸出逐一等於 SDD `sanitize_component`（以 `importlib` 依路徑載入）且冪等；其輸出都被讀取白名單（淨化輸出域）接受；含 `/`、`\`、`:` 的原名經淨化後等價於標準鍵；`GET /sdd/fsm/{name}` 對含 CJK 與空白的名稱可取得 |
| F-9 | 同步與補償（D-115-10、D-115-15） | 以假 CLI 驅動：`COMPLETED` → `delegate-exit done`；`CANCELLED`（非孤兒）→ `delegate-exit done`；引擎升級型 `FAILED` → `delegate-exit failed`；其餘 `FAILED`（額度停機、異常結束、被訊號終止、Bridge 關閉）、孤兒、`PAUSED` → **零呼叫**；spawn 失敗與 `_materialize` 例外 → 補償 `done`（reason `SPAWN-FAILED…`）且回應是 500 `spawn_failed`；`delegate-exit` rc 3 → alert `SDD_SYNC_STATE_DRIFT`、其他失敗 → `SDD_FSM_SYNC_FAILED`；run 的狀態都不被改變；六種 `--reason` 組字逐字釘住；`ALLOWED_VERBS` 釘住 |
| F-10 | 預檢表與回收點（D-115-15） | 假 CLI＋假 run 登錄：預檢表每一列（`IMPLEMENTATION`／`TEST_CONTRACT_NEGOTIATED`／`SPEC_FROZEN`／其他／狀態檔不存在）的動詞序列；回收點五列（`playbook_ref` 缺或不以 `run:` 開頭＝外來／查無 run／他專案的 run／活躍 run／終態 run）；回收兩步之間 `delegate-enter` 失敗 → FSM 停在 `IMPLEMENTATION`、不 spawn、回 5xx；`resume`／`restore` 的重驗（本 run 為引用者⇒續；別的 run⇒409；`IMPLEMENTATION`⇒重進；`ESCALATION`⇒409 不 spawn） |
| F-11 | AT 文法與歸屬（D-115-16；§3.1.4 (e)、(f)） | ADR-016 §8.1 的 17 個樣本逐一以 `re.fullmatch` 驗過（接受 `AT-001-1-1`、`AT-001-1`、`AT-001-12-3-a`、`AT-001-1-E1`、`AT-001-1-E-1`、`AT-029-1-1-1-1`；拒絕 `AT-14-1-1`、`AT-123`、`AT-001-E-1`、`AT-0001-1-1`、`AT-001-1-`、`AT-001--1`、`at-001-1-1`、`AT-001-1-1_a`、`AT-001-1-1 x`、`AT-{NNN}-1-1`）；正向 adapter 與逆向 RTM adapter 由**同一個** `AT_ID_PATTERN` 組 regex；逆向：多段尾綴歸 AC（`AT-001-12-3-a`→`AC-001-12`）、不符文法者計入 `total_at`／`failed_at_ids`／`unmapped_at_ids` 而不進 AC 桶、有 unmapped 時 `fully_covered=False`、舊三段形輸出逐位元不變；宣告位置只掃 AC 映射列第三欄與 Gherkin 標頭 |
| F-12 | CLI rc→HTTP 對映（ADR-016 §4.1） | 假 SDD 樹（暫存目錄內只回放 JSON 的 `tools/fsm_runtime/fsm_runtime.py`）真起子行程：rc 0／1／2／3／4／5 與逾時、無法啟動各一，逐一斷言 §3.1.4 共通規則 4 的對映表；斷言 argv、cwd、環境集合（無 `BRIDGE_*`）、逾時殺樹、`-W ignore::RuntimeWarning`、`--must-exist` |

---
## 6. 差異與裁決

### 6.1 與規格、既有程式的差異（D-01～D-59）

比對對象：PRD §0／§5／§7／附錄 B、Architecture §6／§7／§8／§11、ADR-001（D12、D18、G-xx）、`W3_BACKEND_P3-6.md`（簡稱「W3」）、Bridge 真實行為（README／`app/`／`tests/`）、Phase 1+2 已落地程式；與五份任務書的差異見 §6.2。**主控已定、本文照做的裁決**（stepId＝審核項 id、204、自由文件走 OpenAI 相容 chat completions 與六個 gate、報表路徑、加密值遮罩與 `reveal`、時間與列舉、Bridge 不可達回 200）不在此重列。「裁決」欄是本契約採用的作法。

**v1.1 的變動**：v1.0 標 ⚠ 的六項（D-04、D-05、D-16、D-19、D-41、D-46）與 v1.0 §6.2 第 2 項，已由主控於 2026-10-15 全部採用本契約的建議值（§6.3 第 1～7 項），本表不再標 ⚠；D-11、D-14、D-15、D-18、D-19、D-22、D-28、D-32、D-40、D-42、D-44 依審查回應修訂或補註；D-47、D-48 改寫；D-49～D-59 為 v1.1 新增。各列與審查缺陷（AR-xx）的對照見 §6.4。

| 編號 | 項目 | 來源 A | 來源 B | 裁決 | 理由 |
|------|------|--------|--------|------|------|
| D-01 | signoff 與 confirm 的分工與回傳型別 | PRD §7.1.4.1：signoff 回 `ProjectResponse` 並落庫；W3：signoff 即建專案、confirm 合流 | ADR-001 D12／Architecture §6(b)：signoff 只批准（回 `ImportRecordResponse`），confirm 才落庫 | 採 **D12** | 設計稿是「先 signoff、再按確認匯入」兩個動作；signoff 即落庫會讓 confirm 失去意義，也會讓兩個端點各建一次專案。`confirm` 未 signoff → 409 |
| D-02 | 自由文件的解析手段 | Architecture §6(b)／ADR D12 第 2 點：Bridge decompose 二段拆解 | ADR D18／W3／主控裁決：後端呼叫 OpenAI 相容 chat completions | 採 **D18**（D12 第 2 點作廢，其餘保留） | decompose 回扁平步驟 DAG，產不出多目標三層樹（ADR G-11）；且 decompose 只能讀 Bridge 環境的金鑰 |
| D-03 | 路徑 A 的觸發 | D12：呼叫端給 `specDir` 且 `GET /sdd/fsm/{project}` 顯示已凍結 | D18／W3：`executionPath` 下有凍結規格 | 兩者並存：明示 `specDir` 或以 `executionPath` 探測 `POST /sdd/compile`；「規格存在但被拒」fail-closed 不退回 LLM | 設計稿沒有 `specDir` 欄位；`/sdd/fsm/{project}` 讀的是 SDD 自己的專案狀態，不是使用者目錄；compile 本身就是最準的探針 |
| D-04 | 解析失敗的 HTTP 形式與 `ParseResultResponse.errors` | Architecture §11.1：422；W3：422 結構化錯誤 | 主控裁決：`ParseResultResponse.errors[]` 形狀 `{gate,detail,location?}` | **HTTP 422**，本文為 `ApiError` 的特化（`errors[]` 項目＝`FieldError`＋`gate/detail/location`）；`ParseResultResponse.errors` 保留但成功時恆為 `[]`（主控裁決，§6.3 第 1 項） | 單一失敗通道（一般 client 把項目當 `FieldError` 讀即可）；`errors` 欄位維持裁決的形狀 |
| D-05 | 補充端點 | PRD §7.1.4／§7.1.8 未列 | 設計稿「歷史記錄」重開審核、「放棄」、「全部重置為預設值」；測試連線要用未儲存的表單值 | 新增 `GET /import/{id}`、`POST /import/{id}/reject`、`POST /settings/{category}/reset`；`test-connection` 的 body 選填（主控裁決，§6.3 第 2 項） | 皆為設計稿元素的最小資料來源；不改動 PRD 既有端點的語意 |
| D-06 | playbook `step_id` | Architecture §6(c)：`T001`、`T002`… | W3：`G{goal.sortOrder}-T{task.sortOrder}` | **`G<目標位置>-T<任務位置>`**（位置＝批次範圍內的 1 起序號，§3.4.4）；prompt 標頭含 stepId | `sortOrder` 非唯一（Phase 2 允許重複），會撞 id 使 Bridge 422；位置序保證唯一且保留 W3 要的可讀性；每步 prompt 互異對 Bridge 的邊界判定也必要 |
| D-07 | `global_goal` | Architecture：專案說明，缺則通過標準 | W3：`project.passCriteria` | 採 **W3** | `passCriteria` 必填、是整個專案的終點，最適合給引擎對齊目標 |
| D-08 | 審核項 `kind` | W3：`TASK_CONFIRM／GOAL_CONFIRM／GOAL_REVIEW／TASK_FAILED` | V3 migration 的 CHECK 與 Architecture §11.3：`TASK_CONFIRM／GOAL_CONFIRM／GOAL_COMPLETED／ESCALATED` | 採 **V3 的四種**；等級 ≥5 的「run FAILED」與任務失敗一律用 `ESCALATED` | V1～V4 已套用、不得改；四種足夠表達（§3.6.2） |
| D-09 | 審核閘的 `:pause` 時機 | W3：每個 `step COMPLETED` 後立即 pause | Architecture §6(c).c.4：提前一步（`STARTED` 時 pause） | 採 **Architecture**（§3.6.1） | Bridge 的 pause 在「呼叫後的下一個步驟邊界」生效，而 `COMPLETED(k)` 與 `STARTED(k+1)` 同一瞬間發出——等到 `COMPLETED` 才呼叫會多跑一個任務（Bridge `test_pause_stops_at_the_step_boundary…` 已實證邊界語意） |
| D-10 | `StartExecutionRequest` | Architecture §11.2：`autonomyLevel`／`tokenBudget`／`scope` 必填，`scope` 含 `mode`、`limits` | W3：全部可省，`scope:{goalIds?,taskIds?}` | **全部可省，預設值明定**；`scope` 含 `mode`、`limits`（超集） | 設計稿表單永遠送齊；API 對腳本更友善；`limits` 是 US-E-10 所需 |
| D-11 | `ConnectionTestResponse` 與 SSRF 拒絕 | Architecture §11.2：`{success,latencyMs,message,resolvedHost}` | W3：`{ok,latencyMs,error}`，拒絕以 `ok=false` 表達 | 採 **Architecture 欄位**＋`httpStatus`；SSRF／allowlist 拒絕是 **422**（網路層失敗才是 200＋`success=false`）；探測方式見 D-54 | 政策拒絕與「試了但失敗」要能區分（監控與 QA 都需要）；並與其他 422 的「結構化原因」一致 |
| D-12 | Bridge 不可達的表達 | W3：`bridgeReachable=false` | Architecture §11.2＋主控裁決：`bridge{connected,instance}` | 採 **`bridge.connected`**，另加 `status`／`runKnown`／`checkedAt` | 主控裁決；`runKnown` 區分「網路不通」與「工作區已清」 |
| D-13 | 審計 | W3：`audit_log` 表（V5）；W3-B1 任務書：寫入端點落 `console.audit_log`（V6） | Architecture §8.6：結構化日誌、不新增資料表；Phase 2 已有 `AuditLoggingFilter` | **兩者並行**：沿用結構化日誌並追加 `action`／`entity`，另依任務書落 `audit_log`（V6，內部實作）；契約**不含**審計查詢端點 | 契約無任何端點讀審計，表是內部實作、不影響 HTTP 契約；版號依任務書（V6，§0.5） |
| D-14 | 限流儲存與鍵 | Architecture §8.6／ADR D16：Redis，無則記憶體 | W3：Bucket4j 記憶體，Redis 選配 | 記憶體為基準，Redis 選配；行為（每個**使用者**每分鐘 100 次、429 封包與標頭）在 §0.4 固定；計數鍵見 D-50 | 行為對外一致；儲存是實作細節 |
| D-15 | SSE 的 token 傳遞 | Architecture §8.1：「SSE 以 fetch 串流帶 Bearer，禁止 query-string token」 | 主控裁決／W3：標頭與 `?access_token=` 兩者皆收 | 採**兩者皆收**，加補強：僅 `/api/v1/stream/**`、只收 access token、後端任何存取日誌不得輸出含 `access_token` 的 query（nginx 的 `log_format` 另行遮罩，§0.7，D-59）、`Cache-Control: no-store`；前端優先用 fetch＋標頭 | 瀏覽器 `EventSource` 無法帶標頭；補強降低 URL 洩漏面（token 30 分鐘過期）。v1.0 把遮罩責任放在 `AuditLoggingFilter`，但它只審寫入方法且不記 query，真正會洩漏的是 nginx |
| D-16 | Token 趨勢的資料來源 | Architecture §6(d)：`execution_steps.tokens_used` 分桶加總 | Bridge `mirror_step` 從不寫 `tokens_used`（`db.py`、`runner.py`） | 新增 Console 擁有的 `run_token_samples`（V7），由 `token` 事件寫入；`ExecutionStepResponse.tokensUsed` 由歸因回算（主控裁決，§6.3 第 3 項：不改 Bridge） | 照原設計圖表會永遠是空的；Bridge 維持零侵入 |
| D-17 | 引擎告警的持久化 | W3：ESCALATION／TOKEN_HALT 寫 alerts 並對映 §5.4.4 | PRD §5.4.4 只有六條規則；`alerts.rule` 無 CHECK | 新增 `ENGINE_ESCALATION`／`ENGINE_TOKEN_HALT` 兩個規則名；其餘 Bridge 告警只轉發 | `rule` 欄無約束，不需改 DDL；避免硬套進六條規則造成語意錯置 |
| D-18 | 自治等級 4 與 5 以上的行為 | PRD §5.3.2：4＝重試失敗後介入、5＝僅致命錯誤；W3：4 只在 ESCALATED、≥5 只在 run FAILED | 引擎沒有等級 5 的「替代方案」能力（Architecture §12） | 照 W3 字面：1～4 只對升級型失敗建審核項，≥5 對任何 run 失敗建審核項；等級 6～10 的審核閘行為同等級 5；引擎設定的部分 **v1.3 已更新**：依 §3.4.2 物化 `minimax.enable_kernel_brain` 並在批次回應回報 `engineCapabilities`（v1.2 的寫法是「不另送引擎設定」〔`UNVERIFIED`；RTM `API-AUT-06` 判 🟡〕，現況見附錄 E 與 §6.6） | 字面保守；Console 的審核閘行為在 4 與 5 以上實際相同，差異只在引擎能力旗標（V-8 已於 v1.3 結案，Architecture §12.2） |
| D-19 | 附錄 B 沒涵蓋的狀態結果 | PRD 附錄 B.3：無 `QUEUED→CANCELLED`、`CANCELLED／COMPLETED→QUEUED`；B.2 無 `FAILED→IN_PROGRESS` | US-E-06（取消標 CANCELLED）、US-E-11（還原）、失敗後重新執行 | 定義「**系統重設**」操作與 R-goal 推導（§3.5.3）；手動 API 仍嚴守附錄 B（主控裁決，§6.3 第 4 項）；B.3 已允許的轉移（例：`BLOCKED／ESCALATED／FAILED／PAUSED→QUEUED`）不算系統重設 | 不改 PRD 附錄、不動 `StateMachinesTest` 鎖住的轉移表；結果可決定、可測 |
| D-20 | 審核 `SKIP` 的可行性（Architecture V-4 待驗） | W3：任務 SKIPPED 後 `:resume` | Bridge：`resume` 只收 `PAUSED`；ESCALATION 後 run 已是 `FAILED`；`restore` 無法跳過步驟 | `SKIP`＝標 `SKIPPED`＋**以剔除該任務的新 playbook 開後續批次**（`X-Follow-Up-Run-Id`） | 這是 Bridge 能力下唯一可行的作法；V-4 結論回寫 Architecture §12 |
| D-21 | `RETRY` 的機制 | W3／Architecture：restore 到失敗步驟前的 checkpoint | 使用者可能先「修改任務」再重試 | 採 **restore**（找不到快照的首步改開後續批次）；**restore 沿用原 playbook**，改過的任務內容要另開批次才生效（§1.2.10） | 守主控裁決；限制明文化，避免使用者誤以為改了就會生效 |
| D-22 | `execution_steps.step_number` 的意義 | PRD §5.3.5：「步驟序號」 | Bridge 寫入該 step 事件的 `seq`（位置放在 `input`） | `stepNumber`＝事件 `seq`，`afterSeq` 直接對 `Last-Event-ID`；`stepNumber`／`stepId` 在各型別的多義處見 §0.6 | PRD §7.1.7 本來就要求 `step_number`「對應事件序」；位置另有 `stepId`／`input.step_id` |
| D-23 | `ExecutionStepResponse.tokensUsed` | Architecture §11.2：由 `execution_steps` 帶出 | Bridge 不寫 | 同 D-16：COMPLETED／FAILED 列由歸因回算，其餘 null | |
| D-24 | 設定匯出的加密值 | Architecture §11.2：匯出「不含敏感值」 | W3：輸出 `"<encrypted>"` 佔位、匯入跳過 | 採 **W3 佔位** | 匯出檔與匯入檔同形狀、可往返；敏感值仍不出現 |
| D-25 | 報表 | PRD §7.1.6：`application/pdf` or `text/csv` | 主控裁決：CSV 必做、PDF 標 W5 | CSV 格式在 §1.3.7 固定（四段、BOM、CRLF、注入防護）；PDF＝v1.1 回 501；**v1.2 起回 200**（與 CSV 同四個區段，PDFBox 3＋內嵌 OFL CJK 字型，C-4） | |
| D-26 | KPI 集合 | PRD §5.4.2：八項 | 設計稿：四張卡（含「完成率」「重試率」） | `metrics` 回十個 KPI（八項＋`taskCompletionRate`＋`retryRate`）與分布 | ADR-001 G-13（兩者皆實作）；設計稿「完成率」是專案內進度，不是 PRD 的全域專案完成率 |
| D-27 | `autoclaude.dalBackend` 等的物化 | Architecture §11.4：`dalBackend`→`storage.mode` | Bridge：`storage` 固定 `yaml_only`，帶了會發 `CONFIG_OVERRIDE_IGNORED` | Console **不送** `storage`／`checkpoint_dir`／`log_dir`；三個鍵標 `STORED_ONLY` | 避免每個 run 都帶噪音告警；誠實標示無效參數 |
| D-28 | `model.*` → `minimax.*` | Architecture §11.4：一律映射 | Bridge 會驗證「實際生效的 MiniMax URL」；引擎只靠 `MINIMAX_API_KEY` 的有無決定要不要建 Brain | **只在 `model.apiKey` 有值時**才送 `minimax.*` 與 `MINIMAX_API_KEY`；`model.apiUrl` 原樣當 `minimax.base_url`（D-48）；預設值與 allowlist 已對齊 Bridge（D-53） | 沒有金鑰就不送，引擎本來就用不到 Brain（也是 E2E 關閉演化的做法，D-58）；有金鑰時預設端點在 Bridge 的 allowlist 內，不會被 `outbound_not_allowed` 拒絕 |
| D-29 | `ConfigResponse` 欄位 | Architecture §11.2：11 欄 | US-S-08、遮罩、型別控制項 | 增加 `hasValue`、`options`、`min`、`max`、`impactNote`、`effect` | 皆為 UI 必需的中繼資料（附錄 C 為 SSOT）；除 `impactNote`（存 `system_configs.impact_note`，W3-B1 任務書與 V5）外不入 DB |
| D-30 | execute 的檢查順序與狀態碼 | PRD §7.1.5：僅提 409 | Architecture §6(c)：409／422／502 | 固定 10 級驗證順序（§1.2.1），QA 可逐項斷言 | |
| D-31 | execute 可接受的專案狀態 | W3：`READY／DRAFT／FAILED`；W3-B2 任務書另含 `COMPLETED` | 附錄 B.1：`DRAFT→EXECUTING`、`FAILED→EXECUTING`、`COMPLETED→EXECUTING` 都不是合法轉移（`COMPLETED` 只能 `→ARCHIVED`） | 接受 `DRAFT`／`READY`／`FAILED`／`COMPLETED`（只擋 `EXECUTING`、`ARCHIVED`）；`DRAFT`／`FAILED` 在同一交易內先 `→READY` 再 `→EXECUTING`（兩步都合法）；`COMPLETED` 屬系統重設（§3.5.3） | 不違反 B.1 的手動轉移表，又保留任務書的可用性；`COMPLETED` 專案補了新任務後可再跑（沒有可執行任務則由 7c 擋下） |
| D-32 | `/metrics` 串流的重播 | PRD §7.1.7：每個 event 帶單調遞增 id，重連從 `Last-Event-ID` 重播 | 三個事件都是 latest-wins 的狀態快照 | **收斂快照**：重連先送各一則最新快照，不重播歷史；三則快照的 id 互異（`<S>.1`／`<S>.2`／`<S>.3`），之後的即時事件 id 嚴格大於 `<S>.3` | 對快照語意等價；省去為歷史指標再存一份。互異才不會被客戶端「已處理的最大 id」去重規則丟掉（v1.0 的 `<S>`、`<S>`、`<S>.1` 會丟第二則，AR-02） |
| D-33 | 審核產生後續批次時如何回報 | PRD：`204 No Content` | 需要告訴客戶端新 run id | 204 保持，新 run id 放回應標頭 `X-Follow-Up-Run-Id`（CORS 已暴露） | 不違反主控的 204 裁決 |
| D-34 | Phase 2 `POST /tasks/{id}/retry` | PRD：重試失敗任務 | 引擎無「單任務重跑」介面 | 維持 Phase 2 行為：只改 DB（`QUEUED`、`retryCount+1`），**不啟動 run**；實際重跑要 `execute`（範圍含該任務）或審核 `RETRY`；**v1.2 明文：不受 `maxRetries` 限制**（C-9，§1.6.4） | 避免兩條重試路徑語意混淆 |
| D-35 | `scope.limits` 的執行 | PRD US-E-10：單一任務／目標／整體 Token 上限 | 引擎只認整體 token_guard | 整體＝`tokenBudget`；任務／目標上限由 Console 依 token 事件歸因判定，超過走 `TOKEN_BUDGET_EXCEEDED`＋`:pause` | 不改引擎即可滿足 |
| D-36 | 分頁預設 | PRD §7.2：`size:10` 範例 | `steps`／`logs` 資料量大 | 預設 10／上限 100；`steps`、`logs` 預設 50／上限 200；`settings/history` 預設 20 | |
| D-37 | 時間格式 | 主控裁決：ISO-8601 帶 offset | Phase 2：`Instant` 輸出 `Z`、封包 `timestamp` 輸出伺服器 offset | 兩種都是合法 offset 表示；client 以日期函式解析，不比對字串 | 不改 Phase 2 已鎖的輸出 |
| D-38 | DAG 的 `status` | Architecture §7.1：狀態於讀取時疊加 | 歷史批次的當時狀態沒有保存 | 疊加**現況**並以 `statusAsOf` 明示 | 歷史重建不是本期需求；需要時可擴充 |
| D-39 | 監控端點的篩選參數 | PRD §7.1.6：端點表未列參數 | ADR-001 G-16：補 `runId`／`from`／`to` | `runId`、`from`、`to`（及趨勢的 `bucket`），預設與上限在 §1.3 | |
| D-40 | 評估指令的可執行檔白名單 | Architecture §8.3：「預設值由 W3 後端定案」 | — | 預設名單見附錄 D.3（可由 `console.security.evaluator-allowlist` 覆寫；主控裁決，§6.3 第 10 項）；D.3 的敘述已降級為「第一道檢查＋字元集」，不再宣稱兩層獨立防線（AR-18） | 本契約給出建議預設，後端可擴充並記入交卷 |
| D-41 | restore 的對象 | PRD §7.1.5：任何 run | 較舊的批次其 playbook 範圍可能已過期（任務被跳過／完成） | 只允許對專案**最新**的批次 restore，否則 409 `只能還原專案最新的執行批次`（主控裁決，§6.3 第 5 項） | 避免以過期範圍重跑已 `SKIPPED` 的任務 |
| D-42 | Flyway 版號 | Architecture §11.4：V5＝`seed_engine_configs` | W3：V5＝`audit_log` | V5＝`seed_engine_configs`（含 `impact_note` 欄位、`import_records.parse_path`／`last_parse_errors`、`model.apiUrl`／`model.name`／`monitor.refreshIntervalMs` 的預設校正）、V6＝`audit_log`（皆 W3-B1）、V7＝事件錨點與 token 樣本（W3-B2，必做） | 版號不得撞；依任務書分工；V1～V4 不動 |
| D-43 | 過期的待決審核項 | 未規定 | 新批次、resume、restore、cancel 後舊審核項會懸空 | 一律自動關閉並註明（§3.5.3、§3.6.3 備註） | 避免對已不存在的閘下決定 |
| D-44 | 頂列 Bridge 連線燈 | 設計稿有 | 沒有全域端點（`/actuator/health` 只代表 console-api） | `NotificationSummaryResponse` 加 `bridgeConnected`／`bridgeCheckedAt`；**歸屬**：B1 實作該端點但兩欄回 null（探測環還不存在），B2 建好探測環後在同一支 controller 補實值；前端 B1 階段顯示「未知」灰點（§1.4.1，AR-08）。**v1.4 更新（D-17）**：探測路徑預設改 `/health/deep`、讀取逾時 3→8 秒，`bridgeConnected=false` 從此也涵蓋「Bridge 行程可達但引擎自檢未通過」（§3.1、§3.1.1） | 沿用頂列已在輪詢的端點，不增加端點；v1.0 沒指定誰補欄位，兩包都會以為是對方的事 |
| D-45 | 暫態告警的 SSE id | PRD：每個 event 帶 id | 暫態告警不持久化，無法重播 | 不帶 `id:` 行 | 避免與日後配置的子序號撞號而被客戶端去重誤丟 |
| D-46 | `pendingSignoffs` 的計數範圍 | Architecture §11.1：只定形狀 | W3-B1 任務書：projects＋goals＋tasks＋import_records 中 `signed_off=false` 且未軟刪／未 REJECTED；ADR-002 前端現況：專案＋草案專案底下的目標 | 專案、目標、任務三表中未 signoff 且未軟刪的列，加上匯入記錄中 `PARSED`／`REVIEWING` 且未 signoff 者（§1.4.1；主控裁決，§6.3 第 6 項） | 每個未簽核的列都是一次待做的 signoff（執行閘要求三層全簽）；`UPLOADED`／`PARSING` 的記錄尚無可簽核內容，計入會讓「從未解析的上傳」使徽章永遠不歸零。**v1.4 更新（D-18）**：同一判準現在也有清單端點 `GET /signoffs/pending`（§1.8.1，`counts.total` 恆等於本計數），儀表板「待人工審批」卡的清單改用它（§4.5 G-10） |
| D-47 | SSRF 的 loopback 例外與「allowlist 內的名稱」 | W3-B1 任務書本文：host 字面列於 allowlist 即不檢查解析後 IP 的類別（供本機 E2E 把 `localhost`／`127.0.0.1` 加進去） | NFR-SEC-04：禁私網／loopback／link-local；B1 補充節與主控立場：allowlist 內的名稱解析到私網／loopback 仍拒，本機 E2E 的假伺服器走 e2e 專用屬性 | `link_local`／`private_ip` **任何 profile 都拒**（即使字面列在 allowlist；沒有「允許私網」旗標）；`loopback` 預設拒，只有 `console.security.allow-loopback=true`（**只在 e2e／test／本機 profile 載入**，預設 false）且 host 在 allowlist 內才放行；allowlist 內的名稱解析到 `link_local`／`private_ip` ＝ `dns_rebinding`（§1.5.7） | v1.0 的「loopback 在 allowlist 內即放行、不設開關」讓任何 profile 只要誤把 `127.0.0.1` 放進 allowlist 就開了 SSRF 洞，且 v1.0 §6.2 的開頭宣稱「已對齊任務書」與本列內容自相矛盾；專屬旗標使 production／docker 不可能放行 loopback，e2e 仍可用本機假伺服器 |
| D-48 | 路徑 B 的 URL 與 `model.apiUrl` 的語意 | W3-B1 任務書本文：`POST {model.apiUrl}/chat/completions`（base URL 須含 `/v1`）；v1.0 契約：依結尾自動補路徑 | 引擎 `MinimaxClient` 直接 `POST` 它拿到的 `base_url`（引擎預設即完整端點）；物化時 `model.apiUrl` 原樣當 `minimax.base_url` | **`model.apiUrl`＝完整的 chat-completions 端點 URL**，後端原樣 POST、不補任何路徑（取消 v1.0 的自動補路徑）；物化原樣當 `minimax.base_url`；預設值校正為引擎預設端點（D-53） | 同一個設定值被兩處使用（Console 自己的 LLM 呼叫、引擎的 Brain），語意必須相同；否則預設值或使用者設的 base URL 在其中一處必壞（AR-09） |
| D-49 | 路徑 A 的目標切分（AR-19） | ADR-001 D18：路徑 A「1 個 Goal 容納全部合約」 | 三道有界閘：每個目標任務數 ≤ 24（`max_steps`），「不截斷、不修剪」；凍結規格的合約數常超過 24 | 依編譯順序**每 24 個合約切成一個目標**（只有一組時名稱為 `<scenario>`，多組時 `<scenario>（第 k 批）`），後一組 `dependsOn` 前一組（§3.3.2） | 否則合約數 > 24 的規格會被 `max_steps` 永遠擋成 422、專案無法匯入；切分不改任務順序與總數 |
| D-50 | 限流的計數鍵（AR-06） | Architecture §8.6／W3／B1 任務書本文：每 IP 每分鐘 100 次 | Docker 全棧下所有使用者都經 nginx，連線位址相同；一個頁面同時輪詢多個端點 | 鍵＝已認證請求的 **JWT subject**，未認證才用客戶端 IP；docker／e2e 設 `trust-forwarded-for=true`＋`server.forward-headers-strategy=native`；限流 filter 在 `JwtAuthenticationFilter` 之後、授權判定之前（429 先於 401／403）；輪詢間隔地板 10 秒（`monitor.refreshIntervalMs` 預設與最小皆 10000）（§0.4 第 4 點；主控裁決） | 以連線位址為鍵會讓整個系統共用一個桶；以使用者為鍵才符合「每使用者每分鐘 100 次」的語意；地板 10 秒使監控頁（約 8 個端點）每分鐘約 48 次，留在額度內 |
| D-51 | 外呼 HTTP 實作（AR-10） | W3-B1 任務書本文：Spring `RestClient`＋`MockRestServiceServer`、新依賴只准 PDFBox／POI／Bucket4j | SEC-04 要求「連線釘死在已驗證的 IP、以原 host 驗 TLS」；JDK `HttpClient` 沒有 DNS resolver 注入點、`Host` 為受限標頭 | 核可新增 **Apache HttpClient 5**（`httpclient5`，版本由 Spring Boot BOM 管）：自訂 `DnsResolver` 釘 IP、Host／SNI 用原 host、不跟 redirect；`test-connection` 與匯入路徑 B 共用 `OutboundHttpClient`（附錄 D.4） | 不加依賴就只能降級為「解析→驗證→連線前再解析」並承認 TOCTOU（DNS rebinding 的競態窗）；主控已核可新增依賴 |
| D-52 | 人工判定與 R-goal 重算的優先序（AR-11） | §3.5.3 v1.0：`REJECT` 設目標 `FAILED`，且每個重算點套 R-goal | `:stop` 之後 Bridge 發 `status CANCELLED`，重算會把「任務全 `COMPLETED`」的目標算回 `COMPLETED`，蓋掉人類判定 | 順序＝**先重算 R-goal、再套人工判定**（只對被人工 `REJECT` 的 `GOAL_COMPLETED` 審核項所指的目標）；E2E-04 的 REJECT 變體斷言此順序 | 人類的否決是最終判定，不能被後續事件的機械推導蓋掉；寫成規則才可測 |
| D-53 | 設定種子預設值對齊引擎（AR-06、AR-09） | V2 種子：`model.apiUrl`＝`https://api.anthropic.com`、`model.name`＝`claude-sonnet-4-20250514`、`monitor.refreshIntervalMs`＝3000 | 引擎 minimax 預設：`https://api.minimax.io/v1/text/chatcompletion_v2`、`MiniMax-M2.7`；Bridge 的 allowlist（docker compose 設為 `api.minimax.io,api.minimax.chat`；程式內建預設另含 `localhost`、`127.0.0.1`）；輪詢地板 10 秒 | V5 以「**只在值仍等於舊預設時才改**」的 UPDATE 校正三個預設（value 與 default_value 各自判斷，不覆蓋管理員改過的值）；Console 預設 `console.security.outbound-allowlist` 與 Bridge 對齊為 `api.minimax.io,api.minimax.chat`（§0.5、附錄 D.2） | 否則一設金鑰，種子預設值就被 Bridge 以 `outbound_not_allowed` 拒絕，匯入路徑 B 也連不到預設端點；兩份 allowlist 不一致＝Console 放行、Bridge 拒絕 |
| D-54 | `test-connection` 的探測方式（AR-09 連帶） | v1.0 契約：`GET <base>/v1/models` | `model.apiUrl` 已是「完整 chat-completions 端點」，沒有 base 可附加路徑；MiniMax 預設端點也沒有模型列表 | 對完整端點原樣送一則 **1-token 的 POST ping**（`max_tokens:1`、`stream:false`）；404／405 回 `success=false` 與訊息「端點路徑不存在或不接受 POST」（§1.5.7） | 探測的對象必須和實際使用的是同一個 URL；代價是每次測試連線消耗供應商端約一個 token |
| D-55 | execute 失敗時補償刪除的守門（AR-15） | v1.0：「僅在仍是 `INITIALIZING` 且沒有任何 `execution_steps` 時」刪除 run 列 | `spawn_failed` 時 Bridge 已把該列標成 `FAILED` 並鏡射進 DB，守門條件不成立 | 守門改為「**該 run 尚無 `execution_steps`**」，不看狀態（`spawn_failed` 也刪列）（§1.2.1、§3.4.5） | 否則留下 `FAILED` 空批次並佔用 `run_number`；沒有步驟列就代表引擎從未跑起來，刪除是安全的 |
| D-56 | 任務 `maxRetries` 的上限（AR-14） | Phase 2：`CreateTaskRequest`／`UpdateTaskRequest` 只有 `@Min(0)` | Bridge `PlaybookIn.max_retries` 上限 20；execute 超過會被 Bridge 以 422 `invalid_request` 拒絕（那是「契約缺陷」的訊號） | Phase 2 DTO 加 `@Max(20)`（B1）；execute 驗證表加第 9f 項（422 `任務最大重試次數超過上限 20`，B2）作第二道防線（§0.8、§1.2.1） | 把非法值擋在入口；execute 端的檢查涵蓋 Phase 2 已存在的舊資料 |
| D-57 | 匯入記錄的解析結果儲存（AR-07） | W3-B1 任務書本文：失敗時 `parsed_result.error` 記原因 | 契約的 `ImportRecordResponse` 有 `parsePath`、`lastParseErrors`，而 `ParsedResult` 要求 `project`／`goals`；V1 的 `import_records` 沒有對應欄位 | V5 加 `import_records.parse_path`、`last_parse_errors`（JSONB）；`parsed_result` 在解析成功前為 null，失敗**不寫** `parsed_result`；成功解析後 `last_parse_errors` 清為 null（§0.5、§1.1） | 失敗記錄若把錯誤塞進 `parsed_result`，詳情的 `parsedResult` 非 null 卻不含 `project`／`goals`，違反 schema；專屬欄位最單純 |
| D-58 | E2E 關閉「演化」的方式（AR-12、TBC-2） | B2 補充節：`agent.enableSelfEvolution=false` 對映引擎 config 的對應鍵（現查） | 現查 `AutoClaude/autoclaude/utils/config.py`、`main.py`：引擎**沒有**演化開關鍵；AI 演化提案只由 `MINIMAX_API_KEY` 的有無決定 | E2E 執行類情境的 `model.apiKey` 必須為空（Console 就不送 `MINIMAX_API_KEY`／`minimax.*`），且啟動 Bridge 前清掉其環境的 `MINIMAX_*`（§3.4.2、§5.0.1、§5.0.2）；`enableSelfEvolution` 維持 `UNVERIFIED`（**v1.3 更新**：已驗證，改為 `STORED_ONLY`；本列「沒有金鑰就沒有 AI 演化提案」的結論不變，且 v1.3 補查到 `max_evolutions`／`require_evolution_signoff` 在引擎生產路徑上也沒有讀者，§6.6.2） | 沒有金鑰引擎就不建 Brain，ESCALATION 時只剩規則引擎（只寫 log）；有金鑰時演化提案外呼最壞約 96 秒，會拖垮 E2E-05 的輪詢預算 |
| D-59 | 反向代理（nginx）需求（AR-04、AR-05） | B1／B2 任務書的檔案範圍限 `backend/**`；v1.0 契約只對 SSE 提了 nginx | nginx 預設 `client_max_body_size` 1m（10MB 上傳必被擋）；`log_format` 記 `"$request"`，`?access_token=` 進 access log；`AuditLoggingFilter` 本來就不記 query | 新增 §0.7，指定 nginx 的四項設定與 owner（B1：`/api/v1/import/` 11m／180s、`/api/v1/settings/import` 2m；B2：`/api/v1/stream/`、`log_format` 遮罩）；後端任何存取日誌不得輸出含 `access_token` 的 query | 這些缺口只在 Docker 全棧出現（本機直連看不到），不寫進契約就沒有人驗；任務書的檔案範圍已由主控放寬 |

### 6.2 契約 v1.1 與五份任務書（含〈主控裁決補充〉）仍有差異之處（衝突時以契約為準）

W3-B1／B2、W4-F1／F2、W4-QA 五份任務書寫於本契約之前，都規定「衝突時以契約為準」；主控已於 2026-10-15 在每份檔尾加〈主控裁決補充〉。補充節已與本契約 v1.1 對齊的項目不再列入：B1 的失敗存放（V5 兩欄）、`apiUrl` 語意與預設值、SSRF 釘 IP 與 loopback 放行方式、限流鍵、nginx、`@Max(20)`、通知摘要欄位、既有測試同步、reason 一律中文逐字、路徑探測；B2 的 V7、`step_id`、`mock-env`、DB 位移、探測環 2,880、`SKIP`＝後續批次、halt 不判 `ESCALATED`、啟動對帳 404 只記 WARN、AR-01 相依、補償刪除守門、人工判定優先、ASYNC dispatch、E2E 啟動環境、自治等級；F1／F2／QA 的 reason、輪詢地板 10 秒、時間軸改用 steps、Level 4 跑完、儀表板統計、Bridge 連線點、RTM 三項裁決。**下表只列補充節之後仍與契約不同的點**：實作者照契約；主控若要改採任務書的寫法，請改契約，不要各包各自偏離。

| # | 任務書 | 項目 | 任務書字面 | 契約 v1.1 | 已回寫（v1.2 位置） |
|---|--------|------|-----------|-----------|------|
| 1 | W3-B1 | 有界閘 `empty_prompt` 的檢查欄位 | 每個任務的 `description` 與 `passCriteria` 非空 | 任務 `name` 或 `description` 去空白後為空＝閘 `empty_prompt`（422）；`passCriteria` 空白在 `PUT result` 是 400（結構），parse 的路徑 B／C 則填佔位字串並加 warning `passcriteria_placeholder` | §3.3.5、§1.1.4 |
| 2 | W3-B1 | `parsedResult.path` 的大小寫 | `sdd／llm／decompose` | `SDD／LLM／DECOMPOSE`（主控「列舉全大寫」裁決） | §0.2 |
| 3 | W3-B1 | 路徑 C（decompose）的觸發 | 內容 < 2,000 字元且沒有 Markdown 標題行（`^#{1,6}\s`） | 另須 `sourceType=PLAIN_TEXT`（MARKDOWN／PDF／DOCX 一律不走 C）；標題行判準為 `^[ ]{0,3}#{1,6}[ \t]`；路徑 A 的兩種觸發（`specDir`、探測 `executionPath`）排在 C 之前 | §3.3.1 |
| 4 | W3-B1 | 路徑 B 的請求內容 | 單一 `user` 訊息（PRD §5.2.4 樣板）；body 不含 `top_p`／`stream` | 兩則訊息（`system`＋`user`；system 訊息逐字見 §3.3.3），另帶 `top_p`、`stream:false`；總長超過 `console.import.max-prompt-chars`（120,000）不呼叫模型 | §3.3.3 |
| 5 | W3-B1 | SSRF 校驗細節與 3xx 的表達 | 校驗鏈四步；3xx 視為失敗 `redirect_not_allowed` | 六條規則與 `details.violation` 值域見 §1.5.7（IP 字面須標準寫法、IDN 一律拒、名稱的 DNS 結果全部 A／AAAA 都要驗）；3xx 不是錯誤碼：`test-connection` 為 200＋`success=false`，路徑 B 為 `brain_failed`（不跟隨 redirect） | §1.5.7、§3.3.3 |
| 6 | W3-B1 | Bridge 503 的對映 | Bridge 422／503 原樣轉成 422／502 | `/sdd/compile` 不會回 503（該路由不經 `_sdd_root`；v1.0 的 `sdd_unavailable` 分支已移除）；其餘 5xx 一律 502 `引擎橋接服務錯誤` | §3.2 |
| 7 | W3-B1、W4-QA | 本機驗證環境的設定 | B1 的 bootRun 冒煙與 QA 環境清單第 3 點只設 `CONSOLE_SECURITY_OUTBOUND_ALLOWLIST=localhost,127.0.0.1`，並以 `console.execution.mock-cli` 為測試旗標 | 要打 loopback 的假伺服器還須 `console.security.allow-loopback=true`，而該屬性只在 e2e／test profile 載入，所以須以該 profile 啟動（例：`SPRING_PROFILES_ACTIVE=e2e`）；mock 旗標是 `console.execution.mock-env`；其餘見 §5.0.1（QA 補充節只寫「環境照 §5.0」） | §5.0.1、附錄 D.2 |
| 8 | W3-B1 | `pendingSignoffs` 的計數範圍 | projects＋goals＋tasks＋import_records 中 `signed_off=false` 且未軟刪／未 REJECTED | 匯入記錄只計 `PARSED`／`REVIEWING` 且未 signoff（主控裁決，§6.3 第 6 項）；目標與任務所屬的專案、目標也須未軟刪 | §1.4.1、D-46 |
| 9 | W3-B2 | 未簽核的明細 | `details.unsignedIds[]` | `details.unsignedProjectId／unsignedGoalIds／unsignedTaskIds`（分層列出；沒有值的鍵省略） | §1.2.1 第 5 項 |
| 10 | W3-B2 | `reason` 常數的風格 | 英文識別字：`missing_dependencies`、`prompt_too_long`、`advisory_lock_held`、`invalid_state` | 附錄 B 的中文逐字常數（B1／F1／F2／QA 補充節已明寫，B2 補充節未列，仍以契約為準） | 附錄 B |
| 11 | W3-B2 | 事件時間軸 | `task-trend` 同時回 `events[]` | 只回 `List<TaskTrendPoint>`（PRD §7.1.6）；時間軸改用 `GET /executions/{runId}/steps`（F1／F2 補充節已採） | §4.3 M-12 |
| 12 | W3-B2 | token-trend 與 logs 的資料來源 | token-trend 取 `execution_steps.timestamp` 分桶加總；logs「來源 `execution_steps`」 | token-trend 取 `run_token_samples`（Bridge 從不寫 `tokens_used`，D-16；B2 補充節已要求建表）；logs 由 steps、runs、alerts、review_requests 衍生，不含引擎原始 stdout | §3.8.2、§3.8.3 |
| 13 | W3-B2 | 審核 `REJECT` | 一律 `:stop`、run `CANCELLED`、目標 `FAILED` | 依 `kind`：`TASK_CONFIRM`／`GOAL_CONFIRM` 只取消 run；`GOAL_COMPLETED` 另把被審目標標 `FAILED`；`ESCALATED` 只關閉審核項，run 維持 `FAILED`、不呼叫 Bridge | §3.6.3 |
| 14 | W3-B2 | 審核 `RETRY` 的還原點 | restore 到「該步之前的最後一筆 checkpoint」 | 取 `step_idx = p−1` 的快照（`p`＝步驟位置）；找不到（目標或失敗步驟是第一步）改開後續批次並回 `X-Follow-Up-Run-Id` | §3.6.3 |
| 15 | W3-B2 | 連續失敗告警的動作 | 同目標連續 3 次失敗＝CRITICAL＋`:pause`＋建 review | 持久化＋SSE；僅當 Bridge 狀態仍為 `RUNNING` 才 `:pause`；**不另建審核項**（只在該次 `ESCALATED` 審核項的 `reason` 註明） | §3.7 |
| 16 | W3-B2 | 關閉演化（E2E） | `agent.enableSelfEvolution=false` 對映到引擎 config 的對應鍵 | 引擎沒有此鍵；關閉演化＝`model.apiKey` 為空＋清 Bridge 環境的 `MINIMAX_*`（D-58） | §3.4.2、§5.0.2 |
| 17 | W3-B2、W4-F2、W4-QA | `/metrics` 快照的子序號 | 補充節寫 `<S>.1`（`progress-update`）、`<S>.2`（`token-update`） | 三則：`<S>.1` `progress-update`、`<S>.2` `token-update`、`<S>.3` `metric-update`（三者互異才不會被客戶端去重丟掉）；終態重連回 204 的條件是 `Last-Event-ID ≥ <S>.3` | §2.6、E2E-12 |
| 18 | W4-F1 | 「全部重置為預設值」 | 補充節：逐鍵呼叫 reset，「契約無批次端點」 | 契約**有**分類級批次端點 `POST /settings/{category}/reset`（同交易、加密鍵預設略過、token_guard 跨鍵校驗）；前端對目前分頁呼叫它即可，要跨六個分類才需逐分類呼叫；單鍵另有 `POST …/{key}/reset` | §1.5.5、§1.5.6 |
| 19 | W4-F2 | SSE 斷線後的回補順序 | 先 `GET steps?afterSeq` 分頁回補，再以 `Last-Event-ID` 續接 | 先以 `Last-Event-ID` 自動重連（伺服器端重播）；連續失敗兩次以上才退回 REST 回補再連（`steps` 只含步驟事件） | §2.3 第 6 點、§2.8 |
| 20 | W4-QA | Docker 全棧驗證（矩陣 D） | 登入後走一次「匯入貼文字 → signoff → confirm → 執行（映像內建 mock claude）→ COMPLETED」 | Docker 全棧不載入 e2e profile：沒有 `allow-loopback`、`mock-env`，路徑 B／C 沒有可用模型；匯入步驟改走路徑 A（凍結規格放進容器內專案目錄）或直接用 Phase 2 REST 建專案；10MB 上傳與 `access_token` 不入 nginx 日誌仍須驗 | §5.0.1、§0.7 |

v1.2 註：本表 20 列都是契約為準的定案，最後一欄即各差異在契約正文已寫定的位置（無待回寫項）。**W4 補充節〈契約漂移裁決〉與四份開發者交卷提出的新漂移**不屬於本表（本表是任務書對契約），另列於 §6.5.2，同樣逐條已回寫正文並附程式位置。

### 6.3 主控裁決（2026-10-15）

v1.0 交卷時列為〈未決問題〉的 11 項，主控全部採用本契約的建議預設；本節是這些裁決的正式記錄，各列的落點已在對應章節改成定案寫法。

| # | v1.0 的未決問題 | 主控裁決 | 契約落點 |
|---|-----------------|----------|----------|
| 1 | D-04：解析失敗用 422 還是「200＋errors」 | **422**（本文為 `ApiError` 的特化，`errors[]` 項目帶 `gate/detail/location`）；`ParseResultResponse.errors` 成功時恆為 `[]` | D-04、§1.1.3、§3.3.6 |
| 2 | D-05：補充端點 | 全部採用：`GET /import/{id}`、`POST /import/{id}/reject`、`POST /settings/{category}/reset`、`test-connection` body 選填 | D-05、§1.1.7、§1.1.9、§1.5.6、§1.5.7 |
| 3 | D-16：Token 趨勢的資料來源 | 用 Console 擁有的 `run_token_samples`（V7），**不動 Bridge** | D-16、§0.5、§3.5.2、§3.8.2 |
| 4 | D-19：附錄 B 沒涵蓋的狀態結果 | 接受「系統重設」規則（手動 API 仍嚴守附錄 B） | D-19、§3.5.3、附錄 A.4 |
| 5 | D-41：restore 的對象 | 只限專案**最新**批次 | D-41、§1.2.10、E2E-07 |
| 6 | D-46：`pendingSignoffs` 計數 | 照契約：匯入記錄只計 `PARSED`／`REVIEWING` 且未 signoff | D-46、§1.4.1 |
| 7 | v1.0 §6.2 第 2 項：`reason` 風格 | 維持**中文逐字常數**（B1／F1／F2／QA 補充節已改用） | 附錄 B、§0.3 |
| 8 | 事件時間軸的資料來源 | 照 PRD 形狀：`task-trend` 只回 `List<TaskTrendPoint>`；時間軸用 `GET /executions/{runId}/steps` | §1.3.3、§4.3 M-12 |
| 9 | Dashboard「本週完成任務數」 | 先由前端加總各專案 `task-trend` 的 `completed`（近似值；全域端點留待 W5）→ **v1.2 已補**：全域端點 `GET /monitor/task-totals`（C-1），前端改打該端點、不再扇出 | §1.3.8、§4.6 G-G3 |
| 10 | 評估指令的可執行檔白名單 | 採用附錄 D.3 的預設名單 | D-40、附錄 D.3 |
| 11 | e2e 專用屬性的載入範圍 | `allow-loopback`、`test-dns-overrides`、`mock-env`、`sse.keep-alive-seconds` 只在 e2e／test profile 載入，production／docker 不得出現 | §5.0.1、附錄 D.2、D-47 |

另有三項主控裁決已併入對應章節：AR-01 修 **Bridge**（主控另派修復者）而不是降級契約，契約保留「PAUSED 可 restore」並標明依賴（§1.2.10、§3.6.3、E2E-07）；`model.apiUrl` 為完整端點並取消自動補路徑（AR-09、D-48）；RTM 三項裁決（附錄 E：`API-AUT-06` 🟡、`US-M-10` 資源使用情況 🟡、`US-I-05` 瀏覽按鈕 ⛔；其中前兩項在 v1.3 補了可驗證的資料來源與情境〔D-11、D-12，§6.6〕，狀態由 QA 依證據升級）。

### 6.4 審查回應表（獨立 Architect 審查：AR-01～AR-21、TBC-1～3、RTM）

審查證據：獨立 Architect 審查鏡的長證據檔（2026-10-15，唯讀審查）。每條缺陷的處置與修改位置如下；章節編號為本文的 §，YAML 欄為 `openapi-p3-6.yaml` 對應的 path／schema。

| ID | 審查發現（一句話） | 處置 | 契約位置 | YAML |
|----|-------------------|------|----------|------|
| AR-01（P1） | Bridge DB 模式對 PAUSED run 做 restore 會自撞 advisory lock，且失敗路徑洩漏鎖 | 修 Bridge（主控另派修復者）；契約保留「PAUSED 可 restore」並標明依賴 Bridge 修復 | §1.2.10、§3.1、§3.6.3、E2E-07 步驟 6 | `restore` 描述 |
| AR-02 | `/metrics` 收斂快照的 `progress-update` 與 `token-update` 同為 `<S>`，被客戶端去重丟掉 | 三則快照 id 互異：`<S>.1`／`<S>.2`／`<S>.3`；去重規則維持；終態 204 條件改為 `Last-Event-ID ≥ <S>.3` | §2.2、§2.3、§2.4、§2.6、E2E-12 步驟 8～9、D-32 | `/stream/…/metrics` 描述 |
| AR-03 | 框架位元組字面（冒號後空白）與 Spring `SseEmitter` 實際輸出不符 | 契約改為「冒號後空白不保證」；QA 一律以解析後欄位斷言 | §2.1、§5.0.4、E2E-03 步驟 3、E2E-04 步驟 4、E2E-12 步驟 10 | 兩條 stream 描述 |
| AR-04 | nginx 預設 `client_max_body_size` 1m，10MB 上傳必被擋 | 新增〈反向代理需求〉，指定 owner；匯入 11m／180s、設定檔匯入 2m | §0.7 第 1～2 項、D-59 | `import/upload`、`settings/import` 描述 |
| AR-05 | `?access_token=` 進 nginx access log；`AuditLoggingFilter` 的遮罩是空操作 | 刪除對 `AuditLoggingFilter` 的要求；改為「後端任何存取日誌不得輸出含 `access_token` 的 query」＋nginx `log_format` 遮罩（B2 負責） | §0.4 第 2 點、§0.7 第 4 項、E2E-12 步驟 12、D-15、D-59 | stream 描述 |
| AR-06 | 限流以連線位址為鍵，反向代理後全系統共用一個桶；輪詢地板與 100/分互撞 | 鍵＝JWT subject（未認證才 IP）；docker／e2e 設 `trust-forwarded-for` 與 `forward-headers-strategy=native`；`refreshIntervalMs` 預設與最小 10000；輪詢地板 10 秒；E2E 改以使用者隔離 | §0.4 第 4 點、§1.3、§1.4.1、E2E-11、§5.0.4、附錄 C／D.2、D-14、D-50、D-53 | `notifications/summary` 描述 |
| AR-07 | `lastParseErrors`／`parsePath` 沒有儲存位置 | V5 加 `import_records.parse_path`、`last_parse_errors`；`parsed_result` 解析前為 null；失敗不寫 `parsed_result` | §0.5、§1.1、§1.1.3、§3.3.6、D-57 | `ParsedResult`、`ImportRecordDetailResponse.parsedResult`（可為 null） |
| AR-08 | 通知摘要的 `bridgeConnected`／`bridgeCheckedAt` 沒有明確 owner | B1 實作端點、兩欄先回 null；B2 接探測環後在同一支 controller 補實值 | §1.4.1、§3.1、D-44 | `NotificationSummaryResponse` |
| AR-09 | `model.apiUrl` 一鍵兩義；Console 與 Bridge 的 allowlist 不同，設了金鑰後預設值必被 Bridge 拒絕 | `apiUrl`＝完整端點、取消自動補路徑；預設值校正為引擎預設端點；Console allowlist 預設對齊 Bridge；`test-connection` 連帶改為 POST ping | §0.5、§1.5.3、§1.5.7、§3.3.3、§3.4.2、§5.0.2、附錄 C／D.2、D-28、D-48、D-53、D-54 | `test-connection` 描述、`TestConnectionRequest`、`ConfigResponse` 範例 |
| AR-10 | 「連線釘死於已驗證 IP」在現有依賴下無法實作 | 核可 Apache HttpClient 5＋自訂 `DnsResolver`；`test-connection` 與 LLM client 共用 | §1.5.7（連線實作）、附錄 D.4、D-51 | — |
| AR-11 | 審核 `REJECT` 強制目標 `FAILED`，被後續 `CANCELLED` 的 R-goal 重算蓋回 | 先重算 R-goal、再套人工判定；E2E-04 的 REJECT 變體補斷言順序 | §3.5.3、§3.6.3、E2E-04 REJECT 變體、D-52 | — |
| AR-12 | E2E 環境：mock claude 裸名需 PATH；引擎額度快取未隔離 | `claudeCommand` 用絕對路徑；Bridge 啟動環境三件事（PATH、`AUTOSDD_QUOTA_CACHE_DIR`、清環境）；validation_rule 允許 Windows 絕對路徑與 `.exe` | §5.0.1、§5.0.2、§3.4.2、附錄 C、D-58 | — |
| AR-13 | §6.2 漏列任務書差異 | §6.2 改寫為「契約 v1.1 對任務書（含補充節）」的逐條表 | §6.2 | — |
| AR-14 | Phase 2 `maxRetries` 無上限，Bridge 上限 20 | Phase 2 DTO 加 `@Max(20)`（B1）；execute 加第 9f 項 422（B2） | §0.8 第 2 項、§1.2.1 第 9f 項、§3.4.1、附錄 B.2、E2E-02 步驟 8、D-56 | `execute` 描述 |
| AR-15 | `spawn_failed` 與補償刪除的守門條件衝突 | 守門改為「該 run 尚無 `execution_steps`」，不看狀態 | §1.2.1、§3.2、§3.4.5、D-55 | `execute` 描述 |
| AR-16 | 既有測試會紅，契約與任務書都沒點名要同步修改 | 新增〈須同步修改的既有程式與測試〉，標明各棒與真值 | §0.8 | — |
| AR-17 | `DomainException.details` 禁 null，契約與 E2E 寫了 `null` | 約定「`details` 不輸出 null」；斷言一律「缺席或 null」 | §0.2（null 與缺席）、§5.0.4、E2E-02 步驟 3 | `ApiError.details` 描述 |
| AR-18 | 評估指令白名單「兩層獨立防線」過度宣稱 | 敘述降級（只看第一個 token；字元集不含 `\|`）；字元集不改 | 附錄 D.3、D-40 | — |
| AR-19 | 路徑 A 把全部合約塞進 1 個目標，超過 24 即永遠 422 | 依編譯順序每 24 個合約切一個目標；補 30 合約的整合測試 | §3.3.2、§3.3.5、E2E-01、D-49 | `parse` 描述 |
| AR-20 | 同名多義與 YAML／MD 小差異 | §0.6 寫清 `stepNumber`／`stepId` 三義；YAML 刪頂層 `followUpOfRunId`、`ExecutionStepStatus` 移除 `IN_PROGRESS`、懸空參照改 §3.6.2、七條操作補 400；§2.7 說明 REST `events` 與 SSE `data` 的 `event` 鍵差異 | §0.6、§2.7、§3.1 | `ExecutionRunResponse`、`ExecutionStepStatus`、`ReviewRequestResponse.stepId`、pause／resume／cancel／dag／checkpoints／restore／stream 的 400 |
| AR-21 | 規則細節不一致（八項） | 全修：BLOCKED→QUEUED 不算系統重設（§3.5.3）；§3.5.1(4) 改寫（restore 才必重發）；PARSING 的 parse 統一 409「解析中，請稍候」（§1.1）；空白任務 name 統一為閘 `empty_prompt`（§1.1.4、§3.3.5）；`TOKEN_BUDGET_EXCEEDED` 的 `:pause` 綁真的新增告警（§3.7）；SKIP 與自動 REJECT 的先後（§1.2.11）；移除 `/sdd/compile` 的 503 死分支（§3.2、§3.3.1）；E2E-04 步驟 12 改用新專案 | §1.1、§1.1.4、§1.2.11、§3.2、§3.3.1、§3.3.5、§3.5.1、§3.5.3、§3.7、E2E-04 步驟 12 | `parse`／`PUT result` 描述、`ParsedTask.name` |
| TBC-1 | `SseEmitter` 完成時的 ASYNC dispatch 可能重跑授權鏈，出現 AccessDenied 日誌 | 加實作提醒：`dispatcherTypeMatchers(DispatcherType.ASYNC).permitAll()` 或 `shouldNotFilterAsyncDispatch`；B2 交卷貼「無 AccessDenied」證據；E2E-12 新增步驟 14 | §2.1、§0.4 第 2 點、§0.8 第 1 項、§5.0.4（A3）、E2E-12 步驟 14 | stream 描述 |
| TBC-2 | E2E-05 時引擎會對 `minimax.base_url` 發演化提案，退避可能拖垮輪詢預算 | 以 AR-12 關閉演化處理：執行類情境 `model.apiKey` 必為空、清 `MINIMAX_*` | §3.4.2、§5.0.2、E2E-01 結束動作、E2E-05 前置、D-58 | — |
| TBC-3 | 路徑 A 實務合約數量不明 | 併入 AR-19：切分設計不依賴實際合約數 | §3.3.2、D-49 | — |
| RTM | `API-AUT-06`、`US-M-10`、`US-I-05` 的判定 | `API-AUT-06` 🟡；`US-M-10`（資源使用情況）🟡；`US-I-05`（瀏覽按鈕）⛔ | 附錄 E、§4.6 G-I2／G-M3 | — |

### 6.5 v1.2 變更一覽（W5；2026-10-15）

W4 獨立 QA（`docs/06_quality/QA_P3-6_E2E_Verification.md`）登記 10 筆缺陷（DEF-AC-001～010）與 21 筆觀察（O-01～O-21）。W5 修復波的 22 項主控裁決（`docs/04_planning/agent_briefs/W5_OVERVIEW.md` §3 的 C-1～C-22）與 W4 補充節〈契約漂移裁決〉的漂移，在 v1.2 一次回寫本契約。分三張表：6.5.1 是裁決逐條（改了哪一節）；6.5.2 是漂移回寫逐條（以實作為準，附程式位置）；6.5.3 是 SA 在落筆時做的判斷與請主控確認的偏離。

#### 6.5.1 裁決 C-1～C-22 對照

| 裁決 | 來源 | 內容（一句話） | 契約位置 | YAML | 實作 |
|------|------|----------------|----------|------|------|
| C-1 | DEF-AC-009（P2） | 全域任務總計端點；前端「本週完成」改打它、拿掉 30 專案扇出 | §1.0 #41、§1.3.8、§0.4 角色矩陣、§4.5 G-08、§4.6 G-G3、§6.3 第 9 項、附錄 D.1、附錄 E（`API-MON-08`） | `/api/v1/monitor/task-totals`、`TaskTotalsResponse` | BE、FE |
| C-2 | DEF-AC-003（P1） | Bridge 映像裝 git；新增免認證的 `GET /health/deep`；compose healthcheck 改打它 | §3.1.1、§3.1、E2E-13 第 13 列、附錄 E（`BR-26`） | `/health/deep`（Bridge 端點，路徑層級 `servers` 覆寫）、`BridgeDeepHealthResponse`、`BridgeHealthCheck` | INFRA |
| C-3 | NFR-9.3-04 | 軟刪除復原：`POST /projects/{id}/restore`、`GET /projects?deleted=true`、保留期屬性與預設關閉的清除排程 | §0.4、§0.5 V9、§1.0 #42、§1.6.1／1.6.2／1.6.5、附錄 B.2／B.3／D.2、E2E-13 第 2～3 列、§4.5 G-09；ADR-001 D19；附錄 E（`API-PRJ-06`） | `/api/v1/projects/{id}/restore`、`/api/v1/projects`（`deleted`）、`ProjectSummaryResponse.deletedAt`、`ProjectDetailResponse` | BE、FE |
| C-4 | US-M-07／API-MON-07 | PDF 報表改回 200；501 與 `PDF 報表尚未提供（W5）` 退役 | §0.3 第 6 點、§1.3.7、§4.3 M-16、附錄 B.2、附錄 D.4、E2E-03 步驟 15、E2E-13 第 4 列 | `…/report`（移除 501 與 `NotImplemented`） | BE、FE |
| C-5 | DEF-AC-007（P2） | `POST /auth/refresh` 失敗分 `renewed`／`invalid`／`unavailable` 三類；SSE 取 token 與 1→30 秒退避 | §2.8 第 7～9 點、附錄 B.2（`upstream_unavailable`）、E2E-13 第 5 列 | — | FE |
| C-6 | DEF-AC-002（P3） | 設定匯入：值未變一律 `skipped`，先於值規則與 allowlist 驗證 | §1.5.10、E2E-13 第 6 列 | `/api/v1/settings/import` 描述 | BE |
| C-7 | O-14 | `ENGINE_ESCALATION` 去重鍵 `step:<runId>:<stepId>` | §3.7、E2E-13 第 7 列 | `AlertResponse.subject` 描述 | BE |
| C-8 | O-05 | 專案有進行中批次時，刪除目標／任務回 409 `project_executing` | §0.3、§1.6.3、附錄 B.2、E2E-13 第 8 列 | `/api/v1/goals/{id}`、`/api/v1/tasks/{id}`（DELETE） | BE、FE |
| C-9 | O-04 | 手動重試不受 `maxRetries` 限制；toast 文案改「手動重試第 N 次（不計入自動重試上限 M）」 | §1.2.11、§1.6.4、D-34、E2E-13 第 9 列 | — | FE（文案） |
| C-10 | F1-1／F1-2 | 匯入記錄補 `warnings`、`parse_options`（V8）；詳情回 `warnings[]`、`parseOptions` | §0.5 V8、§1.1.3、§1.1.4、§1.1.9、§4.1 I-12／I-18、E2E-01 步驟 3、E2E-13 第 10 列 | `ImportRecordDetailResponse` | BE、FE |
| C-11 | F2-4 | 批次列表項加 `bridgeStatus` | §1.2.2、§4.3 M-02、E2E-13 第 11 列 | `ExecutionRunSummaryResponse.bridgeStatus` | BE、FE |
| C-12 | NFR-9.4-04／O-11 | `X-Trace-Id` 貫穿 console-api→Bridge；Bridge 回帶標頭、每行日誌含 `trace_id` | §0.4 第 6 點、§3.1.1、E2E-13 第 12 列 | — | BE、INFRA |
| C-13 | UI-KPI-01／02 | KPI「環形」以設計稿數值卡為準 | §4.3 M-07；ADR-001 §4、§5 G-20 | — | （文件） |
| C-14 | US-M-09 | 追蹤鏈視圖以批次下拉＋事件時間軸＋日誌查詢涵蓋 | §4.3 M-12 | — | （文件） |
| C-15 | DEF-AC-008／O-08／O-09 | nginx `error_log` 降為 `crit`、`/api/health` 導向前端、`Cache-Control` 只留一份 | §0.7 第 5～6 項、E2E-12 步驟 12 | — | INFRA |
| C-16 | DEF-AC-006／INF-VOL-06／O-20 | compose 的 `CONSOLE_ENCRYPTION_KEY` 必填；`LOG_DIR`／`BRIDGE_LOG_DIR`；`CONSOLE_INTERNAL_PROXIES` | 附錄 D.2（`LOG_DIR`、`server.tomcat.remoteip.internal-proxies`）、§3.1.1（`BRIDGE_LOG_DIR`） | — | INFRA、BE |
| C-17 | DEF-AC-010 | `restore.sh` 對全新空卷先 `mkdir -p`；README 補核對步驟 | 契約不涉及（`docker/README.md` §4.3） | — | INFRA |
| C-18 | DEF-AC-004／005 | 無障礙：主色底小字、`wg-muted`、aria 與 list 結構 | 契約不涉及（設計 token 與元件） | — | FE |
| C-19 | NFR-9.4-01／NFR-9.1-05 | 前端 Prettier；Markdown 預覽去抖 | 契約不涉及 | — | FE |
| C-20 | O-06／O-16 | 文件寫明預設帳密必換、`/actuator/prometheus` 只靠網路隔離 | 契約不涉及（`docker/README.md`） | — | INFRA |
| C-21 | 契約漂移 | 漂移逐條回寫正文 | §6.5.2 | — | SA |
| C-22 | O-15 | `CONSECUTIVE_FAILURES` 觸發路徑說明（不改規則） | §3.7 | — | SA |

QA 缺陷與觀察的對帳：DEF-AC-002＝C-6、003＝C-2、004／005＝C-18、006＝C-16、007＝C-5、008＝C-15、009＝C-1、010＝C-17；O-04＝C-9、O-05＝C-8、O-08／09＝C-15、O-11＝C-12、O-14＝C-7、O-15＝C-22、O-16／20＝C-16／C-20。**DEF-AC-001**（匯入頁把 `maxRetries: null` 當字面「null」）是前端判空缺陷，契約 §0.2 本來就規定「client 視 `null` 與缺席等價」，**不改契約**。**O-03**（E2E-01 步驟 12 對清單端點寫 `signedOffBy` 過寬）已更正該步驟的措辭。其餘觀察（O-01 `X-RateLimit-*` 不暴露、O-02、O-06／07、O-10、O-12、O-13、O-17～19、O-21）維持觀察或另案（見 `W5_OVERVIEW.md` §3 末段〈不在 W5 範圍〉）；O-01 已在 §0.4 第 3 點明文，O-12／O-13 的行為（審核項被系統關閉的 `comment`、`ENGINE_ESCALATION` 訊息即失敗原因）本來就是 §3.5.3／§3.7 的規格。

#### 6.5.2 漂移回寫對照（C-21；以實作為準；對應程式位置相對 `AgentConsole/`）

| 編號 | 漂移與採用的實作 | v1.2 寫入位置 | 對應程式位置 |
|------|------------------|---------------|--------------|
| B1-1 | `execution.globalTokenBudget` 的範圍上限（13 位）與驗證規則（12 位）矛盾；以規則為準，上限 999999999999 | 附錄 C.3、§0.8 | `backend/src/main/resources/db/migration/V5__seed_engine_configs.sql`（規則 `^[1-9][0-9]{0,11}$`）；`…/domain/service/ConfigValueRules`；`…/domain/model/config/ConfigCatalog`（`max` 常數目前仍是 1000000000000，W5-BE 改 999999999999） |
| B1-2 | `file:///x`（空 host）判 `malformed_url` 而非 `scheme`；host 去尾端 `.` 對 IP 字面仍套分類與 allowlist | §1.5.7 規則 1、4；E2E-10 | `…/domain/service/OutboundUrlPolicy`（`checkStatic` 的空 host 判斷早於 scheme 判斷；`normalizeHost`） |
| B1-3 | 沒有 location 的閘，`errors[].field`＝閘名、`message`＝detail | §1.1.3 | `…/adapter/in/web/dto/ApiError.FieldError.ofGate`、`…/adapter/in/web/GlobalExceptionHandler.errorsOf` |
| B1-4 | `GET /settings`、`GET /settings/{category}` 的 `reveal` 非布林回 400 | §0.3、§1.5.1、§1.5.2 | `…/adapter/in/web/SettingsController`（`listAll`／`listCategory` 的 `boolean reveal`）、`GlobalExceptionHandler.handleTypeMismatch` |
| B1-5 | Bridge 基底位址＝管理員改過的 `engineUrl` 優先，否則 `ENGINE_BRIDGE_URL`（預設 `http://localhost:8081`） | §3.1 | `…/adapter/out/bridge/BridgeEndpoints.base`、`…/infrastructure/config/BridgeProperties` |
| B1-6 | 單鍵 PUT／重置的 token_guard 違規 `errors[].field=value`；群組端點為 `haltThresholdPct` | §1.5.3 第 4 項、§1.5.4 | `…/application/service/SettingsService`（`update`／`reset`／`resetCategory` 傳 `"value"`；`updateTokenGuard` 傳 `"haltThresholdPct"`） |
| B1-7 | 設定匯入：加密鍵給明文 → errors 不套用；項目結構不合法 → `missing_configs`（400）；415 判準＝副檔名 `.json` 且內容型別含 `json`／`octet-stream` 或為空 | §1.5.10 | `SettingsService.importSettings`、`…/adapter/in/web/SettingsFileReader.read` |
| B1-8 | 新增依賴的實際版本：pdfbox 3.0.8、poi-ooxml 5.5.1、bucket4j-core 8.10.1（最後一版，之後改名 `bucket4j_jdk17-core`）、httpclient5 由 BOM 管 | 附錄 D.4 | `backend/build.gradle.kts`（版本區） |
| B1-9 | 限流是固定視窗（每 60 秒 100 次；`Retry-After` 取視窗剩餘秒數進位、不小於 1） | §0.4 第 4 點 | `…/infrastructure/security/RateLimiter`、`RateLimitFilter` |
| F1-1／F1-2 | `GET /import/{id}` 不回 warnings、解析選項不存記錄 → **v1.2 已補**（C-10） | §0.5 V8、§1.1.9、§4.1 I-12／I-18 | （W5-BE 實作） |
| F1-3 | `specDir` 沒有 UI 欄位（契約 D-03） | §4.1 I-05 | `frontend/components/domain/import/SourceCard.tsx`、`sourceRules.ts` |
| F1-4 | token_guard 任一鍵有改就走群組端點（PRD §7.1.8） | §4.4 S-09 | `frontend/components/domain/settings/SettingsView.tsx`（`useUpdateTokenGuard`） |
| F1-5 | `reveal` 以分類為單位、每按一次「顯示」＝一筆審計 | §1.5.1、§4.4 S-05 | `SettingsView.tsx`（`listSettingsByCategory(category,{reveal:true})`）；後端 `SettingsService.listCategory`（`auditReveal`） |
| F1-6 | ENCRYPTED 的 `value` 恆為遮罩，前端以 `hasValue` 判「尚未設定」 | §4.4 S-03 | `SettingsView.tsx`、`SettingControl.tsx` |
| F2-1 | 圖表 `DAY` 桶標籤用瀏覽器本機時區（桶起點仍是 UTC） | §1.3 共通參數 `bucket`、§4.3 M-08 | `frontend/lib/domain/metrics.ts`（`formatBucketLabel`） |
| F2-2 | 審核 `RETRY` 內部的 restore 也發 ENGINE 告警 `RESTORE` | §3.6.3 備註 | `frontend/lib/domain/runLive.ts`（`isRestoreAlert`）；後端 `ExecutionGateApiIT`（恰 1 次） |
| F2-3 | 儀表板「本週完成」是前 30 個專案的近似聚合 → **v1.2 已補**（C-1） | §1.3.8、§4.5 G-08 | — |
| F2-4 | 批次列表沒有 `bridgeStatus` → **v1.2 已補**（C-11） | §1.2.2、§4.3 M-02 | — |
| F2-5 | 「查看結果／查看日誌」只做「查看任務」連結 | §4.2 E-18 | `frontend/components/domain/execute/ReviewCard.tsx` |
| F2-6 | keep-alive 註解行前端不可見，以批次詳情 15 秒輪詢兜底 | §2.1 keep-alive 列 | `frontend/lib/api/queries.ts`（`EXECUTION_POLL_MS`） |
| B2-1 | execute 的簽核檢查取整案（範圍外的未簽任務也擋） | §1.2.1 第 5 項 | `…/application/service/ExecuteProjectService.requireSignedOff` |
| B2-2 | 7b：`COMPLETED` 與 `SKIPPED` 的前置目標都視為已滿足；後續批次不做 7b | §1.2.1 第 7b 項 | `…/domain/service/ExecutionPlanner`（`requireDependenciesAreSelectedOrDone`、`plan(…, enforceDependencies)`） |
| B2-3 | 啟動對帳多補「批次在 DB 已終態、專案仍 `EXECUTING`」，依 `console_last_seq` 補處理 | §3.5.4 | `…/application/service/MonitorTicker.reconcile` |
| B2-4 | 閘點暫停旗標存記憶體；console-api 在 `:pause` 與 `PAUSED` 事件之間重啟會遺失，該次不建審核項、需手動 resume | §3.6.1 | `…/application/service/RunRegistry.Runtime`（`gatePauseRequested`）、`RunEventProcessor` |
| B2-5 | `STEP FAILED` 即時框架的 `errorMessage` 取自 DB 的 `FAILED` 列，列晚於事件時即時框架可能缺文字、重播會補 | §2.5 `log` 備註 | `…/application/service/RunEventProcessor`、`StreamService` |
| B2-6 | 時間查詢參數容忍未編碼 `+`；CSV `runs` 區段含 `started_at < to` 的全部批次、`alerts` 取視窗內 | §1.3（共通）、§1.3.7 | `…/adapter/in/web/TimeParams`、`…/application/service/MonitorService.report` |

#### 6.5.3 SA 的判斷與請主控確認的偏離

1. **C-1 的 400 reason**：裁決寫「400 `validation_error`（`errors[].field=to`）」。契約沒有 `validation_error` 這個常數，同族的監控端點用 `時間範圍不合法`；本版採 `時間範圍不合法`＋`errors[].field=to`＋`details={from,to,maxDays:92}`，不新增常數（QA 斷言 `status=400` 與 `errors[0].field=to` 即可）。若主控確要 `validation_error`，請改契約 §1.3.8 與附錄 B 並通知 FE。
2. **C-4 的區段數**：裁決寫「與 CSV 相同的三段（指標摘要、任務趨勢表、告警清單）」。CSV 實為四段（`summary`／`runs`／`tasks`／`alerts`），沒有「任務趨勢表」；為保持 CSV／PDF 同源，PDF 定為「與 CSV 相同的四個區段」＋標題與產生時間。
3. **C-3 的資料面**：裁決沒有說復原後的專案狀態與清除範圍。本版補：V9 增 `projects.deleted_at`／`status_before_delete`、`goals`／`tasks.deleted_at`；復原還原刪除前的狀態；「同一次刪除連帶軟刪」以相同 `deleted_at` 辨識；清除排程只清專案層級（連同子樹），單獨軟刪的目標／任務不清；`ProjectSummaryResponse` 加 `deletedAt`（只在 `deleted=true` 列表帶值）。
4. **C-8 的 reason 與既有常數並存**：`project_executing`（刪除目標／任務被擋）與 execute 的 `專案正在執行中`（啟動執行被擋）語意相近、字串不同。本版照裁決用 `project_executing`，並在 §0.3 第 5 點註明兩者不可混用；若主控想統一，請改用既有的 `專案正在執行中`（FE 已有對應常數）。
5. **C-5 的未列狀態碼**：裁決只列了 `invalid`（400／401／403）與 `unavailable`（網路錯誤、5xx、429）。其餘狀態碼（例：404、408）本版保守歸 `unavailable`（寧可保留 session，也不誤登出）。
6. **C-7 只改 `ENGINE_ESCALATION`**：`ENGINE_TOKEN_HALT` 的 `step:<stepId>` 有同型缺口，本版依裁決未動，§3.7 已註明並列為後續候選。
7. **B1-1 的 `ConfigCatalog.max`**：實作的規則是 12 位，但 `ConfigCatalog` 的 `max` 常數與 `ConfigResponse.max` 仍報 1000000000000；契約以規則為準（999999999999），W5-BE 須把常數對齊（§0.8），否則 `GET /settings` 的 `max` 會比規則多 1。

### 6.6 v1.3 變更一覽（W7；2026-10-16）

W7 收斂波（`docs/04_planning/agent_briefs/W7_OVERVIEW.md`）有五項掌舵者授權的裁決 D-11～D-15；契約涉及 D-11 與 D-12，其餘三項不涉及。分三張表：6.6.1 是裁決對照（改了哪一節）；6.6.2 是 D-11 的引擎旋鈕查證（問題、結論、檔案:行號與原文）；6.6.3 是 SA 落筆時的判斷，其中**偏離主控預設方案的地方請主控確認**。

#### 6.6.1 裁決 D-11～D-15 對照

| 裁決 | 內容（一句話） | 契約位置 | YAML | 實作 |
|------|----------------|----------|------|------|
| D-11 | 等級 6～10 傳遞引擎（`API-AUT-06`）：依等級與旗標物化 `minimax.enable_kernel_brain`，批次回應帶 `engineCapabilities`；查證後**不送** `playbook.max_evolutions`／`require_evolution_signoff`（§6.6.3 第 1 點） | 檔頭摘要、§0.5 V10、§0.8、§1.2.1、§1.2.3、§3.4.2、§3.6.1、§4.2 E-21、§4.4 S-13、附錄 C.1／C.2、附錄 E（`API-AUT-06`）、E2E-14 第 1～7 列、§6.1 D-18／D-58 的更新註記；ADR-001 D20；Architecture §6(c) c.4、§7.1、§7.2、§11.2～§11.4、§12.1 L-10、§12.2 V-8 | `ExecutionRunResponse.engineCapabilities`、`EngineCapabilities`、`EngineCapabilityState` | BE（物化、V10、DTO）、FE（晶片）、QA |
| D-12 | 資源使用情況（`US-M-10`）：Bridge `RunStateOut.resources`＋psutil 背景取樣；`ExecutionRunDetailResponse.bridge.resources`；Agent 即時狀態卡顯示 | §1.2.3、§3.1（取快照列）、§3.1.2、§4.3 M-19、§4.6 G-M3、附錄 D.1、附錄 E（`US-M-10`）、E2E-14 第 8～9 列；ADR-001 D21、G-18；Architecture §10、§10.1、§11.2 | `BridgeInfo.resources`、`ResourceUsage` | INFRA（Bridge）、BE（投影）、FE（顯示）、QA |
| D-13 | `NFR-9.1-05`：20KB 文件預覽更新追到 100 ms 以下 | 契約不涉及（前端效能） | — | FE、QA |
| D-14 | `NFR-9.3-01`：可用性 99.5% 的量測機制（Prometheus recording rule、告警、`promtool` 測試、Grafana 面板） | 契約不涉及（`docker/prometheus/`、`docker/grafana/`） | — | INFRA、QA |
| D-15 | `INF-VOL-07`：nginx_certs／HTTPS 可重現 | 契約不涉及（`docker/README.md`〈14〉） | — | INFRA、QA |

#### 6.6.2 引擎旋鈕查證（D-11；現查 `AutoClaude/` 與 `AgentConsole/engine-bridge/`，全程唯讀）

路徑相對 monorepo 根，`AutoClaude/autoclaude/` 縮寫為 `ac/`；行號是查證當下（2026-10-16）的行號，`AutoClaude` 之後異動請重查（`grep -n` 即可）。原文片段取自該行，`…` 表示省略。Q 編號對應 W7_OVERVIEW §3.1 A 的四個問題。

| # | 問題 | 結論 | 證據（檔案:行號＋原文） |
|---|------|------|--------------------------|
| Q1-a | `minimax.enable_kernel_brain=true` 開了什麼 | `main.py` 以它決定要不要把 Brain 注入 Kernel；Kernel 在步驟失敗且尚有重試次數時先諮詢 Brain，用它的結果改寫該步驟的 prompt | `ac/main.py:294`：`brain = MinimaxBrainAdapter(minimax) if cfg.minimax.enable_kernel_brain else None`；`ac/core/kernel.py:271`：`if self._brain is not None and attempt < max_retries:`；`:284`：`c = self._brain.decide_correction(`；`:300-301`：`if c.correction_prompt:` ／ `task.prompt = self._preserve_output_contract(task, c.correction_prompt)`；`ac/utils/config.py:94-99`（欄位預設 `False` 與行為註解） |
| Q1-b | Brain 呼叫失敗時 | 該步驟**直接升級（不再重試）**，而且不走失敗型升級的善後（沒有 dump、沒有演化提案） | `ac/infra/adapters/minimax_brain.py:124-125`：`except MinimaxError:` ／ `return None`；`ac/core/kernel.py:289-292`：`if c is None:` ／ `return StepOutcome(action=StepAction.ESCALATE,` ／ `failure_reason="Minimax API 故障，安全停止",`；善後只在 `_announce_escalation`（`:338-376`），由「重試耗盡」（`:332-333`）與 `request_escalation`（`:318`）兩條失敗型升級呼叫 |
| Q1-c | 有沒有「步驟變異」 | 實務上沒有：Kernel 呼叫 Brain 時沒傳 `allow_step_mutation`（預設 false），Brain 不被告知變異格式；`kernel.py:302-306` 的變異分支只在模型自行輸出該欄位時才會走。所以 PRD 的「自動突變」在引擎裡的實際內容是 Brain 逐步校正 | `ac/core/kernel.py:284-288`（呼叫沒有該參數）；`ac/decision/prompt_builder.py:113-117`：`def build_correction_system_prompt(allow_step_mutation: bool = False)` ／ `if allow_step_mutation:` ／ `return CORRECTION_SYSTEM_PROMPT + _MUTATION_SCHEMA_SECTION`；`ac/decision/minimax_client.py:132`：`allow_step_mutation: bool = False,` |
| Q1-d | 沒有 `MINIMAX_API_KEY` 時 | **旗標為真＝出錯：引擎啟動即 `return 1`，不是忽略**；旗標為假＝只記警告，playbook 照跑 | `ac/main.py:262-266`：`elif cfg.minimax.enable_kernel_brain:` ／ `logger.error("初始化失敗: enable_kernel_brain=True 但未設定 MINIMAX_API_KEY／config.minimax.api_key")` ／ `return 1`；`:267-271`：`logger.warning("未設定 MINIMAX_API_KEY：Brain 相關能力（步驟 correction／goal synthesis／自演化提案）本次停用，playbook 仍會照常執行")`；金鑰來源 `:235`：`api_key = os.environ.get("MINIMAX_API_KEY") or cfg.minimax.api_key`；Bridge 對非 0 離開碼判 `FAILED`：`AgentConsole/engine-bridge/app/runner.py:473-476`、`:492-502`（`引擎異常結束（exit=…）`） |
| Q1-e | 金鑰格式與連線 | 建構 `MinimaxClient` 只擋空字串，不檢查格式、不連網；真的外呼時才用 `base_url`（原樣當 URL） | `ac/decision/minimax_client.py:101-106`：`if not api_key:` ／ `raise MinimaxError(`；`:223-228`：`httpx.post(` ／ `self._base_url,` |
| Q2-a | `require_evolution_signoff=true` 而沒有 approver | 舊 `PlaybookRunner`：拒絕這次演化重載（記警告、發通知、`return result`），run 以原本已升級的結果結束，**不是批次繼續**；**生產路徑沒有任何人讀這個旗標** | `ac/execution/playbook_runner.py:306-315`：`if not self._cfg.playbook.require_evolution_signoff:` ／ `return True`……`if approver is None:` ／ `"DEF-13-004 \| require_evolution_signoff=True 但未注入 "` ／ `"evolution_approver → fail-closed 拒絕重載 #%d: %s"` ／ `return False`；`:385-399`：`=== DEF-13-004 \| 演化版重載未獲 signoff，停機不重載: %s ===` ／ `return result`；全樹唯一的讀者：grep `require_evolution_signoff` 只命中 `ac/utils/config.py`（定義與註解）與 `playbook_runner.py:306` |
| Q2-b | 舊路徑在生產有沒有使用 | 沒有：套件內沒有 `PlaybookRunner(` 的建構呼叫；入口走 Kernel | `ac/main.py:276-277`：`# SD_Improving_05 W6：雙路徑已移除；Kernel 路徑為唯一正式路徑。` ／ `# 舊 PlaybookRunner 直連模式已於 W6 拔除`；grep `PlaybookRunner\(`（`AutoClaude/autoclaude/`）無建構呼叫；Bridge 啟動引擎的 `AgentConsole/engine-bridge/app/runner.py:202-203`：`argv = [sys.executable, "-m", "autoclaude", str(self.paths.playbook),` ／ `"--config", str(self.paths.config)]` |
| Q2-c | 生產的演化重載迴圈有沒有核可閘 | 沒有 | `ac/core/services/auto_resume.py:255`：`if result.evolved_playbook_path and _evolution_count < _max_evolutions:`，迴圈體內沒有任何 `require_evolution_signoff` 判斷；引擎測試檔頭 `AutoClaude/tests/core/test_kernel_escalation_emit_def_200_518.py:13-14`：`演化提案只出聲、不套用：AutoResumeService 的演化重載迴圈沒有 DEF-13-004 核可閘，` ／ `任何把 MutationProposal 落成 evolved_playbook_path 的改動都會繞過 require_evolution_signoff。` |
| Q3-a | `max_evolutions` 的語意 | 每個 run 的外層「演化版 Playbook 自動重載」次數上限（1～10，預設 3），不是每步驟；**生產路徑進不去**（見 Q3-b） | `ac/utils/config.py:192-193`：`max_evolutions: int = Field(default=3, ge=1, le=10)` ／ `# Gap-020：自動演化最大次數（1~10，預設 3）`；讀者：`ac/core/services/auto_resume.py:210-211,255-256`、`ac/execution/playbook_runner.py:335-336,385,400`；每步驟版本 `ac/plugins/goto_counter_plugin.py:96-99` 的 `is_step_evolution_over_limit` **全樹零呼叫者**；舊路徑每步驟上限寫死 `ac/execution/steps_orchestrator/_escalation_handler.py:87`：`if _step_evo_count >= 2:` |
| Q3-b | 為什麼生產路徑進不去 | Kernel 從不設 `evolved_playbook_path`：`KernelResult` 預設 `None`、`escalated_()` 不帶它；唯一的來源 `PersistenceResult.kind=="evolved_playbook"` 全樹沒有產生者；`apply_evolution` 只被舊的 `execution/` 呼叫；演化提案只寫日誌 | `ac/core/kernel_state.py:68`：`evolved_playbook_path: str \| None = None`、`:113-127`（`escalated_` 沒有該參數）；`ac/core/resolution_policy.py:116-117`：`if r.kind == "evolved_playbook" and evolved_playbook_path is None:`；`PersistenceResult(` 的 `kind` 只有 `interrupt`／`checkpoint`（`ac/plugins/checkpoint/_phase_handlers.py:63-161`）與 `no_op`（`ac/plugins/playbook_persistence_plugin.py:87-89`）；`apply_evolution` 的呼叫點只有 `ac/execution/steps_orchestrator/_escalation_handler.py:111,208,263` 與 `ac/execution/mutation_applier/_complex_mutations.py:114`（定義 `ac/evolution/playbook_evolver.py:229`）；`ac/core/kernel.py:371-374`：`logger.info("=== EVOLUTION PROPOSAL \| [%s] type=%s \| %s ===", task.step_id,`；引擎測試鎖 `AutoClaude/tests/core/test_kernel_escalation_emit_def_200_518.py:263-281`（`test_proposal_is_logged_but_never_applied`：`assert result.evolved_playbook_path is None and result.escalated is True`） |
| Q3-c | `enable_rtm_feedback` | 預設 false；只在演化提案的 rationale 後附 RTM 覆蓋摘要（日誌文字）；且只對 `step_id` 以 `sdd-` 開頭的步驟生效，Console 的 `G<g>-T<t>` 永遠不會觸發。送不送都沒有可觀測的差別 | `ac/utils/config.py:200-206`；`ac/plugins/evolution_plugin.py:141-142`：`if not self._enable_rtm_feedback or self._rtm_feedback is None:` ／ `return ""`；`:146-147`：`if not step_id.startswith("sdd-"):` ／ `return ""`；`ac/core/wiring.py:248-252` |
| Q3-d | `goal_synthesis_enabled` | 預設 **true**：有金鑰時，最後一步之後（POST_RUN）多一次目標驗證外呼，失敗 fail-open；Kernel 只收集 `contributors`，不套用其補完提案。送 `false` 等於關掉既有檢查，所以永不送 | `ac/utils/config.py:207-208`；`ac/core/wiring.py:228-232`；`ac/plugins/goal_synthesis_plugin.py:61-63`：`if not self._enabled or self._client is None:` ／ `return None`；`:174-192`（例外後 `self.validation_failed = True`，預設 `return None`＝fail-open）；`ac/core/kernel.py:144-151`：`post = self._bus.emit(HookContext(` … `contributors.extend(post.contributors)`（沒有讀 `post.request_mutation`） |
| Q3-e | `enable_translation_auto_propose` | 預設 true；只對 SDD 編譯的 playbook 有作用、只產生諮詢提案；送 `true` 沒有任何變化 | `ac/utils/config.py:218-225`；`ac/core/wiring.py:257-265` |
| Q3-f | 演化的 AI 提案由什麼決定 | 只由金鑰的有無：有金鑰才有 `minimax_client`，失敗型 ESCALATION 時先問外部模型、失敗退回規則引擎；沒有金鑰只剩規則引擎；兩種都只寫日誌 | `ac/plugins/evolution_plugin.py:213-222`：`if self._minimax_client is not None:` ／ `ai_proposal = self._ai_evolver.propose_evolution_via_ai(`；`:225-231`：`# Fallback：規則引擎`；`ac/main.py:250-261`（有金鑰才建 `MinimaxClient`）；`ac/core/kernel.py:338-376` |
| Q4-a | Bridge 是否放行這三個鍵 | 放行：`minimax`、`playbook` 在允許的頂層區段內；鍵必須存在於引擎的 `AppConfig`；值由 `AppConfig.model_validate` 驗（`max_evolutions` 須 1～10）；機密鍵不得進 `config_overrides` | `AgentConsole/engine-bridge/app/security.py:47-50`（`_OVERRIDE_SECTIONS`）、`:244-260`（`_walk_sections`：未知鍵回 `unknown_key`）、`:310-317`：`AppConfig.model_validate(effective)`、`:58-60`（`_SECRET_KEYS`） |
| Q4-b | 落在磁碟的哪裡 | `<ENGINE_WORKSPACE>/<runId>/config.yaml`；`yaml.safe_dump(…, sort_keys=False)`，區段是巢狀映射（例：`minimax:` 下一層 `enable_kernel_brain: true`）；`checkpoint_dir`／`log_dir`／`backup_dir`／`scripts_dir`／`storage` 由 Bridge 覆寫 | `AgentConsole/engine-bridge/app/runstate.py:64`：`self.config = run_dir / "config.yaml"`；`runner.py:777`：`paths = RunPaths(self.settings.engine_workspace / run_id)`；`:783`：`paths.config.write_text(_yaml_dump(materialize_config(req.config_overrides, paths)),`；`:72-82`（`materialize_config`）、`:67-69`（`_yaml_dump`） |
| Q4-c | 金鑰怎麼進引擎 | 只走 `env`（`MINIMAX_API_KEY`），不進 `config.yaml`；Bridge 把自己的環境加上請求的 `env` 傳給子行程；環境變數的優先序高於設定檔。**Docker 全棧下 Bridge 的環境本身就有金鑰** | `AgentConsole/engine-bridge/app/runner.py:189-196`（`_child_env`：`env = dict(os.environ)`）；`ac/main.py:235`；`AgentConsole/docker-compose.yml:206`：`MINIMAX_API_KEY: ${MINIMAX_API_KEY:?MINIMAX_API_KEY is required}`（`engine-bridge` 服務） |
| Q4-d | Bridge 對有效 `minimax.base_url` 的檢查 | 有金鑰或 `enable_kernel_brain` 為真時，實際生效的 URL（含完全沒設、走預設）也要過 Bridge 白名單 | `AgentConsole/engine-bridge/app/runner.py:756-773`（`_effective_minimax_violations`） |

#### 6.6.3 SA 的判斷與請主控確認的偏離

第 1～3 點是**偏離主控預設方案**（W7_OVERVIEW §3.1 B）的地方，主控確認前後端不動工；第 4～10 點是落筆時的判斷。

1. **不送 `playbook.max_evolutions`；`agent.enableSelfEvolution` 的 effect 改 `STORED_ONLY`（預設方案是 `ENGINE`）。** 預設方案依 `effSelfEvolution` 送 `max_evolutions`（等級對映 3／5／8／10）。`require_evolution_signoff` 本來就附條件——「只在問題 2 的答案是『拒絕演化、批次不停機』時才送」；實際答案是「舊路徑：停機不重載；生產路徑：根本不讀」，所以依預設方案自己的條件就不送（這一半不算偏離）。偏離的是 `max_evolutions` 與 effect 標籤：查證結果是兩鍵在生產路徑都沒有讀者（Q2、Q3），引擎自己的測試還明文鎖住「演化只提案不套用」。理由：①標 `ENGINE` 會是假的，而誠實標示正是這次的要求；②`require_evolution_signoff=true` 會製造假的 fail-closed 安全感——`AutoResumeService` 沒有核可閘，日後若有人讓 Kernel 產生 `evolved_playbook_path`，這個鍵仍保護不了任何事；③QA 只能驗到「磁碟上有一個數字」，驗的是一個無作用的鍵。**若主控仍要送**（前向相容的惰性鍵）：改 §3.4.2 的「永不送」清單與決策表加一欄，E2E-14 第 1 列的否定斷言反過來；附錄 C 的 effect 仍不可標 `ENGINE`。
2. **`selfEvolution` 由金鑰決定（有金鑰恆 `ENABLED`），不由旗標或等級決定；語意是「只提案」。** 預設方案是「有效旗標為 false → `OFF`」。引擎沒有演化開關，有金鑰就會在失敗型 ESCALATION 外呼 Brain 提案——旗標為 false 卻報 `OFF` 會是謊。代價：等級 3、有金鑰的批次也顯示 `selfEvolution=ENABLED`；前端 tooltip 必須講清楚「僅提案、不套用、與設定無關」（§4.2 E-21）。旗標只剩一個作用：沒有金鑰時，決定報 `OFF` 還是 `UNAVAILABLE_NO_API_KEY`。**替代案（不建議）**：金鑰按需遞送——只有真的要求 Brain 功能時才送金鑰，讓 `OFF` 成真；但會改變「有金鑰就送」的既有行為（目標驗證會悄悄停止，D-58 的 E2E 關閉演化手法也要重寫）。
3. **`autoMutation` 的語意是「Brain 逐步校正（prompt 改寫）」，與 `model.enableKernelBrain` 共用同一個引擎鍵（∨）。** 預設方案寫的「prompt 改寫＋step mutation」只有前者成立（Q1-c）。名稱沿用 PRD 的「自動突變」；impactNote 與 tooltip 如實寫。
4. **旗標與等級用 ∨**：`agent.enableAutoMutation=false` 關不掉等級 ≥ 6 的強制開啟（§3.4.2 劃界 2）。PRD §5.5.1.2 的字面「啟用自動突變（Level 6+）」可讀成 ∨ 也可讀成 ∧；沿用主控預設的 ∨（PRD §5.3.2「6-10 含自動突變、自演化」），請確認。
5. **有金鑰才送、沒有金鑰絕不送 `minimax.*`**（Q1-d：送了會讓引擎啟動失敗）。沿用 v1.2 的條件，並把「為什麼」寫成引擎事實；`enable_kernel_brain` 改為有金鑰時**顯式送 `true`／`false`**，讓磁碟上的設定檔永遠看得到有效值（QA 可斷言）。
6. **`engineCapabilities` 與送出的設定必須來自同一次 `materialize` 呼叫**（§3.4.2 一致性規則）：現行 `RunLauncher` 是交易 1 之後才呼叫，BE 須把呼叫移到交易 1 之前。`resume`／`restore` 不重算；金鑰在批次中途被清掉時重新啟動會失敗（§3.4.2 劃界 3）——沿用現況，不新增保護。
7. **`bridge.resources` 的位置**：W7_OVERVIEW 寫 `ExecutionRunResponse.bridge.resources`；實際上 `bridge` 物件只存在於 `ExecutionRunDetailResponse`（schema `BridgeInfo`），所以欄位落在那裡（§1.2.3），pause／resume／cancel／restore 的快照沒有它。
8. **`resources` 對 PAUSED 與過期樣本為 null**：Bridge 的 pause 會終止整棵引擎行程樹（ADR-001 D8），暫停中沒有行程可取樣；樣本超過 15 秒未更新也回 null，不回舊數字（§3.1.2）。前端終態一律顯示 `—`，因為詳情輪詢在終態後停止（§4.3 M-19）。
9. **E2E-14 的斷言設計**：磁碟路徑 `<ENGINE_WORKSPACE>/<runId>/config.yaml`；第 1 列加入「`playbook` 區段沒有 `max_evolutions`／`require_evolution_signoff`」的否定斷言，把「不送惰性鍵」變成可驗證的事；第 2、3 列用「Brain 校正請求數」與「attempt 數」的行為差異證明 `enable_kernel_brain` 真的到了引擎，而不只是檔案裡有一個布林。另寫明有金鑰的批次會多出的外呼（目標驗證、演化提案）與假伺服器必須立即回應。
10. **Docker 全棧的環境金鑰**：compose 的 `engine-bridge` 服務必填 `MINIMAX_API_KEY`，Console 看不到它；`engineCapabilities` 以 Console 的 `model.apiKey` 為準，方向是低估（§3.4.2 劃界 1）。要精準回報，需要 Bridge 在 `/health` 回報環境金鑰有無，列為後續候選。

### 6.7 v1.4 變更一覽（W7 第二批；2026-10-16）

W7 第二批的裁決是 D-16～D-20（`Implementation_Plan.md` §5.3；來源是 `docs/06_quality/Completeness_Audit_W7.md` 的 I-01～I-07、D-01～D-04、L-03、L-04、V-07、V-11）。分三張表：6.7.1 是裁決對照（改了哪一節）；6.7.2 是 W7-SA 本輪的現查證據；6.7.3 是 SA 落筆時提出、主控已全部裁決的點（Q1～Q8，保留為決策紀錄）與其餘判斷。

#### 6.7.1 裁決 D-16～D-20 對照

| 裁決 | 內容（一句話） | 契約位置 | YAML | 實作 |
|------|----------------|----------|------|------|
| D-16 | AISDLC_SDD 接入：Bridge `GET /sdd/fsm`（清單）＋三個新欄位；`/health/deep` 加 `sdd`；console-api `GET /engines/sdd`；監控頁 AISDLC_SDD 卡；三項偏離 PRD 登記 | 檔頭摘要、§0.3 第 7 點、§0.4 角色矩陣、§1.0 #43、§1.7.1、§3.1 呼叫總表、§3.1.1（`sdd` 檢查）、§3.1.3、§4.3 M-20、E2E-15、附錄 B.4、附錄 D、附錄 E（`API-ENG-01`、`NFR-OBS-01`）；ADR-001 D22、§4 偏離三列；Architecture §4.3、§10、§10.1、§11.1、§11.2、§12.1 | `/api/v1/engines/sdd`、`SddEngineStatusResponse`、`SddFsmState`、`SddProjectEntry`、`SddVersion`、`BridgeDeepHealthResponse.checks.sdd` | INFRA（Bridge）、BE（`EnginesController`）、FE（M-20）、QA |
| D-17 | 深度探針：`autoclaude.healthCheckPath` 預設 `/health/deep`（種子預設＋V11），探測環讀取逾時 3→8 秒，`/health/deep` 加 `sdd` 檢查（只當資訊，不影響 503），假 Bridge 須提供 `/health/deep` | 檔頭摘要、§0.5 V11、§0.8、§1.4.1、§3.1、§3.1.1、§3.7、§3.8.1、§5.0.1、E2E-16 第 1～2 列、附錄 C.5、§6.1 D-44；Architecture §10.1、§11.4 | `BridgeDeepHealthResponse` | BE、INFRA、FE（mock 預設值）、QA |
| D-18 | 待審批清單：`GET /signoffs/pending`，與 `pendingSignoffs` 同判準；儀表板卡改用它；通知鈴連結（受資料來源限制，見 Q5） | 檔頭摘要、§0.4、§0.8、§1.0 #44、§1.4.1、§1.8.1、§4.5 G-06／G-10、§4.6 G-G2／G-G4、E2E-16 第 3～6 列、附錄 E（`API-SGN-05`）、§6.1 D-46；Architecture §11.1、§11.2 | `/api/v1/signoffs/pending`、`PendingSignoffsResponse`、`PendingSignoffItem`、`PendingSignoffCounts` | BE、FE、QA |
| D-19 | refresh token 撤銷名單：換新輪替與登出時撤銷，Redis 優先、不在線退記憶體並記 WARN；限流計數與 SSE 位移如實登記為不使用 Redis | 檔頭摘要、§0.4 第 7 點、§0.8、§1.0 #45、§1.9、§2.8 第 10 點、附錄 D.2／D.4、E2E-16 第 7～10 列、附錄 E（`API-AUTH-03`）；ADR-001 D16 改寫、D23；Architecture §6(c)、§6(d)、§8.1、§8.6、§9.4 | `/api/v1/auth/logout`、`LogoutRequest` | BE、FE（logout 呼叫）、QA；compose 的 `depends_on: redis` 維持不動（Q6） |
| D-20 | 文件登記：DAG 全螢幕（FE 實作）、公告列靜態標示、任務層級範圍回寫、虛擬執行緒範圍、目錄樹差異、覆蓋率口徑、INFRA 兩項偏離、Redis／`dalBackend` 字樣訂正、Console 依賴 Bridge DB 模式 | §4.2 E-13／E-22、§4.6 G-E1／G-E4／G-G5、§6.7.3 第 9～10 點；ADR-001 D1、§4（V-07 口徑、INFRA 兩項偏離）；Architecture §2.5、§4.1、§6(c)、§6(d)、§11.4、§12.1（L-12） | — | FE（E-22）、SA（文件）、QA（RTM 補列） |

#### 6.7.2 現查證據（W7-SA；路徑相對 monorepo 根，行號是 2026-10-16 查證當下的行號）

| # | 事實 | 證據 |
|---|------|------|
| E1 | FSM 狀態檔的真實結構：`retry_history` 是**以重試閘為鍵的映射**（不是列表）；`human_pending_tracking` 是**單一映射**（不是列表）；**沒有任何 RTM 覆蓋數值的鍵** | `AISDLC_SDD/AISDLC_SDD_v0.30/build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml:1-7`（`fsm_state`、`project`、`current_state: INIT`、`current_sprint: 1`）、`:8-26`（`retry_history`：`SCG_VALIDATION`／`PR_REVIEW`／`RTM_VERIFY`，各有 `current_count`、`max_limit`、`history: []`）、`:47-51`（`human_pending_tracking: {entered_at: null, reminder_sent_at: null, reminder_hours: 72, escalation_hours: 168}`）；全檔 Grep `rtm_coverage`／`coverage` 無命中；範本 `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml` 同形 |
| E2 | `history` 與 `decision_trace` 每筆的形狀 | `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/state_loader.py:215-222`（`history.append({"attempt","date","failure_reason","scg_gate"})`）、`:153-161`（`decision_trace` 每筆 `{ts, from, to, reason, spec_refs, agents_consulted, trigger}`）、`:232-235`（`reset_retry` 只歸零 `current_count`、不清 `history`，所以 `history` 是累計） |
| E3 | `human_pending_tracking.entered_at` 的生命週期：進入人工確認點時蓋時戳、離開時清成 null | `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/timeout_checker.py:108-130`；`tools/fsm_runtime/tests/test_timeout_checker.py:128-131`（`assertIsNotNone`／`assertIsNone`） |
| E4 | `build/reports/` 被 git 忽略，**入庫檔數為 0**；真實專案檔與測試殘留檔都只存在於跑過 SDD runtime 的機器 | `AISDLC_SDD/.gitignore:313`（`AISDLC_SDD_v0.30/build/reports/`）；`git ls-files -- AISDLC_SDD/AISDLC_SDD_v0.30/build/reports` 為 0 筆；`git check-ignore -v` 對 `FSM-STATE-test-11472.yaml` 命中同一行；該目錄現有 `FSM-STATE-AISDLC_SDD.yaml` 與 7 個 `FSM-STATE-test-<數字>.yaml`；對照：`git ls-files -- 'AISDLC_SDD/AISDLC_SDD_v*/AISDLC_SDD_INIT.md'` 為 30 筆，與磁碟上 30 個版本目錄一一對應（入口文件入庫，可作為「這是一棵 SDD 樹」的證據，§3.1.1） |
| E5 | compose 把整個 `AISDLC_SDD` 唯讀掛進 Bridge、Bridge 的 healthcheck 打 `/health/deep`、backend 依賴 Bridge healthy（Q1 的因果鏈） | `AgentConsole/docker-compose.yml:210`（`../AISDLC_SDD:/sdd:ro`）、`:199`（`SDD_ROOT: /sdd`）、`:218`（healthcheck 打 `http://127.0.0.1:8081/health/deep`）、`:168-169`（backend `depends_on: engine-bridge: condition: service_healthy`） |
| E6 | Bridge 對 SDD 目錄的預設探索與 SSOT 的差異 | `AgentConsole/engine-bridge/app/settings.py:71-81`（取目錄名數字最大的 `AISDLC_SDD_v<M>.<N>`，不看 git）、`:127-134`（`SDD_ROOT` 空白＝`discover_sdd_root(REPO_ROOT / "AISDLC_SDD")`；給了值但不是版本目錄名時 `discover_sdd_root(given) or given`）；SSOT `tools/lib/sdd_latest.py` 以 `git ls-files` 判定（完整性審查 I-04）。兩者只在「有未入庫的版本目錄」時才分歧，本輪未驗 |
| E7 | 淺層 `/health` 恆 ok，探測環只看 HTTP 2xx | `AgentConsole/backend/src/main/java/com/aisdlc/console/adapter/out/bridge/BridgeHttpAdapter.java:150-158`（`status >= 200 && status < 300`）、`:70-71`（`CONNECT_TIMEOUT` 2 秒、`HEALTH_READ_TIMEOUT` 3 秒）；`BridgeEndpoints.java:15,35-39`（`DEFAULT_HEALTH_PATH = "/health"`）；Bridge `engine-bridge/app/main.py:118-139`（`build_health` 的 `status` 恆為 `"ok"`，`engines.autoclaude.ok`、`engines.sdd.ok` 可為 false 卻不影響它）與 `app/health.py` 檔頭（`/health` 只證明行程活著、引擎可匯入） |
| E8 | `healthCheckPath` 預設值的存放處：種子（V2、V5）、程式兜底常數、前端 mock；`ConfigCatalog` 只有中繼資料 | `AgentConsole/backend/src/main/resources/db/migration/V2__seed_system_configs.sql:51`（`('autoclaude','healthCheckPath','/health','STRING','/health','健康檢查端點',FALSE)`）、`V5__seed_engine_configs.sql:126`（`impact_note`）；`ConfigCatalog.java:114`（`spec("autoclaude","healthCheckPath",CONSOLE,null,null)`）；`frontend/tests/e2e/settingsFixture.ts:92` |
| E9 | `pendingSignoffs` 的判準與儀表板清單的另一條路 | `backend/.../adapter/out/persistence/NotificationCountsAdapter.java:14-27`（四段 `count(*)`）；`frontend/lib/api/queries.ts:240-279`（`useSignoffQueue`：未簽專案＋其未簽目標）、`frontend/components/domain/views/DashboardView.tsx:63,68,115,182`；`frontend/components/domain/SignoffDialog.tsx:16`（`SignoffTarget` 支援 project／goal／task／import） |
| E10 | 匯入記錄在 `confirm` 前沒有專案；匯入頁沒有以 id 深連結某筆記錄的路由；`source_file_name` 可為空 | §1.1.6（`confirm` 才建專案）；`backend/src/main/resources/db/migration/V1__init.sql:142`（`source_file_name VARCHAR(500)` 可空）；`frontend/app/import/page.tsx` 與匯入元件 Grep `searchParams`／`record=` 無命中 |
| E11 | 通知鈴的落點只看「目前專案」 | `frontend/components/domain/notifications/NotificationBell.tsx:25-31` |
| E12 | 後端沒有 Redis 相依也沒有登出端點；JWT 已經有 `jti`；前端登出只清本機 | `backend/build.gradle.kts` 與 `application*.yml` Grep `redis`（不分大小寫）無命中；`AuthController.java:30-40`（只有 `login`、`refresh`）；`JwtTokenService.java:117-127`（簽發時 `.id(UUID.randomUUID().toString())`）；`AuthService.java:47-55`；`frontend/lib/auth/AuthProvider.tsx:71-75`（`logout()`＝`clearSession()`＋清快取＋導向）；`docker-compose.yml:131-132,166`（傳 `SPRING_DATA_REDIS_HOST／PORT`、要求 redis healthy） |
| E13 | 虛擬執行緒只用在兩處；設定檔沒有全域啟用 | `backend/.../application/service/StreamConnection.java:64`、`RunConsumers.java:90`（`Thread.ofVirtual()`，`src/main` 只有這兩處）；`backend/src/main/resources` 下 yml／properties Grep `virtual` 無命中（沒有 `spring.threads.virtual.enabled`；Spring Boot 4.1 的預設值未驗，只記「未設定」） |
| E14 | 後端實際套件與 PRD §4.1 目錄樹的差異；ArchUnit 八條規則 | `backend/src/main/java/com/aisdlc/console/` 實際：`adapter/in/{web,web/dto}`、`adapter/out/{bridge,document,http,llm,persistence}`、`application/{port/in,port/out,service}`、`domain/{exception,model/*,service}`、`infrastructure/{config,logging,persistence/{entity,repository},security}`；沒有 `adapter/in/sse`、`adapter/out/messaging`、`domain/event`；`backend/src/test/java/com/aisdlc/console/architecture/ArchitectureRulesTest.java:22-69`（八條 `@ArchTest`：A1～A6＋JPA 實體只在 `infrastructure.persistence`＋控制器只在 `adapter.in.web`） |
| E15 | INFRA 的兩項偏離（進行中，W7-INFRA 的 D-14） | `AgentConsole/docker-compose.yml:621-625`（`--storage.tsdb.retention.time=35d`，原 15d）、`:629`（`prometheus_data:/prometheus`）、`:739`（具名卷 `prometheus_data`，註解自承「PRD §11.3 未列」） |
| E16 | INFRA 已在 Bridge 實作 D-16／D-17：INFRA 自行發現 Q1 而偏離主控任務書字面，主控事後裁決採其判準，並裁決 `sdd` 只當資訊（Q4），INFRA 已照此落地並實測 | `AgentConsole/engine-bridge/app/routers/sdd.py`（`fsm_list`、`_human_pending`、`_retry_history`、`_load_state`）、`app/health.py` 的 `check_sdd`／`_INFORMATIONAL_CHECKS`／`deep_health`、`tests/test_sdd_fsm.py`、`tests/test_health_deep.py`——契約 §3.1.1、§3.1.3 從其實作 |

#### 6.7.3 SA 提出的點與主控裁決（Q1～Q8 已全部裁決）

Q1～Q8 是 SA 落筆時提出的八個點，**主控已於 2026-10-16 全部裁決**；每點保留「提問」與「裁決」兩段作為決策紀錄（正文已沒有待裁決標記，所有條文都是已裁決的寫法）。第 9 點以後是落筆時的其他判斷。

1. **Q1　`/health/deep` 的 `sdd` 判準（已裁決：採 INFRA 判準）。** 提問：主控任務書原寫「設了但目錄無效或 `build/reports/fsm` 不存在 → false 且整體 503」；事實（E4、E5）是 `build/reports/` 被 git 忽略、入庫 0 筆，乾淨 clone 沒有 `build/reports/fsm`，而 compose 把 `../AISDLC_SDD` 唯讀掛進 Bridge、healthcheck 打 `/health/deep`、backend 依賴 Bridge healthy——照字面，乾淨 clone 的全棧起不來。**裁決**：採 INFRA 的 `check_sdd` 判準——目錄存在**且**（有 `build/reports/fsm` **或**有入庫的 `AISDLC_SDD_INIT.md`）→ `sdd.ok=true`；`SDD_ROOT` 未設（且預設位置也找不到）→ `null`；目錄不存在、不是目錄、或兩者都沒有 → `false`（§3.1.1）。
2. **Q2　`human_pending`／`retry_history`／`rtm_coverage` 的語意（已裁決：照契約預設）。** 提問：主控形狀把 `human_pending_tracking` 當列表、`retry_history` 當有「尾 1 筆」的序列；真實檔（E1、E2）是單一映射、以重試閘為鍵的映射，且沒有 RTM 覆蓋鍵。**裁決**：照契約（§3.1.3，INFRA 實作相同）——`human_pending`：`entered_at` 有值 → `{count:1, items:[該映射]}`，否則 `{count:0, items:[]}`（若日後是列表則 `count`＝筆數、`items`＝尾 5 筆）；`retry_history`：`count`＝三個閘 `history[]` 筆數總和、`last`＝`date` 最晚一筆原樣加 `gate`；`rtm_coverage`：真實檔無此鍵，恆 null（保留位）。若 Console 需要 RTM 覆蓋率，得由 SDD 側先寫進 FSM-STATE，另案。
3. **Q3　`GET /sdd/fsm` 的邊界（已裁決：照契約預設）。** 提問：主控形狀沒寫目錄不存在、壞檔、排序與測試殘留檔。**裁決**：目錄不存在 → 200 空清單；壞檔、非法檔名、symlink 逃逸、同名目錄、YAML 巢狀過深（`RecursionError`）→ 放 `errors[]`；依專案名（實為檔名，見 §3.1.3 排序列）不分大小寫排序；`.yml`／`.bak` 等不符檔名直接忽略；開發機上的 `FSM-STATE-test-<數字>.yaml`（W7-SA 實見 7 個）照列，斷言寫「包含」不寫「等於」（§3.1.3）。
4. **Q4　D-17 的連動（已裁決：採備選——`checks.sdd` 只當資訊）。** 提問：探測環改打 `/health/deep` 後，與 AutoClaude 批次無關的 `sdd` 檢查失敗若觸發 503，會讓 `bridgeConnected=false`、`agentAvailability` 下降、安靜超過閾值的長步驟被 `AGENT_UNRESPONSIVE` 誤報。**裁決**：`checks.sdd` 照常出現在 `checks` 裡，但 `sdd.ok=false` **不觸發 503**；`/health/deep` 的 200／503 只由 `git`／`autoclaude`／`workspace`／`db` 四項決定，頂層 `reason` 不含 `sdd`（INFRA 已照此落地並實測：`engine-bridge/app/health.py` 的 `_INFORMATIONAL_CHECKS`）。探測讀取逾時 3→8 秒（`git --version` 自己最多 5 秒）主控接受。`bridgeConnected=false` 仍不區分「連不上」與「連得上但四項自檢失敗」（要區分需另增欄位，列為後續候選）；SDD 設定錯誤改由 Console 的 AISDLC_SDD 卡顯示（`available=false`、`reason=sdd_unavailable`）。
5. **Q5　D-18 的兩個落差（已裁決：採契約現寫）。** 提問：(a) 主控形狀的每個項目都「含 `projectId`／`projectName`」，但 `IMPORT` 項（`confirm` 之前沒有專案）沒有專案；(b) 通知鈴「待審核項目」「未確認告警」兩個連結要「帶 `projectId`」，但摘要只有三個計數、`GET /signoffs/pending` 只涵蓋待簽核草案，這兩列沒有資料來源。**裁決**：(a) `IMPORT` 項的 `projectId`／`projectName`／`parentId` 為 null（`title`＝檔名或「貼上文字」），仍列入以與 `pendingSignoffs` 同判準；(b) 維持 v1.3 的鈴連結行為（有目前專案才導向該專案，否則專案列表），登記為已知限制（§4.6 G-G4）；「待簽核草案」列導向儀表板待人工審批卡，卡片各項各自帶專案連結。要精準導向（摘要增兩個 `projectId` 欄位，或新增待審核／告警清單端點）另案。
6. **Q6　D-19 的三件事（已裁決：視同核可）。** 提問：(a) 後端沒有登出端點，「登出時撤銷」需要新增 `POST /api/v1/auth/logout`（主控給定的新路徑清單之外的第三條）；(b) 新增相依 `spring-boot-starter-data-redis`（後端原本零 Redis 相依）；(c) compose 仍要求 redis healthy 才啟動 backend，另須設 `management.health.redis.enabled=false`，否則 Redis 一掛 `/actuator/health` 變 DOWN。**裁決**：`logout` 端點、`spring-boot-starter-data-redis` 相依、`management.health.redis.enabled=false` 視同核可；compose 的 `depends_on: redis` 維持不動（降級只保護執行期的 Redis 中斷，不保護冷啟動）（§1.9、附錄 D.2／D.4）。
7. **Q7　E2E-15 的夾具設計（已裁決：照契約預設）。** 提問：主控原寫「Bridge 指向 repo 的 `AISDLC_SDD` 根，FSM 專案 `AISDLC_SDD` 必須出現；`SDD_ROOT` 清空時 `available=false`」；但 `FSM-STATE-AISDLC_SDD.yaml` 在被 git 忽略的目錄下（E4），乾淨 clone 與 CI 沒有；且 `SDD_ROOT` 空白時 Bridge 退回預設探索（E6），在有 repo 的機器上清空並不會變成不可用。**裁決**：E2E-15 主體用夾具（`sdd.engineUrl` 指向另起的 Bridge）；「不可用」改用「Bridge 停掉」與「`SDD_ROOT` 指向不存在目錄」兩種；真實 repo 根改成第 12 列選跑（檔在才跑、不在要明寫未跑）；FSM 檔 ↔ API ↔ 畫面的比對在夾具上做。
8. **Q8　`GET /engines/sdd` 的小形狀選擇（已裁決：照契約預設）。** 提問：SA 在主控形狀之外做了五個小選擇——(a) 未帶 `project` → `fsm=null`（前端選一個再帶 `project` 取第二次；`localStorage` 記住上次選擇）；(b) `version.root` 是 Bridge 端路徑，開發機上會是主機絕對路徑、VIEWER 可見（僅供顯示，前端只秀 `latest`）；(c) Bridge 的 `errors[]` 只記日誌、不轉發；(d) 三個 Bridge 呼叫依序、失敗短路，各 2 秒／3 秒、不重試；(e) `project` 不合白名單 → 400（不是 `fsm_not_found`）。**裁決**：五項照契約預設，維持不變（§1.7.1）。
9. **D-02、D-03：ADR-002 §4 要補的文字（ADR-002 不在 SA 持有面，文字交主控代填；D-04 已寫在本文 §4.6 G-G5）。** 在 `ADR-002-Frontend-Design-System.md` §4〈與設計稿的已知差異〉表加兩列（#10、#11），並改 #4 的「原因」：
   - **#10**｜差異：專案詳情底部不提供 PRD wireframe（PRD:463）的「匯出」按鈕｜原因：PRD 沒有為「匯出」定義任何 User Story、端點或匯出內容（格式、範圍），設計稿也沒畫；若要做，需先定義匯出什麼、什麼格式（W7 完整性審查 D-02，主控裁決保留）。
   - **#11**｜差異：任務詳情的第三張指標卡取設計稿的「重試次數」，不取 PRD wireframe（PRD:600-603）的「執行時長」｜原因：設計稿 README:111 的三張卡是「開始時間／Token 消耗／重試次數」，實作照設計稿（`TaskDetailView.tsx:107-109`）；PRD 的「執行時長」被取代（W7 完整性審查 D-03，主控裁決保留）。
   - **#4（改原因欄）**：「專案／目標／任務詳情底部多『刪除』；任務詳情沒有 PRD wireframe 的『暫停／取消』」的原因由「暫停／取消屬 Phase 4 執行控制」改為「**執行控制只有批次層級**（`POST /executions/{runId}/pause｜resume｜cancel`，契約 §1.2.4～§1.2.6）；PRD §7.1.3 沒有單任務暫停／取消端點，所以任務詳情不提供；設計稿底部也只有重試／編輯」（原理由已隨 Phase 4 完成而過期）。
10. **D-20 其餘項目的落點**：L-03（虛擬執行緒只用於 SSE 寫出與 run 消費者）→ ADR-001 D1「Consequences」補一句；L-04（目錄樹差異與 ArchUnit 八條規則）→ Architecture §4.1 後補〈與 PRD §4.1 目錄樹的差異〉；V-07（前端覆蓋率口徑：`vitest.config.mts` 的 `coverage.include` 只列 31 個項目〔其中 2 個是 glob；審查稱展開後 36 個檔，W7-SA 只驗到項目數〕、整頁視圖由 E2E 驗證不計入、分支門檻 60；全量數字未量）→ ADR-001 §4 偏離清單；V-11 ①（`autoclaude.dalBackend` 標生效與同節矛盾）、②（Architecture 的 Redis 字樣）→ Architecture §11.4、§6(c)、§6(d)、§8.6；V-11 ③（DAG「全螢幕」與任務層級範圍）→ 本文 §4.2／§4.6；I-07（Console 的斷點清單與步驟時間軸依賴 Bridge 的 DB 模式）→ Architecture §12.1 L-12；INFRA 兩項偏離（Prometheus 保留期 15d→35d、具名卷 `prometheus_data`）→ ADR-001 §4 與 Architecture §2.5。
11. **I-04（Bridge 與 SSOT 對「SDD LATEST」的判定可能分歧）**：E6 的差異是真的（Bridge 看目錄名、SSOT 看 `git ls-files`），但是否在實務上分歧「待驗」，不是這輪的形狀問題；本輪只在 Architecture §12.2 登記為待驗項（V-11），不改 Bridge。
12. **給 QA 的 RTM 對照**：新增 `API-ENG-01`、`API-SGN-05`、`API-AUTH-03` 三列；補強 `NFR-OBS-01`（E2E-15 第 5 列）、`US-M-10`／`UI-KPI-08`（探測改打深度探針，E2E-16 第 2 列）、`BR-13`／`BR-14`（Console 現在消費 Bridge 的 SDD 查詢）、`API-NTF-01`（`pendingSignoffs` 與清單同源）、`US-E-09`（DAG 全螢幕）、`INF-SVC-07`（Redis 現在真的被使用）；細目見附錄 E。

### 6.8 v1.5 變更一覽（整合輪 115；2026-10-17）

整合輪 115（`docs/04_planning/AutoSDD_improving_115.md`；軌道① T1 再開）的主控裁決是 D-115-01～16；契約涉及其中 01～06、09、10、14～16（07、08、11、12、13 是 SDD 本身與流程面的裁決，不涉及本契約）；SA 交卷後另有 D-115-18 五項裁決（6.8.1 末列），皆涉及本契約。SD 的 ADR-XPLAT-016（下稱 ADR-016，Proposed）已落檔，本契約**已與它對齊**（逐項處置見 6.8.6）。分六節：6.8.1 是裁決對照；6.8.2 是 W115-SA 本輪的現查證據；6.8.3 是 SA 當初提出的待裁決點與待 SD 定案清單，以及它們的結案；6.8.4 是 RTM 新列草案（QA 單線合併用）；6.8.5 是 SDD 框架體檢缺陷（S-xx）與契約條文的對照；6.8.6 是與 ADR-016 的對齊處置，以及 ADR 沒寫、契約暫定而需確認的靜默處。

#### 6.8.1 裁決 D-115-01～16、D-115-18 對照

| 裁決 | 內容（一句話） | 契約位置 | YAML | 實作 |
|------|----------------|----------|------|------|
| D-115-01 | FSM 一切寫入只經 FSMRuntime CLI 子行程；Bridge 原始碼不得開寫 `FSM-STATE-*.yaml`；D22③「只讀」修訂為「只經 CLI 窄寫」 | §1.7.1 v1.5 加註、§3.1.4 共通規則 1、E2E-17 第 24 列、F-4 | — | Bridge；ADR-016 |
| D-115-02 | 狀態目錄導向 `<execution_path>/build/reports/fsm`；`/sdd/fsm*` 增選填 `root`；`GET /engines/sdd` 依專案帶 `root` | §1.10.4、§3.1.4 (a)、§4.3 M-21 | `getSddEngineStatus` 的 `projectId` | SDD LATEST；Bridge；Backend |
| D-115-03 | 人工閘只開「核准凍結」一個寫動詞（`HUMAN_PENDING`→`SPEC_FROZEN`，帶 approver、理由、文件摘要）；退回邊不做 | §1.10.2、§3.1.4 (d)、§4.7.1、E2E-17 第 1～7 列 | `freezeProjectSddSpec`、`SddFreezeRequest` | SDD CLI；Bridge；Backend；Frontend |
| D-115-04 | Bridge 是委派與談判狀態的唯一同步者；AutoClaude 與 SDD 互不 import | §3.1.6 | — | Bridge |
| D-115-05 | 「零侵入」改「最小侵入白名單」（ADR-016 §11；`NFR-COMPAT-01` 驗證口徑、`AgentConsole/CLAUDE.md` 鐵律 7、Bridge README、PRD §0.5 註記由主控於收尾單人窗口同步） | 本文不涉及 | — | ADR；收尾 |
| D-115-06 | 外部契約不開 `workflow_*`；SDD 批次以 `sdd` 區塊由 Bridge 伺服端注入；預檢（凍結＋三點摘要）不過不 spawn | §1.2.1 v1.5 加註、§1.10.5、§1.10.6、§3.1.6、§3.4.1 | `ExecutionRunResponse.warnings`、`ExecutionWarning` | Bridge；Backend |
| D-115-09 | 框架體檢併入：S-03 AT 文法（以 D-115-16 為準）與出聲、S-04 增 `spec_file`、S-05＝G-02、S-10 專案名規則、S-11／S-12 | §3.1.4 (b)(e)、§3.3.2 | `ParseOptions.specFile`／`sddProject`、`ParsedResult` 四欄 | AutoClaude adapter；Bridge；Backend |
| D-115-10 | 談判閘對映「Console 簽核匯入草稿＝談判同意」；`delegate-exit failed` 只對引擎升級型失敗——**由 ADR-016 §5.2 定案（附四條件），終態對映由 D-115-15 修訂** | §3.1.6 第 2、5 點、§3.1.7 第 4 點 | — | SD；Bridge |
| D-115-14 | **Console 專案為錨**：路徑 A 匯入增選填 `targetProjectId`（併入既有專案並回填綁定；有不同綁定則 409）；核准凍結維持專案層端點，綁定＝`execution_path`＋`sddProject`（預設＝專案名）；不採佔位專案；凍結請求沒有 `binding`、沒有 `sdd_not_bound` | §1.10.1、§1.10.2、§1.10.5、§1.10.7、§1.10.8、§3.3.2、§0.5 V12、§4.7.1 | `SddFreezeRequest`（無 `binding`）、`SddBindingRequest`、`ParseOptions.targetProjectId` | Backend；Frontend；契約 |
| D-115-15 | 委派退出語意：`done`＝交還控制權（不是成功）；COMPLETED→done、CANCELLED→done、引擎升級型 FAILED→failed、PAUSED／額度停機／孤兒／異常結束不動；新批次遇 `AUTOCLAUDE_DELEGATED` 走回收點（終態或不存在⇒回收，活躍或外來⇒409）；恢復留在 SDD session | §3.1.6 第 3～6 點、§3.1.7 第 1、2、10 點、E2E-17 第 19～21、25 列 | — | Bridge；SD |
| D-115-16 | SA 的 Q2／Q4／Q5 採 SA 建議（rtm 無報告 404；`sdd.approver`、compile 的 `fsm_project` 與回應採用；`unmapped_at_ids` 回 200）；AT 文法 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`、前兩段＝所屬 AC；逆向 RTM 以前兩段歸 AC、無法歸屬者計入 `total_at`；`GET /sdd/fsm/{project}` 補 `escalation_provenance`、`fsm_project`、`recovery`；RTM 回應補 `unmapped_at_ids`／`summary.unmapped_at` 且有 unmapped 時 `fully_covered=false` | §1.10.3、§1.10.4、§3.1.4 (c)(e)(f)、§3.3.2、§4.7.2、§4.7.3 | `ExecutionRtmResponse.unmappedAtIds`、`RtmAtCoverage.unmapped`、`SddFsmState` 三新欄 | AutoClaude adapter；Bridge；Backend |
| D-115-18 | SA 交卷後的五項裁決：①採新端點 `PUT /api/v1/projects/{id}/sdd-binding`（#48）；②併入既有專案時專案層 `signedOff` 不動；③路徑 `{project}` 只收淨化後的 FSM 鍵，含 `/` 的原名不可由 URL 定址（降級為已知邊界，不要求 `{project:path}`）；④SDD run 的 `:resume` 與 `/restore` 也須 `X-Bridge-Token`（ADR §9 的兩個呼叫擴大為四個，缺／錯同 503／403）；⑤`expectedDigests` 維持穿透、v1.5 畫面不送 | §1.10.7、§1.10.8、§3.1.7 第 11 點、§3.1.4 共通規則 2、§1.2.4～§1.2.6、§1.2.10、§3.1.6 第 7 點、§6.8.6 B#1／#2／#3／#6／#14 | `updateProjectSddBinding`、`resumeExecution`／`restoreExecution`（加 503 與說明） | Backend；Bridge；契約 |

#### 6.8.2 現查證據（W115-SA；路徑相對 monorepo 根，行號是 2026-10-17 查證當下的行號）

| # | 事實 | 證據 |
|---|------|------|
| E1 | 外部契約的 `PlaybookIn` 鎖死 `workflow_type=auto` 且 `extra=forbid`；`sdd` 因此只能放 `RunCreateIn` 頂層（與 `playbook` 同層） | `AgentConsole/engine-bridge/app/models.py:76-100`（`PlaybookIn`）、`:103-110`（`RunCreateIn`） |
| E2 | 引擎升級型失敗的判別依據：`_on_state` 在引擎日誌出現 ESCALATION 狀態行時設 `_escalation`，`_failure_reason` 以它組出 `引擎升級（ESCALATION）：…`；額度停機、異常結束、孤兒是另外的 reason 形態 | `AgentConsole/engine-bridge/app/runner.py:423-431`（`_on_state`）、`:507-517`（`_failure_reason`）、`:479-492`（`_finish_normally`）、`:844-867`（`_reap_orphan`） |
| E3 | 子行程環境繼承 Bridge 的 `os.environ`，所以權杖必須在 `_child_env` 剝除，否則引擎裡的 AI 步驟能自己簽自己的核准 | `runner.py:203-210`（`_child_env`）；Architecture §12 L-6（Bridge 無認證） |
| E4 | 建立順序：`_validate`（路徑、環境、覆寫檢查）→ 取鎖 → `_materialize` → `start`（spawn）。預檢第 2～5 項接在 `_validate`，FSM 寫入接在 `_materialize` 之後、spawn 之前 | `runner.py:747-764`（`_create`）、`:766-778`（`_validate`）、`:799-819`（`_materialize`）、`:194-246`（`start`、`_spawn`） |
| E5 | SDD 側 CLI 現有 10 個子命令，沒有談判與委派動詞；談判與委派的 API 已落地（`failed` 會走 `record_escalation` 進 `ESCALATION`）；`record_spec_frozen` 只記階段與文件路徑，沒有摘要 | `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/fsm_runtime.py:3288-3293`（`_cli`）、`:1939-1979`（談判進出）、`:3216-3285`（委派進出）、`:641-648`（`record_spec_frozen`）；`state_loader.py:237-247` |
| E6 | 阻塞集合與觀測集合是 `phase` 表的來源；`_HAPPY_PATH` 的鍵共 43 個 | `fsm_runtime.py:660-662`（`_BLOCKING_STATES`）；`transition_rules.py:12-201`（`_HAPPY_PATH`）、`:223-239`（`OBSERVATION_STATES`） |
| E7 | adapter 現況：凍結閘取字母序第一份狀態檔；多份 TCS 時選檔即 `ValueError`；AT 文法 `AT-[\d\-]+`；`spec_format_version` 擷取；scenario 取內文子字串；`digest`＝對 `read_text` 結果的 sha256（文字模式讀檔，換行已被正規化） | `AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py:63-69`、`:100`、`:137`、`:198-213`、`:241-252`、`:257-278`、`:280-285` |
| E8 | 逆向 RTM：只在 run 正常走完（POST_RUN）才寫；檔名 `RTM-COVERAGE-<project>.yaml`，在 `<checkpoint_dir>/rtm`；欄位 `summary.*`、`failed_at_ids`、`weak_regex_at_ids`；AT 還原文法 `^AT-(\d+)-(\d+)-(\d+)$` | `AutoClaude/autoclaude/plugins/rtm_writeback_plugin.py:4-14,50-87`、`autoclaude/core/wiring.py:299-314`、`autoclaude/infra/adapters/playbook_to_rtm_adapter.py:31,99-125`；run 工作區路徑 `engine-bridge/app/runstate.py:56-70` |
| E9 | Console 路徑 A 現況：`SddTask` 只六欄、`sddTask()` 的 `maxRetries` 傳 null、`maintain_context` 不送、規格 `digest` 只存不比；`projects` 沒有任何 SDD 綁定欄；Flyway 現有最大版號 V11 | `AgentConsole/backend/src/main/java/com/aisdlc/console/application/port/out/AgentBridge.java:47-52`、`application/service/ImportParser.java:188-240`、`backend/src/main/resources/db/migration/V1__init.sql:10-27`、`db/migration/V11__health_check_path_deep.sql` |
| E10 | 執行計畫與 playbook 現況：step_id 是 `G<g>-T<t>`；playbook 任務只送七欄 | `backend/src/main/java/com/aisdlc/console/domain/service/ExecutionPlanner.java:169`、`domain/service/PlaybookBuilder.java:42-60` |
| E11 | 專案名白名單差距：SDD 的淨化函式只替換 Windows 禁用字元與控制字元（NFC、上限 80），Bridge 只收 `[A-Za-z0-9._-]` | `AISDLC_SDD/scripts/component_sanitizer.py:36,113-123`；`engine-bridge/app/routers/sdd.py:18` |
| E12 | 替身 `aisdlc-mock-claude` 只回放 prompt 內符合 `\[[A-Z][A-Z0-9_]*\]` 的字樣、不寫檔，所以夾具的驗收字面值只能是這種詞（成功路徑）或不含方括號的詞（失敗路徑） | `engine-bridge/app/mock_claude.py:14-22,35,56-79` |

#### 6.8.3 SA 提出的待裁決點與待 SD 定案清單：結案紀錄

契約初稿（v1.5 對齊修訂之前）曾列 Q1～Q5 待主控裁決、S1～S8 待 SD 定案；主控已於 D-115-14～16 裁決、SD 已於 ADR-016 附錄 B 逐項給值。本表是結案紀錄（值一律以 ADR-016 為唯一真相源，本文只引用位置；需要機械斷言的值已寫進對應章節）。

**A. 主控裁決（SA 提問 Q1～Q5）**

| # | 提問 | 結案 | 契約位置 |
|---|------|------|----------|
| Q1 | 核准凍結與路徑 A 匯入的先後（循環依賴） | **D-115-14**：Console 專案為錨；匯入帶選填 `targetProjectId`，併入既有專案；核准凍結請求沒有 `binding`、沒有 `sdd_not_bound`。**SA 初稿的「佔位 P0 專案」不採**（一個 FSM 專案綁兩個 Console 專案） | §1.10.1、§1.10.2、§1.10.8 |
| Q2 | rtm 無報告用 404 而非 200 加旗標 | **D-115-16 採 SA 建議**：維持 404 `rtm_not_found` | §1.10.3 |
| Q3 | FSM 停在委派態的解卡 | **D-115-15／ADR-016 §10.3**：取消走 `delegate-exit done`；新批次遇 `AUTOCLAUDE_DELEGATED` 時以 FSM 記的 `playbook_ref` 所指的 run 判定——終態或不存在⇒回收，活躍或外來⇒409。**與 SA 初稿的建議不同**（SA：看 Bridge 有沒有同 `fsm_project` 的活躍 run；ADR 以 FSM 記的 run 為準，能辨認外來委派而不碰） | §3.1.6 第 3、5 點 |
| Q4 | `approver` 與 `fsm_project` 兩個 SA 補的欄位 | **D-115-16 採用**（`sdd.approver` 選填，省略記 `console`；compile 請求 `fsm_project`、回應 `spec_file`／`fsm_project`） | §3.1.4 (e)、§3.1.6 |
| Q5 | 回應形狀的小選擇 | **D-115-16 採用**：`ParsedResult` 四欄伺服器擁有；`unmapped_at_ids` 非空仍回 200、Console 轉警告 `at_unmapped`；清單項不帶 `phase`；`spec_format_version` 只顯示 | §3.3.2、§3.1.4 (c)(e) |

**B. SD 定案（SA 的 S1～S8；ADR-016 附錄 B）**

| # | 項目 | 結案（引用位置；值見 ADR） | 契約位置 |
|---|------|----------------------------|----------|
| S1 | 寫入權杖 | 環境變數 `BRIDGE_SDD_WRITE_TOKEN`（兩端同名）、標頭 `X-Bridge-Token`、backend 屬性 `console.bridge.sdd-write-token`；Bridge 未設⇒503、backend 未設⇒freeze 503＋execute 不送 `sdd` 並警告 `token_not_configured`（**同意 SA 暫行寫法**）、不符⇒403；短於 32 字元或佔位⇒兩端啟動失敗（ADR-016 §9） | §3.1.4 共通規則 2、附錄 D.2 |
| S2 | 環境契約 | `SDD_STATE_DIR`（絕對路徑，**只給 CLI 子行程**）、`SDD_PROJECT`（CLI 與引擎子行程）；`spec_file` 靠 playbook 的 `workflow_path`＝TCS 檔案 realpath 進引擎；CLI argv／cwd／環境／逾時 20 秒（ADR-016 §3.5、§7.3、§8.3） | §3.1.4 共通規則 1、§3.1.6 |
| S3 | CLI 動詞表 | 四個新動詞＋`spec-frozen` 擴充；rc 0／1／2／3／4／5；`playbook-ref`＝`run:<run_id>`（不是裸 run_id）；預設階段名 `Stage-<n>`；六種 `--reason` 組字（ADR-016 §4） | §3.1.4 共通規則 4、§3.1.6 |
| S4 | 摘要鍵名與演算法 | 映射 `{<相對 root 的 POSIX 路徑>: "sha256:<64 位小寫 hex>"}`＋`approved_by`；演算法＝換行正規化後的 UTF-8 文字（不是原始 bytes）；與 adapter `SddSpec.digest` 逐位元相同（ADR-016 §4.3） | §1.10.2、§3.1.4 (d) |
| S5 | 談判閘對映與 `failed` 後恢復 | 接受「Console 簽核匯入草稿＝談判 `agreed`」附四條件 C-1～C-4，誠實標註 R-9.20.3 不滿足；`failed`⇒`ESCALATION`，恢復只有人、留在 SDD session（ADR-016 §5） | §3.1.6 第 2 點、§3.1.7 第 1、4 點 |
| S6 | 逆向 RTM 對放寬文法的 AC 聚合 | AT 文法 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`（正逆向同一份）；前兩段歸 AC；不符者**仍計入** `total_at`、列入 `unmapped_at_ids`、不進 AC 桶；`fully_covered` 在有 unmapped 時為 `false`（ADR-016 §8.5） | §1.10.3、§3.1.4 (f) |
| S7 | `/sdd/compile` 摘要不符的例外型別 | `SpecDigestMismatchError`（`SpecNotFrozenError` 子類）⇒三個預檢點一律 **409** `spec_digest_changed`；其餘 `SpecNotFrozenError`⇒422 `spec_not_frozen`（**與 SA 暫行寫法不同**：凍結後內容已變更是 409，不是 422；ADR-016 §6.2、§6.3） | §3.1.4 (e)、§3.1.6 |
| S8 | 最小侵入白名單 | AutoClaude 與 SDD LATEST 的兩張檔案表（ADR-016 §11）；不屬本契約 | — |

#### 6.8.4 RTM 新列草案（給 QA 單線合併；層與 Phase 依 RTM §1.2、§1.3；摘要不超過 20 字；實作檔相對 `AgentConsole/`，`backend/…` 的套件前綴 `com/aisdlc/console/` 省略）

| ID | 來源 | 摘要 | 層 | Phase | 預期實作檔 | 預期自動測試 |
|----|------|------|----|-------|------------|--------------|
| API-PRJ-07 | 契約 v1.5 §0.5 V12、§1.10.5·G-07·D-115-14·PRD §0.4 | 專案 SDD 綁定與唯一索引 | BE+FE | 2 | `backend/src/main/resources/db/migration/V12__project_sdd_binding.sql`、`ProjectEntity`、`dto/ProjectResponse`、`dto/ProjectDetailResponse`、`domain/model/project/NewProject`、`ImportService`（confirm 回填） | `SchemaMigrationIT`（V12 三欄與部分唯一索引）、`ProjectApiIT`（綁定欄回傳）、`ImportApiIT`（confirm 回填） |
| API-PRJ-08 | 契約 v1.5 §1.10.7·ADR-016 §7.2·`PUT /api/v1/projects/{id}/sdd-binding` | 編輯專案的 FSM 專案 | BE+FE | 2 | `adapter/in/web/ProjectController`（或獨立 Controller）、`application/service/SddGovernanceService`、`frontend/lib/api/endpoints.ts`（`updateProjectSddBinding`）、「編輯 SDD 專案」對話框 | `SddBindingApiIT`（驗證、唯一性 409、角色、冪等、稽核）、前端單元（對話框驗證與錯誤顯示） |
| API-SGN-06 | 契約 v1.5 §1.10.2·`POST /api/v1/projects/{id}/sdd/freeze`·PRD §0.4 | 核准凍結（人工閘） | FE+BE+Bridge | 2 | `adapter/in/web/ProjectController`（或獨立 Controller）、`application/service/SddGovernanceService`、`adapter/out/bridge/BridgeHttpAdapter`（`sddFreeze`）、`frontend/lib/api/endpoints.ts`、SDD 治理區元件 | `SddFreezeApiIT`（驗證順序六項、先檢查後寫入、對映表每列、角色）、`BridgeHttpAdapterTest`（`sddFreeze`）、`RbacIT` |
| API-EXE-15 | 契約 v1.5 §1.10.5～§1.10.6、§3.4.1·G-01、G-06、G-08 | SDD 批次與 warnings | BE | 4 | `domain/service/ExecutionPlanner`、`domain/service/PlaybookBuilder`、`application/service/RunLauncher`、`SddGovernanceService`、`BridgeHttpAdapter`（`startRun` 的 `sdd`、權杖、逾時） | `ExecuteProjectApiIT`（SDD 批次、五種 `cause`、`sdd_frozen_digest_absent`、補償、resume／restore 的 409）、`PlaybookBuilderTest`、`ExecutionPlannerTest`（step_id 沿用） |
| API-EXE-16 | 契約 v1.5 §1.10.3·G-05·`GET /api/v1/executions/{runId}/rtm` | 執行追溯覆蓋（諮詢） | FE+BE+Bridge | 4 | `adapter/in/web/ExecutionController`、`dto/ExecutionRtmResponse`、`BridgeHttpAdapter`（`getRunRtm`）、追溯覆蓋面板元件 | `ExecutionRtmApiIT`（有資料、`unmappedAtIds`、404、422、權限）、`BridgeHttpAdapterTest`（`getRunRtm`）、前端單元（面板顯示規則） |
| API-ENG-02 | 契約 v1.5 §1.10.4·D-115-02·G-13 | 引擎狀態依專案帶 root | FE+BE+Bridge | 5 | `adapter/in/web/EnginesController`、`application/service/SddEngineQueryService`、`dto/SddFsmStateDto`（`phase`、`escalationHistory`、`escalationProvenance`、`fsmProject`、`recovery`）、`frontend/lib/api/queries.ts`、`frontend/lib/domain/sdd.ts` | `EnginesApiIT`（`projectId`、404、`sdd_root_rejected`、新欄位、舊 Bridge 相容、`project` 參數驗證）、`SddEngineQueryServiceTest` |
| API-IMP-11 | 契約 v1.5 §3.3.2·G-08、S-03、S-04 | 路徑 A 欄位保真與選檔 | BE | 3 | `application/service/ImportParser`、`domain/model/imports/ParsedResult`、`ParseOptions`、`application/port/out/AgentBridge`（`SddTask`、`SddCompileResult`） | `ImportParserTest`（欄位表逐列、`at_unmapped`、`frozen_digest_absent`、`specFile`、409 不降級）、`ImportApiIT` |
| API-IMP-12 | 契約 v1.5 §1.10.8、§3.3.2·D-115-14 | 匯入併入既有專案 | BE+FE | 3 | `application/service/ImportParser`、`application/service/ImportService`（confirm 併入與回填）、`ParseOptions`（`targetProjectId`）、匯入頁的專案選擇 | `ImportApiIT`（併入、排序、404、三種 409、不帶 target 的重複綁定 409）、`ImportParserTest` |
| BR-27 | 契約 v1.5 §3.1.4 (d)·`POST /sdd/fsm/{project}:freeze`·D-115-03 | 核准凍結寫入動詞 | Bridge | 3 | `engine-bridge/app/routers/sdd.py`、`engine-bridge/app/models.py`、CLI 呼叫新模組 | `engine-bridge/tests/test_sdd_freeze.py`（檢查順序、409／422／403／503、`expected_digests`、摘要、稽核） |
| BR-28 | 契約 v1.5 §3.1.4 (a)(b)(c)、§3.1.5·D-115-02、S-10、G-13 | FSM 讀取擴充與名稱規則 | Bridge | 5 | `engine-bridge/app/routers/sdd.py`、`fsm_names.py`（淨化鏡像）、`phase` 純函式新模組 | `engine-bridge/tests/test_sdd_fsm.py`（`root`、名稱規則、`escalation_history`、`escalation_provenance`、`fsm_project`、`recovery`）、`test_sdd_phase.py`（T-G） |
| BR-29 | 契約 v1.5 §3.1.4 (e)·S-03、S-04、G-02、G-06 | 規格編譯擴充 | Bridge | 3 | `engine-bridge/app/routers/sdd.py`、`engine-bridge/app/models.py` | `engine-bridge/tests/test_sdd.py`（`spec_file`、`fsm_project`、`unmapped_at_ids`、`frozen_digest`、409 摘要不符） |
| BR-30 | 契約 v1.5 §3.1.6·D-115-06 | SDD 批次預檢與注入 | Bridge | 4 | `engine-bridge/app/routers/autoclaude.py`、`engine-bridge/app/runner.py`、`engine-bridge/app/models.py` | `engine-bridge/tests/test_sdd_run.py`（預檢順序、三點摘要、`workflow_*` 注入、`workflow_path` 為檔） |
| BR-31 | 契約 v1.5 §3.1.6·D-115-04、D-115-15 | 批次的 FSM 同步與回收 | Bridge | 4 | `engine-bridge/app/runner.py`、同步新模組 | `test_sdd_integration_parity.py`（F-9、F-10）、`test_sdd_run.py`（終態同步、回收點、resume／restore 重驗） |
| BR-32 | 契約 v1.5 §3.1.4 (f)·G-05 | 追溯覆蓋讀取 | Bridge | 4 | `engine-bridge/app/routers/autoclaude.py` | `engine-bridge/tests/test_rtm.py`（200、404、422、`advisory`、`unmapped_at_ids`） |
| BR-33 | 契約 v1.5 §3.1.4 共通規則 1、2·D-115-01、G-09 | 寫入權杖與環境剝除 | Bridge | 3 | `engine-bridge/app/settings.py`、`engine-bridge/app/runner.py`（`_child_env`）、`engine-bridge/app/security.py`（`validate_env`）、`engine-bridge/app/routers/sdd.py` | `test_sdd_integration_parity.py`（F-4、F-7、F-12） |
| UI-SDD-01 | 契約 v1.5 §4.7.1·G-07、D-115-03、D-115-14 | 專案詳情 SDD 治理區 | FE | 2 | `frontend/components/domain/views/ProjectDetailView.tsx`、SDD 治理區新元件、`frontend/lib/domain/sdd.ts` | 前端單元（顯示規則、鈕啟用條件、對話框驗證、編輯綁定）、mock e2e |
| UI-SDD-02 | 契約 v1.5 §4.7.2·G-05 | 追溯覆蓋（諮詢）面板 | FE | 4 | 執行頁批次詳情元件、面板新元件、`frontend/lib/domain/sdd.ts` | 前端單元（缺值「—」、`unmappedAtIds`、404 中性文字、諮詢標示） |
| UI-SDD-03 | 契約 v1.5 §4.7.3、M-21·G-13 | SDD 卡階段進度與升級 | FE | 5 | `frontend/components/domain/monitor/SddEngineCard.tsx`、`frontend/lib/domain/sdd.ts` | 前端單元（階段字典、阻塞與觀測呈現、恢復指令與「未解升級」判斷式）、mock e2e |

另需 QA 在合併時處理的**既有列**：`NFR-OBS-01`（E2E 驗證欄加 E2E-17 第 17 列的四源對拍）、`NFR-COMPAT-01`（驗證口徑由「零侵入」改為「最小侵入白名單」，不刪列不改號，依 D-115-05）、`BR-13`／`BR-14`（`GET /sdd/fsm*` 加 `root`、`phase`、`escalation_history`、`escalation_provenance`、`fsm_project`、`recovery`）、`API-ENG-01`（`SddFsmState` 新欄位）、`API-EXE-01`（201 新增 `warnings`）、`API-IMP-03`／`API-IMP-05`（`ParseOptions.targetProjectId`、confirm 併入）。RTM §1.2 的 `UI-` 前綴表要補一個 `SDD`（或改用 `UI-SCR-10～12`），由 QA 擇一。

#### 6.8.5 SDD 框架體檢缺陷（S-xx）與契約條文的對照

| S-xx | 處置 | 契約 |
|------|------|------|
| S-01（P1：FSM 進度沒有文件化的寫入者） | SDD 文件補寫入指令；Console 以 `:freeze` 與批次同步提供生產者 | §1.10.2、§3.1.4 (d)、§3.1.6 |
| S-03 | AT 文法（D-115-16）、`unmapped_at_ids`、CLI rc 6 | §3.1.4 (e)、§3.3.2 |
| S-04 | `spec_file` | §3.1.4 (e)、§3.3.2 |
| S-05（＝G-02） | `fsm_project`、單檔採用、多檔 fail-closed、不再往上層找 | §3.1.4 (e)、§3.1.6 |
| S-06（＝G-16） | 文件漂移由 SDD 側處理；本契約把談判與委派寫成 Bridge 的責任 | §3.1.6 |
| S-09（＝G-17） | 框架目錄的測試殘檔；Console 改讀專案根後不再受污染 | §1.10.4 |
| S-10 | 專案名淨化鏡像與輸出域白名單 | §3.1.4 (b) |
| S-11 | 版本宣告判準；「文中出現該字樣卻解析不出版本」一律拒絕 | §3.1.4 (e) |
| S-12 | `**scenario**:` 欄位優先 | §3.1.4 (e) |
| S-02、S-07、S-08、S-13～S-19 | 不涉及契約 | — |

#### 6.8.6 與 ADR-016 的對齊處置（v1.5 對齊修訂）

**A. 逐項處置**（ADR-016 附錄 A 的 A-1～A-22；「已對齊」＝契約文字已依 ADR 改寫，與 ADR 一致）：

| ADR | 項 | 契約處置 |
|-----|----|----------|
| A-1 | CLI rc 0／1／2／3／4／5；失敗也印單行 JSON | 已對齊：§3.1.4 共通規則 4 的對映表（rc 3⇒409 `fsm_state_conflict`、rc 4⇒422 `sdd_invalid_argument`、rc 5⇒404／422、rc 1⇒502 `sdd_cli_failed`、rc 2⇒500 `sdd_cli_usage`、逾時⇒504 `sdd_cli_timeout`）；SA 初稿的「rc=2⇒409」作廢 |
| A-2 | CLI 旗標、摘要＝正規化文字、缺檔 rc 4 | 已對齊：§3.1.4 (d)、§1.10.2（`--digest`／`--root`／`--approver`／`--json`；16 MiB、UTF-8） |
| A-3 | 引擎子行程只注入 `SDD_PROJECT`；CLI 環境剝除 `BRIDGE_*`／`SDD_*` | 已對齊：§3.1.4 共通規則 1、2、§3.1.6 |
| A-4 | `sdd` 區塊加 `spec_file?`、`root?`、`approver?` | 已對齊：§3.1.6（`root` 由必填改**選填**，預設 `execution_path`） |
| A-5 | `:freeze` 加 `expected_digests`、`docs` 含 TCS、回應帶 `spec_doc_digests` | 已對齊：§3.1.4 (d)、§1.10.2（Console 請求選填穿透 `expectedDigests`，靜默處 #2） |
| A-6 | `/sdd/compile` 的請求／回應欄位、摘要不符＝409、無 `spec_at_dropped` | 已對齊：§3.1.4 (e)（SA 初稿「422 `spec_not_frozen`（內容已變更）」改 409） |
| A-7 | 錯誤 reason 清單；**沒有** `sdd_not_bound` | 已對齊：附錄 B.5（移除 `sdd_not_bound`；新增 `sdd_binding_conflict`；Bridge 側新增 `sdd_block_invalid`、`sdd_invalid_argument`、`sdd_cli_usage`、`sdd_cli_timeout`，`sdd_cli_failed` 改 502） |
| A-8 | 預檢表加 `TEST_CONTRACT_NEGOTIATED` 自癒與 `AUTOCLAUDE_DELEGATED` 回收點 | 已對齊：§3.1.6 預檢表與第 3 點 |
| A-9 | 生命週期：預檢（唯讀）→鎖→FSM 寫入→`_materialize`→spawn；補償；終態在 `handle.lock` 之外 | 已對齊：§3.1.6 建立流程順序與第 4、5 點 |
| A-10 | `GET /sdd/fsm/{project}` 多回 `escalation_provenance`、`fsm_project`，ESCALATION 時回 `recovery` | 已對齊：§3.1.4 (c)、§1.10.4（主控採納 SD 建議，`recovery` 的 `target` 規則見靜默處 #5） |
| A-11 | 專案名：Bridge 鏡像 `fsm_component()`＋輸出域判準 | 已對齊：§3.1.4 (b)（取代 SA 初稿的 `FSM_PROJECT_NAME` regex 與 1～128 字元）；附錄 D.1 |
| A-12 | Backend 綁定欄（含 `sdd_spec_file`）、Console 專案為錨、部分唯一索引、`targetProjectId`、`sdd_binding_conflict`、凍結請求無 `binding` | 已對齊：§0.5 V12（`sdd_project` 為 `VARCHAR(100)`，SA 初稿是 128）、§1.10.1、§1.10.2、§1.10.5、§1.10.8、§3.3.2；**`sddSpecFile` 改為絕對路徑**（SA 初稿是相對 `sddSpecDir`） |
| A-13 | 權杖：backend 屬性、未設行為、<32 字元啟動失敗、`_child_env` 剝除 `SDD_*`、`validate_env`、audit 不記值、compose 預設空 | 已對齊：§3.1.4 共通規則 2、(g)、附錄 D.2 |
| A-14 | 狀態目錄收斂（SDD 側 7 個站點） | 不涉及契約 |
| A-15 | `_POST_FROZEN_STATES` 加 `AUTOCLAUDE_DELEGATED` | 不涉及契約（adapter 內部） |
| A-16 | S-02 PowerShell matcher 與 AUTO_COMPACT 放行 | 不涉及契約 |
| A-17 | 委派退出（D-115-15）：CANCELLED⇒`done`；`done`＝交還控制權；回收點 | 已對齊：§3.1.6 第 3、5 點、§3.1.7 第 1、10 點、E2E-17 第 20、21 列（SA 初稿的「取消不動 FSM」與 E2E 第 18 列作廢） |
| A-18 | `playbook-ref`＝`run:<run_id>` | 已對齊：§3.1.6 `--reason` 表 |
| A-19 | AT 文法與歸屬（D-115-16）；E 類 AT 命名；宣告位置只限 AC 映射列第三欄與 Gherkin 標頭 | 已對齊：§3.1.4 (e)、§3.3.2 第 10 點、E2E-17 夾具（SA 初稿的 `AT-[\w\-]+` 作廢） |
| A-20 | 逆向 RTM：unmapped 計入 `total_at`、不進 AC 桶；`fully_covered` 在有 unmapped 時為 `false` | 已對齊：§1.10.3、§3.1.4 (f)、§4.7.2（RTM 回應新增 `unmappedAtIds`、`at.unmapped`） |
| A-21 | 白名單 | 不涉及契約（D-115-05） |
| A-22 | 預設階段名 `Stage-<n>`、六種 `--reason` 組字、輸入清理 | 已對齊：§1.10.2、§3.1.4 (d)、§3.1.6 `--reason` 表 |

**B. ADR 沒寫、契約暫定而需確認的靜默處**（#1、#2、#3、#6、#14 已由主控以 D-115-18 裁決定案〔SA 交卷後〕；其餘請 SD 或 Dev 在落地時確認，與本表不同處以確認後的契約為準，並回寫本表）：

| # | 靜默處 | 契約暫定 |
|---|--------|----------|
| 1 | 編輯 `sdd_project` 的 API（主控已確認，D-115-18 ①）：ADR-016 §7.2 說「可編輯」「編輯即改綁」「UI 與稽核屬 SA 契約」，但沒給端點；Phase 1+2 的專案更新端點不在本契約範圍 | 新增 `PUT /api/v1/projects/{id}/sdd-binding`（#48；OPERATOR 以上；`operationId=updateProjectSddBinding`；稽核 `project.sdd.bind`）；`OpenApiIT` 路徑 58→61、操作 67→70。替代案：改擴充 Phase 2 的 `PUT /projects/{id}`（不在本文件範圍） |
| 2 | `expectedDigests` 在 Console 層（主控已確認，D-115-18 ⑤） | Console 請求選填穿透給 Bridge 的 `expected_digests`；v1.5 畫面不送（沒有顯示規格摘要的元件）。若要由畫面送，需另加「讀取現檔摘要」的端點（未排入本輪） |
| 3 | 併入既有專案的規則（專案層 `signedOff` 不動：主控已確認，D-115-18 ②）：ADR-016 §7.2 把「排序與編號」交給本契約 | 新目標接在既有未刪目標之後、`dependsOn` 只在草稿內、專案欄位不動、**專案層 `signedOff` 不動**（須另以 Phase 2 專案 signoff；替代案是 confirm 同時把目標專案標為已簽核，但那會讓匯入記錄的 signoff 越權涵蓋人工建立的內容）、`executionPath` 在 `ParseOptions` 仍必填（帶目標專案的值）、目標欄位為 NULL 時以請求值為準、confirm 回 201 |
| 4 | `:freeze` 的 `docs` 檢查歸屬與失敗形狀：ADR-016 §6.3 ① 把「已綁定 `sdd_spec_file` 時它必須在 `docs[]` 內」寫在 Bridge 檢查欄，但該資訊在 Console DB，Bridge 沒有；「含 TCS」的失敗形狀也沒寫 | 前者由 Backend 擋（400 `errors[0].field=docs`）；Bridge 只檢查「含 TCS」，失敗為 422 `sanitization_failed`＋`violations=[{field:"docs",rule:"missing_tcs"}]`（沿用既有 422 封包形狀；規則碼採 Dev-Bridge 實作的 `missing_tcs`，ADR 靜默） |
| 5 | `recovery.target` 的決定規則：ADR-016 §5.3 只給模板，並說 `ESCALATION_FINAL` 的目標可能不同 | 委派失敗（`escalation_provenance.source=autoclaude_delegated_failed`）＝`IMPLEMENTATION`；Bridge 無法判定時整個 `recovery` 省略，Console 不猜 |
| 6 | 路徑參數含 `/` 的原名：ADR-016 §7.4 要求原名與標準鍵等價，但 `%2F` 進路由前已被還原成 `/`，單一路徑段的 `{project}` 對它不匹配 | **主控裁決降級為已知邊界（D-115-18 ③）**：Bridge 的專案路徑只收不含 `/` 的名稱（淨化後的 FSM 鍵），含 `/` 的原名不可由 URL 定址；契約**不要求** `{project:path}`；影響與避開方式見 §3.1.7 第 11 點 |
| 7 | `spec_file` 與 `spec_path` 的關係：ADR-016 §7.2 回填取既有欄位 `spec_path`，§8.3 另增 `spec_file` | `spec_path`＝絕對路徑（Console 填 `sddSpecFile`、父目錄填 `sddSpecDir`）；`spec_file`＝相對 `spec_dir` 的 POSIX 路徑 |
| 8 | Bridge 錯誤封包的 `detail` 型別：ADR 的 `detail.pair`、`detail.current_state`、`detail.reason` 隱含 `detail` 是物件 | `fsm_state_conflict`、`spec_digest_changed` 的 `detail` 為物件；其餘 reason 的 `detail` 仍是字串；SA 初稿的頂層 `current_state`／`doc` 等欄位作廢（Dev-Bridge 目前另在封包頂層重複放同名欄位作過渡相容；Backend 的 `BridgeClient` 一律只讀 `detail`，不依賴頂層欄位） |
| 9 | `warnings` 的形狀與 Console 轉譯：ADR 只說「201 的 `warnings`」「compile 回應 `warnings`」「adapter 出聲」 | Bridge 的 `warnings` 項為 `{code, detail}`；Console 轉入 execute 201 的 `warnings[]`（`sdd_frozen_digest_absent`）與解析結果 `warnings[]`（`state_dir_not_ignored`；`frozen_digest="absent"`⇒`frozen_digest_absent`） |
| 10 | `approver` 的取值：ADR-016 C-1 說「匯入記錄的核准人」 | 範圍內 SDD 來源任務的 `signedOffBy`（承襲自匯入記錄；多值取排序最前者），為空取 JWT subject |
| 11 | alert 碼：ADR 只命名 `SDD_SYNC_STATE_DRIFT` | 沿用 SA 的 `SDD_FSM_SYNC_FAILED` 表示其他非零失敗；捨棄 SA 初稿的 `SDD_FSM_SYNC_SKIPPED`、`SDD_FROZEN_DIGEST_MISSING`（後者改由 201 `warnings` 承擔） |
| 12 | Console `GET /engines/sdd` 的 `project` 參數驗證：ADR 規定 Backend 不淨化 | 1～200 字元（專案名上限）、不含控制字元，其餘交 Bridge |
| 13 | 錯誤的 `details` 鍵：ADR 只給 reason 名稱與 Bridge 的 `detail` | `sdd_binding_conflict`：`cause`（`already_bound_elsewhere`／`target_bound_differently`／`request_differs_from_target`）、`holderProjectId`、`sddProject`、`field`；`sdd_fsm_state_conflict` 另增 `runId`、`runStatus`、`cause`（`foreign_delegation`） |
| 14 | `:resume`／`/restore` 的權杖：ADR-016 §9 只要求 `:freeze` 與含 `sdd` 的建立請求帶 `X-Bridge-Token`，但這兩個動作也會寫 FSM（`delegate-enter` 重進） | **主控已裁決擴大（D-115-18 ④）**：SDD run 的 `:resume` 與 `/restore` 也須帶權杖，ADR §9 的兩個呼叫由此成為四個（缺／錯同 503／403），見 §3.1.4 共通規則 2、§1.2.4～§1.2.6、§1.2.10、§3.1.6 第 7 點；ADR 本文待 SD 同步。仍屬 §3.1.7 第 8 點的誠實劃界（Bridge 本身無認證，Architecture §12 L-6） |

**C. 延後（只登記，本輪不做；沿用 ADR-016 §14.1）**：Console「退回修改」（須改 `_HAPPY_PATH` 與 TLA）、Console 內的 FSM init／gate／`resume-from-escalation` 恢復動詞（再開症狀：使用者回報「ESCALATION 後要在終端機操作太難」）、`negotiate-exit underspecified` 的畫面、「解除綁定」端點（改綁已可由 §1.10.7 達成）、FSM 狀態檔的跨行程鎖、R-9.20.3 的 oracle 獨立性。

---

## 附錄 A　狀態機速查（本期涉及的部分）

**A.1 執行批次**（六態寫入 PG；Bridge 八態折疊）

| 轉移 | 觸發 |
|------|------|
| `INITIALIZING→RUNNING` | Bridge 引擎啟動（`status RUNNING`） |
| `RUNNING→PAUSED` | pause 後在步驟邊界（Bridge 先 `PAUSING`，折為 `RUNNING`） |
| `PAUSED→RUNNING` | resume／restore／審核 `APPROVE` |
| `RUNNING／PAUSED→CANCELLED` | cancel／審核 `REJECT`（Bridge 先 `CANCELLING`，折為 `RUNNING`；`PAUSED` 即時收尾） |
| `RUNNING→COMPLETED` | 引擎正常結束 |
| `RUNNING→FAILED` | 升級（ESCALATION）、Token halt、異常結束、Bridge 孤兒回收 |
| 終態或 `PAUSED→RUNNING` | restore（終態 run 重新進行；SSE 須重連；`PAUSED` 的 restore 依賴 Bridge 修復，§1.2.10） |

**A.2 審核項**：`PENDING→APPROVED／REJECTED／RETRIED／SKIPPED`（人工決定）；`PENDING→REJECTED`（系統自動關閉：新批次取代、cancel、restore）；`PENDING→APPROVED`（以手動 resume 處理）。

**A.3 匯入記錄**：見 §1.1 的狀態圖與表。

**A.4 專案／目標／任務**：手動 API 遵守 PRD 附錄 B；執行引擎事件與審核決定造成的結果見 §3.5.2、§3.5.3（含 R-goal 與人工判定優先）。

---

## 附錄 B　錯誤 `reason` 常數總表（前後端共用；逐字）

HTTP 狀態與端點見各小節。**404 沿用 Phase 2：`reason` 省略，只有 `message`（樣板見 B.3）。**

### B.1 Phase 1+2 既有（不變）

| HTTP | reason |
|------|--------|
| 400 | `MALFORMED_REQUEST_BODY` |
| 401 | `UNAUTHENTICATED`、`TOKEN_EXPIRED`、`TOKEN_INVALID`（登入端點另有 `INVALID_CREDENTIALS`、`INVALID_REFRESH_TOKEN`） |
| 403 | `ACCESS_DENIED` |
| 409 | `已 signoff`、`目前狀態不可重試`、`RUNNING 狀態的任務不可刪除` 等 Phase 2 常數 |
| 400／409 | `命令含禁用字元`（400）、`依賴成環`（400；執行時偵測到成環為 409，同字串） |

### B.2 Phase 3～6 新增

| 區 | HTTP | reason（逐字） | `details` 鍵 |
|----|------|----------------|--------------|
| 通用 | 429 | `超過每分鐘 100 次請求上限` | `limit,windowSeconds,retryAfterSeconds` |
| 通用 | 502 | `引擎橋接服務無法連線` | — |
| 通用 | 504 | `引擎橋接服務逾時` | — |
| 通用 | 502 | `引擎橋接服務錯誤` | `bridgeStatus,bridgeReason` |
| 認證（前端合成） | 503 | `upstream_unavailable` | —（**後端永不回此 reason**：`POST /auth/refresh` 因網路錯誤、5xx、429 暫時失敗時，前端合成 `ApiError{status:503, reason:"upstream_unavailable", message:"伺服器暫時無法連線，請稍後再試"}`，不登出；§2.8，v1.2） |
| 匯入 | 400 | `未提供檔案` | — |
| 匯入 | 400 | `檔案是空的` | — |
| 匯入 | 413 | `檔案超過 10MB 上限` | `limitBytes` |
| 匯入 | 415 | `只支援 .md／.pdf／.docx 檔案` | `extension,allowed` |
| 匯入 | 422 | `檔案內容與副檔名不符` | `extension` |
| 匯入 | 422 | `檔案不是有效的 UTF-8 文字` | — |
| 匯入 | 422 | `PDF 已加密，無法擷取文字` | — |
| 匯入 | 422 | `檔案已損毀，無法讀取` | — |
| 匯入 | 422 | `無法從檔案擷取文字` | — |
| 匯入 | 409 | `解析中，請稍候` | `status` |
| 匯入 | 409 | `已 signoff，不可重新解析` | `signedOffBy,signedOffAt` |
| 匯入 | 409 | `匯入記錄狀態不允許此操作` | `action,status` |
| 匯入 | 422 | `解析結果未通過有界閘` | `path`；`errors[]` 項目帶 `gate,detail,location` |
| 匯入 | 422 | `SDD 規格檢查未通過` | `bridgeReason,detail` |
| 匯入 | 409 | `草案已失效，請重新解析` | `draftId` |
| 匯入 | 409 | `草案尚未 signoff，不可確認匯入` | `status,signedOff` |
| 匯入 | 409 | `已匯入` | `projectId` |
| 執行 | 409 | `未經人工審批的草案不可執行`（PRD 逐字） | `unsignedProjectId,unsignedGoalIds,unsignedTaskIds` |
| 執行 | 409 | `專案正在執行中` | `projectId,runId` |
| 執行 | 409 | `專案狀態不允許執行` | `status` |
| 執行 | 400 | `所選範圍不合法` | `invalidGoalIds,invalidTaskIds` |
| 執行 | 409 | `所選任務或目標已完成` | `goalIds,taskIds` |
| 執行 | 409 | `所選目標依賴未完成的前置目標` | `missingGoalIds` |
| 執行 | 409 | `沒有可執行的任務` | — |
| 執行 | 422 | `步驟 prompt 超過 20000 字元上限` | `taskId,stepId,length,limit` |
| 執行 | 422 | `評估指令含禁用字元` | `taskId,chars` |
| 執行 | 422 | `評估指令不在可執行檔白名單` | `taskId,executable` |
| 執行 | 422 | `expectedOutputRegex 無法編譯` | `taskId` |
| 執行 | 422 | `範圍任務數超過單一批次上限 500` | `count,limit` |
| 執行 | 422 | `任務最大重試次數超過上限 20` | `taskId,maxRetries,limit` |
| 執行 | 409 | `同專案同路徑已有執行中的批次` | `holderRunId` |
| 執行 | 422 | `引擎拒絕此請求` | `bridgeReason,violations` |
| 執行 | 409 | `目前執行狀態不允許此操作` | `action,runStatus,bridgeStatus` |
| 執行 | 409 | `找不到可續跑的 checkpoint` | — |
| 執行 | 409 | `引擎端已無此執行（工作區可能已清除）` | `runId` |
| 執行 | 409 | `只能還原專案最新的執行批次` | `latestRunId,latestRunNumber` |
| 執行 | 409 | `審核項已處理` | `status,decidedBy,decidedAt` |
| 執行 | 409 | `此審核項不允許該決定` | `kind,decision,allowedDecisions` |
| 專案 | 409 | `project_executing` | `projectId,runId`（刪除目標／任務時專案有進行中批次，§1.6.3；**不是** execute 的 `專案正在執行中`；v1.2） |
| 專案 | 409 | `project_not_deleted` | `projectId,status`（復原一個沒被軟刪除的專案，§1.6.1；v1.2） |
| 專案 | 409 | `restore_window_expired` | `projectId,deletedAt,retentionDays`（軟刪除已超過保留期，§1.6.1；v1.2） |
| 監控 | 400 | `時間範圍不合法` | `from,to`（`task-totals` 另帶 `maxDays`，§1.3.8） |
| 監控 | 400 | `不支援的報表格式` | `format,supported` |
| 設定 | 403 | `僅 ADMIN 可揭露敏感參數` | — |
| 設定 | 400 | `參數值不符合型別或驗證規則` | `valueType,validationRule,min,max,options` |
| 設定 | 400 | `halt_threshold_pct 必須大於 compact_threshold_pct`（PRD 逐字） | `compactThresholdPct,haltThresholdPct` |
| 設定 | 400／422 | `目標位址未通過 SSRF／allowlist 檢查`（儲存、匯入時 400；測試連線 422） | `host,violation`（`violation` ∈ `malformed_url,scheme,userinfo,loopback,link_local,private_ip,not_in_allowlist,dns_rebinding`） |
| 設定 | 409 | `敏感參數更新需二次確認（confirm=true）` | `category,key` |
| 設定 | 409 | `敏感參數重置需二次確認（confirm=true）` | `category,key` |
| 設定 | 400 | `設定檔格式錯誤` | `problem` |
| 設定 | 413 | `設定檔超過 1MB 上限` | `limitBytes` |
| 設定 | 415 | `只接受 JSON 設定檔` | — |

### B.3 404 訊息樣板（`reason` 省略）

`匯入記錄不存在或已刪除：<id>`、`專案不存在或已刪除：<id>`、`執行批次不存在或已刪除：<id>`、`執行批次不存在或不屬於此專案：<id>`、`checkpoint 不存在或不屬於此執行：<id>`、`審核項不存在或不屬於此執行：<id>`、`告警不存在：<id>`、`設定分類不存在：<category>`、`設定鍵不存在：<category>.<key>`；v1.2 新增 `專案不存在或已清除：<id>`（`POST /projects/{id}/restore` 找不到該 id 或已被清除排程實體刪除，§1.6.1）。

### B.4 回應本文的 `reason` 欄位值（**不是** `ApiError.reason`；v1.4）

`GET /api/v1/engines/sdd` 的 200 回應本文有一個 `data.reason` 欄位（§1.7.1），值是英文識別字，描述「引擎目前的狀態」；它**不是錯誤封包**，不進 B.2，前端以它選顯示文案（§4.3 M-20），不得拿它做 HTTP 錯誤處理（該端點在引擎不可用時仍回 200）：

| 值 | `available` | 意義 |
|----|:-----------:|------|
| `bridge_unreachable` | false | Bridge 連線失敗或逾時 |
| `sdd_unavailable` | false | Bridge 回 503 `sdd_unavailable`（`SDD_ROOT` 無效、找不到 SDD 版本目錄） |
| `bridge_error` | false | Bridge 回其他非 2xx，或回應本文不是預期的形狀 |
| `fsm_not_found` | true | 帶了 `project`，找不到該專案的 FSM 狀態檔 |
| `fsm_state_unreadable` | true | 帶了 `project`，該狀態檔讀不動（YAML 壞掉、不是 UTF-8、缺 `fsm_state` 根節點、巢狀過深） |
| `sdd_root_rejected` | true | （v1.5）帶了 `projectId`，而 Bridge 對該專案的 `root` 回 422 `sanitization_failed`（路徑不在允許的根目錄內、或已不存在）；`fsm=null`、`projects=[]`，`version` 保留（§1.10.4） |

`fsm_not_found`、`sdd_unavailable`、`fsm_state_unreadable` 同時也是 Bridge 自己錯誤封包的 `reason`（§3.1.3）；console-api 把它們轉成上表欄位的值，而不是轉成 HTTP 錯誤。

### B.5 v1.5 新增（整合輪 115；已與 ADR-016 對齊）

**console-api 的 `ApiError.reason`**（英文識別字；§0.3 第 8 點；前後端各一份常數、逐字）：

| HTTP | reason | `details` 鍵 | 端點與觸發 |
|------|--------|--------------|------------|
| 409 | `sdd_fsm_state_conflict` | `currentState`、`expectedState?`（字串或陣列）、`runId?`、`runStatus?`、`cause?`（`foreign_delegation`） | freeze：`current_state` 不是 `HUMAN_PENDING`；execute／resume／restore（SDD run）：預檢表判 409（§3.1.6）——`current_state` 不在可進入的集合，或回收點判活躍／外來委派（`runId`、`runStatus`、`cause`） |
| 409 | `sdd_fsm_not_found` | `sddProject` | freeze／execute：有效 FSM 專案沒有狀態檔（§1.10.2、§3.1.6） |
| 409 | `sdd_spec_digest_changed` | `pair`（`expected_vs_file`｜`frozen_vs_file`｜`import_vs_file`）、`doc`、`expectedDigest?`、`frozenDigest?`、`importDigest?`、`currentDigest`（沒有的鍵省略） | freeze 帶 `expectedDigests`（`expected_vs_file`）；execute／resume／restore（SDD run）的預檢（`frozen_vs_file`、`import_vs_file`；§3.1.6）。路徑 A 的內容不符走 422 `SDD 規格檢查未通過`，不是這個 reason（§3.3.2 第 8 點） |
| 409 | `sdd_binding_conflict` | `cause`（`already_bound_elsewhere`｜`target_bound_differently`｜`request_differs_from_target`）、`sddProject?`、`holderProjectId?`、`field?` | freeze 的綁定唯一性（第 5 項）、`PUT /projects/{id}/sdd-binding`、路徑 A 匯入帶或不帶 `targetProjectId` 的 parse／confirm（§1.10.5、§1.10.7、§1.10.8） |
| 503 | `sdd_write_disabled` | — | freeze 或 execute（SDD 批次）：backend 或 Bridge 沒有設定寫入權杖；resume／restore（SDD run，D-115-18）：Bridge 沒有設定寫入權杖 |
| 404 | `rtm_not_found` | `runId` | `GET /executions/{runId}/rtm`：批次存在但沒有追溯報告（**404 的 `reason` 省略慣例的唯一例外**，§0.3 第 8 點） |

（SA 初稿的 `sdd_not_bound` **已移除**：D-115-14 之後不存在「未綁定」狀態，核准凍結的請求也沒有 `binding` 欄。）

**沿用既有常數的 SDD 情形**（不新增常數）：`SDD 規格檢查未通過`（`details={bridgeReason, detail}`；execute 的預檢第 3 項與路徑 A 同一個轉譯；`bridgeReason` 新增可能值 `spec_digest_changed`）、`引擎拒絕此請求`（`details={bridgeReason, violations[]}`；`:freeze` 的 `root`／`docs[i]`／`approver`／`reason` 不合法、`rtm_unreadable`、`sdd_block_invalid`）、`引擎橋接服務錯誤`（`details={bridgeStatus, bridgeReason}`；Bridge 403 `sdd_write_forbidden`、500 `sdd_cli_usage`、502 `sdd_cli_failed`、504 `sdd_cli_timeout`）。

**Bridge 自己的錯誤封包 `reason`**（v1.5 新增；形狀 `{"code","reason",…}`，不進上表；ADR-016 §4.1、§6.3、§9、§10）：

| HTTP | reason | 附加欄位 | 觸發 |
|------|--------|----------|------|
| 503 | `sdd_write_disabled` | `detail`（字串） | Bridge 沒設寫入權杖（§3.1.4 共通規則 2）；適用四個呼叫：`:freeze`、帶 `sdd` 的建立、SDD run 的 `:resume`、`/restore`（D-115-18） |
| 403 | `sdd_write_forbidden` | — | 權杖缺漏或不符（缺與錯同一個 reason）；同上四個呼叫 |
| 409 | `fsm_state_conflict` | `detail` 物件：`current_state`、`expected_state?`、`run_id?`、`run_status?`、`reason?`（`foreign_delegation`） | `:freeze` 前置不符；批次預檢表與回收點；CLI rc 3；`resume`／`restore` 的 FSM 檢查 |
| 409 | `spec_digest_changed` | `detail` 物件：`pair`、`doc`、`expected_digest?`、`frozen_digest?`、`import_digest?`、`current_digest` | `:freeze` 的 `expected_digests`、`/sdd/compile`、批次預檢第 3、4 項、`resume`／`restore` |
| 404 | `fsm_not_found` | `project` | 狀態檔不存在（`GET /sdd/fsm/{project}`、`:freeze`、CLI rc 5 `state_not_found`） |
| 422 | `fsm_state_unreadable` | `detail` | 狀態檔讀不動（YAML 壞掉、CLI rc 5 `state_unreadable`） |
| 422 | `sdd_invalid_argument` | `detail`（字串） | `approver`／`reason` 值域不合、CLI rc 4 |
| 422 | `sdd_block_invalid` | `detail`／`violations[]` | `sdd` 區塊結構不合：`spec_dir` 不在 `root` 之下、任務缺 `spec_digest`（Backend bug） |
| 422 | `spec_not_frozen`／`spec_tainted`／`spec_format_version_unsupported`／`spec_not_found`／`spec_ambiguous`（既有；v1.5 擴充情形） | `detail` | `spec_not_frozen` 新增：狀態檔不唯一、`fsm_project` 找不到、規格檔不在凍結清單。**凍結後內容已變更不再是 422**（改 409 `spec_digest_changed`） |
| 500 | `sdd_cli_usage` | `detail` | CLI rc 2（Bridge 自己的 bug，測試必須零次出現） |
| 502 | `sdd_cli_failed` | `detail`（ASCII，≤ 200 字） | CLI rc 1、無法啟動 |
| 504 | `sdd_cli_timeout` | `detail` | CLI 超過 20 秒 |
| 404 | `rtm_not_found` | `run_id` | `GET /autoclaude/runs/{id}/rtm` 沒有報告 |
| 422 | `rtm_unreadable` | `detail` | 報告檔壞掉 |

**回應本文的警告碼與 alert 碼**（不是錯誤）：`ExecutionRunResponse.warnings[].code`＝`sdd_governance_inactive`（`cause` 為 `not_bound`、`token_not_configured`、`mixed_scope`、`spec_mismatch`、`duplicate_step_id`，§1.10.5）、`sdd_frozen_digest_absent`（無 `cause`）；`ParseWarning.code`＝`at_unmapped`、`frozen_digest_absent`、`state_dir_not_ignored`（§3.3.2）；Bridge run alert `code`＝`SDD_SYNC_STATE_DRIFT`（warning）、`SDD_FSM_SYNC_FAILED`（error）（§3.1.6）。

---
## 附錄 C　設定鍵目錄（50 鍵；`ConfigCatalog` 與 V5 `validation_rule` 的唯一真相源）

欄位：`validationRule`＝Java 正規表示式（對完整字串比對，寫入 `system_configs.validation_rule`）；`min／max`＝數值範圍（含邊界；`FLOAT` 亦同）；`effect`：**E**＝ENGINE、**C**＝CONSOLE、**S**＝STORED_ONLY、**U**＝UNVERIFIED（定義見 §1.5）。除特別註明，`impactNote` 為 null。「新批次起生效」指已在跑的批次沿用啟動時的值（引擎設定在 spawn 時物化）。

### C.1 `model`（10）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote`（US-S-08） |
|----|------|------|------------------------------|:------:|--------------------------|
| `provider` | ENUM | `ANTHROPIC` | `^(ANTHROPIC\|OPENAI\|LOCAL\|CUSTOM)$` | S | 僅為 Console 抽象層欄位；引擎是 MiniMax＋Claude CLI 雙腦，不會依此切換 |
| `apiUrl` | STRING | `https://api.minimax.io/v1/text/chatcompletion_v2` | `^https?://[^\s/?#][^\s]*$`；另過 SEC-04（§1.5.7 的 1～5） | E（`apiKey` 有值時） | 須填**完整的 chat-completions 端點 URL**（後端不補路徑）；原樣當引擎 `minimax.base_url`，也用於匯入解析（路徑 B）與測試連線；host 須同時在 Console 與 Bridge 的 allowlist 內；新批次起生效 |
| `apiKey` | ENCRYPTED | （空） | `^.{0,512}$` | E | 加密儲存；新批次起使用新金鑰；留空＝不再帶 MiniMax 設定（引擎不建 Brain，AI 演化提案停用） |
| `name` | STRING | `MiniMax-M2.7` | `^[A-Za-z0-9._:/\-]{1,100}$` | E（`apiKey` 有值時） | 新批次起生效；也用於匯入解析 |
| `maxTokensPerRequest` | INTEGER | `8192` | `^[1-9][0-9]{0,5}$`；1～200000 | C | 只影響匯入解析（路徑 B）的 `max_tokens`；引擎無對應欄位 |
| `temperature` | FLOAT | `0.3` | `^[0-9](\.[0-9]+)?$`；0～2 | C | 只影響匯入解析（路徑 B） |
| `topP` | FLOAT | `0.9` | `^[01](\.[0-9]+)?$`；0～1 | C | 只影響匯入解析（路徑 B） |
| `timeout` | INTEGER | `120` | `^[1-9][0-9]{0,2}$`；1～600 | E | 引擎 `minimax.timeout_seconds` 與匯入解析逾時；測試連線上限 10 秒；經 nginx 部署時建議 ≤ 150（nginx 對匯入的讀取逾時為 180 秒，§0.7） |
| `rateLimitPerMinute` | INTEGER | `60` | `^[1-9][0-9]{0,4}$`；1～10000 | S | 目前不影響任何呼叫 |
| `enableKernelBrain` | BOOLEAN | `false` | `^(true\|false)$` | E（`apiKey` 有值時） | 有金鑰時，引擎的 Brain 會在步驟失敗且尚有重試次數時先改寫 prompt 再重試；Brain 呼叫失敗則該步驟直接升級。與 agent.enableAutoMutation 及自治等級 ≥6 共用引擎鍵 minimax.enable_kernel_brain（任一為真即開）；沒有金鑰時 Console 不送（送了引擎會啟動失敗）；新批次起生效 |

### C.2 `agent`（9）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote` |
|----|------|------|------------------------------|:------:|--------------|
| `defaultAutonomyLevel` | INTEGER | `3` | `^([1-9]\|10)$`；1～10 | C | 只改之後匯入與執行表單的預設值，不改動既有專案 |
| `maxConcurrentTasks` | INTEGER | `3` | `^[1-9][0-9]?$`；1～32 | S | 引擎序列執行，目前不生效（Architecture L-1） |
| `taskTimeout` | INTEGER | `600` | `^[1-9][0-9]{1,4}$`；10～86400 | E | 新批次的單步逾時（秒）；同時是「任務執行過長」告警門檻的基準（×`monitor.alertTaskDurationMultiplier`） |
| `maxRetries` | INTEGER | `3` | `^([0-9]\|1[0-9]\|20)$`；0～20 | E | 新批次的預設最大重試次數（每個任務自己的 `maxRetries` 優先） |
| `retryBackoffMs` | INTEGER | `5000` | `^[0-9]{1,7}$`；0～3600000 | S | 引擎無對應欄位 |
| `retryBackoffMultiplier` | FLOAT | `2.0` | `^([1-9]\|10)(\.[0-9]+)?$`；1～10 | S | 引擎無對應欄位 |
| `checkpointInterval` | INTEGER | `5` | `^[1-9][0-9]{0,3}$`；1～1000 | S | Bridge 於每個步驟邊界自行記錄歷史快照，此值不生效 |
| `enableAutoMutation` | BOOLEAN | `false` | `^(true\|false)$` | E（`apiKey` 有值時） | 對映引擎 minimax.enable_kernel_brain（Brain 逐步校正：失敗步驟先改寫 prompt 再重試），與 model.enableKernelBrain 任一為真即開；自治等級 ≥6 一律視為開啟。需要 model.apiKey：沒有金鑰時不送，批次回報 UNAVAILABLE_NO_API_KEY；新批次起生效（§3.4.2） |
| `enableSelfEvolution` | BOOLEAN | `false` | `^(true\|false)$` | S | 引擎沒有演化開關：有金鑰時失敗型 ESCALATION 一律由 Brain 產生演化提案，只寫引擎日誌、不套用也不重載（max_evolutions／require_evolution_signoff 在引擎執行路徑上沒有讀者，Console 不送）。本鍵只影響沒有金鑰時批次回報 OFF 或 UNAVAILABLE_NO_API_KEY（§3.4.2；E2E 以 model.apiKey 為空關閉演化，§5.0.2） |

### C.3 `execution`（10）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote` |
|----|------|------|------------------------------|:------:|--------------|
| `globalTokenBudget` | LONG | `1000000` | `^[1-9][0-9]{0,11}$`；1～999999999999（規則最多 12 位；v1.2 更正：v1.1 寫的上限 1000000000000 有 13 位、與規則矛盾，以規則為準，B1-1） | C | 新批次的預設 Token 預算；不改動既有批次 |
| `tokenBudgetWarningThreshold` | FLOAT | `0.8` | `^0\.[0-9]{1,2}$`；0.01～0.99 | C | 即時生效於進行中的批次（告警每次評估時讀取） |
| `maxParallelGoals` | INTEGER | `2` | `^([1-9]\|1[0-6])$`；1～16 | S | 引擎序列執行，目前不生效 |
| `dagSchedulerStrategy` | ENUM | `TOPOLOGICAL` | `^(TOPOLOGICAL\|PRIORITY\|SHORTEST_FIRST)$` | C | 影響新批次同層目標的排序 |
| `enableRollback` | BOOLEAN | `true` | `^(true\|false)$` | S | 引擎無對應欄位 |
| `logRetentionDays` | INTEGER | `90` | `^[1-9][0-9]{0,3}$`；1～3650 | C | 日誌與 Bridge 工作區的保留天數（清理排程依此） |
| `compactThresholdPct` | INTEGER | `80` | `^([1-9]\|[1-9][0-9])$`；1～99；**須小於 `haltThresholdPct`** | E | Token Guard：context 達此百分比觸發 `/compact`；新批次起生效；不得經 Console 提高上限以繞過安全收斂（NFR-SEC-05） |
| `haltThresholdPct` | INTEGER | `90` | `^([2-9]\|[1-9][0-9]\|100)$`；2～100；**須大於 `compactThresholdPct`** | E | Token Guard：context 達此百分比儲存 checkpoint 並停機；新批次起生效 |
| `autoResume` | BOOLEAN | `true` | `^(true\|false)$` | E | halt 後引擎是否等待並自動續跑（會讓 run 長時間維持 RUNNING）；新批次起生效 |
| `maxAutoResumes` | INTEGER | `10` | `^([1-9]\|[1-9][0-9]\|100)$`；1～100 | E | 單次 playbook 最多自動恢復次數；新批次起生效 |

### C.4 `monitor`（6）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote` |
|----|------|------|------------------------------|:------:|--------------|
| `refreshIntervalMs` | INTEGER | `10000` | `^(1[0-9]{4}\|[2-5][0-9]{4}\|60000)$`；10000～60000 | C | 前端輪詢間隔（通知摘要、監控儀表板）；下限 10 秒：同一使用者的所有頁面共用每分鐘 100 次的限流額度（§0.4 第 4 點） |
| `alertConsecutiveFailures` | INTEGER | `3` | `^([2-9]\|1[0-9]\|20)$`；2～20 | C | 「連續任務失敗」告警門檻；即時生效 |
| `alertAgentTimeoutSec` | INTEGER | `300` | `^[0-9]{2,5}$`；30～86400 | C | 「Agent 無回應」告警門檻（秒）；即時生效 |
| `alertTaskDurationMultiplier` | FLOAT | `2.0` | `^([1-9]\|1[0-9]\|20)(\.[0-9]+)?$`；1～20 | C | 「執行時間過長」＝`agent.taskTimeout` × 此倍數；即時生效 |
| `enableEmailNotification` | BOOLEAN | `false` | `^(true\|false)$` | S | 目前沒有郵件發送功能，只儲存 |
| `notificationEmail` | STRING | （空） | `^$\|^[^@\s]+@[^@\s]+\.[^@\s]+$` | S | 同上 |

### C.5 `autoclaude`（11）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote` |
|----|------|------|------------------------------|:------:|--------------|
| `engineUrl` | STRING | `http://engine-bridge:8081` | `^https?://[A-Za-z0-9.\-]+(:[0-9]{1,5})?/?$` | C | 所有 Bridge 呼叫改走新位址；填錯會讓執行與監控失效 |
| `healthCheckPath` | STRING | `/health/deep` | `^/[A-Za-z0-9_\-./]*$` | C | Bridge 健康探測路徑（Agent 可用率、頂列連線燈）；預設 /health/deep：Bridge 行程可達但引擎自檢未通過（503）也算失敗，改回 /health 只檢查行程是否存活 |
| `eventBusType` | ENUM | `INTERNAL` | `^(INTERNAL\|KAFKA\|RABBITMQ)$` | S | 引擎只有 INTERNAL |
| `dalBackend` | ENUM | `FILE` | `^(FILE\|IN_MEMORY\|POSTGRESQL)$` | S | Bridge 固定用檔案型 checkpoint（`yaml_only`），此值不生效（ADR-001 D13） |
| `playbookPath` | STRING | `./playbooks` | `^.{1,500}$` | S | Bridge 自行管理 playbook 檔，不生效 |
| `claudeCommand` | STRING | `claude` | `^[A-Za-z0-9_.\-/\\:]{1,200}$`（不可含空白，引擎不做 shlex 切分；**允許 Windows 絕對路徑與 `.exe`**：反斜線、冒號、點皆在字元集內） | E | 新批次起生效；E2E 設為 mock claude 的**絕對路徑**（Windows：`<REPO_ROOT>\.venv\Scripts\aisdlc-mock-claude.exe`，§5.0.2），不依賴 Bridge 行程的 `PATH`；填錯會讓每個步驟在第一秒失敗 |
| `claudeExtraArgs` | STRING | （空） | `^[A-Za-z0-9_.=:,/@\- ]{0,500}$`（以空白切成陣列，每段須符合 §3.4.2） | E | 新批次起生效 |
| `claudeContinueFlag` | STRING | `--continue` | `^--[A-Za-z0-9\-]{1,60}$` | E | 新批次起生效 |
| `claudeEncoding` | STRING | `utf-8` | `^[A-Za-z0-9_\-]{1,30}$` | E | 新批次起生效 |
| `dbDsn` | ENCRYPTED | （空） | `^.{0,512}$` | S | Bridge 固定 `yaml_only`，不生效 |
| `dualReadResolution` | ENUM | `yaml_wins` | `^(yaml_wins\|db_wins\|fail_loud)$` | S | 同上 |

v1.4（D-17）：`healthCheckPath` 的預設由 `/health` 改為 `/health/deep`（種子預設與既有列的校正見 §0.5 V11）；它的 `impactNote` 由 V11 寫進 `impact_note`，**以本表原文為準、逐字相同**（故不含反引號）。

### C.6 `sdd`（4）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote` |
|----|------|------|------------------------------|:------:|--------------|
| `engineUrl` | STRING | `http://engine-bridge:8081` | 同 `autoclaude.engineUrl` | C | 匯入路徑 A 的 `/sdd/compile` 位址 |
| `specFormat` | ENUM | `YAML` | `^(YAML\|JSON\|TOML)$` | U | 與 `/sdd/compile` 行為的對映尚未驗證 |
| `workflowEngine` | ENUM | `DYNAMIC` | `^(STATIC\|DYNAMIC\|ADAPTIVE)$` | U | 同上 |
| `validationLevel` | ENUM | `STRICT` | `^(LAX\|NORMAL\|STRICT)$` | U | 同上 |

合計 10＋9＋10＋6＋11＋4＝**50**。`model.apiKey` 與 `autoclaude.dbDsn` 的 `valueType=ENCRYPTED`、`is_encrypted=TRUE`。

---

## 附錄 D　常數與設定屬性

### D.1 上限與固定常數

| 常數 | 值 | 出處 |
|------|----|------|
| 匯入檔案大小 | 10 MB（10,485,760 bytes；multipart 請求 11MB） | US-I-01 |
| 設定檔大小 | 1 MB（1,048,576 bytes） | §1.5.10 |
| 文字匯入長度 | 2,000,000 字元 | §1.1.2 |
| 每個目標任務數／目標數 | ≤ 24／≤ 24（可下調不可上調） | §3.3.5 |
| 路徑 A 每個目標容納的合約數 | 24（依編譯順序切組；超過就多一個目標） | §3.3.2、D-49 |
| 任務 `maxRetries` | 0～20 | §0.8、§1.2.1 第 9f 項、D-56 |
| 步驟 prompt 長度 | ≤ 20,000 字元（UTF-16 code unit） | §3.4.3、Architecture L-9 |
| 路徑 B 的 LLM 輸入長度 | ≤ 120,000 字元（`console.import.max-prompt-chars`） | §3.3.3 |
| 路徑 C 判斷門檻 | `sourceType=PLAIN_TEXT` 且全文 < 2,000 字元且無 Markdown 標題行 | §3.3.1 |
| 審核 `comment` | ≤ 2,000 字元 | §1.2.11 |
| 設定 `value` | ≤ 4,000 字元（加密值 ≤ 512） | §1.5 |
| 遮罩字串 | `••••••••`（U+2022 ×8） | §1.5 |
| 加密佔位字串（匯出） | `<encrypted>` | §1.5.9 |
| 限流 | 100 次／60 秒／使用者（JWT subject；未認證才以客戶端 IP） | §0.4 第 4 點、D-50 |
| 輪詢間隔地板 | 10 秒（`monitor.refreshIntervalMs` 的預設與最小值） | §0.4 第 4 點、附錄 C.4 |
| SSE keep-alive／佇列 | 15 秒／1,000 框架 | §2.1 |
| 監控視窗上限 | 366 天；趨勢桶數 ≤ 1,000 | §1.3 |
| 全域任務總計視窗上限 | 92 天（`to − from`；`from` 必填） | §1.3.8 |
| 軟刪除保留期 | 30 天（`console.retention.soft-delete-days`）；清除排程預設關閉 | §1.6.5、ADR-001 D19 |
| Bridge 資源取樣間隔／樣本過期門檻 | 5 秒／15 秒（超過 15 秒未更新，`resources` 回 null） | §3.1.2（v1.3，D-12） |
| 引擎能力狀態值域 | `ENABLED`／`OFF`／`UNAVAILABLE_NO_API_KEY`（兩個欄位同值域） | §3.4.2（v1.3，D-11） |
| 等級對映門檻 | 自治等級 ≥ 6 → 視為要求自動突變；≥ 7 → 視為要求自演化 | §3.4.2（v1.3，D-11） |
| 待審批清單 `limit` | 預設 50、範圍 1～200（只截斷 `items`，不影響 `counts`） | §1.8.1（v1.4，D-18） |
| 引擎狀態輪詢間隔 | 30 秒（前端；分頁不可見時暫停） | §1.7.1、§4.3 M-20（v1.4，D-16） |
| FSM 專案名白名單 | `^[A-Za-z0-9._-]{1,128}$`（Bridge 與 console-api 同一條） | §1.7.1、§3.1.3（v1.4，D-16） |
| FSM `decision_trace`／`human_pending.items` 回傳筆數 | 各取尾 5 筆 | §3.1.3（v1.4，D-16） |
| FSM 專案名規則（v1.5；**取代上方「FSM 專案名白名單」那一列的 regex**） | 進入 Bridge 的專案名一律先過淨化鏡像 `fsm_component()`（NFC→strip→把 `< > : " ? * \ /`、ASCII 豎線與控制字元換成 `_`→截 80→`rstrip(" .")`）；讀取白名單＝淨化輸出域（非空、NFC、≤ 80、不是 `.`／`..`、無禁用字元與控制字元、無前後空白、不以 `.` 結尾）。Console 的 `project` 查詢參數只驗 1～200 字元與無控制字元 | §3.1.4 (b)、§1.10.4（v1.5，S-10；ADR-016 §7.4） |
| `escalation_history` 回傳筆數（v1.5） | 取尾 5 筆 | §3.1.4 (c) |
| SDD 寫入相關的逾時（v1.5） | `:freeze` 讀取 40 秒；帶 `sdd` 的 `POST /autoclaude/runs` 讀取 90 秒（一般批次維持 30 秒）；追溯覆蓋讀取 3 秒；**FSM CLI 子行程單次 20 秒**（逾時回 504 `sdd_cli_timeout`；ADR-016 §3.5） | §3.1、§3.1.4 共通規則 1 |
| `:freeze` 欄位上限（v1.5） | `docs` 1～20 項；`stage` ≤ 64 字元；`approver` 1～100 字元且不含 `;` 與控制字元；`reason` 1～500 字元且無控制字元（含換行）；單檔 ≤ 16 MiB、須為 UTF-8；預設階段名 `Stage-<n>` | §1.10.2、§3.1.4 (d) |
| `phase` 的主路徑階段數（v1.5） | 8（`order` 為 1～8）；非主路徑的 `order` 為 0 | §3.1.5 |
| 專案綁定欄位長度（v1.5） | `sdd_project` ≤ 100；`sdd_spec_dir`、`sdd_spec_file` ≤ 500；`ParseOptions.sddProject` 與 `GET /engines/sdd?project=` ≤ 200（專案名上限；值是「有效值」，可以是原名） | §0.5 V12、§1.10.4 |
| 寫入權杖（v1.5） | 環境變數 `BRIDGE_SDD_WRITE_TOKEN`；≥ 32 字元；不得是 `<…>` 佔位；標頭 `X-Bridge-Token` | §3.1.4 共通規則 2；附錄 D.2 |
| Bridge 健康探測逾時 | 連線 2 秒、讀取 **8 秒**（v1.3 以前 3 秒）；每 30 秒一次 | §3.1、§3.1.1（v1.4，D-17） |
| refresh token 撤銷名單 | 鍵＝`jti`；存活到該 token 的 `exp`；降級記憶體名單每 10 分鐘掃描 | §1.9.2（v1.4，D-19） |
| 命令黑名單字元（NFR-SEC-03 第 1、2 層） | `` ! ` > < ~ $ & ; ``（8 個）＋換行、回車、NUL（Bridge 另加） | SSOT：`AutoClaude/autoclaude/utils/shell_deny_chars.py` 的 `BASE_DENY_CHARS`；後端複製並於檔頭註明（W4 QA 腳本比對兩端字元集一致） |

### D.2 `console.*` 屬性（Spring，環境變數以 `CONSOLE_…` 覆寫）

| 屬性 | 預設 | 說明 |
|------|------|------|
| `console.security.outbound-allowlist` | `api.minimax.io,api.minimax.chat`（與 Bridge 的 MiniMax 兩個網域對齊：docker compose 的 `BRIDGE_OUTBOUND_ALLOWLIST` 即此值，Bridge 程式內建預設另含 `localhost`、`127.0.0.1`） | SEC-04 外呼 host 白名單（精確比對）；e2e／本機 profile 另加 `127.0.0.1,localhost`。要用其他供應商（例：`api.anthropic.com`、`api.openai.com`）須由部署者明確加入，且 Bridge 的 `BRIDGE_OUTBOUND_ALLOWLIST` 也要含該 host——兩份名單不一致會變成「Console 放行、Bridge 拒絕」（AR-09、D-53） |
| `console.security.allow-loopback` | `false`（**只在 e2e／test／本機 profile 設為 `true`**；production 與 docker profile 不得出現這個屬性） | 放行 loopback 位址（字面或解析結果），且 host 須在 allowlist 內；`link_local`／`private_ip` 任何情形都拒，沒有「允許私網」旗標（§1.5.7、D-47） |
| `console.security.test-dns-overrides` | （空；**僅 e2e／test profile**） | 測試用 DNS 覆寫（`host: ip`）；由 `OutboundHttpClient` 的 `DnsResolver` 優先查詢，讓 `dns_rebinding` 可決定性重現 |
| `console.security.evaluator-allowlist` | 見 D.3 | 評估指令首個 token 的可執行檔白名單 |
| `console.security.rate-limit.enabled` | `true`（單元／整合測試 profile 為 `false`） | 限流開關；須有一支測試開著它驗第 101 次回 429 |
| `console.security.rate-limit.requests-per-minute` | `100` | 每個使用者（JWT subject）每 60 秒的上限；未認證請求以客戶端 IP 計 |
| `console.security.rate-limit.trust-forwarded-for` | `false`（docker／e2e 為 `true`） | 是否採信代理轉送的客戶端位址；搭配 `server.forward-headers-strategy=native`，限流取處理後的 `getRemoteAddr()`，不自行解析 `X-Forwarded-For`；只有未認證請求會用到 IP（§0.4 第 4 點） |
| `server.forward-headers-strategy`（Spring Boot） | `none`（docker／e2e 為 `native`） | 讓 Tomcat 還原 nginx 轉送的客戶端位址；production 直連（沒有代理）維持 `none` |
| `console.sse.keep-alive-seconds` | `15`；e2e／test profile 覆寫為 `2` | 該覆寫只在 e2e／test profile 載入 |
| `console.sse.queue-size` | `1000` | |
| `console.import.max-prompt-chars` | `120000` | |
| `console.execution.mock-env` | （空；**僅 e2e／test profile**） | 附加到 Bridge 請求 `env` 的 `MOCK_CLAUDE_*` |
| `console.bridge.sdd-write-token`（環境變數 `BRIDGE_SDD_WRITE_TOKEN`；`application.yml` 的 `console.bridge` 段，值 `${BRIDGE_SDD_WRITE_TOKEN:}`；`BridgeProperties.sddWriteToken`） | （空＝SDD 寫入面停用；**repo 內不放真值**，`.env.example` 只放 `<YOUR_BRIDGE_SDD_WRITE_TOKEN_MIN_32_CHARS>`） | v1.5（ADR-016 §9）：核准凍結與帶 `sdd` 的批次所需的寫入權杖，與 Bridge 同名同值；**有設但短於 32 字元或仍是 `<…>` 佔位⇒backend 啟動即失敗**（不靜默退回停用）；未設時 freeze 回 503 `sdd_write_disabled`、execute 不送 `sdd` 並以 `token_not_configured` 警告（§1.10.5）。只附在 `sddFreeze` 與帶 `sdd` 的 `startRun`，**不得寫進日誌、錯誤封包或 `details`** |
| `console.retention.soft-delete-days` | `30` | 軟刪除專案可復原的天數（≥ 1；v1.2，§1.6.5） |
| `console.retention.purge-enabled` | **`false`** | 是否註冊每日清除排程；預設關閉（實體刪除不可逆；v1.2，§1.6.5、ADR-001 D19） |
| `console.security.refresh-revocation.store` | `auto` | refresh token 撤銷名單的儲存（v1.4，§1.9.2）：`auto`＝`spring.data.redis.host` 有值才用 Redis（Redis 不在線時降級為記憶體並記 WARN），否則純記憶體；`redis`＝只用 Redis（降級照舊）；`memory`＝只用記憶體（本機 e2e、單元測試） |
| `spring.data.redis.host`／`spring.data.redis.port`（環境變數 `SPRING_DATA_REDIS_HOST`／`SPRING_DATA_REDIS_PORT`） | **選填**（未設＝不連 Redis；docker compose 設 `redis`／`6379`） | **只**被撤銷名單使用（限流計數與 SSE 位移不用 Redis，ADR-001 D16／D23）；v1.4 起 backend 程式本身不需要 Redis 才能運作（compose 的 `depends_on: redis` 維持不動，主控裁決 Q6） |
| `management.health.redis.enabled` | **`false`（必須）** | 否則 Redis 不在線會讓 `/actuator/health` 變 DOWN、backend 容器 unhealthy，降級承諾落空（§1.9.2） |
| `LOG_DIR`（環境變數） | （空；docker compose 設 `/app/logs`） | 有值時 logback 另啟 JSON 行的 `RollingFileAppender`（`${LOG_DIR}/console.log`，每日切檔、保留 7 天）；沒設時行為不變（C-16） |
| `server.tomcat.remoteip.internal-proxies`（環境變數 `CONSOLE_INTERNAL_PROXIES`） | 只信 compose 子網（值寫在 `docker/README.md`） | Tomcat `RemoteIpValve` 信任的代理位址；縮小它可避免內網客戶端以 `X-Forwarded-For` 繞過未認證限流（QA O-20；C-16） |
| `CONSOLE_ENCRYPTION_KEY`（環境變數） | 必填 | base64 的 32 bytes（AES-256-GCM）；缺少或長度不對＝啟動失敗；docker-compose 對應 `${CONSOLE_ENCRYPTION_KEY:?…}`，未設時 `compose config`／`up` 直接失敗（C-16） |
| `spring.servlet.multipart.max-file-size`／`max-request-size` | `10MB`／`11MB` | 匯入上傳（設定檔另有 1MB 檢查） |

### D.3 評估指令可執行檔白名單（建議預設，Architecture §8.3「預設值由 W3 後端定案」）

判定：取 `evaluatorCommand` 去前後空白後的**第一個以空白分隔的 token**，去掉路徑前綴與 `.exe`／`.cmd`／`.bat` 後綴，**不分大小寫**比對下列名單；不在名單 → execute 回 422 `評估指令不在可執行檔白名單`。

`pytest, python, python3, py, npm, npx, node, pnpm, yarn, mvn, mvnw, gradle, gradlew, java, dotnet, go, cargo, make, tsc, eslint, ruff, mypy, git`

不含 shell 與 shell 內建（`sh`、`bash`、`cmd`、`powershell`、`pwsh`、`echo`、`test`…）——引擎的評估器以平台原生殼執行（Windows 為 `cmd.exe`）。後端可擴充名單並記入交卷。

**這道檢查的實際強度（AR-18；v1.0 曾稱「白名單加禁用字元集是兩層獨立防線」，過度宣稱，已降級）**：白名單只看**第一個 token**，不是沙箱。第一個 token 之後的引數與串接，只靠禁用字元集（`` ! ` > < ~ $ & ; ``，§D.1）把關，而該字元集**不含** `|`、`(`、`)`、`{`、`}`、`*`、`?`——例如 `pytest -q | python -c "…"` 的第一個 token 合法、也沒有任何禁用字元，會通過這兩道檢查。引擎的 `goal_freeze_gate.py`（凍結步驟 prompt 的閘）自己的字元集是 `BASE_DENY_CHARS` 再加 `|`，但那是對 prompt 的另一條路徑，不構成對 `evaluatorCommand` 的第二層。風險判斷：OPERATOR 本來就能指示 Agent 執行程式，這一項的風險有限，所以只降級敘述、**不改字元集**（後端複製的 `BASE_DENY_CHARS` 須與 Bridge、引擎維持逐字元一致，W4 QA 腳本會比對；若日後要補 `|`，須三處同步另案評估）。

### D.4 後端新增依賴（主控已核可；除此之外不得新增，需要別的先在交卷〈沒做／偏離〉提案）

| 依賴 | 用途 | 版本 | 核可來源 |
|------|------|------|----------|
| `org.apache.pdfbox:pdfbox`（3.x） | PDF 文字擷取（§1.1.1）；**v1.2 起另用於 PDF 報表產生**（§1.3.7，`PDType0Font` 內嵌 CJK 字型；不新增相依） | 釘在 `build.gradle.kts` 的版本區：**3.0.8**（B1-8） | W3-B1 任務書 |
| `org.apache.poi:poi-ooxml` | DOCX 文字擷取（§1.1.1） | **5.5.1**（同上） | W3-B1 任務書 |
| `com.bucket4j:bucket4j-core` | 限流（記憶體實作，§0.4 第 4 點） | **8.10.1**（Maven Central 上的最後一版，之後改名 `bucket4j_jdk17-core`；同上） | W3-B1 任務書 |
| `org.apache.httpcomponents.client5:httpclient5` | SSRF 防護的外呼 HTTP 客戶端：自訂 `DnsResolver` 釘 IP、Host／SNI 用原 host、不跟 redirect（§1.5.7；AR-10；D-51） | 由 Spring Boot BOM 管理，**不自行指定版本** | 主控補充裁決（W3-B1 補充節） |
| `org.springframework.boot:spring-boot-starter-data-redis` | refresh token 撤銷名單的 Redis 實作（§1.9.2；內含 Lettuce 客戶端）；v1.4 以前後端**零 Redis 相依** | 由 Spring Boot BOM 管理，**不自行指定版本** | 主控裁決 D-19（`Implementation_Plan.md` §5.3）；主控已裁決視同核可（§6.7.3 Q6） |

**字型資源（v1.2，C-4；不是相依）**：PDF 報表需要的 CJK 字型（建議 Noto Sans TC 靜態 Regular，SIL OFL 1.1）與其授權檔放 `backend/src/main/resources/fonts/`；來源網址與檔案雜湊寫在 W5-BE 交卷。

---

## 附錄 E　RTM 對照（契約位置與驗收情境）

「IT」＝後端整合測試（不在 §5 的 E2E 內）。

| RTM ID | 契約位置 | 驗收 |
|--------|----------|------|
| API-IMP-01、07 | §1.1.1 | E2E-01（上傳變體） |
| API-IMP-02 | §1.1.2 | E2E-01 |
| API-IMP-03、09 | §1.1.3、§3.3.3 | E2E-01（含有界閘變體） |
| API-IMP-04 | §1.1.4 | E2E-01 步驟 4、9 |
| API-IMP-05 | §1.1.6 | E2E-01 步驟 5、11 |
| API-IMP-06 | §1.1.8、§1.1.9 | E2E-01 步驟 3、14；`warnings`／`parseOptions`（v1.2）：E2E-13 第 10 列 |
| API-IMP-08 | §3.3.1、§3.3.2 | IT（假 Bridge：compile 200／各 422／不可達） |
| API-IMP-10 | §1.1 狀態圖與表 | E2E-01 步驟 13、IT（非法轉移矩陣） |
| API-SGN-01 | §1.1.5 | E2E-01 步驟 6～10 |
| API-SGN-02～04 | Phase 2 | Phase 2 測試；E2E-02 步驟 3～6 |
| API-EXE-01、11 | §1.2.1 | E2E-02、E2E-03 |
| API-EXE-02、03 | §1.2.4、§1.2.5 | E2E-04、E2E-08；手動 pause／resume 為 IT |
| API-EXE-04 | §1.2.6 | E2E-06 |
| API-EXE-05 | §1.2.3 | E2E-03 步驟 4；Bridge 不可達回 200 為 IT |
| API-EXE-06 | §1.2.7 | E2E-03 步驟 5、E2E-12 |
| API-EXE-07、DAG-01 | §1.2.8、§3.4.4 | E2E-03 步驟 6 |
| API-EXE-08 | §1.2.9 | E2E-03 步驟 7、E2E-07 |
| API-EXE-09 | §1.2.10 | E2E-07 |
| API-EXE-10 | §1.2.11、§3.6.3 | E2E-04、E2E-05 |
| API-EXE-12 | §1.2.1 第 10 項 | IT（同專案同路徑兩次 execute，Bridge 409＋補償；另以迷你 Bridge 回 `spawn_failed` 驗補償刪除，AR-15）；E2E-02 步驟 7 為 Console 層檢查 |
| API-EXE-13 | §3.4 | E2E-03（mock trace 驗 prompt 與關鍵字）、IT（欄位逐項） |
| API-EXE-14 | §1.2.2 | E2E-03 步驟 13、E2E-05 步驟 7；`bridgeStatus`（v1.2）：E2E-13 第 11 列 |
| API-AUT-01～03 | §3.6.1、§3.6.2 | E2E-04（含 Level 2／3 對照） |
| API-AUT-04、05 | §3.6.2 | E2E-05 變體 V4；決策表單元測試 |
| API-AUT-06（v1.3 改寫） | §3.6.1、§3.4.2 | 單元：`ConfigMaterializerTest`（§3.4.2 決策表 8 列、等級 {1, 5, 6, 7, 10} 邊界、永不送的鍵）；`ReviewGatePolicy` 對等級 6～10 的行為同等級 5（既有單元不變）。IT：`ExecutionLifecycleApiIT`（execute 201 與詳情的 `engineCapabilities`）。**E2E-14 第 1～7 列**：`engineCapabilities` 三種值、磁碟 `config.yaml` 的 `minimax.enable_kernel_brain`、「不含 `max_evolutions`／`require_evolution_signoff`」的否定斷言、Brain 校正請求數與 attempt 數的行為差異。**RTM 狀態由 QA 依 E2E-14 的當回合證據升級**（v1.2 為 🟡「不送引擎設定」；v1.3 的範圍是「Brain 逐步校正已送進引擎、能力狀態如實回報」，自演化只提案不套用是引擎現況而非缺口，§6.6.2） |
| API-MON-01～04、06 | §1.3.1～§1.3.4、§1.3.6 | E2E-03 步驟 9～13 |
| API-MON-05 | §1.3.5 | E2E-08 步驟 7 |
| API-MON-07 | §1.3.7 | E2E-03 步驟 15（CSV 與 PDF 皆 200）、E2E-13 第 4 列 |
| API-MON-08（v1.2） | §1.3.8 | E2E-13 第 1 列；IT（與各專案 `task-trend` 加總逐欄相等、封存與軟刪專案不計、視窗 92 天、VIEWER 200） |
| API-PRJ-06（v1.2） | §1.6.1、§1.6.2 | E2E-13 第 2～3 列；IT（復原連帶目標／任務、單獨先刪的不回來、404／409×2、VIEWER 403） |
| NFR-9.3-04（軟刪除 30 天內可復原；v1.2） | §1.6.1、§1.6.5、§0.5 V9 | E2E-13 第 2～3 列；單元（清除排程：逾期專案連同子樹實體刪除、`purge-enabled=false` 不註冊） |
| BR-26（Bridge 深度探針；v1.2） | §3.1.1 | E2E-13 第 13 列；Bridge pytest（200／503）；Docker 全棧 healthcheck 與批次跑到 `COMPLETED`；**v1.4（D-17）加 `sdd` 檢查（只當資訊，不影響 503）**：Bridge pytest（三態、乾淨 clone 等價、空目錄／掛錯、`sdd.ok=false` 時整體仍 200）、E2E-15 第 8～9 列 |
| BR-13、BR-14（Bridge `GET /sdd/version`、`GET /sdd/fsm/{project}`；v1.4 起 Console 消費） | §1.7.1、§3.1.3 | Bridge pytest（`tests/test_sdd_fsm.py`）；`EnginesApiIT`；E2E-15（此前只驗到 Bridge 直連，完整性審查 I-01） |
| NFR-9.4-04（日誌 traceId 串聯；v1.2） | §0.4 第 6 點、§3.1.1 | E2E-13 第 12 列；`BridgeRunsAdapterTest`（標頭存在）、Bridge pytest（回帶標頭、每行日誌含 `trace_id`） |
| API-NTF-01 | §1.4.1 | E2E-04 步驟 3、E2E-05 步驟 3、E2E-08 步驟 5；v1.4：`pendingSignoffs` 與清單同源（`API-SGN-05` 的不變量，E2E-16 第 3 列）、`bridgeConnected` 對深度探針 503 為 `false`（E2E-16 第 2 列） |
| API-ALR-01、02 | §3.7 | E2E-08 |
| API-ALR-03 | §3.7 | E2E-05（`ENGINE_ESCALATION`）、E2E-13 第 7 列（跨批次不被吞）；連續失敗規則為單元（假事件序列；觸發路徑說明見 §3.7） |
| API-ALR-04～06 | §3.7 | 單元（假時鐘與假探測環） |
| API-SSE-01～03 | §2 | E2E-03、E2E-04（重播）、E2E-12 |
| API-SET-01、02 | §1.5.1、§1.5.2 | E2E-09 步驟 1、8 |
| API-SET-03、04 | §1.5.3、§1.5.4 | E2E-09 步驟 2～7 |
| API-SET-05 | §1.5.5、§1.5.6 | E2E-09 步驟 10、11 |
| API-SET-06 | §1.5.7 | E2E-10 |
| API-SET-07 | §1.5.8 | E2E-09 步驟 16 |
| API-SET-08、09 | §1.5.9、§1.5.10 | E2E-09 步驟 12～14；匯出後原樣匯入（v1.2）：E2E-13 第 6 列 |
| API-SET-10 | §3.4.2 | E2E-03（替身 `claude.command` 生效）、IT（物化表逐列） |
| NFR-SEC-03 | §1.1.4、§1.2.1 第 9 項 | E2E-01（消毒變體）、IT（第 2 層複驗與白名單） |
| NFR-SEC-04 | §1.5.7、§3.3.3 | E2E-10、E2E-01（`brain_unsupported`）、E2E-09 步驟 15 |
| NFR-SEC-05 | §1.5.3～§1.5.6、§1.5.10 | E2E-09 |
| NFR-OBS-01 | §5.0.4 A1、§1.7.1 | E2E-03 步驟 14；每個 run 情境的共通後置斷言 A1。**v1.4 補強（D-16）**：PRD §0.5 的四源之一「FSM-STATE yaml」此前沒有被比對（完整性審查 V-06）；E2E-15 第 5 列做「FSM 檔 ↔ API ↔ 畫面」逐值比對（夾具上；真實檔在第 12 列選跑） |
| US-I-01～10 | §1.1 | E2E-01（US-I-10＝有界閘變體；US-I-05、07、08＝步驟 2 的請求欄位）。**US-I-05 的「瀏覽按鈕」判 ⛔ 範圍外**（主控裁決：Web 不瀏覽伺服器檔案系統，路徑輸入欄即為交付；§4.6 G-I2） |
| US-E-01～02、10 | §1.2.1 | E2E-02、E2E-03、E2E-08 變體 V1 |
| US-E-03、09 | §2、§1.2.8 | E2E-03、E2E-12；DAG 卡「全螢幕」（v1.4，§4.2 E-22）：前端單元（開／關／Esc／焦點歸還）＋一支 e2e 斷言 |
| US-E-04～06 | §1.2.4～§1.2.6 | E2E-04、E2E-06、E2E-08 |
| US-E-07、08 | §1.2.11、§1.4.1 | E2E-04、E2E-05 |
| US-E-11 | §1.2.9、§1.2.10 | E2E-07 |
| US-M-01～07、09 | §1.3 | E2E-03、E2E-08；US-M-06 見 `executions` 列表（E2E-03 步驟 13）；US-M-07 的 PDF 見 E2E-13 第 4 列；**US-M-09（追蹤鏈）以批次下拉＋事件時間軸＋日誌查詢涵蓋，不另做獨立視圖**（主控裁決 C-14，§4.3 M-12） |
| US-M-08 | 純前端（§4.3 M-18） | 前端測試 |
| US-M-10 | §1.2.3、§1.3.1、§3.1.2、§4.3 M-19 | E2E-03 步驟 4、9（連線狀態、目前任務、Token 與步驟進度）。**資源使用情況（v1.3，D-12）**：E2E-14 第 8～9 列；Bridge pytest（欄位型別、終態與 PAUSED 後為 null、已消失的 pid 不炸、跨 tick 持有 `Process` 物件、過期樣本回 null）；`ExecutionLifecycleApiIT`（`bridge.resources` 有值／缺鍵／null 三種）；前端單元（M-19 的顯示格式與 `—`）。**RTM 狀態由 QA 依當回合證據升級**（v1.2 為 🟡「Bridge 沒有資料來源」，§4.6 G-M3 已補）。**v1.4（D-17）Agent 可用率改打深度探針**：E2E-16 第 2 列；`BridgeHealthMonitor` 單元（503 與連線失敗皆計為失敗；`UI-KPI-08` 同） |
| US-S-01～08 | §1.5 | E2E-09、E2E-10 |
| NFR-9.2-06（限流） | §0.4 第 4 點 | E2E-11；IT（開著限流打 101 次，第 101 次回 429） |
| NFR-9.2-07（審計） | §0.4 第 5 點 | IT（寫入端點落 `audit_log` 一列；寫入失敗不影響主請求） |
| 部署需求（反向代理） | §0.7 | W4-QA 矩陣 D（經 nginx 上傳 10MB、`access_token` 不入 nginx 日誌）、E2E-12 步驟 12 |
| 既有測試同步 | §0.8 | B1／B2 交卷時 `gradlew clean build` 全綠（`OpenApiIT`、`SchemaMigrationIT` 依 §0.8 的真值更新） |
| API-ENG-01（v1.4，D-16；QA 追加 RTM 列：AISDLC_SDD 引擎狀態） | §1.7.1、§3.1.3、§4.3 M-20 | `EnginesApiIT`（迷你 Bridge 逐列驗 `reason` 映射：有專案、帶 `project`、`fsm_not_found`、`fsm_state_unreadable`、`sdd_unavailable`、連線失敗、逾時、未帶 `project`、非法 `project` 400、VIEWER 200／未認證 401）；Bridge pytest（`tests/test_sdd_fsm.py`）；前端單元（M-20 的格式與各 `reason` 文案、`—` 與空清單）；**E2E-15** |
| API-SGN-05（v1.4，D-18；QA 追加 RTM 列：待審批清單；編號避開既有 `API-SGN-01～04`） | §1.8.1、§4.5 G-10 | `SignoffsPendingApiIT`（四種各一＋干擾列、`limit`、排序、VIEWER 200／未認證 401、**`counts.total` 等於 `pendingSignoffs` 的不變量**）；前端單元（G-10 的連結與「僅列出最早的 N 筆」）；**E2E-16 第 3～6 列** |
| API-AUTH-03（v1.4，D-19；QA 追加 RTM 列：登出與 refresh token 撤銷名單） | §1.9.1、§1.9.2、§2.8 第 10 點 | `AuthApiIT`（換新後舊 token 401、登出後 401、垃圾 token 仍 204、併發換新只一個成功、Redis 替身降級與恢復各記一次日誌、`/actuator/health` 不受影響）；前端單元（`logout()` 先呼叫端點、失敗不阻擋）；**E2E-16 第 7～10 列** |
| INF-SVC-07（Redis 服務；v1.4 起 backend 真的使用它） | §1.9.2、ADR-001 D16／D23 | E2E-16 第 10 列（Docker 全棧：停 Redis 後撤銷仍有效、backend 維持 healthy；此前只驗容器健康，完整性審查 I-06） |
| API-PRJ-07（v1.5；QA 追加 RTM 列：專案 SDD 綁定） | §0.5 V12、§1.10.5 | `SchemaMigrationIT`（V12 三欄與部分唯一索引）；`ProjectApiIT`（綁定欄回傳）；`ImportApiIT`（confirm 回填）；**E2E-17 第 5、8 列** |
| API-PRJ-08（v1.5；QA 追加 RTM 列：編輯專案的 FSM 專案） | §1.10.7 | `SddBindingApiIT`（驗證、唯一性 409、角色、冪等、稽核）；前端單元（編輯對話框）；**E2E-17 第 7 列** |
| API-SGN-06（v1.5；QA 追加 RTM 列：核准凍結） | §1.10.2、§3.1.4 (d) | `SddFreezeApiIT`（驗證順序六項、先檢查後寫入、對映表每列、角色）；`BridgeHttpAdapterTest`；Bridge `test_sdd_freeze.py`；**E2E-17 第 1～7 列** |
| API-EXE-15（v1.5；QA 追加 RTM 列：SDD 批次） | §1.10.5～§1.10.6、§3.1.6、§3.4.1 | `ExecuteProjectApiIT`；`PlaybookBuilderTest`；`ExecutionPlannerTest`；Bridge `test_sdd_run.py`；**E2E-17 第 15、18～22、25 列** |
| API-EXE-16（v1.5；QA 追加 RTM 列：執行追溯覆蓋） | §1.10.3、§3.1.4 (f) | `ExecutionRtmApiIT`；Bridge `test_rtm.py`；前端單元（面板顯示規則）；**E2E-17 第 16、19 列** |
| API-ENG-02（v1.5；QA 追加 RTM 列：引擎狀態依專案帶 root） | §1.10.4、§3.1.4 (a)(b)(c) | `EnginesApiIT`；`SddEngineQueryServiceTest`；**E2E-17 第 13、14、19 列** |
| API-IMP-11（v1.5；QA 追加 RTM 列：路徑 A 欄位保真與選檔） | §3.3.2、§3.1.4 (e) | `ImportParserTest`；Bridge `test_sdd.py`；**E2E-17 第 8、10～12 列** |
| API-IMP-12（v1.5；QA 追加 RTM 列：匯入併入既有專案） | §1.10.8、§3.3.2 | `ImportApiIT`（併入、排序、404、三種 409、不帶 target 的重複綁定 409）；`ImportParserTest`；**E2E-17 第 8、9 列** |
| BR-27～BR-33（v1.5；QA 追加 RTM 列：Bridge 的 SDD 寫入面、擴充與同步） | §3.1.4～§3.1.6 | Bridge pytest（`test_sdd_freeze.py`、`test_sdd_fsm.py`、`test_sdd_phase.py`、`test_sdd.py`、`test_sdd_run.py`、`test_rtm.py`、`test_sdd_integration_parity.py` 的 F-1～F-12）；**E2E-17** |
| UI-SDD-01～03（v1.5；QA 追加 RTM 列：SDD 治理介面） | §4.7.1～§4.7.3、§4.3 M-21 | 前端單元（`lib/domain/sdd.ts` 的顯示規則）；mock e2e；**E2E-17 第 5、19 列的畫面斷言** |
| NFR-OBS-01（v1.5 補強） | §1.10、§5 E2E-17 第 17 列 | 四源對拍表（FSM 檔 ↔ Bridge ↔ Console API ↔ PG） |
