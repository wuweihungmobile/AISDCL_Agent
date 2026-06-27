# Security Monitoring Specification — Template
# 安全監控規格模板
# Phase 05 — Security 情境 SDD 強化（Stage 6）

**文件類型**: Security Monitoring Specification (SMS)
**SDD 原則**: 安全監控基於 STRIDE 威脅模型，每個高風險威脅有對應告警
**存放位置**: `docs/08_deployment/SECURITY-MONITORING-SPEC-{system}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **系統名稱** | {SystemName} |
| **建立日期** | {YYYY-MM-DD} |
| **負責人** | {Security Engineer + DevOps} |
| **前置文件** | STRIDE-THREAT-MODEL, SAD, INCIDENT-RESPONSE-SPEC |

---

## 1. 安全事件監控規格

### 1.1 認證事件告警（對應 STRIDE-S：Spoofing）

| 告警 ID | 事件類型 | 觸發條件 | 嚴重度 | 回應時間 | 通知管道 |
|--------|---------|---------|-------|---------|---------|
| SEC-ALERT-AUTH-001 | 暴力破解嘗試 | 同一 IP 5 分鐘內失敗登入 ≥ 10 次 | P0 | 立即 | PagerDuty |
| SEC-ALERT-AUTH-002 | 帳號鎖定 | 使用者帳號被鎖定 | P1 | 15 分鐘 | Slack + Email |
| SEC-ALERT-AUTH-003 | 異常地理位置登入 | 登入地理位置與歷史不同 | P1 | 15 分鐘 | Email |
| SEC-ALERT-AUTH-004 | 特權帳號登入 | Admin 帳號在非工作時間登入 | P1 | 15 分鐘 | Slack + Email |
| SEC-ALERT-AUTH-005 | JWT Token 驗證失敗大量 | 5 分鐘內 Token 驗證失敗 ≥ 100 次 | P0 | 立即 | PagerDuty |

### 1.2 授權事件告警（對應 STRIDE-E：Elevation of Privilege）

| 告警 ID | 事件類型 | 觸發條件 | 嚴重度 | 回應時間 | 通知管道 |
|--------|---------|---------|-------|---------|---------|
| SEC-ALERT-AUTHZ-001 | 越權存取嘗試 | 403 回應率 > 5% 持續 5 分鐘 | P1 | 15 分鐘 | Slack |
| SEC-ALERT-AUTHZ-002 | 管理員 API 呼叫 | 任何 /admin/* 端點被呼叫 | P1 | 15 分鐘 | Slack + Email |
| SEC-ALERT-AUTHZ-003 | 權限提升嘗試 | 嘗試存取超出角色範圍資源 | P0 | 立即 | PagerDuty |

### 1.3 注入攻擊告警（對應 STRIDE-T：Tampering）

| 告警 ID | 事件類型 | 觸發條件 | 嚴重度 | 回應時間 |
|--------|---------|---------|-------|---------|
| SEC-ALERT-INJ-001 | SQL Injection 偵測 | WAF 偵測 SQLi 模式 | P0 | 立即 |
| SEC-ALERT-INJ-002 | XSS 攻擊偵測 | WAF 偵測 XSS Payload | P1 | 15 分鐘 |
| SEC-ALERT-INJ-003 | Command Injection 偵測 | WAF 偵測命令注入模式 | P0 | 立即 |

### 1.4 DDoS/服務拒絕告警（對應 STRIDE-D）

| 告警 ID | 事件類型 | 觸發條件 | 嚴重度 | 回應時間 |
|--------|---------|---------|-------|---------|
| SEC-ALERT-DOS-001 | 流量異常激增 | 請求量 5 分鐘內增加 300% | P0 | 立即 |
| SEC-ALERT-DOS-002 | Rate Limit 觸發率高 | 429 回應率 > 10% 持續 5 分鐘 | P1 | 15 分鐘 |
| SEC-ALERT-DOS-003 | 慢速攻擊偵測 | 同一 IP 大量長連接 | P1 | 15 分鐘 |

### 1.5 資訊洩漏告警（對應 STRIDE-I）

| 告警 ID | 事件類型 | 觸發條件 | 嚴重度 |
|--------|---------|---------|-------|
| SEC-ALERT-INFO-001 | 大量資料匯出 | 單次 API 回傳 > {N}MB 或 > {N}條記錄 | P1 |
| SEC-ALERT-INFO-002 | 敏感欄位異常存取 | PII 欄位存取量異常（> 平均 3 倍） | P1 |
| SEC-ALERT-INFO-003 | 未授權資料查詢 | 非正常業務時間的大量查詢 | P1 |

---

## 2. SIEM 規則規格

### 2.1 Prometheus/Grafana 告警規則

```yaml
# 暴力破解告警
groups:
  - name: security_alerts
    rules:
      - alert: BruteForceDetected
        expr: |
          increase(auth_failures_total[5m]) > 10
        for: 1m
        labels:
          severity: critical
          category: authentication
        annotations:
          summary: "暴力破解嘗試偵測"
          description: "IP {{ $labels.ip }} 5分鐘內失敗登入 {{ $value }} 次"
          runbook: "https://runbook/brute-force"

      - alert: MassDataExport
        expr: |
          increase(api_response_size_bytes_total{endpoint=~"/api/export.*"}[10m]) > 104857600
        for: 2m
        labels:
          severity: high
          category: data_exfiltration
        annotations:
          summary: "異常大量資料匯出偵測"
          description: "端點 {{ $labels.endpoint }} 10分鐘內匯出 {{ $value | humanizeBytes }}"
