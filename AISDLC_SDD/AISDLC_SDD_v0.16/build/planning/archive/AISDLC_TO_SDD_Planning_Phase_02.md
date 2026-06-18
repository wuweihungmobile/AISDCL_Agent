# AISDLC → SDD 轉型執行藍圖 Phase 02
# 規劃驅動情境：Greenfield（新專案開發）+ Documentation（文件維護）

**版本**: v1.0
**建立日期**: 2026-04-11
**前置條件**: Phase 01 完成（SDD 基礎設施建立完畢）
**文件類型**: 規劃文件（Planning）
**所屬分類**: docs/04_planning/

---

## 📋 Phase 02 目標

針對 **「規劃驅動型」** 情境（SDD 最天然的應用場域）進行 SDD 深度整合：
1. **Greenfield**：從第一行規格開始驅動整個新專案開發
2. **Documentation**：將文件維護從「事後補充」轉為「Living Spec」

---

## 🟢 情境一：Greenfield（新專案開發）

### SDD 強化分析

**Greenfield 是 SDD 的天然沃土**：從零開始，規格完全先行，無歷史包袱。

**現有流程缺口**（相比 SDD 標準）：
| 缺口 | 現狀 | SDD 目標 |
|------|------|---------|
| ADR 未強制 | 技術選型在 SRD 文字描述 | 每個技術選型必有 ADR |
| C4 圖可選 | 建議產出但非強制 | Context + Container 層必須強制 |
| API 先行度不足 | API Spec 可在 SRD 後補 | API Contract 必須在 Story 估點前完成 |
| 測試規格時序 | 測試計畫在 Story 後 | Test Contract 與 Story 同步定義 |

### SDD 強化版 Greenfield 流程

```
Stage 0: Spec Foundation（🆕 SDD 新增）
  ├── 0.1 建立 ADR 目錄結構
  ├── 0.2 建立 RTM 骨架
  └── 0.3 🔷 SCG-0：確認規格先行原則

Stage 1: Product Vision
  ├── pm-po: 產品願景 → PRD
  ├── ba: 業務需求驗證
  └── 🔷 SCG-1 → 🔴 Human: PRD Spec Freeze

Stage 2: Requirements Spec
  ├── sa: FRD + User Stories（含 AC）
  ├── 🆕 sa: RTM 初版建立（EPIC → F → US → AC）
  └── 🔷 SCG-1 → 🔴 Human: FRD + RTM Spec Freeze

Stage 3: Architecture Spec（關鍵 SDD 階段）
  ├── sd: C4 Context 圖（強制）
  ├── sd: C4 Container 圖（強制）
  ├── 🆕 sd: ADR-001 ~ ADR-N（技術選型 ADR）
  ├── sd: SRD（含非功能需求規格）
  ├── 🆕 sd: NFR 規格化（SLO/SLA 先行定義）
  └── 🔷 SCG-2 → 🔴 Human: SRD + ADR Spec Freeze

Stage 4: API Contract（關鍵 SDD 強化）
  ├── sd + integration-specialist: OpenAPI Spec（所有 API 端點）
  ├── 🆕 Contract-First 原則：UI 開發前 API Spec 必須凍結
  ├── integration-specialist: Consumer-Driven Contract（如適用）
  └── 🔷 SCG-3 → 🔴 Human: API Contract Freeze

Stage 5: Test Strategy Spec（🆕 提前至實作前）
  ├── qa: Test Strategy Document
  ├── 🆕 qa: Test Contract Spec（AC → AT 映射）
  ├── qa: RTM 更新（AT 層完成）
  └── 🔷 SCG-4 → 🔴 Human: Test Strategy Freeze

Stage 6: Security & Compliance Spec（選用）
  ├── security-engineer: STRIDE Threat Model
  ├── security-engineer: Security Architecture Doc (SAD)
  ├── compliance-officer: 合規需求對照表
  └── 🔷 SCG-5 → 🔴 Human: Security Spec Freeze

Stage 7: Sprint Planning（規格完整後）
  ├── pm-po: Story 優先級排序
  ├── dev: Story 估點（基於完整 API Spec）
  └── 🔴 Human: Sprint 0 計畫確認

Stage 8-11: Implementation & Delivery
  └── [原 Greenfield SOP Stage 4-11，規格已先行]
```

### Greenfield SDD 執行 Checklist

#### 2.1 Greenfield — 文件準備

