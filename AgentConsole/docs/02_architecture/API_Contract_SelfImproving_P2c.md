# API 契約 — SelfImproving 排程控制載體（P2c／P4 Console 半：排程設定、立即啟動、排程狀態顯示）

**版本**：v1.0（實作輪校對；PKG-BE 2026-11-09 落地）｜**日期**：2026-11-09｜**作者角色**：SA／Architect 合一（規格棒）；v1.0 由主控依 PKG-BE 交卷如實校對（Console TCS §7.1 D-CS-14～20；先例：P2b v1.0）
**讀者**：後端開發者（Spring Boot 4.1／Java 21）、前端開發者（Next.js 16）、Bridge 維護者（Python）、主機端入帳者（根層 CLI 與巡邏器）、QA
**與前代契約的關係**：本檔**後繼並補充** [API_Contract_SelfImproving_P2b.md](API_Contract_SelfImproving_P2b.md)（v1.0 與 §8 增補一字不改；其 §0 共通約定、§1.2 通則、§2.1 Bridge 步驟、§3.2 簽章、§5 組態在本檔一律引用、不複寫）與 [API_Contract_SelfImproving_P1b.md](API_Contract_SelfImproving_P1b.md)（`GET /si/status` 的 `items[0]` 多一個 `schedule` 鍵，見 §4）。
**機器可讀版**：同 P2b——runtime 的 `/v3/api-docs` 與入庫快照 `frontend/lib/api/schema.d.ts`；與本文衝突時以本文為準並回報修正（實作輪校對後以實作為準）。
**對應需求**：Console PRD §0.11（F-910、US-930、AC-964-1～10；鍵 `agentconsole-si-schedule`）；根層 `docs/01_requirements/SelfImproving_PRD.md` v0.13 的 FR-SI-37（AC-SI-37-1～37-5）、FG-M、§9.1 C24、§9.2〈P4 增補〉、§9.3〈P4 寫入端點〉、§9.6 P4 列、附錄 C.2 #21（D-SCH-4、11、12）；Architecture §5.6、§10.3、§12.1 L-SI-1／L-SI-2；TCS `docs/03_testing/contracts/TCS-SelfImprovingSchedule-20261109.md`（Stage-2，另棒撰寫）。
**權威與引用原則**：**事件欄位、`status.schedule` 形狀、稽核 JSON 兩種新 `kind` 的欄位與入帳動詞，唯一定稿處＝根層 SelfImproving PRD §9.2〈P4 增補〉與 §9.3〈P4 寫入端點〉**；位元組契約的最終權威＝根層 `tools/lib/selfimproving/consoleaudit.py`（P4 根層鍵 RELEASE 後現查）。本檔只複述 Console 側的 HTTP 形狀、閘門序與落點，不另定義上述內容；發現與根層衝突，以根層為準並回報修正本檔。
**前置依賴**：根層鍵 `monorepo-si-p4-schedule` RELEASE（`status.schedule` 形狀與兩個入帳動詞須先在）；P2b 的稽核管線（`si_console_writes`、Bridge `_store_signed_audit`、`SiDecideDialog`）已在。

**版本沿革**

| 版本 | 日期 | 範圍 | 對應來源 |
|------|------|------|----------|
| v0.1 | 2026-11-09 | 規格稿：console-api 兩個 POST；Bridge 兩個 POST；稽核 JSON 兩種新 `kind` 的 Console 側落點；`status.schedule` 與對帳 `kind` 新值；`si_console_writes.kind` CHECK 改版 | Console PRD §0.11（鍵 `agentconsole-si-schedule`） |
| v1.0 | 2026-11-09 | 實作輪校對（只改字面、不改語意）：GET 對兩新路徑的角色回應改為「已登入角色一律 405」（§1.1）；未知欄位忽略不入 body、DTO 以 `Object` 接收使型別錯走 422 一次全列、「全空白」對齊 Python `str.strip()`（§1.2）；`SiKeyNames` 既有通則涵蓋九鍵、無特例表（§4.1）；Flyway 實名 `V23__si_console_writes_kind_sched.sql`、約束實名 `si_console_writes_kind_check`（§5）；黃金檔 G6～G9 定稿值見 Console TCS §5.1 | PKG-BE 交卷（`gradlew clean build` 全綠）；Console TCS §7.1 D-CS-14～20 |

