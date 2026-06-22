---
name: adr-generate
description: 生成 Architecture Decision Record（ADR），記錄架構或技術決策，支援 Greenfield 設計決策與 Brownfield ADR Archaeology 逆向情境
user-invocable: true
disable-model-invocation: false
argument-hint: "[title: 決策標題] [mode: new|archaeology]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# ADR 生成 Skill（SDD 原生）

SDD 三大支柱之 **Design-as-Doc**：每個技術決策必須有 ADR，架構決策顯性化。支援 Greenfield（新決策）與 Brownfield/Refactoring（ADR Archaeology 逆向挖掘）兩種情境。

---

## 觸發方式

```bash
/adr-generate                              # 互動式建立 ADR（Greenfield）
/adr-generate "使用 PostgreSQL"            # 指定決策標題
/adr-generate "API Gateway 選型" new       # 明確指定新 ADR 模式
/adr-generate archaeology                  # Brownfield：從現有代碼逆向挖掘 ADR
/adr-generate "訂單服務部署" archaeology   # Brownfield：針對特定領域逆向
```

---

## 前置條件（SDD Spec-First）

| 模式 | 前置條件 | 說明 |
|------|---------|------|
| new（新 ADR） | 🔷 SCG-1（建議） | 在 SRD 設計階段並行產出 ADR |
| archaeology（逆向） | 無 SCG 前置 | 本 Skill 本身產出 As-Is ADR，為 SCG-2 提供輸入 |

---

## 執行流程

---

### 情境 A：Greenfield — 新建 ADR

#### 階段 1：確認 ADR 觸發時機

| 情境 | 範例決策 |
|------|---------|
| 技術棧選擇 | 語言、框架、資料庫選型 |
| 架構模式選擇 | Monolith / Microservices / Event-Driven |
| 整合策略 | API / Event / File / DB Share |
| 安全機制選擇 | Auth / Encryption / Token 方案 |
| 部署策略 | Container / Serverless / VM |
| 重大重構決策 | Strangler Fig / Branch by Abstraction |

---

#### 階段 2：確認 ADR 序號

掃描 `docs/02_architecture/adr/ADR-*.md`，取得下一個序號（NNN = 現有最大序號 + 1）。

🔴 確認序號不重複。

---

#### 階段 3：填寫 ADR 內容

```markdown
# ADR-{NNN}: {決策標題}

**Status**: Proposed
**Date**: {YYYY-MM-DD}
**Deciders**: {決策者/角色}
**Context Tags**: #{技術標籤}

## Context
{為何需要做此決策。描述當前面臨的問題、約束條件、以及為什麼此決策不可避免。}

## Decision
{選擇了什麼。具體、可執行的決策聲明。}

## Rationale
{選擇理由。為什麼這個方案優於其他替代方案。}

## Consequences
### 正面影響
- {優點 1}
- {優點 2}

### 負面影響 / 風險
- {缺點或需注意事項}
- {遺留問題}

## Alternatives Considered
| 方案 | 優點 | 缺點 | 排除理由 |
|------|------|------|---------|
| {方案 A} | {優} | {缺} | {排除原因} |
| {方案 B} | {優} | {缺} | {排除原因} |

## Related Documents
- [SRD-{SystemName}.md](../../SRD-{SystemName}.md)
- [FRD-{SystemName}.md](../../../01_requirements/FRD-{SystemName}.md)
```

---

#### 階段 4：存檔與索引更新 🔴

1. 存放路徑：`docs/02_architecture/adr/ADR-{NNN}-{kebab-title}.md`
2. 更新 ADR 索引（若 `docs/02_architecture/adr/ADR-INDEX.md` 存在）
3. 執行 `/spec-compliance-check docs/02_architecture/adr/ADR-{NNN}-*.md`
4. 🔴 確認點：Status 是否從 Proposed 更新為 Accepted（需架構師確認）

---

### 情境 B：Brownfield — ADR Archaeology（逆向挖掘）

**適用場景**：現有系統缺乏 ADR 文件，需從代碼、Config、部署設定中逆向推斷當初的架構決策，作為 As-Is 規格化的一部分。

---

#### 階段 1：系統性掃描

