# AISDLC-SDD v0.01 五分鐘快速開始

**版本**: v0.01
**目標**: 5 分鐘內體驗 AISDLC-SDD Spec-First 核心流程
**最後更新**: 2026-04-15

---

## 🎯 快速體驗路徑

### 第 1 分鐘：初始化框架

```
請載入 AISDLC-SDD v0.01 框架。

執行指令：
請閱讀並載入 AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md

我想體驗 AISDLC-SDD 的 Spec-First 開發流程。
```

### 第 2 分鐘：選擇情境

三選一快速體驗：

#### 選項 A：體驗 Greenfield（Spec-First 全新專案）
```
我想開發一個簡單的待辦事項 Web App，使用 SDD Spec-First 流程。

功能需求：
- 用戶可以新增、編輯、刪除待辦事項
- 待辦事項可以標記完成/未完成
- 需要用戶登入功能

請使用 Greenfield 情境，執行 SCG-0 閘門驗證，從 PRD 規格開始。
```

#### 選項 B：體驗 Brownfield（逆向規格工程）
```
我有一個既有的用戶管理系統，需要逆向建立規格文件。

請使用 Brownfield 情境：
1. 分析既有系統建立 As-Is SRD
2. 提取 Business Invariants
3. 執行 Gap Analysis
```

#### 選項 C：體驗 Refactoring（Invariant 保護重構）
```
我有一個訂單處理模組需要重構。

請使用 Refactoring 情境：
1. 識別 Business Invariants（INV-001~）
2. 建立 Invariant Test Contract
3. 規劃 Strangler Fig 策略
```

### 第 3-4 分鐘：執行 Spec-First Workflow

**框架會自動**：
1. ✅ 載入對應情境的 SDD Enhancement
2. ✅ 啟動相關 Agents（SA/SD/QA 等）
3. ✅ 執行 SCG 閘門驗證（規格優先）
4. ✅ 產出規格文檔（PRD/FRD/SRD）

**你只需要**：
- 在 🔴 確認點回應「是」或提供補充資訊
- 通過 SCG 閘門後才進入下一階段（Spec-First 原則）

### 第 5 分鐘：查看成果

**你會得到**：
- 📄 規格文檔（PRD/FRD 通過 SCG-0）
- 🏗️ 架構設計（SRD + C4 + ADR 通過 SCG-1~2）
- 📋 API Contract（OpenAPI 3.1 通過 SCG-3）
- ✅ RTM 需求追蹤矩陣

---

## 💡 SDD 三大支柱提醒

| 支柱 | 說明 | 對應指令 |
|------|------|---------|
| **Spec-First Gate** | 規格先於實作 | 每個 SCG 閘門通過後才繼續 |
| **Design-as-Doc** | ADR 記錄每個技術決策 | `請生成 ADR：[決策描述]` |
| **Contract-Driven** | OpenAPI 凍結後才實作 | 等 SCG-3 通過後才寫後端 |

---

## 🚀 立即開始

```
請載入 AISDLC-SDD v0.01 框架。

執行指令：請閱讀並載入 AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md

我想體驗 SDD Spec-First 流程，請提供 5 分鐘快速體驗。
```

---

**版本**: v0.01（AISDLC-SDD）
**最後更新**: 2026-04-15