> **v0.1 變更摘要**：
> 1. **新路徑**：console-api 2 個（`POST /api/v1/si/schedule/set`、`POST /api/v1/si/runs/request`）；Bridge 2 個（`POST /si/schedule:set`、`POST /si/runs:request`）；既有 `GET /api/v1/si/status` 回應的 `items[0].schedule` 為新增鍵（加鍵、`schema_rev` 不變）。
> 2. **寫入模型不變**：Console 不寫帳本；POST 只做「簽稽核 JSON → 寫 Console 自有稽核列 → 經 Bridge 落稽核檔」；入帳由主機端（巡邏器每心跳自動，或掌舵者手動）完成；**201＝稽核檔已落地、待入帳，不是已生效**。
> 3. **無新 reason**：沿用 P2b 既有 reason 與 `invalid_request`；`sched-set` 的界取得失敗以既有 `si_unavailable`（503）加新 `details.cause` 值呈現（§1.4）。
> 4. **不走決定重送閘**：兩個新 POST 無卡面 digest，`si_decision_duplicate`（P2b §8）只管 decide，本檔兩者不受影響（§1.4 末段；重送防線只在前端的軟停用，§6）。
> 5. **資料表**：`console.si_console_writes.kind` 的 CHECK 由三值擴為五值，**Flyway 新版本**（§5）；無新表、無新欄、「列不可改」trigger 不變。
> 6. **部署**：無新環境變數、無新 compose 掛載（兩個 POST 沿既有稽核目錄可寫掛載與既有金鑰、權杖）。

---

## 0. 共通約定

沿 P2b §0.1～§0.4，下列僅列**差異**：

- **認證、封包、時間、識別碼、機密**＝P2b §0.2（`time` 秒精度、`±HH:MM`、不輸出 `Z`；`auditRef` 小寫 UUID、每次請求新取；金鑰與權杖值不外洩）。
- **閘門序**（兩個新 POST；先中者定案、輸入閘先於一切副作用）：

| 序 | HTTP | reason | 條件 |
|----|------|--------|------|
| 1 | 401 | — | 無有效 JWT |
| 2 | 403 | `ACCESS_DENIED` | 角色非 ADMIN |
| 3 | 403 | `si_write_forbidden` | 帳號名不在 `console.si.deciders` |
| 4 | 503 | `si_write_disabled` | backend 未設金鑰環或 Bridge 權杖（`details.cause`＝`audit_key_unset`｜`bridge_token_unset`） |
| 5 | 422 | `invalid_request` | 靜態輸入閘（§1.2：型別、必填、長度、控制字元；含帳號名 `^[A-Za-z0-9_.-]{1,64}$`） |
| 5′ | 422／503／502／504 | 見 §1.4 | **僅 `sched-set`**：自 `GET status` 取 `schedule.periodMin／periodMax` 驗 `periodMinutes` 界（讀取、零副作用，故仍先於一切副作用） |
| 6 | — | — | 執行（P2b §0.4：先 INSERT 稽核列→單次 Bridge 呼叫→補償／結果不明語意逐字沿用） |

