# 專案規模化調整指引（SDD 版）
# Project Scaling Guide — SDD Edition

**框架版本**: AISDLC-SDD v0.01
**基於**: AISDLC-SDD v0.01 SCALING_GUIDE
**最後更新**: 2026-04-15
**文檔目的**: 提供 AISDLC-SDD 框架在不同專案規模下的調整建議，特別是 SDD 規格深度的調整

---

## 規模化原則（SDD 新增）

> **核心原則**: SDD 的 SCG 閘門在所有規模下都必須執行，但**規格文件的深度和粒度**可依規模調整。

| 規則 | 說明 |
|------|------|
| 閘門不可跳過 | 無論規模大小，SCG 閘門都必須通過才能進入下一階段 |
| 規格深度可調 | 小型專案可使用輕量規格，大型專案使用完整規格 |
| Invariants 必須提取 | 所有規模的 Refactoring/Migration 都必須提取 Business Invariants |
| RTM 覆蓋率不妥協 | SCG-5 的 100% 覆蓋要求不因規模縮水 |

---

## 專案規模定義

| 規模 | 團隊人數 | 時程 | 代碼量 | 功能複雜度 | 範例 |
|-----|---------|------|--------|-----------|------|
| **🟢 小型** | 1-3 人 | 1-3 個月 | < 5 萬行 | 簡單 | MVP、工具型 App、內部管理系統 |
| **🟡 中型** | 4-10 人 | 3-12 個月 | 5-50 萬行 | 中等 | 完整商業應用、SaaS 產品 |
| **🔴 大型** | 10-50 人 | 12+ 個月 | 50-500 萬行 | 複雜 | 企業級系統、大型平台 |
| **⚫ 超大型** | 50+ 人 | 多年 | 500 萬+ 行 | 極複雜 | 國際級平台、作業系統 |

---

## SDD 規格深度調整矩陣

### 🟢 小型專案 — 輕量 SDD

| 規格類型 | 輕量版 | 是否必須 |
|---------|-------|---------|
| PRD | 1 頁精簡版 | ✅ 必須 |
| FRD | User Stories（無完整 FRD） | ✅ 必須 |
| SRD | 架構說明（1-2 頁） | ✅ 必須 |
| C4 Model | Context + Container（省略 Component） | ✅ 必須（前兩層）|
| ADR | 每個重要決策 1 個 ADR | ✅ 必須（核心決策）|
| OpenAPI | 完整 API 規格 | ✅ 必須 |
| RTM | 精簡 RTM（US → TC 對應） | ✅ 必須 |
| Invariants | 核心業務不變量 | ✅ 必須（Refactoring/Migration）|

**SCG 閘門**: 全部執行，但驗證標準為「輕量版通過」

**適用 Skills**: `sdd-gate`、`rtm-generate`（快速模式）

---

### 🟡 中型專案 — 標準 SDD（框架預設）

| 規格類型 | 標準版 | 是否必須 |
|---------|-------|---------|
| PRD | 完整 PRD（含 NFR） | ✅ 必須 |
| FRD | 完整 FRD + User Stories | ✅ 必須 |
| SRD | 完整 SRD（含序列圖） | ✅ 必須 |
| C4 Model | Context + Container + Component | ✅ 必須 |
| ADR | 所有架構決策 ADR | ✅ 必須 |
| OpenAPI | 完整 OpenAPI 3.1 + Error Codes | ✅ 必須 |
| RTM | 完整 RTM（F-XXX → US-XXX → TC-XXX）| ✅ 必須 |
| Invariants | 所有業務不變量（INV-XXX）| ✅ 必須（Refactoring/Migration）|
| Contract Tests | Consumer Contract + Provider Test | ✅ 必須（Integration/Migration）|

**SCG 閘門**: 全部執行，使用完整標準

---

### 🔴 大型專案 — 完整 SDD

在中型基礎上額外增加：

