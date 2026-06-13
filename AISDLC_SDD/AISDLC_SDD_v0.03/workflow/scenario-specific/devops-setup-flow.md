# DevOps Setup Flow
# DevOps 建置與 CI/CD 實作流程

## Workflow 名稱
**devops-setup-flow** - DevOps 完整建置流程

## 描述
建立完整的 DevOps 體系，包含環境規劃、CI/CD Pipeline、容器化、自動化測試、監控、災難恢復和成本優化。
支援多技術棧：Java/Spring Boot、React/Next.js、Android、macOS 桌面應用。

## 適用場景
- **使用時機**：專案啟動、DevOps 轉型、CI/CD 建置
- **適用專案**：所有需要自動化部署的專案（Web、API、行動端、桌面端）
- **執行頻率**：專案初期一次性建置，後續持續優化

## 觸發條件
- 專案需要自動化部署
- 代碼庫已建立
- 基礎設施可存取

---

# 角色與責任

## 主要負責人
**Agent 角色**：DevOps-Engineer (Lead) + SD-Architect (Infrastructure)
**責任**：DevOps 架構設計、CI/CD 建置

## 參與者
- **QA-Automation**：測試自動化整合 CI/CD
- **Dev-Developer**：Pipeline 腳本開發與部署腳本實作
- **Security-Engineer**：DevSecOps 安全掃描整合（SAST/DAST/依賴掃描）

## 可選參與者
- **SD-Mobile-Architect**：行動端 CI/CD（Android/macOS）建置時加入
- **QA-Mobile-Tester**：行動端自動化測試整合時加入
- **Performance-Engineer**：效能測試整合 CI/CD 時加入

---


---

## SDD SCG 閘門整合（v0.01）

> DevOps 流程在 SCG-3（Contract Freeze）通過後才可建立 CI/CD Pipeline。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| CI/CD 策略規劃 | SCG-3 通過後 | CI/CD 規格（基於凍結 Contract） |
| Pipeline 建立 | SCG-3 通過後 | SDD CI/CD（含 SCG-4 Check） |
| 環境配置 | SCG-3 通過後 | 環境規格文件 |
| 發布流程 | **🔴 SCG-6 凍結** | Release Checklist（所有閘門通過） |

**🔷 整合閘門**：SCG-3 後建立 → SCG-6（發布前驗證）
**📌 SDD CI/CD 規格**：參考 `cicd/SDD_TESTING_CICD.md`


# 執行步驟

## 🔴 步驟 0：Layer 0 Security Baseline 建置（強制前置，20-30 分鐘）
**執行者**：DevOps-Engineer + Security-Engineer

> **⚠️ 此步驟為所有情境的強制前置步驟**，無論專案使用哪個 Workflow 情境，都必須先完成 Layer 0 安全基線配置。

**作業內容**：
1. 配置 Pre-commit Hook（Secret Detection + 基礎安全檢查）
2. 配置 CI Pipeline Layer 0 階段（Secret Scan + SCA + License Check）
3. 設定阻塞策略（Critical/High 阻塞，Medium/Low 警告）
4. 設定超時熔斷機制（防止 Pipeline 死結）
5. 配置 Hotfix 旁路規則（緊急修復例外機制）

**確認點** 🔴：Layer 0 安全基線確認
- 審查 Pre-commit Hook 是否正確攔截 Secret
- 確認 SCA 掃描覆蓋所有依賴檔案
- 確認阻塞策略符合專案安全需求
- 驗證 Hotfix 旁路不會繞過 Secret Detection

**產出**：
- `.pre-commit-config.yaml`（本地安全攔截）
- CI Security Baseline Workflow（`.github/workflows/security-baseline.yml` 或等效配置）
- 阻塞策略與熔斷機制配置文件

**參考範本**：
- [Layer0_Security_Baseline_Template.md](../../docs_template/scenario_specific/devops/Layer0_Security_Baseline_Template.md)
- [pre-commit-config-template.yaml](../../docs_template/scenario_specific/devops/pre-commit-config-template.yaml)
- [security-baseline.yml](../../docs_template/scenario_specific/devops/github-actions/security-baseline.yml)

---

## 🔴 步驟 0.5：Layer 1 Build & Verify 建置（強制前置，20-30 分鐘）
**執行者**：DevOps-Engineer + Dev-Developer

