# Performance Optimization Flow
# 效能優化流程

**版本**: v0.01
**最後更新**: 2026-04-17

---

## Workflow Metadata

```yaml
workflow_metadata:
  name: "performance-optimization-flow"
  version: "v0.01"
  scenario: "performance"
  description: "系統性診斷和優化系統效能，包含基準測試、瓶頸分析、策略制定、優化實施、驗證和監控"
  primary_agent: "performance-engineer-zh.yaml"
  supporting_agents:
    - "sd-architect-zh.yaml"
    - "dev-senior-zh.yaml"
    - "qa-automation-zh.yaml"
    - "devops-engineer-zh.yaml"       # 基礎設施優化、監控體系建立與告警配置
  optional_agents:
    - "code-analyzer-zh.yaml"         # 深入代碼複雜度分析時
    - "security-engineer-zh.yaml"     # 效能優化涉及安全敏感區域時（如認證/加密/支付/DDoS防護）
    - "sd-mobile-architect-zh.yaml"   # 涉及 Android/iOS/macOS 行動端效能優化時
    - "qa-mobile-tester-zh.yaml"      # 涉及行動端效能測試（Cold Start/Frame Rate/掃碼回應）時
  sop_reference: "scenarios/performance/SOP.md"
  trigger_conditions:
    - "效能指標未達標"
    - "使用者投訴回應慢"
    - "系統負載增加"
    - "定期效能審查"
```

---

## 適用場景
- **使用時機**：效能問題診斷、回應時間改善、吞吐量提升
- **適用專案**：效能敏感系統、高負載應用、效能優化專案
- **執行頻率**：按需執行或定期（每月/每季）

---

# 角色與責任

## 主要負責人
**Agent 角色**：Performance-Engineer (Perf)
**責任**：效能分析、瓶頸診斷、優化策略制定

## 參與者（Supporting Agents）
- **SD-Architect (Marcus)**：架構級優化設計
- **Dev-Senior**：代碼級優化實施
- **QA-Automation**：效能測試自動化
- **DevOps-Engineer**：基礎設施優化、監控體系建立與告警配置

## 選用參與者（Optional Agents）
- **Code-Analyzer (CodeX)**：深入代碼複雜度分析
- **Security-Engineer**：安全與效能權衡評估（支付/加密/TLS）
- **SD-Mobile-Architect**：行動端架構優化（Android/iOS/macOS）
- **QA-Mobile-Tester**：行動端效能測試（Cold Start/Frame Rate/掃碼）

---


---

## SDD SCG 閘門整合（v0.01）

> 效能優化以 PBS（Performance Baseline Spec）為基礎，SLO 必須在測試前量化定義。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 效能基準分析 | **SCG-1 準備** | PBS（P50/P99/吞吐量/SLO） |
| 效能架構設計 | **SCG-2 準備** | 效能優化 ADR |
| 效能測試設計 | SCG-3 通過後 | 效能測試規格（基於 PBS） |
| 效能驗證 | **🔴 SCG-5 準備** | PBS Gate 通過 + NFR 達標 |
| 發布前驗證 | **🔴 SCG-6 凍結** | 效能 SLO 達標確認 |

**🔷 整合閘門**：SCG-1（PBS）→ SCG-2（效能架構）→ SCG-5（驗證）→ SCG-6（發布）
**📌 SDD CI/CD 規格**：參考 `cicd/SDD_PERFORMANCE_CICD.md`


---

# 執行步驟

## 步驟 1：啟動與情境確認 (20 分鐘)
**執行者**：Performance-Engineer
**對應 SOP**：階段 1

**作業內容**：
1. 載入 AISDLC_INIT.md，識別 performance 情境
2. 確認效能問題描述與影響範圍
3. 確認目標指標（回應時間/吞吐量/資源使用率）
4. 確認技術棧與部署環境

