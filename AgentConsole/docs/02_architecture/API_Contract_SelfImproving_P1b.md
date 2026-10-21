# API 契約 — SelfImproving 唯讀鏡像（P1b）

**版本**：v1.0｜**日期**：2026-10-21｜**作者角色**：Developer 依實作如實起草，主控於 SCG-5 落檔（TCS-SelfImprovingMirror-P1b R26 (2) ①）
**讀者**：後端開發者（Spring Boot 4.1／Java 21）、前端開發者（Next.js 16）、Bridge 維護者（Python）、QA（依本契約驗收）
**與前代契約的關係**：本檔是 PRD §9.1〈C18 檔名表〉所稱的「契約新版」，**後繼**凍結的 [API_Contract_P3-6.md](API_Contract_P3-6.md)（v1.5）。P3-6 契約（含 §0.3 第 8 點）與 `openapi-p3-6.yaml` 一律不改；兩者對同一事項說法不同處（只有一處：「404 的 reason 省略」慣例的例外清單），以本檔為準。
**機器可讀版**：本檔不另附 OpenAPI 檔。機器可讀的真相源是 backend 執行期的 `/v3/api-docs`（springdoc；六個 `/api/v1/si/**` 路徑各只有 `get`，由 `OpenApiIT` 與 `SiMirrorApiIT` 鎖住），入庫快照為 `frontend/lib/api/schema.d.ts`（`AT-940-8-2`）。兩者與本文衝突時以本文為準並回報修正。
**對應需求**：根層 `docs/01_requirements/SelfImproving_PRD.md` 的 FR-SI-32（AC-SI-32-1～32-4、32-6）、§9.2（`export --json` 輸出）、§9.3、§9.4；TCS `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingMirror-P1b-20261021.md`（F-901、US-901～US-907、R1～R29）；Architecture §10.3、§11.1。

> **使用方式**：Bridge 與 backend 開發者照 §1（backend 六端點）、§2（Bridge 六端點與子行程）施工；§3 是兩層之間的失敗對映表；前端照 §4 確認每個畫面元素的資料來源；QA 照各端點的失敗表與 §5 驗收。**本契約沒有待裁決的規格點。**

**版本沿革**

| 版本 | 日期 | 範圍 | 對應來源 |
|------|------|------|----------|
| v1.0 | 2026-10-21 | P1b 初版：console-api 六個 GET、Bridge 六個 GET、子行程通道、兩個新 reason、「404 的 reason 省略」慣例的第二個例外 | TCS-SelfImprovingMirror-P1b（鍵 `agentconsole-si-mirror`）R4～R10、R19、R23、R26 |

> **v1.0 變更摘要**：
> 1. **新路徑**：console-api 6 個（`GET /api/v1/si/status`、`/observations`、`/events`、`/proposals`、`/proposals/{id}`、`/runs`；`OpenApiIT` 路徑 61→67、操作 70→76）、Bridge 6 個（`GET /si/*`）。全部只有 GET：沒有任何寫入端點。
> 2. **資料來源**：Bridge 以子行程呼叫根層 CLI `tools/selfimproving.py export --json --kind <k>`，把輸出**解析後逐值透傳**；backend 只把物件鍵由 snake_case 對映成 camelCase、值不動；兩層都不重算、不快取。
> 3. **新 reason 兩個**：`si_unavailable`（503；帶 `cause`、`detail`）、`si_not_found`（404；帶 `id`）。
> 4. **404 例外**：`si_not_found` 是「404 的 `reason` 省略」慣例的**第二個**例外（第一個是 P3-6 §0.3 第 8 點的 `rtm_not_found`）。
> 5. **部署**：Bridge 容器需 `SI_ROOT`；`docker-compose.yml` 以唯讀 bind 掛入 CLI 與帳本（TCS R23）。

---

## 0. 共通約定

### 0.1 權威順位與事實來源

| 順位 | 來源 | 範圍 |
|------|------|------|
| 1 | 根層 `SelfImproving_PRD.md`（FR-SI-32、§9.2～§9.4） | 需求；`export --json` 的輸出形狀與游標語意 |
| 2 | 本契約 | P1b 的 HTTP 形狀、查詢參數、錯誤對映 |
| 3 | `AgentConsole/engine-bridge/README.md`、`app/si_cli.py`、`app/routers/si.py`、`tests/test_si_*.py` | **Bridge 行為的唯一真相源** |
| 4 | Architecture §10.3、§11.1、§12.1 L-14、§12.2 V-12；TCS R1～R29 | 架構決策與驗收 |
| 5 | 根層 CLI `tools/selfimproving.py export` 與其 TCS | 回應內容的真相；本契約不複寫其欄位語意，§1.7 只列已知鍵 |

