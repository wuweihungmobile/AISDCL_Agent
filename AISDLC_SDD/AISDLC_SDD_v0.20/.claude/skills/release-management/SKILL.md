---
name: release-management
description: 執行完整版本發布流程，驗證 SCG-6 發布閘門條件，產出 Release Notes 和 Runbook，執行部署與回滾
user-invocable: true
disable-model-invocation: false
argument-hint: "<version: 版本號 如 v1.0.0> [type: major|minor|patch|hotfix]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Release Management Workflow Skill（SDD 原生）

發布是 SDD 生命週期的最後一道閘門（SCG-6）。本 Skill 確保所有 SCG-0~5 已通過，產出符合 SDD 格式的 Release Notes，並執行部署驗證。未通過 SCG-6 的版本不可發布。

---

## 觸發方式

```bash
/release-management v1.0.0           # 發布 v1.0.0
/release-management v1.0.1 patch     # Patch 版本
/release-management v2.0.0 major     # Major 版本（需 API-COMPAT 聲明）
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-5 通過 | RTM 100% 覆蓋，所有測試通過 | `/sdd-gate SCG-5` 報告存在 |
| RTM 覆蓋率 100% | `/rtm-generate verify` 通過 | `docs/03_testing/RTM-{System}.md` |
| 無 P1 未修復缺陷 | 所有 Critical 問題已關閉 | Code Review 報告 |

---

## 執行流程

### 階段 1：SCG-6 發布閘門驗證 🔴

執行 `/sdd-gate SCG-6` 並逐一確認：

```markdown
## SCG-6 發布閘門驗證清單

### SCG-0~5 追蹤
- [ ] SCG-0 通過（文件：docs/03_testing/SCG-0-REPORT-{System}.md）
- [ ] SCG-1 通過（文件：docs/03_testing/SCG-1-REPORT-{System}.md）
- [ ] SCG-2 通過（文件：docs/03_testing/SCG-2-REPORT-{System}.md）
- [ ] SCG-3 通過（文件：docs/03_testing/SCG-3-REPORT-{System}.md）
- [ ] SCG-4 通過（文件：docs/03_testing/SCG-4-REPORT-{System}.md）
- [ ] SCG-5 通過（文件：docs/03_testing/SCG-5-REPORT-{System}.md）

### 發布文件
- [ ] Release Notes 已撰寫（SDD 格式）
- [ ] Runbook 已完成
- [ ] 回滾計畫就緒
- [ ] API 相容性聲明（Major 版本必填：API-COMPAT-*.md）

### 技術驗證
- [ ] 所有 Contract Testing 通過（對照凍結 Contract）
- [ ] RTM 覆蓋率 = 100%（/rtm-generate verify 通過）
- [ ] STRIDE 威脅模型已執行（Security 情境）
- [ ] 效能基準（PBS）通過（Performance 情境）
```

🔴 確認點：SCG-6 需由授權人員明確確認後才繼續。

---

### 階段 2：Release Notes 產出（SDD 格式）

**文件路徑**：`docs/08_deployment/RELEASE-NOTES-{version}.md`

```markdown
# Release Notes — {version}

**發布日期**: {YYYY-MM-DD}
**版本類型**: Major / Minor / Patch / Hotfix
**SCG-6 通過日期**: {YYYY-MM-DD}

## 本版本功能（對應 FRD 追溯）

| 功能 | FRD Feature | US-ID | 描述 |
|------|------------|-------|------|
| {功能名稱} | F-{NNN} | US-{NNN} | {業務說明} |

## 改進
- {改進說明}（F-{NNN}）

## Bug 修復
- {修復說明}（TC-{NNN} 已通過）

## 重大變更（Breaking Changes）
> Major 版本必填，Minor/Patch 若無則省略

| 變更 | 影響 | 遷移指南 | API-COMPAT 文件 |
|------|------|---------|---------------|
| {端點 X 廢棄} | {影響} | {步驟} | API-COMPAT-{Module}.md |

## 已知問題
- {問題描述}（預計 {version+1} 修復）

## 升級指南
1. {步驟}

## RTM 覆蓋率
- 本版本 AC 覆蓋率: 100%（/rtm-generate verify 確認）
```

---

### 階段 3：Runbook 產出

**文件路徑**：`docs/08_deployment/RUNBOOK-{version}.md`

```markdown
# Runbook — {version}

## 前置作業
1. {環境確認步驟}
2. {資料庫 migration 確認}

## 部署步驟
1. 🔵 Staging 部署驗證
2. 🟡 Pre-Production（若有）
3. 🟢 Production（金絲雀 / 全量）

## 部署驗證
- [ ] 健康檢查端點正常
- [ ] 核心業務流程冒煙測試
- [ ] 監控指標正常（對照 NFR-XXX 基線）

## 回滾計畫
### 自動回滾條件
- 錯誤率 > 5%（超過 NFR-XXX 定義閾值）
- P99 延遲 > {NFR 定義值}（超過 SLA）

### 手動回滾步驟
1. {步驟}
```

---

### 階段 4：部署執行 🔴

部署順序：
1. 執行 `/sdd-gate SCG-6`（正式確認）
2. 建立 Git Release Tag
3. 觸發 CI/CD Pipeline（`/devops-github-actions` 或 `/devops-gitlab-ci`）
4. 按 Runbook 執行驗證

🔴 確認點：Production 部署必須由授權人員執行，非自動化直接部署。

---

### 階段 5：發布後驗證

```markdown
## Post-Release 驗證清單

- [ ] 所有服務健康檢查通過
- [ ] 核心 Contract 端點回應符合規格
- [ ] 監控告警無異常（對照 NFR 閾值）
- [ ] RTM 全部 ✅（無 🔄 或 ❌）
```

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Release Notes | `docs/08_deployment/RELEASE-NOTES-{version}.md` | SCG-6 |
| Runbook | `docs/08_deployment/RUNBOOK-{version}.md` | SCG-6 |
| API-COMPAT（Major 版本） | `docs/02_architecture/api/API-COMPAT-{Module}.md` | SCG-6 前 |

---

## 後置動作

```
/sdd-gate SCG-6    # 正式執行發布閘門
```

🔷 **本 Skill 協助通過**：SCG-6（Release Gate）

---

## 相關 Skill

- `/sdd-gate SCG-6` — 發布閘門（本 Skill 的核心觸發點）
- `/rtm-generate verify` — RTM 100% 確認（發布前最後檢查）
- `/devops-github-actions` / `/devops-gitlab-ci` — CI/CD 執行
- `/contract-generate compat` — Major 版本 API 相容性聲明

---

**基於**: AISDLC-SDD v0.20
**對應工作流**: `workflow/scenario-specific/`
**對應 CI/CD 規格**: `cicd/SDD_TESTING_CICD.md`
