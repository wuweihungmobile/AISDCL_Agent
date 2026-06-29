# 活文件維護策略
# Living Documentation Strategy

**專案**: {PROJECT_NAME}
**版本**: v1.0
**建立日期**: YYYY-MM-DD
**建立者**: technical-writer（`living_documentation` Skill）
**適用情境**: Documentation / 所有情境

---

## 🎯 策略目標

將文件從「事後補充」轉為「規格驅動的持續維護」，確保：
1. 文件與代碼同步更新
2. 版本化文件可回溯
3. 文件健康度可量化

---

## 1. 文件觸發條件定義

### 必須更新文件的觸發事件

| 觸發事件 | 影響文件 | 負責 Agent | 更新時限 |
|---------|---------|-----------|---------|
| User Story 完成實作 | FRD、RTM（AT 欄位） | sa-analyst | 同 Sprint 內 |
| API 介面變更 | OpenAPI Contract | sd-architect | 變更當天 |
| 架構決策變更 | ADR（新增/更新）、SRD | sd-architect | 變更當天 |
| 依賴套件升級 | SRD（技術棧章節）| dev-senior | 升級後 3 天 |
| 安全漏洞修復 | SAD（安全架構文件）| security-engineer | 修復當天 |
| 效能優化 | PBS（效能基準規格）| performance-engineer | 優化後 3 天 |
| 新功能上線 | FRD、RTM、API Contract | sa-analyst | 上線當天 |

---

## 2. 文件版本化策略

### 版本快照規則

```
每個 Sprint 結束：
  - 若有重大文件更新 → 建立版本快照
  - 快照位置：docs/05_development/snapshots/v{version}/

每個正式發布（Release）：
  - 強制建立完整文件快照
  - 位置：docs/08_deployment/releases/{version}/
```

### 版本命名規則

| 文件類型 | 版本格式 | 範例 |
|---------|---------|------|
| FRD | `FRD-{module}-v{N}.md` | `FRD-Auth-v2.md` |
| SRD | `SRD-{system}-v{N}.md` | `SRD-Backend-v3.md` |
| API Contract | `CONTRACT-{module}-v{N}.yaml` | `CONTRACT-User-v2.yaml` |
| RTM | `RTM-{project}-v{N}.md` | `RTM-MyApp-v4.md` |

---

## 3. 文件健康度指標

### Health Score 計算

```
文件健康度 = (現有文件數 / 應有文件數) × 
             (最新文件數 / 現有文件數) × 
             (已驗證文件數 / 最新文件數) × 100%
```

### 健康度目標

| 指標 | 最低目標 | 優秀目標 |
|------|---------|---------|
| RTM 覆蓋率 | ≥ 80% | ≥ 95% |
| API 文件覆蓋率 | 100% | 100% |
| ADR 覆蓋率 | ≥ 90% | 100% |
| 文件更新及時率 | ≥ 85% | ≥ 95% |

---

## 4. 文件-代碼同步驗證

### 4.1 自動驗證（CI Pipeline）

```yaml
doc_sync_validation:
  trigger: "PR merge 時"
  checks:
    - "SpecTrace：RTM 追溯鏈完整性"
    - "API Spec Validation：OpenAPI 語法驗證"
    - "ADR Index Sync：新 ADR 已入索引"
    - "Link Check：文件連結有效"
```

### 4.2 週期性手動審查

| 週期 | 審查內容 | 負責人 |
|------|---------|--------|
| 每 Sprint | ADR 有效性確認 | sd-architect |
| 每月 | RTM 覆蓋率審查 | sa-analyst |
| 每季 | 全文件健康度評估 | technical-writer |
| 每次發布 | 完整 SDD 符合度審計 | technical-writer + sa |

---

## 5. 文件廢棄處理

### 廢棄規則

1. **已廢棄 ADR**：標記狀態為 Deprecated，不刪除，更新 ADR-INDEX
2. **已廢棄 API Contract**：標記 `deprecated: true`，保留至少 2 個版本
3. **已廢棄 Test Contract**：移至 `docs/03_testing/contracts/archive/`
4. **舊版 RTM**：移至 `docs/03_testing/archive/`

---

## 6. 工具與自動化

| 工具 | 用途 | 觸發方式 |
|------|------|---------|
| markdownlint | 文件格式驗證 | CI/CD 自動 |
| markdown-link-check | 連結有效性 | CI/CD 自動 |
| spectral | OpenAPI 規格驗證 | CI/CD 自動 |
| custom SpecTrace script | RTM 完整性 | CI/CD 自動 |
| adr-index-maintenance | ADR 索引同步 | Agent Skill 手動/自動 |

---

**相關文件**：
- [SDD 符合度審計](../02_architecture/SDD-COMPLIANCE-AUDIT-TEMPLATE.md)
- [ADR 索引](../02_architecture/adr/ADR-INDEX.md)
- [SDD 核心原則](../02_architecture/SDD_Core_Principles.md)
