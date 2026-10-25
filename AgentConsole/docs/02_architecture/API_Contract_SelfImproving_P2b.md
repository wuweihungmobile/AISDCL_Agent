# API 契約 — SelfImproving 寫入載體（P2b：決定、觀察新增／更正／關閉、對帳）

**版本**：v1.0｜**日期**：2026-10-25｜**作者角色**：Developer 依實作如實起草，主控於 SCG-5 落檔（TCS-SelfImprovingDecide-P2b W25；D10）
**讀者**：後端開發者（Spring Boot 4.1／Java 21）、前端開發者（Next.js 16）、Bridge 維護者（Python）、主機端入帳者（根層 CLI）、QA（依本契約驗收）
**與前代契約的關係**：本檔是 PRD §9.1〈C18 檔名表〉所稱的契約新版，**後繼** [API_Contract_SelfImproving_P1b.md](API_Contract_SelfImproving_P1b.md)（讀面六個 GET，v1.0 不改）與凍結的 [API_Contract_P3-6.md](API_Contract_P3-6.md)／`openapi-p3-6.yaml`（一律不改）。P1b 契約的「零寫入」前提自本版改寫為：**SelfImproving 帳本只有根層 CLI 能寫；Console 只產生並落地經簽章的稽核 JSON**（入帳是主機端 pull 模式）。
**機器可讀版**：本檔不另附 OpenAPI 檔。機器可讀的真相源是 backend 執行期的 `/v3/api-docs`（springdoc；SI 路徑由 P1b 的 6 條增為 10 條、`OpenApiIT` 釘路徑 71／操作 81），入庫快照為 `frontend/lib/api/schema.d.ts`（AT-950-10-2）。兩者與本文衝突時以本文為準並回報修正。
**對應需求**：根層 `docs/01_requirements/SelfImproving_PRD.md` v0.10 的 FR-SI-33（AC-SI-33-1、33-2）與 FR-SI-35（AC-SI-35-1～35-5）的 AgentConsole 半、§9.1 C18／C21、§9.3；TCS `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingDecide-P2b-20261024.md`（F-902、US-908～US-916、W1～W25；Stage-2 凍結 `sha256:8f591aed394a0a78bbd2417e82d725989abcf273d05433404618f083d81239c9`）；Architecture §10.2／§10.3、§11.1、§12.1 L-14。**位元組契約的權威＝根層 `tools/lib/selfimproving/consoleaudit.py`**（Console 簽出的檔必須被它收下；本檔只複述、不另定義）。

> **使用方式**：backend 開發者照 §1 施工、Bridge 開發者照 §2、簽章與稽核 JSON 照 §3、對帳照 §4、部署照 §5；前端照 §6 確認每個控件的資料來源與閘；QA 照各端點的失敗表與 §7 驗收。本契約沒有待裁決的規格點（⚖ 已於 TCS §7.1 預設裁決）。

**版本沿革**

| 版本 | 日期 | 範圍 | 對應來源 |
|------|------|------|----------|
| v1.0 | 2026-10-25 | P2b 初版：console-api 四個 POST 加一個對帳 GET；Bridge 三個寫入 POST 加 validate；稽核 JSON 與 HMAC 契約；Flyway V13 `si_console_writes`；三個新 reason | TCS-SelfImprovingDecide-P2b（鍵 `agentconsole-si-decide`）W1～W25 |

> **v1.0 變更摘要**：
> 1. **新路徑**：console-api 5 個（`POST /api/v1/si/proposals/{id}/decide`、`POST /api/v1/si/observations`、`POST /api/v1/si/observations/{id}/close`、`POST /api/v1/si/observations/validate`、`GET /api/v1/si/console-writes`）；Bridge 4 個（`POST /si/proposals/{id}:decide`、`POST /si/observations`、`POST /si/observations/{id}:close`、`POST /si/observations:validate`）。
> 2. **寫入模型**：Console 不寫帳本。POST 只做「簽稽核 JSON → 寫 Console 自有稽核列 → 經 Bridge 落稽核檔」；入帳由主機端根層 CLI（`python tools/selfimproving.py <decide|obs-add|obs-close> --carrier console --audit-ref <ref>`）驗簽完成（pull）。**201＝稽核檔已落地、待入帳，不是已入帳**。
> 3. **新 reason 三個**：`si_write_forbidden`（403）、`si_write_disabled`（503；`details.cause`）、`si_audit_exists`（409）。`invalid_request`（422）沿既有。
> 4. **無刪除能力**：PUT／PATCH／DELETE 對全部 `/api/v1/si/**`：VIEWER 403、OPERATOR 與 ADMIN 405；Bridge 其餘方法一律 405。
> 5. **部署**：compose 的 engine-bridge 恰一條可寫 SI bind（稽核目錄），其餘 SI bind 維持唯讀；backend 新增 `CONSOLE_SI_DECIDERS`、`CONSOLE_SI_AUDIT_KEY`、`BRIDGE_SI_WRITE_TOKEN`；Bridge 新增 `BRIDGE_SI_WRITE_TOKEN`、`BRIDGE_SI_AUDIT_DIR`。