### 0.2 封包、型別與格式

| 項目 | 約定 |
|------|------|
| 前綴與編碼 | `/api/v1/si/**`；UTF-8 JSON；只有 `GET`。 |
| 成功封包 | 沿 P3-6 §0.2 的 `ApiResult<T>`：`{ "code":200, "message":"success", "data":<export 物件>, "timestamp":"…", "traceId":"…" }`；`data` 即 Bridge 的 export 物件（見下兩列與 §1.7）。 |
| 欄名對映（R9；「snake_case↔camelCase 對映」的唯一定義） | `data` 內**所有層級的所有物件鍵**依 `camel(key)`：鍵若符合 `^[a-z][a-z0-9]*(_[a-z0-9]+)+$`，依 `_` 切段、首段不動、其後各段首字元轉大寫（數字不變）後串接（`http_status`→`httpStatus`、`touched_sha256`→`touchedSha256`、`marks_kv`→`marksKv`、`schema_rev`→`schemaRev`）；**其餘鍵恆等**（`digest8`、`PROP-SI-004`、`quota-band`、中文鍵、已含大寫的鍵、單字鍵、`a__b`、`_x`、`x_`）。兩個來源鍵轉出同一名字時不丟欄：不變的鍵先保有名字，轉換後撞名者保留原鍵。實作與測試入口：`SiKeyNames.camel(String)`／`camelKeys(Object)`（`com.aisdlc.console.adapter.in.web.dto`）。 |
| 值透傳 | 值（字串、數字、布林、`null`、陣列元素的個數與順序）一律不動；`null` 必須保留（`headSha`、`nextSince`、`cooldown`、`verdict`、`suspended` 的 `null` 有語意）；`card` 字串逐位元組不動（含 `\n` 與全形字元）；**Bridge 回的任何鍵（含 backend 尚不認得者，例如日後根層加的 `buckets`、`consolePending`）都出現在回應**，不得靜默丟棄。 |
| 不重算、不快取 | backend 與 Bridge 都不折疊事件、不算 digest、不判 NOT-EVALUABLE（以下簡稱 NE）、不補 `generatedAt`（它是子行程輸出的值，不是 backend 時鐘）；每個 backend 請求恰一次 Bridge 呼叫、每個 Bridge 請求恰一次子行程。 |
| 時間 | `generatedAt` 為 ISO-8601 帶 offset 的字串（秒精度，例 `2026-10-21T09:00:00+08:00`）；client 以 `Date.parse` 類函式解析，不比對字串，也不參與差分。 |
| 分頁 | **不採 P3-6 的 `{content,page,size,…}` 分頁封包**；SI 清單沿 `export` 的游標分頁：查詢參數 `since`、`limit`，回應的 `items`、`truncated`、`nextSince`（§0.3）。 |
| null 與缺席 | 與 P3-6 §0.2 相反：**SI 的 `data` 內缺鍵與 `null` 是不同語意，client 不得視為等價**（例：壞列 `valid:false` 沒有 `id`；`headSha` 為 `null` 代表 git 量不到；`cooldown` 為 `null` 代表沒有冷卻）。`ApiError.details` 內仍不輸出 null 值（P3-6 §0.2）。 |

### 0.3 游標分頁語意（四個清單端點共通；來源 PRD §9.2）

