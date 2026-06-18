# AISDLC → SDD 轉型執行藍圖 Phase 03
# 維護情境：Brownfield（舊專案維護）+ Refactoring（系統重構）

**版本**: v1.0
**建立日期**: 2026-04-11
**前置條件**: Phase 01、Phase 02 完成
**文件類型**: 規劃文件（Planning）
**所屬分類**: docs/04_planning/

---

## 📋 Phase 03 目標

針對 **「逆向規格化」** 情境進行 SDD 整合：
1. **Brownfield**：從現有系統逆向提取隱性設計，補齊規格文件
2. **Refactoring**：重構前必須先完成「現況規格」，再設計「目標規格」

> 💡 **SDD 洞察**：Brownfield 與 Refactoring 是 SDD 的最大挑戰——
> 現有系統往往沒有完整規格，必須先「逆向工程規格化（Reverse Spec Engineering）」，
> 才能在 SDD 框架下進行修改或重構。

---

## 🟡 情境三：Brownfield（舊專案維護）

### SDD 強化分析

**Brownfield 的 SDD 挑戰**：
| 挑戰 | 問題描述 | SDD 解法 |
|------|---------|---------|
| 隱性設計 | 設計決策只存在於程式碼 | 逆向提取 ADR（As-Is） |
| 規格缺失 | 無 FRD/SRD 或嚴重過時 | 先補 As-Is SRD，再寫 To-Be SRD |
| 測試不足 | 變更影響範圍不明 | 先建 As-Is 測試規格，再設計回歸策略 |
| 技術債隱藏 | 技術債未文件化 | code-analyzer → 技術債規格文件 |

### 逆向規格工程（Reverse Spec Engineering）模型

```
現有程式碼 / 生產系統
         ↓
[code-analyzer] 程式碼品質分析
[sa-analyst]    業務邏輯提取
[sd-architect]  架構模式識別
         ↓
As-Is SRD（現況系統規格）
  ├── As-Is C4 Context 圖
  ├── As-Is C4 Container 圖
  ├── As-Is ADR（重建歷史決策）
  └── 技術債清單（Tech Debt Spec）
         ↓
🔴 Human: 現況規格確認
         ↓
差異分析（Gap Analysis）
  ├── 規格差距（Spec Gap）
  └── 技術差距（Tech Gap）
         ↓
To-Be SRD（目標系統規格）
  ├── To-Be C4 圖
  ├── To-Be ADR（新決策）
  └── 變更影響評估
         ↓
🔷 SCG-2 → 🔴 Human: To-Be 規格凍結
         ↓
實作（基於 To-Be SRD）
```

### SDD 強化版 Brownfield 流程

```
Stage 1: 現況分析（強化：逆向規格化）
  ├── sa: 業務邏輯提取 → 業務規格文件（As-Is FRD）
  ├── code-analyzer: 程式碼分析 → 技術債規格
  ├── sd: As-Is 架構識別 → C4 圖（強制）
  ├── 🆕 sd: As-Is ADR 重建（識別並文件化歷史決策）
  └── 🔷 SCG-1 → 🔴 Human: As-Is 規格確認

Stage 2: 差異分析與需求（強化）
  ├── sa: 新需求 → To-Be FRD（基於 As-Is）
  ├── pm-po: 業務影響評估
  ├── 🆕 產出：Gap Analysis Report（規格差距）
  └── 🔴 Human: 變更範圍確認

Stage 3: To-Be 架構設計（SDD 核心）
  ├── sd: To-Be C4 圖（Context + Container 強制）
  ├── sd: To-Be ADR（每個架構決策）
  ├── sd: To-Be SRD（含變更影響分析）
  ├── security-engineer（選用）: 安全影響評估
  └── 🔷 SCG-2 → 🔴 Human: To-Be 規格凍結

Stage 4: API Contract（強化）
  ├── sd: 現有 API 轉化為 OpenAPI Spec（As-Is）
  ├── sd: To-Be API Spec（新增/修改 API）
  ├── 🆕 向後相容性驗證（Backward Compatibility Check）
  └── 🔷 SCG-3 → 🔴 Human: API Contract 確認

Stage 5: 回歸測試策略（SDD 前置）
  ├── qa: As-Is 測試規格建立（逆向）
  ├── qa: 回歸測試策略（覆蓋變更影響範圍）
  ├── qa: RTM 建立（從 As-Is FRD 提取）
  └── 🔷 SCG-4 → 🔴 Human: 測試策略確認

Stage 6: 安全合規（選用）
  ├── security-engineer: 安全漏洞影響評估
  └── compliance-officer: 法規合規影響分析

Stage 7-N: 實作（基於凍結規格）
  └── [原 Brownfield SOP 實作階段]
```