- **不走 dedupe**：沒有「同一決定」的概念（`sched-set` 每次是「把排程設成這樣」的請求，`run-request` 每次是「請求啟動一次」）；入帳端以 `audit_ref` 不得二次入帳去重、以「同格同因一筆」與「已有未關運轉改記 `sched.skip`」消化多餘請求（根層 PRD AC-SI-37-2）。P2b §0.2 的「重送一律新 ref」對這兩種寫入**維持成立**。
- **主機端入帳指令**（收據一併顯示）：`python tools/selfimproving.py sched set --carrier console --audit-ref <auditRef>`；`python tools/selfimproving.py run-open --trigger a --carrier console --audit-ref <auditRef> --coord console_audit/<auditRef>.json --by console`。於 monorepo 根、已設主機端 `AUTOSDD_SI_AUDIT_KEY` 的 shell 執行；PowerShell 與 bash 兩形態字串相同。巡邏器已武裝時下一心跳會自動入帳（根層 PRD AC-SI-39-1），Console 看不到武裝與否（Architecture §12.1 L-SI-1），故兩種說明並列。

---

## 1. console-api（backend）端點

### 1.1 總表（編號接 P2b 的 API-SI-07～11；P2b 現存最大＝API-SI-11，現查）

| 編號 | 方法與路徑 | 角色 | 成功 | operationId |
|------|-----------|------|------|-------------|
| API-SI-12 | `POST /api/v1/si/schedule/set` | 僅 ADMIN 且在 `console.si.deciders` | 201 收據 | `postSiScheduleSet` |
| API-SI-13 | `POST /api/v1/si/runs/request` | 同上 | 201 收據 | `postSiRunRequest` |

`SecurityConfig` 既有 `POST /api/v1/si/**`→`ADMIN` 已涵蓋，不新增規則；PUT／PATCH／DELETE 對兩個新路徑：VIEWER 403、OPERATOR 與 ADMIN 405（沿 P2b §1.1 通則，`@RequestMapping` 不帶 `method`、ArchUnit `SiReadOnlyArchTest` 擴充覆蓋）。GET 對這兩個路徑：無 token 401、已登入角色（VIEWER／OPERATOR／ADMIN）一律 405（v1.0 實測：`SecurityConfig` 對 `GET /api/v1/**` 放行 VIEWER 以上、兩路徑無 GET 對映；原 v0.1「VIEWER 與 OPERATOR 403」為規格稿推定；Console TCS D-CS-14）。沒有批次。

### 1.2 請求欄位表（backend 輸入閘＝前端 `lib/domain/si.ts` 表 M-S／M-R 同一張表；前端先擋、backend 為權威）

通則沿 P2b §1.2：字串欄先判原值（控制字元 U+0000～U+001F、DEL、孤立代理字元＝拒收，含首尾換行）→去前後空白→（有值則）不可全空白→長度以 **code point** 計；一次回報全部違規：422、`reason=invalid_request`、`details.violations[{field, message}]`（camelCase 欄名；帳號 `user`）。本文須為單一 JSON 物件（`run-request` 可為 `{}`）；未知欄位：**忽略、不入稽核 body**（Spring Boot 預設；v1.0 現查回寫，Console TCS D-CS-17）；DTO 欄位（`enabled`、`periodMinutes`、`reason`、`note`）以 `Object` 接收，字串 `"true"`、小數、布林充當整數等型別錯一律走輸入閘 422 一次全列，不被序列化器悄悄轉型（D-CS-20 (a)）；「全空白」判準對齊 Python `str.strip()`（Java `isWhitespace`∪`isSpaceChar`∪U+0085，例：全是 U+00A0 也拒；D-CS-20 (b)），避免 Console 放行而 CLI 以 `FIELD-BLANK` 拒收。

**1.2.1 `POST /schedule/set`（表 M-S）**：body `{enabled, periodMinutes, reason?}`

| 欄 | 規則 |
|----|------|
| `enabled` | 布林，**必填**（缺席＝422；不接受字串 `"true"`）。`false`＝停用方向，`true`＝啟用 |
| `periodMinutes` | 整數，**必填**（JSON 整數；小數、字串、負數、0＝422）；須在 `[schedule.periodMin, schedule.periodMax]`（含端點）。**界不寫死在前後端任何一處**：backend 於序 5′ 自 `GET status` 取；前端自橫幅 `schedule.periodMin／periodMax` 取。停用時仍必填（帶目前週期；WHY：根層稽核 body 兩鍵皆必備，AC-SI-37-1） |
| `reason` | 選填；單行 ≤120 code point；有值須非全空白；省略則稽核 body 不含該鍵 |