> **⚠️ 此步驟與步驟 0 (Layer 0) 一同構成所有情境的強制前置步驟**，確保 CI Pipeline 涵蓋 Lint、Build、Unit Test 三道關卡。

**作業內容**：
1. 配置 Lint + Format Check（依專案語言選擇 ESLint/Ruff/Checkstyle/golangci-lint）
2. 配置 Build Job（編譯 + 依賴安裝 + 產出物上傳）
3. 配置 Unit Test + Coverage Gate（覆蓋率閾值預設 80%）
4. 設定依賴快取策略（加速後續 Pipeline 執行）
5. 配置串行執行順序（Lint → Build → Test，Fail-Fast）

**確認點** 🔴：Layer 1 Build & Verify 確認
- 審查 Lint 規則是否符合團隊 Coding Standards
- 確認 Build 產出物可正確生成
- 確認 Unit Test 可執行且 Coverage 達閾值
- 驗證 Fail-Fast 串行邏輯正確

**產出**：
- CI Build & Verify Workflow（`.github/workflows/build-verify.yml` 或等效配置）
- Lint 配置檔（`.eslintrc.js` / `ruff.toml` / `checkstyle.xml` 等）
- Coverage 報告上傳配置

**參考範本**：
- [Layer1_Build_Verify_Template.md](../../docs_template/scenario_specific/devops/Layer1_Build_Verify_Template.md)
- [build-verify.yml](../../docs_template/scenario_specific/devops/github-actions/build-verify.yml)

---

## 🔴 步驟 0.6：Migration 專屬 Pipeline 建置（Migration 情境限定，30-40 分鐘）
**執行者**：DevOps-Engineer + SD-Architect

> **⚠️ 此步驟僅在 Migration 情境時執行**，為 Migration 建立專屬的 Layer 2 (Contract Test) + Layer 3 (Canary Deploy + Rollback Gate) Pipeline。

**作業內容**：
1. 配置 Dual-Build Job（舊棧 + 新棧平行建置）
2. 配置 Contract Test Job（API 相容性驗證，推薦 Pact）
3. 配置 Canary Deploy（5% → 25% → 50% → 100% 漸進部署）
4. 配置 Rollback Gate（錯誤率 > 1% 自動回滾）
5. 配置 DB Migration Dry-Run + Rollback Script 驗證
6. 配置效能比對（新舊系統 P50/P99/RPS）

**確認點** 🔴：Migration Pipeline 確認
- 審查 Dual-Build 是否涵蓋新舊棧
- 確認 Contract Test 覆蓋所有 API 端點
- 確認 Canary 各階段閾值合理
- 驗證 Rollback 腳本可正確執行
- 確認 DB Migration 使用 Expand-Contract Pattern

**產出**：
- Migration Pipeline Workflow（`.github/workflows/migration-pipeline.yml` 或等效配置）
- Canary 配置檔（`deploy/canary-config.yaml`）
- Rollback 腳本（`deploy/rollback.sh`）

**參考範本**：
- [Migration_Pipeline_Template.md](../../docs_template/scenario_specific/devops/Migration_Pipeline_Template.md)
- [migration-pipeline.yml](../../docs_template/scenario_specific/devops/github-actions/migration-pipeline.yml)
- [migration-pipeline-template.yml](../../docs_template/scenario_specific/devops/gitlab-ci/migration-pipeline-template.yml)

---

## 🛡️ 步驟 0.7：Security Integration 增強安全掃描建置（依情境選配，20-30 分鐘）
**執行者**：DevOps-Engineer + Security-Engineer

> **⚠️ 此步驟依情境安全等級執行**，在 Layer 0 基礎安全之上，為各情境添加 SAST / Container Scan / DAST 增強掃描。
> - **Standard** (greenfield/brownfield/refactoring/testing): 加入 SAST
> - **Advanced** (migration/integration/performance/devops): 加入 SAST + Container Scan
> - **Enhanced** (security): 加入 SAST + Container Scan + DAST
> - **Basic** (documentation): 僅需 Layer 0，跳過此步驟

**作業內容**：
1. 確認情境安全等級（Basic/Standard/Advanced/Enhanced）
2. 配置 SAST 掃描（Semgrep/CodeQL，選擇語言專屬規則）
3. 配置 Container Scan（Trivy，Advanced 以上且有 Dockerfile 時）
4. 配置 DAST（OWASP ZAP，Enhanced 等級，需 Staging URL）
5. 設定阻塞策略（SAST/Container: Critical/High 阻塞；DAST: 僅警告）
6. 設定超時熔斷（SAST 10min, Container 10min, DAST 30min）

