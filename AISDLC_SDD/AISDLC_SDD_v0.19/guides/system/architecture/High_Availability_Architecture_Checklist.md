# 高可用性架構設計檢查清單
# High Availability (HA) Architecture Checklist

**版本**: v0.01
**建立日期**: 2025-12-13
**文檔類型**: 系統參考文件 - 架構設計
**適用階段**: Greenfield SOP Stage 3（系統架構設計）
**目標使用者**: SD (System Designer), DevOps Engineer, SA

---

## 🎯 文檔目的

本檢查清單協助 **SD-Architect Agent** 在 **Stage 3（系統架構設計）** 執行 **C4 Model Level 2/3** 設計時，確保高可用性（HA）元件完整納入部署架構，避免上線後單點故障（SPOF）導致系統停機。

**核心原則**: **High Availability by Design（設計階段內建高可用性）**

---

## 📋 使用時機

### 何時使用此檢查清單？

**必須使用**:
- ✅ Greenfield SOP Stage 3.4（C4 Level 2 Container Diagram）
- ✅ Greenfield SOP Stage 3.5（Deployment Architecture Design）
- ✅ SRD「部署架構設計」章節撰寫

**建議使用**:
- 🟡 架構審查會議前（Architecture Review）
- 🟡 生產環境上線前評估（Pre-Production Checklist）
- 🟡 災難復原計畫制定時（DR Planning）

---

## 🏗️ HA 元件強制清單（4 大類別）

根據系統 SLA 需求（通常 ≥ 99.9%），以下 4 類 HA 元件 **必須** 在 C4 Model Level 2 及部署架構中明確設計：

---

### 1️⃣ 負載均衡器（Load Balancer）

**對應 SLA**: 99.9% (單點故障會導致整體停機)

#### C4 Level 2 Container Diagram 檢查清單

- [ ] **Application Load Balancer (ALB)**
  - **位置**: 前端與 API Gateway 之間
  - **技術選型已定義**:
    - [ ] AWS ALB / ELB
    - [ ] NGINX (Self-hosted)
    - [ ] Azure Load Balancer
    - [ ] GCP Load Balancer
  - **負載分配策略**:
    - [ ] Round Robin（輪詢）
    - [ ] Least Connections（最少連線）
    - [ ] IP Hash（會話保持）
  - **健康檢查機制**:
    - [ ] HTTP Health Check (GET /health)
    - [ ] 健康檢查間隔: 30 秒
    - [ ] 失敗閾值: 連續 3 次失敗即移除節點

- [ ] **Database Load Balancer (可選)**
  - **適用場景**: 讀寫分離架構
  - **技術選型**:
    - [ ] ProxySQL (MySQL)
    - [ ] PgBouncer (PostgreSQL)
    - [ ] AWS RDS Proxy

#### 部署架構檢查清單

- [ ] **多 AZ 部署**
  - [ ] Load Balancer 跨 2+ Availability Zones
  - [ ] 單一 AZ 故障不影響服務

- [ ] **Auto Scaling 整合**
  - [ ] 定義 Auto Scaling Policy（CPU > 70% 或 Request Count > 1000/min）
  - [ ] Min Instances: 2
  - [ ] Max Instances: 10

---

### 2️⃣ 應用層高可用性（Application Layer HA）

**對應 SLA**: 99.9% (應用層多實例部署)

#### C4 Level 2 Container Diagram 檢查清單

- [ ] **Application Server 多實例部署**
  - **部署策略已定義**:
    - [ ] Blue-Green Deployment
    - [ ] Rolling Update
    - [ ] Canary Deployment
  - **實例數量規劃**:
    - [ ] 生產環境最小實例數: ≥ 2
    - [ ] 每個 AZ 至少 1 個實例
  - **Session 管理**:
    - [ ] Stateless Design（推薦）
    - [ ] Session Sticky（如需 Stateful）
    - [ ] Redis Session Store（分散式 Session）

