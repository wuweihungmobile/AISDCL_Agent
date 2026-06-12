# AISDLC Claude Skills
# Claude Code 技能套件

**版本**: v0.09
**建立日期**: 2025-01-22
**最後更新**: 2026-04-11
**格式標準**: Claude Code Agent Skills Standard (`<name>/SKILL.md`)
**用途**: 將 AISDLC 十大情境和 Agent 能力轉化為可重複使用的 Claude Skills

---

## 快速開始

```bash
# DevOps
/devops-github          # GitHub Actions CI/CD
/devops-k8s             # Kubernetes 部署
/devops-gitlab          # GitLab CI/CD
/devops-docker          # Docker 容器化
/devops-monitoring      # 監控告警

# Integration
/integration-oauth      # OAuth 認證
/integration-stripe     # Stripe 支付
/integration-api        # API 客戶端
/integration-aws        # AWS 服務
/integration-webhook    # Webhook 處理
/integration-firebase   # Firebase
/integration-sendgrid   # SendGrid 郵件
/integration-openai     # OpenAI API
/integration-database   # Database/Prisma
/integration-redis      # Redis 快取

# Code Quality
/code-review            # 代碼審查流程
/refactor               # 代碼重構
/performance            # 效能優化
/testing                # 測試策略

# Security / Compliance / Docs
/security               # 安全審計
/compliance-audit       # 合規審查 (GDPR/HIPAA/PCI-DSS)
/documentation-api      # API 文檔

# Agents
/sa-analyze             # SA 需求分析
/ba-validate            # BA 業務驗證
/sd-design              # SD 架構設計
/qa-test                # QA 測試策略
/dev-review             # Dev 代碼審查
/pm-planning            # PM 產品規劃

# Workflows
/sprint-planning        # Sprint 規劃
/release-management     # 發布管理

# Scenario / Dev
/brownfield             # 棕地系統分析
/database-migration     # 資料庫遷移
/mobile-development     # 行動端開發
```

---

## 目錄結構

> **格式說明**: 遵循 Claude Code Agent Skills 標準，每個 Skill 為獨立目錄內含 `SKILL.md`。

```
.claude/skills/
├── README.md                              # 本文件
├── SKILL_DEVELOPMENT_PLAN.md              # 開發規劃
│
│── # DevOps 家族 (5個)
├── devops-github-actions/SKILL.md         # GitHub Actions CI/CD
├── devops-kubernetes/SKILL.md             # Kubernetes 部署
├── devops-gitlab-ci/SKILL.md              # GitLab CI/CD
├── devops-docker/SKILL.md                 # Docker 容器化
├── devops-monitoring/SKILL.md             # 監控告警
│
│── # Integration 家族 (10個)
├── integration-oauth/SKILL.md             # OAuth 認證
├── integration-stripe/SKILL.md            # Stripe 支付
├── integration-api-client/SKILL.md        # API 客戶端
├── integration-webhook/SKILL.md           # Webhook 處理
├── integration-aws/SKILL.md               # AWS 服務
├── integration-firebase/SKILL.md          # Firebase
├── integration-sendgrid/SKILL.md          # SendGrid 郵件
├── integration-openai/SKILL.md            # OpenAI API
├── integration-database/SKILL.md          # Database/Prisma
├── integration-redis/SKILL.md             # Redis 快取
│
│── # Code Quality 家族 (4個)
├── code-review/SKILL.md                   # 代碼審查
├── refactoring-code-quality/SKILL.md      # 代碼重構
├── performance-optimization/SKILL.md      # 效能優化
├── testing-strategy/SKILL.md              # 測試策略
│
│── # Security / Compliance / Docs 家族 (3個)
├── security-audit/SKILL.md                # 安全審計
├── compliance-audit/SKILL.md              # 合規審查 (GDPR/HIPAA/PCI-DSS)
├── documentation-api/SKILL.md             # API 文檔
│
│── # Agent 家族 (6個)
├── sa-analyst/SKILL.md                    # SA 需求分析
├── ba-analyst/SKILL.md                    # BA 業務驗證
├── sd-architect/SKILL.md                  # SD 架構設計
├── qa-testing/SKILL.md                    # QA 測試
├── dev-review/SKILL.md                    # Dev 審查
├── pm-planning/SKILL.md                   # PM 規劃
│
│── # Workflow 家族 (2個)
├── sprint-planning/SKILL.md               # Sprint 規劃
├── release-management/SKILL.md            # 發布管理
│
│── # Scenario / Dev 家族 (3個)
├── brownfield-analysis/SKILL.md           # 棕地系統分析
├── database-migration/SKILL.md            # 資料庫遷移
└── mobile-development/SKILL.md            # 行動端開發
```