**1.2.2 `POST /runs/request`（表 M-R）**：body `{note?}`

| 欄 | 規則 |
|----|------|
| `note` | 選填；單行 ≤120 code point；有值須非全空白；省略則稽核 body 不含該鍵 |

稽核 body 內的欄名與型別（`enabled: bool`、`period_minutes: int`、`reason?`、`note?`）＝根層 PRD §9.2〈P4 增補〉逐字；backend DTO 的 camelCase 欄名在組 body 時轉為該 snake_case 鍵（沿 P2b `SiAuditJson`）。

### 1.3 回應形狀（`data`）

- **收據（201）**：沿 P2b §1.3 的收據 `{auditRef, kind, subject, time, keyId}`，其中 `kind` 值域加 `sched-set`｜`run-request`，`subject` 恆為 `null`（兩種新 kind 皆無對象）。不含 `body`、`mac`。
- 無預檢端點（不需要：欄位簡單，界驗證已在序 5′ 同步完成且零副作用）。

### 1.4 狀態碼與 reason 對映

沿 P2b §1.4 全表（401、403×2、503 `si_write_disabled`、422 `invalid_request`、422 `BRIDGE_REJECTED`、409 `si_audit_exists`、503 `si_unavailable`〔落檔 I/O 失敗〕、502、504、405），差異如下：

| HTTP | reason | 何時 | details |
|------|--------|------|---------|
| 422 | `invalid_request` | 序 5 靜態輸入閘；序 5′ `periodMinutes` 超出界 | `violations[{field:"periodMinutes", message:"須在 <periodMin>～<periodMax> 分鐘之間"}]`（message 內數字取自當下 `status`） |
| 503 | `si_unavailable` | 序 5′：`GET status` 讀不到 `schedule.periodMin／periodMax`（`schedule` 鍵缺席〔根層尚未升版〕、兩鍵缺席或非整數、`min>max`）；**不放行、不用快取值、不退回預設界** | `cause`＝`schedule_bounds_unavailable`（本檔新增的 cause 值；P1b 的九個 cause 不變）、`detail`（缺哪個鍵） |
| 502／503／504 | 逐字沿 `GET /si/status` 的對映 | 序 5′：`GET status` 本身失敗（Bridge 不可達、逾時、`si_unavailable` 原因逐字轉出） | 沿 P1b §2.3 |
| 409 | `si_decision_duplicate` | **不會出現**於這兩個端點（只屬 `POST /proposals/{id}/decide`） | — |

序 5′ 的 `GET status` 沿既有 `SiMirrorUseCase` 路徑（連線 2 秒、讀取 20 秒、不重試）；`enabled=false` 的 `sched-set` 同樣經過序 5′（兩鍵皆必備）。已知邊界：根層 params 改界後，原本合法的目前週期可能落到新界外，此時停用也須先帶一個界內週期（畫面週期輸入預填目前值並提示界；見 §6）。`run-request` 無序 5′。

---

## 2. Bridge 端點（只准 backend-net；Bridge 不持有簽章金鑰、不解內層 body、不驗簽）

### 2.1 `POST /si/schedule:set`（`kind=sched-set`）與 `POST /si/runs:request`（`kind=run-request`）

驗證順序、`store_audit` 語意、201 `{"audit_ref","stored":true}`、其餘方法 405＝**逐字沿 P2b §2.1**（寫入面停用 503 `si_write_disabled`→`X-Bridge-Token` 403 `si_write_forbidden`→本文單一 UTF-8 JSON 物件且 ≤65536 位元組→外層形態驗證→`O_CREAT|O_EXCL` 原樣落檔、`fsync`、同名 409 `si_audit_exists`、其他 `OSError` 503 `si_unavailable`〔`cause=audit_write_failed`〕），差異：