- [x] 2.1.1 Stage 0 加入：建立 ADR 目錄（`docs/02_architecture/adr/`）
- [x] 2.1.2 Stage 0 加入：建立空白 RTM（`docs/03_testing/RTM-{project}.md`）
- [x] 2.1.3 Stage 1 強化：PRD 加入「非功能需求章節」（效能/可用性/安全目標初版）
- [x] 2.1.4 Stage 2 強化：FRD 完成後立即產出 RTM（EPIC→F→US→AC 層）
- [x] 2.1.5 Stage 3 強化：SRD 必須包含 C4 Context + Container 圖（強制）
- [x] 2.1.6 Stage 3 新增：每個架構決策建立 ADR（至少 3 個：技術棧/架構模式/部署策略）
- [x] 2.1.7 Stage 3 新增：NFR 規格化（RTM 加入 NFR 層）
- [x] 2.1.8 Stage 4 新增：OpenAPI Spec 作為 API 交付標準（非 FRD 文字描述）
- [x] 2.1.9 Stage 5 前置：Test Strategy + Test Contract 在實作前完成
- [x] 2.1.10 Stage 5 新增：RTM 完整（AC → AT 完整填入）

#### 2.2 Greenfield — Agent 設定變更

- [x] 2.2.1 `pm-po-agent-zh.yaml`：Stage 1 加入「NFR 目標採集」提示詞
- [x] 2.2.2 `sa-analyst-zh.yaml`：Stage 2 加入「RTM 生成」為必要輸出
- [x] 2.2.3 `sd-architect-zh.yaml`：Stage 3 加入「ADR 強制生成提示」（技術決策時自動觸發）
- [x] 2.2.4 `sd-architect-zh.yaml`：Stage 3 加入「C4 圖強制輸出」判斷邏輯
- [x] 2.2.5 `qa-tester-zh.yaml`：Stage 5 加入「Test Contract Spec」格式
- [x] 2.2.6 `integration-specialist-zh.yaml`（選用）：Stage 4 加入「OpenAPI-First 驗證」

#### 2.3 Greenfield — CI/CD Pipeline 調整

- [x] 2.3.1 L0 加入：`DocLint`（Markdown 格式 + Link 檢查）
- [x] 2.3.2 L0 加入：`SpecTrace`（RTM 完整性驗證腳本）
- [x] 2.3.3 L1 維持：Unit Test + Build Check（無變化）
- [x] 2.3.4 SAST 維持：靜態安全掃描（無變化）
- [x] 2.3.5 🔔 Notify 維持：Standard 通知（無變化）
- [x] 2.3.6 🆕 API Spec Validation：OpenAPI Spec 語法驗證加入 CI

#### 2.4 Greenfield — 產出物審查工作流

- [x] 2.4.1 PRD Review：pm-po + ba + sa 三方確認，加入 NFR 完整性檢查
- [x] 2.4.2 FRD Review：sa + ba + sd 三方確認，加入 RTM 完整性檢查
- [x] 2.4.3 SRD Review：sd + dev + qa 三方確認，加入 ADR 清單完整性檢查
- [x] 2.4.4 API Contract Review：sd + dev + qa 確認，Consumer Side 簽字
- [x] 2.4.5 Test Contract Review：qa + dev 確認，覆蓋率目標明確

### Greenfield SDD 新增必產文件

| 文件 | 產出 Stage | 負責 Agent | 格式 |
|------|-----------|-----------|------|
| ADR-001（技術棧選擇）| Stage 3 | sd-architect | ADR Markdown |
| ADR-002（架構模式）| Stage 3 | sd-architect | ADR Markdown |
| ADR-003（部署策略）| Stage 3 | sd-architect | ADR Markdown |
| RTM-{project}.md | Stage 2-5（漸進） | sa+qa | RTM Markdown |
| OpenAPI Spec | Stage 4 | sd + integration | YAML / JSON |
| Test Contract Spec | Stage 5 | qa-tester | Markdown |
| Security Arch Doc（選用）| Stage 6 | security-engineer | Markdown |

---

## 📝 情境二：Documentation（文件維護）

### SDD 強化分析

**Documentation 情境的 SDD 挑戰**：
- 現有文件可能不符合 SDD 規格標準
- 「文件即事後補充」的慣性需要扭轉
- Living Documentation 需要持續維護機制

**SDD 目標**：將 Documentation 情境從「文件產出」升級為「規格維護」

### SDD 強化版 Documentation 流程

