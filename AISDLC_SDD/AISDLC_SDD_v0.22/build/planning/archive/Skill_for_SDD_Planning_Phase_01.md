# Skill for SDD — 全面改寫規劃
# Skills Rewrite for AISDLC-SDD v0.01

**版本**: v1.0
**建立日期**: 2026-04-14
**範疇**: 38 個 Skills 全面 SDD 原生改寫
**目標**: 從「AISDLC v0.09 + 附加 SDD 區塊」改寫為「SDD 原生設計」

---

## 一、改寫動機與問題診斷

### 現狀問題

| 問題 | 現象 | 影響 |
|------|------|------|
| **SDD 附加模式** | SDD 區塊貼在 SKILL.md 末尾，非嵌入流程 | 執行者容易跳過 SDD 步驟 |
| **前置條件不明** | Skill 未聲明需要哪個 SCG 已通過 | 導致亂序執行，違反 Spec-First |
| **閘門游離** | SCG 閘門呼叫在「SDD 強化」段，非流程節點 | 閘門形同虛設 |
| **文件路徑混亂** | 部分 Skill 輸出至舊路徑，未對齊 `docs/` 規範 | 文件找不到 |
| **RTM 缺席** | 多數 Skill 沒有 RTM 追溯步驟 | 需求追溯斷鏈 |
| **Integration Skill 最弱** | 10 個整合 Skill 只有 4 行通用 SDD 說明 | 完全沒有 SDD 流程 |
| **Agent Skill 半整合** | Agent Skill 有「SDD 強化」段但仍為附加式 | 不夠原生 |

### 改寫目標

> **從「AISDLC + SDD 補丁」→「SDD 原生設計」**

- SDD 三大支柱（Spec-First / Design-as-Doc / Contract-Driven）**嵌入**每個 Skill 的執行流程
- 每個 Skill 明確聲明**前置 SCG**（需要哪些閘門已通過）和**後置動作**（協助通過哪個閘門）
- 所有文件輸出路徑對齊 `AISDLC_SDD_v0.01/docs/` 規範
- RTM 追溯步驟成為標準流程節點

---

## 二、SDD 原生 Skill 新標準結構

### 新 SKILL.md 標準模板

```yaml
---
name: skill-name-kebab
description: 角色說明（動詞開頭，含 SDD 關鍵字）
user-invocable: true
disable-model-invocation: false
argument-hint: "<必填> [選填]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# {Skill Title}（SDD 原生）

{一句話說明此 Skill 在 SDD 生命週期中的定位}

---

## 觸發方式

```bash
/{command}                    # 預設執行
/{command} {arg}              # 帶參數執行
```

---

## 前置條件（SDD Spec-First）

> 執行本 Skill 前，下列 SCG 閘門必須已通過：

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-N | {說明} | `/sdd-gate SCG-N` |

> 若閘門尚未通過，請先執行 `/sdd-gate SCG-N` 確認後再繼續。

---

## 執行流程

### 階段 1：{名稱}（含 SCG 時機說明）

...

### 階段 N：文件產出與 RTM 更新 🔴

1. 將產出文件存入正確路徑（見「強制產出」）
2. 執行 `/rtm-generate` 更新 RTM 追溯矩陣
3. 執行 `/spec-compliance-check` 驗證文件格式
4. 🔴 確認點：{需人工確認的內容}

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| {文件名} | `docs/{path}/{FILE}-{System}.md` | SCG-N |

---

## 後置動作

完成本 Skill 後：
```
/{next-skill} 或 /sdd-gate SCG-N
```

🔷 **本 Skill 協助通過**：SCG-N（{名稱}）

---

## 相關 Skill

- `/{related}` — {說明}

---

**基於**: AISDLC-SDD v0.01
**對應 Agent**: `{NN}.{role}-zh.yaml`
**對應 SDD Enhancement**: `scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`
```

### 新舊結構對比

