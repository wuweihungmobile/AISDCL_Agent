# 事件驅動 Agent 通知系統配置範本

> **🔔 P3 事件驅動 Agent 協作**
>
> 此範本定義 CI/CD Pipeline 中的 **事件驅動 Agent 通知系統**，
> 實現 Agent 之間基於事件的自動化協作與通知。
>
> - **核心事件**: PR Opened → PR Approved → Release Tagged
> - **Agent 觸發鏈**: 事件觸發 → 多 Agent 並行執行 → 結果匯聚 → 下游通知
> - **目標**: 從「手動交接」提升到「事件驅動自動協作」

---

**版本**: v1.0
**建立日期**: 2026-03-22
**文檔類型**: DevOps 配置範本 | 事件驅動 Agent 通知
**相關文檔**:
- [CICD_Pipeline_Template.md](./CICD_Pipeline_Template.md) - CI/CD Pipeline 完整範本
- [Layer0_Security_Baseline_Template.md](./Layer0_Security_Baseline_Template.md) - Layer 0 安全基線
- [Layer1_Build_Verify_Template.md](./Layer1_Build_Verify_Template.md) - Layer 1 建置驗證
- [Security_Scan_Integration_Template.md](./Security_Scan_Integration_Template.md) - P1 安全掃描整合
- [Migration_Pipeline_Template.md](./Migration_Pipeline_Template.md) - P1 Migration Pipeline
- [Performance_Benchmark_Gate_Template.md](./Performance_Benchmark_Gate_Template.md) - P2 效能基準門檻
- [Documentation_Pipeline_Template.md](./Documentation_Pipeline_Template.md) - P2 文檔 Pipeline

---

## 📋 目錄