### Brownfield SDD 執行 Checklist

#### 3.1 Brownfield — 文件準備

- [x] 3.1.1 Stage 1 強化：As-Is FRD 必須先於任何改動
- [x] 3.1.2 Stage 1 強化：As-Is C4 Context + Container 圖（強制）
- [x] 3.1.3 Stage 1 新增：As-Is ADR 重建（程式碼考古，文件化歷史決策）
- [x] 3.1.4 Stage 1 新增：技術債規格文件（`docs/06_quality/tech-debt-spec.md`）
- [x] 3.1.5 Stage 2 新增：Gap Analysis Report（As-Is vs To-Be 差距）
- [x] 3.1.6 Stage 3 強化：To-Be SRD 必須包含「變更影響分析」章節
- [x] 3.1.7 Stage 3 強化：To-Be ADR（每個技術決策一份）
- [x] 3.1.8 Stage 4 強化：現有 API 必須轉化為 OpenAPI Spec（As-Is Contract）
- [x] 3.1.9 Stage 4 新增：向後相容性聲明（Breaking Changes 清單）
- [x] 3.1.10 Stage 5 強化：回歸測試策略基於 RTM 的變更影響範圍

#### 3.2 Brownfield — Agent 設定變更

- [x] 3.2.1 `sa-analyst-zh.yaml`：新增 `as_is_srd_reverse` Skill（逆向規格提取標準流程）
- [x] 3.2.2 `sa-analyst-zh.yaml`：新增「Gap Analysis 框架」提示詞
- [x] 3.2.3 `sd-architect-zh.yaml`：新增 `as_is_c4_generation`（逆向 C4 圖生成）
- [x] 3.2.4 `sd-architect-zh.yaml`：新增 `adr_archaeology`（ADR 考古重建）提示詞
- [x] 3.2.5 `code-analyzer-zh.yaml`：新增「技術債規格化」輸出格式
- [x] 3.2.6 `qa-tester-zh.yaml`：新增「As-Is 測試規格提取」能力

#### 3.3 Brownfield — CI/CD Pipeline 調整

- [x] 3.3.1 L0 加入：`DocLint` + `SpecTrace`（As-Is 規格完整性）
- [x] 3.3.2 L1 維持：Unit Test + Build Check
- [x] 3.3.3 SAST：靜態安全掃描（無變化）
- [x] 3.3.4 **Regression（SDD 強化）**：回歸測試範圍必須基於 RTM 的影響矩陣
- [x] 3.3.5 🆕 `compat-check`：API 向後相容性自動驗證
- [x] 3.3.6 🔔 Notify: Standard（無變化）

#### 3.4 Brownfield — 產出物審查工作流

- [x] 3.4.1 As-Is 規格審查：sa + dev-senior + sd 聯合確認（現況準確性）
- [x] 3.4.2 Gap Analysis 審查：sa + pm-po + ba 確認（變更範圍合理性）
- [x] 3.4.3 To-Be 規格審查：sd + dev-senior + qa 確認（技術可行性）
- [x] 3.4.4 ADR 審查：sd + dev-senior 確認（每個決策合理性）
- [x] 3.4.5 API Compat 審查：sd + dev + integration-specialist 確認

### Brownfield SDD 新增必產文件

