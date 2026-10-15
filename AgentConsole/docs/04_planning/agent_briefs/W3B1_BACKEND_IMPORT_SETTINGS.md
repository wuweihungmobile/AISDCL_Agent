# 任務書 W3-B1：後端第一棒（Spring Boot 4.1／Java 21；Phase 3 匯入 ＋ Phase 6 系統設定 ＋ PRD §9.2 安全補完）

> 先讀 `COMMON_CONTEXT.md`（頂部〈本輪環境覆寫〉是 Windows 規則，凌駕其後的 macOS 內容）、`AgentConsole/CLAUDE.md`、`AgentConsole/backend/README.md`，然後讀**契約 SSOT**：`AgentConsole/docs/02_architecture/API_Contract_P3-6.md` ＋ `openapi-p3-6.yaml`（與 `W3_BACKEND_P3-6.md`／`Architecture.md` 衝突時**以契約為準**；契約沒寫到的細節再看 `W3_BACKEND_P3-6.md`〈已拍板決策〉與本檔〈補充裁決〉），最後讀本檔。
> 你在 W2-A 完成的 backend 專案（Phase 1＋2，448 支測試全綠）上續做。W3-B2（執行＋監控）會在你交卷後接手**同一棵樹**，所以你交卷時 `.\gradlew.bat clean build` 必須 BUILD SUCCESSFUL，不能留半套。

## 必讀 PRD 行段
§0.2～§0.6（58～125）、§5.2（647～820）、§5.5（1178～1341）、§7.1.4（1726～1746）、§7.1.8（1791～1807）、§7.2（1809～1855）、§9.2（1955～1966）、§6.2 的 `import_records`／`system_configs`／`system_config_history` DDL（在 1496～1689 內用 Grep 找表名）。Architecture：§6(b)（381～407）、§8（579～639）、§11（845～1038）。

## 範圍（只做這些；執行／監控／SSE／review／alerts 的 API 一律不碰，那是 W3-B2）
1. **Flyway**：`V5__seed_engine_configs.sql`＝Architecture §11.4「V5 補充鍵」9 個鍵的種子 ＋ `ALTER TABLE console.system_configs ADD COLUMN impact_note VARCHAR(500)`（US-S-08）並為關鍵鍵填繁中影響提示（`agent.defaultAutonomyLevel`、`execution.globalTokenBudget`、`execution.compactThresholdPct`、`execution.haltThresholdPct`、`model.apiUrl`、`model.apiKey`、`autoclaude.dalBackend`、`autoclaude.claudeCommand`）；`V6__audit_log.sql`（`id, occurred_at, subject, role, method, path, entity_type, entity_id, http_status, trace_id`）。JPA 實體同步，`ddl-auto=validate` 必過。
2. **系統設定 API**：契約 §1 的 `/api/v1/settings/**` 全部端點（GET all 依分類分組、GET category、PUT 單鍵、PUT `execution/token-guard` 原子、reset、test-connection、history 分頁、export、import）。
3. **匯入 API**：契約 §1 的 `/api/v1/import/**` 全部端點（upload／text／parse／PUT result／signoff／confirm／GET 列表／契約若有 GET 單筆也做）。
4. **安全補完（PRD §9.2）**：Rate limiting、audit_log 持久化、actuator 只開 health／prometheus（已是如此，驗證即可）。
5. **`GET /api/v1/notifications/summary`**（契約 §1）：`pendingSignoffs`（projects＋goals＋tasks＋import_records 中 `signed_off=false` 且未軟刪／未 REJECTED 的筆數）、`pendingReviews`（`review_requests.status=PENDING` 筆數，表已在 V3）、`unacknowledgedAlerts`（`alerts.acknowledged=false`，表已在 V4）。只讀，用簡單 repository 查數即可，B2 不需再改。
6. **OpenAPI 對帳**：springdoc 產物（`/v3/api-docs`）與 `openapi-p3-6.yaml` 逐端點比對（路徑、方法、欄位名、狀態碼），差異逐條列在交卷〈契約漂移〉；**能改碼對齊契約的就改碼**，認為契約錯的寫明理由（主控裁決，不要自行改契約檔）。

