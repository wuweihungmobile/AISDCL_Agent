---
name: contract-generate
description: 生成 API Contract（OpenAPI 3.1）或 Consumer-Driven Contract，實現 Contract-First 開發，支援 Brownfield 逆向 Contract 情境
user-invocable: true
disable-model-invocation: false
argument-hint: "<type: openapi|consumer|provider|compat|reverse> [module: 模組名稱]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Contract 生成 Skill（SDD 原生）

SDD 三大支柱之 **Contract-Driven Development**：API Contract 凍結（SCG-3）後才能開始後端實作。支援 Greenfield（設計先行）與 Brownfield（逆向規格化）兩種情境。

---

## 觸發方式

```bash
/contract-generate openapi "Order API"     # Greenfield: 生成 OpenAPI 3.1 規格
/contract-generate consumer "Payment"      # 生成 Consumer Contract（CDC）
/contract-generate provider "User Service" # 生成 Provider API Spec
/contract-generate compat "v1→v2"          # 生成 API 相容性聲明（廢棄保護）
/contract-generate reverse "src/routes/"   # Brownfield: 從現有代碼逆向生成 Contract
```

---

## 前置條件（SDD Spec-First）

| 情境 | 閘門 | 說明 | 驗證方式 |
|------|------|------|---------|
| Greenfield（openapi/consumer/provider） | 🔷 SCG-1 | SRD 已完成，API 端點清單已確定 | `/sdd-gate SCG-1` |
| Brownfield（reverse） | 無前置 SCG | 本 Skill 本身產出 As-Is Contract，作為 SCG-1 輸入 | — |
| Compat 聲明 | 🔷 SCG-2 | 架構已凍結，廢棄決策已有 ADR | `/sdd-gate SCG-2` |

---

## 執行流程

### 情境 A：Greenfield — OpenAPI Contract 設計

#### 階段 1：收集 API 需求

讀取：
- `docs/01_requirements/FRD-{System}.md`（功能需求）
- `docs/02_architecture/SRD-{System}.md`（API 端點清單）

確認：
- 所有端點的 HTTP Method、URL、參數
- Request/Response Schema（資料模型）
- 認證方式（Bearer/API Key/OAuth）

---

#### 階段 2：撰寫 OpenAPI 3.1 規格

```yaml
openapi: 3.1.0
info:
  title: {Module} API
  version: "1.0.0"
  description: "{功能描述}"
  contact:
    name: "{系統名稱} API Team"

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://api.staging.example.com/v1
    description: Staging

paths:
  /{resource}:
    post:
      operationId: create{Resource}
      summary: "建立 {資源}"
      tags: ["{Module}"]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/{Resource}Request'
      responses:
        '201':
          description: 建立成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/{Resource}Response'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '422':
          $ref: '#/components/responses/UnprocessableEntity'
        '500':
          $ref: '#/components/responses/InternalServerError'

components:
  schemas:
    {Resource}Request:
      type: object
      required: [field1, field2]
      properties:
        field1:
          type: string
          description: "{說明}"
          example: "{範例值}"
    {Resource}Response:
      type: object
      properties:
        id:
          type: string
          format: uuid
        field1:
          type: string

  responses:
    BadRequest:
      description: 請求參數錯誤
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    Unauthorized:
      description: 未授權（Token 無效或過期）
    Forbidden:
      description: 無權限執行此操作
    InternalServerError:
      description: 伺服器內部錯誤

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

---

#### 階段 3：SCG-3 凍結 🔴

```
🔷 SCG-3 通過條件：
  - [ ] openapi: 3.1.0（非 3.0.x 或 2.0）
  - [ ] 所有端點有完整的 Request/Response Schema
  - [ ] 錯誤碼定義完整（400/401/403/404/500）
  - [ ] Consumer Contract（如有整合）完成
  - [ ] API ID 與 RTM 已對應（/rtm-generate update）
  - [ ] Contract 已 Review 通過
```

🔴 **等待人工確認 SCG-3 通過後，後端才可開始實作！**

---

### 情境 B：Consumer-Driven Contract（CDC）

#### 階段 1：定義互動

```yaml
# CONSUMER-CONTRACT-{Service}.yaml
consumer: "{ConsumerService}"
provider: "{ProviderService}"
interactions:
  - description: "請求 {資源}"
    request:
      method: GET
      path: /{resource}/{id}
      headers:
        Authorization: Bearer {token}
    response:
      status: 200
      headers:
        Content-Type: application/json
      body:
        id: "{id}"
        status: "active"
  - description: "請求不存在的 {資源}"
    request:
      method: GET
      path: /{resource}/nonexistent
    response:
      status: 404