- [ ] **Microservices HA 設計**
  - **服務隔離**:
    - [ ] 每個 Microservice 獨立部署
    - [ ] 服務故障不影響其他服務（Circuit Breaker）
  - **服務發現**:
    - [ ] Consul / Eureka / Kubernetes Service Discovery
  - **API Gateway HA**:
    - [ ] API Gateway 多實例部署
    - [ ] Rate Limiting 分散式儲存（Redis）

#### 部署架構檢查清單

- [ ] **Container Orchestration**
  - **技術選型**:
    - [ ] Kubernetes (推薦)
    - [ ] Docker Swarm
    - [ ] AWS ECS/Fargate
  - **副本數量設定**:
    - [ ] ReplicaSet/Deployment replicas ≥ 2
    - [ ] Pod Anti-Affinity（跨節點部署）

- [ ] **健康檢查與自動重啟**
  - [ ] Liveness Probe（存活檢查）
  - [ ] Readiness Probe（就緒檢查）
  - [ ] 失敗自動重啟機制

---

### 3️⃣ 資料庫高可用性（Database HA）

**對應 SLA**: 99.95% (資料層故障影響最嚴重)

#### C4 Level 2 Container Diagram 檢查清單

- [ ] **Database Replication (資料庫複製)**
  - **架構模式已選擇**:
    - [ ] Master-Slave Replication（一主多從）
    - [ ] Master-Master Replication（雙主）
    - [ ] Multi-AZ Deployment（AWS RDS）
  - **技術實作**:
    - [ ] PostgreSQL Streaming Replication
    - [ ] MySQL Master-Slave Replication
    - [ ] MongoDB Replica Set
  - **複製延遲監控**:
    - [ ] Replication Lag < 5 秒
    - [ ] 延遲超過閾值觸發告警

- [ ] **讀寫分離（Read-Write Splitting）**
  - **實作方式**:
    - [ ] Application 層分離（推薦）
    - [ ] Database Proxy（ProxySQL / PgBouncer）
  - **讀寫比例**:
    - [ ] 預估讀寫比: 80/20（80% 讀取）
    - [ ] Slave 節點數量: ≥ 2

- [ ] **自動故障轉移（Automatic Failover）**
  - **技術選型**:
    - [ ] AWS RDS Multi-AZ（自動故障轉移）
    - [ ] PostgreSQL Patroni + etcd
    - [ ] MySQL MHA (Master High Availability)
  - **RTO/RPO 目標**:
    - [ ] RTO (Recovery Time Objective): < 5 分鐘
    - [ ] RPO (Recovery Point Objective): < 1 分鐘

#### 部署架構檢查清單

- [ ] **Multi-AZ 部署**
  - [ ] Master 與 Slave 位於不同 AZ
  - [ ] 單一 AZ 故障不影響資料庫可用性

- [ ] **備份策略**
  - [ ] 自動每日備份（Automated Daily Backup）
  - [ ] 備份保留期限: ≥ 7 天
  - [ ] 定期備份測試（每月驗證還原流程）

---

### 4️⃣ 快取與訊息佇列高可用性（Cache & Queue HA）

**對應 SLA**: 99.9% (快取故障影響效能，佇列故障影響資料一致性)

#### C4 Level 2 Container Diagram 檢查清單

- [ ] **Redis Cluster / Sentinel**
  - **架構模式已選擇**:
    - [ ] Redis Sentinel（主從架構 + 自動故障轉移）
    - [ ] Redis Cluster（分散式架構）
    - [ ] AWS ElastiCache for Redis（Multi-AZ）
  - **節點配置**:
    - [ ] Master 節點數: ≥ 1
    - [ ] Slave 節點數: ≥ 2
    - [ ] Sentinel 節點數: ≥ 3（奇數）
  - **持久化策略**:
    - [ ] RDB（定期快照）
    - [ ] AOF（Append-Only File）
    - [ ] 混合持久化（RDB + AOF）