---

## 0. 共通約定

### 0.1 權威順位與事實來源

| 順位 | 來源 | 範圍 |
|------|------|------|
| 1 | 根層 `SelfImproving_PRD.md`（FR-SI-33、FR-SI-35、§9.3） | 需求；Console 載體三動詞的語意與 K=1 決定者 |
| 2 | 根層 `tools/lib/selfimproving/consoleaudit.py`、`decwrite.py`、`obswrite.py`、`obsrows.py` 與其 TCS（P2、P3） | **稽核 JSON 位元組契約、驗簽、列規則、入帳前提的唯一真相源**；Console 不複製列規則 |
| 3 | 本契約 | P2b 的 HTTP 形狀、閘門序、補償語意、對帳語意、DB 表 |
| 4 | `AgentConsole/engine-bridge/README.md`、`app/si_audit.py`、`app/routers/si.py`、`app/si_cli.py`、`tests/test_si_*.py` | **Bridge 行為的唯一真相源** |
| 5 | Architecture §10.2／§10.3、§11.1、§12.1 L-14；TCS W1～W25 | 架構決策與驗收 |

### 0.2 封包、認證與共通格式

- 認證：Bearer JWT（沿 P3-6 §0）。成功封包 `{code, message, data, timestamp, traceId}`；錯誤封包 `{code, message, errors[], reason?, details?, traceId}`（§0.3）。`errors[]` 與 `details.violations` 內容互為鏡像。
- 時間：稽核 body 的 `time`＝backend `Clock` 現在、截秒、`yyyy-MM-dd'T'HH:mm:ss` 接 `xxx` 偏移；UTC 為 `+00:00`，**絕不輸出 `Z`**（根層 CLI 先於驗簽以 `AUDIT-TIME-FORMAT` 拒收）。對帳回應的 `time` 以 UTC 回。
- 識別碼：`auditRef`＝小寫正規 UUID（backend 每次請求新取；重送一律新 ref）。`keyId`＝金鑰 sha256 前 8 碼。
- 機密：金鑰與權杖的值不出現在任何回應、`details`、日誌、例外訊息、`toString`；`.env.example` 只放 `<YOUR_…>` 佔位。

### 0.3 四個 POST 的閘門序（W10；先中者定案，輸入閘先於一切副作用）

| 序 | HTTP | reason | 條件 |
|----|------|--------|------|
| 1 | 401 | — | 無有效 JWT |
| 2 | 403 | `ACCESS_DENIED` | 角色非 ADMIN（`SecurityConfig` 對 `POST /api/v1/si/**` 要求 ADMIN） |
| 3 | 403 | `si_write_forbidden` | 帳號名不在 `console.si.deciders`（區分大小寫） |
| 4 | 503 | `si_write_disabled` | backend 未設金鑰環或 Bridge 權杖（`details.cause`＝`audit_key_unset`｜`bridge_token_unset`，先中者） |
| 5 | 422 | `invalid_request` | 輸入閘（§1.2 表）；含帳號名 `^[A-Za-z0-9_.-]{1,64}$` |
| 6 | — | — | 執行（§0.4） |

已知邊界：Admin 但不在名單者送無法解析的 JSON 先得 400（框架在用例入口前解析本文；TCS 已知邊界 14）。

### 0.4 寫入流程與補償（W11；AT-950-6-2、AT-950-6-E-1～E-3）

1. 授權 → 停用檢查 → 輸入閘 → 取 `auditRef` 與 `time` → 簽章（§3）→ **先 INSERT `si_console_writes` 一列** → 單次 Bridge 呼叫（連線 2 秒／讀取 20 秒；**不重試**）→ 回收據。
2. **補償（確定未落檔 ⇒ 刪該列）**：Bridge 明確拒絕＝任何 4xx、503 `si_write_disabled`、503 `si_unavailable`；`Failure` 且 bridgeStatus≠200；連線階段失敗（連線被拒）。
3. **結果不明 ⇒ 保留該列並回 `details.outcomeUnknown=true`**：讀取逾時（504）、送出後通訊失敗（502）、2xx 本文無法解析（502）。已知邊界：幽靈待入帳由掌舵者重送（新 ref）並由主控忽略該 ref；補償刪列自身失敗（DB 中斷）留幽靈列、記 warn（TCS 已知邊界 3、13）。
4. 依 `BridgeHttpAdapter` 例外語意對映：`BridgeRejectedException`（4xx）→422 `引擎拒絕此請求`（`details.bridgeReason`、`violations` 逐項）或 403／409／503 逐字透傳（§1.4）；`UpstreamException.Unavailable`（連線階段）→502 刪列；`UpstreamException.Unavailable`（送出後，`deliveryUncertain`）→502 保留；`TimedOut`→504 保留；`Failure`（5xx）→502 刪列。