- **無路徑參數**；外層 `kind` 須分別等於 `sched-set`／`run-request`（與端點相符）；外層 `subject` **須為 null**（非 null＝422 `invalid_request`，`violations[{field:"subject", rule, message}]`）。
- 外層鍵集合仍恰七個（P2b §3.1）；Bridge 只驗形態、不解 `body`。
- 路由實作＝`app/routers/si.py` 內以既有 `_store_signed_audit`（`app/si_audit.py`）共用步驟；**不新增任何檔案寫入點**。

### 2.2 靜態鎖（`tests/test_si_readonly_lock.py`；P2b §2.3 判準 1′～5′ **不變**）

> v1.0 實作輪補充（Console TCS D-CS-21／22）：測試另加「判準 6」——兩個新路由函式本體只呼叫 `_store_signed_audit`、不碰 `si_cli`，且路由檔不得含組 argv 的函式；1′～5′ 的常數與判準一字未改。`subject` 非 null 的 422 違規 rule 名沿既有 `must_be_null`（訊息「此端點的 subject 須為 null」）。

- 兩個新路由**不呼叫任何 CLI 動詞、不組 argv**：組 argv 的函式仍恰兩個（`export`、`obs-add --dry-run`）；`si_cli.py` 的 argv 動詞白名單不變。
- 寫入形態仍只准出現在 `app/si_audit.py` 且路徑引數源自 `audit_dir` 參數；新路由對 `_store_signed_audit` 的呼叫是新增呼叫點，不是新增寫入形態。
- 測試增補（實作輪）：兩個新路由的行為測試（權杖、405、409、422〔`subject` 非 null〕、原樣落檔、檔名安全）以 `test_si_write_routes.py` 的既有夾具擴充，不改既有斷言。

---

## 3. 稽核 JSON 契約（Console 側落點；**欄位定稿＝根層 PRD §9.2〈P4 增補〉，本節不複寫**）

### 3.1 外層與 body

- 外層恰七鍵、序固定、緊湊 JSON、UTF-8 無 BOM、檔位元組＝backend 送出本文＝Bridge 落檔位元組＝`audit_sha256` 的對象：**逐字沿 P2b §3.1**；兩種新 kind 的外層 `subject` 一律 `null`。
- body 共通鍵（`schema_rev, audit_ref, kind, user, role(恆 ADMIN), time`）沿 P2b §3.1；kind 專屬鍵：
  - `sched-set`：`enabled`（布林）、`period_minutes`（整數）、`reason`（選用）——欄位語意與界見根層 PRD §9.2〈P4 增補〉「稽核 JSON 兩種新 `kind`」；
  - `run-request`：`note`（選用）。
- **body 鍵序**：共通鍵之後依上列書寫序接 kind 專屬鍵（選用鍵缺席則略過）。**此序為本棒依 P2b 體例所作的暫定，位元組權威是根層 `consoleaudit.py`**（P4 根層鍵 RELEASE 後現查，不符以它為準並修正本檔與 `SiAuditJson`）；跨語言向量會把序釘死。
- `user`＝JWT subject；`time`＝backend `Clock`；簽章（`CONSOLE_SI_AUDIT_KEY` 第一把、HMAC-SHA256 簽 body 字串本身）沿 P2b §3.2。

### 3.2 跨語言向量與黃金檔要求（實作輪產出；本節只定要求，不預填數值）