| 文件 | 說明 | 存放位置 |
|------|------|---------|
| `AS-IS-FRD-{system}.md` | 現況功能規格 | `docs/01_requirements/` |
| `AS-IS-SRD-{system}.md` | 現況系統規格（含 C4） | `docs/02_architecture/` |
| `ADR-AS-IS-{NNN}.md` | 歷史架構決策重建 | `docs/02_architecture/adr/` |
| `TECH-DEBT-SPEC.md` | 技術債規格清單 | `docs/06_quality/` |
| `GAP-ANALYSIS-{feature}.md` | 規格差距分析 | `docs/04_planning/` |
| `TO-BE-SRD-{feature}.md` | 目標系統規格 | `docs/02_architecture/` |
| `API-COMPAT-{version}.md` | API 向後相容性聲明 | `docs/02_architecture/api/` |

---

## 🔵 情境四：Refactoring（系統重構）

### SDD 強化分析

**Refactoring 的 SDD 核心原則**：
> 「重構不是盲目修改程式碼，而是依照目標規格重新實現相同功能」

**重構前 SDD 必備**：
1. **Before Architecture Spec**：重構前的完整架構文件
2. **Refactoring Plan as Spec**：重構計畫本身即是規格文件
3. **Invariant Spec**：定義重構中**不可改變**的業務行為
4. **After Architecture Spec**：重構後的目標架構文件

### SDD 強化版 Refactoring 流程

```
Stage 0: 重構準備（🆕 SDD 強制）
  ├── code-analyzer: 程式碼品質量化（複雜度 / 耦合度 / 覆蓋率）
  ├── sd: Before Architecture Spec（當前架構文件化）
  ├── sd: Before C4 圖（強制）
  └── 🔴 Human: 確認重構範圍與目標

Stage 1: 不變量規格（🆕 SDD 強制）
  ├── sa: 業務不變量清單（Business Invariants）
  │     「這些行為在重構前後必須完全一致」
  ├── qa: 不變量測試規格（Invariant Test Contract）
  └── 🔷 SCG-1 → 🔴 Human: 不變量規格凍結

Stage 2: 重構目標規格
  ├── sd: After Architecture Spec（目標架構）
  ├── sd: After C4 圖（目標狀態）
  ├── sd: 重構 ADR（每個重構決策）
  │     ADR 格式：Before State → Decision → After State
  ├── dev-senior: 重構風險評估
  └── 🔷 SCG-2 → 🔴 Human: 目標規格凍結

Stage 3: 重構計畫即規格
  ├── sd + dev-senior: 分階段重構計畫（Strangler Fig / Branch by Abstraction）
  ├── 每個重構步驟必須是「原子操作」（單一職責）
  ├── qa: Mutation Test 策略（確保重構不改變行為）
  └── 🔴 Human: 重構計畫確認

Stage 4: 漸進式重構執行
  ├── [每個重構步驟後]
  │   ├── 執行不變量測試（Invariant Tests）
  │   ├── 執行 Mutation Tests
  │   └── 驗證 Before → After 行為一致
  └── 🔴 Human（每個里程碑）: 確認繼續

Stage 5: 重構完成驗證
  ├── sd: After Architecture 文件確認
  ├── qa: 完整回歸驗證
  └── 🔴 Human: 重構完成確認
```

### Refactoring SDD 執行 Checklist

#### 3.5 Refactoring — 文件準備

- [x] 3.5.1 Stage 0 強制：Before Architecture Spec（重構前必須完整）
- [x] 3.5.2 Stage 0 強制：Before C4 Context + Container 圖
- [x] 3.5.3 Stage 0 強制：程式碼品質基準報告（量化指標）
- [x] 3.5.4 Stage 1 新增：Business Invariants Spec（業務不變量清單）
- [x] 3.5.5 Stage 1 新增：Invariant Test Contract（不變量測試規格）
- [x] 3.5.6 Stage 2 新增：After Architecture Spec（目標架構文件）
- [x] 3.5.7 Stage 2 新增：After C4 圖（目標 C4）
- [x] 3.5.8 Stage 2 強化：重構 ADR（Before/Decision/After 格式）
- [x] 3.5.9 Stage 3 強化：重構計畫本身視為規格（Refactoring Plan as Spec）
- [x] 3.5.10 每個重構步驟後：更新 After Architecture 進度文件

