---
name: devops-docker
description: Docker 容器化配置，包含 Dockerfile、docker-compose、多階段構建
user-invocable: true
disable-model-invocation: false
argument-hint: "<app_type: 應用類型 (nodejs/python/java/go/static)> [environment: 環境類型 (dev/production)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# DevOps Docker Skill

建立專業的 Docker 容器化配置。

---

## 觸發方式

```bash
/devops-docker nodejs           # Node.js 應用
/devops-docker python production # Python 生產環境
/devops-docker --app_type=go
```

---

## 執行流程

### 階段 1: 需求評估 🔴

**確認項目**:
- [ ] 應用類型和運行時版本
- [ ] 基礎映像選擇
- [ ] 環境變數需求
- [ ] 掛載卷需求
- [ ] 網路配置需求

🔴 **確認點**: 確認容器化需求

---

### 階段 2: Dockerfile 配置

#### Node.js 多階段構建

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

# Stage 3: Production
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# 安全性：非 root 使用者
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 appuser

COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

USER appuser

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

#### Python 應用

```dockerfile
# Dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app

RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt

FROM python:3.12-slim
WORKDIR /app

RUN useradd --create-home appuser
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
```

#### Java/Spring Boot 多階段構建 (Layered JAR)

```dockerfile
# Dockerfile
# Stage 1: Build with Gradle
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app
COPY gradle gradle
COPY gradlew build.gradle.kts settings.gradle.kts ./
RUN chmod +x gradlew && ./gradlew dependencies --no-daemon
COPY src src
RUN ./gradlew bootJar --no-daemon

# Stage 2: Extract layers
FROM eclipse-temurin:21-jdk-alpine AS extractor
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar
RUN java -Djarmode=layertools -jar app.jar extract

# Stage 3: Production
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

RUN addgroup --system --gid 1001 spring
RUN adduser --system --uid 1001 appuser

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

#### Next.js 多階段構建

```dockerfile
# Dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Stage 2: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 3: Production
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

---

### 階段 3: Docker Compose 配置

```yaml
# docker-compose.yml
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
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  db:
    image: postgres:18-alpine
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
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    driver: bridge
```

---

### 階段 4: 開發環境配置

```yaml
# docker-compose.override.yml (開發環境)
version: '3.9'

services:
  app:
    build:
      target: builder
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
    command: npm run dev
```

---

### 階段 5: .dockerignore 配置

```
# .dockerignore
node_modules
npm-debug.log
Dockerfile*
docker-compose*
.git
.gitignore
.env*
*.md
.vscode
.idea
coverage
.nyc_output
```

---

### 階段 6: 驗證 🔴

**驗證清單**:
- [ ] Docker build 成功
- [ ] 容器正常啟動
- [ ] 健康檢查通過
- [ ] 服務間通訊正常
- [ ] 掛載卷正確

**驗證命令**:
```bash
# 構建
docker compose build

# 啟動
docker compose up -d

# 檢查狀態
docker compose ps

# 查看日誌
docker compose logs -f app

# 健康檢查
docker compose exec app curl localhost:3000/health
```

🔴 **確認點**: 確認容器運行正常

---

## 最佳實踐

| 項目 | 建議 |
|------|------|
| 基礎映像 | 使用 Alpine 減少體積 |
| 多階段構建 | 分離構建和運行環境 |
| 非 root 使用者 | 安全性考量 |
| 健康檢查 | 確保服務可用性 |
| .dockerignore | 排除不必要文件 |

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Dockerfile | `Dockerfile` |
| Docker Compose | `docker-compose.yml` |
| 開發覆蓋 | `docker-compose.override.yml` |
| 忽略文件 | `.dockerignore` |

---

## 相關 Skill

- `/devops-k8s` - Kubernetes 部署
- `/devops-github` - CI/CD Pipeline
- `/devops-gitlab` - GitLab CI/CD

---


## 相關檔案

- SOP 參考: `scenarios/devops/SOP_QuickRef.md`

**基於**: AISDLC v0.09 DevOps 情境
