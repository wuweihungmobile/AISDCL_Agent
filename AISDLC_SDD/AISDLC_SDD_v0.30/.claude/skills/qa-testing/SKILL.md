---
name: qa-testing
description: 以 QA Engineer 角色制定測試策略，產出測試計畫和測試案例，更新 RTM 並準備 SCG-4/SCG-5 閘門
user-invocable: true
disable-model-invocation: false
argument-hint: "[test_type: full|unit|integration|e2e|contract|acceptance] [scope: feature|module|regression|release]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# QA 測試策略 Skill（SDD 原生）

QA 在 SDD 工作流中負責從 Contract 凍結（SCG-3）後制定測試策略，確保每個 AC 都有對應的 TC，RTM 達到 100% 覆蓋率（SCG-5 條件）。Contract Testing 是本 Skill 的核心新增能力。

---

## 觸發方式

```bash
/qa-testing                           # 完整測試策略（SCG-3 通過後）
/qa-testing acceptance                # 驗收測試設計（從 AC 產出 TC）
/qa-testing contract                  # Contract Testing（從 OpenAPI 產出）
/qa-testing integration               # 整合測試規劃
/qa-testing e2e                       # 端到端測試
/qa-testing regression                # 回歸測試計畫
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-3 通過 | API Contract 已凍結 | `/sdd-gate SCG-3` 報告存在 |
| FRD 存在 | 驗收標準（AC-XXX-Y）已定義 | `docs/01_requirements/FRD-{System}.md` |
| RTM 初版存在 | SA 已建立 RTM 初版 | `docs/03_testing/RTM-{System}.md` |

---

## 執行流程

### 階段 1：前置讀取與可測試性分析

讀取：
- `docs/01_requirements/FRD-{SystemName}.md`（AC-XXX-Y 清單）
- `docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml`（Contract Testing 依據）
- `docs/03_testing/RTM-{SystemName}.md`（確認哪些 AC 尚未有 TC）

可測試性評估：
```markdown
## 可測試性分析

- [ ] 每個 AC 都有明確 Given-When-Then 格式
- [ ] 驗收標準可量化或可觀察（非模糊描述）
- [ ] 邊界條件已在 AC 中定義
- [ ] NFR 測試基準（P99/並發量）已量化

### 測試風險識別
| 風險 | 等級 | 緩解措施 |
|------|------|---------|
| {風險} | 高/中/低 | {措施} |
```

🔴 確認點：不可測試的 AC 必須退回 SA 修改。

---

### 階段 2：測試策略（Test Pyramid Spec）設計

**文件路徑**：`docs/03_testing/TEST-STRATEGY-{SystemName}.md`

```markdown
# Test Strategy Spec — {SystemName}

## 測試金字塔分層

| 層級 | 類型 | 目標覆蓋率 | 執行方式 |
|------|------|-----------|---------|
| L1 | 單元測試（Unit） | ≥ 80% 代碼覆蓋率 | 自動化 |
| L2 | 整合測試（Integration） | 核心業務流程 100% | 自動化 |
| L3 | Contract Testing | 所有 API 端點（SCG-3 Contract） | 自動化 |
| L4 | E2E 測試 | Happy Path + Critical Edge Cases | 自動化 |
| L5 | 驗收測試（AT） | 所有 AC-XXX-Y | 手動/自動化 |

## 測試環境
| 環境 | 用途 | 資料策略 |
|------|------|---------|
| Dev | 單元/整合測試 | Mock |
| Staging | Contract/E2E | 測試資料 |
| UAT | 驗收測試 | 類生產資料（脫敏） |

## 進入/退出條件

### 進入條件（SCG-3 通過後）
- [ ] API Contract 已凍結
- [ ] FRD AC 清單完整
- [ ] 測試環境就緒

### 退出條件（SCG-5 前）
- [ ] RTM 覆蓋率 = 100%
- [ ] 無 P1 未修復缺陷
- [ ] Contract Testing 全部通過
```

---

### 階段 3：Contract Testing 設計（SDD 新增核心）

基於 SCG-3 凍結的 Contract 自動產出 Contract Test Cases：

```markdown
## Contract Test Cases — {Module} API

**來源 Contract**: docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml

