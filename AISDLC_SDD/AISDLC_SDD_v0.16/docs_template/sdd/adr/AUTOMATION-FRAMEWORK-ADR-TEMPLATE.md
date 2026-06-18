# ADR-{NNN}: 測試自動化框架選型決策
# Automation Framework Architecture Decision Record — Template
# Phase 05 — Testing 情境 SDD 強化

**狀態**: □ Proposed / □ Accepted / □ Deprecated / □ Superseded
**決策日期**: {YYYY-MM-DD}
**ADR 負責人**: {QA Lead / QA Automation}
**相關文件**: TEST-STRATEGY-SPEC-{project}.md, SRD-{project}.md

---

## 背景（Context）

{專案名稱} 需要選定測試自動化框架，以支持 Test Strategy Spec 所定義的測試金字塔。

**技術棧**: {Frontend: React/Vue/Angular | Backend: Node.js/Java/Python | Mobile: iOS/Android}
**團隊規模**: {N} 人
**CI/CD 平台**: GitHub Actions / GitLab CI / Jenkins / Azure DevOps

---

## 決策問題（Decision Question）

> 針對以下測試層，應選擇哪些自動化框架？

1. **Unit Test 框架** — 業務邏輯單元測試
2. **Integration Test 框架** — 服務整合測試
3. **API/Contract Test 框架** — API 契約測試
4. **E2E Test 框架** — 使用者旅程測試
5. **Performance Test 框架** — 效能負載測試
6. **Security Test 框架** — SAST/DAST

---

## 選項分析

### 1. Unit Test 框架

| # | 選項 | 優點 | 缺點 | 適用場景 |
|---|------|------|------|---------|
| 1 | Jest（JavaScript） | 速度快、生態完整、內建 Mock | 僅限 JS/TS | Node.js / React / Vue |
| 2 | JUnit 5（Java） | 成熟穩定、功能豐富 | Java 生態限定 | Spring Boot |
| 3 | pytest（Python） | 簡潔、插件豐富 | Python 限定 | Django / FastAPI |
| 4 | Go Testing（Go） | 內建、零依賴 | 功能相對基礎 | Go 服務 |

**選定**: {選項 #}
**理由**: {reason}

---

### 2. Integration Test 框架

| # | 選項 | 優點 | 缺點 |
|---|------|------|------|
| 1 | Testcontainers | 真實容器環境、跨語言 | 需要 Docker、較慢 |
| 2 | REST Assured（Java） | 流式 API 測試、易讀 | Java 限定 |
| 3 | Supertest（Node.js） | 輕量、與 Express 完美整合 | Node.js 限定 |
| 4 | pytest + requests（Python） | 靈活、易用 | 需手動管理環境 |

**選定**: {選項 #}
**理由**: {reason}

---

### 3. Contract Test 框架（建議固定選 Pact）

| # | 選項 | 優點 | 缺點 |
|---|------|------|------|
| 1 | **Pact（推薦）** | Consumer-Driven、多語言、Pact Broker 生態 | 學習曲線較高 |
| 2 | Spring Cloud Contract | 與 Spring 整合佳 | Java 限定 |
| 3 | Dredd | OpenAPI 驅動 | 僅支持 HTTP |

**選定**: Pact（SDD 框架標準選型，支持 Consumer-Driven Contract）
**理由**: 符合 SDD Contract-Driven 第三支柱，支持 `can-i-deploy` 破壞性變更保護

---

### 4. E2E Test 框架

| # | 選項 | 優點 | 缺點 | 適用場景 |
|---|------|------|------|---------|
| 1 | Playwright | 跨瀏覽器、速度快、現代 API | 需 Node.js | Web App |
| 2 | Cypress | DX 佳、即時重載 | 單一 Tab、無 iframe 限制 | Web App |
| 3 | Selenium + WebDriver | 最成熟、多語言 | 速度較慢 | 舊系統維護 |
| 4 | Appium | 跨平台 Mobile | 設定複雜 | iOS + Android |
| 5 | XCUITest / Espresso | 原生效能最佳 | 平台限定 | Native Mobile |

**選定**: {選項 #}
**理由**: {reason}

---

### 5. Performance Test 框架

| # | 選項 | 優點 | 缺點 |
|---|------|------|------|
| 1 | k6 | 現代、JS 腳本、CI 友好、雲端版 | 協議支持不如 JMeter |
| 2 | Apache JMeter | 功能最完整、GUI 工具 | 資源耗用高、Java |
| 3 | Gatling | 高效能、Scala DSL | 學習曲線 |
| 4 | Locust | Python 腳本、分散式 | 效能稍低 |

**選定**: {選項 #}
**理由**: {reason}

---

### 6. Security Test 工具

| # | 選項 | 用途 | 推薦 |
|---|------|------|------|
| 1 | SonarQube / Semgrep | SAST — 靜態分析 | ✅ |
| 2 | OWASP ZAP | DAST — 動態掃描 | ✅ |
| 3 | Snyk / Dependabot | SCA — 依賴漏洞 | ✅ |
| 4 | Trivy | Container 安全掃描 | ✅ |

**選定**: SAST={選項}, DAST=OWASP ZAP, SCA=Snyk, Container=Trivy
**理由**: {reason}

---

## 決策（Decision）

### 最終選型矩陣

| 測試層 | 選定框架 | 版本 | CI 整合方式 |
|-------|---------|------|-----------|
| Unit | {framework} | {version} | `{CI step}` |
| Integration | {framework} | {version} | `{CI step}` |
| Contract | Pact | {version} | Pact Broker + `can-i-deploy` |
| E2E | {framework} | {version} | `{CI step}` |
| Performance | {framework} | {version} | Benchmark Stage |
| SAST | {tool} | {version} | L1 Stage |
| DAST | OWASP ZAP | latest | L3 Stage |

---

## 後果（Consequences）

### 正面後果
- 統一的測試工具鏈，降低維護成本
- Pact 確保 Contract-Driven 原則落地
- CI 全自動化，Quality Gate 可量化

### 負面後果 / 風險
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| 團隊 Pact 學習曲線 | Medium | 安排 Workshop 培訓 |
| {risk} | {impact} | {mitigation} |

---

## 合規追蹤

| 原則 | 合規狀態 |
|------|---------|
| SDD Contract-Driven（第三支柱） | □ 合規（Pact 實作 CDC） |
| Test Pyramid Spec 覆蓋 | □ 合規（每層有工具） |
| CI/CD 整合 | □ 合規（每工具有 CI Step） |

---

## 版本記錄

| 日期 | 版本 | 變更內容 | 作者 |
|------|------|---------|------|
| {date} | v1.0 | 初始決策 | {author} |