- [ ] **Message Queue HA**
  - **技術選型**:
    - [ ] RabbitMQ Cluster
    - [ ] Kafka Cluster（分散式）
    - [ ] AWS SQS / SNS（託管服務）
  - **副本配置**:
    - [ ] RabbitMQ: Mirrored Queue（鏡像佇列）
    - [ ] Kafka: Replication Factor ≥ 3
  - **訊息持久化**:
    - [ ] 訊息持久化至磁碟
    - [ ] 消費者確認機制（ACK）

#### 部署架構檢查清單

- [ ] **Multi-AZ 部署**
  - [ ] Redis/Kafka 節點分散於不同 AZ
  - [ ] 單一 AZ 故障不影響快取/佇列服務

- [ ] **監控與告警**
  - [ ] Redis Memory Usage > 80% 告警
  - [ ] Kafka Lag Monitoring（消費延遲監控）
  - [ ] Message Queue Depth > 10000 告警

---

## 🔍 C4 Level 2 HA 架構整合範例

### 範例：BnB 訂房系統 HA 架構 (含 4 大類別)

```
┌────────────────────────────────────────────────────────────────┐
│            BnB Platform - HA Deployment Architecture           │
└────────────────────────────────────────────────────────────────┘

👤 使用者 (Web/Mobile)
   │
   │ HTTPS
   ↓
┌──────────────────────────────────────────────────────────────┐
│  1️⃣ AWS ALB (Application Load Balancer)                     │
│  - Multi-AZ: ap-northeast-1a, 1c                            │
│  - Health Check: GET /health (30s interval)                 │
└──────────────────────────────────────────────────────────────┘
   │
   ├──→ AZ-1a ┌────────────────────┐  ┌────────────────────┐
   │          │ 2️⃣ API Server (x2) │  │ 2️⃣ Booking Service │
   │          │  [Node.js Pod]     │  │  [Node.js Pod]     │
   │          └────────────────────┘  └────────────────────┘
   │
   └──→ AZ-1c ┌────────────────────┐  ┌────────────────────┐
              │ 2️⃣ API Server (x2) │  │ 2️⃣ Booking Service │
              │  [Node.js Pod]     │  │  [Node.js Pod]     │
              └────────────────────┘  └────────────────────┘
                  │                        │
                  ↓                        ↓
┌──────────────────────────────────────────────────────────────┐
│  3️⃣ AWS RDS PostgreSQL (Multi-AZ)                           │
│  - Master: ap-northeast-1a                                  │
│  - Standby: ap-northeast-1c                                 │
│  - Automatic Failover: < 2 min                              │
│  - Backup Retention: 7 days                                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  4️⃣ AWS ElastiCache Redis (Cluster Mode)                    │
│  - Primary Node: ap-northeast-1a                            │
│  - Replica Nodes: ap-northeast-1c (x2)                      │
│  - Automatic Failover Enabled                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  監控與告警 (CloudWatch / Prometheus)                        │
│  - ALB 5xx Error Rate > 5% → 告警                           │
│  - API Server CPU > 80% → Auto Scaling                      │
│  - RDS Replication Lag > 10s → 告警                         │
│  - Redis Memory Usage > 85% → 告警                          │
└──────────────────────────────────────────────────────────────┘
```

---

## ✅ Stage 3 HA 架構設計完整檢查清單

### 階段 1: C4 Level 2 Container Diagram HA 檢查

- [ ] **1️⃣ 負載均衡器已定義**
  - [ ] Application Load Balancer 已標示技術棧
  - [ ] 健康檢查機制已說明
  - [ ] Auto Scaling 整合已規劃

- [ ] **2️⃣ 應用層 HA 已定義**
  - [ ] Application Server 多實例部署已標示
  - [ ] Session 管理策略已說明
  - [ ] Microservices HA 設計已規劃