- `since`（選填；整數 ≥0）：只回「游標」嚴格大於 `since` 的項目。游標：`events` 取 `seq`；`observations`、`proposals`、`runs` 取 ID 的數字部分（`PROP-SI-004`→4）。項目依游標遞增排序。
- `limit`（選填；整數 ≥1）：每頁最多幾筆；缺省與上限＝根層協定參數檔 `docs/06_quality/SelfImproving_Protocol/params.json` 的 `export_limit_max`（現值 500）。**上限不在 Bridge 或 backend 複製**：超過上限時 CLI 以 rc 3 失敗，Bridge 依 §2.3 回 503 `si_unavailable`（`cause=nonzero_rc`）——語意上是使用者輸入錯誤卻被標為「SI 不可用」，是「rc 非 0 即 503」字面的後果；前端永不送超限值（頁大小常數 `SI_PAGE_LIMIT`＝100）。
- 回應：`truncated` 為 true 表示尚有下一頁，此時 `nextSince`＝本頁最後一筆的游標，以它作為下一次請求的 `since`；已無下一頁時 `truncated=false`、`nextSince=null`。`status` 不分頁（`items` 為單元素陣列、`nextSince=null`、`truncated=false`）。
- 帳本在兩次請求之間被另一視窗改動時，分頁可能短暫不一致（不在偵測範圍；回應帶 `headSha` 與 `generatedAt` 供人對照）。

### 0.4 錯誤封包與 `reason` 常數

錯誤一律使用 Phase 1+2 的 `ApiError`（P3-6 §0.3）：`{ code, message, reason?, errors:[{field,message}], details?, timestamp, traceId }`。

1. **任何失敗的回應都沒有 `data`**——不回空表、不回部分資料、不回上一次的結果（PRD AC-SI-32-3）。
2. **兩個新 reason**（英文識別字；後端 `ErrorReasons`，前端 `lib/domain/si.ts` 的 `SI_REASONS`；兩邊字串逐字相同，Architecture §11.1 為對拍來源）：

| reason | 狀態碼 | `details` | 意義 |
|--------|:------:|-----------|------|
| `si_unavailable` | 503 | `cause`、`detail`（皆有才帶；逐字轉自 Bridge） | SelfImproving 資料面不可用：Bridge 無法取得有效的 export 輸出（§2.3 九種 `cause`） |
| `si_not_found` | 404 | `id`（有才帶） | 單筆提案不存在：`{id}` 格式合法但查無此提案 |

3. 前端把這兩個常數放在 `lib/domain/si.ts`，**不進** `lib/api/reasons.ts` 的 `REASONS` 集合（`reasons.test.ts` 的雙向鎖不受影響；`AT-940-5-1`）。
4. **「404 的 reason 省略」慣例的例外**：P3-6 §0.3 第 8 點稱 `rtm_not_found` 是該慣例的**唯一**例外；自本契約起例外有兩個——`rtm_not_found` 與 `si_not_found`。一般 404（未定義路徑、資源不存在）仍不帶 `reason`。凍結的 P3-6 契約與 `openapi-p3-6.yaml` 的字樣不改（另由主控登 OBS）；程式內四處註解（`NotFoundException`、`ErrorResponseDocumentation`、`ErrorReasons.RTM_NOT_FOUND`、`reasons.ts`）已改述為「例外之一」。
5. **`invalid_request` 是 Bridge 層的 reason**：Bridge 回 422 時，backend 回應的頂層 `reason` 是既有常數 `引擎拒絕此請求`（`ErrorReasons.BRIDGE_REJECTED`），`invalid_request` 只經 `details.bridgeReason` 帶出，所以前端不為它建 reason 常數。
6. 其餘失敗沿用既有常數（P3-6 附錄 B）：`引擎橋接服務無法連線`（502）、`引擎橋接服務錯誤`（502）、`引擎橋接服務逾時`（504）。

狀態碼語意（SI 範圍）：

| 碼 | 語意 |
|----|------|
| 200 | Bridge 回 200 且本文為合法 JSON 物件 |
| 400 | `since` 或 `limit` 型別不符（例 `since=abc`；訊息 `參數 since 的值格式不正確`），或範圍不合（`since=-1`、`limit=0`；`errors[]` 一筆，`field` 為 `since` 或 `limit`）。**不觸及 Bridge** |
| 401 | 無有效 JWT（`UNAUTHENTICATED`／`TOKEN_EXPIRED`／`TOKEN_INVALID`）。**不觸及 Bridge** |
| 403 | 非 GET 方法且角色為 VIEWER（`SecurityConfig` 既有規則）。GET 不會 403（VIEWER 以上可讀） |
| 404 | `si_not_found`（單筆提案）；或未定義的 `/api/v1/si/…` 路徑（一般 404，無 `reason`） |
| 405 | 非 GET 方法且角色為 OPERATOR 或 ADMIN（沒有任何非 GET 對映） |
| 422 | Bridge 回 422 `invalid_request`（例：`{id}` 格式不合）：頂層 `reason`＝`引擎拒絕此請求`，`details.bridgeReason`＝`invalid_request`、`details.violations` 逐項原樣 |
| 502 | Bridge 無法連線（`引擎橋接服務無法連線`）；Bridge 回其他 4xx／5xx，或 200 但本文不是 JSON 物件（`引擎橋接服務錯誤`，`details.bridgeStatus`） |
| 503 | `si_unavailable` |
| 504 | 讀取逾時（`引擎橋接服務逾時`；約 20 秒；不重試） |