---

## 1. console-api（backend）端點

### 1.1 總表（編號接 P1b 的 API-SI-01～06）

| 編號 | 方法與路徑 | 角色 | 成功 | operationId |
|------|-----------|------|------|-------------|
| API-SI-07 | `POST /api/v1/si/proposals/{id}/decide` | 僅 ADMIN 且在 `console.si.deciders` | 201 收據 | `postSiDecide` |
| API-SI-08 | `POST /api/v1/si/observations` | 同上 | 201 收據 | `postSiObservation` |
| API-SI-09 | `POST /api/v1/si/observations/{id}/close` | 同上 | 201 收據 | `postSiObservationClose` |
| API-SI-10 | `POST /api/v1/si/observations/validate` | 同上 | 200 預檢結果 | `postSiObservationValidate` |
| API-SI-11 | `GET /api/v1/si/console-writes?limit=` | VIEWER 以上（Console 畫面只對 ADMIN 顯示） | 200 對帳 | `getSiConsoleWrites` |

PUT／PATCH／DELETE 對全部 `/api/v1/si/**`：VIEWER 403、OPERATOR 與 ADMIN 405（AT-935-3-E-1）；POST 對五個無 POST 映射的讀路徑：無 token 401、VIEWER 與 OPERATOR 403、ADMIN 405。沒有批次或「全部核准」。

### 1.2 請求欄位表（backend 輸入閘 W12＝前端 `lib/domain/si.ts` 同一張表；前端先擋、backend 為權威）

通則：字串欄先判原值（含控制字元 U+0000～U+001F、DEL U+007F 或孤立代理字元＝拒收，連首尾換行也拒、不靜默剝除）→ 去前後空白 → 不可全空白 → 長度以 **code point** 計；觀察與關閉的字串欄拒收 `|`（觀察列是 Markdown 九欄表）。一次回報全部違規：422、`reason=invalid_request`、`details.violations[{field, message}]`（camelCase 欄名；路徑 id 的欄名 `id`、帳號 `user`）。

**1.2.1 決定 `POST /proposals/{id}/decide`（表 M-D；路徑 id＝`PROP-SI-\d{3,}`；`resume` 為 `RUN-SI-\d{3,}`）**

body：`{dkind, digest?, reason?, reasonClass?, unverifiedAck?}`。`digest`＝`sha256:` 接 64 位小寫 hex（綁定開啟決定當下看到的卡面）；`reason`＝1～500 code point 單行；`reasonClass`∈{證據不足, 風險過高, 工件類別錯, 已被涵蓋, 範圍外, 卡面不清, 未說明}；`unverifiedAck` 只有 `promote` 可為 true（verdict 為 NE 的晉升後式；稽核 body 的 `flags` 因此為 `["unverified_ack"]`），其餘動詞為 true 回 422（false 或缺席視為未勾選）。

| dkind | 路徑 id | 必填 | 禁止（有值即 422） |
|-------|---------|------|--------------------|
| approve | PROP | digest | reason, reasonClass, unverifiedAck |
| reject | PROP | digest, reason, reasonClass | unverifiedAck |
| return | PROP | digest, reason, reasonClass | unverifiedAck |
| promote | PROP | digest（NE 時前端另要求勾 unverifiedAck） | reason, reasonClass |
| decline-promote | PROP | digest, reason, reasonClass | unverifiedAck |
| rollback | PROP | reason | digest, reasonClass, unverifiedAck |
| unblock | PROP | （無） | digest, reason, reasonClass, unverifiedAck |
| resume | RUN | reason | digest, reasonClass, unverifiedAck |
| ack-handoff | PROP | digest | reason, reasonClass, unverifiedAck |

dkind 恰這九個（＝根層 `decide --carrier console` 實際受理者）。卡面 digest 新鮮度與 PROP 狀態前提入帳時才由 CLI 判（`STALE-CARD` 等），Console 不複製。

**1.2.2 新增觀察 `POST /observations` 與預檢 `POST /observations/validate`（表 M-O；同一請求本文）**

