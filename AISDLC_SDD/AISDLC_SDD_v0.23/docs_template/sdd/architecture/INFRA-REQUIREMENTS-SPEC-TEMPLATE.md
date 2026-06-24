# Infrastructure Requirements Spec — 基礎設施需求規格模板
# 使用說明：複製至 docs/02_architecture/INFRA-REQUIREMENTS-SPEC-{system}.md 後填寫

**系統名稱**: {SystemName}
**版本**: v1.0
**建立日期**: {date}
**SCG 狀態**: 待 SCG-2 凍結
**前置文件**: `SRD-{system}.md`（非功能需求章節）

---

## 1. 可用性目標（RTO / RPO）

| 指標 | 定義 | 目標值 | 說明 |
|------|------|--------|------|
| **RTO**（Recovery Time Objective） | 故障後最大恢復時間 | {N 分鐘/小時} | 超過此時間視為 SLA 違反 |
| **RPO**（Recovery Point Objective） | 最大可接受資料遺失時間 | {N 分鐘} | 決定備份頻率 |
| **可用性 SLO** | 年度可用性目標 | {99.9 / 99.95 / 99.99}% | 對應最大停機時間 |
| **MTTR**（Mean Time to Recover） | 平均恢復時間 | < {N 分鐘} | 運維效率指標 |

---

## 2. 計算資源規格（CPU / Memory / Storage SLO）

### 2.1 應用層

| 服務 | CPU（cores） | Memory（GB） | 副本數（Min/Max） | 自動擴展觸發 |
|------|------------|------------|----------------|------------|
| {Service-A} | {N}c / {N}c limit | {N}GB / {N}GB limit | {min}/{max} | CPU > {%} |
| {Service-B} | {N}c / {N}c limit | {N}GB / {N}GB limit | {min}/{max} | RPS > {N} |
| {Service-N} | {N}c / {N}c limit | {N}GB / {N}GB limit | {min}/{max} | {條件} |

### 2.2 資料庫層

| 資料庫 | 類型 | 規格 | 儲存空間 | IOPS | 副本策略 |
|--------|------|------|---------|------|---------|
| {DB-A} | {RDS/PostgreSQL/MySQL} | {instance type} | {N}GB (成長 {N}%/月) | {N} IOPS | 1 Primary + {N} Read Replica |
| {DB-N} | {類型} | {規格} | {N}GB | {N} IOPS | {副本策略} |

### 2.3 儲存規格

| 儲存類型 | 用途 | 容量 | 成長率 | 保留期 |
|---------|------|------|--------|--------|
| Object Storage（S3/GCS） | {用途} | {N}GB | {N}%/月 | {N 天/年} |
| Block Storage | {用途} | {N}GB | {N}%/月 | — |
| Cache（Redis） | {用途} | {N}GB | — | TTL: {N}s |

---

## 3. 網路拓撲規格

```
[網路架構圖 — Mermaid]

Internet
    ↓
[CDN / WAF]
    ↓
[Load Balancer（Public Subnet）]
    ↓
[Application Tier（Private Subnet）]
    ↓
[Database Tier（Isolated Subnet）]
```

### 3.1 VPC / 網路分區

| 子網路 | CIDR | 用途 | 存取控制 |
|--------|------|------|---------|
| Public Subnet | {CIDR} | Load Balancer, NAT Gateway | Internet 可達 |
| Private Subnet | {CIDR} | Application Services | 僅 LB 可達 |
| Isolated Subnet | {CIDR} | Database, Cache | 僅 App 可達 |

### 3.2 安全邊界規格

| 規則 | Source | Destination | Port | Protocol |
|------|--------|-------------|------|---------|
| HTTPS 入站 | 0.0.0.0/0 | Load Balancer | 443 | TCP |
| App → DB | {App Subnet} | {DB Subnet} | {5432/3306} | TCP |
| 禁止 DB 出站 | {DB Subnet} | 0.0.0.0/0 | ALL | ALL |

---

## 4. 部署環境規格

| 環境 | 用途 | 資源規格 | 資料來源 | 存取控制 |
|------|------|---------|---------|---------|
| Development | 開發測試 | {最小規格} | 隔離測試資料 | 開發團隊 |
| Staging | 整合測試/UAT | {中等規格，接近 Prod} | 去識別化生產資料 | QA + PM |
| Production | 生產環境 | {正式規格} | 生產資料 | 嚴格 RBAC |

### 環境一致性保證（IaC）
- Dev / Staging / Production 使用**相同 IaC 模板**，僅 `{env}.tfvars` 不同
- 任何環境差異必須有 ADR 記錄並說明原因

---

## 5. SLO 摘要

| SLO 類型 | 目標 | 計算方式 | 警告閾值 | 違反閾值 |
|---------|------|---------|---------|---------|
| 可用性 | {99.9}% | (成功請求 / 總請求) * 100 | < {99.7}% | < {99.5}% |
| P95 延遲 | < {N}ms | 95th percentile 回應時間 | > {N}ms | > {N}ms |
| P99 延遲 | < {N}ms | 99th percentile 回應時間 | > {N}ms | > {N}ms |
| 錯誤率 | < {%} | (5xx 回應 / 總回應) * 100 | > {%} | > {%} |

---

## 6. SCG-2 凍結確認

- [ ] RTO/RPO 目標已定義並業務確認
- [ ] 所有服務資源規格已定義
- [ ] 網路拓撲已設計並審查
- [ ] 安全邊界規格已定義（對應安全 ADR）
- [ ] 部署架構 ADR 已建立（`ADR-DEPLOYMENT-{NNN}.md`）
- [ ] 🔴 Human 確認：基礎設施規格凍結

**最後更新**: {date}