```
Stage 1: Documentation Audit（🆕 SDD 新增）
  ├── technical-writer: 現有文件 SDD 符合度審計
  ├── sa: 規格完整性驗證
  └── 🔷 SCG-Doc：文件缺口清單確認

Stage 2: ADR Index 建立（🆕 SDD 強制）
  ├── technical-writer: 掃描現有架構決策
  ├── sd-architect: 將隱性決策轉化為 ADR
  └── 產出：ADR-INDEX.md（所有決策索引）

Stage 3: Living Documentation 架構
  ├── technical-writer: 建立文件-程式碼雙向連結
  ├── technical-writer: 版本化文件策略
  └── dev-senior: 技術正確性審查

Stage 4: RTM 建立/更新（🆕）
  ├── sa: 從現有文件提取需求追溯鏈
  └── 產出：完整 RTM（即使系統已上線）

Stage 5: API Documentation（強化）
  ├── sd: 現有 API 轉化為 OpenAPI Spec
  ├── integration-specialist: API 契約驗證
  └── 🔷 SCG-3 → 🔴 Human: API Spec Freeze

Stage 6: Security & Compliance Doc（選用）
  ├── security-engineer: 安全架構文件補齊
  └── compliance-officer: 合規文件更新
```

### Documentation SDD 執行 Checklist

#### 2.5 Documentation — 文件準備

- [x] 2.5.1 Stage 1 新增：文件 SDD 符合度審計（對照 SDD 三大支柱）
- [x] 2.5.2 Stage 2 新增：ADR 索引建立（`docs/02_architecture/adr/ADR-INDEX.md`）
- [x] 2.5.3 Stage 2 強化：將 SRD 中的隱性技術決策提取為 ADR
- [x] 2.5.4 Stage 3 強化：建立文件版本化策略（每個主要版本一份快照）
- [x] 2.5.5 Stage 4 新增：逆向建立 RTM（從現有 FRD/SRD 提取）
- [x] 2.5.6 Stage 5 強化：現有 API 文件升級為 OpenAPI Spec 格式
- [x] 2.5.7 Stage 5 新增：API 版本化策略（向後相容性文件）

#### 2.6 Documentation — Agent 設定變更

- [x] 2.6.1 `technical-writer-zh.yaml`：新增 `living_documentation` Skill 觸發條件
- [x] 2.6.2 `technical-writer-zh.yaml`：新增 `adr_index_maintenance` 標準流程
- [x] 2.6.3 `technical-writer-zh.yaml`：加入「文件-程式碼同步」驗證提示詞
- [x] 2.6.4 `sa-analyst-zh.yaml`：新增逆向 RTM 提取能力
- [x] 2.6.5 `sd-architect-zh.yaml`：新增「隱性決策 ADR 化」流程

#### 2.7 Documentation — CI/CD Pipeline 調整

- [x] 2.7.1 L0 維持：Markdown Lint（無變化）
- [x] 2.7.2 📝 DocPipeline 強化：
  - `link-check`：所有文件內連結有效性
  - `adr-index-sync`：ADR-INDEX.md 自動同步
  - `openapi-validate`：API Spec 語法驗證
  - `rtm-completeness`：RTM 追溯鏈完整性
- [x] 2.7.3 🔔 Notify 選配：文件更新通知（Slack/Teams）

#### 2.8 Documentation — 產出物審查工作流

- [x] 2.8.1 SDD 審計報告：technical-writer + sa 聯合審查
- [x] 2.8.2 ADR 索引審查：sd-architect 確認歷史決策完整性
- [x] 2.8.3 RTM 審查：sa + qa 確認追溯鏈完整
- [x] 2.8.4 API Spec 審查：sd + dev + integration-specialist 確認

### Documentation SDD 新增必產文件

| 文件 | 說明 | 負責 Agent |
|------|------|-----------|
| `SDD-COMPLIANCE-AUDIT.md` | 現有文件 SDD 符合度審計報告 | technical-writer |
| `ADR-INDEX.md` | 所有架構決策索引 | sd-architect |
| `RTM-EXISTING-SYSTEM.md` | 既有系統需求追溯矩陣 | sa-analyst |
| `LIVING-DOC-STRATEGY.md` | 活文件維護策略 | technical-writer |

---

## 📊 Phase 02 完成標準（Definition of Done）

| 情境 | 驗證項目 | 預期結果 |
|------|---------|---------|
| Greenfield | 每個技術選型有 ADR | 至少 3 個 ADR 範例 |
| Greenfield | C4 圖強制輸出 | Context + Container 2 層必須存在 |
| Greenfield | API Spec 先於實作 | OpenAPI Spec 在 Sprint 0 完成 |
| Greenfield | RTM 完整 | EPIC→AT 四層全填 |
| Documentation | ADR-INDEX.md 建立 | 所有既有架構決策已索引 |
| Documentation | DocPipeline 完整 | 4 個管道腳本全部運作 |

---

**上一階段**: [Phase 01 - Foundation](AISDLC_TO_SDD_Planning_Phase_01.md)
**下一階段**: [Phase 03 - Brownfield & Refactoring](AISDLC_TO_SDD_Planning_Phase_03.md)

**建立者**: 首席 AI-SDLC 轉型架構師
**最後更新**: 2026-04-11
