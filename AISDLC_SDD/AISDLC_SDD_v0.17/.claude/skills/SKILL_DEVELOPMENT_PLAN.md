# AISDLC Claude Skill 開發規劃
# Claude Skill Development Plan

**版本**: v0.02-SDD
**建立日期**: 2025-01-22
**最後更新**: 2026-04-14
**用途**: 規劃 AISDLC 九大情境和 Agent 轉化為 Claude Skill 的完整路線圖

---

## ✅ SDD 原生改寫完成（2026-04-14）

**改寫範圍**: 38 個 Skills 全部改寫為 SDD 原生設計

| 改寫 Phase | Skill 數量 | 狀態 |
|-----------|-----------|------|
| Phase 01：SDD Core Skills | 5 | ✅ 完成 |
| Phase 02：Agent Skills | 6 | ✅ 完成 |
| Phase 03：Scenario/Workflow Skills | 5 | ✅ 完成 |
| Phase 04：DevOps/Security/Doc Skills | 8 | ✅ 完成 |
| Phase 05：Integration/Quality Skills | 14 | ✅ 完成 |
| **總計** | **38** | ✅ **全部完成** |

**改寫核心變化**：
- SCG 閘門前置條件嵌入每個 Skill（非附加）
- RTM 更新步驟嵌入執行流程
- ADR 決策步驟嵌入設計先行階段
- Consumer Contract / Webhook Event Schema 定義嵌入 Integration Skills
- NFR 量化值作為 Monitoring/Performance Skill 的閾值依據

---

## 執行總覽

### 轉化評估矩陣

| 情境 | 獨立性 | 重複性 | 標準化 | 複雜度 | 用戶需求 | **總分** | **優先級** |
|------|--------|--------|--------|--------|----------|----------|-----------|
| DevOps | 5 | 5 | 5 | 3 | 5 | **4.6** | 🥇 第一波 |
| Integration | 5 | 5 | 5 | 3 | 5 | **4.6** | 🥇 第一波 |
| Brownfield | 5 | 5 | 5 | 2 | 4 | **4.2** | 🥇 第一波 |
| Refactoring | 5 | 4 | 5 | 3 | 4 | **4.2** | 🥈 第二波 |
| Performance | 5 | 4 | 4 | 4 | 4 | **4.2** | 🥈 第二波 |
| Testing | 4 | 5 | 3 | 4 | 5 | **4.2** | 🥈 第二波 |
| Documentation | 4 | 5 | 4 | 3 | 3 | **3.8** | 🥉 第三波 |
| Security | 4 | 3 | 4 | 4 | 3 | **3.6** | 🥉 第三波 |
| Greenfield | 3 | 4 | 3 | 5 | 3 | **3.6** | ❌ 不建議 |

**評分說明**: 5=完美, 4=高, 3=中, 2=低, 1=不適合

---

## 開發優先級與時程

### 🥇 第一波 - 立即開發（核心 Skills）

**目標**: 建立最常用、最高 ROI 的 Skills

| 序號 | Skill 名稱 | 觸發命令 | 檔案路徑 | 狀態 |
|------|-----------|---------|---------|------|
| 1 | DevOps GitHub Actions | `/devops-github` | `devops-github-actions/SKILL.md` | ✅ 已建立 |
| 2 | Integration OAuth | `/integration-oauth` | `scenarios/integration-oauth.md` | ✅ 已建立 |
| 3 | Brownfield Analysis | `/brownfield` | `scenarios/brownfield-analysis.md` | ✅ 已建立 |
| 4 | SA Analyst | `/sa-analyze` | `agents/sa-analyst.md` | ✅ 已建立 |

### 🥈 第二波 - 近期開發（擴展 Skills）

**目標**: 補完代碼改造和效能優化能力

| 序號 | Skill 名稱 | 觸發命令 | 檔案路徑 | 狀態 |
|------|-----------|---------|---------|------|
| 5 | Refactoring Code Quality | `/refactor` | `scenarios/refactoring-code-quality.md` | ✅ 已建立 |
| 6 | Performance Optimization | `/performance` | `scenarios/performance-optimization.md` | ✅ 已建立 |
| 7 | Testing Strategy | `/testing` | `scenarios/testing-strategy.md` | ✅ 已建立 |
| 8 | DevOps Kubernetes | `/devops-k8s` | `scenarios/devops-kubernetes.md` | ✅ 已建立 |
| 9 | Integration Stripe | `/integration-stripe` | `scenarios/integration-stripe.md` | ✅ 已建立 |

