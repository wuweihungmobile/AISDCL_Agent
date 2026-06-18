# Greenfield SDD 強化規範
# SDD Enhancement for Greenfield Scenario

**版本**: v1.0
**建立日期**: 2026-04-12
**前置條件**: Phase 01 完成
**適用情境**: Greenfield（新專案開發）

---

## 🎯 SDD 強化流程總覽

Greenfield 是 SDD 的天然沃土，規格完全先行，無歷史包袱。

### 強化後完整流程

```
Stage 0: Spec Foundation（🆕 SDD 新增）
  ├── 0.1 建立 ADR 目錄（docs/02_architecture/adr/）
  ├── 0.2 建立空白 RTM 骨架（docs/03_testing/RTM-{project}.md）
  └── 0.3 🔷 SCG-0：確認規格先行原則

Stage 1: Product Vision
  ├── pm-po: 產品願景 → PRD（含 NFR 章節）🆕
  ├── ba: 業務需求驗證
  └── 🔷 SCG-1 → 🔴 Human: PRD Spec Freeze

Stage 2: Requirements Spec
  ├── sa: FRD + User Stories（含 AC）
  ├── 🆕 sa: RTM 初版（EPIC → F → US → AC 層）
  └── 🔷 SCG-1 → 🔴 Human: FRD + RTM Spec Freeze

Stage 3: Architecture Spec（關鍵 SDD 階段）
  ├── sd: C4 Context 圖（強制）🆕
  ├── sd: C4 Container 圖（強制）🆕
  ├── 🆕 sd: ADR-001～ADR-N（技術選型 ADR）
  ├── sd: SRD（含非功能需求規格）
  ├── 🆕 sd: NFR 規格化（SLO/SLA 先行）
  └── 🔷 SCG-2 → 🔴 Human: SRD + ADR Spec Freeze

Stage 4: API Contract（關鍵 SDD 強化）
  ├── sd + integration: OpenAPI Spec（所有 API 端點）
  ├── 🆕 Contract-First：UI 開發前 API Spec 凍結
  ├── integration: Consumer-Driven Contract（如適用）
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
  └── [原 Greenfield SOP Stage，規格已先行]
```

---

## ✅ 2.1 文件準備規範

### Stage 0：Spec Foundation（🆕）

**2.1.1 建立 ADR 目錄**
- 執行：`mkdir -p docs/02_architecture/adr/`
- 建立：`docs/02_architecture/adr/ADR-INDEX.md`（空白索引）
- 時機：專案啟動第一步

**2.1.2 建立空白 RTM 骨架**
- 執行：從 `docs/03_testing/RTM-TEMPLATE.md` 複製
- 存放：`docs/03_testing/RTM-{project}-v0.md`
- 時機：Stage 0，作為追溯鏈的容器

**2.1.3 SCG-0 Spec Foundation Gate**
```
🔷 SCG-0 通過標準：
  - [ ] ADR 目錄已建立
  - [ ] 空白 RTM 已建立
  - [ ] 規格先行原則已由 Human 確認
```

---

### Stage 1：PRD 強化

**2.1.3 PRD 加入非功能需求章節**

PRD 必須包含以下 NFR 初版：
```markdown
## 非功能需求目標（初版）

| NFR 類型 | 目標值 | 備註 |
|---------|-------|------|
| 可用性 | XX.XX% | 生產環境 |
| 回應時間（P95） | < XXX ms | API 呼叫 |
| 吞吐量 | > XXX RPS | 尖峰流量 |
| 安全標準 | OWASP Top 10 | 最低標準 |
```

---

### Stage 2：FRD + RTM 強化

**2.1.4 FRD 完成後立即產出 RTM（EPIC→F→US→AC 層）**

RTM 第一版（Stage 2）必須包含：
- EPIC 層：所有業務史詩
- Feature 層：每個 EPIC 下的功能列表
- User Story 層：每個 Feature 的 US
- AC 層：每個 US 的驗收標準

AT 欄位此時留空（Stage 5 填入）。

---

### Stage 3：Architecture Spec 強化

**2.1.5 SRD 強制包含 C4 Context + Container 圖**

不允許只有文字描述的 SRD！必須包含：
```
docs/02_architecture/
├── C4-{system}-L1-Context.md    ← 必須
├── C4-{system}-L2-Container.md  ← 必須
└── SRD-{system}.md              ← 引用上述圖表
```