1. [架構概覽](#架構概覽)
2. [核心事件定義](#核心事件定義)
3. [Agent 觸發鏈模型](#agent-觸發鏈模型)
4. [情境專屬觸發規則](#情境專屬觸發規則)
5. [非同步協作時序](#非同步協作時序)
6. [通知渠道與格式](#通知渠道與格式)
7. [避坑指南與風險緩解](#避坑指南與風險緩解)
8. [情境適用性](#情境適用性)
9. [Pipeline 整合位置](#pipeline-整合位置)
10. [維護與更新](#維護與更新)

---

## 架構概覽

### 事件驅動協作模型

```
事件源                Agent 觸發層              通知層
┌──────────┐        ┌───────────────────┐     ┌──────────────────┐
│ PR Opened │──────→│ code-analyzer      │────→│ PR Comment       │
│           │──────→│ security-engineer  │────→│ Slack/Teams      │
│           │──────→│ qa-automation      │────→│ Email (摘要)     │
└──────────┘        │                   │     └──────────────────┘
                    │ [All Pass?]       │
                    │   ├─ Yes → deploy-preview + notify pm-po
                    │   └─ No  → block PR + notify dev
                    └───────────────────┘

┌──────────────┐    ┌───────────────────┐     ┌──────────────────┐
│ PR Approved   │──→│ devops-engineer    │────→│ Staging URL      │
│               │──→│ qa-tester          │────→│ Smoke Test 報告  │
└──────────────┘    │ [All Pass?]       │     │ PM/PO 驗收通知   │
                    └───────────────────┘     └──────────────────┘

┌──────────────┐    ┌───────────────────┐     ┌──────────────────┐
│ Release Tagged│──→│ devops-engineer    │────→│ 部署進度通知     │
│               │──→│ performance-eng    │────→│ Benchmark 報告   │
│               │──→│ security-engineer  │────→│ DAST 掃描報告    │
└──────────────┘    └───────────────────┘     └──────────────────┘
```

### 設計原則

| 原則 | 說明 |
|------|------|
| **事件驅動** | Agent 不輪詢，由 CI/CD 事件主動觸發 |
| **並行執行** | 無依賴的 Agent 並行運行，縮短反饋迴圈 |
| **結果匯聚** | 所有 Agent 完成後統一判定（All Pass / Any Fail） |
| **分級通知** | 依嚴重程度選擇通知渠道（阻塞→PR評論、警告→Slack、資訊→Email） |
| **超時熔斷** | 單一 Agent 超時不阻塞整條鏈，降級為 Warning |

---

## 核心事件定義

### 事件清單

| 事件 | 觸發條件 | 阻塞性 | 涉及 Agent |
|------|---------|--------|-----------|
| `pr_opened` | PR 建立或更新 | 🔴 阻塞合併 | code-analyzer, security-engineer, qa-automation |
| `pr_approved` | PR 通過審查 | ⚠️ 半阻塞 | devops-engineer, qa-tester |
| `release_tagged` | 版本標記建立 | 🔴 阻塞發布 | devops-engineer, performance-engineer, security-engineer |
| `deploy_completed` | 部署完成 | ❌ 不阻塞 | 全員通知 |
| `pipeline_failed` | Pipeline 失敗 | 🔴 阻塞 | 相關 Agent + Dev |

### 事件生命週期

```yaml
event_lifecycle:
  pr_opened:
    phase: "pre-merge"
    timeout: 15m          # 整體超時
    agent_timeout: 10m    # 單一 Agent 超時
    on_timeout: warn      # 超時降級為警告
    retry: 1              # 失敗重試次數

  pr_approved:
    phase: "pre-deploy"
    timeout: 20m
    agent_timeout: 15m
    on_timeout: warn
    retry: 0

  release_tagged:
    phase: "deploy"
    timeout: 60m
    agent_timeout: 30m
    on_timeout: block     # 部署超時必須阻塞
    retry: 1
```

---

## Agent 觸發鏈模型

### pr_opened 事件

```yaml
# PR 開啟 → 觸發品質守門 Agent 群
pr_opened:
  triggers:
    - agent: code-analyzer          # SAST + Code Quality
      action: static-analysis
      blocking: true
      timeout: 600s
      notify_on: [failure, timeout]

    - agent: security-engineer      # Secret + Dependency Scan
      action: security-scan
      blocking: true
      timeout: 600s
      blocking_severity: [critical, high]
      warning_severity: [medium, low]
      notify_on: [failure, warning]

    - agent: qa-automation          # Unit + Integration Test
      action: run-test-suite
      blocking: true
      timeout: 600s
      notify_on: [failure]

  on_all_pass:
    - agent: devops-engineer
      action: deploy-preview
      blocking: false
      notify: [pr_comment, slack]

  on_any_fail:
    - notify: pr_comment            # PR 評論標記失敗項
    - notify: slack_dev_channel     # 通知開發者頻道
    - action: block_merge           # 阻塞合併
```

### pr_approved 事件

```yaml
# PR 核准 → 觸發 Staging 部署
pr_approved:
  triggers:
    - agent: devops-engineer
      action: deploy-staging
      blocking: true
      timeout: 900s

    - agent: qa-tester
      action: smoke-test-staging
      blocking: true
      timeout: 600s
      depends_on: deploy-staging    # 等待部署完成

  on_all_pass:
    - notify: pm-po                 # 通知 PM/PO 可驗收
      message: "Staging 部署完成，預覽環境可供驗收"
      include: [staging_url, test_report_url]

  on_any_fail:
    - notify: [pr_comment, slack_dev_channel]
    - action: rollback_staging
```

### release_tagged 事件

```yaml
# 版本標記 → 觸發生產部署
release_tagged:
  triggers:
    - agent: devops-engineer
      action: deploy-production
      strategy: canary              # 預設 Canary 部署
      canary_steps: [5%, 25%, 50%, 100%]
      blocking: true

    - agent: performance-engineer
      action: post-deploy-benchmark
      blocking: false
      depends_on: deploy-production

    - agent: security-engineer
      action: dast-scan-production
      blocking: false
      depends_on: deploy-production

  on_all_pass:
    - notify: all_stakeholders
      message: "v{version} 已成功部署至生產環境"
      include: [release_notes, benchmark_report, security_report]

  on_any_fail:
    - action: auto_rollback
    - notify: [slack_oncall, email_team_lead]
      severity: critical
```

---

## 情境專屬觸發規則

### Migration 情境（最高風險）

```yaml
migration_triggers:
  branch_pattern: "migration/*"

  pr_opened:
    additional_agents:
      - agent: integration-specialist
        action: contract-test        # 驗證 API 相容性
        blocking: true

    additional_checks:
      - dual-build                   # 舊棧 + 新棧同時建置
      - rollback-script-exists       # 驗證回滾腳本存在

  release_tagged:
    deploy_strategy:
      type: canary
      steps: [5%, 25%, 50%, 100%]
      rollback_trigger:
        error_rate: "> 1%"
        latency_p99: "> 2x baseline"
      require:
        - dual_write_verification
        - expand_contract_pattern

    additional_agents:
      - agent: performance-engineer
        action: compare-old-new-latency
        blocking: true
```

### Refactoring 情境

```yaml
refactoring_triggers:
  branch_pattern: "refactor/*"

  pr_opened:
    additional_agents:
      - agent: code-analyzer
        action: mutation-test         # 驗證測試品質
        blocking: true

      - agent: code-analyzer
        action: diff-coverage-check   # 變更行 ≥ 80% 覆蓋
        blocking: true
        threshold: 80%

    notification:
      include: [refactoring_impact_report]
```

### Performance 情境

```yaml
performance_triggers:
  branch_pattern: "perf/*"
  schedule: "0 2 * * *"            # Nightly

  pr_opened:
    additional_agents:
      - agent: performance-engineer
        action: micro-benchmark
        blocking: true
        regression_threshold: 10%

  nightly:
    agents:
      - agent: performance-engineer
        action: full-load-test
        blocking: false
        notify: [slack_perf_channel, email_perf_team]
```

### Security 情境（增強掃描）

```yaml
security_triggers:
  # 所有 PR 強制安全掃描（已在 Layer 0）
  # Security 情境額外觸發
  branch_pattern: "security/*"

  pr_opened:
    additional_agents:
      - agent: security-engineer
        action: enhanced-sast         # 深度靜態分析
        blocking: true

      - agent: compliance-officer
        action: compliance-check
        blocking: true

  release_tagged:
    additional_agents:
      - agent: security-engineer
        action: dast-full-scan        # 完整動態掃描
        blocking: true
        timeout: 3600s
```

---

## 非同步協作時序

### PR 開啟 → 合併 → 部署 完整時序

```
Developer     CI Pipeline      code-analyzer    security-eng    qa-automation    devops-eng     pm-po
    |              |                 |                |               |               |            |
    |--PR Open---->|                 |                |               |               |            |
    |              |                 |                |               |               |            |
    |              |--Static Scan--->|                |               |               |            |
    |              |--Security-------|--------------->|               |               |            |
    |              |--Test Suite-----|----------------|-------------->|               |            |
    |              |                 |                |               |               |            |
    |              |<--Report--------|                |               |               |            |
    |              |<--Scan Result---|----------------|               |               |            |
    |              |<--Test Result---|----------------|---------------|               |            |
    |              |                 |                |               |               |            |
    |              |====[All Pass?]====              |               |               |            |
    |              |  Yes:                            |               |               |            |
    |              |---Deploy Preview-|----------------|---------------|-------------->|            |
    |              |                 |                |               |               |            |
    |<--PR Comment-|  (結果摘要 + Preview URL)        |               |               |            |
    |              |                 |                |               |               |            |
    |--PR Approve->|                 |                |               |               |            |
    |              |---Deploy Staging|----------------|---------------|-------------->|            |
    |              |                 |                |               |               |            |
    |              |---Smoke Test----|----------------|-------------->|               |            |
    |              |                 |                |               |               |            |
    |              |<--Staging OK----|----------------|---------------|               |            |
    |              |                 |                |               |               |            |
    |              |---Notify PM/PO--|----------------|---------------|---------------|----------->|
    |              |                 |                |               |               |            |
```

### 通知結果匯聚模式

```
Agent 1 ──Result──┐
Agent 2 ──Result──┤ Aggregator ──→ Unified Notification
Agent 3 ──Result──┘
                    │
                    ├─ PR Comment (結構化摘要)
                    ├─ Slack (即時通知)
                    └─ Dashboard (歷史記錄)
```

---

## 通知渠道與格式

### 通知渠道配置

```yaml
notification_channels:
  pr_comment:
    provider: github/gitlab
    format: markdown
    triggers: [all_events]
    content:
      - status_summary          # ✅/❌ 各 Agent 狀態
      - failure_details          # 失敗項詳情
      - action_items             # 建議修復動作
      - urls                     # Preview/Staging URL

  slack:
    provider: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channels:
      dev: "#dev-notifications"
      oncall: "#oncall-alerts"
      perf: "#perf-monitoring"
    triggers: [failure, deploy_completed, release]

  email:
    provider: smtp/sendgrid
    recipients:
      team_lead: "${TEAM_LEAD_EMAIL}"
      all: "${TEAM_EMAIL_LIST}"
    triggers: [release_tagged, critical_failure]

  dashboard:
    provider: grafana/datadog
    url: "${DASHBOARD_URL}"
    triggers: [all_events]
    retention: 90d
```

### PR Comment 格式範本

```markdown
## 🔔 CI/CD Agent 協作報告

### 狀態摘要
| Agent | 動作 | 狀態 | 耗時 |
|-------|------|------|------|
| code-analyzer | Static Analysis | ✅ Pass | 2m 15s |
| security-engineer | Security Scan | ⚠️ Warn (2 Medium) | 3m 42s |
| qa-automation | Test Suite | ✅ Pass (Coverage: 87%) | 4m 08s |

### 整體判定: ✅ 可合併

### 詳細報告
- 📊 [Code Quality Report](link)
- 🛡️ [Security Report](link) — 2 Medium issues (不阻塞)
- 🧪 [Test Report](link) — 156 passed, 0 failed

### 下一步
PR 合併後將自動部署至 Staging 環境。
```

### Slack 通知格式

```yaml
slack_message_templates:
  pipeline_success:
    color: "#36a64f"
    title: "✅ Pipeline 通過"
    fields:
      - title: "PR"
        value: "${PR_TITLE} (#${PR_NUMBER})"
      - title: "Agent 結果"
        value: "Code ✅ | Security ✅ | Tests ✅"
      - title: "Preview"
        value: "${PREVIEW_URL}"

  pipeline_failure:
    color: "#e01e5a"
    title: "🔴 Pipeline 失敗"
    fields:
      - title: "PR"
        value: "${PR_TITLE} (#${PR_NUMBER})"
      - title: "失敗 Agent"
        value: "${FAILED_AGENTS}"
      - title: "動作"
        value: "請修復後重新提交"

  deploy_production:
    color: "#2eb886"
    title: "🚀 生產部署完成"
    fields:
      - title: "版本"
        value: "${RELEASE_TAG}"
      - title: "Canary 進度"
        value: "${CANARY_PROGRESS}"
      - title: "Benchmark"
        value: "P50: ${P50_LATENCY} | P99: ${P99_LATENCY}"
```

---

## 避坑指南與風險緩解

### 風險 1：Pipeline 死結 (Deadlock)

**場景**：`security-engineer` 掃描阻塞 PR → `dev-developer` 無法合併 → `qa-tester` 無環境測試 → 全線停擺。

**緩解策略**：

```yaml
deadlock_prevention:
  # 超時熔斷機制
  agent_timeout:
    default: 600s                    # 10 分鐘硬超時
    on_timeout: degrade_to_warning   # 超時降級為警告

  # 分級阻塞
  blocking_policy:
    critical: block_merge            # Critical 阻塞
    high: block_merge                # High 阻塞
    medium: warn_only                # Medium 僅警告
    low: info_only                   # Low 僅記錄

  # 旁路通道
  bypass:
    branches: ["hotfix/*"]           # hotfix 可跳過非關鍵掃描
    requires: post_merge_audit       # 需事後審核
    approvers: ["security-engineer"] # 需安全工程師核准
```

### 風險 2：通知風暴 (Notification Storm)

**場景**：大量 PR 同時觸發 → Slack 頻道被淹沒 → 重要通知被忽略。

**緩解策略**：

```yaml
notification_throttle:
  # 通知聚合
  aggregation:
    window: 300s                     # 5 分鐘聚合窗口
    max_per_window: 5                # 每窗口最多 5 則通知
    overflow: digest                 # 超出則合併為摘要

  # 通知分級
  priority_routing:
    critical: immediate              # 立即發送
    high: immediate
    medium: batched                  # 批次發送（每 15 分鐘）
    low: digest                      # 每日摘要

  # 靜默時段
  quiet_hours:
    enabled: false                   # 預設關閉
    schedule: "22:00-08:00"          # 非工作時段
    exception: [critical]            # Critical 例外
```

### 風險 3：Agent 回饋延遲

**場景**：Agent 完成後未及時通知，開發者空等。

**緩解策略**：

```yaml
feedback_optimization:
  # 即時回饋（不等全部完成）
  incremental_feedback: true
  notify_on_each_completion: true    # 每個 Agent 完成立即通知

  # 進度更新
  progress_update:
    interval: 60s                    # 每 60 秒更新進度
    format: "⏳ 3/5 Agents completed..."

  # 預估完成時間
  eta_prediction:
    enabled: true
    based_on: historical_average     # 基於歷史平均耗時
```

---

## 情境適用性

### Agent 通知系統適用矩陣

| 情境 | PR 事件通知 | 部署通知 | 情境專屬觸發 | 說明 |
|------|:---:|:---:|:---:|------|
| `greenfield` | 🔴 強制 | 🔴 強制 | ❌ | 標準事件通知 |
| `brownfield` | 🔴 強制 | 🔴 強制 | ❌ | 標準事件通知 |
| `refactoring` | 🔴 強制 | ⚠️ 選配 | ✅ mutation-test + diff-coverage | 重構品質守門 |
| `migration` | 🔴 強制 | 🔴 強制 | ✅ dual-build + canary + rollback | 最高風險，全鏈通知 |
| `integration` | 🔴 強制 | 🔴 強制 | ✅ contract-test | API 相容性通知 |
| `performance` | 🔴 強制 | ⚠️ 選配 | ✅ benchmark + SLA gate | 效能迴歸通知 |
| `devops` | 🔴 強制 | 🔴 強制 | ✅ IaC validate + plan | 基礎設施變更通知 |
| `testing` | 🔴 強制 | ⚠️ 選配 | ❌ | 標準事件通知 |
| `security` | 🔴 強制 | 🔴 強制 | ✅ enhanced-SAST + DAST | 安全增強通知 |
| `documentation` | ⚠️ 選配 | ⚠️ 選配 | ❌ | 文檔變更通知（輕量） |

> **說明**：PR 事件通知為所有程式碼相關情境的強制基線。Documentation 情境因無程式碼變更，通知為選配。

---

## Pipeline 整合位置

### 執行順序

```
Layer 0: Security Baseline ✅
Layer 1: Build & Verify ✅
Layer 2: Quality Assurance ✅（依情境選配）
Layer 3: Deploy & Validate ✅
    ↓
┌─────────────────────────────────────────────────┐
│  Layer 4: Event-Driven Agent Notification (本範本) │
│  ├── PR Comment (結果匯聚, 即時)                  │
│  ├── Slack/Teams (即時通知, 分級)                 │
│  ├── Email (摘要, 定期)                          │
│  └── Dashboard (歷史, 持續)                      │
└─────────────────────────────────────────────────┘
```

> **整合特性**：通知系統是 **橫切關注點 (Cross-Cutting Concern)**，不屬於特定 Layer，
> 而是貫穿 Layer 0~3 所有階段，在每個 Agent 完成動作後觸發通知。

### 與既有 Pipeline 的整合點

| 既有 Pipeline | 整合方式 | 觸發通知 |
|--------------|---------|---------|
| Layer 0 (Security) | 掃描完成時 | Secret/依賴漏洞結果 |
| Layer 1 (Build) | 建置/測試完成時 | 編譯錯誤、測試失敗 |
| P1 Migration | Canary 每階段 | 進度更新、錯誤率門檻 |
| P1 Security | 增強掃描完成時 | SAST/DAST 報告 |
| P2 Performance | Benchmark 完成時 | 迴歸偵測結果 |
| P2 Documentation | Doc Lint 完成時 | 連結斷裂、格式問題 |

---

## 維護與更新

### 定期更新週期

| 項目 | 更新頻率 | 負責角色 |
|------|---------|---------|
| 通知渠道配置 | 每季審查 | DevOps-Engineer |
| Agent 超時閾值 | 每月微調 | DevOps-Engineer |
| 通知模板 | 功能變更時 | DevOps-Engineer + PM/PO |
| 情境觸發規則 | 新情境加入時 | SD-Architect + DevOps-Engineer |
| Slack Webhook | 每季輪換 | DevOps-Engineer |

### 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|---------|
| 2026-03-22 | v1.0 | 初始版本，建立事件驅動 Agent 協作模型、通知渠道、風險緩解策略 |
