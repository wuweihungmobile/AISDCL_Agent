# 情境銜接指南（SDD 版）
# Scenario Transition Guide — SDD Edition

**框架版本**: AISDLC-SDD v0.01
**基於**: AISDLC-SDD v0.01 SCENARIO_TRANSITION_GUIDE
**最後更新**: 2026-04-15
**文檔目的**: 定義 SDD 十大情境之間的銜接關係、SCG 閘門轉換要求與文檔傳遞規範

---

## 場景切換前的 SCG 驗證（強制）

> **SDD 核心原則**: 場景切換是高風險動作，**在任何情境切換前，必須確認當前情境所有應完成的 SCG 閘門均已通過**。SCG 未通過的情況下進行情境切換，將導致規格不完整、追溯鏈斷裂，以及下游情境無法正常執行。

### 切換前 SCG 檢查清單（每次切換前必須確認）

```
切換前強制自我檢查:
  □ 當前情境的出口 SCG 閘門狀態是否為「通過」？
  □ 所有必要規格文件是否已凍結（不處於 Draft 狀態）？
  □ RTM 追溯鏈是否完整（無孤立需求或孤立測試案例）？
  □ 所有未解決的規格衝突是否已處理（已有對應 ADR）？
  □ 人工確認轉換意圖（🔴 必須等待人工確認）

推薦做法: 使用 /sdd-gate Skill 執行自動化 SCG 狀態確認
```

### 為何不可在 SCG 未通過時切換

| 問題情境 | 後果 | 嚴重程度 |
|---------|------|---------|
| SCG-0 未通過就切換到 Integration | FRD 未凍結，Consumer Contract 無法對應需求 | 🔴 嚴重 |
| SCG-2 未通過就切換到 Testing | C4/ADR 未完成，Test Strategy 無架構依據 | 🔴 嚴重 |
| SCG-3 未通過就切換到 DevOps | Contract 未凍結，CI/CD Pipeline Spec 對應規格不穩定 | 🟡 中等 |
| 情境 A 的規格有衝突，帶入情境 B | 情境 B 繼承衝突規格，導致更大的規格不一致 | 🔴 嚴重 |

---

## SDD 轉換核心規則

> **SDD 強制要求**: 情境轉換前，必須確認當前情境的相關 **SCG 閘門已通過**，並傳遞必要的規格文件。不允許在 SCG 未通過的情況下進行情境切換。

| 轉換規則 | 說明 |
|---------|------|
| **SCG 先行** | 當前情境的出口 SCG 閘門必須通過才能轉換 |
| **規格傳遞** | 所有已通過 SCG 的規格文件必須傳遞給下一情境 |
| **ADR 延續** | ADR 不重複建立，在新情境中繼續補充 |
| **RTM 延伸** | RTM 在轉換後延伸，不重置 |

---

## 情境轉換矩陣（含 SCG 要求）

| 從情境（From）| 可轉換到（To）| 轉換時機 | 必要 SCG | 機率 |
|-------------|-------------|---------|---------|------|
| **Greenfield** | Integration | 需整合第三方服務 | SCG-2 通過 | 80% |
| **Greenfield** | Testing | 開發完成 | SCG-4 通過 | 100% |
| **Greenfield** | Security | 需安全審查 | SCG-2 通過 | 60% |
| **Greenfield** | Performance | 效能要求高 | SCG-4 通過 | 40% |
| **Greenfield** | DevOps | 準備部署 | SCG-4 通過 | 100% |
| **Greenfield** | Documentation | 需產出文檔 | SCG-2 通過 | 90% |
| **Brownfield** | Refactoring | 需重構 | SCG-0 通過 | 70% |
| **Brownfield** | Integration | 新增整合功能 | SCG-0 通過 | 50% |
| **Brownfield** | Testing | 改造完成後測試 | SCG-4 通過 | 100% |
| **Brownfield** | Security | 安全漏洞修復 | SCG-0 通過 | 30% |
| **Brownfield** | Performance | 效能問題優化 | SCG-0 通過 | 60% |
| **Brownfield** | Migration | 需全面技術棧替換 | SCG-0 通過 | 20% |
| **Brownfield** | DevOps | 更新部署流程 | SCG-4 通過 | 80% |
| **Brownfield** | Documentation | 更新文檔 | 任何 SCG | 70% |
| **Refactoring** | Testing | 重構後驗證 | INV Gate 通過 + SCG-4 | 100% |
| **Refactoring** | Performance | 效能驗證 | SCG-4 通過 | 50% |
| **Refactoring** | Migration | 重構擴大至技術棧替換 | INV Gate 通過 | 15% |
| **Refactoring** | Documentation | 更新技術文檔 | SCG-4 通過 | 80% |
| **Integration** | Testing | 整合測試 | SCG-3 通過（Contract 凍結）| 100% |
| **Integration** | Security | API 安全審查 | SCG-3 通過 | 40% |
| **Integration** | Documentation | API 文檔 | SCG-3 通過 | 90% |
| **Performance** | Testing | 效能測試驗證 | PBS Gate 通過 | 100% |
| **Performance** | Refactoring | 效能重構 | PBS Gate 通過 | 30% |
| **Security** | Testing | 安全測試 | STRIDE 完成 | 100% |
| **Security** | Documentation | 安全文檔 | SCG-5 通過 | 80% |
| **Testing** | DevOps | 測試通過後部署 | SCG-5 通過 | 100% |
| **Testing** | Documentation | 測試報告文檔 | SCG-5 通過 | 70% |
| **DevOps** | Documentation | 部署文檔 | SCG-6 通過 | 60% |
| **Migration** | Testing | 遷移後全面驗證 | MCM + SCG-3 通過 | 100% |
| **Migration** | DevOps | CI/CD 重建 | SCG-3 通過 | 100% |
| **Migration** | Security | 遷移後安全審查 | SCG-3 通過 | 70% |
| **Migration** | Performance | 遷移後效能對比 | SCG-4 通過 | 80% |
| **Migration** | Documentation | 遷移手冊 | 任何 SCG | 90% |