| 項目 | 舊結構 | 新結構 |
|------|--------|--------|
| SDD 位置 | 文件末尾附加 | 嵌入各階段流程節點 |
| 前置條件 | 無 | 明確 SCG 前置聲明 |
| RTM 更新 | 無或可選 | 每個 Skill 最後必執行 |
| 文件路徑 | 不統一 | 強制對齊 `docs/` 規範 |
| 後置動作 | 無 | 明確下一步 SCG/Skill |
| Spec Check | 僅部分 Skill | 所有 Skill 的最終步驟 |

---

## 三、改寫範疇（38 個 Skills）

### 改寫優先級矩陣

| 類別 | 數量 | SDD 重要度 | 現狀品質 | 改寫優先級 |
|------|------|-----------|---------|-----------|
| SDD 核心 Skill | 5 | ⭐⭐⭐⭐⭐ | 🟢 中等 | 🥇 Phase 01 |
| Agent Skill | 6 | ⭐⭐⭐⭐⭐ | 🟡 附加式 | 🥇 Phase 02 |
| Scenario/Dev Skill | 3 | ⭐⭐⭐⭐ | 🟡 附加式 | 🥈 Phase 03 |
| Workflow Skill | 2 | ⭐⭐⭐⭐ | 🟡 附加式 | 🥈 Phase 03 |
| DevOps Skill | 5 | ⭐⭐⭐ | 🟡 通用補丁 | 🥉 Phase 04 |
| Security/Docs Skill | 3 | ⭐⭐⭐ | 🟡 通用補丁 | 🥉 Phase 04 |
| Code Quality Skill | 4 | ⭐⭐⭐ | 🟡 通用補丁 | 🥉 Phase 05 |
| Integration Skill | 10 | ⭐⭐ | 🔴 幾乎無 SDD | 🥉 Phase 05 |

---

## 四、分階段執行計畫

---

### Phase 01：新標準建立 + SDD 核心 Skill 精化（5 個）

**目標**：確立新 SKILL.md 標準，優化已有的 5 個 SDD 專屬 Skill

**改寫重點**：
- 補充各閘門之間的引用關係（sdd-gate 與其他 4 個 SDD Skill 的協作）
- 確保 sdd-gate 的閘門輸出格式成為所有其他 Skill 的標準參考
- spec-compliance-check：增加對 33 個 Skill 所有文件類型的驗證規則

| # | Skill | 目前問題 | 改寫要點 |
|---|-------|---------|---------|
| 1 | `sdd-gate` | 閘門定義完整，但缺少與其他 Skill 的引用鏈 | 補充「此閘門需要哪些 Skill 的產出」 |
| 2 | `spec-compliance-check` | 驗證規則不夠具體 | 按文件類型列出詳細驗證項目清單 |
| 3 | `rtm-generate` | 獨立 Skill，未與各 Agent Skill 串連 | 增加「哪個階段呼叫 RTM 更新」的上下文 |
| 4 | `contract-generate` | 良好，補充 Brownfield 逆向 Contract 情境 | 新增 `compat` 類型的完整範本 |
| 5 | `adr-generate` | 良好，補充 ADR Archaeology 情境 | 新增「從現有代碼逆向產出 ADR」流程 |

**完成標準**：
- [ ] 5 個 SDD 核心 Skill 符合新標準結構
- [ ] 建立 `SKILL_STANDARD_TEMPLATE.md`（可複製的範本）
- [ ] 更新 README.md 的 SDD Skill 說明

---

### Phase 02：Agent Skill 全面改寫（6 個）

**目標**：Agent Skill 是 SDD 工作流的主執行者，必須最先達到 SDD 原生標準

**改寫重點**：
- 每個 Agent Skill 必須有明確的「前置 SCG」和「後置 SCG」
- 流程中嵌入 RTM 更新、spec-compliance-check 呼叫
- 產出路徑對齊 `docs/` 分層結構