| 欄 | 規則 |
|----|------|
| `context`, `symptom`, `evidence` | 必填；各 1～300 code point；不含 `\|`；三欄 UTF-8 位元組和 ≤700（必要條件，違反時三欄一併標示；權威＝預檢與 CLI 的 `row_max_bytes`） |
| `category` | `process`｜`bug`｜`tooling`｜`doc`｜`decision` |
| `severity` | `P1`｜`P2`｜`P3`｜`P4` |
| `face` | `守衛`｜`產品`｜`文件`｜`流程` |
| `exposure` | `face=守衛` 時必填 `a`｜`b`｜`c`｜`無`；否則禁止 |
| `externalDerived` | 布林，必填（表單預設 false） |
| `corrects` | 選填；`OBS-SI-\d{3,}`（被更正列是否存在由 CLI 判）；帶時標記欄產生 `rel=corrects:<ID>` |

刻意不提供 `marks_extra`。

**1.2.3 關閉 `POST /observations/{id}/close`（表 M-C；路徑 id＝`OBS-SI-\d{3,}`）**

body：`{terminal, ref?, text?}`；`terminal` 七值（沒有 `open`；送 `open` 回 422）；`ref` 與 `text` 依終值恰擇一，另一欄有值即 422。

| terminal | 必填 | 格式 | disposition（backend 組） |
|----------|------|------|--------------------------|
| fixed | ref | 7～40 碼小寫 hex | `fixed@<ref>` |
| def | ref | `DEF-<n>-<n>` | `<ref>` |
| merged | ref | `OBS-SI-\d{3,}` | `merged@<ref>` |
| proposed | ref | `PROP-SI-\d{3,}` | `proposed@<ref>` |
| deferred／retired／decided | text | 1～120 code point，不含 `\|`、控制字元與「之後再看」 | `<terminal>：<text>`（全形冒號） |

retired 的可定位座標、該列是否仍為 open，入帳時由 CLI 判（validate 不涵蓋關閉；⚖13）。120 個 code point 只是上界：列是否超過 700 位元組取決於該列既有內容，權威仍是 CLI（TCS 已知邊界 1）。

### 1.3 回應形狀（`data`）

- **收據（201）**：`{auditRef: 小寫 UUID, kind: decide｜obs-add｜obs-close, subject: string｜null（decide＝PROP 或 RUN 號、obs-close＝OBS 號、obs-add＝null）, time: 稽核 body 的 time（秒精度、±HH:MM，UTC 為 +00:00，絕不 Z）, keyId: 金鑰 sha256 前 8 碼}`。不含 `body`、`mac`。
- **預檢（200；`ok=false` 仍 200）**：`{ok, row: 預覽列全文（通過才有，否則空字串；audit_ref 以全零 UUID 佔位）, rowBytes, rowMaxBytes: 整數｜null, findings: [{code, detail}]}`。預檢零副作用：不取 ref、不簽、不寫 DB、不落檔。
- **對帳**：見 §4。

### 1.4 狀態碼與 reason 對映（W10、W15）

| HTTP | reason | 何時 | details |
|------|--------|------|---------|
| 401 | — | 無有效 JWT | |
| 403 | `ACCESS_DENIED` | 角色非 ADMIN | |
| 403 | `si_write_forbidden` | 帳號不在 deciders；或 Bridge 拒絕 backend 附的權杖（兩端 `BRIDGE_SI_WRITE_TOKEN` 不一致） | |
| 503 | `si_write_disabled` | backend 未設金鑰環或 Bridge 權杖（先中者）；或 Bridge 端停用 | `cause`＝`audit_key_unset`｜`bridge_token_unset`；Bridge 端停用時 `detail` 逐字 |
| 422 | `invalid_request` | 輸入閘 | `violations[{field, message}]` |
| 422 | `引擎拒絕此請求`（`BRIDGE_REJECTED`） | Bridge 422 | `bridgeReason`、`violations` 逐項 |
| 409 | `si_audit_exists` | 稽核目錄已有同名 `<audit_ref>.json`（不覆寫） | |
| 503 | `si_unavailable` | 落檔 I/O 失敗（`detail` 帶 errno，不含路徑）、預檢子行程失敗 | `cause`、`detail` 逐字 |
| 502 | — | 其他 Bridge 5xx；連線階段失敗（已補償刪列）；送出後通訊失敗、2xx 本文無法解析（保留列） | 後兩者 `outcomeUnknown=true` |
| 504 | — | 讀取逾時（保留列） | `outcomeUnknown=true` |
| 400 | — | `console-writes` 的 `limit` 非整數或越界 | |
| 405 | — | PUT／PATCH／DELETE（OPERATOR、ADMIN）；VIEWER 為 403 | |

