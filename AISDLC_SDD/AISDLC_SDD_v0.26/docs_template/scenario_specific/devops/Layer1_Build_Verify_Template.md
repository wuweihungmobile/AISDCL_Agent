# Layer 1: Build & Verify 建置與驗證配置範本

> **🔴 強制要求**
>
> Layer 1 是**所有情境的強制建置驗證層**，緊接 Layer 0 (Security Baseline) 之後執行。
> 任何程式碼變更都必須通過 Lint、Build、Unit Test 三道關卡。
>
> - **適用範圍**: 所有 11 個 AISDLC 情境（greenfield ~ security）
> - **執行時機**: 每次 PR / Push（Layer 0 通過後）
> - **阻塞等級**: Lint 失敗阻塞、Build 失敗阻塞、Coverage 低於閾值阻塞
> - **前置條件**: Layer 0 Security Baseline 已通過

---

**版本**: v1.0
**建立日期**: 2026-03-22
**文檔類型**: DevOps 配置範本 | Build & Verify
**相關文檔**:
- [Layer0_Security_Baseline_Template.md](./Layer0_Security_Baseline_Template.md) - Layer 0 安全基線
- [Security_Scan_Integration_Template.md](./Security_Scan_Integration_Template.md) - P1 增強安全掃描（SAST/Container/DAST）
- [Migration_Pipeline_Template.md](./Migration_Pipeline_Template.md) - P1 Migration Pipeline
- [CICD_Pipeline_Template.md](./CICD_Pipeline_Template.md) - CI/CD Pipeline 完整範本
- [Performance_Benchmark_Gate_Template.md](./Performance_Benchmark_Gate_Template.md) - P2 效能基準關卡
- [Documentation_Pipeline_Template.md](./Documentation_Pipeline_Template.md) - P2 文檔 Pipeline
- [Event_Driven_Agent_Notification_Template.md](./Event_Driven_Agent_Notification_Template.md) - P3 事件驅動 Agent 通知
- [CICD_STRATEGIC_RESTRUCTURE_PLAN.md](../../../build/planning/archive/CICD_STRATEGIC_RESTRUCTURE_PLAN.md) - 戰略重構計畫

---

## 📋 目錄

