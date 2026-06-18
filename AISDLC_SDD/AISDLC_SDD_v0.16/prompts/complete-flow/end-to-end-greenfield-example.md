# AISDLC-SDD v0.01 Greenfield 端到端完整範例

**版本**: v0.01（SDD 版）
**範例專案**: 任務管理 Web App（TaskMaster）
**SDD 流程**: Spec-First → SCG-0~6 全流程
**最後更新**: 2026-04-15

---

## 📋 專案背景

一家新創公司使用 **SDD Spec-First** 流程開發任務管理 Web App。

### 核心功能
- 用戶註冊/登入
- 任務 CRUD（含優先級、截止日期）
- 任務狀態管理與篩選

### NFR（Non-Functional Requirements）
- 回應時間 < 1 秒（P95）
- 支援 100 並發用戶
- 符合 OWASP Top 10

---

## 🚀 SDD 完整執行流程

### 步驟 1：框架初始化

```
請載入 AISDLC-SDD v0.01 框架。
執行：請閱讀並載入 AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md

專案：TaskMaster - 任務管理 Web App
情境：Greenfield（全新 Spec-First 開發）
```

---

### 步驟 2：需求分析 → SCG-0（需求凍結）

```
請 SA 分析師開始需求分析。

業務目標：幫助小型團隊（5-20人）協作管理任務
核心功能需求：
- F-001：用戶可以註冊和登入
- F-002：用戶可以創建/編輯/刪除任務
- F-003：任務可以設定優先級（高/中/低）
- F-004：任務可以設定截止日期
- F-005：用戶可以標記任務完成
- F-006：用戶可以按狀態/優先級篩選任務

NFR：
- NFR-001：API 回應時間 P95 < 1 秒
- NFR-002：支援 100 並發用戶
- NFR-003：OWASP Top 10 安全合規

產出：PRD + FRD，完成後執行 SCG-0 閘門驗證。
```

**🔴 人工確認點（SCG-0）**：
```
PRD 和 FRD 已產出，請執行 SCG-0 閘門驗證。

文件路徑：
- docs/01_requirements/PRD-TaskMaster.md
- docs/01_requirements/FRD-TaskMaster.md

所有需求（F-001~006, NFR-001~003）是否完整？
[等待人工確認通過 SCG-0]
```

---

### 步驟 3：系統設計 → SCG-1（設計凍結）

```
SCG-0 已通過，請 SD 架構師開始系統設計。

技術棧：React + Node.js + PostgreSQL
FRD 路徑：docs/01_requirements/FRD-TaskMaster.md

請產出：
- SRD（系統需求文檔）
- ADR-001：技術棧選擇決策

完成後執行 SCG-1 閘門驗證。
```

---

### 步驟 4：架構設計 → SCG-2（架構凍結）

```
SRD 已完成，請繼續架構設計。

請產出：
- C4 Context + Container 圖
- ADR-002：資料庫設計決策（PostgreSQL 選型）
- ADR-003：認證機制決策（JWT vs Session）

完成後執行 SCG-2 閘門驗證。
```

**🔴 人工確認點（SCG-2）**：
```
C4 架構圖和 ADR-001~003 已完成。
請確認架構設計方向後，凍結架構（SCG-2 通過）。

[等待人工確認通過 SCG-2]
```

---

### 步驟 5：API Contract → SCG-3（Contract Freeze）

```
SCG-2 已通過，請生成 OpenAPI 3.1 規格。

API 模組：
- AUTH：POST /auth/register, POST /auth/login, POST /auth/logout
- TASKS：GET /tasks, POST /tasks, PUT /tasks/{id}, DELETE /tasks/{id}
- FILTERS：GET /tasks?status=&priority=

參考 SRD：docs/02_architecture/SRD-TaskMaster.md

完成後執行 SCG-3 Contract Freeze。
後端實作在 SCG-3 通過前不可開始。
```

**🔴 人工確認點（SCG-3）**：
```
OpenAPI 3.1 規格已完成，請確認後凍結 API Contract（SCG-3）。
Contract Frozen 後，API 簽名不可在廢棄程序外變更。

[等待人工確認 SCG-3 通過]
```

---

### 步驟 6：RTM 建立 + 測試規格 → SCG-5 準備

```
SCG-3 已通過，後端實作可以開始。
同時請 QA 測試師：

1. 生成 RTM（需求追蹤矩陣）
   - 對應 F-001~006 每個需求生成測試案例 TC-XXX
   
2. 建立測試策略：
   - 單元測試：覆蓋業務邏輯
   - 整合測試：API Contract 驗證
   - E2E 測試：核心用戶流程

目標：SCG-5 時 RTM 覆蓋率達 100%。
```

---

### 步驟 7：SCG-4 PR Review 指引

```
後端 API 實作完成，執行 SCG-4 PR Review。

請驗證：
1. 實作是否符合 OpenAPI 3.1 規格
2. 每個端點是否有對應的測試
3. 是否有偏離規格的地方（需更新 ADR）

PR 路徑：[PR 連結]
OpenAPI 規格：docs/02_architecture/api/openapi.yaml
```

---

### 步驟 8：交付前驗證 → SCG-5 + SCG-6

```
功能開發完成，執行最終交付驗證。

SCG-5 驗證：
- RTM 覆蓋率：[X]%（目標 100%）
- 未覆蓋需求：[列出]

SCG-6 發布前：
- 所有 SCG-0~5 是否已通過？
- 效能測試：P95 < 1 秒是否達標？
- 安全掃描：OWASP Top 10 是否合規？

請產出 SCG-6 Final Release Report。
```

---

## 📁 最終產出文件清單

| 文件 | 路徑 | SCG 對應 |
|------|------|---------|
| PRD-TaskMaster.md | docs/01_requirements/ | SCG-0 |
| FRD-TaskMaster.md | docs/01_requirements/ | SCG-0 |
| SRD-TaskMaster.md | docs/02_architecture/ | SCG-1 |
| C4-TaskMaster.md | docs/02_architecture/ | SCG-2 |
| ADR-001~003.md | docs/02_architecture/adr/ | SCG-2 |
| openapi.yaml | docs/02_architecture/api/ | SCG-3 |
| RTM-TaskMaster.md | docs/03_testing/ | SCG-5 |
| Test-Plan-TaskMaster.md | docs/03_testing/ | SCG-5 |

---

**版本**: v0.01（AISDLC-SDD）
**最後更新**: 2026-04-15