---

## 情境組合機制（SDD 規格合併規則）

### 組合原則

1. **SCG 閘門取聯集** — 兩個情境的 SCG 要求都必須通過
2. **規格文件取聯集** — 兩個情境的必要規格文件都必須產出
3. **Agent 取聯集** — 兩個情境的 Agent 都可用
4. **RTM 合併** — 主情境和輔情境的需求合併到同一 RTM

### 常用組合模式

| 組合 | 主情境 | 輔情境 | SCG 要求 | 使用時機 |
|------|--------|--------|---------|---------|
| **遷移+新功能** | Migration | Greenfield | MCM + SCG-0 + SCG-3 | 技術棧遷移同時新增功能 |
| **重構+遷移** | Refactoring | Migration | INV Gate + MCM | 重構發現需技術棧替換 |
| **重構+新功能** | Refactoring | Greenfield | INV Gate + SCG-0 | 重構同時加新功能 |
| **新專案+整合** | Greenfield | Integration | SCG-3（兩情境共用 Contract）| 新專案需大量第三方整合 |
| **維護+效能** | Brownfield | Performance | SCG-0 + PBS Gate | 既有系統改版+效能優化 |

---

## 標準轉換流程（SDD 5 步驟）

### 步驟 1: 確認 SCG 閘門通過 🔴

```
轉換前自動檢查（sdd-gate 執行）:
  - [ ] 當前情境出口 SCG 閘門已通過
  - [ ] 所有必要規格文件已凍結
  - [ ] RTM 追蹤鏈完整
  - [ ] 人工確認轉換意圖

範例對話:
使用者: 「Greenfield 設計完成，需要整合 Stripe 支付」
AI: 「✅ 識別轉換需求: Greenfield → Integration
     🔍 SCG 檢查:
       SCG-2 狀態: ✅ 通過（C4 + ADR 完整）
       OpenAPI 狀態: ✅ SCG-3 已通過
     ✅ 建議載入: Integration 情境
     請確認是否進行轉換?」
使用者: 「確認」🔴
```

### 步驟 2: 準備規格傳遞包

```
📦 規格傳遞包（Greenfield → Integration）

SCG 通過的規格（自動帶入）:
  ✅ PRD v1.2（SCG-0 通過）
  ✅ FRD v1.1（SCG-0 通過）
  ✅ SRD v1.0（SCG-1 通過）
  ✅ C4 Model v1.0（SCG-2 通過）
  ✅ ADR-001~005（SCG-2 通過）
  ✅ OpenAPI 3.1 v1.0（SCG-3 通過）
  ✅ RTM v1.0（現有覆蓋率）

新情境需要補充（Integration）:
  ⬜ Consumer Contract（Stripe API）
  ⬜ Third-Party API Research Report

🔴 SCG-3 目標：Consumer Contract 凍結
```

### 步驟 3: 執行情境切換

```
AI 執行:
1. ✅ 載入 Integration SOP + SDD_INTEGRATION_ENHANCEMENT.md
2. ✅ 載入相關 Agents（integration-specialist, sd, qa, dev）
3. ✅ 載入規格傳遞包（PRD, FRD, SRD, OpenAPI）
4. ✅ 設定 SCG 目標（本情境：Consumer Contract SCG-3）
5. ✅ 延伸 RTM（新增 Integration 相關需求追蹤）

AI 回應:
「✅ 已切換到 Integration 情境（SDD 模式）
 ✅ 已載入規格: PRD/FRD/SRD/OpenAPI（均已通過 SCG）
 ✅ SCG-3 目標: Consumer Contract 凍結
 
 接下來步驟:
 Stage 1: API 研究（Stripe Payment API）
 Stage 2: 建立 Consumer Contract（contract-generate）
 Stage 3: SCG-3 閘門驗證 🔴
 Stage 4: 整合實作
 Stage 5: SCG-4 PR Review 🔴
```