## 補充裁決（主控已定；與 W3_BACKEND_P3-6.md 衝突時以本節為準）
- **外呼 allowlist 與 SSRF**：新增設定 `console.security.outbound-allowlist`（逗號分隔 host；預設 `api.minimax.io,api.minimax.chat,api.anthropic.com,api.openai.com`）。校驗鏈＝URL 解析（拒 userinfo、反斜線、IDN、十進位／十六進位 IP）→ host 精確命中 allowlist → DNS 解析後**每個** IP 不得落在私網／loopback／link-local（**除非該 host 字面本身明列於 allowlist**，供本機 E2E 把 `localhost`／`127.0.0.1` 加進去）→ HTTP 連線不跟 redirect（3xx 視為失敗 `redirect_not_allowed`）。`model.apiUrl` 寫入設定時就套同一套校驗（不過＝400 附 reason）。DNS 解析用可注入的 resolver 介面，測試以假 resolver 驗 rebinding（解析結果落私網 ⇒ 拒）。
- **LLM 自由文件路徑**：`POST {model.apiUrl}/chat/completions`（OpenAI 相容；`model.apiUrl` 是 base URL，不含 `/chat/completions`）；header `Authorization: Bearer <解密後 apiKey>`；body `{model: model.name, messages:[{role:"user", content:<PRD §5.2.4 模板逐字填值>}], temperature: model.temperature, max_tokens: model.maxTokensPerRequest, response_format:{type:"json_object"}}`；逾時 `model.timeout` 秒；回應取 `choices[0].message.content` → 去掉 ``` 圍欄 → 依 §5.2.4 schema 解析，失敗回 422 `gate=brain_failed`；`usage.total_tokens` → `tokenUsed`、回應 `model` → `aiModel`。
- **三條路徑的選擇規則**：`specDir` 非空 → sdd compile（Bridge `POST /sdd/compile`；Bridge 422／503 原樣轉成 422／502 並帶原 reason）；否則內容 < 2,000 字元且沒有 Markdown 標題行（`^#{1,6}\s`）→ decompose（Bridge `POST /autoclaude/decompose`，422 原樣轉）；否則 LLM。`parsedResult.path ∈ {sdd, llm, decompose}` 一律寫入。
- **有界閘在後端一律重現**（三條路徑都套，不信任上游）：每 Goal 任務數 ≤ 24（`max_steps`）、Goal 依賴 Kahn 無環（`cycle`；草案若無依賴欄位即視為無邊）、每 Task 的 description 與 passCriteria 非空（`empty_prompt`）、每步 prompt（description＋passCriteria 組裝後）≤ 20,000 字元（`prompt_too_long`，Architecture L-9）。違反回 422 `{code:422, reason:"bounded_gate_violation", errors:[{gate, detail, location}]}`，`import_records.status` 退回 `UPLOADED`、`parsed_result.error` 記原因；**不截斷不修剪**。`PUT /import/{id}/result` 重新過閘。
- **加密**：`CONSOLE_ENCRYPTION_KEY`（base64 編碼的 32 bytes）缺或長度不對＝啟動失敗（與 JWT_SECRET 同款 fail-fast，做在 `@ConfigurationProperties` 驗證）；AES-256-GCM，密文字串格式 `v1:<iv base64>:<ciphertext base64>`；GET 回 `••••••••`＋`hasValue`；`?reveal=true` 只准 ADMIN 且寫 audit_log。測試用固定測試金鑰放 `src/test/resources/application-test.yml`（不是真機密，註解寫明）。
- **Rate limiting**：Bucket4j（`com.bucket4j:bucket4j-core`，版本現查 Maven Central，釘在 build.gradle.kts 版本區）in-memory，每 IP 每分鐘 100 次，只套 `/api/**`；超限 429 ApiError `reason:"rate_limited"` 並帶 `Retry-After`。設定 `console.security.rate-limit.enabled`（預設 true；測試 profile 預設 false），但必須有一支 IT 開著它打 101 次驗第 101 次 429。
- **審計**：既有 `AuditLoggingFilter` 的 log 行保留，另把寫入端點（POST／PUT／PATCH／DELETE）在同一處落 `console.audit_log` 一列（非同步或同步皆可，但失敗不得影響主請求）。
- **角色**：讀＝VIEWER 以上；匯入／parse／signoff／confirm＝OPERATOR 以上；settings 寫入、reveal、export／import、test-connection＝ADMIN。角色名沿用既有 `infrastructure/security`。
- **Bridge client**：`application/port/out/AgentBridge.java` 本棒只放 `decompose`、`approveDraft`、`sddCompile`、`health` 四個方法（B2 會在同一介面加 runs 系列；方法名照契約 §3）＋ `adapter/out/bridge/BridgeHttpAdapter.java`（Spring `RestClient`，base URL 取 `ENGINE_BRIDGE_URL`，預設 `http://localhost:8081`）。測試用 `MockRestServiceServer`（免新依賴）。LLM client 同法（`application/port/out/LlmClient.java` ＋ `adapter/out/llm/OpenAiCompatibleClient.java`）。
- **檔案文字抽取**：PDFBox 3.x（`org.apache.pdfbox:pdfbox`）、POI（`org.apache.poi:poi-ooxml`），版本現查並釘版；> 10MB → 413；副檔名不在 `.md/.pdf/.docx` → 415；抽出文字為空 → 422 `empty_document`。`sourceContent` 存抽出的純文字。
- **confirm 的交易**：單一 `@Transactional`：建 Project（`signedOff=true`、by／at 承襲 import、`autonomyLevel`／`executionPath` 取 ParseOptions）→ Goals（含 `dependsOn` 若有）→ Tasks；寫回 `import_records.project_id`、`status=IMPORTED`；回 201 `ProjectResponse`。decompose 路徑在 signoff 時逐一呼叫 Bridge `:approve`（409 `already_signed_off` 視為成功；404 → Console 409 `draft_expired`）。
- **新依賴**只准上面點名的（PDFBox、POI、Bucket4j）；需要別的先在交卷〈沒做／偏離〉提案，不要先加。

