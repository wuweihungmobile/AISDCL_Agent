---
name: brownfield
description: 分析既有系統，執行逆向規格工程產出 As-Is SRD，完成 Gap Analysis 和 Tech Debt 量化，為 SDD Brownfield 場景提供 SCG-0/1 前置基線
user-invocable: true
disable-model-invocation: false
argument-hint: "[focus: full|as-is-srd|gap-analysis|tech-debt|arch] [system_path: 系統根目錄]"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Brownfield 逆向規格工程 Skill（SDD 原生）

Brownfield 是 SDD 中最複雜的場景。本 Skill 是 Brownfield 工作流的**起點**，從現有系統逆向產出 As-Is 規格，作為 SCG-0/1 的前置基線。完成後交棒給 `/sa-analyze` 和 `/sd-design`。

---

## 觸發方式

```bash
/brownfield                        # 完整逆向規格工程（Brownfield 起點）
/brownfield as-is-srd              # 僅產出 As-Is SRD
/brownfield gap-analysis           # 僅執行 Gap Analysis
/brownfield tech-debt              # 僅量化技術債
/brownfield arch                   # 僅分析架構問題
```

---

## 前置條件（SDD Spec-First）

> 本 Skill 是 Brownfield 場景的起點，無 SCG 前置條件。本 Skill 產出的文件是後續 SCG-0/1 的前置輸入。

---

## 執行流程

### 階段 0：系統範圍確認 🔴

確認分析範圍：
- 系統名稱（{SystemName}）
- 要分析的根目錄路徑
- 是否有現有文件（架構文件/ADR/API 文件）

🔴 確認點：明確分析範圍，避免過寬或過窄。

---

### 階段 1：技術棧識別（As-Is 技術輪廓）

掃描：
- 依賴管理文件（`package.json`/`pom.xml`/`requirements.txt`/`go.mod`）
- 框架識別（目錄結構/import 分析）
- 部署設定（`Dockerfile`/`docker-compose.yml`/K8s YAML）
- 資料庫（連線設定/migration 文件）
- 第三方整合（環境變數/config）

**產出：技術棧清單**

```markdown
## As-Is 技術棧

| 層級 | 技術 | 版本 | 備註 |
|------|------|------|------|
| Backend | {框架} | {版本} | |
| Database | {DB} | {版本} | 已知問題: {TD-XXX} |
| Cache | {技術} | {版本} | |
| 第三方整合 | {服務} | — | |
```

---

### 階段 2：逆向架構分析（As-Is Architecture）

#### 2.1 目錄結構與模組分析

識別：
- 主要模組/服務邊界
- 分層結構（是否清晰）
- 循環依賴（風險項目 → TD-XXX）
- 未文件化端點（逐一記錄）

#### 2.2 API 端點逆向

掃描路由文件，識別所有 API 端點：

```markdown
## As-Is API 端點清單

| Method | Path | 說明（推斷） | Auth | 問題 |
|--------|------|------------|------|------|
| POST | /{resource} | {推斷} | Bearer | {缺少 401} |
```

調用 `/contract-generate reverse` 產出 As-Is Contract。

#### 2.3 資料模型逆向

從 migration/schema 文件識別資料結構：

```markdown
## As-Is 資料模型

| 表格 | 主要欄位 | 關係 | 索引 | 問題（TD-XXX） |
|------|---------|------|------|------------|
| {table} | {fields} | {FK} | {index} | {TD-XXX} |
```

---

### 階段 3：As-Is SRD 產出（SCG-1 輸入基線）

**文件路徑**：`docs/02_architecture/AS-IS-SRD-{SystemName}.md`
**範本來源**：`docs_template/sdd/architecture/AS-IS-SRD-TEMPLATE.md`

```markdown
# As-Is System Requirements Document — {SystemName}

**版本**: 1.0
**日期**: {YYYY-MM-DD}
**x-sdd-type**: as-is（逆向規格化）

## 1. 系統概述（逆向推斷）
## 2. As-Is 技術棧
## 3. As-Is 架構（C4 Context/Container 逆向）
## 4. As-Is API 端點清單
## 5. As-Is 資料模型
## 6. 已知問題清單（TD-XXX 格式）
## 7. 架構決策（ADR Archaeology 結果）
```

