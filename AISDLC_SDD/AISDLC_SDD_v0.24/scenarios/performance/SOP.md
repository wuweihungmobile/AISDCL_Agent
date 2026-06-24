# Performance Optimization 效能優化 SOP

**版本**: v0.01 | **最後更新**: 2026-02-17
> 📘 **文檔導航**: [快速參考 QuickRef](./SOP_QuickRef.md) | [深度技術指南 DeepDive](./SOP_DeepDive.md) | [情境轉換指引](../SCENARIO_TRANSITION_GUIDE.md)

> 📝 **關於範例連結說明**:
> 本 SOP 中部分連結（如文檔路徑、配置檔案等）為示例性質，
> 展示一般專案的文檔結構。實際使用時，請根據您的專案結構調整路徑。

## 🎯 情境概述

**適用場景**：系統效能問題診斷與優化、回應時間改善、吞吐量提升、資源使用優化

**預計時間**:
- 📋 **AISDLC 規劃階段**: 3-4 小時
  - **規劃時間** (AI 分析 + 人工確認): 3-4 小時
  - **執行時間** (依專案規模):
    - 小型專案: 1-2 週 (單一瓶頸優化)
    - 中型專案: 2-4 週 (系統級優化)
    - 大型專案: 1-2 月 (架構級優化)
- 🔨 **實際執行階段**: 1-3 週 (依優化複雜度而定)

> 💡 **時間估算說明**:
> - **規劃時間**指使用 AISDLC 流程進行效能分析、瓶頸識別、優化方案設計的時間
> - **執行時間**指實際進行效能優化開發的時間
> - 小型專案指單一瓶頸優化(如 SQL 查詢、快取策略)
> - 中型專案指系統級優化(如資料庫架構、API 設計)
> - 大型專案指架構級優化(如微服務拆分、分散式系統)

**涉及角色**：Performance-Engineer, SD-Architect, Dev-Senior, DevOps-Engineer, QA-Automation ⭐ Phase 2新增; 選用: Security-Engineer（安全敏感區域）

**最終產出**：效能基準報告 + 瓶頸分析報告 + 優化方案 + 優化實作指引 + 效能對比報告 + 監控方案

---

## 🤝 協作模式 (Phase 2: v0.01)

### 主要協作模式

#### 1. Lead-Support (主導-支援) + Iterative-Refinement (迭代精煉)
- **主導 Agent**: Performance-Engineer
- **支援 Agents**: SD-Architect (架構優化), Dev-Senior (代碼優化), QA-Automation ⭐ (效能測試自動化)
- **使用階段**: 全流程
- **模式說明**: Performance-Engineer 主導效能分析和優化循環

#### 2. Iterative-Refinement 循環
```
Performance-Engineer 識別瓶頸
    ↓
SD + Dev-Senior + QA-Automation 提供優化建議
    ↓
Performance-Engineer 實施優化
    ↓
測量驗證（QA-Automation 自動化測試）
    ↓
達標？→ 是 → 🔴 完成
      → 否 → 繼續迭代
```

### 第二階段優化
- **新增**: qa-automation 為 Supporting Agent
- **理由**: 效能測試自動化需要專業支援，持續監控能力
- **貢獻**: 自動化效能測試、持續監控、負載測試腳本

---

> **📋 Workflow 對應**：本 SOP 對應 [performance-optimization-flow](../../workflow/scenario-specific/performance-optimization-flow.md)，
> 該 Workflow 提供 7 個步驟的執行流程與 SOP-Workflow 步驟對照表。

## 📋 前置準備檢查清單

> ⚠️ **重要提示**: 以下前置材料為理想狀態。若材料缺失,請參考「材料缺失應對方案」。

### 必要材料
- [ ] 系統存取權限（Production 或 Staging）
- [ ] 效能問題描述或目標
- [ ] 現有監控數據（如有）
- [ ] 測試環境存取權限
- [ ] 效能測試工具權限

### 選擇性材料
- [ ] 歷史效能數據
- [ ] 使用者回饋和投訴
- [ ] 業務增長數據（QPS 趨勢）
- [ ] 架構圖和資料流圖
- [ ] 第三方服務 SLA
- [ ] 成本預算（如需擴容）

### 環境檢查
- [ ] 可複製 Production 負載到測試環境
- [ ] Profiling 工具可用（APM/tracing）
- [ ] 資料庫慢查詢日誌已啟用
- [ ] 負載測試工具已準備（JMeter/k6/Locust）

---

## 🔧 材料缺失應對方案

> 💡 **現實情況**: 效能優化常在「出現問題後」才啟動,此時可能缺乏完整的監控數據和基準。以下提供實用的替代方案。

| 缺失材料 | 影響程度 | 應對方案 | 預計額外時間 |
|---------|---------|---------|-------------|
| **效能基準數據 (Baseline)** | 🔴 高 | • **方案 1**: 立即建立臨時監控收集 1-3 天基準數據 (使用免費 APM 如 Prometheus + Grafana)<br>• **方案 2**: 從應用日誌分析歷史回應時間 (使用 `awk`/`grep` 或 ELK Stack)<br>• **方案 3**: 從資料庫慢查詢日誌反推效能狀況<br>• **方案 4**: 使用負載測試工具建立當前狀態基準 (k6/Apache Bench) | +0.5-3 天 |
| **監控數據 (Metrics)** | 🔴 高 | • **方案 1**: 快速建立最小監控集 (CPU/Memory/Disk/Network) 使用免費工具<br>• **方案 2**: 使用雲平台內建監控 (AWS CloudWatch/GCP Monitoring/Azure Monitor 基本版免費)<br>• **方案 3**: 啟用應用層面 APM (免費額度: New Relic/Datadog/Elastic APM)<br>• **方案 4**: 使用開源方案: Prometheus + Grafana + Node Exporter | +2-6 小時 |
| **架構圖和資料流圖** | 🟡 中 | • **方案 1**: 使用 Code-Analyzer 生成基本架構圖<br>• **方案 2**: 從部署配置反推架構 (Kubernetes YAML/Docker Compose)<br>• **方案 3**: 使用分散式追蹤工具生成實際呼叫鏈 (Jaeger/Zipkin 免費)<br>• **方案 4**: 訪談團隊快速繪製簡易架構圖 (30-60 分鐘) | +1-3 小時 |
| **歷史效能數據** | 🟡 中 | • **方案 1**: 檢查 Git 歷史中的效能測試報告或 benchmark 結果<br>• **方案 2**: 搜尋 Issue/Ticket 系統中的效能相關回報<br>• **方案 3**: 詢問團隊成員或維運人員的經驗記憶<br>• **方案 4**: 暫時跳過歷史對比,聚焦於「建立未來基準」 | +0.5-1 小時 |
| **真實流量模式** | 🟡 中 | • **方案 1**: 使用流量錄製工具記錄 Production 流量 (GoReplay/tcpdump)<br>• **方案 2**: 從 Web Server 日誌分析流量模式 (nginx/Apache access logs)<br>• **方案 3**: 使用 Google Analytics/Mixpanel 等分析工具推測使用模式<br>• **方案 4**: 建立「典型使用場景」手動測試腳本 | +1-4 小時 |
| **負載測試環境** | 🟡 中 | • **方案 1**: 使用雲平台臨時擴容測試環境 (用完即刪,成本可控)<br>• **方案 2**: 使用本地 Docker/K8s 建立縮小版環境 (資源需求 × 0.3)<br>• **方案 3**: 直接在 Staging 環境測試 (確保不影響其他團隊)<br>• **方案 4**: 使用負載測試 SaaS (如 Loader.io 免費額度) | +1-3 小時 |
| **第三方服務效能數據** | 🟢 低 | • **方案 1**: 查詢第三方服務的狀態頁面 (status.service.com) 和 SLA 文檔<br>• **方案 2**: 在應用層面添加第三方 API 呼叫計時<br>• **方案 3**: 使用網路監控工具測量外部 API 延遲 (Pingdom/UptimeRobot 免費)<br>• **方案 4**: 暫時假設第三方服務正常,後續驗證 | +0.5-1 小時 |

### 完全無監控時的應急方案

若系統完全沒有監控,建議採用「**快速監控啟動 (Quick Monitoring Bootstrap)**」策略:

#### 階段 1: 15 分鐘最小監控 (緊急)
立即建立最基本監控以避免「盲目優化」:

```bash
# 1. 應用層面: 添加簡易計時日誌
# 範例 (Node.js/Express):
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.path} - ${duration}ms`);
  });
  next();
});

# 2. 系統層面: 使用系統工具收集基本指標
top -b -n 1 > baseline-$(date +%Y%m%d-%H%M%S).txt  # CPU/Memory
iostat -x 1 10 > disk-baseline.txt                 # Disk I/O
netstat -s > network-baseline.txt                  # Network

# 3. 資料庫層面: 啟用慢查詢日誌
# MySQL:
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  # 記錄 > 1 秒的查詢

# PostgreSQL:
ALTER SYSTEM SET log_min_duration_statement = 1000;  # 記錄 > 1 秒的查詢
```

#### 階段 2: 1-2 小時基礎監控建立
使用免費開源工具建立可持續監控:

**選項 A: Prometheus + Grafana** (推薦,全功能)
- Prometheus: 指標收集
- Node Exporter: 系統指標
- Grafana: 視覺化儀表板
- 預計時間: 1-2 小時

**選項 B: 雲平台內建監控** (最快)
- AWS CloudWatch / GCP Cloud Monitoring / Azure Monitor
- 基本指標免費,無需配置
- 預計時間: 15-30 分鐘

**選項 C: ELK Stack** (適合已有日誌)
- 從現有應用日誌提取效能數據
- Logstash 解析 → Elasticsearch 儲存 → Kibana 視覺化
- 預計時間: 2-4 小時

#### 階段 3: 建立效能基準 (1-3 天)
- 收集 1-3 天的正常流量數據
- 記錄 P50/P95/P99 延遲
- 識別尖峰和離峰時段差異
- 建立「可接受效能範圍」基準

---

## 🛠️ 免費工具替代方案

> 💡 **成本考量**: 商業APM工具價格高昂（New Relic $99-549/月, Datadog $15-23/host/月），以下提供功能相近的免費/開源替代方案。

### APM與監控工具對照表

| 工具類別 | 商業方案 | 免費/開源替代 | 功能對比 | 適用場景 |
|---------|---------|-------------|---------|---------|
| **APM (應用效能監控)** | New Relic<br>Datadog<br>AppDynamics | **Prometheus + Grafana**<br>**Elastic APM**<br>**SigNoz** | 核心功能齊全<br>缺少: AI分析、自動異常檢測 | 指標收集與視覺化<br>告警與儀表板 |
| **分散式追蹤** | Datadog APM<br>New Relic | **Jaeger**<br>**Zipkin**<br>**OpenTelemetry** | 開源方案完整<br>CNCF標準 | 微服務鏈路追蹤<br>效能瓶頸分析 |
| **前端效能** | SpeedCurve<br>Calibre | **Lighthouse CI**<br>**WebPageTest**<br>**Sitespeed.io** | 功能完整,免費<br>缺少: RUM持續監控 | Core Web Vitals<br>前端效能優化 |
| **負載測試** | LoadRunner<br>BlazeMeter | **k6**<br>**Gatling**<br>**Locust** | 功能強大,免費<br>缺少: 雲端分散式 | 壓力測試<br>效能基準測試 |
| **資料庫監控** | Datadog DB<br>VividCortex | **PMM** (Percona)<br>**pg_stat_statements**<br>**pgBadger** | 開源版功能完整 | 慢查詢分析<br>資料庫優化 |
| **基礎設施監控** | Datadog<br>New Relic Infra | **Prometheus + Node Exporter**<br>**Telegraf + InfluxDB** | 完全免費,CNCF標準 | CPU/Memory/Disk<br>系統資源監控 |

### 推薦工具組合 (依專案規模)

| 專案規模 | APM | 分散式追蹤 | 負載測試 | 前端監控 | 年度成本 |
|---------|-----|-----------|---------|---------|---------|
| **小型** (<10人) | Prometheus + Grafana | - | k6 | Lighthouse CI | $0 |
| **中型** (10-50人) | Prometheus + Grafana + Elastic APM | Jaeger | k6 + InfluxDB + Grafana | Lighthouse CI | $0 (自架) |
| **大型** (50+人) | 開源組合 或 New Relic/Datadog | Jaeger | k6 Cloud | 商業RUM方案 | $0 或 $10k+/年 |

### 成本對比

| 方案 | 月度成本 | 年度成本 | 工具組合 | 維護成本 |
|------|---------|---------|---------|---------|
| **完全免費 (自架)** | $0 | $0 | Prometheus + Grafana + Jaeger + k6 | 中 (需DevOps維護) |
| **混合方案** | $50-200 | $600-2,400 | 基礎免費 + k6 Cloud + Sentry | 低-中 |
| **全商業方案** | $1,000-3,000 | $12k-36k | New Relic/Datadog 全套 | 低 (廠商支援) |

---

## 🎯 Claude Code Skills 整合指引 (v0.01+)

> **🔴 重要**：在效能優化流程中，可透過 Claude Code Skills 快速觸發特定能力。以下列出各階段建議使用的 Skills。

### 各階段建議 Skills

| 階段 | 建議 Skill | 觸發時機 |
|------|-----------|---------|
| 階段 1 啟動 | `/performance-optimization` | 啟動效能優化情境 |
| 階段 2 基準測試 | `/qa-testing` | 效能測試策略制定 |
| 階段 2 基準測試 | `/mobile-development` | 行動端效能基準測試（涉及 Android/iOS/macOS 時） |
| 階段 3 瓶頸分析 | `/dev-review` | 代碼層級效能審查 |
| 階段 3 瓶頸分析 | `/brownfield-analysis` | 現有系統效能瓶頸分析 |
| 階段 4 優化策略 | `/sd-architect` | 架構級優化方案設計 |
| 階段 4 優化策略 | `/integration-database` | 資料庫架構優化規劃（索引、連線池、讀寫分離） |
| 階段 5 實施指引 | `/dev-review` | 優化代碼審查與實作指導 |
| 階段 5 實施指引 | `/integration-redis` | Redis 快取整合 |
| 階段 5 實施指引 | `/mobile-development` | 行動端效能優化實施（涉及 Android/iOS/macOS 時） |
| 階段 6 驗證對比 | `/qa-testing` | 效能回歸測試 |
| 階段 6 驗證對比 | `/performance-optimization` | 效能前後對比分析 |
| 階段 7 監控 | `/devops-monitoring` | 監控告警系統設定 |
| 階段 7 監控 | `/devops-github-actions` | CI/CD 效能測試整合 |
| 階段 3-5 | `/security-audit` | 安全敏感效能場景（支付/加密/TLS）的安全與效能 tradeoff 審查 |

---

## 🔄 開發-編譯-測試循環 (AISDLC 強制規則)

> **🔴 CRITICAL**：依據 AISDLC CLAUDE.md 強制規則，效能優化實施階段必須嚴格遵守以下循環。

```
優化 1 個方法/查詢/配置
    ↓