1. [Layer 1 概覽](#layer-1-概覽)
2. [三大驗證關卡](#三大驗證關卡)
3. [多技術棧配置指引](#多技術棧配置指引)
4. [Coverage Gate 策略](#coverage-gate-策略)
5. [情境適配規則](#情境適配規則)
6. [快取與效能優化](#快取與效能優化)
7. [失敗處理與通知](#失敗處理與通知)
8. [維護與更新](#維護與更新)

---

## Layer 1 概覽

### 定位

```
Layer 0: Security Baseline ✅ 已通過
        ↓
┌───────────────────────────────────┐
│  Layer 1: Build & Verify          │  ← 強制、不可跳過
│  ├── 1.1 Lint + Format Check      │
│  ├── 1.2 Compile / Build          │
│  └── 1.3 Unit Test + Coverage Gate│
└───────────────────────────────────┘
        ↓ (全部通過)
Layer 2: Quality Assurance (情境選配)
        ↓
Layer 3: Deploy & Validate (情境選配)
```

### 設計原則

| 原則 | 說明 |
|------|------|
| **Fast Feedback** | 10 分鐘內完成，讓開發者快速得到結果 |
| **Fail-Fast** | Lint 失敗立即停止，不浪費 Build 時間 |
| **Deterministic** | 相同程式碼必須產出相同結果（鎖定依賴版本） |
| **Cacheable** | 依賴安裝和 Build 結果可快取，加速後續執行 |

### 執行順序（串行）

```
1.1 Lint + Format → 失敗? → 🔴 停止
        ↓ 通過
1.2 Compile / Build → 失敗? → 🔴 停止
        ↓ 通過
1.3 Unit Test + Coverage → Coverage < 閾值? → 🔴 停止
        ↓ 全部通過
→ 進入 Layer 2 或直接完成
```

---

## 三大驗證關卡

### 關卡 1: Lint + Format Check（程式碼風格驗證）

**目的**: 確保程式碼風格一致，在編譯前攔截低級錯誤。

**各語言推薦工具**:

| 語言 | Linter | Formatter | 配置檔 |
|------|--------|-----------|--------|
| **JavaScript/TypeScript** | ESLint | Prettier | `.eslintrc.js` + `.prettierrc` |
| **Python** | Ruff / Flake8 | Black / Ruff format | `pyproject.toml` / `ruff.toml` |
| **Java** | Checkstyle + SpotBugs | google-java-format | `checkstyle.xml` |
| **Go** | golangci-lint | gofmt / goimports | `.golangci.yml` |
| **Kotlin** | ktlint + detekt | ktlint | `.editorconfig` |
| **Rust** | clippy | rustfmt | `clippy.toml` + `rustfmt.toml` |
| **C#/.NET** | dotnet format | dotnet format | `.editorconfig` |

**執行策略**:
```yaml
lint_policy:
  blocking: true           # Lint 失敗阻塞 PR
  auto_fix: false          # CI 中不自動修復（保持 PR 乾淨）
  timeout: 300s            # 5 分鐘超時
  fail_fast: true          # 第一個錯誤即可停止（可選）
```

### 關卡 2: Compile / Build（編譯建置）

**目的**: 確認程式碼可成功編譯，依賴正確安裝，產出物可生成。

**各語言建置命令**:

| 語言/框架 | 安裝依賴 | 建置命令 | 產出物 |
|-----------|---------|---------|--------|
| **Node.js / Next.js** | `npm ci` | `npm run build` | `dist/` 或 `.next/` |
| **Python** | `pip install -r requirements.txt` | `python -m py_compile` 或 `python setup.py build` | `*.pyc` / `dist/` |
| **Java (Maven)** | `mvn dependency:resolve` | `mvn compile -DskipTests` | `target/classes/` |
| **Java (Gradle)** | `gradle dependencies` | `gradle compileJava -x test` | `build/classes/` |
| **Spring Boot** | 同上 | `gradle bootJar -x test` | `build/libs/*.jar` |
| **Go** | `go mod download` | `go build ./...` | 二進制檔 |
| **Android** | `gradle dependencies` | `gradle assembleDebug -x test` | `app/build/outputs/apk/` |
| **Rust** | (自動) | `cargo build` | `target/debug/` |
| **.NET** | `dotnet restore` | `dotnet build --no-restore` | `bin/` |

**執行策略**:
```yaml
build_policy:
  blocking: true           # Build 失敗阻塞 PR
  timeout: 600s            # 10 分鐘超時
  cache_dependencies: true # 快取依賴加速後續建置
  artifact_retention: 7d   # 產出物保留 7 天
```

### 關卡 3: Unit Test + Coverage Gate（單元測試 + 覆蓋率門檻）

**目的**: 驗證程式邏輯正確性，確保測試覆蓋率達標。

**各語言測試框架**:

| 語言 | 測試框架 | 覆蓋率工具 | 執行命令 |
|------|---------|-----------|---------|
| **JavaScript/TypeScript** | Jest / Vitest | c8 / istanbul | `npm run test -- --coverage` |
| **Python** | pytest | coverage.py / pytest-cov | `pytest --cov=src --cov-report=xml` |
| **Java (Maven)** | JUnit 5 | JaCoCo | `mvn test jacoco:report` |
| **Java (Gradle)** | JUnit 5 | JaCoCo | `gradle test jacocoTestReport` |
| **Go** | go test | 內建 | `go test -coverprofile=coverage.out ./...` |
| **Kotlin** | JUnit 5 / Kotest | JaCoCo / Kover | `gradle test koverReport` |
| **Rust** | 內建 | cargo-tarpaulin | `cargo tarpaulin --out Xml` |
| **.NET** | xUnit / NUnit | coverlet | `dotnet test --collect:"XPlat Code Coverage"` |

**覆蓋率門檻策略**:
```yaml
coverage_policy:
  # 全局最低覆蓋率
  global_threshold:
    lines: 80%             # 行覆蓋率 ≥ 80%
    branches: 70%          # 分支覆蓋率 ≥ 70%
    functions: 75%         # 函數覆蓋率 ≥ 75%

  # 差異覆蓋率（僅計算本次 PR 變更的程式碼）
  diff_threshold:
    lines: 85%             # 新增/修改行覆蓋率 ≥ 85%

  # 阻塞策略
  blocking: true           # 未達閾值阻塞 PR
  report_format: [html, xml, lcov]  # 報告格式
  upload_to: codecov       # 或 coveralls, sonarqube
```

---

## 多技術棧配置指引

### Node.js / Next.js / React

```yaml
# Layer 1 配置摘要
lint:
  tool: eslint + prettier
  command: "npm run lint && npx prettier --check ."
build:
  command: "npm ci && npm run build"
  cache: node_modules (hash of package-lock.json)
test:
  command: "npm run test -- --coverage --ci"
  coverage_tool: jest/c8
  threshold: { lines: 80, branches: 70 }
```

### Python (Django / Flask / FastAPI)

```yaml
lint:
  tool: ruff
  command: "ruff check . && ruff format --check ."
build:
  command: "pip install -r requirements.txt && python -m py_compile src/*.py"
  cache: pip cache dir
test:
  command: "pytest --cov=src --cov-report=xml --cov-fail-under=80"
  coverage_tool: pytest-cov
  threshold: { lines: 80, branches: 70 }
```

### Java (Spring Boot / Maven)

```yaml
lint:
  tool: checkstyle + spotbugs
  command: "mvn checkstyle:check spotbugs:check"
build:
  command: "mvn compile -DskipTests"
  cache: ~/.m2/repository
test:
  command: "mvn test jacoco:report"
  coverage_tool: jacoco
  threshold: { lines: 80, branches: 70 }
```

### Java (Spring Boot / Gradle)

```yaml
lint:
  tool: checkstyle + spotbugs
  command: "gradle checkstyleMain spotbugsMain"
build:
  command: "gradle compileJava -x test"
  cache: ~/.gradle/caches
test:
  command: "gradle test jacocoTestReport"
  coverage_tool: jacoco
  threshold: { lines: 80, branches: 70 }
```

### Go

```yaml
lint:
  tool: golangci-lint
  command: "golangci-lint run ./..."
build:
  command: "go build ./..."
  cache: GOMODCACHE
test:
  command: "go test -race -coverprofile=coverage.out ./..."
  coverage_tool: go tool cover
  threshold: { lines: 80 }
```

### Android (Kotlin/Java)

```yaml
lint:
  tool: ktlint + android lint
  command: "gradle ktlintCheck lint"
build:
  command: "gradle assembleDebug -x test"
  cache: ~/.gradle/caches
test:
  command: "gradle testDebugUnitTest koverReport"
  coverage_tool: kover
  threshold: { lines: 70, branches: 60 }
```

---

## Coverage Gate 策略

### 階梯式閾值（推薦）

新專案不必一開始就要求 80%，可採用階梯式提升：

| 階段 | 全局行覆蓋率 | 差異覆蓋率 | 適用時機 |
|------|:---:|:---:|---------|
| **啟動期** | ≥ 50% | ≥ 70% | 專案前 3 個 Sprint |
| **成長期** | ≥ 65% | ≥ 80% | 核心功能穩定後 |
| **成熟期** | ≥ 80% | ≥ 85% | 進入維護階段 |

### 覆蓋率排除規則

以下程式碼可排除覆蓋率計算（但需明確聲明）：

```yaml
coverage_exclusions:
  - "**/*.test.*"          # 測試檔案本身
  - "**/*.spec.*"          # 測試規格檔
  - "**/mocks/**"          # Mock 檔案
  - "**/migrations/**"     # DB 遷移腳本
  - "**/generated/**"      # 自動生成程式碼
  - "**/config/**"         # 配置檔案
  - "**/*_pb.go"           # Protobuf 生成
  - "**/index.ts"          # 純 re-export 檔案
```

---

## 情境適配規則

### 各情境 Layer 1 要求

| 情境 | Lint | Build | Unit Test | Coverage 閾值 | 附加要求 |
|------|:---:|:---:|:---:|:---:|---------|
| `greenfield` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 80% | - |
| `brownfield` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 65%* | *差異覆蓋率 85%，既有代碼按現狀 |
| `refactoring` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 80% | + Mutation Test (Layer 2) |
| `migration` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 70% | 新舊棧都要建置成功 |
| `performance` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 75% | + Benchmark (Layer 2) |
| `integration` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 75% | + Contract Test (Layer 2) |
| `devops` | ⚠️ IaC Lint | ⚠️ IaC Validate | ⚠️ IaC Test | N/A | Terraform validate + tflint |
| `testing` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 85% | 測試框架本身也需測試 |
| `documentation` | ⚠️ Doc Lint | ⚠️ Doc Build | ❌ 不適用 | N/A | markdownlint + link check |
| `security` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 80% | + SAST（Layer 0 Enhanced） |

> **`*` brownfield 特殊規則**: 既有程式碼覆蓋率可低於閾值，但**新增/修改行**的差異覆蓋率必須 ≥ 85%。

---

## 快取與效能優化

### 依賴快取策略

| 平台 | 快取 Key | 快取路徑 |
|------|---------|---------|
| **GitHub Actions** | `hashFiles('**/package-lock.json')` | `~/.npm` 或 `node_modules` |
| **GitLab CI** | `$CI_COMMIT_REF_SLUG` | `/cache/node_modules` |
| **Jenkins** | 手動管理 | Agent 本地目錄 |

### Build 產出物共享

```yaml
# Layer 1 Build 產出物供 Layer 2/3 使用
artifacts:
  build_output:
    path: dist/             # 或 build/, target/
    retention: 7 days
    shared_with: [layer2-jobs, layer3-jobs]
```

> **📦 Immutable Artifact 原則**：Layer 1 Build 產出的 Artifact（Docker Image / JAR / Bundle）必須遵循「**Build Once, Deploy Many**」原則 — 後續 Layer 2 測試、Layer 3 部署皆使用同一 Artifact，禁止在不同環境重新建置。
> 詳見 → [CICD_Pipeline_Template.md — Immutable Artifact（不可變產物模式）](./CICD_Pipeline_Template.md#immutable-artifact不可變產物模式)

### 超時設定

| 關卡 | 建議超時 | 說明 |
|------|---------|------|
| Lint | 3 分鐘 | 通常 < 1 分鐘 |
| Build | 10 分鐘 | 大型專案可達 5-8 分鐘 |
| Unit Test | 10 分鐘 | 包含覆蓋率計算 |
| **Layer 1 總計** | **15 分鐘** | 串行執行上限 |

---

## 失敗處理與通知

### 失敗分類與處理

| 失敗類型 | 處理方式 | 通知對象 |
|---------|---------|---------|
| **Lint 失敗** | 🔴 阻塞 PR，PR Comment 顯示錯誤位置 | PR 作者 |
| **Build 失敗** | 🔴 阻塞 PR，顯示編譯錯誤日誌 | PR 作者 |
| **Test 失敗** | 🔴 阻塞 PR，顯示失敗測試列表 | PR 作者 + QA |
| **Coverage 不足** | 🔴 阻塞 PR，顯示覆蓋率差異報告 | PR 作者 |
| **超時** | ⚠️ 警告，不阻塞（可能是 Runner 問題） | DevOps Engineer |

### PR Comment 自動報告

```markdown
## 🏗️ Layer 1: Build & Verify Results

| Check | Status | Details |
|-------|--------|---------|
| Lint  | ✅ Pass | 0 errors, 2 warnings |
| Build | ✅ Pass | 1m 23s |
| Tests | ✅ Pass | 142 passed, 0 failed |
| Coverage | ✅ 83.2% | +2.1% from base (threshold: 80%) |
```

---

## 維護與更新

### 定期更新週期

| 項目 | 更新頻率 | 負責角色 |
|------|---------|---------|
| Lint 規則 | 團隊共識時 | Tech Lead |
| 覆蓋率閾值 | 每季審查 | QA Lead + Tech Lead |
| 測試框架版本 | 每季 | DevOps Engineer |
| Build 工具版本 | 依 Security Advisory | DevOps Engineer |

### 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|---------|
| 2026-03-22 | v1.0 | 初始版本，建立三大驗證關卡 + 多技術棧配置 |
