---
name: devops-docker
description: Docker 容器化配置，SCG-2 架構凍結後執行，產出 Dockerfile/Compose 並對應 ADR 決策
user-invocable: true
disable-model-invocation: false
argument-hint: "<app_type: nodejs|python|java|go|static> [environment: dev|production]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# DevOps Docker Skill（SDD 原生）

Docker 容器化是 SDD 部署架構的實作。本 Skill 在 SCG-2 架構凍結後執行，每個容器化決策（基礎映像選型、多階段構建策略）必須對應 ADR，Dockerfile 設計需符合 SRD 部署架構章節規格。

---

## 觸發方式

```bash
/devops-docker nodejs
/devops-docker python production
/devops-docker java
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-2 通過 | 架構凍結，部署策略確定 | `docs/02_architecture/SRD-{System}.md` 第 8 章（部署架構） |
| ADR 存在 | 容器化決策已記錄 | `/adr-generate "容器化策略"` 已執行，或在本 Skill 中執行 |

---

## 執行流程

### 階段 1：讀取 SRD 部署架構

讀取 `docs/02_architecture/SRD-{System}.md` 的部署架構章節，確認：
- 基礎映像版本要求（對應 NFR 版本要求）
- 環境變數清單（對應 FRD 設定需求）
- 服務依賴（DB / Cache / Queue）
- 健康檢查端點（對應 SRD 或 Contract 定義的 `/health`）

---

### 階段 2：ADR 建立（容器化決策）🔴

若 SRD 尚未記錄容器化 ADR，呼叫 `/adr-generate "容器化策略"` 記錄：

```markdown
# ADR-{NNN}: Docker 容器化策略

## Decision
使用多階段構建（Multi-stage Build）+ 非 root 使用者

## Rationale
- 多階段構建：分離構建/運行環境，減少映像大小
- 非 root：符合 NFR-SEC-XXX 安全要求
- Alpine 基礎映像：符合 NFR-XXX 映像大小限制

## Consequences
- Dockerfile 維護成本增加（多個 Stage）
- 需確保 Production Stage 不含開發依賴
```

🔴 確認點：ADR 記錄容器化策略決定後才繼續。

---

### 階段 3：Dockerfile 產出

依 app_type 產出對應 Dockerfile：

**Node.js 多階段構建**:

```dockerfile
# Dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Stage 2: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 3: Production（對應 SRD 部署架構）
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# 安全性：非 root（ADR-NNN 決策）
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 appuser

COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

USER appuser
EXPOSE 3000

# 健康檢查端點（對應 Contract /health）
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["node", "dist/index.js"]
```

**Java/Spring Boot 多階段構建（Layered JAR）**:

```dockerfile
# Dockerfile
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app
COPY gradle gradle
COPY gradlew build.gradle.kts settings.gradle.kts ./
RUN chmod +x gradlew && ./gradlew dependencies --no-daemon
COPY src src
RUN ./gradlew bootJar --no-daemon

FROM eclipse-temurin:21-jdk-alpine AS extractor
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar
RUN java -Djarmode=layertools -jar app.jar extract

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

RUN addgroup --system --gid 1001 spring && \
    adduser --system --uid 1001 appuser

COPY --from=extractor /app/dependencies/ ./
COPY --from=extractor /app/spring-boot-loader/ ./
COPY --from=extractor /app/snapshot-dependencies/ ./
COPY --from=extractor /app/application/ ./

USER appuser
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
```

---

### 階段 4：Docker Compose 產出（對應 SRD 服務拓撲）

```yaml
# docker-compose.yml
# 對應 SRD 服務清單（C4 Container 圖）
version: '3.9'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: runner
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/app
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:18-alpine     # 版本對應 SRD/ADR
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: app
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d app"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine         # 版本對應 SRD/ADR
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  postgres_data:
  redis_data:
```

---

### 階段 5：RTM 更新與規格確認 🔴

```bash
/rtm-generate update    # 更新部署相關 NFR 驗收 TC 狀態
/spec-compliance-check docs/02_architecture/SRD-{System}.md
```

🔴 確認點：Dockerfile 中的服務版本、健康檢查端點與 SRD 一致。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Dockerfile | `Dockerfile` | SCG-2 後 |
| Docker Compose | `docker-compose.yml` | SCG-2 後 |
| 容器化 ADR | `docs/02_architecture/adr/ADR-{NNN}-containerization.md` | SCG-2 |

---

## 後置動作

```
/devops-github-actions     # 配置 CI/CD Pipeline 使用 Docker
/devops-kubernetes         # 若需 K8s 部署（參考 SRD 部署架構）
/sdd-gate SCG-4            # Pipeline 設置完成後進行 PR Review
```

🔷 **本 Skill 對應 SCG**：SCG-2 後（部署架構凍結的實作）

---

## 相關 Skill

- `/sd-architect` — SRD 部署架構（Docker 設計的規格依據）
- `/adr-generate` — 容器化策略 ADR
- `/devops-github-actions` — 使用 Docker 的 CI/CD Pipeline
- `/devops-kubernetes` — K8s 部署（Docker Image 消費方）

---

**基於**: AISDLC-SDD v0.30
**對應架構規格**: `docs/02_architecture/SRD-{System}.md` 第 8 章