立即編譯 (Compile/Build)
    ↓
編譯失敗？ → 🔴 立即停止 → 修復 → 重新編譯
    ↓
編譯成功 ✅
    ↓
執行單元測試 + 效能測試 (Unit Test + Performance Test)
    ↓
測試失敗？ → 🔴 立即停止 → 修復 → 重新測試
    ↓
測試通過 ✅ → Commit
    ↓
繼續優化下一個方法/查詢/配置
```

**禁止行為**：
- ❌ 優化多個模組後才編譯
- ❌ 編譯失敗繼續優化其他模組
- ❌ 跳過效能測試直接優化下一個

---

## 🔒 CI/CD 安全基線與增強掃描（強制前置）

> **⚠️ CRITICAL**: 開始效能優化前，必須確認 CI/CD Pipeline 已配置以下安全層級。
> **Performance 情境安全等級: Advanced** (L0 + L1 + SAST 選配 + Container Scan)

### Layer 0: Security Baseline（強制）

所有 PR 必須通過以下檢查：

| 檢查項 | 工具 | 阻塞等級 |
|--------|------|---------|
| Secret Detection | TruffleHog / gitleaks | 🔴 永遠阻塞 |
| Dependency Scan (SCA) | Trivy / npm audit | 🔴 Critical/High 阻塞 |
| License Compliance | license-checker | ⚠️ GPL-3.0/AGPL 阻塞 |

📖 **配置範本**: [Layer0_Security_Baseline_Template.md](../../docs_template/scenario_specific/devops/Layer0_Security_Baseline_Template.md)

### Layer 1: Build & Verify（強制）

| 關卡 | 目的 | 阻塞等級 |
|------|------|---------|
| Lint + Format | 程式碼風格一致性 | 🔴 失敗阻塞 |
| Compile / Build | 編譯成功 | 🔴 失敗阻塞 |
| Unit Test + Coverage | 覆蓋率 ≥ 80% | 🔴 失敗阻塞 |

📖 **配置範本**: [Layer1_Build_Verify_Template.md](../../docs_template/scenario_specific/devops/Layer1_Build_Verify_Template.md)

### 增強安全掃描: SAST 選配 + Container Scan（Advanced 等級）

效能優化工具本身需要安全性驗證，容器化部署需映像掃描。

| 掃描類型 | 工具 | 阻塞策略 | 說明 |
|---------|------|---------|------|
| **SAST** | Semgrep / CodeQL | ⚠️ 選配 | 效能工具自身安全性 |
| **Container Scan** | Trivy / Grype | 🔴 有 Docker 時 | 效能測試環境映像安全 |

📖 **配置範本**: [Security_Scan_Integration_Template.md](../../docs_template/scenario_specific/devops/Security_Scan_Integration_Template.md)

- [ ] Layer 0 Security Baseline 已配置
- [ ] Layer 1 Build & Verify 已配置
- [ ] Container Scan 已配置（有 Docker 時）
- [ ] SAST 已評估是否需要啟用

### ⚡ Performance Benchmark Gate（🔴 強制）

Performance 情境為效能基準關卡的**核心適用情境**，Micro-Benchmark 和 Full Load Test **均為強制**。

| 層級 | 觸發時機 | 耗時 | 阻塞策略 |
|------|---------|------|---------|
| **Micro-Benchmark** | 每次 PR | < 2 分鐘 | 🔴 退化 > 10% 阻塞 |
| **Full Load Test** | Nightly 排程 | 30-60 分鐘 | ⚠️ 結果次日審查 |

**SLA Gate 閾值**:
| 指標 | PR 閾值（Micro） | Nightly 閾值（Full） |
|------|-----------------|-------------------|
| P50 延遲 | 退化 ≤ 10% | ≤ 200ms |
| P95 延遲 | 退化 ≤ 15% | ≤ 500ms |
| P99 延遲 | 退化 ≤ 20% | ≤ 1000ms |
| 吞吐量 | 退化 ≤ 10% | ≥ 1000 RPS |
| 錯誤率 | ≤ 0.1% | ≤ 0.5% |

📖 **配置範本**: [Performance_Benchmark_Gate_Template.md](../../docs_template/scenario_specific/devops/Performance_Benchmark_Gate_Template.md)
📄 **CI 範本**: [perf-benchmark.yml](../../docs_template/scenario_specific/devops/github-actions/perf-benchmark.yml)
🔧 **建置流程**: [devops-setup-flow 步驟 0.8](../../workflow/scenario-specific/devops-setup-flow.md)

- [ ] Micro-Benchmark 工具已選型並配置
- [ ] 退化閾值已設定（P50/P95/P99）
- [ ] Full Load Test (Nightly) 已配置
- [ ] 效能基線快取已建立
- [ ] SLA Gate 閾值已依專案需求調整

### 🔔 Event-Driven Agent Notification（🔴 強制）

> PR 事件通知為強制。情境專屬觸發：benchmark 結果 + SLA gate 閾值通知 + Nightly 效能報告。

📖 **配置範本**: [Event_Driven_Agent_Notification_Template.md](../../docs_template/scenario_specific/devops/Event_Driven_Agent_Notification_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.10](../../workflow/scenario-specific/devops-setup-flow.md)

---

## 🚀 完整執行流程

### 階段 1：啟動和情境確認 (20 分鐘)

#### 步驟 1.1：載入 AISDLC 框架
```
執行指令：
「請載入 AISDLC_INIT.md，我要進行效能優化」

或具體說明：
「請載入 AISDLC_INIT.md，Web API 回應時間過慢需要優化」
「請載入 AISDLC_INIT.md，資料庫查詢效能問題診斷」
「請載入 AISDLC_INIT.md，iOS App 啟動時間優化」
```

#### 步驟 1.2：回答情境識別問題
系統會詢問：
- 效能問題類型（回應時間/吞吐量/資源使用/啟動時間）
- 問題嚴重程度（緊急/嚴重/中度/優化）
- 影響範圍（全系統/特定功能/特定場景）
- 當前指標（如已知）
- 目標指標（期望達成的效能目標）
- 🆕 **是否涉及行動端效能？**（無/Android/iOS/macOS Desktop/多平台）
- 🆕 **是否涉及硬體整合效能？**（無/掃碼槍/手機相機掃碼/NFC/藍牙印表機）
- 🆕 **是否涉及安全敏感效能場景？**（無/支付流程/加密運算/TLS 配置/認證授權）
- 🆕 **是否涉及多業務域共用資源？**（無/共用 DB/共用 Cache/共用 API Gateway）

> **⚠️ 情境觸發指引**：
> - 若涉及行動端效能，載入 `sd-mobile-architect` + `qa-mobile-tester`
> - 若涉及掃碼/硬體效能，載入 `integration-specialist`（掃碼回應時間優化）
> - 若涉及安全敏感效能場景，載入 `security-engineer`（安全與效能 tradeoff 評估）
> - 若涉及多業務域共用 DB，重點分析跨域查詢效能與連線池策略

#### 步驟 1.3：確認載入結果
期待回應：
```
✅ 識別情境：Performance Optimization (效能優化)
✅ 識別問題類型：[您的問題類型]
✅ 載入主導 Agent：Performance-Engineer (Perf)
✅ 載入支援 Agents：SD-Architect, Dev-Senior, QA-Automation
✅ 推薦 Workflow：performance-optimization-flow
準備開始效能基準測試...
```

#### 步驟 1.4：情境確認點 🔴

> 🔴 **人機協作點：情境確認**
>
> **AI 提供**：
> - 識別的效能問題類型與嚴重程度
> - 影響範圍評估
> - 建議的目標指標
> - 載入的 Agent 團隊清單
>
> **人類確認**：
> - [ ] 效能問題類型正確識別
> - [ ] 問題嚴重程度與影響範圍已確認
> - [ ] 目標指標合理可達成
> - [ ] 正確 Agent 團隊已載入
>
> **⚠️ 必須人類確認後才能進入階段 2**

---

### 階段 2：效能基準測試 (Baseline) (40-60 分鐘)

#### 步驟 2.1：定義效能指標
```
執行指令：
「請協助定義效能測試的關鍵指標」
```

#### 步驟 2.2：關鍵效能指標 (KPIs) 定義

**回應時間指標**：
- **P50 (Median)**：50% 請求的回應時間
- **P95**：95% 請求的回應時間（常用 SLA 指標）
- **P99**：99% 請求的回應時間（尾部延遲）
- **Max**：最大回應時間
- **Average**：平均回應時間

**吞吐量指標**：
- **RPS (Requests Per Second)**：每秒請求數
- **TPS (Transactions Per Second)**：每秒交易數
- **QPM/QPS (Queries Per Minute/Second)**：資料庫查詢率
- **Throughput (MB/s)**：資料傳輸量

**資源使用指標**：
- **CPU 使用率**：平均和峰值
- **記憶體使用率**：平均和峰值
- **磁碟 I/O**：IOPS、讀寫速度
- **網路 I/O**：頻寬使用
- **資料庫連線數**：活躍連線、等待連線

**錯誤率指標**：
- **Error Rate**：錯誤請求比例
- **Timeout Rate**：超時比例
- **5xx Rate**：伺服器錯誤比例

**業務指標** (Web/App 專屬)：
- **FCP (First Contentful Paint)**：首次內容繪製
- **LCP (Largest Contentful Paint)**：最大內容繪製
- **TTI (Time to Interactive)**：可互動時間
- **App Launch Time**：應用啟動時間
- **Frame Rate**：畫面更新率 (FPS)

#### 步驟 2.3：基準測試執行 (Performance-Engineer + Dev-Senior)

**測試場景設計**：
1. **正常負載測試**：模擬平均流量
2. **峰值負載測試**：模擬高峰流量（1.5-2x 正常）
3. **壓力測試**：逐步增加負載直到系統崩潰
4. **浸泡測試**：長時間穩定負載（檢查記憶體洩漏）
5. **尖峰測試**：突發流量（秒殺、促銷）

**效能測試類型選擇矩陣**：

> 依專案規模和需求選擇適當的測試類型，**不必全部執行**

| 專案規模 | 必要測試 | 建議測試 | 可選測試 | 預估時間 |
|---------|---------|---------|---------|---------|
| **小型** (MVP/內部工具) | 基準測試 | 負載測試 | - | 2-4 小時 |
| **中型** (一般產品) | 基準測試、負載測試 | 壓力測試 | 尖峰測試 | 4-8 小時 |
| **大型** (高流量/關鍵業務) | 基準測試、負載測試、壓力測試 | 浸泡測試、尖峰測試 | 混沌測試 | 1-2 天 |
| **電商/秒殺** | 基準測試、負載測試、尖峰測試 | 壓力測試 | 浸泡測試 | 8-16 小時 |
| **金融/交易** | 全部必要 | - | 混沌測試 | 2-3 天 |

**選擇指引**：
- 🟢 **時間有限**：僅執行「基準測試 + 負載測試」
- 🟡 **標準流程**：依專案規模選擇「必要 + 建議」
- 🔴 **關鍵系統**：執行全部測試類型

**測試工具選擇**：
- **Backend API**：JMeter, k6, Gatling, Locust
- **Web 前端**：Lighthouse, WebPageTest, Chrome DevTools
- **Mobile App**：Xcode Instruments, Android Profiler
- **資料庫**：sysbench, pgbench, YCSB

**執行步驟**：
```bash
# 範例：使用 k6 進行負載測試
k6 run --vus 100 --duration 5m load-test.js