reason 常數落點：Java `ErrorReasons`（`si_write_forbidden`、`si_write_disabled`、`si_audit_exists` 三個新常數）、TS `lib/domain/si.ts` 的 `SI_REASONS`（P1b 兩鍵加本版三鍵，共五鍵；AT-950-9-2、AT-940-5-1）；`invalid_request` 於 backend 以 `SiWriteGates` 的區域常數存在、不進 `ErrorReasons`。

---

## 2. Bridge 端點（只准 backend-net；Bridge 不持有簽章金鑰、不解內層 body、不驗簽）

### 2.1 寫入三端點（W3）：`POST /si/proposals/{id}:decide`、`POST /si/observations`、`POST /si/observations/{id}:close`

驗證順序（先中者定案）：
1. 寫入面停用 ⇒ 503 `si_write_disabled`（先於權杖與本文；`BRIDGE_SI_WRITE_TOKEN` 與 `BRIDGE_SI_AUDIT_DIR` 皆須設才算啟用）。
2. `X-Bridge-Token` 缺或錯 ⇒ 403 `si_write_forbidden`（`hmac.compare_digest`；缺與錯同一回應、逐位元組相同；不記權杖值）。
3. 本文須為單一 UTF-8 JSON 物件且 ≤65536 位元組（恰 65536 為 201），否則 422。
4. 外層鍵集合恰七個（§3.1）、`schema_rev`＝整數 1、`kind` 等於端點、`audit_ref` 為小寫正規 UUID、`subject`（decide／close 須為字串且等於路徑 `{id}`；obs-add 須為 null）、`body`／`key_id`／`mac` 為字串；路徑 id：decide `^(PROP|RUN)-SI-[0-9]{3,}$`、close `^OBS-SI-[0-9]{3,}$`；不符 ⇒ 422 `invalid_request`（`violations[{field, rule, message}]`）。
5. `store_audit`：`os.open(O_WRONLY|O_CREAT|O_EXCL[|O_BINARY])` → 寫全部位元組（原樣，含結尾換行與 CRLF 變體）→ `fsync` → 關閉；同名 ⇒ 409 `si_audit_exists`；其他 `OSError` ⇒ 503 `si_unavailable`（`cause=audit_write_failed`、`detail=errno=<n>; <例外類名>`、不含路徑），半成品以 `os.unlink` 清除；不建立稽核目錄；不用 `os.replace`／`rename`／`move`。
6. 201 `{"audit_ref": <ref>, "stored": true}`。其餘方法一律 405（Starlette 對 `GET /si/proposals/{id}:decide` 落到既有 GET 單筆處理器回 422，故 405 斷言用 DELETE／PUT／PATCH；TCS 已知邊界 7）。

### 2.2 預檢 `POST /si/observations:validate`（W4）

不需權杖、不看寫入設定、不落檔；本文須為單一 JSON 物件且 ≤65536；子行程 `[sys.executable, <si_root>/tools/selfimproving.py, "obs-add", "--dry-run", "--body-file", "-", "--json"]`（stdin 餵本文位元組；環境白名單與逾時同 `export`）；rc 0 或 1 且 stdout 為含 `ok`／`row`／`row_bytes`／`row_max_bytes`／`findings` 的單一 JSON 物件 ⇒ 200 逐值透傳（`ok=false` 仍 200）；其餘 ⇒ 503 `si_unavailable`（`cause`：`si_root_unset`、`si_script_missing`、`spawn_failed`、`timeout`、`stdout_too_large`、`nonzero_rc`、`bad_json`、`bad_shape`；`detail=rc=<n|none>; stderr=<尾段>`）。

### 2.3 靜態鎖（`tests/test_si_readonly_lock.py`；W5 判準 1′～5′）

寫入形態只准出現在 `app/si_audit.py` 且路徑引數源自 `audit_dir` 參數（唯一精確例外＝validate 對子行程 stdin 的 `_feed_stdin`）；組 argv 的函式恰兩個（`export`、`obs-add --dry-run`）；形態判準看不到 `getattr`／動態拼接／`importlib`（已知邊界 5），行為面由 AT-950-2-1 的落檔清單與 AT-933-1-5 的真 CLI 入帳覆蓋。

---

## 3. 稽核 JSON 契約（W7、W8；位元組契約以根層 `consoleaudit.py` 為準）

### 3.1 外層與 body