**確認點** 🔴：Security Integration 確認
- 審查 SAST 規則是否涵蓋專案語言
- 確認 Container Scan 覆蓋所有 Dockerfile
- 確認阻塞策略符合情境安全等級
- 驗證超時熔斷不影響正常 Pipeline 流程

**產出**：
- Enhanced Security Scan Workflow（`.github/workflows/security-scan-enhanced.yml` 或等效配置）
- `.security-ignore.yml`（例外清單，如需要）

**參考範本**：
- [Security_Scan_Integration_Template.md](../../docs_template/scenario_specific/devops/Security_Scan_Integration_Template.md)
- [security-scan-enhanced.yml](../../docs_template/scenario_specific/devops/github-actions/security-scan-enhanced.yml)
- [security-scan-enhanced-template.yml](../../docs_template/scenario_specific/devops/gitlab-ci/security-scan-enhanced-template.yml)

---

## ⚡ 步驟 0.8：Performance Benchmark Gate 效能基準關卡建置（依情境選配，15-20 分鐘）
**執行者**：DevOps-Engineer + Performance-Engineer

> **⚠️ 此步驟依情境適用性執行**，在 CI/CD Pipeline 中整合效能基準關卡，防止效能退化進入主分支。
> - **🔴 強制**: `performance` 情境 — Micro-Benchmark + Full Load Test
> - **⚠️ 選配**: `greenfield`, `brownfield`, `refactoring`, `migration` — 僅 Micro-Benchmark
> - **❌ 不適用**: `integration`, `devops`, `testing`, `documentation`, `security`

**作業內容**：
1. 確認情境是否需要 Performance Benchmark Gate
2. 選擇 Micro-Benchmark 工具（依語言：Vitest bench / pytest-benchmark / JMH / go bench）
3. 配置 Micro-Benchmark（PR 階段，< 2 分鐘硬上限）
4. 設定退化閾值（P50 > 10%、P95 > 15% 阻塞）
5. 配置 Full Load Test（Nightly 排程，performance 情境強制）
6. 設定效能基線快取策略（main 分支自動更新）

**確認點** 🔴：Performance Benchmark Gate 確認
- 審查 Benchmark 工具選型是否適合專案語言
- 確認退化閾值符合 SLA 要求
- 確認 Nightly 排程不影響通用 Runner 資源
- 驗證基線快取機制運作正常

**產出**：
- Performance Benchmark Workflow（`.github/workflows/perf-benchmark.yml` 或等效配置）
- `.perf-config.yml`（SLA 閾值配置，如需要）

**參考範本**：
- [Performance_Benchmark_Gate_Template.md](../../docs_template/scenario_specific/devops/Performance_Benchmark_Gate_Template.md)
- [perf-benchmark.yml](../../docs_template/scenario_specific/devops/github-actions/perf-benchmark.yml)
- [perf-benchmark-template.yml](../../docs_template/scenario_specific/devops/gitlab-ci/perf-benchmark-template.yml)

---

## 📝 步驟 0.9：Documentation Pipeline 文檔品質 Pipeline 建置（依情境選配，10-15 分鐘）
**執行者**：DevOps-Engineer + Technical-Writer

> **⚠️ 此步驟依情境適用性執行**，在 CI/CD Pipeline 中整合文檔品質自動化檢查。
> - **🔴 強制**: `documentation` 情境 — Doc Lint + Link Check + Build + Deploy
> - **⚠️ 選配**: `greenfield`, `brownfield`, `migration`, `integration` — 僅 Doc Lint + Link Check
> - **❌ 不適用**: `refactoring`, `performance`, `devops`, `testing`, `security`

**作業內容**：
1. 確認情境是否需要 Documentation Pipeline
2. 配置 Markdown Lint（markdownlint-cli2 + 自訂規則）
3. 配置 Link Check（lychee，PR 內部連結 + Nightly 外部連結）
4. 配置拼字檢查（cspell + 專案術語白名單）
5. 配置 Doc Build（MkDocs / Docusaurus / VitePress）
6. 配置 Deploy-Docs（GitHub Pages / GitLab Pages）

