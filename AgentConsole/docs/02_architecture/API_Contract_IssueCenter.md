# API 契約 — 議題中心（Issue Center：議題聚合的匯出形狀、Bridge 兩個 GET、console-api 四個端點、優先順序表）

**版本**：v1.0｜**日期**：2026-10-27｜**作者角色**：Developer 依 TCS 契約節（§C0～§C6）逐表抄成（TCS-IssueCenter-20261027 D-C11；**TCS 為真相，本檔不得與它不同**）
**讀者**：後端開發者（Spring Boot 4.1／Java 21）、前端開發者（Next.js 16）、Bridge 維護者（Python）、根層 CLI 維護者、QA（依本契約驗收）
**與前代契約的關係**：本檔**不改**凍結的 [API_Contract_P3-6.md](API_Contract_P3-6.md)／`openapi-p3-6.yaml`，也不改 [API_Contract_SelfImproving_P1b.md](API_Contract_SelfImproving_P1b.md)（讀面）與 [API_Contract_SelfImproving_P2b.md](API_Contract_SelfImproving_P2b.md)（寫入載體）：封包與錯誤格式沿 P1b §0.2、Bridge 失敗映射沿 P1b §2.3、輸入閘的 422 形狀沿 P2b。新增的 reason 只有一個（§5.1），**不進** `lib/api/reasons.ts`（它與 P3-6 附錄 B 雙向鎖）；`Architecture.md` 同樣一字不改。
**機器可讀版**：本檔不另附 OpenAPI 檔。機器可讀的真相源是 backend 執行期的 `/v3/api-docs`（springdoc；議題中心路徑 3 條、操作 4 個，`OpenApiIT` 釘路徑 74／操作 85），入庫快照為 `frontend/lib/api/schema.d.ts`。兩者與本文衝突時以本文為準並回報修正。
**對應需求**：根層 `docs/01_requirements/Issue_Center_PRD.md` v1.0 的 FR-IC-01～FR-IC-12 與 §5～§7；TCS `docs/03_testing/contracts/TCS-IssueCenter-20261027.md`（兩把 SDD 鍵 `monorepo-issue-center`、`agentconsole-issue-center` 共用同一份；Console 半＝R-IC-45～R-IC-75）。

> **使用方式**：根層開發者照 §1、§2 施工（匯出形狀與 CLI）；Bridge 開發者照 §3；backend 開發者照 §4、§5、§6；前端照 §1.2～§1.4 取欄位形狀、§4 取端點與錯誤、§5 取中文訊息。

**版本沿革**

| 版本 | 日期 | 範圍 | 對應來源 |
|------|------|------|----------|
| v1.0 | 2026-10-27 | 初版：匯出形狀 `export --kind issues`；Bridge `GET /si/issues`、`GET /si/issues/{id}`；console-api 四個端點；issue 類 reason 一個；Flyway V14 `issue_priority` | TCS-IssueCenter-20261027 §C0～§C6（鍵 `agentconsole-issue-center`） |

---

## C0 共通約定

| 項目 | 約定 |
|------|------|
| 命名 | `export`、CLI `--json`、Bridge 一律 snake_case；console-api 與畫面一律 camelCase（`SiKeyNames.camel`：鍵符合 `^[a-z][a-z0-9]*(_[a-z0-9]+)+$` 者轉換，其餘鍵恆等；**值一律不動**）。下表鍵名兩種寫法並列（snake／camel）；單字鍵兩者相同 |
| 封包 | 成功沿 P1b §0.2 `ApiResult<T>`：`{code:200, message:'success', data, timestamp, traceId}`；失敗沿 `ApiError`：`{code, message, reason?, errors[{field,message}], details?, timestamp, traceId}`；任何失敗沒有 `data` |
| 編碼與鍵序 | UTF-8、無 BOM、LF；`export` 為單一 JSON 文件一行；鍵序固定（下表由上而下；backend 以保序 Map）；console-api 追加的鍵在該物件最後 |
| 缺鍵與 null | 缺鍵與 `null` 語意不同（沿 P1b §0.2）：單筆缺 `legend`、`summary` 是「不適用」；`null` 是「量不到」 |

## C1 `export --kind issues`（根層半交付；Bridge、backend 透傳）

### C1.1 頂層物件（鍵序）

