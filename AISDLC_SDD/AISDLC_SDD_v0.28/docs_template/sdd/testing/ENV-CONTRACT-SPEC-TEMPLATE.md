# Environment Contract Spec — 環境契約測試規格模板
# 使用說明：複製至 docs/03_testing/contracts/ENV-CONTRACT-SPEC-{project}.md 後填寫

**專案名稱**: {ProjectName}
**版本**: v1.0
**建立日期**: {date}
**目的**: 確保 Dev / Staging / Production 環境行為一致，消除「在我機器上是好的」問題
**spec-format-version**: 1.0  <!-- improving_85：AutoClaude SddToPlaybookAdapter 防漂移閘讀取（_SUPPORTED_SPEC_FORMAT_VERSIONS）；本契約格式跨版不相容演進時 bump 並同步 adapter 支援集 -->

---

## 1. 環境一致性原則

> IaC as Spec：Dev / Staging / Production 使用相同 IaC 模板，僅環境變數不同

| 差異類型 | 是否允許 | 說明 |
|---------|---------|------|
| 資源規格（CPU/Memory） | ✅ 允許 | Dev 可小於 Prod |
| 網路拓撲 | ❌ 禁止 | 所有環境網路架構一致 |
| 軟體版本（Runtime/DB） | ❌ 禁止 | 版本必須完全一致 |
| 環境變數名稱 | ❌ 禁止 | 名稱一致，值可不同 |
| 安全配置 | ❌ 禁止 | 安全策略必須一致 |

---

## 2. 環境間行為契約測試

### TCS-ENV-001：Runtime 版本一致性

```yaml
test_case: TCS-ENV-001
name: "所有環境 Runtime 版本相同"
given:
  - Dev / Staging / Production 均已部署
when:
  - 查詢各環境 Runtime 版本
  - GET {health-endpoint}/version
then:
  - 所有環境回應的 runtime_version 欄位相同
  - 例如：node: "20.x.x"（三環境一致）
pass_criteria: 100% 版本一致
```

### TCS-ENV-002：API 端點行為一致性

```yaml
test_case: TCS-ENV-002
name: "相同請求在所有環境產生等價回應"
given:
  - 使用相同測試資料集
when:
  - 對 Dev、Staging、Production 發送相同請求
then:
  - HTTP Status Code 相同
  - Response Schema 相同
  - 業務邏輯計算結果相同（非環境敏感資料）
pass_criteria: 三環境回應語義等價
```

### TCS-ENV-003：環境變數完整性

```yaml
test_case: TCS-ENV-003
name: "所有必要環境變數在各環境均存在"
given:
  - 定義必要環境變數清單（見 Section 3）
when:
  - 啟動各環境應用
then:
  - 無任何「環境變數未設定」錯誤
  - 應用健康端點回應 HTTP 200
pass_criteria: 所有環境啟動成功，無缺失變數
```

### TCS-ENV-004：資料庫 Schema 一致性

```yaml
test_case: TCS-ENV-004
name: "所有環境資料庫 Schema 版本一致"
given:
  - 所有環境均執行了相同的 Migration Scripts
when:
  - 查詢各環境 schema_version
then:
  - 三環境 schema_version 相同
pass_criteria: 100% Schema 版本一致
```

### TCS-ENV-005：網路連通性一致性

```yaml
test_case: TCS-ENV-005
name: "服務間網路路徑一致（相同拓撲）"
given:
  - 各環境按相同網路拓撲部署
when:
  - Service A → Service B 連通性測試
  - Service A → DB 連通性測試
then:
  - 連通性結果一致（均可達或均不可達）
  - 無「Dev 可達但 Prod 不可達」情況
```

---

## 3. 必要環境變數清單

| 變數名稱 | 必填 | Dev 值示例 | Staging 值示例 | Prod 值示例 |
|---------|------|-----------|--------------|------------|
| `DATABASE_URL` | ✅ | `postgres://dev-db:5432/...` | `postgres://stg-db:5432/...` | `postgres://prod-db:5432/...` |
| `REDIS_URL` | ✅ | `redis://dev-cache:6379` | `redis://stg-cache:6379` | `redis://prod-cache:6379` |
| `APP_ENV` | ✅ | `development` | `staging` | `production` |
| `LOG_LEVEL` | ✅ | `debug` | `info` | `warn` |
| `{VAR_NAME}` | {✅/⬜} | {值} | {值} | {值} |

---

## 4. IaC 注解規格

每段 IaC 必須包含以下注解：

```hcl
# Spec: INFRA-{NNN} — {對應需求說明}
# ENV: dev/staging/prod 均適用（差異見 {env}.tfvars）
# Reason: {為何這樣配置}
resource "aws_instance" "app_server" {
  # ...
}
```

---

## 5. 環境漂移偵測

```yaml
# 定期執行（建議每日）
env_drift_detection:
  schedule: "0 6 * * *"
  checks:
    - type: "version_comparison"
      target: "runtime, db_engine, cache_version"
    - type: "schema_version_comparison"
      target: "all databases"
    - type: "config_key_comparison"
      target: "environment variables"
  alert_on: "any_drift_detected"
  notify: "#devops-alerts"
```

---

## 6. 測試執行策略

| 測試時機 | 測試範圍 | 負責人 |
|---------|---------|--------|
| 新環境建立後 | TCS-ENV-001 ~ TCS-ENV-005 全套 | DevOps |
| 每次 IaC 變更後 | TCS-ENV-003 ~ TCS-ENV-004 | DevOps |
| 每次 Deploy 後 | TCS-ENV-002（Smoke） | CI/CD 自動 |
| 每日排程 | 環境漂移偵測 | CI/CD 自動 |

**最後更新**: {date}