# 範例：Lighthouse 前端效能測試
lighthouse https://example.com --output html

# 範例：資料庫基準測試
sysbench oltp_read_write --mysql-host=localhost run
```

#### 🆕 技術棧特定效能基準說明

> **Next.js + Spring Boot + PostgreSQL 技術棧常見效能瓶頸與關鍵指標**：

| 技術層 | 常見瓶頸 | 關鍵指標 | 優先檢查工具 |
|--------|---------|---------|------------|
| **Next.js SSR** | RSC 渲染時間長、TTFB 高、大型 JS bundle | TTFB < 200ms, LCP < 2.5s, Bundle < 250KB | Lighthouse, Next.js Analytics |
| **Next.js SSR** | Server Components 過度呼叫 DB / API | Server Component 回應時間 | Next.js DevTools + OpenTelemetry |
| **Spring Boot** | JVM 冷啟動慢（首次請求延遲高） | Cold Start < 5s, JVM Warm-up 後 P95 | JVM Profiler (VisualVM / JFR) |
| **Spring Boot** | GC Stop-the-World 暫停 | GC Pause < 100ms, GC Throughput > 95% | GC Log 分析（`-Xlog:gc*`） |
| **Spring Boot** | HikariCP 連線池耗盡 | 連線等待時間 < 30ms, Pool Utilization < 80% | HikariCP Metrics（Micrometer/Prometheus）|
| **PostgreSQL** | N+1 查詢（JPA/Hibernate 懶載入陷阱） | Slow Query Log（`log_min_duration_statement`） | pgBadger, pg_stat_statements |
| **PostgreSQL** | 缺少索引（全表掃描） | Seq Scan vs Index Scan 比率 | `EXPLAIN ANALYZE` |
| **PostgreSQL** | 多業務域共用 DB 的跨域查詢鎖競爭 | 鎖等待時間（`pg_locks`）、Vacuum 頻率 | `pg_stat_activity` |
| **Android 掃碼** | 相機 API 初始化慢、條碼識別延遲 | 掃碼回應時間 < 300ms, 識別準確率 > 99% | Android Profiler |
| **macOS 掃碼** | HID 掃碼槍輸入延遲、Continuity Camera 延遲 | 掃碼到系統接收 < 100ms | macOS Instruments |

#### 步驟 2.4：基準數據收集與分析 (Performance-Engineer)

**收集數據來源**：
- 負載測試工具報告
- APM 系統數據（New Relic, Datadog, AppDynamics）
- 系統監控數據（Prometheus, Grafana）
- 資料庫慢查詢日誌
- 應用程式日誌
- Profiling 數據（CPU/Memory Profiler）

#### 步驟 2.5：基準測試確認點 (15 分鐘)

> 🔴 **人機協作點：基準測試確認**
>
> **AI 提供**：
> - 效能基準報告（各項 KPI 的當前值、負載測試結果摘要、資源使用分析、錯誤率統計）
> - 效能基準線數據表（正常負載、峰值負載、壓力測試、目標值、差距分析）
> - 瓶頸初步識別（明顯的效能熱點、資源瓶頸、潛在問題區域）
>
> **需人工確認**：
> - ✅ 測試場景是否反映真實使用
> - ✅ 基準數據是否準確可信
> - ✅ 目標值是否合理
> - ✅ 是否需要補充測試場景
>
> **產出文件**：
> - 效能基準報告 (Performance Baseline Report)
> - 負載測試結果 (Load Test Results)
> - KPI 基準數據 (KPI Baseline Data)

---

### 階段 3：瓶頸深度分析 (1-1.5 小時)

#### 步驟 3.1：觸發瓶頸分析
```
執行指令：
「基於基準測試結果，請進行深度瓶頸分析」
```

#### 步驟 3.2：多層次瓶頸分析 (Performance-Engineer + SD-Architect + Dev-Senior)

**Layer 1: 應用層分析**

**代碼層級**：
- CPU Profiling（識別 CPU 密集函式）
- Memory Profiling（記憶體洩漏、過度分配）
- 演算法複雜度問題（O(n²) → O(n log n)）
- 不必要的計算和重複工作
- 同步 vs 非同步問題
- 阻塞式 I/O

**常見問題模式**：
- **N+1 查詢問題**：迴圈中執行資料庫查詢
- **過度序列化**：JSON encode/decode 開銷
- **記憶體洩漏**：未釋放的物件引用
- **大物件分配**：頻繁創建大型物件
- **鎖競爭**：多執行緒鎖等待

**Layer 2: 資料庫層分析**

**查詢效能**：
- 慢查詢日誌分析
- 缺少索引 (Missing Indexes)
- 索引未使用 (Unused Indexes)
- 全表掃描 (Table Scan)
- JOIN 效能問題
- 子查詢優化

**資料庫配置**：
- 連線池設定不當
- 查詢快取配置
- Buffer Pool 大小
- 事務隔離級別過高

**資料設計**：
- 資料表設計不合理
- 過度正規化或反正規化
- 資料類型選擇不當
- 資料量過大（需要分區/分片）

**Layer 3: 網路層分析**

**網路延遲**：
- API 呼叫次數過多（Chatty API）
- Payload 過大
- 缺少壓縮（Gzip/Brotli）
- 缺少 CDN 加速
- DNS 查詢延遲
- SSL/TLS handshake 開銷

**連線管理**：
- 連線池設定不當
- Keep-Alive 未啟用
- HTTP/2 或 HTTP/3 未使用

**Layer 4: 基礎設施層分析**

**硬體資源**：
- CPU 瓶頸（單核心/多核心）
- 記憶體不足（Swap 頻繁）
- 磁碟 I/O 瓶頸（IOPS 不足）
- 網路頻寬限制

**系統配置**：
- 作業系統參數調優
- 檔案描述符限制
- TCP 參數設定
- 容器資源限制不當

**Layer 5: 架構層分析**

**架構問題**：
- 單體架構擴展性限制
- 缺少快取層
- 同步處理應改為非同步
- 缺少負載均衡
- 無狀態設計不足
- 過度集中化（單點瓶頸）

**第三方依賴**：
- 外部 API 呼叫延遲
- 第三方服務不穩定
- 依賴服務未做降級
- 缺少熔斷機制

#### 步驟 3.3：Root Cause 根因分析

使用 **5 Whys 方法**：
```
問題：API 回應時間 P95 達 1200ms

Why 1: 為什麼回應這麼慢？
→ 資料庫查詢耗時 800ms

Why 2: 為什麼資料庫查詢這麼慢？
→ 查詢執行了全表掃描

Why 3: 為什麼會全表掃描？
→ WHERE 條件的欄位沒有索引

Why 4: 為什麼沒有索引？
→ 初期資料量小，未考慮索引

Why 5: 為什麼沒有監控發現？
→ 缺少慢查詢監控機制

根因：缺少效能監控 + 索引規劃不足
```

#### 步驟 3.4：瓶頸分析確認點 (20 分鐘)

> 🔴 **人機協作點：瓶頸分析確認**
>
> **AI 提供**：
> - 瓶頸清單（按影響程度排序：P0/P1/P2，包含瓶頸類型、具體問題、影響程度、優化難度、ROI）
> - 瓶頸視覺化（火焰圖、資料庫查詢執行計畫、網路瀑布圖、資源使用熱力圖）
> - Root Cause 分析（每個瓶頸的根本原因、因果關係鏈、依賴關係）
> - 優化潛力評估（理論最大改善幅度、實際可達成改善幅度、Quick Wins）
>
> **需人工確認**：
> - ✅ 瓶頸識別是否準確
> - ✅ 優先級排序是否合理
> - ✅ Root Cause 分析是否正確
> - ✅ 是否有遺漏的瓶頸
>
> **產出文件**：
> - 瓶頸分析報告 (Bottleneck Analysis Report)
> - Root Cause 分析 (Root Cause Analysis)
> - 優化機會清單 (Optimization Opportunities)
> - 火焰圖和 Profiling 數據

---

### 階段 4：優化策略制定 (1-1.5 小時)

#### 步驟 4.1：觸發策略制定
```
執行指令：
「請針對識別的瓶頸，制定優化策略」
```

#### 步驟 4.2：優化策略選擇 (Performance-Engineer + SD-Architect)

**策略 A：代碼優化 (Code-Level Optimization)**

**演算法優化**：
- 降低時間複雜度（O(n²) → O(n log n) → O(n)）
- 使用更高效的資料結構（Array → HashMap）
- 減少不必要的計算（快取計算結果）
- 惰性載入 (Lazy Loading)

**範例**：
```javascript
// Before: O(n²)
for (let i = 0; i < users.length; i++) {
  for (let j = 0; j < orders.length; j++) {
    if (orders[j].userId === users[i].id) {
      users[i].orders.push(orders[j]);
    }
  }
}

// After: O(n)
const ordersByUser = orders.reduce((acc, order) => {
  (acc[order.userId] = acc[order.userId] || []).push(order);
  return acc;
}, {});
users.forEach(user => {
  user.orders = ordersByUser[user.id] || [];
});
```

**非同步處理**：
- 同步改非同步（提升吞吐量）
- 並行處理（Promise.all）
- 背景任務處理（Queue/Worker）
- Stream 處理（逐塊處理大文件）

**記憶體優化**：
- 減少大物件分配
- 物件池 (Object Pooling)
- 及時釋放資源
- 修復記憶體洩漏

**策略 B：資料庫優化 (Database Optimization)**

**索引優化**：
- 新增缺失的索引
- 複合索引設計
- 移除未使用的索引
- 索引覆蓋查詢 (Covering Index)

**查詢優化**：
```sql
-- Before: N+1 查詢
SELECT * FROM users;
-- 然後對每個 user 查詢 orders

