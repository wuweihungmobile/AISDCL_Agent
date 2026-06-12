---
name: release-management
description: 完整的版本發布流程，包含發布準備、驗證、部署和回滾
user-invocable: true
disable-model-invocation: false
argument-hint: "<version: 版本號 (如 v1.0.0)> [type: 發布類型 (major/minor/patch/hotfix)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Release Management Workflow Skill

完整的版本發布管理流程。

---

## 觸發方式

```bash
/release-management v1.0.0           # 發布 v1.0.0
/release-management v1.0.1 patch     # Patch 發布
/release-management v2.0.0 major     # Major 發布
```

---

## 參與角色

| 角色 | 職責 |
|------|------|
| **PM/PO** | 發布決策、Release Notes 審核 |
| **QA** | 發布驗證、回歸測試 |
| **Dev** | 發布準備、技術支援 |
| **DevOps** | 部署執行、監控 |

---

## 執行流程

### 階段 1: 發布準備 🔴

**檢查清單**:
- [ ] 所有計劃功能已完成
- [ ] 所有 Bug 已修復或延後
- [ ] 代碼凍結執行
- [ ] 版本號確認

**版本號規則 (Semantic Versioning)**:
```
MAJOR.MINOR.PATCH

- MAJOR: 不相容的 API 變更
- MINOR: 新增向下相容的功能
- PATCH: 向下相容的 Bug 修復
```

🔴 **確認點**: 確認發布範圍和版本號

---

### 階段 2: 發布驗證

**QA 驗證清單**:

```markdown
## Release Validation Checklist

### 功能驗證
- [ ] 所有新功能測試通過
- [ ] 回歸測試通過
- [ ] 效能測試通過
- [ ] 安全掃描通過

### 環境驗證
- [ ] Staging 環境驗證
- [ ] 資料庫遷移測試
- [ ] 配置檢查

### 文檔驗證
- [ ] API 文檔更新
- [ ] 用戶手冊更新
- [ ] Release Notes 完成
```

---

### 階段 3: Release Notes

**Release Notes 模板**:

```markdown
# Release Notes - v[X.Y.Z]

**發布日期**: [YYYY-MM-DD]
**發布類型**: [Major/Minor/Patch/Hotfix]

## 新功能 ✨
- [功能1描述] (#Issue-ID)
- [功能2描述] (#Issue-ID)

## 改進 🚀
- [改進1描述]
- [改進2描述]

## Bug 修復 🐛
- [修復1描述] (#Issue-ID)
- [修復2描述] (#Issue-ID)

## 重大變更 ⚠️
- [變更描述和遷移指南]

## 已知問題
- [問題描述] - 預計 v[X.Y.Z] 修復

## 升級指南
1. [步驟1]
2. [步驟2]

## 貢獻者
- @[contributor1]
- @[contributor2]
```

---

### 階段 4: 部署準備 🔴

**部署檢查**:

```markdown
## Pre-Deployment Checklist

### 代碼準備
- [ ] Release branch 已建立
- [ ] 版本號已更新 (package.json, etc.)
- [ ] CHANGELOG 已更新
- [ ] Git tag 已建立

### 環境準備
- [ ] 環境變數配置確認
- [ ] 資料庫遷移腳本準備
- [ ] 回滾腳本準備
- [ ] 監控告警配置

### 通知準備
- [ ] 團隊通知
- [ ] 客戶通知 (如需要)
- [ ] 維護公告 (如需要)
```

🔴 **確認點**: 確認部署準備完成

---

### 階段 5: 部署執行

**部署流程**:

```bash
# 1. 建立 Release Tag
git tag -a v[X.Y.Z] -m "Release v[X.Y.Z]"
git push origin v[X.Y.Z]

# 2. 觸發部署 (CI/CD)
# - GitHub Actions / GitLab CI 自動觸發
# - 或手動執行部署腳本

# 3. 驗證部署
curl -s https://api.example.com/health
```

**部署順序**:
1. 🔵 Staging 環境
2. 🟡 Pre-Production 環境
3. 🟢 Production 環境 (分批/金絲雀)

---

### 階段 6: 發布驗證 🔴

**Post-Deployment Checklist**:

```markdown
## Post-Deployment Verification

### 服務健康
- [ ] 所有服務啟動正常
- [ ] 健康檢查端點回應正常
- [ ] 無錯誤日誌

### 功能驗證
- [ ] 核心功能煙霧測試
- [ ] 關鍵業務流程驗證
- [ ] 第三方整合驗證

### 效能監控
- [ ] 回應時間正常
- [ ] 錯誤率正常
- [ ] 資源使用正常
```

🔴 **確認點**: 確認發布成功

---

### 階段 7: 回滾計劃

**回滾決策**:

```markdown
## Rollback Criteria

### 自動回滾
- 錯誤率 > 5%
- P99 延遲 > 5s
- 核心功能失敗

### 手動回滾
- 業務決策
- 重大 Bug 發現
```

**回滾步驟**:

```bash
# 1. 確認回滾決策
# 2. 執行回滾
git checkout v[PREVIOUS]
# 或觸發 CI/CD 回滾

# 3. 驗證回滾
curl -s https://api.example.com/health

# 4. 通知團隊
# 5. 記錄回滾原因
```

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Release Notes | `docs/08_deployment/RELEASE_NOTES_v[X.Y.Z].md` |
| 部署清單 | `docs/08_deployment/DEPLOYMENT_CHECKLIST.md` |
| 回滾計劃 | `docs/08_deployment/ROLLBACK_PLAN.md` |

---

## 相關 Skill

- `/devops-github` - GitHub Actions CI/CD
- `/devops-k8s` - Kubernetes 部署
- `/sprint-planning` - Sprint 規劃

---


## 相關檔案

- Workflow 定義: `workflow/scenario-specific/`

**基於**: AISDLC v0.09 Workflow
