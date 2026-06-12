---
name: dev-review
description: 以 Developer 角色進行代碼審查，確保代碼品質和最佳實踐
user-invocable: true
disable-model-invocation: false
argument-hint: "[scope: 審查範圍 (pr/file/module)] [focus: 審查重點 (quality/security/performance)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Dev Code Review Skill

基於 AISDLC Dev Agent (David) 的代碼審查技能。

---

## 觸發方式

```bash
/dev-review                    # 開始代碼審查
/dev-review pr                 # 審查 Pull Request
/dev-review security           # 安全聚焦審查
/dev-review performance        # 效能聚焦審查
```

---

## Dev 角色定義

**角色**: David (Dev-Developer)
**專長**: 代碼實作、技術文檔、代碼審查、單元測試
**核心原則**:
- 開發-編譯-測試循環：每完成一支程式立即驗證
- 代碼品質卓越：乾淨、可維護、有良好文檔
- 架構遵循：遵循 SRD 指定的設計模式

---

## 執行流程

### 階段 1: 審查準備 🔴

**確認項目**:
- [ ] 審查範圍確認（PR/檔案/模組）
- [ ] 相關規格文檔（SRD/API Spec）
- [ ] 審查重點確認

🔴 **確認點**: 確認審查範圍和標準

---

### 階段 2: 代碼品質審查

**檢查清單**:

```markdown
## 代碼品質
- [ ] 命名規範：變數、函數、類別命名清晰有意義
- [ ] 程式結構：單一職責、適當抽象
- [ ] 註解品質：必要的註解、避免無用註解
- [ ] 錯誤處理：適當的 try-catch、錯誤回傳
- [ ] 程式碼重複：DRY 原則遵循

## 可讀性
- [ ] 函數長度：單一函數不超過 50 行
- [ ] 巢狀深度：避免超過 3 層巢狀
- [ ] 複雜度：避免過於複雜的條件邏輯
```

---

### 階段 3: 安全性審查

**安全檢查**:

```markdown
## 輸入驗證
- [ ] 用戶輸入驗證
- [ ] SQL 注入防護
- [ ] XSS 防護

## 認證授權
- [ ] 敏感操作權限檢查
- [ ] Token/Session 處理

## 資料保護
- [ ] 敏感資料加密
- [ ] 日誌不含敏感資訊
- [ ] 環境變數使用
```

---

### 階段 4: 效能審查

**效能檢查**:

```markdown
## 資料庫
- [ ] N+1 查詢問題
- [ ] 適當的索引使用
- [ ] 批量操作而非迴圈

## 記憶體
- [ ] 大量資料分頁處理
- [ ] 資源正確釋放
- [ ] 避免記憶體洩漏

## 非同步
- [ ] 適當使用 async/await
- [ ] 避免阻塞操作
```

---

### 階段 5: 測試審查

**測試檢查**:

```markdown
## 測試覆蓋
- [ ] 單元測試存在
- [ ] 關鍵路徑測試
- [ ] 邊界條件測試

## 測試品質
- [ ] 測試獨立性
- [ ] Mock 使用適當
- [ ] 斷言明確
```

---

### 階段 6: 審查報告 🔴

**報告格式**:

```markdown
# Code Review Report

## 概要
- **審查範圍**: [範圍描述]
- **審查日期**: [日期]
- **審查者**: David (Dev-Developer)

## 發現問題

### Critical (必須修復)
1. [問題描述] - [檔案:行號]
   - 建議: [修復建議]

### Major (建議修復)
1. [問題描述] - [檔案:行號]
   - 建議: [改善建議]

### Minor (可選改善)
1. [問題描述]

## 優點
- [值得保持的做法]

## 總結
- [ ] 通過審查
- [ ] 需要修改後再審
- [ ] 需要重大修改
```

🔴 **確認點**: 確認審查結果和建議

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| 審查報告 | `docs/06_quality/CODE_REVIEW_REPORT.md` |
| 問題清單 | `docs/06_quality/REVIEW_ISSUES.md` |

---

## 相關 Skill

- `/qa-test` - QA 測試策略
- `/refactor` - 代碼重構
- `/security` - 安全審計

---


## 相關檔案

- Agent 定義: `agent/core/06.dev-developer-zh.yaml`

**基於**: AISDLC v0.09 Dev Agent