### 步驟 4: 規格延伸驗證

```
🔍 轉換後規格一致性驗證（spec-compliance-check 執行）

已繼承規格:
  ✅ API 端點定義（來自 OpenAPI，SCG-3 已通過）
  ✅ 錯誤碼定義（API_Error_Codes.md）

需要建立:
  ⬜ Consumer Contract（Stripe 視角）
  ⬜ Trust Boundary Map（前後端 + Stripe 邊界）

RTM 狀態:
  現有覆蓋: 85%（Greenfield 需求）
  新增需求: F-INT-001~010（Integration 需求）
  目標: RTM 延伸後達 SCG-5 100%

🔴 請確認規格傳遞完整，開始 Integration 情境？
```

### 步驟 5: 開始新情境並延伸 SCG

```
🎯 Integration 情境 — SCG 延伸計畫

繼承自 Greenfield 已通過:
  ✅ SCG-0: PRD + FRD 完整性
  ✅ SCG-1: SRD + API Spec
  ✅ SCG-2: C4 + ADR
  ✅ SCG-3: OpenAPI（主系統）

Integration 新增 SCG-3（Consumer Contract）:
  目標: Stripe Consumer Contract 凍結
  負責: integration-specialist

整體 SCG-6 路徑:
  Greenfield SCG-4 → Integration SCG-3（Consumer Contract）
  → Integration SCG-4 → 合計 SCG-6 通過
```

---

## 常見情境組合流程（SDD 版）

### 1. 全新專案完整流程（Greenfield Full Stack）

```
Greenfield: PRD+FRD → SCG-0 🔴 → SRD+C4+ADR → SCG-2 🔴 → OpenAPI → SCG-3 🔴
    ↓ 傳遞: PRD/FRD/SRD/C4/ADR/OpenAPI（全部帶入）
Integration: Consumer Contract → SCG-3 🔴 → 整合實作 → SCG-4 🔴
    ↓ 傳遞: + Consumer Contract
Security: STRIDE → 安全設計 → SCG-5 🔴
    ↓ 傳遞: + STRIDE + 安全需求
Testing: RTM 延伸 → SCG-5 🔴 → 測試執行
    ↓ 傳遞: + RTM（100% 覆蓋）
Performance: PBS Gate 🔴 → 優化 → SCG-6 🔴
    ↓ 傳遞: + PBS + Benchmark 結果
DevOps: Pipeline Spec → SCG-4 🔴 → SCG-6 🔴
    ↓ 傳遞: + Pipeline Spec
Documentation: Living Doc Strategy → 撰寫 → SCG-4 🔴
```

**關鍵規格傳遞點**:
- ✅ Greenfield → Integration: OpenAPI（SCG-3 通過）必須完整
- ✅ Integration → Security: Consumer Contract 必須凍結
- ✅ Security → Testing: 安全需求納入 RTM
- ✅ Testing → Performance: RTM 100% 覆蓋後才執行 PBS Gate
- ✅ Performance → DevOps: PBS SLO 納入 Pipeline 監控

---

### 2. 既有系統改造流程（Brownfield Improvement）

```
Brownfield: As-Is SRD → Gap Analysis → SCG-0 🔴（改造需求凍結）
    ↓ 傳遞: As-Is SRD + Tech Debt Spec + Gap Analysis
    分支決策 🔴:
    ├─ 代碼品質差? → Refactoring（INV Gate 🔴 → 重構 → SCG-4 🔴）
    ├─ 效能問題? → Performance（PBS Gate 🔴 → 優化 → SCG-6 🔴）
    └─ 安全漏洞? → Security（STRIDE → SCG-5 🔴）
    ↓
Testing: RTM 延伸（含改造需求）→ SCG-5 🔴
    ↓
DevOps: Pipeline 更新 → SCG-6 🔴
    ↓
Documentation: 更新 As-Is → To-Be 文檔
```

---

### 3. 技術棧遷移完整流程

```
Migration: As-Is SRD → Contract Map → MCM Validate 🔴 → SCG-3 🔴
    ↓ 傳遞: As-Is SRD + Migration ADR + Contract Map
    分層執行（每層 SCG-4 🔴）:
      DB 層遷移 → 後端層遷移 → 前端層遷移 → 新平台
    ↓
Testing: 遷移驗證 RTM → SCG-5 🔴（含資料一致性）
    ↓
Performance: 遷移後 PBS 對比 → SCG-6 🔴
    ↓
Security: 新系統安全審查 → SCG-5 🔴
    ↓
Documentation: 遷移手冊 + 新架構文檔
```