| snake／camel | 型別 | 清單 | 單筆（`--id`） | 說明 |
|---|---|---|---|---|
| `schema_rev`／`schemaRev` | int | 有 | 有 | 恆為 1 |
| `kind` | string | 有 | 有 | 恆為 `issues` |
| `generated_at`／`generatedAt` | string | 有 | 有 | ISO-8601 帶 offset、秒精度（沿既有 export） |
| `head_sha`／`headSha` | string 或 null | 有 | 有 | git 取不到＝null 並列 `ne` `git-unavailable` |
| `items` | array | 有 | 有（恰一筆；查無＝空陣列） | 議題物件（§C1.2） |
| `next_since`／`nextSince` | int 或 null | 有 | 有（恆 null） | 本頁最後一項游標；末頁 null |
| `truncated` | bool | 有 | 有（恆 false） | 符合者多於本頁上限 |
| `ne` | array | 有 | 有 | `{field, reason}`（§C1.5） |
| `problems` | array | 有 | 有 | `{subject, code, detail}`（§C1.5） |
| `legend` | object | 有 | **缺鍵** | §C1.3 |
| `summary` | object | 有 | **缺鍵** | §C1.4 |

### C1.2 議題物件（鍵序；`raw`、`timeline` 只在單筆；`priority`、`priorityNote` 只由 console-api 加，export 與 CLI 沒有）

| snake／camel | 型別 | 值域與說明 |
|---|---|---|
| `id` | string | `OBS-SI-NNN`、`DEF-<族>-<序>`、`PROP-SI-NNN` |
| `source` | string 或 null | 使用者提案、系統缺陷、研究提案、系統改善、「未歸類：<原值>」；null＝所屬帳本讀不到（並列 `ne`） |
| `title` | string | R-IC-23；≤80 code point 加「…」 |
| `severity` | string 或 null | 緊急、高、中、低、「未歸類：<原值>」；null＝量不到 |
| `severity_rank`／`severityRank` | int 或 null | 1～4；量不到或表外＝null |
| `status` | string | 七狀態之一或「未歸類：<原值>」 |
| `result` | string 或 null | 八結果之一或「未歸類：<原值>」；僅 `status`＝已完成有值 |
| `updated_at`／`updatedAt` | string 或 null | `YYYY-MM-DD`；解不出＝null |
| `next_step`／`nextStep` | string | R-IC-31 |
| `origin` | object | 觀察、缺陷 `{ledger, file, line}`；提案 `{ledger:'事件帳本', file, seq}` |
| `links` | string[] | R-IC-27 |
| `rankable` | bool | R-IC-28 |
| `action` | string 或 null | `decide-proposal`、`close-observation`、null |
| `raw`（單筆） | `[{label, value}]` | R-IC-29；兩者皆 string |
| `timeline`（單筆） | `[{seq, t, by, action}]` | R-IC-30；`seq` int、`t` ISO-8601 帶 offset、`by`、`action` string |
| `priority`（console-api） | int 或 null | 僅 `rankable` 為真且有列＝值；否則 null |
| `priority_note`→`priorityNote`（console-api） | string 或 null | 同上；有列時可為空字串 |

### C1.3 `legend`（鍵序）

`statuses[{name, meaning, tab, rankable}]`（7；`tab` 為專屬分頁名、候選與延後為 null）、`results[{name, meaning}]`（8）、`sources[{name, meaning}]`（4，依順位）、`severities[{name, rank, meaning}]`（4）、`problem_codes`→`problemCodes[{code, meaning}]`（5）、`ne_reasons`→`neReasons[{reason, meaning}]`（9）、`unmapped_label`→`unmappedLabel`（「未歸類」）、`updated_at_note`→`updatedAtNote`（含「最後已知動靜」）。

`problem_codes` 的 `ROW-ARITY` 釋義＝PRD §4.5 該句「帳本列欄數不符（觀察列另含 ID 格式不合），該列不成議題」後加「；編號或行號過大而無法編入游標者同樣不成議題」。

### C1.4 `summary`（鍵序）

`total`（int）、`by_status`→`byStatus`（七狀態名→int，鍵序＝候選、待您決定、待解、進行中、觀察中、延後、已完成）、`by_tab`→`byTab`（`待處理`、`待您決定`、`已完成`→int 或 null，D-R5）、`unmapped`（int）。

