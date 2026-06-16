# Brownfield 情境 SDD 強化規範
# SDD Brownfield Scenario Enhancement

**版本**: v1.0
**建立日期**: 2026-04-12
**適用情境**: Brownfield（舊專案維護）
**前置條件**: Phase 01 SDD_CICD_BASE_LAYER.md 已定義

---

## 🎯 目標：逆向規格工程（Reverse Spec Engineering）

Brownfield 是 SDD 的最大挑戰——現有系統往往沒有完整規格。
SDD 解法：**先逆向提取現況規格（As-Is Spec），再設計目標規格（To-Be Spec）**。

---

## 🏗️ SDD 強化版 Brownfield 流程

### Stage 0 → Stage 1：現況分析（3.1.1-3.1.3）

```
Stage 1: 現況分析（逆向規格化）
  ├── sa-analyst: 業務邏輯提取 → As-Is FRD（必須先於任何改動）
  ├── code-analyzer: 程式碼分析 → 技術債規格文件
  ├── sd-architect: As-Is 架構識別 → C4 Context + Container 圖（強制）
  ├── 🆕 sd-architect: As-Is ADR 重建（程式碼考古，文件化歷史決策）
  └── 🔷 SCG-1 → 🔴 Human: As-Is 規格確認（Before State 已充分文件化）
```

**3.1.1 As-Is FRD 強制規則**:
- 任何 Brownfield 修改前，必須先完成 As-Is FRD
- 格式：`docs/01_requirements/AS-IS-FRD-{system}.md`
- 內容：現有業務流程、業務規則、用戶角色（從程式碼逆向）
- SCG-1 通過條件：As-Is FRD 已由 Human 確認準確

**3.1.2 As-Is C4 圖強制規則**:
- C4 Context（L1）+ C4 Container（L2）均為強制輸出
- 格式：`docs/02_architecture/AS-IS-SRD-{system}.md`（含 C4 圖）
- Mermaid 語法嵌入 Markdown
- SCG-2 通過條件：C4 圖已由 sd-architect + Human 確認

**3.1.3 As-Is ADR 重建（程式碼考古）**:
- 識別程式碼中的隱性技術決策（框架選擇、設計模式、資料庫方案等）
- 每個歷史決策轉化為 ADR 文件（標記 Context 為「推斷自程式碼考古」）
- 至少重建 3 個核心架構決策
- 格式：`docs/02_architecture/adr/ADR-AS-IS-{NNN}-{title}.md`
- 更新 ADR-INDEX.md

---

### Stage 1-2：技術債與差距分析（3.1.4-3.1.5）

**3.1.4 技術債規格文件**:
```yaml
tech_debt_spec:
  file: "docs/06_quality/TECH-DEBT-SPEC.md"
  content:
    - "技術債 ID（TD-{NNN}）"
    - "技術債類型（架構/程式碼/測試/文件/安全）"
    - "嚴重程度（P0/P1/P2/P3）"
    - "業務影響評估"
    - "修復成本估算（Story Points）"
    - "建議修復時程"
  output_by: "code-analyzer"
  template: "docs/06_quality/TECH-DEBT-SPEC-TEMPLATE.md"
```

**3.1.5 Gap Analysis Report**:
```yaml
gap_analysis:
  file: "docs/04_planning/GAP-ANALYSIS-{feature}.md"
  content:
    - "As-Is 現況規格摘要"
    - "To-Be 目標規格摘要"
    - "規格差距清單（功能差距 / 架構差距 / API 差距）"
    - "技術差距清單（技術債影響）"
    - "變更風險評估"
    - "建議實施優先級"
  output_by: "sa-analyst"
  template: "docs/04_planning/GAP-ANALYSIS-TEMPLATE.md"
  human_confirmation: "🔴 Human: 變更範圍確認"
```

---

### Stage 3：To-Be 架構設計（3.1.6-3.1.7）

**3.1.6 To-Be SRD 必要章節**:
```yaml
to_be_srd_requirements:
  mandatory_sections:
    - "To-Be C4 Context 圖（L1）"
    - "To-Be C4 Container 圖（L2）"
    - "變更影響分析（Impact Analysis）"
      - "受影響模組清單"
      - "API 版本影響"
      - "資料庫 Schema 影響"
      - "下游系統影響"
    - "From As-Is → To-Be 對照表"
  file: "docs/02_architecture/TO-BE-SRD-{feature}.md"
  spec_gate: "🔷 SCG-2 Architecture Spec Gate"
  human_confirmation: "🔴 Human: To-Be 規格凍結"
```

**3.1.7 To-Be ADR 強制規則**:
- 每個架構決策必須有獨立 ADR
- ADR 格式：包含「As-Is → 決策 → To-Be」對照
- 不可使用「稍後補充」或「待確認」狀態
- 必須在 SCG-2 審查前完成

---

### Stage 4：API Contract（3.1.8-3.1.9）

**3.1.8 現有 API 轉化為 OpenAPI Spec（As-Is Contract）**:
```yaml
as_is_api_contract:
  requirement: "所有現有 API 必須轉化為 OpenAPI 3.1 格式"
  file: "docs/02_architecture/api/CONTRACT-{module}-as-is.yaml"
  process:
    - "掃描現有 API 端點（路由、方法、參數）"
    - "逆向生成 OpenAPI Schema"
    - "標記 deprecated 端點"
    - "驗證 OpenAPI 語法（spectral）"
  spec_gate: "🔷 SCG-3 API Contract Gate"
```