### 🥉 第三波 - 未來開發（專業 Skills）

| 序號 | Skill 名稱 | 觸發命令 | 檔案路徑 | 狀態 |
|------|-----------|---------|---------|------|
| 10 | Security Audit | `/security` | `scenarios/security-audit.md` | ✅ 已建立 |
| 11 | Documentation API | `/doc-api` | `scenarios/documentation-api.md` | ✅ 已建立 |
| 12 | SD Architect | `/sd-design` | `agents/sd-architect.md` | ✅ 已建立 |
| 13 | QA Testing | `/qa-test` | `agents/qa-testing.md` | ✅ 已建立 |

---

## Skill 家族規劃

### DevOps Skill 家族

```
devops/
├── devops-github-actions.md   ✅ GitHub Actions CI/CD
├── devops-kubernetes.md       ✅ Kubernetes 部署
├── devops-gitlab-ci.md        ✅ GitLab CI/CD
├── devops-docker.md           ✅ Docker 容器化
└── devops-monitoring.md       ✅ 監控告警設定 (Prometheus/Grafana)
```

### Integration Skill 家族

```
integration/
├── integration-oauth.md       ✅ OAuth 認證整合
├── integration-stripe.md      ✅ Stripe 支付
├── integration-api-client.md  ✅ 通用 API 客戶端
├── integration-aws.md         ✅ AWS 服務整合 (S3/SES/SQS/SNS)
├── integration-webhook.md     ✅ Webhook 處理
├── integration-firebase.md    ✅ Firebase BaaS 整合
├── integration-sendgrid.md    ✅ SendGrid 郵件服務
├── integration-openai.md      ✅ OpenAI API 整合
├── integration-database.md    ✅ 資料庫/ORM 整合 (Prisma)
└── integration-redis.md       ✅ Redis 快取/佇列
```

### Code Quality Skill 家族

```
code-quality/
├── brownfield-analysis.md     ✅ 系統分析
├── refactoring-code-quality.md ✅ 代碼重構
├── code-review.md             📋 代碼審查
└── tech-debt-tracking.md      📋 技術債追蹤
```

### Agent Skill 家族

```
agents/
├── sa-analyst.md              ✅ 需求分析 (SA)
├── ba-analyst.md              ✅ 業務驗證 (BA) 🆕
├── sd-architect.md            ✅ 架構設計 (SD)
├── qa-testing.md              ✅ 測試策略 (QA)
├── dev-review.md              ✅ 代碼審查 (Dev)
└── pm-planning.md             ✅ 產品規劃 (PM)
```

### Workflow Skill 家族

```
workflows/
├── sprint-planning.md         ✅ Sprint 規劃流程
├── release-management.md      ✅ 發布管理流程
└── code-review.md             ✅ 代碼審查流程
```

---

## 完成進度統計

### 已完成 Skills

| 類別 | 數量 | 詳細 |
|------|------|------|
| DevOps | 5 | github-actions, kubernetes, gitlab-ci, docker, monitoring |
| Integration | 10 | oauth, stripe, api-client, aws, webhook, firebase, sendgrid, openai, database, redis |
| Code Quality | 4 | brownfield, refactoring, performance, testing |
| Security/Docs/Compliance | 3 | security-audit, compliance-audit, documentation-api |
| Agents | 6 | sa-analyst, ba-analyst, sd-architect, qa-testing, dev-review, pm-planning |
| Workflows | 3 | sprint-planning, release-management, code-review |
| **總計** | **31** | - |

### 待開發 Skills

| 類別 | 數量 | 優先級 |
|------|------|--------|
| - | 0 | 所有規劃項目已完成 ✅ |

---

## 設計原則

### 1. Skill 命名規範

```
{category}-{feature}/SKILL.md

範例:
- devops-github-actions/SKILL.md
- integration-oauth/SKILL.md
- sa-analyst/SKILL.md
```

### 2. Skill 結構標準 (Claude Code Agent Skills Standard)

```yaml
---
name: skill-name-kebab-case
description: 功能描述
user-invocable: true
disable-model-invocation: false
argument-hint: "<required_param: 說明> [optional_param: 說明]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Skill 內容

## 觸發方式
## 執行流程
## 產出物
## 相關 Skill
## 相關檔案
```

### 3. 人機確認點設計

所有關鍵決策點必須標記 🔴:

```markdown
🔴 **確認點**: 向使用者確認 XXX
```

### 4. 與 AISDLC SOP 對應

