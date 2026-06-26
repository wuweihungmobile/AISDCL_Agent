---
name: devops-monitoring
description: 監控告警設定，告警閾值對應 NFR 量化，PBS Gate 前執行效能基準監控
user-invocable: true
disable-model-invocation: false
argument-hint: "[stack: prometheus|datadog|cloudwatch] [target: app|infra|all]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# DevOps Monitoring Skill（SDD 原生）

監控是 SDD NFR 量化的執行驗證器。告警閾值不可由工程師任意設定，必須直接引用 FRD 中 NFR-XXX 的量化值（P99 延遲、錯誤率 SLO、可用性 SLA）。本 Skill 同時作為 PBS（Performance Baseline Specification）Gate 的監控基礎設施。

---

## 觸發方式

```bash
/devops-monitoring prometheus app
/devops-monitoring datadog all
/devops-monitoring cloudwatch infra
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 NFR 量化 | 效能/可用性 SLO 已定義 | `docs/01_requirements/FRD-{System}.md` NFR 章節（NFR-XXX 有數值） |
| SCG-2 通過 | 監控架構確定 | `docs/02_architecture/SRD-{System}.md` 監控章節 |

---

## 執行流程

### 階段 1：讀取 NFR 量化值（必要）

讀取 `docs/01_requirements/FRD-{System}.md` 的 NFR 章節，提取：

```markdown
## 監控告警閾值對應表（從 NFR 提取）

| NFR ID | 指標 | SDD 量化值 | 告警閾值 | 嚴重程度 |
|--------|------|-----------|---------|---------|
| NFR-P001 | P99 API 回應時間 | < 200ms | > 500ms (2.5x) | Warning; > 1000ms: Critical |
| NFR-P002 | 錯誤率 | < 0.1% | > 1% | Warning; > 5%: Critical |
| NFR-A001 | 服務可用性 | 99.9% SLA | 連續 1 分鐘 down | Critical |
| NFR-R001 | CPU 使用率 | < 70% 正常 | > 80% | Warning; > 90%: Critical |
```

🔴 確認點：告警閾值必須來自 NFR，不可由工程師自行設定。

---

### 階段 2：Prometheus 配置（指標採集）

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: [alertmanager:9093]

rule_files:
  - "rules/nfr-alerts.yml"   # 以 NFR 命名，明確告警來源

scrape_configs:
  - job_name: '{app_name}'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['{app}:{port}']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

---

### 階段 3：告警規則（閾值對應 NFR）

```yaml
# prometheus/rules/nfr-alerts.yml
# 告警規則直接引用 NFR ID，確保可追溯
groups:
  - name: nfr_alerts
    rules:
      # NFR-P002: 錯誤率 SLO
      - alert: ErrorRateExceedsSLO
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
          nfr_id: "NFR-P002"     # 追溯 NFR
        annotations:
          summary: "錯誤率超過 NFR-P002 閾值（SLO: < 0.1%）"
          description: "當前錯誤率 {{ $value | humanizePercentage }}，違反 NFR-P002"

      # NFR-P001: P95 延遲 SLO
      - alert: LatencyExceedsSLO
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 0.5
        for: 5m
        labels:
          severity: warning
          nfr_id: "NFR-P001"
        annotations:
          summary: "P95 延遲超過 NFR-P001 閾值（SLO: < 200ms）"
          description: "P95 延遲 {{ $value | humanizeDuration }}，接近 NFR-P001 邊界"

      # NFR-A001: 可用性 SLA
      - alert: ServiceAvailabilityViolation
        expr: up == 0
        for: 1m
        labels:
          severity: critical
          nfr_id: "NFR-A001"
        annotations:
          summary: "服務停機，NFR-A001 可用性 SLA 面臨違反"
          description: "{{ $labels.job }} 不可用，SLA 要求 99.9%"

      # NFR-R001: 資源使用率
      - alert: CPUThresholdExceeded
        expr: |
          100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 10m
        labels:
          severity: warning
          nfr_id: "NFR-R001"
        annotations:
          summary: "CPU 超過 NFR-R001 閾值（< 70% 正常）"
          description: "CPU {{ $value | printf \"%.1f\" }}%"
```

---

### 階段 4：PBS Gate 監控 Dashboard

PBS（Performance Baseline Specification）Gate 要求監控能驗證效能基準：

```yaml
# grafana/provisioning/dashboards/nfr-dashboard.json
# Dashboard 面板對應每個 NFR-XXX
# 必須包含：
# - P50/P95/P99 延遲趨勢
# - 錯誤率趨勢（對應 NFR-P002 SLO 線）
# - 服務可用性（對應 NFR-A001 SLA 線）
# - 資源使用率（CPU/Memory，對應 NFR-R001）
```

---

### 階段 5：Alertmanager 通知路由

```yaml
# alertmanager/alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'nfr_id']   # 按 NFR ID 分組
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        title: '{{ .GroupLabels.alertname }} [{{ .GroupLabels.nfr_id }}]'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'critical-alerts'
    slack_configs:
      - channel: '#alerts-critical'
        title: '🔴 {{ .GroupLabels.alertname }} (NFR: {{ .GroupLabels.nfr_id }})'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_KEY}'
```

---

### 階段 6：RTM 更新 🔴

```bash
/rtm-generate update    # 更新監控相關 NFR TC 狀態
/spec-compliance-check docs/01_requirements/FRD-{System}.md
```

🔴 確認點：每個告警規則都有對應的 NFR-XXX 標籤，無孤立告警。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Prometheus 配置 | `prometheus/prometheus.yml` | SCG-2 後 |
| NFR 告警規則 | `prometheus/rules/nfr-alerts.yml` | SCG-2 後 |
| Alertmanager 配置 | `alertmanager/alertmanager.yml` | SCG-2 後 |
| NFR 閾值對應表 | `docs/08_deployment/MONITORING-NFR-MAPPING-{System}.md` | SCG-2 後 |

---

## 後置動作

```
/sdd-gate SCG-5            # 交付前確認監控就緒（RTM 包含 NFR TC）
/release-management        # 發布 Runbook 包含監控回滾條件
```

🔷 **本 Skill 協助通過**：SCG-5（NFR 測試通過，監控基礎就緒）

---

## 相關 Skill

- `/sa-analyst` — 定義 NFR 量化值（monitoring 的閾值依據）
- `/devops-kubernetes` — K8s 指標採集（Pod 資源監控）
- `/performance-optimization` — PBS Gate（效能基準監控）
- `/release-management` — Runbook 中的監控回滾條件

---

**基於**: AISDLC-SDD v0.27
**對應 NFR 規格**: `docs/01_requirements/FRD-{System}.md` NFR 章節
**對應 CI/CD 規格**: `cicd/SDD_PERFORMANCE_CICD.md`