```

### 2.2 日誌分析規則（ELK/Splunk）

```
# SQL Injection 偵測
查詢: request_body:("' OR" OR "1=1" OR "UNION SELECT" OR "DROP TABLE")
告警: 任何匹配 → SEC-ALERT-INJ-001

# 異常時間存取
查詢: user_role:admin AND timestamp:[00:00 TO 06:00]
告警: 任何匹配 → SEC-ALERT-AUTH-004

# 大量 403 錯誤
查詢: http_status:403
告警: 5分鐘內 count > 50 → SEC-ALERT-AUTHZ-001
```

---

## 3. 安全事件嚴重度分級

| 嚴重度 | 定義 | 首次回應 | 緩解目標 | 通知對象 |
|-------|------|---------|---------|---------|
| P0 - Critical | 正在發生的攻擊，資料可能外洩 | 5 分鐘 | 30 分鐘 | 全員 + 管理層 |
| P1 - High | 高風險異常行為，需立即調查 | 15 分鐘 | 2 小時 | 安全團隊 |
| P2 - Medium | 可疑行為，需調查評估 | 1 小時 | 1 天 | 安全工程師 |
| P3 - Low | 輕微異常，定期審查 | 1 天 | 1 週 | 日誌記錄 |

---

## 4. 安全監控儀表板規格

| 儀表板 | 核心指標 | 更新頻率 |
|-------|---------|---------|
| Authentication Overview | 登入成功/失敗率、帳號鎖定趨勢 | 即時 |
| Attack Detection | WAF 阻擋事件、注入嘗試次數 | 即時 |
| Authorization Monitor | 403 錯誤率、RBAC 違規次數 | 即時 |
| Data Access Audit | PII 存取量、異常匯出事件 | 5 分鐘 |
| Compliance Dashboard | 安全控制狀態、OWASP 覆蓋率 | 每日 |

---

## 5. 安全告警響應 Runbook

| 告警 ID | Runbook 連結 | 初步響應步驟 |
|--------|------------|------------|
| SEC-ALERT-AUTH-001 | {runbook_url} | 1. 封鎖來源 IP 2. 調查是否為 Pen Test 3. 通報 INCIDENT |
| SEC-ALERT-INJ-001 | {runbook_url} | 1. WAF 規則確認 2. 查詢 DB 是否被竄改 3. 啟動 IR |
| SEC-ALERT-DOS-001 | {runbook_url} | 1. 啟用 DDoS 防護 2. 擴容評估 3. 封鎖來源 IP 範圍 |

---

## 6. 與 Incident Response 的整合

```
觸發 P0 告警
  → 自動建立 Incident Ticket
  → 通知 On-Call Security Engineer
  → 啟動 INCIDENT-RESPONSE-SPEC 流程
  → 72 小時內評估是否需 GDPR Art.33 通報
```

---

> **參考文件**:
> - STRIDE 威脅模型: STRIDE-THREAT-MODEL-{system}.md
> - 事件回應規格: INCIDENT-RESPONSE-SPEC-{system}.md
> - 安全測試規格: SECURITY-TEST-SPEC-{system}.md