- **向量**：沿 P2b §3.3 的形式（固定 body、金鑰、預期 mac，Java 與 Python 兩端各一份、值逐字相同），**新增 V5～V8**：`sched-set` 啟用（含 `reason`）、`sched-set` 停用（不含 `reason`）、`run-request` 含 `note`、`run-request` 不含 `note`；向量值由實作輪以 Java 序列化器產出、經根層 `consoleaudit.py` 驗簽收下後入表（本棒不預造數值，避免與 CLI 序不一致）。
- **黃金檔**：沿 P2b §3.4，新增 G6～G9（對映 V5～V8；`Clock.fixed`、金鑰 K0、帳號 admin），住 `backend/src/test/resources/si/audit/` 與 `engine-bridge/tests/fixtures/si_audit/` 逐位元組相同。
- **真 CLI 收下**：`test_si_console_ingest.py` 增兩個案例——G6～G9 被根層 `sched set --carrier console` 與 `run-open --trigger a --carrier console` 收下（這是「Console 簽出的檔能入帳」的唯一自動化證據；前置＝根層鍵 RELEASE）。
- **拒收碼**沿 P2b §3.2 的根層碼（`AUDIT-MAC-MISMATCH`、`AUDIT-TIME-FORMAT`、`AUDIT-SCHEMA`、`AUDIT-KEY-MISSING`、`AUDIT-REF-REUSED`、`AUDIT-KEY-UNKNOWN`、`CTRL-CHAR` 等）；P4 新增的拒收碼（界外週期等）以根層為準，實作輪回寫。

---

## 4. 讀面：`GET /api/v1/si/status` 的 `schedule` 鍵與對帳 `console-writes`

### 4.1 `status.items[0].schedule`

- 形狀＝根層 PRD §9.2〈P4 增補〉「`status.schedule`」逐字（`enabled`、`period_minutes`、`period_min`、`period_max`、`heartbeat_minutes`、`last_set{at,by,carrier}`、`cell_start`、`cell_end`、`ran_this_cell`、`last_skip{at,reason,detail}|null`、`overdue`、`armed`）；`export` 路徑的 `armed` 恆為字串 `NOT-EVALUABLE：export-reads-no-home`（Console 只看事件折出的欄位）；`overdue` 於量不到時為 `null` 並入 `ne`。
- **backend 經既有 `GET /api/v1/si/status` 原樣轉出**，`SiKeyNames` 深層欄名對映擴充（`period_minutes→periodMinutes`、`period_min→periodMin`、`period_max→periodMax`、`heartbeat_minutes→heartbeatMinutes`、`last_set→lastSet`、`cell_start→cellStart`、`cell_end→cellEnd`、`ran_this_cell→ranThisCell`、`last_skip→lastSkip`；`last_set.at／by／carrier` 與 `last_skip.at／reason／detail` 內層鍵本即單字；v1.0 現查：既有 `camel()` 通則已涵蓋九鍵，`SiKeyNames` 主程式零改動、無特例表，`SiKeyNamesTest.AT_964_7_8` 釘住——Console TCS D-CS-15）；缺鍵≠null、未知鍵透傳的既有規則不變（P1b §0.2）。`schema_rev` 維持 1，Bridge 常數 `SI_EXPORT_SCHEMA_REV` 不變。
- 序 5′ 取界使用同一份轉出結果的 `schedule.periodMin／periodMax`（backend 內部以 `SiExport` 取用，不另開查詢路徑）。

### 4.2 `GET /api/v1/si/console-writes` 的變更

沿 P2b §4 與 §8.3 的全部規則，差異：

- `items[].kind` 值域加 `sched-set`、`run-request`；這兩種列的 `subjectId`、`digest`、`dkind`、`supersededBy` **恆為 `null`**（無對象、無 digest；不參與取代判定，P2b §8.5 的 `kind=decide` 前提天然排除）。「`subject_id` 回填」只對 `obs-add` 適用，不變。
- **`ingested` 判準（新 kind）**：事件帳本含任一筆帶相同 `audit_ref` 的 `sched.set`、`run.open` 或 `sched.skip`（根層 PRD AC-SI-37-5）即為 `true`；否則 `false`；`reconcile.status` 為 `NOT-EVALUABLE` 時沿既有整欄為 `null`。（備註：`run-request` 於「已有未關運轉」時入帳結果是 `sched.skip` 而非 `run.open`，兩者都算已入帳——請求已被消耗。）
- **`orphans[]` 新 kind**：事件帳本中 `carrier=console` 且帶 `audit_ref` 的 `sched.set`（映為 kind `sched-set`）、`run.open`／`sched.skip`（映為 kind `run-request`），而表內無對應 `audit_ref` 者，以 `{auditRef, kind, subject:null}` 入列（排序、去重規則沿 P2b §4）。
- 掃描量：events 仍以 `limit=500`、各上限 20 頁；`sched.skip` 已依「同格同因一筆」有界，不另設上限；超限仍是 `scan_cap_exceeded`（NOT-EVALUABLE），不改。
- `kind` 欄的 DB 約束見 §5。

