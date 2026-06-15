# CI/CD Pipeline 配置範本
# CI/CD Pipeline Configuration Template

> **🎯 文檔目的**
>
> 本範本提供 **CI/CD Pipeline 的標準化配置指引**，涵蓋主流 CI/CD 平台與最佳實踐。
>
> - **適用階段**: Stage 8 - 開發準備階段
> - **適用平台**: GitHub Actions、GitLab CI、Jenkins、Azure DevOps
> - **執行角色**: DevOps Engineer、SD-Architect、Dev Lead
> - **目標**: 建立自動化、可靠、安全的持續整合與部署流程

---

**版本**: v1.4
**最後更新**: 2026-03-23
**文檔類型**: DevOps 配置範本 | CI/CD
**相關文檔**:
- [Code_Review_Guidelines.md](../../../guides/user/process/Code_Review_Guidelines.md) - Code Review 指南
- [Testing_Plan_Template.md](../testing/Testing_Plan_Template.md) - 測試計畫範本
- [Deployment_Checklist.md](./Deployment_Checklist.md) - 部署檢查清單

---

## 📋 目錄

0. [🔴 Layer 0: Security Baseline（強制）](#layer-0-security-baseline強制)
0.5. [🔴 Layer 1: Build & Verify（強制）](#layer-1-build--verify強制)
0.52. [📦 Immutable Artifact（不可變產物模式）](#immutable-artifact不可變產物模式)
0.55. [🧪 Layer 2: Test Isolation（測試隔離模式）](#layer-2-test-isolation測試隔離模式)
0.6. [🔄 Migration Pipeline（Canary + Rollback）](#migration-pipelinecanary--rollback)
0.7. [🛡️ Security Integration（增強安全掃描）](#security-integration增強安全掃描)
0.8. [⚡ Performance Benchmark Gate（效能基準關卡）](#performance-benchmark-gate效能基準關卡)
0.9. [📝 Documentation Pipeline（文檔 Pipeline）](#documentation-pipeline文檔-pipeline)
0.10. [🔔 Event-Driven Agent Notification（事件驅動 Agent 通知）](#event-driven-agent-notification事件驅動-agent-通知)
1. [CI/CD Pipeline 概覽](#cicd-pipeline-概覽)
2. [GitHub Actions 配置](#github-actions-配置)
3. [GitLab CI 配置](#gitlab-ci-配置)
4. [Jenkins Pipeline 配置](#jenkins-pipeline-配置)
5. [Azure DevOps Pipeline 配置](#azure-devops-pipeline-配置)
6. [通用最佳實踐](#通用最佳實踐)
7. [環境變數管理](#環境變數管理)
8. [部署策略](#部署策略)
9. [監控與告警](#監控與告警)

---

## 🔴 Layer 0: Security Baseline（強制）

> **⚠️ CRITICAL**: Layer 0 是所有 CI/CD Pipeline 的**強制第一階段**，所有情境（greenfield ~ security）的所有 PR 都必須通過 Layer 0 檢查後，才能進入後續 Build/Test/Deploy 階段。

### Layer 0 三大安全支柱

| 支柱 | 目的 | 阻塞等級 | 超時熔斷 |
|------|------|---------|---------|
| **Secret Detection** | 防止機密洩漏（API Key/Token/密碼） | 🔴 永遠阻塞 | 5 分鐘（超時仍阻塞） |
| **Dependency Scan (SCA)** | 掃描已知依賴漏洞 (CVE) | 🔴 CRITICAL/HIGH 阻塞 | 10 分鐘（超時降級警告） |
| **License Compliance** | 確保開源授權相容 | ⚠️ GPL-3.0/AGPL 阻塞 | 5 分鐘（超時降級警告） |

### Pipeline 層級架構

```
Layer 0: Security Baseline ← 你在這裡（強制所有情境）
  ├── Secret Detection (pre-commit + CI)
  ├── Dependency Scan (SCA)
  └── License Compliance
        ↓ 全部通過
Layer 1: Build & Verify（強制所有情境）
  📦 Immutable Artifact（Build Once → Push to Registry）
Layer 2: Quality Assurance（情境選配，使用同一 Artifact）
Layer 3: Deploy & Validate（情境選配，使用同一 Artifact）
```

### 完整配置範本與工具選型

📖 **詳細指南**: [Layer0_Security_Baseline_Template.md](./Layer0_Security_Baseline_Template.md)
📄 **Pre-commit 配置**: [pre-commit-config-template.yaml](./pre-commit-config-template.yaml)
📄 **GitHub Actions**: [github-actions/security-baseline.yml](./github-actions/security-baseline.yml)
📄 **GitLab CI**: [gitlab-ci/security-baseline-template.yml](./gitlab-ci/security-baseline-template.yml)

---

## 🔴 Layer 1: Build & Verify（強制）

> **⚠️ CRITICAL**: Layer 1 是所有 CI/CD Pipeline 的**強制第二階段**，Layer 0 通過後執行。
> 確保程式碼風格一致、編譯成功、單元測試通過且覆蓋率達標。

### Layer 1 三大驗證關卡

| 關卡 | 目的 | 阻塞等級 | 超時 |
|------|------|---------|------|
| **Lint + Format** | 程式碼風格一致性 | 🔴 失敗阻塞 | 5 分鐘 |
| **Compile / Build** | 編譯成功、依賴正確 | 🔴 失敗阻塞 | 10 分鐘 |
| **Unit Test + Coverage** | 邏輯正確、覆蓋率 ≥ 80% | 🔴 失敗或低覆蓋阻塞 | 10 分鐘 |

### 執行順序

```
Lint → (通過) → Build → (通過) → Test + Coverage Gate → (通過) → 📦 Artifact Push → Layer 2
  ↓ 失敗          ↓ 失敗              ↓ 失敗                       (Registry)
  🔴 停止          🔴 停止              🔴 停止
  ※ Build 產出 Immutable Artifact，後續 Layer 2/3 使用同一個（詳見 Immutable Artifact 章節）
```

### 完整配置範本與工具選型

📖 **詳細指南**: [Layer1_Build_Verify_Template.md](./Layer1_Build_Verify_Template.md)
📄 **GitHub Actions**: [github-actions/build-verify.yml](./github-actions/build-verify.yml)
📄 **GitLab CI**: [gitlab-ci/build-verify-template.yml](./gitlab-ci/build-verify-template.yml)

---

## 📦 Immutable Artifact（不可變產物模式）

> **🔴 CRITICAL**: Layer 1 Build 產出的 Artifact 必須是**唯一、不可變的部署單元**。
> 後續 Layer 2 測試、Layer 3 部署**必須使用同一個 Artifact**，禁止在不同環境重新建置。
>
> - **核心原則**: Build Once, Deploy Many
> - **適用範圍**: 所有含容器化部署的情境（greenfield, brownfield, migration, integration, devops）
> - **定位**: Layer 1 Build 的產出規範，Layer 2/Layer 3 的輸入約束

### 為什麼需要不可變產物？

```
問題場景（無不可變產物）：
  CI Build ✅ → 部署 Staging（重新 Build）→ 部署 Production（再次 Build）
  → 三次 Build 的依賴版本可能不同（npm install 拉到新版）
  → CI 測試通過 ≠ Production 環境正確
  → 「CI 過了但 Prod 壞了」

正確做法（不可變產物）：
  CI Build ✅ → 產出 Image:abc123 → Staging 部署 Image:abc123 → Prod 部署 Image:abc123
  → 三個環境 100% 同一個二進位檔
  → CI 測試通過 = Production 環境正確
```

### 不可變產物規則

| # | 規則 | 說明 | 強制等級 |
|---|------|------|---------|
| 1 | **Build Once** | 在 Layer 1 Build 階段產出唯一 Artifact | 🔴 必須 |
| 2 | **Deploy Many** | Layer 2 測試、Layer 3 部署皆使用同一 Artifact | 🔴 必須 |
| 3 | **禁止重新建置** | Staging/Production 禁止執行 `docker build` 或 `npm run build` | 🔴 必須 |
| 4 | **唯一標識** | 每個 Artifact 以 Git SHA + Timestamp 唯一標識 | 🔴 必須 |
| 5 | **完整性校驗** | 部署前以 SHA256 校驗確保產物未被竄改 | 🟡 建議 |
| 6 | **Registry 儲存** | Artifact 推送至 Container Registry / Artifact Repository | 🔴 必須 |

### Artifact 標識與版本策略

```
標識格式：
  {app-name}-{git-sha-short}-{timestamp}

範例：
  myapi-a1b2c3d-20260323T1430    # 開發/PR 版本
  myapi-a1b2c3d-20260323T1430    # Staging 部署（同一個！）
  myapi-a1b2c3d-20260323T1430    # Production 部署（同一個！）

Release Tag：
  myapi:v1.2.3                    # Semantic Versioning（Release 時額外標記）
  myapi:latest                    # 最新穩定版（僅指向，不重建）
```

**Tagging 規則**：

| 事件 | Tag 格式 | 範例 |
|------|---------|------|
| PR / Feature Branch | `{app}:{branch}-{sha}` | `myapi:feat-login-a1b2c3d` |
| Main Branch | `{app}:{sha}-{timestamp}` | `myapi:a1b2c3d-20260323` |
| Release | `{app}:v{semver}` + `{app}:latest` | `myapi:v1.2.3` + `myapi:latest` |

### 完整性校驗 (Integrity Verification)

```bash
# Build 階段：記錄 Artifact SHA256
docker build -t myapi:a1b2c3d .
ARTIFACT_SHA=$(docker inspect --format='{{.Id}}' myapi:a1b2c3d)
echo "$ARTIFACT_SHA" > artifact-sha256.txt

# 部署階段：校驗 Artifact 未被竄改
DEPLOY_SHA=$(docker inspect --format='{{.Id}}' myapi:a1b2c3d)
BUILD_SHA=$(cat artifact-sha256.txt)
if [ "$DEPLOY_SHA" != "$BUILD_SHA" ]; then
  echo "🔴 Artifact 完整性校驗失敗！Build SHA ≠ Deploy SHA"
  exit 1
fi
echo "✅ Artifact 完整性校驗通過"
```

### 多階段 Dockerfile 最佳實踐

```dockerfile
# ============================================================
# Multi-stage Build — 不可變產物最佳實踐
# ============================================================

# Stage 1: Build（建置階段 — 僅在 CI 執行一次）
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --production=false    # 安裝所有依賴（含 devDependencies）
COPY . .
RUN npm run build                # 編譯
RUN npm prune --production       # 移除 devDependencies

# Stage 2: Runtime（執行階段 — 最小化映像）
FROM node:20-alpine AS runtime
WORKDIR /app

# 安全性：非 root 用戶
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# 僅複製必要檔案（不含原始碼、devDependencies）
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

# 環境變數由部署時注入（非 Build 時寫死）
# ❌ ENV DATABASE_URL=postgresql://... （禁止！）
# ✅ 部署時透過 -e 或 ConfigMap 注入

USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q --spider http://localhost:8080/health || exit 1
CMD ["node", "dist/main.js"]
```

### Pipeline 流程中的 Artifact 傳遞

```
Layer 1: Build & Verify
  ├── Lint + Format ✅
  ├── Compile / Build ✅
  ├── Unit Test + Coverage ✅
  └── 📦 Build Artifact（Docker Image / JAR / Bundle）
        ↓ Push to Registry
        ↓ 記錄 SHA256
        ↓
Layer 2: Quality Assurance（使用同一 Artifact）
  ├── Integration Test（拉取 Registry 中的 Image）
  ├── Contract Test
  └── Security Scan（掃描同一 Image）
        ↓
Layer 3: Deploy & Validate（使用同一 Artifact）
  ├── Deploy to Staging（拉取同一 Image）
  ├── Smoke Test
  ├── Deploy to Production（拉取同一 Image）
  └── SHA256 校驗 ✅
```

### 反模式清單

| # | 反模式 | 問題 | 正確替代 |
|---|--------|------|---------|
| 1 | ❌ 每個環境各自 `docker build` | 依賴版本飄移，環境不一致 | ✅ Build 一次，Push to Registry |
| 2 | ❌ `npm install` 在 Staging/Prod 執行 | 可能拉到不同版本的套件 | ✅ 使用 CI Build 產出的 Image |
| 3 | ❌ Image Tag 使用 `latest` 部署 | 無法追溯版本，無法回滾 | ✅ 使用 `{sha}` 或 `v{semver}` Tag |
| 4 | ❌ 環境變數寫死在 Dockerfile | 不同環境需要不同設定 | ✅ 部署時透過 `-e` / ConfigMap 注入 |
| 5 | ❌ Build 後不推送 Registry 就部署 | 無法跨環境使用同一 Artifact | ✅ 推送 Registry 後再從 Registry 拉取 |

### 情境適用矩陣

| 情境 | Artifact 類型 | Registry 類型 | 強制等級 |
|------|-------------|-------------|---------|
| `greenfield` | Docker Image | Container Registry (GHCR/ECR/GCR) | 🔴 強制 |
| `brownfield` | Docker Image / JAR / WAR | Container Registry / Artifactory | 🔴 強制 |
| `migration` | Docker Image（新舊棧各一） | Container Registry | 🔴 強制 |
| `integration` | Docker Image | Container Registry | ⭐ 推薦 |
| `devops` | Docker Image / Helm Chart | Container Registry / Chart Museum | 🔴 強制 |
| `refactoring` | 同原有 Artifact 類型 | 同原有 Registry | ⭐ 推薦 |
| `performance` | Docker Image（含 Benchmark 工具） | Container Registry | ⭐ 推薦 |

---

## 🧪 Layer 2: Test Isolation（測試隔離模式）

> **⚠️ CRITICAL**: Integration Test 必須在**隔離環境**中執行，確保「每次測試的起點都是乾淨、可預測的狀態」。
> 本章節定義容器化測試隔離的標準模式，消除狀態殘留 (State Leak) 與間歇性失敗 (Flaky Tests)。
>
> - **適用範圍**: greenfield, brownfield, migration, integration, testing
> - **執行時機**: Layer 1 通過後，Layer 2 Integration Test 階段
> - **核心原則**: 每次測試起點都是乾淨環境 — 零狀態殘留

### 核心原則：為什麼需要測試隔離？

```
問題場景（無隔離）：
  Test A 寫入 user_id=1 → Test B 假設 DB 為空 → Test B 失敗（殘留資料干擾）
  → 間歇性失敗 → 開發者不信任 CI → 忽略紅燈 → 品質下降

正確做法（有隔離）：
  Test A: 啟動臨時 DB → 寫入 → 驗證 → 銷毀容器
  Test B: 啟動新臨時 DB → 起點保證為空 → 驗證 → 銷毀容器
  → 每次測試 100% 可重現 → 開發者信任 CI
```

### 三大隔離策略

| 策略 | 適用場景 | 隔離程度 | 速度 | 推薦度 |
|------|---------|---------|------|--------|
| **Testcontainers（推薦）** | 需要真實 DB/Redis/MQ 的 Integration Test | 🟢 完全隔離 | 中（首次啟動 5-15s） | ⭐⭐⭐ |
| **CI Services** | CI 平台原生支援的服務容器 | 🟡 Job 級隔離 | 快（平台管理） | ⭐⭐ |
| **In-Memory DB** | 簡單 SQL 測試（無需特定 DB 功能） | 🟢 完全隔離 | 最快（毫秒） | ⭐（適用範圍小） |

### 策略 1：Testcontainers（推薦方案）

**原理**：測試框架自動啟動 Docker 容器，測試結束後自動銷毀。

```
生命週期：
  @BeforeAll / setUp()
    ↓
  啟動 Docker 容器（PostgreSQL/MySQL/Redis/Kafka...）
    ↓
  等待就緒（WaitStrategy — 確定性同步，非 sleep）
    ↓
  執行測試（使用臨時容器連線）
    ↓
  @AfterAll / tearDown()
    ↓
  自動銷毀容器 + 清理資源
```

**多語言支援**：

| 語言 | 套件 | 安裝指令 |
|------|------|---------|
| Java/Kotlin | `org.testcontainers:testcontainers` | `implementation 'org.testcontainers:testcontainers:1.20+'` |
| Node.js | `testcontainers` | `npm install -D testcontainers` |
| Python | `testcontainers` | `pip install testcontainers` |
| Go | `testcontainers-go` | `go get github.com/testcontainers/testcontainers-go` |
| .NET | `Testcontainers` | `dotnet add package Testcontainers` |

**Java/Spring Boot 範例**：

```java
@SpringBootTest
@Testcontainers
class UserRepositoryIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:18-alpine")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private UserRepository userRepository;

    @Test
    void shouldSaveAndFindUser() {
        // 每次測試都是乾淨 DB — 零狀態殘留
        User user = new User("test@example.com", "Test User");
        userRepository.save(user);

        Optional<User> found = userRepository.findByEmail("test@example.com");
        assertThat(found).isPresent();
        assertThat(found.get().getName()).isEqualTo("Test User");
    }
}
```

**Node.js 範例**：

```typescript
import { PostgreSqlContainer, StartedPostgreSqlContainer } from '@testcontainers/postgresql';
import { Pool } from 'pg';

describe('UserRepository Integration', () => {
  let container: StartedPostgreSqlContainer;
  let pool: Pool;

  beforeAll(async () => {
    // 啟動臨時 PostgreSQL 容器
    container = await new PostgreSqlContainer('postgres:18-alpine')
      .withDatabase('testdb')
      .start();

    pool = new Pool({ connectionString: container.getConnectionUri() });

    // 執行 Schema Migration
    await pool.query(`
      CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL
      )
    `);
  }, 30000); // 30s 超時（含 Docker 啟動時間）

  afterAll(async () => {
    await pool.end();
    await container.stop(); // 自動銷毀容器
  });

  test('should save and find user', async () => {
    // 每次測試都是乾淨 DB
    await pool.query("INSERT INTO users (email, name) VALUES ($1, $2)", ['test@example.com', 'Test User']);
    const result = await pool.query("SELECT * FROM users WHERE email = $1", ['test@example.com']);
    expect(result.rows[0].name).toBe('Test User');
  });
});
```

**Python 範例**：

```python
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="module")
def postgres_container():
    """啟動臨時 PostgreSQL 容器，測試完成後自動銷毀"""
    with PostgresContainer("postgres:18-alpine") as postgres:
        yield postgres

@pytest.fixture
def db_connection(postgres_container):
    """每次測試取得乾淨連線"""
    import psycopg2
    conn = psycopg2.connect(postgres_container.get_connection_url())
    conn.autocommit = True
    yield conn
    conn.close()

def test_save_and_find_user(db_connection):
    cursor = db_connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL, email TEXT, name TEXT)")
    cursor.execute("INSERT INTO users (email, name) VALUES (%s, %s)", ("test@example.com", "Test User"))
    cursor.execute("SELECT name FROM users WHERE email = %s", ("test@example.com",))
    assert cursor.fetchone()[0] == "Test User"
```

### 策略 2：CI Services（平台原生服務容器）

**適用場景**：不需要程式碼控制容器生命週期，由 CI 平台管理。

> 詳見下方 [GitHub Actions 配置](#github-actions-testcontainers-整合) 和 [GitLab CI 配置](#gitlab-ci-testcontainers-整合)。

### 策略 3：In-Memory DB（輕量替代）

**適用場景**：僅需驗證 SQL 邏輯，不依賴特定 DB 功能（如 PostgreSQL 的 JSONB、MySQL 的全文索引）。

| 語言 | In-Memory 方案 | 限制 |
|------|---------------|------|
| Java | H2 Database | 不支援 PostgreSQL/MySQL 專屬語法 |
| Python | SQLite `:memory:` | 不支援 ALTER COLUMN 等 |
| Node.js | better-sqlite3 | 僅 SQLite 語法 |

**注意**：⚠️ In-Memory DB 僅適合簡單場景，**生產環境使用 PostgreSQL/MySQL 時，強烈建議用 Testcontainers 以保證行為一致**。

### 確定性同步（WaitUntil Pattern）

> **🔴 重要**：容器啟動後必須確認服務就緒，才能開始測試。**嚴禁使用 `sleep` 猜測等待時間**。

| 場景 | 正確做法 | 錯誤做法 |
|------|---------|---------|
| DB 容器就緒 | Testcontainers `WaitStrategy` / `wait-for-it.sh` / `dockerize` | ❌ `sleep 10` |
| Schema Migration | 驗證 migration exit code + schema_version 表 | ❌ 假設 migration 很快 |
| 服務就緒 | HTTP Health Check (`/health` 回傳 200) / K8s Readiness Probe | ❌ `sleep 5 && curl` |
| 部署穩定性 | Smoke Test + Canary 錯誤率門檻（已有 Layer 3） | ❌ 部署完直接宣告成功 |

**DB Migration 就緒確認（CI 階段必備）**：

> DB Schema Migration 是 Integration Test 和部署的前置條件。Migration 失敗必須**立即中止後續步驟**，絕不「先跳過」。

```bash
# CI Pipeline 中的 DB Migration 確定性同步模式
# Step 1: 等待 DB 容器就緒
dockerize -wait tcp://localhost:5432 -timeout 30s

# Step 2: 執行 Migration，嚴格檢查 exit code
npx prisma migrate deploy   # 或 flyway migrate / alembic upgrade head
MIGRATION_EXIT=$?
if [ $MIGRATION_EXIT -ne 0 ]; then
  echo "🔴 Migration 失敗 (exit code: $MIGRATION_EXIT)，立即中止！"
  exit 1
fi

# Step 3: 驗證 Schema 版本正確
EXPECTED_VERSION="20260323_add_user_table"
ACTUAL_VERSION=$(psql -t -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
if [ "$ACTUAL_VERSION" != "$EXPECTED_VERSION" ]; then
  echo "🔴 Schema 版本不符！預期: $EXPECTED_VERSION, 實際: $ACTUAL_VERSION"
  exit 1
fi

echo "✅ Migration 完成，Schema 版本驗證通過"
# Step 4: 才開始執行測試
npm test
```

**反模式**：
- ❌ Migration 失敗後繼續跑測試（測試結果無意義）
- ❌ 不驗證 Schema 版本（可能 Migration 靜默跳過）
- ❌ 在正式環境直接執行 `migrate deploy`（應先 Dry-Run）

**工具選型**：

| 工具 | 適用場景 | 優勢 | 安裝方式 |
|------|---------|------|---------|
| **Testcontainers WaitStrategy** | 程式碼內 Integration Test | 與測試框架深度整合，自動管理 | 隨 Testcontainers 套件 |
| **wait-for-it.sh** | CI Script / Docker Compose | 輕量、無依賴、Bash 原生 | `curl -o wait-for-it.sh` |
| **dockerize** | Docker Entrypoint / CI Script | 支援多協定（TCP/HTTP/Unix Socket） | `apt-get install dockerize` |
| **K8s Readiness Probe** | Kubernetes 部署 | 平台原生、自動重試、與負載均衡整合 | K8s YAML 配置 |

**wait-for-it.sh 用法**：
```bash
# 等待 PostgreSQL 就緒（最多 30 秒），就緒後才執行測試
./wait-for-it.sh localhost:5432 --timeout=30 --strict -- npm test
```

**dockerize 用法**：
```bash
# 等待多個服務就緒後才啟動應用（支援 TCP + HTTP 混合等待）
dockerize \
  -wait tcp://postgres:5432 \
  -wait tcp://redis:6379 \
  -wait http://api-gateway:8080/health \
  -timeout 60s \
  -- npm start
```

**Testcontainers 內建 WaitStrategy（推薦）**：
```java
// Java: 等待 PostgreSQL 接受連線後才回傳容器實例
new PostgreSQLContainer<>("postgres:18-alpine")
    .waitingFor(Wait.forListeningPort())           // 等待 Port 就緒
    .waitingFor(Wait.forLogMessage(".*ready.*", 1)) // 等待日誌訊息
    .withStartupTimeout(Duration.ofSeconds(30));    // 30 秒硬超時
```

**Kubernetes Readiness Probe + Init Container**：
```yaml
# K8s Deployment — 確保 Pod 就緒後才接收流量
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      # Init Container: 等待 DB 就緒後才啟動主容器
      initContainers:
        - name: wait-for-db
          image: busybox:1.36
          command: ['sh', '-c', 'until nc -z postgres-svc 5432; do sleep 1; done']

      containers:
        - name: api-server
          # Readiness Probe: 確認應用程式已就緒才加入負載均衡
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          # Liveness Probe: 持續監控應用程式健康
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
```

### 反模式清單（Anti-Patterns）

| # | 反模式 | 問題 | 正確替代 |
|---|--------|------|---------|
| 1 | ❌ 共用開發資料庫跑 Integration Test | 測試間資料污染、平行測試互相干擾 | ✅ Testcontainers 臨時 DB |
| 2 | ❌ 依賴測試執行順序 | 隱性耦合，單獨跑某測試會失敗 | ✅ 每個測試自行準備資料 |
| 3 | ❌ 手動清理測試資料 (`DELETE FROM ...`) | 容易遺漏、Transaction rollback 不可靠 | ✅ 容器銷毀 = 徹底清理 |
| 4 | ❌ `sleep N` 等待服務就緒 | 時間猜測不可靠，太短失敗太長浪費 | ✅ WaitStrategy / Health Check |
| 5 | ❌ 測試中寫死連線字串 | 環境不可攜、Port 衝突 | ✅ 動態取得容器連線資訊 |

### CI Runner 環境需求

| CI 平台 | 需求 | 配置方式 |
|---------|------|---------|
| **GitHub Actions** | Docker 已預裝（ubuntu-latest） | 直接使用，無需額外配置 |
| **GitLab CI** | Docker-in-Docker 或 Docker Socket | `services: [docker:dind]` 或 `volumes: [/var/run/docker.sock]` |
| **Jenkins** | Docker 安裝在 Agent 上 | `docker` pipeline step 或 Docker Plugin |
| **Azure DevOps** | 使用 ubuntu-latest Agent | 預裝 Docker，直接使用 |

### 情境適用矩陣

| 情境 | Testcontainers | CI Services | In-Memory |
|------|:-:|:-:|:-:|
| `greenfield` | ⭐ 推薦 | ✅ 可用 | ⚠️ 簡單場景 |
| `brownfield` | ⭐ 推薦 | ✅ 可用 | ❌ 通常需要特定 DB |
| `migration` | 🔴 強制 | ⚠️ 不足（需雙 DB） | ❌ |
| `integration` | ⭐ 推薦 | ✅ 可用 | ❌ |
| `testing` | ⭐ 推薦 | ✅ 可用 | ⚠️ 簡單場景 |
| `refactoring` | ✅ 可用 | ✅ 可用 | ⚠️ |
| 其他情境 | ⚠️ 視需求 | ⚠️ 視需求 | ⚠️ |

---

## 🔄 Migration Pipeline（Canary + Rollback）

> **⚠️ 最高風險情境**: Migration 情境涉及技術棧全面替換，需要專屬的 Layer 2 + Layer 3 Pipeline。
> 此 Pipeline 在 Layer 0 + Layer 1 之上，新增 Dual-Build、Contract Test、Canary Deploy、Rollback Gate。

### Migration Pipeline 架構

| 階段 | 內容 | 阻塞等級 |
|------|------|---------|
| **Layer 2.1 Dual-Build** | 舊棧 + 新棧同時建置測試 | 🔴 任一失敗阻塞 |
| **Layer 2.2 Contract Test** | API 相容性驗證（Pact/Schema） | 🔴 不相容阻塞 |
| **Layer 2.3 Performance Compare** | 新舊系統效能比對 | ⚠️ 警告 |
| **Layer 3.1 DB Dry-Run** | DB Migration 乾跑 + Rollback 驗證 | 🔴 失敗阻塞 |
| **Layer 3.2 Canary Deploy** | 5% → 25% → 50% → 100% 漸進部署 | 🔴 錯誤率 > 1% 自動回滾 |
| **Layer 3.3 Smoke + E2E** | 端對端驗證 + 雙寫一致性 | 🔴 失敗回滾 |

### 完整配置範本

📖 **詳細指南**: [Migration_Pipeline_Template.md](./Migration_Pipeline_Template.md)
📄 **GitHub Actions**: [github-actions/migration-pipeline.yml](./github-actions/migration-pipeline.yml)
📄 **GitLab CI**: [gitlab-ci/migration-pipeline-template.yml](./gitlab-ci/migration-pipeline-template.yml)

---

## 🛡️ Security Integration（增強安全掃描）

> **P1 安全整合**: 在 Layer 0 基礎安全之上，依情境風險等級添加 SAST / Container Scan / DAST 增強掃描。
> 將安全從獨立的 `security` 情境，擴展為貫穿所有情境的防護網。

### 四級安全模型

| 安全等級 | 包含內容 | 適用情境 |
|---------|---------|---------|
| **Basic** | Layer 0 (Secret + SCA + License) | documentation |
| **Standard** | Basic + SAST | greenfield, brownfield, refactoring, testing |
| **Advanced** | Standard + Container Scan | migration, integration, performance, devops |
| **Enhanced** | Advanced + DAST + Compliance Gate | security |

### 增強掃描工具

| 掃描類型 | 推薦工具 | 阻塞策略 | 超時 |
|---------|---------|---------|------|
| **SAST** | Semgrep / CodeQL | 🔴 Critical/High 阻塞 | 10 分鐘 |
| **Container Scan** | Trivy / Grype | 🔴 Critical/High 阻塞 | 10 分鐘 |
| **DAST** | OWASP ZAP | ⚠️ High 阻塞（誤報率考量） | 30 分鐘 |

### 執行時機

```
PR 階段: L0 → L1 → SAST + Container Scan（平行）→ L2/L3
Staging: Deploy → DAST Baseline（Enhanced 等級）
Nightly: DAST Full Scan + Container 全映像掃描
```

### 完整配置範本

📖 **詳細指南**: [Security_Scan_Integration_Template.md](./Security_Scan_Integration_Template.md)
📄 **GitHub Actions**: [github-actions/security-scan-enhanced.yml](./github-actions/security-scan-enhanced.yml)
📄 **GitLab CI**: [gitlab-ci/security-scan-enhanced-template.yml](./gitlab-ci/security-scan-enhanced-template.yml)

---

## ⚡ Performance Benchmark Gate（效能基準關卡）

> **🔴 P2 效能關卡** — 防止效能退化進入主分支

### 雙層效能測試模型

| 層級 | 觸發時機 | 耗時 | 阻塞策略 |
|------|---------|------|---------|
| **Micro-Benchmark** | 每次 PR | < 2 分鐘 | 🔴 退化 > 10% 阻塞 |
| **Full Load Test** | Nightly 排程 | 30-60 分鐘 | ⚠️ 僅警告 |

### 情境適用性

| 情境 | Micro-Benchmark | Full Load Test |
|------|:---:|:---:|
| `performance` | 🔴 強制 | 🔴 強制 (Nightly) |
| `greenfield` | ⚠️ 選配 | ❌ |
| `brownfield` | ⚠️ 選配 | ❌ |
| `refactoring` | ⚠️ 選配 | ❌ |
| `migration` | ⚠️ 選配 | ⚠️ 新舊棧比對 |
| 其他情境 | ❌ | ❌ |

### SLA Gate 閾值（預設）

| 指標 | PR 閾值 | Nightly 閾值 |
|------|---------|-------------|
| P50 延遲 | 退化 ≤ 10% | ≤ 200ms |
| P95 延遲 | 退化 ≤ 15% | ≤ 500ms |
| 錯誤率 | ≤ 0.1% | ≤ 0.5% |

### 完整配置範本

📖 **詳細指南**: [Performance_Benchmark_Gate_Template.md](./Performance_Benchmark_Gate_Template.md)
📄 **GitHub Actions**: [github-actions/perf-benchmark.yml](./github-actions/perf-benchmark.yml)
📄 **GitLab CI**: [gitlab-ci/perf-benchmark-template.yml](./gitlab-ci/perf-benchmark-template.yml)

---

## 📝 Documentation Pipeline（文檔 Pipeline）

> **📝 P2 文檔品質自動化** — Doc Lint + Link Check + Build + Deploy

### Pipeline 流程

| 階段 | 觸發時機 | 耗時 | 阻塞策略 |
|------|---------|------|---------|
| **Doc Lint** | 每次 PR（.md 變更） | < 1 分鐘 | 🔴 格式錯誤阻塞 |
| **Link Check (內部)** | 每次 PR | < 2 分鐘 | 🔴 斷裂連結阻塞 |
| **Link Check (外部)** | Nightly | < 30 分鐘 | ⚠️ 僅警告 |
| **Doc Build + Deploy** | Main 合併後 | < 10 分鐘 | 🔴 失敗通知 |

### 情境適用性

| 情境 | Doc Lint + Link Check | Build + Deploy |
|------|:---:|:---:|
| `documentation` | 🔴 強制 | 🔴 強制 |
| `greenfield` / `brownfield` | ⚠️ 選配 | ❌ |
| `migration` / `integration` | ⚠️ 選配 | ❌ |
| 其他情境 | ❌ | ❌ |

### 完整配置範本

📖 **詳細指南**: [Documentation_Pipeline_Template.md](./Documentation_Pipeline_Template.md)
📄 **GitHub Actions**: [github-actions/docs-pipeline.yml](./github-actions/docs-pipeline.yml)
📄 **GitLab CI**: [gitlab-ci/docs-pipeline-template.yml](./gitlab-ci/docs-pipeline-template.yml)

---

## 🔔 Event-Driven Agent Notification（事件驅動 Agent 通知）

> **🔔 P3 事件驅動 Agent 協作** — PR 事件 → Agent 並行執行 → 結果匯聚 → 統一通知

### 事件驅動模型

| 事件 | 觸發條件 | Agent 觸發鏈 | 通知渠道 |
|------|---------|-------------|---------|
| **pr_opened** | PR 建立/更新 | code-analyzer + security-engineer + qa-automation | PR Comment, Slack |
| **pr_approved** | PR 通過審查 | devops-engineer (deploy-staging) + qa-tester (smoke-test) | PM/PO 驗收通知 |
| **release_tagged** | 版本標記 | devops-engineer (canary) + performance + security (DAST) | 全員通知 |
| **pipeline_failed** | Pipeline 失敗 | — | Slack 即時警報 |

### Agent 通知適用矩陣

| 情境 | PR 事件通知 | 部署通知 | 情境專屬觸發 |
|------|:---:|:---:|:---:|
| `greenfield` | 🔴 強制 | 🔴 強制 | ❌ |
| `brownfield` | 🔴 強制 | 🔴 強制 | ❌ |
| `refactoring` | 🔴 強制 | ⚠️ 選配 | ✅ mutation-test |
| `migration` | 🔴 強制 | 🔴 強制 | ✅ canary + rollback |
| `integration` | 🔴 強制 | 🔴 強制 | ✅ contract-test |
| `performance` | 🔴 強制 | ⚠️ 選配 | ✅ benchmark |
| `devops` | 🔴 強制 | 🔴 強制 | ✅ IaC validate |
| `testing` | 🔴 強制 | ⚠️ 選配 | ❌ |
| `security` | 🔴 強制 | 🔴 強制 | ✅ enhanced-SAST |
| `documentation` | ⚠️ 選配 | ⚠️ 選配 | ❌ |

### 避坑指南

| 風險 | 緩解策略 |
|------|---------|
| Pipeline 死結 | 超時熔斷（10 分鐘）、分級阻塞、hotfix 旁路 |
| 通知風暴 | 聚合窗口（5 分鐘）、分級路由、靜默時段 |
| Agent 回饋延遲 | 增量通知、進度更新（60s）、ETA 預估 |

📖 **詳細指南**: [Event_Driven_Agent_Notification_Template.md](./Event_Driven_Agent_Notification_Template.md)
📄 **GitHub Actions**: [github-actions/agent-notification.yml](./github-actions/agent-notification.yml)
📄 **GitLab CI**: [gitlab-ci/agent-notification-template.yml](./gitlab-ci/agent-notification-template.yml)

---

## CI/CD Pipeline 概覽

### Pipeline 階段定義

**標準 CI/CD Pipeline 包含以下階段**:

```mermaid
graph LR
    A[Code Push] --> B[Build]
    B --> C[Test]
    C --> D[Security Scan]
    D --> E[Quality Gate]
    E --> F[Deploy to Dev]
    F --> G[Integration Test]
    G --> H{Manual Approval?}
    H -->|Yes| I[Deploy to Staging]
    H -->|No| I
    I --> J[E2E Test]
    J --> K{Manual Approval?}
    K -->|Yes| L[Deploy to Production]
    K -->|No| M[Skip]
    L --> N[Smoke Test]
    N --> O[Monitoring]

    style B fill:#87CEEB
    style C fill:#87CEEB
    style D fill:#FFD700
    style E fill:#FFD700
    style F fill:#90EE90
    style I fill:#90EE90
    style L fill:#FF6B6B
    style O fill:#D3D3D3
```

**各階段說明**:

| 階段 | 目的 | 執行時間 | 失敗處理 |
|------|------|---------|---------|
| **Build** | 編譯程式碼、安裝依賴、打包 | 2-5 分鐘 | 立即停止 Pipeline |
| **Test** | 單元測試、整合測試 | 5-10 分鐘 | 立即停止 Pipeline |
| **Security Scan** | 安全漏洞掃描、依賴檢查 | 2-3 分鐘 | 警告或停止（依嚴重度） |
| **Quality Gate** | 程式碼品質檢查（SonarQube） | 1-2 分鐘 | 警告或停止（依設定） |
| **Deploy to Dev** | 部署至開發環境 | 2-5 分鐘 | 回滾至前一版本 |
| **Integration Test** | 開發環境整合測試 | 3-5 分鐘 | 標記失敗，通知團隊 |
| **Deploy to Staging** | 部署至測試環境 | 3-5 分鐘 | 回滾至前一版本 |
| **E2E Test** | 端對端測試 | 10-15 分鐘 | 標記失敗，通知團隊 |
| **Deploy to Production** | 部署至正式環境 | 5-10 分鐘 | 立即回滾 |
| **Smoke Test** | 正式環境冒煙測試 | 2-3 分鐘 | 立即回滾 |
| **Monitoring** | 持續監控關鍵指標 | 持續 | 觸發告警 |

---

## GitHub Actions 配置

### 完整配置範例

**檔案位置**: `.github/workflows/ci-cd.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches:
      - main
      - develop
      - 'release/**'
  pull_request:
    branches:
      - main
      - develop
  workflow_dispatch:  # 允許手動觸發

env:
  NODE_VERSION: '18.x'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ==================== Build Stage ====================
  build:
    name: Build and Compile
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 完整歷史記錄（用於版本標記）

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install Dependencies
        run: npm ci

      - name: Build Application
        run: npm run build

      - name: Generate Version
        id: version
        run: |
          echo "version=$(date +'%Y%m%d')-$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT

      - name: Upload Build Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ steps.version.outputs.version }}
          path: dist/
          retention-days: 7

  # ==================== Test Stage ====================
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    needs: build

    strategy:
      matrix:
        test-type: [unit, integration]

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install Dependencies
        run: npm ci

      - name: Run ${{ matrix.test-type }} Tests
        run: npm run test:${{ matrix.test-type }}

      - name: Generate Coverage Report
        if: matrix.test-type == 'unit'
        run: npm run test:coverage

      - name: Upload Coverage to Codecov
        if: matrix.test-type == 'unit'
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage/lcov.info
          fail_ci_if_error: true

      - name: Check Coverage Threshold
        if: matrix.test-type == 'unit'
        run: |
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "❌ Coverage $COVERAGE% is below threshold 80%"
            exit 1
          fi
          echo "✅ Coverage $COVERAGE% meets threshold"

  # ==================== Security Scan Stage ====================
  security:
    name: Security Scanning
    runs-on: ubuntu-latest
    needs: build

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run Dependency Security Scan (Snyk)
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

      - name: Run SAST (Static Application Security Testing)
        uses: github/codeql-action/init@v3
        with:
          languages: javascript

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3

      - name: Run Secret Scanning
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD

  # ==================== Code Quality Stage ====================
  quality:
    name: Code Quality Check
    runs-on: ubuntu-latest
    needs: build

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # SonarQube 需要完整歷史

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install Dependencies
        run: npm ci

      - name: Run Linter
        run: npm run lint

      - name: Run SonarQube Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  # ==================== Build Docker Image ====================
  docker:
    name: Build and Push Docker Image
    runs-on: ubuntu-latest
    needs: [test, security, quality]
    if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop')

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and Push Docker Image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache
          cache-to: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache,mode=max

  # ==================== Deploy to Development ====================
  deploy-dev:
    name: Deploy to Development
    runs-on: ubuntu-latest
    needs: docker
    if: github.ref == 'refs/heads/develop'
    environment:
      name: development
      url: https://dev.example.com

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Deploy to Kubernetes (Dev)
        uses: azure/k8s-deploy@v4
        with:
          manifests: |
            k8s/deployment.yaml
            k8s/service.yaml
          images: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:develop
          namespace: development

      - name: Run Integration Tests
        run: |
          npm run test:integration:dev
        env:
          API_BASE_URL: https://api.dev.example.com

  # ==================== Deploy to Staging ====================
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: docker
    if: github.ref == 'refs/heads/main'
    environment:
      name: staging
      url: https://staging.example.com

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Deploy to Kubernetes (Staging)
        uses: azure/k8s-deploy@v4
        with:
          manifests: |
            k8s/deployment.yaml
            k8s/service.yaml
          images: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main
          namespace: staging

      - name: Run E2E Tests
        run: |
          npm run test:e2e:staging
        env:
          API_BASE_URL: https://api.staging.example.com

      - name: Performance Test
        run: |
          npm run test:performance:staging

  # ==================== Deploy to Production ====================
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://example.com

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Deploy to Kubernetes (Production) - Blue/Green
        uses: azure/k8s-deploy@v4
        with:
          manifests: |
            k8s/deployment.yaml
            k8s/service.yaml
          images: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          namespace: production
          strategy: blue-green

      - name: Run Smoke Tests
        run: |
          npm run test:smoke:production
        env:
          API_BASE_URL: https://api.example.com

      - name: Validate Deployment
        run: |
          # 檢查健康檢查端點
          RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health)
          if [ $RESPONSE -ne 200 ]; then
            echo "❌ Health check failed: $RESPONSE"
            exit 1
          fi
          echo "✅ Health check passed"

      - name: Notify Deployment Success
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: '🚀 Production deployment successful!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        if: success()

      - name: Rollback on Failure
        if: failure()
        run: |
          kubectl rollout undo deployment/app -n production
          echo "❌ Deployment failed. Rolled back to previous version."

  # ==================== Notification ====================
  notify:
    name: Send Notifications
    runs-on: ubuntu-latest
    needs: [deploy-production]
    if: always()

    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          fields: repo,message,commit,author,action,eventName,ref,workflow
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}

      - name: Create GitHub Release (on main)
        if: github.ref == 'refs/heads/main' && success()
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: v${{ needs.build.outputs.version }}
          release_name: Release v${{ needs.build.outputs.version }}
          draft: false
          prerelease: false
```

### GitHub Actions 最佳實踐

| 最佳實踐 | 說明 | 範例 |
|---------|------|------|
| **使用 Matrix Strategy** | 並行執行多個測試 | `strategy.matrix.test-type: [unit, integration]` |
| **快取依賴** | 加速 Pipeline 執行 | `cache: 'npm'` |
| **Artifact 管理** | 儲存建置產物 | `actions/upload-artifact@v4` |
| **環境隔離** | 使用 Environment 管理部署 | `environment: production` |
| **Manual Approval** | 正式環境需人工批准 | `environment` + Branch Protection |
| **Secrets 管理** | 敏感資料使用 Secrets | `${{ secrets.CODECOV_TOKEN }}` |

### GitHub Actions Immutable Artifact 整合

**Build Once, Push to Registry, Deploy from Registry**：

```yaml
  # ==================== Build & Push Immutable Artifact ====================
  build-artifact:
    name: Build Immutable Artifact
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4

      - name: Generate Image Metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha,prefix=,format=short
            type=semver,pattern=v{{version}},enable=${{ startsWith(github.ref, 'refs/tags/v') }}
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}

      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build & Push (Build Once)
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Record Artifact SHA256
        run: echo "ARTIFACT_DIGEST=${{ steps.build.outputs.digest }}" >> $GITHUB_STEP_SUMMARY

  # ==================== Deploy to Staging (Deploy Many — 同一 Artifact) ====================
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [build-artifact, integration-test]  # 測試通過後才部署
    environment: staging
    steps:
      - name: Deploy Same Artifact to Staging
        run: |
          # 從 Registry 拉取同一 Image（非重新 Build）
          kubectl set image deployment/myapi \
            myapi=ghcr.io/${{ github.repository }}@${{ needs.build-artifact.outputs.image-digest }}

      - name: Verify Artifact Integrity
        run: |
          DEPLOYED_DIGEST=$(kubectl get pod -l app=myapi -o jsonpath='{.items[0].status.containerStatuses[0].imageID}' | cut -d@ -f2)
          EXPECTED_DIGEST="${{ needs.build-artifact.outputs.image-digest }}"
          if [ "$DEPLOYED_DIGEST" != "$EXPECTED_DIGEST" ]; then
            echo "🔴 Artifact 完整性校驗失敗！"
            exit 1
          fi
          echo "✅ Staging 部署的 Artifact 與 CI Build 完全一致"
```

### GitHub Actions Testcontainers 整合

**方案 A：使用 Testcontainers（推薦 — 程式碼控制容器生命週期）**

```yaml
  # ==================== Integration Test with Testcontainers ====================
  integration-test:
    name: Integration Test (Testcontainers)
    runs-on: ubuntu-latest  # ubuntu-latest 已預裝 Docker
    needs: [build]

    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 21  # Java 範例，其他語言替換對應 setup action
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'

      - name: Run Integration Tests with Testcontainers
        run: ./gradlew integrationTest  # Testcontainers 會自動啟動/銷毀 Docker 容器
        env:
          TESTCONTAINERS_RYUK_DISABLED: false  # 啟用資源清理守護容器

      - name: Upload Test Results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: integration-test-results
          path: build/reports/tests/integrationTest/
```

**方案 B：使用 CI Services（平台管理容器生命週期）**

```yaml
  # ==================== Integration Test with CI Services ====================
  integration-test-services:
    name: Integration Test (CI Services)
    runs-on: ubuntu-latest
    needs: [build]

    services:
      postgres:
        image: postgres:18-alpine
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd="pg_isready -U test"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd="redis-cli ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5

    steps:
      - uses: actions/checkout@v4

      - name: Wait for Services  # 確定性同步 — 非 sleep
        run: |
          until pg_isready -h localhost -p 5432 -U test; do sleep 1; done
          echo "PostgreSQL is ready"

      - name: Run Integration Tests
        run: npm test -- --testPathPattern=integration
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
```

---

## GitLab CI 配置

### 完整配置範例

**檔案位置**: `.gitlab-ci.yml`

```yaml
# GitLab CI/CD Pipeline Configuration

variables:
  NODE_VERSION: "18"
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"
  REGISTRY: registry.gitlab.com
  IMAGE_NAME: $CI_REGISTRY_IMAGE

stages:
  - build
  - test
  - security
  - quality
  - package
  - deploy-dev
  - deploy-staging
  - deploy-production

# ==================== Build Stage ====================
build:
  stage: build
  image: node:${NODE_VERSION}
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/
      - .npm/
  script:
    - npm ci --cache .npm --prefer-offline
    - npm run build
  artifacts:
    paths:
      - dist/
    expire_in: 1 week
  only:
    - main
    - develop
    - merge_requests

# ==================== Unit Test ====================
test:unit:
  stage: test
  image: node:${NODE_VERSION}
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/
    policy: pull
  script:
    - npm run test:unit
    - npm run test:coverage
  coverage: '/Lines\s*:\s*(\d+\.\d+)%/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
      junit: junit.xml
  only:
    - main
    - develop
    - merge_requests

# ==================== Integration Test ====================
test:integration:
  stage: test
  image: node:${NODE_VERSION}
  services:
    - postgres:14
    - redis:7
  variables:
    POSTGRES_DB: test_db
    POSTGRES_USER: test_user
    POSTGRES_PASSWORD: test_password
    DATABASE_URL: "postgresql://test_user:test_password@postgres:5432/test_db"
    REDIS_URL: "redis://redis:6379"
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/
    policy: pull
  script:
    - npm run test:integration
  only:
    - main
    - develop
    - merge_requests

# ==================== Security Scan ====================
security:dependencies:
  stage: security
  image: node:${NODE_VERSION}
  script:
    - npm audit --audit-level=moderate
  allow_failure: true
  only:
    - main
    - develop
    - merge_requests

security:sast:
  stage: security
  variables:
    SAST_EXCLUDED_PATHS: "spec, test, tests, tmp, node_modules"
  script:
    - echo "Running SAST..."
  artifacts:
    reports:
      sast: gl-sast-report.json
  only:
    - main
    - develop
    - merge_requests

# ==================== Code Quality ====================
code_quality:
  stage: quality
  image: sonarsource/sonar-scanner-cli:latest
  variables:
    SONAR_USER_HOME: "${CI_PROJECT_DIR}/.sonar"
    GIT_DEPTH: "0"
  cache:
    key: "${CI_JOB_NAME}"
    paths:
      - .sonar/cache
  script:
    - sonar-scanner
  allow_failure: true
  only:
    - main
    - develop
    - merge_requests

lint:
  stage: quality
  image: node:${NODE_VERSION}
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/
    policy: pull
  script:
    - npm run lint
  only:
    - main
    - develop
    - merge_requests

# ==================== Build Docker Image ====================
docker:build:
  stage: package
  image: docker:24
  services:
    - docker:24-dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -t $IMAGE_NAME:$CI_COMMIT_SHORT_SHA .
    - docker tag $IMAGE_NAME:$CI_COMMIT_SHORT_SHA $IMAGE_NAME:$CI_COMMIT_REF_SLUG
    - docker push $IMAGE_NAME:$CI_COMMIT_SHORT_SHA
    - docker push $IMAGE_NAME:$CI_COMMIT_REF_SLUG
    - |
      if [ "$CI_COMMIT_BRANCH" == "main" ]; then
        docker tag $IMAGE_NAME:$CI_COMMIT_SHORT_SHA $IMAGE_NAME:latest
        docker push $IMAGE_NAME:latest
      fi
  only:
    - main
    - develop

# ==================== Deploy to Development ====================
deploy:dev:
  stage: deploy-dev
  image: alpine/kubectl:latest
  environment:
    name: development
    url: https://dev.example.com
    on_stop: stop:dev
  script:
    - kubectl config use-context development
    - kubectl set image deployment/app app=$IMAGE_NAME:$CI_COMMIT_SHORT_SHA -n development
    - kubectl rollout status deployment/app -n development
  only:
    - develop

stop:dev:
  stage: deploy-dev
  image: alpine/kubectl:latest
  environment:
    name: development
    action: stop
  script:
    - kubectl delete deployment app -n development
  when: manual
  only:
    - develop

# ==================== Deploy to Staging ====================
deploy:staging:
  stage: deploy-staging
  image: alpine/kubectl:latest
  environment:
    name: staging
    url: https://staging.example.com
  script:
    - kubectl config use-context staging
    - kubectl set image deployment/app app=$IMAGE_NAME:$CI_COMMIT_SHORT_SHA -n staging
    - kubectl rollout status deployment/app -n staging
  only:
    - main

test:e2e:staging:
  stage: deploy-staging
  image: mcr.microsoft.com/playwright:latest
  needs: ["deploy:staging"]
  script:
    - npm run test:e2e:staging
  artifacts:
    when: always
    paths:
      - playwright-report/
    expire_in: 30 days
  only:
    - main

# ==================== Deploy to Production ====================
deploy:production:
  stage: deploy-production
  image: alpine/kubectl:latest
  environment:
    name: production
    url: https://example.com
  script:
    - kubectl config use-context production
    - kubectl set image deployment/app app=$IMAGE_NAME:latest -n production
    - kubectl rollout status deployment/app -n production
    - |
      # Smoke Test
      RESPONSE=$(wget --spider -S "https://api.example.com/health" 2>&1 | grep "HTTP/" | awk '{print $2}')
      if [ "$RESPONSE" != "200" ]; then
        echo "❌ Health check failed"
        kubectl rollout undo deployment/app -n production
        exit 1
      fi
      echo "✅ Deployment successful"
  when: manual
  only:
    - main
```

### GitLab CI 特色功能

| 功能 | 說明 | 優勢 |
|------|------|------|
| **內建 Container Registry** | 不需額外設定 Docker Registry | 簡化配置 |
| **環境管理** | 內建環境追蹤與部署歷史 | 視覺化部署狀態 |
| **Auto DevOps** | 自動產生 Pipeline | 快速啟動 |
| **Services** | 測試時啟動依賴服務（DB, Redis） | 整合測試更容易 |

### GitLab CI Immutable Artifact 整合

**Build Once, Push to GitLab Container Registry, Deploy from Registry**：

```yaml
# .gitlab-ci.yml — Immutable Artifact Pattern

variables:
  IMAGE_TAG: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA-$CI_PIPELINE_ID

# ==================== Build & Push (Build Once) ====================
build-artifact:
  stage: build
  image: docker:24
  services:
    - docker:dind
  variables:
    DOCKER_TLS_CERTDIR: ""
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $IMAGE_TAG .
    # 記錄 Artifact SHA256
    - docker inspect --format='{{.Id}}' $IMAGE_TAG > artifact-digest.txt
    - docker push $IMAGE_TAG
    # Release Tag（僅在 tag 事件）
    - |
      if [ -n "$CI_COMMIT_TAG" ]; then
        docker tag $IMAGE_TAG $CI_REGISTRY_IMAGE:$CI_COMMIT_TAG
        docker tag $IMAGE_TAG $CI_REGISTRY_IMAGE:latest
        docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_TAG
        docker push $CI_REGISTRY_IMAGE:latest
      fi
  artifacts:
    paths:
      - artifact-digest.txt
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_TAG

# ==================== Deploy to Staging (Deploy Many — 同一 Artifact) ====================
deploy-staging:
  stage: deploy
  image: bitnami/kubectl:latest
  needs: [build-artifact, integration-test]
  environment:
    name: staging
    url: https://staging.example.com
  script:
    # 從 Registry 拉取同一 Image（非重新 Build）
    - kubectl set image deployment/myapi myapi=$IMAGE_TAG
    - kubectl rollout status deployment/myapi --timeout=120s
    # 完整性校驗
    - |
      DEPLOYED_IMAGE=$(kubectl get pod -l app=myapi -o jsonpath='{.items[0].spec.containers[0].image}')
      if [ "$DEPLOYED_IMAGE" != "$IMAGE_TAG" ]; then
        echo "🔴 部署的 Image 與 Build 產出不一致！"
        exit 1
      fi
      echo "✅ Staging 部署完整性校驗通過"
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      when: manual
```

### GitLab CI Testcontainers 整合

**方案 A：使用 Testcontainers（推薦 — 需要 Docker-in-Docker）**

```yaml
# .gitlab-ci.yml — Integration Test with Testcontainers
integration-test-testcontainers:
  stage: test
  image: gradle:8-jdk21  # 或 node:20, python:3.12 等
  services:
    - docker:dind  # Docker-in-Docker，讓 Testcontainers 可以啟動容器
  variables:
    DOCKER_HOST: tcp://docker:2375
    DOCKER_TLS_CERTDIR: ""
    TESTCONTAINERS_HOST_OVERRIDE: docker  # 告訴 Testcontainers Docker 在哪
  script:
    - ./gradlew integrationTest  # Testcontainers 自動管理容器生命週期
  artifacts:
    when: always
    reports:
      junit: build/test-results/integrationTest/*.xml
    paths:
      - build/reports/tests/integrationTest/
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

**方案 B：使用 GitLab Services（平台管理容器）**

```yaml
# .gitlab-ci.yml — Integration Test with GitLab Services
integration-test-services:
  stage: test
  image: node:20-alpine
  services:
    - name: postgres:18-alpine
      alias: postgres
      variables:
        POSTGRES_DB: testdb
        POSTGRES_USER: test
        POSTGRES_PASSWORD: test
    - name: redis:7-alpine
      alias: redis
  variables:
    DATABASE_URL: postgresql://test:test@postgres:5432/testdb
    REDIS_URL: redis://redis:6379
  before_script:
    # 確定性同步 — 等待服務就緒
    - apt-get update && apt-get install -y postgresql-client
    - until pg_isready -h postgres -U test; do sleep 1; done
    - echo "PostgreSQL is ready"
  script:
    - npm ci
    - npm test -- --testPathPattern=integration
  artifacts:
    when: always
    reports:
      junit: test-results/*.xml
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

---

## Jenkins Pipeline 配置

### Jenkinsfile (Declarative Pipeline)

**檔案位置**: `Jenkinsfile`

```groovy
pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
        timeout(time: 1, unit: 'HOURS')
    }

    environment {
        NODE_VERSION = '18'
        DOCKER_REGISTRY = 'registry.example.com'
        IMAGE_NAME = 'myapp'
        SLACK_CHANNEL = '#deployments'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT_SHORT = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                    env.VERSION = "${env.BUILD_NUMBER}-${env.GIT_COMMIT_SHORT}"
                }
            }
        }

        stage('Build') {
            agent {
                docker {
                    image "node:${NODE_VERSION}"
                    args '-v $HOME/.npm:/.npm'
                }
            }
            steps {
                sh 'npm ci'
                sh 'npm run build'
                stash includes: 'dist/**', name: 'build-artifacts'
            }
        }

        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    agent {
                        docker {
                            image "node:${NODE_VERSION}"
                        }
                    }
                    steps {
                        sh 'npm ci'
                        sh 'npm run test:unit'
                        sh 'npm run test:coverage'
                    }
                    post {
                        always {
                            junit 'junit.xml'
                            publishHTML([
                                reportDir: 'coverage',
                                reportFiles: 'index.html',
                                reportName: 'Coverage Report'
                            ])
                        }
                    }
                }

                stage('Integration Tests') {
                    agent {
                        docker {
                            image "node:${NODE_VERSION}"
                        }
                    }
                    steps {
                        sh 'npm ci'
                        sh 'npm run test:integration'
                    }
                }
            }
        }

        stage('Security Scan') {
            parallel {
                stage('Dependency Check') {
                    steps {
                        sh 'npm audit --audit-level=moderate'
                    }
                }

                stage('SAST') {
                    steps {
                        sh 'sonar-scanner'
                    }
                }
            }
        }

        stage('Build Docker Image') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                script {
                    docker.withRegistry("https://${DOCKER_REGISTRY}", 'docker-credentials') {
                        def app = docker.build("${IMAGE_NAME}:${VERSION}")
                        app.push()
                        if (env.BRANCH_NAME == 'main') {
                            app.push('latest')
                        }
                    }
                }
            }
        }

        stage('Deploy to Development') {
            when {
                branch 'develop'
            }
            steps {
                sh "kubectl set image deployment/app app=${DOCKER_REGISTRY}/${IMAGE_NAME}:${VERSION} -n development"
                sh "kubectl rollout status deployment/app -n development"
            }
        }

        stage('Deploy to Staging') {
            when {
                branch 'main'
            }
            steps {
                sh "kubectl set image deployment/app app=${DOCKER_REGISTRY}/${IMAGE_NAME}:${VERSION} -n staging"
                sh "kubectl rollout status deployment/app -n staging"
            }
        }

        stage('E2E Tests (Staging)') {
            when {
                branch 'main'
            }
            steps {
                sh 'npm run test:e2e:staging'
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                input message: 'Deploy to Production?', ok: 'Deploy'
                // ✅ 使用與 Staging 相同的 VERSION Tag（Immutable Artifact 原則）
                // ❌ 禁止使用 latest（反模式：無法追溯版本、無法回滾）
                sh "kubectl set image deployment/app app=${DOCKER_REGISTRY}/${IMAGE_NAME}:${VERSION} -n production"
                sh "kubectl rollout status deployment/app -n production"
            }
        }

        stage('Smoke Test') {
            when {
                branch 'main'
            }
            steps {
                script {
                    def response = sh(returnStdout: true, script: 'curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health')
                    if (response != '200') {
                        error("Health check failed: ${response}")
                    }
                }
            }
        }
    }

    post {
        success {
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'good',
                message: "✅ Pipeline Success: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
            )
        }
        failure {
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'danger',
                message: "❌ Pipeline Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
            )
        }
        always {
            cleanWs()
        }
    }
}
```

---

## Azure DevOps Pipeline 配置

### 完整配置範例

**檔案位置**: `azure-pipelines.yml`

```yaml
trigger:
  branches:
    include:
      - main
      - develop

pr:
  branches:
    include:
      - main
      - develop

variables:
  nodeVersion: '18.x'
  dockerRegistry: 'myregistry.azurecr.io'
  imageName: 'myapp'

stages:
  # ==================== Build Stage ====================
  - stage: Build
    displayName: 'Build Application'
    jobs:
      - job: BuildJob
        displayName: 'Build and Test'
        pool:
          vmImage: 'ubuntu-latest'
        steps:
          - task: NodeTool@0
            inputs:
              versionSpec: $(nodeVersion)
            displayName: 'Install Node.js'

          - script: |
              npm ci
              npm run build
            displayName: 'Install and Build'

          - task: PublishBuildArtifacts@1
            inputs:
              PathtoPublish: 'dist'
              ArtifactName: 'drop'
            displayName: 'Publish Artifacts'

  # ==================== Test Stage ====================
  - stage: Test
    displayName: 'Run Tests'
    dependsOn: Build
    jobs:
      - job: UnitTests
        displayName: 'Unit Tests'
        pool:
          vmImage: 'ubuntu-latest'
        steps:
          - task: NodeTool@0
            inputs:
              versionSpec: $(nodeVersion)

          - script: |
              npm ci
              npm run test:unit
              npm run test:coverage
            displayName: 'Run Unit Tests'

          - task: PublishTestResults@2
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: '**/junit.xml'

          - task: PublishCodeCoverageResults@1
            inputs:
              codeCoverageTool: 'Cobertura'
              summaryFileLocation: '$(System.DefaultWorkingDirectory)/coverage/cobertura-coverage.xml'

  # ==================== Deploy to Dev ====================
  - stage: DeployDev
    displayName: 'Deploy to Development'
    dependsOn: Test
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/develop'))
    jobs:
      - deployment: DeployDevJob
        displayName: 'Deploy to Dev'
        environment: 'development'
        pool:
          vmImage: 'ubuntu-latest'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: Kubernetes@1
                  inputs:
                    connectionType: 'Kubernetes Service Connection'
                    namespace: 'development'
                    command: 'apply'
                    useConfigurationFile: true
                    configurationType: 'inline'
                    inline: |
                      apiVersion: apps/v1
                      kind: Deployment
                      metadata:
                        name: myapp
                      spec:
                        replicas: 2
                        template:
                          spec:
                            containers:
                            - name: myapp
                              image: $(dockerRegistry)/$(imageName):$(Build.BuildId)

  # ==================== Deploy to Production ====================
  - stage: DeployProd
    displayName: 'Deploy to Production'
    dependsOn: DeployDev
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployProdJob
        displayName: 'Deploy to Production'
        environment: 'production'
        pool:
          vmImage: 'ubuntu-latest'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: Kubernetes@1
                  inputs:
                    connectionType: 'Kubernetes Service Connection'
                    namespace: 'production'
                    command: 'apply'
                    useConfigurationFile: true
                    configurationType: 'inline'
                    inline: |
                      apiVersion: apps/v1
                      kind: Deployment
                      metadata:
                        name: myapp
                      spec:
                        replicas: 3
                        template:
                          spec:
                            containers:
                            - name: myapp
                              # ✅ 使用 Build ID 標識（Immutable Artifact 原則）
                              # ❌ 禁止使用 latest（反模式：無法追溯版本、無法回滾）
                              image: $(dockerRegistry)/$(imageName):$(Build.BuildId)
```

---

## 通用最佳實踐

### 1. Pipeline 效能優化

| 優化策略 | 說明 | 預期改善 |
|---------|------|---------|
| **並行執行** | 使用 Matrix/Parallel 策略 | 減少 30-50% 執行時間 |
| **快取依賴** | 快取 node_modules, Docker layers | 減少 40-60% 安裝時間 |
| **增量建置** | 僅建置變更的部分 | 減少 50-70% 建置時間 |
| **Docker Layer 優化** | 善用 Docker Cache | 減少 60-80% 映像建置時間 |

### 2. 安全性最佳實踐

| 安全措施 | 實作方式 | 重要性 |
|---------|---------|--------|
| **Secrets 管理** | 使用 CI/CD 平台的 Secrets 功能 | 🔴 必須 |
| **依賴掃描** | Snyk, npm audit | 🔴 必須 |
| **SAST 掃描** | SonarQube, CodeQL | 🟡 建議 |
| **Container 掃描** | Trivy, Clair | 🟡 建議 |
| **Least Privilege** | 最小權限原則 | 🔴 必須 |

### 3. 測試覆蓋率要求

參考 [SOP.md Stage 8 - Testing Standards](../../../scenarios/greenfield/SOP.md):

- ✅ 單元測試覆蓋率 ≥ 80%
- ✅ 整合測試覆蓋率 ≥ 60%
- ✅ E2E 測試覆蓋率 ≥ 40%

### 4. 測試隔離最佳實踐

| 原則 | 說明 | 重要性 |
|------|------|--------|
| **環境隔離** | Integration Test 使用 Testcontainers 或 CI Services，禁止共用開發 DB | 🔴 必須 |
| **確定性同步** | 使用 WaitStrategy/Health Check 確認服務就緒，禁止 `sleep` 猜測 | 🔴 必須 |
| **資料獨立** | 每個測試自行準備資料，禁止依賴測試執行順序 | 🔴 必須 |
| **容器清理** | 測試完成後自動銷毀容器（Testcontainers Ryuk / CI 平台管理） | 🟡 建議 |
| **動態連線** | 從容器動態取得連線資訊，禁止寫死 IP/Port | 🟡 建議 |

> 📖 詳見 [Layer 2: Test Isolation（測試隔離模式）](#layer-2-test-isolation測試隔離模式) 完整指引。

### 5. 確定性同步最佳實踐（WaitUntil Pattern）

> **核心原則**：「絕不假設服務已就緒，必須確認後才繼續」— 適用於 CI 測試階段與 CD 部署階段。

| 場景 | 確認機制 | 超時策略 | 失敗處理 |
|------|---------|---------|---------|
| **容器/服務啟動** | wait-for-it.sh / dockerize / Testcontainers WaitStrategy | 30 秒硬超時 | 超時 = 啟動失敗，中止 Pipeline |
| **DB Migration** | exit code 驗證 + schema_version 表比對 | 依 Migration 規模 | 失敗立即中止，不繼續測試 |
| **HTTP 服務就緒** | Health Check endpoint (`/health` 回傳 200) | 30-60 秒 | 重試 3-5 次後中止 |
| **K8s Pod 就緒** | Readiness Probe + Init Container | 依 `failureThreshold` | Pod 不加入 Service 負載均衡 |
| **部署穩定性** | Smoke Test + Canary 錯誤率門檻 | 依 Canary 階段設定 | 自動回滾至前一版本 |

**反模式速查**：

| ❌ 絕對禁止 | ✅ 正確替代 |
|------------|-----------|
| `sleep 10 && run_tests` | `wait-for-it.sh host:port --timeout=30 -- run_tests` |
| `sleep 5 && curl /health` | `dockerize -wait http://host/health -timeout 30s` |
| Migration 失敗後繼續測試 | `migrate && verify_version \|\| exit 1` |
| 部署完直接宣告成功 | 部署 → Smoke Test → Health Check → 才宣告成功 |

> 📖 詳細工具用法與程式碼範例見 [Layer 2: 確定性同步](#確定性同步waituntil-pattern)。

### 6. 不可變產物最佳實踐（Immutable Artifact Pattern）

> **核心原則**：「Build Once, Deploy Many」— CI Build 產出的 Artifact 是唯一部署單元，所有環境使用同一個。

| 原則 | 說明 | 重要性 |
|------|------|--------|
| **Build Once** | Layer 1 Build 產出唯一 Artifact，推送至 Registry | 🔴 必須 |
| **Deploy Many** | Staging/Production 從 Registry 拉取同一 Artifact，禁止重新建置 | 🔴 必須 |
| **唯一標識** | 使用 Git SHA + Timestamp 標識，禁止依賴 `latest` 部署 | 🔴 必須 |
| **完整性校驗** | 部署前以 SHA256/Digest 校驗 Artifact 一致性 | 🟡 建議 |
| **環境注入** | 環境變數由部署時注入，禁止寫死在 Dockerfile | 🔴 必須 |

> 📖 詳見 [Immutable Artifact（不可變產物模式）](#immutable-artifact不可變產物模式) 完整指引。

---

## 環境變數管理

### 環境變數分類

| 類型 | 範例 | 儲存方式 | 存取方式 |
|------|------|---------|---------|
| **公開變數** | `NODE_ENV`, `API_VERSION` | Pipeline YAML | 直接引用 |
| **敏感變數** | `DATABASE_URL`, `API_KEY` | Secrets Manager | `${{ secrets.XXX }}` |
| **環境特定** | `API_BASE_URL` (Dev/Staging/Prod) | Environment Variables | 依環境載入 |

### Secrets 管理範例

**GitHub Actions**:
```yaml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  JWT_SECRET: ${{ secrets.JWT_SECRET }}
  STRIPE_API_KEY: ${{ secrets.STRIPE_API_KEY }}
```

**GitLab CI**:
```yaml
variables:
  DATABASE_URL: $DATABASE_URL  # 在 GitLab Settings → CI/CD → Variables 設定
```

---

## 部署策略

### 1. Blue/Green Deployment（藍綠部署）

**適用情境**: 需要零停機時間、快速回滾

```yaml
# GitHub Actions 範例
- name: Blue/Green Deployment
  run: |
    # 部署 Green 環境
    kubectl apply -f k8s/deployment-green.yaml
    kubectl wait --for=condition=available deployment/app-green

    # 切換流量至 Green
    kubectl patch service app -p '{"spec":{"selector":{"version":"green"}}}'

    # 驗證 Green 環境
    npm run test:smoke

    # 成功後刪除 Blue 環境
    kubectl delete deployment app-blue
```

### 2. Canary Deployment（金絲雀部署）

**適用情境**: 漸進式部署、風險降低

```yaml
# 階段 1: 部署 10% 流量至新版本
- name: Canary 10%
  run: |
    kubectl apply -f k8s/deployment-canary.yaml
    kubectl scale deployment app-canary --replicas=1
    kubectl scale deployment app-stable --replicas=9

# 階段 2: 監控 15 分鐘
- name: Monitor Canary
  run: |
    sleep 900
    ERROR_RATE=$(curl -s https://api.example.com/metrics | jq '.error_rate')
    if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
      echo "❌ Canary failed, rolling back"
      kubectl delete deployment app-canary
      exit 1
    fi

# 階段 3: 逐步增加至 100%
- name: Promote Canary
  run: |
    kubectl scale deployment app-canary --replicas=10
    kubectl scale deployment app-stable --replicas=0
    kubectl delete deployment app-stable
```

### 3. Rolling Update（滾動更新）

**適用情境**: 標準部署、Kubernetes 預設策略

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

---

## 監控與告警

### 部署監控指標

| 指標 | 說明 | 告警閾值 |
|------|------|---------|
| **部署成功率** | 成功部署次數 / 總部署次數 | < 95% |
| **部署時間** | 從開始到完成的時間 | > 30 分鐘 |
| **回滾次數** | 需要回滾的部署次數 | > 5% |
| **Pipeline 失敗率** | 失敗的 Pipeline 次數 | > 10% |

### Slack 通知範例

```yaml
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: |
      🚀 Deployment Status: ${{ job.status }}
      📦 Version: ${{ github.sha }}
      🌿 Branch: ${{ github.ref }}
      👤 Author: ${{ github.actor }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
  if: always()
```

---

## 變更歷史

| 版本 | 日期 | 變更內容 | 作者 |
|------|------|---------|------|
| v1.0 | 2025-11-21 | 初版建立：GitHub Actions、GitLab CI、Jenkins、Azure DevOps 完整配置範例、部署策略、監控告警 | AISDLC Team |
| v1.1 | 2026-03-23 | 新增 Layer 2 測試隔離模式（Testcontainers / CI Services / In-Memory DB 三策略）、確定性同步模式（WaitUntil Pattern）、反模式清單、GitHub Actions & GitLab CI Testcontainers 整合範例、通用最佳實踐「測試隔離」條目 | AISDLC Team |
| v1.2 | 2026-03-23 | P2-C 補強：確定性同步模式新增 dockerize 工具、K8s Readiness Probe + Init Container YAML 範例、DB Migration 就緒確認完整流程（exit code + schema_version 驗證）、通用最佳實踐新增獨立「確定性同步最佳實踐」子章節（跨測試+部署 5 場景） | AISDLC Team |
| v1.3 | 2026-03-23 | P2-A 不可變產物模式：新增 Immutable Artifact 完整章節（6 規則、標籤策略、SHA256 驗證、Multi-stage Dockerfile、Pipeline 流程圖、反模式、情境矩陣）、GitHub Actions & GitLab CI Immutable Artifact 整合範例、通用最佳實踐新增「不可變產物最佳實踐」子章節（5 原則） | AISDLC Team |
| v1.4 | 2026-03-23 | P2-A 驗證補強：Pipeline 層級架構圖新增 Immutable Artifact 層、Layer 1 執行順序圖新增 Artifact Push 步驟、Jenkins/Azure DevOps Production 部署修正 `latest` 反模式為版本標識、Layer1_Build_Verify_Template.md 新增 Immutable Artifact 交叉引用 | AISDLC Team |

---

## 授權與使用

本文檔為 **AISDLC Framework v0.01** 的一部分，遵循專案整體授權條款。

**使用建議**:
- ✅ 可自由複製、修改此範本，以符合專案需求
- ✅ 可整合至團隊的 CI/CD 平台
- ✅ 建議根據專案規模調整 Pipeline 階段
- ✅ 建議定期檢視與優化 Pipeline 效能

---

**🔗 相關文檔**:
- [Code_Review_Guidelines.md](../../../guides/user/process/Code_Review_Guidelines.md) - Code Review 指南
- [SOP.md - Stage 8](../../../scenarios/greenfield/SOP.md#階段-8開發準備) - Testing Standards
- [Security_Design_Checklist.md](../../../guides/system/quality/Security_Design_Checklist.md) - 安全性設計檢查清單