### 0.5 認證、角色、逾時

- **角色**（ADMIN ⊃ OPERATOR ⊃ VIEWER）：六個端點皆 `GET`，**VIEWER 以上可讀**；`SecurityConfig` 零改動，既有規則（`GET /api/v1/**`＝VIEWER 以上、其餘＝OPERATOR 以上）涵蓋。無有效 JWT＝401。
- **零寫入**：沒有任何非 GET 對映（`SiController` 的 `@RequestMapping` 不帶 `method`，不含 `@PostMapping` 等；ArchUnit 鎖 `AT-932-2-5`）。非 GET：VIEWER＝403、OPERATOR／ADMIN＝405。
- **對 Bridge 的呼叫**：每個請求帶 `X-Trace-Id`（沿 P3-6 §0.4 第 6 點），**不帶** `X-Bridge-Token`（權杖只屬寫入動詞）；連線逾時 2 秒、讀取逾時 20 秒（大於 Bridge 子行程逾時 15 秒，使 Bridge 的 503 不被 backend 的 504 蓋掉）、**不重試**；讀取 Bridge 本文上限 8 MiB（等於 Bridge 子行程 stdout 上限）。
- **瀏覽器不直連 Bridge**：Bridge 無認證、只准 backend-net（Architecture §12.1 L-6）；`docker-compose.yml` 的 engine-bridge 服務沒有 `ports`（`AT-932-4-4`）。

---

## 1. console-api 端點（`/api/v1/si/**`）

### 1.0 總表（6 個，皆 GET）

| # | 方法與路徑 | operationId | 查詢參數 | Bridge 呼叫 |
|---|-----------|-------------|----------|-------------|
| API-SI-01 | `GET /api/v1/si/status` | `getSiStatus` | 無（任何查詢參數忽略、不轉發） | `GET /si/status` |
| API-SI-02 | `GET /api/v1/si/observations` | `getSiObservations` | `since`、`limit` | `GET /si/observations[?since=&limit=]` |
| API-SI-03 | `GET /api/v1/si/events` | `getSiEvents` | `since`、`limit` | `GET /si/events[?since=&limit=]` |
| API-SI-04 | `GET /api/v1/si/proposals` | `getSiProposals` | `since`、`limit` | `GET /si/proposals[?since=&limit=]` |
| API-SI-05 | `GET /api/v1/si/proposals/{id}` | `getSiProposal` | 無（忽略、不轉發） | `GET /si/proposals/{id}`（`id` 嚴格 percent-encode） |
| API-SI-06 | `GET /api/v1/si/runs` | `getSiRuns` | `since`、`limit` | `GET /si/runs[?since=&limit=]` |

共通規則：
- **未知查詢參數不轉發**：送往 Bridge 的 URL 只由 kind 與 `since`、`limit` 組成；轉發時依固定次序先 `since` 後 `limit`，`null` 不進網址；`status` 與單筆提案不轉發任何查詢參數。
- 回應 `data`＝export 物件經 §0.2 欄名對映；形狀見 §1.7。失敗對映見 §0.4 與 §3。

### 1.1 `GET /api/v1/si/status`　SelfImproving 狀態摘要　〔API-SI-01／US-901〕

- 回應 200：`data.kind="status"`；`data.items` 恰一個元素（根層 `si status --json` 的物件，欄位見 §1.7）；不分頁。
- 失敗：401、502、503 `si_unavailable`、504。

### 1.2 `GET /api/v1/si/observations`　觀察帳本　〔API-SI-02〕

- 查詢：`since`、`limit`（§0.3）。
- 回應 200：`data.kind="observations"`；`items` 為帳本逐列；無法解析的壞列（欄數不是 9）以 `{line, raw, valid:false}` 出現，`problems[]` 逐項說明。
- 失敗：400、401、502、503、504。