#### 3.6 Refactoring — Agent 設定變更

- [x] 3.6.1 `sd-architect-zh.yaml`：新增「重構 ADR 格式」（Before/Decision/After）
- [x] 3.6.2 `sd-architect-zh.yaml`：新增「架構對比圖生成」能力（Before vs After）
- [x] 3.6.3 `code-analyzer-zh.yaml`：新增量化指標輸出格式（複雜度/耦合度/覆蓋率）
- [x] 3.6.4 `qa-tester-zh.yaml`：新增「Invariant Test Contract」格式
- [x] 3.6.5 `dev-senior-zh.yaml`：新增「漸進式重構策略」提示詞（Strangler Fig / Branch by Abstraction）
- [x] 3.6.6 `sa-analyst-zh.yaml`：新增「Business Invariants 提取」能力

#### 3.7 Refactoring — CI/CD Pipeline 調整

- [x] 3.7.1 L0 加入：`DocLint` + `SpecTrace`（Before/After 規格一致性）
- [x] 3.7.2 L1 維持：Unit Test（不變量測試必須 100% 通過）
- [x] 3.7.3 SAST：靜態安全掃描
- [x] 3.7.4 **Mutation Test（SDD 強化）**：
  - 每個重構步驟後執行
  - 目標：確認業務行為不變
  - 通過標準：Mutation Score ≥ 80%
- [x] 3.7.5 🆕 `arch-diff`：Before/After 架構差異自動分析
- [x] 3.7.6 🔔 Notify: Standard（無變化）

#### 3.8 Refactoring — 產出物審查工作流

- [x] 3.8.1 Before Architecture 審查：sd + dev-senior 確認現況準確
- [x] 3.8.2 業務不變量審查：sa + ba + qa 聯合確認（不可遺漏任何不變量）
- [x] 3.8.3 After Architecture 審查：sd + dev-senior + dev 確認可行性
- [x] 3.8.4 重構計畫審查：sd + dev-senior + qa 確認步驟完整性
- [x] 3.8.5 每個重構里程碑：自動化驗證 + Human 確認

### Refactoring SDD 新增必產文件

| 文件 | 說明 | 存放位置 |
|------|------|---------|
| `BEFORE-ARCH-{system}.md` | 重構前架構規格 | `docs/02_architecture/` |
| `AFTER-ARCH-{system}.md` | 重構後目標架構 | `docs/02_architecture/` |
| `ADR-REFACTOR-{NNN}.md` | 重構決策記錄 | `docs/02_architecture/adr/` |
| `INVARIANT-SPEC-{system}.md` | 業務不變量規格 | `docs/01_requirements/` |
| `INVARIANT-TEST-CONTRACT.md` | 不變量測試規格 | `docs/03_testing/contracts/` |
| `REFACTOR-PLAN-{system}.md` | 重構計畫（即規格） | `docs/04_planning/` |
| `CODE-QUALITY-BASELINE.md` | 程式碼品質基準 | `docs/06_quality/` |

---

## 📊 Phase 03 完成標準（Definition of Done）

| 情境 | 驗證項目 | 預期結果 |
|------|---------|---------|
| Brownfield | As-Is 規格完整 | As-Is FRD + SRD + C4 全部存在 |
| Brownfield | ADR 考古完成 | 至少 3 個歷史決策 ADR 重建 |
| Brownfield | API 向後相容性文件 | Breaking Changes 清單明確 |
| Refactoring | 業務不變量清單 | 所有業務行為已列舉並測試化 |
| Refactoring | Before/After 規格 | 兩版 C4 圖均存在 |
| Refactoring | Mutation Test 整合 | Mutation Score 目標 ≥ 80% |

---

**上一階段**: [Phase 02 - Greenfield & Documentation](AISDLC_TO_SDD_Planning_Phase_02.md)
**下一階段**: [Phase 04 - Migration & DevOps & Integration](AISDLC_TO_SDD_Planning_Phase_04.md)

**建立者**: 首席 AI-SDLC 轉型架構師
**最後更新**: 2026-04-11