- [ ] **3️⃣ 資料庫 HA 已定義**
  - [ ] Database Replication 架構已標示
  - [ ] 讀寫分離機制已說明
  - [ ] 自動故障轉移已規劃

- [ ] **4️⃣ 快取與佇列 HA 已定義**
  - [ ] Redis Cluster/Sentinel 已標示
  - [ ] Message Queue HA 已規劃
  - [ ] 持久化策略已說明

### 階段 2: Deployment Architecture Design HA 檢查

- [ ] **Multi-AZ 部署已設計**
  - [ ] 所有關鍵元件跨 2+ AZ 部署
  - [ ] 單一 AZ 故障不影響服務（SPOF 已消除）

- [ ] **Auto Scaling 已配置**
  - [ ] 定義 Scaling Policy（CPU / Request Count）
  - [ ] Min/Max Instances 已設定
  - [ ] Scaling 測試計畫已規劃

- [ ] **監控與告警已設計**
  - [ ] 定義關鍵監控指標（CPU, Memory, Latency, Error Rate）
  - [ ] 告警閾值已設定
  - [ ] On-Call 輪值機制已規劃

### 階段 3: SRD 文檔整合檢查

- [ ] **SRD「部署架構設計」章節已撰寫**
  - [ ] 包含 HA 架構圖（C4 Level 2 + Deployment Diagram）
  - [ ] 對應 NFR-AVL-xxx 可用性需求
  - [ ] 每個 HA 元件有詳細技術規格

- [ ] **災難復原計畫已撰寫**
  - [ ] RTO/RPO 目標已定義
  - [ ] Failover 流程已說明
  - [ ] 備份與還原測試計畫已規劃

- [ ] **SLA 計算已完成**
  - [ ] 計算整體系統 SLA（依賴鏈 SLA 相乘）
  - [ ] 識別 SLA 瓶頸元件
  - [ ] 提出 SLA 改進方案

### 階段 4: 架構審查會議檢查

- [ ] **SD 審查**: HA 架構設計完整性
- [ ] **DevOps 審查**: 部署可行性與成本評估
- [ ] **SA 審查**: 需求追蹤完整性（NFR-AVL → HA 元件）
- [ ] **PM 確認**: 成本與時程可行性

---

## 📊 預期效益

### 執行 HA 架構設計後：

| 指標 | 改進前 | 改進後 | 提升幅度 |
|------|--------|--------|---------|
| **系統可用性 (Uptime)** | 95% | 99.9% | ↑ 4.9% |
| **單點故障 (SPOF) 數量** | 5 個 | 0 個 | ↓ 100% |
| **平均故障恢復時間 (MTTR)** | 30 分鐘 | 5 分鐘 | ↓ 83% |
| **年度停機時間** | 18.25 天 | 8.76 小時 | ↓ 98% |

**ROI 評估**:
- **投入成本**: 3 人日（SD 2 人日 + DevOps 1 人日）
- **預期效益**: 避免停機損失 $50k/年（假設停機成本 $100/小時）
- **ROI**: 83:1

**可用性計算**:
```
改進前 95% = 年度停機 18.25 天
改進後 99.9% = 年度停機 8.76 小時

停機減少: 18.25 天 - 8.76 小時 = 17.88 天 = 429 小時
成本節省: 429 小時 × $100/小時 = $42,900
```

---

## 📚 相關文檔

- [Security_Architecture_Checklist.md](./Security_Architecture_Checklist.md) - 安全架構檢查清單
- [C4_Model_Guidelines.md](./C4_Model_Guidelines.md) - C4 Model 完整指南
- [FRD_Universal_Template.md](../../../docs_template/core/frd/FRD_Universal_Template.md) - FRD 模板（可用性需求章節）
- [SRD_Universal_Template.md](../../../docs_template/core/srd/SRD_Universal_Template.md) - SRD 模板（部署架構章節）

---

**維護記錄**:
- v0.01 (2025-12-13): 初版建立（P2-8 改進項目）