- 外層恰七鍵、序固定：`schema_rev`(1)、`kind`、`audit_ref`、`subject`、`body`（**字串**）、`key_id`、`mac`；緊湊 JSON、UTF-8 無 BOM、非 ASCII 原樣、無結尾換行；**檔位元組＝backend 送出的請求本文＝Bridge 落檔位元組＝`audit_sha256` 的對象**。
- body 鍵序：共通 `schema_rev, audit_ref, kind, user, role(恆 ADMIN), time`；decide：`…, time, (prop｜run), [digest], dkind, [reason_class], [reason], flags`；obs-add：`…, time, context, symptom, evidence, category, severity, face, [exposure], external_derived, [corrects]`；obs-close：`…, time, obs_id, disposition`。預檢用的未簽 body 無 `audit_ref`。`user`＝JWT subject。

### 3.2 簽章

- 金鑰環 `CONSOLE_SI_AUDIT_KEY`（逗號分隔；空白與空項剝除）**第一把**的 UTF-8 位元組簽（不做 base64 解碼）；`key_id`＝sha256(金鑰) 前 8 碼；`mac`＝HMAC-SHA256(金鑰, body 字串的 UTF-8 位元組) 小寫 hex——**簽 body 字串本身、不重新序列化**。主機端 `AUTOSDD_SI_AUDIT_KEY` 環須含全部仍待入帳檔所用的金鑰（CLI 依 `key_id` 選鑰）。
- 根層拒收碼（AT-933-1-E-4 八種變形）：`AUDIT-MAC-MISMATCH`、`STALE-CARD`、`AUDIT-TIME-FORMAT`、`AUDIT-SCHEMA`、`AUDIT-KEY-MISSING`、`AUDIT-REF-REUSED`、`AUDIT-KEY-UNKNOWN`；寫入前判準（根層 P3 D12、R136）另有 `CTRL-CHAR`、`EVENT-KEY-UNKNOWN`、`REASON-EMPTY`、`DISPOSITION-INVALID`，與 §1.2 兩端防線同判準。

### 3.3 跨語言向量（TCS §5.1；Java 與 Python 共用）

向量金鑰 K0＝`si-p2-vector-key-0123456789-abcdefghijklmnopqrstuvwxyz`（`key_id` `f076edf0`）；共用 digest `sha256:a45ee65a…9bfe`、time `2026-10-21T09:15:30+08:00`、user `admin`。

| 向量 | kind／subject | audit_ref | body 位元組 | mac | 檔位元組 | 檔 sha256 |
|------|---------------|-----------|-------------|-----|----------|-----------|
| V1 | decide／PROP-SI-004 | 6f1c2a3e-8b4d-4e5f-9a7b-0c1d2e3f4a5b | 281 | a23f62da5cc2b8668a05570632b60700316350667c2fef600beda100c4bf3c21 | 527 | 4e35c9e5df306c11d77698bd0dbca4090d46fa4d09b8ffae87f135b27335c43f |
| V2 | decide／PROP-SI-004 | 0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d | 355 | 830722c9fcfccc37861f9fe62498aa0074822595e85578e48c8a04298de0ce9b | 609 | df7419ef9502262538fe8640a23a6bb691299b683929858178b02b89fe1ed3eb |
| V3 | obs-add／null | b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e | 380 | 0e67b0e0be050c07dc3b539fed87b3f53f88856446d2468b0e9f1da71cb94f35 | 630 | a923a24521bb7a05e2e05427e0b5f7e30d7080350c8ce6cba6944ae887cef601 |
| V4 | obs-close／OBS-SI-247 | c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f | 227 | f299d74dd7c261072b69a4c14a79999cda39716b5a9851b65fce8b6da016f6bc | 469 | 5d3f20980c464cb020b8031a3009435ecc94e408c1f8b5873a45610bb590eba4 |

負控：V1 的 dkind 換 reject 其 mac 為 `7801839b…5c6b2b`；V1 以 K0 接 `x` 簽的 mac 為 `e4a88cff…e967`；V1 的 `+08:00` 換 `Z` 被 `AUDIT-TIME-FORMAT` 拒收。

### 3.4 黃金檔 G1～G5（TCS §5.3；Java 正式碼在固定輸入下的輸出；`Clock.fixed` 2026-10-24T22:30:15+08:00、金鑰 K0、帳號 admin；住 `backend/src/test/resources/si/audit/` 與 `engine-bridge/tests/fixtures/si_audit/`，逐位元組相同）

