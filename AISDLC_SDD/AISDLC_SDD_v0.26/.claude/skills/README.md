# AISDLC Claude Skills
# Claude Code 技能套件

**版本**: v0.26-SDD
**建立日期**: 2025-01-22
**最後更新**: 2026-04-15
**格式標準**: Claude Code Agent Skills Standard (`<name>/SKILL.md`)
**用途**: 將 AISDLC-SDD 十大情境和 Agent 能力轉化為可重複使用的 Claude Skills
**SDD 轉型 Phase 01**: ✅ 完成（2026-04-14）— 33 個繼承 Skill 加入 SDD 合規區塊；5 個 SDD 專屬新增 Skill
**SDD 原生改寫**: ✅ 完成（2026-04-14）— 38 個 Skill 全部改寫為 SDD 原生設計（SCG 嵌入 + RTM 嵌入 + Contract-Driven）

> ℹ️ 上兩行為 **Phase 01 當時（2026-04-14）里程碑數**（33 繼承 + 5 SDD 專屬 = 38）。後續陸續加入 1 個 SDD 專屬（SCG-4 Review）與 3 個 SDD Runtime（spec-logical-validator / test-failure-analyzer / stage-compaction），**現總計 42**，以下方統計表與 `FRAMEWORK_STATUS.md` 為唯一真相源。

---

## 快速開始