| # | Skill | 對應 SCG | 前置條件 | 主要產出 | 後置動作 |
|---|-------|---------|---------|---------|---------|
| 1 | `sa-analyst` | SCG-0 | 無（首個） | PRD確認、FRD、US、RTM初版 | → SCG-0 → `sd-architect` |
| 2 | `ba-analyst` | SCG-0 | PRD 草稿存在 | 需求驗證報告、利害關係人確認 | → SCG-0 協助 |
| 3 | `sd-architect` | SCG-1, SCG-2 | SCG-0 通過 | SRD、C4圖、ADR、API Spec草稿 | → SCG-2 → `contract-generate` |
| 4 | `qa-testing` | SCG-4, SCG-5 | SCG-3 通過 | 測試計畫、Test Cases、RTM更新 | → SCG-5 |
| 5 | `dev-review` | SCG-4 | SCG-3 通過 | 代碼審查報告、實作規格一致性確認 | → SCG-4 |
| 6 | `pm-planning` | SCG-0 輔助 | 無 | Sprint 計畫、Backlog | → 協助 SCG-0 |

**改寫要點（共同）**：
- 移除末尾的「SDD 強化」區塊，將其內容嵌入對應流程階段
- 在「產出文件」步驟後，強制加入 `/rtm-generate` 和 `/spec-compliance-check` 呼叫
- 新增「前置條件」表格作為 Skill 開頭第一個 section

**完成標準**：
- [ ] 6 個 Agent Skill 符合新標準結構
- [ ] 每個 Agent Skill 有明確 SCG 入出
- [ ] Agent 協作關係在每個 Skill 中明確表達

---

### Phase 03：Scenario + Workflow Skill 改寫（5 個）

**目標**：Scenario Skill 對應 SDD 四大場景，Workflow Skill 整合跨 Agent 流程

#### Scenario Skill（3 個）

| # | Skill | 對應 SDD 場景 | 改寫重點 |
|---|-------|------------|---------|
| 1 | `brownfield-analysis` | Brownfield | 逆向規格工程流程完整化；As-Is SRD → Gap Analysis → RTM 現有系統版 |
| 2 | `database-migration` | Brownfield/Refactoring | 加入 MCM Validate（Migration CI/CD）；資料庫 Contract 生成 |
| 3 | `mobile-development` | Greenfield/Brownfield | 加入行動端特有的 SCG 考量；App Store 發布作為 SCG-6 一環 |

**Brownfield 改寫重點**（最重要）：
```
階段 0: 前置確認（無 SCG 前置，此 Skill 本身產出 As-Is 規格）
階段 1: 逆向規格化（產出 As-Is SRD）         → 填入 SCG-0 前置資料
階段 2: Gap Analysis（As-Is vs To-Be）        → 為 SCG-1 準備
階段 3: Tech Debt 量化（TD-XXX 格式）         → docs/06_quality/
階段 4: RTM 現有系統版                        → /rtm-generate
🔷 作為 Greenfield/Refactoring 情境的起點
```

#### Workflow Skill（2 個）

| # | Skill | 改寫重點 |
|---|-------|---------|
| 1 | `sprint-planning` | 整合 SCG-0 確認；Sprint Goal 必須對應 FRD Feature ID |
| 2 | `release-management` | 整合 SCG-6（Release Gate）；Release Notes 格式對齊 SDD |

**完成標準**：
- [ ] 5 個 Skill 符合新標準結構
- [ ] Brownfield 成為 SDD 四大場景中最完整的 Skill
- [ ] Sprint Planning 中每個 Story 有 FRD 追溯

---

### Phase 04：DevOps + Security/Docs Skill 改寫（8 個）

**目標**：DevOps Skill 對應 SDD CI/CD 規格，Security Skill 整合 STRIDE 威脅模型

#### DevOps Skill（5 個）