**確認點** 🔴：Documentation Pipeline 確認
- 審查 Markdown Lint 規則是否適合專案
- 確認 Link Check 排除清單合理
- 確認文檔建置工具選型
- 驗證部署目標可達

**產出**：
- Documentation Pipeline Workflow（`.github/workflows/docs-pipeline.yml` 或等效配置）
- `.markdownlint.yml` + `.cspell.json`（如需要）

**參考範本**：
- [Documentation_Pipeline_Template.md](../../docs_template/scenario_specific/devops/Documentation_Pipeline_Template.md)
- [docs-pipeline.yml](../../docs_template/scenario_specific/devops/github-actions/docs-pipeline.yml)
- [docs-pipeline-template.yml](../../docs_template/scenario_specific/devops/gitlab-ci/docs-pipeline-template.yml)

---

## 🔔 步驟 0.10：Event-Driven Agent Notification 事件驅動 Agent 通知系統建置（依情境選配，15-20 分鐘）
**執行者**：DevOps-Engineer + SD-Architect

> **⚠️ 此步驟建立跨 Agent 事件驅動協作通知系統**，使 Pipeline 各階段結果自動匯聚並通知相關角色。
> - **🔴 強制**: 所有程式碼相關情境（PR 事件通知）
> - **⚠️ 選配**: `documentation` 情境（輕量通知）
> - **情境專屬觸發**: `migration` (canary)、`refactoring` (mutation)、`security` (enhanced-SAST) 等

**作業內容**：
1. 配置事件驅動模型（pr_opened / pr_approved / release_tagged）
2. 配置 Agent 觸發鏈（並行執行 → 結果匯聚 → 統一判定）
3. 配置通知渠道（PR Comment + Slack + Email）
4. 配置超時熔斷機制（Agent 超時 10 分鐘 → 降級為 Warning）
5. 配置通知風暴防護（聚合窗口、分級路由）
6. 配置情境專屬觸發規則（依情境需求）

**確認點** 🔴：Agent 通知系統確認
- 審查事件觸發鏈是否完整覆蓋 PR → Staging → Production 生命週期
- 確認通知渠道配置（Slack Webhook URL / Email）
- 驗證超時熔斷機制不會造成 Pipeline 死結
- 確認通知格式清晰、包含足夠資訊供決策

**產出**：
- Agent Notification Workflow（`.github/workflows/agent-notification.yml` 或等效配置）
- 通知渠道配置（Slack Webhook URL in Secrets）

**參考範本**：
- [Event_Driven_Agent_Notification_Template.md](../../docs_template/scenario_specific/devops/Event_Driven_Agent_Notification_Template.md)
- [agent-notification.yml](../../docs_template/scenario_specific/devops/github-actions/agent-notification.yml)
- [agent-notification-template.yml](../../docs_template/scenario_specific/devops/gitlab-ci/agent-notification-template.yml)

---

## 步驟 1：環境規劃與架構設計 (40-60 分鐘)
**執行者**：DevOps-Engineer + SD

**作業內容**：
1. 環境分層設計（Local/Dev/Staging/Prod）
2. 基礎設施選型
3. 網路架構設計
4. IaC（Infrastructure as Code）設計

**確認點** 🔴：環境規劃確認
- 審查環境架構圖
- 確認基礎設施選型
- 確認成本預估

**產出**：環境規劃文件、基礎設施架構圖、IaC 配置

## 步驟 2：CI Pipeline 設計 (1-1.5 小時)
**執行者**：DevOps-Engineer + QA-Automation

**作業內容**：
1. 設計 CI Pipeline 流程
2. 配置 Quality Gates
3. Docker 容器化
4. 測試自動化整合

**確認點** 🔴：CI Pipeline 確認
- 審查 CI Pipeline 配置
- 確認 Quality Gates
- 確認容器化方案

**產出**：CI Pipeline 配置、Dockerfile、Docker Compose

## 步驟 3：CD Pipeline 設計 (1-1.5 小時)
**執行者**：DevOps-Engineer

**作業內容**：
1. 選擇部署策略（Rolling/Blue-Green/Canary）
2. 設計 CD Pipeline
3. Kubernetes 配置（如適用）
4. 自動擴展配置

**確認點** 🔴：CD Pipeline 確認
- 審查部署策略
- 確認 CD Pipeline
- 確認回滾方案