**確認點** 🔴：情境確認
- 效能問題描述清楚
- 目標指標已定義
- 環境資訊完整

**產出**：情境確認記錄

## 步驟 2：效能基準測試 (40-60 分鐘)
**執行者**：Performance-Engineer + Dev-Senior
**對應 SOP**：階段 2

**作業內容**：
1. 定義效能 KPIs（P50/P95/P99/QPS）
2. 設計測試場景
3. 執行負載測試（JMeter/k6/Artillery）
4. 收集基準數據
5. 分析當前效能

**確認點** 🔴：基準測試確認
- 審查測試場景
- 確認基準數據準確
- 確認目標值合理

**產出**：效能基準報告、負載測試結果、KPI 基準數據

## 步驟 3：瓶頸深度分析 (1-1.5 小時)
**執行者**：Performance-Engineer + SD-Architect (Marcus) + Dev-Senior
> 💡 **可選**：需要深入分析代碼複雜度時，可加入 Code-Analyzer (CodeX)
**對應 SOP**：階段 3

**作業內容**：
1. 應用層分析（CPU/Memory Profiling）
2. 資料庫層分析（慢查詢、索引）
3. 網路層分析（延遲、頻寬）
4. 基礎設施分析（資源使用）
5. Root Cause 分析（5 Whys）

**確認點** 🔴：瓶頸分析確認
- 審查瓶頸清單
- 確認優先級排序
- 確認 Root Cause

**產出**：瓶頸分析報告、Root Cause 分析、優化機會清單

## 步驟 4：優化策略制定 (1-1.5 小時)
**執行者**：Performance-Engineer + SD-Architect (Marcus)
**對應 SOP**：階段 4

**作業內容**：
1. 代碼優化策略（Quick Wins）
2. 資料庫優化策略
3. 快取策略設計
4. 非同步處理策略
5. 架構調整方案（High Impact）
6. ROI 評估

**確認點** 🔴：策略確認
- 審查優化路線圖
- 確認方案選擇
- 確認成本評估

**產出**：優化策略文件、優化路線圖、成本效益分析

## 步驟 5：優化實施指引 (40-60 分鐘)
**執行者**：Dev-Senior + Performance-Engineer
**對應 SOP**：階段 5

**作業內容**：
1. 分階段實施計畫
2. 程式碼範例與最佳實踐
3. 實施檢查清單
4. 常見陷阱提醒

**確認點** 🔴：實施指引確認
- 審查實施計畫
- 確認範例正確
- 確認風險控制措施

**產出**：優化實施計畫、程式碼範例、驗證檢查清單

## 步驟 6：效能驗證與對比 (30-40 分鐘)
**執行者**：QA-Automation + Performance-Engineer
**對應 SOP**：階段 6

**作業內容**：
1. A/B Testing 驗證
2. Regression Testing
3. 效能指標對比（與步驟 2 基準線）
4. ROI 計算

**確認點** 🔴：驗證確認
- 效能達標確認
- 無回歸問題
- ROI 達成

**產出**：效能驗證報告、前後對比分析、ROI 報告

## 步驟 7：監控與持續優化 (30 分鐘)
**執行者**：DevOps-Engineer + Performance-Engineer
**對應 SOP**：階段 7

**作業內容**：
1. 建立監控體系（Prometheus/Grafana）
2. 設定告警規則（依 PBS 中的 SLO 定義）
3. 設定效能預算
4. 建立持續優化機制
5. 配置 **SLO 違反 → PBS 回饋觸發器**（見下方 ACT-009）

**確認點** 🔴：監控方案確認
- 審查監控指標覆蓋範圍
- 確認告警閾值合理（對應 PBS NFR_ID）
- 確認效能預算可執行
- 確認 SLO 違反告警已連結至 NFR/US ID

**產出**：監控方案、告警配置、效能預算、SLO 回饋觸發設定

---

### 🔔 SLO 違反 → PBS 回饋觸發機制（ACT-009）