| # | Skill | SDD 前置 | 改寫重點 |
|---|-------|---------|---------|
| 1 | `devops-github-actions` | SCG-3 通過後（Contract 凍結） | 加入 Contract 驗證 Step；對應 `cicd/SDD_TESTING_CICD.md` |
| 2 | `devops-gitlab-ci` | SCG-3 通過後 | 同上（GitLab 版） |
| 3 | `devops-docker` | SCG-2 通過後（Architecture Freeze） | Dockerfile 設計有對應 ADR |
| 4 | `devops-kubernetes` | SCG-3 通過後 | K8s 部署規格對應 SRD 部署架構 |
| 5 | `devops-monitoring` | SCG-6 前 | 監控指標對應 NFR 量化要求；PBS Gate |

**共同改寫原則**：
- 每個 DevOps Skill 在前置條件中聲明對應的 SDD CI/CD 規格文件
- Pipeline 中加入「Contract 一致性驗證」步驟
- 產出的 Pipeline 配置存入 `docs/08_deployment/`

#### Security/Docs/Compliance Skill（3 個）

| # | Skill | SDD 前置 | 改寫重點 |
|---|-------|---------|---------|
| 1 | `security-audit` | SCG-2 後（架構凍結後執行 STRIDE） | 加入 STRIDE 威脅模型為第一步；對應 `cicd/SDD_SECURITY_CICD.md` |
| 2 | `compliance-audit` | SCG-5 前 | 合規項目對應 RTM 驗收標準 |
| 3 | `documentation-api` | SCG-3 Contract 凍結後 | 從 OpenAPI Contract 自動生成 API 文件（非手工） |

**完成標準**：
- [ ] 8 個 Skill 符合新標準結構
- [ ] DevOps Skill 引用對應 SDD CI/CD 規格
- [ ] Security Audit 以 STRIDE 開場

---

### Phase 05：Integration + Code Quality Skill 改寫（14 個）

**目標**：Integration Skill 是改寫幅度最大的（現狀幾乎無 SDD），Code Quality Skill 補強 SDD 文件追溯

#### Integration Skill（10 個）— 重大改寫

**現狀問題**：10 個整合 Skill 的 SDD 區塊只有以下 4 行：
```
- 若有技術決策，觸發 /adr-generate
- 產出文件執行 /spec-compliance-check
- 若有 API 新增，觸發 /contract-generate
- 參考對應情境 SDD Enhancement
```

**改寫方向**：每個 Integration Skill 必須遵循「整合設計先於整合實作」原則：

```
整合設計流程（SDD 原生）：
步驟 0: 前置確認 — SCG-1（SRD 包含整合架構說明）已通過
步驟 1: 整合規格設計（Third-Party API Research 文件）
步驟 2: Consumer Contract 設計 → /contract-generate consumer
步驟 3: ADR 記錄整合決策 → /adr-generate
步驟 4: 實作整合代碼
步驟 5: RTM 更新 → /rtm-generate
步驟 6: Spec 驗證 → /spec-compliance-check
```

| # | Skill | 前置 SCG | 新增必要產出 |
|---|-------|---------|-----------|
| 1 | `integration-oauth` | SCG-1 | ADR（Auth 機制選型）、Consumer Contract |
| 2 | `integration-stripe` | SCG-1 | ADR（支付方案）、Webhook Contract |
| 3 | `integration-api-client` | SCG-1 | ADR（API 客戶端設計）、Error Contract |
| 4 | `integration-aws` | SCG-2（需 Architecture ADR） | ADR（AWS 服務選型）、IAM Policy Spec |
| 5 | `integration-webhook` | SCG-1 | Webhook Contract、Event Schema Spec |
| 6 | `integration-firebase` | SCG-2 | ADR（BaaS 選型）、Firebase Security Rules Spec |
| 7 | `integration-sendgrid` | SCG-1 | ADR（郵件服務選型）、Email Template Spec |
| 8 | `integration-openai` | SCG-1 | ADR（AI API 選型）、Prompt Contract |
| 9 | `integration-database` | SCG-2（需 DB Architecture ADR） | ADR（ORM 選型）、DB Schema Spec |
| 10 | `integration-redis` | SCG-2 | ADR（快取策略）、Cache Contract |