```bash
# DevOps
/devops-github-actions          # GitHub Actions CI/CD
/devops-kubernetes             # Kubernetes 部署
/devops-gitlab-ci          # GitLab CI/CD
/devops-docker          # Docker 容器化
/devops-monitoring      # 監控告警

# Integration
/integration-oauth      # OAuth 認證
/integration-stripe     # Stripe 支付
/integration-api-client # API 客戶端
/integration-aws        # AWS 服務
/integration-webhook    # Webhook 處理
/integration-firebase   # Firebase
/integration-sendgrid   # SendGrid 郵件
/integration-openai     # OpenAI API
/integration-database   # Database/Prisma
/integration-redis      # Redis 快取

# Code Quality
/code-review            # 代碼審查流程
/refactoring-code-quality               # 代碼重構
/performance-optimization            # 效能優化
/testing-strategy                # 測試策略

# Security / Compliance / Docs
/security-audit               # 安全審計
/compliance-audit       # 合規審查 (GDPR/HIPAA/PCI-DSS)
/documentation-api      # API 文檔

# Agents
/sa-analyst             # SA 需求分析
/ba-analyst            # BA 業務驗證
/sd-architect              # SD 架構設計
/qa-testing                # QA 測試策略
/dev-review             # Dev 代碼審查
/pm-planning            # PM 產品規劃

# Workflows
/sprint-planning        # Sprint 規劃
/release-management     # 發布管理

# Scenario / Dev
/brownfield-analysis             # 棕地系統分析
/database-migration     # 資料庫遷移
/mobile-development     # 行動端開發

# ★ SDD 專屬（新增）
/adr-generate           # ADR 架構決策生成
/spec-compliance-check  # Spec 符合性驗證
/rtm-generate           # RTM 需求追溯矩陣
/contract-generate      # API Contract 生成（OpenAPI/CDC）
/sdd-gate               # SCG 閘門驗證
/sdd-review             # SCG-4 PR Review — 實作規格一致性審查
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
├── mobile-development/SKILL.md            # 行動端開發
│
│── # ★ SDD 專屬家族 (6個，AISDLC-SDD v0.01 新增)
├── adr-generate/SKILL.md                  # ADR 架構決策生成
├── spec-compliance-check/SKILL.md         # Spec 符合性驗證
├── rtm-generate/SKILL.md                  # RTM 需求追溯矩陣
├── contract-generate/SKILL.md             # API Contract（OpenAPI/CDC）
├── sdd-gate/SKILL.md                      # SCG 閘門驗證
├── sdd-review/SKILL.md                    # SCG-4 PR Review（實作規格一致性）
│
│── # ★ SDD Runtime 家族 (3個，FSM 閉環 runtime skill)
├── spec-logical-validator/SKILL.md        # Spec 邏輯一致性驗證（SLV-001~014）
├── test-failure-analyzer/SKILL.md         # 測試失敗 → Spec 自動映射橋接（TFA）
└── stage-compaction/SKILL.md              # Stage 凍結後上下文壓縮
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
| ★ **SDD 專屬** | 6 | ADR生成、Spec驗證、RTM、Contract、SCG閘門、SCG-4 Review |
| ★ **SDD Runtime** | 3 | Spec 邏輯驗證、測試失敗映射(TFA)、Stage 壓縮 |
| **總計** | **42** | 33 繼承（SDD 強化）+ 6 SDD 新增 + 3 SDD Runtime |

---

## Skill 家族

### DevOps 家族
| 命令 | Skill | 用途 |
|------|-------|------|
| `/devops-github-actions` | GitHub Actions | CI/CD Pipeline |
| `/devops-kubernetes` | Kubernetes | 容器編排部署 |
| `/devops-gitlab-ci` | GitLab CI | GitLab Pipeline |
| `/devops-docker` | Docker | 容器化 |
| `/devops-monitoring` | Monitoring | Prometheus/Grafana |

### Integration 家族
| 命令 | Skill | 用途 |
|------|-------|------|
| `/integration-oauth` | OAuth | 認證整合 |
| `/integration-stripe` | Stripe | 支付整合 |
| `/integration-api-client` | API Client | 通用 API 客戶端 |
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
| `/refactoring-code-quality` | Refactoring | 代碼重構、技術債清除 |
| `/performance-optimization` | Performance | 效能分析與優化 |
| `/testing-strategy` | Testing Strategy | 測試策略與測試案例 |

### Security / Compliance / Docs 家族
| 命令 | Skill | 用途 |
|------|-------|------|
| `/security-audit` | Security Audit | OWASP Top 10 安全審計 |
| `/compliance-audit` | Compliance | GDPR/HIPAA/PCI-DSS/SOC2 |
| `/documentation-api` | API Docs | OpenAPI/Swagger 文檔 |

### Agent 家族
| 命令 | Agent | 專長 |
|------|-------|------|
| `/sa-analyst` | Amanda (SA) | 需求分析、FRD、User Stories |
| `/ba-analyst` | Beatrice (BA) | 需求驗證、利害關係人管理 |
| `/sd-architect` | Marcus (SD) | 架構設計、SRD、API 規格 |
| `/qa-testing` | Quincy (QA) | 測試策略、驗收準則 |
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
| `/brownfield-analysis` | Brownfield Analysis | 既有系統分析、架構問題識別 |
| `/database-migration` | Database Migration | DB 平台遷移 (Oracle/MySQL → PostgreSQL) |
| `/mobile-development` | Mobile Dev | Android/iOS/跨平台開發規劃 |

### ★ SDD 專屬家族
| 命令 | Skill | SCG 閘門 | 用途 |
|------|-------|---------|------|
| `/adr-generate` | ADR Generate | SCG-2 | 架構決策記錄自動生成 |
| `/spec-compliance-check` | Spec Compliance | SCG-0~6 | SDD 文件規格合規驗證 |
| `/rtm-generate` | RTM Generate | SCG-0/5 | 需求追溯矩陣生成與更新 |
| `/contract-generate` | Contract Generate | SCG-3 | OpenAPI 3.1 Contract 生成 |
| `/sdd-gate` | SDD Gate | SCG-0~6 | SCG 閘門驗證 |
| `/sdd-review` | SDD Review | SCG-4 | PR Review 實作規格一致性審查 |

### ★ SDD Runtime 家族
| 命令 | Skill | 用途 |
|------|-------|------|
| `/spec-logical-validator` | Spec Logical Validator | Spec 邏輯一致性驗證（SLV-001~014：邏輯/物理可行性/不可測 AC/跨媒介一致性/沙箱硬化），於 SCG 格式驗證前執行 |
| `/test-failure-analyzer` | Test Failure Analyzer | 測試失敗 → AC/US/FRD 自動映射（TFA），分類修程式碼 vs 修 Spec，供閉環消費 |
| `/stage-compaction` | Stage Compaction | Stage 凍結里程碑後壓縮上下文、產出 Stage Summary，保後續 Token 預算 |

---

## SDD 原生設計原則（v0.02 引入，沿用至 v0.19）

1. **Spec-First 前置條件** - 每個 Skill 有明確的 SCG 閘門前置條件，未通過不可執行
2. **SCG 嵌入執行流程** - SCG 驗證步驟嵌入 Skill 執行階段，不附加在末尾
3. **RTM 嵌入** - 每個 Skill 完成後直接呼叫 `/rtm-generate update`
4. **Contract-Driven** - Integration Skills 必須有 Consumer Contract / Event Schema Contract
5. **ADR 強制** - 所有架構決策型 Skill（devops / integration）必須有 ADR
6. **文件路徑明確** - 每個 Skill 的產出物有明確的 `docs/` 路徑
7. **SDD 三大支柱貫穿** - Spec-First Gate / Design-as-Doc / Contract-Driven 嵌入每個 Skill 執行流程

---

## 安裝與部署

安裝腳本 (`tools/init_project.sh`) 會自動將 `.claude/skills/` 複製到專案根目錄，確保 Claude Code 能自動發現所有 Skills。

---

## Skill 調用命名空間（monorepo 整合層）

> 從 monorepo 根 `d:/CursorProject/AISDCL_Agent/` 啟動 session 時，Claude Code 對 skills 採
> **按需巢狀探索**：觸及 `AISDLC_SDD/` 子樹檔案後，本套 skills 會以兩種 namespace 同時曝光：
>
> | 形式 | 來源 | 用途 |
> |------|------|------|
> | `AISDLC_SDD:<skill>` | 父層 SSOT 鏡像（= ci-gate LATEST，由 `scripts/sync_exposed_skills.py` 守新鮮） | **對外預設調用**（版本穩定，免綁版本號） |
> | `AISDLC_SDD/AISDLC_SDD_v0.0X:<skill>` | 該版本目錄 | 僅限**明確指定版本做 B 軌 dogfooding** 時使用 |
>
> **優先序規範**：對外一律用父層 `AISDLC_SDD:` 形式；路徑版僅在需鎖定特定凍結版本時用。
> ⚠️ 同名 skill 在多版目錄並存（父層 + 各 `v0.0X`），CC 以路徑前綴區分；跨多版工作時務必認明
> namespace 前綴，對外請一律用父層 `AISDLC_SDD:`（= LATEST）以免誤叫到某凍結版。
> （實測 `sdd-gate` 等 skill 跨版內容一致、差異僅 line-ending〔CRLF/LF〕，無語意落後；個別 skill
> 若未來某版做語意改寫，需鎖該版內容時改用路徑版 `AISDLC_SDD/AISDLC_SDD_v0.0X:<skill>`。）
>
> 🔁 **hooks / skills 版本綁定不對稱（刻意設計，非缺陷）**：B 軌 dogfooding 以 `SDD_ACTIVE_VERSION`
> 釘凍結版時，**治理 hooks 經根 router 走該指定版、但 `AISDLC_SDD:` skills 一律曝光 LATEST**
> （skills 為無狀態知識載體、父層鏡像綁 LATEST 為單一 SSOT 並由 ci-gate 守新鮮；hooks 為有狀態
> 治理閉環故需精確版本路由）。兩者版本語意敏感度不同，採差異化策略。若需 skill 內容也鎖該版，
> 改用路徑版 `AISDLC_SDD/AISDLC_SDD_v0.0X:<skill>`。

---

## 相關文檔

- [SKILL_DEVELOPMENT_PLAN.md](SKILL_DEVELOPMENT_PLAN.md) - 開發規劃

---

**維護者**: AISDLC Framework Team