### C1.5 `ne` 與 `problems` 條目

| 清單 | 條目 | 鍵序與值 |
|---|---|---|
| `ne` | `{field, reason}` | `field`：整本帳 `ledger.observation`、`ledger.observation.<歸檔檔名>`、`ledger.defect`、`ledger.sibling.<檔名>`、`ledger.events`、`head_sha`；項目級 `issues.<ID>.<欄>`（欄∈severity、updated_at、title、next_step）。`reason`：九個封閉值（R-IC-08） |
| `problems` | `{subject, code, detail}` | `subject`：議題 ID、`L<行號>`（觀察無效列、事件帳本行）、`<檔名>:L<行號>`（姊妹軌列）；`code`：五個封閉值；`detail`：`UNMAPPED` 為「<維度>：<原值>」；`ROW-ARITY` 為「欄數與表頭不符」「ID 欄不合 OBS-SI-NNN」「編號或行號過大，游標無法編碼」三者之一；其餘為中文說明 |

### C1.6 游標（D-R4；S＝10,000,000）

| 來源 | 游標 | 備註 |
|---|---|---|
| 觀察（含歸檔檔） | OBS 號的數字 | 範圍 [0, S) |
| 缺陷主檔 | S＋主檔資料列行號 | 行號＝`DefRow.lineno` |
| 提案 | 2S＋PROP 號的數字 | |
| `AutoSDD_External_Blocked_Log.md` 孤列 | 3S＋該檔行號 | |
| `AutoSDD_Structural_Debt_Log.md` 孤列 | 4S＋該檔行號 | |

`items` 依游標升冪；`since` 取游標嚴格大於者；號碼或行號 ≥ S 者不成議題（`ROW-ARITY`，detail「編號或行號過大，游標無法編碼」）；最大游標 4S＋行號 < 2^31。

### C1.7 範例（snake_case 原形）

```json
{"field": "ledger.sibling.AutoSDD_External_Blocked_Log.md", "reason": "SIBLING-LEDGER-UNAVAILABLE"}
{"field": "issues.PROP-SI-004.next_step", "reason": "MEASURE-UNAVAILABLE"}
{"subject": "OBS-SI-001", "code": "UNMAPPED", "detail": "狀態：later"}
{"subject": "L5", "code": "EVENT-UNSOUND", "detail": "事件未通過 events.validate，已略過"}
{"total": 597, "by_status": {"候選": 0, "待您決定": 0, "待解": 0, "進行中": 0, "觀察中": 2, "延後": 51, "已完成": 544}, "by_tab": {"待處理": 2, "待您決定": 0, "已完成": 544}, "unmapped": 0}
```

前四行依序是 `ne` 條目、`problems` 的 `UNMAPPED` 與 `EVENT-UNSOUND` 條目；末行是 `summary`（2026-10-26 真帳本參考值，非釘值）。`detail` 的中文說明字句不入 AT（AT 只驗 `code`、`subject`、`UNMAPPED` 的 detail 形如「<維度>：<原值>」）。

## C2 根層 CLI（`tools/selfimproving.py`）

| 項目 | 約定 |
|---|---|
| `issues` | `python tools/selfimproving.py issues [--status <中文[,中文…]>] [--source <中文[,中文…]>] [--since N] [--limit N] [--json] [--repo <路徑>]`；rc 0＝已執行、3＝用法或輸入錯誤（stderr 一行「selfimproving: …」；未知篩選值列合法值）；唯讀 |
| 文字表 | 每列：`編號  來源  嚴重度  狀態[・結果]  最後更新  標題→下一步`（欄間兩空白、依顯示寬度對齊、null＝「—」）；末行 `共 N 件；問題 M 筆`＋被截斷時 `；尚有更多，--since <next_since>` |
| `export` | `python tools/selfimproving.py export --json --kind issues [--since N] [--limit N] [--id <ID>] [--status …] [--source …]`；`--id` 與 `--status`／`--source` 不併用；後二者只配 `--kind issues` |

## C3 Engine Bridge（唯讀；每請求恰一次 `si export` 子行程；無快取）