**產出**：CD Pipeline 配置、Kubernetes Manifests、部署 Runbook

## 步驟 4：監控與告警 (40-60 分鐘)
**執行者**：DevOps-Engineer

**作業內容**：
1. 建立監控體系（四大黃金指標）
2. 配置 Prometheus + Grafana
3. 設定告警規則
4. 配置應用程式指標

**確認點** 🔴：監控確認

**產出**：監控方案、Grafana 儀表板、告警規則

## 步驟 5：災難恢復與備份 (30-40 分鐘)
**執行者**：DevOps-Engineer

**作業內容**：
1. 設計備份策略（資料庫自動備份、異地備份）
2. 定義 RTO/RPO
3. 制定災難恢復計畫
4. 準備回復腳本

**產出**：備份策略、災難恢復計畫、RTO/RPO 定義

## 步驟 6：安全整合 DevSecOps (30-40 分鐘)
**執行者**：DevOps-Engineer + Security-Engineer

**作業內容**：
1. CI 整合安全掃描（SAST、依賴漏洞掃描）
2. Container Image 安全掃描（Trivy/Snyk）
3. Secret 管理方案（Vault/SOPS/GitHub Secrets）
4. HTTPS/TLS 憑證管理自動化

**確認點** 🔴：安全整合確認
- 審查安全掃描配置
- 確認 Secret 管理方案
- 確認合規需求覆蓋

**產出**：DevSecOps Pipeline 配置、Secret 管理方案

## 步驟 7：成本優化與文檔 (30-40 分鐘)
**執行者**：DevOps-Engineer

**作業內容**：
1. 資源使用量估算與成本優化
2. 成本告警設定
3. Runbook 與操作文檔撰寫
4. 團隊培訓材料準備

**產出**：成本優化方案、Runbook、操作手冊

---

# 輸出與交付

## 主要交付物
- 環境規劃文件
- CI/CD Pipeline 配置（支援多技術棧）
- 容器化方案（Dockerfile + Docker Compose + K8s Manifests）
- 監控方案（Prometheus + Grafana + 告警規則）
- 災難恢復計畫
- DevSecOps 安全配置
- 成本優化方案與 Runbook

## 交付標準
- CI/CD 自動化（建置 < 10 分鐘）
- 零停機部署
- 監控完整（四大黃金指標）
- 回滾可用（< 5 分鐘）
- 安全掃描整合

---

## 📚 參考資源

- [DevOps SOP 完整版](../../scenarios/devops/SOP.md)
- [DevOps QuickRef 快速參考](../../scenarios/devops/SOP_QuickRef.md)
- [DevOps DeepDive 深度指南](../../scenarios/devops/SOP_DeepDive.md)
- [DevOps 快速啟動指令集](../../prompts/scenario-prompts/devops-prompts.md)
- [AISDLC_INIT.md](../../AISDLC_SDD_INIT.md)

### 相關 Agents
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（主導）
- [sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（基礎設施架構設計）
- [qa-automation-zh.yaml](../../agent/specialized/qa-automation-zh.yaml) - QA Automation（CI 測試自動化）
- [dev-developer-zh.yaml](../../agent/core/06.dev-developer-zh.yaml) - David（Pipeline 腳本開發）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（DevSecOps）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（行動端 CI/CD，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端自動化測試，選用）
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（效能監控整合，選用）

### 相關 Skills
- `/devops-github-actions` - GitHub Actions CI/CD Pipeline 建置
- `/devops-gitlab-ci` - GitLab CI/CD Pipeline 建置
- `/devops-docker` - Docker 容器化配置（Dockerfile、docker-compose）
- `/devops-kubernetes` - Kubernetes 部署配置（Deployment、Service、Ingress）
- `/devops-monitoring` - 監控告警系統（Prometheus/Grafana）
- `/release-management` - 版本發布流程管理
- `/security-audit` - 安全審查（OWASP Top 10、DevSecOps）
- `/integration-database` - 資料庫整合（PostgreSQL 備份、連線池）
- `/performance-optimization` - 效能基準測試整合 CI/CD
- `/mobile-development` - 行動端 CI/CD（涉及 Android/iOS/macOS 時）

---

**版本**：v0.01
**維護者**：AISDLC Framework Team
**最後更新**：2026-04-17