## 測試要求
- 單元：有界閘四條（25 任務、成環、空描述、prompt 20,001 字元的 422 形狀逐欄）；路徑選擇規則三分支；LLM 回應解析（含圍欄、非 JSON）；AES 加解密（往返、壞密文、錯金鑰）；SSRF 校驗（私網／loopback／link-local／userinfo／十六進位 IP／假 resolver rebinding／redirect）；token_guard 跨鍵校驗（單鍵 PUT 讀對端鍵）；valueType 與 validationRule 校驗；export 遮罩／import 跳過佔位。
- 整合（Testcontainers PG18 ＋ `MockRestServiceServer` 當 Bridge 與 LLM）：匯入文字 → parse（假 chat completions 回三層 JSON）→ 草案 → PUT result 編輯 → signoff → confirm → 專案存在且全部 signedOff；parse 遇 25 任務 → 422 且 status 退回 UPLOADED；decompose 路徑（假 Bridge 回 draft）→ signoff 打 `:approve`；sdd 路徑（假 Bridge 422）→ 422 原 reason；upload .md／.pdf／.docx 各一（用測試資源檔）、11MB → 413、`.txt` → 415；settings 全流程（GET 分組、PUT、敏感鍵無 confirm 409、reveal 非 ADMIN 403、token-guard 原子 400／200、reset、history 分頁、export／import）；rate limit 101 次 → 429；viewer 寫入 403、無 token 401；notifications/summary 三個數字。
- `jacocoTestCoverageVerification` ≥ 80% 仍過；ArchUnit A1～A6 仍綠；Checkstyle 0 warning。

## 閘門（自己跑、逐字貼關鍵行；長輸出導檔）
```powershell
Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\backend; .\gradlew.bat clean build > "<scratchpad>\gradle.log" 2>&1; $rc = $LASTEXITCODE; Pop-Location; "rc=$rc"; Select-String -Path "<scratchpad>\gradle.log" -Pattern 'Test result|BUILD'
Select-String -Path D:\CursorProject\AISDCL_Agent\AgentConsole\backend\build\reports\jacoco\test\html\index.html -Pattern '<tfoot>.*</tfoot>' | ForEach-Object { $_.Matches.Value }
```
- bootRun 冒煙（PG 容器照 `backend/README.md`；環境變數另加 `CONSOLE_ENCRYPTION_KEY`、`CONSOLE_SECURITY_OUTBOUND_ALLOWLIST=localhost,127.0.0.1`；用 `run_in_background: true` 起，交卷前 `Stop-Process` 並 `docker rm -f`）：`Invoke-RestMethod` 登入 → `GET /api/v1/settings` 貼分類鍵數 → `PUT /api/v1/settings/execution/token-guard` 以 halt≤compact 貼 400 body → `POST /api/v1/import/text` → `POST /import/{id}/parse` 對準一支你在 scratchpad 寫的 Python 假 chat-completions server（`http://127.0.0.1:<port>`，固定回三層 JSON；先把 `model.apiUrl` 設成它）→ signoff → confirm → `GET /api/v1/projects/{id}` 貼 `signedOff=true` 與 goals 數；`GET /v3/api-docs` 貼 paths 數與 Phase 3／6 端點清單。
- 交卷前 `git -C D:\CursorProject\AISDCL_Agent status --porcelain` 全部落在 `AgentConsole/backend/**` 與你的 RTM 回填檔。