```

---

### 情境 C：API Compat 聲明（廢棄保護）

使用時機：廢棄舊 API 端點前，必須先建立 compat 聲明。

```markdown
# API Compat 聲明：{Module} v{N} → v{N+1}

**ADR 依據**: ADR-{NNN}-{kebab-title}.md
**廢棄日期**: {YYYY-MM-DD}（至少 3 個月緩衝期）

## 廢棄端點清單

| 舊端點 | 新端點 | 廢棄時間 | 遷移說明 |
|--------|--------|---------|---------|
| POST /api/v1/orders | POST /api/v2/orders | {date} | Request body 新增 `customerId` 必填欄位 |

## 向後相容承諾

- v1 端點在 {廢棄日期} 前繼續提供服務
- 回應格式新增欄位不視為 Breaking Change
- 移除欄位前需 ADR 決策

## 遷移指引

{詳細遷移說明}
```

---

### 情境 D：Brownfield — 逆向生成 Contract（reverse）

**適用場景**：現有系統無 Contract 文件，需從程式碼逆向產出，作為 As-Is 規格化的一部分。

#### 階段 1：分析現有 API 實作

掃描路由檔案（依框架判斷）：
- Express/Fastify：`src/routes/`、`app/api/`
- Spring Boot：`@RestController` 類別
- FastAPI：`@router.get/post/put/delete` 裝飾器
- Django/DRF：`urls.py` + `views.py`

#### 階段 2：萃取端點資訊

對每個發現的端點記錄：
```
- HTTP Method + URL
- Path/Query/Body 參數（推斷型別）
- Response 結構（從代碼推斷）
- 認證方式（從 middleware 推斷）
- 錯誤處理（從 try/catch 推斷）
```

#### 階段 3：產出 As-Is Contract

- 格式與 Greenfield OpenAPI 3.1 相同
- 欄位說明標注 `[逆向推斷]`，需人工確認
- Status 標記為 `x-status: as-is-reverse`
- 存放路徑：`docs/02_architecture/api/AS-IS-CONTRACT-{Module}.yaml`

#### 階段 4：差距標記 🔴

```yaml
x-sdd-gap:
  missing-error-codes:
    - "POST /orders: 缺少 401/403 定義"
  schema-incomplete:
    - "GET /users/{id}: Response schema 需補充"
  undocumented-endpoints:
    - "/internal/admin: 未文件化端點，建議補充或移除"
```

🔴 **確認點**：逆向產出的 Contract 需人工審查確認正確性，才可作為 As-Is 規格凍結依據。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| OpenAPI Contract | `docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml` | SCG-3 |
| Consumer Contract | `docs/02_architecture/api/CONSUMER-CONTRACT-{Service}.yaml` | SCG-3 |
| Provider API Spec | `docs/02_architecture/api/PROVIDER-API-SPEC-{Service}.yaml` | SCG-3 |
| API Compat 聲明 | `docs/02_architecture/api/API-COMPAT-{Module}.md` | SCG-2 後 |
| As-Is Contract（逆向） | `docs/02_architecture/api/AS-IS-CONTRACT-{Module}.yaml` | Brownfield 起點 |

---

## 後置動作

完成本 Skill 後：
```
/rtm-generate update          # 更新 RTM 的 API 追溯欄位
/spec-compliance-check docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml
/sdd-gate SCG-3               # （Greenfield openapi 完成後）
```

🔷 **本 Skill 協助通過**：SCG-3（API Contract Freeze）

---

## 相關 Skill

- `/adr-generate` — 記錄 API 設計決策（Contract 設計前建立）
- `/spec-compliance-check` — 驗證 Contract 格式是否符合 OpenAPI 3.1
- `/sdd-gate SCG-3` — 執行 Contract Freeze 閘門
- `/rtm-generate update` — 更新 RTM API 追溯
- `/brownfield-analysis` — Brownfield 逆向分析（reverse 情境的前置）

---

**基於**: AISDLC-SDD v0.26（SDD 專屬 Skill）
**對應 SDD 原則**: Contract-Driven Development（SCG-3）
**對應範本**: `docs_template/sdd/api/CONTRACT-TEMPLATE.yaml`