| 檔 | kind／subject | audit_ref | body | 檔位元組 | 檔 sha256 | mac |
|----|---------------|-----------|------|----------|-----------|-----|
| G1 decide-approve.json | decide／PROP-SI-004 | a1000000-0000-4000-8000-000000000001 | 281 | 527 | 831acfcd69993cee663ded3ab6d5ac6305a90631d3c55259bdaa452b3e87b337 | 18f299d249ab36dfe28975fc61fff8a15a1c20fa9602af66fadd26e4af5917aa |
| G2 decide-reject.json | decide／PROP-SI-004 | …0002 | 355 | 609 | 9d81e866542ae0c84331861671f7780de91a328c19b487b3a23a45c85d06d046 | ae47199c39cad71546f64170c885b7545c4f77a8a32b5a39b7f0a10933858c8b |
| G3 obs-add.json | obs-add／null | …0003 | 380 | 630 | fc3917fa5c1d3b0dad7c258de028130981e5ac63ed1c0e991919054a9ffd3c1f | 7505ec8a9eb60f7b6b168d2c659dbe77ed6fad2c103b0238396b42fc70accf09 |
| G4 obs-add-corrects.json | obs-add／null | …0004 | 404 | 658 | faba0eed8cfe1cee1087a291c385011160d5fcca2406c8eb84889c3a1fc646c7 | ccbc3e7aa73925b976a553dc2e062b758d556c7e5d27a2ded8202334b7b012b9 |
| G5 obs-close.json | obs-close／OBS-SI-005 | …0005 | 212 | 454 | 4c5985a35c6da9189ab0277149c67f745c9977b5b5694f229e03c95910af5b57 | fb9c251546f9f40bbe303579c40c39ea2a3e53e09acea60317a0e72533e24410 |

序列化器日後變動會使 Bridge 副本與其不一致而紅（AT-950-4-3，刻意）；G1～G5 被真 CLI 收下（`test_si_console_ingest.py`）是「Console 簽出的檔能入帳」的唯一自動化證據。

---

## 4. 對帳 `GET /api/v1/si/console-writes?limit=<1..500，預設 100>`（W14）

- `data`＝`{items, truncated, orphans, reconcile}`。`items[]`（時間新到舊、同刻 `auditRef` 升冪）鍵集合恰：`auditRef, kind, user, role, time(UTC), subjectId(string｜null), digest(string｜null；只有六種決定動詞有), keyId, ingested(boolean｜null)`——**不含 `body`、`mac`**。`truncated`＝表內還有更舊的列。
- `reconcile`＝`{status: ok｜NOT-EVALUABLE, reason: null｜si_unavailable｜bridge_unreachable｜bridge_timeout｜scan_cap_exceeded, backfilled: 本次回填筆數}`。對帳在 backend 一次全量做（Bridge 永遠只被呼叫 GET）：observations 與 events 各以 `limit=500` 迴圈取頁（`truncated` 且 `next_since` 為數字即續取，各上限 20 頁）；「已入帳」＝帳本有同 `audit_ref` 的 `dec`／`obs.add`／`obs.close` 事件，或觀察列 `marks_kv.audit_ref` 相同。
- `orphans[]`＝帳本中 carrier 為 console 而表內無對應 `audit_ref` 的項 `{auditRef, kind, subject}`（先事件側依 seq 升冪、後觀察列側依行序，以 `auditRef` 去重）。
- **回填**：kind 為 obs-add 且 `subject_id` 為 NULL 的列，若某觀察列的 `marks_kv.audit_ref` 相同，`UPDATE … SET subject_id=<OBS id> WHERE audit_ref=? AND subject_id IS NULL`（冪等；讀路徑唯一的副作用）。
- 量不到（Bridge 失敗、逾時、頁數超限）＝`status NOT-EVALUABLE`、`items` 照回、`ingested` 與 `orphans` 為 null、不回填——不回空陣列、不冒充「無待入帳」（前端對 NOT-EVALUABLE 不顯示「無待入帳」）。
- 表 `console.si_console_writes`（Flyway V13）：`audit_ref UUID PK`、`kind` CHECK、`"user"`、`role`、`"time" timestamptz`、`subject_id`、`digest`、`body`、`key_id CHAR(8)`（regex CHECK `^[0-9a-f]{8}$`）、`mac CHAR(64)`（regex CHECK `^[0-9a-f]{64}$`）；BEFORE UPDATE 觸發器拒改任何欄位，唯一例外是 `subject_id` 由 NULL 變非 NULL；DELETE 允許（補償）。

---

## 5. 組態與部署

| 變數 | 服務 | 規則 |
|------|------|------|
| `CONSOLE_SI_DECIDERS` | backend | 逗號清單；預設空＝無人可寫 |
| `CONSOLE_SI_AUDIT_KEY` | backend | 金鑰環；每把 ≥32 字元、不得為 `<…>` 佔位，違反＝啟動失敗且訊息只講長度與序號；空＝寫入面停用 |
| `BRIDGE_SI_WRITE_TOKEN` | backend、Bridge（同值） | ≥32 字元；空＝停用 |
| `BRIDGE_SI_AUDIT_DIR` | Bridge | 容器內稽核目錄（compose 掛 `/si-audit`） |
| `AUTOSDD_SI_AUDIT_KEY`、`AUTOSDD_SI_DIR` | 主機端入帳（monorepo 根） | 與 `CONSOLE_SI_AUDIT_KEY` 同一把；`AUTOSDD_SI_DIR` 與 compose 同目錄 |