### 1.3 `GET /api/v1/si/events`　事件帳本　〔API-SI-03〕

- 同 §1.2；`items` 為事件帳本逐行（多型，鍵依 `kind` 而異，原樣只對映鍵名）。

### 1.4 `GET /api/v1/si/proposals`　提案清單　〔API-SI-04〕

- 同 §1.2；每筆含狀態、route、digest、verdict、cooldown 與卡面 `card`（`si card` 的逐位元組輸出；量不到時為 `null` 並於 `ne[]` 說明）。

### 1.5 `GET /api/v1/si/proposals/{id}`　單筆提案　〔API-SI-05〕

- 路徑：`id` 例 `PROP-SI-004`。backend **不驗格式**（單一真相在 Bridge）：原樣嚴格 percent-encode 成單一路徑段後交給 Bridge——只有 RFC 3986 非保留字元（`A-Z a-z 0-9 - . _ ~`）原樣，其餘位元組（UTF-8）一律 `%XX`；整段恰為 `.` 或 `..` 時點字元亦編為 `%2E`（避免被 HTTP 堆疊當路徑穿越正規化）。含編碼斜線、編碼百分號、分號、反斜線或未正規化路徑段的網址，在進入控制器前即被 Spring Security 預設的 `StrictHttpFirewall` 以 400 拒絕。
- 不收任何查詢參數（忽略、不轉發）。
- 回應 200：`items` 恰一筆。
- 失敗：404 `si_not_found`（格式合法而查無；`details.id`）、422（格式不合，經 `details.bridgeReason=invalid_request`）、401、502、503、504。

### 1.6 `GET /api/v1/si/runs`　運轉　〔API-SI-06〕

- 同 §1.2；`items` 為運轉摺疊（開關事件序號、觸發、研究事件、提案結果）。

### 1.7 回應形狀（資訊性；權威＝根層 PRD §9.2 與 CLI `export`；backend 與前端不依賴未列的鍵）

最外層（所有 kind 相同；鍵序固定；以下為對映後的鍵名）：

```json
{
  "schemaRev": 1,
  "kind": "observations",
  "generatedAt": "2026-10-21T09:00:00+08:00",
  "headSha": "<40 位十六進位字串，或 null>",
  "items": [],
  "nextSince": null,
  "truncated": false,
  "ne": [{ "field": "head_sha", "reason": "git-unavailable" }],
  "problems": [{ "subject": "OBS-SI-012", "code": "ROW-ARITY", "detail": "欄數不是 9 或行未以 | 結尾" }]
}
```

`ne[]`：量不到的欄位逐一列出、不省略（NOT-EVALUABLE 不是 0、無或通過）；`problems[]`：帳本結構層問題（壞列、壞行）。**兩者非空都不是錯誤**；空 `items` 只在帳本真的為空時合法。

各 kind 的 `items` 元素（對映後鍵名）：

| kind | `items` 元素 |
|------|--------------|
| `observations` | 九欄 `id`、`time`、`context`、`symptom`、`evidence`、`category`、`severity`、`disposition`、`marks`（皆字串）＋`marksKv`（標記解析後的鍵值物件，鍵為中文原字）＋`line`（帳本 1 起算實體行號）；根層 P2 交付後另有 `buckets[]`（模組桶；缺席時前端停用模組桶篩選）；壞列＝`{line, raw, valid:false}`（無 `id`） |
| `events` | 事件原樣（不加鍵）：共通 `seq`、`t`、`kind`、`by`，其餘依 `kind`（例：`run.open` 帶 `run`、`trigger`、`coords[]`、`headSha`；`research.scan` 帶 `sources[]`、`sourcesSha256`、`fetchedAt`；`attr` 帶 `id`、`type`、`obs[]`、`items[]`）；鍵名只經 §0.2 對映 |
| `proposals` | `id`、`state`、`route`、`cls`、`action`、`run`、`rev`、`digest`、`target[]`、`touched[]`（可為 null）、`touchedCount`（可為 null）、`sources[]`、`createdSeq`、`lastSeq`、`verdict`（可為 null）、`flags[]`、`cooldown`（物件或 null）、`card`（字串或 null；為 null 時 `ne[]` 有 `proposals.<id>.card` 一項） |
| `runs` | `id`、`openedSeq`、`closedSeq`、`trigger`、`headSha`、`research`（`{kind, seq}` 或 null）、`propIds[]`、`outcome`（`{<PROP ID>: <狀態>}`） |
| `status` | 單元素陣列；元素至少含 `eventsDetected[]`、`openRuns[]`、`pendingProps[]`（`{id, rev, state, route, digest8}`）、`suspended`（可為 null）、`cooldowns[]`、`skipReasons{}`（鍵如 `quota-band`，恆等不改名）、`capacity`；依根層版本另可有 `unavailable[]`（`{trigger, reason}`）、`frictionReconcile`、`rootCauseChanges`、`reopenCandidates`、`pendingWindows`、`noEvent` 等——未知鍵一律原樣透傳 |