每個 Skill 必須：
- 引用對應的 SOP 文件
- 遵循 AISDLC 流程規範
- 保持追蹤鏈完整

---

## 下一步行動

### 短期 (本週) ✅ 已完成

- [x] 完善已建立的 Skill
- [x] 建立完整 DevOps 家族 (5 個)
- [x] 建立完整 Integration 家族 (10 個)

### 中期 (本月) ✅ 已完成

- [x] 建立 Agents 家族 (dev-review, pm-planning)
- [x] 建立 Workflow Skills (sprint-planning, release-management, code-review)

### 🔴 當前優先任務：SDD 原生改寫（2026-04-14 啟動）

> 計畫文件：`build/planning/active/Skill_for_SDD_Planning_Phase_01.md`

**問題**：現有 33 個繼承 Skill 採用「AISDLC v0.01 + 附加 SDD 區塊」模式，
非 SDD 原生設計，SCG 閘門游離、RTM 缺席、前置條件不明。

**目標**：38 個 Skill 全部改寫為 SDD 原生，嵌入 Spec-First/Design-as-Doc/Contract-Driven 三大支柱

| Phase | 範疇 | Skill 數 | 狀態 |
|-------|------|---------|------|
| Phase 01 | SDD 核心 Skill 精化 + 新標準建立 | 5 | ⬜ 待執行 |
| Phase 02 | Agent Skill 全面改寫 | 6 | ⬜ 待執行 |
| Phase 03 | Scenario + Workflow Skill 改寫 | 5 | ⬜ 待執行 |
| Phase 04 | DevOps + Security/Docs Skill 改寫 | 8 | ⬜ 待執行 |
| Phase 05 | Integration + Code Quality Skill 改寫 | 14 | ⬜ 待執行 |
| Phase 06 | 整合測試 + 文件更新 | - | ⬜ 待執行 |

### 長期 (季度)

- [ ] Skill 組合使用指南
- [ ] 根據改寫後回饋繼續優化

---

## 檔案結構 (Claude Code Agent Skills Standard)

```
AISDLC_SDD_v0.01/.claude/skills/
├── README.md                              ✅ 總覽文檔
├── SKILL_DEVELOPMENT_PLAN.md              ✅ 本文件
├── devops-github-actions/SKILL.md         ✅ GitHub Actions
├── devops-kubernetes/SKILL.md             ✅ Kubernetes
├── devops-gitlab-ci/SKILL.md              ✅ GitLab CI/CD
├── devops-docker/SKILL.md                 ✅ Docker 容器化
├── devops-monitoring/SKILL.md             ✅ 監控告警
├── integration-oauth/SKILL.md             ✅ OAuth 認證
├── integration-stripe/SKILL.md            ✅ Stripe 支付
├── integration-api-client/SKILL.md        ✅ API 客戶端
├── integration-webhook/SKILL.md           ✅ Webhook 處理
├── integration-aws/SKILL.md               ✅ AWS 服務
├── integration-firebase/SKILL.md          ✅ Firebase
├── integration-sendgrid/SKILL.md          ✅ SendGrid 郵件
├── integration-openai/SKILL.md            ✅ OpenAI API
├── integration-database/SKILL.md          ✅ 資料庫/Prisma
├── integration-redis/SKILL.md             ✅ Redis 快取
├── brownfield-analysis/SKILL.md           ✅ 系統分析
├── refactoring-code-quality/SKILL.md      ✅ 代碼重構
├── performance-optimization/SKILL.md      ✅ 效能優化
├── testing-strategy/SKILL.md              ✅ 測試策略
├── security-audit/SKILL.md                ✅ 安全審計
├── compliance-audit/SKILL.md              ✅ 合規審查 (GDPR/HIPAA/PCI-DSS)
├── documentation-api/SKILL.md             ✅ API 文檔
├── sa-analyst/SKILL.md                    ✅ 需求分析
├── ba-analyst/SKILL.md                    ✅ 業務驗證
├── sd-architect/SKILL.md                  ✅ 架構設計
├── qa-testing/SKILL.md                    ✅ 測試策略
├── dev-review/SKILL.md                    ✅ 代碼審查
├── pm-planning/SKILL.md                   ✅ 產品規劃
├── sprint-planning/SKILL.md               ✅ Sprint 規劃
├── release-management/SKILL.md            ✅ 發布管理
└── code-review/SKILL.md                   ✅ 代碼審查流程
```

---

**維護者**: AISDLC Framework Team
**最後更新**: 2026-02-05
**格式標準**: Claude Code Agent Skills Standard (`<name>/SKILL.md`)
