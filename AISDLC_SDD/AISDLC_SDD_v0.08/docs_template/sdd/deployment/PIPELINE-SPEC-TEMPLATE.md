# Pipeline Specification Document — CI/CD Pipeline 規格模板
# 使用說明：複製至 docs/08_deployment/iac/PIPELINE-SPEC-{project}.md 後填寫

**專案名稱**: {ProjectName}
**版本**: v1.0
**建立日期**: {date}
**SCG 狀態**: 待 SCG-Pipeline 凍結
**前置文件**: `INFRA-REQUIREMENTS-SPEC-{system}.md`

---

## 1. Pipeline 概覽

**Pipeline 工具**: {GitHub Actions / GitLab CI / Jenkins}
**觸發條件**: Push to `{branch}` / PR to `{branch}` / Scheduled `{cron}`
**平均執行時間目標**: < {N 分鐘}

```
[Pipeline 流程圖 — Mermaid]

L0: DocLint → SpecTrace → IaCS-Validate
    ↓（通過）
L1: Build → Unit Test → Lint / SAST
    ↓（通過）
L2: Contract Test → Integration Test → Performance Gate
    ↓（通過，僅 main branch）
L3: Deploy to Staging → Smoke Test → [Manual Gate] → Deploy to Prod → Canary
```

---

## 2. L0 — 文件規格層（SDD Gate）

> 目的：確保規格文件先於實作，且規格完整

### 2.1 DocLint

| 項目 | 規格 | 失敗行為 |
|------|------|---------|
| 工具 | `markdownlint` + 自定義規則 | Fail Build |
| 觸發 | 所有 `docs/**/*.md` 修改 | — |
| 驗證規則 | 命名規範符合 AISDLC Rule 5 | — |
| 輸出 | `build/reports/lint/DocLint-{date}.md` | — |

```yaml
# Pipeline 配置範例（GitHub Actions）
doc_lint:
  name: "L0 DocLint"
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Lint docs
      run: npx markdownlint-cli2 "docs/**/*.md"
    - name: Check naming conventions
      run: python tools/doc-naming-check.py
```

### 2.2 SpecTrace（規格追溯驗證）

| 項目 | 規格 |
|------|------|
| 工具 | `tools/spec-trace-validator.py` |
| 驗證 | RTM 追溯鏈完整、ADR 覆蓋率 ≥ {%}、API Contract 追溯至 US |
| 失敗行為 | Fail Build |

### 2.3 IaCS-Validate（IaC 規格完整性）

| 項目 | 規格 |
|------|------|
| 工具 | `terraform validate` + 自定義規格檢查 |
| 驗證 | 每段 IaC 有對應規格注解（`# Spec: INFRA-{NNN}`） |
| 失敗行為 | Fail Build |

---

## 3. L1 — 建置測試層

### 3.1 Build

| 項目 | 規格 |
|------|------|
| 命令 | `{build command}` |
| 快取策略 | 依賴快取（`node_modules` / Maven / Gradle） |
| 工件產出 | `{artifact path}` |
| 預計時間 | < {N 分鐘} |

### 3.2 Unit Test

| 項目 | 規格 |
|------|------|
| 框架 | {JUnit / Jest / pytest} |
| 覆蓋率要求 | ≥ {%} (Line) / ≥ {%} (Branch) |
| 並行執行 | {是/否} |
| 預計時間 | < {N 分鐘} |

### 3.3 SAST（靜態安全掃描）

| 項目 | 規格 |
|------|------|
| 工具 | {SonarQube / Snyk / Semgrep} |
| 失敗條件 | Critical 或 High 漏洞 |
| 例外處理 | 需 Security Engineer ADR 核准 |

---

## 4. L2 — 契約測試層（SDD 核心）

### 4.1 Contract Tests

| 項目 | 規格 |
|------|------|
| 框架 | {Pact / Spring Cloud Contract} |
| 測試類型 | Consumer Contract Tests + Provider Verification |
| 執行環境 | Staging（或 Docker Compose 本地） |
| 失敗行為 | **Block PR merge**（任何契約測試失敗） |
| 輸出 | `build/reports/contract/Contract-Test-{date}.md` |

