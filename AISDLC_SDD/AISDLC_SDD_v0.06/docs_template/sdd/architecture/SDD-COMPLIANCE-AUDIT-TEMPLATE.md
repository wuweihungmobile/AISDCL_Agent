# SDD 符合度審計報告
# SDD Compliance Audit Report

**專案**: {PROJECT_NAME}
**審計日期**: YYYY-MM-DD
**審計者**: {technical-writer} + {sa-analyst}
**文件版本**: v1.0
**適用情境**: Documentation

---

## 審計說明

本報告依據 SDD 三大核心支柱，審計現有文件的符合程度：

1. **Spec-First Gate**：規格是否先於實作
2. **Design-as-Doc**：架構設計是否文件化
3. **Contract-Driven**：API 是否有 Contract 規格

---

## 1. Spec-First Gate 符合度

### 1.1 規格文件存在性

| 文件類型 | 預期位置 | 存在？ | 符合 SDD？ | 缺口說明 |
|---------|---------|-------|----------|---------|
| PRD | `docs/01_requirements/` | ✅/❌ | ✅/⚠️/❌ | |
| FRD | `docs/01_requirements/` | ✅/❌ | ✅/⚠️/❌ | |
| SRD | `docs/02_architecture/` | ✅/❌ | ✅/⚠️/❌ | |
| API Spec | `docs/02_architecture/api/` | ✅/❌ | ✅/⚠️/❌ | |
| RTM | `docs/03_testing/` | ✅/❌ | ✅/⚠️/❌ | |
| Test Plan | `docs/03_testing/` | ✅/❌ | ✅/⚠️/❌ | |

**符合度評分**：___/6 文件存在

### 1.2 規格時序驗證

| 問題 | 回答 | 說明 |
|------|------|------|
| PRD 是否在開發前完成？ | ✅/❌ | |
| FRD 是否在實作前完成？ | ✅/❌ | |
| API Spec 是否在 UI 開發前凍結？ | ✅/❌ | |
| 測試計畫是否在實作前完成？ | ✅/❌ | |

---

## 2. Design-as-Doc 符合度

### 2.1 架構文件檢查

| 項目 | 存在？ | 位置 | 缺口說明 |
|------|-------|------|---------|
| C4 Context 圖（L1） | ✅/❌ | | |
| C4 Container 圖（L2） | ✅/❌ | | |
| ADR 目錄 | ✅/❌ | | |
| ADR 索引（ADR-INDEX.md） | ✅/❌ | | |
| NFR 規格（SLO/SLA） | ✅/❌ | | |

**ADR 清單**（已發現的架構決策）：

| 決策 | ADR 存在？ | ADR 路徑 | 需補充？ |
|------|----------|---------|---------|
| 技術棧選擇 | ✅/❌ | | ✅/❌ |
| 架構模式 | ✅/❌ | | ✅/❌ |
| 部署策略 | ✅/❌ | | ✅/❌ |
| {其他決策} | ✅/❌ | | ✅/❌ |

### 2.2 隱性決策識別

在 SRD/FRD 中發現以下隱性技術決策（需轉化為 ADR）：

1. {決策描述} → 建議 ADR 編號：ADR-{NNN}
2. {決策描述} → 建議 ADR 編號：ADR-{NNN}

---

## 3. Contract-Driven 符合度

### 3.1 API 文件格式

| API 模組 | 現有文件格式 | OpenAPI 格式？ | 需升級？ |
|---------|------------|--------------|---------|
| {Module 1} | Word/Markdown/OpenAPI | ✅/❌ | ✅/❌ |
| {Module 2} | Word/Markdown/OpenAPI | ✅/❌ | ✅/❌ |

### 3.2 測試契約

| 功能 | Test Contract 存在？ | 位置 | 需補充？ |
|------|-------------------|------|---------|
| {Feature 1} | ✅/❌ | | ✅/❌ |

---

## 4. 缺口總結與修補優先級

### 高優先級（P0）- 必須立即補充
1. {缺口描述} → 負責：{Agent} → 預計完成：{Date}

### 中優先級（P1）- 本 Sprint 補充
1. {缺口描述} → 負責：{Agent} → 預計完成：{Date}

### 低優先級（P2）- 下個版本補充
1. {缺口描述} → 負責：{Agent} → 預計完成：{Date}

---

## 5. 審計結論

**SDD 整體符合度**：___% （高/中/低）

**建議行動**：
- [ ] 優先建立 ADR-INDEX.md
- [ ] 升級 API 文件至 OpenAPI 格式
- [ ] 建立/補充 RTM
- [ ] 建立 Living Documentation 策略

---

**審計者簽字**：
- technical-writer：___________
- sa-analyst：___________
- 確認日期：YYYY-MM-DD

**相關文件**：
- [SDD 核心原則](SDD_Core_Principles.md)
- [ADR 範本](adr/ADR-TEMPLATE.md)