---

## 2. Bridge 端點（`/si/*`；Bridge 內部契約，只給 backend 呼叫）

### 2.1 六個 GET（`app/routers/si.py`；`APIRouter(prefix="/si")`）

| 路徑 | 查詢參數 | 子行程 argv 尾段 |
|------|----------|------------------|
| `GET /si/status` | 無 | `--kind status` |
| `GET /si/observations` | `since`、`limit` | `--kind observations [--since N] [--limit N]` |
| `GET /si/events` | 同上 | `--kind events [--since N] [--limit N]` |
| `GET /si/proposals` | 同上 | `--kind proposals [--since N] [--limit N]` |
| `GET /si/proposals/{id}` | 無 | `--kind proposals --id <id>` |
| `GET /si/runs` | 同上 | `--kind runs [--since N] [--limit N]` |

輸入驗證（**皆在啟動子行程之前**；不合規輸入不啟動子行程）：
- 清單類只收 `since`（整數 ≥0）與 `limit`（整數 ≥1）；型別或範圍不合（`since=abc`、`since=-1`、`limit=0`）→ 422 `invalid_request`（沿 Bridge 既有 `RequestValidationError` 處理器）。
- **任何其他查詢參數名**（含 `/si/status` 與 `/si/proposals/{id}` 上的 `since`、`limit`）→ 422 `invalid_request`，`violations[]` 每個未知參數一筆 `{field:<參數名>, rule:"unknown_parameter", message}`。
- `{id}` 須符 `^PROP-SI-\d{3,}$`（ASCII 數字、整串比對）；不符 → 422 `invalid_request`（`violations[]` 一筆 `{field:"id", rule:"invalid_format", message}`；路由器在路徑層就擋下的形態會回 404，兩者皆不啟動子行程）。格式合法而 CLI 回 `items: []` → 404 `si_not_found`，本文 `{"code":404,"reason":"si_not_found","id":"<id>"}`。
- 非 GET 一律 405（FastAPI 預設）；未定義的 `/si/…` 路徑 404。

200：本文為子行程輸出**解析後的 export 物件逐值透傳**（鍵序保留、非 ASCII 不跳脫；Bridge 不增刪改任何鍵，含 `generated_at`、`head_sha`、`ne`、`problems` 與未知鍵）。SI 不可用**不影響** `/health` 與 `/health/deep`（SI 與 SDD 同為選用面，不進健康判準）。

### 2.2 子行程通道（`app/si_cli.py`；Bridge 對根層 CLI 的**唯一**通道）

| 項目 | 規格 |
|------|------|
| argv | 恆為 `[sys.executable, <SI_ROOT>/tools/selfimproving.py, "export", "--json", "--kind", <kind>]`，之後依序可接 `--since`、`--limit`、`--id`；**不帶 `--repo`**（預設值＝腳本所在 repo＝`SI_ROOT`）、**不帶 `-I`／`-P`**（3.11 起 `-I` 蘊含 `-P`，腳本目錄不進 `sys.path`，CLI 自己的相對匯入會失敗）。 |
| cwd | `SI_ROOT` |
| 環境 | 白名單加固定鍵：名稱（不分大小寫）為 `PATH`、`SYSTEMROOT`、`TEMP`、`TMP`、`HOME`、`USERPROFILE`、`LANG`、`LC_ALL` 者原樣保留；另加 `PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1`、`GIT_CONFIG_COUNT=1`、`GIT_CONFIG_KEY_0=safe.directory`、`GIT_CONFIG_VALUE_0=<SI_ROOT>`（只放行該路徑，不用 `*`，不寫 `.gitconfig`）；機密與 `BRIDGE_*`、`MINIMAX_API_KEY`、`AUTOSDD_*` 一律不繼承。 |
| 標準輸入輸出 | stdin 為 `DEVNULL`；stdout、stderr 以位元組讀取、UTF-8 解碼；stdout 上限 8 MiB（超過即終止行程樹，`stdout_too_large`）；stderr 只留尾端 1,000 字元。 |
| 逾時 | 15 秒（`SI_CLI_TIMEOUT_SECONDS`）；逾時終止**整棵行程樹**（Windows 上 venv 的 `python.exe` 是啟動器，必須殺整棵）；不留孤兒。 |
| 設定 | 環境變數 `SI_ROOT`：非空者解析為絕對路徑並拒檔案系統根；空白時本機直跑取 monorepo 根，其餘為 `None`（容器內必須設定）；**不併入** `allowed_path_roots`（`AT-940-1-1`）。 |
| 副作用 | 無：不寫任何檔、不快取；Bridge 原始碼對 SI 路徑無寫入形態、不 import 根層 `tools/lib`、argv 動詞只有 `export`（AST 鎖 `AT-932-2-1`）。 |