| TC-ID | API 端點 | 測試場景 | 對應 AC |
|-------|---------|---------|--------|
| TC-CT-001-1 | POST /{resource} | 正常建立 200 | AC-001-1 |
| TC-CT-001-2 | POST /{resource} | 缺少必填欄位 400 | AC-001-2 |
| TC-CT-001-3 | POST /{resource} | 未認證 401 | NFR-002 |
| TC-CT-001-4 | POST /{resource} | 無權限 403 | NFR-002 |
```

---

### 階段 4：測試案例設計（AC → TC 完整覆蓋）

**文件路徑**：`docs/03_testing/TEST-CASES-{Feature}.md`

```markdown
## TC-{US序號}-{AC序號}-{測試序號}: {測試案例標題}

**優先級**: P1 (Critical) / P2 (High) / P3 (Medium)
**測試類型**: Unit / Integration / Contract / E2E / Acceptance
**對應 AC**: AC-{US序號}-{AC序號}
**對應 API**: API-{NNN}（若適用）
**自動化**: Yes / No / Planned

**前置條件**:
1. {前置條件}

**測試步驟（Given-When-Then）**:
- **Given**: {系統/資料狀態}
- **When**: {使用者/系統動作}
- **Then**: {預期結果，可量化}

**測試資料**:
```json
{
  "input": {},
  "expected": {}
}
```

**後置清理**: {需要清理的資料/狀態}
```

---

### 階段 5：RTM 更新（嵌入流程）🔴

測試案例產出後，立即更新 RTM：

```bash
/rtm-generate update docs/03_testing/TEST-CASES-{Feature}.md
```

RTM 更新後，檢查覆蓋率：

```bash
/rtm-generate verify
```

若覆蓋率 < 100%，必須補充缺失的 TC，不可跳過。

---

### 階段 6：Invariant Test Contract（Refactoring 情境）

若為 Refactoring 場景，需額外產出 Invariant Test Contract：

**文件路徑**：`docs/03_testing/contracts/ITC-{SystemName}.md`

```markdown
# Invariant Test Contract — {SystemName}

## 業務不變量測試保護

| INV-ID | 不變量描述 | 測試覆蓋方式 | TC-ID |
|--------|-----------|-----------|-------|
| INV-001 | {業務約束} | {自動化測試方案} | TC-{NNN}-{N}-1 |
```

---

### 階段 7：文件驗證 🔴

1. 執行 `/spec-compliance-check docs/03_testing/TEST-STRATEGY-{SystemName}.md`
2. 執行 `/rtm-generate verify`（確認覆蓋率達標）
3. 🔴 確認點：測試策略需與 Dev 確認自動化可行性，與 PM 確認發布標準

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Test Strategy Spec | `docs/03_testing/TEST-STRATEGY-{SystemName}.md` | SCG-3 後 |
| Test Cases | `docs/03_testing/TEST-CASES-{Feature}.md` | SCG-4 前 |
| Contract Test Cases | `docs/03_testing/TEST-CASES-CONTRACT-{Module}.md` | SCG-4 前 |
| Invariant Test Contract（Refactoring） | `docs/03_testing/contracts/ITC-{SystemName}.md` | SCG-4 前 |
| RTM（更新至 TC 追溯） | `docs/03_testing/RTM-{SystemName}.md` | SCG-5 前 |

---

## 後置動作

```
/rtm-generate verify               # 確認 RTM 100% 覆蓋
/spec-compliance-check SCG-5       # 驗證 SCG-5 條件
/sdd-gate SCG-5                    # 交付閘門（RTM 100% 後執行）
```

🔷 **本 Skill 協助通過**：SCG-4（Implementation Review）、SCG-5（Delivery Gate）

---

## 相關 Skill

- `/sa-analyst` — 需求分析（AC 來源）
- `/contract-generate` — API Contract（Contract Testing 的依據）
- `/rtm-generate` — RTM 追溯（在本 Skill 中呼叫）
- `/dev-review` — 代碼審查（SCG-4 協同）
- `/sdd-gate SCG-5` — 交付閘門

---

**基於**: AISDLC-SDD v0.30
**對應 Agent**: `07.qa-tester-zh.yaml`
**對應 SDD Enhancement**: `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`
**對應 CI/CD 規格**: `cicd/SDD_TESTING_CICD.md`