**2.1.6 每個架構決策建立 ADR（至少 3 個）**

最低要求：
- `ADR-001-{tech-stack}.md`：技術棧選擇
- `ADR-002-{architecture-pattern}.md`：架構模式
- `ADR-003-{deployment-strategy}.md`：部署策略

**2.1.7 NFR 規格化（RTM 加入 NFR 層）**

RTM Stage 3 版本需增加 NFR 欄位：
```
| EPIC | F | US | AC | AT | API | NFR | 狀態 |
```

---

### Stage 4：API Contract 強化

**2.1.8 OpenAPI Spec 作為 API 交付標準**

Contract-First 強制規則：
- UI 開發不得在 API Contract Freeze 前開始
- 每個端點使用 CONTRACT-TEMPLATE.yaml
- `x-aisdlc.related_us` 欄位必須填寫
- 儲存至 `docs/02_architecture/api/CONTRACT-{module}-v{N}.yaml`

---

### Stage 5：Test Strategy 強化

**2.1.9 Test Strategy + Test Contract 在實作前完成**

強制時序：
```
RTM（AC 層完整）→ Test Contract Spec → Test Strategy → 🔷 SCG-4 → 🔴 Human → 開始實作
```

**2.1.10 RTM 完整（AC → AT 完整填入）**

Stage 5 RTM 必須達到：
- AC → AT 一對一或一對多映射
- 覆蓋率 ≥ 90%（至少）
- 無 `❌ 未覆蓋` 狀態的 P0/P1 功能

---

## 🔍 2.4 產出物審查工作流

### 2.4.1 PRD Review
**參與方**：pm-po + ba + sa
**追加檢查**：
- [ ] NFR 章節完整（可用性/效能/安全目標已定義）
- [ ] 業務目標可量化
- [ ] 所有利害關係人已確認

### 2.4.2 FRD Review
**參與方**：sa + ba + sd
**追加檢查**：
- [ ] RTM 已建立（EPIC→AC 四層）
- [ ] AC 全部可測試
- [ ] User Story 符合 INVEST 原則

### 2.4.3 SRD Review
**參與方**：sd + dev + qa
**追加檢查**：
- [ ] ADR 清單完整（至少技術棧/架構模式/部署策略 3 個）
- [ ] C4 圖（L1 + L2）已產出
- [ ] NFR 已規格化（SLO/SLA 數值明確）

### 2.4.4 API Contract Review
**參與方**：sd + dev + qa
**Consumer Side 簽字確認**：
- [ ] 所有端點已定義
- [ ] Response Schema 完整
- [ ] 安全機制明確（Bearer/OAuth）
- [ ] Consumer 代表簽字：___________

### 2.4.5 Test Contract Review
**參與方**：qa + dev
**覆蓋率確認**：
- [ ] AC → AT 映射完整（覆蓋率 ≥ 90%）
- [ ] 測試退出標準明確
- [ ] 自動化測試範圍已定義

---

## 🗂️ Greenfield SDD 新增必產文件

| 文件 | Stage | Agent | 位置 |
|------|-------|-------|------|
| `ADR-001-tech-stack.md` | 3 | sd-architect | `docs/02_architecture/adr/` |
| `ADR-002-arch-pattern.md` | 3 | sd-architect | `docs/02_architecture/adr/` |
| `ADR-003-deployment.md` | 3 | sd-architect | `docs/02_architecture/adr/` |
| `RTM-{project}.md` | 2-5（漸進） | sa + qa | `docs/03_testing/` |
| `CONTRACT-{module}-v1.yaml` | 4 | sd + integration | `docs/02_architecture/api/` |
| `TCS-{feature}-{date}.md` | 5 | qa-tester | `docs/03_testing/contracts/` |
| `SAD-{system}-{date}.md`（選用） | 6 | security-engineer | `docs/06_quality/security/` |

---

## 🔗 相關文件

- [SDD 核心原則](../../docs/02_architecture/SDD_Core_Principles.md)
- [ADR 範本](../../docs/02_architecture/adr/ADR-TEMPLATE.md)
- [RTM 範本](../../docs/03_testing/RTM-TEMPLATE.md)
- [API Contract 範本](../../docs/02_architecture/api/CONTRACT-TEMPLATE.yaml)
- [Greenfield SOP](SOP.md)