-- After: JOIN 一次查詢
SELECT users.*, orders.*
FROM users
LEFT JOIN orders ON users.id = orders.user_id;
```

- 避免 SELECT *，只查詢需要的欄位
- 使用 EXPLAIN 分析查詢計畫
- 批次查詢代替迴圈查詢
- 分頁查詢大結果集

**資料庫設計優化**：
- 反正規化（減少 JOIN）
- 垂直分割（冷熱資料分離）
- 水平分割（Sharding）
- 讀寫分離（Master-Slave）
- 資料歸檔（歷史資料分離）

> **⚠️ 資料庫分片最佳實踐 (Database Sharding Best Practices)**
>
> 水平分片 (Sharding) 是處理海量資料的關鍵策略,但需慎選分片鍵和策略:
>
> **分片策略對比**:
> | 策略 | 原理 | 優點 | 缺點 | 適用場景 |
> |------|------|------|------|---------|
> | **範圍分片<br>(Range-based)** | 按 ID/時間範圍分片<br>(1-1000萬 → Shard1) | 範圍查詢快<br>易擴展 | 可能熱點不均<br>(新資料集中) | 時序資料<br>(日誌、訂單) |
> | **雜湊分片<br>(Hash-based)** | ID 做 Hash 取模<br>hash(user_id) % N | 資料分佈均勻<br>無熱點 | 範圍查詢慢<br>擴展需 Rehash | 使用者資料<br>(無範圍查詢需求) |
> | **地理分片<br>(Geo-based)** | 按地區分片<br>(亞洲/歐洲/美洲) | 就近存取快<br>合規友善 | 跨區查詢慢<br>資料不均 | 跨國服務<br>(符合資料主權) |
> | **一致性雜湊<br>(Consistent Hash)** | 虛擬節點環<br>最小化 Rehash | 擴展時遷移少<br>(僅 1/N) | 實作複雜 | 快取分片<br>動態擴縮容 |
>
> **分片鍵選擇指南**:
> ```yaml
> shard_key_evaluation:
>   # ✅ 好的分片鍵特徵
>   good_shard_key:
>     - high_cardinality: true  # 高基數 (大量不同值)
>     - even_distribution: true  # 均勻分佈
>     - query_friendly: true  # 常用於查詢條件
>     - immutable: true  # 不可變 (避免跨分片遷移)
>   
>   # ❌ 不好的分片鍵
>   bad_shard_key:
>     - low_cardinality: true  # 低基數 (如性別、狀態)
>     - time_based_only: true  # 僅時間 (新資料熱點)
>     - mutable: true  # 可變 (如使用者等級)
> 
> # 範例: 電商系統分片鍵選擇
> examples:
>   orders_table:
>     good: "user_id"  # 高基數、不可變、常查詢
>     bad: "order_status"  # 低基數 (pending/completed/cancelled)
>   
>   products_table:
>     good: "product_id"  # 高基數、不可變
>     bad: "category"  # 低基數 (可能某類別特別多)
> ```
>
> **實作範例 1: 範圍分片 (訂單表)**
> ```javascript
> // 按訂單 ID 範圍分片
> class OrderShardRouter {
>   constructor() {
>     this.shards = [
>       { name: "shard1", range: [1, 10000000] },
>       { name: "shard2", range: [10000001, 20000000] },
>       { name: "shard3", range: [20000001, 30000000] }
>     ];
>   }
>   
>   getShard(orderId) {
>     return this.shards.find(
>       s => orderId >= s.range[0] && orderId <= s.range[1]
>     );
>   }
>   
>   async getOrder(orderId) {
>     const shard = this.getShard(orderId);
>     return await db[shard.name].orders.findById(orderId);
>   }
>   
>   // 範圍查詢
>   async getOrdersByRange(startId, endId) {
>     const involvedShards = this.shards.filter(s => 
>       !(endId < s.range[0] || startId > s.range[1])
>     );
>     
>     const results = await Promise.all(
>       involvedShards.map(s => 
>         db[s.name].orders.find({ id: { \$gte: startId, \$lte: endId } })
>       )
>     );
>     
>     return results.flat();
>   }
> }
> ```
>
> **實作範例 2: 雜湊分片 (使用者表)**
> ```python
> import hashlib
> 
> class UserShardRouter:
>     def __init__(self, shard_count=4):
>         self.shard_count = shard_count
>         self.shards = [f"shard{i}" for i in range(shard_count)]
>     
>     def get_shard(self, user_id):
>         # 使用 CRC32 雜湊 + 取模
>         hash_value = hashlib.md5(str(user_id).encode()).hexdigest()
>         shard_index = int(hash_value, 16) % self.shard_count
>         return self.shards[shard_index]
>     
>     def get_user(self, user_id):
>         shard = self.get_shard(user_id)
>         return db[shard].users.find_one({"_id": user_id})
>     
>     def create_user(self, user_data):
>         user_id = user_data["_id"]
>         shard = self.get_shard(user_id)
>         return db[shard].users.insert_one(user_data)
> ```
>
> **跨分片查詢處理**:
> ```javascript
> // Scatter-Gather 模式
> async function searchUsers(keyword) {
>   // 1. Scatter: 發送到所有分片
>   const promises = shards.map(shard => 
>     db[shard].users.find({ name: { \$regex: keyword } })
>   );
>   
>   // 2. Gather: 收集結果
>   const results = await Promise.all(promises);
>   const allUsers = results.flat();
>   
>   // 3. Merge: 應用層合併排序
>   return allUsers.sort((a, b) => a.name.localeCompare(b.name));
> }
> 
> // 避免跨分片 JOIN
> // ❌ 壞範例: 跨分片 JOIN
> SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id; // 不可行
> 
> // ✅ 好範例: 反正規化 + 冗餘
> // orders 表冗餘儲存 user_name, user_email
> {
>   order_id: 123,
>   user_id: 456,
>   user_name: "John Doe",  // 冗餘
>   user_email: "john@example.com",  // 冗餘
>   ...
> }
> ```
>
> **分片擴展 (Resharding)**:
> ```yaml
> # 從 4 個分片擴展到 8 個分片
> resharding_strategy:
>   # 方案 A: 停機維護 (適合小型系統)
>   offline:
>     steps:
>       - "1. 停止寫入"
>       - "2. 導出所有資料"
>       - "3. Rehash 並重新分佈"
>       - "4. 導入新分片"
>       - "5. 恢復服務"
>     downtime: "2-4 小時"
>   
>   # 方案 B: 雙寫策略 (適合大型系統)
>   online:
>     steps:
>       - "1. 新增 4 個空分片"
>       - "2. 雙寫: 同時寫入舊分片和新分片位置"
>       - "3. 背景遷移: 逐步搬移舊資料"
>       - "4. 驗證資料一致性"
>       - "5. 切換讀取到新分片"
>       - "6. 停止雙寫,移除舊分片"
>     downtime: "0 (無停機)"
>     duration: "數天到數週"
> ```
>
> **分片管理工具**:
> | 資料庫 | 原生分片支援 | 第三方工具 |
> |-------|------------|-----------|
> | **MongoDB** | ✅ 內建 (Sharded Cluster) | - |
> | **PostgreSQL** | ❌ (需手動或 Citus) | Citus, pg_shard |
> | **MySQL** | ❌ (需中介軟體) | Vitess, ProxySQL, ShardingSphere |
> | **Redis** | ✅ 內建 (Redis Cluster) | Twemproxy, Codis |

**📊 NoSQL 效能優化指引** 🆕 (v0.01 新增)

> **適用對象**：MongoDB、Redis 等 NoSQL 資料庫的效能優化

**MongoDB 效能優化**：

| 優化策略 | 說明 | 效果 |
|---------|------|------|
| **索引優化** | 建立複合索引、覆蓋查詢 | 查詢速度 10-100x |
| **Schema 設計** | 嵌入 vs 參照、反正規化 | 減少 lookup |
| **聚合管線** | $match 早執行、$project 減少欄位 | 記憶體使用減少 |
| **分片策略** | 選擇高基數分片鍵 | 負載均衡 |

**MongoDB 常見效能問題與解法**：
```javascript
// ❌ 低效：未使用索引的查詢
db.users.find({ email: "test@example.com" });

// ✅ 高效：建立索引
db.users.createIndex({ email: 1 });

// ❌ 低效：N+1 查詢 (參照模式)
const user = await User.findById(id);
const orders = await Order.find({ userId: id }); // 另一次查詢

// ✅ 高效：使用 $lookup 或嵌入模式
db.users.aggregate([
  { $match: { _id: ObjectId(id) } },
  { $lookup: { from: "orders", localField: "_id", foreignField: "userId", as: "orders" } }
]);

// ✅ 高效：嵌入模式 (適合一對少)
{
  _id: ObjectId("..."),
  name: "John",
  recentOrders: [{ orderId: "...", amount: 100 }, ...] // 嵌入最近 10 筆
}
```

**MongoDB 效能監控指標**：
```javascript
// 啟用 Profiler 找慢查詢
db.setProfilingLevel(1, { slowms: 100 });

// 查看慢查詢
db.system.profile.find().sort({ ts: -1 }).limit(10);

// 分析查詢計畫
db.collection.find({ ... }).explain("executionStats");
```

---

**Redis 效能優化**：

| 優化策略 | 說明 | 效果 |
|---------|------|------|
| **Key 設計** | 短 Key、統一前綴 | 記憶體節省 10-30% |
| **資料結構選擇** | Hash vs String、Set vs List | 記憶體/效能平衡 |
| **Pipeline** | 批次執行多命令 | 網路延遲減少 |
| **Cluster** | 水平擴展 | 支援更大資料集 |

**Redis 常見效能問題與解法**：
```redis
# ❌ 低效：大量小 Key
SET user:1:name "John"
SET user:1:age "30"
SET user:1:email "john@example.com"

# ✅ 高效：使用 Hash 結構
HSET user:1 name "John" age "30" email "john@example.com"

# ❌ 低效：逐一執行命令
GET key1
GET key2
GET key3

# ✅ 高效：使用 Pipeline
MGET key1 key2 key3

# ❌ 危險：KEYS * 命令 (阻塞)
KEYS user:*

# ✅ 安全：使用 SCAN 命令
SCAN 0 MATCH user:* COUNT 100
```

**Redis 記憶體優化配置**：
```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru  # LRU 淘汰策略

# 壓縮設定 (適合小值)
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
```

**NoSQL 效能檢查清單**：
- [ ] 關鍵查詢都有索引支援
- [ ] 避免全表掃描 (MongoDB: collscan, Redis: KEYS *)
- [ ] 適當的資料結構選擇 (嵌入 vs 參照, Hash vs String)
- [ ] 啟用慢查詢監控
- [ ] 記憶體使用在合理範圍

---

**策略 C：快取策略 (Caching Strategy)**

**快取層次**：
```
Client-Side Cache (瀏覽器快取)
  ↓
CDN Cache (靜態資源)
  ↓
Application Cache (Redis/Memcached)
  ↓
Database Query Cache
  ↓