### 2.3 失敗判定與 503 本文（`cause` 九值；先中者定案）

| 順序 | `cause` | 條件 |
|:----:|---------|------|
| 1 | `si_root_unset` | `SI_ROOT` 為 `None` |
| 2 | `si_script_missing` | `SI_ROOT` 不是目錄，或 `<SI_ROOT>/tools/selfimproving.py` 不是檔案 |
| 3 | `spawn_failed` | 啟動子行程拋 `OSError` |
| 4 | `timeout` | 超過 15 秒仍未結束（行程樹已終止） |
| 5 | `stdout_too_large` | stdout 位元組數超過 8 MiB（行程已終止） |
| 6 | `nonzero_rc` | 離開碼非 0（含 `limit` 超過 `export_limit_max` 的 rc 3） |
| 7 | `bad_json` | stdout（UTF-8 解碼、去尾端空白）不是恰好一份 JSON 文件，或解出來不是物件 |
| 8 | `schema_rev_mismatch` | 物件缺 `schema_rev`、不是整數（布林不算），或不等於 Bridge 常數 `SI_EXPORT_SCHEMA_REV`（現值 1） |
| 9 | `bad_shape` | 物件的 `kind` 不等於請求的 kind，或 `items` 不是陣列 |

失敗本文恆為 `{"code": 503, "reason": "si_unavailable", "cause": <上表之一>, "detail": "rc=<n 或 none>; stderr=<尾段>"}`。`<n>` 為離開碼（未啟動，或被 Bridge 終止而沒有離開碼＝`none`）；`<尾段>` 為 stderr（UTF-8、`errors=replace` 解碼）的最後 1,000 個字元；順序 1～3 沒有行程，`stderr=` 之後是 Bridge 自寫的固定說明（含字樣 `SI_ROOT`）。Bridge 日誌只記 kind、cause、rc，**不記 stderr 與任何環境值**。

**合法輸出不是錯誤**：rc 0 且 stdout 為合法 export 物件即原樣回傳，即使 `items` 為空、`ne`／`problems` 非空、stderr 有雜訊、物件含未知的額外鍵。環境缺件使某欄量不到時（例：無 git → `headSha=null`），該欄以 NE 呈現、不省略欄位（`AT-932-3-3`）。

---

## 3. Bridge → console-api 失敗對映（`BridgeHttpAdapter.handle` 與 `SiBridgeErrors`）

| Bridge 回應 | console-api HTTP | 頂層 `reason` | `details` |
|-------------|:----------------:|---------------|-----------|
| 200 且本文為 JSON 物件 | 200 | — | — |
| 503 `si_unavailable` | 503 | `si_unavailable` | `cause`、`detail`＝Bridge 本文逐字（有才帶） |
| 404 `si_not_found` | 404 | `si_not_found` | `id`＝Bridge 本文的 `id`（有才帶） |
| 422 `invalid_request` | 422 | `引擎拒絕此請求` | `bridgeReason`＝`invalid_request`、`violations` 逐項原樣 |
| 其他 4xx 與 5xx | 502 | `引擎橋接服務錯誤` | `bridgeStatus`（Bridge 有 reason 時另有 `bridgeReason`） |
| 連線失敗（拒絕、主機不可解、連線逾時） | 502 | `引擎橋接服務無法連線` | — |
| 讀取逾時 | 504 | `引擎橋接服務逾時` | — |
| 200 但本文不是 JSON 物件（或無法解析） | 502 | `引擎橋接服務錯誤` | `bridgeStatus`＝200 |