**3.1.9 向後相容性聲明（Breaking Changes 清單）**:
```yaml
backward_compatibility:
  file: "docs/02_architecture/api/API-COMPAT-{version}.md"
  content:
    - "Breaking Changes 清單（每個 Breaking Change 一行）"
    - "非 Breaking Changes 清單"
    - "廢棄端點清單（含廢棄日期）"
    - "遷移指南（如何從舊版本升級）"
    - "影響的 Consumer 清單"
  template: "docs/02_architecture/api/API-COMPAT-TEMPLATE.md"
  human_confirmation: "🔴 Consumer Side 確認 Breaking Changes"
```

---

### Stage 5：回歸測試策略（3.1.10）

**3.1.10 回歸測試策略基於 RTM 影響範圍**:
```yaml
regression_strategy:
  requirement: "回歸測試範圍必須由 RTM 的 Impact Analysis 決定，而非人工判斷"
  process:
    - "從 Gap Analysis 提取受影響 US 清單"
    - "從 RTM 查找受影響 US 的 AT"
    - "生成「受影響 AT 清單」（最小必要回歸範圍）"
    - "加入「核心路徑 AT 清單」（無論是否受影響）"
  output: "docs/03_testing/REGRESSION-STRATEGY-{feature}.md"
  ci_integration: "Regression Pipeline 自動讀取 RTM 影響矩陣"
```

---

## 🔍 3.4 產出物審查工作流

### 3.4.1 As-Is 規格審查

**參與者**: sa-analyst（主持）+ dev-senior + sd-architect
**觸發時機**: Stage 1 完成後（SCG-1 前）
**審查項目**:
```yaml
as_is_review:
  accuracy_checks:
    - "As-Is FRD 是否完整描述現有業務邏輯？"
    - "As-Is C4 圖是否反映實際部署架構？"
    - "As-Is ADR 重建是否合理（與程式碼對應）？"
    - "技術債清單是否完整（無遺漏的隱性債務）？"
  red_flags:
    - "FRD 描述與程式碼行為不符"
    - "C4 Container 圖缺少重要元件"
    - "無法確認的歷史決策標記為 ADR-AS-IS-UNKNOWN"
  output: "As-Is 規格審查確認單"
  human_confirmation: "🔴 Human: 現況準確性確認"
```

### 3.4.2 Gap Analysis 審查

**參與者**: sa-analyst（主持）+ pm-po + ba
**觸發時機**: Stage 2 完成後
**審查項目**:
```yaml
gap_analysis_review:
  scope_checks:
    - "功能差距清單是否完整？"
    - "架構差距是否涵蓋所有受影響模組？"
    - "變更風險評估是否合理？"
    - "優先級排序是否符合業務價值？"
  output: "docs/04_planning/GAP-ANALYSIS-{feature}.md 確認版"
  human_confirmation: "🔴 Human: 變更範圍與優先級確認"
```

### 3.4.3 To-Be 規格審查

**參與者**: sd-architect（主持）+ dev-senior + qa-tester
**觸發時機**: Stage 3 完成後（SCG-2 前）
**審查項目**:
```yaml
to_be_review:
  feasibility_checks:
    - "To-Be C4 圖是否技術可行？"
    - "每個 To-Be ADR 的決策理由是否充分？"
    - "變更影響分析是否完整（無遺漏的下游影響）？"
    - "As-Is → To-Be 對照表是否清晰？"
  output: "To-Be SRD 確認版"
  spec_gate: "🔷 SCG-2 通過"
  human_confirmation: "🔴 Human: To-Be 規格凍結"
```

### 3.4.4 ADR 審查

**參與者**: sd-architect（主持）+ dev-senior
**觸發時機**: 每個 ADR 建立後（即時審查）
**審查項目**:
```yaml
adr_review:
  quality_checks:
    - "Context 描述是否完整說明決策背景？"
    - "Decision 是否明確（無模糊語言）？"
    - "Rationale 是否列出被否決的替代方案？"
    - "Consequences 是否誠實列出負面影響？"
  brownfield_specific:
    - "As-Is ADR 是否有程式碼行號或 commit hash 佐證？"
    - "To-Be ADR 是否說明從 As-Is 決策的差異？"
  output: "ADR-INDEX.md 更新"
```

### 3.4.5 API Compat 審查

**參與者**: sd-architect（主持）+ dev-developer + integration-specialist
**觸發時機**: Stage 4 完成後（SCG-3 前）
**審查項目**:
```yaml
api_compat_review:
  breaking_change_checks:
    - "所有 Breaking Changes 是否已明確列出？"
    - "Consumer Side 是否已通知並確認影響？"
    - "廢棄端點是否有足夠的 Sunset Period？"
    - "遷移指南是否可操作？"
  spec_gate: "🔷 SCG-3 通過"
  consumer_sign_off: "🔴 所有 Consumer 確認 Breaking Changes"
```

---

## 📊 Brownfield SDD 健康度指標

| 指標 | 計算方式 | 目標 |
|------|---------|------|
| As-Is 規格完整度 | 已文件化功能 / 實際功能數 | ≥ 90% |
| ADR 考古完整度 | 已重建 ADR / 識別的歷史決策數 | ≥ 80% |
| 技術債覆蓋率 | 已規格化技術債 / 掃描發現技術債 | 100% |
| 回歸測試 RTM 覆蓋 | RTM 指導的回歸 AT / 總回歸 AT | ≥ 80% |

---

## 🔗 相關文件

- [SDD CI/CD Brownfield](../../../docs/08_deployment/SDD_BROWNFIELD_CICD.md)
- [SDD 核心原則](../../../docs/02_architecture/SDD_Core_Principles.md)
- [ADR 範本](../../../docs/02_architecture/adr/ADR-TEMPLATE.md)
- [ADR 索引](../../../docs/02_architecture/adr/ADR-INDEX.md)
- [Phase 03 執行藍圖](../../../docs/04_planning/AISDLC_TO_SDD_Planning_Phase_03.md)
