---
name: documentation-api
description: API 文件從 OpenAPI Contract 生成（非逆向），SCG-3 Contract 凍結後才產出，Living Doc 策略
user-invocable: true
disable-model-invocation: false
argument-hint: "[format: openapi|markdown|both] [source: contract|code]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Documentation API Skill（SDD 原生）

在 SDD 中，API 文件的唯一真相來源是 OpenAPI Contract，而非程式碼。本 Skill 在 SCG-3 Contract 凍結後從 `CONTRACT-*.yaml` 生成開發者文件，確保文件與規格一致（Contract-as-Documentation）。本 Skill **不逆向掃描程式碼**產生 API 文件，那是 Brownfield 情境用 `/contract-generate reverse`。

---

## 觸發方式

```bash
/documentation-api openapi        # 從 Contract 生成 OpenAPI 文件
/documentation-api markdown       # 生成 Markdown 開發者指南
/documentation-api both           # 兩種格式都生成
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-3 通過 | API Contract 已凍結 | `docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml` 存在 |

> **SDD 規則**：SCG-3 未通過 → 不可生成 API 文件（文件應來自規格，而非代碼）

---

## 執行流程

### 階段 1：讀取凍結 Contract

讀取 `docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml`，確認：
- `openapi: 3.1.0`（非 3.0.x）
- `info.version` 版本號
- 所有端點的 `operationId` 已定義
- 所有端點有完整的 `summary` 和 `description`
- `x-sdd-feature-id`（追溯 FRD F-XXX）標籤存在

---

### 階段 2：OpenAPI 文件美化（Redoc/Swagger UI 可用格式）

驗證並補充 Contract 缺少的文件屬性：

```yaml
# 補充至 CONTRACT-{Module}-v{N}.yaml（不修改業務定義，只補文件屬性）
info:
  title: "{SystemName} API"
  version: "{N}.{N}"
  description: |
    {系統說明}

    ## 使用前提
    - 所有請求需帶 `Authorization: Bearer <JWT>`
    - Base URL: `https://api.{system}.com/v1`

  contact:
    name: "{Team}"
  x-sdd-contract-frozen: true
  x-sdd-scg3-date: "{YYYY-MM-DD}"

# 確保每個端點有 FRD 追溯
paths:
  /users:
    post:
      summary: 建立用戶
      description: |
        建立新用戶帳號。
        **FRD 追溯**: F-001 用戶註冊功能
        **AC**: AC-001-1, AC-001-2
      x-sdd-feature-id: "F-001"
      x-sdd-us-id: "US-001"
```

---

### 階段 3：Markdown 開發者指南產出

**文件路徑**：`docs/02_architecture/api/API-GUIDE-{Module}.md`

```markdown
# {Module} API 開發者指南

**Contract 版本**: {N}.{N}（SCG-3 凍結：{date}）
**Contract 來源**: `CONTRACT-{Module}-v{N}.yaml`

## 概覽

- **Base URL**: `https://api.{system}.com/v1`
- **認證方式**: Bearer Token（JWT，RS256）
- **回應格式**: JSON（application/json）
- **版本策略**: URL Path Versioning（`/v1`, `/v2`）

## 端點清單（對應 FRD Feature）

| 端點 | 方法 | FRD Feature | 說明 |
|------|------|------------|------|
| /users | POST | F-001 | 建立用戶 |
| /users/{id} | GET | F-002 | 取得用戶資料 |

## 認證說明

```
Authorization: Bearer <JWT>
```

JWT 有效期：{NFR-SEC-001 定義值}（如：1h）

## 錯誤碼對照表

| HTTP 狀態碼 | 業務錯誤碼 | 說明 |
|------------|----------|------|
| 400 | VALIDATION_ERROR | 請求格式不符 Contract |
| 401 | UNAUTHORIZED | JWT 無效或過期 |
| 403 | FORBIDDEN | 無授權執行此操作 |
| 404 | NOT_FOUND | 資源不存在 |
| 500 | INTERNAL_ERROR | 系統錯誤 |

## 變更歷史（Contract 版本追蹤）

| 版本 | 日期 | 變更摘要 | SCG-3 凍結 |
|------|------|---------|-----------|
| 1.0 | {date} | 初版 | ✅ |
```

---

### 階段 4：Living Documentation 策略 🔴

SDD Living Doc：文件更新與 Contract 版本同步，非手動維護：

```markdown
# Living Documentation 策略（docs/05_development/LIVING-DOC-STRATEGY-{System}.md）

## Contract-as-Documentation 原則

1. API 文件的唯一真相來源：`CONTRACT-*.yaml`
2. 文件更新觸發點：Contract 版本升級（需重走 SCG-3）
3. CI/CD 自動驗證：Pipeline contract-validation Stage 驗證文件版本
4. 禁止手動修改生成的 API 文件（直接修改 Contract）
```

```bash
/rtm-generate update    # 更新 API 文件相關追溯鏈（AC → API-XXX → 文件版本）
/spec-compliance-check docs/02_architecture/api/API-GUIDE-{Module}.md
```

🔴 確認點：API-GUIDE 版本號與 CONTRACT 版本號一致。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| API 開發者指南 | `docs/02_architecture/api/API-GUIDE-{Module}.md` | SCG-3 後 |
| Living Doc 策略 | `docs/05_development/LIVING-DOC-STRATEGY-{System}.md` | SCG-3 後 |

---

## 後置動作

```
/spec-compliance-check docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml
/devops-github-actions    # 確認 CI/CD 包含 Contract 文件同步驗證
```

🔷 **本 Skill 對應 SCG**：SCG-3 後（Contract 凍結的文件化）

---

## 相關 Skill

- `/contract-generate` — 產出 API Contract（本 Skill 的輸入來源）
- `/sdd-gate SCG-3` — Contract 凍結閘門（本 Skill 的前置條件）
- `/spec-compliance-check` — 驗證 Contract 格式合規

---

**基於**: AISDLC-SDD v0.22
**Contract 規格**: `docs/02_architecture/api/CONTRACT-*.yaml`
**對應工作流**: `workflow/core/SDD_SPEC_FIRST_GATE.md`