| 路由 | 查詢參數 | argv（`<py>` 為直譯器、`<S>` 為腳本） | 成功 |
|---|---|---|---|
| `GET /si/issues` | `since`、`limit`、`status`、`source`（其餘 422 `unknown_parameter`） | `<py> <S> export --json --kind issues [--since N] [--limit N] [--status=<值>] [--source=<值>]` | 200，本文＝子行程輸出解析後逐值透傳 |
| `GET /si/issues/{id}` | 無（任何參數 422 `unknown_parameter`） | `<py> <S> export --json --kind issues --id <ID>` | 200（`items` 恰一筆）；`items` 空＝404 `si_not_found`（`id`） |

| 驗證（子行程之前；422 `invalid_request`，`violations[{field, rule, message}]`） | `rule` |
|---|---|
| 未知查詢參數 | `unknown_parameter` |
| `{id}` 不符 `OBS-SI-\d{3,}`、`PROP-SI-\d{3,}`、`DEF-\d+-\d+` | `invalid_format` |
| `status`／`source` 超過 64 字元 | `too_long` |
| `status`／`source` 以 `-` 起頭 | `leading_dash` |
| `status`／`source` 含 U+0000～U+001F、U+007F | `control_char` |

失敗映射沿 P1b §2.3：CLI rc≠0（含未知篩選值 rc 3）→503 `si_unavailable`（`cause=nonzero_rc`、`detail` 逐字）；其餘 cause 不變。其他 HTTP 方法 405。

## C4 console-api（`/api/v1`；operationId 與 tag「議題中心（Issue Center）」）

| # | 方法與路徑 | operationId | 角色 | Bridge 呼叫 |
|---|---|---|---|---|
| API-IC-01 | `GET /api/v1/issues` | `getIssues` | VIEWER 以上 | `siExport('issues', since, limit, null, status, source)` |
| API-IC-02 | `GET /api/v1/issues/{id}` | `getIssue` | VIEWER 以上 | `siExport('issues', null, null, id, null, null)` |
| API-IC-03 | `PUT /api/v1/issues/{id}/priority` | `putIssuePriority` | 僅 ADMIN | 先 `siExport('issues', null, null, id, null, null)` 取單筆（D-C4） |
| API-IC-04 | `DELETE /api/v1/issues/{id}/priority` | `deleteIssuePriority` | 僅 ADMIN | 無 |

### C4.1 `GET /api/v1/issues`

查詢 `status`（string，選填；七狀態名或「待處理」，逗號分隔）、`source`（string，選填；四來源名，逗號分隔）、`since`（int ≥0，選填）、`limit`（int ≥1，選填；上限住根層參數檔、不在此複製）。200 `data`＝§C1.1（含 `legend`、`summary`）經 camelCase、每筆加 `priority`、`priorityNote`。

| 狀態 | reason | details | 條件 |
|---|---|---|---|
| 400 | （無） | `errors[{field, message}]` | `since`<0、`limit`<1、型別不符（例 `since=abc`）；不觸及 Bridge |
| 401 | `UNAUTHENTICATED`／`TOKEN_EXPIRED`／`TOKEN_INVALID` | | 無有效 JWT |
| 422 | `引擎拒絕此請求` | `bridgeReason=invalid_request`、`violations` 逐項 | Bridge 422（`status`／`source` 衛生） |
| 502 | `引擎橋接服務無法連線`／`引擎橋接服務錯誤` | `bridgeStatus`（有才帶） | Bridge 不可達、回其他 4xx／5xx 或 200 本文非 JSON 物件 |
| 503 | `si_unavailable` | `cause`、`detail` 逐字 | Bridge 503（含 CLI rc≠0）；順位表讀取失敗為 5xx（無 `data`） |
| 504 | `引擎橋接服務逾時` | | 讀取逾時（約 20 秒、不重試） |

### C4.2 `GET /api/v1/issues/{id}`

不收查詢參數。200 `data`＝§C1.1 單筆形（無 `legend`、`summary`；項目含 `raw`、`timeline`、`priority`、`priorityNote`）。錯誤同 C4.1，另：404 `si_not_found`（`details.id`；訊息「查無此議題」）；422 `引擎拒絕此請求`（`bridgeReason=invalid_request`，`{id}` 格式不合）。

### C4.3 `PUT /api/v1/issues/{id}/priority`

