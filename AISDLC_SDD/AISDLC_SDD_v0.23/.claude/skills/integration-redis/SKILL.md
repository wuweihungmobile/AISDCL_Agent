---
name: integration-redis
description: Redis 快取整合，Cache Contract 定義快取鍵規範，ADR 記錄快取策略，NFR 量化命中率
user-invocable: true
disable-model-invocation: false
argument-hint: "<use_case: cache|session|queue|pubsub|all> [framework: nodejs|python|java]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Integration Redis Skill（SDD 原生）

Redis 整合在 SDD 中必須設計先行：快取策略需有 ADR（Cache Aside / Write Through / Write Behind），Cache Contract 定義所有快取鍵的格式和 TTL，NFR 量化快取命中率目標，整合結果 RTM 追蹤。

---

## 觸發方式

```bash
/integration-redis cache nodejs
/integration-redis session
/integration-redis queue python
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-2 通過 | 快取架構確定 | `docs/02_architecture/SRD-{System}.md` 快取架構章節 |
| NFR 效能需求 | 效能 NFR 已量化 | NFR-P001（回應時間）作為快取目標依據 |

---

## 執行流程

### 階段 1：快取策略 ADR

呼叫 `/adr-generate "Redis 快取策略"`：

```markdown
# ADR-{NNN}: Redis 快取策略

## Decision
使用 Cache Aside（Lazy Loading）模式，TTL = {NFR 決定}

## Rationale（對應 NFR）
| 快取模式 | 適用場景 | 選擇依據 |
|---------|---------|---------|
| Cache Aside | 讀多寫少 | 當前主要查詢模式（NFR-P001）|
| Write Through | 寫入頻繁 | 用於 Session（NFR-SEC 要求）|

## NFR 對應
- 目標快取命中率：> {NFR-P004：快取命中率 SLO}%
- 快取逐出策略：allkeys-lru（記憶體壓力下）
- 最大記憶體：{NFR-R002：Redis 記憶體上限}

## Security
- 資料不含 PII（或加密後才快取）
- Redis AUTH 必須啟用
- 不快取認證 Token（安全要求）
```

---

### 階段 2：Cache Contract（快取鍵規範）

**文件路徑**：`docs/02_architecture/INTEGRATION-SPEC-Redis-Cache-{System}.md`

```markdown
# Cache Contract — {System}

**格式**: `{namespace}:{resource_type}:{id}`
**版本**: {N}.{N}（修改快取鍵格式需更新此文件）

## 快取鍵清單（對應 FRD Feature）

| 快取鍵 | TTL | 快取內容 | 使用場景 | FRD Feature | 失效觸發 |
|--------|-----|---------|---------|------------|---------|
| `user:{uid}:profile` | 3600s | 用戶 Profile | 用戶詳情頁 | F-USR-002 | 用戶更新 |
| `product:{id}:detail` | 1800s | 商品詳情 | 商品頁面 | F-PROD-001 | 商品更新 |
| `session:{token}` | 86400s | 用戶 Session | 認證 | F-AUTH-001 | 登出 |

## 快取失效策略

| 場景 | 失效方式 | 說明 |
|------|---------|------|
| 用戶更新 | DEL user:{uid}:* | 主動失效 |
| 商品更新 | DEL product:{id}:detail | 主動失效 |
| Session 登出 | DEL session:{token} | 主動失效 |

## 不可快取的資料（安全要求）
- 認證 Token / 密碼
- 支付相關 PAN 資料
- 包含 PII 的完整用戶資料（需加密）
```

---

### 階段 3：NFR 監控（對應 devops-monitoring）

快取 NFR 需在監控中設定告警：

```yaml
# prometheus/rules/nfr-alerts.yml 中新增
- alert: CacheHitRateLow
  expr: redis_keyspace_hits / (redis_keyspace_hits + redis_keyspace_misses) < 0.8
  for: 10m
  labels:
    severity: warning
    nfr_id: "NFR-P004"
  annotations:
    summary: "Redis 快取命中率低於 NFR-P004 目標（80%）"
```

---

### 階段 4：RTM 更新 🔴

```bash
/rtm-generate update
/spec-compliance-check docs/02_architecture/INTEGRATION-SPEC-Redis-Cache-{System}.md
```

🔴 確認點：快取 TC（TC-CACHE-XXX）包含快取命中 / Miss / 失效三種場景。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| 快取策略 ADR | `docs/02_architecture/adr/ADR-{NNN}-cache-strategy.md` | SCG-2 |
| Cache Contract | `docs/02_architecture/INTEGRATION-SPEC-Redis-Cache-{System}.md` | SCG-2 |

---

**基於**: AISDLC-SDD v0.23
**對應情境**: Integration 場景
