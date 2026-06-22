---
name: sd-architect
description: 以 System Designer 角色設計系統架構，產出 SRD、C4 圖和 ADR，準備 SCG-1/SCG-2 架構閘門
user-invocable: true
disable-model-invocation: false
argument-hint: "[scope: full|api|c4|adr] [scenario: greenfield|brownfield|refactoring]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# SD 系統架構設計 Skill（SDD 原生）

SD 在 SDD 工作流中負責從 FRD 到可執行架構的轉化。本 Skill 產出 SRD、C4 模型、ADR，以及 API Spec 草稿，分別對應 SCG-1（設計凍結）和 SCG-2（架構凍結）兩個閘門。

---

## 觸發方式

```bash
/sd-architect                         # 完整架構設計（Greenfield 全流程）
/sd-architect api                     # 僅 API 端點設計
/sd-architect c4                      # 僅 C4 架構圖設計
/sd-architect adr                     # 補建架構決策 ADR
/sd-architect brownfield              # Brownfield：As-Is → To-Be 架構設計
/sd-architect refactoring             # Refactoring：現有架構評估與改善設計
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-0 通過 | FRD 已凍結，需求明確 | `/sdd-gate SCG-0` 報告存在 |

> Brownfield 情境額外需要：`docs/02_architecture/AS-IS-SRD-{System}.md`（來自 `/brownfield-analysis`）

---

## 執行流程

### 階段 1：技術需求分析

讀取前置文件：
- `docs/01_requirements/FRD-{SystemName}.md`
- `docs/03_testing/RTM-{SystemName}.md`（確認 NFR 量化指標）

技術評估確認（🔴 確認點）：

```markdown
## 技術評估確認問題

- Q1: 核心功能的技術複雜度？是否有即時/高並發/大數據需求？
- Q2: 需整合的外部系統清單（影響整合架構決策）？
- Q3: NFR 效能目標（P99/吞吐量）？
- Q4: 可用性 SLA？單點故障容忍度？
- Q5: 安全等級（資料分類/合規要求）？
- Q6: 現有技術棧約束（若 Brownfield）？
- Q7: 部署環境限制（雲/地端/混合）？
```

🔴 技術評估問題必須有答案才進入設計。

---

### 階段 2：C4 架構圖設計（SCG-2 必要條件）

#### C4 Level 1 — Context（系統邊界）

```markdown
## C4 Context — {SystemName}

**說明**: 系統與外部角色/系統的關係

### 使用者
- {角色 A}: {如何與系統互動}
- {角色 B}: {如何與系統互動}

### 外部系統
- {外部系統 A}: {整合方式，ADR-XXX}
- {外部系統 B}: {整合方式，ADR-XXX}

[附 PlantUML/Mermaid 圖表]
```

#### C4 Level 2 — Container（主要組件）

```markdown
## C4 Container — {SystemName}

| 容器 | 技術 | 說明 | ADR |
|------|------|------|-----|
| Web App | {框架} | {用途} | ADR-{NNN} |
| API Server | {框架} | {用途} | ADR-{NNN} |
| Database | {DB} | {用途} | ADR-{NNN} |
| Cache | {Redis/等} | {用途} | ADR-{NNN} |

[附容器架構圖]
```

---

### 階段 3：架構決策（ADR）產出

**每個重大技術選型必須有 ADR**。直接呼叫 `/adr-generate`：

```bash
/adr-generate "技術棧選型 — Backend Framework"
/adr-generate "資料庫選型"
/adr-generate "認證機制選型"
/adr-generate "部署策略"
# ... 依決策數量重複
```

ADR 類型清單（需確認全部覆蓋）：
- [ ] 後端框架選型 ADR
- [ ] 資料庫選型 ADR
- [ ] 認證/授權機制 ADR
- [ ] 部署策略 ADR
- [ ] 整合策略 ADR（若有第三方整合）
- [ ] 安全架構 ADR（Security 情境）
- [ ] Strangler Fig / Branch by Abstraction ADR（Refactoring 情境）

---

### 階段 4：SRD 文件產出（SCG-1 必要條件）

**文件路徑**：`docs/02_architecture/SRD-{SystemName}.md`
**範本來源**：`docs_template/core/srd/SRD_Module_Template.md`

```markdown
# System Requirements Document — {SystemName}