Database
```

**快取模式**：
- **Cache-Aside**：應用程式管理快取
- **Read-Through**：快取層自動載入
- **Write-Through**：寫入同時更新快取
- **Write-Behind**：非同步寫入資料庫

**快取策略**：
- 熱點資料快取（80/20 法則）
- 計算結果快取
- Session 快取
- 全頁快取 (Full Page Cache)
- Fragment Cache (部分內容快取)

**快取失效策略**：
- TTL (Time To Live)
- LRU (Least Recently Used)
- 主動失效（資料更新時）
- Cache Stampede 防護

> **⚠️ 快取高可用設計 - 雪崩、穿透、擊穿防護 (Cache High Availability)**
>
> 快取失效可能導致系統崩潰,需針對三大問題設計防護機制:
>
> **問題 1: 快取雪崩 (Cache Avalanche)**
> - **定義**: 大量快取同時失效,請求瞬間打到資料庫
> - **觸發場景**: 
>   - 大量 Key 使用相同 TTL
>   - Redis 重啟
>   - 流量高峰期
>
> **防護方案**:
> ```javascript
> // 方案 A: TTL 加上隨機偏移
> function setCache(key, value, baseTTL = 3600) {
>   const randomOffset = Math.floor(Math.random() * 300); // 0-300 秒
>   const ttl = baseTTL + randomOffset; // 避免同時失效
>   redis.setex(key, ttl, JSON.stringify(value));
> }
> 
> // 方案 B: 多層快取 (L1: 記憶體, L2: Redis)
> class TieredCache {
>   constructor() {
>     this.l1Cache = new Map(); // 本地記憶體快取
>     this.l2Cache = redisClient; // Redis
>   }
>   
>   async get(key) {
>     // L1 命中
>     if (this.l1Cache.has(key)) {
>       return this.l1Cache.get(key);
>     }
>     
>     // L2 命中
>     const l2Value = await this.l2Cache.get(key);
>     if (l2Value) {
>       this.l1Cache.set(key, l2Value); // 填充 L1
>       return l2Value;
>     }
>     
>     return null;
>   }
> }
> 
> // 方案 C: 永不過期 + 非同步更新
> async function getCachedData(key) {
>   const cached = await redis.get(key);
>   if (cached) {
>     const data = JSON.parse(cached);
>     // 檢查邏輯過期時間
>     if (Date.now() < data.logicalExpireAt) {
>       return data.value;
>     } else {
>       // 邏輯過期,但仍返回舊值
>       setImmediate(() => refreshCache(key)); // 非同步更新
>       return data.value;
>     }
>   }
>   // 快取未命中
>   return await loadFromDB(key);
> }
> ```
>
> **問題 2: 快取穿透 (Cache Penetration)**
> - **定義**: 查詢不存在的資料,繞過快取直擊資料庫
> - **觸發場景**:
>   - 惡意攻擊 (查詢不存在的 ID)
>   - 業務邏輯錯誤
>
> **防護方案**:
> ```javascript
> // 方案 A: 快取空值 (Null Object Pattern)
> async function getUser(userId) {
>   const cached = await redis.get(`user:${userId}`);
>   if (cached === "NULL") {
>     return null; // 快取的空值
>   }
>   if (cached) {
>     return JSON.parse(cached);
>   }
>   
>   const user = await db.users.findById(userId);
>   if (user) {
>     await redis.setex(`user:${userId}`, 3600, JSON.stringify(user));
>   } else {
>     await redis.setex(`user:${userId}`, 300, "NULL"); // 快取空值 5 分鐘
>   }
>   return user;
> }
> 
> // 方案 B: Bloom Filter (空間高效)
> const { BloomFilter } = require("bloom-filters");
> 
> const userIdFilter = new BloomFilter(10000000, 4); // 1000 萬 ID, 4 個雜湊
> 
> // 初始化: 載入所有存在的 ID
> async function initBloomFilter() {
>   const allUserIds = await db.users.find({}, { _id: 1 });
>   allUserIds.forEach(user => userIdFilter.add(user._id.toString()));
> }
> 
> async function getUser(userId) {
>   // 快速檢查是否可能存在
>   if (!userIdFilter.has(userId)) {
>     return null; // 100% 不存在
>   }
>   // 可能存在,繼續查詢快取和資料庫
>   return await normalGetUser(userId);
> }
> 
> // 方案 C: 請求限流 (Rate Limiting)
> const rateLimit = require("express-rate-limit");
> 
> const limiter = rateLimit({
>   windowMs: 1 * 60 * 1000, // 1 分鐘
>   max: 100, // 最多 100 次請求
>   message: "Too many requests, please try again later"
> });
> 
> app.use("/api/users/:id", limiter);
> ```
>
> **問題 3: 快取擊穿 (Cache Breakdown / Hotkey Problem)**
> - **定義**: 熱點 Key 過期瞬間,大量並發請求擊穿快取
> - **觸發場景**:
>   - 爆款商品快取過期
>   - 熱門內容快取失效
>
> **防護方案**:
> ```javascript
> // 方案 A: 互斥鎖 (Mutex Lock)
> const locks = new Map();
> 
> async function getProduct(productId) {
>   const cached = await redis.get(`product:${productId}`);
>   if (cached) return JSON.parse(cached);
>   
>   // 獲取鎖
>   const lockKey = `lock:product:${productId}`;
>   const locked = await redis.set(lockKey, "1", "EX", 10, "NX"); // 10 秒過期
>   
>   if (locked) {
>     try {
>       // 取得鎖,查詢資料庫
>       const product = await db.products.findById(productId);
>       await redis.setex(`product:${productId}`, 3600, JSON.stringify(product));
>       return product;
>     } finally {
>       await redis.del(lockKey); // 釋放鎖
>     }
>   } else {
>     // 未取得鎖,等待並重試
>     await sleep(50);
>     return await getProduct(productId); // 遞迴重試
>   }
> }
> 
> // 方案 B: 邏輯過期 (見雪崩方案 C)
> 
> // 方案 C: 提前更新熱點資料
> // 使用定時任務提前刷新熱門商品快取
> cron.schedule("*/5 * * * *", async () => {
>   const hotProducts = await getHotProductIds(); // 取得熱門商品 ID
>   for (const id of hotProducts) {
>     const product = await db.products.findById(id);
>     await redis.setex(`product:${id}`, 3600, JSON.stringify(product));
>   }
> });
> ```
>
> **高可用架構範例**:
> ```yaml
> # 完整快取高可用方案
> cache_strategy:
>   # L1: 應用本地快取
>   l1_cache:
>     type: "node-cache"
>     ttl: 60  # 1 分鐘
>     max_keys: 1000
>   
>   # L2: Redis Cluster
>   l2_cache:
>     type: "redis-cluster"
>     nodes: ["redis-1:6379", "redis-2:6379", "redis-3:6379"]
>     ttl_base: 3600
>     ttl_jitter: 300  # 隨機偏移
>   
>   # 防護機制
>   protection:
>     avalanche:
>       - "TTL randomization"
>       - "Logical expiration"
>       - "Tiered caching"
>     
>     penetration:
>       - "Bloom filter"
>       - "Null caching (300s)"
>       - "Rate limiting (100 req/min per IP)"
>     
>     breakdown:
>       - "Mutex lock"
>       - "Logical expiration for hotkeys"
>       - "Proactive refresh (top 100 hotkeys)"
> ```

- Cache Stampede 防護

**策略 D：非同步與佇列 (Async & Queue)**

**適用場景**：
- 耗時任務（圖片處理、報表生成）
- 非即時需求（Email 發送、通知推播）
- 流量削峰（秒殺、促銷）
- 解耦服務

**技術選擇**：
- Message Queue (RabbitMQ, Kafka, Redis Queue)
- Background Job (Sidekiq, Celery, Bull)
- Event-Driven Architecture
- CQRS (Command Query Responsibility Segregation)

**策略 E：擴容與架構調整 (Scaling & Architecture)**

**垂直擴容 (Scale Up)**：
- 增加 CPU/記憶體/磁碟
- 優點：簡單直接
- 缺點：有上限、成本高、單點故障

**水平擴容 (Scale Out)**：
- 增加伺服器數量
- 負載均衡 (Load Balancer)
- 無狀態設計
- 優點：理論無限擴展
- 缺點：架構複雜度增加

**架構模式**：
- **微服務化**：服務拆分，獨立擴展
- **CQRS**：讀寫分離
- **Event Sourcing**：事件驅動
- **Serverless**：按需擴展

**CDN 與邊緣計算**：
- 靜態資源 CDN 加速
- 動態內容邊緣快取
- Edge Computing

#### 步驟 4.3：優化方案設計

針對每個瓶頸制定具體方案：

**範例：資料庫查詢優化方案**
```
瓶頸：users 表查詢慢 (800ms)

方案 1：新增索引 (Quick Win)
- 在 email 欄位新增索引
- 在 created_at 欄位新增索引
- 複合索引 (status, created_at)
- 預估改善：800ms → 50ms (-93%)
- 實作時間：1 小時
- 風險：低

方案 2：查詢改寫
- 避免 SELECT *
- 移除不必要的 JOIN
- 分頁查詢優化
- 預估改善：50ms → 20ms (-60%)
- 實作時間：2 小時
- 風險：中

方案 3：快取熱點資料
- Redis 快取 用戶基本資訊
- TTL 設定 5 分鐘
- 快取命中率預估 80%
- 預估改善：20ms → 4ms (快取命中時)
- 實作時間：4 小時
- 風險：中（需處理快取一致性）
```

#### 步驟 4.4：優化策略確認點 (20 分鐘)

> 🔴 **人機協作點：優化策略確認**
>
> **AI 提供**：
> - 優化路線圖（Phase 1: Quick Wins、Phase 2: 中期優化、Phase 3: 架構升級）
> - 優化方案清單（方案、預估改善、實作時間、風險、ROI、優先級）
> - 成本評估（開發成本、基礎設施成本、維護成本、ROI 計算）
> - 風險評估（技術風險、業務風險、緩解措施）
>
> **需人工確認**：
> - ✅ 優化策略是否合適
> - ✅ 優先級排序是否正確
> - ✅ 預估改善是否合理
> - ✅ 成本是否可接受
> - ✅ 風險是否可控
>
> **產出文件**：
> - 優化策略文件 (Optimization Strategy)
> - 優化路線圖 (Optimization Roadmap)
> - 成本效益分析 (Cost-Benefit Analysis)
> - 風險評估 (Risk Assessment)

---

### 階段 5：優化實施指引 (40-60 分鐘)

#### 步驟 5.1：觸發實施規劃
```
執行指令：
「請制定詳細的優化實施步驟和程式碼範例」
```

#### 步驟 5.2：分階段實施計畫 (Dev-Senior + Performance-Engineer)

**Phase 1: Quick Wins** (1-2 天)

```
步驟 1.1：資料庫索引優化 (2 小時)
[ ] 分析慢查詢日誌
[ ] 設計索引方案
[ ] 在測試環境驗證
[ ] Production 部署（維護窗口）
[ ] 驗證效能改善

步驟 1.2：啟用 Gzip 壓縮 (1 小時)
[ ] 配置 Web Server (Nginx/Apache)
[ ] 測試壓縮率
[ ] 部署到 Production
[ ] 驗證檔案大小降低

步驟 1.3：靜態資源 CDN (2 小時)
[ ] 設定 CDN (CloudFlare/CloudFront)
[ ] 配置 DNS
[ ] 驗證資源從 CDN 載入
[ ] 測試回源機制
```

**Phase 2: 代碼與快取優化** (1-2 週)

```
步驟 2.1：解決 N+1 查詢問題 (4 小時)
[ ] 識別所有 N+1 查詢點
[ ] 改寫為 JOIN 或 Eager Loading
[ ] 補充單元測試
[ ] 效能測試驗證
[ ] Code Review
[ ] 部署

步驟 2.2：引入 Redis 快取 (1-2 天)
[ ] 設計快取架構
[ ] 識別快取熱點
[ ] 實作快取層
[ ] 快取失效策略
[ ] 監控快取命中率
[ ] 灰度部署

步驟 2.3：演算法優化 (2-3 天)
[ ] Profiling 找出 CPU 熱點
[ ] 優化時間複雜度
[ ] Benchmark 驗證
[ ] 功能測試
[ ] 部署驗證
```

**Phase 3: 架構升級** (1-2 月，可選)

```
步驟 3.1：讀寫分離 (1 週)
[ ] 設定 Database Replication
[ ] 應用程式支援讀寫分離
[ ] 處理複製延遲
[ ] 監控主從同步
[ ] 部署驗證

步驟 3.2：微服務拆分 (2-4 週)
[ ] 服務邊界設計
[ ] API Gateway 設定
[ ] 服務間通訊機制
[ ] 逐步遷移功能
[ ] 監控與 Tracing
```

#### 步驟 5.3：程式碼範例與最佳實踐

**範例 1：資料庫索引**
```sql
-- 分析慢查詢
EXPLAIN ANALYZE
SELECT * FROM users
WHERE email = 'user@example.com'
AND status = 'active';

-- 新增複合索引
CREATE INDEX idx_users_email_status
ON users(email, status);

-- 驗證使用索引
EXPLAIN ANALYZE
SELECT * FROM users
WHERE email = 'user@example.com'
AND status = 'active';
-- 應該看到 "Index Scan using idx_users_email_status"
```

**範例 2：解決 N+1 查詢 (Node.js + Sequelize)**
```javascript
// Before: N+1 查詢
const users = await User.findAll();
for (const user of users) {
  user.orders = await Order.findAll({
    where: { userId: user.id }
  });
}

// After: Eager Loading
const users = await User.findAll({
  include: [{
    model: Order,
    as: 'orders'
  }]
});
```

**範例 3：Redis 快取實作**
```javascript
// Cache-Aside Pattern
async function getUser(userId) {
  // 1. 嘗試從快取讀取
  const cached = await redis.get(`user:${userId}`);
  if (cached) {
    return JSON.parse(cached);
  }

  // 2. 快取未命中，從 DB 讀取
  const user = await db.users.findById(userId);

  // 3. 寫入快取（TTL 5分鐘）
  await redis.setex(
    `user:${userId}`,
    300,
    JSON.stringify(user)
  );

  return user;
}

// 更新時主動失效
async function updateUser(userId, data) {
  await db.users.update(userId, data);
  await redis.del(`user:${userId}`); // 失效快取
}
```

**範例 4：非同步處理**
```javascript
// Before: 同步發送 Email（阻塞回應）
app.post('/register', async (req, res) => {
  const user = await createUser(req.body);
  await sendWelcomeEmail(user.email); // 阻塞 500ms
  res.json({ success: true });
});

// After: 非同步處理
const queue = new Queue('emails');

app.post('/register', async (req, res) => {
  const user = await createUser(req.body);
  await queue.add('welcome', { email: user.email }); // 立即返回
  res.json({ success: true });
});