body `{rank, note}`（見下表）；200 `data`＝`{id, rank, note, setBy, setAt}`（`setAt` 為 ISO-8601 帶 offset）。

| 欄位 | 型別與規則 |
|---|---|
| 路徑 `id` | 符 `^(OBS-SI-[0-9]{3,}\|PROP-SI-[0-9]{3,}\|DEF-[0-9]+-[0-9]+)$`（與 DB CHECK 同式） |
| `rank` | 必填；整數 1～9999；`null`、缺鍵、0、-1、1.5、字串、`true`、`[]`、`{}`、10000 一律 422（欄 `rank`），**不是 400**、不當清除 |
| `note` | 選填（缺＝空字串；只有缺鍵才是缺省）；string（數字與 `null` 一律 422，欄 `note`）；≤200 code point（全形與表情符號各算 1）；不含 U+0000～U+001F、U+007F |

| 驗證序（先中者定案） | 狀態 | reason | details |
|---|---|---|---|
| 無有效 JWT | 401 | `UNAUTHENTICATED` 等 | |
| 角色非 ADMIN | 403 | `ACCESS_DENIED` | |
| 本文不是 JSON 物件（`[]`、`"x"`；JSON 語法錯亦同） | 400 | `MALFORMED_REQUEST_BODY`（既有 reason，沿 `GlobalExceptionHandler.handleUnreadable`） | |
| 輸入閘 | 422 | `invalid_request` | `violations[{field, message}]` 一次全列（與 `errors[]` 互為鏡像） |
| Bridge 失敗 | 503／502／504 | 同 C4.1 | 同 C4.1 |
| 查無議題 | 404 | `si_not_found` | `id` |
| `rankable` 為 false | 409 | `issue_not_rankable` | `id`、`status`（中文狀態） |
| 成功（UPSERT） | 200 | | |

### C4.4 `DELETE /api/v1/issues/{id}/priority`

無 body；成功 204（無本文）；列不存在也 204；不呼叫 Bridge。驗證序：401→403 `ACCESS_DENIED`→422 `invalid_request`（`id` 格式）→DELETE。兩個寫入端點都不要求 `console.si.deciders`；`AuditLoggingFilter` 對成功（200、204）、被拒（401、403）與失敗（422、409）各留一列 `console.audit_log`。

## C5 reason

### issue 類 reason 表（C5.1；雙向鎖的對象；契約檔內以標題 `issue 類 reason 表` 起頭的第一張表為準，欄序固定）

| reason | 狀態碼 | details | 中文訊息 | 意義 |
|---|---|---|---|---|
| `issue_not_rankable` | 409 | `id`、`status` | 此議題目前的狀態不能設定優先順序 | 議題狀態不是待您決定、待解、進行中（候選、觀察中、延後、已完成、未歸類）；PUT 不寫入 |

### C5.2 沿用的 reason（不入鎖表）

`si_unavailable`（503）、`si_not_found`（404）沿 P1b；`invalid_request`（422）沿 P2b（後端區域常數）；`ACCESS_DENIED`（403）、`MALFORMED_REQUEST_BODY`（400）、`引擎拒絕此請求`、`引擎橋接服務無法連線`、`引擎橋接服務錯誤`、`引擎橋接服務逾時` 沿 P3-6 附錄 B。`reasons.ts`、`API_Contract_P3-6.md`、`Architecture.md` 一字不改（AC-IC-07-8）。

## C6 資料所有權（V14）

```sql
CREATE TABLE console.issue_priority (
    issue_id VARCHAR(64) PRIMARY KEY CHECK (issue_id ~ '^(OBS-SI-[0-9]{3,}|PROP-SI-[0-9]{3,}|DEF-[0-9]+-[0-9]+)$'),
    rank     INTEGER      NOT NULL CHECK (rank BETWEEN 1 AND 9999),
    note     VARCHAR(200) NOT NULL DEFAULT '',
    set_by   VARCHAR(64)  NOT NULL,
    set_at   TIMESTAMP WITH TIME ZONE NOT NULL
);
```

寫入者只有 `IssuePriorityAdapter`（JDBC；UPSERT 與 DELETE 各一條敘述，另有唯讀 SELECT）；無 JPA 實體；不存歷史（變更軌跡在 `console.audit_log`）；順位可重複。