**SRD-ID**: SRD-{System}-{seq}
**版本**: 1.0
**日期**: {YYYY-MM-DD}
**狀態**: Draft → Approved
**來源**: FRD-{SystemName}.md（via SCG-0）

## 1. 系統概述
### 1.1 目的與範圍
### 1.2 架構決策摘要（引用 ADR-XXX）

## 2. C4 架構模型
- [C4 Context 圖](../diagrams/C4-Context-{System}.md)
- [C4 Container 圖](../diagrams/C4-Container-{System}.md)

## 3. 技術棧
| 層級 | 技術 | 版本 | ADR |
|------|------|------|-----|
| Backend | {框架} | {版本} | ADR-{NNN} |
| Database | {DB} | {版本} | ADR-{NNN} |
| Cache | {Redis} | {版本} | ADR-{NNN} |

## 4. 模組設計
### {模組 A}
- **職責**: {說明}
- **介面**: {對外 API}
- **依賴**: {依賴模組}

## 5. 資料模型設計
{ER 圖或表格}

## 6. API 端點清單（草稿）
| API-ID | Method | Path | 說明 | 認證 |
|--------|--------|------|------|------|
| API-001 | POST | /{resource} | {說明} | Bearer |

（詳細規格由 `/contract-generate` 產出）

## 7. NFR 設計對應
| NFR-ID | 指標 | 設計方案 |
|--------|------|---------|
| NFR-001 | P99 < {N}ms | {快取/索引/負載均衡策略} |

## 8. 部署架構
{部署圖說明}

## 9. Brownfield 情境：Before/After 對比
（僅 Brownfield/Refactoring 情境填寫）
| 組件 | As-Is | To-Be | ADR |
|------|-------|-------|-----|

## 10. 安全設計（Security 情境）
- Trust Boundary Map（ADR-{NNN}）
- {STRIDE 威脅模型引用}
```

---

### 階段 5：RTM 更新（嵌入流程）

SRD 完成後執行 RTM 更新，加入 API 追溯：

```bash
/rtm-generate update docs/02_architecture/SRD-{SystemName}.md
```

---

### 階段 6：文件驗證與閘門準備 🔴

1. 執行 `/spec-compliance-check docs/02_architecture/SRD-{SystemName}.md`
2. 執行 `/spec-compliance-check SCG-1`（確認 SRD + API Spec 草稿完整）
3. 若 SCG-1 通過 → 繼續 C4 + ADR → 執行 `/spec-compliance-check SCG-2`
4. 🔴 確認點：架構設計必須由開發團隊確認技術可行性

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| SRD（Greenfield） | `docs/02_architecture/SRD-{SystemName}.md` | SCG-1 |
| AS-IS SRD（Brownfield） | `docs/02_architecture/AS-IS-SRD-{SystemName}.md` | SCG-1 |
| C4 Context 圖 | `docs/02_architecture/diagrams/C4-Context-{System}.md` | SCG-2 |
| C4 Container 圖 | `docs/02_architecture/diagrams/C4-Container-{System}.md` | SCG-2 |
| ADR（每個架構決策） | `docs/02_architecture/adr/ADR-{NNN}-{title}.md` | SCG-2 |
| API 端點清單（草稿） | SRD 第 6 章（正式 Contract 由 /contract-generate 產出） | SCG-1 草稿 |

---

## 後置動作

```
/adr-generate                          # 補建任何遺漏的 ADR
/sdd-gate SCG-1                        # 設計凍結閘門
/sdd-gate SCG-2                        # 架構凍結閘門（ADR 全部 Accepted 後）
/contract-generate openapi "{Module}"  # SCG-2 通過後，開始 Contract 設計
```

🔷 **本 Skill 協助通過**：SCG-1（Architecture Spec Gate）、SCG-2（Architecture Freeze Gate）

---

## 相關 Skill

- `/sa-analyst` — 需求分析（本 Skill 的前置）
- `/adr-generate` — 架構決策（在本 Skill 中呼叫）
- `/contract-generate` — API Contract（SCG-2 通過後接棒）
- `/brownfield-analysis` — Brownfield 場景 As-Is 分析
- `/sdd-gate SCG-2` — 架構凍結閘門

---

**基於**: AISDLC-SDD v0.19
**對應 Agent**: `05.sd-architect-zh.yaml`
**對應 SDD Enhancement**: `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`