| 額外規格 | 說明 |
|---------|------|
| 模組化 PRD | 每個功能模組獨立 FRD |
| ADR Index | 維護 ADR 索引（ADR-INDEX.md）|
| Trust Boundary Map | 明確定義系統信任邊界 |
| PBS（Performance Baseline Spec）| 所有效能目標文件化 |
| STRIDE Threat Model | 每個服務獨立威脅模型 |
| Migration Contract Map | 跨系統合約對應表 |
| 多層 RTM | F-XXX → US-XXX → API-XXX → TC-XXX |

**SCG 閘門**: 分模組執行，每個模組獨立通過

**建議工具**: `adr-generate`（自動生成 ADR）、`contract-generate`（Contract Map）

---

### ⚫ 超大型專案 — Enterprise SDD

| 額外考量 | 建議方案 |
|---------|---------|
| 規格版本管理 | ADR 版本化（ADR-NNN-v2） |
| 跨團隊規格同步 | Consumer Contract 跨服務治理 |
| 規格審查委員會 | SCG 閘門需委員會投票通過 |
| 自動化 RTM 更新 | CI/CD 整合 rtm-generate |
| Living Documentation | 文件與代碼同步（CI/CD 觸發更新）|

---

## 各情境規模調整建議

### Greenfield 規模調整

| 規模 | SCG 閘門頻率 | ADR 數量 | C4 層次 |
|-----|------------|---------|---------|
| 小型 | SCG-0, SCG-3, SCG-6 | 3-5 個 | 2 層 |
| 中型 | SCG-0 ~ SCG-6 全套 | 10-20 個 | 3 層 |
| 大型 | SCG-0 ~ SCG-6 + 模組 SCG | 20+ 個 | 4 層 |

### Brownfield 規模調整

| 規模 | 逆向規格深度 | Tech Debt 規格化 |
|-----|------------|----------------|
| 小型 | 核心模組 As-Is SRD | 重點 Tech Debt（TD-XXX Top 5）|
| 中型 | 完整 As-Is SRD + Gap Analysis | 完整 Tech Debt Spec |
| 大型 | 分模組 As-Is SRD | 分優先級 Tech Debt 路線圖 |

### Refactoring 規模調整

| 規模 | Invariants 數量 | INV Gate 嚴格度 |
|-----|---------------|----------------|
| 小型 | 核心 Invariants（3-5 個）| 輕量驗證 |
| 中型 | 完整 Invariants（10-20 個）| 標準驗證 |
| 大型 | 分層 Invariants（Business + Technical）| 嚴格驗證 + 自動化 |

---

## 時程調整係數

以中型專案為基準（1.0x）：

| 規模 | SDD 規格時間係數 | SDD 閘門時間係數 | 整體建議 |
|-----|--------------|--------------|---------|
| 小型 | 0.3x | 0.5x | 規格精簡但閘門仍需執行 |
| 中型 | 1.0x | 1.0x | 框架預設標準 |
| 大型 | 2.0x | 1.5x | 規格分模組，閘門並行執行 |
| 超大型 | 3.0x+ | 2.0x | 需要專責規格管理人員 |

> **提示**: SDD 規格時間在初期看似增加成本，但可顯著減少後期返工和實作錯誤。

---

## 規模升級時的 SDD 調整

當專案規模從小型升級為中型時：

```
1. 將輕量 PRD 擴展為完整 PRD（補充 NFR）
2. 補充缺失的 C4 Component 層
3. 補充所有架構決策的 ADR
4. 執行完整 RTM（補充缺失的追蹤關係）
5. 重新執行 sdd-gate 驗證（確保升級後仍通過）
6. 🔴 人工確認規格升級完成
```

---

## 相關文檔

- `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` — SCG 閘門標準
- `docs_template/sdd/` — 各層次的規格模板
- `guides/system/sdd/SDD_GUIDE.md` — SDD 快速指引
- `scenarios/SCENARIO_AGENT_MAPPING.md` — 各情境 Agent 配置

---

**維護者**: AISDLC-SDD Framework Team
**SDD 版本**: v0.01
**最後更新**: 2026-04-15
