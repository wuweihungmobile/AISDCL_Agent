# Defect Classification Specification — Template
# 缺陷分類規格文件模板
# Phase 05 — Testing 情境 SDD 強化

**文件類型**: Defect Classification Specification (DCS)
**使用時機**: Test Strategy Spec 制定時同步產出
**存放位置**: `docs/03_testing/DEFECT-CLASSIFICATION-SPEC-{project}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **專案名稱** | {ProjectName} |
| **建立日期** | {YYYY-MM-DD} |
| **負責人** | {QA Lead Name} |
| **適用範圍** | 所有環境（Dev / QA / Staging / Prod） |

---

## 1. 嚴重度（Severity）定義

> **SDD 原則**: 嚴重度基於技術影響，與業務優先級無關。

| 嚴重度 | 代碼 | 定義 | 範例 |
|-------|------|------|------|
| **Critical** | SEV-1 | 系統崩潰、資料遺失、安全漏洞、所有使用者無法操作 | 系統當機、SQL Injection、生產資料損毀 |
| **High** | SEV-2 | 主要功能完全失效、無替代方案 | 無法登入、付款失敗、核心 API 錯誤 |
| **Medium** | SEV-3 | 功能降級但仍可用、有替代方案 | 某報表顯示錯誤、非關鍵 UI 異常 |
| **Low** | SEV-4 | 輕微問題，不影響核心功能 | 拼字錯誤、排版問題、次要 UI 瑕疵 |
| **Info** | SEV-5 | 改進建議，非缺陷 | 效能建議、UX 改善建議 |

---

## 2. 優先級（Priority）定義

> **SDD 原則**: 優先級基於業務影響和修復緊迫度，由 QA Lead + PM 共同決定。

| 優先級 | 代碼 | 定義 | 典型 Severity 組合 |
|-------|------|------|-------------------|
| **Urgent** | P0 | 必須立即修復，阻擋當前測試/發布 | SEV-1, SEV-2 in prod |
| **High** | P1 | 必須在當前 Sprint 修復 | SEV-1, SEV-2 |
| **Normal** | P2 | 下個 Sprint 修復 | SEV-3 |
| **Low** | P3 | Backlog，擇機修復 | SEV-4, SEV-5 |

---

## 3. Severity × Priority 決策矩陣

| 嚴重度 ↓ / 環境 → | Dev | QA | Staging | Production |
|-----------------|-----|----|---------|------------|
| Critical (SEV-1) | P1 | P0 | P0 | P0（立即修復） |
| High (SEV-2) | P2 | P1 | P0 | P0 |
| Medium (SEV-3) | P3 | P2 | P1 | P1 |
| Low (SEV-4) | P3 | P3 | P2 | P2 |

---

## 4. 修復 SLA

| 優先級 | 首次回應時間 | 修復時間 | 驗證時間 |
|-------|------------|---------|---------|
| P0 | 30 分鐘 | 4 小時 | 2 小時 |
| P1 | 4 小時 | 24 小時 | 8 小時 |
| P2 | 1 個工作天 | 1 週 | 2 個工作天 |
| P3 | 1 週 | 下個 Sprint | 1 個工作天 |

---

## 5. 缺陷分類標籤（Labels）

### 5.1 缺陷類型

| 標籤 | 說明 |
|-----|------|
| `type:functional` | 功能邏輯錯誤 |
| `type:ui` | 介面顯示問題 |
| `type:performance` | 效能/速度問題 |
| `type:security` | 安全漏洞 |
| `type:data` | 資料錯誤/遺失 |
| `type:integration` | 整合/API 問題 |
| `type:regression` | 回歸問題（舊功能被破壞） |
| `type:environment` | 環境配置問題 |

### 5.2 根本原因分類

| 標籤 | 說明 |
|-----|------|
| `root:requirement` | 需求不明確 |
| `root:design` | 設計缺陷 |
| `root:implementation` | 實作錯誤 |
| `root:config` | 配置錯誤 |
| `root:third-party` | 第三方服務問題 |
| `root:test-data` | 測試資料問題 |
| `root:environment` | 環境差異 |

---

## 6. 缺陷阻擋發布標準

### 6.1 必須修復後才能發布（Blocking）

- [ ] 任何 P0 缺陷
- [ ] 任何 P1 缺陷（標記 `type:security` 或 `type:functional`）
- [ ] Critical + Security 類型缺陷（無論優先級）
- [ ] 任何導致資料遺失的缺陷
- [ ] Contract Test 失敗相關缺陷

### 6.2 可帶缺陷發布（Non-Blocking，需記錄）

- [ ] P2 缺陷（需在 Release Notes 記載已知問題）
- [ ] P3 缺陷
- [ ] `type:ui` 輕微問題（需 PM 確認接受）

---

## 7. 缺陷生命週期

```
New → Assigned → In-Progress → Fixed → In-Verification → Closed
  ↘ Won't Fix（需 PM 批准）
  ↘ Duplicate（標記原始缺陷）
  ↘ Cannot Reproduce（需提供復現步驟後重開）
  ↘ Deferred（需記錄延後理由）
```

---

## 8. 缺陷報告必填欄位

| 欄位 | 說明 | 範例 |
|------|------|------|
| **標題** | 簡短描述問題 | `[SEV-2] 使用者登入後無法取得 JWT token` |
| **Severity** | SEV-1 ~ SEV-5 | SEV-2 |
| **Priority** | P0 ~ P3 | P1 |
| **環境** | 發現的環境 | QA / Staging |
| **版本** | 系統版本 | v1.2.3 |
| **重現步驟** | 完整操作步驟 | 1. 開啟登入頁... |
| **預期結果** | 正確行為 | 應回傳 JWT token |
| **實際結果** | 錯誤行為 | 回傳 null |
| **截圖/Log** | 證據 | 附件或 Log 路徑 |
| **標籤** | 類型標籤 | `type:functional`, `root:implementation` |
| **AT 連結** | 對應的 AT ID | AT-{NNN}-{Y}-{Z} |

---

## 9. 缺陷趨勢追蹤指標

| 指標 | 說明 | 目標 |
|------|------|------|
| 缺陷密度 | 缺陷數 / KLOC | < {N}/KLOC |
| 缺陷逃逸率 | 生產缺陷 / 總缺陷 | < 5% |
| P0/P1 平均修復時間 | SLA 達成率 | > 95% |
| 缺陷重開率 | 重開缺陷 / 已關閉缺陷 | < 10% |
| Contract 缺陷占比 | Contract 相關缺陷 / 總缺陷 | → 0%（目標消除） |