```yaml
# Contract Test 配置
contract_test:
  name: "L2 Contract Tests"
  runs-on: ubuntu-latest
  needs: [unit-test, build]
  steps:
    - name: Start services (Docker Compose)
      run: docker-compose -f docker-compose.test.yml up -d
    - name: Run Consumer Contract Tests
      run: {contract test command}
    - name: Run Provider Verification
      run: {provider verification command}
    - name: Publish Pact results
      run: {publish command}
    - name: Fail on contract violation
      if: failure()
      run: echo "CONTRACT VIOLATION - PR blocked"
```

### 4.2 Integration Tests

| 項目 | 規格 |
|------|------|
| 環境 | Staging（去識別化資料） |
| 覆蓋 | 所有外部整合點 |
| 超時設定 | {N 分鐘} |

### 4.3 Performance Gate

| 指標 | 閾值 | 測試工具 |
|------|------|---------|
| P95 延遲 | < {N}ms | {k6 / Gatling / JMeter} |
| 錯誤率 | < {%} | — |
| 吞吐量 | ≥ {N} RPS | — |

---

## 5. L3 — 部署層

### 5.1 Deploy to Staging

| 項目 | 規格 |
|------|------|
| 觸發 | `main` branch 通過 L0/L1/L2 |
| 策略 | Rolling Deploy |
| 驗證 | Smoke Tests |
| 通知 | Slack #deploy |

### 5.2 Manual Gate（Production 部署授權）

```
🔴 Human 確認：{決策者} 必須在 Staging 驗證後，手動授權 Production 部署
- 授權方式: {GitHub Environment Protection / Slack Bot / 操作介面}
- 授權超時: {N 小時}（超時自動取消）
```

### 5.3 Deploy to Production（Canary）

| 項目 | 規格 |
|------|------|
| 觸發 | Human Gate 通過 |
| 策略 | Canary（按 `CANARY-SPEC-{system}.md` 執行） |
| Phase 1 | 5% 流量，觀察 {N}h |
| 全量確認 | 🔴 Human 最終確認 |

---

## 6. 失敗處理規格

| 階段 | 失敗類型 | 自動行為 | 通知對象 |
|------|---------|---------|---------|
| L0 DocLint | 文件格式錯誤 | Block PR | PR 作者 |
| L1 Unit Test | 測試失敗 | Block PR | PR 作者 + Tech Lead |
| L1 SAST | Critical 漏洞 | Block PR | Security + Tech Lead |
| L2 Contract | 契約違反 | **Block PR + Alert** | Tech Lead + Integration Owner |
| L3 Staging | Smoke Test 失敗 | 告警 + 等待 | DevOps + Dev Lead |
| L3 Prod Canary | 錯誤率超標 | 自動回滾觸發 | All Team + Stakeholders |

---

## 7. 通知規格（Advanced）

```yaml
notifications:
  slack_channel: "#ci-cd-alerts"
  on_success:
    - "✅ {branch} Pipeline 通過 — {commit_sha[:8]}"
  on_failure:
    - "❌ {branch} Pipeline 失敗 — Stage: {stage}"
    - "@{author} 請查看: {run_url}"
  on_contract_violation:
    - "🚨 Contract Violation detected!"
    - "Breaking change in: {contract_name}"
    - "@{integration_owner} 需要立即處理"
  on_production_deploy:
    - "🚀 Production 部署開始 — {version}"
    - "Canary: {%}% 流量切換至新版本"
  on_canary_complete:
    - "🎉 Production 部署完成 100%"
```

---

## 8. SCG-Pipeline 凍結確認

- [ ] 所有 Stage 的輸入/輸出/成功條件已定義
- [ ] L2 Contract Test 已整合（不可跳過）
- [ ] L3 Canary 策略已連結至 Canary Spec
- [ ] 失敗處理規格完整
- [ ] 通知策略已定義
- [ ] IaC 每段均有規格注解
- [ ] 🔴 Human 確認：Pipeline 規格凍結

**最後更新**: {date}