---

## 轉換常見問題（SDD 版）

### 問題 1: SCG 未通過就想轉換

```
❌ 轉換被阻止:
當前情境: Greenfield
出口 SCG-3 狀態: ❌ 未通過（OpenAPI 不完整）
轉換目標: Integration

解決方案:
選項 A: 補充 OpenAPI 規格 → 重新 SCG-3 → 再轉換 ✅ 建議
選項 B: 強制轉換（覆蓋 SCG）❌ 禁止

SDD 原則: 未凍結的規格帶入新情境，會導致整體規格不一致。
```

### 問題 2: 轉換後規格衝突

```
⚠️ 規格衝突警告:
當前情境: Integration
繼承規格: OpenAPI v1.0（SCG-3 通過）
新發現: 整合後需要修改現有 API 端點設計

解決方案:
1. 啟動 Change Management（workflow/core/change-management.md）
2. 建立 ADR 記錄變更原因
3. 更新 OpenAPI 規格
4. 重新執行 SCG-3（在 Integration 情境中）
5. 通知所有已凍結的下游情境重新驗證

禁止: 不建立 ADR 直接修改已凍結的規格
```

### 問題 3: RTM 在轉換後失去連結

```
⚠️ RTM 追蹤鏈中斷:
當前情境: Testing
RTM 狀態: 新增 TC-INT-XXX（Integration 測試案例）
問題: 這些 TC 沒有對應到 F-INT-XXX 需求

解決方案:
1. rtm-generate 重新掃描，識別孤立測試案例
2. 補充 F-INT-XXX 需求（FRD 更新，需 SCG-0 重新確認）
3. 重新建立 RTM 追蹤鏈
4. SCG-5 重新驗證覆蓋率
```

### 問題 4: 並行情境規格衝突

```
⚠️ 並行 SCG 衝突:
情境 A: Greenfield（SCG-3 已凍結 OpenAPI v1.0）
情境 B: Integration（同時修改 OpenAPI 端點）

解決方案:
1. 停止情境 B 的修改
2. 在主情境（Greenfield）啟動 Change Management
3. 更新 OpenAPI v1.1
4. 重新執行 Greenfield SCG-3
5. Integration 繼承新版 OpenAPI v1.1 繼續

原則: SCG 凍結的規格只能透過 Change Management 修改
```

---

## 轉換時程規劃（SDD 版）

### 小型專案（1-3 人）

| 情境組合 | SCG 閘門 | 總時程 |
|---------|---------|-------|
| Greenfield → Testing → DevOps | SCG-0, SCG-3, SCG-4, SCG-5, SCG-6 | 4-6 週 |
| Brownfield → SCG-0 → Testing → DevOps | SCG-0, SCG-4, SCG-5, SCG-6 | 2-4 週 |

### 中型專案（4-10 人）

| 情境組合 | SCG 閘門 | 總時程 |
|---------|---------|-------|
| Greenfield → Integration → Security → Testing → DevOps | SCG-0~6 全套 | 10-16 週 |
| Brownfield → Refactoring（INV Gate）→ Testing → DevOps | INV Gate + SCG-0/4/5/6 | 6-10 週 |

### 大型專案（10+ 人）

- SCG 閘門分模組並行執行
- 每個模組獨立 SCG-0 ~ SCG-4
- 統一 SCG-5（整合 RTM）+ SCG-6（全系統發布）

---

## 最佳實踐

### ✅ 推薦

1. **情境轉換前執行 sdd-gate 確認** — 自動檢查 SCG 狀態
2. **規格傳遞包版本化** — 記錄轉換時各文件的版本號
3. **RTM 連續延伸** — 不重置，只新增
4. **ADR 跨情境共用** — 在新情境中追加 ADR，不重複建立
5. **情境轉換決策建立 ADR** — 記錄為何選擇此轉換路徑

### ❌ 禁止

1. **SCG 未通過就轉換** — 違反 SDD Spec-First 原則
2. **繞過 Change Management 修改凍結規格** — 破壞規格一致性
3. **並行修改同一規格文件** — 導致版本衝突
4. **轉換後不更新 RTM** — 導致 SCG-5 覆蓋率計算錯誤

---

## 相關文檔

- `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` — SCG 閘門執行規範
- `workflow/core/change-management.md` — 規格變更管理
- `scenarios/SCENARIO_AGENT_MAPPING.md` — 各情境 Agent 配置
- `scenarios/ERROR_RECOVERY_GUIDE.md` — SCG 失敗恢復
- `.claude/skills/sdd-gate/SKILL.md` — SCG 驗證技能

---

**維護者**: AISDLC-SDD Framework Team
**SDD 版本**: v0.01
**最後更新**: 2026-04-15