#### Code Quality Skill（4 個）

| # | Skill | SDD 前置 | 改寫重點 |
|---|-------|---------|---------|
| 1 | `refactoring-code-quality` | Brownfield 場景：As-Is SRD 已完成 | 重構前必須有 As-Is SRD；重構後更新 To-Be SRD；Business Invariant 保護 |
| 2 | `performance-optimization` | SCG-1 完成（NFR 已量化） | PBS 量化指標必須來自 NFR；對應 `cicd/SDD_PERFORMANCE_CICD.md` |
| 3 | `testing-strategy` | SCG-3 Contract 凍結後 | Test Case 對應 RTM；Contract Testing 納入策略 |
| 4 | `code-review` | SCG-4 實作後 | 審查清單對應規格文件（SRD/OpenAPI）；輸出 SCG-4 通過依據 |

**完成標準**：
- [ ] 10 個 Integration Skill 有完整「整合設計→Contract→實作」流程
- [ ] 4 個 Code Quality Skill 有 SDD 文件追溯
- [ ] 所有 Skill 的前置條件明確

---

### Phase 06：整合測試 + 文件更新

**目標**：確保 38 個改寫後的 Skill 可協同工作，更新 README 與 DEVELOPMENT_PLAN

| 任務 | 說明 |
|------|------|
| 完整 SDD 工作流串連測試 | 執行 `/sa-analyze` → `/sd-design` → `/contract-generate` → `/sdd-gate SCG-3` 確認串連 |
| README.md 更新 | 更新 Skill 統計、加入 SDD 生命週期圖 |
| SKILL_DEVELOPMENT_PLAN.md 更新 | 標記所有 Skill 為「SDD 原生改寫完成」 |
| `SKILL_STANDARD_TEMPLATE.md` 建立 | 作為未來新增 Skill 的標準範本 |

---

## 五、執行進度追蹤

### Phase 01 — SDD 核心 Skill 精化

| Skill | 狀態 | 改寫重點完成 |
|-------|------|------------|
| `sdd-gate` | ✅ 完成 | 補充 Skill 引用鏈 |
| `spec-compliance-check` | ✅ 完成 | 詳細驗證規則 |
| `rtm-generate` | ✅ 完成 | 串連各 Agent Skill |
| `contract-generate` | ✅ 完成 | Brownfield 逆向情境 |
| `adr-generate` | ✅ 完成 | ADR Archaeology 流程 |

### Phase 02 — Agent Skill

| Skill | 狀態 | SCG 入出 | RTM 嵌入 | 路徑對齊 |
|-------|------|---------|---------|---------|
| `sa-analyst` | ✅ 完成 | ✅ | ✅ | ✅ |
| `ba-analyst` | ✅ 完成 | ✅ | ✅ | ✅ |
| `sd-architect` | ✅ 完成 | ✅ | ✅ | ✅ |
| `qa-testing` | ✅ 完成 | ✅ | ✅ | ✅ |
| `dev-review` | ✅ 完成 | ✅ | ✅ | ✅ |
| `pm-planning` | ✅ 完成 | ✅ | ✅ | ✅ |

### Phase 03 — Scenario + Workflow Skill

| Skill | 狀態 |
|-------|------|
| `brownfield-analysis` | ✅ 完成 |
| `database-migration` | ✅ 完成 |
| `mobile-development` | ✅ 完成 |
| `sprint-planning` | ✅ 完成 |
| `release-management` | ✅ 完成 |

### Phase 04 — DevOps + Security/Docs Skill

| Skill | 狀態 |
|-------|------|
| `devops-github-actions` | ✅ 完成 |
| `devops-gitlab-ci` | ✅ 完成 |
| `devops-docker` | ✅ 完成 |
| `devops-kubernetes` | ✅ 完成 |
| `devops-monitoring` | ✅ 完成 |
| `security-audit` | ✅ 完成 |
| `compliance-audit` | ✅ 完成 |
| `documentation-api` | ✅ 完成 |