**目的**：將生產環境 SLO 違反事件，自動回饋至下一 Sprint 的 PBS 更新流程，形成「運行時 → 規格」的閉環。

```yaml
slo_feedback_trigger:
  監控告警條件:
    - "SLO 連續違反 3 次（基於 NFR 定義的閾值）"
    - "P99 回應時間連續 3 次超過 PBS 定義的 SLO"
    
  觸發動作:
    step_1: "讀取違反的 SLO 指標，查詢對應的 NFR_ID（從 PBS 文件）"
    step_2: "查詢 RTM：NFR_ID → US_ID → F_ID（確認影響範圍）"
    step_3: "產出 PBS-REVIEW 任務至 build/reports/performance/PBS-REVIEW-{date}.md"
    step_4: "在下一 Sprint Planning 時，將 PBS-REVIEW 加入 Sprint Backlog"
    
  PBS-REVIEW 內容:
    - "違反的 SLO 指標與實際觀測值"
    - "對應 NFR_ID 與當前 PBS 目標值"
    - "建議：調整 PBS 目標 OR 優化實作"
    - "影響的 US_ID 清單"
    
  NFR_ID_SLO_對應表:
    存放位置: "docs/04_planning/performance/PBS-{SystemName}.md"
    格式: |
      | NFR_ID | SLO 指標 | 目標值 | 告警閾值 | 監控面板連結 |
      |--------|---------|-------|---------|------------|
      | NFR-001 | P99 回應時間 | ≤ 500ms | > 600ms × 3 | {grafana_url} |
```

---

# SOP-Workflow 步驟對照表

| Workflow 步驟 | SOP 階段 | 說明 |
|--------------|---------|------|
| 步驟 1：啟動與情境確認 | 階段 1 | 載入框架、確認情境 |
| 步驟 2：效能基準測試 | 階段 2 | 建立效能 Baseline |
| 步驟 3：瓶頸深度分析 | 階段 3 | 分層瓶頸診斷 |
| 步驟 4：優化策略制定 | 階段 4 | 制定優化路線圖 |
| 步驟 5：優化實施指引 | 階段 5 | 實施計畫與範例 |
| 步驟 6：效能驗證與對比 | 階段 6 | A/B 測試與效能對比 |
| 步驟 7：監控與持續優化 | 階段 7 | 監控告警與持續機制 |

---

# 輸出與交付

## 主要交付物
- 效能基準報告
- 瓶頸分析報告
- 優化策略文件
- 優化實施計畫
- 效能對比報告
- 監控方案

## 交付標準
- 效能目標達成
- 優化可持續
- 監控完整

---

## 📚 參考資源

- [Performance SOP 完整版](../../scenarios/performance/SOP.md)
- [Performance QuickRef 快速參考](../../scenarios/performance/SOP_QuickRef.md)
- [Performance DeepDive 深度指南](../../scenarios/performance/SOP_DeepDive.md)
- [Performance 快速啟動指令集](../../prompts/scenario-prompts/performance-prompts.md)
- [AISDLC_INIT.md](../../AISDLC_SDD_INIT.md)

### 相關 Agents
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（主導）
- [sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（架構優化）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - Senior Developer（代碼優化）
- [qa-automation-zh.yaml](../../agent/specialized/qa-automation-zh.yaml) - QA Automation（效能測試）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps（基礎設施與監控）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（行動端架構優化，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端效能測試，選用）

### 相關 Skills
- `/performance-optimization` - 效能分析與優化
- `/devops-monitoring` - 監控告警系統
- `/integration-redis` - Redis 快取整合
- `/integration-database` - 資料庫架構優化（索引、連線池、讀寫分離）
- `/mobile-development` - 行動端效能優化（涉及 Android/iOS/macOS 時）

---

**版本**: v0.01
**維護者**: AISDLC Framework Team
**最後更新**: 2026-02-17