// Worker 處理
queue.process('welcome', async (job) => {
  await sendWelcomeEmail(job.data.email);
});
```

#### 步驟 5.4：實施檢查清單

**優化前檢查**：
- [ ] Benchmark 基準已建立
- [ ] 程式碼已備份 / Git branch 已建立
- [ ] 測試環境已驗證優化效果
- [ ] 回滾計畫已準備
- [ ] 監控告警已設定

**優化中檢查**：
- [ ] 逐步優化，每次改動可驗證
- [ ] 持續執行效能測試
- [ ] 監控資源使用變化
- [ ] 功能測試確保無退化

**優化後檢查**：
- [ ] 效能測試確認改善
- [ ] 功能測試全部通過
- [ ] 監控無異常告警
- [ ] 效能對比報告已生成
- [ ] 文檔已更新

#### 步驟 5.5：實施指引確認點 (15 分鐘)

> 🔴 **人機協作點：實施指引確認**
>
> **AI 提供**：
> - 詳細實施步驟（每個優化的具體執行步驟）
> - 程式碼範例集（關鍵優化的實作範例）
> - 部署計畫（部署時間、順序、風險控制）
> - 驗證方法（如何驗證優化效果）
> - 回滾方案（出問題時如何回滾）
>
> **需人工確認**：
> - ✅ 實施步驟是否清晰可執行
> - ✅ 程式碼範例是否正確
> - ✅ 部署計畫是否合理
> - ✅ 驗證方法是否充分
> - ✅ 回滾方案是否可行
>
> **產出文件**：
> - 優化實施計畫 (Implementation Plan)
> - 程式碼範例集 (Code Examples)
> - 部署腳本 (Deployment Scripts)
> - 驗證檢查清單 (Validation Checklist)

---

### 階段 6：效能驗證與對比 (30-40 分鐘)

#### 步驟 6.1：觸發效能驗證
```
執行指令：
「請制定優化後的效能驗證計畫」
```

#### 步驟 6.2：驗證策略 (QA-Automation + Performance-Engineer)

**A/B Testing 驗證**：
- 部分流量使用優化版本
- 對比優化前後效能
- 逐步放量（10% → 50% → 100%）
- 監控關鍵指標

**Regression Testing**：
- 所有功能測試通過
- 效能測試套件執行
- 邊界條件測試
- 壓力測試

**效能指標對比**：
- 相同負載下的指標對比
- 各 Percentile 改善幅度
- 資源使用變化
- 錯誤率變化

#### 步驟 6.3：對比報告生成

**量化指標對比**：

| 指標 | 優化前 | 優化後 | 改善幅度 | 目標 | 達成率 |
|------|--------|--------|---------|------|--------|
| P50 回應時間 | 450ms | 80ms | ↓ 82.2% | <100ms | ✅ 達標 |
| P95 回應時間 | 1200ms | 180ms | ↓ 85.0% | <300ms | ✅ 達標 |
| P99 回應時間 | 2500ms | 450ms | ↓ 82.0% | <500ms | ✅ 達標 |
| QPS | 1200 | 4500 | ↑ 275% | 3000 | ✅ 超標 |
| CPU 使用率 | 85% | 45% | ↓ 47.1% | <70% | ✅ 達標 |
| Memory 使用 | 75% | 60% | ↓ 20.0% | <70% | ✅ 達標 |
| 錯誤率 | 2.3% | 0.05% | ↓ 97.8% | <0.1% | ✅ 達標 |
| DB 查詢時間 | 800ms | 25ms | ↓ 96.9% | <50ms | ✅ 達標 |

**視覺化對比**：
- 回應時間分佈圖（Before vs After）
- QPS 趨勢對比
- 資源使用對比
- 火焰圖對比

**成本效益分析**：
```
投入成本：
- 開發時間：40 小時 × $50/hr = $2,000
- 基礎設施：Redis 伺服器 $50/月
- 總計：$2,000 + $50/月