### Phase 05 — Integration + Code Quality Skill

| Skill | 狀態 | ADR 前置 | Contract | RTM |
|-------|------|---------|---------|-----|
| `integration-oauth` | ✅ 完成 | ✅ | ✅ Consumer Contract | ✅ |
| `integration-stripe` | ✅ 完成 | ✅ | ✅ Webhook Contract | ✅ |
| `integration-api-client` | ✅ 完成 | ✅ | ✅ Error Contract | ✅ |
| `integration-aws` | ✅ 完成 | ✅ | ✅ IAM Policy Spec | ✅ |
| `integration-webhook` | ✅ 完成 | ✅ | ✅ Event Schema Contract | ✅ |
| `integration-firebase` | ✅ 完成 | ✅ | ✅ Security Rules Spec | ✅ |
| `integration-sendgrid` | ✅ 完成 | ✅ | ✅ Email Template Spec | ✅ |
| `integration-openai` | ✅ 完成 | ✅ | ✅ Prompt Contract | ✅ |
| `integration-database` | ✅ 完成 | ✅ | ✅ DB Schema Contract | ✅ |
| `integration-redis` | ✅ 完成 | ✅ | ✅ Cache Contract | ✅ |
| `refactoring-code-quality` | ✅ 完成 | - | - | ✅ |
| `performance-optimization` | ✅ 完成 | - | ✅ PBS | ✅ |
| `testing-strategy` | ✅ 完成 | - | ✅ Consumer Contract | ✅ |
| `code-review` | ✅ 完成 | - | - | ✅ |

### Phase 06 — 整合測試 + 文件更新

| 任務 | 狀態 |
|------|------|
| README.md 更新 | ✅ 完成（2026-04-14）|
| SKILL_DEVELOPMENT_PLAN.md 更新 | ✅ 完成（2026-04-14）|
| SKILL_STANDARD_TEMPLATE.md 建立 | ✅ 已建立（見 skills/SKILL_STANDARD_TEMPLATE.md）|
| 完整工作流串連測試 | ⬜ 下一步（用戶驗收）|

**總完成率**: 38/38 Skills ✅ = **100%**

---

## 六、SDD 工作流 Skill 串連圖

```
需求階段
  /sa-analyze ──→ /ba-validate ──→ /sdd-gate SCG-0
                                          │
設計階段                                  ▼
  /sd-design ──→ /adr-generate ──→ /sdd-gate SCG-2
                       │                  │
                       ▼                  ▼
  /contract-generate ──→ /sdd-gate SCG-3（Contract Freeze）
                                          │
實作階段                                  ▼
  /devops-github-actions             /qa-testing
  /integration-* ──→ /adr-generate  /dev-review ──→ /sdd-gate SCG-4
                                          │
交付階段                                  ▼
  /rtm-generate ──→ /spec-compliance-check ──→ /sdd-gate SCG-5
                                          │
發布階段                                  ▼
  /release-management ──→ /sdd-gate SCG-6
```

---

## 七、完成定義（Definition of Done）

每個改寫後的 Skill 必須滿足：

- [ ] 符合「SDD 原生 Skill 新標準結構」（第二節）
- [ ] 有明確「前置條件（SCG）」表格
- [ ] 執行流程各階段嵌入 SCG/RTM/Spec 步驟（非附加）
- [ ] 所有產出路徑對齊 `docs/` 分層結構
- [ ] 最後步驟包含 `/rtm-generate` + `/spec-compliance-check`
- [ ] 有明確「後置動作」聲明協助通過哪個 SCG
- [ ] `argument-hint` 清楚標示必填/選填參數
- [ ] `allowed-tools` 列表最小化（只列實際使用的工具）

---

**維護者**: AISDLC Framework Team
**下一步**: 依 Phase 01 → Phase 06 順序逐步執行改寫
**執行方式**: 每個 Phase 啟動時呼叫對應的「改寫 Skill 任務」