注意：(a) 503 `si_unavailable` 與 404 `si_not_found` 是 Bridge 的**明確回報**，不是上游故障，所以不併入「其他 5xx → 502」（`BridgeHttpAdapter.handle` 把兩者與 4xx 同走 `BridgeRejectedException`）；(b) 舊版 Bridge 沒有 `/si/*` 時的 404、403 等其餘 4xx 一律當作上游故障（502），不偽裝成使用者錯誤；(c) `detail` 可含全形字元與換行，原樣轉出；(d) 連線逾時 2 秒、讀取逾時 20 秒、不重試。

---

## 4. 前端消費（`/self-improving`；資訊性，不增加後端義務）

| 畫面元素 | 端點 | 備註 |
|---------|------|------|
| 狀態橫幅 | `GET /api/v1/si/status` | 一個查詢、自成 loading／error／ok 三態；error 時只顯示錯誤，絕不渲染成「無事件」 |
| 觀察分頁 | `GET /api/v1/si/observations` | 游標分頁（`since=<nextSince>`、`limit=100`）；「載入更多」按鈕；篩選只作用於已載入的頁 |
| 提案分頁 | `GET /api/v1/si/proposals` | 同上；卡面 `card` 以純文字（`<pre>`）逐位元組顯示 |
| 事件分頁 | `GET /api/v1/si/events` 與 `GET /api/v1/si/runs` | 兩個獨立查詢（運轉表、事件表各自失敗互不影響） |
| （P1b 頁面未使用） | `GET /api/v1/si/proposals/{id}` | API 層函式 `getSiProposal` 已匯出並有測試；提案分頁以清單取全部 |

- 所有 SI 查詢 `retry:false`、`staleTime:0`、`gcTime:0`：失敗不重試、不顯示舊資料、切分頁即卸載舊面板（回到分頁重新載入）。
- 帳本字串（九欄、標記、卡面、事件 JSON、`ne`／`problems`）一律以 React 文字節點渲染，不經 HTML 或 Markdown；沒有任何寫入型控制項，頁面的所有請求都是不帶本文的 GET。
- 導覽入口取自登記表 `lib/nav/registry.ts`（`id: self-improving`、圖示 `Dna`、`order: 70`、`mobile: false`＝<768 的底部 Tab 不顯示；`roles` 缺＝所有已登入角色皆可見）。
- 瀏覽器不直連 Bridge：前端原始碼沒有任何 Bridge 路徑字面（`AT-932-4-3` 靜態掃描鎖住），`/si/…` 一律經 `/api/v1/si/…`。

## 5. 已知邊界（誠實劃界；不是待修缺陷）

1. **差分只證明頁面＝`export` 輸出**，不證明 `export` 的折疊邏輯正確（PRD AC-SI-32-1）；「同一時刻」實務上是兩次相鄰的呼叫，帳本在兩次之間被另一視窗改動的短暫不一致不在偵測範圍，回應帶 `headSha` 與 `generatedAt` 供人對照（PRD AC-SI-32-3）。
2. **黃金檔是子集比較**：容忍根層日後加欄位，但偵測不到「鍵不變、語意改變」的根層變動——那一類由 `schema_rev` 與根層 TCS 承擔。
3. **容器掛載有兩個未實測風險**：單檔 bind（`HEAD`、`packed-refs`）在主機端 git 以 lock 加 rename 換檔後，容器可能保留舊 inode 使 `headSha` 靜默過期；`packed-refs` 於主機不存在時 `create_host_path: false` 使容器起不來。真容器行為由 V3 決定採設計 A 或 B（Architecture §12.1 L-14、§12.2 V-12）。
4. **`safe.directory` 的環境變數式放行與 git ≥2.31** 未在真容器驗證（V3）。
5. **`limit` 超過 `export_limit_max` 時回 503**（§0.3）：語意上是輸入錯誤而被標為「SI 不可用」；前端永不送超限值。
6. **jsdom 不評估 CSS**：`max-md:hidden` 類別存在不等於 <768 時真的隱藏；真視窗行為由 V2 實測。