效益：
- QPS 提升 275%，可支撐 3.75x 流量
- 延遲伺服器擴容需求 6-12 月
- 節省硬體成本：$500/月
- 使用者體驗改善 → 轉換率提升估計 5%
- ROI：($500 - $50) × 12 / $2,000 = 270% 年化回報
```

#### 步驟 6.4：效能驗證確認點 (10 分鐘)

> 🔴 **人機協作點：效能驗證確認**
>
> **AI 提供**：
> - 效能對比報告（所有指標的前後對比）
> - 目標達成分析（哪些目標已達成、哪些未達成）
> - 視覺化圖表（直觀展示改善成果）
> - ROI 報告（投資回報計算）
> - 問題與建議（還有哪些優化空間）
>
> **需人工確認**：
> - ✅ 效能改善是否達到預期
> - ✅ 目標達成率是否滿意
> - ✅ ROI 是否符合商業期望
> - ✅ 是否需要進一步優化
>
> **產出文件**：
> - 效能驗證報告 (Performance Validation Report)
> - 前後對比分析 (Before/After Analysis)
> - ROI 報告 (Return on Investment Report)
> - 優化成果總結 (Optimization Summary)

---

### 階段 7：監控與持續優化 (30 分鐘)

#### 步驟 7.1：建立效能監控
```
執行指令：
「請設計效能監控和告警方案」
```

#### 步驟 7.2：監控體系建立 (DevOps-Engineer + Performance-Engineer)

**監控層次**：

**Layer 1: 基礎設施監控**
- CPU / Memory / Disk / Network
- 工具：Prometheus, Grafana, CloudWatch
- 告警閾值：CPU > 80%, Memory > 85%

**Layer 2: 應用程式監控 (APM)**
- 回應時間、吞吐量、錯誤率
- 分散式追蹤 (Distributed Tracing)
- 工具：New Relic, Datadog, Elastic APM
- 告警：P95 > 300ms, Error Rate > 0.5%

**Layer 3: 業務指標監控**
- 轉換率、使用者活躍度
- 核心業務流程效能
- 自定義業務指標

**Layer 4: 日誌監控**
- 錯誤日誌聚合
- 慢查詢日誌
- 工具：ELK Stack, Splunk
- 告警：特定錯誤模式

**監控儀表板設計**：
```
Dashboard: API 效能監控
├── 回應時間 (P50/P95/P99)
├── QPS / TPS
├── 錯誤率
├── 資源使用 (CPU/Memory)
├── 資料庫效能
│   ├── 查詢時間
│   ├── 連線數
│   └── 慢查詢統計
├── 快取效能
│   ├── 命中率
│   ├── 記憶體使用
│   └── Eviction 率
└── 依賴服務健康度
```

**告警策略**：
- 分級告警（Critical / Warning / Info）
- 多渠道通知（Email / Slack / PagerDuty）
- 告警收斂（避免告警風暴）
- On-call 輪值

#### 步驟 7.3：效能退化預防

**自動化效能測試**：
- CI/CD Pipeline 整合效能測試
- Pull Request 效能回歸檢查
- 定期效能基準測試（每週/每月）

**效能預算 (Performance Budget)**：
```javascript
// 範例：效能預算配置
{
  "api_response_time_p95": 300,  // ms
  "bundle_size": 200,             // KB
  "time_to_interactive": 3000,    // ms
  "lighthouse_score": 90          // 0-100
}
```

- 超過預算時 CI 失敗
- 強制開發者重視效能

> **📊 Performance Budget 完整指引**
>
> **什麼是 Performance Budget？**
> - 定義網頁/API 效能的「可接受上限」
> - 在 CI/CD 中強制執行，超過預算即失敗
> - 讓效能成為開發流程的一等公民
>
> **🎯 預算類型與建議值**
>
> | 預算類型 | 指標 | 建議值 | 測量工具 |
> |---------|------|-------|---------|
> | **載入時間** | Time to Interactive (TTI) | <3.5s (3G) | Lighthouse |
> | **載入時間** | First Contentful Paint (FCP) | <1.8s | WebPageTest |
> | **核心體驗** | Largest Contentful Paint (LCP) | <2.5s | CrUX |
> | **核心體驗** | Cumulative Layout Shift (CLS) | <0.1 | CrUX |
> | **核心體驗** | Interaction to Next Paint (INP) | <200ms | CrUX |
> | **資源大小** | JavaScript Bundle | <200KB (gzipped) | webpack-bundle-analyzer |
> | **資源大小** | CSS Bundle | <50KB (gzipped) | bundlesize |
> | **資源大小** | 圖片總量 | <500KB | Lighthouse |
> | **API 效能** | Response Time (P95) | <300ms | APM Tools |
> | **API 效能** | Error Rate | <1% | Prometheus |
>
> **🛠️ CI/CD 整合範例 (GitHub Actions)**
>
> ```yaml
> # .github/workflows/performance-budget.yml
> name: Performance Budget Check
> on: [pull_request]
> jobs:
>   lighthouse:
>     runs-on: ubuntu-latest
>     steps:
>       - uses: actions/checkout@v4
>       - name: Build
>         run: npm run build
>       - name: Lighthouse CI
>         uses: treosh/lighthouse-ci-action@v10
>         with:
>           budgetPath: ./budget.json
>           uploadArtifacts: true
>           temporaryPublicStorage: true
>
>   bundle-size:
>     runs-on: ubuntu-latest
>     steps:
>       - uses: actions/checkout@v4
>       - name: Check Bundle Size
>         uses: siddharthkp/bundlesize2@v1
>         with:
>           github_token: ${{ secrets.GITHUB_TOKEN }}
> ```
>
> **📋 budget.json 完整配置**
>
> ```json
> [
>   {
>     "path": "/*",
>     "resourceSizes": [
>       { "resourceType": "script", "budget": 200 },
>       { "resourceType": "stylesheet", "budget": 50 },
>       { "resourceType": "image", "budget": 500 },
>       { "resourceType": "total", "budget": 1000 }
>     ],
>     "timings": [
>       { "metric": "interactive", "budget": 3500 },
>       { "metric": "first-contentful-paint", "budget": 1800 },
>       { "metric": "largest-contentful-paint", "budget": 2500 }
>     ]
>   }
> ]
> ```
>
> **🔄 預算調整策略**
>
> | 情境 | 建議做法 |
> |------|---------|
> | **新專案** | 設定嚴格預算，從一開始養成好習慣 |
> | **既有專案** | 以目前值 +10% 為起點，逐步收緊 |
> | **預算超標** | 分析原因 → 優化 or 申請例外（需 Tech Lead 核准）|
> | **持續達標** | 每季檢視，考慮收緊預算 |
>
> **⚠️ 預算超標處理流程**
>
> ```
> PR 提交 → CI 檢查失敗（超過預算）
>     ↓
> 開發者選擇：
> (A) 優化程式碼直到符合預算
> (B) 申請例外（填寫 Performance Budget Exception Form）
>     ↓
> Tech Lead 審核例外申請
>     ↓
> 核准 → 記錄技術債，設定改善期限
> 拒絕 → 必須優化後才能合併
> ```

**Code Review 效能檢查清單**：
- [ ] 是否引入 N+1 查詢
- [ ] 是否有不必要的迴圈
- [ ] 大量資料是否分頁處理
- [ ] 是否有記憶體洩漏風險
- [ ] 資料庫查詢是否有索引支援

#### 步驟 7.4：持續優化文化

**定期效能審查**：
- 每季度效能健檢
- 識別新的瓶頸
- 技術債清理
- 架構演進規劃

**效能知識分享**：
- 內部分享會
- 效能優化 Playbook
- 最佳實踐文檔
- Case Study 累積

#### 步驟 7.5：監控方案確認點 (10 分鐘)

> 🔴 **人機協作點：監控方案確認**
>
> **AI 提供**：
> - 監控體系架構與告警規則
> - 效能預算設定
> - 持續優化機制建議
>
> **人類確認**：
> - [ ] 監控指標覆蓋關鍵效能面向
> - [ ] 告警閾值合理
> - [ ] 效能預算可執行
> - [ ] 持續優化流程可落地
>
> **產出文件**：
> - 監控方案 (Monitoring Plan)
> - 告警配置 (Alert Configuration)
> - 效能預算 (Performance Budget)
> - 持續優化指南 (Continuous Optimization Guide)

---

## 🎯 成功標準

### 效能目標達成
- [ ] 所有 P0 優化已完成
- [ ] 關鍵指標達到或超越目標
- [ ] 無效能退化
- [ ] 無新增錯誤或 Bug

### 可持續性
- [ ] 監控告警已建立
- [ ] 效能預算已設定
- [ ] 自動化測試已整合
- [ ] 團隊知識已轉移

### 成本效益
- [ ] ROI 為正
- [ ] 符合預算
- [ ] 長期維護成本可接受

### 文檔完整性
- [ ] 優化方案已記錄
- [ ] 監控手冊已完成
- [ ] Troubleshooting Guide 已更新
- [ ] 知識已分享

---

## 📊 時間分配參考

| 階段 | 預估時間 | 可彈性調整 |
|------|---------|-----------|
| 啟動和情境確認 | 20 分鐘 | ±5 分鐘 |
| 效能基準測試 | 40-60 分鐘 | 視系統複雜度 |
| 瓶頸深度分析 | 1-1.5 小時 | 視問題數量 |
| 優化策略制定 | 1-1.5 小時 | - |
| 優化實施指引 | 40-60 分鐘 | - |
| 效能驗證與對比 | 30-40 分鐘 | - |
| 監控與持續優化 | 30 分鐘 | - |
| **準備階段總計** | **3-4 小時** | |
| **實際優化執行** | 2 天 - 2 週 | 依複雜度 |

---

## 🎨 前端效能優化專項 (Frontend Performance Optimization)

> **⚠️ Core Web Vitals 優化指南 (FCP / LCP / TTI / CLS / FID)**
>
> Google Core Web Vitals 是前端效能的關鍵指標,直接影響 SEO 和使用者體驗:
>
> **指標定義與目標值**:
> | 指標 | 全名 | 定義 | 良好 | 需改善 | 差 | 影響 |
> |------|------|------|------|--------|-----|------|
> | **FCP** | First Contentful Paint | 首次內容繪製 | <1.8s | 1.8-3s | >3s | 首屏速度感知 |
> | **LCP** | Largest Contentful Paint | 最大內容繪製 | <2.5s | 2.5-4s | >4s | 主要內容載入 |
> | **TTI** | Time to Interactive | 可互動時間 | <3.8s | 3.8-7.3s | >7.3s | 互動流暢度 |
> | **CLS** | Cumulative Layout Shift | 累積版面位移 | <0.1 | 0.1-0.25 | >0.25 | 視覺穩定性 |
> | **FID** | First Input Delay | 首次輸入延遲 | <100ms | 100-300ms | >300ms | 互動反應速度 |
> | **INP** | Interaction to Next Paint | 互動到下次繪製 | <200ms | 200-500ms | >500ms | 互動體驗 (新指標) |
>
> **優化策略 1: FCP / LCP (載入速度)**
>
> ```javascript
> // 1. 資源優先級提示
> // HTML <head>
> <link rel="preconnect" href="https://fonts.googleapis.com"> // 提前連線
> <link rel="dns-prefetch" href="https://api.example.com"> // DNS 預解析
> <link rel="preload" href="/hero-image.jpg" as="image"> // 預載入關鍵資源
> 
> // 2. 圖片優化
> <picture>
>   <source srcset="hero.webp" type="image/webp"> // WebP 格式
>   <source srcset="hero.avif" type="image/avif"> // AVIF 格式 (更小)
>   <img src="hero.jpg" alt="Hero" loading="lazy"> // 懶載入
> </picture>
> 
> // 3. 代碼分割 (Code Splitting)
> // React 範例
> const HeavyComponent = React.lazy(() => import("./HeavyComponent"));
> 
> function App() {
>   return (
>     <Suspense fallback={<Loading />}>
>       <HeavyComponent />
>     </Suspense>
>   );
> }
> 
> // 4. 關鍵 CSS 內聯
> <style>
>   /* Critical CSS: 首屏必要樣式內聯在 <head> */
>   .hero { display: flex; height: 100vh; }
> </style>
> <link rel="stylesheet" href="/styles.css" media="print" onload="this.media=\"all\""> // 非關鍵 CSS 延遲載入
> 
> // 5. 字體優化
> <link rel="preload" href="/fonts/main.woff2" as="font" type="font/woff2" crossorigin>
> <style>
>   @font-face {
>     font-family: "Main";
>     src: url("/fonts/main.woff2") format("woff2");
>     font-display: swap; /* 避免 FOIT (Flash of Invisible Text) */
>   }
> </style>
> ```
>
> **優化策略 2: CLS (版面穩定性)**
>
> ```html
> <!-- ❌ 壞範例: 未設定尺寸,載入時會位移 -->
> <img src="banner.jpg" alt="Banner">
> 
> <!-- ✅ 好範例: 明確設定寬高 -->
> <img src="banner.jpg" alt="Banner" width="1200" height="400">
> 
> <!-- ✅ 更好: 使用 aspect-ratio -->
> <img src="banner.jpg" alt="Banner" style="aspect-ratio: 16/9; width: 100%;">
> 
> <!-- ✅ 預留廣告空間 -->
> <div class="ad-slot" style="min-height: 250px;">
>   <!-- 廣告腳本載入 -->
> </div>
> 
> <!-- CSS 動畫使用 transform 而非 top/left -->
> <style>
>   /* ❌ 會觸發 Layout */
>   .box { animation: move 1s; }
>   @keyframes move { from { top: 0; } to { top: 100px; } }
>   
>   /* ✅ 不觸發 Layout */
>   .box { animation: move 1s; }
>   @keyframes move { from { transform: translateY(0); } to { transform: translateY(100px); } }
> </style>
> ```
>
> **優化策略 3: FID / INP (互動反應)**
>
> ```javascript
> // 1. 避免長任務 (Long Tasks > 50ms)
> function processLargeArray(data) {
>   // ❌ 壞範例: 一次處理,阻塞主執行緒
>   const results = data.map(item => expensiveOperation(item));
>   return results;
> }
> 
> // ✅ 好範例: 分批處理
> async function processLargeArray(data, batchSize = 100) {
>   const results = [];
>   for (let i = 0; i < data.length; i += batchSize) {
>     const batch = data.slice(i, i + batchSize);
>     results.push(...batch.map(item => expensiveOperation(item)));
>     await new Promise(resolve => setTimeout(resolve, 0)); // 讓出控制權
>   }
>   return results;
> }
> 
> // 2. 使用 Web Worker 處理複雜計算
> // main.js
> const worker = new Worker("worker.js");
> worker.postMessage({ data: largeDataset });
> worker.onmessage = (e) => {
>   console.log("Result:", e.data);
> };
> 
> // worker.js
> self.onmessage = (e) => {
>   const result = expensiveOperation(e.data);
>   self.postMessage(result);
> };
> 
> // 3. 節流 (Throttle) 和防抖 (Debounce)
> // 滾動事件節流
> let throttleTimer;
> window.addEventListener("scroll", () => {
>   if (throttleTimer) return;
>   throttleTimer = setTimeout(() => {
>     handleScroll();
>     throttleTimer = null;
>   }, 100); // 每 100ms 最多執行一次
> });
> 
> // 搜尋輸入防抖
> let debounceTimer;
> input.addEventListener("input", (e) => {
>   clearTimeout(debounceTimer);
>   debounceTimer = setTimeout(() => {
>     search(e.target.value);
>   }, 300); // 停止輸入 300ms 後才執行
> });
> ```
>
> **整合測試與監控**:
>
> ```yaml
> # 效能測試工具
> testing_tools:
>   # 開發階段
>   development:
>     - tool: "Lighthouse (Chrome DevTools)"
>       usage: "本地測試"
>       command: "lighthouse https://localhost:3000 --view"
>     
>     - tool: "WebPageTest"
>       usage: "多地點/多設備測試"
>       url: "https://www.webpagetest.org"
>   
>   # CI/CD 整合
>   ci_cd:
>     - tool: "Lighthouse CI"
>       config: ".lighthouserc.json"
>       command: "lhci autorun"
>       fail_threshold:
>         performance: 90
>         accessibility: 90
>         best-practices: 90
>         seo: 90
>     
>     - tool: "Bundle Size Check"
>       command: "bundlesize"
>       config:
>         - path: "dist/main.js"
>           maxSize: "250 kB"
>   
>   # 生產環境監控
>   production:
>     - tool: "Google Analytics 4"
>       metrics: ["FCP", "LCP", "CLS", "FID"]
>     
>     - tool: "Sentry Performance"
>       features: ["Transaction tracing", "Web Vitals"]
>     
>     - tool: "Cloudflare Web Analytics"
>       features: ["RUM", "Core Web Vitals"]
> 
> # .lighthouserc.json
> {
>   "ci": {
>     "collect": {
>       "url": ["http://localhost:3000/"],
>       "numberOfRuns": 3
>     },
>     "assert": {
>       "assertions": {
>         "categories:performance": ["error", {"minScore": 0.9}],
>         "first-contentful-paint": ["error", {"maxNumericValue": 2000}],
>         "largest-contentful-paint": ["error", {"maxNumericValue": 2500}],
>         "cumulative-layout-shift": ["error", {"maxNumericValue": 0.1}]
>       }
>     }
>   }
> }
> ```
>
> **快速檢查清單**:
> - [ ] **圖片**: 使用 WebP/AVIF,設定 width/height,懶載入
> - [ ] **字體**: WOFF2 格式,font-display: swap,預載入
> - [ ] **JavaScript**: Code Splitting,Tree Shaking,壓縮
> - [ ] **CSS**: Critical CSS 內聯,移除未使用樣式
> - [ ] **快取**: Service Worker,CDN,強快取
> - [ ] **監控**: Lighthouse CI,RUM (Real User Monitoring)
> - [ ] **預算**: Performance Budget 設定在 CI/CD

## 💡 最佳實踐

### 1. 測量先於優化
- 沒有數據就沒有優化
- 建立基準線 (Baseline)
- 量化改善成果
- 避免過早優化

### 2. 關注瓶頸，不要猜測
- 使用 Profiling 找瓶頸
- 80/20 法則：20% 代碼造成 80% 效能問題
- 優先優化影響最大的部分
- 不要優化不是瓶頸的代碼

### 3. 分階段優化
- Quick Wins 優先（低成本高效益）
- 驗證一個再進行下一個
- 避免一次改動太多
- 保持可回滾性

### 4. 權衡取捨
- 效能 vs 可維護性
- 效能 vs 開發成本
- 效能 vs 基礎設施成本
- 追求合理的效能，不是極致效能

### 5. 監控不可少
- 優化不是一次性工作
- 持續監控效能趨勢
- 及早發現效能退化
- 建立效能文化

### 6. 記錄與分享
- 記錄優化過程和決策
- 分享最佳實踐
- 建立團隊知識庫
- 避免重複犯錯

---

## 🚨 常見陷阱

### ❌ 避免這些錯誤

**1. 分析階段**
- ❌ 憑感覺猜測瓶頸
- ❌ 只看平均值，忽略 P95/P99
- ❌ 測試環境與 Production 差異大
- ❌ 負載測試不真實

**2. 優化階段**
- ❌ 過早優化（沒有效能問題就優化）
- ❌ 過度優化（犧牲可讀性和可維護性）
- ❌ 只優化代碼，忽略架構問題
- ❌ 優化錯方向（優化非瓶頸部分）

**3. 驗證階段**
- ❌ 沒有 A/B Testing 直接全量部署
- ❌ 只測 Happy Path
- ❌ 忽視長期效能（記憶體洩漏）
- ❌ 沒有回滾計畫

**4. 監控階段**
- ❌ 優化完就不管了
- ❌ 沒有效能退化告警
- ❌ 監控指標不全面
- ❌ 告警閾值設定不合理

**5. 團隊協作**
- ❌ 獨自優化不通知團隊
- ❌ 沒有知識轉移
- ❌ 優化成果沒有展示
- ❌ 沒有建立效能文化

---

## 📞 需要幫助？

### 效能問題診斷
```
「系統出現 [具體現象]，請協助診斷效能問題」
```

### 優化方案選擇
```
「針對 [具體瓶頸]，應該採用哪種優化方案？」
```

### 工具使用指導
```
「如何使用 [工具名稱] 進行效能分析？」
```

### 權衡建議
```
「優化方案 A 和 B 的利弊分析？如何選擇？」
```

---

## 📚 實際案例走查

### 案例 1：API 回應時間優化 (2000ms → 200ms)

#### 背景
電商平台商品列表 API 回應時間 P95 達 2000ms，嚴重影響使用者體驗和轉換率。目標：優化至 200ms 以內。

#### 挑戰
- ❌ **N+1 查詢問題**：單一請求觸發 100+ 次資料庫查詢
- ❌ **缺少快取**：每次請求都查詢資料庫
- ❌ **資料過度載入**：回傳不必要的欄位和關聯資料
- ❌ **序列化耗時**：大量 JSON 序列化耗時 300ms+

#### 執行步驟

**Week 1：效能分析與瓶頸識別**
```
載入 AISDLC_INIT.md + Performance-Engineer
→ 使用 New Relic APM 追蹤請求
→ 使用 pg_stat_statements 分析 SQL 查詢
→ 🔴 確認瓶頸清單

發現:
1. 資料庫查詢: 1200ms (60%)
   - N+1 查詢: 100+ 次 SELECT
   - 缺少索引: category_id, brand_id
2. JSON 序列化: 350ms (17.5%)
3. 業務邏輯: 280ms (14%)
4. 網路傳輸: 170ms (8.5%)
```

**Week 2：N+1 查詢優化**
```
問題代碼 (Before):
// 觸發 1 + N 次查詢
const products = await Product.findAll();
for (const product of products) {
  product.category = await Category.findByPk(product.categoryId);  // N 次查詢
  product.brand = await Brand.findByPk(product.brandId);           // N 次查詢
}

優化後 (After):
// 使用 Eager Loading，只需 1 次查詢
const products = await Product.findAll({
  include: [
    { model: Category, attributes: ['id', 'name'] },
    { model: Brand, attributes: ['id', 'name'] }
  ]
});

結果:
- 資料庫查詢次數: 102 次 → 1 次
- 查詢時間: 1200ms → 180ms (-85%)
```

**Week 2：索引優化**
```sql
-- 分析慢查詢
EXPLAIN ANALYZE
SELECT * FROM products WHERE category_id = 123 AND is_active = true;

-- 建立複合索引
CREATE INDEX idx_products_category_active
ON products(category_id, is_active)
WHERE is_active = true;  -- Partial Index

-- 建立涵蓋索引 (Covering Index)
CREATE INDEX idx_products_list
ON products(category_id, is_active)
INCLUDE (name, price, image_url);

結果:
- 索引掃描時間: 180ms → 35ms (-80%)
```

**Week 3：快取層導入**
```
實作 3 層快取:

1. 應用層快取 (Redis)
const cacheKey = `products:category:${categoryId}:page:${page}`;
let products = await redis.get(cacheKey);

if (!products) {
  products = await Product.findAll({ where: { categoryId } });
  await redis.setex(cacheKey, 300, JSON.stringify(products));  // 5 分鐘 TTL
}

