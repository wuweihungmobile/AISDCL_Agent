---
name: devops-monitoring
description: 設定監控告警系統，包含 Prometheus、Grafana、告警規則
user-invocable: true
disable-model-invocation: false
argument-hint: "[stack: 監控堆疊 (prometheus/datadog/cloudwatch)] [target: 監控目標 (app/infra/all)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# DevOps Monitoring Skill

建立完整的監控告警系統。

---

## 觸發方式

```bash
/devops-monitoring                    # 預設 Prometheus 堆疊
/devops-monitoring prometheus app     # 應用監控
/devops-monitoring --stack=datadog
```

---

## 執行流程

### 階段 1: 監控需求評估 🔴

**確認項目**:
- [ ] 監控目標 (應用/基礎設施/業務指標)
- [ ] 告警通知管道 (Slack/Email/PagerDuty)
- [ ] 資料保留期限
- [ ] Dashboard 需求
- [ ] SLA/SLO 定義

🔴 **確認點**: 確認監控需求

---

### 階段 2: Prometheus 配置

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

rule_files:
  - "rules/*.yml"

scrape_configs:
  # Prometheus 自身
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # 應用程式 (Node.js - prom-client)
  - job_name: 'app-node'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['frontend:3000']

  # 應用程式 (Spring Boot Actuator - Micrometer)
  - job_name: 'app-spring'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['backend:8080']
    # Spring Boot Actuator 需在 application.yml 中啟用:
    # management:
    #   endpoints:
    #     web:
    #       exposure:
    #         include: health,prometheus,info
    #   metrics:
    #     export:
    #       prometheus:
    #         enabled: true

  # Node Exporter (主機指標)
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  # Docker 容器
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  # PostgreSQL
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

---

### 階段 3: 告警規則

```yaml
# prometheus/rules/alerts.yml
groups:
  - name: app_alerts
    rules:
      # 高錯誤率
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "高錯誤率告警"
          description: "錯誤率超過 5%，當前: {{ $value | humanizePercentage }}"

      # 回應時間過長
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 延遲過高"
          description: "P95 延遲超過 1 秒，當前: {{ $value | humanizeDuration }}"

      # 服務不可用
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "服務不可用"
          description: "{{ $labels.job }} 已停止運行"

  - name: infra_alerts
    rules:
      # CPU 使用率過高
      - alert: HighCPUUsage
        expr: |
          100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "CPU 使用率過高"
          description: "CPU 使用率超過 80%，當前: {{ $value | printf \"%.1f\" }}%"

      # 記憶體不足
      - alert: LowMemory
        expr: |
          (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 < 20
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "可用記憶體不足"
          description: "可用記憶體低於 20%"

      # 磁碟空間不足
      - alert: LowDiskSpace
        expr: |
          (node_filesystem_avail_bytes{mountpoint="/"}
           / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 20
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "磁碟空間不足"
          description: "可用空間低於 20%"
```

---

### 階段 4: Alertmanager 配置

```yaml
# alertmanager/alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: '${SLACK_WEBHOOK_URL}'

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'critical-alerts'
    slack_configs:
      - channel: '#alerts-critical'
        title: '🔴 {{ .GroupLabels.alertname }}'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_KEY}'

  - name: 'warning-alerts'
    slack_configs:
      - channel: '#alerts'
        title: '🟡 {{ .GroupLabels.alertname }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname']
```

---

### 階段 5: Docker Compose 監控堆疊

```yaml
# docker-compose.monitoring.yml
version: '3.9'

services:
  prometheus:
    image: prom/prometheus:v2.51.0
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
    ports:
      - "9090:9090"

  alertmanager:
    image: prom/alertmanager:v0.27.0
    volumes:
      - ./alertmanager:/etc/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
    ports:
      - "9093:9093"

  grafana:
    image: grafana/grafana:10.4.0
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    ports:
      - "3001:3000"

  node-exporter:
    image: prom/node-exporter:v1.7.0
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.49.1
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro

volumes:
  prometheus_data:
  grafana_data:
```

---

### 階段 6: 驗證 🔴

**驗證清單**:
- [ ] Prometheus 正常採集指標
- [ ] Alertmanager 收到告警
- [ ] Grafana Dashboard 正常顯示
- [ ] 告警通知正確發送

🔴 **確認點**: 確認監控系統運行正常

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Prometheus 配置 | `prometheus/prometheus.yml` |
| 告警規則 | `prometheus/rules/*.yml` |
| Alertmanager 配置 | `alertmanager/alertmanager.yml` |
| Docker Compose | `docker-compose.monitoring.yml` |

---

## 相關 Skill

- `/devops-k8s` - Kubernetes 監控
- `/devops-docker` - Docker 容器
- `/performance` - 效能優化

---


## 相關檔案

- SOP 參考: `scenarios/devops/SOP_QuickRef.md`

**基於**: AISDLC v0.09 DevOps 情境