---

## Skill 統計

| 類別 | 數量 | 說明 |
|------|------|------|
| **DevOps** | 5 | CI/CD、容器、監控 |
| **Integration** | 10 | 第三方服務整合 |
| **Code Quality** | 4 | 審查、重構、效能、測試 |
| **Security/Compliance/Docs** | 3 | 安全、合規、文檔 |
| **Agents** | 6 | SA/BA/SD/QA/Dev/PM |
| **Workflows** | 2 | Sprint/Release |
| **Scenario/Dev** | 3 | 棕地分析、資料庫遷移、行動開發 |
| **總計** | **33** | - |

---

## Skill 家族

### DevOps 家族
| 命令 | Skill | 用途 |
|------|-------|------|
| `/devops-github` | GitHub Actions | CI/CD Pipeline |
| `/devops-k8s` | Kubernetes | 容器編排部署 |
| `/devops-gitlab` | GitLab CI | GitLab Pipeline |
| `/devops-docker` | Docker | 容器化 |
| `/devops-monitoring` | Monitoring | Prometheus/Grafana |

### Integration 家族
| 命令 | Skill | 用途 |
|------|-------|------|
| `/integration-oauth` | OAuth | 認證整合 |
| `/integration-stripe` | Stripe | 支付整合 |
| `/integration-api` | API Client | 通用 API 客戶端 |
| `/integration-aws` | AWS | S3/SES/SNS/Lambda |
| `/integration-webhook` | Webhook | 事件處理 |
| `/integration-firebase` | Firebase | BaaS 整合 |
| `/integration-sendgrid` | SendGrid | 郵件服務 |
| `/integration-openai` | OpenAI | AI API 整合 |
| `/integration-database` | Database | Prisma ORM / Spring Data JPA |
| `/integration-redis` | Redis | 快取/佇列 |

### Code Quality 家族
| 命令 | Skill | 用途 |
|------|-------|------|
| `/code-review` | Code Review | 標準化代碼審查 |
| `/refactor` | Refactoring | 代碼重構、技術債清除 |
| `/performance` | Performance | 效能分析與優化 |
| `/testing` | Testing Strategy | 測試策略與測試案例 |

### Security / Compliance / Docs 家族
| 命令 | Skill | 用途 |
|------|-------|------|
| `/security` | Security Audit | OWASP Top 10 安全審計 |
| `/compliance-audit` | Compliance | GDPR/HIPAA/PCI-DSS/SOC2 |
| `/documentation-api` | API Docs | OpenAPI/Swagger 文檔 |

### Agent 家族
| 命令 | Agent | 專長 |
|------|-------|------|
| `/sa-analyze` | Amanda (SA) | 需求分析、FRD、User Stories |
| `/ba-validate` | Beatrice (BA) | 需求驗證、利害關係人管理 |
| `/sd-design` | Marcus (SD) | 架構設計、SRD、API 規格 |
| `/qa-test` | Quincy (QA) | 測試策略、驗收準則 |
| `/dev-review` | David (Dev) | 代碼審查、最佳實踐 |
| `/pm-planning` | Victoria (PM) | 產品規劃、Sprint/Backlog |

### Workflow 家族
| 命令 | Workflow | 流程 |
|------|----------|------|
| `/sprint-planning` | Sprint Planning | 完整 Sprint 規劃 (PM/SA/Dev/QA) |
| `/release-management` | Release | 版本發布、驗證、回滾 |

### Scenario / Dev 家族
| 命令 | Skill | 用途 |
|------|-------|------|
| `/brownfield` | Brownfield Analysis | 既有系統分析、架構問題識別 |
| `/database-migration` | Database Migration | DB 平台遷移 (Oracle/MySQL → PostgreSQL) |
| `/mobile-development` | Mobile Dev | Android/iOS/跨平台開發規劃 |

---

## 設計原則

1. **遵循 Claude Code Agent Skills 標準** - 每個 Skill 為 `<name>/SKILL.md` 目錄格式
2. **遵循 AISDLC SOP** - 每個 Skill 對應標準作業程序
3. **人機確認點** - 🔴 標記需人類確認的步驟
4. **產出物明確** - 每個 Skill 有明確 Deliverables
5. **可組合使用** - Skills 之間可組合使用

---

## 安裝與部署

安裝腳本 (`tools/init_project.sh`) 會自動將 `.claude/skills/` 複製到專案根目錄，確保 Claude Code 能自動發現所有 Skills。

---

## 相關文檔

- [SKILL_DEVELOPMENT_PLAN.md](SKILL_DEVELOPMENT_PLAN.md) - 開發規劃

---

**維護者**: AISDLC Framework Team