呼叫 `/adr-generate archaeology` 逆向挖掘架構決策 ADR。

---

### 階段 4：Gap Analysis（As-Is vs To-Be）

**文件路徑**：`docs/04_planning/GAP-ANALYSIS-{SystemName}.md`

```markdown
# Gap Analysis — {SystemName}

**As-Is 基線**: docs/02_architecture/AS-IS-SRD-{SystemName}.md
**To-Be 目標**: docs/01_requirements/PRD-{SystemName}.md（若存在）

## 功能差距

| 功能 | As-Is 狀態 | To-Be 需求 | 差距 | 優先級 |
|------|-----------|-----------|------|--------|
| {功能} | {現況} | {目標} | {差距說明} | P1/P2/P3 |

## 技術差距

| 技術面向 | As-Is | To-Be | 遷移策略 | ADR |
|---------|-------|-------|---------|-----|
| {架構} | {現況} | {目標} | Strangler Fig / 直接替換 | ADR-{NNN} |

## 重構路線建議
### Phase 1: 穩定（修復 P1 Tech Debt）
### Phase 2: 改善（架構重構）
### Phase 3: 演進（To-Be 架構）
```

---

### 階段 5：Tech Debt 量化（TD-XXX 格式）

**文件路徑**：`docs/06_quality/TECH-DEBT-SPEC-{SystemName}.md`

```markdown
# Tech Debt Spec — {SystemName}

| TD-ID | 描述 | 類型 | 影響 | 估算工時 | 優先級 |
|-------|------|------|------|---------|--------|
| TD-001 | {技術債描述} | 代碼/架構/依賴/安全 | {業務影響} | {N}h | P1 |
```

---

### 階段 6：RTM 現有系統版本建立

```bash
/rtm-generate full docs/02_architecture/AS-IS-SRD-{SystemName}.md
# 產出 docs/03_testing/RTM-{SystemName}-existing.md
```

---

### 階段 7：文件驗證 🔴

1. 執行 `/spec-compliance-check docs/02_architecture/AS-IS-SRD-{SystemName}.md`
2. 🔴 確認點：As-Is SRD 必須由熟悉現有系統的人員審查確認（非僅由分析工具決定）

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 後續使用 |
|--------|------|---------|
| As-Is SRD | `docs/02_architecture/AS-IS-SRD-{SystemName}.md` | SCG-1 基線 |
| As-Is Contract | `docs/02_architecture/api/AS-IS-CONTRACT-{Module}.yaml` | Contract 差距分析 |
| Gap Analysis | `docs/04_planning/GAP-ANALYSIS-{SystemName}.md` | To-Be 設計輸入 |
| Tech Debt Spec | `docs/06_quality/TECH-DEBT-SPEC-{SystemName}.md` | Refactoring 計畫 |
| ADR Archaeology | `docs/02_architecture/ADR-ARCHAEOLOGY-{SystemName}.md` | SCG-2 補充 |
| RTM（現有系統）| `docs/03_testing/RTM-{SystemName}-existing.md` | 現有測試基線 |

---

## 後置動作

```
/adr-generate archaeology           # 逆向挖掘架構決策 ADR
/sa-analyze brownfield              # SA 基於 As-Is SRD 分析 To-Be 需求
/sd-design brownfield               # SD 設計 To-Be 架構
```

🔷 **本 Skill 產出**：Brownfield 場景的 SCG-0/1 前置基線（非通過閘門，而是提供輸入）

---

## 相關 Skill

- `/adr-generate archaeology` — ADR 逆向挖掘（在本 Skill 中呼叫）
- `/contract-generate reverse` — API Contract 逆向（在本 Skill 中呼叫）
- `/sa-analyze brownfield` — 需求分析（本 Skill 完成後接棒）
- `/refactoring-code-quality` — 代碼重構（依 Tech Debt Spec 執行）

---

**基於**: AISDLC-SDD v0.01
**對應場景**: `scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md`