compose：engine-bridge 恰一條可寫 SI bind（長語法、`${AUTOSDD_SI_DIR:-${USERPROFILE:-${HOME}}/.autosdd/selfimproving}/console_audit` → 容器 `/si-audit`、`create_host_path: false`），其餘 SI bind 維持唯讀；Bridge 不對 host 發布埠。CI：`.github/workflows/agentconsole-ci.yml` 兩個觸發器的 `paths` 含寫入動詞閉包的根層輸入（`tools/lib/apply_lock.py`、`tools/lib/sdd_latest.py`，D10）。真容器的可寫 bind（Windows Docker Desktop 寫入權限、主機端 CLI 讀得到同一目錄）只由靜態檢查與 V3 承擔。

---

## 6. 前端（`components/domain/si/`）資料來源與閘

| 控件 | 資料來源 | 閘與行為 |
|------|----------|----------|
| `SiDecideDialog` | 卡片（state、route、verdict、cooldown；`decideVerbOptions` 依表 M-V）；橫幅 `suspended.run` 開 resume | 只對 ADMIN 顯示；預設不選動詞；NE 的卡只給晉升後式（勾 `unverifiedAck`）與不晉升；缺必填停用送出、連點只送一次；403／409／503／422 的 reason 逐字顯示、失敗不關窗 |
| `SiObsForm` | 表 M-O；即時 `estimateRowBytes`（三欄位元組和） | 送出前先 `validate`（不通過不送）；多行輸入框接住貼上的換行與 TAB 並擋下；停用原因寫在送出鈕旁 |
| `SiObsCloseDialog` | 表 M-C；只對 open 列 | `ref`／`text` 依終值擇一；`text` ≤120 code point |
| `SiWritesPanel` | `GET /console-writes` | 待入帳列（`ingested=false`）、孤兒紅色警示、NOT-EVALUABLE 不顯示「無待入帳」；收據（`auditRef`、入帳指令）即時顯示；mutation 成功後使 SI 查詢與 console-writes 失效重取（validate 不失效） |

既有登記表 `lib/nav/registry.ts` 不改（仍 7 項）；`lib/api/endpoints.ts` 加 `postSiDecide`、`postSiObservation`、`postSiObservationClose`、`postSiObservationValidate`、`getSiConsoleWrites` 五個函式（74→79）。

---

## 7. 驗收對照

| 面 | AT 群（TCS §1） | 自動測試 |
|----|-----------------|----------|
| Bridge 設定、落檔、權杖、validate、AST 鎖、契約 | AC-950-1～950-4、AC-933-1（Bridge 半） | `engine-bridge/tests/test_si_write_routes.py`、`test_si_audit_filename_safety.py`、`test_si_console_ingest.py`（真 CLI 入帳）、`test_si_readonly_lock.py`、`test_si_cli.py`、`test_si_deploy_config.py`、`test_si_routes.py` |
| backend 設定、閘門序、寫入與補償、輸入閘、V13、對帳 | AC-950-5～950-8、AC-933-1／933-2、AC-935-1～935-5 | `SiConsoleWriteApiIT`、`SiConsoleWritesReadApiIT`、`SiAuditSignerTest`、`SiWriteGatesTest`、`BridgeHttpAdapterSiWriteTest`、`SiWritePropertiesTest`、`SiConsoleWritesMigrationIT`、`SiReadOnlyArchTest`、`OpenApiIT`、`SchemaMigrationIT`、`V5UpgradeMigrationIT`、`SiMirrorApiIT` |
| frontend 控件、純函式、契約面釘選 | AC-950-9、950-10、AC-933-1、AC-935-1～935-5 | `SiDecideDialog.test.tsx`、`SiObsForm.test.tsx`、`SiObsCloseDialog.test.tsx`、`SiView.test.tsx`、`si.static.test.ts`、`lib/domain/si.test.ts`、`lib/api/{endpoints,si.endpoints}.test.ts`、`lib/nav/registry.test.ts` |
| 部署與 CI | AC-950-11 | `test_si_deploy_config.py`（compose、`.env.example`、CI paths） |

V 系列（V1～V12；真後端／真容器／真瀏覽器／掌舵者真機）不是 AT：結果記於 SCG-4 報告與 RTM §2.3 子表的 E2E 欄，未驗者如實標「未驗」。
