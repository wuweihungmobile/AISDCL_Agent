# AISDLC-SDD v0.01 Release Notes

**發布日期**: 2026-04-16
**基於**: AISDLC v0.09
**類型**: 初始版本（Major Redesign）

---

## 🎯 版本定位

AISDLC-SDD v0.01 是 AISDLC v0.09 的全面改版，引入 **Spec-First Design（規格先行）** 三大支柱，確保軟體開發過程中規格先於實作。

---

## ✨ 新增功能

### SDD 三大支柱
- **Spec-First Gate（SCG）**：7 個閘門（SCG-0~6）確保規格先行
- **Design-as-Doc**：所有技術決策必須有 ADR；架構必須有 C4 圖
- **Contract-Driven**：OpenAPI 3.1 Contract Freeze（SCG-3）後才允許後端實作

### 新增 SDD 專屬 Skills（6 個）
- `adr-generate` — ADR 自動生成
- `contract-generate` — OpenAPI 3.1 Contract 生成
- `rtm-generate` — 需求追蹤矩陣生成
- `sdd-gate` — SCG 閘門驗證
- `sdd-review` — SDD 規格審查
- `spec-compliance-check` — 規格合規性檢查

### 10 個場景 SDD Enhancement
每個場景都有對應的 SDD Enhancement 文件，說明如何將 SCG 閘門整合到現有流程。

### SDD 文件模板（51 個）
新增 `docs_template/sdd/` 目錄，包含 51 個 SDD 專屬模板（48 .md + 3 .yaml）涵蓋 PRD/FRD/SRD/C4/ADR/RTM/API 等所有文件類型。

### SDD CI/CD 規格（9 個）
- `SDD_CICD_BASE_LAYER.md` — 通用基底層
- `SDD_GREENFIELD_CICD.md` — Greenfield 場景
- `SDD_BROWNFIELD_CICD.md` — Brownfield 場景
- `SDD_REFACTORING_CICD.md` — Refactoring 場景
- `SDD_TESTING_CICD.md`（含 SCG-4 Check）
- `SDD_PERFORMANCE_CICD.md`（含 PBS Gate）
- `SDD_SECURITY_CICD.md`（含 STRIDE Validate）
- `SDD_MIGRATION_CICD.md`（含 MCM Validate）
- `SDD_INTEGRATION_CICD.md`（含 Consumer Contract）

---

## 📊 改善項目（vs v0.09）

| 類別 | v0.09 | v0.01 SDD | 改善 |
|------|-------|-----------|------|
| Skills | 36 | 39 | +6 SDD 專屬（含 sdd-review） |
| 文件模板 | ~50 | ~101 | +51 SDD 專屬（48 md + 3 yaml） |
| CI/CD 規格 | 0 | 9 | 全新（1 基底 + 8 場景） |
| SCG 閘門 | 0 | 7 | 全新 |
| Scenarios | 10 | 10 + 跨場景指南 | 補充指南 |
| Prompts | 有 | 有（SDD 版） | 全面更新 |

---

## ⚠️ 破壞性變更

- **工作流程改變**：所有開發流程必須通過 SCG 閘門，不可跳過
- **文件路徑改變**：專案文件必須輸出到 `AISDLC_SDD_v0.01/docs/` 下
- **API 設計順序改變**：OpenAPI 規格必須在 SCG-3 凍結前完成，後端實作在此之後才可開始

---

## 🔄 從 v0.09 升版指引

1. 閱讀 `SDD_Core_Principles.md` 了解三大支柱
2. 閱讀 `AISDLC_SDD_INIT.md` 了解框架初始化
3. 選擇對應場景的 `SDD_[SCENARIO]_ENHANCEMENT.md`
4. 在現有流程中加入 SCG 閘門確認點

---

**發布日期**: 2026-04-16
**框架維護者**: AISDLC-SDD Framework Team