2. 資料庫查詢結果快取 (pg_bouncer)
- Connection Pooling: 減少連線建立時間

3. CDN 快取 (CloudFlare)
- 靜態資源: images, CSS, JS
- API 快取: Cache-Control: public, max-age=60

結果:
- Cache Hit Rate: 85%
- 回應時間 (Cache Hit): 35ms
- 回應時間 (Cache Miss): 220ms
```

**Week 3：序列化優化**
```
問題: JSON.stringify() 處理大型物件耗時

優化 1: 欄位裁剪
// Before: 回傳所有欄位 (50+ 個)
SELECT * FROM products;

// After: 只回傳必要欄位
SELECT id, name, price, image_url, stock FROM products;

優化 2: 使用更快的序列化函式庫
// Before: JSON.stringify()
return res.json(products);  // 350ms

// After: fast-json-stringify (預編譯 schema)
const stringify = fastJson({
  type: 'array',
  items: {
    type: 'object',
    properties: {
      id: { type: 'integer' },
      name: { type: 'string' },
      price: { type: 'number' }
    }
  }
});
return res.send(stringify(products));  // 80ms (-77%)
```

**Week 4：壓力測試與驗證**
```
使用 k6 執行負載測試:

// load-test.js
export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'],  // 目標: P95 < 200ms
  },
};

結果:
- P50: 45ms (目標 < 100ms) ✅
- P95: 180ms (目標 < 200ms) ✅
- P99: 250ms (可接受) ✅
- 錯誤率: 0% ✅
```

#### 關鍵成果
- ✅ **回應時間改善**：P95 從 2000ms → 180ms (-91%)
- ✅ **資料庫負載降低**：查詢次數 -98%、CPU 使用率 -65%
- ✅ **快取命中率**：85% (目標 > 80%)
- ✅ **使用者體驗提升**：轉換率 +12%、跳出率 -18%

#### 時程與成本
- **總時程**：4 週
- **人力**：1 後端資深工程師 + 1 DevOps
- **成本**：約 $15k (人力) + $500/月 (Redis, CDN)
- **ROI**：轉換率提升帶來額外營收 $50k/月

#### 經驗教訓
1. **分析優先於優化**：先用 APM 找瓶頸，不要盲目優化
2. **80/20 法則**：N+1 查詢和快取解決了 80% 的問題
3. **測試驗證必須**：Benchmark 確保優化有效且無副作用
4. **監控持續化**：設定 Alerting (P95 > 300ms 即告警)

---

### 案例 2：資料庫 N+1 查詢優化

#### 背景
社交平台動態牆 (Timeline) 載入時間過長，分析發現嚴重的 N+1 查詢問題，單一頁面觸發 500+ 次資料庫查詢。

#### 挑戰
- ❌ **N+1 查詢爆炸**：查詢 20 篇貼文，觸發 20 次使用者查詢 + 20 次留言查詢 + 每則留言再查詢作者
- ❌ **ORM 濫用**：過度依賴 ORM 的 Lazy Loading
- ❌ **無快取機制**：重複資料每次都查詢資料庫
- ❌ **分頁問題**：未使用 Cursor-based Pagination，OFFSET 很大時效能極差

#### 執行步驟

**階段 1：問題量化 (1 天)**
```
載入 AISDLC_INIT.md
→ 啟用 PostgreSQL 查詢日誌
→ 使用 Datadog APM 追蹤

問題代碼:
async function getTimeline(userId, page = 1) {
  const posts = await Post.findAll({
    where: { authorId: userId },
    limit: 20,
    offset: (page - 1) * 20,
    order: [['createdAt', 'DESC']]
  });

  for (const post of posts) {
    post.author = await User.findByPk(post.authorId);          // +20 queries
    post.comments = await Comment.findAll({                     // +20 queries
      where: { postId: post.id },
      limit: 5
    });

    for (const comment of post.comments) {
      comment.author = await User.findByPk(comment.authorId);  // +100 queries
    }
  }

  return posts;
}

實測:
- 總查詢數: 1 + 20 + 20 + 100 = 141 次
- 載入時間: 3.5 秒
- 資料庫 CPU: 85%
```

**階段 2：Eager Loading 改造 (2 天)**
```
優化策略: 使用 JOIN 預載入關聯資料

async function getTimeline(userId, page = 1) {
  const posts = await Post.findAll({
    where: { authorId: userId },
    limit: 20,
    offset: (page - 1) * 20,
    order: [['createdAt', 'DESC']],
    include: [
      {
        model: User,
        as: 'author',
        attributes: ['id', 'name', 'avatar']  // 只取需要的欄位
      },
      {
        model: Comment,
        as: 'comments',
        limit: 5,
        include: [{
          model: User,
          as: 'author',
          attributes: ['id', 'name', 'avatar']
        }],
        separate: true  // 使用 separate query 避免 cartesian product
      }
    ]
  });

  return posts;
}

改善結果:
- 總查詢數: 1 + 1 (comments with JOIN) = 2 次 (-98.6%)
- 載入時間: 3.5s → 450ms (-87%)
```

**階段 3：DataLoader 批次載入 (2 天)**
```
問題: 即使使用 Eager Loading，仍有重複查詢相同使用者

使用 DataLoader 批次載入並去重:

const DataLoader = require('dataloader');

// 建立 User DataLoader
const userLoader = new DataLoader(async (userIds) => {
  const users = await User.findAll({
    where: { id: userIds },
    attributes: ['id', 'name', 'avatar']
  });

  const userMap = new Map(users.map(u => [u.id, u]));
  return userIds.map(id => userMap.get(id));
});

// 使用 DataLoader
async function getTimeline(userId, page = 1) {
  const posts = await Post.findAll({
    where: { authorId: userId },
    limit: 20,
    offset: (page - 1) * 20,
    order: [['createdAt', 'DESC']]
  });

  // DataLoader 自動批次載入並去重
  for (const post of posts) {
    post.author = await userLoader.load(post.authorId);

    const comments = await Comment.findAll({
      where: { postId: post.id },
      limit: 5
    });

    for (const comment of comments) {
      comment.author = await userLoader.load(comment.authorId);
    }

    post.comments = comments;
  }

  return posts;
}

改善結果:
- 使用者查詢次數: 20 次 → 1 次 (批次查詢所有不重複使用者)
- 載入時間: 450ms → 280ms (-38%)
```

**階段 4：快取層與 Cursor-based Pagination (2 天)**
```
1. Redis 快取熱門資料

const cacheKey = `user:${userId}:timeline:${cursorId}`;
let posts = await redis.get(cacheKey);

if (!posts) {
  posts = await getTimelineFromDB(userId, cursorId);
  await redis.setex(cacheKey, 300, JSON.stringify(posts));  // 5 min TTL
}

2. Cursor-based Pagination (取代 OFFSET)

// Before: OFFSET 效能差 (需掃描 offset 筆資料)
SELECT * FROM posts
WHERE author_id = 123
ORDER BY created_at DESC
LIMIT 20 OFFSET 1000;  // 需掃描前 1000 筆

// After: Cursor-based (使用索引)
SELECT * FROM posts
WHERE author_id = 123
  AND created_at < '2024-01-01 10:00:00'  -- Cursor
ORDER BY created_at DESC
LIMIT 20;  // 直接從 cursor 開始

實作:
function getTimeline(userId, cursor = null) {
  const where = { authorId: userId };

  if (cursor) {
    const decodedCursor = Buffer.from(cursor, 'base64').toString();
    const [id, createdAt] = decodedCursor.split('|');
    where.createdAt = { [Op.lt]: new Date(createdAt) };
  }

  const posts = await Post.findAll({
    where,
    limit: 20,
    order: [['createdAt', 'DESC']]
  });

  const nextCursor = posts.length > 0
    ? Buffer.from(`${posts[posts.length - 1].id}|${posts[posts.length - 1].createdAt}`).toString('base64')
    : null;

  return { posts, nextCursor };
}

改善結果:
- 分頁查詢時間 (page 50): 1200ms → 35ms (-97%)
- Cache Hit Rate: 75%
```

**階段 5：資料庫索引優化 (1 天)**
```sql
-- 建立複合索引 (覆蓋查詢條件和排序)
CREATE INDEX idx_posts_author_created
ON posts(author_id, created_at DESC);

-- 建立 Covering Index (包含常用欄位,避免回表)
CREATE INDEX idx_posts_timeline
ON posts(author_id, created_at DESC)
INCLUDE (id, content, image_url, likes_count);

-- 分析索引使用狀況
EXPLAIN ANALYZE
SELECT id, content, image_url, likes_count
FROM posts
WHERE author_id = 123 AND created_at < '2024-01-01'
ORDER BY created_at DESC
LIMIT 20;

改善結果:
- Index Scan: 280ms → 15ms (-95%)
- 減少 Heap Fetches (不需回表)
```

#### 關鍵成果
- ✅ **查詢次數**：141 次 → 2-3 次 (-98%)
- ✅ **載入時間**：3.5s → 180ms (快取命中時 35ms) (-95%)
- ✅ **資料庫 CPU**：85% → 12% (-86%)
- ✅ **吞吐量提升**：200 req/s → 2000 req/s (+900%)

#### 時程與成本
- **總時程**：1.5 週
- **人力**：1 後端資深工程師
- **成本**：約 $10k (人力) + $200/月 (Redis)
- **ROI**：節省資料庫升級成本 $50k/年

#### 優化技術總結
| 優化技術 | 適用場景 | 改善幅度 |
|---------|---------|---------|
| **Eager Loading** | ORM 關聯查詢 | -90%+ 查詢次數 |
| **DataLoader** | GraphQL、批次查詢 | -80%+ 重複查詢 |
| **索引優化** | 慢查詢優化 | -70-95% 查詢時間 |
| **Cursor Pagination** | 大量分頁資料 | -90%+ 深度分頁時間 |
| **Redis 快取** | 熱門資料讀取 | -90%+ 資料庫負載 |

#### 經驗教訓
1. **ORM 是雙面刃**：方便但易產生 N+1 查詢，需謹慎使用
2. **監控先行**：使用 APM 持續監控，及早發現問題
3. **DataLoader 必備**：GraphQL 專案必用，RESTful 也適用
4. **分頁設計**：Cursor-based > Offset-based (大資料量時)

---

## 🎓 相關資源

### 文檔與流程
- [Performance QuickRef 快速參考](./SOP_QuickRef.md)
- [Performance DeepDive 深度指南](./SOP_DeepDive.md)
- [Performance 快速啟動指令集](../../prompts/scenario-prompts/performance-prompts.md)
- [performance-optimization-flow Workflow](../../workflow/scenario-specific/performance-optimization-flow.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（主導）
- [sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（架構優化）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - Senior Developer（代碼優化）
- [qa-automation-zh.yaml](../../agent/specialized/qa-automation-zh.yaml) - QA Automation（效能測試）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（基礎設施與監控）
- [code-analyzer-zh.yaml](../../agent/specialized/code-analyzer-zh.yaml) - CodeX（代碼效能分析，選用）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（安全敏感區域優化，選用）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（行動端架構優化，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端效能測試，選用）

### 相關 Skills
- `/performance-optimization` - 效能分析與優化
- `/devops-monitoring` - 監控告警系統
- `/integration-redis` - Redis 快取整合
- `/integration-database` - 資料庫架構優化（索引、連線池、讀寫分離）
- `/mobile-development` - 行動端效能優化（涉及 Android/iOS/macOS 時）

### 文檔模板
- [Performance 文檔模板](../../docs_template/scenario_specific/performance/)

---

**文檔版本: v0.01
**最後更新**: 2026-02-17
**維護者**: AISDLC Framework Team

---

## AutoClaude 自動化執行（Phase Z / v0.02 新增）

> 規格凍結（SPEC_FROZEN）後，本場景的 AT 契約可交由 AutoClaude 引擎自動執行實作與雙重驗證。
> 標準作業全文：`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`；
> 翻譯保真規則：`governance/rules/R-9.38-playbook-translation-fidelity.yaml`。

1. **編譯**（AutoClaude/ 目錄）：`python -m autoclaude.tools.sdd_compile --spec-dir <docs path> --out playbooks/sdd_bridge.yaml`
   - 規格未凍結 → exit 2 拒絕（Spec-First 硬閘）；weak_regex 斷言入 audit log。
   - 量化 NFR 斷言（延遲／吞吐門檻等）會落入 weak_regex，需人工補強 evaluator 後再執行。
2. **人工 review** 生成的 playbook YAML（SCG-4 精神：生成物 = 待審工件）。
3. **執行**：`python -m autoclaude playbooks/sdd_bridge.yaml` — SddGovernancePlugin 自動守 SCG 閘門、記帳契約違反、防規格 drift。
4. 🔴 人工確認閘門不可由自動化跳過（Rule 8）；ESCALATION 後必等人工。