## RTM 回填（不要直接改 RTM.md——多個 agent 並行會互踩）
把你完成列的四格寫到 `AgentConsole/docs/06_quality/rtm_backfill_W3B1.md`（表格：ID｜實作檔｜自動測試｜狀態；狀態只能填 `✅ 實作+測試` 或 `🟡 部分`＋缺什麼），涵蓋 US-I-01～10（BE 側）、US-S-01～08（BE 側）、API-IMP-01～06、API-SGN-01、API-SET-*、API-NTF-01、NFR-9.2-*（rate limit／audit／SSRF／加密）。QA 會合併進 RTM.md。

## 交卷
照 COMMON_CONTEXT〈交卷格式〉：`STATUS:` 首行；〈做了什麼〉；〈驗證證據〉每道閘門指令＋關鍵行；〈契約漂移〉；〈沒做／偏離〉；〈給 W3-B2 的提醒〉（AgentBridge 介面現況、ConfigMaterializer 需要的 settings 讀取 API、加密解密入口、測試 profile 的開關）。不准 commit／push、不派子 agent、不留背景行程。

## 主控裁決補充（2026-10-15，依獨立 Architect 審查 AR-xx；與本檔上文衝突時以本節與契約 v1.1 為準）
- **失敗存放（AR-07）**：V5 另加 `import_records.parse_path VARCHAR(20)` 與 `last_parse_errors JSONB`；有界閘違規回 422、`last_parse_errors` 存 `errors[]`、`status` 退回 UPLOADED；`parsed_result` 解析前為 null（上文的 `parsed_result.error` 作廢）。
- **`model.apiUrl` 語意（AR-09）**：＝完整 chat-completions 端點 URL，Console 的 LLM 路徑直接 POST 它（不自動補 `/v1/chat/completions`），物化時原樣當引擎 `minimax.base_url`。V5 以 UPDATE 把 `model.apiUrl` 的 value／default_value 改成引擎預設的完整端點（現查 `AutoClaude/autoclaude/utils/config.py` 的 minimax base_url 預設字串）；Console outbound allowlist 預設對齊 Bridge：`api.minimax.io,api.minimax.chat`。
- **SSRF 釘 IP（AR-10）**：允許新增 Apache HttpClient 5（`org.apache.httpcomponents.client5:httpclient5`，Spring Boot BOM 管版本）：自訂 `DnsResolver` 釘住已驗證 IP、Host 標頭與 TLS SNI 用原 host、不跟 redirect；test-connection 與 LLM client 都走它。allowlist 內的 host 解析到私網／loopback 仍拒（契約 D-47）；本機假 server 的放行＝`console.security.allow-loopback=true`（只在 e2e／test profile 載入，契約 §5.0.1／附錄 D.2），所以你的 bootRun 冒煙要以 e2e profile 啟動；mock 旗標是 `console.execution.mock-env`（map），不是 `mock-cli`。
- **限流（AR-06）**：鍵＝JWT subject（未認證才用 IP）；`console.security.rate-limit.trust-forwarded-for` 在 docker／e2e profile 為 true 且只信任 nginx；`monitor.refreshIntervalMs` 的 validation_rule 最小 10000。
- **nginx（AR-04）**：你的檔案範圍放寬到 `AgentConsole/docker/nginx/conf.d/default.conf`：`/api/v1/import/` location（`client_max_body_size 11m`、`proxy_read_timeout 180s`）與 `/api/v1/settings/import`（`client_max_body_size 2m`），規格見契約 §0.7。
- **Phase 2 DTO（AR-14）**：`CreateTaskRequest`／`UpdateTaskRequest` 的 `maxRetries` 加 `@Max(20)`（Bridge 上限）。
- **通知摘要（AR-08）**：`bridgeConnected`／`bridgeCheckedAt` 本棒回 null；B2 接探測環時改同一支 controller。
- **既有測試須同步改（AR-16，不是刪）**：`OpenApiIT::theDocumentListsExactlyTheEndpointsOfPhaseOneAndTwo`（paths 數）、`SchemaMigrationIT::flywayAppliedVersionsOneToFourSuccessfully`、`::seedHasAllSixCategoriesWithTheDocumentedParameterCounts`、`::onlyTheApiKeyIsEncryptedAndItsValueIsEmpty`（V5 後 `dbDsn` 是第二把加密鍵）。
- **reason 常數**：一律用契約附錄 B 的中文逐字常數（上文的英文蛇形只是示意）；後端集中在 `ErrorReasons`。
- **路徑選擇**：除 `specDir` 外，也依契約探測 `executionPath` 下的凍結規格（§3.3）。