---

## 5. 組態與部署

- **無新環境變數、無新 compose 掛載、無新 CI paths**：兩個 POST 沿既有 `CONSOLE_SI_DECIDERS`、`CONSOLE_SI_AUDIT_KEY`、`BRIDGE_SI_WRITE_TOKEN`、`BRIDGE_SI_AUDIT_DIR`（P2b §5）；`agentconsole-ci.yml` 的 `paths` 已含 SI 路徑（實作輪現查）；`docker-compose.yml` 不改。主機端入帳另需 `AUTOSDD_SI_AUDIT_KEY`（同一把，P2b §5）；巡邏器的金鑰通道見根層 PRD AC-SI-39-1（包裝腳本讀 `AgentConsole/.env` 的 `CONSOLE_SI_AUDIT_KEY` 第一把）。
- **Flyway 新版本（`si_console_writes.kind` CHECK 改版）**：版本號＝實作輪現查 `backend/src/main/resources/db/migration/` 最大號＋1（**本棒寫稿現查最大為 `V22__research_flow_phase_delivered.sql`，故為 V23**；根層 PRD §9.1 C24 檔名表與任務前置所寫「V19／V20」是寫稿時快照，已落後，以現查為準）。內容：`V13__si_console_writes.sql` 的 `kind` 為**欄位內聯的匿名 CHECK**（`CHECK (kind IN ('decide','obs-add','obs-close'))`），PostgreSQL 自動命名（預期為 `si_console_writes_kind_check`，**實作輪以 `pg_constraint` 現查實名，不得憑記憶寫死**）；新版本＝`ALTER TABLE console.si_console_writes DROP CONSTRAINT <實名>`＋`ADD CONSTRAINT … CHECK (kind IN ('decide','obs-add','obs-close','sched-set','run-request'))`。`kind VARCHAR(12)` 足夠（`run-request` 11 字元、`sched-set` 9 字元；**再加 kind 須先放寬欄寬**，記於遷移註解）。`si_console_writes_guard()` trigger 不變（`kind` 仍不可改）；`subject_id`、`digest` 於兩新 kind 為 NULL（欄位本即可為 NULL）。
- 測試：`SiConsoleWritesMigrationIT` 增案例（五值皆可 INSERT、第六值被 CHECK 拒、舊三值列不受影響）、`SchemaMigrationIT`／`V5UpgradeMigrationIT` 的版本斷言隨版本號更新（只改預期值）。

---

## 6. 前端（`components/domain/si/`）資料來源與閘