**技術棧線索**：
```
package.json / pom.xml / requirements.txt / go.mod
  → 框架版本、主要依賴庫 → 推斷技術選型決策

Dockerfile / docker-compose.yml / k8s/*.yaml
  → 部署策略 → 推斷部署架構決策

.env.example / config/
  → 整合服務（DB/Cache/Queue）→ 推斷資料存儲決策

src/auth/ / middleware/
  → 認證實作 → 推斷認證方案決策

src/models/ / migrations/
  → ORM/Schema → 推斷資料模型決策
```

**架構模式線索**：
```
單一 main.go/app.js → Monolith
多個 service/ 目錄 → Microservices
/events/ 或 MQ 配置 → Event-Driven
```

---

#### 階段 2：逆向 ADR 產出格式

```markdown
# ADR-{NNN}: {推斷的決策標題}

**Status**: Accepted（推斷，需人工確認）
**Date**: {推斷日期，從 git log 取第一次相關 commit 日期}
**Deciders**: 不明（Archaeology 模式）
**x-sdd-archaeology**: true（標記為逆向產出）

## Context
{從代碼結構和依賴推斷的背景說明}

**[逆向推斷]** 根據 {具體文件/代碼位置} 判斷：{推斷依據}

## Decision
{從代碼推斷的決策}

**[逆向推斷]** 此決策體現於：{具體文件路徑:行號}

## Rationale
[不明] 原始決策理由未有文件記錄。推測可能原因：{合理推測}

## Consequences
### 已觀察到的影響
- {從代碼/問題中觀察到的實際後果}

### 已知問題
- {Tech Debt 或已知問題，引用 TD-XXX}

## Alternatives Considered
[無文件記錄，Archaeology 模式略]

## Related Documents
- [現有代碼路徑]({相對路徑})
- Tech Debt: TD-{NNN}（若有相關技術債）

## Archaeology Notes
**來源文件**: {掃描的文件清單}
**信心度**: 高/中/低
**待確認**: {需人工驗證的內容}
```

---

#### 階段 3：Archaeology 彙整報告 🔴

彙整所有逆向產出的 ADR：

```markdown
## ADR Archaeology 摘要

**系統**: {SystemName}
**掃描範圍**: {目錄清單}
**產出 ADR 數**: {N}

| ADR | 決策類型 | 信心度 | 待確認 |
|-----|---------|--------|--------|
| ADR-{NNN} | 技術棧選型 | 高 | 選型理由 |
| ADR-{NNN} | 部署策略 | 中 | 為何選 K8s |
```

🔴 **確認點**：Archaeology 產出的 ADR 需原系統熟悉者審查，Status 才可從 Proposed 改為 Accepted。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| ADR 文件（new） | `docs/02_architecture/adr/ADR-{NNN}-{kebab-title}.md` | SCG-2 前 |
| ADR 文件（archaeology） | `docs/02_architecture/adr/ADR-{NNN}-{kebab-title}.md` | Brownfield SCG-2 前 |
| Archaeology 摘要 | `docs/02_architecture/ADR-ARCHAEOLOGY-{System}.md` | Brownfield 場景 |

---

## 後置動作

```
/spec-compliance-check docs/02_architecture/adr/ADR-{NNN}-*.md
```

- 若 new 模式完成所有架構決策 ADR → `/sdd-gate SCG-2`
- 若 archaeology 完成 → `/brownfield-analysis` 繼續 Gap Analysis

🔷 **本 Skill 協助通過**：SCG-2（Architecture Freeze Gate）

---

## 相關 Skill

- `/sd-architect` — 架構設計（觸發 ADR 的主要 Skill）
- `/brownfield-analysis` — Brownfield 場景（archaeology 模式的上下文）
- `/spec-compliance-check` — 驗證 ADR 格式
- `/sdd-gate SCG-2` — 架構凍結閘門（所有 ADR Status: Accepted 才通過）

---

**基於**: AISDLC-SDD v0.01（SDD 專屬 Skill）
**對應 SDD 原則**: Design-as-Doc（設計即文件）
**對應範本**: `docs_template/sdd/adr/ADR-TEMPLATE.md`