| 控件 | 資料來源 | 閘與行為 |
|------|----------|----------|
| 橫幅「自動演化排程」欄位組（`SiStatusBanner`／`SiSchedulePanel`） | `useSiStatus()` 的 `items[0].schedule`（不新增 GET）；純函式 `scheduleFields` | 具名欄位；`armed` 固定顯示「量不到：Console 看不到主機上的排程任務」；任何欄位缺席或型別不符＝「量不到」；`schedule` 整鍵缺席＝整組量不到；`overdue===true` 顯示「逾期未巡邏：請在主機執行 `python tools/selfimproving.py sched show`」、`null`＝量不到；`lastSkip` 非 null 顯示時間、原因、細節；全部純文字渲染 |
| `SiScheduleDialog`（啟停＋週期） | 表 M-S；界取自橫幅 `schedule.periodMin／periodMax`（模組內無界值常數）；`periodHint` 換算 | 只對 ADMIN 顯示；週期預填目前 `periodMinutes`；界外值或非整數即時標紅並停用送出；橫幅界取不到＝送出停用並說明「量不到界值」（不放行、以 backend 為準）；缺必填停用送出、連點只送一次；403／503／422 的 reason 與 `violations` 逐字顯示、失敗不關窗；成功顯示收據與入帳指令 |
| `SiRunRequestDialog`（立即啟動） | 表 M-R | 只對 ADMIN 顯示；對帳快取（`console-writes` 既有查詢鍵，**只讀、不發新請求**）已有 `kind=run-request`、`ingested=false` 的列時主鈕停用並顯示「已送出待入帳（稽核編號 <auditRef>）」；快取缺席（無面板的頁面）或對帳 NOT-EVALUABLE 時不停用；成功與失敗呈現同上 |
| `SiWritesPanel` | `GET /console-writes` | 種類標籤加「排程設定」「立即啟動」；待入帳列顯示入帳指令（兩種新指令）；兩新 kind 的 `supersededBy` 恆 null、不進取代群組；孤兒警示含新 kind |
| 說明 `lib/help/self-improving.ts` | — | 補排程欄位與步驟（國高中程度；欄位名逐字取自畫面字樣） |

mutation 成功後使 `status` 與 `console-writes` 查詢失效重取。`lib/api/endpoints.ts` 加 `postSiScheduleSet`、`postSiRunRequest`（數量實作輪現查）；`lib/domain/si.ts` 的 `SI_REASONS` **不新增鍵**（本檔無新 reason）；`SiWriteKind` 與標籤、`ingestCommands`、`SI_STATUS_KNOWN_KEYS` 的增補見 Architecture §5.6。

---

## 7. 驗收對照

| 面 | AT 群（TCS-SelfImprovingSchedule 預定分群；以該 TCS 為準） | 自動測試（預定檔，實作輪現查） |
|----|-----------------------------------------------------------|-------------------------------|
| Bridge 兩個 POST、AST 鎖、契約 | AC-964-8 | `engine-bridge/tests/test_si_write_routes.py`、`test_si_audit_filename_safety.py`、`test_si_console_ingest.py`（真 CLI 入帳）、`test_si_readonly_lock.py` |
| backend 閘門序、輸入閘、界取得、補償、V23 | AC-964-7 | `SiConsoleWriteApiIT`、`SiWriteGatesTest`、`SiAuditSignerTest`、`SiConsoleWritesMigrationIT`、`SiReadOnlyArchTest`、`OpenApiIT`、`SchemaMigrationIT` |
| 稽核 JSON 向量與黃金檔、對帳新 kind | AC-964-9 | `SiAuditSignerTest`（V5～V8）、`SiConsoleWritesReadApiIT`、`test_si_console_ingest.py` |
| frontend 欄位組、對話框、純函式 | AC-964-1～6 | `SiSchedulePanel.test.tsx`、`SiScheduleDialog.test.tsx`、`SiRunRequestDialog.test.tsx`、`SiView.test.tsx`、`si.static.test.ts`、`lib/domain/si.test.ts`、`lib/api/{endpoints,si.endpoints}.test.ts` |
| 文件、說明與既有鎖連動 | AC-964-10 | `lib/help/*.test.ts` 三道鎖與可讀性鎖、`lib/nav/registry.test.ts`（不改）、RTM 子表 |

V 系列（真後端、真容器、真瀏覽器、掌舵者真機；根層 PRD §8.1 P4 出口 (b)：Console `sched-set`／`run-request` 真機走完入帳）不是 AT：結果記於 SCG-4 報告與 RTM 子表的 E2E 欄，未驗者如實標「未驗」。
